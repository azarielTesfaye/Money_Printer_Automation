from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class DrawdownPoint:
    index: int
    equity: float
    peak: float
    drawdown: float


def drawdown_series(equity: Sequence[float]) -> list[DrawdownPoint]:
    if not equity:
        return []
    peak = equity[0]
    out: list[DrawdownPoint] = []
    for i, v in enumerate(equity):
        peak = max(peak, v)
        dd = (peak - v) / peak if peak else 0.0
        out.append(DrawdownPoint(index=i, equity=v, peak=peak, drawdown=dd))
    return out


def underwater_summary(equity: Sequence[float]) -> dict:
    series = drawdown_series(equity)
    if not series:
        return {
            "max_drawdown": 0.0,
            "max_drawdown_index": None,
            "time_underwater_bars": 0,
            "longest_underwater_bars": 0,
            "avg_drawdown": 0.0,
        }
    max_dd = 0.0
    max_idx: int | None = None
    underwater = 0
    longest = 0
    streak = 0
    total_dd = 0.0
    for p in series:
        total_dd += p.drawdown
        if p.drawdown > max_dd:
            max_dd = p.drawdown
            max_idx = p.index
        if p.drawdown > 1e-12:
            underwater += 1
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 0
    return {
        "max_drawdown": max_dd,
        "max_drawdown_index": max_idx,
        "time_underwater_bars": underwater,
        "longest_underwater_bars": longest,
        "avg_drawdown": total_dd / len(series),
    }
