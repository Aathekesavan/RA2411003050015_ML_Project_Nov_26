"""Tests for SentinelX Analyst Review Dashboard and Queue API.

Verifies:
1. LocalReviewStore persistence (insert, query, filters, statistics).
2. Analyst review action recording and status transitions.
3. API endpoints:
   - GET /api/v1/alerts (filtered queue)
   - GET /api/v1/alerts/{alert_id} (detail telemetry)
   - POST /api/v1/alerts/{alert_id}/review (recording decisions)
   - POST /api/v1/queue/load_sample (sample traffic ingestion)
4. Monitor-only invariant: ensuring review actions never offer or trigger packet blocking.
5. Missing/unavailable signal transparency in queue alerts.
"""

import pytest
from pathlib import Path
import tempfile
import pandas as pd

from src.alerts.store import LocalReviewStore
from src.alerts.schema import (
    RiskTier,
    RecommendedAction,
    FlowAlert,
    ScoresBreakdown,
    ConfirmingSignalEvidence,
    ReviewStatus,
    ReviewAction,
    ReviewRecord,
)
from src.api.service import (
    app,
    get_store,
    list_queue_alerts,
    get_alert_detail,
    record_analyst_review,
    load_sample_alerts,
    ReviewActionRequest,
)


@pytest.fixture
def temp_store(tmp_path):
    """Creates a temporary isolated SQLite review store."""
    db_file = tmp_path / "test_reviews.db"
    return LocalReviewStore(db_path=db_file)


@pytest.fixture
def mock_flow_alert():
    """Generates a synthetic mock FlowAlert for testing."""
    scores = ScoresBreakdown(
        supervised_score=0.85,
        autoencoder_score=0.72,
        production_score=0.95,
        gated_activation=True,
        tau=0.56,
        gamma=0.41,
    )
    signals = {
        "request_rate": ConfirmingSignalEvidence(
            signal_name="request_rate",
            present=True,
            value=120.0,
            threshold=50.0,
            confirmed=True,
            description="Observed request rate 120.0 req/s"
        ),
        "auth_failures": ConfirmingSignalEvidence(
            signal_name="auth_failures",
            present=False,
            value=None,
            threshold=5,
            confirmed=None,
            description="Authentication telemetry was not provided in input."
        )
    }
    return FlowAlert(
        alert_id="test-alert-uuid-1",
        timestamp="2026-10-19T12:00:00Z",
        flow_id="flow-test-1",
        risk_tier=RiskTier.CRITICAL,
        recommended_action=RecommendedAction.ESCALATE_TO_ANALYST,
        autonomous_blocking_authorized=False,
        scores=scores,
        confirming_signals=signals,
        suspected_family="PortScan",
        policy_notes=["Defensive Principle 1 applied: autonomous packet/connection blocking strictly disabled."]
    )


def test_store_insert_and_retrieve(temp_store, mock_flow_alert):
    """Store inserts alert and retrieves it with PENDING review status."""
    inserted = temp_store.insert_alerts([mock_flow_alert], telemetry_list=[{"Flow Duration": 12345}])
    assert inserted == 1

    alerts, count = temp_store.get_alerts()
    assert count == 1
    assert len(alerts) == 1
    assert alerts[0].alert.alert_id == "test-alert-uuid-1"
    assert alerts[0].review_status == ReviewStatus.PENDING
    assert alerts[0].flow_telemetry == {"Flow Duration": 12345}


def test_store_filters(temp_store, mock_flow_alert):
    """Store properly filters by risk tier, family, and review status."""
    temp_store.insert_alerts([mock_flow_alert])

    # Filter matching
    res_tier, cnt = temp_store.get_alerts(risk_tier="CRITICAL")
    assert cnt == 1
    res_fam, cnt = temp_store.get_alerts(suspected_family="PortScan")
    assert cnt == 1
    res_status, cnt = temp_store.get_alerts(review_status="PENDING")
    assert cnt == 1

    # Filter non-matching
    res_non, cnt = temp_store.get_alerts(risk_tier="LOW")
    assert cnt == 0
    res_non_fam, cnt = temp_store.get_alerts(suspected_family="Bot")
    assert cnt == 0


def test_store_record_review_actions(temp_store, mock_flow_alert):
    """Analyst review actions update status, persist notes, and reflect in stats."""
    temp_store.insert_alerts([mock_flow_alert])

    # Record confirmation
    review = temp_store.record_review(
        alert_id="test-alert-uuid-1",
        action=ReviewAction.CONFIRM_INCIDENT,
        analyst_id="sec-analyst-alpha",
        notes="Verified active scanning probes against port 80."
    )
    assert review.action == ReviewAction.CONFIRM_INCIDENT
    assert review.status == ReviewStatus.CONFIRMED_INCIDENT
    assert review.notes == "Verified active scanning probes against port 80."

    # Retrieve and check updated status
    item = temp_store.get_alert_by_id("test-alert-uuid-1")
    assert item is not None
    assert item.review_status == ReviewStatus.CONFIRMED_INCIDENT
    assert item.latest_review.analyst_id == "sec-analyst-alpha"

    # Verify queue statistics
    stats = temp_store.get_queue_statistics()
    assert stats["total_alerts"] == 1
    assert stats["pending_review"] == 0
    assert stats["confirmed_incidents"] == 1


def test_store_suppress_and_escalate(temp_store, mock_flow_alert):
    """Store handles MARK_BENIGN and ESCALATE_TIER_2 actions."""
    temp_store.insert_alerts([mock_flow_alert])

    # Mark benign
    rev1 = temp_store.record_review(
        alert_id="test-alert-uuid-1",
        action=ReviewAction.MARK_BENIGN,
        notes="Internal monitoring health probe."
    )
    assert rev1.status == ReviewStatus.BENIGN_SUPPRESSED

    stats = temp_store.get_queue_statistics()
    assert stats["suppressed_benign"] == 1

    # Escalate
    rev2 = temp_store.record_review(
        alert_id="test-alert-uuid-1",
        action=ReviewAction.ESCALATE_TIER_2,
        notes="Requires CSIRT escalation."
    )
    assert rev2.status == ReviewStatus.ESCALATED_TIER_2


def test_api_queue_integration():
    """API list_queue_alerts, load_sample, and review actions work seamlessly."""
    # 1. Load sample traffic
    sample_res = load_sample_alerts()
    assert sample_res.returned_count > 0
    assert sample_res.guard_mode == "MONITOR_ONLY"

    # 2. Query queue
    queue_res = list_queue_alerts(limit=5)
    assert queue_res.returned_count > 0
    target_alert_id = queue_res.alerts[0].alert.alert_id

    # 3. Get detail
    detail = get_alert_detail(target_alert_id)
    assert detail.alert.alert_id == target_alert_id
    assert detail.alert.autonomous_blocking_authorized is False

    # 4. Record review
    rev_res = record_analyst_review(
        alert_id=target_alert_id,
        body=ReviewActionRequest(
            action=ReviewAction.INVESTIGATE_FURTHER,
            analyst_id="analyst-test",
            notes="Reviewing connection patterns."
        )
    )
    assert rev_res.status == ReviewStatus.IN_INVESTIGATION


def test_unavailable_signals_in_queue():
    """Stored queue alerts preserve explicit signal unavailability notes."""
    sample_res = load_sample_alerts()
    first_alert = sample_res.alerts[0].alert

    signals = first_alert.confirming_signals
    # At least one signal should be marked as present=False, confirmed=None
    unavail_signals = [s for s in signals.values() if not s.present]
    assert len(unavail_signals) > 0
    for s in unavail_signals:
        assert s.confirmed is None
        assert "not provided" in s.description.lower()


def test_cards_expose_distinct_alert_identities_for_repeated_flow_ids(temp_store, mock_flow_alert):
    """Proves that queue items expose distinct alert identities (UUIDs & timestamps) even when flow_id repeats."""
    import copy
    alert1 = copy.deepcopy(mock_flow_alert)
    alert1.alert_id = "11112222-aaaa-bbbb-cccc-000000000001"
    alert1.flow_id = "flow-0"
    alert1.timestamp = "2026-10-19T10:00:00Z"
    alert1.batch_id = "batch-run-alpha"

    alert2 = copy.deepcopy(mock_flow_alert)
    alert2.alert_id = "99998888-zzzz-yyyy-xxxx-000000000002"
    alert2.flow_id = "flow-0"
    alert2.timestamp = "2026-10-19T11:00:00Z"
    alert2.batch_id = "batch-run-beta"

    temp_store.insert_alerts([alert1, alert2])

    items, count = temp_store.get_alerts()
    assert count == 2
    # Both alerts share the identical flow_id
    assert items[0].alert.flow_id == "flow-0"
    assert items[1].alert.flow_id == "flow-0"
    # But alert UUIDs, short representations, batch IDs, and timestamps are completely distinct
    assert items[0].alert.alert_id != items[1].alert.alert_id
    assert items[0].alert.alert_id[:8] != items[1].alert.alert_id[:8]
    assert items[0].alert.batch_id != items[1].alert.batch_id
    assert items[0].alert.timestamp != items[1].alert.timestamp


def test_reviewing_one_uuid_leaves_same_flow_id_unchanged(temp_store, mock_flow_alert):
    """Proves reviewing one alert UUID leaves another alert record with the same flow ID untouched."""
    import copy
    alert_a = copy.deepcopy(mock_flow_alert)
    alert_a.alert_id = "uuid-flow4-first"
    alert_a.flow_id = "flow-4"

    alert_b = copy.deepcopy(mock_flow_alert)
    alert_b.alert_id = "uuid-flow4-second"
    alert_b.flow_id = "flow-4"

    temp_store.insert_alerts([alert_a, alert_b])

    # Review only alert_a
    temp_store.record_review(
        alert_id="uuid-flow4-first",
        action=ReviewAction.CONFIRM_INCIDENT,
        analyst_id="analyst-lead",
        notes="Confirmed brute force attack on first occurrence."
    )

    item_a = temp_store.get_alert_by_id("uuid-flow4-first")
    item_b = temp_store.get_alert_by_id("uuid-flow4-second")

    assert item_a is not None and item_b is not None
    assert item_a.review_status == ReviewStatus.CONFIRMED_INCIDENT
    assert item_a.latest_review.action == ReviewAction.CONFIRM_INCIDENT
    # Second alert sharing flow-4 must remain PENDING with no review
    assert item_b.review_status == ReviewStatus.PENDING
    assert item_b.latest_review is None


def test_sample_ingestion_idempotence():
    """Proves repeated default sample-ingestion calls do not keep adding duplicate pending sample batches."""
    # Ensure initial sample ingestion
    res1 = load_sample_alerts(force=False)
    initial_count = res1.returned_count

    # Second call without force should recognise pending batch and return existing queue without duplicating
    res2 = load_sample_alerts(force=False)
    assert res2.returned_count == initial_count

    # Verify queue alert count has not increased
    queue_res = list_queue_alerts()
    assert queue_res.returned_count == initial_count


def test_store_has_pending_batch_lifecycle(temp_store, mock_flow_alert):
    """Proves has_pending_batch tracks pending batches and clears once all alerts are reviewed."""
    import copy
    alert = copy.deepcopy(mock_flow_alert)
    alert.alert_id = "uuid-batch-test-1"
    alert.batch_id = "test-lifecycle-batch"

    # Initially not present
    assert temp_store.has_pending_batch("test-lifecycle-batch") is False

    # Insert pending alert
    temp_store.insert_alerts([alert])
    assert temp_store.has_pending_batch("test-lifecycle-batch") is True

    # Review alert to CONFIRMED_INCIDENT
    temp_store.record_review(
        alert_id="uuid-batch-test-1",
        action=ReviewAction.CONFIRM_INCIDENT,
        analyst_id="analyst-test",
        notes="Lifecycle test review"
    )

    # Now no alerts in this batch are PENDING
    assert temp_store.has_pending_batch("test-lifecycle-batch") is False

