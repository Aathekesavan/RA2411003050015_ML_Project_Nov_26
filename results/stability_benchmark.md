# Alert Prioritization Stability Benchmark (5-Seed LOFO)

- **Run ID:** `run_20261019_eddc08e` | **Git Hash:** `eddc08e-dirty`
- **Seeds Evaluated:** 5 seeds (42, 101, 202, 303, 404)
- **Verdict Decision Variant:** V2 (`s_risk * ((1 - b) + b * S_exp)`) determines verdict; V2_rank reported alongside as rank-tie sensitivity diagnostic.
- **Single Verdict Rule:** `holm_adj_p < 0.05` and CI excludes zero -> `helped`/`hurt`; otherwise `no benefit detected`.

| Family_Fold | Prevalence | Variant | Formula / Description | Precision@100 | R-Precision | Mean_Delta_P@100_pp | Mean_Delta_R-Prec_pp | Mean_CI_Width_pp | Consensus_Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DoS_DDoS | 1.0% | V1_s_risk | s_risk (Baseline) | 33.00% +/- 0.00% | 36.52% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| DoS_DDoS | 1.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.2) + 0.2 * S_exp) [*Determines Verdict*] | 9.00% +/- 0.00% | 6.48% +/- 0.00% | -24.00 | -30.03 | 19.60 | hurt |
| DoS_DDoS | 1.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.4) + 0.4 * S_score) | 32.20% +/- 0.40% | 36.52% +/- 0.00% | -0.80 | +0.00 | 4.60 | no benefit detected |
| DoS_DDoS | 1.0% | V4a_exp_stab_alone | S_exp alone | 7.00% +/- 0.00% | 3.07% +/- 0.00% | -26.00 | -33.45 | 19.60 | hurt |
| DoS_DDoS | 1.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 10.00% +/- 0.00% | 5.80% +/- 0.00% | -23.00 | -30.72 | 19.61 | hurt |
| DoS_DDoS | 1.0% | V5_random_reorder | Random Reorder | 27.20% +/- 5.56% | 28.81% +/- 1.12% | -5.80 | -7.71 | 24.00 | no benefit detected |
| DoS_DDoS | 1.0% | V2_rank_sensitivity | r_risk * ((1 - 0.2) + 0.2 * S_exp) (Rank Variant for Ties) | 30.00% +/- 0.00% | 36.52% +/- 0.00% | -3.00 | +0.00 | 6.40 | no benefit detected |
| DoS_DDoS | 5.0% | V1_s_risk | s_risk (Baseline) | 94.00% +/- 0.00% | 95.43% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| DoS_DDoS | 5.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 94.20% +/- 0.40% | 95.56% +/- 0.26% | +0.20 | +0.13 | 2.60 | no benefit detected |
| DoS_DDoS | 5.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 95.20% +/- 0.98% | 96.26% +/- 0.68% | +1.20 | +0.83 | 7.20 | no benefit detected |
| DoS_DDoS | 5.0% | V4a_exp_stab_alone | S_exp alone | 91.00% +/- 0.00% | 96.07% +/- 0.00% | -3.00 | +0.64 | 14.60 | no benefit detected |
| DoS_DDoS | 5.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 92.00% +/- 0.00% | 96.07% +/- 0.00% | -2.00 | +0.64 | 14.40 | no benefit detected |
| DoS_DDoS | 5.0% | V5_random_reorder | Random Reorder | 96.20% +/- 2.14% | 95.56% +/- 0.08% | +2.20 | +0.13 | 11.80 | no benefit detected |
| DoS_DDoS | 5.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 94.20% +/- 0.40% | 95.41% +/- 0.04% | +0.20 | -0.02 | 2.60 | no benefit detected |
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
| PortScan | 1.0% | V1_s_risk | s_risk (Baseline) | 56.00% +/- 0.00% | 53.37% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| PortScan | 1.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 56.00% +/- 0.00% | 53.37% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| PortScan | 1.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 56.00% +/- 0.00% | 53.37% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| PortScan | 1.0% | V4a_exp_stab_alone | S_exp alone | 6.00% +/- 0.00% | 4.49% +/- 0.00% | -50.00 | -48.88 | 20.80 | hurt |
| PortScan | 1.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 7.00% +/- 0.00% | 6.18% +/- 0.00% | -49.00 | -47.19 | 20.60 | hurt |
| PortScan | 1.0% | V5_random_reorder | Random Reorder | 19.20% +/- 5.91% | 18.09% +/- 3.38% | -36.80 | -35.28 | 23.21 | hurt |
| PortScan | 1.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 56.00% +/- 0.00% | 53.37% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| PortScan | 5.0% | V1_s_risk | s_risk (Baseline) | 90.00% +/- 0.00% | 81.24% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| PortScan | 5.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 90.00% +/- 0.00% | 81.24% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| PortScan | 5.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 90.00% +/- 0.00% | 81.24% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| PortScan | 5.0% | V4a_exp_stab_alone | S_exp alone | 38.00% +/- 0.00% | 40.92% +/- 0.00% | -52.00 | -40.32 | 24.00 | hurt |
| PortScan | 5.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 33.00% +/- 0.00% | 40.72% +/- 0.00% | -57.00 | -40.52 | 27.20 | hurt |
| PortScan | 5.0% | V5_random_reorder | Random Reorder | 55.00% +/- 2.61% | 51.58% +/- 1.70% | -35.00 | -29.66 | 23.80 | hurt |
| PortScan | 5.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 90.00% +/- 0.00% | 81.24% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
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
| Bot | 5.0% | V4a_exp_stab_alone | S_exp alone | 33.00% +/- 0.00% | 38.05% +/- 0.00% | +33.00 | +38.05 | 18.40 | helped |
| Bot | 5.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| Bot | 5.0% | V5_random_reorder | Random Reorder | 19.00% +/- 3.29% | 19.51% +/- 1.02% | +19.00 | +19.51 | 15.40 | helped |
| Bot | 5.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 1.0% | V1_s_risk | s_risk (Baseline) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| WebAttack | 1.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.0) + 0.0 * S_exp) [*Determines Verdict*] | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 1.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 1.0% | V4a_exp_stab_alone | S_exp alone | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 1.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 1.0% | V5_random_reorder | Random Reorder | 0.20% +/- 0.40% | 0.00% +/- 0.00% | +0.20 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 1.0% | V2_rank_sensitivity | r_risk * ((1 - 0.0) + 0.0 * S_exp) (Rank Variant for Ties) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 5.0% | V1_s_risk | s_risk (Baseline) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | baseline |
| WebAttack | 5.0% | V2_s_risk_x_exp_stab | s_risk * ((1 - 0.2) + 0.2 * S_exp) [*Determines Verdict*] | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 5.0% | V3_s_risk_x_score_stab | s_risk * ((1 - 0.0) + 0.0 * S_score) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 5.0% | V4a_exp_stab_alone | S_exp alone | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 5.0% | V4b_s_risk_x_exp_mult | s_risk * S_exp (Multiplicative, b=1.0) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 5.0% | V5_random_reorder | Random Reorder | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |
| WebAttack | 5.0% | V2_rank_sensitivity | r_risk * ((1 - 0.2) + 0.2 * S_exp) (Rank Variant for Ties) | 0.00% +/- 0.00% | 0.00% +/- 0.00% | +0.00 | +0.00 | 0.00 | no benefit detected |