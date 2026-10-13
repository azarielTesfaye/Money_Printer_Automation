from __future__ import annotations

from money_printer.indicators import momentum
from money_printer.models import Bar, Side, Signal
from money_printer.strategies.base import Strategy


class MomentumBreakout(Strategy):
    """Enter long on strong positive momentum; exit on momentum fade."""

    name = "momentum"

    def __init__(
        self,
        lookback: int = 10,
        entry_threshold: float = 0.03,
        exit_threshold: float = 0.0,
        **_: float | int,
    ) -> None:
        super().__init__(
            lookback=lookback,
            entry_threshold=entry_threshold,
            exit_threshold=exit_threshold,
        )
        self.lookback = int(lookback)
        self.entry_threshold = float(entry_threshold)
        self.exit_threshold = float(exit_threshold)
        self._in_position = False

    def on_bar(self, bar: Bar, history: list[Bar]) -> Signal | None:
        closes = [b.close for b in history] + [bar.close]
        mom = momentum(closes, self.lookback)
        if mom is None:
            return None
        if not self._in_position and mom >= self.entry_threshold:
            self._in_position = True
            return Signal(
                symbol=bar.symbol,
                side=Side.BUY,
                strength=min(1.0, mom / max(self.entry_threshold, 1e-9)),
                reason=f"mom_entry:{mom:.4f}",
                ts=bar.ts,
            )
        if self._in_position and mom <= self.exit_threshold:
            self._in_position = False
            return Signal(
                symbol=bar.symbol,
                side=Side.SELL,
                reason=f"mom_exit:{mom:.4f}",
                ts=bar.ts,
            )
        return None
