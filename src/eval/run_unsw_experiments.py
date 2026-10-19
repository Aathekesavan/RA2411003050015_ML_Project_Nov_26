"""UNSW-NB15 Multi-Seed LOFO Benchmark Runner, Leakage Audit, and Cross-Dataset Aggregator.

Executes Leave-One-Attack-Family-Group-Out on UNSW-NB15 across 5 seeds:
- Groups: Recon_Analysis, Exploit_Payload, DoS, Fuzzers, Generic
- Prevalences: 1% and 5%
- 5 Seeds: 42, 101, 202, 303, 404
- Fixed Best Single Detector rule (highest mean inner-LOFO PR-AUC across seeds per fold)
- Evaluates fusion weight stability and degenerate tuning
- Programmatically recomputes results/cross_dataset_comparison.csv & .md reading strictly from saved result files
"""

from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler, MinMaxScaler

from src.data.adapters.unswnb15 import UNSWNB15Adapter
from src.data.adapters.cicids2017 import CICIDS2017Adapter
from src.data.adapters.lycos2017 import LYCOS2017Adapter
from src.data.adapters.cicids2018 import CICIDS2018Adapter
from src.eval.lofo import resample_prevalence
from src.models.detector import FeaturePipeline, XGBoostDetector
from src.models.pipeline import train_lofo_pipeline
from src.fusion.fuse import compute_pr_auc, compute_operating_points

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sentinelx.unsw_eval")


def format_markdown_table(df: pd.DataFrame) -> str:
    """Format DataFrame as markdown table without external dependencies."""
    headers = list(df.columns)
    lines = ["| " + " | ".join(str(h) for h in headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in df.iterrows():
        row_str = " | ".join(str(row[c]) for c in headers)
        lines.append(f"| {row_str} |")
    return "\n".join(lines)


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


def run_unsw_leakage_audit(
    df: pd.DataFrame,
    groups: List[str],
    feature_cols: List[str],
    results_dir: Path,
    random_seed: int = 42
) -> pd.DataFrame:
    """Compute 3-decimal, log1p, and kNN nearest-neighbor leakage for UNSW-NB15."""
    logger.info("Computing UNSW-NB15 Leakage Audit across family groups...")
    audit_records = []

    # 1. Random 70/30 split
    rng = np.random.RandomState(random_seed)
    shuffled_idx = rng.permutation(len(df))
    n_tr = int(round(len(df) * 0.70))
    rand_tr = df.iloc[shuffled_idx[:n_tr]].copy()
    rand_te = df.iloc[shuffled_idx[n_tr:]].copy()

    # Scale for standard near-duplicate check
    scaler_std = MinMaxScaler()
    X_tr_std = pd.DataFrame(scaler_std.fit_transform(rand_tr[feature_cols]), columns=feature_cols, index=rand_tr.index)
    X_te_std = pd.DataFrame(scaler_std.transform(rand_te[feature_cols]), columns=feature_cols, index=rand_te.index)

    # Scale for log1p near-duplicate check
    scaler_log = MinMaxScaler()
    X_tr_log = pd.DataFrame(scaler_log.fit_transform(np.log1p(np.maximum(0, rand_tr[feature_cols]))), columns=feature_cols, index=rand_tr.index)
    X_te_log = pd.DataFrame(scaler_log.transform(np.log1p(np.maximum(0, rand_te[feature_cols]))), columns=feature_cols, index=rand_te.index)

    # Scale for kNN distance
    scaler_knn = StandardScaler()
    X_tr_knn = scaler_knn.fit_transform(np.log1p(np.maximum(0, rand_tr[feature_cols])))
    X_te_knn = scaler_knn.transform(np.log1p(np.maximum(0, rand_te[feature_cols])))

    # Epsilon from benign training
    b_tr_knn = X_tr_knn[(rand_tr["Label"] == "Benign").to_numpy()]
    nn_b = NearestNeighbors(n_neighbors=2, metric="euclidean", n_jobs=1).fit(b_tr_knn[:10000])
    dists_b, _ = nn_b.kneighbors(b_tr_knn[:10000])
    epsilon = float(np.percentile(dists_b[:, 1], 5.0))

    nn_rand_train = NearestNeighbors(n_neighbors=1, metric="euclidean", n_jobs=1).fit(X_tr_knn)

    for grp in groups:
        # Random split test positives for this group
        te_mask_series = (rand_te["Family_Group"] == grp)
        te_mask_np = te_mask_series.to_numpy()
        n_pos_rand = int(te_mask_series.sum())
        if n_pos_rand == 0:
            continue

        # Random 3-dec leakage
        tr_3dec = set(X_tr_std.round(3).itertuples(index=False, name=None))
        te_grp_3dec = list(X_te_std[te_mask_series].round(3).itertuples(index=False, name=None))
        rand_near_cnt = sum(1 for t in te_grp_3dec if t in tr_3dec)
        rand_near_pct = (rand_near_cnt / n_pos_rand) * 100.0

        # Random log1p 3-dec leakage
        tr_log_3dec = set(X_tr_log.round(3).itertuples(index=False, name=None))
        te_grp_log_3dec = list(X_te_log[te_mask_series].round(3).itertuples(index=False, name=None))
        rand_log_cnt = sum(1 for t in te_grp_log_3dec if t in tr_log_3dec)
        rand_log_pct = (rand_log_cnt / n_pos_rand) * 100.0

        # Random NN distance
        dists_rand, _ = nn_rand_train.kneighbors(X_te_knn[te_mask_np])
        rand_med_nn = float(np.median(dists_rand[:, 0]))
        rand_pct_eps = float(np.mean(dists_rand[:, 0] <= epsilon) * 100.0)

        # 2. LOFO Split for this group
        lofo_tr = df[df["Family_Group"] != grp].copy()
        lofo_te_pos = df[df["Family_Group"] == grp].copy()
        n_pos_lofo = len(lofo_te_pos)

        # LOFO 3-dec leakage
        scaler_lofo = MinMaxScaler()
        X_lofo_tr_std = pd.DataFrame(scaler_lofo.fit_transform(lofo_tr[feature_cols]), columns=feature_cols, index=lofo_tr.index)
        X_lofo_te_std = pd.DataFrame(scaler_lofo.transform(lofo_te_pos[feature_cols]), columns=feature_cols, index=lofo_te_pos.index)

        tr_lofo_3dec = set(X_lofo_tr_std.round(3).itertuples(index=False, name=None))
        te_lofo_3dec = list(X_lofo_te_std.round(3).itertuples(index=False, name=None))
        lofo_near_cnt = sum(1 for t in te_lofo_3dec if t in tr_lofo_3dec)
        lofo_near_pct = (lofo_near_cnt / n_pos_lofo) * 100.0

        # LOFO log1p 3-dec leakage
        scaler_lofo_log = MinMaxScaler()
        X_lofo_tr_log = pd.DataFrame(scaler_lofo_log.fit_transform(np.log1p(np.maximum(0, lofo_tr[feature_cols]))), columns=feature_cols, index=lofo_tr.index)
        X_lofo_te_log = pd.DataFrame(scaler_lofo_log.transform(np.log1p(np.maximum(0, lofo_te_pos[feature_cols]))), columns=feature_cols, index=lofo_te_pos.index)

        tr_lofo_log_3dec = set(X_lofo_tr_log.round(3).itertuples(index=False, name=None))
        te_lofo_log_3dec = list(X_lofo_te_log.round(3).itertuples(index=False, name=None))
        lofo_log_cnt = sum(1 for t in te_lofo_log_3dec if t in tr_lofo_log_3dec)
        lofo_log_pct = (lofo_log_cnt / n_pos_lofo) * 100.0

        # LOFO NN distance
        scaler_lofo_knn = StandardScaler()
        X_lofo_tr_knn = scaler_lofo_knn.fit_transform(np.log1p(np.maximum(0, lofo_tr[feature_cols])))
        X_lofo_te_knn = scaler_lofo_knn.transform(np.log1p(np.maximum(0, lofo_te_pos[feature_cols])))

        nn_lofo_train = NearestNeighbors(n_neighbors=1, metric="euclidean", n_jobs=1).fit(X_lofo_tr_knn)
        dists_lofo, _ = nn_lofo_train.kneighbors(X_lofo_te_knn)
        lofo_med_nn = float(np.median(dists_lofo[:, 0]))
        lofo_pct_eps = float(np.mean(dists_lofo[:, 0] <= epsilon) * 100.0)

        audit_records.append({
            "Family_Group": grp,
            "Rand_Test_Pos": n_pos_rand,
            "Rand_Near_Matches_3dec": rand_near_cnt,
            "Rand_Near_Leakage_3dec_Pct": round(rand_near_pct, 2),
            "Rand_Log1p_Leakage_3dec_Pct": round(rand_log_pct, 2),
            "Rand_Median_NN_Dist": round(rand_med_nn, 4),
            "Rand_Pct_Within_Eps": round(rand_pct_eps, 2),
            "LOFO_Test_Pos": n_pos_lofo,
            "LOFO_Near_Matches_3dec": lofo_near_cnt,
            "LOFO_Near_Leakage_3dec_Pct": round(lofo_near_pct, 2),
            "LOFO_Log1p_Leakage_3dec_Pct": round(lofo_log_pct, 2),
            "LOFO_Median_NN_Dist": round(lofo_med_nn, 4),
            "LOFO_Pct_Within_Eps": round(lofo_pct_eps, 2),
            "Epsilon": round(epsilon, 4),
        })

    audit_df = pd.DataFrame(audit_records)
    audit_csv = results_dir / "leakage_audit.csv"
    audit_df.to_csv(audit_csv, index=False)
    audit_md = results_dir / "leakage_audit.md"
    from src.eval.report_utils import save_report_with_sidecar
    save_report_with_sidecar(audit_md, format_markdown_table(audit_df), df=audit_df)
    logger.info(f"Saved UNSW leakage audit to {audit_csv}")
    return audit_df


def run_unsw_lofo_benchmark(
    max_rows: int = 50_000,
    groups_to_evaluate: Optional[List[str]] = None,
    prevalences: List[float] = [0.01, 0.05],
    seeds: List[int] = [42, 101, 202, 303, 404],
    results_dir: Path = Path("results/unsw_nb15")
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Execute Leave-One-Family-Group-Out benchmark on UNSW-NB15 across 5 seeds."""
    results_dir.mkdir(parents=True, exist_ok=True)
    models_dir = results_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    adapter = UNSWNB15Adapter(max_rows=max_rows)
    if not adapter.is_available():
        raise FileNotFoundError("UNSW-NB15 raw data not found in data/raw/unsw_nb15. Failing as required.")

    features_df, y_binary, family, family_group, data_card = adapter.load()
    df = adapter.build_unified_dataframe(features_df, y_binary, family, family_group)
    feature_cols = [c for c in features_df.columns]

    if groups_to_evaluate is None:
        # All 5 qualified family groups (>= 500 unique flows)
        groups_to_evaluate = ["Recon_Analysis", "Exploit_Payload", "Fuzzers", "DoS", "Generic"]

    logger.info(f"Loaded UNSW-NB15: {len(df):,} flows, {len(feature_cols)} features. Groups: {groups_to_evaluate}")

    # Run leakage audit on UNSW
    run_unsw_leakage_audit(df, groups_to_evaluate, feature_cols, results_dir)

    run_cache = []
    group_inner_detector_scores = {grp: {"Isolation_Forest": [], "Autoencoder": [], "Mean_Anomaly": []} for grp in groups_to_evaluate}
    fusion_stability_records = []

    for seed in seeds:
        logger.info(f"=== UNSW-NB15 SEED {seed} ===")
        # Partition benign flows into 60/20/20
        benign_df = df[df["Label"] == "Benign"].sample(frac=1.0, random_state=seed)
        n_b = len(benign_df)
        n_b_tr = int(round(n_b * 0.60))
        n_b_val = int(round(n_b * 0.20))

        b_train = benign_df.iloc[:n_b_tr]
        b_val = benign_df.iloc[n_b_tr:n_b_tr + n_b_val]
        b_test = benign_df.iloc[n_b_tr + n_b_val:]

        for grp in groups_to_evaluate:
            logger.info(f"--- [Seed {seed}] Training UNSW LOFGO for Group: {grp} ---")
            grp_flows = df[df["Family_Group"] == grp]
            other_attacks = df[(df["Family_Group"] != grp) & (df["Label"] != "Benign")]

            # Split other attacks between train (75%) and val (25%)
            shuffled_other = other_attacks.sample(frac=1.0, random_state=seed)
            n_other_tr = int(round(len(shuffled_other) * 0.75))
            att_train = shuffled_other.iloc[:n_other_tr]
            att_val = shuffled_other.iloc[n_other_tr:]

            train_df = pd.concat([b_train, att_train], ignore_index=True)
            val_df = pd.concat([b_val, att_val], ignore_index=True)

            predictor = train_lofo_pipeline(
                train_df=train_df,
                val_df=val_df,
                held_out_family=grp,
                feature_cols=feature_cols,
                random_seed=seed,
                label_col="Family_Group"
            )

            # Record inner LOFO detector means
            for det in ["Isolation_Forest", "Autoencoder", "Mean_Anomaly"]:
                sc = predictor.inner_detector_means.get(det, 0.0)
                group_inner_detector_scores[grp][det].append(sc)

            fusion_stability_records.append({
                "Seed": seed,
                "Family_Group": grp,
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

            # Persist checkpoint for seed 42
            if seed == 42:
                predictor.save(models_dir / f"sentinelx_unsw_{grp}.joblib")

            # Family-Seen Control: train with 70% of held-out group
            grp_shuffled = grp_flows.sample(frac=1.0, random_state=seed)
            n_grp_tr = int(round(len(grp_shuffled) * 0.70))
            grp_tr = grp_shuffled.iloc[:n_grp_tr]
            grp_held_out = grp_shuffled.iloc[n_grp_tr:]

            ctrl_train = pd.concat([train_df, grp_tr], ignore_index=True)
            ctrl_pipe = FeaturePipeline(feature_cols).fit(ctrl_train)
            X_ctrl_tr = ctrl_pipe.transform(ctrl_train)
            X_ctrl_val = ctrl_pipe.transform(val_df)
            y_ctrl_tr = (ctrl_train["Family_Group"] != "Benign").astype(int).to_numpy()
            y_ctrl_val = (val_df["Family_Group"] != "Benign").astype(int).to_numpy()

            ctrl_xgb = XGBoostDetector(random_seed=seed, n_estimators=60, max_depth=4)
            ctrl_xgb.fit(X_ctrl_tr, y_ctrl_tr, X_ctrl_val, y_ctrl_val)

            run_cache.append({
                "seed": seed,
                "grp": grp,
                "predictor": predictor,
                "ctrl_xgb": ctrl_xgb,
                "ctrl_pipe": ctrl_pipe,
                "b_test": b_test,
                "grp_flows": grp_flows,
                "grp_held_out": grp_held_out,
            })

    # ONE FIXED RULE: Highest mean inner-LOFO PR-AUC across all seeds per group fold
    fixed_best_single = {}
    for grp in groups_to_evaluate:
        avg_scores = {det: float(np.mean(group_inner_detector_scores[grp][det])) for det in group_inner_detector_scores[grp]}
        fixed_det = max(avg_scores.keys(), key=lambda k: avg_scores[k])
        fixed_best_single[grp] = fixed_det
        logger.info(f"UNSW Group {grp} Fixed Best Single Detector: '{fixed_det}' (Inner PR-AUCs: {avg_scores})")

    seed_records = []
    unsw_raw_records = []

    # Evaluate test sets with fixed single detector per fold
    for item in run_cache:
        seed = item["seed"]
        grp = item["grp"]
        predictor = item["predictor"]
        ctrl_xgb = item["ctrl_xgb"]
        ctrl_pipe = item["ctrl_pipe"]
        b_test = item["b_test"]
        grp_flows = item["grp_flows"]
        grp_held_out = item["grp_held_out"]
        rule_name = fixed_best_single[grp]

        for p in prevalences:
            resamp = resample_prevalence(
                benign_test=b_test,
                attack_test=grp_flows,
                target_prevalence=p,
                random_seed=seed
            )
            test_df = resamp["test_df"].copy()
            y_test = (test_df["Family_Group"] == grp).astype(int).to_numpy()
            pred_dict = predictor.predict_scores(test_df)

            # Control prediction
            resamp_ctrl = resample_prevalence(
                benign_test=b_test,
                attack_test=grp_held_out,
                target_prevalence=p,
                random_seed=seed
            )
            ctrl_test = resamp_ctrl["test_df"]
            s_ctrl = ctrl_xgb.predict_scores(ctrl_pipe.transform(ctrl_test))
            y_ctrl = (ctrl_test["Family_Group"] == grp).astype(int).to_numpy()

            eval_methods = {
                "Supervised_XGBoost": pred_dict["supervised"],
                "Isolation_Forest": pred_dict["iforest"],
                "Autoencoder": pred_dict["autoencoder"],
                "Mean_Anomaly": pred_dict["mean_anomaly"],
                "Fusion_XGB_Mean_Anomaly": pred_dict["fused_inner_mean"],
                "Fusion_XGB_IForest": pred_dict["fused_inner_iforest"],
                "Fusion_XGB_AE": pred_dict["fused_inner_ae"],
                "Baseline_Rank_Average_0.5_0.5": pred_dict["rank_average"],
                "Ablation_Gated_Boost": pred_dict["gated_boost"],
            }

            p_metrics = {}
            for m_name, s_arr in eval_methods.items():
                roc = float(roc_auc_score(y_test, s_arr)) if len(np.unique(y_test)) > 1 else 0.5
                pr = compute_pr_auc(y_test, s_arr)
                ops = compute_operating_points(y_test, s_arr)
                p_metrics[m_name] = {"roc_auc": roc, "pr_auc": pr, **ops}

            best_single_m = p_metrics[rule_name].copy()
            best_single_m["source_detector"] = rule_name

            # Control metrics
            ctrl_roc = float(roc_auc_score(y_ctrl, s_ctrl)) if len(np.unique(y_ctrl)) > 1 else 0.5
            ctrl_pr = compute_pr_auc(y_ctrl, s_ctrl)
            ctrl_ops = compute_operating_points(y_ctrl, s_ctrl)

            all_eval = {
                **p_metrics,
                f"Selected_Best_Single [*] ({rule_name})": best_single_m,
                "Family_Seen_Control": {"roc_auc": ctrl_roc, "pr_auc": ctrl_pr, **ctrl_ops},
            }

            for m_name, m_data in all_eval.items():
                diff_roc = (m_data["roc_auc"] - best_single_m["roc_auc"]) * 100.0
                diff_pr = (m_data["pr_auc"] - best_single_m["pr_auc"]) * 100.0

                seed_records.append({
                    "Seed": seed,
                    "Family_Group": grp,
                    "Prevalence": f"{p:.1%}",
                    "Method": m_name,
                    "ROC_AUC": m_data["roc_auc"],
                    "PR_AUC": m_data["pr_auc"],
                    "Diff_ROC_pp": diff_roc,
                    "Diff_PR_pp": diff_pr,
                    "FA_per_10k_rec90": m_data["fa_per_10k_recall90"],
                    "FA_per_10k_rec50": m_data["fa_per_10k_recall50"],
                    "P@100": m_data["precision_at_100"],
                    "R_Precision": m_data.get("r_precision", 0.0),
                })

            # Record raw flow predictions for UNSW
            for i in range(len(test_df)):
                unsw_raw_records.append({
                    "dataset": "UNSW-NB15",
                    "fold": grp,
                    "seed": int(seed),
                    "prevalence": float(p),
                    "flow_id": f"{grp}_{int(p*100)}pct_s{seed}_flow_{i}",
                    "label": str(test_df["Label"].iloc[i]),
                    "is_attack": int(y_test[i]),
                    "supervised": np.float32(pred_dict["supervised"][i]),
                    "iforest": np.float32(pred_dict["iforest"][i]),
                    "autoencoder": np.float32(pred_dict["autoencoder"][i]),
                    "mean_anomaly": np.float32(pred_dict["mean_anomaly"][i]),
                    "fused_inner_mean": np.float32(pred_dict["fused_inner_mean"][i]),
                    "fused_inner_iforest": np.float32(pred_dict["fused_inner_iforest"][i]),
                    "fused_inner_ae": np.float32(pred_dict["fused_inner_ae"][i]),
                    "rank_average": np.float32(pred_dict["rank_average"][i]),
                    "gated_boost": np.float32(pred_dict["gated_boost"][i]),
                })

    # Save UNSW raw scores
    from src.eval.report_utils import save_report_with_sidecar
    unsw_raw_df = pd.DataFrame(unsw_raw_records)
    unsw_raw_df.to_parquet(results_dir / "raw_scores.parquet", index=False)
    logger.info(f"Saved UNSW raw scores to {results_dir / 'raw_scores.parquet'} ({len(unsw_raw_df):,} rows).")

    # Save Fusion Weight Stability & Variability Tables for UNSW
    fusion_stab_df = pd.DataFrame(fusion_stability_records)
    fusion_stab_df.to_csv(results_dir / "fusion_weight_stability.csv", index=False)

    variability_records = []
    for grp in groups_to_evaluate:
        grp_df = fusion_stab_df[fusion_stab_df["Family_Group"] == grp]
        for sig_name, col1, col2 in [
            ("XGB + Mean_Anomaly", "w1_mean", "w2_mean"),
            ("XGB + IForest", "w1_iforest", "w2_iforest"),
            ("XGB + Autoencoder", "w1_ae", "w2_ae"),
        ]:
            w1_arr = grp_df[col1].to_numpy()
            w2_arr = grp_df[col2].to_numpy()
            n_extreme = int(np.sum((np.isclose(w1_arr, 1.0)) | (np.isclose(w2_arr, 1.0))))
            status = "Degenerate Tuning" if n_extreme > 2 else "Stable"
            variability_records.append({
                "Family_Group": grp,
                "Fusion_Signal": sig_name,
                "Mean_w1": f"{np.mean(w1_arr):.2f} +/- {np.std(w1_arr):.2f}",
                "Mean_w2": f"{np.mean(w2_arr):.2f} +/- {np.std(w2_arr):.2f}",
                "Extreme_Seeds_Count (w1=1.0 or w2=1.0)": f"{n_extreme}/{len(w1_arr)}",
                "Tuning_Status": status,
            })
    variability_df = pd.DataFrame(variability_records)
    variability_df.to_csv(results_dir / "fusion_weight_variability.csv", index=False)
    save_report_with_sidecar(results_dir / "fusion_weight_variability.md", format_markdown_table(variability_df), df=variability_df)

    # Combined stability MD
    combined_stab_content = (
        "## Per-Seed Inner-LOFO Fusion Weights (UNSW-NB15)\n\n"
        + format_markdown_table(fusion_stab_df)
        + "\n\n## Fusion-Weight Variability & Degenerate Tuning Summary (UNSW-NB15)\n\n"
        + format_markdown_table(variability_df)
    )
    save_report_with_sidecar(results_dir / "fusion_weight_stability.md", combined_stab_content, df=fusion_stab_df)

    # Aggregate Benchmark & Differences
    seed_df = pd.DataFrame(seed_records)
    agg_records = []
    diff_records = []

    for (grp, prev, method), group in seed_df.groupby(["Family_Group", "Prevalence", "Method"], sort=False):
        roc_m = float(group["ROC_AUC"].mean())
        roc_s = float(group["ROC_AUC"].std())
        pr_m = float(group["PR_AUC"].mean())
        pr_s = float(group["PR_AUC"].std())

        agg_records.append({
            "Family_Group": grp,
            "Prevalence": prev,
            "Method": method,
            "ROC_AUC": f"{roc_m:.4f} +/- {roc_s:.4f}",
            "PR_AUC": f"{pr_m:.4f} +/- {pr_s:.4f}",
            "FA@90% Recall": f"{group['FA_per_10k_rec90'].mean():.1f} +/- {group['FA_per_10k_rec90'].std():.1f}",
            "FA@50% Recall": f"{group['FA_per_10k_rec50'].mean():.1f} +/- {group['FA_per_10k_rec50'].std():.1f}",
            "P@100": f"{group['P@100'].mean():.4f} +/- {group['P@100'].std():.4f}",
            "R-Precision": f"{group['R_Precision'].mean():.4f} +/- {group['R_Precision'].std():.4f}",
        })

        if (
            method.startswith("Fusion_")
            or "Selected_Best_Single" in method
            or method.startswith("Baseline_")
            or method.startswith("Ablation_")
            or method == "Supervised_XGBoost"
            or method == "Family_Seen_Control"
        ):
            roc_diff_m = float(group["Diff_ROC_pp"].mean())
            roc_diff_s = float(group["Diff_ROC_pp"].std())
            pr_diff_m = float(group["Diff_PR_pp"].mean())
            pr_diff_s = float(group["Diff_PR_pp"].std())

            ci_roc_l, ci_roc_h = compute_bootstrap_ci(group["Diff_ROC_pp"].tolist())
            ci_pr_l, ci_pr_h = compute_bootstrap_ci(group["Diff_PR_pp"].tolist())
            is_unc = (ci_pr_h - ci_pr_l > 20.0 or ci_roc_h - ci_roc_l > 20.0)

            diff_records.append({
                "Family_Group": grp,
                "Prevalence": prev,
                "Method": method,
                "ROC_AUC": f"{roc_m:.4f} +/- {roc_s:.4f}",
                "Delta_ROC_AUC_pp": f"{roc_diff_m:+.2f} +/- {roc_diff_s:.2f}",
                "95% CI (ROC-AUC pp)": f"[{ci_roc_l:+.2f}, {ci_roc_h:+.2f}]",
                "PR_AUC": f"{pr_m:.4f} +/- {pr_s:.4f}",
                "Delta_PR_AUC_pp": f"{pr_diff_m:+.2f} +/- {pr_diff_s:.2f}",
                "95% CI (PR-AUC pp)": f"[{ci_pr_l:+.2f}, {ci_pr_h:+.2f}]",
                "Reliability": "Uncertain (CI width > 20pp)" if is_unc else "Reliable",
                "P@100": f"{group['P@100'].mean():.4f} +/- {group['P@100'].std():.4f}",
                "R-Precision": f"{group['R_Precision'].mean():.4f} +/- {group['R_Precision'].std():.4f}",
            })

    # Verify every fold has non-zero std across seeds
    std_check_fails = []
    for grp in groups_to_evaluate:
        grp_rows = seed_df[(seed_df["Family_Group"] == grp) & (seed_df["Method"] == "Supervised_XGBoost")]
        if len(grp_rows) > 1 and np.isclose(grp_rows["ROC_AUC"].std(), 0.0):
            std_check_fails.append(grp)
    if std_check_fails:
        raise RuntimeError(f"Validation failed: Groups with zero standard deviation across seeds: {std_check_fails}")

    bench_header = (
        f"# UNSW-NB15 Multi-Seed LOFGO Benchmark\n\n"
        f"- **Dataset Provenance:** UNSW-NB15 (pre-split partition, pooled and deduplicated)\n"
        f"- **Seeds Evaluated:** 5 seeds ({', '.join(str(s) for s in seeds)})\n"
        f"- **Note:** *Computed dynamically across 5 random seeds (mean +/- std)*\n\n"
    )
    agg_df = pd.DataFrame(agg_records)
    agg_df.to_csv(results_dir / "unsw_nb15_benchmark.csv", index=False)
    save_report_with_sidecar(results_dir / "unsw_nb15_benchmark.md", bench_header + format_markdown_table(agg_df), df=agg_df)

    diff_header = (
        f"# UNSW-NB15 Fusion vs Reference Single Detectors Comparison\n\n"
        f"- **Dataset Provenance:** UNSW-NB15 (pre-split partition, pooled and deduplicated)\n"
        f"- **Seeds Evaluated:** 5 seeds ({', '.join(str(s) for s in seeds)})\n"
        f"- **Note:** *Computed dynamically across 5 random seeds (mean +/- std)*\n\n"
    )
    diff_df = pd.DataFrame(diff_records)
    diff_df.to_csv(results_dir / "fusion_vs_single_comparison.csv", index=False)
    save_report_with_sidecar(results_dir / "fusion_vs_single_comparison.md", diff_header + format_markdown_table(diff_df), df=diff_df)

    logger.info("UNSW-NB15 5-seed benchmark completed.")
    return seed_df, agg_df, diff_df, variability_df


def generate_cross_dataset_summary() -> pd.DataFrame:
    """Build summary table comparing datasets strictly by delegating to generate_cross_dataset."""
    from scripts.generate_cross_dataset import build_cross_dataset_comparison
    build_cross_dataset_comparison()
    csv_path = Path("results/cross_dataset_comparison.csv")
    if not csv_path.exists():
        raise FileNotFoundError(f"Generated comparison CSV not found at {csv_path}")
    return pd.read_csv(csv_path)



def main():
    logger.info("Executing Part B Multi-Seed UNSW Benchmark and Cross-Dataset Aggregation...")
    run_unsw_lofo_benchmark(
        max_rows=50_000,
        groups_to_evaluate=["Recon_Analysis", "Exploit_Payload", "Fuzzers", "DoS", "Generic"],
        prevalences=[0.01, 0.05],
        seeds=[42, 101, 202, 303, 404]
    )
    cross_df = generate_cross_dataset_summary()
    print("\n=======================================================")
    print("   PROGRAMMATIC CROSS-DATASET COMPARISON TABLE")
    print("=======================================================\n")
    print(format_markdown_table(cross_df))


if __name__ == "__main__":
    main()
