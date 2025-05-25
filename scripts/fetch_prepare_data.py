from kiteconnect import KiteConnect
import pandas as pd
import pandas_ta as ta
import datetime
import os
import time

# --- Zerodha Credentials ---
API_KEY = "wzpxu24i12m84kgp"
API_SECRET = "unh0zs6j2r2uqhf2fdogowrxz1vga014"
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "access_token.txt")

# --- Load Access Token ---
with open(TOKEN_PATH, "r") as f:
    ACCESS_TOKEN = f.read().strip()

# --- Connect to Kite ---
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# --- Function to Fetch Data in 30-Day Chunks ---
def fetch_zerodha_historical_data(instrument_token, from_date, to_date, interval="5minute"):
    print(f"Fetching data from {from_date} to {to_date}...")

    all_data = []
    current_start = from_date
    while current_start < to_date:
        current_end = min(current_start + datetime.timedelta(days=29), to_date)
        print(f"  → Fetching: {current_start} to {current_end}")
        try:
            data = kite.historical_data(instrument_token, current_start, current_end, interval)
            all_data.extend(data)
            time.sleep(1)  # to avoid rate limit
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
    
    # Simple target: 1 if next close is higher else 0
    df['target'] = (df['Close'].shift(-1) > df['Close']).astype(int)

    df.dropna(inplace=True)
    return df

# --- Main Run Block ---
if __name__ == "__main__":
    instrument_token = 256265  # Example: NIFTYBEES token
    to_date = datetime.date.today()
    from_date = to_date - datetime.timedelta(days=90)  # 3 months

    df = fetch_zerodha_historical_data(instrument_token, from_date, to_date)

    if df is not None:
        df_prepared = prepare_data(df)
        os.makedirs("data", exist_ok=True)
        df_prepared.to_csv("data/niftybees_zerodha_prepared_2.csv", index=False)
        print("✅ Data saved to data/niftybees_zerodha_prepared_2.csv")
    else:
        print("❌ Failed to fetch or prepare data.")
