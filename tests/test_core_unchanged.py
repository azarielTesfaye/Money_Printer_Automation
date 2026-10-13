"""Guardrail: core CLI backtest path still works after new modules."""

from pathlib import Path

from money_printer.cli import build_parser
from money_printer.config import ProfileSettings
from money_printer.data.csv_replay import CsvReplayProvider
from money_printer.engine import BacktestEngine
from money_printer.strategies.sma import SmaCrossover


def test_core_engine_backtest_still_works(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    settings = ProfileSettings(
        starting_cash=100_000,
        journal_path=str(tmp_path / "j.db"),
        health_path=str(tmp_path / "h.json"),
        stop_file=str(tmp_path / "STOP"),
    )
    engine = BacktestEngine(
        settings,
        SmaCrossover(fast=5, slow=20),
        CsvReplayProvider(root / "data" / "sample_ohlcv.csv", "DEMO"),
    )
    report = engine.run("DEMO")
    assert report["n_bars"] > 0
    assert "final_equity" in report


def test_cli_backtest_exit_zero(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    args = build_parser().parse_args(
        [
            "backtest",
            "--strategy",
            "sma",
            "--csv",
            str(root / "data" / "sample_ohlcv.csv"),
            "--no-journal",
            "--reports-dir",
            str(tmp_path / "reports"),
        ]
    )
    assert args.func(args) == 0
    assert list((tmp_path / "reports").glob("backtest_*.json"))
