from __future__ import annotations

import sqlite3
from pathlib import Path

from money_printer.models import Fill


SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  qty REAL NOT NULL,
  price REAL NOT NULL,
  commission REAL NOT NULL,
  ts TEXT NOT NULL,
  reason TEXT,
  dry_run INTEGER NOT NULL DEFAULT 0
);
"""


class TradeJournal:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._migrate()

    def _migrate(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(SCHEMA_V1)
        cur.execute("SELECT COUNT(*) FROM schema_version")
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO schema_version(version) VALUES (1)")
        self._conn.commit()

    def append(self, fill: Fill) -> None:
        self._conn.execute(
            """
            INSERT INTO fills(symbol, side, qty, price, commission, ts, reason, dry_run)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fill.symbol,
                fill.side.value,
                fill.qty,
                fill.price,
                fill.commission,
                fill.ts.isoformat(),
                fill.reason,
                1 if fill.dry_run else 0,
            ),
        )
        self._conn.commit()

    def all_fills(self) -> list[dict]:
        cur = self._conn.execute(
            "SELECT symbol, side, qty, price, commission, ts, reason, dry_run FROM fills ORDER BY id"
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()
