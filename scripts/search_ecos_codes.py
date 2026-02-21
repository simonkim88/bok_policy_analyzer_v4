import requests
import os
import json

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def search_ecos_tables(keyword="전망"):
    # TODO: Remove hardcoded fallback key in production
    api_key = os.environ.get('ECOS_API_KEY', 'LZUNMUPZQ4FFUITEF1R7')
    base_url = f"https://ecos.bok.or.kr/api/StatisticTableList/{api_key}/json/kr/1/1000/"
    
    print(f"Searching ECOS tables for keyword: '{keyword}'...")
    
    try:
        response = requests.get(base_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if "StatisticTableList" not in data:
            print("Error: Invalid API response format.")
            if "RESULT" in data:
                print(f"Message: {data['RESULT']['MESSAGE']}")
            return

        rows = data["StatisticTableList"]["row"]
        found = False
        
        print("-" * 80)
        print(f"{'Code':<10} | {'Table Name':<50}")
        print("-" * 80)
        
        for row in rows:
            stat_name = row["STAT_NAME"]
            if keyword in stat_name:
                print(f"{row['STAT_CODE']:<10} | {stat_name}")
                found = True
                
        if not found:
            print(f"No tables found containing '{keyword}'.")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    search_ecos_tables("전망")
    print("\n")
    search_ecos_tables("경제")
