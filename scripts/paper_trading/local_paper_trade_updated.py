import os
import time
import math
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

# Initial capital and trade params
balance = 100000
position = 0
buy_price = 0
stop_loss_pct = 0.02
take_profit_pct = 0.04

# Logs
trade_logs = []

# Initialize Kite client
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

instruments = kite.instruments("NSE")
df = pd.DataFrame(instruments)
reliance_token = df[df.tradingsymbol == "RELIANCE"]["instrument_token"].values[0]

def is_market_open():
    now = datetime.now().time()
    return dt_time(9, 15) <= now <= dt_time(15, 30)

def fetch_live_candles(token, interval="5minute", min_candles=50):
    days_back = max(1, (min_candles // 78) + 1)
    from_date = datetime.now().date() - timedelta(days=days_back)
    to_date = datetime.now().date()
    data = kite.historical_data(token, from_date=from_date, to_date=to_date, interval=interval)
    df = pd.DataFrame(data)
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date').reset_index(drop=True)
    return df.tail(min_candles).reset_index(drop=True)

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

def save_logs():
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    trade_file = os.path.join(logs_dir, "live_paper_trade_updated_log.csv")
    df_new = pd.DataFrame(trade_logs)
    if os.path.exists(trade_file):
        df_old = pd.read_csv(trade_file)
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_combined = df_new
    df_combined.to_csv(trade_file, index=False)
    print(f"Trade log updated at {trade_file}")

def log_trade(action, price, qty, date, pnl=None):
    trade_logs.append({
        'date': date,
        'action': action,
        'price': price,
        'quantity': qty,
        'pnl': pnl
    })
    print(f"{date} | {action} at ₹{price:.2f} qty={qty} pnl={pnl}")
    save_logs()

def main_loop():
    global balance, position, buy_price

    print("Starting live paper trading...")

    while is_market_open():
        try:
            df = fetch_live_candles(reliance_token, min_candles=50)
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
        current_price = today['close']

        unrealized_pnl = 0
        if position == 1:
            unrealized_pnl = (current_price - buy_price) * quantity
        net_worth = balance + unrealized_pnl

        # Trading logic
        buy_signal = (
            position == 0 and
            today['macd'] > 0 and
            today['ema_20'] > today['ema_50']
        )
        stop_loss_price = buy_price * (1 - stop_loss_pct)
        take_profit_price = buy_price * (1 + take_profit_pct)
        price_below_stop = current_price < stop_loss_price if position == 1 else False
        price_above_tp = current_price > take_profit_price if position == 1 else False

        sell_signal = (
            position == 1 and (
                today['macd'] < 0 or
                price_below_stop or
                price_above_tp
            )
        )

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if buy_signal:
            quantity = int(balance // current_price)
            if quantity > 0:
                buy_price = current_price
                position = 1
                log_trade("BUY", buy_price, quantity, now)
            else:
                print(f"{now} | Not enough balance to buy | Price: ₹{current_price:.2f} | Balance: ₹{balance:.2f}")
        elif sell_signal:
            sell_price = current_price
            pnl = (sell_price - buy_price) * quantity
            balance += pnl
            position = 0
            log_trade("SELL", sell_price, quantity, now, pnl)

        print(f"{datetime.now().strftime('%H:%M:%S')} | Net Worth: ₹{net_worth:.2f} | Balance: ₹{balance:.2f} | Position: {position}")
        time.sleep(300)  # Wait 5 mins

    print("Market closed. Exiting live paper trading.")

if __name__ == "__main__":
    main_loop()
