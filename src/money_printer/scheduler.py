from __future__ import annotations

import logging
import signal
import time
from datetime import datetime

from money_printer.config import ProfileSettings
from money_printer.data.base import MarketDataProvider
from money_printer.engine import BacktestEngine
from money_printer.health import write_health
from money_printer.journal import TradeJournal
from money_printer.notifier import WebhookNotifier
from money_printer.strategies.base import Strategy

log = logging.getLogger(__name__)


class DaemonLoop:
    """Poll-style paper loop: re-run strategy on latest history each interval."""

    def __init__(
        self,
        settings: ProfileSettings,
        strategy: Strategy,
        provider: MarketDataProvider,
        symbol: str,
        notifier: WebhookNotifier | None = None,
        dry_run: bool = False,
    ) -> None:
        self.settings = settings
        self.strategy = strategy
        self.provider = provider
        self.symbol = symbol
        self.notifier = notifier or WebhookNotifier(None)
        self.dry_run = dry_run
        self._stop = False

    def _handle_sig(self, *_: object) -> None:
        log.info("shutdown_requested")
        self._stop = True

    def run_forever(self) -> None:
        signal.signal(signal.SIGINT, self._handle_sig)
        try:
            signal.signal(signal.SIGTERM, self._handle_sig)
        except (AttributeError, ValueError):
            pass

        journal = TradeJournal(self.settings.journal_path)
        while not self._stop:
            try:
                engine = BacktestEngine(
                    self.settings,
                    self.strategy,
                    self.provider,
                    dry_run=self.dry_run,
                    journal=journal,
                )
                report = engine.run(self.symbol)
                write_health(
                    self.settings.health_path,
                    ok=True,
                    extra={"symbol": self.symbol, "final_equity": report["final_equity"]},
                )
                self.notifier.send("money-printer tick", report)
            except Exception as exc:  # noqa: BLE001
                log.exception("daemon_tick_failed")
                write_health(self.settings.health_path, ok=False, last_error=str(exc))
            time.sleep(self.settings.poll_interval_sec)
        journal.close()
