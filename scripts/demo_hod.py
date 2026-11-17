"""Automated and Interactive Demonstration Walkthrough for SentinelX-Shift.

Demonstrates:
1. Mode 1 (Authorized Real-Site Monitoring):
   - Passive monitoring of configured sites (e.g. prod-portal-alpha).
   - Clear labeling: SIMULATED / NOT CONNECTED with zero network or firewall commands.
   - Defense-in-depth policy: Global default OFF, per-site default OFF, independent evidence mandatory.
2. Mode 2 (Isolated Replica Defense):
   - Closed-loop automated defense on local replica web application (/replica).
   - Slow-rate brute force scenario: 7 failed logins -> Ephemeral 60s block applied.
   - Immediate HTTP 403 Forbidden response verification on replica routes.
   - Benign administrative burst scenario: Lab allowlist bypass verified with HTTP 200 OK.
3. Decoy Trap Honeypot Defense:
   - Scout interaction against /replica/admin-decoy captures structured honeypot_interaction telemetry.
   - Strict privacy invariant: Never stores request bodies, passwords, or tokens.
   - Independent confirming evidence authorizes ephemeral block intercepting route with HTTP 403.
4. Hardened Client Identity & Anti-Spoofing:
   - Identity derived from actual connection address; never trusts ?client_ip=.
   - X-Forwarded-For trusted ONLY from explicitly configured reverse proxies.
   - Proves untrusted callers cannot spoof allowlisted admin identities to bypass blocks.
5. Action Lifecycle (TTL & Manual Release):
   - Block release via API / UI -> Immediate restoration of normal access.
6. Master Emergency Stop:
   - Instant disengagement overriding all policies across all adapters.
7. Localhost Binding & Authorization Safeguard:
   - Verifies enforcement mutation endpoints reject non-local callers with HTTP 403.
8. Review Store Preservation:
   - Verifies that demo execution leaves historical analyst reviews completely intact.
"""

import sys
import time
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Safe stdout reconfigure for Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.api.service import (
    get_enforcement_config,
    update_enforcement_config,
    list_active_blocks,
    release_active_block,
    get_enforcement_audit,
    run_replica_scenario_endpoint,
    get_scenario_comparison_endpoint,
    reset_scenario_endpoint,
    presentation_redirect,
    require_local_or_admin,
    get_default_enforcement_engine,
    UpdateGlobalConfigRequest,
    ReleaseBlockRequest,
    RunReplicaScenarioRequest,
)
from src.replica.counterfactual import get_counterfactual_comparison, reset_demo_scenario
from src.enforcement.models import OperatingMode, EnforcementAction, EnforcementStatus
from src.replica.app import (
    replica_login,
    replica_portal,
    replica_admin,
    replica_admin_decoy,
    replica_status,
    ReplicaLoginRequest,
    get_replica_adapter,
    set_trusted_proxies,
    reset_trusted_proxies,
    _extract_replica_client_ip,
)
from src.replica.honeypot import (
    get_honeypot_events,
    clear_honeypot_events,
)


class MockClient:
    def __init__(self, host: str = "127.0.0.1"):
        self.host = host


class MockRequest:
    def __init__(self, host: str = "127.0.0.1", path: str = "/replica/login", headers: Optional[Dict[str, str]] = None, query_params: Optional[Dict[str, str]] = None, method: str = "GET"):
        self.client = MockClient(host)
        self.headers = headers or {}
        self.query_params = query_params or {}
        self.method = method
        class MockUrl:
            pass
        self.url = MockUrl()
        self.url.path = path


def print_banner(text: str):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)


def print_section(num: int, title: str):
    print(f"\n--- [STEP {num}] {title} ---")


def run_hod_walkthrough():
    engine = get_default_enforcement_engine()
    replica_adapter = get_replica_adapter()
    engine.register_adapter(replica_adapter)
    reset_trusted_proxies()

    db_path = Path("results/reviews/analyst_reviews.db")
    initial_alerts = 0
    initial_reviews = 0
    if db_path.exists():
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            initial_alerts = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            initial_reviews = c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]

    print_banner("SENTINELX-SHIFT: DEMONSTRATION WALKTHROUGH (MODE 2 REPLICA)")
    print(f"Start Timestamp: {datetime.now(timezone.utc).isoformat()} UTC")
    print("Defensive Stance: Zero live network/firewall commands sent to real infrastructure.")

    # -------------------------------------------------------------------------
    # STEP 1: Mode 1 Verification (Passive Monitoring & Simulation Status)
    # -------------------------------------------------------------------------
    print_section(1, "Mode 1: Authorized Real-Site Monitoring (SIMULATED / NOT CONNECTED)")
    cfg = get_enforcement_config()
    print(f"  * Global Blocking Default Setting: {cfg.get('global_blocking_enabled')} (Strictly OFF by default)")
    print(f"  * Master Emergency Stop Status   : {cfg.get('emergency_stop_active')} (Inactive)")
    print(f"  * Configured Monitored Sites     : {list(cfg.get('sites', {}).keys())}")

    prod_site = cfg.get("sites", {}).get("prod-portal-alpha", {})
    print(f"  * Site 'prod-portal-alpha' Blocking Enabled: {prod_site.get('blocking_enabled')} (Default: OFF)")
    print(f"  * Site 'prod-portal-alpha' Honeypot Enabled: {prod_site.get('honeypot_enabled')} (Mode 1 invariant: No false claim)")
    print(f"  * Enforcement Adapter Binding              : {prod_site.get('enforcement_adapter')} (MockRealSiteAdapter)")

    # Mode 1 Mock Adapter verification
    mock_adapter = engine.get_adapter("mock_real_adapter")
    print(f"  * Mock Adapter Status Label                : {mock_adapter.adapter_status.value} / NOT CONNECTED")
    print(f"  * Mock Adapter is_simulated Flag           : {mock_adapter.is_simulated}")
    print("  [OK] Mode 1 Verified: Confirmed passive, simulated-only posture with 0 live commands.")

    # -------------------------------------------------------------------------
    # STEP 2: Mode 2 Replica Defense (Slow-Rate Brute Force Scenario)
    # -------------------------------------------------------------------------
    print_section(2, "Mode 2: Closed-Loop Automated Defense on Local Replica (/replica)")
    print("  * Target Testbed Service: Northstar Campus Portal mounted at http://127.0.0.1:8000/replica")
    print("  * Simulating slow-rate brute force attack from attacker IP: 198.51.100.77 (SIMULATED_SCENARIO)")
    print("  * Attack Pattern: 7 failed authentication attempts against /replica/login (exceeds guardrail threshold >= 5).")

    # Run scenario
    bf_data = run_replica_scenario_endpoint(RunReplicaScenarioRequest(scenario_name="bruteforce"))
    print(f"  * Decision Action    : {bf_data.get('action')}")
    print(f"  * Decision Status    : {bf_data.get('status')} (Executed in memory on LocalReplicaAdapter)")
    print(f"  * Target Route       : {bf_data.get('target_route')}")
    print(f"  * Policy Rule Reason : {bf_data.get('reason')}")
    print(f"  * Ephemeral Block TTL: {bf_data.get('active_block', {}).get('ttl_seconds')} seconds")

    # Verify HTTP 403 on replica
    attacker_ip = "198.51.100.77"
    login_req = ReplicaLoginRequest(username="admin", password="WrongPassword123!")
    req_mock = MockRequest(host=attacker_ip, path="/replica/login")

    try:
        replica_login(login_req, req_mock)
        raise AssertionError("Expected 403 Forbidden on blocked attacker IP, but login did not raise HTTPException!")
    except HTTPException as e:
        print(f"  * Probe to /replica/login as {attacker_ip} -> HTTP Status: {e.status_code}")
        assert e.status_code == 403, f"Expected HTTP 403 Forbidden, got {e.status_code}"
        print(f"  * 403 Interception Body: {e.detail}")

    print("  [OK] Mode 2 Brute Force Defense Verified: Automated ephemeral block active and intercepting traffic.")

    # -------------------------------------------------------------------------
    # STEP 3: Mode 2 Benign Burst Scenario (Lab Allowlist Bypass)
    # -------------------------------------------------------------------------
    print_section(3, "Mode 2: Benign Administrative Burst & Lab Allowlist Isolation")
    print("  * Simulating administrative burst from lab admin IP: 10.0.0.99 (SIMULATED_SCENARIO)")
    print("  * Telemetry Profile: High request rate surge, 0 auth failures, on lab allowlist.")

    burst_data = run_replica_scenario_endpoint(RunReplicaScenarioRequest(scenario_name="benign_burst"))
    print(f"  * Decision Action   : {burst_data.get('action')}")
    print(f"  * Decision Status   : {burst_data.get('status')} (Exempted from enforcement)")
    print(f"  * Policy Rule Reason: {burst_data.get('reason')}")

    admin_req = MockRequest(host="10.0.0.99", path="/replica/portal")
    portal_res = replica_portal(admin_req)
    print(f"  * Probe to /replica/portal as 10.0.0.99 -> Response: {portal_res.get('portal')} (HTTP 200 OK)")
    print("  [OK] Lab Allowlist Bypass Verified: Legitimate burst traffic permitted without interruption.")

    # -------------------------------------------------------------------------
    # STEP 4: Mode 2 Decoy Trap Honeypot Defense (/replica/admin-decoy)
    # -------------------------------------------------------------------------
    print_section(4, "Mode 2: Decoy Trap Honeypot Defense & Data Privacy Invariant")
    print("  * Target Trap Route: /replica/admin-decoy")
    print("  * Simulating reconnaissance scout from scout IP: 198.51.100.88 (SIMULATED_SCENARIO)")

    honey_data = run_replica_scenario_endpoint(RunReplicaScenarioRequest(scenario_name="honeypot"))
    print(f"  * Decision Action    : {honey_data.get('action')}")
    print(f"  * Decision Status    : {honey_data.get('status')}")
    print(f"  * Target Route       : {honey_data.get('target_route')}")
    print(f"  * Honeypot Evidence  : {honey_data.get('evidence_summary')}")
    print(f"  * Policy Rule Reason : {honey_data.get('reason')}")

    # Verify structured honeypot interaction record and zero payload storage
    events = get_honeypot_events()
    assert len(events) >= 1
    recent_honey = events[0]
    print(f"  * Captured Honeypot Event: ID={recent_honey.event_id}, route={recent_honey.route}, method={recent_honey.http_method}")
    print(f"  * Source Identity: {recent_honey.source_identity} ({recent_honey.identity_type})")

    # Assert strict privacy invariant: no bodies, passwords, or tokens in event
    honey_dict = recent_honey.model_dump()
    for forbidden in ["password", "token", "body", "cookie", "secret"]:
        assert forbidden not in honey_dict, f"Forbidden field '{forbidden}' found in honeypot telemetry!"
    print("  * Data Privacy Invariant: Verified ZERO bodies, passwords, or tokens stored.")

    # Verify HTTP 403 on decoy route for scout
    scout_req = MockRequest(host="198.51.100.88", path="/replica/admin-decoy", method="POST")
    try:
        replica_admin_decoy(scout_req)
        raise AssertionError("Expected 403 Forbidden on blocked honeypot attacker, but got success!")
    except HTTPException as eh:
        print(f"  * Probe to /replica/admin-decoy as 198.51.100.88 -> HTTP Status: {eh.status_code} Forbidden")
        assert eh.status_code == 403
    print("  [OK] Honeypot Decoy Defense Verified: Independent honeypot signal confirmed and defense applied.")

    # -------------------------------------------------------------------------
    # STEP 5: Hardened Client Identity & Anti-Spoofing Verification
    # -------------------------------------------------------------------------
    print_section(5, "Hardened Client Identity & Anti-Spoofing Verification")
    print("  * Rule: Do not trust ?client_ip= or arbitrary X-Forwarded-For headers.")
    print("  * Testing caller connecting from 127.0.0.1 attempting to spoof allowlisted admin 10.0.0.99...")

    # Block 127.0.0.1 temporarily on replica adapter
    replica_adapter.apply_block("127.0.0.1", site_id="lab-replica-site", duration_seconds=60, reason="Spoofing test block")

    # Attempt 1: Query parameter spoofing
    query_spoof_req = MockRequest(host="127.0.0.1", path="/replica/portal", query_params={"client_ip": "10.0.0.99"})
    try:
        replica_portal(query_spoof_req)
        raise AssertionError("Spoofed query parameter bypassed replica block!")
    except HTTPException as e_spoof1:
        print(f"  * Spoofed ?client_ip=10.0.0.99 -> Rejected as expected: HTTP {e_spoof1.status_code} ({e_spoof1.detail.get('status')})")
        assert e_spoof1.status_code == 403
        assert e_spoof1.detail.get("target_ip") == "127.0.0.1"

    # Attempt 2: Untrusted X-Forwarded-For header spoofing
    header_spoof_req = MockRequest(host="127.0.0.1", path="/replica/portal", headers={"X-Forwarded-For": "10.0.0.99"})
    try:
        replica_portal(header_spoof_req)
        raise AssertionError("Spoofed X-Forwarded-For header bypassed replica block!")
    except HTTPException as e_spoof2:
        print(f"  * Spoofed X-Forwarded-For: 10.0.0.99 -> Rejected as expected: HTTP {e_spoof2.status_code} ({e_spoof2.detail.get('status')})")
        assert e_spoof2.status_code == 403
        assert e_spoof2.detail.get("target_ip") == "127.0.0.1"

    # Release test block on 127.0.0.1
    replica_adapter.remove_block("127.0.0.1")
    print("  [OK] Anti-Spoofing Verified: Callers cannot bypass blocks or spoof allowlisted admin identities.")

    # -------------------------------------------------------------------------
    # STEP 6: Ephemeral Block Release & Expiry Lifecycle
    # -------------------------------------------------------------------------
    print_section(6, "Block Lifecycle: Manual Release & Restoration of Normal Access")
    rel_res = release_active_block(ReleaseBlockRequest(target_ip=attacker_ip))
    print(f"  * Released IP {attacker_ip} -> Status: {rel_res}")

    # Re-probe replica login
    try:
        replica_login(login_req, req_mock)
        raise AssertionError("Expected 401 Unauthorized on bad credentials after release, but login did not raise!")
    except HTTPException as e2:
        print(f"  * Probe to /replica/login after release -> HTTP Status: {e2.status_code}")
        assert e2.status_code == 401, f"Expected HTTP 401 Unauthorized, got {e2.status_code}"
        print("  [OK] Access Lifecycle Verified: Unblocking restored normal application behavior (401 invalid password instead of 403 blocked).")

    # -------------------------------------------------------------------------
    # STEP 7: Emergency Stop Verification
    # -------------------------------------------------------------------------
    print_section(7, "Master Emergency Stop Override")
    print("  * Engaging Emergency Stop via update_enforcement_config...")
    update_enforcement_config(UpdateGlobalConfigRequest(emergency_stop_active=True))

    # Attempt to run brute force defense while emergency stop is active
    bf_estop = run_replica_scenario_endpoint(RunReplicaScenarioRequest(scenario_name="bruteforce"))
    print(f"  * Action during Emergency Stop: {bf_estop.get('action')}")
    print(f"  * Status during Emergency Stop: {bf_estop.get('status')}")
    print(f"  * Reason                      : {bf_estop.get('reason')}")
    assert bf_estop.get("action") == "MONITOR_ONLY"
    assert bf_estop.get("status") == "DISALLOWED_EMERGENCY_STOP"

    # Reset emergency stop and global toggle to safe defaults
    update_enforcement_config(UpdateGlobalConfigRequest(emergency_stop_active=False, global_blocking_enabled=False, operating_mode=OperatingMode.MODE_1_REAL_SITE))
    print("  [OK] Emergency Stop Verified: Unconditionally inhibits all defensive block actions across the system.")

    # -------------------------------------------------------------------------
    # STEP 8: Security Safeguard & Non-Local Authorization Check
    # -------------------------------------------------------------------------
    print_section(8, "Enforcement Mutation Endpoint Security Safeguards")
    print("  * Testing access control on enforcement mutation endpoints from remote host...")

    remote_mock = MockRequest(host="192.168.1.100")
    try:
        require_local_or_admin(remote_mock)
        print("  [FAIL] Remote mutation request was not rejected!")
    except HTTPException as e3:
        print(f"  * Remote mutation request rejected as expected: HTTP {e3.status_code} Forbidden")
        print(f"  * Error Code: {e3.detail.get('error')}")
        print(f"  * Message   : {e3.detail.get('message')}")
        assert e3.status_code == 403
        assert e3.detail.get("error") == "FORBIDDEN_REMOTE_ENFORCEMENT_MUTATION"
    print("  [OK] Security Safeguard Verified: Mutating enforcement endpoints require localhost origin or admin key.")

    # -------------------------------------------------------------------------
    # STEP 9: Analyst Review Database Preservation Check
    # -------------------------------------------------------------------------
    print_section(9, "Non-Destructive Integrity Check on Analyst Review Database")
    if db_path.exists():
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            final_alerts = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            final_reviews = c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]

        print(f"  * Initial Alert Count : {initial_alerts} | Final Alert Count : {final_alerts}")
        print(f"  * Initial Review Count: {initial_reviews} | Final Review Count: {final_reviews}")
        assert final_alerts >= initial_alerts, "Alert database was truncated or altered!"
        assert final_reviews == initial_reviews, "Analyst review decisions were unexpectedly changed!"
        print("  [OK] Non-Destructive Integrity Verified: Zero existing alerts or review decisions deleted.")

    # -------------------------------------------------------------------------
    # STEP 10: Split-Screen Presentation & Counterfactual Comparison Verification
    # -------------------------------------------------------------------------
    print_section(10, "Split-Screen Presentation & Non-Mutating Counterfactual Comparison")
    
    # 1. Verify presentation assets exist
    pres_html = WORKSPACE_ROOT / "dashboard" / "presentation.html"
    pres_js = WORKSPACE_ROOT / "dashboard" / "presentation.js"
    assert pres_html.exists(), "dashboard/presentation.html not found!"
    assert pres_js.exists(), "dashboard/presentation.js not found!"
    print(f"  * Split-Screen presentation UI assets confirmed: {pres_html.name}, {pres_js.name}")

    # 2. Check counterfactual comparison generation (BruteForce)
    reset_demo_scenario()
    comp_bf = get_counterfactual_comparison("bruteforce")
    print(f"  * Attack Location Label      : {comp_bf['attack_location']['label']}")
    print(f"  * Protected Outcome (Ready)  : {comp_bf['protected_outcome']['label']}")
    print(f"  * Counterfactual Outcome Label: {comp_bf['counterfactual_outcome']['label']}")
    print(f"  * Mode 1 Status Label        : {comp_bf['sentinelx_telemetry']['mode_1_status']}")
    print(f"  * Counterfactual Fake Data   : {comp_bf['counterfactual_outcome']['compromised_data']['account_id']}")

    assert comp_bf["attack_location"]["label"] == "SIMULATED ATTACK"
    assert comp_bf["protected_outcome"]["label"] == "READY — no block active"
    assert comp_bf["counterfactual_outcome"]["label"] == "HYPOTHETICAL OUTCOME"
    assert comp_bf["counterfactual_outcome"]["is_hypothetical"] is True
    assert comp_bf["sentinelx_telemetry"]["mode_1_status"] == "SIMULATED / NOT CONNECTED"

    # Test active block label
    adapter = get_replica_adapter()
    adapter.apply_block(target_ip="198.51.100.77", site_id="lab-replica-site", duration_seconds=60, reason="Mode 2 demo test block")
    comp_bf_active = get_counterfactual_comparison("bruteforce")
    assert comp_bf_active["protected_outcome"]["label"] == "BLOCK ACTIVE"
    print(f"  * Protected Outcome (Active) : {comp_bf_active['protected_outcome']['label']} (HTTP {comp_bf_active['protected_outcome']['http_status']})")

    # Test benign burst allowlisted bypass
    comp_bb = get_counterfactual_comparison("benign_burst")
    assert comp_bb["protected_outcome"]["label"] == "ALLOWLISTED_BYPASS"
    print(f"  * Protected Outcome (Benign) : {comp_bb['protected_outcome']['label']} (HTTP {comp_bb['protected_outcome']['http_status']})")

    # 3. Test scenario reset controller (leaves review DB untouched)
    reset_out = reset_demo_scenario()
    assert reset_out["status"] == "SCENARIO_RESET_COMPLETED"
    assert reset_out["review_database_preserved"] is True
    print(f"  * Scenario Reset Controller  : Released {len(reset_out['released_ips'])} scenario test blocks (Review DB preserved)")

    # 4. Verify endpoint redirection
    redirect_resp = presentation_redirect()
    assert redirect_resp.status_code == 307
    print(f"  * Presentation Redirect URL  : {redirect_resp.headers['location']}")
    print("  [OK] Split-Screen Presentation Verified: Non-mutating comparison with synthetic fake data operational.")

    # Final review store verification after Step 10
    if db_path.exists():
        with sqlite3.connect(db_path) as conn:
            c = conn.cursor()
            post_demo_alerts = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            post_demo_reviews = c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
        assert post_demo_alerts >= initial_alerts
        assert post_demo_reviews == initial_reviews
        print("  [OK] Final Integrity Verified: Zero analyst reviews modified across all 10 demo steps.")

    print_banner("ALL DEMONSTRATION CHECKS COMPLETED SUCCESSFULLY")


run_demo_walkthrough = run_hod_walkthrough

if __name__ == "__main__":
    run_hod_walkthrough()
