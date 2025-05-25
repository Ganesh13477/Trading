import pandas as pd
import os

print("Starting backtest...")

# Load data
data_path = os.path.join(os.path.dirname(__file__), "..", "data", "niftybees_3months.csv")
df = pd.read_csv(data_path)

# Normalize columns
df.columns = df.columns.str.strip().str.lower()

# Convert date column to datetime
df['date'] = pd.to_datetime(df['date'])

# Sort by date ascending
df = df.sort_values(by='date').reset_index(drop=True)

balance = 100000  # Starting capital
position = 0      # 0 means no position, 1 means holding stock
buy_price = 0

trade_logs = []   # Store trades info
daily_balances = []  # Store daily balance & position info

for i in range(len(df) - 1):
    today = df.loc[i]
    tomorrow = df.loc[i + 1]

    # Record daily balance and position
    if position == 1:
        # Calculate unrealized PnL for today using today's close
        unrealized_pnl = today['close'] - buy_price
    else:
        unrealized_pnl = 0

    net_worth = balance + (unrealized_pnl if position == 1 else 0)
    daily_balances.append({
        'date': today['date'],
        'balance': balance,
        'position': position,
        'buy_price': buy_price if position == 1 else None,
        'close_price': today['close'],
        'unrealized_pnl': unrealized_pnl,
        'net_worth': net_worth
    })

    # Trading logic:
    # Buy signal
    if today['close'] > today['open'] and position == 0:
        buy_price = today['close']
        position = 1
        trade_logs.append({
            'date': today['date'],
            'action': 'BUY',
            'price': buy_price,
            'pnl': None
        })

    # Sell signal
    elif today['close'] < today['open'] and position == 1:
        sell_price = tomorrow['close']  # sell next day's close price
        pnl = sell_price - buy_price
        balance += pnl
        position = 0
        trade_logs.append({
            'date': tomorrow['date'],
            'action': 'SELL',
            'price': sell_price,
            'pnl': pnl
        })

# Append last day info
last_day = df.iloc[-1]
if position == 1:
    unrealized_pnl = last_day['close'] - buy_price
else:
    unrealized_pnl = 0
net_worth = balance + (unrealized_pnl if position == 1 else 0)

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

# Save to CSV
trade_file = os.path.join(os.path.dirname(__file__), "..", "logs", "trade_log.csv")
daily_file = os.path.join(os.path.dirname(__file__), "..", "logs", "daily_balance.csv")

trade_df.to_csv(trade_file, index=False)
daily_balance_df.to_csv(daily_file, index=False)

print(f"Trades saved to {trade_file}")
print(f"Daily balance saved to {daily_file}")

print(f"\nFinal Balance: ₹{balance:.2f}")
if position == 1:
    print(f"Holding position at end. Buy price: ₹{buy_price}, Last close: ₹{last_day['close']}")

