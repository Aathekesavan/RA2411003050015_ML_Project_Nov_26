"""Local Replica Defense Enforcement Adapter for SentinelX Mode 2.

Manages local application-level blocks against the isolated replica web application:
- Real local enforcement inside the lab testbed (status: REPLICA).
- Tracks active ephemeral blocks with automatic expiration.
- Strictly isolated from Mode 1 real-site traffic, allowlists, and configurations.
"""

import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from src.enforcement.adapters.base import BaseEnforcementAdapter
from src.enforcement.models import ActiveBlock, EnforcementStatus

logger = logging.getLogger(__name__)


class LocalReplicaAdapter(BaseEnforcementAdapter):
    """Local enforcement adapter dedicated to Mode 2 Isolated Replica Defense."""

    def __init__(self, adapter_name: str = "local_replica_adapter"):
        super().__init__(
            adapter_name=adapter_name,
            is_simulated=False,
            adapter_status=EnforcementStatus.REPLICA,
        )

    def apply_block(
        self,
        target_ip: str,
        site_id: str,
        duration_seconds: int,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActiveBlock:
        """Apply a local ephemeral block against the isolated replica testbed."""
        now_dt = datetime.now(timezone.utc)
        exp_dt = now_dt + timedelta(seconds=duration_seconds)

        meta = dict(metadata or {})
        meta["lab_isolated"] = True
        meta["target_environment"] = "Local Replica Testbed (/replica)"
        meta["enforcement_type"] = "LocalReplicaAdapter"

        block = ActiveBlock(
            block_id=f"rep-blk-{uuid.uuid4().hex[:8]}",
            target_ip=target_ip,
            site_id=site_id,
            created_at=now_dt.isoformat(),
            expires_at=exp_dt.isoformat(),
            ttl_seconds=duration_seconds,
            reason=reason,
            adapter_name=self.adapter_name,
            status=EnforcementStatus.REPLICA,
            is_simulated=False,
            metadata=meta,
        )

        self._blocks[target_ip] = block
        logger.info(
            f"[REPLICA LAB BLOCK] Local replica blocked {target_ip} for {duration_seconds}s. Reason: {reason}"
        )
        return block

    def remove_block(self, target_ip: str) -> bool:
        """Remove a block from the local replica testbed."""
        if target_ip in self._blocks:
            del self._blocks[target_ip]
            logger.info(f"[REPLICA LAB UNBLOCK] Local replica released {target_ip}.")
            return True
        return False
