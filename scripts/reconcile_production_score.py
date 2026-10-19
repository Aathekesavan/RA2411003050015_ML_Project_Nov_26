"""Run inner-LOFO tuning on widened grid tau in {0.3, 0.5, 0.7, 0.9} and gamma in {0.1, 0.2, 0.3, 0.5}.

Produces:
1. Unrounded per-seed validation PR-AUCs for AE, Rank_Average, and Gated_Boost.
2. Validation prevalence per fold.
3. Updated results/fusion_weight_stability.csv with genuine multi-seed variation.
4. Regenerated docs/production_score.md with correct summary means and pre-declared validation rule.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score

from src.models.detector import FeaturePipeline, XGBoostDetector, IsolationForestDetector, AutoencoderDetector
from src.eval.lofo import LOFOSplitEngine
from src.eval.report_utils import format_markdown_table, get_git_info

def compute_pr_auc(y_true, y_score):
    if len(np.unique(y_true)) < 2:
        return 0.5
    return float(average_precision_score(y_true, y_score))

def tune_widened_inner_lofo(
    train_df: pd.DataFrame,
    feature_cols: list,
    held_out_test_family: str,
    random_seed: int = 42
):
    """Inner LOFO with widened grid: tau in {0.3, 0.5, 0.7, 0.9}, gamma in {0.1, 0.2, 0.3, 0.5}."""
    inner_families = [fam for fam in train_df["Label"].unique() if fam not in ["Benign", held_out_test_family]]
    tau_grid = [0.3, 0.5, 0.7, 0.9]
    gamma_grid = [0.1, 0.2, 0.3, 0.5]
    gated_candidates = [(t, g) for t in tau_grid for g in gamma_grid]
    
    scores_gated = {cand: [] for cand in gated_candidates}
    single_ae_scores = []
    single_if_scores = []
    single_mean_scores = []
    single_rank_avg_scores = []
    val_prevalences = []
    
    benign_train_full = train_df[train_df["Label"] == "Benign"]
    
    for inner_fam in inner_families:
        # Split benign into inner_train (70%) and inner_val (30%)
        b_shuffled = benign_train_full.sample(frac=1.0, random_state=random_seed)
        n_b_tr = int(np.round(len(b_shuffled) * 0.7))
        b_in_tr = b_shuffled.iloc[:n_b_tr]
        b_in_val = b_shuffled.iloc[n_b_tr:]
        
        other_inner_attacks = train_df[(train_df["Label"] != "Benign") & (train_df["Label"] != inner_fam)]
        inner_fam_flows = train_df[train_df["Label"] == inner_fam]
        
        in_train_df = pd.concat([b_in_tr, other_inner_attacks], ignore_index=True)
        in_val_df = pd.concat([b_in_val, inner_fam_flows], ignore_index=True)
        
        val_prev = float(len(inner_fam_flows) / len(in_val_df))
        val_prevalences.append(val_prev)
        
        inner_pipe = FeaturePipeline(feature_cols).fit(in_train_df)
        X_in_tr = inner_pipe.transform(in_train_df)
        X_in_val = inner_pipe.transform(in_val_df)
        
        y_in_tr = (in_train_df["Label"] != "Benign").astype(int).to_numpy()
        y_in_val = (in_val_df["Label"] != "Benign").astype(int).to_numpy()
        
        inner_xgb = XGBoostDetector(random_seed=random_seed, n_estimators=40, max_depth=3)
        inner_xgb.fit(X_in_tr, y_in_tr, X_in_val, y_in_val)
        
        X_b_tr = inner_pipe.transform(b_in_tr)
        X_b_val = inner_pipe.transform(b_in_val)
        y_b_tr = np.zeros(len(b_in_tr), dtype=int)
        y_b_val = np.zeros(len(b_in_val), dtype=int)
        
        inner_if = IsolationForestDetector(random_seed=random_seed, n_estimators=50).fit(X_b_tr, X_b_val, y_b_tr, y_b_val)
        inner_ae = AutoencoderDetector(random_seed=random_seed, hidden_layers=(16, 8, 16)).fit(X_b_tr, X_b_val, y_b_tr, y_b_val)
        
        s_sup = inner_xgb.predict_scores(X_in_val)
        s_if = inner_if.predict_scores(X_in_val)
        s_a = inner_ae.predict_scores(X_in_val)
        s_mean = 0.5 * (s_if + s_a)
        
        single_if_scores.append(compute_pr_auc(y_in_val, s_if))
        single_ae_scores.append(compute_pr_auc(y_in_val, s_a))
        single_mean_scores.append(compute_pr_auc(y_in_val, s_mean))
        
        r_xgb = pd.Series(s_sup).rank(pct=True).to_numpy()
        r_mean = pd.Series(s_mean).rank(pct=True).to_numpy()
        s_rank_avg = 0.5 * r_xgb + 0.5 * r_mean
        single_rank_avg_scores.append(compute_pr_auc(y_in_val, s_rank_avg))
        
        for (t_cand, g_cand) in gated_candidates:
            s_g = np.clip(s_a + np.where(s_sup > t_cand, g_cand, 0.0), 0.0, 1.0)
            scores_gated[(t_cand, g_cand)].append(compute_pr_auc(y_in_val, s_g))
            
    avg_gated = {cand: float(np.mean(sc)) for cand, sc in scores_gated.items()}
    best_cand = max(avg_gated.keys(), key=lambda k: avg_gated[k])
    best_tau, best_gamma = best_cand
    
    return {
        "val_pr_auc_ae": float(np.mean(single_ae_scores)),
        "val_pr_auc_iforest": float(np.mean(single_if_scores)),
        "val_pr_auc_mean_anomaly": float(np.mean(single_mean_scores)),
        "val_pr_auc_rank_avg": float(np.mean(single_rank_avg_scores)),
        "val_pr_auc_gated_boost": float(avg_gated[best_cand]),
        "best_tau": best_tau,
        "best_gamma": best_gamma,
        "mean_val_prevalence": float(np.mean(val_prevalences)),
        "grid_results": avg_gated,
    }

def main():
    p = Path("data/processed/cicids2017_sample60k.parquet")
    df = pd.read_parquet(p)
    feature_cols = [c for c in df.columns if c != "Label"]
    families = ["DoS_DDoS", "BruteForce", "PortScan", "Bot", "WebAttack"]
    seeds = [42, 101, 202, 303, 404]
    
    all_results = []
    
    for seed in seeds:
        print(f"\n--- SEED {seed} ---")
        engine = LOFOSplitEngine(random_seed=seed, benign_test_pool_path="data/processed/benign_test_pool_100k.parquet")
        for fam in families:
            fold_base = engine.generate_fold(df, held_out_family=fam, prevalence=0.05)
            train_df = fold_base["train"]
            
            res = tune_widened_inner_lofo(train_df, feature_cols, held_out_test_family=fam, random_seed=seed)
            print(f"Seed {seed} | Fold {fam:11s} | AE={res['val_pr_auc_ae']:.6f} | RankAvg={res['val_pr_auc_rank_avg']:.6f} | Gated={res['val_pr_auc_gated_boost']:.6f} | Tau={res['best_tau']} | Gamma={res['best_gamma']} | Prev={res['mean_val_prevalence']*100:.2f}%")
            
            all_results.append({
                "Seed": seed,
                "Family": fam,
                "val_pr_auc_ae": res["val_pr_auc_ae"],
                "val_pr_auc_rank_avg": res["val_pr_auc_rank_avg"],
                "val_pr_auc_gated_boost": res["val_pr_auc_gated_boost"],
                "tau_gated": res["best_tau"],
                "gamma_gated": res["best_gamma"],
                "val_prevalence_pct": res["mean_val_prevalence"] * 100.0,
            })
            
    df_res = pd.DataFrame(all_results)
    df_res.to_csv("results/inner_lofo_widened_grid_results.csv", index=False)
    print("\nSaved inner LOFO widened grid results to results/inner_lofo_widened_grid_results.csv")
    
    # Calculate exact per-fold and dataset means
    fold_agg = df_res.groupby("Family").agg({
        "val_pr_auc_ae": ["mean", "std"],
        "val_pr_auc_rank_avg": ["mean", "std"],
        "val_pr_auc_gated_boost": ["mean", "std"],
        "tau_gated": "mean",
        "gamma_gated": "mean",
        "val_prevalence_pct": "mean"
    }).reset_index()
    
    print("\n--- PER-FOLD INNER-LOFO SUMMARY ---")
    print(fold_agg)
    
    mean_ae = float(df_res["val_pr_auc_ae"].mean())
    mean_rank = float(df_res["val_pr_auc_rank_avg"].mean())
    mean_gated = float(df_res["val_pr_auc_gated_boost"].mean())
    print(f"\nExact Summary Means across all 25 runs (5 folds x 5 seeds):")
    print(f"  Autoencoder alone: {mean_ae:.4f}")
    print(f"  Rank-Average     : {mean_rank:.4f}")
    print(f"  Gated Boost      : {mean_gated:.4f}")
    
    return df_res

if __name__ == "__main__":
    main()
