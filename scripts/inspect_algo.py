import docx

doc_path = r'C:\Users\aathe\.gemini\antigravity\brain\88acc046-8fc2-4a66-b076-a12bc285ecc1\.user_uploaded\media_1793032504393_12c4f761.docx'
doc = docx.Document(doc_path)

for i in range(315, 345):
    if i < len(doc.paragraphs):
        p = doc.paragraphs[i]
        txt = p.text.strip()
        if txt.startswith('Algorithm') or txt.startswith('Input') or '---' in txt or txt.startswith('1:') or txt.startswith(' 1:'):
            print(f'{i}: "{txt[:80]}"')
