"""SentinelX-Shift Score Fusion and Model Coordination.

Fuses supervised and anomaly risk signals:
risk = w1 * supervised + w2 * anomaly  (where w1 + w2 = 1.0)

Tuning Strategies:
(a) Standard Validation Set grid search (maximizing PR-AUC on val).
(b) Nested Inner LOFO grid search (holding out remaining attack families inside train).

Ablations:
- Max-Fusion: max(supervised, anomaly)
- Logistic Regression Stacking fit on validation scores.
"""

from typing import Dict, List, Optional, Tuple, Union, Any
import logging
import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve, auc, roc_auc_score
from sklearn.linear_model import LogisticRegression
import joblib

logger = logging.getLogger(__name__)


def compute_pr_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Compute Area Under the Precision-Recall Curve (PR-AUC)."""
    if len(np.unique(y_true)) < 2:
        return 0.0
    precision, recall, _ = precision_recall_curve(y_true, y_score)
    return float(auc(recall, precision))


def tune_weights_validation(
    s_sup_val: np.ndarray,
    s_anom_val: np.ndarray,
    y_val: np.ndarray,
    step: float = 0.05
) -> Tuple[float, float, float]:
    """Tune w1 and w2 on the standard validation set using grid search.

    Returns:
        (best_w1, best_w2, best_val_pr_auc)
    """
    best_pr_auc = -1.0
    best_w1 = 0.5

    candidates = np.linspace(0.0, 1.0, int(np.round(1.0 / step)) + 1)
    for w1 in candidates:
        w2 = 1.0 - w1
        fused = w1 * s_sup_val + w2 * s_anom_val
        score = compute_pr_auc(y_val, fused)
        if score > best_pr_auc:
            best_pr_auc = score
            best_w1 = float(w1)

    best_w2 = float(1.0 - best_w1)
    return best_w1, best_w2, best_pr_auc


def compute_operating_points(y_true: np.ndarray, y_score: np.ndarray) -> Dict[str, float]:
    """Calculate false alarms per 10k benign flows at 90% and 50% recall, plus P@100 and P@500."""
    y_true = np.asarray(y_true, dtype=int).flatten()
    y_score = np.asarray(y_score, dtype=float).flatten()

    n_pos = int(np.sum(y_true == 1))
    n_neg = int(np.sum(y_true == 0))

    if n_pos == 0 or n_neg == 0:
        return {
            "fa_per_10k_recall90": 0.0,
            "fa_per_10k_recall50": 0.0,
            "precision_at_100": 0.0,
            "precision_at_500": 0.0,
        }

    # Sort descending
    order = np.argsort(-y_score)
    y_sorted = y_true[order]

    # Cumulative TP and FP
    tp = np.cumsum(y_sorted == 1)
    fp = np.cumsum(y_sorted == 0)
    recalls = tp / float(n_pos)

    # 1. False alarms per 10k at 90% recall
    idx_90 = np.searchsorted(recalls, 0.90, side="left")
    if idx_90 < len(recalls):
        fa_90 = (float(fp[idx_90]) / float(n_neg)) * 10000.0
    else:
        fa_90 = 10000.0

    # 2. False alarms per 10k at 50% recall
    idx_50 = np.searchsorted(recalls, 0.50, side="left")
    if idx_50 < len(recalls):
        fa_50 = (float(fp[idx_50]) / float(n_neg)) * 10000.0
    else:
        fa_50 = 10000.0

    # 3. Precision@100
    k100 = min(100, len(y_sorted))
    p_100 = float(np.mean(y_sorted[:k100])) if k100 > 0 else 0.0

    # 4. Precision@500
    k500 = min(500, len(y_sorted))
    p_500 = float(np.mean(y_sorted[:k500])) if k500 > 0 else 0.0

    # 5. R-Precision (Precision evaluated at rank R = total positives, critical when positives < k)
    r_prec = float(np.mean(y_sorted[:n_pos])) if n_pos > 0 else 0.0

    return {
        "fa_per_10k_recall90": round(fa_90, 2),
        "fa_per_10k_recall50": round(fa_50, 2),
        "precision_at_100": round(p_100, 4),
        "precision_at_500": round(p_500, 4),
        "r_precision": round(r_prec, 4),
    }



class ScoreFusion:
    """Coordinates risk score fusion, tuning, and ablations."""

    def __init__(self, step: float = 0.05):
        self.step = step
        self.w1_val: float = 0.5
        self.w2_val: float = 0.5
        # Inner LOFO weights for each specific anomaly signal
        self.w1_inner_mean: float = 0.5
        self.w2_inner_mean: float = 0.5
        self.w1_inner_iforest: float = 0.5
        self.w2_inner_iforest: float = 0.5
        self.w1_inner_ae: float = 0.5
        self.w2_inner_ae: float = 0.5
        # Gated boost ablation parameters: AE + boost * (XGB > t)
        self.t_gated: float = 0.70
        self.boost_gated: float = 0.20
        self.stacker: Optional[LogisticRegression] = None
        self.is_tuned: bool = False

    @property
    def w1_inner_lofo(self) -> float:
        return self.w1_inner_mean

    @property
    def w2_inner_lofo(self) -> float:
        return self.w2_inner_mean

    def set_gated_boost_params(self, t: float, boost: float) -> "ScoreFusion":
        """Set gated boost ablation parameters tuned on inner LOFO."""
        self.t_gated = float(t)
        self.boost_gated = float(boost)
        return self

    def fit_validation_fusion(
        self,
        s_sup_val: np.ndarray,
        s_anom_val: np.ndarray,
        y_val: np.ndarray
    ) -> "ScoreFusion":
        """Fit weights (a) on standard validation set and fit stacking ablation."""
        self.w1_val, self.w2_val, _ = tune_weights_validation(
            s_sup_val, s_anom_val, y_val, step=self.step
        )

        # Fit Logistic Stacker ablation
        X_val_scores = np.column_stack([s_sup_val, s_anom_val])
        self.stacker = LogisticRegression(random_state=42)
        if len(np.unique(y_val)) > 1:
            self.stacker.fit(X_val_scores, y_val)

        self.is_tuned = True
        return self

    def set_inner_lofo_weights(
        self,
        w1: float,
        w2: float,
        signal: str = "mean"
    ) -> "ScoreFusion":
        """Set weights (b) obtained from nested inner LOFO tuning."""
        assert np.isclose(w1 + w2, 1.0), "Weights must sum to 1.0"
        if signal == "mean":
            self.w1_inner_mean = float(w1)
            self.w2_inner_mean = float(w2)
        elif signal == "iforest":
            self.w1_inner_iforest = float(w1)
            self.w2_inner_iforest = float(w2)
        elif signal == "ae":
            self.w1_inner_ae = float(w1)
            self.w2_inner_ae = float(w2)
        else:
            raise ValueError(f"Unknown inner LOFO signal: {signal}")
        return self

    def fuse(
        self,
        s_sup: np.ndarray,
        s_anom: np.ndarray,
        method: str = "inner_mean"
    ) -> np.ndarray:
        """Fuse calibrated supervised and anomaly scores."""
        if method == "val":
            return np.clip(self.w1_val * s_sup + self.w2_val * s_anom, 0.0, 1.0)
        elif method in ["inner_lofo", "inner_mean"]:
            return np.clip(self.w1_inner_mean * s_sup + self.w2_inner_mean * s_anom, 0.0, 1.0)
        elif method == "inner_iforest":
            return np.clip(self.w1_inner_iforest * s_sup + self.w2_inner_iforest * s_anom, 0.0, 1.0)
        elif method == "inner_ae":
            return np.clip(self.w1_inner_ae * s_sup + self.w2_inner_ae * s_anom, 0.0, 1.0)
        elif method == "rank_average":
            return np.clip(0.50 * s_sup + 0.50 * s_anom, 0.0, 1.0)
        elif method == "anomaly_heavy":
            return np.clip(0.20 * s_sup + 0.80 * s_anom, 0.0, 1.0)
        elif method == "gated_boost":
            # AE score plus boost when XGBoost > t
            boost_term = np.where(s_sup > self.t_gated, self.boost_gated, 0.0)
            return np.clip(s_anom + boost_term, 0.0, 1.0)
        elif method == "max":
            return np.maximum(s_sup, s_anom)
        elif method == "stacking":
            if self.stacker is None:
                return np.maximum(s_sup, s_anom)
            X_scores = np.column_stack([s_sup, s_anom])
            return self.stacker.predict_proba(X_scores)[:, 1]
        else:
            raise ValueError(f"Unknown fusion method: {method}")

