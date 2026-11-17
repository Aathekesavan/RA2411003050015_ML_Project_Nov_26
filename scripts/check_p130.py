import docx

doc = docx.Document('docs/retinaxai_project_report.docx')
for p_idx in [130, 159]:
    if p_idx < len(doc.paragraphs):
        p = doc.paragraphs[p_idx]
        print(f'Para {p_idx}: text="{p.text}"')
        for r_idx, r in enumerate(p.runs):
            print(f'  run {r_idx}: text="{r.text}", xml="{r._r.xml[:200]}"')
