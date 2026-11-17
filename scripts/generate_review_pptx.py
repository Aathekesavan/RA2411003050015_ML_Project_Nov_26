import os
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_presentation(output_path):
    prs = Presentation()
    # Set slide dimensions to 16:9 widescreen (13.333 x 7.5 inches)
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    # Colors
    NAVY = RGBColor(15, 23, 42)       # Slate 900
    BLUE = RGBColor(30, 58, 138)      # Blue 900
    ACCENT_BLUE = RGBColor(37, 99, 235) # Blue 600
    CYAN = RGBColor(6, 182, 212)      # Cyan 500
    DARK_GRAY = RGBColor(51, 65, 85)  # Slate 700
    LIGHT_BG = RGBColor(248, 250, 252) # Slate 50
    CARD_BG = RGBColor(255, 255, 255)
    BORDER_COLOR = RGBColor(226, 232, 240)
    WHITE = RGBColor(255, 255, 255)
    GREEN = RGBColor(22, 101, 52)     # Green 800
    RED = RGBColor(153, 27, 27)       # Red 800

    blank_slide_layout = prs.slide_layouts[6]

    def add_header(slide, title_text, category_text="END SEMESTER PROJECT REVIEW"):
        # Header banner container
        header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(0.9))
        tf = header_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        
        # Category label
        p_cat = tf.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.name = 'Arial'
        p_cat.font.size = Pt(10)
        p_cat.font.bold = True
        p_cat.font.color.rgb = ACCENT_BLUE
        p_cat.space_after = Pt(2)
        
        # Title
        p_title = tf.add_paragraph()
        p_title.text = title_text
        p_title.font.name = 'Arial'
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = NAVY
        
        # Top accent bar
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.35), Inches(11.733), Inches(0.04))
        bar.fill.solid()
        bar.fill.fore_color.rgb = ACCENT_BLUE
        bar.line.fill.background()

    def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=BORDER_COLOR):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        if border_color:
            card.line.color.rgb = border_color
            card.line.width = Pt(1.5)
        else:
            card.line.fill.background()
        return card

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    s1 = prs.slides.add_slide(blank_slide_layout)
    
    # Left Hero Banner
    hero = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(4.8), Inches(7.5))
    hero.fill.solid()
    hero.fill.fore_color.rgb = NAVY
    hero.line.fill.background()
    
    # Hero text
    hero_box = s1.shapes.add_textbox(Inches(0.6), Inches(1.0), Inches(3.6), Inches(5.5))
    htf = hero_box.text_frame
    htf.word_wrap = True
    
    hp1 = htf.paragraphs[0]
    hp1.text = "SRM IST"
    hp1.font.name = 'Arial'
    hp1.font.size = Pt(14)
    hp1.font.bold = True
    hp1.font.color.rgb = CYAN
    hp1.space_after = Pt(8)
    
    hp2 = htf.add_paragraph()
    hp2.text = "End Semester Project Work Review"
    hp2.font.name = 'Arial'
    hp2.font.size = Pt(22)
    hp2.font.bold = True
    hp2.font.color.rgb = WHITE
    hp2.space_after = Pt(16)
    
    hp3 = htf.add_paragraph()
    hp3.text = "Department of Computer Science & Engineering\nTiruchirappalli Campus\nAcademic Year 2026 – 2027"
    hp3.font.name = 'Arial'
    hp3.font.size = Pt(12)
    hp3.font.color.rgb = RGBColor(203, 213, 225)
    hp3.space_after = Pt(28)

    # Right Content Area
    # Project Title Box
    title_box = s1.shapes.add_textbox(Inches(5.4), Inches(0.8), Inches(7.3), Inches(2.2))
    ttf = title_box.text_frame
    ttf.word_wrap = True
    
    tp1 = ttf.paragraphs[0]
    tp1.text = "SENTINELX-SHIFT"
    tp1.font.name = 'Arial'
    tp1.font.size = Pt(28)
    tp1.font.bold = True
    tp1.font.color.rgb = BLUE
    tp1.space_after = Pt(6)
    
    tp2 = ttf.add_paragraph()
    tp2.text = "Operational Network Intrusion Detection & Prioritized Alert Review System Combining Behavioral NetFlow Models, Autoencoder-Anchored Scoring, and Independent Web/WAF Telemetry Confirmation"
    tp2.font.name = 'Arial'
    tp2.font.size = Pt(13)
    tp2.font.color.rgb = DARK_GRAY
    
    # Metadata Cards
    add_card(s1, Inches(5.4), Inches(3.2), Inches(3.5), Inches(3.5))
    meta1 = s1.shapes.add_textbox(Inches(5.6), Inches(3.4), Inches(3.1), Inches(3.1))
    mtf1 = meta1.text_frame
    mtf1.word_wrap = True
    
    mp1 = mtf1.paragraphs[0]
    mp1.text = "PROJECT TEAM"
    mp1.font.size = Pt(11)
    mp1.font.bold = True
    mp1.font.color.rgb = ACCENT_BLUE
    mp1.space_after = Pt(12)
    
    mp2 = mtf1.add_paragraph()
    mp2.text = "AATHEKESAVAN R."
    mp2.font.size = Pt(13)
    mp2.font.bold = True
    mp2.font.color.rgb = NAVY
    
    mp3 = mtf1.add_paragraph()
    mp3.text = "Reg No: RA2411003050015\n"
    mp3.font.size = Pt(11)
    mp3.font.color.rgb = DARK_GRAY
    mp3.space_after = Pt(8)
    
    mp4 = mtf1.add_paragraph()
    mp4.text = "PRAVEEN K."
    mp4.font.size = Pt(13)
    mp4.font.bold = True
    mp4.font.color.rgb = NAVY
    
    mp5 = mtf1.add_paragraph()
    mp5.text = "Reg No: RA2411003050056"
    mp5.font.size = Pt(11)
    mp5.font.color.rgb = DARK_GRAY

    add_card(s1, Inches(9.2), Inches(3.2), Inches(3.5), Inches(3.5))
    meta2 = s1.shapes.add_textbox(Inches(9.4), Inches(3.4), Inches(3.1), Inches(3.1))
    mtf2 = meta2.text_frame
    mtf2.word_wrap = True
    
    gp1 = mtf2.paragraphs[0]
    gp1.text = "SUPERVISOR & GUIDE"
    gp1.font.size = Pt(11)
    gp1.font.bold = True
    gp1.font.color.rgb = ACCENT_BLUE
    gp1.space_after = Pt(12)
    
    gp2 = mtf2.add_paragraph()
    gp2.text = "Dr. S. KANAGA SUBA RAJA"
    gp2.font.size = Pt(13)
    gp2.font.bold = True
    gp2.font.color.rgb = NAVY
    
    gp3 = mtf2.add_paragraph()
    gp3.text = "Professor & Head of Department (CSE)\nSRM IST Tiruchirappalli\nEmail: hod.cse.try@srmist.edu.in"
    gp3.font.size = Pt(11)
    gp3.font.color.rgb = DARK_GRAY
    gp3.space_after = Pt(12)
    
    gp4 = mtf2.add_paragraph()
    gp4.text = "Review Date: Nov 12–13, 2026"
    gp4.font.size = Pt(11)
    gp4.font.bold = True
    gp4.font.color.rgb = GREEN

    # =========================================================================
    # SLIDE 2: Background & Context
    # =========================================================================
    s2 = prs.slides.add_slide(blank_slide_layout)
    add_header(s2, "The Crisis in Academic ML-NIDS vs. Enterprise SOC Deployment")
    
    # 3 Comparison Columns
    col_w = Inches(3.64)
    # Col 1: Academic Claims
    add_card(s2, Inches(0.8), Inches(1.6), col_w, Inches(5.3))
    tb1 = s2.shapes.add_textbox(Inches(1.0), Inches(1.8), col_w - Inches(0.4), Inches(4.9))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "Academic Benchmark Claims"
    p.font.bold = True
    p.font.size = Pt(14)
    p.font.color.rgb = BLUE
    p.space_after = Pt(12)
    
    points1 = [
        ("99%+ Accuracy Reported:", "Published papers on CIC-IDS2017 & NSL-KDD claim near-perfect intrusion classification."),
        ("Low Stated False Positives:", "Random 80/20 train-test splits report false alarm rates approaching 0%."),
        ("Supervised Over-Optimism:", "Standard k-fold cross-validation masks distribution shift and zero-day failures.")
    ]
    for h, b in points1:
        p = tf1.add_paragraph()
        p.text = f"• {h} {b}"
        p.font.size = Pt(11.5)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(10)

    # Col 2: SOC Reality
    add_card(s2, Inches(4.84), Inches(1.6), col_w, Inches(5.3))
    tb2 = s2.shapes.add_textbox(Inches(5.04), Inches(1.8), col_w - Inches(0.4), Inches(4.9))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "Enterprise SOC Reality"
    p.font.bold = True
    p.font.size = Pt(14)
    p.font.color.rgb = RED
    p.space_after = Pt(12)
    
    points2 = [
        ("Alert Fatigue & Storms:", "SOC analysts receive thousands of false-positive alarms daily from benign traffic spikes."),
        ("Zero-Day Brittleness:", "Minor syntax or behavioral shifts in attacks result in catastrophic detection collapse."),
        ("No Inline Autonomy:", "SOC directors strictly refuse automated packet dropping due to risk of self-inflicted outages.")
    ]
    for h, b in points2:
        p = tf2.add_paragraph()
        p.text = f"• {h} {b}"
        p.font.size = Pt(11.5)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(10)

    # Col 3: SentinelX Resolution
    add_card(s2, Inches(8.88), Inches(1.6), col_w, Inches(5.3), bg_color=RGBColor(240, 253, 250), border_color=CYAN)
    tb3 = s2.shapes.add_textbox(Inches(9.08), Inches(1.8), col_w - Inches(0.4), Inches(4.9))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    p = tf3.paragraphs[0]
    p.text = "SentinelX-Shift Resolution"
    p.font.bold = True
    p.font.size = Pt(14)
    p.font.color.rgb = GREEN
    p.space_after = Pt(12)
    
    points3 = [
        ("Strict Monitor-Only Posture:", "Live production networks are never autonomously blocked; triage is prioritized for human SOC review."),
        ("Dual-Engine Score Fusion:", "Unsupervised Autoencoder anchors novel anomaly detection; XGBoost gates known threat boosts."),
        ("Cross-Tier Telemetry:", "Combines NetFlow transport anomalies with Nginx reverse proxy and ModSecurity WAF audit logs.")
    ]
    for h, b in points3:
        p = tf3.add_paragraph()
        p.text = f"• {h} {b}"
        p.font.size = Pt(11.5)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(10)

    # =========================================================================
    # SLIDE 3: Problem Statement
    # =========================================================================
    s3 = prs.slides.add_slide(blank_slide_layout)
    add_header(s3, "Problem Statement: 4 Systemic Pathologies in NIDS")

    # 4 Grid Cards
    cards_info = [
        ("1. Shortcut Learning & Metadata Leakage", 
         "Standard pipelines retain IP addresses, ephemeral ports, and timestamps.\nGradient descent memorizes subnet addresses rather than generalizable packet dynamics.",
         Inches(0.8), Inches(1.6), Inches(5.6), Inches(2.5)),
        ("2. Massive Dataset Duplication (21.03%)", 
         "CIC-IDS2017 contains 594,712 exact duplicate flow vectors (21.03%) across 8 partitions.\nNaive random splits place identical vectors in train and test sets, reducing evaluation to database lookup.",
         Inches(6.8), Inches(1.6), Inches(5.6), Inches(2.5)),
        ("3. Cross-Family Semantic Bleed", 
         "Random k-fold validation blends sub-attack classes (e.g. SSH and Web BruteForce).\nModels appear accurate while failing completely when an entire attack family is withheld (zero-day test).",
         Inches(0.8), Inches(4.4), Inches(5.6), Inches(2.5)),
        ("4. Autonomous Action Hazards", 
         "Stand-alone statistical models making inline firewall decisions cause catastrophic denial-of-service against legitimate user surges (e.g., flash crowds or bulk backups).",
         Inches(6.8), Inches(4.4), Inches(5.6), Inches(2.5))
    ]
    
    for title, desc, left, top, width, height in cards_info:
        add_card(s3, left, top, width, height)
        tb = s3.shapes.add_textbox(left + Inches(0.2), top + Inches(0.2), width - Inches(0.4), height - Inches(0.4))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.bold = True
        p.font.size = Pt(13)
        p.font.color.rgb = NAVY
        p.space_after = Pt(8)
        
        p2 = tf.add_paragraph()
        p2.text = desc
        p2.font.size = Pt(11)
        p2.font.color.rgb = DARK_GRAY

    # =========================================================================
    # SLIDE 4: Objectives & Defensive Principles
    # =========================================================================
    s4 = prs.slides.add_slide(blank_slide_layout)
    add_header(s4, "Project Objectives & Core Defensive Principles")

    # Left: 4 Objectives
    add_card(s4, Inches(0.8), Inches(1.6), Inches(5.7), Inches(5.3))
    tb_obj = s4.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.3), Inches(4.9))
    tf_obj = tb_obj.text_frame
    tf_obj.word_wrap = True
    
    p = tf_obj.paragraphs[0]
    p.text = "Core Project Objectives"
    p.font.bold = True
    p.font.size = Pt(14)
    p.font.color.rgb = BLUE
    p.space_after = Pt(12)
    
    objs = [
        "Curate a Leakage-Free Benchmark: Ingest 2.8M flows, purge 594k duplicates (21.03%), and strip all environmental identifiers into 76 transport features.",
        "Leave-One-Family-Out (LOFO) Evaluation: Test zero-day detection resilience across 5 canonical families over 5 independent seeds (42, 101, 202, 303, 404).",
        "Formulate Autoencoder-Anchored Gated Boost: Anchor detection to reconstruction MSE to prevent zero-day blindness while boosting known attacks.",
        "Implement Multi-Tier Log Guardrails: Correlate NetFlow with Nginx & ModSecurity WAF logs in a ±30s window to de-escalate false positives."
    ]
    for o in objs:
        p = tf_obj.add_paragraph()
        p.text = f"✔ {o}"
        p.font.size = Pt(11)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(10)

    # Right: 5 Operational Principles
    add_card(s4, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3))
    tb_prin = s4.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
    tf_prin = tb_prin.text_frame
    tf_prin.word_wrap = True
    
    p = tf_prin.paragraphs[0]
    p.text = "Operational Defensive Principles"
    p.font.bold = True
    p.font.size = Pt(14)
    p.font.color.rgb = NAVY
    p.space_after = Pt(12)
    
    prins = [
        "Principle 1 (Strictly Monitor-Only): Live endpoints operate exclusively in monitor mode. Zero automated packet dropping on model scores alone.",
        "Principle 2 (Leakage-Free Protocol): All training strips IP, MAC, ports, and raw timestamps to ensure purely behavioral feature learning.",
        "Principle 3 (Independent Signal Confirmation): Stealthy attack escalation requires corroborating evidence (WAF alerts, repeated HTTP 401s).",
        "Principle 4 (Privacy Invariant): Full query strings and URL fragments are sanitized; request bodies and passwords are NEVER inspected or stored.",
        "Principle 5 (Traceability): Thread-safe SQLite review store maintains immutable triage audit records with short UUID badges."
    ]
    for pr in prins:
        p = tf_prin.add_paragraph()
        p.text = f"🔒 {pr}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(8)

    # =========================================================================
    # SLIDE 5: Architecture Diagram
    # =========================================================================
    s5 = prs.slides.add_slide(blank_slide_layout)
    add_header(s5, "SentinelX-Shift System Architecture")
    
    arch_path = "d:/sentinelx/docs/figures/fig1_architecture.png"
    if os.path.exists(arch_path):
        s5.shapes.add_picture(arch_path, Inches(0.8), Inches(1.6), width=Inches(8.2))
    
    # Legend / Callout box on right
    add_card(s5, Inches(9.2), Inches(1.6), Inches(3.3), Inches(5.3))
    tb_arch = s5.shapes.add_textbox(Inches(9.4), Inches(1.8), Inches(2.9), Inches(4.9))
    tf_arch = tb_arch.text_frame
    tf_arch.word_wrap = True
    
    p = tf_arch.paragraphs[0]
    p.text = "Architectural Flow"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = BLUE
    p.space_after = Pt(10)
    
    arch_steps = [
        "1. Traffic Tap: Raw PCAP / NetFlow stream ingested.",
        "2. Sanitization: Strips IPs/ports; extracts 76 normalized features.",
        "3. Dual Scoring: Unsupervised AE baseline + Supervised XGBoost.",
        "4. Empirical CDF: Uniform score calibration [0, 1].",
        "5. Gated Fusion: Anchored boost applies only if XGB > 0.56.",
        "6. Log Correlator: Cross-checks Nginx & ModSecurity WAF events.",
        "7. SOC Queue: High-priority triage cards with short UUID pills."
    ]
    for s in arch_steps:
        p = tf_arch.add_paragraph()
        p.text = s
        p.font.size = Pt(10)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 6: Methodology & Formula
    # =========================================================================
    s6 = prs.slides.add_slide(blank_slide_layout)
    add_header(s6, "Mathematical Formulation: Autoencoder-Anchored Gated Boost")

    # Formula Box
    add_card(s6, Inches(0.8), Inches(1.6), Inches(11.733), Inches(1.8), bg_color=RGBColor(241, 245, 249), border_color=BLUE)
    tb_f = s6.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(11.333), Inches(1.4))
    tf_f = tb_f.text_frame
    tf_f.word_wrap = True
    
    p = tf_f.paragraphs[0]
    p.text = "THE PRODUCTION SCORING FORMULATION"
    p.font.bold = True
    p.font.size = Pt(11)
    p.font.color.rgb = ACCENT_BLUE
    p.space_after = Pt(4)
    
    p_math = tf_f.add_paragraph()
    p_math.text = "s_guard = s_AE + γ* · I(s_XGB > τ*),   where  τ* = 0.56,  γ* = 0.41"
    p_math.font.bold = True
    p_math.font.size = Pt(20)
    p_math.font.color.rgb = BLUE
    p_math.space_after = Pt(4)
    
    p_sub = tf_f.add_paragraph()
    p_sub.text = "where s_AE, s_XGB ∈ [0, 1] are empirical CDF-calibrated percentiles, and I(·) is the indicator function."
    p_sub.font.size = Pt(11)
    p_sub.font.color.rgb = DARK_GRAY

    # 3 Explanation Cards below
    col_w = Inches(3.64)
    add_card(s6, Inches(0.8), Inches(3.6), col_w, Inches(3.3))
    tb_e1 = s6.shapes.add_textbox(Inches(1.0), Inches(3.8), col_w - Inches(0.4), Inches(2.9))
    tf_e1 = tb_e1.text_frame
    tf_e1.word_wrap = True
    p = tf_e1.paragraphs[0]
    p.text = "1. Autoencoder Anomaly Floor"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = NAVY
    p.space_after = Pt(6)
    p = tf_e1.add_paragraph()
    p.text = "Symmetric architecture [76-48-24-12-24-48-76] trained exclusively on 38,742 clean normal flows. Reconstruction MSE spikes on any departure from benign manifold, guaranteeing zero-day anomaly floor."
    p.font.size = Pt(10.5)
    p.font.color.rgb = DARK_GRAY

    add_card(s6, Inches(4.84), Inches(3.6), col_w, Inches(3.3))
    tb_e2 = s6.shapes.add_textbox(Inches(5.04), Inches(3.8), col_w - Inches(0.4), Inches(2.9))
    tf_e2 = tb_e2.text_frame
    tf_e2.word_wrap = True
    p = tf_e2.paragraphs[0]
    p.text = "2. Empirical CDF Calibration"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = NAVY
    p.space_after = Pt(6)
    p = tf_e2.add_paragraph()
    p.text = "Raw MSE and tree scores inhabit incompatible non-linear scales. SentinelX calibrates raw scores using empirical CDF rank percentiles evaluated over clean validation sets, normalizing them into uniform [0, 1] probabilities."
    p.font.size = Pt(10.5)
    p.font.color.rgb = DARK_GRAY

    add_card(s6, Inches(8.88), Inches(3.6), col_w, Inches(3.3))
    tb_e3 = s6.shapes.add_textbox(Inches(9.08), Inches(3.8), col_w - Inches(0.4), Inches(2.9))
    tf_e3 = tb_e3.text_frame
    tf_e3.word_wrap = True
    p = tf_e3.paragraphs[0]
    p.text = "3. Gated Additive Activation"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = NAVY
    p.space_after = Pt(6)
    p = tf_e3.add_paragraph()
    p.text = "Standard linear blends (0.5·AE + 0.5·XGB) collapse when XGB predicts 0 on zero-day attacks. SentinelX anchors s_AE and gates the boost: supervised risk activates only when confidence exceeds τ* = 0.56."
    p.font.size = Pt(10.5)
    p.font.color.rgb = DARK_GRAY

    # =========================================================================
    # SLIDE 7: Dataset & Deduplication Audit
    # =========================================================================
    s7 = prs.slides.add_slide(blank_slide_layout)
    add_header(s7, "Dataset Provenance & The 21.03% Deduplication Audit")

    dedup_path = "d:/sentinelx/docs/figures/fig2_deduplication.png"
    if os.path.exists(dedup_path):
        s7.shapes.add_picture(dedup_path, Inches(0.8), Inches(1.6), width=Inches(6.8))

    add_card(s7, Inches(7.8), Inches(1.6), Inches(4.7), Inches(5.3))
    tb_ds = s7.shapes.add_textbox(Inches(8.0), Inches(1.8), Inches(4.3), Inches(4.9))
    tf_ds = tb_ds.text_frame
    tf_ds.word_wrap = True
    
    p = tf_ds.paragraphs[0]
    p.text = "CIC-IDS2017 Audit Breakdown"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = BLUE
    p.space_after = Pt(10)
    
    ds_stats = [
        ("Total Raw Flows Ingested:", "2,827,840 flows across 8 capture CSVs"),
        ("Duplicate Vectors Purged:", "594,712 exact duplicate vectors (21.03%)"),
        ("Unique Flows Retained:", "2,233,128 unique flows"),
        ("Balanced Benchmark Size:", "60,000 stratified sampled flows"),
        ("DoS/DDoS Attack Flows:", "6,572 flows"),
        ("BruteForce Attack Flows:", "9,150 flows"),
        ("WebAttack Flows:", "2,143 flows"),
        ("PortScan Flows:", "1,956 flows"),
        ("Botnet Flows:", "1,437 flows"),
        ("Benign Baseline Flows:", "38,742 flows")
    ]
    for label, val in ds_stats:
        p = tf_ds.add_paragraph()
        p.text = f"• {label} {val}"
        p.font.size = Pt(10)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(4)

    # =========================================================================
    # SLIDE 8: Experimental Setup & Results Table
    # =========================================================================
    s8 = prs.slides.add_slide(blank_slide_layout)
    add_header(s8, "Multi-Seed LOFO Benchmark Results (5% Prevalence)")

    # Table
    table_shape = s8.shapes.add_table(rows=6, cols=5, left=Inches(0.8), top=Inches(1.6), width=Inches(11.733), height=Inches(3.4))
    table = table_shape.table
    
    # Column widths
    table.columns[0].width = Inches(2.333)
    table.columns[1].width = Inches(2.35)
    table.columns[2].width = Inches(2.35)
    table.columns[3].width = Inches(2.35)
    table.columns[4].width = Inches(2.35)

    headers = ["Held-Out Attack Family", "Supervised XGBoost", "Autoencoder Baseline", "Proposed SentinelX-Shift", "Detection Regime"]
    for i, h in enumerate(headers):
        cell = table.cell(0, i)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.bold = True
        p.font.size = Pt(11)
        p.font.color.rgb = WHITE
        p.alignment = PP_ALIGN.CENTER

    data_rows = [
        ("DoS / DDoS", "ROC: 0.9632 | PR: 0.7854\nRecall@1%FAR: 70.87%", "ROC: 0.7951 | PR: 0.2845\nRecall@1%FAR: 18.23%", "ROC: 0.9645 | PR: 0.7891\nRecall@1%FAR: 70.87%", "Volumetric (Generalizes)"),
        ("PortScan", "ROC: 0.9845 | PR: 0.8412\nRecall@1%FAR: 87.89%", "ROC: 0.8123 | PR: 0.3120\nRecall@1%FAR: 22.45%", "ROC: 0.9851 | PR: 0.8435\nRecall@1%FAR: 87.89%", "Volumetric (Generalizes)"),
        ("BruteForce", "ROC: 0.9202 | PR: 0.3149\nRecall@1%FAR: 4.18%", "ROC: 0.8034 | PR: 0.1144\nRecall@1%FAR: 0.00%", "ROC: 0.8042 | PR: 0.1199\nRecall@1%FAR: 1.55%", "Stealthy (Fails Pure Netflow)"),
        ("Botnet", "ROC: 0.7845 | PR: 0.1420\nRecall@1%FAR: 0.00%", "ROC: 0.7612 | PR: 0.0980\nRecall@1%FAR: 0.00%", "ROC: 0.7650 | PR: 0.1015\nRecall@1%FAR: 0.00%", "Stealthy (Fails Pure Netflow)"),
        ("WebAttack", "ROC: 0.9824 | PR: 0.7481\nRecall@1%FAR: 57.22%", "ROC: 0.7414 | PR: 0.0995\nRecall@1%FAR: 0.00%", "ROC: 0.7535 | PR: 0.1053\nRecall@1%FAR: 0.77%", "Stealthy (Fails Pure Netflow)")
    ]

    for r_idx, row in enumerate(data_rows, start=1):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(248, 250, 252) if r_idx % 2 == 1 else WHITE
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.size = Pt(9.5)
            p.alignment = PP_ALIGN.CENTER
            if c_idx == 3:
                p.font.bold = True
                p.font.color.rgb = BLUE
            elif c_idx == 4 and "Stealthy" in val:
                p.font.bold = True
                p.font.color.rgb = RED

    # Key observation card below table
    add_card(s8, Inches(0.8), Inches(5.2), Inches(11.733), Inches(1.7), bg_color=RGBColor(254, 242, 242), border_color=RED)
    tb_obs = s8.shapes.add_textbox(Inches(1.0), Inches(5.3), Inches(11.333), Inches(1.5))
    tf_obs = tb_obs.text_frame
    tf_obs.word_wrap = True
    p = tf_obs.paragraphs[0]
    p.text = "CRITICAL RESEARCH FINDING: The Generalization Divide"
    p.font.bold = True
    p.font.size = Pt(11)
    p.font.color.rgb = RED
    p.space_after = Pt(2)
    p = tf_obs.add_paragraph()
    p.text = "Pure NetFlow statistical models generalize effectively on volumetric attacks (DoS/PortScan >70% Recall@1%FAR), but suffer near-total collapse on stealthy attacks (BruteForce/WebAttack/Bot ~0% Recall@1%FAR) during zero-day holdout. This rigorously justifies SentinelX's requirement for Multi-Tier WAF/Web Log Confirmation!"
    p.font.size = Pt(10.5)
    p.font.color.rgb = DARK_GRAY

    # =========================================================================
    # SLIDE 9: Visual Charts (Bar Chart & Joint Holdout)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_slide_layout)
    add_header(s9, "Empirical Validation: LOFO Performance & Semantic Degradation")

    bar_path = "d:/sentinelx/docs/figures/fig3_lofo_performance.png"
    if os.path.exists(bar_path):
        s9.shapes.add_picture(bar_path, Inches(0.8), Inches(1.6), width=Inches(5.6))

    line_path = "d:/sentinelx/docs/figures/fig4_joint_holdout.png"
    if os.path.exists(line_path):
        s9.shapes.add_picture(line_path, Inches(6.8), Inches(1.6), width=Inches(5.7))

    # Caption boxes
    cap1 = s9.shapes.add_textbox(Inches(0.8), Inches(5.7), Inches(5.6), Inches(1.2))
    tf = cap1.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Figure A: Volumetric vs Stealthy Divide"
    p.font.bold = True
    p.font.size = Pt(11)
    p = tf.add_paragraph()
    p.text = "High detection on DoS/PortScan; collapse on low-rate brute force under strict zero-day holdout."
    p.font.size = Pt(9.5)
    p.font.color.rgb = DARK_GRAY

    cap2 = s9.shapes.add_textbox(Inches(6.8), Inches(5.7), Inches(5.7), Inches(1.2))
    tf = cap2.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Figure B: Joint Holdout Semantic Bleed"
    p.font.bold = True
    p.font.size = Pt(11)
    p = tf.add_paragraph()
    p.text = "Holding out {BruteForce, WebAttack} drops PR-AUC from 0.7481 to 0.2962 (-60.4%), proving benchmark cross-leakage."
    p.font.size = Pt(9.5)
    p.font.color.rgb = DARK_GRAY

    # =========================================================================
    # SLIDE 10: Negative Finding on TreeSHAP
    # =========================================================================
    s10 = prs.slides.add_slide(blank_slide_layout)
    add_header(s10, "Negative Finding & Technical Rigor: Why TreeSHAP Was Rejected")

    add_card(s10, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3))
    tb_sh1 = s10.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.9))
    tf_sh1 = tb_sh1.text_frame
    tf_sh1.word_wrap = True
    
    p = tf_sh1.paragraphs[0]
    p.text = "Explanation Instability (Lipschitz Violation)"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = RED
    p.space_after = Pt(10)
    
    pts = [
        "Network Jitter Sensitivity: Perturbing flow inter-arrival time (IAT) by under 1.5% completely scrambled top-3 SHAP feature rankings.",
        "Violates Invariant Trust: Analysts cannot trust explanations that shift drastically between consecutive packets of the same flow.",
        "Theoretical Flaw in NIDS: Netflow features exhibit intense collinearity, violating SHAP's feature-independence assumptions."
    ]
    for pt in pts:
        p = tf_sh1.add_paragraph()
        p.text = f"• {pt}"
        p.font.size = Pt(11)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(10)

    add_card(s10, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3))
    tb_sh2 = s10.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
    tf_sh2 = tb_sh2.text_frame
    tf_sh2.word_wrap = True
    
    p = tf_sh2.paragraphs[0]
    p.text = "Severe Latency Overhead"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = RED
    p.space_after = Pt(10)
    
    pts2 = [
        "150+ ms Per-Flow Penalty: Computing TreeSHAP values requires 120–180 ms per flow on x86 CPU.",
        "Violates Operational SLA: Production SOC networks require sub-10 ms flow triage.",
        "SentinelX Decision: Formally rejected TreeSHAP from real-time scoring path. Replaced with direct score breakdowns and multi-modal evidence pills, achieving 1.25–2.45 ms CPU latency!"
    ]
    for pt in pts2:
        p = tf_sh2.add_paragraph()
        p.text = f"• {pt}"
        p.font.size = Pt(11)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(10)

    # =========================================================================
    # SLIDE 11: Cross-Tier Guardrails & Walkthrough Scenarios
    # =========================================================================
    s11 = prs.slides.add_slide(blank_slide_layout)
    add_header(s11, "Multi-Tier Log Guardrails: Resolving False Alarm Storms")

    # 3 Scenario Cards
    col_w = Inches(3.64)
    # Scenario 1
    add_card(s11, Inches(0.8), Inches(1.6), col_w, Inches(5.3))
    tb = s11.shapes.add_textbox(Inches(1.0), Inches(1.8), col_w - Inches(0.4), Inches(4.9))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Scenario 1: Stealthy Brute Force"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = RED
    p.space_after = Pt(8)
    
    s1_text = [
        ("Flow Characteristics:", "Low-rate attack at 0.53 req/s. Well below volumetric DDoS threshold."),
        ("NetFlow Score:", "Model anomaly score s_prod = 1.0 (unsupervised AE triggers)."),
        ("Cross-Tier Evidence:", "Correlated Nginx error log detects 8 consecutive HTTP 401s + ModSecurity rule 200002."),
        ("Triage Action:", "Guardrail satisfied -> Escalated to CRITICAL with ESCALATE_TO_ANALYST.")
    ]
    for h, b in s1_text:
        p = tf.add_paragraph()
        p.text = f"{h}\n{b}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(6)

    # Scenario 2
    add_card(s11, Inches(4.84), Inches(1.6), col_w, Inches(5.3), bg_color=RGBColor(240, 253, 250))
    tb = s11.shapes.add_textbox(Inches(5.04), Inches(1.8), col_w - Inches(0.4), Inches(4.9))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Scenario 2: Benign Traffic Burst"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = GREEN
    p.space_after = Pt(8)
    
    s2_text = [
        ("Flow Characteristics:", "Internal client initiates 75 requests in 1 second (e.g. data backup/refresh)."),
        ("NetFlow Score:", "Model anomaly spikes to s_AE = 0.9969 (false-positive trigger)."),
        ("Cross-Tier Evidence:", "Correlated logs reveal HTTP 200 OK responses, 0 auth failures, 0 WAF violations."),
        ("Triage Action:", "Burst Guardrail suppresses alarm -> De-escalated to MEDIUM / MONITOR.")
    ]
    for h, b in s2_text:
        p = tf.add_paragraph()
        p.text = f"{h}\n{b}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(6)

    # Scenario 3
    add_card(s11, Inches(8.88), Inches(1.6), col_w, Inches(5.3))
    tb = s11.shapes.add_textbox(Inches(9.08), Inches(1.8), col_w - Inches(0.4), Inches(4.9))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Scenario 3: Missing Telemetry"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = DARK_GRAY
    p.space_after = Pt(8)
    
    s3_text = [
        ("Flow Characteristics:", "NetFlow record missing Source IP or Timestamp header."),
        ("NetFlow Score:", "Model computes score normally based on packet dynamics."),
        ("Cross-Tier Evidence:", "Correlator safely marks telemetry as 'Unavailable' (present=False)."),
        ("Triage Action:", "Fallback Guardrail holds risk at default tier without crashing or false blocking.")
    ]
    for h, b in s3_text:
        p = tf.add_paragraph()
        p.text = f"{h}\n{b}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 12: Working Demo & Deployment Console
    # =========================================================================
    s12 = prs.slides.add_slide(blank_slide_layout)
    add_header(s12, "Working Demo: SOC Analyst Dashboard & Presentation Console")

    add_card(s12, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3))
    tb_dm1 = s12.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.9))
    tf_dm1 = tb_dm1.text_frame
    tf_dm1.word_wrap = True
    
    p = tf_dm1.paragraphs[0]
    p.text = "Interactive SOC Dashboard"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = BLUE
    p.space_after = Pt(8)
    
    dm_items = [
        ("Prioritized Queue:", "Filters incoming flows by Risk Tier (CRITICAL/HIGH/MED/LOW) and Review Status."),
        ("Telemetry Drilldown Modal:", "Inspects AE/XGBoost score breakdowns, confirming signal badges, and raw flow headers."),
        ("One-Click SOC Actions:", "Escalate to analyst, mark false positive, or apply ephemeral 60s replica blocks."),
        ("Persistent SQLite Review Store:", "All analyst triage decisions recorded with timestamp and short UUID badges.")
    ]
    for h, b in dm_items:
        p = tf_dm1.add_paragraph()
        p.text = f"• {h} {b}"
        p.font.size = Pt(11)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(8)

    add_card(s12, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3))
    tb_dm2 = s12.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
    tf_dm2 = tb_dm2.text_frame
    tf_dm2.word_wrap = True
    
    p = tf_dm2.paragraphs[0]
    p.text = "Demonstration Endpoints & CLI"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = NAVY
    p.space_after = Pt(8)
    
    demo_cmds = [
        ("Dashboard URL:", "http://localhost:8000/dashboard"),
        ("Active Presentation Console:", "http://localhost:8000/presentation"),
        ("Automated HOD Walkthrough:", "python scripts/demo_hod.py"),
        ("Phase 3 Telemetry Demo:", "python scripts/demo_phase3.py"),
        ("Offline CLI Scanner:", "sentinelx-scan.bat --file data/samples/logs/synthetic_flows.csv --output table"),
        ("Automated Verification Suite:", "pytest tests/ -v (97 tests passed)")
    ]
    for label, val in demo_cmds:
        p = tf_dm2.add_paragraph()
        p.text = f"⚡ {label}\n    {val}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 13: Project Outcomes & Publications (CRITICAL FOR 30 MARKS)
    # =========================================================================
    s13 = prs.slides.add_slide(blank_slide_layout)
    add_header(s13, "Project Outcomes & Publications (Evaluation Component: 30 Marks)")

    # 3 Outcome Cards
    add_card(s13, Inches(0.8), Inches(1.6), Inches(3.64), Inches(5.3))
    tb_o1 = s13.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(3.24), Inches(4.9))
    tf_o1 = tb_o1.text_frame
    tf_o1.word_wrap = True
    p = tf_o1.paragraphs[0]
    p.text = "Outcome 1: Book Chapter"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = BLUE
    p.space_after = Pt(8)
    
    b_pts = [
        ("Title:", "A Comprehensive Operational Framework for Network Intrusion Detection and Alert Prioritization Using Autoencoder-Anchored Scoring"),
        ("Authors:", "Aathekesavan R., Praveen K., Dr. S. Kanaga Suba Raja"),
        ("Status:", "Final Formatted Draft Completed (Nov 7, 2026)"),
        ("Pages/File:", "SentinelX_Book_Chapter_Final.docx (56 KB, ~25 pages)")
    ]
    for h, b in b_pts:
        p = tf_o1.add_paragraph()
        p.text = f"{h} {b}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(6)

    add_card(s13, Inches(4.84), Inches(1.6), Inches(3.64), Inches(5.3))
    tb_o2 = s13.shapes.add_textbox(Inches(5.04), Inches(1.8), Inches(3.24), Inches(4.9))
    tf_o2 = tb_o2.text_frame
    tf_o2.word_wrap = True
    p = tf_o2.paragraphs[0]
    p.text = "Outcome 2: Research Paper"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = BLUE
    p.space_after = Pt(8)
    
    r_pts = [
        ("Format:", "IEEE Transactions on Information Forensics and Security (TIFS) / IEEE Access Style"),
        ("Artifacts:", "SentinelX_IEEE_Transactions.tex (64 KB) & Docx (935 KB)"),
        ("Highlights:", "Comprehensive 5-seed LOFO benchmark, UNSW-NB15 cross-dataset evaluation, TreeSHAP negative audit finding.")
    ]
    for h, b in r_pts:
        p = tf_o2.add_paragraph()
        p.text = f"{h} {b}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(6)

    add_card(s13, Inches(8.88), Inches(1.6), Inches(3.64), Inches(5.3), bg_color=RGBColor(240, 253, 250))
    tb_o3 = s13.shapes.add_textbox(Inches(9.08), Inches(1.8), Inches(3.24), Inches(4.9))
    tf_o3 = tb_o3.text_frame
    tf_o3.word_wrap = True
    p = tf_o3.paragraphs[0]
    p.text = "Outcome 3: Competition & SIH"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = GREEN
    p.space_after = Pt(8)
    
    c_pts = [
        ("Alignment:", "Smart India Hackathon (SIH 2026) & Seva First Innovation Challenge (Ministry of Education, GoI)."),
        ("Theme:", "Cybersecurity & Cyber Defense for Critical Information Infrastructures."),
        ("Key Innovation:", "Elimination of self-inflicted outages via Monitor-Only posture + cross-tier WAF correlation.")
    ]
    for h, b in c_pts:
        p = tf_o3.add_paragraph()
        p.text = f"{h} {b}"
        p.font.size = Pt(10.5)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 14: Conclusion & Future Work
    # =========================================================================
    s14 = prs.slides.add_slide(blank_slide_layout)
    add_header(s14, "Conclusion & Future Research Directions")

    # Left: Conclusion
    add_card(s14, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.3))
    tb_c = s14.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.9))
    tf_c = tb_c.text_frame
    tf_c.word_wrap = True
    
    p = tf_c.paragraphs[0]
    p.text = "Summary of Contributions"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = NAVY
    p.space_after = Pt(10)
    
    concs = [
        "Uncovered Benchmark Vulnerabilities: Demonstrated that academic claims of >99% accuracy collapse under 21% deduplication and Leave-One-Family-Out validation.",
        "Engineered Resilient Scoring: Autoencoder-Anchored Gated Boost prevents zero-day blindspots while utilizing supervised threat signals.",
        "Bridged Network & Host Tiers: Integrated Nginx and ModSecurity WAF audit logs within ±30s windows to eliminate false-alarm storms.",
        "Operational Safety: Enforced strictly Monitor-Only live deployment; active mitigation verified only on isolated honeypot replicas."
    ]
    for c in concs:
        p = tf_c.add_paragraph()
        p.text = f"✔ {c}"
        p.font.size = Pt(11)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(10)

    # Right: Future Work
    add_card(s14, Inches(6.8), Inches(1.6), Inches(5.7), Inches(5.3))
    tb_fw = s14.shapes.add_textbox(Inches(7.0), Inches(1.8), Inches(5.3), Inches(4.9))
    tf_fw = tb_fw.text_frame
    tf_fw.word_wrap = True
    
    p = tf_fw.paragraphs[0]
    p.text = "Future Roadmap"
    p.font.bold = True
    p.font.size = Pt(13)
    p.font.color.rgb = BLUE
    p.space_after = Pt(10)
    
    fws = [
        "Kernel-Level eBPF / XDP Ingestion: Direct zero-copy packet interception at the Linux network driver level for sub-millisecond line-rate NetFlow telemetry.",
        "JA4 / Encrypted SNI Fingerprinting: Extracting cryptographic TLS handshake primitives without decrypting encrypted payload streams.",
        "Multi-Agent LLM SOC Triage: Integrating local quantized reasoning models to synthesize automated incident response summaries for tier-1 analysts."
    ]
    for fw in fws:
        p = tf_fw.add_paragraph()
        p.text = f"🚀 {fw}"
        p.font.size = Pt(11)
        p.font.color.rgb = DARK_GRAY
        p.space_after = Pt(10)

    # =========================================================================
    # SLIDE 15: Q&A / Thank You
    # =========================================================================
    s15 = prs.slides.add_slide(blank_slide_layout)
    
    # Large Hero Center
    add_card(s15, Inches(1.5), Inches(1.2), Inches(10.333), Inches(5.1), bg_color=NAVY, border_color=ACCENT_BLUE)
    tb_ty = s15.shapes.add_textbox(Inches(2.0), Inches(1.8), Inches(9.333), Inches(4.0))
    tf_ty = tb_ty.text_frame
    tf_ty.word_wrap = True
    
    p = tf_ty.paragraphs[0]
    p.text = "Thank You!"
    p.font.bold = True
    p.font.size = Pt(36)
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER
    p.space_after = Pt(12)
    
    p = tf_ty.add_paragraph()
    p.text = "SENTINELX-SHIFT: Operational Network Intrusion Detection & Prioritized Alert Review System"
    p.font.size = Pt(14)
    p.font.color.rgb = CYAN
    p.alignment = PP_ALIGN.CENTER
    p.space_after = Pt(24)
    
    p = tf_ty.add_paragraph()
    p.text = "Aathekesavan R. [RA2411003050015]   |   Praveen K. [RA2411003050056]\nGuided by Dr. S. Kanaga Suba Raja (HOD, CSE)\nSRM Institute of Science and Technology, Tiruchirappalli"
    p.font.size = Pt(13)
    p.font.color.rgb = RGBColor(203, 213, 225)
    p.alignment = PP_ALIGN.CENTER
    p.space_after = Pt(20)
    
    p = tf_ty.add_paragraph()
    p.text = "Questions & Technical Discussion"
    p.font.bold = True
    p.font.size = Pt(18)
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER

    prs.save(output_path)
    print(f"Presentation saved successfully to: {output_path}")

if __name__ == '__main__':
    out_file = os.path.join(os.getcwd(), "SentinelX_Project_Review_Presentation.pptx")
    create_presentation(out_file)
