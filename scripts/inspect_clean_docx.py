import docx

doc = docx.Document('SentinelX_Project_Report_Clean.docx')
print('Paragraphs:', len(doc.paragraphs))
print('Tables:', len(doc.tables))
for i, t in enumerate(doc.tables):
    first_cell = t.rows[0].cells[0].text.replace('\n', ' ')[:50]
    print(f'Table {i}: rows={len(t.rows)}, cols={len(t.columns)}, content="{first_cell}"')
