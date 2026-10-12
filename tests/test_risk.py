from pathlib import Path

from money_printer.config import ProfileSettings
from money_printer.models import Side, Signal
from money_printer.portfolio import Portfolio
from money_printer.risk import RiskGate


def test_kill_switch(tmp_path: Path):
    stop = tmp_path / "STOP"
    stop.write_text("1")
    settings = ProfileSettings(stop_file=str(stop))
    gate = RiskGate(settings)
    port = Portfolio(10_000)
    ok, reason = gate.allow(Signal("X", Side.BUY), port, 10.0, 10_000)
    assert not ok
    assert reason == "kill_switch"


def test_max_open_positions():
    settings = ProfileSettings(max_open_positions=1)
    gate = RiskGate(settings)
    port = Portfolio(10_000)
    from money_printer.models import Position

    port.positions["A"] = Position(symbol="A", qty=10, avg_cost=5)
    ok, reason = gate.allow(Signal("B", Side.BUY), port, 10.0, 10_000)
    assert not ok
    assert reason == "max_open_positions"
