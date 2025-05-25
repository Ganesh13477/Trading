import pandas as pd
import matplotlib.pyplot as plt

def update_daily_balance(df, index, balance, position, entry_price, quantity):
    row = df.iloc[index]
    price = row['close']
    if position == 1:
        net_worth = balance + quantity * price
    elif position == -1:
        net_worth = balance + quantity * (2 * entry_price - price)  # short position valuation
    else:
        net_worth = balance

    return {
        'date': row['date'],
        'balance': balance,
        'position': position,
        'entry_price': entry_price,
        'quantity': quantity,
        'net_worth': net_worth
    }

def record_trade(trade_logs, date, trade_type, price, quantity, pnl=0.0):
    trade = {
        'date': date,
        'type': trade_type,
        'price': price,
        'quantity': quantity,
        'pnl': pnl  # Always include pnl key
    }
    trade_logs.append(trade)

def save_logs(trade_df, daily_df, prefix='backtest'):
    trade_df.to_csv(f"{prefix}_trades.csv", index=False)
    daily_df.to_csv(f"{prefix}_daily.csv", index=False)

def max_drawdown(net_worths):
    peak = net_worths[0]
    max_dd = 0
    for x in net_worths:
        if x > peak:
            peak = x
        dd = (peak - x) / peak
        if dd > max_dd:
            max_dd = dd
    return max_dd

def plot(trade_df, daily_df):
    plt.figure(figsize=(12,6))
    plt.plot(pd.to_datetime(daily_df['date']), daily_df['net_worth'], label='Net Worth')
    plt.title("Backtest Net Worth Over Time")
    plt.xlabel("Date")
    plt.ylabel("Net Worth")
    plt.legend()
    plt.grid()
    plt.show()
