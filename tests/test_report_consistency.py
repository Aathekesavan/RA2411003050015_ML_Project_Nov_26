"""Rigorous Consistency and Traceability Verification Test for SentinelX-Shift.

Recomputes 10 random metrics per summary table directly from raw_scores.parquet
and fails if difference > 1e-6 (matching reported rounding precision).
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


from src.eval.generate_reports import fast_auc


def test_recompute_ten_random_metrics_lofo_benchmark():
    """Recompute 10 random metrics from results/lofo_benchmark_multi_seed.csv directly from raw_scores.parquet."""
    raw_path = Path("results/raw_scores/raw_scores.parquet")
    bench_csv = Path("results/lofo_benchmark_multi_seed.csv")
    assert raw_path.exists(), f"Missing {raw_path}"
    assert bench_csv.exists(), f"Missing {bench_csv}"

    df_raw = pd.read_parquet(raw_path)
    df_bench = pd.read_csv(bench_csv)

    # Recompute composites from component scores matching generate_reports.py
    df_raw["mean_anomaly"] = (df_raw["iforest"] + df_raw["autoencoder"]) / 2.0
    for (fold, prev, seed), group in df_raw.groupby(["fold", "prevalence", "seed"]):
        r_xgb = group["supervised"].rank(pct=True).to_numpy()
        r_anom = group["mean_anomaly"].rank(pct=True).to_numpy()
        df_raw.loc[group.index, "rank_average"] = 0.5 * r_xgb + 0.5 * r_anom
        df_raw.loc[group.index, "anomaly_heavy"] = 0.2 * r_xgb + 0.8 * r_anom

    col_map = {
        "Supervised_XGBoost": "supervised",
        "Isolation_Forest": "iforest",
        "Autoencoder": "autoencoder",
        "Mean_Anomaly": "mean_anomaly",
        "Baseline_Rank_Average_0.5_0.5": "rank_average",
        "Baseline_Anomaly_Heavy_0.2_0.8": "anomaly_heavy",
    }
    evaluable = df_bench[df_bench["Method"].isin(col_map.keys())].copy()
    assert len(evaluable) >= 10

    sample_rows = evaluable.sample(n=10, random_state=42)

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
        for seed, seed_df in sub_raw.groupby("seed"):
            y = seed_df["is_attack"].to_numpy().astype(int)
            s = seed_df[score_col].to_numpy()
            seed_roc.append(roc_auc_score(y, s))
            seed_pr.append(average_precision_score(y, s))

        recomputed_roc_mean = float(np.mean(seed_roc))
        recomputed_pr_mean = float(np.mean(seed_pr))

        reported_roc = parse_reported_mean(row["ROC_AUC"])
        reported_pr = parse_reported_mean(row["PR_AUC"])

        diff_roc = abs(round(recomputed_roc_mean, 4) - round(reported_roc, 4))
        diff_pr = abs(round(recomputed_pr_mean, 4) - round(reported_pr, 4))

        assert diff_roc <= 1e-6, (
            f"ROC-AUC mismatch for {fam} {prev_str} {method}: "
            f"recomputed={recomputed_roc_mean:.4f}, reported={reported_roc:.4f}, diff={diff_roc}"
        )
        assert diff_pr <= 1e-6, (
            f"PR-AUC mismatch for {fam} {prev_str} {method}: "
            f"recomputed={recomputed_pr_mean:.4f}, reported={reported_pr:.4f}, diff={diff_pr}"
        )


def test_recompute_ten_random_metrics_fusion_comparison():
    """Recompute 10 random differences from results/fusion_vs_single_comparison.csv directly from raw_scores.parquet."""
    raw_path = Path("results/raw_scores/raw_scores.parquet")
    comp_csv = Path("results/fusion_vs_single_comparison.csv")
    assert raw_path.exists(), f"Missing {raw_path}"
    assert comp_csv.exists(), f"Missing {comp_csv}"

    df_raw = pd.read_parquet(raw_path)
    df_comp = pd.read_csv(comp_csv)

    # Recompute composites from component scores matching generate_reports.py
    df_raw["mean_anomaly"] = (df_raw["iforest"] + df_raw["autoencoder"]) / 2.0
    for (fold, prev, seed), group in df_raw.groupby(["fold", "prevalence", "seed"]):
        r_xgb = group["supervised"].rank(pct=True).to_numpy()
        r_anom = group["mean_anomaly"].rank(pct=True).to_numpy()
        df_raw.loc[group.index, "rank_average"] = 0.5 * r_xgb + 0.5 * r_anom
        df_raw.loc[group.index, "anomaly_heavy"] = 0.2 * r_xgb + 0.8 * r_anom

    col_map = {
        "Supervised_XGBoost": "supervised",
        "Fusion_XGB_Mean_Anomaly [Exploratory]": "fused_inner_lofo",
        "Fusion_XGB_IForest [Exploratory]": "fused_inner_iforest",
        "Fusion_XGB_AE [Exploratory]": "fused_inner_ae",
        "Baseline_Rank_Average_0.5_0.5": "rank_average",
        "Baseline_Anomaly_Heavy_0.2_0.8": "anomaly_heavy",
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

        # Recompute PR-AUC difference vs Autoencoder using fast_auc on pooled set
        y = sub_raw["is_attack"].to_numpy().astype(int)
        _, pr_m = fast_auc(y, sub_raw[score_col].to_numpy())
        _, pr_ae = fast_auc(y, sub_raw["autoencoder"].to_numpy())
        recomputed_delta_ae = (pr_m - pr_ae) * 100.0

        reported_delta_ae = parse_reported_mean(row["Delta_PR_vs_AE_pp"])

        diff = abs(round(recomputed_delta_ae, 2) - round(reported_delta_ae, 2))
        assert diff <= 1e-6, (
            f"Delta PR-AUC vs AE mismatch for {fam} {prev_str} {method}: "
            f"recomputed={recomputed_delta_ae:.2f}, reported={reported_delta_ae:.2f}, diff={diff}"
        )
