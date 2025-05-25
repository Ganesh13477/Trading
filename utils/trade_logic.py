def evaluate_signals(df, index, position, buy_price):
    """
    Evaluate buy/sell/short/cover signals based on technical indicators.
    Returns action: one of ['BUY', 'SELL', 'SHORT', 'COVER', None]
    """
    row = df.loc[index]
    action = None

    dynamic_sl = row['atr'] * 1.5
    dynamic_tp = row['atr'] * 2.5
    stop_loss_price = (
        buy_price - dynamic_sl if position == 1
        else buy_price + dynamic_sl if position == -1
        else 0
    )
    take_profit_price = (
        buy_price + dynamic_tp if position == 1
        else buy_price - dynamic_tp if position == -1
        else 0
    )

    # BUY signal
    if position == 0 and (
        row['macd'] > 0 and
        row['ema_20'] > row['ema_50'] and
        row['close'] > row['bb_upper'] and
        row['adx'] > 20
    ):
        action = 'BUY'

    # SELL signal (for long positions)
    elif position == 1 and (
        row['macd'] < 0 or
        row['close'] < stop_loss_price or
        row['close'] > take_profit_price or
        row['close'] < row['bb_lower'] or
        row['adx'] < 20
    ):
        action = 'SELL'

    # SHORT signal
    elif position == 0 and (
        row['macd'] < 0 and
        row['ema_20'] < row['ema_50'] and
        row['close'] < row['bb_lower'] and
        row['adx'] > 20
    ):
        action = 'SHORT'

    # COVER signal (for short positions)
    elif position == -1 and (
        row['macd'] > 0 or
        row['close'] > stop_loss_price or
        row['close'] < take_profit_price or
        row['close'] > row['bb_upper'] or
        row['adx'] < 20
    ):
        action = 'COVER'

    return action
