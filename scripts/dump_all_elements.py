import docx

doc_path = r'C:\Users\aathe\.gemini\antigravity\brain\88acc046-8fc2-4a66-b076-a12bc285ecc1\.user_uploaded\media_1793032504393_12c4f761.docx'
doc = docx.Document(doc_path)

body_elements = []
for child in doc.element.body:
    tag = child.tag.split('}')[-1]
    if tag == 'p':
        p = docx.text.paragraph.Paragraph(child, doc)
        txt = p.text.strip()
        has_break = any('w:type="page"' in r._r.xml for r in p.runs)
        has_img = any('graphic' in r._r.xml or 'drawing' in r._r.xml for r in p.runs)
        body_elements.append(('p', txt, has_break, has_img))
    elif tag == 'tbl':
        tbl = docx.table.Table(child, doc)
        first_row = [c.text.strip().replace('\n', ' ') for c in tbl.rows[0].cells]
        body_elements.append(('tbl', len(tbl.rows), len(tbl.columns), first_row[:2]))

print(f'Total elements: {len(body_elements)}')
for idx, el in enumerate(body_elements):
    if el[0] == 'tbl':
        print(f'{idx}: TBL rows={el[1]}, cols={el[2]}, header={el[3]}')
    elif el[2]: # has_break
        print(f'{idx}: PAGE BREAK -> text: "{el[1][:40]}"')
    elif el[3]: # has_img
        print(f'{idx}: IMAGE -> text: "{el[1][:40]}"')
    elif el[1].startswith('CHAPTER') or el[1].startswith('Figure') or el[1].startswith('Table') or el[1] in ['BONAFIDE CERTIFICATE', 'PROJECT PROBLEM STATEMENT', 'ABSTRACT', 'ACKNOWLEDGEMENTS', 'TABLE OF CONTENTS', 'LIST OF TABLES', 'LIST OF FIGURES', 'ABBREVIATIONS AND SYMBOLS', 'REFERENCES', 'ANNEXURE I', 'APPENDIX A']:
        print(f'{idx}: HEADING/CAPTION -> "{el[1][:60]}"')
