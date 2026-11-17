import docx

doc = docx.Document('SentinelX_Project_Report_Clean.docx')

print("Checking paragraphs around 4.1...")
for i, p in enumerate(doc.paragraphs):
    if "4.1 Overall System Architecture" in p.text:
        print(f"Paragraph {i}: {p.text}")
        for j in range(max(0, i-2), min(len(doc.paragraphs), i+5)):
            print(f"  {j}: [{doc.paragraphs[j].style.name}] {doc.paragraphs[j].text[:60]}")

print("\nChecking paragraphs around 4.5.2...")
for i, p in enumerate(doc.paragraphs):
    if "4.5.2 Deduplication Audit" in p.text:
        print(f"Paragraph {i}: {p.text}")
        for j in range(max(0, i-2), min(len(doc.paragraphs), i+5)):
            print(f"  {j}: [{doc.paragraphs[j].style.name}] {doc.paragraphs[j].text[:60]}")

print("\nChecking paragraphs around 5.5.1...")
for i, p in enumerate(doc.paragraphs):
    if "5.5.1 Multi-Seed LOFO" in p.text:
        print(f"Paragraph {i}: {p.text}")
        for j in range(max(0, i-2), min(len(doc.paragraphs), i+5)):
            print(f"  {j}: [{doc.paragraphs[j].style.name}] {doc.paragraphs[j].text[:60]}")

print("\nChecking paragraphs around 5.5.2...")
for i, p in enumerate(doc.paragraphs):
    if "5.5.2 Cross-Dataset Evaluation" in p.text:
        print(f"Paragraph {i}: {p.text}")
        for j in range(max(0, i-2), min(len(doc.paragraphs), i+5)):
            print(f"  {j}: [{doc.paragraphs[j].style.name}] {doc.paragraphs[j].text[:60]}")

print("\nChecking paragraphs around 5.5.4...")
for i, p in enumerate(doc.paragraphs):
    if "5.5.4 System Latency Analysis" in p.text:
        print(f"Paragraph {i}: {p.text}")
        for j in range(max(0, i-2), min(len(doc.paragraphs), i+5)):
            print(f"  {j}: [{doc.paragraphs[j].style.name}] {doc.paragraphs[j].text[:60]}")
