# SentinelX-Shift Fusion vs Reference Single Detectors Comparison

- **Run ID:** `run_20261019_99c9f0a`
- **Git Commit Hash:** `99c9f0a`
- **Date:** `2026-10-19 06:25:21 UTC`
- **Raw Scores Row Count:** `4,131,380`
- **Seed Count:** `5`
- **Note:** *Computed entirely from raw_scores.parquet*

> [!NOTE] Dataset-Level Generalization Gain
> Gated-boost fusion improved PR-AUC by +18.02 pp [-1.63, +40.05] over the rule-selected single detector and by +8.10 pp [+0.18, +20.59] over the Autoencoder across 5 folds at 5% prevalence.

| Family | Prevalence | Rule_Selected_Detector | Method | Delta_ROC_vs_Rule_pp | 95% CI (vs Rule ROC pp) | Delta_PR_vs_Rule_pp | 95% CI (vs Rule PR pp) | Delta_ROC_vs_AE_pp | 95% CI (vs AE ROC pp) | Delta_PR_vs_AE_pp | 95% CI (vs AE PR pp) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bot | 1.0% | Mean_Anomaly | Supervised_XGBoost | +2.44 | [-9.20, +4.43] | -0.41 | [-1.85, +0.43] | +2.70 | [-8.37, +4.49] | +0.41 | [-0.50, +0.98] |
| Bot | 1.0% | Mean_Anomaly | Fusion_XGB_Mean_Anomaly [Exploratory] | -10.68 | [-17.47, -5.54] | -0.89 | [-1.80, -0.21] | -10.42 | [-17.36, -5.51] | -0.07 | [-0.61, +0.58] |
| Bot | 1.0% | Mean_Anomaly | Fusion_XGB_IForest [Exploratory] | +2.44 | [-9.20, +4.43] | -0.41 | [-1.85, +0.43] | +2.70 | [-8.37, +4.49] | +0.41 | [-0.50, +0.98] |
| Bot | 1.0% | Mean_Anomaly | Fusion_XGB_AE [Exploratory] | -9.73 | [-16.84, -4.64] | -1.43 | [-2.53, -0.60] | -9.47 | [-16.56, -4.69] | -0.61 | [-1.20, -0.04] |
| Bot | 1.0% | Mean_Anomaly | Baseline_Rank_Average_0.5_0.5 | +7.72 | [+4.49, +10.68] | +0.68 | [-0.16, +1.61] | +7.99 | [+5.18, +10.66] | +1.49 | [+0.77, +2.50] |
| Bot | 1.0% | Mean_Anomaly | Baseline_Anomaly_Heavy_0.2_0.8 | +2.63 | [+1.66, +3.52] | +1.07 | [+0.16, +2.50] | +2.90 | [+1.71, +4.07] | +1.89 | [+0.84, +3.56] |
| Bot | 1.0% | Mean_Anomaly | Ablation_Gated_Boost_AE_plus_XGB | -0.32 | [-1.57, +1.01] | -0.83 | [-1.47, -0.41] | -0.05 | [-0.08, -0.03] | -0.02 | [-0.03, -0.01] |
| Bot | 5.0% | Mean_Anomaly | Supervised_XGBoost | +2.42 | [-4.84, +0.96] | -1.21 | [-3.87, +0.11] | +2.72 | [-4.45, +1.07] | +1.72 | [-0.30, +2.50] |
| Bot | 5.0% | Mean_Anomaly | Fusion_XGB_Mean_Anomaly [Exploratory] | -10.61 | [-14.02, -8.69] | -3.53 | [-5.02, -2.35] | -10.31 | [-13.54, -8.52] | -0.60 | [-1.61, +0.41] |
| Bot | 5.0% | Mean_Anomaly | Fusion_XGB_IForest [Exploratory] | +2.42 | [-4.84, +0.96] | -1.21 | [-3.87, +0.11] | +2.72 | [-4.45, +1.07] | +1.72 | [-0.30, +2.50] |
| Bot | 5.0% | Mean_Anomaly | Fusion_XGB_AE [Exploratory] | -9.72 | [-13.34, -7.79] | -5.62 | [-7.43, -4.19] | -9.42 | [-13.03, -7.58] | -2.69 | [-3.75, -1.72] |
| Bot | 5.0% | Mean_Anomaly | Baseline_Rank_Average_0.5_0.5 | +7.87 | [+6.53, +9.16] | +2.92 | [+1.55, +4.43] | +8.17 | [+6.89, +9.35] | +5.86 | [+4.62, +7.31] |
| Bot | 5.0% | Mean_Anomaly | Baseline_Anomaly_Heavy_0.2_0.8 | +2.64 | [+2.23, +3.05] | +3.66 | [+2.31, +5.35] | +2.93 | [+2.42, +3.48] | +6.59 | [+5.01, +8.66] |
| Bot | 5.0% | Mean_Anomaly | Ablation_Gated_Boost_AE_plus_XGB | -0.35 | [-0.91, +0.25] | -3.00 | [-3.91, -2.27] | -0.05 | [-0.08, -0.03] | -0.07 | [-0.12, -0.03] |
| BruteForce | 1.0% | Mean_Anomaly | Supervised_XGBoost | +7.17 | [+3.90, +10.40] | +3.86 | [+2.76, +5.71] | +10.65 | [+7.23, +14.14] | +4.36 | [+3.20, +6.31] |
| BruteForce | 1.0% | Mean_Anomaly | Fusion_XGB_Mean_Anomaly [Exploratory] | +7.17 | [+3.90, +10.40] | +3.86 | [+2.76, +5.71] | +10.65 | [+7.23, +14.14] | +4.36 | [+3.20, +6.31] |
| BruteForce | 1.0% | Mean_Anomaly | Fusion_XGB_IForest [Exploratory] | +7.17 | [+3.90, +10.40] | +3.86 | [+2.76, +5.71] | +10.65 | [+7.23, +14.14] | +4.36 | [+3.20, +6.31] |
| BruteForce | 1.0% | Mean_Anomaly | Fusion_XGB_AE [Exploratory] | +7.17 | [+3.90, +10.40] | +3.86 | [+2.76, +5.71] | +10.65 | [+7.23, +14.14] | +4.36 | [+3.20, +6.31] |
| BruteForce | 1.0% | Mean_Anomaly | Baseline_Rank_Average_0.5_0.5 | +10.90 | [+9.15, +12.60] | +7.77 | [+5.87, +10.21] | +14.38 | [+12.33, +16.35] | +8.27 | [+6.27, +10.82] |
| BruteForce | 1.0% | Mean_Anomaly | Baseline_Anomaly_Heavy_0.2_0.8 | +6.68 | [+5.98, +7.26] | +2.72 | [+1.94, +3.76] | +10.16 | [+9.13, +11.14] | +3.22 | [+2.33, +4.40] |
| BruteForce | 1.0% | Mean_Anomaly | Ablation_Gated_Boost_AE_plus_XGB | -3.42 | [-4.15, -2.64] | -0.45 | [-0.64, +0.12] | +0.06 | [-0.09, +0.34] | +0.05 | [-0.01, +0.60] |
| BruteForce | 5.0% | Mean_Anomaly | Supervised_XGBoost | +7.10 | [+5.63, +8.74] | +13.56 | [+11.78, +16.26] | +10.58 | [+9.05, +12.35] | +15.62 | [+13.72, +18.32] |
| BruteForce | 5.0% | Mean_Anomaly | Fusion_XGB_Mean_Anomaly [Exploratory] | +7.10 | [+5.63, +8.74] | +13.56 | [+11.78, +16.26] | +10.58 | [+9.05, +12.35] | +15.62 | [+13.72, +18.32] |
| BruteForce | 5.0% | Mean_Anomaly | Fusion_XGB_IForest [Exploratory] | +7.10 | [+5.63, +8.74] | +13.56 | [+11.78, +16.26] | +10.58 | [+9.05, +12.35] | +15.62 | [+13.72, +18.32] |
| BruteForce | 5.0% | Mean_Anomaly | Fusion_XGB_AE [Exploratory] | +7.10 | [+5.63, +8.74] | +13.56 | [+11.78, +16.26] | +10.58 | [+9.05, +12.35] | +15.62 | [+13.72, +18.32] |
| BruteForce | 5.0% | Mean_Anomaly | Baseline_Rank_Average_0.5_0.5 | +10.87 | [+10.04, +11.79] | +24.06 | [+21.72, +26.85] | +14.36 | [+13.36, +15.37] | +26.11 | [+23.66, +29.02] |
| BruteForce | 5.0% | Mean_Anomaly | Baseline_Anomaly_Heavy_0.2_0.8 | +6.17 | [+5.82, +6.52] | +8.79 | [+7.68, +10.12] | +9.65 | [+9.09, +10.18] | +10.85 | [+9.56, +12.37] |
| BruteForce | 5.0% | Mean_Anomaly | Ablation_Gated_Boost_AE_plus_XGB | -3.40 | [-3.81, -2.95] | -1.77 | [-2.16, -1.02] | +0.09 | [-0.01, +0.22] | +0.29 | [+0.04, +0.99] |
| DoS_DDoS | 1.0% | Isolation_Forest | Supervised_XGBoost | -11.48 | [-18.72, -6.92] | +9.92 | [+3.21, +18.75] | -16.97 | [-24.26, -12.28] | -26.02 | [-38.34, -11.38] |
| DoS_DDoS | 1.0% | Isolation_Forest | Fusion_XGB_Mean_Anomaly [Exploratory] | -11.48 | [-18.72, -6.92] | +9.92 | [+3.21, +18.75] | -16.97 | [-24.26, -12.28] | -26.02 | [-38.34, -11.38] |
| DoS_DDoS | 1.0% | Isolation_Forest | Fusion_XGB_IForest [Exploratory] | -11.48 | [-18.72, -6.92] | +9.92 | [+3.21, +18.75] | -16.97 | [-24.26, -12.28] | -26.02 | [-38.34, -11.38] |
| DoS_DDoS | 1.0% | Isolation_Forest | Fusion_XGB_AE [Exploratory] | -11.48 | [-18.72, -6.92] | +9.92 | [+3.21, +18.75] | -16.97 | [-24.26, -12.28] | -26.02 | [-38.34, -11.38] |
| DoS_DDoS | 1.0% | Isolation_Forest | Baseline_Rank_Average_0.5_0.5 | +2.50 | [+0.39, +4.39] | +28.74 | [+19.43, +39.97] | -3.00 | [-5.00, -1.05] | -7.20 | [-20.41, +8.41] |
| DoS_DDoS | 1.0% | Isolation_Forest | Baseline_Anomaly_Heavy_0.2_0.8 | +5.60 | [+4.57, +6.65] | +30.64 | [+22.36, +41.06] | +0.11 | [-0.73, +0.92] | -5.29 | [-16.35, +8.06] |
| DoS_DDoS | 1.0% | Isolation_Forest | Ablation_Gated_Boost_AE_plus_XGB | +6.24 | [+5.11, +7.37] | +46.03 | [+36.20, +55.66] | +0.75 | [+0.28, +1.34] | +10.09 | [+0.44, +20.37] |
| DoS_DDoS | 5.0% | Isolation_Forest | Supervised_XGBoost | -11.59 | [-14.77, -9.74] | +12.04 | [+6.68, +17.26] | -17.09 | [-20.32, -15.20] | -34.15 | [-40.54, -27.61] |
| DoS_DDoS | 5.0% | Isolation_Forest | Fusion_XGB_Mean_Anomaly [Exploratory] | -11.59 | [-14.77, -9.74] | +12.04 | [+6.68, +17.26] | -17.09 | [-20.32, -15.20] | -34.15 | [-40.54, -27.61] |
| DoS_DDoS | 5.0% | Isolation_Forest | Fusion_XGB_IForest [Exploratory] | -11.59 | [-14.77, -9.74] | +12.04 | [+6.68, +17.26] | -17.09 | [-20.32, -15.20] | -34.15 | [-40.54, -27.61] |
| DoS_DDoS | 5.0% | Isolation_Forest | Fusion_XGB_AE [Exploratory] | -11.59 | [-14.77, -9.74] | +12.04 | [+6.68, +17.26] | -17.09 | [-20.32, -15.20] | -34.15 | [-40.54, -27.61] |
| DoS_DDoS | 5.0% | Isolation_Forest | Baseline_Rank_Average_0.5_0.5 | +2.80 | [+1.88, +3.75] | +37.55 | [+32.64, +42.08] | -2.70 | [-3.54, -1.77] | -8.64 | [-13.67, -2.87] |
| DoS_DDoS | 5.0% | Isolation_Forest | Baseline_Anomaly_Heavy_0.2_0.8 | +5.74 | [+5.20, +6.28] | +43.70 | [+39.97, +47.41] | +0.24 | [-0.14, +0.66] | -2.50 | [-6.41, +2.32] |
| DoS_DDoS | 5.0% | Isolation_Forest | Ablation_Gated_Boost_AE_plus_XGB | +6.30 | [+5.67, +6.90] | +54.41 | [+50.92, +57.16] | +0.80 | [+0.56, +1.08] | +8.22 | [+5.49, +11.18] |
| PortScan | 1.0% | Mean_Anomaly | Supervised_XGBoost | -11.38 | [-14.18, -3.80] | +32.98 | [+22.72, +43.42] | -13.27 | [-16.23, -5.28] | +30.17 | [+19.66, +41.33] |
| PortScan | 1.0% | Mean_Anomaly | Fusion_XGB_Mean_Anomaly [Exploratory] | -12.52 | [-16.76, -6.11] | +33.34 | [+23.17, +43.61] | -14.41 | [-18.84, -7.75] | +30.54 | [+19.83, +41.54] |
| PortScan | 1.0% | Mean_Anomaly | Fusion_XGB_IForest [Exploratory] | -12.44 | [-16.58, -6.02] | +32.99 | [+22.92, +43.35] | -14.33 | [-18.84, -7.67] | +30.19 | [+19.49, +41.21] |
| PortScan | 1.0% | Mean_Anomaly | Fusion_XGB_AE [Exploratory] | -12.44 | [-16.68, -6.01] | +34.21 | [+23.88, +44.50] | -14.33 | [-18.81, -7.65] | +31.41 | [+20.55, +42.29] |
| PortScan | 1.0% | Mean_Anomaly | Baseline_Rank_Average_0.5_0.5 | +1.67 | [-0.04, +3.25] | +17.67 | [+11.78, +26.22] | -0.21 | [-2.26, +1.78] | +14.87 | [+8.89, +23.47] |
| PortScan | 1.0% | Mean_Anomaly | Baseline_Anomaly_Heavy_0.2_0.8 | +3.05 | [+2.15, +3.93] | +11.97 | [+7.68, +18.36] | +1.17 | [-0.17, +2.50] | +9.17 | [+4.78, +15.56] |
| PortScan | 1.0% | Mean_Anomaly | Ablation_Gated_Boost_AE_plus_XGB | +4.87 | [+3.76, +5.91] | +29.82 | [+21.57, +40.88] | +2.99 | [+2.01, +4.09] | +27.02 | [+18.63, +38.18] |
| PortScan | 5.0% | Mean_Anomaly | Supervised_XGBoost | -11.11 | [-10.85, -6.52] | +29.97 | [+25.74, +34.21] | -13.01 | [-12.86, -8.14] | +21.57 | [+16.46, +26.51] |
| PortScan | 5.0% | Mean_Anomaly | Fusion_XGB_Mean_Anomaly [Exploratory] | -12.21 | [-13.45, -8.89] | +30.77 | [+26.26, +34.87] | -14.11 | [-15.43, -10.58] | +22.37 | [+16.97, +27.02] |
| PortScan | 5.0% | Mean_Anomaly | Fusion_XGB_IForest [Exploratory] | -12.11 | [-13.30, -8.81] | +29.33 | [+24.64, +33.24] | -14.01 | [-15.28, -10.50] | +20.93 | [+15.55, +25.61] |
| PortScan | 5.0% | Mean_Anomaly | Fusion_XGB_AE [Exploratory] | -12.13 | [-13.36, -8.81] | +31.46 | [+26.97, +35.54] | -14.03 | [-15.35, -10.50] | +23.06 | [+17.85, +27.77] |
| PortScan | 5.0% | Mean_Anomaly | Baseline_Rank_Average_0.5_0.5 | +1.81 | [+0.98, +2.55] | +29.26 | [+25.54, +32.79] | -0.08 | [-1.02, +0.80] | +20.86 | [+16.57, +25.16] |
| PortScan | 5.0% | Mean_Anomaly | Baseline_Anomaly_Heavy_0.2_0.8 | +2.95 | [+2.51, +3.35] | +22.15 | [+19.18, +25.21] | +1.05 | [+0.44, +1.66] | +13.75 | [+10.41, +17.62] |
| PortScan | 5.0% | Mean_Anomaly | Ablation_Gated_Boost_AE_plus_XGB | +4.92 | [+4.38, +5.45] | +40.00 | [+36.27, +43.83] | +3.02 | [+2.55, +3.49] | +31.60 | [+27.32, +35.49] |
| WebAttack | 1.0% | Autoencoder | Supervised_XGBoost | +24.46 | [+21.87, +26.98] | +27.90 | [+22.53, +35.71] | +24.46 | [+21.87, +26.98] | +27.90 | [+22.53, +35.71] |
| WebAttack | 1.0% | Autoencoder | Fusion_XGB_Mean_Anomaly [Exploratory] | +13.83 | [+10.68, +16.93] | +9.45 | [+6.06, +15.16] | +13.83 | [+10.68, +16.93] | +9.45 | [+6.06, +15.16] |
| WebAttack | 1.0% | Autoencoder | Fusion_XGB_IForest [Exploratory] | +24.46 | [+21.87, +26.98] | +27.90 | [+22.53, +35.71] | +24.46 | [+21.87, +26.98] | +27.90 | [+22.53, +35.71] |
| WebAttack | 1.0% | Autoencoder | Fusion_XGB_AE [Exploratory] | +5.94 | [+2.24, +9.50] | +7.66 | [+3.98, +13.81] | +5.94 | [+2.24, +9.50] | +7.66 | [+3.98, +13.81] |
| WebAttack | 1.0% | Autoencoder | Baseline_Rank_Average_0.5_0.5 | +22.08 | [+20.24, +23.94] | +11.65 | [+9.15, +14.51] | +22.08 | [+20.24, +23.94] | +11.65 | [+9.15, +14.51] |
| WebAttack | 1.0% | Autoencoder | Baseline_Anomaly_Heavy_0.2_0.8 | +15.61 | [+14.33, +16.76] | +3.25 | [+2.52, +4.25] | +15.61 | [+14.33, +16.76] | +3.25 | [+2.52, +4.25] |
| WebAttack | 1.0% | Autoencoder | Ablation_Gated_Boost_AE_plus_XGB | +1.24 | [+0.40, +2.31] | +0.10 | [+0.02, +0.48] | +1.24 | [+0.40, +2.31] | +0.10 | [+0.02, +0.48] |
| WebAttack | 5.0% | Autoencoder | Supervised_XGBoost | +24.28 | [+23.01, +25.56] | +58.94 | [+54.84, +63.64] | +24.28 | [+23.01, +25.56] | +58.94 | [+54.84, +63.64] |
| WebAttack | 5.0% | Autoencoder | Fusion_XGB_Mean_Anomaly [Exploratory] | +13.74 | [+12.26, +15.20] | +26.32 | [+22.81, +30.72] | +13.74 | [+12.26, +15.20] | +26.32 | [+22.81, +30.72] |
| WebAttack | 5.0% | Autoencoder | Fusion_XGB_IForest [Exploratory] | +24.28 | [+23.01, +25.56] | +58.94 | [+54.84, +63.64] | +24.28 | [+23.01, +25.56] | +58.94 | [+54.84, +63.64] |
| WebAttack | 5.0% | Autoencoder | Fusion_XGB_AE [Exploratory] | +5.85 | [+4.17, +7.54] | +17.69 | [+14.34, +21.51] | +5.85 | [+4.17, +7.54] | +17.69 | [+14.34, +21.51] |
| WebAttack | 5.0% | Autoencoder | Baseline_Rank_Average_0.5_0.5 | +22.04 | [+21.05, +23.09] | +35.39 | [+32.50, +39.00] | +22.04 | [+21.05, +23.09] | +35.39 | [+32.50, +39.00] |
| WebAttack | 5.0% | Autoencoder | Baseline_Anomaly_Heavy_0.2_0.8 | +14.98 | [+14.31, +15.64] | +11.60 | [+10.49, +13.09] | +14.98 | [+14.31, +15.64] | +11.60 | [+10.49, +13.09] |
| WebAttack | 5.0% | Autoencoder | Ablation_Gated_Boost_AE_plus_XGB | +1.21 | [+0.79, +1.65] | +0.44 | [+0.25, +0.89] | +1.21 | [+0.79, +1.65] | +0.44 | [+0.25, +0.89] |