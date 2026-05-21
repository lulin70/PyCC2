"""
Unit tests for HealthComponent
"""

from __future__ import annotations

from pycc2.domain.components.health_component import (
    HealthComponent,
    HealthState,
)


class TestHealthComponentConstruction:
    def test_default_construction(self):
        hc = HealthComponent(hp=100, max_hp=100)
        assert hc.hp == 100
        assert hc.max_hp == 100
        assert hc.state == HealthState.HEALTHY

    def test_full_hp_is_healthy(self):
        hc = HealthComponent(hp=100, max_hp=100)
        assert hc.state == HealthState.HEALTHY
        assert hc.is_healthy is True
        assert hc.is_alive is True

    def test_wounded_state(self):
        hc = HealthComponent(hp=50, max_hp=100)
        assert hc.state == HealthState.WOUNDED
        assert hc.is_healthy is False
        assert hc.is_alive is True

    def test_critical_state(self):
        hc = HealthComponent(hp=20, max_hp=100)
        assert hc.state == HealthState.CRITICAL
        assert hc.is_healthy is False
        assert hc.is_alive is True

    def test_dead_state_at_zero(self):
        hc = HealthComponent(hp=0, max_hp=100)
        assert hc.state == HealthState.DEAD
        assert hc.is_alive is False


class TestHealthComponentHpRatio:
    def test_full_hp_ratio(self):
        hc = HealthComponent(hp=100, max_hp=100)
        assert hc.hp_ratio == 1.0

    def test_half_hp_ratio(self):
        hc = HealthComponent(hp=50, max_hp=100)
        assert hc.hp_ratio == 0.5

    def test_zero_hp_ratio(self):
        hc = HealthComponent(hp=0, max_hp=100)
        assert hc.hp_ratio == 0.0

    def test_boundary_healthy_wounded(self):
        hc = HealthComponent(hp=71, max_hp=100)
        assert hc.state == HealthState.HEALTHY
        hc2 = HealthComponent(hp=70, max_hp=100)
        assert hc2.state == HealthState.WOUNDED

    def test_boundary_wounded_critical(self):
        hc = HealthComponent(hp=30, max_hp=100)
        assert hc.state == HealthState.WOUNDED
        hc2 = HealthComponent(hp=29, max_hp=100)
        assert hc2.state == HealthState.CRITICAL


class TestHealthComponentTakeDamage:
    def test_normal_damage(self):
        hc = HealthComponent(hp=100, max_hp=100)
        actual = hc.take_damage(30)
        assert actual == 30
        assert hc.hp == 70
        assert hc.state == HealthState.WOUNDED

    def test_overkill_damage(self):
        hc = HealthComponent(hp=50, max_hp=100)
        actual = hc.take_damage(100)
        assert actual == 50
        assert hc.hp == 0
        assert hc.state == HealthState.DEAD

    def test_zero_damage(self):
        hc = HealthComponent(hp=100, max_hp=100)
        actual = hc.take_damage(0)
        assert actual == 0
        assert hc.hp == 100
        assert hc.state == HealthState.HEALTHY

    def test_lethal_damage(self):
        hc = HealthComponent(hp=10, max_hp=100)
        actual = hc.take_damage(10)
        assert actual == 10
        assert hc.hp == 0
        assert hc.state == HealthState.DEAD

    def test_damage_on_dead_unit(self):
        hc = HealthComponent(hp=0, max_hp=100)
        actual = hc.take_damage(10)
        assert actual == 0
        assert hc.hp == 0


class TestHealthComponentHeal:
    def test_normal_heal(self):
        hc = HealthComponent(hp=50, max_hp=100)
        actual = hc.heal(20)
        assert actual == 20
        assert hc.hp == 70

    def test_heal_exceeds_max(self):
        hc = HealthComponent(hp=80, max_hp=100)
        actual = hc.heal(50)
        assert actual == 20
        assert hc.hp == 100
        assert hc.state == HealthState.HEALTHY

    def test_zero_heal(self):
        hc = HealthComponent(hp=50, max_hp=100)
        actual = hc.heal(0)
        assert actual == 0
        assert hc.hp == 50

    def test_heal_dead_unit(self):
        hc = HealthComponent(hp=0, max_hp=100)
        actual = hc.heal(20)
        assert actual == 20
        assert hc.hp == 20
        assert hc.state == HealthState.CRITICAL


class TestHealthStateTransitions:
    def test_healthy_to_wounded(self):
        hc = HealthComponent(hp=100, max_hp=100)
        hc.take_damage(31)
        assert hc.state == HealthState.WOUNDED

    def test_wounded_to_critical(self):
        hc = HealthComponent(hp=60, max_hp=100)
        hc.take_damage(35)
        assert hc.state == HealthState.CRITICAL

    def test_critical_to_dead(self):
        hc = HealthComponent(hp=20, max_hp=100)
        hc.take_damage(25)
        assert hc.state == HealthState.DEAD

    def test_cannot_recover_from_dead_by_healing(self):
        hc = HealthComponent(hp=0, max_hp=100)
        hc.heal(5)
        assert hc.state != HealthState.DEAD
