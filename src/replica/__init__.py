"""SentinelX Mode 2 Isolated Replica Defense Package."""

from src.replica.app import replica_router, get_replica_adapter, set_replica_adapter
from src.replica.scenarios import (
    run_replica_bruteforce_scenario,
    run_replica_benign_burst_scenario,
)

__all__ = [
    "replica_router",
    "get_replica_adapter",
    "set_replica_adapter",
    "run_replica_bruteforce_scenario",
    "run_replica_benign_burst_scenario",
]
