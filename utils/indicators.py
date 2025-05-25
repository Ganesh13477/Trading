import pandas_ta as ta

def add_indicators(df):
    df['rsi'] = ta.rsi(df['close'])
    df['ema_20'] = ta.ema(df['close'], length=20)
    df['ema_50'] = ta.ema(df['close'], length=50)
    df['macd'] = ta.macd(df['close'])['MACD_12_26_9']
    
    bbands = ta.bbands(df['close'], length=20, std=2)
    df['bb_upper'] = bbands['BBU_20_2.0']
    df['bb_lower'] = bbands['BBL_20_2.0']
    
    df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    df.dropna(inplace=True)
    return df
