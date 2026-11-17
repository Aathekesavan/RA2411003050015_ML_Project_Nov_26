"""Abstract base enforcement adapter interface for SentinelX.

Defines the contract for applying temporary blocks, removing blocks,
querying active blocks, and reporting adapter simulation status.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid

from src.enforcement.models import ActiveBlock, EnforcementStatus, EnforcementAction


class BaseEnforcementAdapter(ABC):
    """Abstract interface for all SentinelX enforcement adapters."""

    def __init__(self, adapter_name: str, is_simulated: bool, adapter_status: EnforcementStatus):
        self.adapter_name = adapter_name
        self.is_simulated = is_simulated
        self.adapter_status = adapter_status
        self._blocks: Dict[str, ActiveBlock] = {}

    @abstractmethod
    def apply_block(
        self,
        target_ip: str,
        site_id: str,
        duration_seconds: int,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActiveBlock:
        """Apply a temporary block on target_ip."""
        pass

    @abstractmethod
    def remove_block(self, target_ip: str) -> bool:
        """Remove an active block on target_ip."""
        pass

    def get_active_blocks(self) -> List[ActiveBlock]:
        """Return all non-expired active blocks, pruning expired entries."""
        now_dt = datetime.now(timezone.utc)
        active: List[ActiveBlock] = []
        expired_ips: List[str] = []

        for ip, block in self._blocks.items():
            exp_dt = datetime.fromisoformat(block.expires_at)
            if now_dt < exp_dt:
                active.append(block)
            else:
                expired_ips.append(ip)

        for ip in expired_ips:
            del self._blocks[ip]

        return active

    def is_ip_blocked(self, target_ip: str) -> bool:
        """Check if target_ip is currently actively blocked."""
        self.get_active_blocks()  # Prunes expired
        return target_ip in self._blocks

    def clear_all_blocks(self) -> int:
        """Clear all active blocks."""
        count = len(self._blocks)
        self._blocks.clear()
        return count
