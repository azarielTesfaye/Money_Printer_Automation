from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Sequence

from money_printer.analytics.attribution import attribution_summary
from money_printer.analytics.calendar import monthly_returns, yearly_returns
from money_printer.analytics.drawdown import underwater_summary
from money_printer.metrics import max_drawdown, sharpe, win_rate
from money_printer.models import Fill


def _returns_from_equity(equity: Sequence[float]) -> list[float]:
    rets: list[float] = []
    for i in range(1, len(equity)):
        prev = equity[i - 1]
        rets.append((equity[i] - prev) / prev if prev else 0.0)
    return rets


def sortino(returns: Sequence[float], periods_per_year: float = 252.0, target: float = 0.0) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    downside = [(min(0.0, r - target)) ** 2 for r in returns]
    down_dev = math.sqrt(sum(downside) / (len(returns) - 1))
    if down_dev == 0:
        return 0.0
    return ((mean - target) / down_dev) * math.sqrt(periods_per_year)


def calmar(total_return: float, max_dd: float, years: float) -> float:
    if max_dd <= 0 or years <= 0:
        return 0.0
    cagr = (1.0 + total_return) ** (1.0 / years) - 1.0 if total_return > -1 else -1.0
    return cagr / max_dd


def volatility(returns: Sequence[float], periods_per_year: float = 252.0) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(var) * math.sqrt(periods_per_year)


@dataclass
class PerformanceReport:
    starting_cash: float
    final_equity: float
    total_return_pct: float
    cagr: float
    sharpe: float
    sortino: float
    calmar: float
    volatility: float
    max_drawdown: float
    win_rate: float
    n_fills: int
    n_bars: int
    underwater: dict
    attribution: dict
    monthly_returns: dict[str, float]
    yearly_returns: dict[str, float]

    def to_dict(self) -> dict:
        return asdict(self)


def analyze_performance(
    equity_curve: list[tuple[object, float]],
    fills: list[Fill],
    starting_cash: float,
    periods_per_year: float = 252.0,
) -> PerformanceReport:
    equities = [e for _, e in equity_curve]
    rets = _returns_from_equity(equities)
    final = equities[-1] if equities else starting_cash
    total_ret = (final - starting_cash) / starting_cash if starting_cash else 0.0
    years = (len(equities) / periods_per_year) if equities else 0.0
    cagr = (1.0 + total_ret) ** (1.0 / years) - 1.0 if years > 0 and total_ret > -1 else 0.0
    dd = max_drawdown(equities)
    return PerformanceReport(
        starting_cash=starting_cash,
        final_equity=final,
        total_return_pct=total_ret,
        cagr=cagr,
        sharpe=sharpe(rets, periods_per_year),
        sortino=sortino(rets, periods_per_year),
        calmar=calmar(total_ret, dd, years if years > 0 else 1.0),
        volatility=volatility(rets, periods_per_year),
        max_drawdown=dd,
        win_rate=win_rate(fills),
        n_fills=len([f for f in fills if not f.dry_run]),
        n_bars=len(equities),
        underwater=underwater_summary(equities),
        attribution=attribution_summary(fills),
        monthly_returns=monthly_returns(equity_curve),
        yearly_returns=yearly_returns(equity_curve),
    )
