"""CSE-CIC-IDS2018 Dataset Adapter for SentinelX-Shift.

Provides streaming and chunked loading for the large-scale CSE-CIC-IDS2018 dataset,
capping at 500,000 deduplicated rows. Skips gracefully if files are absent.
"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import pandas as pd
import numpy as np

from src.data.adapters.base import DatasetAdapter
from src.data.loader import clean_column_names, drop_leaky_columns, map_labels
from src.data.cleaner import clean_numeric_features, remove_exact_duplicates


class CICIDS2018Adapter(DatasetAdapter):
    """Adapter for AWS-hosted CSE-CIC-IDS2018 dataset."""

    FAMILY_GROUPS = {
        "DoS_DDoS": ["DoS", "DDoS"],
        "BruteForce": ["BruteForce"],
        "PortScan": ["PortScan"],
        "Bot": ["Bot"],
        "Infiltration": ["Infiltration"],
        "WebAttack": ["WebAttack"],
    }

    def __init__(
        self,
        data_dir: Path = Path("data/raw/cicids2018"),
        processed_dir: Path = Path("data/processed/cicids2018"),
        max_rows: int = 500_000
    ):
        super().__init__(name="CSE-CIC-IDS2018", data_dir=data_dir, processed_dir=processed_dir)
        self.max_rows = max_rows

    def is_available(self) -> bool:
        if not self.data_dir.exists():
            return False
        files = list(self.data_dir.glob("*.csv")) + list(self.data_dir.glob("*.parquet"))
        return len(files) > 0

    def get_family_groups(self) -> Dict[str, List[str]]:
        return self.FAMILY_GROUPS

    def load(self) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series, Dict[str, Any]]:
        """Stream and standardize CSE-CIC-IDS2018 chunks up to max_rows."""
        if not self.is_available():
            raise FileNotFoundError(
                f"CSE-CIC-IDS2018 raw files not found in {self.data_dir}. "
                "Download CSE-CIC-IDS2018 CSV/parquet files into data/raw/cicids2018/ to enable this adapter."
            )

        csv_files = list(self.data_dir.glob("*.csv"))
        parquet_files = list(self.data_dir.glob("*.parquet"))

        collected_dfs = []
        total_rows = 0

        if parquet_files:
            for pf in parquet_files:
                cdf = pd.read_parquet(pf)
                collected_dfs.append(cdf)
                total_rows += len(cdf)
                if total_rows >= self.max_rows:
                    break
        elif csv_files:
            # Chunked streaming reader to avoid out-of-memory errors
            for cf in csv_files:
                for chunk in pd.read_csv(cf, chunksize=50_000, low_memory=False):
                    clean_chunk = clean_column_names(chunk)
                    collected_dfs.append(clean_chunk)
                    total_rows += len(clean_chunk)
                    if total_rows >= self.max_rows:
                        break
                if total_rows >= self.max_rows:
                    break

        df = pd.concat(collected_dfs, ignore_index=True)
        df = clean_column_names(df)
        df, _ = clean_numeric_features(df)
        df = drop_leaky_columns(df)
        df["Label"] = map_labels(df["Label"])

        # Deduplicate
        features_sub = df.drop(columns=["Label"], errors="ignore")
        dedup_mask = ~features_sub.duplicated()
        df = df[dedup_mask].iloc[:self.max_rows].reset_index(drop=True)

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
