from __future__ import annotations

from typing import NotRequired, Required, TypedDict


class PlayerCommand(TypedDict, total=False):
    command: Required[str]
    unit_ids: Required[list[str]]
    target_id: NotRequired[str]
    target: NotRequired[tuple[int, int]]
    timestamp: float
