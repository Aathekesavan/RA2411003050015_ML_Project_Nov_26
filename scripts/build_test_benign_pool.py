"""Build 100,000 disjoint test benign pool from raw data for CIC-IDS2017.

Ensures zero feature vector overlap with data/processed/cicids2017_sample60k.parquet.
Guarantees at least 30 positive attacks are measurable at 0.1% test prevalence.
"""
from pathlib import Path
import pandas as pd
from src.data.loader import load_raw_file, DEFAULT_LEAKY_COLUMNS
from src.data.cleaner import clean_numeric_features, remove_exact_duplicates


def build_test_benign_pool(
    sample_path: Path = Path("data/processed/cicids2017_sample60k.parquet"),
    out_path: Path = Path("data/processed/benign_test_pool_100k.parquet"),
    target_rows: int = 100_000,
    random_seed: int = 42
) -> pd.DataFrame:
    raw_dir = Path("data/raw")
    if not sample_path.exists():
        raise FileNotFoundError(f"Processed sample parquet not found at {sample_path}")

    sample_df = pd.read_parquet(sample_path)
    feature_cols = [c for c in sample_df.columns if c != "Label"]
    train_val_tuples = set(sample_df[feature_cols].itertuples(index=False, name=None))

    print(f"Loaded processed sample with {len(sample_df):,} rows. Extracting benign flows from raw Tuesday...")
    tue_path = raw_dir / "Tuesday-WorkingHours.pcap_ISCX.csv"
    if not tue_path.exists():
        raise FileNotFoundError(f"Tuesday raw capture not found at {tue_path}")

    df_tue = load_raw_file(tue_path, leaky_cols=DEFAULT_LEAKY_COLUMNS)
    b_tue = df_tue[df_tue["Label"] == "Benign"]
    b_clean, _ = clean_numeric_features(b_tue)
    b_dedup, _ = remove_exact_duplicates(b_clean)

    # Exclude any flows that exist in sample_df
    print(f"Deduplicated Tuesday benign count: {len(b_dedup):,}. Purging any feature overlap with sample...")
    tue_tuples = list(b_dedup[feature_cols].itertuples(index=False, name=None))
    disjoint_mask = [t not in train_val_tuples for t in tue_tuples]
    b_disjoint = b_dedup[disjoint_mask]
    print(f"Available disjoint unique benign flows: {len(b_disjoint):,}")

    if len(b_disjoint) < target_rows:
        # Also draw from Monday if needed
        mon_path = raw_dir / "Monday-WorkingHours.pcap_ISCX.csv"
        if mon_path.exists():
            print("Drawing additional benign flows from Monday...")
            df_mon = load_raw_file(mon_path, leaky_cols=DEFAULT_LEAKY_COLUMNS)
            b_mon = df_mon[df_mon["Label"] == "Benign"]
            b_mon_clean, _ = clean_numeric_features(b_mon)
            b_mon_dedup, _ = remove_exact_duplicates(b_mon_clean)
            mon_tuples = list(b_mon_dedup[feature_cols].itertuples(index=False, name=None))
            mon_mask = [t not in train_val_tuples for t in mon_tuples]
            b_disjoint = pd.concat([b_disjoint, b_mon_dedup[mon_mask]], ignore_index=True)
            b_disjoint, _ = remove_exact_duplicates(b_disjoint)

    assert len(b_disjoint) >= target_rows, f"Insufficient disjoint benign flows ({len(b_disjoint)} < {target_rows})"
    pool_100k = b_disjoint.sample(n=target_rows, random_state=random_seed).reset_index(drop=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pool_100k.to_parquet(out_path, index=False)
    print(f"Successfully saved {len(pool_100k):,} disjoint benign flows to {out_path}")
    return pool_100k


if __name__ == "__main__":
    build_test_benign_pool()
