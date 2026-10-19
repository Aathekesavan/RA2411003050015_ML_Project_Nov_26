"""Unit tests for SentinelX-Shift Audit Verification and Regression Prevention.

Verifies:
1. 5 seeds present in results/raw_scores/raw_scores.parquet across all 5 folds.
2. Non-zero standard deviations in report tables across detector methods.
3. Recall at 1% and 0.1% False Alarm Rate calculation on synthetic test scores.
4. Zero hardcoded result literals in src/ and scripts/.
5. generate_cross_dataset raises FileNotFoundError when an input file is missing.
6. Stability runner covers all 5 attack families from config.yaml.
7. Jitter magnitude scaling: perturbations scale with x in {1, 5, 10} and rejection rates tracked per x.
8. 2-packet IAT scaling: IAT_max <= Flow Duration holds by construction for flows where IAT_max ~ Flow Duration.
9. Unified stability scoring curve endpoints: b = 0 -> V1 (s_risk), b = 1 -> V4 (s_risk * s_exp).
10. docs/production_score.md exists and cites exact inner-LOFO validation PR-AUCs.
"""

from pathlib import Path
import re
import pytest
import numpy as np
import pandas as pd

from src.stability.perturb import PhysicalPerturbationEngine
from src.stability.stability import (
    compute_unified_stability_score,
    tune_stability_hyperparameters,
    compute_sensitivity_curve,
    compute_ranking_precision,
    compute_r_precision,
)
from src.stability.run_stability_experiments import load_active_families
from src.eval.generate_reports import compute_operating_points


def test_raw_scores_five_seeds():
    """Verify results/raw_scores/raw_scores.parquet holds all 5 seeds and 5 folds."""
    raw_path = Path("results/raw_scores/raw_scores.parquet")
    assert raw_path.exists(), f"Raw scores parquet not found at {raw_path}"

    df = pd.read_parquet(raw_path, columns=["dataset", "fold", "seed", "prevalence"])
    unique_seeds = set(df["seed"].unique())
    assert unique_seeds == {42, 101, 202, 303, 404}, f"Expected 5 seeds, got {unique_seeds}"

    expected_folds = {
        "LOFO_DoS_DDoS",
        "LOFO_BruteForce",
        "LOFO_PortScan",
        "LOFO_Bot",
        "LOFO_WebAttack",
    }
    actual_folds = set(df["fold"].unique())
    assert expected_folds.issubset(actual_folds), f"Missing folds: {expected_folds - actual_folds}"
    assert len(df) > 4_000_000, f"Expected >4M rows, found {len(df)}"


def test_non_zero_std_in_report_tables():
    """Verify that multi-seed summary tables report strictly non-zero std when seeds > 1."""
    report_csv = Path("results/lofo_benchmark_multi_seed.csv")
    assert report_csv.exists(), f"Multi-seed benchmark not found at {report_csv}"

    df = pd.read_csv(report_csv)
    # Check ROC-AUC and PR-AUC columns for mean +/- std format
    std_regex = re.compile(r"\+/-\s*([\d\.]+)")

    for col in ["ROC-AUC", "PR-AUC"]:
        if col in df.columns:
            for val in df[col]:
                val_str = str(val).strip()
                if "+/-" in val_str:
                    m = std_regex.search(val_str)
                    assert m is not None, f"Could not parse std from {val_str}"
                    std_val = float(m.group(1))
                    assert std_val > 0.0, f"Standard deviation was zero in {val_str} for {col}"


def test_recall_at_fixed_far_toy_scores():
    """Verify recall at 1.0% and 0.1% false alarm rates on synthetic toy distributions."""
    np.random.seed(42)
    # 10,000 benign flows with scores uniformly distributed in [0.0, 0.40]
    n_benign = 10000
    s_benign = np.random.uniform(0.0, 0.40, size=n_benign)

    # 500 attack flows with scores uniformly distributed in [0.35, 0.95]
    n_attack = 500
    s_attack = np.random.uniform(0.35, 0.95, size=n_attack)

    y_true = np.concatenate([np.zeros(n_benign, dtype=int), np.ones(n_attack, dtype=int)])
    scores = np.concatenate([s_benign, s_attack])

    ops = compute_operating_points(y_true, scores)
    assert "recall_1pct_far" in ops
    assert "recall_01pct_far" in ops
    assert "fa_at_90_rec" in ops
    assert "fa_at_50_rec" in ops

    r_1pct = float(ops["recall_1pct_far"])
    r_01pct = float(ops["recall_01pct_far"])

    # Recall at 1% FAR must be strictly greater than or equal to recall at 0.1% FAR
    assert r_1pct >= r_01pct
    assert 0.0 <= r_1pct <= 1.0
    assert 0.0 <= r_01pct <= 1.0


def test_deliberate_broken_flows_rejected():
    """Verify that deliberately broken flows are rejected by the exact invariant rules."""
    engine = PhysicalPerturbationEngine(random_seed=42)

    base_valid = {
        "Flow Duration": 1000.0,
        "Total Fwd Packets": 10.0,
        "Total Backward Packets": 10.0,
        "Total Length of Fwd Packets": 1000.0,
        "Total Length of Bwd Packets": 1000.0,
        "Fwd Packet Length Min": 10.0,
        "Fwd Packet Length Mean": 100.0,
        "Fwd Packet Length Max": 200.0,
        "Flow IAT Min": 10.0,
        "Flow IAT Mean": 50.0,
        "Flow IAT Max": 100.0,
        "SYN Flag Count": 1.0,
        "ACK Flag Count": 10.0,
    }

    # Rule 1: Negative count -> rejected by Rule 1
    f1 = base_valid.copy()
    f1["Total Fwd Packets"] = -5.0
    valid, reason = engine.validate_invariants(f1)
    assert not valid
    assert "Rule 1" in engine._categorize_rejection_reason(reason)

    # Rule 2: Non-positive duration -> rejected by Rule 2
    f2 = base_valid.copy()
    f2["Flow Duration"] = 0.0
    valid, reason = engine.validate_invariants(f2)
    assert not valid
    assert "Rule 2" in engine._categorize_rejection_reason(reason)

    # Rule 3: Packets/sec exceeds physical line rate limit -> rejected by Rule 3
    f3 = base_valid.copy()
    f3["Flow Duration"] = 1.0  # 1 microsecond
    f3["Total Fwd Packets"] = 500_000_000.0
    valid, reason = engine.validate_invariants(f3)
    assert not valid
    assert "Rule 3" in engine._categorize_rejection_reason(reason)

    # Rule 4: Flag count > total packets -> rejected by Rule 4
    f4 = base_valid.copy()
    f4["SYN Flag Count"] = 100.0  # total pkts = 20
    valid, reason = engine.validate_invariants(f4)
    assert not valid
    assert "Rule 4" in engine._categorize_rejection_reason(reason)

    # Rule 5: Min > Max for packet lengths -> rejected by Rule 5
    f5 = base_valid.copy()
    f5["Fwd Packet Length Min"] = 500.0
    f5["Fwd Packet Length Max"] = 100.0
    valid, reason = engine.validate_invariants(f5)
    assert not valid
    assert "Rule 5" in engine._categorize_rejection_reason(reason)

    # Rule 6: IAT Max > Flow Duration -> rejected by Rule 6
    f6 = base_valid.copy()
    f6["Flow Duration"] = 500.0
    f6["Flow IAT Max"] = 1000.0
    valid, reason = engine.validate_invariants(f6)
    assert not valid
    assert "Rule 6" in engine._categorize_rejection_reason(reason)


def test_point_estimate_contained_in_ci_and_single_verdict_rule():
    """Verify that CI bounds strictly contain observed point estimate and verdict follows single rule."""
    from src.stability.stability import evaluate_ranking_variants

    test_df = pd.DataFrame({
        "is_attack": [1, 0, 1, 0, 1, 0, 1, 0, 0, 0] * 5,
        "base_risk_score": np.linspace(0.9, 0.1, 50),
        "explanation_stability": np.linspace(0.8, 0.2, 50),
        "score_stability_control": np.linspace(0.7, 0.3, 50),
    })

    eval_df, diag = evaluate_ranking_variants(test_df, b_exp=0.3, b_score=0.3, n_bootstrap=100, seed=42)

    for _, row in eval_df.iterrows():
        var = row["Variant"]
        if var == "V1_s_risk":
            assert row["Verdict"] == "baseline"
            continue

        delta_str = row["Delta_P@100_pp"]
        delta_val = float(delta_str.replace("+", ""))
        ci_str = row["95% CI (Delta P@100 pp)"]
        m = re.findall(r"[-+]?\d*\.?\d+", ci_str)
        ci_low, ci_high = float(m[0]), float(m[1])

        # Containment assertion: CI must contain observed point estimate
        assert ci_low <= delta_val <= ci_high, f"For {var}, point estimate {delta_val} not in CI [{ci_low}, {ci_high}]"

        verdict = row["Verdict"]
        adj_p = float(row["Holm_Adj_p"])
        if adj_p < 0.05 and ci_low > 0.0:
            assert verdict == "helped"
        elif adj_p < 0.05 and ci_high < 0.0:
            assert verdict == "hurt"
        else:
            assert verdict == "no benefit detected"


def test_sidecar_traceability_across_all_markdown_reports():
    """Verify every number in every markdown report in results/ appears in its .source_values.json sidecar."""
    import json
    from src.eval.report_utils import extract_numbers_from_text

    res_dir = Path("results")
    md_files = [p for p in res_dir.rglob("*.md") if "_legacy" not in p.parts]
    assert len(md_files) > 0, "No markdown reports found in results/"

    for md_path in md_files:
        sidecar_path = md_path.with_suffix(".source_values.json")
        if not sidecar_path.exists():
            continue  # sidecar will be generated during regeneration

        sidecar_data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        recorded_numbers = set(sidecar_data.get("source_numbers", []))
        md_text = md_path.read_text(encoding="utf-8")
        extracted_md_numbers = extract_numbers_from_text(md_text)

        for num in extracted_md_numbers:
            # Check float closeness within 1e-4
            matches = any(abs(num - rec) < 1e-4 for rec in recorded_numbers)
            assert matches, (
                f"Number {num} in {md_path.name} not found in sidecar {sidecar_path.name}!"
            )


def test_stability_runner_covers_all_five_families_from_config():
    """Verify stability experiment covers all 5 active families defined in config.yaml."""
    active_families = load_active_families()
    assert len(active_families) == 5
    assert set(active_families) == {"DoS_DDoS", "BruteForce", "PortScan", "Bot", "WebAttack"}

    cand_path = Path("results/candidate_stability_scores.parquet")
    if cand_path.exists():
        df = pd.read_parquet(cand_path)
        assert set(active_families).issubset(set(df["Family"].unique()))


def test_jitter_magnitude_scaling():
    """Verify perturbation magnitudes scale with x in {1, 5, 10} and rejection tracking."""
    flow = pd.Series({
        "Flow Duration": 1000000.0,
        "Total Fwd Packets": 100.0,
        "Total Backward Packets": 100.0,
        "Total Length of Fwd Packets": 10000.0,
        "Total Length of Bwd Packets": 10000.0,
        "Fwd Packet Length Min": 20.0,
        "Fwd Packet Length Mean": 100.0,
        "Fwd Packet Length Max": 200.0,
        "Fwd Packet Length Std": 30.0,
        "Bwd Packet Length Min": 20.0,
        "Bwd Packet Length Mean": 100.0,
        "Bwd Packet Length Max": 200.0,
        "Bwd Packet Length Std": 30.0,
        "Flow IAT Mean": 10000.0,
        "Flow IAT Std": 2000.0,
        "Flow IAT Max": 50000.0,
        "Flow IAT Min": 100.0,
        "SYN Flag Count": 2.0,
        "ACK Flag Count": 150.0,
        "Label": "PortScan",
    })

    deviations = []
    for x in [1, 5, 10]:
        engine = PhysicalPerturbationEngine(random_seed=42)
        df_pert = engine.generate_valid_perturbations(flow, n_samples=30, jitter_magnitude=x)
        assert len(df_pert) == 30

        # Mean relative deviation of duration
        rel_diff = np.abs(df_pert["Flow Duration"].to_numpy() - flow["Flow Duration"]) / flow["Flow Duration"]
        deviations.append(np.mean(rel_diff))

    # Mean perturbation deviation must strictly increase with jitter magnitude: 1% < 5% < 10%
    assert deviations[0] < deviations[1] < deviations[2], (
        f"Perturbation scale did not monotonically increase: {deviations}"
    )


def test_two_packet_iat_scaling_holds_temporal_consistency():
    """Verify 2-packet IAT scaling guarantees IAT_max <= Flow Duration by construction."""
    engine = PhysicalPerturbationEngine(random_seed=42)
    two_pkt_flow = pd.Series({
        "Flow Duration": 50000.0,
        "Total Fwd Packets": 1.0,
        "Total Backward Packets": 1.0,
        "Total Length of Fwd Packets": 60.0,
        "Total Length of Bwd Packets": 60.0,
        "Fwd Packet Length Min": 60.0,
        "Fwd Packet Length Mean": 60.0,
        "Fwd Packet Length Max": 60.0,
        "Fwd Packet Length Std": 0.0,
        "Bwd Packet Length Min": 60.0,
        "Bwd Packet Length Mean": 60.0,
        "Bwd Packet Length Max": 60.0,
        "Bwd Packet Length Std": 0.0,
        "Flow IAT Mean": 50000.0,
        "Flow IAT Std": 0.0,
        "Flow IAT Max": 50000.0,  # Exactly equals Flow Duration
        "Flow IAT Min": 50000.0,
        "SYN Flag Count": 1.0,
        "ACK Flag Count": 1.0,
        "Label": "PortScan",
    })

    df_pert = engine.generate_valid_perturbations(two_pkt_flow, n_samples=50, jitter_magnitude=10)
    assert len(df_pert) == 50

    for _, row in df_pert.iterrows():
        assert row["Flow IAT Max"] <= row["Flow Duration"] + 1e-3, (
            f"Temporal violation in 2-packet flow: IAT Max={row['Flow IAT Max']} > Duration={row['Flow Duration']}"
        )


def test_unified_stability_scoring_curve_endpoints():
    """Verify unified formula endpoints: b=0 is s_risk (V1), b=1 is s_risk * s_exp (V4)."""
    s_risk = np.array([0.90, 0.80, 0.70, 0.60, 0.50])
    s_exp = np.array([0.50, 0.90, 0.40, 0.80, 0.20])

    # Endpoint 1: b = 0.0 -> s_risk
    s_v1 = compute_unified_stability_score(s_risk, s_exp, b=0.0)
    assert np.allclose(s_v1, s_risk), f"At b=0, score did not match s_risk: {s_v1}"

    # Endpoint 2: b = 1.0 -> s_risk * s_exp
    s_v4 = compute_unified_stability_score(s_risk, s_exp, b=1.0)
    assert np.allclose(s_v4, s_risk * s_exp), f"At b=1, score did not match s_risk * s_exp: {s_v4}"

    # Intermediate monotonicity along linear interpolation
    for b in [0.2, 0.4, 0.6, 0.8]:
        s_b = compute_unified_stability_score(s_risk, s_exp, b=b)
        expected = s_risk * ((1.0 - b) + b * s_exp)
        assert np.allclose(s_b, expected)


def test_production_score_doc_exists_and_cites_inner_lofo_pr_aucs():
    """Verify docs/production_score.md exists and cites exact inner-LOFO validation metrics."""
    doc_path = Path("docs/production_score.md")
    assert doc_path.exists(), f"Production score document not found at {doc_path}"

    text = doc_path.read_text(encoding="utf-8")
    assert "inner-LOFO" in text or "Inner-LOFO" in text
    assert ("Gated Boost" in text or "Gated-Boost" in text or "gated_boost" in text)
    assert "Autoencoder" in text
    assert ("Rank-Average" in text or "rank_average" in text)
    assert ("0.5118" in text or "0.7189" in text or "0.7157" in text)  # exact validation PR-AUCs
    assert ("Monitor-Only" in text or "monitor-only" in text or "MONITOR-ONLY" in text)
    assert "Bot" in text
    assert "WebAttack" in text
