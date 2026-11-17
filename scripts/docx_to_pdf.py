import os
import sys
import win32com.client

def convert(docx_path, pdf_path):
    docx_path = os.path.abspath(docx_path)
    pdf_path = os.path.abspath(pdf_path)
    
    word = win32com.client.Dispatch('Word.Application')
    word.Visible = False
    try:
        doc = word.Documents.Open(docx_path)
        # 17 = wdFormatPDF
        doc.SaveAs(pdf_path, FileFormat=17)
        doc.Close()
        print(f"Successfully converted {docx_path} to {pdf_path}")
    finally:
        word.Quit()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python docx_to_pdf.py <input.docx> <output.pdf>")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
