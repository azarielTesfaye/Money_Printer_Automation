from __future__ import annotations

from money_printer.indicators import macd
from money_printer.models import Bar, Side, Signal
from money_printer.strategies.base import Strategy


class MacdCrossover(Strategy):
    """Buy when MACD crosses above signal; sell when it crosses below."""

    name = "macd"

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        **_: float | int,
    ) -> None:
        if fast >= slow:
            raise ValueError("fast must be < slow")
        super().__init__(fast=fast, slow=slow, signal=signal)
        self.fast = int(fast)
        self.slow = int(slow)
        self.signal_n = int(signal)
        self._prev_hist: float | None = None

    def on_bar(self, bar: Bar, history: list[Bar]) -> Signal | None:
        closes = [b.close for b in history] + [bar.close]
        line, sig, hist = macd(closes, self.fast, self.slow, self.signal_n)
        if hist is None:
            return None
        out: Signal | None = None
        if self._prev_hist is not None:
            if self._prev_hist <= 0 < hist:
                out = Signal(symbol=bar.symbol, side=Side.BUY, reason="macd_cross_up", ts=bar.ts)
            elif self._prev_hist >= 0 > hist:
                out = Signal(symbol=bar.symbol, side=Side.SELL, reason="macd_cross_down", ts=bar.ts)
        self._prev_hist = hist
        return out
