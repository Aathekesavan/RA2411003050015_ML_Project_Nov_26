import docx

doc_path = r'C:\Users\aathe\.gemini\antigravity\brain\88acc046-8fc2-4a66-b076-a12bc285ecc1\.user_uploaded\media_1793032504393_12c4f761.docx'
doc = docx.Document(doc_path)

for i, p in enumerate(doc.paragraphs):
    txt = p.text.strip()
    if 'Figure' in txt:
        print(f'Para {i}: "{txt[:80]}"')
