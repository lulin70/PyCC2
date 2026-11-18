from __future__ import annotations

from typing import NotRequired, Required, TypedDict


class PlayerCommand(TypedDict, total=False):
    command: Required[str]
    unit_ids: Required[list[str]]
    target_id: NotRequired[str]
    target: NotRequired[tuple[int, int]]
    timestamp: float
    # MC2-01: issuing side ("player" / "commander" / "self"); absent = player.
    origin: NotRequired[str]
