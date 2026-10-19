"""Abstract Dataset Adapter for SentinelX-Shift Multi-Dataset Support.

Standardizes heterogeneous intrusion datasets into a unified schema:
- features_df: DataFrame of numeric, non-leaky flow features
- y_binary: Series of binary intrusion indicators (0 = Benign, 1 = Attack)
- family: Series of specific attack family labels (e.g. DoS, PortScan, Exploits)
- family_group: Series of grouped attack families held out jointly
- data_card: Dictionary containing dataset provenance, class balance, and schema metadata
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import pandas as pd
import numpy as np


class DatasetAdapter(ABC):
    """Abstract base class for network intrusion dataset adapters."""

    def __init__(self, name: str, data_dir: Path, processed_dir: Path):
        self.name = name
        self.data_dir = Path(data_dir)
        self.processed_dir = Path(processed_dir)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the raw data files for this dataset exist on disk."""
        pass

    @abstractmethod
    def get_family_groups(self) -> Dict[str, List[str]]:
        """Return the mapping from family group name to list of attack families."""
        pass

    @abstractmethod
    def load(self) -> Tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series, Dict[str, Any]]:
        """Load, clean, and standardize the dataset into the unified schema.

        Returns:
            features_df: Cleaned numeric features (no IP, port, timestamp, ID).
            y_binary: Binary labels (0 = Benign, 1 = Attack).
            family: Fine-grained attack family name (or 'Benign').
            family_group: Coarser family group for joint leave-out evaluation.
            data_card: Metadata dictionary detailing flow counts, class ratios, and columns.
        """
        pass

    def build_unified_dataframe(
        self,
        features_df: pd.DataFrame,
        y_binary: pd.Series,
        family: pd.Series,
        family_group: pd.Series
    ) -> pd.DataFrame:
        """Combine components into a single DataFrame with canonical metadata columns."""
        df = features_df.copy()
        df["y_binary"] = y_binary.values
        df["Label"] = family.values
        df["Family_Group"] = family_group.values
        return df
