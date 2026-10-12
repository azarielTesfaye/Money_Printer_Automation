from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Optional

from money_printer.data.base import MarketDataProvider
from money_printer.models import Bar

log = logging.getLogger(__name__)


class YahooFinanceProvider(MarketDataProvider):
    """Public chart API adapter with retry/backoff. Optional — CSV is the default offline path."""

    BASE = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    def __init__(self, timeout: float = 20.0, max_retries: int = 3) -> None:
        self.timeout = timeout
        self.max_retries = max_retries

    def history(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[Bar]:
        params: dict[str, str] = {"interval": "1d", "range": "1y"}
        if start and end:
            params = {
                "interval": "1d",
                "period1": str(int(start.timestamp())),
                "period2": str(int(end.timestamp())),
            }

        url = self.BASE.format(symbol=symbol) + "?" + urllib.parse.urlencode(params)
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "money-printer/0.1"})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    payload = json.loads(resp.read().decode())
                return self._parse(symbol, payload)
            except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
                last_err = exc
                log.warning("yahoo_fetch_failed attempt=%s error=%s", attempt, exc)
                time.sleep(0.5 * attempt)
        raise RuntimeError(f"Yahoo fetch failed for {symbol}: {last_err}")

    @staticmethod
    def _parse(symbol: str, payload: dict) -> list[Bar]:
        result = payload["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        bars: list[Bar] = []
        for i, ts in enumerate(timestamps):
            o, h, l, c, v = (
                quote["open"][i],
                quote["high"][i],
                quote["low"][i],
                quote["close"][i],
                quote["volume"][i],
            )
            if None in (o, h, l, c):
                continue
            bars.append(
                Bar(
                    symbol=symbol,
                    ts=datetime.utcfromtimestamp(ts),
                    open=float(o),
                    high=float(h),
                    low=float(l),
                    close=float(c),
                    volume=float(v or 0),
                )
            )
        return bars
