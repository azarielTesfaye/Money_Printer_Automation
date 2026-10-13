from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from money_printer.brokers.base import Broker, BrokerOrder
from money_printer.models import Fill, Side
from money_printer.oms.events import EventStore, OrderEvent, OrderEventType
from money_printer.oms.rules import PreTradeRules, apply_transition
from money_printer.oms.types import ManagedOrder, OrderIntent, OrderLifecycle


class OrderManager:
    """
    Order Management System sitting above broker adapters.
    Does not replace BacktestEngine; optional for live/paper routing.
    """

    def __init__(
        self,
        broker: Broker,
        events: EventStore | None = None,
        rules: PreTradeRules | None = None,
        position_lookup: Callable[[str], float] | None = None,
    ) -> None:
        self.broker = broker
        self.events = events
        self.rules = rules or PreTradeRules()
        self.position_lookup = position_lookup or (lambda _symbol: 0.0)
        self._orders: dict[str, ManagedOrder] = {}

    def _emit(self, order_id: str, event_type: OrderEventType, payload: dict | None = None) -> None:
        if self.events is None:
            return
        self.events.append(
            OrderEvent(order_id=order_id, event_type=event_type, payload=payload or {})
        )

    def submit(self, intent: OrderIntent, *, mark_price: float, ts: datetime | None = None) -> ManagedOrder:
        now = ts or datetime.now(timezone.utc)
        order = ManagedOrder(intent=intent, created_at=now, updated_at=now, remaining_qty=intent.qty)
        self._orders[order.order_id] = order
        self._emit(order.order_id, OrderEventType.CREATED, {"intent_id": intent.intent_id, "symbol": intent.symbol})

        open_count = len([o for o in self._orders.values() if o.is_open])
        result = self.rules.validate(
            intent,
            mark_price=mark_price,
            position_qty=self.position_lookup(intent.symbol),
            open_order_count=max(0, open_count - 1),
        )
        if not result.ok:
            apply_transition(order, OrderLifecycle.REJECTED)
            order.reject_reason = result.reason
            order.updated_at = now
            self._emit(order.order_id, OrderEventType.REJECTED, {"reason": result.reason})
            return order

        apply_transition(order, OrderLifecycle.VALIDATED)
        self._emit(order.order_id, OrderEventType.VALIDATED, {"reason": result.reason})

        apply_transition(order, OrderLifecycle.ROUTED)
        self._emit(order.order_id, OrderEventType.ROUTED, {"broker": getattr(self.broker, "name", "broker")})

        broker_order = BrokerOrder(
            symbol=intent.symbol,
            side=intent.side,
            qty=intent.qty,
            order_type=intent.order_type,
            limit_price=intent.limit_price,
            client_order_id=order.order_id,
        )
        filled = self.broker.submit(broker_order, mark_price=mark_price, ts=now)
        order.broker_order_id = filled.client_order_id
        order.updated_at = now

        status = filled.status.value
        if status == "rejected":
            apply_transition(order, OrderLifecycle.REJECTED)
            order.reject_reason = filled.reject_reason or "broker_rejected"
            self._emit(order.order_id, OrderEventType.REJECTED, {"reason": order.reject_reason})
            return order

        apply_transition(order, OrderLifecycle.ACKNOWLEDGED)
        self._emit(order.order_id, OrderEventType.ACK, {"broker_status": status})

        if filled.filled_qty > 0:
            self._apply_fill_qty(order, filled.filled_qty, filled.avg_fill_price or mark_price, now)
        return order

    def _apply_fill_qty(self, order: ManagedOrder, qty: float, price: float, ts: datetime) -> None:
        if qty <= 0:
            return
        prev = order.filled_qty
        new_filled = prev + qty
        if new_filled <= 0:
            avg = price
        else:
            avg = ((order.avg_price * prev) + (price * qty)) / new_filled
        order.filled_qty = new_filled
        order.avg_price = avg
        order.remaining_qty = max(0.0, order.intent.qty - order.filled_qty)
        order.updated_at = ts
        if order.remaining_qty <= 1e-9:
            apply_transition(order, OrderLifecycle.FILLED)
            self._emit(
                order.order_id,
                OrderEventType.FILL,
                {"qty": qty, "price": price, "filled_qty": order.filled_qty},
            )
        else:
            apply_transition(order, OrderLifecycle.PARTIALLY_FILLED)
            self._emit(
                order.order_id,
                OrderEventType.PARTIAL_FILL,
                {"qty": qty, "price": price, "filled_qty": order.filled_qty},
            )

    def cancel(self, order_id: str, ts: datetime | None = None) -> ManagedOrder | None:
        order = self._orders.get(order_id)
        if order is None or order.is_terminal:
            return order
        now = ts or datetime.now(timezone.utc)
        apply_transition(order, OrderLifecycle.CANCEL_PENDING)
        self._emit(order.order_id, OrderEventType.CANCEL_REQUESTED, {})
        canceled = self.broker.cancel(order.broker_order_id or order.order_id)
        if canceled is None or canceled.status.value == "canceled":
            apply_transition(order, OrderLifecycle.CANCELED)
            order.updated_at = now
            self._emit(order.order_id, OrderEventType.CANCELED, {})
        return order

    def get(self, order_id: str) -> ManagedOrder | None:
        return self._orders.get(order_id)

    def open_orders(self) -> list[ManagedOrder]:
        return [o for o in self._orders.values() if o.is_open]

    def all_orders(self) -> list[ManagedOrder]:
        return list(self._orders.values())

    def ingest_broker_fills(self, fills: list[Fill], ts: datetime | None = None) -> int:
        """Optional hook: map broker fills back onto open OMS orders by symbol/side FIFO."""
        now = ts or datetime.now(timezone.utc)
        applied = 0
        for fill in fills:
            candidates = [
                o
                for o in self.open_orders()
                if o.intent.symbol == fill.symbol and o.intent.side == fill.side
            ]
            remaining = fill.qty
            for order in candidates:
                if remaining <= 1e-9:
                    break
                take = min(remaining, order.remaining_qty)
                self._apply_fill_qty(order, take, fill.price, now)
                remaining -= take
                applied += 1
        return applied
