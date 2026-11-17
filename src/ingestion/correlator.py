"""Flow and log event correlation engine for SentinelX-Shift.

Correlates parsed web-server (Nginx) and WAF (ModSecurity) log events with
network-flow records using explicit metadata fields and temporal windows.

Defensive Principle:
If matching keys (source_ip or flow timestamp) are missing or cannot be reliably
matched, the evidence is kept strictly UNAVAILABLE (present=False, confirmed=None).
It is NEVER fabricated or assumed confirmed.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Union, Tuple
import pandas as pd

from src.ingestion.models import LogEvent, CorrelationSummary

logger = logging.getLogger(__name__)

# Canonical matching key candidates
SOURCE_IP_KEYS = ["source_ip", "Source IP", "src_ip", "srcip", "Source_IP", "client_ip"]
TIMESTAMP_KEYS = ["timestamp", "Timestamp", "flow_start", "start_time", "time"]
DURATION_KEYS = ["Flow Duration", "flow_duration", "duration", "duration_ms", "duration_sec"]
FLOW_ID_KEYS = ["flow_id", "Flow ID", "id"]


def parse_flow_timestamp(val: Any) -> Optional[datetime]:
    """Parse netflow timestamp into timezone-aware UTC datetime."""
    if val is None or pd.isna(val):
        return None
    if isinstance(val, datetime):
        return val.astimezone(timezone.utc) if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, (int, float)):
        # Epoch seconds or milliseconds
        if val > 1e11:  # Milliseconds
            val = val / 1000.0
        return datetime.fromtimestamp(val, tz=timezone.utc)

    val_str = str(val).strip()
    if not val_str:
        return None

    # Try ISO format
    try:
        dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass

    # Try common netflow formats: e.g. "19/10/2026 02:00:00 PM", "2026-10-19 14:00:00"
    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M:%S %p",
        "%d/%b/%Y:%H:%M:%S %z",
        "%Y/%m/%d %H:%M:%S",
    ]:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue

    logger.warning(f"Unable to parse flow timestamp '{val_str}'")
    return None


def extract_flow_duration_seconds(flow: Dict[str, Any]) -> float:
    """Extract flow duration in seconds, handling CIC-IDS2017 microseconds convention."""
    for key in DURATION_KEYS:
        if key in flow and flow[key] is not None and not pd.isna(flow[key]):
            try:
                val = float(flow[key])
                # CIC-IDS2017 stores Flow Duration in microseconds
                if val > 10_000:
                    return max(val / 1_000_000.0, 0.001)
                return max(val, 0.001)
            except (ValueError, TypeError):
                break
    return 1.0  # Default 1.0 second span


class LogFlowCorrelator:
    """Correlates network flow records with parsed web-server and WAF log events."""

    def __init__(
        self,
        events: Optional[List[LogEvent]] = None,
        time_window_seconds: float = 30.0,
    ):
        """Initialize correlator with parsed log events.

        Args:
            events: List of parsed LogEvent objects.
            time_window_seconds: Temporal padding around flow interval (+/- delta seconds).
        """
        self.events: List[LogEvent] = events or []
        self.time_window_seconds = float(time_window_seconds)

    def add_events(self, events: List[LogEvent]) -> None:
        """Add more parsed log events to the correlator."""
        self.events.extend(events)

    def correlate_flow(self, flow: Dict[str, Any], flow_index: int = 0) -> CorrelationSummary:
        """Correlate a single flow record against available log events.

        Returns:
            CorrelationSummary containing extracted confirming signals or unavailable indicators.
        """
        # 1. Resolve Flow ID
        flow_id = None
        for k in FLOW_ID_KEYS:
            if k in flow and flow[k] is not None and not pd.isna(flow[k]):
                flow_id = str(flow[k])
                break
        if not flow_id:
            flow_id = f"flow-{flow_index}"

        # 2. Resolve Source IP
        source_ip = None
        for k in SOURCE_IP_KEYS:
            if k in flow and flow[k] is not None and not pd.isna(flow[k]):
                source_ip = str(flow[k]).strip()
                break

        # 3. Resolve Flow Timestamp
        flow_dt = None
        for k in TIMESTAMP_KEYS:
            if k in flow and flow[k] is not None:
                flow_dt = parse_flow_timestamp(flow[k])
                if flow_dt:
                    break

        notes: List[str] = []

        # Defensive Principle: If matching keys are missing, keep evidence UNAVAILABLE.
        if not source_ip or not flow_dt:
            missing_parts = []
            if not source_ip:
                missing_parts.append("Source IP")
            if not flow_dt:
                missing_parts.append("Flow Timestamp")
            reason = f"Correlation impossible: {', '.join(missing_parts)} missing from flow metadata."
            notes.append(reason)
            logger.debug(f"Flow {flow_id}: {reason}")

            return CorrelationSummary(
                flow_id=flow_id,
                source_ip=source_ip,
                flow_timestamp=flow_dt,
                window_start=None,
                window_end=None,
                matched_events_count=0,
                signals={
                    "request_rate": None,
                    "auth_failures": None,
                    "waf_alert": None,
                    "connection_attempts": None,
                },
                correlation_successful=False,
                notes=notes
            )

        # 4. Compute temporal correlation window [flow_start - delta, flow_end + delta]
        duration_sec = extract_flow_duration_seconds(flow)
        window_start = flow_dt - timedelta(seconds=self.time_window_seconds)
        window_end = flow_dt + timedelta(seconds=duration_sec + self.time_window_seconds)

        # 5. If no log events were loaded at all
        if not self.events:
            notes.append("No web-server or WAF log events loaded into correlator.")
            return CorrelationSummary(
                flow_id=flow_id,
                source_ip=source_ip,
                flow_timestamp=flow_dt,
                window_start=window_start,
                window_end=window_end,
                matched_events_count=0,
                signals={
                    "request_rate": None,
                    "auth_failures": None,
                    "waf_alert": None,
                    "connection_attempts": None,
                },
                correlation_successful=False,
                notes=notes
            )

        # 6. Filter events matching IP and temporal window
        matched_events = [
            e for e in self.events
            if e.client_ip == source_ip and (window_start <= e.timestamp <= window_end)
        ]

        matched_count = len(matched_events)
        if matched_count == 0:
            notes.append(f"Zero log events matched Source IP {source_ip} within window [{window_start.isoformat()}, {window_end.isoformat()}].")
            return CorrelationSummary(
                flow_id=flow_id,
                source_ip=source_ip,
                flow_timestamp=flow_dt,
                window_start=window_start,
                window_end=window_end,
                matched_events_count=0,
                signals={
                    "request_rate": 0.0,
                    "auth_failures": 0,
                    "waf_alert": False,
                    "connection_attempts": 0,
                    "http_status": None,
                },
                correlation_successful=True,
                notes=notes
            )

        # 7. Aggregate evidence across matched events
        auth_failures = sum(1 for e in matched_events if e.is_auth_failure)
        waf_alert = any(e.is_waf_alert for e in matched_events)
        access_events = [e for e in matched_events if e.log_type == "nginx_access"]

        # Calculate observed request rate over effective flow duration
        eff_dur = max(duration_sec, 1.0)
        request_rate = float(len(access_events)) / eff_dur

        # Most severe HTTP status observed
        statuses = [e.status_code for e in matched_events if e.status_code is not None]
        if any(s in [403, 401, 429] for s in statuses):
            most_severe_status = next(s for s in [403, 401, 429] if s in statuses)
        elif statuses:
            most_severe_status = max(statuses)
        else:
            most_severe_status = None

        connection_attempts = len(matched_events)

        notes.append(
            f"Correlated {matched_count} events for {source_ip}: "
            f"auth_failures={auth_failures}, waf_alert={waf_alert}, "
            f"request_rate={request_rate:.1f} req/s, conn_attempts={connection_attempts}"
        )

        signals_dict = {
            "request_rate": request_rate,
            "auth_failures": auth_failures,
            "waf_alert": waf_alert,
            "connection_attempts": connection_attempts,
            "http_status": most_severe_status,
        }

        return CorrelationSummary(
            flow_id=flow_id,
            source_ip=source_ip,
            flow_timestamp=flow_dt,
            window_start=window_start,
            window_end=window_end,
            matched_events_count=matched_count,
            signals=signals_dict,
            correlation_successful=True,
            notes=notes
        )

    def correlate_batch(
        self,
        flows: Union[pd.DataFrame, List[Dict[str, Any]]]
    ) -> Tuple[List[Dict[str, Any]], List[CorrelationSummary]]:
        """Correlate a batch of flow records against parsed events.

        Returns:
            Tuple of:
            - signals_list: List of signal dicts ready for SentinelGuard.analyze_flows
            - summaries: List of CorrelationSummary objects
        """
        if isinstance(flows, pd.DataFrame):
            records = flows.to_dict(orient="records")
        else:
            records = list(flows)

        signals_list: List[Dict[str, Any]] = []
        summaries: List[CorrelationSummary] = []

        for idx, flow in enumerate(records):
            summary = self.correlate_flow(flow, flow_index=idx)
            summaries.append(summary)
            signals_list.append(summary.signals)

        return signals_list, summaries
