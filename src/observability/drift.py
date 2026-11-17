"""Score and feature drift evaluation for SentinelX Phase 5 Observability.

Compares sliding-window operational flow scores and input feature distributions
against documented benchmark baseline distributions from CIC-IDS2017.

Invariant:
Drift detection is strictly for observability and audit alerts. It NEVER triggers
automatic threshold adaptation, autonomous blocking, or automated model retraining.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from src.observability.models import (
    DistributionSummary,
    ScoreDriftMetric,
    FeatureDriftMetric,
)

# Benchmark baseline score distributions (derived from raw_scores.parquet across 5 folds/seeds)
BASELINE_SCORE_STATS = {
    "supervised_score": DistributionSummary(
        mean=0.0103, std=0.0711, min=0.0, p25=0.0, median=0.0, p75=0.0, max=1.0
    ),
    "autoencoder_score": DistributionSummary(
        mean=0.5034, std=0.2947, min=0.0, p25=0.2450, median=0.5012, p75=0.7580, max=1.0
    ),
    "production_score": DistributionSummary(
        mean=0.5076, std=0.3012, min=0.0, p25=0.2480, median=0.5020, p75=0.7620, max=1.0
    ),
}

# Benchmark baseline feature statistics (from cicids2017_sample60k.parquet)
BASELINE_FEATURE_STATS = {
    "Flow Duration": {"mean": 15838764.47, "std": 32832407.18},
    "Total Fwd Packets": {"mean": 17.16, "std": 1334.72},
    "Total Backward Packets": {"mean": 20.91, "std": 1761.76},
    "Flow Bytes/s": {"mean": 282700.22, "std": 2698027.40},
    "Flow Packets/s": {"mean": 14509.98, "std": 101158.89},
    "Packet Length Mean": {"mean": 170.84, "std": 301.20},
}


def summarize_distribution(values: np.ndarray) -> DistributionSummary:
    """Compute empirical distribution statistics for an array of values."""
    if len(values) == 0:
        return DistributionSummary()
    
    clean_vals = values[~np.isnan(values)]
    if len(clean_vals) == 0:
        return DistributionSummary()

    return DistributionSummary(
        mean=float(np.mean(clean_vals)),
        std=float(np.std(clean_vals)),
        min=float(np.min(clean_vals)),
        p25=float(np.percentile(clean_vals, 25)),
        median=float(np.median(clean_vals)),
        p75=float(np.percentile(clean_vals, 75)),
        max=float(np.max(clean_vals)),
    )


class DriftAnalyzer:
    """Computes score and input-feature drift summaries without altering scoring policies."""

    def __init__(
        self,
        score_drift_threshold: float = 0.15,
        feature_drift_std_threshold: float = 2.0,
    ):
        self.score_drift_threshold = float(score_drift_threshold)
        self.feature_drift_std_threshold = float(feature_drift_std_threshold)

    def evaluate_score_drift(self, scores_dict: Dict[str, np.ndarray]) -> List[ScoreDriftMetric]:
        """Compute score drift metrics comparing current scores against baseline."""
        results: List[ScoreDriftMetric] = []

        mapping = {
            "production_score": scores_dict.get("production"),
            "autoencoder_score": scores_dict.get("autoencoder"),
            "supervised_score": scores_dict.get("supervised"),
        }

        for score_name, arr in mapping.items():
            if arr is None or len(arr) == 0:
                continue

            current_stats = summarize_distribution(arr)
            base_stats = BASELINE_SCORE_STATS.get(score_name, DistributionSummary())

            mean_shift = abs(current_stats.mean - base_stats.mean)
            std_shift = abs(current_stats.std - base_stats.std)
            drift_detected = mean_shift > self.score_drift_threshold

            results.append(ScoreDriftMetric(
                score_name=score_name,
                baseline_stats=base_stats,
                current_stats=current_stats,
                mean_shift=float(mean_shift),
                std_shift=float(std_shift),
                drift_detected=drift_detected
            ))

        return results

    def evaluate_feature_drift(self, features_df: pd.DataFrame) -> List[FeatureDriftMetric]:
        """Compute feature drift summaries for monitored canonical netflow features."""
        results: List[FeatureDriftMetric] = []

        for feat_name, base_info in BASELINE_FEATURE_STATS.items():
            if feat_name not in features_df.columns:
                continue

            col_vals = pd.to_numeric(features_df[feat_name], errors="coerce").dropna().to_numpy()
            if len(col_vals) == 0:
                continue

            curr_mean = float(np.mean(col_vals))
            curr_std = float(np.std(col_vals))
            base_mean = base_info["mean"]
            base_std = base_info["std"]

            norm_shift = abs(curr_mean - base_mean) / (base_std + 1e-6)
            drift_detected = norm_shift > self.feature_drift_std_threshold

            results.append(FeatureDriftMetric(
                feature_name=feat_name,
                baseline_mean=float(base_mean),
                baseline_std=float(base_std),
                current_mean=curr_mean,
                current_std=curr_std,
                normalized_mean_shift=float(norm_shift),
                drift_detected=drift_detected
            ))

        return results
