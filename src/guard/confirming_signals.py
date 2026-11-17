"""Independent confirming signal evaluation for the SentinelX Guard.

Evaluates behavioral signals that corroborate or constrain model scores:
- Request rates over defined time windows.
- Sequences of failed authentication attempts (essential for BruteForce).
- Web Application Firewall (WAF) or reverse proxy events.
- Repeated connection attempts from the same source IP / client.

Defensive Principle:
Missing signals are explicitly marked as unavailable/not present.
They are NEVER silently assumed to be confirmed.
"""

from typing import Dict, Any, Optional
from src.alerts.schema import ConfirmingSignalEvidence


# Standard operational default thresholds
DEFAULT_BURST_REQUEST_RATE_THRESHOLD = 50.0  # requests per second
DEFAULT_AUTH_FAILURES_THRESHOLD = 5          # failed logins/attempts
DEFAULT_CONNECTION_ATTEMPTS_THRESHOLD = 20   # repeated connection attempts


def evaluate_confirming_signals(
    signals_input: Optional[Dict[str, Any]] = None,
    burst_rate_thresh: float = DEFAULT_BURST_REQUEST_RATE_THRESHOLD,
    auth_failures_thresh: int = DEFAULT_AUTH_FAILURES_THRESHOLD,
    conn_attempts_thresh: int = DEFAULT_CONNECTION_ATTEMPTS_THRESHOLD,
) -> Dict[str, ConfirmingSignalEvidence]:
    """Evaluate independent confirming signals from input metadata.

    If signals_input is None or a specific signal is missing, it is documented
    as present=False, confirmed=None, preserving transparency.
    """
    signals = signals_input or {}
    evidence: Dict[str, ConfirmingSignalEvidence] = {}

    # 1. Request Rate Signal
    if "request_rate" in signals and signals["request_rate"] is not None:
        val = float(signals["request_rate"])
        is_confirmed = val >= burst_rate_thresh
        evidence["request_rate"] = ConfirmingSignalEvidence(
            signal_name="request_rate",
            present=True,
            value=val,
            threshold=burst_rate_thresh,
            confirmed=is_confirmed,
            description=f"Observed request rate of {val:.1f} req/s (threshold: {burst_rate_thresh:.1f} req/s; confirmed={is_confirmed})."
        )
    else:
        evidence["request_rate"] = ConfirmingSignalEvidence(
            signal_name="request_rate",
            present=False,
            value=None,
            threshold=burst_rate_thresh,
            confirmed=None,
            description="Request rate telemetry was not provided in input."
        )

    # 2. Authentication Failures Signal (Critical protocol confirmation for BruteForce)
    if "auth_failures" in signals and signals["auth_failures"] is not None:
        val = int(signals["auth_failures"])
        is_confirmed = val >= auth_failures_thresh
        evidence["auth_failures"] = ConfirmingSignalEvidence(
            signal_name="auth_failures",
            present=True,
            value=val,
            threshold=auth_failures_thresh,
            confirmed=is_confirmed,
            description=f"Observed {val} authentication failures (threshold: {auth_failures_thresh}; confirmed={is_confirmed})."
        )
    elif "failed_logins" in signals and signals["failed_logins"] is not None:
        val = int(signals["failed_logins"])
        is_confirmed = val >= auth_failures_thresh
        evidence["auth_failures"] = ConfirmingSignalEvidence(
            signal_name="auth_failures",
            present=True,
            value=val,
            threshold=auth_failures_thresh,
            confirmed=is_confirmed,
            description=f"Observed {val} failed logins (threshold: {auth_failures_thresh}; confirmed={is_confirmed})."
        )
    else:
        evidence["auth_failures"] = ConfirmingSignalEvidence(
            signal_name="auth_failures",
            present=False,
            value=None,
            threshold=auth_failures_thresh,
            confirmed=None,
            description="Authentication telemetry was not provided in input."
        )

    # 3. WAF Event / Reverse Proxy Signal
    if "waf_alert" in signals and signals["waf_alert"] is not None:
        val = bool(signals["waf_alert"])
        evidence["waf_event"] = ConfirmingSignalEvidence(
            signal_name="waf_event",
            present=True,
            value=val,
            threshold=True,
            confirmed=val,
            description=f"WAF alert trigger status: {val}."
        )
    elif "http_status" in signals and signals["http_status"] is not None:
        status_code = int(signals["http_status"])
        is_waf_anomaly = status_code in [401, 403, 429, 500, 502, 503]
        evidence["waf_event"] = ConfirmingSignalEvidence(
            signal_name="waf_event",
            present=True,
            value=status_code,
            threshold="[401, 403, 429, 5xx]",
            confirmed=is_waf_anomaly,
            description=f"HTTP response status code: {status_code} (anomaly={is_waf_anomaly})."
        )
    else:
        evidence["waf_event"] = ConfirmingSignalEvidence(
            signal_name="waf_event",
            present=False,
            value=None,
            threshold=True,
            confirmed=None,
            description="WAF / reverse proxy events not provided in input."
        )

    # 4. Repeated Connection Attempts Signal
    if "connection_attempts" in signals and signals["connection_attempts"] is not None:
        val = int(signals["connection_attempts"])
        is_confirmed = val >= conn_attempts_thresh
        evidence["connection_attempts"] = ConfirmingSignalEvidence(
            signal_name="connection_attempts",
            present=True,
            value=val,
            threshold=conn_attempts_thresh,
            confirmed=is_confirmed,
            description=f"Observed {val} connection attempts (threshold: {conn_attempts_thresh}; confirmed={is_confirmed})."
        )
    else:
        evidence["connection_attempts"] = ConfirmingSignalEvidence(
            signal_name="connection_attempts",
            present=False,
            value=None,
            threshold=conn_attempts_thresh,
            confirmed=None,
            description="Connection attempt count not provided in input."
        )

    # 5. Honeypot Decoy Trap Signal
    if "honeypot_interaction" in signals and signals["honeypot_interaction"] is not None:
        val = bool(signals["honeypot_interaction"])
        route_info = signals.get("honeypot_route", "/replica/admin-decoy") if val else ""
        evidence["honeypot_interaction"] = ConfirmingSignalEvidence(
            signal_name="honeypot_interaction",
            present=True,
            value=val,
            threshold=True,
            confirmed=val,
            description=f"Honeypot decoy trap interaction confirmed on '{route_info}'." if val else "Honeypot decoy trap evaluated: negative (no interaction)."
        )
    elif "honeypot_hit" in signals and signals["honeypot_hit"] is not None:
        val = bool(signals["honeypot_hit"])
        route_info = signals.get("honeypot_route", "/replica/admin-decoy") if val else ""
        evidence["honeypot_interaction"] = ConfirmingSignalEvidence(
            signal_name="honeypot_interaction",
            present=True,
            value=val,
            threshold=True,
            confirmed=val,
            description=f"Honeypot decoy trap hit confirmed on '{route_info}'." if val else "Honeypot decoy trap evaluated: negative."
        )
    else:
        evidence["honeypot_interaction"] = ConfirmingSignalEvidence(
            signal_name="honeypot_interaction",
            present=False,
            value=None,
            threshold=True,
            confirmed=None,
            description="Honeypot telemetry was not provided or not deployed for this site."
        )

    return evidence
