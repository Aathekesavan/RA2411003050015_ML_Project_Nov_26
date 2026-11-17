import docx

doc = docx.Document('SentinelX_Project_Report_Clean.docx')

print("All occurrences of Table 4.1:")
for i, p in enumerate(doc.paragraphs):
    if "Table 4.1" in p.text:
        print(f"  P{i}: [{p.style.name}] {p.text[:70]}")

print("All occurrences of 5.5 Results and Discussion:")
for i, p in enumerate(doc.paragraphs):
    if "5.5 Results and Discussion" in p.text:
        print(f"  P{i}: [{p.style.name}] {p.text[:70]}")

print("All occurrences of Table 5.6:")
for i, p in enumerate(doc.paragraphs):
    if "Table 5.6" in p.text:
        print(f"  P{i}: [{p.style.name}] {p.text[:70]}")
