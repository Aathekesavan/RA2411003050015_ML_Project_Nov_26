"""Data loader for CIC-IDS2017 dataset.

================================================================================
KNOWN CIC-IDS2017 DATASET ISSUES AND MITIGATION NOTES:
1. Label Encoding Corruption:
   - Several CSV files contain non-standard encoding artifacts in attack names.
     Specifically, 'Web Attack \ufffd Brute Force', 'Web Attack \ufffd XSS', and
     'Web Attack \ufffd Sql Injection' use the Unicode replacement character
     or Windows-1252 byte sequences (e.g., 0x96). We sanitize these to canonical
     family names (e.g., 'WebAttack').
2. Identity and Port Leakage:
   - Features like 'Destination Port', 'Source Port', 'Flow ID', IP addresses,
     and 'Timestamp' allow classifiers to trivially achieve >99.9% accuracy by
     memorizing specific ports (e.g. port 21 for FTP-Patator, port 22 for SSH-Patator,
     port 80 for DoS/DDoS) rather than learning generalized flow dynamics. We
     strictly strip these columns.
3. Duplicated Columns and Header Inconsistencies:
   - The CSV headers in some files contain duplicate columns (such as
     'Fwd Header Length' appearing twice as 'Fwd Header Length.1' or
     'Fwd Header Length_duplicated_0') and leading/trailing whitespace. All
     whitespace is stripped and duplicates dropped.
4. Infinite and Missing Values:
   - Flow metrics like 'Flow Bytes/s' and 'Flow Packets/s' have division-by-zero
     generating 'Infinity', '-Infinity', or NaN. These are coerced and sanitized.
5. Infiltration Class Rarity:
   - Infiltration only has 36 positive instances in the entire 2.8M row dataset,
     making standard stratified evaluation problematic.
6. Extreme Cross-Split Duplication (Leakage):
   - In standard random k-fold splits, 93% to 99.5% of "unseen" attack test
     positives have identical or near-identical flow signatures in the training set
     due to repetitive packet generator loops. Leave-One-Attack-Family-Out (LOFO)
     and rigorous flow deduplication are mandatory to prevent synthetic over-optimism.
================================================================================
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import logging
import pandas as pd
import numpy as np
import yaml

logger = logging.getLogger(__name__)

# Default canonical family mappings
CANONICAL_FAMILIES: Dict[str, str] = {
    # Benign
    "BENIGN": "Benign",
    "benign": "Benign",
    # DoS
    "DoS Hulk": "DoS",
    "DoS GoldenEye": "DoS",
    "DoS slowloris": "DoS",
    "DoS Slowhttptest": "DoS",
    "Heartbleed": "DoS",
    # PortScan
    "PortScan": "PortScan",
    # Brute Force
    "FTP-Patator": "BruteForce",
    "SSH-Patator": "BruteForce",
    # DDoS
    "DDoS": "DDoS",
    # Bot
    "Bot": "Bot",
    # Web Attacks
    "Web Attack \ufffd Brute Force": "WebAttack",
    "Web Attack – Brute Force": "WebAttack",
    "Web Attack - Brute Force": "WebAttack",
    "Web Attack \ufffd XSS": "WebAttack",
    "Web Attack – XSS": "WebAttack",
    "Web Attack - XSS": "WebAttack",
    "Web Attack \ufffd Sql Injection": "WebAttack",
    "Web Attack – Sql Injection": "WebAttack",
    "Web Attack - Sql Injection": "WebAttack",
    # Infiltration
    "Infiltration": "Infiltration",
}

DEFAULT_LEAKY_COLUMNS: List[str] = [
    "Flow ID",
    "Source IP",
    "Source Port",
    "Destination IP",
    "Destination Port",
    "Timestamp",
    "Fwd Header Length.1",
    "Fwd Header Length_duplicated_0",
    "Unnamed: 0",
]


def load_config(config_path: Union[str, Path] = "configs/config.yaml") -> dict:
    """Load the project configuration from YAML."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace, remove weird characters, and drop duplicate column names."""
    df = df.copy()
    # Strip whitespace from column headers
    df.columns = [str(c).strip() for c in df.columns]

    # Deduplicate columns if any repeated names exist
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    return df


def map_labels(
    series: pd.Series,
    custom_mapping: Optional[Dict[str, str]] = None
) -> pd.Series:
    """Map raw CIC-IDS2017 labels to canonical attack families.
    
    Any unrecognized label with 'dos' in name is mapped to DoS,
    'portscan' to PortScan, 'patator' to BruteForce, etc.
    """
    mapping = custom_mapping or CANONICAL_FAMILIES
    
    def _map_single_label(val: str) -> str:
        s = str(val).strip()
        if s in mapping:
            return mapping[s]
        
        # Fuzzy fallback based on substrings
        s_lower = s.lower()
        if "benign" in s_lower:
            return "Benign"
        if "hulk" in s_lower or "goldeneye" in s_lower or "slow" in s_lower or "heartbleed" in s_lower or "dos" in s_lower:
            if "ddos" in s_lower:
                return "DDoS"
            return "DoS"
        if "portscan" in s_lower or "port scan" in s_lower:
            return "PortScan"
        if "patator" in s_lower or "brute" in s_lower:
            return "BruteForce"
        if "ddos" in s_lower:
            return "DDoS"
        if "bot" in s_lower:
            return "Bot"
        if "web attack" in s_lower:
            return "WebAttack"
        if "infil" in s_lower:
            return "Infiltration"
        return s  # Return as is if unmatched

    return series.apply(_map_single_label)


def drop_leaky_columns(
    df: pd.DataFrame,
    leaky_cols: Optional[List[str]] = None
) -> pd.DataFrame:
    """Drop identity and leaky columns (IPs, Ports, Timestamps, Flow IDs)."""
    cols_to_drop = leaky_cols if leaky_cols is not None else DEFAULT_LEAKY_COLUMNS
    existing_to_drop = [c for c in cols_to_drop if c in df.columns]
    if existing_to_drop:
        df = df.drop(columns=existing_to_drop)
    return df


def load_raw_file(
    file_path: Union[str, Path],
    leaky_cols: Optional[List[str]] = None,
    label_mapping: Optional[Dict[str, str]] = None,
    sample_fraction: Optional[float] = None,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Load a single raw CSV or Parquet file, clean columns, map labels, drop leaky cols."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    logger.info(f"Loading {path.name}...")
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix == ".csv":
        # Handle potential encoding issues with latin1 / utf-8
        try:
            df = pd.read_csv(path, encoding="utf-8", low_memory=False)
        except UnicodeDecodeError:
            df = pd.read_csv(path, encoding="latin1", low_memory=False)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")

    # Standardize column names
    df = clean_column_names(df)

    # Standardize label column name to 'Label'
    label_col = None
    for candidate in ["Label", "label", " Label", "Label "]:
        if candidate in df.columns:
            label_col = candidate
            break
    if label_col and label_col != "Label":
        df = df.rename(columns={label_col: "Label"})
    elif not label_col:
        raise KeyError("Could not find 'Label' column in dataframe")

    # Map labels to canonical attack families
    df["Label"] = map_labels(df["Label"], label_mapping)

    # Drop leaky columns
    df = drop_leaky_columns(df, leaky_cols)

    # Optional subsample at load time
    if sample_fraction is not None and 0.0 < sample_fraction < 1.0:
        df = df.sample(frac=sample_fraction, random_state=random_seed)

    return df
