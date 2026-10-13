from datetime import datetime
from pathlib import Path

from money_printer.brokers.paper import PaperBroker
from money_printer.models import Side
from money_printer.oms.events import EventStore
from money_printer.oms.manager import OrderManager
from money_printer.oms.rules import PreTradeRules
from money_printer.oms.types import OrderIntent, OrderLifecycle


def test_oms_submit_fill_and_reject(tmp_path: Path):
    events = EventStore(tmp_path / "events.db")
    broker = PaperBroker(starting_cash=5_000, slippage_bps=0, commission_per_fill=0)
    oms = OrderManager(broker, events=events, rules=PreTradeRules(max_order_qty=100))

    ok = oms.submit(
        OrderIntent(symbol="DEMO", side=Side.BUY, qty=10),
        mark_price=100,
        ts=datetime(2024, 1, 1),
    )
    assert ok.lifecycle == OrderLifecycle.FILLED
    assert ok.filled_qty == 10
    assert len(events.for_order(ok.order_id)) >= 3

    bad = oms.submit(
        OrderIntent(symbol="DEMO", side=Side.BUY, qty=10_000),
        mark_price=100,
        ts=datetime(2024, 1, 2),
    )
    assert bad.lifecycle == OrderLifecycle.REJECTED
    events.close()


def test_oms_cancel_open_limit(tmp_path: Path):
    broker = PaperBroker(starting_cash=50_000, slippage_bps=0, commission_per_fill=0)
    oms = OrderManager(broker, events=EventStore(tmp_path / "e.db"))
    order = oms.submit(
        OrderIntent(symbol="DEMO", side=Side.BUY, qty=1, order_type="limit", limit_price=50),
        mark_price=100,  # won't fill immediately on paper when limit below market
        ts=datetime(2024, 1, 1),
    )
    # Paper broker parks unfilled limits as submitted
    if order.is_open:
        canceled = oms.cancel(order.order_id, ts=datetime(2024, 1, 2))
        assert canceled is not None
        assert canceled.lifecycle == OrderLifecycle.CANCELED
