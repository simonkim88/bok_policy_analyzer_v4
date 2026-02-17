import pandas as pd
import numpy as np
import statsmodels.api as sm
from src.ecos_loader import get_base_rate, get_cpi, get_gdp_real

def calculate_taylor_rule(
    alpha=0.5, 
    beta=0.5, 
    r_star=2.0, 
    pi_star=2.0
):
    """
    Calculates Taylor Rule Rate.
    
    Formula: i = r* + pi + alpha(pi - pi*) + beta(y)
    
    Args:
        alpha (float): Weight on inflation gap.
        beta (float): Weight on output gap.
        r_star (float): Neutral real interest rate.
        pi_star (float): Inflation target.
        
    Returns:
        pd.DataFrame: Merged data with calculated Taylor Rule Rate.
    """
    
    # 1. Fetch Data
    base_rate_df = get_base_rate()
    cpi_df = get_cpi()
    gdp_df = get_gdp_real()
    
    # 2. Process Data
    # Convert dates to datetime for merging
    base_rate_df['Date'] = pd.to_datetime(base_rate_df['Date'], format='%Y%m')
    cpi_df['Date'] = pd.to_datetime(cpi_df['Date'], format='%Y%m')
    
    # GDP is Quarterly. We need to upsample to Monthly or downsample others to Quarterly.
    # Taylor rule is often analyzed Quarterly, but Monthly is good for high freq.
    # Let's upsample GDP to Monthly (ffill or interpolation) for smoother chart, 
    # OR calculate Output Gap on Quarterly and then ffill result to Monthly.
    
    # Process GDP for Output Gap
    gdp_df['Date'] = pd.to_datetime(gdp_df['Date']) # YYYYQn handled by pandas? No.
    # Custom parser for 2010Q1
    gdp_df['Date'] = gdp_df['Date'].apply(lambda x: pd.to_datetime(str(x).replace('Q1', '-03-31').replace('Q2', '-06-30').replace('Q3', '-09-30').replace('Q4', '-12-31')))
    
    # Log GDP
    gdp_df['ln_GDP'] = np.log(gdp_df['Value'])
    
    # HP Filter for Potential GDP
    # Lambda for quarterly data is usually 1600.
    cycle, trend = sm.tsa.filters.hpfilter(gdp_df['ln_GDP'], lamb=1600)
    gdp_df['Potential_ln_GDP'] = trend
    gdp_df['Output_Gap'] = (gdp_df['ln_GDP'] - gdp_df['Potential_ln_GDP']) * 100
    
    # Merge GDP (Quarterly) into Monthly timeframe
    # Create a monthly date range covering the full period
    start_date = min(base_rate_df['Date'].min(), cpi_df['Date'].min(), gdp_df['Date'].min())
    end_date = max(base_rate_df['Date'].max(), cpi_df['Date'].max(), gdp_df['Date'].max())
    dates = pd.date_range(start=start_date, end=end_date, freq='ME') # Month End
    
    merged_df = pd.DataFrame({'Date': dates})
    
    # Merge Data
    merged_df = pd.merge_asof(merged_df, base_rate_df.rename(columns={'Value': 'Base_Rate'}), on='Date', direction='backward')
    merged_df = pd.merge_asof(merged_df, cpi_df.rename(columns={'Value': 'CPI'}), on='Date', direction='backward')
    
    # For GDP Output Gap, we forward fill the quarterly value to subsequent months
    # Resample GDP to daily/monthly then merge? merge_asof with backward takes the latest known quarter value.
    merged_df = pd.merge_asof(merged_df, gdp_df[['Date', 'Output_Gap']], on='Date', direction='backward')
    
    # 3. Calculate Inflation (YoY)
    # Ensure correct sorting
    merged_df = merged_df.sort_values('Date')
    merged_df['Inflation'] = merged_df['CPI'].pct_change(periods=12) * 100
    
    # 4. Taylor Rule Calculation
    # i = r* + pi + alpha(pi - pi*) + beta(y)
    # We use current inflation (pi_t)
    
    # Dealing with NaN (start of period)
    merged_df = merged_df.dropna()
    
    merged_df['Inflation_Gap'] = merged_df['Inflation'] - pi_star
    
    merged_df['Taylor_Rate'] = r_star + merged_df['Inflation'] + \
                               (alpha * merged_df['Inflation_Gap']) + \
                               (beta * merged_df['Output_Gap'])
                               
    return merged_df

if __name__ == "__main__":
    df = calculate_taylor_rule()
    print(df[['Date', 'Base_Rate', 'Inflation', 'Output_Gap', 'Taylor_Rate']].tail(10))
