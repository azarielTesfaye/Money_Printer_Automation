from __future__ import annotations

from pathlib import Path

from money_printer.config import ProfileSettings
from money_printer.models import Side, Signal
from money_printer.portfolio import Portfolio


class RiskGate:
    def __init__(self, settings: ProfileSettings) -> None:
        self.settings = settings
        self._day_start_equity: float | None = None

    def set_day_start(self, equity: float) -> None:
        self._day_start_equity = equity

    def kill_switch_active(self) -> bool:
        return Path(self.settings.stop_file).exists()

    def allow(self, signal: Signal, portfolio: Portfolio, price: float, equity: float) -> tuple[bool, str]:
        if self.kill_switch_active():
            return False, "kill_switch"

        if self._day_start_equity is None:
            self._day_start_equity = equity
        day_loss = (self._day_start_equity - equity) / max(self._day_start_equity, 1e-9)
        if day_loss >= self.settings.max_daily_loss_pct:
            return False, "max_daily_loss"

        pos = portfolio.position(signal.symbol)
        if signal.side == Side.BUY:
            if pos.qty <= 0 and portfolio.open_count() >= self.settings.max_open_positions:
                return False, "max_open_positions"
            max_notional = equity * self.settings.max_position_pct
            if price * 1.0 > max_notional and pos.qty <= 0:
                # sizing handled in executor; here we only block absurd cash
                if portfolio.cash < price:
                    return False, "insufficient_cash"
        return True, "ok"
