import pandas as pd
import os
import matplotlib.pyplot as plt
import pandas_ta as ta

print("Starting full improved backtest with BB, ADX and dynamic SL...")

# Load CSV
data_path = os.path.join(os.path.dirname(__file__), "..", "data", "niftybees_zerodha_prepared_2.csv")
df = pd.read_csv(data_path)
print("Loaded CSV columns:", df.columns.tolist())

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

# Indicators
df['rsi'] = ta.rsi(df['close'])
df['ema_20'] = ta.ema(df['close'], length=20)
df['ema_50'] = ta.ema(df['close'], length=50)
df['macd'] = ta.macd(df['close'])['MACD_12_26_9']
bbands = ta.bbands(df['close'], length=20, std=2)
df['bb_upper'] = bbands['BBU_20_2.0']
df['bb_lower'] = bbands['BBL_20_2.0']
df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)

df.dropna(inplace=True)
df = df.sort_values(by='date').reset_index(drop=True)
print(f"Dataframe shape after cleaning: {df.shape}")

# Backtest vars
balance = 100000
position = 0
quantity = 100
buy_price = 0
trade_logs = []
daily_balances = []

def max_drawdown(equity):
    peak = equity[0]
    max_dd = 0
    for val in equity:
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        max_dd = max(max_dd, dd)
    return max_dd

for i in range(len(df) - 1):
    today = df.loc[i]
    tomorrow = df.loc[i + 1]

    unrealized_pnl = (today['close'] - buy_price) * quantity if position else 0
    net_worth = balance + unrealized_pnl

    daily_balances.append({
        'date': today['date'],
        'balance': balance,
        'position': position,
        'buy_price': buy_price if position else None,
        'close_price': today['close'],
        'unrealized_pnl': unrealized_pnl,
        'net_worth': net_worth
    })

    # ATR-based dynamic SL/TP
    dynamic_sl = today['atr'] * 1.5
    dynamic_tp = today['atr'] * 2.5
    stop_loss_price = buy_price - dynamic_sl if position else 0
    take_profit_price = buy_price + dynamic_tp if position else 0

    buy_signal = (
        today['macd'] > 0 and
        today['ema_20'] > today['ema_50'] and
        today['close'] > today['bb_upper'] and
        today['adx'] > 20 and
        position == 0
    )

    sell_signal = (
        position == 1 and (
            today['macd'] < 0 or
            today['close'] < stop_loss_price or
            today['close'] > take_profit_price or
            today['close'] < today['bb_lower'] or
            today['adx'] < 20
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

# Final day
last_day = df.iloc[-1]
unrealized_pnl = (last_day['close'] - buy_price) * quantity if position else 0
net_worth = balance + unrealized_pnl
daily_balances.append({
    'date': last_day['date'],
    'balance': balance,
    'position': position,
    'buy_price': buy_price if position else None,
    'close_price': last_day['close'],
    'unrealized_pnl': unrealized_pnl,
    'net_worth': net_worth
})

# Results
trade_df = pd.DataFrame(trade_logs)
daily_df = pd.DataFrame(daily_balances)
total_return = ((net_worth - 100000) / 100000) * 100

if not trade_df.empty and 'action' in trade_df.columns:
    sell_trades = trade_df[trade_df['action'] == 'SELL'].copy()
    wins = sell_trades[sell_trades['pnl'] > 0].shape[0]
    losses = sell_trades[sell_trades['pnl'] <= 0].shape[0]
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
else:
    wins = losses = win_rate = 0

max_dd = max_drawdown(daily_df['net_worth'].tolist()) * 100

print("\n=== Performance Summary ===")
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
trade_df.to_csv(os.path.join(logs_dir, "trade_log_bb_adx.csv"), index=False)
daily_df.to_csv(os.path.join(logs_dir, "daily_balance_bb_adx.csv"), index=False)
print("Logs saved.")

# Plot
plt.figure(figsize=(12, 6))
plt.plot(daily_df['date'], daily_df['net_worth'], label='Equity Curve', color='blue')
plt.title('Equity Curve (Net Worth Over Time)')
plt.xlabel('Date')
plt.ylabel('Net Worth (₹)')
plt.grid(True)
plt.legend()

for _, row in trade_df.iterrows():
    try:
        net_val = daily_df.loc[daily_df['date'] == row['date'], 'net_worth'].values[0]
        if row['action'] == 'BUY':
            plt.scatter(row['date'], net_val, color='green', marker='^', s=100)
        elif row['action'] == 'SELL':
            plt.scatter(row['date'], net_val, color='red', marker='v', s=100)
    except IndexError:
        continue

plt.tight_layout()
plt.show()
