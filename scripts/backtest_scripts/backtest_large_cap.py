import os
import pandas as pd
import matplotlib.pyplot as plt

# --- Paths ---
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "large_cap_5_year"))
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs", "large_cap_backtest"))
os.makedirs(LOG_DIR, exist_ok=True)

# --- Load Historical Data ---
def load_data(symbol):
    path = os.path.join(DATA_DIR, f"{symbol}_5year_data.csv")
    df = pd.read_csv(path, parse_dates=['date'])
    return df

# --- Generate Buy/Sell Signals (Simple EMA Crossover) ---
def generate_signals(df):
    df['ema_10'] = df['close'].rolling(10).mean()
    df['ema_30'] = df['close'].rolling(30).mean()
    df['signal'] = 0
    df.loc[df['ema_10'] > df['ema_30'], 'signal'] = 1
    df.loc[df['ema_10'] < df['ema_30'], 'signal'] = -1
    return df

# --- Simulate Backtest with Balance Sheet ---
def run_backtest(df, initial_capital=100000, stop_loss_pct=0.01, target_pct=0.02):
    position = 0
    buy_price = 0
    cash = initial_capital
    trades = []
    equity_curve = []
    balance_sheet = []
    full_log = []

    realized_pnl = 0

    for i in range(1, len(df)):
        price = df['close'].iloc[i]
        open_price = df['open'].iloc[i]
        high_price = df['high'].iloc[i]
        low_price = df['low'].iloc[i]
        signal = df['signal'].iloc[i]
        date = df['date'].iloc[i]

        unrealized_pnl = (price - buy_price) * position if position > 0 else 0
        portfolio_value = cash + position * price

        log_entry = {
            'date': date,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': price,
            'signal': signal,
            'position': position,
            'cash': cash,
            'portfolio_value': portfolio_value,
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'action': 'HOLD',
            'trade_type': '',
            'quantity': 0,
            'trade_pnl': 0,
            'reason': ''
        }

        if position > 0:
            change = (price - buy_price) / buy_price
            if change <= -stop_loss_pct:
                pnl = (price - buy_price) * position
                cash += position * price
                trades.append({'type': 'STOP-LOSS', 'price': price, 'date': date, 'status': 'Closed', 'reason': 'Stop loss', 'quantity': position, 'pnl': pnl})
                realized_pnl += pnl
                log_entry.update({'action': 'EXIT', 'trade_type': 'STOP-LOSS', 'quantity': position, 'trade_pnl': pnl, 'reason': 'Price dropped below stop loss threshold'})
                position = 0
                buy_price = 0
            elif change >= target_pct:
                pnl = (price - buy_price) * position
                cash += position * price
                trades.append({'type': 'TARGET-HIT', 'price': price, 'date': date, 'status': 'Closed', 'reason': 'Target hit', 'quantity': position, 'pnl': pnl})
                realized_pnl += pnl
                log_entry.update({'action': 'EXIT', 'trade_type': 'TARGET-HIT', 'quantity': position, 'trade_pnl': pnl, 'reason': 'Price reached target profit'})
                position = 0
                buy_price = 0
            elif signal == -1:
                pnl = (price - buy_price) * position
                cash += position * price
                trades.append({'type': 'SELL', 'price': price, 'date': date, 'status': 'Closed', 'reason': 'Signal exit', 'quantity': position, 'pnl': pnl})
                realized_pnl += pnl
                log_entry.update({'action': 'EXIT', 'trade_type': 'SELL', 'quantity': position, 'trade_pnl': pnl, 'reason': 'Exit signal triggered'})
                position = 0
                buy_price = 0

        elif position == 0 and signal == 1:
            quantity = int(cash // price)
            if quantity > 0:
                position = quantity
                buy_price = price
                cash -= position * price
                trades.append({'type': 'BUY', 'price': price, 'date': date, 'status': 'Open', 'reason': 'Signal entry', 'quantity': position, 'pnl': 0})
                log_entry.update({'action': 'BUY', 'trade_type': 'BUY', 'quantity': position, 'reason': 'Entry signal triggered'})

        equity_curve.append({'date': date, 'equity': portfolio_value})

        balance_sheet.append({
            'date': date,
            'cash': cash,
            'position': position,
            'price': price,
            'portfolio_value': portfolio_value,
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl
        })

        full_log.append(log_entry)

    final_value = cash + position * df['close'].iloc[-1]
    return trades, final_value, pd.DataFrame(equity_curve), pd.DataFrame(balance_sheet), pd.DataFrame(full_log)

# --- Calculate Metrics ---
def calculate_metrics(trades, initial_capital, final_value):
    buys = [t for t in trades if t['type'] == 'BUY']
    sells = [t for t in trades if t['type'] in ['SELL', 'STOP-LOSS', 'TARGET-HIT']]
    profits = [s['price'] - b['price'] for b, s in zip(buys, sells) if s['price'] and b['price']]

    total_trades = len(profits)
    win_trades = len([p for p in profits if p > 0])
    loss_trades = len([p for p in profits if p <= 0])
    win_rate = (win_trades / total_trades) * 100 if total_trades > 0 else 0
    return_pct = ((final_value - initial_capital) / initial_capital) * 100

    return {
        'Final Value': final_value,
        'Return (%)': return_pct,
        'Total Trades': total_trades,
        'Win Rate (%)': win_rate,
        'Profit Trades': win_trades,
        'Loss Trades': loss_trades
    }

# --- Save Logs ---
def save_logs(symbol, trades, equity_curve, balance_sheet, full_log):
    pd.DataFrame(trades).to_csv(os.path.join(LOG_DIR, f"{symbol}_trades.csv"), index=False)
    equity_curve.to_csv(os.path.join(LOG_DIR, f"{symbol}_equity.csv"), index=False)
    balance_sheet.to_csv(os.path.join(LOG_DIR, f"{symbol}_balance_sheet.csv"), index=False)
    full_log.to_csv(os.path.join(LOG_DIR, f"{symbol}_log.csv"), index=False)

# --- Run All Backtests ---
def run_all_backtests():
    results = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".csv"):
            symbol = filename.replace("_5year_data.csv", "")
            print(f"\nRunning backtest for {symbol}...")
            try:
                df = load_data(symbol)
                df = generate_signals(df)
                trades, final_value, equity_curve, balance_sheet, full_log = run_backtest(df)
                metrics = calculate_metrics(trades, 100000, final_value)
                metrics['Symbol'] = symbol
                results.append(metrics)
                save_logs(symbol, trades, equity_curve, balance_sheet, full_log)
                print(f"Backtest done for {symbol}. Final portfolio value: ₹{final_value:.2f}")
            except Exception as e:
                print(f"Error running backtest for {symbol}: {e}")

    summary_df = pd.DataFrame(results)
    summary_df.to_csv(os.path.join(LOG_DIR, "largecap_summary.csv"), index=False)
    print(f"\nSummary saved to {os.path.join(LOG_DIR, 'largecap_summary.csv')}")

# --- Main ---
if __name__ == "__main__":
    run_all_backtests()
