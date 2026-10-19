| Variant | Formula / Description | Precision@50 | Precision@100 | Precision@500 | R-Precision | Delta_P@100_pp | 95% CI (Delta P@100 pp) | Unadjusted_p | Holm_Adj_p | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| V1_s_risk | s_risk (Baseline) | 88.00% | 65.00% | 60.19% | 84.62% | 0.00 | [+0.00, +0.00] | 1.0000 | 1.0000 | baseline |
| V2_s_risk_x_exp_stab | s_risk * (0.5 + 0.0 * S_exp_stab) | 88.00% | 65.00% | 60.19% | 84.62% | +0.00 | [+0.00, +0.00] | 1.0000 | 1.0000 | no effect |
| V3_s_risk_x_score_stab | s_risk * (0.5 + 0.0 * S_score_stab) | 88.00% | 65.00% | 60.19% | 84.62% | +0.00 | [+0.00, +0.00] | 1.0000 | 1.0000 | no effect |
| V4_exp_stab_alone | S_exp_stab alone | 72.00% | 63.00% | 60.19% | 66.15% | -2.00 | [-6.00, +0.00] | 0.1440 | 0.4320 | no effect |
| V5_random_reorder | Random Reorder | 60.00% | 58.00% | 60.19% | 58.46% | -7.00 | [-8.00, -4.00] | 0.0010 | 0.0040 | hurt |