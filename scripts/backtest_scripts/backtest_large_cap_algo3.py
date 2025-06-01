# ----------------------------------------------------------------------------------------
# File: backtest_large_cap_algo3.py
# Description:
#   - Batch backtesting framework for large cap stocks using 5-year historical data.
#   - Implements an enhanced strategy with EMA crossover, MACD, RSI, and ATR-based stop loss/target.
#   - Entry: EMA(10) > EMA(30), MACD bullish, RSI between 40 and 60.
#   - Exit: MACD bearish or RSI > 70, or ATR-based stop loss/target hit.
#   - Uses standard ATR calculation for volatility-based exits.
#   - Adds a cooldown period after each exit to reduce overtrading.
#   - Runs backtests in parallel for all symbols using ProcessPoolExecutor for speed.
#   - Logs trades, equity curve, balance sheet, and detailed actions for each symbol.
#   - Outputs a summary CSV of results for all symbols.
# ----------------------------------------------------------------------------------------
# Author: Ganesh K
# Date: [YYYY-MM-DD]
# ----------------------------------------------------------------------------------------

# ...existing code...

import os
import pandas as pd
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor, as_completed

# --- Paths ---
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "large_cap_5_year"))
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs_algo3", "large_cap_backtest"))
os.makedirs(LOG_DIR, exist_ok=True)

# --- Load Historical Data ---
def load_data(symbol):
    path = os.path.join(DATA_DIR, f"{symbol}_5year_data.csv")
    df = pd.read_csv(path, parse_dates=['date'])
    return df

# --- Generate Buy/Sell Signals ---
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

    df['prev_close'] = df['close'].shift(1)
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = (df['high'] - df['prev_close']).abs()
    df['tr3'] = (df['low'] - df['prev_close']).abs()
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['tr'].rolling(14).mean()

    df['signal'] = 0
    df.loc[(df['ema_10'] > df['ema_30']) &
           (df['macd'] > df['macd_signal']) &
           (df['rsi'] > 40) & (df['rsi'] < 60), 'signal'] = 1
    df.loc[(df['macd'] < df['macd_signal']) | (df['rsi'] > 70), 'signal'] = -1

    return df

# --- Backtest Core ---
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
    atr_multiplier_tp = 2.0
    cooldown_period = 5
    last_exit_index = -999

    for i in range(1, len(df)):
        price = df['close'].iloc[i]
        date = df['date'].iloc[i]
        atr = df['atr'].iloc[i]
        signal = df['signal'].iloc[i]

        stop_loss = buy_price - atr_multiplier_sl * atr if position > 0 else 0
        target = buy_price + atr_multiplier_tp * atr if position > 0 else 0

        unrealized_pnl = (price - buy_price) * position if position > 0 else 0
        portfolio_value = cash + (position * price if position > 0 else 0)

        log_entry = {
            'date': date, 'close': price, 'signal': signal, 'position': position,
            'cash': cash, 'portfolio_value': portfolio_value, 'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl, 'action': 'HOLD', 'trade_type': '',
            'quantity': 0, 'trade_pnl': 0, 'reason': ''
        }

        exit_condition = (
            df['ema_10'].iloc[i] < df['ema_30'].iloc[i] or
            df['macd'].iloc[i] < df['macd_signal'].iloc[i] or
            df['rsi'].iloc[i] > 70
        )

        if position == 0 and signal == 1 and (i - last_exit_index) > cooldown_period:
            quantity = int(cash // price)
            if quantity > 0:
                position = quantity
                buy_price = price
                cash -= quantity * price
                trades.append({'type': 'BUY', 'price': price, 'date': date, 'status': 'Open', 'quantity': quantity, 'pnl': 0})
                log_entry.update({'action': 'BUY', 'trade_type': 'BUY', 'quantity': quantity, 'reason': 'Entry signal triggered'})

        elif position > 0:
            if price <= stop_loss:
                pnl = (stop_loss - buy_price) * position
                cash += position * stop_loss
                realized_pnl += pnl
                trades.append({'type': 'STOP-LOSS', 'price': stop_loss, 'date': date, 'status': 'Closed', 'quantity': position, 'pnl': pnl})
                log_entry.update({'action': 'EXIT', 'trade_type': 'STOP-LOSS', 'quantity': position, 'trade_pnl': pnl, 'reason': 'ATR-based stop loss hit'})
                position = 0
                buy_price = 0
                last_exit_index = i
            elif price >= target:
                pnl = (target - buy_price) * position
                cash += position * target
                realized_pnl += pnl
                trades.append({'type': 'TARGET-HIT', 'price': target, 'date': date, 'status': 'Closed', 'quantity': position, 'pnl': pnl})
                log_entry.update({'action': 'EXIT', 'trade_type': 'TARGET-HIT', 'quantity': position, 'trade_pnl': pnl, 'reason': 'ATR-based target hit'})
                position = 0
                buy_price = 0
                last_exit_index = i
            elif exit_condition:
                pnl = (price - buy_price) * position
                cash += position * price
                realized_pnl += pnl
                trades.append({'type': 'INDICATOR-EXIT', 'price': price, 'date': date, 'status': 'Closed', 'quantity': position, 'pnl': pnl})
                log_entry.update({'action': 'EXIT', 'trade_type': 'INDICATOR-EXIT', 'quantity': position, 'trade_pnl': pnl, 'reason': 'Exit indicator triggered'})
                position = 0
                buy_price = 0
                last_exit_index = i

        equity_curve.append({'date': date, 'equity': portfolio_value})
        balance_sheet.append({
            'date': date, 'cash': cash, 'position': position, 'price': price,
            'portfolio_value': portfolio_value, 'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl
        })
        full_log.append(log_entry)

    final_value = cash + (position * df['close'].iloc[-1] if position > 0 else 0)
    return trades, final_value, pd.DataFrame(equity_curve), pd.DataFrame(balance_sheet), pd.DataFrame(full_log)

# --- Metrics ---
def calculate_metrics(trades, initial_capital, final_value):
    total_trades = sum(1 for t in trades if t['type'] == 'BUY')
    closed = [t for t in trades if t['type'] in ['STOP-LOSS', 'TARGET-HIT', 'INDICATOR-EXIT']]
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
def save_logs(symbol, trades, equity_curve, balance_sheet, full_log):
    pd.DataFrame(trades).to_csv(os.path.join(LOG_DIR, f"{symbol}_trades.csv"), index=False)
    equity_curve.to_csv(os.path.join(LOG_DIR, f"{symbol}_equity.csv"), index=False)
    balance_sheet.to_csv(os.path.join(LOG_DIR, f"{symbol}_balance_sheet.csv"), index=False)
    full_log.to_csv(os.path.join(LOG_DIR, f"{symbol}_log.csv"), index=False)

# --- Backtest Worker ---
def backtest_symbol(symbol):
    try:
        df = load_data(symbol)
        df = generate_signals(df)
        trades, final_value, equity_curve, balance_sheet, full_log = run_backtest(df)
        metrics = calculate_metrics(trades, 100000, final_value)
        metrics['Symbol'] = symbol
        save_logs(symbol, trades, equity_curve, balance_sheet, full_log)
        return metrics
    except Exception as e:
        return {'Symbol': symbol, 'Error': str(e)}

# --- Run All Backtests in Parallel ---
def run_all_backtests():
    symbols = [f.replace("_5year_data.csv", "") for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    results = []
    print(f"Starting parallel backtests for {len(symbols)} symbols...\n")

    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(backtest_symbol, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
                if 'Error' not in result:
                    print(f"✔ {result['Symbol']}: ₹{result['Final Value']:.2f}")
                else:
                    print(f"✖ {result['Symbol']} failed: {result['Error']}")

    summary_df = pd.DataFrame(results)
    summary_df.to_csv(os.path.join(LOG_DIR, "largecap_summary.csv"), index=False)
    print(f"\n✅ Summary saved to {os.path.join(LOG_DIR, 'largecap_summary.csv')}")

# --- Main ---
if __name__ == "__main__":
    run_all_backtests()
