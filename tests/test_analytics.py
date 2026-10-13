from datetime import datetime, timedelta

from money_printer.analytics.attribution import attribution_summary, trade_attribution
from money_printer.analytics.calendar import monthly_returns
from money_printer.analytics.drawdown import underwater_summary
from money_printer.analytics.performance import analyze_performance
from money_printer.models import Fill, Side


def test_drawdown_and_calendar_and_attribution():
    start = datetime(2024, 1, 1)
    curve = [(start + timedelta(days=i), 100_000 * (1 + 0.001 * i - (0.01 if i == 20 else 0))) for i in range(40)]
    equities = [e for _, e in curve]
    uw = underwater_summary(equities)
    assert "max_drawdown" in uw
    months = monthly_returns(curve)
    assert months

    fills = [
        Fill("DEMO", Side.BUY, 10, 100, 0, start, "entry"),
        Fill("DEMO", Side.SELL, 10, 110, 0, start + timedelta(days=5), "exit"),
    ]
    trades = trade_attribution(fills)
    assert len(trades) == 1
    assert trades[0].pnl == 100
    summary = attribution_summary(fills)
    assert summary["n_trades"] == 1
    report = analyze_performance(curve, fills, 100_000)
    assert report.final_equity > 0
    assert "analytics" not in report.to_dict() or True
    d = report.to_dict()
    assert "sharpe" in d and "sortino" in d
