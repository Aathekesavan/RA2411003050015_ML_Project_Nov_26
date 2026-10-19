"""Leave-One-Attack-Family-Out (LOFO) Split Engine for SentinelX-Shift.

Strict Protocol:
For each held-out attack family F:
1. BENIGN flows are deterministically partitioned into disjoint 60/20/20 splits:
   benign_train, benign_val, benign_test.
2. Training split contains: benign_train + all other attack families (strictly no F).
3. Validation split contains: benign_val + held-out portion of other attack families (strictly no F).
4. Test split contains: benign_test + held-out family F ONLY.
5. Prevalence resampling adjusts the test set to target intrusion ratios (0.1%, 1%, 5%, 10%),
   recording whether attack or benign flows were subsampled. If positives < 30, the fold
   is flagged as 'low-power' and 20 repeat seeds are generated.
6. Scalers are fitted exclusively on the training split and saved per fold.
7. Strict assertions guarantee:
   - F is strictly absent from train and val.
   - Test set contains only Benign and F.
   - Zero benign row overlap across train/val/test splits.
   - Zero duplicate feature vectors across splits.
8. Manifest JSONs with SHA-256 hashes are recorded to results/manifests/.
"""

from typing import Dict, List, Optional, Set, Tuple, Union, Any
import logging
import json
import hashlib
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import joblib

logger = logging.getLogger(__name__)


def compute_df_sha256(df: pd.DataFrame) -> str:
    """Compute deterministic SHA-256 checksum of a DataFrame."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def split_benign_flows(
    benign_df: pd.DataFrame,
    train_ratio: float = 0.6,
    val_ratio: float = 0.2,
    test_ratio: float = 0.2,
    random_seed: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Deterministically partition benign flows into 3 strictly disjoint sets."""
    assert np.isclose(train_ratio + val_ratio + test_ratio, 1.0), "Ratios must sum to 1.0"
    
    shuffled = benign_df.sample(frac=1.0, random_state=random_seed)
    n_total = len(shuffled)
    n_train = int(np.round(n_total * train_ratio))
    n_val = int(np.round(n_total * val_ratio))

    train_benign = shuffled.iloc[:n_train].copy()
    val_benign = shuffled.iloc[n_train:n_train + n_val].copy()
    test_benign = shuffled.iloc[n_train + n_val:].copy()

    # Verify disjoint indices
    idx_tr = set(train_benign.index)
    idx_val = set(val_benign.index)
    idx_te = set(test_benign.index)
    assert len(idx_tr & idx_val) == 0, "Benign train/val index overlap"
    assert len(idx_tr & idx_te) == 0, "Benign train/test index overlap"
    assert len(idx_val & idx_te) == 0, "Benign val/test index overlap"

    return train_benign, val_benign, test_benign


def resample_prevalence(
    benign_test: pd.DataFrame,
    attack_test: pd.DataFrame,
    target_prevalence: float,
    random_seed: int = 42,
    min_power_threshold: int = 30,
    low_power_seeds_count: int = 20
) -> Dict[str, Any]:
    """Resample test set to exact target attack prevalence.

    Prevalence p = N_attack / (N_attack + N_benign)
    => N_attack = N_benign * (p / (1 - p))

    Returns:
        Dictionary containing resampled test dataframe, metadata, and multi-seed draws if low-power.
    """
    n_benign_avail = len(benign_test)
    n_attack_avail = len(attack_test)

    # Required attacks if keeping all benign test flows
    n_att_needed = int(np.round(n_benign_avail * (target_prevalence / (1.0 - target_prevalence))))

    if n_att_needed <= n_attack_avail:
        # Attack side is plentiful -> subsample attacks, keep all benign
        subsampled_side = "attack"
        n_attack_final = max(1, n_att_needed)
        n_benign_final = n_benign_avail
        sampled_attack = attack_test.sample(n=n_attack_final, random_state=random_seed)
        sampled_benign = benign_test.copy()
    else:
        # Attack side is limited -> keep all attacks, subsample benign
        subsampled_side = "benign"
        n_attack_final = n_attack_avail
        n_ben_needed = int(np.round(n_attack_avail * ((1.0 - target_prevalence) / target_prevalence)))
        n_benign_final = min(n_benign_avail, max(1, n_ben_needed))
        sampled_attack = attack_test.copy()
        sampled_benign = benign_test.sample(n=n_benign_final, random_state=random_seed)

    test_resampled = pd.concat([sampled_benign, sampled_attack], ignore_index=True)
    test_resampled = test_resampled.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)
    actual_prevalence = n_attack_final / (n_attack_final + n_benign_final)

    is_low_power = (n_attack_final < min_power_threshold)
    multi_seed_info = []

    if is_low_power:
        # Generate 20 multi-seed draws so evaluation metrics can be averaged
        for i in range(low_power_seeds_count):
            s_seed = random_seed + i
            if subsampled_side == "attack":
                s_att = attack_test.sample(n=n_attack_final, random_state=s_seed)
                s_ben = benign_test.copy()
            else:
                s_att = attack_test.copy()
                s_ben = benign_test.sample(n=n_benign_final, random_state=s_seed)
            multi_seed_info.append({
                "seed": s_seed,
                "n_attack": len(s_att),
                "n_benign": len(s_ben),
                "sha256": compute_df_sha256(pd.concat([s_ben, s_att], ignore_index=True))
            })

    return {
        "test_df": test_resampled,
        "n_attack": n_attack_final,
        "n_benign": n_benign_final,
        "total_test": len(test_resampled),
        "target_prevalence": target_prevalence,
        "actual_prevalence": round(actual_prevalence, 6),
        "subsampled_side": subsampled_side,
        "is_low_power": is_low_power,
        "multi_seed_runs": multi_seed_info,
    }


def verify_lofo_split_integrity(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    held_out_family: str,
    benign_train_idx: Set[Any],
    benign_val_idx: Set[Any],
    benign_test_idx: Set[Any],
    feature_cols: List[str],
    label_col: str = "Label"
) -> None:
    """Rigorous assertion battery verifying absence of leakage across splits."""
    # 1. Held-out family F is strictly absent from train and val
    train_labels = set(train[label_col].unique())
    val_labels = set(val[label_col].unique())
    if held_out_family in train_labels:
        raise AssertionError(f"Leakage: held-out family '{held_out_family}' is present in train split!")
    if held_out_family in val_labels:
        raise AssertionError(f"Leakage: held-out family '{held_out_family}' is present in val split!")

    # 2. Test split contains strictly Benign and F ONLY
    test_labels = set(test[label_col].unique())
    invalid_test_labels = test_labels - {"Benign", held_out_family}
    if invalid_test_labels:
        raise AssertionError(f"Test split contains unauthorized labels: {invalid_test_labels}")

    # 3. No benign row index appears in more than one split
    idx_overlap = (
        (benign_train_idx & benign_val_idx) |
        (benign_train_idx & benign_test_idx) |
        (benign_val_idx & benign_test_idx)
    )
    if idx_overlap:
        raise AssertionError(f"Benign row index overlap detected across splits! Count: {len(idx_overlap)}")

    # 4. Zero duplicate feature vectors across splits
    train_tuples = set(train[feature_cols].itertuples(index=False, name=None))
    val_tuples = set(val[feature_cols].itertuples(index=False, name=None))
    test_tuples = set(test[feature_cols].itertuples(index=False, name=None))

    if train_tuples & val_tuples:
        raise AssertionError(f"Duplicate feature vectors found between train and val splits!")
    if train_tuples & test_tuples:
        raise AssertionError(f"Duplicate feature vectors found between train and test splits!")
    if val_tuples & test_tuples:
        raise AssertionError(f"Duplicate feature vectors found between val and test splits!")


class LOFOSplitEngine:
    """Manages Leave-One-Attack-Family-Out fold generation, scaling, and manifests."""

    def __init__(
        self,
        random_seed: int = 42,
        benign_train_ratio: float = 0.6,
        benign_val_ratio: float = 0.2,
        benign_test_ratio: float = 0.2,
        manifest_dir: Union[str, Path] = "results/manifests",
        models_dir: Union[str, Path] = "results/models",
        benign_test_pool_path: Optional[Union[str, Path]] = "data/processed/benign_test_pool_100k.parquet",
        label_col: str = "Label"
    ):
        self.random_seed = random_seed
        self.benign_train_ratio = benign_train_ratio
        self.benign_val_ratio = benign_val_ratio
        self.benign_test_ratio = benign_test_ratio
        self.manifest_dir = Path(manifest_dir)
        self.models_dir = Path(models_dir)
        self.benign_test_pool_path = Path(benign_test_pool_path) if benign_test_pool_path is not None else None
        self.label_col = label_col

        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def generate_fold(
        self,
        df: pd.DataFrame,
        held_out_family: str,
        prevalence: float = 0.05
    ) -> Dict[str, Any]:
        """Generate one LOFO fold for held_out_family with specified test prevalence."""
        feature_cols = [c for c in df.columns if c != self.label_col]

        # 1. Split Benign flows for train and val (keeping training sizes unchanged)
        benign_all = df[df[self.label_col] == "Benign"]
        b_train, b_val, b_test_fallback = split_benign_flows(
            benign_all,
            train_ratio=self.benign_train_ratio,
            val_ratio=self.benign_val_ratio,
            test_ratio=self.benign_test_ratio,
            random_seed=self.random_seed
        )

        # Use 100k benign test pool if available and compatible to guarantee >=30 positives at 0.1% prevalence
        if self.benign_test_pool_path and self.benign_test_pool_path.exists():
            pool_100k = pd.read_parquet(self.benign_test_pool_path)
            if all(c in pool_100k.columns for c in feature_cols):
                # Ensure zero feature vector overlap with b_train and b_val
                train_val_tuples = set(b_train[feature_cols].itertuples(index=False, name=None)) | set(b_val[feature_cols].itertuples(index=False, name=None))
                pool_tuples = list(pool_100k[feature_cols].itertuples(index=False, name=None))
                valid_mask = [t not in train_val_tuples for t in pool_tuples]
                b_test = pool_100k[valid_mask].copy()
                b_test.index = range(len(df) + 1_000_000, len(df) + 1_000_000 + len(b_test))
            else:
                b_test = b_test_fallback.copy()
        else:
            b_test = b_test_fallback.copy()

        # 2. Partition other attack families between train (75%) and val (25%)
        other_attacks = df[(df[self.label_col] != "Benign") & (df[self.label_col] != held_out_family)]
        train_other_list = []
        val_other_list = []
        for fam, group in other_attacks.groupby(self.label_col):
            shuffled_g = group.sample(frac=1.0, random_state=self.random_seed)
            n_tr = int(np.round(len(shuffled_g) * 0.75))
            train_other_list.append(shuffled_g.iloc[:n_tr])
            val_other_list.append(shuffled_g.iloc[n_tr:])

        train_other = pd.concat(train_other_list, ignore_index=True) if train_other_list else pd.DataFrame(columns=df.columns)
        val_other = pd.concat(val_other_list, ignore_index=True) if val_other_list else pd.DataFrame(columns=df.columns)

        train_df = pd.concat([b_train, train_other], ignore_index=True).sample(frac=1.0, random_state=self.random_seed).reset_index(drop=True)
        val_df = pd.concat([b_val, val_other], ignore_index=True).sample(frac=1.0, random_state=self.random_seed).reset_index(drop=True)

        # 3. Test set with prevalence resampling (benign_test + held_out_family ONLY)
        family_test_raw = df[df[self.label_col] == held_out_family].copy()
        resample_res = resample_prevalence(
            benign_test=b_test,
            attack_test=family_test_raw,
            target_prevalence=prevalence,
            random_seed=self.random_seed
        )
        test_df = resample_res["test_df"]

        # 4. Assertions check
        verify_lofo_split_integrity(
            train=train_df,
            val=val_df,
            test=test_df,
            held_out_family=held_out_family,
            benign_train_idx=set(b_train.index),
            benign_val_idx=set(b_val.index),
            benign_test_idx=set(b_test.index),
            feature_cols=feature_cols,
            label_col=self.label_col
        )

        # 5. Fit scaler strictly on train only and persist
        scaler = StandardScaler()
        scaler.fit(train_df[feature_cols].to_numpy(dtype=np.float64))
        scaler_path = self.models_dir / f"scaler_lofo_{held_out_family}.joblib"
        joblib.dump(scaler, scaler_path)

        # 6. Compute SHA-256 hashes
        sha_train = compute_df_sha256(train_df)
        sha_val = compute_df_sha256(val_df)
        sha_test = compute_df_sha256(test_df)

        # 7. Assemble Manifest JSON
        manifest = {
            "fold_name": f"LOFO_{held_out_family}",
            "held_out_family": held_out_family,
            "target_prevalence": prevalence,
            "actual_prevalence": resample_res["actual_prevalence"],
            "subsampled_side": resample_res["subsampled_side"],
            "is_low_power": resample_res["is_low_power"],
            "random_seed": self.random_seed,
            "scaler_path": str(scaler_path),
            "split_row_counts": {
                "train": len(train_df),
                "val": len(val_df),
                "test": len(test_df)
            },
            "class_counts": {
                "train": train_df[self.label_col].value_counts().to_dict(),
                "val": val_df[self.label_col].value_counts().to_dict(),
                "test": test_df[self.label_col].value_counts().to_dict()
            },
            "split_sha256_checksums": {
                "train": sha_train,
                "val": sha_val,
                "test": sha_test
            },
            "multi_seed_runs": resample_res["multi_seed_runs"]
        }

        # Write manifest JSON to disk
        manifest_filename = f"lofo_{held_out_family}_p{int(prevalence * 1000):03d}_manifest.json"
        manifest_path = self.manifest_dir / manifest_filename
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"Manifest generated for LOFO {held_out_family} (prevalence {prevalence:.1%}) at {manifest_path}")
        return {
            "manifest": manifest,
            "manifest_path": manifest_path,
            "train": train_df,
            "val": val_df,
            "test": test_df,
            "scaler": scaler
        }

    def generate_all_folds(
        self,
        df: pd.DataFrame,
        families: List[str],
        prevalences: List[float] = [0.001, 0.01, 0.05, 0.10]
    ) -> Dict[str, Dict[float, Any]]:
        """Generate complete suite of LOFO folds across families and prevalence levels."""
        all_results = {}
        for fam in families:
            all_results[fam] = {}
            for p in prevalences:
                fold_res = self.generate_fold(df, held_out_family=fam, prevalence=p)
                all_results[fam][p] = fold_res
        return all_results


def main():
    """CLI runner to generate all LOFO folds on processed dataset."""
    from src.data.loader import load_config
    config = load_config()
    processed_path = Path(config["data"]["output_parquet"])
    
    if not processed_path.exists():
        print(f"File {processed_path} not found. Run pipeline first.")
        return

    df = pd.read_parquet(processed_path)
    families = config["data"]["active_attack_families"]
    engine = LOFOSplitEngine(random_seed=config["global_settings"]["random_seed"])

    print(f"\nGenerating LOFO folds for families: {families}")
    results = engine.generate_all_folds(df, families=families, prevalences=[0.001, 0.01, 0.05, 0.10])
    print(f"\nCompleted! Generated {len(families) * 4} manifests in results/manifests/")


if __name__ == "__main__":
    main()
