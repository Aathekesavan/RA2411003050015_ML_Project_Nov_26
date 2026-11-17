import pptx

pptx_path = 'C:/Users/aathe/.gemini/antigravity/brain/722aad3e-8779-44e1-8bf4-0d3eb310252d/.user_uploaded/media_1794444955506_33c3068c.pptx'
prs = pptx.Presentation(pptx_path)

for slide_idx, slide in enumerate(prs.slides):
    print(f'============================= SLIDE {slide_idx+1} =============================')
    for shape_idx, shape in enumerate(slide.shapes):
        text_summary = ''
        if shape.has_text_frame:
            text_summary = ' | '.join([p.text.strip() for p in shape.text_frame.paragraphs if p.text.strip()])
            if len(text_summary) > 80:
                text_summary = text_summary[:80] + '...'
        elif shape.has_table:
            text_summary = f'TABLE: {len(shape.table.rows)} rows x {len(shape.table.columns)} cols'
        elif shape.shape_type == 13:
            text_summary = f'PICTURE: {shape.name}'
        print(f'Shape [{shape_idx}]: name="{shape.name}", type={shape.shape_type}, left={shape.left}, top={shape.top}, w={shape.width}, h={shape.height} -> "{text_summary}"')
