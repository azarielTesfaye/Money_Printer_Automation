from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Type

from money_printer.models import Bar, Signal


class Strategy(ABC):
    name: str = "base"

    def __init__(self, **params: float | int) -> None:
        self.params = params

    @abstractmethod
    def on_bar(self, bar: Bar, history: list[Bar]) -> Signal | None:
        raise NotImplementedError


class StrategyRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, Type[Strategy]] = {}

    def register(self, name: str, cls: Type[Strategy]) -> None:
        self._factories[name] = cls

    def create(self, name: str, **params: float | int) -> Strategy:
        if name not in self._factories:
            raise KeyError(f"Unknown strategy '{name}'. Available: {sorted(self._factories)}")
        return self._factories[name](**params)

    def names(self) -> list[str]:
        return sorted(self._factories)


registry = StrategyRegistry()
