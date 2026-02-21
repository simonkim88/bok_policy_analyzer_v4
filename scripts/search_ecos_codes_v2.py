import requests
import json
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def search_ecos_tables(keyword):
    # TODO: Remove hardcoded fallback key in production
    api_key = os.environ.get('ECOS_API_KEY', 'LZUNMUPZQ4FFUITEF1R7')
    base_url = f"https://ecos.bok.or.kr/api/StatisticTableList/{api_key}/json/kr/1/1000/"
    
    print(f"Searching ECOS tables for keyword: '{keyword}'...")
    
    try:
        response = requests.get(base_url, timeout=30)
        data = response.json()
        
        if "StatisticTableList" in data:
            rows = data["StatisticTableList"]["row"]
            found = False
            for row in rows:
                if keyword in row["STAT_NAME"]:
                    print(f"{row['STAT_CODE']} : {row['STAT_NAME']}")
                    found = True
            if not found:
                print(f"No match for '{keyword}'")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    search_ecos_tables("성장률")
    print("-" * 20)
    search_ecos_tables("물가")
