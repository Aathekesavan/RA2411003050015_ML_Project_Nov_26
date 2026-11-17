import pypdf

reader = pypdf.PdfReader('RetinaXAI_Project_Report_Final.pdf')
for p in range(10, len(reader.pages) + 1):
    txt = reader.pages[p-1].extract_text()
    lines = [l.strip() for l in txt.split('\n') if l.strip()]
    first_few = " | ".join(lines[:2]) if lines else "EMPTY"
    last_line = lines[-1] if lines else "EMPTY"
    print(f"Page {p} (Total lines: {len(lines)}):  First: {first_few[:70]}  |  Last: {last_line[:60]}")
