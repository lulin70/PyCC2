"""Integration tests: Victory flow.

Tests VictoryManager initialization, event subscription,
victory condition evaluation when units are eliminated,
and battle stats recording.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.victory_conditions import BattleStats
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.event_bus import EventBus
from pycc2.services.event_protocol import UnitAttacked
from pycc2.services.victory_manager import VictoryManager


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def victory_manager():
    return VictoryManager()


@pytest.fixture
def ally_unit():
    return Unit(
        id="ally_1",
        name="Ally Unit",
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(3, 3)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def ally_commander():
    return Unit(
        id="ally_cmd",
        name="Ally Commander",
        faction=Faction.ALLIES,
        unit_type=UnitType.COMMANDER,
        health=HealthComponent(hp=80, max_hp=80),
        morale=MoraleComponent(value=90),
        weapon=WeaponComponent(primary_weapon_id="pistol", ammo_remaining=14, max_ammo=14),
        position=PositionComponent(tile_coord=TileCoord(2, 2)),
        vision=VisionComponent(range_tiles=6),
    )


@pytest.fixture
def enemy_unit():
    return Unit(
        id="enemy_1",
        name="Enemy Unit",
        faction=Faction.AXIS,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(5, 5)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture
def enemy_commander():
    return Unit(
        id="enemy_cmd",
        name="Enemy Commander",
        faction=Faction.AXIS,
        unit_type=UnitType.COMMANDER,
        health=HealthComponent(hp=80, max_hp=80),
        morale=MoraleComponent(value=90),
        weapon=WeaponComponent(primary_weapon_id="pistol", ammo_remaining=14, max_ammo=14),
        position=PositionComponent(tile_coord=TileCoord(10, 10)),
        vision=VisionComponent(range_tiles=6),
    )


# ── Tests ─────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestVictoryManagerInitialize:
    def test_initialize_creates_evaluator(self, victory_manager, event_bus):
        """initialize() should create a VictoryConditionEvaluator."""
        victory_manager.initialize(event_bus=event_bus)
        assert victory_manager._victory_evaluator is not None

    def test_initialize_creates_battle_stats(self, victory_manager, event_bus):
        """initialize() should create BattleStats."""
        victory_manager.initialize(event_bus=event_bus)
        assert victory_manager._battle_stats is not None

    def test_initialize_subscribes_to_events(self, victory_manager, event_bus):
        """initialize() should subscribe to UnitAttacked events."""
        victory_manager.initialize(event_bus=event_bus)
        # Verify subscription by checking the event bus has handlers for UnitAttacked
        handlers = event_bus.get_handlers_for(UnitAttacked)
        assert len(handlers) >= 1

    def test_initialize_resets_game_result(self, victory_manager, event_bus):
        """initialize() should reset game result."""
        victory_manager.initialize(event_bus=event_bus)
        assert victory_manager.game_result is None

    def test_initialize_with_combat_director(self, victory_manager, event_bus, ally_unit, enemy_unit):
        """initialize() with combat_director should store the reference."""
        from tests.conftest import FakeCombatDirector

        fake_cd = FakeCombatDirector(units=[ally_unit, enemy_unit])
        victory_manager.initialize(event_bus=event_bus, combat_director=fake_cd)
        assert victory_manager._combat_director is fake_cd


@pytest.mark.integration
class TestVictoryEvaluation:
    def test_evaluate_returns_none_before_minimum_ticks(self, victory_manager, event_bus, ally_unit, enemy_unit):
        """evaluate() should return None before the minimum tick threshold."""
        victory_manager.initialize(event_bus=event_bus)
        units = [ally_unit, enemy_unit]

        # Tick 0 — too early
        result = victory_manager.evaluate(units, tick=0)
        assert result is None

        # Tick 100 — still too early (minimum is 300)
        result = victory_manager.evaluate(units, tick=100)
        assert result is None

    def test_evaluate_all_axis_eliminated(self, victory_manager, event_bus, ally_unit, enemy_unit):
        """When all axis units are dead, evaluate should return ALLIES_VICTORY."""
        victory_manager.initialize(event_bus=event_bus)

        # Kill the enemy unit using take_damage so state is properly updated
        enemy_unit.health.take_damage(enemy_unit.health.hp)
        units = [ally_unit, enemy_unit]

        # Evaluate at tick 300 (first evaluation tick)
        result = victory_manager.evaluate(units, tick=600)
        assert result is not None
        game_result, reason = result
        assert game_result.name == "ALLIES_VICTORY"

    def test_evaluate_all_allies_eliminated(self, victory_manager, event_bus, ally_unit, enemy_unit):
        """When all allied units are dead, evaluate should return AXIS_VICTORY."""
        victory_manager.initialize(event_bus=event_bus)

        # Kill the ally unit using take_damage so state is properly updated
        ally_unit.health.take_damage(ally_unit.health.hp)
        units = [ally_unit, enemy_unit]

        result = victory_manager.evaluate(units, tick=600)
        assert result is not None
        game_result, reason = result
        assert game_result.name == "AXIS_VICTORY"

    def test_evaluate_ongoing_when_both_alive(self, victory_manager, event_bus, ally_unit, enemy_unit):
        """When both sides have alive units, evaluate should return None (ongoing)."""
        victory_manager.initialize(event_bus=event_bus)
        units = [ally_unit, enemy_unit]

        result = victory_manager.evaluate(units, tick=600)
        assert result is None

    def test_evaluate_all_enemies_eliminated(self, victory_manager, event_bus, ally_commander, enemy_commander):
        """When all enemy units are eliminated, allies should win."""
        victory_manager.initialize(event_bus=event_bus)

        # Kill the enemy commander using take_damage
        enemy_commander.health.take_damage(enemy_commander.health.hp)
        units = [ally_commander, enemy_commander]

        result = victory_manager.evaluate(units, tick=600)
        assert result is not None
        game_result, reason = result
        assert game_result.name == "ALLIES_VICTORY"
        assert "destroyed" in reason.lower()

    def test_evaluate_morale_collapse(self, victory_manager, event_bus, ally_unit, enemy_unit):
        """When enemy morale collapses, allies should win."""
        victory_manager.initialize(event_bus=event_bus)

        # Set enemy morale to 0 (below threshold of 10)
        enemy_unit.morale.value = 0
        units = [ally_unit, enemy_unit]

        result = victory_manager.evaluate(units, tick=600)
        assert result is not None
        game_result, reason = result
        assert game_result.name == "ALLIES_VICTORY"

    def test_evaluate_sets_show_post_battle(self, victory_manager, event_bus, ally_unit, enemy_unit):
        """When a result is determined, show_post_battle should be True."""
        victory_manager.initialize(event_bus=event_bus)

        enemy_unit.health.take_damage(enemy_unit.health.hp)
        units = [ally_unit, enemy_unit]

        victory_manager.evaluate(units, tick=600)
        assert victory_manager.show_post_battle is True

    def test_evaluate_not_on_every_tick(self, victory_manager, event_bus, ally_unit, enemy_unit):
        """evaluate() only checks on every 30th tick for performance."""
        victory_manager.initialize(event_bus=event_bus)

        enemy_unit.health.take_damage(enemy_unit.health.hp)
        units = [ally_unit, enemy_unit]

        # Tick 301 is not a multiple of 30, so should not evaluate
        result = victory_manager.evaluate(units, tick=601)
        assert result is None


@pytest.mark.integration
class TestBattleStats:
    def test_battle_stats_initial_values(self):
        """BattleStats should start with zero values."""
        stats = BattleStats()
        assert stats.allies_kills == 0
        assert stats.axis_kills == 0
        assert stats.allies_damage_dealt == 0.0
        assert stats.axis_damage_dealt == 0.0
        assert stats.allies_units_lost == 0
        assert stats.axis_units_lost == 0
        assert stats.shots_fired_allies == 0
        assert stats.shots_fired_axis == 0

    def test_record_kill_allies(self):
        """Recording a kill for allies should increment allies_kills."""
        stats = BattleStats()
        stats.record_kill("allies")
        assert stats.allies_kills == 1
        assert stats.axis_kills == 0

    def test_record_kill_axis(self):
        """Recording a kill for axis should increment axis_kills."""
        stats = BattleStats()
        stats.record_kill("axis")
        assert stats.axis_kills == 1
        assert stats.allies_kills == 0

    def test_record_damage(self):
        """Recording damage should accumulate correctly."""
        stats = BattleStats()
        stats.record_damage("allies", 25.0)
        stats.record_damage("allies", 15.0)
        assert stats.allies_damage_dealt == 40.0

    def test_record_shot(self):
        """Recording shots should track hits and misses."""
        stats = BattleStats()
        stats.record_shot("allies", hit=True)
        stats.record_shot("allies", hit=False)
        stats.record_shot("allies", hit=True)
        assert stats.shots_fired_allies == 3
        assert stats.shots_hit_allies == 2

    def test_accuracy_calculation(self):
        """Accuracy should be calculated correctly."""
        stats = BattleStats()
        stats.record_shot("allies", hit=True)
        stats.record_shot("allies", hit=True)
        stats.record_shot("allies", hit=False)
        assert stats.allies_accuracy == pytest.approx(2.0 / 3.0)

    def test_accuracy_zero_shots(self):
        """Accuracy with zero shots should be 0.0."""
        stats = BattleStats()
        assert stats.allies_accuracy == 0.0
        assert stats.axis_accuracy == 0.0

    def test_record_unit_lost(self):
        """Recording unit lost should increment the correct counter."""
        stats = BattleStats()
        stats.record_unit_lost("allies")
        assert stats.allies_units_lost == 1
        stats.record_unit_lost("axis")
        assert stats.axis_units_lost == 1

    def test_kill_ratio(self):
        """Kill ratio should be allies_kills / axis_kills."""
        stats = BattleStats()
        stats.record_kill("allies")
        stats.record_kill("allies")
        stats.record_kill("axis")
        assert stats.kill_ratio == pytest.approx(2.0)

    def test_kill_ratio_no_axis_kills(self):
        """Kill ratio with no axis kills should return allies_kills or 0."""
        stats = BattleStats()
        stats.record_kill("allies")
        assert stats.kill_ratio == 1.0

    def test_summary_dict(self):
        """summary_dict should contain all expected keys."""
        stats = BattleStats()
        stats.record_kill("allies")
        stats.record_shot("allies", hit=True)
        summary = stats.summary_dict()
        assert "allies_kills" in summary
        assert "axis_kills" in summary
        assert "allies_accuracy" in summary
        assert "axis_accuracy" in summary
        assert "kill_ratio" in summary
        assert "ticks_elapsed" in summary


@pytest.mark.integration
class TestVictoryManagerReset:
    def test_reset_clears_game_result(self, victory_manager, event_bus, ally_unit, enemy_unit):
        """reset() should clear the game result."""
        victory_manager.initialize(event_bus=event_bus)

        enemy_unit.health.take_damage(enemy_unit.health.hp)
        victory_manager.evaluate([ally_unit, enemy_unit], tick=600)
        assert victory_manager.game_result is not None

        victory_manager.reset()
        assert victory_manager.game_result is None

    def test_reset_clears_show_post_battle(self, victory_manager, event_bus, ally_unit, enemy_unit):
        """reset() should clear show_post_battle flag."""
        victory_manager.initialize(event_bus=event_bus)

        enemy_unit.health.take_damage(enemy_unit.health.hp)
        victory_manager.evaluate([ally_unit, enemy_unit], tick=600)
        assert victory_manager.show_post_battle is True

        victory_manager.reset()
        assert victory_manager.show_post_battle is False


@pytest.mark.integration
class TestVictoryManagerWithCombat:
    def test_stats_recorded_on_attack(self, victory_manager, event_bus, ally_unit, enemy_unit):
        """When an attack event is published, battle stats should be recorded."""
        from tests.conftest import FakeCombatDirector

        victory_manager.initialize(event_bus=event_bus)

        # Set up a fake combat director that has units and records stats
        fake_cd = FakeCombatDirector(units=[ally_unit, enemy_unit])
        victory_manager._combat_director = fake_cd

        # Publish an attack event
        event_bus.publish(
            UnitAttacked(
                attacker_id="ally_1",
                target_id="enemy_1",
                is_hit=True,
                damage=25.0,
                kill_shot=False,
            )
        )

        # The combat director's record_stats should have been called
        assert len(fake_cd._record_stats_calls) == 1

    def test_multiple_kills_tracked(self):
        """Multiple kills should be tracked correctly in BattleStats."""
        stats = BattleStats()
        for _ in range(5):
            stats.record_kill("allies")
        for _ in range(3):
            stats.record_kill("axis")
        assert stats.allies_kills == 5
        assert stats.axis_kills == 3
        assert stats.kill_ratio == pytest.approx(5.0 / 3.0)
