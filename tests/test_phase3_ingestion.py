"""Tests for SentinelX Phase 3: Web-Server & WAF Log Ingestion and Flow Correlation.

Covers:
1. Log Parsing: Nginx access logs, Nginx error logs, ModSecurity text and JSON.
2. Malformed Line Handling: Isolation without crashing.
3. Correlation Logic: Matching keys, temporal windows, and boundaries.
4. Defensive Invariant: Unavailable evidence when metadata is missing.
5. Scenario 1: Slow-rate Brute Force requiring authentication-failure evidence.
6. Scenario 2: Benign traffic burst de-escalated to monitor without attack confirmation.
7. API Integration: Ingestion and scoring endpoints with review queue persistence.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd

from src.ingestion.models import LogEvent, ParseResult
from src.ingestion.parsers import (
    NginxAccessLogParser,
    NginxErrorLogParser,
    ModSecurityParser,
    parse_nginx_timestamp,
    parse_nginx_error_timestamp,
)
from src.ingestion.correlator import (
    LogFlowCorrelator,
    parse_flow_timestamp,
    extract_flow_duration_seconds,
)
from src.guard.engine import SentinelGuard
from src.alerts.schema import RiskTier, RecommendedAction
from src.alerts.store import LocalReviewStore
from src.api.service import (
    correlate_and_score_flows,
    run_phase3_demo_endpoint,
    CorrelateAndScoreRequest,
)


@pytest.fixture(scope="module")
def guard():
    """Shared SentinelGuard instance."""
    return SentinelGuard(tau=0.56, gamma=0.41)


@pytest.fixture
def temp_store(tmp_path):
    """Creates a temporary isolated SQLite review store."""
    db_file = tmp_path / "test_phase3_reviews.db"
    return LocalReviewStore(db_path=db_file)


# ---------------------------------------------------------------------------
# 1. Parsing & Malformed Line Tests
# ---------------------------------------------------------------------------

def test_nginx_access_log_parser_valid():
    """Valid access log lines are correctly parsed with timestamps and status codes."""
    line = '198.51.100.42 - admin [19/Oct/2026:14:15:01 +0000] "POST /api/v1/auth/login HTTP/1.1" 401 128 "-" "python-requests/2.28"'
    parser = NginxAccessLogParser()
    event = parser.parse_line(line)

    assert event is not None
    assert event.client_ip == "198.51.100.42"
    assert event.status_code == 401
    assert event.is_auth_failure is True
    assert event.method == "POST"
    assert event.uri == "/api/v1/auth/login"
    assert event.timestamp.year == 2026
    assert event.timestamp.month == 10
    assert event.timestamp.day == 19
    assert event.timestamp.hour == 14
    assert event.timestamp.minute == 15
    assert event.timestamp.second == 1


def test_nginx_access_log_parser_uri_redaction():
    """Confirms query strings and tokens in URIs are safely redacted to preserve privacy."""
    line = '198.51.100.42 - - [19/Oct/2026:14:15:01 +0000] "GET /api/v1/user/profile?token=SECRET_AUTH_KEY_999&session=xyz123 HTTP/1.1" 200 512 "-" "-"'
    parser = NginxAccessLogParser()
    event = parser.parse_line(line)

    assert event is not None
    assert event.uri == "/api/v1/user/profile"
    assert "SECRET_AUTH_KEY_999" not in event.uri
    assert "SECRET_AUTH_KEY_999" not in event.message
    assert "SECRET_AUTH_KEY_999" not in event.raw_line
    assert "[REDACTED]" in event.raw_line



def test_nginx_access_log_parser_malformed():
    """Malformed or corrupt access log lines are isolated without raising exceptions."""
    lines = [
        '# Valid header comment',
        'MALFORMED_LINE_WITHOUT_IP_OR_BRACKETS - - garbage HTTP text',
        '198.51.100.99 - - [INVALID_DATE_FORMAT] "GET /test HTTP/1.1" 200 123 "-" "curl/7.68.0"',
        '192.0.2.10 - - [19/Oct/2026:14:10:00 +0000] "GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
    ]
    parser = NginxAccessLogParser()
    result = parser.parse(lines)

    assert result.parsed_count == 1
    assert result.malformed_count == 2
    assert result.events[0].client_ip == "192.0.2.10"
    # Inspect malformed line metadata
    malformed_line_nos = [m[0] for m in result.malformed_lines]
    assert 2 in malformed_line_nos
    assert 3 in malformed_line_nos


def test_nginx_error_log_parser_auth_failure():
    """Error log lines with password mismatches or auth errors are flagged."""
    line = '2026/10/19 14:15:05 [error] 1002#1002: *105 user "admin": password mismatch, client: 198.51.100.42, server: api.internal, request: "POST /api/v1/auth/login HTTP/1.1"'
    parser = NginxErrorLogParser()
    event = parser.parse_line(line)

    assert event is not None
    assert event.client_ip == "198.51.100.42"
    assert event.is_auth_failure is True
    assert event.timestamp.hour == 14
    assert event.timestamp.minute == 15


def test_modsecurity_parser_text_and_json():
    """ModSecurity parser supports both native text format and JSON event formats."""
    text_line = '[2026-10-19 14:15:08 +0000] [client 198.51.100.42] ModSecurity: Access denied with code 403 (phase 2). [id "200002"] [msg "Excessive Auth Failures"]'
    json_line = '{"timestamp": "2026-10-19T14:15:10Z", "client_ip": "198.51.100.42", "status": 403, "rule_id": 200002, "message": "Excessive Failed Logins", "action": "alert"}'

    parser = ModSecurityParser()

    ev_text = parser.parse_line(text_line)
    assert ev_text is not None
    assert ev_text.client_ip == "198.51.100.42"
    assert ev_text.rule_id == "200002"
    assert ev_text.is_waf_alert is True
    assert ev_text.status_code == 403

    ev_json = parser.parse_line(json_line)
    assert ev_json is not None
    assert ev_json.client_ip == "198.51.100.42"
    assert ev_json.rule_id == "200002"
    assert ev_json.is_waf_alert is True
    assert ev_json.status_code == 403


# ---------------------------------------------------------------------------
# 2. Correlation Logic & Time Windows
# ---------------------------------------------------------------------------

def test_correlator_ip_and_time_window():
    """Correlator strictly matches IP and filters events within temporal window."""
    t_flow = datetime(2026, 10, 19, 14, 15, 0, tzinfo=timezone.utc)

    # Event 1: Inside window (t_flow + 5s), matching IP
    e_inside = LogEvent(
        timestamp=t_flow + timedelta(seconds=5),
        client_ip="198.51.100.42",
        log_type="nginx_access",
        status_code=401,
        is_auth_failure=True,
    )
    # Event 2: Outside window (t_flow + 120s), matching IP
    e_outside = LogEvent(
        timestamp=t_flow + timedelta(seconds=120),
        client_ip="198.51.100.42",
        log_type="nginx_access",
        status_code=401,
        is_auth_failure=True,
    )
    # Event 3: Inside window, different IP
    e_other_ip = LogEvent(
        timestamp=t_flow + timedelta(seconds=2),
        client_ip="10.0.0.99",
        log_type="nginx_access",
        status_code=401,
        is_auth_failure=True,
    )

    correlator = LogFlowCorrelator(
        events=[e_inside, e_outside, e_other_ip],
        time_window_seconds=30.0
    )

    flow = {
        "Flow ID": "test-flow-window",
        "Source IP": "198.51.100.42",
        "Timestamp": t_flow.isoformat(),
        "Flow Duration": 5000000,  # 5 seconds
    }

    summary = correlator.correlate_flow(flow)
    assert summary.correlation_successful is True
    assert summary.matched_events_count == 1
    assert summary.signals["auth_failures"] == 1


def test_correlator_unavailable_evidence_on_missing_fields():
    """Missing Source IP or Timestamp keeps confirming signals explicitly unavailable."""
    correlator = LogFlowCorrelator(
        events=[
            LogEvent(
                timestamp=datetime.now(timezone.utc),
                client_ip="198.51.100.42",
                log_type="nginx_access",
                status_code=401,
                is_auth_failure=True
            )
        ]
    )

    # Case A: Missing Source IP
    flow_no_ip = {
        "Flow ID": "test-no-ip",
        "Timestamp": "2026-10-19T14:15:00Z",
    }
    sum_no_ip = correlator.correlate_flow(flow_no_ip)
    assert sum_no_ip.correlation_successful is False
    assert sum_no_ip.signals["auth_failures"] is None
    assert sum_no_ip.signals["request_rate"] is None
    assert any("Source IP" in n for n in sum_no_ip.notes)

    # Case B: Missing Timestamp
    flow_no_time = {
        "Flow ID": "test-no-time",
        "Source IP": "198.51.100.42",
    }
    sum_no_time = correlator.correlate_flow(flow_no_time)
    assert sum_no_time.correlation_successful is False
    assert sum_no_time.signals["auth_failures"] is None
    assert any("Flow Timestamp" in n for n in sum_no_time.notes)


# ---------------------------------------------------------------------------
# 3. Scenario 1: Slow-rate Brute Force Attempt
# ---------------------------------------------------------------------------

def test_scenario_1_slow_bruteforce(guard):
    """Slow-rate Brute Force requires auth-failure confirmation for incident escalation."""
    sample_path = Path("scratch/sample_flows.csv")
    df_src = pd.read_csv(sample_path)
    bf_flow = df_src.iloc[0:1].copy()
    bf_flow["Label"] = "BruteForce"
    bf_flow["Source IP"] = "198.51.100.42"
    bf_flow["Timestamp"] = "2026-10-19T14:15:00Z"
    bf_flow["Flow Duration"] = 15000000  # 15s

    # Generate 8 auth failure events in access log
    t_start = datetime(2026, 10, 19, 14, 15, 0, tzinfo=timezone.utc)
    events = [
        LogEvent(
            timestamp=t_start + timedelta(seconds=i),
            client_ip="198.51.100.42",
            log_type="nginx_access",
            status_code=401,
            is_auth_failure=True
        )
        for i in range(1, 9)
    ]

    correlator = LogFlowCorrelator(events=events, time_window_seconds=30.0)
    signals_list, summaries = correlator.correlate_batch(bf_flow)

    assert summaries[0].signals["auth_failures"] == 8
    assert summaries[0].signals["request_rate"] < 1.0  # Slow rate

    # Analyze WITH correlated signals -> Escalates to CRITICAL
    resp_with = guard.analyze_flows(bf_flow, signals=signals_list)
    alert_with = resp_with.alerts[0]
    assert alert_with.confirming_signals["auth_failures"].confirmed is True
    assert alert_with.risk_tier == RiskTier.CRITICAL
    assert alert_with.recommended_action == RecommendedAction.ESCALATE_TO_ANALYST
    assert any("BruteForce protocol confirmation satisfied" in n for n in alert_with.policy_notes)

    # Analyze WITHOUT signals -> De-escalates to HIGH / INVESTIGATE_FLOW
    resp_without = guard.analyze_flows(bf_flow, signals=None)
    alert_without = resp_without.alerts[0]
    assert alert_without.risk_tier == RiskTier.HIGH
    assert alert_without.recommended_action == RecommendedAction.INVESTIGATE_FLOW
    assert any("BruteForce protocol guardrail applied" in n for n in alert_without.policy_notes)


# ---------------------------------------------------------------------------
# 4. Scenario 2: Benign Traffic Burst
# ---------------------------------------------------------------------------

def test_scenario_2_benign_traffic_burst(guard):
    """Benign traffic burst alone does NOT trigger incident escalation without attack confirmation."""
    sample_path = Path("data/samples/logs/synthetic_flows.csv")
    df_src = pd.read_csv(sample_path)
    benign_flow = df_src[df_src["Flow ID"] == "flow-scenario-2-benign-burst"].copy()


    # Generate 75 benign HTTP 200 requests (burst)
    t_start = datetime(2026, 10, 19, 14, 20, 0, tzinfo=timezone.utc)
    events = [
        LogEvent(
            timestamp=t_start,
            client_ip="203.0.113.88",
            log_type="nginx_access",
            status_code=200,
            is_auth_failure=False,
            is_waf_alert=False
        )
        for _ in range(75)
    ]

    correlator = LogFlowCorrelator(events=events, time_window_seconds=30.0)
    signals_list, summaries = correlator.correlate_batch(benign_flow)

    assert summaries[0].signals["request_rate"] == 75.0
    assert summaries[0].signals["auth_failures"] == 0
    assert summaries[0].signals["waf_alert"] is False

    response = guard.analyze_flows(benign_flow, signals=signals_list)
    alert = response.alerts[0]

    # Verify that burst is confirmed but does not cause incident escalation (CRITICAL)
    assert alert.confirming_signals["request_rate"].confirmed is True
    assert alert.confirming_signals["auth_failures"].confirmed is False
    assert alert.risk_tier != RiskTier.CRITICAL
    assert alert.recommended_action in [RecommendedAction.MONITOR, RecommendedAction.ALLOW]


# ---------------------------------------------------------------------------
# 5. API Integration & Demo Endpoint
# ---------------------------------------------------------------------------

def test_api_correlate_and_score():
    """POST /api/v1/correlate_and_score integrates log parsing, correlation, and scoring."""
    sample_path = Path("scratch/sample_flows.csv")
    df_src = pd.read_csv(sample_path)
    flow_rec = df_src.iloc[0].to_dict()
    flow_rec["Source IP"] = "198.51.100.42"
    flow_rec["Timestamp"] = "2026-10-19T14:15:00Z"
    flow_rec["Flow Duration"] = 10000000
    flow_rec["Label"] = "BruteForce"

    access_log = (
        '198.51.100.42 - admin [19/Oct/2026:14:15:01 +0000] "POST /login HTTP/1.1" 401 128 "-" "-"\n'
        '198.51.100.42 - admin [19/Oct/2026:14:15:02 +0000] "POST /login HTTP/1.1" 401 128 "-" "-"\n'
        '198.51.100.42 - admin [19/Oct/2026:14:15:03 +0000] "POST /login HTTP/1.1" 401 128 "-" "-"\n'
        '198.51.100.42 - admin [19/Oct/2026:14:15:04 +0000] "POST /login HTTP/1.1" 401 128 "-" "-"\n'
        '198.51.100.42 - admin [19/Oct/2026:14:15:05 +0000] "POST /login HTTP/1.1" 401 128 "-" "-"\n'
    )

    req = CorrelateAndScoreRequest(
        flows=flow_rec,
        access_logs=access_log,
        time_window_seconds=30.0,
        persist_to_queue=False
    )

    resp = correlate_and_score_flows(req)
    assert resp.alerts_generated == 1
    alert = resp.alerts[0]
    assert alert.confirming_signals["auth_failures"].value == 5
    assert alert.confirming_signals["auth_failures"].confirmed is True


def test_api_phase3_demo_endpoint_idempotence():
    """POST /api/v1/demo/phase3 is idempotent by default and respects batch identity."""
    res1 = run_phase3_demo_endpoint(force=False, batch_id="phase3-test-batch")
    count1 = res1.returned_count

    # Second call with same batch_id should not duplicate
    res2 = run_phase3_demo_endpoint(force=False, batch_id="phase3-test-batch")
    assert res2.returned_count == count1
