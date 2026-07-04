"""Tests for EngineerAssaultAI — CC2-authentic fortified position assault.

Covers the engineer assault team AI that uses demo charges, flamethrowers,
and bangalore torpedoes to clear fortified enemy positions (buildings,
bunkers, walls).

Real domain components are used (Unit, GameMap, EventBus, TacticalContext) —
no mocks. Determinism for probabilistic methods is achieved via ``random.seed``.
"""

from __future__ import annotations

import os
import random
import time

import numpy as np

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from pycc2.domain.ai.engineer_assault import (
    BANGALORE_CLEARABLE,
    BANGALORE_LENGTH,
    DEMO_CHARGE_DAMAGE,
    DEMO_CHARGE_PLACE_TICKS,
    DEMO_CHARGE_RADIUS,
    DEMO_CHARGE_RETREAT_DISTANCE,
    FLAMETHROWER_EXPLODE_CHANCE,
    FLAMETHROWER_FIRE_DAMAGE_PER_TICK,
    FLAMETHROWER_FIRE_DURATION,
    FLAMETHROWER_MAX_BURSTS,
    AssaultPhase,
    AssaultState,
    EngineerAssaultAI,
    FireZone,
)
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.infrastructure.events.event_bus import EventBus

# ---------------------------------------------------------------------------
# Helpers — real components, no mocks
# ---------------------------------------------------------------------------


def _make_unit(
    uid: str = "u1",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.AT_GUN_TEAM,
    x: int = 10,
    y: int = 10,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 80,
) -> Unit:
    """Create a real Unit instance with sensible defaults for assault tests."""
    return Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
    )


def _make_map(
    w: int = 20,
    h: int = 20,
    default_terrain: TerrainType = TerrainType.OPEN,
) -> GameMap:
    """Create a GameMap filled with the given default terrain."""
    grid = np.full((h, w), default_terrain.value, dtype=np.int8)
    return GameMap(id="test_map", name="test", width=w, height=h, tile_grid=grid)


def _make_map_with_terrain(
    terrain_map: dict[tuple[int, int], TerrainType],
    w: int = 20,
    h: int = 20,
) -> GameMap:
    """Create a GameMap with specific terrain at given positions; rest is OPEN."""
    grid = np.zeros((h, w), dtype=np.int8)
    for (x, y), terrain in terrain_map.items():
        grid[y, x] = terrain.value
    return GameMap(id="test_map", name="test", width=w, height=h, tile_grid=grid)


def _make_context(
    friendly: list[Unit] | None = None,
    enemy: list[Unit] | None = None,
    game_map: GameMap | None = None,
    tick: int = 1,
) -> TacticalContext:
    """Create a TacticalContext with real units and map."""
    return TacticalContext(
        friendly_units=friendly or [],
        enemy_units=enemy or [],
        game_map=game_map or _make_map(),
        current_tick=tick,
    )


def _kill_unit(unit: Unit) -> None:
    """Force a unit into the DEAD state without going through take_damage."""
    unit.health.hp = 0
    unit.health._update_state()
    unit.die()


# ---------------------------------------------------------------------------
# Module-level invariants
# ---------------------------------------------------------------------------


class TestModuleInvariants:
    def test_assault_phase_has_seven_members(self):
        """Verify: AssaultPhase enum has exactly 7 distinct phases.

        Scenario: Inspect the AssaultPhase enum.
        Expected: APPROACH, PLACE_CHARGE, RETREAT, DETONATE, FLAMETHROWER,
                  BANGALORE, COMPLETE — 7 members total.
        """
        phases = {
            AssaultPhase.APPROACH,
            AssaultPhase.PLACE_CHARGE,
            AssaultPhase.RETREAT,
            AssaultPhase.DETONATE,
            AssaultPhase.FLAMETHROWER,
            AssaultPhase.BANGALORE,
            AssaultPhase.COMPLETE,
        }
        assert len(phases) == 7

    def test_demo_charge_constants_have_expected_values(self):
        """Verify: Demo charge constants match the CC2 design values.

        Scenario: Check DEMO_CHARGE_* module constants.
        Expected: DAMAGE=50, RADIUS=2, PLACE_TICKS=5, RETREAT_DISTANCE=3.
        """
        assert DEMO_CHARGE_DAMAGE == 50
        assert DEMO_CHARGE_RADIUS == 2
        assert DEMO_CHARGE_PLACE_TICKS == 5
        assert DEMO_CHARGE_RETREAT_DISTANCE == 3

    def test_flamethrower_constants_have_expected_values(self):
        """Verify: Flamethrower constants match the CC2 design values.

        Scenario: Check FLAMETHROWER_* module constants.
        Expected: FIRE_DURATION=30, MAX_BURSTS=5, EXPLODE_CHANCE=0.50.
        """
        assert FLAMETHROWER_FIRE_DURATION == 30
        assert FLAMETHROWER_MAX_BURSTS == 5
        assert FLAMETHROWER_EXPLODE_CHANCE == 0.50
        assert FLAMETHROWER_FIRE_DAMAGE_PER_TICK == 5

    def test_bangalore_clearable_contains_only_hedge(self):
        """Verify: BANGALORE_CLEARABLE contains only TerrainType.HEDGE.

        Scenario: Inspect BANGALORE_CLEARABLE set.
        Expected: Contains HEDGE only.
        Note: The docstring says "Clears hedges and wire" but the code only
              includes HEDGE. WIRE is absent — documented as observed behavior.
        """
        assert {TerrainType.HEDGE} == BANGALORE_CLEARABLE

    def test_bangalore_length_is_five(self):
        """Verify: BANGALORE_LENGTH is 5 tiles.

        Scenario: Check BANGALORE_LENGTH constant.
        Expected: 5.
        """
        assert BANGALORE_LENGTH == 5


# ---------------------------------------------------------------------------
# AssaultState dataclass
# ---------------------------------------------------------------------------


class TestAssaultState:
    def test_default_phase_is_approach(self):
        """Verify: AssaultState defaults to APPROACH phase.

        Scenario: Create an AssaultState with only required fields.
        Expected: phase == AssaultPhase.APPROACH, charge_progress == 0.
        """
        state = AssaultState(
            engineer_id="eng1",
            target_position=TileCoord(5, 5),
        )
        assert state.phase == AssaultPhase.APPROACH
        assert state.charge_progress == 0
        assert state.flamethrower_bursts_used == 0
        assert state.bangalore_direction is None

    def test_has_flamethrower_fuel_true_when_below_max(self):
        """Verify: has_flamethrower_fuel is True when bursts_used < MAX_BURSTS.

        Scenario: AssaultState with flamethrower_bursts_used=0.
        Expected: has_flamethrower_fuel is True.
        """
        state = AssaultState(
            engineer_id="eng1",
            target_position=TileCoord(5, 5),
            flamethrower_bursts_used=0,
        )
        assert state.has_flamethrower_fuel is True

    def test_has_flamethrower_fuel_false_at_max(self):
        """Verify: has_flamethrower_fuel is False when bursts_used >= MAX_BURSTS.

        Scenario: AssaultState with flamethrower_bursts_used=FLAMETHROWER_MAX_BURSTS.
        Expected: has_flamethrower_fuel is False.
        """
        state = AssaultState(
            engineer_id="eng1",
            target_position=TileCoord(5, 5),
            flamethrower_bursts_used=FLAMETHROWER_MAX_BURSTS,
        )
        assert state.has_flamethrower_fuel is False

    def test_has_flamethrower_fuel_boundary_one_below_max(self):
        """Verify: has_flamethrower_fuel is True at MAX_BURSTS - 1 (boundary).

        Scenario: flamethrower_bursts_used = FLAMETHROWER_MAX_BURSTS - 1.
        Expected: True (still has one burst left).
        """
        state = AssaultState(
            engineer_id="eng1",
            target_position=TileCoord(5, 5),
            flamethrower_bursts_used=FLAMETHROWER_MAX_BURSTS - 1,
        )
        assert state.has_flamethrower_fuel is True


# ---------------------------------------------------------------------------
# FireZone dataclass
# ---------------------------------------------------------------------------


class TestFireZone:
    def test_default_damage_per_tick_matches_constant(self):
        """Verify: FireZone defaults damage_per_tick to FLAMETHROWER_FIRE_DAMAGE_PER_TICK.

        Scenario: Create a FireZone with only position and remaining_ticks.
        Expected: damage_per_tick == 5 (FLAMETHROWER_FIRE_DAMAGE_PER_TICK).
        """
        fz = FireZone(position=TileCoord(5, 5), remaining_ticks=30)
        assert fz.damage_per_tick == FLAMETHROWER_FIRE_DAMAGE_PER_TICK
        assert fz.remaining_ticks == 30

    def test_custom_damage_per_tick(self):
        """Verify: FireZone accepts a custom damage_per_tick value.

        Scenario: Create a FireZone with damage_per_tick=10.
        Expected: damage_per_tick == 10.
        """
        fz = FireZone(position=TileCoord(3, 3), remaining_ticks=10, damage_per_tick=10)
        assert fz.damage_per_tick == 10


# ---------------------------------------------------------------------------
# EngineerAssaultAI — construction and properties
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_fresh_ai_has_no_active_assaults(self):
        """Verify: A fresh EngineerAssaultAI has no active assaults.

        Scenario: Construct EngineerAssaultAI.
        Expected: active_assaults is empty, fire_zones is empty.
        """
        ai = EngineerAssaultAI()
        assert ai.active_assaults == []
        assert ai.fire_zones == []

    def test_active_assaults_returns_copy(self):
        """Verify: active_assaults returns a copy, not the internal list.

        Scenario: Get active_assaults, mutate the returned list.
        Expected: Internal state is not affected.
        """
        ai = EngineerAssaultAI()
        assaults = ai.active_assaults
        assaults.append("fake")
        assert ai.active_assaults == []

    def test_fire_zones_returns_copy(self):
        """Verify: fire_zones returns a copy, not the internal list.

        Scenario: Get fire_zones, mutate the returned list.
        Expected: Internal state is not affected.
        """
        ai = EngineerAssaultAI()
        zones = ai.fire_zones
        zones.append("fake")
        assert ai.fire_zones == []


# ---------------------------------------------------------------------------
# EngineerAssaultAI — evaluate
# ---------------------------------------------------------------------------


class TestEvaluate:
    def test_evaluate_zero_when_no_engineers(self):
        """Verify: evaluate returns 0.0 when no engineer-capable units exist.

        Scenario: Friendly units contain only INFANTRY_SQUAD (not in _ENGINEER_TYPES).
        Expected: Returns 0.0.
        """
        ai = EngineerAssaultAI()
        friendly = [_make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD)]
        enemy = [_make_unit("enemy", faction=Faction.AXIS, x=5, y=5)]
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})
        ctx = _make_context(friendly=friendly, enemy=enemy, game_map=game_map)
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_zero_when_no_fortified_enemies(self):
        """Verify: evaluate returns 0.0 when engineers exist but no fortified enemies.

        Scenario: Engineer present, enemy on OPEN terrain (not fortified).
        Expected: Returns 0.0.
        """
        ai = EngineerAssaultAI()
        friendly = [_make_unit("eng", unit_type=UnitType.AT_GUN_TEAM)]
        enemy = [_make_unit("enemy", faction=Faction.AXIS, x=5, y=5)]
        game_map = _make_map_with_terrain({(5, 5): TerrainType.OPEN})
        ctx = _make_context(friendly=friendly, enemy=enemy, game_map=game_map)
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_zero_when_no_enemies_at_all(self):
        """Verify: evaluate returns 0.0 when there are no enemy units.

        Scenario: Engineer present, no enemies.
        Expected: Returns 0.0.
        """
        ai = EngineerAssaultAI()
        friendly = [_make_unit("eng", unit_type=UnitType.AT_GUN_TEAM)]
        ctx = _make_context(friendly=friendly, enemy=[])
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_positive_with_engineer_and_fortified_enemy(self):
        """Verify: evaluate returns >0 when an engineer and a fortified enemy exist.

        Scenario: 1 engineer, 1 enemy in BUILDING_SOLID.
        Expected: Score = 0.5*(1/3) + 0.5*1.0 ≈ 0.667.
        """
        ai = EngineerAssaultAI()
        friendly = [_make_unit("eng", unit_type=UnitType.AT_GUN_TEAM)]
        enemy = [_make_unit("enemy", faction=Faction.AXIS, x=5, y=5)]
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})
        ctx = _make_context(friendly=friendly, enemy=enemy, game_map=game_map)
        score = ai.evaluate(ctx)
        assert 0.0 < score <= 1.0
        expected = 0.5 * (1.0 / 3.0) + 0.5 * 1.0
        assert abs(score - expected) < 0.001

    def test_evaluate_score_capped_at_one(self):
        """Verify: evaluate never exceeds 1.0 even with many fortified and engineers.

        Scenario: 5 fortified positions, 5 engineers (none in assault).
        Expected: fort_ratio capped at 1.0, eng_ratio = 1.0, score = 1.0.
        """
        ai = EngineerAssaultAI()
        friendly = [_make_unit(f"eng{i}", unit_type=UnitType.AT_GUN_TEAM) for i in range(5)]
        enemy_positions = [(5, 5), (6, 6), (7, 7), (8, 8), (9, 9)]
        enemy = [
            _make_unit(f"e{i}", faction=Faction.AXIS, x=x, y=y)
            for i, (x, y) in enumerate(enemy_positions)
        ]
        terrain = {pos: TerrainType.BUILDING_SOLID for pos in enemy_positions}
        game_map = _make_map_with_terrain(terrain)
        ctx = _make_context(friendly=friendly, enemy=enemy, game_map=game_map)
        assert ai.evaluate(ctx) == 1.0

    def test_evaluate_lower_score_when_engineer_busy(self):
        """Verify: evaluate score decreases when an engineer is already in an assault.

        Scenario: 2 engineers, 3 fortified. One engineer is in an active assault.
        Expected: eng_ratio = 1/2 = 0.5, score = 0.5*1.0 + 0.5*0.5 = 0.75
                  (lower than 1.0 when both are available).
        """
        ai = EngineerAssaultAI()
        eng1 = _make_unit("eng1", unit_type=UnitType.AT_GUN_TEAM)
        eng2 = _make_unit("eng2", unit_type=UnitType.AT_GUN_TEAM)
        enemy = [
            _make_unit("e0", faction=Faction.AXIS, x=5, y=5),
            _make_unit("e1", faction=Faction.AXIS, x=6, y=6),
            _make_unit("e2", faction=Faction.AXIS, x=7, y=7),
        ]
        terrain = {
            (5, 5): TerrainType.BUILDING_SOLID,
            (6, 6): TerrainType.BUILDING_SOLID,
            (7, 7): TerrainType.BUILDING_SOLID,
        }
        game_map = _make_map_with_terrain(terrain)
        ctx = _make_context(friendly=[eng1, eng2], enemy=enemy, game_map=game_map)

        score_free = ai.evaluate(ctx)
        assert score_free == 1.0

        # Put eng1 in an assault
        ai._assaults["eng1"] = AssaultState(engineer_id="eng1", target_position=TileCoord(5, 5))
        score_busy = ai.evaluate(ctx)
        expected = 0.5 * 1.0 + 0.5 * 0.5
        assert abs(score_busy - expected) < 0.001

    def test_evaluate_ignores_dead_engineers(self):
        """Verify: evaluate ignores dead engineer units.

        Scenario: 2 engineers, one dead. 1 fortified enemy.
        Expected: Only the living engineer counts. eng_ratio = 1/1 = 1.0.
        """
        ai = EngineerAssaultAI()
        eng_alive = _make_unit("eng1", unit_type=UnitType.AT_GUN_TEAM)
        eng_dead = _make_unit("eng2", unit_type=UnitType.AT_GUN_TEAM)
        _kill_unit(eng_dead)
        enemy = [_make_unit("e0", faction=Faction.AXIS, x=5, y=5)]
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})
        ctx = _make_context(friendly=[eng_alive, eng_dead], enemy=enemy, game_map=game_map)
        score = ai.evaluate(ctx)
        expected = 0.5 * (1.0 / 3.0) + 0.5 * 1.0
        assert abs(score - expected) < 0.001


# ---------------------------------------------------------------------------
# EngineerAssaultAI — execute (start new assaults)
# ---------------------------------------------------------------------------


class TestExecuteStartNew:
    def test_execute_returns_empty_when_no_engineers(self):
        """Verify: execute returns [] when no engineers are available.

        Scenario: No AT_GUN_TEAM units in friendly list.
        Expected: Empty intent list.
        """
        ai = EngineerAssaultAI()
        friendly = [_make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD)]
        enemy = [_make_unit("e", faction=Faction.AXIS, x=5, y=5)]
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})
        ctx = _make_context(friendly=friendly, enemy=enemy, game_map=game_map)
        assert ai.execute(ctx) == []

    def test_execute_returns_empty_when_no_fortified_enemies(self):
        """Verify: execute returns [] when no fortified enemy positions exist.

        Scenario: Engineer present, enemy on OPEN terrain.
        Expected: Empty intent list.
        """
        ai = EngineerAssaultAI()
        friendly = [_make_unit("eng", unit_type=UnitType.AT_GUN_TEAM)]
        enemy = [_make_unit("e", faction=Faction.AXIS, x=5, y=5)]
        game_map = _make_map_with_terrain({(5, 5): TerrainType.OPEN})
        ctx = _make_context(friendly=friendly, enemy=enemy, game_map=game_map)
        assert ai.execute(ctx) == []

    def test_execute_starts_new_assault_with_assault_fortified_intent(self):
        """Verify: execute starts a new assault and returns an ASSAULT_FORTIFIED intent.

        Scenario: 1 engineer, 1 fortified enemy at (5,5).
        Expected: 1 intent with tactic_type=ASSAULT_FORTIFIED, priority=7,
                  target_position=(5,5). Assault state is created.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        enemy = [_make_unit("e", faction=Faction.AXIS, x=5, y=5)]
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})
        ctx = _make_context(friendly=[eng], enemy=enemy, game_map=game_map)

        intents = ai.execute(ctx)

        assert len(intents) == 1
        assert intents[0].tactic_type == TacticType.ASSAULT_FORTIFIED
        assert intents[0].priority == 7
        assert intents[0].target_position == TileCoord(5, 5)
        assert intents[0].unit_id == "eng"
        assert len(ai.active_assaults) == 1

    def test_execute_targets_nearest_fortified_position(self):
        """Verify: execute assigns the nearest fortified position to each engineer.

        Scenario: Engineer at (10,10). Fortified enemies at (5,5) and (12,11).
        Expected: Target is (12,11) — nearest by chebyshev distance.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        enemy_far = [_make_unit("far", faction=Faction.AXIS, x=5, y=5)]
        enemy_near = [_make_unit("near", faction=Faction.AXIS, x=12, y=11)]
        game_map = _make_map_with_terrain(
            {(5, 5): TerrainType.BUILDING_SOLID, (12, 11): TerrainType.WALL}
        )
        ctx = _make_context(friendly=[eng], enemy=enemy_far + enemy_near, game_map=game_map)

        intents = ai.execute(ctx)

        assert len(intents) == 1
        assert intents[0].target_position == TileCoord(12, 11)

    def test_execute_does_not_start_duplicate_assault(self):
        """Verify: execute does not start a second assault for an already-assigned engineer.

        Scenario: Engineer already has an active assault. Call execute again.
        Expected: No new assault intent for that engineer (only the continuing one).
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        enemy = [_make_unit("e", faction=Faction.AXIS, x=5, y=5)]
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})
        ctx = _make_context(friendly=[eng], enemy=enemy, game_map=game_map)

        # First call starts the assault
        ai.execute(ctx)
        assert len(ai.active_assaults) == 1

        # Second call should not create a duplicate
        ai.execute(ctx)
        assert len(ai.active_assaults) == 1

    def test_execute_removes_assault_for_dead_engineer(self):
        """Verify: execute removes an assault when the engineer is dead.

        Scenario: Engineer has an active assault, then dies. Call execute.
        Expected: Assault is removed from _assaults because the cleanup loop
        runs before the early-return guard, so dead engineers' assaults are
        purged even when no new assaults can be started.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        enemy = [_make_unit("e", faction=Faction.AXIS, x=5, y=5)]
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})
        ctx = _make_context(friendly=[eng], enemy=enemy, game_map=game_map)

        ai.execute(ctx)
        assert len(ai.active_assaults) == 1

        _kill_unit(eng)
        intents = ai.execute(ctx)
        # Cleanup loop removes the dead engineer's assault before early return
        assert len(ai.active_assaults) == 0
        # No intents returned because no engineers or fortified enemies remain
        assert intents == []

    def test_execute_removes_assault_when_engineer_not_found(self):
        """Verify: execute removes assault when engineer missing from friendly list.

        Scenario: Engineer has an assault, then is removed from friendly_units.
        Expected: Assault is removed from _assaults because the cleanup loop
        runs before the early-return guard, treating missing engineers the
        same as dead ones.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        enemy = [_make_unit("e", faction=Faction.AXIS, x=5, y=5)]
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})
        ctx = _make_context(friendly=[eng], enemy=enemy, game_map=game_map)

        ai.execute(ctx)
        assert len(ai.active_assaults) == 1

        # Remove engineer from friendly list
        ctx_no_eng = _make_context(friendly=[], enemy=enemy, game_map=game_map)
        intents = ai.execute(ctx_no_eng)
        # Cleanup loop removes the missing engineer's assault before early return
        assert len(ai.active_assaults) == 0
        # No intents returned because no engineers or fortified enemies remain
        assert intents == []

    def test_execute_assigns_multiple_engineers_to_different_targets(self):
        """Verify: execute assigns multiple engineers to different fortified positions.

        Scenario: 2 engineers at different positions, 2 fortified enemies.
        Expected: 2 intents, each targeting the nearest fortified position.
        """
        ai = EngineerAssaultAI()
        eng1 = _make_unit("eng1", unit_type=UnitType.AT_GUN_TEAM, x=5, y=10)
        eng2 = _make_unit("eng2", unit_type=UnitType.AT_GUN_TEAM, x=15, y=10)
        enemy1 = [_make_unit("e1", faction=Faction.AXIS, x=3, y=10)]
        enemy2 = [_make_unit("e2", faction=Faction.AXIS, x=17, y=10)]
        game_map = _make_map_with_terrain(
            {(3, 10): TerrainType.BUILDING_SOLID, (17, 10): TerrainType.BUILDING_SOLID}
        )
        ctx = _make_context(friendly=[eng1, eng2], enemy=enemy1 + enemy2, game_map=game_map)

        intents = ai.execute(ctx)

        assert len(intents) == 2
        targets = {i.target_position for i in intents}
        assert TileCoord(3, 10) in targets
        assert TileCoord(17, 10) in targets


# ---------------------------------------------------------------------------
# EngineerAssaultAI — _advance_assault phase transitions
# ---------------------------------------------------------------------------


class TestAdvanceAssaultApproach:
    def test_approach_far_returns_move_to_intent(self):
        """Verify: APPROACH phase with dist > 1 returns a MOVE_TO intent.

        Scenario: Engineer at (10,10), target at (5,5), dist=5 > 1.
        Expected: MOVE_TO intent, phase stays APPROACH.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=10, y=10)
        target = TileCoord(5, 5)
        state = AssaultState(engineer_id="eng", target_position=target, phase=AssaultPhase.APPROACH)
        ai._assaults["eng"] = state
        game_map = _make_map()
        ctx = _make_context(friendly=[eng], game_map=game_map)

        intent = ai._advance_assault(state, eng, ctx)

        assert intent is not None
        assert intent.tactic_type == TacticType.MOVE_TO
        assert intent.target_position == target
        assert state.phase == AssaultPhase.APPROACH

    def test_approach_adjacent_transitions_to_place_charge(self):
        """Verify: APPROACH phase with dist <= 1 transitions to PLACE_CHARGE.

        Scenario: Engineer at (5,6), target at (5,5), dist=1.
        Expected: ASSAULT_FORTIFIED intent, phase -> PLACE_CHARGE.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=5, y=6)
        target = TileCoord(5, 5)
        state = AssaultState(engineer_id="eng", target_position=target, phase=AssaultPhase.APPROACH)
        ai._assaults["eng"] = state
        ctx = _make_context(friendly=[eng])

        intent = ai._advance_assault(state, eng, ctx)

        assert intent is not None
        assert intent.tactic_type == TacticType.ASSAULT_FORTIFIED
        assert intent.priority == 8
        assert state.phase == AssaultPhase.PLACE_CHARGE

    def test_approach_at_same_position_transitions_to_place_charge(self):
        """Verify: APPROACH phase with dist=0 transitions to PLACE_CHARGE (boundary).

        Scenario: Engineer at (5,5) — same as target, dist=0 <= 1.
        Expected: Phase transitions to PLACE_CHARGE.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=5, y=5)
        target = TileCoord(5, 5)
        state = AssaultState(engineer_id="eng", target_position=target, phase=AssaultPhase.APPROACH)
        ai._assaults["eng"] = state
        ctx = _make_context(friendly=[eng])

        intent = ai._advance_assault(state, eng, ctx)

        assert intent is not None
        assert state.phase == AssaultPhase.PLACE_CHARGE


class TestAdvanceAssaultPlaceCharge:
    def test_place_charge_returns_hold_position(self):
        """Verify: PLACE_CHARGE phase returns HOLD_POSITION and increments progress.

        Scenario: charge_progress=0, PLACE_CHARGE phase.
        Expected: HOLD_POSITION intent, charge_progress=1.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=5, y=5)
        target = TileCoord(5, 5)
        state = AssaultState(
            engineer_id="eng",
            target_position=target,
            phase=AssaultPhase.PLACE_CHARGE,
            charge_progress=0,
        )
        ai._assaults["eng"] = state
        ctx = _make_context(friendly=[eng])

        intent = ai._advance_assault(state, eng, ctx)

        assert intent is not None
        assert intent.tactic_type == TacticType.HOLD_POSITION
        assert intent.priority == 8
        assert state.charge_progress == 1
        assert state.phase == AssaultPhase.PLACE_CHARGE

    def test_place_charge_transitions_to_retreat_after_five_ticks(self):
        """Verify: PLACE_CHARGE transitions to RETREAT after DEMO_CHARGE_PLACE_TICKS increments.

        Scenario: charge_progress=4 (one tick away from 5). Call _advance_assault.
        Expected: charge_progress=5, phase -> RETREAT.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=5, y=5)
        target = TileCoord(5, 5)
        state = AssaultState(
            engineer_id="eng",
            target_position=target,
            phase=AssaultPhase.PLACE_CHARGE,
            charge_progress=DEMO_CHARGE_PLACE_TICKS - 1,
        )
        ai._assaults["eng"] = state
        ctx = _make_context(friendly=[eng])

        intent = ai._advance_assault(state, eng, ctx)

        assert intent is not None
        assert state.charge_progress == DEMO_CHARGE_PLACE_TICKS
        assert state.phase == AssaultPhase.RETREAT


class TestAdvanceAssaultRetreat:
    def test_retreat_close_returns_move_to_retreat_position(self):
        """Verify: RETREAT phase with dist < 3 returns MOVE_TO to a retreat position.

        Scenario: Engineer at (5,6), target at (5,5), dist=1 < 3.
        Expected: MOVE_TO intent targeting a position further from target.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=5, y=6)
        target = TileCoord(5, 5)
        state = AssaultState(
            engineer_id="eng",
            target_position=target,
            phase=AssaultPhase.RETREAT,
        )
        ai._assaults["eng"] = state
        ctx = _make_context(friendly=[eng])

        intent = ai._advance_assault(state, eng, ctx)

        assert intent is not None
        assert intent.tactic_type == TacticType.MOVE_TO
        assert intent.priority == 9
        assert state.phase == AssaultPhase.RETREAT

    def test_retreat_far_enough_transitions_to_detonate(self):
        """Verify: RETREAT phase with dist >= 3 transitions to DETONATE.

        Scenario: Engineer at (5,8), target at (5,5), dist=3 >= RETREAT_DISTANCE.
        Expected: ASSAULT_FORTIFIED intent, phase -> DETONATE.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=5, y=8)
        target = TileCoord(5, 5)
        state = AssaultState(
            engineer_id="eng",
            target_position=target,
            phase=AssaultPhase.RETREAT,
        )
        ai._assaults["eng"] = state
        ctx = _make_context(friendly=[eng])

        intent = ai._advance_assault(state, eng, ctx)

        assert intent is not None
        assert intent.tactic_type == TacticType.ASSAULT_FORTIFIED
        assert intent.priority == 9
        assert state.phase == AssaultPhase.DETONATE


class TestAdvanceAssaultDetonate:
    def test_detonate_applies_demo_charge_and_damages_enemies(self):
        """Verify: DETONATE phase applies demo charge and damages nearby enemies.

        Scenario: Engineer at (5,8), target at (5,5). Enemy at (5,5) in BUILDING_SOLID.
        Expected: BUILDING_SOLID -> OPEN at target, enemy takes DEMO_CHARGE_DAMAGE,
                  phase -> COMPLETE, assault removed, HOLD_POSITION intent returned.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=5, y=8)
        target = TileCoord(5, 5)
        enemy = _make_unit("enemy", faction=Faction.AXIS, x=5, y=5, hp=100)
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})
        state = AssaultState(
            engineer_id="eng",
            target_position=target,
            phase=AssaultPhase.DETONATE,
        )
        ai._assaults["eng"] = state
        ctx = _make_context(friendly=[eng], enemy=[enemy], game_map=game_map)

        enemy_hp_before = enemy.health.hp
        intent = ai._advance_assault(state, eng, ctx)

        assert intent is not None
        assert intent.tactic_type == TacticType.HOLD_POSITION
        assert intent.priority == 5
        assert state.phase == AssaultPhase.COMPLETE
        assert "eng" not in ai._assaults
        assert game_map.get_terrain(target) == TerrainType.OPEN
        assert enemy.health.hp == enemy_hp_before - DEMO_CHARGE_DAMAGE

    def test_detonate_damages_enemies_within_radius(self):
        """Verify: DETONATE damages all enemies within DEMO_CHARGE_RADIUS (2 tiles).

        Scenario: Target at (5,5). Enemies at (5,5) dist=0, (6,6) dist=1, (7,7) dist=2.
        Expected: All three enemies take DEMO_CHARGE_DAMAGE.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=10, y=10)
        target = TileCoord(5, 5)
        e1 = _make_unit("e1", faction=Faction.AXIS, x=5, y=5, hp=100)
        e2 = _make_unit("e2", faction=Faction.AXIS, x=6, y=6, hp=100)
        e3 = _make_unit("e3", faction=Faction.AXIS, x=7, y=7, hp=100)
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})
        state = AssaultState(
            engineer_id="eng",
            target_position=target,
            phase=AssaultPhase.DETONATE,
        )
        ai._assaults["eng"] = state
        ctx = _make_context(friendly=[eng], enemy=[e1, e2, e3], game_map=game_map)

        ai._advance_assault(state, eng, ctx)

        assert e1.health.hp == 100 - DEMO_CHARGE_DAMAGE
        assert e2.health.hp == 100 - DEMO_CHARGE_DAMAGE
        assert e3.health.hp == 100 - DEMO_CHARGE_DAMAGE

    def test_detonate_does_not_damage_enemies_outside_radius(self):
        """Verify: DETONATE does not damage enemies beyond DEMO_CHARGE_RADIUS.

        Scenario: Target at (5,5). Enemy at (8,8) dist=3 > DEMO_CHARGE_RADIUS=2.
        Expected: Enemy HP unchanged.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=10, y=10)
        target = TileCoord(5, 5)
        enemy_far = _make_unit("far", faction=Faction.AXIS, x=8, y=8, hp=100)
        game_map = _make_map()
        state = AssaultState(
            engineer_id="eng",
            target_position=target,
            phase=AssaultPhase.DETONATE,
        )
        ai._assaults["eng"] = state
        ctx = _make_context(friendly=[eng], enemy=[enemy_far], game_map=game_map)

        ai._advance_assault(state, eng, ctx)

        assert enemy_far.health.hp == 100

    def test_detonate_does_not_damage_dead_enemies(self):
        """Verify: DETONATE skips dead enemies when applying damage.

        Scenario: Dead enemy at target position. DETONATE fires.
        Expected: No exception, dead enemy's HP stays at 0.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=10, y=10)
        target = TileCoord(5, 5)
        dead_enemy = _make_unit("dead", faction=Faction.AXIS, x=5, y=5, hp=100)
        _kill_unit(dead_enemy)
        game_map = _make_map()
        state = AssaultState(
            engineer_id="eng",
            target_position=target,
            phase=AssaultPhase.DETONATE,
        )
        ai._assaults["eng"] = state
        ctx = _make_context(friendly=[eng], enemy=[dead_enemy], game_map=game_map)

        ai._advance_assault(state, eng, ctx)
        assert dead_enemy.health.hp == 0


class TestAdvanceAssaultOtherPhases:
    def test_complete_phase_returns_none(self):
        """Verify: _advance_assault returns None for COMPLETE phase.

        Scenario: Assault in COMPLETE phase.
        Expected: Returns None (no further action).
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=5, y=5)
        target = TileCoord(5, 5)
        state = AssaultState(
            engineer_id="eng",
            target_position=target,
            phase=AssaultPhase.COMPLETE,
        )
        ctx = _make_context(friendly=[eng])

        intent = ai._advance_assault(state, eng, ctx)
        assert intent is None

    def test_flamethrower_phase_returns_none(self):
        """Verify: _advance_assault returns None for FLAMETHROWER phase.

        Scenario: Assault in FLAMETHROWER phase (not yet implemented in _advance_assault).
        Expected: Returns None.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=5, y=5)
        target = TileCoord(5, 5)
        state = AssaultState(
            engineer_id="eng",
            target_position=target,
            phase=AssaultPhase.FLAMETHROWER,
        )
        ctx = _make_context(friendly=[eng])

        intent = ai._advance_assault(state, eng, ctx)
        assert intent is None

    def test_bangalore_phase_returns_none(self):
        """Verify: _advance_assault returns None for BANGALORE phase.

        Scenario: Assault in BANGALORE phase (not yet implemented in _advance_assault).
        Expected: Returns None.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=5, y=5)
        target = TileCoord(5, 5)
        state = AssaultState(
            engineer_id="eng",
            target_position=target,
            phase=AssaultPhase.BANGALORE,
        )
        ctx = _make_context(friendly=[eng])

        intent = ai._advance_assault(state, eng, ctx)
        assert intent is None


# ---------------------------------------------------------------------------
# EngineerAssaultAI — tick_fire_zones
# ---------------------------------------------------------------------------


class TestTickFireZones:
    def test_tick_decrements_remaining_ticks(self):
        """Verify: tick_fire_zones decrements remaining_ticks by 1.

        Scenario: Fire zone with remaining_ticks=10. Call tick with no units.
        Expected: remaining_ticks=9, zone not expired.
        """
        ai = EngineerAssaultAI()
        ai.apply_flamethrower(TileCoord(0, 0), TileCoord(5, 5))
        ai.tick_fire_zones([])

        assert len(ai.fire_zones) == 1
        assert ai.fire_zones[0].remaining_ticks == FLAMETHROWER_FIRE_DURATION - 1

    def test_tick_applies_damage_to_unit_at_zone_position(self):
        """Verify: tick_fire_zones applies damage_per_tick to units at the zone position.

        Scenario: Fire zone at (5,5) with damage_per_tick=5. Unit at (5,5) with hp=100.
        Expected: Unit hp = 100 - 5 = 95.
        """
        ai = EngineerAssaultAI()
        ai.apply_flamethrower(TileCoord(0, 0), TileCoord(5, 5))
        unit = _make_unit("u1", x=5, y=5, hp=100)

        ai.tick_fire_zones([unit])

        assert unit.health.hp == 100 - FLAMETHROWER_FIRE_DAMAGE_PER_TICK

    def test_tick_does_not_damage_unit_not_at_zone_position(self):
        """Verify: tick_fire_zones does not damage units not at the zone position.

        Scenario: Fire zone at (5,5). Unit at (6,6).
        Expected: Unit HP unchanged.
        """
        ai = EngineerAssaultAI()
        ai.apply_flamethrower(TileCoord(0, 0), TileCoord(5, 5))
        unit = _make_unit("u1", x=6, y=6, hp=100)

        ai.tick_fire_zones([unit])

        assert unit.health.hp == 100

    def test_tick_does_not_damage_dead_units(self):
        """Verify: tick_fire_zones skips dead units.

        Scenario: Fire zone at (5,5). Dead unit at (5,5).
        Expected: No exception, dead unit HP stays at 0.
        """
        ai = EngineerAssaultAI()
        ai.apply_flamethrower(TileCoord(0, 0), TileCoord(5, 5))
        dead = _make_unit("dead", x=5, y=5, hp=100)
        _kill_unit(dead)

        ai.tick_fire_zones([dead])

        assert dead.health.hp == 0

    def test_tick_removes_expired_zone_and_returns_it(self):
        """Verify: tick_fire_zones removes expired zones and returns them.

        Scenario: Fire zone with remaining_ticks=1. Tick once.
        Expected: Zone expires (remaining_ticks=0), removed from _fire_zones,
                  returned in the expired list.
        """
        ai = EngineerAssaultAI()
        ai.apply_flamethrower(TileCoord(0, 0), TileCoord(5, 5))
        # Manually set remaining_ticks to 1 for fast expiry
        ai._fire_zones[0].remaining_ticks = 1

        expired = ai.tick_fire_zones([])

        assert len(expired) == 1
        assert expired[0].position == TileCoord(5, 5)
        assert len(ai.fire_zones) == 0

    def test_tick_keeps_non_expired_zones(self):
        """Verify: tick_fire_zones does not remove zones that have not expired.

        Scenario: Fire zone with remaining_ticks=5. Tick once.
        Expected: Zone remains in _fire_zones, expired list is empty.
        """
        ai = EngineerAssaultAI()
        ai.apply_flamethrower(TileCoord(0, 0), TileCoord(5, 5))
        ai._fire_zones[0].remaining_ticks = 5

        expired = ai.tick_fire_zones([])

        assert expired == []
        assert len(ai.fire_zones) == 1

    def test_tick_multiple_zones(self):
        """Verify: tick_fire_zones processes multiple fire zones simultaneously.

        Scenario: Two fire zones at (5,5) and (10,10), both with remaining_ticks=5.
        Expected: Both zones decremented, both remain, empty expired list.
        """
        ai = EngineerAssaultAI()
        ai.apply_flamethrower(TileCoord(0, 0), TileCoord(5, 5))
        ai.apply_flamethrower(TileCoord(0, 0), TileCoord(10, 10))

        expired = ai.tick_fire_zones([])

        assert expired == []
        assert len(ai.fire_zones) == 2
        for fz in ai.fire_zones:
            assert fz.remaining_ticks == FLAMETHROWER_FIRE_DURATION - 1

    def test_tick_empty_zones_is_noop(self):
        """Verify: tick_fire_zones with no fire zones returns empty list.

        Scenario: No fire zones. Call tick.
        Expected: Empty expired list, no exception.
        """
        ai = EngineerAssaultAI()
        expired = ai.tick_fire_zones([])
        assert expired == []


# ---------------------------------------------------------------------------
# EngineerAssaultAI — apply_demo_charge
# ---------------------------------------------------------------------------


class TestApplyDemoCharge:
    def test_demo_charge_converts_building_solid_to_open(self):
        """Verify: apply_demo_charge converts BUILDING_SOLID terrain to OPEN.

        Scenario: Map with BUILDING_SOLID at (5,5). Apply charge at (5,5).
        Expected: Terrain at (5,5) becomes OPEN.
        """
        ai = EngineerAssaultAI()
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})

        ai.apply_demo_charge(TileCoord(5, 5), game_map)

        assert game_map.get_terrain(TileCoord(5, 5)) == TerrainType.OPEN

    def test_demo_charge_converts_bridge_to_bridge_destroyed(self):
        """Verify: apply_demo_charge converts BRIDGE terrain to BRIDGE_DESTROYED.

        Scenario: Map with BRIDGE at (5,5). Apply charge at (5,5).
        Expected: Terrain at (5,5) becomes BRIDGE_DESTROYED.
        """
        ai = EngineerAssaultAI()
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BRIDGE})

        ai.apply_demo_charge(TileCoord(5, 5), game_map)

        assert game_map.get_terrain(TileCoord(5, 5)) == TerrainType.BRIDGE_DESTROYED

    def test_demo_charge_publishes_bridge_destroyed_event(self):
        """Verify: apply_demo_charge publishes a 'BridgeDestroyed' named event for bridges.

        Scenario: BRIDGE at (5,5), event_bus provided. A handler captures the event.
        Expected: Handler receives a dict with event_type='BridgeDestroyed' and position.
        """
        ai = EngineerAssaultAI()
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BRIDGE})
        bus = EventBus()
        captured: list[dict] = []
        bus.subscribe_to("BridgeDestroyed", captured.append)

        ai.apply_demo_charge(TileCoord(5, 5), game_map, event_bus=bus)

        assert len(captured) == 1
        assert captured[0]["event_type"] == "BridgeDestroyed"
        assert captured[0]["position"] == (5, 5)

    def test_demo_charge_no_event_when_no_bridge(self):
        """Verify: apply_demo_charge does not publish events when no bridge is destroyed.

        Scenario: BUILDING_SOLID at (5,5), event_bus provided.
        Expected: No events published.
        """
        ai = EngineerAssaultAI()
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})
        bus = EventBus()
        captured: list[dict] = []
        bus.subscribe_to("BridgeDestroyed", captured.append)

        ai.apply_demo_charge(TileCoord(5, 5), game_map, event_bus=bus)

        assert captured == []

    def test_demo_charge_returns_all_affected_tiles(self):
        """Verify: apply_demo_charge returns all tiles within the radius.

        Scenario: Apply charge at (10,10) on an OPEN map. Radius=2.
        Expected: Returns (2*2+1)^2 = 25 tiles.
        """
        ai = EngineerAssaultAI()
        game_map = _make_map(w=20, h=20)

        affected = ai.apply_demo_charge(TileCoord(10, 10), game_map)

        assert len(affected) == (2 * DEMO_CHARGE_RADIUS + 1) ** 2

    def test_demo_charge_skips_out_of_bounds_tiles(self):
        """Verify: apply_demo_charge skips tiles outside map bounds.

        Scenario: Apply charge at (0,0) on a 20x20 map. Radius=2.
        Expected: Only in-bounds tiles are affected (3x3 = 9 tiles, not 25).
        """
        ai = EngineerAssaultAI()
        game_map = _make_map(w=20, h=20)

        affected = ai.apply_demo_charge(TileCoord(0, 0), game_map)

        expected_count = (DEMO_CHARGE_RADIUS + 1) ** 2  # 3x3 = 9
        assert len(affected) == expected_count

    def test_demo_charge_no_event_bus_is_safe(self):
        """Verify: apply_demo_charge works without an event_bus (None default).

        Scenario: BRIDGE at (5,5), no event_bus passed.
        Expected: Bridge destroyed, no exception.
        """
        ai = EngineerAssaultAI()
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BRIDGE})

        ai.apply_demo_charge(TileCoord(5, 5), game_map, event_bus=None)

        assert game_map.get_terrain(TileCoord(5, 5)) == TerrainType.BRIDGE_DESTROYED

    def test_demo_charge_does_not_modify_open_terrain(self):
        """Verify: apply_demo_charge does not change OPEN terrain.

        Scenario: All OPEN terrain. Apply charge at (10,10).
        Expected: Terrain at (10,10) remains OPEN.
        """
        ai = EngineerAssaultAI()
        game_map = _make_map()

        ai.apply_demo_charge(TileCoord(10, 10), game_map)

        assert game_map.get_terrain(TileCoord(10, 10)) == TerrainType.OPEN

    def test_demo_charge_at_map_edge(self):
        """Verify: apply_demo_charge works at the edge of the map (boundary).

        Scenario: Apply charge at (19,19) on a 20x20 map.
        Expected: Only in-bounds tiles are affected, no exception.
        """
        ai = EngineerAssaultAI()
        game_map = _make_map(w=20, h=20)

        affected = ai.apply_demo_charge(TileCoord(19, 19), game_map)

        assert len(affected) == (DEMO_CHARGE_RADIUS + 1) ** 2  # 3x3 = 9


# ---------------------------------------------------------------------------
# EngineerAssaultAI — apply_flamethrower
# ---------------------------------------------------------------------------


class TestApplyFlamethrower:
    def test_flamethrower_creates_fire_zone_at_target(self):
        """Verify: apply_flamethrower creates a FireZone at the target position.

        Scenario: Fire from (0,0) to (5,5).
        Expected: Fire zone at (5,5) with FLAMETHROWER_FIRE_DURATION ticks.
        """
        ai = EngineerAssaultAI()
        fz = ai.apply_flamethrower(TileCoord(0, 0), TileCoord(5, 5))

        assert fz.position == TileCoord(5, 5)
        assert fz.remaining_ticks == FLAMETHROWER_FIRE_DURATION
        assert fz.damage_per_tick == FLAMETHROWER_FIRE_DAMAGE_PER_TICK
        assert len(ai.fire_zones) == 1

    def test_flamethrower_fire_zone_appears_in_fire_zones_property(self):
        """Verify: The created fire zone is visible via the fire_zones property.

        Scenario: Apply flamethrower, then check fire_zones.
        Expected: fire_zones list contains the new zone.
        """
        ai = EngineerAssaultAI()
        ai.apply_flamethrower(TileCoord(0, 0), TileCoord(3, 3))

        zones = ai.fire_zones
        assert len(zones) == 1
        assert zones[0].position == TileCoord(3, 3)

    def test_flamethrower_multiple_shots_accumulate(self):
        """Verify: Multiple flamethrower shots create multiple fire zones.

        Scenario: Fire twice to different targets.
        Expected: 2 fire zones in the list.
        """
        ai = EngineerAssaultAI()
        ai.apply_flamethrower(TileCoord(0, 0), TileCoord(3, 3))
        ai.apply_flamethrower(TileCoord(0, 0), TileCoord(5, 5))

        assert len(ai.fire_zones) == 2


# ---------------------------------------------------------------------------
# EngineerAssaultAI — apply_bangalore
# ---------------------------------------------------------------------------


class TestApplyBangalore:
    def test_bangalore_clears_hedges_in_line(self):
        """Verify: apply_bangalore returns tiles with HEDGE terrain in a 5-tile line.

        Scenario: Map with HEDGE at (5,5), (6,5), (7,5), (8,5), (9,5).
                  Bangalore from (5,5) toward (10,5).
        Expected: Returns all 5 HEDGE tiles.
        Note: apply_bangalore only *detects* clearable tiles; it does not modify terrain.
        """
        ai = EngineerAssaultAI()
        hedges = {(x, 5): TerrainType.HEDGE for x in range(5, 10)}
        game_map = _make_map_with_terrain(hedges)

        cleared = ai.apply_bangalore(TileCoord(5, 5), TileCoord(10, 5), game_map)

        assert len(cleared) == BANGALORE_LENGTH
        for i, tc in enumerate(cleared):
            assert tc == TileCoord(5 + i, 5)

    def test_bangalore_does_not_modify_terrain(self):
        """Verify: apply_bangalore does not actually change terrain (only detects).

        Scenario: HEDGE at (5,5). Bangalore from (5,5) toward (10,5).
        Expected: Terrain at (5,5) remains HEDGE.
        Note: The docstring says "Clears hedges and wire" but the implementation
              only appends clearable tiles to the return list without calling
              modify_terrain(). Documented as observed behavior.
        """
        ai = EngineerAssaultAI()
        game_map = _make_map_with_terrain({(5, 5): TerrainType.HEDGE})

        ai.apply_bangalore(TileCoord(5, 5), TileCoord(10, 5), game_map)

        assert game_map.get_terrain(TileCoord(5, 5)) == TerrainType.HEDGE

    def test_bangalore_returns_empty_for_no_clearable_terrain(self):
        """Verify: apply_bangalore returns empty list when no HEDGE tiles are in the line.

        Scenario: All OPEN terrain. Bangalore from (5,5) toward (10,5).
        Expected: Empty cleared list.
        """
        ai = EngineerAssaultAI()
        game_map = _make_map()

        cleared = ai.apply_bangalore(TileCoord(5, 5), TileCoord(10, 5), game_map)

        assert cleared == []

    def test_bangalore_stops_at_map_boundary(self):
        """Verify: apply_bangalore stops when tiles go out of bounds.

        Scenario: 20x20 map. Bangalore from (18,5) toward (25,5) — goes out of bounds.
        Expected: Only 2 tiles processed (18,5 and 19,5), rest out of bounds.
        """
        ai = EngineerAssaultAI()
        hedges = {(18, 5): TerrainType.HEDGE, (19, 5): TerrainType.HEDGE}
        game_map = _make_map_with_terrain(hedges, w=20, h=20)

        cleared = ai.apply_bangalore(TileCoord(18, 5), TileCoord(25, 5), game_map)

        assert len(cleared) == 2

    def test_bangalore_vertical_direction(self):
        """Verify: apply_bangalore works in the vertical direction.

        Scenario: HEDGE tiles at (5,5), (5,6), (5,7), (5,8), (5,9).
                  Bangalore from (5,5) toward (5,10).
        Expected: Returns all 5 HEDGE tiles vertically.
        """
        ai = EngineerAssaultAI()
        hedges = {(5, y): TerrainType.HEDGE for y in range(5, 10)}
        game_map = _make_map_with_terrain(hedges)

        cleared = ai.apply_bangalore(TileCoord(5, 5), TileCoord(5, 10), game_map)

        assert len(cleared) == BANGALORE_LENGTH
        for i, tc in enumerate(cleared):
            assert tc == TileCoord(5, 5 + i)

    def test_bangalore_same_start_and_direction(self):
        """Verify: apply_bangalore handles start == direction (zero delta) gracefully.

        Scenario: Bangalore from (5,5) toward (5,5) — dx=0, dy=0.
        Expected: Processes tile (5,5) BANGALORE_LENGTH times (5 times).
        Note: With zero delta, length=max(0,0,1)=1, step_x=0, step_y=0.
              The bangalore stays on the same tile for all 5 iterations.
        """
        ai = EngineerAssaultAI()
        game_map = _make_map_with_terrain({(5, 5): TerrainType.HEDGE})

        cleared = ai.apply_bangalore(TileCoord(5, 5), TileCoord(5, 5), game_map)

        # Same tile checked 5 times, all HEDGE → 5 entries
        assert len(cleared) == BANGALORE_LENGTH
        assert all(tc == TileCoord(5, 5) for tc in cleared)


# ---------------------------------------------------------------------------
# EngineerAssaultAI — check_flamethrower_hit
# ---------------------------------------------------------------------------


class TestCheckFlamethrowerHit:
    def test_hit_causes_explosion_with_low_random(self):
        """Verify: check_flamethrower_hit returns True when random < 0.5.

        Scenario: random.seed(1) produces random()=0.134 < 0.5.
        Expected: Returns True (fuel tank explodes).
        """
        random.seed(1)
        ai = EngineerAssaultAI()
        eng = _make_unit("eng")
        assert ai.check_flamethrower_hit(eng) is True

    def test_hit_no_explosion_with_high_random(self):
        """Verify: check_flamethrower_hit returns False when random >= 0.5.

        Scenario: random.seed(0) produces random()=0.844 >= 0.5.
        Expected: Returns False (no explosion).
        """
        random.seed(0)
        ai = EngineerAssaultAI()
        eng = _make_unit("eng")
        assert ai.check_flamethrower_hit(eng) is False

    def test_hit_statistical_distribution(self):
        """Verify: check_flamethrower_hit produces ~50% explosions over many trials.

        Scenario: Run 1000 trials with different seeds.
        Expected: Explosion count is approximately 500 (within +/- 100).
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng")
        explosions = 0
        for seed in range(1000):
            random.seed(seed)
            if ai.check_flamethrower_hit(eng):
                explosions += 1
        assert 400 < explosions < 600


# ---------------------------------------------------------------------------
# EngineerAssaultAI — _find_unit helper
# ---------------------------------------------------------------------------


class TestFindUnit:
    def test_find_unit_returns_matching_unit(self):
        """Verify: _find_unit returns the unit with the given ID.

        Scenario: Search for 'eng' in a list of units.
        Expected: Returns the unit with id='eng'.
        """
        ai = EngineerAssaultAI()
        u1 = _make_unit("u1")
        u2 = _make_unit("eng")
        result = ai._find_unit("eng", [u1, u2])
        assert result is u2

    def test_find_unit_returns_none_when_not_found(self):
        """Verify: _find_unit returns None when the ID is not in the list.

        Scenario: Search for 'missing' in a list of units.
        Expected: Returns None.
        """
        ai = EngineerAssaultAI()
        u1 = _make_unit("u1")
        result = ai._find_unit("missing", [u1])
        assert result is None

    def test_find_unit_returns_none_for_empty_list(self):
        """Verify: _find_unit returns None for an empty unit list.

        Scenario: Search in an empty list.
        Expected: Returns None.
        """
        ai = EngineerAssaultAI()
        result = ai._find_unit("any", [])
        assert result is None


# ---------------------------------------------------------------------------
# Integration — full assault lifecycle
# ---------------------------------------------------------------------------


class TestFullAssaultLifecycle:
    def test_full_assault_from_approach_to_detonate(self):
        """Verify: An assault progresses through all phases from APPROACH to COMPLETE.

        Scenario: Engineer at (10,10), fortified enemy at (5,5) in BUILDING_SOLID.
                  Execute repeatedly, moving the engineer through phases.
        Expected: Phases transition APPROACH -> PLACE_CHARGE -> RETREAT -> DETONATE -> COMPLETE.
                  Building is destroyed, enemy is damaged, assault is removed.
        """
        ai = EngineerAssaultAI()
        eng = _make_unit("eng", x=10, y=10)
        enemy = _make_unit("enemy", faction=Faction.AXIS, x=5, y=5, hp=200)
        game_map = _make_map_with_terrain({(5, 5): TerrainType.BUILDING_SOLID})
        ctx = _make_context(friendly=[eng], enemy=[enemy], game_map=game_map)

        # 1. Start assault (APPROACH phase, dist=5 > 1)
        intents = ai.execute(ctx)
        assert len(intents) == 1
        assert intents[0].tactic_type == TacticType.ASSAULT_FORTIFIED
        state = ai.active_assaults[0]
        assert state.phase == AssaultPhase.APPROACH

        # 2. Move engineer adjacent to target (dist=1)
        eng.position.move_to_tile(TileCoord(5, 6))
        intents = ai.execute(ctx)
        assert state.phase == AssaultPhase.PLACE_CHARGE

        # 3. Place charge (5 ticks)
        for _ in range(DEMO_CHARGE_PLACE_TICKS):
            ai.execute(ctx)
        assert state.phase == AssaultPhase.RETREAT

        # 4. Move engineer to safe distance (dist >= 3)
        eng.position.move_to_tile(TileCoord(5, 8))
        ai.execute(ctx)
        assert state.phase == AssaultPhase.DETONATE

        # 5. Detonate
        intents = ai.execute(ctx)
        assert state.phase == AssaultPhase.COMPLETE
        assert len(ai.active_assaults) == 0
        assert game_map.get_terrain(TileCoord(5, 5)) == TerrainType.OPEN
        assert enemy.health.hp == 200 - DEMO_CHARGE_DAMAGE


# ---------------------------------------------------------------------------
# Performance — timing baselines
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_evaluate_performance_under_load(self):
        """Verify: evaluate completes within a reasonable time for 50 units.

        Scenario: 25 engineers, 25 fortified enemies. Call evaluate 100 times.
        Expected: Total time < 2.0 seconds (relaxed baseline).
        """
        ai = EngineerAssaultAI()
        friendly = [
            _make_unit(f"eng{i}", unit_type=UnitType.AT_GUN_TEAM, x=i, y=0) for i in range(25)
        ]
        enemy = [_make_unit(f"e{i}", faction=Faction.AXIS, x=i, y=15) for i in range(25)]
        terrain = {(i, 15): TerrainType.BUILDING_SOLID for i in range(25)}
        game_map = _make_map_with_terrain(terrain, w=30, h=20)
        ctx = _make_context(friendly=friendly, enemy=enemy, game_map=game_map)

        start = time.perf_counter()
        for _ in range(100):
            ai.evaluate(ctx)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0

    def test_apply_demo_charge_performance(self):
        """Verify: apply_demo_charge completes quickly on a large map.

        Scenario: 100x100 map. Apply demo charge 100 times.
        Expected: Total time < 1.0 seconds.
        """
        ai = EngineerAssaultAI()
        game_map = _make_map(w=100, h=100)

        start = time.perf_counter()
        for i in range(100):
            ai.apply_demo_charge(TileCoord(50, 50), game_map)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0
