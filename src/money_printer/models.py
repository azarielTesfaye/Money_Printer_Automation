from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"
    FLAT = "flat"


@dataclass(frozen=True)
class Bar:
    symbol: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(frozen=True)
class Signal:
    symbol: str
    side: Side
    strength: float = 1.0
    reason: str = ""
    ts: Optional[datetime] = None


@dataclass
class Fill:
    symbol: str
    side: Side
    qty: float
    price: float
    commission: float
    ts: datetime
    reason: str = ""
    dry_run: bool = False


@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_cost: float = 0.0

    @property
    def market_value(self) -> float:
        return self.qty * self.avg_cost
