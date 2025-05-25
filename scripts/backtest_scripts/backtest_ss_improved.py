"""
Backtest script for improved short selling strategy with Bollinger Bands, ADX, ATR SL/TP.
Loads historical data, runs signals, executes trades, calculates performance, and plots results.
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

from utils.indicators import add_indicators
from utils.signals import generate_signals
from utils.backtest_helpers import max_drawdown, update_daily_balance, record_trade,save_logs,plot

print("Starting full improved backtest with shorting, BB, ADX, ATR SL/TP...")

# Load CSV
data_path = os.path.join(os.path.dirname(__file__), "..", "data", "niftybees_zerodha_prepared_2.csv")
df = pd.read_csv(data_path)

# Clean columns
if 'close' in df.columns and 'Close' in df.columns:
    print("Dropping duplicate 'Close' column")
    df.drop(columns=['Close'], inplace=True)
df.columns = df.columns.str.strip().str.lower()
print("Normalized columns:", df.columns.tolist())

# Convert and ensure numeric
df['date'] = pd.to_datetime(df['date'])
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = pd.to_numeric(df[col], errors='coerce')


# Add indicators
df = add_indicators(df)
df = df.sort_values(by='date').dropna().reset_index(drop=True)
# Initialize backtest state
balance = 100000
position = 0   # 0 = no position, 1 = long, -1 = short
buy_price = 0
quantity = 100
trade_logs = []
daily_balances = []

# Backtest loop
for i in range(len(df) - 1):
    today = df.loc[i]
    tomorrow = df.loc[i + 1]

    daily_balances.append(update_daily_balance(df, i, balance, position, buy_price, quantity))

    signal = generate_signals(today, position, buy_price)

    if signal == 'BUY':
        buy_price = today['close']
        position = 1
        record_trade(trade_logs, today['date'], 'BUY', buy_price, quantity)

    elif signal == 'SELL':
        sell_price = tomorrow['close']
        pnl = (sell_price - buy_price) * quantity
        balance += pnl
        position = 0
        record_trade(trade_logs, tomorrow['date'], 'SELL', sell_price, quantity, pnl)

    elif signal == 'SHORT':
        buy_price = today['close']
        position = -1
        record_trade(trade_logs, today['date'], 'SHORT', buy_price, quantity)

    elif signal == 'COVER':
        cover_price = tomorrow['close']
        pnl = (buy_price - cover_price) * quantity
        balance += pnl
        position = 0
        record_trade(trade_logs, tomorrow['date'], 'COVER', cover_price, quantity, pnl)

# Final record
last = df.iloc[-1]
daily_balances.append(update_daily_balance(df, len(df) - 1, balance, position, buy_price, quantity))

# Results
trade_df = pd.DataFrame(trade_logs)
daily_df = pd.DataFrame(daily_balances)
net_worth = daily_df.iloc[-1]['net_worth']
total_return = ((net_worth - 100000) / 100000) * 100
max_dd = max_drawdown(daily_df['net_worth'].tolist()) * 100

# Summary
wins = trade_df[(trade_df['action'].isin(['SELL', 'COVER'])) & (trade_df['pnl'] > 0)].shape[0]
losses = trade_df[(trade_df['action'].isin(['SELL', 'COVER'])) & (trade_df['pnl'] <= 0)].shape[0]
win_rate = (wins / (wins + losses) * 100) if (wins + losses) else 0

print("\n=== Performance Summary ===")
print(f"Total Return: {total_return:.2f}%")
print(f"Number of Trades: {len(trade_df)}")
print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Max Drawdown: {max_dd:.2f}%")
print(f"Ending Net Worth: ₹{net_worth:.2f}")

# Save logs
save_logs(trade_df,daily_df)

# Plot equity curve
plot(trade_df,daily_df)
