"""
Unit Entity - Core Game Unit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.state_machine import StateMachine
    from pycc2.domain.systems.combat_mechanics_enhanced import (
        CombatState,
        ConcealmentProfile,
        SuppressionEffect,
        SuppressionState,
    )


class Faction(Enum):
    ALLIES = auto()
    POLISH = auto()
    AXIS = auto()


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
    state_machine: StateMachine = field(init=False)
    armor_front: float = 1.0
    armor_side: float = 0.65
    armor_rear: float = 0.40
    armor_top: float = 0.50
    combat_state: CombatState | None = None

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

    @property
    def is_alive(self) -> bool:
        return self.health.is_alive

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

    def move_to_tile(self, tile: TileCoord) -> None:
        self.position.move_to_tile(tile)

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
