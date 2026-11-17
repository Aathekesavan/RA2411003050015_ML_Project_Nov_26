"""Tests for SentinelX Operating Modes, Enforcement Adapters, and Lab Isolation.

Verifies:
1. Default OFF behavior: Both global blocking and per-site blocking are OFF by default.
2. Emergency Stop: Immediate, unconditional override halting all enforcement.
3. Mode 1 Mock Adapter: Cleanly labeled as SIMULATED with zero real network action.
4. Independent Evidence Invariant: Model scores alone cannot cause a block.
5. BruteForce Guardrail: Authentication confirmation (>= 5 failures) strictly required.
6. Trusted Client Allowlist: Exemption from enforcement for allowlisted IPs.
7. Ephemeral Action Expiry: Time-to-live (TTL) expiration automatically unblocks targets.
8. Mode 2 Lab Isolation: Separate allowlists, configurations, and adapter state from Mode 1.
9. Replica Defense: Blocked clients receive HTTP 403 on replica routes until release.
10. Geo-IP Privacy Invariant: Location is never inferred without authorized source.
11. API Endpoints: Enforcement configuration, per-site toggles, block management, and audit logs.
"""

import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest
from fastapi import HTTPException
import pandas as pd

from src.guard.engine import SentinelGuard
from src.alerts.schema import RiskTier, RecommendedAction, FlowAlert, ScoresBreakdown, ConfirmingSignalEvidence
from src.enforcement.models import (
    OperatingMode,
    EnforcementAction,
    EnforcementStatus,
    SiteConfig,
    ActiveBlock,
    GlobalEnforcementConfig,
)
from src.enforcement.adapters.mock_real import MockRealSiteAdapter
from src.enforcement.adapters.local_replica import LocalReplicaAdapter
from src.enforcement.policy import (
    EnforcementPolicyEngine,
    get_default_enforcement_engine,
    set_default_enforcement_engine,
)
from src.replica.app import (
    replica_login,
    replica_portal,
    replica_admin_decoy,
    ReplicaLoginRequest,
    set_replica_adapter,
    get_replica_adapter,
    set_trusted_proxies,
    reset_trusted_proxies,
)
from src.replica.honeypot import (
    record_honeypot_interaction,
    get_honeypot_events,
    clear_honeypot_events,
)
from src.replica.scenarios import (
    run_replica_bruteforce_scenario,
    run_replica_benign_burst_scenario,
    run_replica_honeypot_scenario,
)
from src.guard.confirming_signals import evaluate_confirming_signals
from src.api.service import (
    get_enforcement_config,
    update_enforcement_config,
    update_site_config,
    list_active_blocks,
    release_active_block,
    get_enforcement_audit,
    run_replica_scenario_endpoint,
    get_scenario_comparison_endpoint,
    reset_scenario_endpoint,
    presentation_redirect,
    UpdateGlobalConfigRequest,
    UpdateSiteConfigRequest,
    ReleaseBlockRequest,
    RunReplicaScenarioRequest,
    health_check,
)
from src.replica.counterfactual import get_counterfactual_comparison, reset_demo_scenario
from src.alerts.store import LocalReviewStore


@pytest.fixture
def clean_engine():
    """Provides a fresh, isolated EnforcementPolicyEngine instance with default settings."""
    engine = EnforcementPolicyEngine()
    set_default_enforcement_engine(engine)
    return engine


@pytest.fixture
def mock_attack_alert():
    """Generates a test FlowAlert with high model scores."""
    scores = ScoresBreakdown(
        supervised_score=0.92,
        autoencoder_score=0.88,
        production_score=0.95,
        gated_activation=True,
        tau=0.56,
        gamma=0.41,
    )
    return FlowAlert(
        alert_id="test-attack-uuid-1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        flow_id="flow-test-attack",
        risk_tier=RiskTier.CRITICAL,
        recommended_action=RecommendedAction.ESCALATE_TO_ANALYST,
        autonomous_blocking_authorized=False,
        scores=scores,
        confirming_signals={},
        suspected_family="PortScan",
        policy_notes=["Test attack alert"],
    )


# ---------------------------------------------------------------------------
# 1. Default Settings & Emergency Stop Tests
# ---------------------------------------------------------------------------

def test_default_settings_all_blocking_off(clean_engine, mock_attack_alert):
    """Enforcement is strictly OFF by default at both global and per-site levels."""
    assert clean_engine.config.global_blocking_enabled is False
    assert clean_engine.config.emergency_stop_active is False
    for site in clean_engine.config.sites.values():
        assert site.blocking_enabled is False

    # Attempt enforcement evaluation
    decision = clean_engine.evaluate_and_enforce(
        alert=mock_attack_alert,
        target_ip="198.51.100.99",
        site_id="prod-portal-alpha",
    )
    assert decision.allowed_to_block is False
    assert decision.status == EnforcementStatus.DISALLOWED_OFF
    assert decision.action == EnforcementAction.MONITOR_ONLY
    assert "Global blocking enable toggle is OFF" in decision.reason


def test_emergency_stop_overrides_all_settings(clean_engine, mock_attack_alert):
    """Emergency stop immediately halts enforcement even when all toggles are ON."""
    clean_engine.config.global_blocking_enabled = True
    clean_engine.config.sites["prod-portal-alpha"].blocking_enabled = True
    clean_engine.config.emergency_stop_active = True

    # Add confirmed signal
    mock_attack_alert.confirming_signals = {
        "waf_event": ConfirmingSignalEvidence(
            signal_name="waf_event", present=True, value=1.0, threshold=1.0, confirmed=True, description="WAF rule triggered"
        )
    }

    decision = clean_engine.evaluate_and_enforce(
        alert=mock_attack_alert,
        target_ip="198.51.100.99",
        site_id="prod-portal-alpha",
    )
    assert decision.allowed_to_block is False
    assert decision.status == EnforcementStatus.DISALLOWED_EMERGENCY_STOP
    assert decision.action == EnforcementAction.MONITOR_ONLY
    assert "Emergency stop is activated" in decision.reason


# ---------------------------------------------------------------------------
# 2. Mode 1 Mock Adapter & Independent Evidence Invariant Tests
# ---------------------------------------------------------------------------

def test_mode1_mock_adapter_simulated_status(clean_engine, mock_attack_alert):
    """Eligible Mode 1 blocks use MockRealSiteAdapter and are explicitly SIMULATED."""
    clean_engine.config.global_blocking_enabled = True
    clean_engine.config.emergency_stop_active = False
    site = clean_engine.config.sites["prod-portal-alpha"]
    site.blocking_enabled = True

    # Independent WAF event confirmation
    mock_attack_alert.confirming_signals = {
        "waf_event": ConfirmingSignalEvidence(
            signal_name="waf_event", present=True, value=1.0, threshold=1.0, confirmed=True, description="SQLi Rule 942100"
        )
    }

    decision = clean_engine.evaluate_and_enforce(
        alert=mock_attack_alert,
        target_ip="198.51.100.55",
        site_id="prod-portal-alpha",
    )

    assert decision.allowed_to_block is True
    assert decision.action == EnforcementAction.BLOCK
    assert decision.status == EnforcementStatus.SIMULATED
    assert decision.is_simulated is True
    assert decision.active_block is not None
    assert decision.active_block.metadata["real_network_action"] is False
    assert "Zero network commands" in decision.active_block.metadata["simulation_notice"]

    # Verify adapter state
    adapter = clean_engine.get_adapter("mock_real_adapter")
    assert adapter.is_ip_blocked("198.51.100.55") is True


def test_independent_evidence_required_model_alone_rejected(clean_engine, mock_attack_alert):
    """Model scores alone CANNOT cause a block; independent evidence is mandatory."""
    clean_engine.config.global_blocking_enabled = True
    clean_engine.config.emergency_stop_active = False
    clean_engine.config.sites["prod-portal-alpha"].blocking_enabled = True

    # Alert has production score 0.95, but NO confirming signals
    mock_attack_alert.confirming_signals = {
        "waf_event": ConfirmingSignalEvidence(signal_name="waf_event", present=False, value=None, threshold=1.0, confirmed=None, description="Unavailable"),
        "auth_failures": ConfirmingSignalEvidence(signal_name="auth_failures", present=False, value=None, threshold=5.0, confirmed=None, description="Unavailable"),
    }

    decision = clean_engine.evaluate_and_enforce(
        alert=mock_attack_alert,
        target_ip="198.51.100.66",
        site_id="prod-portal-alpha",
    )
    assert decision.allowed_to_block is False
    assert decision.status == EnforcementStatus.DISALLOWED_NO_EVIDENCE
    assert decision.policy_rule == "MODEL_ALONE_REJECTED"
    assert "Model score alone cannot authorize blocking" in decision.reason


def test_bruteforce_auth_confirmation_guardrail(clean_engine, mock_attack_alert):
    """BruteForce attacks strictly require confirmed authentication failures (>= 5)."""
    clean_engine.config.global_blocking_enabled = True
    clean_engine.config.emergency_stop_active = False
    clean_engine.config.sites["prod-portal-alpha"].blocking_enabled = True
    mock_attack_alert.suspected_family = "BruteForce"

    # Case A: Auth failures unconfirmed (< 5 attempts)
    mock_attack_alert.confirming_signals = {
        "auth_failures": ConfirmingSignalEvidence(
            signal_name="auth_failures", present=True, value=2.0, threshold=5.0, confirmed=False, description="Only 2 failures"
        )
    }
    decision_unconfirmed = clean_engine.evaluate_and_enforce(
        alert=mock_attack_alert,
        target_ip="198.51.100.70",
        site_id="prod-portal-alpha",
    )
    assert decision_unconfirmed.allowed_to_block is False
    assert decision_unconfirmed.policy_rule == "BRUTEFORCE_GUARDRAIL_UNCONFIRMED"

    # Case B: Auth failures confirmed (>= 5 attempts)
    mock_attack_alert.confirming_signals = {
        "auth_failures": ConfirmingSignalEvidence(
            signal_name="auth_failures", present=True, value=7.0, threshold=5.0, confirmed=True, description="7 failures"
        )
    }
    decision_confirmed = clean_engine.evaluate_and_enforce(
        alert=mock_attack_alert,
        target_ip="198.51.100.70",
        site_id="prod-portal-alpha",
    )
    assert decision_confirmed.allowed_to_block is True
    assert decision_confirmed.status == EnforcementStatus.SIMULATED


# ---------------------------------------------------------------------------
# 3. Trusted Client Allowlist & TTL Expiry Tests
# ---------------------------------------------------------------------------

def test_trusted_client_allowlist_bypass(clean_engine, mock_attack_alert):
    """Allowlisted clients are strictly exempt from automated enforcement."""
    clean_engine.config.global_blocking_enabled = True
    clean_engine.config.emergency_stop_active = False
    site = clean_engine.config.sites["prod-portal-alpha"]
    site.blocking_enabled = True
    site.trusted_allowlist.append("198.51.100.10")

    mock_attack_alert.confirming_signals = {
        "waf_event": ConfirmingSignalEvidence(signal_name="waf_event", present=True, value=1.0, threshold=1.0, confirmed=True, description="WAF rule triggered")
    }

    decision = clean_engine.evaluate_and_enforce(
        alert=mock_attack_alert,
        target_ip="198.51.100.10",
        site_id="prod-portal-alpha",
    )
    assert decision.allowed_to_block is False
    assert decision.status == EnforcementStatus.ALLOWLISTED_BYPASS
    assert decision.policy_rule == "TRUSTED_ALLOWLIST_BYPASS"


def test_temporary_action_ttl_expiry():
    """Active blocks expire automatically when their TTL elapses."""
    adapter = MockRealSiteAdapter()
    target_ip = "198.51.100.123"

    # Apply ephemeral block with 1-second TTL
    adapter.apply_block(target_ip=target_ip, site_id="test-site", duration_seconds=1, reason="Test TTL")
    assert adapter.is_ip_blocked(target_ip) is True
    assert len(adapter.get_active_blocks()) == 1

    # Wait 1.1s for expiration
    time.sleep(1.1)

    assert adapter.is_ip_blocked(target_ip) is False
    assert len(adapter.get_active_blocks()) == 0


# ---------------------------------------------------------------------------
# 4. Mode 2 Lab Isolation & Replica Defense Tests
# ---------------------------------------------------------------------------

def test_mode2_lab_isolation_from_mode1(clean_engine):
    """Mode 2 replica configurations, allowlists, and adapter states are strictly isolated from Mode 1."""
    mode1_site = clean_engine.config.sites["prod-portal-alpha"]
    replica_site = clean_engine.config.replica_site

    # Ensure separate allowlists
    assert mode1_site.trusted_allowlist != replica_site.trusted_allowlist

    # Block an IP on the local replica adapter
    rep_adapter = clean_engine.get_adapter("local_replica_adapter")
    mock_adapter = clean_engine.get_adapter("mock_real_adapter")

    test_ip = "192.0.2.99"
    rep_adapter.apply_block(test_ip, site_id=replica_site.site_id, duration_seconds=60, reason="Lab test")

    assert rep_adapter.is_ip_blocked(test_ip) is True
    # Invariant: Block must NOT exist in Mode 1 mock adapter
    assert mock_adapter.is_ip_blocked(test_ip) is False


def test_mode2_replica_defense_blocks_and_expires(clean_engine):
    """Mode 2 Slow-Rate Brute Force defense blocks the attacker on the replica application."""
    res = run_replica_bruteforce_scenario(engine=clean_engine)
    assert res["operating_mode"] == "MODE_2_REPLICA_DEFENSE"
    assert res["status"] == "REPLICA"
    assert res["allowed_to_block"] is True
    assert res["replica_is_blocked"] is True
    assert res["is_simulated"] is False  # Real enforcement against the local lab testbed
    assert res["active_block"]["ttl_seconds"] == 15

    # Test that replica login route denies access with HTTP 403
    rep_adapter = clean_engine.get_adapter("local_replica_adapter")
    set_replica_adapter(rep_adapter)

    from unittest.mock import MagicMock
    req_mock = MagicMock()
    req_mock.client.host = res["target_ip"]

    login_req = ReplicaLoginRequest(
        username="admin",
        password="SomePassword!",
        client_ip=res["target_ip"],
    )

    with pytest.raises(HTTPException) as exc_info:
        replica_login(login_req, req_mock)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"] == "ACCESS_BLOCKED"

    # Manually release block and verify access returns to normal
    clean_engine.release_block(res["target_ip"])
    assert rep_adapter.is_ip_blocked(res["target_ip"]) is False

    with pytest.raises(HTTPException) as exc_info2:
        replica_login(login_req, req_mock)
    # Returns 401 (invalid password) instead of 403 (blocked)
    assert exc_info2.value.status_code == 401
    assert exc_info2.value.detail["error"] == "INVALID_CREDENTIALS"


def test_geo_ip_privacy_invariant(clean_engine, mock_attack_alert):
    """Enforcement decisions never guess or infer geo-location from raw IP without authorized source."""
    decision = clean_engine.evaluate_and_enforce(
        alert=mock_attack_alert,
        target_ip="198.51.100.88",
        site_id="prod-portal-alpha",
    )
    assert "Unverified / Not Authorized" in decision.geo_privacy_notice


# ---------------------------------------------------------------------------
# 5. Service API Endpoints Tests
# ---------------------------------------------------------------------------

def test_enforcement_api_endpoints(clean_engine):
    """Validates FastAPI enforcement and scenario management endpoints."""
    # 1. Health check reports mode and blocking state
    h = health_check()
    assert h["operating_mode"] in ["MODE_1_REAL_SITE", "MODE_2_REPLICA_DEFENSE"]
    assert h["global_blocking_enabled"] is False
    assert h["emergency_stop_active"] is False

    # 2. Get and update global enforcement config
    cfg = get_enforcement_config()
    assert cfg["global_blocking_enabled"] is False

    updated_cfg = update_enforcement_config(
        UpdateGlobalConfigRequest(global_blocking_enabled=True, operating_mode=OperatingMode.MODE_2_REPLICA_DEFENSE)
    )
    assert updated_cfg["global_blocking_enabled"] is True
    assert updated_cfg["operating_mode"] == OperatingMode.MODE_2_REPLICA_DEFENSE.value

    # 3. Update per-site config
    site_res = update_site_config(
        "prod-portal-alpha",
        UpdateSiteConfigRequest(blocking_enabled=True, block_ttl_seconds=120)
    )
    assert site_res["blocking_enabled"] is True
    assert site_res["block_ttl_seconds"] == 120

    # 4. Trigger replica scenario
    scen_res = run_replica_scenario_endpoint(RunReplicaScenarioRequest(scenario_name="benign_burst"))
    assert scen_res["scenario"] == "Mode 2 Benign Administrative Burst"
    assert scen_res["allowed_to_block"] is False

    # 5. List and release blocks
    blocks_res = list_active_blocks()
    assert "blocks" in blocks_res

    # 6. Audit log
    audit_res = get_enforcement_audit(limit=10)
    assert "records" in audit_res
    assert audit_res["audit_count"] >= 1


def test_enforcement_mutation_security_safeguard():
    """Verifies that non-local callers without an admin key are rejected with HTTP 403."""
    from src.api.service import require_local_or_admin

    class MockRemoteClient:
        host = "192.168.1.100"

    class MockRemoteRequest:
        client = MockRemoteClient()
        headers = {}

    with pytest.raises(HTTPException) as exc_info:
        require_local_or_admin(MockRemoteRequest())

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error"] == "FORBIDDEN_REMOTE_ENFORCEMENT_MUTATION"

    # Localhost allowed
    class MockLocalClient:
        host = "127.0.0.1"

    class MockLocalRequest:
        client = MockLocalClient()
        headers = {}

    assert require_local_or_admin(MockLocalRequest()) is True


def test_replica_client_identity_spoofing_prevented(clean_engine):
    """Verifies that callers cannot spoof ?client_ip= or arbitrary X-Forwarded-For

    to bypass replica blocks or impersonate allowlisted identities.
    """
    rep_adapter = clean_engine.get_adapter("local_replica_adapter")
    set_replica_adapter(rep_adapter)
    reset_trusted_proxies()

    blocked_ip = "127.0.0.1"
    rep_adapter.apply_block(
        target_ip=blocked_ip,
        site_id="lab-replica-site",
        duration_seconds=60,
        reason="Test client block",
    )

    class MockSpoofingClient:
        host = "127.0.0.1"

    # 1. Attacker attempts to bypass block by passing allowlisted admin in query param ?client_ip=10.0.0.99
    class MockQuerySpoofRequest:
        client = MockSpoofingClient()
        headers = {}
        query_params = {"client_ip": "10.0.0.99"}
        url = type("Url", (), {"path": "/replica/portal"})()

    with pytest.raises(HTTPException) as exc_info:
        replica_portal(MockQuerySpoofRequest())
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["status"] == "REPLICA_BLOCKED"
    assert exc_info.value.detail["target_ip"] == "127.0.0.1"

    # 2. Attacker attempts to bypass block by passing allowlisted admin in X-Forwarded-For header
    class MockHeaderSpoofRequest:
        client = MockSpoofingClient()
        headers = {"X-Forwarded-For": "10.0.0.99"}
        query_params = {}
        url = type("Url", (), {"path": "/replica/portal"})()

    with pytest.raises(HTTPException) as exc_info2:
        replica_portal(MockHeaderSpoofRequest())
    assert exc_info2.value.status_code == 403
    assert exc_info2.value.detail["status"] == "REPLICA_BLOCKED"
    assert exc_info2.value.detail["target_ip"] == "127.0.0.1"

    # 3. Attacker attempts to bypass block on login with spoofed payload client_ip
    login_req = ReplicaLoginRequest(username="admin", password="WrongPassword123!", client_ip="10.0.0.99")
    with pytest.raises(HTTPException) as exc_info3:
        replica_login(login_req, MockHeaderSpoofRequest())
    assert exc_info3.value.status_code == 403
    assert exc_info3.value.detail["status"] == "REPLICA_BLOCKED"


def test_trusted_proxy_configuration():
    """Verifies that X-Forwarded-For is only honored when connecting host is in trusted proxies."""
    reset_trusted_proxies()

    class MockProxyClient:
        host = "10.10.10.1"

    class MockProxyRequest:
        client = MockProxyClient()
        headers = {"X-Forwarded-For": "198.51.100.222, 10.10.10.1"}
        query_params = {}

    from src.replica.app import _extract_replica_client_ip

    # Untrusted proxy -> X-Forwarded-For is ignored, actual host used
    assert _extract_replica_client_ip(MockProxyRequest()) == "10.10.10.1"

    # Add to trusted proxies -> X-Forwarded-For is honored
    set_trusted_proxies({"10.10.10.1"})
    assert _extract_replica_client_ip(MockProxyRequest()) == "198.51.100.222"

    reset_trusted_proxies()
    assert _extract_replica_client_ip(MockProxyRequest()) == "10.10.10.1"


def test_honeypot_decoy_trap_interaction_recording_and_privacy():
    """Verifies that accessing /replica/admin-decoy logs a structured honeypot_interaction

    and NEVER stores request bodies, passwords, tokens, or form data.
    """
    clear_honeypot_events()

    class MockScoutClient:
        host = "198.51.100.88"

    class MockDecoyRequest:
        client = MockScoutClient()
        method = "POST"
        headers = {
            "Authorization": "Bearer sensitive-secret-token-xyz",
            "Cookie": "session=secret-cookie-12345",
        }
        query_params = {"submitted_token": "secret-token-token"}
        url = type("Url", (), {"path": "/replica/admin-decoy"})()

    res = replica_admin_decoy(MockDecoyRequest())
    assert res["status"] == "CHALLENGE_REQUIRED"
    assert res["route"] == "/replica/admin-decoy"

    events = get_honeypot_events()
    assert len(events) >= 1
    event = events[0]

    assert event.route == "/replica/admin-decoy"
    assert event.http_method == "POST"
    assert event.source_identity == "198.51.100.88"
    assert event.identity_type == "REAL_CONNECTION"

    # Strict Data Privacy Invariants: No body, password, token, or form fields exist
    event_dict = event.model_dump()
    for forbidden in ["password", "token", "body", "cookie", "submitted_token", "secret"]:
        assert forbidden not in event_dict, f"Forbidden sensitive field '{forbidden}' found in honeypot record!"


def test_honeypot_confirming_signal_and_mode_invariants(clean_engine):
    """Verifies honeypot creates strong independent evidence in Mode 2,

    but Mode 1 does not claim a honeypot is deployed when unconfigured.
    """
    # 1. Test signal evaluation
    signals_eval = evaluate_confirming_signals({"honeypot_interaction": True, "honeypot_route": "/replica/admin-decoy"})
    honey_sig = signals_eval["honeypot_interaction"]
    assert honey_sig.present is True
    assert honey_sig.confirmed is True
    assert "Honeypot decoy trap interaction confirmed" in honey_sig.description

    # 2. Test Mode 2 policy evaluation: Honeypot confirms independent evidence and authorizes block
    rep_adapter = clean_engine.get_adapter("local_replica_adapter")
    clean_engine.register_adapter(rep_adapter)
    clean_engine.config.operating_mode = OperatingMode.MODE_2_REPLICA_DEFENSE
    clean_engine.config.global_blocking_enabled = True
    clean_engine.config.replica_site.blocking_enabled = True

    alert = FlowAlert(
        alert_id="test-honey-alert",
        timestamp=datetime.now(timezone.utc).isoformat(),
        flow_id="honey-flow-1",
        risk_tier=RiskTier.HIGH,
        recommended_action=RecommendedAction.INVESTIGATE_FLOW,
        scores=ScoresBreakdown(
            supervised_score=0.88,
            autoencoder_score=0.75,
            production_score=0.90,
            gated_activation=True,
            tau=0.56,
            gamma=0.41,
        ),
        confirming_signals=signals_eval,
        suspected_family="Probe/Recon",
    )

    decision_mode2 = clean_engine.evaluate_and_enforce(
        alert=alert,
        target_ip="198.51.100.88",
        target_route="/replica/admin-decoy",
        site_id="lab-replica-site",
        requested_mode=OperatingMode.MODE_2_REPLICA_DEFENSE,
    )
    assert decision_mode2.action == EnforcementAction.BLOCK
    assert decision_mode2.status == EnforcementStatus.REPLICA
    assert decision_mode2.independent_evidence_confirmed is True

    # 3. Test Mode 1 policy evaluation: Monitored real sites have honeypot_enabled=False
    # Mode 1 must NOT claim a honeypot is deployed or use it for independent evidence!
    clean_engine.config.operating_mode = OperatingMode.MODE_1_REAL_SITE
    prod_site = clean_engine.get_site_config("prod-portal-alpha")
    assert prod_site.honeypot_enabled is False

    decision_mode1 = clean_engine.evaluate_and_enforce(
        alert=alert,
        target_ip="198.51.100.88",
        site_id="prod-portal-alpha",
        requested_mode=OperatingMode.MODE_1_REAL_SITE,
    )
    # Block rejected because honeypot is unavailable on prod-portal-alpha and per-site blocking is OFF
    assert decision_mode1.action == EnforcementAction.MONITOR_ONLY
    assert any("honeypot_interaction: UNAVAILABLE" in ev for ev in decision_mode1.evidence_summary)


def test_run_replica_honeypot_scenario(clean_engine):
    """Verifies that the server-side honeypot scenario runner injects simulated client identity

    and confirms automated defense against the decoy trap.
    """
    res = run_replica_honeypot_scenario(engine=clean_engine)
    assert res["scenario"] == "Mode 2 Decoy Trap Honeypot Defense"
    assert res["identity_type"] == "SIMULATED_SCENARIO"
    assert res["attacker_ip"] == "198.51.100.88"
    assert res["target_route"] == "/replica/admin-decoy"
    assert res["action"] == "BLOCK"
    assert res["status"] == "REPLICA"
    assert res["replica_probe_status"] == 403
    assert res["independent_evidence_confirmed"] is True
    assert res["active_block"]["ttl_seconds"] == 15
    assert "honeypot_event" in res
    assert res["honeypot_event"]["identity_type"] == "SIMULATED_SCENARIO"
    assert "password" not in res["honeypot_event"]
    assert "body" not in res["honeypot_event"]


def test_counterfactual_comparison_non_mutating(clean_engine):
    """Verifies that counterfactual comparison is strictly non-mutating:
    - Returns required labels: SIMULATED ATTACK, HYPOTHETICAL OUTCOME
    - Returns READY — no block active when adapter has no active block
    - Returns ALLOWLISTED_BYPASS for benign burst
    - Mode 1 is marked SIMULATED / NOT CONNECTED
    - Uses fake data for hypothetical outcome (never mutates real or replica state)
    - Leaves review database and adapter blocks strictly unchanged.
    """
    rep_adapter = clean_engine.get_adapter("local_replica_adapter")
    set_replica_adapter(rep_adapter)

    store = LocalReviewStore()
    with store._get_connection() as conn:
        initial_alerts_cnt = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        initial_reviews_cnt = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
    initial_blocks = len(rep_adapter.get_active_blocks())
    initial_global_blocking = clean_engine.config.global_blocking_enabled

    # 1. Test bruteforce scenario comparison (before run -> READY — no block active)
    comp_bf = get_counterfactual_comparison("bruteforce")
    assert comp_bf["scenario_name"] == "bruteforce"
    assert comp_bf["attack_location"]["label"] == "SIMULATED ATTACK"
    assert comp_bf["protected_outcome"]["label"] == "READY — no block active"
    assert comp_bf["protected_outcome"]["status"] == "READY_NO_BLOCK"
    assert comp_bf["protected_outcome"]["requires_scenario_run"] is True
    assert comp_bf["counterfactual_outcome"]["label"] == "HYPOTHETICAL OUTCOME"
    assert comp_bf["counterfactual_outcome"]["is_hypothetical"] is True
    assert comp_bf["counterfactual_outcome"]["simulation_type"] == "NON_MUTATING_FAKE_DATA_SIMULATION"
    assert comp_bf["counterfactual_outcome"]["hypothetical_page"] == "/replica/admin"
    assert "ACC-99201-REPLICA" in comp_bf["counterfactual_outcome"]["compromised_data"]["account_id"]
    assert comp_bf["sentinelx_telemetry"]["mode_1_status"] == "SIMULATED / NOT CONNECTED"

    # 2. Test honeypot scenario comparison (before run -> READY — no block active)
    comp_hp = get_counterfactual_comparison("honeypot")
    assert comp_hp["scenario_name"] == "honeypot"
    assert comp_hp["attack_location"]["label"] == "SIMULATED ATTACK"
    assert comp_hp["attack_location"]["target_route"] == "/replica/admin-decoy"
    assert comp_hp["protected_outcome"]["label"] == "READY — no block active"
    assert comp_hp["counterfactual_outcome"]["label"] == "HYPOTHETICAL OUTCOME"
    assert comp_hp["sentinelx_telemetry"]["mode_1_status"] == "SIMULATED / NOT CONNECTED"

    # 3. Test benign_burst scenario comparison (allowlisted bypass)
    comp_bb = get_counterfactual_comparison("benign_burst")
    assert comp_bb["scenario_name"] == "benign_burst"
    assert comp_bb["attack_location"]["label"] == "SIMULATED ATTACK"
    assert comp_bb["attack_location"]["simulated_source_ip"] == "10.0.0.99"
    assert comp_bb["protected_outcome"]["label"] == "ALLOWLISTED_BYPASS"
    assert comp_bb["protected_outcome"]["status"] == "ALLOWLISTED_BYPASS"
    assert comp_bb["protected_outcome"]["http_status"] == 200
    assert comp_bb["protected_outcome"]["is_real_replica_enforced"] is False
    assert comp_bb["counterfactual_outcome"]["label"] == "HYPOTHETICAL OUTCOME"

    # 4. Verify non-mutating guarantee
    with store._get_connection() as conn:
        after_alerts_cnt = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        after_reviews_cnt = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]

    assert after_alerts_cnt == initial_alerts_cnt, "Counterfactual comparison modified alerts table!"
    assert after_reviews_cnt == initial_reviews_cnt, "Counterfactual comparison modified reviews table!"
    assert len(rep_adapter.get_active_blocks()) == initial_blocks, "Counterfactual comparison created or removed active blocks!"
    assert clean_engine.config.global_blocking_enabled == initial_global_blocking, "Counterfactual comparison altered engine configuration!"


def test_reset_demo_scenario_preserves_reviews(clean_engine):
    """Verifies that reset_demo_scenario clears only the scenario test blocks
    and leaves stored analyst review decisions and historical alerts intact.
    """
    rep_adapter = clean_engine.get_adapter("local_replica_adapter")
    set_replica_adapter(rep_adapter)

    store = LocalReviewStore()
    with store._get_connection() as conn:
        initial_alerts_cnt = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        initial_reviews_cnt = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]

    # Apply test block
    rep_adapter.apply_block(target_ip="198.51.100.77", site_id="lab-replica-site", duration_seconds=60, reason="Scenario test block")
    assert rep_adapter.is_ip_blocked("198.51.100.77") is True

    # Execute reset
    reset_res = reset_demo_scenario()
    assert reset_res["status"] == "SCENARIO_RESET_COMPLETED"
    assert "198.51.100.77" in reset_res["released_ips"]
    assert reset_res["review_database_preserved"] is True
    assert rep_adapter.is_ip_blocked("198.51.100.77") is False

    # Verify review database completely preserved
    with store._get_connection() as conn:
        after_alerts_cnt = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        after_reviews_cnt = conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]

    assert after_alerts_cnt == initial_alerts_cnt
    assert after_reviews_cnt == initial_reviews_cnt


def test_counterfactual_active_block_state(clean_engine):
    """Verifies that counterfactual comparison shows 'BLOCK ACTIVE' when the local
    replica adapter confirms an active block for the scenario source IP.
    """
    rep_adapter = clean_engine.get_adapter("local_replica_adapter")
    set_replica_adapter(rep_adapter)

    # 1. Bruteforce scenario with active block
    rep_adapter.apply_block(target_ip="198.51.100.77", site_id="lab-replica-site", duration_seconds=15, reason="BruteForce block")
    comp_bf = get_counterfactual_comparison("bruteforce")
    assert comp_bf["protected_outcome"]["label"] == "BLOCK ACTIVE"
    assert comp_bf["protected_outcome"]["status"] == "REPLICA_BLOCKED"
    assert comp_bf["protected_outcome"]["http_status"] == 403
    assert comp_bf["protected_outcome"]["is_real_replica_enforced"] is True
    assert comp_bf["protected_outcome"]["requires_scenario_run"] is False
    assert comp_bf["protected_outcome"]["ttl_seconds"] == 15
    assert comp_bf["protected_outcome"]["ttl_remaining_seconds"] > 0
    assert comp_bf["protected_outcome"]["expires_at"] is not None

    # 2. Honeypot scenario with active block
    rep_adapter.apply_block(target_ip="198.51.100.88", site_id="lab-replica-site", duration_seconds=15, reason="Honeypot decoy probe block")
    comp_hp = get_counterfactual_comparison("honeypot")
    assert comp_hp["protected_outcome"]["label"] == "BLOCK ACTIVE"
    assert comp_hp["protected_outcome"]["status"] == "REPLICA_BLOCKED"
    assert comp_hp["protected_outcome"]["http_status"] == 403
    assert comp_hp["protected_outcome"]["is_real_replica_enforced"] is True
    assert comp_hp["protected_outcome"]["requires_scenario_run"] is False
    assert comp_hp["protected_outcome"]["ttl_seconds"] == 15

    # Cleanup blocks
    reset_demo_scenario()


def test_counterfactual_no_active_block_state(clean_engine):
    """Verifies that counterfactual comparison shows 'READY — no block active'
    when no block is active, and explains that the scenario must be run first.
    """
    rep_adapter = clean_engine.get_adapter("local_replica_adapter")
    set_replica_adapter(rep_adapter)
    reset_demo_scenario()

    # Bruteforce before run
    comp_bf = get_counterfactual_comparison("bruteforce")
    assert comp_bf["protected_outcome"]["label"] == "READY — no block active"
    assert comp_bf["protected_outcome"]["status"] == "READY_NO_BLOCK"
    assert comp_bf["protected_outcome"]["is_real_replica_enforced"] is False
    assert comp_bf["protected_outcome"]["requires_scenario_run"] is True
    assert "must be run first" in comp_bf["protected_outcome"]["execution_guidance"].lower()

    # Honeypot before run
    comp_hp = get_counterfactual_comparison("honeypot")
    assert comp_hp["protected_outcome"]["label"] == "READY — no block active"
    assert comp_hp["protected_outcome"]["status"] == "READY_NO_BLOCK"
    assert comp_hp["protected_outcome"]["is_real_replica_enforced"] is False
    assert comp_hp["protected_outcome"]["requires_scenario_run"] is True


def test_counterfactual_allowlisted_benign_bypass(clean_engine):
    """Verifies that the benign-burst scenario shows that the trusted client
    was allowed (ALLOWLISTED_BYPASS), not blocked.
    """
    rep_adapter = clean_engine.get_adapter("local_replica_adapter")
    set_replica_adapter(rep_adapter)

    comp_bb = get_counterfactual_comparison("benign_burst")
    assert comp_bb["protected_outcome"]["label"] == "ALLOWLISTED_BYPASS"
    assert comp_bb["protected_outcome"]["status"] == "ALLOWLISTED_BYPASS"
    assert comp_bb["protected_outcome"]["http_status"] == 200
    assert comp_bb["protected_outcome"]["is_real_replica_enforced"] is False
    assert comp_bb["protected_outcome"]["is_allowlisted"] is True
    assert comp_bb["protected_outcome"]["requires_scenario_run"] is False
    assert "allowlist" in comp_bb["protected_outcome"]["reason"].lower()
    assert "allowlisted" in comp_bb["protected_outcome"]["execution_guidance"].lower()


def test_presentation_endpoints_and_redirection():
    """Verifies the comparison API, scenario reset endpoint, and /presentation redirect."""
    # 1. Comparison endpoint (no block initially)
    reset_scenario_endpoint()
    comp = get_scenario_comparison_endpoint(scenario_name="bruteforce")
    assert comp["scenario_name"] == "bruteforce"
    assert comp["attack_location"]["label"] == "SIMULATED ATTACK"
    assert comp["counterfactual_outcome"]["label"] == "HYPOTHETICAL OUTCOME"
    assert comp["protected_outcome"]["label"] == "READY — no block active"

    # 2. Reset endpoint
    reset_out = reset_scenario_endpoint()
    assert reset_out["status"] == "SCENARIO_RESET_COMPLETED"
    assert reset_out["review_database_preserved"] is True

    # 3. Presentation redirect
    redirect_resp = presentation_redirect()
    assert redirect_resp.status_code == 307
    assert redirect_resp.headers["location"] == "/dashboard/presentation.html"


def test_mode2_15s_ttl_and_scenario_explanations(clean_engine):
    """Verifies that Mode 2 uses 15s temporary block duration while Mode 1 remains 300s,
    brute force and honeypot scenarios apply 15s blocks with clear explanations,
    honeypot records metadata only without body/password storage,
    benign burst demonstrates allowlist bypass, and reset clears all blocks.
    """
    rep_adapter = clean_engine.get_adapter("local_replica_adapter")
    set_replica_adapter(rep_adapter)
    reset_demo_scenario()

    # 1. Mode 2 replica TTL is 15 seconds; Mode 1 sites remain default 300 seconds
    assert clean_engine.config.replica_site.block_ttl_seconds == 15
    assert clean_engine.config.sites["prod-portal-alpha"].block_ttl_seconds == 300

    # 2. Run Brute Force scenario
    bf_res = run_replica_bruteforce_scenario(engine=clean_engine)
    assert bf_res["action"] == "BLOCK"
    assert bf_res["active_block"]["ttl_seconds"] == 15
    assert rep_adapter.is_ip_blocked(bf_res["attacker_ip"]) is True
    assert bf_res["replica_probe_status"] == 403

    comp_bf = get_counterfactual_comparison("bruteforce")
    assert comp_bf["protected_outcome"]["label"] == "BLOCK ACTIVE"
    assert comp_bf["protected_outcome"]["ttl_seconds"] == 15
    assert 0 < comp_bf["protected_outcome"]["ttl_remaining_seconds"] <= 15
    assert "bruteforce" in comp_bf["attack_location"]["description"].lower() or "credential" in comp_bf["attack_location"]["description"].lower()

    # 3. Run Honeypot Decoy scenario
    hp_res = run_replica_honeypot_scenario(engine=clean_engine)
    assert hp_res["action"] == "BLOCK"
    assert hp_res["active_block"]["ttl_seconds"] == 15
    assert rep_adapter.is_ip_blocked(hp_res["attacker_ip"]) is True
    assert hp_res["replica_probe_status"] == 403
    assert hp_res["independent_evidence_confirmed"] is True

    # Honeypot privacy: metadata recorded, no body/password/tokens stored
    assert "honeypot_event" in hp_res
    event_data = hp_res["honeypot_event"]
    assert event_data["route"] == "/replica/admin-decoy"
    assert event_data["source_identity"] == "198.51.100.88"
    for forbidden in ["password", "body", "token", "cookie"]:
        assert forbidden not in event_data

    comp_hp = get_counterfactual_comparison("honeypot")
    assert comp_hp["protected_outcome"]["label"] == "BLOCK ACTIVE"
    assert comp_hp["protected_outcome"]["ttl_seconds"] == 15
    assert 0 < comp_hp["protected_outcome"]["ttl_remaining_seconds"] <= 15

    # 4. Run Benign Burst scenario (Allowlist bypass)
    bb_res = run_replica_benign_burst_scenario(engine=clean_engine)
    assert bb_res["action"] == "MONITOR_ONLY"
    assert bb_res["allowed_to_block"] is False
    assert bb_res["status"] == "ALLOWLISTED_BYPASS"
    assert rep_adapter.is_ip_blocked(bb_res["admin_ip"]) is False
    assert bb_res["replica_probe_status"] == 200

    comp_bb = get_counterfactual_comparison("benign_burst")
    assert comp_bb["protected_outcome"]["label"] == "ALLOWLISTED_BYPASS"
    assert comp_bb["protected_outcome"]["is_allowlisted"] is True
    assert comp_bb["protected_outcome"]["http_status"] == 200

    # 5. Reset demo scenario clears all temporary blocks
    reset_res = reset_demo_scenario()
    assert reset_res["status"] == "SCENARIO_RESET_COMPLETED"
    assert rep_adapter.is_ip_blocked("198.51.100.77") is False
    assert rep_adapter.is_ip_blocked("198.51.100.88") is False

    comp_after_reset = get_counterfactual_comparison("bruteforce")
    assert comp_after_reset["protected_outcome"]["label"] == "READY — no block active"
    assert comp_after_reset["protected_outcome"]["http_status"] == 200


def test_honeypot_probe_presentation_scenario(clean_engine):
    """Verifies that the Mode 2 presentation page includes the Honeypot Probe scenario,
    renders the decoy admin preview and 3-step sequence, displays metadata and 15s TTL,
    guarantees metadata-only privacy, and supports clean reset without deleting honeypot history.
    """
    rep_adapter = clean_engine.get_adapter("local_replica_adapter")
    set_replica_adapter(rep_adapter)
    reset_demo_scenario()

    # 1. Verify presentation assets contain the requested Honeypot Probe UI elements
    pres_html_path = Path("dashboard/presentation.html")
    pres_js_path = Path("dashboard/presentation.js")
    assert pres_html_path.exists()
    assert pres_js_path.exists()

    html_content = pres_html_path.read_text(encoding="utf-8")
    js_content = pres_js_path.read_text(encoding="utf-8")

    # Selector contains Honeypot probe — /replica/admin-decoy
    assert "Honeypot probe" in html_content
    assert "/replica/admin-decoy" in html_content
    assert 'value="honeypot"' in html_content

    # UI explains privacy safeguard (metadata only, no passwords/bodies saved)
    assert "Decoy Privacy Safeguard" in html_content or "Privacy Safeguard" in html_content
    assert "does not save" in html_content or "never stores" in html_content or "does not store" in html_content
    assert "metadata only" in html_content.lower()

    # Three-step progress sequence exists in presentation logic
    assert "Decoy route accessed" in js_content
    assert "Honeypot interaction confirmed" in js_content
    assert "Simulated source blocked in local replica" in js_content

    # 2. Before scenario execution, comparison returns READY — no block active
    comp_initial = get_scenario_comparison_endpoint(scenario_name="honeypot")
    assert comp_initial["scenario_name"] == "honeypot"
    assert comp_initial["attack_location"]["target_route"] == "/replica/admin-decoy"
    assert comp_initial["attack_location"]["simulated_source_ip"] == "198.51.100.88"
    assert comp_initial["protected_outcome"]["label"] == "READY — no block active"
    assert comp_initial["protected_outcome"]["http_status"] == 200

    # 3. Execute Honeypot scenario via endpoint
    req = RunReplicaScenarioRequest(scenario_name="honeypot")
    res = run_replica_scenario_endpoint(req)

    assert res["action"] == "BLOCK"
    assert res["status"] == "REPLICA"
    assert res["replica_probe_status"] == 403
    assert res["target_ip"] == "198.51.100.88"
    assert res["target_route"] == "/replica/admin-decoy"
    assert res["active_block"]["ttl_seconds"] == 15
    assert rep_adapter.is_ip_blocked("198.51.100.88") is True

    # Check actual honeypot event telemetry details
    assert "honeypot_event" in res
    event_data = res["honeypot_event"]
    assert event_data["route"] == "/replica/admin-decoy"
    assert event_data["source_identity"] == "198.51.100.88"
    assert event_data["http_method"] == "POST"
    for forbidden in ["password", "body", "token", "cookie"]:
        assert forbidden not in event_data

    # 4. While block is active, comparison endpoint reflects BLOCK ACTIVE with remaining TTL
    comp_active = get_scenario_comparison_endpoint(scenario_name="honeypot")
    assert comp_active["protected_outcome"]["label"] == "BLOCK ACTIVE"
    assert comp_active["protected_outcome"]["http_status"] == 403
    assert 0 < comp_active["protected_outcome"]["ttl_remaining_seconds"] <= 15
    assert comp_active["protected_outcome"]["expires_at"] is not None

    # 5. Reset endpoint clears active scenario blocks without deleting honeypot history
    events_before_reset = len(get_honeypot_events())
    reset_out = reset_scenario_endpoint()
    assert reset_out["status"] == "SCENARIO_RESET_COMPLETED"
    assert rep_adapter.is_ip_blocked("198.51.100.88") is False
    assert len(get_honeypot_events()) == events_before_reset  # Honeypot history preserved

    # 6. After reset, comparison is restored to READY
    comp_reset = get_scenario_comparison_endpoint(scenario_name="honeypot")
    assert comp_reset["protected_outcome"]["label"] == "READY — no block active"
    assert comp_reset["protected_outcome"]["http_status"] == 200


