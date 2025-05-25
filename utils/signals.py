def generate_signals(row, position, entry_price):
    """
    Generate trading signals: BUY, SELL, SHORT, COVER, or HOLD.
    """
    # Dynamic stop-loss and take-profit using ATR
    atr = row['atr']
    dynamic_sl = atr * 1.5
    dynamic_tp = atr * 2.5

    stop_loss_price_long = entry_price - dynamic_sl
    take_profit_price_long = entry_price + dynamic_tp

    stop_loss_price_short = entry_price + dynamic_sl
    take_profit_price_short = entry_price - dynamic_tp

    # Entry logic
    if position == 0:
        if (
            row['macd'] > 0 and
            row['ema_20'] > row['ema_50'] and
            row['close'] > row['bb_upper'] and
            row['adx'] > 20
        ):
            return 'BUY'

        elif (
            row['macd'] < 0 and
            row['ema_20'] < row['ema_50'] and
            row['close'] < row['bb_lower'] and
            row['adx'] > 20
        ):
            return 'SHORT'

    # Exit logic for long position
    if position == 1:
        if (
            row['macd'] < 0 or
            row['close'] < stop_loss_price_long or
            row['close'] > take_profit_price_long or
            row['close'] < row['bb_lower'] or
            row['adx'] < 20
        ):
            return 'SELL'

    # Exit logic for short position
    if position == -1:
        if (
            row['macd'] > 0 or
            row['close'] > stop_loss_price_short or
            row['close'] < take_profit_price_short or
            row['close'] > row['bb_upper'] or
            row['adx'] < 20
        ):
            return 'COVER'

    return 'HOLD'
