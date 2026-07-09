"""Unit Entity - Core Game Unit.

Facade composing SRP-split behavior mixins (D12 Phase 4 P0-2 God Class split,
2026-07-04). The original 937L / 54-method monolith was split into this
facade plus 5 function-specific mixins:

  - ``unit_movement_mixin.UnitMovementMixin`` (16 methods)
      Movement-mode properties (movement_mode, is_fast_moving, is_sneaking,
      is_defending, can_use_smoke, can_sneak, can_hide), mode mutation
      (set_movement_mode, update_movement_mode), mode-derived modifiers
      (get_speed_multiplier, get_accuracy_modifier, get_detection_modifier),
      garrison status (update_garrison_status), and movement execution
      (move_to_tile, set_move_target, update_movement).
  - ``unit_combat_mixin.UnitCombatMixin`` (5 methods)
      Combat-action eligibility (can_act, combat_effective, is_pinned) and
      suppression/concealment queries (suppression_level, concealment_level).
  - ``unit_morale_mixin.UnitMoraleMixin`` (4 methods)
      Morale-derived state (is_broken, morale_state) and order-acceptance
      gating (can_move, can_accept_orders) via MoraleSystem.
  - ``unit_damage_vfx_mixin.UnitDamageVfxMixin`` (4 methods)
      Damage-state classification (damage_state, is_damaged,
      damage_level_numeric) and per-tick VFX particle generation
      (update_damage_vfx).
  - ``unit_command_queue_mixin.UnitCommandQueueMixin`` (5 methods)
      Shift+right-click queued-command manipulation (queue_command,
      get_next_queued_command, has_queued_commands, clear_command_queue,
      _execute_queued_command).

The facade ``Unit`` inherits all of the above (mixin-first order in MRO) and
keeps the dataclass fields, ``__post_init__``, legacy component aliases,
squad-reference properties, life-state queries, and core life-cycle
(take_damage / die). Public API is 100% backward-compatible.
"""

from __future__ import annotations

import logging
from collections import deque
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
from pycc2.domain.entities.unit_combat_mixin import UnitCombatMixin
from pycc2.domain.entities.unit_command_queue_mixin import UnitCommandQueueMixin
from pycc2.domain.entities.unit_damage_vfx_mixin import UnitDamageVfxMixin
from pycc2.domain.entities.unit_morale_mixin import UnitMoraleMixin
from pycc2.domain.entities.unit_movement_mixin import UnitMovementMixin
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.squad import Squad
    from pycc2.domain.state_machine import StateMachine
    from pycc2.domain.systems.combat_mechanics_enhanced import (
        CombatState,
    )
    from pycc2.domain.systems.vehicle_crew_system import VehicleCrew


class Faction(Enum):
    """Playable factions grouped by alliance (Allies vs Axis)."""

    ALLIES = auto()
    AMERICAN = auto()
    BRITISH = auto()
    POLISH = auto()
    AXIS = auto()
    GERMAN = auto()


class UnitType(Enum):
    """Classification of unit roles such as infantry, armor, and support teams."""

    INFANTRY_SQUAD = auto()
    MACHINE_GUN_SQUAD = auto()
    AT_GUN_TEAM = auto()
    COMMANDER = auto()
    MORTAR_TEAM = auto()
    TANK = auto()
    SNIPER_TEAM = auto()
    MEDIC_TEAM = auto()


class UnitState(Enum):
    """Operational state of a unit in the state machine."""

    IDLE = auto()
    MOVING = auto()
    ATTACKING = auto()
    RELOADING = auto()
    SURRENDERED = auto()
    DEAD = auto()


@dataclass(slots=True)
class Unit(
    UnitMovementMixin,
    UnitCombatMixin,
    UnitMoraleMixin,
    UnitDamageVfxMixin,
    UnitCommandQueueMixin,
):
    """Core combat unit aggregating health, morale, weapon, and position components.

    Composes 5 SRP-split mixins (movement/combat/morale/damage-vfx/command-queue)
    split out during Phase 4 P0-2 (2026-07-04). Each mixin holds the methods
    for its functional group; the facade provides dataclass fields,
    ``__post_init__``, legacy component aliases, squad-reference properties,
    life-state queries, and core life-cycle (take_damage / die). Public API
    100% backward-compatible.
    """

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
    is_squad_leader: bool = False  # Marks squad leader for degradation/NCO rally (used by squad_degradation.py, tick_scheduler.py)
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
    move_target: TileCoord | None = field(default=None, init=False)  # Movement destination
    facing: float = 0.0  # Facing direction in degrees (0=East, 90=South, 180=West, 270=North)
    current_building_pos: tuple[int, int] | None = (
        None  # None = not in building; set when on BUILDING_ENTERABLE tile
    )
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
    _defend_mobility_penalty: float = 0.5  # 50% slower when defending

    # Command queue (Shift+right-click queued commands)
    _command_queue: deque[dict] = field(default_factory=deque)

    # Popup tracking (used by game_loop._process_combat_popups)
    _prev_morale_state: object = field(init=False, default=None)
    _kia_popup_shown: bool = field(init=False, default=False)

    # P1-7 Fix: Smoke grenade capability
    has_smoke_grenades: bool = False  # Set True for units with smoke capability
    smoke_grenade_count: int = 0  # Remaining smoke grenades (0=unlimited in CC2)
    _grenade_count: int = 0  # Internal grenade counter for legacy melee/grenade AI
    _ammo_popup_shown: bool = field(init=False, default=False)

    # Action flags used by casualty system
    _can_move: bool = True
    _can_attack: bool = True
    move_speed: float = 1.0  # Base movement speed multiplier

    # STEP A-2: Damage visualization system (CC2-style vehicle/infantry damage states)
    _damage_state: str = field(
        init=False, default="undamaged"
    )  # undamaged/light/moderate/heavy/destroyed
    _smoke_particles: list = field(init=False, default_factory=list)  # Smoke effect positions
    _fire_particles: list = field(init=False, default_factory=list)  # Fire effect positions
    _damage_vfx_timer: int = field(init=False, default=0)  # Animation timer
    # TD-065: Vehicle component damage states (tracks/turret/engine → intact/damaged/destroyed).
    # Empty dict for infantry; populated by UnitDamageVfxMixin.update_vehicle_damage_components.
    _damage_components: dict = field(init=False, default_factory=dict)

    @property
    def unit_id(self) -> str:
        """Alias for id used by several subsystems."""
        return self.id

    @property
    def position_component(self) -> PositionComponent:
        """Legacy alias for position."""
        return self.position

    @property
    def weapon_component(self) -> WeaponComponent:
        """Legacy alias for weapon."""
        return self.weapon

    @property
    def health_component(self) -> HealthComponent:
        """Legacy alias for health."""
        return self.health

    @property
    def morale_component(self) -> MoraleComponent:
        """Legacy alias for morale."""
        return self.morale

    @property
    def vision_component(self) -> VisionComponent:
        """Legacy alias for vision."""
        return self.vision

    @property
    def fatigue_component(self) -> FatigueComponent | None:
        """Legacy alias for fatigue."""
        return self.fatigue

    @property
    def veterancy_component(self) -> VeterancyComponent | None:
        """Legacy alias for veterancy."""
        return self.veterancy

    @property
    def vision_range(self) -> int:
        """Convenience alias for vision range in tiles."""
        return self.vision.range_tiles

    @property
    def ammo(self) -> int:
        """Convenience alias for remaining primary weapon ammo."""
        return self.weapon.ammo_remaining

    @property
    def display_name(self) -> str:
        """Human-readable name for UI and logs."""
        return self.name or self.id

    def __post_init__(self) -> None:
        from pycc2.domain.state_machine import StateMachine

        self.state_machine = StateMachine(
            initial=UnitState.IDLE,
            transitions={
                UnitState.IDLE: {
                    UnitState.MOVING,
                    UnitState.ATTACKING,
                    UnitState.DEAD,
                    UnitState.SURRENDERED,
                },
                UnitState.MOVING: {
                    UnitState.IDLE,
                    UnitState.ATTACKING,
                    UnitState.DEAD,
                    UnitState.SURRENDERED,
                },
                UnitState.ATTACKING: {
                    UnitState.IDLE,
                    UnitState.MOVING,
                    UnitState.RELOADING,
                    UnitState.DEAD,
                    UnitState.SURRENDERED,
                },
                UnitState.RELOADING: {
                    UnitState.IDLE,
                    UnitState.ATTACKING,
                    UnitState.DEAD,
                    UnitState.SURRENDERED,
                },
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
    def squad(self) -> Squad | None:
        """Legacy alias for squad_ref."""
        return self.squad_ref

    @property
    def is_alive(self) -> bool:
        """Return True if the unit still has health remaining."""
        return self.health.is_alive

    @property
    def is_out_of_fuel(self) -> bool:
        """R6: Check if vehicle is out of fuel (immobilized)."""
        if self.fuel < 0:
            return False  # Not a vehicle
        return self.fuel <= 0

    def take_damage(self, amount: int) -> int:
        """Apply damage to the unit and return the actual amount dealt."""
        actual = self.health.take_damage(amount)
        if not self.is_alive:
            self.die()
        return actual

    def die(self) -> None:
        """Force the unit into the DEAD state."""
        self.state_machine.force_transition(UnitState.DEAD)


@dataclass(slots=True)
class UnitTemplate:
    """Static factory parameters used to instantiate a unit of a given type."""

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
