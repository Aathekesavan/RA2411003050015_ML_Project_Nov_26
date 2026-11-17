import docx
import zipfile
import os

doc_path = r'C:\Users\aathe\.gemini\antigravity\brain\88acc046-8fc2-4a66-b076-a12bc285ecc1\.user_uploaded\media_1793032504393_12c4f761.docx'

# Extract all images from the docx to docs/retinaxai_figures/
extract_dir = 'docs/retinaxai_figures'
os.makedirs(extract_dir, exist_ok=True)

with zipfile.ZipFile(doc_path, 'r') as z:
    for filename in z.namelist():
        if filename.startswith('word/media/'):
            base_name = os.path.basename(filename)
            target_path = os.path.join(extract_dir, base_name)
            with open(target_path, 'wb') as f_out:
                f_out.write(z.read(filename))
            print(f'Extracted: {filename} -> {target_path} ({os.path.getsize(target_path)} bytes)')

doc = docx.Document(doc_path)
print(f'\nTotal paragraphs in friend docx: {len(doc.paragraphs)}')
print(f'Total tables: {len(doc.tables)}')

# Print TOC paragraphs
print('\n--- Search for TOC / Headings ---')
for i, p in enumerate(doc.paragraphs):
    txt = p.text.strip()
    if 'TABLE OF CONTENTS' in txt or 'LIST OF TABLES' in txt or 'LIST OF FIGURES' in txt:
        print(f'Para {i}: "{txt}"')
        for j in range(i, min(len(doc.paragraphs), i + 10)):
            print(f'   {j}: "{doc.paragraphs[j].text.strip()}"')
