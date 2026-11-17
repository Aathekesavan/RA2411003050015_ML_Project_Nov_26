# SentinelX Domain Inspector (Standalone Website)

An independent, standalone exterior posture and domain security verification website, operated separately from the primary SentinelX-Shift analyst dashboard.

SentinelX Domain Inspector provides safe, non-disruptive, read-only public exterior security auditing for modern web applications and domain infrastructure.

---

## 📁 Project Structure

```
domain_inspector/
├── assets/
│   ├── brand/
│   │   ├── wordmark.svg       # SentinelX vector logo & mark
│   │   └── mark.svg           # SentinelX shield guardian emblem
│   ├── css/
│   │   └── site.css           # Responsive stylesheet (SentinelX cyber-slate design system)
│   └── js/
│       └── site.js            # Interactive behaviors, authorization gate, DoH DNS & scanner engine
├── index.html                 # Flagship landing page with hero demo, authorization flow, and scope matrix
├── how-it-works.html          # Step-by-step verification methodology & 11 public attack surfaces
├── pricing.html               # Security Checks & Public Scope explorer (zero commercial billing)
├── sample-report.html         # Demonstration verification report with observed evidence & remediation
├── server.py                  # Standalone Python HTTP server & non-disruptive public inspection API
└── README.md                  # This file
```

---

## 🚀 How to Launch This Standalone Website

### Option 1: Standalone Server with Live Verified Telemetry (Recommended)

Run the included standalone Python server to enable direct TLS handshake inspection, response header auditing, DoH DNS queries, and RFC 9116 verification:

```powershell
# Navigate to the domain_inspector directory
cd domain_inspector

# Launch the standalone inspector server
python server.py
```

- Open **http://localhost:8080** in your browser.
- Live verification API endpoint: `http://localhost:8080/api/check?domain=example.com&authorized=true`

### Option 2: Direct File Opening (Static Mode)

All paths in the project are configured with portable relative URLs. You can double-click [index.html](index.html) or right-click and choose **Open with > Chrome / Edge / Firefox**.

```powershell
# Or using standard Python static server
cd domain_inspector
python -m http.server 3000
# Open http://localhost:3000 in your browser
```

> **Note on Static Mode:** When launched as a purely static site without `server.py`, client-side JavaScript queries live DNS records (SPF, DMARC, CAA) via public DNS-over-HTTPS (DoH). Socket handshakes and HTTP response headers (which browser CORS policies restrict) are transparently labeled as educational baseline demonstration samples with clear instructions to launch `server.py` for full live verified socket telemetry.

---

## 🛡️ Safety, Accuracy, and Integrity Principles

1. **Non-Disruptive Public Checks Only**:
   - Checks are strictly limited to passive, exterior inspection:
     * Port 443 HTTPS availability and HTTP-to-HTTPS (301) redirection.
     * TLS cryptographic certificate validity, issuer, expiration, and cipher suites.
     * Standard HTTP response security headers (`Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`).
     * Public DNS-over-HTTPS email authentication records (`SPF`, `DMARC`, `CAA`, `MX`).
     * Coordinated vulnerability disclosure document (`/.well-known/security.txt`).
   - **Zero Intrusion**: No exploit payloads, no SQL injection, no password brute-forcing, no port scanning, and no denial-of-service tests.

2. **Operator Authorization Required**:
   - The user must explicitly confirm authorization before initiating domain inspection.
   - The UI includes an authorization confirmation checkbox on all check forms and an authorization gate modal.

3. **Verifiable Wire Evidence & Transparent Labeling**:
   - Every finding displays verbatim observed evidence (raw response headers, DNS TXT strings, cryptographic parameters).
   - Sample or simulated results are prominently labeled (`[DEMONSTRATION SAMPLE REPORT]`, `[SAMPLE BASELINE]`).
   - A vulnerability is **never** claimed unless verified by actual observed telemetry.

4. **Zero Commercial Billing or Payment References**:
   - Fully open security inspection tool. No prices, paid plans, credits, checkouts, Stripe/payment references, subscriptions, or billing.
