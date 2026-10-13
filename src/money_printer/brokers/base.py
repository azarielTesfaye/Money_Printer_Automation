from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from money_printer.models import Fill, Side


class OrderStatus(str, Enum):
    NEW = "new"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


@dataclass
class BrokerOrder:
    symbol: str
    side: Side
    qty: float
    order_type: str = "market"
    limit_price: float | None = None
    client_order_id: str = field(default_factory=lambda: uuid4().hex)
    status: OrderStatus = OrderStatus.NEW
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    reject_reason: str = ""


class Broker(ABC):
    """Broker adapter: submit/cancel orders and query account state."""

    name: str = "broker"

    @abstractmethod
    def submit(self, order: BrokerOrder, *, mark_price: float, ts: datetime) -> BrokerOrder:
        raise NotImplementedError

    @abstractmethod
    def cancel(self, client_order_id: str) -> BrokerOrder | None:
        raise NotImplementedError

    @abstractmethod
    def get_order(self, client_order_id: str) -> BrokerOrder | None:
        raise NotImplementedError

    @abstractmethod
    def open_orders(self) -> list[BrokerOrder]:
        raise NotImplementedError

    @abstractmethod
    def cash(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def positions(self) -> dict[str, float]:
        raise NotImplementedError

    @abstractmethod
    def fills(self) -> list[Fill]:
        raise NotImplementedError
