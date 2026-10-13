from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from money_printer.storage.migrate import apply_migrations


@dataclass
class BacktestRunRecord:
    run_id: str
    strategy: str
    symbol: str
    starting_cash: float
    final_equity: float
    total_return_pct: float
    max_drawdown: float
    sharpe: float
    n_fills: int
    created_at: str
    report: dict[str, Any]


@dataclass
class OrderRecord:
    order_id: str
    symbol: str
    side: str
    qty: float
    filled_qty: float
    avg_price: float
    lifecycle: str
    strategy: str
    reject_reason: str
    created_at: str
    updated_at: str


@dataclass
class PositionSnapshot:
    symbol: str
    qty: float
    avg_cost: float
    market_price: float
    ts: str


class StorageRepository:
    """SQLite persistence for runs/orders/positions. Optional; core CLI works without it."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        apply_migrations(self.path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row

    def save_backtest_run(self, report: dict[str, Any]) -> str:
        run_id = report.get("run_id") or uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO backtest_runs(
              run_id, strategy, symbol, starting_cash, final_equity, total_return_pct,
              max_drawdown, sharpe, n_fills, created_at, report_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                str(report.get("strategy", "")),
                str(report.get("symbol", "")),
                float(report.get("starting_cash", 0)),
                float(report.get("final_equity", 0)),
                float(report.get("total_return_pct", 0)),
                float(report.get("max_drawdown", 0)),
                float(report.get("sharpe", 0)),
                int(report.get("n_fills", 0)),
                now,
                json.dumps(report, default=str),
            ),
        )
        self._conn.commit()
        return run_id

    def list_backtest_runs(self, limit: int = 50) -> list[BacktestRunRecord]:
        rows = self._conn.execute(
            """
            SELECT * FROM backtest_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            BacktestRunRecord(
                run_id=r["run_id"],
                strategy=r["strategy"],
                symbol=r["symbol"],
                starting_cash=r["starting_cash"],
                final_equity=r["final_equity"],
                total_return_pct=r["total_return_pct"],
                max_drawdown=r["max_drawdown"],
                sharpe=r["sharpe"],
                n_fills=r["n_fills"],
                created_at=r["created_at"],
                report=json.loads(r["report_json"]),
            )
            for r in rows
        ]

    def save_order(self, order: OrderRecord) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO oms_orders(
              order_id, symbol, side, qty, filled_qty, avg_price, lifecycle,
              strategy, reject_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order.order_id,
                order.symbol,
                order.side,
                order.qty,
                order.filled_qty,
                order.avg_price,
                order.lifecycle,
                order.strategy,
                order.reject_reason,
                order.created_at,
                order.updated_at,
            ),
        )
        self._conn.commit()

    def list_orders(self, limit: int = 100) -> list[OrderRecord]:
        rows = self._conn.execute(
            "SELECT * FROM oms_orders ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            OrderRecord(
                order_id=r["order_id"],
                symbol=r["symbol"],
                side=r["side"],
                qty=r["qty"],
                filled_qty=r["filled_qty"],
                avg_price=r["avg_price"],
                lifecycle=r["lifecycle"],
                strategy=r["strategy"],
                reject_reason=r["reject_reason"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def save_position_snapshot(self, snap: PositionSnapshot) -> None:
        self._conn.execute(
            """
            INSERT INTO position_snapshots(symbol, qty, avg_cost, market_price, ts)
            VALUES (?, ?, ?, ?, ?)
            """,
            (snap.symbol, snap.qty, snap.avg_cost, snap.market_price, snap.ts),
        )
        self._conn.commit()

    def save_account_snapshot(self, cash: float, equity: float, broker: str) -> None:
        self._conn.execute(
            """
            INSERT INTO account_snapshots(cash, equity, broker, ts)
            VALUES (?, ?, ?, ?)
            """,
            (cash, equity, broker, datetime.now(timezone.utc).isoformat()),
        )
        self._conn.commit()

    def audit(self, actor: str, action: str, detail: dict[str, Any] | None = None) -> None:
        self._conn.execute(
            """
            INSERT INTO audit_log(actor, action, detail_json, ts)
            VALUES (?, ?, ?, ?)
            """,
            (
                actor,
                action,
                json.dumps(detail or {}, default=str),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
