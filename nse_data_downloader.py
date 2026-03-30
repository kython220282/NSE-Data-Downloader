"""
Interactive NSE Historical Data Downloader
Downloads daily/weekly/monthly/quarterly/yearly OHLC data for NSE stocks and indices
"""

import NseUtility
import pandas as pd
from datetime import datetime, timedelta
import time


def normalize_index_name(name):
    """Normalize index name for better matching with NSE index names."""
    if not name:
        return name

    replacements = {
        'nifty': 'NIFTY',
        'sensex': 'SENSEX',
        'bankex': 'BANKEX',
    }

    words = name.split()
    normalized_words = []
    for word in words:
        normalized_words.append(replacements.get(word.lower(), word))
    return ' '.join(normalized_words)

def get_date_input(prompt):
    """Get date input from user in DD-MM-YYYY format."""
    while True:
        date_str = input(prompt)
        try:
            date_obj = datetime.strptime(date_str, '%d-%m-%Y')
            return date_obj, date_str
        except ValueError:
            print("❌ Invalid date format! Please use DD-MM-YYYY (e.g., 01-01-2021)")

def _prepare_ohlcv_for_resample(df):
    """Clean and normalize OHLCV fields before time aggregation."""
    clean_df = df.copy()
    clean_df['Date'] = pd.to_datetime(clean_df['Date'], format='%d-%m-%Y', errors='coerce')
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        clean_df[col] = pd.to_numeric(clean_df[col], errors='coerce')
    clean_df = clean_df.dropna(subset=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
    clean_df = clean_df.sort_values('Date')
    return clean_df

def _resample_ohlcv(df, rule):
    """Resample OHLCV while preserving the symbol column."""
    clean_df = _prepare_ohlcv_for_resample(df)
    if clean_df.empty:
        return pd.DataFrame(columns=['Symbol', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume'])

    symbol_name = clean_df['Symbol'].iloc[0] if 'Symbol' in clean_df.columns else ''
    clean_df = clean_df.set_index('Date')

    sampled = clean_df.resample(rule).agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })

    sampled = sampled.dropna().reset_index()
    sampled['Date'] = sampled['Date'].dt.strftime('%d-%m-%Y')
    sampled.insert(0, 'Symbol', symbol_name)
    return sampled[['Symbol', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]

def resample_to_weekly(df):
    """Convert daily data to weekly data."""
    return _resample_ohlcv(df, 'W-FRI')

def resample_to_monthly(df):
    """Convert daily data to monthly data."""
    return _resample_ohlcv(df, 'ME')

def resample_to_quarterly(df):
    """Convert daily data to quarterly data (calendar quarter)."""
    return _resample_ohlcv(df, 'QE-DEC')

def resample_to_yearly(df):
    """Convert daily data to yearly data (calendar year)."""
    return _resample_ohlcv(df, 'YE-DEC')

def main():
    print("=" * 100)
    print(" " * 30 + "NSE HISTORICAL DATA DOWNLOADER")
    print("=" * 100)
    
    # Get user inputs
    print("\n📊 Select Instrument Type")
    print("1. Index")
    print("2. Stock/ETF")
    while True:
        instrument_choice = input("Enter choice (1/2): ").strip()
        if instrument_choice in ['1', '2']:
            instrument_type = 'Index' if instrument_choice == '1' else 'Stock/ETF'
            break
        print("❌ Invalid choice! Please enter 1 or 2")

    if instrument_type == 'Index':
        print("\n📊 Enter the NSE Index Name")
        print("Examples: NIFTY 50, Nifty Bank, Nifty Midcap 150, NIFTY IT")
        symbol = normalize_index_name(input("Index Name: ").strip())
    else:
        print("\n📊 Enter the NSE Stock/ETF Symbol")
        print("Examples: RELIANCE, TCS, INFY, NIFTYBEES, BANKBEES")
        symbol = input("Stock/ETF Symbol: ").strip().upper()
    
    print("\n📅 Enter Date Range")
    from_date_obj, from_date_str = get_date_input("From Date (DD-MM-YYYY): ")
    to_date_obj, to_date_str = get_date_input("To Date (DD-MM-YYYY): ")
    
    # Validate date range
    if to_date_obj <= from_date_obj:
        print("❌ Error: 'To Date' must be after 'From Date'")
        return
    
    print("\n⏱️ Select Timeframe")
    print("1. Daily (1d)")
    print("2. Weekly (1w)")
    print("3. Monthly (1m)")
    print("4. Quarterly (1q)")
    print("5. Yearly (1y)")
    
    while True:
        choice = input("Enter choice (1/2/3/4/5): ").strip()
        if choice in ['1', '2', '3', '4', '5']:
            timeframe = {'1': '1d', '2': '1w', '3': '1m', '4': '1q', '5': '1y'}[choice]
            break
        print("❌ Invalid choice! Please enter 1, 2, 3, 4, or 5")
    
    print("\n" + "=" * 100)
    print("DOWNLOAD SETTINGS")
    print("=" * 100)
    print(f"  Type:         {instrument_type}")
    print(f"  Symbol/Index: {symbol}")
    print(f"  From Date:    {from_date_str}")
    print(f"  To Date:      {to_date_str}")
    print(f"  Timeframe:    {timeframe}")
    print("=" * 100)
    
    confirm = input("\nProceed with download? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Download cancelled.")
        return
    
    # Initialize NSE
    print("\n🔄 Initializing NSE connection...")
    nse = NseUtility.NseUtils()
    
    # Download data day by day
    print(f"📥 Downloading data from {from_date_str} to {to_date_str}...")
    print("   This may take a few minutes...\n")
    
    all_data = []
    successful_downloads = 0
    holidays_skipped = 0
    failed_downloads = 0
    
    current_date = from_date_obj
    total_days = (to_date_obj - from_date_obj).days
    day_counter = 0
    
    while current_date <= to_date_obj:
        day_counter += 1
        date_str = current_date.strftime('%d-%m-%Y')
        
        # Progress indicator
        if day_counter % 50 == 0:
            progress = (day_counter / total_days) * 100
            print(f"   Progress: {progress:.1f}% | Downloaded: {successful_downloads} days")
        
        try:
            if instrument_type == 'Index':
                bhav_data = nse.bhav_copy_indices(date_str)
                if bhav_data is not None and not bhav_data.empty:
                    index_data = bhav_data[bhav_data['Index Name'] == symbol]
                    if index_data.empty:
                        index_data = bhav_data[bhav_data['Index Name'].str.contains(symbol, case=False, na=False)]

                    if not index_data.empty:
                        row = index_data.iloc[0]
                        all_data.append({
                            'Symbol': row['Index Name'],
                            'Date': row['Index Date'],
                            'Open': row['Open Index Value'],
                            'High': row['High Index Value'],
                            'Low': row['Low Index Value'],
                            'Close': row['Closing Index Value'],
                            'Volume': row['Volume']
                        })
                        successful_downloads += 1
                    else:
                        holidays_skipped += 1
                else:
                    holidays_skipped += 1
            else:
                bhav_data = nse.bhav_copy_with_delivery(date_str)
                if bhav_data is not None and not bhav_data.empty:
                    stock_data = bhav_data[bhav_data['SYMBOL'] == symbol]
                    if not stock_data.empty:
                        row = stock_data.iloc[0]
                        all_data.append({
                            'Symbol': row['SYMBOL'],
                            'Date': date_str,
                            'Open': row['OPEN_PRICE'],
                            'High': row['HIGH_PRICE'],
                            'Low': row['LOW_PRICE'],
                            'Close': row['CLOSE_PRICE'],
                            'Volume': row['TTL_TRD_QNTY']
                        })
                        successful_downloads += 1
                    else:
                        holidays_skipped += 1
                else:
                    holidays_skipped += 1

            if successful_downloads > 0 and successful_downloads % 100 == 0:
                print(f"   ✓ {successful_downloads} trading days downloaded")
                
        except Exception as e:
            if "No data available" in str(e):
                holidays_skipped += 1
            else:
                failed_downloads += 1
                if failed_downloads <= 5:
                    print(f"   ⚠️ Error on {date_str}: {str(e)[:60]}")
        
        current_date += timedelta(days=1)
        
        # Small delay to avoid overwhelming server
        if day_counter % 10 == 0:
            time.sleep(0.2)
    
    print("\n" + "=" * 100)
    print("DOWNLOAD COMPLETE")
    print("=" * 100)
    print(f"  Trading days downloaded:  {successful_downloads}")
    print(f"  Holidays/Weekends:        {holidays_skipped}")
    print(f"  Failed downloads:         {failed_downloads}")
    
    if not all_data:
        print("\n❌ No data was downloaded. Please check:")
        print("   - Symbol/Index name is correct")
        print("   - Date range includes trading days")
        print("   - NSE website is accessible")
        return
    
    # Create DataFrame
    df = pd.DataFrame(all_data)
    
    # Apply timeframe resampling if needed
    if timeframe == '1w':
        print("\n📊 Resampling to weekly data...")
        df = resample_to_weekly(df)
    elif timeframe == '1m':
        print("\n📊 Resampling to monthly data...")
        df = resample_to_monthly(df)
    elif timeframe == '1q':
        print("\n📊 Resampling to quarterly data...")
        df = resample_to_quarterly(df)
    elif timeframe == '1y':
        print("\n📊 Resampling to yearly data...")
        df = resample_to_yearly(df)
    
    # Get actual symbol name from data
    actual_symbol = df['Symbol'].iloc[0] if len(df) > 0 else symbol
    
    print("\n" + "=" * 100)
    print("DATA SUMMARY")
    print("=" * 100)
    print(f"  Symbol:        {actual_symbol}")
    print(f"  Total Records: {len(df)}")
    print(f"  Date Range:    {df['Date'].min()} to {df['Date'].max()}")
    print(f"  Timeframe:     {timeframe}")
    
    print("\n  First 5 rows:")
    print(df.head().to_string(index=False))
    
    print("\n  Last 5 rows:")
    print(df.tail().to_string(index=False))
    
    # Save to CSV
    safe_symbol = actual_symbol.replace(' ', '_').replace('/', '_')
    filename = f"{safe_symbol}_{timeframe}_{from_date_obj.strftime('%Y%m%d')}_to_{to_date_obj.strftime('%Y%m%d')}.csv"
    
    df.to_csv(filename, index=False)
    
    print("\n" + "=" * 100)
    print(f"✅ SUCCESS! Data saved to: {filename}")
    print("=" * 100)
    print(f"\n📁 File contains {len(df)} records with columns: Symbol, Date, Open, High, Low, Close, Volume")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Download cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
