from datetime import datetime, timedelta

from money_printer.models import Bar
from money_printer.strategies.atr_breakout import AtrChannelBreakout
from money_printer.strategies.bollinger import BollingerMeanReversion
from money_printer.strategies.macd import MacdCrossover
from money_printer.strategies.momentum import MomentumBreakout


def _bars(closes: list[float], symbol: str = "DEMO") -> list[Bar]:
    start = datetime(2024, 1, 1)
    out = []
    for i, c in enumerate(closes):
        out.append(
            Bar(
                symbol=symbol,
                ts=start + timedelta(days=i),
                open=c,
                high=c * 1.01,
                low=c * 0.99,
                close=c,
                volume=1000,
            )
        )
    return out


def _run(strategy, closes):
    bars = _bars(closes)
    history = []
    signals = []
    for bar in bars:
        sig = strategy.on_bar(bar, history)
        if sig:
            signals.append(sig)
        history.append(bar)
    return signals


def test_macd_emits_on_trend_change():
    # prolonged down then sharp up to force histogram sign change
    closes = [100 - i * 0.5 for i in range(40)] + [80 + i for i in range(40)]
    signals = _run(MacdCrossover(fast=5, slow=15, signal=5), closes)
    assert any(s.side.value == "buy" for s in signals)


def test_bollinger_mean_reversion_triggers():
    base = [100.0] * 25
    spike_down = base + [70.0, 70.0]
    signals = _run(BollingerMeanReversion(window=20, num_std=2.0), spike_down)
    assert any(s.side.value == "buy" for s in signals)


def test_momentum_entry_and_exit():
    flat = [100.0] * 12
    rally = flat + [100 * (1.05) ** i for i in range(1, 15)]
    fade = rally + [rally[-1] * 0.99 for _ in range(15)]
    signals = _run(
        MomentumBreakout(lookback=5, entry_threshold=0.02, exit_threshold=0.0),
        fade,
    )
    sides = [s.side.value for s in signals]
    assert "buy" in sides


def test_atr_breakout_runs_without_error():
    closes = [100 + (i % 7) - 3 for i in range(80)]
    signals = _run(AtrChannelBreakout(channel=10, atr_period=5, atr_mult=0.5), closes)
    assert isinstance(signals, list)
