import os

# Read the validated fixed project report markdown
with open('d:/sentinelx/docs/project_report_fixed.md', 'r', encoding='utf-8') as f:
    report_md = f.read()

with open('d:/sentinelx/docs/project_report.md', 'w', encoding='utf-8') as f:
    f.write(report_md)

print('Updated d:/sentinelx/docs/project_report.md successfully. Size:', len(report_md))
