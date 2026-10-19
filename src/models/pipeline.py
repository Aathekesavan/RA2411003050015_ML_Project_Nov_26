"""SentinelX-Shift Model Pipeline and Predictor API.

Orchestrates training and inference:
- FeaturePipeline: log1p + StandardScaler fit on train only.
- Supervised: class-weighted XGBoost with early stopping and isotonic calibration.
- Unsupervised: Isolation Forest and Autoencoder trained strictly on BENIGN flows.
- Fusion: Combines supervised and anomaly scores using (a) validation tuning and (b) nested inner LOFO.
- API: predict_scores(X) returns a comprehensive dictionary of all risk scores.
"""

from typing import Dict, List, Optional, Tuple, Union, Any
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

from src.models.detector import (
    FeaturePipeline,
    XGBoostDetector,
    IsolationForestDetector,
    AutoencoderDetector,
)
from src.fusion.fuse import ScoreFusion, compute_pr_auc

logger = logging.getLogger(__name__)


class SentinelXPredictor:
    """End-to-end model pipeline providing unified risk score inference."""

    def __init__(
        self,
        feature_cols: List[str],
        pipeline: FeaturePipeline,
        supervised_model: XGBoostDetector,
        iforest_model: IsolationForestDetector,
        autoencoder_model: AutoencoderDetector,
        fusion: ScoreFusion,
        rule_selected_single: str = "Mean_Anomaly",
        inner_detector_means: Optional[Dict[str, float]] = None
    ):
        self.feature_cols = feature_cols
        self.pipeline = pipeline
        self.supervised_model = supervised_model
        self.iforest_model = iforest_model
        self.autoencoder_model = autoencoder_model
        self.fusion = fusion
        self.rule_selected_single = rule_selected_single
        self.inner_detector_means = inner_detector_means or {}

    def predict_scores(self, X: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Generate all risk scores for input flows.

        Returns dictionary of arrays in [0, 1]:
        - 'supervised': Calibrated XGBoost attack probability
        - 'iforest': Calibrated Isolation Forest anomaly score
        - 'autoencoder': Calibrated Autoencoder reconstruction error
        - 'mean_anomaly': Average of iforest and autoencoder
        - 'fused_val': Risk score tuned on standard validation set (method a)
        - 'fused_inner_lofo': Risk score tuned with nested inner LOFO (method b)
        - 'fused_inner_mean': Inner LOFO tuned XGBoost + Mean Anomaly
        - 'fused_inner_iforest': Inner LOFO tuned XGBoost + IForest
        - 'fused_inner_ae': Inner LOFO tuned XGBoost + Autoencoder
        - 'rank_average': Untuned 0.5/0.5 XGBoost + Mean Anomaly baseline
        - 'anomaly_heavy': Untuned 0.2/0.8 XGBoost + Mean Anomaly baseline
        - 'gated_boost': AE score plus boost when XGBoost > t (ablation)
        - 'max_fusion': Max ablation max(supervised, anomaly)
        - 'logistic_stack': Logistic regression stacked ablation
        """
        X_trans = self.pipeline.transform(X)

        s_sup = self.supervised_model.predict_scores(X_trans)
        s_iforest = self.iforest_model.predict_scores(X_trans)
        s_ae = self.autoencoder_model.predict_scores(X_trans)

        # Primary anomaly signals
        s_mean_anom = np.clip(0.5 * (s_iforest + s_ae), 0.0, 1.0)

        s_fused_val = self.fusion.fuse(s_sup, s_mean_anom, method="val")
        s_fused_mean = self.fusion.fuse(s_sup, s_mean_anom, method="inner_mean")
        s_fused_iforest = self.fusion.fuse(s_sup, s_iforest, method="inner_iforest")
        s_fused_ae = self.fusion.fuse(s_sup, s_ae, method="inner_ae")
        s_rank_avg = self.fusion.fuse(s_sup, s_mean_anom, method="rank_average")
        s_anom_heavy = self.fusion.fuse(s_sup, s_mean_anom, method="anomaly_heavy")
        s_gated = self.fusion.fuse(s_sup, s_ae, method="gated_boost")
        s_max = self.fusion.fuse(s_sup, s_mean_anom, method="max")
        s_stack = self.fusion.fuse(s_sup, s_mean_anom, method="stacking")

        return {
            "supervised": s_sup,
            "iforest": s_iforest,
            "autoencoder": s_ae,
            "mean_anomaly": s_mean_anom,
            "fused_val": s_fused_val,
            "fused_inner_lofo": s_fused_mean,
            "fused_inner_mean": s_fused_mean,
            "fused_inner_iforest": s_fused_iforest,
            "fused_inner_ae": s_fused_ae,
            "rank_average": s_rank_avg,
            "anomaly_heavy": s_anom_heavy,
            "gated_boost": s_gated,
            "max_fusion": s_max,
            "logistic_stack": s_stack,
        }

    def save(self, filepath: Union[str, Path]) -> None:
        """Persist full pipeline and models to disk."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        logger.info(f"SentinelXPredictor persisted to {path}")

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "SentinelXPredictor":
        """Load persisted predictor from disk."""
        return joblib.load(filepath)


class InnerLOFOResult(tuple):
    """Custom tuple returning (w1_mean, w2_mean) when unpacked, with access to all tuned components."""
    def __new__(
        cls,
        w1_mean: float,
        w2_mean: float,
        w1_if: float,
        w2_if: float,
        w1_ae: float,
        w2_ae: float,
        t_gated: float = 0.70,
        boost_gated: float = 0.20,
        rule_selected_single: str = "Mean_Anomaly",
        detector_means: Optional[Dict[str, float]] = None
    ):
        return super().__new__(cls, (float(w1_mean), float(w2_mean)))

    def __init__(
        self,
        w1_mean: float,
        w2_mean: float,
        w1_if: float,
        w2_if: float,
        w1_ae: float,
        w2_ae: float,
        t_gated: float = 0.70,
        boost_gated: float = 0.20,
        rule_selected_single: str = "Mean_Anomaly",
        detector_means: Optional[Dict[str, float]] = None
    ):
        self.mean = (float(w1_mean), float(w2_mean))
        self.iforest = (float(w1_if), float(w2_if))
        self.ae = (float(w1_ae), float(w2_ae))
        self.gated = (float(t_gated), float(boost_gated))
        self.rule_selected_single = rule_selected_single
        self.detector_means = detector_means or {}


def tune_nested_inner_lofo(
    train_df: pd.DataFrame,
    feature_cols: List[str],
    held_out_test_family: str,
    random_seed: int = 42,
    step: float = 0.05
) -> InnerLOFOResult:
    """Tune fusion weights (w1, w2) via nested inner LOFO inside training data.

    Tunes weights for:
    1. XGBoost + Mean Anomaly (0.5 * iforest + 0.5 * ae)
    2. XGBoost + Isolation Forest
    3. XGBoost + Autoencoder
    4. Gated Boost ablation: AE + boost * (XGB > t)
    Also selects best single detector strictly by inner validation PR-AUC.
    """
    inner_families = [fam for fam in train_df["Label"].unique() if fam not in ["Benign", held_out_test_family]]
    if not inner_families:
        return InnerLOFOResult(0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.7, 0.2, "Mean_Anomaly", {})

    candidates = np.linspace(0.0, 1.0, int(np.round(1.0 / step)) + 1)
    scores_mean = {float(w): [] for w in candidates}
    scores_if = {float(w): [] for w in candidates}
    scores_ae = {float(w): [] for w in candidates}

    # Gated boost grid: tau in [0.3, 0.5, 0.7], gamma in [0.1, 0.2, 0.3]
    gated_candidates = [(t, b) for t in [0.3, 0.5, 0.7] for b in [0.1, 0.2, 0.3]]
    scores_gated = {cand: [] for cand in gated_candidates}

    # Standalone single detector tracking for rule-based selection
    single_if_scores = []
    single_ae_scores = []
    single_mean_scores = []
    single_rank_avg_scores = []

    benign_train_full = train_df[train_df["Label"] == "Benign"]

    for inner_fam in inner_families:
        # Split benign into inner_train (70%) and inner_val (30%)
        b_shuffled = benign_train_full.sample(frac=1.0, random_state=random_seed)
        n_b_tr = int(np.round(len(b_shuffled) * 0.7))
        b_in_tr = b_shuffled.iloc[:n_b_tr]
        b_in_val = b_shuffled.iloc[n_b_tr:]

        # Attacks: inner_val gets inner_fam, inner_train gets all other remaining attacks
        other_inner_attacks = train_df[(train_df["Label"] != "Benign") & (train_df["Label"] != inner_fam)]
        inner_fam_flows = train_df[train_df["Label"] == inner_fam]

        in_train_df = pd.concat([b_in_tr, other_inner_attacks], ignore_index=True)
        in_val_df = pd.concat([b_in_val, inner_fam_flows], ignore_index=True)

        # Feature pipeline fit strictly on in_train
        inner_pipe = FeaturePipeline(feature_cols).fit(in_train_df)
        X_in_tr = inner_pipe.transform(in_train_df)
        X_in_val = inner_pipe.transform(in_val_df)

        y_in_tr = (in_train_df["Label"] != "Benign").astype(int).to_numpy()
        y_in_val = (in_val_df["Label"] != "Benign").astype(int).to_numpy()

        # Inner models
        inner_xgb = XGBoostDetector(random_seed=random_seed, n_estimators=40, max_depth=3)
        inner_xgb.fit(X_in_tr, y_in_tr, X_in_val, y_in_val)

        X_b_tr = inner_pipe.transform(b_in_tr)
        X_b_val = inner_pipe.transform(b_in_val)
        inner_if = IsolationForestDetector(random_seed=random_seed, n_estimators=50).fit(X_b_tr, X_b_val)
        inner_ae = AutoencoderDetector(random_seed=random_seed, hidden_layers=(16, 8, 16)).fit(X_b_tr, X_b_val)

        s_sup = inner_xgb.predict_scores(X_in_val)
        s_if = inner_if.predict_scores(X_in_val)
        s_a = inner_ae.predict_scores(X_in_val)
        s_mean = 0.5 * (s_if + s_a)

        # Evaluate standalone detectors for fixed-rule selection
        single_if_scores.append(compute_pr_auc(y_in_val, s_if))
        single_ae_scores.append(compute_pr_auc(y_in_val, s_a))
        single_mean_scores.append(compute_pr_auc(y_in_val, s_mean))

        # Evaluate rank average baseline (50/50 percentile ranks)
        r_xgb = pd.Series(s_sup).rank(pct=True).to_numpy()
        r_mean = pd.Series(s_mean).rank(pct=True).to_numpy()
        s_rank_avg = 0.5 * r_xgb + 0.5 * r_mean
        single_rank_avg_scores.append(compute_pr_auc(y_in_val, s_rank_avg))

        # Evaluate candidate weights on held-out inner family
        for w1 in candidates:
            w2 = 1.0 - w1
            scores_mean[float(w1)].append(compute_pr_auc(y_in_val, w1 * s_sup + w2 * s_mean))
            scores_if[float(w1)].append(compute_pr_auc(y_in_val, w1 * s_sup + w2 * s_if))
            scores_ae[float(w1)].append(compute_pr_auc(y_in_val, w1 * s_sup + w2 * s_a))

        # Evaluate gated boost candidates
        for (t_cand, b_cand) in gated_candidates:
            s_g = np.clip(s_a + np.where(s_sup > t_cand, b_cand, 0.0), 0.0, 1.0)
            scores_gated[(t_cand, b_cand)].append(compute_pr_auc(y_in_val, s_g))

    # Best weights for each anomaly signal
    def find_best(scores_dict):
        avg = {w: float(np.mean(sc)) for w, sc in scores_dict.items()}
        b_w1 = max(avg.keys(), key=lambda w: avg[w])
        return float(b_w1), float(1.0 - b_w1)

    w1_mean, w2_mean = find_best(scores_mean)
    w1_if, w2_if = find_best(scores_if)
    w1_ae, w2_ae = find_best(scores_ae)

    # Best gated parameters
    avg_gated = {cand: float(np.mean(sc)) for cand, sc in scores_gated.items()}
    best_t, best_boost = max(avg_gated.keys(), key=lambda k: avg_gated[k])

    # Rule-based selection of Best Single Detector strictly on inner validation PR-AUC
    detector_means = {
        "Isolation_Forest": float(np.mean(single_if_scores)),
        "Autoencoder": float(np.mean(single_ae_scores)),
        "Mean_Anomaly": float(np.mean(single_mean_scores)),
    }
    rule_selected_single = max(detector_means.keys(), key=lambda k: detector_means[k])

    production_candidates = {
        "Autoencoder": float(np.mean(single_ae_scores)),
        "Rank_Average": float(np.mean(single_rank_avg_scores)),
        "Gated_Boost": float(avg_gated[(best_t, best_boost)]),
    }

    logger.info(
        f"Nested Inner LOFO: Mean({w1_mean:.2f}/{w2_mean:.2f}), "
        f"IForest({w1_if:.2f}/{w2_if:.2f}), AE({w1_ae:.2f}/{w2_ae:.2f}), "
        f"Gated(tau={best_t:.1f}, gamma={best_boost:.1f}) | "
        f"Rule-Selected Best Single: {rule_selected_single} "
        f"(IF={detector_means['Isolation_Forest']:.4f}, AE={detector_means['Autoencoder']:.4f}, Mean={detector_means['Mean_Anomaly']:.4f}) | "
        f"Production Candidates Validation PR-AUC: {production_candidates}"
    )
    res = InnerLOFOResult(
        w1_mean, w2_mean, w1_if, w2_if, w1_ae, w2_ae,
        best_t, best_boost, rule_selected_single, detector_means
    )
    res.production_candidates = production_candidates
    res.inner_families_count = len(inner_families)
    return res


def train_lofo_pipeline(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    held_out_family: str,
    feature_cols: Optional[List[str]] = None,
    random_seed: int = 42,
    label_col: str = "Label"
) -> SentinelXPredictor:
    """Train complete model pipeline on a single LOFO training fold."""
    if feature_cols is None:
        feature_cols = [c for c in train_df.columns if c != label_col]

    # Verify held-out family is absent from train and val
    assert held_out_family not in train_df[label_col].values, f"Leaked {held_out_family} in train!"
    assert held_out_family not in val_df[label_col].values, f"Leaked {held_out_family} in val!"

    # 1. Feature Pipeline
    pipeline = FeaturePipeline(feature_cols)
    pipeline.fit(train_df)

    X_train = pipeline.transform(train_df)
    X_val = pipeline.transform(val_df)

    y_train = (train_df[label_col] != "Benign").astype(int).to_numpy()
    y_val = (val_df[label_col] != "Benign").astype(int).to_numpy()

    # 2. Supervised XGBoost
    xgb = XGBoostDetector(random_seed=random_seed, n_estimators=80, max_depth=4)
    xgb.fit(X_train, y_train, X_val, y_val)

    # 3. Unsupervised Detectors (Trained EXCLUSIVELY on Benign Flows)
    benign_train_mask = (train_df[label_col] == "Benign").to_numpy()
    benign_val_mask = (val_df[label_col] == "Benign").to_numpy()

    X_train_benign = X_train[benign_train_mask]
    X_val_benign = X_val[benign_val_mask]

    # Strict assertion: Anomaly detectors never observe attack rows during fit
    assert np.all(y_train[benign_train_mask] == 0), "Anomaly detector train set contains attack rows!"
    assert np.all(y_val[benign_val_mask] == 0), "Anomaly detector val calibration set contains attack rows!"

    y_train_b = y_train[benign_train_mask]
    y_val_b = y_val[benign_val_mask]

    iforest = IsolationForestDetector(random_seed=random_seed, n_estimators=100)
    iforest.fit(X_train_benign, X_val_benign, y_train_benign=y_train_b, y_val_benign=y_val_b)

    autoencoder = AutoencoderDetector(random_seed=random_seed, hidden_layers=(32, 16, 32))
    autoencoder.fit(X_train_benign, X_val_benign, y_train_benign=y_train_b, y_val_benign=y_val_b)

    # 4. Score Fusion
    # A. Validation set tuning
    s_sup_val = xgb.predict_scores(X_val)
    s_anom_val = 0.5 * (iforest.predict_scores(X_val) + autoencoder.predict_scores(X_val))

    fusion = ScoreFusion(step=0.05)
    fusion.fit_validation_fusion(s_sup_val, s_anom_val, y_val)

    # B. Nested inner LOFO tuning for all signals & ablation
    inner_res = tune_nested_inner_lofo(
        train_df=train_df,
        feature_cols=feature_cols,
        held_out_test_family=held_out_family,
        random_seed=random_seed
    )
    fusion.set_inner_lofo_weights(inner_res.mean[0], inner_res.mean[1], signal="mean")
    fusion.set_inner_lofo_weights(inner_res.iforest[0], inner_res.iforest[1], signal="iforest")
    fusion.set_inner_lofo_weights(inner_res.ae[0], inner_res.ae[1], signal="ae")
    fusion.set_gated_boost_params(inner_res.gated[0], inner_res.gated[1])

    predictor = SentinelXPredictor(
        feature_cols=feature_cols,
        pipeline=pipeline,
        supervised_model=xgb,
        iforest_model=iforest,
        autoencoder_model=autoencoder,
        fusion=fusion,
        rule_selected_single=inner_res.rule_selected_single,
        inner_detector_means=inner_res.detector_means
    )
    predictor.production_candidates = getattr(inner_res, "production_candidates", {})
    predictor.inner_families_count = getattr(inner_res, "inner_families_count", 4)
    return predictor

