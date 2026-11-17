import pypdf

reader = pypdf.PdfReader('test_perfect.pdf')
searches = {
    '2.1': 'International Research',
    '2.2': 'National Research',
    '7.1 / Module 1': 'Module 1',
    '7.2 / Module 2': 'Module 2',
    '7.3 / Module 3': 'Module 3',
    '7.4 / Module 4': 'Module 4',
    'A.1': 'A.1',
    'A.2': 'A.2',
    'A.3': 'A.3',
    'A.4': 'A.4',
    'References': 'REFERENCES'
}

for label, term in searches.items():
    pages = []
    for idx, page in enumerate(reader.pages):
        pnum = idx + 1
        if pnum in [6, 7, 8]:
            continue
        text = page.extract_text()
        if term in text:
            pages.append(pnum)
    print(f'{label}: {pages}')
