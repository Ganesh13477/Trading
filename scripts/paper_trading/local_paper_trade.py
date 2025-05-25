import os
import time
import pandas as pd
import pandas_ta as ta
from kiteconnect import KiteConnect
from datetime import datetime, time as dt_time, timedelta

API_KEY = "wzpxu24i12m84kgp"
API_SECRET = "unh0zs6j2r2uqhf2fdogowrxz1vga014"
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "..", "access_token.txt")

# Load access token
with open(TOKEN_PATH, "r") as f:
    ACCESS_TOKEN = f.read().strip()

# Instrument token for NIFTYBEES (replace with actual token)
NIFTYBEES_TOKEN = 260105  # example token, confirm with Zerodha instruments

# Initial capital and trade params
balance = 100000
position = 0
quantity = 100
buy_price = 0
stop_loss_pct = 0.02
take_profit_pct = 0.04

# Logs
trade_logs = []
daily_balances = []

# Initialize Kite client
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

def is_market_open():
    now = datetime.now().time()
    # NSE market hours approx: 09:15 to 15:30
    return dt_time(9, 15) <= now <= dt_time(15, 30)

def fetch_live_candles(token, interval="5minute", min_candles=50):
    """
    Fetches historical candle data going back enough days to get at least min_candles candles.
    Returns a DataFrame with candles sorted by date.
    """
    # Calculate how many days back to fetch approx (5-min candles per day ~ 78)
    days_back = max(1, (min_candles // 78) + 1)  # 78 = ~ number of 5-min candles in one NSE day

    from_date = datetime.now().date() - timedelta(days=days_back)
    to_date = datetime.now().date()

    data = kite.historical_data(token, from_date=from_date, to_date=to_date, interval=interval)
    df = pd.DataFrame(data)
    if df.empty:
        return None

    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date').reset_index(drop=True)

    # Keep only the last min_candles candles for safety
    if len(df) > min_candles:
        df = df.iloc[-min_candles:].reset_index(drop=True)

    return df

def calculate_indicators(df):
    macd_df = ta.macd(df['close'])
    if macd_df is None or macd_df.empty:
        raise ValueError("MACD calculation failed due to insufficient data")
    df['macd'] = macd_df['MACD_12_26_9']
    df['rsi'] = ta.rsi(df['close'])
    df['ema_20'] = ta.ema(df['close'], length=20)
    df['ema_50'] = ta.ema(df['close'], length=50)
    df.dropna(inplace=True)
    return df

def log_trade(action, price, qty, date, pnl=None):
    trade_logs.append({
        'date': date,
        'action': action,
        'price': price,
        'quantity': qty,
        'pnl': pnl
    })
    print(f"{date} | {action} at ₹{price:.2f} qty={qty} pnl={pnl}")

def save_logs():
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    trade_file = os.path.join(logs_dir, "live_paper_trade_log.csv")
    pd.DataFrame(trade_logs).to_csv(trade_file, index=False)
    print(f"Trade log saved to {trade_file}")

def main_loop():
    global balance, position, buy_price

    print("Starting live paper trading...")

    while is_market_open():
        try:
            df = fetch_live_candles(NIFTYBEES_TOKEN, min_candles=50)
            if df is None or df.empty or len(df) < 40:
                print(f"Waiting for enough data: currently {0 if df is None else len(df)} candles, need ~40")
                time.sleep(300)
                continue

            df = calculate_indicators(df)
        except Exception as e:
            print(f"Indicator calculation error: {e}")
            time.sleep(300)
            continue

        today = df.iloc[-1]

        unrealized_pnl = 0
        if position == 1:
            unrealized_pnl = (today['close'] - buy_price) * quantity
        net_worth = balance + unrealized_pnl

        # Trading signals
        buy_signal = (
            position == 0 and
            today['macd'] > 0 and
            today['ema_20'] > today['ema_50']
        )
        stop_loss_price = buy_price * (1 - stop_loss_pct)
        take_profit_price = buy_price * (1 + take_profit_pct)
        price_below_stop = today['close'] < stop_loss_price if position == 1 else False
        price_above_tp = today['close'] > take_profit_price if position == 1 else False

        sell_signal = (
            position == 1 and (
                today['macd'] < 0 or
                price_below_stop or
                price_above_tp
            )
        )

        now = datetime.now()

        if buy_signal:
            buy_price = today['close']
            position = 1
            log_trade("BUY", buy_price, quantity, now.strftime("%Y-%m-%d %H:%M:%S"))
        elif sell_signal:
            sell_price = today['close']
            pnl = (sell_price - buy_price) * quantity
            balance += pnl
            position = 0
            log_trade("SELL", sell_price, quantity, now.strftime("%Y-%m-%d %H:%M:%S"), pnl)

        print(f"{now.strftime('%H:%M:%S')} | Net Worth: ₹{net_worth:.2f} | Balance: ₹{balance:.2f} | Position: {position}")
        time.sleep(300)  # Wait 5 minutes for next candle

    # Market closed, save logs
    save_logs()
    print("Market closed. Exiting live paper trading.")

if __name__ == "__main__":
    main_loop()
