from __future__ import annotations

from money_printer.models import Fill, Position, Side


class Portfolio:
    def __init__(self, cash: float) -> None:
        self.cash = cash
        self.starting_cash = cash
        self.positions: dict[str, Position] = {}
        self.fills: list[Fill] = []
        self.equity_curve: list[tuple[object, float]] = []

    def position(self, symbol: str) -> Position:
        return self.positions.get(symbol, Position(symbol=symbol))

    def open_count(self) -> int:
        return sum(1 for p in self.positions.values() if abs(p.qty) > 1e-9)

    def mark_to_market(self, prices: dict[str, float], ts: object) -> float:
        equity = self.cash
        for sym, pos in self.positions.items():
            px = prices.get(sym, pos.avg_cost)
            equity += pos.qty * px
        self.equity_curve.append((ts, equity))
        return equity

    def apply_fill(self, fill: Fill) -> None:
        if fill.dry_run:
            self.fills.append(fill)
            return

        pos = self.positions.get(fill.symbol, Position(symbol=fill.symbol))
        notional = fill.qty * fill.price

        if fill.side == Side.BUY:
            new_qty = pos.qty + fill.qty
            if new_qty > 0:
                pos.avg_cost = ((pos.qty * pos.avg_cost) + notional) / new_qty
            pos.qty = new_qty
            self.cash -= notional + fill.commission
        elif fill.side == Side.SELL:
            pos.qty -= fill.qty
            self.cash += notional - fill.commission
            if abs(pos.qty) < 1e-9:
                pos.qty = 0.0
                pos.avg_cost = 0.0

        self.positions[fill.symbol] = pos
        self.fills.append(fill)
