import docx

doc = docx.Document('SentinelX_Project_Report_Final.docx')
print('Total paragraphs:', len(doc.paragraphs))
print('Total tables:', len(doc.tables))

print('\n--- VERIFYING FIRST PAGE (P0 to P14) ---')
for i in range(15):
    print(f'P{i}: {doc.paragraphs[i].text}')

print('\n--- VERIFYING BONAFIDE CERTIFICATE (P15 to P17) ---')
for i in range(15, 18):
    print(f'P{i}: {doc.paragraphs[i].text}')

print('\n--- VERIFYING GUIDE / HOD SIGNATURE TABLE ---')
for row in doc.tables[0].rows:
    print([c.text.replace('\n', ' ') for c in row.cells])

print('\n--- VERIFYING INSERTED FIGURES ---')
for i, p in enumerate(doc.paragraphs):
    for run in p.runs:
        if 'graphic' in run._r.xml:
            print(f'Image at P{i}, followed by caption: "{doc.paragraphs[i+1].text}"')

print('\n--- VERIFYING EVALUATION PARAMETERS ---')
for i, p in enumerate(doc.paragraphs):
    if "Evaluation Parameters" in p.text:
        print(f'Heading at P{i}: {p.text}')
        print(f'Content at P{i+1}: {doc.paragraphs[i+1].text[:120]}...')

print('\n--- VERIFYING CHAPTER 7 INTACT ---')
for i, p in enumerate(doc.paragraphs):
    if "CHAPTER 7" in p.text:
        print(f'P{i}: {p.text}')
        for j in range(i+1, min(len(doc.paragraphs), i+8)):
            print(f'  P{j}: {doc.paragraphs[j].text[:70]}')
