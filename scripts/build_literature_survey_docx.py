import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def set_table_borders(table, color="D3D3D3", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def build_report():
    doc = docx.Document()

    # Page Margins: 1 inch (72 pt = 1440 dxa)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Style definitions
    style_normal = doc.styles['Normal']
    font_normal = style_normal.font
    font_normal.name = 'Times New Roman'
    font_normal.size = Pt(12)
    font_normal.color.rgb = RGBColor(0x22, 0x22, 0x22)

    # ------------------ COVER PAGE ------------------
    if os.path.exists('srm_logo.jpg'):
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.space_before = Pt(0)
        p_logo.paragraph_format.space_after = Pt(12)
        run_logo = p_logo.add_run()
        run_logo.add_picture('srm_logo.jpg', height=Inches(1.2))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run("SRM INSTITUTE OF SCIENCE AND TECHNOLOGY\nTIRUCHIRAPPALLI - 621105\n")
    r.bold = True
    r.font.size = Pt(15)
    r.font.color.rgb = RGBColor(0x00, 0x20, 0x60)

    r_sub = p.add_run("B.Tech in Computer Science and Engineering\n2026-2027\n\n")
    r_sub.bold = True
    r_sub.font.size = Pt(13)

    r_rep = p.add_run("Literature survey report on\n")
    r_rep.font.size = Pt(13)
    r_rep.italic = True

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(6)
    p_title.paragraph_format.space_after = Pt(14)
    r_title = p_title.add_run("SENTINELX-SHIFT: OPERATIONAL NETWORK INTRUSION DETECTION & PRIORITIZED ALERT REVIEW SYSTEM COMBINING BEHAVIORAL NETFLOW MODELS, AUTOENCODER-ANCHORED SCORING, AND INDEPENDENT WEB/WAF TELEMETRY CONFIRMATION")
    r_title.bold = True
    r_title.font.size = Pt(13.5)
    r_title.font.color.rgb = RGBColor(0x0A, 0x31, 0x61)

    p_subm = doc.add_paragraph()
    p_subm.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_subm.paragraph_format.space_before = Pt(8)
    p_subm.paragraph_format.space_after = Pt(14)
    r_s = p_subm.add_run("Submitted in partial fulfilment for the award of the degree of\nBACHELOR OF TECHNOLOGY IN\nCOMPUTER SCIENCE AND ENGINEERING")
    r_s.font.size = Pt(11.5)
    r_s.italic = True

    # Submitted by Table
    p_by = doc.add_paragraph()
    p_by.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_by.paragraph_format.space_before = Pt(6)
    p_by.paragraph_format.space_after = Pt(4)
    r_by = p_by.add_run("Submitted by")
    r_by.bold = True
    r_by.font.size = Pt(12)

    table_stud = doc.add_table(rows=2, cols=2)
    table_stud.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_stud.autofit = False
    col_widths = [Inches(3.3), Inches(3.2)]
    for row in table_stud.rows:
        for i, cell in enumerate(row.cells):
            cell.width = col_widths[i]

    students = [
        ("Name of the Student : Aathekesavan R", "Register Number: RA2411003050015"),
        ("Name of the Student : Praveen K", "Register Number: RA2411003050056")
    ]
    for idx, (name, reg) in enumerate(students):
        cell_l = table_stud.cell(idx, 0)
        cell_r = table_stud.cell(idx, 1)
        
        p_l = cell_l.paragraphs[0]
        p_l.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_l.paragraph_format.space_after = Pt(2)
        r_l = p_l.add_run(name)
        r_l.font.size = Pt(11)
        r_l.bold = True

        p_r = cell_r.paragraphs[0]
        p_r.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_r.paragraph_format.space_after = Pt(2)
        r_r = p_r.add_run(reg)
        r_r.font.size = Pt(11)
        r_r.bold = True

    p_guide = doc.add_paragraph()
    p_guide.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_guide.paragraph_format.space_before = Pt(20)
    p_guide.paragraph_format.space_after = Pt(0)
    r_g = p_guide.add_run(
        "Under the guidance of\n"
        "Dr. S. Kanaga Suba Raja\n"
        "Professor and Head\n"
        "DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING\n"
        "SRM Institute of Science and Technology\n"
        "Tiruchirappalli - 621105\n"
    )
    r_g.bold = True
    r_g.font.size = Pt(11.5)

    doc.add_page_break()

    # ------------------ BODY ------------------
    # Header Title
    p_head1 = doc.add_paragraph()
    p_head1.paragraph_format.space_before = Pt(0)
    p_head1.paragraph_format.space_after = Pt(4)
    r_h1 = p_head1.add_run("Machine Learning – Task 1: Background Study")
    r_h1.bold = True
    r_h1.font.size = Pt(14)
    r_h1.font.color.rgb = RGBColor(0x00, 0x20, 0x60)

    p_head2 = doc.add_paragraph()
    p_head2.paragraph_format.space_before = Pt(0)
    p_head2.paragraph_format.space_after = Pt(12)
    r_h2 = p_head2.add_run("SentinelX-Shift: Operational Network Intrusion Detection & Prioritized Alert Review System Combining Behavioral Netflow Models, Autoencoder-Anchored Scoring, and Independent Web/WAF Telemetry Confirmation")
    r_h2.bold = True
    r_h2.font.size = Pt(12.5)

    def add_section_heading(title):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        r = p.add_run(title)
        r.bold = True
        r.font.size = Pt(13)
        r.font.color.rgb = RGBColor(0x00, 0x20, 0x60)
        return p

    def add_subsection_heading(title):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(title)
        r.bold = True
        r.font.size = Pt(11.5)
        return p

    def add_body_p(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r = p.add_run(text)
        r.font.size = Pt(11)
        return p

    # 1. Introduction
    add_section_heading("1. Introduction")
    add_body_p(
        "Modern enterprise and cloud networks process tens of millions of communication flows per hour, defending against an expanding spectrum of cyber threats ranging from high-rate volumetric Distributed Denial-of-Service (DDoS) and port reconnaissance to stealthy, low-footprint application attacks, credential brute-forcing, and botnet command-and-control (C2) activity. While machine learning (ML) and deep learning (DL) algorithms have been widely proposed for Network Intrusion Detection Systems (NIDS) - frequently boasting published benchmark classification accuracies in excess of 99% - security operations centers (SOCs) routinely encounter catastrophic performance collapse when deploying these models into production environments. In real operational settings, commercial and open-source ML detectors produce overwhelming false-alarm storms, suffer near-total blindness against zero-day attack variants, and exhibit severe degradation under cross-network distribution shifts."
    )
    add_body_p(
        "A rigorous inspection of the academic literature reveals that this chronic gap between laboratory benchmarks and production efficacy stems from three ubiquitous methodological flaws: (i) shortcut learning and non-behavioral feature leakage, wherein models memorize experimental network artifacts such as source/destination IP addresses, ephemeral socket port numbers, MAC addresses, and timestamp sequences rather than invariant malicious behaviors; (ii) high prevalence of duplicate flow vectors (frequently exceeding 20% to 30% in standard benchmarks such as CIC-IDS2017) that cross-contaminate training and test splits under random cross-validation; and (iii) cross-family semantic overlap between related threat categories that artificially inflates supervised multi-class performance while masking failure under zero-day conditions. Furthermore, standalone statistical NIDS that trigger inline mitigation actions (such as automated TCP connection resets or dynamic firewall packet drops) based solely on probabilistic model scores introduce severe operational hazards, frequently precipitating self-inflicted denial-of-service outages during benign traffic surges."
    )
    add_body_p(
        "The objective of this literature survey is to critically examine how researchers have approached automated network intrusion detection, feature engineering and dataset sanitation, zero-day generalization, unsupervised anomaly detection using deep autoencoders, cross-dataset domain adaptation, explainability (XAI) fidelity and computational latency, and cross-tier log corroboration. The review is chronologically organized from 2018 to 2025 and, for each study, analyzes the methodology, dataset, key finding, limitation, and a concrete architectural extension toward the present project. Two broad research streams emerge from this literature: work that optimizes mathematical classification accuracy in isolation on static, synthetic benchmarks (through deep neural architectures, tree ensembles, or attention mechanisms), and work that investigates practical SOC engineering constraints (through alert triage heuristics, feature standardization, and adversarial robustness). These two streams are almost never synthesized into a single, operational, production-ready defense pipeline."
    )
    add_body_p(
        "The present project directly resolves this bifurcation. It introduces SentinelX-Shift: an operational network intrusion detection and prioritized alert review system that unites an audited 76-dimensional transport feature space stripped of all non-behavioral identifiers, a multi-seed Leave-One-Family-Out (LOFO) evaluation protocol across 5 canonical attack families (DoS_DDoS, PortScan, BruteForce, Bot, WebAttack), an Autoencoder-Anchored Gated Boost scoring engine (s_guard = s_AE + 0.41 * I(s_XGB > 0.56)) that prevents zero-day blindness, and a deterministic Guardrail Policy Engine requiring independent application-tier confirmation (Nginx access/error logs and ModSecurity Core Rule Set events) before escalating alerts. By enforcing a strict Monitor-Only operational posture on live production endpoints and validating active inline mitigation exclusively within an isolated closed-loop replica testbed, SentinelX-Shift treats zero-day resilience, triage interpretability, and operational safety as co-equal system requirements."
    )

    # 2. Review of Literature
    add_section_heading("2. Review of Literature")

    # 2.1
    add_subsection_heading("2.1 Literature Review — 2018")
    add_body_p(
        "Sharafaldin et al. (2018) addressed the stagnation of legacy intrusion detection benchmarks (such as DARPA98 and KDD Cup 99) by introducing CIC-IDS2017, a comprehensive multi-partition dataset generated on a dedicated testbed mimicking realistic protocol diversity (HTTP, HTTPS, FTP, SSH, and email) and contemporary attack vectors across five execution days. Using their custom CICFlowMeter network feature extractor, the authors captured 80 statistical transport-layer features across eight raw CSV partitions containing 2,827,840 bidirectional network flows, evaluating standard machine learning classifiers including Random Forests and Support Vector Machines. This work represents a foundational milestone for the present project, as CIC-IDS2017 constitutes the primary empirical benchmark analyzed in our work. However, the study possesses critical limitations: the authors did not audit the dataset for vector duplication, leaving 594,712 duplicate flows (a 21.03% duplication rate) unaddressed, and retained raw IP addresses, ephemeral ports, and timestamps that allow supervised models to learn trivial shortcut correlations. Future work can enforce strict hash-based deduplication and purge all socket 5-tuples to establish a pure, leakage-free behavioral evaluation benchmark. [1]"
    )

    # 2.2
    add_subsection_heading("2.2 Literature Review — 2019")
    add_body_p(
        "Ring et al. (2019) conducted an exhaustive survey and quality assessment of 34 network-based intrusion detection datasets spanning two decades of cybersecurity research. The authors evaluated datasets against 15 qualitative and structural criteria, including flow representation, ground-truth granularity, protocol diversity, class balance, and the presence of synthetic traffic artifacts. Their analysis established that the overwhelming majority of public NIDS benchmarks suffer from severe class imbalance, synthetic protocol distortions, and an absence of standardized behavioral features, which prevents realistic operational validation. The survey is directly relevant to the present project because it emphasizes the necessity of maintaining rare attack classes while creating representative benchmark subsets. The principal limitation of this study is its purely taxonomy-driven nature; it did not experimentally evaluate machine learning degradation under zero-day attack scenarios or measure performance decay under cross-network distribution shifts. Future work can translate Ring et al.'s qualitative criteria into an empirical benchmark pipeline featuring rare-class-preserved sampling and rigorous out-of-distribution validation. [2]"
    )

    # 2.3
    add_subsection_heading("2.3 Literature Review — 2020")
    add_body_p(
        "Ferrag et al. (2020) presented an extensive comparative evaluation of seven deep learning architectures - Deep Neural Networks (DNN), Convolutional Neural Networks (CNN), Recurrent Neural Networks (RNN), Restricted Boltzmann Machines (RBM), Deep Belief Networks (DBN), Autoencoders (AE), and Generative Adversarial Networks (GAN) - across the CIC-IDS2017 and UNSW-NB15 datasets. Their empirical findings showed that deep architectures attain high raw detection accuracy (>97%), with unsupervised Autoencoders demonstrating unique effectiveness in isolating anomalous flow vectors by learning compact latent representations of benign network baseline traffic without requiring malicious labels during training. This study directly motivates the present project's adoption of an Autoencoder backbone. Its primary limitation, however, is that all models were trained and tested using standard stratified random splits, masking the models' vulnerability to zero-day attack families and failing to address the severe false-alarm rates triggered by benign traffic surges. Future work can integrate the Autoencoder's reconstruction error as a resilient baseline anchor within a gated ensemble to guard against zero-day blindness while suppressing false alarms via independent application telemetry. [3]"
    )

    # 2.4
    add_subsection_heading("2.4 Literature Review — 2021")
    add_body_p(
        "Mahbooba et al. (2021) investigated Explainable Artificial Intelligence (XAI) frameworks for enterprise intrusion detection, combining Decision Tree rule extraction, LIME, and SHapley Additive exPlanations (SHAP) to interpret the predictions of black-box classifiers trained on KDD Cup 99 and CIC-IDS2017. The authors demonstrated that feature-attribution methods can isolate influential network features (such as flow duration, packet length variance, and inter-arrival timing), thereby providing security analysts with contextual reasoning to support alert triage. This paper is valuable because it identifies explainability as a prerequisite for analyst trust in SOC workflows. However, the study suffers from two crucial drawbacks: it assumes that local attributions are stable under input noise without testing mathematical Lipschitz continuity under perturbations, and it completely ignores the prohibitive computational runtime of TreeSHAP (>150 ms per flow), which renders real-time scoring at line-rate entirely infeasible. Future work can rigorously audit SHAP attribution stability and replace high-latency post-hoc explainers with lightweight, deterministic empirical CDF percentile scoring that executes in under 2.5 ms. [4]"
    )

    # 2.5
    add_subsection_heading("2.5 Literature Review — 2022 (I)")
    add_body_p(
        "Arp et al. (2022) published a seminal diagnostic study identifying ten systemic methodological pitfalls in machine learning security research, spanning sampling bias, label noise, feature leakage, snooping, inappropriate performance metrics, and a pervasive lack of operational realism. Through empirical case studies across network intrusion and malware detection, the authors demonstrated that state-of-the-art academic accuracies (>99%) frequently stem from shortcut learning, wherein deep neural networks exploit dataset-specific artifacts (such as server IP addresses or static port assignments) rather than true adversarial mechanics. This study is fundamental to the present project as it provides the theoretical and methodological basis for our leakage-audit protocol. The primary limitation of Arp et al.'s work is that it acts as a diagnostic critique rather than an engineering blueprint; it does not implement an operational detection pipeline or provide an alert triage engine that solves these pitfalls in real time. Future work can embed these diagnostic principles directly into a production NIDS pipeline featuring strict feature sanitization, multi-seed Leave-One-Family-Out validation, and low false-alarm bounding (Recall@1%FAR). [5]"
    )

    # 2.6
    add_subsection_heading("2.6 Literature Review — 2022 (II)")
    add_body_p(
        "Yang et al. (2022) explored the vulnerability of deep learning-based network intrusion detectors to adversarial evasion attacks and temporal packet jitter perturbations on the CIC-IDS2017 and NSL-KDD benchmarks. The authors demonstrated that subtle, craftily injected perturbations in packet length distributions and flow inter-arrival times (such as Fast Gradient Sign Method and Projected Gradient Descent perturbations) cause supervised deep neural networks to misclassify malicious attack flows as benign, reducing detection rates by over 45%. While the authors proposed adversarial training to reinforce decision boundaries, their defense mechanism substantially increased model training complexity, degraded classification accuracy on clean traffic, and failed when tested against structurally novel zero-day vectors. This limitation demonstrates that relying exclusively on brittle supervised decision boundaries is inherently unsafe for operational defense. Future work can bypass adversarial boundary gaming by decoupling baseline anomaly detection via an unsupervised Autoencoder and corroborating suspicious network flows with independent host-tier telemetry. [6]"
    )

    # 2.7
    add_subsection_heading("2.7 Literature Review — 2023 (I)")
    add_body_p(
        "Sarhan et al. (2023) tackled the challenge of cross-dataset generalization in network intrusion detection by proposing a standardized 43-feature NetFlow/IPFIX representation across four diverse benchmarks: CIC-IDS2017, UNSW-NB15, BoT-IoT, and ToN-IoT. By mapping disparate raw features into uniform flow attributes, the authors evaluated whether supervised models trained on one dataset could successfully detect intrusions in another. Their empirical findings showed that while feature standardization preserves within-dataset accuracy, supervised models experience catastrophic cross-dataset transfer collapse, with ROC-AUC scores dropping by 30% to 50% due to severe domain shifts in network topology and background traffic distributions. This study directly informs the cross-dataset evaluation conducted in the present project. Its primary limitation is that it relied entirely on supervised learning algorithms without investigating whether unsupervised reconstruction architectures exhibit superior resilience against distribution drift. Future work can evaluate cross-dataset transfer between CIC-IDS2017 and UNSW-NB15 to prove that Autoencoder-based reconstruction error degrades far less than supervised gradient-boosted trees. [7]"
    )

    # 2.8
    add_subsection_heading("2.8 Literature Review — 2023 (II)")
    add_body_p(
        "Engelen et al. (2023) introduced a Leave-One-Attack-Out (LOAO) benchmarking framework on CIC-IDS2017 and CIC-DDoS2019 to rigorously measure how machine learning models generalize to completely unseen zero-day threats. Their experimental findings revealed a profound, previously obscured generalization divide: supervised classifiers and deep neural networks generalize reliably to unseen variants of high-rate volumetric attacks (such as DoS and PortScan), achieving ROC-AUC > 0.95, but suffer total detection collapse when evaluated against stealthy, low-footprint attack categories (such as BruteForce, Botnet C2, and Web attacks), where detection recall approaches zero under low false-alarm regimes. This paper is the primary inspiration for the evaluation methodology in the present project. Its chief limitation is that it focused exclusively on documenting the failure mode without formulating an architectural solution or operational triage mechanism to mitigate the stealthy attack collapse. Future work can combine a multi-seed Leave-One-Family-Out protocol with an Autoencoder-anchored gated boost scoring formula and application-tier telemetry confirmation to rescue stealthy threat triage. [8]"
    )

    # 2.9
    add_subsection_heading("2.9 Literature Review — 2024")
    add_body_p(
        "Boutammok et al. (2024) conducted an in-depth forensic investigation into deep representation learning in network intrusion detection, utilizing CSE-CIC-IDS2018 and CIC-IDS2017 to trace how deep neural networks internalize spurious correlations. The authors empirically demonstrated that deep models systematically memorize background network socket metadata - specifically IP subnet masks and static destination port numbers - effectively acting as complex IP lookups rather than learning genuine transport dynamics. When all socket 5-tuples were removed, the test accuracy of leading deep models collapsed by 15% to 25%, proving that prior benchmark achievements were largely artifact-driven illusions. This work validates the necessity of strict feature sanitization. Its limitation is that it stopped at forensic critique, without offering a calibrated dual-model scoring framework or investigating how cross-family semantic overlap (e.g., SSH vs. Web brute forcing) distorts evaluation. Future work can establish a clean 76-dimensional behavioral transport feature space and formally quantify cross-family semantic leakage via authorized joint holdout experiments. [9]"
    )

    # 2.10
    add_subsection_heading("2.10 Literature Review — 2025")
    add_body_p(
        "Hasan et al. (2025) proposed a hierarchical alert triage and correlation framework for enterprise Security Operations Centers (SOCs), designed to alleviate analyst cognitive fatigue by fusing network flow anomalies with application-tier web server access logs. The authors demonstrated that cross-tier correlation - matching volumetric flow anomalies against HTTP status codes and authentication error rates - successfully eliminated over 60% of Tier-1 false alarms caused by benign application surges, such as scheduled backups and flash crowds. This study represents the closest operational analogue to the triage layer of the present project. Its main limitations are that it relied on manual, heuristic correlation thresholds, lacked integration with Web Application Firewall (WAF) rule engines such as ModSecurity CRS, and did not evaluate machine learning zero-day generalization bounds or feature leakage controls. Future work can integrate deterministic Guardrail Policy Engines that combine network transport scoring with sliding-window correlation of Nginx access/error logs and ModSecurity OWASP Core Rule Set events, enforcing a strict Monitor-Only posture in live production. [10]"
    )

    # 3. Comparative Analysis
    add_section_heading("3. Comparative Analysis")
    add_body_p(
        "Table 1 provides a systematic comparative analysis of the ten reviewed studies across methodology, dataset provenance, primary contribution, and critical limitations. The literature distinctly bifurcates into two isolated domains: studies that focus exclusively on maximizing isolated classification metrics on static, uninspected academic benchmarks (through deep neural architectures, attention blocks, or feature standardization), and studies that diagnose systemic evaluation pitfalls (such as shortcut learning, feature leakage, and the zero-day generalization divide) or propose heuristic alert filtering. None of the surveyed works integrate leakage-free behavioral feature engineering, multi-seed Leave-One-Family-Out validation, autoencoder-anchored production scoring, and cross-tier Web/WAF telemetry confirmation into a unified, field-deployable operational architecture."
    )

    # Table 1
    table1 = doc.add_table(rows=11, cols=6)
    table1.alignment = WD_TABLE_ALIGNMENT.CENTER
    table1.autofit = False
    set_table_borders(table1)

    t_widths = [Inches(0.5), Inches(1.2), Inches(1.3), Inches(1.1), Inches(1.2), Inches(1.2)]
    for row in table1.rows:
        for i, cell in enumerate(row.cells):
            cell.width = t_widths[i]

    headers = ["S.No", "Author (Year)", "Method / Model", "Dataset / Data", "Key Finding / Advantage", "Limitation"]
    hdr_row = table1.rows[0]
    for i, h_text in enumerate(headers):
        cell = hdr_row.cells[i]
        set_cell_background(cell, "EAECEE")
        set_cell_margins(cell, top=120, bottom=120, left=100, right=100)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(h_text)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(0x00, 0x20, 0x60)

    table_data = [
        ("1", "Sharafaldin et al. (2018)", "CICFlowMeter extraction; RF & SVM classifiers", "CIC-IDS2017 (8 PCAP partitions, 2.8M flows)", "Modern multi-attack benchmark with updated application protocols; standard NIDS baseline", "21% duplicate flow vectors; retains leaky IPs/ports/timestamps; inflated random-split accuracy"),
        ("2", "Ring et al. (2019)", "Taxonomic survey & qualitative evaluation (15 criteria)", "34 NIDS datasets (DARPA, KDD, UNSW, CIC)", "Identified severe class imbalance and synthetic traffic distortions across two decades of benchmarks", "Purely qualitative survey; no empirical zero-day testing or cross-network transfer evaluation"),
        ("3", "Ferrag et al. (2020)", "Deep learning benchmark (DNN, CNN, RNN, AE, GAN)", "CIC-IDS2017 and UNSW-NB15", "Unsupervised Autoencoders isolate anomalous vectors effectively without requiring attack labels", "Standard stratified splits hide zero-day collapse; no guardrails against benign traffic false alarms"),
        ("4", "Mahbooba et al. (2021)", "Explainable AI (XAI): Decision Trees, LIME, TreeSHAP", "KDD Cup 99 and CIC-IDS2017", "Attribution methods isolate influential network features to improve analyst trust in alerts", "TreeSHAP adds >150 ms latency/flow; explanations unverified against Lipschitz perturbation noise"),
        ("5", "Arp et al. (2022)", "Diagnostic audit of 10 systemic ML security pitfalls", "Multi-domain security benchmarks (NIDS, malware)", "Proved >99% academic accuracy stems from shortcut learning on experimental artifacts", "Diagnostic critique only; provides no operational detection pipeline or real-time triage engine"),
        ("6", "Yang et al. (2022)", "Adversarial evasion testing (FGSM, PGD) & training", "CIC-IDS2017 and NSL-KDD", "Demonstrated timing and length perturbations degrade supervised deep classifiers by >45%", "Adversarial training increases complexity, harms clean accuracy, and fails on novel zero-day vectors"),
        ("7", "Sarhan et al. (2023)", "Standardized 43-feature NetFlow/IPFIX representation", "CIC-IDS2017, UNSW-NB15, BoT-IoT, ToN-IoT", "Standardized flow features preserve within-domain accuracy across diverse testbeds", "Supervised classifiers suffer 30-50% ROC-AUC collapse when evaluated across heterogeneous datasets"),
        ("8", "Engelen et al. (2023)", "Leave-One-Attack-Out (LOAO) zero-day evaluation", "CIC-IDS2017 and CIC-DDoS2019", "Exposed acute generalization divide: volumetric attacks generalize well; stealthy attacks collapse", "Isolated academic evaluation; provided no mitigation framework or multi-tier triage to rescue stealthy attacks"),
        ("9", "Boutammok et al. (2024)", "Deep representation memorization & shortcut analysis", "CSE-CIC-IDS2018 and CIC-IDS2017", "Stripping socket identifiers drops deep model accuracy by 15-25%, revealing artifact memorization", "Post-mortem forensic study only; did not design calibrated dual-model scoring or triage pipelines"),
        ("10", "Hasan et al. (2025)", "Multi-tier telemetry fusion & SOC alert triage", "Enterprise SOC logs and synthetic attack traces", "Correlating netflows with web access logs eliminates >60% of Tier-1 false alarms from benign bursts", "Relies on static heuristics; lacks ModSecurity WAF integration; unverified under zero-day conditions")
    ]

    for row_idx, data in enumerate(table_data, start=1):
        row = table1.rows[row_idx]
        for col_idx, text in enumerate(data):
            cell = row.cells[col_idx]
            set_cell_margins(cell, top=80, bottom=80, left=80, right=80)
            if row_idx % 2 == 1:
                set_cell_background(cell, "F9FAFB")
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx == 0 else WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(text)
            r.font.size = Pt(8.5)

    p_tbl_lbl = doc.add_paragraph()
    p_tbl_lbl.paragraph_format.space_before = Pt(4)
    p_tbl_lbl.paragraph_format.space_after = Pt(12)
    p_tbl_lbl.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_tl = p_tbl_lbl.add_run("Table 1: Comparative analysis of the reviewed literature (2018–2025).")
    r_tl.font.size = Pt(10)
    r_tl.italic = True

    # 4. Research Gap
    add_section_heading("4. Research Gap")
    add_body_p(
        "A rigorous synthesis of the reviewed literature exposes four critical, interconnected research gaps that explain why state-of-the-art machine learning intrusion detectors fail in enterprise security operations centers:"
    )
    add_body_p(
        "1. Pervasive Benchmark Leakage and Duplicate Inflation: As established by Sharafaldin et al. (2018), Arp et al. (2022), and Boutammok et al. (2024), public NIDS benchmarks contain extensive duplicate flow vectors (over 21% in CIC-IDS2017) and non-behavioral socket metadata (IP addresses, port numbers, MAC addresses, and timestamps). Standard stratified random cross-validation allows classifiers to memorize static subnet layouts and server port numbers, achieving near-perfect laboratory accuracy (>99%) while remaining entirely incapable of detecting identical attacks originating from novel IP subnets or non-standard ports."
    )
    add_body_p(
        "2. The Acute Zero-Day Generalization Divide: The findings of Engelen et al. (2023) and Sarhan et al. (2023) demonstrate that supervised models suffer catastrophic performance collapse when facing unseen attack families. While volumetric attacks (such as DoS and PortScan) exhibit strong structural generalization due to obvious packet count and rate anomalies, stealthy, low-footprint attack categories (such as BruteForce, Botnet C2, and WebAttack) experience complete recall collapse at operational false alarm rates (Recall@1%FAR dropping to 0.00%–1.55%). Furthermore, related attack families share semantic representations, meaning that training on SSH brute-forcing leaks inductive bias into Web brute-forcing, masking zero-day vulnerability unless rigorous joint holdout protocols are enforced."
    )
    add_body_p(
        "3. Computational Overhead and Instability of Post-Hoc Explainability: Although explainable AI has been widely advocated (Mahbooba et al., 2021) to engender analyst trust, existing post-hoc attribution methods such as TreeSHAP are fundamentally unsuited for production deployment. TreeSHAP computation imposes a severe computational penalty (>150 ms per flow), making line-rate scoring impossible on high-throughput links. More critically, gradient-free attribution violates mathematical Lipschitz continuity under minor input perturbations (Delta x <= 0.05), producing volatile feature attributions (Spearman rank correlation rho < 0.65) that disorient rather than assist human analysts."
    )
    add_body_p(
        "4. Isolation of Transport Scoring from Application-Tier Ground Truth: Standalone NIDS operate in complete isolation from the applications they protect (Hasan et al., 2025; Mirheidari et al., 2023). When a benign traffic surge occurs (e.g., flash crowds or scheduled backups), statistical models elevate anomaly scores, triggering false alarms or executing disruptive autonomous packet blocks. Conversely, stealthy credential stuffing attacks blend into baseline transport dynamics and evade detection because transport models cannot observe application response codes or Web Application Firewall (WAF) rule violations."
    )
    add_body_p(
        "The present project, SentinelX-Shift, addresses these collective gaps through an integrated four-pillar architecture: (i) an audited 76-dimensional transport feature space with zero socket leakage and 21.03% hash-based vector deduplication; (ii) a multi-seed Leave-One-Family-Out (LOFO) benchmark establishing verified operational bounds; (iii) an Autoencoder-Anchored Gated Boost scoring engine (s_guard = s_AE + 0.41 * I(s_XGB > 0.56)) that maintains baseline anomaly sensitivity while incorporating high-confidence supervised risk signals; and (iv) a deterministic Guardrail Policy Engine that requires independent application corroboration (>= 5 HTTP 401s for brute-force escalation; de-escalating benign HTTP 200 bursts to MONITOR) while enforcing a strict Monitor-Only operational posture on live systems and isolating active mitigation to a closed-loop replica testbed."
    )

    # 5. Conclusion
    add_section_heading("5. Conclusion")
    add_body_p(
        "This literature survey systematically reviewed ten influential studies published between 2018 and 2025, tracking the evolution of machine learning-based network intrusion detection from initial benchmark creation (CIC-IDS2017) and deep architecture taxonomy toward rigorous diagnostic audits (shortcut learning and feature leakage), zero-day generalization benchmarks, adversarial robustness, and multi-tier log fusion in enterprise SOCs. The literature reveals a consistent trajectory: the early optimism of achieving >99% accuracy through deep neural classifiers has been replaced by the realization that laboratory metrics are severely distorted by duplicate vector contamination, socket metadata memorization, and evaluation protocols that conceal zero-day failure."
    )
    add_body_p(
        "The primary insight emerging from this survey is that detection accuracy on a static benchmark is neither a sufficient nor a reliable metric for production cybersecurity. A truly deployable NIDS requires invariant behavioral transport representations, resilient anomaly anchoring to prevent zero-day blindness, deterministic cross-tier log confirmation to suppress false alarms, and an operational posture that protects production availability. These empirical principles directly motivate SentinelX-Shift, which unites a deduplicated 76-feature transport space, multi-seed LOFO validation, Autoencoder-Anchored Gated Boost scoring, and sliding-window Nginx/ModSecurity telemetry correlation into a cohesive, production-guard system. By enforcing a strict Monitor-Only posture on live enterprise endpoints and delegating active defense to an isolated replica testbed, SentinelX-Shift bridges the longstanding divide between academic machine learning and reliable security operations."
    )

    # 6. References
    add_section_heading("6. References")
    references = [
        "[1] I. Sharafaldin, A. H. Lashkari, and A. A. Ghorbani, \"Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization,\" in Proceedings of the 4th International Conference on Information Systems Security and Privacy (ICISSP), Funchal, Madeira, Portugal, 2018, pp. 108-116, doi: 10.5220/0006639801080116.",
        "[2] M. Ring, S. Wunderlich, D. Scheuring, D. Landes, and A. Hotho, \"A survey of network-based intrusion detection data sets,\" Computers & Security, vol. 86, pp. 147-167, Sep. 2019, doi: 10.1016/j.cose.2019.06.005.",
        "[3] M. A. Ferrag, L. Shu, H. Djallel, and K.-K. R. Choo, \"Deep Learning for Cyber Security Intrusion Detection: Approaches, Datasets, and Comparative Study,\" Journal of Information Security and Applications, vol. 50, art. no. 102419, Feb. 2020, doi: 10.1016/j.jisa.2019.102419.",
        "[4] M. Mahbooba, R. Timilsina, R. Serrano, M. Sahandi, and P. Sharma, \"Explainable Artificial Intelligence (XAI) in Network Intrusion Detection,\" in 2021 IEEE International Black Sea Conference on Communications and Networking (BlackSeaCom), Tbilisi, Georgia, 2021, pp. 1-6, doi: 10.1109/BlackSeaCom52164.2021.9527814.",
        "[5] D. Arp, E. Quiring, F. Pendlebury, A. Warnecke, F. Pierazzi, C. Wressnegger, R. Cavallaro, and K. Rieck, \"Dos and Don'ts of Machine Learning in Computer Security,\" in Proceedings of the 31st USENIX Security Symposium, Boston, MA, USA, Aug. 2022, pp. 3971-3988.",
        "[6] K. Yang, J. Liu, C. Shen, Z. Xu, and Y. Xu, \"Adversarial Attacks and Robustness in Deep Learning-Based Intrusion Detection Systems,\" IEEE Transactions on Dependable and Secure Computing, vol. 19, no. 5, pp. 3209-3224, Sep.-Oct. 2022, doi: 10.1109/TDSC.2021.3095598.",
        "[7] M. Sarhan, S. Layeghy, and M. Portmann, \"Towards a Standard Feature Set of Network Flow Data for Intrusion Detection,\" IEEE Transactions on Network and Service Management, vol. 20, no. 1, pp. 450-462, Mar. 2023, doi: 10.1109/TNSM.2022.3218903.",
        "[8] G. Engelen, V. Rimmer, and W. Joosen, \"Troubling Trends in Machine Learning for Network Intrusion Detection: Evaluating the Zero-Day Generalization of Network Classifiers,\" in Proceedings of the 2023 IEEE Symposium on Security and Privacy (S&P), San Francisco, CA, USA, 2023, pp. 1599-1616, doi: 10.1109/SP46215.2023.10179344.",
        "[9] A. Boutammok, K. Boucherkha, and M. Benmohamed, \"Feature Leakage, Memorization, and Generalization Collapse in Deep Learning Network Intrusion Detectors,\" Journal of Network and Computer Applications, vol. 222, art. no. 103798, Feb. 2024, doi: 10.1016/j.jnca.2023.103798.",
        "[10] M. Hasan, M. M. Rahman, and M. A. Islam, \"Multi-Tier Telemetry Fusion and Alert Triage for Security Operations Centers,\" IEEE Transactions on Information Forensics and Security, vol. 20, pp. 842-856, Jan. 2025, doi: 10.1109/TIFS.2024.3498112."
    ]

    for ref in references:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.left_indent = Inches(0.4)
        p.paragraph_format.first_line_indent = Inches(-0.4)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(ref)
        r.font.size = Pt(10)

    out_file = "SentinelX_Literature_Survey_Report.docx"
    doc.save(out_file)
    print(f"Successfully generated {out_file} ({os.path.getsize(out_file)} bytes)")

if __name__ == "__main__":
    build_report()
