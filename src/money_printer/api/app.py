from __future__ import annotations

import json
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from money_printer.brokers import build_broker
from money_printer.config import load_profile
from money_printer.data.csv_replay import CsvReplayProvider
from money_printer.engine import BacktestEngine
from money_printer.models import Side
from money_printer.oms.events import EventStore
from money_printer.oms.manager import OrderManager
from money_printer.oms.types import OrderIntent
from money_printer.storage.repository import OrderRecord, StorageRepository
import money_printer.strategies  # noqa: F401
from money_printer.strategies import registry


class AppState:
    def __init__(
        self,
        *,
        db_path: str = "data/app_store.db",
        event_path: str = "data/oms_events.db",
        broker_name: str = "paper",
    ) -> None:
        self.store = StorageRepository(db_path)
        self.events = EventStore(event_path)
        self.broker = build_broker(broker_name, starting_cash=100_000.0, offline=True)
        self.oms = OrderManager(self.broker, events=self.events)
        self.broker_name = broker_name

    def close(self) -> None:
        self.store.close()
        self.events.close()


def create_app(
    *,
    db_path: str = "data/app_store.db",
    event_path: str = "data/oms_events.db",
    broker_name: str = "paper",
) -> AppState:
    """Create API state. Use `make_handler` / `serve_app` to run HTTP."""
    return AppState(db_path=db_path, event_path=event_path, broker_name=broker_name)


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    body = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def handle_request(state: AppState, method: str, path: str, body: dict[str, Any], query: dict[str, list[str]]) -> tuple[int, Any, str | None]:
    """Pure request handler used by HTTP server and tests. Returns (status, payload, html_or_none)."""
    if method == "GET" and path == "/health":
        return (
            200,
            {
                "ok": True,
                "ts": datetime.now(timezone.utc).isoformat(),
                "broker": getattr(state.broker, "name", state.broker_name),
                "open_orders": len(state.oms.open_orders()),
            },
            None,
        )

    if method == "GET" and path == "/strategies":
        return 200, {"strategies": registry.names()}, None

    if method == "POST" and path == "/backtests":
        strategy = str(body.get("strategy", "sma"))
        symbol = str(body.get("symbol", "DEMO"))
        csv_path = str(body.get("csv", "data/sample_ohlcv.csv"))
        analytics = bool(body.get("analytics", False))
        profile_name = body.get("profile")
        if strategy not in registry.names():
            return 400, {"detail": f"unknown strategy {strategy}"}, None
        _, profile, strategies_cfg = load_profile(profile_name)
        params = dict(strategies_cfg.get(strategy, {}))
        engine = BacktestEngine(
            profile,
            registry.create(strategy, **params),
            CsvReplayProvider(csv_path, symbol=symbol),
            rich_analytics=analytics,
        )
        report = engine.run(symbol)
        run_id = state.store.save_backtest_run(report)
        state.store.audit("api", "backtest", {"run_id": run_id, "strategy": strategy})
        report["run_id"] = run_id
        return 200, report, None

    if method == "GET" and path == "/backtests":
        limit = int((query.get("limit") or ["20"])[0])
        rows = state.store.list_backtest_runs(limit=limit)
        return (
            200,
            {
                "runs": [
                    {
                        "run_id": r.run_id,
                        "strategy": r.strategy,
                        "symbol": r.symbol,
                        "final_equity": r.final_equity,
                        "total_return_pct": r.total_return_pct,
                        "sharpe": r.sharpe,
                        "created_at": r.created_at,
                    }
                    for r in rows
                ]
            },
            None,
        )

    if method == "POST" and path == "/orders":
        try:
            side = Side(str(body.get("side", "buy")).lower())
        except ValueError:
            return 400, {"detail": "side must be buy or sell"}, None
        intent = OrderIntent(
            symbol=str(body.get("symbol", "DEMO")),
            side=side,
            qty=float(body.get("qty", 0)),
            order_type=str(body.get("order_type", "market")),
            limit_price=(float(body["limit_price"]) if body.get("limit_price") is not None else None),
            strategy=str(body.get("strategy", "")),
        )
        mark_price = float(body.get("mark_price", 0))
        order = state.oms.submit(intent, mark_price=mark_price)
        state.store.save_order(
            OrderRecord(
                order_id=order.order_id,
                symbol=order.intent.symbol,
                side=order.intent.side.value,
                qty=order.intent.qty,
                filled_qty=order.filled_qty,
                avg_price=order.avg_price,
                lifecycle=order.lifecycle.value,
                strategy=order.intent.strategy,
                reject_reason=order.reject_reason,
                created_at=(order.created_at or datetime.now(timezone.utc)).isoformat(),
                updated_at=(order.updated_at or datetime.now(timezone.utc)).isoformat(),
            )
        )
        state.store.audit("api", "order_submit", {"order_id": order.order_id, "lifecycle": order.lifecycle.value})
        return (
            200,
            {
                "order_id": order.order_id,
                "lifecycle": order.lifecycle.value,
                "filled_qty": order.filled_qty,
                "avg_price": order.avg_price,
                "reject_reason": order.reject_reason,
            },
            None,
        )

    if method == "GET" and path == "/orders":
        limit = int((query.get("limit") or ["50"])[0])
        return (
            200,
            {
                "orders": [
                    {
                        "order_id": o.order_id,
                        "symbol": o.symbol,
                        "side": o.side,
                        "qty": o.qty,
                        "filled_qty": o.filled_qty,
                        "lifecycle": o.lifecycle,
                        "reject_reason": o.reject_reason,
                    }
                    for o in state.store.list_orders(limit=limit)
                ]
            },
            None,
        )

    if method == "GET" and path == "/account":
        return (
            200,
            {
                "cash": state.broker.cash(),
                "positions": state.broker.positions(),
                "broker": getattr(state.broker, "name", state.broker_name),
            },
            None,
        )

    if method == "GET" and path == "/events":
        limit = int((query.get("limit") or ["100"])[0])
        rows = state.events.all_events(limit=limit)
        return (
            200,
            {
                "events": [
                    {
                        "event_id": e.event_id,
                        "order_id": e.order_id,
                        "event_type": e.event_type.value,
                        "payload": e.payload,
                        "ts": e.ts.isoformat(),
                    }
                    for e in rows
                ]
            },
            None,
        )

    if method == "GET" and path == "/":
        html_path = Path(__file__).with_name("dashboard.html")
        html = html_path.read_text(encoding="utf-8") if html_path.exists() else "<h1>Money Printer</h1>"
        return 200, None, html

    return 404, {"detail": "not found"}, None


def make_handler(state: AppState) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:  # quieter tests
            return

        def _dispatch(self) -> None:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            body: dict[str, Any] = {}
            if self.command in {"POST", "PUT", "PATCH"}:
                try:
                    body = _read_json(self)
                except json.JSONDecodeError:
                    _json_response(self, 400, {"detail": "invalid json"})
                    return
            status, payload, html = handle_request(state, self.command, parsed.path, body, query)
            if html is not None:
                raw = html.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                return
            _json_response(self, status, payload)

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch()

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch()

    return Handler


def serve_app(
    state: AppState,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), make_handler(state))
    return server
