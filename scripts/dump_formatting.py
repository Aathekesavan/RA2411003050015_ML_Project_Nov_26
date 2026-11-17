import pptx

prs = pptx.Presentation('C:/Users/aathe/.gemini/antigravity/brain/722aad3e-8779-44e1-8bf4-0d3eb310252d/.user_uploaded/media_1794444955506_33c3068c.pptx')

for s_idx, s in enumerate(prs.slides):
    print(f'*** SLIDE {s_idx+1} ***')
    for sh in s.shapes:
        if sh.has_text_frame:
            for p_idx, p in enumerate(sh.text_frame.paragraphs):
                font = p.font
                col = font.color.rgb if (font and font.color and font.color.type == 1) else None
                sz = font.size.pt if (font and font.size) else None
                bld = font.bold if font else None
                name = font.name if font else None
                print(f'[{sh.name} P{p_idx}] font={name} sz={sz} bold={bld} col={col} align={p.alignment} text="{p.text[:60]}"')
        elif sh.has_table:
            t = sh.table
            print(f'[{sh.name}] TABLE {len(t.rows)}x{len(t.columns)}')
            for r_i, row in enumerate(t.rows):
                for c_i, cell in enumerate(row.cells):
                    for p_i, p in enumerate(cell.text_frame.paragraphs):
                        font = p.font
                        col = font.color.rgb if (font and font.color and font.color.type == 1) else None
                        sz = font.size.pt if (font and font.size) else None
                        bld = font.bold if font else None
                        print(f'  Cell({r_i},{c_i}) P{p_i} sz={sz} bold={bld} col={col} txt="{p.text[:40]}"')
