from money_printer.strategies.base import Strategy, registry
from money_printer.strategies.rsi import RsiMeanReversion
from money_printer.strategies.sma import SmaCrossover

# Side-effect registration
registry.register("sma", SmaCrossover)
registry.register("rsi", RsiMeanReversion)

__all__ = ["Strategy", "registry", "SmaCrossover", "RsiMeanReversion"]
