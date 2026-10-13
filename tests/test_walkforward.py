from pathlib import Path

from money_printer.config import ProfileSettings
from money_printer.data.csv_replay import CsvReplayProvider
from money_printer.strategies.sma import SmaCrossover
from money_printer.walkforward import build_windows, run_walk_forward


def test_walk_forward_on_sample_csv(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "data" / "sample_ohlcv.csv"
    provider = CsvReplayProvider(csv_path, "DEMO")
    bars = provider.history("DEMO")
    windows = build_windows(bars, train_bars=30, test_bars=15, step_bars=15)
    assert len(windows) >= 1

    settings = ProfileSettings(
        starting_cash=100_000,
        journal_path=str(tmp_path / "j.db"),
        health_path=str(tmp_path / "h.json"),
        stop_file=str(tmp_path / "STOP"),
    )
    result = run_walk_forward(
        settings,
        lambda: SmaCrossover(fast=5, slow=20),
        provider,
        "DEMO",
        train_bars=30,
        test_bars=15,
        step_bars=15,
    )
    assert result.aggregate["n_folds"] >= 1
