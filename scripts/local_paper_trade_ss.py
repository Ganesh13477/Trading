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
position = 0      # 0 = no position, 1 = long, -1 = short
quantity = 0      # calculated dynamically
buy_price = 0
stop_loss_pct = 0.02
take_profit_pct = 0.04

# Logs
trade_logs = []

# Initialize Kite client
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# Fetch instrument token for RELIANCE
instruments = kite.instruments("NSE")
df_instr = pd.DataFrame(instruments)
reliance_token = df_instr[df_instr.tradingsymbol == "RELIANCE"]["instrument_token"].values[0]

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
    save_logs()  # Save immediately after every trade

def save_logs():
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    trade_file = os.path.join(logs_dir, "live_paper_trade_ss_log.csv")
    pd.DataFrame(trade_logs).to_csv(trade_file, index=False)

def calculate_quantity(price):
    global balance
    qty = balance // price  # Floor division for whole quantity
    return int(qty) if qty > 0 else 0

def main_loop():
    global balance, position, buy_price, quantity

    print("Starting live paper trading with short selling support...")

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

        # Calculate quantity based on current balance and price
        quantity = calculate_quantity(current_price)

        if quantity == 0:
            print("Insufficient balance to buy any quantity at current price.")
            time.sleep(300)
            continue

        unrealized_pnl = 0
        if position == 1:
            unrealized_pnl = (current_price - buy_price) * quantity
        elif position == -1:
            unrealized_pnl = (buy_price - current_price) * quantity
        net_worth = balance + unrealized_pnl

        # Trading signals
        buy_signal = position == 0 and today['macd'] > 0 and today['ema_20'] > today['ema_50']
        sell_signal = position == 1 and (today['macd'] < 0 or current_price < buy_price * (1 - stop_loss_pct) or current_price > buy_price * (1 + take_profit_pct))
        short_signal = position == 0 and today['macd'] < 0 and today['ema_20'] < today['ema_50']
        cover_signal = position == -1 and (today['macd'] > 0 or current_price > buy_price * (1 + stop_loss_pct) or current_price < buy_price * (1 - take_profit_pct))

        now = datetime.now()

        # Execute trades based on signals
        if buy_signal:
            buy_price = current_price
            position = 1
            log_trade("BUY", buy_price, quantity, now.strftime("%Y-%m-%d %H:%M:%S"))
        elif sell_signal:
            sell_price = current_price
            pnl = (sell_price - buy_price) * quantity
            balance += pnl
            position = 0
            log_trade("SELL", sell_price, quantity, now.strftime("%Y-%m-%d %H:%M:%S"), pnl)
        elif short_signal:
            buy_price = current_price
            position = -1
            log_trade("SHORT SELL", buy_price, quantity, now.strftime("%Y-%m-%d %H:%M:%S"))
        elif cover_signal:
            cover_price = current_price
            pnl = (buy_price - cover_price) * quantity
            balance += pnl
            position = 0
            log_trade("BUY TO COVER", cover_price, quantity, now.strftime("%Y-%m-%d %H:%M:%S"), pnl)

        print(f"{now.strftime('%H:%M:%S')} | Net Worth: ₹{net_worth:.2f} | Balance: ₹{balance:.2f} | Position: {position}")
        time.sleep(300)  # wait 5 minutes for next candle

    # Market closed
    print("Market closed. Exiting live paper trading.")

if __name__ == "__main__":
    main_loop()
