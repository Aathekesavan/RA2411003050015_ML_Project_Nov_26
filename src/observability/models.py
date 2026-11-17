"""Data models and schemas for SentinelX Phase 5 Shadow-Mode Observability.

Defines schemas for:
- LatencyStats: Empirical p50, p95, min, max, and sample counts.
- FeatureDriftMetric: Mean, std, and distributional shift per netflow feature.
- ScoreDriftMetric: Distribution shift for production, AE, and supervised scores.
- QualityCounters: Invalid records, unavailable signals, and correlation misses.
- ShadowMetricsSnapshot: Comprehensive point-in-time operational snapshot.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class LatencyStats(BaseModel):
    """Empirical inference latency distribution metrics."""
    sample_count: int = Field(0, description="Total number of evaluated samples")
    p50_ms: float = Field(0.0, description="50th percentile (median) latency in milliseconds")
    p95_ms: float = Field(0.0, description="95th percentile latency in milliseconds")
    min_ms: float = Field(0.0, description="Minimum latency in milliseconds")
    max_ms: float = Field(0.0, description="Maximum latency in milliseconds")
    mean_ms: float = Field(0.0, description="Mean latency in milliseconds")
    is_batched: bool = Field(False, description="Whether measurement was evaluated under batching (N >= 10)")


class QualityCounters(BaseModel):
    """Data quality, invalid record, and signal availability counters."""
    total_records_received: int = Field(0, description="Total flow records submitted")
    valid_records_scored: int = Field(0, description="Records successfully validated and scored")
    invalid_records_count: int = Field(0, description="Records rejected due to missing features or corrupt data")
    unavailable_signals_count: int = Field(0, description="Flows where confirming signals were unavailable (missing IP/time)")
    correlation_misses_count: int = Field(0, description="Flows with valid IP/time where zero log events matched in window")
    correlation_hits_count: int = Field(0, description="Flows successfully correlated with web/WAF events")


class DistributionSummary(BaseModel):
    """Basic statistical summary of a numerical distribution."""
    mean: float = 0.0
    std: float = 0.0
    min: float = 0.0
    p25: float = 0.0
    median: float = 0.0
    p75: float = 0.0
    max: float = 0.0


class ScoreDriftMetric(BaseModel):
    """Score drift comparison between current sliding window and baseline."""
    score_name: str  # 'production_score', 'autoencoder_score', 'supervised_score'
    baseline_stats: DistributionSummary
    current_stats: DistributionSummary
    mean_shift: float = Field(0.0, description="Absolute shift in mean score")
    std_shift: float = Field(0.0, description="Absolute shift in score standard deviation")
    drift_detected: bool = Field(False, description="Flagged if mean shift exceeds drift threshold (0.15)")


class FeatureDriftMetric(BaseModel):
    """Feature drift summary for a canonical netflow feature."""
    feature_name: str
    baseline_mean: float = 0.0
    baseline_std: float = 0.0
    current_mean: float = 0.0
    current_std: float = 0.0
    normalized_mean_shift: float = Field(0.0, description="|current_mean - baseline_mean| / (baseline_std + 1e-6)")
    drift_detected: bool = Field(False, description="Flagged if normalized shift > 2.0 std")


class ShadowMetricsSnapshot(BaseModel):
    """Complete operational observability snapshot in shadow mode."""
    snapshot_id: str
    timestamp: str
    operational_mode: str = "MONITOR_ONLY"
    autonomous_blocking_authorized: bool = False
    
    # Throughput & Alerts Breakdown
    total_flows_evaluated: int = 0
    alerts_per_hour_rate: float = 0.0
    risk_tier_counts: Dict[str, int] = Field(default_factory=dict)
    suspected_family_counts: Dict[str, int] = Field(default_factory=dict)
    
    # Queue & Review Telemetry
    queue_backlog_pending: int = 0
    analyst_review_outcomes: Dict[str, int] = Field(default_factory=dict)
    
    # Latency Distributions
    latency_single_flow: LatencyStats = Field(default_factory=LatencyStats)
    latency_batched: LatencyStats = Field(default_factory=LatencyStats)
    
    # Data Quality & Missingness
    quality: QualityCounters = Field(default_factory=QualityCounters)
    
    # Drift Observability
    score_drift: List[ScoreDriftMetric] = Field(default_factory=list)
    feature_drift: List[FeatureDriftMetric] = Field(default_factory=list)
    
    notes: List[str] = Field(default_factory=list)
