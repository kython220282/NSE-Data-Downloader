"""
Streamlit Frontend for NSE Historical Data Downloader
Interactive web interface to download NSE stocks, indices, and ETF data
"""

import streamlit as st
import NseUtility
import pandas as pd
from datetime import datetime, timedelta
import time
import io

# Page configuration
st.set_page_config(
    page_title="NSE Data Downloader",
    page_icon="📊",
    layout="wide"
)

def normalize_index_name(name):
    """
    Normalize index name to match NSE naming convention.
    NSE uses 'NIFTY' in all caps, but rest varies (e.g., 'NIFTY Midcap 100').
    """
    if not name:
        return name
    
    # Common index name patterns in NSE
    replacements = {
        'nifty': 'NIFTY',
        'sensex': 'SENSEX',
        'bankex': 'BANKEX',
    }
    
    # Split and process each word
    words = name.split()
    normalized_words = []
    
    for word in words:
        word_lower = word.lower()
        # Check if it's a known prefix that should be uppercase
        if word_lower in replacements:
            normalized_words.append(replacements[word_lower])
        else:
            # Keep original casing for other words
            normalized_words.append(word)
    
    return ' '.join(normalized_words)

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

def download_stock_data(symbol, from_date_obj, to_date_obj, progress_bar, status_text):
    """Download stock data from equity bhav copy."""
    nse = NseUtility.NseUtils()
    all_data = []
    successful_downloads = 0
    current_date = from_date_obj
    total_days = (to_date_obj - from_date_obj).days
    errors = []
    
    while current_date <= to_date_obj:
        date_str = current_date.strftime('%d-%m-%Y')
        progress = (current_date - from_date_obj).days / total_days
        progress_bar.progress(progress)
        status_text.text(f"Downloading... {date_str} ({successful_downloads} records)")
        
        try:
            bhav_data = nse.bhav_copy_with_delivery(date_str)
            
            if bhav_data is not None and not bhav_data.empty:
                stock_data = bhav_data[bhav_data['SYMBOL'] == symbol.upper()]
                
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
        except Exception as e:
            if len(errors) < 3:  # Store first 3 errors for diagnostics
                errors.append(f"{date_str}: {str(e)}")
        
        current_date += timedelta(days=1)
        if successful_downloads % 5 == 0:
            time.sleep(0.1)
    
    if errors and successful_downloads == 0:
        st.warning(f"⚠️ Sample errors: {errors[0]}")
    
    return pd.DataFrame(all_data) if all_data else None

def download_index_data(symbol, from_date_obj, to_date_obj, progress_bar, status_text):
    """Download index data from indices bhav copy."""
    nse = NseUtility.NseUtils()
    all_data = []
    successful_downloads = 0
    current_date = from_date_obj
    total_days = (to_date_obj - from_date_obj).days
    errors = []
    
    # Normalize the symbol to match NSE naming conventions
    normalized_symbol = normalize_index_name(symbol)
    
    while current_date <= to_date_obj:
        date_str = current_date.strftime('%d-%m-%Y')
        progress = (current_date - from_date_obj).days / total_days
        progress_bar.progress(progress)
        status_text.text(f"Downloading... {date_str} ({successful_downloads} records)")
        
        try:
            bhav_data = nse.bhav_copy_indices(date_str)
            
            if bhav_data is not None and not bhav_data.empty:
                # Try exact match first with normalized name
                index_data = bhav_data[bhav_data['Index Name'] == normalized_symbol]
                
                # If not found, try case-insensitive partial match
                if index_data.empty:
                    index_data = bhav_data[bhav_data['Index Name'].str.contains(normalized_symbol, case=False, na=False)]
                
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
        except Exception as e:
            if len(errors) < 3:  # Store first 3 errors for diagnostics
                errors.append(f"{date_str}: {str(e)}")
        
        current_date += timedelta(days=1)
        if successful_downloads % 5 == 0:
            time.sleep(0.1)
    
    if errors and successful_downloads == 0:
        st.warning(f"⚠️ Sample errors: {errors[0]}")
    
    return pd.DataFrame(all_data) if all_data else None

# App title and description
st.title("📊 NSE Historical Data Downloader")
st.markdown("Download historical OHLC data for NSE stocks, indices, and ETFs")
st.markdown("Application support for daily, weekly, monthly, quarterly, and yearly data frequencies")

# Create two columns for layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Input Parameters")
    
    # Instrument type selection
    instrument_type = st.radio(
        "Select Instrument Type:",
        ["Index", "Stock/ETF"],
        help="Choose whether to download Index or Stock/ETF data"
    )
    
    # Symbol input with examples
    if instrument_type == "Index":
        st.info("💡 Examples: NIFTY 50, Nifty Bank, Nifty Midcap 150, Nifty Smallcap 250, NIFTY IT")
        symbol = st.text_input(
            "Index Name:",
            placeholder="e.g., NIFTY 50",
            help="Enter the index name (auto-normalized for NSE format)"
        )
        # Show normalized name if user entered something
        if symbol:
            normalized = normalize_index_name(symbol)
            if normalized != symbol:
                st.caption(f"🔄 Will search for: **{normalized}**")
    else:
        st.info("💡 Stocks: RELIANCE, TCS, INFY | ETFs: NIFTYBEES, BANKBEES")
        symbol = st.text_input(
            "Stock/ETF Symbol:",
            placeholder="e.g., RELIANCE",
            help="Enter stock symbol in uppercase"
        ).upper()
    
    # Date inputs
    st.markdown("#### 📅 Date Range")
    col_from, col_to = st.columns(2)
    
    with col_from:
        from_date = st.date_input(
            "From Date:",
            value=datetime.now() - timedelta(days=365),
            max_value=datetime.now()
        )
    
    with col_to:
        to_date = st.date_input(
            "To Date:",
            value=datetime.now(),
            max_value=datetime.now()
        )
    
    # Timeframe selection
    st.markdown("#### ⏱️ Timeframe")
    timeframe = st.selectbox(
        "Select Timeframe:",
        ["1d (Daily)", "1w (Weekly)", "1m (Monthly)", "1q (Quarterly)", "1y (Yearly)"],
        help="Choose data frequency"
    )
    timeframe_code = timeframe.split()[0]
    download_button = st.button("Download Data", type="primary", width="content")

with col2:
    st.subheader("📋 Download Settings")
    
    # Display current settings
    st.markdown("**Selected Parameters:**")
    st.write(f"- **Type:** {instrument_type}")
    
    # Show normalized symbol for indices
    if instrument_type == "Index" and symbol:
        display_symbol = normalize_index_name(symbol)
        st.write(f"- **Symbol:** {display_symbol}")
    else:
        st.write(f"- **Symbol:** {symbol if symbol else 'Not entered'}")
    
    st.write(f"- **From Date:** {from_date.strftime('%d-%m-%Y')}")
    st.write(f"- **To Date:** {to_date.strftime('%d-%m-%Y')}")
    st.write(f"- **Timeframe:** {timeframe_code}")
    
    # Calculate estimated records
    days_diff = (to_date - from_date).days
    estimated_records = int(days_diff * 0.7)  # Approx 70% are trading days
    
    if timeframe_code == '1w':
        estimated_records = estimated_records // 5
    elif timeframe_code == '1m':
        estimated_records = estimated_records // 20
    elif timeframe_code == '1q':
        estimated_records = estimated_records // 60
    elif timeframe_code == '1y':
        estimated_records = estimated_records // 240
    
    st.info(f"📊 Estimated records: ~{estimated_records}")
    st.markdown("---")
    st.write("⚠️ Note: Download time may vary based on date range and NSE server response.")


# Session state to store data
if 'downloaded_data' not in st.session_state:
    st.session_state.downloaded_data = None
if 'filename' not in st.session_state:
    st.session_state.filename = None

# Download process
if download_button:
    if not symbol:
        st.error("❌ Please enter a symbol/index name")
    elif to_date <= from_date:
        st.error("❌ 'To Date' must be after 'From Date'")
    else:
        st.markdown("---")
        st.subheader("⬇️ Downloading Data")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Download based on instrument type
            if instrument_type == "Index":
                df = download_index_data(symbol, from_date, to_date, progress_bar, status_text)
            else:
                df = download_stock_data(symbol, from_date, to_date, progress_bar, status_text)
            
            if df is not None and len(df) > 0:
                # Apply timeframe resampling
                if timeframe_code == '1w':
                    status_text.text("Resampling to weekly data...")
                    df = resample_to_weekly(df)
                elif timeframe_code == '1m':
                    status_text.text("Resampling to monthly data...")
                    df = resample_to_monthly(df)
                elif timeframe_code == '1q':
                    status_text.text("Resampling to quarterly data...")
                    df = resample_to_quarterly(df)
                elif timeframe_code == '1y':
                    status_text.text("Resampling to yearly data...")
                    df = resample_to_yearly(df)
                
                progress_bar.progress(1.0)
                status_text.text(f"✅ Complete! Downloaded {len(df)} records")
                
                # Store in session state
                st.session_state.downloaded_data = df
                actual_symbol = df['Symbol'].iloc[0].replace(' ', '_').replace('/', '_')
                st.session_state.filename = f"{actual_symbol}.csv"
                
                st.success(f"✅ Successfully downloaded {len(df)} records!")
                
            else:
                progress_bar.empty()
                status_text.empty()
                st.error("❌ No data found. Please check:")
                st.markdown("""
                - Symbol/Index name is correct
                - Date range includes trading days
                - NSE website is accessible
                """)
                
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Error: {str(e)}")

# Display and download results
if st.session_state.downloaded_data is not None:
    st.markdown("---")
    st.subheader("📊 Data Preview")
    
    df = st.session_state.downloaded_data
    
    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        #SYMBOL NAME
        st.metric("Symbol", df['Symbol'].iloc[0])
    with col2:
        st.metric("Total Records", len(df))
    with col3:
        st.metric("Highest", f"{df['Close'].max():.2f}")
    with col4:
        st.metric("Lowest", f"{df['Close'].min():.2f}")
        
    # Data table
    st.dataframe(df, width="stretch", height=300)
    
    # Download button
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_data = csv_buffer.getvalue()
    
    st.download_button(
        label="💾 Download CSV File",
        data=csv_data,
        file_name=st.session_state.filename,
        mime="text/csv",
        type="primary",
        width="stretch"
    )
    
    # Clear button
    if st.button("🔄 Start New Download", width="stretch"):
        st.session_state.downloaded_data = None
        st.session_state.filename = None
        st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>NSE Data Downloader | Powered by NseUtility | Data from NSE India</p>
    <p style='font-size: 0.8em;'>⚠️ For educational purposes only. Requires NSE approval for commercial use.</p>
</div>
""", unsafe_allow_html=True)
