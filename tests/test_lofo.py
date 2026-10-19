"""Unit tests for SentinelX-Shift LOFO split engine (src/eval/lofo.py)."""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import json

from src.eval.lofo import (
    split_benign_flows,
    resample_prevalence,
    verify_lofo_split_integrity,
    LOFOSplitEngine,
    compute_df_sha256,
)


@pytest.fixture
def synthetic_ids_df():
    """Create a synthetic dataset mirroring CIC-IDS2017 structure."""
    np.random.seed(42)
    n_benign = 600
    n_dos = 150
    n_portscan = 80
    n_bruteforce = 50

    total = n_benign + n_dos + n_portscan + n_bruteforce
    # Generate unique distinct feature vectors
    base = np.arange(total * 4, dtype=float).reshape(total, 4)

    labels = (
        ["Benign"] * n_benign +
        ["DoS"] * n_dos +
        ["PortScan"] * n_portscan +
        ["BruteForce"] * n_bruteforce
    )

    df = pd.DataFrame(base, columns=["f1", "f2", "f3", "f4"])
    df["Label"] = labels
    return df


class TestLOFOSplitEngine:

    def test_lofo_normal_case_passes(self, synthetic_ids_df, tmp_path):
        """Verify normal LOFO split executes cleanly and satisfies all strict assertions."""
        engine = LOFOSplitEngine(
            random_seed=42,
            benign_train_ratio=0.6,
            benign_val_ratio=0.2,
            benign_test_ratio=0.2,
            manifest_dir=tmp_path / "manifests",
            models_dir=tmp_path / "models",
        )

        for fam in ["DoS", "PortScan", "BruteForce"]:
            res = engine.generate_fold(synthetic_ids_df, held_out_family=fam, prevalence=0.05)
            
            train = res["train"]
            val = res["val"]
            test = res["test"]
            manifest = res["manifest"]

            # Assertions on split contents
            assert fam not in train["Label"].values
            assert fam not in val["Label"].values
            assert set(test["Label"].unique()).issubset({"Benign", fam})
            assert fam in test["Label"].values

            # Verify manifest
            assert manifest["held_out_family"] == fam
            assert Path(res["manifest_path"]).exists()
            assert len(manifest["split_sha256_checksums"]["train"]) == 64
            assert len(manifest["split_sha256_checksums"]["val"]) == 64
            assert len(manifest["split_sha256_checksums"]["test"]) == 64

    def test_lofo_assertion_fails_when_f_in_train(self, synthetic_ids_df):
        """Verify engine raises AssertionError when held-out family F is leaked into train."""
        engine = LOFOSplitEngine(random_seed=42)
        held_out = "PortScan"
        b_train, b_val, b_test = split_benign_flows(synthetic_ids_df[synthetic_ids_df["Label"] == "Benign"])

        # Intentionally leak PortScan into train
        leaked_train = pd.concat([b_train, synthetic_ids_df[synthetic_ids_df["Label"] == held_out]], ignore_index=True)
        val = b_val
        test = pd.concat([b_test, synthetic_ids_df[synthetic_ids_df["Label"] == held_out]], ignore_index=True)

        with pytest.raises(AssertionError, match=f"Leakage: held-out family '{held_out}' is present in train split!"):
            verify_lofo_split_integrity(
                train=leaked_train,
                val=val,
                test=test,
                held_out_family=held_out,
                benign_train_idx=set(b_train.index),
                benign_val_idx=set(b_val.index),
                benign_test_idx=set(b_test.index),
                feature_cols=["f1", "f2", "f3", "f4"]
            )

    def test_lofo_assertion_fails_when_f_in_val(self, synthetic_ids_df):
        """Verify engine raises AssertionError when held-out family F is leaked into val."""
        held_out = "DoS"
        b_train, b_val, b_test = split_benign_flows(synthetic_ids_df[synthetic_ids_df["Label"] == "Benign"])

        train = b_train
        # Intentionally leak DoS into val
        leaked_val = pd.concat([b_val, synthetic_ids_df[synthetic_ids_df["Label"] == held_out]], ignore_index=True)
        test = pd.concat([b_test, synthetic_ids_df[synthetic_ids_df["Label"] == held_out]], ignore_index=True)

        with pytest.raises(AssertionError, match=f"Leakage: held-out family '{held_out}' is present in val split!"):
            verify_lofo_split_integrity(
                train=train,
                val=leaked_val,
                test=test,
                held_out_family=held_out,
                benign_train_idx=set(b_train.index),
                benign_val_idx=set(b_val.index),
                benign_test_idx=set(b_test.index),
                feature_cols=["f1", "f2", "f3", "f4"]
            )

    def test_lofo_assertion_fails_on_duplicate_rows_across_splits(self, synthetic_ids_df):
        """Verify engine raises AssertionError when identical rows exist across splits."""
        held_out = "BruteForce"
        b_train, b_val, b_test = split_benign_flows(synthetic_ids_df[synthetic_ids_df["Label"] == "Benign"])

        train = b_train.copy()
        val = b_val.copy()
        # Deliberately clone the first row of train into test
        cloned_row = train.iloc[[0]].copy()
        test = pd.concat([b_test, cloned_row], ignore_index=True)

        with pytest.raises(AssertionError, match="Duplicate feature vectors found between train and test splits!"):
            verify_lofo_split_integrity(
                train=train,
                val=val,
                test=test,
                held_out_family=held_out,
                benign_train_idx=set(b_train.index),
                benign_val_idx=set(b_val.index),
                benign_test_idx=set(b_test.index),
                feature_cols=["f1", "f2", "f3", "f4"]
            )

    def test_lofo_assertion_fails_on_benign_index_overlap(self, synthetic_ids_df):
        """Verify engine raises AssertionError if benign index partitions overlap."""
        held_out = "DoS"
        b_train, b_val, b_test = split_benign_flows(synthetic_ids_df[synthetic_ids_df["Label"] == "Benign"])

        # Inject deliberate index overlap between train and test
        overlapping_idx = set(b_train.index) | {list(b_train.index)[0]}

        with pytest.raises(AssertionError, match="Benign row index overlap detected"):
            verify_lofo_split_integrity(
                train=b_train,
                val=b_val,
                test=b_test,
                held_out_family=held_out,
                benign_train_idx=overlapping_idx,
                benign_val_idx=set(b_val.index),
                benign_test_idx=set(b_train.index[:1]),  # Overlapping index
                feature_cols=["f1", "f2", "f3", "f4"]
            )

    def test_prevalence_resampling_attack_and_benign_sides(self):
        """Verify prevalence resampling logic correctly subsamples attack or benign side."""
        benign_test = pd.DataFrame({"f1": range(1000), "Label": ["Benign"] * 1000})
        # 1. Attack plentiful (1000 attacks vs 1000 benign, target p = 0.05)
        # N_att_needed = 1000 * (0.05 / 0.95) = ~53 attacks (< 1000 available)
        plentiful_attacks = pd.DataFrame({"f1": range(1000), "Label": ["DoS"] * 1000})
        res1 = resample_prevalence(benign_test, plentiful_attacks, target_prevalence=0.05, random_seed=42)
        assert res1["subsampled_side"] == "attack"
        assert res1["n_benign"] == 1000
        assert np.isclose(res1["actual_prevalence"], 0.05, atol=0.005)
        assert res1["is_low_power"] is False

        # 2. Attack scarce / low-power (10 attacks vs 1000 benign, target p = 0.05)
        # Positives = 10 < 30 -> low-power must be True with 20 multi-seed draws
        scarce_attacks = pd.DataFrame({"f1": range(10), "Label": ["PortScan"] * 10})
        res2 = resample_prevalence(benign_test, scarce_attacks, target_prevalence=0.05, random_seed=42)
        assert res2["subsampled_side"] == "benign"
        assert res2["n_attack"] == 10
        assert res2["is_low_power"] is True
        assert len(res2["multi_seed_runs"]) == 20
