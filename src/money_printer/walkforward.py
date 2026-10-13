from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from money_printer.config import ProfileSettings
from money_printer.data.base import MarketDataProvider
from money_printer.engine import BacktestEngine
from money_printer.models import Bar
from money_printer.strategies.base import Strategy


@dataclass(frozen=True)
class WalkForwardWindow:
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime


@dataclass
class WalkForwardResult:
    windows: list[dict]
    aggregate: dict


def build_windows(
    bars: list[Bar],
    train_bars: int,
    test_bars: int,
    step_bars: int | None = None,
) -> list[WalkForwardWindow]:
    if train_bars <= 0 or test_bars <= 0:
        raise ValueError("train_bars and test_bars must be positive")
    step = step_bars or test_bars
    windows: list[WalkForwardWindow] = []
    i = 0
    while i + train_bars + test_bars <= len(bars):
        train = bars[i : i + train_bars]
        test = bars[i + train_bars : i + train_bars + test_bars]
        windows.append(
            WalkForwardWindow(
                train_start=train[0].ts,
                train_end=train[-1].ts,
                test_start=test[0].ts,
                test_end=test[-1].ts,
            )
        )
        i += step
    return windows


class SliceProvider(MarketDataProvider):
    """Provider that returns a fixed bar slice for one walk-forward fold."""

    def __init__(self, bars: list[Bar]) -> None:
        self._bars = bars

    def history(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Bar]:
        out = self._bars
        if start:
            out = [b for b in out if b.ts >= start]
        if end:
            out = [b for b in out if b.ts <= end]
        return out


def run_walk_forward(
    settings: ProfileSettings,
    strategy_factory: Callable[[], Strategy],
    provider: MarketDataProvider,
    symbol: str,
    train_bars: int = 40,
    test_bars: int = 20,
    step_bars: int | None = None,
    dry_run: bool = False,
) -> WalkForwardResult:
    bars = provider.history(symbol)
    if len(bars) < train_bars + test_bars:
        raise ValueError(
            f"Need at least {train_bars + test_bars} bars, got {len(bars)}"
        )
    windows = build_windows(bars, train_bars, test_bars, step_bars)
    fold_reports: list[dict] = []
    equity_parts: list[float] = []
    for idx, w in enumerate(windows):
        test_bars_data = [b for b in bars if w.test_start <= b.ts <= w.test_end]
        engine = BacktestEngine(
            settings,
            strategy_factory(),
            SliceProvider(test_bars_data),
            dry_run=dry_run,
        )
        report = engine.run(symbol)
        report["fold"] = idx
        report["train_start"] = w.train_start.isoformat()
        report["train_end"] = w.train_end.isoformat()
        report["test_start"] = w.test_start.isoformat()
        report["test_end"] = w.test_end.isoformat()
        fold_reports.append(report)
        equity_parts.append(float(report.get("final_equity", settings.starting_cash)))

    if not fold_reports:
        aggregate = {"n_folds": 0}
    else:
        avg_ret = sum(r.get("total_return_pct", 0.0) for r in fold_reports) / len(fold_reports)
        avg_sharpe = sum(r.get("sharpe", 0.0) for r in fold_reports) / len(fold_reports)
        avg_dd = sum(r.get("max_drawdown", 0.0) for r in fold_reports) / len(fold_reports)
        aggregate = {
            "n_folds": len(fold_reports),
            "avg_total_return_pct": avg_ret,
            "avg_sharpe": avg_sharpe,
            "avg_max_drawdown": avg_dd,
            "fold_final_equities": equity_parts,
        }
    return WalkForwardResult(windows=fold_reports, aggregate=aggregate)
