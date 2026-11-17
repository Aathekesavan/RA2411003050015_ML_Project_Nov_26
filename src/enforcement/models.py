"""Enforcement models, schemas, and configurations for SentinelX Operating Modes.

Defines:
- OperatingMode: Mode 1 (Authorized Real-Site Monitoring) vs Mode 2 (Isolated Replica Defense).
- EnforcementAction: BLOCK, RATE_LIMIT, CHALLENGE, MONITOR_ONLY.
- EnforcementStatus: Clear distinction between SIMULATED, REPLICA, UNAVAILABLE, REAL, and DISALLOWED states.
- SiteConfig: Per-site settings (blocking toggle, trusted allowlist, TTL, adapter binding).
- GlobalEnforcementState: System-wide emergency stop, global blocking enable, and audit trail.
- ActiveBlock: Ephemeral block record with expiration timestamp and TTL.
- EnforcementDecision: Structured result of evaluating flow evidence against enforcement policy.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class OperatingMode(str, Enum):
    """SentinelX Operating Modes."""
    MODE_1_REAL_SITE = "MODE_1_REAL_SITE"
    MODE_2_REPLICA_DEFENSE = "MODE_2_REPLICA_DEFENSE"


class EnforcementAction(str, Enum):
    """Enforcement actions supported by adapters."""
    BLOCK = "BLOCK"
    RATE_LIMIT = "RATE_LIMIT"
    CHALLENGE = "CHALLENGE"
    MONITOR_ONLY = "MONITOR_ONLY"


class EnforcementStatus(str, Enum):
    """Unambiguous operational execution status."""
    SIMULATED = "SIMULATED"                          # Mode 1 Mock adapter (no real commands sent)
    REPLICA = "REPLICA"                              # Mode 2 Local replica lab enforcement
    REAL = "REAL"                                    # Production adapter (only if real backend connected)
    UNAVAILABLE = "UNAVAILABLE"                      # Missing adapter, evidence, or site mapping
    DISALLOWED_OFF = "DISALLOWED_OFF"                # Site or global blocking toggle is OFF
    DISALLOWED_EMERGENCY_STOP = "DISALLOWED_EMERGENCY_STOP"  # Emergency stop active
    ALLOWLISTED_BYPASS = "ALLOWLISTED_BYPASS"        # Client IP on trusted allowlist
    DISALLOWED_NO_EVIDENCE = "DISALLOWED_NO_EVIDENCE" # Model score alone without independent confirmation


class SiteConfig(BaseModel):
    """Configuration for a monitored site or application."""
    site_id: str = Field(..., description="Unique site identifier, e.g. 'prod-portal-alpha'")
    name: str = Field(..., description="Human-readable site name")
    mode: OperatingMode = Field(OperatingMode.MODE_1_REAL_SITE, description="Associated operating mode")
    site_url: str = Field("https://portal.example.com", description="Monitored site URL or hostname")
    routes: List[str] = Field(default_factory=lambda: ["/login", "/api/v1", "/portal"], description="Protected routes")
    blocking_enabled: bool = Field(False, description="Per-site blocking toggle (DEFAULT: OFF)")
    trusted_allowlist: List[str] = Field(
        default_factory=lambda: ["127.0.0.1", "10.0.0.1", "192.168.1.1"],
        description="Trusted client IPs or CIDRs exempt from automated enforcement"
    )
    enforcement_adapter: str = Field("mock_real_adapter", description="Configured enforcement adapter name")
    block_ttl_seconds: int = Field(300, ge=10, le=86400, description="Temporary block duration in seconds (default: 5 min)")
    honeypot_enabled: bool = Field(False, description="Whether a honeypot decoy is deployed for this site")
    honeypot_routes: List[str] = Field(default_factory=list, description="Configured honeypot decoy routes for this site")


class ActiveBlock(BaseModel):
    """Active temporary block entry."""
    block_id: str
    target_ip: str
    site_id: str
    created_at: str
    expires_at: str
    ttl_seconds: int
    reason: str
    adapter_name: str
    status: EnforcementStatus
    is_simulated: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if block has expired based on UTC timestamp."""
        exp_dt = datetime.fromisoformat(self.expires_at)
        now_dt = datetime.now(timezone.utc)
        return now_dt >= exp_dt


class EnforcementDecision(BaseModel):
    """Structured audit record for an enforcement evaluation."""
    decision_id: str
    timestamp: str
    site_id: str
    site_name: str
    operating_mode: OperatingMode
    target_ip: str
    target_route: Optional[str] = Field("/login", description="Target URL route under evaluation")
    suspected_attack: Optional[str]
    model_score: float
    independent_evidence_confirmed: bool
    evidence_summary: List[str]
    action: EnforcementAction
    status: EnforcementStatus
    is_simulated: bool
    allowed_to_block: bool
    policy_rule: str
    reason: str
    active_block: Optional[ActiveBlock] = None
    geo_privacy_notice: str = "Geo-location: Unverified / Not Authorized (Strict Privacy Invariant)"


class GlobalEnforcementConfig(BaseModel):
    """System-wide enforcement configuration and state."""
    operating_mode: OperatingMode = Field(
        OperatingMode.MODE_1_REAL_SITE,
        description="Active dashboard/system mode"
    )
    global_blocking_enabled: bool = Field(
        False,
        description="Master global blocking enable switch (DEFAULT: OFF)"
    )
    emergency_stop_active: bool = Field(
        False,
        description="Emergency stop switch. When TRUE, instantly overrides and halts all blocking"
    )
    sites: Dict[str, SiteConfig] = Field(
        default_factory=dict,
        description="Mode 1 Monitored sites configurations"
    )
    replica_site: SiteConfig = Field(
        default_factory=lambda: SiteConfig(
            site_id="lab-replica-site",
            name="Northstar Campus Portal (Lab Replica)",
            mode=OperatingMode.MODE_2_REPLICA_DEFENSE,
            site_url="http://127.0.0.1:8000/replica",
            routes=["/replica", "/replica/login", "/replica/portal", "/replica/admin", "/replica/admin-decoy"],
            blocking_enabled=True,
            trusted_allowlist=["127.0.0.1", "10.0.0.99"],
            enforcement_adapter="local_replica_adapter",
            block_ttl_seconds=15,
            honeypot_enabled=True,
            honeypot_routes=["/replica/admin-decoy"],
        ),
        description="Mode 2 Isolated Replica site configuration"
    )
