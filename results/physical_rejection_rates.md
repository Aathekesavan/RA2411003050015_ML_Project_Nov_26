# Domain Invariant Validation & Physical Jitter Audit

> [!NOTE] Invariant-Preserving Clamping Impact
> The perturbation generator proactively applies invariant-preserving clamping (2-packet duration/IAT synchronization, flag capping to packet totals, line-rate bounds, and statistical hierarchies). While raw unconstrained jitter triggers domain violations, defensive clamping successfully prevents invalid flows from propagating, yielding a final post-clamping rejection rate of 0.00% across all jitter magnitudes.

| Jitter_Magnitude | Total_Perturbations_Evaluated | Valid_Perturbations_Accepted | Raw_Domain_Violations_Pre_Clamp | Raw_Violation_Rate_Pct | Defensive_Clamping_Actions | Clamping_Rate_Pct | Post_Clamping_Rejections | Final_Rejection_Rate_Pct | Mean_Relative_Change_Pct | Top_Clamped_Invariant |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| +/- 1% | 500 | 500 | 270 | 54.00% | 220 | 44.00% | 0 | 0.00% | 2.43% | Rule 6 (2-Packet / Equal IAT Duration Sync) (220) |
| +/- 5% | 500 | 500 | 285 | 57.00% | 238 | 47.60% | 0 | 0.00% | 3.39% | Rule 6 (2-Packet / Equal IAT Duration Sync) (220) |
| +/- 10% | 500 | 500 | 307 | 61.40% | 256 | 51.20% | 0 | 0.00% | 4.65% | Rule 6 (2-Packet / Equal IAT Duration Sync) (220) |