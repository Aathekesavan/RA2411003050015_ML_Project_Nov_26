"""Data cleaner for SentinelX-Shift.

Handles numeric validation, infinite/NaN value resolution, exact flow deduplication,
and stratified subsampling.
"""

from typing import Dict, List, Optional, Tuple, Union
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def clean_numeric_features(
    df: pd.DataFrame,
    label_col: str = "Label",
    drop_na: bool = True
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Sanitize numeric flow features by resolving infinite and NaN values.

    Returns:
        Cleaned dataframe, and a dictionary of removal statistics.
    """
    df = df.copy()
    feature_cols = [c for c in df.columns if c != label_col]
    initial_rows = len(df)

    # Coerce all feature columns to float64
    for col in feature_cols:
        if not np.issubdtype(df[col].dtype, np.number):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Replace inf and -inf with NaN
    inf_count = int(np.isinf(df[feature_cols].to_numpy()).sum())
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], np.nan)
    nan_count = int(df[feature_cols].isna().any(axis=1).sum())

    if drop_na:
        # Drop rows containing NaNs in any feature column
        df = df.dropna(subset=feature_cols)

    stats = {
        "initial_rows": initial_rows,
        "inf_values_detected": inf_count,
        "nan_rows_dropped": nan_count,
        "remaining_rows": len(df),
    }
    logger.info(f"Numeric cleaning: {inf_count} infs detected, {nan_count} rows dropped.")
    return df, stats


def remove_exact_duplicates(
    df: pd.DataFrame,
    feature_cols_only: bool = False,
    label_col: str = "Label"
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Deduplicate flows.

    If feature_cols_only is True, drops duplicates considering only feature vectors.
    If False, considers full row (features + Label).
    """
    initial_count = len(df)
    subset = [c for c in df.columns if c != label_col] if feature_cols_only else None
    
    df_dedup = df.drop_duplicates(subset=subset, keep="first").copy()
    duplicates_dropped = initial_count - len(df_dedup)
    
    stats = {
        "before_dedup": initial_count,
        "after_dedup": len(df_dedup),
        "duplicates_dropped": duplicates_dropped,
        "duplicate_fraction": duplicates_dropped / max(1, initial_count),
    }
    logger.info(f"Deduplication: {duplicates_dropped:,} duplicate rows dropped ({stats['duplicate_fraction']:.2%}).")
    return df_dedup, stats


def stratified_subsample(
    df: pd.DataFrame,
    fraction: float = 0.05,
    label_col: str = "Label",
    random_seed: int = 42,
    min_samples_per_class: int = 10,
) -> pd.DataFrame:
    """Perform deterministic stratified subsampling across attack families.

    Preserves rare classes by enforcing a minimum floor per class where possible.
    """
    if fraction >= 1.0 or fraction <= 0.0:
        return df

    subsets = []
    for label, group in df.groupby(label_col):
        n_samples = max(min_samples_per_class, int(np.round(len(group) * fraction)))
        n_samples = min(n_samples, len(group))
        sampled = group.sample(n=n_samples, random_state=random_seed)
        subsets.append(sampled)

    sampled_df = pd.concat(subsets, ignore_index=True)
    # Shuffle so classes aren't in consecutive blocks
    return sampled_df.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)


def preserve_rare_families_sample(
    df: pd.DataFrame,
    target_total: int = 60000,
    rare_threshold: int = 20000,
    label_col: str = "Label",
    random_seed: int = 42
) -> pd.DataFrame:
    """Subsample dataset keeping 100% of rare families and subsampling abundant families.

    All families with count <= rare_threshold are retained at 100%.
    Families exceeding rare_threshold (e.g. Benign, DoS) are subsampled proportionally
    to fill the remaining row budget towards target_total.
    """
    counts = df[label_col].value_counts().to_dict()
    rare_families = {fam: cnt for fam, cnt in counts.items() if cnt <= rare_threshold}
    abundant_families = {fam: cnt for fam, cnt in counts.items() if cnt > rare_threshold}

    rare_total = sum(rare_families.values())
    logger.info(f"Rare families (100% retained): {rare_families} (Total: {rare_total:,})")

    subsets = []
    # Retain 100% of rare families
    for fam in rare_families.keys():
        subsets.append(df[df[label_col] == fam])

    # Subsample abundant families to fill the remaining budget
    remaining_budget = max(0, target_total - rare_total)
    total_abundant_available = sum(abundant_families.values())

    if total_abundant_available > 0 and remaining_budget > 0:
        for fam, cnt in abundant_families.items():
            fam_budget = int(np.round(remaining_budget * (cnt / total_abundant_available)))
            fam_budget = min(cnt, max(1, fam_budget))
            sampled_fam = df[df[label_col] == fam].sample(n=fam_budget, random_state=random_seed)
            subsets.append(sampled_fam)
    elif total_abundant_available > 0 and remaining_budget == 0:
        logger.warning("Rare families exceed target_total; keeping rare families only.")

    combined = pd.concat(subsets, ignore_index=True)
    return combined.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)

