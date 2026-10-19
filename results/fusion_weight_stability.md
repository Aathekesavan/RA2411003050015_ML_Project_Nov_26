## Per-Seed Inner-LOFO Fusion Weights

| Seed | Family | w1_mean | w2_mean | w1_iforest | w2_iforest | w1_ae | w2_ae | tau_gated | gamma_gated | rule_selected_single_seed | inner_folds_count | inner_folds_status | val_pr_auc_ae | val_pr_auc_rank_avg | val_pr_auc_gated_boost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | DoS_DDoS | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.3 | Isolation_Forest | 4 | Normal (4 inner folds) | 0.3847 | 0.0 | 0.0 |
| 42 | BruteForce | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Isolation_Forest | 4 | Normal (4 inner folds) | 0.3461 | 0.0 | 0.0 |
| 42 | PortScan | 0.55 | 0.45 | 0.95 | 0.05 | 0.55 | 0.45 | 0.3 | 0.3 | Mean_Anomaly | 4 | Normal (4 inner folds) | 0.5003 | 0.0 | 0.0 |
| 42 | Bot | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Mean_Anomaly | 4 | Normal (4 inner folds) | 0.4933 | 0.0 | 0.0 |
| 42 | WebAttack | 0.4 | 0.6 | 1.0 | 0.0 | 0.4 | 0.6 | 0.3 | 0.2 | Autoencoder | 4 | Normal (4 inner folds) | 0.5767 | 0.0 | 0.0 |
| 101 | DoS_DDoS | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.3 | Mean_Anomaly | 4 | Normal (4 inner folds) | 0.3996 | 0.0 | 0.0 |
| 101 | BruteForce | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder | 4 | Normal (4 inner folds) | 0.4818 | 0.0 | 0.0 |
| 101 | PortScan | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.2 | Mean_Anomaly | 4 | Normal (4 inner folds) | 0.5247 | 0.0 | 0.0 |
| 101 | Bot | 0.4 | 0.6 | 1.0 | 0.0 | 0.45 | 0.55 | 0.5 | 0.2 | Autoencoder | 4 | Normal (4 inner folds) | 0.5678 | 0.0 | 0.0 |
| 101 | WebAttack | 0.35 | 0.65 | 1.0 | 0.0 | 0.4 | 0.6 | 0.3 | 0.3 | Autoencoder | 4 | Normal (4 inner folds) | 0.6072 | 0.0 | 0.0 |
| 202 | DoS_DDoS | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.3 | Isolation_Forest | 4 | Normal (4 inner folds) | 0.3672 | 0.0 | 0.0 |
| 202 | BruteForce | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.3 | Isolation_Forest | 4 | Normal (4 inner folds) | 0.4461 | 0.0 | 0.0 |
| 202 | PortScan | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.3 | Isolation_Forest | 4 | Normal (4 inner folds) | 0.499 | 0.0 | 0.0 |
| 202 | Bot | 0.4 | 0.6 | 1.0 | 0.0 | 0.35 | 0.65 | 0.5 | 0.3 | Mean_Anomaly | 4 | Normal (4 inner folds) | 0.588 | 0.0 | 0.0 |
| 202 | WebAttack | 0.35 | 0.65 | 1.0 | 0.0 | 0.3 | 0.7 | 0.3 | 0.3 | Autoencoder | 4 | Normal (4 inner folds) | 0.621 | 0.0 | 0.0 |
| 303 | DoS_DDoS | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.3 | Mean_Anomaly | 4 | Normal (4 inner folds) | 0.4533 | 0.0 | 0.0 |
| 303 | BruteForce | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Mean_Anomaly | 4 | Normal (4 inner folds) | 0.4782 | 0.0 | 0.0 |
| 303 | PortScan | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.3 | Mean_Anomaly | 4 | Normal (4 inner folds) | 0.5517 | 0.0 | 0.0 |
| 303 | Bot | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.3 | Autoencoder | 4 | Normal (4 inner folds) | 0.5642 | 0.0 | 0.0 |
| 303 | WebAttack | 0.65 | 0.35 | 1.0 | 0.0 | 0.6 | 0.4 | 0.3 | 0.1 | Autoencoder | 4 | Normal (4 inner folds) | 0.6275 | 0.0 | 0.0 |
| 404 | DoS_DDoS | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.3 | Isolation_Forest | 4 | Normal (4 inner folds) | 0.3722 | 0.0 | 0.0 |
| 404 | BruteForce | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.3 | Mean_Anomaly | 4 | Normal (4 inner folds) | 0.4776 | 0.0 | 0.0 |
| 404 | PortScan | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.3 | Mean_Anomaly | 4 | Normal (4 inner folds) | 0.5274 | 0.0 | 0.0 |
| 404 | Bot | 0.4 | 0.6 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Mean_Anomaly | 4 | Normal (4 inner folds) | 0.5595 | 0.0 | 0.0 |
| 404 | WebAttack | 0.4 | 0.6 | 1.0 | 0.0 | 1.0 | 0.0 | 0.3 | 0.3 | Autoencoder | 4 | Normal (4 inner folds) | 0.5216 | 0.0 | 0.0 |

## Fusion-Weight Variability & Degenerate Tuning Summary

| Family | Fusion_Signal | Mean_w1 | Mean_w2 | Extreme_Seeds_Count (w1=1.0 or w2=1.0) | Tuning_Status |
| --- | --- | --- | --- | --- | --- |
| DoS_DDoS | XGB + Mean_Anomaly | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| DoS_DDoS | XGB + IForest | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| DoS_DDoS | XGB + Autoencoder | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| BruteForce | XGB + Mean_Anomaly | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| BruteForce | XGB + IForest | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| BruteForce | XGB + Autoencoder | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| PortScan | XGB + Mean_Anomaly | 0.91 +/- 0.18 | 0.09 +/- 0.18 | 4/5 | Degenerate Tuning |
| PortScan | XGB + IForest | 0.99 +/- 0.02 | 0.01 +/- 0.02 | 4/5 | Degenerate Tuning |
| PortScan | XGB + Autoencoder | 0.91 +/- 0.18 | 0.09 +/- 0.18 | 4/5 | Degenerate Tuning |
| Bot | XGB + Mean_Anomaly | 0.64 +/- 0.29 | 0.36 +/- 0.29 | 2/5 | Stable |
| Bot | XGB + IForest | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| Bot | XGB + Autoencoder | 0.76 +/- 0.30 | 0.24 +/- 0.30 | 3/5 | Degenerate Tuning |
| WebAttack | XGB + Mean_Anomaly | 0.43 +/- 0.11 | 0.57 +/- 0.11 | 0/5 | Stable |
| WebAttack | XGB + IForest | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| WebAttack | XGB + Autoencoder | 0.54 +/- 0.25 | 0.46 +/- 0.25 | 1/5 | Stable |