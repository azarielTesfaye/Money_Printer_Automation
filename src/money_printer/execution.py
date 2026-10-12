from __future__ import annotations

from datetime import datetime, timezone

from money_printer.config import ProfileSettings
from money_printer.models import Fill, Side, Signal
from money_printer.portfolio import Portfolio
from money_printer.risk import RiskGate


class PaperExecutor:
    def __init__(self, settings: ProfileSettings, risk: RiskGate, dry_run: bool = False) -> None:
        self.settings = settings
        self.risk = risk
        self.dry_run = dry_run

    def _slip_price(self, price: float, side: Side) -> float:
        slip = price * (self.settings.slippage_bps / 10_000.0)
        return price + slip if side == Side.BUY else price - slip

    def size_order(self, portfolio: Portfolio, equity: float, price: float) -> float:
        budget = equity * self.settings.max_position_pct
        qty = budget / max(price, 1e-9)
        # spend at most available cash on buys
        max_by_cash = portfolio.cash / max(price, 1e-9)
        return max(0.0, min(qty, max_by_cash))

    def execute(
        self,
        signal: Signal,
        portfolio: Portfolio,
        price: float,
        equity: float,
        ts: datetime | None = None,
    ) -> Fill | None:
        ok, reason = self.risk.allow(signal, portfolio, price, equity)
        if not ok:
            return None

        fill_ts = ts or signal.ts or datetime.now(timezone.utc)
        px = self._slip_price(price, signal.side)

        if signal.side == Side.BUY:
            qty = self.size_order(portfolio, equity, px)
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
