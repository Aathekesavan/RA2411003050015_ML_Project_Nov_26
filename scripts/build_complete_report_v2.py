# scripts/build_complete_report_v2.py
# Fully assembled, calibrated RETINAXAI project report targeting 41-44 pages

import os
import sys
import re
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

fig_dir = 'docs/retinaxai_figures'

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=45, bottom=45, left=65, right=65):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def set_table_borders(table, color="D1D5DB", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
            <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def set_borderless_table(table):
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="none"/>
            <w:bottom w:val="none"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
            <w:insideH w:val="none"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def add_formatted_runs(paragraph, text, font_name="Times New Roman", font_size=11.5, italic_default=False, bold_default=False, color=None):
    pattern = re.compile(r'(\*\*.*?\*\*|\*.*?\*|`.*?`|\$.*?\$|\[.*?\]\(.*?\))')
    parts = pattern.split(text)
    for part in parts:
        if not part:
            continue
        run = paragraph.add_run()
        run.font.name = font_name
        run.font.size = Pt(font_size)
        if color:
            run.font.color.rgb = color
        else:
            run.font.color.rgb = RGBColor(0, 0, 0)

        if part.startswith('**') and part.endswith('**') and len(part) >= 4:
            run.text = part[2:-2]
            run.bold = True
            run.italic = italic_default
        elif part.startswith('*') and part.endswith('*') and len(part) >= 2:
            run.text = part[1:-1]
            run.italic = True
            run.bold = bold_default
        elif part.startswith('`') and part.endswith('`') and len(part) >= 2:
            run.text = part[1:-1]
            run.font.name = "Consolas"
            run.font.size = Pt(font_size - 1.0)
            run.font.color.rgb = RGBColor(30, 30, 30)
            run.bold = bold_default
        elif part.startswith('$') and part.endswith('$') and len(part) >= 2:
            math_text = part[1:-1].replace(r'\text', '').replace('{', '').replace('}', '').replace(r'\mathbf', '')
            run.text = math_text
            run.italic = True
            run.bold = bold_default
        elif part.startswith('[') and '](' in part and part.endswith(')'):
            match = re.match(r'\[(.*?)\]\((.*?)\)', part)
            if match:
                run.text = match.group(1)
                run.font.color.rgb = RGBColor(0, 0, 0)
                run.bold = bold_default
            else:
                run.text = part
        else:
            run.text = part
            run.bold = bold_default
            run.italic = italic_default

def add_major_heading(doc, text):
    h = doc.add_heading(level=1)
    h.paragraph_format.page_break_before = True
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    h.paragraph_format.space_before = Pt(14)
    h.paragraph_format.space_after = Pt(6)
    h.paragraph_format.keep_with_next = True
    add_formatted_runs(h, text, font_size=14.0, bold_default=True)
    return h

def add_subheading(doc, text):
    h = doc.add_heading(level=2)
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h.paragraph_format.space_before = Pt(9)
    h.paragraph_format.space_after = Pt(3)
    h.paragraph_format.keep_with_next = True
    add_formatted_runs(h, text, font_size=12.0, bold_default=True)
    return h

def add_subsubheading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    add_formatted_runs(p, text, font_size=11.0, bold_default=True)
    return p

def add_body_p(doc, text, space_after=3.5, line_spacing=1.18):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    add_formatted_runs(p, text, font_size=11.5)
    return p

def add_bullet_p(doc, text, space_after=2.0):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    add_formatted_runs(p, text, font_size=11.5)
    return p

def add_numbered_p(doc, num, text, space_after=2.0):
    p = doc.add_paragraph(style='List Number')
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    add_formatted_runs(p, f"{num}. {text}", font_size=11.5)
    return p

def add_figure(doc, img_name, caption, width_in=4.8, page_break=False):
    img_path = os.path.join(fig_dir, img_name)
    if not os.path.exists(img_path):
        return
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if page_break:
        p_img.paragraph_format.page_break_before = True
    p_img.paragraph_format.space_before = Pt(6)
    p_img.paragraph_format.space_after = Pt(2)
    r = p_img.add_run()
    r.add_picture(img_path, width=Inches(width_in))
    
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(1)
    p_cap.paragraph_format.space_after = Pt(6)
    add_formatted_runs(p_cap, caption, font_size=9.5, bold_default=True, italic_default=True)

def add_code_box(doc, code_text):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, "F9FAFB")
    set_cell_margins(cell, top=50, bottom=50, left=80, right=80)
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="4" w:color="D1D5DB"/>
            <w:bottom w:val="single" w:sz="4" w:color="D1D5DB"/>
            <w:left w:val="single" w:sz="16" w:color="374151"/>
            <w:right w:val="single" w:sz="4" w:color="D1D5DB"/>
        </w:tcBorders>
    ''')
    tcPr.append(tcBorders)
    cp = cell.paragraphs[0]
    cp.paragraph_format.line_spacing = 1.05
    cp.paragraph_format.space_before = Pt(0)
    cp.paragraph_format.space_after = Pt(0)
    c_run = cp.add_run(code_text)
    c_run.font.name = "Consolas"
    c_run.font.size = Pt(8.5)
    c_run.font.color.rgb = RGBColor(17, 24, 39)

def add_table_data(doc, headers, rows_data, col_widths=None):
    num_rows = len(rows_data) + 1
    num_cols = len(headers)
    t = doc.add_table(rows=num_rows, cols=num_cols)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t, color="D1D5DB", sz="4")
    
    # Header row
    hdr_row = t.rows[0]
    trPr = hdr_row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
    trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
    for c_idx, h_text in enumerate(headers):
        cell = t.cell(0, c_idx)
        set_cell_margins(cell, top=35, bottom=35, left=50, right=50)
        set_cell_background(cell, "E5E7EB")
        cp = cell.paragraphs[0]
        cp.paragraph_format.line_spacing = 1.08
        cp.paragraph_format.space_before = Pt(0)
        cp.paragraph_format.space_after = Pt(0)
        add_formatted_runs(cp, h_text, font_size=8.5, bold_default=True)
        if col_widths and c_idx < len(col_widths):
            cell.width = Inches(col_widths[c_idx])
            
    # Data rows
    for r_idx, r_data in enumerate(rows_data):
        row = t.rows[r_idx + 1]
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        bg_color = "FFFFFF" if r_idx % 2 == 0 else "F9FAFB"
        for c_idx in range(num_cols):
            cell_txt = r_data[c_idx] if c_idx < len(r_data) else ""
            cell = t.cell(r_idx + 1, c_idx)
            set_cell_margins(cell, top=30, bottom=30, left=50, right=50)
            set_cell_background(cell, bg_color)
            cp = cell.paragraphs[0]
            cp.paragraph_format.line_spacing = 1.08
            cp.paragraph_format.space_before = Pt(0)
            cp.paragraph_format.space_after = Pt(0)
            add_formatted_runs(cp, cell_txt, font_size=8.0)
            if col_widths and c_idx < len(col_widths):
                cell.width = Inches(col_widths[c_idx])

def add_toc_line(doc, title, page_str, is_major=False, indent=0.0):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(1.0)
    p.paragraph_format.line_spacing = 1.06
    p.paragraph_format.left_indent = Inches(indent)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    
    r_title = p.add_run(title)
    r_title.font.name = "Times New Roman"
    r_title.font.size = Pt(9.5)
    r_title.font.color.rgb = RGBColor(0, 0, 0)
    if is_major:
        r_title.bold = True
        
    r_tab = p.add_run(f"\t{page_str}")
    r_tab.font.name = "Times New Roman"
    r_tab.font.size = Pt(9.5)
    r_tab.font.color.rgb = RGBColor(0, 0, 0)
    if is_major:
        r_tab.bold = True

print("v2 definitions ready.")

def add_preliminary_pages(doc):
    # ==================== PAGE 1: COVER PAGE ====================
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(14)
    p_title.paragraph_format.space_after = Pt(10)
    add_formatted_runs(p_title, "RETINAXAI: EXPLAINABLE ARTIFICIAL INTELLIGENCE FOR MULTI-STAGE DIABETIC RETINOPATHY SCREENING AND CLINICAL DECISION SUPPORT", font_size=14.5, bold_default=True)
    
    p_rep = doc.add_paragraph()
    p_rep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_rep.paragraph_format.space_before = Pt(4)
    p_rep.paragraph_format.space_after = Pt(6)
    add_formatted_runs(p_rep, "A PROJECT REPORT", font_size=12.5, bold_default=True)
    
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(2)
    p_sub.paragraph_format.space_after = Pt(2)
    add_formatted_runs(p_sub, "Submitted by", font_size=11.0, italic_default=True)
    
    p_names = doc.add_paragraph()
    p_names.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_names.paragraph_format.space_before = Pt(2)
    p_names.paragraph_format.space_after = Pt(6)
    add_formatted_runs(p_names, "VISHAL RASWANTH (RA2411003050031)\nDHARSHINI. E (RA2411003050048)", font_size=11.5, bold_default=True)
    
    p_guid = doc.add_paragraph()
    p_guid.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_guid.paragraph_format.space_before = Pt(2)
    p_guid.paragraph_format.space_after = Pt(2)
    add_formatted_runs(p_guid, "Under the guidance of", font_size=11.0, italic_default=True)
    
    p_guide_name = doc.add_paragraph()
    p_guide_name.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_guide_name.paragraph_format.space_before = Pt(2)
    p_guide_name.paragraph_format.space_after = Pt(1)
    add_formatted_runs(p_guide_name, "Dr. S. Kanaga Suba Raja", font_size=11.5, bold_default=True)
    
    p_guide_desig = doc.add_paragraph()
    p_guide_desig.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_guide_desig.paragraph_format.space_before = Pt(0)
    p_guide_desig.paragraph_format.space_after = Pt(6)
    add_formatted_runs(p_guide_desig, "Professor and Head, Department of Computer Science and Engineering", font_size=10.5)
    
    p_req = doc.add_paragraph()
    p_req.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_req.paragraph_format.space_before = Pt(2)
    p_req.paragraph_format.space_after = Pt(1)
    add_formatted_runs(p_req, "In Partial Fulfillment of the Requirements\nfor the Degree of", font_size=10.5)
    
    p_deg = doc.add_paragraph()
    p_deg.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_deg.paragraph_format.space_before = Pt(2)
    p_deg.paragraph_format.space_after = Pt(1)
    add_formatted_runs(p_deg, "BACHELOR OF TECHNOLOGY", font_size=11.5, bold_default=True)
    
    p_in = doc.add_paragraph()
    p_in.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_in.paragraph_format.space_before = Pt(0)
    p_in.paragraph_format.space_after = Pt(1)
    add_formatted_runs(p_in, "in", font_size=10.5)
    
    p_dept = doc.add_paragraph()
    p_dept.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_dept.paragraph_format.space_before = Pt(1)
    p_dept.paragraph_format.space_after = Pt(6)
    add_formatted_runs(p_dept, "COMPUTER SCIENCE AND ENGINEERING", font_size=11.5, bold_default=True)
    
    logo_path = os.path.join(fig_dir, 'image1.png')
    if os.path.exists(logo_path):
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.space_before = Pt(4)
        p_logo.paragraph_format.space_after = Pt(6)
        r = p_logo.add_run()
        r.add_picture(logo_path, width=Inches(2.2))
        
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.space_before = Pt(2)
    p_inst.paragraph_format.space_after = Pt(2)
    add_formatted_runs(p_inst, "SCHOOL OF COMPUTING\nFACULTY OF ENGINEERING AND TECHNOLOGY\n**SRM INSTITUTE OF SCIENCE AND TECHNOLOGY**\nTIRUCHIRAPPALLI – 621105\n**OCTOBER 2026**", font_size=11.0, bold_default=True)

    # ==================== PAGE 2: BONAFIDE CERTIFICATE ====================
    add_major_heading(doc, "BONAFIDE CERTIFICATE")
    add_body_p(doc, 'Certified that this project report titled “**RETINAXAI: EXPLAINABLE ARTIFICIAL INTELLIGENCE FOR MULTI-STAGE DIABETIC RETINOPATHY SCREENING AND CLINICAL DECISION SUPPORT**” is the bonafide work of **VISHAL RASWANTH [RA2411003050031]** and **DHARSHINI. E [RA2411003050048]**, who carried out the project work under the supervision of **Dr. S. Kanaga Suba Raja**, Professor and Head, Department of Computer Science and Engineering.')
    add_body_p(doc, 'Certified further, that to the best of our knowledge, the work reported herein does not form the basis of any other project report or dissertation on the basis of which a degree or award was conferred earlier on this or any other candidate.')
    
    sig_table = doc.add_table(rows=6, cols=2)
    sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_borderless_table(sig_table)
    sig_data = [
        ["Signature of Guide", "Signature of Head of the Department"],
        ["\n\n\nDr. S. Kanaga Suba Raja", "\n\n\nDr. S. Kanaga Suba Raja"],
        ["Professor and HOD / Guide", "Head of the Department"],
        ["Department of Computer Science and Engineering", "Department of Computer Science and Engineering"],
        ["SRM Institute of Science and Technology", "SRM Institute of Science and Technology"],
        ["Tiruchirappalli, Tamil Nadu", "Tiruchirappalli, Tamil Nadu"]
    ]
    for r_idx, row in enumerate(sig_data):
        for c_idx, cell_text in enumerate(row):
            cell = sig_table.cell(r_idx, c_idx)
            set_cell_margins(cell, top=35, bottom=35, left=50, right=50)
            cp = cell.paragraphs[0]
            cp.paragraph_format.line_spacing = 1.12
            cp.paragraph_format.space_before = Pt(0)
            cp.paragraph_format.space_after = Pt(2)
            bold = (r_idx in [0, 1])
            add_formatted_runs(cp, cell_text, font_size=10.5, bold_default=bold)

    # ==================== PAGE 3: PROJECT PROBLEM STATEMENT ====================
    add_major_heading(doc, "PROJECT PROBLEM STATEMENT")
    add_body_p(doc, "Diabetic Retinopathy (DR) is fundamentally a progressive microvascular complication resulting from chronic hyperglycemia that damages the retinal capillary network. In India, often termed the 'Diabetes Capital of the World,' over 77 million citizens live with diabetes, and epidemiological surveys indicate that one in five already exhibits retinal microvascular lesions—putting over 15 million individuals at imminent risk of preventable blindness.")
    add_body_p(doc, "Herein lies the central paradox of modern diabetic eye care: while timely interventions such as pan-retinal laser photocoagulation and intravitreal anti-VEGF therapy arrest severe visual loss in over 90% of cases, early stages (Mild and Moderate NPDR) remain entirely asymptomatic. Consequently, patients present to tertiary centers only when irreversible structural damage, vitreous hemorrhage, or macular edema occurs.")
    add_body_p(doc, "This operational screening breakdown stems from five foundational systemic failures:")
    add_bullet_p(doc, "**Extreme Specialist Geographic Scarcity:** India has fewer than 25,000 registered ophthalmologists for 1.4 billion citizens (~1:56,000), with over 70% clustered in tier-1 metropolitan cities. In rural districts, the specialist-to-patient ratio exceeds 1:100,000, and tele-reading backlogs span 2 to 6 weeks.")
    add_bullet_p(doc, "**Black-Box Opacity and Clinician Distrust:** Commercial and academic deep learning models output uncalibrated scores without localizing underlying lesions, making them unverifiable in medical jurisprudence and unadoptable in frontline triage.")
    add_bullet_p(doc, "**Severe Clinical Class Skew:** Real-world screening cohorts are heavily long-tailed (~50% healthy vs. 5.27% Severe NPDR). Standard cross-entropy loss heavily optimizes majority classes, leading to catastrophic false-negative misclassifications on sight-threatening stages.")
    add_bullet_p(doc, "**Total Vulnerability to Non-Retinal Inputs:** Conventional models assume every upload is a well-centered fundus photo. When non-retinal images (selfies, documents) or severely blurred captures are submitted, naive models produce confident but spurious medical diagnoses.")
    add_bullet_p(doc, "**Lighting and Hardware Diversity:** Variations across camera optics (high-end Zeiss/Topcon units vs. low-cost handheld smartphone adapters), pupil dilation levels, and ethnic choroidal pigmentation induce severe diagnostic distribution shifts.")
    add_body_p(doc, "**RETINAXAI** directly overcomes these systemic hurdles. We design, implement, and validate an edge-executable, clinician-in-the-loop screening pipeline combining automated HSV chromatic and Laplacian quality gatekeeping, Ben Graham local contrast standardization, compound-scaled EfficientNet-B0 inference, class-imbalanced Focal Loss, and transparent Grad-CAM lesion heatmaps.")

    # ==================== PAGE 4: ABSTRACT ====================
    add_major_heading(doc, "ABSTRACT")
    add_body_p(doc, "Preventable blindness caused by Diabetic Retinopathy (DR) poses an escalating public health crisis across India, where over 77 million individuals live with diabetes. Although timely laser photocoagulation or intravitreal pharmacotherapy arrests visual deterioration in over 90% of progressive cases, community screening remains crippled by acute specialist shortages, manual grading fatigue, and subjective diagnostic variance. While modern deep neural networks achieve high benchmark accuracy, their clinical translation is hindered by uncalibrated black-box predictions, severe class imbalance, and vulnerability to corrupt or non-retinal inputs.")
    add_body_p(doc, "To resolve these barriers, this project presents **RETINAXAI**, an explainable, end-to-end computer vision platform engineered for multi-stage Diabetic Retinopathy screening and accountable clinical decision support. The architecture integrates six core modules: (1) a pre-inference Quality and Authenticity Gatekeeper using HSV chromatic distribution analysis and Laplacian focus variance to intercept non-fundus or severely degraded images; (2) domain-specific Ben Graham preprocessing combining circular boundary masking with local color subtraction ($I_{\\text{norm}} = 4I - 4\\text{Gauss}(I, \\sigma=30) + 128$) to homogenize illumination across heterogeneous fundus cameras; (3) a lightweight EfficientNet-B0 backbone (5.3M weights) fine-tuned with a custom dual-dropout classification head; (4) a modular loss engine integrating Class-Weighted Cross-Entropy and Focal Loss (γ = 2.0) with label smoothing (ε = 0.1) to penalize minority stage errors; (5) multi-view Test-Time Augmentation (TTA) to generate calibrated uncertainty boundaries; and (6) Gradient-weighted Class Activation Mapping (Grad-CAM), projecting 2D lesion heatmaps overlaid directly on retinal microvasculature.")
    add_body_p(doc, "Empirical evaluation on 367 clinical test images from the APTOS 2019 Blindness Detection benchmark demonstrates that RETINAXAI achieves an overall 5-stage accuracy of **72.21%**, a weighted F1-score of **0.7241**, a macro sensitivity of **58.05%**, and a healthy (Stage 0) sensitivity of **95.58%**. Crucially, across all 100 Moderate and 19 Severe DR cases in the unseen benchmark, the system produced **exactly zero false-negatives** into the healthy category, satisfying the non-negotiable safety requirements of primary triage. Deployed as an interactive 8-page Streamlit application with sub-120 ms CPU latency and a memory footprint under 450 MB, RETINAXAI offers an open-source, edge-ready clinical screening solution for rural vision centers.")
    add_body_p(doc, "**Keywords:** Diabetic Retinopathy, Deep Learning, EfficientNet-B0, Explainable AI, Grad-CAM, Ben Graham Preprocessing, Focal Loss, Retinal Fundus Imaging, Clinical Decision Support.")

    # ==================== PAGE 5: ACKNOWLEDGEMENTS ====================
    add_major_heading(doc, "ACKNOWLEDGEMENTS")
    add_body_p(doc, "We express our deepest gratitude to our project guide, **Dr. S. Kanaga Suba Raja**, Professor and Head of the Department of Computer Science and Engineering, SRM Institute of Science and Technology, Tiruchirappalli, for his constant technical guidance, rigorous feedback, and generous encouragement throughout the conceptualization, model development, and empirical evaluation of this research.")
    add_body_p(doc, "We sincerely thank the faculty members and administrative leadership of the School of Computing and Faculty of Engineering and Technology at SRM Institute of Science and Technology for providing the high-performance computing resources, laboratory access, and supportive academic setting essential for training and validating our deep learning architectures.")
    add_body_p(doc, "We also acknowledge the open-source machine learning and medical imaging communities behind PyTorch, Torchvision, Albumentations, OpenCV, Streamlit, and scikit-learn, whose robust libraries formed the bedrock of our software pipeline. Finally, we thank our parents and peers whose constant encouragement sustained our commitment throughout this work.")
    p_ack_names = doc.add_paragraph()
    p_ack_names.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_ack_names.paragraph_format.space_before = Pt(28)
    add_formatted_runs(p_ack_names, "**VISHAL RASWANTH (RA2411003050031)**\n**DHARSHINI. E (RA2411003050048)**", font_size=11.0)

    # ==================== PAGE 6: TABLE OF CONTENTS ====================
    add_major_heading(doc, "TABLE OF CONTENTS")
    toc_items = [
        ("Bonafide Certificate", "2", True, 0.0),
        ("Project Problem Statement", "3", True, 0.0),
        ("Abstract", "4", True, 0.0),
        ("Acknowledgements", "5", True, 0.0),
        ("List of Tables", "7", True, 0.0),
        ("List of Figures", "8", True, 0.0),
        ("Abbreviations and Symbols", "9", True, 0.0),
        ("1. Introduction", "10", True, 0.0),
        ("1.1 Background and Motivation", "10", False, 0.2),
        ("1.2 Problem Statement and Demand of the Problem", "11", False, 0.2),
        ("1.3 Objectives", "11", False, 0.2),
        ("1.4 Scope and Applications", "12", False, 0.2),
        ("1.5 Relevance to Operational Healthcare and Tele-Ophthalmology", "12", False, 0.2),
        ("1.6 Organisation of the Report", "13", False, 0.2),
        ("2. Literature Survey", "14", True, 0.0),
        ("2.1 International Research (20 Papers, 2020–2026)", "14", False, 0.2),
        ("2.2 National Research (10 Papers, 2020–2025)", "17", False, 0.2),
        ("2.3 Comparative Synthesis", "19", False, 0.2),
        ("2.4 Research Gap", "20", False, 0.2),
        ("2.5 Literature Survey Summary Tables", "20", False, 0.2),
        ("3. System Analysis", "22", True, 0.0),
        ("3.1 Existing System", "22", False, 0.2),
        ("3.2 Proposed System", "22", False, 0.2),
        ("3.3 Functional Requirements", "23", False, 0.2),
        ("3.4 Non-Functional Requirements", "23", False, 0.2),
        ("3.5 Hardware Requirements", "24", False, 0.2),
        ("3.6 Software Requirements", "24", False, 0.2),
        ("3.7 Feasibility Study", "24", False, 0.2),
        ("4. System Architecture and Methodology", "25", True, 0.0),
        ("4.1 Overall System Architecture", "25", False, 0.2),
        ("4.2 Component-Level Design", "26", False, 0.2),
        ("4.3 Working Method and Data Flow", "26", False, 0.2),
        ("4.4 Algorithms", "27", False, 0.2),
        ("4.5 Data Acquisition, Augmentation and Feature Engineering", "29", False, 0.2),
        ("5. Coding, Testing, Results and Discussion", "30", True, 0.0),
        ("5.1 Development Environment and Coding", "30", False, 0.2),
        ("5.2 Data Pre-processing", "30", False, 0.2),
        ("5.3 Exploratory Data Analysis", "31", False, 0.2),
        ("5.4 Model Training and Evaluation", "31", False, 0.2),
        ("5.5 Results and Discussion", "32", False, 0.2),
        ("5.6 Hardware and Functional Verification", "34", False, 0.2),
        ("5.7 Limitations and Threats to Validity", "35", False, 0.2),
        ("6. Conclusion and Future Work", "36", True, 0.0),
        ("6.1 Conclusion", "36", False, 0.2),
        ("6.2 Future Work", "37", False, 0.2),
        ("7. Accenture-Style Coding Practice (Supplementary)", "38", True, 0.0),
        ("REFERENCES", "40", True, 0.0),
        ("ANNEXURE I: SOURCE CODE IMPLEMENTATION", "42", True, 0.0),
        ("APPENDIX A: SAMPLE DATASET AND CLINICAL RECORDS", "44", True, 0.0),
    ]
    for title, pg, is_maj, ind in toc_items:
        add_toc_line(doc, title, pg, is_major=is_maj, indent=ind)

    # ==================== PAGE 7: LIST OF TABLES ====================
    add_major_heading(doc, "LIST OF TABLES")
    lot_items = [
        ("Table 2.1: International Literature Summary (20 Papers, 2020–2026)", "20"),
        ("Table 2.2: National Literature Summary (10 Papers, 2020–2025)", "21"),
        ("Table 2.3: Comparative Synthesis of Existing Literature vs. RETINAXAI", "21"),
        ("Table 3.1: Hardware Components of the Triage Prototype", "24"),
        ("Table 3.2: Software Tools and Libraries Used", "24"),
        ("Table 4.1: Architecture Layers, Inputs, Processing, and Outputs", "25"),
        ("Table 4.2: Operational Risk Tier and ICDR Action Mapping", "26"),
        ("Table 4.3: Canonical Retinal Feature Extraction and Engineering Rationale", "29"),
        ("Table 5.1: APTOS 2019 Dataset Partitioning and Stratification Breakdown", "30"),
        ("Table 5.2: Clinical Stage Prevalence in the APTOS 2019 Dataset", "30"),
        ("Table 5.3: Model Settings and Hyperparameter Ranges", "31"),
        ("Table 5.4: Baseline Model Performance on Multi-Class Test Benchmark (367 Samples)", "32"),
        ("Table 5.5: Per-Class Diagnostic Precision, Recall, F1-Score and Support Breakdown", "32"),
        ("Table 5.6: System Inference Latency: Batched vs. Single-Image Execution", "34"),
        ("Table 5.7: Functional Test Scenarios and Clinical Triage Verification", "34"),
    ]
    for title, pg in lot_items:
        add_toc_line(doc, title, pg, is_major=False, indent=0.0)

    # ==================== PAGE 8: LIST OF FIGURES ====================
    add_major_heading(doc, "LIST OF FIGURES")
    lof_items = [
        ("Figure 4.1: End-to-End Architectural Pipeline and Workflow of RETINAXAI", "25"),
        ("Figure 5.1: Class Representation Distribution in APTOS 2019 Benchmark", "31"),
        ("Figure 5.2: Training vs. Validation Loss and Accuracy Curves over 15 Epochs", "31"),
        ("Figure 5.3: Normalized 5×5 Confusion Matrix on 367 Unseen Test Fundus Scans", "33"),
        ("Figure 5.4: Multi-Class Receiver Operating Characteristic (ROC) Curves", "33"),
        ("Figure 5.5: Qualitative Visual Validations: Grad-CAM Saliency across Stages", "35"),
        ("Figure A.1: Source Code — Pre-Inference Authenticity & Blur Gatekeeper", "42"),
        ("Figure A.2: Source Code — Ben Graham Color Subtraction Preprocessing", "42"),
        ("Figure A.3: Source Code — EfficientNet-B0 Classifier with Dual-Dropout Head", "43"),
        ("Figure A.4: Source Code — Real-Time Grad-CAM Saliency Engine", "43"),
    ]
    for title, pg in lof_items:
        add_toc_line(doc, title, pg, is_major=False, indent=0.0)

    # ==================== PAGE 9: ABBREVIATIONS AND SYMBOLS ====================
    add_major_heading(doc, "ABBREVIATIONS AND SYMBOLS")
    abbr_headers = ["Abbreviation", "Complete Scientific / Engineering Description"]
    abbr_data = [
        ["AI", "Artificial Intelligence"],
        ["XAI", "Explainable Artificial Intelligence"],
        ["DR", "Diabetic Retinopathy"],
        ["NPDR", "Non-Proliferative Diabetic Retinopathy"],
        ["PDR", "Proliferative Diabetic Retinopathy"],
        ["DME", "Diabetic Macular Edema"],
        ["ICDR", "International Clinical Diabetic Retinopathy Disease Severity Scale"],
        ["CNN", "Convolutional Neural Network"],
        ["ViT", "Vision Transformer"],
        ["Grad-CAM", "Gradient-weighted Class Activation Mapping"],
        ["TTA", "Test-Time Augmentation"],
        ["FL", "Focal Loss"],
        ["WCE", "Class-Weighted Cross Entropy"],
        ["HSV", "Hue, Saturation, Value Color Space"],
        ["ROC-AUC", "Receiver Operating Characteristic — Area Under Curve"],
        ["PR-AUC", "Precision-Recall — Area Under Curve"],
        ["IDF", "International Diabetes Federation"],
        ["PHC", "Primary Health Centre"],
        ["VEGF", "Vascular Endothelial Growth Factor"],
        ["OCT", "Optical Coherence Tomography"],
        ["MPS", "Metal Performance Shaders (Apple Silicon GPU Acceleration)"],
        ["CUDA", "Compute Unified Device Architecture (NVIDIA)"],
    ]
    add_table_data(doc, abbr_headers, abbr_data, col_widths=[1.5, 5.0])

print("Preliminary pages defined.")

# Chapter definitions using the v2 formatting (Times New Roman 11.5pt, 1.18 line spacing)

def add_chapter_1(doc):
    add_major_heading(doc, "CHAPTER 1 — INTRODUCTION")
    add_subheading(doc, "1.1 Background and Overview")
    add_body_p(doc, "Diabetic Retinopathy (DR) is fundamentally an insidious vascular breakdown that unfolds in the light-sensitive retina of the human eye. When an individual lives with poorly regulated blood glucose over several years, persistent metabolic stress damages the delicate endothelial lining of retinal capillaries. Supportive pericytes gradually die off, causing vessel walls to weaken and balloon into microscopic outpouchings known as **microaneurysms**. As the blood-retinal barrier fails, lipid particles and serous fluids seep into retinal parenchyma, precipitating as sharp, yellow lipid deposits termed **hard exudates**. Simultaneously, ruptured capillaries bleed into the retinal nerve fiber layer, manifesting as flame-shaped hemorrhages and deep dot-blot hemorrhages.")
    add_body_p(doc, "If left unchecked, widespread capillary closure chokes off blood supply to extensive retinal zones, causing localized ischemia. In a desperate attempt to restore oxygenation, starved retinal cells pump out excessive Vascular Endothelial Growth Factor (VEGF). This chemical trigger drives the frantic sprouting of fragile, disorganized new blood vessels—a stage known as **Proliferative Diabetic Retinopathy (PDR)**. These delicate vessels frequently bleed directly into the vitreous gel, abruptly plunging the patient into darkness, or contract into fibrous bands that exert mechanical traction on the retina, eventually tearing it away from the pigment epithelium in a catastrophic tractional detachment.")
    add_body_p(doc, "Globally, the International Diabetes Federation estimates that over 537 million adults currently live with diabetes, projected to climb toward 783 million by 2045. Within this epidemiological crisis, India occupies a deeply vulnerable position. As the 'Diabetes Capital of the World,' India is home to over 77 million diagnosed diabetic adults, with millions more remaining undiagnosed. Extensive clinical surveys across Tamil Nadu, Maharashtra, and Karnataka indicate that 18% to 22% of Indian diabetic individuals exhibit observable signs of DR, translating to more than **15 million citizens living under the immediate shadow of progressive blindness**.")

    add_subheading(doc, "1.2 Motivation for Developing the Project")
    add_body_p(doc, "The primary tragedy of diabetic blindness is that it is almost entirely preventable. When detected early—at Mild or Moderate Non-Proliferative stages—standard outpatient interventions like targeted pan-retinal laser photocoagulation or intravitreal anti-VEGF therapy arrest severe vision loss in over 90% of cases in a twenty-minute clinic visit. However, early DR produces zero ocular pain, notices no refractive change, and retains 20/20 central visual acuity because the fovea is not yet engulfed by edema. Consequently, patients rarely seek care until symptoms become alarming—sudden dark floaters from a vitreous hemorrhage or profound central blur from macular edema—by which time structural damage is already advanced (Stage 3 or 4).")
    add_body_p(doc, "Overcoming this bottleneck requires moving diagnostic capability out of tertiary metropolitan hospitals directly into frontline Primary Health Centres (PHCs) and community vision centers. Empowering rural health workers and optometrists with an automated, reliable, and explainable AI screening tool running locally on standard laptop hardware without expensive cloud subscriptions enables thousands of high-risk patients to be triaged months before suffering irreversible vision loss. This humanitarian mission motivated the creation of **RETINAXAI**.")

    add_subheading(doc, "1.3 Demand and Necessity of the Problem Statement")
    add_body_p(doc, "Traditional diagnostic pathways in Indian ophthalmology rely on dilated slit-lamp biomicroscopy and indirect ophthalmoscopy by certified specialists. This model fails to scale nationally due to five systemic roadblocks:")
    add_numbered_p(doc, 1, "**Extreme Specialist Geographic Deficit:** India has ~25,000 ophthalmologists serving 1.4 billion people (1:56,000 ratio), with >70% practicing in tier-1 metropolitan cities. In rural districts, the ratio exceeds 1:100,000, and tele-ophthalmology reading centers suffer from 2-to-6-week backlogs.")
    add_numbered_p(doc, 2, "**Black-Box Opacity and Clinician Distrust:** Commercial and academic AI models return raw probability vectors without localizing lesions. In high-stakes medical triage, unexplained predictions cannot be legally or ethically incorporated into patient care plans.")
    add_numbered_p(doc, 3, "**Severe Clinical Class Skew:** In real-world screening cohorts, normal eyes represent ~50% of visits, whereas vision-threatening Severe NPDR represents barely 5.27%. Standard cross-entropy loss favors the majority class, frequently missing critical stages.")
    add_numbered_p(doc, 4, "**Total Vulnerability to Garbage Inputs:** Existing automated pipelines assume all uploads are clean fundus images. Non-retinal photos (selfies, documents) or severely blurred frames produce spurious confident diagnoses.")
    add_numbered_p(doc, 5, "**Illumination and Camera Hardware Disparities:** Fundus cameras vary from high-end desktop units to handheld smartphone scopes. Flash variations, pupil dilation differences, and ethnic choroidal pigmentation shifts severely degrade uncalibrated models.")

    add_subheading(doc, "1.4 Objectives and Scope of the Project")
    add_body_p(doc, "To resolve each systemic limitation, the RETINAXAI project was engineered around six concrete technical objectives:")
    add_numbered_p(doc, 1, "**Automated Quality Gatekeeper:** Design a pre-inference routine using HSV chromatic analysis and Laplacian focus variance to automatically reject non-fundus or severely degraded images before neural processing.")
    add_numbered_p(doc, 2, "**Domain-Specific Contrast Standardization:** Implement Ben Graham's local average color subtraction with automated circular boundary cropping to eliminate vignetting and standardize illumination across cameras.")
    add_numbered_p(doc, 3, "**Lightweight Compound-Scaled Backbone:** Fine-tune an EfficientNet-B0 CNN (5.3M weights) with a custom dual-dropout classification head for low-latency CPU inference without requiring dedicated GPUs.")
    add_numbered_p(doc, 4, "**Modular Class-Imbalance Mitigation:** Formulate Class-Weighted Cross-Entropy and Focal Loss (γ = 2.0) with label smoothing (ε = 0.1) to heavily penalize errors on minority severe and proliferative stages.")
    add_numbered_p(doc, 5, "**Transparent Lesion-Level Explainability:** Implement Grad-CAM hooked to the final convolutional feature extractor, generating localized 2D heatmaps overlaid on microvascular lesions.")
    add_numbered_p(doc, 6, "**Edge-Ready Clinical Triage Interface:** Deploy an interactive Streamlit dashboard integrating multi-view Test-Time Augmentation (TTA), confidence distributions, referral warning banners, and one-click PDF report export.")

    add_subheading(doc, "1.5 Scope and Real-World Application Areas")
    add_body_p(doc, "The scope of RETINAXAI covers automated 5-stage grading per the International Clinical Diabetic Retinopathy (ICDR) scale: Stage 0 (No DR), Stage 1 (Mild NPDR), Stage 2 (Moderate NPDR), Stage 3 (Severe NPDR), and Stage 4 (Proliferative DR). Primary deployment domains include:")
    add_bullet_p(doc, "**Rural Primary Health Centres (PHCs):** Frontline triage assistant enabling general nurses to screen diabetic patients during routine checkups and refer those needing specialist care.")
    add_bullet_p(doc, "**Mobile Tele-Ophthalmology Screening Vans:** Offline diagnostic engine delivering assessments in under 150 ms per patient in remote camps without requiring internet connectivity.")
    add_bullet_p(doc, "**Hospital Second-Reader Decision Support:** Tireless second-reader in busy eye hospitals, pre-flagging suspicious microaneurysms and hard exudates via Grad-CAM heatmaps.")

    add_subheading(doc, "1.6 Relevance to Operational Healthcare and Tele-Ophthalmology")
    add_body_p(doc, "In community healthcare screening, the penalty for a false negative on sight-threatening disease is infinitely higher than a false positive on a healthy patient. A missed Severe NPDR case leads to irreversible blindness, whereas a false-positive healthy case merely leads to a harmless specialist re-check. RETINAXAI was built around this clinical safety asymmetry: our benchmark achieves **95.58% sensitivity on healthy eyes** (safely clearing 95% of healthy visitors) while producing **zero false-negatives from Moderate and Severe DR into the healthy category**.")

    add_subheading(doc, "1.7 Expected Contributions of the Proposed System")
    add_bullet_p(doc, "A fail-safe input verification algorithm in `src/image_quality.py` that intercepts non-retinal photos and blurred frames before GPU tensor ingestion.")
    add_bullet_p(doc, "A robust adaptation of Ben Graham preprocessing in `src/dataset.py` that standardizes illumination across diverse camera optics and ethnic fundus pigmentation.")
    add_bullet_p(doc, "An empirically audited EfficientNet-B0 architecture balancing high representational capacity with a minimal 5.3M parameter footprint for sub-120 ms CPU inference.")
    add_bullet_p(doc, "A modular loss engine in `src/losses.py` combining Focal Loss (γ = 2.0) and class weighting to suppress majority-class bias.")
    add_bullet_p(doc, "A clinically calibrated Grad-CAM attribution module in `src/explainability.py` providing transparent visual justifications to consulting ophthalmologists.")
    add_bullet_p(doc, "A fully interactive Streamlit clinical decision support application in `app.py` with one-click audit-ready PDF export.")

    add_subheading(doc, "1.8 Organisation of the Report")
    add_body_p(doc, "The remainder of this report is organized as follows: Chapter 2 reviews 30 recent peer-reviewed publications (20 International, 10 National Indian studies) and outlines research gaps. Chapter 3 provides system analysis, specifications, and feasibility. Chapter 4 details system architecture, mathematical formulations, and algorithms. Chapter 5 presents coding, exploratory data analysis, hyperparameter tuning, empirical results, and latency benchmarks. Chapter 6 concludes with future work. Chapter 7 presents Accenture-style technical coding modules. References, Annexure I (Source Code), and Appendix A (Sample Dataset) conclude the report.")

print("Chapter 1 defined in v2.")

from build_full_report_reduced import (
    add_chapter_2, add_chapter_3, add_chapter_4,
    add_chapter_5, add_chapter_6, add_chapter_7,
    add_references, add_annexure_and_appendix
)

def generate_report_v2(out_path="RetinaXAI_Project_Report_Final.docx"):
    doc = Document()
    
    # 1. Page Margins & Section Setup
    for sec in doc.sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)
        
        # Clear Header
        sec.header.is_linked_to_previous = False
        for p in sec.header.paragraphs:
            p.text = ""
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            
        # Centered dynamic page number in footer
        footer = sec.footer
        f_p = footer.paragraphs[0]
        f_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        f_p.paragraph_format.space_before = Pt(0)
        f_p.paragraph_format.space_after = Pt(0)
        f_run = f_p.add_run()
        f_run.font.name = "Times New Roman"
        f_run.font.size = Pt(11)
        f_run.font.color.rgb = RGBColor(0, 0, 0)
        
        fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
        instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> PAGE </w:instrText>' % nsdecls('w'))
        fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
        fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
        f_run._r.append(fldChar1)
        f_run._r.append(instrText)
        f_run._r.append(fldChar2)
        f_run._r.append(fldChar3)

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(11.5)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.18
    normal_style.paragraph_format.space_after = Pt(3.5)
    normal_style.paragraph_format.space_before = Pt(0)

    # Build all sections in proper order
    add_preliminary_pages(doc)
    add_chapter_1(doc)
    add_chapter_2(doc)
    add_chapter_3(doc)
    add_chapter_4(doc)
    add_chapter_5(doc)
    add_chapter_6(doc)
    add_chapter_7(doc)
    add_references(doc)
    add_annexure_and_appendix(doc)

    doc.save(out_path)
    print(f"Report v2 successfully saved to {out_path} ({os.path.getsize(out_path)} bytes)")

if __name__ == '__main__':
    generate_report_v2()
