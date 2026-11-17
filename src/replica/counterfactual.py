"""Safe Counterfactual Comparison & Demo Scenario Controller for SentinelX Mode 2.

Provides:
- Non-mutating "Protected by SentinelX vs. Without SentinelX" comparison.
- Generates hypothetical outcomes using synthetic fake data to illustrate what
  would occur if SentinelX had not intervened (e.g. unauthorized access to fake admin page).
- Reads actual local replica block status (HTTP 403, active TTL, expiry) without mutating state.
- Strictly non-mutating: Does NOT disable enforcement, does NOT alter review database,
  and does NOT transmit any network traffic to real infrastructure.
- Demo scenario reset controller that clears ONLY scenario test blocks while preserving
  analyst review history.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from src.enforcement.models import OperatingMode
from src.replica.app import get_replica_adapter


def get_counterfactual_comparison(scenario_name: str = "bruteforce") -> Dict[str, Any]:
    """Generate a structured, non-mutating side-by-side comparison between SentinelX protection

    and a hypothetical 'Without SentinelX' baseline using fake data.
    """
    adapter = get_replica_adapter()
    now_iso = datetime.now(timezone.utc).isoformat()

    if scenario_name == "honeypot":
        target_ip = "198.51.100.88"
        target_route = "/replica/admin-decoy"
        attack_family = "Probe/Recon"
        attack_desc = "Unauthorized reconnaissance probe against administrative decoy trap route"
        active_blocks = [b for b in adapter.get_active_blocks() if b.target_ip == target_ip]
        is_blocked = len(active_blocks) > 0
        ttl_rem = 0
        exp_at = None
        if is_blocked:
            exp_at = active_blocks[0].expires_at
            now_dt = datetime.now(timezone.utc)
            exp_dt = datetime.fromisoformat(exp_at)
            ttl_rem = max(0, int((exp_dt - now_dt).total_seconds()))

        prot_label = "BLOCK ACTIVE" if is_blocked else "READY — no block active"
        prot_status = "REPLICA_BLOCKED" if is_blocked else "READY_NO_BLOCK"
        prot_reason = (
            "Automated defense: Probe/Recon with confirmed decoy trap evidence. Ephemeral block active."
            if is_blocked
            else "Decoy trap is primed; ready to trigger block on interaction. Run scenario to activate."
        )

        return {
            "scenario_name": "honeypot",
            "attack_location": {
                "label": "SIMULATED ATTACK",
                "site_id": "lab-replica-site",
                "site_name": "Northstar Campus Portal (Lab Replica)",
                "target_route": target_route,
                "simulated_source_ip": target_ip,
                "identity_type": "SIMULATED_SCENARIO",
                "attack_type": "Reconnaissance / Decoy Probe",
                "timestamp": now_iso,
                "description": attack_desc,
            },
            "protected_outcome": {
                "label": prot_label,
                "enforced_by": "LocalReplicaAdapter (In-Process Interceptor)",
                "is_real_replica_enforced": is_blocked,
                "requires_scenario_run": not is_blocked,
                "execution_guidance": (
                    "Active block is currently enforced on the local replica."
                    if is_blocked
                    else "Scenario must be run first (click 'Start Scenario') to trigger detection and activate a block."
                ),
                "http_status": 403 if is_blocked else 200,
                "status": prot_status,
                "reason": prot_reason,
                "ttl_remaining_seconds": ttl_rem,
                "ttl_seconds": active_blocks[0].ttl_seconds if is_blocked else 15,
                "expires_at": exp_at,
                "business_impact": (
                    "Reconnaissance halted immediately; attacker prevented from mapping internal Northstar administrative APIs."
                    if is_blocked
                    else "Baseline state: Decoy trap primed. Run the scenario to simulate the probe and verify automated isolation."
                ),
            },
            "counterfactual_outcome": {
                "label": "HYPOTHETICAL OUTCOME",
                "simulation_type": "NON_MUTATING_FAKE_DATA_SIMULATION",
                "is_hypothetical": True,
                "http_status": 200,
                "status": "UNNOTICED_MAPPING",
                "hypothetical_page": "/replica/admin",
                "compromised_data": {
                    "mapped_endpoint": "/replica/admin-decoy (Internal)",
                    "recon_status": "API Topology Discovered (Fake Simulation)",
                    "vulnerability_scan": "Campus administrative portal structure enumerated without alert",
                },
                "business_impact": "Scout maps internal architecture silently; escalates to target real faculty administration console unnoticed.",
                "disclaimer": "Hypothetical outcome modeled with synthetic fake data. No real enforcement disabled; zero traffic dispatched.",
            },
            "sentinelx_telemetry": {
                "operating_mode": OperatingMode.MODE_2_REPLICA_DEFENSE.value,
                "mode_1_status": "SIMULATED / NOT CONNECTED",
                "model_score": 0.90,
                "suspected_family": attack_family,
                "independent_evidence": [
                    "honeypot_interaction: CONFIRMED (/replica/admin-decoy)",
                    "waf_event: UNCONFIRMED",
                ],
                "policy_rule": "AUTHORIZED_INDEPENDENT_EVIDENCE",
                "action": "BLOCK",
            },
        }

    elif scenario_name == "benign_burst":
        admin_ip = "10.0.0.99"
        target_route = "/replica/portal"
        return {
            "scenario_name": "benign_burst",
            "attack_location": {
                "label": "SIMULATED ATTACK",
                "site_id": "lab-replica-site",
                "site_name": "Northstar Campus Portal (Lab Replica)",
                "target_route": target_route,
                "simulated_source_ip": admin_ip,
                "identity_type": "SIMULATED_SCENARIO",
                "attack_type": "Legitimate Administrative Burst",
                "timestamp": now_iso,
                "description": "High-volume maintenance request burst from authorized administrator",
            },
            "protected_outcome": {
                "label": "ALLOWLISTED_BYPASS",
                "enforced_by": "LocalReplicaAdapter (Allowlist Filter)",
                "is_real_replica_enforced": False,
                "is_allowlisted": True,
                "requires_scenario_run": False,
                "execution_guidance": "Trusted administrator IP is allowlisted; requests are permitted without blocking.",
                "http_status": 200,
                "status": "ALLOWLISTED_BYPASS",
                "reason": "Client IP '10.0.0.99' is on trusted allowlist for 'Northstar Campus Portal'. Enforcement bypassed.",
                "ttl_remaining_seconds": 0,
                "expires_at": None,
                "business_impact": "Zero operational disruption; legitimate student self-service queries and admin maintenance permitted without false alarms.",
            },
            "counterfactual_outcome": {
                "label": "HYPOTHETICAL OUTCOME",
                "simulation_type": "NON_MUTATING_FAKE_DATA_SIMULATION",
                "is_hypothetical": True,
                "http_status": 429,
                "status": "CRUDE_RATE_LIMIT_OUTAGE",
                "hypothetical_page": "/replica/portal",
                "compromised_data": {
                    "error": "RATE_LIMIT_EXCEEDED (Naive Threshold)",
                    "admin_locked_out": True,
                    "maintenance_window": "Failed due to false positive threshold during enrollment surge",
                },
                "business_impact": "Naive rate limiter blocks administrator during registration window, creating high campus downtime.",
                "disclaimer": "Hypothetical outcome modeled with synthetic fake data. No real enforcement disabled; zero traffic dispatched.",
            },
            "sentinelx_telemetry": {
                "operating_mode": OperatingMode.MODE_2_REPLICA_DEFENSE.value,
                "mode_1_status": "SIMULATED / NOT CONNECTED",
                "model_score": 0.35,
                "suspected_family": "NormalTraffic",
                "independent_evidence": [
                    "auth_failures: UNCONFIRMED (0 failures)",
                    "request_rate: UNCONFIRMED (Allowlist bypass applied)",
                ],
                "policy_rule": "TRUSTED_ALLOWLIST_BYPASS",
                "action": "MONITOR_ONLY",
            },
        }

    else:
        # Default: Slow-Rate Brute Force
        target_ip = "198.51.100.77"
        target_route = "/replica/login"
        attack_family = "BruteForce"
        attack_desc = "Slow-rate credential stuffing password spray against student & staff authentication endpoint"
        active_blocks = [b for b in adapter.get_active_blocks() if b.target_ip == target_ip]
        is_blocked = len(active_blocks) > 0
        ttl_rem = 0
        exp_at = None
        if is_blocked:
            exp_at = active_blocks[0].expires_at
            now_dt = datetime.now(timezone.utc)
            exp_dt = datetime.fromisoformat(exp_at)
            ttl_rem = max(0, int((exp_dt - now_dt).total_seconds()))

        prot_label = "BLOCK ACTIVE" if is_blocked else "READY — no block active"
        prot_status = "REPLICA_BLOCKED" if is_blocked else "READY_NO_BLOCK"
        prot_reason = (
            "Automated defense: confirmed BruteForce with independent evidence. Ephemeral block active."
            if is_blocked
            else "Authentication endpoint monitored; ready to trigger block on threshold. Run scenario to activate."
        )

        return {
            "scenario_name": "bruteforce",
            "attack_location": {
                "label": "SIMULATED ATTACK",
                "site_id": "lab-replica-site",
                "site_name": "Northstar Campus Portal (Lab Replica)",
                "target_route": target_route,
                "simulated_source_ip": target_ip,
                "identity_type": "SIMULATED_SCENARIO",
                "attack_type": "BruteForce (Credential Spraying)",
                "timestamp": now_iso,
                "description": attack_desc,
            },
            "protected_outcome": {
                "label": prot_label,
                "enforced_by": "LocalReplicaAdapter (In-Process Interceptor)",
                "is_real_replica_enforced": is_blocked,
                "requires_scenario_run": not is_blocked,
                "execution_guidance": (
                    "Active block is currently enforced on the local replica."
                    if is_blocked
                    else "Scenario must be run first (click 'Start Scenario') to trigger detection and activate a block."
                ),
                "http_status": 403 if is_blocked else 200,
                "status": prot_status,
                "reason": prot_reason,
                "ttl_remaining_seconds": ttl_rem,
                "ttl_seconds": active_blocks[0].ttl_seconds if is_blocked else 15,
                "expires_at": exp_at,
                "business_impact": (
                    "8th login attempt actively intercepted with HTTP 403 Forbidden; student account compromise prevented."
                    if is_blocked
                    else "Baseline state: No active block. Run the scenario to simulate the attack and engage SentinelX defense."
                ),
            },
            "counterfactual_outcome": {
                "label": "HYPOTHETICAL OUTCOME",
                "simulation_type": "NON_MUTATING_FAKE_DATA_SIMULATION",
                "is_hypothetical": True,
                "http_status": 200,
                "status": "COMPROMISED",
                "hypothetical_page": "/replica/admin",
                "compromised_data": {
                    "account_id": "ACC-99201-REPLICA (Northstar Student #NS-88412)",
                    "balance": "$4,250.00 (Campus Tuition Account)",
                    "token_issued": "fake-jwt-stolen-token-991",
                    "exfiltration_risk": "CRITICAL",
                },
                "business_impact": "Attacker successfully guesses password on attempt 8; issues valid SSO student session token; accesses student records unnoticed.",
                "disclaimer": "Hypothetical outcome modeled with synthetic fake data. No real enforcement disabled; zero traffic dispatched.",
            },
            "sentinelx_telemetry": {
                "operating_mode": OperatingMode.MODE_2_REPLICA_DEFENSE.value,
                "mode_1_status": "SIMULATED / NOT CONNECTED",
                "model_score": 1.00,
                "suspected_family": attack_family,
                "independent_evidence": [
                    "auth_failures: CONFIRMED (7 failures >= threshold 5)",
                    "waf_event: UNCONFIRMED",
                ],
                "policy_rule": "AUTHORIZED_INDEPENDENT_EVIDENCE",
                "action": "BLOCK",
            },
        }


def reset_demo_scenario(scenario_name: Optional[str] = None) -> Dict[str, Any]:
    """Reset active demo scenario blocks on the local replica adapter.

    Strict Invariant: Clears ONLY the scenario simulated attacker blocks.
    NEVER deletes or modifies stored analyst review decisions or historical alerts.
    """
    adapter = get_replica_adapter()
    scenario_ips = ["198.51.100.77", "198.51.100.88", "10.0.0.99"]

    released_ips: List[str] = []
    for ip in scenario_ips:
        if adapter.is_ip_blocked(ip):
            adapter.remove_block(ip)
            released_ips.append(ip)

    return {
        "status": "SCENARIO_RESET_COMPLETED",
        "released_ips": released_ips,
        "message": f"Demo scenario reset. Released {len(released_ips)} ephemeral test blocks.",
        "review_database_preserved": True,
    }
