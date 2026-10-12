from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ProfileSettings:
    starting_cash: float = 100_000.0
    max_position_pct: float = 0.2
    max_open_positions: int = 4
    max_daily_loss_pct: float = 0.03
    slippage_bps: float = 8.0
    commission_per_fill: float = 1.0
    poll_interval_sec: int = 30
    journal_path: str = "data/journal_paper.db"
    health_path: str = "data/health.json"
    stop_file: str = "data/STOP"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProfileSettings":
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed})


@dataclass
class AppSettings:
    profile: str = "paper"
    webhook_url: str | None = None
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "AppSettings":
        return cls(
            profile=os.getenv("MP_PROFILE", "paper"),
            webhook_url=os.getenv("MP_WEBHOOK_URL") or None,
            log_level=os.getenv("MP_LOG_LEVEL", "INFO"),
        )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_yaml_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or (_repo_root() / "config" / "settings.yaml")
    with cfg_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_profile(profile: str | None = None) -> tuple[AppSettings, ProfileSettings, dict[str, Any]]:
    env = AppSettings.from_env()
    name = (profile or env.profile or "paper").lower()
    raw = load_yaml_config()
    profiles = raw.get("profiles", {})
    if name not in profiles:
        raise ValueError(f"Unknown profile '{name}'. Choose from: {sorted(profiles)}")
    profile_cfg = ProfileSettings.from_dict(profiles[name])
    strategies = raw.get("strategies", {})
    return env, profile_cfg, strategies
