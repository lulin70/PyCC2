"""Tests for CC2 fire discipline modes (P1-7)."""

from __future__ import annotations

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.combat_director import CombatDirector


class _FixedRng:
    def uniform(self, low: float, high: float) -> float:
        return (low + high) / 2.0

    def gaussian(self, mu: float, sigma: float) -> float:
        return mu


class _RecordingEventBus:
    def __init__(self) -> None:
        self.published: list[object] = []

    def subscribe(self, event_type, handler):
        pass

    def publish(self, event):
        self.published.append(event)

    def publish_named(self, name, data):
        self.published.append({"name": name, "data": data})


def _unit(unit_id: str, x: int = 0, y: int = 0, faction: Faction = Faction.ALLIES) -> Unit:
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=80),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=20, ammo_remaining=20),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(),
    )


def _director() -> tuple[CombatDirector, _RecordingEventBus]:
    bus = _RecordingEventBus()
    director = CombatDirector(event_bus=bus, display_config=object())
    director.ballistic_engine = BallisticEngine(rng=_FixedRng())
    return director, bus


def test_cycle_fire_mode_order():
    unit = _unit("u1")

    assert unit.fire_mode == "free"
    assert unit.cycle_fire_mode() == "return"
    assert unit.cycle_fire_mode() == "hold"
    assert unit.cycle_fire_mode() == "free"


def test_hold_fire_blocks_attack():
    director, bus = _director()
    attacker = _unit("u1")
    target = _unit("e1", x=3, faction=Faction.AXIS)
    attacker.fire_mode = "hold"

    director.execute_attack(attacker, target)

    assert attacker.weapon.ammo_remaining == 20
    assert bus.published == []


def test_return_fire_waits_when_not_attacked():
    director, bus = _director()
    attacker = _unit("u1")
    target = _unit("e1", x=3, faction=Faction.AXIS)
    attacker.fire_mode = "return"

    director.execute_attack(attacker, target)

    assert attacker.weapon.ammo_remaining == 20
    assert bus.published == []


def test_return_fire_engages_after_being_hit():
    director, bus = _director()
    attacker = _unit("u1")
    target = _unit("e1", x=3, faction=Faction.AXIS)
    attacker.fire_mode = "return"
    attacker._last_attacked_tick = attacker._estimated_tick()

    director.execute_attack(attacker, target)

    assert attacker.weapon.ammo_remaining < 20
    assert bus.published != []


def test_free_fire_engages():
    director, bus = _director()
    attacker = _unit("u1")
    target = _unit("e1", x=3, faction=Faction.AXIS)

    director.execute_attack(attacker, target)

    assert attacker.weapon.ammo_remaining < 20
    assert bus.published != []


def test_set_fire_mode_command_sets_explicit_mode():
    director, _ = _director()
    unit = _unit("u1")

    director.handle_player_command(
        {"command": "set_fire_mode", "unit_ids": ["u1"], "fire_mode": "hold"}, [unit], object()
    )

    assert unit.fire_mode == "hold"


def test_set_fire_mode_command_cycles_without_value():
    director, _ = _director()
    unit = _unit("u1")

    director.handle_player_command({"command": "set_fire_mode", "unit_ids": ["u1"]}, [unit], object())

    assert unit.fire_mode == "return"
