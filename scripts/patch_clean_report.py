import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

def patch_clean_report():
    input_path = "SentinelX_Project_Report_Clean.docx"
    output_path = "SentinelX_Project_Report_Final.docx"
    
    doc = docx.Document(input_path)
    print(f"Loaded {input_path}: {len(doc.paragraphs)} paragraphs, {len(doc.tables)} tables")

    def add_image_before(target_p, img_path, width_inches, caption_text):
        if not os.path.exists(img_path):
            print(f"Warning: {img_path} not found!")
            return
        
        # 1. Insert image paragraph before target_p
        p_img = target_p.insert_paragraph_before()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(14)
        p_img.paragraph_format.space_after = Pt(3)
        run_img = p_img.add_run()
        run_img.add_picture(img_path, width=Inches(width_inches))

        # 2. Insert caption paragraph before target_p
        p_cap = target_p.insert_paragraph_before()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_before = Pt(2)
        p_cap.paragraph_format.space_after = Pt(14)
        p_cap.paragraph_format.line_spacing = 1.15
        run_cap = p_cap.add_run(caption_text)
        run_cap.font.name = "Times New Roman"
        run_cap.font.size = Pt(10)
        run_cap.font.italic = True
        run_cap.font.color.rgb = RGBColor(55, 65, 81)
        print(f"Inserted image {img_path} with caption: {caption_text}")

    # Helper: find paragraph in chapter body (i > 120 to bypass TOC / preliminary lists)
    def find_body_paragraph(target_substr, min_idx=120):
        for i in range(min_idx, len(doc.paragraphs)):
            p = doc.paragraphs[i]
            if target_substr in p.text and '\t' not in p.text:
                return i, p
        return None, None

    # 1. Figure 4.1: Architecture Diagram in Section 4.1
    idx_4_1, p_4_1 = find_body_paragraph("Table 4.1: Architecture Layers")
    if p_4_1:
        print(f"Found 4.1 target at P{idx_4_1}")
        add_image_before(
            p_4_1,
            "docs/figures/fig1_architecture.png",
            5.8,
            "Figure 4.1: Overall System Architecture of the SentinelX-Shift Unit (300 DPI Block Diagram)."
        )

    # 2. Figure 4.2: Deduplication Audit in Section 4.5.2
    idx_4_2, p_4_2 = find_body_paragraph("4.5.3 Canonical Feature Engineering")
    if p_4_2:
        print(f"Found 4.5.2 target at P{idx_4_2}")
        add_image_before(
            p_4_2,
            "docs/figures/fig2_deduplication.png",
            5.8,
            "Figure 4.2: Feature Sanitization and Deduplication Pipeline across 8 Partitions (21.03% Duplicates Purged)."
        )

    # 3. Add Evaluation Parameters (5.4.3) in Chapter 5.4
    idx_eval, p_eval = find_body_paragraph("5.5 Results and Discussion")
    if p_eval:
        print(f"Found 5.4.3 target at P{idx_eval}")
        p_h = p_eval.insert_paragraph_before()
        p_h.style = 'Heading 3'
        p_h.paragraph_format.space_before = Pt(12)
        p_h.paragraph_format.space_after = Pt(4)
        r_h = p_h.add_run("5.4.3 Evaluation Parameters")
        r_h.font.name = "Times New Roman"
        r_h.font.size = Pt(12)
        r_h.bold = True

        p_desc = p_eval.insert_paragraph_before()
        p_desc.paragraph_format.space_before = Pt(0)
        p_desc.paragraph_format.space_after = Pt(8)
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

    # 4. Figure 5.2: Multi-Seed LOFO Performance Bar Chart
    idx_5_2, p_5_2 = find_body_paragraph("The Zero-Day Generalization Divide & Joint Holdout Finding")
    if p_5_2:
        print(f"Found 5.5.1 target at P{idx_5_2}")
        add_image_before(
            p_5_2,
            "docs/figures/fig3_lofo_performance.png",
            5.8,
            "Figure 5.2: Multi-Seed LOFO Performance: Volumetric vs. Stealthy Collapse (Bar Chart, 300 DPI)."
        )

    # 5. Figure 5.3: Joint Holdout Line Chart
    idx_5_3, p_5_3 = find_body_paragraph("5.5.2 Cross-Dataset Evaluation (UNSW-NB15)")
    if p_5_3:
        print(f"Found Joint Holdout target at P{idx_5_3}")
        add_image_before(
            p_5_3,
            "docs/figures/fig4_joint_holdout.png",
            5.8,
            "Figure 5.3: Joint Holdout Degradation Curve ({BruteForce, WebAttack}) (Line Chart, 300 DPI)."
        )

    # 6. Figure 5.4: Cross-Dataset ROC-AUC Performance Drop
    idx_5_4, p_5_4 = find_body_paragraph("5.5.3 Audited Explanation-Stability Result: Negative Finding")
    if p_5_4:
        print(f"Found Cross-Dataset target at P{idx_5_4}")
        add_image_before(
            p_5_4,
            "docs/figures/fig5_cross_dataset.png",
            5.8,
            "Figure 5.4: Cross-Dataset ROC-AUC Performance Drop on UNSW-NB15 (300 DPI)."
        )

    # 7. Figure 5.6: Latency Breakdown Bar Chart
    idx_5_6, p_5_6 = find_body_paragraph("5.6 Hardware and Functional Verification")
    if p_5_6:
        print(f"Found Latency target at P{idx_5_6}")
        add_image_before(
            p_5_6,
            "docs/figures/fig6_latency.png",
            5.8,
            "Figure 5.6: Latency Breakdown: Batched Inference vs. Single-Flow Calls (300 DPI)."
        )

    doc.save(output_path)
    doc.save("SentinelX_Project_Report_Fixed.docx")
    print(f"Saved patched document to {output_path} ({os.path.getsize(output_path)} bytes)")

if __name__ == '__main__':
    patch_clean_report()
