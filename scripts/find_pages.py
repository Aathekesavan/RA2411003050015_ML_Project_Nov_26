import pypdf
import re

reader = pypdf.PdfReader('reduced_report_perfect.pdf')

targets = [
    ('Bonafide', r'BONAFIDE CERTIFICATE'),
    ('Problem', r'PROJECT PROBLEM STATEMENT'),
    ('Abstract', r'ABSTRACT'),
    ('Acknowledgements', r'ACKNOWLEDGEMENTS'),
    ('LOT', r'LIST OF TABLES'),
    ('LOF', r'LIST OF FIGURES'),
    ('Abbreviations', r'ABBREVIATIONS AND SYMBOLS'),
    ('Ch1', r'CHAPTER 1 — INTRODUCTION'),
    ('Ch1_1', r'1\.1 Background and Overview'),
    ('Ch1_2', r'1\.2 Motivation for Developing'),
    ('Ch1_3', r'1\.3 Demand and Necessity'),
    ('Ch1_4', r'1\.4 Objectives and Scope'),
    ('Ch1_5', r'1\.5 Scope and Real-World'),
    ('Ch1_6', r'1\.6 Relevance to Operational'),
    ('Ch1_7', r'1\.7 Expected Contributions'),
    ('Ch1_8', r'1\.8 Organisation of the Report'),
    ('Ch2', r'CHAPTER 2 — LITERATURE SURVEY'),
    ('Ch2_1', r'2\.1 International Research'),
    ('Ch2_Nat', r'2\.2 National Research'),
    ('Ch2_Synth', r'2\.3 Comparative Synthesis'),
    ('Ch2_Gap', r'2\.4 Research Gaps'),
    ('Ch2_Tables', r'2\.5 Literature Survey Summary Tables'),
    ('Ch3', r'CHAPTER 3 — SYSTEM ANALYSIS'),
    ('Ch3_1', r'3\.1 Existing System'),
    ('Ch3_2', r'3\.2 Proposed RETINAXAI'),
    ('Ch3_FR', r'3\.3 Functional Requirements'),
    ('Ch3_NFR', r'3\.4 Non-Functional Requirements'),
    ('Ch3_HW', r'3\.5 Hardware Requirements'),
    ('Ch3_SW', r'3\.6 Software Requirements'),
    ('Ch3_Feas', r'3\.7 Feasibility Study'),
    ('Ch4', r'CHAPTER 4 — SYSTEM ARCHITECTURE'),
    ('Ch4_1', r'4\.1 Overall Architectural Design'),
    ('Ch4_Comp', r'4\.2 Component-Level'),
    ('Ch4_Flow', r'4\.3 Working Method'),
    ('Ch4_Algo', r'4\.4 Detailed Algorithms'),
    ('Ch4_Data', r'4\.5 Data Acquisition'),
    ('Ch4_Sec', r'4\.6 Security, Reliability'),
    ('Ch5', r'CHAPTER 5 — CODING'),
    ('Ch5_1', r'5\.1 Development Environment'),
    ('Ch5_2', r'5\.2 Data Pre-processing'),
    ('Ch5_EDA', r'5\.3 Exploratory Data Analysis'),
    ('Ch5_Train', r'5\.4 Model Training Dynamics'),
    ('Ch5_Results', r'5\.5 Audited Results'),
    ('Ch5_Latency', r'5\.6 System Inference Latency'),
    ('Ch5_Verify', r'5\.7 Hardware and Functional'),
    ('Ch5_Limits', r'5\.8 Limitations and Threats'),
    ('Ch6', r'CHAPTER 6 — CONCLUSION'),
    ('Ch6_1', r'6\.1 Conclusion'),
    ('Ch6_Future', r'6\.2 Future Work'),
    ('Ch7', r'CHAPTER 7 — ACCENTURE'),
    ('Refs', r'REFERENCES'),
    ('Annex', r'ANNEXURE I — SOURCE CODE'),
    ('AppA', r'APPENDIX A — SAMPLE DATASET'),
    ('T21', r'Table 2\.1:'),
    ('T22', r'Table 2\.2:'),
    ('T23', r'Table 2\.3:'),
    ('T31', r'Table 3\.1:'),
    ('T32', r'Table 3\.2:'),
    ('T41', r'Table 4\.1:'),
    ('T42', r'Table 4\.2:'),
    ('T43', r'Table 4\.3:'),
    ('T51', r'Table 5\.1:'),
    ('T52', r'Table 5\.2:'),
    ('T53', r'Table 5\.3:'),
    ('T54', r'Table 5\.4:'),
    ('T55', r'Table 5\.5:'),
    ('T56', r'Table 5\.6:'),
    ('T57', r'Table 5\.7:'),
    ('F41', r'Figure 4\.1:'),
    ('F51', r'Figure 5\.1:'),
    ('F52', r'Figure 5\.2:'),
    ('F53', r'Figure 5\.3:'),
    ('F54', r'Figure 5\.4:'),
    ('F55', r'Figure 5\.5:'),
    ('FA1', r'Figure A\.1:'),
    ('FA2', r'Figure A\.2:'),
    ('FA3', r'Figure A\.3:'),
    ('FA4', r'Figure A\.4:')
]

found = {}
# Skip page 6, 7, 8 (TOC, LOT, LOF) when searching for chapter headings
for idx, page in enumerate(reader.pages):
    pnum = idx + 1
    if pnum in [6, 7, 8]:
        continue
    text = page.extract_text()
    for tag, pat in targets:
        if tag not in found and re.search(pat, text, re.IGNORECASE):
            found[tag] = pnum

print("page_map = {")
for tag, _ in targets:
    val = found.get(tag, '?')
    print(f"    '{tag}': '{val}',")
print("}")
