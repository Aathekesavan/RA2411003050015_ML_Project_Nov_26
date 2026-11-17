"""Generate synthetic web server (Nginx) and WAF (ModSecurity) log files for Phase 3 demo.

Uses synthetic non-routable documentation IPs (RFC 5737: 198.51.100.0/24, 203.0.113.0/24)
to ensure no real sensitive traffic is stored.
"""

from pathlib import Path


def generate_samples(output_dir: Path = Path("data/samples/logs")):
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Nginx access log
    access_lines = [
        '# Nginx Access Log - Synthetic Telemetry',
        '192.0.2.10 - - [19/Oct/2026:14:10:00 +0000] "GET /index.html HTTP/1.1" 200 1024 "-" "Mozilla/5.0"',
        '192.0.2.11 - - [19/Oct/2026:14:12:00 +0000] "GET /favicon.ico HTTP/1.1" 200 342 "-" "Mozilla/5.0"',
    ]

    # Scenario 1: Slow-rate Brute Force (8 requests over ~12s = ~0.67 req/s; 401 Unauthorized)
    for i in range(1, 9):
        sec = f"{i:02d}"
        access_lines.append(
            f'198.51.100.42 - admin [19/Oct/2026:14:15:{sec} +0000] "POST /api/v1/auth/login HTTP/1.1" 401 128 "-" "python-requests/2.28"'
        )

    # Scenario 2: Benign Traffic Burst (75 requests at 14:20:00, all 200 OK)
    for _ in range(75):
        access_lines.append(
            '203.0.113.88 - - [19/Oct/2026:14:20:00 +0000] "GET /static/bundle.min.js HTTP/1.1" 200 4520 "https://app.internal/" "Mozilla/5.0"'
        )

    # Malformed access lines (to test parser robustness)
    access_lines.append('MALFORMED_LINE_WITHOUT_IP_OR_BRACKETS - - garbage HTTP text')
    access_lines.append('198.51.100.99 - - [INVALID_DATE_FORMAT] "GET /test HTTP/1.1" 200 123 "-" "curl/7.68.0"')
    access_lines.append('corrupt raw binary \x00\x01\x02 truncated line')

    access_path = output_dir / "nginx_access.log"
    access_path.write_text("\n".join(access_lines) + "\n", encoding="utf-8")

    # 2. Nginx error log
    error_lines = [
        '# Nginx Error Log - Synthetic Telemetry',
        '2026/10/19 14:00:00 [notice] 1001#1001: using the "epoll" event method',
        '2026/10/19 14:00:00 [notice] 1001#1001: start worker process 1002',
    ]

    # Scenario 1: Error log entries for the authentication failures
    for i in range(1, 9):
        sec = f"{i:02d}"
        error_lines.append(
            f'2026/10/19 14:15:{sec} [error] 1002#1002: *{100+i} user "admin": password mismatch, client: 198.51.100.42, server: api.internal, request: "POST /api/v1/auth/login HTTP/1.1"'
        )

    # Malformed error lines
    error_lines.append('2026/10/19 14:15:00 [crit] invalid line with missing client parameter')
    error_lines.append('broken timestamp log line [error] client: 1.2.3.4')

    error_path = output_dir / "nginx_error.log"
    error_path.write_text("\n".join(error_lines) + "\n", encoding="utf-8")

    # 3. ModSecurity WAF log
    waf_lines = [
        '# ModSecurity WAF Log - Synthetic Telemetry',
        '[2026-10-19 14:15:08 +0000] [client 198.51.100.42] ModSecurity: Access denied with code 403 (phase 2). [id "200002"] [msg "Rule 200002: Excessive Authentication Failures Triggered"] [severity "WARNING"] [uri "/api/v1/auth/login"]',
        '{"timestamp": "2026-10-19T14:15:10Z", "client_ip": "198.51.100.42", "status": 403, "rule_id": 200002, "message": "Excessive Failed Logins Threshold Exceeded", "action": "alert"}',
        # Malformed WAF lines
        '{"timestamp": "2026-10-19T14:15:10Z", malformed_json_missing_brace',
        'Just random text in waf file without client or brackets',
    ]

    waf_path = output_dir / "modsecurity_waf.log"
    waf_path.write_text("\n".join(waf_lines) + "\n", encoding="utf-8")

    print(f"Generated synthetic logs in {output_dir}:")
    print(f"  - {access_path} ({len(access_lines)} lines)")
    print(f"  - {error_path} ({len(error_lines)} lines)")
    print(f"  - {waf_path} ({len(waf_lines)} lines)")


if __name__ == "__main__":
    generate_samples()
