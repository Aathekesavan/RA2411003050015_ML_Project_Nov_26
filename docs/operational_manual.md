# SentinelX-Shift: Security Operations Center (SOC) Manual & Runbook

**Version**: 2.0.0-production-guard  
**Operational Posture**: MONITOR-ONLY  
**Target Audience**: SOC Analysts (Tier 1/2), Incident Responders, Security Administrators  

---

## 1. Operational Posture & Guiding Principles

### Defensive Principle 1: Strictly Monitor-Only
SentinelX operates exclusively in **MONITOR-ONLY** mode when deployed against network traffic.
- **No Autonomous Disruption**: The Guard will **never** automatically drop packets, reset TCP sessions, or inject firewall null-routes based on model scores alone.
- **Human-in-the-Loop**: Every alert represents a prioritized decision-support item for analyst investigation. Mitigation requires human authorization.
- **Autonomous Blocking Scope**: Automated blocking is restricted to laboratory simulation testbeds.

---

## 2. Architecture & Deployment Overview

The operational deployment comprises four integrated components:
1. **SentinelGuard Engine**: High-throughput CPU inference engine executing feature preprocessing, Autoencoder reconstruction scoring ($s_{\text{AE}}$), supervised XGBoost scoring ($s_{\text{XGB}}$), and the gated boost fusion formula ($s_{\text{guard}}$).
2. **Telemetry Correlator**: Correlates network flow records with Nginx access/error logs and ModSecurity WAF events within a $\pm 30$-second temporal window.
3. **Local Review Store**: Lightweight, local SQLite persistence engine (`results/reviews/analyst_reviews.db`) maintaining immutable alert records, full telemetry snapshots, and analyst audit histories.
4. **Analyst Review Dashboard**: Web-based operational console (`http://localhost:8000/dashboard`) providing queue filtering, telemetry inspection, and one-click triage recording.

---

## 3. Analyst Review Queue Runbook

### 3.1 Prioritized Queue Cards
Every alert in the queue displays unambiguous identification:
- **Flow Identifier**: e.g. `flow-scenario-1-bruteforce` or `flow-4`.
- **Short Alert UUID**: `#<id[:8]>` (e.g. `#86602326`), uniquely identifying the detection instance even when identical flows recur across different runs.
- **Ingestion Timestamp**: Formatted UTC time (`🕒 YYYY-MM-DD HH:MM:SS UTC`).
- **Batch Badge**: Ingestion run identifier (e.g. `batch: phase3-demo-run`).
- **Risk Tier Badge**:
  - `CRITICAL` (Red, score $\ge 0.80$): Action: `ESCALATE_TO_ANALYST`
  - `HIGH` (Orange, score $0.60 - 0.79$): Action: `INVESTIGATE_FLOW`
  - `MEDIUM` (Yellow, score $0.30 - 0.59$): Action: `MONITOR`
  - `LOW` (Green, score $< 0.30$): Action: `ALLOW`

### 3.2 Confirming Signal Evidence Pills
On each card and in the modal inspector, independent signals are displayed:
- **Request Rate (`request_rate`)**:
  - Confirmed ($\ge 50$ req/s): Indicates burst / volumetric surge.
  - Unconfirmed ($< 50$ req/s): Normal request frequency.
- **Authentication Failures (`auth_failures`)**:
  - Confirmed ($\ge 5$ failed attempts): Satisfies BruteForce protocol confirmation.
  - Unconfirmed ($< 5$): Non-malicious credential activity.
- **WAF Event (`waf_event`)**:
  - Confirmed: ModSecurity rule trigger or 403 block observed for client IP.
- **Connection Attempts (`connection_attempts`)**:
  - Confirmed ($\ge 20$): Reconnaissance or aggressive connection cycling.
- **Unavailable Evidence**:
  - Gray badge marked `Unavailable`: Network flow lacked Source IP or Timestamp. Missing telemetry is **never assumed confirmed**.

### 3.3 Triage Decisions & Status Transitions
Analysts can record one of four triage decisions per alert:

| Action | Resulting Review Status | Operational Next Step |
| :--- | :--- | :--- |
| **Confirm Incident** | `CONFIRMED_INCIDENT` | Incident confirmed. Analyst initiates manual containment (IP blocking, credential reset). |
| **Investigate Further**| `IN_INVESTIGATION` | Telemetry ambiguous. Analyst pulls additional pcaps or endpoint telemetry. |
| **Escalate to Tier 2** | `ESCALATED_TIER_2` | High-complexity incident requiring CSIRT or reverse engineering analysis. |
| **Mark Benign / Suppress** | `BENIGN_SUPPRESSED` | Verified benign behavior (e.g. vulnerability scanner, scheduled load test). |

---

## 4. Operational Walkthrough Scenarios

### Scenario 1: Slow-Rate Brute Force Attack
- **Telemetry Profile**: High model score ($s_{\text{prod}} = 1.0$), but low request rate ($0.53$ req/s).
- **Guardrail Action**: Model score alone is **unauthorized** to escalate BruteForce attacks to `CRITICAL` due to low zero-day recall.
- **Correlated Evidence**: Correlator detects 8x HTTP 401s in Nginx access logs and password mismatches in error logs for `198.51.100.42`.
- **Triage Decision**: Protocol confirmation satisfied $\to$ Alert escalated to `CRITICAL`. Analyst clicks **Confirm Incident** and triggers an account lockout.

### Scenario 2: Benign Traffic Burst
- **Telemetry Profile**: Internal client `203.0.113.88` initiates 75 requests in 1 second for web application assets. High Autoencoder reconstruction error ($s_{\text{AE}} = 0.9969$).
- **Guardrail Action**: Benign burst guardrail prevents incident escalation. All responses are HTTP `200 OK`, `auth_failures = 0`, `waf_alert = False`.
- **Triage Decision**: Alert assigned `MEDIUM` / `MONITOR`. Analyst verifies legitimate traffic and clicks **Mark Benign / Suppress**.

---

## 5. CLI Scanner Usage

The CLI enables rapid offline scanning of network flow captures:

```powershell
# Scan flows CSV and output human-readable terminal table
python -m src.api.cli --file data/samples/logs/synthetic_flows.csv --output table

# Scan flows and export JSON alerts to file
python -m src.api.cli --file data/samples/logs/synthetic_flows.csv --output json --output-file results/alerts.json

# Using the Windows batch launcher
.\sentinelx-scan.bat --file data/samples/logs/synthetic_flows.csv --output table
```

---

## 6. REST API Reference

The SentinelX service exposes OpenAPI-compliant endpoints at `http://localhost:8000/docs`:

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/health` | `GET` | Health check, loaded model name, and queue statistics. |
| `/api/v1/score` | `POST` | Core inference endpoint scoring flow batches with optional signals. |
| `/api/v1/correlate_and_score` | `POST` | Ingests flows and raw Nginx/ModSecurity logs, correlates signals, and scores. |
| `/api/v1/alerts` | `GET` | Queries prioritized review queue with risk tier, family, and status filters. |
| `/api/v1/alerts/{alert_id}` | `GET` | Detailed telemetry and confirming signal breakdown for a single alert. |
| `/api/v1/alerts/{alert_id}/review` | `POST` | Records an analyst triage action (`CONFIRM_INCIDENT`, etc.). |
| `/api/v1/queue/load_sample` | `POST` | Idempotently loads default sample benchmark traffic for demonstration. |
| `/api/v1/demo/phase3` | `POST` | Idempotently executes the Phase 3 web log correlation demo. |

---

## 7. System Maintenance & Privacy Safeguards

1. **Privacy Invariant**:
   - Query strings (`?token=...`, `?key=...`) and URL fragments (`#...`) are automatically stripped before storage.
   - HTTP request bodies and raw packet payloads are never stored or inspected.
2. **Database Integrity**:
   - The review store resides at `results/reviews/analyst_reviews.db`.
   - Automatic non-destructive schema migrations ensure existing reviews and historical decisions are never overwritten or deleted.
3. **NTP Synchronization Check**:
   - Verify that web servers and network tap capture engines are synchronized within $\pm 100\text{ ms}$ via NTP to prevent temporal correlation misses.

---

## 8. Phase 5: Safe Shadow-Mode Evaluation & Operational Observability

### 8.1 Operational Principles & Safety Invariants
Phase 5 introduces a safe shadow-mode observation framework that passively benchmarks detector throughput, inference latency, signal availability, and statistical drift without taking network action:
- **Monitor-Only Enforced**: `autonomous_blocking_authorized` is strictly `False` across all alerts and snapshots. No automated firewall or routing rules are touched.
- **No Online Retraining**: Drift flags trigger audit notifications for security engineering. Model weights, activation threshold $\tau^* = 0.56$, and boost magnitude $\gamma^* = 0.41$ are **never** adapted dynamically based on live or drift data.
- **Zero Payload Retention**: Only canonical behavioral netflow statistics and sanitized metadata are ingested. HTTP payloads and sensitive query parameters are excluded.

### 8.2 Observability Metrics Captured
Each shadow snapshot records:
1. **Inference Latency Profile**:
   - Empirical median (p50) and 95th percentile (p95) in milliseconds.
   - Monitored separately for single-flow lookups ($N=1$, baseline $\sim 15.55$ ms) and batched processing ($N \ge 10$, operational target $\le 10.0$ ms/flow).
2. **Operational Throughput & Rates**:
   - Projected alerts per hour rate derived from netflow session duration.
   - Risk tier breakdown (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and suspected attack family frequencies.
3. **Queue Backlog & Triage Outcomes**:
   - Synchronized tracking of pending analyst review backlogs and historical resolutions (`CONFIRMED_INCIDENT`, `BENIGN_SUPPRESSED`, etc.) from `analyst_reviews.db`.
4. **Data Hygiene & Signal Quality**:
   - `invalid_records_count`: Records missing canonical features or containing corrupted non-numeric values (isolated without pipeline disruption).
   - `unavailable_signals_count`: Flows lacking Source IP or Timestamp required for log correlation.
   - `correlation_misses_count`: Valid flows with zero corresponding web or WAF log events in the temporal window.
5. **Statistical Score & Feature Drift**:
   - Baseline score distributions from CIC-IDS2017 benchmark: Production score (mean $0.5076$, std $0.3012$), Autoencoder score (mean $0.5034$, std $0.2947$), Supervised score (mean $0.0103$, std $0.0711$).
   - Canonical feature baselines: `Flow Duration`, `Total Fwd Packets`, `Total Backward Packets`, `Flow Bytes/s`, `Flow Packets/s`, and `Packet Length Mean`.
   - Drift flags are triggered when normalized mean shift exceeds $2.0\sigma$ (features) or absolute shift $> 0.15$ (scores).

### 8.3 Safe Replay Runner
Security teams can evaluate the pipeline against historical or synthetic captures without connecting to live tap interfaces:
```powershell
# Run shadow replay over synthetic sample traffic with WAF correlation
curl -X POST http://localhost:8000/api/v1/shadow/replay -H "Content-Type: application/json" -d '{\"dataset_source\": \"synthetic\", \"batch_size\": 10, \"max_flows\": 50}'

# Fetch latest operational observability snapshot
curl -X GET http://localhost:8000/api/v1/shadow/metrics
```

### 8.4 Retention Window & Safe Reset Policy
- **Local Metrics Database**: Stored in `results/observability/shadow_metrics.db`.
- **Automatic Pruning**: Sliding FIFO retention window preserves the most recent 500 snapshots. Older snapshots are safely pruned on write.
- **Safe Reset (`POST /api/v1/shadow/reset`)**: Purges `shadow_snapshots` and `shadow_runs` tables while leaving `results/reviews/analyst_reviews.db` completely intact.

---

## 9. Operating Modes & Automated Enforcement Controls

SentinelX supports two strictly separated operating modes to bridge the gap between passive telemetry monitoring and active defensive response:

### 9.1 Mode 1: Authorized Real-Site Monitoring
- **Posture**: Passive monitoring of authorized production endpoints (e.g. `prod-portal-alpha`, `corp-api-gateway`).
- **Default State**: Blocking is **DISABLED BY DEFAULT** globally (`global_blocking_enabled=False`) and per site (`blocking_enabled=False`).
- **Enforcement Adapter**: Mode 1 utilizes `MockRealSiteAdapter`, which logs intended defensive blocks, tracks ephemeral block state in local memory, and explicitly labels all responses as `SIMULATED`. **Zero network packets, probes, or firewall commands are dispatched to live production infrastructure.**
- **Enforcement Criteria**: Even when blocking is explicitly enabled by an operator, the policy engine requires all of the following:
  1. `emergency_stop_active == False`
  2. `global_blocking_enabled == True`
  3. Per-site `blocking_enabled == True`
  4. Client IP is not present in the site's `trusted_allowlist`
  5. Alert severity is `CRITICAL` or `HIGH`
  6. **Mandatory Independent Attack Evidence**: Model risk scores alone cannot trigger a block. Corroborating signals (e.g. WAF event or burst rate) are required.
  7. **BruteForce Authentication Guardrail**: For the `BruteForce` family, independent authentication failures ($\ge 5$) are strictly mandatory.
  8. Configured enforcement adapter is online.

### 9.2 Mode 2: Isolated Replica Defense
- **Posture**: Active closed-loop defense executed against a dedicated, isolated replica web service mounted at `http://localhost:8000/replica`.
- **Replica Endpoints**:
  - `/replica/` - Welcome and public catalog
  - `/replica/login` - Authentication endpoint returning HTTP 401 on bad credentials
  - `/replica/portal` - Authenticated customer dashboard
  - `/replica/admin` - Administrative interface
  - `/replica/admin-decoy` - Decoy honeypot trap interface
  - `/replica/status` - Health check and honeypot status
- **Enforcement Adapter**: `LocalReplicaAdapter`, an in-process memory interceptor that intercepts traffic directed to `/replica`. Blocked IPs immediately receive an `HTTP 403 Forbidden` response displaying the block reason, expiry timestamp, and remaining TTL.
- **Decoy Trap Honeypot (`/replica/admin-decoy`)**:
  - Acts as an administrative trap route. Any probe records a structured `honeypot_interaction` telemetry event.
  - **Strict Data Privacy Invariant**: SentinelX **never** stores request bodies, passwords, bearer tokens, cookies, or submitted form fields. Telemetry captures only the route, HTTP method, timestamp, site ID, and authenticated connection address.
  - A confirmed honeypot trap hit provides strong independent attack evidence (`honeypot_interaction: CONFIRMED`), authorizing automated ephemeral defense on the replica.
  - **Mode 1 Invariant**: Monitored real sites have `honeypot_enabled=False` by default; Mode 1 policy evaluation explicitly marks honeypot telemetry as `UNAVAILABLE` and will never claim a honeypot is deployed or use unconfigured traps to authorize blocks.
- **Lab Isolation Invariant**: Mode 2 operates under its own distinct site configuration (`replica-site`). Allowlist entries, blocks, and parameters configured for the replica lab **never** cross over or affect Mode 1 real-site configurations.
- **Interactive Scenarios**:
  - **Slow-Rate Brute Force Defense**: Simulates an attacker (`198.51.100.77`, labeled `SIMULATED_SCENARIO`) attempting password stuffing across 7 failed logins. Once confirmed by telemetry, an ephemeral 60s block is applied on the replica adapter, and subsequent requests to `/replica` are rejected with HTTP 403.
  - **Benign Burst Allowlisting**: Simulates an administrator (`10.0.0.99`, labeled `SIMULATED_SCENARIO`) triggering a rapid traffic surge. Because the IP is configured on the lab allowlist, the block is safely bypassed and requests receive HTTP 200 OK.
  - **Decoy Trap Honeypot Defense**: Simulates an unauthorized scout (`198.51.100.88`, labeled `SIMULATED_SCENARIO`) probing `/replica/admin-decoy`. Captures structured honeypot telemetry and immediately applies a 60s block with HTTP 403 verification.

### 9.3 Master Emergency Stop Runbook
SentinelX includes an unconditional **Emergency Stop** switch designed to abort all automated blocking immediately across all sites and adapters:
- **Web Dashboard**: Click the pulsing red **"🛑 EMERGENCY STOP"** button on the top-right control bar.
- **REST API Command**:
  ```powershell
  curl -X POST http://localhost:8000/api/v1/enforcement/config \
       -H "Content-Type: application/json" \
       -d '{\"emergency_stop_active\": true}'
  ```
- **Operational Effect**: When active, all subsequent traffic evaluations unconditionally resolve to `ALLOW` (or `MONITOR`), citing `Emergency stop is active`. Existing active blocks remain paused or can be flushed via `POST /api/v1/enforcement/blocks/release`.

### 9.4 Geo-Privacy Invariant
In accordance with user privacy guidelines, the Mode 2 Defense Inspector and Audit Trail enforce a strict **Geo-Privacy Invariant**:
- Network telemetry displayed in the dashboard shows source and destination IP addresses, ports, and protocols.
- **No Geo-IP Inference**: SentinelX does **not** perform heuristic geographic lookups (e.g. country, city, coordinates) from raw IP addresses without an authorized, verified organizational provider. All IP entries in the UI are flagged with `Protected (No Geo-IP inferred)`.

### 9.5 Localhost Binding, Hardened Client Identity & Anti-Spoofing Safeguards
- **Service Binding Posture**: By default, SentinelX binds strictly to loopback (`127.0.0.1:8000`).
- **Hardened Client Identity**:
  - SentinelX derives client identity strictly from the underlying network socket (`request.client.host`).
  - User-controlled identity overrides such as `?client_ip=` or payload fields are **strictly rejected and ignored** for all authorization, block, and allowlist decisions.
  - Reverse proxy headers (`X-Forwarded-For`) are trusted **only** when the direct connection originates from an explicitly configured proxy in `_trusted_proxies` (`set_trusted_proxies(...)`). Forwarded headers from untrusted clients are completely disregarded.
  - **Anti-Spoofing Proof**: If an attacker IP is blocked, sending `?client_ip=10.0.0.99` or `X-Forwarded-For: 10.0.0.99` (the allowlisted lab administrator) will still result in `HTTP 403 Forbidden` (`REPLICA_BLOCKED`).
- **Real vs. Simulated Scenario Identities**:
  - `REAL_CONNECTION`: Live HTTP connections arriving at the FastAPI server from actual clients/proxies.
  - `SIMULATED_SCENARIO`: Synthetically injected identities (e.g., `198.51.100.77`, `10.0.0.99`, `198.51.100.88`) constructed exclusively inside the server-side scenario runner (`src/replica/scenarios.py`) for safe multi-client testbed demonstrations.
- **Enforcement Endpoint Mutation Safeguards**:
  - Mutating enforcement endpoints enforce the `require_local_or_admin` security dependency.
  - Any request originating from a non-loopback IP (`request.client.host not in ("127.0.0.1", "::1", "localhost")`) is immediately rejected with `HTTP 403 Forbidden` and error code `FORBIDDEN_REMOTE_ENFORCEMENT_MUTATION`.
  - For authorized remote administration across management subnets, administrators must define the environment variable `SENTINELX_ADMIN_KEY` on the host and provide the corresponding `X-SentinelX-Admin-Key` header with each request.

### 9.6 Mode 2 Defense Demonstration Runbook & Narration Guide

#### A. Exact Startup & Preparation Steps
1. **Launch the SentinelX Service**:
   ```powershell
   python -m uvicorn src.api.service:app --host 127.0.0.1 --port 8000
   ```
2. **Access the Web Consoles**:
   - Analyst Review Queue & Defense Inspector: [http://127.0.0.1:8000/dashboard/](http://127.0.0.1:8000/dashboard/)
   - Isolated Replica Customer Portal: [http://127.0.0.1:8000/replica/](http://127.0.0.1:8000/replica/)
3. **Execute the Automated Verification Walkthrough** (Optional CLI demo):
   ```powershell
   python scripts/demo_walkthrough.py
   ```

#### B. Presentation Script & Narration Talking Points
- **Part 1 — Introducing Mode 1 (Authorized Real-Site Monitoring)**:
  > *"Here in Mode 1, SentinelX passively monitors traffic from authorized production sites like `prod-portal-alpha`. Notice that all automated blocking is strictly DISABLED BY DEFAULT. Even if we toggle blocking on for demonstration, our backend adapter is `MockRealSiteAdapter`, explicitly labeled `SIMULATED / NOT CONNECTED`. Zero firewall commands or network packets are dispatched to real infrastructure. Crucially, model scores alone can NEVER trigger an automated block—independent attack evidence is mandatory."*
- **Part 2 — Demonstrating Mode 2 (Isolated Replica Defense)**:
  > *"To demonstrate closed-loop automated defense safely, we switch to Mode 2. This operates against our dedicated local replica website, Acme Financial Portal, mounted at `/replica`. Notice that Mode 2's configurations and allowlists are completely isolated from Mode 1."*
  > *(Click 'Run BruteForce Scenario')*
  > *"Attacker `198.51.100.77` attempted 7 consecutive credential stuffing logins on `/replica/login`. Our telemetry correlator confirmed the repeated authentication failures. Because independent evidence exists, the policy engine issued an ephemeral 60-second block. If we now probe `/replica/login` with that IP, it is immediately rejected with `HTTP 403 Forbidden` showing the remaining TTL. Meanwhile, legitimate users on the lab allowlist continue without disruption."*
- **Part 3 — Demonstrating Block Lifecycle & Emergency Stop**:
  > *"Defenses are temporary by design to avoid permanent lockouts. In the active blocks table, we can watch the TTL countdown or click 'Release Block' to immediately restore normal access (returning HTTP 401 instead of 403). Furthermore, should any anomaly arise, the master 'EMERGENCY STOP' button instantly overrides and disables all blocking across all adapters in a single click."*
- **Part 4 — Demonstrating Decoy Trap Honeypot & Hardened Identity**:
  > *(Click 'Run Honeypot Decoy Scenario')*
  > *"Here, scout `198.51.100.88` probes our administrative decoy trap route `/replica/admin-decoy`. SentinelX captures a structured `honeypot_interaction` event while strictly obeying privacy—no bodies, passwords, or tokens are ever recorded. Because a honeypot hit provides strong, independent corroboration, the engine immediately blocks the scout. When the scout probes the decoy route again, it is blocked with `HTTP 403 Forbidden`. Furthermore, our client identity logic is hardened: an attacker cannot bypass defenses by spoofing `?client_ip=` or `X-Forwarded-For` to mimic an administrator."*
- **Part 5 — Split-Screen Guided View & Counterfactual Comparison**:
  > *(Navigate to `http://127.0.0.1:8000/presentation`)*
  > *"Here on our split-screen console, we have the local replica web application on the left and the SentinelX AI Guard inspection stream on the right, perfectly synchronized to the active scenario. When we click 'Start Scenario', watch the live progression: Stage 1 ingests the telemetry; Stage 2 applies the gated boost scoring model; Stage 3 correlates independent confirming evidence; and Stage 4 triggers the policy engine. On the replica browser, the attacker immediately receives an `HTTP 403 Forbidden` overlay with a live TTL countdown."*
  > *"Notice the side-by-side comparison below: Under 'Protected by SentinelX', the attack is actively intercepted with HTTP 403. Beside it, under 'Without SentinelX', we present a non-mutating counterfactual simulation using synthetic fake data: without intervention, the attacker guesses the password on the 8th attempt and obtains a fake session token to administrative endpoints. This hypothetical baseline illustrates the defensive value without disabling real enforcement or transmitting any traffic to real sites. Finally, clicking 'Reset Scenario' releases test blocks while preserving all historical analyst review decisions in our review database."*

### 9.7 Split-Screen Presentation Console & Counterfactual Comparison

#### A. Architecture & Page Overview
The Split-Screen Presentation Console (`http://localhost:8000/presentation` or `/dashboard/presentation.html`) provides a synchronized, dual-panel display designed for executive and Mode 2 demonstrations:
1. **Left Panel — Local Replica Website (`/replica`)**:
   - Displays attack location metadata: Site Name, Route (`/replica/login`), Simulated Source IP (`198.51.100.77`), Timestamp, labeled `SIMULATED ATTACK`.
   - Simulated browser viewport rendering the replica portal form, with an animated HTTP 403 `BLOCKED IN LOCAL REPLICA` overlay and active TTL countdown when enforcement triggers.
2. **Right Panel — SentinelX AI Guard & Policy Inspector**:
   - Stepped four-stage inspection stream:
     - **Stage 1**: Flow Ingestion & Telemetry (Packets/s, Bytes/s, Flow Duration, Source IP).
     - **Stage 2**: Model Scoring (Gated Boost Score $s_{\text{guard}}$, Suspected Family, $\tau^*$ Activation Threshold).
     - **Stage 3**: Independent Confirming Evidence (`auth_failures`, `honeypot_interaction`, `waf_event`).
     - **Stage 4**: Policy Enforcement Decision (Policy Rule, Action `BLOCK`/`MONITOR_ONLY`, Reason).
3. **Bottom Section — Protected vs. Without SentinelX Comparison**:
   - **Protected by SentinelX**: Shows the real in-process enforcement by `LocalReplicaAdapter`, enforced HTTP 403 status, and business impact.
   - **Without SentinelX (Hypothetical Baseline)**: Non-mutating simulation using synthetic fake data (e.g. simulated compromised account `ACC-99201-REPLICA`, fake JWT token, hypothetical unauthorized access to `/replica/admin`).
   - Clear labels throughout: `SIMULATED ATTACK`, `HYPOTHETICAL OUTCOME`, `BLOCKED IN LOCAL REPLICA`, and Mode 1 marked `SIMULATED / NOT CONNECTED`.

#### B. Controls & Non-Destructive Scenario Reset
- **Active Demo Scenario Dropdown**:
  - `1. Slow-Rate Brute Force (/replica/login)`
  - `2. Decoy Trap Honeypot (/replica/admin-decoy)`
  - `3. Benign Administrative Burst (/replica/portal)`
- **Start Scenario (`▶ Start Scenario`)**: Launches the synchronized 4-stage evaluation animation and calls `POST /api/v1/replica/scenarios/run`.
- **Pause / Resume (`⏸ Pause`)**: Freezes/resumes the animation stream and TTL countdown.
- **Reset Scenario (`🔄 Reset Scenario`)**: Calls `POST /api/v1/replica/scenarios/reset`.
  - **Review Store Preservation Invariant**: Clears **only** the scenario simulated attacker blocks (`198.51.100.77`, `198.51.100.88`, `10.0.0.99`) from the in-memory adapter.
  - Leaves the local SQLite review database (`results/reviews/analyst_reviews.db`), historical alerts, and recorded review actions completely intact.

#### C. Troubleshooting Common Issues
| Symptom | Probable Cause | Resolution |
| :--- | :--- | :--- |
| `Address already in use: 8000` | Prior uvicorn process or background task running. | Run `Get-Process python \| Stop-Process` or bind to an alternative port `--port 8080`. |
| `HTTP 403: FORBIDDEN_REMOTE_ENFORCEMENT_MUTATION` | Accessing mutation API from LAN IP instead of localhost. | Connect via `http://127.0.0.1:8000` or configure `SENTINELX_ADMIN_KEY`. |
| Scenario shows `DISALLOWED_EMERGENCY_STOP` | Emergency Stop switch remained engaged from prior test. | Click `🛑 EMERGENCY STOP` in UI to disengage, or call `POST /api/v1/enforcement/config {"emergency_stop_active": false}`. |
| Replica returns `403 Forbidden` for all queries | IP was blocked during test scenario. | Click `Release Block` in the Active Blocks table or click `🔄 Reset Scenario` on the presentation page. |
