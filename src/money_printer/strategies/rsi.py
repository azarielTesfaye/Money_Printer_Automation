from __future__ import annotations

from money_printer.models import Bar, Side, Signal
from money_printer.strategies.base import Strategy


def rsi(closes: list[float], period: int) -> float | None:
    if len(closes) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    window = closes[-(period + 1) :]
    for i in range(1, len(window)):
        delta = window[i] - window[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


class RsiMeanReversion(Strategy):
    name = "rsi"

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
        **_: float | int,
    ) -> None:
        super().__init__(period=period, oversold=oversold, overbought=overbought)
        self.period = int(period)
        self.oversold = float(oversold)
        self.overbought = float(overbought)
        self._last_side: Side | None = None

    def on_bar(self, bar: Bar, history: list[Bar]) -> Signal | None:
        closes = [b.close for b in history] + [bar.close]
        value = rsi(closes, self.period)
        if value is None:
            return None
        if value <= self.oversold and self._last_side != Side.BUY:
            self._last_side = Side.BUY
            return Signal(symbol=bar.symbol, side=Side.BUY, reason=f"rsi_oversold:{value:.1f}", ts=bar.ts)
        if value >= self.overbought and self._last_side != Side.SELL:
            self._last_side = Side.SELL
            return Signal(symbol=bar.symbol, side=Side.SELL, reason=f"rsi_overbought:{value:.1f}", ts=bar.ts)
        return None
