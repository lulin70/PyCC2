"""Tests for ammo reload and rear-area resupply (P0-3)."""

from __future__ import annotations

from types import SimpleNamespace

from pycc2.domain.components.weapon_component import WeaponComponent, WeaponState
from pycc2.services.combat_director import RELOAD_TICKS, CombatDirector
from pycc2.services.game_loop_updating import GameLoopUpdatingMixin


def _weapon(ammo: int = 0, reserve: int = 10, max_ammo: int = 10) -> WeaponComponent:
    weapon = WeaponComponent(
        primary_weapon_id="rifle",
        max_ammo=max_ammo,
        ammo_remaining=ammo,
        reserve_ammo=reserve,
    )
    return weapon


def test_finite_reserve_is_consumed_on_reload():
    weapon = _weapon(ammo=0, reserve=10, max_ammo=10)
    weapon.start_reload(RELOAD_TICKS)

    for _ in range(RELOAD_TICKS):
        weapon.tick()

    assert weapon.ammo_remaining == 10
    assert weapon.reserve_ammo == 0
    assert weapon.state == WeaponState.READY


def test_empty_finite_reserve_stays_out_of_ammo():
    weapon = _weapon(ammo=0, reserve=0, max_ammo=10)
    weapon.start_reload(RELOAD_TICKS)

    for _ in range(RELOAD_TICKS):
        weapon.tick()

    assert weapon.ammo_remaining == 0
    assert weapon.state == WeaponState.OUT_OF_AMMO


def test_legacy_reserve_behaviour_is_unchanged():
    weapon = WeaponComponent(
        primary_weapon_id="rifle",
        max_ammo=10,
        ammo_remaining=0,
    )
    weapon.start_reload(RELOAD_TICKS)

    for _ in range(RELOAD_TICKS):
        weapon.tick()

    assert weapon.ammo_remaining == 10
    assert weapon.state == WeaponState.READY


class _MapStub:
    width = 10
    height = 10


def _director() -> CombatDirector:
    return CombatDirector(event_bus=object(), display_config=object())


def _unit_with_weapon(weapon: WeaponComponent):
    return SimpleNamespace(
        id="u1",
        weapon=weapon,
        is_alive=True,
        squad_ref=None,
        position=SimpleNamespace(tile_coord=SimpleNamespace(x=0, y=0)),
    )


def test_combat_director_starts_reload_when_empty():
    director = _director()
    weapon = _weapon(ammo=0, reserve=10, max_ammo=10)
    unit = _unit_with_weapon(weapon)

    director.update([unit], _MapStub(), 0.033)

    assert weapon.state == WeaponState.RELOADING


def test_combat_director_does_not_reload_without_reserve():
    director = _director()
    weapon = _weapon(ammo=0, reserve=0, max_ammo=10)
    unit = _unit_with_weapon(weapon)

    director.update([unit], _MapStub(), 0.033)

    assert weapon.state == WeaponState.OUT_OF_AMMO


def test_logistics_restores_reserve_near_friendly_spawn():
    weapon = _weapon(ammo=5, reserve=0, max_ammo=10)
    unit = SimpleNamespace(
        is_alive=True,
        faction=SimpleNamespace(name="ALLIES"),
        position=SimpleNamespace(tile_coord=SimpleNamespace(x=2, y=2)),
        weapon=weapon,
    )
    fake_loop = SimpleNamespace(
        _logistics_counter=59,
        _scenario_data={"spawn_points": [{"side": "allies", "position": [2, 2]}]},
        state=SimpleNamespace(units=[unit]),
    )

    GameLoopUpdatingMixin._update_logistics(fake_loop)

    assert weapon.reserve_ammo == 1
    assert fake_loop._logistics_counter == 0


def test_logistics_ignores_distant_units():
    weapon = _weapon(ammo=5, reserve=0, max_ammo=10)
    unit = SimpleNamespace(
        is_alive=True,
        faction=SimpleNamespace(name="ALLIES"),
        position=SimpleNamespace(tile_coord=SimpleNamespace(x=9, y=9)),
        weapon=weapon,
    )
    fake_loop = SimpleNamespace(
        _logistics_counter=59,
        _scenario_data={"spawn_points": [{"side": "allies", "position": [2, 2]}]},
        state=SimpleNamespace(units=[unit]),
    )

    GameLoopUpdatingMixin._update_logistics(fake_loop)

    assert weapon.reserve_ammo == 0
