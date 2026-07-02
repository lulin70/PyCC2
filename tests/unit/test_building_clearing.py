"""Tests for building_clearing module — BuildingClearingAI and ClearingState.

Covers clearing-phase lifecycle, grenade effects in buildings, surprise
accuracy bonus, defender penalty, approach-position selection, and the
AI evaluate/execute paths for issuing CLEAR_BUILDING intents.
"""

from __future__ import annotations

import numpy as np

from pycc2.domain.ai.building_clearing import (
    GRENADE_BUILDING_DAMAGE,
    MIN_CLEARING_UNITS,
    SURPRISE_ACCURACY_BONUS,
    SURPRISE_DURATION_TICKS,
    BuildingClearingAI,
    ClearingPhase,
    ClearingState,
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

# ---------------------------------------------------------------------------
# Helpers — real components, no mocks
# ---------------------------------------------------------------------------


def _make_unit(
    uid: str = "u1",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    x: int = 10,
    y: int = 10,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 80,
) -> Unit:
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


def _make_map(w: int = 40, h: int = 30) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    return GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)


def _make_map_with_building(
    bx: int = 15,
    by: int = 15,
    w: int = 40,
    h: int = 30,
) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    grid[by, bx] = TerrainType.BUILDING_ENTERABLE
    return GameMap(id="test", name="test_bldg", width=w, height=h, tile_grid=grid)


def _make_context(
    friendly: list[Unit] | None = None,
    enemy: list[Unit] | None = None,
    game_map: GameMap | None = None,
    tick: int = 1,
) -> TacticalContext:
    return TacticalContext(
        friendly_units=friendly or [],
        enemy_units=enemy or [],
        game_map=game_map or _make_map(),
        current_tick=tick,
    )


# ---------------------------------------------------------------------------
# ClearingState dataclass
# ---------------------------------------------------------------------------


class TestClearingState:
    def test_default_state_is_approach_not_complete(self):
        """Verify: fresh ClearingState starts in APPROACH and is not complete."""
        s = ClearingState(building_pos=TileCoord(5, 5))
        assert s.phase == ClearingPhase.APPROACH
        assert s.is_complete is False
        assert s.has_surprise_bonus is False

    def test_is_complete_true_only_when_complete_phase(self):
        """Verify: is_complete is True only when phase == COMPLETE."""
        s = ClearingState(building_pos=TileCoord(5, 5))
        s.phase = ClearingPhase.CLEAR
        assert s.is_complete is False
        s.phase = ClearingPhase.COMPLETE
        assert s.is_complete is True

    def test_has_surprise_bonus_tracks_timer(self):
        """Verify: has_surprise_bonus is True while surprise_timer > 0."""
        s = ClearingState(building_pos=TileCoord(5, 5))
        assert s.has_surprise_bonus is False
        s.surprise_timer = SURPRISE_DURATION_TICKS
        assert s.has_surprise_bonus is True
        s.surprise_timer = 0
        assert s.has_surprise_bonus is False


# ---------------------------------------------------------------------------
# BuildingClearingAI.evaluate
# ---------------------------------------------------------------------------


class TestEvaluate:
    def test_zero_when_no_enemies_in_buildings(self):
        """Verify: evaluate returns 0.0 when no enemies occupy buildings."""
        ai = BuildingClearingAI()
        inf1 = _make_unit("f1", x=10, y=10)
        inf2 = _make_unit("f2", x=11, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)  # open terrain
        ctx = _make_context(friendly=[inf1, inf2], enemy=[enemy])
        assert ai.evaluate(ctx) == 0.0

    def test_zero_when_insufficient_infantry(self):
        """Verify: evaluate returns 0.0 when fewer than MIN_CLEARING_UNITS available."""
        ai = BuildingClearingAI()
        gm = _make_map_with_building(bx=15, by=15)
        inf = _make_unit("f1", x=14, y=15)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=15, y=15)
        ctx = _make_context(friendly=[inf], enemy=[enemy], game_map=gm)
        assert ai.evaluate(ctx) == 0.0

    def test_positive_when_enemies_in_building_and_infantry_available(self):
        """Verify: evaluate returns positive score with building + 2+ infantry."""
        ai = BuildingClearingAI()
        gm = _make_map_with_building(bx=15, by=15)
        inf1 = _make_unit("f1", x=10, y=15)
        inf2 = _make_unit("f2", x=11, y=15)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=15, y=15)
        ctx = _make_context(friendly=[inf1, inf2], enemy=[enemy], game_map=gm)
        score = ai.evaluate(ctx)
        assert 0.0 < score <= 1.0


# ---------------------------------------------------------------------------
# BuildingClearingAI.execute
# ---------------------------------------------------------------------------


class TestExecute:
    def test_issues_clear_building_intents_for_team(self):
        """Verify: execute issues CLEAR_BUILDING intents for a 2-unit team."""
        ai = BuildingClearingAI()
        gm = _make_map_with_building(bx=15, by=15)
        inf1 = _make_unit("f1", x=13, y=15)
        inf2 = _make_unit("f2", x=14, y=15)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=15, y=15)
        ctx = _make_context(friendly=[inf1, inf2], enemy=[enemy], game_map=gm)
        intents = ai.execute(ctx)
        clear_intents = [i for i in intents if i.tactic_type == TacticType.CLEAR_BUILDING]
        assert len(clear_intents) == MIN_CLEARING_UNITS
        for ci in clear_intents:
            assert ci.target_position == TileCoord(15, 15)
            assert ci.target_unit_id == enemy.id
            assert ci.priority == 8

    def test_no_intents_when_no_enemies_in_buildings(self):
        """Verify: execute returns [] when no enemies are in buildings."""
        ai = BuildingClearingAI()
        inf1 = _make_unit("f1", x=10, y=10)
        inf2 = _make_unit("f2", x=11, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        ctx = _make_context(friendly=[inf1, inf2], enemy=[enemy])
        assert ai.execute(ctx) == []

    def test_no_intents_when_insufficient_infantry(self):
        """Verify: execute returns [] when fewer than MIN_CLEARING_UNITS available."""
        ai = BuildingClearingAI()
        gm = _make_map_with_building(bx=15, by=15)
        inf = _make_unit("f1", x=14, y=15)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=15, y=15)
        ctx = _make_context(friendly=[inf], enemy=[enemy], game_map=gm)
        assert ai.execute(ctx) == []

    def test_enemies_adjacent_to_building_also_targeted(self):
        """Verify: enemies on tile adjacent to building count as in-building."""
        ai = BuildingClearingAI()
        gm = _make_map_with_building(bx=15, by=15)
        inf1 = _make_unit("f1", x=13, y=15)
        inf2 = _make_unit("f2", x=14, y=15)
        # Enemy adjacent to building (not on it)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=16, y=15)
        ctx = _make_context(friendly=[inf1, inf2], enemy=[enemy], game_map=gm)
        intents = ai.execute(ctx)
        clear_intents = [i for i in intents if i.tactic_type == TacticType.CLEAR_BUILDING]
        assert len(clear_intents) == MIN_CLEARING_UNITS


# ---------------------------------------------------------------------------
# BuildingClearingAI.find_adjacent_approach_pos
# ---------------------------------------------------------------------------


class TestFindAdjacentApproachPos:
    def test_returns_nearest_passable_adjacent_tile(self):
        """Verify: returns the adjacent passable tile closest to unit.

        Scenario: building at (15,15), unit at (10,10). The adjacent tiles
        and their chebyshev distances from (10,10):
          (14,14)=4, (15,14)=5, (16,14)=6,
          (14,15)=5, (16,15)=6,
          (14,16)=6, (15,16)=6, (16,16)=6.
        (14,14) is the unique closest, so it must be returned.
        """
        gm = _make_map_with_building(bx=15, by=15)
        pos = BuildingClearingAI.find_adjacent_approach_pos(
            building_pos=TileCoord(15, 15),
            unit_pos=TileCoord(10, 10),
            game_map=gm,
        )
        assert pos == TileCoord(14, 14)

    def test_returns_none_when_no_passable_adjacent(self):
        """Verify: returns None when all adjacent tiles are impassable.

        Scenario: surround building with BUILDING_SOLID tiles.
        Expected: no passable adjacent tile, returns None.
        """
        h, w = 5, 5
        grid = np.full((h, w), TerrainType.BUILDING_SOLID, dtype=np.int8)
        grid[2, 2] = TerrainType.BUILDING_ENTERABLE
        gm = GameMap(id="t", name="t", width=w, height=h, tile_grid=grid)
        pos = BuildingClearingAI.find_adjacent_approach_pos(
            building_pos=TileCoord(2, 2),
            unit_pos=TileCoord(0, 0),
            game_map=gm,
        )
        assert pos is None

    def test_skips_out_of_bounds_adjacent(self):
        """Verify: out-of-bounds adjacent tiles are skipped (corner building)."""
        # Building at corner (0,0); only in-bounds adjacents considered
        h, w = 5, 5
        grid = np.zeros((h, w), dtype=np.int8)
        grid[0, 0] = TerrainType.BUILDING_ENTERABLE
        gm = GameMap(id="t", name="t", width=w, height=h, tile_grid=grid)
        pos = BuildingClearingAI.find_adjacent_approach_pos(
            building_pos=TileCoord(0, 0),
            unit_pos=TileCoord(4, 4),
            game_map=gm,
        )
        # Among in-bounds adjacents, the closest to (4,4) is (1,1)
        assert pos == TileCoord(1, 1)


# ---------------------------------------------------------------------------
# BuildingClearingAI.apply_grenade_effects
# ---------------------------------------------------------------------------


class TestApplyGrenadeEffects:
    def test_applies_damage_to_all_occupants(self):
        """Verify: grenade damages every alive occupant of the building."""
        gm = _make_map_with_building(bx=15, by=15)
        u1 = _make_unit("u1", x=15, y=15, hp=100)
        u2 = _make_unit("u2", x=15, y=15, hp=80)
        effects = BuildingClearingAI.apply_grenade_effects(
            building_pos=TileCoord(15, 15),
            game_map=gm,
            units_in_building=[u1, u2],
        )
        assert len(effects) == 2
        assert effects[0]["damage"] == GRENADE_BUILDING_DAMAGE
        assert effects[0]["source"] == "grenade_building"
        assert u1.health.hp == 100 - GRENADE_BUILDING_DAMAGE
        assert u2.health.hp == 80 - GRENADE_BUILDING_DAMAGE

    def test_skips_dead_units(self):
        """Verify: dead occupants are not affected by the grenade."""
        gm = _make_map_with_building(bx=15, by=15)
        alive = _make_unit("alive", x=15, y=15, hp=100)
        dead = _make_unit("dead", x=15, y=15, hp=0)
        effects = BuildingClearingAI.apply_grenade_effects(
            building_pos=TileCoord(15, 15),
            game_map=gm,
            units_in_building=[alive, dead],
        )
        assert len(effects) == 1
        assert effects[0]["unit_id"] == "alive"

    def test_applies_suppression_when_combat_state_present(self):
        """Verify: grenade applies 40 suppression to units with combat_state."""
        gm = _make_map_with_building(bx=15, by=15)
        u = _make_unit("u1", x=15, y=15, hp=100)
        before = u.combat_state.suppression.current_suppression
        BuildingClearingAI.apply_grenade_effects(
            building_pos=TileCoord(15, 15),
            game_map=gm,
            units_in_building=[u],
        )
        after = u.combat_state.suppression.current_suppression
        assert after > before


# ---------------------------------------------------------------------------
# BuildingClearingAI.apply_surprise_bonus / apply_defender_penalty
# ---------------------------------------------------------------------------


class TestApplySurpriseBonus:
    def test_adds_special_bonus_to_attacker(self):
        """Verify: apply_surprise_bonus adds SURPRISE_ACCURACY_BONUS to concealment."""
        attacker = _make_unit("att", x=10, y=10)
        before = attacker.combat_state.concealment.special_bonus
        BuildingClearingAI.apply_surprise_bonus(attacker)
        after = attacker.combat_state.concealment.special_bonus
        assert abs((after - before) - SURPRISE_ACCURACY_BONUS) < 1e-9

    def test_no_error_when_combat_state_none(self):
        """Verify: apply_surprise_bonus is a no-op when combat_state is None."""
        attacker = _make_unit("att", x=10, y=10)
        attacker.combat_state = None
        # Should not raise
        BuildingClearingAI.apply_surprise_bonus(attacker)


class TestApplyDefenderPenalty:
    def test_applies_suppression_to_defender(self):
        """Verify: apply_defender_penalty adds suppression to the defender."""
        defender = _make_unit("def", x=10, y=10)
        before = defender.combat_state.suppression.current_suppression
        BuildingClearingAI.apply_defender_penalty(defender)
        after = defender.combat_state.suppression.current_suppression
        assert after > before

    def test_no_error_when_combat_state_none(self):
        """Verify: apply_defender_penalty is a no-op when combat_state is None."""
        defender = _make_unit("def", x=10, y=10)
        defender.combat_state = None
        # Should not raise
        BuildingClearingAI.apply_defender_penalty(defender)


# ---------------------------------------------------------------------------
# BuildingClearingAI._enemies_in_buildings (indirect via evaluate)
# ---------------------------------------------------------------------------


class TestEnemiesInBuildings:
    def test_enemies_in_building_counted(self):
        """Verify: enemy on BUILDING_ENTERABLE tile is counted."""
        ai = BuildingClearingAI()
        gm = _make_map_with_building(bx=15, by=15)
        inf1 = _make_unit("f1", x=10, y=15)
        inf2 = _make_unit("f2", x=11, y=15)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=15, y=15)
        ctx = _make_context(friendly=[inf1, inf2], enemy=[enemy], game_map=gm)
        enemies = ai._enemies_in_buildings(ctx)
        assert len(enemies) == 1
        assert enemies[0].id == "e1"

    def test_dead_enemies_excluded(self):
        """Verify: dead enemies are not counted as in-building threats."""
        ai = BuildingClearingAI()
        gm = _make_map_with_building(bx=15, by=15)
        inf1 = _make_unit("f1", x=10, y=15)
        inf2 = _make_unit("f2", x=11, y=15)
        dead_enemy = _make_unit("e1", faction=Faction.AXIS, x=15, y=15, hp=0)
        ctx = _make_context(friendly=[inf1, inf2], enemy=[dead_enemy], game_map=gm)
        assert ai._enemies_in_buildings(ctx) == []

    def test_out_of_bounds_enemy_excluded(self):
        """Verify: enemy outside map bounds is not counted."""
        ai = BuildingClearingAI()
        gm = _make_map_with_building(bx=15, by=15)
        inf1 = _make_unit("f1", x=10, y=15)
        inf2 = _make_unit("f2", x=11, y=15)
        # Enemy at negative coord (out of bounds)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=-5, y=-5)
        ctx = _make_context(friendly=[inf1, inf2], enemy=[enemy], game_map=gm)
        assert ai._enemies_in_buildings(ctx) == []


# ---------------------------------------------------------------------------
# BuildingClearingAI._find_clearing_team
# ---------------------------------------------------------------------------


class TestFindClearingTeam:
    def test_returns_nearest_two_unassigned(self):
        """Verify: team is the 2 nearest unassigned infantry sorted by distance."""
        ai = BuildingClearingAI()
        inf1 = _make_unit("near1", x=12, y=15)
        inf2 = _make_unit("near2", x=13, y=15)
        inf3 = _make_unit("far", x=25, y=25)
        ctx = _make_context(friendly=[inf3, inf2, inf1])
        team = ai._find_clearing_team(
            available=[inf3, inf2, inf1],
            building_pos=TileCoord(15, 15),
            assigned=set(),
            context=ctx,
        )
        assert team is not None
        assert len(team) == MIN_CLEARING_UNITS
        assert {u.id for u in team} == {"near1", "near2"}

    def test_returns_none_when_insufficient_unassigned(self):
        """Verify: returns None when only 1 unassigned infantry remains."""
        ai = BuildingClearingAI()
        inf1 = _make_unit("f1", x=12, y=15)
        inf2 = _make_unit("f2", x=13, y=15)
        ctx = _make_context(friendly=[inf1, inf2])
        team = ai._find_clearing_team(
            available=[inf1, inf2],
            building_pos=TileCoord(15, 15),
            assigned={"f1"},  # f1 already assigned
            context=ctx,
        )
        assert team is None
