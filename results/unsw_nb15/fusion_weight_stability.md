## Per-Seed Inner-LOFO Fusion Weights (UNSW-NB15)

| Seed | Family_Group | w1_mean | w2_mean | w1_iforest | w2_iforest | w1_ae | w2_ae | gated_t | gated_boost | rule_selected_single_seed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | Recon_Analysis | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.6 | 0.3 | Autoencoder |
| 42 | Exploit_Payload | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 42 | Fuzzers | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 42 | DoS | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.6 | 0.3 | Autoencoder |
| 42 | Generic | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 101 | Recon_Analysis | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Mean_Anomaly |
| 101 | Exploit_Payload | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 101 | Fuzzers | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 101 | DoS | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Mean_Anomaly |
| 101 | Generic | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 202 | Recon_Analysis | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 202 | Exploit_Payload | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 202 | Fuzzers | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 202 | DoS | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 202 | Generic | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 303 | Recon_Analysis | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 303 | Exploit_Payload | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 303 | Fuzzers | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.6 | 0.3 | Autoencoder |
| 303 | DoS | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 303 | Generic | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |
| 404 | Recon_Analysis | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Mean_Anomaly |
| 404 | Exploit_Payload | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Mean_Anomaly |
| 404 | Fuzzers | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Mean_Anomaly |
| 404 | DoS | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Mean_Anomaly |
| 404 | Generic | 1.0 | 0.0 | 1.0 | 0.0 | 1.0 | 0.0 | 0.5 | 0.3 | Autoencoder |

## Fusion-Weight Variability & Degenerate Tuning Summary (UNSW-NB15)

| Family_Group | Fusion_Signal | Mean_w1 | Mean_w2 | Extreme_Seeds_Count (w1=1.0 or w2=1.0) | Tuning_Status |
| --- | --- | --- | --- | --- | --- |
| Recon_Analysis | XGB + Mean_Anomaly | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| Recon_Analysis | XGB + IForest | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| Recon_Analysis | XGB + Autoencoder | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| Exploit_Payload | XGB + Mean_Anomaly | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| Exploit_Payload | XGB + IForest | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| Exploit_Payload | XGB + Autoencoder | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| Fuzzers | XGB + Mean_Anomaly | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| Fuzzers | XGB + IForest | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| Fuzzers | XGB + Autoencoder | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| DoS | XGB + Mean_Anomaly | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| DoS | XGB + IForest | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| DoS | XGB + Autoencoder | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| Generic | XGB + Mean_Anomaly | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| Generic | XGB + IForest | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |
| Generic | XGB + Autoencoder | 1.00 +/- 0.00 | 0.00 +/- 0.00 | 5/5 | Degenerate Tuning |