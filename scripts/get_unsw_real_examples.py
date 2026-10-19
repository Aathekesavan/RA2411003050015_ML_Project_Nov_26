"""Extract 5 real UNSW-NB15 test flows and their nearest training neighbors."""
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from src.data.adapters.unswnb15 import UNSWNB15Adapter

def main():
    adapter = UNSWNB15Adapter(max_rows=50000, random_seed=42)
    features_df, y_binary, attack_cat, family_group, card = adapter.load()
    print(f"Loaded UNSW: {len(features_df):,} flows, {len(features_df.columns)} features.")

    df = features_df.copy()
    df["Label"] = attack_cat
    df["Family_Group"] = family_group
    df["is_attack"] = y_binary

    feature_cols = list(features_df.columns)

    # Stratified 70/30 random split
    train_df, test_df = train_test_split(df, test_size=0.3, random_state=42, stratify=df["Family_Group"])

    # Scale log1p + StandardScaler fit strictly on train
    X_tr_raw = np.maximum(0, train_df[feature_cols].to_numpy(dtype=np.float64))
    X_te_raw = np.maximum(0, test_df[feature_cols].to_numpy(dtype=np.float64))

    X_tr_log = np.log1p(X_tr_raw)
    X_te_log = np.log1p(X_te_raw)

    scaler = StandardScaler()
    X_tr_std = scaler.fit_transform(X_tr_log)
    X_te_std = scaler.transform(X_te_log)

    # Benign epsilon
    b_tr_mask = (train_df["is_attack"] == 0).to_numpy()
    X_b_tr = X_tr_std[b_tr_mask]
    nn_b = NearestNeighbors(n_neighbors=2, metric="euclidean", n_jobs=2).fit(X_b_tr[:10000])
    dists_b, _ = nn_b.kneighbors(X_b_tr[:10000])
    epsilon = float(np.percentile(dists_b[:, 1], 5.0))
    print(f"Epsilon (5th percentile 1-NN benign): {epsilon:.4f}")

    # Nearest neighbor on train
    test_att_mask = (test_df["is_attack"] == 1).to_numpy()
    test_att_df = test_df[test_att_mask].copy().reset_index(drop=True)
    X_te_att = X_te_std[test_att_mask]

    nn_train = NearestNeighbors(n_neighbors=1, metric="euclidean", n_jobs=2).fit(X_tr_std)
    dists_te, idxs_te = nn_train.kneighbors(X_te_att)
    dists_te = dists_te[:, 0]
    idxs_te = idxs_te[:, 0]

    within_eps = dists_te <= epsilon
    print(f"Total test attack flows: {len(test_att_df)}")
    print(f"Within epsilon: {int(np.sum(within_eps))} ({np.mean(within_eps)*100:.2f}%)")
    print(f"Median NN distance: {float(np.median(dists_te)):.4f}")

    near_indices = np.where(within_eps)[0]
    far_indices = np.where(~within_eps)[0]

    # Select 2 near-duplicate flows and 3 non-near flows
    selected = list(near_indices[:2]) + list(far_indices[:3])
    key_cols = ["dur", "spkts", "dpkts", "sbytes", "dbytes", "rate", "sttl", "dttl"]
    key_cols = [c for c in key_cols if c in feature_cols]

    print("\n" + "="*80)
    print("5 REAL UNSW-NB15 TEST FLOWS WITH NEAREST RANDOM-SPLIT TRAINING NEIGHBORS")
    print("="*80)

    for i, s_idx in enumerate(selected):
        t_row = test_att_df.iloc[s_idx]
        tr_row = train_df.iloc[idxs_te[s_idx]]
        d = dists_te[s_idx]
        verdict = "NEAR-DUPLICATE (<= epsilon)" if d <= epsilon else "DISTINCT (> epsilon)"
        print(f"\n[Flow {i+1}] Verdict: {verdict} | NN Distance: {d:.4f} (Epsilon: {epsilon:.4f})")
        print(f"  Test Positive Flow : Group={t_row['Family_Group']}, Attack={t_row['Label']}")
        print(f"    Key Features: " + ", ".join(f"{c}={t_row[c]}" for c in key_cols))
        print(f"  Nearest Train Flow : Group={tr_row['Family_Group']}, Attack={tr_row['Label']}")
        print(f"    Key Features: " + ", ".join(f"{c}={tr_row[c]}" for c in key_cols))

if __name__ == "__main__":
    main()
