"""CIC-IDS2017 Dataset Adapter for SentinelX-Shift.

Adapts CIC-IDS2017 flow data into the unified schema.
Family Groups:
- DoS_DDoS: DoS, DDoS
- BruteForce: FTP-Patator, SSH-Patator (BruteForce)
- PortScan: PortScan
- Bot: Bot
- WebAttack: WebAttack (Brute Force, XSS, Sql Injection)
"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import pandas as pd
import numpy as np

from src.data.adapters.base import DatasetAdapter


class CICIDS2017Adapter(DatasetAdapter):
    """Adapter for Canadian Institute for Cybersecurity IDS 2017 dataset."""

    FAMILY_GROUPS = {
        "DoS_DDoS": ["DoS", "DDoS"],
        "BruteForce": ["BruteForce"],
        "PortScan": ["PortScan"],
        "Bot": ["Bot"],
        "WebAttack": ["WebAttack"],
    }

    def __init__(
        self,
        data_dir: Path = Path("data/raw"),
        processed_dir: Path = Path("data/processed"),
        sample_path: Path = Path("data/processed/cicids2017_sample60k.parquet")
    ):
        super().__init__(name="CIC-IDS2017", data_dir=data_dir, processed_dir=processed_dir)
        self.sample_path = Path(sample_path)

    def is_available(self) -> bool:
        if self.sample_path.exists():
            return True
        return len(list(self.data_dir.glob("*ISCX*.csv*"))) > 0

    def get_family_groups(self) -> Dict[str, List[str]]:
        return self.FAMILY_GROUPS

    def load(self) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series, Dict[str, Any]]:
        """Load CIC-IDS2017 dataset, mapping labels to families and family groups."""
        if self.sample_path.exists():
            df = pd.read_parquet(self.sample_path)
        else:
            raise FileNotFoundError(f"Processed CIC-IDS2017 dataset not found at {self.sample_path}")

        family_series = df["Label"].copy()
        y_binary = (family_series != "Benign").astype(int)

        # Map each family to its family group
        fam_to_group = {}
        for group_name, members in self.FAMILY_GROUPS.items():
            for fam in members:
                fam_to_group[fam] = group_name

        family_group = family_series.map(lambda f: fam_to_group.get(f, "Benign" if f == "Benign" else "OtherAttack"))

        feature_cols = [c for c in df.columns if c not in ["Label", "y_binary", "Family_Group"]]
        features_df = df[feature_cols].copy()

        # Data card metadata
        counts = family_series.value_counts().to_dict()
        group_counts = family_group.value_counts().to_dict()
        data_card = {
            "dataset_name": self.name,
            "total_flows": len(df),
            "features_count": len(feature_cols),
            "benign_count": int((y_binary == 0).sum()),
            "attack_count": int((y_binary == 1).sum()),
            "family_counts": counts,
            "family_group_counts": group_counts,
        }

        return features_df, y_binary, family_series, family_group, data_card
