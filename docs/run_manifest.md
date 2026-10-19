# SentinelX-Shift: Execution & Provenance Run Manifest

**Run ID:** `run_sentinelx_audit_resolved_20261019`  
**Git Commit Hash:** `96b0f25`  
**Execution Environment:** Windows (x64), Python 3.12.10 (`.venv`)  
**Timestamp:** 2026-10-19T11:22:00+05:30  
**Verification Status:** AUDIT RESOLVED & TEST VERIFIED (51 / 51 tests passing)  

---

## 1. Experimental Configuration & Random Seeds

All evaluation experiments use 5 pre-declared deterministic random seeds across model training, data splitting, test resampling, and bootstrapping:
- **Seeds:** `[42, 101, 202, 303, 404]`
- **Prevalences:** 1.0% and 5.0%
- **Bootstrap Iterations:** 1,000 paired resamples per fold/condition
- **Multiple Comparisons Adjustment:** Holm-Bonferroni step-down correction

---

## 2. Datasets & Raw Partition Lineage

### A. CIC-IDS2017 Rebuild
- **Dataset Lineage:** 8 raw PCAP flow partitions loaded from `data/raw/`:
  - `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`: 225,745 rows
  - `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`: 286,467 rows
  - `Friday-WorkingHours-Morning.pcap_ISCX.csv`: 191,033 rows
  - `Monday-WorkingHours.pcap_ISCX.csv`: 529,918 rows
  - `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv`: 288,602 rows
  - `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`: 170,366 rows
  - `Tuesday-WorkingHours.pcap_ISCX.csv`: 445,909 rows
  - `Wednesday-workingHours.pcap_ISCX.csv`: 692,703 rows
  - **Total Raw Partition Flows:** 2,830,743 rows
- **Processed Benchmark Pool:** `data/processed/cicids2017_sample60k.parquet` (60,011 rows, deduplicated, 5 canonical family groups)
  - `DoS_DDoS`: 6,572 flows
  - `BruteForce`: 9,150 flows
  - `PortScan`: 1,955 flows
  - `Bot`: 1,437 flows
  - `WebAttack`: 2,143 flows
  - `Benign`: 38,741 flows
  - `Infiltration`: skipped (under 500 flows; 36 flows total)
- **Held-Out Benign Test Pool:** `data/processed/benign_test_pool_100k.parquet` (100,000 disjoint flows, 0 overlap with train/val sets)
- **Unified Raw Scores:** `results/raw_scores/raw_scores.parquet` (4,131,380 rows, float32, all 5 seeds × 5 folds × 2 prevalences)

### B. UNSW-NB15 Partition
- **Dataset Lineage:** Pre-split partition, pooled and deduplicated:
  - `data/raw/UNSW-NB15/UNSW_NB15_training-set.csv`: 175,341 rows
  - `data/raw/UNSW-NB15/UNSW_NB15_testing-set.csv`: 82,332 rows
  - **Total Pooled Raw Flows:** 257,673 rows
- **Processed Benchmark Pool:** `data/processed/unsw_nb15_pre_split_sample60k.parquet` (60,000 rows, deduplicated, 5 canonical groups)
  - `Recon_Analysis`: 10,000 flows
  - `Exploit_Payload`: 10,000 flows
  - `Fuzzers`: 6,000 flows
  - `DoS`: 4,000 flows
  - `Generic`: 10,000 flows
  - `Benign`: 20,000 flows
- **Held-Out Benign Test Pool:** `data/processed/unsw_nb15_benign_test_pool_100k.parquet` (56,000 disjoint flows, 0 overlap)

---

## 3. Generated Evaluation Results & Artifacts

All numbers in markdown reports and tables are dynamically computed from files saved on disk:

| File Path | Description | Input Lineage |
| --- | --- | --- |
| `results/leakage_audit.csv` | Duplicate & kNN leakage audit for CIC-IDS2017 | `cicids2017_sample60k.parquet` |
| `results/raw_scores/raw_scores.parquet` | 5-seed flow-level detector scores (4.13M rows) | LOFO splits + saved models |
| `results/lofo_benchmark_multi_seed.csv` / `.md` | Full LOFO benchmark table (mean ± std across 5 seeds) | `raw_scores.parquet` |
| `results/fusion_vs_single_comparison.csv` / `.md` | Paired bootstrap differences vs Rule-Selected & AE | `raw_scores.parquet` |
| `results/fusion_weight_stability.csv` / `.md` | Per-seed inner-LOFO weights & degenerate collapse audit | LOFO training checkpoints |
| `results/cross_dataset_comparison.csv` / `.md` | Dataset-level comparison across CIC-IDS2017 & UNSW-NB15 | Benchmark CSVs on disk |
| `results/physical_rejection_rates.csv` / `.md` | Physical domain invariant audit (1%, 5%, 10% jitter) | Sample flows + perturbation engine |
| `results/stability_benchmark.csv` / `.md` | 5 alert ranking variants evaluation & Holm-adjusted CIs | `candidate_stability_scores.parquet` |
| `results/stability_sensitivity_curve.csv` / `.md` | Unified formula sensitivity curve sweeping $b \in [0, 1]$ | `candidate_stability_scores.parquet` |
| `results/unsw_nb15/unsw_nb15_benchmark.csv` / `.md` | 5-seed benchmark table for UNSW-NB15 | UNSW raw partitions |
| `results/unsw_nb15/fusion_vs_single_comparison.csv` / `.md` | Paired bootstrap differences for UNSW-NB15 | UNSW raw partitions |
| `docs/production_score.md` | Guard score specification with exact inner-LOFO validation PR-AUCs | Inner-LOFO tuning results |

---

## 4. End-to-End Reproduction Commands

To reproduce all results, manifests, and tables from scratch without manual intervention, run the following sequential targets:

```bash
# 1. Clean and process raw flow partitions into deduplicated 60k datasets
make process-data

# 2. Execute LOFO duplicate, kNN distance, and train/val/test leakage audit
make audit

# 3. Train models and generate raw scores across all 5 seeds and 5 folds for CIC-IDS2017
make lofo-benchmark

# 4. Train models and evaluate all 5 seeds across 5 groups for UNSW-NB15
make unsw-benchmark

# 5. Run physical perturbation audit, latency calibration, and explanation stability benchmark
make stability-benchmark

# 6. Generate multi-seed benchmark tables, paired bootstrap comparisons, and cross-dataset reports
make report

# 7. Execute full 51-test verification test suite
make test
```
