"""Schema definitions for SentinelX-Shift alerts and API responses.

Defines Pydantic models for:
- Risk tiers and recommended analyst triage actions.
- Model score breakdowns (Autoencoder, XGBoost, Gated Boost).
- Independent confirming signal evidence.
- Structured flow alerts and batch alert responses.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class RiskTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendedAction(str, Enum):
    ALLOW = "ALLOW"
    MONITOR = "MONITOR"
    INVESTIGATE_FLOW = "INVESTIGATE_FLOW"
    ESCALATE_TO_ANALYST = "ESCALATE_TO_ANALYST"


class ScoresBreakdown(BaseModel):
    """Breakdown of calibrated individual and fused detection scores in [0, 1]."""
    supervised_score: float = Field(..., ge=0.0, le=1.0, description="Calibrated XGBoost attack probability")
    autoencoder_score: float = Field(..., ge=0.0, le=1.0, description="Calibrated Autoencoder reconstruction anomaly score")
    iforest_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Calibrated Isolation Forest score")
    mean_anomaly_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Average anomaly score (AE + IForest)")
    production_score: float = Field(..., ge=0.0, le=1.0, description="Autoencoder-Anchored Gated Boost production score")
    gated_activation: bool = Field(..., description="Whether supervised score exceeded activation threshold tau")
    tau: float = Field(..., description="High-confidence activation threshold")
    gamma: float = Field(..., description="Boost increment magnitude")


class ConfirmingSignalEvidence(BaseModel):
    """Evidence structure for independent confirming signals."""
    signal_name: str
    present: bool = Field(..., description="Whether this signal was provided in the input telemetry")
    value: Optional[Any] = Field(None, description="Observed value if present")
    threshold: Optional[Any] = Field(None, description="Evaluation threshold if applicable")
    confirmed: Optional[bool] = Field(None, description="True if confirmed, False if evaluated negative, None if unavailable")
    description: str = Field(..., description="Explanatory description or unavailability note")


class FlowAlert(BaseModel):
    """Complete structured alert for an analyzed network flow record."""
    alert_id: str = Field(..., description="Unique UUID for this alert")
    timestamp: str = Field(..., description="ISO 8601 alert generation timestamp")
    flow_id: Optional[str] = Field(None, description="Identifier of the flow if provided in metadata")
    risk_tier: RiskTier
    recommended_action: RecommendedAction
    autonomous_blocking_authorized: bool = Field(
        default=False,
        description="Strictly False: SentinelX operates in monitor-and-recommend mode only"
    )
    scores: ScoresBreakdown
    confirming_signals: Dict[str, ConfirmingSignalEvidence]
    suspected_family: Optional[str] = Field(None, description="Suspected attack family if high confidence")
    policy_notes: List[str] = Field(default_factory=list, description="Policy and guardrail notes applied")
    batch_id: Optional[str] = Field(None, description="Optional batch or ingestion run identifier")


class AlertResponse(BaseModel):
    """Response payload for flow scoring batch or single record."""
    total_flows: int = Field(..., description="Total flows received and processed")
    alerts_generated: int = Field(..., description="Count of alerts generated")
    high_priority_count: int = Field(0, description="Count of HIGH or CRITICAL priority alerts")
    alerts: List[FlowAlert]
    execution_time_ms: float = Field(..., description="Total execution latency in milliseconds")
    model_family: str = Field(..., description="Loaded production model identifier")
    guard_mode: str = Field("MONITOR_ONLY", description="Operational guard mode")


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED_INCIDENT = "CONFIRMED_INCIDENT"
    BENIGN_SUPPRESSED = "BENIGN_SUPPRESSED"
    IN_INVESTIGATION = "IN_INVESTIGATION"
    ESCALATED_TIER_2 = "ESCALATED_TIER_2"


class ReviewAction(str, Enum):
    CONFIRM_INCIDENT = "CONFIRM_INCIDENT"
    MARK_BENIGN = "MARK_BENIGN"
    SUPPRESS_ALERT = "SUPPRESS_ALERT"
    INVESTIGATE_FURTHER = "INVESTIGATE_FURTHER"
    ESCALATE_TIER_2 = "ESCALATE_TIER_2"


class ReviewRecord(BaseModel):
    """Record of an analyst decision on an alert."""
    alert_id: str
    action: ReviewAction
    status: ReviewStatus
    analyst_id: str = "analyst-1"
    timestamp: str
    notes: Optional[str] = None


class QueueAlert(BaseModel):
    """Enriched alert object displayed in the analyst review queue."""
    alert: FlowAlert
    review_status: ReviewStatus = ReviewStatus.PENDING
    latest_review: Optional[ReviewRecord] = None
    flow_telemetry: Optional[Dict[str, Any]] = None


class QueueResponse(BaseModel):
    """Response payload for analyst review queue query."""
    total_matching: int
    returned_count: int
    queue_stats: Dict[str, int]
    alerts: List[QueueAlert]
    guard_mode: str = "MONITOR_ONLY"

