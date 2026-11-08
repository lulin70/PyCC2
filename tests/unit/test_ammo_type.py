"""Tests for AP/HE ammunition switching (P1-6)."""

from __future__ import annotations

from types import SimpleNamespace

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.domain.value_objects.ammo_type import AmmoType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.combat_director import CombatDirector


class _FixedRng:
    """Deterministic RNG: always rolls the middle of the range."""

    def uniform(self, low: float, high: float) -> float:
        return (low + high) / 2.0

    def gaussian(self, mu: float, sigma: float) -> float:
        return mu


class _StubEventBus:
    def subscribe(self, event_type, handler):
        pass

    def publish(self, event):
        pass


def _unit(
    unit_id: str = "u1",
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    weapon_id: str = "rifle",
    ammo_type: AmmoType | None = None,
    available: tuple[AmmoType, ...] = (),
    x: int = 0,
    y: int = 0,
) -> Unit:
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=Faction.ALLIES,
        unit_type=unit_type,
        health=HealthComponent(hp=1000, max_hp=1000),
        morale=MoraleComponent(value=80),
        weapon=WeaponComponent(
            primary_weapon_id=weapon_id,
            max_ammo=20,
            ammo_remaining=20,
            ammo_type=ammo_type,
            available_ammo_types=available,
        ),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(),
    )


def _shot(attacker_faction: AmmoType, target: Unit) -> float:
    attacker = _unit(
        unit_id="shooter",
        unit_type=UnitType.TANK,
        weapon_id="tank_cannon",
        ammo_type=attacker_faction,
        available=(AmmoType.AP, AmmoType.HE),
    )
    target.position = PositionComponent(tile_coord=TileCoord(3, 0))
    engine = BallisticEngine(rng=_FixedRng())
    result = engine.calculate_shot(attacker, target)
    assert result.hit is True
    return result.damage_dealt


def test_cycle_ammo_toggles_between_ap_and_he():
    weapon = WeaponComponent(
        primary_weapon_id="tank_cannon",
        max_ammo=20,
        ammo_remaining=20,
        ammo_type=AmmoType.AP,
        available_ammo_types=(AmmoType.AP, AmmoType.HE),
    )

    assert weapon.cycle_ammo() is AmmoType.HE
    assert weapon.ammo_type is AmmoType.HE
    assert weapon.cycle_ammo() is AmmoType.AP


def test_cycle_ammo_returns_none_without_options():
    weapon = WeaponComponent(primary_weapon_id="rifle", max_ammo=20, ammo_remaining=20)

    assert weapon.can_switch_ammo is False
    assert weapon.cycle_ammo() is None


def test_he_deals_more_damage_to_infantry():
    target = _unit(unit_id="infantry", unit_type=UnitType.INFANTRY_SQUAD)

    assert _shot(AmmoType.HE, target) > _shot(AmmoType.AP, target)


def test_ap_deals_more_damage_to_vehicles():
    target = _unit(unit_id="tank", unit_type=UnitType.TANK)

    assert _shot(AmmoType.AP, target) > _shot(AmmoType.HE, target)


def test_legacy_weapon_without_ammo_type_is_unchanged():
    attacker = _unit(unit_id="rifleman")
    target = _unit(unit_id="target", x=3)
    engine = BallisticEngine(rng=_FixedRng())

    result = engine.calculate_shot(attacker, target)

    assert result.hit is True
    assert result.damage_dealt > 0.0


def test_switch_ammo_command_changes_weapon():
    director = CombatDirector(event_bus=_StubEventBus(), display_config=object())
    unit = _unit(
        unit_type=UnitType.TANK,
        weapon_id="tank_cannon",
        ammo_type=AmmoType.AP,
        available=(AmmoType.AP, AmmoType.HE),
    )

    director.handle_player_command(
        {"command": "switch_ammo", "unit_ids": ["u1"]}, [unit], SimpleNamespace()
    )

    assert unit.weapon.ammo_type is AmmoType.HE
