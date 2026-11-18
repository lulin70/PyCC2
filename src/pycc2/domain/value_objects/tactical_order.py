"""TacticalOrder — unified immutable command record for the order layer (MC2-01).

Every battle command (player click, AI commander decision) is normalized into
a ``TacticalOrder`` before dispatch. ``CombatDirector.issue_order`` is the
single entry point that consumes orders and routes them through the existing
``_CMD_DISPATCH`` table, while keeping one ring-buffered log for replay and
debugging.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class OrderOrigin(Enum):
    """Who issued a tactical order: the player, the AI commander, or the unit itself."""

    PLAYER = "player"
    COMMANDER = "commander"
    SELF = "self"


@dataclass(frozen=True)
class TacticalOrder:
    """One normalized tactical command ready for CombatDirector dispatch.

    ``command`` must match a ``_CMD_DISPATCH`` key; ``params`` carries the
    command payload (``target_id`` / ``target`` / ``fire_mode`` / ...).
    ``issued_tick`` anchors the order on the replay/record timeline.
    """

    command: str
    unit_ids: tuple[str, ...]
    origin: OrderOrigin = OrderOrigin.PLAYER
    params: Mapping[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    issued_tick: int = 0

    def to_command_data(self) -> dict[str, Any]:
        """Build the PlayerCommand-style data view consumed by ``_CMD_DISPATCH`` handlers."""
        data: dict[str, Any] = {
            "command": self.command,
            "unit_ids": list(self.unit_ids),
        }
        data.update(self.params)
        return data
