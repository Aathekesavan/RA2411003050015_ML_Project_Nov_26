# Alert Prioritization Stability Benchmark (5-Seed LOFO)

- **Run ID:** `run_20261019_99c9f0a` | **Git Hash:** `99c9f0a-dirty`
- **Seeds Evaluated:** 5 seeds (42, 101, 202, 303, 404)
- **Verdict Decision Variant:** V2 (`s_risk * ((1 - b) + b * S_exp)`) determines verdict; V2_rank reported alongside as rank-tie sensitivity diagnostic.
- **Single Verdict Rule:** `holm_adj_p < 0.05` and CI excludes zero -> `helped`/`hurt`; otherwise `no benefit detected`.

| Family_Fold | Prevalence | Variant | Formula / Description | Precision@100 | R-Precision | Mean_Delta_P@100_pp | Mean_Delta_R-Prec_pp | Mean_CI_Width_pp | Consensus_Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DoS_DDoS | 1.0% | V1_s_risk | s_risk (Baseline) | 10.00% +/- 0.00% | 32.26% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| DoS_DDoS | 1.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.4) + 0.4 * S_exp) [*Determines Verdict*] | 12.60% +/- 0.80% | 10.51% +/- 0.18% | +2.60 | -21.75 | 17.00 | no benefit detected |
| DoS_DDoS | 1.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.4) + 0.4 * S_score) | 9.80% +/- 0.40% | 32.26% +/- 0.00% | -0.20 | +0.00 | 3.80 | no benefit detected |
| DoS_DDoS | 1.0% | V4a_exp_stab_alone | S_exp alone | 7.00% +/- 0.00% | 7.37% +/- 0.00% | -3.00 | -24.88 | 17.00 | no benefit detected |
| DoS_DDoS | 1.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 10.00% +/- 0.00% | 10.14% +/- 0.00% | +0.00 | -22.12 | 16.61 | no benefit detected |
| DoS_DDoS | 1.0% | V5_random_reorder | Random Reorder | 31.40% +/- 1.02% | 30.05% +/- 2.03% | +21.40 | -2.21 | 21.40 | helped |
| DoS_DDoS | 1.0% | V2_rank_sensitivity | r_risk * ((1 - 0.4) + 0.4 * S_exp) (Rank Variant for Ties) | 10.80% +/- 0.40% | 31.80% +/- 0.92% | +0.80 | -0.46 | 5.40 | no benefit detected |
| DoS_DDoS | 5.0% | V1_s_risk | s_risk (Baseline) | 91.00% +/- 0.00% | 93.29% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| DoS_DDoS | 5.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 93.00% +/- 2.45% | 93.77% +/- 0.59% | +2.00 | +0.48 | 4.80 | no benefit detected |
| DoS_DDoS | 5.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.2) + 0.2 * S_score) | 97.40% +/- 3.20% | 94.25% +/- 0.48% | +6.40 | +0.95 | 8.20 | no benefit detected |
| DoS_DDoS | 5.0% | V4a_exp_stab_alone | S_exp alone | 96.00% +/- 0.00% | 94.49% +/- 0.00% | +5.00 | +1.19 | 12.00 | no benefit detected |
| DoS_DDoS | 5.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 96.00% +/- 0.00% | 94.49% +/- 0.00% | +5.00 | +1.19 | 12.00 | no benefit detected |
| DoS_DDoS | 5.0% | V5_random_reorder | Random Reorder | 94.80% +/- 1.33% | 93.17% +/- 0.20% | +3.80 | -0.12 | 12.80 | no benefit detected |
| DoS_DDoS | 5.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 93.00% +/- 2.45% | 93.65% +/- 0.44% | +2.00 | +0.36 | 4.80 | no benefit detected |
| BruteForce | 1.0% | V1_s_risk | s_risk (Baseline) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| BruteForce | 1.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| BruteForce | 1.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| BruteForce | 1.0% | V4a_exp_stab_alone | S_exp alone | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| BruteForce | 1.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| BruteForce | 1.0% | V5_random_reorder | Random Reorder | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| BruteForce | 1.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| BruteForce | 5.0% | V1_s_risk | s_risk (Baseline) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| BruteForce | 5.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| BruteForce | 5.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| BruteForce | 5.0% | V4a_exp_stab_alone | S_exp alone | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| BruteForce | 5.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| BruteForce | 5.0% | V5_random_reorder | Random Reorder | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| BruteForce | 5.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| PortScan | 1.0% | V1_s_risk | s_risk (Baseline) | 53.00% +/- 0.00% | 54.44% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| PortScan | 1.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 53.00% +/- 0.00% | 54.44% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| PortScan | 1.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 53.00% +/- 0.00% | 54.44% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| PortScan | 1.0% | V4a_exp_stab_alone | S_exp alone | 10.00% +/- 0.00% | 27.41% +/- 0.00% | -43.00 | -27.04 | 22.60 | hurt |
| PortScan | 1.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 10.00% +/- 0.00% | 28.52% +/- 0.00% | -43.00 | -25.93 | 22.40 | hurt |
| PortScan | 1.0% | V5_random_reorder | Random Reorder | 41.20% +/- 4.96% | 39.56% +/- 2.07% | -11.80 | -14.89 | 25.00 | no benefit detected |
| PortScan | 1.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 53.00% +/- 0.00% | 54.44% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| PortScan | 5.0% | V1_s_risk | s_risk (Baseline) | 85.00% +/- 0.00% | 85.30% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| PortScan | 5.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 85.00% +/- 0.00% | 85.30% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| PortScan | 5.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 81.40% +/- 7.20% | 83.04% +/- 4.52% | -3.60 | -2.26 | 4.20 | no benefit detected |
| PortScan | 5.0% | V4a_exp_stab_alone | S_exp alone | 31.00% +/- 0.00% | 75.27% +/- 0.00% | -54.00 | -10.04 | 25.00 | hurt |
| PortScan | 5.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 32.00% +/- 0.00% | 75.27% +/- 0.00% | -53.00 | -10.04 | 24.61 | hurt |
| PortScan | 5.0% | V5_random_reorder | Random Reorder | 82.60% +/- 2.33% | 77.78% +/- 0.85% | -2.40 | -7.53 | 19.40 | no benefit detected |
| PortScan | 5.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 85.00% +/- 0.00% | 85.30% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| Bot | 1.0% | V1_s_risk | s_risk (Baseline) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| Bot | 1.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| Bot | 1.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| Bot | 1.0% | V4a_exp_stab_alone | S_exp alone | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| Bot | 1.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| Bot | 1.0% | V5_random_reorder | Random Reorder | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| Bot | 1.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| Bot | 5.0% | V1_s_risk | s_risk (Baseline) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| Bot | 5.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| Bot | 5.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| Bot | 5.0% | V4a_exp_stab_alone | S_exp alone | 1.00% +/- 0.00% | 0.00% +/- 0.00% | +1.00 | +0.00 | 11.20 | no benefit detected |
| Bot | 5.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| Bot | 5.0% | V5_random_reorder | Random Reorder | 0.20% +/- 0.40% | 0.00% +/- 0.00% | +0.20 | +0.00 | 0.00 | no benefit detected |
| Bot | 5.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 1.0% | V1_s_risk | s_risk (Baseline) | 5.00% +/- 0.00% | 12.50% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| WebAttack | 1.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 5.00% +/- 0.00% | 12.50% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 1.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 5.00% +/- 0.00% | 12.50% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 1.0% | V4a_exp_stab_alone | S_exp alone | 0.00% +/- 0.00% | 0.00% +/- 0.00% | -5.00 | -12.50 | 40.01 | no benefit detected |
| WebAttack | 1.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 2.00% +/- 0.00% | 0.00% +/- 0.00% | -3.00 | -12.50 | 40.01 | no benefit detected |
| WebAttack | 1.0% | V5_random_reorder | Random Reorder | 1.20% +/- 0.98% | 2.50% +/- 5.00% | -3.80 | -10.00 | 48.00 | no benefit detected |
| WebAttack | 1.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 5.00% +/- 0.00% | 12.50% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 5.0% | V1_s_risk | s_risk (Baseline) | 2.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| WebAttack | 5.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 2.20% +/- 0.40% | 0.00% +/- 0.00% | +0.20 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 5.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 2.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 5.0% | V4a_exp_stab_alone | S_exp alone | 0.00% +/- 0.00% | 0.00% +/- 0.00% | -2.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 5.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 3.00% +/- 0.00% | 0.00% +/- 0.00% | +1.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 5.0% | V5_random_reorder | Random Reorder | 0.00% +/- 0.00% | 0.00% +/- 0.00% | -2.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 5.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 2.20% +/- 0.40% | 0.00% +/- 0.00% | +0.20 | +0.00 | 5.00 | no benefit detected |