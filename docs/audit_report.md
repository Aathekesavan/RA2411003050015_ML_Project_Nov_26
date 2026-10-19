# SentinelX-Shift Repository Read-Only Audit Report

**Date of Audit**: October 19, 2026  
**Auditor**: Antigravity Code Integrity & Reproducibility Auditor  
**Scope**: Read-only verification of data lineage, raw score parquet schemas, deterministic seed propagation, hard-coded literals, report generation scripts, family fold definitions, stability evaluation engine, and test suite completeness across `d:/sentinelx`.

---

## 1. Lineage & File Dependency Chain

### Complete Inventory of `results/` and Related Artifacts
Every file in `results/`, along with its modification timestamp (`mtime`), writing script, and input data sources, was inspected:

| File Path | Timestamp (`mtime`) | Writing Script / Function | Inputs Read by Script | Status / Lineage Flag |
| :--- | :--- | :--- | :--- | :--- |
| `data/processed/cicids2017_sample60k.parquet` | 2026-10-19 07:47:11 | `src/data/pipeline.py:save_processed_parquet` | `data/raw/*.csv` (8 CSV partitions) | **CURRENT BASELINE** |
| `data/processed/benign_test_pool_100k.parquet` | 2026-10-18 23:25:43 | `src/eval/lofo.py:build_test_benign_pool` | `cicids2017_sample60k.parquet` (old build) | **STALE** (older than current processed dataset) |
| `results/raw_scores/raw_scores.parquet` | 2026-10-19 08:08:13 | `src/eval/run_lofo_experiments.py` | `data/processed/cicids2017_sample60k.parquet` | Current, but contains seed 42 only |
| `results/raw_scores.parquet` | 2026-10-19 08:08:13 | `src/eval/run_lofo_experiments.py` | Copy of `results/raw_scores/raw_scores.parquet` | Current, seed 42 only |
| `results/lofo_benchmark_multi_seed.csv` | 2026-10-19 08:14:01 | `src/eval/generate_reports.py:regenerate_all_reports` | `results/raw_scores/raw_scores.parquet` | Built from 1 seed (seed 42) |
| `results/lofo_benchmark_multi_seed.md` | 2026-10-19 08:14:01 | `src/eval/generate_reports.py:regenerate_all_reports` | `results/raw_scores/raw_scores.parquet` | Built from 1 seed (seed 42) |
| `results/fusion_vs_single_comparison.csv` | 2026-10-19 08:14:01 | `src/eval/generate_reports.py:regenerate_all_reports` | `results/raw_scores/raw_scores.parquet` | Built from 1 seed (seed 42) |
| `results/fusion_vs_single_comparison.md` | 2026-10-19 08:14:01 | `src/eval/generate_reports.py:regenerate_all_reports` | `results/raw_scores/raw_scores.parquet` | Built from 1 seed (seed 42) |
| `results/reproducibility_report.md` | 2026-10-19 08:14:01 | `src/eval/generate_reports.py:regenerate_all_reports` | `results/raw_scores/raw_scores.parquet` | Built from 1 seed (seed 42) |
| `results/fusion_weight_stability.csv` | 2026-10-19 08:08:13 | `src/eval/run_lofo_experiments.py` | Validation inner folds during LOFO | Current |
| `results/fusion_weight_stability.md` | 2026-10-19 08:08:13 | `src/eval/run_lofo_experiments.py` | Validation inner folds during LOFO | Current |
| `results/fusion_weight_variability.csv` | 2026-10-19 08:08:13 | `src/eval/run_lofo_experiments.py` | Validation inner folds during LOFO | Current |
| `results/fusion_weight_variability.md` | 2026-10-19 08:08:13 | `src/eval/run_lofo_experiments.py` | Validation inner folds during LOFO | Current |
| `results/leakage_audit.csv` | 2026-10-19 07:44:32 | `src/data/audit.py:run_leakage_audit` | `data/processed/cicids2017_sample60k.parquet` (old build) | **STALE** (created before 07:47:11 dataset rebuild) |
| `results/leakage_audit_comparison.png` | 2026-10-19 07:44:36 | `src/data/audit.py:run_leakage_audit` | `results/leakage_audit.csv` | **STALE** (created before 07:47:11 dataset rebuild) |
| `results/lofo_benchmark_results.csv` | 2026-10-18 23:36:26 | `src/eval/run_lofo_experiments.py` (legacy) | Legacy 3-family sample | **STALE** (legacy 3-family run from previous day) |
| `results/lofo_benchmark_results.md` | 2026-10-18 23:36:26 | `src/eval/run_lofo_experiments.py` (legacy) | Legacy 3-family sample | **STALE** (legacy 3-family run from previous day) |
| `results/cross_dataset_comparison.csv` | 2026-10-19 07:51:30 | `scripts/generate_cross_dataset.py` | Hard-coded strings + result CSVs | Contains hard-coded fallback strings |
| `results/cross_dataset_comparison.md` | 2026-10-19 07:51:30 | `scripts/generate_cross_dataset.py` | Hard-coded strings + result CSVs | Contains hard-coded fallback strings |
| `results/candidate_stability_scores.parquet`| 2026-10-19 01:31:56 | `src/stability/run_stability_experiments.py`| Old sample & legacy 3 models | **STALE** (evaluated on 3 legacy families only) |
| `results/stability_benchmark.csv` | 2026-10-19 09:38:22 | `src/stability/run_stability_experiments.py`| `candidate_stability_scores.parquet` | Evaluated on legacy 3 families only |
| `results/stability_benchmark.md` | 2026-10-19 09:38:22 | `src/stability/run_stability_experiments.py`| `candidate_stability_scores.parquet` | Evaluated on legacy 3 families only |
| `results/physical_rejection_rates.csv` | 2026-10-19 09:38:21 | `src/stability/run_stability_experiments.py`| `cicids2017_sample60k.parquet` | Current |
| `results/physical_rejection_rates.md` | 2026-10-19 09:38:21 | `src/stability/run_stability_experiments.py`| `cicids2017_sample60k.parquet` | Current |
| `results/stability_sensitivity_curve.csv` | 2026-10-19 09:38:22 | `src/stability/run_stability_experiments.py`| `candidate_stability_scores.parquet` | Evaluated on legacy 3 families only |
| `results/stability_sensitivity_curve.md` | 2026-10-19 09:38:22 | `src/stability/run_stability_experiments.py`| `candidate_stability_scores.parquet` | Evaluated on legacy 3 families only |
| `results/example_explanations.json` | 2026-10-19 01:09:27 | `src/explain/run_explanation_experiments.py`| Old sample & legacy models | **STALE** (older than current processed dataset) |
| `results/explanation_faithfulness.csv` | 2026-10-19 01:09:28 | `src/explain/run_explanation_experiments.py`| Old sample & legacy models | **STALE** (older than current processed dataset) |
| `results/explanation_faithfulness.md` | 2026-10-19 01:09:28 | `src/explain/run_explanation_experiments.py`| Old sample & legacy models | **STALE** (older than current processed dataset) |
| `results/explanation_latency.csv` | 2026-10-19 01:09:28 | `src/explain/run_explanation_experiments.py`| Old sample & legacy models | **STALE** (older than current processed dataset) |
| `results/explanation_latency.md` | 2026-10-19 01:09:28 | `src/explain/run_explanation_experiments.py`| Old sample & legacy models | **STALE** (older than current processed dataset) |
| `results/models/sentinelx_lofo_DoS.joblib` | 2026-10-19 00:54:17 | `src/eval/run_lofo_experiments.py` | Legacy 3-family sample | **STALE** (orphaned; new model is `DoS_DDoS`) |
| `results/models/sentinelx_lofo_DoS_DDoS.joblib`| 2026-10-19 07:48:34 | `src/eval/run_lofo_experiments.py`| `cicids2017_sample60k.parquet` | Current |
| `results/models/sentinelx_lofo_BruteForce.joblib`| 2026-10-19 07:49:02 | `src/eval/run_lofo_experiments.py`| `cicids2017_sample60k.parquet` | Current |
| `results/models/sentinelx_lofo_PortScan.joblib`| 2026-10-19 07:49:26 | `src/eval/run_lofo_experiments.py`| `cicids2017_sample60k.parquet` | Current |
| `results/models/sentinelx_lofo_Bot.joblib` | 2026-10-19 07:49:50 | `src/eval/run_lofo_experiments.py` | `cicids2017_sample60k.parquet` | Current |
| `results/models/sentinelx_lofo_WebAttack.joblib`| 2026-10-19 07:50:19 | `src/eval/run_lofo_experiments.py` | `cicids2017_sample60k.parquet` | Current |
| `results/manifests/lofo_*_p001_manifest.json`| 2026-10-18 23:16:xx | `src/eval/lofo.py:save_manifest` | Legacy 3-family sample | **STALE** (0.1% prevalence manifests from 2026-10-18) |
| `results/manifests/lofo_*_p100_manifest.json`| 2026-10-18 23:16:xx | `src/eval/lofo.py:save_manifest` | Legacy 3-family sample | **STALE** (10% prevalence manifests from 2026-10-18) |
| `results/unsw_nb15/*` (all 11 files) | 2026-10-19 01:18–01:25 | `src/eval/run_unsw_experiments.py` | `data/raw/unsw_nb15/*.parquet` | Generated during Prompt 5 run |

### End-to-End Lineage Flow Diagram
```
[Raw Network Flow Captures: 8 CSV Files in data/raw/]
                   |
                   v (src/data/pipeline.py: save_processed_parquet @ 07:47:11)
[data/processed/cicids2017_sample60k.parquet] (60,000 rows, 5 mapped attack groups)
         |                                                 |
         | (Pre-rebuild 07:44:32: STALE)                   | (08:06:30 - 08:08:13)
         v                                                 v
[results/leakage_audit.csv]               [src/eval/run_lofo_experiments.py]
                                                 |              |
                    +----------------------------+              v
                    |                                 [results/models/*.joblib]
                    v                                 [results/fusion_weight_*.csv]
   [results/raw_scores/raw_scores.parquet]
   (814,707 rows, Seed 42 ONLY, Prevalences 1% & 5%)
                    |
                    v (src/eval/generate_reports.py: regenerate_all_reports @ 08:14:01)
   [results/lofo_benchmark_multi_seed.csv / .md]
   [results/fusion_vs_single_comparison.csv / .md]
   [results/reproducibility_report.md]
```

### Stale Artifact Flags
- `results/leakage_audit.csv` & `results/leakage_audit_comparison.png` (`07:44:32`) were produced **3 minutes before** `data/processed/cicids2017_sample60k.parquet` (`07:47:11`) was rebuilt.
- `data/processed/benign_test_pool_100k.parquet` (`2026-10-18 23:25:43`) was generated prior to the 8-file rebuild.
- `results/models/sentinelx_lofo_DoS.joblib` (`2026-10-19 00:54:17`) is an orphaned artifact from the legacy 3-family scheme.
- `results/example_explanations.json`, `results/explanation_faithfulness.*`, and `results/explanation_latency.*` (`01:09:27`) were never updated with the 5-group rebuild.

---

## 2. Stale Results & Schema Audit of `raw_scores.parquet`

### Command Execution
```python
import pandas as pd
df = pd.read_parquet('results/raw_scores/raw_scores.parquet')
print('Columns:', df.columns.tolist())
print('Dataset in columns:', 'dataset' in df.columns)
print('Seed in columns:', 'seed' in df.columns)
print('Family in columns:', 'family' in df.columns)
print('Fold in columns:', 'fold' in df.columns)
print('Unique folds:', df['fold'].unique().tolist())
print('Unique prevalences:', df['prevalence'].unique().tolist())
print('Row counts per fold and prevalence:\n', df.groupby(['fold', 'prevalence']).size())
print('Total rows:', len(df))
```

### Verbatim Output
```
Columns: ['fold', 'prevalence', 'flow_id', 'label', 'is_attack', 'supervised', 'iforest', 'autoencoder', 'mean_anomaly', 'fused_val', 'fused_inner_lofo', 'fused_inner_iforest', 'fused_inner_ae', 'rank_average', 'anomaly_heavy', 'gated_boost', 'max_fusion', 'logistic_stack']
Dataset in columns: False
Seed in columns: False
Family in columns: False
Fold in columns: True
Unique folds: ['LOFO_DoS_DDoS', 'LOFO_BruteForce', 'LOFO_PortScan', 'LOFO_Bot', 'LOFO_WebAttack']
Unique prevalences: [0.01, 0.05]
Row counts per fold and prevalence:
fold             prevalence
LOFO_Bot         0.01           99377
                 0.05           28740
LOFO_BruteForce  0.01           99377
                 0.05          103561
LOFO_DoS_DDoS    0.01           99377
                 0.05          103561
LOFO_PortScan    0.01           99377
                 0.05           39100
LOFO_WebAttack   0.01           99377
                 0.05           42860
dtype: int64
Total rows: 814707
```

### Analysis of Findings
1. **Attack Groups**: The file contains all **5 family groups** (`LOFO_DoS_DDoS`, `LOFO_BruteForce`, `LOFO_PortScan`, `LOFO_Bot`, `LOFO_WebAttack`). It does not contain the legacy 3-family-only set.
2. **Missing Columns**:
   - `dataset` is **NOT** in the columns.
   - `family` is **NOT** in the columns (stored under `fold`).
   - `seed` is **NOT** in the columns.
3. **Number of Seeds Held**: The file holds **ONLY 1 SEED** (seed 42).
   - In `src/eval/run_lofo_experiments.py` line 277, the code contains:
     ```python
     # Record raw flow-level scores for primary seed 42
     if seed == 42:
         for i in range(len(test_df)):
             raw_scores_records.append({...})
     ```
   - Seeds 101, 202, 303, and 404 were executed in memory for computing summary metrics, but their raw prediction scores were discarded and never saved to `raw_scores.parquet`.

---

## 3. Seed Tracing & Multi-Seed Verification

### Trace of Seed Propagation Through Code

| Component | Code Location | Mechanism |
| :--- | :--- | :--- |
| **(a) XGBoost** | `src/models/pipeline.py:309`<br>`src/models/detector.py:97` | `Pipeline.fit()` passes `random_seed=random_seed` to `XGBoostDetector(random_seed=...)`. Inside detector: `self.model = XGBClassifier(random_state=self.random_seed, ...)`. |
| **(b) Isolation Forest**| `src/models/pipeline.py:326`<br>`src/models/detector.py:132` | `Pipeline.fit()` passes `random_seed=random_seed` to `IsolationForestDetector(random_seed=...)`. Inside detector: `self.model = IsolationForest(random_state=self.random_seed, ...)`. |
| **(c) Autoencoder** | `src/models/pipeline.py:329`<br>`src/models/detector.py:172` | `Pipeline.fit()` passes `random_seed=random_seed` to `AutoencoderDetector(random_seed=...)`. Inside detector: `self.model = MLPRegressor(random_state=self.random_seed, ...)`. |
| **(d) Test Resampling** | `src/eval/lofo.py:208, 236, 259`<br>`src/eval/lofo.py:98, 107, 110` | `LOFOSplitEngine(random_seed=random_seed)` sets `self.random_seed`. `split_benign_flows` uses `train_test_split(random_state=self.random_seed)`, other attack held-out split uses `random_state=self.random_seed`, and `resample_prevalence` uses `sample(n=..., random_state=random_seed)`. |
| **(e) Perturbations** | `src/stability/perturb.py:53-54`<br>`src/stability/run_stability_experiments.py:66` | `PhysicalPerturbationEngine(random_seed=...)` initializes `self.rng = np.random.RandomState(random_seed)`. **Defect noted**: In `run_stability_experiments.py:66`, `engine = PhysicalPerturbationEngine(random_seed=42)` is hardcoded to 42, ignoring incoming seeds. |

### 2-Seed Mini-Check on Fold `PortScan` (Seeds 42 vs 100)
To verify whether model predictions and fusion scores actually vary between seeds, identical models were trained on fold `PortScan` using seeds 42 and 100, and evaluated on the same 20 test flows:

```
Method               Mean Absolute Score Difference    Max Absolute Difference    Scores Identical?
Supervised (XGB)     0.004390                          0.086927                   False
Isolation Forest     0.044799                          0.162494                   False
Autoencoder          0.043011                          0.165978                   False
Fused Inner-LOFO     0.180169                          0.414194                   False
Gated Boost          0.042301                          0.165978                   False
```
**Conclusion**: When seeds are propagated, model training and scores genuinely change across seeds. The lack of standard deviations in `lofo_benchmark_multi_seed.md` is solely because `raw_scores.parquet` stores only seed 42.

---

## 4. Hard-Coded Values & Non-Generated Results Literals

A search across `src/` and `scripts/` identified numeric literals and result strings:

### 1. `scripts/generate_cross_dataset.py`
- **Lines 33–40**:
  ```python
  cic_raw_rows = "2,830,743"
  cic_dedup_rate = "21.03% (2,233,128 unique flows)"
  cic_rand_leak = "72.8% (3dec), 4.1% (log1p), 84.5% (NN eps; DoS=74.8%, PortScan=96.6%, BruteForce=82.2%)"
  cic_lofo_leak = "21.2% (3dec: 131/1956 PortScan, 162/9150 BruteForce, 259/6572 DoS, 553/1437 Bot, 1179/2143 WebAttack), 0.1% (log1p), 1.4% (NN eps; DoS=3.8%, PortScan=0.0%, BruteForce=0.4%)"
  cic_roc_comp = "0.9999 +/- 0.0001 vs 0.7151 +/- 0.0633 (-28.48 pp)"
  cic_best_det = "Mean_Anomaly"
  cic_fusion_gain = "+21.45 pp [+17.82, +25.10] (Mean PR-AUC gain of Gated Boost vs Best Single across 5 folds)"
  ```
- **Lines 59–66**:
  ```python
  unsw_raw_rows = "257,673"
  unsw_dedup_rate = "47.67% (134,842 unique flows)"
  unsw_rand_leak = "0.8% (3dec), 0.5% (log1p), 0.3% (NN eps)"
  unsw_lofo_leak = "0.5% (3dec: 25/3007 Recon_Analysis, 25/9795 Exploit, 18/5241 Fuzzers, 35/4023 DoS, 9/2822 Generic), 0.4% (log1p), 0.2% (NN eps)"
  unsw_roc_comp = "0.9761 +/- 0.0026 vs 0.9264 +/- 0.0057 (-4.97 pp)"
  unsw_best_det = "Autoencoder"
  unsw_fusion_gain = "+26.81 pp [+23.10, +30.50] (Mean PR-AUC gain of XGB+AE Fusion vs Best Single across 5 folds)"
  ```
- **Lines 150–169** (Hard-coded text in generated markdown document):
  - Line 150: `- **PortScan**: 96.6% of test positives lie within \epsilon of training flows.`
  - Line 151: `- **BruteForce**: 82.2% of test positives lie within \epsilon of training flows.`
  - Line 152: `- **DoS**: 74.8% of test positives lie within \epsilon of training flows.`
  - Line 157: `Clarification on 98.3%: The previously reported 98.3% figure was the coarse 1-decimal rounding...`
  - Line 158: `Clarification on Naive Accuracy: The previously cited "99.4%" was the empirical test accuracy...`
  - Line 162: `In published literature claiming 84.2%+ memorization on UNSW-NB15...`
  - Line 168: `- **CIC-IDS2017 Mean Gain**: +21.45 pp (95% CI: [+17.82, +25.10])`
  - Line 169: `- **UNSW-NB15 Mean Gain**: +26.81 pp (95% CI: [+23.10, +30.50])`

### 2. `src/eval/run_unsw_experiments.py`
- **Lines 530–565** (Fallback variables if result CSVs are absent):
  ```python
  cic_raw_rows = 1_425_079
  cic_dedup_rate = "24.61% (1,072,941 unique)"
  cic_rand_leak = "88.9% (3dec), 4.3% (log1p)"
  cic_lofo_leak = "3.3% (65/1956), 0.0% (log1p)"
  cic_roc_comp = "0.9999 vs 0.7151 (-28.48 pp)"
  cic_fusion_gain = "+24.19 pp [+19.77, +28.62]"
  ```
- **Lines 569–600**:
  ```python
  unsw_raw_rows = 257_673
  unsw_dedup_rate = "47.67% (134,842 unique)"
  unsw_rand_leak = "82.4% (3dec), 12.1% (log1p), 85.0% (NN eps)"
  unsw_lofo_leak = "0.0% (0/7819), 0.0% (log1p), 0.0% (NN eps)"
  unsw_roc_comp = "0.9776 vs 0.9236 (-5.40 pp)"
  unsw_fusion_gain = "+26.81 pp [+23.10, +30.50]"
  ```
- **Lines 663–672**:
  Hardcoded docstring text describing `1,425,079 raw rows`, `24.61%`, `88.93%`, and `99.4%`.

### 3. `src/eval/generate_reports.py`
- **Line 483**: Hard-coded summary in generated markdown:
  `On unseen DoS attacks (1% prevalence), Gated Boost achieves **0.5621 PR-AUC** (compared to 0.0999 for XGBoost alone and ...)`

### 4. Search for `16.67`
- `16.67` was **NOT FOUND** in `src/` or `scripts/`.
- Grep located occurrences exclusively in raw network flow captures (`data/raw/Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`, `Tuesday-WorkingHours.pcap_ISCX.csv`, `Wednesday-workingHours.pcap_ISCX.csv`), where `16.666667` represents flow packet rates / duration microseconds.

---

## 5. Report Generators & Data Origin Audit

| Table File | Generating Function | Source File Read | Integrity Analysis: Computed vs Copied/Interpolated |
| :--- | :--- | :--- | :--- |
| `results/lofo_benchmark_multi_seed.md` & `.csv` | `regenerate_all_reports()` in `src/eval/generate_reports.py:161` | `results/raw_scores/raw_scores.parquet` | **Computed from raw scores, but with single-seed limitation**: Computed across rows of `raw_scores.parquet`. However, because `raw_scores.parquet` contains only seed 42, no multi-seed mean or std exists; it outputs point estimates for seed 42 under a "Multi-Seed" header. Gated boost is computed with a fixed formula (`AE + 0.2*(XGB>0.5)`) rather than per-fold inner-LOFO tuned thresholds. Rule detector is selected via hardcoded conditional (WebAttack $\to$ AE, others $\to$ Mean_Anomaly). |
| `results/fusion_vs_single_comparison.md` & `.csv` | `regenerate_all_reports()` in `src/eval/generate_reports.py:334` | `results/raw_scores/raw_scores.parquet` | **Computed from raw scores**: Recomputes paired bootstrap deltas (100 bootstrap resamples) using component columns of seed 42. |
| `results/fusion_weight_stability.md` & `.csv` | `run_lofo_experiments()` in `src/eval/run_lofo_experiments.py:470` | Validation inner folds during execution | **Computed dynamically**: Formatted from fold tuning logs. |
| `results/fusion_weight_variability.md` & `.csv` | `run_lofo_experiments()` in `src/eval/run_lofo_experiments.py:504` | Validation inner folds during execution | **Computed dynamically**: Formatted from fold tuning logs; flags degenerate tuning when $w \in \{0.0, 1.0\}$. |
| `results/leakage_audit.csv` & `.png` | `run_leakage_audit()` in `src/data/audit.py:201` | `data/processed/cicids2017_sample60k.parquet` | **Computed dynamically**, but input file at runtime was the pre-07:47:11 version. |
| `results/cross_dataset_comparison.md` & `.csv` | `build_cross_dataset_comparison()` in `scripts/generate_cross_dataset.py:28` | Result CSVs with hard-coded fallbacks | **Copied and Interpolated**: Uses hard-coded strings for raw row counts, duplication rates, leakage rates, and fallback CI intervals. |
| `results/reproducibility_report.md` | `regenerate_all_reports()` in `src/eval/generate_reports.py:440` | `results/raw_scores/raw_scores.parquet` | Stamped with git hash (`96b0f25`), but contains hard-coded narrative numbers (`0.5621 PR-AUC`). |
| `results/stability_benchmark.md` & `.csv` | `run_stability_experiments()` in `src/stability/run_stability_experiments.py:107` | `results/candidate_stability_scores.parquet` | Computed on 3 legacy families only. |
| `results/physical_rejection_rates.md` & `.csv`| `run_physical_rejection_audit()` in `src/stability/run_stability_experiments.py:73`| `cicids2017_sample60k.parquet` | **Computed dynamically** from 100 flows $\times$ 50 perturbations. |
| `results/unsw_nb15/unsw_nb15_benchmark.md` & `.csv`| `run_unsw_experiments()` in `src/eval/run_unsw_experiments.py:400`| In-memory fold runs on UNSW data | **Computed dynamically** across 5 seeds. |

---

## 6. Fold Definitions & Family-Group Mappings

### Configuration in `configs/config.yaml`
```yaml
data:
  active_attack_families:
    - "DoS_DDoS"
    - "BruteForce"
    - "PortScan"
    - "Bot"
    - "WebAttack"

  label_mapping:
    "BENIGN": "Benign"
    "DoS Hulk": "DoS"
    "DoS GoldenEye": "DoS"
    "DoS slowloris": "DoS"
    "DoS Slowhttptest": "DoS"
    "Heartbleed": "DoS"
    "PortScan": "PortScan"
    "FTP-Patator": "BruteForce"
    "SSH-Patator": "BruteForce"
    "DDoS": "DDoS"
    "Bot": "Bot"
    "Web Attack – Brute Force": "WebAttack"
    "Web Attack – XSS": "WebAttack"
    "Web Attack – Sql Injection": "WebAttack"
    "Infiltration": "Infiltration"
```

### Mapping in `src/data/pipeline.py`
```python
FAMILY_GROUP_MAPPING = {
    "Benign": "Benign",
    "DoS": "DoS_DDoS",
    "DDoS": "DoS_DDoS",
    "BruteForce": "BruteForce",
    "PortScan": "PortScan",
    "Bot": "Bot",
    "WebAttack": "WebAttack",
}
```
`Infiltration` is skipped during dataset construction (`pipeline.py:281`) because it has only 36 unique flows in the 2.83M raw dataset, falling below the threshold of 500 unique flows.

### Consistency Check Across System Components
1. **Processed Parquet (`data/processed/cicids2017_sample60k.parquet`)**: Matches `FAMILY_GROUP_MAPPING`. Labels present: `['Benign', 'BruteForce', 'DoS_DDoS', 'WebAttack', 'PortScan', 'Bot']`.
2. **LOFO Engine & Models (`src/eval/run_lofo_experiments.py`)**: Uses `config["data"]["active_attack_families"]`. Trained 5 model files: `sentinelx_lofo_DoS_DDoS.joblib`, `sentinelx_lofo_BruteForce.joblib`, `sentinelx_lofo_PortScan.joblib`, `sentinelx_lofo_Bot.joblib`, `sentinelx_lofo_WebAttack.joblib`.
3. **Leakage Audit (`src/data/audit.py`)**: Uses `config["data"]["active_attack_families"]` (5 groups).
4. **Reports Generator (`src/eval/generate_reports.py`)**: Reads `df_raw["fold"]`, correctly expecting `['LOFO_DoS_DDoS', 'LOFO_BruteForce', 'LOFO_PortScan', 'LOFO_Bot', 'LOFO_WebAttack']`.
5. **Stability Runner (`src/stability/run_stability_experiments.py:127`)**: **MISMATCH FOUND**. Hardcodes:
   ```python
   families = ["DoS", "PortScan", "BruteForce"]
   ```
   It looks for `sentinelx_lofo_DoS.joblib` (which only exists as a stale artifact from 00:54) and completely ignores `DoS_DDoS`, `Bot`, and `WebAttack`.

---

## 7. Explanation Stability Engine Audit

### Candidate Set Construction
- **Code Location**: `src/stability/run_stability_experiments.py:152–160`
  ```python
  fam_attacks = df[df["Label"] == fam]
  n_att = min(int(n_candidates_per_family * 0.6), len(fam_attacks))
  n_ben = n_candidates_per_family - n_att

  cand_attacks = fam_attacks.sample(n=n_att, random_state=random_seed)
  cand_benign = train_benign.sample(n=n_ben, random_state=random_seed)
  candidate_pool = pd.concat([cand_attacks, cand_benign], ignore_index=True).sample(
      frac=1.0, random_state=random_seed
  ).reset_index(drop=True)
  ```
- **Size and Composition**:
  - `n_candidates_per_family = 60` flows per family $\times$ 3 families (`DoS`, `PortScan`, `BruteForce`) = **180 candidate flows total**.
  - **Class Balance**: 60% attack flows (36 per family) and 40% benign flows (24 per family).
  - **Train / Test Split** (lines 180–182): 40% inner validation pool (72 flows) for tuning hyperparameters $(a, b)$, and 60% held-out test pool (108 flows: 65 attacks, 43 benign) for reporting final ranking metrics.

### Mathematical Formulation of Stability Weight $b$
A mathematical discrepancy exists between the $V_2$ ranking score and the sensitivity curve:
1. **$V_2$ Score Formula (`src/stability/stability.py:283`)**:
   $$V_2 = s_{\text{risk}} \cdot (a + b \cdot S_{\text{exp}})$$
   Here, $b$ is a **multiplicative gating weight** scaling explanation stability $S_{\text{exp}}$, added to baseline intercept $a$, and modulated by base risk score $s_{\text{risk}}$.
2. **Sensitivity Curve Formula (`src/stability/stability.py:455`)**:
   $$s(b) = (1 - b) \cdot s_{\text{risk}} + b \cdot S_{\text{exp}}$$
   Here, $b \in [0, 1]$ is a **convex linear interpolation weight** blending base risk and explanation stability.
3. **Secondary Variants ($V_{2a}, V_{2b}$)** (`src/stability/stability.py:294–298`):
   Fixed convex combinations: $V_{2a} = 0.70 \cdot s_{\text{risk}} + 0.30 \cdot S_{\text{exp}}$ and $V_{2b} = 0.50 \cdot s_{\text{risk}} + 0.50 \cdot S_{\text{exp}}$.

### Perturbation Generator Order of Operations (`src/stability/perturb.py`)
To preserve physical networking validity without creating non-physical packet flows, perturbations follow a strict order of operations:

1. **Flow Duration Bounded Jitter** (lines 219–226):
   - Jitters `Flow Duration` (or `dur`) uniformly within $\pm 5\%$, bounded to $\ge 1.0\,\mu\text{s}$.
2. **Base Packet and Byte Counts Jitter** (lines 228–234):
   - Jitters base integers (`Total Fwd Packets`, `Total Backward Packets`, `Total Length of Fwd Packets`, `Total Length of Bwd Packets`, `spkts`, `dpkts`, `sbytes`, `dbytes`) by uniform $\pm 5\%$ with rounded integer casting.
3. **Physical Line-Rate Enforcement** (lines 240–248):
   - Computes $\text{PPS} = \frac{\text{Total Packets}}{\text{Duration}}$. If $\text{PPS} > 1.5 \times 10^8$ (150 Mpps line rate limit for 100 GbE), flow duration is extended to enforce physical feasibility.
4. **TCP Flag Bounding** (lines 250–255):
   - Jitters TCP flag counts (`FIN`, `SYN`, `RST`, `PSH`, `ACK`, `URG`, `ECE`, `CWR`) and clamps each to $[0, \text{Total Packets}]$.
5. **Statistical Packet Length Hierarchy Preservation** (lines 256–285):
   - Applies common scaling to (`Min`, `Mean`, `Max`) followed by fine sub-jitter, strictly clamping to enforce:
     $$\text{Min Packet Length} \le \text{Packet Length Mean} \le \text{Max Packet Length}$$
   - Jitters standard deviation and sets $\text{Variance} = \text{Std}^2$.
6. **Inter-Arrival Time (IAT) Hierarchy Preservation** (lines 289–320):
   - Jitters `Flow IAT`, `Fwd IAT`, and `Bwd IAT` statistics preserving $\text{Min} \le \text{Mean} \le \text{Max}$.
   - Clamps `Flow IAT Max` $\le$ `Flow Duration`.
7. **Active / Idle Temporal Preservation** (lines 321–337):
   - Scales active/idle time windows preserving $\text{Min} \le \text{Mean} \le \text{Max}$.
8. **Strict Recomputation of Derived Features** (`_recalculate_derived_features`, lines 143–202):
   - The following features are **never jittered directly**; they are strictly recomputed from base quantities:
     - `Flow Bytes/s` $= \frac{\text{Total Bytes}}{\text{Duration}}$
     - `Flow Packets/s` $= \frac{\text{Total Packets}}{\text{Duration}}$
     - `Fwd Packets/s` $= \frac{\text{Total Fwd Packets}}{\text{Duration}}$
     - `Bwd Packets/s` $= \frac{\text{Total Bwd Packets}}{\text{Duration}}$
     - `Average Packet Size` $= \frac{\text{Total Bytes}}{\text{Total Packets}}$
     - `Avg Fwd Segment Size` $= \frac{\text{Total Fwd Bytes}}{\text{Total Fwd Packets}}$
     - `Avg Bwd Segment Size` $= \frac{\text{Total Bwd Bytes}}{\max(1, \text{Total Bwd Packets})}$
     - `Down/Up Ratio` $= \frac{\text{Total Bwd Packets}}{\text{Total Fwd Packets}}$
     - Mirrored subflow counts (`Subflow Fwd Packets`, `Subflow Fwd Bytes`, etc.)
     - UNSW-NB15 metrics: `rate`, `sload`, `dload`, `smean`, `dmean`.
9. **Invariant Verification Gate** (`_validate_invariants`, lines 76–141):
   - Verifies 8 physical rules (non-negativity, positive duration, line rate, flag bounds, length hierarchy, IAT hierarchy, non-negative std, temporal max IAT). Rejects candidate flow if any rule is violated.

---

## 8. Test Suite Analysis (41 Tests)

### Inventory of All 41 Collected Tests
```
tests/test_adapters.py:
  1. test_cicids2017_adapter_schema
  2. test_unsw_nb15_adapter_schema
  3. test_missing_dataset_graceful_handling
  4. test_no_group_is_split_across_train_and_test
tests/test_data_pipeline.py:
  5. TestColumnCleaningAndMapping::test_clean_column_names_strips_whitespace
  6. TestColumnCleaningAndMapping::test_clean_column_names_deduplicates_headers
  7. TestColumnCleaningAndMapping::test_label_mapping_canonical_families
  8. TestColumnCleaningAndMapping::test_drop_leaky_columns
  9. TestDataCleanerAndDeduplication::test_clean_numeric_features_inf_nan
 10. TestDataCleanerAndDeduplication::test_remove_exact_duplicates
 11. TestDataCleanerAndDeduplication::test_preserve_rare_families_sample
 12. TestLeakageAudit::test_leakage_audit_detects_zero_leakage_on_disjoint_sets
 13. TestLeakageAudit::test_sanity_check_benign_overlap_known_duplicates
 14. TestLeakageAudit::test_run_leakage_contrast_audit
 15. TestLeakageAudit::test_lofo_total_equals_union_and_overlap_count
 16. TestLeakageAudit::test_exact_leakage_vs_nn_distance_submicrosecond_jitter
tests/test_explain.py:
 17. test_explanation_has_exactly_five_features_per_list
 18. test_shap_contributions_sum_close_to_model_output
 19. test_render_json_validity
 20. test_zero_test_data_used_for_background_set
 21. test_plain_english_sentence_only_flow_behavior
 22. test_evaluate_faithfulness_calibrated_threshold
tests/test_lofo.py:
 23. TestLOFOSplitEngine::test_lofo_normal_case_passes
 24. TestLOFOSplitEngine::test_lofo_assertion_fails_when_f_in_train
 25. TestLOFOSplitEngine::test_lofo_assertion_fails_when_f_in_val
 26. TestLOFOSplitEngine::test_lofo_assertion_fails_on_duplicate_rows_across_splits
 27. TestLOFOSplitEngine::test_lofo_assertion_fails_on_benign_index_overlap
 28. TestLOFOSplitEngine::test_prevalence_resampling_attack_and_benign_sides
tests/test_models_fusion.py:
 29. test_feature_pipeline
 30. test_ecdf_calibrator_bounds
 31. test_calibrated_scores_in_zero_one
 32. test_anomaly_detectors_never_trained_on_attack_rows
 33. test_fusion_weights_sum_to_one_and_no_test_leakage
 34. test_nested_inner_lofo_tuning_weights
 35. test_sentinelx_predictor_api_and_persistence
tests/test_stability.py:
 36. test_perturbation_rejection_rate_bounded
 37. test_physical_perturbation_preserves_invariants
 38. test_variant_iii_not_identical_to_variant_i_when_b_positive
 39. test_ranking_variants_correct_order
 40. test_a_and_b_tuned_on_inner_folds_only
 41. test_jaccard_and_spearman_bounds
```

### Coverage of Items Added in Previous Prompts
- **Tests That Exist**:
  - Adapter schemas and graceful missing dataset handling (`test_adapters.py:1–4`).
  - Strict LOFO partition assertions and prevalence resampling (`test_lofo.py:23–28`).
  - Leakage audit union equality, nearest-neighbor distance, and exact collision checks (`test_data_pipeline.py:12–16`).
  - Plain English sentence constraints and calibrated faithfulness alert threshold (`test_explain.py:21–22`).
  - Inner LOFO weight tuning on validation and zero attack exposure for unsupervised models (`test_models_fusion.py:32–34`).
  - Physical invariant preservation during flow perturbation (`test_stability.py:36–37`).
  - Strict order of ranking variants $V_1$ through $V_5$ and inner-fold tuning of $(a, b)$ (`test_stability.py:38–40`).

- **Tests That Are Missing**:
  1. **Multi-Seed Coverage in Raw Scores**: No test verifies that all 5 seeds are serialized to `raw_scores.parquet`.
  2. **Report Regeneration (`src/eval/generate_reports.py`)**: No test verifies that `regenerate_all_reports` executes without error, produces valid markdown/CSV tables, and stamps them with git commit hashes.
  3. **Recall @ 1% FAR & Recall @ 0.1% FAR Metrics**: No test verifies operating-point calculation logic for fixed false alarm rate thresholds.
  4. **5 Family Groups in Stability Runner**: No test checks that `run_stability_experiments.py` supports all active family groups (`DoS_DDoS`, `Bot`, `WebAttack`, etc.).
  5. **Dynamic Data Loading in Cross-Dataset Summary**: No test guards against hardcoded fallback strings in `generate_cross_dataset.py` or `run_unsw_experiments.py`.
  6. **Production Score Selection Assertion**: No test verifies that `docs/production_score.md` exists and declares the chosen production scoring policy.

### Why the Test Count Stayed at 41
When the requirements from the previous prompts were addressed, the changes were implemented by modifying core scripts (`generate_reports.py`, `run_lofo_experiments.py`, `scripts/generate_cross_dataset.py`, `config.yaml`) and modifying existing assertions inside existing test functions (e.g., updating `test_ranking_variants_correct_order`, `test_a_and_b_tuned_on_inner_folds_only`, and `test_evaluate_faithfulness_calibrated_threshold`). No new `def test_*` functions were declared or added to the test files. Consequently, the total collected test count remained at 41.

---

## 9. Ranked Root Causes, Affected Files, and Minimal Proposed Fixes

| Rank | Root Cause | Affected Files | Minimal Fix Proposal (Not Implemented) |
| :---: | :--- | :--- | :--- |
| **1** | **`raw_scores.parquet` stores only seed 42**<br>`run_lofo_experiments.py` line 277 explicitly conditioned score recording on `if seed == 42:`. Consequently, `generate_reports.py` cannot compute 5-seed means and standard deviations, leaving `lofo_benchmark_multi_seed.md` populated with single-seed results. | `src/eval/run_lofo_experiments.py`<br>`src/eval/generate_reports.py` | 1. In `run_lofo_experiments.py:277`, remove `if seed == 42:` and append `'seed': seed` to each record.<br>2. In `generate_reports.py`, group raw scores by `['fold', 'prevalence', 'seed']`, calculate seed-level metrics, and report `mean +/- std` across seeds. |
| **2** | **Hard-coded literals and fallback strings in summary reports**<br>`scripts/generate_cross_dataset.py` and `src/eval/run_unsw_experiments.py` contain hardcoded numbers (`2,830,743`, `21.03%`, `84.5%`, `+21.45 pp [+17.82, +25.10]`, `+26.81 pp`) rather than dynamically calculating them from underlying data and saved results. | `scripts/generate_cross_dataset.py`<br>`src/eval/run_unsw_experiments.py` | 1. Replace hardcoded variables in `generate_cross_dataset.py` with dynamic aggregation from `results/lofo_benchmark_multi_seed.csv`, `results/unsw_nb15/unsw_nb15_benchmark.csv`, and `results/leakage_audit.csv`.<br>2. Remove static fallback dictionaries; raise explicit `FileNotFoundError` if prerequisites are missing. |
| **3** | **Stale artifacts in `results/` from earlier/legacy runs**<br>`results/leakage_audit.csv` (`07:44:32`) was generated before the latest dataset parquet rebuild (`07:47:11`). Legacy files (`lofo_benchmark_results.*`, `sentinelx_lofo_DoS.joblib`, `benign_test_pool_100k.parquet`) remain from previous day runs. | `results/leakage_audit.csv`<br>`results/leakage_audit_comparison.png`<br>`data/processed/benign_test_pool_100k.parquet`<br>`results/models/sentinelx_lofo_DoS.joblib` | 1. Re-run `python -m src.data.audit` to refresh `results/leakage_audit.csv` on current `cicids2017_sample60k.parquet`.<br>2. Remove orphaned legacy files (`sentinelx_lofo_DoS.joblib`, `lofo_benchmark_results.*`). |
| **4** | **Stability runner family mismatch**<br>`src/stability/run_stability_experiments.py` line 127 hardcodes `families = ["DoS", "PortScan", "BruteForce"]`, attempting to load `sentinelx_lofo_DoS.joblib` rather than the active 5 family groups (`DoS_DDoS`, `Bot`, `WebAttack`, etc.). | `src/stability/run_stability_experiments.py` | In `run_stability_experiments.py:127`, load active attack groups dynamically from `config["data"]["active_attack_families"]` and evaluate all 5 folds. |
| **5** | **Mathematical formulation discrepancy for stability parameter $b$**<br>$V_2$ score applies $b$ multiplicatively ($s_{\text{risk}} \cdot (a + b \cdot S_{\text{exp}})$), whereas the sensitivity curve evaluates $b$ as a convex interpolation weight ($(1 - b) \cdot s_{\text{risk}} + b \cdot S_{\text{exp}}$). | `src/stability/stability.py` | Standardize sensitivity curve to evaluate the exact $V_2$ functional form $s_{\text{risk}} \cdot (a + b \cdot S_{\text{exp}})$ across varying $b$, or clearly distinguish multiplicative gating from convex interpolation in the documentation. |
| **6** | **Missing test coverage for report generation and multi-seed serialization**<br>Total test count remained at 41 because new prompt requirements were added directly to production and script code without declaring corresponding test functions in `tests/`. | `tests/test_models_fusion.py`<br>`tests/test_stability.py`<br>`tests/test_data_pipeline.py` | Add unit tests covering `generate_reports.py`, verifying 5-seed serialization in `raw_scores.parquet`, operating-point metric computations (Recall @ FAR), and 5-group stability runs. |
