"""
Unit Tests for WeaponJamSystem

Tests jam probability, unjam mechanics, captured weapon penalties,
and per-weapon-type configurations.
"""

import pytest
from unittest.mock import Mock

from pycc2.domain.ai.weapon_jam import (
    WeaponJamSystem,
    JamConfig,
    WEAPON_JAM_CONFIGS,
    CAPTURED_WEAPON_JAM_PENALTY,
    CAPTURED_WEAPON_CLEAR_MULTIPLIER,
)
from pycc2.domain.components.weapon_component import WeaponState
from pycc2.domain.entities.unit import Faction


# ===========================================================================
# Stub helpers
# ===========================================================================

def _make_unit(unit_id, weapon_id="rifle", faction=Faction.ALLIES,
               weapon_state=WeaponState.READY, ammo_remaining=100):
    """Create a mock unit for jam testing."""
    unit = Mock()
    unit.id = unit_id
    unit.faction = faction

    weapon = Mock()
    weapon.primary_weapon_id = weapon_id
    weapon.ammo_remaining = ammo_remaining
    weapon.state = weapon_state
    weapon.clear_jam = Mock()
    unit.weapon = weapon

    return unit


# ===========================================================================
# Tests — JamConfig Lookup
# ===========================================================================

@pytest.mark.unit
class TestJamConfigLookup:
    """Test weapon jam configuration lookup."""

    def test_rifle_config_exists(self):
        assert "rifle" in WEAPON_JAM_CONFIGS
        assert WEAPON_JAM_CONFIGS["rifle"].jam_probability == 0.001

    def test_sten_high_jam_probability(self):
        assert "sten" in WEAPON_JAM_CONFIGS
        assert WEAPON_JAM_CONFIGS["sten"].jam_probability == 0.015

    def test_mg_config_exists(self):
        assert "mg42" in WEAPON_JAM_CONFIGS
        assert WEAPON_JAM_CONFIGS["mg42"].jam_clear_ticks == 8

    def test_pistol_config_exists(self):
        assert "pistol" in WEAPON_JAM_CONFIGS
        assert WEAPON_JAM_CONFIGS["pistol"].jam_clear_ticks == 2

    def test_at_weapon_config(self):
        assert "piat" in WEAPON_JAM_CONFIGS
        assert WEAPON_JAM_CONFIGS["piat"].jam_probability == 0.008

    def test_tank_cannon_config(self):
        assert "tank_cannon" in WEAPON_JAM_CONFIGS
        assert WEAPON_JAM_CONFIGS["tank_cannon"].jam_clear_ticks == 8


# ===========================================================================
# Tests — Check Jam on Fire
# ===========================================================================

@pytest.mark.unit
class TestCheckJamOnFire:
    """Test jam checking when unit fires."""

    def test_no_jam_with_rng_high(self):
        import random
        rng = random.Random()
        rng.random = lambda: 1.0  # Always above jam probability
        system = WeaponJamSystem(rng=rng)
        unit = _make_unit("u1", weapon_id="rifle")
        result = system.check_jam_on_fire(unit)
        assert result is False

    def test_jam_with_rng_low(self):
        import random
        rng = random.Random()
        rng.random = lambda: 0.0  # Always below jam probability
        system = WeaponJamSystem(rng=rng)
        unit = _make_unit("u1", weapon_id="rifle")
        result = system.check_jam_on_fire(unit)
        assert result is True
        assert unit.weapon.state == WeaponState.JAMMED

    def test_unknown_weapon_no_jam(self):
        import random
        rng = random.Random()
        rng.random = lambda: 0.0
        system = WeaponJamSystem(rng=rng)
        unit = _make_unit("u1", weapon_id="unknown_weapon_xyz")
        result = system.check_jam_on_fire(unit)
        assert result is False

    def test_jam_sets_clear_timer(self):
        import random
        rng = random.Random()
        rng.random = lambda: 0.0
        system = WeaponJamSystem(rng=rng)
        unit = _make_unit("u1", weapon_id="rifle")
        system.check_jam_on_fire(unit)
        assert system.get_jam_clear_remaining("u1") == WEAPON_JAM_CONFIGS["rifle"].jam_clear_ticks

    def test_sten_jam_clear_ticks(self):
        import random
        rng = random.Random()
        rng.random = lambda: 0.0
        system = WeaponJamSystem(rng=rng)
        unit = _make_unit("u1", weapon_id="sten")
        system.check_jam_on_fire(unit)
        assert system.get_jam_clear_remaining("u1") == 5


# ===========================================================================
# Tests — Captured Weapon Penalty
# ===========================================================================

@pytest.mark.unit
class TestCapturedWeaponPenalty:
    """Test captured weapon jam and clear time penalties."""

    def test_captured_weapon_higher_jam_chance(self):
        import random
        rng = random.Random()
        rng.random = lambda: 0.0
        system = WeaponJamSystem(rng=rng)
        # Allied unit with German weapon prefix — use mg42 which is in configs
        unit = _make_unit("u1", weapon_id="mg42", faction=Faction.ALLIES)
        # mg42 is a German weapon (de_ prefix not in ID, but _is_captured_weapon
        # checks for "de_" prefix). Let's use a weapon that IS captured.
        # Actually, mg42 doesn't start with "de_" so it won't be detected as captured.
        # Use a custom weapon ID that starts with "de_" and is in configs.
        system._configs["de_mg42"] = JamConfig(weapon_type="de_mg42", jam_probability=0.01, jam_clear_ticks=8)
        unit2 = _make_unit("u2", weapon_id="de_mg42", faction=Faction.ALLIES)
        result = system.check_jam_on_fire(unit2)
        assert result is True

    def test_captured_weapon_longer_clear_time(self):
        import random
        rng = random.Random()
        rng.random = lambda: 0.0
        system = WeaponJamSystem(rng=rng)
        unit = _make_unit("u1", weapon_id="de_mg42", faction=Faction.ALLIES)
        # Need to add de_mg42 to configs for this test
        system._configs["de_mg42"] = JamConfig(weapon_type="de_mg42", jam_probability=0.01, jam_clear_ticks=8)
        system.check_jam_on_fire(unit)
        # Captured weapon: 8 * 1.5 = 12 ticks
        assert system.get_jam_clear_remaining("u1") == 12

    def test_native_weapon_no_penalty(self):
        import random
        rng = random.Random()
        rng.random = lambda: 0.0
        system = WeaponJamSystem(rng=rng)
        # Allied unit with Allied weapon
        unit = _make_unit("u1", weapon_id="rifle", faction=Faction.ALLIES)
        system.check_jam_on_fire(unit)
        expected = WEAPON_JAM_CONFIGS["rifle"].jam_clear_ticks
        assert system.get_jam_clear_remaining("u1") == expected


# ===========================================================================
# Tests — Tick (Unjam Mechanics)
# ===========================================================================

@pytest.mark.unit
class TestTickUnjam:
    """Test jam clearing over time."""

    def test_tick_decrements_clear_timer(self):
        import random
        rng = random.Random()
        rng.random = lambda: 0.0
        system = WeaponJamSystem(rng=rng)
        unit = _make_unit("u1", weapon_id="rifle")
        system.check_jam_on_fire(unit)
        initial = system.get_jam_clear_remaining("u1")

        unit.weapon.state = WeaponState.JAMMED
        system.tick(unit)
        assert system.get_jam_clear_remaining("u1") == initial - 1

    def test_jam_cleared_after_ticks(self):
        import random
        rng = random.Random()
        rng.random = lambda: 0.0
        system = WeaponJamSystem(rng=rng)
        unit = _make_unit("u1", weapon_id="pistol")  # 2 ticks to clear
        system.check_jam_on_fire(unit)

        unit.weapon.state = WeaponState.JAMMED
        system.tick(unit)  # remaining: 2 -> 1
        system.tick(unit)  # remaining: 1 -> 0
        system.tick(unit)  # remaining: 0 -> clear_jam called
        unit.weapon.clear_jam.assert_called()

    def test_no_tick_for_non_jammed_weapon(self):
        system = WeaponJamSystem()
        unit = _make_unit("u1", weapon_id="rifle", weapon_state=WeaponState.READY)
        system.tick(unit)
        unit.weapon.clear_jam.assert_not_called()

    def test_get_jam_clear_remaining_no_entry(self):
        system = WeaponJamSystem()
        assert system.get_jam_clear_remaining("nonexistent") == 0


# ===========================================================================
# Tests — Custom Jam Configs
# ===========================================================================

@pytest.mark.unit
class TestCustomJamConfigs:
    """Test using custom jam configurations."""

    def test_custom_config(self):
        custom = {
            "test_weapon": JamConfig(
                weapon_type="test_weapon",
                jam_probability=0.5,
                jam_clear_ticks=10,
            ),
        }
        system = WeaponJamSystem(jam_configs=custom)
        import random
        rng = random.Random()
        rng.random = lambda: 0.0
        system._rng = rng

        unit = _make_unit("u1", weapon_id="test_weapon")
        result = system.check_jam_on_fire(unit)
        assert result is True
        assert system.get_jam_clear_remaining("u1") == 10


# ===========================================================================
# Tests — Is Captured Weapon
# ===========================================================================

@pytest.mark.unit
class TestIsCapturedWeapon:
    """Test captured weapon detection."""

    def test_allied_with_us_prefix(self):
        unit = _make_unit("u1", weapon_id="us_m1_garand", faction=Faction.ALLIES)
        assert WeaponJamSystem._is_captured_weapon(unit, "us_m1_garand") is False

    def test_allied_with_de_prefix(self):
        unit = _make_unit("u1", weapon_id="de_mg42", faction=Faction.ALLIES)
        assert WeaponJamSystem._is_captured_weapon(unit, "de_mg42") is True

    def test_axis_with_de_prefix(self):
        unit = _make_unit("u1", weapon_id="de_mg42", faction=Faction.AXIS)
        assert WeaponJamSystem._is_captured_weapon(unit, "de_mg42") is False

    def test_axis_with_us_prefix(self):
        unit = _make_unit("u1", weapon_id="us_m1_garand", faction=Faction.AXIS)
        assert WeaponJamSystem._is_captured_weapon(unit, "us_m1_garand") is True

    def test_unknown_faction_no_penalty(self):
        unit = _make_unit("u1", weapon_id="rifle")
        unit.faction = Mock()
        unit.faction.name = "NEUTRAL"
        assert WeaponJamSystem._is_captured_weapon(unit, "rifle") is False
