# ----------------------------------------------------------------------------------------
# File: backtest_large_cap_algo4.py
# Description:
#   - Enhanced batch backtesting framework for large cap stocks using 5-year historical data.
#   - Implements risk-based position sizing using ATR-based stop loss and target.
#   - Models transaction costs (brokerage) and slippage for realistic trade execution.
#   - Includes data validation for required columns, missing values, and date order.
#   - Supports walk-forward/out-of-sample testing by trading only after TRAIN_END_DATE.
#   - Entry: EMA(10) > EMA(30), MACD bullish, RSI between 40 and 60.
#   - Exit: MACD bearish, RSI > 70, or ATR-based stop loss/target hit.
#   - Handles price gaps and logs all trades, equity curve, balance sheet, and actions.
#   - Runs backtests in parallel for all symbols using ProcessPoolExecutor.
#   - Outputs a summary CSV of results for all symbols.
# ----------------------------------------------------------------------------------------
# Author: Ganesh K
# Date: [YYYY-MM-DD]
# ----------------------------------------------------------------------------------------

# ...existing code...
import os
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

# --- Configurable Parameters ---
ATR_SL_MULTIPLIER = 1.5
ATR_TP_MULTIPLIER = 2.0
RISK_PER_TRADE = 0.01  # 1% of capital
BROKERAGE = 0.001  # 0.1% cost per trade
SLIPPAGE = 0.002  # 0.2% slippage
COOLDOWN_PERIOD = 5
TRAIN_END_DATE = '2022-01-01'

# --- Paths ---
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "large_cap_5_year"))
LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs_algo4", "large_cap_backtest"))
os.makedirs(LOG_DIR, exist_ok=True)

# --- Data Validation ---
def validate_data(df):
    required = {'date', 'open', 'high', 'low', 'close'}
    if not required.issubset(df.columns):
        return False
    if df.isnull().any().any():
        return False
    if not df['date'].is_monotonic_increasing:
        return False
    return True

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
    df.loc[(df['ema_10'] > df['ema_30']) & (df['macd'] > df['macd_signal']) & (df['rsi'].between(40, 60)), 'signal'] = 1
    df.loc[(df['macd'] < df['macd_signal']) | (df['rsi'] > 70), 'signal'] = -1
    return df

# --- Run Backtest ---
def run_backtest(df, initial_capital=100000):
    df = df[df['date'] >= TRAIN_END_DATE].reset_index(drop=True)
    position = 0
    buy_price = 0
    cash = initial_capital
    trades, equity_curve, balance_sheet, full_log = [], [], [], []
    realized_pnl, last_exit_index = 0, -999

    for i in range(1, len(df)):
        row = df.iloc[i]
        date, price, atr, signal = row['date'], row['close'], row['atr'], row['signal']

        if pd.isna(atr):
            continue

        exit_condition = (row['ema_10'] < row['ema_30']) or (row['macd'] < row['macd_signal']) or (row['rsi'] > 70)
        unrealized_pnl = (price - buy_price) * position if position > 0 else 0
        portfolio_value = cash + (position * price if position > 0 else 0)

        log_entry = {
            'date': date, 'close': price, 'signal': signal, 'position': position, 'cash': cash,
            'portfolio_value': portfolio_value, 'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl, 'action': 'HOLD', 'quantity': 0, 'trade_pnl': 0, 'reason': ''
        }

        stop_loss = buy_price - ATR_SL_MULTIPLIER * atr if position > 0 else 0
        target = buy_price + ATR_TP_MULTIPLIER * atr if position > 0 else 0

        if position == 0 and signal == 1 and (i - last_exit_index) > COOLDOWN_PERIOD:
            risk = RISK_PER_TRADE * cash
            qty = int(risk / (ATR_SL_MULTIPLIER * atr))
            if qty > 0:
                entry_price = price * (1 + SLIPPAGE)
                total_cost = qty * entry_price * (1 + BROKERAGE)
                if total_cost <= cash:
                    position = qty
                    buy_price = entry_price
                    cash -= total_cost
                    trades.append({'type': 'BUY', 'price': entry_price, 'date': date, 'quantity': qty, 'status': 'Open', 'pnl': 0})
                    log_entry.update({'action': 'BUY', 'quantity': qty, 'reason': 'Entry signal'})

        elif position > 0:
            exit_price = price * (1 - SLIPPAGE)
            if exit_price <= stop_loss:
                pnl = (stop_loss - buy_price) * position - stop_loss * position * BROKERAGE
                cash += position * stop_loss * (1 - BROKERAGE)
                realized_pnl += pnl
                trades.append({'type': 'STOP-LOSS', 'price': stop_loss, 'date': date, 'quantity': position, 'status': 'Closed', 'pnl': pnl})
                log_entry.update({'action': 'EXIT', 'quantity': position, 'trade_pnl': pnl, 'reason': 'Stop loss hit'})
                position, buy_price, last_exit_index = 0, 0, i
            elif exit_price >= target:
                pnl = (target - buy_price) * position - target * position * BROKERAGE
                cash += position * target * (1 - BROKERAGE)
                realized_pnl += pnl
                trades.append({'type': 'TARGET-HIT', 'price': target, 'date': date, 'quantity': position, 'status': 'Closed', 'pnl': pnl})
                log_entry.update({'action': 'EXIT', 'quantity': position, 'trade_pnl': pnl, 'reason': 'Target hit'})
                position, buy_price, last_exit_index = 0, 0, i
            elif exit_condition:
                pnl = (exit_price - buy_price) * position - exit_price * position * BROKERAGE
                cash += position * exit_price * (1 - BROKERAGE)
                realized_pnl += pnl
                trades.append({'type': 'INDICATOR-EXIT', 'price': exit_price, 'date': date, 'quantity': position, 'status': 'Closed', 'pnl': pnl})
                log_entry.update({'action': 'EXIT', 'quantity': position, 'trade_pnl': pnl, 'reason': 'Indicator exit'})
                position, buy_price, last_exit_index = 0, 0, i

        equity_curve.append({'date': date, 'equity': portfolio_value})
        balance_sheet.append({'date': date, 'cash': cash, 'position': position, 'price': price, 'portfolio_value': portfolio_value})
        full_log.append(log_entry)

    final_value = cash + (position * df['close'].iloc[-1] if position > 0 else 0)
    return trades, final_value, pd.DataFrame(equity_curve), pd.DataFrame(balance_sheet), pd.DataFrame(full_log)

# --- Metrics ---
def calculate_metrics(trades, initial_capital, final_value):
    total_trades = sum(1 for t in trades if t['type'] == 'BUY')
    closed = [t for t in trades if t['type'] != 'BUY']
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

# --- Backtest Worker ---
def backtest_symbol(symbol):
    try:
        df = load_data(symbol)
        if not validate_data(df):
            return {'Symbol': symbol, 'Error': 'Invalid or corrupt data'}
        df = generate_signals(df)
        trades, final_value, equity, balance, log = run_backtest(df)
        metrics = calculate_metrics(trades, 100000, final_value)
        metrics['Symbol'] = symbol
        save_logs(symbol, trades, equity, balance, log)
        return metrics
    except Exception as e:
        return {'Symbol': symbol, 'Error': str(e)}

# --- Batch Backtest ---
def run_all_backtests():
    symbols = [f.replace("_5year_data.csv", "") for f in os.listdir(DATA_DIR) if f.endswith(".csv")]
    results = []
    print(f"Running backtests on {len(symbols)} symbols...")

    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(backtest_symbol, symbol): symbol for symbol in symbols}
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            if 'Error' in res:
                print(f"✖ {res['Symbol']} failed: {res['Error']}")
            else:
                print(f"✔ {res['Symbol']}: ₹{res['Final Value']:.2f}")

    pd.DataFrame(results).to_csv(os.path.join(LOG_DIR, "largecap_summary.csv"), index=False)
    print("✅ All results saved.")

if __name__ == "__main__":
    run_all_backtests()
