"""Attack Line System - CC2-style attack visualization with LOS/range checking."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

from pycc2.domain.entities.unit import Faction

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.vec2 import Vec2


class AttackLineStatus(Enum):
    """Status of an attack line."""

    CAN_ATTACK = auto()  # Green: in range, clear LOS
    OUT_OF_RANGE = auto()  # Red: target too far
    BLOCKED = auto()  # Red: blocked by terrain/obstacle
    NO_TARGET = auto()  # No valid target selected
    TRACKING_UNIT = auto()  # Tracking a moving unit target
    # CC2 4-color hit probability system
    HIT_HIGH = auto()  # Green (60-100%): High hit chance
    HIT_MODERATE = auto()  # Yellow (30-59%): Moderate hit chance
    HIT_LOW = auto()  # Red (10-29%): Low hit chance
    HIT_IMPOSSIBLE = auto()  # Black (0-9%): Cannot hit


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
    """CC2-style attack line system.

    Features:
    - Green line: Target in range with clear line-of-sight
    - Red line: Target out of range or blocked
    - Ground targets: Fixed position (smoke, artillery)
    - Unit targets: Auto-follows unit movement
    """

    # Colors for attack lines (RGBA)
    COLOR_CAN_ATTACK: tuple[int, int, int, int] = (0, 255, 0, 200)  # Green
    COLOR_OUT_OF_RANGE: tuple[int, int, int, int] = (255, 50, 50, 200)  # Red
    COLOR_BLOCKED: tuple[int, int, int, int] = (255, 100, 0, 200)  # Orange
    COLOR_TRACKING: tuple[int, int, int, int] = (255, 255, 0, 200)  # Yellow
    # CC2 4-color hit probability colors
    COLOR_HIT_HIGH: tuple[int, int, int, int] = (0, 255, 0, 200)  # Green (60-100%)
    COLOR_HIT_MODERATE: tuple[int, int, int, int] = (255, 255, 0, 200)  # Yellow (30-59%)
    COLOR_HIT_LOW: tuple[int, int, int, int] = (255, 50, 50, 200)  # Red (10-29%)
    COLOR_HIT_IMPOSSIBLE: tuple[int, int, int, int] = (0, 0, 0, 200)  # Black (0-9%)
    LINE_WIDTH: int = 2
    DASH_LENGTH: int = 8  # For dashed effect

    def __init__(self) -> None:
        self.state = AttackLineState()
        self._confirmed_attacks: dict[str, AttackTarget] = {}  # unit_id -> locked target
        # R8: Attack line fade-out animation
        self._fading_lines: list[dict] = []  # [{source, target, color, alpha, start_tick}]
        self._fade_duration_ms: int = 1500  # 1.5 seconds fade
        self._active_source = None

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
        attacker_faction: str | Faction,
    ) -> AttackTarget:
        """Update attack line endpoint based on mouse position."""
        if not self.state.active or not self.state.source_position:
            return AttackTarget(position=world_pos)

        self.state.current_mouse_pos = screen_pos
        self.state.current_world_pos = world_pos

        # Check if hovering over enemy unit
        target_unit = None
        attacker_name = (
            attacker_faction.name if isinstance(attacker_faction, Faction) else attacker_faction
        )
        for unit in units:
            if unit.faction.name != attacker_name and unit.is_alive:
                upos = unit.position.pixel_position
                dx = world_pos.x - upos.x
                dy = world_pos.y - upos.y
                if dx * dx + dy * dy < 900:  # 30px radius
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
        target.distance = math.sqrt(dx * dx + dy * dy)

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
        los_system=None,
    ) -> AttackLineStatus:
        """Evaluate if attack is possible and return CC2 4-color hit probability status.

        Factors in: distance, cover/concealment, attacker accuracy (fatigue, veterancy, mode), weather.
        """
        if not attacker.weapon:
            return AttackLineStatus.NO_TARGET

        weapon_range = (
            getattr(attacker.weapon, "max_range", 300) if attacker.weapon is not None else 300
        )
        target.weapon_range = weapon_range

        if target.distance > weapon_range:
            return AttackLineStatus.OUT_OF_RANGE

        if los_system and game_map:
            try:
                from pycc2.domain.value_objects.tile_coord import TileCoord

                from_coord = TileCoord(
                    int(attacker.position.tile_coord.x),
                    int(attacker.position.tile_coord.y),
                )
                to_coord = TileCoord(
                    int(target.position.x // 32),
                    int(target.position.y // 32),
                )
                can_see, los_result = los_system.check_los(from_coord, to_coord)

                if not can_see:
                    return AttackLineStatus.BLOCKED
            except (ValueError, TypeError, AttributeError) as e:
                logger.warning("[AttackLine] LOS check failed: %s, assuming clear", e)

        # Calculate hit probability for 4-color system
        hit_prob = self.calculate_hit_probability(attacker, target, game_map)
        return self._hit_probability_to_status(hit_prob)

    @staticmethod
    def calculate_hit_probability(
        attacker: Unit,
        target: AttackTarget,
        game_map=None,
    ) -> float:
        """Calculate hit probability (0.0 - 1.0) factoring in:
        - Distance ratio (closer = higher)
        - Cover/concealment of target
        - Attacker's accuracy modifier (fatigue, veterancy, mode)
        - Weather effects
        """
        # Base probability from distance ratio
        weapon_range = (
            getattr(attacker.weapon, "max_range", 300) if attacker.weapon is not None else 300
        )
        if weapon_range <= 0:
            return 0.0
        distance_ratio = min(target.distance / weapon_range, 1.0)
        # Optimal range is 0-30%, linear degradation after that
        base_prob = 0.9 if distance_ratio <= 0.3 else 0.9 - 0.7 * ((distance_ratio - 0.3) / 0.7)
        base_prob = max(base_prob, 0.05)

        # Cover/concealment penalty for target
        cover_penalty = 0.0
        if game_map is not None:
            try:
                tx = int(target.position.x // 32)
                ty = int(target.position.y // 32)
                tile = game_map.get_tile(tx, ty) if hasattr(game_map, "get_tile") else None
                if tile is not None:
                    cover_level = getattr(tile, "cover_level", 0)
                    concealment = getattr(tile, "concealment", 0)
                    cover_penalty = cover_level * 0.15 + concealment * 0.10
            except (ValueError, TypeError, AttributeError) as e:
                logging.debug("Cover penalty calculation failed: %s", e)

        # Attacker accuracy modifier (fatigue, veterancy, mode)
        accuracy_mod = 1.0
        # Fatigue penalty
        fatigue_attr = getattr(attacker, "fatigue", 0)
        fatigue_val = fatigue_attr.value if hasattr(fatigue_attr, "value") else fatigue_attr
        if isinstance(fatigue_val, (int, float)):
            if fatigue_val > 70:
                accuracy_mod *= 0.7
            elif fatigue_val > 40:
                accuracy_mod *= 0.85
        # Veterancy bonus
        experience_level = getattr(attacker, "experience_level", 0)
        if experience_level >= 3:  # Elite
            accuracy_mod *= 1.2
        elif experience_level >= 2:  # Veteran
            accuracy_mod *= 1.1
        # Mode penalty (moving/sneaking reduces accuracy)
        if hasattr(attacker, "move_mode"):
            mode = attacker.move_mode
            if mode == "fast":
                accuracy_mod *= 0.5
            elif mode == "sneak":
                accuracy_mod *= 0.8
        # Morale accuracy modifier
        if attacker.morale is not None:
            from pycc2.domain.systems.morale_system import MoraleSystem

            morale_state = MoraleSystem.get_state(attacker.morale.value)
            accuracy_mod *= MoraleSystem.get_accuracy_modifier(morale_state)

        # Weather penalty
        weather_penalty = 0.0
        if game_map is not None:
            weather = getattr(game_map, "weather", None)
            if weather is not None:
                weather_str = str(weather).lower()
                if "rain" in weather_str:
                    weather_penalty = 0.10
                elif "fog" in weather_str:
                    weather_penalty = 0.20
                elif "snow" in weather_str:
                    weather_penalty = 0.15

        # Captured weapon penalty
        if attacker.weapon is not None and attacker.weapon.is_captured:
            accuracy_mod *= 0.8

        hit_prob = base_prob - cover_penalty - weather_penalty
        hit_prob *= accuracy_mod
        return max(0.0, min(hit_prob, 1.0))

    @staticmethod
    def _hit_probability_to_status(hit_prob: float) -> AttackLineStatus:
        """Map hit probability to CC2 4-color status."""
        if hit_prob >= 0.60:
            return AttackLineStatus.HIT_HIGH
        elif hit_prob >= 0.30:
            return AttackLineStatus.HIT_MODERATE
        elif hit_prob >= 0.10:
            return AttackLineStatus.HIT_LOW
        else:
            return AttackLineStatus.HIT_IMPOSSIBLE

    def get_line_color(self, status: AttackLineStatus) -> tuple[int, int, int, int]:
        """Get color based on attack status."""
        colors = {
            AttackLineStatus.CAN_ATTACK: self.COLOR_CAN_ATTACK,
            AttackLineStatus.OUT_OF_RANGE: self.COLOR_OUT_OF_RANGE,
            AttackLineStatus.BLOCKED: self.COLOR_BLOCKED,
            AttackLineStatus.TRACKING_UNIT: self.COLOR_TRACKING,
            AttackLineStatus.NO_TARGET: (128, 128, 128, 100),
            # CC2 4-color hit probability
            AttackLineStatus.HIT_HIGH: self.COLOR_HIT_HIGH,
            AttackLineStatus.HIT_MODERATE: self.COLOR_HIT_MODERATE,
            AttackLineStatus.HIT_LOW: self.COLOR_HIT_LOW,
            AttackLineStatus.HIT_IMPOSSIBLE: self.COLOR_HIT_IMPOSSIBLE,
        }
        return colors.get(status, self.COLOR_OUT_OF_RANGE)

    def remove_attack(self, unit_id: str) -> None:
        """Remove confirmed attack for a unit, starting fade-out animation."""
        target = self._confirmed_attacks.get(unit_id)
        if target is not None:
            # R8: Start fade-out animation instead of instant removal
            source_pos = self._active_source
            if source_pos is not None:
                import time

                self._fading_lines.append(
                    {
                        "source": source_pos,
                        "target": target.position,
                        "color": self.COLOR_CAN_ATTACK[:3],
                        "alpha": 200,
                        "start_tick": time.monotonic(),
                    }
                )
        self._confirmed_attacks.pop(unit_id, None)

    def update_fading(self) -> list[dict]:
        """R8: Update fading attack lines. Returns list of still-visible fading lines."""
        import time

        now = time.monotonic()
        remaining = []
        for line in self._fading_lines:
            elapsed_ms = (now - line["start_tick"]) * 1000
            if elapsed_ms < self._fade_duration_ms:
                line["alpha"] = int(200 * (1.0 - elapsed_ms / self._fade_duration_ms))
                remaining.append(line)
        self._fading_lines = remaining
        return remaining

    def clear_all(self) -> None:
        """Clear all attacks."""
        self._confirmed_attacks.clear()
        self.cancel()
