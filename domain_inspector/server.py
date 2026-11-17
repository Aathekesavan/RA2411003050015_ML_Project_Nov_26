#!/usr/bin/env python3
"""
SentinelX Standalone Domain Security Inspector Server.

Serves the standalone SentinelX domain-checking website and provides
a safe, non-disruptive, read-only public exterior verification API.

SAFETY & INTEGRITY CONSTRAINTS:
- Strictly limited to non-disruptive public checks:
    * HTTPS availability and HTTP-to-HTTPS redirects
    * TLS certificate validity, issuer, expiration, and protocol version
    * Standard HTTP security headers (HSTS, CSP, XFO, XCTO, Referrer-Policy)
    * Public DNS & email authentication records (SPF, DMARC, CAA, MX) via DoH
    * RFC 9116 security disclosure document (/.well-known/security.txt)
- ZERO intrusive testing: no exploitation, password attempts, DoS tests, or port scans.
- Explicit authorization parameter required.
- Only verified evidence is reported; simulated samples are strictly labeled.
"""

import sys
import os
import re
import json
import ssl
import socket
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("SENTINELX_PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

USER_AGENT = "SentinelX-Domain-Inspector/2.0 (+https://sentinelx.local; polite public verification)"


def safe_query_doh(name: str, record_type: str = "TXT") -> list:
    """Query public DNS-over-HTTPS (Cloudflare DoH with Google fallback) for read-only records."""
    urls = [
        f"https://cloudflare-dns.com/dns-query?name={urllib.parse.quote(name)}&type={record_type}",
        f"https://dns.google/resolve?name={urllib.parse.quote(name)}&type={record_type}",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/dns-json",
                    "User-Agent": USER_AGENT,
                },
            )
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                answers = data.get("Answer", [])
                results = []
                for ans in answers:
                    val = ans.get("data", "").strip(' "')
                    if val:
                        results.append(val)
                return results
        except Exception:
            continue
    return []


def check_tls_certificate(domain: str) -> dict:
    """Safely inspect TLS certificate via standard SSL handshake on port 443 with SNI."""
    try:
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        with socket.create_connection((domain, 443), timeout=4.0) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                cipher = ssock.cipher()
                version = ssock.version()

                # Extract Issuer
                issuer_dict = dict(x[0] for x in cert.get("issuer", []))
                issuer_name = issuer_dict.get("commonName") or issuer_dict.get("organizationName") or "Known Certificate Authority"

                # Extract Subject
                subject_dict = dict(x[0] for x in cert.get("subject", []))
                subject_cn = subject_dict.get("commonName", domain)

                # Extract SANs
                sans = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"]

                # Expiration parsing
                not_after_str = cert.get("notAfter", "")
                days_left = None
                if not_after_str:
                    try:
                        exp_date = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                        now = datetime.now(timezone.utc)
                        days_left = (exp_date - now).days
                    except Exception:
                        pass

                return {
                    "valid": True,
                    "issuer": issuer_name,
                    "subject": subject_cn,
                    "sans": sans[:10],
                    "version": version,
                    "cipher": cipher[0] if cipher else "Unknown",
                    "expires_in_days": days_left,
                    "raw_expiration": not_after_str,
                }
    except ssl.SSLCertVerificationError as e:
        return {"valid": False, "error": f"TLS Verification Failed: {e.reason}", "unverified": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def check_https_and_headers(domain: str) -> dict:
    """Fetch HTTP/HTTPS response headers and check redirection."""
    result = {
        "http_redirects_to_https": False,
        "https_available": False,
        "final_url": "",
        "status_code": 0,
        "headers": {},
        "server_banner": "",
        "security_txt_found": False,
        "security_txt_preview": "",
    }

    # 1. Test HTTP to HTTPS redirect
    try:
        http_url = f"http://{domain}/"
        req = urllib.request.Request(
            http_url,
            headers={"User-Agent": USER_AGENT},
            method="GET",
        )
        # Custom redirect tracker
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                nonlocal result
                if newurl.lower().startswith("https://"):
                    result["http_redirects_to_https"] = True
                return None

        opener = urllib.request.build_opener(NoRedirectHandler)
        try:
            with opener.open(req, timeout=4.0) as resp:
                if resp.geturl().lower().startswith("https://"):
                    result["http_redirects_to_https"] = True
        except urllib.error.HTTPError as he:
            loc = he.headers.get("Location", "")
            if loc.lower().startswith("https://"):
                result["http_redirects_to_https"] = True
    except Exception:
        pass

    # 2. Test HTTPS endpoint & retrieve security headers
    try:
        https_url = f"https://{domain}/"
        req = urllib.request.Request(
            https_url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=4.5) as resp:
            result["https_available"] = True
            result["status_code"] = resp.getcode()
            result["final_url"] = resp.geturl()

            for k, v in resp.headers.items():
                result["headers"][k.lower()] = v

            result["server_banner"] = resp.headers.get("Server", "") or resp.headers.get("X-Powered-By", "")
    except urllib.error.HTTPError as he:
        result["https_available"] = True
        result["status_code"] = he.code
        result["final_url"] = he.geturl()
        for k, v in he.headers.items():
            result["headers"][k.lower()] = v
        result["server_banner"] = he.headers.get("Server", "") or he.headers.get("X-Powered-By", "")
    except Exception as e:
        result["https_error"] = str(e)

    # 3. Test RFC 9116 security.txt
    try:
        sec_url = f"https://{domain}/.well-known/security.txt"
        req = urllib.request.Request(sec_url, headers={"User-Agent": USER_AGENT}, method="GET")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.getcode() == 200:
                body = resp.read(1024).decode("utf-8", errors="ignore")
                if "contact:" in body.lower():
                    result["security_txt_found"] = True
                    result["security_txt_preview"] = body[:200].strip()
    except Exception:
        pass

    return result


def inspect_domain_public(domain: str) -> dict:
    """Conduct strictly safe, non-disruptive exterior public security checks."""
    checks = []

    # 1. TLS Certificate Check
    tls_info = check_tls_certificate(domain)
    if tls_info.get("valid"):
        checks.append({
            "id": "tls_cert",
            "category": "Encryption & TLS",
            "title": "TLS Certificate & Cryptographic Handshake",
            "status": "PASS",
            "severity": "Good",
            "verified": True,
            "evidence": f"Issuer: {tls_info['issuer']} | Protocol: {tls_info['version']} | Cipher: {tls_info['cipher']} | Expires in {tls_info.get('expires_in_days', '?')} days",
            "recommendation": "Maintain automated certificate renewal before expiration.",
        })
    else:
        err = tls_info.get("error", "Unable to establish secure TLS handshake")
        checks.append({
            "id": "tls_cert",
            "category": "Encryption & TLS",
            "title": "TLS Certificate & Cryptographic Handshake",
            "status": "FAIL",
            "severity": "High",
            "verified": True,
            "evidence": f"TLS Connection failed: {err}",
            "recommendation": "Configure a valid, trusted TLS certificate using modern automated tooling (e.g., Let's Encrypt).",
        })

    # 2. HTTPS & Redirection Check
    http_data = check_https_and_headers(domain)
    if http_data.get("https_available"):
        redir_ok = http_data.get("http_redirects_to_https")
        checks.append({
            "id": "https_redirect",
            "category": "Transport Security",
            "title": "HTTPS Redirection & Downgrade Prevention",
            "status": "PASS" if redir_ok else "WARN",
            "severity": "Good" if redir_ok else "Medium",
            "verified": True,
            "evidence": (
                f"HTTP-to-HTTPS redirect verified (Status: {http_data['status_code']})"
                if redir_ok
                else "Unencrypted HTTP does not automatically redirect to HTTPS."
            ),
            "recommendation": "Enforce HTTP 301 redirection from http:// to https:// on all requests.",
        })
    else:
        checks.append({
            "id": "https_redirect",
            "category": "Transport Security",
            "title": "HTTPS Redirection & Downgrade Prevention",
            "status": "FAIL",
            "severity": "High",
            "verified": True,
            "evidence": f"HTTPS endpoint not answering on port 443 ({http_data.get('https_error', 'Connection refused')})",
            "recommendation": "Enable HTTPS listener on port 443 with TLS 1.2 or 1.3.",
        })

    headers = http_data.get("headers", {})

    # 3. HSTS Header
    hsts = headers.get("strict-transport-security")
    if hsts:
        checks.append({
            "id": "hsts",
            "category": "Security Headers",
            "title": "HTTP Strict Transport Security (HSTS)",
            "status": "PASS",
            "severity": "Good",
            "verified": True,
            "evidence": f"Strict-Transport-Security: {hsts}",
            "recommendation": "Keep HSTS enabled with long max-age (>= 31536000 seconds).",
        })
    else:
        checks.append({
            "id": "hsts",
            "category": "Security Headers",
            "title": "HTTP Strict Transport Security (HSTS)",
            "status": "WARN",
            "severity": "Medium",
            "verified": True,
            "evidence": "Strict-Transport-Security header absent from HTTPS response.",
            "recommendation": "Add 'Strict-Transport-Security: max-age=31536000; includeSubDomains' to server configuration.",
        })

    # 4. Content Security Policy (CSP)
    csp = headers.get("content-security-policy")
    if csp:
        checks.append({
            "id": "csp",
            "category": "Security Headers",
            "title": "Content Security Policy (CSP)",
            "status": "PASS",
            "severity": "Good",
            "verified": True,
            "evidence": f"Content-Security-Policy: {csp[:120]}...",
            "recommendation": "Periodically audit allowed script sources and enforce restrictive directives.",
        })
    else:
        checks.append({
            "id": "csp",
            "category": "Security Headers",
            "title": "Content Security Policy (CSP)",
            "status": "WARN",
            "severity": "Low",
            "verified": True,
            "evidence": "Content-Security-Policy header absent from HTTPS response.",
            "recommendation": "Deploy Content-Security-Policy to mitigate cross-site scripting and unauthorized data exfiltration.",
        })

    # 5. Framing and MIME Protection (XFO, XCTO)
    xfo = headers.get("x-frame-options")
    xcto = headers.get("x-content-type-options")
    if xcto == "nosniff" and (xfo or csp):
        checks.append({
            "id": "frame_mime",
            "category": "Security Headers",
            "title": "Clickjacking & MIME-Sniffing Defenses",
            "status": "PASS",
            "severity": "Good",
            "verified": True,
            "evidence": f"X-Content-Type-Options: {xcto} | X-Frame-Options: {xfo or 'Guarded by CSP'}",
            "recommendation": "Maintain X-Content-Type-Options: nosniff and restrictive frame-ancestors.",
        })
    else:
        missing = []
        if xcto != "nosniff":
            missing.append("X-Content-Type-Options: nosniff")
        if not xfo and not csp:
            missing.append("X-Frame-Options: SAMEORIGIN")
        checks.append({
            "id": "frame_mime",
            "category": "Security Headers",
            "title": "Clickjacking & MIME-Sniffing Defenses",
            "status": "WARN",
            "severity": "Low",
            "verified": True,
            "evidence": f"Missing or incomplete headers: {', '.join(missing)}",
            "recommendation": "Configure 'X-Content-Type-Options: nosniff' and 'X-Frame-Options: SAMEORIGIN'.",
        })

    # 6. Email Security: SPF Record
    txt_records = safe_query_doh(domain, "TXT")
    spf_record = next((r for r in txt_records if r.lower().startswith("v=spf1")), None)
    if spf_record:
        checks.append({
            "id": "spf",
            "category": "Email & DNS Hygiene",
            "title": "Sender Policy Framework (SPF) Verification",
            "status": "PASS",
            "severity": "Good",
            "verified": True,
            "evidence": f"TXT Record: {spf_record}",
            "recommendation": "Maintain authorized sending IP addresses and avoid permissive '?all' or '+all' qualifiers.",
        })
    else:
        checks.append({
            "id": "spf",
            "category": "Email & DNS Hygiene",
            "title": "Sender Policy Framework (SPF) Verification",
            "status": "WARN",
            "severity": "Medium",
            "verified": True,
            "evidence": f"No TXT record starting with 'v=spf1' located for {domain}.",
            "recommendation": "Publish an SPF TXT record designating permitted mail servers to reduce email spoofing.",
        })

    # 7. Email Security: DMARC Policy
    dmarc_records = safe_query_doh(f"_dmarc.{domain}", "TXT")
    dmarc_record = next((r for r in dmarc_records if "v=dmarc1" in r.lower()), None)
    if dmarc_record:
        checks.append({
            "id": "dmarc",
            "category": "Email & DNS Hygiene",
            "title": "DMARC Spoofing Protection Policy",
            "status": "PASS",
            "severity": "Good",
            "verified": True,
            "evidence": f"TXT Record at _dmarc.{domain}: {dmarc_record}",
            "recommendation": "Monitor aggregate delivery reports (rua) and progressively advance policy to 'p=quarantine' or 'p=reject'.",
        })
    else:
        checks.append({
            "id": "dmarc",
            "category": "Email & DNS Hygiene",
            "title": "DMARC Spoofing Protection Policy",
            "status": "WARN",
            "severity": "Low",
            "verified": True,
            "evidence": f"No DMARC record observed at _dmarc.{domain}.",
            "recommendation": "Add a TXT record at _dmarc.{domain} with at least 'v=DMARC1; p=none; rua=mailto:dmarc@{domain}'.",
        })

    # 8. Certificate Authority Authorization (CAA)
    caa_records = safe_query_doh(domain, "CAA")
    if caa_records:
        checks.append({
            "id": "caa",
            "category": "DNS & Authority Defenses",
            "title": "Certificate Authority Authorization (CAA)",
            "status": "PASS",
            "severity": "Good",
            "verified": True,
            "evidence": f"CAA Records: {', '.join(caa_records[:3])}",
            "recommendation": "Explicitly whitelist allowed CAs to prevent unauthorized certificate issuance.",
        })
    else:
        checks.append({
            "id": "caa",
            "category": "DNS & Authority Defenses",
            "title": "Certificate Authority Authorization (CAA)",
            "status": "INFO",
            "severity": "Info",
            "verified": True,
            "evidence": f"No CAA records published for {domain}. Any public CA can issue certificates if ownership is proven.",
            "recommendation": "Consider adding CAA DNS records to restrict certificate issuance to your designated provider.",
        })

    # 9. Security.txt Vulnerability Disclosure Policy
    if http_data.get("security_txt_found"):
        checks.append({
            "id": "security_txt",
            "category": "Vulnerability Disclosure",
            "title": "RFC 9116 Security Disclosure Policy (security.txt)",
            "status": "PASS",
            "severity": "Good",
            "verified": True,
            "evidence": f"GET /.well-known/security.txt -> 200 OK ({http_data.get('security_txt_preview', '')[:100]}...)",
            "recommendation": "Keep security contacts and PGP key signatures updated.",
        })
    else:
        checks.append({
            "id": "security_txt",
            "category": "Vulnerability Disclosure",
            "title": "RFC 9116 Security Disclosure Policy (security.txt)",
            "status": "INFO",
            "severity": "Info",
            "verified": True,
            "evidence": "RFC 9116 security contact file was not located at /.well-known/security.txt.",
            "recommendation": "Publish security contact instructions at /.well-known/security.txt for coordinated vulnerability disclosure.",
        })

    # Calculate summary
    passed_count = sum(1 for c in checks if c["status"] == "PASS")
    actionable_count = sum(1 for c in checks if c["status"] in ("WARN", "FAIL"))
    info_count = sum(1 for c in checks if c["status"] == "INFO")

    return {
        "status": "success",
        "domain": domain,
        "is_live_verified": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_areas": len(checks),
            "passed": passed_count,
            "actionable": actionable_count,
            "informational": info_count,
            "health_score": max(20, min(100, int((passed_count / len(checks)) * 100))),
        },
        "checks": checks,
    }


class SentinelXHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler serving REPLICA static files and the public domain inspector API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/api/check":
            query = urllib.parse.parse_qs(parsed.query)
            domain = query.get("domain", [""])[0].strip()
            authorized = query.get("authorized", ["false"])[0].lower() in ("true", "1", "yes")

            # Basic clean
            domain = re.sub(r"^https?://", "", domain, flags=re.I)
            domain = domain.split("/")[0].split(":")[0].strip()

            if not domain or not DOMAIN_REGEX.match(domain):
                self._send_json(400, {
                    "status": "error",
                    "error": "Invalid target domain format. Please provide a valid hostname (e.g., example.com).",
                })
                return

            if not authorized:
                self._send_json(403, {
                    "status": "error",
                    "error": "Authorization confirmation required. You must confirm permission to inspect the target domain.",
                })
                return

            try:
                report = inspect_domain_public(domain)
                self._send_json(200, report)
            except Exception as e:
                self._send_json(500, {
                    "status": "error",
                    "error": f"Verification inspection failed: {str(e)}",
                })
            return

        # Serve static files as normal
        return super().do_GET()

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Clean terminal output
        sys.stderr.write(f"[SentinelX Standalone] {self.address_string()} - {format % args}\n")


def main():
    server_address = ("127.0.0.1", PORT)
    httpd = ThreadingHTTPServer(server_address, SentinelXHandler)
    print(f"\n=======================================================")
    print(f"  SentinelX Standalone Domain Security Inspector")
    print(f"  URL: http://localhost:{PORT}/")
    print(f"  Root: {BASE_DIR}")
    print(f"  API: http://localhost:{PORT}/api/check?domain=example.com&authorized=true")
    print(f"  Safety: Read-only, non-disruptive public checks only")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[SentinelX] Shutting down standalone server.")
        httpd.server_close()


if __name__ == "__main__":
    main()
