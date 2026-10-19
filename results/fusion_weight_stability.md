## Per-Seed Inner-LOFO Fusion Weights

| Seed | Family | w1_mean | w2_mean | w1_iforest | w2_iforest | w1_ae | w2_ae | gated_t | gated_boost | rule_selected_single_seed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | DoS | 0.55 | 0.45 | 1.0 | 0.0 | 0.55 | 0.45 | 0.5 | 0.1 | Autoencoder |
| 42 | PortScan | 0.4 | 0.6 | 0.15 | 0.85 | 0.2 | 0.8 | 0.5 | 0.1 | Mean_Anomaly |
| 42 | BruteForce | 0.65 | 0.35 | 0.5 | 0.5 | 0.7 | 0.3 | 0.5 | 0.2 | Autoencoder |
| 101 | DoS | 0.6 | 0.4 | 1.0 | 0.0 | 0.6 | 0.4 | 0.5 | 0.2 | Mean_Anomaly |
| 101 | PortScan | 0.35 | 0.65 | 0.45 | 0.55 | 0.3 | 0.7 | 0.5 | 0.1 | Mean_Anomaly |
| 101 | BruteForce | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Mean_Anomaly |
| 202 | DoS | 0.7 | 0.3 | 1.0 | 0.0 | 0.65 | 0.35 | 0.5 | 0.1 | Autoencoder |
| 202 | PortScan | 0.45 | 0.55 | 0.35 | 0.65 | 0.5 | 0.5 | 0.6 | 0.3 | Mean_Anomaly |
| 202 | BruteForce | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.5 | 0.5 | 0.2 | Autoencoder |
| 303 | DoS | 0.5 | 0.5 | 0.45 | 0.55 | 1.0 | 0.0 | 0.5 | 0.3 | Isolation_Forest |
| 303 | PortScan | 0.45 | 0.55 | 0.4 | 0.6 | 0.45 | 0.55 | 0.5 | 0.2 | Isolation_Forest |
| 303 | BruteForce | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Isolation_Forest |
| 404 | DoS | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.2 | Isolation_Forest |
| 404 | PortScan | 0.55 | 0.45 | 0.1 | 0.9 | 0.25 | 0.75 | 0.5 | 0.1 | Mean_Anomaly |
| 404 | BruteForce | 1.0 | 0.0 | 0.95 | 0.05 | 1.0 | 0.0 | 0.5 | 0.3 | Isolation_Forest |

## Fusion-Weight Variability & Degenerate Tuning Summary

| Family | Fusion_Signal | Mean_w1 | Mean_w2 | Extreme_Seeds_Count (w1=1.0 or w2=1.0) | Tuning_Status |
| --- | --- | --- | --- | --- | --- |
| DoS | XGB + Mean_Anomaly | 0.67 +/- 0.18 | 0.33 +/- 0.18 | 1/5 | Stable |
| DoS | XGB + IForest | 0.89 +/- 0.22 | 0.11 +/- 0.22 | 4/5 | Degenerate Tuning |
| DoS | XGB + Autoencoder | 0.76 +/- 0.20 | 0.24 +/- 0.20 | 2/5 | Stable |
| PortScan | XGB + Mean_Anomaly | 0.44 +/- 0.07 | 0.56 +/- 0.07 | 0/5 | Stable |
| PortScan | XGB + IForest | 0.29 +/- 0.14 | 0.71 +/- 0.14 | 0/5 | Stable |
| PortScan | XGB + Autoencoder | 0.34 +/- 0.12 | 0.66 +/- 0.12 | 0/5 | Stable |
| BruteForce | XGB + Mean_Anomaly | 0.93 +/- 0.14 | 0.07 +/- 0.14 | 4/5 | Degenerate Tuning |
| BruteForce | XGB + IForest | 0.89 +/- 0.20 | 0.11 +/- 0.20 | 3/5 | Degenerate Tuning |
| BruteForce | XGB + Autoencoder | 0.84 +/- 0.21 | 0.16 +/- 0.21 | 3/5 | Degenerate Tuning |