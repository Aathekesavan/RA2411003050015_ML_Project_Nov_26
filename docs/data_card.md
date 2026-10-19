# SentinelX-Shift Data Card: Complete CIC-IDS2017 Family Groups Sample

**Version**: 2.0.0-complete-family-groups  
**Generated Date**: 2026-10-19 07:44:36  
**Deterministic Seed**: `42`  
**Dataset Provenance**: All 8 raw partitions of the official CIC-IDS2017 benchmark loaded (2,830,743 raw flows).  
**Family Groups Protocol**: Grouped into `['Bot', 'BruteForce', 'DoS_DDoS', 'PortScan', 'WebAttack']`. Infiltration (36 flows) skipped (< 500 unique flows).  
**Sampling Strategy**: 100% retention of all rare family groups (`<20,000` unique flows); proportional subsampling of `Benign` and `DoS_DDoS` to ~65,000 total.  
**Primary Artifact**: [`data/processed/cicids2017_sample60k.parquet`](file:///D:/sentinelx/data/processed/cicids2017_sample60k.parquet)  
**Feature Count**: 76 behavioral netflow features (all leaky identifiers stripped)  

---

## 1. Raw Files Ingestion & Row Counts

Every raw partition provided in the official CIC-IDS2017 distribution was loaded:

| Raw Partition File | Loaded Row Count |
| :--- | :--- |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv.parquet` | 225,745 |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv.parquet` | 286,467 |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv.parquet` | 191,033 |
| `Monday-WorkingHours.pcap_ISCX.csv.parquet` | 529,918 |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv.parquet` | 288,602 |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv.parquet` | 170,366 |
| `Tuesday-WorkingHours.pcap_ISCX.csv.parquet` | 445,909 |
| `Wednesday-workingHours.pcap_ISCX.csv.parquet` | 692,703 |
| **Total Ingested Raw Flows** | **2,830,743** |

---

## 2. Ingested Partitions & Deduplication Audit

| Metric | Count | Description |
| :--- | :--- | :--- |
| **Raw Input Rows Loaded** | 2,827,840 | Loaded from all 8 raw partition files |
| **Duplicates Removed** | 594,712 | Exact full-vector duplicates removed (21.03%) |
| **Rows After Deduplication** | 2,233,128 | Unique behavioral flow feature vectors |
| **Final Sampled Rows** | 60,000 | Rare-preserved benchmark sample saved to parquet |
| **Feature Dimensions** | 76 | Extracted behavioral features (ports, IPs, timestamps removed) |

### 2.1 Per-Family-Group Breakdown

| Family Group | Raw Rows | Unique Rows (Dedup) | Duplication Rate (%) | Final Sample Rows | Final Proportion (%) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `Benign` | 2,271,320 | 1,896,672 | 16.49% | 38,742 | 64.57% |
| `Bot` | 1,956 | 1,437 | 26.53% | 1,437 | 2.40% |
| `BruteForce` | 13,832 | 9,150 | 33.85% | 9,150 | 15.25% |
| `DoS_DDoS` | 379,748 | 321,770 | 15.27% | 6,572 | 10.95% |
| `PortScan` | 158,804 | 1,956 | 98.77% | 1,956 | 3.26% |
| `WebAttack` | 2,180 | 2,143 | 1.70% | 2,143 | 3.57% |
| **Total** | **2,827,840** | **2,233,128** | **21.03%** | **60,000** | **100.00%** |

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

- **Measured Test Accuracy**: `99.3278%`
- **Measured Macro F1-Score**: `0.9855`
- **Test Sample Size**: `18,000` flows (Train: `42,000` flows)

```text
Classification Report:
              precision    recall  f1-score   support

      Benign     0.9922    0.9983    0.9952     11622
         Bot     0.9784    0.9466    0.9623       431
  BruteForce     1.0000    0.9920    0.9960      2745
    DoS_DDoS     0.9949    0.9848    0.9898      1972
    PortScan     0.9864    0.9864    0.9864       587
   WebAttack     0.9952    0.9720    0.9835       643

    accuracy                         0.9933     18000
   macro avg     0.9912    0.9800    0.9855     18000
weighted avg     0.9933    0.9933    0.9933     18000

```

---

## 4. Multi-Decimal Contrast Leakage Audit Across the 5 Family Groups

> [!IMPORTANT]
> **Primary Metric**: **3-decimal near-duplicate leakage** (`3dec`) represents true protocol-level flow vector collision.  
> All LOFO matches are decomposed into matches to **benign training flows** vs matches to **other attack families**.

| Family | Rand_Near_Leakage_3dec_Pct | LOFO_Near_Leakage_3dec_Pct | LOFO_Matches_Benign_3dec_Pct | LOFO_Matches_OtherAttacks_3dec_Pct | Rand_Log1p_Near_Leakage_3dec_Pct | LOFO_Log1p_Near_Leakage_3dec_Pct | Rand_Near_Leakage_2dec_Pct | LOFO_Near_Leakage_2dec_Pct | LOFO_Exact_Leakage_Pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DoS_DDoS | 29.2089 | 3.941 | 3.941 | 1.4912 | 1.927 | 0.4869 | 55.9331 | 9.8448 | 0.0 |
| BruteForce | 57.1585 | 1.7705 | 1.1038 | 1.5738 | 0.4736 | 0.0 | 99.2714 | 2.8634 | 0.0 |
| PortScan | 93.5264 | 6.6973 | 6.4928 | 3.3231 | 3.9182 | 0.0 | 97.4446 | 39.7239 | 0.0 |
| Bot | 89.0951 | 38.483 | 38.483 | 0.0 | 1.6241 | 0.1392 | 94.8956 | 51.4962 | 0.0 |
| WebAttack | 94.8678 | 55.0163 | 51.1433 | 14.1391 | 12.7527 | 0.0 | 97.9782 | 89.4074 | 0.0 |

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
   - *Problem*: Raw labels contain `\ufffd` or Windows-1252 byte corruption in Web Attack names.
   - *Mitigation*: Unified under canonical mapping.
