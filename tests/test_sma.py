from datetime import datetime, timedelta

from money_printer.models import Bar
from money_printer.strategies.sma import SmaCrossover


def _bars(closes: list[float], symbol: str = "DEMO") -> list[Bar]:
    start = datetime(2024, 1, 1)
    out = []
    for i, c in enumerate(closes):
        out.append(
            Bar(
                symbol=symbol,
                ts=start + timedelta(days=i),
                open=c,
                high=c,
                low=c,
                close=c,
                volume=1,
            )
        )
    return out


def test_sma_cross_up_and_down():
    # flat then jump above, then drop — with fast=2 slow=4
    closes = [10, 10, 10, 10, 10, 12, 12, 12, 12, 8, 8, 8, 8]
    bars = _bars(closes)
    strat = SmaCrossover(fast=2, slow=4)
    signals = []
    history: list[Bar] = []
    for bar in bars:
        sig = strat.on_bar(bar, history)
        if sig:
            signals.append(sig)
        history.append(bar)
    sides = [s.side.value for s in signals]
    assert "buy" in sides
    assert "sell" in sides
