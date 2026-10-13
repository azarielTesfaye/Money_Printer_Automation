from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str


MIGRATIONS: list[Migration] = [
    Migration(
        1,
        "init_core_tables",
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS backtest_runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          run_id TEXT NOT NULL UNIQUE,
          strategy TEXT NOT NULL,
          symbol TEXT NOT NULL,
          starting_cash REAL NOT NULL,
          final_equity REAL NOT NULL,
          total_return_pct REAL NOT NULL,
          max_drawdown REAL NOT NULL,
          sharpe REAL NOT NULL,
          n_fills INTEGER NOT NULL,
          created_at TEXT NOT NULL,
          report_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS oms_orders (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          order_id TEXT NOT NULL UNIQUE,
          symbol TEXT NOT NULL,
          side TEXT NOT NULL,
          qty REAL NOT NULL,
          filled_qty REAL NOT NULL,
          avg_price REAL NOT NULL,
          lifecycle TEXT NOT NULL,
          strategy TEXT NOT NULL,
          reject_reason TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS position_snapshots (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          symbol TEXT NOT NULL,
          qty REAL NOT NULL,
          avg_cost REAL NOT NULL,
          market_price REAL NOT NULL,
          ts TEXT NOT NULL
        );
        """,
    ),
    Migration(
        2,
        "add_account_and_audit",
        """
        CREATE TABLE IF NOT EXISTS account_snapshots (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          cash REAL NOT NULL,
          equity REAL NOT NULL,
          broker TEXT NOT NULL,
          ts TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          actor TEXT NOT NULL,
          action TEXT NOT NULL,
          detail_json TEXT NOT NULL,
          ts TEXT NOT NULL
        );
        """,
    ),
    Migration(
        3,
        "add_strategy_params_and_indexes",
        """
        CREATE TABLE IF NOT EXISTS strategy_param_sets (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          strategy TEXT NOT NULL,
          params_json TEXT NOT NULL,
          label TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_backtest_runs_strategy
          ON backtest_runs(strategy);
        CREATE INDEX IF NOT EXISTS idx_oms_orders_symbol
          ON oms_orders(symbol);
        """,
    ),
]


class MigrationRunner:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def current_version(self, conn: sqlite3.Connection) -> int:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version INTEGER PRIMARY KEY,
              name TEXT NOT NULL,
              applied_at TEXT NOT NULL
            )
            """
        )
        row = conn.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations").fetchone()
        return int(row["v"])

    def apply(self) -> list[int]:
        from datetime import datetime, timezone

        applied: list[int] = []
        with self.connect() as conn:
            current = self.current_version(conn)
            for mig in MIGRATIONS:
                if mig.version <= current:
                    continue
                conn.executescript(mig.sql)
                conn.execute(
                    "INSERT INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)",
                    (mig.version, mig.name, datetime.now(timezone.utc).isoformat()),
                )
                conn.commit()
                applied.append(mig.version)
        return applied


def apply_migrations(path: str | Path) -> list[int]:
    return MigrationRunner(path).apply()
