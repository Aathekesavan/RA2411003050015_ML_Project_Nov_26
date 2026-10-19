"""Empirically evaluate Family_Seen_Control across all 5 seeds, 5 folds, and 2 prevalences.

Calculates genuine ROC-AUC, PR-AUC, Recall@1%FAR, Recall@0.1%FAR, FA@90%, FA@50%, P@100, P@500, R-Precision
with exact tie handling, removing the previous artifact.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score

from src.models.detector import FeaturePipeline, XGBoostDetector
from src.eval.lofo import LOFOSplitEngine, resample_prevalence
from scripts.run_merged_holdout import compute_recall_at_far

def compute_fa_at_recall(y_true, y_score, target_recall=0.90):
    neg_scores = y_score[y_true == 0]
    pos_scores = y_score[y_true == 1]
    if len(pos_scores) == 0 or len(neg_scores) == 0:
        return 0.0
    thresh = float(np.percentile(pos_scores, (1.0 - target_recall) * 100.0))
    fa_rate = float(np.mean(neg_scores >= thresh) * 10000.0)
    return fa_rate

def run_all_controls():
    p = Path("data/processed/cicids2017_sample60k.parquet")
    df = pd.read_parquet(p)
    feature_cols = [c for c in df.columns if c != "Label"]
    families = ["DoS_DDoS", "BruteForce", "PortScan", "Bot", "WebAttack"]
    seeds = [42, 101, 202, 303, 404]
    prevalences = [0.01, 0.05]
    
    records = []
    
    for seed in seeds:
        print(f"\n--- SEED {seed} ---")
        engine = LOFOSplitEngine(random_seed=seed, benign_test_pool_path="data/processed/benign_test_pool_100k.parquet")
        
        for fam in families:
            fold_base = engine.generate_fold(df, held_out_family=fam, prevalence=0.05)
            train_df = fold_base["train"]
            val_df = fold_base["val"]
            b_test = fold_base["test"][fold_base["test"]["Label"] == "Benign"]
            
            fam_flows = df[df["Label"] == fam]
            fam_shuffled = fam_flows.sample(frac=1.0, random_state=seed)
            n_tr = int(np.round(len(fam_shuffled) * 0.70))
            fam_tr = fam_shuffled.iloc[:n_tr].copy()
            fam_held_out = fam_shuffled.iloc[n_tr:].copy()
            
            control_train = pd.concat([train_df, fam_tr], ignore_index=True)
            pipe = FeaturePipeline(feature_cols).fit(control_train)
            X_tr = pipe.transform(control_train)
            X_val = pipe.transform(val_df)
            y_tr = (control_train["Label"] != "Benign").astype(int).to_numpy()
            y_val = (val_df["Label"] != "Benign").astype(int).to_numpy()
            
            xgb = XGBoostDetector(random_seed=seed, n_estimators=80, max_depth=4)
            xgb.fit(X_tr, y_tr, X_val, y_val)
            
            for prev in prevalences:
                resamp = resample_prevalence(benign_test=b_test, attack_test=fam_held_out, target_prevalence=prev, random_seed=seed)
                sub_test = resamp["test_df"]
                s_sub = xgb.predict_scores(pipe.transform(sub_test))
                y_sub = (sub_test["Label"] == fam).astype(int).to_numpy()
                
                roc = float(roc_auc_score(y_sub, s_sub))
                pr = float(average_precision_score(y_sub, s_sub))
                rec1 = compute_recall_at_far(y_sub, s_sub, target_far=0.01)
                rec01 = compute_recall_at_far(y_sub, s_sub, target_far=0.001)
                fa90 = compute_fa_at_recall(y_sub, s_sub, target_recall=0.90)
                fa50 = compute_fa_at_recall(y_sub, s_sub, target_recall=0.50)
                
                sorted_order = np.argsort(-s_sub)
                sorted_labels = y_sub[sorted_order]
                p100 = float(np.mean(sorted_labels[:min(100, len(sorted_labels))]))
                p500 = float(np.mean(sorted_labels[:min(500, len(sorted_labels))]))
                n_pos = int(np.sum(y_sub))
                r_prec = float(np.mean(sorted_labels[:n_pos]))
                
                records.append({
                    "Seed": seed,
                    "Family": fam,
                    "Prevalence": f"{prev*100:.1f}%",
                    "Method": "Family_Seen_Control",
                    "ROC_AUC": roc,
                    "PR_AUC": pr,
                    "Recall@1%FAR": rec1,
                    "Recall@0.1%FAR": rec01,
                    "FA@90% Recall (per 10k)": fa90,
                    "FA@50% Recall (per 10k)": fa50,
                    "P@100": p100,
                    "P@500": p500,
                    "R-Precision": r_prec,
                    "Positives": n_pos,
                    "Test_Samples": len(sub_test),
                })
                print(f"Seed {seed} | Fold {fam:11s} | Prev {prev*100:.1f}% | ROC={roc:.4f}, PR={pr:.4f}, Rec@1%FAR={rec1*100:.2f}%, Rec@0.1%FAR={rec01*100:.2f}%")
                
    df_out = pd.DataFrame(records)
    out_csv = Path("results/family_seen_control_empirical.csv")
    df_out.to_csv(out_csv, index=False)
    print(f"\nSaved empirical family seen control results to {out_csv}")
    
    # Aggregated summary
    agg = df_out.groupby(["Family", "Prevalence"]).agg(
        ROC_mean=("ROC_AUC", "mean"),
        ROC_std=("ROC_AUC", "std"),
        PR_mean=("PR_AUC", "mean"),
        PR_std=("PR_AUC", "std"),
        Rec1_mean=("Recall@1%FAR", "mean"),
        Rec1_std=("Recall@1%FAR", "std"),
        Rec01_mean=("Recall@0.1%FAR", "mean"),
        Rec01_std=("Recall@0.1%FAR", "std"),
        FA90_mean=("FA@90% Recall (per 10k)", "mean"),
        FA90_std=("FA@90% Recall (per 10k)", "std"),
        FA50_mean=("FA@50% Recall (per 10k)", "mean"),
        FA50_std=("FA@50% Recall (per 10k)", "std"),
        P100_mean=("P@100", "mean"),
        P100_std=("P@100", "std"),
        P500_mean=("P@500", "mean"),
        P500_std=("P@500", "std"),
        RPrec_mean=("R-Precision", "mean"),
        RPrec_std=("R-Precision", "std"),
        Positives_mean=("Positives", "mean"),
        Samples_mean=("Test_Samples", "mean"),
    ).reset_index()
    
    summary_rows = []
    for _, r in agg.iterrows():
        p500_str = f"{r['P500_mean']:.4f} +/- {r['P500_std']:.4f}" if r["Positives_mean"] >= 500 else "n/a"
        summary_rows.append({
            "Family": r["Family"],
            "Prevalence": r["Prevalence"],
            "Method": "Family_Seen_Control",
            "ROC_AUC": f"{r['ROC_mean']:.4f} +/- {r['ROC_std']:.4f}",
            "PR_AUC": f"{r['PR_mean']:.4f} +/- {r['PR_std']:.4f}",
            "Recall@1%FAR": f"{r['Rec1_mean']*100:.2f}% +/- {r['Rec1_std']*100:.2f}%",
            "Recall@0.1%FAR": f"{r['Rec01_mean']*100:.2f}% +/- {r['Rec01_std']*100:.2f}%",
            "FA@90% Recall (per 10k)": f"{r['FA90_mean']:.1f} +/- {r['FA90_std']:.1f}",
            "FA@50% Recall (per 10k)": f"{r['FA50_mean']:.1f} +/- {r['FA50_std']:.1f}",
            "P@100": f"{r['P100_mean']:.4f} +/- {r['P100_std']:.4f}",
            "P@500": p500_str,
            "R-Precision": f"{r['RPrec_mean']:.4f} +/- {r['RPrec_std']:.4f}",
            "Test_Samples": int(r["Samples_mean"]),
            "Positives": int(r["Positives_mean"]),
        })
    df_summary = pd.DataFrame(summary_rows)
    df_summary.to_csv("results/family_seen_control_summary.csv", index=False)
    print("\n--- EMPIRICAL FAMILY SEEN CONTROL SUMMARY ---")
    print(df_summary.to_string(index=False))
    return df_summary

if __name__ == "__main__":
    run_all_controls()
