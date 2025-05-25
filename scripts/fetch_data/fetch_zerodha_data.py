from kiteconnect import KiteConnect
import pandas as pd
import datetime
import os
import time

API_KEY = "wzpxu24i12m84kgp"
API_SECRET = "unh0zs6j2r2uqhf2fdogowrxz1vga014"
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "access_token.txt")

# Load access token
with open(TOKEN_PATH, "r") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

def fetch_data_range(instrument_token, from_date, to_date, interval="5minute"):
    data = []
    current_from = from_date
    while current_from < to_date:
        current_to = current_from + datetime.timedelta(days=30)
        if current_to > to_date:
            current_to = to_date
        print(f"Fetching {current_from} to {current_to}")
        try:
            chunk = kite.historical_data(instrument_token, current_from, current_to, interval)
            data.extend(chunk)
            time.sleep(1)  # avoid rate limits
        except Exception as e:
            print("Error fetching data:", e)
        current_from = current_to + datetime.timedelta(days=1)
    return pd.DataFrame(data)

if __name__ == "__main__":
    instrument_token = 256265  # Replace with actual token (e.g., NIFTYBEES)
    to_date = datetime.date.today()
    from_date = to_date - datetime.timedelta(days=90)  # 3 months back

    df = fetch_data_range(instrument_token, from_date, to_date, interval="5minute")
    if not df.empty:
        df.to_csv("data/niftybees_3months.csv", index=False)
        print("✅ Data saved to data/niftybees_3months.csv")
    else:
        print("❌ No data fetched.")
