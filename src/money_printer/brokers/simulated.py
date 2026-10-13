from __future__ import annotations

import random
from datetime import datetime

from money_printer.brokers.base import Broker, BrokerOrder, OrderStatus
from money_printer.models import Fill, Side


class SimulatedExchangeBroker(Broker):
    """
    Exchange simulator with latency fills, partial fills, and reject probability.
    Useful for stress-testing execution paths without a live API.
    """

    name = "simulated"

    def __init__(
        self,
        starting_cash: float = 100_000.0,
        slippage_bps: float = 10.0,
        commission_per_fill: float = 1.0,
        partial_fill_prob: float = 0.15,
        reject_prob: float = 0.02,
        seed: int | None = 42,
    ) -> None:
        self._cash = starting_cash
        self.slippage_bps = slippage_bps
        self.commission_per_fill = commission_per_fill
        self.partial_fill_prob = partial_fill_prob
        self.reject_prob = reject_prob
        self._rng = random.Random(seed)
        self._orders: dict[str, BrokerOrder] = {}
        self._positions: dict[str, float] = {}
        self._fills: list[Fill] = []
        self._pending: list[str] = []

    def _slip(self, price: float, side: Side) -> float:
        # randomize slippage around configured bps
        noise = self._rng.uniform(0.5, 1.5)
        slip = price * (self.slippage_bps / 10_000.0) * noise
        return price + slip if side == Side.BUY else price - slip

    def submit(self, order: BrokerOrder, *, mark_price: float, ts: datetime) -> BrokerOrder:
        order.created_at = ts
        order.updated_at = ts
        if order.qty <= 0:
            order.status = OrderStatus.REJECTED
            order.reject_reason = "non_positive_qty"
            self._orders[order.client_order_id] = order
            return order

        if self._rng.random() < self.reject_prob:
            order.status = OrderStatus.REJECTED
            order.reject_reason = "exchange_reject"
            self._orders[order.client_order_id] = order
            return order

        order.status = OrderStatus.SUBMITTED
        self._orders[order.client_order_id] = order
        self._pending.append(order.client_order_id)
        # attempt immediate match on submit
        self.match_pending(mark_price=mark_price, ts=ts)
        return self._orders[order.client_order_id]

    def match_pending(self, *, mark_price: float, ts: datetime) -> list[Fill]:
        """Advance the matching engine for resting / newly submitted orders."""
        produced: list[Fill] = []
        still_pending: list[str] = []
        for oid in self._pending:
            order = self._orders[oid]
            if order.status in {OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED}:
                continue

            if order.order_type == "limit" and order.limit_price is not None:
                if order.side == Side.BUY and mark_price > order.limit_price:
                    still_pending.append(oid)
                    continue
                if order.side == Side.SELL and mark_price < order.limit_price:
                    still_pending.append(oid)
                    continue

            remaining = order.qty - order.filled_qty
            fill_qty = remaining
            if self._rng.random() < self.partial_fill_prob and remaining > 1:
                fill_qty = max(remaining * self._rng.uniform(0.2, 0.8), 1e-6)

            fill_px = self._slip(mark_price, order.side)
            notional = fill_qty * fill_px

            if order.side == Side.BUY and notional + self.commission_per_fill > self._cash:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "insufficient_cash"
                order.updated_at = ts
                continue
            if order.side == Side.SELL:
                held = self._positions.get(order.symbol, 0.0)
                if fill_qty > held + 1e-9:
                    order.status = OrderStatus.REJECTED
                    order.reject_reason = "insufficient_position"
                    order.updated_at = ts
                    continue

            if order.side == Side.BUY:
                self._cash -= notional + self.commission_per_fill
                self._positions[order.symbol] = self._positions.get(order.symbol, 0.0) + fill_qty
            else:
                self._cash += notional - self.commission_per_fill
                self._positions[order.symbol] = self._positions.get(order.symbol, 0.0) - fill_qty

            prev_filled = order.filled_qty
            new_filled = prev_filled + fill_qty
            if new_filled <= 0:
                avg = fill_px
            else:
                avg = ((order.avg_fill_price * prev_filled) + (fill_px * fill_qty)) / new_filled
            order.filled_qty = new_filled
            order.avg_fill_price = avg
            order.updated_at = ts
            if order.filled_qty + 1e-9 >= order.qty:
                order.status = OrderStatus.FILLED
            else:
                order.status = OrderStatus.PARTIAL
                still_pending.append(oid)

            fill = Fill(
                symbol=order.symbol,
                side=order.side,
                qty=fill_qty,
                price=fill_px,
                commission=self.commission_per_fill,
                ts=ts,
                reason=f"sim:{order.client_order_id}",
            )
            self._fills.append(fill)
            produced.append(fill)
        self._pending = still_pending
        return produced

    def cancel(self, client_order_id: str) -> BrokerOrder | None:
        order = self._orders.get(client_order_id)
        if order is None:
            return None
        if order.status in {OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED}:
            return order
        order.status = OrderStatus.CANCELED
        self._pending = [oid for oid in self._pending if oid != client_order_id]
        return order

    def get_order(self, client_order_id: str) -> BrokerOrder | None:
        return self._orders.get(client_order_id)

    def open_orders(self) -> list[BrokerOrder]:
        return [
            o
            for o in self._orders.values()
            if o.status in {OrderStatus.NEW, OrderStatus.SUBMITTED, OrderStatus.PARTIAL}
        ]

    def cash(self) -> float:
        return self._cash

    def positions(self) -> dict[str, float]:
        return dict(self._positions)

    def fills(self) -> list[Fill]:
        return list(self._fills)
