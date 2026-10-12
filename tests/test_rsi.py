from money_printer.strategies.rsi import rsi


def test_rsi_bounds():
    # rising series → high RSI
    up = [float(i) for i in range(1, 30)]
    assert rsi(up, 14) > 70
    # falling series → low RSI
    down = [float(i) for i in range(30, 1, -1)]
    assert rsi(down, 14) < 30
