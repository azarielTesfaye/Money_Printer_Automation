from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Sequence


def _to_dt(ts: object) -> datetime | None:
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return None
    return None


def _period_returns(
    equity_curve: Sequence[tuple[object, float]],
    key_fn,
) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for ts, equity in equity_curve:
        dt = _to_dt(ts)
        if dt is None:
            continue
        buckets[key_fn(dt)].append(equity)
    out: dict[str, float] = {}
    for key, vals in sorted(buckets.items()):
        if len(vals) < 2 or vals[0] == 0:
            out[key] = 0.0
        else:
            out[key] = (vals[-1] / vals[0]) - 1.0
    return out


def monthly_returns(equity_curve: Sequence[tuple[object, float]]) -> dict[str, float]:
    return _period_returns(equity_curve, lambda dt: f"{dt.year:04d}-{dt.month:02d}")


def yearly_returns(equity_curve: Sequence[tuple[object, float]]) -> dict[str, float]:
    return _period_returns(equity_curve, lambda dt: f"{dt.year:04d}")
