import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def patch_report():
    input_path = "SentinelX_Project_Report_Clean.docx"
    output_path = "SentinelX_Project_Report_Final.docx"
    
    doc = docx.Document(input_path)
    print(f"Loaded {input_path}: {len(doc.paragraphs)} paragraphs, {len(doc.tables)} tables")

    def add_image_before(target_p, img_path, width_inches, caption_text):
        if not os.path.exists(img_path):
            print(f"Warning: {img_path} not found!")
            return
        
        # Insert image paragraph before target_p
        p_img = target_p.insert_paragraph_before()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(12)
        p_img.paragraph_format.space_after = Pt(3)
        run_img = p_img.add_run()
        run_img.add_picture(img_path, width=Inches(width_inches))

        # Insert caption paragraph before target_p
        p_cap = target_p.insert_paragraph_before()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(2)
        p_cap.paragraph_format.space_after = Pt(12)
        p_cap.paragraph_format.line_spacing = 1.15
        run_cap = p_cap.add_run(caption_text)
        run_cap.font.name = "Times New Roman"
        run_cap.font.size = Pt(10)
        run_cap.font.italic = True
        run_cap.font.color.rgb = RGBColor(55, 65, 81)
        print(f"Inserted image {img_path} with caption: {caption_text}")

    # 1. Figure 4.1: Architecture Diagram in Section 4.1
    # Locate Paragraph "Table 4.1: Architecture Layers, Inputs, Processing, and Outputs"
    target_4_1 = None
    for p in doc.paragraphs:
        if "Table 4.1: Architecture Layers, Inputs, Processing, and Outputs" in p.text:
            target_4_1 = p
            break
    if target_4_1:
        add_image_before(
            target_4_1,
            "docs/figures/fig1_architecture.png",
            5.8,
            "Figure 4.1: Overall System Architecture of the SentinelX-Shift Unit (300 DPI Block Diagram)."
        )

    # 2. Figure 4.2: Deduplication Audit in Section 4.5.2
    # Locate Paragraph "4.5.3 Canonical Feature Engineering"
    target_4_2 = None
    for p in doc.paragraphs:
        if "4.5.3 Canonical Feature Engineering" in p.text:
            target_4_2 = p
            break
    if target_4_2:
        add_image_before(
            target_4_2,
            "docs/figures/fig2_deduplication.png",
            5.8,
            "Figure 4.2: Feature Sanitization and Deduplication Pipeline across 8 Partitions (21.03% Duplicates Purged)."
        )

    # 3. Add Evaluation Parameters (5.4.3) in Chapter 5.4
    # Locate Paragraph "5.5 Results and Discussion"
    target_eval = None
    for p in doc.paragraphs:
        if "5.5 Results and Discussion" in p.text:
            target_eval = p
            break
    if target_eval:
        p_h = target_eval.insert_paragraph_before()
        p_h.style = 'Heading 3'
        p_h.paragraph_format.space_before = Pt(10)
        p_h.paragraph_format.space_after = Pt(3)
        r_h = p_h.add_run("5.4.3 Evaluation Parameters")
        r_h.font.name = "Times New Roman"
        r_h.font.size = Pt(12)
        r_h.bold = True

        p_desc = target_eval.insert_paragraph_before()
        p_desc.paragraph_format.space_before = Pt(0)
        p_desc.paragraph_format.space_after = Pt(6)
        p_desc.paragraph_format.line_spacing = 1.15
        r_d = p_desc.add_run(
            "To evaluate model resilience under realistic operational conditions, performance is measured using four canonical parameters:\n"
            "• Receiver Operating Characteristic Area Under Curve (ROC-AUC): Quantifies the global discrimination boundary across all classification thresholds.\n"
            "• Precision-Recall Area Under Curve (PR-AUC): Evaluates classifier precision under severe operational class imbalances (1% and 5% attack prevalence).\n"
            "• Recall @ 1% False Alarm Rate (Recall@1%FAR): Measures the percentage of true attacks successfully detected when false alarms are strictly capped at <= 1.0%.\n"
            "• System Inference Latency: Mean execution latency per flow in milliseconds under single-flow and batched CPU execution modes (strict SLA: <= 10.0 ms)."
        )
        r_d.font.name = "Times New Roman"
        r_d.font.size = Pt(11)
        print("Inserted Section 5.4.3 Evaluation Parameters")

    # 4. Figure 5.2: Multi-Seed LOFO Performance Bar Chart (Figure 5.2 in List of Figures)
    # Locate Paragraph "The Zero-Day Generalization Divide & Joint Holdout Finding"
    target_5_2 = None
    for p in doc.paragraphs:
        if "The Zero-Day Generalization Divide & Joint Holdout Finding" in p.text:
            target_5_2 = p
            break
    if target_5_2:
        add_image_before(
            target_5_2,
            "docs/figures/fig3_lofo_performance.png",
            5.8,
            "Figure 5.2: Multi-Seed LOFO Performance: Volumetric vs. Stealthy Collapse (Bar Chart, 300 DPI)."
        )

    # 5. Figure 5.3: Joint Holdout Line Chart
    # Locate Paragraph "5.5.2 Cross-Dataset Evaluation (UNSW-NB15)"
    target_5_3 = None
    for p in doc.paragraphs:
        if "5.5.2 Cross-Dataset Evaluation (UNSW-NB15)" in p.text:
            target_5_3 = p
            break
    if target_5_3:
        add_image_before(
            target_5_3,
            "docs/figures/fig4_joint_holdout.png",
            5.8,
            "Figure 5.3: Joint Holdout Degradation Curve ({BruteForce, WebAttack}) (Line Chart, 300 DPI)."
        )

    # 6. Figure 5.4: Cross-Dataset ROC-AUC Performance Drop
    # Locate Paragraph "5.5.3 Audited Explanation-Stability Result: Negative Finding"
    target_5_4 = None
    for p in doc.paragraphs:
        if "5.5.3 Audited Explanation-Stability Result: Negative Finding" in p.text:
            target_5_4 = p
            break
    if target_5_4:
        add_image_before(
            target_5_4,
            "docs/figures/fig5_cross_dataset.png",
            5.8,
            "Figure 5.4: Cross-Dataset ROC-AUC Performance Drop on UNSW-NB15 (300 DPI)."
        )

    # 7. Figure 5.6: Latency Breakdown Bar Chart
    # Locate Paragraph "5.6 Hardware and Functional Verification"
    target_5_6 = None
    for p in doc.paragraphs:
        if "5.6 Hardware and Functional Verification" in p.text:
            target_5_6 = p
            break
    if target_5_6:
        add_image_before(
            target_5_6,
            "docs/figures/fig6_latency.png",
            5.8,
            "Figure 5.6: Latency Breakdown: Batched Inference vs. Single-Flow Calls (300 DPI)."
        )

    doc.save(output_path)
    # Also save as SentinelX_Project_Report_Fixed.docx
    doc.save("SentinelX_Project_Report_Fixed.docx")
    print(f"Saved patched document to {output_path} and SentinelX_Project_Report_Fixed.docx ({os.path.getsize(output_path)} bytes)")

if __name__ == '__main__':
    patch_report()
