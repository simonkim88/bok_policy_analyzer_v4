import pdfplumber
from pathlib import Path

pdf_path = Path("data/pdfs/minutes_2025_10_23.pdf")
target_phrases = [
    "금융통화위원회는 다음 통화정책방향",
    "국내경제는",
    "소비자물가는",
    "앞으로 성장세는",
    "금년중 소비자물가 상승률은"
]

print(f"Reading PDF: {pdf_path}")
if not pdf_path.exists():
    print("File not found.")
    exit()

full_text = ""
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        full_text += page.extract_text() + "\n"

print("\n--- Searching for Resolution Text (Oct 2025) ---")

for phrase in target_phrases:
    print(f"\n[Phrase: {phrase}]")
    idx = full_text.find(phrase)
    if idx != -1:
        # Extract surrounding context
        start = max(0, idx - 100)
        end = min(len(full_text), idx + 600)
        print(f"Index: {idx}")
        print(f"Context: ...{full_text[start:end].replace(chr(10), ' ')}...")
    else:
        print("Not found.")
