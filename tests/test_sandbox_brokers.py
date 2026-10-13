from datetime import datetime

from money_printer.brokers import build_broker
from money_printer.brokers.alpaca_sandbox import AlpacaSandboxBroker
from money_printer.brokers.base import BrokerOrder
from money_printer.brokers.binance_sandbox import BinanceSandboxBroker
from money_printer.models import Side


def test_alpaca_and_binance_offline_fill():
    ts = datetime(2024, 1, 1)
    alpaca = AlpacaSandboxBroker(starting_cash=20_000, offline=True)
    buy = alpaca.submit(BrokerOrder(symbol="AAPL", side=Side.BUY, qty=5), mark_price=100, ts=ts)
    assert buy.status.value == "filled"
    assert alpaca.cash() < 20_000
    assert alpaca.account_summary()["mode"] == "offline"

    binance = BinanceSandboxBroker(starting_cash=20_000, offline=True, seed=2)
    order = binance.submit(BrokerOrder(symbol="BTCUSDT", side=Side.BUY, qty=1), mark_price=100, ts=ts)
    assert order.status.value in {"filled", "partial", "submitted", "rejected"}


def test_build_broker_factory():
    assert build_broker("paper").name == "paper"
    assert build_broker("alpaca", offline=True).name == "alpaca_sandbox"
    assert build_broker("binance", offline=True).name == "binance_sandbox"
