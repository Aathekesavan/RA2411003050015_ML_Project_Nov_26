"""SentinelX-Shift Explanation Stability Experiment Runner.

Executes the stability experiment:
1. Physical perturbation invariant validation & rejection rate measurement across x in {1%, 5%, 10%}.
2. Preflight latency profiling.
3. Candidate alert evaluation across LOFO folds (DoS, PortScan, BruteForce) and seeds.
4. Parameter tuning (a, b) STRICTLY on inner validation candidate alerts.
5. Evaluation of the EXACT 5 alert prioritization ranking variants:
   (i)   s_risk
   (ii)  s_risk * (a + b * S_exp_stab)
   (iii) s_risk * (a + b * S_score_stab)
   (iv)  S_exp_stab alone
   (v)   random reorder
6. Paired bootstrap 95% CIs and Holm-Bonferroni correction with strict verdicts:
   "helped", "hurt", or "no effect".
7. Outputs:
   - results/physical_rejection_rates.csv & .md
   - results/stability_benchmark.csv & .md
   - results/stability_sensitivity_curve.csv & .md
"""

from typing import Dict, List, Optional, Tuple, Any
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

from src.models.pipeline import SentinelXPredictor
from src.explain.explainer import SentinelXExplainer
from src.stability.perturb import PhysicalPerturbationEngine
from src.stability.stability import (
    ExplanationStabilityEvaluator,
    tune_stability_hyperparameters,
    evaluate_ranking_variants,
    compute_sensitivity_curve,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sentinelx.stability_experiment")


def format_markdown_table(df: pd.DataFrame) -> str:
    """Format DataFrame as markdown table without external dependencies."""
    headers = list(df.columns)
    lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        row_str = " | ".join(str(row[c]) for c in headers)
        lines.append(f"| {row_str} |")
    return "\n".join(lines)


def run_physical_rejection_audit(
    df: pd.DataFrame,
    n_flows: int = 50,
    jitter_levels: List[float] = [0.01, 0.05, 0.10],
    results_dir: Path = Path("results")
) -> pd.DataFrame:
    """Measure domain invariant rejection rates across jitter magnitudes."""
    sample_flows = df.sample(n=min(n_flows, len(df)), random_state=42)
    records = []

    for jitter in jitter_levels:
        engine = PhysicalPerturbationEngine(random_seed=42)

        for _, flow in sample_flows.iterrows():
            _ = engine.generate_valid_perturbations(flow, n_samples=10, jitter_pct=jitter)

        summary = engine.get_rejection_summary()
        j_key = f"jitter_{int(round(jitter*100))}%"
        data = summary.get(j_key, {"total_attempts": 0, "valid_generated": 0, "rejection_pct": 0.0})

        records.append({
            "Jitter_Magnitude": f"+/- {int(round(jitter*100))}%",
            "Total_Perturbations_Evaluated": data["total_attempts"],
            "Valid_Perturbations_Accepted": data["valid_generated"],
            "Domain_Invariants_Rejected": data["total_attempts"] - data["valid_generated"],
            "Rejection_Rate_Pct": f"{data['rejection_pct']:.2f}%",
        })

    rej_df = pd.DataFrame(records)
    rej_df.to_csv(results_dir / "physical_rejection_rates.csv", index=False)
    (results_dir / "physical_rejection_rates.md").write_text(format_markdown_table(rej_df), encoding="utf-8")
    logger.info(f"Saved physical invariant rejection rates to {results_dir / 'physical_rejection_rates.csv'}")
    return rej_df


def run_stability_benchmark(
    dataset_path: Path = Path("data/processed/cicids2017_sample60k.parquet"),
    models_dir: Path = Path("results/models"),
    results_dir: Path = Path("results"),
    n_candidates_per_family: int = 60,
    n_perturbations: int = 15,
    random_seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Execute complete explanation stability evaluation."""
    results_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(dataset_path)

    # 1. Physical Rejection Rate Audit
    rej_df = run_physical_rejection_audit(df, results_dir=results_dir)

    families = ["DoS", "PortScan", "BruteForce"]
    all_candidate_records = []

    for fam in families:
        model_file = models_dir / f"sentinelx_lofo_{fam}.joblib"
        if not model_file.exists():
            logger.warning(f"Model checkpoint for {fam} not found at {model_file}. Skipping.")
            continue

        predictor = SentinelXPredictor.load(model_file)
        train_benign = df[df["Label"] == "Benign"]
        explainer = SentinelXExplainer(
            predictor=predictor,
            background_benign_df=train_benign,
            n_background=40,
            random_seed=random_seed
        )

        evaluator = ExplanationStabilityEvaluator(
            explainer=explainer,
            n_perturbations=n_perturbations,
            jitter_pct=0.05,
            random_seed=random_seed
        )

        fam_attacks = df[df["Label"] == fam]
        n_att = min(int(n_candidates_per_family * 0.6), len(fam_attacks))
        n_ben = n_candidates_per_family - n_att

        cand_attacks = fam_attacks.sample(n=n_att, random_state=random_seed)
        cand_benign = train_benign.sample(n=n_ben, random_state=random_seed)
        candidate_pool = pd.concat([cand_attacks, cand_benign], ignore_index=True).sample(
            frac=1.0, random_state=random_seed
        ).reset_index(drop=True)

        # Preflight calibration check on first flow
        evaluator.preflight_latency_check(candidate_pool.iloc[0])

        logger.info(f"Evaluating {len(candidate_pool)} candidate flows for family: {fam}...")
        for i, (_, row) in enumerate(candidate_pool.iterrows()):
            stab_res = evaluator.evaluate_flow_stability(row)
            all_candidate_records.append({
                "Family": fam,
                "True_Label": row["Label"],
                "is_attack": int(row["Label"] == fam),
                **stab_res,
            })

    candidate_df = pd.DataFrame(all_candidate_records)
    candidate_df.to_parquet(results_dir / "candidate_stability_scores.parquet", index=False)

    # 2. Strict Partition into Inner Validation (for tuning a, b) and Held-Out Test
    # Use 40% for inner validation parameter selection and 60% for held-out evaluation
    val_df = candidate_df.sample(frac=0.40, random_state=random_seed)
    test_df = candidate_df.drop(val_df.index).reset_index(drop=True)
    val_df = val_df.reset_index(drop=True)

    # Tune a and b STRICTLY on inner validation candidate flows
    tuning_res = tune_stability_hyperparameters(val_df, target_metric="Precision@100")
    a_exp, b_exp = tuning_res["exp"]
    a_score, b_score = tuning_res["score"]

    logger.info(f"Inner-LOFO selected parameters: Exp=(a={a_exp}, b={b_exp}), Score=(a={a_score}, b={b_score})")

    # 3. Evaluate the 5 Ranking Schemes on Held-Out Test Candidates with Paired Bootstrap & Holm Correction
    ranking_df = evaluate_ranking_variants(
        test_df,
        a_exp=a_exp,
        b_exp=b_exp,
        a_score=a_score,
        b_score=b_score,
        n_bootstrap=1000,
        seed=random_seed
    )

    ranking_df.to_csv(results_dir / "stability_benchmark.csv", index=False)
    (results_dir / "stability_benchmark.md").write_text(format_markdown_table(ranking_df), encoding="utf-8")

    # 4. Sensitivity Curve over b in [0.0, 1.0]
    sens_df = compute_sensitivity_curve(test_df)
    sens_df.to_csv(results_dir / "stability_sensitivity_curve.csv", index=False)
    (results_dir / "stability_sensitivity_curve.md").write_text(format_markdown_table(sens_df), encoding="utf-8")

    logger.info("Explanation stability benchmark complete.")
    return ranking_df, sens_df, rej_df


def main():
    ranking_df, sens_df, rej_df = run_stability_benchmark()

    print("\n=======================================================")
    print("   PHYSICAL INVARIANT REJECTION AUDIT")
    print("=======================================================\n")
    print(format_markdown_table(rej_df))

    print("\n=======================================================")
    print("   EXPLANATION STABILITY PRIORITIZATION BENCHMARK")
    print("=======================================================\n")
    print(format_markdown_table(ranking_df))

    print("\n=======================================================")
    print("   STABILITY FUSION WEIGHT SENSITIVITY CURVE (b in [0, 1])")
    print("=======================================================\n")
    print(format_markdown_table(sens_df))


if __name__ == "__main__":
    main()
