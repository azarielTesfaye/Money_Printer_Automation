from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from money_printer.config import load_profile
from money_printer.data.csv_replay import CsvReplayProvider
from money_printer.engine import BacktestEngine, write_report
from money_printer.health import write_health
from money_printer.journal import TradeJournal
from money_printer.logging_setup import setup_logging
from money_printer.notifier import WebhookNotifier
from money_printer.scheduler import DaemonLoop
from money_printer.sizing import build_sizer
import money_printer.strategies  # noqa: F401 — register strategies
from money_printer.strategies import registry
from money_printer.walkforward import run_walk_forward

STRATEGY_CHOICES = ["sma", "rsi", "macd", "bollinger", "momentum", "atr_breakout"]


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    return datetime.strptime(raw, "%Y-%m-%d")


def cmd_backtest(args: argparse.Namespace) -> int:
    env, profile, strategies_cfg = load_profile(args.profile)
    setup_logging(env.log_level)
    params = dict(strategies_cfg.get(args.strategy, {}))
    strategy = registry.create(args.strategy, **params)
    provider = CsvReplayProvider(args.csv, symbol=args.symbol)
    journal = TradeJournal(profile.journal_path) if not args.no_journal else None
    sizer = None
    if args.sizer:
        kv = {}
        for raw in args.sizer_param or []:
            k, v = raw.split("=", 1)
            kv[k] = float(v)
        sizer = build_sizer(args.sizer, **kv)
    engine = BacktestEngine(
        profile,
        strategy,
        provider,
        dry_run=args.dry_run,
        journal=journal,
        sizer=sizer,
        rich_analytics=args.analytics,
    )
    report = engine.run(args.symbol, start=_parse_date(args.start), end=_parse_date(args.end))
    out = write_report(report, args.reports_dir)
    write_health(profile.health_path, ok=True, extra={"last_report": str(out)})
    if env.webhook_url:
        WebhookNotifier(env.webhook_url).send("backtest complete", report)
    print(out)
    if journal:
        journal.close()
    return 0


def cmd_walkforward(args: argparse.Namespace) -> int:
    env, profile, strategies_cfg = load_profile(args.profile)
    setup_logging(env.log_level)
    params = dict(strategies_cfg.get(args.strategy, {}))
    provider = CsvReplayProvider(args.csv, symbol=args.symbol)

    def factory():
        return registry.create(args.strategy, **params)

    result = run_walk_forward(
        profile,
        factory,
        provider,
        args.symbol,
        train_bars=args.train_bars,
        test_bars=args.test_bars,
        step_bars=args.step_bars,
        dry_run=args.dry_run,
    )
    out_dir = Path(args.reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out_dir / f"walkforward_{args.strategy}_{args.symbol}_{stamp}.json"
    payload = {"aggregate": result.aggregate, "windows": result.windows}
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(path)
    print(json.dumps(result.aggregate, indent=2))
    return 0


def cmd_daemon(args: argparse.Namespace) -> int:
    env, profile, strategies_cfg = load_profile(args.profile)
    setup_logging(env.log_level)
    params = dict(strategies_cfg.get(args.strategy, {}))
    strategy = registry.create(args.strategy, **params)
    provider = CsvReplayProvider(args.csv, symbol=args.symbol)
    loop = DaemonLoop(
        profile,
        strategy,
        provider,
        args.symbol,
        notifier=WebhookNotifier(env.webhook_url),
        dry_run=args.dry_run,
    )
    loop.run_forever()
    return 0


def cmd_strategies(_: argparse.Namespace) -> int:
    for name in registry.names():
        print(name)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="money-printer", description="Paper-trading automation")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("backtest", help="Run a CSV backtest")
    b.add_argument("--strategy", default="sma", choices=STRATEGY_CHOICES)
    b.add_argument("--symbol", default="DEMO")
    b.add_argument("--csv", default="data/sample_ohlcv.csv")
    b.add_argument("--from", dest="start", default=None, help="YYYY-MM-DD")
    b.add_argument("--to", dest="end", default=None, help="YYYY-MM-DD")
    b.add_argument("--profile", default=None)
    b.add_argument("--dry-run", action="store_true")
    b.add_argument("--no-journal", action="store_true")
    b.add_argument("--analytics", action="store_true", help="Attach rich portfolio analytics")
    b.add_argument("--sizer", default=None, help="fixed|vol|atr|kelly")
    b.add_argument(
        "--sizer-param",
        action="append",
        default=[],
        help="Sizer param as key=value (repeatable)",
    )
    b.add_argument("--reports-dir", default="reports")
    b.set_defaults(func=cmd_backtest)

    w = sub.add_parser("walkforward", help="Walk-forward out-of-sample folds")
    w.add_argument("--strategy", default="sma", choices=STRATEGY_CHOICES)
    w.add_argument("--symbol", default="DEMO")
    w.add_argument("--csv", default="data/sample_ohlcv.csv")
    w.add_argument("--train-bars", type=int, default=40)
    w.add_argument("--test-bars", type=int, default=20)
    w.add_argument("--step-bars", type=int, default=None)
    w.add_argument("--profile", default=None)
    w.add_argument("--dry-run", action="store_true")
    w.add_argument("--reports-dir", default="reports")
    w.set_defaults(func=cmd_walkforward)

    d = sub.add_parser("daemon", help="Poll loop (SIGINT to stop)")
    d.add_argument("--strategy", default="sma", choices=STRATEGY_CHOICES)
    d.add_argument("--symbol", default="DEMO")
    d.add_argument("--csv", default="data/sample_ohlcv.csv")
    d.add_argument("--profile", default=None)
    d.add_argument("--dry-run", action="store_true")
    d.set_defaults(func=cmd_daemon)

    s = sub.add_parser("strategies", help="List registered strategies")
    s.set_defaults(func=cmd_strategies)
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
