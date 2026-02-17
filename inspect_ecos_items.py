import requests
import json

ECOS_API_KEY = "LZUNMUPZQ4FFUITEF1R7"

def inspect_ecos_items(stat_code):
    base_url = f"https://ecos.bok.or.kr/api/StatisticItemList/{ECOS_API_KEY}/json/kr/1/1000/{stat_code}"
    
    print(f"Inspecting items for table: {stat_code}...")
    
    try:
        response = requests.get(base_url)
        response.raise_for_status()
        data = response.json()
        
        if "StatisticItemList" not in data:
            print("Error: Invalid API response format.")
            print(data)
            return

        rows = data["StatisticItemList"]["row"]
        
        print("-" * 100)
        print(f"{'Item Code':<15} | {'Item Name':<50} | {'Cycle'}")
        print("-" * 100)
        
        for row in rows:
            print(f"{row['ITEM_CODE']:<15} | {row['ITEM_NAME']:<50} | {row['CYCLE']}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    inspect_ecos_items("200Y104")
