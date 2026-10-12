from pathlib import Path

from money_printer.config import ProfileSettings
from money_printer.data.csv_replay import CsvReplayProvider
from money_printer.engine import BacktestEngine, write_report
from money_printer.strategies.sma import SmaCrossover


def test_csv_backtest_produces_report(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "data" / "sample_ohlcv.csv"
    settings = ProfileSettings(
        starting_cash=100_000,
        journal_path=str(tmp_path / "j.db"),
        health_path=str(tmp_path / "health.json"),
        stop_file=str(tmp_path / "STOP"),
    )
    engine = BacktestEngine(settings, SmaCrossover(fast=5, slow=20), CsvReplayProvider(csv_path, "DEMO"))
    report = engine.run("DEMO")
    assert report["n_bars"] > 0
    assert "final_equity" in report
    out = write_report(report, tmp_path / "reports")
    assert out.exists()
