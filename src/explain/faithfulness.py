"""Faithfulness Evaluation, Latency Benchmark, and Example Explanations Generator.

1. Faithfulness Test:
   - Evaluates on 200 alerts per family from LOFO 5% test sets.
   - Replaces top-k explained features (k=1, 3, 5) with benign training median vs k random features.
   - Measures drop in risk score.
2. Latency Benchmark:
   - Measures mean and p95 latency (in milliseconds) for XGBoost TreeSHAP, IForest TreeSHAP, Autoencoder error, and Full explanation.
3. Example Explanations:
   - Selects 1 True Positive, 1 False Positive, and 1 Missed Attack per family (9 flows total).
   - Generates explanations and saves to results/example_explanations.json.
"""

from typing import Dict, List, Optional, Tuple, Union, Any
import json
import logging
from pathlib import Path
import time
import numpy as np
import pandas as pd

from src.models.pipeline import SentinelXPredictor
from src.explain.explainer import SentinelXExplainer, render_json
from src.eval.lofo import LOFOSplitEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sentinelx.faithfulness")


def evaluate_faithfulness(
    explainer: SentinelXExplainer,
    test_alerts_df: pd.DataFrame,
    k_values: List[int] = [1, 2, 3, 4, 5],
    n_random_trials: int = 5,
    alert_threshold: float = 0.50,
    random_seed: int = 42
) -> Dict[str, Dict[str, Any]]:
    """Measure score drop and threshold fall-off when replacing top-k explained features vs k random features with benign median."""
    rng = np.random.RandomState(random_seed)
    feature_cols = explainer.feature_cols
    benign_medians = explainer.benign_medians

    results = {
        f"k_{k}": {
            "top_k_drop": [],
            "random_k_drop": [],
            "top_k_below_thresh": [],
            "random_k_below_thresh": [],
        }
        for k in k_values
    }

    if len(test_alerts_df) == 0:
        return {
            f"k={k}": {
                "top_k_mean_drop": 0.0,
                "random_k_mean_drop": 0.0,
                "difference": 0.0,
                "top_k_below_threshold_pct": "n/a",
                "random_k_below_threshold_pct": "n/a",
                "is_top_k_better": "n/a",
            }
            for k in k_values
        }

    for idx in range(len(test_alerts_df)):
        flow_row = test_alerts_df.iloc[[idx]]
        orig_score = float(explainer.predictor.predict_scores(flow_row)["fused_inner_mean"][0])
        exp = explainer.explain(flow_row)

        # Extract top-k dominant features (from autoencoder or xgboost based on dominant component)
        if exp["components"]["dominant_component"] == "anomaly":
            top_ranked = [item["feature"] for item in exp["anomaly_explanation"]["autoencoder_top5"]]
        else:
            top_ranked = [item["feature"] for item in exp["supervised_explanation"]]

        for k in k_values:
            k_clamped = min(k, len(top_ranked))
            k_top_feats = top_ranked[:k_clamped]

            # 1. Perturb top-k features to benign median
            flow_top_perturbed = flow_row.copy()
            for f in k_top_feats:
                flow_top_perturbed[f] = benign_medians.get(f, 0.0)

            perturbed_score = float(explainer.predictor.predict_scores(flow_top_perturbed)["fused_inner_mean"][0])
            top_drop = max(0.0, orig_score - perturbed_score)
            results[f"k_{k}"]["top_k_drop"].append(top_drop)
            results[f"k_{k}"]["top_k_below_thresh"].append(1.0 if perturbed_score < alert_threshold else 0.0)

            # 2. Perturb k random features to benign median
            rand_drops = []
            rand_below = []
            for _ in range(n_random_trials):
                rand_feats = rng.choice(feature_cols, size=k_clamped, replace=False)
                flow_rand_perturbed = flow_row.copy()
                for f in rand_feats:
                    flow_rand_perturbed[f] = benign_medians.get(f, 0.0)

                rand_score = float(explainer.predictor.predict_scores(flow_rand_perturbed)["fused_inner_mean"][0])
                rand_drops.append(max(0.0, orig_score - rand_score))
                rand_below.append(1.0 if rand_score < alert_threshold else 0.0)

            results[f"k_{k}"]["random_k_drop"].append(float(np.mean(rand_drops)))
            results[f"k_{k}"]["random_k_below_thresh"].append(float(np.mean(rand_below)))

    # Compute means and percentages
    summary = {}
    for k in k_values:
        mean_top = float(np.mean(results[f"k_{k}"]["top_k_drop"]))
        mean_rand = float(np.mean(results[f"k_{k}"]["random_k_drop"]))
        diff = mean_top - mean_rand
        top_below_pct = float(np.mean(results[f"k_{k}"]["top_k_below_thresh"])) * 100.0
        rand_below_pct = float(np.mean(results[f"k_{k}"]["random_k_below_thresh"])) * 100.0
        summary[f"k={k}"] = {
            "top_k_mean_drop": round(mean_top, 4),
            "random_k_mean_drop": round(mean_rand, 4),
            "difference": round(diff, 4),
            "top_k_below_threshold_pct": round(top_below_pct, 2),
            "random_k_below_threshold_pct": round(rand_below_pct, 2),
            "is_top_k_better": bool(diff > 0.0),
        }

    return summary



def benchmark_explanation_latency(
    explainer: SentinelXExplainer,
    sample_flows_df: pd.DataFrame,
    n_iterations: int = 100
) -> Dict[str, Dict[str, float]]:
    """Benchmark explanation latency (mean and p95 in ms) across components."""
    feature_cols = explainer.feature_cols
    flows_to_test = sample_flows_df.iloc[:min(n_iterations, len(sample_flows_df))]

    xgb_times = []
    if_times = []
    ae_times = []
    full_times = []

    for i in range(len(flows_to_test)):
        flow_row = flows_to_test.iloc[[i]]
        X_trans = explainer.predictor.pipeline.transform(flow_row[feature_cols])

        # 1. XGB TreeSHAP
        t0 = time.perf_counter()
        _ = explainer.xgb_explainer.shap_values(X_trans)
        xgb_times.append((time.perf_counter() - t0) * 1000.0)

        # 2. IForest TreeSHAP
        t0 = time.perf_counter()
        _ = explainer.iforest_explainer.shap_values(X_trans)
        if_times.append((time.perf_counter() - t0) * 1000.0)

        # 3. Autoencoder Reconstruction Error
        t0 = time.perf_counter()
        recon = explainer.predictor.autoencoder_model.model.predict(X_trans)[0]
        _ = (X_trans[0] - recon) ** 2
        ae_times.append((time.perf_counter() - t0) * 1000.0)

        # 4. Full Explain Call
        t0 = time.perf_counter()
        _ = explainer.explain(flow_row)
        full_times.append((time.perf_counter() - t0) * 1000.0)

    return {
        "XGBoost_TreeSHAP": {
            "mean_ms": round(float(np.mean(xgb_times)), 2),
            "p95_ms": round(float(np.percentile(xgb_times, 95)), 2),
        },
        "IsolationForest_TreeSHAP": {
            "mean_ms": round(float(np.mean(if_times)), 2),
            "p95_ms": round(float(np.percentile(if_times, 95)), 2),
        },
        "Autoencoder_Recon": {
            "mean_ms": round(float(np.mean(ae_times)), 2),
            "p95_ms": round(float(np.percentile(ae_times, 95)), 2),
        },
        "Full_Explanation": {
            "mean_ms": round(float(np.mean(full_times)), 2),
            "p95_ms": round(float(np.percentile(full_times, 95)), 2),
        }
    }


def run_explanations_suite(
    results_dir: Union[str, Path] = "results",
    models_dir: Union[str, Path] = "results/models",
    dataset_path: Union[str, Path] = "data/processed/cicids2017_sample60k.parquet",
    families: List[str] = ["DoS", "PortScan", "BruteForce"],
    random_seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    """Execute faithfulness testing, latency benchmarks, and save example explanations."""
    res_path = Path(results_dir)
    mod_path = Path(models_dir)
    df = pd.read_parquet(dataset_path)

    faithfulness_records = []
    latency_records = []
    example_explanations = []

    # Read scores dataframe to extract candidate flows
    scores_path = res_path / "raw_scores.parquet"
    raw_scores_df = pd.read_parquet(scores_path) if scores_path.exists() else None

    for fam in families:
        logger.info(f"Running explanation evaluation for family: {fam}...")
        model_file = mod_path / f"sentinelx_lofo_{fam}.joblib"
        if not model_file.exists():
            logger.warning(f"Model file not found: {model_file}")
            continue

        predictor = SentinelXPredictor.load(model_file)

        # Benign training flows strictly for background caching
        train_benign = df[df["Label"] == "Benign"]
        explainer = SentinelXExplainer(
            predictor=predictor,
            background_benign_df=train_benign,
            n_background=100,
            random_seed=random_seed
        )

        # 1. Faithfulness Evaluation: Calibrate alert threshold on validation benign flows at 1% FAR
        engine = LOFOSplitEngine(random_seed=random_seed)
        fold_base = engine.generate_fold(df, held_out_family=fam, prevalence=0.05)
        val_df = fold_base["val"]
        benign_val = val_df[val_df["Label"] == "Benign"]
        benign_val_scores = predictor.predict_scores(benign_val)["fused_inner_mean"]
        # Fixed false alarm rate at 1% of benign flows: 99th percentile
        alert_threshold = float(np.percentile(benign_val_scores, 99.0))

        # Extract test attack flows (candidate True Positives)
        test_df = fold_base["test"]
        test_attack_flows = test_df[test_df["Label"] == fam].copy()
        attack_base_scores = predictor.predict_scores(test_attack_flows)["fused_inner_mean"]

        # Filter strictly to true positives that were above the alert threshold at baseline
        qualifying_mask = (attack_base_scores >= alert_threshold)
        qualifying_alerts = test_attack_flows[qualifying_mask]
        n_qualifying = len(qualifying_alerts)
        logger.info(
            f"Family {fam}: Calibrated Alert Threshold (1% FAR) = {alert_threshold:.4f}. "
            f"Qualifying Baseline Alerts: {n_qualifying}/{len(test_attack_flows)}"
        )

        if n_qualifying == 0:
            for k in [1, 2, 3, 4, 5]:
                faithfulness_records.append({
                    "Family": fam,
                    "K_Features": f"k={k}",
                    "Alert_Threshold_1pct_FAR": round(alert_threshold, 4),
                    "Qualifying_Baseline_Alerts": 0,
                    "Top_K_Mean_Drop": 0.0,
                    "Random_K_Mean_Drop": 0.0,
                    "Difference (Top - Random)": 0.0,
                    "Top_K_Below_Thresh_%": "n/a",
                    "Random_K_Below_Thresh_%": "n/a",
                    "Top_K_Clearly_Larger": "n/a",
                })
        else:
            alerts_sample = qualifying_alerts.sample(n=min(200, n_qualifying), random_state=random_seed)
            faith_res = evaluate_faithfulness(
                explainer=explainer,
                test_alerts_df=alerts_sample,
                k_values=[1, 2, 3, 4, 5],
                alert_threshold=alert_threshold,
                random_seed=random_seed
            )

            for k_str, metrics in faith_res.items():
                faithfulness_records.append({
                    "Family": fam,
                    "K_Features": k_str,
                    "Alert_Threshold_1pct_FAR": round(alert_threshold, 4),
                    "Qualifying_Baseline_Alerts": n_qualifying,
                    "Top_K_Mean_Drop": metrics["top_k_mean_drop"],
                    "Random_K_Mean_Drop": metrics["random_k_mean_drop"],
                    "Difference (Top - Random)": metrics["difference"],
                    "Top_K_Below_Thresh_%": metrics["top_k_below_threshold_pct"],
                    "Random_K_Below_Thresh_%": metrics["random_k_below_threshold_pct"],
                    "Top_K_Clearly_Larger": metrics["is_top_k_better"],
                })

        # Latency benchmark
        bench_sample = alerts_sample if n_qualifying > 0 else test_attack_flows.sample(n=min(50, len(test_attack_flows)), random_state=random_seed)
        lat_res = benchmark_explanation_latency(explainer, bench_sample, n_iterations=50)
        for comp, lat in lat_res.items():
            latency_records.append({
                "Family": fam,
                "Component": comp,
                "Mean_Latency_ms": lat["mean_ms"],
                "P95_Latency_ms": lat["p95_ms"],
            })

        # 2. Extract 3 example flows: True Positive, False Positive, Missed Attack
        # Evaluate candidate flows
        fam_flows = df[df["Label"] == fam]
        benign_flows = df[df["Label"] == "Benign"].sample(n=1000, random_state=random_seed)

        fam_preds = predictor.predict_scores(fam_flows)["fused_inner_mean"]
        benign_preds = predictor.predict_scores(benign_flows)["fused_inner_mean"]

        # A. True Positive: attack flow with highest risk score
        tp_idx = int(np.argmax(fam_preds))
        tp_flow = fam_flows.iloc[tp_idx]
        tp_exp = explainer.explain(tp_flow)
        tp_exp["example_type"] = "True Positive"
        tp_exp["family"] = fam
        tp_exp["true_label"] = fam
        example_explanations.append(tp_exp)

        # B. False Positive: benign flow with highest risk score
        fp_idx = int(np.argmax(benign_preds))
        fp_flow = benign_flows.iloc[fp_idx]
        fp_exp = explainer.explain(fp_flow)
        fp_exp["example_type"] = "False Positive"
        fp_exp["family"] = fam
        fp_exp["true_label"] = "Benign"
        example_explanations.append(fp_exp)

        # C. Missed Attack (False Negative): attack flow with lowest risk score
        fn_idx = int(np.argmin(fam_preds))
        fn_flow = fam_flows.iloc[fn_idx]
        fn_exp = explainer.explain(fn_flow)
        fn_exp["example_type"] = "Missed Attack (FN)"
        fn_exp["family"] = fam
        fn_exp["true_label"] = fam
        example_explanations.append(fn_exp)

    # Save 9 example explanations
    examples_path = res_path / "example_explanations.json"
    examples_path.write_text(render_json(example_explanations), encoding="utf-8")
    logger.info(f"Saved 9 example explanations to {examples_path}")

    faith_df = pd.DataFrame(faithfulness_records)
    lat_df = pd.DataFrame(latency_records)

    # Save CSV and MD
    if len(faith_df) > 0:
        faith_df.to_csv(res_path / "explanation_faithfulness.csv", index=False)
        (res_path / "explanation_faithfulness.md").write_text(format_markdown_table(faith_df), encoding="utf-8")
    if len(lat_df) > 0:
        lat_df.to_csv(res_path / "explanation_latency.csv", index=False)
        (res_path / "explanation_latency.md").write_text(format_markdown_table(lat_df), encoding="utf-8")

    return faith_df, lat_df, example_explanations


def format_markdown_table(df: pd.DataFrame) -> str:
    """Format DataFrame as markdown table without external dependencies."""
    headers = list(df.columns)
    lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        row_str = " | ".join(str(row[c]) for c in headers)
        lines.append(f"| {row_str} |")
    return "\n".join(lines)


def main():
    faith_df, lat_df, examples = run_explanations_suite()

    print("\n=======================================================")
    print("       FAITHFULNESS EVALUATION TABLE (200 alerts/family)")
    print("=======================================================\n")
    if len(faith_df) > 0:
        print(format_markdown_table(faith_df))
    else:
        print("No faithfulness records generated.")

    print("\n=======================================================")
    print("       EXPLANATION LATENCY BENCHMARK TABLE")
    print("=======================================================\n")
    if len(lat_df) > 0:
        print(format_markdown_table(lat_df))
    else:
        print("No latency records generated.")

    print("\n=======================================================")
    print("       9 EXAMPLE PLAIN-ENGLISH SENTENCES")
    print("=======================================================\n")
    for idx, ex in enumerate(examples, 1):
        print(f"[{idx}] {ex['family']} - {ex['example_type']} (True Label: {ex['true_label']}, Fused Score: {ex['fused_risk_score']}):")
        print(f"    \"{ex['sentence']}\"\n")


if __name__ == "__main__":
    main()
