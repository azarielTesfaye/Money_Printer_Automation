from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

log = logging.getLogger(__name__)


class WebhookNotifier:
    def __init__(self, url: str | None) -> None:
        self.url = url

    def send(self, title: str, body: dict[str, Any]) -> bool:
        if not self.url:
            log.debug("webhook_skipped_no_url")
            return False
        payload = json.dumps({"content": f"**{title}**\n```json\n{json.dumps(body, default=str)}\n```"}).encode()
        req = urllib.request.Request(
            self.url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return 200 <= getattr(resp, "status", 200) < 300
        except urllib.error.URLError as exc:
            log.warning("webhook_failed error=%s", exc)
            return False
