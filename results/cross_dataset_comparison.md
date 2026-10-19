# Cross-Dataset Generalization & Leakage Audit Summary

- **Git Commit Hash:** `96b0f25`
- **Date:** `2026-10-19 05:33:12 UTC`
- **Raw Scores Row Count:** `4,131,380`
- **Seed Count:** `5`
- **Note:** *Computed entirely from raw_scores.parquet*

This table is dynamically computed from saved result files:

| dataset | files used | raw rows | duplication rate after raw load | random-split leakage (3-dec, log1p, NN) | LOFO leakage (same, raw counts) | family-seen vs LOFO supervised ROC-AUC | best detector | fusion gain vs best single with CI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CIC-IDS2017 | 3 raw partitions (Friday-WorkingHours-Afternoon-PortScan, Tuesday-WorkingHours, Wednesday-workingHours) | 59,998 | Processed sample deduplicated | 72.7% (3dec), 4.2% (log1p), 0.0% (NN eps) | 19.8% (3dec), 0.1% (log1p), 0.0% (NN eps) | 0.9992 vs 0.8513 (-14.79 pp) | Rule_Selected | +18.02 pp [-2.88, +52.97] (Mean PR-AUC gain across folds) |
| UNSW-NB15 | 2 files (test.parquet, train.parquet) [pre-split partition, pooled and deduplicated] | Pre-split partition files | Pooled and deduplicated | 0.8% (3dec), 0.5% (log1p), 0.3% (NN eps) | 0.5% (3dec), 0.4% (log1p), 0.2% (NN eps) | 0.9709 vs 0.9424 (-2.84 pp) | Rule_Selected | +32.90 pp [+7.51, +52.97] (Mean PR-AUC gain across folds) |
| LYCOS-IDS2017 | None (files not provided) | files not provided | files not provided | files not provided | files not provided | files not provided | files not provided | files not provided |
| CSE-CIC-IDS2018 | None (files not provided) | files not provided | files not provided | files not provided | files not provided | files not provided | files not provided | files not provided |

---

### Dataset Provenance & Missing Datasets Note
- **CIC-IDS2017**: Ingested from raw partition CSV files in `data/raw/`. Mapped into active family groups.
- **UNSW-NB15**: 2 partition files (`train.parquet`, `test.parquet`) found in `data/raw/unsw_nb15/`. Labeled strictly as **pre-split partition, pooled and deduplicated**.
- **LYCOS-IDS2017 & CSE-CIC-IDS2018**: **Files not provided on disk**. Their rows are explicitly designated as `"files not provided"`.
