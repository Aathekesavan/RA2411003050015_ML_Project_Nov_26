"""Data models for log ingestion and flow correlation in SentinelX-Shift.

Defines:
- LogEvent: Standardized representation of parsed web-server and WAF events.
- ParseResult: Aggregation of successfully parsed events and malformed lines.
- CorrelationSummary: Correlated signals and metadata for a single network flow.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple


@dataclass
class LogEvent:
    """Standardized representation of a parsed web-server or WAF log event."""
    timestamp: datetime
    client_ip: str
    log_type: str  # 'nginx_access', 'nginx_error', 'modsecurity', 'waf_json'
    status_code: Optional[int] = None
    is_auth_failure: bool = False
    is_waf_alert: bool = False
    method: Optional[str] = None
    uri: Optional[str] = None
    rule_id: Optional[str] = None
    message: Optional[str] = None
    raw_line: str = ""


@dataclass
class ParseResult:
    """Result of parsing a log source, tracking successes and malformed lines."""
    events: List[LogEvent] = field(default_factory=list)
    malformed_lines: List[Tuple[int, str, str]] = field(default_factory=list)  # (line_num, raw_line, reason)
    total_lines: int = 0

    @property
    def parsed_count(self) -> int:
        return len(self.events)

    @property
    def malformed_count(self) -> int:
        return len(self.malformed_lines)


@dataclass
class CorrelationSummary:
    """Result of correlating log events with a network flow."""
    flow_id: str
    source_ip: Optional[str]
    flow_timestamp: Optional[datetime]
    window_start: Optional[datetime]
    window_end: Optional[datetime]
    matched_events_count: int
    signals: Dict[str, Any]
    correlation_successful: bool
    notes: List[str] = field(default_factory=list)
