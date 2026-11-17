import pypdf

reader = pypdf.PdfReader('RetinaXAI_Project_Report_Final.pdf')
total_pages = len(reader.pages)
print(f"=== TOTAL PAGES: {total_pages} ===")

print("\n--- TOC PAGE (PAGE 6) ---")
print(reader.pages[5].extract_text()[:600])

print("\n--- LOT PAGE (PAGE 7) ---")
print(reader.pages[6].extract_text()[:600])

print("\n--- LOF PAGE (PAGE 8) ---")
print(reader.pages[7].extract_text()[:600])

print("\n--- LAST PAGE (PAGE 40) ---")
print(reader.pages[-1].extract_text()[:400])
