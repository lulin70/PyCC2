"""Tests for AmbushAI — general infantry ambush tactical behavior."""

from __future__ import annotations

import numpy as np

from pycc2.domain.ai.ambush_ai import AmbushAI
from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.environment import TimeOfDay
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord

# ---------------------------------------------------------------------------
# Helpers
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
    weapon_id: str = "rifle",
) -> Unit:
    return Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id=weapon_id, ammo_remaining=8, max_ammo=8),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
    )


def _make_map(w: int = 40, h: int = 30) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    return GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)


def _make_map_with_woods(
    woods_x: int = 10, woods_y: int = 10, w: int = 40, h: int = 30
) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    grid[woods_y, woods_x] = TerrainType.WOODS
    return GameMap(id="test", name="test_woods", width=w, height=h, tile_grid=grid)


def _make_context(
    friendly: list[Unit] | None = None,
    enemy: list[Unit] | None = None,
    game_map: GameMap | None = None,
    vl_positions: list[tuple[TileCoord, str | None, int]] | None = None,
    tick: int = 1,
    blackboards: dict[str, Blackboard] | None = None,
) -> TacticalContext:
    return TacticalContext(
        friendly_units=friendly or [],
        enemy_units=enemy or [],
        game_map=game_map or _make_map(),
        current_tick=tick,
        vl_positions=vl_positions or [],
        blackboards=blackboards or {},
    )


# ---------------------------------------------------------------------------
# Test: evaluate — high score for infantry in woods
# ---------------------------------------------------------------------------


class TestEvaluateInfantryInWoods:
    def test_evaluate_returns_high_score_for_infantry_in_woods(self):
        ai = AmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        inf = _make_unit("inf1", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=14, y=10
        )
        ctx = _make_context(friendly=[inf], enemy=[enemy], game_map=gm)
        score = ai.evaluate(ctx)
        # Woods concealment (0.50) + enemy within 15 tiles → meaningful score
        assert score > 0.3

    def test_mg_in_building_also_scores(self):
        ai = AmbushAI()
        grid = np.zeros((30, 40), dtype=np.int8)
        grid[10, 10] = TerrainType.BUILDING_ENTERABLE
        gm = GameMap(id="t", name="t", width=40, height=30, tile_grid=grid)
        mg = _make_unit("mg1", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=13, y=10
        )
        ctx = _make_context(friendly=[mg], enemy=[enemy], game_map=gm)
        score = ai.evaluate(ctx)
        assert score > 0.3


# ---------------------------------------------------------------------------
# Test: evaluate — returns zero for tank units (non-infantry)
# ---------------------------------------------------------------------------


class TestEvaluateReturnsZeroForTanks:
    def test_evaluate_returns_zero_for_tank_units(self):
        ai = AmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        # Friendly tank in woods — tanks are not ambush infantry
        tank = _make_unit("tank1", unit_type=UnitType.TANK, x=10, y=10)
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=14, y=10
        )
        ctx = _make_context(friendly=[tank], enemy=[enemy], game_map=gm)
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_returns_zero_for_at_gun_team(self):
        ai = AmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        at_gun = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=14, y=10
        )
        ctx = _make_context(friendly=[at_gun], enemy=[enemy], game_map=gm)
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_returns_zero_when_enemy_too_far(self):
        ai = AmbushAI()
        gm = _make_map_with_woods(woods_x=5, woods_y=5)
        inf = _make_unit("inf1", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=5)
        # Enemy 25 tiles away — beyond the 15-tile approach radius
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=30, y=5
        )
        ctx = _make_context(friendly=[inf], enemy=[enemy], game_map=gm)
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_returns_zero_when_no_concealment(self):
        ai = AmbushAI()
        # Open terrain map — concealment modifier is 0.0 (< 0.4 threshold)
        gm = _make_map()
        inf = _make_unit("inf1", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=14, y=10
        )
        ctx = _make_context(friendly=[inf], enemy=[enemy], game_map=gm)
        assert ai.evaluate(ctx) == 0.0


# ---------------------------------------------------------------------------
# Test: execute — BREAK_AMBUSH when enemy is close
# ---------------------------------------------------------------------------


class TestExecuteBreakAmbush:
    def test_execute_issues_break_ambush_when_enemy_close(self):
        ai = AmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        inf = _make_unit("inf1", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        # Enemy 5 tiles away — within the 8-tile break-ambush radius
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=15, y=10
        )
        ctx = _make_context(friendly=[inf], enemy=[enemy], game_map=gm)
        intents = ai.execute(ctx)
        break_intents = [
            i for i in intents if i.tactic_type == TacticType.BREAK_AMBUSH
        ]
        assert len(break_intents) == 1
        assert break_intents[0].unit_id == "inf1"
        assert break_intents[0].target_unit_id == "e1"
        assert break_intents[0].target_position == enemy.position.tile_coord

    def test_break_ambush_targets_nearest_enemy(self):
        ai = AmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        inf = _make_unit("inf1", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        near = _make_unit(
            "near", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=12, y=10
        )
        far = _make_unit(
            "far", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=7, y=10
        )
        ctx = _make_context(friendly=[inf], enemy=[far, near], game_map=gm)
        intents = ai.execute(ctx)
        break_intents = [
            i for i in intents if i.tactic_type == TacticType.BREAK_AMBUSH
        ]
        assert len(break_intents) == 1
        # "near" at distance 2 is closer than "far" at distance 3
        assert break_intents[0].target_unit_id == "near"


# ---------------------------------------------------------------------------
# Test: execute — SET_AMBUSH when enemy is far
# ---------------------------------------------------------------------------


class TestExecuteSetAmbush:
    def test_execute_issues_set_ambush_when_enemy_far(self):
        ai = AmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        inf = _make_unit("inf1", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        # Enemy 12 tiles away — outside break radius (8) but within approach (15)
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=22, y=10
        )
        ctx = _make_context(friendly=[inf], enemy=[enemy], game_map=gm)
        intents = ai.execute(ctx)
        set_intents = [i for i in intents if i.tactic_type == TacticType.SET_AMBUSH]
        assert len(set_intents) == 1
        assert set_intents[0].unit_id == "inf1"
        assert set_intents[0].target_position == inf.position.tile_coord
        # SET_AMBUSH should hold fire (no target unit)
        assert set_intents[0].target_unit_id is None

    def test_set_ambush_issued_when_no_enemies_visible(self):
        ai = AmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        inf = _make_unit("inf1", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        ctx = _make_context(friendly=[inf], enemy=[], game_map=gm)
        intents = ai.execute(ctx)
        set_intents = [i for i in intents if i.tactic_type == TacticType.SET_AMBUSH]
        assert len(set_intents) == 1


# ---------------------------------------------------------------------------
# Test: execute — priority order (sniper > MG > infantry)
# ---------------------------------------------------------------------------


class TestExecutePriorityOrder:
    def test_sniper_priority_over_mg_and_infantry(self):
        ai = AmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        # Place all three unit types on the same woods tile with the same enemy
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        sniper = _make_unit("sniper", unit_type=UnitType.SNIPER_TEAM, x=10, y=10)
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=15, y=10
        )
        ctx = _make_context(
            friendly=[inf, mg, sniper], enemy=[enemy], game_map=gm
        )
        intents = ai.execute(ctx)
        # All three should produce intents
        unit_ids_in_order = [i.unit_id for i in intents]
        # Sniper should be processed first (highest priority)
        assert unit_ids_in_order[0] == "sniper"
        # MG before infantry
        assert unit_ids_in_order.index("mg") < unit_ids_in_order.index("inf")


# ---------------------------------------------------------------------------
# Test: night time bonus
# ---------------------------------------------------------------------------


class TestNightTimeBonus:
    def test_night_time_bonus(self):
        ai = AmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        inf = _make_unit("inf1", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=14, y=10
        )

        # Day context (no time_of_day set → defaults to DAY)
        ctx_day = _make_context(friendly=[inf], enemy=[enemy], game_map=gm)
        score_day = ai.evaluate(ctx_day)

        # Night context — set time_of_day in blackboard
        bb = Blackboard()
        bb.set("time_of_day", TimeOfDay.NIGHT)
        ctx_night = _make_context(
            friendly=[inf],
            enemy=[enemy],
            game_map=gm,
            blackboards={"inf1": bb},
        )
        score_night = ai.evaluate(ctx_night)

        # Night score should exceed day score by the +0.2 bonus
        assert score_night > score_day
        assert abs((score_night - score_day) - 0.2) < 1e-6

    def test_dawn_also_grants_bonus(self):
        ai = AmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        inf = _make_unit("inf1", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=14, y=10
        )

        bb = Blackboard()
        bb.set("time_of_day", TimeOfDay.DAWN)
        ctx_dawn = _make_context(
            friendly=[inf],
            enemy=[enemy],
            game_map=gm,
            blackboards={"inf1": bb},
        )
        ctx_day = _make_context(friendly=[inf], enemy=[enemy], game_map=gm)
        assert ai.evaluate(ctx_dawn) > ai.evaluate(ctx_day)


# ---------------------------------------------------------------------------
# Test: execute — empty context
# ---------------------------------------------------------------------------


class TestExecuteEmptyContext:
    def test_no_intents_with_no_friendly_units(self):
        ai = AmbushAI()
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=14, y=10
        )
        ctx = _make_context(friendly=[], enemy=[enemy])
        assert ai.execute(ctx) == []

    def test_no_intents_with_only_tank_friendly(self):
        ai = AmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        tank = _make_unit("tank1", unit_type=UnitType.TANK, x=10, y=10)
        enemy = _make_unit(
            "e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD, x=14, y=10
        )
        ctx = _make_context(friendly=[tank], enemy=[enemy], game_map=gm)
        assert ai.execute(ctx) == []
