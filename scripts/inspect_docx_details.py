import docx

doc_path = r'C:\Users\aathe\.gemini\antigravity\brain\88acc046-8fc2-4a66-b076-a12bc285ecc1\.user_uploaded\media_1793032504393_12c4f761.docx'
doc = docx.Document(doc_path)

breaks = []
images = []
for i, p in enumerate(doc.paragraphs):
    for r in p.runs:
        if 'w:type="page"' in r._r.xml:
            breaks.append((i, p.text.strip()))
        if 'graphic' in r._r.xml or 'drawing' in r._r.xml:
            images.append((i, p.text.strip()))

print(f'Total page breaks: {len(breaks)}')
for b in breaks:
    print('  Break at para:', b)

print(f'\nTotal images: {len(images)}')
for img in images:
    print('  Image at para:', img)

print('\nTotal tables:', len(doc.tables))
for i, t in enumerate(doc.tables):
    first_row = [c.text.strip().replace('\n', ' ') for c in t.rows[0].cells]
    print(f'Table {i}: cols={len(t.columns)}, rows={len(t.rows)}, header={first_row[:3]}')
