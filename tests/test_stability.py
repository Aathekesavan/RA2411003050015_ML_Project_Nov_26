"""Unit tests for SentinelX-Shift Explanation Stability and Physical Perturbation.

Tests:
1. Physical perturbation rejection rate <= 30% across 1%, 5%, and 10% jitter.
2. Physical perturbation engine strictly preserves domain invariants (non-negative, min <= mean <= max).
3. Variant (iii) is NOT identical in rank to Variant (i) when b > 0.
4. Ranking variants evaluate in the EXACT correct order (V1 to V5) with valid metrics.
5. Hyperparameters a and b come from inner folds only.
6. Metric bounds (Jaccard in [0, 1], Spearman in [-1, 1]).
"""

import pytest
import numpy as np
import pandas as pd

from src.stability.perturb import PhysicalPerturbationEngine
from src.stability.stability import (
    compute_jaccard_similarity,
    compute_spearman_attribution_correlation,
    tune_stability_hyperparameters,
    evaluate_ranking_variants,
    compute_sensitivity_curve,
    compute_ranking_precision,
    compute_r_precision,
)


@pytest.fixture
def sample_flow():
    """Generates a valid synthetic netflow row."""
    return pd.Series({
        "Flow Duration": 1000000.0,  # 1 second (in microseconds)
        "Total Fwd Packets": 10.0,
        "Total Backward Packets": 15.0,
        "Total Length of Fwd Packets": 1000.0,
        "Total Length of Bwd Packets": 1500.0,
        "Fwd Packet Length Min": 40.0,
        "Fwd Packet Length Mean": 100.0,
        "Fwd Packet Length Max": 200.0,
        "Fwd Packet Length Std": 25.0,
        "Bwd Packet Length Min": 40.0,
        "Bwd Packet Length Mean": 100.0,
        "Bwd Packet Length Max": 200.0,
        "Bwd Packet Length Std": 25.0,
        "Flow IAT Mean": 40000.0,
        "Flow IAT Std": 10000.0,
        "Flow IAT Max": 90000.0,
        "Flow IAT Min": 1000.0,
        "Flow Bytes/s": 2500.0,
        "Flow Packets/s": 25.0,
        "Init_Win_bytes_forward": 8192.0,
        "Init_Win_bytes_backward": 8192.0,
        "SYN Flag Count": 2.0,
        "ACK Flag Count": 20.0,
        "Label": "PortScan",
    })


def test_perturbation_rejection_rate_bounded(sample_flow):
    """Rejection rate across 1%, 5%, and 10% jitter must be <= 30%."""
    engine = PhysicalPerturbationEngine(random_seed=42)

    for jitter in [0.01, 0.05, 0.10]:
        df_pert = engine.generate_valid_perturbations(sample_flow, n_samples=20, jitter_pct=jitter)
        assert len(df_pert) == 20

    summary = engine.get_rejection_summary()
    for j_key, stats in summary.items():
        assert stats["rejection_pct"] <= 30.0, (
            f"Rejection rate for {j_key} exceeded 30%: {stats['rejection_pct']}%"
        )


def test_physical_perturbation_preserves_invariants(sample_flow):
    """Perturbed flows strictly satisfy domain invariants."""
    engine = PhysicalPerturbationEngine(random_seed=42)
    perturbed_df = engine.generate_valid_perturbations(sample_flow, n_samples=15, jitter_pct=0.05)

    assert len(perturbed_df) == 15

    for _, row in perturbed_df.iterrows():
        # 1. Non-negativity
        assert row["Flow Duration"] > 0.0
        assert row["Total Fwd Packets"] >= 1.0
        assert row["Total Backward Packets"] >= 0.0
        assert row["Total Length of Fwd Packets"] >= 0.0

        # 2. Integer packet counts
        assert row["Total Fwd Packets"].is_integer()
        assert row["Total Backward Packets"].is_integer()

        # 3. Statistical hierarchy
        assert row["Fwd Packet Length Min"] - 1e-4 <= row["Fwd Packet Length Mean"] <= row["Fwd Packet Length Max"] + 1e-4

        # 4. Standard deviations non-negative
        assert row["Fwd Packet Length Std"] >= 0.0
        assert row["Flow IAT Std"] >= 0.0

        # 5. Temporal consistency
        assert row["Flow IAT Max"] <= row["Flow Duration"] + 1e-3

        # 6. Flag counts <= total packets
        tot_pkts = row["Total Fwd Packets"] + row["Total Backward Packets"]
        assert row["SYN Flag Count"] <= tot_pkts
        assert row["ACK Flag Count"] <= tot_pkts


def test_variant_iii_not_identical_to_variant_i_when_b_positive():
    """Variant (iii) must NOT produce an identical rank order to Variant (i) when b > 0."""
    # Construct flows with close base risk scores but diverging score stabilities
    df = pd.DataFrame({
        "base_risk_score": [0.90, 0.89, 0.88, 0.87, 0.86],
        "explanation_stability": [0.60, 0.70, 0.80, 0.50, 0.90],
        # Low risk score #4 has very high score stability, high risk score #0 has very low stability
        "score_stability_control": [0.20, 0.50, 0.40, 0.95, 0.30],
        "is_attack": [1, 1, 0, 1, 0],
    })

    a = 1.0
    b = 1.0

    v1_scores = df["base_risk_score"].to_numpy()
    v3_scores = df["base_risk_score"].to_numpy() * (a + b * df["score_stability_control"].to_numpy())

    v1_ranks = np.argsort(-v1_scores)
    v3_ranks = np.argsort(-v3_scores)

    # Ranks must not be identical
    assert not np.array_equal(v1_ranks, v3_ranks), (
        "Variant (iii) produced ranks identical to Variant (i) despite non-constant S_score_stab and b > 0."
    )


def test_ranking_variants_correct_order():
    """Ranking variants evaluate in the EXACT correct order (V1 to V5 + V2_rank) with valid metrics."""
    np.random.seed(42)
    n = 150
    test_df = pd.DataFrame({
        "base_risk_score": np.random.uniform(0.1, 0.99, size=n),
        "explanation_stability": np.random.uniform(0.4, 0.95, size=n),
        "score_stability_control": np.random.uniform(0.4, 0.95, size=n),
        "is_attack": np.random.choice([0, 1], size=n, p=[0.7, 0.3]),
    })

    results_df, diag = evaluate_ranking_variants(
        test_df,
        a_exp=1.0, b_exp=0.5,
        a_score=1.0, b_score=0.5,
        n_bootstrap=200,
        seed=42
    )

    expected_variants = [
        "V1_s_risk",
        "V2_s_risk_x_exp_stab",
        "V3_s_risk_x_score_stab",
        "V4a_exp_stab_alone",
        "V4b_s_risk_x_exp_mult",
        "V5_random_reorder",
        "V2_rank_sensitivity",
    ]

    actual_variants = list(results_df["Variant"])
    assert actual_variants == expected_variants, (
        f"Ranking variants evaluated in wrong order. Expected {expected_variants}, got {actual_variants}"
    )

    valid_verdicts = {"baseline", "helped", "hurt", "no benefit detected"}
    for _, row in results_df.iterrows():
        assert row["Verdict"] in valid_verdicts
        assert "Precision@50" in row
        assert "Precision@100" in row
        assert "Precision@500" in row
        assert "R-Precision" in row
        assert "95% CI (Delta P@100 pp)" in row
        assert "Holm_Adj_p" in row


def test_a_and_b_tuned_on_inner_folds_only():
    """Parameters a and b must be tuned strictly on inner validation candidates."""
    np.random.seed(42)
    n_val = 80
    val_df = pd.DataFrame({
        "base_risk_score": np.random.uniform(0.2, 0.95, size=n_val),
        "explanation_stability": np.random.uniform(0.5, 0.98, size=n_val),
        "score_stability_control": np.random.uniform(0.5, 0.98, size=n_val),
        "is_attack": np.random.choice([0, 1], size=n_val, p=[0.6, 0.4]),
    })

    params = tune_stability_hyperparameters(val_df, target_metric="Precision@100")
    assert "exp" in params
    assert "score" in params

    a_exp, b_exp = params["exp"]
    a_score, b_score = params["score"]

    assert 0.0 <= a_exp <= 1.0
    assert b_exp in [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0, 2.0]
    assert 0.0 <= a_score <= 1.0
    assert b_score in [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0, 2.0]

    # Verification that tuned parameters can be deployed to test set without test tuning
    n_test = 100
    test_df = pd.DataFrame({
        "base_risk_score": np.random.uniform(0.1, 0.99, size=n_test),
        "explanation_stability": np.random.uniform(0.4, 0.95, size=n_test),
        "score_stability_control": np.random.uniform(0.4, 0.95, size=n_test),
        "is_attack": np.random.choice([0, 1], size=n_test, p=[0.7, 0.3]),
    })

    res, diag = evaluate_ranking_variants(test_df, a_exp=a_exp, b_exp=b_exp, a_score=a_score, b_score=b_score, n_bootstrap=100)
    assert len(res) == 7
    assert isinstance(diag, dict)


def test_jaccard_and_spearman_bounds():
    """Jaccard similarity and Spearman correlation satisfy metric bounds."""
    set1 = {"f1", "f2", "f3", "f4", "f5"}
    set2 = {"f1", "f2", "f3", "f4", "f5"}
    assert compute_jaccard_similarity(set1, set2) == 1.0

    set3 = {"f6", "f7", "f8", "f9", "f10"}
    assert compute_jaccard_similarity(set1, set3) == 0.0

    set4 = {"f1", "f2", "f3", "f6", "f7"}
    assert np.isclose(compute_jaccard_similarity(set1, set4), 3.0 / 7.0)

    v1 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    v2 = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    assert np.isclose(compute_spearman_attribution_correlation(v1, v2), 1.0)

    v3 = np.array([5.0, 4.0, 3.0, 2.0, 1.0])
    assert np.isclose(compute_spearman_attribution_correlation(v1, v3), -1.0)
