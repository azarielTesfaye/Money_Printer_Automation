from __future__ import annotations

from money_printer.indicators import bollinger
from money_printer.models import Bar, Side, Signal
from money_printer.strategies.base import Strategy


class BollingerMeanReversion(Strategy):
    """Buy when price pierces lower band; sell when it pierces upper band."""

    name = "bollinger"

    def __init__(
        self,
        window: int = 20,
        num_std: float = 2.0,
        **_: float | int,
    ) -> None:
        super().__init__(window=window, num_std=num_std)
        self.window = int(window)
        self.num_std = float(num_std)
        self._last_side: Side | None = None

    def on_bar(self, bar: Bar, history: list[Bar]) -> Signal | None:
        closes = [b.close for b in history] + [bar.close]
        lower, mid, upper = bollinger(closes, self.window, self.num_std)
        if lower is None or upper is None or mid is None:
            return None
        if bar.close <= lower and self._last_side != Side.BUY:
            self._last_side = Side.BUY
            return Signal(
                symbol=bar.symbol,
                side=Side.BUY,
                reason=f"bb_lower:{bar.close:.4f}<={lower:.4f}",
                ts=bar.ts,
            )
        if bar.close >= upper and self._last_side != Side.SELL:
            self._last_side = Side.SELL
            return Signal(
                symbol=bar.symbol,
                side=Side.SELL,
                reason=f"bb_upper:{bar.close:.4f}>={upper:.4f}",
                ts=bar.ts,
            )
        return None
