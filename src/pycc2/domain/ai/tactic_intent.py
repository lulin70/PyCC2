"""Tactic intent types and data carried between AI decision layers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.value_objects.tile_coord import TileCoord


class TacticType(Enum):
    """Discrete tactical intents dispatched to units for execution."""

    IDLE = auto()
    PATROL = auto()
    MOVE_TO = auto()
    ATTACK = auto()
    RETREAT = auto()
    SUPPRESS_FIRE = auto()
    DEFEND = auto()
    HOLD_POSITION = auto()
    TAKE_COVER = auto()
    REGROUP = auto()
    FLANKING = auto()
    COORDINATED_ADVANCE = auto()
    CAPTURE_VL = auto()
    DEFEND_VL = auto()
    DEMOLISH_BRIDGE = auto()
    SCAVENGE_AMMO = auto()
    SURRENDER = auto()
    DEPLOY_SMOKE = auto()
    RALLY_NCO = auto()
    HEAL_WOUNDED = auto()
    DIG_TRENCH = auto()
    CLEAR_BUILDING = auto()
    CALL_ARTILLERY = auto()
    MELEE_ATTACK = auto()
    MOUNT_TANK = auto()
    DISMOUNT_TANK = auto()
    LAY_MINE = auto()
    DETECT_MINES = auto()
    ASSAULT_FORTIFIED = auto()
    COUNTER_ATTACK = auto()  # Strategic counterattack after reinforcement
    SET_AMBUSH = auto()  # 设置伏击（隐蔽等待）
    BREAK_AMBUSH = auto()  # 触发伏击（集中开火）


@dataclass(slots=True)
class TacticIntent:
    """Concrete order carrying a tactic type, priority, and optional target for a unit."""

    unit_id: str
    tactic_type: TacticType
    priority: int = 0
    target_position: TileCoord | None = None
    target_unit_id: str | None = None
    path: list[TileCoord] | None = None

    @property
    def has_target(self) -> bool:
        """Return whether the intent carries a position or unit target."""
        return self.target_position is not None or self.target_unit_id is not None
