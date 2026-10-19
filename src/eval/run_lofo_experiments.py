"""LOFO Multi-Seed Experiment Runner and Benchmarking Suite for SentinelX-Shift.

Executes 5-seed Leave-One-Attack-Family-Out (LOFO) benchmark across DoS, PortScan, and BruteForce
at 1% and 5% prevalence test sets.

Evaluates:
- Supervised XGBoost (standalone, with Precision@100)
- Isolation Forest (standalone, benign-only)
- Autoencoder (standalone, benign-only)
- Mean Anomaly (0.5 * iforest + 0.5 * autoencoder)
- Selected Best Single Detector (strictly chosen by inner-LOFO validation rule, never test data)
- Fusion: XGBoost + Mean-Anomaly (nested inner-LOFO weights)
- Fusion: XGBoost + IForest (nested inner-LOFO weights)
- Fusion: XGBoost + Autoencoder (nested inner-LOFO weights)
- Baseline: Untuned Rank Average (0.50 / 0.50)
- Baseline: Untuned Anomaly Heavy (0.20 / 0.80)
- Ablation: Gated Boost (AE + boost * I(XGB > t), t tuned on inner LOFO)
- Family-Seen Control: Trained on LOFO train + 70% of family F, tested on identical benign pool + 30% of F

Outputs:
- results/raw_scores.parquet (flow-level risk predictions for primary seed)
- results/fusion_weight_stability.csv & .md (inner LOFO weights across folds and seeds)
- results/lofo_benchmark_multi_seed.csv & .md (complete operating metrics)
- results/fusion_vs_single_comparison.csv & .md (pp differences and bootstrap 95% CIs vs selected best single)
- results/models/ model checkpoints
"""

from typing import Dict, List, Optional, Tuple, Union, Any
import logging
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
import joblib

from src.data.loader import load_config
from src.eval.lofo import LOFOSplitEngine, resample_prevalence
from src.models.detector import FeaturePipeline, XGBoostDetector
from src.models.pipeline import train_lofo_pipeline, SentinelXPredictor
from src.fusion.fuse import compute_pr_auc, compute_operating_points

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sentinelx.experiment")


def format_markdown_table(df: pd.DataFrame) -> str:
    """Format DataFrame as markdown table without external dependencies."""
    headers = list(df.columns)
    lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        row_str = " | ".join(str(row[c]) for c in headers)
        lines.append(f"| {row_str} |")
    return "\n".join(lines)


def compute_roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Compute ROC-AUC score, handling single-class edge cases."""
    if len(np.unique(y_true)) < 2:
        return 0.5
    return float(roc_auc_score(y_true, y_score))


def compute_bootstrap_ci(
    diffs: List[float],
    n_bootstraps: int = 1000,
    confidence: float = 0.95,
    random_seed: int = 42
) -> Tuple[float, float]:
    """Calculate non-parametric bootstrap confidence interval for metric differences."""
    if len(diffs) == 0:
        return 0.0, 0.0
    arr = np.asarray(diffs, dtype=float)
    if len(arr) == 1:
        return float(arr[0]), float(arr[0])

    rng = np.random.RandomState(random_seed)
    boot_means = []
    for _ in range(n_bootstraps):
        sample = rng.choice(arr, size=len(arr), replace=True)
        boot_means.append(float(np.mean(sample)))

    alpha = (1.0 - confidence) / 2.0
    ci_lower = float(np.percentile(boot_means, 100.0 * alpha))
    ci_upper = float(np.percentile(boot_means, 100.0 * (1.0 - alpha)))
    return round(ci_lower, 2), round(ci_upper, 2)


def run_family_seen_control(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    full_df: pd.DataFrame,
    held_out_family: str,
    benign_test_pool: pd.DataFrame,
    feature_cols: List[str],
    prevalences: List[float] = [0.01, 0.05],
    random_seed: int = 42,
    label_col: str = "Label"
) -> Dict[float, Dict[str, Any]]:
    """Train XGBoost on LOFO train + 70% of family F; test on the SAME benign pool + held-out 30% of F.
    
    This isolates the exact generalization cost of unseen families under identical test distribution.
    """
    fam_flows = full_df[full_df[label_col] == held_out_family]
    fam_shuffled = fam_flows.sample(frac=1.0, random_state=random_seed)
    n_tr = int(np.round(len(fam_shuffled) * 0.70))
    fam_tr = fam_shuffled.iloc[:n_tr].copy()
    fam_held_out = fam_shuffled.iloc[n_tr:].copy()

    control_train = pd.concat([train_df, fam_tr], ignore_index=True)
    pipe = FeaturePipeline(feature_cols).fit(control_train)
    X_tr = pipe.transform(control_train)
    X_val = pipe.transform(val_df)

    y_tr = (control_train[label_col] != "Benign").astype(int).to_numpy()
    y_val = (val_df[label_col] != "Benign").astype(int).to_numpy()

    xgb = XGBoostDetector(random_seed=random_seed, n_estimators=80, max_depth=4)
    xgb.fit(X_tr, y_tr, X_val, y_val)

    control_results = {}
    for p in prevalences:
        resamp = resample_prevalence(
            benign_test=benign_test_pool,
            attack_test=fam_held_out,
            target_prevalence=p,
            random_seed=random_seed
        )
        sub_test = resamp["test_df"]
        X_sub = pipe.transform(sub_test)
        s_sub = xgb.predict_scores(X_sub)
        y_sub = (sub_test[label_col] == held_out_family).astype(int).to_numpy()

        ops = compute_operating_points(y_sub, s_sub)
        control_results[p] = {
            "roc_auc": compute_roc_auc(y_sub, s_sub),
            "pr_auc": compute_pr_auc(y_sub, s_sub),
            **ops,
            "test_samples": len(sub_test),
            "positives": int(np.sum(y_sub)),
        }

    return control_results


def run_full_lofo_experiments(
    dataset_path: Union[str, Path] = "data/processed/cicids2017_sample60k.parquet",
    families: Optional[List[str]] = None,
    prevalences: List[float] = [0.01, 0.05],
    seeds: List[int] = [42, 101, 202, 303, 404],
    results_dir: Union[str, Path] = "results"
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Execute complete 5-seed LOFO benchmark suite across families and prevalence levels."""
    res_dir = Path(results_dir)
    res_dir.mkdir(parents=True, exist_ok=True)
    models_dir = res_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(dataset_path)
    if families is None:
        families = ["DoS", "PortScan", "BruteForce"]

    feature_cols = [c for c in df.columns if c != "Label"]
    logger.info(f"Loaded dataset: {len(df):,} rows, {len(feature_cols)} features. Running {len(seeds)} seeds...")

    raw_scores_records = []
    seed_records = []
    fusion_stability_records = []

    # Cache trained models and engines for two-stage evaluation
    run_cache = []
    fold_inner_detector_scores = {fam: {"Isolation_Forest": [], "Autoencoder": [], "Mean_Anomaly": []} for fam in families}

    for seed_idx, seed in enumerate(seeds):
        logger.info(f"\n=======================================================")
        logger.info(f"=== SEED {seed} ({seed_idx + 1}/{len(seeds)}) ===")
        logger.info(f"=======================================================")

        engine = LOFOSplitEngine(
            random_seed=seed,
            manifest_dir=res_dir / "manifests",
            models_dir=models_dir
        )

        for fam in families:
            logger.info(f"--- [Seed {seed}] Training LOFO Pipeline for: {fam} ---")
            fold_base = engine.generate_fold(df, held_out_family=fam, prevalence=0.05)
            train_df = fold_base["train"]
            val_df = fold_base["val"]

            predictor = train_lofo_pipeline(
                train_df=train_df,
                val_df=val_df,
                held_out_family=fam,
                feature_cols=feature_cols,
                random_seed=seed
            )

            # Record inner LOFO detector scores for fixed rule selection
            for det in ["Isolation_Forest", "Autoencoder", "Mean_Anomaly"]:
                sc = predictor.inner_detector_means.get(det, 0.0)
                fold_inner_detector_scores[fam][det].append(sc)

            # Record inner LOFO fusion parameters and stability
            fusion_stability_records.append({
                "Seed": seed,
                "Family": fam,
                "w1_mean": round(predictor.fusion.w1_inner_mean, 2),
                "w2_mean": round(predictor.fusion.w2_inner_mean, 2),
                "w1_iforest": round(predictor.fusion.w1_inner_iforest, 2),
                "w2_iforest": round(predictor.fusion.w2_inner_iforest, 2),
                "w1_ae": round(predictor.fusion.w1_inner_ae, 2),
                "w2_ae": round(predictor.fusion.w2_inner_ae, 2),
                "gated_t": round(predictor.fusion.t_gated, 2),
                "gated_boost": round(predictor.fusion.boost_gated, 2),
                "rule_selected_single_seed": predictor.rule_selected_single,
            })

            # Persist model checkpoint for primary seed 42
            if seed == 42:
                model_save_path = models_dir / f"sentinelx_lofo_{fam}.joblib"
                predictor.save(model_save_path)

            # Run Family-Seen Control for this fold & seed
            benign_pool_for_control = fold_base["test"][fold_base["test"]["Label"] == "Benign"]
            control_results = run_family_seen_control(
                train_df=train_df,
                val_df=val_df,
                full_df=df,
                held_out_family=fam,
                benign_test_pool=benign_pool_for_control,
                feature_cols=feature_cols,
                prevalences=prevalences,
                random_seed=seed
            )

            run_cache.append({
                "seed": seed,
                "fam": fam,
                "predictor": predictor,
                "engine": engine,
                "control_results": control_results,
            })

    # ONE FIXED RULE: Highest mean inner-LOFO PR-AUC across all seeds, per fold
    fixed_best_single = {}
    for fam in families:
        avg_scores = {det: float(np.mean(fold_inner_detector_scores[fam][det])) for det in fold_inner_detector_scores[fam]}
        fixed_det = max(avg_scores.keys(), key=lambda k: avg_scores[k])
        fixed_best_single[fam] = fixed_det
        logger.info(
            f"Fold {fam} Fixed Rule-Selected Single Detector: '{fixed_det}' "
            f"(5-Seed Mean Inner PR-AUCs: {avg_scores})"
        )

    # Evaluate test sets with the single fixed rule-selected detector per fold
    for item in run_cache:
        seed = item["seed"]
        fam = item["fam"]
        predictor = item["predictor"]
        engine = item["engine"]
        control_results = item["control_results"]
        rule_name = fixed_best_single[fam]

        for p in prevalences:
            fold_p = engine.generate_fold(df, held_out_family=fam, prevalence=p)
            test_df = fold_p["test"].copy()

            pred_dict = predictor.predict_scores(test_df)
            y_test = (test_df["Label"] == fam).astype(int).to_numpy()

            # Record raw flow-level scores for primary seed 42
            if seed == 42:
                for i in range(len(test_df)):
                    raw_scores_records.append({
                        "fold": f"LOFO_{fam}",
                        "prevalence": p,
                        "flow_id": f"{fam}_{int(p*100)}pct_flow_{i}",
                        "label": test_df["Label"].iloc[i],
                        "is_attack": int(y_test[i]),
                        "supervised": float(pred_dict["supervised"][i]),
                        "iforest": float(pred_dict["iforest"][i]),
                        "autoencoder": float(pred_dict["autoencoder"][i]),
                        "mean_anomaly": float(pred_dict["mean_anomaly"][i]),
                        "fused_val": float(pred_dict["fused_val"][i]),
                        "fused_inner_lofo": float(pred_dict["fused_inner_lofo"][i]),
                        "fused_inner_iforest": float(pred_dict["fused_inner_iforest"][i]),
                        "fused_inner_ae": float(pred_dict["fused_inner_ae"][i]),
                        "rank_average": float(pred_dict["rank_average"][i]),
                        "anomaly_heavy": float(pred_dict["anomaly_heavy"][i]),
                        "gated_boost": float(pred_dict["gated_boost"][i]),
                        "max_fusion": float(pred_dict["max_fusion"][i]),
                        "logistic_stack": float(pred_dict["logistic_stack"][i]),
                    })

            # Methods to evaluate
            methods_dict = {
                "Supervised_XGBoost": pred_dict["supervised"],
                "Isolation_Forest": pred_dict["iforest"],
                "Autoencoder": pred_dict["autoencoder"],
                "Mean_Anomaly": pred_dict["mean_anomaly"],
                "Fusion_XGB_Mean_Anomaly": pred_dict["fused_inner_mean"],
                "Fusion_XGB_IForest": pred_dict["fused_inner_iforest"],
                "Fusion_XGB_AE": pred_dict["fused_inner_ae"],
                "Baseline_Rank_Average_0.5_0.5": pred_dict["rank_average"],
                "Baseline_Anomaly_Heavy_0.2_0.8": pred_dict["anomaly_heavy"],
                "Ablation_Gated_Boost_AE_plus_XGB": pred_dict["gated_boost"],
            }

            p_metrics = {}
            for m_name, s_arr in methods_dict.items():
                roc = compute_roc_auc(y_test, s_arr)
                pr = compute_pr_auc(y_test, s_arr)
                ops = compute_operating_points(y_test, s_arr)
                p_metrics[m_name] = {
                    "roc_auc": roc,
                    "pr_auc": pr,
                    **ops,
                }

            # Best single detector metrics using strictly the fixed rule detector across all seeds
            best_single_metrics = p_metrics[rule_name].copy()
            best_single_metrics["source_detector"] = rule_name

            fam_ctrl_p = control_results[p]

            all_eval_methods = {
                **p_metrics,
                f"Selected_Best_Single [*] (Rule: {rule_name})": best_single_metrics,
                "Family_Seen_Control": fam_ctrl_p,
            }

            for m_name, m_data in all_eval_methods.items():
                diff_roc_pp = (m_data["roc_auc"] - best_single_metrics["roc_auc"]) * 100.0
                diff_pr_pp = (m_data["pr_auc"] - best_single_metrics["pr_auc"]) * 100.0

                seed_records.append({
                    "Seed": seed,
                    "Family": fam,
                    "Prevalence": f"{p:.1%}",
                    "Method": m_name,
                    "ROC_AUC": m_data["roc_auc"],
                    "PR_AUC": m_data["pr_auc"],
                    "Diff_ROC_pp": diff_roc_pp,
                    "Diff_PR_pp": diff_pr_pp,
                    "FA_per_10k_rec90": m_data["fa_per_10k_recall90"],
                    "FA_per_10k_rec50": m_data["fa_per_10k_recall50"],
                    "Precision_at_100": m_data["precision_at_100"],
                    "Precision_at_500": m_data["precision_at_500"],
                    "R_Precision": m_data.get("r_precision", 0.0),
                    "Test_Samples": len(test_df),
                    "Positives": int(np.sum(y_test)),
                })

    # Save raw scores parquet
    raw_df = pd.DataFrame(raw_scores_records)
    raw_scores_path = res_dir / "raw_scores.parquet"
    raw_df.to_parquet(raw_scores_path, index=False)
    logger.info(f"Saved flow score predictions to {raw_scores_path}")

    # Build Fusion Weight Stability & Variability Tables
    fusion_stab_df = pd.DataFrame(fusion_stability_records)
    fusion_stab_csv = res_dir / "fusion_weight_stability.csv"
    fusion_stab_df.to_csv(fusion_stab_csv, index=False)

    # Compute fold variability and flag degenerate tuning
    variability_records = []
    for fam in families:
        fam_df = fusion_stab_df[fusion_stab_df["Family"] == fam]
        for sig_name, col1, col2 in [
            ("XGB + Mean_Anomaly", "w1_mean", "w2_mean"),
            ("XGB + IForest", "w1_iforest", "w2_iforest"),
            ("XGB + Autoencoder", "w1_ae", "w2_ae"),
        ]:
            w1_arr = fam_df[col1].to_numpy()
            w2_arr = fam_df[col2].to_numpy()
            n_extreme = int(np.sum((np.isclose(w1_arr, 1.0)) | (np.isclose(w2_arr, 1.0))))
            status = "Degenerate Tuning" if n_extreme > 2 else "Stable"
            variability_records.append({
                "Family": fam,
                "Fusion_Signal": sig_name,
                "Mean_w1": f"{np.mean(w1_arr):.2f} +/- {np.std(w1_arr):.2f}",
                "Mean_w2": f"{np.mean(w2_arr):.2f} +/- {np.std(w2_arr):.2f}",
                "Extreme_Seeds_Count (w1=1.0 or w2=1.0)": f"{n_extreme}/{len(w1_arr)}",
                "Tuning_Status": status,
            })
    variability_df = pd.DataFrame(variability_records)
    var_csv = res_dir / "fusion_weight_variability.csv"
    variability_df.to_csv(var_csv, index=False)
    var_md = res_dir / "fusion_weight_variability.md"
    var_md.write_text(format_markdown_table(variability_df), encoding="utf-8")

    # Combine both in fusion_weight_stability.md
    fusion_stab_md = res_dir / "fusion_weight_stability.md"
    combined_stab_content = (
        "## Per-Seed Inner-LOFO Fusion Weights\n\n"
        + format_markdown_table(fusion_stab_df)
        + "\n\n## Fusion-Weight Variability & Degenerate Tuning Summary\n\n"
        + format_markdown_table(variability_df)
    )
    fusion_stab_md.write_text(combined_stab_content, encoding="utf-8")
    logger.info(f"Saved fusion weight stability to {fusion_stab_csv} and variability to {var_csv}")

    # Build multi-seed aggregated metrics
    seed_df = pd.DataFrame(seed_records)

    agg_records = []
    diff_records = []

    grouped = seed_df.groupby(["Family", "Prevalence", "Method"], sort=False)
    for (fam, prev, method), group in grouped:
        roc_mean = float(group["ROC_AUC"].mean())
        roc_std = float(group["ROC_AUC"].std())
        pr_mean = float(group["PR_AUC"].mean())
        pr_std = float(group["PR_AUC"].std())

        fa90_mean = float(group["FA_per_10k_rec90"].mean())
        fa90_std = float(group["FA_per_10k_rec90"].std())
        fa50_mean = float(group["FA_per_10k_rec50"].mean())
        fa50_std = float(group["FA_per_10k_rec50"].std())

        p100_mean = float(group["Precision_at_100"].mean())
        p100_std = float(group["Precision_at_100"].std())
        p500_mean = float(group["Precision_at_500"].mean())
        p500_std = float(group["Precision_at_500"].std())
        r_prec_mean = float(group["R_Precision"].mean())
        r_prec_std = float(group["R_Precision"].std())

        agg_records.append({
            "Family": fam,
            "Prevalence": prev,
            "Method": method,
            "ROC_AUC": f"{roc_mean:.4f} +/- {roc_std:.4f}",
            "PR_AUC": f"{pr_mean:.4f} +/- {pr_std:.4f}",
            "FA@90% Recall (per 10k)": f"{fa90_mean:.1f} +/- {fa90_std:.1f}",
            "FA@50% Recall (per 10k)": f"{fa50_mean:.1f} +/- {fa50_std:.1f}",
            "P@100": f"{p100_mean:.4f} +/- {p100_std:.4f}",
            "P@500": f"{p500_mean:.4f} +/- {p500_std:.4f}",
            "R-Precision": f"{r_prec_mean:.4f} +/- {r_prec_std:.4f}",
            "Test_Samples": group["Test_Samples"].iloc[0],
            "Positives": group["Positives"].iloc[0],
        })

        # Record fusion vs best single comparison rows
        if (
            method.startswith("Fusion_")
            or "Selected_Best_Single" in method
            or method.startswith("Baseline_")
            or method.startswith("Ablation_")
            or method == "Supervised_XGBoost"
            or method == "Family_Seen_Control"
        ):
            roc_diff_mean = float(group["Diff_ROC_pp"].mean())
            roc_diff_std = float(group["Diff_ROC_pp"].std())
            pr_diff_mean = float(group["Diff_PR_pp"].mean())
            pr_diff_std = float(group["Diff_PR_pp"].std())

            ci_roc_low, ci_roc_high = compute_bootstrap_ci(group["Diff_ROC_pp"].tolist())
            ci_pr_low, ci_pr_high = compute_bootstrap_ci(group["Diff_PR_pp"].tolist())
            ci_pr_width = ci_pr_high - ci_pr_low
            ci_roc_width = ci_roc_high - ci_roc_low

            is_uncertain = (ci_pr_width > 20.0 or ci_roc_width > 20.0)
            reliability = "Uncertain (CI width > 20pp)" if is_uncertain else "Reliable"

            diff_records.append({
                "Family": fam,
                "Prevalence": prev,
                "Method": method,
                "ROC_AUC": f"{roc_mean:.4f} +/- {roc_std:.4f}",
                "Delta_ROC_AUC_pp": f"{roc_diff_mean:+.2f} +/- {roc_diff_std:.2f}",
                "95% CI (ROC-AUC pp)": f"[{ci_roc_low:+.2f}, {ci_roc_high:+.2f}]",
                "PR_AUC": f"{pr_mean:.4f} +/- {pr_std:.4f}",
                "Delta_PR_AUC_pp": f"{pr_diff_mean:+.2f} +/- {pr_diff_std:.2f}",
                "95% CI (PR-AUC pp)": f"[{ci_pr_low:+.2f}, {ci_pr_high:+.2f}]",
                "Reliability": reliability,
                "P@100": f"{p100_mean:.4f} +/- {p100_std:.4f}",
                "R-Precision": f"{r_prec_mean:.4f} +/- {r_prec_std:.4f}",
            })

    agg_df = pd.DataFrame(agg_records)
    diff_df = pd.DataFrame(diff_records)

    # Save CSV and Markdown
    agg_csv = res_dir / "lofo_benchmark_multi_seed.csv"
    agg_df.to_csv(agg_csv, index=False)
    agg_md = res_dir / "lofo_benchmark_multi_seed.md"
    agg_md.write_text(format_markdown_table(agg_df), encoding="utf-8")

    diff_csv = res_dir / "fusion_vs_single_comparison.csv"
    diff_df.to_csv(diff_csv, index=False)
    diff_md = res_dir / "fusion_vs_single_comparison.md"
    diff_md.write_text(format_markdown_table(diff_df), encoding="utf-8")

    logger.info(f"Saved multi-seed results to {agg_csv} and {diff_csv}")
    return agg_df, diff_df, raw_df, fusion_stab_df, variability_df


def main():
    config = load_config()
    dataset_path = Path(config["data"]["output_parquet"])
    agg_df, diff_df, _, fusion_stab_df, variability_df = run_full_lofo_experiments(
        dataset_path=dataset_path,
        seeds=[42, 101, 202, 303, 404]
    )

    print("\n=======================================================")
    print("   FUSION WEIGHT STABILITY & DEGENERATE TUNING SUMMARY")
    print("=======================================================\n")
    print(format_markdown_table(variability_df))

    print("\n=======================================================")
    print("   SENTINELX-SHIFT 5-SEED LOFO BENCHMARK TABLE")
    print("=======================================================\n")
    print(format_markdown_table(agg_df))

    print("\n=======================================================")
    print("   FUSION VS BEST SINGLE DETECTOR COMPARISON (pp GAINS & 95% CIs)")
    print("=======================================================\n")
    print(format_markdown_table(diff_df))

    print("\n=======================================================")
    print("   FUSION WEIGHT STABILITY (NESTED INNER-LOFO)")
    print("=======================================================\n")
    print(format_markdown_table(fusion_stab_df))

    print("\n=======================================================")
    print("   SENTINELX-SHIFT 5-SEED LOFO BENCHMARK TABLE")
    print("=======================================================\n")
    print(format_markdown_table(agg_df))

    print("\n=======================================================")
    print("   FUSION VS BEST SINGLE DETECTOR COMPARISON (pp GAINS & 95% CIs)")
    print("=======================================================\n")
    print(format_markdown_table(diff_df))


if __name__ == "__main__":
    main()
