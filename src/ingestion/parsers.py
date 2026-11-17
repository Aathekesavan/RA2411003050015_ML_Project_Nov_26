"""Parsers for Nginx access/error logs and ModSecurity/WAF events.

Provides robust, exception-safe parsing for web-tier logs, recording structured
events while isolating and reporting malformed lines without halting execution.
"""

import re
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

from src.ingestion.models import LogEvent, ParseResult

logger = logging.getLogger(__name__)

# Standard Nginx combined access log pattern
# Format: $remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"
NGINX_ACCESS_REGEX = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>[A-Z]+)\s+(?P<uri>\S+)(?:\s+(?P<proto>[^"]+))?"\s+(?P<status>\d{3})\s+(?P<bytes>\S+)(?:\s+"(?P<referer>[^"]*)"\s+"(?P<agent>[^"]*)")?'
)

# Nginx error log pattern
# Format: YYYY/MM/DD HH:MM:SS [level] pid#tid: *cid message, client: <ip>, server: ...
NGINX_ERROR_REGEX = re.compile(
    r'^(?P<time>\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(?P<level>\w+)\]\s+\d+#\d+:\s+(?:\*\d+\s+)?(?P<msg>.*?),\s+client:\s+(?P<ip>\S+)(?:,\s+server:\s+(?P<server>\S+))?(?:,\s+request:\s+"(?P<req>[^"]*)")?'
)

# ModSecurity error log / text audit pattern
MODSEC_TEXT_REGEX = re.compile(
    r'(?:\[(?P<time>[^\]]+)\]\s+)?(?:\[\S+\]\s+)*\[client\s+(?P<ip>\S+)\]\s+ModSecurity:\s+(?P<action>.*?)(?:\[id\s+"(?P<rule_id>\d+)"\])?(?:.*?\[msg\s+"(?P<msg>[^"]+)"\])?'
)


def parse_nginx_timestamp(ts_str: str) -> datetime:
    """Parse Nginx access log timestamp (e.g. '19/Oct/2026:14:00:05 +0000')."""
    ts_str = ts_str.strip()
    # Try standard Nginx access format with timezone
    try:
        return datetime.strptime(ts_str, "%d/%b/%Y:%H:%M:%S %z").astimezone(timezone.utc)
    except ValueError:
        pass

    # Try ISO8601 formats
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    # Try without timezone offset
    try:
        dt = datetime.strptime(ts_str.split()[0], "%d/%b/%Y:%H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except Exception as e:
        raise ValueError(f"Unable to parse timestamp '{ts_str}': {e}")


def parse_nginx_error_timestamp(ts_str: str) -> datetime:
    """Parse Nginx error log timestamp (e.g. '2026/10/19 14:00:05')."""
    ts_str = ts_str.strip()
    try:
        dt = datetime.strptime(ts_str, "%Y/%m/%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass

    try:
        return parse_nginx_timestamp(ts_str)
    except Exception as e:
        raise ValueError(f"Unable to parse error log timestamp '{ts_str}': {e}")


def sanitize_uri(raw_uri: str) -> str:
    """Sanitize request URI to prevent retention of sensitive query strings, tokens, or PII.

    Extracts only the request path, stripping query parameters (?token=...) and fragments (#...).
    Strictly enforces privacy preservation requirements (zero payload / sensitive parameter inspection).
    """
    if not raw_uri:
        return ""
    # Strip scheme and authority if absolute URL was provided
    if "://" in raw_uri:
        raw_uri = raw_uri.split("://", 1)[1]
        if "/" in raw_uri:
            raw_uri = "/" + raw_uri.split("/", 1)[1]
        else:
            raw_uri = "/"
    path = raw_uri.split("?")[0].split("#")[0]
    return path.strip()


def sanitize_log_line(line: str) -> str:
    """Redact sensitive query string parameters from raw log lines before storage."""
    # Redact query strings in HTTP request quotes: "METHOD /path?query HTTP/x.y" -> "METHOD /path?[REDACTED] HTTP/x.y"
    return re.sub(r'(\s+"[A-Z]+\s+[^"?\s]+)\?[^"\s]*(\s+HTTP/[^"]*")', r'\1?[REDACTED]\2', line)


class NginxAccessLogParser:
    """Parser for Nginx access logs with automatic query string redaction."""

    @staticmethod
    def parse_line(line: str, line_no: int = 1) -> Optional[LogEvent]:
        """Parse a single line from an Nginx access log. Returns None if malformed."""
        line = line.strip()
        if not line or line.startswith("#"):
            return None

        match = NGINX_ACCESS_REGEX.match(line)
        if not match:
            raise ValueError(f"Line does not match Nginx access log pattern: '{line[:80]}'")

        d = match.groupdict()
        try:
            dt = parse_nginx_timestamp(d["time"])
        except Exception as e:
            raise ValueError(f"Timestamp parsing error: {e}")

        status_code = int(d["status"])
        is_auth_failure = (status_code == 401)
        sanitized_uri = sanitize_uri(d["uri"])
        clean_raw_line = sanitize_log_line(line)

        return LogEvent(
            timestamp=dt,
            client_ip=d["ip"],
            log_type="nginx_access",
            status_code=status_code,
            is_auth_failure=is_auth_failure,
            is_waf_alert=(status_code == 403),
            method=d["method"],
            uri=sanitized_uri,
            message=f"HTTP {status_code} {d['method']} {sanitized_uri}",
            raw_line=clean_raw_line
        )

    def parse(self, text_or_lines: Union[str, List[str]]) -> ParseResult:
        """Parse multiple log lines, gracefully isolating malformed lines."""
        if isinstance(text_or_lines, str):
            lines = text_or_lines.splitlines()
        else:
            lines = text_or_lines

        result = ParseResult(total_lines=len(lines))
        for idx, line in enumerate(lines, 1):
            if not line.strip() or line.strip().startswith("#"):
                continue
            try:
                event = self.parse_line(line, line_no=idx)
                if event:
                    result.events.append(event)
            except Exception as e:
                result.malformed_lines.append((idx, line, str(e)))

        return result


class NginxErrorLogParser:
    """Parser for Nginx error logs with authentication failure detection."""

    AUTH_KEYWORDS = [
        "password mismatch",
        "user was not found",
        "authentication failure",
        "auth failure",
        "failed to authenticate",
        "invalid credentials",
        "client unauthorized",
    ]

    @classmethod
    def parse_line(cls, line: str, line_no: int = 1) -> Optional[LogEvent]:
        """Parse a single line from an Nginx error log."""
        line = line.strip()
        if not line or line.startswith("#"):
            return None

        match = NGINX_ERROR_REGEX.match(line)
        if not match:
            raise ValueError(f"Line does not match Nginx error log pattern: '{line[:80]}'")

        d = match.groupdict()
        try:
            dt = parse_nginx_error_timestamp(d["time"])
        except Exception as e:
            raise ValueError(f"Timestamp parsing error: {e}")

        msg = d["msg"]
        msg_lower = msg.lower()
        is_auth_failure = any(kw in msg_lower for kw in cls.AUTH_KEYWORDS)
        client_ip = d["ip"].rstrip(",").strip()

        return LogEvent(
            timestamp=dt,
            client_ip=client_ip,
            log_type="nginx_error",
            status_code=401 if is_auth_failure else None,
            is_auth_failure=is_auth_failure,
            is_waf_alert="limiting requests" in msg_lower,
            message=f"[{d['level']}] {msg}",
            raw_line=line
        )

    def parse(self, text_or_lines: Union[str, List[str]]) -> ParseResult:
        """Parse multiple error log lines."""
        if isinstance(text_or_lines, str):
            lines = text_or_lines.splitlines()
        else:
            lines = text_or_lines

        result = ParseResult(total_lines=len(lines))
        for idx, line in enumerate(lines, 1):
            if not line.strip() or line.strip().startswith("#"):
                continue
            try:
                event = self.parse_line(line, line_no=idx)
                if event:
                    result.events.append(event)
            except Exception as e:
                result.malformed_lines.append((idx, line, str(e)))

        return result


class ModSecurityParser:
    """Parser for ModSecurity / WAF events in text or JSON format."""

    @staticmethod
    def parse_line(line: str, line_no: int = 1) -> Optional[LogEvent]:
        """Parse a single line of ModSecurity text or JSON event."""
        line = line.strip()
        if not line or line.startswith("#"):
            return None

        # 1. Attempt JSON parsing
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                client_ip = data.get("client_ip", data.get("client", data.get("src_ip", "")))
                if not client_ip:
                    raise ValueError("JSON WAF event missing client_ip field")

                ts_raw = data.get("timestamp", data.get("time", ""))
                if not ts_raw:
                    raise ValueError("JSON WAF event missing timestamp field")
                dt = parse_nginx_timestamp(ts_raw)

                status_code = data.get("status", data.get("status_code", 403))
                rule_id = str(data.get("rule_id", data.get("id", "")))
                msg = data.get("message", data.get("msg", "WAF Alert triggered"))
                action = data.get("action", "alert")

                return LogEvent(
                    timestamp=dt,
                    client_ip=client_ip,
                    log_type="waf_json",
                    status_code=int(status_code) if status_code else 403,
                    is_auth_failure=(int(status_code) == 401 if status_code else False),
                    is_waf_alert=True,
                    rule_id=rule_id if rule_id else None,
                    message=f"ModSecurity WAF [id={rule_id}]: {msg} (action={action})",
                    raw_line=line
                )
            except json.JSONDecodeError as jde:
                raise ValueError(f"Malformed JSON WAF event: {jde}")

        # 2. Attempt Text ModSecurity regex
        if "ModSecurity:" in line:
            ip_m = re.search(r'\[client\s+([^\s\]]+)\]', line)
            if not ip_m:
                raise ValueError(f"Line does not match ModSecurity format: '{line[:80]}'")
            client_ip = ip_m.group(1).rstrip(",")

            time_m = re.search(r'^\[([^\]]+)\]', line)
            if time_m:
                try:
                    dt = parse_nginx_timestamp(time_m.group(1))
                except Exception:
                    dt = datetime.now(timezone.utc)
            else:
                dt = datetime.now(timezone.utc)

            id_m = re.search(r'\[id\s+"?(\d+)"?\]', line)
            rule_id = id_m.group(1) if id_m else None

            msg_m = re.search(r'\[msg\s+"([^"]+)"\]', line)
            msg = msg_m.group(1) if msg_m else "ModSecurity Rule Triggered"

            code_m = re.search(r'(?:code|status)\s+(\d+)', line)
            status_code = int(code_m.group(1)) if code_m else 403

            return LogEvent(
                timestamp=dt,
                client_ip=client_ip,
                log_type="modsecurity",
                status_code=status_code,
                is_auth_failure=(status_code == 401),
                is_waf_alert=True,
                rule_id=rule_id,
                message=f"ModSecurity [id={rule_id}]: {msg}",
                raw_line=line
            )

        raise ValueError(f"Line does not match ModSecurity format: '{line[:80]}'")


    def parse(self, text_or_lines: Union[str, List[str]]) -> ParseResult:
        """Parse multiple ModSecurity log lines."""
        if isinstance(text_or_lines, str):
            lines = text_or_lines.splitlines()
        else:
            lines = text_or_lines

        result = ParseResult(total_lines=len(lines))
        for idx, line in enumerate(lines, 1):
            if not line.strip() or line.strip().startswith("#"):
                continue
            try:
                event = self.parse_line(line, line_no=idx)
                if event:
                    result.events.append(event)
            except Exception as e:
                result.malformed_lines.append((idx, line, str(e)))

        return result


def parse_log_file(filepath: Union[str, Path], log_type: str = "auto") -> ParseResult:
    """Parse log file with automatic or explicit parser selection."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {path}")

    content = path.read_text(encoding="utf-8", errors="replace")
    
    if log_type == "access" or (log_type == "auto" and "access" in path.name.lower()):
        return NginxAccessLogParser().parse(content)
    elif log_type == "error" or (log_type == "auto" and "error" in path.name.lower()):
        return NginxErrorLogParser().parse(content)
    elif log_type in ["modsec", "waf"] or (log_type == "auto" and any(k in path.name.lower() for k in ["waf", "modsec"])):
        return ModSecurityParser().parse(content)
    else:
        # Fallback heuristic: try access first, then modsec, then error
        res = NginxAccessLogParser().parse(content)
        if res.parsed_count > 0:
            return res
        res_sec = ModSecurityParser().parse(content)
        if res_sec.parsed_count > 0:
            return res_sec
        return NginxErrorLogParser().parse(content)
