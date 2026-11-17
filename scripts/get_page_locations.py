import pypdf
import re

reader = pypdf.PdfReader('test_perfect.pdf')
print(f"Total Pages: {len(reader.pages)}")

# Let's inspect headings, tables, figures
items_to_find = [
    # Front matter
    ('Bonafide Certificate', r'BONAFIDE CERTIFICATE'),
    ('Project Problem Statement', r'PROJECT PROBLEM STATEMENT'),
    ('Abstract', r'ABSTRACT'),
    ('Acknowledgements', r'ACKNOWLEDGEMENTS'),
    ('Table of Contents', r'TABLE OF CONTENTS'),
    ('List of Tables', r'LIST OF TABLES'),
    ('List of Figures', r'LIST OF FIGURES'),
    ('Abbreviations and Symbols', r'ABBREVIATIONS AND SYMBOLS'),
    # Chapter 1
    ('Chapter 1', r'CHAPTER 1\s*[—-]\s*INTRODUCTION'),
    ('1.1', r'1\.1\s+Background and Overview'),
    ('1.2', r'1\.2\s+Motivation for Developing'),
    ('1.3', r'1\.3\s+Demand and Necessity'),
    ('1.4', r'1\.4\s+Objectives and Scope'),
    ('1.5', r'1\.5\s+Scope and Real-World'),
    ('1.6', r'1\.6\s+Relevance to Operational'),
    ('1.7', r'1\.7\s+Expected Contributions'),
    ('1.8', r'1\.8\s+Organisation of the Report'),
    # Chapter 2
    ('Chapter 2', r'CHAPTER 2\s*[—-]\s*LITERATURE SURVEY'),
    ('2.1', r'2\.1\s+International Research Papers'),
    ('2.2', r'2\.2\s+National Research Papers'),
    ('2.3', r'2\.3\s+Comparative Synthesis'),
    ('2.4', r'2\.4\s+Research Gaps'),
    ('2.5', r'2\.5\s+Literature Survey Summary Tables'),
    # Chapter 3
    ('Chapter 3', r'CHAPTER 3\s*[—-]\s*SYSTEM ANALYSIS'),
    ('3.1', r'3\.1\s+Existing System'),
    ('3.2', r'3\.2\s+Proposed RETINAXAI'),
    ('3.3', r'3\.3\s+Functional Requirements'),
    ('3.4', r'3\.4\s+Non-Functional Requirements'),
    ('3.5', r'3\.5\s+Hardware Requirements'),
    ('3.6', r'3\.6\s+Software Requirements'),
    ('3.7', r'3\.7\s+Feasibility Study'),
    # Chapter 4
    ('Chapter 4', r'CHAPTER 4\s*[—-]\s*SYSTEM ARCHITECTURE'),
    ('4.1', r'4\.1\s+Overall Architectural Design'),
    ('4.2', r'4\.2\s+Component-Level'),
    ('4.3', r'4\.3\s+Working Method'),
    ('4.4', r'4\.4\s+Detailed Algorithms'),
    ('4.5', r'4\.5\s+Data Acquisition'),
    ('4.6', r'4\.6\s+Security'),
    # Chapter 5
    ('Chapter 5', r'CHAPTER 5\s*[—-]\s*CODING'),
    ('5.1', r'5\.1\s+Development Environment'),
    ('5.2', r'5\.2\s+Data Pre-processing'),
    ('5.3', r'5\.3\s+Exploratory Data Analysis'),
    ('5.4', r'5\.4\s+Model Training Dynamics'),
    ('5.5', r'5\.5\s+Audited Results'),
    ('5.6', r'5\.6\s+System Inference Latency'),
    ('5.7', r'5\.7\s+Hardware and Functional'),
    ('5.8', r'5\.8\s+Limitations and Threats'),
    # Chapter 6
    ('Chapter 6', r'CHAPTER 6\s*[—-]\s*CONCLUSION'),
    ('6.1', r'6\.1\s+Conclusion'),
    ('6.2', r'6\.2\s+Future Work'),
    # Chapter 7
    ('Chapter 7', r'CHAPTER 7\s*[—-]\s*ACCENTURE'),
    ('7.1', r'Module 1: Circular Retinal ROI'),
    ('7.2', r'Module 2: Ben Graham Illumination'),
    ('7.3', r'Module 3: Fast Breadth-First'),
    ('7.4', r'Module 4: Dynamic Severity Triage'),
    # References, Annexure, Appendix
    ('References', r'^\s*REFERENCES\s*$'),
    ('Annexure I', r'ANNEXURE I\s*[—-]\s*SOURCE CODE'),
    ('A.1', r'A\.1\s+Preprocessing Module'),
    ('A.2', r'A\.2\s+EfficientNet-B0'),
    ('A.3', r'A\.3\s+Explainable AI'),
    ('A.4', r'A\.4\s+Streamlit Interactive'),
    ('Appendix A', r'APPENDIX A\s*[—-]\s*SAMPLE DATASET'),
    # Tables
    ('Table 2.1', r'Table\s+2\.1:'),
    ('Table 2.2', r'Table\s+2\.2:'),
    ('Table 2.3', r'Table\s+2\.3:'),
    ('Table 3.1', r'Table\s+3\.1:'),
    ('Table 3.2', r'Table\s+3\.2:'),
    ('Table 4.1', r'Table\s+4\.1:'),
    ('Table 4.2', r'Table\s+4\.2:'),
    ('Table 4.3', r'Table\s+4\.3:'),
    ('Table 5.1', r'Table\s+5\.1:'),
    ('Table 5.2', r'Table\s+5\.2:'),
    ('Table 5.3', r'Table\s+5\.3:'),
    ('Table 5.4', r'Table\s+5\.4:'),
    ('Table 5.5', r'Table\s+5\.5:'),
    ('Table 5.6', r'Table\s+5\.6:'),
    ('Table 5.7', r'Table\s+5\.7:'),
    ('Table A.1', r'Table\s+A\.1:'),
    # Figures
    ('Figure 4.1', r'Figure\s+4\.1:'),
    ('Figure 5.1', r'Figure\s+5\.1:'),
    ('Figure 5.2', r'Figure\s+5\.2:'),
    ('Figure 5.3', r'Figure\s+5\.3:'),
    ('Figure 5.4', r'Figure\s+5\.4:'),
    ('Figure 5.5', r'Figure\s+5\.5:'),
    ('Figure A.1', r'Figure\s+A\.1:'),
    ('Figure A.2', r'Figure\s+A\.2:'),
    ('Figure A.3', r'Figure\s+A\.3:'),
    ('Figure A.4', r'Figure\s+A\.4:')
]

found = {}
for pnum in range(1, len(reader.pages) + 1):
    text = reader.pages[pnum - 1].extract_text()
    # skip TOC, LOT, LOF pages for chapter/section matching
    if pnum in [6, 7, 8]:
        continue
    for key, pat in items_to_find:
        if key not in found:
            if re.search(pat, text, re.IGNORECASE | re.MULTILINE):
                found[key] = pnum

# For TOC, LOT, LOF
found['Table of Contents'] = 6
found['List of Tables'] = 7
found['List of Figures'] = 8

print("RESULTS:")
for key, pat in items_to_find:
    print(f"'{key}': {found.get(key, 'NOT_FOUND')},")
