import requests
from bs4 import BeautifulSoup
import re

def search_bok(query):
    url = "https://www.bok.or.kr/portal/main/contents/search/search.do"
    params = {
        "menuNo": "200091",
        "query": query
    }
    try:
        response = requests.get(url, params=params, verify=False) # Skip verify for now to avoid SSL issues
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for links that might be PDFs or download pages
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text(strip=True)
            if 'pdf' in href.lower() or 'download' in href.lower() or 'pdf' in text.lower():
                full_url = href if href.startswith('http') else f"https://www.bok.or.kr{href}"
                links.append((text, full_url))
        
        return links
    except Exception as e:
        print(f"Error searching for {query}: {e}")
        return []

queries = [
    "2026년 1월 통화정책방향 의결문",
    "2026년 1월 금융통화위원회 의사록",
    "2026년 1월 총재 기자간담회",
    "금융안정보고서 2025년 12월",
    "통화신용정책보고서 2025년 12월"
]

print("Searching BOK for documents. Please wait...")
found_files = {}

for q in queries:
    print(f"\nQuery: {q}")
    results = search_bok(q)
    for text, url in results:
        print(f"  Found: {text} -> {url}")
        # Simple heuristic to identify target files
        if "의결문" in q and "의결문" in text:
            found_files["decision"] = url
        elif "의사록" in q and "의사록" in text:
            found_files["minutes"] = url
        elif "기자간담회" in q and ("모두발언" in text or "질의응답" in text):
            if "모두발언" in text: found_files["remarks"] = url
            if "질의응답" in text: found_files["qa"] = url

print("\n--- Summary of Candidates ---")
for k, v in found_files.items():
    print(f"{k}: {v}")
