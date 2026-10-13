from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from money_printer.models import Fill, Side


@dataclass(frozen=True)
class TradePnL:
    symbol: str
    qty: float
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float
    entry_ts: object
    exit_ts: object
    reason: str


def trade_attribution(fills: Sequence[Fill]) -> list[TradePnL]:
    """FIFO round-trip attribution across buys then sells."""
    inventory: dict[str, list[tuple[float, float, object, str]]] = {}
    trades: list[TradePnL] = []
    for f in fills:
        if f.dry_run:
            continue
        if f.side == Side.BUY:
            inventory.setdefault(f.symbol, []).append((f.qty, f.price, f.ts, f.reason))
            continue
        if f.side != Side.SELL:
            continue
        lots = inventory.get(f.symbol, [])
        remaining = f.qty
        while remaining > 1e-9 and lots:
            q, px, entry_ts, reason = lots[0]
            take = min(q, remaining)
            pnl = (f.price - px) * take
            ret = (f.price / px) - 1.0 if px else 0.0
            trades.append(
                TradePnL(
                    symbol=f.symbol,
                    qty=take,
                    entry_price=px,
                    exit_price=f.price,
                    pnl=pnl,
                    return_pct=ret,
                    entry_ts=entry_ts,
                    exit_ts=f.ts,
                    reason=reason or f.reason,
                )
            )
            q -= take
            remaining -= take
            if q <= 1e-9:
                lots.pop(0)
            else:
                lots[0] = (q, px, entry_ts, reason)
    return trades


def attribution_summary(fills: Sequence[Fill]) -> dict:
    trades = trade_attribution(fills)
    if not trades:
        return {
            "n_trades": 0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "net_pnl": 0.0,
            "profit_factor": 0.0,
            "avg_trade_pnl": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "by_symbol": {},
        }
    profits = [t.pnl for t in trades if t.pnl > 0]
    losses = [t.pnl for t in trades if t.pnl <= 0]
    gross_profit = sum(profits)
    gross_loss = abs(sum(losses))
    by_symbol: dict[str, float] = {}
    for t in trades:
        by_symbol[t.symbol] = by_symbol.get(t.symbol, 0.0) + t.pnl
    return {
        "n_trades": len(trades),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_pnl": sum(t.pnl for t in trades),
        "profit_factor": (gross_profit / gross_loss) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0,
        "avg_trade_pnl": sum(t.pnl for t in trades) / len(trades),
        "best_trade": max(t.pnl for t in trades),
        "worst_trade": min(t.pnl for t in trades),
        "by_symbol": by_symbol,
    }
