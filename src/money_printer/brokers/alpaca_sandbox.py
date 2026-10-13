from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from money_printer.brokers.base import Broker, BrokerOrder, OrderStatus
from money_printer.brokers.paper import PaperBroker
from money_printer.models import Fill, Side


@dataclass
class AlpacaCredentials:
    api_key: str = "PAPER_KEY"
    api_secret: str = "PAPER_SECRET"
    base_url: str = "https://paper-api.alpaca.markets"


class AlpacaSandboxBroker(Broker):
    """
    Alpaca paper-trading shaped adapter.
    Default mode is offline (local PaperBroker mirror) so the core app never
    depends on network. Set offline=False to attempt real paper HTTP calls.
    """

    name = "alpaca_sandbox"

    def __init__(
        self,
        credentials: AlpacaCredentials | None = None,
        *,
        starting_cash: float = 100_000.0,
        offline: bool = True,
        timeout: float = 10.0,
    ) -> None:
        self.credentials = credentials or AlpacaCredentials()
        self.offline = offline
        self.timeout = timeout
        self._local = PaperBroker(starting_cash=starting_cash, slippage_bps=5.0, commission_per_fill=0.0)
        self._remote_orders: dict[str, dict[str, Any]] = {}

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self.credentials.api_key,
            "APCA-API-SECRET-KEY": self.credentials.api_secret,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        url = self.credentials.base_url.rstrip("/") + path
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.URLError as exc:
            raise RuntimeError(f"alpaca_http_error: {exc}") from exc

    def submit(self, order: BrokerOrder, *, mark_price: float, ts: datetime) -> BrokerOrder:
        if self.offline:
            return self._local.submit(order, mark_price=mark_price, ts=ts)

        payload = {
            "symbol": order.symbol,
            "qty": str(order.qty),
            "side": order.side.value,
            "type": order.order_type,
            "time_in_force": "day",
            "client_order_id": order.client_order_id,
        }
        if order.limit_price is not None:
            payload["limit_price"] = str(order.limit_price)
        try:
            remote = self._request("POST", "/v2/orders", payload)
        except RuntimeError as exc:
            order.status = OrderStatus.REJECTED
            order.reject_reason = str(exc)
            return order

        self._remote_orders[order.client_order_id] = remote
        status = str(remote.get("status", "accepted")).lower()
        order.created_at = ts
        order.updated_at = ts
        if status in {"filled", "partially_filled"}:
            order.status = OrderStatus.FILLED if status == "filled" else OrderStatus.PARTIAL
            order.filled_qty = float(remote.get("filled_qty") or order.qty)
            order.avg_fill_price = float(remote.get("filled_avg_price") or mark_price)
        elif status in {"rejected", "canceled"}:
            order.status = OrderStatus.REJECTED if status == "rejected" else OrderStatus.CANCELED
            order.reject_reason = str(remote.get("status", status))
        else:
            order.status = OrderStatus.SUBMITTED
        return order

    def cancel(self, client_order_id: str) -> BrokerOrder | None:
        if self.offline:
            return self._local.cancel(client_order_id)
        remote = self._remote_orders.get(client_order_id)
        if not remote:
            return None
        try:
            self._request("DELETE", f"/v2/orders/{remote.get('id', client_order_id)}")
        except RuntimeError:
            return None
        order = BrokerOrder(
            symbol=str(remote.get("symbol", "")),
            side=Side(str(remote.get("side", "buy"))),
            qty=float(remote.get("qty") or 0),
            client_order_id=client_order_id,
            status=OrderStatus.CANCELED,
            updated_at=datetime.now(timezone.utc),
        )
        return order

    def get_order(self, client_order_id: str) -> BrokerOrder | None:
        if self.offline:
            return self._local.get_order(client_order_id)
        remote = self._remote_orders.get(client_order_id)
        if not remote:
            return None
        return BrokerOrder(
            symbol=str(remote.get("symbol", "")),
            side=Side(str(remote.get("side", "buy"))),
            qty=float(remote.get("qty") or 0),
            client_order_id=client_order_id,
            status=OrderStatus.SUBMITTED,
        )

    def open_orders(self) -> list[BrokerOrder]:
        if self.offline:
            return self._local.open_orders()
        return []

    def cash(self) -> float:
        if self.offline:
            return self._local.cash()
        acct = self._request("GET", "/v2/account")
        return float(acct.get("cash") or 0)

    def positions(self) -> dict[str, float]:
        if self.offline:
            return self._local.positions()
        rows = self._request("GET", "/v2/positions")
        if isinstance(rows, list):
            return {str(r["symbol"]): float(r.get("qty") or 0) for r in rows}
        return {}

    def fills(self) -> list[Fill]:
        return self._local.fills()

    def account_summary(self) -> dict[str, Any]:
        if self.offline:
            return {
                "broker": self.name,
                "mode": "offline",
                "cash": self.cash(),
                "positions": self.positions(),
            }
        acct = self._request("GET", "/v2/account")
        return {"broker": self.name, "mode": "online", "account": acct}
