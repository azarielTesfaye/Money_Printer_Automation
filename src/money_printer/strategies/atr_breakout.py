from __future__ import annotations

from money_printer.indicators import atr, rolling_max, rolling_min
from money_printer.models import Bar, Side, Signal
from money_printer.strategies.base import Strategy


class AtrChannelBreakout(Strategy):
    """Donchian-style breakout confirmed by ATR expansion."""

    name = "atr_breakout"

    def __init__(
        self,
        channel: int = 20,
        atr_period: int = 14,
        atr_mult: float = 1.5,
        **_: float | int,
    ) -> None:
        super().__init__(channel=channel, atr_period=atr_period, atr_mult=atr_mult)
        self.channel = int(channel)
        self.atr_period = int(atr_period)
        self.atr_mult = float(atr_mult)
        self._in_position = False

    def on_bar(self, bar: Bar, history: list[Bar]) -> Signal | None:
        if not history:
            return None
        highs = [b.high for b in history]
        lows = [b.low for b in history]
        closes = [b.close for b in history] + [bar.close]
        # prior channel excludes current bar
        prior_high = rolling_max(highs, self.channel)
        prior_low = rolling_min(lows, self.channel)
        atr_v = atr(
            [b.high for b in history] + [bar.high],
            [b.low for b in history] + [bar.low],
            closes,
            self.atr_period,
        )
        if prior_high is None or prior_low is None or atr_v is None:
            return None

        range_width = prior_high - prior_low
        expanded = range_width >= self.atr_mult * atr_v

        if not self._in_position and expanded and bar.close > prior_high:
            self._in_position = True
            return Signal(
                symbol=bar.symbol,
                side=Side.BUY,
                reason=f"atr_break_up:{bar.close:.4f}>{prior_high:.4f}",
                ts=bar.ts,
            )
        if self._in_position and bar.close < prior_low:
            self._in_position = False
            return Signal(
                symbol=bar.symbol,
                side=Side.SELL,
                reason=f"atr_break_down:{bar.close:.4f}<{prior_low:.4f}",
                ts=bar.ts,
            )
        return None
