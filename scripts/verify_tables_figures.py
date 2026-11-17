import pypdf
import re

reader = pypdf.PdfReader('RetinaXAI_Project_Report_Final.pdf')

print("--- TABLES IN BODY (skipping p1-9) ---")
for pnum in range(10, len(reader.pages) + 1):
    txt = reader.pages[pnum - 1].extract_text()
    for m in re.finditer(r'(Table\s+\d+\.\d+|Table\s+A\.\d+)', txt):
        print(f"{m.group(1)} -> Page {pnum}")

print("\n--- FIGURES IN BODY (skipping p1-9) ---")
for pnum in range(10, len(reader.pages) + 1):
    txt = reader.pages[pnum - 1].extract_text()
    for m in re.finditer(r'(Figure\s+\d+\.\d+|Figure\s+A\.\d+)', txt):
        print(f"{m.group(1)} -> Page {pnum}")
