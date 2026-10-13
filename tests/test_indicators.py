from money_printer.indicators import atr, bollinger, ema, macd, momentum, rsi, sma, stdev


def test_sma_and_ema():
    vals = [float(i) for i in range(1, 21)]
    assert sma(vals, 5) == sum(vals[-5:]) / 5
    assert ema(vals, 5) is not None


def test_rsi_macd_bollinger_momentum_atr():
    up = [100 + i for i in range(60)]
    assert rsi(up, 14) is not None
    line, sig, hist = macd(up)
    assert line is not None and sig is not None and hist is not None
    lo, mid, hi = bollinger(up, 20, 2.0)
    assert lo is not None and mid is not None and hi is not None and lo < mid < hi
    assert momentum(up, 10) is not None
    highs = [v + 1 for v in up]
    lows = [v - 1 for v in up]
    assert atr(highs, lows, up, 14) is not None
    assert stdev(up, 10) is not None
