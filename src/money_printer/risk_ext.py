from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CircuitBreaker:
    """Trip after N consecutive losses or a hard equity drawdown from peak."""

    max_consecutive_losses: int = 5
    max_drawdown_pct: float = 0.15
    consecutive_losses: int = 0
    peak_equity: float = 0.0
    tripped: bool = False
    reason: str = ""
    tripped_at: datetime | None = None
    history: list[dict] = field(default_factory=list)

    def reset(self) -> None:
        self.consecutive_losses = 0
        self.tripped = False
        self.reason = ""
        self.tripped_at = None

    def on_trade_pnl(self, pnl: float) -> None:
        if self.tripped:
            return
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        if self.consecutive_losses >= self.max_consecutive_losses:
            self._trip(f"consecutive_losses:{self.consecutive_losses}")

    def on_equity(self, equity: float) -> None:
        if equity > self.peak_equity:
            self.peak_equity = equity
        if self.peak_equity <= 0 or self.tripped:
            return
        dd = (self.peak_equity - equity) / self.peak_equity
        if dd >= self.max_drawdown_pct:
            self._trip(f"max_drawdown:{dd:.4f}")

    def _trip(self, reason: str) -> None:
        self.tripped = True
        self.reason = reason
        self.tripped_at = datetime.now(timezone.utc)
        self.history.append({"reason": reason, "ts": self.tripped_at.isoformat()})

    def allow_new_risk(self) -> tuple[bool, str]:
        if self.tripped:
            return False, self.reason or "circuit_open"
        return True, "ok"


@dataclass
class ExposureLimit:
    symbol: str
    max_qty: float
    max_notional: float

    def check(self, qty: float, price: float) -> tuple[bool, str]:
        if qty > self.max_qty:
            return False, "symbol_qty_limit"
        if qty * price > self.max_notional:
            return False, "symbol_notional_limit"
        return True, "ok"


class PortfolioExposureGuard:
    def __init__(self, limits: list[ExposureLimit] | None = None, max_gross_notional: float = 1_000_000.0) -> None:
        self.limits = {l.symbol.upper(): l for l in (limits or [])}
        self.max_gross_notional = max_gross_notional

    def check(self, symbol: str, qty: float, price: float, current_gross: float) -> tuple[bool, str]:
        lim = self.limits.get(symbol.upper())
        if lim is not None:
            ok, reason = lim.check(qty, price)
            if not ok:
                return ok, reason
        if current_gross + qty * price > self.max_gross_notional:
            return False, "gross_notional_limit"
        return True, "ok"
