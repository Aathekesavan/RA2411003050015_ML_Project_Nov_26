"""LYCOS-IDS2017 Dataset Adapter for SentinelX-Shift.

Adapts the LYCOS-IDS2017 revised dataset (addressing CIC-IDS2017 labeling bugs)
into the unified schema. If files are not present on disk, gracefully reports availability.
"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import pandas as pd
import numpy as np

from src.data.adapters.base import DatasetAdapter
from src.data.loader import clean_column_names, drop_leaky_columns, map_labels
from src.data.cleaner import clean_numeric_features, remove_exact_duplicates


class LYCOS2017Adapter(DatasetAdapter):
    """Adapter for LYCOS-IDS2017 dataset."""

    FAMILY_GROUPS = {
        "DoS_DDoS": ["DoS", "DDoS"],
        "BruteForce": ["BruteForce"],
        "PortScan": ["PortScan"],
        "Bot": ["Bot"],
        "WebAttack": ["WebAttack"],
    }

    def __init__(
        self,
        data_dir: Path = Path("data/raw/lycos2017"),
        processed_dir: Path = Path("data/processed/lycos2017")
    ):
        super().__init__(name="LYCOS-IDS2017", data_dir=data_dir, processed_dir=processed_dir)

    def is_available(self) -> bool:
        if not self.data_dir.exists():
            return False
        files = list(self.data_dir.glob("*.csv")) + list(self.data_dir.glob("*.parquet"))
        return len(files) > 0

    def get_family_groups(self) -> Dict[str, List[str]]:
        return self.FAMILY_GROUPS

    def load(self) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series, Dict[str, Any]]:
        """Load and clean LYCOS-IDS2017 files if present."""
        if not self.is_available():
            raise FileNotFoundError(
                f"LYCOS-IDS2017 raw files not found in {self.data_dir}. "
                "Download the LYCOS-IDS2017 CSV/parquet archives into data/raw/lycos2017/ to enable this adapter."
            )

        files = list(self.data_dir.glob("*.parquet")) or list(self.data_dir.glob("*.csv"))
        dfs = []
        for f in files:
            if f.suffix == ".parquet":
                dfs.append(pd.read_parquet(f))
            else:
                dfs.append(pd.read_csv(f, low_memory=False))

        df = pd.concat(dfs, ignore_index=True)
        df = clean_column_names(df)
        df, _ = clean_numeric_features(df)
        df = drop_leaky_columns(df)
        df["Label"] = map_labels(df["Label"])

        family_series = df["Label"].copy()
        y_binary = (family_series != "Benign").astype(int)

        fam_to_group = {}
        for group_name, members in self.FAMILY_GROUPS.items():
            for fam in members:
                fam_to_group[fam] = group_name

        family_group = family_series.map(
            lambda f: fam_to_group.get(f, "Benign" if f == "Benign" else "OtherAttack")
        )

        feature_cols = [c for c in df.columns if c not in ["Label", "y_binary", "Family_Group"]]
        features_df = df[feature_cols].copy()

        data_card = {
            "dataset_name": self.name,
            "total_flows": len(df),
            "features_count": len(feature_cols),
            "benign_count": int((y_binary == 0).sum()),
            "attack_count": int((y_binary == 1).sum()),
            "family_counts": family_series.value_counts().to_dict(),
            "family_group_counts": family_group.value_counts().to_dict(),
        }

        return features_df, y_binary, family_series, family_group, data_card
