import pdfplumber
import os

pdf_files = [
    "data/01_minutes/pdf/minutes_2026_01.pdf",
    "data/02_decision_statements/pdf/decision_statement_2026_01.pdf",
    "data/03_press_conferences/opening_remarks/opening_remarks_2026_01.pdf",
    "data/05_policy_reports/reference_2026_01.pdf"
]

def extract_text(pdf_path, txt_path):
    print(f"Extracting {pdf_path} -> {txt_path}")
    try:
        if not os.path.exists(pdf_path):
            print(f"Skipping missing file: {pdf_path}")
            return
            
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        
        os.makedirs(os.path.dirname(txt_path), exist_ok=True)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        print("Success.")
    except Exception as e:
        print(f"Failed to extract {pdf_path}: {e}")

# Define output paths
mappings = {
    "data/01_minutes/pdf/minutes_2026_01.pdf": "data/01_minutes/txt/minutes_2026_01.txt",
    "data/02_decision_statements/pdf/decision_statement_2026_01.pdf": "data/02_decision_statements/txt/decision_statement_2026_01.txt",
    "data/03_press_conferences/opening_remarks/opening_remarks_2026_01.pdf": "data/03_press_conferences/txt/opening_remarks_2026_01.txt",
    "data/05_policy_reports/reference_2026_01.pdf": "data/05_policy_reports/txt/reference_2026_01.txt"
}

for pdf, txt in mappings.items():
    extract_text(pdf, txt)
