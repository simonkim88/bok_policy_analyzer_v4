import pdfplumber
from pathlib import Path

pdf_path = Path("data/pdfs/minutes_2025_10_23.pdf")
print(f"Reading PDF: {pdf_path}")

with pdfplumber.open(pdf_path) as pdf:
    total_pages = len(pdf.pages)
    print(f"Total Pages: {total_pages}")
    
    # Read last 3 pages
    for i in range(max(0, total_pages - 3), total_pages):
        print(f"\n--- Page {i+1} ---")
        print(pdf.pages[i].extract_text())
