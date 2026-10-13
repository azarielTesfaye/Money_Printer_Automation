from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from money_printer.indicators import atr, stdev


class PositionSizer(ABC):
    """Convert equity + price (+ optional vol) into a share quantity."""

    @abstractmethod
    def size(
        self,
        *,
        equity: float,
        price: float,
        cash: float,
        closes: list[float] | None = None,
        highs: list[float] | None = None,
        lows: list[float] | None = None,
        signal_strength: float = 1.0,
    ) -> float:
        raise NotImplementedError


@dataclass
class FixedFractionalSizer(PositionSizer):
    """Risk a fixed fraction of equity at the current price."""

    fraction: float = 0.2

    def size(
        self,
        *,
        equity: float,
        price: float,
        cash: float,
        closes: list[float] | None = None,
        highs: list[float] | None = None,
        lows: list[float] | None = None,
        signal_strength: float = 1.0,
    ) -> float:
        if price <= 0 or equity <= 0:
            return 0.0
        strength = max(0.0, min(1.0, signal_strength))
        budget = equity * self.fraction * strength
        qty = budget / price
        return max(0.0, min(qty, cash / price))


@dataclass
class VolatilityTargetSizer(PositionSizer):
    """Size so estimated daily vol contribution ≈ target_vol * equity."""

    target_vol: float = 0.15
    lookback: int = 20
    periods_per_year: float = 252.0
    max_fraction: float = 0.35

    def size(
        self,
        *,
        equity: float,
        price: float,
        cash: float,
        closes: list[float] | None = None,
        highs: list[float] | None = None,
        lows: list[float] | None = None,
        signal_strength: float = 1.0,
    ) -> float:
        if price <= 0 or equity <= 0 or not closes or len(closes) < self.lookback + 1:
            return FixedFractionalSizer(self.max_fraction).size(
                equity=equity, price=price, cash=cash, signal_strength=signal_strength
            )
        rets = [
            (closes[i] / closes[i - 1]) - 1.0
            for i in range(len(closes) - self.lookback, len(closes))
            if closes[i - 1] > 0
        ]
        vol = stdev(rets, len(rets)) if len(rets) > 1 else None
        if vol is None or vol <= 1e-12:
            return 0.0
        annual_vol = vol * (self.periods_per_year**0.5)
        raw_fraction = (self.target_vol / annual_vol) * max(0.0, min(1.0, signal_strength))
        fraction = min(self.max_fraction, max(0.0, raw_fraction))
        qty = (equity * fraction) / price
        return max(0.0, min(qty, cash / price))


@dataclass
class AtrRiskSizer(PositionSizer):
    """Risk a fixed dollar amount per ATR stop distance."""

    risk_pct: float = 0.01
    atr_period: int = 14
    atr_stop_mult: float = 2.0
    max_fraction: float = 0.3

    def size(
        self,
        *,
        equity: float,
        price: float,
        cash: float,
        closes: list[float] | None = None,
        highs: list[float] | None = None,
        lows: list[float] | None = None,
        signal_strength: float = 1.0,
    ) -> float:
        if price <= 0 or equity <= 0 or not closes or not highs or not lows:
            return 0.0
        atr_v = atr(highs, lows, closes, self.atr_period)
        if atr_v is None or atr_v <= 0:
            return 0.0
        stop_dist = atr_v * self.atr_stop_mult
        risk_dollars = equity * self.risk_pct * max(0.0, min(1.0, signal_strength))
        qty = risk_dollars / stop_dist
        cap = (equity * self.max_fraction) / price
        return max(0.0, min(qty, cap, cash / price))


@dataclass
class KellySizer(PositionSizer):
    """Fractional Kelly using estimated edge and odds from recent trades."""

    win_rate: float = 0.55
    avg_win: float = 1.0
    avg_loss: float = 1.0
    fraction_of_kelly: float = 0.5
    max_fraction: float = 0.25

    def size(
        self,
        *,
        equity: float,
        price: float,
        cash: float,
        closes: list[float] | None = None,
        highs: list[float] | None = None,
        lows: list[float] | None = None,
        signal_strength: float = 1.0,
    ) -> float:
        if price <= 0 or equity <= 0 or self.avg_loss <= 0:
            return 0.0
        b = self.avg_win / self.avg_loss
        p = max(0.0, min(1.0, self.win_rate))
        q = 1.0 - p
        kelly = p - (q / b) if b > 0 else 0.0
        kelly = max(0.0, kelly) * self.fraction_of_kelly * max(0.0, min(1.0, signal_strength))
        kelly = min(self.max_fraction, kelly)
        qty = (equity * kelly) / price
        return max(0.0, min(qty, cash / price))


def build_sizer(name: str, **params: float | int) -> PositionSizer:
    key = name.lower().strip()
    if key in {"fixed", "fixed_fractional", "ff"}:
        return FixedFractionalSizer(fraction=float(params.get("fraction", 0.2)))
    if key in {"vol", "volatility", "vol_target"}:
        return VolatilityTargetSizer(
            target_vol=float(params.get("target_vol", 0.15)),
            lookback=int(params.get("lookback", 20)),
            max_fraction=float(params.get("max_fraction", 0.35)),
        )
    if key in {"atr", "atr_risk"}:
        return AtrRiskSizer(
            risk_pct=float(params.get("risk_pct", 0.01)),
            atr_period=int(params.get("atr_period", 14)),
            atr_stop_mult=float(params.get("atr_stop_mult", 2.0)),
            max_fraction=float(params.get("max_fraction", 0.3)),
        )
    if key in {"kelly"}:
        return KellySizer(
            win_rate=float(params.get("win_rate", 0.55)),
            avg_win=float(params.get("avg_win", 1.0)),
            avg_loss=float(params.get("avg_loss", 1.0)),
            fraction_of_kelly=float(params.get("fraction_of_kelly", 0.5)),
            max_fraction=float(params.get("max_fraction", 0.25)),
        )
    raise KeyError(f"Unknown sizer '{name}'")
