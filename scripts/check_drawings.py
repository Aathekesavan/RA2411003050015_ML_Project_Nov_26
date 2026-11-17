import docx

doc = docx.Document('docs/retinaxai_project_report.docx')
actual_pics = []
for i, p in enumerate(doc.paragraphs):
    drawings = p._p.xpath('.//w:drawing')
    if drawings:
        actual_pics.append((i, p.text.strip()))

print('Actual drawing elements in document:', len(actual_pics))
for idx, (p_idx, txt) in enumerate(actual_pics):
    cap = doc.paragraphs[p_idx+1].text.strip() if p_idx+1 < len(doc.paragraphs) else ''
    print(f'Drawing {idx+1} at para {p_idx}: caption="{cap[:60]}"')
