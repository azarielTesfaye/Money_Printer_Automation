from __future__ import annotations

import math
from typing import Sequence

from money_printer.models import Fill, Side


def max_drawdown(equity: Sequence[float]) -> float:
    if not equity:
        return 0.0
    peak = equity[0]
    worst = 0.0
    for v in equity:
        peak = max(peak, v)
        dd = (peak - v) / peak if peak else 0.0
        worst = max(worst, dd)
    return worst


def sharpe(returns: Sequence[float], periods_per_year: float = 252.0) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(periods_per_year)


def win_rate(fills: Sequence[Fill]) -> float:
    # Approximate: pair buys then sells on same symbol FIFO PnL sign
    inventory: dict[str, list[tuple[float, float]]] = {}
    wins = 0
    trades = 0
    for f in fills:
        if f.dry_run:
            continue
        if f.side == Side.BUY:
            inventory.setdefault(f.symbol, []).append((f.qty, f.price))
        elif f.side == Side.SELL:
            lots = inventory.get(f.symbol, [])
            remaining = f.qty
            while remaining > 1e-9 and lots:
                q, px = lots[0]
                take = min(q, remaining)
                pnl = (f.price - px) * take
                trades += 1
                if pnl > 0:
                    wins += 1
                q -= take
                remaining -= take
                if q <= 1e-9:
                    lots.pop(0)
                else:
                    lots[0] = (q, px)
    return (wins / trades) if trades else 0.0


def summarize(equity_curve: list[tuple[object, float]], fills: list[Fill], starting_cash: float) -> dict:
    equities = [e for _, e in equity_curve]
    returns: list[float] = []
    for i in range(1, len(equities)):
        prev = equities[i - 1]
        returns.append((equities[i] - prev) / prev if prev else 0.0)
    final = equities[-1] if equities else starting_cash
    return {
        "starting_cash": starting_cash,
        "final_equity": final,
        "total_return_pct": (final - starting_cash) / starting_cash if starting_cash else 0.0,
        "max_drawdown": max_drawdown(equities),
        "sharpe": sharpe(returns),
        "win_rate": win_rate(fills),
        "n_fills": len([f for f in fills if not f.dry_run]),
        "n_bars": len(equities),
    }
