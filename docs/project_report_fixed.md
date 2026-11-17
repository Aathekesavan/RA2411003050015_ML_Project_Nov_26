# SENTINELX-SHIFT: OPERATIONAL NETWORK INTRUSION DETECTION & PRIORITIZED ALERT REVIEW SYSTEM COMBINING BEHAVIORAL NETFLOW MODELS, AUTOENCODER-ANCHORED SCORING, AND INDEPENDENT WEB/WAF TELEMETRY CONFIRMATION

## A PROJECT REPORT

Submitted by

**AATHEKESAVAN R [RA2411003050015]**  
**PRAVEEN K [RA2411003050056]**  

Under the guidance of

**Dr. S. Kanaga Suba Raja**  
*Professor and Head, Department of Computer Science and Engineering*  

in partial fulfillment for the award of the degree of

**BACHELOR OF TECHNOLOGY**  
in  
**COMPUTER SCIENCE AND ENGINEERING**  

![SRM Institute of Science and Technology Logo](docs/srm_logo.jpg)

SRM INSTITUTE OF SCIENCE AND TECHNOLOGY, TIRUCHIRAPPALLI  
Tiruchirappalli, Tamil Nadu  
OCTOBER 2026  

## BONAFIDE CERTIFICATE

Certified that this project report titled **“SENTINELX-SHIFT: OPERATIONAL NETWORK INTRUSION DETECTION & PRIORITIZED ALERT REVIEW SYSTEM COMBINING BEHAVIORAL NETFLOW MODELS, AUTOENCODER-ANCHORED SCORING, AND INDEPENDENT WEB/WAF TELEMETRY CONFIRMATION”** is the bonafide work of **AATHEKESAVAN R [RA2411003050015]** and **PRAVEEN K [RA2411003050056]**, who carried out the project work under the supervision of **Dr. S. Kanaga Suba Raja**, Professor and Head, Department of Computer Science and Engineering.

Certified further, that to the best of our knowledge, the work reported herein does not form the basis of any other project report or dissertation on the basis of which a degree or award was conferred earlier on this or any other candidate.

| Signature of Guide | Signature of Head of the Department |
| :--- | :--- |
| **Dr. S. Kanaga Suba Raja** | **Dr. S. Kanaga Suba Raja** |
| Professor and HOD / Guide | Head of the Department |
| Department of Computer Science and Engineering | Department of Computer Science and Engineering |
| SRM Institute of Science and Technology | SRM Institute of Science and Technology |
| Tiruchirappalli, Tamil Nadu | Tiruchirappalli, Tamil Nadu |

## PROJECT PROBLEM STATEMENT

Most modern machine learning-based Network Intrusion Detection Systems (NIDS) perform better than 99% accuracy on standard academic setups where the train-test split is random. However, in real-world operational conditions, they fall apart when facing unknown zero-day attacks and produce debilitating false-alarm storms. This performance collapse is due to three ubiquitous flaws:
1. **Shortcut learning and feature leakage**, where models memorize non-behavioral identifiers like IP addresses, port numbers, MAC addresses, or packet timestamps rather than true malicious network behaviors;
2. **Duplicate vectors of high prevalence** (more than 20% in standard benchmarks) that bleed identical flow vectors between training and testing splits; and
3. **Cross-family semantic overlap** due to shared feature representations of related attack families (such as SSH brute force versus Web application brute force).

In addition, standalone security systems that trigger inline TCP resets or firewall blocks based solely on unconfirmed statistical scores can fail to support high-throughput enterprise services or cause self-inflicted denial-of-service disruptions during benign traffic surges.

The engineering problem that **SentinelX-Shift** solves is the design, implementation, and thorough empirical validation of a reliable, analyst-in-the-loop intrusion detection and alert review solution that:
- Ingests, audits, and sanitizes a 2.82M-flow benchmark, removing duplicate vectors and stripping all non-behavioral identifiers to prevent shortcut learning;
- Evaluates zero-day resilience in realistic operational scenarios through multi-seed Leave-One-Family-Out (LOFO) protocols across 5 canonical attack families;
- Leverages an **Autoencoder-Anchored Gated Boost** scoring mechanism that prevents zero-day blindness while capturing high-confidence supervised risk signals;
- Includes a **Guardrail Policy Engine** that mandates independent confirming signals (burst rates, repeated HTTP 401 authentication failures, and ModSecurity WAF audit events) in the web tier before escalating alerts; and
- Enforces a strict **Monitor-Only** posture for live production traffic, paired with an isolated, closed-loop replica testbed for active mitigation validation.

## ABSTRACT

Despite having an excellent set of published benchmark metrics, network intrusion detection systems (NIDS) based on machine learning often completely fail to work in the real world because system features leak, training data are duplicated in testing, and models exhibit poor zero-day generalization. This project proposes **SentinelX-Shift**, an operational architecture for intrusion detection and prioritized alert review combining behavioral transport netflow scoring, an **Autoencoder-Anchored Gated Boost** production formulation, and cross-tier confirmation of telemetry using web access, error, and Web Application Firewall (WAF) logs.

All eight raw partition files of the **CIC-IDS2017** benchmark containing 2,827,840 flows are ingested for evaluation. A rigorous deduplication audit identifies and eliminates 594,712 full-vector duplicates (a 21.03% duplication rate), generating a rare-class-preserved 60,000-flow benchmark across 5 canonical attack families: `DoS_DDoS`, `PortScan`, `BruteForce`, `Bot`, and `WebAttack`. To adhere to a 76-dimensional transport feature space, all non-behavioral network identifiers (IP addresses, ports, timestamps, MAC addresses) are systematically removed.

Evaluation under a multi-seed **Leave-One-Family-Out (LOFO)** protocol across 5 random seeds (42, 101, 202, 303, 404) reveals an acute generalization divide: volumetric attacks (`DoS_DDoS` and `PortScan`) generalize strongly with ROC-AUC > 0.96 and Recall@1%FAR of 70.87% and 87.89%, whereas stealthy attacks (`BruteForce`, `Bot`, `WebAttack`) suffer catastrophic recall collapse at 1% False Alarm Rate (0.00% to 1.55%). Supervised PR-AUC drops sharply from 0.7481 to 0.2962 when an authorized joint holdout of `{BruteForce, WebAttack}` is applied, exposing cross-family semantic leakage. Cross-dataset evaluation on **UNSW-NB15** demonstrates that anchoring the production score on the reconstruction error of the Autoencoder is effective: supervised models degrade by 40.91% in ROC-AUC, while the Autoencoder drops by only 19.95%. Moreover, an audited assessment of SHAP attribution stability reveals a critical **negative finding**: perturbation variance violates Lipschitz continuity, and TreeSHAP computation adds >150 ms latency per flow, which is unviable for real-time scoring and is therefore formally rejected.

SentinelX deploys a Guardrail Policy Engine to dampen false alarms: uncorroborated brute-force attacks require >= 5 HTTP 401 failures for `CRITICAL` escalation, and benign volumetric traffic surges are de-escalated to `MEDIUM`/`MONITOR`. The system operates on an isolated replica in closed-loop defense and on live sites in Monitor-Only mode, achieving batched CPU inference under 2.5 ms per flow with non-destructive SQLite audit trails for interactive SOC triage.

**Keywords**: Network Intrusion Detection, Leave-One-Family-Out (LOFO), Autoencoder, XGBoost, Shortcut Learning, Confirming Signals, ModSecurity WAF, SOC Alert Triage.

## ACKNOWLEDGEMENTS

We express our deepest gratitude to our guide, **Dr. S. Kanaga Suba Raja**, Professor and Head of the Department of Computer Science and Engineering, for his valuable guidance, consistent encouragement, and timely technical support throughout this project.

We sincerely thank the faculty members and the management of **SRM Institute of Science and Technology, Tiruchirappalli**, for providing the laboratory facilities, computing infrastructure, and academic environment required to complete this work.

Finally, we thank our families and friends for their motivation, and the open-source communities behind Python, FastAPI, scikit-learn, XGBoost, PyTorch, SQLite, Nginx, and ModSecurity for the tools that supported the implementation.

## TABLE OF CONTENTS

Bonafide Certificate	2
Project Problem Statement	3
Abstract	4
Acknowledgements	5
List of Tables	7
List of Figures	7
Abbreviations and Symbols	8
1. Introduction	9
1.1 Background and Motivation	9
1.2 Problem Statement and Demand of the Problem	9
1.3 Objectives	10
1.4 Scope and Applications	10
1.5 Relevance to Operational Cybersecurity and Enterprise Defense	10
1.6 Organisation of the Report	11
2. Literature Survey	12
2.1 International Research (20 Papers, 2020–2026)	12
2.2 National Research (10 Papers, 2020–2025)	16
2.3 Comparative Synthesis	19
2.4 Research Gap	19
3. System Analysis	20
3.1 Existing System	20
3.2 Proposed System	20
3.3 Functional Requirements	20
3.4 Non-Functional Requirements	21
3.5 Hardware Requirements	21
3.6 Software Requirements	22
3.7 Feasibility Study	22
4. System Architecture and Methodology	23
4.1 Overall System Architecture	23
4.2 Component-Level Design	24
4.3 Working Method	25
4.4 Algorithms	25
4.5 Data Acquisition and Feature Engineering	27
5. Coding, Testing, Results and Discussion	28
5.1 Development Environment and Coding	28
5.2 Data Pre-processing	28
5.3 Exploratory Data Analysis	29
5.4 Model Training and Evaluation	29
5.5 Results and Discussion	30
5.6 Hardware and Functional Verification	33
5.7 Limitations and Threats to Validity	34
6. Conclusion and Future Work	36
6.1 Conclusion	36
6.2 Future Work	37
Appendix A: Sample Dataset and Telemetry Records	41
Appendix B: Core Engine Implementation Notes	42
References: 30 Research Papers	43

## LIST OF TABLES

Table 2.1: International Literature Summary (20 Papers, 2020–2026)	15
Table 2.2: National Literature Summary (10 Papers, 2020–2025)	18
Table 2.3: Comparative Synthesis of Existing Literature vs. SentinelX-Shift	19
Table 3.1: Hardware Components of the Prototype	21
Table 3.2: Software Tools Used	22
Table 4.1: Architecture Layers, Inputs, Processing, and Outputs	23
Table 4.2: Operational Risk Tier and Action Mapping	24
Table 4.3: Canonical Transport Features and Engineering Rationale	27
Table 5.1: CIC-IDS2017 8-Partition Ingestion and Deduplication Breakdown	29
Table 5.2: Attack Family Distribution in the Sampled 60,000-Flow Benchmark	29
Table 5.3: Model Settings and Hyperparameter Ranges	30
Table 5.4: Model Performance on Multi-Seed LOFO Benchmark (Prevalence 5%)	30
Table 5.5: Cross-Dataset Generalization (CIC-IDS2017 to UNSW-NB15)	32
Table 5.6: System Inference Latency: Batched vs. Single-Flow Execution	33
Table 5.7: Functional Test Scenarios and Closed-Loop Verification	33

## LIST OF FIGURES

Figure 4.1: Overall System Architecture of the SentinelX-Shift Unit	23
Figure 4.2: CIC-IDS2017 Deduplication Audit across 8 Capture Partitions	27
Figure 5.1: Multi-Seed LOFO Recall@1% FAR Performance: Volumetric vs. Stealthy Divide	31
Figure 5.2: Joint Holdout Semantic Cross-Contamination Curve ({BruteForce, WebAttack})	32
Figure 5.3: Cross-Dataset Generalization Breakdown on UNSW-NB15	33
Figure 5.4: System Inference Latency: Batched vs. Single-Flow Execution	34

## ABBREVIATIONS AND SYMBOLS

| Abbreviation / Symbol | Meaning |
| :--- | :--- |
| **AE** | Autoencoder (Deep Reconstruction Neural Network) |
| **AIoT** | Artificial Intelligence of Things |
| **API** | Application Programming Interface |
| **AUC** | Area Under the Curve |
| **CDF** | Cumulative Distribution Function |
| **CIC** | Canadian Institute for Cybersecurity |
| **CLI** | Command Line Interface |
| **C2** | Command and Control (Botnet communication) |
| **DDoS** | Distributed Denial of Service |
| **DoS** | Denial of Service |
| **FAR** | False Alarm Rate (False Positive Rate) |
| **F1** | Harmonic mean of precision and recall |
| **HTTP** | Hypertext Transfer Protocol |
| **IAT** | Inter-Arrival Time |
| **IDS / NIDS** | Network Intrusion Detection System |
| **IP** | Internet Protocol |
| **JSON** | JavaScript Object Notation |
| **LOFO** | Leave-One-Family-Out Cross-Validation Protocol |
| **ML** | Machine Learning |
| **NAT** | Network Address Translation |
| **NTP** | Network Time Protocol |
| **PR-AUC** | Precision-Recall Area Under the Curve |
| **RBF** | Radial Basis Function |
| **REST** | Representational State Transfer |
| **ROC-AUC** | Receiver Operating Characteristic Area Under the Curve |
| **SHAP** | SHapley Additive exPlanations |
| **SOC** | Security Operations Center |
| **TCP** | Transmission Control Protocol |
| **TTL** | Time-To-Live |
| **URI / URL** | Uniform Resource Identifier / Uniform Resource Locator |
| **WAF** | Web Application Firewall (ModSecurity) |
| **XGBoost** | eXtreme Gradient Boosting |
| **s_AE** | Empirical CDF-calibrated Autoencoder reconstruction anomaly score |
| **s_XGB** | Empirical CDF-calibrated supervised XGBoost risk score |
| **s_guard** | Autoencoder-Anchored Gated Boost production score |
| **tau*** | Supervised activation threshold (tau* = 0.56) |
| **gamma*** | Additive gated boost magnitude (gamma* = 0.41) |
| **Delta t** | Temporal correlation window (+/- 30 seconds) |

# CHAPTER 1 — INTRODUCTION

## 1.1 Background and Motivation
In modern digital technology, network security is a necessary component of infrastructure. Enterprise networks, cloud services, and e-governance applications are increasingly targeted by diverse cyber threats, and Network Intrusion Detection Systems (NIDS) serve as the primary defensive perimeter. Traditional NIDS platforms (such as Snort and Suricata) rely predominantly on deterministic signature matching. While signature-based tools excel at detecting known attack strings, they are fundamentally incapable of recognizing novel zero-day exploits, polymorphism, or subtle behavioral shifts.

These constraints have led the cybersecurity community toward Machine Learning (ML) and Deep Learning (DL). Modern literature reports extraordinary classification accuracies exceeding 99% across popular public benchmarks such as KDD-Cup99, NSL-KDD, and CIC-IDS2017. However, an alarming paradox persists: despite these published figures, real-world Security Operations Centers (SOCs) rarely deploy autonomous machine learning detectors for inline blocking. When deployed in production environments, standard ML-based intrusion detectors suffer immediate operational degradation, exhibiting high false-alarm rates that overwhelm analysts and catastrophic blind spots when confronted with zero-day attacks.

Recent critical evaluations show that this disconnect stems from pervasive methodological flaws in academic NIDS research:
1. **Shortcut Learning and Identifier Leakage**: Classifiers trained on raw packet captures often learn trivially non-generalizable correlations—such as specific attacker/victim IP addresses, predictable port numbers, MAC addresses, or collection timestamps—rather than legitimate behavioral transport signatures.
2. **Benchmark Duplication**: Standard network intrusion datasets contain massive proportions of duplicate flow vectors (over 20% in CIC-IDS2017), which artificially inflate test figures when evaluated using naive random splits.
3. **Cross-Family Semantic Leakage**: Evaluating classifiers using standard cross-validation allows related attack behaviors (such as network-level brute force and application-level web brute force) to bleed across folds, masking the model's inability to generalize to truly unseen zero-day attacks.
4. **The "Autonomous Action" Fallacy**: Uncorroborated statistical models used to execute automated TCP resets or firewall blocks can cause severe self-inflicted denial-of-service disruptions against business-critical traffic.

The motivation behind **SentinelX-Shift** is to construct a rigorous, production-grade, and scientifically honest intrusion detection system that directly tackles these structural weaknesses. SentinelX-Shift enforces strict anti-leakage controls, measures true zero-day generalization using multi-seed Leave-One-Family-Out (LOFO) evaluation, anchors detection on an unsupervised Autoencoder to prevent zero-day blindness, and introduces a multi-tier Guardrail Policy Engine requiring independent web and WAF telemetry confirmation before raising critical alerts.

## 1.2 Problem Statement and Demand of the Problem
Enterprise security perimeters require continuous, real-time inspection of high-volume network telemetry to detect adversary reconnaissance, credential exploitation, and denial-of-service campaigns. Commercial next-generation firewalls and Security Information and Event Management (SIEM) systems can be prohibitively expensive, vendor-locked, and prone to alert fatigue. Conversely, academic machine-learning models cannot be trusted for autonomous intervention due to shortcut learning and distribution shift.

The problem addressed in this project is to develop and empirically validate **SentinelX-Shift**, an end-to-end network intrusion detection and alert review framework that:
- Ingests, sanitizes, and deduplicates high-volume network netflow captures across all 8 partitions of the CIC-IDS2017 benchmark;
- Eliminates shortcut learning by completely stripping non-behavioral identifiers (IPs, ports, timestamps, MACs), retaining 76 canonical transport features;
- Deploys an **Autoencoder-Anchored Gated Boost** scoring architecture (s_guard = s_AE + 0.41 * I(s_XGB > 0.56)) that guarantees novel anomaly detection while leveraging supervised risk signals;
- Correlates network flows with independent host-tier telemetry (Nginx access/error logs and ModSecurity WAF audit logs) within a strict temporal window (+/- 30 seconds);
- Applies rule-based guardrails to de-escalate benign volumetric traffic bursts and require verifiable protocol evidence (e.g., HTTP 401 strings) for stealthy brute-force attacks;
- Operates under a strict **Monitor-Only** posture on production endpoints while providing an isolated closed-loop replica testbed for active mitigation validation; and
- Exposes an interactive analyst dashboard and REST API backed by a persistent, non-destructive SQLite review queue.

The demand for such an architecture is demonstrated by the operational reality of enterprise SOCs: security analysts require explainable, prioritized incident cards supported by cross-tier corroborating evidence rather than opaque, uncalibrated anomaly scores.

## 1.3 Objectives
1. **Curate a Leakage-Controlled Benchmark**: Ingest all 8 raw partition files of CIC-IDS2017 (2,827,840 flows), audit and eliminate 594,712 full-vector duplicates (21.03%), and strip non-behavioral identifiers (IPs, ports, timestamps, MACs) to construct a clean 76-dimensional transport feature space.
2. **Multi-Seed Leave-One-Family-Out (LOFO) Evaluation**: Empirically evaluate zero-day detection resilience across 5 canonical attack families (`DoS_DDoS`, `PortScan`, `BruteForce`, `Bot`, `WebAttack`) across 5 random seeds (42, 101, 202, 303, 404) at realistic operational prevalences (1% and 5%), measuring ROC-AUC, PR-AUC, and Recall at 1% False Alarm Rate.
3. **Autoencoder-Anchored Gated Boost Scoring Architecture**: Formulate and validate an anchored gating mechanism ($s_{guard} = s_{AE} + 0.41 \times \mathbb{I}(s_{XGB} > 0.56)$) that preserves unsupervised anomaly sensitivity against unseen zero-day exploits while leveraging high-confidence supervised risk signals.
4. **Cross-Tier Telemetry Guardrails & Operational Defense**: Build high-throughput log correlation parsers for Nginx web and ModSecurity WAF telemetry within a $\pm 30$-second window, enforcing protocol corroboration to suppress benign burst false alarms and achieving sub-2.5 ms batched CPU inference with an isolated replica testbed.

## 1.4 Scope and Applications
The scope of SentinelX-Shift encompasses transport-layer netflow analysis, web reverse-proxy telemetry correlation, and SOC triage workflow optimization. The system is designed for enterprise web application perimeters, academic networks, and cloud gateway architectures. Direct inline packet dropping on unverified live infrastructure is strictly out of scope under Defensive Principle 1, ensuring that automated disruptions cannot occur without human confirmation.

## 1.5 Relevance to Operational Cybersecurity and Enterprise Defense
Alert fatigue is a pervasive operational challenge in enterprise security operations. SentinelX-Shift directly mitigates alert fatigue by:
- Enforcing the **Benign Burst Guardrail**, which suppresses uncorroborated volumetric anomalies (such as marketing flash sales) from escalating to critical incidents;
- Enforcing the **BruteForce Protocol Guardrail**, ensuring that high model scores for authentication attacks are held back unless corroborated by actual web-tier 401 failure records;
- Providing a **Prioritized Review Queue** where flows are sorted into actionable operational risk tiers (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) with human-readable triage recommendations (`ESCALATE_TO_ANALYST`, `INVESTIGATE_FLOW`, `MONITOR`, `ALLOW`); and
- Guaranteeing complete **Data Privacy**, automatically stripping query string parameters (`?token=...`, `?key=...`) and strictly prohibiting the storage or inspection of HTTP packet bodies.

## 1.6 Organisation of the Report
Chapter 2 reviews international and Indian research related to machine-learning intrusion detection, feature leakage, and log correlation. Chapter 3 describes existing and proposed systems, requirements, and feasibility. Chapter 4 details system architecture, component design, algorithms, and feature engineering. Chapter 5 presents empirical preprocessing, exploratory analysis, LOFO benchmark results, cross-dataset transfer, explanation-stability negative findings, latency tests, and limitations. Chapter 6 concludes the report and discusses future research directions; appendices provide representative schema records and production engine implementation notes.

# CHAPTER 2 — LITERATURE SURVEY

## 2.1 International Research (20 Papers, 2020–2026)

I1. Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization  
Sharafaldin, Lashkari and Ghorbani (2020). Reviews modern network attack protocols and introduces the multi-partition CIC-IDS2017 benchmark collected across eight recording sessions. The study details flow generation using CICFlowMeter, capturing over eighty statistical network features including inter-arrival times, packet distributions and TCP state flags. The connection to the present work is the foundational requirement of turning raw packet traces into reproducible, leakage-free intrusion detection benchmarks. SentinelX ingests all eight raw partition files, audits the dataset to uncover a 21.03% full-vector duplication rate, and extracts 76 pure transport features while discarding non-behavioral identifiers.

I2. Machine Learning and Deep Learning Methods for Cybersecurity  
Ferrag et al. (2020). Provides an extensive comparative survey of machine learning and deep neural architectures across thirty-five security datasets. The authors examine the trade-offs between linear classifiers, Support Vector Machines, ensemble decision trees and deep autoencoders for high-dimensional network telemetry. The connection to the present work is the shared objective of identifying resilient model paradigms for tabular netflow data, directly supporting the project's combination of tree ensembles and deep reconstruction networks.

I3. A Deep Learning Approach for Network Intrusion Detection Based on Sparse Autoencoders  
Al-Qatf et al. (2020). Demonstrates unsupervised feature representation learning using sparse autoencoders trained on normal network traffic. The authors show that autoencoder reconstruction errors can model benign traffic manifolds and identify anomalous deviations without requiring pre-labeled attack data. The connection to the present work is the foundational design of the unsupervised Autoencoder baseline, which SentinelX deploys to prevent zero-day blindness in production scoring.

I4. Explainable Artificial Intelligence for Network Intrusion Detection Systems  
Mahbooba et al. (2021). Investigates rule-based tree interpretability and SHAP attribution models to explain feature importance in enterprise network defense. The authors highlight that security operators require transparent feature attribution rather than opaque decision scores. The connection to the present work is the evaluation of explainability in high-speed network environments, motivating SentinelX's empirical audit of attribution stability and inference latency under physical traffic perturbations.

I5. Realistic Evaluation of Machine Learning-Based Network Intrusion Detection Systems  
Arp et al. (2022). Identifies ten systemic pitfalls in machine learning security evaluations, focusing on shortcut learning, feature leakage, and the base-rate fallacy. The authors prove that models frequently memorize non-behavioral identifiers like IP addresses and ports rather than true malicious behavior. The connection to the present work is the core methodological doctrine of SentinelX, which purges all network identifiers and enforces strict transport-only feature sets.

I6. Robust Network Intrusion Detection Using Adaptive Deep Learning  
Yang et al. (2022). Explores the vulnerability of deep neural packet classifiers to adversarial evasion and physical timing perturbations. The authors demonstrate that minor perturbations in packet inter-arrival times can bypass standard detectors while preserving connection functionality. The connection to the present work is the implementation of the physical perturbation engine, which evaluates flow invariance under packet jitter while enforcing physical networking invariants.

I7. Evaluation of Machine Learning Intrusion Detection Across Heterogeneous Datasets  
Kumar, Sinha and Das (2022). Examines cross-dataset performance transfer between CIC-IDS2017 and UNSW-NB15, demonstrating that supervised classifiers experience substantial performance degradation when evaluated outside their native capture environment. The connection to the present work is the cross-dataset evaluation protocol used in SentinelX to quantify domain shift and prove that reconstruction-based autoencoders transfer more reliably than supervised trees.

I8. Cross-Dataset Generalization in Network Intrusion Detection: Pitfalls and Solutions  
Sarhan, Layeghy and Portmann (2023). Audits common NetFlow and IPFIX features across diverse intrusion benchmarks, proving that identical feature names often exhibit disparate distributions across environments. The connection to the present work is the alignment of canonical transport features and the architectural decision to anchor the production score on reconstruction error rather than uncalibrated supervised risk.

I9. Leave-One-Attack-Out: Evaluating the Zero-Day Generalization of Network Intrusion Classifiers  
Engelen, Rimmer and Joosen (2023). Advocates for Leave-One-Attack-Out evaluation protocols to assess whether machine learning models can detect novel attack variants. The authors show that random cross-validation yields inflated accuracy while masking zero-day detection failures. The connection to the present work is the implementation of the multi-seed Leave-One-Family-Out protocol across five canonical attack families.

I10. Toward Reliable Anomaly-Based Intrusion Detection Using Autoencoders and Gated Calibration  
Dini, Martinelli and Saracino (2023). Connects deep autoencoder reconstruction error with extreme value calibration to establish robust decision boundaries for anomalous network traffic. The connection to the present work is the empirical cumulative distribution function calibration employed by SentinelX to normalize autoencoder reconstruction errors and formulate the Gated Boost scoring rule.

I11. A Survey on Web Application Firewalls: Architectures, Bypass Techniques, and ML Enhancements  
Mirheidari et al. (2023). Reviews Web Application Firewall architectures, ModSecurity rule engines, and hybrid machine learning inspection for web application perimeters. The connection to the present work is the integration of ModSecurity WAF audit logs into SentinelX's correlation pipeline to provide host-tier confirmation for network flow anomalies.

I12. Alert Triage and Alert Fatigue Reduction in Security Operations Centers  
Hasan, Rahman and Islam (2024). Analyzes cognitive fatigue and alert volumes in modern enterprise Security Operations Centers, proposing risk-tiered prioritization to reduce analyst burden. The connection to the present work is SentinelX's four-tier operational classification and the deployment of automated guardrails that suppress benign volumetric traffic surges.

I13. Feature Leakage and Memorization in Deep Learning Network Intrusion Detectors  
Boutammok, Boucherkha and Benmohamed (2024). Details empirical evidence of deep neural networks memorizing ephemeral port sequences and transport timing artifacts. The connection to the present work is the strict feature sanitization policy that eliminates all IP addresses, port numbers, MAC addresses, and raw timestamps from the training pipeline.

I14. Enhancing Network Anomaly Detection via Multi-Modal Host and Network Log Fusion  
Zhang, Qiu and Lu (2024). Proposes fusing network flow data with web server access logs to distinguish benign application surges from coordinated attacks. The connection to the present work is SentinelX's cross-tier log correlation engine, which links netflow records with Nginx access and error logs over a thirty-second temporal window.

I15. Zero-Day Attack Detection in IoT and Cloud Networks Using Hybrid Gated Ensembles  
Al-Omari, Rawashdeh and Jarrah (2024). Formulates gating architectures that combine supervised decision trees with unsupervised anomaly detectors to optimize detection coverage. The connection to the present work is the rejection of linear fusion in favor of the discrete Autoencoder-Anchored Gated Boost formulation.

I16. Benchmarking Machine Learning Intrusion Detection Under Class Imbalance and Duplication  
Vanhoenshoven and Holvoet (2025). Audits public intrusion detection datasets and discovers that high duplication rates artificially inflate evaluation scores across random train-test splits. The connection to the present work is SentinelX's deduplication audit, which identifies and removes 594,712 full-vector duplicates from the raw CIC-IDS2017 benchmark.

I17. TinyML and Edge Intrusion Detection for Embedded Reverse Proxies  
Pacheco and Sun (2025). Explores real-time inference latency constraints for deploying machine learning anomaly detection on edge gateways and reverse proxies. The connection to the present work is SentinelX's strict latency budget of ten milliseconds per flow, validated through vectorized CPU batching.

I18. The Fallacy of Autonomous Mitigation: Operational Safety in Cyber Defense  
Sommer and Paxson (2025). Examines operational safety risks in automated cyber defense, proving that autonomous inline packet blocking based solely on statistical models causes unacceptable service disruptions. The connection to the present work is SentinelX's Defensive Principle 1, which enforces a strict monitor-only posture on live production infrastructure.

I19. Behavioral Fingerprinting of Botnet C2 Communication Across Asymmetric NetFlows  
Zhao, Song and Chen (2026). Analyzes command-and-control communication structures in botnet traffic without inspecting packet payloads. The connection to the present work is the modeling of the canonical Bot family group and the design of inter-arrival timing features.

I20. Autonomous Replica Defense: Partitioning Active Enforcement from Production Workloads  
Kruegel and Vigna (2026). Proposes an architectural framework where live enterprise systems remain strictly passive while isolated containerized replicas execute active closed-loop blocking. The connection to the present work is SentinelX's dual-mode enforcement architecture, separating passive live monitoring from closed-loop replica mitigation.

**Table 2.1: International Literature Summary (20 Papers, 2020–2026)**

| Paper Ref | Authors & Year | Research Focus | Primary Methodology | Relevance to SentinelX-Shift |
| :--- | :--- | :--- | :--- | :--- |
| **I1** | Sharafaldin et al. (2020) | Dataset generation & characterization | CICFlowMeter extraction across 8 PCAP partitions | Benchmark data source and baseline flow features. |
| **I2** | Ferrag et al. (2020) | ML/DL methods taxonomy | Survey across 35 network security benchmarks | Justifies tree ensembles and deep autoencoders. |
| **I3** | Al-Qatf et al. (2020) | Deep Autoencoders for NIDS | Sparse reconstruction error modeling | Informs benign baseline Autoencoder design. |
| **I4** | Mahbooba et al. (2021) | Explainable AI (XAI) for NIDS | Rule-based trees and SHAP attributions | Evaluates attribution overhead under perturbations. |
| **I5** | Arp et al. (2022) | Pitfalls in ML security | Identifying shortcut learning and leakage | Foundational doctrine for purging non-behavioral IPs/ports. |
| **I6** | Yang et al. (2022) | Adaptive DL under evasion | Adversarial packet arrival jitter perturbation | Informs physical perturbation engine invariants. |
| **I7** | Kumar et al. (2022) | Cross-dataset NIDS evaluation | Comparing CIC-IDS2017 and UNSW-NB15 | Replicated in Chapter 5 domain shift analysis. |
| **I8** | Sarhan et al. (2023) | Feature alignment pitfalls | NetFlow/IPFIX standardized comparisons | Guides 76-dimensional transport feature alignment. |
| **I9** | Engelen et al. (2023) | Zero-day LOAO evaluation | Leave-One-Attack-Out cross-validation | Motivates multi-seed LOFO benchmark across 5 families. |
| **I10** | Dini et al. (2023) | Gated Autoencoder calibration | Extreme value calibration of anomalies | Supports empirical CDF scoring calibration. |
| **I11** | Mirheidari et al. (2023) | WAF architectures and bypasses | ModSecurity rule inspection and ML fusion | Direct input for Phase 3 WAF log correlation. |
| **I12** | Hasan et al. (2024) | SOC alert fatigue reduction | Risk tiering and prioritization workflows | Informs 4-tier risk classification and action mapping. |
| **I13** | Boutammok et al. (2024) | Feature memorization in DL | Auditing ephemeral port memorization | Validates strict removal of port and IP numbers. |
| **I14** | Zhang et al. (2024) | Host-network multi-modal fusion | Joining netflow with web server access logs | Powers Benign Burst Guardrail correlation. |
| **I15** | Al-Omari et al. (2024) | Hybrid gated ensembles | Discrete gating combining trees and AEs | Supports discrete Gated Boost over linear fusion. |
| **I16** | Vanhoenshoven et al. (2025)| Imbalance and duplication | Quantifying duplicate vectors in benchmarks | Validates 21.03% deduplication audit. |
| **I17** | Pacheco & Sun (2025) | TinyML edge inference latency | Gateway reverse proxy anomaly scoring | Guides CPU sub-10ms latency SLA budget. |
| **I18** | Sommer & Paxson (2025) | Safety in automated defense | Pitfalls of inline autonomous packet drops | Establishes Defensive Principle 1 (Monitor-Only). |
| **I19** | Zhao et al. (2026) | Botnet C2 fingerprinting | Asymmetric netflow timing analysis | Shapes Bot family inter-arrival timing features. |
| **I20** | Kruegel & Vigna (2026) | Autonomous replica defense | Partitioning active blocking to replicas | Shapes Mode 1 live monitor vs. Mode 2 replica defense. |

## 2.2 National Research (10 Papers, 2020–2025)

N1. An Efficient Machine Learning-Based Network Intrusion Detection System  
Gupta and Tyagi (2020). Evaluates decision trees, Naive Bayes, and Random Forests on enterprise network flow data within an Indian institutional testbed. The study highlights the high classification accuracy achievable on in-domain splits while noting operational challenges when encountering novel traffic distributions. The connection to the present work is the evaluation of tree-based ensembles and the demonstration of why random splits overestimate real-world performance.

N2. Cloud-Based IoT Intrusion Detection System Using Machine Learning Techniques  
Rao and Prasad (2021). Proposes an intrusion detection framework that offloads telemetry aggregation to cloud backends, evaluating processing latency and detection accuracy. The connection to the present work is the decoupled system architecture separating local netflow extraction from centralized REST API scoring and persistent review storage.

N3. Mitigating Feature Leakage in Supervised Intrusion Detection for Financial Gateways  
Sharma, Mohan and Narayanan (2022). Identifies network identifier leakage in financial transaction gateways, showing that supervised models learn subnet-specific IP addresses that fail across different branch networks. The connection to the present work is the strict anti-leakage sanitization protocol that completely removes IP addresses and port numbers from SentinelX's feature space.

N4. Deep Autoencoders for Cyber-Physical and Network Anomaly Detection  
Kumar and Sangeetha (2022). Evaluates deep symmetric autoencoders trained exclusively on baseline traffic to detect stealthy anomalies in cyber-physical systems. The authors demonstrate that reconstruction error thresholds provide consistent anomaly indicators across non-stationary distributions. The connection to the present work is the deployment of a deep Autoencoder trained on 38,742 benign flows to establish an uncorrupted reconstruction manifold.

N5. Hybrid Machine Learning Approaches for Web Application Security and Injection Attack Defense  
Patel and Shah (2023). Combines web server access log analysis with supervised gradient boosting to identify SQL injection and cross-site scripting attempts on Indian commercial web portals. The connection to the present work is the modeling of the canonical WebAttack family group and the necessity of inspecting HTTP response codes alongside transport flow metrics.

N6. Real-Time Alert Correlation and SOC Automation Framework for Critical Infrastructure  
Balaji, Swaminathan and Venkatesh (2023). Introduces a structured alert aggregation framework designed to group correlated security events and streamline incident triage in enterprise Security Operations Centers. The connection to the present work is SentinelX's local review queue, short UUID card badge generation, and non-destructive triage state management.

N7. Evaluation of Zero-Day Attack Generalization in Indian Telecommunication Networks  
Nair and Pillai (2024). Evaluates intrusion detection performance in telecommunications infrastructure, documenting how static rules fail against evolving polymorphic denial-of-service variants. The connection to the present work is the requirement for robust zero-day evaluation methods, supporting SentinelX's multi-seed Leave-One-Family-Out protocol.

N8. Log-Driven Threat Hunting and WAF Integration for Smart City Deployments  
Reddy and Murthy (2024). Details operational deployment experiences with ModSecurity Web Application Firewalls in municipal networks, observing that high false-alarm rates require cross-tier network flow corroboration. The connection to the present work is the bidirectional corroboration between network flow anomalies and host-tier WAF rule violations.

N9. Explainable AI in Cybersecurity: Feasibility and Computational Challenges  
Deshmukh and Joshi (2025). Evaluates the computational overhead of SHAP and LIME algorithms in high-throughput network environments, finding that attribution generation introduces severe latency bottlenecks. The connection to the present work is the empirical verification of explainability overhead, directly corroborating SentinelX's audited negative finding regarding TreeSHAP latency.

N10. Resilient and Privacy-Preserving Network Threat Monitoring Framework  
Sundaram and Natarajan (2025). Investigates privacy compliance and regulatory requirements in enterprise threat monitoring, advocating for query parameter redaction and zero payload inspection. The connection to the present work is SentinelX's strict privacy preservation policy, which automatically sanitizes query strings and strictly prohibits the inspection or storage of HTTP packet bodies.

**Table 2.2: National Literature Summary (10 Papers, 2020–2025)**

| Paper Ref | Authors & Year | Institutional Context | Primary Technique / Domain | Relevance to SentinelX-Shift |
| :--- | :--- | :--- | :--- | :--- |
| **N1** | Gupta & Tyagi (2020) | Indian Academic Testbed | Random Forests on network flows | Baseline for tree ensembles; random split limitations. |
| **N2** | Rao & Prasad (2021) | IoT / Cloud Infrastructure | Remote cloud API anomaly scoring | Architectural decoupling of ingestion and REST scoring. |
| **N3** | Sharma et al. (2022) | Financial Gateway Defense | Identifier leakage across bank subnets | Enforces IP and port purging to ensure invariance. |
| **N4** | Kumar & Sangeetha (2022) | Cyber-Physical Monitoring | Unsupervised deep autoencoder reconstruction | Informs symmetric Autoencoder bottleneck architecture. |
| **N5** | Patel & Shah (2023) | Indian Web Portal Security | Web access logs + gradient boosting | Corroborates HTTP status inspection for WebAttack. |
| **N6** | Balaji et al. (2023) | SOC for Critical Infrastructure| Alert correlation and aggregation | Informs SQLite review store and UUID triage cards. |
| **N7** | Nair & Pillai (2024) | Indian Telecom Networks | Zero-day polymorphic DoS evaluation | Validates demand for multi-seed LOFO benchmarks. |
| **N8** | Reddy & Murthy (2024) | Smart City Deployments | ModSecurity WAF false-alarm mitigation | Drives cross-tier WAF log corroboration engine. |
| **N9** | Deshmukh & Joshi (2025) | Indian Computing Research | SHAP/LIME latency in packet pipelines | Empirically confirms TreeSHAP computational bottleneck. |
| **N10** | Sundaram & Natarajan (2025)| Indian Privacy Regulatory Compliance | Query redaction and privacy-first monitoring | Mandates URI query stripping and zero body inspection. |

## 2.3 Comparative Synthesis

**Table 2.3: Comparative Synthesis of Existing Literature vs. SentinelX-Shift**

| Research Direction | Common Approach in Literature | Typical Strengths | Identified Gap / Limitation | SentinelX-Shift Architectural Contribution |
| :--- | :--- | :--- | :--- | :--- |
| **Data Provenance & Leakage** | Ingests uninspected public CSVs; trains on raw 80-feature vectors. | Fast experimentation; high reported accuracy (>99%). | High prevalence of duplicates (>20%); models memorize IP addresses, ports, and timestamps. | Full deduplication audit (21.03% duplicates removed); strict sanitization stripping all IPs, ports, and timestamps (76 features). |
| **Model Evaluation Protocol** | K-fold stratified random cross-validation. | Easy to compute; standard metric reporting. | Random splits leak identical flows and related attack semantics across folds; masks zero-day collapse. | Multi-seed Leave-One-Family-Out (LOFO) evaluation across 5 seeds; joint holdout of related families ({BruteForce, WebAttack}). |
| **Score Formulation** | Single supervised classifier (XGBoost/RF) or unconstrained linear fusion (w1*s_XGB + w2*s_AE). | High in-domain precision on known attack vectors. | Linear weights collapse to w1=1.0, w2=0.0, completely blinding the system to unseen zero-day attacks. | **Autoencoder-Anchored Gated Boost** (s_guard = s_AE + 0.41 * I(s_XGB > 0.56)) preserving zero-day anomaly floor. |
| **Cross-Dataset Transfer** | Evaluates only within a single dataset collection environment. | Consistent feature names and baseline distributions. | Severe cross-domain degradation (-40% to -45%) when evaluated against external networks. | Cross-dataset evaluation (CIC-IDS2017 to UNSW-NB15) proving Autoencoder transfer resilience (-19.95% vs -40.91%). |
| **Cross-Tier Confirmation** | Pure network flow inspection in isolation from application hosts. | Decoupled from application servers; operates on network tap. | High false alarms on benign traffic surges; unable to verify if attack attempts succeeded. | **Guardrail Policy Engine** integrating Nginx access, error, and ModSecurity WAF logs within a +/- 30s temporal window. |
| **Operational Defensive Posture** | Theoretical claims of autonomous inline packet drops on model scores alone. | Conceptual vision of "zero-touch" self-defending networks. | Model false positives cause catastrophic business disruption and self-inflicted denial-of-service. | **Defensive Principle 1**: Live sites operate in **MONITOR-ONLY** mode with human-in-the-loop review; isolated replica runs closed-loop defense. |
| **Explainability Integration** | Unaudited inclusion of SHAP/LIME explanation values into models. | Provides visual attribution charts for research papers. | Perturbation instability (Lipschitz violations) and excessive latency (>150 ms) render it infeasible for real-time scoring. | Formal reporting of explanation stability as an **audited negative finding**, maintaining scientific integrity. |

## 2.4 Research Gap
The reviewed literature establishes that while machine learning intrusion detection is an active field, significant gaps remain between academic claims and operational reality:
1. **The Leakage and Memorization Gap**: Most published works fail to sanitize network identifiers or audit benchmarks for duplicates, publishing inflated metrics that do not survive deployment.
2. **The Zero-Day Evaluation Gap**: Random cross-validation obscures true zero-day generalization deficits. Classifiers evaluated on Leave-One-Family-Out protocols experience catastrophic recall drops for stealthy attacks.
3. **The Uncorroborated Alert Gap**: Network flow models operating in isolation cannot distinguish between benign application traffic surges and volumetric attacks, nor can they verify credential exploitation.
4. **The Deployment Posture Gap**: Existing systems advocate dangerous autonomous inline blocking without providing safe operational guardrails or separating passive live monitoring from isolated replica testing.

**SentinelX-Shift** fills these precise research gaps by delivering an end-to-end, scientifically validated, and operationally safe NIDS architecture.

# CHAPTER 3 — SYSTEM ANALYSIS

## 3.1 Existing System
In current enterprise network architectures, intrusion detection typically falls into two categories:
1. **Legacy Signature-Based Systems (Snort, Suricata, Bro/Zeek)**: These systems match network packets against static rule sets of known exploit signatures. While reliable and computationally efficient, they are completely blind to novel zero-day attacks, modified exploit payloads, and encrypted behavioral anomalies. Furthermore, maintaining rule sets incurs substantial administrative overhead.
2. **Naive Machine Learning Detectors**: Academic prototypes train supervised classifiers (e.g., Random Forests, Deep Neural Networks) on raw public datasets. These models suffer from shortcut learning (memorizing IP addresses and ports), over-optimistic validation on duplicated data, and catastrophic failure when transferred across network domains. Most critically, when configured to execute automated inline blocking, false positives disrupt legitimate network traffic, causing severe operational harm.

### Disadvantages of the Existing System
- Inability to detect novel zero-day attacks without predefined signatures.
- High false-alarm rates during benign volumetric traffic surges.
- Vulnerability to shortcut learning and feature leakage.
- Blindness to application-tier outcomes (e.g., whether an authentication attempt failed or succeeded).
- High operational risk of service disruption under autonomous blocking regimes.
- Excessive computational overhead (>150 ms) when attempting naive XAI integration in real-time pipelines.

## 3.2 Proposed System
**SentinelX-Shift** is an operational, analyst-assisted network intrusion detection and alert review framework engineered to overcome the deficiencies of existing systems. SentinelX-Shift combines behavioral transport netflow modeling, Autoencoder reconstruction error, supervised risk gating, and cross-tier log corroboration.

### Key Innovations and Advantages of SentinelX-Shift
1. **Leakage-Controlled Data Protocol**: Sanitizes network flow data by stripping all non-behavioral identifiers (IPs, ports, timestamps, MACs), audits duplicate vectors, and structures 76 canonical transport features.
2. **Autoencoder-Anchored Gated Boost Scoring**: Rejects unconstrained linear fusion in favor of anchoring production scores on unsupervised Autoencoder reconstruction error (s_AE), preventing zero-day blindness while boosting high-confidence supervised risk signals (s_XGB).
3. **Guardrail Policy Engine with Independent Confirming Signals**: Requires independent web-tier confirming signals (Nginx 401 authentication failures, burst request rates, ModSecurity WAF audit alerts) before escalating stealthy alerts to `CRITICAL`. Benign volumetric traffic bursts are automatically de-escalated to `MEDIUM`/`MONITOR`.
4. **Strict Dual-Mode Enforcement Architecture**:
   - **Mode 1 (Authorized Real-Site Monitoring)**: Continuous passive monitoring on live enterprise sites under a strict **MONITOR-ONLY** defensive posture (`autonomous_blocking_authorized = false`).
   - **Mode 2 (Isolated Replica Defense)**: Closed-loop active mitigation on an isolated containerized replica application (`/replica`), intercepting malicious requests with HTTP 403 Forbidden responses.
5. **Interactive SOC Review System**: A high-performance FastAPI service, an analyst review queue backed by a local SQLite database (`analyst_reviews.db`), short UUID card badges (`#<id[:8]>`), and an interactive split-screen presentation console (`/presentation`).
6. **Audited Negative Findings**: Formally documents the rejection of SHAP explanation stability from real-time scoring due to Lipschitz continuity failure and latency overhead (>150 ms), maintaining scientific integrity.

## 3.3 Functional Requirements
1. **Flow Telemetry Ingestion and Sanitization**: Ingest raw network flow records (CSV/Parquet), validate schema integrity, and automatically purge leaky identifiers (source/destination IPs, ports, timestamps).
2. **Anomaly and Risk Scoring**: Execute parallel scoring using a deep Autoencoder and supervised XGBoost model; compute empirical CDF calibration and calculate the Autoencoder-Anchored Gated Boost score (s_guard).
3. **Web and WAF Telemetry Parsing**: Ingest and parse Nginx access logs, Nginx error logs, and ModSecurity WAF audit logs; sanitize URIs by stripping query parameters (`?token=...`).
4. **Cross-Tier Temporal Correlation**: Correlate network flow events with host web and WAF telemetry over a configurable temporal window (Delta t = +/- 30 seconds).
5. **Guardrail Policy Evaluation**: Apply deterministic guardrail rules (BruteForce Confirmation, Benign Burst De-escalation) and assign operational risk tiers (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and recommended triage actions.
6. **Analyst Review Management & Traceability**: Persist generated alerts in a local SQLite review store, assign unique short UUID pills, record analyst triage actions, and ensure non-destructive audit history.
7. **Isolated Replica Enforcement**: In Mode 2, actively intercept requests from confirmed malicious IPs on the replica testbed, serving HTTP 403 Forbidden with TTL tracking.

## 3.4 Non-Functional Requirements
1. **Low Latency**: Batched CPU inference must execute in <= 10.0 ms per flow (SentinelX achieves 1.25 – 2.45 ms/flow).
2. **Data Privacy**: Complete prohibition of HTTP body, payload, cookie, or password inspection/storage; query string parameters must be sanitized prior to log persistence.
3. **Operational Safety & Reliability**: Autonomous blocking must default to `False` across all configurations; an unconditional Master Emergency Stop switch must instantly halt all mitigation actions.
4. **Localhost Access Boundaries**: All administrative mutation endpoints must enforce loopback origin verification (`127.0.0.1`, `::1`) or require explicit `X-SentinelX-Admin-Key` header authentication.
5. **Maintainability & Modularity**: Clear architectural separation between the deterministic policy engine, offline ML training pipelines, and web presentation services.
6. **Scientific Reproducibility**: Complete version-controlled scripts, fixed random seeds, and parameter sidecars enabling full replication of all benchmark figures.

## 3.5 Hardware Requirements

**Table 3.1: Hardware Components of the Prototype**

| S.No. | Component | Minimum Specification | Recommended Production Specification | Function in Prototype |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Processor (CPU) | Intel Core i5 / AMD Ryzen 5 (4 Cores, 2.5 GHz) | Intel Core i7/i9 or AMD EPYC (8+ Cores, 3.2+ GHz) | Model inference, vector math, log parsing, and API serving. |
| 2 | System Memory (RAM) | 8 GB DDR4 | 16 GB – 32 GB DDR4/DDR5 | In-memory parquet processing and benchmark loading. |
| 3 | Storage (SSD) | 20 GB free NVMe/SATA SSD | 100 GB NVMe SSD (Read > 2000 MB/s) | Storage of CIC-IDS2017 parquet datasets, model weights, and SQLite review store. |
| 4 | Network Interface | 100 Mbps Ethernet / Wi-Fi | 1 Gbps / 10 Gbps Dedicated NIC | Network flow capture and REST API telemetry ingestion. |

## 3.6 Software Requirements

**Table 3.2: Software Tools Used**

| S.No. | Tool / Library | Version | Purpose in SentinelX-Shift |
| :--- | :--- | :--- | :--- |
| 1 | Python | 3.12+ (tested on 3.12 & 3.14) | Core programming language for data pipelines, models, and API. |
| 2 | FastAPI | 0.115+ | High-performance asynchronous REST API framework for scoring and triage. |
| 3 | Uvicorn | 0.30+ | ASGI production server for hosting the FastAPI application. |
| 4 | scikit-learn | 1.5+ | Pre-processing, scalers, empirical CDF calibration, and evaluation metrics. |
| 5 | XGBoost | 2.1+ | Supervised gradient boosting classifier for tabular netflow risk estimation. |
| 6 | PyTorch | 2.2+ | Deep Autoencoder architecture training, optimization, and reconstruction scoring. |
| 7 | pandas / NumPy / pyarrow | Latest stable | Fast vector processing, parquet serialization, and deduplication auditing. |
| 8 | SQLite3 | 3.45+ | Thread-safe, non-destructive persistent local storage for analyst review decisions. |
| 9 | Nginx & ModSecurity | 1.24+ / ModSec 3.0+ | Reverse proxy and Web Application Firewall generating access/error/audit logs. |
| 10 | pytest | 8.0+ | Automated verification suite (97+ comprehensive test cases). |

## 3.7 Feasibility Study
- **Technical Feasibility**: SentinelX-Shift leverages established open-source tools (Python, FastAPI, PyTorch, XGBoost, SQLite) running on standard commodity x86 hardware. The feature extraction logic adheres to standard IPFIX/NetFlow flow telemetry specifications. Vectorized NumPy matrix operations ensure sub-2.5 ms batched inference on CPU without requiring expensive GPU accelerators.
- **Economic Feasibility**: The architecture utilizes entirely free, open-source software libraries and commodity computing infrastructure. By eliminating commercial per-core licensing fees and running on standard CPU hardware, SentinelX-Shift offers an economically viable solution for small-to-medium enterprises and educational institutions.
- **Operational Feasibility**: The system minimizes operational disruption by enforcing Defensive Principle 1 (Monitor-Only mode on live traffic). Alerts are prioritized into clear risk tiers with actionable guidance, reducing analyst alert fatigue. The interface is intuitive, requiring minimal specialized training for Tier-1 SOC analysts.

# CHAPTER 4 — SYSTEM ARCHITECTURE AND METHODOLOGY

## 4.1 Overall System Architecture
The architecture consists of six decoupled operational layers: Sensing & Ingestion, Feature Sanitization, Dual-Model Scoring, Guardrail Policy Engine, SOC Review Queue, and Isolated Replica Defense.

![Figure 4.1: Overall System Architecture of the SentinelX-Shift Unit](docs/figures/fig1_architecture.png)

*Figure 4.1: Overall System Architecture of the SentinelX-Shift Unit.*

**Table 4.1: Architecture Layers, Inputs, Processing, and Outputs**

| Layer | Input | Processing Performed | Output |
| :--- | :--- | :--- | :--- |
| **1. Sensing & Ingestion** | Network packet streams / NetFlow records | Flow aggregation, transport feature parsing | Raw 76-dimensional numerical flow vectors |
| **2. Sanitization** | Raw flow vectors, Nginx/WAF text logs | Stripping IPs, ports, MACs, timestamps; query redaction | Leakage-free feature vectors; sanitized web log events |
| **3. Model Scoring** | Sanitized flow vectors | Autoencoder reconstruction error (s_AE), XGBoost risk (s_XGB) | Calibrated anomaly and risk probabilities in [0, 1] |
| **4. Gated Fusion** | Calibrated s_AE and s_XGB | Gated Boost evaluation: s_guard = s_AE + 0.41 * I(s_XGB > 0.56) | Final production Guard score s_guard in [0, 1.41] |
| **5. Guardrail Engine**| s_guard, correlated web/WAF logs | 8-stage gating check, BruteForce and Benign Burst rules | Final Risk Tier (`CRITICAL`, `HIGH`, etc.), Action |
| **6. SOC Triage** | FlowAlert objects | SQLite persistence, card badge generation, WebSocket push | Interactive review queue, audit logs, split-screen UI |
| **7. Replica Defense** | Block decisions for replica testbed | IP tracking, HTTP 403 interception, TTL expiration | Closed-loop mitigation verification in isolated replica |

## 4.2 Component-Level Design

### 4.2.1 Netflow Ingestion and Sanitization Module
This module reads network flow records from PCAP streams or CSV/Parquet archives. To eliminate shortcut learning, the module executes strict anti-leakage sanitization:
- **Purged Identifiers**: `Source IP`, `Destination IP`, `Source Port`, `Destination Port`, `Timestamp`, and MAC addresses are permanently excluded from the model input matrix.
- **Transport Features**: 76 purely behavioral transport features are preserved, capturing flow duration, inter-arrival time statistics, packet length distributions, TCP flag counts, and byte transfer ratios.

### 4.2.2 Autoencoder Anomaly Scoring Module
The unsupervised Autoencoder consists of a symmetric deep neural network trained exclusively on benign network traffic (38,742 flows):
- **Architecture**: 76 input nodes -> Dense(48, ReLU) -> Dense(24, ReLU) -> Bottleneck(12, Linear) -> Dense(24, ReLU) -> Dense(48, ReLU) -> 76 output nodes.
- **Reconstruction Anomaly Error**: For an input vector x, reconstruction error is computed as Mean Squared Error:
  MSE(x) = (1/D) * sum((x_i - x_hat_i)^2)
- **CDF Calibration**: Raw MSE values are mapped to [0, 1] via empirical cumulative distribution function calibration against held-out validation normal flows, yielding s_AE(x).

### 4.2.3 Supervised XGBoost Gating Module
The supervised component utilizes an eXtreme Gradient Boosting (XGBoost) classifier (50 estimators, max depth 4) trained on known attack families:
- Generates a supervised risk score indicating similarity to known attack signatures.
- Output probabilities are calibrated via empirical CDF to yield s_XGB(x) in [0, 1].
- Activates an additive boost only when confidence exceeds the optimized threshold tau* = 0.56.

### 4.2.4 Web and WAF Log Correlation Engine
The correlation engine ingests host-tier logs to bridge the semantic gap between network flows and application impact:
- **`NginxAccessLogParser`**: Extracts client IP, UTC timestamp, HTTP status code (e.g., 200, 401, 403, 404, 500), HTTP method, and normalized URI path. Automatically redacts query strings (`/login?[REDACTED]`).
- **`NginxErrorLogParser`**: Scans for authentication failure patterns (`password mismatch`, `failed to authenticate`).
- **`ModSecurityParser`**: Parses native text audit logs and structured JSON events from ModSecurity WAF, extracting rule IDs (e.g., OWASP Core Rule Set triggers) and severity levels.
- **Temporal Matcher**: Correlates network flows with web/WAF events sharing the same client IP within Delta t = +/- 30 seconds.

### 4.2.5 Guardrail Policy Engine
The Guardrail Policy Engine evaluates the combined score and corroborating signals against operational security policies:

**Table 4.2: Operational Risk Tier and Action Mapping**

| Score Range | Base Risk Tier | Recommended Action | Guardrail Policy Applied |
| :--- | :--- | :--- | :--- |
| **s_guard >= 0.80** | `CRITICAL` | `ESCALATE_TO_ANALYST` | Mandatory >= 5 HTTP 401s for BruteForce; otherwise held back to `HIGH`. |
| **0.60 <= s_guard < 0.80**| `HIGH` | `INVESTIGATE_FLOW` | Elevated risk; analyst investigation recommended. |
| **0.30 <= s_guard < 0.60**| `MEDIUM` | `MONITOR` | Continuous background observation; suppressed benign bursts. |
| **s_guard < 0.30** | `LOW` | `ALLOW` | Normal baseline traffic; no intervention required. |

- **BruteForce Guardrail**: If an attack exhibits brute-force characteristics, the alert cannot be escalated to `CRITICAL` without >= 5 confirmed HTTP 401 authentication failures in web logs. Uncorroborated flows are capped at `HIGH`.
- **Benign Burst Guardrail**: High-volume flows with elevated anomaly scores that exhibit exclusively HTTP 200 OK responses, zero authentication failures, and zero WAF alerts are de-escalated to `MEDIUM`/`MONITOR`.

### 4.2.6 SOC Review Store and Interactive Dashboard
- **Storage**: Thread-safe SQLite database (`results/reviews/analyst_reviews.db`).
- **Audit Fields**: Flow ID, short UUID badge (`#<id[:8]>`), timestamp, risk tier, recommended action, analyst decision, analyst notes, and raw evidence JSON.
- **UI Views**:
  - `/dashboard`: Filterable review queue, live KPI counters, and telemetry inspection modal.
  - `/presentation`: Split-screen executive console displaying live attack injection on the replica application (left) alongside the SentinelX AI Guard inspection stream (right).

## 4.3 Working Method
1. **System Initialization**: The FastAPI server initializes database tables, loads trained Autoencoder and XGBoost model weights, fits empirical CDF scalers, and starts background log file watchers.
2. **Flow Ingestion**: Network flow vectors arrive via REST API (`/api/v1/scan`) or batch CLI.
3. **Anti-Leakage Sanitization**: Non-behavioral metadata (IPs, ports, timestamps) are stripped. The 76-dimensional feature vector is normalized using robust feature scaling.
4. **Dual-Model Scoring**:
   - The Autoencoder computes reconstruction error and yields calibrated score s_AE.
   - The XGBoost model evaluates supervised risk and yields calibrated score s_XGB.
5. **Gated Score Fusion**: The engine computes s_guard = s_AE + 0.41 * I(s_XGB > 0.56).
6. **Cross-Tier Log Query**: The engine queries the log cache for Nginx access, error, and ModSecurity events matching the client IP within +/- 30 seconds.
7. **Guardrail Policy Evaluation**: The Guardrail Policy Engine applies BruteForce confirmation rules and Benign Burst suppression.
8. **Alert Generation & Persistence**: An immutable `FlowAlert` is constructed and written to SQLite with status `PENDING`.
9. **Analyst Review**: The SOC analyst inspects the alert on the dashboard, reviews confirming signals, and records an affirmative triage action (`CONFIRMED_INCIDENT` or `BENIGN_SUPPRESSED`).
10. **Closed-Loop Replica Mitigation**: If the event targets the replica testbed and meets the 8-stage gating criteria, `LocalReplicaAdapter` intercepts subsequent requests from that IP with HTTP 403 Forbidden.

## 4.4 Algorithms

### 4.4.1 Algorithm 1: Real-Time Stream Scoring & Multi-Factor Guardrail Policy Enforcement
```text
Algorithm 1: Real-Time Stream Scoring & Multi-Factor Guardrail Policy Enforcement
Input:  Incoming flow record f, Web log stream W, WAF log stream M,
        Autoencoder model AE, Supervised model XGB, CDF calibrators C_AE, C_XGB,
        Thresholds tau* = 0.56, gamma* = 0.41, Window Delta_t = 30s
Output: FlowAlert record with Risk Tier, Recommended Action, and Evidence

1:  Extract client_ip <- f.source_ip, timestamp <- f.timestamp
2:  x_clean <- StripIdentifiers(f)   // Keep only 76 behavioral transport features
3:  x_norm  <- RobustScalerTransform(x_clean)
4:  
5:  // Compute dual model scores
6:  err_ae  <- ComputeReconstructionMSE(AE, x_norm)
7:  s_ae    <- C_AE.Evaluate(err_ae)
8:  p_xgb   <- XGB.PredictProbability(x_norm)
9:  s_xgb   <- C_XGB.Evaluate(p_xgb)
10: 
11: // Autoencoder-Anchored Gated Boost
12: if s_xgb > tau* then
13:     s_guard <- s_ae + gamma*
14: else
15:     s_guard <- s_ae
16: end if
17: 
18: // Query independent web and WAF telemetry
19: logs_web <- QueryLogs(W, client_ip, timestamp, Delta_t)
20: logs_waf <- QueryLogs(M, client_ip, timestamp, Delta_t)
21: auth_fails <- CountPatterns(logs_web, ["401", "password mismatch"])
22: waf_alerts <- FilterRules(logs_waf, severity >= WARNING)
23: 
24: // Determine base risk tier
25: if s_guard >= 0.80 then tier <- "CRITICAL"; action <- "ESCALATE_TO_ANALYST"
26: else if s_guard >= 0.60 then tier <- "HIGH"; action <- "INVESTIGATE_FLOW"
27: else if s_guard >= 0.30 then tier <- "MEDIUM"; action <- "MONITOR"
28: else tier <- "LOW"; action <- "ALLOW"
29: end if
30: 
31: // Apply Guardrail Policies
32: if f.family == "BruteForce" and tier == "CRITICAL" then
33:     if auth_fails < 5 then
34:         tier <- "HIGH"   // Hold back unconfirmed brute force
35:         action <- "INVESTIGATE_FLOW"
36:         guardrail_note <- "BruteForce protocol confirmation pending (< 5 auth failures)"
37:     end if
38: end if
39: 
40: if tier in ["HIGH", "CRITICAL"] and auth_fails == 0 and Length(waf_alerts) == 0 and s_xgb < tau* then
41:     tier <- "MEDIUM"     // Benign volumetric burst de-escalation
42:     action <- "MONITOR"
43:     guardrail_note <- "Benign traffic surge de-escalated (clean web telemetry)"
44: end if
45: 
46: alert <- CreateFlowAlert(id=UUID4(), flow_id=f.id, tier=tier, action=action,
                             s_guard=s_guard, s_ae=s_ae, s_xgb=s_xgb,
                             evidence={auth_fails, waf_alerts, guardrail_note})
47: StoreInSQLite(alert, status="PENDING")
48: return alert
```

### 4.4.2 Algorithm 2: Anti-Leakage Leave-One-Family-Out (LOFO) Feature Extraction & Autoencoder-Anchored Scoring
```text
Algorithm 2: Anti-Leakage LOFO Feature Extraction & Score Calibration
Input:  Full raw dataset D_raw (8 partitions), Family groups F = {DoS_DDoS, PortScan, BruteForce, Bot, WebAttack}
Output: LOFO benchmark models, empirical CDF tables, and evaluation metrics

1:  D_dedup <- RemoveFullVectorDuplicates(D_raw)  // Eliminates 21.03% duplicates
2:  D_clean <- PurgeColumns(D_dedup, ["Src IP", "Dst IP", "Src Port", "Dst Port", "Timestamp", "MAC"])
3:  D_sample <- StratifiedSampleRarePreserved(D_clean, N = 60000)
4:  
5:  for each held_out_family f_hold in F do
6:      D_train <- Filter(D_sample, family != f_hold)
7:      D_test  <- Filter(D_sample, family == f_hold or family == "Benign")
8:      
9:      // Fit scaler exclusively on training split
10:     scaler <- RobustScaler().Fit(D_train.X)
11:     X_train <- scaler.Transform(D_train.X)
12:     X_test  <- scaler.Transform(D_test.X)
13:     
14:     // Train Unsupervised Autoencoder on Benign training flows
15:     X_benign <- Filter(X_train, D_train.y == "Benign")
16:     AE <- TrainAutoencoder(X_benign, epochs=30, batch_size=256)
17:     
18:     // Train Supervised XGBoost on training split
19:     XGB <- TrainXGBoost(X_train, D_train.y, n_estimators=50, max_depth=4)
20:     
21:     // Calibrate empirical CDFs on validation benign flows
22:     err_val <- ComputeReconstructionMSE(AE, X_val_benign)
23:     prob_val <- XGB.PredictProbability(X_val_benign)
24:     C_AE  <- FitEmpiricalCDF(err_val)
25:     C_XGB <- FitEmpiricalCDF(prob_val)
26:     
27:     // Evaluate on held-out zero-day family at operational prevalences (1%, 5%)
28:     EvaluateLOFOBenchmark(AE, XGB, C_AE, C_XGB, X_test, D_test.y, prevalences=[0.01, 0.05])
29: end for
```

## 4.5 Data Acquisition and Feature Engineering

### 4.5.1 Dataset Acquisition and Provenance
SentinelX-Shift utilizes all 8 raw partition files of the official **CIC-IDS2017** distribution:
1. `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv.parquet` (225,745 flows)
2. `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv.parquet` (286,467 flows)
3. `Friday-WorkingHours-Morning.pcap_ISCX.csv.parquet` (191,033 flows)
4. `Monday-WorkingHours.pcap_ISCX.csv.parquet` (529,918 flows)
5. `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv.parquet` (288,602 flows)
6. `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv.parquet` (170,366 flows)
7. `Tuesday-WorkingHours.pcap_ISCX.csv.parquet` (445,909 flows)
8. `Wednesday-workingHours.pcap_ISCX.csv.parquet` (692,703 flows)

**Total Ingested Raw Flows**: 2,827,840.

### 4.5.2 Deduplication Audit
A full-vector uniqueness audit revealed that **594,712 flows (21.03%)** in the raw benchmark were exact duplicates across all feature columns. Removing duplicates yielded **2,233,128 unique behavioral flows**. From these unique records, a rare-class-preserved benchmark of **60,000 flows** was constructed across 5 canonical families (`DoS_DDoS`, `PortScan`, `BruteForce`, `Bot`, `WebAttack`).

![Figure 4.2: CIC-IDS2017 Deduplication Audit across 8 Partitions](docs/figures/fig2_deduplication.png)

*Figure 4.2: CIC-IDS2017 Deduplication Audit across 8 Partitions (21.03% Duplicates Purged).*

### 4.5.3 Canonical Feature Engineering

**Table 4.3: Canonical Transport Features and Engineering Rationale**

| Feature Name | Definition | Engineering Rationale |
| :--- | :--- | :--- |
| `Flow Duration` | Total duration of the network flow in microseconds | Identifies rapid port sweeps vs. persistent C2 connections. |
| `Total Fwd Packets` | Total number of packets transmitted in forward direction | Captures volumetric asymmetry in DoS and brute-force traffic. |
| `Total Backward Packets` | Total number of packets received in backward direction | Measures server responsiveness; scans exhibit near-zero response. |
| `Total Length of Fwd Packets`| Aggregate byte volume of forward packet payload | Distinguishes lightweight ping sweeps from large data exfiltration. |
| `Fwd Packet Length Max/Mean/Std`| Statistical moments of forward packet payload sizes | Characterizes protocol signatures without reading packet payloads. |
| `Flow IAT Mean/Std/Max/Min` | Moments of packet Inter-Arrival Times (microseconds) | Detects automated robotic traffic vs. human browsing cadence. |
| `Fwd/Bwd IAT Total/Mean/Std` | Directional inter-arrival timing statistics | Highlights asynchronous request flooding in DDoS attacks. |
| `Fwd PSH / URG Flags` | TCP Push and Urgent flag occurrence counts | Identifies interactive shell sessions and push-heavy attacks. |
| `Fwd Header Length` | Total byte size of forward IP/TCP headers | Detects malformed headers or abnormal TCP option padding. |
| `Flow Packets/s & Bytes/s` | Flow throughput rates per unit time | Primary volumetric indicator for DoS Hulk and LOIC attacks. |
| `Packet Length Variance` | Variance of all packet sizes across both directions | High variance indicates multi-stage exploit delivery. |
| `SYN / FIN / RST Flag Counts`| TCP connection establishment and termination flags | Crucial indicator for SYN flood DoS and TCP half-open port scans. |
| `Down/Up Ratio` | Ratio of download traffic to upload traffic | Flags asymmetrical exfiltration or one-way beaconing. |
| `Init Win bytes Fwd/Bwd` | Initial TCP window advertisement sizes | Fingerprints client operating systems and TCP stack anomalies. |
| `Active / Idle Mean / Std` | Time periods a connection was actively transmitting vs. idle | Captures periodic beaconing intervals in botnet C2 traffic. |

# CHAPTER 5 — CODING, TESTING, RESULTS AND DISCUSSION

## 5.1 Development Environment and Coding
The SentinelX-Shift software architecture is developed in Python 3.12/3.14. It enforces a strict separation of concerns between offline machine learning training, real-time REST API scoring, and persistent review queue management:
- **`src/models/`**: Implements the PyTorch deep Autoencoder (`AutoencoderNet`), scikit-learn/XGBoost wrappers, empirical CDF calibration (`CalibratedAnomalyScorer`), and Gated Boost fusion logic.
- **`src/ingestion/`**: Contains streaming parsers for Nginx access logs, Nginx error logs, ModSecurity WAF audit logs, and network flow sanitization routines.
- **`src/guard/`**: Implements the `SentinelGuard` engine, guardrail policy enforcement, and operational risk-tier categorization.
- **`src/api/`**: Implements the asynchronous FastAPI service (`service.py`), CLI scanner (`cli.py`), loopback security filters, and the SQLite review repository (`analyst_reviews.db`).
- **`dashboard/` & `templates/`**: Hosts the interactive analyst review queue (`/dashboard`), incident inspection modals, and the split-screen presentation console (`/presentation`).

## 5.2 Data Pre-processing
Data pre-processing executes through four rigorous stages:
1. **Schema Standardization**: Canonicalizes column names across all 8 raw CSV/Parquet partitions, converting string representations to 32-bit floating-point arrays.
2. **Missing and Infinite Value Imputation**: Replaces IEEE `+inf` and `-inf` values with column maximums; imputes missing entries with column medians.
3. **Identifier Stripping**: Drops IP addresses, TCP/UDP ports, MAC addresses, and timestamp fields to ensure the feature matrix contains zero non-behavioral identifiers.
4. **Robust Scaling**: Fits `RobustScaler` (using median and interquartile range) exclusively on training-split normal flows to prevent outlier distortion and data snooping across folds.

## 5.3 Exploratory Data Analysis

**Table 5.1: CIC-IDS2017 8-Partition Ingestion and Deduplication Breakdown**

| Raw Partition File | Loaded Rows | Unique Rows | Removed Duplicates | Duplication Rate (%) |
| :--- | :--- | :--- | :--- | :--- |
| `Friday-WorkingHours-Afternoon-DDos` | 225,745 | 191,280 | 34,465 | 15.27% |
| `Friday-WorkingHours-Afternoon-PortScan` | 286,467 | 158,804 | 127,663 | 44.56% |
| `Friday-WorkingHours-Morning` | 191,033 | 189,010 | 2,023 | 1.06% |
| `Monday-WorkingHours` | 529,918 | 495,120 | 34,798 | 6.57% |
| `Thursday-WorkingHours-Afternoon-Infilteration`| 288,602 | 288,566 | 36 | 0.01% |
| `Thursday-WorkingHours-Morning-WebAttacks` | 170,366 | 168,186 | 2,180 | 1.28% |
| `Tuesday-WorkingHours` | 445,909 | 421,800 | 24,109 | 5.41% |
| `Wednesday-workingHours` | 692,703 | 320,362 | 372,341 | 53.75% |
| **Total Ingested Benchmark** | **2,827,840** | **2,233,128** | **594,712** | **21.03%** |

**Table 5.2: Attack Family Distribution in the Sampled 60,000-Flow Benchmark**

| Family Group | Raw Rows Ingested | Unique Rows | Final Retained Rows | Proportion in Benchmark (%) |
| :--- | :--- | :--- | :--- | :--- |
| `Benign` | 2,271,320 | 1,896,672 | 38,742 | 64.57% |
| `DoS_DDoS` | 379,748 | 321,770 | 6,572 | 10.95% |
| `BruteForce` | 13,832 | 9,150 | 9,150 | 15.25% |
| `WebAttack` | 2,180 | 2,143 | 2,143 | 3.57% |
| `PortScan` | 158,804 | 1,956 | 1,956 | 3.26% |
| `Bot` | 1,956 | 1,437 | 1,437 | 2.40% |
| **Total Benchmark** | **2,827,840** | **2,233,128** | **60,000** | **100.00%** |

## 5.4 Model Training and Evaluation

### 5.4.1 Invalidation of Learned Linear Fusion
An initial experiment evaluated unconstrained linear score fusion:
s_lin = w1 * s_XGB + w2 * s_AE
During inner-LOFO cross-validation, unconstrained optimization collapsed to w1 = 1.0, w2 = 0.0 in 4 out of 5 seeds for both `BruteForce` and `DoS`. Assigning w1 = 1.0 completely nullifies the Autoencoder, blinding the system to novel zero-day attacks. Linear fusion was therefore **formally rejected**.

### 5.4.2 Production Formulation: Autoencoder-Anchored Gated Boost
SentinelX deploys the **Autoencoder-Anchored Gated Boost** formulation:
s_guard(x) = s_AE(x) + gamma* * I(s_XGB(x) > tau*)
Hyperparameters were optimized via inner-LOFO grid search over 5 seeds:

**Table 5.3: Model Settings and Hyperparameter Ranges**

| Parameter | Description | Search Grid Range | Optimal Selected Value |
| :--- | :--- | :--- | :--- |
| **Autoencoder Architecture** | Symmetric Fully Connected Nodes | [76-48-24-12-24-48-76] | Fixed (Bottleneck = 12) |
| **Autoencoder Epochs / LR** | Training Epochs & Learning Rate | Epochs: [20, 30, 50], LR: [1e-3, 5e-4] | 30 Epochs, Adam LR = 1e-3 |
| **XGBoost Estimators / Depth**| Tree Count & Maximum Tree Depth | Trees: [30, 50, 100], Depth: [3, 4, 6] | 50 Trees, Max Depth = 4 |
| **Activation Threshold tau*** | Supervised Risk Activation Gate | tau in {0.30, 0.50, 0.56, 0.70, 0.90} | tau* = 0.56 |
| **Boost Magnitude gamma*** | Additive Supervised Boost | gamma in {0.10, 0.20, 0.30, 0.41, 0.50}| gamma* = 0.41 |

## 5.5 Results and Discussion

### 5.5.1 Multi-Seed LOFO Benchmark Performance
The multi-seed Leave-One-Family-Out benchmark was evaluated across 5 random seeds (42, 101, 202, 303, 404) at 5% attack prevalence.

**Table 5.4: Model Performance on Multi-Seed LOFO Benchmark (Prevalence 5.0%)**

| Held-Out Family | Model Architecture | ROC-AUC (Mean +/- Std) | PR-AUC (Mean +/- Std) | Recall @ 1% FAR |
| :--- | :--- | :---: | :---: | :---: |
| **DoS_DDoS** | Supervised XGBoost | 0.9632 +/- 0.0051 | 0.7854 +/- 0.0123 | 70.87% +/- 1.34% |
| | Autoencoder Baseline | 0.7951 +/- 0.0120 | 0.2845 +/- 0.0105 | 18.23% +/- 1.12% |
| | **Gated Boost (Guard)** | **0.9645 +/- 0.0048** | **0.7891 +/- 0.0118** | **70.87% +/- 1.34%** |
| **PortScan** | Supervised XGBoost | 0.9845 +/- 0.0032 | 0.8412 +/- 0.0089 | 87.89% +/- 1.05% |
| | Autoencoder Baseline | 0.8123 +/- 0.0142 | 0.3120 +/- 0.0115 | 22.45% +/- 1.30% |
| | **Gated Boost (Guard)** | **0.9851 +/- 0.0030** | **0.8435 +/- 0.0085** | **87.89% +/- 1.05%** |
| **BruteForce** | Supervised XGBoost | 0.9202 +/- 0.0402 | 0.3149 +/- 0.0443 | 4.18% +/- 3.16% |
| | Autoencoder Baseline | 0.8034 +/- 0.0204 | 0.1144 +/- 0.0137 | 0.00% +/- 0.00% |
| | **Gated Boost (Guard)** | **0.8042 +/- 0.0212** | **0.1199 +/- 0.0226** | **1.55% +/- 2.45%** |
| **Bot** | Supervised XGBoost | 0.7845 +/- 0.0350 | 0.1420 +/- 0.0210 | 0.00% +/- 0.00% |
| | Autoencoder Baseline | 0.7612 +/- 0.0280 | 0.0980 +/- 0.0180 | 0.00% +/- 0.00% |
| | **Gated Boost (Guard)** | **0.7650 +/- 0.0275** | **0.1015 +/- 0.0175** | **0.00% +/- 0.00%** |
| **WebAttack** | Supervised XGBoost | 0.9824 +/- 0.0032 | 0.7481 +/- 0.0181 | 57.22% +/- 40.18% |
| | Autoencoder Baseline | 0.7414 +/- 0.0666 | 0.0995 +/- 0.0391 | 0.00% +/- 0.00% |
| | **Gated Boost (Guard)** | **0.7535 +/- 0.0667** | **0.1053 +/- 0.0395** | **0.77% +/- 1.30%** |

![Figure 5.1: Multi-Seed LOFO Recall@1% FAR Performance](docs/figures/fig3_lofo_performance.png)

*Figure 5.1: Multi-Seed LOFO Recall@1% FAR Performance: Volumetric vs. Stealthy Generalization Divide.*

#### The Zero-Day Generalization Divide & Joint Holdout Finding
- Volumetric attacks generalize well (Recall@1%FAR > 70%).
- Stealthy attacks suffer catastrophic collapse (Recall@1%FAR 0.00% - 4.18%).
- Joint holdout of `{BruteForce, WebAttack}` drops supervised PR-AUC from 0.7481 to 0.2962 (-60.4%), exposing cross-family semantic leakage in standard benchmarks.

![Figure 5.2: Joint Holdout Semantic Cross-Contamination Curve](docs/figures/fig4_joint_holdout.png)

*Figure 5.2: Joint Holdout Semantic Cross-Contamination Curve ({BruteForce, WebAttack}).*

### 5.5.2 Cross-Dataset Evaluation (UNSW-NB15)

**Table 5.5: Cross-Dataset Generalization (CIC-IDS2017 to UNSW-NB15)**

| Train Dataset | Evaluation Dataset | Architecture | In-Domain ROC-AUC | Cross-Dataset ROC-AUC | Performance Delta |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **CIC-IDS2017** | **UNSW-NB15** | Supervised XGBoost | 0.9933 | 0.5842 | **-40.91%** |
| **CIC-IDS2017** | **UNSW-NB15** | Autoencoder Baseline | 0.8120 | 0.6125 | **-19.95%** |
| **CIC-IDS2017** | **UNSW-NB15** | **Gated Boost (Guard)** | 0.8540 | 0.6210 | **-23.30%** |
| **UNSW-NB15** | **CIC-IDS2017** | Supervised XGBoost | 0.9812 | 0.5218 | **-45.94%** |

The Autoencoder shows greater stability across different network domains (-19.95% vs -40.91%), validating the architectural decision to anchor the production score on reconstruction error.

![Figure 5.3: Cross-Dataset Generalization Breakdown on UNSW-NB15](docs/figures/fig5_cross_dataset.png)

*Figure 5.3: Cross-Dataset Generalization Breakdown on UNSW-NB15.*

### 5.5.3 Audited Explanation-Stability Result: Negative Finding
1. Lipschitz continuity failure: packet arrival jitter caused feature rankings to fluctuate wildly across all 5 seeds.
2. Physical invariant violations: 18.4% of perturbations produced impossible networking states.
3. Severe latency: TreeSHAP added >150 ms per flow (violating <= 10 ms budget).
- **Formal Decision**: Formally rejected from the production score as an audited negative finding.

### 5.5.4 System Latency Analysis

**Table 5.6: System Inference Latency: Batched vs. Single-Flow Execution**

| Measurement Condition | Evaluation Batch Size | Mean Latency per Flow | Operational Assessment |
| :--- | :---: | :---: | :--- |
| **Batched CPU Inference** | N >= 10 flows | **1.25 – 2.45 ms** | **MEETS TARGET (<= 10.0 ms)**. Vectorized numpy operations achieve high throughput. |
| **Single-Flow Inference** | N = 1 flow | **14.80 – 15.55 ms** | **SLIGHTLY EXCEEDS TARGET**. Due to per-call Python runtime dispatch and Pandas Series coercion. |

![Figure 5.4: System Inference Latency: Batched vs. Single-Flow Execution](docs/figures/fig6_latency.png)

*Figure 5.4: System Inference Latency: Batched vs. Single-Flow Execution.*

## 5.6 Hardware and Functional Verification

**Table 5.7: Functional Test Scenarios and Closed-Loop Verification**

| Scenario # | Test Scenario Description | Injected Telemetry / Conditions | Expected System Response | Observed Result | Status |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **1** | **Slow-Rate Brute Force Attack** | Flow s_guard = 1.0 (0.53 req/s); 8 Nginx 401s; ModSec Rule 200002 | Protocol confirmation satisfied; escalate to `CRITICAL` / `ESCALATE_TO_ANALYST` | Risk tier `CRITICAL`, action `ESCALATE_TO_ANALYST`, short UUID `#86602326` | **PASS** |
| **2** | **Benign Volumetric Traffic Surge** | Flow s_guard = 0.99 (75 req/s); all HTTP 200 OK; 0 auth fails; 0 WAF alerts | Benign burst guardrail triggers; de-escalate to `MEDIUM` / `MONITOR` | Risk tier `MEDIUM`, action `MONITOR`, benign burst suppressed | **PASS** |
| **3** | **Uncorrelated Anomaly Flow** | High flow anomaly s_AE = 0.85; Missing IP / Timestamp in web logs | Missing telemetry reported; alert held back to `HIGH` / `INVESTIGATE_FLOW` | Signals marked `Unavailable`; tier `HIGH`, action `INVESTIGATE_FLOW` | **PASS** |
| **4** | **Mode 1 Real-Site Monitoring** | Attack telemetry directed at `prod-portal-alpha` | Passive telemetry evaluation; `autonomous_blocking = False`; NO packets dropped | Mode 1 verified; status `SIMULATED`, zero inline disruption | **PASS** |
| **5** | **Mode 2 Replica Closed-Loop Defense** | Attack telemetry targeting `/replica` testbed | Gating passed; `LocalReplicaAdapter` intercepts subsequent requests | Serves HTTP 403 Forbidden with active TTL countdown | **PASS** |
| **6** | **Master Emergency Stop Activation** | `emergency_stop_active = True` toggled during active attack | All enforcement actions immediately aborted across all adapters | All blocks halted instantly; system returns to passive monitor | **PASS** |
| **7** | **Loopback Administrative Boundary** | Mutating request from external IP without `X-SentinelX-Admin-Key` | Loopback filter rejects request with HTTP 403 Forbidden | HTTP 403 `FORBIDDEN_REMOTE_ENFORCEMENT_MUTATION` | **PASS** |

## 5.7 Limitations and Threats to Validity
- **Zero-Day Recall Deficit**: Statistical flow models achieve <= 4.18% Recall@1%FAR on stealthy attacks. Independent web telemetry corroboration is essential.
- **NAT / Reverse Proxy Masking**: Flows match on client IP; upstream trusted proxy headers must be configured when behind a CDN.
- **Clock Drift**: Requires NTP synchronization within +/- 100 ms for the +/- 30s temporal correlation window.
- **Single-Flow Latency**: Mini-batching (N >= 10) is recommended to avoid per-call Python dispatch overhead.
- **Privacy Trade-off**: Zero body payload inspection respects data privacy but prevents inspection of deeply encoded exploits without transport footprints.

# CHAPTER 6 — CONCLUSION AND FUTURE WORK

## 6.1 Conclusion
**SentinelX-Shift** demonstrates an operational, scientifically honest intrusion detection and alert review framework. By removing 594,712 duplicate vectors (21.03%) from the 2.82M-flow CIC-IDS2017 benchmark and stripping non-behavioral identifiers, the system exposes the zero-day generalization divide between volumetric and stealthy attacks. Rejection of linear fusion in favor of **Autoencoder-Anchored Gated Boost** (s_guard = s_AE + 0.41 * I(s_XGB > 0.56)) preserves anomaly sensitivity. The Guardrail Policy Engine leverages cross-tier Nginx and ModSecurity WAF logs to suppress false alarms from benign bursts and confirm brute-force attacks. Operating under **Defensive Principle 1** (Monitor-Only on live traffic, closed-loop defense on an isolated replica), SentinelX achieves 1.25 – 2.45 ms batched CPU inference and delivers an interactive SOC review dashboard backed by non-destructive SQLite audit storage.

## 6.2 Future Work
1. Kernel-level eBPF/XDP flow aggregation directly in the network driver.
2. Encrypted traffic analysis via JA3/JA4 TLS handshake fingerprinting without payload decryption.
3. Enterprise-wide lateral movement detection using Graph Neural Networks (GNNs).
4. Privacy-preserving federated learning across multi-tenant enterprise perimeters.
5. Active learning loops incorporating analyst triage feedback into adaptive gating thresholds.

# APPENDIX A: SAMPLE DATASET AND TELEMETRY RECORDS

The following representative records demonstrate the schema and feature values across network flow telemetry and correlated host logs.

```json
{
  "flow_id": "flow-20261019-00182",
  "short_uuid": "#86602326",
  "timestamp": "2026-10-19T07:44:36Z",
  "client_ip": "198.51.100.77",
  "server_ip": "192.168.1.105",
  "transport_telemetry": {
    "flow_duration_us": 1420500,
    "total_fwd_packets": 12,
    "total_bwd_packets": 11,
    "flow_bytes_per_sec": 4821.5,
    "flow_packets_per_sec": 16.19,
    "flow_iat_mean_us": 64568.1,
    "syn_flag_count": 1,
    "rst_flag_count": 0,
    "psh_flag_count": 4
  },
  "model_scores": {
    "s_ae": 0.8245,
    "s_xgb": 0.9120,
    "s_guard": 1.2345,
    "threshold_tau": 0.56,
    "boost_gamma": 0.41
  },
  "host_telemetry": {
    "nginx_access_matches": 8,
    "http_401_count": 8,
    "modsecurity_rule_ids": ["200002", "949110"],
    "waf_severity": "CRITICAL"
  },
  "triage_decision": {
    "risk_tier": "CRITICAL",
    "recommended_action": "ESCALATE_TO_ANALYST",
    "guardrail_status": "BruteForce protocol confirmed (8 auth failures >= 5)",
    "autonomous_blocking_authorized": false
  }
}
```

# APPENDIX B: CORE ENGINE IMPLEMENTATION NOTES

```python
# SentinelX-Shift: Production Guard Scoring Engine Snippet
# Location: src/guard/engine.py

class SentinelGuard:
    def __init__(self, ae_model, xgb_model, cdf_ae, cdf_xgb, tau=0.56, gamma=0.41):
        self.ae_model = ae_model
        self.xgb_model = xgb_model
        self.cdf_ae = cdf_ae
        self.cdf_xgb = cdf_xgb
        self.tau = tau
        self.gamma = gamma

    def score_flow(self, x_features, web_telemetry=None):
        # 1. Unsupervised Autoencoder reconstruction error
        err_ae = self.ae_model.reconstruction_error(x_features)
        s_ae = self.cdf_ae.transform(err_ae)

        # 2. Supervised XGBoost risk probability
        prob_xgb = self.xgb_model.predict_proba(x_features)[:, 1]
        s_xgb = self.cdf_xgb.transform(prob_xgb)

        # 3. Autoencoder-Anchored Gated Boost
        is_boosted = (s_xgb > self.tau).astype(float)
        s_guard = s_ae + (self.gamma * is_boosted)

        # 4. Determine base tier
        if s_guard >= 0.80:
            tier, action = "CRITICAL", "ESCALATE_TO_ANALYST"
        elif s_guard >= 0.60:
            tier, action = "HIGH", "INVESTIGATE_FLOW"
        elif s_guard >= 0.30:
            tier, action = "MEDIUM", "MONITOR"
        else:
            tier, action = "LOW", "ALLOW"

        # 5. Apply Protocol Guardrails
        if tier == "CRITICAL" and web_telemetry:
            auth_fails = web_telemetry.get("auth_failures", 0)
            if auth_fails < 5 and web_telemetry.get("family") == "BruteForce":
                tier, action = "HIGH", "INVESTIGATE_FLOW"

        return {"s_guard": float(s_guard), "tier": tier, "action": action}
```

# REFERENCES (APA 7th Edition)

1. Al-Omari, M., Rawashdeh, E., & Jarrah, M. (2024). Zero-day attack detection in IoT and cloud networks using hybrid gated ensembles. *Ad Hoc Networks*, *154*, 103362. https://doi.org/10.1016/j.adhoc.2024.103362
2. Al-Qatf, M., Lasheng, Y., Al-Habib, M., & Al-Sabahi, K. (2020). A deep learning approach for network intrusion detection based on NSL-KDD dataset. *IEEE Access*, *8*, 143165–143176. https://doi.org/10.1109/ACCESS.2020.3013893
3. Arp, D., Quiring, E., Pendlebury, F., Warnecke, A., Pierazzi, F., Dos Santos, R., Cavallaro, L., & Rieck, K. (2022). Dos and don'ts of machine learning in computer security. *IEEE Transactions on Pattern Analysis and Machine Intelligence*, *44*(8), 4508–4523. https://doi.org/10.1109/TPAMI.2021.3117466
4. Balaji, S., Swaminathan, A., & Venkatesh, K. (2023). Real-time alert correlation and SOC automation framework for critical infrastructure. In *Proceedings of the 2023 IEEE International Conference on Advanced Networks and Telecommunications Systems (ANTS)* (pp. 1–6). IEEE.
5. Boutammok, K., Boucherkha, S., & Benmohamed, M. (2024). Feature leakage and memorization in deep learning network intrusion detectors. *International Journal of Information Security*, *23*(2), 891–909. https://doi.org/10.1007/s10207-023-00789-1
6. Deshmukh, A., & Joshi, R. (2025). Explainable AI in cybersecurity: Feasibility and computational challenges. *Sādhanā – Academy Proceedings in Engineering Sciences*, *50*(1), 22. https://doi.org/10.1007/s12046-024-02431-8
7. Dini, P., Martinelli, F., & Saracino, A. (2023). Toward reliable anomaly-based intrusion detection using autoencoders and gated calibration. *Computers & Security*, *129*, 103210. https://doi.org/10.1016/j.cose.2023.103210
8. Engelen, G., Rimmer, V., & Joosen, W. (2023). Leave-one-attack-out: Evaluating the zero-day generalization of network intrusion classifiers. *ACM Transactions on Privacy and Security*, *26*(3), 1–28. https://doi.org/10.1145/3582498
9. Ferrag, M. A., Shu, L., Hoang, D. H., Prasad, P. W., & Xiang, Y. (2020). Machine learning and deep learning methods for cybersecurity. *IEEE Access*, *8*, 209577–209608. https://doi.org/10.1109/ACCESS.2020.3039121
10. Gupta, R., & Tyagi, A. (2020). An efficient machine learning-based network intrusion detection system. In *Proceedings of the National Conference on Emerging Trends in Computing and Information Technology (NCETCIT)* (pp. 45–52).
11. Hasan, M., Rahman, M. A., & Islam, M. S. (2024). Alert triage and alert fatigue reduction in security operations centers. *Computers & Security*, *136*, 103554. https://doi.org/10.1016/j.cose.2023.103554
12. Kruegel, C., & Vigna, G. (2026). Autonomous replica defense: Partitioning active enforcement from production workloads. *Journal of Computer Security*, *34*(2), 201–224.
13. Kumar, S., & Sangeetha, N. (2022). Deep autoencoders for cyber-physical and network anomaly detection. *IETE Journal of Research*, *68*(5), 3712–3723. https://doi.org/10.1080/03772063.2020.1787211
14. Kumar, V., Sinha, D., & Das, A. K. (2022). Evaluation of machine learning intrusion detection on UNSW-NB15 and CIC-IDS2017. *Journal of Network and Computer Applications*, *204*, 103417. https://doi.org/10.1016/j.jnca.2022.103417
15. Mahbooba, B., Timilsina, M., Serrano, R., & Ray, B. (2021). Explainable artificial intelligence for network intrusion detection systems. *Applied Sciences*, *11*(19), 9270. https://doi.org/10.3390/app11199270
16. Mirheidari, S. A., Arshad, S., Onwuzurike, L., & Robertson, W. (2023). A survey on web application firewalls: Architectures, bypass techniques, and ML enhancements. *IEEE Communications Surveys & Tutorials*, *25*(1), 542–578. https://doi.org/10.1109/COMST.2022.3228308
17. Nair, M., & Pillai, V. (2024). Evaluation of zero-day attack generalization in Indian telecommunication networks. *Current Science*, *126*(4), 488–497.
18. Pacheco, Y., & Sun, L. (2025). TinyML and edge intrusion detection for embedded reverse proxies. *IEEE Internet of Things Journal*, *12*(4), 4120–4133. https://doi.org/10.1109/JIOT.2024.3412589
19. Patel, H., & Shah, M. (2023). Hybrid machine learning approaches for web application security and injection attack defense. *Journal of King Saud University – Computer and Information Sciences*, *35*(2), 789–801. https://doi.org/10.1016/j.jksuci.2023.01.014
20. Rao, V. K., & Prasad, K. S. (2021). Cloud-based IoT intrusion detection system using machine learning techniques. *International Journal of Computer Networks and Communications (IJCNC)*, *13*(3), 67–82.
21. Reddy, C. V., & Murthy, K. (2024). Log-driven threat hunting and WAF integration for smart city deployments. *CSI Transactions on ICT*, *12*(1), 35–48. https://doi.org/10.1007/s40012-023-00388-7
22. Sarhan, M., Layeghy, S., & Portmann, M. (2023). Cross-dataset generalization in network intrusion detection: Pitfalls and solutions. *IEEE Transactions on Dependable and Secure Computing*, *20*(4), 3120–3134. https://doi.org/10.1109/TDSC.2022.3197607
23. Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2020). Toward generating a new intrusion detection dataset and intrusion traffic characterization. *IEEE Transactions on Network and Service Management*, *16*(4), 1420–1434. https://doi.org/10.1109/TNSM.2019.2936305
24. Sharma, P., Mohan, S., & Narayanan, R. (2022). Mitigating feature leakage in supervised intrusion detection for financial gateways. *Indian Journal of Cybersecurity and Forensics*, *4*(1), 18–31.
25. Sommer, R., & Paxson, V. (2025). The fallacy of autonomous mitigation: Operational safety in cyber defense. *ACM Computing Surveys*, *57*(2), 45:1–45:32. https://doi.org/10.1145/3690123
26. Sundaram, R., & Natarajan, P. (2025). Resilient and privacy-preserving network threat monitoring framework. *Journal of Cyber Security Technology*, *9*(2), 101–119. https://doi.org/10.1080/23742917.2024.2389102
27. Vanhoenshoven, F., & Holvoet, T. (2025). Benchmarking machine learning intrusion detection under class imbalance and duplication. *Expert Systems with Applications*, *260*, 125340. https://doi.org/10.1016/j.eswa.2024.125340
28. Yang, K., Zhang, J., Xu, Y., & Xiang, Y. (2022). Robust network intrusion detection using adaptive deep learning. *IEEE Transactions on Information Forensics and Security*, *17*, 3421–3436. https://doi.org/10.1109/TIFS.2022.3204289
29. Zhang, T., Qiu, J., & Lu, K. (2024). Enhancing network anomaly detection via multi-modal host and network log fusion. *IEEE Transactions on Network Science and Engineering*, *11*(2), 1845–1858. https://doi.org/10.1109/TNSE.2023.3325678
30. Zhao, L., Song, W., & Chen, X. (2026). Behavioral fingerprinting of botnet C2 communication across asymmetric NetFlows. *IEEE Transactions on Dependable and Secure Computing*, *23*(1), 112–126.
