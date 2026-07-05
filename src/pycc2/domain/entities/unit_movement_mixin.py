"""Unit movement mixin — extracted from unit.py (D12 Phase 4 P0-2 God Class split).

Contains movement-mode and movement-execution methods used by the Unit facade:
  - Movement-mode properties: movement_mode, is_fast_moving, is_sneaking,
    is_defending, can_use_smoke, can_sneak, can_hide.
  - Movement-mode mutation: set_movement_mode, update_movement_mode.
  - Mode-derived modifiers: get_speed_multiplier, get_accuracy_modifier,
    get_detection_modifier.
  - Movement execution: move_to_tile, set_move_target, update_movement.
  - Garrison status: update_garrison_status.

This is a mixin — do not instantiate directly. The Unit facade inherits this
mixin and provides all required fields via its dataclass definition.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.components.fatigue_component import FatigueComponent
    from pycc2.domain.components.position_component import PositionComponent
    from pycc2.domain.components.veterancy_component import VeterancyComponent
    from pycc2.domain.components.weapon_component import WeaponComponent
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import UnitType
    from pycc2.domain.state_machine import StateMachine
    from pycc2.domain.systems.vehicle_crew_system import VehicleCrew
    from pycc2.domain.value_objects.tile_coord import TileCoord

logger = logging.getLogger(__name__)

__all__ = ["UnitMovementMixin"]


class UnitMovementMixin:
    """Movement-mode and movement-execution methods for Unit.

    Inherited by the Unit facade, not instantiated. Provides 16 methods
    covering movement mode (normal/fast_move/sneak/defend), speed/accuracy/
    detection modifiers, and per-tick movement execution with fuel consumption.
    """

    # -- Facade fields used by movement methods (set by Unit dataclass) --
    _movement_mode: str
    _movement_mode_ticks_remaining: int
    _sneak_speed_multiplier: float
    _fast_speed_multiplier: float
    _defend_accuracy_bonus: float
    _defend_mobility_penalty: float
    fatigue: FatigueComponent | None
    veterancy: VeterancyComponent | None
    crew: VehicleCrew | None
    unit_type: UnitType
    weapon: WeaponComponent
    position: PositionComponent
    move_target: TileCoord | None
    state_machine: StateMachine
    fuel: float
    max_fuel: float
    fuel_per_tile: float
    current_building_pos: tuple[int, int] | None
    move_speed: float
    name: str
    id: str
    morale: object  # MoraleComponent, declared as object to avoid circular import

    if TYPE_CHECKING:
        # -- Cross-mixin properties provided by Unit facade (declared for typing
        # only; @property cannot be used inside TYPE_CHECKING at class scope, so
        # we declare them as plain methods which mypy treats as readable attrs). --
        @property
        def is_alive(self) -> bool: ...

        @property
        def is_out_of_fuel(self) -> bool: ...

        # -- Cross-mixin methods provided by UnitCommandQueueMixin via MRO --
        def get_next_queued_command(self) -> dict | None: ...

        def _execute_queued_command(self, cmd: dict) -> None: ...

    # ------------------------------------------------------------------
    # Movement-mode properties (read-only views)
    # ------------------------------------------------------------------

    @property
    def movement_mode(self) -> str:
        """Current movement mode."""
        return self._movement_mode

    @property
    def is_fast_moving(self) -> bool:
        """Check if unit is in fast move mode."""
        return self._movement_mode == "fast_move"

    @property
    def is_sneaking(self) -> bool:
        """Check if unit is in sneak mode."""
        return self._movement_mode == "sneak"

    @property
    def is_defending(self) -> bool:
        """Check if unit is in defend mode."""
        return self._movement_mode == "defend"

    @property
    def can_use_smoke(self) -> bool:
        """Check if unit can deploy smoke (has smoke grenades)."""
        if not hasattr(self, "weapon") or self.weapon is None:
            return False
        # Local import to avoid circular import at module load time.
        from pycc2.domain.entities.unit import UnitType

        return self.unit_type in (
            UnitType.INFANTRY_SQUAD,
            UnitType.MACHINE_GUN_SQUAD,
            UnitType.COMMANDER,
            UnitType.SNIPER_TEAM,
        )

    @property
    def can_sneak(self) -> bool:
        """Check if unit can use sneak mode."""
        from pycc2.domain.entities.unit import UnitType

        return self.unit_type in (
            UnitType.INFANTRY_SQUAD,
            UnitType.SNIPER_TEAM,
            UnitType.COMMANDER,
            UnitType.MEDIC_TEAM,
        )

    @property
    def can_hide(self) -> bool:
        """Check if unit can hide (take cover)."""
        return not getattr(self, "is_vehicle", False)

    # ------------------------------------------------------------------
    # Movement-mode mutation
    # ------------------------------------------------------------------

    def set_movement_mode(self, mode: str, duration_ticks: int = -1) -> None:
        """Set movement mode for the unit.

        Args:
            mode: One of "normal", "fast_move", "sneak", "defend"
            duration_ticks: Duration in game ticks (-1 = indefinite until cancelled)

        """
        valid_modes = {"normal", "fast_move", "sneak", "defend"}
        if mode not in valid_modes:
            raise ValueError(f"Invalid movement mode: {mode}. Must be one of {valid_modes}")

        old_mode = self._movement_mode
        self._movement_mode = mode

        if duration_ticks > 0:
            self._movement_mode_ticks_remaining = duration_ticks
        elif duration_ticks == -1:
            self._movement_mode_ticks_remaining = -1  # Indefinite
        else:
            self._movement_mode_ticks_remaining = 0  # Immediate reset

        if old_mode != mode:
            logger.info(f"[COMMAND] {self.name or self.id} mode change: {old_mode} -> {mode}")

    def update_movement_mode(self) -> None:
        """Update movement mode timer (call once per tick)."""
        if self._movement_mode_ticks_remaining > 0:
            self._movement_mode_ticks_remaining -= 1
            if self._movement_mode_ticks_remaining == 0:
                # Reset to normal when duration expires
                self._movement_mode = "normal"

    # ------------------------------------------------------------------
    # Mode-derived modifiers
    # ------------------------------------------------------------------

    def get_speed_multiplier(self) -> float:
        """Get current speed multiplier based on movement mode.

        Returns:
            Speed multiplier (1.0 = normal, <1.0 = slower, >1.0 = faster)

        """
        if self._movement_mode == "fast_move":
            base = self._fast_speed_multiplier
        elif self._movement_mode == "sneak":
            base = self._sneak_speed_multiplier
        elif self._movement_mode == "defend":
            base = self._defend_mobility_penalty
        else:
            base = 1.0
        # Apply fatigue penalty
        if self.fatigue is not None:
            base *= self.fatigue.movement_modifier
        # Apply crew efficiency for vehicles
        if self.crew is not None:
            base *= self.crew.vehicle_efficiency
        return base

    def get_accuracy_modifier(self) -> float:
        """Get accuracy modifier based on movement mode.

        Returns:
            Accuracy multiplier (1.0 = normal, >1.0 = bonus)

        """
        base = 1.0
        if self._movement_mode == "defend":
            base = 1.0 + self._defend_accuracy_bonus
        elif self._movement_mode == "fast_move":
            base = 0.85
        elif self._movement_mode == "sneak":
            base = 0.95
        # Apply fatigue penalty
        if self.fatigue is not None:
            base *= self.fatigue.accuracy_modifier
        # Apply veterancy bonus
        if self.veterancy is not None:
            base *= self.veterancy.accuracy_bonus
        # Apply crew efficiency for vehicles
        if self.crew is not None:
            base *= self.crew.vehicle_efficiency
        return base

    def get_detection_modifier(self) -> float:
        """Get detection chance modifier based on movement mode.

        Returns:
            Detection multiplier (>1.0 = easier to detect, <1.0 = harder to detect)

        """
        if self._movement_mode == "fast_move":
            base = 1.5  # Much easier to detect when sprinting
        elif self._movement_mode == "sneak":
            base = 0.5  # Harder to detect when sneaking
        elif self._movement_mode == "defend":
            base = 0.8  # Slightly harder (stationary)
        else:
            base = 1.0
        # Veterans are harder to spot (better fieldcraft)
        if self.veterancy is not None and self.veterancy.rank.value >= 3:  # VETERAN+
            base *= 0.9
        return base

    # ------------------------------------------------------------------
    # Garrison status
    # ------------------------------------------------------------------

    def update_garrison_status(self, game_map: GameMap) -> None:
        """Update building garrison status based on current tile terrain.

        When a unit moves onto a BUILDING_ENTERABLE tile, it is considered
        garrisoned inside the building. When it moves off, the garrison
        status is cleared.
        """
        from pycc2.domain.value_objects.terrain_type import TerrainType

        tc = self.position.tile_coord
        if 0 <= tc.x < game_map.width and 0 <= tc.y < game_map.height:
            terrain = game_map.get_terrain(tc)
            if terrain == TerrainType.BUILDING_ENTERABLE:
                self.current_building_pos = (tc.x, tc.y)
            else:
                self.current_building_pos = None
        else:
            self.current_building_pos = None

    # ------------------------------------------------------------------
    # Movement execution
    # ------------------------------------------------------------------

    def move_to_tile(self, tile: TileCoord) -> None:
        """Move the unit immediately to the specified tile coordinate."""
        self.position.move_to_tile(tile)

    def set_move_target(self, tile: TileCoord) -> None:
        """Set movement target (unit will move toward it each tick)."""
        from pycc2.domain.entities.unit import UnitState

        self.move_target = tile
        if self.state_machine.current != UnitState.MOVING:
            try:
                self.state_machine.try_transition(UnitState.MOVING)
            except (ValueError, RuntimeError) as e:
                logging.warning("Unit state transition to MOVING failed: %s", e)

    def update_movement(self, dt: float = 1.0) -> bool:
        """Move unit toward target. Call once per game tick.

        Returns True if unit reached target, False if still moving.
        """
        from pycc2.domain.entities.unit import UnitState

        if self.move_target is None:
            return True  # Not moving

        if not self.is_alive:
            self.move_target = None
            return True

        # R6: Out of fuel vehicles cannot move
        if self.is_out_of_fuel:
            self.move_target = None
            try:
                self.state_machine.try_transition(UnitState.IDLE)
            except (ValueError, RuntimeError) as e:
                logging.warning("Unit state transition to IDLE failed: %s", e)
            return True

        # Get current and target positions
        current = self.position.tile_coord
        target = self.move_target

        # Check if already at target
        if current.x == target.x and current.y == target.y:
            self.move_target = None
            try:
                self.state_machine.try_transition(UnitState.IDLE)
            except (ValueError, RuntimeError) as e:
                logging.warning("Unit state transition to IDLE failed: %s", e)
            return True  # Arrived!

        # Calculate direction
        dx = target.x - current.x
        dy = target.y - current.y
        dist = (dx * dx + dy * dy) ** 0.5

        # Move based on speed (tiles per tick)
        # Speed affected by: base speed, fatigue, morale, unit type
        base_speed = getattr(self, "movement_speed", 3.0)

        # Apply modifiers
        speed_modifier = 1.0

        # Apply movement mode speed multiplier (Fast Move, Sneak, Defend)
        if hasattr(self, "get_speed_multiplier"):
            speed_modifier *= self.get_speed_multiplier()

        # Fatigue reduces speed (if fatigue system exists)
        if hasattr(self, "fatigue"):
            fatigue_val = getattr(self.fatigue, "current", 0) if self.fatigue else 0
            # Fatigue 0-100: at 100, speed reduced by 50%
            speed_modifier *= 1.0 - (fatigue_val / 200)

        # Low morale slightly reduces speed
        if hasattr(self, "morale"):
            morale_val = getattr(self.morale, "current", 75) if self.morale else 75
            # Morale < 30: panic, slower movement
            if morale_val < 30:
                speed_modifier *= 0.6
            elif morale_val < 50:
                speed_modifier *= 0.8

        # Vehicles move faster than infantry on roads, slower in rough terrain
        # (terrain modifier would be applied here if we had terrain data)

        # Final speed calculation
        speed = base_speed * speed_modifier * dt * 0.15  # Scaled for smooth visual movement

        if dist <= speed:
            # Close enough: snap to target
            # R6: Consume fuel for vehicle movement
            if self.fuel >= 0:
                self.fuel = max(0.0, self.fuel - self.fuel_per_tile)
            self.move_to_tile(target)
            self.move_target = None
            # Check for queued commands before transitioning to IDLE
            next_cmd = self.get_next_queued_command()
            if next_cmd is not None:
                self._execute_queued_command(next_cmd)
            else:
                try:
                    self.state_machine.try_transition(UnitState.IDLE)
                except (ValueError, RuntimeError) as e:
                    logging.warning("Unit state transition to IDLE (after move) failed: %s", e)
            return True
        else:
            # Move toward target
            # R6: Consume fuel for vehicle movement (partial tile)
            if self.fuel >= 0:
                self.fuel = max(0.0, self.fuel - self.fuel_per_tile * speed / max(dist, 1.0))
            move_x = int(dx / dist * speed)
            move_y = int(dy / dist * speed)
            new_tile = type(target)(x=current.x + move_x, y=current.y + move_y)
            self.move_to_tile(new_tile)
            return False  # Still moving
