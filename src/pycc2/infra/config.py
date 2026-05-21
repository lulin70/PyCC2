from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Settings:
    tick_rate: float = 60.0
    debug: bool = False
    log_level: str = "INFO"
