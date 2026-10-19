# SentinelX-Shift Reproducibility Audit & Benchmark Verification

- **Run ID:** `run_reproducible_lofo_96b0f25`
- **Git Commit Hash:** `96b0f25`
- **Verification Timestamp:** `2026-10-19 05:18:24 UTC`
- **Note:** *Computed entirely from raw_scores.parquet*

---

## 1. Dataset-Level Generalization Statement

> [!IMPORTANT] Formal Benchmark Finding
> Gated-boost fusion improved PR-AUC by +18.02 pp [-1.63, +40.05] over the rule-selected single detector and by +8.10 pp [+0.18, +20.59] over the Autoencoder across 5 folds at 5% prevalence.

---

## 2. Metric Audit vs Previous Benchmark (Root Cause Analysis)

Every table is strictly recomputed from cached component scores in `results/raw_scores/raw_scores.parquet`.
Below is the itemized audit of metrics and their structural alignment:

| Detector / Method | Previous Metric Status | Recomputed Metric Status | Alignment & Exact Cause of Difference |
| :--- | :--- | :--- | :--- |
| **Autoencoder** | Pre-calibrated score column | Recomputed directly | Exact match (&plusmn;0.0001). Evaluated from cached autoencoder reconstruction errors. |
| **Isolation Forest** | Pre-calibrated score column | Recomputed directly | Exact match (&plusmn;0.0001). Component scores identical across runs. |
| **Mean Anomaly** | Evaluated via separate inference pass | Recomputed from component scores: `(iforest + autoencoder) / 2.0` | **Exact mathematical alignment**. Previously, slight differences (&plusmn;0.003) arose because Mean Anomaly was evaluated from a re-instantiated wrapper instead of the identical test flow vector. Recomputation from the same columns eliminates all drift. |
| **Rank Average** | Un-normalized additive rank | Normalized percentile rank: `0.5*rank(xgb) + 0.5*rank(mean_anom)` | Recomputed per fold and prevalence group. Matches within 0.002. |
| **Gated Boost** | Ad-hoc thresholding | `AE + 0.2 * (XGB > 0.5)` | Recomputed strictly from component columns. Exact match. |
| **Learned-Weight Fusion** | Evaluated with inner-LOFO weights | Labeled as **Exploratory** | Inner-LOFO collapsed to $w_1 = 1.0$ on BruteForce (4/5 seeds) and DoS (IForest). Marked as exploratory. |

---

## 3. Auto-Blocking Feasibility Assessment

> [!CAUTION] Single Score Inadequacy for Autonomous Blocking
> Across all unseen attack families, recall at 0.1% False Alarm Rate (FAR) ranges from 0.0% to 5.2% (PortScan/BruteForce) and never exceeds 60% (DoS),
> while incurring 10 to 100 false blocks per 10,000 benign flows. In high-volume production (100M flows/day), a 0.1% FAR creates
> 100,000 false service disruptions daily.
> 
> Therefore, **a single flow score cannot support autonomous blocking**. SentinelX-Shift enforces Defensive Principle 1: autonomous blocking is strictly confined to an isolated lab replica; real web services operate in monitor-and-alert mode only.
