"""Tests for ATAmbushAI — anti-tank ambush tactical behavior."""

from __future__ import annotations

import numpy as np

from pycc2.domain.ai.at_ambush_ai import ATAmbushAI
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
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord

# ---------------------------------------------------------------------------
# Helpers
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
    weapon_id: str = "at_gun",
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


def _make_map_with_woods(woods_x: int = 10, woods_y: int = 10, w: int = 40, h: int = 30) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    grid[woods_y, woods_x] = TerrainType.WOODS
    return GameMap(id="test", name="test_woods", width=w, height=h, tile_grid=grid)


def _make_map_with_mixed_terrain(w: int = 40, h: int = 30) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    # Woods along y=10 for ambush positions
    grid[10, 8:15] = TerrainType.WOODS
    # Road along y=15 for tank route
    grid[15, :] = TerrainType.ROAD
    return GameMap(id="test", name="test_mixed", width=w, height=h, tile_grid=grid)


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
# Test: evaluate — no enemy armor
# ---------------------------------------------------------------------------


class TestEvaluateNoEnemyArmor:
    def test_returns_zero_when_no_enemies(self):
        ai = ATAmbushAI()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM)
        ctx = _make_context(friendly=[at_unit], enemy=[])
        assert ai.evaluate(ctx) == 0.0

    def test_returns_zero_when_only_infantry_enemies(self):
        ai = ATAmbushAI()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM)
        enemy_inf = _make_unit("e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD)
        ctx = _make_context(friendly=[at_unit], enemy=[enemy_inf])
        assert ai.evaluate(ctx) == 0.0


# ---------------------------------------------------------------------------
# Test: evaluate — no AT units
# ---------------------------------------------------------------------------


class TestEvaluateNoATUnits:
    def test_returns_zero_when_no_friendly_units(self):
        ai = ATAmbushAI()
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=30, y=10)
        ctx = _make_context(friendly=[], enemy=[tank])
        assert ai.evaluate(ctx) == 0.0

    def test_returns_zero_when_only_infantry_friendlies(self):
        ai = ATAmbushAI()
        inf = _make_unit("inf1", unit_type=UnitType.INFANTRY_SQUAD, weapon_id="rifle")
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=30, y=10)
        ctx = _make_context(friendly=[inf], enemy=[tank])
        assert ai.evaluate(ctx) == 0.0


# ---------------------------------------------------------------------------
# Test: evaluate — high score when tanks are close
# ---------------------------------------------------------------------------


class TestEvaluateProximity:
    def test_high_score_when_tanks_close(self):
        ai = ATAmbushAI()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=12, y=10)
        ctx = _make_context(friendly=[at_unit], enemy=[tank])
        score = ai.evaluate(ctx)
        assert score > 0.3

    def test_low_score_when_tanks_far_away(self):
        ai = ATAmbushAI()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=5, y=5)
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=35, y=25)
        ctx = _make_context(friendly=[at_unit], enemy=[tank])
        score = ai.evaluate(ctx)
        assert score < 0.3

    def test_score_increases_as_tank_approaches(self):
        ai = ATAmbushAI()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        tank_close = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=12, y=10)
        tank_far = _make_unit("tank2", faction=Faction.AXIS, unit_type=UnitType.TANK, x=25, y=10)
        ctx_close = _make_context(friendly=[at_unit], enemy=[tank_close])
        ctx_far = _make_context(friendly=[at_unit], enemy=[tank_far])
        assert ai.evaluate(ctx_close) > ai.evaluate(ctx_far)


# ---------------------------------------------------------------------------
# Test: evaluate — engagement penalty
# ---------------------------------------------------------------------------


class TestEvaluateEngagementPenalty:
    def test_engaged_at_units_lower_score(self):
        ai = ATAmbushAI()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=12, y=10)

        # Without engagement
        ctx_normal = _make_context(friendly=[at_unit], enemy=[tank])

        # With engagement (suppressed)
        at_engaged = _make_unit("at2", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        at_engaged.morale.add_suppression(10)
        ctx_engaged = _make_context(friendly=[at_engaged], enemy=[tank])

        score_normal = ai.evaluate(ctx_normal)
        score_engaged = ai.evaluate(ctx_engaged)
        assert score_normal >= score_engaged


# ---------------------------------------------------------------------------
# Test: _find_at_units
# ---------------------------------------------------------------------------


class TestFindATUnits:
    def test_finds_at_gun_team(self):
        ai = ATAmbushAI()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM)
        ctx = _make_context(friendly=[at_unit])
        result = ai._find_at_units(ctx)
        assert len(result) == 1
        assert result[0].id == "at1"

    def test_finds_infantry_with_at_weapon(self):
        ai = ATAmbushAI()
        inf_with_piat = _make_unit("inf_at", unit_type=UnitType.INFANTRY_SQUAD, weapon_id="piat")
        ctx = _make_context(friendly=[inf_with_piat])
        result = ai._find_at_units(ctx)
        assert len(result) == 1
        assert result[0].id == "inf_at"

    def test_excludes_dead_at_units(self):
        ai = ATAmbushAI()
        dead_at = _make_unit("dead_at", unit_type=UnitType.AT_GUN_TEAM, hp=0)
        ctx = _make_context(friendly=[dead_at])
        result = ai._find_at_units(ctx)
        assert len(result) == 0

    def test_excludes_infantry_without_at_weapon(self):
        ai = ATAmbushAI()
        inf = _make_unit("inf1", unit_type=UnitType.INFANTRY_SQUAD, weapon_id="rifle")
        ctx = _make_context(friendly=[inf])
        result = ai._find_at_units(ctx)
        assert len(result) == 0

    def test_finds_pak40_unit(self):
        ai = ATAmbushAI()
        pak_unit = _make_unit("pak1", unit_type=UnitType.AT_GUN_TEAM, weapon_id="pak40")
        ctx = _make_context(friendly=[pak_unit])
        result = ai._find_at_units(ctx)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Test: _find_enemy_armor
# ---------------------------------------------------------------------------


class TestFindEnemyArmor:
    def test_finds_tanks(self):
        ai = ATAmbushAI()
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=30, y=10)
        ctx = _make_context(enemy=[tank])
        result = ai._find_enemy_armor(ctx)
        assert len(result) == 1
        assert result[0].id == "tank1"

    def test_excludes_dead_tanks(self):
        ai = ATAmbushAI()
        dead_tank = _make_unit("dead_tank", faction=Faction.AXIS, unit_type=UnitType.TANK, hp=0)
        ctx = _make_context(enemy=[dead_tank])
        result = ai._find_enemy_armor(ctx)
        assert len(result) == 0

    def test_excludes_infantry(self):
        ai = ATAmbushAI()
        enemy_inf = _make_unit("e_inf", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD)
        ctx = _make_context(enemy=[enemy_inf])
        result = ai._find_enemy_armor(ctx)
        assert len(result) == 0

    def test_finds_multiple_tanks(self):
        ai = ATAmbushAI()
        tanks = [
            _make_unit(f"tank{i}", faction=Faction.AXIS, unit_type=UnitType.TANK, x=20 + i, y=10)
            for i in range(3)
        ]
        ctx = _make_context(enemy=tanks)
        result = ai._find_enemy_armor(ctx)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Test: _predict_tank_route
# ---------------------------------------------------------------------------


class TestPredictTankRoute:
    def test_returns_list_of_coords(self):
        ai = ATAmbushAI()
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=5, y=15)
        gm = _make_map_with_mixed_terrain()
        vl = [(TileCoord(35, 15), None, 10)]
        ctx = _make_context(enemy=[tank], game_map=gm, vl_positions=vl)
        route = ai._predict_tank_route(tank, ctx)
        assert isinstance(route, list)
        assert len(route) >= 1
        assert route[0] == tank.position.tile_coord

    def test_route_starts_at_tank_position(self):
        ai = ATAmbushAI()
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=5, y=15)
        ctx = _make_context(enemy=[tank])
        route = ai._predict_tank_route(tank, ctx)
        assert route[0] == TileCoord(5, 15)

    def test_route_toward_vl(self):
        ai = ATAmbushAI()
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=5, y=15)
        gm = _make_map_with_mixed_terrain()
        vl = [(TileCoord(35, 15), None, 10)]
        ctx = _make_context(enemy=[tank], game_map=gm, vl_positions=vl)
        route = ai._predict_tank_route(tank, ctx)
        # Route should generally move toward the VL
        if len(route) > 1:
            last = route[-1]
            assert last.x > tank.position.tile_coord.x or last.y != tank.position.tile_coord.y


# ---------------------------------------------------------------------------
# Test: _find_ambush_position
# ---------------------------------------------------------------------------


class TestFindAmbushPosition:
    def test_returns_none_for_empty_route(self):
        ai = ATAmbushAI()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        ctx = _make_context(friendly=[at_unit])
        result = ai._find_ambush_position(at_unit, [], ctx)
        assert result is None

    def test_finds_woods_near_route(self):
        ai = ATAmbushAI()
        gm = _make_map_with_mixed_terrain()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        # Tank route along the road at y=15
        route = [TileCoord(x, 15) for x in range(5, 20)]
        ctx = _make_context(friendly=[at_unit], game_map=gm)
        result = ai._find_ambush_position(at_unit, route, ctx)
        if result is not None:
            # Should be a passable position with some cover
            assert gm.is_within_bounds(result)
            assert gm.is_passable(result)

    def test_prefers_cover_over_open(self):
        ai = ATAmbushAI()
        # Map with woods at (10, 12) near the route
        gm = _make_map_with_woods(woods_x=10, woods_y=12)
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        route = [TileCoord(10, 15)]
        ctx = _make_context(friendly=[at_unit], game_map=gm)
        result = ai._find_ambush_position(at_unit, route, ctx)
        if result is not None:
            terrain = gm.get_terrain(result)
            # Should prefer a position with cover
            assert terrain.cover_bonus > 0 or terrain.concealment_modifier > 0


# ---------------------------------------------------------------------------
# Test: _is_in_ambush_position
# ---------------------------------------------------------------------------


class TestIsInAmbushPosition:
    def test_in_woods_is_ambush(self):
        ai = ATAmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        ctx = _make_context(friendly=[at_unit], game_map=gm)
        assert ai._is_in_ambush_position(at_unit, ctx) is True

    def test_in_open_is_not_ambush(self):
        ai = ATAmbushAI()
        gm = _make_map()  # all open terrain
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        ctx = _make_context(friendly=[at_unit], game_map=gm)
        assert ai._is_in_ambush_position(at_unit, ctx) is False

    def test_in_hedge_is_ambush(self):
        ai = ATAmbushAI()
        grid = np.zeros((30, 40), dtype=np.int8)
        grid[10, 10] = TerrainType.HEDGE
        gm = GameMap(id="test", name="test", width=40, height=30, tile_grid=grid)
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        ctx = _make_context(friendly=[at_unit], game_map=gm)
        assert ai._is_in_ambush_position(at_unit, ctx) is True


# ---------------------------------------------------------------------------
# Test: _effective_at_range
# ---------------------------------------------------------------------------


class TestEffectiveATRange:
    def test_piat_range(self):
        ai = ATAmbushAI()
        unit = _make_unit("at1", unit_type=UnitType.INFANTRY_SQUAD, weapon_id="piat")
        assert ai._effective_at_range(unit) == 8

    def test_pak40_range(self):
        ai = ATAmbushAI()
        unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, weapon_id="pak40")
        assert ai._effective_at_range(unit) == 12

    def test_at_gun_range(self):
        ai = ATAmbushAI()
        unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, weapon_id="at_gun")
        assert ai._effective_at_range(unit) == 12

    def test_bazooka_range(self):
        ai = ATAmbushAI()
        unit = _make_unit("at1", unit_type=UnitType.INFANTRY_SQUAD, weapon_id="bazooka")
        assert ai._effective_at_range(unit) == 8

    def test_unknown_weapon_default_range(self):
        ai = ATAmbushAI()
        unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, weapon_id="unknown_at")
        assert ai._effective_at_range(unit) == 10

    def test_panzerschreck_range(self):
        ai = ATAmbushAI()
        unit = _make_unit("at1", unit_type=UnitType.INFANTRY_SQUAD, weapon_id="panzerschreck")
        assert ai._effective_at_range(unit) == 8


# ---------------------------------------------------------------------------
# Test: execute — positioning AT units in ambush
# ---------------------------------------------------------------------------


class TestExecutePositioning:
    def test_at_unit_in_ambush_holds_position(self):
        ai = ATAmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=30, y=10)
        ctx = _make_context(friendly=[at_unit], enemy=[tank], game_map=gm)
        intents = ai.execute(ctx)
        # AT unit in ambush should either hold position or move
        at_intents = [i for i in intents if i.unit_id == "at1"]
        assert len(at_intents) >= 1

    def test_at_unit_not_in_ambush_moves_to_position(self):
        ai = ATAmbushAI()
        gm = _make_map_with_mixed_terrain()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=5, y=5)
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=20, y=15)
        ctx = _make_context(friendly=[at_unit], enemy=[tank], game_map=gm)
        intents = ai.execute(ctx)
        at_intents = [i for i in intents if i.unit_id == "at1"]
        # Should produce at least one intent (move or hold)
        assert len(at_intents) >= 1


# ---------------------------------------------------------------------------
# Test: execute — holds fire until tanks in range
# ---------------------------------------------------------------------------


class TestExecuteHoldFire:
    def test_holds_fire_when_tank_out_of_range(self):
        ai = ATAmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        # Tank far away (20 tiles, beyond at_gun range of 12)
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=30, y=10)
        ctx = _make_context(friendly=[at_unit], enemy=[tank], game_map=gm)
        intents = ai.execute(ctx)
        # Should NOT have an ATTACK intent since tank is out of range
        attack_intents = [
            i for i in intents if i.unit_id == "at1" and i.tactic_type == TacticType.ATTACK
        ]
        assert len(attack_intents) == 0

    def test_fires_when_tank_in_range(self):
        ai = ATAmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        # Tank within range (5 tiles, within at_gun range of 12)
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=15, y=10)
        ctx = _make_context(friendly=[at_unit], enemy=[tank], game_map=gm)
        intents = ai.execute(ctx)
        # Should have an ATTACK intent
        attack_intents = [
            i for i in intents if i.unit_id == "at1" and i.tactic_type == TacticType.ATTACK
        ]
        assert len(attack_intents) == 1
        assert attack_intents[0].target_unit_id == "tank1"


# ---------------------------------------------------------------------------
# Test: execute — empty context
# ---------------------------------------------------------------------------


class TestExecuteEmptyContext:
    def test_no_intents_with_no_at_units(self):
        ai = ATAmbushAI()
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=30, y=10)
        ctx = _make_context(friendly=[], enemy=[tank])
        intents = ai.execute(ctx)
        assert intents == []

    def test_no_intents_with_no_enemy_armor(self):
        ai = ATAmbushAI()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM)
        enemy_inf = _make_unit("e1", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD)
        ctx = _make_context(friendly=[at_unit], enemy=[enemy_inf])
        intents = ai.execute(ctx)
        assert intents == []


# ---------------------------------------------------------------------------
# Test: execute — reposition after firing
# ---------------------------------------------------------------------------


class TestExecuteReposition:
    def test_reposition_when_no_concealment_after_firing(self):
        ai = ATAmbushAI()
        # AT unit in open terrain (no concealment) with tank in range
        gm = _make_map_with_woods(woods_x=12, woods_y=10)
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=15, y=10)
        ctx = _make_context(friendly=[at_unit], enemy=[tank], game_map=gm)
        intents = ai.execute(ctx)
        # AT unit is in open terrain, fires at tank, then may reposition
        # Check that there's at least an attack or hold intent
        at_intents = [i for i in intents if i.unit_id == "at1"]
        assert len(at_intents) >= 1


# ---------------------------------------------------------------------------
# Test: execute — multiple AT units
# ---------------------------------------------------------------------------


class TestExecuteMultipleATUnits:
    def test_each_at_unit_gets_intent(self):
        ai = ATAmbushAI()
        gm = _make_map_with_woods(woods_x=10, woods_y=10)
        at1 = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        at2 = _make_unit("at2", unit_type=UnitType.AT_GUN_TEAM, x=10, y=11)
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=15, y=10)
        ctx = _make_context(friendly=[at1, at2], enemy=[tank], game_map=gm)
        intents = ai.execute(ctx)
        at1_intents = [i for i in intents if i.unit_id == "at1"]
        at2_intents = [i for i in intents if i.unit_id == "at2"]
        assert len(at1_intents) >= 1
        assert len(at2_intents) >= 1


# ---------------------------------------------------------------------------
# Test: _best_target_for
# ---------------------------------------------------------------------------


class TestBestTargetFor:
    def test_selects_closest_tank_with_los(self):
        ai = ATAmbushAI()
        gm = _make_map()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        tank_close = _make_unit("close", faction=Faction.AXIS, unit_type=UnitType.TANK, x=15, y=10)
        tank_far = _make_unit("far", faction=Faction.AXIS, unit_type=UnitType.TANK, x=30, y=10)
        ctx = _make_context(friendly=[at_unit], enemy=[tank_close, tank_far], game_map=gm)
        best = ai._best_target_for(at_unit, [tank_close, tank_far], ctx)
        assert best is not None
        assert best.id == "close"

    def test_returns_closest_if_no_los(self):
        ai = ATAmbushAI()
        gm = _make_map()
        at_unit = _make_unit("at1", unit_type=UnitType.AT_GUN_TEAM, x=10, y=10)
        tank = _make_unit("tank1", faction=Faction.AXIS, unit_type=UnitType.TANK, x=30, y=10)
        ctx = _make_context(friendly=[at_unit], enemy=[tank], game_map=gm)
        best = ai._best_target_for(at_unit, [tank], ctx)
        assert best is not None
        assert best.id == "tank1"
