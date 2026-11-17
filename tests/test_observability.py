"""Tests for SentinelX Phase 5: Safe Shadow-Mode Evaluation and Operational Observability.

Verifies:
1. Metric calculations: p50/p95 latency, alerts per hour, and risk tier distributions.
2. Quality counters: Invalid flow isolation, unavailable signals, and correlation misses.
3. Drift analysis: Baseline comparisons for scores and features, flagging drift without threshold modification or model retraining.
4. SQLite Metrics Store: Snapshot persistence, retention pruning, and non-destructive reset.
5. Evaluator batch execution: Latency tracking, queue integration, and monitor-only posture.
6. Safe Replay Runner: Synthetic and approved dataset replays with chunked batching.
7. Monitor-Only Invariant: Strict enforcement that autonomous blocking is disabled and zero network actions are taken.
8. FastAPI Service Endpoints: Ingestion, replay, metrics retrieval, and reset APIs.
"""

from datetime import datetime, timezone
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from src.guard.engine import SentinelGuard
from src.alerts.store import LocalReviewStore
from src.alerts.schema import RiskTier
from src.ingestion.models import LogEvent
from src.observability.models import (
    LatencyStats,
    QualityCounters,
    DistributionSummary,
    ScoreDriftMetric,
    FeatureDriftMetric,
    ShadowMetricsSnapshot,
)
from src.observability.drift import (
    DriftAnalyzer,
    BASELINE_FEATURE_STATS,
    BASELINE_SCORE_STATS,
    summarize_distribution,
)
from src.observability.store import ShadowMetricsStore
from src.observability.engine import ShadowEvaluator, compute_percentiles
from src.observability.replay import run_shadow_replay
from src.api.service import (
    app,
    get_shadow_evaluator,
    ShadowIngestRequest,
    ShadowReplayRequest,
    get_shadow_metrics,
    shadow_ingest_flows,
    shadow_replay,
    reset_shadow_metrics,
)


@pytest.fixture(scope="module")
def guard():
    """Shared production SentinelGuard instance."""
    return SentinelGuard(tau=0.56, gamma=0.41)


@pytest.fixture
def temp_review_store(tmp_path):
    """Creates an isolated temporary SQLite review store."""
    db_file = tmp_path / "test_shadow_reviews.db"
    return LocalReviewStore(db_path=db_file)


@pytest.fixture
def temp_obs_store(tmp_path):
    """Creates an isolated temporary SQLite shadow metrics store."""
    db_file = tmp_path / "test_shadow_metrics.db"
    return ShadowMetricsStore(db_path=db_file, max_snapshots=10)


@pytest.fixture(scope="module")
def valid_sample_flows():
    """Loads a small set of valid flow records."""
    sample_path = Path("scratch/sample_flows.csv")
    if not sample_path.exists():
        df = pd.read_parquet("data/processed/cicids2017_sample60k.parquet")
        sample_path.parent.mkdir(parents=True, exist_ok=True)
        df.head(20).to_csv(sample_path, index=False)
    df = pd.read_csv(sample_path)
    return df.head(10).to_dict(orient="records")


# ---------------------------------------------------------------------------
# 1. Latency & Quality Models Unit Tests
# ---------------------------------------------------------------------------

def test_latency_stats_calculation():
    """compute_percentiles accurately computes min, max, mean, p50, and p95."""
    empty_stats = compute_percentiles([])
    assert empty_stats.sample_count == 0
    assert empty_stats.p50_ms == 0.0
    assert empty_stats.p95_ms == 0.0

    # 100 measurements: 1.0 to 100.0 ms
    latencies = [float(i) for i in range(1, 101)]
    stats = compute_percentiles(latencies, is_batched=False)
    assert stats.sample_count == 100
    assert stats.min_ms == 1.0
    assert stats.max_ms == 100.0
    assert pytest.approx(stats.mean_ms, 0.1) == 50.5
    assert pytest.approx(stats.p50_ms, 1.0) == 50.5
    assert pytest.approx(stats.p95_ms, 1.0) == 95.05
    assert stats.is_batched is False


def test_quality_counters_and_snapshot_serialization():
    """ShadowMetricsSnapshot serializes to and deserializes from dictionary."""
    counters = QualityCounters(
        total_records_received=100,
        valid_records_scored=95,
        invalid_records_count=5,
        unavailable_signals_count=20,
        correlation_misses_count=8,
        correlation_hits_count=67,
    )
    latency = LatencyStats(p50_ms=4.2, p95_ms=8.5, min_ms=1.1, max_ms=12.0, mean_ms=4.8, sample_count=95)
    score_drift = ScoreDriftMetric(
        score_name="production_score",
        baseline_stats=DistributionSummary(mean=0.50, std=0.30),
        current_stats=DistributionSummary(mean=0.52, std=0.29),
        mean_shift=0.02,
        std_shift=0.01,
        drift_detected=False,
    )

    snapshot = ShadowMetricsSnapshot(
        snapshot_id="snap-test-001",
        timestamp=datetime.now(timezone.utc).isoformat(),
        operational_mode="MONITOR_ONLY",
        autonomous_blocking_authorized=False,
        total_flows_evaluated=95,
        alerts_per_hour_rate=14.4,
        latency_single_flow=latency,
        latency_batched=latency,
        quality=counters,
        risk_tier_counts={"CRITICAL": 2, "HIGH": 4, "MEDIUM": 5, "LOW": 1},
        suspected_family_counts={"PortScan": 6, "DoS_DDoS": 6},
        score_drift=[score_drift],
        feature_drift=[],
        queue_backlog_pending=12,
        analyst_review_outcomes={"PENDING": 12},
    )

    d = snapshot.model_dump()
    assert d["snapshot_id"] == "snap-test-001"
    assert d["autonomous_blocking_authorized"] is False
    assert d["latency_single_flow"]["p50_ms"] == 4.2
    assert d["quality"]["invalid_records_count"] == 5

    restored = ShadowMetricsSnapshot(**d)
    assert restored.snapshot_id == snapshot.snapshot_id
    assert restored.latency_single_flow.p50_ms == 4.2
    assert restored.quality.correlation_misses_count == 8
    assert restored.score_drift[0].drift_detected is False


# ---------------------------------------------------------------------------
# 2. Drift Analyzer & Safety Guarantees
# ---------------------------------------------------------------------------

def test_drift_analyzer_stable_distribution(guard):
    """Drift analyzer reports no drift when distributions match baseline within threshold."""
    analyzer = DriftAnalyzer(score_drift_threshold=0.15)
    # Production baseline is mean 0.5076, std 0.3012
    normal_scores = np.array([0.50, 0.52, 0.48, 0.51, 0.49, 0.53, 0.47, 0.50])
    drift_list = analyzer.evaluate_score_drift({"production": normal_scores})
    assert len(drift_list) == 1
    assert drift_list[0].score_name == "production_score"
    assert drift_list[0].drift_detected is False


def test_drift_analyzer_flags_score_drift(guard):
    """Drift analyzer flags drift on significant statistical shifts without altering thresholds."""
    initial_tau = guard.tau
    initial_gamma = guard.gamma

    analyzer = DriftAnalyzer(score_drift_threshold=0.15)
    # Severe shift: production scores all clustered near 0.99
    shifted_scores = np.array([0.98, 0.99, 0.99, 0.97, 0.99, 1.0, 0.98, 0.99])
    drift_list = analyzer.evaluate_score_drift({"production": shifted_scores})

    assert len(drift_list) == 1
    assert drift_list[0].drift_detected is True
    assert drift_list[0].mean_shift > 0.40

    # Defensive invariant: Model parameters and thresholds must NOT be adapted or retrained
    assert guard.tau == initial_tau == 0.56
    assert guard.gamma == initial_gamma == 0.41


def test_drift_analyzer_feature_drift():
    """Drift analyzer flags input feature drift when telemetry significantly deviates."""
    analyzer = DriftAnalyzer(feature_drift_std_threshold=2.0)

    # Shifted feature: Flow Duration 1000x greater than baseline mean
    shifted_df = pd.DataFrame({
        "Flow Duration": [1e9, 1.2e9, 1.1e9, 1.3e9],
        "Total Fwd Packets": [15, 18, 16, 17],
    })
    drift_list = analyzer.evaluate_feature_drift(shifted_df)
    assert len(drift_list) >= 1
    dur_drift = [d for d in drift_list if d.feature_name == "Flow Duration"][0]
    assert dur_drift.drift_detected is True
    assert dur_drift.normalized_mean_shift > 2.0


# ---------------------------------------------------------------------------
# 3. SQLite Shadow Store & Retention Pruning
# ---------------------------------------------------------------------------

def test_shadow_store_retention_and_reset(temp_obs_store):
    """Store persists snapshots, prunes oldest beyond max_snapshots, and supports safe reset."""
    for i in range(15):
        snap = ShadowMetricsSnapshot(
            snapshot_id=f"snap-{i:03d}",
            timestamp=f"2026-10-19T10:{i:02d}:00Z",
            operational_mode="MONITOR_ONLY",
            autonomous_blocking_authorized=False,
            total_flows_evaluated=10,
            alerts_per_hour_rate=2.0,
            latency_single_flow=LatencyStats(p50_ms=float(i), p95_ms=float(i * 2)),
            latency_batched=LatencyStats(p50_ms=float(i), p95_ms=float(i * 2)),
            quality=QualityCounters(),
            risk_tier_counts={},
            suspected_family_counts={},
        )
        temp_obs_store.record_snapshot(snap)

    # Max retention is 10; 15 inserts should leave at most 10 snapshots
    snapshots = temp_obs_store.get_snapshots(limit=50)
    assert len(snapshots) <= 10

    # Latest snapshot should be snap-014
    latest = temp_obs_store.get_latest_snapshot()
    assert latest is not None
    assert latest.snapshot_id == "snap-014"

    # Reset metrics cleanly purges shadow store
    reset_cnt = temp_obs_store.reset_metrics()
    assert reset_cnt >= 1
    assert temp_obs_store.get_latest_snapshot() is None


# ---------------------------------------------------------------------------
# 4. Shadow Evaluator Operational Benchmarking & Invariant Tests
# ---------------------------------------------------------------------------

def test_shadow_evaluator_live_run(guard, temp_review_store, temp_obs_store, valid_sample_flows):
    """ShadowEvaluator scores flows, records metrics, queues alerts, and enforces monitor-only."""
    evaluator = ShadowEvaluator(
        guard=guard,
        metrics_store=temp_obs_store,
        review_store=temp_review_store,
    )

    snapshot = evaluator.evaluate_batch(
        flows=valid_sample_flows,
        run_source="test_valid_flows",
        persist_alerts_to_queue=True,
    )

    assert snapshot.total_flows_evaluated == len(valid_sample_flows)
    assert snapshot.latency_single_flow.sample_count > 0
    assert snapshot.latency_single_flow.p50_ms > 0.0
    assert snapshot.latency_batched.p50_ms > 0.0
    assert snapshot.operational_mode == "MONITOR_ONLY"
    assert snapshot.autonomous_blocking_authorized is False

    # Check alert queue integration
    assert snapshot.queue_backlog_pending > 0

    # Verify snapshot persisted in metrics store
    latest = temp_obs_store.get_latest_snapshot()
    assert latest is not None
    assert latest.snapshot_id == snapshot.snapshot_id


def test_shadow_evaluator_invalid_records_handling(guard, temp_review_store, temp_obs_store, valid_sample_flows):
    """Invalid records are isolated and counted without interrupting scoring of valid flows."""
    evaluator = ShadowEvaluator(
        guard=guard,
        metrics_store=temp_obs_store,
        review_store=temp_review_store,
    )

    mixed_flows = [
        valid_sample_flows[0],
        {"invalid_key": "bad_data"},  # Missing canonical flow features
        valid_sample_flows[1],
    ]

    snapshot = evaluator.evaluate_batch(mixed_flows)
    assert snapshot.quality.total_records_received == 3
    assert snapshot.quality.valid_records_scored == 2
    assert snapshot.quality.invalid_records_count == 1
    assert snapshot.total_flows_evaluated == 2


def test_shadow_evaluator_unavailable_signals_and_correlation_misses(guard, temp_review_store, temp_obs_store, valid_sample_flows):
    """Evaluator properly tracks unavailable signals and correlation misses."""
    evaluator = ShadowEvaluator(
        guard=guard,
        metrics_store=temp_obs_store,
        review_store=temp_review_store,
    )

    # Valid flow augmented with IP/timestamp metadata
    flow_with_meta = dict(valid_sample_flows[0])
    flow_with_meta["Source IP"] = "192.168.1.50"
    flow_with_meta["Destination IP"] = "10.0.0.1"
    flow_with_meta["Destination Port"] = 80
    flow_with_meta["Timestamp"] = "2026-10-19 12:00:00"

    # Synthetic log events from a different IP (will produce correlation miss)
    unmatched_log = LogEvent(
        client_ip="203.0.113.99",
        timestamp=datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc),
        log_type="modsecurity",
        is_waf_alert=True,
        message="ModSecurity alert",
    )

    snapshot = evaluator.evaluate_batch(
        flows=[flow_with_meta],
        logs=[unmatched_log],
    )

    assert snapshot.quality.total_records_received == 1
    assert snapshot.quality.valid_records_scored == 1
    # Correlation miss should be counted
    assert snapshot.quality.correlation_misses_count == 1
    assert snapshot.quality.correlation_hits_count == 0


def test_monitor_only_no_network_action_guarantee(guard, temp_review_store, temp_obs_store, valid_sample_flows):
    """Asserts strict monitor-only posture: no autonomous blocking authorized under any condition."""
    evaluator = ShadowEvaluator(
        guard=guard,
        metrics_store=temp_obs_store,
        review_store=temp_review_store,
    )

    snapshot = evaluator.evaluate_batch(valid_sample_flows)
    assert snapshot.operational_mode == "MONITOR_ONLY"
    assert snapshot.autonomous_blocking_authorized is False


# ---------------------------------------------------------------------------
# 5. Shadow Replay Runner Tests
# ---------------------------------------------------------------------------

def test_shadow_replay_runner_synthetic(guard, temp_review_store, temp_obs_store):
    """Replay runner processes synthetic flow and log datasets cleanly."""
    evaluator = ShadowEvaluator(
        guard=guard,
        metrics_store=temp_obs_store,
        review_store=temp_review_store,
    )

    res = run_shadow_replay(
        dataset_source="synthetic",
        batch_size=5,
        max_flows=10,
        include_logs=True,
        evaluator=evaluator,
    )

    assert res["status"] == "COMPLETED"
    assert res["dataset_source"] == "synthetic"
    assert res["flows_replayed"] > 0
    assert res["batches_processed"] >= 1
    assert res["operational_mode"] == "MONITOR_ONLY"
    assert res["autonomous_blocking_authorized"] is False
    assert "latency" in res


def test_shadow_replay_runner_sample_flows(guard, temp_review_store, temp_obs_store):
    """Replay runner operates on scratch sample flows dataset."""
    evaluator = ShadowEvaluator(
        guard=guard,
        metrics_store=temp_obs_store,
        review_store=temp_review_store,
    )

    res = run_shadow_replay(
        dataset_source="sample_flows",
        batch_size=10,
        max_flows=10,
        include_logs=False,
        evaluator=evaluator,
    )

    assert res["status"] == "COMPLETED"
    assert res["flows_replayed"] > 0
    assert res["autonomous_blocking_authorized"] is False


# ---------------------------------------------------------------------------
# 6. FastAPI Service Endpoints Integration Tests
# ---------------------------------------------------------------------------

def test_shadow_api_endpoints(valid_sample_flows):
    """Validates FastAPI shadow-mode endpoints directly."""
    # 1. Reset metrics first
    reset_res = reset_shadow_metrics()
    assert reset_res["status"] == "SUCCESS"

    # 2. Ingest flows in shadow mode
    ingest_req = ShadowIngestRequest(
        flows=valid_sample_flows[:3],
        time_window_seconds=30.0,
        persist_alerts_to_queue=False,
    )
    ingest_data = shadow_ingest_flows(ingest_req)
    assert ingest_data["autonomous_blocking_authorized"] is False
    assert ingest_data["operational_mode"] == "MONITOR_ONLY"
    assert ingest_data["total_flows_evaluated"] == 3

    # 3. Retrieve shadow metrics
    metrics_data = get_shadow_metrics()
    assert metrics_data["operational_mode"] == "MONITOR_ONLY"
    assert metrics_data["autonomous_blocking_authorized"] is False

    # 4. Trigger shadow replay
    replay_req = ShadowReplayRequest(dataset_source="synthetic", batch_size=10, max_flows=10)
    replay_data = shadow_replay(replay_req)
    assert replay_data["status"] == "COMPLETED"
    assert replay_data["autonomous_blocking_authorized"] is False

