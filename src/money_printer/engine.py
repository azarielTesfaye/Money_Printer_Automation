from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from money_printer.analytics.performance import analyze_performance
from money_printer.config import ProfileSettings
from money_printer.data.base import MarketDataProvider
from money_printer.execution import PaperExecutor
from money_printer.journal import TradeJournal
from money_printer.metrics import summarize
from money_printer.portfolio import Portfolio
from money_printer.risk import RiskGate
from money_printer.sizing import PositionSizer
from money_printer.strategies.base import Strategy


class BacktestEngine:
    def __init__(
        self,
        settings: ProfileSettings,
        strategy: Strategy,
        provider: MarketDataProvider,
        dry_run: bool = False,
        journal: TradeJournal | None = None,
        sizer: PositionSizer | None = None,
        rich_analytics: bool = False,
    ) -> None:
        self.settings = settings
        self.strategy = strategy
        self.provider = provider
        self.dry_run = dry_run
        self.journal = journal
        self.rich_analytics = rich_analytics
        self.portfolio = Portfolio(settings.starting_cash)
        self.risk = RiskGate(settings)
        self.executor = PaperExecutor(settings, self.risk, dry_run=dry_run, sizer=sizer)

    def run(self, symbol: str, start: datetime | None = None, end: datetime | None = None) -> dict:
        bars = self.provider.history(symbol, start=start, end=end)
        if not bars:
            raise ValueError(f"No bars for {symbol}")

        history: list = []
        first_equity = self.settings.starting_cash
        self.risk.set_day_start(first_equity)

        for bar in bars:
            signal = self.strategy.on_bar(bar, history)
            prices = {bar.symbol: bar.close}
            equity = self.portfolio.mark_to_market(prices, bar.ts)
            if signal is not None:
                fill = self.executor.execute(
                    signal,
                    self.portfolio,
                    bar.close,
                    equity,
                    ts=bar.ts,
                    history=history + [bar],
                )
                if fill and self.journal is not None:
                    self.journal.append(fill)
            history.append(bar)

        report = summarize(self.portfolio.equity_curve, self.portfolio.fills, self.settings.starting_cash)
        report["symbol"] = symbol
        report["strategy"] = self.strategy.name
        report["dry_run"] = self.dry_run
        if self.rich_analytics:
            perf = analyze_performance(
                self.portfolio.equity_curve,
                self.portfolio.fills,
                self.settings.starting_cash,
            )
            report["analytics"] = perf.to_dict()
        return report


def write_report(report: dict, out_dir: str | Path = "reports") -> Path:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    name = f"backtest_{report.get('strategy', 'na')}_{report.get('symbol', 'na')}_{stamp}.json"
    out = path / name
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    md = path / name.replace(".json", ".md")
    lines = [
        f"# Backtest {report.get('strategy')} / {report.get('symbol')}",
        "",
        f"- Final equity: {report.get('final_equity'):.2f}",
        f"- Total return: {100 * report.get('total_return_pct', 0):.2f}%",
        f"- Max drawdown: {100 * report.get('max_drawdown', 0):.2f}%",
        f"- Sharpe: {report.get('sharpe', 0):.3f}",
        f"- Win rate: {100 * report.get('win_rate', 0):.1f}%",
        f"- Fills: {report.get('n_fills')}",
    ]
    analytics = report.get("analytics") or {}
    if analytics:
        lines.extend(
            [
                "",
                "## Analytics",
                f"- CAGR: {100 * analytics.get('cagr', 0):.2f}%",
                f"- Sortino: {analytics.get('sortino', 0):.3f}",
                f"- Calmar: {analytics.get('calmar', 0):.3f}",
                f"- Volatility: {100 * analytics.get('volatility', 0):.2f}%",
            ]
        )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out
