"""SentinelX-Shift Explanation Engine.

Provides multi-signal, explanation-aware interpretability for unseen attack detection:
1. Decomposes fused risk into supervised and anomaly contributions.
2. Supervised explanation: TreeSHAP on XGBoost with top-5 features, values, contributions, and directions.
3. Anomaly explanation: TreeSHAP on Isolation Forest (path-length reduction) and Autoencoder reconstruction error (top-5 features each).
4. Plain-English narrative template built strictly from netflow behavior (zero request inspection).
5. Human-readable feature name translation.
6. JSON rendering API for the web dashboard.
"""

from typing import Dict, List, Optional, Tuple, Union, Any
import json
import logging
import numpy as np
import pandas as pd
import shap

from src.models.pipeline import SentinelXPredictor

logger = logging.getLogger(__name__)

# Canonical mapping from raw CIC-IDS2017 feature keys to human-readable network domain concepts
FEATURE_READABLE_MAP: Dict[str, str] = {
    "Flow Duration": "flow duration",
    "Total Fwd Packets": "forward packet count",
    "Total Backward Packets": "backward packet count",
    "Total Length of Fwd Packets": "forward payload volume",
    "Total Length of Bwd Packets": "backward payload volume",
    "Fwd Packet Length Max": "max forward packet size",
    "Fwd Packet Length Min": "min forward packet size",
    "Fwd Packet Length Mean": "mean forward packet size",
    "Fwd Packet Length Std": "forward packet size variance",
    "Bwd Packet Length Max": "max backward packet size",
    "Bwd Packet Length Min": "min backward packet size",
    "Bwd Packet Length Mean": "mean backward packet size",
    "Bwd Packet Length Std": "backward packet size variance",
    "Flow Bytes/s": "flow byte throughput",
    "Flow Packets/s": "flow packet rate",
    "Flow IAT Mean": "mean inter-packet arrival time",
    "Flow IAT Std": "inter-packet arrival variance",
    "Flow IAT Max": "max inter-packet arrival gap",
    "Flow IAT Min": "min inter-packet arrival gap",
    "Fwd IAT Total": "total forward inter-arrival time",
    "Fwd IAT Mean": "mean forward inter-arrival time",
    "Fwd IAT Std": "forward inter-arrival variance",
    "Fwd IAT Max": "max forward inter-arrival gap",
    "Fwd IAT Min": "min forward inter-arrival gap",
    "Bwd IAT Total": "total backward inter-arrival time",
    "Bwd IAT Mean": "mean backward inter-arrival time",
    "Bwd IAT Std": "backward inter-arrival variance",
    "Bwd IAT Max": "max backward inter-arrival gap",
    "Bwd IAT Min": "min backward inter-arrival gap",
    "Fwd PSH Flags": "forward PSH flag count",
    "Bwd PSH Flags": "backward PSH flag count",
    "Fwd URG Flags": "forward URG flag count",
    "Bwd URG Flags": "backward URG flag count",
    "Fwd Header Length": "forward header size",
    "Bwd Header Length": "backward header size",
    "Fwd Packets/s": "forward packet rate",
    "Bwd Packets/s": "backward packet rate",
    "Min Packet Length": "minimum packet size",
    "Max Packet Length": "maximum packet size",
    "Packet Length Mean": "average packet length",
    "Packet Length Std": "packet length variance",
    "Packet Length Variance": "packet length variance",
    "FIN Flag Count": "FIN connection termination count",
    "SYN Flag Count": "SYN connection handshake count",
    "RST Flag Count": "RST connection reset count",
    "PSH Flag Count": "PSH push flag count",
    "ACK Flag Count": "ACK acknowledgment packet count",
    "URG Flag Count": "URG urgent packet count",
    "CWE Flag Count": "CWE flag count",
    "ECE Flag Count": "ECE explicit congestion count",
    "Down/Up Ratio": "download-to-upload ratio",
    "Average Packet Size": "average packet size",
    "Avg Fwd Segment Size": "average forward segment size",
    "Avg Bwd Segment Size": "average backward segment size",
    "Fwd Header Length.1": "duplicate forward header length",
    "Fwd Avg Bytes/Bulk": "forward bulk byte average",
    "Fwd Avg Packets/Bulk": "forward bulk packet average",
    "Fwd Avg Bulk Rate": "forward bulk transmission rate",
    "Bwd Avg Bytes/Bulk": "backward bulk byte average",
    "Bwd Avg Packets/Bulk": "backward bulk packet average",
    "Bwd Avg Bulk Rate": "backward bulk transmission rate",
    "Subflow Fwd Packets": "subflow forward packet count",
    "Subflow Fwd Bytes": "subflow forward byte volume",
    "Subflow Bwd Packets": "subflow backward packet count",
    "Subflow Bwd Bytes": "subflow backward byte volume",
    "Init_Win_bytes_forward": "forward initial TCP window size",
    "Init_Win_bytes_backward": "backward initial TCP window size",
    "act_data_pkt_fwd": "forward packet count with valid payload",
    "min_seg_size_forward": "minimum segment size forward",
    "Active Mean": "active connection time mean",
    "Active Std": "active connection time variance",
    "Active Max": "maximum active connection time",
    "Active Min": "minimum active connection time",
    "Idle Mean": "idle connection time mean",
    "Idle Std": "idle connection time variance",
    "Idle Max": "maximum idle connection time",
    "Idle Min": "minimum idle connection time",
}


def get_readable_feature(feature_name: str) -> str:
    """Return clean human-readable domain name for feature."""
    return FEATURE_READABLE_MAP.get(feature_name, feature_name.lower().replace("_", " "))


class SentinelXExplainer:
    """Multi-model explainer synthesizing TreeSHAP, reconstruction error, and component attribution."""

    def __init__(
        self,
        predictor: SentinelXPredictor,
        background_benign_df: pd.DataFrame,
        n_background: int = 100,
        random_seed: int = 42
    ):
        self.predictor = predictor
        self.feature_cols = predictor.feature_cols
        self.random_seed = random_seed

        # Sample and cache background set strictly from benign training flows
        if len(background_benign_df) > n_background:
            self.background_df = background_benign_df.sample(n=n_background, random_state=random_seed).copy()
        else:
            self.background_df = background_benign_df.copy()

        # Feature transform of background set
        self.X_bg = self.predictor.pipeline.transform(self.background_df[self.feature_cols])

        # Initialize TreeSHAP explainers
        self.xgb_explainer = shap.TreeExplainer(self.predictor.supervised_model.model)
        self.iforest_explainer = shap.TreeExplainer(self.predictor.iforest_model.model, data=self.X_bg)

        # Baseline medians for faithfulness tests
        self.benign_medians = self.background_df[self.feature_cols].median().to_dict()

    def explain(
        self,
        flow: Union[pd.Series, pd.DataFrame, Dict[str, Any]],
        fusion_method: str = "inner_mean"
    ) -> Dict[str, Any]:
        """Generate complete explanation for a single network flow."""
        if isinstance(flow, pd.Series):
            flow_df = flow.to_frame().T
        elif isinstance(flow, dict):
            flow_df = pd.DataFrame([flow])
        else:
            flow_df = flow.copy()

        # Ensure all feature columns exist
        for col in self.feature_cols:
            if col not in flow_df.columns:
                flow_df[col] = 0.0

        # Transform flow
        X_trans = self.predictor.pipeline.transform(flow_df[self.feature_cols])

        # 1. Model scores and component fusion
        scores = self.predictor.predict_scores(flow_df[self.feature_cols])
        s_sup = float(scores["supervised"][0])
        s_if = float(scores["iforest"][0])
        s_ae = float(scores["autoencoder"][0])
        s_anom = float(scores["mean_anomaly"][0])

        if fusion_method == "inner_iforest":
            w1 = self.predictor.fusion.w1_inner_iforest
            w2 = self.predictor.fusion.w2_inner_iforest
            s_anom_used = s_if
            anom_label = "Isolation Forest"
            fused_score = float(scores["fused_inner_iforest"][0])
        elif fusion_method == "inner_ae":
            w1 = self.predictor.fusion.w1_inner_ae
            w2 = self.predictor.fusion.w2_inner_ae
            s_anom_used = s_ae
            anom_label = "Autoencoder"
            fused_score = float(scores["fused_inner_ae"][0])
        else:
            # Default: nested inner LOFO mean anomaly fusion
            w1 = self.predictor.fusion.w1_inner_mean
            w2 = self.predictor.fusion.w2_inner_mean
            s_anom_used = s_anom
            anom_label = "Mean Anomaly (IForest + Autoencoder)"
            fused_score = float(scores["fused_inner_mean"][0])

        c_sup = float(w1 * s_sup)
        c_anom = float(w2 * s_anom_used)
        dominant = "supervised" if c_sup >= c_anom else "anomaly"

        # 2. Supervised Explanation: TreeSHAP on XGBoost
        xgb_shap = self.xgb_explainer.shap_values(X_trans)[0]
        xgb_base = float(self.xgb_explainer.expected_value)
        xgb_top_idx = np.argsort(np.abs(xgb_shap))[::-1][:5]

        supervised_top5 = []
        for idx in xgb_top_idx:
            feat_name = self.feature_cols[idx]
            raw_val = float(flow_df[feat_name].iloc[0])
            shap_val = float(xgb_shap[idx])
            direction = "increases_risk" if shap_val > 0 else "decreases_risk"
            supervised_top5.append({
                "feature": feat_name,
                "readable_feature": get_readable_feature(feat_name),
                "value": round(raw_val, 4),
                "shap_value": round(shap_val, 4),
                "direction": direction,
            })

        # 3. Anomaly Explanation: TreeSHAP on Isolation Forest
        # Shorter path lengths indicate anomalies; negative depth delta corresponds to increased anomaly
        if_shap = self.iforest_explainer.shap_values(X_trans)[0]
        if_base = float(self.iforest_explainer.expected_value)
        # Sort by most negative depth impact (highest anomaly contribution)
        if_top_idx = np.argsort(if_shap)[:5]

        iforest_top5 = []
        for idx in if_top_idx:
            feat_name = self.feature_cols[idx]
            raw_val = float(flow_df[feat_name].iloc[0])
            shap_val = float(if_shap[idx])
            direction = "increases_anomaly" if shap_val < 0 else "decreases_anomaly"
            iforest_top5.append({
                "feature": feat_name,
                "readable_feature": get_readable_feature(feat_name),
                "value": round(raw_val, 4),
                "shap_value": round(shap_val, 4),
                "direction": direction,
            })

        # 4. Anomaly Explanation: Autoencoder Reconstruction Error
        recon = self.predictor.autoencoder_model.model.predict(X_trans)[0]
        feat_errors = (X_trans[0] - recon) ** 2
        ae_top_idx = np.argsort(feat_errors)[::-1][:5]

        autoencoder_top5 = []
        for idx in ae_top_idx:
            feat_name = self.feature_cols[idx]
            raw_val = float(flow_df[feat_name].iloc[0])
            err_val = float(feat_errors[idx])
            autoencoder_top5.append({
                "feature": feat_name,
                "readable_feature": get_readable_feature(feat_name),
                "value": round(raw_val, 4),
                "reconstruction_error": round(err_val, 4),
            })

        # 5. Build Plain-English Sentence from Templates
        sentence = self._build_plain_english_sentence(
            fused_score=fused_score,
            c_sup=c_sup,
            c_anom=c_anom,
            w1=w1,
            w2=w2,
            dominant=dominant,
            anom_label=anom_label,
            supervised_top5=supervised_top5,
            iforest_top5=iforest_top5,
            autoencoder_top5=autoencoder_top5
        )

        return {
            "fused_risk_score": round(fused_score, 4),
            "components": {
                "supervised_score": round(s_sup, 4),
                "anomaly_score": round(s_anom_used, 4),
                "supervised_weight": round(w1, 2),
                "anomaly_weight": round(w2, 2),
                "supervised_contribution": round(c_sup, 4),
                "anomaly_contribution": round(c_anom, 4),
                "dominant_component": dominant,
                "anomaly_signal_type": anom_label,
            },
            "supervised_explanation": supervised_top5,
            "anomaly_explanation": {
                "iforest_top5": iforest_top5,
                "autoencoder_top5": autoencoder_top5,
            },
            "sentence": sentence,
            "shap_diagnostics": {
                "xgb_base_value": round(xgb_base, 4),
                "xgb_shap_sum": round(float(np.sum(xgb_shap)), 4),
                "iforest_base_value": round(if_base, 4),
                "iforest_shap_sum": round(float(np.sum(if_shap)), 4),
            }
        }

    def _build_plain_english_sentence(
        self,
        fused_score: float,
        c_sup: float,
        c_anom: float,
        w1: float,
        w2: float,
        dominant: str,
        anom_label: str,
        supervised_top5: List[Dict[str, Any]],
        iforest_top5: List[Dict[str, Any]],
        autoencoder_top5: List[Dict[str, Any]],
        alert_threshold: float = 0.50
    ) -> str:
        """Construct domain-focused plain English explanation describing flow behavior."""
        # Rule (c): Use "Alert" strictly above threshold
        # Rule (a): Below-threshold flows say "no strong evidence of attack", never "severe deviations"
        if fused_score < alert_threshold:
            top_feats = [item["readable_feature"] for item in autoencoder_top5[:2]]
            return (
                f"Normal Network Flow (Risk: {fused_score:.2f}): Score is below detection threshold ({alert_threshold:.2f}); "
                f"no strong evidence of attack in netflow timing, packet sizes, or connection dynamics."
            )

        # Above threshold: Alert
        if dominant == "anomaly":
            top_feats = [item["readable_feature"] for item in autoencoder_top5[:3]]
            feat_phrase = f"{top_feats[0]}, {top_feats[1]}, and {top_feats[2]}"
            return (
                f"Intrusion Alert (Risk: {fused_score:.2f}) driven primarily by {anom_label} anomaly detection "
                f"(anomaly contribution {c_anom:.2f} vs supervised {c_sup:.2f}, weight {w2:.2f}). "
                f"The flow exhibited anomalous network characteristics in {feat_phrase} relative to baseline benign traffic patterns, "
                f"indicating novel or out-of-distribution network behavior rather than known signatures."
            )
        else:
            # Rule (b): Supervised-dominated alerts say "resembles attack patterns seen in training" plus "this may not hold for new attack types"
            top_feats = [item["readable_feature"] for item in supervised_top5[:3] if item["direction"] == "increases_risk"]
            if len(top_feats) < 3:
                top_feats = [item["readable_feature"] for item in supervised_top5[:3]]
            feat_phrase = f"{top_feats[0]}, {top_feats[1]}, and {top_feats[2]}"
            return (
                f"Intrusion Alert (Risk: {fused_score:.2f}) driven primarily by Supervised Classifier "
                f"(supervised contribution {c_sup:.2f} vs anomaly {c_anom:.2f}, weight {w1:.2f}). "
                f"The flow resembles attack patterns seen in training characterized by elevated {feat_phrase}; "
                f"however, this may not hold for new attack types."
            )


def render_json(explanation: Dict[str, Any], indent: int = 2) -> str:
    """Render explanation dictionary as formatted JSON string with float sanitization."""
    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    return json.dumps(explanation, cls=CustomEncoder, indent=indent)
