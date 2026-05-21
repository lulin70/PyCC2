"""
Unit tests for WeaponComponent
"""

from __future__ import annotations

from pycc2.domain.components.weapon_component import (
    WeaponComponent,
    WeaponState,
)


class TestWeaponComponentConstruction:
    def test_default_construction(self):
        wc = WeaponComponent(
            primary_weapon_id="m16",
            ammo_remaining=30,
            max_ammo=30,
        )
        assert wc.primary_weapon_id == "m16"
        assert wc.ammo_remaining == 30
        assert wc.max_ammo == 30
        assert wc.state == WeaponState.READY

    def test_empty_ammo_state(self):
        wc = WeaponComponent(
            primary_weapon_id="m16",
            ammo_remaining=0,
            max_ammo=30,
        )
        assert wc.state == WeaponState.OUT_OF_AMMO

    def test_reloading_state_on_construction(self):
        wc = WeaponComponent(
            primary_weapon_id="m16",
            ammo_remaining=10,
            max_ammo=30,
            reload_ticks_left=5,
        )
        assert wc.state == WeaponState.RELOADING


class TestWeaponComponentFire:
    def test_fire_consumes_ammo(self):
        wc = WeaponComponent(primary_weapon_id="m16", ammo_remaining=30, max_ammo=30)
        result = wc.fire()
        assert result is True
        assert wc.ammo_remaining == 29

    def test_fire_returns_false_when_out_of_ammo(self):
        wc = WeaponComponent(primary_weapon_id="m16", ammo_remaining=0, max_ammo=30)
        result = wc.fire()
        assert result is False
        assert wc.state == WeaponState.OUT_OF_AMMO

    def test_fire_last_round(self):
        wc = WeaponComponent(primary_weapon_id="m16", ammo_remaining=1, max_ammo=30)
        result = wc.fire()
        assert result is True
        assert wc.ammo_remaining == 0
        assert wc.state == WeaponState.OUT_OF_AMMO

    def test_fire_when_reloading(self):
        wc = WeaponComponent(
            primary_weapon_id="m16",
            ammo_remaining=20,
            max_ammo=30,
            reload_ticks_left=3,
        )
        result = wc.fire()
        assert result is False


class TestWeaponComponentReload:
    def test_start_reload(self):
        wc = WeaponComponent(primary_weapon_id="m16", ammo_remaining=5, max_ammo=30)
        wc.start_reload(5)
        assert wc.state == WeaponState.RELOADING
        assert wc.reload_ticks_left == 5

    def test_tick_decrements_reload(self):
        wc = WeaponComponent(
            primary_weapon_id="m16",
            ammo_remaining=5,
            max_ammo=30,
            reload_ticks_left=3,
        )
        wc.tick()
        assert wc.reload_ticks_left == 2
        assert wc.state == WeaponState.RELOADING

    def test_tick_completes_reload(self):
        wc = WeaponComponent(
            primary_weapon_id="m16",
            ammo_remaining=5,
            max_ammo=30,
            reload_ticks_left=1,
        )
        wc.tick()
        assert wc.reload_ticks_left == 0
        assert wc.ammo_remaining == wc.max_ammo
        assert wc.state == WeaponState.READY

    def test_tick_when_not_reloading(self):
        wc = WeaponComponent(primary_weapon_id="m16", ammo_remaining=20, max_ammo=30)
        initial_ticks = wc.reload_ticks_left
        wc.tick()
        assert wc.reload_ticks_left == initial_ticks


class TestWeaponComponentJam:
    def test_clear_jam(self):
        wc = WeaponComponent(
            primary_weapon_id="m16",
            ammo_remaining=15,
            max_ammo=30,
        )
        object.__setattr__(wc, "state", WeaponState.JAMMED)
        wc.clear_jam()
        assert wc.state == WeaponState.READY


class TestWeaponComponentProperties:
    def test_can_fire_true(self):
        wc = WeaponComponent(primary_weapon_id="m16", ammo_remaining=20, max_ammo=30)
        assert wc.can_fire is True

    def test_can_fire_false_no_ammo(self):
        wc = WeaponComponent(primary_weapon_id="m16", ammo_remaining=0, max_ammo=30)
        assert wc.can_fire is False

    def test_can_fire_false_reloading(self):
        wc = WeaponComponent(
            primary_weapon_id="m16",
            ammo_remaining=20,
            max_ammo=30,
            reload_ticks_left=3,
        )
        assert wc.can_fire is False

    def test_ammo_ratio_full(self):
        wc = WeaponComponent(primary_weapon_id="m16", ammo_remaining=30, max_ammo=30)
        assert wc.ammo_ratio == 1.0

    def test_ammo_ratio_half(self):
        wc = WeaponComponent(primary_weapon_id="m16", ammo_remaining=15, max_ammo=30)
        assert wc.ammo_ratio == 0.5

    def test_is_reloading_true(self):
        wc = WeaponComponent(
            primary_weapon_id="m16",
            ammo_remaining=20,
            max_ammo=30,
            reload_ticks_left=3,
        )
        assert wc.is_reloading is True

    def test_is_reloading_false(self):
        wc = WeaponComponent(primary_weapon_id="m16", ammo_remaining=20, max_ammo=30)
        assert wc.is_reloading is False


class TestWeaponStateMachineTransitions:
    def test_ready_to_out_of_ammo(self):
        wc = WeaponComponent(primary_weapon_id="m16", ammo_remaining=1, max_ammo=30)
        wc.fire()
        assert wc.state == WeaponState.OUT_OF_AMMO

    def test_ready_to_reloading(self):
        wc = WeaponComponent(primary_weapon_id="m16", ammo_remaining=20, max_ammo=30)
        wc.start_reload(3)
        assert wc.state == WeaponState.RELOADING

    def test_reloading_to_ready(self):
        wc = WeaponComponent(
            primary_weapon_id="m16",
            ammo_remaining=5,
            max_ammo=30,
            reload_ticks_left=1,
        )
        wc.tick()
        assert wc.state == WeaponState.READY
