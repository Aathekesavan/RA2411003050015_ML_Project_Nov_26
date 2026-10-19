"""Execute authorized additional LOFO evaluation: holding out {BruteForce, WebAttack} together.

Evaluates XGBoost, Autoencoder, and Gated Boost across 5 random seeds (42, 101, 202, 303, 404)
at 1% and 5% test prevalence, reporting ROC-AUC, PR-AUC, and Recall@1%FAR with exact tie-breaking.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score

from src.models.detector import FeaturePipeline, XGBoostDetector, AutoencoderDetector, IsolationForestDetector
from src.eval.lofo import split_benign_flows, resample_prevalence
from src.models.pipeline import tune_nested_inner_lofo

def compute_recall_at_far(y_true: np.ndarray, y_score: np.ndarray, target_far: float = 0.01) -> float:
    """Calculate recall at fixed false alarm rate with exact tie handling."""
    y_true = np.asarray(y_true, dtype=int)
    y_score = np.asarray(y_score, dtype=float)
    neg_scores = y_score[y_true == 0]
    pos_scores = y_score[y_true == 1]
    if len(pos_scores) == 0 or len(neg_scores) == 0:
        return 0.0
    
    # Threshold at (1 - target_far) percentile of benign
    thresh = float(np.percentile(neg_scores, (1.0 - target_far) * 100.0))
    n_neg = len(neg_scores)
    k_allowed = int(np.floor(target_far * n_neg))
    
    n_gt = int(np.sum(neg_scores > thresh))
    n_eq = int(np.sum(neg_scores == thresh))
    
    if n_eq > 0:
        p_tie = max(0.0, min(1.0, float(k_allowed - n_gt) / float(n_eq)))
    else:
        p_tie = 0.0
        
    pos_gt = np.sum(pos_scores > thresh)
    pos_eq = np.sum(pos_scores == thresh)
    rec = float(pos_gt + p_tie * pos_eq) / float(len(pos_scores))
    return rec

def run_merged_holdout(
    parquet_path: Path = Path("data/processed/cicids2017_sample60k.parquet"),
    benign_pool_path: Path = Path("data/processed/benign_test_pool_100k.parquet"),
    seeds: list = [42, 101, 202, 303, 404],
    prevalences: list = [0.01, 0.05]
):
    print("Loading processed dataset...")
    df = pd.read_parquet(parquet_path)
    feature_cols = [c for c in df.columns if c != "Label"]
    
    merged_families = ["BruteForce", "WebAttack"]
    remaining_families = [fam for fam in df["Label"].unique() if fam != "Benign" and fam not in merged_families]
    print(f"Holding out merged families: {merged_families}")
    print(f"Remaining training attack families: {remaining_families}")
    
    benign_all = df[df["Label"] == "Benign"]
    merged_attacks = df[df["Label"].isin(merged_families)]
    
    # Load 100k benign test pool if available
    pool_100k = pd.read_parquet(benign_pool_path) if benign_pool_path.exists() else None
    
    results = []
    
    for seed in seeds:
        print(f"\n--- Running Seed {seed} ---")
        b_train, b_val, b_test_fallback = split_benign_flows(
            benign_all, train_ratio=0.6, val_ratio=0.2, test_ratio=0.2, random_seed=seed
        )
        
        if pool_100k is not None:
            train_val_tuples = set(b_train[feature_cols].itertuples(index=False, name=None)) | set(b_val[feature_cols].itertuples(index=False, name=None))
            pool_tuples = list(pool_100k[feature_cols].itertuples(index=False, name=None))
            valid_mask = [t not in train_val_tuples for t in pool_tuples]
            b_test = pool_100k[valid_mask].copy()
        else:
            b_test = b_test_fallback.copy()
            
        # Partition remaining attacks between train (75%) and val (25%)
        train_other_list, val_other_list = [], []
        for fam in remaining_families:
            g = df[df["Label"] == fam]
            shuffled = g.sample(frac=1.0, random_state=seed)
            n_tr = int(np.round(len(shuffled) * 0.75))
            train_other_list.append(shuffled.iloc[:n_tr])
            val_other_list.append(shuffled.iloc[n_tr:])
            
        train_other = pd.concat(train_other_list, ignore_index=True)
        val_other = pd.concat(val_other_list, ignore_index=True)
        
        train_df = pd.concat([b_train, train_other], ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)
        val_df = pd.concat([b_val, val_other], ignore_index=True).sample(frac=1.0, random_state=seed).reset_index(drop=True)
        
        # Verify strictly zero presence of merged families in train or val
        assert not any(train_df["Label"].isin(merged_families)), "Leakage in train_df!"
        assert not any(val_df["Label"].isin(merged_families)), "Leakage in val_df!"
        
        # Pipelines & Models
        pipe = FeaturePipeline(feature_cols).fit(train_df)
        X_tr = pipe.transform(train_df)
        X_val = pipe.transform(val_df)
        y_tr = (train_df["Label"] != "Benign").astype(int).to_numpy()
        y_val = (val_df["Label"] != "Benign").astype(int).to_numpy()
        
        xgb = XGBoostDetector(random_seed=seed, n_estimators=80, max_depth=4)
        xgb.fit(X_tr, y_tr, X_val, y_val)
        
        b_tr_feats = pipe.transform(b_train)
        b_val_feats = pipe.transform(b_val)
        y_b_tr = np.zeros(len(b_train), dtype=int)
        y_b_val = np.zeros(len(b_val), dtype=int)
        
        ae = AutoencoderDetector(random_seed=seed, hidden_layers=(32, 16, 32))
        ae.fit(b_tr_feats, b_val_feats, y_train_benign=y_b_tr, y_val_benign=y_b_val)
        
        # Inner LOFO tuning for gated boost
        inner_res = tune_nested_inner_lofo(
            train_df=train_df,
            feature_cols=feature_cols,
            held_out_test_family="BruteForce", # placeholder, both already excluded
            random_seed=seed
        )
        tau_val, gamma_val = inner_res.gated
        
        for p in prevalences:
            resamp = resample_prevalence(
                benign_test=b_test,
                attack_test=merged_attacks,
                target_prevalence=p,
                random_seed=seed
            )
            sub_test = resamp["test_df"]
            X_te = pipe.transform(sub_test)
            y_te = sub_test["Label"].isin(merged_families).astype(int).to_numpy()
            
            s_xgb = xgb.predict_scores(X_te)
            s_ae = ae.predict_scores(X_te)
            s_gated = np.clip(s_ae + np.where(s_xgb > tau_val, gamma_val, 0.0), 0.0, 1.0)
            
            for m_name, s_arr in [
                ("Supervised_XGBoost", s_xgb),
                ("Autoencoder", s_ae),
                ("Ablation_Gated_Boost", s_gated),
            ]:
                roc = float(roc_auc_score(y_te, s_arr))
                pr = float(average_precision_score(y_te, s_arr))
                rec1 = compute_recall_at_far(y_te, s_arr, target_far=0.01)
                
                results.append({
                    "Seed": seed,
                    "Fold": "BruteForce_WebAttack_Merged",
                    "Prevalence": f"{p*100:.1f}%",
                    "Method": m_name,
                    "ROC_AUC": roc,
                    "PR_AUC": pr,
                    "Recall@1%FAR": rec1,
                    "Tau": tau_val,
                    "Gamma": gamma_val,
                    "Positives": int(np.sum(y_te)),
                    "Total_Samples": len(y_te),
                })
                
    df_res = pd.DataFrame(results)
    out_csv = Path("results/merged_holdout_results.csv")
    df_res.to_csv(out_csv, index=False)
    print(f"\nSaved raw merged holdout results to {out_csv}")
    
    # Aggregated summary
    agg = df_res.groupby(["Fold", "Prevalence", "Method"]).agg(
        ROC_mean=("ROC_AUC", "mean"),
        ROC_std=("ROC_AUC", "std"),
        PR_mean=("PR_AUC", "mean"),
        PR_std=("PR_AUC", "std"),
        Rec1_mean=("Recall@1%FAR", "mean"),
        Rec1_std=("Recall@1%FAR", "std")
    ).reset_index()
    
    agg_table = []
    for _, row in agg.iterrows():
        agg_table.append({
            "Fold": row["Fold"],
            "Prevalence": row["Prevalence"],
            "Method": row["Method"],
            "ROC_AUC": f"{row['ROC_mean']:.4f} +/- {row['ROC_std']:.4f}",
            "PR_AUC": f"{row['PR_mean']:.4f} +/- {row['PR_std']:.4f}",
            "Recall@1%FAR": f"{row['Rec1_mean']*100:.2f}% +/- {row['Rec1_std']*100:.2f}%"
        })
    df_agg = pd.DataFrame(agg_table)
    agg_csv = Path("results/merged_holdout_summary.csv")
    df_agg.to_csv(agg_csv, index=False)
    print("\n--- MERGED HOLDOUT SUMMARY ---")
    print(df_agg.to_markdown(index=False))
    return df_agg

if __name__ == "__main__":
    run_merged_holdout()
