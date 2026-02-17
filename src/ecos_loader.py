import requests
import pandas as pd
from datetime import datetime, timedelta

ECOS_API_KEY = "LZUNMUPZQ4FFUITEF1R7"

def fetch_ecos_data(stat_code, item_code1, item_code2="?", cycle_type="M", start_date="20100101", end_date=None):
    """
    Fetches data from BOK ECOS API.
    
    Args:
        stat_code (str): Statistic Table Code (e.g., '722Y001')
        item_code1 (str): Item Code 1
        item_code2 (str): Item Code 2 (default '?')
        cycle_type (str): Cycle Type ('M', 'Q', 'A', 'D')
        start_date (str): Start date (YYYYMMDD or YYYYMM)
        end_date (str): End date (defaults to today)
        
    Returns:
        pd.DataFrame: DataFrame with 'Date' and 'Value' columns.
    """
    if end_date is None:
        end_date = datetime.now().strftime("%Y%m%d")
        
    # Adjust date format based on cycle
    if cycle_type == 'M':
        start_date = start_date[:6]
        end_date = end_date[:6]
    elif cycle_type == 'Q':
        start_date = start_date[:6] # ECOS expects YYYYQn for quarter but let's see if YYYYMM works or if we need conversion
        # ECOS API format for Quarter: 2020Q1
        # We might need a helper if user passes YYYYMM. 
        # For now assuming user provides correct format or we handle simple YYYYMM -> API format if needed.
        pass 

    url = f"https://ecos.bok.or.kr/api/StatisticSearch/{ECOS_API_KEY}/json/kr/1/10000/{stat_code}/{cycle_type}/{start_date}/{end_date}/{item_code1}/{item_code2}/"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if "StatisticSearch" not in data:
            print(f"Error fetching {stat_code}: {data.get('RESULT', {}).get('MESSAGE', 'Unknown Error')}")
            return pd.DataFrame()
            
        rows = data["StatisticSearch"]["row"]
        df = pd.DataFrame(rows)
        
        # Select relevant columns
        df = df[['TIME', 'DATA_VALUE']]
        df.columns = ['Date', 'Value']
        df['Value'] = pd.to_numeric(df['Value'])
        
        return df
        
    except Exception as e:
        print(f"Exception fetching ECOS data: {e}")
        return pd.DataFrame()

def get_base_rate():
    # 722Y001: 1.3.1. 한국은행 기준금리 및 여수신금리
    # Item 1: 0101000 (한국은행 기준금리)
    print("Fetching Base Rate...")
    return fetch_ecos_data("722Y001", "0101000", cycle_type="M", start_date="201001")

def get_cpi():
    # 901Y009: 4.1.1 소비자물가지수(2020=100) (전국, 특수분류)
    # Item 1: 0 (총지수)
    print("Fetching CPI...")
    # Using YoY change often requires fetching the index and calculating pct_change, 
    # Or checking if ECOS provides inflation rate directly. 
    # Usually 901Y009 provides the Index. 902Y006 might provide inflation rate.
    # Let's fetch Index first to correspond with Taylor rule \pi_t calculation (YoY).
    return fetch_ecos_data("901Y009", "0", cycle_type="M", start_date="200901")

def get_gdp_real():
    # 200Y104: 2.1.2.1.2. 경제활동별 GDP 및 GNI(계절조정, 실질, 분기)
    # Item: 1400 (국내총생산(시장가격, GDP))
    print("Fetching Real GDP (Quarterly, SA)...")
    
    # Date format for Quarter in ECOS: YYYYQn
    # Converter needed from start_date (YYYYMM) to YYYYQn
    # Simple logic: 2010Q1
    start_q = "2010Q1"
    
    # Calculate current quarter
    now = datetime.now()
    curr_q = f"{now.year}Q{(now.month-1)//3 + 1}"
    
    return fetch_ecos_data("200Y104", "1400", cycle_type="Q", start_date=start_q, end_date=curr_q)

if __name__ == "__main__":
    # Test
    base_rate = get_base_rate()
    print(f"Base Rate (Last 5):\n{base_rate.tail()}")
    
    cpi = get_cpi()
    print(f"CPI (Last 5):\n{cpi.tail()}")
    
    gdp = get_gdp_real()
    print(f"GDP Real (Last 5):\n{gdp.tail()}")
