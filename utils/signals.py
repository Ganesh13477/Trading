def generate_signals(row, position, entry_price, cooldown=0, holding_period=0):
    """
    Generate signals: BUY, SELL, SHORT, COVER, or HOLD
    """
    if cooldown > 0:
        return 'HOLD'

    atr = row['atr']
    sl = atr * 1.5
    tp = atr * 2.5

    stop_loss_long = entry_price - sl
    take_profit_long = entry_price + tp
    stop_loss_short = entry_price + sl
    take_profit_short = entry_price - tp

    # Minimum holding period before exiting to avoid whipsaw
    min_hold = 3

    if position == 0:
        if (
            row['macd'] > 0 and
            row['ema_20'] > row['ema_50'] and
            row['close'] > row['bb_upper'] and
            row['adx'] > 20 and
            row['volume_spike'] == 1 and
            row['volatility'] < 2.5
        ):
            return 'BUY'

        elif (
            row['macd'] < 0 and
            row['ema_20'] < row['ema_50'] and
            row['close'] < row['bb_lower'] and
            row['adx'] > 20 and
            row['volume_spike'] == 1 and
            row['volatility'] < 2.5
        ):
            return 'SHORT'

    elif position == 1:
        if holding_period < min_hold:
            return 'HOLD'
        if (
            row['macd'] < 0 or
            row['close'] < stop_loss_long or
            row['close'] > take_profit_long or
            row['close'] < row['bb_lower'] or
            row['adx'] < 20
        ):
            return 'SELL'

    elif position == -1:
        if holding_period < min_hold:
            return 'HOLD'
        if (
            row['macd'] > 0 or
            row['close'] > stop_loss_short or
            row['close'] < take_profit_short or
            row['close'] > row['bb_upper'] or
            row['adx'] < 20
        ):
            return 'COVER'

    return 'HOLD'
