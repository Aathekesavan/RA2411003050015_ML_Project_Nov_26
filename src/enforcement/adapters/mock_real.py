"""Mock Real-Site Enforcement Adapter for SentinelX Mode 1.

Used during development, evaluation, and demonstration:
- Explicitly labeled as SIMULATED (no real network commands sent).
- Tracks active ephemeral blocks in memory with automatic expiration.
- Does NOT send probes, simulated attacks, or firewall rules to production sites.
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from src.enforcement.adapters.base import BaseEnforcementAdapter
from src.enforcement.models import ActiveBlock, EnforcementStatus

logger = logging.getLogger(__name__)


class MockRealSiteAdapter(BaseEnforcementAdapter):
    """Mock enforcement adapter for Mode 1 Real-Site Monitoring demonstration."""

    def __init__(self, adapter_name: str = "mock_real_adapter"):
        super().__init__(
            adapter_name=adapter_name,
            is_simulated=True,
            adapter_status=EnforcementStatus.SIMULATED,
        )

    def apply_block(
        self,
        target_ip: str,
        site_id: str,
        duration_seconds: int,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActiveBlock:
        """Record a simulated block on target_ip without touching real network equipment."""
        now_dt = datetime.now(timezone.utc)
        exp_dt = now_dt + timedelta(seconds=duration_seconds)

        meta = dict(metadata or {})
        meta["real_network_action"] = False
        meta["adapter_type"] = "MockRealSiteAdapter"
        meta["simulation_notice"] = "Mock adapter: Zero network commands or firewall changes dispatched."

        block = ActiveBlock(
            block_id=f"sim-blk-{uuid.uuid4().hex[:8]}",
            target_ip=target_ip,
            site_id=site_id,
            created_at=now_dt.isoformat(),
            expires_at=exp_dt.isoformat(),
            ttl_seconds=duration_seconds,
            reason=reason,
            adapter_name=self.adapter_name,
            status=EnforcementStatus.SIMULATED,
            is_simulated=True,
            metadata=meta,
        )

        self._blocks[target_ip] = block
        logger.info(
            f"[SIMULATED MOCK BLOCK] Target {target_ip} for site '{site_id}' "
            f"blocked in-memory for {duration_seconds}s. Reason: {reason}"
        )
        return block

    def remove_block(self, target_ip: str) -> bool:
        """Remove a simulated block."""
        if target_ip in self._blocks:
            del self._blocks[target_ip]
            logger.info(f"[SIMULATED MOCK UNBLOCK] Target {target_ip} released.")
            return True
        return False
