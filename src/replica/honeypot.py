"""Decoy Honeypot Trap for SentinelX Mode 2 Isolated Replica.

Provides:
- Decoy administrative trap route (/replica/admin-decoy).
- Structured honeypot_interaction telemetry recording without storing sensitive payload data.
- Strict data privacy: Never stores request bodies, passwords, tokens, or submitted form values.
- Clean distinction between real connection identity and simulated scenario identity.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel, Field


class HoneypotInteractionEvent(BaseModel):
    """Structured telemetry record for a honeypot decoy interaction."""
    event_id: str = Field(..., description="Unique honeypot event identifier")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of interaction")
    route: str = Field("/replica/admin-decoy", description="Decoy trap route accessed")
    http_method: str = Field("GET", description="HTTP method used (GET, POST, etc.)")
    source_identity: str = Field(..., description="Resolved client IP address")
    identity_type: str = Field(
        "REAL_CONNECTION",
        description="Origin classification: 'REAL_CONNECTION' or 'SIMULATED_SCENARIO'"
    )
    site_id: str = Field("lab-replica-site", description="Target site identifier")
    honeypot_name: str = Field("Northstar Admin Decoy Trap", description="Name of decoy honeypot trap")
    severity: str = Field("HIGH", description="Alert severity classification")
    description: str = Field(
        "Unauthorized probe against administrative decoy trap route",
        description="Human-readable event description"
    )
    # Explicit invariant check: no body, password, or token fields exist in schema


# In-memory store for honeypot interaction records
_honeypot_events: List[HoneypotInteractionEvent] = []
MAX_HONEYPOT_EVENTS = 500


def record_honeypot_interaction(
    route: str = "/replica/admin-decoy",
    http_method: str = "GET",
    source_identity: str = "127.0.0.1",
    identity_type: str = "REAL_CONNECTION",
    site_id: str = "lab-replica-site",
    description: Optional[str] = None,
) -> HoneypotInteractionEvent:
    """Record a structured honeypot interaction event.

    Adheres to strict privacy boundaries: NEVER stores request bodies, passwords,
    tokens, query parameters, or form data.
    """
    event = HoneypotInteractionEvent(
        event_id=f"honey-{uuid.uuid4().hex[:8]}",
        timestamp=datetime.now(timezone.utc).isoformat(),
        route=route,
        http_method=http_method.upper(),
        source_identity=source_identity,
        identity_type=identity_type,
        site_id=site_id,
        honeypot_name="Northstar Admin Decoy Trap",
        severity="HIGH",
        description=description or f"Unauthorized {http_method.upper()} probe against administrative decoy trap route '{route}'.",
    )
    _honeypot_events.insert(0, event)
    if len(_honeypot_events) > MAX_HONEYPOT_EVENTS:
        _honeypot_events.pop()
    return event


def get_honeypot_events(limit: int = 50) -> List[HoneypotInteractionEvent]:
    """Retrieve recent honeypot events."""
    return _honeypot_events[:limit]


def get_honeypot_events_for_ip(ip: str) -> List[HoneypotInteractionEvent]:
    """Retrieve honeypot events associated with a specific IP address."""
    return [e for e in _honeypot_events if e.source_identity == ip]


def clear_honeypot_events():
    """Clear in-memory honeypot records (useful for test resets)."""
    global _honeypot_events
    _honeypot_events = []
