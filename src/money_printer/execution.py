from __future__ import annotations

from datetime import datetime, timezone

from money_printer.config import ProfileSettings
from money_printer.models import Bar, Fill, Side, Signal
from money_printer.portfolio import Portfolio
from money_printer.risk import RiskGate
from money_printer.sizing import FixedFractionalSizer, PositionSizer


class PaperExecutor:
    def __init__(
        self,
        settings: ProfileSettings,
        risk: RiskGate,
        dry_run: bool = False,
        sizer: PositionSizer | None = None,
    ) -> None:
        self.settings = settings
        self.risk = risk
        self.dry_run = dry_run
        self.sizer = sizer or FixedFractionalSizer(fraction=settings.max_position_pct)

    def _slip_price(self, price: float, side: Side) -> float:
        slip = price * (self.settings.slippage_bps / 10_000.0)
        return price + slip if side == Side.BUY else price - slip

    def size_order(
        self,
        portfolio: Portfolio,
        equity: float,
        price: float,
        history: list[Bar] | None = None,
        signal_strength: float = 1.0,
    ) -> float:
        closes = [b.close for b in history] if history else None
        highs = [b.high for b in history] if history else None
        lows = [b.low for b in history] if history else None
        return self.sizer.size(
            equity=equity,
            price=price,
            cash=portfolio.cash,
            closes=closes,
            highs=highs,
            lows=lows,
            signal_strength=signal_strength,
        )

    def execute(
        self,
        signal: Signal,
        portfolio: Portfolio,
        price: float,
        equity: float,
        ts: datetime | None = None,
        history: list[Bar] | None = None,
    ) -> Fill | None:
        ok, reason = self.risk.allow(signal, portfolio, price, equity)
        if not ok:
            return None

        fill_ts = ts or signal.ts or datetime.now(timezone.utc)
        px = self._slip_price(price, signal.side)

        if signal.side == Side.BUY:
            qty = self.size_order(portfolio, equity, px, history=history, signal_strength=signal.strength)
            if qty <= 0:
                return None
        elif signal.side == Side.SELL:
            qty = portfolio.position(signal.symbol).qty
            if qty <= 0:
                return None
        else:
            return None

        fill = Fill(
            symbol=signal.symbol,
            side=signal.side,
            qty=qty,
            price=px,
            commission=self.settings.commission_per_fill,
            ts=fill_ts,
            reason=signal.reason or reason,
            dry_run=self.dry_run,
        )
        portfolio.apply_fill(fill)
        return fill
