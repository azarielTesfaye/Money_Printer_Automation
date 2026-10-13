"""Stdlib HTTP API + dashboard (no FastAPI/pydantic required)."""

from money_printer.api.app import create_app, handle_request, serve_app

__all__ = ["create_app", "handle_request", "serve_app"]
