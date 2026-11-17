"""Local SQLite storage for SentinelX Phase 5 Shadow-Mode Observability Metrics.

Persists time-series operational snapshots, tracks data quality and drift metrics,
and enforces configurable retention and explicit reset policies without touching
analyst review records.
"""

import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from src.observability.models import (
    ShadowMetricsSnapshot,
    LatencyStats,
    QualityCounters,
    ScoreDriftMetric,
    FeatureDriftMetric,
)

logger = logging.getLogger(__name__)

DEFAULT_METRICS_DB_PATH = Path("results/observability/shadow_metrics.db")
DEFAULT_RETENTION_MAX_SNAPSHOTS = 500


class ShadowMetricsStore:
    """Manages persistence, retrieval, retention, and reset of shadow metrics."""

    def __init__(self, db_path: Optional[Path] = None, max_snapshots: int = DEFAULT_RETENTION_MAX_SNAPSHOTS):
        self.db_path = Path(db_path) if db_path else DEFAULT_METRICS_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_snapshots = max_snapshots
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shadow_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    total_flows INTEGER NOT NULL,
                    alerts_per_hour REAL NOT NULL,
                    risk_tier_json TEXT NOT NULL,
                    family_json TEXT NOT NULL,
                    queue_backlog INTEGER NOT NULL,
                    review_outcomes_json TEXT NOT NULL,
                    latency_single_json TEXT NOT NULL,
                    latency_batched_json TEXT NOT NULL,
                    quality_json TEXT NOT NULL,
                    score_drift_json TEXT NOT NULL,
                    feature_drift_json TEXT NOT NULL,
                    notes_json TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shadow_runs (
                    run_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    flows_count INTEGER NOT NULL,
                    is_replay BOOLEAN NOT NULL,
                    source TEXT NOT NULL,
                    notes TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_time ON shadow_snapshots(timestamp);")
            conn.commit()

    def record_snapshot(self, snap: ShadowMetricsSnapshot) -> str:
        """Persist a shadow observability metrics snapshot."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO shadow_snapshots (
                    snapshot_id, timestamp, total_flows, alerts_per_hour,
                    risk_tier_json, family_json, queue_backlog, review_outcomes_json,
                    latency_single_json, latency_batched_json, quality_json,
                    score_drift_json, feature_drift_json, notes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snap.snapshot_id,
                snap.timestamp,
                snap.total_flows_evaluated,
                snap.alerts_per_hour_rate,
                json.dumps(snap.risk_tier_counts),
                json.dumps(snap.suspected_family_counts),
                snap.queue_backlog_pending,
                json.dumps(snap.analyst_review_outcomes),
                snap.latency_single_flow.model_dump_json(),
                snap.latency_batched.model_dump_json(),
                snap.quality.model_dump_json(),
                json.dumps([m.model_dump() for m in snap.score_drift]),
                json.dumps([m.model_dump() for m in snap.feature_drift]),
                json.dumps(snap.notes),
            ))
            conn.commit()

        self.prune_retention()
        return snap.snapshot_id

    def record_run(self, run_id: str, flows_count: int, is_replay: bool, source: str, notes: str = ""):
        """Record a shadow evaluation or replay execution run."""
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO shadow_runs (run_id, timestamp, flows_count, is_replay, source, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (run_id, now_iso, flows_count, is_replay, source, notes))
            conn.commit()

    def get_latest_snapshot(self) -> Optional[ShadowMetricsSnapshot]:
        """Fetch the most recent shadow metrics snapshot."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM shadow_snapshots ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            if not row:
                return None
            return self._row_to_snapshot(row)

    def get_snapshots(self, limit: int = 20) -> List[ShadowMetricsSnapshot]:
        """Fetch recent shadow metrics snapshots."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM shadow_snapshots ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [self._row_to_snapshot(r) for r in rows]

    list_snapshots = get_snapshots

    def _row_to_snapshot(self, row: sqlite3.Row) -> ShadowMetricsSnapshot:
        return ShadowMetricsSnapshot(
            snapshot_id=row["snapshot_id"],
            timestamp=row["timestamp"],
            operational_mode="MONITOR_ONLY",
            autonomous_blocking_authorized=False,
            total_flows_evaluated=row["total_flows"],
            alerts_per_hour_rate=row["alerts_per_hour"],
            risk_tier_counts=json.loads(row["risk_tier_json"]),
            suspected_family_counts=json.loads(row["family_json"]),
            queue_backlog_pending=row["queue_backlog"],
            analyst_review_outcomes=json.loads(row["review_outcomes_json"]),
            latency_single_flow=LatencyStats.model_validate_json(row["latency_single_json"]),
            latency_batched=LatencyStats.model_validate_json(row["latency_batched_json"]),
            quality=QualityCounters.model_validate_json(row["quality_json"]),
            score_drift=[ScoreDriftMetric.model_validate(m) for m in json.loads(row["score_drift_json"])],
            feature_drift=[FeatureDriftMetric.model_validate(m) for m in json.loads(row["feature_drift_json"])],
            notes=json.loads(row["notes_json"]) if row["notes_json"] else []
        )

    def prune_retention(self):
        """Enforce retention window by pruning snapshots beyond max_snapshots limit."""
        with self._get_connection() as conn:
            count = conn.execute("SELECT COUNT(*) as cnt FROM shadow_snapshots").fetchone()["cnt"]
            if count > self.max_snapshots:
                excess = count - self.max_snapshots
                conn.execute("""
                    DELETE FROM shadow_snapshots WHERE snapshot_id IN (
                        SELECT snapshot_id FROM shadow_snapshots ORDER BY timestamp ASC LIMIT ?
                    )
                """, (excess,))
                conn.commit()
                logger.info(f"Pruned {excess} expired shadow metrics snapshots.")

    def reset_metrics(self) -> int:
        """Safely reset all shadow metrics and run logs without altering analyst reviews."""
        with self._get_connection() as conn:
            cnt = conn.execute("SELECT COUNT(*) as cnt FROM shadow_snapshots").fetchone()["cnt"]
            conn.execute("DELETE FROM shadow_snapshots")
            conn.execute("DELETE FROM shadow_runs")
            conn.commit()
            logger.info("Shadow metrics store successfully reset.")
            return cnt
