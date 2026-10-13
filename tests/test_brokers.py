from datetime import datetime

from money_printer.brokers.paper import PaperBroker
from money_printer.brokers.simulated import SimulatedExchangeBroker
from money_printer.brokers.base import BrokerOrder
from money_printer.models import Side


def test_paper_broker_buy_and_sell():
    b = PaperBroker(starting_cash=10_000, slippage_bps=0, commission_per_fill=0)
    ts = datetime(2024, 1, 1)
    buy = b.submit(BrokerOrder(symbol="DEMO", side=Side.BUY, qty=10), mark_price=100, ts=ts)
    assert buy.status.value == "filled"
    assert b.cash() == 9000
    assert b.positions()["DEMO"] == 10
    sell = b.submit(BrokerOrder(symbol="DEMO", side=Side.SELL, qty=10), mark_price=110, ts=ts)
    assert sell.status.value == "filled"
    assert abs(b.cash() - 10_100) < 1e-6


def test_simulated_broker_can_fill():
    b = SimulatedExchangeBroker(starting_cash=20_000, reject_prob=0.0, partial_fill_prob=0.0, seed=1)
    ts = datetime(2024, 1, 2)
    order = b.submit(BrokerOrder(symbol="DEMO", side=Side.BUY, qty=5), mark_price=50, ts=ts)
    assert order.status.value in {"filled", "partial", "submitted"}
    assert len(b.fills()) >= 1 or order.status.value == "submitted"
