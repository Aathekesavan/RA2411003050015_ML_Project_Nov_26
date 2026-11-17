import re
import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=60, bottom=60, left=80, right=80):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def set_table_borders(table, color="D1D5DB", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
            <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def set_borderless_table(table):
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="none"/>
            <w:bottom w:val="none"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
            <w:insideH w:val="none"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def add_page_number(run):
    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> PAGE </w:instrText>' % nsdecls('w'))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)

def add_formatted_runs(paragraph, text, font_name="Times New Roman", font_size=11.5, italic_default=False, bold_default=False, color=None):
    pattern = re.compile(r'(\*\*.*?\*\*|\*.*?\*|`.*?`|\$.*?\$|\[.*?\]\(.*?\))')
    parts = pattern.split(text)
    for part in parts:
        if not part:
            continue
        run = paragraph.add_run()
        run.font.name = font_name
        run.font.size = Pt(font_size)
        if color:
            run.font.color.rgb = color
        else:
            run.font.color.rgb = RGBColor(0, 0, 0)
            
        if part.startswith('**') and part.endswith('**') and len(part) >= 4:
            run.text = part[2:-2]
            run.bold = True
            run.italic = italic_default
        elif part.startswith('*') and part.endswith('*') and len(part) >= 2:
            run.text = part[1:-1]
            run.italic = True
            run.bold = bold_default
        elif part.startswith('`') and part.endswith('`') and len(part) >= 2:
            run.text = part[1:-1]
            run.font.name = "Consolas"
            run.font.size = Pt(font_size - 1)
            run.font.color.rgb = RGBColor(30, 30, 30)
            run.bold = bold_default
        elif part.startswith('$') and part.endswith('$') and len(part) >= 2:
            math_text = part[1:-1].replace(r'\text', '').replace('{', '').replace('}', '').replace(r'\mathbf', '').replace(r'\mathbb{I}', 'I')
            run.text = math_text
            run.italic = True
            run.bold = bold_default
        elif part.startswith('[') and '](' in part and part.endswith(')'):
            match = re.match(r'\[(.*?)\]\((.*?)\)', part)
            if match:
                run.text = match.group(1)
                run.font.color.rgb = RGBColor(0, 0, 0)
                run.bold = bold_default
            else:
                run.text = part
        else:
            run.text = part
            run.bold = bold_default
            run.italic = italic_default

PAGE_BREAK_HEADINGS = [
    "BONAFIDE CERTIFICATE",
    "PROJECT PROBLEM STATEMENT",
    "ABSTRACT",
    "ACKNOWLEDGEMENTS",
    "TABLE OF CONTENTS",
    "LIST OF TABLES",
    "ABBREVIATIONS AND SYMBOLS",
    "CHAPTER 1",
    "CHAPTER 2",
    "CHAPTER 3",
    "CHAPTER 4",
    "CHAPTER 5",
    "CHAPTER 6",
    "APPENDIX A",
    "APPENDIX B",
    "REFERENCES"
]

CENTERED_HEADINGS = [
    "BONAFIDE CERTIFICATE",
    "PROJECT PROBLEM STATEMENT",
    "ABSTRACT",
    "ACKNOWLEDGEMENTS",
    "TABLE OF CONTENTS",
    "LIST OF TABLES",
    "LIST OF FIGURES",
    "ABBREVIATIONS AND SYMBOLS",
    "CHAPTER 1",
    "CHAPTER 2",
    "CHAPTER 3",
    "CHAPTER 4",
    "CHAPTER 5",
    "CHAPTER 6",
    "APPENDIX A",
    "APPENDIX B",
    "REFERENCES"
]

def should_break_page_for_heading(heading_text):
    clean = re.sub(r'[^A-Z0-9 ]', ' ', heading_text.upper()).strip()
    clean = re.sub(r'\s+', ' ', clean)
    for h in PAGE_BREAK_HEADINGS:
        if clean.startswith(h):
            return True
    return False

def should_center_heading(heading_text):
    clean = re.sub(r'[^A-Z0-9 ]', ' ', heading_text.upper()).strip()
    clean = re.sub(r'\s+', ' ', clean)
    for h in CENTERED_HEADINGS:
        if clean.startswith(h):
            return True
    return False

def parse_markdown_to_docx(md_path, docx_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    doc = Document()
    
    # Configure Page Margins (1 inch everywhere)
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        
        section.header.is_linked_to_previous = False
        for p in section.header.paragraphs:
            p.text = ""
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)

        footer = section.footer
        f_p = footer.paragraphs[0]
        f_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        f_p.paragraph_format.space_before = Pt(0)
        f_p.paragraph_format.space_after = Pt(0)
        f_run = f_p.add_run()
        f_run.font.name = "Times New Roman"
        f_run.font.size = Pt(11)
        f_run.font.color.rgb = RGBColor(0, 0, 0)
        add_page_number(f_run)

    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(11.5)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.2
    normal_style.paragraph_format.space_after = Pt(4)
    normal_style.paragraph_format.space_before = Pt(0)

    in_code_block = False
    code_lines = []
    
    in_table = False
    table_rows = []

    is_cover_page = True

    i = 0
    num_lines = len(lines)

    while i < num_lines:
        line = lines[i].rstrip('\r\n')
        stripped = line.strip()

        # Handle Code Blocks
        if stripped.startswith('```'):
            if in_code_block:
                in_code_block = False
                code_text = "\n".join(code_lines)
                code_table = doc.add_table(rows=1, cols=1)
                code_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                cell = code_table.cell(0, 0)
                set_cell_background(cell, "F9FAFB")
                set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
                
                tcPr = cell._tc.get_or_add_tcPr()
                tcBorders = parse_xml(f'''
                    <w:tcBorders {nsdecls("w")}>
                        <w:top w:val="single" w:sz="4" w:color="D1D5DB"/>
                        <w:bottom w:val="single" w:sz="4" w:color="D1D5DB"/>
                        <w:left w:val="single" w:sz="16" w:color="374151"/>
                        <w:right w:val="single" w:sz="4" w:color="D1D5DB"/>
                    </w:tcBorders>
                ''')
                tcPr.append(tcBorders)

                cp = cell.paragraphs[0]
                cp.paragraph_format.line_spacing = 1.05
                cp.paragraph_format.space_before = Pt(0)
                cp.paragraph_format.space_after = Pt(0)
                c_run = cp.add_run(code_text)
                c_run.font.name = "Consolas"
                c_run.font.size = Pt(9.5)
                c_run.font.color.rgb = RGBColor(17, 24, 39)

                code_lines = []
            else:
                in_code_block = True
                code_lines = []
            i += 1
            continue

        if in_code_block:
            code_lines.append(line)
            i += 1
            continue

        # Handle Tables
        if stripped.startswith('|') and stripped.endswith('|'):
            in_table = True
            cells = [c.strip() for c in stripped[1:-1].split('|')]
            table_rows.append(cells)
            i += 1
            continue
        elif in_table:
            in_table = False
            content_rows = [r for r in table_rows if not all(re.match(r'^:?-+:?$', c) for c in r if c)]
            if content_rows:
                is_signature_table = any("Signature of Guide" in c for c in content_rows[0])
                num_cols = max(len(r) for r in content_rows)
                t = doc.add_table(rows=len(content_rows), cols=num_cols)
                t.alignment = WD_TABLE_ALIGNMENT.CENTER

                if is_signature_table:
                    set_borderless_table(t)
                    for row_idx, r in enumerate(content_rows):
                        for col_idx in range(num_cols):
                            cell_text = r[col_idx] if col_idx < len(r) else ""
                            cell = t.cell(row_idx, col_idx)
                            set_cell_margins(cell, top=60, bottom=60, left=80, right=80)
                            cp = cell.paragraphs[0]
                            cp.paragraph_format.line_spacing = 1.15
                            if row_idx == 1:
                                cp.paragraph_format.space_before = Pt(32)
                            else:
                                cp.paragraph_format.space_before = Pt(0)
                            cp.paragraph_format.space_after = Pt(2)
                            add_formatted_runs(cp, cell_text, font_size=11, bold_default=(row_idx == 0 or row_idx == 1), color=RGBColor(0, 0, 0))
                else:
                    set_table_borders(t, color="D1D5DB", sz="4")
                    for row_idx, r in enumerate(content_rows):
                        for col_idx in range(num_cols):
                            cell_text = r[col_idx] if col_idx < len(r) else ""
                            cell = t.cell(row_idx, col_idx)
                            set_cell_margins(cell, top=50, bottom=50, left=80, right=80)
                            cp = cell.paragraphs[0]
                            cp.paragraph_format.line_spacing = 1.15
                            cp.paragraph_format.space_before = Pt(0)
                            cp.paragraph_format.space_after = Pt(0)

                            if row_idx == 0:
                                set_cell_background(cell, "E5E7EB")
                                add_formatted_runs(cp, cell_text, font_size=9.5, bold_default=True, color=RGBColor(0, 0, 0))
                            else:
                                if row_idx % 2 == 1:
                                    set_cell_background(cell, "FFFFFF")
                                else:
                                    set_cell_background(cell, "F9FAFB")
                                add_formatted_runs(cp, cell_text, font_size=9.0, color=RGBColor(0, 0, 0))

            table_rows = []

        if not stripped:
            i += 1
            continue

        if stripped == '---':
            i += 1
            continue

        # Handle Markdown Images (e.g. ![Caption](docs/figures/fig1_architecture.png))
        img_match = re.match(r'^!\[(.*?)\]\((.*?)\)$', stripped)
        if img_match:
            img_alt = img_match.group(1)
            img_src = img_match.group(2)
            possible_paths = [
                img_src,
                os.path.join(os.path.dirname(md_path), img_src),
                os.path.join("d:/sentinelx", img_src),
                os.path.join("d:/sentinelx/docs/figures", os.path.basename(img_src)),
                "docs/srm_logo.jpg",
                "srm_logo.jpg"
            ]
            found_path = None
            for pth in possible_paths:
                if pth and os.path.exists(pth):
                    found_path = pth
                    break

            if found_path:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(12)
                p.paragraph_format.space_after = Pt(4)
                r = p.add_run()
                
                # Sizing: Logo is compact; full architecture and charts take readable width
                if "logo" in found_path.lower():
                    r.add_picture(found_path, width=Inches(2.4))
                else:
                    r.add_picture(found_path, width=Inches(5.8))
            else:
                print(f"Warning: Image path not found: {img_src}")
            i += 1
            continue

        # Handle Figure Captions (*Figure X.Y: ...*)
        if (stripped.startswith('*Figure') or stripped.startswith('*Table') or stripped.startswith('Figure ')) and not in_table:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(10)
            p.paragraph_format.line_spacing = 1.15
            add_formatted_runs(p, stripped, font_size=10.0, italic_default=True, color=RGBColor(55, 65, 81))
            i += 1
            continue

        # Check if line contains a tab (Table of Contents, List of Tables, List of Figures)
        if '\t' in stripped:
            parts = stripped.split('\t')
            title_text = parts[0].strip()
            page_str = parts[1].strip() if len(parts) > 1 else ""

            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(1.5)
            p.paragraph_format.line_spacing = 1.12

            p.paragraph_format.tab_stops.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)

            if re.match(r'^\d+\.\d+\.\d+', title_text):
                p.paragraph_format.left_indent = Inches(0.35)
            elif re.match(r'^\d+\.\d+', title_text):
                p.paragraph_format.left_indent = Inches(0.2)
            else:
                p.paragraph_format.left_indent = Inches(0.0)

            is_major = (
                title_text.startswith(('1. ', '2. ', '3. ', '4. ', '5. ', '6. ', 'Appendix', 'References', 'Bonafide', 'Project Problem', 'Abstract', 'Acknowledgements', 'List of Tables', 'List of Figures', 'Abbreviations'))
                and not re.match(r'^\d+\.\d+', title_text)
            )

            r_title = p.add_run(title_text)
            r_title.font.name = "Times New Roman"
            r_title.font.size = Pt(10)
            r_title.font.color.rgb = RGBColor(0, 0, 0)
            if is_major:
                r_title.bold = True

            if page_str:
                r_tab = p.add_run(f"\t{page_str}")
                r_tab.font.name = "Times New Roman"
                r_tab.font.size = Pt(10)
                r_tab.font.color.rgb = RGBColor(0, 0, 0)
                if is_major:
                    r_tab.bold = True

            i += 1
            continue

        # Level-1 Heading
        if stripped.startswith('# '):
            text = stripped[2:].strip()
            if is_cover_page:
                h = doc.add_paragraph()
                h.alignment = WD_ALIGN_PARAGRAPH.CENTER
                h.paragraph_format.space_before = Pt(16)
                h.paragraph_format.space_after = Pt(12)
                add_formatted_runs(h, text, font_size=15, bold_default=True, color=RGBColor(0, 0, 0))
            else:
                h = doc.add_heading(level=1)
                if should_break_page_for_heading(text):
                    h.paragraph_format.page_break_before = True

                if should_center_heading(text):
                    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
                h.paragraph_format.space_before = Pt(16)
                h.paragraph_format.space_after = Pt(8)
                h.paragraph_format.keep_with_next = True
                add_formatted_runs(h, text, font_size=14, bold_default=True, color=RGBColor(0, 0, 0))
            i += 1
            continue

        # Level-2 Heading
        if stripped.startswith('## '):
            text = stripped[3:].strip()
            
            if is_cover_page:
                if text == "A PROJECT REPORT":
                    p = doc.add_paragraph()
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_before = Pt(8)
                    p.paragraph_format.space_after = Pt(8)
                    add_formatted_runs(p, text, font_size=13, bold_default=True, color=RGBColor(0, 0, 0))
                    i += 1
                    continue
                else:
                    is_cover_page = False

            if should_center_heading(text):
                h = doc.add_heading(level=1)
                if should_break_page_for_heading(text):
                    h.paragraph_format.page_break_before = True
                h.alignment = WD_ALIGN_PARAGRAPH.CENTER
                if "LIST OF FIGURES" in text.upper():
                    h.paragraph_format.space_before = Pt(16)
                else:
                    h.paragraph_format.space_before = Pt(14)
                h.paragraph_format.space_after = Pt(8)
                h.paragraph_format.keep_with_next = True
                add_formatted_runs(h, text, font_size=14, bold_default=True, color=RGBColor(0, 0, 0))
            else:
                h = doc.add_heading(level=2)
                if should_break_page_for_heading(text):
                    h.paragraph_format.page_break_before = True
                h.alignment = WD_ALIGN_PARAGRAPH.LEFT
                h.paragraph_format.space_before = Pt(12)
                h.paragraph_format.space_after = Pt(4)
                h.paragraph_format.keep_with_next = True
                add_formatted_runs(h, text, font_size=12.5, bold_default=True, color=RGBColor(0, 0, 0))
            i += 1
            continue

        # Level-3 Heading
        if stripped.startswith('### '):
            text = stripped[4:].strip()
            h = doc.add_heading(level=3)
            h.alignment = WD_ALIGN_PARAGRAPH.LEFT
            h.paragraph_format.space_before = Pt(10)
            h.paragraph_format.space_after = Pt(3)
            h.paragraph_format.keep_with_next = True
            add_formatted_runs(h, text, font_size=11.5, bold_default=True, color=RGBColor(0, 0, 0))
            i += 1
            continue

        # Level-4 Heading
        if stripped.startswith('#### '):
            text = stripped[5:].strip()
            h = doc.add_heading(level=4)
            h.alignment = WD_ALIGN_PARAGRAPH.LEFT
            h.paragraph_format.space_before = Pt(8)
            h.paragraph_format.space_after = Pt(2)
            h.paragraph_format.keep_with_next = True
            add_formatted_runs(h, text, font_size=11, bold_default=True, color=RGBColor(0, 0, 0))
            i += 1
            continue

        # Bullet lists
        if stripped.startswith('- ') or stripped.startswith('* '):
            text = stripped[2:].strip()
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            add_formatted_runs(p, text, font_size=11.5, color=RGBColor(0, 0, 0))
            i += 1
            continue

        # Numbered lists - FIXED TO PREVENT GLOBAL CONTINUOUS NUMBERING BUG
        num_match = re.match(r'^(\d+)\.\s+(.*)$', stripped)
        if num_match and not is_cover_page:
            num_val = num_match.group(1)
            text = num_match.group(2)
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.35)
            p.paragraph_format.first_line_indent = Inches(-0.35)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(2.5)
            p.paragraph_format.line_spacing = 1.15
            r_num = p.add_run(f"{num_val}. ")
            r_num.font.name = "Times New Roman"
            r_num.font.size = Pt(11.5)
            r_num.font.color.rgb = RGBColor(0, 0, 0)
            add_formatted_runs(p, text, font_size=11.5, color=RGBColor(0, 0, 0))
            i += 1
            continue

        # Regular paragraph
        p = doc.add_paragraph()
        if is_cover_page:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(4)
            add_formatted_runs(p, stripped, font_size=11.5, bold_default=False, color=RGBColor(0, 0, 0))
        else:
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(5)
            p.paragraph_format.line_spacing = 1.2
            add_formatted_runs(p, stripped, font_size=11.5, color=RGBColor(0, 0, 0))

        i += 1

    doc.save(docx_path)
    print(f"Document successfully created at {docx_path}, size: {os.path.getsize(docx_path)} bytes")

if __name__ == "__main__":
    md_file = "d:/sentinelx/docs/project_report_fixed.md"
    docx_file = "d:/sentinelx/SentinelX_Project_Report_Final.docx"
    parse_markdown_to_docx(md_file, docx_file)
    # Also save as SentinelX_Project_Report_Fixed.docx
    parse_markdown_to_docx(md_file, "d:/sentinelx/SentinelX_Project_Report_Fixed.docx")
    parse_markdown_to_docx(md_file, "d:/sentinelx/docs/project_report.docx")
