import os
import win32com.client

def export_pptx(pptx_rel_path, out_dir):
    abs_pptx = os.path.abspath(pptx_rel_path)
    abs_out = os.path.abspath(out_dir)
    os.makedirs(abs_out, exist_ok=True)
    
    ppt_app = win32com.client.Dispatch("PowerPoint.Application")
    ppt_app.Visible = 1
    
    try:
        prs = ppt_app.Presentations.Open(abs_pptx, WithWindow=False)
        base_name = os.path.splitext(os.path.basename(abs_pptx))[0]
        pdf_path = os.path.join(abs_out, f"{base_name}.pdf")
        
        # Save as PDF (format 32 = ppSaveAsPDF)
        prs.SaveAs(pdf_path, 32)
        print(f"Exported PDF: {pdf_path}")
        
        # Export each slide as PNG
        for i, slide in enumerate(prs.Slides):
            slide_png = os.path.join(abs_out, f"{base_name}_slide_{i+1}.png")
            slide.Export(slide_png, "PNG", 1920, 1080)
            print(f"Exported Slide {i+1} PNG: {slide_png}")
            
        prs.Close()
    finally:
        try:
            ppt_app.Quit()
        except:
            pass

if __name__ == '__main__':
    print("Exporting RetinaXAI presentation...")
    export_pptx('RetinaXAI_Project_Review_Presentation_Template.pptx', 'docs/presentation_exports/retinaxai')
    print("\nExporting SentinelX presentation...")
    export_pptx('SentinelX_Project_Review_Presentation_4Slides.pptx', 'docs/presentation_exports/sentinelx')
