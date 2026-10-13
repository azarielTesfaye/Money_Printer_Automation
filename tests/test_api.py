from pathlib import Path

from money_printer.api.app import create_app, handle_request


def test_api_health_strategies_backtest_order(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    state = create_app(
        db_path=str(tmp_path / "app.db"),
        event_path=str(tmp_path / "events.db"),
        broker_name="paper",
    )
    try:
        status, health, _ = handle_request(state, "GET", "/health", {}, {})
        assert status == 200 and health["ok"] is True

        status, strategies, _ = handle_request(state, "GET", "/strategies", {}, {})
        assert status == 200 and "sma" in strategies["strategies"]

        status, report, _ = handle_request(
            state,
            "POST",
            "/backtests",
            {
                "strategy": "sma",
                "symbol": "DEMO",
                "csv": str(root / "data" / "sample_ohlcv.csv"),
                "analytics": False,
            },
            {},
        )
        assert status == 200
        assert "final_equity" in report
        assert report.get("run_id")

        status, runs, _ = handle_request(state, "GET", "/backtests", {}, {})
        assert status == 200 and len(runs["runs"]) >= 1

        status, order, _ = handle_request(
            state,
            "POST",
            "/orders",
            {"symbol": "DEMO", "side": "buy", "qty": 1, "mark_price": 100},
            {},
        )
        assert status == 200
        assert order["lifecycle"] in {"filled", "rejected", "acknowledged", "partially_filled"}

        assert handle_request(state, "GET", "/orders", {}, {})[0] == 200
        assert handle_request(state, "GET", "/account", {}, {})[0] == 200
        assert handle_request(state, "GET", "/events", {}, {})[0] == 200
        status, _, html = handle_request(state, "GET", "/", {}, {})
        assert status == 200 and html and "Money Printer" in html
    finally:
        state.close()
