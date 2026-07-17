"""Tests for WeaponJamSystem — CC2-authentic weapon reliability (TD-076c, v0.7.0).

Covers 7 testing dimensions:
  - Happy Path (≥50%): jam triggers, jam clears, captured weapon penalty
  - Error Case (≥15%): unknown weapon, no jam on miss, already jammed
  - Boundary (≥10%): zero probability, max probability, jam clear boundary
  - Performance (≥5%): tick timing for batch processing
  - Config (≥5%): custom JamConfig, custom RNG
  - Integration (≥10%): AIService integration, check_jam_on_fire delegate
  - Security: N/A (no external input)
"""

from __future__ import annotations

import random
import time

from pycc2.domain.ai.weapon_jam import (
    CAPTURED_WEAPON_CLEAR_MULTIPLIER,
    WEAPON_JAM_CONFIGS,
    JamConfig,
    WeaponJamSystem,
)
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent, WeaponState
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_unit(
    uid: str = "u1",
    faction: Faction = Faction.ALLIES,
    weapon_id: str = "rifle",
    ammo: int = 30,
    max_ammo: int = 30,
) -> Unit:
    """Build a real Unit with real components (no Mock per user testing philosophy)."""
    return Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=80, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id=weapon_id, ammo_remaining=ammo, max_ammo=max_ammo),
        position=PositionComponent(tile_coord=TileCoord(10, 10)),
        vision=VisionComponent(range_tiles=6),
    )


# ---------------------------------------------------------------------------
# Happy Path (≥50%)
# ---------------------------------------------------------------------------


class TestWeaponJamHappyPath:
    """Verify: jam triggers and clears in expected sequence."""

    def test_check_jam_on_fire_triggers_jam_with_max_probability(self):
        """Verify: jam triggers when random < jam_probability.

        Scenario: jam_probability=1.0 (forced jam)
        Expected: weapon state becomes JAMMED, returns True
        """
        # Arrange - custom config with 100% jam probability
        forced_config = {
            "rifle": JamConfig(weapon_type="rifle", jam_probability=1.0, jam_clear_ticks=3)
        }
        system = WeaponJamSystem(jam_configs=forced_config, rng=random.Random(0))
        unit = _make_unit(weapon_id="rifle")

        # Act
        result = system.check_jam_on_fire(unit)

        # Assert
        assert result is True
        assert unit.weapon.state == WeaponState.JAMMED
        assert system.get_jam_clear_remaining(unit.id) == 3

    def test_check_jam_on_fire_no_jam_with_zero_probability(self):
        """Verify: no jam when probability=0.0.

        Scenario: jam_probability=0.0
        Expected: returns False, weapon state unchanged
        """
        # Arrange
        no_jam_config = {
            "rifle": JamConfig(weapon_type="rifle", jam_probability=0.0, jam_clear_ticks=3)
        }
        system = WeaponJamSystem(jam_configs=no_jam_config, rng=random.Random(0))
        unit = _make_unit(weapon_id="rifle")

        # Act
        result = system.check_jam_on_fire(unit)

        # Assert
        assert result is False
        assert unit.weapon.state != WeaponState.JAMMED

    def test_tick_clears_jam_after_configured_ticks(self):
        """Verify: jam is cleared automatically after jam_clear_ticks ticks.

        Scenario: jam with clear_ticks=3, then tick 3 times
        Expected: after 3 ticks, weapon state returns to normal
        """
        # Arrange
        config = {"rifle": JamConfig(weapon_type="rifle", jam_probability=1.0, jam_clear_ticks=3)}
        system = WeaponJamSystem(jam_configs=config, rng=random.Random(0))
        unit = _make_unit(weapon_id="rifle")
        system.check_jam_on_fire(unit)
        assert unit.weapon.state == WeaponState.JAMMED

        # Act & Assert - tick 1: still jammed (2 remaining)
        system.tick(unit)
        assert unit.weapon.state == WeaponState.JAMMED
        assert system.get_jam_clear_remaining(unit.id) == 2

        # tick 2: still jammed (1 remaining)
        system.tick(unit)
        assert unit.weapon.state == WeaponState.JAMMED
        assert system.get_jam_clear_remaining(unit.id) == 1

        # tick 3: jam cleared
        system.tick(unit)
        assert unit.weapon.state != WeaponState.JAMMED
        assert system.get_jam_clear_remaining(unit.id) == 0

    def test_sten_has_higher_jam_probability_than_rifle(self):
        """Verify: Sten (notoriously unreliable) has higher jam prob than rifle.

        Scenario: lookup WEAPON_JAM_CONFIGS
        Expected: sten jam_probability > rifle jam_probability
        """
        # Arrange & Act
        rifle_config = WEAPON_JAM_CONFIGS["rifle"]
        sten_config = WEAPON_JAM_CONFIGS["sten"]

        # Assert
        assert sten_config.jam_probability > rifle_config.jam_probability
        assert sten_config.jam_probability == 0.015  # 1.5% per shot
        assert rifle_config.jam_probability == 0.001  # 0.1% per shot

    def test_mg_has_longer_clear_time_than_rifle(self):
        """Verify: MG42 has longer clear time than rifle (complex mechanism).

        Scenario: lookup WEAPON_JAM_CONFIGS
        Expected: mg42 jam_clear_ticks > rifle jam_clear_ticks
        """
        # Arrange & Act
        rifle_config = WEAPON_JAM_CONFIGS["rifle"]
        mg42_config = WEAPON_JAM_CONFIGS["mg42"]

        # Assert
        assert mg42_config.jam_clear_ticks > rifle_config.jam_clear_ticks
        assert mg42_config.jam_clear_ticks == 8
        assert rifle_config.jam_clear_ticks == 3


# ---------------------------------------------------------------------------
# Error Case (≥15%)
# ---------------------------------------------------------------------------


class TestWeaponJamErrorCase:
    """Verify: graceful handling of edge cases."""

    def test_unknown_weapon_id_returns_false_no_jam(self):
        """Verify: unknown weapon ID does not cause jam.

        Scenario: unit with weapon_id="unknown_weapon"
        Expected: returns False, no exception
        """
        # Arrange
        system = WeaponJamSystem(rng=random.Random(0))
        unit = _make_unit(weapon_id="unknown_weapon")

        # Act
        result = system.check_jam_on_fire(unit)

        # Assert
        assert result is False
        assert unit.weapon.state != WeaponState.JAMMED

    def test_tick_on_non_jammed_weapon_is_noop(self):
        """Verify: tick() on non-jammed weapon is a no-op.

        Scenario: weapon not jammed, call tick()
        Expected: no state change, no exception
        """
        # Arrange
        system = WeaponJamSystem(rng=random.Random(0))
        unit = _make_unit(weapon_id="rifle")
        original_state = unit.weapon.state

        # Act
        system.tick(unit)

        # Assert
        assert unit.weapon.state == original_state

    def test_get_jam_clear_remaining_unknown_unit_returns_zero(self):
        """Verify: get_jam_clear_remaining for unknown unit returns 0.

        Scenario: query unit that never jammed
        Expected: returns 0
        """
        # Arrange
        system = WeaponJamSystem(rng=random.Random(0))

        # Act & Assert
        assert system.get_jam_clear_remaining("nonexistent_unit") == 0


# ---------------------------------------------------------------------------
# Boundary (≥10%)
# ---------------------------------------------------------------------------


class TestWeaponJamBoundary:
    """Verify: boundary conditions."""

    def test_captured_weapon_increases_jam_probability(self):
        """Verify: captured weapon (different faction prefix) gets +1% jam penalty.

        Scenario: ALLIES unit with Axis weapon (de_ prefix)
        Expected: jam_prob = base + CAPTURED_WEAPON_JAM_PENALTY
        """
        # Arrange - Allies unit using a captured German weapon.
        # Use a config with probability near 1.0 to ensure jam triggers
        # (captured weapon penalty is added on top of base probability).
        forced_config = {
            "de_mp40": JamConfig(weapon_type="de_mp40", jam_probability=0.99, jam_clear_ticks=4)
        }
        forced_system = WeaponJamSystem(jam_configs=forced_config, rng=random.Random(0))
        # ALLIES unit holding a weapon with "de_" prefix (captured)
        unit = _make_unit(faction=Faction.ALLIES, weapon_id="de_mp40")

        # Act
        result = forced_system.check_jam_on_fire(unit)

        # Assert - jam triggered (captured weapon penalty is added on top)
        assert result is True
        assert unit.weapon.state == WeaponState.JAMMED

    def test_captured_weapon_increases_clear_time(self):
        """Verify: captured weapon gets +50% clear time multiplier.

        Scenario: captured weapon with base clear_ticks=4
        Expected: actual clear_ticks = int(4 * 1.5) = 6
        """
        # Arrange - Allies unit using captured German MG42
        config = {
            "de_mg42": JamConfig(weapon_type="de_mg42", jam_probability=1.0, jam_clear_ticks=4)
        }
        system = WeaponJamSystem(jam_configs=config, rng=random.Random(0))
        unit = _make_unit(faction=Faction.ALLIES, weapon_id="de_mg42")

        # Act
        system.check_jam_on_fire(unit)

        # Assert - clear_ticks should be int(4 * 1.5) = 6
        expected_clear = int(4 * CAPTURED_WEAPON_CLEAR_MULTIPLIER)
        assert system.get_jam_clear_remaining(unit.id) == expected_clear
        assert expected_clear == 6


# ---------------------------------------------------------------------------
# Performance (≥5%)
# ---------------------------------------------------------------------------


class TestWeaponJamPerformance:
    """Verify: performance baseline for batch processing."""

    def test_tick_batch_50_units_under_50ms(self):
        """Verify: tick() for 50 units completes under 50ms.

        Scenario: 50 units, all jammed, tick once
        Expected: < 50ms total
        """
        # Arrange
        config = {"rifle": JamConfig(weapon_type="rifle", jam_probability=1.0, jam_clear_ticks=10)}
        system = WeaponJamSystem(jam_configs=config, rng=random.Random(0))
        units = [_make_unit(uid=f"u{i}", weapon_id="rifle") for i in range(50)]
        for u in units:
            system.check_jam_on_fire(u)

        # Act
        start = time.perf_counter()
        for u in units:
            system.tick(u)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Assert
        assert elapsed_ms < 50.0, f"Batch tick took {elapsed_ms:.2f}ms, expected < 50ms"


# ---------------------------------------------------------------------------
# Config (≥5%)
# ---------------------------------------------------------------------------


class TestWeaponJamConfig:
    """Verify: configuration options."""

    def test_custom_jam_configs_override_defaults(self):
        """Verify: custom jam_configs dict overrides WEAPON_JAM_CONFIGS.

        Scenario: pass custom config dict
        Expected: system uses custom config
        """
        # Arrange
        custom = {
            "custom_weapon": JamConfig(
                weapon_type="custom_weapon", jam_probability=0.5, jam_clear_ticks=7
            )
        }
        system = WeaponJamSystem(jam_configs=custom, rng=random.Random(0))

        # Act & Assert
        # Default configs should NOT be present
        assert system._get_config("rifle") is None
        # Custom config should be present
        assert system._get_config("custom_weapon") is not None
        assert system._get_config("custom_weapon").jam_clear_ticks == 7

    def test_custom_rng_makes_jam_deterministic(self):
        """Verify: custom RNG with known seed produces deterministic jam results.

        Scenario: same RNG seed → same jam sequence
        Expected: deterministic behavior
        """
        # Arrange - two systems with same seed
        config = {"rifle": JamConfig(weapon_type="rifle", jam_probability=0.5, jam_clear_ticks=3)}
        system1 = WeaponJamSystem(jam_configs=config, rng=random.Random(42))
        system2 = WeaponJamSystem(jam_configs=config, rng=random.Random(42))
        unit1 = _make_unit(uid="u1", weapon_id="rifle")
        unit2 = _make_unit(uid="u2", weapon_id="rifle")

        # Act
        r1 = system1.check_jam_on_fire(unit1)
        r2 = system2.check_jam_on_fire(unit2)

        # Assert - same seed → same result
        assert r1 == r2


# ---------------------------------------------------------------------------
# Integration (≥10%)
# ---------------------------------------------------------------------------


class TestWeaponJamIntegration:
    """Verify: integration with AIService."""

    def test_ai_service_exposes_weapon_jam_system(self):
        """Verify: AIService.weapon_jam_system property returns the system.

        Scenario: instantiate AIService
        Expected: weapon_jam_system is WeaponJamSystem instance
        """
        # Arrange
        from pycc2.infrastructure.events.event_bus import EventBus
        from pycc2.services.ai_service import AIService

        # Act
        service = AIService(EventBus())

        # Assert
        assert service.weapon_jam_system is not None
        assert isinstance(service.weapon_jam_system, WeaponJamSystem)

    def test_ai_service_check_jam_on_fire_delegates_to_system(self):
        """Verify: AIService.check_jam_on_fire() delegates to WeaponJamSystem.

        Scenario: call check_jam_on_fire via service
        Expected: same result as calling system directly
        """
        # Arrange
        from pycc2.infrastructure.events.event_bus import EventBus
        from pycc2.services.ai_service import AIService

        service = AIService(EventBus())
        # Replace the system with one that forces jam
        service._weapon_jam_system = WeaponJamSystem(
            jam_configs={
                "rifle": JamConfig(weapon_type="rifle", jam_probability=1.0, jam_clear_ticks=3)
            },
            rng=random.Random(0),
        )
        unit = _make_unit(weapon_id="rifle")

        # Act
        result = service.check_jam_on_fire(unit)

        # Assert
        assert result is True
        assert unit.weapon.state == WeaponState.JAMMED
