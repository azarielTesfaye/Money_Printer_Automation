from money_printer.brokers.alpaca_sandbox import AlpacaCredentials, AlpacaSandboxBroker
from money_printer.brokers.base import Broker, BrokerOrder, OrderStatus
from money_printer.brokers.binance_sandbox import BinanceCredentials, BinanceSandboxBroker
from money_printer.brokers.paper import PaperBroker
from money_printer.brokers.simulated import SimulatedExchangeBroker


def build_broker(name: str, **kwargs) -> Broker:
    key = name.lower().strip()
    if key in {"paper"}:
        return PaperBroker(**{k: v for k, v in kwargs.items() if k in {"starting_cash", "slippage_bps", "commission_per_fill"}})
    if key in {"simulated", "sim"}:
        return SimulatedExchangeBroker(
            **{
                k: v
                for k, v in kwargs.items()
                if k
                in {
                    "starting_cash",
                    "slippage_bps",
                    "commission_per_fill",
                    "partial_fill_prob",
                    "reject_prob",
                    "seed",
                }
            }
        )
    if key in {"alpaca", "alpaca_sandbox"}:
        return AlpacaSandboxBroker(
            offline=bool(kwargs.get("offline", True)),
            starting_cash=float(kwargs.get("starting_cash", 100_000.0)),
        )
    if key in {"binance", "binance_sandbox"}:
        return BinanceSandboxBroker(
            offline=bool(kwargs.get("offline", True)),
            starting_cash=float(kwargs.get("starting_cash", 100_000.0)),
            seed=int(kwargs.get("seed", 7)),
        )
    raise KeyError(f"Unknown broker '{name}'")


__all__ = [
    "Broker",
    "BrokerOrder",
    "OrderStatus",
    "PaperBroker",
    "SimulatedExchangeBroker",
    "AlpacaSandboxBroker",
    "AlpacaCredentials",
    "BinanceSandboxBroker",
    "BinanceCredentials",
    "build_broker",
]
