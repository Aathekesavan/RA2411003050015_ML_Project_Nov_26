"""SentinelX-Shift Explanation Stability Package."""

from src.stability.perturb import PhysicalPerturbationEngine
from src.stability.stability import (
    ExplanationStabilityEvaluator,
    compute_jaccard_similarity,
    compute_spearman_attribution_correlation,
    evaluate_ranking_variants,
    compute_sensitivity_curve,
)

__all__ = [
    "PhysicalPerturbationEngine",
    "ExplanationStabilityEvaluator",
    "compute_jaccard_similarity",
    "compute_spearman_attribution_correlation",
    "evaluate_ranking_variants",
    "compute_sensitivity_curve",
]
