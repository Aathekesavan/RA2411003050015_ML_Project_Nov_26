import pptx
import os

template_path = 'C:/Users/aathe/.gemini/antigravity/brain/722aad3e-8779-44e1-8bf4-0d3eb310252d/.user_uploaded/media_1794444955506_33c3068c.pptx'
prs = pptx.Presentation(template_path)

slide2 = prs.slides[1]
for shape in list(slide2.shapes):
    if shape.name == 'Picture 9':
        left, top, w, h = shape.left, shape.top, shape.width, shape.height
        spTree = slide2.shapes._spTree
        spTree.remove(shape._element)
        slide2.shapes.add_picture('docs/retinaxai_figures/system_architecture.png', left, top, w, h)
        print("Replaced Picture 9 on Slide 2")

prs.save('scratch/test_replace.pptx')
print("Saved scratch/test_replace.pptx successfully!")
