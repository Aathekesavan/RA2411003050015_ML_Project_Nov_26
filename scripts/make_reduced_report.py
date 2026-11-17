# scripts/make_reduced_report.py
# High-precision document generator for RETINAXAI Project Report in SRM format (40-45 pages)

import os
import sys
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

from build_retinaxai_reduced import (
    set_cell_background, set_cell_margins, set_table_borders, set_borderless_table,
    add_formatted_runs, add_major_heading, add_subheading, add_subsubheading,
    add_body_p, add_bullet_p, add_numbered_p, add_figure, add_code_box, add_table_data, add_toc_line,
    fig_dir
)

def create_report_doc():
    doc = Document()
    
    # Margins & Section Setup
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
            
        # Footer
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
    normal_style.font.size = Pt(11.0)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(3.0)
    normal_style.paragraph_format.space_before = Pt(0)

    # ==================== PAGE 1: COVER PAGE ====================
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(12)
    p_title.paragraph_format.space_after = Pt(10)
    add_formatted_runs(p_title, "RETINAXAI: EXPLAINABLE ARTIFICIAL INTELLIGENCE FOR MULTI-STAGE DIABETIC RETINOPATHY SCREENING AND CLINICAL DECISION SUPPORT", font_size=14.0, bold_default=True)
    
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
        r.add_picture(logo_path, width=Inches(2.1))
        
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

    return doc

print("create_report_doc initialized.")
