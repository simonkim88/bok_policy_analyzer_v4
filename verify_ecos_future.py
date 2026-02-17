from src.data.ecos_api import EcosAPI, StatCode
import pandas as pd
from datetime import datetime

def check_future_data():
    api = EcosAPI()
    print("Checking ECOS API for future data (forecasts)...")
    
    # 1. Check CPI (Consumer Price Index)
    print("\n[1] Checking Consumer Price Index (901Y009)")
    try:
        # Fetch data up to a future date (e.g., end of next year)
        future_date = (datetime.now().year + 1) * 100 + 12 # next year Dec
        start_date = (datetime.now().year - 1) * 100 + 1 # last year Jan
        
        df = api.fetch_data(
            stat_code=StatCode.CPI,
            period_type="M",
            start_date=str(start_date),
            end_date=str(future_date),
            item_code1="0" # All items
        )
        
        if df is not None:
            last_row = df.iloc[-1]
            last_date = last_row['TIME']
            print(f"Latest CPI Data Available: {last_date}")
            print(f"Value: {last_row['DATA_VALUE']}")
            
            # Check if it's in the future
            today_str = datetime.now().strftime("%Y%m")
            if last_date > today_str:
                print(">> ECOS contains FUTURE/FORECAST data!")
            else:
                print(">> ECOS contains only HISTORICAL data.")
        else:
            print("Failed to fetch CPI data.")
            
    except Exception as e:
        print(f"Error checking CPI: {e}")

if __name__ == "__main__":
    check_future_data()
