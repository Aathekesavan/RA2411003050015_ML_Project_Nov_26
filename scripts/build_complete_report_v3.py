# scripts/build_complete_report_v3.py
# Production generator for RETINAXAI Project Report in SRM format (Target: 41-43 pages)

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

def set_cell_margins(cell, top=40, bottom=40, left=60, right=60):
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
    h.paragraph_format.space_before = Pt(8)
    h.paragraph_format.space_after = Pt(2)
    h.paragraph_format.keep_with_next = True
    add_formatted_runs(h, text, font_size=12.0, bold_default=True)
    return h

def add_subsubheading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(1.5)
    p.paragraph_format.keep_with_next = True
    add_formatted_runs(p, text, font_size=11.0, bold_default=True)
    return p

def add_body_p(doc, text, space_after=3.0, line_spacing=1.15):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    add_formatted_runs(p, text, font_size=11.5)
    return p

def add_bullet_p(doc, text, space_after=1.8):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.left_indent = Inches(0.25)
    add_formatted_runs(p, f"•  {text}", font_size=11.5)
    return p

def add_numbered_p(doc, num, text, space_after=1.8):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.left_indent = Inches(0.25)
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
    p_img.paragraph_format.space_before = Pt(5)
    p_img.paragraph_format.space_after = Pt(2)
    r = p_img.add_run()
    r.add_picture(img_path, width=Inches(width_in))
    
    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(1)
    p_cap.paragraph_format.space_after = Pt(5)
    add_formatted_runs(p_cap, caption, font_size=9.5, bold_default=True, italic_default=True)

def add_code_box(doc, code_text):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, "F9FAFB")
    set_cell_margins(cell, top=45, bottom=45, left=75, right=75)
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
            set_cell_margins(cell, top=28, bottom=28, left=50, right=50)
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
    p.paragraph_format.space_after = Pt(0.5)
    p.paragraph_format.line_spacing = 1.02
    p.paragraph_format.left_indent = Inches(indent)
    p.paragraph_format.tab_stops.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
    
    r_title = p.add_run(title)
    r_title.font.name = "Times New Roman"
    r_title.font.size = Pt(9.0)
    r_title.font.color.rgb = RGBColor(0, 0, 0)
    if is_major:
        r_title.bold = True
        
    r_tab = p.add_run(f"\t{page_str}")
    r_tab.font.name = "Times New Roman"
    r_tab.font.size = Pt(9.0)
    r_tab.font.color.rgb = RGBColor(0, 0, 0)
    if is_major:
        r_tab.bold = True

print("v3 helper functions initialized.")

from make_reduced_report import (
    create_report_doc
)

from build_complete_report_v2 import add_preliminary_pages

from build_full_report_reduced import (
    add_chapter_2, add_chapter_3, add_chapter_4,
    add_chapter_5, add_chapter_6, add_chapter_7,
    add_references, add_annexure_and_appendix
)

def add_chapter_1_tight(doc):
    add_major_heading(doc, "CHAPTER 1 — INTRODUCTION")
    add_subheading(doc, "1.1 Background and Overview")
    add_body_p(doc, "Diabetic Retinopathy (DR) is fundamentally an insidious vascular breakdown that unfolds in the light-sensitive retina of the human eye. When an individual lives with poorly regulated blood glucose over several years, persistent metabolic stress damages the delicate endothelial lining of retinal capillaries. Supportive pericytes gradually die off, weakening vessel walls into microscopic outpouchings known as **microaneurysms**. As the blood-retinal barrier fails, lipid particles and serous fluids seep into retinal parenchyma, precipitating as sharp, yellow lipid deposits termed **hard exudates**. Simultaneously, ruptured capillaries bleed into the retinal nerve fiber layer, manifesting as flame-shaped and deep dot-blot hemorrhages.")
    add_body_p(doc, "If left unchecked, widespread capillary closure chokes off blood supply to extensive retinal zones, causing localized ischemia. In a desperate attempt to restore oxygenation, starved retinal cells pump out excessive Vascular Endothelial Growth Factor (VEGF). This chemical trigger drives the frantic sprouting of fragile, disorganized new blood vessels—a stage known as **Proliferative Diabetic Retinopathy (PDR)**. These delicate vessels bleed directly into the vitreous gel, abruptly plunging the patient into darkness, or contract into fibrous bands that exert mechanical traction on the retina, eventually tearing it away from the pigment epithelium in a catastrophic tractional detachment.")
    add_body_p(doc, "Globally, the International Diabetes Federation estimates that over 537 million adults live with diabetes, projected to climb toward 783 million by 2045. Within this epidemiological crisis, India occupies a deeply vulnerable position. As the 'Diabetes Capital of the World,' India is home to over 77 million diagnosed diabetic adults, with millions more remaining undiagnosed. Extensive clinical surveys across Tamil Nadu, Maharashtra, and Karnataka indicate that 18% to 22% of Indian diabetic individuals exhibit observable signs of DR, translating to more than **15 million citizens living under the immediate shadow of progressive blindness**.")

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

def generate_report_v3(out_path="RetinaXAI_Project_Report_Final.docx"):
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
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(3.0)
    normal_style.paragraph_format.space_before = Pt(0)

    # Build all sections in proper order
    add_preliminary_pages(doc)
    add_chapter_1_tight(doc)
    add_chapter_2(doc)
    add_chapter_3(doc)
    add_chapter_4(doc)
    add_chapter_5(doc)
    add_chapter_6(doc)
    add_chapter_7(doc)
    add_references(doc)
    add_annexure_and_appendix(doc)

    doc.save(out_path)
    print(f"Report v3 successfully saved to {out_path} ({os.path.getsize(out_path)} bytes)")

if __name__ == '__main__':
    generate_report_v3()
