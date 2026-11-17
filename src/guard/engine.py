"""SentinelX Production Guard Engine.

Provides reusable, high-performance flow inference and alert generation:
- Reusable model caching to prevent reloading artifacts per request.
- Strict input validation against the 76 canonical netflow features.
- Preprocessing via the trained FeaturePipeline.
- Model score generation (Autoencoder anomaly, XGBoost risk).
- Gated Boost production score calculation.
- Independent confirming signal evaluation.
- Strict enforcement of Defensive Principle 1 (monitor-and-recommend only,
  autonomous blocking strictly disabled) and BruteForce protocol guardrails.
"""

from typing import Dict, List, Optional, Union, Any, Tuple
import logging
from pathlib import Path
import time
import uuid
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import joblib

from src.models.pipeline import SentinelXPredictor
from src.alerts.schema import (
    RiskTier,
    RecommendedAction,
    ScoresBreakdown,
    FlowAlert,
    AlertResponse,
)
from src.guard.confirming_signals import evaluate_confirming_signals

logger = logging.getLogger(__name__)

# Global model cache to prevent reloading from disk
_MODEL_CACHE: Dict[str, SentinelXPredictor] = {}

DEFAULT_MODEL_PATH = Path("results/models/sentinelx_lofo_DoS_DDoS.joblib")

# Documented production hyperparameters from docs/production_score.md
DEFAULT_PRODUCTION_TAU = 0.56
DEFAULT_PRODUCTION_GAMMA = 0.41

# Standard metadata and leaky columns to separate from behavioral features
METADATA_COLUMNS = {
    "Flow ID",
    "Source IP",
    "Source Port",
    "Destination IP",
    "Destination Port",
    "Timestamp",
    "Label",
    "flow_id",
    "source_ip",
    "dest_ip",
    "src_port",
    "dst_port",
    "timestamp",
    "Fwd Header Length.1",
    "Fwd Header Length_duplicated_0",
    "Unnamed: 0",
}


class FlowValidationError(ValueError):
    """Raised when flow records do not match the required schema."""
    pass


class SentinelGuard:
    """Reusable production Guard inference engine for SentinelX-Shift."""

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        tau: float = DEFAULT_PRODUCTION_TAU,
        gamma: float = DEFAULT_PRODUCTION_GAMMA,
        use_model_params: bool = False,
    ):
        """Initialize SentinelGuard with loaded model predictor and parameters.

        Args:
            model_path: Path to serialized SentinelXPredictor (.joblib).
            tau: Supervised activation threshold.
            gamma: Additive boost magnitude.
            use_model_params: If True, uses the model's inner-LOFO tuned parameters.
        """
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model artifact not found at {self.model_path}")

        self.predictor = self._load_model(self.model_path)
        self.feature_cols = self.predictor.feature_cols

        if use_model_params and hasattr(self.predictor, "fusion"):
            self.tau = float(getattr(self.predictor.fusion, "t_gated", tau))
            self.gamma = float(getattr(self.predictor.fusion, "boost_gated", gamma))
        else:
            self.tau = float(tau)
            self.gamma = float(gamma)

        logger.info(
            f"SentinelGuard initialized with model={self.model_path.name}, "
            f"features={len(self.feature_cols)}, tau={self.tau:.2f}, gamma={self.gamma:.2f}"
        )

    @classmethod
    def _load_model(cls, path: Path) -> SentinelXPredictor:
        """Cached model loader."""
        resolved = str(path.resolve())
        if resolved not in _MODEL_CACHE:
            logger.info(f"Loading SentinelXPredictor from {resolved}")
            predictor = joblib.load(resolved)
            _MODEL_CACHE[resolved] = predictor
        return _MODEL_CACHE[resolved]

    def validate_and_prepare_input(
        self,
        flows: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]]
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """Validate input records and separate feature columns from metadata.

        Returns:
            Tuple of (features_df, metadata_list)
        """
        if isinstance(flows, dict):
            df = pd.DataFrame([flows])
        elif isinstance(flows, list):
            if len(flows) == 0:
                raise FlowValidationError("Input flow batch is empty.")
            df = pd.DataFrame(flows)
        elif isinstance(flows, pd.DataFrame):
            if flows.empty:
                raise FlowValidationError("Input flow dataframe is empty.")
            df = flows.copy()
        else:
            raise FlowValidationError(f"Unsupported input type: {type(flows)}")

        # Check for missing required behavioral features
        missing_features = [col for col in self.feature_cols if col not in df.columns]
        if missing_features:
            raise FlowValidationError(
                f"Missing {len(missing_features)} required feature(s): {missing_features[:5]}... "
                f"Expected {len(self.feature_cols)} canonical behavioral features."
            )

        # Extract metadata
        metadata_list: List[Dict[str, Any]] = []
        for idx in range(len(df)):
            row = df.iloc[idx]
            meta = {}
            for col in df.columns:
                if col not in self.feature_cols or col in METADATA_COLUMNS:
                    meta[col] = row[col]
            metadata_list.append(meta)

        # Extract features dataframe strictly in expected column order
        features_df = df[self.feature_cols].copy()

        # Numeric coercion and validation
        for col in self.feature_cols:
            if not np.issubdtype(features_df[col].dtype, np.number):
                features_df[col] = pd.to_numeric(features_df[col], errors="coerce")

        # Handle inf and -inf
        features_df = features_df.replace([np.inf, -np.inf], np.nan)
        if features_df.isna().any().any():
            nan_cols = features_df.columns[features_df.isna().any()].tolist()
            logger.warning(f"NaN values detected in columns {nan_cols[:3]}, filling with 0.0")
            features_df = features_df.fillna(0.0)

        return features_df, metadata_list

    def compute_scores(self, features_df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Run feature preprocessing and score inference.

        Returns:
            Dictionary with calibrated scores and production Gated Boost.
        """
        X_trans = self.predictor.pipeline.transform(features_df)

        s_sup = self.predictor.supervised_model.predict_scores(X_trans)
        s_ae = self.predictor.autoencoder_model.predict_scores(X_trans)

        s_if: Optional[np.ndarray] = None
        s_mean_anom: Optional[np.ndarray] = None
        if hasattr(self.predictor, "iforest_model"):
            try:
                s_if = self.predictor.iforest_model.predict_scores(X_trans)
                s_mean_anom = np.clip(0.5 * (s_if + s_ae), 0.0, 1.0)
            except Exception as e:
                logger.debug(f"IForest scoring skipped: {e}")

        # Autoencoder-Anchored Gated Boost: s_guard = min(s_AE + gamma * I(s_XGB > tau), 1.0)
        gated_active = (s_sup > self.tau)
        s_prod = np.clip(s_ae + np.where(gated_active, self.gamma, 0.0), 0.0, 1.0)

        return {
            "supervised": s_sup,
            "autoencoder": s_ae,
            "iforest": s_if,
            "mean_anomaly": s_mean_anom,
            "production": s_prod,
            "gated_activation": gated_active,
        }

    def analyze_flows(
        self,
        flows: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]],
        signals: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
        batch_id: Optional[str] = None,
        site_id: Optional[str] = None,
        enforce_policy: bool = False,
    ) -> AlertResponse:
        """Analyze flow records and return structured, prioritized alerts.

        Args:
            flows: Dataframe, list of flow records, or single flow dict.
            signals: Optional confirming signal metadata (dict or list of dicts).
            batch_id: Optional identifier for ingestion batch or run.
            site_id: Optional identifier for monitored site.
            enforce_policy: If True, evaluates backend per-site blocking policy (default: False).

        Returns:
            AlertResponse with structured FlowAlert objects.
        """
        start_time = time.perf_counter()

        features_df, metadata_list = self.validate_and_prepare_input(flows)
        n_flows = len(features_df)

        # Parse signals list matching number of flows
        if isinstance(signals, dict):
            signals_list = [signals] * n_flows
        elif isinstance(signals, list):
            if len(signals) != n_flows:
                raise ValueError(f"Signals list length ({len(signals)}) does not match flows ({n_flows})")
            signals_list = signals
        else:
            signals_list = [None] * n_flows

        scores_dict = self.compute_scores(features_df)

        alerts: List[FlowAlert] = []
        high_priority_count = 0
        now_iso = datetime.now(timezone.utc).isoformat()

        for i in range(n_flows):
            s_sup = float(scores_dict["supervised"][i])
            s_ae = float(scores_dict["autoencoder"][i])
            s_if = float(scores_dict["iforest"][i]) if scores_dict["iforest"] is not None else None
            s_mean = float(scores_dict["mean_anomaly"][i]) if scores_dict["mean_anomaly"] is not None else None
            s_prod = float(scores_dict["production"][i])
            gated_act = bool(scores_dict["gated_activation"][i])

            scores_breakdown = ScoresBreakdown(
                supervised_score=s_sup,
                autoencoder_score=s_ae,
                iforest_score=s_if,
                mean_anomaly_score=s_mean,
                production_score=s_prod,
                gated_activation=gated_act,
                tau=self.tau,
                gamma=self.gamma,
            )

            # Evaluate independent confirming signals
            flow_meta = metadata_list[i]
            # Merge explicit signals with metadata if present
            merged_signals = dict(signals_list[i] or {})
            for sig_key in ["request_rate", "auth_failures", "failed_logins", "waf_alert", "http_status", "connection_attempts"]:
                if sig_key in flow_meta and sig_key not in merged_signals:
                    merged_signals[sig_key] = flow_meta[sig_key]

            evidence = evaluate_confirming_signals(merged_signals)

            # Determine suspected family from metadata or heuristics
            suspected = str(flow_meta.get("Label", flow_meta.get("suspected_family", "")))
            if not suspected or suspected == "Benign":
                suspected = None

            # Risk tier and action assignment
            policy_notes: List[str] = [
                "Defensive Principle 1 applied: autonomous packet/connection blocking strictly disabled."
            ]

            if s_prod < 0.30:
                risk_tier = RiskTier.LOW
                action = RecommendedAction.ALLOW
            elif s_prod < 0.60:
                risk_tier = RiskTier.MEDIUM
                action = RecommendedAction.MONITOR
            elif s_prod < 0.80:
                risk_tier = RiskTier.HIGH
                action = RecommendedAction.INVESTIGATE_FLOW
            else:
                risk_tier = RiskTier.CRITICAL
                action = RecommendedAction.ESCALATE_TO_ANALYST

            # Apply BruteForce Guardrail Policy
            # Model score alone must not cause priority escalation without protocol confirmation
            is_bruteforce = (
                suspected == "BruteForce"
                or "Patator" in str(flow_meta.get("Label", ""))
                or (s_sup >= 0.70 and "brute" in str(flow_meta).lower())
            )

            if is_bruteforce:
                auth_sig = evidence.get("auth_failures")
                auth_confirmed = (auth_sig is not None and auth_sig.confirmed is True)
                if not auth_confirmed:
                    # Model score alone is unauthorized to escalate BruteForce
                    if risk_tier == RiskTier.CRITICAL:
                        risk_tier = RiskTier.HIGH
                        action = RecommendedAction.INVESTIGATE_FLOW
                    policy_notes.append(
                        "BruteForce protocol guardrail applied: model score alone cannot authorize incident "
                        "escalation without independent protocol confirmation (repeated auth failures)."
                    )
                else:
                    policy_notes.append(
                        "BruteForce protocol confirmation satisfied: repeated authentication failures confirmed."
                    )

            # Apply Benign Traffic Burst Guardrail Policy
            # A traffic burst or AE reconstruction anomaly alone without confirming attack signals
            # (supervised score < tau, zero auth failures, no WAF alert) cannot trigger incident escalation.
            rate_sig = evidence.get("request_rate")
            waf_sig = evidence.get("waf_event")
            auth_sig = evidence.get("auth_failures")

            has_attack_confirmation = (
                (auth_sig is not None and auth_sig.confirmed is True)
                or (waf_sig is not None and waf_sig.confirmed is True)
                or (s_sup >= self.tau)
            )

            is_benign_label = (
                suspected is None
                or suspected == "Benign"
                or str(flow_meta.get("Label", "")) == "Benign"
            )

            if is_benign_label and not has_attack_confirmation:
                if risk_tier == RiskTier.CRITICAL:
                    risk_tier = RiskTier.MEDIUM
                    action = RecommendedAction.MONITOR
                    policy_notes.append(
                        "Benign traffic burst guardrail applied: volumetric rate burst alone without confirming attack "
                        "signals (supervised score < tau, zero auth failures, no WAF alert) cannot trigger incident escalation."
                    )

            if risk_tier in [RiskTier.HIGH, RiskTier.CRITICAL]:
                high_priority_count += 1

            flow_id_val = str(flow_meta.get("Flow ID", flow_meta.get("flow_id", f"flow-{i}")))

            # Evaluate per-site authorization state (strictly defaulting OFF)
            auto_block_auth = False
            if enforce_policy and site_id:
                try:
                    from src.enforcement.policy import get_default_enforcement_engine
                    engine = get_default_enforcement_engine()
                    target_ip = flow_meta.get("Source IP") or flow_id_val

                    # Temporary alert structure for policy engine evaluation
                    eval_alert = FlowAlert(
                        alert_id=str(uuid.uuid4()),
                        timestamp=now_iso,
                        flow_id=flow_id_val,
                        risk_tier=risk_tier,
                        recommended_action=action,
                        autonomous_blocking_authorized=False,
                        scores=scores_breakdown,
                        confirming_signals=evidence,
                        suspected_family=suspected,
                        policy_notes=list(policy_notes),
                        batch_id=batch_id,
                    )
                    decision = engine.evaluate_and_enforce(
                        alert=eval_alert,
                        target_ip=target_ip,
                        site_id=site_id,
                        flow_telemetry=flow_meta,
                    )
                    auto_block_auth = decision.allowed_to_block
                    policy_notes.append(
                        f"Enforcement policy: {decision.policy_rule} -> {decision.status.value}. {decision.reason}"
                    )
                except Exception as e:
                    logger.warning(f"Policy evaluation failed for site '{site_id}': {e}")

            alert = FlowAlert(
                alert_id=str(uuid.uuid4()),
                timestamp=now_iso,
                flow_id=flow_id_val,
                risk_tier=risk_tier,
                recommended_action=action,
                autonomous_blocking_authorized=auto_block_auth,
                scores=scores_breakdown,
                confirming_signals=evidence,
                suspected_family=suspected,
                policy_notes=policy_notes,
                batch_id=batch_id,
            )
            alerts.append(alert)

        exec_time = (time.perf_counter() - start_time) * 1000.0

        return AlertResponse(
            total_flows=n_flows,
            alerts_generated=len(alerts),
            high_priority_count=high_priority_count,
            alerts=alerts,
            execution_time_ms=round(exec_time, 2),
            model_family=self.model_path.stem,
            guard_mode="MONITOR_ONLY",
        )
