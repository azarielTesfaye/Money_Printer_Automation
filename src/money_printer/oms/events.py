from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4


class OrderEventType(str, Enum):
    CREATED = "created"
    VALIDATED = "validated"
    ROUTED = "routed"
    ACK = "ack"
    PARTIAL_FILL = "partial_fill"
    FILL = "fill"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    NOTE = "note"


@dataclass
class OrderEvent:
    order_id: str
    event_type: OrderEventType
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid4().hex)
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventStore:
    """Append-only OMS event log (SQLite). Safe to use alongside TradeJournal."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_version (
              version INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS order_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              event_id TEXT NOT NULL UNIQUE,
              order_id TEXT NOT NULL,
              event_type TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              ts TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_order_events_order_id
              ON order_events(order_id);
            """
        )
        cur = self._conn.execute("SELECT COUNT(*) AS c FROM schema_version")
        if cur.fetchone()["c"] == 0:
            self._conn.execute("INSERT INTO schema_version(version) VALUES (1)")
        self._conn.commit()

    def append(self, event: OrderEvent) -> None:
        self._conn.execute(
            """
            INSERT INTO order_events(event_id, order_id, event_type, payload_json, ts)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.order_id,
                event.event_type.value,
                json.dumps(event.payload, default=str),
                event.ts.isoformat(),
            ),
        )
        self._conn.commit()

    def for_order(self, order_id: str) -> list[OrderEvent]:
        rows = self._conn.execute(
            """
            SELECT event_id, order_id, event_type, payload_json, ts
            FROM order_events
            WHERE order_id = ?
            ORDER BY id
            """,
            (order_id,),
        ).fetchall()
        return [self._row_to_event(r) for r in rows]

    def all_events(self, limit: int = 1000) -> list[OrderEvent]:
        rows = self._conn.execute(
            """
            SELECT event_id, order_id, event_type, payload_json, ts
            FROM order_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [self._row_to_event(r) for r in reversed(rows)]

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> OrderEvent:
        return OrderEvent(
            event_id=row["event_id"],
            order_id=row["order_id"],
            event_type=OrderEventType(row["event_type"]),
            payload=json.loads(row["payload_json"]),
            ts=datetime.fromisoformat(row["ts"]),
        )

    def close(self) -> None:
        self._conn.close()
