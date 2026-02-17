import requests
from bs4 import BeautifulSoup
import os

# Setup directories
base_dir = "data"
print(f"Current Working Directory: {os.getcwd()}")
os.makedirs(f"{base_dir}/01_minutes/pdf", exist_ok=True)
os.makedirs(f"{base_dir}/02_decision_statements/pdf", exist_ok=True)
os.makedirs(f"{base_dir}/03_press_conferences/opening_remarks", exist_ok=True)
os.makedirs(f"{base_dir}/03_press_conferences/q_and_a", exist_ok=True)

def download_file(url, filepath):
    print(f"Downloading {url} to {filepath}...")
    try:
        response = requests.get(url, verify=False, stream=True)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        if os.path.exists(filepath):
             print(f"File successfully created at {filepath}, size: {os.path.getsize(filepath)} bytes")
        else:
             print(f"Error: File verified as MISSING at {filepath}")
        print("Done.")
        return True
    except Exception as e:
        print(f"Failed to download: {e}")
        return False

# 1. Decision Statement (Jan 2026)
# Direct link found from search
decision_url = "https://www.bok.or.kr/portal/cmm/fms/FileDown.do?atchFileId=FILE_000000000000371&fileSn=1&apndFile=Y"
download_file(decision_url, f"{base_dir}/02_decision_statements/pdf/decision_statement_2026_01.pdf")

# 2. Minutes (Jan 2026)
# Scrape the list page
minutes_list_url = "https://www.bok.or.kr/portal/bbs/B0000224/list.do?menuNo=200760"
print(f"Scraping Minutes from {minutes_list_url}...")
try:
    res = requests.get(minutes_list_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    # Find the link for Jan 2026 (usually title contains "2026" and "1월" or "1차")
    # Note: Regex or simple string matching
    found_minutes = False
    for a in soup.find_all('a'):
        text = a.get_text(strip=True)
        # Debug: Print potential titles
        if "의사록" in text:
            print(f"Candidate: {text}")
        
        if "2026년" in text and ("1차" in text or "1월" in text) and "의사록" in text:
            print(f"Found Minutes entry: {text}")
            # The link might be to a view page, which then has the PDF download
            # Or it might be a direct download if it's an attachment icon
            href = a['href']
            full_href = f"https://www.bok.or.kr{href}" if href.startswith('/') else href
            
            # Use a slightly more robust way: Navigate to the view page then find file download
            if "view.do" in full_href:
                print(f"Navigating to view page: {full_href}")
                view_res = requests.get(full_href, verify=False)
                view_soup = BeautifulSoup(view_res.text, 'html.parser')
                # Find file download link
                file_link = view_soup.find('a', href=lambda x: x and 'FileDown.do' in x)
                if file_link:
                    file_url = f"https://www.bok.or.kr{file_link['href']}" if file_link['href'].startswith('/') else file_link['href']
                    download_file(file_url, f"{base_dir}/01_minutes/pdf/minutes_2026_01.pdf")
                    found_minutes = True
                    break
    
    if not found_minutes:
        print("Could not find Jan 2026 Minutes on the first page.")

except Exception as e:
    print(f"Error scraping minutes: {e}")


# 3. Press Conference (Remarks & Q&A)
# Try to find recent press releases or specific search
# Just a placeholder log for now as direct links are hard to simplify without more scraping logic
print("Skipping automatic download for Press Conference files (requires more complex scraping).")

