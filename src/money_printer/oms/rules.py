from __future__ import annotations

from dataclasses import dataclass

from money_printer.models import Side
from money_printer.oms.types import ManagedOrder, OrderIntent, OrderLifecycle


@dataclass
class ValidationResult:
    ok: bool
    reason: str = "ok"


class PreTradeRules:
    """OMS pre-trade checks (separate from strategy RiskGate)."""

    def __init__(
        self,
        *,
        max_order_qty: float = 1_000_000.0,
        max_notional: float = 5_000_000.0,
        allowed_symbols: set[str] | None = None,
        allow_short: bool = False,
    ) -> None:
        self.max_order_qty = max_order_qty
        self.max_notional = max_notional
        self.allowed_symbols = {s.upper() for s in allowed_symbols} if allowed_symbols else None
        self.allow_short = allow_short

    def validate(
        self,
        intent: OrderIntent,
        *,
        mark_price: float,
        position_qty: float = 0.0,
        open_order_count: int = 0,
        max_open_orders: int = 50,
    ) -> ValidationResult:
        if intent.qty <= 0:
            return ValidationResult(False, "qty_must_be_positive")
        if intent.qty > self.max_order_qty:
            return ValidationResult(False, "qty_exceeds_max_order_qty")
        if mark_price <= 0:
            return ValidationResult(False, "invalid_mark_price")
        notional = intent.qty * mark_price
        if notional > self.max_notional:
            return ValidationResult(False, "notional_exceeds_max")
        if self.allowed_symbols is not None and intent.symbol.upper() not in self.allowed_symbols:
            return ValidationResult(False, "symbol_not_allowed")
        if intent.order_type == "limit" and intent.limit_price is None:
            return ValidationResult(False, "limit_price_required")
        if intent.side == Side.SELL and not self.allow_short and intent.qty > position_qty + 1e-9:
            return ValidationResult(False, "short_not_allowed")
        if open_order_count >= max_open_orders:
            return ValidationResult(False, "too_many_open_orders")
        if intent.side not in {Side.BUY, Side.SELL}:
            return ValidationResult(False, "side_not_tradable")
        return ValidationResult(True, "ok")


ALLOWED_TRANSITIONS: dict[OrderLifecycle, set[OrderLifecycle]] = {
    OrderLifecycle.CREATED: {OrderLifecycle.VALIDATED, OrderLifecycle.REJECTED},
    OrderLifecycle.VALIDATED: {OrderLifecycle.ROUTED, OrderLifecycle.REJECTED, OrderLifecycle.CANCELED},
    OrderLifecycle.ROUTED: {
        OrderLifecycle.ACKNOWLEDGED,
        OrderLifecycle.REJECTED,
        OrderLifecycle.CANCELED,
    },
    OrderLifecycle.ACKNOWLEDGED: {
        OrderLifecycle.PARTIALLY_FILLED,
        OrderLifecycle.FILLED,
        OrderLifecycle.CANCEL_PENDING,
        OrderLifecycle.CANCELED,
        OrderLifecycle.EXPIRED,
    },
    OrderLifecycle.PARTIALLY_FILLED: {
        OrderLifecycle.PARTIALLY_FILLED,
        OrderLifecycle.FILLED,
        OrderLifecycle.CANCEL_PENDING,
        OrderLifecycle.CANCELED,
        OrderLifecycle.EXPIRED,
    },
    OrderLifecycle.CANCEL_PENDING: {
        OrderLifecycle.CANCELED,
        OrderLifecycle.FILLED,
        OrderLifecycle.PARTIALLY_FILLED,
    },
    OrderLifecycle.FILLED: set(),
    OrderLifecycle.CANCELED: set(),
    OrderLifecycle.REJECTED: set(),
    OrderLifecycle.EXPIRED: set(),
}


def can_transition(current: OrderLifecycle, new: OrderLifecycle) -> bool:
    if current == new and current == OrderLifecycle.PARTIALLY_FILLED:
        return True
    return new in ALLOWED_TRANSITIONS.get(current, set())


def apply_transition(order: ManagedOrder, new: OrderLifecycle) -> None:
    if not can_transition(order.lifecycle, new):
        raise ValueError(f"illegal transition {order.lifecycle.value} -> {new.value}")
    order.lifecycle = new
