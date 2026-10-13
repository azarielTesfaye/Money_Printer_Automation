from money_printer.risk_ext import CircuitBreaker, ExposureLimit, PortfolioExposureGuard


def test_circuit_breaker_trips_on_losses_and_drawdown():
    cb = CircuitBreaker(max_consecutive_losses=3, max_drawdown_pct=0.1)
    cb.on_equity(100)
    cb.on_trade_pnl(-1)
    cb.on_trade_pnl(-1)
    assert cb.allow_new_risk()[0]
    cb.on_trade_pnl(-1)
    ok, reason = cb.allow_new_risk()
    assert not ok
    assert "consecutive_losses" in reason

    cb2 = CircuitBreaker(max_consecutive_losses=10, max_drawdown_pct=0.1)
    cb2.on_equity(100)
    cb2.on_equity(85)
    assert not cb2.allow_new_risk()[0]


def test_exposure_guard():
    guard = PortfolioExposureGuard(
        limits=[ExposureLimit(symbol="DEMO", max_qty=10, max_notional=1000)],
        max_gross_notional=5000,
    )
    assert guard.check("DEMO", 5, 100, 0)[0]
    assert not guard.check("DEMO", 20, 100, 0)[0]
    assert not guard.check("OTHER", 10, 100, 4500)[0]
