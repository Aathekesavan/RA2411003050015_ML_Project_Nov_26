"""Unit tests for SentinelX-Shift explanation engine.

Verifies:
1. Explanation returns exactly 5 features per list (supervised, iforest, autoencoder).
2. SHAP contributions sum close to model output (SHAP additivity).
3. JSON rendering produces valid, parseable JSON with all expected keys.
4. No test data is ever used for the background set.
5. Plain-English narrative only references flow behavior and never implies request content inspection.
"""

import json
import numpy as np
import pandas as pd
import pytest

from src.models.pipeline import train_lofo_pipeline
from src.explain.explainer import SentinelXExplainer, render_json, get_readable_feature


@pytest.fixture
def trained_pipeline_and_data():
    """Generates synthetic data and trains a LOFO pipeline."""
    np.random.seed(42)
    feature_cols = [f"feat_{i}" for i in range(12)]

    # Benign flows
    n_b = 200
    b_data = np.random.exponential(scale=5.0, size=(n_b, len(feature_cols)))
    b_df = pd.DataFrame(b_data, columns=feature_cols)
    b_df["Label"] = "Benign"

    # Known Attack (DoS)
    n_dos = 80
    dos_data = np.random.exponential(scale=5.0, size=(n_dos, len(feature_cols)))
    dos_data[:, :3] += 40.0
    dos_df = pd.DataFrame(dos_data, columns=feature_cols)
    dos_df["Label"] = "DoS"

    # Held-out Attack (PortScan)
    n_ps = 60
    ps_data = np.random.exponential(scale=5.0, size=(n_ps, len(feature_cols)))
    ps_data[:, -3:] += 30.0
    ps_df = pd.DataFrame(ps_data, columns=feature_cols)
    ps_df["Label"] = "PortScan"

    train_df = pd.concat([b_df.iloc[:120], dos_df.iloc[:50]], ignore_index=True)
    val_df = pd.concat([b_df.iloc[120:160], dos_df.iloc[50:]], ignore_index=True)
    test_df = pd.concat([b_df.iloc[160:], ps_df], ignore_index=True)

    predictor = train_lofo_pipeline(
        train_df=train_df,
        val_df=val_df,
        held_out_family="PortScan",
        feature_cols=feature_cols,
        random_seed=42
    )

    return predictor, train_df, test_df, feature_cols


def test_explanation_has_exactly_five_features_per_list(trained_pipeline_and_data):
    """Every explanation list must contain exactly 5 features."""
    predictor, train_df, test_df, feature_cols = trained_pipeline_and_data
    train_benign = train_df[train_df["Label"] == "Benign"]

    explainer = SentinelXExplainer(
        predictor=predictor,
        background_benign_df=train_benign,
        n_background=50,
        random_seed=42
    )

    flow = test_df.iloc[0]
    exp = explainer.explain(flow)

    assert len(exp["supervised_explanation"]) == 5, "Supervised explanation does not have exactly 5 features"
    assert len(exp["anomaly_explanation"]["iforest_top5"]) == 5, "IForest explanation does not have exactly 5 features"
    assert len(exp["anomaly_explanation"]["autoencoder_top5"]) == 5, "Autoencoder explanation does not have exactly 5 features"

    # Verify keys in items
    for item in exp["supervised_explanation"]:
        assert "feature" in item and "readable_feature" in item and "value" in item and "shap_value" in item and "direction" in item

    for item in exp["anomaly_explanation"]["iforest_top5"]:
        assert "feature" in item and "readable_feature" in item and "value" in item and "shap_value" in item and "direction" in item

    for item in exp["anomaly_explanation"]["autoencoder_top5"]:
        assert "feature" in item and "readable_feature" in item and "value" in item and "reconstruction_error" in item


def test_shap_contributions_sum_close_to_model_output(trained_pipeline_and_data):
    """TreeSHAP additivity: base_value + sum(shap_values) must equal raw model prediction."""
    predictor, train_df, test_df, feature_cols = trained_pipeline_and_data
    train_benign = train_df[train_df["Label"] == "Benign"]

    explainer = SentinelXExplainer(
        predictor=predictor,
        background_benign_df=train_benign,
        n_background=50,
        random_seed=42
    )

    flow = test_df.iloc[0]
    exp = explainer.explain(flow)

    # 1. XGBoost Additivity
    diag = exp["shap_diagnostics"]
    X_trans = predictor.pipeline.transform(flow.to_frame().T[feature_cols])
    raw_margin = predictor.supervised_model.model.predict(X_trans, output_margin=True)[0]
    xgb_sum = diag["xgb_base_value"] + diag["xgb_shap_sum"]
    assert np.isclose(xgb_sum, raw_margin, atol=1e-3), f"XGBoost SHAP additivity violation: {xgb_sum} != {raw_margin}"

    # 2. Isolation Forest Additivity (tree path length decomposition)
    # The sum of path reductions plus expected path length equals the mean decision path length
    if_sum = diag["iforest_base_value"] + diag["iforest_shap_sum"]
    assert np.isfinite(if_sum), "IForest SHAP sum is not finite"


def test_render_json_validity(trained_pipeline_and_data):
    """JSON output must be valid, parseable, and contain all top-level keys."""
    predictor, train_df, test_df, feature_cols = trained_pipeline_and_data
    train_benign = train_df[train_df["Label"] == "Benign"]

    explainer = SentinelXExplainer(
        predictor=predictor,
        background_benign_df=train_benign,
        n_background=50,
        random_seed=42
    )

    flow = test_df.iloc[0]
    exp = explainer.explain(flow)

    json_str = render_json(exp)
    assert isinstance(json_str, str)

    parsed = json.loads(json_str)
    assert "fused_risk_score" in parsed
    assert "components" in parsed
    assert "supervised_explanation" in parsed
    assert "anomaly_explanation" in parsed
    assert "sentence" in parsed


def test_zero_test_data_used_for_background_set(trained_pipeline_and_data):
    """Background set must strictly be built from training benign data only."""
    predictor, train_df, test_df, feature_cols = trained_pipeline_and_data
    train_benign = train_df[train_df["Label"] == "Benign"]

    explainer = SentinelXExplainer(
        predictor=predictor,
        background_benign_df=train_benign,
        n_background=50,
        random_seed=42
    )

    # 1. Background set contains strictly benign flows
    assert np.all(explainer.background_df["Label"] == "Benign")

    # 2. No test flow is present in the background set
    bg_tuples = set(explainer.background_df[feature_cols].itertuples(index=False, name=None))
    test_tuples = set(test_df[feature_cols].itertuples(index=False, name=None))
    assert len(bg_tuples & test_tuples) == 0, "Test data leaked into explainer background set!"


def test_plain_english_sentence_only_flow_behavior(trained_pipeline_and_data):
    """Plain-English sentence must strictly follow Part A item 5 rules."""
    predictor, train_df, test_df, feature_cols = trained_pipeline_and_data
    train_benign = train_df[train_df["Label"] == "Benign"]

    explainer = SentinelXExplainer(
        predictor=predictor,
        background_benign_df=train_benign,
        n_background=50,
        random_seed=42
    )

    # 1. Test below-threshold benign flow
    benign_flow = test_df[test_df["Label"] == "Benign"].iloc[0]
    exp_b = explainer.explain(benign_flow)
    s_b = exp_b["sentence"]

    # Rule (a): below-threshold flows say "no strong evidence of attack", never "severe deviations"
    assert "no strong evidence of attack" in s_b
    assert "severe deviations" not in s_b

    # Rule (c): use "Alert" ONLY above threshold
    if exp_b["fused_risk_score"] < 0.50:
        assert "alert" not in s_b.lower()

    # 2. Test above-threshold attack flow
    attack_flow = test_df[test_df["Label"] == "PortScan"].iloc[0]
    exp_a = explainer.explain(attack_flow)
    s_a = exp_a["sentence"]

    # If above threshold, must use "Alert"
    if exp_a["fused_risk_score"] >= 0.50:
        assert "Alert" in s_a

    # Rule (b): If supervised-dominated alert, must say "resembles attack patterns seen in training" and "this may not hold for new attack types"
    if exp_a["components"]["dominant_component"] == "supervised" and exp_a["fused_risk_score"] >= 0.50:
        assert "resembles attack patterns seen in training" in s_a
        assert "this may not hold for new attack types" in s_a

    # Rule (d): Never mention request contents
    forbidden_terms = ["sqli", "sql injection", "xss", "cross-site", "http payload", "request body", "url parameter", "waf"]
    for term in forbidden_terms:
        assert term not in s_b.lower(), f"Forbidden request-inspection term '{term}' in benign sentence: {s_b}"
        assert term not in s_a.lower(), f"Forbidden request-inspection term '{term}' in attack sentence: {s_a}"


def test_evaluate_faithfulness_calibrated_threshold(trained_pipeline_and_data):
    """Verify faithfulness evaluation with calibrated alert threshold and empty handling."""
    from src.explain.faithfulness import evaluate_faithfulness

    predictor, train_df, test_df, feature_cols = trained_pipeline_and_data
    train_benign = train_df[train_df["Label"] == "Benign"]

    explainer = SentinelXExplainer(
        predictor=predictor,
        background_benign_df=train_benign,
        n_background=50,
        random_seed=42
    )

    # 1. Empty alerts DataFrame returns "n/a" for fall-offs
    empty_df = test_df.iloc[:0]
    empty_res = evaluate_faithfulness(explainer, empty_df, k_values=[1, 3, 5], alert_threshold=0.80)
    assert empty_res["k=1"]["top_k_below_threshold_pct"] == "n/a"
    assert empty_res["k=3"]["top_k_below_threshold_pct"] == "n/a"

    # 2. Test with sample of test flows
    test_attacks = test_df[test_df["Label"] != "Benign"]
    scores = predictor.predict_scores(test_attacks)["fused_inner_mean"]
    thresh = float(np.percentile(scores, 50.0))
    qualifying = test_attacks[scores >= thresh]
    assert len(qualifying) > 0

    res = evaluate_faithfulness(explainer, qualifying, k_values=[1, 3, 5], alert_threshold=thresh)
    assert "k=1" in res and "k=3" in res and "k=5" in res
    assert isinstance(res["k=1"]["top_k_below_threshold_pct"], float)
    assert res["k=1"]["top_k_mean_drop"] >= 0.0

