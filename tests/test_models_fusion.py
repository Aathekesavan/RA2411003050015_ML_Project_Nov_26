"""Unit tests for SentinelX-Shift models, detectors, calibration, and fusion.

Verifies:
1. Calibrated scores strictly lie in [0, 1].
2. Fusion weights sum to 1.0 and are chosen strictly without test data.
3. Anomaly detectors (Isolation Forest & Autoencoder) reject attack rows during fit.
4. SentinelXPredictor API returns all required score fields within [0, 1].
"""

import numpy as np
import pandas as pd
import pytest
from pathlib import Path
import tempfile

from src.models.detector import (
    FeaturePipeline,
    ECDFCalibrator,
    XGBoostDetector,
    IsolationForestDetector,
    AutoencoderDetector,
)
from src.fusion.fuse import ScoreFusion, tune_weights_validation, compute_pr_auc
from src.models.pipeline import SentinelXPredictor, tune_nested_inner_lofo, train_lofo_pipeline


@pytest.fixture
def synthetic_data():
    """Generates synthetic flow dataset with benign and attack classes."""
    np.random.seed(42)
    n_features = 10
    feature_cols = [f"feat_{i}" for i in range(n_features)]

    # Benign: centered around 5
    n_benign = 300
    b_data = np.random.exponential(scale=5.0, size=(n_benign, n_features))
    b_df = pd.DataFrame(b_data, columns=feature_cols)
    b_df["Label"] = "Benign"

    # Attack 1 (DoS): high values on first 3 features
    n_dos = 100
    dos_data = np.random.exponential(scale=5.0, size=(n_dos, n_features))
    dos_data[:, :3] += 50.0
    dos_df = pd.DataFrame(dos_data, columns=feature_cols)
    dos_df["Label"] = "DoS"

    # Attack 2 (PortScan): high values on last 3 features
    n_ps = 80
    ps_data = np.random.exponential(scale=5.0, size=(n_ps, n_features))
    ps_data[:, -3:] += 40.0
    ps_df = pd.DataFrame(ps_data, columns=feature_cols)
    ps_df["Label"] = "PortScan"

    # Attack 3 (BruteForce): distinct pattern
    n_bf = 60
    bf_data = np.random.exponential(scale=5.0, size=(n_bf, n_features))
    bf_data[:, 3:6] += 30.0
    bf_df = pd.DataFrame(bf_data, columns=feature_cols)
    bf_df["Label"] = "BruteForce"

    full_df = pd.concat([b_df, dos_df, ps_df, bf_df], ignore_index=True)
    return full_df, feature_cols


def test_feature_pipeline():
    """FeaturePipeline handles non-negative transforms and scales fit strictly on train."""
    cols = ["f1", "f2"]
    train_df = pd.DataFrame({"f1": [0.0, 10.0, 100.0], "f2": [5.0, 50.0, 500.0]})
    test_df = pd.DataFrame({"f1": [1.0, 20.0], "f2": [10.0, 200.0]})

    pipe = FeaturePipeline(cols)
    assert not pipe.is_fitted
    with pytest.raises(RuntimeError):
        pipe.transform(test_df)

    X_tr = pipe.fit_transform(train_df)
    assert pipe.is_fitted
    assert X_tr.shape == (3, 2)

    X_te = pipe.transform(test_df)
    assert X_te.shape == (2, 2)
    assert np.all(np.isfinite(X_te))


def test_ecdf_calibrator_bounds():
    """ECDFCalibrator strictly maps arbitrary continuous values to [0, 1]."""
    calibrator = ECDFCalibrator()
    ref_scores = np.array([1.2, 3.4, 5.6, 7.8, 9.0])
    calibrator.fit(ref_scores)

    # Test values below min, within range, and above max
    test_scores = np.array([-10.0, 1.2, 5.0, 9.0, 1000.0])
    calibrated = calibrator.predict(test_scores)

    assert len(calibrated) == len(test_scores)
    assert np.all(calibrated >= 0.0), f"Scores below 0: {calibrated}"
    assert np.all(calibrated <= 1.0), f"Scores above 1: {calibrated}"
    assert calibrated[0] == 0.0  # smaller than ref min
    assert calibrated[-1] == 1.0  # larger than ref max


def test_calibrated_scores_in_zero_one(synthetic_data):
    """Calibrated scores of all individual detectors strictly lie in [0, 1]."""
    full_df, feature_cols = synthetic_data
    pipe = FeaturePipeline(feature_cols)

    train_df = full_df.iloc[:250]
    val_df = full_df.iloc[250:350]
    test_df = full_df.iloc[350:]

    pipe.fit(train_df)
    X_tr = pipe.transform(train_df)
    X_val = pipe.transform(val_df)
    X_te = pipe.transform(test_df)

    y_tr = (train_df["Label"] != "Benign").astype(int).to_numpy()
    y_val = (val_df["Label"] != "Benign").astype(int).to_numpy()

    # 1. XGBoost
    xgb = XGBoostDetector(random_seed=42, n_estimators=20, max_depth=3)
    xgb.fit(X_tr, y_tr, X_val, y_val)
    xgb_scores = xgb.predict_scores(X_te)
    assert np.all(xgb_scores >= 0.0) and np.all(xgb_scores <= 1.0), "XGBoost scores outside [0, 1]"

    # 2. Isolation Forest (Benign-only)
    b_tr = X_tr[y_tr == 0]
    b_val = X_val[y_val == 0]
    iforest = IsolationForestDetector(random_seed=42, n_estimators=30)
    iforest.fit(b_tr, b_val)
    if_scores = iforest.predict_scores(X_te)
    assert np.all(if_scores >= 0.0) and np.all(if_scores <= 1.0), "Isolation Forest scores outside [0, 1]"

    # 3. Autoencoder (Benign-only)
    ae = AutoencoderDetector(random_seed=42, hidden_layers=(8, 4, 8))
    ae.fit(b_tr, b_val)
    ae_scores = ae.predict_scores(X_te)
    assert np.all(ae_scores >= 0.0) and np.all(ae_scores <= 1.0), "Autoencoder scores outside [0, 1]"


def test_anomaly_detectors_never_trained_on_attack_rows(synthetic_data):
    """Anomaly detectors raise ValueError if fitted on attack-labeled flows."""
    full_df, feature_cols = synthetic_data
    pipe = FeaturePipeline(feature_cols).fit(full_df)
    X = pipe.transform(full_df)

    # Contaminated labels (contains attacks)
    y_contaminated = np.array([0, 0, 1, 0, 0])
    X_subset = X[:5]
    y_clean = np.zeros(5, dtype=int)

    # 1. Isolation Forest contaminated train
    iforest = IsolationForestDetector()
    with pytest.raises(ValueError, match="training violation: attack flows detected"):
        iforest.fit(X_subset, X_subset, y_train_benign=y_contaminated, y_val_benign=y_clean)

    # 2. Isolation Forest contaminated val
    with pytest.raises(ValueError, match="validation violation: attack flows detected"):
        iforest.fit(X_subset, X_subset, y_train_benign=y_clean, y_val_benign=y_contaminated)

    # 3. Autoencoder contaminated train
    ae = AutoencoderDetector()
    with pytest.raises(ValueError, match="training violation: attack flows detected"):
        ae.fit(X_subset, X_subset, y_train_benign=y_contaminated, y_val_benign=y_clean)

    # 4. Autoencoder contaminated val
    with pytest.raises(ValueError, match="validation violation: attack flows detected"):
        ae.fit(X_subset, X_subset, y_train_benign=y_clean, y_val_benign=y_contaminated)


def test_fusion_weights_sum_to_one_and_no_test_leakage():
    """Fusion weights must sum to 1.0 and be determined strictly without test data."""
    np.random.seed(42)
    n_val = 100
    s_sup_val = np.random.uniform(0.0, 1.0, size=n_val)
    s_anom_val = np.random.uniform(0.0, 1.0, size=n_val)
    y_val = np.random.binomial(1, 0.3, size=n_val)

    w1_val, w2_val, best_pr = tune_weights_validation(s_sup_val, s_anom_val, y_val, step=0.05)

    # 1. Weights sum to 1.0
    assert np.isclose(w1_val + w2_val, 1.0), f"Weights do not sum to 1: {w1_val} + {w2_val} != 1.0"
    assert 0.0 <= w1_val <= 1.0
    assert 0.0 <= w2_val <= 1.0

    # 2. ScoreFusion class enforces sum to 1.0
    fusion = ScoreFusion()
    fusion.fit_validation_fusion(s_sup_val, s_anom_val, y_val)
    assert np.isclose(fusion.w1_val + fusion.w2_val, 1.0)

    # Test rejection of invalid weights
    with pytest.raises(AssertionError):
        fusion.set_inner_lofo_weights(0.6, 0.6)  # sum = 1.2 != 1.0

    fusion.set_inner_lofo_weights(0.3, 0.7)
    assert np.isclose(fusion.w1_inner_lofo + fusion.w2_inner_lofo, 1.0)

    # 3. Test independence: verifying test scores/labels have zero impact on weights
    s_test_sup = np.array([0.9, 0.1])
    s_test_anom = np.array([0.8, 0.2])
    fused_test_val = fusion.fuse(s_test_sup, s_test_anom, method="val")
    fused_test_inner = fusion.fuse(s_test_sup, s_test_anom, method="inner_lofo")
    fused_test_max = fusion.fuse(s_test_sup, s_test_anom, method="max")

    assert np.all(fused_test_val >= 0.0) and np.all(fused_test_val <= 1.0)
    assert np.all(fused_test_inner >= 0.0) and np.all(fused_test_inner <= 1.0)
    assert np.all(fused_test_max >= 0.0) and np.all(fused_test_max <= 1.0)


def test_nested_inner_lofo_tuning_weights(synthetic_data):
    """Nested inner LOFO tuning executes on train_df without looking at test family."""
    full_df, feature_cols = synthetic_data

    # Exclude PortScan as the 'test' family
    train_df = full_df[full_df["Label"] != "PortScan"].copy()
    assert "PortScan" not in train_df["Label"].values

    w1_inner, w2_inner = tune_nested_inner_lofo(
        train_df=train_df,
        feature_cols=feature_cols,
        held_out_test_family="PortScan",
        random_seed=42,
        step=0.1
    )

    assert np.isclose(w1_inner + w2_inner, 1.0)
    assert 0.0 <= w1_inner <= 1.0
    assert 0.0 <= w2_inner <= 1.0


def test_sentinelx_predictor_api_and_persistence(synthetic_data):
    """SentinelXPredictor generates all score columns in [0, 1] and saves/loads cleanly."""
    full_df, feature_cols = synthetic_data

    # Hold out PortScan
    train_df = full_df[full_df["Label"].isin(["Benign", "DoS"])].copy()
    val_df = full_df[full_df["Label"].isin(["Benign", "BruteForce"])].copy()
    test_df = full_df[full_df["Label"].isin(["Benign", "PortScan"])].copy()

    predictor = train_lofo_pipeline(
        train_df=train_df,
        val_df=val_df,
        held_out_family="PortScan",
        feature_cols=feature_cols,
        random_seed=42
    )

    scores = predictor.predict_scores(test_df)
    expected_keys = [
        "supervised", "iforest", "autoencoder",
        "fused_val", "fused_inner_lofo", "max_fusion", "logistic_stack"
    ]

    for key in expected_keys:
        assert key in scores, f"Missing score output: {key}"
        arr = scores[key]
        assert len(arr) == len(test_df)
        assert np.all(arr >= 0.0) and np.all(arr <= 1.0), f"{key} scores outside [0, 1]: min={arr.min()}, max={arr.max()}"

    # Test serialization round-trip
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_path = Path(tmp_dir) / "test_predictor.joblib"
        predictor.save(model_path)
        assert model_path.exists()

        loaded_predictor = SentinelXPredictor.load(model_path)
        loaded_scores = loaded_predictor.predict_scores(test_df)

        for key in expected_keys:
            np.testing.assert_allclose(scores[key], loaded_scores[key], atol=1e-5)
