from money_printer.sizing import AtrRiskSizer, FixedFractionalSizer, KellySizer, VolatilityTargetSizer, build_sizer


def test_fixed_fractional_caps_by_cash():
    s = FixedFractionalSizer(fraction=0.5)
    qty = s.size(equity=10_000, price=100, cash=200)
    assert qty == 2.0  # cash limited


def test_vol_and_atr_and_kelly():
    closes = [100 + i * 0.1 for i in range(40)]
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    vol_qty = VolatilityTargetSizer(target_vol=0.2, lookback=20).size(
        equity=50_000, price=100, cash=50_000, closes=closes
    )
    atr_qty = AtrRiskSizer(risk_pct=0.01).size(
        equity=50_000, price=100, cash=50_000, closes=closes, highs=highs, lows=lows
    )
    kelly_qty = KellySizer(win_rate=0.6, avg_win=1.2, avg_loss=1.0).size(
        equity=50_000, price=100, cash=50_000
    )
    assert vol_qty > 0
    assert atr_qty > 0
    assert kelly_qty > 0
    assert build_sizer("fixed", fraction=0.1).size(equity=1000, price=10, cash=1000) > 0
