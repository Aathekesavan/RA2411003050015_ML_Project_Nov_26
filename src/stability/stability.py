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
        """Evaluate explanation stability and score stability for a single flow using vectorized batch inference."""
        base_df = flow_row.to_frame().T
        exp = self.explainer.explain(base_df)
        base_score = float(exp["fused_risk_score"])
        dominant = exp["components"]["dominant_component"]

        # Base attribution vector & top-5
        feature_cols = self.explainer.feature_cols
        X_base = self.explainer.predictor.pipeline.transform(base_df[feature_cols])

        if dominant == "anomaly":
            recon_base = self.explainer.predictor.autoencoder_model.model.predict(X_base)[0]
            base_att = (X_base[0] - recon_base) ** 2
        else:
            base_att = np.abs(self.explainer.xgb_explainer.shap_values(X_base)[0])

        top5_base_idx = np.argsort(-base_att)[:5]
        base_set = set(feature_cols[i] for i in top5_base_idx)

        # Generate N valid physical perturbations
        perturbed_df = self.perturb_engine.generate_valid_perturbations(
            flow_row, n_samples=self.n_perturbations, jitter_pct=self.jitter_pct, audit_mode=False
        )

        # Batch pipeline transform
        X_pert = self.explainer.predictor.pipeline.transform(perturbed_df[feature_cols])
        pred_dict = self.explainer.predictor.predict_scores(perturbed_df)
        scores_arr = pred_dict.get("gated_boost", pred_dict.get("fused_inner_lofo", pred_dict["supervised"]))

        # Batch attribution vectors
        if dominant == "anomaly":
            recon_pert = self.explainer.predictor.autoencoder_model.model.predict(X_pert)
            att_mat = (X_pert - recon_pert) ** 2
        else:
            att_mat = np.abs(self.explainer.xgb_explainer.shap_values(X_pert))

        jaccards = []
        spearmans = []
        for i in range(len(perturbed_df)):
            p_att = att_mat[i]
            p_top5_idx = np.argsort(-p_att)[:5]
            p_set = set(feature_cols[j] for j in p_top5_idx)

            j_sim = compute_jaccard_similarity(base_set, p_set)
            jaccards.append(j_sim)

            sp_corr = compute_spearman_attribution_correlation(base_att, p_att)
            spearmans.append(max(0.0, sp_corr))

        mean_jaccard = float(np.mean(jaccards)) if jaccards else 1.0
        mean_spearman = float(np.mean(spearmans)) if spearmans else 1.0
        comp_exp_stab = 0.5 * (mean_jaccard + mean_spearman)

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


def compute_unified_stability_score(
    s_risk: np.ndarray,
    s_stab: np.ndarray,
    b: float
) -> np.ndarray:
    """Compute unified stability scoring formula:
    s_risk * ((1.0 - b) + b * s_stab).

    Endpoints:
      b = 0.0 -> s_risk (baseline V1)
      b = 1.0 -> s_risk * s_stab (V4b multiplicative)
    """
    return s_risk * ((1.0 - b) + b * s_stab)


def tune_stability_hyperparameters(
    val_candidates_df: pd.DataFrame,
    target_metric: str = "Precision@50",
    b_grid: Optional[List[float]] = None
) -> Dict[str, Any]:
    """Tune parameter b STRICTLY on inner-LOFO validation candidates via grid search.

    Unified Formula:
      (ii)  s_risk * ((1 - b) + b * S_exp_stab)
      (iii) s_risk * ((1 - b) + b * S_score_stab)

    Returns:
      {"b_exp": b_exp, "b_score": b_score, "exp": (1-b_exp, b_exp), "score": (1-b_score, b_score), ...}
    """
    if b_grid is None:
        b_grid = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]

    df = val_candidates_df.copy()
    y_val = df["is_attack"].to_numpy().astype(int)
    s_risk = df["base_risk_score"].to_numpy()
    s_exp = df["explanation_stability"].to_numpy()
    s_score = df["score_stability_control"].to_numpy()

    def eval_metric(y: np.ndarray, s: np.ndarray) -> float:
        if target_metric == "Precision@50":
            return compute_ranking_precision(y, s, min(50, len(y)))
        elif target_metric == "Precision@100":
            return compute_ranking_precision(y, s, min(100, len(y)))
        elif target_metric == "Precision@500":
            return compute_ranking_precision(y, s, min(500, len(y)))
        elif target_metric == "R-Precision":
            return compute_r_precision(y, s)
        return compute_ranking_precision(y, s, min(50, len(y)))

    # Base performance
    base_val_perf = eval_metric(y_val, s_risk)

    # Grid search for Variant (ii): exp_stab
    best_exp_perf = -1.0
    best_b_exp = 0.0
    for b in b_grid:
        ranked_scores = compute_unified_stability_score(s_risk, s_exp, b)
        perf = eval_metric(y_val, ranked_scores)
        if perf > best_exp_perf or (np.isclose(perf, best_exp_perf) and b < best_b_exp):
            best_exp_perf = perf
            best_b_exp = b

    # Grid search for Variant (iii): score_stab
    best_score_perf = -1.0
    best_b_score = 0.0
    for b in b_grid:
        ranked_scores = compute_unified_stability_score(s_risk, s_score, b)
        perf = eval_metric(y_val, ranked_scores)
        if perf > best_score_perf or (np.isclose(perf, best_score_perf) and b < best_b_score):
            best_score_perf = perf
            best_b_score = b

    logger.info(
        f"Inner-LOFO stability tuning: Base {target_metric}={base_val_perf:.4f} | "
        f"Exp tuned (b={best_b_exp}) -> {best_exp_perf:.4f} | "
        f"Score tuned (b={best_b_score}) -> {best_score_perf:.4f}"
    )

    a_exp = round(1.0 - best_b_exp, 2)
    a_score = round(1.0 - best_b_score, 2)

    return {
        "exp": (a_exp, best_b_exp),
        "score": (a_score, best_b_score),
        "b_exp": best_b_exp,
        "b_score": best_b_score,
        "a_exp": a_exp,
        "a_score": a_score,
        "inner_val_base_perf": base_val_perf,
        "inner_val_exp_perf": best_exp_perf,
        "inner_val_score_perf": best_score_perf,
    }


def evaluate_ranking_variants(
    test_df: pd.DataFrame,
    b_exp: float = 0.2,
    b_score: float = 0.2,
    a_exp: Optional[float] = None,
    a_score: Optional[float] = None,
    n_bootstrap: int = 1000,
    seed: int = 42,
    include_secondary: bool = False
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Evaluate ranking schemes with paired bootstrap CIs and Holm-Bonferroni correction.

    Six Variants + Rank Variant for Ties:
      (1)   V1_s_risk: s_risk (Baseline, b=0.0)
      (2)   V2_s_risk_x_exp_stab: s_risk * ((1 - b_exp) + b_exp * S_exp_stab) [DETERMINES VERDICT]
      (3)   V3_s_risk_x_score_stab: s_risk * ((1 - b_score) + b_score * S_score_stab)
      (4a)  V4a_exp_stab_alone: S_exp_stab alone
      (4b)  V4b_s_risk_x_exp_mult: s_risk * S_exp_stab (Multiplicative, b=1.0)
      (5)   V5_random_reorder: random reorder
      (6)   V2_rank: r_risk * ((1 - b_exp) + b_exp * S_exp_stab) [Rank variant for ties]

    Strict Single Verdict Rule:
      - "helped": Holm-corrected CI strictly positive (> 0) and p_adj < 0.05
      - "hurt": Holm-corrected CI strictly negative (< 0) and p_adj < 0.05
      - "no benefit detected": otherwise
    """
    from scipy.stats import rankdata
    from sklearn.metrics import roc_auc_score

    df = test_df.copy()
    y_true = df["is_attack"].to_numpy().astype(int)
    s_risk = df["base_risk_score"].to_numpy()
    s_exp = df["explanation_stability"].to_numpy()
    s_score = df["score_stability_control"].to_numpy()

    # Ties diagnostics
    rounded_risk = np.round(s_risk, 6)
    _, counts = np.unique(rounded_risk, return_counts=True)
    n_ties = int(np.sum(counts[counts > 1]))
    pct_ties = (n_ties / max(1, len(s_risk))) * 100.0

    # Normalized rank for risk ties sensitivity
    r_risk = rankdata(s_risk, method="average") / max(1, len(s_risk))

    # Reproducible random reordering
    rng = np.random.RandomState(seed)
    s_rand = rng.uniform(0.0, 1.0, size=len(df))

    # EXACT Six Variants + Rank Variant
    v1_scores = compute_unified_stability_score(s_risk, s_exp, 0.0)
    v2_scores = compute_unified_stability_score(s_risk, s_exp, b_exp)
    v3_scores = compute_unified_stability_score(s_risk, s_score, b_score)
    v4a_scores = s_exp.copy()
    v4b_scores = compute_unified_stability_score(s_risk, s_exp, 1.0)
    v5_scores = s_rand
    v2_rank_scores = r_risk * ((1.0 - b_exp) + b_exp * s_exp)

    variants = [
        ("V1_s_risk", v1_scores, "s_risk (Baseline, b=0.0)"),
        ("V2_s_risk_x_exp_stab", v2_scores, f"s_risk * ((1 - {b_exp:.1f}) + {b_exp:.1f} * S_exp) [*Determines Verdict*]"),
        ("V3_s_risk_x_score_stab", v3_scores, f"s_risk * ((1 - {b_score:.1f}) + {b_score:.1f} * S_score)"),
        ("V4a_exp_stab_alone", v4a_scores, "S_exp alone"),
        ("V4b_s_risk_x_exp_mult", v4b_scores, "s_risk * S_exp (Multiplicative, b=1.0)"),
        ("V5_random_reorder", v5_scores, "Random Reorder"),
        ("V2_rank_sensitivity", v2_rank_scores, f"r_risk * ((1 - {b_exp:.1f}) + {b_exp:.1f} * S_exp) (Rank Variant for Ties)"),
    ]

    # Metrics to evaluate
    p50_k = min(50, len(y_true))
    p100_k = min(100, len(y_true))
    metrics_to_eval = [
        ("Precision@50", lambda y, s: compute_ranking_precision(y, s, p50_k)),
        ("Precision@100", lambda y, s: compute_ranking_precision(y, s, p100_k)),
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
    candidate_vars = [v for v in variants if v[0] != "V1_s_risk"]
    boot_diffs = {
        m_name: {var_name: [] for var_name, _, _ in candidate_vars}
        for m_name, _ in metrics_to_eval
    }

    boot_rng = np.random.RandomState(seed)
    for _ in range(n_bootstrap):
        boot_idx = boot_rng.choice(n_samples, size=n_samples, replace=True)
        y_boot = y_true[boot_idx]

        for m_name, m_func in metrics_to_eval:
            v1_val = m_func(y_boot, v1_scores[boot_idx])
            for var_name, scores, _ in candidate_vars:
                var_val = m_func(y_boot, scores[boot_idx])
                delta_pp = (var_val - v1_val) * 100.0
                boot_diffs[m_name][var_name].append(delta_pp)

    n_pos = int(np.sum(y_true))
    primary_metric = "R-Precision" if n_pos < 100 else "Precision@100"

    p_values = {}
    ci_bounds = {}
    ci_bounds_p100 = {}
    ci_bounds_rprec = {}
    for var_name, _, _ in candidate_vars:
        diffs_primary = np.array(boot_diffs[primary_metric][var_name])
        ci_bounds[var_name] = (float(np.percentile(diffs_primary, 2.5)), float(np.percentile(diffs_primary, 97.5)))

        diffs_p100 = np.array(boot_diffs["Precision@100"][var_name])
        ci_bounds_p100[var_name] = (float(np.percentile(diffs_p100, 2.5)), float(np.percentile(diffs_p100, 97.5)))

        diffs_r = np.array(boot_diffs["R-Precision"][var_name])
        ci_bounds_rprec[var_name] = (float(np.percentile(diffs_r, 2.5)), float(np.percentile(diffs_r, 97.5)))

        # Two-sided empirical bootstrap p-value on primary metric
        p_val = 2.0 * min(np.mean(diffs_primary <= 0.0), np.mean(diffs_primary >= 0.0))
        p_val = float(np.clip(p_val, 1.0 / n_bootstrap, 1.0))
        p_values[var_name] = p_val

    # Apply Holm-Bonferroni correction across candidate comparisons
    sorted_vars = sorted(candidate_vars, key=lambda v: p_values[v[0]])
    m = len(sorted_vars)
    holm_adj_p = {}
    running_max_p = 0.0

    for rank, (var_name, _, _) in enumerate(sorted_vars):
        multiplier = m - rank
        raw_p = p_values[var_name]
        adj_p = min(1.0, raw_p * multiplier)
        running_max_p = max(running_max_p, adj_p)
        holm_adj_p[var_name] = min(1.0, running_max_p)

    records = []
    # Add V1 baseline row
    records.append({
        "Variant": "V1_s_risk",
        "Formula / Description": "s_risk (Baseline)",
        "Precision@50": f"{observed['V1_s_risk']['Precision@50'] * 100.0:.2f}%",
        "Precision@100": f"{observed['V1_s_risk']['Precision@100'] * 100.0:.2f}%",
        "Precision@500": "n/a" if len(df) < 500 else f"{compute_ranking_precision(y_true, v1_scores, 500)*100:.2f}%",
        "R-Precision": f"{observed['V1_s_risk']['R-Precision'] * 100.0:.2f}%",
        "Delta_P@100_pp": "0.00",
        "95% CI (Delta P@100 pp)": "[+0.00, +0.00]",
        "Delta_R_Prec_pp": "0.00",
        "95% CI (Delta R-Prec pp)": "[+0.00, +0.00]",
        "CI_Width_pp": "0.00",
        "Unadjusted_p": "1.0000",
        "Holm_Adj_p": "1.0000",
        "Verdict": "baseline",
    })

    for var_name, scores, desc in candidate_vars:
        p100_obs = observed[var_name]["Precision@100"] * 100.0
        v1_p100_obs = observed["V1_s_risk"]["Precision@100"] * 100.0
        delta_p100_pp = p100_obs - v1_p100_obs

        r_obs = observed[var_name]["R-Precision"] * 100.0
        v1_r_obs = observed["V1_s_risk"]["R-Precision"] * 100.0
        delta_r_pp = r_obs - v1_r_obs

        # Enforce CI containment: min(ci_low, delta), max(ci_high, delta)
        raw_ci_low, raw_ci_high = ci_bounds[var_name]
        delta_primary = delta_r_pp if primary_metric == "R-Precision" else delta_p100_pp
        ci_low = min(raw_ci_low, delta_primary)
        ci_high = max(raw_ci_high, delta_primary)
        ci_width = ci_high - ci_low

        raw_p100_l, raw_p100_h = ci_bounds_p100[var_name]
        ci_p100_low = min(raw_p100_l, delta_p100_pp)
        ci_p100_high = max(raw_p100_h, delta_p100_pp)

        raw_r_l, raw_r_h = ci_bounds_rprec[var_name]
        ci_r_low = min(raw_r_l, delta_r_pp)
        ci_r_high = max(raw_r_h, delta_r_pp)

        adj_p = holm_adj_p[var_name]

        # Single verdict rule:
        # holm_adj_p < 0.05 and CI excludes zero -> helped/hurt; otherwise "no benefit detected"
        if adj_p < 0.05 and ci_low > 0.0:
            verdict = "helped"
        elif adj_p < 0.05 and ci_high < 0.0:
            verdict = "hurt"
        else:
            verdict = "no benefit detected"

        ci_p100_str = f"[{'+' if ci_p100_low >= 0 else ''}{ci_p100_low:.2f}, {'+' if ci_p100_high >= 0 else ''}{ci_p100_high:.2f}]"
        ci_r_str = f"[{'+' if ci_r_low >= 0 else ''}{ci_r_low:.2f}, {'+' if ci_r_high >= 0 else ''}{ci_r_high:.2f}]"
        records.append({
            "Variant": var_name,
            "Formula / Description": desc,
            "Precision@50": f"{observed[var_name]['Precision@50'] * 100.0:.2f}%",
            "Precision@100": f"{observed[var_name]['Precision@100'] * 100.0:.2f}%",
            "Precision@500": "n/a" if len(df) < 500 else f"{compute_ranking_precision(y_true, scores, 500)*100:.2f}%",
            "R-Precision": f"{observed[var_name]['R-Precision'] * 100.0:.2f}%",
            "Delta_P@100_pp": f"{'+' if delta_p100_pp >= 0 else ''}{delta_p100_pp:.2f}",
            "95% CI (Delta P@100 pp)": ci_p100_str,
            "Delta_R_Prec_pp": f"{'+' if delta_r_pp >= 0 else ''}{delta_r_pp:.2f}",
            "95% CI (Delta R-Prec pp)": ci_r_str,
            "CI_Width_pp": f"{ci_width:.2f}",
            "Unadjusted_p": f"{p_values[var_name]:.4f}",
            "Holm_Adj_p": f"{adj_p:.4f}",
            "Verdict": verdict,
        })

    # Compute diagnostics
    auc_stab = float(roc_auc_score(y_true, s_exp)) if len(np.unique(y_true)) > 1 else np.nan
    corr_risk_exp, _ = spearmanr(s_risk, s_exp)
    mean_stab_tp = float(np.mean(s_exp[y_true == 1])) if np.sum(y_true == 1) > 0 else np.nan
    mean_stab_fp = float(np.mean(s_exp[y_true == 0])) if np.sum(y_true == 0) > 0 else np.nan

    diagnostics = {
        "n_candidates": len(df),
        "n_positives": n_pos,
        "n_ties_rounded_1e6": n_ties,
        "pct_ties": round(pct_ties, 2),
        "auc_stability_alone": round(auc_stab, 4) if not np.isnan(auc_stab) else "n/a",
        "spearman_corr_risk_stability": round(float(corr_risk_exp), 4) if not np.isnan(corr_risk_exp) else "n/a",
        "mean_stability_tp": round(mean_stab_tp, 4) if not np.isnan(mean_stab_tp) else "n/a",
        "mean_stability_fp": round(mean_stab_fp, 4) if not np.isnan(mean_stab_fp) else "n/a",
        "verdict_determining_variant": "V2_s_risk_x_exp_stab",
    }

    return pd.DataFrame(records), diagnostics


def compute_sensitivity_curve(
    stability_results_df: pd.DataFrame,
    b_values: Optional[List[float]] = None
) -> pd.DataFrame:
    """Compute Precision@50, Precision@100, Precision@500, and R-Precision across stability weight b in [0.0, 1.0]."""
    if b_values is None:
        b_values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    df = stability_results_df.copy()
    y_true = df["is_attack"].to_numpy().astype(int)
    s_risk = df["base_risk_score"].to_numpy()
    s_exp = df["explanation_stability"].to_numpy()

    records = []
    for b in b_values:
        s_fused = compute_unified_stability_score(s_risk, s_exp, b)
        p50 = compute_ranking_precision(y_true, s_fused, min(50, len(y_true)))
        p100 = compute_ranking_precision(y_true, s_fused, min(100, len(y_true))) if len(y_true) >= 100 else np.nan
        r_prec = compute_r_precision(y_true, s_fused)

        records.append({
            "b_weight": f"{b:.1f}",
            "Precision@50": f"{p50 * 100.0:.2f}%",
            "Precision@100": f"{p100 * 100.0:.2f}%" if not np.isnan(p100) else "n/a",
            "Precision@500": "n/a" if len(df) < 500 else f"{compute_ranking_precision(y_true, s_fused, 500)*100:.2f}%",
            "R-Precision": f"{r_prec * 100.0:.2f}%",
        })

    return pd.DataFrame(records)
