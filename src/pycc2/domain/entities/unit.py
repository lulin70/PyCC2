"""
Unit Entity - Core Game Unit
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

from pycc2.domain.components.fatigue_component import FatigueComponent
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.veterancy_component import VeterancyComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.squad import Squad
    from pycc2.domain.state_machine import StateMachine
    from pycc2.domain.systems.combat_mechanics_enhanced import (
        CombatState,
        ConcealmentProfile,
        SuppressionEffect,
        SuppressionState,
    )
    from pycc2.domain.systems.vehicle_crew_system import VehicleCrew


class Faction(Enum):
    ALLIES = auto()
    AMERICAN = auto()
    BRITISH = auto()
    POLISH = auto()
    AXIS = auto()
    GERMAN = auto()


class UnitType(Enum):
    INFANTRY_SQUAD = auto()
    MACHINE_GUN_SQUAD = auto()
    AT_GUN_TEAM = auto()
    COMMANDER = auto()
    MORTAR_TEAM = auto()
    TANK = auto()
    SNIPER_TEAM = auto()
    MEDIC_TEAM = auto()


class UnitState(Enum):
    IDLE = auto()
    MOVING = auto()
    ATTACKING = auto()
    RELOADING = auto()
    SURRENDERED = auto()
    DEAD = auto()


@dataclass(slots=True)
class Unit:
    id: str
    name: str
    faction: Faction
    unit_type: UnitType
    health: HealthComponent
    morale: MoraleComponent
    weapon: WeaponComponent
    position: PositionComponent
    vision: VisionComponent
    squad_id: str | None = None
    fatigue: FatigueComponent | None = None
    veterancy: VeterancyComponent | None = None
    crew: VehicleCrew | None = None  # Only for vehicle units
    squad_ref: Squad | None = None  # Direct reference replaces squad_id
    state_machine: StateMachine = field(init=False)
    armor_front: float = 1.0
    armor_side: float = 0.65
    armor_rear: float = 0.40
    armor_top: float = 0.50
    combat_state: CombatState | None = None
    move_target: "TileCoord | None" = field(default=None, init=False)  # Movement destination
    facing: float = 0.0  # Facing direction in degrees (0=East, 90=South, 180=West, 270=North)
    current_building_pos: tuple[int, int] | None = None  # None = not in building; set when on BUILDING_ENTERABLE tile
    building_floor: int = 0  # 0=ground, 1=2nd floor, 2=3rd floor, etc.

    # R6: Vehicle fuel tracking
    fuel: float = -1.0  # -1 = not a vehicle (infantry); vehicles start with max_fuel
    max_fuel: float = 100.0
    fuel_per_tile: float = 1.0  # Fuel consumed per tile moved
    
    # Movement mode system (for Fast Move, Sneak, Defend commands)
    _movement_mode: str = field(init=False, default="normal")  # normal, fast_move, sneak, defend
    _movement_mode_ticks_remaining: int = field(init=False, default=0)  # Duration in ticks
    _sneak_speed_multiplier: float = 0.6
    _fast_speed_multiplier: float = 1.5
    _defend_accuracy_bonus: float = 0.25  # +25% accuracy when defending
    _defend_mobility_penalty: float = 0.5   # 50% slower when defending

    # Command queue (Shift+right-click queued commands)
    _command_queue: list[dict] = field(default_factory=list)

    # Popup tracking (used by game_loop._process_combat_popups)
    _prev_morale_state: object = field(init=False, default=None)
    _kia_popup_shown: bool = field(init=False, default=False)

    # P1-7 Fix: Smoke grenade capability
    has_smoke_grenades: bool = False  # Set True for units with smoke capability
    smoke_grenade_count: int = 0     # Remaining smoke grenades (0=unlimited in CC2)
    _ammo_popup_shown: bool = field(init=False, default=False)

    # STEP A-2: Damage visualization system (CC2-style vehicle/infantry damage states)
    _damage_state: str = field(init=False, default="undamaged")  # undamaged/light/moderate/heavy/destroyed
    _smoke_particles: list = field(init=False, default_factory=list)  # Smoke effect positions
    _fire_particles: list = field(init=False, default_factory=list)   # Fire effect positions
    _damage_vfx_timer: int = field(init=False, default=0)            # Animation timer
    
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
        if not hasattr(self, 'weapon') or self.weapon is None:
            return False
        # Most infantry and support units have smoke capability
        return self.unit_type in (
            UnitType.INFANTRY_SQUAD,
            UnitType.MACHINE_GUN_SQUAD,
            UnitType.COMMANDER,
            UnitType.SNIPER_TEAM,
        )
    
    @property
    def can_sneak(self) -> bool:
        """Check if unit can use sneak mode."""
        # Infantry and recon units can sneak
        return self.unit_type in (
            UnitType.INFANTRY_SQUAD,
            UnitType.SNIPER_TEAM,
            UnitType.COMMANDER,
            UnitType.MEDIC_TEAM,
        )
    
    @property
    def can_hide(self) -> bool:
        """Check if unit can hide (take cover)."""
        # All infantry-sized units can hide
        return not getattr(self, 'is_vehicle', False)
    
    def set_movement_mode(self, mode: str, duration_ticks: int = -1) -> None:
        """
        Set movement mode for the unit.
        
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
            logger.info(
                f"[COMMAND] {self.name or self.id} mode change: {old_mode} -> {mode}"
            )
    
    def get_speed_multiplier(self) -> float:
        """
        Get current speed multiplier based on movement mode.

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
        """
        Get accuracy modifier based on movement mode.

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
        """
        Get detection chance modifier based on movement mode.

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
    
    def update_movement_mode(self) -> None:
        """Update movement mode timer (call once per tick)."""
        if self._movement_mode_ticks_remaining > 0:
            self._movement_mode_ticks_remaining -= 1
            if self._movement_mode_ticks_remaining == 0:
                # Reset to normal when duration expires
                self._movement_mode = "normal"

    def queue_command(self, command_type: str, target_x: float = 0, target_y: float = 0, **kwargs) -> None:
        """Add a command to the execution queue (Shift+right-click)."""
        self._command_queue.append({
            'type': command_type,
            'target_x': target_x,
            'target_y': target_y,
            **kwargs
        })

    def get_next_queued_command(self) -> dict | None:
        """Get and remove the next command from the queue."""
        if self._command_queue:
            return self._command_queue.pop(0)
        return None

    @property
    def has_queued_commands(self) -> bool:
        return len(self._command_queue) > 0

    def clear_command_queue(self) -> None:
        self._command_queue.clear()

    def _execute_queued_command(self, cmd: dict) -> None:
        """Execute the next queued command after current one completes."""
        cmd_type = cmd.get('type', 'move')
        if cmd_type == 'move':
            tx = cmd.get('target_x', 0)
            ty = cmd.get('target_y', 0)
            from pycc2.domain.value_objects.tile_coord import TileCoord
            self.set_move_target(TileCoord(int(tx), int(ty)))
        elif cmd_type == 'attack':
            try:
                self.state_machine.transition(UnitState.ATTACKING)
            except Exception as e:
                logging.warning(f"Unit state transition to ATTACKING failed: {e}")

    def __post_init__(self) -> None:
        from pycc2.domain.state_machine import StateMachine

        self.state_machine = StateMachine(
            initial=UnitState.IDLE,
            transitions={
                UnitState.IDLE: {UnitState.MOVING, UnitState.ATTACKING, UnitState.DEAD, UnitState.SURRENDERED},
                UnitState.MOVING: {UnitState.IDLE, UnitState.ATTACKING, UnitState.DEAD, UnitState.SURRENDERED},
                UnitState.ATTACKING: {
                    UnitState.IDLE,
                    UnitState.MOVING,
                    UnitState.RELOADING,
                    UnitState.DEAD,
                    UnitState.SURRENDERED,
                },
                UnitState.RELOADING: {UnitState.IDLE, UnitState.ATTACKING, UnitState.DEAD, UnitState.SURRENDERED},
                UnitState.SURRENDERED: set(),
                UnitState.DEAD: set(),
            },
        )
        if self.combat_state is None:
            from pycc2.domain.systems.combat_mechanics_enhanced import CombatState
            self.combat_state = CombatState()

        # Auto-create component instances
        if self.fatigue is None:
            self.fatigue = FatigueComponent()
        if self.veterancy is None:
            self.veterancy = VeterancyComponent()
        # Crew only for vehicles
        if self.crew is None and self.unit_type == UnitType.TANK:
            from pycc2.domain.systems.vehicle_crew_system import VehicleCrew
            self.crew = VehicleCrew(self.id)
        # R6: Initialize fuel for vehicle units
        if self.fuel < 0 and self.unit_type == UnitType.TANK:
            self.fuel = self.max_fuel

        # P1-7 Fix: Initialize smoke grenade capability based on unit type
        self.has_smoke_grenades = self.unit_type in (
            UnitType.INFANTRY_SQUAD,
            UnitType.MACHINE_GUN_SQUAD,
            UnitType.COMMANDER,
            UnitType.SNIPER_TEAM,
        )
        # CC2: Most units have unlimited smoke (0 = infinite)
        self.smoke_grenade_count = 0 if self.has_smoke_grenades else -1

    @property
    def squad_size(self) -> int:
        """Get squad size from linked squad."""
        if self.squad_ref is not None:
            return self.squad_ref.size
        return 1

    @property
    def squad_casualties(self) -> int:
        """Get squad casualties from linked squad."""
        if self.squad_ref is not None:
            return self.squad_ref.dead_count
        return 0

    @property
    def squad_status_string(self) -> str:
        """Get squad status string for UI."""
        if self.squad_ref is not None:
            return self.squad_ref.get_status_string()
        return ""

    @property
    def is_alive(self) -> bool:
        return self.health.is_alive

    @property
    def is_out_of_fuel(self) -> bool:
        """R6: Check if vehicle is out of fuel (immobilized)."""
        if self.fuel < 0:
            return False  # Not a vehicle
        return self.fuel <= 0

    @property
    def damage_state(self) -> str:
        """STEP A-2: Calculate damage state based on HP percentage.

        Returns one of: undamaged / light / moderate / heavy / destroyed
        Used for visual feedback (smoke, fire, appearance changes).
        """
        if not hasattr(self, 'health') or self.health is None:
            return "undamaged"

        hp_ratio = self.health.hp / self.health.max_hp if self.health.max_hp > 0 else 1.0

        if hp_ratio <= 0:
            return "destroyed"
        elif hp_ratio <= 0.25:
            return "heavy"      # 🔥 Heavy damage: fire + thick smoke
        elif hp_ratio <= 0.50:
            return "moderate"   # 💨 Moderate: smoke + visible damage
        elif hp_ratio <= 0.75:
            return "light"      # ☁️ Light: light smoke wisps
        else:
            return "undamaged"

    @property
    def is_damaged(self) -> bool:
        """Check if unit has any damage (for quick filtering)."""
        return self.damage_state != "undamaged"

    @property
    def damage_level_numeric(self) -> int:
        """Numeric damage level (0-4) for rendering intensity."""
        states = {"undamaged": 0, "light": 1, "moderate": 2, "heavy": 3, "destroyed": 4}
        return states.get(self.damage_state, 0)

    def update_damage_vfx(self) -> None:
        """STEP A-2: Update visual effect particles based on current damage state.

        Called each tick to animate smoke/fire particles.
        Generates particle positions for renderer to display.
        """
        self._damage_vfx_timer += 1

        state = self.damage_state

        # Clear old particles periodically
        if self._damage_vfx_timer % 30 == 0:
            self._smoke_particles.clear()
            self._fire_particles.clear()

        # Generate new particles based on damage state
        import random as _rng
        rng = _rng.Random(self.id + self._damage_vfx_timer)

        if state in ("light", "moderate", "heavy", "destroyed"):
            # Smoke particles (more for heavier damage)
            num_smoke = {"light": 2, "moderate": 4, "heavy": 6, "destroyed": 8}.get(state, 0)
            for _ in range(num_smoke):
                offset_x = rng.randint(-8, 8)
                offset_y = rng.randint(-10, -2)  # Smoke rises upward
                alpha = rng.randint(80, 180)       # Semi-transparent
                size = rng.randint(2, 5)
                self._smoke_particles.append({
                    'x': offset_x, 'y': offset_y,
                    'alpha': alpha, 'size': size,
                    'life': rng.randint(15, 30),  # Ticks until fade
                })

        if state in ("heavy", "destroyed"):
            # Fire particles (only for heavy damage or destroyed)
            num_fire = 4 if state == "heavy" else 6
            for _ in range(num_fire):
                offset_x = rng.randint(-6, 6)
                offset_y = rng.randint(-4, 4)
                color_var = rng.choice([
                    (220, 120, 20),   # Orange
                    (240, 200, 50),   # Yellow
                    (180, 50, 10),    # Red-orange
                ])
                size = rng.randint(2, 4)
                self._fire_particles.append({
                    'x': offset_x, 'y': offset_y,
                    'color': color_var, 'size': size,
                    'life': rng.randint(8, 20),
                })

    @property
    def can_act(self) -> bool:
        return (
            self.is_alive
            and self.state_machine.current != UnitState.DEAD
            and self.state_machine.current != UnitState.RELOADING
            and self.state_machine.current != UnitState.SURRENDERED
        )

    @property
    def combat_effective(self) -> bool:
        return self.is_alive and self.morale.is_combat_effective

    @property
    def is_pinned(self) -> bool:
        return self.combat_state.is_pinned if self.combat_state is not None else False

    @property
    def is_broken(self) -> bool:
        """Check if unit is in broken state (morale < 20)."""
        if hasattr(self, 'morale') and self.morale is not None:
            return self.morale.value < 20
        return False

    @property
    def morale_state(self):
        """Get current morale state from MoraleSystem."""
        from pycc2.domain.systems.morale_system import MoraleSystem
        if hasattr(self, 'morale') and self.morale is not None:
            return MoraleSystem.get_state(self.morale.value)
        from pycc2.domain.systems.morale_system import MoraleState
        return MoraleState.RALLYED

    def can_move(self) -> bool:
        """Check if unit can move based on morale and suppression."""
        from pycc2.domain.systems.morale_system import MoraleSystem
        
        # Check alive status first
        if not self.is_alive:
            return False
        
        # Check combat state machine
        if self.state_machine.current in (UnitState.DEAD, UnitState.SURRENDERED):
            return False
        
        # Use MoraleSystem for detailed check
        if hasattr(self, 'morale') and self.morale is not None:
            return MoraleSystem.can_move(self)
        
        return True

    def can_accept_orders(self) -> bool:
        """Check if unit will accept orders."""
        from pycc2.domain.systems.morale_system import MoraleSystem
        if hasattr(self, 'morale') and self.morale is not None:
            return MoraleSystem.can_accept_orders(self)
        return True

    @property
    def suppression_level(self) -> SuppressionEffect:
        if self.combat_state is not None:
            return self.combat_state.suppression.get_current_effect()
        from pycc2.domain.systems.combat_mechanics_enhanced import SuppressionEffect
        return SuppressionEffect.NONE

    @property
    def concealment_level(self) -> float:
        if self.combat_state is not None:
            return self.combat_state.concealment.calculate_total_concealment()
        return 0.0

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

    def move_to_tile(self, tile: TileCoord) -> None:
        self.position.move_to_tile(tile)

    def set_move_target(self, tile: "TileCoord") -> None:
        """Set movement target (unit will move toward it each tick)."""
        from pycc2.domain.value_objects.tile_coord import TileCoord
        self.move_target = tile
        if self.state_machine.current != UnitState.MOVING:
            try:
                self.state_machine.transition(UnitState.MOVING)
            except Exception as e:
                logging.warning(f"Unit state transition to MOVING failed: {e}")

    def update_movement(self, dt: float = 1.0) -> bool:
        """
        Move unit toward target. Call once per game tick.
        Returns True if unit reached target, False if still moving.
        """
        if self.move_target is None:
            return True  # Not moving

        if not self.is_alive:
            self.move_target = None
            return True

        # R6: Out of fuel vehicles cannot move
        if self.is_out_of_fuel:
            self.move_target = None
            try:
                self.state_machine.transition(UnitState.IDLE)
            except Exception as e:
                logger.debug("State transition to IDLE failed: %s", e)
            return True

        # Get current and target positions
        current = self.position.tile_coord
        target = self.move_target

        # Check if already at target
        if current.x == target.x and current.y == target.y:
            self.move_target = None
            try:
                self.state_machine.transition(UnitState.IDLE)
            except Exception as e:
                logging.warning(f"Unit state transition to IDLE failed: {e}")
            return True  # Arrived!

        # Calculate direction
        dx = target.x - current.x
        dy = target.y - current.y
        dist = (dx*dx + dy*dy) ** 0.5

        # Move based on speed (tiles per tick)
        # Speed affected by: base speed, fatigue, morale, unit type
        base_speed = getattr(self, 'movement_speed', 3.0)

        # Apply modifiers
        speed_modifier = 1.0
        
        # Apply movement mode speed multiplier (Fast Move, Sneak, Defend)
        if hasattr(self, 'get_speed_multiplier'):
            speed_modifier *= self.get_speed_multiplier()
        
        # Fatigue reduces speed (if fatigue system exists)
        if hasattr(self, 'fatigue'):
            fatigue_val = getattr(self.fatigue, 'current', 0) if self.fatigue else 0
            # Fatigue 0-100: at 100, speed reduced by 50%
            speed_modifier *= (1.0 - (fatigue_val / 200))

        # Low morale slightly reduces speed
        if hasattr(self, 'morale'):
            morale_val = getattr(self.morale, 'current', 75) if self.morale else 75
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
                    self.state_machine.transition(UnitState.IDLE)
                except Exception as e:
                    logging.warning(f"Unit state transition to IDLE (after move) failed: {e}")
            return True
        else:
            # Move toward target
            # R6: Consume fuel for vehicle movement (partial tile)
            if self.fuel >= 0:
                self.fuel = max(0.0, self.fuel - self.fuel_per_tile * speed / max(dist, 1.0))
            move_x = int(dx / dist * speed)
            move_y = int(dy / dist * speed)
            new_tile = type(target)(
                x=current.x + move_x,
                y=current.y + move_y
            )
            self.move_to_tile(new_tile)
            return False  # Still moving

    def take_damage(self, amount: int) -> int:
        actual = self.health.take_damage(amount)
        if not self.is_alive:
            self.die()
        return actual

    def die(self) -> None:
        self.state_machine.force_transition(UnitState.DEAD)


@dataclass(slots=True)
class UnitTemplate:
    unit_type: UnitType
    display_name: str
    max_hp: int
    base_morale: int
    primary_weapon_id: str
    max_ammo: int
    weapon_damage_range: tuple[float, float]
    vision_range: int
    movement_speed: float
    size_radius: int
    is_vehicle: bool = False
    can_heal: bool = False
    heal_per_tick: float = 0.0
    heal_range: int = 0
    stealth_bonus: float = 0.0


UNIT_TEMPLATES: dict[UnitType, UnitTemplate] = {
    UnitType.INFANTRY_SQUAD: UnitTemplate(
        unit_type=UnitType.INFANTRY_SQUAD,
        display_name="Rifle Squad",
        max_hp=100,
        base_morale=85,
        primary_weapon_id="rifle",
        max_ammo=10,
        weapon_damage_range=(8, 18),
        vision_range=5,
        movement_speed=3.0,
        size_radius=4,
    ),
    UnitType.MACHINE_GUN_SQUAD: UnitTemplate(
        unit_type=UnitType.MACHINE_GUN_SQUAD,
        display_name="MG Team",
        max_hp=80,
        base_morale=75,
        primary_weapon_id="mg42",
        max_ammo=50,
        weapon_damage_range=(12, 25),
        vision_range=6,
        movement_speed=2.0,
        size_radius=5,
    ),
    UnitType.COMMANDER: UnitTemplate(
        unit_type=UnitType.COMMANDER,
        display_name="Commander",
        max_hp=100,
        base_morale=95,
        primary_weapon_id="pistol",
        max_ammo=14,
        weapon_damage_range=(6, 12),
        vision_range=7,
        movement_speed=3.0,
        size_radius=4,
    ),
    UnitType.AT_GUN_TEAM: UnitTemplate(
        unit_type=UnitType.AT_GUN_TEAM,
        display_name="AT Gun Team",
        max_hp=60,
        base_morale=70,
        primary_weapon_id="at_gun",
        max_ammo=8,
        weapon_damage_range=(30, 60),
        vision_range=6,
        movement_speed=1.0,
        size_radius=5,
    ),
    UnitType.MORTAR_TEAM: UnitTemplate(
        unit_type=UnitType.MORTAR_TEAM,
        display_name="Mortar Team",
        max_hp=50,
        base_morale=65,
        primary_weapon_id="mortar",
        max_ammo=6,
        weapon_damage_range=(20, 45),
        vision_range=5,
        movement_speed=1.5,
        size_radius=4,
    ),
    UnitType.TANK: UnitTemplate(
        unit_type=UnitType.TANK,
        display_name="Medium Tank",
        max_hp=200,
        base_morale=90,
        primary_weapon_id="tank_cannon",
        max_ammo=30,
        weapon_damage_range=(35, 70),
        vision_range=7,
        movement_speed=2.5,
        size_radius=8,
        is_vehicle=True,
    ),
    UnitType.SNIPER_TEAM: UnitTemplate(
        unit_type=UnitType.SNIPER_TEAM,
        display_name="Sniper Team",
        max_hp=60,
        base_morale=80,
        primary_weapon_id="sniper_rifle",
        max_ammo=15,
        weapon_damage_range=(25, 50),
        vision_range=10,
        movement_speed=2.5,
        size_radius=3,
        stealth_bonus=0.40,
    ),
    UnitType.MEDIC_TEAM: UnitTemplate(
        unit_type=UnitType.MEDIC_TEAM,
        display_name="Medic Team",
        max_hp=70,
        base_morale=88,
        primary_weapon_id="pistol",
        max_ammo=12,
        weapon_damage_range=(4, 8),
        vision_range=5,
        movement_speed=3.0,
        size_radius=4,
        can_heal=True,
        heal_per_tick=0.5,
        heal_range=3,
    ),
}

UNIT_ARMOR_PROFILES: dict[str, dict[str, float]] = {
    "TANK": {"front": 1.0, "side": 0.65, "rear": 0.40, "top": 0.50},
    "INFANTRY_SQUAD": {"front": 0.15, "side": 0.10, "rear": 0.10, "top": 0.10},
    "MACHINE_GUN_SQUAD": {"front": 0.12, "side": 0.08, "rear": 0.08, "top": 0.08},
    "SNIPER_TEAM": {"front": 0.05, "side": 0.03, "rear": 0.03, "top": 0.03},
    "MORTAR_TEAM": {"front": 0.10, "side": 0.07, "rear": 0.07, "top": 0.07},
    "COMMANDER": {"front": 0.10, "side": 0.07, "rear": 0.07, "top": 0.07},
    "MEDIC_TEAM": {"front": 0.08, "side": 0.05, "rear": 0.05, "top": 0.05},
    "AT_GUN_TEAM": {"front": 0.20, "side": 0.15, "rear": 0.12, "top": 0.12},
}
