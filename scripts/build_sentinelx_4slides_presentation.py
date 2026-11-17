import os
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

def build_sentinelx_4slides_presentation():
    template_path = 'C:/Users/aathe/.gemini/antigravity/brain/722aad3e-8779-44e1-8bf4-0d3eb310252d/.user_uploaded/media_1794444955506_33c3068c.pptx'
    prs = pptx.Presentation(template_path)

    # Color constants
    C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)
    C_CYAN = RGBColor(0x00, 0xC3, 0xEB)
    C_BLUE = RGBColor(0x19, 0x5F, 0xD7)
    C_DARK_BLUE = RGBColor(0x10, 0x30, 0x69)
    C_DARK = RGBColor(0x0F, 0x19, 0x2D)
    C_MUTED = RGBColor(0x50, 0x64, 0x7D)

    def set_cell_text(cell, text, font_size=10.0, bold=False, color=C_DARK, align=PP_ALIGN.LEFT):
        cell.text_frame.clear()
        p = cell.text_frame.paragraphs[0]
        p.alignment = align
        run = p.add_run()
        run.text = text
        run.font.name = 'Calibri'
        run.font.size = Pt(font_size)
        run.font.bold = bold
        run.font.color.rgb = color

    # =========================================================================
    # SLIDE 1: Title & Overview
    # =========================================================================
    s1 = prs.slides[0]
    for shape in s1.shapes:
        if shape.name == "TextBox 5":
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.LEFT
            r0 = p0.add_run()
            r0.text = "SENTINELX-SHIFT: Operational Network Intrusion Detection"
            r0.font.name = 'Calibri'
            r0.font.size = Pt(21.0)
            r0.font.bold = True
            r0.font.color.rgb = C_WHITE

            p1 = shape.text_frame.add_paragraph()
            p1.alignment = PP_ALIGN.LEFT
            r1 = p1.add_run()
            r1.text = "Dual-Engine Score Fusion & Multi-Tier Guardrails for High-Volume Enterprise SOC Deployments"
            r1.font.name = 'Calibri'
            r1.font.size = Pt(13.0)
            r1.font.color.rgb = C_CYAN

        elif shape.name == "Rounded Rectangle 6":  # Problem statement body
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.LEFT
            r0a = p0.add_run()
            r0a.text = "• Shortcut Learning & Benchmark Duplication: "
            r0a.font.bold = True
            r0a.font.size = Pt(11.0)
            r0a.font.color.rgb = C_DARK_BLUE
            r0b = p0.add_run()
            r0b.text = "Academic NIDS claim >99% accuracy by memorizing IP/port metadata. Benchmarks contain 21.03% duplicate flows that bleed test data into training.\n\n"
            r0b.font.bold = False
            r0b.font.size = Pt(10.0)
            r0b.font.color.rgb = C_DARK

            r1a = p0.add_run()
            r1a.text = "• Zero-Day Fragility & Autonomous Outage Hazard: "
            r1a.font.bold = True
            r1a.font.size = Pt(11.0)
            r1a.font.color.rgb = C_DARK_BLUE
            r1b = p0.add_run()
            r1b.text = "Supervised models fail under novel distribution shifts (-60.4% PR-AUC in LOFO tests), while autonomous inline blocking triggers catastrophic production downtime."
            r1b.font.bold = False
            r1b.font.size = Pt(10.0)
            r1b.font.color.rgb = C_DARK

        elif shape.name == "Rounded Rectangle 7":  # Problem statement badge
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            r.text = "PROBLEM STATEMENT"
            r.font.bold = True
            r.font.size = Pt(11.0)
            r.font.color.rgb = C_WHITE

        elif shape.name == "Rounded Rectangle 8":  # System objective body
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.LEFT
            r0a = p0.add_run()
            r0a.text = "• Autoencoder-Anchored Gated Boost: "
            r0a.font.bold = True
            r0a.font.size = Pt(11.0)
            r0a.font.color.rgb = C_DARK_BLUE
            r0b = p0.add_run()
            r0b.text = "Unsupervised Autoencoder establishes an anomaly baseline for novel zero-day attacks, with calibrated XGBoost additive boost gated at tau=0.56.\n\n"
            r0b.font.bold = False
            r0b.font.size = Pt(10.0)
            r0b.font.color.rgb = C_DARK

            r1a = p0.add_run()
            r1a.text = "• Multi-Tier Guardrails & Monitor-Only Posture: "
            r1a.font.bold = True
            r1a.font.size = Pt(11.0)
            r1a.font.color.rgb = C_DARK_BLUE
            r1b = p0.add_run()
            r1b.text = "Correlates transport NetFlow with Nginx & ModSecurity WAF audit logs to de-escalate benign traffic bursts, enforcing strict monitor-only safety (0% outage risk)."
            r1b.font.bold = False
            r1b.font.size = Pt(10.0)
            r1b.font.color.rgb = C_DARK

        elif shape.name == "Rounded Rectangle 9":  # System objective badge
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            r.text = "SYSTEM OBJECTIVE"
            r.font.bold = True
            r.font.size = Pt(11.0)
            r.font.color.rgb = C_DARK

        elif shape.name == "Rounded Rectangle 10":  # Team members
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.CENTER
            r0 = p0.add_run()
            r0.text = "TEAM MEMBERS:   Aathekesavan R (RA2411003050015)   |   Praveen K (RA2411003050056)"
            r0.font.bold = True
            r0.font.size = Pt(13.0)
            r0.font.color.rgb = C_CYAN

            p1 = shape.text_frame.add_paragraph()
            p1.alignment = PP_ALIGN.CENTER
            r1 = p1.add_run()
            r1.text = "3rd Year, CSE-A  |  Department of Computer Science & Engineering  |  SRM Institute of Science and Technology, Tiruchirappalli"
            r1.font.bold = False
            r1.font.size = Pt(11.0)
            r1.font.color.rgb = C_WHITE

    # =========================================================================
    # SLIDE 2: Objective & System Architecture
    # =========================================================================
    s2 = prs.slides[1]
    for shape in list(s2.shapes):
        if shape.name == "TextBox 5":
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "Objective & Problem Statement"
            r.font.bold = True
            r.font.size = Pt(22.0)
            r.font.color.rgb = C_WHITE

        elif shape.name == "Rounded Rectangle 6":  # Objective banner
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            r.text = "OBJECTIVE: Deploy an operational network intrusion detection system (SentinelX-Shift) combining unsupervised autoencoder baselines, calibrated gated boosting, and cross-tier host log guardrails."
            r.font.bold = True
            r.font.size = Pt(11.5)
            r.font.color.rgb = C_DARK_BLUE

        elif shape.name == "TextBox 8":
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "SentinelX-Shift System Architecture"
            r.font.bold = True
            r.font.size = Pt(14.0)
            r.font.color.rgb = C_BLUE

        elif shape.name == "Picture 9":  # Replace architecture picture
            left, top, w, h = shape.left, shape.top, shape.width, shape.height
            spTree = s2.shapes._spTree
            idx = list(spTree).index(shape._element)
            spTree.remove(shape._element)
            img_path = 'docs/figures/fig1_architecture.png'
            new_shape = s2.shapes.add_picture(img_path, left, top + Pt(10), w, int(h * 0.82))
            spTree.remove(new_shape._element)
            spTree.insert(idx, new_shape._element)

        elif shape.name == "TextBox 11":
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "Core Architectural & Scoring Innovations"
            r.font.bold = True
            r.font.size = Pt(14.0)
            r.font.color.rgb = C_DARK_BLUE

        elif shape.name == "Rounded Rectangle 12":  # Breakdown Card 1
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.CENTER
            r0 = p0.add_run()
            r0.text = "• Leakage-Free Feature Engineering (76 Features)"
            r0.font.bold = True
            r0.font.size = Pt(11.0)
            r0.font.color.rgb = C_BLUE

            p1 = shape.text_frame.add_paragraph()
            p1.alignment = PP_ALIGN.LEFT
            r1 = p1.add_run()
            r1.text = "Strips IP, MAC, ports, and timestamps. Retains purely statistical transport dynamics, flow rates, and packet length distributions."
            r1.font.size = Pt(9.5)
            r1.font.color.rgb = C_DARK

        elif shape.name == "Rounded Rectangle 13":  # Breakdown Card 2
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.CENTER
            r0 = p0.add_run()
            r0.text = "• Unsupervised Autoencoder Anomaly Floor"
            r0.font.bold = True
            r0.font.size = Pt(11.0)
            r0.font.color.rgb = C_BLUE

            p1 = shape.text_frame.add_paragraph()
            p1.alignment = PP_ALIGN.LEFT
            r1 = p1.add_run()
            r1.text = "Symmetric [76-48-24-12-24-48-76] autoencoder trained exclusively on clean benign flows, anchoring detection floor on novel zero-day attacks."
            r1.font.size = Pt(9.5)
            r1.font.color.rgb = C_DARK

        elif shape.name == "Rounded Rectangle 14":  # Breakdown Card 3
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.CENTER
            r0 = p0.add_run()
            r0.text = "• Empirical CDF & Gated Boost Scoring"
            r0.font.bold = True
            r0.font.size = Pt(11.0)
            r0.font.color.rgb = C_BLUE

            p1 = shape.text_frame.add_paragraph()
            p1.alignment = PP_ALIGN.LEFT
            r1 = p1.add_run()
            r1.text = "Normalizes disparate loss scales via CDF. Additive boost (gamma=0.41) activates only when supervised XGBoost exceeds threshold tau=0.56."
            r1.font.size = Pt(9.5)
            r1.font.color.rgb = C_DARK

        elif shape.name == "Rounded Rectangle 15":  # Breakdown Card 4
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.CENTER
            r0 = p0.add_run()
            r0.text = "• Multi-Tier Log Correlator & Guardrails"
            r0.font.bold = True
            r0.font.size = Pt(11.0)
            r0.font.color.rgb = C_BLUE

            p1 = shape.text_frame.add_paragraph()
            p1.alignment = PP_ALIGN.LEFT
            r1 = p1.add_run()
            r1.text = "Correlates NetFlow spikes with Nginx HTTP return codes and ModSecurity WAF rules to de-escalate benign bursts and isolate true attacks."
            r1.font.size = Pt(9.5)
            r1.font.color.rgb = C_DARK

        elif shape.name == "Rectangle 16":  # Footer
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            r.text = "SRM Institute of Science & Technology  |  SentinelX-Shift NIDS System  |  Slide 2 of 4"
            r.font.size = Pt(10.0)
            r.font.color.rgb = C_MUTED

    # =========================================================================
    # SLIDE 3: Target Users & Deployment Ecosystem
    # =========================================================================
    s3 = prs.slides[2]
    for shape in list(s3.shapes):
        if shape.name == "TextBox 5":
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "Target Users & End Users"
            r.font.bold = True
            r.font.size = Pt(22.0)
            r.font.color.rgb = C_WHITE

        elif shape.name == "TextBox 7":
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "Operational SOC Deployment Ecosystem"
            r.font.bold = True
            r.font.size = Pt(15.0)
            r.font.color.rgb = C_BLUE

        elif shape.name == "Picture 8":  # Replace deployment picture
            left, top, w, h = shape.left, shape.top, shape.width, shape.height
            spTree = s3.shapes._spTree
            idx = list(spTree).index(shape._element)
            spTree.remove(shape._element)
            img_path = 'docs/figures/sentinelx_deployment_ecosystem.png'
            new_shape = s3.shapes.add_picture(img_path, left, top, w, int(h * 0.85))
            spTree.remove(new_shape._element)
            spTree.insert(idx, new_shape._element)

        elif shape.name == "TextBox 9":
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "Strict Monitor-Only TAP deployment across enterprise network cores, DMZ routers, and Managed SOC environments."
            r.font.size = Pt(9.5)
            r.font.color.rgb = C_MUTED

        elif shape.name == "TextBox 11":
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "Stakeholder Landscape & Target Audience"
            r.font.bold = True
            r.font.size = Pt(15.0)
            r.font.color.rgb = C_DARK_BLUE

        elif shape.name == "Rounded Rectangle 12":  # Target Users
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.CENTER
            r0 = p0.add_run()
            r0.text = "• Target Users (Tier-1/2 SOC Analysts & Incident Responders)"
            r0.font.bold = True
            r0.font.size = Pt(11.0)
            r0.font.color.rgb = C_BLUE

            p1 = shape.text_frame.add_paragraph()
            p1.alignment = PP_ALIGN.LEFT
            r1 = p1.add_run()
            r1.text = "Security Operation Center (SOC) teams triaging high-volume alerts; incident response teams needing correlated host-network evidence."
            r1.font.size = Pt(9.8)
            r1.font.color.rgb = C_DARK

        elif shape.name == "Rounded Rectangle 13":  # End Users
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.CENTER
            r0 = p0.add_run()
            r0.text = "• End Users (CISOs & Enterprise Infrastructure Engineers)"
            r0.font.bold = True
            r0.font.size = Pt(11.0)
            r0.font.color.rgb = C_BLUE

            p1 = shape.text_frame.add_paragraph()
            p1.alignment = PP_ALIGN.LEFT
            r1 = p1.add_run()
            r1.text = "IT directors and network architects demanding guaranteed operational uptime without automated misclassifications taking services offline."
            r1.font.size = Pt(9.8)
            r1.font.color.rgb = C_DARK

        elif shape.name == "Rounded Rectangle 14":  # Regional Focus
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.CENTER
            r0 = p0.add_run()
            r0.text = "• Deployment Focus (Indian Critical Information Infrastructure)"
            r0.font.bold = True
            r0.font.size = Pt(11.0)
            r0.font.color.rgb = C_BLUE

            p1 = shape.text_frame.add_paragraph()
            p1.alignment = PP_ALIGN.LEFT
            r1 = p1.add_run()
            r1.text = "Banking networks, university campuses, smart city grids, and government data centers requiring sovereign, offline-capable cyber defense."
            r1.font.size = Pt(9.8)
            r1.font.color.rgb = C_DARK

        elif shape.name == "Rounded Rectangle 15":  # Callout Box
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.CENTER
            r0 = p0.add_run()
            r0.text = "RESOLVING ALERT FATIGUE WHILE PREVENTING SELF-INFLICTED OUTAGES"
            r0.font.bold = True
            r0.font.size = Pt(10.5)
            r0.font.color.rgb = C_CYAN

            p1 = shape.text_frame.add_paragraph()
            p1.alignment = PP_ALIGN.CENTER
            r1 = p1.add_run()
            r1.text = "Provides a fail-safe, monitor-only triage architecture that filters 95%+ of false alarms without ever autonomously blocking business traffic."
            r1.font.size = Pt(9.5)
            r1.font.color.rgb = C_WHITE

        elif shape.name == "Rectangle 16":  # Footer
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            r.text = "SRM Institute of Science & Technology  |  SentinelX-Shift NIDS System  |  Slide 3 of 4"
            r.font.size = Pt(10.0)
            r.font.color.rgb = C_MUTED

    # =========================================================================
    # SLIDE 4: Competitor Matrix & Strategic Differentiation
    # =========================================================================
    s4 = prs.slides[3]
    for shape in s4.shapes:
        if shape.name == "TextBox 5":
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "Competitor Companies & Market Matrix"
            r.font.bold = True
            r.font.size = Pt(22.0)
            r.font.color.rgb = C_WHITE

        elif shape.name == "TextBox 6":
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = "Enterprise NIDS & AI Cybersecurity Platforms vs. SentinelX-Shift Architecture"
            r.font.bold = True
            r.font.size = Pt(13.0)
            r.font.color.rgb = C_DARK

        elif shape.has_table:  # Table 7
            t = shape.table
            # Header Row
            set_cell_text(t.cell(0, 0), "Competitor System", font_size=11.5, bold=True, color=C_CYAN, align=PP_ALIGN.LEFT)
            set_cell_text(t.cell(0, 1), "Operational Model & Limitations", font_size=11.5, bold=True, color=C_CYAN, align=PP_ALIGN.LEFT)
            set_cell_text(t.cell(0, 2), "Official Web Portal", font_size=11.5, bold=True, color=C_CYAN, align=PP_ALIGN.LEFT)

            # Row 1: Darktrace
            set_cell_text(t.cell(1, 0), "Darktrace Enterprise\n(Self-Learning AI)", font_size=10.0, bold=True, color=C_DARK)
            set_cell_text(t.cell(1, 1), "Autonomous 'Antigena' inline response causes catastrophic self-inflicted business outages during benign network bursts. Exorbitant multi-million enterprise licensing.", font_size=9.5, color=C_DARK)
            set_cell_text(t.cell(1, 2), "https://www.darktrace.com/products/network", font_size=9.0, color=C_BLUE)

            # Row 2: Cisco Secure Network Analytics
            set_cell_text(t.cell(2, 0), "Cisco Secure Analytics\n(Stealthwatch)", font_size=10.0, bold=True, color=C_DARK)
            set_cell_text(t.cell(2, 1), "Proprietary Cisco appliance lock-in. Relies on heavy manual behavioral threshold tuning; lacks cross-tier application log (WAF/web server) correlation guardrails.", font_size=9.5, color=C_DARK)
            set_cell_text(t.cell(2, 2), "https://www.cisco.com/c/en/us/products/security/stealthwatch/", font_size=9.0, color=C_BLUE)

            # Row 3: Snort / Suricata
            set_cell_text(t.cell(3, 0), "Snort 3 / Suricata\n(Signature-Based NIDS)", font_size=10.0, bold=True, color=C_DARK)
            set_cell_text(t.cell(3, 1), "Rigid rule engines blind to novel zero-day attacks and polymorphic evasion techniques. Heavy CPU load during deep packet inspection (DPI) on encrypted traffic.", font_size=9.5, color=C_DARK)
            set_cell_text(t.cell(3, 2), "https://www.snort.org/ / https://suricata.io/", font_size=9.0, color=C_BLUE)

        elif shape.name == "Rounded Rectangle 8":  # Bottom Callout Box
            shape.text_frame.clear()
            p0 = shape.text_frame.paragraphs[0]
            p0.alignment = PP_ALIGN.CENTER
            r0 = p0.add_run()
            r0.text = "OUR STRATEGIC DIFFERENTIATION & ADVANTAGE"
            r0.font.bold = True
            r0.font.size = Pt(12.0)
            r0.font.color.rgb = C_CYAN

            p1 = shape.text_frame.add_paragraph()
            r1 = p1.add_run()
            r1.text = "• Zero Self-Inflicted Outages: Strict Monitor-Only TAP architecture guarantees 100% network uptime and zero accidental drops."
            r1.font.size = Pt(10.5)
            r1.font.color.rgb = C_WHITE

            p2 = shape.text_frame.add_paragraph()
            r2 = p2.add_run()
            r2.text = "• Autoencoder-Anchored Resilience: Prevents catastrophic failure on novel attacks; evaluated rigorously under Leave-One-Family-Out (LOFO)."
            r2.font.size = Pt(10.5)
            r2.font.color.rgb = C_WHITE

            p3 = shape.text_frame.add_paragraph()
            r3 = p3.add_run()
            r3.text = "• Cross-Tier Log Guardrails: Fuses transport NetFlow with Nginx & ModSecurity WAF audit logs to eliminate false alarm storms."
            r3.font.size = Pt(10.5)
            r3.font.color.rgb = C_WHITE

        elif shape.name == "Rectangle 9":  # Footer
            shape.text_frame.clear()
            p = shape.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.CENTER
            r = p.add_run()
            r.text = "SRM Institute of Science & Technology  |  SentinelX-Shift NIDS System  |  Slide 4 of 4"
            r.font.size = Pt(10.0)
            r.font.color.rgb = C_MUTED

    output_path = 'SentinelX_Project_Review_Presentation_4Slides.pptx'
    prs.save(output_path)
    print(f"Successfully generated {output_path}!")

if __name__ == '__main__':
    build_sentinelx_4slides_presentation()
