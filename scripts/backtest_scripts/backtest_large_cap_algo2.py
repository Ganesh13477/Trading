import os
import pandas as pd
import matplotlib.pyplot as plt
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Paths ---
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "large_cap_5_year"))
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs_algo2", "large_cap_backtest"))
os.makedirs(LOG_DIR, exist_ok=True)

# --- Load Historical Data ---
def load_data(symbol):
    path = os.path.join(DATA_DIR, f"{symbol}_5year_data.csv")
    df = pd.read_csv(path, parse_dates=['date'])
    return df

# --- Generate Buy/Sell Signals (Improved Strategy) ---
def generate_signals(df):
    df['ema_10'] = df['close'].ewm(span=10, adjust=False).mean()
    df['ema_30'] = df['close'].ewm(span=30, adjust=False).mean()

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

    df['tr'] = df[['high', 'low', 'close']].max(axis=1) - df[['high', 'low', 'close']].min(axis=1)
    df['atr'] = df['tr'].rolling(14).mean()

    df['signal'] = 0
    df.loc[(df['ema_10'] > df['ema_30']) & (df['macd'] > df['macd_signal']) & (df['rsi'] > 40) & (df['rsi'] < 60), 'signal'] = 1
    df.loc[(df['macd'] < df['macd_signal']) | (df['rsi'] > 70), 'signal'] = -1

    return df

# --- Run Backtest ---
def run_backtest(df, initial_capital=100000):
    position = 0
    buy_price = 0
    cash = initial_capital
    trades = []
    equity_curve = []
    balance_sheet = []
    full_log = []
    realized_pnl = 0
    atr_multiplier_sl = 1.5
    atr_multiplier_tp = 2.5

    for i in range(1, len(df)):
        price = df['close'].iloc[i]
        open_price = df['open'].iloc[i]
        high_price = df['high'].iloc[i]
        low_price = df['low'].iloc[i]
        signal = df['signal'].iloc[i]
        date = df['date'].iloc[i]
        atr = df['atr'].iloc[i]

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
            stop_loss_price = buy_price - atr_multiplier_sl * atr
            target_price = buy_price + atr_multiplier_tp * atr

            if low_price <= stop_loss_price:
                pnl = (stop_loss_price - buy_price) * position
                cash += position * stop_loss_price
                realized_pnl += pnl
                trades.append({'type': 'STOP-LOSS', 'price': stop_loss_price, 'date': date, 'status': 'Closed', 'quantity': position, 'pnl': pnl})
                log_entry.update({'action': 'EXIT', 'trade_type': 'STOP-LOSS', 'quantity': position, 'trade_pnl': pnl, 'reason': 'ATR stop loss'})
                position = 0
                buy_price = 0
            elif high_price >= target_price:
                pnl = (target_price - buy_price) * position
                cash += position * target_price
                realized_pnl += pnl
                trades.append({'type': 'TARGET-HIT', 'price': target_price, 'date': date, 'status': 'Closed', 'quantity': position, 'pnl': pnl})
                log_entry.update({'action': 'EXIT', 'trade_type': 'TARGET-HIT', 'quantity': position, 'trade_pnl': pnl, 'reason': 'ATR target hit'})
                position = 0
                buy_price = 0
            elif signal == -1:
                pnl = (price - buy_price) * position
                cash += position * price
                realized_pnl += pnl
                trades.append({'type': 'SELL', 'price': price, 'date': date, 'status': 'Closed', 'quantity': position, 'pnl': pnl})
                log_entry.update({'action': 'EXIT', 'trade_type': 'SELL', 'quantity': position, 'trade_pnl': pnl, 'reason': 'Exit signal'})
                position = 0
                buy_price = 0

        elif position == 0 and signal == 1:
            quantity = int(cash // price)
            if quantity > 0:
                position = quantity
                buy_price = price
                cash -= position * price
                trades.append({'type': 'BUY', 'price': price, 'date': date, 'status': 'Open', 'quantity': position, 'pnl': 0})
                log_entry.update({'action': 'BUY', 'trade_type': 'BUY', 'quantity': position, 'reason': 'Entry signal'})

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

# --- Metrics ---
def calculate_metrics(trades, initial_capital, final_value):
    total_trades = sum(1 for t in trades if t['type'] == 'BUY')
    closed = [t for t in trades if t['type'] in ['SELL', 'STOP-LOSS', 'TARGET-HIT']]
    wins = [t for t in closed if t['pnl'] > 0]
    losses = [t for t in closed if t['pnl'] <= 0]
    win_rate = (len(wins) / len(closed)) * 100 if closed else 0
    return_pct = ((final_value - initial_capital) / initial_capital) * 100
    return {
        'Final Value': final_value,
        'Return (%)': return_pct,
        'Total Trades': total_trades,
        'Win Rate (%)': win_rate,
        'Profit Trades': len(wins),
        'Loss Trades': len(losses)
    }

# --- Save Logs ---
def save_logs(symbol, trades, equity, balance, log):
    pd.DataFrame(trades).to_csv(os.path.join(LOG_DIR, f"{symbol}_trades.csv"), index=False)
    equity.to_csv(os.path.join(LOG_DIR, f"{symbol}_equity.csv"), index=False)
    balance.to_csv(os.path.join(LOG_DIR, f"{symbol}_balance_sheet.csv"), index=False)
    log.to_csv(os.path.join(LOG_DIR, f"{symbol}_log.csv"), index=False)

# --- Process Single Symbol (for threading) ---
def process_symbol(symbol):
    try:
        df = load_data(symbol)
        df = generate_signals(df)
        trades, final_value, equity, balance, log = run_backtest(df)
        metrics = calculate_metrics(trades, 100000, final_value)
        metrics['Symbol'] = symbol
        save_logs(symbol, trades, equity, balance, log)
        print(f"{symbol}: Done. ₹{final_value:.2f}")
        return metrics
    except Exception as e:
        print(f"{symbol}: Error - {e}")
        return {'Symbol': symbol, 'Final Value': 0, 'Return (%)': 0, 'Total Trades': 0, 'Win Rate (%)': 0, 'Profit Trades': 0, 'Loss Trades': 0}

# --- Run All with Threading ---
def run_all_backtests():
    symbols = [f.replace("_5year_data.csv", "") for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    results = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_symbol, symbol) for symbol in symbols]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    summary_df = pd.DataFrame(results)
    summary_df.to_csv(os.path.join(LOG_DIR, "largecap_summary.csv"), index=False)
    print(f"\n✅ Summary saved to: {os.path.join(LOG_DIR, 'largecap_summary.csv')}")

# --- Main ---
if __name__ == "__main__":
    run_all_backtests()
