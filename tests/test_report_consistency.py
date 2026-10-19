"""Rigorous Consistency and Traceability Verification Test for SentinelX-Shift.

Verifies:
1. Benchmark table metrics (ROC-AUC, PR-AUC, Recall@1%FAR, Recall@0.1%FAR, FA@90%, FA@50%)
   recomputed directly from raw_scores.parquet using independent sklearn.metrics.
2. Verification of Gated_Boost, Family_Seen_Control, and Merged Holdout in benchmark table.
3. Fusion vs single detector comparison table deltas recomputed directly using sklearn.metrics.
4. Cross-dataset comparison table consistency with raw row counts (2,830,743), duplication rate (21.03%),
   leakage audit values, and dataset-level fusion gain statement.
"""

from pathlib import Path
import re
import pytest
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score


def parse_reported_mean(val_str: str) -> float:
    """Extract numeric mean from string formatted as 'mean +/- std' or 'mean%'."""
    clean = str(val_str).replace("%", "").strip()
    if "+/-" in clean:
        clean = clean.split("+/-")[0].strip()
    if "[" in clean:
        clean = clean.split("[")[0].strip()
    return float(clean)


def calc_empirical_recall_at_far(y_true: np.ndarray, scores: np.ndarray, target_far: float) -> float:
    """Compute empirical recall at target FAR with fractional tie-breaking interpolation."""
    neg_scores = scores[y_true == 0]
    pos_scores = scores[y_true == 1]
    n_neg = len(neg_scores)
    n_pos = len(pos_scores)
    if n_pos == 0 or n_neg == 0:
        return 0.0

    thresh = float(np.percentile(neg_scores, (1.0 - target_far) * 100.0))
    k_allowed = int(np.floor(target_far * n_neg))
    n_gt = int(np.sum(neg_scores > thresh))
    n_eq = int(np.sum(neg_scores == thresh))
    p_tie = max(0.0, min(1.0, float(k_allowed - n_gt) / float(n_eq))) if n_eq > 0 else 0.0

    pos_gt = np.sum(pos_scores > thresh)
    pos_eq = np.sum(pos_scores == thresh)
    return float(pos_gt + p_tie * pos_eq) / float(n_pos)


def test_recompute_ten_random_metrics_lofo_benchmark():
    """Recompute random metrics from results/lofo_benchmark_multi_seed.csv directly from raw_scores.parquet."""
    raw_path = Path("results/raw_scores/raw_scores.parquet")
    bench_csv = Path("results/lofo_benchmark_multi_seed.csv")
    assert raw_path.exists(), f"Missing {raw_path}"
    assert bench_csv.exists(), f"Missing {bench_csv}"

    df_raw = pd.read_parquet(raw_path)
    df_bench = pd.read_csv(bench_csv)

    # Recompute composites from component scores
    df_raw["mean_anomaly"] = ((df_raw["iforest"] + df_raw["autoencoder"]) / 2.0).astype(np.float32)
    df_raw["gated_boost"] = (df_raw["autoencoder"] + 0.2 * (df_raw["supervised"] > 0.5)).astype(np.float32)

    df_raw["rank_average"] = 0.0
    df_raw["anomaly_heavy"] = 0.0
    for (fold, prev, seed), group in df_raw.groupby(["fold", "prevalence", "seed"]):
        r_xgb = group["supervised"].rank(pct=True).to_numpy(dtype=np.float32)
        r_anom = group["mean_anomaly"].rank(pct=True).to_numpy(dtype=np.float32)
        df_raw.loc[group.index, "rank_average"] = (0.5 * r_xgb + 0.5 * r_anom).astype(np.float32)
        df_raw.loc[group.index, "anomaly_heavy"] = (0.2 * r_xgb + 0.8 * r_anom).astype(np.float32)

    col_map = {
        "Supervised_XGBoost": "supervised",
        "Isolation_Forest": "iforest",
        "Autoencoder": "autoencoder",
        "Mean_Anomaly": "mean_anomaly",
        "Baseline_Rank_Average_0.5_0.5": "rank_average",
        "Baseline_Anomaly_Heavy_0.2_0.8": "anomaly_heavy",
        "Ablation_Gated_Boost_AE_plus_XGB": "gated_boost",
    }
    evaluable = df_bench[
        (df_bench["Method"].isin(col_map.keys())) &
        (df_bench["Family"] != "BruteForce_WebAttack_Merged")
    ].copy()
    assert len(evaluable) >= 10

    # Ensure Ablation_Gated_Boost_AE_plus_XGB is explicitly sampled
    gated_rows = evaluable[evaluable["Method"] == "Ablation_Gated_Boost_AE_plus_XGB"]
    assert len(gated_rows) > 0, "Ablation_Gated_Boost_AE_plus_XGB not found in benchmark table"

    sample_rows = evaluable.sample(n=10, random_state=42)
    if "Ablation_Gated_Boost_AE_plus_XGB" not in sample_rows["Method"].values:
        sample_rows = pd.concat([sample_rows.iloc[:-1], gated_rows.iloc[:1]])

    for idx, row in sample_rows.iterrows():
        fam = row["Family"]
        prev_str = row["Prevalence"]
        prev_val = 0.01 if "1" in prev_str else 0.05
        method = row["Method"]
        score_col = col_map[method]

        fold_str = f"LOFO_{fam}"
        sub_raw = df_raw[(df_raw["fold"] == fold_str) & (np.isclose(df_raw["prevalence"], prev_val))]
        assert len(sub_raw) > 0, f"No raw scores for fold={fold_str}, prev={prev_val}"

        seed_roc = []
        seed_pr = []
        seed_rec1 = []
        seed_rec01 = []
        seed_fa90 = []
        seed_fa50 = []

        for seed, seed_df in sub_raw.groupby("seed"):
            y = seed_df["is_attack"].to_numpy().astype(int)
            s = seed_df[score_col].to_numpy()
            seed_roc.append(roc_auc_score(y, s))
            seed_pr.append(average_precision_score(y, s))

            seed_rec1.append(calc_empirical_recall_at_far(y, s, 0.01))
            seed_rec01.append(calc_empirical_recall_at_far(y, s, 0.001))

            neg_s = s[y == 0]
            pos_s = s[y == 1]
            t90 = float(np.percentile(pos_s, 10.0))
            t50 = float(np.percentile(pos_s, 50.0))
            seed_fa90.append(float(np.mean(neg_s >= t90) * 10000.0))
            seed_fa50.append(float(np.mean(neg_s >= t50) * 10000.0))

        recomputed_roc_mean = float(np.mean(seed_roc))
        recomputed_pr_mean = float(np.mean(seed_pr))
        recomputed_rec1_mean = float(np.mean(seed_rec1)) * 100.0
        recomputed_rec01_mean = float(np.mean(seed_rec01)) * 100.0
        recomputed_fa90_mean = float(np.mean(seed_fa90))
        recomputed_fa50_mean = float(np.mean(seed_fa50))

        reported_roc = parse_reported_mean(row["ROC_AUC"])
        reported_pr = parse_reported_mean(row["PR_AUC"])
        reported_rec1 = parse_reported_mean(row["Recall@1%FAR"])
        reported_rec01 = parse_reported_mean(row["Recall@0.1%FAR"])
        reported_fa90 = parse_reported_mean(row["FA@90% Recall (per 10k)"])
        reported_fa50 = parse_reported_mean(row["FA@50% Recall (per 10k)"])

        assert abs(round(recomputed_roc_mean, 4) - round(reported_roc, 4)) <= 1e-4, (
            f"ROC-AUC mismatch for {fam} {prev_str} {method}: {recomputed_roc_mean} vs {reported_roc}"
        )
        assert abs(round(recomputed_pr_mean, 4) - round(reported_pr, 4)) <= 1e-4, (
            f"PR-AUC mismatch for {fam} {prev_str} {method}: {recomputed_pr_mean} vs {reported_pr}"
        )
        assert abs(round(recomputed_rec1_mean, 2) - round(reported_rec1, 2)) <= 1e-2, (
            f"Recall@1%FAR mismatch for {fam} {prev_str} {method}: {recomputed_rec1_mean} vs {reported_rec1}"
        )
        assert abs(round(recomputed_rec01_mean, 2) - round(reported_rec01, 2)) <= 1e-2, (
            f"Recall@0.1%FAR mismatch for {fam} {prev_str} {method}: {recomputed_rec01_mean} vs {reported_rec01}"
        )
        assert abs(round(recomputed_fa90_mean, 1) - round(reported_fa90, 1)) <= 0.2, (
            f"FA@90% mismatch for {fam} {prev_str} {method}: {recomputed_fa90_mean} vs {reported_fa90}"
        )
        assert abs(round(recomputed_fa50_mean, 1) - round(reported_fa50, 1)) <= 0.2, (
            f"FA@50% mismatch for {fam} {prev_str} {method}: {recomputed_fa50_mean} vs {reported_fa50}"
        )


def test_family_seen_control_consistency():
    """Verify Family_Seen_Control rows in lofo_benchmark_multi_seed match empirical summary."""
    bench_csv = Path("results/lofo_benchmark_multi_seed.csv")
    ctrl_summary_csv = Path("results/family_seen_control_summary.csv")
    assert bench_csv.exists(), f"Missing {bench_csv}"
    assert ctrl_summary_csv.exists(), f"Missing {ctrl_summary_csv}"

    df_bench = pd.read_csv(bench_csv)
    df_ctrl = pd.read_csv(ctrl_summary_csv)

    bench_ctrl = df_bench[df_bench["Method"] == "Family_Seen_Control"]
    assert len(bench_ctrl) == 10, f"Expected 10 Family_Seen_Control rows (5 folds x 2 prev), found {len(bench_ctrl)}"

    for _, c_row in df_ctrl.iterrows():
        match = bench_ctrl[
            (bench_ctrl["Family"] == c_row["Family"]) &
            (bench_ctrl["Prevalence"] == c_row["Prevalence"])
        ]
        assert len(match) == 1, f"Missing Family_Seen_Control match for {c_row['Family']} {c_row['Prevalence']}"
        b_row = match.iloc[0]
        assert b_row["ROC_AUC"] == c_row["ROC_AUC"]
        assert b_row["PR_AUC"] == c_row["PR_AUC"]
        assert b_row["Recall@1%FAR"] == c_row["Recall@1%FAR"]
        assert b_row["Recall@0.1%FAR"] == c_row["Recall@0.1%FAR"]


def test_merged_holdout_benchmark_consistency():
    """Verify BruteForce_WebAttack_Merged rows in lofo_benchmark_multi_seed match merged_holdout_summary.csv."""
    bench_csv = Path("results/lofo_benchmark_multi_seed.csv")
    merged_csv = Path("results/merged_holdout_summary.csv")
    assert bench_csv.exists(), f"Missing {bench_csv}"
    assert merged_csv.exists(), f"Missing {merged_csv}"

    df_bench = pd.read_csv(bench_csv)
    df_merged = pd.read_csv(merged_csv)

    bench_merged = df_bench[df_bench["Family"] == "BruteForce_WebAttack_Merged"]
    assert len(bench_merged) == len(df_merged)

    for _, m_row in df_merged.iterrows():
        match = bench_merged[
            (bench_merged["Prevalence"] == m_row["Prevalence"]) &
            (bench_merged["Method"] == m_row["Method"])
        ]
        assert len(match) == 1
        b = match.iloc[0]
        assert b["ROC_AUC"] == m_row["ROC_AUC"]
        assert b["PR_AUC"] == m_row["PR_AUC"]
        assert b["Recall@1%FAR"] == m_row["Recall@1%FAR"]


def test_recompute_ten_random_metrics_fusion_comparison():
    """Recompute 10 random differences from results/fusion_vs_single_comparison.csv directly using sklearn.metrics."""
    raw_path = Path("results/raw_scores/raw_scores.parquet")
    comp_csv = Path("results/fusion_vs_single_comparison.csv")
    assert raw_path.exists(), f"Missing {raw_path}"
    assert comp_csv.exists(), f"Missing {comp_csv}"

    df_raw = pd.read_parquet(raw_path)
    df_comp = pd.read_csv(comp_csv)

    # Recompute composites from component scores
    df_raw["mean_anomaly"] = ((df_raw["iforest"] + df_raw["autoencoder"]) / 2.0).astype(np.float32)
    df_raw["gated_boost"] = (df_raw["autoencoder"] + 0.2 * (df_raw["supervised"] > 0.5)).astype(np.float32)
    df_raw["rank_average"] = 0.0
    df_raw["anomaly_heavy"] = 0.0
    for (fold, prev, seed), group in df_raw.groupby(["fold", "prevalence", "seed"]):
        r_xgb = group["supervised"].rank(pct=True).to_numpy(dtype=np.float32)
        r_anom = group["mean_anomaly"].rank(pct=True).to_numpy(dtype=np.float32)
        df_raw.loc[group.index, "rank_average"] = (0.5 * r_xgb + 0.5 * r_anom).astype(np.float32)
        df_raw.loc[group.index, "anomaly_heavy"] = (0.2 * r_xgb + 0.8 * r_anom).astype(np.float32)

    col_map = {
        "Supervised_XGBoost": "supervised",
        "Fusion_XGB_Mean_Anomaly [Exploratory]": "fused_inner_lofo",
        "Fusion_XGB_IForest [Exploratory]": "fused_inner_iforest",
        "Fusion_XGB_AE [Exploratory]": "fused_inner_ae",
        "Baseline_Rank_Average_0.5_0.5": "rank_average",
        "Baseline_Anomaly_Heavy_0.2_0.8": "anomaly_heavy",
        "Ablation_Gated_Boost_AE_plus_XGB": "gated_boost",
    }
    evaluable = df_comp[df_comp["Method"].isin(col_map.keys())].copy()
    assert len(evaluable) >= 10

    sample_rows = evaluable.sample(n=10, random_state=101)

    for idx, row in sample_rows.iterrows():
        fam = row["Family"]
        prev_str = row["Prevalence"]
        prev_val = 0.01 if "1" in prev_str else 0.05
        method = row["Method"]
        score_col = col_map[method]

        fold_str = f"LOFO_{fam}"
        sub_raw = df_raw[(df_raw["fold"] == fold_str) & (np.isclose(df_raw["prevalence"], prev_val))]
        assert len(sub_raw) > 0, f"No raw scores for fold={fold_str}, prev={prev_val}"

        # Recompute PR-AUC and ROC-AUC differences vs Autoencoder using sklearn.metrics on pooled set
        y = sub_raw["is_attack"].to_numpy().astype(int)
        pr_m = float(average_precision_score(y, sub_raw[score_col].to_numpy()))
        pr_ae = float(average_precision_score(y, sub_raw["autoencoder"].to_numpy()))
        recomputed_delta_pr_ae = (pr_m - pr_ae) * 100.0

        roc_m = float(roc_auc_score(y, sub_raw[score_col].to_numpy()))
        roc_ae = float(roc_auc_score(y, sub_raw["autoencoder"].to_numpy()))
        recomputed_delta_roc_ae = (roc_m - roc_ae) * 100.0

        reported_delta_pr_ae = parse_reported_mean(row["Delta_PR_vs_AE_pp"])
        reported_delta_roc_ae = parse_reported_mean(row["Delta_ROC_vs_AE_pp"])

        diff_pr = abs(round(recomputed_delta_pr_ae, 2) - round(reported_delta_pr_ae, 2))
        diff_roc = abs(round(recomputed_delta_roc_ae, 2) - round(reported_delta_roc_ae, 2))

        assert diff_pr <= 1e-4, (
            f"Delta PR-AUC vs AE mismatch for {fam} {prev_str} {method}: "
            f"recomputed={recomputed_delta_pr_ae:.2f}, reported={reported_delta_pr_ae:.2f}, diff={diff_pr}"
        )
        assert diff_roc <= 1e-4, (
            f"Delta ROC-AUC vs AE mismatch for {fam} {prev_str} {method}: "
            f"recomputed={recomputed_delta_roc_ae:.2f}, reported={reported_delta_roc_ae:.2f}, diff={diff_roc}"
        )


def test_cross_dataset_table_consistency():
    """Verify results/cross_dataset_comparison.csv against data card, raw files, and leakage audits."""
    comp_csv = Path("results/cross_dataset_comparison.csv")
    comp_md = Path("results/cross_dataset_comparison.md")
    fusion_md = Path("results/fusion_vs_single_comparison.md")
    cic_leakage_csv = Path("results/leakage_audit.csv")
    unsw_leakage_csv = Path("results/unsw_nb15/leakage_audit.csv")

    assert comp_csv.exists(), f"Missing {comp_csv}"
    assert comp_md.exists(), f"Missing {comp_md}"
    assert fusion_md.exists(), f"Missing {fusion_md}"
    assert cic_leakage_csv.exists(), f"Missing {cic_leakage_csv}"
    assert unsw_leakage_csv.exists(), f"Missing {unsw_leakage_csv}"

    df = pd.read_csv(comp_csv)
    cic_row = df[df["dataset"] == "CIC-IDS2017"].iloc[0]
    unsw_row = df[df["dataset"] == "UNSW-NB15"].iloc[0]

    # 1. CIC-IDS2017 raw rows and duplication
    assert "2,830,743" in str(cic_row["raw rows"]), f"Expected 2,830,743 raw rows, got {cic_row['raw rows']}"
    assert "21.03%" in str(cic_row["duplication rate after raw load"]), f"Expected 21.03% dedup, got {cic_row['duplication rate after raw load']}"

    # 2. CIC-IDS2017 Leakage Audit consistency
    cic_leak = pd.read_csv(cic_leakage_csv)
    rand_3dec_mean = float(cic_leak["Rand_Near_Leakage_3dec_Pct"].mean())
    assert f"{rand_3dec_mean:.1f}%" in str(cic_row["random-split leakage (3-dec, log1p, NN)"])

    # 3. UNSW-NB15 raw rows and leakage consistency
    assert "257,673" in str(unsw_row["raw rows"])
    unsw_leak = pd.read_csv(unsw_leakage_csv)
    unsw_rand_3dec = float(unsw_leak["Rand_Near_Leakage_3dec_Pct"].mean())
    assert f"{unsw_rand_3dec:.2f}%" in str(unsw_row["random-split leakage (3-dec, log1p, NN)"])

    # 4. Gain statement matches fusion comparison
    fusion_text = fusion_md.read_text(encoding="utf-8")
    comp_md_text = comp_md.read_text(encoding="utf-8")

    m_gain_ci = re.search(r"(\+18\.\d+ pp \[-?\d+\.\d+, \+\d+\.\d+\])", fusion_text)
    assert m_gain_ci is not None, "Could not find gain CI in fusion_vs_single_comparison.md"
    gain_ci_str = m_gain_ci.group(1)

    assert gain_ci_str in str(cic_row["fusion gain vs best single with CI"]), (
        f"Gain CI '{gain_ci_str}' not found in cross_dataset_comparison.csv"
    )
    assert gain_ci_str in comp_md_text, (
        f"Gain CI '{gain_ci_str}' not found in cross_dataset_comparison.md"
    )

    # 5. Missing datasets clearly marked
    lycos_row = df[df["dataset"] == "LYCOS-IDS2017"].iloc[0]
    assert "not provided" in str(lycos_row["files used"]).lower()
    cic2018_row = df[df["dataset"] == "CSE-CIC-IDS2018"].iloc[0]
    assert "not provided" in str(cic2018_row["files used"]).lower()
