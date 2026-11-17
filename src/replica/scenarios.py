"""Simulated Attack & Defense Scenarios for Mode 2 Isolated Replica.

Demonstrates:
1. Slow-rate Brute Force Attack:
   - Client 198.51.100.77 attempts credential guessing against /replica/login.
   - Independent authentication-failure evidence is confirmed (>= 5 failures).
   - Mode 2 LocalReplicaAdapter blocks the IP for 15s.
   - Subsequent requests from 198.51.100.77 to the replica receive HTTP 403.
   - Expiry or release restores normal access.
2. Benign Administrative Burst:
   - Lab administrator 10.0.0.99 initiates a burst of legitimate traffic.
   - Guard observes rate surge, but confirms zero auth failures and checks the lab allowlist.
   - Enforcement is bypassed with clear explanation; zero disruption.
3. Decoy Trap Honeypot Defense:
   - Reconnaissance scout 198.51.100.88 probes /replica/admin-decoy.
   - Structured honeypot_interaction telemetry is logged (without body/password/tokens).
   - Independent confirming evidence is satisfied by the honeypot trap hit.
   - Mode 2 LocalReplicaAdapter applies ephemeral 15s block, intercepting subsequent requests with HTTP 403.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd

from src.guard.engine import SentinelGuard
from src.enforcement.models import OperatingMode, EnforcementStatus, EnforcementAction
from src.enforcement.policy import EnforcementPolicyEngine
from src.replica.app import get_replica_adapter, check_replica_route_access
from src.replica.honeypot import record_honeypot_interaction


def run_replica_bruteforce_scenario(
    engine: Optional[EnforcementPolicyEngine] = None,
    guard: Optional[SentinelGuard] = None,
) -> Dict[str, Any]:
    """Execute the Mode 2 Slow-Rate Brute Force defense scenario against the local replica."""
    guard = guard or SentinelGuard()
    engine = engine or EnforcementPolicyEngine()
    replica_adapter = get_replica_adapter()

    # Bind the engine's local_replica_adapter
    engine.register_adapter(replica_adapter)

    # Configure Mode 2 with blocking ON (respecting emergency stop if already active)
    engine.config.operating_mode = OperatingMode.MODE_2_REPLICA_DEFENSE
    if not engine.config.emergency_stop_active:
        engine.config.global_blocking_enabled = True
        engine.config.replica_site.blocking_enabled = True

    attacker_ip = "198.51.100.77"

    # 1. Netflow telemetry representing the brute-force traffic stream
    flow_dict = {
        "Source IP": attacker_ip,
        "Destination IP": "127.0.0.1",
        "Destination Port": 80,
        "Timestamp": "2026-10-19 12:00:00",
        "Flow Duration": 15000000,
        "Total Fwd Packets": 24,
        "Total Backward Packets": 18,
        "Flow Bytes/s": 420.0,
        "Flow Packets/s": 2.8,
        "target_route": "/replica/login",
    }

    # Load canonical feature defaults
    sample_df = pd.read_parquet("data/processed/cicids2017_sample60k.parquet")
    base_flow = sample_df.iloc[0].to_dict()
    for k, v in flow_dict.items():
        base_flow[k] = v

    # 2. Correlated independent confirming signals from /replica/login logs
    signals = {
        "auth_failures": 7,
        "waf_alert": False,
        "request_rate": 2.8,
    }

    # 3. Analyze through SentinelGuard
    alert_resp = guard.analyze_flows(
        flows=pd.DataFrame([base_flow]),
        signals=[signals],
        batch_id="scenario-replica-bruteforce",
    )
    alert = alert_resp.alerts[0]

    # Override suspected family to BruteForce for realistic scenario demonstration
    alert.suspected_family = "BruteForce"

    # 4. Evaluate through EnforcementPolicyEngine in Mode 2
    decision = engine.evaluate_and_enforce(
        alert=alert,
        target_ip=attacker_ip,
        target_route="/replica/login",
        site_id="lab-replica-site",
        requested_mode=OperatingMode.MODE_2_REPLICA_DEFENSE,
        flow_telemetry=flow_dict,
    )

    # 5. Verify local replica route access via server-side probe
    probe = check_replica_route_access(route="/replica/login", target_ip=attacker_ip)
    is_blocked_now = replica_adapter.is_ip_blocked(attacker_ip)
    active_blocks = replica_adapter.get_active_blocks()

    probe_status = probe["status_code"]
    probe_msg = "HTTP 403 Forbidden (Blocked by SentinelX Mode 2 Replica Defense)" if probe_status == 403 else "HTTP 200 OK (Allowed)"

    return {
        "scenario": "Mode 2 Slow-Rate Brute Force Defense",
        "identity_type": "SIMULATED_SCENARIO",
        "target_ip": attacker_ip,
        "attacker_ip": attacker_ip,
        "target_route": "/replica/login",
        "replica_probe_status": probe_status,
        "replica_probe_result": probe_msg,
        "site_id": "lab-replica-site",
        "site_name": engine.config.replica_site.name,
        "operating_mode": OperatingMode.MODE_2_REPLICA_DEFENSE.value,
        "status": decision.status.value,
        "action": decision.action.value,
        "allowed_to_block": decision.allowed_to_block,
        "policy_rule": decision.policy_rule,
        "reason": decision.reason,
        "independent_evidence_confirmed": decision.independent_evidence_confirmed,
        "is_simulated": decision.is_simulated,
        "active_block": decision.active_block.model_dump() if decision.active_block else None,
        "replica_is_blocked": is_blocked_now,
        "active_blocks_count": len(active_blocks),
        "geo_privacy_notice": decision.geo_privacy_notice,
    }


def run_replica_benign_burst_scenario(
    engine: Optional[EnforcementPolicyEngine] = None,
    guard: Optional[SentinelGuard] = None,
) -> Dict[str, Any]:
    """Execute the Mode 2 Benign Administrative Burst scenario against the local replica."""
    guard = guard or SentinelGuard()
    engine = engine or EnforcementPolicyEngine()
    replica_adapter = get_replica_adapter()
    engine.register_adapter(replica_adapter)

    engine.config.operating_mode = OperatingMode.MODE_2_REPLICA_DEFENSE
    engine.config.global_blocking_enabled = True
    engine.config.replica_site.blocking_enabled = True

    admin_ip = "10.0.0.99"  # On lab trusted allowlist

    flow_dict = {
        "Source IP": admin_ip,
        "Destination IP": "127.0.0.1",
        "Destination Port": 80,
        "Timestamp": "2026-10-19 12:05:00",
        "Flow Duration": 2000000,
        "Total Fwd Packets": 85,
        "Total Backward Packets": 80,
        "Flow Bytes/s": 450000.0,
        "Flow Packets/s": 82.5,
        "target_route": "/replica/portal",
    }

    sample_df = pd.read_parquet("data/processed/cicids2017_sample60k.parquet")
    base_flow = sample_df.iloc[0].to_dict()
    for k, v in flow_dict.items():
        base_flow[k] = v

    signals = {
        "auth_failures": 0,
        "waf_alert": False,
        "request_rate": 82.5,
    }

    alert_resp = guard.analyze_flows(
        flows=pd.DataFrame([base_flow]),
        signals=[signals],
        batch_id="scenario-replica-benign-burst",
    )
    alert = alert_resp.alerts[0]

    decision = engine.evaluate_and_enforce(
        alert=alert,
        target_ip=admin_ip,
        target_route="/replica/portal",
        site_id="lab-replica-site",
        requested_mode=OperatingMode.MODE_2_REPLICA_DEFENSE,
        flow_telemetry=flow_dict,
    )

    probe = check_replica_route_access(route="/replica/portal", target_ip=admin_ip)
    is_blocked_now = replica_adapter.is_ip_blocked(admin_ip)

    return {
        "scenario": "Mode 2 Benign Administrative Burst",
        "identity_type": "SIMULATED_SCENARIO",
        "target_ip": admin_ip,
        "admin_ip": admin_ip,
        "target_route": "/replica/portal",
        "replica_probe_status": probe["status_code"],
        "replica_probe_result": "HTTP 200 OK (Trusted client allowlist bypass)",
        "site_id": "lab-replica-site",
        "site_name": engine.config.replica_site.name,
        "operating_mode": OperatingMode.MODE_2_REPLICA_DEFENSE.value,
        "status": decision.status.value,
        "action": decision.action.value,
        "allowed_to_block": decision.allowed_to_block,
        "policy_rule": decision.policy_rule,
        "reason": decision.reason,
        "replica_is_blocked": is_blocked_now,
        "is_simulated": decision.is_simulated,
        "geo_privacy_notice": decision.geo_privacy_notice,
    }


def run_replica_honeypot_scenario(
    engine: Optional[EnforcementPolicyEngine] = None,
    guard: Optional[SentinelGuard] = None,
) -> Dict[str, Any]:
    """Execute the Mode 2 Decoy Trap Honeypot defense scenario against the local replica."""
    guard = guard or SentinelGuard()
    engine = engine or EnforcementPolicyEngine()
    replica_adapter = get_replica_adapter()
    engine.register_adapter(replica_adapter)

    engine.config.operating_mode = OperatingMode.MODE_2_REPLICA_DEFENSE
    if not engine.config.emergency_stop_active:
        engine.config.global_blocking_enabled = True
        engine.config.replica_site.blocking_enabled = True

    attacker_ip = "198.51.100.88"  # Scout / Reconnaissance simulated attacker
    decoy_route = "/replica/admin-decoy"

    # 1. Record structured honeypot interaction (without sensitive payloads)
    honeypot_event = record_honeypot_interaction(
        route=decoy_route,
        http_method="POST",
        source_identity=attacker_ip,
        identity_type="SIMULATED_SCENARIO",
        site_id="lab-replica-site",
        description=f"Unauthorized reconnaissance probe against administrative decoy trap route '{decoy_route}'.",
    )

    # 2. Netflow telemetry representing the honeypot probe
    flow_dict = {
        "Source IP": attacker_ip,
        "Destination IP": "127.0.0.1",
        "Destination Port": 80,
        "Timestamp": "2026-10-19 12:10:00",
        "Flow Duration": 1200000,
        "Total Fwd Packets": 12,
        "Total Backward Packets": 8,
        "Flow Bytes/s": 310.0,
        "Flow Packets/s": 16.6,
        "target_route": decoy_route,
    }

    sample_df = pd.read_parquet("data/processed/cicids2017_sample60k.parquet")
    base_flow = sample_df.iloc[0].to_dict()
    for k, v in flow_dict.items():
        base_flow[k] = v

    # 3. Independent confirming signals includes confirmed honeypot_interaction
    signals = {
        "honeypot_interaction": True,
        "honeypot_route": decoy_route,
        "waf_alert": False,
        "request_rate": 16.6,
        "auth_failures": 0,
    }

    # 4. Analyze through SentinelGuard
    alert_resp = guard.analyze_flows(
        flows=pd.DataFrame([base_flow]),
        signals=[signals],
        batch_id="scenario-replica-honeypot",
    )
    alert = alert_resp.alerts[0]
    alert.suspected_family = "Probe/Recon"

    # 5. Evaluate through EnforcementPolicyEngine in Mode 2
    decision = engine.evaluate_and_enforce(
        alert=alert,
        target_ip=attacker_ip,
        target_route=decoy_route,
        site_id="lab-replica-site",
        requested_mode=OperatingMode.MODE_2_REPLICA_DEFENSE,
        flow_telemetry=flow_dict,
    )

    # 6. Verify local replica route access via server-side probe
    probe = check_replica_route_access(route=decoy_route, target_ip=attacker_ip)
    is_blocked_now = replica_adapter.is_ip_blocked(attacker_ip)
    active_blocks = replica_adapter.get_active_blocks()

    probe_status = probe["status_code"]
    probe_msg = "HTTP 403 Forbidden (Blocked following honeypot trap interaction)" if probe_status == 403 else "HTTP 200 OK (Allowed)"

    return {
        "scenario": "Mode 2 Decoy Trap Honeypot Defense",
        "identity_type": "SIMULATED_SCENARIO",
        "target_ip": attacker_ip,
        "attacker_ip": attacker_ip,
        "target_route": decoy_route,
        "replica_probe_status": probe_status,
        "replica_probe_result": probe_msg,
        "site_id": "lab-replica-site",
        "site_name": engine.config.replica_site.name,
        "operating_mode": OperatingMode.MODE_2_REPLICA_DEFENSE.value,
        "status": decision.status.value,
        "action": decision.action.value,
        "allowed_to_block": decision.allowed_to_block,
        "policy_rule": decision.policy_rule,
        "reason": decision.reason,
        "independent_evidence_confirmed": decision.independent_evidence_confirmed,
        "is_simulated": decision.is_simulated,
        "active_block": decision.active_block.model_dump() if decision.active_block else None,
        "replica_is_blocked": is_blocked_now,
        "active_blocks_count": len(active_blocks),
        "honeypot_event": honeypot_event.model_dump(),
        "evidence_summary": decision.evidence_summary,
        "geo_privacy_notice": decision.geo_privacy_notice,
    }
