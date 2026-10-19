"""Explanation Stability Evaluator and Ranking Benchmark for SentinelX-Shift.

Implements:
1. Top-5 Jaccard Similarity and Spearman Rank Correlation over N=20 physical perturbations.
2. Score Stability Control to differentiate attribution stability from risk score variance.
3. Cost-controlled candidate alert batching (timing calibration + pool capping).
4. Exactly Five Ranking Variants:
   (i)   s_risk
   (ii)  s_risk * (a + b * S_exp_stab)
   (iii) s_risk * (a + b * S_score_stab)
   (iv)  S_exp_stab alone
   (v)   random reorder
5. Parameter tuning (a, b) STRICTLY on inner-LOFO validation folds.
6. Statistical evaluation: Precision@k (k in {50, 100, 500}), R-Precision,
   paired bootstrap 95% CIs, Holm-Bonferroni correction, and strict verdicts:
   "helped", "hurt", or "no effect".
"""

from typing import Dict, List, Optional, Tuple, Set, Any
import logging
import time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.models.pipeline import SentinelXPredictor
from src.explain.explainer import SentinelXExplainer
from src.stability.perturb import PhysicalPerturbationEngine

logger = logging.getLogger(__name__)


def compute_jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Compute Jaccard similarity index between two feature sets."""
    union_len = len(set_a | set_b)
    if union_len == 0:
        return 1.0
    return float(len(set_a & set_b) / union_len)


def compute_spearman_attribution_correlation(
    vec_a: np.ndarray,
    vec_b: np.ndarray
) -> float:
    """Compute Spearman rank correlation between two explanation attribution vectors."""
    if len(vec_a) < 2 or np.all(vec_a == vec_a[0]) or np.all(vec_b == vec_b[0]):
        return 1.0 if np.allclose(vec_a, vec_b) else 0.0
    corr, _ = spearmanr(vec_a, vec_b)
    if np.isnan(corr):
        return 0.0
    return float(corr)


class ExplanationStabilityEvaluator:
    """Measures explanation stability metrics over physical perturbations of candidate flows."""

    def __init__(
        self,
        explainer: SentinelXExplainer,
        perturb_engine: Optional[PhysicalPerturbationEngine] = None,
        n_perturbations: int = 20,
        jitter_pct: float = 0.05,
        random_seed: int = 42
    ):
        self.explainer = explainer
        self.perturb_engine = perturb_engine or PhysicalPerturbationEngine(random_seed=random_seed)
        self.n_perturbations = n_perturbations
        self.jitter_pct = jitter_pct
        self.random_seed = random_seed

    def _extract_explanation_features_and_vector(
        self,
        flow_df: pd.DataFrame
    ) -> Tuple[List[str], np.ndarray, float]:
        """Extract top-5 features, full attribution vector, and fused score for a flow."""
        exp = self.explainer.explain(flow_df)
        fused_score = exp["fused_risk_score"]

        # Dominant component determines primary attribution vector
        if exp["components"]["dominant_component"] == "anomaly":
            top5 = [item["feature"] for item in exp["anomaly_explanation"]["autoencoder_top5"]]
            X_trans = self.explainer.predictor.pipeline.transform(flow_df[self.explainer.feature_cols])
            recon = self.explainer.predictor.autoencoder_model.model.predict(X_trans)[0]
            att_vec = (X_trans[0] - recon) ** 2
        else:
            top5 = [item["feature"] for item in exp["supervised_explanation"]]
            X_trans = self.explainer.predictor.pipeline.transform(flow_df[self.explainer.feature_cols])
            att_vec = np.abs(self.explainer.xgb_explainer.shap_values(X_trans)[0])

        return top5, att_vec, fused_score

    def evaluate_flow_stability(self, flow_row: pd.Series) -> Dict[str, float]:
        """Evaluate explanation stability and score stability for a single flow."""
        base_df = flow_row.to_frame().T
        base_top5, base_att, base_score = self._extract_explanation_features_and_vector(base_df)
        base_set = set(base_top5)

        # Generate N valid physical perturbations
        perturbed_df = self.perturb_engine.generate_valid_perturbations(
            flow_row, n_samples=self.n_perturbations, jitter_pct=self.jitter_pct
        )

        jaccards = []
        spearmans = []
        perturbed_scores = []

        for i in range(len(perturbed_df)):
            p_row = perturbed_df.iloc[[i]]
            p_top5, p_att, p_score = self._extract_explanation_features_and_vector(p_row)

            # 1. Jaccard similarity
            j_sim = compute_jaccard_similarity(base_set, set(p_top5))
            jaccards.append(j_sim)

            # 2. Spearman rank correlation
            sp_corr = compute_spearman_attribution_correlation(base_att, p_att)
            spearmans.append(max(0.0, sp_corr))

            perturbed_scores.append(p_score)

        mean_jaccard = float(np.mean(jaccards)) if jaccards else 1.0
        mean_spearman = float(np.mean(spearmans)) if spearmans else 1.0
        comp_exp_stab = 0.5 * (mean_jaccard + mean_spearman)

        # 3. Score Stability Control (flow-specific metric)
        scores_arr = np.asarray(perturbed_scores, dtype=float)
        mean_score = float(np.mean(scores_arr))
        std_score = float(np.std(scores_arr))
        score_cv = std_score / (mean_score + 1e-4)
        score_stability_control = float(np.clip(1.0 - score_cv, 0.0, 1.0))

        return {
            "base_risk_score": round(base_score, 4),
            "jaccard_similarity": round(mean_jaccard, 4),
            "spearman_correlation": round(mean_spearman, 4),
            "explanation_stability": round(comp_exp_stab, 4),
            "score_std": round(std_score, 4),
            "score_stability_control": round(score_stability_control, 4),
        }

    def preflight_latency_check(self, candidate_row: pd.Series) -> float:
        """Measure execution time (ms) for evaluating 1 flow across N perturbations."""
        t0 = time.perf_counter()
        _ = self.evaluate_flow_stability(candidate_row)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        logger.info(f"Preflight latency benchmark: {elapsed_ms:.1f} ms per flow ({self.n_perturbations} perturbations).")
        return elapsed_ms


def compute_ranking_precision(y_true: np.ndarray, scores: np.ndarray, k: int) -> float:
    """Compute precision among top-k ranked alerts."""
    if len(y_true) == 0:
        return 0.0
    actual_k = min(k, len(y_true))
    if actual_k == 0:
        return 0.0
    top_indices = np.argsort(-scores)[:actual_k]
    return float(np.mean(y_true[top_indices]))


def compute_r_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    """Compute R-precision where R is the total number of true positives."""
    n_pos = int(np.sum(y_true))
    if n_pos == 0:
        return 0.0
    return compute_ranking_precision(y_true, scores, k=n_pos)


def tune_stability_hyperparameters(
    val_candidates_df: pd.DataFrame,
    target_metric: str = "Precision@100"
) -> Dict[str, Tuple[float, float]]:
    """Tune parameters (a, b) STRICTLY on inner-LOFO validation candidates via grid search.

    Variants:
      (ii)  s_risk * (a + b * S_exp_stab)
      (iii) s_risk * (a + b * S_score_stab)

    Returns:
      {"exp": (a_exp, b_exp), "score": (a_score, b_score)}
    """
    df = val_candidates_df.copy()
    y_val = df["is_attack"].to_numpy().astype(int)
    s_risk = df["base_risk_score"].to_numpy()
    s_exp = df["explanation_stability"].to_numpy()
    s_score = df["score_stability_control"].to_numpy()

    a_grid = [0.5, 1.0]
    b_grid = [0.0, 0.2, 0.5, 1.0, 2.0]

    def eval_metric(y: np.ndarray, s: np.ndarray) -> float:
        if target_metric == "Precision@50":
            return compute_ranking_precision(y, s, 50)
        elif target_metric == "Precision@100":
            return compute_ranking_precision(y, s, 100)
        elif target_metric == "Precision@500":
            return compute_ranking_precision(y, s, 500)
        elif target_metric == "R-Precision":
            return compute_r_precision(y, s)
        return compute_ranking_precision(y, s, 100)

    # Base performance
    base_val_perf = eval_metric(y_val, s_risk)

    # Grid search for Variant (ii): exp_stab
    best_exp_perf = -1.0
    best_exp_params = (1.0, 0.0)
    for a in a_grid:
        for b in b_grid:
            ranked_scores = s_risk * (a + b * s_exp)
            perf = eval_metric(y_val, ranked_scores)
            # Prefer improvement, or smallest b if tied
            if perf > best_exp_perf or (np.isclose(perf, best_exp_perf) and b < best_exp_params[1]):
                best_exp_perf = perf
                best_exp_params = (a, b)

    # Grid search for Variant (iii): score_stab
    best_score_perf = -1.0
    best_score_params = (1.0, 0.0)
    for a in a_grid:
        for b in b_grid:
            ranked_scores = s_risk * (a + b * s_score)
            perf = eval_metric(y_val, ranked_scores)
            if perf > best_score_perf or (np.isclose(perf, best_score_perf) and b < best_score_params[1]):
                best_score_perf = perf
                best_score_params = (a, b)

    logger.info(
        f"Inner-LOFO stability tuning: Base {target_metric}={base_val_perf:.4f} | "
        f"Exp tuned (a={best_exp_params[0]}, b={best_exp_params[1]}) -> {best_exp_perf:.4f} | "
        f"Score tuned (a={best_score_params[0]}, b={best_score_params[1]}) -> {best_score_perf:.4f}"
    )

    return {
        "exp": best_exp_params,
        "score": best_score_params,
        "inner_val_base_perf": base_val_perf,
        "inner_val_exp_perf": best_exp_perf,
        "inner_val_score_perf": best_score_perf,
    }


def evaluate_ranking_variants(
    test_df: pd.DataFrame,
    a_exp: float = 1.0,
    b_exp: float = 0.5,
    a_score: float = 1.0,
    b_score: float = 0.5,
    n_bootstrap: int = 1000,
    seed: int = 42
) -> pd.DataFrame:
    """Evaluate EXACTLY the 5 ranking schemes with paired bootstrap CIs and Holm-Bonferroni correction.

    Ranking Variants:
      (i)   s_risk
      (ii)  s_risk * (a + b * S_exp_stab)
      (iii) s_risk * (a + b * S_score_stab)
      (iv)  S_exp_stab alone
      (v)   random reorder

    Strict Verdicts:
      - "helped": Holm-corrected CI strictly positive (> 0)
      - "hurt": Holm-corrected CI strictly negative (< 0)
      - "no effect": otherwise (CI includes zero / p_adj >= 0.05)
    """
    df = test_df.copy()
    y_true = df["is_attack"].to_numpy().astype(int)
    s_risk = df["base_risk_score"].to_numpy()
    s_exp = df["explanation_stability"].to_numpy()
    s_score = df["score_stability_control"].to_numpy()

    # Reproducible random reordering
    rng = np.random.RandomState(seed)
    s_rand = rng.uniform(0.0, 1.0, size=len(df))

    # EXACT 5 Ranking Schemes
    v1_scores = s_risk
    v2_scores = s_risk * (a_exp + b_exp * s_exp)
    v3_scores = s_risk * (a_score + b_score * s_score)
    v4_scores = s_exp
    v5_scores = s_rand

    variants = [
        ("V1_s_risk", v1_scores, "Baseline Fused Risk Score"),
        ("V2_s_risk_x_exp_stab", v2_scores, f"s_risk * ({a_exp} + {b_exp} * S_exp_stab)"),
        ("V3_s_risk_x_score_stab", v3_scores, f"s_risk * ({a_score} + {b_score} * S_score_stab)"),
        ("V4_exp_stab_alone", v4_scores, "S_exp_stab alone"),
        ("V5_random_reorder", v5_scores, "Random Reorder"),
    ]

    # Compute baseline metrics on full test set
    metrics_to_eval = [
        ("Precision@50", lambda y, s: compute_ranking_precision(y, s, 50)),
        ("Precision@100", lambda y, s: compute_ranking_precision(y, s, 100)),
        ("Precision@500", lambda y, s: compute_ranking_precision(y, s, 500)),
        ("R-Precision", lambda y, s: compute_r_precision(y, s)),
    ]

    # Precalculate observed values
    observed = {}
    for var_name, scores, _ in variants:
        observed[var_name] = {}
        for m_name, m_func in metrics_to_eval:
            observed[var_name][m_name] = m_func(y_true, scores)

    # Paired Bootstrap Differences vs V1 (s_risk)
    n_samples = len(df)
    boot_diffs = {
        m_name: {var_name: [] for var_name, _, _ in variants if var_name != "V1_s_risk"}
        for m_name, _ in metrics_to_eval
    }

    boot_rng = np.random.RandomState(seed)
    for _ in range(n_bootstrap):
        boot_idx = boot_rng.choice(n_samples, size=n_samples, replace=True)
        y_boot = y_true[boot_idx]

        for m_name, m_func in metrics_to_eval:
            v1_val = m_func(y_boot, v1_scores[boot_idx])
            for var_name, scores, _ in variants:
                if var_name == "V1_s_risk":
                    continue
                var_val = m_func(y_boot, scores[boot_idx])
                # Delta in percentage points
                delta_pp = (var_val - v1_val) * 100.0
                boot_diffs[m_name][var_name].append(delta_pp)

    # Perform Holm-Bonferroni correction per metric across the 4 candidate comparisons (V2, V3, V4, V5)
    records = []

    # First add V1 row
    records.append({
        "Variant": "V1_s_risk",
        "Formula / Description": "s_risk (Baseline)",
        "Precision@50": f"{observed['V1_s_risk']['Precision@50'] * 100.0:.2f}%",
        "Precision@100": f"{observed['V1_s_risk']['Precision@100'] * 100.0:.2f}%",
        "Precision@500": f"{observed['V1_s_risk']['Precision@500'] * 100.0:.2f}%",
        "R-Precision": f"{observed['V1_s_risk']['R-Precision'] * 100.0:.2f}%",
        "Delta_P@100_pp": "0.00",
        "95% CI (Delta P@100 pp)": "[+0.00, +0.00]",
        "Unadjusted_p": "1.0000",
        "Holm_Adj_p": "1.0000",
        "Verdict": "baseline",
    })

    candidate_vars = [v for v in variants if v[0] != "V1_s_risk"]

    # Focus primary hypothesis test on Precision@100 (or R-Precision if candidate pool < 100)
    primary_metric = "Precision@100"

    # Compute unadjusted empirical p-values for primary metric
    p_values = {}
    ci_bounds = {}
    for var_name, _, _ in candidate_vars:
        diffs = np.array(boot_diffs[primary_metric][var_name])
        ci_low = float(np.percentile(diffs, 2.5))
        ci_high = float(np.percentile(diffs, 97.5))
        ci_bounds[var_name] = (ci_low, ci_high)

        # Two-sided empirical bootstrap p-value
        p_val = 2.0 * min(np.mean(diffs <= 0.0), np.mean(diffs >= 0.0))
        p_val = float(np.clip(p_val, 1.0 / n_bootstrap, 1.0))
        p_values[var_name] = p_val

    # Apply Holm-Bonferroni correction across the 4 comparisons
    sorted_vars = sorted(candidate_vars, key=lambda v: p_values[v[0]])
    m = len(sorted_vars)  # 4
    holm_adj_p = {}
    running_max_p = 0.0

    for rank, (var_name, _, _) in enumerate(sorted_vars):
        multiplier = m - rank
        raw_p = p_values[var_name]
        adj_p = min(1.0, raw_p * multiplier)
        running_max_p = max(running_max_p, adj_p)
        holm_adj_p[var_name] = min(1.0, running_max_p)

    # Classify verdicts strictly
    for var_name, scores, desc in candidate_vars:
        p_obs = observed[var_name]["Precision@100"] * 100.0
        v1_obs = observed["V1_s_risk"]["Precision@100"] * 100.0
        delta_pp = p_obs - v1_obs
        ci_low, ci_high = ci_bounds[var_name]
        adj_p = holm_adj_p[var_name]

        # Strict verdict rules:
        if adj_p < 0.05 and ci_low > 0.0:
            verdict = "helped"
        elif adj_p < 0.05 and ci_high < 0.0:
            verdict = "hurt"
        else:
            verdict = "no effect"

        ci_str = f"[{'+' if ci_low >= 0 else ''}{ci_low:.2f}, {'+' if ci_high >= 0 else ''}{ci_high:.2f}]"
        records.append({
            "Variant": var_name,
            "Formula / Description": desc,
            "Precision@50": f"{observed[var_name]['Precision@50'] * 100.0:.2f}%",
            "Precision@100": f"{observed[var_name]['Precision@100'] * 100.0:.2f}%",
            "Precision@500": f"{observed[var_name]['Precision@500'] * 100.0:.2f}%",
            "R-Precision": f"{observed[var_name]['R-Precision'] * 100.0:.2f}%",
            "Delta_P@100_pp": f"{'+' if delta_pp >= 0 else ''}{delta_pp:.2f}",
            "95% CI (Delta P@100 pp)": ci_str,
            "Unadjusted_p": f"{p_values[var_name]:.4f}",
            "Holm_Adj_p": f"{adj_p:.4f}",
            "Verdict": verdict,
        })

    return pd.DataFrame(records)


def compute_sensitivity_curve(
    stability_results_df: pd.DataFrame,
    b_values: Optional[List[float]] = None
) -> pd.DataFrame:
    """Compute Precision@50, Precision@100, and Precision@500 across stability weight b in [0.0, 1.0]."""
    if b_values is None:
        b_values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    df = stability_results_df.copy()
    y_true = df["is_attack"].to_numpy().astype(int)

    records = []
    for b in b_values:
        s_fused = df["base_risk_score"] * (1.0 + b * df["explanation_stability"])
        p50 = compute_ranking_precision(y_true, s_fused.to_numpy(), 50)
        p100 = compute_ranking_precision(y_true, s_fused.to_numpy(), 100)
        p500 = compute_ranking_precision(y_true, s_fused.to_numpy(), 500)
        r_prec = compute_r_precision(y_true, s_fused.to_numpy())

        records.append({
            "b_weight": b,
            "Precision@50": f"{p50 * 100.0:.2f}%",
            "Precision@100": f"{p100 * 100.0:.2f}%",
            "Precision@500": f"{p500 * 100.0:.2f}%",
            "R-Precision": f"{r_prec * 100.0:.2f}%",
        })

    return pd.DataFrame(records)
