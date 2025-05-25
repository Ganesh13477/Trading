from kiteconnect import KiteConnect
import pandas as pd
import pandas_ta as ta
import datetime
import os

API_KEY = "wzpxu24i12m84kgp"
API_SECRET = "unh0zs6j2r2uqhf2fdogowrxz1vga014"
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "access_token.txt")

# Load access token
with open(TOKEN_PATH, "r") as f:
    ACCESS_TOKEN = f.read().strip()

def fetch_zerodha_historical_data(instrument_token, from_date, to_date, interval="5minute"):
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)

    print(f"Fetching data for instrument_token {instrument_token} from {from_date} to {to_date}")

    try:
        data = kite.historical_data(instrument_token, from_date, to_date, interval)
        df = pd.DataFrame(data)
        if df.empty:
            print("No data returned from Zerodha API.")
            return None
        return df
    except Exception as e:
        print("Error fetching data:", e)
        return None

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

if __name__ == "__main__":
    # Example instrument token for NIFTYBEES (You must get the correct instrument_token from Zerodha's instruments API)
    instrument_token = 256265  # Replace with correct token

    # Define date range (max 5-7 days for 5min data from Zerodha usually)
    to_date = datetime.date.today()
    from_date = to_date - datetime.timedelta(days=7)

    df = fetch_zerodha_historical_data(instrument_token, from_date, to_date, interval="5minute")

    if df is not None:
        df_prepared = prepare_data(df)
        print(df_prepared.head())
        df_prepared.to_csv('data/niftybees_zerodha_prepared.csv', index=False)
        print("Data saved to niftybees_zerodha_prepared.csv")
    else:
        print("Failed to fetch or prepare data.")
