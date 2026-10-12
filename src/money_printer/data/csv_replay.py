from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Optional

from money_printer.data.base import MarketDataProvider
from money_printer.models import Bar


def _parse_ts(raw: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(raw.strip())


class CsvReplayProvider(MarketDataProvider):
    """Offline OHLCV replay from a CSV with columns: date,open,high,low,close,volume."""

    def __init__(self, path: str | Path, symbol: str | None = None) -> None:
        self.path = Path(path)
        self.default_symbol = symbol or self.path.stem.upper()

    def history(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[Bar]:
        if not self.path.exists():
            raise FileNotFoundError(f"CSV not found: {self.path}")

        bars: list[Bar] = []
        with self.path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = _parse_ts(row.get("date") or row.get("timestamp") or row["ts"])
                if start and ts < start:
                    continue
                if end and ts > end:
                    continue
                bars.append(
                    Bar(
                        symbol=symbol or self.default_symbol,
                        ts=ts,
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row.get("volume") or 0),
                    )
                )
        return bars
