import pandas as pd
import os
from utils.indicators import add_indicators
from utils.signals import generate_signals
from utils.backtest_helpers import update_daily_balance, record_trade, save_logs, plot, max_drawdown

print("Starting improved backtest with realistic trade sizing, commissions, slippage, holding period and position sizing...")

# Load data
data_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "niftybees_zerodha_prepared_2.csv")
df = pd.read_csv(data_path)
print("Loaded CSV columns:", df.columns.tolist())
df.reset_index(drop=True, inplace=True)
df = add_indicators(df)

initial_balance = 100000
balance = initial_balance
position = 0
entry_price = 0
quantity = 0
cooldown = 0
cooldown_period = 3

trade_logs = []
daily_logs = []

holding_period = 0
risk_pct = 0.1  # Use 10% of balance per trade

for i in range(len(df)):
    today = df.iloc[i]
    date = today['date']

    signal = generate_signals(today, position, entry_price, cooldown, holding_period)
    cooldown = max(0, cooldown - 1)

    if signal == 'BUY' and position == 0:
        max_trade_value = balance * risk_pct
        quantity = int(max_trade_value // today['close'])
        if quantity > 0:
            entry_price = today['close']
            cost = entry_price * quantity * 1.001  # includes commission/slippage
            balance -= cost
            position = 1
            record_trade(trade_logs, date, 'BUY', entry_price, quantity)  # pnl defaults to 0.0 now
            cooldown = cooldown_period
            holding_period = 0

    elif signal == 'SHORT' and position == 0:
        max_trade_value = balance * risk_pct
        quantity = int(max_trade_value // today['close'])
        if quantity > 0:
            entry_price = today['close']
            # Assume margin/short proceeds added to balance (simplified)
            position = -1
            record_trade(trade_logs, date, 'SHORT', entry_price, quantity)  # pnl defaults to 0.0 now
            cooldown = cooldown_period
            holding_period = 0

    elif signal == 'SELL' and position == 1:
        exit_price = today['close']
        proceeds = exit_price * quantity * 0.999  # after commission/slippage
        balance += proceeds
        pnl = proceeds - (entry_price * quantity * 1.001)
        record_trade(trade_logs, date, 'SELL', exit_price, quantity, pnl)
        position = 0
        quantity = 0
        entry_price = 0
        cooldown = cooldown_period
        holding_period = 0

    elif signal == 'COVER' and position == -1:
        exit_price = today['close']
        pnl = (entry_price - exit_price) * quantity  # simplified PnL for short
        balance += pnl
        record_trade(trade_logs, date, 'COVER', exit_price, quantity, pnl)
        position = 0
        quantity = 0
        entry_price = 0
        cooldown = cooldown_period
        holding_period = 0

    else:
        if position != 0:
            holding_period += 1

    daily_record = update_daily_balance(df, i, balance, position, entry_price, quantity)
    daily_logs.append(daily_record)

# Create DataFrames
trade_df = pd.DataFrame(trade_logs)
daily_df = pd.DataFrame(daily_logs)

# Ensure 'pnl' column exists to avoid KeyError
if 'pnl' not in trade_df.columns:
    trade_df['pnl'] = 0.0

total_return = (balance - initial_balance) / initial_balance * 100
win_trades = trade_df[trade_df['pnl'] > 0]
lose_trades = trade_df[trade_df['pnl'] <= 0]
win_rate = len(win_trades) / len(trade_df) * 100 if len(trade_df) > 0 else 0
max_dd = max_drawdown(daily_df['net_worth'].tolist())

print(f"=== Performance Summary ===")
print(f"Total Return: {total_return:.2f}%")
print(f"Number of Trades: {len(trade_df)}")
print(f"Winning Trades: {len(win_trades)}")
print(f"Losing Trades: {len(lose_trades)}")
print(f"Win Rate: {win_rate:.2f}%")
print(f"Max Drawdown: {max_dd * 100:.2f}%")
print(f"Ending Net Worth: ₹{balance:.2f}")

save_logs(trade_df, daily_df, prefix='backtest_improved')
# plot(trade_df, daily_df)
