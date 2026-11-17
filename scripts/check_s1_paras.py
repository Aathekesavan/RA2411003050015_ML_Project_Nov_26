import pptx

prs = pptx.Presentation('C:/Users/aathe/.gemini/antigravity/brain/722aad3e-8779-44e1-8bf4-0d3eb310252d/.user_uploaded/media_1794444955506_33c3068c.pptx')
s1 = prs.slides[0]
for name in ['Rounded Rectangle 6', 'Rounded Rectangle 8']:
    sh = [s for s in s1.shapes if s.name == name][0]
    print(f'=== {name} ===')
    for p_i, p in enumerate(sh.text_frame.paragraphs):
        print(f'  P{p_i}: text="{p.text}"')
        for r_i, r in enumerate(p.runs):
            print(f'    R{r_i}: bold={r.font.bold}, size={r.font.size.pt if r.font.size else None}, color={r.font.color.rgb if (r.font.color and r.font.color.type==1) else None}, text="{r.text}"')
