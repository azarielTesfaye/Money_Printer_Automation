from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, Optional

from money_printer.models import Bar


class MarketDataProvider(ABC):
    """Interface for historical or live OHLCV sources."""

    @abstractmethod
    def history(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[Bar]:
        raise NotImplementedError

    def stream(self, symbol: str) -> Iterable[Bar]:
        """Default stream: yield each historical bar in order."""
        yield from self.history(symbol)
