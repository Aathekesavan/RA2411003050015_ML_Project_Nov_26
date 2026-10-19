"""Extract 5 real UNSW test flows and their nearest training neighbors,
plus print the exact raw counts, definitions, and verify the computation.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.neighbors import NearestNeighbors

def main():
    p = Path("data/processed/unsw_nb15/unsw_nb15_cleaned.parquet")
    df = pd.read_parquet(p)
    print(f"Loaded UNSW cleaned dataset: {len(df):,} rows, {len(df.columns)} columns")
    print(f"Columns: {list(df.columns[:10])} ... Label column: {df.columns[-3:]}")

    non_feature_cols = ["y_binary", "Label", "Family_Group", "attack_cat", "label", "binary_label"]
    label_col = "Family_Group" if "Family_Group" in df.columns else "Label"
    feature_cols = [c for c in df.columns if c not in non_feature_cols]

    print(f"Feature count: {len(feature_cols)}, Label column: {label_col}")
    print(f"Class distribution:\n{df[label_col].value_counts()}")

    # Perform stratified 70/30 random split (seed 42)
    train_df, test_df = train_test_split(df, test_size=0.3, random_state=42, stratify=df[label_col])
    print(f"Train size: {len(train_df):,}, Test size: {len(test_df):,}")

    # Standardize log1p features fit strictly on train
    X_train_raw = np.maximum(0, train_df[feature_cols].to_numpy(dtype=np.float64))
    X_test_raw = np.maximum(0, test_df[feature_cols].to_numpy(dtype=np.float64))

    X_train_log = np.log1p(X_train_raw)
    X_test_log = np.log1p(X_test_raw)

    scaler = StandardScaler()
    X_train_std = scaler.fit_transform(X_train_log)
    X_test_std = scaler.transform(X_test_log)

    # Compute epsilon: 5th percentile of 1-NN distances between benign training flows
    train_benign_mask = (train_df[label_col] == "Benign").to_numpy()
    X_train_benign = X_train_std[train_benign_mask]

    # Sample up to 10k benign
    rng = np.random.RandomState(42)
    sub_idx = rng.choice(len(X_train_benign), size=min(10000, len(X_train_benign)), replace=False)
    X_b_sub = X_train_benign[sub_idx]

    nn_benign = NearestNeighbors(n_neighbors=2, metric="euclidean", n_jobs=2)
    nn_benign.fit(X_b_sub)
    dists_b, _ = nn_benign.kneighbors(X_b_sub)
    benign_1nn_dists = dists_b[:, 1]
    epsilon = float(np.percentile(benign_1nn_dists, 5.0))
    print(f"Epsilon (5th percentile 1-NN distance between benign flows): {epsilon:.6f}")

    # Query test positives against train
    test_attack_mask = (test_df[label_col] != "Benign").to_numpy()
    test_attacks_df = test_df[test_attack_mask].copy().reset_index(drop=True)
    X_test_att_std = X_test_std[test_attack_mask]

    nn_train = NearestNeighbors(n_neighbors=1, metric="euclidean", n_jobs=2)
    nn_train.fit(X_train_std)
    dists_test, indices_test = nn_train.kneighbors(X_test_att_std)
    dists_test = dists_test[:, 0]
    indices_test = indices_test[:, 0]

    # Print overall stats
    within_eps = dists_test <= epsilon
    print(f"Total test positives: {len(test_attacks_df)}")
    print(f"Test positives with NN dist <= epsilon: {int(np.sum(within_eps))} ({np.mean(within_eps)*100:.2f}%)")
    print(f"Median NN distance: {float(np.median(dists_test)):.4f}")

    # Select 5 representative test attack flows: 2 within epsilon (near duplicates) and 3 outside epsilon
    near_idx = np.where(within_eps)[0]
    far_idx = np.where(~within_eps)[0]

    selected_test_indices = []
    if len(near_idx) >= 2:
        selected_test_indices.extend(near_idx[:2])
    else:
        selected_test_indices.extend(near_idx)
    remaining = 5 - len(selected_test_indices)
    selected_test_indices.extend(far_idx[:remaining])

    print("\n--- 5 REAL TEST FLOWS WITH NEAREST TRAINING NEIGHBORS ---")
    key_features = ["dur", "sbytes", "dbytes", "sttl", "dttl", "sload", "dload", "spkts", "dpkts"]
    avail_key_feats = [f for f in key_features if f in feature_cols]
    if len(avail_key_feats) < 5:
        avail_key_feats = feature_cols[:6]

    for i, t_idx in enumerate(selected_test_indices):
        tr_idx = indices_test[t_idx]
        d = dists_test[t_idx]
        t_row = test_attacks_df.iloc[t_idx]
        tr_row = train_df.iloc[tr_idx]

        print(f"\nExample {i+1}:")
        print(f"  Test Flow: Family={t_row[label_col]}, NN Distance={d:.4f} ({'<= eps (NEAR DUPLICATE)' if d <= epsilon else '> eps'})")
        print(f"    Features (Test) : " + ", ".join(f"{f}={t_row[f]}" for f in avail_key_feats))
        print(f"  Nearest Train Flow: Family={tr_row[label_col]}")
        print(f"    Features (Train): " + ", ".join(f"{f}={tr_row[f]}" for f in avail_key_feats))

if __name__ == "__main__":
    main()
