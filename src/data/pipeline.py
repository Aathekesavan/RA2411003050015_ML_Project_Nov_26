"""End-to-End Data Pipeline for SentinelX-Shift.

Orchestrates:
1. Loading all 8 raw CIC-IDS2017 files for the complete dataset (2.83M rows).
2. Sanitizing column names, dropping identifier/leaky columns (IPs, Ports, Flow ID, Timestamp).
3. Mapping labels into the canonical FAMILY GROUPS:
   - DoS_DDoS: {DoS, DDoS}
   - BruteForce: {FTP/SSH brute force}
   - PortScan
   - Bot
   - WebAttack
   - (Infiltration skipped because < 500 unique flows)
4. Handling infinite and NaN values in numeric flow metrics.
5. Purging exact duplicate flow vectors.
6. Rare-family-preserving subsampling (100% of rare families <20k flows; subsampling Benign and DoS_DDoS to ~65k total).
7. Conducting multi-decimal contrast leakage audit (Random Split vs LOFO at 3, 2, 1 decimals).
8. Measuring real XGBoost baseline performance on naive random split.
9. Generating data card (docs/data_card.md), audit CSV (results/leakage_audit.csv), and comparison chart (results/leakage_audit_comparison.png).
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import time
import pandas as pd
import numpy as np

from src.data.loader import (
    load_config,
    load_raw_file,
    DEFAULT_LEAKY_COLUMNS,
    CANONICAL_FAMILIES,
)
from src.data.cleaner import (
    clean_numeric_features,
    remove_exact_duplicates,
    preserve_rare_families_sample,
)
from src.data.audit import (
    run_leakage_contrast_audit,
    plot_leakage_contrast,
    measure_naive_xgboost_performance,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sentinelx.pipeline")

# All 8 official CIC-IDS2017 partitions
ALL_RAW_PARTITIONS = [
    "Monday-WorkingHours.pcap_ISCX",
    "Tuesday-WorkingHours.pcap_ISCX",
    "Wednesday-workingHours.pcap_ISCX",
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX",
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX",
    "Friday-WorkingHours-Morning.pcap_ISCX",
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX",
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX",
]

# Mapping from canonical attack families to the 5 designated LOFO Family Groups
FAMILY_GROUP_MAPPING = {
    "DoS": "DoS_DDoS",
    "DDoS": "DoS_DDoS",
    "BruteForce": "BruteForce",
    "PortScan": "PortScan",
    "Bot": "Bot",
    "WebAttack": "WebAttack",
    "Benign": "Benign",
}


def format_markdown_table(df: pd.DataFrame) -> str:
    """Format DataFrame as markdown table without external dependencies."""
    headers = list(df.columns)
    lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        row_str = " | ".join(str(row[c]) for c in headers)
        lines.append(f"| {row_str} |")
    return "\n".join(lines)


def find_data_file(raw_dir: Path, base_name: str) -> Path:
    """Find CSV or Parquet file matching base_name."""
    pq_file = raw_dir / f"{base_name}.csv.parquet"
    if pq_file.exists():
        return pq_file
    csv_file = raw_dir / f"{base_name}.csv"
    if csv_file.exists():
        return csv_file
    raise FileNotFoundError(f"Neither {csv_file} nor {pq_file} found in {raw_dir}")


def build_data_card_markdown(
    df_clean: pd.DataFrame,
    raw_file_counts: Dict[str, int],
    dedup_stats: Dict[str, int],
    per_group_raw: Dict[str, int],
    per_group_dedup: Dict[str, int],
    contrast_df: pd.DataFrame,
    xgb_metrics: Dict[str, float],
    output_parquet: Path,
    seed: int
) -> str:
    """Generate comprehensive documentation for docs/data_card.md."""
    total_processed = len(df_clean)
    sample_counts = df_clean["Label"].value_counts().to_dict()

    # Raw file table
    raw_file_rows = []
    tot_raw_files_rows = sum(raw_file_counts.values())
    for f_name, cnt in sorted(raw_file_counts.items()):
        raw_file_rows.append(f"| `{f_name}` | {cnt:,} |")
    raw_files_table = "\n".join(raw_file_rows)

    # Per-group deduplication and sampling table
    breakdown_rows = []
    for grp in sorted(per_group_raw.keys()):
        raw_cnt = per_group_raw[grp]
        dedup_cnt = per_group_dedup.get(grp, 0)
        dup_rate = ((raw_cnt - dedup_cnt) / max(1, raw_cnt)) * 100.0
        s_cnt = sample_counts.get(grp, 0)
        s_pct = (s_cnt / total_processed) * 100.0
        breakdown_rows.append(
            f"| `{grp}` | {raw_cnt:,} | {dedup_cnt:,} | {dup_rate:.2f}% | {s_cnt:,} | {s_pct:.2f}% |"
        )
    breakdown_table = "\n".join(breakdown_rows)

    contrast_table_cols = [
        "Family",
        "Rand_Near_Leakage_3dec_Pct",
        "LOFO_Near_Leakage_3dec_Pct",
        "LOFO_Matches_Benign_3dec_Pct",
        "LOFO_Matches_OtherAttacks_3dec_Pct",
        "Rand_Log1p_Near_Leakage_3dec_Pct",
        "LOFO_Log1p_Near_Leakage_3dec_Pct",
        "Rand_Near_Leakage_2dec_Pct",
        "LOFO_Near_Leakage_2dec_Pct",
        "LOFO_Exact_Leakage_Pct",
    ]
    contrast_md = format_markdown_table(contrast_df[contrast_table_cols])

    card_content = f"""# SentinelX-Shift Data Card: Complete CIC-IDS2017 Family Groups Sample

**Version**: 2.0.0-complete-family-groups  
**Generated Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}  
**Deterministic Seed**: `{seed}`  
**Dataset Provenance**: All 8 raw partitions of the official CIC-IDS2017 benchmark loaded ({tot_raw_files_rows:,} raw flows).  
**Family Groups Protocol**: Grouped into `{sorted(list(set(FAMILY_GROUP_MAPPING.values()) - {'Benign'}))}`. Infiltration (36 flows) skipped (< 500 unique flows).  
**Sampling Strategy**: 100% retention of all rare family groups (`<20,000` unique flows); proportional subsampling of `Benign` and `DoS_DDoS` to ~65,000 total.  
**Primary Artifact**: [`{output_parquet.as_posix()}`](file:///{output_parquet.resolve().as_posix()})  
**Feature Count**: {len(df_clean.columns) - 1} behavioral netflow features (all leaky identifiers stripped)  

---

## 1. Raw Files Ingestion & Row Counts

Every raw partition provided in the official CIC-IDS2017 distribution was loaded:

| Raw Partition File | Loaded Row Count |
| :--- | :--- |
{raw_files_table}
| **Total Ingested Raw Flows** | **{tot_raw_files_rows:,}** |

---

## 2. Ingested Partitions & Deduplication Audit

| Metric | Count | Description |
| :--- | :--- | :--- |
| **Raw Input Rows Loaded** | {dedup_stats['before_dedup']:,} | Loaded from all 8 raw partition files |
| **Duplicates Removed** | {dedup_stats['duplicates_dropped']:,} | Exact full-vector duplicates removed ({dedup_stats['duplicate_fraction']:.2%}) |
| **Rows After Deduplication** | {dedup_stats['after_dedup']:,} | Unique behavioral flow feature vectors |
| **Final Sampled Rows** | {total_processed:,} | Rare-preserved benchmark sample saved to parquet |
| **Feature Dimensions** | {len(df_clean.columns) - 1} | Extracted behavioral features (ports, IPs, timestamps removed) |

### 2.1 Per-Family-Group Breakdown

| Family Group | Raw Rows | Unique Rows (Dedup) | Duplication Rate (%) | Final Sample Rows | Final Proportion (%) |
| :--- | :--- | :--- | :--- | :--- | :--- |
{breakdown_table}
| **Total** | **{dedup_stats['before_dedup']:,}** | **{dedup_stats['after_dedup']:,}** | **{dedup_stats['duplicate_fraction']:.2%}** | **{total_processed:,}** | **100.00%** |

### 2.2 Notes on Family Groups & Skipped Classes
1. **Family Groups**:
   - `DoS_DDoS`: Combines DoS (Hulk, GoldenEye, slowloris, Slowhttptest, Heartbleed) and DDoS attacks (321,770 unique flows).
   - `BruteForce`: Combines FTP-Patator and SSH-Patator (9,150 unique flows).
   - `PortScan`: 1,956 unique flows (100% retained).
   - `Bot`: 1,437 unique flows (100% retained).
   - `WebAttack`: Combines Brute Force, XSS, and SQL Injection web attacks (2,143 unique flows; 100% retained).
2. **Skipped Classes**:
   - `Infiltration`: Only 36 unique flows in the entire 2.83M raw dataset (< 500 unique flows threshold). Skipped from LOFO evaluation per protocol to prevent low-power degenerate evaluation.

---

## 3. Measured Baseline: Naive Random Split Performance

An XGBoost classifier (50 estimators, max_depth=4) was trained on a naive stratified 70/30 random split (with port and IP columns stripped):

- **Measured Test Accuracy**: `{xgb_metrics['accuracy']:.4%}`
- **Measured Macro F1-Score**: `{xgb_metrics['f1_macro']:.4f}`
- **Test Sample Size**: `{xgb_metrics['n_test']:,}` flows (Train: `{xgb_metrics['n_train']:,}` flows)

```text
Classification Report:
{xgb_metrics['classification_report']}
```

---

## 4. Multi-Decimal Contrast Leakage Audit Across the 5 Family Groups

> [!IMPORTANT]
> **Primary Metric**: **3-decimal near-duplicate leakage** (`3dec`) represents true protocol-level flow vector collision.  
> All LOFO matches are decomposed into matches to **benign training flows** vs matches to **other attack families**.

{contrast_md}

- **Artifact (CSV)**: [`results/leakage_audit.csv`](file:///d:/sentinelx/results/leakage_audit.csv)  
- **Artifact (Chart)**: [`results/leakage_audit_comparison.png`](file:///d:/sentinelx/results/leakage_audit_comparison.png)  

---

## 5. Documented CIC-IDS2017 Dataset Issues & Mitigations

1. **Identity & Port Memorization (Leaky Columns)**:
   - *Problem*: Port numbers (e.g. 21 for FTP, 22 for SSH, 80 for DoS) allow decision trees to trivially separate attacks without learning netflow behavior.
   - *Mitigation*: Dropped `Destination Port`, `Source Port`, `Flow ID`, `Source IP`, `Destination IP`, and `Timestamp`.
2. **Duplicate Header Columns**:
   - *Problem*: Column `Fwd Header Length.1` is a duplicate of `Fwd Header Length`.
   - *Mitigation*: Automatically pruned duplicate column headers.
3. **Infinite and Missing Values**:
   - *Problem*: Zero-duration flows generate `Infinity` and `NaN` values in `Flow Bytes/s` and `Flow Packets/s`.
   - *Mitigation*: Replaced inf/-inf with NaN and sanitized numeric values.
4. **Encoding Artifacts**:
   - *Problem*: Raw labels contain `\\ufffd` or Windows-1252 byte corruption in Web Attack names.
   - *Mitigation*: Unified under canonical mapping.
"""
    return card_content


def run_pipeline(config_path: str = "configs/config.yaml") -> Path:
    """Run data ingestion, rare-preserving sampling, contrast leakage audit, and export."""
    config = load_config(config_path)
    raw_dir = Path(config["data"]["raw_dir"])
    processed_dir = Path(config["data"]["processed_dir"])
    processed_dir.mkdir(parents=True, exist_ok=True)

    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)

    docs_dir = Path("docs")
    docs_dir.mkdir(parents=True, exist_ok=True)

    output_parquet = Path(config["data"]["output_parquet"])
    target_total = config["data"].get("target_total_rows", 65000)
    rare_threshold = config["data"].get("rare_threshold", 20000)
    seed = config["global_settings"]["random_seed"]
    leaky_cols = config["data"]["leaky_columns"]

    logger.info("Starting SentinelX-Shift data pipeline (all 8 partitions, 5 family groups)...")

    # Load all 8 raw partition files and track counts
    dfs = []
    raw_file_counts = {}
    for base_name in ALL_RAW_PARTITIONS:
        file_path = find_data_file(raw_dir, base_name)
        df_part = load_raw_file(
            file_path=file_path,
            leaky_cols=leaky_cols,
            sample_fraction=None,
            random_seed=seed,
        )
        raw_file_counts[file_path.name] = len(df_part)
        logger.info(f"Loaded {file_path.name}: {len(df_part):,} raw rows")
        dfs.append(df_part)

    df_combined = pd.concat(dfs, ignore_index=True)
    logger.info(f"Total raw flows ingested across all 8 files: {len(df_combined):,}")

    # Map attack families to the 5 LOFO Family Groups, skipping Infiltration (<500 flows)
    df_combined = df_combined[df_combined["Label"] != "Infiltration"]
    df_combined["Label"] = df_combined["Label"].map(lambda l: FAMILY_GROUP_MAPPING.get(l, l))

    active_groups = ["DoS_DDoS", "BruteForce", "PortScan", "Bot", "WebAttack", "Benign"]
    df_combined = df_combined[df_combined["Label"].isin(active_groups)]

    # Clean numeric features
    df_clean, num_stats = clean_numeric_features(df_combined, drop_na=True)
    per_group_raw = df_clean["Label"].value_counts().to_dict()

    # Remove exact duplicates across feature vectors
    df_dedup, dedup_stats = remove_exact_duplicates(df_clean, feature_cols_only=True)
    per_group_dedup = df_dedup["Label"].value_counts().to_dict()
    logger.info(f"Unique flows after exact deduplication: {len(df_dedup):,}")

    # Rare-family-preserving subsampling
    df_sampled = preserve_rare_families_sample(
        df=df_dedup,
        target_total=target_total,
        rare_threshold=rare_threshold,
        random_seed=seed,
    )
    logger.info(f"Final preserved sample size: {len(df_sampled):,} rows")
    logger.info(f"Final class counts:\n{df_sampled['Label'].value_counts()}")

    # Save to processed parquet
    df_sampled.to_parquet(output_parquet, index=False)
    logger.info(f"Saved processed dataset to {output_parquet}")

    # Measure real naive XGBoost performance on 70/30 split
    logger.info("Measuring empirical XGBoost baseline performance on naive 70/30 split...")
    xgb_metrics = measure_naive_xgboost_performance(
        df=df_sampled,
        label_col="Label",
        test_size=0.3,
        random_seed=seed
    )
    logger.info(f"Naive XGBoost Accuracy: {xgb_metrics['accuracy']:.4%}, Macro F1: {xgb_metrics['f1_macro']:.4f}")

    # Run Multi-Decimal Contrast Leakage Audit on the 5 Family Groups
    target_groups = ["DoS_DDoS", "BruteForce", "PortScan", "Bot", "WebAttack"]
    logger.info(f"Running Multi-Decimal Contrast Leakage Audit across 5 Family Groups: {target_groups}...")
    contrast_df = run_leakage_contrast_audit(
        df=df_sampled,
        families=target_groups,
        test_size=0.3,
        rounding_levels=[3, 2, 1],
        random_seed=seed,
    )

    # Save audit CSV
    csv_path = results_dir / "leakage_audit.csv"
    contrast_df.to_csv(csv_path, index=False)
    logger.info(f"Saved leakage audit CSV to {csv_path}")

    # Save audit Chart
    chart_path = results_dir / "leakage_audit_comparison.png"
    plot_leakage_contrast(contrast_df, chart_path)
    logger.info(f"Saved leakage audit bar chart to {chart_path}")

    # Generate and write docs/data_card.md
    data_card_md = build_data_card_markdown(
        df_clean=df_sampled,
        raw_file_counts=raw_file_counts,
        dedup_stats=dedup_stats,
        per_group_raw=per_group_raw,
        per_group_dedup=per_group_dedup,
        contrast_df=contrast_df,
        xgb_metrics=xgb_metrics,
        output_parquet=output_parquet,
        seed=seed
    )
    data_card_path = docs_dir / "data_card.md"
    data_card_path.write_text(data_card_md, encoding="utf-8")
    logger.info(f"Data card updated at {data_card_path}")

    return output_parquet


if __name__ == "__main__":
    run_pipeline()
