from money_printer.strategies.atr_breakout import AtrChannelBreakout
from money_printer.strategies.base import Strategy, registry
from money_printer.strategies.bollinger import BollingerMeanReversion
from money_printer.strategies.macd import MacdCrossover
from money_printer.strategies.momentum import MomentumBreakout
from money_printer.strategies.rsi import RsiMeanReversion
from money_printer.strategies.sma import SmaCrossover

registry.register("sma", SmaCrossover)
registry.register("rsi", RsiMeanReversion)
registry.register("macd", MacdCrossover)
registry.register("bollinger", BollingerMeanReversion)
registry.register("momentum", MomentumBreakout)
registry.register("atr_breakout", AtrChannelBreakout)

__all__ = [
    "Strategy",
    "registry",
    "SmaCrossover",
    "RsiMeanReversion",
    "MacdCrossover",
    "BollingerMeanReversion",
    "MomentumBreakout",
    "AtrChannelBreakout",
]
