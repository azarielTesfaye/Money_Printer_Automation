from pathlib import Path

from money_printer.storage.migrate import apply_migrations
from money_printer.storage.repository import OrderRecord, PositionSnapshot, StorageRepository


def test_migrations_and_repository(tmp_path: Path):
    db = tmp_path / "store.db"
    applied = apply_migrations(db)
    assert applied == [1, 2, 3]
    assert apply_migrations(db) == []

    repo = StorageRepository(db)
    run_id = repo.save_backtest_run(
        {
            "strategy": "sma",
            "symbol": "DEMO",
            "starting_cash": 100000,
            "final_equity": 101000,
            "total_return_pct": 0.01,
            "max_drawdown": 0.02,
            "sharpe": 1.2,
            "n_fills": 3,
        }
    )
    assert run_id
    runs = repo.list_backtest_runs()
    assert len(runs) == 1
    assert runs[0].strategy == "sma"

    repo.save_order(
        OrderRecord(
            order_id="abc",
            symbol="DEMO",
            side="buy",
            qty=1,
            filled_qty=1,
            avg_price=10,
            lifecycle="filled",
            strategy="sma",
            reject_reason="",
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-01T00:00:00+00:00",
        )
    )
    assert repo.list_orders()[0].order_id == "abc"
    repo.save_position_snapshot(
        PositionSnapshot(symbol="DEMO", qty=1, avg_cost=10, market_price=11, ts="2024-01-01T00:00:00+00:00")
    )
    repo.save_account_snapshot(1000, 1100, "paper")
    repo.audit("test", "ping", {"ok": True})
    repo.close()
