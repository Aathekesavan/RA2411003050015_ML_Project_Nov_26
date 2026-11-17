"""Unit and regression tests for SentinelX Production Guard Engine.

Verifies:
1. Reusable model loading and caching.
2. Input validation for 76 canonical features, missing columns, and empty batches.
3. Preprocessing compatibility and numeric hygiene.
4. Autoencoder-Anchored Gated Boost scoring calculation.
5. Confirming signals evaluation (present, confirmed, missing/unavailable).
6. Strict enforcement of Defensive Principle 1 (autonomous_blocking_authorized is False).
7. BruteForce protocol confirmation policy (model score alone cannot escalate to CRITICAL).
8. CPU inference latency measurement (target <= 10 ms/flow).
"""

import time
import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from src.guard.engine import SentinelGuard, FlowValidationError
from src.guard.confirming_signals import evaluate_confirming_signals
from src.alerts.schema import RiskTier, RecommendedAction, FlowAlert, AlertResponse


@pytest.fixture(scope="module")
def guard():
    """Shared SentinelGuard instance."""
    return SentinelGuard(tau=0.56, gamma=0.41)


@pytest.fixture(scope="module")
def sample_flows_df():
    """Loads real preprocessed sample flows."""
    sample_path = Path("scratch/sample_flows.csv")
    if not sample_path.exists():
        # Fallback to reading 10 rows from cicids2017_sample60k.parquet
        df = pd.read_parquet("data/processed/cicids2017_sample60k.parquet")
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        df.head(10).to_csv(sample_path, index=False)
    return pd.read_csv(sample_path)


def test_guard_initialization_and_caching(guard):
    """Guard initializes properly, extracts 76 features, and reuses cached model."""
    assert len(guard.feature_cols) == 76
    assert guard.tau == 0.56
    assert guard.gamma == 0.41

    # Re-initialization should reuse cached predictor
    guard2 = SentinelGuard(model_path=guard.model_path)
    assert guard.predictor is guard2.predictor


def test_input_validation_empty(guard):
    """Empty batch or empty DataFrame raises FlowValidationError."""
    with pytest.raises(FlowValidationError, match="empty"):
        guard.validate_and_prepare_input([])

    with pytest.raises(FlowValidationError, match="empty"):
        guard.validate_and_prepare_input(pd.DataFrame())


def test_input_validation_missing_columns(guard, sample_flows_df):
    """Missing required feature columns raises FlowValidationError."""
    incomplete_df = sample_flows_df.drop(columns=["Flow Duration"])
    with pytest.raises(FlowValidationError, match="Missing 1 required feature"):
        guard.validate_and_prepare_input(incomplete_df)


def test_input_validation_nan_and_inf(guard, sample_flows_df):
    """NaN and inf values in input are sanitized without raising unhandled errors."""
    corrupted_df = sample_flows_df.copy()
    corrupted_df.loc[0, "Flow Duration"] = np.nan
    corrupted_df.loc[1, "Flow Duration"] = np.inf

    feat_df, _ = guard.validate_and_prepare_input(corrupted_df)
    assert not np.isnan(feat_df["Flow Duration"].iloc[0])
    assert not np.isinf(feat_df["Flow Duration"].iloc[1])


def test_gated_boost_scoring_formula(guard, sample_flows_df):
    """Verifies that production score strictly satisfies s_guard = min(s_AE + gamma * I(s_XGB > tau), 1.0)."""
    scores = guard.compute_scores(sample_flows_df[guard.feature_cols])

    s_sup = scores["supervised"]
    s_ae = scores["autoencoder"]
    s_prod = scores["production"]
    gated_act = scores["gated_activation"]

    expected_activation = s_sup > guard.tau
    np.testing.assert_array_equal(gated_act, expected_activation)

    expected_prod = np.clip(s_ae + np.where(expected_activation, guard.gamma, 0.0), 0.0, 1.0)
    np.testing.assert_allclose(s_prod, expected_prod, rtol=1e-5, atol=1e-5)


def test_no_autonomous_blocking(guard, sample_flows_df):
    """Defensive Principle 1: autonomous_blocking_authorized is strictly False for all alerts."""
    response = guard.analyze_flows(sample_flows_df)
    assert isinstance(response, AlertResponse)
    assert response.guard_mode == "MONITOR_ONLY"
    assert len(response.alerts) == len(sample_flows_df)

    for alert in response.alerts:
        assert alert.autonomous_blocking_authorized is False
        assert any("autonomous packet/connection blocking strictly disabled" in note for note in alert.policy_notes)


def test_confirming_signals_missing_handling():
    """Missing signals are explicitly reported as present=False, confirmed=None, never assumed confirmed."""
    evidence = evaluate_confirming_signals(None)

    for sig_name in ["request_rate", "auth_failures", "waf_event", "connection_attempts"]:
        assert sig_name in evidence
        assert evidence[sig_name].present is False
        assert evidence[sig_name].confirmed is None
        assert "not provided" in evidence[sig_name].description.lower()


def test_confirming_signals_evaluation():
    """Present confirming signals are properly evaluated against operational thresholds."""
    input_signals = {
        "request_rate": 150.0,      # > 50.0 threshold
        "auth_failures": 8,         # >= 5 threshold
        "waf_alert": True,
        "connection_attempts": 5,   # < 20 threshold
    }
    evidence = evaluate_confirming_signals(input_signals)

    assert evidence["request_rate"].present is True
    assert evidence["request_rate"].confirmed is True

    assert evidence["auth_failures"].present is True
    assert evidence["auth_failures"].confirmed is True

    assert evidence["waf_event"].present is True
    assert evidence["waf_event"].confirmed is True

    assert evidence["connection_attempts"].present is True
    assert evidence["connection_attempts"].confirmed is False  # below threshold


def test_bruteforce_policy_without_confirmation(guard, sample_flows_df):
    """BruteForce attack without protocol confirmation must NOT escalate to CRITICAL."""
    # Create synthetic BruteForce row with high score
    bf_row = sample_flows_df.iloc[0:1].copy()
    bf_row["Label"] = "BruteForce"

    # Analyze without confirming signals
    response = guard.analyze_flows(bf_row, signals=None)
    alert = response.alerts[0]

    # Verify BruteForce guardrail was applied
    assert alert.risk_tier != RiskTier.CRITICAL
    assert alert.recommended_action != RecommendedAction.ESCALATE_TO_ANALYST
    assert any("BruteForce protocol guardrail applied" in note for note in alert.policy_notes)


def test_bruteforce_policy_with_confirmation(guard, sample_flows_df):
    """BruteForce attack with confirmed auth failures satisfies protocol confirmation."""
    bf_row = sample_flows_df.iloc[0:1].copy()
    bf_row["Label"] = "BruteForce"

    # Provide confirmed authentication failures
    response = guard.analyze_flows(bf_row, signals={"auth_failures": 10})
    alert = response.alerts[0]

    assert alert.confirming_signals["auth_failures"].confirmed is True
    assert any("BruteForce protocol confirmation satisfied" in note for note in alert.policy_notes)


def test_cpu_inference_latency(guard, sample_flows_df):
    """Measures CPU inference latency and verifies <= 10 ms per flow target."""
    n_flows = len(sample_flows_df)
    # Warmup
    _ = guard.analyze_flows(sample_flows_df)

    # Benchmark across 5 iterations
    latencies = []
    for _ in range(5):
        t0 = time.perf_counter()
        resp = guard.analyze_flows(sample_flows_df)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies.append(elapsed_ms / n_flows)

    mean_latency_per_flow = float(np.mean(latencies))
    print(f"\n[BENCHMARK] Mean CPU inference latency per flow: {mean_latency_per_flow:.3f} ms (target <= 10.0 ms)")

    # Assert that inference latency is under target
    assert mean_latency_per_flow < 10.0, f"Latency {mean_latency_per_flow:.2f} ms exceeded 10.0 ms target!"
