<div align="center">

<img src="docs/srm_trc_logo.jpg" alt="SRM Institute of Science and Technology, Tiruchirappalli" width="480" />

# SentinelX-Shift: Operational Network Intrusion Detection & Prioritized Alert Review System

> **Combining Behavioral Netflow Models, Autoencoder-Anchored Scoring, and Independent Web/WAF Telemetry Confirmation**

</div>

---

## 🎓 Academic Submission & Course Details

| Field | Details |
| :--- | :--- |
| **Institution** | SRM Institute of Science and Technology, Tiruchirappalli Campus |
| **Department** | Department of Computer Science and Engineering (CSE) |
| **Course ID** | **21CSC305P** |
| **Course Name** | **MACHINE LEARNING** |
| **Academic Year** | **2026** |
| **Repository Name** | `RA2411003050015_ML_Project_Nov_26` |

### 👥 Team Members

| # | Full Name | Register Number | Department | Section | Academic Year | Role |
| :-: | :--- | :--- | :--- | :-: | :-: | :--- |
| 1 | **AATHEKESAVAN R** | `RA2411003050015` | Computer Science and Engineering | **A** | **2026** | Team Leader |
| 2 | **PRAVEEN K** | `RA2411003050056` | Computer Science and Engineering | **A** | **2026** | Team Member |

### 👨‍🏫 Mentor Details

| Field | Details |
| :--- | :--- |
| **Mentor Full Name** | **Dr. S. Kanaga Suba Raja** |
| **Designation** | Professor and Head, Department of Computer Science and Engineering |
| **Department** | Computer Science and Engineering |
| **Institution** | SRM Institute of Science and Technology, Tiruchirappalli |

---

## 📑 Project Report & Documentation

- 📄 **[Final Project Report (PDF)](SentinelX_Project_Report_Final.pdf)** *(Complete 40+ page formal academic project report)*
- 📑 **[Project Review Report & Evaluation Format (PDF)](SentinelX_Project_Review_Report_Format.pdf)**
- 📘 **[SOC Operational Manual & Runbook](docs/operational_manual.md)**: Analyst triage guide, risk tier interpretation, review action workflows, and API reference.
- 📄 **[Consolidated Technical Report](docs/technical_report.md)**: Full architecture, leakage controls, LOFO multi-seed benchmarks, and cross-dataset evaluation.
- 📊 **[Data Card](docs/data_card.md)**: Ingestion provenance from all 8 CIC-IDS2017 raw partitions, 21.03% deduplication audit, and 60,000 sampled benchmark specification.
- ⚙️ **[Production Scoring Specification](docs/production_score.md)**: Autoencoder-Anchored Gated Boost formula and parameter grid validation.

---

## 🛡️ 1. Operational Posture & Defensive Principles

1. **Strictly Monitor-Only (Defensive Principle 1)**: Automated inline packet dropping and TCP connection resets on model scores alone are **strictly disabled**. Real endpoints and reverse proxies operate exclusively in monitor-and-alert mode. All triage and mitigation actions require affirmative SOC analyst confirmation.
2. **Leakage-Free Evaluation**: Leave-One-Family-Out (LOFO) protocol evaluated across 5 canonical attack families (`DoS_DDoS`, `PortScan`, `BruteForce`, `Bot`, `WebAttack`). All leaky network identifiers (IPs, ports, MACs, raw timestamps) are stripped from training features.
3. **Independent Signal Confirmation**: Model scores alone cannot authorize priority escalation for stealthy attacks. Guardrails require corroborating evidence (repeated authentication failures, burst request rates, or WAF triggers).
4. **Privacy-Preserving Architecture**: Full query strings (`?token=...`, `?key=...`) and URL fragments (`#...`) are automatically stripped before log storage. HTTP request bodies, POST data, and network payloads are **never** stored or inspected.
5. **Traceability & Non-Destructive Storage**: Stored in a local SQLite review store (`results/reviews/analyst_reviews.db`). Alerts maintain distinct short UUID badges (`#<id[:8]>`) and formatted timestamps. Historical decisions are never deleted or reset.

---

## 💻 2. Environment & Setup

### Requirements
- **OS**: Windows, Linux, or macOS
- **Python**: 3.12+
- **Dependencies**: `pip install -r requirements.txt`

### Quick Setup
```powershell
# Clone the repository
git clone https://github.com/Aathekesavan/RA2411003050015_ML_Project_Nov_26.git
cd RA2411003050015_ML_Project_Nov_26

# Install required dependencies
python -m pip install -r requirements.txt
```

---

## 🚀 3. Launching SentinelX Services

### A. Interactive Analyst Dashboard & REST API
Start the FastAPI server:
```powershell
python -m uvicorn src.api.service:app --host 127.0.0.1 --port 8000
```
Open **`http://localhost:8000/dashboard`** in your browser.
- **Prioritized Queue**: Inspect incoming alerts filtered by Risk Tier (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), Family, and Review Status.
- **Card Identity**: Distinct flow ID, short UUID pill (`#86602326`), UTC timestamp, and batch pill (`#phase3-demo-run`).
- **Telemetry Modal**: Click any card to inspect the Autoencoder/XGBoost score breakdown, confirming signal evidence pills, raw netflow telemetry, and record triage decisions.
- **Interactive Action Bar**:
  - `🚀 Ingest Phase 3 Demo`: Correlates synthetic Nginx/ModSecurity logs with flows.
  - `⚡ Ingest Sample Traffic`: Idempotently loads default benchmark sample flows.
  - `🔄 Refresh Queue`: Refreshes live KPIs and alert status.

### B. Command-Line Interface (CLI Scanner)
Scan network flow captures offline and generate structured alerts:
```powershell
# Human-readable table output
python -m src.api.cli --file data/samples/logs/synthetic_flows.csv --output table

# Schema-validated JSON alerts
python -m src.api.cli --file data/samples/logs/synthetic_flows.csv --output json --output-file results/alerts.json

# Using the Windows batch runner
.\sentinelx-scan.bat --file data/samples/logs/synthetic_flows.csv --output table
```

### C. SentinelX Domain Inspector (Exterior Security Portal)
A standalone, non-disruptive exterior posture and domain security verification portal:
```powershell
cd domain_inspector
python server.py
```
Open **`http://localhost:8080`** in your browser to inspect TLS certificates, HTTP response security headers, and DoH DNS records.

---

## 🔬 4. Walkthrough Demos (Phase 3 Web Log & WAF Correlation)

Run the local, repeatable Phase 3 correlation demo:
```powershell
python scripts/demo_phase3.py
# or using Makefile:
make demo
```

### Walkthrough Scenarios
1. **Scenario 1: Slow-Rate Brute Force Attack**:
   - Attack flow ($s_{\text{prod}} = 1.0$) with low rate ($0.53$ req/s, below volumetric threshold).
   - Correlated Nginx access/error logs show 8 consecutive HTTP 401s and ModSecurity rule 200002.
   - **Triage Result**: Protocol confirmation satisfied $\to$ Escalated to `CRITICAL` / `ESCALATE_TO_ANALYST`.
2. **Scenario 2: Benign Traffic Burst**:
   - Internal client initiates 75 requests in 1 second. Model anomaly score elevates ($s_{\text{AE}} = 0.9969$).
   - Correlated logs show all responses are HTTP `200 OK`, `auth_failures = 0`, `waf_alert = False`.
   - **Triage Result**: Benign burst guardrail prevents false alarm $\to$ De-escalated to `MEDIUM` / `MONITOR`.
3. **Edge Case: Missing Telemetry Flow**:
   - Flows missing `Source IP` or `Timestamp` have confirming signals explicitly reported as `Unavailable` (`present=False, confirmed=None`).

---

## 🧪 5. Automated Verification & Testing

Execute the unified verification suite:
```powershell
python scripts/verify_release.py
# or using Makefile:
make verify
```

To run the automated test suite directly:
```powershell
python -m pytest tests/
```

---

## 📝 6. License & Academic Integrity

This project is developed as part of the academic curriculum for the **B.Tech Computer Science and Engineering** program at **SRM Institute of Science and Technology, Tiruchirappalli Campus**.
All rights reserved © 2026.
