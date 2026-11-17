"""Local persistence store for SentinelX analyst reviews and alert queue.

Implements lightweight, local SQLite persistence:
- Stored locally at results/reviews/analyst_reviews.db (no cloud dependencies).
- Stores alerts and recorded analyst review actions.
- Supports filtering by risk tier, attack family, and review status.
"""

from typing import Dict, List, Optional, Any, Tuple
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from src.alerts.schema import (
    RiskTier,
    RecommendedAction,
    FlowAlert,
    ReviewStatus,
    ReviewAction,
    ReviewRecord,
    QueueAlert,
)

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path("results/reviews/analyst_reviews.db")


class LocalReviewStore:
    """SQLite-backed local storage for queue alerts and analyst reviews."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    alert_id TEXT PRIMARY KEY,
                    flow_id TEXT,
                    timestamp TEXT NOT NULL,
                    risk_tier TEXT NOT NULL,
                    recommended_action TEXT NOT NULL,
                    production_score REAL NOT NULL,
                    autoencoder_score REAL NOT NULL,
                    supervised_score REAL NOT NULL,
                    suspected_family TEXT,
                    review_status TEXT NOT NULL DEFAULT 'PENDING',
                    alert_json TEXT NOT NULL,
                    flow_telemetry_json TEXT,
                    batch_id TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    analyst_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
                )
            """)
            # Migration check: ensure batch_id column exists on pre-existing tables
            cursor = conn.execute("PRAGMA table_info(alerts)")
            cols = [row["name"] for row in cursor.fetchall()]
            if "batch_id" not in cols:
                conn.execute("ALTER TABLE alerts ADD COLUMN batch_id TEXT")

            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_tier ON alerts(risk_tier)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(review_status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_family ON alerts(suspected_family)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_batch ON alerts(batch_id)")
            conn.commit()

    def insert_alerts(
        self,
        alerts: List[FlowAlert],
        telemetry_list: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """Insert a batch of alerts into the store."""
        inserted = 0
        with self._get_connection() as conn:
            for idx, alert in enumerate(alerts):
                telemetry = telemetry_list[idx] if (telemetry_list and idx < len(telemetry_list)) else None
                conn.execute("""
                    INSERT OR REPLACE INTO alerts (
                        alert_id, flow_id, timestamp, risk_tier, recommended_action,
                        production_score, autoencoder_score, supervised_score,
                        suspected_family, review_status, alert_json, flow_telemetry_json,
                        batch_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.alert_id,
                    alert.flow_id,
                    alert.timestamp,
                    alert.risk_tier.value,
                    alert.recommended_action.value,
                    alert.scores.production_score,
                    alert.scores.autoencoder_score,
                    alert.scores.supervised_score,
                    alert.suspected_family,
                    ReviewStatus.PENDING.value,
                    alert.model_dump_json(),
                    json.dumps(telemetry) if telemetry else None,
                    getattr(alert, "batch_id", None),
                ))
                inserted += 1
            conn.commit()
        return inserted

    def has_pending_batch(self, batch_id: str) -> bool:
        """Check if a batch_id already exists in the store with PENDING review status."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM alerts WHERE batch_id = ? AND review_status = 'PENDING'",
                (batch_id,)
            ).fetchone()
            return bool(row["cnt"] > 0)

    def get_alerts(
        self,
        risk_tier: Optional[str] = None,
        suspected_family: Optional[str] = None,
        review_status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[QueueAlert], int]:
        """Query queue alerts with optional filters.

        Returns:
            Tuple of (list_of_queue_alerts, total_matching_count)
        """
        query = "SELECT * FROM alerts WHERE 1=1"
        count_query = "SELECT COUNT(*) as cnt FROM alerts WHERE 1=1"
        params: List[Any] = []

        if risk_tier and isinstance(risk_tier, str):
            query += " AND risk_tier = ?"
            count_query += " AND risk_tier = ?"
            params.append(risk_tier.upper())

        if suspected_family and isinstance(suspected_family, str):
            query += " AND suspected_family = ?"
            count_query += " AND suspected_family = ?"
            params.append(suspected_family)

        if review_status and isinstance(review_status, str):
            query += " AND review_status = ?"
            count_query += " AND review_status = ?"
            params.append(review_status.upper())

        limit_val = int(limit) if isinstance(limit, (int, str)) and str(limit).isdigit() else 100
        offset_val = int(offset) if isinstance(offset, (int, str)) and str(offset).isdigit() else 0

        # Sort priority: CRITICAL > HIGH > MEDIUM > LOW, then newest first
        query += """
            ORDER BY 
                CASE risk_tier 
                    WHEN 'CRITICAL' THEN 1 
                    WHEN 'HIGH' THEN 2 
                    WHEN 'MEDIUM' THEN 3 
                    ELSE 4 
                END ASC,
                production_score DESC,
                timestamp DESC
            LIMIT ? OFFSET ?
        """
        exec_params = list(params) + [limit_val, offset_val]

        with self._get_connection() as conn:
            total_count = conn.execute(count_query, params).fetchone()["cnt"]
            rows = conn.execute(query, exec_params).fetchall()

            alerts: List[QueueAlert] = []
            for row in rows:
                alert_dict = json.loads(row["alert_json"])
                flow_alert = FlowAlert.model_validate(alert_dict)

                # Fetch latest review if any
                rev_row = conn.execute(
                    "SELECT * FROM reviews WHERE alert_id = ? ORDER BY review_id DESC LIMIT 1",
                    (row["alert_id"],)
                ).fetchone()

                latest_review = None
                if rev_row:
                    latest_review = ReviewRecord(
                        alert_id=rev_row["alert_id"],
                        action=ReviewAction(rev_row["action"]),
                        status=ReviewStatus(rev_row["status"]),
                        analyst_id=rev_row["analyst_id"],
                        timestamp=rev_row["timestamp"],
                        notes=rev_row["notes"],
                    )

                telemetry = json.loads(row["flow_telemetry_json"]) if row["flow_telemetry_json"] else None

                alerts.append(QueueAlert(
                    alert=flow_alert,
                    review_status=ReviewStatus(row["review_status"]),
                    latest_review=latest_review,
                    flow_telemetry=telemetry
                ))

            return alerts, total_count

    def get_alert_by_id(self, alert_id: str) -> Optional[QueueAlert]:
        """Fetch single alert by alert_id."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
            if not row:
                return None

            flow_alert = FlowAlert.model_validate(json.loads(row["alert_json"]))

            rev_row = conn.execute(
                "SELECT * FROM reviews WHERE alert_id = ? ORDER BY review_id DESC LIMIT 1",
                (alert_id,)
            ).fetchone()

            latest_review = None
            if rev_row:
                latest_review = ReviewRecord(
                    alert_id=rev_row["alert_id"],
                    action=ReviewAction(rev_row["action"]),
                    status=ReviewStatus(rev_row["status"]),
                    analyst_id=rev_row["analyst_id"],
                    timestamp=rev_row["timestamp"],
                    notes=rev_row["notes"],
                )

            telemetry = json.loads(row["flow_telemetry_json"]) if row["flow_telemetry_json"] else None

            return QueueAlert(
                alert=flow_alert,
                review_status=ReviewStatus(row["review_status"]),
                latest_review=latest_review,
                flow_telemetry=telemetry
            )

    def record_review(
        self,
        alert_id: str,
        action: ReviewAction,
        analyst_id: str = "analyst-1",
        notes: Optional[str] = None
    ) -> ReviewRecord:
        """Record an analyst review action and update the alert's review status."""
        action_status_map = {
            ReviewAction.CONFIRM_INCIDENT: ReviewStatus.CONFIRMED_INCIDENT,
            ReviewAction.MARK_BENIGN: ReviewStatus.BENIGN_SUPPRESSED,
            ReviewAction.SUPPRESS_ALERT: ReviewStatus.BENIGN_SUPPRESSED,
            ReviewAction.INVESTIGATE_FURTHER: ReviewStatus.IN_INVESTIGATION,
            ReviewAction.ESCALATE_TIER_2: ReviewStatus.ESCALATED_TIER_2,
        }
        new_status = action_status_map[action]
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            # Check alert exists
            row = conn.execute("SELECT alert_id FROM alerts WHERE alert_id = ?", (alert_id,)).fetchone()
            if not row:
                raise KeyError(f"Alert ID '{alert_id}' not found in store.")

            conn.execute("""
                INSERT INTO reviews (alert_id, action, status, analyst_id, timestamp, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (alert_id, action.value, new_status.value, analyst_id, now_iso, notes))

            conn.execute("""
                UPDATE alerts SET review_status = ? WHERE alert_id = ?
            """, (new_status.value, alert_id))
            conn.commit()

        return ReviewRecord(
            alert_id=alert_id,
            action=action,
            status=new_status,
            analyst_id=analyst_id,
            timestamp=now_iso,
            notes=notes
        )

    def get_queue_statistics(self) -> Dict[str, int]:
        """Get summary statistics for review queue."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) as cnt FROM alerts").fetchone()["cnt"]
            pending = conn.execute("SELECT COUNT(*) as cnt FROM alerts WHERE review_status = 'PENDING'").fetchone()["cnt"]
            critical = conn.execute("SELECT COUNT(*) as cnt FROM alerts WHERE risk_tier = 'CRITICAL'").fetchone()["cnt"]
            high = conn.execute("SELECT COUNT(*) as cnt FROM alerts WHERE risk_tier = 'HIGH'").fetchone()["cnt"]
            confirmed = conn.execute("SELECT COUNT(*) as cnt FROM alerts WHERE review_status = 'CONFIRMED_INCIDENT'").fetchone()["cnt"]
            suppressed = conn.execute("SELECT COUNT(*) as cnt FROM alerts WHERE review_status = 'BENIGN_SUPPRESSED'").fetchone()["cnt"]
            investigating = conn.execute("SELECT COUNT(*) as cnt FROM alerts WHERE review_status = 'IN_INVESTIGATION'").fetchone()["cnt"]
            escalated = conn.execute("SELECT COUNT(*) as cnt FROM alerts WHERE review_status = 'ESCALATED_TIER_2'").fetchone()["cnt"]

            return {
                "total_alerts": total,
                "pending_review": pending,
                "high_priority": critical + high,
                "critical": critical,
                "high": high,
                "confirmed_incidents": confirmed,
                "suppressed_benign": suppressed,
                "in_investigation": investigating,
                "escalated_tier_2": escalated,
            }
