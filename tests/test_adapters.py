"""Unit tests for SentinelX-Shift Multi-Dataset Adapters.

Tests:
1. Unified schema compliance: (features_df, y_binary, family, family_group, data_card).
2. Absence of identifier / leaky columns across all adapters.
3. Proper categorical encoding and absence of inf/NaN values.
4. Family grouping logic and rare-family preservation.
5. Graceful handling of missing files for uninstalled datasets.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile

from src.data.adapters.base import DatasetAdapter
from src.data.adapters.cicids2017 import CICIDS2017Adapter
from src.data.adapters.unswnb15 import UNSWNB15Adapter
from src.data.adapters.lycos2017 import LYCOS2017Adapter
from src.data.adapters.cicids2018 import CICIDS2018Adapter


def test_cicids2017_adapter_schema():
    """Verify CICIDS2017Adapter returns valid unified schema and metadata."""
    adapter = CICIDS2017Adapter()
    if not adapter.is_available():
        pytest.skip("CIC-IDS2017 processed sample parquet not found on disk")

    features_df, y_binary, family, family_group, data_card = adapter.load()

    assert len(features_df) == len(y_binary) == len(family) == len(family_group)
    assert set(y_binary.unique()).issubset({0, 1})
    assert "Benign" in family.values
    assert "DoS_DDoS" in family_group.values or "PortScan" in family_group.values

    # Check data card
    assert data_card["dataset_name"] == "CIC-IDS2017"
    assert data_card["total_flows"] == len(features_df)
    assert data_card["features_count"] == len(features_df.columns)
    assert data_card["benign_count"] + data_card["attack_count"] == len(features_df)

    # Assert no non-finite values
    assert np.all(np.isfinite(features_df.to_numpy()))


def test_unsw_nb15_adapter_schema():
    """Verify UNSWNB15Adapter loads, standardizes, encodes, and deduplicates cleanly."""
    adapter = UNSWNB15Adapter(max_rows=1000)
    if not adapter.is_available():
        pytest.skip("UNSW-NB15 raw parquets not found on disk")

    features_df, y_binary, family, family_group, data_card = adapter.load()

    assert len(features_df) <= 1000
    assert len(features_df) == len(y_binary) == len(family) == len(family_group)

    # Zero identifiers
    leaky_cols = {"id", "srcip", "dstip", "sport", "dsport", "stime", "ltime"}
    assert not any(c in features_df.columns for c in leaky_cols)

    # All numeric, finite
    assert np.all(np.isfinite(features_df.to_numpy()))

    # Check family group mappings
    groups = adapter.get_family_groups()
    assert "Recon_Analysis" in groups
    assert "Exploit_Payload" in groups
    assert "Fuzzers" in groups
    assert "DoS" in groups
    assert "Generic" in groups

    # Check data card
    assert data_card["dataset_name"] == "UNSW-NB15"
    assert "family_counts" in data_card
    assert "family_group_counts" in data_card


def test_missing_dataset_graceful_handling():
    """Verify adapters for uninstalled datasets report is_available=False and raise FileNotFoundError on load."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        empty_path = Path(tmp_dir) / "empty_dir"
        empty_path.mkdir()

        # LYCOS-IDS2017
        lycos = LYCOS2017Adapter(data_dir=empty_path)
        assert not lycos.is_available()
        with pytest.raises(FileNotFoundError):
            lycos.load()

        # CSE-CIC-IDS2018
        cic2018 = CICIDS2018Adapter(data_dir=empty_path)
        assert not cic2018.is_available()
        with pytest.raises(FileNotFoundError):
            cic2018.load()


def test_no_group_is_split_across_train_and_test():
    """Verify that in group-level LOFO, no family group is split across train and test splits."""
    from src.eval.lofo import LOFOSplitEngine

    # Test with UNSW-NB15 adapter (sample 2000 rows for fast testing)
    adapter = UNSWNB15Adapter(max_rows=2000, random_seed=42)
    if not adapter.is_available():
        pytest.skip("UNSW-NB15 raw parquets not found on disk")

    features_df, y_binary, family_series, family_group, data_card = adapter.load()
    df = features_df.copy()
    df["Label"] = family_group.values

    groups = [g for g in family_group.unique() if g not in ["Benign", "OtherAttack"]]
    assert len(groups) >= 3, f"Expected at least 3 groups, found {len(groups)}"

    engine = LOFOSplitEngine(random_seed=42, benign_test_pool_path=None)

    for grp in groups:
        # Check if group has enough flows in this small sample
        n_grp = (df["Label"] == grp).sum()
        if n_grp < 10:
            continue
        fold = engine.generate_fold(df, held_out_family=grp, prevalence=0.05)
        train_df = fold["train"]
        val_df = fold["val"]
        test_df = fold["test"]

        train_attack_groups = set(train_df[train_df["Label"] != "Benign"]["Label"].unique())
        val_attack_groups = set(val_df[val_df["Label"] != "Benign"]["Label"].unique())
        test_attack_groups = set(test_df[test_df["Label"] != "Benign"]["Label"].unique())

        # 1. Held-out group grp must NEVER appear in train or val
        assert grp not in train_attack_groups, f"Group {grp} leaked into train split!"
        assert grp not in val_attack_groups, f"Group {grp} leaked into val split!"

        # 2. Test attack flows must belong strictly to grp
        assert test_attack_groups == {grp}, f"Test attacks contain unauthorized groups: {test_attack_groups}"

        # 3. Disjoint group sets: intersection between train and test attack groups is strictly empty
        assert len(train_attack_groups & test_attack_groups) == 0, f"Train and test groups overlap: {train_attack_groups & test_attack_groups}"

