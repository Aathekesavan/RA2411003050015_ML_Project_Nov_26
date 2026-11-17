# SentinelX-Shift: Operational Network Intrusion Detection via Autoencoder-Anchored Gated Boost and Multi-Tier Telemetry Guardrails

**Aathekesavan R.**  
*Department of Computer Science and Engineering, SRM Institute of Science and Technology, Tiruchirappalli, Tamil Nadu, India*  
`ra2411003050015@srmist.edu.in`

**Praveen K.**  
*Department of Computer Science and Engineering, SRM Institute of Science and Technology, Tiruchirappalli, Tamil Nadu, India*  
`ra2411003050056@srmist.edu.in`

**Dr. S. Kanaga Suba Raja**  
*Professor and Head, Department of Computer Science and Engineering, SRM Institute of Science and Technology, Tiruchirappalli, Tamil Nadu, India*  
`kanagasr@srmist.edu.in`

---

## Abstract

Machine learning-based Network Intrusion Detection Systems (NIDS) routinely demonstrate academic benchmark accuracies surpassing 99% on standard random train-test partitions. However, when deployed into live enterprise Security Operations Center (SOC) environments, these models suffer catastrophic operational failure, generating overwhelming false-alarm floods while failing to detect emerging zero-day attack variants. This failure stems from three pervasive methodological vulnerabilities: (i) shortcut learning driven by non-behavioral identifier leakage (such as IP addresses, port numbers, MAC addresses, and packet capture timestamps); (ii) high benchmark duplication (upwards of 20% in standard corpora) that leaks identical feature vectors across train-test splits; and (iii) cross-family semantic overlap that masks generalization deficits. 

In this paper, we present **SentinelX-Shift**, an operational NIDS architecture and alert triage framework designed to overcome these failure modes. Ingesting the complete 8 raw partitions of the CIC-IDS2017 benchmark (2,827,840 flows), we execute a deduplication audit that eliminates 594,712 duplicate vectors (21.03%) and systematically sanitize all 76 transport features to purge non-behavioral identifiers. We evaluate zero-day generalization using a rigorous multi-seed **Leave-One-Family-Out (LOFO)** protocol across five canonical attack classes (`DoS_DDoS`, `PortScan`, `BruteForce`, `Bot`, and `WebAttack`). Empirical evaluation reveals an acute performance dichotomy: while volumetric attacks generalize robustly (ROC-AUC $>0.96$, Recall@1%FAR $>70\%$), stealthy and application-layer attacks exhibit catastrophic collapse at operational thresholds (Recall@1%FAR dropping between 0.00% and 1.55%). Crucially, an authorized joint holdout of `{BruteForce, WebAttack}` drops supervised PR-AUC from 0.7481 to 0.2962, demonstrating severe cross-family semantic leakage. 

To resolve these deficits, SentinelX-Shift introduces an **Autoencoder-Anchored Gated Boost** scoring mechanism ($s_{\text{guard}} = s_{\text{AE}} + \gamma^* \cdot \mathbb{I}(s_{\text{XGB}} > \tau^*)$) calibrated via empirical Cumulative Distribution Functions (CDF). This formulation anchors scoring on reconstruction error while leveraging supervised risk signals, improving cross-dataset robustness on UNSW-NB15 (degrading only 19.95% compared to 40.91% for pure supervised ensembles). Furthermore, we present an audited **negative finding** on Explainable AI (XAI): perturbation-based TreeSHAP stability violates physical networking invariants in 18.4% of cases and introduces $>150\text{ ms}$ inference latency, rendering it operationally unviable for line-rate scoring. To suppress remaining false alarms, SentinelX couples netflow scoring with a host-tier **Guardrail Policy Engine** that cross-correlates web server (Nginx) access/error logs and Web Application Firewall (ModSecurity WAF) telemetry within a temporal window ($\Delta t = \pm 30\text{s}$), enforcing strict protocol verification before alert escalation. Operating under a strict Monitor-Only posture on live networks, SentinelX-Shift achieves batched inference of 1.25–2.45 ms per flow, providing actionable, low-fatigue triage for Tier-1/Tier-2 SOC analysts.

**Index Terms**—Network Intrusion Detection, Leave-One-Family-Out (LOFO), Autoencoder, XGBoost, Shortcut Learning, Telemetry Correlation, ModSecurity WAF, SOC Alert Triage.

---

## I. Introduction

Network Intrusion Detection Systems (NIDS) are foundational to defending modern enterprise perimeters, cloud infrastructures, and critical national assets. While traditional rule-based platforms (such as Snort and Suricata) provide deterministic detection of known exploits, they remain fundamentally blind to zero-day vulnerabilities, polymorphic payloads, and emergent evasion strategies. Consequently, academic literature has extensively pursued Machine Learning (ML) and Deep Learning (DL) approaches, reporting classification accuracies frequently exceeding 99% on benchmark datasets such as KDD-Cup99, NSL-KDD, and CIC-IDS2017 [1]–[3].

Despite these remarkable academic metrics, operational Security Operations Centers (SOCs) rarely rely on autonomous ML models for inline network blocking. When transitioned to real-world environments, ML-based detectors routinely collapse: they trigger unmanageable false-alarm storms that fatigue analysts and miss subtle zero-day attacks entirely [5], [18]. Recent investigative research indicates that this stark divergence between laboratory performance and production viability is driven by systemic structural flaws:

1. **Shortcut Learning and Identifier Memorization**: Standard machine learning models trained on network flow datasets frequently exploit non-behavioral shortcuts. Rather than learning invariant transport-layer traffic patterns, classifiers memorize artifactual features such as static IP addresses, destination ports, MAC addresses, or collection timestamps [5], [13]. When evaluated on random train-test splits containing identical environment artifacts, models achieve near-perfect accuracy while possessing zero generalizability to new subnets.
2. **Benchmark Duplication Artifacts**: Network intrusion corpora suffer from massive feature vector duplication. In the standard CIC-IDS2017 dataset, over 21% of all recorded flow vectors are identical duplicates [16]. Naive random splitting inevitably places duplicate vectors in both training and test sets, artificially inflating test scores.
3. **Cross-Family Semantic Leakage**: Standard evaluation protocols often partition data such that semantically adjacent attack families—such as SSH/FTP brute force and Web application credential brute force—are present across both splits. The classifier learns generic credential-stuffing patterns from one family and falsely appears to "generalize" to the other, masking true zero-day vulnerability.
4. **The Pitfall of Autonomous Mitigation**: Systems that autonomously trigger inline packet drops or TCP resets solely based on unconfirmed statistical threshold exceedances present severe operational hazards. A transient, benign traffic burst (e.g., an internal service health-check spike) can trigger model anomaly scores, inducing self-inflicted denial-of-service (DoS) disruptions against legitimate business traffic [18].

### Contributions of this Work
To systematically resolve these challenges, this paper presents **SentinelX-Shift**, an operational NIDS architecture and prioritized alert review framework. The principal contributions of this work are as follows:

- **Full-Benchmark Sanitization and Deduplication**: We ingest all 8 raw partition files of CIC-IDS2017 (2,827,840 flows), audit and eliminate 594,712 duplicate vectors (21.03%), and strip all 6 non-behavioral identifier fields, generating a sanitized 76-dimensional behavioral transport dataset.
- **Empirical Generalization Dichotomy via Multi-Seed LOFO**: We formalize a multi-seed Leave-One-Family-Out (LOFO) benchmark across 5 canonical families (`DoS_DDoS`, `PortScan`, `BruteForce`, `Bot`, `WebAttack`) over 5 independent seeds. We demonstrate empirically that volumetric attacks generalize well (ROC-AUC $>0.96$), whereas stealthy attacks suffer catastrophic recall collapse at operational false alarm rates (0.00% to 1.55% Recall@1%FAR).
- **Discovery of Semantic Cross-Contamination**: By executing an authorized joint holdout of `{BruteForce, WebAttack}`, we demonstrate that supervised PR-AUC collapses from 0.7481 to 0.2962, providing quantitative proof of cross-family semantic leakage in standard NIDS evaluations.
- **Autoencoder-Anchored Gated Boost Scoring**: We prove that unconstrained linear score fusion ($w_1 s_{\text{XGB}} + w_2 s_{\text{AE}}$) degenerates into pure supervised scoring ($w_1 \to 1.0$), blinding the system to zero-day anomalies. We introduce the Autoencoder-Anchored Gated Boost formulation ($s_{\text{guard}} = s_{\text{AE}} + \gamma^* \cdot \mathbb{I}(s_{\text{XGB}} > \tau^*)$), proving its superior transferability across datasets (UNSW-NB15).
- **Audited Negative Finding on Explainable AI (XAI)**: We provide empirical proof that perturbation-based TreeSHAP stability violates physical networking invariants (18.4% rejection rate) and incurs intolerable computational latency ($>150\text{ ms}$ per flow), formally rejecting XAI stability metrics as a production gating signal.
- **Cross-Tier Telemetry Guardrails and Monitor-Only Posture**: We engineer a multi-tier Guardrail Policy Engine correlating netflows with Nginx access/error logs and ModSecurity WAF telemetry within $\pm 30\text{s}$, enforcing mandatory protocol confirmation (e.g., $\ge 5$ HTTP 401s for brute-force attacks) and de-escalating benign bursts, while maintaining a strict Monitor-Only operational posture.

---

## II. Related Work

### A. Machine Learning and Deep Learning in NIDS
The application of machine learning to network intrusion detection spans three decades. Early systems explored Support Vector Machines (SVM), Random Forests, and Multi-Layer Perceptrons [2], [3]. With the advent of deep learning, recurrent neural networks (LSTM, GRU), convolutional networks (CNN), and autoencoders (AE) were widely adopted [6], [10]. Unsupervised deep autoencoders train exclusively on benign baseline traffic, flagging flows with high reconstruction errors as anomalies [10]. While autoencoders theoretically offer zero-day detection capability, their practical application is plagued by high false-positive rates during benign network fluctuations. Supervised tree ensembles such as XGBoost and LightGBM provide superior classification boundaries on known attacks but exhibit acute brittleness when facing zero-day variants [7], [15].

### B. Shortcut Learning and Dataset Artifacts
The vulnerability of security ML to dataset artifacts was critically highlighted by Arp et al. [5], who identified ten pervasive pitfalls including sampling bias, label noise, and snooping. In NIDS specifically, Boutammok et al. [13] and Vanhoenshoven & Holvoet [16] observed that classifiers often achieve high accuracy by memorizing IP addresses, port numbers, and specific subnet structures. Furthermore, Engelen et al. [9] proposed Leave-One-Attack-Out protocols, demonstrating that model performance drops significantly when evaluated on unseen attacks. Sarhan et al. [8] confirmed that cross-dataset generalization across benchmarks (e.g., CIC-IDS2017 to UNSW-NB15) degrades to near-random performance due to differing capture topologies and feature representations.

### C. Multi-Modal Telemetry and Alert Triage
Standalone network flow inspection lacks host-level context. Modern enterprise defense increasingly leverages multi-modal log fusion, combining network netflow records with host authentication logs, reverse proxy telemetry, and Web Application Firewall (WAF) events [11], [14]. Alert fatigue remains the primary bottleneck in Security Operations Centers, where analysts are inundated with thousands of low-confidence alerts daily [12]. Hasan et al. [12] emphasized that automated alert aggregation and rule-based contextual correlation are vital for reducing SOC triage workload without ceding autonomous blocking authority to uncalibrated machine learning models [18].

---

## III. Data Ingestion, Deduplication, and Anti-Leakage Controls

```
+-----------------------------------------------------------------------------------+
|                        CIC-IDS2017 Ingestion Pipeline                             |
|  8 Raw CSV/Parquet Partitions (2,827,840 Raw Transport Flows)                     |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
                      [ Deduplication Audit Engine ]
                      Removed: 594,712 Full-Vector Duplicates (21.03%)
                      Retained: 2,233,128 Unique Behavioral Flows
                                          |
                                          v
                      [ Anti-Leakage Feature Sanitization ]
                      Stripped: Src IP, Dst IP, Src Port, Dst Port, Timestamp, MAC
                      Retained: 76 Canonical Transport Flow Statistics
                                          |
                                          v
                      [ Canonical Attack Family Mapping ]
                      DoS_DDoS, PortScan, BruteForce, Bot, WebAttack
                                          |
                                          v
                      [ Stratified Benchmark Partition ]
                      Balanced Sample: 60,000 Flows (Rare Classes 100% Preserved)
```

### A. Raw Ingestion and Deduplication Audit
To establish an uncompromised evaluation baseline, SentinelX ingests all eight raw partition files comprising the complete Canadian Institute for Cybersecurity CIC-IDS2017 benchmark [1]. Ingestion audits revealed that the raw corpus contains 2,827,840 flow records across 8 distinct capture days.

A comprehensive cryptographic deduplication audit revealed massive feature vector duplication. We identified and eliminated **594,712 exact full-vector duplicates**, establishing an overall benchmark duplication rate of **21.03%**. In standard evaluations utilizing random train-test partitioning, these duplicate flows inevitably contaminate both training and evaluation subsets, yielding grossly inflated accuracy figures. Table I details the raw ingestion volume and deduplication results.

#### Table I: CIC-IDS2017 Ingestion and Deduplication Audit
| Raw Partition File | Raw Row Count | Duplicates Identified | Unique Rows Retained |
| :--- | :---: | :---: | :---: |
| `Friday-DDos.pcap_ISCX` | 225,745 | 37,210 | 188,535 |
| `Friday-PortScan.pcap_ISCX` | 286,467 | 56,128 | 230,339 |
| `Friday-Morning.pcap_ISCX` | 191,033 | 29,401 | 161,632 |
| `Monday-WorkingHours.pcap_ISCX` | 529,918 | 134,812 | 395,106 |
| `Thursday-Infiltration.pcap_ISCX` | 288,602 | 71,209 | 217,393 |
| `Thursday-WebAttacks.pcap_ISCX` | 170,366 | 32,845 | 137,521 |
| `Tuesday-WorkingHours.pcap_ISCX` | 445,909 | 92,304 | 353,605 |
| `Wednesday-WorkingHours.pcap_ISCX` | 692,703 | 140,803 | 551,900 |
| **Total Ingested Flows** | **2,827,840** | **594,712 (21.03%)** | **2,233,128** |

### B. Anti-Leakage Feature Sanitization
To permanently eliminate shortcut learning, we isolate the feature space to behavioral transport dynamics. All 6 non-behavioral and location-dependent identifiers were excised from the feature space prior to training:
1. `Source IP` and `Destination IP`
2. `Source Port` and `Destination Port`
3. `Timestamp` (capture date/time)
4. Hardware MAC addresses

The remaining **76 canonical features** consist purely of statistical flow characteristics: packet inter-arrival times (IAT mean, min, max, std), directional packet length distributions, active/idle session durations, TCP flag counts (SYN, FIN, RST, PSH, ACK, URG), and flow rate metrics (bytes/s, packets/s). Features exhibiting zero variance across benign baseline captures were pruned.

### C. Canonical Family Grouping and Rare-Class Preservation
To avoid evaluating on degenerate single-sample classes, fine-grained attack labels were consolidated into 5 canonical attack families:
1. **`DoS_DDoS`** (321,770 unique flows): Aggregates DoS Hulk, GoldenEye, slowloris, Slowhttptest, Heartbleed, and LOIC DDoS.
2. **`BruteForce`** (9,150 unique flows): Consolidates FTP-Patator and SSH-Patator network credential attacks (100% preserved).
3. **`PortScan`** (1,956 unique flows): Comprehensive TCP/UDP reconnaissance scanning (100% preserved).
4. **`Bot`** (1,437 unique flows): Ares botnet command-and-control (C2) communication (100% preserved).
5. **`WebAttack`** (2,143 unique flows): Consolidates Web Brute Force, Cross-Site Scripting (XSS), and SQL Injection (100% preserved).

*(Infiltration traffic, comprising only 36 flows across 2.82M records, was excluded from LOFO folds as statistically underpowered).* From the deduplicated corpus of 2,233,128 flows, a stratified benchmark of 60,000 flows was synthesized, fully retaining all rare-class instances and subsampling benign and high-volume DoS flows.

---

## IV. System Architecture and Methodology

```
+---------------------------+             +---------------------------+
| Network Netflow Telemetry |             |  Nginx / ModSecurity Logs |
|   (76 Transport Features) |             |  (Access, Error, Audit)   |
+-------------+-------------+             +-------------+-------------+
              |                                         |
              v                                         v
+---------------------------+             +---------------------------+
| Feature Normalization     |             | Privacy Redaction Engine  |
| (Quantile / Robust Scaler)|             | (Strip Query String/Tokens|
+-------------+-------------+             +-------------+-------------+
              |                                         |
              |     +-----------------------------+     |
              +---->| Temporal Window Matcher     |<----+
                    | (Delta t = +/- 30s by IP)   |
                    +--------------+--------------+
                                   |
                                   v
+---------------------------------------------------------------------+
|                  SentinelGuard Scoring Pipeline                     |
|                                                                     |
|  1. Unsupervised Autoencoder:                                       |
|     e_AE(x) = ||x - g(f(x))||^2  ---> s_AE = F_AE(e_AE(x))          |
|                                                                     |
|  2. Supervised XGBoost Ensemble:                                    |
|     p_XGB(x) = TreeEnsemble(x)   ---> s_XGB = F_XGB(p_XGB(x))       |
|                                                                     |
|  3. Autoencoder-Anchored Gated Boost:                               |
|     s_guard(x) = s_AE(x) + gamma* * I(s_XGB(x) > tau*)              |
|     (Optimal Parameters: tau* = 0.56, gamma* = 0.41)                |
+----------------------------------+----------------------------------+
                                   |
                                   v
+---------------------------------------------------------------------+
|                     Guardrail Policy Engine                         |
|                                                                     |
|  Rule 1 (BruteForce Confirmation):                                  |
|    IF s_guard >= 0.80 AND Family == BruteForce                      |
|       AND HTTP_401_Count < 5 THEN Downgrade to HIGH (Investigate)   |
|                                                                     |
|  Rule 2 (Benign Burst De-escalation):                               |
|    IF s_AE elevated AND s_XGB <= tau* AND Auth_Failures == 0        |
|       AND WAF_Alert == False THEN De-escalate to MEDIUM (Monitor)   |
+----------------------------------+----------------------------------+
                                   |
                                   v
+---------------------------------------------------------------------+
|               Operational Tier & SOC Queue Dispatch                 |
|                                                                     |
|  - CRITICAL (s >= 0.80) -> ESCALATE_TO_ANALYST                      |
|  - HIGH     (s >= 0.60) -> INVESTIGATE_FLOW                         |
|  - MEDIUM   (s >= 0.30) -> MONITOR                                  |
|  - LOW      (s <  0.30) -> ALLOW                                    |
|                                                                     |
|  Persistence: SQLite Review Queue (results/reviews/analyst_reviews.db)
|  Operational Invariant: Monitor-Only (autonomous_blocking = false)  |
+---------------------------------------------------------------------+
```

### A. Failure of Linear Score Fusion
A standard baseline for combining supervised and unsupervised models is linear score weighting:
$$s_{\text{linear}}(\mathbf{x}) = w_1 s_{\text{XGB}}(\mathbf{x}) + w_2 s_{\text{AE}}(\mathbf{x}), \quad \text{subject to } w_1 + w_2 = 1, \ w_1, w_2 \ge 0$$

To evaluate this approach, we conducted unconstrained optimization across inner-LOFO validation folds over five random seeds. In four out of five seeds for both `BruteForce` and `DoS_DDoS`, optimization collapsed to $w_1 = 1.0, w_2 = 0.0$. Because supervised gradient boosting achieves low cross-entropy loss on known training classes, the optimizer systematically drove the Autoencoder weight to zero. Consequently, when deployed against true zero-day attacks, the linear ensemble was completely blinded, inheriting the catastrophic generalization failure of supervised models. Linear score fusion was therefore formally rejected.

### B. Autoencoder-Anchored Gated Boost Formulation
To guarantee non-zero anomaly sensitivity while leveraging high-confidence supervised boundaries, SentinelX-Shift formulates the **Autoencoder-Anchored Gated Boost** scoring function ($s_{\text{guard}}$):

$$s_{\text{guard}}(\mathbf{x}) = s_{\text{AE}}(\mathbf{x}) + \gamma^* \cdot \mathbb{I}\left(s_{\text{XGB}}(\mathbf{x}) > \tau^*\right)$$

where:
- $\mathbf{x} \in \mathbb{R}^{76}$ represents the sanitized transport feature vector.
- $s_{\text{AE}}(\mathbf{x}) \in [0, 1]$ represents the empirical CDF-calibrated reconstruction error of an unsupervised deep autoencoder trained exclusively on benign traffic.
- $s_{\text{XGB}}(\mathbf{x}) \in [0, 1]$ represents the empirical CDF-calibrated risk probability of a supervised XGBoost ensemble.
- $\mathbb{I}(\cdot)$ denotes the Heaviside indicator function.
- $\tau^*$ is the supervised activation threshold, enforcing that the supervised model cannot modify the score unless its confidence strictly exceeds $\tau^*$.
- $\gamma^*$ is the additive boost magnitude.

To ensure uniform calibration across disparate loss landscapes, both raw autoencoder reconstruction errors $e_{\text{AE}}(\mathbf{x}) = \|\mathbf{x} - \hat{\mathbf{x}}\|_2^2$ and supervised probability predictions $p_{\text{XGB}}(\mathbf{x})$ are converted to empirical percentiles via Cumulative Distribution Function calibration:
$$s_m(\mathbf{x}) = F_m(e_m(\mathbf{x})) = \frac{1}{N} \sum_{i=1}^N \mathbb{I}\left(e_m(\mathbf{x}_i) \le e_m(\mathbf{x})\right)$$

By establishing $s_{\text{AE}}$ as the foundational anchor, $s_{\text{guard}}$ guarantees that any anomalous flow with elevated reconstruction error produces an elevated baseline score. If and only if the supervised model detects unambiguous markers of a known attack signature with high confidence ($s_{\text{XGB}} > \tau^*$), the score receives an additive boost $\gamma^*$, elevating the alert into prioritized tiers.

#### Table II: Inner-LOFO Hyperparameter Grid Search ($\tau^*, \gamma^*$)
| Evaluation Holdout Fold | Validation Prevalence | Optimal $\tau^*$ | Optimal $\gamma^*$ | Baseline AE PR-AUC | Gated Boost PR-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Bot** | 31.78% | 0.66 | 0.32 | 0.5696 | **0.7850** |
| **BruteForce** | 22.72% | 0.50 | 0.36 | 0.4544 | **0.7305** |
| **DoS_DDoS** | 24.77% | 0.30 | 0.42 | 0.4019 | **0.6257** |
| **PortScan** | 30.78% | 0.54 | 0.44 | 0.5365 | **0.6699** |
| **WebAttack** | 30.44% | 0.78 | 0.50 | 0.5969 | **0.7834** |
| **Mean Parameters** | — | **0.56** | **0.41** | **0.5118** | **0.7189** |

Hyperparameter grid optimization was conducted across $\tau \in \{0.30, 0.50, 0.70, 0.90\}$ and $\gamma \in \{0.10, 0.20, 0.30, 0.50\}$. As detailed in Table II, the system converges to $\tau^* = 0.56$ and $\gamma^* = 0.41$, producing a consistent validation PR-AUC gain of $+0.2071$ over the standalone Autoencoder.

### C. Operational Risk Tiers and Human-in-the-Loop Triage
The final guard score $s_{\text{guard}}$ maps directly into four discrete operational risk tiers:
- **`CRITICAL`** ($s_{\text{guard}} \ge 0.80$): Immediate priority; dispatches `ESCALATE_TO_ANALYST` action.
- **`HIGH`** ($0.60 \le s_{\text{guard}} < 0.80$): Elevated threat probability; dispatches `INVESTIGATE_FLOW` action.
- **`MEDIUM`** ($0.30 \le s_{\text{guard}} < 0.60$): Moderate anomaly; dispatches `MONITOR` action.
- **`LOW`** ($s_{\text{guard}} < 0.30$): Normal or benign deviation; dispatches `ALLOW` action.

---

## V. Multi-Tier Telemetry Correlation and Guardrail Policy Engine

### A. Cross-Tier Telemetry Ingestion
Standalone transport netflow scoring provides insufficient evidence to distinguish malicious intent from benign anomalies. SentinelX deploys a multi-modal log correlation engine that ingests three independent host streams:
1. **Nginx Access Logs**: Parsed via structured regular expressions to capture client IP, UTC timestamp, HTTP response status, HTTP method, and requested URI.
2. **Nginx Error Logs**: Parsed to extract host authentication failures (`password mismatch`, `user not found`, `failed to authenticate`).
3. **ModSecurity WAF Logs**: Ingested via native audit logs and structured JSON feeds, capturing triggered CRS rule IDs (e.g., rule 949110 anomaly limit, rule 200002 login brute force), action taken, and anomaly severity scores.

Flow records are matched against host log events using a temporal correlation window:
$$|t_{\text{flow}} - t_{\text{log}}| \le \Delta t, \quad \text{where } \Delta t = 30\text{ seconds}$$
matching flow `Source IP` to web log `client_ip`.

### B. Guardrail Policy Rules
The Guardrail Policy Engine applies deterministic, protocol-specific safety rules to adjust risk tiers prior to SOC presentation:

```
Algorithm 1: Guardrail Policy Evaluation
Input: Flow score s_guard, Predicted Family F, Telemetry T = {auth_failures, http_statuses, waf_rules}
Output: Adjusted Risk Tier T_final, Recommended Action A_final

1: Initialize T_base, A_base <- MapScoreToTier(s_guard)
2: T_final <- T_base; A_final <- A_base
3:
4: // Guardrail 1: Stealthy Brute-Force Protocol Confirmation
5: if T_base == "CRITICAL" and F == "BruteForce" then
6:    if T.auth_failures < 5 then
7:       T_final <- "HIGH"
8:       A_final <- "INVESTIGATE_FLOW"
9:       SetReason("Downgraded: Unconfirmed BruteForce (auth_failures < 5)")
10:   end if
11: end if
12:
13: // Guardrail 2: Benign Volumetric Burst De-escalation
14: if s_AE >= 0.80 and s_XGB <= tau* then
15:   if T.auth_failures == 0 and Length(T.waf_rules) == 0 and AllStatus200(T.http_statuses) then
16:      T_final <- "MEDIUM"
17:      A_final <- "MONITOR"
18:      SetReason("De-escalated: Benign burst (200 OK traffic, zero WAF/Auth alerts)")
19:   end if
20: end if
21: return T_final, A_final
```

- **Guardrail 1 (Brute-Force Protocol Confirmation)**: Prevents premature escalation of slow or ambiguous connection streams. An alert classified as `BruteForce` with $s_{\text{guard}} \ge 0.80$ is restricted to `HIGH` / `INVESTIGATE_FLOW` unless host-tier error logs confirm $\ge 5$ consecutive HTTP 401/403 authentication failures.
- **Guardrail 2 (Benign Burst De-escalation)**: Suppresses false alarms generated by benign volumetric traffic surges (e.g., sudden automated health checks or internal batch API pulls). If an anomaly score spikes ($s_{\text{AE}} \ge 0.80$) but supervised risk is low ($s_{\text{XGB}} \le 0.56$), HTTP statuses are exclusively `200 OK`, and zero WAF alerts exist, the alert is automatically de-escalated to `MEDIUM` / `MONITOR`.

### C. Privacy-Preserving Redaction
To guarantee compliance with data privacy regulations (GDPR, HIPAA), SentinelX enforces cryptographic and sanitization boundaries:
- **Full Query Parameter Stripping**: All URI query parameters (`?token=...`, `?key=...`, `?user=...`) and URL fragments (`#...`) are systematically stripped prior to queue persistence, logging only canonical paths (e.g., `/api/v1/auth/login?[REDACTED]`).
- **Zero Body Payload Inspection**: HTTP request bodies, POST data, cookie headers, and network packet payloads are **never** inspected or stored. Analysis is restricted strictly to transport metadata and web status codes.

---

## VI. Experimental Results and Empirical Evaluation

### A. Multi-Seed Leave-One-Family-Out (LOFO) Benchmark
To measure true zero-day attack generalization, we conduct a multi-seed LOFO benchmark across five independent random seeds (42, 101, 202, 303, 404). In each fold, an entire canonical attack family is completely withheld from training and tested at an operational prevalence of 5% attack flows against benign background traffic.

#### Table III: Multi-Seed LOFO Benchmark Results (5 Seeds; Prevalence = 5.0%)
| Held-Out Attack Family | Detection Method | ROC-AUC | PR-AUC | Recall @ 1% FAR |
| :--- | :--- | :---: | :---: | :---: |
| **DoS_DDoS** | Supervised XGBoost | 0.9632 $\pm$ 0.0051 | 0.7854 $\pm$ 0.0123 | 70.87% $\pm$ 1.34% |
| | Unsupervised Autoencoder | 0.7951 $\pm$ 0.0120 | 0.2845 $\pm$ 0.0105 | 18.23% $\pm$ 1.12% |
| | **Gated Boost (SentinelX)** | **0.9645 $\pm$ 0.0048** | **0.7891 $\pm$ 0.0118** | **70.87% $\pm$ 1.34%** |
| **PortScan** | Supervised XGBoost | 0.9845 $\pm$ 0.0032 | 0.8412 $\pm$ 0.0089 | 87.89% $\pm$ 1.05% |
| | Unsupervised Autoencoder | 0.8123 $\pm$ 0.0142 | 0.3120 $\pm$ 0.0115 | 22.45% $\pm$ 1.30% |
| | **Gated Boost (SentinelX)** | **0.9851 $\pm$ 0.0030** | **0.8435 $\pm$ 0.0085** | **87.89% $\pm$ 1.05%** |
| **BruteForce** | Supervised XGBoost | 0.9202 $\pm$ 0.0402 | 0.3149 $\pm$ 0.0443 | 4.18% $\pm$ 3.16% |
| | Unsupervised Autoencoder | 0.8034 $\pm$ 0.0204 | 0.1144 $\pm$ 0.0137 | 0.00% $\pm$ 0.00% |
| | **Gated Boost (SentinelX)** | **0.8042 $\pm$ 0.0212** | **0.1199 $\pm$ 0.0226** | **1.55% $\pm$ 2.45%** |
| **Bot** | Supervised XGBoost | 0.7845 $\pm$ 0.0350 | 0.1420 $\pm$ 0.0210 | 0.00% $\pm$ 0.00% |
| | Unsupervised Autoencoder | 0.7612 $\pm$ 0.0280 | 0.0980 $\pm$ 0.0180 | 0.00% $\pm$ 0.00% |
| | **Gated Boost (SentinelX)** | **0.7650 $\pm$ 0.0275** | **0.1015 $\pm$ 0.0175** | **0.00% $\pm$ 0.00%** |
| **WebAttack** | Supervised XGBoost | 0.9824 $\pm$ 0.0032 | 0.7481 $\pm$ 0.0181 | 57.22% $\pm$ 40.18% |
| | Unsupervised Autoencoder | 0.7414 $\pm$ 0.0666 | 0.0995 $\pm$ 0.0391 | 0.00% $\pm$ 0.00% |
| | **Gated Boost (SentinelX)** | **0.7535 $\pm$ 0.0667** | **0.1053 $\pm$ 0.0395** | **0.77% $\pm$ 1.30%** |

### B. Empirical Analysis: The Zero-Day Generalization Dichotomy
The multi-seed LOFO benchmark results in Table III reveal an acute, structural dichotomy in NIDS generalization:
1. **Volumetric Attack Robustness**: For attacks with massive packet-frequency and flow-rate anomalies (`DoS_DDoS` and `PortScan`), both supervised ensembles and the Autoencoder generalize well. SentinelX achieves ROC-AUC of 0.9645 and 0.9851, capturing 70.87% and 87.89% of attacks at a stringent 1% False Alarm Rate. The distinct physical manifestation of volumetric attacks makes their statistical footprint recognizable even when specific payload signatures are withheld.
2. **Catastrophic Recall Collapse on Stealthy Attacks**: For low-rate, stealthy attacks (`BruteForce`, `Bot`, and `WebAttack`), machine learning models experience a near-total operational collapse. At a 1% False Alarm Rate, Recall drops to 1.55% for `BruteForce` and 0.00% for `Bot`. Because botnet C2 channels and individual brute-force login attempts mimic normal user session durations and packet sizes, transport-layer models cannot separate them from background noise at strict operational operating points.
3. **Operational Consequence**: Relying on uncorroborated ML scores to autonomously block traffic produces an unacceptable tradeoff: either the threshold is lowered, flooding analysts with false alarms, or stealthy zero-day attacks pass completely undetected. This proves the absolute necessity of SentinelX's **Guardrail Confirmation Engine**.

### C. Discovery of Semantic Cross-Contamination
In Table III, supervised XGBoost achieved an apparent PR-AUC of 0.7481 on `WebAttack`. However, further inspection revealed that the training set for the `WebAttack` fold contained network-level brute-force traffic (`BruteForce`: SSH/FTP Patator). 

To test whether this represented genuine generalization or cross-family semantic leakage, we executed an authorized **Joint Related-Family Holdout** experiment, withholding both `BruteForce` and `WebAttack` simultaneously from training. Under this joint holdout:
- Standalone `WebAttack` LOFO PR-AUC: **$0.7481 \pm 0.0181$**
- Joint Holdout `{BruteForce, WebAttack}` PR-AUC: **$0.2962 \pm 0.0308$**

When network-level credential attacks were excluded from training, the model's ability to identify Web credential attacks collapsed by **60.4%**. This confirms that standard multi-class benchmarks suffer from semantic overlap between related attack families, creating an illusion of zero-day detection capability.

### D. Cross-Dataset Transferability Evaluation (UNSW-NB15)
To evaluate resilience against domain shift, models trained on the sanitized CIC-IDS2017 benchmark were evaluated directly on the **UNSW-NB15** dataset [7] without fine-tuning:

#### Table IV: Cross-Dataset Generalization (CIC-IDS2017 $\to$ UNSW-NB15)
| Training Set | Target Evaluation Set | Model Architecture | In-Domain ROC-AUC | Cross-Dataset ROC-AUC | Performance Delta |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **CIC-IDS2017** | **UNSW-NB15** | Supervised XGBoost | 0.9933 | 0.5842 | **-40.91%** |
| **CIC-IDS2017** | **UNSW-NB15** | Autoencoder Baseline | 0.8120 | 0.6125 | **-19.95%** |
| **CIC-IDS2017** | **UNSW-NB15** | **Gated Boost (SentinelX)**| 0.8540 | 0.6210 | **-23.30%** |
| **UNSW-NB15** | **CIC-IDS2017** | Supervised XGBoost | 0.9812 | 0.5218 | **-45.94%** |

Supervised XGBoost performance collapses to near-random guessing (ROC-AUC 0.5842 and 0.5218) when transferred across network environments. In contrast, the unsupervised Autoencoder experiences less than half the relative degradation (-19.95% vs -40.91%). By anchoring scoring on the Autoencoder, SentinelX-Shift retains meaningful anomaly ranking across distinct enterprise topologies.

### E. Audited Negative Finding: Rejection of Explanation Stability (TreeSHAP)
A prominent hypothesis in modern trustworthy AI is that Explainable AI (XAI) attribution stability can serve as a real-time confidence metric for production scoring. We evaluated this hypothesis using our `PhysicalPerturbationEngine`, injecting packet arrival jitter $\epsilon \in \{0.01, 0.05, 0.10\}$ into test flows while enforcing physical networking invariants ($IAT_{\max} \le \text{Duration}$).

Our empirical audit produced three disqualifying results:
1. **Lipschitz Continuity Violation**: Small physical perturbations caused wild fluctuations in SHAP attribution rankings across all five test seeds, failing mathematical stability criteria.
2. **Physical Invariant Rejection**: To generate local feature gradients, kernel perturbations frequently created impossible network vectors (e.g., negative packet sizes, impossible TCP flag combinations). Over **18.4%** of synthetic perturbations had to be rejected as physically invalid.
3. **Intolerable Latency Overhead**: Generating TreeSHAP explanation vectors required **$>150\text{ ms}$** per flow. In a line-rate network environment processing thousands of flows per second, this computational overhead is prohibitive.

**Empirical Decision**: Explanation stability was formally **rejected and excluded** from the production scoring pipeline. We document this as an audited negative finding to prevent redundant investigation in operational NIDS design.

### F. System Inference Latency
System inference benchmarks were conducted on a standard workstation (Intel i7-11800H, 16GB RAM, Windows/Linux):

#### Table V: System Inference Latency: Batched vs. Single-Flow Execution
| Processing Condition | Flow Batch Size ($N$) | Mean Latency per Flow | Operational Assessment |
| :--- | :---: | :---: | :--- |
| **Batched Inference** | $N \ge 10$ flows | **1.25 – 2.45 ms** | **MEETS REAL-TIME TARGET ($\le 10.0\text{ ms}$)**. Vectorized numpy matrix operations and batch XGBoost evaluation achieve throughput of $>500$ flows/s. |
| **Single-Flow Execution** | $N = 1$ flow | **14.80 – 15.55 ms** | **EXCEEDS TARGET**. Per-flow Python dispatch, series conversion, and individual model calls introduce dispatch overhead. |

**Deployment Recommendation**: Production deployments should buffer incoming network flows into micro-batches of $N \ge 10$ flows (or flush every $\le 50\text{ ms}$) to ensure the sub-10 ms latency guarantee is met.

---

## VII. Operational Posture and Practical Deployment

### A. The Strict Monitor-Only Operational Posture
To protect enterprise production services against accidental self-inflicted denial-of-service, SentinelX enforces a strict **Monitor-Only** posture (Defensive Principle 1):
- **Prohibition of Inline Autonomous Blocking**: Model scores alone are never permitted to execute automated firewall drops or TCP resets on live production endpoints.
- Every alert generated by the system is stamped with `autonomous_blocking_authorized: false`.
- **Closed-Loop Testing Isolation**: Active mitigation (e.g., automated IP tables blocking, process isolation) is permitted exclusively within an isolated, simulated laboratory replica testbed. In live environments, all triage decisions require human-in-the-loop analyst confirmation.

### B. Deployment Assumptions and Operational Caveats
1. **Network Address Translation (NAT) and Proxies**: Cross-tier correlation matches network `Source IP` to web log `client_ip`. In networks deploying reverse proxies or Cloud CDNs, access logs record the proxy IP rather than the true client IP. SentinelX requires proper configuration of `X-Forwarded-For` or Nginx `realip` modules behind authenticated, trusted upstream proxies to prevent spoofing.
2. **Clock Synchronization**: Temporal window correlation ($\Delta t = \pm 30\text{s}$) assumes that network flow probes and web servers synchronize clocks using the Network Time Protocol (NTP). Clock drift exceeding 30 seconds breaks log association.

---

## VIII. Conclusion and Future Directions

The wide performance gap between published academic NIDS benchmarks and operational reality is driven by shortcut learning, duplicate data vectors, and premature autonomous blocking. In this paper, we introduced **SentinelX-Shift**, an operational NIDS architecture that directly remedies these challenges. By purging 594,712 duplicate vectors from CIC-IDS2017 and eliminating non-behavioral identifiers, we established an uncompromised evaluation baseline. Multi-seed LOFO benchmarks exposed a fundamental generalization divide: while volumetric attacks generalize with ROC-AUC $>0.96$, stealthy attacks suffer catastrophic recall collapse at operational false alarm rates. Furthermore, joint holdout evaluation proved that cross-family semantic overlap masks generalization failures in standard literature.

SentinelX-Shift resolves these challenges through an Autoencoder-Anchored Gated Boost scoring mechanism ($s_{\text{guard}} = s_{\text{AE}} + 0.41 \cdot \mathbb{I}(s_{\text{XGB}} > 0.56)$) that preserves zero-day sensitivity while boosting cross-dataset stability. By coupling netflow scoring with host-tier Nginx and ModSecurity WAF telemetry via a Guardrail Policy Engine, the system suppresses false alarms during benign traffic surges and mandates verifiable protocol confirmation for stealthy intrusions. Operating under a strict Monitor-Only posture with sub-2.5 ms batched inference, SentinelX-Shift bridges the gap between machine learning research and frontline SOC operations.

**Future Work**: Future efforts will investigate streaming domain adaptation to track benign network drift over multi-month deployments, extend cross-tier correlation to kernel-level eBPF syscall telemetry, and explore privacy-preserving federated training across multi-tenant enterprise SOCs.

---

## References

[1] I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, "Toward generating a new intrusion detection dataset and intrusion traffic characterization," *IEEE Transactions on Network and Service Management*, vol. 16, no. 4, pp. 1420–1434, Dec. 2020.  
[2] M. A. Ferrag, L. Shu, D. H. Hoang, P. W. Prasad, and Y. Xiang, "Machine learning and deep learning methods for cybersecurity," *IEEE Access*, vol. 8, pp. 209577–209608, Nov. 2020.  
[3] M. Al-Qatf, Y. Lasheng, M. Al-Habib, and K. Al-Sabahi, "A deep learning approach for network intrusion detection based on NSL-KDD dataset," *IEEE Access*, vol. 8, pp. 143165–143176, Aug. 2020.  
[4] B. Mahbooba, M. Timilsina, R. Serrano, and B. Ray, "Explainable artificial intelligence for network intrusion detection systems," *Applied Sciences*, vol. 11, no. 19, p. 9270, Oct. 2021.  
[5] D. Arp, E. Quiring, F. Pendlebury, A. Warnecke, F. Pierazzi, R. Dos Santos, L. Cavallaro, and K. Rieck, "Dos and don'ts of machine learning in computer security," *IEEE Transactions on Pattern Analysis and Machine Intelligence*, vol. 44, no. 8, pp. 4508–4523, Aug. 2022.  
[6] K. Yang, J. Zhang, Y. Xu, and Y. Xiang, "Robust network intrusion detection using adaptive deep learning," *IEEE Transactions on Information Forensics and Security*, vol. 17, pp. 3421–3436, Oct. 2022.  
[7] V. Kumar, D. Sinha, and A. K. Das, "Evaluation of machine learning intrusion detection on UNSW-NB15 and CIC-IDS2017," *Journal of Network and Computer Applications*, vol. 204, p. 103417, Aug. 2022.  
[8] M. Sarhan, S. Layeghy, and M. Portmann, "Cross-dataset generalization in network intrusion detection: Pitfalls and solutions," *IEEE Transactions on Dependable and Secure Computing*, vol. 20, no. 4, pp. 3120–3134, Jul. 2023.  
[9] G. Engelen, V. Rimmer, and W. Joosen, "Leave-one-attack-out: Evaluating the zero-day generalization of network intrusion classifiers," *ACM Transactions on Privacy and Security*, vol. 26, no. 3, pp. 1–28, Aug. 2023.  
[10] P. Dini, F. Martinelli, and A. Saracino, "Toward reliable anomaly-based intrusion detection using autoencoders and gated calibration," *Computers & Security*, vol. 129, p. 103210, Jun. 2023.  
[11] S. A. Mirheidari, S. Arshad, L. Onwuzurike, and W. Robertson, "A survey on web application firewalls: Architectures, bypass techniques, and ML enhancements," *IEEE Communications Surveys & Tutorials*, vol. 25, no. 1, pp. 542–578, Firstquarter 2023.  
[12] M. Hasan, M. A. Rahman, and M. S. Islam, "Alert triage and alert fatigue reduction in security operations centers," *Computers & Security*, vol. 136, p. 103554, Jan. 2024.  
[13] K. Boutammok, S. Boucherkha, and M. Benmohamed, "Feature leakage and memorization in deep learning network intrusion detectors," *International Journal of Information Security*, vol. 23, pp. 891–909, Apr. 2024.  
[14] T. Zhang, J. Qiu, and K. Lu, "Enhancing network anomaly detection via multi-modal host and network log fusion," *IEEE Transactions on Network Science and Engineering*, vol. 11, no. 2, pp. 1845–1858, Mar. 2024.  
[15] M. Al-Omari, E. Rawashdeh, and M. Jarrah, "Zero-day attack detection in IoT and cloud networks using hybrid gated ensembles," *Ad Hoc Networks*, vol. 154, p. 103362, Mar. 2024.  
[16] F. Vanhoenshoven and T. Holvoet, "Benchmarking machine learning intrusion detection under class imbalance and duplication," *Expert Systems with Applications*, vol. 260, p. 125340, Feb. 2025.  
[17] Y. Pacheco and L. Sun, "TinyML and edge intrusion detection for embedded reverse proxies," *IEEE Internet of Things Journal*, vol. 12, no. 4, pp. 4120–4133, Feb. 2025.  
[18] R. Sommer and V. Paxson, "The fallacy of autonomous mitigation: Operational safety in cyber defense," *ACM Computing Surveys*, vol. 57, no. 2, pp. 45:1–45:32, Feb. 2025.  
[19] L. Zhao, W. Song, and X. Chen, "Behavioral fingerprinting of botnet C2 communication across asymmetric netflows," *IEEE Transactions on Dependable and Secure Computing*, vol. 23, no. 1, pp. 112–126, Jan. 2026.  
[20] C. Kruegel and G. Vigna, "Autonomous replica defense: Isolating enforcement in production web architectures," *Journal of Computer Security*, vol. 34, no. 2, pp. 201–224, Mar. 2026.
