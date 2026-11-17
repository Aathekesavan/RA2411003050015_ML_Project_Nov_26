import docx

doc = docx.Document("docs/project_report.docx")
print("Total paragraphs:", len(doc.paragraphs))
print("Cover page paragraphs:")
for i in range(16):
    p = doc.paragraphs[i]
    has_pic = any('graphic' in r._r.xml for r in p.runs)
    print(f"Para {i}: '{p.text}' (has_pic: {has_pic}, align: {p.alignment})")

breaks = [(i, p.text.strip()) for i, p in enumerate(doc.paragraphs) if p.paragraph_format.page_break_before]
print(f"\nTotal page_break_before: {len(breaks)}")
for idx, (p_idx, txt) in enumerate(breaks):
    print(f"Break {idx+1} at para {p_idx}: '{txt}'")
