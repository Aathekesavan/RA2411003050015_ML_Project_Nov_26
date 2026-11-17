import docx

doc_path = r'C:\Users\aathe\.gemini\antigravity\brain\88acc046-8fc2-4a66-b076-a12bc285ecc1\.user_uploaded\media_1793032504393_12c4f761.docx'
doc = docx.Document(doc_path)

body_items = []
tbl_count = 0
p_count = 0
for child in doc.element.body:
    tag = child.tag.split('}')[-1]
    if tag == 'p':
        p = docx.text.paragraph.Paragraph(child, doc)
        txt = p.text.strip()
        body_items.append(('p', txt))
        p_count += 1
    elif tag == 'tbl':
        tbl = docx.table.Table(child, doc)
        # extract table data
        rows_data = []
        for row in tbl.rows:
            row_cells = [c.text.strip() for c in row.cells]
            rows_data.append(row_cells)
        body_items.append(('tbl', rows_data))
        tbl_count += 1

print(f'Parsed {p_count} paragraphs and {tbl_count} tables.')

# Let's inspect where tables occur relative to text
for i, item in enumerate(body_items):
    if item[0] == 'tbl':
        # what was preceding text?
        prec = ''
        for k in range(max(0, i-3), i):
            if body_items[k][0] == 'p' and body_items[k][1]:
                prec = body_items[k][1]
        print(f'Table at index {i}: {len(item[1])} rows x {len(item[1][0])} cols. Preceded by: "{prec[:60]}"')
