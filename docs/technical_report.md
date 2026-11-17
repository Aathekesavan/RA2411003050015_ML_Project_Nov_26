# SentinelX-Shift: Comprehensive Technical Report & Evaluation Analysis

**Project**: SentinelX-Shift  
**Release Version**: 2.0.0-production-guard  
**Status**: APPROVED FOR MONITOR-ONLY TRIAGE  
**Author**: SentinelX Security ML Research & Core Engineering Team  
**Evaluation Benchmark**: CIC-IDS2017 (Complete 8 Partitions) & UNSW-NB15  

---

## 1. Executive Summary & Purpose

Modern intrusion detection systems (IDS) operating on machine learning frequently report near-perfect benchmark performance (>99% accuracy on naive random splits) yet catastrophically fail when deployed against unfamiliar attack variants or real-world traffic. This failure stems from three systemic issues:
1. **Shortcut Learning & Identifiers Leakage**: Models memorize IP addresses, port numbers, MAC addresses, and packet timestamps rather than generalizable behavioral patterns.
2. **High-Prevalence Duplication**: Raw network traffic benchmarks contain upwards of 20% duplicate flow vectors that artificially inflate test accuracy across random splits.
3. **Cross-Family Semantic Overlap**: Related attack families (such as SSH brute force and Web application brute force) share feature representations across cross-validation splits, masking generalization failures.

**SentinelX-Shift** was architected to solve these challenges. It provides a robust, analyst-assisted network intrusion detection and alert-prioritization system combining:
- Leakage-controlled, deduplicated data protocols.
- Leave-One-Family-Out (LOFO) evaluation across 5 canonical attack families.
- An **Autoencoder-Anchored Gated Boost** production scoring engine ($s_{\text{guard}}$).
- A Guardrail mechanism with **independent confirming signals** (request rates, repeated authentication failures, and ModSecurity/WAF triggers).
- An interactive analyst dashboard and review queue that respects human-in-the-loop decision-making.

### Target Users
- **Tier-1 / Tier-2 Security Operations Center (SOC) Analysts**: Review prioritized alerts, investigate correlated web-tier telemetry, and triage incidents.
- **Web Application & Network Security Administrators**: Monitor external reverse proxies and services under strict **MONITOR-ONLY** defensive posture without risking autonomous network disruptions.
- **Security Research & Audit Teams**: Inspect reproducible LOFO evaluation benchmarks and leakage audits.

---

## 2. System Architecture & Defensive Invariants

```
               [ Network Flow Telemetry ]           [ Nginx / WAF Logs ]
                           |                                 |
                           v                                 v
                 [ Feature Extraction ]            [ Parsing & Redaction ]
                 (76 Canonical Features)           (Strip Query Params)
                           |                                 |
                           +---------------+                 |
                                           |                 |
                                           v                 v
                                  [ SentinelGuard Engine ]<--+ (Temporal Window
                                           |                   Matching: +/-30s)
               +---------------------------+---------------------------+
               |                                                       |
               v                                                       v
       [ Scoring Pipeline ]                                   [ Confirming Signals ]
    s_AE  (CDF-Calibrated)                                  - Request Rate (Burst)
    s_XGB (Supervised Risk)                                 - Auth Failures (401s)
               |                                            - WAF Alerts (ModSec)
               v                                                       |
      s_guard = s_AE + gamma* * I(s_XGB > tau*)                       |
               |                                                       |
               +---------------------------+---------------------------+
                                           |
                                           v
                              [ Guardrail Policy Engine ]
                               - BruteForce Confirmation
                               - Benign Burst De-escalation
                                           |
                                           v
                             [ Prioritized FlowAlert ]
                             (Risk Tier, Action, Evidence)
                                           |
                                           v
                             [ Analyst Review Queue ]
                             (Local SQLite Review Store)
                                           |
                                           v
                             [ Interactive Dashboard ]
                                (Human Triage Action)
```

### Defensive Invariant 1: MONITOR-ONLY Operational Mode
Under Defensive Principle 1, SentinelX operates in **MONITOR-ONLY** mode when observing live external web traffic. 
- Autonomous inline packet dropping and TCP connection resets on model scores alone are **STRICTLY PROHIBITED**.
- Every alert produced by the Guard is marked with `autonomous_blocking_authorized: false`.
- All mitigation actions (quarantine, firewall blocking, session revocation) require affirmative analyst review and confirmation. Autonomous blocking occurs exclusively inside isolated laboratory simulation testbeds.

---

## 3. Data Provenance & Leakage Controls

### 3.1 Raw Ingestion & Deduplication Audit
SentinelX evaluates on all 8 raw partition files of the official **CIC-IDS2017** benchmark:

| Raw Partition File | Loaded Row Count |
| :--- | :--- |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv.parquet` | 225,745 |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv.parquet` | 286,467 |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv.parquet` | 191,033 |
| `Monday-WorkingHours.pcap_ISCX.csv.parquet` | 529,918 |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv.parquet` | 288,602 |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv.parquet` | 170,366 |
| `Tuesday-WorkingHours.pcap_ISCX.csv.parquet` | 445,909 |
| `Wednesday-workingHours.pcap_ISCX.csv.parquet` | 692,703 |
| **Total Ingested Raw Flows** | **2,827,840** |
| **Full-Vector Duplicates Removed** | **594,712 (21.03%)** |
| **Unique Behavioral Flows** | **2,233,128** |
| **Sampled Benchmark Dataset** (`data/processed/cicids2017_sample60k.parquet`) | **60,000** |

### 3.2 Canonical Family Group Mapping
To prevent low-power degenerate evaluation, attacks are consolidated into 5 canonical family groups:
1. **`DoS_DDoS`**: Consolidates DoS Hulk, GoldenEye, slowloris, Slowhttptest, Heartbleed, and LOIC DDoS (321,770 unique flows; subsampled).
2. **`BruteForce`**: Combines FTP-Patator and SSH-Patator (9,150 unique flows; 100% retained).
3. **`PortScan`**: Comprehensive port scanning reconnaissance (1,956 unique flows; 100% retained).
4. **`Bot`**: Ares botnet command and control traffic (1,437 unique flows; 100% retained).
5. **`WebAttack`**: Combines Web Brute Force, XSS, and SQL Injection (2,143 unique flows; 100% retained).
*(Infiltration with only 36 flows in 2.8M rows was excluded from LOFO per protocol as statistically underpowered).*

### 3.3 Strict Anti-Leakage Feature Sanitization
The 76 features in `cicids2017_sample60k.parquet` consist purely of transport and flow statistics (`Flow Duration`, `Total Fwd Packets`, `Flow IAT Mean`, `Packet Length Std`, etc.). All leaky fields (`Source IP`, `Destination IP`, `Source Port`, `Destination Port`, `Timestamp`, and MAC addresses) were systematically stripped from the feature matrix prior to training.

### 3.4 Joint Related-Family Holdout Finding ({BruteForce, WebAttack})
To audit cross-family semantic leakage, a joint holdout experiment holding out both `BruteForce` and `WebAttack` simultaneously was executed:
- **Separate LOFO WebAttack PR-AUC**: `0.7481 +/- 0.0181`
- **Merged Joint Holdout PR-AUC**: `0.2962 +/- 0.0308`
- **Finding**: When SSH/FTP brute-force is present in the training set, supervised models learn generic credential-stuffing flow patterns that artificially boost performance on WebAttack. Holding them out together reveals the true zero-day generalization deficit.

---

## 4. Detection Models & Production Scoring Policy

### 4.1 Invalidation of Learned Linear Weight Fusion
Linear score combination ($s = w_1 s_{\text{XGB}} + w_2 s_{\text{AE}}$) was evaluated and **rejected for production**:
- During inner-LOFO validation, unconstrained optimization collapsed to $w_1 = 1.0, w_2 = 0.0$ in 4 out of 5 seeds for both `BruteForce` and `DoS`.
- A weight of $w_1 = 1.0$ completely zeros out the Autoencoder, blinding the detector to novel zero-day attacks that share no lexical or feature overlap with training data.

### 4.2 Designated Production Score: Autoencoder-Anchored Gated Boost
SentinelX deploys **Autoencoder-Anchored Gated Boost** ($s_{\text{guard}}$):
$$s_{\text{guard}}(\mathbf{x}) = s_{\text{AE}}(\mathbf{x}) + \gamma^* \cdot \mathbb{I}\left(s_{\text{XGB}}(\mathbf{x}) > \tau^*\right)$$
where:
- $s_{\text{AE}}(\mathbf{x}) \in [0, 1]$ is the empirical CDF-calibrated Autoencoder reconstruction error.
- $s_{\text{XGB}}(\mathbf{x}) \in [0, 1]$ is the empirical CDF-calibrated supervised XGBoost risk score.
- $\tau^* = 0.56$ is the supervised high-confidence activation threshold.
- $\gamma^* = 0.41$ is the additive boost magnitude.

### 4.3 Hyperparameter Tuning Results
Hyperparameters were tuned via inner-LOFO grid search across $\tau \in \{0.3, 0.5, 0.7, 0.9\}$ and $\gamma \in \{0.1, 0.2, 0.3, 0.5\}$ over 5 seeds:

| Evaluation Fold | Validation Prevalence | Mean $\tau^*$ | Mean $\gamma^*$ | Mean Val PR-AUC (AE) | Mean Val PR-AUC (Gated Boost) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Bot** | 31.78% | 0.66 | 0.32 | 0.5696 | **0.7850** |
| **BruteForce** | 22.72% | 0.50 | 0.36 | 0.4544 | **0.7305** |
| **DoS_DDoS** | 24.77% | 0.30 | 0.42 | 0.4019 | **0.6257** |
| **PortScan** | 30.78% | 0.54 | 0.44 | 0.5365 | **0.6699** |
| **WebAttack** | 30.44% | 0.78 | 0.50 | 0.5969 | **0.7834** |
| **Overall Mean** | — | **0.56** | **0.41** | **0.5118** | **0.7189** |

---

## 5. Multi-Seed LOFO Benchmark Results

The multi-seed LOFO benchmark measures performance when each family is completely withheld from training and evaluated at realistic operational prevalences (1% and 5% attack flow prevalence).

### Benchmark Performance Table (5 Seeds: 42, 101, 202, 303, 404)
*(Source: `results/lofo_benchmark_multi_seed.csv` and `results/raw_scores/raw_scores.parquet`)*

| Held-Out Family | Prevalence | Method | ROC-AUC | PR-AUC | Recall @ 1% FAR |
| :--- | :---: | :--- | :---: | :---: | :---: |
| **DoS_DDoS** | 5.0% | Supervised XGBoost | 0.9632 +/- 0.0051 | 0.7854 +/- 0.0123 | 70.87% +/- 1.34% |
| | 5.0% | Autoencoder | 0.7951 +/- 0.0120 | 0.2845 +/- 0.0105 | 18.23% +/- 1.12% |
| | 5.0% | **Gated Boost (Guard)** | **0.9645 +/- 0.0048** | **0.7891 +/- 0.0118** | **70.87% +/- 1.34%** |
| **PortScan** | 5.0% | Supervised XGBoost | 0.9845 +/- 0.0032 | 0.8412 +/- 0.0089 | 87.89% +/- 1.05% |
| | 5.0% | Autoencoder | 0.8123 +/- 0.0142 | 0.3120 +/- 0.0115 | 22.45% +/- 1.30% |
| | 5.0% | **Gated Boost (Guard)** | **0.9851 +/- 0.0030** | **0.8435 +/- 0.0085** | **87.89% +/- 1.05%** |
| **BruteForce** | 5.0% | Supervised XGBoost | 0.9202 +/- 0.0402 | 0.3149 +/- 0.0443 | 4.18% +/- 3.16% |
| | 5.0% | Autoencoder | 0.8034 +/- 0.0204 | 0.1144 +/- 0.0137 | 0.00% +/- 0.00% |
| | 5.0% | **Gated Boost (Guard)** | **0.8042 +/- 0.0212** | **0.1199 +/- 0.0226** | **1.55% +/- 2.45%** |
| **Bot** | 5.0% | Supervised XGBoost | 0.7845 +/- 0.0350 | 0.1420 +/- 0.0210 | 0.00% +/- 0.00% |
| | 5.0% | Autoencoder | 0.7612 +/- 0.0280 | 0.0980 +/- 0.0180 | 0.00% +/- 0.00% |
| | 5.0% | **Gated Boost (Guard)** | **0.7650 +/- 0.0275** | **0.1015 +/- 0.0175** | **0.00% +/- 0.00%** |
| **WebAttack** | 5.0% | Supervised XGBoost | 0.9824 +/- 0.0032 | 0.7481 +/- 0.0181 | 57.22% +/- 40.18% |
| | 5.0% | Autoencoder | 0.7414 +/- 0.0666 | 0.0995 +/- 0.0391 | 0.00% +/- 0.00% |
| | 5.0% | **Gated Boost (Guard)** | **0.7535 +/- 0.0667** | **0.1053 +/- 0.0395** | **0.77% +/- 1.30%** |

### Critical Zero-Day Generalization Finding
While high volumetric attacks (`DoS_DDoS`, `PortScan`) generalize strongly due to unmistakable packet rate footprints, stealthy or application-layer attacks (`BruteForce`, `Bot`, `WebAttack`) experience catastrophic recall drops at 1% False Alarm Rate (0.00% to 4.18%).
- **Policy Consequence**: Relying on model scores alone to block stealthy attacks produces massive false-negative rates or unmanageable false alarms.
- This finding formally mandates SentinelX's **Guardrail Confirmation Policy** (requiring independent web-tier signals).

---

## 6. Cross-Dataset Evaluation (UNSW-NB15)

To evaluate real-world cross-domain generalization, models trained on CIC-IDS2017 were evaluated directly on the **UNSW-NB15** network intrusion dataset (and vice versa):

| Train Dataset | Test Dataset | Model Architecture | In-Domain ROC-AUC | Cross-Dataset ROC-AUC | Performance Delta |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **CIC-IDS2017** | **UNSW-NB15** | Supervised XGBoost | 0.9933 | 0.5842 | **-40.91%** |
| **CIC-IDS2017** | **UNSW-NB15** | Autoencoder Baseline | 0.8120 | 0.6125 | **-19.95%** |
| **CIC-IDS2017** | **UNSW-NB15** | Gated Boost | 0.8540 | 0.6210 | **-23.30%** |
| **UNSW-NB15** | **CIC-IDS2017** | Supervised XGBoost | 0.9812 | 0.5218 | **-45.94%** |

### Takeaway
Supervised models degrade to near-random guessing (ROC-AUC ~0.52 - 0.58) when transferred across network environments without domain adaptation. The unsupervised Autoencoder exhibits greater cross-domain stability (-19.95% vs -40.91%), validating the architectural decision to anchor the Guard score on reconstruction error.

---

## 7. Audited Explanation-Stability Result: Negative Finding

A core hypothesis of Phase 0 was that SHAP attribution stability ($S_{\text{exp\_stab}}$) under physical perturbations could serve as a confidence multiplier in production scoring.

### Physical Perturbation Audit
Using the `PhysicalPerturbationEngine`, valid physical perturbations (packet arrival jitter $\epsilon \in \{0.01, 0.05, 0.10\}$ preserving physical invariants $IAT_{\max} \le \text{Duration}$) were applied to test flows:
- **Lipschitz Continuity Failure**: Perturbation variance across feature attributions exceeded acceptable stability bounds across all 5 evaluation seeds.
- **Physical Rejection Rate**: Up to 18.4% of synthetic perturbations had to be rejected for violating physical networking invariants (negative packet length, impossible inter-arrival intervals).
- **Latency Overhead**: Generating TreeSHAP explanation vectors added **>150 ms** of latency per flow, completely violating real-time operational thresholds (<= 10 ms).

### Final Architectural Decision
Explanation stability is **formally rejected and excluded from the production score**. Explanation stability is unstable, computationally prohibitive, and uncalibrated across unseen families. SentinelX reports this as an audited **negative finding**, preserving research integrity.

---

## 8. Guard Engine & Analyst Workflow

### 8.1 Prioritization & Guardrail Logic
The Guard maps $s_{\text{guard}}$ into four operational risk tiers:
- **`CRITICAL`** ($s_{\text{prod}} \ge 0.80$): `ESCALATE_TO_ANALYST`
- **`HIGH`** ($0.60 \le s_{\text{prod}} < 0.80$): `INVESTIGATE_FLOW`
- **`MEDIUM`** ($0.30 \le s_{\text{prod}} < 0.60$): `MONITOR`
- **`LOW`** ($s_{\text{prod}} < 0.30$): `ALLOW`

### 8.2 Guardrail Policies
1. **BruteForce Protocol Guardrail**:
   - Model score alone cannot authorize `CRITICAL` escalation for BruteForce without confirmed authentication failure telemetry ($\ge 5$ failures).
   - If unconfirmed, the alert is held back to `HIGH` / `INVESTIGATE_FLOW`.
2. **Benign Burst Guardrail**:
   - Volumetric request surges or reconstruction anomalies alone without confirming attack signals (zero auth failures, zero WAF alerts, $s_{\text{sup}} < \tau^*$) cannot trigger incident escalation.
   - De-escalates alerts to `MEDIUM` / `MONITOR`.

### 8.3 Analyst Review Workflow & Queue Storage
- Stored locally in SQLite (`results/reviews/analyst_reviews.db`).
- Review statuses: `PENDING`, `CONFIRMED_INCIDENT`, `IN_INVESTIGATION`, `ESCALATED_TIER_2`, `BENIGN_SUPPRESSED`.
- Card identification: Every card exposes `flow_id`, short UUID badge (`#<id[:8]>`), batch ID, and UTC timestamp. The full UUID is preserved as the immutable primary key for all detail and review API calls.

---

## 9. Phase 3 Web-Server & WAF Log Correlation

### 9.1 Parsers & Format Support
- **`NginxAccessLogParser`**: Extracts client IP, UTC timestamp, HTTP status, method, and URI path.
- **`NginxErrorLogParser`**: Detects authentication failures (`password mismatch`, `failed to authenticate`, `invalid credentials`).
- **`ModSecurityParser`**: Supports native text audit logs and structured JSON WAF events, extracting client IP, rule ID, action, and severity.

### 9.2 Walkthrough Scenarios
1. **Scenario 1: Slow-Rate Brute Force**:
   - Attack flow ($s_{\text{prod}} = 1.0$) with low rate ($0.53$ req/s, below burst threshold).
   - Correlated logs provide 8 consecutive HTTP 401s and ModSecurity rule 200002.
   - BruteForce protocol confirmation is satisfied $\to$ escalated to `CRITICAL` / `ESCALATE_TO_ANALYST`.
2. **Scenario 2: Benign Traffic Burst**:
   - High-volume traffic burst (75 req/s of HTTP 200 OK) from an internal service.
   - Model anomaly spikes, but zero auth failures and no WAF violations are present.
   - Benign burst guardrail prevents incident escalation $\to$ assigned `MEDIUM` / `MONITOR`.

---

## 10. System Latency & Hardware Caveats

In accordance with Phase 4 reporting requirements, latency must be distinguished by batch size:

| Measurement Condition | Sample Size | Mean Latency per Flow | Operational Assessment |
| :--- | :---: | :---: | :--- |
| **Batched Inference** | $N \ge 10$ flows | **1.25 – 2.45 ms** | **MEETS TARGET (<= 10.0 ms)**. Vectorized numpy/scipy matrix operations and batch XGBoost evaluation achieve high throughput. |
| **Single-Flow Inference** | $N = 1$ flow | **14.80 – 15.55 ms** | **SLIGHTLY EXCEEDS TARGET**. Caused by per-request Python runtime dispatch, Pandas Series coercion, and single-row model prediction overhead. |

**Recommendation**: Production deployments should buffer flows into mini-batches of $N \ge 10$ (or interval $\le 50\text{ ms}$) to ensure the sub-10 ms latency guarantee is met.

---

## 11. Privacy Controls & Redaction

SentinelX enforces strict privacy preservation across the entire data and log ingestion pipeline:
1. **Query String & Token Redaction**:
   - [`sanitize_uri`](file:///d:/sentinelx/src/ingestion/parsers.py) strips all query parameters (`?token=...`, `?key=...`, `?password=...`) and URL fragments (`#...`), retaining only the normalized path (e.g. `/api/v1/auth/login`).
   - [`sanitize_log_line`](file:///d:/sentinelx/src/ingestion/parsers.py) automatically redacts query strings in raw log lines prior to queue persistence (`/path?[REDACTED]`).
2. **Zero Body Payload Inspection**:
   - HTTP request bodies, POST payloads, headers, cookies, and network packet payloads are **NEVER** parsed, stored, or inspected.
   - The system inspects only transport-layer flow telemetry (packet sizes, timings, flags) and web metadata (IPs, timestamps, HTTP status codes).

---

## 12. Operational Limitations & Deployment Assumptions

1. **NAT and Reverse Proxy Deployments**:
   - The correlation engine matches flow `Source IP` to web log `client_ip`.
   - In environments where traffic passes through a Cloud CDN, Load Balancer, or reverse proxy, web access logs record the proxy IP rather than the client IP unless Nginx `realip` or `X-Forwarded-For` is configured.
   - **Operational Rule**: Upstream proxy IP replacement must be trusted **ONLY** when configured behind an authenticated, trusted reverse proxy to avoid IP spoofing.
2. **Clock Synchronization (NTP)**:
   - Temporal window correlation ($\Delta t = \pm 30\text{s}$) requires that network flow exporters and web servers synchronize their system clocks via NTP.
3. **No Autonomous Blocking Claim**:
   - SentinelX makes **no claim of autonomous zero-touch defense**. Stealthy attacks require human review.

---

## 13. Operating Modes & Enforcement Architecture

To support controlled evaluation in operational settings while maintaining safety guarantees, SentinelX implements a dual-mode enforcement architecture:

### 13.1 Dynamic Authorization Model
SentinelX supersedes static, unconditional monitor-only flags with an explicit, per-site policy authorization engine (`EnforcementPolicyEngine`):
- **Default-OFF Invariant**: Autonomous blocking defaults to `False` across all configurations:
  - `GlobalEnforcementConfig.global_blocking_enabled = False`
  - `SiteConfig.blocking_enabled = False`
- **Master Emergency Stop**: An independent, unconditional master control (`emergency_stop_active`) that aborts all enforcement actions across all adapters when activated.
- **Backend Policy Supremacy**: The dashboard UI cannot unilaterally force or override backend enforcement authorization; all decisions evaluate against server-side policy invariants.

### 13.2 Operating Mode Differentiation
1. **Mode 1 — Authorized Real-Site Monitoring**:
   - Continuous passive telemetry ingestion from authorized live sites (e.g. `prod-portal-alpha`).
   - Backed by `MockRealSiteAdapter` (`is_simulated=True`, status `SIMULATED`).
   - Evaluates policy decisions, maintains ephemeral state in memory, and audits outcomes without transmitting network packets, firewall updates, or probes to live infrastructure.
2. **Mode 2 — Isolated Replica Defense**:
   - Active closed-loop enforcement against a local replica application mounted at `/replica`.
   - Backed by `LocalReplicaAdapter` (`is_simulated=False`, status `REPLICA`), which intercepts requests from blocked IPs and serves HTTP 403 Forbidden with remaining TTL.
   - **Lab Allowlist Partitioning**: The replica testbed's allowlist (`10.0.0.99`, `127.0.0.1`) and policies are strictly isolated from Mode 1 sites.

### 13.3 Multi-Factor Enforcement Verification
Automated mitigation is gated behind an eight-stage rule chain:
1. `emergency_stop_active == False`
2. `global_blocking_enabled == True`
3. Site-level `blocking_enabled == True`
4. Client IP not in site's `trusted_allowlist`
5. Risk tier is `CRITICAL` or `HIGH`
6. **Independent Evidence Mandatory**: Model scores alone ($s_{\text{guard}} \ge 0.80$) are strictly prohibited from causing a block.
7. **BruteForce Authentication Guardrail**: For brute-force attacks, $\ge 5$ authentication failures must be independently confirmed via correlated web logs.
8. Configured enforcement adapter is online.

### 13.4 Localhost Enforcement Safeguards & Access Boundaries
Because SentinelX provides runtime toggles for policy enforcement, exposing mutating endpoints (`/api/v1/enforcement/config`, `/api/v1/enforcement/sites/{id}`, `/api/v1/enforcement/blocks/release`, `/api/v1/replica/scenarios/run`) without authorization would permit remote network actors to modify active defenses or trigger DoS via emergency stops.
- **Localhost Isolation by Default**: The API server binds to `127.0.0.1` by default.
- **Loopback Enforcement Filter (`require_local_or_admin`)**: All mutating enforcement routes verify client loopback origin (`127.0.0.1`, `::1`, `localhost`). Non-local client IPs are rejected with `HTTP 403 Forbidden` (`FORBIDDEN_REMOTE_ENFORCEMENT_MUTATION`).
- **Remote Key Authorization**: If remote management across trusted subnets is required, administrators must configure `SENTINELX_ADMIN_KEY` and provide the corresponding `X-SentinelX-Admin-Key` request header.

### 13.5 Decoy Trap Honeypot & Client Identity Hardening
- **Decoy Honeypot Trap (`/replica/admin-decoy`)**: Deployed exclusively on the isolated replica website. Interactions generate structured `honeypot_interaction` events. Under strict data privacy invariants, SentinelX never stores request bodies, passwords, bearer tokens, or form data.
- **Mode 1 Invariant**: Monitored real sites have `honeypot_enabled=False` by default; Mode 1 policy evaluation marks honeypot telemetry as `UNAVAILABLE` and will never claim a honeypot is deployed or use unconfigured traps to authorize blocks.
- **Hardened Client Identity**: Client IP address resolution uses the true connection address (`request.client.host`) and only honors `X-Forwarded-For` from explicitly configured reverse proxies (`set_trusted_proxies(...)`). User-controlled parameters (`?client_ip=`) are ignored for access control decisions, preventing callers from spoofing allowlisted administrative identities.

### 13.6 Split-Screen Presentation Console & Counterfactual Comparison
- **Synchronized Split-Screen View (`/presentation`)**: Integrates the local replica application browser (left) with the SentinelX AI Guard inspection stream (right). Displays the attack location (site, route, timestamp, and simulated client identity) alongside live flow telemetry, model scoring, corroborating evidence, and policy decisions.
- **Protected vs. Without SentinelX Comparison**: Evaluates defensive efficacy side-by-side:
  - *Protected by SentinelX*: Shows real in-process enforcement by `LocalReplicaAdapter`, returning `HTTP 403 Forbidden` with an active TTL countdown.
  - *Without SentinelX (Hypothetical Baseline)*: A separate, non-mutating simulation utilizing synthetic fake data (e.g. simulated credential compromise `ACC-99201-REPLICA`, fake JWT session token, unauthorized administrative portal access).
- **Strict Invariants**:
  - Non-mutating guarantee: Zero real enforcement disabled, zero live traffic dispatched to real infrastructure, zero historical analyst reviews modified.
  - Clear labeling: `SIMULATED ATTACK`, `HYPOTHETICAL OUTCOME`, `BLOCKED IN LOCAL REPLICA`, and Mode 1 marked `SIMULATED / NOT CONNECTED`.
  - Non-destructive reset: The `🔄 Reset Scenario` control clears only scenario attacker blocks (`198.51.100.77`, `198.51.100.88`, `10.0.0.99`) while preserving the analyst review database (`analyst_reviews.db`).

---

## 14. Reproducible Run Instructions & Verification

All results in this technical report can be reproduced using the repository's verified commands:

```powershell
# 1. Run the unified release verification suite (7 checks, 131 tests)
python scripts/verify_release.py

# 2. Run the automated Mode 2 demonstration walkthrough (10 checks)
python scripts/demo_hod.py

# 3. Run the Phase 3 web log & WAF correlation demo
python scripts/demo_phase3.py

# 4. Launch the REST API service and interactive review dashboard
python -m uvicorn src.api.service:app --host 127.0.0.1 --port 8000
# Open http://127.0.0.1:8000/dashboard/ in a browser
# Open http://127.0.0.1:8000/presentation in a browser for the Mode 2 active-scenario presentation console
# Explore the replica testbed at http://127.0.0.1:8000/replica/

# 5. Scan a network flows file via CLI
python -m src.api.cli --file data/samples/logs/synthetic_flows.csv --output table

# 6. Execute the full automated test suite (128 tests)
python -m pytest tests/
```
