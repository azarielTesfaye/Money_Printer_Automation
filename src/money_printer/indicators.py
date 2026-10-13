from __future__ import annotations

import math
from typing import Sequence


def sma(values: Sequence[float], window: int) -> float | None:
    if window <= 0 or len(values) < window:
        return None
    return sum(values[-window:]) / window


def ema(values: Sequence[float], window: int) -> float | None:
    if window <= 0 or len(values) < window:
        return None
    alpha = 2.0 / (window + 1)
    # seed with SMA of first window
    seed = sum(values[:window]) / window
    level = seed
    for v in values[window:]:
        level = alpha * v + (1.0 - alpha) * level
    return level


def ema_series(values: Sequence[float], window: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if window <= 0 or len(values) < window:
        return out
    alpha = 2.0 / (window + 1)
    level = sum(values[:window]) / window
    out[window - 1] = level
    for i in range(window, len(values)):
        level = alpha * values[i] + (1.0 - alpha) * level
        out[i] = level
    return out


def stdev(values: Sequence[float], window: int) -> float | None:
    if window <= 1 or len(values) < window:
        return None
    chunk = values[-window:]
    mean = sum(chunk) / window
    var = sum((x - mean) ** 2 for x in chunk) / (window - 1)
    return math.sqrt(var)


def rsi(closes: Sequence[float], period: int) -> float | None:
    if period <= 0 or len(closes) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    window = closes[-(period + 1) :]
    for i in range(1, len(window)):
        delta = window[i] - window[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    closes: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[float | None, float | None, float | None]:
    """Return (macd_line, signal_line, histogram) for the latest bar."""
    if len(closes) < slow + signal:
        return None, None, None
    fast_s = ema_series(closes, fast)
    slow_s = ema_series(closes, slow)
    macd_line_series: list[float] = []
    for f, s in zip(fast_s, slow_s):
        if f is None or s is None:
            continue
        macd_line_series.append(f - s)
    if len(macd_line_series) < signal:
        return None, None, None
    signal_line = ema(macd_line_series, signal)
    macd_line = macd_line_series[-1]
    if signal_line is None:
        return macd_line, None, None
    return macd_line, signal_line, macd_line - signal_line


def bollinger(
    closes: Sequence[float],
    window: int = 20,
    num_std: float = 2.0,
) -> tuple[float | None, float | None, float | None]:
    mid = sma(closes, window)
    sd = stdev(closes, window)
    if mid is None or sd is None:
        return None, None, None
    return mid - num_std * sd, mid, mid + num_std * sd


def true_range(high: float, low: float, prev_close: float) -> float:
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> float | None:
    if period <= 0 or len(closes) < period + 1:
        return None
    trs: list[float] = []
    for i in range(1, len(closes)):
        trs.append(true_range(highs[i], lows[i], closes[i - 1]))
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def momentum(closes: Sequence[float], lookback: int) -> float | None:
    if lookback <= 0 or len(closes) <= lookback:
        return None
    prev = closes[-(lookback + 1)]
    if prev == 0:
        return None
    return (closes[-1] / prev) - 1.0


def rolling_max(values: Sequence[float], window: int) -> float | None:
    if window <= 0 or len(values) < window:
        return None
    return max(values[-window:])


def rolling_min(values: Sequence[float], window: int) -> float | None:
    if window <= 0 or len(values) < window:
        return None
    return min(values[-window:])
