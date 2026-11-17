import pptx
import os

def verify_presentation(pptx_path):
    print(f"\n=======================================================")
    print(f"VERIFYING: {pptx_path}")
    print(f"=======================================================")
    assert os.path.exists(pptx_path), f"File {pptx_path} does not exist!"
    prs = pptx.Presentation(pptx_path)
    print(f"Total Slides: {len(prs.slides)}")
    assert len(prs.slides) == 4, f"Expected 4 slides, got {len(prs.slides)}"

    for s_idx, slide in enumerate(prs.slides):
        print(f"\n--- Slide {s_idx + 1} ---")
        for sh_idx, shape in enumerate(slide.shapes):
            if shape.has_text_frame:
                texts = [p.text.strip() for p in shape.text_frame.paragraphs if p.text.strip()]
                if texts:
                    print(f"  [{shape.name}] ({len(texts)} paragraphs):")
                    for t in texts[:3]:
                        print(f"     • {t[:90]}")
            elif shape.has_table:
                t = shape.table
                print(f"  [{shape.name}] Table: {len(t.rows)} rows x {len(t.columns)} cols")
                for r_idx in range(len(t.rows)):
                    row_txt = [t.cell(r_idx, c).text.strip()[:25].replace('\n', ' ') for c in range(len(t.columns))]
                    print(f"     Row {r_idx}: {' | '.join(row_txt)}")
            elif shape.shape_type == 13: # Picture
                print(f"  [{shape.name}] Picture: dimensions=({shape.width}, {shape.height}), at ({shape.left}, {shape.top})")

if __name__ == '__main__':
    verify_presentation('RetinaXAI_Project_Review_Presentation_Template.pptx')
    verify_presentation('SentinelX_Project_Review_Presentation_4Slides.pptx')
