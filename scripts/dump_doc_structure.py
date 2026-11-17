import docx

doc_path = r'C:\Users\aathe\.gemini\antigravity\brain\88acc046-8fc2-4a66-b076-a12bc285ecc1\.user_uploaded\media_1793032504393_12c4f761.docx'
doc = docx.Document(doc_path)

# Iterate over body elements in order
body_elements = []
for child in doc.element.body:
    tag = child.tag.split('}')[-1]
    if tag == 'p':
        p = docx.text.paragraph.Paragraph(child, doc)
        txt = p.text.strip()
        body_elements.append(('p', txt, len(p.runs)))
    elif tag == 'tbl':
        tbl = docx.table.Table(child, doc)
        body_elements.append(('tbl', len(tbl.rows), len(tbl.columns)))

print(f'Total body elements: {len(body_elements)}')
for idx, item in enumerate(body_elements[:50]):
    print(f'{idx}: {item[0]} -> {str(item[1:])[:70]}')
