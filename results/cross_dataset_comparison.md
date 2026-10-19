# Cross-Dataset Generalization & Leakage Audit Summary

- **Run ID:** `run_20261019_eddc08e`
- **Git Commit Hash:** `eddc08e-dirty`
- **Date:** `2026-10-19 14:29:04 UTC`
- **Seed Count:** `5`
- **CIC-IDS2017 Raw Rows:** `2,830,743` (Sum of all 8 partition files)
- **CIC-IDS2017 Duplication Rate:** `21.03%` (Sourced from Data Card)
- **Note:** *Dynamically computed entirely from saved evaluation results*

This table is dynamically computed from saved result files:

| dataset | files used | raw rows | duplication rate after raw load | random-split leakage (3-dec, log1p, NN) | LOFO leakage (same, raw counts) | family-seen vs LOFO supervised ROC-AUC | best detector | fusion gain vs best single with CI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CIC-IDS2017 | 8 raw partitions (2,830,743 rows across files) | 2,830,743 | 21.03% | 72.5% (3dec), 4.2% (log1p), NN-med: 0.0568 | 19.3% (3dec), 0.1% (log1p), NN-med: 2.1618 | 0.9992 vs 0.8496 (-14.96 pp) | Bot: Mean_Anomaly, BruteForce: Mean_Anomaly, DoS_DDoS: Isolation_Forest, PortScan: Mean_Anomaly, WebAttack: Autoencoder | +18.01 pp [-1.64, +40.04] (Mean PR-AUC gain across folds) |
| UNSW-NB15 | 2 raw partition files (257,673 rows: train.parquet, test.parquet) | 257,673 | Pooled and deduplicated (254,004 cleaned flows) | 0.88% (3dec), 0.67% (log1p), NN-med: 0.2641 | 0.52% (3dec), 0.36% (log1p), NN-med: 0.5755 | 0.9709 vs 0.9424 (-2.84 pp) | All 5 folds: Autoencoder (Recon_Analysis, Exploit_Payload, Fuzzers, DoS, Generic) | +29.75 pp [+6.02, +58.12] (Mean PR-AUC gain across folds) |
| LYCOS-IDS2017 | None (files not provided) | files not provided | files not provided | files not provided | files not provided | files not provided | files not provided | files not provided |
| CSE-CIC-IDS2018 | None (files not provided) | files not provided | files not provided | files not provided | files not provided | files not provided | files not provided | files not provided |

---

### Dataset Provenance & Missing Datasets Note
- **CIC-IDS2017**: Ingested from all 8 raw partition files in `data/raw/` (2,830,743 total raw rows). Mapped into active family groups.
- **UNSW-NB15**: 2 raw partition files (`train.parquet`, `test.parquet`) found in `data/raw/unsw_nb15/` (257,673 raw rows). Labeled strictly as **pre-split partition, pooled and deduplicated**.
- **LYCOS-IDS2017 & CSE-CIC-IDS2018**: **Files not provided on disk**. Their rows are explicitly designated as `"files not provided"`.
