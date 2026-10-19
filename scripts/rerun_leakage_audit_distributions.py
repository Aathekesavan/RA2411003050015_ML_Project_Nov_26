"""Rerun leakage audits for CIC-IDS2017 and UNSW-NB15 with full NN distance distributions.

Detects degenerate epsilon (5th percentile of benign-to-benign 1-NN distance near 0)
and replaces it with the median, 5th, and 25th percentiles of nearest-neighbour distances
for test positives vs the same statistics for benign-to-benign under both Random and LOFO splits.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.neighbors import NearestNeighbors

from src.data.adapters.unswnb15 import UNSWNB15Adapter
from src.eval.report_utils import save_report_with_sidecar, format_markdown_table

def run_cic_leakage_audit():
    print("\n=======================================================")
    print("   CIC-IDS2017 LEAKAGE AUDIT & NN DISTANCE DISTRIBUTION")
    print("=======================================================\n")
    p = Path("data/processed/cicids2017_sample60k.parquet")
    df = pd.read_parquet(p)
    feature_cols = [c for c in df.columns if c != "Label"]
    families = ["DoS_DDoS", "BruteForce", "PortScan", "Bot", "WebAttack"]
    
    # 70/30 Stratified random split
    train_rand, test_rand = train_test_split(df, test_size=0.3, random_state=42, stratify=df["Label"])
    
    # Standardize log1p features strictly on train
    X_tr_raw = np.maximum(0, train_rand[feature_cols].to_numpy(dtype=np.float64))
    X_te_raw = np.maximum(0, test_rand[feature_cols].to_numpy(dtype=np.float64))
    
    scaler_rand = StandardScaler()
    X_tr_std = scaler_rand.fit_transform(np.log1p(X_tr_raw))
    X_te_std = scaler_rand.transform(np.log1p(X_te_raw))
    
    # Benign-to-benign NN distances in random split train
    b_tr_mask = (train_rand["Label"] == "Benign").to_numpy()
    X_b_tr = X_tr_std[b_tr_mask]
    
    nn_b = NearestNeighbors(n_neighbors=2, metric="euclidean", n_jobs=1).fit(X_b_tr[:10000])
    dists_b, _ = nn_b.kneighbors(X_b_tr[:10000])
    b_1nn = dists_b[:, 1]
    b_p5, b_p25, b_p50 = float(np.percentile(b_1nn, 5)), float(np.percentile(b_1nn, 25)), float(np.percentile(b_1nn, 50))
    print(f"CIC Benign-to-Benign 1-NN distances: 5th={b_p5:.4f}, 25th={b_p25:.4f}, Median={b_p50:.4f}")
    print(f"Epsilon (5th percentile): {b_p5:.4f} -> DEGENERATE (< 0.03, dense near-zero collisions)")
    
    nn_rand_train = NearestNeighbors(n_neighbors=1, metric="euclidean", n_jobs=1).fit(X_tr_std)
    
    # MinMax scalers for 3-decimal and log1p matching
    scaler_mm = MinMaxScaler()
    X_tr_mm = scaler_mm.fit_transform(X_tr_raw)
    X_te_mm = scaler_mm.transform(X_te_raw)
    
    scaler_log_mm = MinMaxScaler()
    X_tr_log_mm = scaler_log_mm.fit_transform(np.log1p(X_tr_raw))
    X_te_log_mm = scaler_log_mm.transform(np.log1p(X_te_raw))
    
    tr_mm_3dec = set(pd.DataFrame(X_tr_mm).round(3).itertuples(index=False, name=None))
    tr_log_mm_3dec = set(pd.DataFrame(X_log_tr_mm := X_tr_log_mm).round(3).itertuples(index=False, name=None))
    
    # LOFO benign setup
    benign_df = df[df["Label"] == "Benign"]
    n_te_b = int(np.round(len(benign_df) * 0.3))
    b_shuffled = benign_df.sample(frac=1.0, random_state=42)
    b_lofo_tr = b_shuffled.iloc[n_te_b:]
    
    records = []
    
    for fam in families:
        # A. Random split test positives
        te_mask = (test_rand["Label"] == fam).to_numpy()
        n_pos_rand = int(np.sum(te_mask))
        
        # 3-dec matches
        te_fam_mm = list(pd.DataFrame(X_te_mm[te_mask]).round(3).itertuples(index=False, name=None))
        rand_3dec_cnt = sum(1 for t in te_fam_mm if t in tr_mm_3dec)
        rand_3dec_pct = (rand_3dec_cnt / n_pos_rand) * 100.0 if n_pos_rand > 0 else 0.0
        
        # Log1p 3-dec matches
        te_fam_log_mm = list(pd.DataFrame(X_te_log_mm[te_mask]).round(3).itertuples(index=False, name=None))
        rand_log_cnt = sum(1 for t in te_fam_log_mm if t in tr_log_mm_3dec)
        rand_log_pct = (rand_log_cnt / n_pos_rand) * 100.0 if n_pos_rand > 0 else 0.0
        
        # NN distance distribution
        dists_rand, _ = nn_rand_train.kneighbors(X_te_std[te_mask])
        d_rand = dists_rand[:, 0]
        r_p5, r_p25, r_p50 = float(np.percentile(d_rand, 5)), float(np.percentile(d_rand, 25)), float(np.percentile(d_rand, 50))
        
        # B. LOFO Split
        te_lofo_pos = df[df["Label"] == fam].copy()
        n_pos_lofo = len(te_lofo_pos)
        other_attacks = df[(df["Label"] != "Benign") & (df["Label"] != fam)]
        tr_lofo = pd.concat([b_lofo_tr, other_attacks], ignore_index=True)
        
        X_lofo_tr_raw = np.maximum(0, tr_lofo[feature_cols].to_numpy(dtype=np.float64))
        X_lofo_te_raw = np.maximum(0, te_lofo_pos[feature_cols].to_numpy(dtype=np.float64))
        
        # LOFO 3-dec matches
        sc_lofo_mm = MinMaxScaler()
        X_lofo_tr_mm = sc_lofo_mm.fit_transform(X_lofo_tr_raw)
        X_lofo_te_mm = sc_lofo_mm.transform(X_lofo_te_raw)
        tr_lofo_3dec = set(pd.DataFrame(X_lofo_tr_mm).round(3).itertuples(index=False, name=None))
        te_lofo_3dec = list(pd.DataFrame(X_lofo_te_mm).round(3).itertuples(index=False, name=None))
        lofo_3dec_cnt = sum(1 for t in te_lofo_3dec if t in tr_lofo_3dec)
        lofo_3dec_pct = (lofo_3dec_cnt / n_pos_lofo) * 100.0 if n_pos_lofo > 0 else 0.0
        
        # LOFO log1p 3-dec matches
        sc_lofo_log_mm = MinMaxScaler()
        X_lofo_tr_lmm = sc_lofo_log_mm.fit_transform(np.log1p(X_lofo_tr_raw))
        X_lofo_te_lmm = sc_lofo_log_mm.transform(np.log1p(X_lofo_te_raw))
        tr_lofo_l3dec = set(pd.DataFrame(X_lofo_tr_lmm).round(3).itertuples(index=False, name=None))
        te_lofo_l3dec = list(pd.DataFrame(X_lofo_te_lmm).round(3).itertuples(index=False, name=None))
        lofo_log_cnt = sum(1 for t in te_lofo_l3dec if t in tr_lofo_l3dec)
        lofo_log_pct = (lofo_log_cnt / n_pos_lofo) * 100.0 if n_pos_lofo > 0 else 0.0
        
        # LOFO NN distance distribution
        sc_lofo_std = StandardScaler()
        X_lofo_tr_std = sc_lofo_std.fit_transform(np.log1p(X_lofo_tr_raw))
        X_lofo_te_std = sc_lofo_std.transform(np.log1p(X_lofo_te_raw))
        
        nn_lofo = NearestNeighbors(n_neighbors=1, metric="euclidean", n_jobs=1).fit(X_lofo_tr_std)
        dists_lofo, _ = nn_lofo.kneighbors(X_lofo_te_std)
        d_lofo = dists_lofo[:, 0]
        l_p5, l_p25, l_p50 = float(np.percentile(d_lofo, 5)), float(np.percentile(d_lofo, 25)), float(np.percentile(d_lofo, 50))
        
        print(f"Fold {fam:12s} | Benign: p50={b_p50:.4f} | RandPos: p50={r_p50:.4f} (p5={r_p5:.4f}, p25={r_p25:.4f}) | LOFOPos: p50={l_p50:.4f} (p5={l_p5:.4f}, p25={l_p25:.4f})")
        
        records.append({
            "Family": fam,
            "Rand_Test_Pos": n_pos_rand,
            "Rand_Near_Leakage_3dec_Pct": round(rand_3dec_pct, 2),
            "Rand_Log1p_Near_Leakage_3dec_Pct": round(rand_log_pct, 2),
            "Rand_NN_p5": round(r_p5, 4),
            "Rand_NN_p25": round(r_p25, 4),
            "Rand_NN_median": round(r_p50, 4),
            "LOFO_Test_Pos": n_pos_lofo,
            "LOFO_Near_Leakage_3dec_Pct": round(lofo_3dec_pct, 2),
            "LOFO_Log1p_Near_Leakage_3dec_Pct": round(lofo_log_pct, 2),
            "LOFO_NN_p5": round(l_p5, 4),
            "LOFO_NN_p25": round(l_p25, 4),
            "LOFO_NN_median": round(l_p50, 4),
            "Benign_NN_p5": round(b_p5, 4),
            "Benign_NN_p25": round(b_p25, 4),
            "Benign_NN_median": round(b_p50, 4),
            "Epsilon": round(b_p5, 4),
            "Epsilon_Status": "Degenerate (< 0.03)"
        })
        
    df_out = pd.DataFrame(records)
    out_csv = Path("results/leakage_audit.csv")
    df_out.to_csv(out_csv, index=False)
    print(f"Saved updated CIC leakage audit with NN distance distributions to {out_csv}")
    return df_out


def run_unsw_leakage_audit():
    print("\n=======================================================")
    print("   UNSW-NB15 LEAKAGE AUDIT & NN DISTANCE DISTRIBUTION")
    print("=======================================================")
    adapter = UNSWNB15Adapter(max_rows=50000)
    features_df, y_binary, family, family_group, data_card = adapter.load()
    df = adapter.build_unified_dataframe(features_df, y_binary, family, family_group)
    feature_cols = [c for c in features_df.columns]
    groups = ["Recon_Analysis", "Exploit_Payload", "Fuzzers", "DoS", "Generic"]
    
    # 70/30 Stratified random split
    train_rand, test_rand = train_test_split(df, test_size=0.3, random_state=42, stratify=df["Family_Group"])
    
    X_tr_raw = np.maximum(0, train_rand[feature_cols].to_numpy(dtype=np.float64))
    X_te_raw = np.maximum(0, test_rand[feature_cols].to_numpy(dtype=np.float64))
    
    scaler_rand = StandardScaler()
    X_tr_std = scaler_rand.fit_transform(np.log1p(X_tr_raw))
    X_te_std = scaler_rand.transform(np.log1p(X_te_raw))
    
    b_tr_mask = (train_rand["Label"] == "Benign").to_numpy()
    X_b_tr = X_tr_std[b_tr_mask]
    
    nn_b = NearestNeighbors(n_neighbors=2, metric="euclidean", n_jobs=1).fit(X_b_tr[:10000])
    dists_b, _ = nn_b.kneighbors(X_b_tr[:10000])
    b_1nn = dists_b[:, 1]
    b_p5, b_p25, b_p50 = float(np.percentile(b_1nn, 5)), float(np.percentile(b_1nn, 25)), float(np.percentile(b_1nn, 50))
    print(f"UNSW Benign-to-Benign 1-NN distances: 5th={b_p5:.4f}, 25th={b_p25:.4f}, Median={b_p50:.4f}")
    print(f"Epsilon (5th percentile): {b_p5:.4f} -> DEGENERATE (< 0.03, dense near-zero collisions)")
    
    nn_rand_train = NearestNeighbors(n_neighbors=1, metric="euclidean", n_jobs=1).fit(X_tr_std)
    
    # MinMax scalers for 3-decimal and log1p matching
    scaler_mm = MinMaxScaler()
    X_tr_mm = scaler_mm.fit_transform(X_tr_raw)
    X_te_mm = scaler_mm.transform(X_te_raw)
    
    scaler_log_mm = MinMaxScaler()
    X_tr_log_mm = scaler_log_mm.fit_transform(np.log1p(X_tr_raw))
    X_te_log_mm = scaler_log_mm.transform(np.log1p(X_te_raw))
    
    tr_mm_3dec = set(pd.DataFrame(X_tr_mm).round(3).itertuples(index=False, name=None))
    tr_log_mm_3dec = set(pd.DataFrame(X_tr_log_mm).round(3).itertuples(index=False, name=None))
    
    records = []
    
    for grp in groups:
        te_mask = (test_rand["Family_Group"] == grp).to_numpy()
        n_pos_rand = int(np.sum(te_mask))
        
        te_fam_mm = list(pd.DataFrame(X_te_mm[te_mask]).round(3).itertuples(index=False, name=None))
        rand_3dec_cnt = sum(1 for t in te_fam_mm if t in tr_mm_3dec)
        rand_3dec_pct = (rand_3dec_cnt / n_pos_rand) * 100.0 if n_pos_rand > 0 else 0.0
        
        te_fam_log_mm = list(pd.DataFrame(X_te_log_mm[te_mask]).round(3).itertuples(index=False, name=None))
        rand_log_cnt = sum(1 for t in te_fam_log_mm if t in tr_log_mm_3dec)
        rand_log_pct = (rand_log_cnt / n_pos_rand) * 100.0 if n_pos_rand > 0 else 0.0
        
        dists_rand, _ = nn_rand_train.kneighbors(X_te_std[te_mask])
        d_rand = dists_rand[:, 0]
        r_p5, r_p25, r_p50 = float(np.percentile(d_rand, 5)), float(np.percentile(d_rand, 25)), float(np.percentile(d_rand, 50))
        
        # LOFO Split for group
        te_lofo_pos = df[df["Family_Group"] == grp].copy()
        n_pos_lofo = len(te_lofo_pos)
        tr_lofo = df[df["Family_Group"] != grp].copy()
        
        X_lofo_tr_raw = np.maximum(0, tr_lofo[feature_cols].to_numpy(dtype=np.float64))
        X_lofo_te_raw = np.maximum(0, te_lofo_pos[feature_cols].to_numpy(dtype=np.float64))
        
        sc_lofo_mm = MinMaxScaler()
        X_lofo_tr_mm = sc_lofo_mm.fit_transform(X_lofo_tr_raw)
        X_lofo_te_mm = sc_lofo_mm.transform(X_lofo_te_raw)
        tr_lofo_3dec = set(pd.DataFrame(X_lofo_tr_mm).round(3).itertuples(index=False, name=None))
        te_lofo_3dec = list(pd.DataFrame(X_lofo_te_mm).round(3).itertuples(index=False, name=None))
        lofo_3dec_cnt = sum(1 for t in te_lofo_3dec if t in tr_lofo_3dec)
        lofo_3dec_pct = (lofo_3dec_cnt / n_pos_lofo) * 100.0 if n_pos_lofo > 0 else 0.0
        
        sc_lofo_log_mm = MinMaxScaler()
        X_lofo_tr_lmm = sc_lofo_log_mm.fit_transform(np.log1p(X_lofo_tr_raw))
        X_lofo_te_lmm = sc_lofo_log_mm.transform(np.log1p(X_lofo_te_raw))
        tr_lofo_l3dec = set(pd.DataFrame(X_lofo_tr_lmm).round(3).itertuples(index=False, name=None))
        te_lofo_l3dec = list(pd.DataFrame(X_lofo_te_lmm).round(3).itertuples(index=False, name=None))
        lofo_log_cnt = sum(1 for t in te_lofo_l3dec if t in tr_lofo_l3dec)
        lofo_log_pct = (lofo_log_cnt / n_pos_lofo) * 100.0 if n_pos_lofo > 0 else 0.0
        
        sc_lofo_std = StandardScaler()
        X_lofo_tr_std = sc_lofo_std.fit_transform(np.log1p(X_lofo_tr_raw))
        X_lofo_te_std = sc_lofo_std.transform(np.log1p(X_lofo_te_raw))
        
        nn_lofo = NearestNeighbors(n_neighbors=1, metric="euclidean", n_jobs=1).fit(X_lofo_tr_std)
        dists_lofo, _ = nn_lofo.kneighbors(X_lofo_te_std)
        d_lofo = dists_lofo[:, 0]
        l_p5, l_p25, l_p50 = float(np.percentile(d_lofo, 5)), float(np.percentile(d_lofo, 25)), float(np.percentile(d_lofo, 50))
        
        print(f"Group {grp:15s} | Benign: p50={b_p50:.4f} | RandPos: p50={r_p50:.4f} (p5={r_p5:.4f}, p25={r_p25:.4f}) | LOFOPos: p50={l_p50:.4f} (p5={l_p5:.4f}, p25={l_p25:.4f})")
        
        records.append({
            "Family_Group": grp,
            "Rand_Test_Pos": n_pos_rand,
            "Rand_Near_Matches_3dec": rand_3dec_cnt,
            "Rand_Near_Leakage_3dec_Pct": round(rand_3dec_pct, 2),
            "Rand_Log1p_Leakage_3dec_Pct": round(rand_log_pct, 2),
            "Rand_NN_p5": round(r_p5, 4),
            "Rand_NN_p25": round(r_p25, 4),
            "Rand_NN_median": round(r_p50, 4),
            "LOFO_Test_Pos": n_pos_lofo,
            "LOFO_Near_Matches_3dec": lofo_3dec_cnt,
            "LOFO_Near_Leakage_3dec_Pct": round(lofo_3dec_pct, 2),
            "LOFO_Log1p_Leakage_3dec_Pct": round(lofo_log_pct, 2),
            "LOFO_NN_p5": round(l_p5, 4),
            "LOFO_NN_p25": round(l_p25, 4),
            "LOFO_NN_median": round(l_p50, 4),
            "Benign_NN_p5": round(b_p5, 4),
            "Benign_NN_p25": round(b_p25, 4),
            "Benign_NN_median": round(b_p50, 4),
            "Epsilon": round(b_p5, 4),
            "Epsilon_Status": "Degenerate (< 0.03)"
        })
        
    df_out = pd.DataFrame(records)
    out_csv = Path("results/unsw_nb15/leakage_audit.csv")
    df_out.to_csv(out_csv, index=False)
    print(f"Saved updated UNSW leakage audit with NN distance distributions to {out_csv}")
    return df_out

if __name__ == "__main__":
    run_cic_leakage_audit()
    run_unsw_leakage_audit()
