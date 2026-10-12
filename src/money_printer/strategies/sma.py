from __future__ import annotations

from money_printer.models import Bar, Side, Signal
from money_printer.strategies.base import Strategy


def _sma(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


class SmaCrossover(Strategy):
    name = "sma"

    def __init__(self, fast: int = 5, slow: int = 20, **_: float | int) -> None:
        if fast >= slow:
            raise ValueError("fast must be < slow")
        super().__init__(fast=fast, slow=slow)
        self.fast = int(fast)
        self.slow = int(slow)
        self._prev_diff: float | None = None

    def on_bar(self, bar: Bar, history: list[Bar]) -> Signal | None:
        closes = [b.close for b in history] + [bar.close]
        fast = _sma(closes, self.fast)
        slow = _sma(closes, self.slow)
        if fast is None or slow is None:
            return None
        diff = fast - slow
        signal: Signal | None = None
        if self._prev_diff is not None:
            if self._prev_diff <= 0 < diff:
                signal = Signal(symbol=bar.symbol, side=Side.BUY, reason="sma_cross_up", ts=bar.ts)
            elif self._prev_diff >= 0 > diff:
                signal = Signal(symbol=bar.symbol, side=Side.SELL, reason="sma_cross_down", ts=bar.ts)
        self._prev_diff = diff
        return signal
