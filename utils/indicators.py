import pandas as pd
import numpy as np

def add_indicators(df):
    # ATR
    df['tr0'] = abs(df['high'] - df['low'])
    df['tr1'] = abs(df['high'] - df['close'].shift())
    df['tr2'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
    df['atr'] = df['tr'].rolling(14).mean()

    # Bollinger Bands (20, 2)
    df['bb_middle'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']

    # EMA 20 and 50
    df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

    # MACD (12,26,9)
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

    # RSI (14)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # ADX (14)
    df['up_move'] = df['high'] - df['high'].shift()
    df['down_move'] = df['low'].shift() - df['low']
    df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
    df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
    df['tr'] = df[['high', 'low', 'close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['close']), abs(x['low'] - x['close'])), axis=1)
    df['atr'] = df['tr'].rolling(14).mean()
    df['plus_di'] = 100 * (df['plus_dm'].ewm(alpha=1/14).mean() / df['atr'])
    df['minus_di'] = 100 * (df['minus_dm'].ewm(alpha=1/14).mean() / df['atr'])
    df['dx'] = 100 * (abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di']))
    df['adx'] = df['dx'].rolling(14).mean()

    # Volatility - rolling std dev of returns (1-day)
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(14).std() * np.sqrt(252) * 100  # annualized volatility %

    # Volume spike - volume > 1.5x 20-period avg volume
    df['volume_spike'] = (df['volume'] > 1.5 * df['volume'].rolling(20).mean()).astype(int)

    # Clean up temporary columns
    df.drop(['tr0', 'tr1', 'tr2', 'up_move', 'down_move', 'plus_dm', 'minus_dm', 'dx', 'returns', 'tr'], axis=1, inplace=True, errors='ignore')

    return df
