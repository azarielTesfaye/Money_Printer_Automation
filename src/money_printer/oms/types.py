from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from money_printer.models import Side


class OrderLifecycle(str, Enum):
    CREATED = "created"
    VALIDATED = "validated"
    ROUTED = "routed"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCEL_PENDING = "cancel_pending"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class OrderIntent:
    """User/strategy intent before OMS validation."""

    symbol: str
    side: Side
    qty: float
    order_type: str = "market"
    limit_price: float | None = None
    time_in_force: str = "day"
    strategy: str = ""
    client_tag: str = ""
    intent_id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class ManagedOrder:
    """OMS-owned order with lifecycle and fill progress."""

    intent: OrderIntent
    order_id: str = field(default_factory=lambda: uuid4().hex)
    lifecycle: OrderLifecycle = OrderLifecycle.CREATED
    filled_qty: float = 0.0
    avg_price: float = 0.0
    remaining_qty: float = 0.0
    broker_order_id: str = ""
    reject_reason: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.remaining_qty <= 0:
            self.remaining_qty = self.intent.qty

    @property
    def is_terminal(self) -> bool:
        return self.lifecycle in {
            OrderLifecycle.FILLED,
            OrderLifecycle.CANCELED,
            OrderLifecycle.REJECTED,
            OrderLifecycle.EXPIRED,
        }

    @property
    def is_open(self) -> bool:
        return not self.is_terminal
