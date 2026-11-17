import docx

doc = docx.Document('docs/retinaxai_project_report.docx')
for i, p in enumerate(doc.paragraphs):
    for r in p.runs:
        if 'graphic' in r._r.xml or 'drawing' in r._r.xml:
            print(f'Para {i}: text="{p.text[:60]}"')
            # Check what image or element
            for child in r._r:
                tag = child.tag.split('}')[-1]
                print(f'   child tag: {tag}')
