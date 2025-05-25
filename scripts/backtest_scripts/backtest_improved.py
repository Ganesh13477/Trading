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

# Calculate indicators fresh (in case not present or to ensure accuracy)
# MACD
macd_df = ta.macd(df['close'])
df['macd'] = macd_df['MACD_12_26_9']
# RSI
df['rsi'] = ta.rsi(df['close'])
# EMA 20 and EMA 50
df['ema_20'] = ta.ema(df['close'], length=20)
df['ema_50'] = ta.ema(df['close'], length=50)

# Drop rows with NaN values caused by indicator calculation
df.dropna(inplace=True)
df = df.sort_values(by='date').reset_index(drop=True)

print(f"Dataframe shape after cleaning: {df.shape}")

# Parameters
balance = 100000  # Starting capital in ₹
position = 0      # 0 = no position, 1 = holding
quantity = 100    # Number of units per trade
buy_price = 0
stop_loss_pct = 0.02   # 2% stop loss
take_profit_pct = 0.04 # 4% take profit

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

    # Calculate unrealized PnL
    unrealized_pnl = 0
    if position == 1:
        unrealized_pnl = (today['close'] - buy_price) * quantity

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

    # Trading signals based on indicators:
    # BUY conditions:
    # - MACD line > 0 (positive histogram)
    # - RSI < 30 (oversold)
    # - EMA20 > EMA50 (uptrend)
    buy_signal = (
        (today['macd'] > 0) and 
        (today['ema_20'] > today['ema_50']) and
        (position == 0)
    )

    # SELL conditions:
    # - MACD line < 0 or RSI > 70 (overbought)
    # - or price hits stop loss or take profit
    stop_loss_price = buy_price * (1 - stop_loss_pct)
    take_profit_price = buy_price * (1 + take_profit_pct)
    price_below_stop = today['close'] < stop_loss_price
    price_above_tp = today['close'] > take_profit_price
    sell_signal = (
        (position == 1) and (
            (today['macd'] < 0) or
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
        sell_price = tomorrow['close']  # sell at next day's close for realism
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
if position == 1:
    unrealized_pnl = (last_day['close'] - buy_price) * quantity
else:
    unrealized_pnl = 0
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

# Convert logs to DataFrame
trade_df = pd.DataFrame(trade_logs)
daily_balance_df = pd.DataFrame(daily_balances)

# Calculate performance metrics
total_return = ((net_worth - 100000) / 100000) * 100
if not trade_df.empty and 'action' in trade_df.columns:
    sell_trades = trade_df[trade_df['action'] == 'SELL'].copy()
    wins = sell_trades[sell_trades['pnl'] > 0].shape[0]
    losses = sell_trades[sell_trades['pnl'] <= 0].shape[0]
    win_rate = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0
else:
    wins = losses = 0
    win_rate = 0

max_dd = max_drawdown(daily_balance_df['net_worth'].tolist()) * 100

print(f"\n=== Performance Summary ===")
print(f"Total Return: {total_return:.2f}%")
print(f"Number of Trades: {len(trade_df)}")
print(f"Winning Trades: {wins}")
print(f"Losing Trades: {losses}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Max Drawdown: {max_dd:.2f}%")
print(f"Ending Net Worth: ₹{net_worth:.2f}")


# Save CSV logs
logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(logs_dir, exist_ok=True)

trade_file = os.path.join(logs_dir, "trade_log_improved.csv")
daily_file = os.path.join(logs_dir, "daily_balance_improved.csv")

trade_df.to_csv(trade_file, index=False)
daily_balance_df.to_csv(daily_file, index=False)

print(f"Trade log saved to {trade_file}")
print(f"Daily balance saved to {daily_file}")

# Plot equity curve
plt.figure(figsize=(12,6))
plt.plot(daily_balance_df['date'], daily_balance_df['net_worth'], label='Equity Curve', color='blue')
plt.title('Equity Curve (Net Worth Over Time)')
plt.xlabel('Date')
plt.ylabel('Net Worth (₹)')
plt.grid(True)
plt.legend()

# Mark buy and sell trades on the equity curve
for _, row in trade_df.iterrows():
    try:
        net_worth_val = daily_balance_df.loc[daily_balance_df['date'] == row['date'], 'net_worth'].values[0]
        if row['action'] == 'BUY':
            plt.scatter(row['date'], net_worth_val, color='green', marker='^', s=100)
        else:
            plt.scatter(row['date'], net_worth_val, color='red', marker='v', s=100)
    except IndexError:
        # If date not found in daily_balance_df, skip plotting that point
        continue

plt.tight_layout()
plt.show()
