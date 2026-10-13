from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from money_printer.brokers.base import Broker, BrokerOrder, OrderStatus
from money_printer.brokers.simulated import SimulatedExchangeBroker
from money_printer.models import Fill, Side


@dataclass
class BinanceCredentials:
    api_key: str = "BINANCE_TEST_KEY"
    api_secret: str = "BINANCE_TEST_SECRET"
    base_url: str = "https://testnet.binance.vision"


class BinanceSandboxBroker(Broker):
    """
    Binance spot testnet-shaped adapter.
    Offline mode uses SimulatedExchangeBroker so CI/dev never need network.
    """

    name = "binance_sandbox"

    def __init__(
        self,
        credentials: BinanceCredentials | None = None,
        *,
        starting_cash: float = 100_000.0,
        offline: bool = True,
        timeout: float = 10.0,
        seed: int = 7,
    ) -> None:
        self.credentials = credentials or BinanceCredentials()
        self.offline = offline
        self.timeout = timeout
        self._local = SimulatedExchangeBroker(
            starting_cash=starting_cash,
            slippage_bps=8.0,
            commission_per_fill=0.1,
            partial_fill_prob=0.1,
            reject_prob=0.01,
            seed=seed,
        )

    def _sign(self, query: str) -> str:
        return hmac.new(
            self.credentials.api_secret.encode(),
            query.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _request(self, method: str, path: str, params: dict[str, Any] | None = None) -> Any:
        params = dict(params or {})
        params["timestamp"] = int(time.time() * 1000)
        query = urllib.parse.urlencode(params)
        signature = self._sign(query)
        url = f"{self.credentials.base_url.rstrip('/')}{path}?{query}&signature={signature}"
        req = urllib.request.Request(
            url,
            headers={"X-MBX-APIKEY": self.credentials.api_key},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.URLError as exc:
            raise RuntimeError(f"binance_http_error: {exc}") from exc

    def submit(self, order: BrokerOrder, *, mark_price: float, ts: datetime) -> BrokerOrder:
        if self.offline:
            return self._local.submit(order, mark_price=mark_price, ts=ts)
        params = {
            "symbol": order.symbol.replace("/", ""),
            "side": order.side.value.upper(),
            "type": order.order_type.upper(),
            "quantity": order.qty,
            "newClientOrderId": order.client_order_id,
        }
        if order.limit_price is not None:
            params["price"] = order.limit_price
            params["timeInForce"] = "GTC"
        try:
            remote = self._request("POST", "/api/v3/order", params)
        except RuntimeError as exc:
            order.status = OrderStatus.REJECTED
            order.reject_reason = str(exc)
            return order
        order.created_at = ts
        order.updated_at = ts
        status = str(remote.get("status", "NEW")).upper()
        if status == "FILLED":
            order.status = OrderStatus.FILLED
            order.filled_qty = float(remote.get("executedQty") or order.qty)
            fills = remote.get("fills") or []
            if fills:
                order.avg_fill_price = float(fills[0].get("price") or mark_price)
            else:
                order.avg_fill_price = mark_price
        elif status == "PARTIALLY_FILLED":
            order.status = OrderStatus.PARTIAL
            order.filled_qty = float(remote.get("executedQty") or 0)
            order.avg_fill_price = mark_price
        elif status in {"CANCELED", "REJECTED", "EXPIRED"}:
            order.status = OrderStatus.REJECTED if status == "REJECTED" else OrderStatus.CANCELED
        else:
            order.status = OrderStatus.SUBMITTED
        return order

    def cancel(self, client_order_id: str) -> BrokerOrder | None:
        if self.offline:
            return self._local.cancel(client_order_id)
        try:
            self._request("DELETE", "/api/v3/order", {"origClientOrderId": client_order_id})
        except RuntimeError:
            return None
        return BrokerOrder(
            symbol="",
            side=Side.BUY,
            qty=0,
            client_order_id=client_order_id,
            status=OrderStatus.CANCELED,
            updated_at=datetime.now(timezone.utc),
        )

    def get_order(self, client_order_id: str) -> BrokerOrder | None:
        if self.offline:
            return self._local.get_order(client_order_id)
        try:
            remote = self._request("GET", "/api/v3/order", {"origClientOrderId": client_order_id})
        except RuntimeError:
            return None
        return BrokerOrder(
            symbol=str(remote.get("symbol", "")),
            side=Side(str(remote.get("side", "BUY")).lower()),
            qty=float(remote.get("origQty") or 0),
            client_order_id=client_order_id,
            status=OrderStatus.SUBMITTED,
        )

    def open_orders(self) -> list[BrokerOrder]:
        if self.offline:
            return self._local.open_orders()
        return []

    def cash(self) -> float:
        return self._local.cash()

    def positions(self) -> dict[str, float]:
        return self._local.positions()

    def fills(self) -> list[Fill]:
        return self._local.fills()

    def match_pending(self, *, mark_price: float, ts: datetime) -> list[Fill]:
        if hasattr(self._local, "match_pending"):
            return self._local.match_pending(mark_price=mark_price, ts=ts)
        return []
