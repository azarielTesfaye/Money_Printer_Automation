from __future__ import annotations

from datetime import datetime

from money_printer.brokers.base import Broker, BrokerOrder, OrderStatus
from money_printer.models import Fill, Side


class PaperBroker(Broker):
    """Immediate market fills with configurable slippage and commission."""

    name = "paper"

    def __init__(
        self,
        starting_cash: float = 100_000.0,
        slippage_bps: float = 8.0,
        commission_per_fill: float = 1.0,
    ) -> None:
        self._cash = starting_cash
        self.slippage_bps = slippage_bps
        self.commission_per_fill = commission_per_fill
        self._orders: dict[str, BrokerOrder] = {}
        self._positions: dict[str, float] = {}
        self._fills: list[Fill] = []

    def _slip(self, price: float, side: Side) -> float:
        slip = price * (self.slippage_bps / 10_000.0)
        return price + slip if side == Side.BUY else price - slip

    def submit(self, order: BrokerOrder, *, mark_price: float, ts: datetime) -> BrokerOrder:
        order.created_at = ts
        order.updated_at = ts
        order.status = OrderStatus.SUBMITTED

        if order.qty <= 0:
            order.status = OrderStatus.REJECTED
            order.reject_reason = "non_positive_qty"
            self._orders[order.client_order_id] = order
            return order

        px = order.limit_price if order.order_type == "limit" and order.limit_price else mark_price
        if order.order_type == "limit" and order.limit_price is not None:
            if order.side == Side.BUY and mark_price > order.limit_price:
                order.status = OrderStatus.SUBMITTED
                self._orders[order.client_order_id] = order
                return order
            if order.side == Side.SELL and mark_price < order.limit_price:
                order.status = OrderStatus.SUBMITTED
                self._orders[order.client_order_id] = order
                return order

        fill_px = self._slip(px, order.side)
        notional = order.qty * fill_px
        if order.side == Side.BUY and notional + self.commission_per_fill > self._cash:
            order.status = OrderStatus.REJECTED
            order.reject_reason = "insufficient_cash"
            self._orders[order.client_order_id] = order
            return order
        if order.side == Side.SELL:
            held = self._positions.get(order.symbol, 0.0)
            if order.qty > held + 1e-9:
                order.status = OrderStatus.REJECTED
                order.reject_reason = "insufficient_position"
                self._orders[order.client_order_id] = order
                return order

        if order.side == Side.BUY:
            self._cash -= notional + self.commission_per_fill
            self._positions[order.symbol] = self._positions.get(order.symbol, 0.0) + order.qty
        else:
            self._cash += notional - self.commission_per_fill
            self._positions[order.symbol] = self._positions.get(order.symbol, 0.0) - order.qty

        order.filled_qty = order.qty
        order.avg_fill_price = fill_px
        order.status = OrderStatus.FILLED
        order.updated_at = ts
        self._orders[order.client_order_id] = order
        self._fills.append(
            Fill(
                symbol=order.symbol,
                side=order.side,
                qty=order.qty,
                price=fill_px,
                commission=self.commission_per_fill,
                ts=ts,
                reason=f"paper:{order.client_order_id}",
            )
        )
        return order

    def cancel(self, client_order_id: str) -> BrokerOrder | None:
        order = self._orders.get(client_order_id)
        if order is None:
            return None
        if order.status in {OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED}:
            return order
        order.status = OrderStatus.CANCELED
        return order

    def get_order(self, client_order_id: str) -> BrokerOrder | None:
        return self._orders.get(client_order_id)

    def open_orders(self) -> list[BrokerOrder]:
        return [o for o in self._orders.values() if o.status in {OrderStatus.NEW, OrderStatus.SUBMITTED, OrderStatus.PARTIAL}]

    def cash(self) -> float:
        return self._cash

    def positions(self) -> dict[str, float]:
        return dict(self._positions)

    def fills(self) -> list[Fill]:
        return list(self._fills)
