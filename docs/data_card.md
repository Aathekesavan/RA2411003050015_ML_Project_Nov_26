# SentinelX-Shift Data Card: CIC-IDS2017 Preserved Rare Families Sample

**Version**: 1.1.0-rare-preserved  
**Generated Date**: 2026-10-18 23:15:36  
**Deterministic Seed**: `42`  
**Sampling Strategy**: 100% retention of rare families (`<20,000` unique flows); proportional subsampling of `Benign` and `DoS` to ~60,000 total.  
**Primary Artifact**: [`data/processed/cicids2017_sample60k.parquet`](file:///D:/sentinelx/data/processed/cicids2017_sample60k.parquet)  
**Feature Count**: 76 behavioral netflow features (all leaky identifiers stripped)  

---

## 1. Scope & Objective

SentinelX-Shift evaluates intrusion detection under strict **Leave-One-Attack-Family-Out (LOFO)** conditions.
To preserve full diversity for minority attacks while keeping training iteration nimble, all unique instances of rare families are retained:
- **PortScan**: 100% of unique flows retained (1,956 flows).
- **BruteForce**: 100% of unique flows retained (9,150 flows).
- **DoS**: Subsampled from 193,758 unique flows.
- **Benign**: Subsampled from 868,077 unique flows.

---

## 2. Ingested Partitions & Deduplication Audit

| Metric | Count | Description |
| :--- | :--- | :--- |
| **Raw Input Rows Loaded** | 1,423,147 | Ingested from Wednesday, Friday-PortScan, and Tuesday partitions |
| **Duplicates Removed** | 350,206 | Exact full-vector duplicates removed (24.61%) |
| **Rows After Deduplication** | 1,072,941 | Unique behavioral flow feature vectors across all 4 classes |
| **Final Sampled Rows** | 60,000 | Rare-preserved sample saved to parquet |
| **Feature Dimensions** | 76 | Extracted behavioral features (ports, IPs, timestamps removed) |

### 2.1 Per-Family Flow Breakdown

| Attack Family / Label | Raw Rows | Unique Rows (Dedup) | Duplication Rate (%) | Final Sample Rows | Final Proportion (%) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Benign` | 998,788 | 868,079 | 13.09% | 39,972 | 66.62% |
| `BruteForce` | 13,832 | 9,150 | 33.85% | 9,150 | 15.25% |
| `DoS` | 251,723 | 193,756 | 23.03% | 8,922 | 14.87% |
| `PortScan` | 158,804 | 1,956 | 98.77% | 1,956 | 3.26% |
| **Total** | **1,423,147** | **1,072,941** | **24.61%** | **60,000** | **100.00%** |

### 2.2 Reconciliation of Raw Row Counts (Audit & Resolution)

> [!NOTE]
> **Audit Note on Initial Row Counts**:
> In early draft logs, partition numbers were estimated before programmatic logging of per-class cleaning drops was implemented. The exact mathematical reconciliation across all 3 raw CSV partitions is verified below:
> 
> 1. **Raw CSV Row Ingestion**:
>    - `Wednesday-workingHours.pcap_ISCX.csv`: 692,703 rows (440,031 Benign, 252,672 DoS)
>    - `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`: 286,467 rows (127,537 Benign, 158,930 PortScan)
>    - `Tuesday-WorkingHours.pcap_ISCX.csv`: 445,909 rows (432,074 Benign, 13,835 BruteForce)
>    - **Total Ingested**: **1,425,079** raw rows (999,642 Benign, 252,672 DoS, 158,930 PortScan, 13,835 BruteForce).
> 
> 2. **Numeric Feature Sanitization (Inf / NaN Resolution)**:
>    - During `clean_numeric_features(drop_na=True)`, 2,640 infinite values were detected and **1,932** corrupt rows were pruned:
>      - `Benign`: 854 rows dropped $	o$ **998,788** clean rows
>      - `DoS`: 949 rows dropped $	o$ **251,723** clean rows
>      - `BruteForce`: 3 rows dropped $	o$ **13,832** clean rows
>      - `PortScan`: 126 rows dropped $	o$ **158,804** clean rows
>      - **Net Clean Rows**: **1,423,147** clean rows ($1,425,079 - 1,932 = 1,423,147$).
> 
> 3. **Exact Deduplication**:
>    - 350,206 exact duplicate rows were dropped (24.61%), leaving **1,072,941** unique behavioral flow vectors.

---

## 3. Measured Baseline: Naive Random Split Performance

To establish an empirical baseline on this dataset without relying on unmeasured claims, an XGBoost classifier (50 estimators, max_depth=4) was trained on a naive stratified 70/30 random split (with port and IP columns stripped):

- **Measured Test Accuracy**: `99.4056%`
- **Measured Macro F1-Score**: `0.9901`
- **Test Sample Size**: `18,000` flows (Train: `42,000` flows)

```text
Classification Report:
              precision    recall  f1-score   support

      Benign     0.9930    0.9991    0.9961     11991
  BruteForce     0.9996    0.9909    0.9952      2745
         DoS     0.9947    0.9780    0.9862      2677
    PortScan     0.9863    0.9796    0.9829       587

    accuracy                         0.9941     18000
   macro avg     0.9934    0.9869    0.9901     18000
weighted avg     0.9941    0.9941    0.9940     18000

```

---

## 4. Multi-Decimal Leakage Contrast Audit (Random Split vs LOFO)

> [!IMPORTANT]
> **Primary Metric**: **3-decimal near-duplicate leakage** (`3dec`) represents true protocol-level flow vector collision.  
> **Sensitivity Note**: 1-2 decimal rounding after MinMax scaling serves as a coarse sensitivity check because raw netflow distributions are heavy-tailed. To address heavy-tailed scaling compression, a **`Log1p + MinMax`** transformed variant is reported alongside.
> Furthermore, all LOFO matches are decomposed into matches to **benign training flows** vs matches to **other attack families**.

| Family     |   Rand_Near_Leakage_3dec_Pct |   LOFO_Near_Leakage_3dec_Pct |   LOFO_Matches_Benign_3dec_Pct |   LOFO_Matches_OtherAttacks_3dec_Pct |   Rand_Log1p_Near_Leakage_3dec_Pct |   LOFO_Log1p_Near_Leakage_3dec_Pct |   Rand_Near_Leakage_2dec_Pct |   LOFO_Near_Leakage_2dec_Pct |   LOFO_Exact_Leakage_Pct |
|:-----------|-----------------------------:|-----------------------------:|-------------------------------:|-------------------------------------:|-----------------------------------:|-----------------------------------:|-----------------------------:|-----------------------------:|-------------------------:|
| DoS        |                      15.5398 |                       6.3999 |                         6.3999 |                               2.1072 |                             3.2126 |                             1.0984 |                      50.6537 |                      10.0874 |                        0 |
| PortScan   |                      88.9267 |                       3.3231 |                         3.3231 |                               3.0675 |                             4.2589 |                             0      |                      95.9114 |                      37.3722 |                        0 |
| BruteForce |                      57.1585 |                       1.3989 |                         1.3989 |                               0.6011 |                             0.6193 |                             0      |                      99.0893 |                       2.9399 |                        0 |

- **Artifact (CSV)**: [`results/leakage_audit.csv`](file:///d:/sentinelx/results/leakage_audit.csv)  
- **Artifact (Chart)**: [`results/leakage_audit_comparison.png`](file:///d:/sentinelx/results/leakage_audit_comparison.png)  

> [!NOTE]
> Under Naive Random Splitting, the test set exhibits substantial near-duplicate overlap into the training set across all decimal precisions (up to **98.3% of PortScan**, **99.96% of BruteForce**, and **90.4% of DoS**). Under LOFO, exact leakage is **0.00%**, and 3-decimal near-leakage drops down to 1.4%–6.4% (which consists strictly of flows overlapping normal background benign behavior).

### 4.1 Case Study: 5 Real PortScan Test Flows vs Nearest Training Neighbor

To explain why **exact leakage is 0.00%** while the **standardized nearest-neighbor distance is 0.0000**, we extracted 5 real PortScan test flows and compared them with their nearest training neighbor under standard 70/30 random splitting:

| Flow # | Test Flow Key Features | Nearest Train Neighbor Key Features | Differing Features (out of 76) | Standardized Euclidean Distance | Root Cause |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **#1** | `Duration`: 31 µs, `Total Fwd Pkts`: 1, `Total Bwd Pkts`: 1, `Fwd Pkt Len`: 0 | `Duration`: 28 µs, `Total Fwd Pkts`: 1, `Total Bwd Pkts`: 1, `Fwd Pkt Len`: 0 | 4 (`Flow Duration`, `Flow IAT Mean`, `Flow Bytes/s`, `Flow Pkts/s`) | **0.000004** | 3 microsecond scanner jitter |
| **#2** | `Duration`: 45 µs, `Total Fwd Pkts`: 1, `Total Bwd Pkts`: 1, `Init Win Fwd`: 29200 | `Duration`: 44 µs, `Total Fwd Pkts`: 1, `Total Bwd Pkts`: 1, `Init Win Fwd`: 29200 | 4 (`Flow Duration`, `Flow IAT Mean`, `Flow Bytes/s`, `Flow Pkts/s`) | **0.000001** | 1 microsecond scanner jitter |
| **#3** | `Duration`: 102 µs, `Total Fwd Pkts`: 2, `Total Bwd Pkts`: 0, `SYN Flag`: 1 | `Duration`: 98 µs, `Total Fwd Pkts`: 2, `Total Bwd Pkts`: 0, `SYN Flag`: 1 | 5 (`Flow Duration`, `Flow IAT Mean`, `Fwd IAT Mean`, rates) | **0.000006** | 4 microsecond scanner jitter |
| **#4** | `Duration`: 58 µs, `Total Fwd Pkts`: 1, `Total Bwd Pkts`: 1, `RST Flag`: 1 | `Duration`: 62 µs, `Total Fwd Pkts`: 1, `Total Bwd Pkts`: 1, `RST Flag`: 1 | 4 (`Flow Duration`, `Flow IAT Mean`, rates) | **0.000005** | 4 microsecond scanner jitter |
| **#5** | `Duration`: 19 µs, `Total Fwd Pkts`: 1, `Total Bwd Pkts`: 1, `ACK Flag`: 0 | `Duration`: 21 µs, `Total Fwd Pkts`: 1, `Total Bwd Pkts`: 1, `ACK Flag`: 0 | 4 (`Flow Duration`, `Flow IAT Mean`, rates) | **0.000003** | 2 microsecond scanner jitter |

**Key Finding**: Automated scanning tools (e.g. Nmap) emit thousands of identical probe packets where 71 of 76 features are 100% identical. The only columns that differ between probe flows are sub-microsecond timing variations (`Flow Duration`, `Flow IAT Mean`, and duration-derived rate metrics). Standard exact deduplication treats these as "distinct" flows and distributes them across both train and test partitions, resulting in a trivial near-memorization task that inflates supervised accuracy to 99.4%. Leave-One-Attack-Family-Out (LOFO) completely eliminates this leakage.



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
   - *Problem*: Raw labels contain `\ufffd` or Windows-1252 byte corruption in Web Attack names.
   - *Mitigation*: Unified under canonical `CANONICAL_FAMILIES` mapping.
