"""
E2E tests for AI behaviors in an integrated combat context.

Validates ammo pickup, weapon jam, surrender, squad degradation,
NCO rally, and smoke tactical systems work correctly without
requiring pygame/display.
"""

from __future__ import annotations

import random
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from pycc2.domain.ai.ammo_pickup import (
    AmmoPickupSystem,
    AmmoSourceType,
    FallenUnitCache,
    FallenUnitEntry,
    PickupResult,
)
from pycc2.domain.ai.smoke_tactical_ai import (
    SmokeDeployment,
    SmokeGrenadeCapability,
    SmokeManager,
)
from pycc2.domain.ai.squad_degradation import (
    ADVANCED_TACTICS,
    BASIC_TACTICS,
    RALLY_COOLDOWN_TICKS,
    RALLY_RESTORE_MORALE,
    SquadDegradationManager,
    SquadState,
    NCORallyBehavior,
)
from pycc2.domain.ai.surrender_system import (
    AMMO_RATIO_THRESHOLD,
    MORALE_THRESHOLD,
    SurrenderSystem,
    FallenUnitCache as SurrenderFallenUnitCache,
)
from pycc2.domain.ai.weapon_jam import (
    CAPTURED_WEAPON_CLEAR_MULTIPLIER,
    CAPTURED_WEAPON_JAM_PENALTY,
    WEAPON_JAM_CONFIGS,
    WeaponJamSystem,
)
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent, MoraleState
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.weapon_component import WeaponComponent, WeaponState
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitState, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord


# ---------------------------------------------------------------------------
# Helpers — create units without pygame
# ---------------------------------------------------------------------------

def _make_unit(
    unit_id: str = "test_unit",
    name: str = "Test Unit",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 80,
    ammo: int = 10,
    max_ammo: int = 10,
    weapon_id: str = "rifle",
    x: int = 5,
    y: int = 5,
    squad_id: str | None = None,
) -> Unit:
    unit = Unit(
        id=unit_id,
        name=name,
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale),
        weapon=WeaponComponent(
            primary_weapon_id=weapon_id,
            ammo_remaining=ammo,
            max_ammo=max_ammo,
        ),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=5),
        squad_id=squad_id,
    )
    return unit


def _kill_unit(unit: Unit) -> None:
    unit.take_damage(unit.health.max_hp + 100)


# ---------------------------------------------------------------------------
# FallenUnitCache tests
# ---------------------------------------------------------------------------

class TestFallenUnitCache:
    def test_fallen_unit_cache_creation(self) -> None:
        """When a unit dies, FallenUnitCache registers its position/ammo/weapon."""
        cache = FallenUnitCache()
        unit = _make_unit(
            unit_id="fallen_1",
            ammo=7,
            max_ammo=10,
            weapon_id="sten",
            x=8,
            y=12,
        )
        _kill_unit(unit)

        cache.register(unit, current_tick=100)

        assert cache.entry_count == 1
        entry = cache._entries[0]
        assert entry.unit_id == "fallen_1"
        assert entry.position == TileCoord(8, 12)
        assert entry.ammo_remaining == 7
        assert entry.weapon_type == "sten"

    def test_fallen_unit_cache_expiry(self) -> None:
        """Caches expire after 300 ticks."""
        cache = FallenUnitCache()
        unit = _make_unit(unit_id="expired_unit", ammo=5, x=3, y=3)
        _kill_unit(unit)

        cache.register(unit, current_tick=0)
        assert cache.entry_count == 1

        # Before expiry — should still be there
        sources = cache.find_sources_near(
            position=TileCoord(3, 3),
            seeker_faction=Faction.AXIS,
            current_tick=299,
        )
        assert cache.entry_count == 1

        # After expiry — should be pruned
        sources = cache.find_sources_near(
            position=TileCoord(3, 3),
            seeker_faction=Faction.AXIS,
            current_tick=300,
        )
        assert cache.entry_count == 0


# ---------------------------------------------------------------------------
# AmmoPickupSystem tests
# ---------------------------------------------------------------------------

class TestAmmoPickup:
    def test_ammo_pickup_from_friendly(self) -> None:
        """AmmoPickupSystem allows picking up ammo from friendly fallen within 5 tiles."""
        cache = FallenUnitCache()
        fallen = _make_unit(
            unit_id="fallen_ally",
            faction=Faction.ALLIES,
            ammo=8,
            max_ammo=10,
            weapon_id="rifle",
            x=7,
            y=5,
        )
        _kill_unit(fallen)
        cache.register(fallen, current_tick=0)

        seeker = _make_unit(
            unit_id="seeker_ally",
            faction=Faction.ALLIES,
            ammo=1,
            max_ammo=10,
            weapon_id="rifle",
            x=5,
            y=5,
        )

        pickup_system = AmmoPickupSystem(fallen_cache=cache)
        sources = cache.find_sources_near(
            position=seeker.position.tile_coord,
            seeker_faction=seeker.faction,
            current_tick=0,
        )
        assert len(sources) >= 1, "Should find friendly fallen within 5 tiles"
        assert sources[0].source_type == AmmoSourceType.FALLEN_COMRADE

    def test_ammo_pickup_from_enemy(self) -> None:
        """Picking up enemy weapons incurs accuracy penalty (-20%) and slower reload (+50%)."""
        cache = FallenUnitCache()
        fallen = _make_unit(
            unit_id="fallen_enemy",
            faction=Faction.AXIS,
            ammo=6,
            max_ammo=10,
            weapon_id="mp40",
            x=6,
            y=5,
        )
        _kill_unit(fallen)
        cache.register(fallen, current_tick=0)

        seeker = _make_unit(
            unit_id="seeker_ally",
            faction=Faction.ALLIES,
            ammo=1,
            max_ammo=10,
            weapon_id="rifle",
            x=5,
            y=5,
        )

        pickup_system = AmmoPickupSystem(fallen_cache=cache)
        sources = cache.find_sources_near(
            position=seeker.position.tile_coord,
            seeker_faction=seeker.faction,
            current_tick=0,
        )
        enemy_sources = [s for s in sources if s.source_type == AmmoSourceType.ENEMY_CORPSE]
        assert len(enemy_sources) >= 1, "Should find enemy corpse within 3 tiles"

        # Verify penalty constants
        assert pickup_system.CAPTURED_ACCURACY_PENALTY == pytest.approx(0.20)
        assert pickup_system.CAPTURED_RELOAD_PENALTY == pytest.approx(0.50)

    def test_ammo_pickup_requires_stance(self) -> None:
        """Must be PRONE or CROUCHING to pick up."""
        pickup_system = AmmoPickupSystem()
        unit = _make_unit(unit_id="standing_unit")

        # Default stance is STANDING via combat_state — should fail
        from pycc2.domain.systems.combat_mechanics_enhanced import Stance

        with patch.object(
            AmmoPickupSystem, "_get_unit_stance", return_value=Stance.STANDING
        ):
            assert pickup_system.can_pickup(unit) is False

        with patch.object(
            AmmoPickupSystem, "_get_unit_stance", return_value=Stance.PRONE
        ):
            with patch.object(
                AmmoPickupSystem, "_is_suppressed_moderate", return_value=False
            ):
                assert pickup_system.can_pickup(unit) is True

        with patch.object(
            AmmoPickupSystem, "_get_unit_stance", return_value=Stance.CROUCHING
        ):
            with patch.object(
                AmmoPickupSystem, "_is_suppressed_moderate", return_value=False
            ):
                assert pickup_system.can_pickup(unit) is True

    def test_ammo_pickup_blocked_when_suppressed(self) -> None:
        """Cannot pick up when suppression > MODERATE."""
        pickup_system = AmmoPickupSystem()
        unit = _make_unit(unit_id="suppressed_unit")

        with patch.object(
            AmmoPickupSystem, "_is_suppressed_moderate", return_value=True
        ):
            assert pickup_system.can_pickup(unit) is False

        with patch.object(
            AmmoPickupSystem, "_is_suppressed_moderate", return_value=False
        ):
            with patch.object(
                AmmoPickupSystem, "_get_unit_stance", return_value=MagicMock()
            ):
                # With stance returning PRONE, it should be allowed
                from pycc2.domain.systems.combat_mechanics_enhanced import Stance
                with patch.object(
                    AmmoPickupSystem, "_get_unit_stance", return_value=Stance.PRONE
                ):
                    assert pickup_system.can_pickup(unit) is True


# ---------------------------------------------------------------------------
# WeaponJamSystem tests
# ---------------------------------------------------------------------------

class TestWeaponJam:
    def test_weapon_jam_probability(self) -> None:
        """WeaponJamSystem has correct jam probabilities for weapon types."""
        # Rifle: 0.1%
        assert WEAPON_JAM_CONFIGS["rifle"].jam_probability == pytest.approx(0.001)
        # Sten (SMG): 1.5%
        assert WEAPON_JAM_CONFIGS["sten"].jam_probability == pytest.approx(0.015)
        # MG42: 0.3%
        assert WEAPON_JAM_CONFIGS["mg42"].jam_probability == pytest.approx(0.003)
        # Pistol: 0.5%
        assert WEAPON_JAM_CONFIGS["pistol"].jam_probability == pytest.approx(0.005)
        # PIAT (AT): 0.8%
        assert WEAPON_JAM_CONFIGS["piat"].jam_probability == pytest.approx(0.008)

    def test_weapon_jam_clear_time(self) -> None:
        """Jammed weapons clear after specified ticks."""
        # Rifle: 3 ticks
        assert WEAPON_JAM_CONFIGS["rifle"].jam_clear_ticks == 3
        # Sten: 5 ticks
        assert WEAPON_JAM_CONFIGS["sten"].jam_clear_ticks == 5
        # MG42: 8 ticks
        assert WEAPON_JAM_CONFIGS["mg42"].jam_clear_ticks == 8
        # PIAT: 6 ticks
        assert WEAPON_JAM_CONFIGS["piat"].jam_clear_ticks == 6

        # Verify jam system clears after correct ticks
        rng = random.Random(42)
        jam_system = WeaponJamSystem(rng=rng)

        unit = _make_unit(unit_id="jam_tester", weapon_id="rifle", ammo=10)

        # Force a jam by setting probability to 1.0
        from pycc2.domain.ai.weapon_jam import JamConfig
        forced_config = {"rifle": JamConfig(weapon_type="rifle", jam_probability=1.0, jam_clear_ticks=3)}
        jam_system = WeaponJamSystem(jam_configs=forced_config, rng=rng)

        jam_system.check_jam_on_fire(unit)
        assert unit.weapon.state == WeaponState.JAMMED
        assert jam_system.get_jam_clear_remaining(unit.id) == 3

        # Tick 1: remaining 3 → 2
        jam_system.tick(unit)
        assert unit.weapon.state == WeaponState.JAMMED
        assert jam_system.get_jam_clear_remaining(unit.id) == 2

        # Tick 2: remaining 2 → 1
        jam_system.tick(unit)
        assert unit.weapon.state == WeaponState.JAMMED
        assert jam_system.get_jam_clear_remaining(unit.id) == 1

        # Tick 3: remaining 1 → 0
        jam_system.tick(unit)
        assert unit.weapon.state == WeaponState.JAMMED
        assert jam_system.get_jam_clear_remaining(unit.id) == 0

        # Tick 4: remaining 0 detected → clear
        jam_system.tick(unit)
        assert unit.weapon.state == WeaponState.READY
        assert jam_system.get_jam_clear_remaining(unit.id) == 0

    def test_captured_weapon_jam_penalty(self) -> None:
        """Captured weapons have +1% jam rate and +50% clear time."""
        assert CAPTURED_WEAPON_JAM_PENALTY == pytest.approx(0.01)
        assert CAPTURED_WEAPON_CLEAR_MULTIPLIER == pytest.approx(1.5)

        # Verify captured weapon gets increased clear time
        rng = random.Random(42)
        from pycc2.domain.ai.weapon_jam import JamConfig
        forced_config = {
            "rifle": JamConfig(weapon_type="rifle", jam_probability=1.0, jam_clear_ticks=3),
            "de_mp40": JamConfig(weapon_type="de_mp40", jam_probability=1.0, jam_clear_ticks=4),
        }
        jam_system = WeaponJamSystem(jam_configs=forced_config, rng=rng)

        # Create a unit with a captured weapon (ALLIES unit with "de_" prefix weapon)
        unit = _make_unit(
            unit_id="captured_user",
            faction=Faction.ALLIES,
            weapon_id="de_mp40",
            ammo=10,
        )
        jam_system.check_jam_on_fire(unit)
        assert unit.weapon.state == WeaponState.JAMMED
        # de_mp40 base clear = 4, captured multiplier = 1.5 → int(4 * 1.5) = 6
        assert jam_system.get_jam_clear_remaining(unit.id) == int(4 * 1.5)


# ---------------------------------------------------------------------------
# SurrenderSystem tests
# ---------------------------------------------------------------------------

class TestSurrender:
    def test_surrender_conditions(self) -> None:
        """SurrenderSystem checks ammo < 5%, morale < 15, isolated, enemy nearby."""
        # Unit meeting ALL conditions
        unit = _make_unit(
            unit_id="surrender_candidate",
            faction=Faction.ALLIES,
            ammo=4,
            max_ammo=100,
            morale=10,
            x=5,
            y=5,
        )

        # Enemy nearby (within 5 tiles)
        enemy = _make_unit(
            unit_id="nearby_enemy",
            faction=Faction.AXIS,
            x=7,
            y=5,
        )

        # No friendlies within 8 tiles
        all_units = [unit, enemy]

        assert SurrenderSystem._meets_conditions(unit, all_units) is True

    def test_surrender_conditions_not_met_with_friendlies(self) -> None:
        """Should NOT surrender if friendlies are nearby."""
        unit = _make_unit(
            unit_id="not_isolated",
            faction=Faction.ALLIES,
            ammo=4,
            max_ammo=100,
            morale=10,
            x=5,
            y=5,
        )
        friendly = _make_unit(
            unit_id="nearby_friendly",
            faction=Faction.ALLIES,
            x=6,
            y=5,
        )
        enemy = _make_unit(
            unit_id="nearby_enemy",
            faction=Faction.AXIS,
            x=7,
            y=5,
        )
        all_units = [unit, friendly, enemy]
        assert SurrenderSystem._meets_conditions(unit, all_units) is False

    def test_surrender_drops_equipment(self) -> None:
        """Surrendered unit drops weapons/ammo as FallenUnitCache."""
        rng = random.Random(42)
        system = SurrenderSystem(rng=rng)

        unit = _make_unit(
            unit_id="surrenderer",
            faction=Faction.ALLIES,
            ammo=4,
            max_ammo=100,
            weapon_id="rifle",
            morale=10,
            x=5,
            y=5,
        )
        enemy = _make_unit(
            unit_id="enemy_nearby",
            faction=Faction.AXIS,
            x=7,
            y=5,
        )
        all_units = [unit, enemy]

        # Force surrender by setting probability to 1.0
        system._rng = random.Random()
        system._rng.random = lambda: 0.0  # Always trigger

        result = system.evaluate_tick(unit, all_units, current_tick=100)
        assert result is True
        assert unit.state_machine.current == UnitState.SURRENDERED

        # Check fallen cache was created
        assert len(system.fallen_caches) == 1
        cache = system.fallen_caches[0]
        assert cache.unit_id == "surrenderer"
        assert cache.weapon_id == "rifle"
        assert cache.ammo_count == 4


# ---------------------------------------------------------------------------
# SquadDegradation tests
# ---------------------------------------------------------------------------

class TestSquadDegradation:
    def test_squad_degradation_on_leader_killed(self) -> None:
        """SquadDegradationManager degrades squad when leader dies."""
        manager = SquadDegradationManager()
        leader = _make_unit(
            unit_id="leader_1",
            unit_type=UnitType.COMMANDER,
            squad_id="squad_alpha",
            x=5,
            y=5,
        )
        member = _make_unit(
            unit_id="member_1",
            squad_id="squad_alpha",
            morale=80,
            x=6,
            y=5,
        )
        manager.register_squad("squad_alpha", ["leader_1", "member_1"])

        _kill_unit(leader)
        manager.on_leader_killed(leader, [leader, member])

        state = manager.get_squad_state("squad_alpha")
        assert state == SquadState.DEGRADED_SEVERE

    def test_squad_degradation_blocks_advanced_tactics(self) -> None:
        """Degraded squads cannot use bounding overwatch/crossfire/flanking."""
        manager = SquadDegradationManager()
        manager.register_squad("squad_beta", ["u1"])

        # COMBAT_READY: all tactics available
        assert manager.is_tactic_available("squad_beta", "BOUNDING_OVERWATCH") is True
        assert manager.is_tactic_available("squad_beta", "CROSSFIRE") is True
        assert manager.is_tactic_available("squad_beta", "FLANKING") is True
        assert manager.is_tactic_available("squad_beta", "FIRE_CONCENTRATION") is True

        # Manually set to DEGRADED_MODERATE
        manager._squad_records["squad_beta"].state = SquadState.DEGRADED_MODERATE
        assert manager.is_tactic_available("squad_beta", "BOUNDING_OVERWATCH") is False
        assert manager.is_tactic_available("squad_beta", "CROSSFIRE") is False
        assert manager.is_tactic_available("squad_beta", "FLANKING") is False
        assert manager.is_tactic_available("squad_beta", "FIRE_CONCENTRATION") is True

        # DEGRADED_SEVERE: also blocks advanced
        manager._squad_records["squad_beta"].state = SquadState.DEGRADED_SEVERE
        assert manager.is_tactic_available("squad_beta", "BOUNDING_OVERWATCH") is False
        assert manager.is_tactic_available("squad_beta", "FIRE_CONCENTRATION") is True


# ---------------------------------------------------------------------------
# NCORally tests
# ---------------------------------------------------------------------------

class TestNCORally:
    def test_nco_rally_restores_morale(self) -> None:
        """NCORallyBehavior restores panicked unit morale to 40."""
        rally = NCORallyBehavior()
        nco = _make_unit(
            unit_id="nco_1",
            unit_type=UnitType.COMMANDER,
            faction=Faction.ALLIES,
            morale=80,
            x=5,
            y=5,
        )
        panicked = _make_unit(
            unit_id="panicked_1",
            faction=Faction.ALLIES,
            morale=5,
            x=5,
            y=6,
        )
        # Force panic state
        panicked.morale.state = MoraleState.BROKEN

        result = rally.rally_unit(nco, panicked)
        assert result is True
        assert panicked.morale.value == RALLY_RESTORE_MORALE
        assert panicked.morale.state == MoraleState.WAVERING

    def test_nco_rally_cooldown(self) -> None:
        """NCO cannot rally again for 60 ticks after rallying."""
        rally = NCORallyBehavior()
        nco = _make_unit(
            unit_id="nco_2",
            unit_type=UnitType.COMMANDER,
            faction=Faction.ALLIES,
            morale=80,
            x=5,
            y=5,
        )
        panicked = _make_unit(
            unit_id="panicked_2",
            faction=Faction.ALLIES,
            morale=5,
            x=5,
            y=6,
        )
        panicked.morale.state = MoraleState.BROKEN

        # First rally succeeds
        assert rally.rally_unit(nco, panicked) is True
        assert rally.get_cooldown("nco_2") == RALLY_COOLDOWN_TICKS

        # Second rally should fail (cooldown)
        panicked2 = _make_unit(
            unit_id="panicked_3",
            faction=Faction.ALLIES,
            morale=5,
            x=5,
            y=6,
        )
        panicked2.morale.state = MoraleState.BROKEN
        assert rally.can_rally(nco) is False

        # Tick through cooldown
        for _ in range(RALLY_COOLDOWN_TICKS):
            rally.tick()
        assert rally.get_cooldown("nco_2") == 0
        assert rally.can_rally(nco) is True


# ---------------------------------------------------------------------------
# Smoke system tests
# ---------------------------------------------------------------------------

class TestSmokeSystem:
    def test_smoke_deployment_properties(self) -> None:
        """SmokeDeployment has correct radius(3), duration(180), drift."""
        smoke = SmokeDeployment(position=(10, 10))
        assert smoke.radius == 3
        assert smoke.duration_ticks == 180
        assert smoke.remaining_ticks == 180
        assert smoke.drift_direction == (0, 0)
        assert smoke.DRIFT_INTERVAL == 60

    def test_smoke_manager_expiry(self) -> None:
        """SmokeManager removes expired smoke deployments."""
        manager = SmokeManager()
        smoke = SmokeDeployment(
            position=(10, 10),
            duration_ticks=5,
            remaining_ticks=5,
        )
        manager.deploy(smoke)
        assert len(manager.active_deployments) == 1

        for _ in range(5):
            manager.tick()
        assert len(manager.active_deployments) == 0

    def test_smoke_blocks_los(self) -> None:
        """SmokeManager.blocks_los() returns True for lines through smoke."""
        manager = SmokeManager()
        smoke = SmokeDeployment(position=(10, 10), radius=3)
        manager.deploy(smoke)

        # Line passing through smoke center
        assert manager.blocks_los((5, 10), (15, 10)) is True

        # Line far from smoke
        assert manager.blocks_los((5, 5), (5, 0)) is False

    def test_smoke_grenade_capability(self) -> None:
        """infantry=2, mortar=3, nebeltrupp=6 smoke grenades."""
        infantry = SmokeGrenadeCapability.for_infantry_squad()
        assert infantry.smoke_count == 2
        assert infantry.max_smoke == 2
        assert infantry.is_mortar_smoke is False

        mortar = SmokeGrenadeCapability.for_mortar_team()
        assert mortar.smoke_count == 3
        assert mortar.max_smoke == 3
        assert mortar.is_mortar_smoke is True

        nebeltrupp = SmokeGrenadeCapability.for_nebeltrupp()
        assert nebeltrupp.smoke_count == 6
        assert nebeltrupp.max_smoke == 6
        assert nebeltrupp.is_mortar_smoke is False
