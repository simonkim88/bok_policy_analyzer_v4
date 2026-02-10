import sys
from pathlib import Path
from src.data.database import DatabaseManager

def verify_forecast_flow():
    print("Verifying Forecast Automation Flow...")
    
    db = DatabaseManager()
    
    # 1. Seed Data (Simulating a successful crawl)
    release_date = '2025-11-27'
    print(f"Seeding database with forecast for {release_date}...")
    
    # 2025년 전망 (Target Year: 2025)
    db.save_forecast(
        release_date=release_date,
        target_year=2025,
        gdp_growth=1.0,
        cpi_inflation=2.1,
        source_url="http://test-url.com",
        description="Verification Test Forecast"
    )
    
    # 2. Retrieve Data (Simulating UI behavior)
    print("Retrieving latest forecast from database...")
    latest = db.get_latest_forecast(target_date='2025-11-27')
    
    if not latest:
        print("FAIL: No forecast retrieved.")
        return
        
    print(f"Retrieved Forecast: {latest}")
    
    # 3. Verify Values
    forecasts = latest.get('forecasts', {})
    if 2025 in forecasts:
        gdp = forecasts[2025]['gdp']
        cpi = forecasts[2025]['cpi']
        
        print(f"2025 Forecast - GDP: {gdp}%, CPI: {cpi}%")
        
        if gdp == 1.0 and cpi == 2.1:
            print("SUCCESS: Values match the expected corrected figures.")
        else:
            print(f"FAIL: Values do not match. Expected GDP 1.0, CPI 2.1. Got GDP {gdp}, CPI {cpi}")
    else:
        print("FAIL: 2025 forecast not found in result.")

if __name__ == "__main__":
    verify_forecast_flow()
