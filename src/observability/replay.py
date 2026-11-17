"""Replay runner for SentinelX Phase 5 Shadow-Mode Observability.

Replays synthetic and approved benchmark flow datasets through the ShadowEvaluator
without connecting to live network traffic or taking network actions.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd

from src.observability.engine import ShadowEvaluator
from src.observability.models import ShadowMetricsSnapshot
from src.ingestion.parsers import parse_log_file

logger = logging.getLogger(__name__)


def run_shadow_replay(
    dataset_source: str = "synthetic",
    batch_size: int = 10,
    max_flows: int = 100,
    include_logs: bool = True,
    evaluator: Optional[ShadowEvaluator] = None,
) -> Dict[str, Any]:
    """Execute a shadow-mode replay run over local sample datasets.

    Args:
        dataset_source: 'synthetic' (samples/logs/), 'sample_flows' (scratch/), or 'benchmark' (data/processed/).
        batch_size: Number of flows evaluated per batch.
        max_flows: Maximum number of flows to replay.
        include_logs: Whether to load and correlate synthetic web/WAF logs.
        evaluator: Optional custom ShadowEvaluator instance.

    Returns:
        Dictionary summarizing replay execution, snapshots generated, and latency/quality metrics.
    """
    evaluator = evaluator or ShadowEvaluator()

    # 1. Load flow dataset
    if dataset_source == "synthetic":
        flow_path = Path("data/samples/logs/synthetic_flows.csv")
        df = pd.read_csv(flow_path)
    elif dataset_source == "sample_flows":
        flow_path = Path("scratch/sample_flows.csv")
        df = pd.read_csv(flow_path)
    elif dataset_source == "benchmark":
        flow_path = Path("data/processed/cicids2017_sample60k.parquet")
        df = pd.read_parquet(flow_path).head(max_flows)
    else:
        raise ValueError(f"Unknown dataset_source '{dataset_source}'. Supported: 'synthetic', 'sample_flows', 'benchmark'")

    df = df.head(max_flows)
    total_available = len(df)
    logger.info(f"Replay starting: source={dataset_source}, total_flows={total_available}, batch_size={batch_size}")

    # 2. Optionally load sample logs
    parsed_events = []
    if include_logs and Path("data/samples/logs").exists():
        access_p = Path("data/samples/logs/nginx_access.log")
        error_p = Path("data/samples/logs/nginx_error.log")
        waf_p = Path("data/samples/logs/modsecurity_waf.log")

        if access_p.exists():
            parsed_events.extend(parse_log_file(access_p, log_type="access").events)
        if error_p.exists():
            parsed_events.extend(parse_log_file(error_p, log_type="error").events)
        if waf_p.exists():
            parsed_events.extend(parse_log_file(waf_p, log_type="waf").events)

    # 3. Stream through evaluator in batches
    snapshots: List[ShadowMetricsSnapshot] = []
    num_batches = int(np.ceil(total_available / max(batch_size, 1))) if "np" in globals() else (total_available + batch_size - 1) // batch_size

    for i in range(0, total_available, batch_size):
        chunk = df.iloc[i : i + batch_size]
        snap = evaluator.evaluate_batch(
            flows=chunk,
            logs=parsed_events if include_logs else None,
            is_replay=True,
            run_source=f"replay_{dataset_source}",
            persist_alerts_to_queue=False  # Do not pollute review queue during automated replays
        )
        snapshots.append(snap)

    latest_snap = snapshots[-1] if snapshots else None

    return {
        "status": "COMPLETED",
        "operational_mode": "MONITOR_ONLY",
        "autonomous_blocking_authorized": False,
        "dataset_source": dataset_source,
        "total_flows_replayed": total_available,
        "flows_replayed": total_available,
        "batches_processed": len(snapshots),
        "latest_snapshot_id": latest_snap.snapshot_id if latest_snap else None,
        "latest_alerts_per_hour": latest_snap.alerts_per_hour_rate if latest_snap else 0.0,
        "latest_latency_batched_p95_ms": latest_snap.latency_batched.p95_ms if latest_snap else 0.0,
        "latest_latency_single_p50_ms": latest_snap.latency_single_flow.p50_ms if latest_snap else 0.0,
        "latency": {
            "p50_ms": latest_snap.latency_single_flow.p50_ms if latest_snap else 0.0,
            "batched_p95_ms": latest_snap.latency_batched.p95_ms if latest_snap else 0.0,
        },
        "data_quality": latest_snap.quality.model_dump() if latest_snap else {},
        "notes": [
            "Replay executed safely without connecting to live traffic.",
            "Defensive Principle 1 satisfied: autonomous blocking strictly disabled (0 network actions).",
        ]
    }
