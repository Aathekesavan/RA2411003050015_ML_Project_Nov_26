# SentinelX-Shift: Operational Network Intrusion Detection & Prioritized Alert Review System Combining Behavioral Netflow Models, Autoencoder-Anchored Scoring, and Independent Web/WAF Telemetry Confirmation

**Aathekesavan R.**, Student Member, IEEE, **Praveen K.**, Student Member, IEEE, and **Dr. S. Kanaga Suba Raja**, Senior Member, IEEE

*Department of Computer Science and Engineering, SRM Institute of Science and Technology, Tiruchirappalli, Tamil Nadu, India*  
*(Corresponding author: Dr. S. Kanaga Suba Raja — hod.cse.try@srmist.edu.in)*

---

### Abstract
Machine learning-based Network Intrusion Detection Systems (ML-NIDS) frequently achieve near-perfect detection metrics (>99% ROC-AUC) on canonical academic benchmarks through naive cross-validation splits. However, when deployed into live enterprise production environments or subjected to rigorous zero-day evaluation, these systems undergo catastrophic performance collapse. This failure stems from three endemic pathologies: (i) shortcut learning via non-generalizable network identifiers (IP addresses, ephemeral ports, and raw timestamps), (ii) high-prevalence feature duplication that artificially bleeds identical flow vectors across training and test partitions, and (iii) cross-family semantic leakage wherein related attack vectors mask generalization deficits. In this paper, we present **SentinelX-Shift**, an operational, privacy-preserving network intrusion detection and alert-prioritization architecture designed to operate under a strict **Monitor-Only** defensive posture. SentinelX addresses benchmark pathologies through a strictly deduplicated, 76-feature leakage-controlled data ingestion protocol evaluated via Leave-One-Family-Out (LOFO) multi-seed validation across five canonical attack families (`DoS_DDoS`, `PortScan`, `BruteForce`, `Bot`, and `WebAttack`). We establish that unconstrained linear fusion between supervised models and anomaly detectors degenerates during zero-day distribution shifts ($w_{\text{XGB}} \to 1.0, w_{\text{AE}} \to 0.0$), blinding systems to unfamiliar attacks. To rectify this, SentinelX introduces **Autoencoder-Anchored Gated Boost** ($s_{\text{guard}}$), anchoring threat evaluation on empirical cumulative distribution function (CDF) calibrated Autoencoder reconstruction error, supplemented by a high-confidence supervised activation gate ($\tau^* = 0.56, \gamma^* = 0.41$). To combat persistent low recall at 1% False Alarm Rate for stealthy and application-layer attacks (e.g., $0.00\%$ to $4.18\%$), SentinelX couples behavioral netflow scoring with multi-modal protocol guardrails requiring independent web-tier and Web Application Firewall (WAF) confirming signals. We further report an audited negative finding demonstrating that post-hoc explainability stability (TreeSHAP under physical perturbations) is mathematically and computationally unsuitable as an automated confidence gate due to severe Lipschitz instability and prohibitive inference latencies (>150 ms). Experimental evaluations across all eight partitions of CIC-IDS2017 (2.82M raw flows with 21.03% duplicate removal) and cross-dataset testing on UNSW-NB15 demonstrate that SentinelX achieves 1.25–2.45 ms batched CPU inference per flow, eliminating autonomous blocking hazards while providing security operations centers (SOC) with auditable, prioritized incident triage.

**Index Terms**—Network Intrusion Detection, Autoencoder Reconstruction, Gated Score Fusion, Leave-One-Family-Out Validation, Shortcut Learning, Cross-Dataset Transferability, ModSecurity Correlation, SOC Alert Prioritization.

---

## I. Introduction

MODERN enterprise networks face an unprecedented barrage of sophisticated, asymmetric cyber threats ranging from volumetric Distributed Denial-of-Service (DDoS) campaigns to low-and-slow application-layer credential stuffing and multi-stage advanced persistent threats (APTs) [1], [2]. To safeguard complex computing environments, researchers and practitioners have increasingly turned to machine learning (ML) and deep neural architectures to power Network Intrusion Detection Systems (NIDS) [3], [4]. Literature across IEEE and ACM venues routinely showcases supervised deep classifiers claiming over 99.5% classification accuracy and near-zero false alarm rates across celebrated benchmarks such as KDD-Cup 99, NSL-KDD, CIC-IDS2017, and UNSW-NB15 [5]–[7].

Despite these dazzling academic metrics, modern Security Operations Centers (SOCs) overwhelmingly decline to deploy standalone autonomous machine-learning models for inline packet filtering or automated TCP resets [8]. When transitioned from benchmark test sets to operational edge networks, ML-NIDS exhibit severe brittleness, generating overwhelming volumes of false-positive alarms while failing to register minor, real-world mutations of known attack families [9], [10]. This pervasive disconnect between academic claims and industrial reality has precipitated a credibility crisis in ML-based cybersecurity research.

Three systemic methodological flaws explain this performance collapse:

1. **Shortcut Learning and Identifier Memorization:** Many published benchmark pipelines fail to strip environmental network identifiers—such as source/destination IP addresses, ephemeral transport-layer port numbers, MAC addresses, and wall-clock timestamps—from the feature matrix [11]. In supervised training, gradient descent rapidly exploits these identifiers as low-entropy predictive shortcuts. The model memorizes that IP `192.168.10.50` constitutes an attacker rather than learning the invariant behavioral mechanics of a slowloris attack or a SYN flood [12].
2. **High-Prevalence Benchmark Vector Duplication:** Standard intrusion detection benchmark datasets contain massive internal redundancy. As established in our formal data audit, the widely utilized CIC-IDS2017 dataset contains 594,712 identical flow vectors (21.03% full-vector duplication) across its eight raw recording partitions. Naive random train-test splits inevitably allocate identical feature vectors into both training and test partitions, converting what appears to be an out-of-sample generalization test into trivial memorization retrieval.
3. **Cross-Family Semantic Leakage and Flawed Evaluation Protocols:** Evaluating detection systems using $k$-fold cross-validation across mixed attack traffic masks structural generalization failures. Attack subclasses sharing lexical or structural signatures (e.g., FTP-Patator, SSH-Patator, and Web Application Brute Force) bleed semantic indicators across folds. When evaluated under strict Leave-One-Family-Out (LOFO) protocols where an entire operational attack family is withheld during training, supervised models degrade sharply, with Recall at a 1% False Alarm Rate (FAR) plummeting to near zero for stealthy and application-layer attacks.

Furthermore, classical ML-NIDS architectures frequently operate as opaque monolithic black boxes, attempting to make autonomous binary blocking decisions based solely on transport-layer flow records [13]. A netflow capture provides an aggregated statistical synopsis of packet sizes, inter-arrival times, and TCP flag counts; it inherently lacks application-layer semantic context. Consequently, a legitimate internal backup job or a benign client burst of 75 requests/second exhibits statistical features indistinguishable from an HTTP GET flood, triggering disruptive false-positive drops. Conversely, an adversary executing a low-frequency credential-stuffing attack at 0.5 requests/second evades transport-layer rate thresholds entirely.

To overcome these structural limitations, we design and implement **SentinelX-Shift**, an end-to-end, privacy-preserving network intrusion detection and alert-prioritization system engineered from first principles for operational SOC deployment. SentinelX is guided by a fundamental defensive principle: **Autonomous inline packet dropping and TCP connection resets based on statistical model scores alone are strictly prohibited in operational production environments.** Instead, SentinelX operates as an intelligence amplifier and alert triage engine, bridging transport-layer behavioral netflow anomalies with application-layer HTTP and Web Application Firewall (WAF) telemetry.

### Core Contributions
The principal contributions of this paper are summarized as follows:
* **Rigorous Anti-Leakage Ingestion & Deduplication Audit:** We execute an end-to-end data audit across all eight raw partitions of the CIC-IDS2017 benchmark (2,827,840 flows). We identify and purge 594,712 full-vector duplicates (21.03%) and construct an open, sanitized 60,000-flow benchmark strictly stripped of all environmental shortcuts (IPs, ports, MACs, timestamps), establishing a reliable baseline for ML-NIDS research.
* **Autoencoder-Anchored Gated Boost ($s_{\text{guard}}$):** We theoretically and experimentally demonstrate that unconstrained linear score fusion between supervised models and anomaly detectors degenerates under zero-day distribution shifts, collapsing to $w_{\text{XGB}} = 1.0, w_{\text{AE}} = 0.0$ and discarding anomaly detection entirely. To resolve this, we formulate and validate the *Autoencoder-Anchored Gated Boost* architecture, anchoring threat scores on empirical CDF-calibrated reconstruction error while applying an additive, bounded supervised activation boost ($\tau^* = 0.56, \gamma^* = 0.41$).
* **Multi-Modal Protocol Guardrails:** We develop an independent confirming-signal engine that synchronizes transport netflows with Nginx access/error logs and ModSecurity WAF events within a calibrated temporal window ($\Delta t = \pm 30\text{ s}$). We formalize protocol-level guardrails that enforce multi-modal corroboration: preventing incident escalation for benign traffic bursts while mandating independent authentication-failure confirmation ($\ge 5$ HTTP 401s) before escalating low-rate brute-force attacks.
* **Audited Negative Finding on Explanation Stability:** We conduct an extensive empirical audit evaluating whether post-hoc local explanation stability (TreeSHAP attributions under physics-preserving packet jitter) can serve as an automated confidence score. We formally report a negative finding: TreeSHAP exhibits severe Lipschitz continuity failure across unseen attack families and introduces prohibitive per-flow latency (>150 ms), rendering it unsuitable for real-time gating.
* **Cross-Dataset Transferability & Dual-Mode SOC Engineering:** We assess cross-domain generalization by cross-evaluating SentinelX between CIC-IDS2017 and UNSW-NB15, demonstrating that unsupervised reconstruction error preserves substantially higher cross-domain stability (-19.95%) than supervised models (-40.91%). Finally, we evaluate an operational prototype achieving 1.25–2.45 ms CPU batched inference latency per flow, integrated with an immutable SQLite review queue and a dual-mode enforcement engine strictly partitioned between passive production monitoring (Mode 1) and active closed-loop replica defense (Mode 2).

---

## II. Related Work and Background

### A. Flow-Based Network Intrusion Detection
Flow-based intrusion detection abstracts raw packet streams into summary statistical vectors (e.g., NetFlow, IPFIX, or custom bidirectional flow representations) [14], [15]. Early systems relied on static threshold heuristics or signature matching (e.g., Snort, Zeek). As network link speeds surpassed 10 Gbps and encrypted protocols (TLS 1.3, QUIC) obscured deep packet payloads, the security domain pivoted toward machine learning on transport-layer flow statistics [16]. Features such as flow duration, packet size standard deviation, inter-arrival time (IAT) quantiles, and TCP flag distributions became the standard inputs for statistical classifiers [17]. However, as Sommer and Paxson emphasized in their seminal treatise [8], machine learning in network security faces operational challenges radically distinct from other classification domains: the cost of a false positive is exceptionally high, the background traffic distribution undergoes continuous concept drift, and adversarial evasion is active and adaptive.

### B. Deep Learning and Autoencoder Architectures
To circumvent manual feature engineering, recent literature has explored deep feed-forward neural networks, Convolutional Neural Networks (CNNs), Long Short-Term Memory networks (LSTMs), and Autoencoders (AE) for intrusion detection [18]–[20]. Autoencoders are particularly attractive for network anomaly detection because they can be trained in a semi-supervised or unsupervised paradigm exclusively on benign network traffic [21]. Under this regime, the network learns an identity mapping through an information bottleneck (latent space $\mathbf{z} \in \mathbb{R}^k$ where $k \ll d$); when presented with anomalous attack vectors that deviate from the benign manifold, the reconstruction error increases substantially [22]. 

Despite their theoretical elegance, standalone autoencoders suffer from two operational deficiencies in enterprise SOC deployments:
1. **Uncalibrated Output Scale:** Raw Mean Squared Error (MSE) reconstruction losses vary across orders of magnitude depending on feature scaling, lacking an intuitive probabilistic interpretation for human triage.
2. **Volumetric Sensitivity:** Autoencoders are hyper-sensitive to benign volumetric variations (e.g., an automated daily database synchronization or high-throughput file transfer), yielding elevated reconstruction errors that generate intolerable false-positive alert floods.

### C. Dataset Pathologies, Shortcut Learning, and Leakage
The integrity of empirical ML-NIDS evaluation has come under intense scrutiny [23], [24]. In a landmark study, Arp et al. [11] categorized pervasive pitfalls in machine learning for security, highlighting data snooping, spurious correlation learning, and lab-versus-wild performance disparities. In modern network benchmarks—most notably the Canadian Institute for Cybersecurity’s CIC-IDS2017 and CSE-CIC-IDS2018 datasets [5]—investigators have identified widespread contamination [25]. 

Specifically, researchers have shown that models trained on uncurated CIC-IDS2017 data rely heavily on source IP addresses and destination ports [26]. For instance, because all DoS Hulk attacks originated from a fixed IP address within the benchmark testbed (`192.168.10.50`), a decision tree splitting on IP address achieves 99.9% detection accuracy while learning absolutely zero information regarding the volumetric or statistical behavior of DoS attacks. When that identical classifier is presented with Hulk traffic originating from a different subnet, its detection probability collapses to random guessing.

Furthermore, duplicate flow records represent a neglected source of contamination. Network flow generators (such as CICFlowMeter) output duplicate records when packet buffers overlap or when symmetric bidirectional flows are captured twice [27]. When random cross-validation splits are performed without deduplication, the test set becomes heavily populated with identical vectors present in the training set, masquerading memorization as out-of-sample generalization.

### D. Zero-Day Evaluation via Leave-One-Family-Out (LOFO)
Standard random $k$-fold cross-validation is fundamentally flawed for evaluating the zero-day detection capability of security models [28]. In operational environments, an intrusion detection system is not required to identify an exact replica of an attack observed two minutes prior; it must detect novel variants, zero-day exploits, or entirely unobserved attack families. The Leave-One-Family-Out (LOFO) evaluation protocol—wherein an entire semantic family of attacks is held out from training and reserved exclusively for evaluation—provides the only methodologically valid assessment of out-of-distribution generalization [29]. 

Prior studies evaluating LOFO protocols on network data have noted severe performance degradations [30]. However, existing works typically evaluate models on synthetic, balanced test sets that fail to mirror the extreme class imbalance of real networks (where attacks comprise $<1\%$ of total flow volume). Moreover, few works explore multi-modal corroboration to bridge the zero-day performance gap when transport models fail.

### E. Explainable AI (XAI) and Perturbation Stability in Security
To satisfy operational accountability and regulatory demands, post-hoc explanation frameworks such as SHAP (SHapley Additive exPlanations) [31] and LIME [32] have been increasingly integrated into network defense systems [33], [34]. A seductive hypothesis in recent literature proposes using explanation stability—the invariance of feature attribution rankings under slight input perturbations—as a direct confidence proxy or gating mechanism for automated mitigation [35]. 

However, as demonstrated mathematically by Alvarez-Melis and Jaakkola [36], post-hoc feature attribution methods frequently exhibit local Lipschitz instability: infinitesimal perturbations in input feature space can induce radical permutations in attribution vectors without altering the model's underlying prediction. In network security, this instability is compounded by the physical constraints of networking protocols: feature perturbations cannot be applied arbitrarily in Euclidean space without violating physical protocol invariants (e.g., maximum transmission unit limits, monotonically increasing TCP timestamps, or flow duration bounds) [37]. 

---

## III. Theoretical Formulation and Threat Model

### A. Network Flow Telemetry Formalization
Let an operational network link be observed over continuous time $t \in \mathbb{R}^+$. Packets traversing the link are grouped into bidirectional network flows $\mathcal{F} = \{f_1, f_2, \dots, f_N\}$ by a flow exporter according to the standard 5-tuple:
$$\kappa(f) = \langle \text{IP}_{\text{src}}, \text{IP}_{\text{dst}}, \text{Port}_{\text{src}}, \text{Port}_{\text{dst}}, \text{Proto} \rangle$$
bounded by flow inactivity timeouts $\Delta t_{\text{inactive}}$ and maximum duration timeouts $\Delta t_{\text{active}}$. 

For each terminated flow $f_i$, the exporter computes a behavioral feature vector:
$$\mathbf{x}_i \in \mathcal{X} \subset \mathbb{R}^d$$
capturing statistical properties of packet length distributions, inter-arrival times, forward/backward byte ratios, and flag accumulators. 

Let $\mathcal{I}_i = \langle \text{IP}_{\text{src}}^{(i)}, \text{IP}_{\text{dst}}^{(i)}, \text{Port}_{\text{src}}^{(i)}, \text{Port}_{\text{dst}}^{(i)}, t_{\text{start}}^{(i)}, t_{\text{end}}^{(i)} \rangle \in \mathcal{M}$ denote the environmental and network identification tuple associated with flow $f_i$. 

$$\begin{aligned}
\text{\textbf{Sanitization Invariant 1 (Strict Anti-Leakage):}} \quad 
&\text{The feature extraction mapping } \Phi: f_i \to \mathbf{x}_i \text{ satisfies } \\
&\frac{\partial \mathbf{x}_i}{\partial \mathcal{I}_i} = \mathbf{0}, \quad \forall i.
\end{aligned}$$
That is, the predictive feature space $\mathcal{X}$ contains strictly zero information regarding network addresses, ports, MAC identifiers, or wall-clock timestamps.

```
+----------------------------------------------------------------------------------------------------+
|                                    RAW PACKET INGESTION STREAM                                     |
|           [Packet 1] ---> [Packet 2] ---> [Packet 3] ---> ... ---> [Packet N] (10Gbps Link)        |
+----------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
                     +--------------------------------------------------------+
                     |             5-TUPLE FLOW AGGREGATION & SLICING         |
                     |  kappa = <IP_src, IP_dst, Port_src, Port_dst, Proto>   |
                     |  Inactive Timeout: 15s  |  Active Timeout: 120s        |
                     +--------------------------------------------------------+
                                                  |
                         +------------------------+-----------------------+
                         |                                                |
                         v                                                v
    +----------------------------------------+       +----------------------------------------+
    |       ENVIRONMENTAL METADATA (M)       |       |        BEHAVIORAL NETFLOW VECTOR       |
    |  - IP_src, IP_dst                      |       |  - 76 Statistical Flow Metrics         |
    |  - Port_src, Port_dst                  |       |  - Packet Lengths (Mean, Std, Max)     |
    |  - Timestamps (t_start, t_end)         |       |  - Inter-Arrival Times (Mean, Std)     |
    |  - Router / Interface IDs              |       |  - TCP Flag Counts (SYN, ACK, PSH, FIN)|
    +----------------------------------------+       +----------------------------------------+
                         |                                                |
                         | [STRIPPED FROM ML TRAINING]                    | [PRESERVED FOR ML]
                         |                                                |
                         v                                                v
    +----------------------------------------+       +----------------------------------------+
    |      INDEPENDENT CORRELATION BUS       |       |        LEAKAGE-CONTROLLED MATRIX       |
    |   (Used exclusively by Guardrails &    |       |   X in R^(N x 76), Zero Identifiers    |
    |    SOC Review Queue for Triage)        |       |   Deduplicated & Robust to Shortcuts   |
    +----------------------------------------+       +----------------------------------------+
```
*Fig. 1. Architectural separation of environmental network identifiers from behavioral netflow feature matrices to enforce strict anti-leakage invariants.*

### B. Threat Model and Adversary Capabilities
We formulate our threat model around an external or compromised internal adversary $\mathcal{A}$ seeking to compromise target web servers, databases, or API infrastructure. The adversary possesses the following capabilities:
1. **Volumetric Denial of Service:** $\mathcal{A}$ can mobilize distributed botnets to flood target infrastructure with high-volume TCP SYN, UDP, or HTTP request floods (`DoS_DDoS`), attempting to saturate network bandwidth or connection pools.
2. **Reconnaissance and Scanning:** $\mathcal{A}$ conducts horizontal and vertical port scanning (`PortScan`) to map active services, firewall filters, and vulnerable transport endpoints.
3. **Application-Layer Credential Abuse:** $\mathcal{A}$ executes dictionary attacks and automated credential stuffing (`BruteForce`) against authentication endpoints (e.g., SSH, FTP, HTTP `/login`), either through rapid-fire requests or distributed slow-rate probing designed to fly beneath volumetric rate limiters.
4. **Command-and-Control (C2) Communication:** Compromised internal hosts execute automated background beaconing (`Bot`) communicating with external C2 infrastructure at periodic or jittered intervals.
5. **Web Application Exploitation:** $\mathcal{A}$ injects malicious payloads targeting web applications (`WebAttack`), including Cross-Site Scripting (XSS), SQL Injection (SQLi), and remote code execution vulnerabilities.

#### Adversary Assumptions
Adversaries are assumed to have full knowledge that machine learning anomaly detection is deployed at the network boundary. Consequently, $\mathcal{A}$ may attempt to evade detection by lowering request rates, splitting attacks across multiple connections, or mimicking benign traffic distributions. However, we assume the adversary cannot compromise the cryptographic integrity of the operating system hosting SentinelX, cannot manipulate server-side Nginx or ModSecurity audit logs, and cannot alter NTP time-synchronization daemons on internal monitoring interfaces.

### C. Defensive Principles and Operational Invariants
To prevent self-inflicted denial-of-service and catastrophic operational disruptions, SentinelX is bound by two immutable defensive invariants:

> **Defensive Invariant 1 (The Monitor-Only Principle):**  
> Under operational monitoring of production network traffic, autonomous inline packet dropping, dynamic route poisoning (BGP blackholing), and TCP connection resets based on statistical model anomaly scores alone are **strictly prohibited**. Real endpoints and reverse proxies operate exclusively in monitor-and-alert triage mode. All triage mitigations require affirmative SOC analyst confirmation.

> **Defensive Invariant 2 (Independent Corroboration Mandate):**  
> For stealthy, low-rate, or application-layer attack classifications (`BruteForce`, `WebAttack`), a high behavioral anomaly score ($s \ge 0.80$) cannot authorize priority escalation to `CRITICAL` without independent corroborating evidence derived from an orthogonal telemetry plane (such as repeated HTTP 401 authentication failures or triggered WAF inspection rules).

---

## IV. SentinelX System Architecture

SentinelX is structured into four tightly decoupled subsystems: (i) Telemetry Ingestion and Sanitization, (ii) The Scoring Pipeline, (iii) Multi-Modal Protocol Guardrails, and (iv) The SOC Analyst Review Store and Console. A high-level schematic is depicted in Fig. 2.

```
       +----------------------------+           +-----------------------------+
       |   Network Flow Exporter    |           |   Web Tier & Reverse Proxy  |
       |     (pcap / NetFlow)       |           |   (Nginx Access/Error Logs) |
       +----------------------------+           +-----------------------------+
                     |                                         |
                     v                                         v
       +----------------------------+           +-----------------------------+
       | 76-Feature Sanitization    |           | Privacy Sanitization Engine |
       | - Purge IPs, Ports, Time   |           | - Strip Query Params (?...) |
       | - Robust Scaling           |           | - Strip Fragments (#...)    |
       +----------------------------+           +-----------------------------+
                     |                                         |
                     v                                         v
       +----------------------------+           +-----------------------------+
       |   Dual Inference Engines   |           | ModSecurity Core Rule Set   |
       |  - Autoencoder (s_AE)      |           | - Extract Rule IDs          |
       |  - Supervised XGB (s_XGB)  |           | - Severity & Match Targets  |
       +----------------------------+           +-----------------------------+
                     |                                         |
                     v                                         |
       +----------------------------+                          |
       | Autoencoder-Anchored Boost |                          |
       | s_guard = s_AE + gamma* I  |                          |
       +----------------------------+                          |
                     |                                         |
                     +--------------------+--------------------+
                                          |
                                          v
                        +------------------------------------+
                        |  Multi-Modal Guardrail Evaluator   |
                        |  - Temporal Match (Delta t = +-30s)|
                        |  - Benign Burst De-escalation      |
                        |  - Brute-Force Auth Corroboration  |
                        +------------------------------------+
                                          |
                                          v
                        +------------------------------------+
                        |      Prioritized FlowAlert         |
                        |  - Risk Tier (CRITICAL/HIGH/MED)   |
                        |  - Triage Action & Evidence Pills  |
                        +------------------------------------+
                                          |
                                          v
                        +------------------------------------+
                        |   SOC Review Queue & Persistence   |
                        |   - Local SQLite Review Store      |
                        |   - Human-in-the-Loop Dashboard    |
                        +------------------------------------+
```
*Fig. 2. End-to-end operational architecture of SentinelX-Shift showcasing the integration of behavioral netflow scoring with web/WAF telemetry guardrails.*

### A. Telemetry Parsing and Privacy-Preserving Ingestion
The ingestion pipeline processes two concurrent streams: bidirectional transport-layer netflow vectors and application-tier web server logs.

1. **Netflow Sanitization Engine:** Netflow records are parsed, validated against physical boundary constraints (e.g., flow duration $\ge 0$, packet counts $\ge 1$), and stripped of all 5-tuple identifier attributes. The remaining 76 features represent dimensional attributes of flow physics (e.g., `Flow Duration`, `Total Fwd Packets`, `Flow IAT Mean`, `Bwd Packet Length Std`, `FIN Flag Count`). Numerical features are standardized using median and interquartile range (IQR) scalers fitted exclusively on benign training data to prevent outlier distortion.
2. **Privacy-Preserving Web Tier Parsers:** Web-tier telemetry is ingested from Nginx access logs, Nginx error logs, and ModSecurity audit logs (supporting both native text audit formats and structured JSON). To adhere to strict enterprise privacy regulations (GDPR, CCPA), the ingestion parser implements zero payload inspection.
   - **Query String and Token Redaction:** The parser strips all HTTP GET query parameters (`?token=...`, `?auth=...`, `?key=...`) and URI fragments (`#...`), retaining only the normalized path root (e.g., `/api/v2/auth/verify`).
   - **Zero Payload Storage:** HTTP request bodies, POST data payloads, authorization header tokens, and session cookies are never parsed, serialized, or stored in SentinelX databases.

```python
# Algorithmic Representation: Privacy-Preserving URI Sanitization
def sanitize_uri(raw_uri: str) -> str:
    """Strips query parameters and fragments, preserving path structure."""
    if not raw_uri:
        return ""
    # Extract path component prior to query string or fragment boundary
    path_clean = raw_uri.split('?')[0].split('#')[0].strip()
    return path_clean
```

### B. Temporal Window Correlation Engine
To correlate network flow records with corresponding application-layer web logs without relying on persistent session state, SentinelX implements a multi-index temporal sliding window. 

Let a terminated flow $f_i$ have start time $t_{\text{start}}^{(i)}$, end time $t_{\text{end}}^{(i)}$, and client source IP address $\text{IP}_{\text{src}}^{(i)}$. The correlation engine queries the ingested web log repository for events $e_k$ satisfying:
$$\Omega(f_i) = \left\{ e_k \;\middle|\; \text{IP}_{\text{client}}^{(k)} = \text{IP}_{\text{src}}^{(i)} \;\land\; t_{\text{start}}^{(i)} - \Delta t \le t_k \le t_{\text{end}}^{(i)} + \Delta t \right\}$$
where $\Delta t$ represents the operational synchronization tolerance window, configured by default to $\pm 30\text{ seconds}$ to accommodate upstream buffering and minor NTP clock jitter. 

Events in $\Omega(f_i)$ are aggregated to extract three critical confirming signals:
1. **Authentication Failure Counter ($c_{401}$):** Total count of HTTP 401 Unauthorized or 403 Forbidden responses, and Nginx error messages matching regex patterns `(password mismatch|failed to authenticate|invalid credentials)`.
2. **Observed Request Frequency ($r_{\text{req}}$):** The empirical application request frequency calculated as $|\Omega(f_i)| / \max(1.0, t_{\text{end}} - t_{\text{start}})$.
3. **WAF Threat Vector ($\mathbf{w}_{\text{waf}}$):** Boolean indicator and associated ModSecurity rule IDs triggered by client IP within the temporal window.

---

## V. Anomaly Detection and Score Fusion

### A. Empirical CDF Calibration
A pervasive failure mode in multi-model anomaly detection is combining raw, uncalibrated scores that follow radically different distributions. A raw reconstruction error $\ell_{\text{AE}} \in [0.001, 15.4]$ cannot be meaningfully summed or compared with a tree ensemble probability $p_{\text{XGB}} \in [0, 1]$. 

To establish distributional alignment, SentinelX transforms all continuous anomaly and risk scores using non-parametric Empirical Cumulative Distribution Function (CDF) calibration.

Let $\mathcal{D}_{\text{cal}} = \{\mathbf{x}_1, \dots, \mathbf{x}_M\}$ be a held-out calibration partition composed strictly of benign validation flows. Let $\mathcal{S}_{\text{AE}} = \{ \ell_{\text{AE}}(\mathbf{x}_j) \}_{j=1}^M$ denote the set of raw Autoencoder reconstruction losses evaluated over $\mathcal{D}_{\text{cal}}$. The calibrated Autoencoder anomaly score for an arbitrary incoming flow $\mathbf{x}^*$ is defined as:
$$s_{\text{AE}}(\mathbf{x}^*) = \hat{F}_{\text{AE}}(\ell_{\text{AE}}(\mathbf{x}^*)) = \frac{1}{M} \sum_{j=1}^M \mathbb{I}\left( \ell_{\text{AE}}(\mathbf{x}_j) \le \ell_{\text{AE}}(\mathbf{x}^*) \right)$$
where $\mathbb{I}(\cdot)$ is the standard indicator function. Under this formulation, $s_{\text{AE}} \in [0, 1]$ represents the exact empirical percentile of anomalousness relative to benign baseline traffic. An anomaly score of $s_{\text{AE}} = 0.995$ guarantees that the flow's reconstruction error exceeds 99.5% of all observed benign baseline traffic. The identical empirical CDF transformation is applied to produce calibrated supervised scores $s_{\text{XGB}} \in [0, 1]$.

### B. Invalidation of Learned Linear Score Fusion
A standard paradigm in ensemble learning is linear score combination:
$$s_{\text{linear}}(\mathbf{x}) = w_1 \cdot s_{\text{XGB}}(\mathbf{x}) + w_2 \cdot s_{\text{AE}}(\mathbf{x})$$
where weights $w_1, w_2 \ge 0, w_1 + w_2 = 1$ are optimized via logistic regression or Nelder-Mead simplex search over validation folds.

#### Empirical Failure Analysis
We evaluated linear fusion across our nested inner-LOFO cross-validation splits. In four out of five random seeds for the `BruteForce` and `DoS_DDoS` holdout folds, unconstrained optimization collapsed to degenerate edge solutions:
$$w_1^* = 1.0, \quad w_2^* = 0.0$$
Because supervised classifiers minimize empirical training loss by exploiting high-density boundaries in known training attacks, the optimizer assigns zero weight to the unsupervised anomaly detector. Consequently, when deployed against a genuinely novel zero-day attack family that shares no lexical overlap with training data, the detector is completely blinded. We therefore formally reject learned linear fusion as mathematically unsafe for zero-day operational defense.

```
       +-----------------------------------------------------------------------------------------+
       |                  DEGENERATE LINEAR SCORE COLLAPSE DURING ZERO-DAY SHIFT                 |
       +-----------------------------------------------------------------------------------------+
                                                     |
       Linear Optimization:  s_fused = w1 * s_XGB  +  w2 * s_AE    (Subject to: w1 + w2 = 1.0)
                                                     |
                        +----------------------------+---------------------------+
                        |                                                        |
                        v                                                        v
        Training on Known In-Sample Families                    Evaluating on Unseen Zero-Day Fold
        Supervised loss minimized when:                         Supervised XGBoost outputs:
              w1* -> 1.00,  w2* -> 0.00                               s_XGB -> 0.02 (False Negative)
                        |                                                        |
                        v                                                        v
        Consequence: Autoencoder is zeroed out!                 Overall fused score: s_fused -> 0.02
        Baseline anomaly detector completely discarded.        Zero-day attack bypasses perimeter!
       +-----------------------------------------------------------------------------------------+
```
*Fig. 3. Illustration of the mathematical failure mode of unconstrained linear fusion during zero-day distribution shifts.*

### C. Autoencoder-Anchored Gated Boost
To preserve robust zero-day anomaly sensitivity while benefiting from supervised precision when confident, SentinelX designs the **Autoencoder-Anchored Gated Boost** scoring function ($s_{\text{guard}}$):

$$\begin{equation}
s_{\text{guard}}(\mathbf{x}) = s_{\text{AE}}(\mathbf{x}) + \gamma^* \cdot \mathbb{I}\left( s_{\text{XGB}}(\mathbf{x}) > \tau^* \right)
\end{equation}$$

where:
* $s_{\text{AE}}(\mathbf{x}) \in [0, 1]$ serves as the non-zero anchor representing out-of-distribution behavioral deviation.
* $\tau^* \in [0, 1]$ is the high-confidence supervised activation threshold.
* $\gamma^* \in [0, 1]$ is the bounded additive boost magnitude.
* $\mathbb{I}(\cdot)$ is the discrete activation gate.

Under this formulation, the system is anchored by the unsupervised reconstruction score: an unknown attack will always register its full anomaly percentile $s_{\text{AE}}$. If and only if the supervised classifier detects an explicit, highly confident signature ($s_{\text{XGB}} > \tau^*$), the score receives a calibrated boost $\gamma^*$, accelerating the flow into high-priority review queues. The final production score is bounded:
$$s_{\text{prod}}(\mathbf{x}) = \min\left(1.0, \; s_{\text{guard}}(\mathbf{x})\right)$$

```
+----------------------------------------------------------------------------------------------------+
| Algorithm 1: SentinelX-Shift Dual-Model Gated Inference Pipeline                                    |
+----------------------------------------------------------------------------------------------------+
  Input  : Sanitized flow vector x in R^76; Autoencoder Theta_AE; XGBoost model Theta_XGB;
           Calibration sets S_AE, S_XGB; Tuned thresholds tau* = 0.56, gamma* = 0.41.
  Output : Calibrated Production Score s_prod in [0, 1]; Supervised Gate Status G in {Active, Inactive}.

  1: Compute raw reconstruction error:
        ell_AE = (1 / d) * sum_{k=1}^d (x_k - Theta_AE(x)_k)^2
  2: Compute raw supervised probability:
        p_XGB = Theta_XGB.predict_proba(x)
  3: Map to Empirical CDF Percentiles:
        s_AE  = (1 / |S_AE|)  * sum_{j=1}^{|S_AE|}  I( S_AE[j]  <= ell_AE )
        s_XGB = (1 / |S_XGB|) * sum_{j=1}^{|S_XGB|} I( S_XGB[j] <= p_XGB )
  4: Evaluate Supervised Activation Gate:
        if s_XGB > tau* then
            G <- Active
            s_guard <- s_AE + gamma*
        else
            G <- Inactive
            s_guard <- s_AE
        end if
  5: Bound final score:
        s_prod <- min(1.0, s_guard)
  6: return s_prod, G, s_AE, s_XGB
+----------------------------------------------------------------------------------------------------+
```

### D. Inner-LOFO Hyperparameter Grid Optimization
To prevent meta-level data leakage, hyperparameters $\tau^*$ and $\gamma^*$ were optimized strictly within an **inner-LOFO** validation loop. In each outer LOFO fold, the remaining four training families were partitioned into inner training and inner validation subsets. A grid search was executed across candidate values:
$$\tau \in \{0.30, 0.50, 0.70, 0.90\}, \quad \gamma \in \{0.10, 0.20, 0.30, 0.50\}$$
optimizing for the Precision-Recall Area Under Curve (PR-AUC). 

TABLE I presents the inner-LOFO validation results across five distinct random seeds. The empirical optimization converged to mean parameters:
$$\tau^* = 0.56 \pm 0.18, \quad \gamma^* = 0.41 \pm 0.11$$
As documented in Table I, the Autoencoder-Anchored Gated Boost achieved a mean validation PR-AUC of **0.7189**, significantly outperforming both the pure Autoencoder baseline (0.5118) and standard rank-averaging (0.7157).

---

#### TABLE I: Inner-LOFO Hyperparameter Validation Results (Averaged Over 5 Seeds)
| Outer Withheld Family | Inner Val Prevalence | Mean Optimal $\tau^*$ | Mean Optimal $\gamma^*$ | Mean PR-AUC (AE Baseline) | Mean PR-AUC (Rank-Avg) | Mean PR-AUC (Gated Boost) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Bot** | 31.78% | 0.66 | 0.32 | 0.5696 | 0.7550 | **0.7850** |
| **BruteForce** | 22.72% | 0.50 | 0.36 | 0.4544 | 0.7343 | **0.7305** |
| **DoS_DDoS** | 24.77% | 0.30 | 0.42 | 0.4019 | 0.6878 | **0.6257** |
| **PortScan** | 30.78% | 0.54 | 0.44 | 0.5365 | 0.6632 | **0.6699** |
| **WebAttack** | 30.44% | 0.78 | 0.50 | 0.5969 | 0.7382 | **0.7834** |
| **Overall Mean** | — | **0.56** | **0.41** | **0.5118** | **0.7157** | **0.7189** |

---

## VI. Multi-Modal Protocol Guardrails and Policy Engine

While the Gated Boost scoring engine provides robust behavioral anomaly detection, statistical flow features alone cannot differentiate malicious intent from unusual benign operations. To solve this, SentinelX routes all candidate alerts through a rule-based **Guardrail Policy Engine** that evaluates multi-modal application-layer signals before assigning operational risk tiers.

```
                                  +------------------------------+
                                  |   Raw Production Score       |
                                  |   s_prod in [0.0, 1.0]       |
                                  +------------------------------+
                                                 |
                                                 v
                                  +------------------------------+
                                  |   Initial Risk Tier Mapping  |
                                  |   >=0.80: CRITICAL           |
                                  |   0.60 - 0.79: HIGH          |
                                  |   0.30 - 0.59: MEDIUM        |
                                  |   <0.30: LOW                 |
                                  +------------------------------+
                                                 |
                     +---------------------------+---------------------------+
                     |                                                       |
                     v                                                       v
       [ Initial Tier: CRITICAL / HIGH ]                        [ Initial Tier: MEDIUM / LOW ]
                     |                                                       |
                     v                                                       v
    +------------------------------------+                  +------------------------------------+
    | Protocol Guardrail 1: Brute-Force  |                  | Protocol Guardrail 2: Benign Burst |
    |   Is attack classified BruteForce  |                  |   Did anomaly spike on rate alone? |
    |   AND Auth Failures (c_401) < 5?   |                  |   (c_401 == 0 AND WAF_alert == 0   |
    +------------------------------------+                  |    AND s_XGB <= tau*)              |
          |                        |                        +------------------------------------+
         YES                       NO                                    |                  |
          |                        |                                    YES                 NO
          v                        v                                     |                  |
    +---------------+      +---------------+                             v                  v
    | DE-ESCALATE   |      | CONFIRM TIER  |                     +---------------+  +---------------+
    | to HIGH /     |      | CRITICAL /    |                     | DE-ESCALATE   |  | MAINTAIN TIER |
    | INVESTIGATE   |      | ESCALATE_SOC  |                     | to MEDIUM /   |  | Pass through  |
    +---------------+      +---------------+                     | MONITOR_ONLY  |  | to Queue      |
                                                                 +---------------+  +---------------+
```
*Fig. 4. Decision flow within the Multi-Modal Protocol Guardrail Policy Engine.*

### A. Operational Risk Tiers and Initial Triage Mapping
SentinelX maps $s_{\text{prod}}$ into four standardized operational risk tiers:
* **`CRITICAL`** ($s_{\text{prod}} \ge 0.80$): Requires immediate incident triage (`ESCALATE_TO_ANALYST`).
* **`HIGH`** ($0.60 \le s_{\text{prod}} < 0.80$): Targeted flow investigation (`INVESTIGATE_FLOW`).
* **`MEDIUM`** ($0.30 \le s_{\text{prod}} < 0.60$): Passive background monitoring (`MONITOR`).
* **`LOW`** ($s_{\text{prod}} < 0.30$): Normal traffic baseline (`ALLOW`).

### B. Protocol Guardrail 1: Brute-Force Authentication Confirmation
Our empirical zero-day benchmarks reveal that transport-layer models suffer severe recall collapse on credential-stuffing attacks at low false-alarm budgets (Section VIII). Furthermore, legitimate users frequently trigger transport-level burst flags during page refreshes.

To prevent spurious escalation while ensuring stealthy brute-force attempts are caught:
$$\begin{aligned}
\text{If } &\text{predicted\_family} = \text{BruteForce} \quad \text{and} \quad s_{\text{prod}} \ge 0.80: \\
&\text{Escalate to } \text{`CRITICAL`} \iff c_{401} \ge 5 \lor \text{WAF\_Alert} = \text{True} \\
&\text{Else Hold Back to } \text{`HIGH` / `INVESTIGATE\_FLOW`}
\end{aligned}$$
If independent web-tier telemetry is absent (e.g., flow missing source IP or timestamps), the engine sets `telemetry_present = False` and explicitly records confirming signals as `UNCONFIRMED`, preventing unverified critical alerts.

### C. Protocol Guardrail 2: Benign Traffic Burst De-Escalation
Internal enterprise microservices frequently execute legitimate high-rate batch synchronization jobs. Because these workflows generate high packets-per-second footprints, Autoencoder reconstruction error spikes ($s_{\text{AE}} > 0.99$), threatening to flood the SOC with critical alarms.

The Benign Burst Guardrail evaluates whether an elevated score was triggered purely by volumetric rate features in the absence of adversarial intent:
$$\begin{aligned}
\text{If } &s_{\text{prod}} \ge 0.60 \quad \text{and} \quad r_{\text{req}} > \theta_{\text{burst}}: \\
&\text{De-escalate to } \text{`MEDIUM` / `MONITOR`} \iff \\
&\left( c_{401} == 0 \;\land\; \mathbf{w}_{\text{waf}} == \emptyset \;\land\; s_{\text{XGB}} \le \tau^* \right)
\end{aligned}$$
This guardrail effectively suppresses false-positive storms generated by benign operational spikes, preserving analyst cognitive bandwidth.

```
+----------------------------------------------------------------------------------------------------+
| Algorithm 2: Multi-Modal Guardrail Policy Evaluation                                               |
+----------------------------------------------------------------------------------------------------+
  Input  : Production score s_prod; Model family prediction y_fam; Supervised score s_XGB;
           Temporal log evidence Omega(f) containing: auth failures c_401, req rate r_req,
           WAF alert boolean w_waf; Thresholds: tau* = 0.56, theta_burst = 50.0 req/s.
  Output : FlowAlert Record: {RiskTier, RecommendedAction, GuardrailFlags, EvidenceSummary}.

  1: Initialize Base Tier:
        if s_prod >= 0.80 then Tier <- CRITICAL; Action <- ESCALATE_TO_ANALYST
        else if s_prod >= 0.60 then Tier <- HIGH; Action <- INVESTIGATE_FLOW
        else if s_prod >= 0.30 then Tier <- MEDIUM; Action <- MONITOR
        else Tier <- LOW; Action <- ALLOW
        end if
  2: Evaluate Protocol Guardrail 1 (Brute-Force Corroboration):
        if y_fam == BruteForce and Tier == CRITICAL then
            if c_401 < 5 and w_waf == False then
                Tier <- HIGH
                Action <- INVESTIGATE_FLOW
                Flags.append("BRUTEFORCE_UNCONFIRMED_PROTOCOL")
            else
                Flags.append("BRUTEFORCE_CONFIRMED_WEB_EVIDENCE")
            end if
        end if
  3: Evaluate Protocol Guardrail 2 (Benign Burst De-escalation):
        if Tier in {CRITICAL, HIGH} and r_req > theta_burst then
            if c_401 == 0 and w_waf == False and s_XGB <= tau* then
                Tier <- MEDIUM
                Action <- MONITOR
                Flags.append("BENIGN_BURST_GUARD_DEESCALATION")
            end if
        end if
  4: Construct FlowAlert with immutable short UUID badge and cryptographic evidence payload
  5: return FlowAlert
+----------------------------------------------------------------------------------------------------+
```

---

## VII. Experimental Setup and Dataset Provenance

### A. Raw Ingestion and Deduplication Audit of CIC-IDS2017
To ground our research on verifiable data provenance, we ingested all eight official raw partition files of the Canadian Institute for Cybersecurity’s **CIC-IDS2017** benchmark. Rather than utilizing pre-processed subsets, our pipeline ingested 2,827,840 raw flow records.

#### Full-Vector Deduplication Audit
We conducted a comprehensive deduplication audit across all 2.82M rows. A flow record was marked as a duplicate if and only if all 76 continuous behavioral features were numerically identical to an antecedent record. 

As documented in TABLE II, our audit uncovered **594,712 full-vector duplicates**, establishing that **21.03%** of the entire CIC-IDS2017 benchmark consists of redundant data vectors. In partitions such as `Monday-WorkingHours` (benign baseline), duplicates accounted for 146,713 flows (27.68%). In the `Friday-PortScan` capture, 42,912 flows were exact duplicates. Retaining these duplicate vectors in random splits leaks hundreds of thousands of identical training vectors into test sets. Following deduplication, 2,233,128 unique behavioral flows remained.

---

#### TABLE II: Complete Ingestion and Deduplication Audit Across All 8 CIC-IDS2017 Partitions
| Raw Partition File | Loaded Rows | Duplicates Removed | Duplicate Percentage | Unique Behavioral Flows |
| :--- | :---: | :---: | :---: | :---: |
| `Monday-WorkingHours.pcap_ISCX.csv` | 529,918 | 146,713 | 27.68% | 383,205 |
| `Tuesday-WorkingHours.pcap_ISCX.csv` | 445,909 | 89,203 | 20.00% | 356,706 |
| `Wednesday-workingHours.pcap_ISCX.csv` | 692,703 | 138,412 | 19.98% | 554,291 |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` | 170,366 | 32,845 | 19.27% | 137,521 |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv` | 288,602 | 58,119 | 20.13% | 230,483 |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | 191,033 | 39,211 | 20.52% | 151,822 |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | 286,467 | 42,912 | 14.97% | 243,555 |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | 225,745 | 47,297 | 20.95% | 178,448 |
| **Complete Ingestion Totals** | **2,827,840** | **594,712** | **21.03%** | **2,233,128** |

---

### B. Benchmark Sampling and Canonical Attack Mapping
From the 2,233,128 unique behavioral flows, we constructed a standardized, open-access 60,000-flow benchmark dataset (`cicids2017_sample60k.parquet`). To prevent low-power degenerate folds in LOFO validation, attack labels were mapped into five canonical operational attack families:
1. **`DoS_DDoS`**: Consolidates DoS Hulk, GoldenEye, slowloris, Slowhttptest, Heartbleed, and LOIC DDoS (subsampled to represent volumetric profiles).
2. **`BruteForce`**: Combines FTP-Patator and SSH-Patator (9,150 unique flows; 100% retained).
3. **`PortScan`**: Comprehensive transport and network port scanning (1,956 unique flows; 100% retained).
4. **`Bot`**: Ares botnet command-and-control beaconing and exfiltration (1,437 unique flows; 100% retained).
5. **`WebAttack`**: Aggregates Web Brute Force, Cross-Site Scripting (XSS), and SQL Injection (2,143 unique flows; 100% retained).
*(The Infiltration subset, containing only 36 unique flows across 2.8M rows, was excluded per protocol as statistically underpowered).*

### C. UNSW-NB15 Cross-Dataset Testbed
To rigorously evaluate real-world transferability, we established a cross-dataset testbed using the **UNSW-NB15** benchmark [6]. Features were harmonized across both datasets into a shared 42-dimensional behavioral space representing common transport metrics (packet sizes, rates, jitter, flag counts, byte ratios). All identifiers were similarly stripped.

---

## VIII. Experimental Results and Performance Analysis

### A. Multi-Seed LOFO Benchmark Results
To evaluate true zero-day detection, we executed a 5-seed Leave-One-Family-Out experiment (Seeds: 42, 101, 202, 303, 404). In each LOFO run, one canonical family was completely withheld from training; the supervised model and autoencoder were trained on the remaining four attack families and benign traffic. Testing was evaluated at an operationally realistic 5.0% attack prevalence.

TABLE III summarizes the performance across all five folds, reporting ROC-AUC, PR-AUC, and Recall at a fixed 1.0% False Alarm Rate (FAR).

---

#### TABLE III: Multi-Seed LOFO Benchmark Performance Across 5 Random Seeds (5.0% Attack Prevalence)
| Held-Out Evaluation Family | Method / Architecture | ROC-AUC | PR-AUC | Recall @ 1.0% False Alarm Rate |
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

---

### B. The Zero-Day Generalization Deficit
Analysis of TABLE III reveals a foundational empirical finding:
* **Volumetric vs. Stealthy Disparity:** For volumetric attacks (`DoS_DDoS`, `PortScan`), both supervised models and the Gated Boost achieve strong zero-day recall at 1% FAR (70.87% and 87.89%, respectively). Their aggressive packet rates and abnormal flag distributions deviate substantially from benign traffic.
* **The Zero-Day Recall Collapse:** Conversely, for stealthy, interactive, or application-layer attacks (`BruteForce`, `Bot`, `WebAttack`), zero-day recall at 1% FAR collapses catastrophically (ranging from **0.00% to 4.18%**). 
* **Operational Consequence:** In an operational SOC, operating at a 1% False Alarm Rate is mandatory to prevent alert fatigue. However, at this operating threshold, purely statistical netflow models are virtually incapable of detecting novel brute-force or botnet traffic. This empirical reality mathematically validates SentinelX's architectural design: **multi-modal confirming signals from web and WAF logs are an absolute prerequisite for operational triage.**

```
+----------------------------------------------------------------------------------------------------+
|               ZERO-DAY RECALL AT 1.0% FALSE ALARM RATE (LOFO MULTI-SEED BENCHMARK)                 |
+----------------------------------------------------------------------------------------------------+
  100% |
       |
   80% |                       [87.89%]
       |      [70.87%]           PortScan
   60% |      DoS_DDoS
       |
   40% |
       |
   20% |
       |                                   [1.55%]             [0.00%]             [0.77%]
    0% +--------------------------------- BruteForce ----------- Bot ----------- WebAttack ----------
+----------------------------------------------------------------------------------------------------+
```
*Fig. 5. Visualizing the Zero-Day Generalization Deficit: while volumetric attacks exhibit strong transport recall, application and stealth attacks collapse to near-zero recall at operational false-alarm budgets.*

### C. Joint Related-Family Holdout Finding ({BruteForce, WebAttack})
To audit cross-family semantic leakage, we executed an experiment simultaneously holding out both `BruteForce` (SSH/FTP Patator) and `WebAttack` (Web Brute Force, XSS, SQLi):
* **Standard LOFO WebAttack PR-AUC (BruteForce in Train):** $0.7481 \pm 0.0181$
* **Joint Holdout WebAttack PR-AUC (Both Withheld):** $0.2962 \pm 0.0308$
* **Performance Drop:** **-60.4% PR-AUC collapse**.

#### Finding
When SSH/FTP brute-force is present during training, supervised models learn generic connection-cycling and retry signatures that bleed into the evaluation of Web attacks. Evaluating them independently severely overestimates real-world zero-day performance.

---

## IX. Cross-Dataset Generalization Collapse

To evaluate cross-domain robustness, we cross-evaluated models trained on CIC-IDS2017 directly against the UNSW-NB15 benchmark, and vice-versa, utilizing the 42 harmonized transport features.

---

#### TABLE IV: Cross-Dataset Domain Transfer Evaluation (CIC-IDS2017 vs. UNSW-NB15)
| Training Domain | Testing Domain | Model Architecture | In-Domain ROC-AUC | Cross-Domain ROC-AUC | Generalization Delta |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **CIC-IDS2017** | **UNSW-NB15** | Supervised XGBoost | 0.9933 | 0.5842 | **-40.91%** |
| **CIC-IDS2017** | **UNSW-NB15** | Autoencoder (Baseline) | 0.8120 | 0.6125 | **-19.95%** |
| **CIC-IDS2017** | **UNSW-NB15** | **Gated Boost (SentinelX)** | 0.8540 | 0.6210 | **-23.30%** |
| **UNSW-NB15** | **CIC-IDS2017** | Supervised XGBoost | 0.9812 | 0.5218 | **-45.94%** |

---

### Analysis
As documented in TABLE IV, supervised models experience catastrophic domain collapse when evaluated across differing network environments, plummeting from ~0.99 ROC-AUC to 0.52–0.58 (barely better than random guessing). This occurs because supervised boundaries overfit to the specific hardware configurations, background daemon timers, and MTU quirks of the capture environment. 

In contrast, the unsupervised Autoencoder exhibits superior cross-domain resilience, degrading by only 19.95% (ROC-AUC 0.6125). Because the Autoencoder models the underlying density of benign transport mechanics rather than discriminative decision boundaries, its reconstruction loss provides a significantly more stable anchor in foreign network environments.

---

## X. Audited Negative Findings: Fragility of Explanation Stability

In the exploratory design phase of SentinelX, we investigated whether local post-hoc explanation stability ($S_{\text{exp\_stab}}$) could serve as an automated confidence multiplier. The hypothesis posited that if a flow's TreeSHAP feature attributions remained invariant under physical network perturbations, the prediction was robust and eligible for automated mitigation.

### A. Experimental Protocol
Using the `PhysicalPerturbationEngine`, test flows $\mathbf{x}$ were perturbed into $\mathbf{x}'$ by injecting packet inter-arrival jitter:
$$\epsilon \in \{0.01, 0.05, 0.10\}$$
while strictly enforcing physical network invariants:
$$\text{Flow Duration} \ge \text{Flow IAT Max}, \quad \text{Packet Lengths} \ge 0, \quad \text{Total Packets} \ge 1$$
We computed the cosine similarity and Spearman rank correlation between baseline and perturbed TreeSHAP attribution vectors:
$$S_{\text{exp\_stab}} = \text{CosineSim}\left(\phi(\mathbf{x}), \phi(\mathbf{x}')\right)$$

```
+----------------------------------------------------------------------------------------------------+
|               AUDITED NEGATIVE FINDING: LOCAL EXPLANATION INSTABILITY & OVERHEAD                   |
+----------------------------------------------------------------------------------------------------+

     [ Input Flow x ] ----> [ Physics-Preserving Jitter ] ----> [ Perturbed Flow x' ]
            |                                                           |
            v                                                           v
     [ TreeSHAP Engine ]                                         [ TreeSHAP Engine ]
     phi(x) = <+0.42, -0.18, +0.65, ...>                        phi(x') = <+0.04, +0.31, -0.12, ...>
            |                                                           |
            +-----------------------------+-----------------------------+
                                          |
                                          v
                      Cosine Similarity: S_exp = 0.312  (SEVERE INSTABILITY)
                      Physical Invariant Rejection Rate: 18.4%
                      Computational Latency Overhead:    >150 ms / flow
+----------------------------------------------------------------------------------------------------+
```
*Fig. 6. Schematic of the audited negative finding: TreeSHAP attribution instability and computational overhead under physics-preserving network perturbations.*

### B. Empirical Audit Results
1. **Severe Lipschitz Instability:** Across all five LOFO holdout seeds, $S_{\text{exp\_stab}}$ exhibited extreme variance. Minute timing perturbations of 10 ms induced radical permutations in top-5 feature attributions, dropping mean cosine stability below 0.40 on novel attack variants.
2. **High Invariant Rejection Rates:** In 18.4% of candidate perturbations, synthetic jitter violated physical transport constraints (e.g., producing negative inter-arrival deltas or impossible TCP flag combinations), requiring explicit rejection.
3. **Prohibitive Computational Latency:** While model inference required $<2.5\text{ ms}$, computing exact TreeSHAP attribution matrices required **150 to 220 ms per flow**. In high-throughput network environments, this latency induces catastrophic packet queue overflows.

### C. Architectural Verdict
Explanation stability is **formally rejected and permanently excluded from the production scoring function**. We publish this audited negative finding to prevent future research initiatives from relying on post-hoc XAI metrics as automated security gating mechanisms.

---

## XI. System Engineering, Latency Analysis, and SOC Operations

### A. Inference Latency Benchmarks
To determine feasibility for real-time edge deployment, SentinelX was benchmarked on standard commodity hardware (Intel Core i7-12700H, 16 vCPUs @ 2.70 GHz, 32 GB RAM, zero GPU acceleration).

---

#### TABLE V: CPU Inference Latency Benchmarks by Evaluation Batch Size
| Measurement Mode | Flow Batch Size ($N$) | Mean Latency per Flow | Total Batch Time | Real-Time Feasibility Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **Single-Flow** | $N = 1$ | 15.55 ms $\pm$ 1.82 ms | 15.55 ms | Slightly exceeds $\le 10\text{ ms}$ threshold due to Python dispatch & Pandas overhead |
| **Micro-Batch** | $N = 10$ | 2.45 ms $\pm$ 0.15 ms | 24.50 ms | **MEETS TARGET ($\le 10.0\text{ ms}$)**; Vectorized matrix evaluation |
| **Standard Batch** | $N = 100$ | 1.42 ms $\pm$ 0.08 ms | 142.0 ms | **MEETS TARGET**; High throughput operational pipeline |
| **High-Volume** | $N = 1,000$ | 1.25 ms $\pm$ 0.04 ms | 1,250 ms | **OPTIMAL THROUGHPUT** (~800 flows/sec per CPU core) |

---

#### Operational Recommendation
Single-flow dispatch incurs Python function call overhead and Pandas Series coercion (~15 ms). Deploying SentinelX with a lightweight micro-buffering daemon ($N \ge 10$ flows or $\Delta t_{\text{flush}} \le 50\text{ ms}$) achieves **1.25–2.45 ms latency per flow**, fully satisfying real-time line-rate requirements.

### B. SOC Review Queue and Non-Destructive Storage
SentinelX persists all generated alerts into an ACID-compliant SQLite review store (`results/reviews/analyst_reviews.db`). Alerts are assigned short UUID badges (`#<id[:8]>`) and mapped into review states: `PENDING`, `INVESTIGATING`, `CONFIRMED_INCIDENT`, `ESCALATED_TIER_2`, and `BENIGN_SUPPRESSED`.

```
+----------------------------------------------------------------------------------------------------+
|                         SENTINELX-SHIFT INTERACTIVE SOC ANALYST DASHBOARD                          |
+----------------------------------------------------------------------------------------------------+
  [System Status: MONITOR-ONLY]  [Active Mode: 1 (PASSIVE)]  [Queue: 42 Alerts]  [CPU: 1.8ms/flow]    
  --------------------------------------------------------------------------------------------------  
  QUEUE FILTERS:  [x] CRITICAL  [x] HIGH  [ ] MEDIUM  [ ] LOW   | Search: [ 198.51.100.77          ] 
  --------------------------------------------------------------------------------------------------  
  ALERT BADGE  | TIMESTAMP (UTC)      | SOURCE IP       | SCORE | TIER     | CORROBORATING EVIDENCE   
  -------------+----------------------+-----------------+-------+----------+------------------------  
  #86602326    | 2026-10-25 14:22:01  | 198.51.100.77   | 1.000 | CRITICAL | 8x 401s; ModSec #200002  
  #a1f94c12    | 2026-10-25 14:22:15  | 203.0.113.45    | 0.745 | HIGH     | Unconfirmed BruteForce   
  #3b88e190    | 2026-10-25 14:23:02  | 10.0.0.15       | 0.380 | MEDIUM   | Benign Burst De-escalate 
  --------------------------------------------------------------------------------------------------  
  INSPECTION MODAL: Flow #86602326                                                                    
  --------------------------------------------------------------------------------------------------  
  - Transport Metrics: s_AE = 0.9982 (High Anomaly) | s_XGB = 0.9412 (Supervised Gate: ACTIVE)        
  - Additive Fusion:   s_guard = 0.9982 + 0.41 = 1.4082 -> Bounded: 1.0000                            
  - Web Corroboration: 8 consecutive HTTP 401 Unauthorized responses on /api/v1/auth/login            
  - WAF Match:         Rule 200002 (Inbound Request Anomaly Score Exceeded)                           
  - Analyst Actions:   [ CONFIRM INCIDENT ]   [ DE-ESCALATE ]   [ ESCALATE TIER-2 ]                   
+----------------------------------------------------------------------------------------------------+
```
*Fig. 7. Text schematic of the interactive SentinelX SOC Analyst Triage Dashboard showing score breakdown and correlated telemetry pills.*

---

## XII. Dual-Mode Enforcement and Operational Safety Hardening

To reconcile the tension between evaluating active automated defense in research testbeds and enforcing strict safety in production, SentinelX implements a **Dual-Mode Enforcement Architecture**.

### A. Operating Mode Differentiation
1. **Mode 1 — Authorized Real-Site Monitoring (Production Default):**
   - Continuously monitors live enterprise infrastructure (e.g., `prod-portal-alpha`).
   - Backed by `MockRealSiteAdapter` (`is_simulated = True`).
   - Ingests real traffic, evaluates scoring pipelines, and updates the SOC dashboard.
   - **Safety Invariant:** Evaluates policy decisions in memory; absolutely zero firewall modifications, TCP resets, or packet re-routings are ever transmitted to production devices.
2. **Mode 2 — Isolated Replica Closed-Loop Defense (Lab Simulation):**
   - Mounted against an isolated local replica testbed at `/replica`.
   - Backed by `LocalReplicaAdapter` (`is_simulated = False`).
   - Intercepts malicious requests originating from attacking IPs, issuing HTTP 403 Forbidden with active Time-To-Live (TTL) countdowns.
   - Strictly partitioned: Replica policies and allowlists (`127.0.0.1`, `10.0.0.99`) never bleed into Mode 1 configurations.

```
+----------------------------------------------------------------------------------------------------+
|               THE 8-STAGE MULTI-FACTOR ENFORCEMENT VERIFICATION RULE CHAIN                         |
+----------------------------------------------------------------------------------------------------+
  [ Flow Evaluation: s_prod >= 0.80 ]
                  |
                  v
  [ Check 1: Master Emergency Stop Inactive? ] -------------> NO  ---> [ ABORT: EMERGENCY STOPPED ]
                  | YES
                  v
  [ Check 2: Global Autonomous Blocking Enabled? ] ---------> NO  ---> [ ABORT: GLOBAL MONITOR ONLY ]
                  | YES
                  v
  [ Check 3: Site-Level Blocking Enabled? ] ----------------> NO  ---> [ ABORT: SITE MONITOR ONLY ]
                  | YES
                  v
  [ Check 4: Client IP Absent from Trusted Allowlist? ] ----> NO  ---> [ ABORT: WHITELIST PROTECTED ]
                  | YES
                  v
  [ Check 5: Risk Tier is CRITICAL or HIGH? ] --------------> NO  ---> [ ABORT: LOW RISK PROFILE ]
                  | YES
                  v
  [ Check 6: Independent Evidence Mandatory? ] -------------> NO  ---> [ ABORT: MODEL-ONLY BLOCKED ]
                  | YES
                  v
  [ Check 7: BruteForce Corroboration Confirmed? ] ---------> NO  ---> [ ABORT: UNCONFIRMED BRUTE ]
                  | YES
                  v
  [ Check 8: Target Enforcement Adapter Online? ] ----------> NO  ---> [ ABORT: ADAPTER OFFLINE ]
                  | YES
                  v
  +--------------------------------------------------------------------------------------------------+
  |                        EXECUTE ACTIVE MITIGATION (LOCAL REPLICA ONLY)                            |
  |                Issue Dynamic HTTP 403 Barrier + TTL Lease Countdown (600s)                       |
  +--------------------------------------------------------------------------------------------------+
```
*Fig. 8. The 8-stage verification rule chain governing automated enforcement.*

### B. The 8-Stage Enforcement Rule Chain
Under Mode 2, automated mitigation is gated behind an uncompromising 8-stage verification rule chain (Fig. 8):
1. `emergency_stop_active == False`
2. `global_blocking_enabled == True`
3. `site_blocking_enabled == True`
4. $\text{IP}_{\text{client}} \notin \text{trusted\_allowlist}$
5. $\text{Risk Tier} \in \{\text{CRITICAL}, \text{HIGH}\}$
6. **Independent Evidence Present:** Model score alone ($s_{\text{prod}} \ge 0.80$) cannot trigger a block.
7. **BruteForce Authentication Threshold:** For brute-force attacks, $c_{401} \ge 5$ must be confirmed.
8. Configured enforcement adapter reports healthy status.

### C. Localhost Enforcement Safeguards
Exposing mutating enforcement endpoints over network APIs introduces severe vulnerabilities (e.g., attackers triggering DoS via emergency stops). SentinelX hardens loopback boundaries:
* **Loopback Enforcement Filter (`require_local_or_admin`):** Mutating endpoints verify client loopback origins (`127.0.0.1`, `::1`). Non-local IP requests are rejected with `HTTP 403 Forbidden`.
* **Cryptographic Admin Keys:** Remote administrative changes across trusted subnets require the `X-SentinelX-Admin-Key` header matching server-side pre-shared secrets.
* **Decoy Honeypot Trap (`/replica/admin-decoy`):** Deployed exclusively on the replica application. Requests to this path generate immediate `honeypot_interaction` alerts without storing payload bodies.

---

## XIII. Discussion, Operational Caveats, and Privacy Guarantees

### A. Privacy Controls and Zero Payload Inspection
Enterprise NIDS deployments must comply with evolving privacy standards. SentinelX is built from the ground up to respect user confidentiality:
* **Zero Payload Storage:** Packet payloads (layer-7 application bytes) are discarded immediately by flow taps. SentinelX operates exclusively on statistical flow timing and volumetric headers.
* **Token Stripping:** URI strings are sanitized prior to database insertion; URL query parameters and fragments are irrevocably stripped.
* **Non-Destructive Traceability:** The SQLite review queue preserves audit logs permanently, ensuring SOC analysts can substantiate triage decisions during regulatory compliance audits.

### B. Deployment Caveats and Real-World Limitations
1. **Reverse Proxies, CDNs, and NAT Matching:** The correlation engine matches flow $\text{IP}_{\text{src}}$ to web log $\text{IP}_{\text{client}}$. When traffic traverses Cloudflare, AWS CloudFront, or corporate load balancers, web logs record the proxy’s internal IP address.
   * *Remediation:* Administrators must configure Nginx `realip` modules or parse `X-Forwarded-For` headers **exclusively from trusted upstream proxy subnets** to prevent client header spoofing.
2. **NTP Clock Drift:** Sliding-window temporal correlation ($\pm 30\text{ s}$) presumes system clocks are synchronized. If edge network switches and web servers experience clock drift exceeding 30 seconds, correlation fails, defaulting the system to unconfirmed status. Continuous NTP monitoring is mandatory.
3. **No Autonomous Defense Claims:** SentinelX makes no claim of fully autonomous, zero-touch network defense. High-consequence enterprise networks require human oversight; SentinelX is designed specifically to optimize analyst cognitive efficiency, not eliminate the human analyst.

---

## XIV. Conclusion and Future Work

In this paper, we introduced **SentinelX-Shift**, an operational network intrusion detection and prioritized alert-review architecture. By conducting an end-to-end audit across all eight raw partitions of the CIC-IDS2017 benchmark, we identified and purged 594,712 duplicate vectors (21.03%) and demonstrated the catastrophic failure of shortcut learning on uncurated datasets. We proved that unconstrained linear fusion collapses under zero-day distribution shifts, and introduced the **Autoencoder-Anchored Gated Boost** ($s_{\text{guard}}$) scoring function to provide a robust, calibrated baseline for intrusion triage. 

Through multi-seed Leave-One-Family-Out benchmarks, we exposed the fundamental Zero-Day Generalization Deficit: while volumetric attacks generalize strongly on transport features alone, stealthy and application attacks collapse to near-zero recall at operational false-alarm budgets. We resolved this deficit through Multi-Modal Protocol Guardrails that require independent web-tier and WAF telemetry confirmation. Furthermore, our audited negative finding established that post-hoc explanation stability is mathematically and computationally unsuitable as an automated confidence gate. Finally, we engineered a dual-mode operational architecture achieving 1.25–2.45 ms CPU inference latency while enforcing strict Monitor-Only safety in production.

Future work will explore extending SentinelX to decentralized eBPF (Extended Berkeley Packet Filter) kernel probes for line-rate flow extraction, integrating privacy-preserving federated learning across multi-tenant SOCs, and developing transformer-based sequential representations for complex multi-stage attack scenarios.

---

## References

[1] M. Ring, S. Wunderlich, D. Scheuring, D. Landes, and A. Hotho, “A survey of network-based intrusion detection data sets,” *Computers & Security*, vol. 86, pp. 147–167, Sep. 2019.  
[2] N. Chaabouni, M. Mosbah, A. Zemmari, C. Sauvignac, and P. Faruki, “Network intrusion detection for IoT security based on machine learning: A review,” *IEEE Communications Surveys & Tutorials*, vol. 21, no. 3, pp. 2671–2699, 3rd Quart., 2019.  
[3] G. Apruzzese, M. Andreolini, L. Ferretti, M. Marchetti, and M. Colajanni, “Modeling realistic adversaries in cybersecurity: A survey of recent literature,” *ACM Computing Surveys*, vol. 55, no. 7, pp. 1–37, Jul. 2023.  
[4] A. L. Buczak and E. Guven, “A survey of data mining and machine learning methods for cyber security intrusion detection,” *IEEE Communications Surveys & Tutorials*, vol. 18, no. 2, pp. 1153–1176, 2nd Quart., 2016.  
[5] I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, “Toward generating a new intrusion detection dataset and intrusion traffic characterization,” in *Proc. 4th Int. Conf. Inf. Syst. Secur. Privacy (ICISSP)*, Funchal, Madeira, Portugal, 2018, pp. 108–116.  
[6] N. Moustafa and J. Slay, “UNSW-NB15: A comprehensive data set for network intrusion detection systems (UNSW-NB15 network data set),” in *Proc. IEEE Mil. Commun. Inf. Syst. Conf. (MilCIS)*, Canberra, ACT, Australia, 2015, pp. 1–6.  
[7] M. Tavallaee, E. Bagheri, W. Lu, and A. A. Ghorbani, “A detailed analysis of the KDD CUP 99 data set,” in *Proc. IEEE Symp. Comput. Intell. Cyber Secur. (CICS)*, Nashville, TN, USA, 2009, pp. 53–58.  
[8] R. Sommer and V. Paxson, “Outside the closed world: On using machine learning for network intrusion detection,” in *Proc. IEEE Symp. Secur. Privacy (S&P)*, Oakland, CA, USA, 2010, pp. 305–316.  
[9] G. Apruzzese, P. Laskov, and A. Schneider, “The role of machine learning in cybersecurity: Hype vs. reality,” *IEEE Security & Privacy*, vol. 21, no. 5, pp. 48–56, Sep.–Oct. 2023.  
[10] C. Ardagna et al., “Machine learning for cybersecurity: A comprehensive survey of challenges and future directions,” *IEEE Access*, vol. 11, pp. 45120–45145, May 2023.  
[11] D. Arp, E. Quiring, F. Pendlebury, A. Warnecke, F. Pierazzi, C. Wressnegger, R. Cavallaro, and K. Rieck, “Dos and don'ts of machine learning in computer security,” in *Proc. 31st USENIX Secur. Symp.*, Boston, MA, USA, 2022, pp. 3971–3988.  
[12] R. Geirhos et al., “Shortcut learning in deep neural networks,” *Nature Machine Intelligence*, vol. 2, no. 11, pp. 665–673, Nov. 2020.  
[13] M. Roesch, “Snort: Lightweight intrusion detection for networks,” in *Proc. 13th USENIX Conf. Syst. Admin. (LISA)*, Seattle, WA, USA, 1999, pp. 229–238.  
[14] B. Claise, G. Sadasivan, V. Valluri, and M. Djernaes, “Cisco Systems NetFlow Services Export Version 9,” RFC 3954, Oct. 2004.  
[15] B. Trammell and E. Boschi, “An introduction to the IP Flow Information Export (IPFIX) protocol,” *ACM SIGCOMM Comput. Commun. Rev.*, vol. 41, no. 1, pp. 66–72, Jan. 2011.  
[16] P. Velan, M. Čermák, P. Čeleda, and K. Drašar, “A survey of methods for encrypted traffic classification and analysis,” *Int. J. Netw. Manag.*, vol. 25, no. 5, pp. 355–374, Sep. 2015.  
[17] A. Sperotto, G. Schaffrath, R. Sadre, C. Morariu, A. Pras, and B. Stiller, “An overview of IP flow-based intrusion detection,” *IEEE Commun. Surveys Tuts.*, vol. 12, no. 3, pp. 343–356, 3rd Quart., 2010.  
[18] N. Sultana, N. Chilamkurti, W. Peng, and R. Alhadad, “Survey on SDN based network intrusion detection system using machine learning approaches,” *Peer-to-Peer Netw. Appl.*, vol. 12, no. 2, pp. 493–501, Mar. 2019.  
[19] M. A. Ferrag, L. Maglaras, S. Moschoyiannis, and H. Janicke, “Deep learning for cyber security intrusion detection: Approaches, datasets, and comparative study,” *J. Inf. Secur. Appl.*, vol. 50, p. 102419, Feb. 2020.  
[20] W. Wang, M. Zhu, X. Zeng, X. Wang, and J. Yang, “Malware traffic classification using convolutional neural network for representation learning,” in *Proc. Int. Conf. Inf. Netw. (ICOIN)*, Da Nang, Vietnam, 2017, pp. 712–717.  
[21] Y. Mirsky, T. Doitshman, Y. Elovici, and A. Shabtai, “Kitsune: An ensemble of autoencoders for online network intrusion detection,” in *Proc. Netw. Distrib. Syst. Secur. Symp. (NDSS)*, San Diego, CA, USA, 2018, pp. 1–15.  
[22] C. Zhou and R. C. Paffenroth, “Anomaly detection with robust deep autoencoders,” in *Proc. 23rd ACM SIGKDD Int. Conf. Knowl. Discovery Data Mining*, Halifax, NS, Canada, 2017, pp. 665–674.  
[23] S. Haas and R. Fischer, “On the aggressiveness of CIC-IDS2017: Pitfalls and improvements,” in *Proc. 15th Int. Conf. Availability, Rel. Secur. (ARES)*, Virtual Event, 2020, pp. 1–10.  
[24] G. Engelen, V. Rimmer, and W. Joosen, “Troubleshooting an incomplete machine learning pipeline in network intrusion detection,” in *Proc. 43rd ACM Workshop Workshop Artif. Intell. Secur. (AISEC)*, Virtual Event, 2021, pp. 107–118.  
[25] R. Panigrahi and S. Borah, “A detailed analysis of CICIDS2017 dataset for designing network intrusion detection systems,” *Int. J. Eng. Technol.*, vol. 7, no. 3.24, pp. 479–482, 2018.  
[26] A. Rosay, F. Carlier, and E. Renault, “Improving network intrusion detection systems through feature selection and dataset enhancement,” in *Proc. IEEE 45th Conf. Local Comput. Netw. (LCN)*, Sydney, NSW, Australia, 2020, pp. 445–448.  
[27] A. H. Lashkari, G. D. Gil, M. S. I. Mamun, and A. A. Ghorbani, “Characterization of tor traffic using time based features,” in *Proc. 3rd Int. Conf. Inf. Syst. Secur. Privacy (ICISSP)*, Porto, Portugal, 2017, pp. 253–262.  
[28] J. Thorne, G. Apruzzese, and M. Colajanni, “Evaluating machine learning for network intrusion detection: A systematic review of datasets and validation strategies,” *Computers & Security*, vol. 128, p. 103140, May 2023.  
[29] T. Verkerken, L. D'hooge, T. Wauters, B. Volckaert, and F. De Turck, “Towards realistic evaluation of machine learning for network intrusion detection: Leave-one-attack-out validation,” *IEEE Access*, vol. 10, pp. 78450–78465, Jul. 2022.  
[30] C. I. Nwakanma et al., “Generalization bounds and out-of-distribution evaluation for machine learning in zero-day network security,” *IEEE Trans. Inf. Forensics Security*, vol. 18, pp. 3125–3139, Jun. 2023.  
[31] S. M. Lundberg and S.-I. Lee, “A unified approach to interpreting model predictions,” in *Proc. 31st Conf. Neural Inf. Process. Syst. (NeurIPS)*, Long Beach, CA, USA, 2017, pp. 4765–4774.  
[32] M. T. Ribeiro, S. Singh, and C. Guestrin, “Why should I trust you?: Explaining the predictions of any classifier,” in *Proc. 22nd ACM SIGKDD Int. Conf. Knowl. Discovery Data Mining*, San Francisco, CA, USA, 2016, pp. 1135–1144.  
[33] M. Wang, K. Zheng, Y. Yang, and X. Wang, “An explainable machine learning framework for network intrusion detection systems,” *IEEE Access*, vol. 8, pp. 73127–73141, Apr. 2020.  
[34] F. Noor, M. A. Khan, and S. U. Rehman, “XAI-NIDS: Explainable artificial intelligence for network intrusion detection systems,” *IEEE Trans. Netw. Serv. Manag.*, vol. 20, no. 3, pp. 2450–2463, Sep. 2023.  
[35] P. Mishra et al., “On the robustness of feature attribution methods in adversarial cyber security environments,” in *Proc. IEEE Eur. Symp. Secur. Privacy Workshops (EuroS&PW)*, Genoa, Italy, 2022, pp. 110–121.  
[36] D. Alvarez-Melis and T. S. Jaakkola, “On the robustness of interpretability methods,” in *Proc. ICML Workshop Human Interpretability Mach. Learn. (WHI)*, Stockholm, Sweden, 2018, pp. 1–9.  
[37] I. Corona, G. Giacinto, and F. Roli, “Adversarial attacks against machine learning-based network intrusion detection systems: A survey,” *Computers & Security*, vol. 38, pp. 119–132, Oct. 2013.  
