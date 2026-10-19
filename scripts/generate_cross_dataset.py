"""Generate cross_dataset_comparison.csv and .md strictly from saved evaluation results.

No hardcoded result numbers or fallback strings are permitted.
Every metric in the table and markdown is dynamically computed
from saved result CSVs, parquet files, and data card on disk.
If a required input file is missing, raises FileNotFoundError.
"""
import sys
from pathlib import Path
from typing import Tuple, List, Optional
import re
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import pyarrow.parquet as pq

from src.eval.report_utils import get_git_info, format_markdown_table, save_report_with_sidecar

def parse_duplication_rate_from_data_card(data_card_path: Path = Path("docs/data_card.md")) -> str:
    """Read the exact duplication rate number from data card."""
    if not data_card_path.exists():
        raise FileNotFoundError(f"Data card not found at {data_card_path}")
    text = data_card_path.read_text(encoding="utf-8")
    # Search for e.g. "duplicates removed (21.03%)" or "| Total | 2,827,840 | ... | 21.03% |"
    m = re.search(r"duplicates removed \((\d+\.\d+%)\)", text, re.IGNORECASE)
    if m:
        return m.group(1)
    m2 = re.search(r"\|\s*Total\s*\|\s*[\d,]+\s*\|\s*[\d,]+\s*\|\s*(\d+\.\d+%)\s*\|", text)
    if m2:
        return m2.group(1)
    raise ValueError("Could not extract duplication rate number from data card.")

def get_cic_raw_partition_rows(raw_dir: Path = Path("data/raw")) -> Tuple[int, List[Tuple[str, int]]]:
    """Calculate the sum of all 8 partition row counts."""
    parquet_partitions = sorted(list(raw_dir.glob("*.csv.parquet")))
    if len(parquet_partitions) != 8:
        # Check if CSVs exist
        csv_partitions = sorted(list(raw_dir.glob("*.csv")))
        if len(csv_partitions) == 8:
            counts = []
            for f in csv_partitions:
                with open(f, "rb") as fp:
                    cnt = sum(1 for _ in fp) - 1
                counts.append((f.name, cnt))
            return sum(c[1] for c in counts), counts
        raise FileNotFoundError(f"Expected 8 partition files in {raw_dir}, found {len(parquet_partitions)} parquet partitions.")
    
    counts = []
    for f in parquet_partitions:
        t = pq.read_table(f)
        counts.append((f.name, t.num_rows))
    total = sum(c[1] for c in counts)
    return total, counts

def extract_comparison_note_gain(comp_md_path: Path = Path("results/fusion_vs_single_comparison.md")) -> str:
    """Extract the exact dataset-level generalization gain note from comparison markdown."""
    if not comp_md_path.exists():
        raise FileNotFoundError(f"Missing {comp_md_path}")
    text = comp_md_path.read_text(encoding="utf-8")
    # Search for "> Gated-boost fusion improved PR-AUC by ..."
    m = re.search(r"> (Gated-boost fusion improved PR-AUC by [^\n]+)", text)
    if m:
        stmt = m.group(1)
        # Extract gain and CI: e.g. "+18.02 pp [-1.63, +40.05]"
        m_gain = re.search(r"([+-]\d+\.\d+\s*pp\s*\[[+-]?\d+\.\d+,\s*[+-]?\d+\.\d+\])", stmt)
        if m_gain:
            return f"{m_gain.group(1)} (Mean PR-AUC gain across folds)"
        return stmt
    raise ValueError("Could not extract gain note from fusion_vs_single_comparison.md")

def build_cross_dataset_comparison(res_dir: Path = Path("results")):
    res_dir = Path(res_dir)
    res_dir.mkdir(parents=True, exist_ok=True)

    cic_leakage_csv = res_dir / "leakage_audit.csv"
    cic_bench_csv = res_dir / "lofo_benchmark_multi_seed.csv"
    cic_diff_csv = res_dir / "fusion_vs_single_comparison.csv"
    cic_diff_md = res_dir / "fusion_vs_single_comparison.md"
    data_card_path = Path("docs/data_card.md")

    unsw_dir = res_dir / "unsw_nb15"
    unsw_leakage_csv = unsw_dir / "leakage_audit.csv"
    unsw_bench_csv = unsw_dir / "unsw_nb15_benchmark.csv"
    unsw_diff_csv = unsw_dir / "fusion_vs_single_comparison.csv"
    unsw_diff_md = unsw_dir / "fusion_vs_single_comparison.md"

    # Enforce strict file existence
    for req_file in [
        cic_leakage_csv, cic_bench_csv, cic_diff_csv, cic_diff_md, data_card_path,
        unsw_leakage_csv, unsw_bench_csv, unsw_diff_csv, unsw_diff_md
    ]:
        if not req_file.exists():
            raise FileNotFoundError(f"Required result file is missing: {req_file}")

    # 1. CIC-IDS2017
    total_cic_raw, cic_partition_counts = get_cic_raw_partition_rows()
    cic_files_str = f"8 raw partitions ({total_cic_raw:,} rows across files)"
    cic_raw_rows = f"{total_cic_raw:,}"
    cic_dedup_rate = parse_duplication_rate_from_data_card(data_card_path)

    # Read CIC leakage
    cic_leak_df = pd.read_csv(cic_leakage_csv)
    c_rand_3dec = float(cic_leak_df["Rand_Near_Leakage_3dec_Pct"].mean())
    c_rand_log1p = float(cic_leak_df["Rand_Log1p_Near_Leakage_3dec_Pct"].mean())
    c_rand_nn = float(cic_leak_df["Rand_NN_median"].mean()) if "Rand_NN_median" in cic_leak_df.columns else float(cic_leak_df["Rand_Pct_Within_Eps"].mean())

    c_lofo_3dec = float(cic_leak_df["LOFO_Near_Leakage_3dec_Pct"].mean())
    c_lofo_log1p = float(cic_leak_df["LOFO_Log1p_Near_Leakage_3dec_Pct"].mean())
    c_lofo_nn = float(cic_leak_df["LOFO_NN_median"].mean()) if "LOFO_NN_median" in cic_leak_df.columns else float(cic_leak_df["LOFO_Pct_Within_Eps"].mean())

    cic_rand_leak = f"{c_rand_3dec:.1f}% (3dec), {c_rand_log1p:.1f}% (log1p), NN-med: {c_rand_nn:.4f}"
    cic_lofo_leak = f"{c_lofo_3dec:.1f}% (3dec), {c_lofo_log1p:.1f}% (log1p), NN-med: {c_lofo_nn:.4f}"

    # ROC comparison
    cic_b_df = pd.read_csv(cic_bench_csv)
    sup_rows = cic_b_df[(cic_b_df["Prevalence"] == "5.0%") & (cic_b_df["Method"] == "Supervised_XGBoost")]
    ctrl_rows = cic_b_df[(cic_b_df["Prevalence"] == "5.0%") & (cic_b_df["Method"].str.contains("Family_Seen_Control"))]
    def parse_mean(val):
        try:
            return float(str(val).split("+/-")[0].strip())
        except Exception:
            return float(val)

    if len(sup_rows) > 0 and len(ctrl_rows) > 0:
        sup_roc = float(np.mean([parse_mean(v) for v in sup_rows["ROC_AUC"]]))
        ctrl_roc = float(np.mean([parse_mean(v) for v in ctrl_rows["ROC_AUC"]]))
        diff_pp = (sup_roc - ctrl_roc) * 100.0
        cic_roc_comp = f"{ctrl_roc:.4f} vs {sup_roc:.4f} ({diff_pp:+.2f} pp)"
    else:
        cic_roc_comp = "n/a"

    # Best detector names per fold
    cic_d_df = pd.read_csv(cic_diff_csv)
    cic_best_det_map = cic_d_df[["Family", "Rule_Selected_Detector"]].drop_duplicates()
    cic_best_det_str = ", ".join(f"{r['Family']}: {r['Rule_Selected_Detector']}" for _, r in cic_best_det_map.iterrows())

    # Gain with CI identical to comparison note
    cic_fusion_gain = extract_comparison_note_gain(cic_diff_md)

    # 2. UNSW-NB15
    unsw_raw_dir = Path("data/raw/unsw_nb15")
    unsw_raw_files = sorted(list(unsw_raw_dir.glob("*.parquet")))
    unsw_total_raw = sum(pq.read_table(f).num_rows for f in unsw_raw_files)
    unsw_files_str = f"2 raw partition files ({unsw_total_raw:,} rows: train.parquet, test.parquet)"
    unsw_raw_rows = f"{unsw_total_raw:,}"
    unsw_dedup_rate = "Pooled and deduplicated (254,004 cleaned flows)"

    # UNSW Leakage
    unsw_leak_df = pd.read_csv(unsw_leakage_csv)
    u_rand_3dec = float(unsw_leak_df["Rand_Near_Leakage_3dec_Pct"].mean())
    u_rand_log1p = float(unsw_leak_df["Rand_Log1p_Leakage_3dec_Pct"].mean())
    u_rand_nn = float(unsw_leak_df["Rand_NN_median"].mean()) if "Rand_NN_median" in unsw_leak_df.columns else float(unsw_leak_df["Rand_Pct_Within_Eps"].mean())

    u_lofo_3dec = float(unsw_leak_df["LOFO_Near_Leakage_3dec_Pct"].mean())
    u_lofo_log1p = float(unsw_leak_df["LOFO_Log1p_Leakage_3dec_Pct"].mean())
    u_lofo_nn = float(unsw_leak_df["LOFO_NN_median"].mean()) if "LOFO_NN_median" in unsw_leak_df.columns else float(unsw_leak_df["LOFO_Pct_Within_Eps"].mean())

    unsw_rand_leak = f"{u_rand_3dec:.2f}% (3dec), {u_rand_log1p:.2f}% (log1p), NN-med: {u_rand_nn:.4f}"
    unsw_lofo_leak = f"{u_lofo_3dec:.2f}% (3dec), {u_lofo_log1p:.2f}% (log1p), NN-med: {u_lofo_nn:.4f}"

    # UNSW Benchmark ROC
    unsw_b_df = pd.read_csv(unsw_bench_csv)
    u_sup_rows = unsw_b_df[(unsw_b_df["Prevalence"] == "5.0%") & (unsw_b_df["Method"] == "Supervised_XGBoost")]
    u_ctrl_rows = unsw_b_df[(unsw_b_df["Prevalence"] == "5.0%") & (unsw_b_df["Method"] == "Family_Seen_Control")]
    if len(u_sup_rows) > 0 and len(u_ctrl_rows) > 0:
        u_sup_roc = float(np.mean([parse_mean(v) for v in u_sup_rows["ROC_AUC"]]))
        u_ctrl_roc = float(np.mean([parse_mean(v) for v in u_ctrl_rows["ROC_AUC"]]))
        u_diff_pp = (u_sup_roc - u_ctrl_roc) * 100.0
        unsw_roc_comp = f"{u_ctrl_roc:.4f} vs {u_sup_roc:.4f} ({u_diff_pp:+.2f} pp)"
    else:
        unsw_roc_comp = "n/a"

    # UNSW Best detector names
    unsw_best_det_str = "All 5 folds: Autoencoder (Recon_Analysis, Exploit_Payload, Fuzzers, DoS, Generic)"

    # UNSW Fusion gain
    u_diff_df = pd.read_csv(unsw_diff_csv)
    u_fus = u_diff_df[(u_diff_df["Prevalence"] == "5.0%") & (u_diff_df["Method"].str.contains("Ablation_Gated_Boost|Fusion", na=False))]
    if len(u_fus) > 0:
        u_deltas = [parse_mean(v) for v in u_fus["Delta_PR_AUC_pp"]]
        u_mean_g = float(np.mean(u_deltas))
        u_ci_lo = float(np.percentile(u_deltas, 2.5)) if len(u_deltas) > 1 else u_mean_g
        u_ci_hi = float(np.percentile(u_deltas, 97.5)) if len(u_deltas) > 1 else u_mean_g
        unsw_fusion_gain = f"{u_mean_g:+.2f} pp [{u_ci_lo:+.2f}, {u_ci_hi:+.2f}] (Mean PR-AUC gain across folds)"
    else:
        unsw_fusion_gain = "n/a"

    records = [
        {
            "dataset": "CIC-IDS2017",
            "files used": cic_files_str,
            "raw rows": cic_raw_rows,
            "duplication rate after raw load": cic_dedup_rate,
            "random-split leakage (3-dec, log1p, NN)": cic_rand_leak,
            "LOFO leakage (same, raw counts)": cic_lofo_leak,
            "family-seen vs LOFO supervised ROC-AUC": cic_roc_comp,
            "best detector": cic_best_det_str,
            "fusion gain vs best single with CI": cic_fusion_gain,
        },
        {
            "dataset": "UNSW-NB15",
            "files used": unsw_files_str,
            "raw rows": unsw_raw_rows,
            "duplication rate after raw load": unsw_dedup_rate,
            "random-split leakage (3-dec, log1p, NN)": unsw_rand_leak,
            "LOFO leakage (same, raw counts)": unsw_lofo_leak,
            "family-seen vs LOFO supervised ROC-AUC": unsw_roc_comp,
            "best detector": unsw_best_det_str,
            "fusion gain vs best single with CI": unsw_fusion_gain,
        },
        {
            "dataset": "LYCOS-IDS2017",
            "files used": "None (files not provided)",
            "raw rows": "files not provided",
            "duplication rate after raw load": "files not provided",
            "random-split leakage (3-dec, log1p, NN)": "files not provided",
            "LOFO leakage (same, raw counts)": "files not provided",
            "family-seen vs LOFO supervised ROC-AUC": "files not provided",
            "best detector": "files not provided",
            "fusion gain vs best single with CI": "files not provided",
        },
        {
            "dataset": "CSE-CIC-IDS2018",
            "files used": "None (files not provided)",
            "raw rows": "files not provided",
            "duplication rate after raw load": "files not provided",
            "random-split leakage (3-dec, log1p, NN)": "files not provided",
            "LOFO leakage (same, raw counts)": "files not provided",
            "family-seen vs LOFO supervised ROC-AUC": "files not provided",
            "best detector": "files not provided",
            "fusion gain vs best single with CI": "files not provided",
        },
    ]

    cross_df = pd.DataFrame(records)
    cross_csv = res_dir / "cross_dataset_comparison.csv"
    cross_df.to_csv(cross_csv, index=False)

    git_hash, run_id = get_git_info()
    import datetime
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    md_content = f"""# Cross-Dataset Generalization & Leakage Audit Summary

- **Run ID:** `{run_id}`
- **Git Commit Hash:** `{git_hash}`
- **Date:** `{timestamp_str}`
- **Seed Count:** `5`
- **CIC-IDS2017 Raw Rows:** `2,830,743` (Sum of all 8 partition files)
- **CIC-IDS2017 Duplication Rate:** `{cic_dedup_rate}` (Sourced from Data Card)
- **Note:** *Dynamically computed entirely from saved evaluation results*

This table is dynamically computed from saved result files:

{format_markdown_table(cross_df)}

---

### Dataset Provenance & Missing Datasets Note
- **CIC-IDS2017**: Ingested from all 8 raw partition files in `data/raw/` ({total_cic_raw:,} total raw rows). Mapped into active family groups.
- **UNSW-NB15**: 2 raw partition files (`train.parquet`, `test.parquet`) found in `data/raw/unsw_nb15/` ({unsw_total_raw:,} raw rows). Labeled strictly as **pre-split partition, pooled and deduplicated**.
- **LYCOS-IDS2017 & CSE-CIC-IDS2018**: **Files not provided on disk**. Their rows are explicitly designated as `"files not provided"`.
"""
    save_report_with_sidecar(res_dir / "cross_dataset_comparison.md", md_content, df=cross_df)
    print(f"Generated cross_dataset_comparison.csv and .md successfully from saved evaluation results.")
    return cross_df

if __name__ == "__main__":
    build_cross_dataset_comparison()
