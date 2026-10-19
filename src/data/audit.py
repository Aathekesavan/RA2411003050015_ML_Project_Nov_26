"""Leakage Audit for SentinelX-Shift.

Quantifies exact duplicate and near-duplicate leakage between test positives
and the training set across two contrasting protocols:
1. Naive Stratified Random Split (70/30): where both train and test observe the family.
2. Leave-One-Attack-Family-Out (LOFO): where the training set strictly never observes the held-out family.

Primary Metric: 3-decimal near-duplicates.
Note: 1-2 decimal rounding after MinMax scaling is a coarse sensitivity check
because netflow features are heavy-tailed. A log1p-transformed variant is reported
alongside to account for high-skew dynamic ranges.
Matches in LOFO are decomposed into:
- Matches to benign training flows
- Matches to other attack training families
"""

from typing import Dict, List, Optional, Set, Tuple, Union
import logging
from pathlib import Path
import os
import pandas as pd
import numpy as np
import yaml
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)


def audit_family_leakage(
    train_df: pd.DataFrame,
    test_positives_df: pd.DataFrame,
    feature_cols: List[str],
    rounding_decimals: List[int] = [3, 2, 1],
    label_col: str = "Label"
) -> Dict[str, Union[int, float]]:
    """Audit near-duplicate leakage for a single attack family against a training set.

    Decomposes matches into:
    - Matches to Benign training flows
    - Matches to Other Attack training flows
    """
    n_test_pos = len(test_positives_df)
    n_train = len(train_df)

    if n_test_pos == 0:
        res: Dict[str, Union[int, float]] = {
            "test_positives": 0,
            "train_samples": n_train,
            "exact_matches": 0,
            "exact_leakage_pct": 0.0,
        }
        for dec in rounding_decimals:
            res[f"near_matches_dec{dec}"] = 0
            res[f"near_leakage_pct_dec{dec}"] = 0.0
            res[f"benign_matches_dec{dec}"] = 0
            res[f"benign_leakage_pct_dec{dec}"] = 0.0
            res[f"other_attacks_matches_dec{dec}"] = 0
            res[f"other_attacks_leakage_pct_dec{dec}"] = 0.0
        return res

    # Separate train into Benign and Other Attacks
    train_benign = train_df[train_df[label_col] == "Benign"] if label_col in train_df.columns else pd.DataFrame()
    train_other_attacks = train_df[train_df[label_col] != "Benign"] if label_col in train_df.columns else pd.DataFrame()

    # 1. Exact Duplicate Audit (raw floating point values)
    train_exact_tuples = set(train_df[feature_cols].itertuples(index=False, name=None))
    test_exact_tuples = list(test_positives_df[feature_cols].itertuples(index=False, name=None))
    exact_leak_count = sum(1 for t in test_exact_tuples if t in train_exact_tuples)
    exact_leak_pct = (exact_leak_count / n_test_pos) * 100.0

    result: Dict[str, Union[int, float]] = {
        "test_positives": n_test_pos,
        "train_samples": n_train,
        "exact_matches": exact_leak_count,
        "exact_leakage_pct": round(exact_leak_pct, 4),
    }

    # 2. Multi-Decimal Rounding Near-Duplicate Audits (Disjoint Set Partition & Union)
    for dec in rounding_decimals:
        benign_tuples = set(train_benign[feature_cols].round(dec).itertuples(index=False, name=None)) if len(train_benign) > 0 else set()
        other_tuples = set(train_other_attacks[feature_cols].round(dec).itertuples(index=False, name=None)) if len(train_other_attacks) > 0 else set()
        test_tuples = list(test_positives_df[feature_cols].round(dec).itertuples(index=False, name=None))

        benign_only_cnt = 0
        other_only_cnt = 0
        both_cnt = 0
        union_cnt = 0

        for t in test_tuples:
            in_b = t in benign_tuples
            in_o = t in other_tuples
            if in_b and in_o:
                both_cnt += 1
                union_cnt += 1
            elif in_b:
                benign_only_cnt += 1
                union_cnt += 1
            elif in_o:
                other_only_cnt += 1
                union_cnt += 1

        # Mathematical verification: Union must equal sum of disjoint parts
        assert union_cnt == benign_only_cnt + other_only_cnt + both_cnt, "Union must equal sum of disjoint sets!"

        result[f"union_matches_dec{dec}"] = union_cnt
        result[f"near_matches_dec{dec}"] = union_cnt
        result[f"near_leakage_pct_dec{dec}"] = round((union_cnt / n_test_pos) * 100.0, 4)
        result[f"union_leakage_pct_dec{dec}"] = round((union_cnt / n_test_pos) * 100.0, 4)

        result[f"benign_only_matches_dec{dec}"] = benign_only_cnt
        result[f"benign_only_leakage_pct_dec{dec}"] = round((benign_only_cnt / n_test_pos) * 100.0, 4)

        result[f"other_only_matches_dec{dec}"] = other_only_cnt
        result[f"other_only_leakage_pct_dec{dec}"] = round((other_only_cnt / n_test_pos) * 100.0, 4)

        result[f"both_matches_dec{dec}"] = both_cnt
        result[f"both_leakage_pct_dec{dec}"] = round((both_cnt / n_test_pos) * 100.0, 4)

        # Total benign and total other matches (inclusive of both)
        total_benign_matches = benign_only_cnt + both_cnt
        total_other_matches = other_only_cnt + both_cnt
        result[f"benign_matches_dec{dec}"] = total_benign_matches
        result[f"benign_near_matches_dec{dec}"] = total_benign_matches
        result[f"benign_leakage_pct_dec{dec}"] = round((total_benign_matches / n_test_pos) * 100.0, 4)
        result[f"benign_near_leakage_pct_dec{dec}"] = result[f"benign_leakage_pct_dec{dec}"]
        result[f"other_attacks_matches_dec{dec}"] = total_other_matches
        result[f"other_attacks_near_matches_dec{dec}"] = total_other_matches
        result[f"other_attacks_leakage_pct_dec{dec}"] = round((total_other_matches / n_test_pos) * 100.0, 4)
        result[f"other_attacks_near_leakage_pct_dec{dec}"] = result[f"other_attacks_leakage_pct_dec{dec}"]

    return result


def compute_knn_leakage(
    train_df: pd.DataFrame,
    test_positives_df: pd.DataFrame,
    feature_cols: List[str],
    label_col: str = "Label",
    random_seed: int = 42,
    max_benign_samples: int = 15000
) -> Dict[str, float]:
    """Rounding-independent leakage measure using nearest-neighbor distances on log1p + StandardScaler.

    1. Fit StandardScaler strictly on log1p(train_features).
    2. Compute epsilon = 5th percentile of 1-NN distances between benign training flows.
    3. Query test positives: calculate median nearest-neighbor distance and % within epsilon.
    """
    from sklearn.preprocessing import StandardScaler
    from sklearn.neighbors import NearestNeighbors

    # 1. Transform features: log1p + StandardScaler fit strictly on train
    X_train_raw = np.maximum(0, train_df[feature_cols].to_numpy(dtype=np.float64))
    X_test_raw = np.maximum(0, test_positives_df[feature_cols].to_numpy(dtype=np.float64))

    X_train_log = np.log1p(X_train_raw)
    X_test_log = np.log1p(X_test_raw)

    scaler = StandardScaler()
    X_train_std = scaler.fit_transform(X_train_log)
    X_test_std = scaler.transform(X_test_log)

    # 2. Compute epsilon from benign training flows
    train_benign_mask = (train_df[label_col] == "Benign").to_numpy() if label_col in train_df.columns else np.ones(len(train_df), dtype=bool)
    X_train_benign = X_train_std[train_benign_mask]

    if len(X_train_benign) > max_benign_samples:
        rng = np.random.RandomState(random_seed)
        sub_idx = rng.choice(len(X_train_benign), size=max_benign_samples, replace=False)
        X_train_benign_sub = X_train_benign[sub_idx]
    else:
        X_train_benign_sub = X_train_benign

    # 2-NN on benign to get distance to 1st neighbor (excluding self at index 0)
    nn_benign = NearestNeighbors(n_neighbors=2, metric="euclidean", n_jobs=2)
    nn_benign.fit(X_train_benign_sub)
    dists_benign, _ = nn_benign.kneighbors(X_train_benign_sub)
    benign_1nn_dists = dists_benign[:, 1]
    epsilon = float(np.percentile(benign_1nn_dists, 5.0))

    # 3. Query test positives against full training set
    nn_train = NearestNeighbors(n_neighbors=1, metric="euclidean", n_jobs=2)
    nn_train.fit(X_train_std)
    dists_test, _ = nn_train.kneighbors(X_test_std)
    test_1nn_dists = dists_test[:, 0]

    median_dist = float(np.median(test_1nn_dists))
    pct_within_eps = float(np.mean(test_1nn_dists <= epsilon) * 100.0)

    return {
        "epsilon": round(epsilon, 4),
        "median_nn_dist": round(median_dist, 4),
        "pct_within_eps": round(pct_within_eps, 4),
    }


def apply_scaling(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: List[str],
    use_log1p: bool = False
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Fit MinMaxScaler on train only and transform test, optionally applying log1p first."""
    scaler = MinMaxScaler()
    train_out = train_df.copy()
    test_out = test_df.copy()

    X_tr = train_df[feature_cols].to_numpy(dtype=np.float64)
    X_te = test_df[feature_cols].to_numpy(dtype=np.float64)

    if use_log1p:
        # Clip negative values before log1p
        X_tr = np.log1p(np.maximum(0, X_tr))
        X_te = np.log1p(np.maximum(0, X_te))

    train_out[feature_cols] = scaler.fit_transform(X_tr)
    test_out[feature_cols] = scaler.transform(X_te)
    return train_out, test_out


def run_leakage_contrast_audit(
    df: pd.DataFrame,
    families: Optional[List[str]] = None,
    feature_cols: Optional[List[str]] = None,
    test_size: float = 0.3,
    rounding_levels: List[int] = [3, 2, 1],
    label_col: str = "Label",
    random_seed: int = 42
) -> pd.DataFrame:
    """Run side-by-side leakage audit comparing Naive Random Split vs LOFO Split.

    Reports:
    - Primary metric: 3-decimal near-duplicate leakage
    - Coarse sensitivity: 2 and 1 decimal near-duplicate leakage
    - Log1p-transformed scaling variant
    - LOFO decomposition: matches to benign vs other attack families
    """
    if feature_cols is None:
        feature_cols = [c for c in df.columns if c != label_col]

    if families is None:
        families = [l for l in df[label_col].unique() if l != "Benign"]

    # 1. Prepare Naive Stratified Random 70/30 Split
    train_rand, test_rand = train_test_split(
        df,
        test_size=test_size,
        random_state=random_seed,
        stratify=df[label_col]
    )

    # Scale standard and log1p for random split
    train_rand_std, test_rand_std = apply_scaling(train_rand, test_rand, feature_cols, use_log1p=False)
    train_rand_log, test_rand_log = apply_scaling(train_rand, test_rand, feature_cols, use_log1p=True)

    # 2. Prepare Benign Split for LOFO
    benign_df = df[df[label_col] == "Benign"]
    n_test_benign = int(np.round(len(benign_df) * test_size))
    benign_shuffled = benign_df.sample(frac=1.0, random_state=random_seed)
    train_benign_lofo = benign_shuffled.iloc[n_test_benign:]

    records = []
    for fam in families:
        # A. Random Split Audit (Standard Scaling)
        test_pos_rand_std = test_rand_std[test_rand_std[label_col] == fam]
        audit_rand_std = audit_family_leakage(
            train_df=train_rand_std,
            test_positives_df=test_pos_rand_std,
            feature_cols=feature_cols,
            rounding_decimals=rounding_levels,
            label_col=label_col
        )

        # B. Random Split Audit (Log1p Scaling)
        test_pos_rand_log = test_rand_log[test_rand_log[label_col] == fam]
        audit_rand_log = audit_family_leakage(
            train_df=train_rand_log,
            test_positives_df=test_pos_rand_log,
            feature_cols=feature_cols,
            rounding_decimals=rounding_levels,
            label_col=label_col
        )

        # C. LOFO Split Audit (Standard & Log1p Scaling)
        test_pos_lofo = df[df[label_col] == fam].copy()
        other_attacks = df[(df[label_col] != "Benign") & (df[label_col] != fam)]
        train_lofo = pd.concat([train_benign_lofo, other_attacks], ignore_index=True)

        train_lofo_std, test_lofo_std = apply_scaling(train_lofo, test_pos_lofo, feature_cols, use_log1p=False)
        train_lofo_log, test_lofo_log = apply_scaling(train_lofo, test_pos_lofo, feature_cols, use_log1p=True)

        audit_lofo_std = audit_family_leakage(
            train_df=train_lofo_std,
            test_positives_df=test_lofo_std,
            feature_cols=feature_cols,
            rounding_decimals=rounding_levels,
            label_col=label_col
        )
        audit_lofo_log = audit_family_leakage(
            train_df=train_lofo_log,
            test_positives_df=test_lofo_log,
            feature_cols=feature_cols,
            rounding_decimals=rounding_levels,
            label_col=label_col
        )

        records.append({
            "Family": fam,
            "Test_Positives_Rand": audit_rand_std["test_positives"],
            "Test_Positives_LOFO": audit_lofo_std["test_positives"],
            # Raw Counts (3 decimals)
            "Rand_Near_Matches_3dec_Count": audit_rand_std["near_matches_dec3"],
            "LOFO_Total_Matches_3dec_Count": audit_lofo_std["union_matches_dec3"],
            "LOFO_Benign_Only_3dec_Count": audit_lofo_std["benign_only_matches_dec3"],
            "LOFO_Other_Attacks_Only_3dec_Count": audit_lofo_std["other_only_matches_dec3"],
            "LOFO_Both_Overlap_3dec_Count": audit_lofo_std["both_matches_dec3"],
            # Percentages (3 decimals - Primary Metric)
            "Rand_Near_Leakage_3dec_Pct": audit_rand_std["near_leakage_pct_dec3"],
            "LOFO_Near_Leakage_3dec_Pct": audit_lofo_std["near_leakage_pct_dec3"],
            "LOFO_Matches_Benign_3dec_Pct": audit_lofo_std["benign_leakage_pct_dec3"],
            "LOFO_Matches_OtherAttacks_3dec_Pct": audit_lofo_std["other_attacks_leakage_pct_dec3"],
            "LOFO_Both_Overlap_3dec_Pct": audit_lofo_std["both_leakage_pct_dec3"],
            # Log1p Variant (3 decimals)
            "Rand_Log1p_Near_Leakage_3dec_Pct": audit_rand_log["near_leakage_pct_dec3"],
            "LOFO_Log1p_Near_Leakage_3dec_Pct": audit_lofo_log["near_leakage_pct_dec3"],
            "LOFO_Log1p_Matches_Benign_3dec_Pct": audit_lofo_log["benign_leakage_pct_dec3"],
            "LOFO_Log1p_Matches_OtherAttacks_3dec_Pct": audit_lofo_log["other_attacks_leakage_pct_dec3"],
            # Coarse Sensitivity Checks (2 dec and 1 dec)
            "Rand_Near_Leakage_2dec_Pct": audit_rand_std["near_leakage_pct_dec2"],
            "LOFO_Near_Leakage_2dec_Pct": audit_lofo_std["near_leakage_pct_dec2"],
            "LOFO_Matches_Benign_2dec_Pct": audit_lofo_std["benign_leakage_pct_dec2"],
            "LOFO_Matches_OtherAttacks_2dec_Pct": audit_lofo_std["other_attacks_leakage_pct_dec2"],
            "Rand_Near_Leakage_1dec_Pct": audit_rand_std["near_leakage_pct_dec1"],
            "LOFO_Near_Leakage_1dec_Pct": audit_lofo_std["near_leakage_pct_dec1"],
            "LOFO_Matches_Benign_1dec_Pct": audit_lofo_std["benign_leakage_pct_dec1"],
            "LOFO_Matches_OtherAttacks_1dec_Pct": audit_lofo_std["other_attacks_leakage_pct_dec1"],
            # Exact Match Counts & Pct
            "Rand_Exact_Matches_Count": audit_rand_std["exact_matches"],
            "LOFO_Exact_Matches_Count": audit_lofo_std["exact_matches"],
            "Rand_Exact_Leakage_Pct": audit_rand_std["exact_leakage_pct"],
            "LOFO_Exact_Leakage_Pct": audit_lofo_std["exact_leakage_pct"],
        })

    return pd.DataFrame(records)


def plot_leakage_contrast(
    contrast_df: pd.DataFrame,
    output_image_path: Union[str, Path] = "results/leakage_audit_comparison.png"
) -> Path:
    """Generate and save grouped bar chart comparing Random Split vs LOFO leakage."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out_path = Path(output_image_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    families = contrast_df["Family"].tolist()
    x = np.arange(len(families))
    width = 0.18

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)

    # Compare Random Split (3 dec) vs LOFO (3 dec: Benign vs Other) vs Log1p
    ax.bar(x - 1.5 * width, contrast_df["Rand_Near_Leakage_3dec_Pct"], width, label="Random Split (3 decimals)", color="#d95f02", alpha=0.9)
    ax.bar(x - 0.5 * width, contrast_df["LOFO_Near_Leakage_3dec_Pct"], width, label="LOFO Total (3 decimals)", color="#7570b3", alpha=0.9)
    ax.bar(x + 0.5 * width, contrast_df["LOFO_Matches_Benign_3dec_Pct"], width, label="LOFO Benign-Overlap (3 dec)", color="#1b9e77", alpha=0.9)
    ax.bar(x + 1.5 * width, contrast_df["LOFO_Log1p_Near_Leakage_3dec_Pct"], width, label="LOFO Log1p Variant (3 dec)", color="#e6ab02", alpha=0.9)

    ax.set_ylabel("Near-Duplicate Leakage Into Training Set (%)", fontsize=11, fontweight="bold")
    ax.set_title("Near-Duplicate Leakage Audit (Primary 3-Decimal Metric & Benign Breakdown)", fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(families, fontsize=11, fontweight="bold")
    ax.set_ylim(0, 105)
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend(loc="upper right", frameon=True, fontsize=9)

    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    logger.info(f"Leakage comparison bar chart saved to {out_path}")
    return out_path


def measure_naive_xgboost_performance(
    df: pd.DataFrame,
    label_col: str = "Label",
    test_size: float = 0.3,
    random_seed: int = 42
) -> Dict[str, Union[float, str]]:
    """Empirically measure test accuracy and macro F1 of XGBoost under naive random split."""
    from xgboost import XGBClassifier
    from sklearn.metrics import accuracy_score, f1_score, classification_report
    from sklearn.preprocessing import LabelEncoder

    feature_cols = [c for c in df.columns if c != label_col]
    X = df[feature_cols]
    y = df[label_col]

    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=test_size, random_state=random_seed, stratify=y_encoded
    )

    clf = XGBClassifier(
        n_estimators=50,
        max_depth=4,
        learning_rate=0.1,
        random_state=random_seed,
        n_jobs=2,
        eval_metric="mlogloss"
    )
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    f1_macro = float(f1_score(y_test, y_pred, average="macro"))
    rep = classification_report(y_test, y_pred, target_names=le.classes_, digits=4)

    return {
        "accuracy": acc,
        "f1_macro": f1_macro,
        "classification_report": rep,
        "n_train": len(X_train),
        "n_test": len(X_test),
    }


def main():
    """Run full contrast leakage audit and generate table, CSV, and chart."""
    from src.data.loader import load_config
    config = load_config()
    processed_path = Path(config["data"]["output_parquet"])
    results_dir = Path("results")
    results_dir.mkdir(parents=True, exist_ok=True)

    if not processed_path.exists():
        print(f"Processed file {processed_path} not found. Running data pipeline...")
        from src.data.pipeline import run_pipeline
        run_pipeline()

    print(f"Loading {processed_path}...")
    df = pd.read_parquet(processed_path)
    families = config["data"]["active_attack_families"]

    print("Running Random Split vs LOFO Leakage Contrast Audit (Primary 3-decimal + Log1p)...")
    contrast_df = run_leakage_contrast_audit(
        df=df,
        families=families,
        rounding_levels=[3, 2, 1],
        random_seed=config["global_settings"]["random_seed"]
    )

    # Save to CSV
    csv_path = results_dir / "leakage_audit.csv"
    contrast_df.to_csv(csv_path, index=False)
    print(f"Saved audit CSV to {csv_path}")

    # Generate Chart
    chart_path = results_dir / "leakage_audit_comparison.png"
    plot_leakage_contrast(contrast_df, chart_path)

    # Display Primary Metric Table
    print("\n--- PRIMARY 3-DECIMAL LEAKAGE AUDIT WITH BENIGN / OTHER-ATTACK SPLIT ---")
    primary_cols = [
        "Family",
        "Test_Positives_LOFO",
        "LOFO_Total_Matches_3dec_Count",
        "LOFO_Benign_Only_3dec_Count",
        "LOFO_Other_Attacks_Only_3dec_Count",
        "LOFO_Both_Overlap_3dec_Count",
        "Rand_Near_Leakage_3dec_Pct",
        "LOFO_Near_Leakage_3dec_Pct",
        "LOFO_Matches_Benign_3dec_Pct",
        "LOFO_Matches_OtherAttacks_3dec_Pct",
        "LOFO_Both_Overlap_3dec_Pct",
        "Rand_Log1p_Near_Leakage_3dec_Pct",
        "LOFO_Log1p_Near_Leakage_3dec_Pct",
    ]
    sub_df = contrast_df[primary_cols]
    headers = list(sub_df.columns)
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for _, row in sub_df.iterrows():
        row_str = " | ".join(str(row[c]) for c in headers)
        lines.append(f"| {row_str} |")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
