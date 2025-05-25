import pandas as pd
import os
import matplotlib.pyplot as plt
import pandas_ta as ta

print("Starting full improved backtest...")

# Path to your prepared CSV file
data_path = os.path.join(os.path.dirname(__file__), "..", "data", "niftybees_zerodha_prepared_2.csv")

# Load data
df = pd.read_csv(data_path)
print("Loaded CSV columns:", df.columns.tolist())

# Remove duplicate columns like uppercase 'Close' if 'close' also exists
if 'close' in df.columns and 'Close' in df.columns:
    print("Dropping duplicate 'Close' column")
    df.drop(columns=['Close'], inplace=True)

# Normalize columns to lowercase
df.columns = df.columns.str.strip().str.lower()
print("Normalized columns:", df.columns.tolist())

# Convert date column to datetime
df['date'] = pd.to_datetime(df['date'])

# Convert price and indicator columns to numeric safely
for col in ['open', 'high', 'low', 'close', 'volume']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Calculate indicators fresh
macd_df = ta.macd(df['close'])
df['macd'] = macd_df['MACD_12_26_9']
df['rsi'] = ta.rsi(df['close'])
df['ema_20'] = ta.ema(df['close'], length=20)
df['ema_50'] = ta.ema(df['close'], length=50)

# Drop rows with NaN values caused by indicator calculation
df.dropna(inplace=True)
df = df.sort_values(by='date').reset_index(drop=True)

print(f"Dataframe shape after cleaning: {df.shape}")

# Parameters
balance = 100000
position = 0
quantity = 100
buy_price = 0
stop_loss_pct = 0.02
take_profit_pct = 0.04

trade_logs = []
daily_balances = []

def max_drawdown(equity_curve):
    peak = equity_curve[0]
    max_dd = 0
    for x in equity_curve:
        if x > peak:
            peak = x
        dd = (peak - x) / peak
        if dd > max_dd:
            max_dd = dd
    return max_dd

for i in range(len(df) - 1):
    today = df.loc[i]
    tomorrow = df.loc[i + 1]

    unrealized_pnl = (today['close'] - buy_price) * quantity if position == 1 else 0
    net_worth = balance + unrealized_pnl

    daily_balances.append({
        'date': today['date'],
        'balance': balance,
        'position': position,
        'buy_price': buy_price if position == 1 else None,
        'close_price': today['close'],
        'unrealized_pnl': unrealized_pnl,
        'net_worth': net_worth
    })

    buy_signal = (
        (today['macd'] > 0) and 
        (today['ema_20'] > today['ema_50']) and
        (position == 0)
    )

    stop_loss_price = buy_price * (1 - stop_loss_pct)
    take_profit_price = buy_price * (1 + take_profit_pct)
    price_below_stop = today['close'] < stop_loss_price
    price_above_tp = today['close'] > take_profit_price

    # NEW SELL LOGIC
    sell_signal = (
        (position == 1) and (
            (today['ema_20'] < today['ema_50']) or
            price_below_stop or
            price_above_tp
        )
    )

    if buy_signal:
        buy_price = today['close']
        position = 1
        trade_logs.append({
            'date': today['date'],
            'action': 'BUY',
            'price': buy_price,
            'quantity': quantity,
            'pnl': None
        })

    elif sell_signal:
        sell_price = tomorrow['close']
        pnl = (sell_price - buy_price) * quantity
        balance += pnl
        position = 0
        trade_logs.append({
            'date': tomorrow['date'],
            'action': 'SELL',
            'price': sell_price,
            'quantity': quantity,
            'pnl': pnl
        })

# Append last day info
last_day = df.iloc[-1]
unrealized_pnl = (last_day['close'] - buy_price) * quantity if position == 1 else 0
net_worth = balance + unrealized_pnl

daily_balances.append({
    'date': last_day['date'],
    'balance': balance,
    'position': position,
    'buy_price': buy_price if position == 1 else None,
    'close_price': last_day['close'],
    'unrealized_pnl': unrealized_pnl,
    'net_worth': net_worth
})

# DataFrames
trade_df = pd.DataFrame(trade_logs)
daily_balance_df = pd.DataFrame(daily_balances)

# Performance metrics
total_return = ((net_worth - 100000) / 100000) * 100
if not trade_df.empty and 'action' in trade_df.columns:
    sell_trades = trade_df[trade_df['action'] == 'SELL']
    wins = sell_trades[sell_trades['pnl'] > 0].shape[0]
    losses = sell_trades[sell_trades['pnl'] <= 0].shape[0]
    win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
else:
    wins = losses = win_rate = 0

max_dd = max_drawdown(daily_balance_df['net_worth'].tolist()) * 100

print(f"\n=== Performance Summary ===")
print(f"Total Return: {total_return:.2f}%")
print(f"Number of Trades: {len(trade_df)}")
print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Max Drawdown: {max_dd:.2f}%")
print(f"Ending Net Worth: ₹{net_worth:.2f}")

# Save logs
logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(logs_dir, exist_ok=True)
trade_df.to_csv(os.path.join(logs_dir, "trade_log_improved_1.csv"), index=False)
daily_balance_df.to_csv(os.path.join(logs_dir, "daily_balance_improved_1.csv"), index=False)

# Plot equity curve
plt.figure(figsize=(12,6))
plt.plot(daily_balance_df['date'], daily_balance_df['net_worth'], label='Equity Curve', color='blue')
plt.title('Equity Curve (Net Worth Over Time)')
plt.xlabel('Date')
plt.ylabel('Net Worth (₹)')
plt.grid(True)
plt.legend()

# Plot trades
for _, row in trade_df.iterrows():
    try:
        net_worth_val = daily_balance_df.loc[daily_balance_df['date'] == row['date'], 'net_worth'].values[0]
        color = 'green' if row['action'] == 'BUY' else 'red'
        marker = '^' if row['action'] == 'BUY' else 'v'
        plt.scatter(row['date'], net_worth_val, color=color, marker=marker, s=100)
    except IndexError:
        continue

plt.tight_layout()
plt.show()

#=== Performance Summary ===
#Total Return: 219.70%
#Number of Trades: 79
#Winning Trades: 12
#Losing Trades: 27
#Win Rate: 30.77%
#Max Drawdown: 45.78%
#Ending Net Worth: ₹319700.00

#✅ High Return: 3x the capital is impressive.

#⚠️ Low Win Rate: Many losing trades — indicates high volatility or wide stops.

#⚠️ High Drawdown: 45.78% is risky for real capital; drawdown limits should be tightened before live trading.
