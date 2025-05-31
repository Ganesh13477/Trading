import os
import time
import datetime
import pandas as pd
import pandas_ta as ta
import requests
from kiteconnect import KiteConnect
from concurrent.futures import ThreadPoolExecutor, as_completed

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

# --- Small Cap Symbols (NSE Tradingsymbols) ---
SMALLCAP_SYMBOLS = [
    "ABCAPITAL", "ABFRL", "ADANIGREEN", "ADVENZYMES", "AFFLE", "AJANTPHARM", "ALKYLAMINE", "AMARAJABAT",
    "ANURAS", "APLAPOLLO", "ARVINDFASN", "ASTERDM", "ASTRAZEN", "ATUL", "BASF", "BAYERCROP", "BBTC",
    "BORORENEW", "CANFINHOME", "CAPLIPOINT", "CEATLTD", "CENTRALBK", "CENTURYPLY", "CERA", "COCHINSHIP",
    "CRAFTSMAN", "CREDITACC", "CYIENT", "DEEPAKNTR", "EIDPARRY", "ELGIEQUIP", "FDC", "FINCABLES",
    "FINOLEXIND", "FLUOROCHEM", "FSL", "GHCL", "GLENMARK", "GMDCLTD", "GNFC", "GRANULES", "GRAPHITE",
    "GREAVESCOT", "GRSE", "HEG", "HFCL", "HGINFRA", "IIFL", "IOLCP", "IRB", "IRCON", "ITDCEM", "JBCHEPHARM",
    "JYOTHYLAB", "KNRCON", "KPITTECH", "KRBL", "KSB", "LAURUSLABS", "LEMONTREE", "LUXIND", "MAHINDCIE",
    "MAHSCOOTER", "MARKSANS", "MAZDOCK", "METROPOLIS", "MSTCLTD", "NCC", "NIACL", "NIITLTD", "NLCINDIA",
    "NOCIL", "OLECTRA", "ORIENTCEM", "POLYMED", "PRSMJOHNSN", "PSB", "PTC", "RALLIS", "REDINGTON", "RENUKA",
    "ROUTE", "SAREGAMA", "SFL", "SHILPAMED", "SHOPERSTOP", "SIS", "SJVN", "SOLARA", "SPARC", "STLTECH",
    "TANLA", "TEAMLEASE", "THERMAX", "TIMKEN", "TRIDENT", "UCOBANK", "UJJIVANSFB", "VENKEYS", "VGUARD",
    "VIPIND", "VMART", "WELSPUNIND", "WESTLIFE"
]

# --- Get Instrument Tokens ---
def get_symbol_token_map(symbols):
    instrument_url = "https://api.kite.trade/instruments"
    response = requests.get(instrument_url)
    with open("instruments.csv", "wb") as f:
        f.write(response.content)

    instruments_df = pd.read_csv("instruments.csv")
    nse_df = instruments_df[(instruments_df["exchange"] == "NSE") & (instruments_df["segment"] == "NSE")]

    token_map = {}
    for symbol in symbols:
        try:
            token = nse_df[nse_df["tradingsymbol"] == symbol]["instrument_token"].values[0]
            token_map[symbol] = token
        except IndexError:
            print(f"❌ Token not found for {symbol}")
    return token_map

# --- Fetch Data ---
def fetch_zerodha_historical_data(instrument_token, from_date, to_date, interval="minute"):
    all_data = []
    current_start = from_date
    while current_start < to_date:
        current_end = min(current_start + datetime.timedelta(days=29), to_date)
        try:
            data = kite.historical_data(instrument_token, current_start, current_end, interval)
            all_data.extend(data)
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ Error: {e}")
        current_start = current_end + datetime.timedelta(days=1)
    return pd.DataFrame(all_data)

# --- Add Indicators ---
def prepare_data(df):
    df['Close'] = pd.to_numeric(df['close'])
    df['macd'] = ta.macd(df['Close'])['MACD_12_26_9']
    df['rsi'] = ta.rsi(df['Close'])
    df['ema_20'] = ta.ema(df['Close'], length=20)
    df['ema_50'] = ta.ema(df['Close'], length=50)
    df['target'] = (df['Close'].shift(-1) > df['Close']).astype(int)
    df.dropna(inplace=True)
    return df

# --- Threaded Process Function ---
def process_symbol(symbol, token, from_date, to_date):
    print(f"📅 {symbol}: Fetching data...")
    df = fetch_zerodha_historical_data(token, from_date, to_date)
    if df.empty:
        print(f"❌ {symbol}: No data fetched")
        return
    df = prepare_data(df)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),"..", "..", "..", "data", "small_cap_5_year"))
    os.makedirs(base_dir, exist_ok=True)
    filepath = os.path.join(base_dir, f"{symbol}_5year_data.csv")
    df.to_csv(filepath, index=False)
    print(f"✅ {symbol}: Data saved to {filepath}")

# --- Main Execution ---
if __name__ == "__main__":
    print("🔍 Getting token map for small-cap stocks...")
    token_map = get_symbol_token_map(SMALLCAP_SYMBOLS)

    to_date = datetime.date.today()
    from_date = to_date - datetime.timedelta(days=5*365)

    print("🚀 Starting threaded data fetch for all small-cap companies...")
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(process_symbol, sym, token, from_date, to_date) for sym, token in token_map.items()]
        for future in as_completed(futures):
            pass  # Logging is handled in the function

    print("🎉 All small-cap data fetching complete.")
