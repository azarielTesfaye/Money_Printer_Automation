from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def write_health(path: str | Path, *, ok: bool, last_error: str | None = None, extra: dict | None = None) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "last_error": last_error,
        **(extra or {}),
    }
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
