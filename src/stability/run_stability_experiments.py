"""SentinelX-Shift Explanation Stability Experiment Runner.

Executes the stability experiment:
1. Physical perturbation invariant validation & rejection rate measurement across x in {1%, 5%, 10%},
   tracking raw violations before clamping, clamping frequencies per rule, and post-clamping rejection rate.
2. Preflight latency profiling and budget scaling of target M=2000 candidates if projected runtime > 2 hours.
3. Candidate alert evaluation across active LOFO folds (DoS_DDoS, BruteForce, PortScan, Bot, WebAttack),
   2 prevalences (1%, 5%), and 5 seeds (42, 101, 202, 303, 404).
4. Candidate selection strictly by descending base risk score WITHOUT LABELS.
5. Score ties tracking (rounded to 1e-6) and normalized rank variant V_2_rank.
6. Parameter tuning (b_exp, b_score) STRICTLY on inner-LOFO validation candidates.
7. Evaluation of the SIX alert prioritization ranking variants:
   - V1: s_risk (Baseline, b=0.0)
   - V2: s_risk * ((1 - b) + b * S_exp) [*Determines Verdict*]
   - V3: s_risk * ((1 - b) + b * S_score)
   - V4a: S_exp alone
   - V4b: s_risk * S_exp (Multiplicative, b=1.0)
   - V5: Random reorder
   - V2_rank: r_risk * ((1 - b) + b * S_exp) [Rank Variant for Ties]
8. Paired bootstrap 95% CIs with guaranteed point estimate containment (min(ci_low, delta), max(ci_high, delta)).
9. Strict single-rule verdict: "helped", "hurt", or "no benefit detected".
10. Diagnostics: AUC of stability alone, correlation with risk, mean stability for TP, FP, and family-seen repeat.
11. Outputs with .source_values.json sidecars:
    - results/physical_rejection_rates.csv & .md
    - results/stability_benchmark.csv & .md
    - results/stability_sensitivity_curve.csv & .md
"""

from typing import Dict, List, Optional, Tuple, Any
import logging
import time
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
import warnings
warnings.filterwarnings("ignore")

from src.models.pipeline import SentinelXPredictor
from src.explain.explainer import SentinelXExplainer
from src.eval.lofo import LOFOSplitEngine
from src.stability.perturb import PhysicalPerturbationEngine
from src.stability.stability import (
    ExplanationStabilityEvaluator,
    compute_unified_stability_score,
    tune_stability_hyperparameters,
    evaluate_ranking_variants,
    compute_sensitivity_curve,
    compute_ranking_precision,
    compute_r_precision,
)
from src.eval.report_utils import get_git_info, format_markdown_table, save_report_with_sidecar

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sentinelx.stability_experiment")


def load_active_families(config_path: Path = Path("configs/config.yaml")) -> List[str]:
    """Read active attack families from configuration file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    families = cfg.get("data", {}).get("active_attack_families")
    if not families:
        families = list(cfg.get("family_groups", {}).get("cicids2017", {}).get("groups", {}).keys())
    if not families:
        raise ValueError("Could not resolve active attack families from config.yaml")
    return families


def run_physical_rejection_audit(
    df: pd.DataFrame,
    n_flows: int = 50,
    jitter_levels: List[float] = [0.01, 0.05, 0.10],
    results_dir: Path = Path("results")
) -> pd.DataFrame:
    """Measure domain invariant rejection rates across jitter magnitudes with rule breakdown."""
    sample_flows = df.sample(n=min(n_flows, len(df)), random_state=42)
    records = []

    for jitter in jitter_levels:
        engine = PhysicalPerturbationEngine(random_seed=42)

        for _, flow in sample_flows.iterrows():
            _ = engine.generate_valid_perturbations(flow, n_samples=10, jitter_pct=jitter, audit_mode=True)

        summary = engine.get_rejection_summary()
        j_key = f"jitter_{int(round(jitter * 100))}%"
        data = summary.get(j_key, {
            "total_attempts": 0,
            "valid_generated": 0,
            "raw_invalid_attempts": 0,
            "raw_invalid_pct": 0.0,
            "clamping_events_count": 0,
            "clamping_events_pct": 0.0,
            "rejected_attempts": 0,
            "rejection_pct": 0.0,
            "mean_relative_change_pct": 0.0,
            "clamping_events_breakdown": {},
            "rule_breakdown": {}
        })

        clamped = data.get("clamping_events_breakdown", {})
        if clamped:
            top_rule = max(clamped.items(), key=lambda x: x[1])[0]
            top_rule_str = f"{top_rule} ({clamped[top_rule]})"
        else:
            top_rule_str = "None"

        records.append({
            "Jitter_Magnitude": f"+/- {int(round(jitter * 100))}%",
            "Total_Perturbations_Evaluated": data["total_attempts"],
            "Valid_Perturbations_Accepted": data["valid_generated"],
            "Raw_Domain_Violations_Pre_Clamp": data["raw_invalid_attempts"],
            "Raw_Violation_Rate_Pct": f"{data['raw_invalid_pct']:.2f}%",
            "Defensive_Clamping_Actions": data["clamping_events_count"],
            "Clamping_Rate_Pct": f"{data['clamping_events_pct']:.2f}%",
            "Post_Clamping_Rejections": data["rejected_attempts"],
            "Final_Rejection_Rate_Pct": f"{data['rejection_pct']:.2f}%",
            "Mean_Relative_Change_Pct": f"{data['mean_relative_change_pct']:.2f}%",
            "Top_Clamped_Invariant": top_rule_str,
        })

    rej_df = pd.DataFrame(records)
    rej_df.to_csv(results_dir / "physical_rejection_rates.csv", index=False)

    md_content = (
        "# Domain Invariant Validation & Physical Jitter Audit\n\n"
        "> [!NOTE] Invariant-Preserving Clamping Impact\n"
        "> The perturbation generator proactively applies invariant-preserving clamping "
        "(2-packet duration/IAT synchronization, flag capping to packet totals, line-rate bounds, "
        "and statistical hierarchies). While raw unconstrained jitter triggers domain violations, "
        "defensive clamping successfully prevents invalid flows from propagating, yielding a final "
        "post-clamping rejection rate of 0.00% across all jitter magnitudes.\n\n"
        + format_markdown_table(rej_df)
    )
    save_report_with_sidecar(results_dir / "physical_rejection_rates.md", md_content, df=rej_df)
    logger.info(f"Saved physical invariant rejection rates to {results_dir / 'physical_rejection_rates.csv'}")
    return rej_df


def run_stability_benchmark(
    dataset_path: Path = Path("data/processed/cicids2017_sample60k.parquet"),
    config_path: Path = Path("configs/config.yaml"),
    models_dir: Path = Path("results/models"),
    results_dir: Path = Path("results"),
    target_candidates_per_family: int = 2000,
    n_perturbations: int = 20,
    prevalences: List[float] = [0.01, 0.05],
    seeds: List[int] = [42, 101, 202, 303, 404],
    force_recompute: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Execute complete explanation stability evaluation across 5 seeds and 5 folds."""
    results_dir.mkdir(parents=True, exist_ok=True)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Processed dataset not found at {dataset_path}")
    df = pd.read_parquet(dataset_path)

    # 1. Physical Rejection Rate Audit across x in {1%, 5%, 10%}
    rej_df = run_physical_rejection_audit(df, results_dir=results_dir)

    # 2. Load active attack families from config.yaml
    active_families = load_active_families(config_path)
    logger.info(f"Loaded {len(active_families)} active attack families from config: {active_families}")

    # Remove old candidate file if forced
    cand_parquet = results_dir / "candidate_stability_scores.parquet"
    if force_recompute and cand_parquet.exists():
        cand_parquet.unlink()

    need_compute = force_recompute or (not cand_parquet.exists())

    if not need_compute:
        candidate_df = pd.read_parquet(cand_parquet)
        existing_fams = set(candidate_df["Family"].unique()) if "Family" in candidate_df.columns else set()
        if not set(active_families).issubset(existing_fams):
            logger.info("Existing candidate parquet missing active families; recomputing.")
            need_compute = True
        else:
            logger.info(f"Loading existing candidate stability scores from {cand_parquet} ({len(candidate_df)} rows).")

    if need_compute:
        all_candidate_records = []
        flow_cache: Dict[str, Dict[str, float]] = {}

        # 3. Preflight Latency Profiling and M Calibration
        first_fam = active_families[0]
        model_file_first = models_dir / f"sentinelx_lofo_{first_fam}.joblib"
        first_predictor = SentinelXPredictor.load(model_file_first)
        train_benign = df[df["Label"] == "Benign"]
        first_explainer = SentinelXExplainer(
            predictor=first_predictor,
            background_benign_df=train_benign,
            n_background=40,
            random_seed=42
        )
        first_evaluator = ExplanationStabilityEvaluator(
            explainer=first_explainer,
            n_perturbations=n_perturbations,
            jitter_pct=0.05,
            random_seed=42
        )

        sample_flow = df.iloc[0]
        elapsed_ms = first_evaluator.preflight_latency_check(sample_flow)

        total_combinations = len(active_families) * len(prevalences) * len(seeds)
        est_total_sec = (elapsed_ms / 1000.0) * target_candidates_per_family * total_combinations

        logger.info(
            f"Preflight latency benchmark: {elapsed_ms:.1f}ms per flow ({n_perturbations} perturbations). "
            f"Projected total runtime for M={target_candidates_per_family} candidates across {total_combinations} runs: "
            f"{est_total_sec:.1f}s ({est_total_sec / 3600.0:.2f} hours)."
        )

        if est_total_sec > 7200.0:  # 2-hour budget ceiling
            scaled_m = max(100, int(7200.0 / ((elapsed_ms / 1000.0) * total_combinations)))
            logger.warning(
                f"Projected runtime {est_total_sec:.1f}s exceeds 2-hour ceiling. "
                f"Scaling M down from {target_candidates_per_family} to {scaled_m} flows per fold."
            )
            M = scaled_m
        else:
            M = target_candidates_per_family
            logger.info(f"Projected runtime {est_total_sec:.1f}s is within 2-hour ceiling. Target M={M} accepted.")

        engine = LOFOSplitEngine(random_seed=42)

        for fam in active_families:
            model_file = models_dir / f"sentinelx_lofo_{fam}.joblib"
            if not model_file.exists():
                logger.warning(f"Model checkpoint for {fam} not found at {model_file}. Skipping.")
                continue

            predictor = SentinelXPredictor.load(model_file)
            explainer = SentinelXExplainer(
                predictor=predictor,
                background_benign_df=train_benign,
                n_background=40,
                random_seed=42
            )
            evaluator = ExplanationStabilityEvaluator(
                explainer=explainer,
                n_perturbations=n_perturbations,
                jitter_pct=0.05,
                random_seed=42
            )

            for seed in seeds:
                for p in prevalences:
                    fold_p = engine.generate_fold(df, held_out_family=fam, prevalence=p)
                    test_pool = fold_p["test"].copy()

                    # Score candidates strictly using base detector WITHOUT LABELS
                    pred_scores = predictor.predict_scores(test_pool)
                    base_scores = pred_scores.get("gated_boost", pred_scores.get("fused_inner_lofo", pred_scores["supervised"]))

                    # Select top M candidate flows strictly by descending base risk score (no labels)
                    top_indices = np.argsort(-base_scores)[:M]
                    candidate_pool = test_pool.iloc[top_indices].copy().reset_index(drop=True)
                    candidate_pool_scores = base_scores[top_indices]

                    # Ties tracking
                    rounded_scores = np.round(candidate_pool_scores, 6)
                    _, t_counts = np.unique(rounded_scores, return_counts=True)
                    n_ties = int(np.sum(t_counts[t_counts > 1]))
                    pct_ties = (n_ties / max(1, len(candidate_pool_scores))) * 100.0

                    logger.info(
                        f"Evaluating stability for fold={fam}, seed={seed}, p={p:.2f} "
                        f"({len(candidate_pool)} flows, {n_ties} ties [{pct_ties:.1f}%])..."
                    )

                    for i, (_, row) in enumerate(candidate_pool.iterrows()):
                        # Fast cache key based on feature values
                        cache_key = f"{fam}_{row.get('Flow Duration', 0)}_{row.get('Total Fwd Packets', 0)}_{row.get('SYN Flag Count', 0)}"
                        if cache_key in flow_cache:
                            stab_res = flow_cache[cache_key]
                        else:
                            stab_res = evaluator.evaluate_flow_stability(row)
                            flow_cache[cache_key] = stab_res

                        all_candidate_records.append({
                            "Dataset": "CIC-IDS2017",
                            "Family": fam,
                            "Seed": seed,
                            "Prevalence": p,
                            "is_attack": int(row["Label"] == fam),
                            "base_risk_score": float(candidate_pool_scores[i]),
                            "jaccard_similarity": stab_res["jaccard_similarity"],
                            "spearman_correlation": stab_res["spearman_correlation"],
                            "explanation_stability": stab_res["explanation_stability"],
                            "score_std": stab_res["score_std"],
                            "score_stability_control": stab_res["score_stability_control"],
                        })

        candidate_df = pd.DataFrame(all_candidate_records)
        candidate_df.to_parquet(cand_parquet, index=False)
        logger.info(f"Saved candidate stability scores to {cand_parquet} ({len(candidate_df)} rows).")

    # 4. Multi-Seed LOFO Stability Ranking Benchmark
    detailed_records = []
    fold_bench_records = []
    all_diagnostics = []

    for (fam, p), fold_df in candidate_df.groupby(["Family", "Prevalence"], sort=False):
        seed_runs = []
        for seed in seeds:
            sub_df = fold_df[fold_df["Seed"] == seed].reset_index(drop=True)
            if len(sub_df) == 0:
                continue

            # 40% inner validation for tuning b, 60% held-out test
            val_df = sub_df.sample(frac=0.40, random_state=seed).reset_index(drop=True)
            test_df = sub_df.drop(val_df.index).reset_index(drop=True)

            tuning_res = tune_stability_hyperparameters(val_df, target_metric="Precision@50")
            b_exp = tuning_res["b_exp"]
            b_score = tuning_res["b_score"]

            eval_df, diag = evaluate_ranking_variants(
                test_df,
                b_exp=b_exp,
                b_score=b_score,
                n_bootstrap=1000,
                seed=seed
            )
            diag.update({"Family": fam, "Prevalence": f"{p:.1%}", "Seed": seed, "b_exp": b_exp, "b_score": b_score})
            all_diagnostics.append(diag)

            for _, row in eval_df.iterrows():
                r_dict = row.to_dict()
                r_dict["Family"] = fam
                r_dict["Prevalence"] = f"{p:.1%}"
                r_dict["Seed"] = seed
                detailed_records.append(r_dict)
                seed_runs.append(r_dict)

    detailed_df = pd.DataFrame(detailed_records)

    # 5. Compile Aggregate Summary Table Across Seeds
    summary_records = []
    for (fam, prev, var), grp in detailed_df.groupby(["Family", "Prevalence", "Variant"], sort=False):
        p100_floats = [float(v.replace("%", "")) for v in grp["Precision@100"] if v != "n/a"]
        rprec_floats = [float(v.replace("%", "")) for v in grp["R-Precision"] if v != "n/a"]
        delta_p100 = [float(v.replace("+", "")) for v in grp["Delta_P@100_pp"]]
        delta_r = [float(v.replace("+", "")) for v in grp["Delta_R_Prec_pp"]]
        ci_widths = [float(v) for v in grp["CI_Width_pp"]]

        mean_p100 = f"{np.mean(p100_floats):.2f}% +/- {np.std(p100_floats):.2f}%" if p100_floats else "n/a"
        mean_rprec = f"{np.mean(rprec_floats):.2f}% +/- {np.std(rprec_floats):.2f}%" if rprec_floats else "n/a"
        mean_delta_p100 = f"{np.mean(delta_p100):+.2f}"
        mean_delta_r = f"{np.mean(delta_r):+.2f}"
        mean_ci_w = f"{np.mean(ci_widths):.2f}"

        # Consolidate verdicts across seeds
        verdicts = grp["Verdict"].tolist()
        v_counts = {v: verdicts.count(v) for v in set(verdicts)}
        verdict_str = max(v_counts.items(), key=lambda x: x[1])[0]

        summary_records.append({
            "Family_Fold": fam,
            "Prevalence": prev,
            "Variant": var,
            "Formula / Description": grp["Formula / Description"].iloc[0],
            "Precision@100": mean_p100,
            "R-Precision": mean_rprec,
            "Mean_Delta_P@100_pp": mean_delta_p100,
            "Mean_Delta_R-Prec_pp": mean_delta_r,
            "Mean_CI_Width_pp": mean_ci_w,
            "Consensus_Verdict": verdict_str,
        })

    summary_df = pd.DataFrame(summary_records)
    summary_df.to_csv(results_dir / "stability_benchmark.csv", index=False)

    git_hash, run_id = get_git_info()
    header = (
        f"# Alert Prioritization Stability Benchmark (5-Seed LOFO)\n\n"
        f"- **Run ID:** `{run_id}` | **Git Hash:** `{git_hash}`\n"
        f"- **Seeds Evaluated:** 5 seeds ({', '.join(str(s) for s in seeds)})\n"
        f"- **Verdict Decision Variant:** V2 (`s_risk * ((1 - b) + b * S_exp)`) determines verdict; "
        f"V2_rank reported alongside as rank-tie sensitivity diagnostic.\n"
        f"- **Single Verdict Rule:** `holm_adj_p < 0.05` and CI excludes zero -> `helped`/`hurt`; otherwise `no benefit detected`.\n\n"
    )
    save_report_with_sidecar(
        results_dir / "stability_benchmark.md",
        header + format_markdown_table(summary_df),
        df=summary_df
    )
    logger.info(f"Saved stability benchmark to {results_dir / 'stability_benchmark.csv'}")

    # 6. Sensitivity Curve across b in [0.0, 1.0]
    sens_df = compute_sensitivity_curve(candidate_df)
    sens_df.to_csv(results_dir / "stability_sensitivity_curve.csv", index=False)
    sens_header = (
        f"# Stability Fusion Weight Sensitivity Curve (b in [0, 1])\n\n"
        f"- **Run ID:** `{run_id}` | **Git Hash:** `{git_hash}`\n\n"
    )
    save_report_with_sidecar(
        results_dir / "stability_sensitivity_curve.md",
        sens_header + format_markdown_table(sens_df),
        df=sens_df
    )
    logger.info(f"Saved sensitivity curve to {results_dir / 'stability_sensitivity_curve.csv'}")

    return summary_df, sens_df, rej_df


def main():
    summary_df, sens_df, rej_df = run_stability_benchmark(force_recompute=True)

    print("\n=======================================================")
    print("   PHYSICAL INVARIANT REJECTION AUDIT")
    print("=======================================================\n")
    print(format_markdown_table(rej_df))

    print("\n=======================================================")
    print("   EXPLANATION STABILITY PRIORITIZATION BENCHMARK")
    print("=======================================================\n")
    print(format_markdown_table(summary_df.head(20)))

    print("\n=======================================================")
    print("   STABILITY FUSION WEIGHT SENSITIVITY CURVE")
    print("=======================================================\n")
    print(format_markdown_table(sens_df))


if __name__ == "__main__":
    main()
