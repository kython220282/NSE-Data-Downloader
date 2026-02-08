"""
Interactive NSE Historical Data Downloader
Downloads daily/weekly/monthly OHLC data for NSE stocks and indices
"""

import NseUtility
import pandas as pd
from datetime import datetime, timedelta
import time

def get_date_input(prompt):
    """Get date input from user in DD-MM-YYYY format."""
    while True:
        date_str = input(prompt)
        try:
            date_obj = datetime.strptime(date_str, '%d-%m-%Y')
            return date_obj, date_str
        except ValueError:
            print("❌ Invalid date format! Please use DD-MM-YYYY (e.g., 01-01-2021)")

def resample_to_weekly(df):
    """Convert daily data to weekly data."""
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
    df.set_index('Date', inplace=True)
    
    weekly = df.resample('W-FRI').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })
    
    weekly = weekly.dropna()
    weekly.reset_index(inplace=True)
    weekly['Date'] = weekly['Date'].dt.strftime('%d-%m-%Y')
    return weekly

def resample_to_monthly(df):
    """Convert daily data to monthly data."""
    df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
    df.set_index('Date', inplace=True)
    
    monthly = df.resample('M').agg({
        'Open': 'first',
        'High': 'max',
        'Low': 'min',
        'Close': 'last',
        'Volume': 'sum'
    })
    
    monthly = monthly.dropna()
    monthly.reset_index(inplace=True)
    monthly['Date'] = monthly['Date'].dt.strftime('%d-%m-%Y')
    return monthly

def main():
    print("=" * 100)
    print(" " * 30 + "NSE HISTORICAL DATA DOWNLOADER")
    print("=" * 100)
    
    # Get user inputs
    print("\n📊 Enter the NSE Symbol/Index Name")
    print("Examples: RELIANCE, TCS, NIFTY 50, Nifty Bank, Nifty Smallcap 250")
    symbol = input("Symbol/Index: ").strip()
    
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
    
    while True:
        choice = input("Enter choice (1/2/3): ").strip()
        if choice in ['1', '2', '3']:
            timeframe = {'1': '1d', '2': '1w', '3': '1m'}[choice]
            break
        print("❌ Invalid choice! Please enter 1, 2, or 3")
    
    print("\n" + "=" * 100)
    print("DOWNLOAD SETTINGS")
    print("=" * 100)
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
            bhav_data = nse.bhav_copy_indices(date_str)
            
            if bhav_data is not None and not bhav_data.empty:
                # Search for the symbol/index
                # Try exact match first, then partial match
                index_data = bhav_data[bhav_data['Index Name'] == symbol]
                
                if index_data.empty:
                    # Try case-insensitive partial match
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
                    
                    if successful_downloads % 100 == 0:
                        print(f"   ✓ {successful_downloads} trading days downloaded")
                else:
                    holidays_skipped += 1
            else:
                holidays_skipped += 1
                
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
