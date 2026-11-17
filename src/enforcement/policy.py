"""Enforcement Policy Engine for SentinelX Operating Modes.

Enforces strict defense-in-depth authorization rules:
1. Emergency Stop overrides all settings and disallows any enforcement.
2. Global Blocking toggle must be explicitly enabled (default: OFF).
3. Per-site Blocking toggle must be explicitly enabled (default: OFF).
4. Trusted-client allowlists bypass all blocking (Mode 1 and Mode 2 lists kept strictly isolated).
5. Model scores alone CANNOT cause a block; independent confirming attack evidence is mandatory.
6. BruteForce guardrail requires confirmed authentication failure evidence (>= 5 failures).
7. If evidence, site configuration, or adapter is unavailable, blocking is disallowed with explicit reasons.
8. Ephemeral actions have strict TTLs with automatic expiration.
9. Maintains an audit trail of all enforcement decisions and active blocks.
"""

import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from src.enforcement.models import (
    OperatingMode,
    EnforcementAction,
    EnforcementStatus,
    SiteConfig,
    ActiveBlock,
    EnforcementDecision,
    GlobalEnforcementConfig,
)
from src.enforcement.adapters.base import BaseEnforcementAdapter
from src.enforcement.adapters.mock_real import MockRealSiteAdapter
from src.enforcement.adapters.local_replica import LocalReplicaAdapter
from src.alerts.schema import FlowAlert, RiskTier, RecommendedAction

logger = logging.getLogger(__name__)


class EnforcementPolicyEngine:
    """Evaluates flow alerts against operating mode configurations and executes safe enforcement."""

    def __init__(self, config: Optional[GlobalEnforcementConfig] = None):
        self.config = config or GlobalEnforcementConfig()
        # Seed default Mode 1 sites
        if not self.config.sites:
            self._seed_default_sites()

        # Initialize adapters
        self.adapters: Dict[str, BaseEnforcementAdapter] = {
            "mock_real_adapter": MockRealSiteAdapter(adapter_name="mock_real_adapter"),
            "local_replica_adapter": LocalReplicaAdapter(adapter_name="local_replica_adapter"),
        }

        # Audit trail of decisions
        self.audit_log: List[EnforcementDecision] = []
        self.max_audit_records = 200

    def _seed_default_sites(self):
        """Seed default Mode 1 real sites with blocking strictly OFF."""
        self.config.sites["prod-portal-alpha"] = SiteConfig(
            site_id="prod-portal-alpha",
            name="Production Customer Portal",
            mode=OperatingMode.MODE_1_REAL_SITE,
            site_url="https://portal.acme-corp.com",
            routes=["/login", "/dashboard", "/api/v1/auth", "/transfer"],
            blocking_enabled=False,  # DEFAULT: OFF
            trusted_allowlist=["127.0.0.1", "10.0.0.1", "192.168.1.1", "198.51.100.1"],
            enforcement_adapter="mock_real_adapter",
            block_ttl_seconds=300,
        )
        self.config.sites["corp-api-gateway"] = SiteConfig(
            site_id="corp-api-gateway",
            name="Corporate API Gateway",
            mode=OperatingMode.MODE_1_REAL_SITE,
            site_url="https://api.acme-corp.com",
            routes=["/api/v2/transactions", "/api/v2/users", "/health"],
            blocking_enabled=False,  # DEFAULT: OFF
            trusted_allowlist=["127.0.0.1", "10.10.0.5"],
            enforcement_adapter="mock_real_adapter",
            block_ttl_seconds=600,
        )

    def register_adapter(self, adapter: BaseEnforcementAdapter):
        """Register a new enforcement adapter."""
        self.adapters[adapter.adapter_name] = adapter

    def get_adapter(self, adapter_name: str) -> Optional[BaseEnforcementAdapter]:
        """Retrieve an adapter by name."""
        return self.adapters.get(adapter_name)

    def get_site_config(self, site_id: str) -> Optional[SiteConfig]:
        """Retrieve site configuration by ID (checks Mode 1 sites and Mode 2 replica)."""
        if site_id == self.config.replica_site.site_id:
            return self.config.replica_site
        return self.config.sites.get(site_id)

    def evaluate_and_enforce(
        self,
        alert: FlowAlert,
        target_ip: Optional[str] = None,
        target_route: Optional[str] = None,
        site_id: Optional[str] = None,
        requested_mode: Optional[OperatingMode] = None,
        flow_telemetry: Optional[Dict[str, Any]] = None,
    ) -> EnforcementDecision:
        """Evaluate a flow alert against mode authorization rules and execute temporary block if eligible."""
        now_iso = datetime.now(timezone.utc).isoformat()
        decision_id = f"dec-{uuid.uuid4().hex[:8]}"

        # Resolve mode
        mode = requested_mode or self.config.operating_mode

        # Resolve site
        if mode == OperatingMode.MODE_2_REPLICA_DEFENSE:
            site = self.config.replica_site
        else:
            site = self.get_site_config(site_id or "prod-portal-alpha")

        site_name = site.name if site else (site_id or "Unknown Site")
        site_id_val = site.site_id if site else (site_id or "unknown-site")

        # Resolve target IP
        resolved_ip = target_ip or (flow_telemetry.get("Source IP") if flow_telemetry else None)
        if not resolved_ip:
            # Fall back to alert flow_id if it looks like an IP, else placeholder
            resolved_ip = alert.flow_id if "." in alert.flow_id else "unknown_ip"

        # Resolve target route
        resolved_route = (
            target_route
            or (flow_telemetry.get("target_route") if flow_telemetry else None)
            or (flow_telemetry.get("request_path") if flow_telemetry else None)
            or (flow_telemetry.get("uri") if flow_telemetry else None)
            or ("/replica/login" if mode == OperatingMode.MODE_2_REPLICA_DEFENSE else (site.routes[0] if site and site.routes else "/login"))
        )

        model_score = alert.scores.production_score if alert.scores else 0.0
        suspected_family = alert.suspected_family or "Unknown"

        # Collect evidence summary
        evidence_summary: List[str] = []
        independent_confirmed = False

        site_has_honeypot = site.honeypot_enabled if site else False

        if alert.confirming_signals:
            for sig_name, sig in alert.confirming_signals.items():
                if sig_name == "honeypot_interaction" and not site_has_honeypot:
                    evidence_summary.append("honeypot_interaction: UNAVAILABLE (No honeypot configured for this site)")
                    continue
                if sig.present:
                    status_str = "CONFIRMED" if sig.confirmed else "UNCONFIRMED"
                    evidence_summary.append(f"{sig_name}: {status_str} ({sig.description or ''})")
                    if sig.confirmed:
                        independent_confirmed = True
                else:
                    evidence_summary.append(f"{sig_name}: UNAVAILABLE")

        # Check 1: Emergency Stop Check
        if self.config.emergency_stop_active:
            decision = EnforcementDecision(
                decision_id=decision_id,
                timestamp=now_iso,
                site_id=site_id_val,
                site_name=site_name,
                operating_mode=mode,
                target_ip=resolved_ip,
                target_route=resolved_route,
                suspected_attack=suspected_family,
                model_score=model_score,
                independent_evidence_confirmed=independent_confirmed,
                evidence_summary=evidence_summary,
                action=EnforcementAction.MONITOR_ONLY,
                status=EnforcementStatus.DISALLOWED_EMERGENCY_STOP,
                is_simulated=True,
                allowed_to_block=False,
                policy_rule="EMERGENCY_STOP_ACTIVE",
                reason="Emergency stop is activated. All automated enforcement actions are strictly halted.",
            )
            self._record_decision(decision)
            return decision

        # Check 2: Global Blocking Enable Check
        if not self.config.global_blocking_enabled:
            decision = EnforcementDecision(
                decision_id=decision_id,
                timestamp=now_iso,
                site_id=site_id_val,
                site_name=site_name,
                operating_mode=mode,
                target_ip=resolved_ip,
                target_route=resolved_route,
                suspected_attack=suspected_family,
                model_score=model_score,
                independent_evidence_confirmed=independent_confirmed,
                evidence_summary=evidence_summary,
                action=EnforcementAction.MONITOR_ONLY,
                status=EnforcementStatus.DISALLOWED_OFF,
                is_simulated=True,
                allowed_to_block=False,
                policy_rule="GLOBAL_BLOCKING_OFF",
                reason="Global blocking enable toggle is OFF. System operates in passive monitor-only mode.",
            )
            self._record_decision(decision)
            return decision

        # Check 3: Site Configuration Check
        if not site:
            decision = EnforcementDecision(
                decision_id=decision_id,
                timestamp=now_iso,
                site_id=site_id_val,
                site_name=site_name,
                operating_mode=mode,
                target_ip=resolved_ip,
                target_route=resolved_route,
                suspected_attack=suspected_family,
                model_score=model_score,
                independent_evidence_confirmed=independent_confirmed,
                evidence_summary=evidence_summary,
                action=EnforcementAction.MONITOR_ONLY,
                status=EnforcementStatus.UNAVAILABLE,
                is_simulated=True,
                allowed_to_block=False,
                policy_rule="SITE_CONFIG_MISSING",
                reason=f"Site configuration for '{site_id_val}' is not found.",
            )
            self._record_decision(decision)
            return decision

        # Check 4: Per-site Blocking Toggle Check
        if not site.blocking_enabled:
            decision = EnforcementDecision(
                decision_id=decision_id,
                timestamp=now_iso,
                site_id=site_id_val,
                site_name=site_name,
                operating_mode=mode,
                target_ip=resolved_ip,
                target_route=resolved_route,
                suspected_attack=suspected_family,
                model_score=model_score,
                independent_evidence_confirmed=independent_confirmed,
                evidence_summary=evidence_summary,
                action=EnforcementAction.MONITOR_ONLY,
                status=EnforcementStatus.DISALLOWED_OFF,
                is_simulated=True,
                allowed_to_block=False,
                policy_rule="SITE_BLOCKING_OFF",
                reason=f"Per-site blocking is OFF for '{site.name}'. (Backend policy enforced).",
            )
            self._record_decision(decision)
            return decision

        # Check 5: Trusted-Client Allowlist Check
        if resolved_ip in site.trusted_allowlist:
            decision = EnforcementDecision(
                decision_id=decision_id,
                timestamp=now_iso,
                site_id=site_id_val,
                site_name=site_name,
                operating_mode=mode,
                target_ip=resolved_ip,
                target_route=resolved_route,
                suspected_attack=suspected_family,
                model_score=model_score,
                independent_evidence_confirmed=independent_confirmed,
                evidence_summary=evidence_summary,
                action=EnforcementAction.MONITOR_ONLY,
                status=EnforcementStatus.ALLOWLISTED_BYPASS,
                is_simulated=True,
                allowed_to_block=False,
                policy_rule="TRUSTED_ALLOWLIST_BYPASS",
                reason=f"Client IP '{resolved_ip}' is on trusted allowlist for '{site.name}'. Enforcement bypassed.",
            )
            self._record_decision(decision)
            return decision

        # Check 6: Severity & Recommendation Check
        if alert.risk_tier not in [RiskTier.CRITICAL, RiskTier.HIGH]:
            decision = EnforcementDecision(
                decision_id=decision_id,
                timestamp=now_iso,
                site_id=site_id_val,
                site_name=site_name,
                operating_mode=mode,
                target_ip=resolved_ip,
                target_route=resolved_route,
                suspected_attack=suspected_family,
                model_score=model_score,
                independent_evidence_confirmed=independent_confirmed,
                evidence_summary=evidence_summary,
                action=EnforcementAction.MONITOR_ONLY,
                status=EnforcementStatus.DISALLOWED_NO_EVIDENCE,
                is_simulated=True,
                allowed_to_block=False,
                policy_rule="INSUFFICIENT_SEVERITY",
                reason=f"Alert risk tier is {alert.risk_tier.value}; automated blocking is restricted to CRITICAL/HIGH.",
            )
            self._record_decision(decision)
            return decision

        # Check 7: Independent Attack Evidence Mandatory (Model Scores Alone Cannot Block)
        auth_sig = alert.confirming_signals.get("auth_failures") if alert.confirming_signals else None
        waf_sig = alert.confirming_signals.get("waf_event") if alert.confirming_signals else None
        rate_sig = alert.confirming_signals.get("request_rate") if alert.confirming_signals else None
        honey_sig = alert.confirming_signals.get("honeypot_interaction") if alert.confirming_signals else None

        # BruteForce Guardrail: Requires confirmed auth_failures (>= 5)
        if suspected_family == "BruteForce":
            if not auth_sig or not auth_sig.present or not auth_sig.confirmed:
                decision = EnforcementDecision(
                    decision_id=decision_id,
                    timestamp=now_iso,
                    site_id=site_id_val,
                    site_name=site_name,
                    operating_mode=mode,
                    target_ip=resolved_ip,
                    target_route=resolved_route,
                    suspected_attack=suspected_family,
                    model_score=model_score,
                    independent_evidence_confirmed=False,
                    evidence_summary=evidence_summary,
                    action=EnforcementAction.MONITOR_ONLY,
                    status=EnforcementStatus.DISALLOWED_NO_EVIDENCE,
                    is_simulated=True,
                    allowed_to_block=False,
                    policy_rule="BRUTEFORCE_GUARDRAIL_UNCONFIRMED",
                    reason="BruteForce guardrail applied: independent authentication failure confirmation (>=5 attempts) is required. Model score alone cannot cause a block.",
                )
                self._record_decision(decision)
                return decision

        # General Independent Evidence Check for all attack families
        has_independent_evidence = False
        if auth_sig and auth_sig.present and auth_sig.confirmed:
            has_independent_evidence = True
        elif waf_sig and waf_sig.present and waf_sig.confirmed:
            has_independent_evidence = True
        elif site_has_honeypot and honey_sig and honey_sig.present and honey_sig.confirmed:
            has_independent_evidence = True
        elif rate_sig and rate_sig.present and rate_sig.confirmed and model_score >= 0.70:
            has_independent_evidence = True

        if not has_independent_evidence:
            decision = EnforcementDecision(
                decision_id=decision_id,
                timestamp=now_iso,
                site_id=site_id_val,
                site_name=site_name,
                operating_mode=mode,
                target_ip=resolved_ip,
                target_route=resolved_route,
                suspected_attack=suspected_family,
                model_score=model_score,
                independent_evidence_confirmed=False,
                evidence_summary=evidence_summary,
                action=EnforcementAction.MONITOR_ONLY,
                status=EnforcementStatus.DISALLOWED_NO_EVIDENCE,
                is_simulated=True,
                allowed_to_block=False,
                policy_rule="MODEL_ALONE_REJECTED",
                reason="Independent attack evidence absent or unconfirmed. Model score alone cannot authorize blocking.",
            )
            self._record_decision(decision)
            return decision

        # Check 8: Adapter Availability Check
        adapter = self.get_adapter(site.enforcement_adapter)
        if not adapter:
            decision = EnforcementDecision(
                decision_id=decision_id,
                timestamp=now_iso,
                site_id=site_id_val,
                site_name=site_name,
                operating_mode=mode,
                target_ip=resolved_ip,
                target_route=resolved_route,
                suspected_attack=suspected_family,
                model_score=model_score,
                independent_evidence_confirmed=True,
                evidence_summary=evidence_summary,
                action=EnforcementAction.MONITOR_ONLY,
                status=EnforcementStatus.UNAVAILABLE,
                is_simulated=True,
                allowed_to_block=False,
                policy_rule="ADAPTER_UNAVAILABLE",
                reason=f"Configured enforcement adapter '{site.enforcement_adapter}' is unavailable.",
            )
            self._record_decision(decision)
            return decision

        # Check 9: Execute Ephemeral Block on Adapter
        block_duration = site.block_ttl_seconds
        block_reason = f"Automated defense: {suspected_family} (score: {model_score:.2f}) with confirmed evidence."

        active_block = adapter.apply_block(
            target_ip=resolved_ip,
            site_id=site.site_id,
            duration_seconds=block_duration,
            reason=block_reason,
            metadata={
                "alert_id": alert.alert_id,
                "model_score": model_score,
                "suspected_family": suspected_family,
                "evidence": evidence_summary,
                "site_name": site.name,
                "mode": mode.value,
            },
        )

        decision = EnforcementDecision(
            decision_id=decision_id,
            timestamp=now_iso,
            site_id=site.site_id,
            site_name=site.name,
            operating_mode=mode,
            target_ip=resolved_ip,
            target_route=resolved_route,
            suspected_attack=suspected_family,
            model_score=model_score,
            independent_evidence_confirmed=True,
            evidence_summary=evidence_summary,
            action=EnforcementAction.BLOCK,
            status=adapter.adapter_status,
            is_simulated=adapter.is_simulated,
            allowed_to_block=True,
            policy_rule="AUTHORIZED_INDEPENDENT_EVIDENCE",
            reason=f"Eligible for automated defense: confirmed {suspected_family} with independent evidence. Temporary {block_duration}s block applied.",
            active_block=active_block,
        )

        self._record_decision(decision)
        return decision

    def _record_decision(self, decision: EnforcementDecision):
        """Record decision in audit trail."""
        self.audit_log.insert(0, decision)
        if len(self.audit_log) > self.max_audit_records:
            self.audit_log.pop()

    def get_all_active_blocks(self) -> List[ActiveBlock]:
        """Collect active blocks across all registered adapters."""
        all_blocks: List[ActiveBlock] = []
        for adapter in self.adapters.values():
            all_blocks.extend(adapter.get_active_blocks())
        return all_blocks

    def release_block(self, target_ip: str) -> bool:
        """Release a block on target_ip across all adapters."""
        released = False
        for adapter in self.adapters.values():
            if adapter.remove_block(target_ip):
                released = True
        return released


_default_policy_engine: Optional[EnforcementPolicyEngine] = None


def get_default_enforcement_engine() -> EnforcementPolicyEngine:
    """Get or create singleton EnforcementPolicyEngine."""
    global _default_policy_engine
    if _default_policy_engine is None:
        _default_policy_engine = EnforcementPolicyEngine()
    return _default_policy_engine


def set_default_enforcement_engine(engine: Optional[EnforcementPolicyEngine]):
    """Set or override singleton EnforcementPolicyEngine."""
    global _default_policy_engine
    _default_policy_engine = engine
