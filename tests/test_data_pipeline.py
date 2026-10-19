"""Unit tests for SentinelX-Shift data pipeline, deduplication, and leakage audit."""

import pytest
import pandas as pd
import numpy as np

from src.data.loader import (
    clean_column_names,
    map_labels,
    drop_leaky_columns,
    DEFAULT_LEAKY_COLUMNS,
)
from src.data.cleaner import (
    clean_numeric_features,
    remove_exact_duplicates,
    stratified_subsample,
    preserve_rare_families_sample,
)
from src.data.audit import (
    audit_family_leakage,
    run_leakage_contrast_audit,
)


class TestColumnCleaningAndMapping:
    def test_clean_column_names_strips_whitespace(self):
        df = pd.DataFrame({
            " Destination Port ": [80, 443],
            "Flow Duration": [1000, 2000],
            " Label ": ["BENIGN", "DoS Hulk"]
        })
        cleaned = clean_column_names(df)
        assert list(cleaned.columns) == ["Destination Port", "Flow Duration", "Label"]

    def test_clean_column_names_deduplicates_headers(self):
        df = pd.DataFrame([[1, 2, 3]], columns=["Fwd Header Length", "Fwd Header Length", "Flow Duration"])
        cleaned = clean_column_names(df)
        assert cleaned.shape[1] == 2
        assert list(cleaned.columns) == ["Fwd Header Length", "Flow Duration"]

    def test_label_mapping_canonical_families(self):
        raw_labels = pd.Series([
            "BENIGN",
            "DoS Hulk",
            "DoS GoldenEye",
            "DoS slowloris",
            "Heartbleed",
            "PortScan",
            "FTP-Patator",
            "SSH-Patator",
            "DDoS",
            "Web Attack \ufffd Brute Force",
            "Infiltration",
        ])
        mapped = map_labels(raw_labels)
        expected = [
            "Benign",
            "DoS",
            "DoS",
            "DoS",
            "DoS",
            "PortScan",
            "BruteForce",
            "BruteForce",
            "DDoS",
            "WebAttack",
            "Infiltration",
        ]
        assert list(mapped) == expected

    def test_drop_leaky_columns(self):
        df = pd.DataFrame({
            "Flow ID": ["flow_1"],
            "Source IP": ["192.168.1.1"],
            "Destination Port": [80],
            "Timestamp": ["2017-07-07 10:00:00"],
            "Total Fwd Packets": [15],
            "Label": ["Benign"]
        })
        cleaned = drop_leaky_columns(df)
        assert "Destination Port" not in cleaned.columns
        assert "Flow ID" not in cleaned.columns
        assert "Total Fwd Packets" in cleaned.columns
        assert "Label" in cleaned.columns


class TestDataCleanerAndDeduplication:
    def test_clean_numeric_features_inf_nan(self):
        df = pd.DataFrame({
            "Flow Bytes/s": [100.0, np.inf, 250.0, -np.inf, np.nan],
            "Flow Packets/s": [10.0, 20.0, 30.0, 40.0, 50.0],
            "Label": ["Benign", "DoS", "PortScan", "BruteForce", "Benign"]
        })
        cleaned, stats = clean_numeric_features(df, drop_na=True)
        assert stats["inf_values_detected"] == 2
        assert stats["nan_rows_dropped"] == 3
        assert len(cleaned) == 2
        assert not np.isinf(cleaned["Flow Bytes/s"].to_numpy()).any()
        assert not cleaned["Flow Bytes/s"].isna().any()

    def test_remove_exact_duplicates(self):
        """Verify exact identical flow feature vectors are completely purged."""
        unique_data = pd.DataFrame({
            "feat1": [1.0, 2.0, 3.0, 4.0, 5.0],
            "feat2": [10.0, 20.0, 30.0, 40.0, 50.0],
            "Label": ["Benign", "DoS", "DoS", "PortScan", "BruteForce"]
        })
        # Duplicate the entire dataset twice (total 15 rows, 5 unique)
        duplicate_df = pd.concat([unique_data, unique_data, unique_data], ignore_index=True)
        assert len(duplicate_df) == 15

        deduped, stats = remove_exact_duplicates(duplicate_df)
        assert len(deduped) == 5
        assert stats["duplicates_dropped"] == 10
        assert stats["before_dedup"] == 15
        assert stats["after_dedup"] == 5
        assert np.isclose(stats["duplicate_fraction"], 10 / 15)

    def test_preserve_rare_families_sample(self):
        """Verify rare families (< threshold) are kept at 100% and large classes subsampled."""
        df = pd.DataFrame({
            "feat1": np.arange(1200, dtype=float),
            "feat2": np.arange(1200, dtype=float),
            "Label": ["Benign"] * 800 + ["DoS"] * 300 + ["PortScan"] * 80 + ["BruteForce"] * 20
        })
        # Threshold: 100 (PortScan=80, BruteForce=20 are rare and kept 100%)
        # Target total: 500
        sampled = preserve_rare_families_sample(
            df,
            target_total=500,
            rare_threshold=100,
            random_seed=42
        )
        assert len(sampled[sampled["Label"] == "PortScan"]) == 80
        assert len(sampled[sampled["Label"] == "BruteForce"]) == 20
        assert len(sampled) == 500


class TestLeakageAudit:
    def test_leakage_audit_detects_zero_leakage_on_disjoint_sets(self):
        """When train and test distributions do not overlap, leakage must be 0%."""
        train_df = pd.DataFrame({
            "feat1": [1.0, 2.0, 3.0, 4.0],
            "feat2": [10.0, 20.0, 30.0, 40.0],
            "Label": ["Benign", "Benign", "DoS", "DoS"]
        })
        test_positives = pd.DataFrame({
            "feat1": [100.0, 200.0],
            "feat2": [1000.0, 2000.0],
            "Label": ["PortScan", "PortScan"]
        })
        result = audit_family_leakage(
            train_df=train_df,
            test_positives_df=test_positives,
            feature_cols=["feat1", "feat2"],
            rounding_decimals=[3, 2, 1]
        )
        assert result["exact_matches"] == 0
        assert result["exact_leakage_pct"] == 0.0
        assert result["near_matches_dec3"] == 0
        assert result["near_matches_dec2"] == 0
        assert result["near_matches_dec1"] == 0

    def test_sanity_check_benign_overlap_known_duplicates(self):
        """Inject known synthetic perturbations to verify detection at each decimal precision level.

        Prompt 1 Item 4 requirement:
        Confirms audit detects exact matches and near-duplicates at each rounding level.
        """
        # Baseline training set with Benign and DoS
        train_df = pd.DataFrame({
            "f1": [10.0000, 20.0000, 30.0000],
            "f2": [50.0000, 60.0000, 70.0000],
            "Label": ["Benign", "Benign", "DoS"]
        })

        # Test flows with known perturbations relative to train row 0 [10.0, 50.0] (Benign):
        # Index 0: Exact clone -> [10.0000, 50.0000] (matches exact, 3 dec, 2 dec, 1 dec)
        # Index 1: Jitter = 0.0002 -> [10.0002, 50.0002] (matches 3 dec, 2 dec, 1 dec; NOT exact)
        # Index 2: Jitter = 0.0030 -> [10.0030, 50.0030] (matches 2 dec, 1 dec; NOT 3 dec, NOT exact)
        # Index 3: Jitter = 0.0300 -> [10.0300, 50.0300] (matches 1 dec; NOT 2 dec, NOT 3 dec, NOT exact)
        # Index 4: Completely disjoint -> [999.0, 999.0] (matches none)
        test_positives = pd.DataFrame({
            "f1": [10.0000, 10.0002, 10.0030, 10.0300, 999.0000],
            "f2": [50.0000, 50.0002, 50.0030, 50.0300, 999.0000],
            "Label": ["PortScan"] * 5
        })

        result = audit_family_leakage(
            train_df=train_df,
            test_positives_df=test_positives,
            feature_cols=["f1", "f2"],
            rounding_decimals=[3, 2, 1],
            label_col="Label"
        )

        # 1 out of 5 exact (20.0%)
        assert result["exact_matches"] == 1
        assert np.isclose(result["exact_leakage_pct"], 20.0)

        # 2 out of 5 match at 3 decimals (Index 0, 1) -> 40.0%
        assert result["near_matches_dec3"] == 2
        assert np.isclose(result["near_leakage_pct_dec3"], 40.0)

        # 3 out of 5 match at 2 decimals (Index 0, 1, 2) -> 60.0%
        assert result["near_matches_dec2"] == 3
        assert np.isclose(result["near_leakage_pct_dec2"], 60.0)

        # 4 out of 5 match at 1 decimal (Index 0, 1, 2, 3) -> 80.0%
        assert result["near_matches_dec1"] == 4
        assert np.isclose(result["near_leakage_pct_dec1"], 80.0)

        # Confirm benign-specific overlap mirrors the exact test flows overlapping train benign
        assert result["benign_near_matches_dec2"] == 3
        assert np.isclose(result["benign_near_leakage_pct_dec2"], 60.0)

    def test_run_leakage_contrast_audit(self):
        """Test the contrast audit runs side-by-side random split vs LOFO."""
        df = pd.DataFrame({
            "f1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "f2": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
            "Label": ["Benign"] * 6 + ["DoS"] * 2 + ["PortScan"] * 2
        })
        contrast = run_leakage_contrast_audit(
            df=df,
            families=["DoS", "PortScan"],
            feature_cols=["f1", "f2"],
            test_size=0.5,
            rounding_levels=[3, 2, 1],
            random_seed=42
        )
        assert len(contrast) == 2
        assert "Family" in contrast.columns
        assert "Rand_Near_Leakage_3dec_Pct" in contrast.columns
        assert "LOFO_Near_Leakage_3dec_Pct" in contrast.columns
        assert "LOFO_Total_Matches_3dec_Count" in contrast.columns
        assert "LOFO_Both_Overlap_3dec_Count" in contrast.columns

    def test_lofo_total_equals_union_and_overlap_count(self):
        """Verify LOFO total equals union of benign-only, other-only, and both overlap."""
        feature_cols = ["f1", "f2"]

        # Train contains Benign and OtherAttack (e.g. DoS)
        train_df = pd.DataFrame({
            "f1": [1.000, 2.000, 3.000],
            "f2": [10.000, 20.000, 30.000],
            "Label": ["Benign", "DoS", "Benign"]
        })
        # Test positives (e.g. PortScan)
        # flow 0: matches Benign only (1.0001, 10.0001 -> rounds to 1.000, 10.000)
        # flow 1: matches DoS only (2.0001, 20.0001 -> rounds to 2.000, 20.000)
        # flow 2: matches both (we add a flow in DoS that also matches 1.000, 10.000)
        # flow 3: novel flow (9.999, 99.999)
        train_with_both = pd.DataFrame({
            "f1": [1.000, 2.000, 1.000],
            "f2": [10.000, 20.000, 10.000],
            "Label": ["Benign", "DoS", "DoS"] # now (1.0, 10.0) is in both Benign and DoS
        })
        test_positives = pd.DataFrame({
            "f1": [1.0001, 2.0001, 9.999],
            "f2": [10.0001, 20.0001, 99.999],
            "Label": ["PortScan", "PortScan", "PortScan"]
        })

        res = audit_family_leakage(
            train_df=train_with_both,
            test_positives_df=test_positives,
            feature_cols=feature_cols,
            rounding_decimals=[3],
            label_col="Label"
        )

        assert res["both_matches_dec3"] == 1        # flow 0 matches both Benign and DoS
        assert res["other_only_matches_dec3"] == 1  # flow 1 matches DoS only
        assert res["benign_only_matches_dec3"] == 0 # no flow matches ONLY benign
        assert res["union_matches_dec3"] == 2       # total union = 1 + 1 + 0 = 2
        assert res["union_matches_dec3"] == (
            res["benign_only_matches_dec3"] + res["other_only_matches_dec3"] + res["both_matches_dec3"]
        )

    def test_exact_leakage_vs_nn_distance_submicrosecond_jitter(self):
        """Explain and verify why exact leakage is 0.0% while standardized NN distance is 0.0000 on identical columns."""
        from src.data.audit import compute_knn_leakage

        cols = [f"feat_{i}" for i in range(10)]
        # Training set with 50 flows
        np.random.seed(42)
        X_train_vals = np.random.uniform(10.0, 100.0, size=(50, 10))
        train_df = pd.DataFrame(X_train_vals, columns=cols)
        train_df["Label"] = "Benign"

        # Test flows generated with 1 microsecond / 1e-7 jitter on only 1 feature
        X_test_vals = X_train_vals[:10].copy()
        X_test_vals[:, 0] += 1e-7 # 0.0000001 difference (e.g. sub-microsecond timestamp/duration jitter)
        test_df = pd.DataFrame(X_test_vals, columns=cols)
        test_df["Label"] = "PortScan"

        # 1. Exact duplicate check on the exact same feature columns
        audit_res = audit_family_leakage(
            train_df=train_df,
            test_positives_df=test_df,
            feature_cols=cols,
            rounding_decimals=[3],
            label_col="Label"
        )
        # Exact leakage is strictly 0% because 1e-7 != 0
        assert audit_res["exact_matches"] == 0
        assert audit_res["exact_leakage_pct"] == 0.0

        # 2. Rounding-independent NN distance on the EXACT SAME feature columns
        knn_res = compute_knn_leakage(
            train_df=train_df,
            test_positives_df=test_df,
            feature_cols=cols,
            label_col="Label"
        )
        # In standardized space, 1e-7 / std rounds to 0.0000
        assert knn_res["median_nn_dist"] < 1e-4
        assert knn_res["median_nn_dist"] == 0.0000
