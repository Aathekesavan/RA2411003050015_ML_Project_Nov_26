"""UNSW-NB15 Dataset Adapter for SentinelX-Shift.

Adapts the UNSW-NB15 network intrusion dataset into the unified schema.
Family Groups:
- Recon_Analysis: Reconnaissance, Analysis (network probing / scanning)
- Exploit_Payload: Exploits, Shellcode, Backdoor, Worms (intrusion exploitation / payloads)
- Fuzzers: Fuzzers (protocol fuzzing / corruption)
- DoS: Denial of Service
- Generic: Generic attacks
"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import pandas as pd
import numpy as np

from src.data.adapters.base import DatasetAdapter


class UNSWNB15Adapter(DatasetAdapter):
    """Adapter for University of New South Wales NB15 network dataset."""

    FAMILY_GROUPS = {
        "Recon_Analysis": ["Reconnaissance", "Analysis"],
        "Exploit_Payload": ["Exploits", "Shellcode", "Backdoor", "Worms"],
        "Fuzzers": ["Fuzzers"],
        "DoS": ["DoS"],
        "Generic": ["Generic"],
    }

    IDENTIFIER_COLUMNS = [
        "id", "srcip", "dstip", "sport", "dsport", "stime", "ltime"
    ]

    CATEGORICAL_COLUMNS = ["proto", "service", "state"]

    def __init__(
        self,
        data_dir: Path = Path("data/raw/unsw_nb15"),
        processed_dir: Path = Path("data/processed/unsw_nb15"),
        max_rows: Optional[int] = 100_000,
        random_seed: int = 42
    ):
        super().__init__(name="UNSW-NB15", data_dir=data_dir, processed_dir=processed_dir)
        self.max_rows = max_rows
        self.random_seed = random_seed
        self.parquet_path = self.processed_dir / "unsw_nb15_cleaned.parquet"

    def is_available(self) -> bool:
        train_p = self.data_dir / "train.parquet"
        test_p = self.data_dir / "test.parquet"
        return train_p.exists() or test_p.exists() or len(list(self.data_dir.glob("*.csv"))) > 0

    def get_family_groups(self) -> Dict[str, List[str]]:
        return self.FAMILY_GROUPS

    def load(self) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series, Dict[str, Any]]:
        """Load and standardize UNSW-NB15 dataset."""
        train_p = self.data_dir / "train.parquet"
        test_p = self.data_dir / "test.parquet"

        dfs = []
        if train_p.exists():
            dfs.append(pd.read_parquet(train_p))
        if test_p.exists():
            dfs.append(pd.read_parquet(test_p))

        if not dfs:
            raise FileNotFoundError(f"No UNSW-NB15 parquet files found in {self.data_dir}")

        raw_df = pd.concat(dfs, ignore_index=True)

        # 1. Clean labels and families
        # attack_cat has the attack type; 'Normal' represents benign flows
        attack_cat = raw_df["attack_cat"].astype(str).str.strip()
        attack_cat = attack_cat.replace({
            "Normal": "Benign",
            "Backdoors": "Backdoor",
        })

        # Ensure label column matches
        if "label" in raw_df.columns:
            y_binary = raw_df["label"].astype(int)
        else:
            y_binary = (attack_cat != "Benign").astype(int)

        # 2. Map family groups
        fam_to_group = {}
        for group_name, members in self.FAMILY_GROUPS.items():
            for fam in members:
                fam_to_group[fam] = group_name

        family_group = attack_cat.map(
            lambda f: fam_to_group.get(f, "Benign" if f == "Benign" else "OtherAttack")
        )

        # 3. Drop identifier columns
        cols_to_drop = [c for c in self.IDENTIFIER_COLUMNS if c in raw_df.columns]
        cols_to_drop += ["attack_cat", "label"]
        features_df = raw_df.drop(columns=cols_to_drop, errors="ignore").copy()

        # 4. Clean categoricals (ordinal encoding with unknown handling)
        for cat_col in self.CATEGORICAL_COLUMNS:
            if cat_col in features_df.columns:
                features_df[cat_col] = features_df[cat_col].astype("category").cat.codes.astype(float)

        # 5. Clean non-finite values
        features_df = features_df.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        # 6. Deduplicate exact duplicate feature rows
        dedup_mask = ~features_df.duplicated()
        features_df = features_df[dedup_mask].reset_index(drop=True)
        y_binary = y_binary[dedup_mask].reset_index(drop=True)
        attack_cat = attack_cat[dedup_mask].reset_index(drop=True)
        family_group = family_group[dedup_mask].reset_index(drop=True)

        # 7. Subsample if total exceeds max_rows, preserving rare attack families
        if self.max_rows is not None and len(features_df) > self.max_rows:
            rng = np.random.RandomState(self.random_seed)
            # Retain all flows for rare families (< 5,000 flows)
            fam_counts = attack_cat.value_counts()
            rare_fams = fam_counts[fam_counts < 5000].index.tolist()

            rare_mask = attack_cat.isin(rare_fams)
            rare_indices = np.where(rare_mask)[0]

            if len(rare_indices) > self.max_rows:
                selected_idx = rng.choice(rare_indices, size=self.max_rows, replace=False)
            else:
                common_indices = np.where(~rare_mask)[0]
                n_common_to_sample = max(0, self.max_rows - len(rare_indices))
                sampled_common = rng.choice(common_indices, size=min(n_common_to_sample, len(common_indices)), replace=False)
                selected_idx = np.concatenate([rare_indices, sampled_common])

            selected_idx = np.sort(selected_idx)
            features_df = features_df.iloc[selected_idx].reset_index(drop=True)
            y_binary = y_binary.iloc[selected_idx].reset_index(drop=True)
            attack_cat = attack_cat.iloc[selected_idx].reset_index(drop=True)
            family_group = family_group.iloc[selected_idx].reset_index(drop=True)

        data_card = {
            "dataset_name": self.name,
            "total_flows": len(features_df),
            "features_count": len(features_df.columns),
            "benign_count": int((y_binary == 0).sum()),
            "attack_count": int((y_binary == 1).sum()),
            "family_counts": attack_cat.value_counts().to_dict(),
            "family_group_counts": family_group.value_counts().to_dict(),
        }

        # Cache cleaned dataset
        unified = self.build_unified_dataframe(features_df, y_binary, attack_cat, family_group)
        unified.to_parquet(self.parquet_path, index=False)

        return features_df, y_binary, attack_cat, family_group, data_card
