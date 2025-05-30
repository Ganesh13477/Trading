from kiteconnect import KiteConnect
import pandas as pd
import pandas_ta as ta
import datetime
import os
import time

# --- Zerodha Credentials ---
API_KEY = "wzpxu24i12m84kgp"
API_SECRET = "unh0zs6j2r2uqhf2fdogowrxz1vga014"
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "access_token.txt")

# --- Load Access Token ---
with open(TOKEN_PATH, "r") as f:
    ACCESS_TOKEN = f.read().strip()

# --- Connect to Kite ---
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# --- Nifty 50 Token Map (NSE) ---
NIFTY_50_TOKENS = {
    "ADANIPORTS": 3861249,
    "ASIANPAINT": 60417,
    "AXISBANK": 1510401,
    "BAJAJ-AUTO": 4268801,
    "BAJFINANCE": 4267265,
    "BAJAJFINSV": 4268801,
    "BHARTIARTL": 2714625,
    "BPCL": 134657,
    "BRITANNIA": 140033,
    "CIPLA": 177665,
    "COALINDIA": 5215745,
    "DIVISLAB": 2800641,
    "DRREDDY": 225537,
    "EICHERMOT": 232961,
    "GRASIM": 315393,
    "HCLTECH": 1850625,
    "HDFCBANK": 341249,
    "HDFC": 340481,
    "HEROMOTOCO": 345089,
    "HINDALCO": 348929,
    "HINDUNILVR": 356865,
    "ICICIBANK": 1270529,
    "INDUSINDBK": 1346049,
    "INFY": 408065,
    "ITC": 424961,
    "JSWSTEEL": 3001089,
    "KOTAKBANK": 492033,
    "LT": 2939649,
    "M&M": 519937,
    "MARUTI": 2815745,
    "NESTLEIND": 784129,
    "NTPC": 2977281,
    "ONGC": 633601,
    "POWERGRID": 3834113,
    "RELIANCE": 738561,
    "SBILIFE": 5582849,
    "SBIN": 779521,
    "SHREECEM": 1131777,
    "SUNPHARMA": 857857,
    "TATACONSUM": 878593,
    "TATAMOTORS": 884737,
    "TATASTEEL": 895745,
    "TCS": 2953217,
    "TECHM": 3465729,
    "TITAN": 900609,
    "ULTRACEMCO": 2952193,
    "UPL": 2889473,
    "WIPRO": 969473,
    "HDFCLIFE": 4849665
}

# --- Function to Fetch Data in 30-Day Chunks ---
def fetch_zerodha_historical_data(instrument_token, from_date, to_date, interval="minute"):
    print(f"Fetching data from {from_date} to {to_date}...")

    all_data = []
    current_start = from_date
    while current_start < to_date:
        current_end = min(current_start + datetime.timedelta(days=29), to_date)
        print(f"  → Fetching: {current_start} to {current_end}")
        try:
            data = kite.historical_data(instrument_token, current_start, current_end, interval)
            all_data.extend(data)
            time.sleep(1)  # avoid rate limit
        except Exception as e:
            print("  ❌ Error fetching data:", e)

        current_start = current_end + datetime.timedelta(days=1)

    if not all_data:
        print("❌ No data received from any range.")
        return None

    return pd.DataFrame(all_data)

# --- Function to Add Indicators and Target Column ---
def prepare_data(df):
    df['Close'] = pd.to_numeric(df['close'])
    df['macd'] = ta.macd(df['Close'])['MACD_12_26_9']
    df['rsi'] = ta.rsi(df['Close'])
    df['ema_20'] = ta.ema(df['Close'], length=20)
    df['ema_50'] = ta.ema(df['Close'], length=50)
    df['target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    df.dropna(inplace=True)
    return df

# --- Main Block ---
if __name__ == "__main__":
    to_date = datetime.date.today()
    from_date = to_date - datetime.timedelta(days=5*365)

    os.makedirs("data", exist_ok=True)

    for symbol, token in NIFTY_50_TOKENS.items():
        print(f"\n🔄 Processing {symbol}...")
        try:
            df = fetch_zerodha_historical_data(token, from_date, to_date)
            if df is not None:
                df_prepared = prepare_data(df)
                file_path = f"data/{symbol.lower()}_5year_data.csv"
                df_prepared.to_csv(file_path, index=False)
                print(f"✅ Saved: {file_path}")
            else:
                print(f"❌ No data for {symbol}")
        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")
        time.sleep(1)  # Avoid hitting rate limits