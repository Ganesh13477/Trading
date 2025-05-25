import os
import matplotlib.pyplot as plt
def max_drawdown(equity_curve):
    """
    Calculate the maximum drawdown from a list of equity values.
    """
    peak = equity_curve[0]
    max_dd = 0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak
        max_dd = max(max_dd, dd)
    return max_dd


def update_daily_balance(df, index, balance, position, buy_price, quantity):
    row = df.loc[index]
    unrealized_pnl = 0

    if position == 1:
        unrealized_pnl = (row['close'] - buy_price) * quantity
    elif position == -1:
        unrealized_pnl = (buy_price - row['close']) * quantity

    net_worth = balance + unrealized_pnl

    return {
        'date': row['date'],
        'balance': balance,
        'position': position,
        'buy_price': buy_price if position != 0 else None,
        'close_price': row['close'],
        'unrealized_pnl': unrealized_pnl,
        'net_worth': net_worth
    }


def record_trade(trade_logs, date, action, price, quantity, pnl=None):
    trade_logs.append({
        'date': date,
        'action': action,
        'price': price,
        'quantity': quantity,
        'pnl': pnl
    })

def save_logs(trade_df,daily_df):
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    trade_df.to_csv(os.path.join(logs_dir, "trade_log_ss_improved.csv"), index=False)
    daily_df.to_csv(os.path.join(logs_dir, "daily_balance_ss_improved.csv"), index=False)
    print("Logs saved.")

def plot(trade_df,daily_df):
    # Plot equity curve
    plt.figure(figsize=(12, 6))
    plt.plot(daily_df['date'], daily_df['net_worth'], label='Equity Curve', color='blue')
    plt.title('Equity Curve')
    plt.xlabel('Date')
    plt.ylabel('Net Worth (₹)')
    plt.grid(True)
    plt.legend()

    for _, row in trade_df.iterrows():
        try:
            y_val = daily_df.loc[daily_df['date'] == row['date'], 'net_worth'].values[0]
            color = 'green' if row['action'] in ['BUY', 'COVER'] else 'red'
            marker = '^' if row['action'] in ['BUY', 'SHORT'] else 'v'
            plt.scatter(row['date'], y_val, color=color, marker=marker, s=100)
        except IndexError:
            continue

    plt.tight_layout()
    plt.show()