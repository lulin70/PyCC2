"""Attack Line System - CC2-style attack visualization with LOS/range checking."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.vec2 import Vec2


class AttackLineStatus(Enum):
    """Status of an attack line."""
    CAN_ATTACK = auto()       # Green: in range, clear LOS
    OUT_OF_RANGE = auto()     # Red: target too far
    BLOCKED = auto()          # Red: blocked by terrain/obstacle
    NO_TARGET = auto()        # No valid target selected
    TRACKING_UNIT = auto()    # Tracking a moving unit target


@dataclass(slots=True)
class AttackTarget:
    """Attack target information."""
    position: Vec2  # World coordinates of target
    unit_id: str | None = None  # If attacking a unit (for tracking)
    is_ground_target: bool = False  # True if attacking ground (smoke, etc.)
    status: AttackLineStatus = AttackLineStatus.NO_TARGET
    distance: float = 0.0
    weapon_range: float = 0.0


@dataclass
class AttackLineState:
    """Current state of attack line being drawn."""
    active: bool = False
    source_unit_id: str | None = None
    source_position: Vec2 | None = None
    current_mouse_pos: tuple[float, float] | None = None  # Screen coords
    current_world_pos: Vec2 | None = None  # World coords
    target: AttackTarget | None = None
    confirmed_target: AttackTarget | None = None  # Locked after click


class AttackLineSystem:
    """
    CC2-style attack line system.

    Features:
    - Green line: Target in range with clear line-of-sight
    - Red line: Target out of range or blocked
    - Ground targets: Fixed position (smoke, artillery)
    - Unit targets: Auto-follows unit movement
    """

    # Colors for attack lines (RGBA)
    COLOR_CAN_ATTACK: tuple[int, int, int, int] = (0, 255, 0, 200)      # Green
    COLOR_OUT_OF_RANGE: tuple[int, int, int, int] = (255, 50, 50, 200)   # Red
    COLOR_BLOCKED: tuple[int, int, int, int] = (255, 100, 0, 200)       # Orange
    COLOR_TRACKING: tuple[int, int, int, int] = (255, 255, 0, 200)      # Yellow
    LINE_WIDTH: int = 2
    DASH_LENGTH: int = 8  # For dashed effect

    def __init__(self) -> None:
        self.state = AttackLineState()
        self._confirmed_attacks: dict[str, AttackTarget] = {}  # unit_id -> locked target

    def begin_attack(self, unit_id: str, source_pos: Vec2) -> None:
        """Start drawing attack line from this unit."""
        self.state.active = True
        self.state.source_unit_id = unit_id
        self.state.source_position = source_pos
        self.state.current_mouse_pos = None
        self.state.current_world_pos = None
        self.state.target = None
        self.state.confirmed_target = None

    def update_mouse_position(
        self,
        screen_pos: tuple[float, float],
        world_pos: Vec2,
        units: list[Unit],
        attacker_faction: str,
    ) -> AttackTarget:
        """Update attack line endpoint based on mouse position."""
        if not self.state.active or not self.state.source_position:
            return AttackTarget(position=world_pos)

        self.state.current_mouse_pos = screen_pos
        self.state.current_world_pos = world_pos

        # Check if hovering over enemy unit
        target_unit = None
        for unit in units:
            if unit.faction != attacker_faction and unit.is_alive:
                upos = unit.position.pixel_position
                dx = world_pos.x - upos.x
                dy = world_pos.y - upos.y
                if dx*dx + dy*dy < 900:  # 30px radius
                    target_unit = unit
                    break

        # Create target
        if target_unit:
            target_pos = target_unit.position.pixel_position
            target = AttackTarget(
                position=target_pos,
                unit_id=target_unit.id,
                is_ground_target=False,
            )
        else:
            target = AttackTarget(
                position=world_pos,
                unit_id=None,
                is_ground_target=True,
            )

        # Calculate distance
        dx = target.position.x - self.state.source_position.x
        dy = target.position.y - self.state.source_position.y
        target.distance = math.sqrt(dx*dx + dy*dy)

        self.state.target = target
        return target

    def confirm_attack(self, target: AttackTarget) -> None:
        """Lock in the attack target."""
        if self.state.source_unit_id:
            self._confirmed_attacks[self.state.source_unit_id] = target
            self.state.confirmed_target = target
        self.cancel()

    def cancel(self) -> None:
        """Cancel current attack line drawing."""
        self.state.active = False
        self.state.source_unit_id = None
        self.state.source_position = None
        self.state.current_mouse_pos = None
        self.state.current_world_pos = None
        self.state.target = None

    def get_confirmed_attack(self, unit_id: str) -> AttackTarget | None:
        """Get confirmed attack target for a unit."""
        return self._confirmed_attacks.get(unit_id)

    def update_tracking(self, units: list[Unit]) -> None:
        """Update tracking positions for unit targets."""
        for unit_id, target in list(self._confirmed_attacks.items()):
            if target.unit_id and not target.is_ground_target:
                # Find the target unit and update position
                for unit in units:
                    if unit.id == target.unit_id and unit.is_alive:
                        target.position = unit.position.pixel_position
                        break
                else:
                    # Target unit eliminated, remove attack
                    del self._confirmed_attacks[unit_id]

    def evaluate_attack(
        self,
        attacker: Unit,
        target: AttackTarget,
        game_map=None,
    ) -> AttackLineStatus:
        """
        Evaluate if attack is possible.
        Returns the status (CAN_ATTACK, OUT_OF_RANGE, BLOCKED).
        """
        if not attacker.weapon:
            return AttackLineStatus.NO_TARGET

        # Check range
        weapon_range = getattr(attacker.weapon, 'max_range', 300)  # Default 300px (~10 tiles)
        target.weapon_range = weapon_range

        if target.distance > weapon_range:
            return AttackLineStatus.OUT_OF_RANGE

        # TODO: Implement LOS check using game_map terrain
        # For now, assume clear LOS if in range
        # This would check for buildings, hills blocking view

        return AttackLineStatus.CAN_ATTACK

    def get_line_color(self, status: AttackLineStatus) -> tuple[int, int, int, int]:
        """Get color based on attack status."""
        colors = {
            AttackLineStatus.CAN_ATTACK: self.COLOR_CAN_ATTACK,
            AttackLineStatus.OUT_OF_RANGE: self.COLOR_OUT_OF_RANGE,
            AttackLineStatus.BLOCKED: self.COLOR_BLOCKED,
            AttackLineStatus.TRACKING: self.COLOR_TRACKING,
            AttackLineStatus.NO_TARGET: (128, 128, 128, 100),
        }
        return colors.get(status, self.COLOR_OUT_OF_RANGE)

    def remove_attack(self, unit_id: str) -> None:
        """Remove confirmed attack for a unit."""
        self._confirmed_attacks.pop(unit_id, None)

    def clear_all(self) -> None:
        """Clear all attacks."""
        self._confirmed_attacks.clear()
        self.cancel()
