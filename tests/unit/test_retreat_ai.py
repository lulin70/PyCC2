"""Tests for RetreatDecisionAI — retreat and bridge demolition decisions."""

from __future__ import annotations

import numpy as np

from pycc2.domain.ai.retreat_ai import RetreatDecisionAI
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.terrain_type import TerrainType


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


def _make_map_with_bridge(
    bridge_x: int = 20, bridge_y: int = 15, w: int = 40, h: int = 30
) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    grid[bridge_y, bridge_x] = TerrainType.BRIDGE
    return GameMap(id="test", name="test_bridge", width=w, height=h, tile_grid=grid)


def _make_context(
    friendly: list[Unit] | None = None,
    enemy: list[Unit] | None = None,
    game_map: GameMap | None = None,
    vl_positions: list[tuple[TileCoord, str | None, int]] | None = None,
    tick: int = 1,
) -> TacticalContext:
    return TacticalContext(
        friendly_units=friendly or [],
        enemy_units=enemy or [],
        game_map=game_map or _make_map(),
        current_tick=tick,
        vl_positions=vl_positions or [],
    )


# ---------------------------------------------------------------------------
# Test: evaluate — force ratio
# ---------------------------------------------------------------------------

class TestEvaluateForceRatio:
    def test_favorable_ratio_returns_low_score(self):
        """When force ratio >= 0.7, evaluate should return near 0.0."""
        ai = RetreatDecisionAI()
        friendlies = [_make_unit("f1"), _make_unit("f2"), _make_unit("f3")]
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=30, y=10)]
        ctx = _make_context(friendly=friendlies, enemy=enemies)
        score = ai.evaluate(ctx)
        assert 0.0 <= score <= 0.15

    def test_medium_ratio_returns_medium_score(self):
        """When 0.5 <= force_ratio < 0.7, evaluate should return 0.3-0.5."""
        ai = RetreatDecisionAI()
        friendlies = [_make_unit("f1"), _make_unit("f2")]
        enemies = [
            _make_unit("e1", faction=Faction.AXIS, x=30, y=10),
            _make_unit("e2", faction=Faction.AXIS, x=31, y=10),
            _make_unit("e3", faction=Faction.AXIS, x=32, y=10),
        ]
        ctx = _make_context(friendly=friendlies, enemy=enemies)
        score = ai.evaluate(ctx)
        assert 0.25 <= score <= 0.55

    def test_unfavorable_ratio_returns_high_score(self):
        """When force_ratio < 0.5, evaluate should return 0.7-0.9."""
        ai = RetreatDecisionAI()
        friendlies = [_make_unit("f1")]
        enemies = [
            _make_unit("e1", faction=Faction.AXIS, x=30, y=10),
            _make_unit("e2", faction=Faction.AXIS, x=31, y=10),
            _make_unit("e3", faction=Faction.AXIS, x=32, y=10),
        ]
        ctx = _make_context(friendly=friendlies, enemy=enemies)
        score = ai.evaluate(ctx)
        assert 0.65 <= score <= 0.95

    def test_no_enemies_returns_low_score(self):
        """When no enemies, force_ratio is very high, score should be low."""
        ai = RetreatDecisionAI()
        friendlies = [_make_unit("f1")]
        ctx = _make_context(friendly=friendlies, enemy=[])
        score = ai.evaluate(ctx)
        assert score <= 0.15

    def test_no_friendlies_returns_high_score(self):
        """When no friendlies alive, force_ratio = 0, score should be high."""
        ai = RetreatDecisionAI()
        # Dead friendly unit
        friendlies = [_make_unit("f1", hp=0)]
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=30, y=10)]
        ctx = _make_context(friendly=friendlies, enemy=enemies)
        score = ai.evaluate(ctx)
        assert score >= 0.65


# ---------------------------------------------------------------------------
# Test: evaluate — morale boost
# ---------------------------------------------------------------------------

class TestEvaluateMoraleBoost:
    def test_low_morale_boosts_priority(self):
        """Average morale < 30 should boost retreat priority."""
        ai = RetreatDecisionAI()
        # 2 friendlies vs 2 enemies → ratio = 1.0, base ~0.0
        # But low morale should add +0.15
        friendlies = [
            _make_unit("f1", morale=20),
            _make_unit("f2", morale=25),
        ]
        enemies = [
            _make_unit("e1", faction=Faction.AXIS, x=30, y=10),
            _make_unit("e2", faction=Faction.AXIS, x=31, y=10),
        ]
        ctx = _make_context(friendly=friendlies, enemy=enemies)
        score = ai.evaluate(ctx)
        # Without morale boost score would be ~0.0-0.1; with boost >= 0.1
        assert score >= 0.1

    def test_high_morale_no_boost(self):
        """High morale should not add extra priority."""
        ai = RetreatDecisionAI()
        friendlies = [_make_unit("f1", morale=80), _make_unit("f2", morale=90)]
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=30, y=10)]
        ctx = _make_context(friendly=friendlies, enemy=enemies)
        score = ai.evaluate(ctx)
        # ratio = 2.0 → base near 0, no morale boost
        assert score <= 0.15


# ---------------------------------------------------------------------------
# Test: evaluate — bridge threat boost
# ---------------------------------------------------------------------------

class TestEvaluateBridgeThreatBoost:
    def test_bridge_threat_boosts_priority(self):
        """Bridge VL with nearby enemies should boost priority by 0.1."""
        ai = RetreatDecisionAI()
        gm = _make_map_with_bridge(bridge_x=20, bridge_y=15)
        friendlies = [_make_unit("f1"), _make_unit("f2")]
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=21, y=15)]
        vl = [(TileCoord(20, 15), "ALLIES", 10)]
        ctx = _make_context(
            friendly=friendlies, enemy=enemies, game_map=gm, vl_positions=vl
        )
        score_with_bridge = ai.evaluate(ctx)

        # Same setup without bridge terrain
        gm2 = _make_map()
        ctx2 = _make_context(
            friendly=friendlies, enemy=enemies, game_map=gm2, vl_positions=vl
        )
        score_without_bridge = ai.evaluate(ctx2)

        assert score_with_bridge > score_without_bridge


# ---------------------------------------------------------------------------
# Test: _calculate_force_ratio
# ---------------------------------------------------------------------------

class TestCalculateForceRatio:
    def test_basic_ratio(self):
        ai = RetreatDecisionAI()
        friendlies = [_make_unit("f1"), _make_unit("f2")]
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=30, y=10)]
        ctx = _make_context(friendly=friendlies, enemy=enemies)
        assert ai._calculate_force_ratio(ctx) == 2.0

    def test_no_enemies_denominator_is_one(self):
        ai = RetreatDecisionAI()
        friendlies = [_make_unit("f1")]
        ctx = _make_context(friendly=friendlies, enemy=[])
        assert ai._calculate_force_ratio(ctx) == 1.0

    def test_dead_units_not_counted(self):
        ai = RetreatDecisionAI()
        friendlies = [_make_unit("f1"), _make_unit("f2", hp=0)]
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=30, y=10)]
        ctx = _make_context(friendly=friendlies, enemy=enemies)
        assert ai._calculate_force_ratio(ctx) == 1.0

    def test_zero_alive_ratio(self):
        ai = RetreatDecisionAI()
        friendlies = [_make_unit("f1", hp=0)]
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=30, y=10)]
        ctx = _make_context(friendly=friendlies, enemy=enemies)
        assert ai._calculate_force_ratio(ctx) == 0.0


# ---------------------------------------------------------------------------
# Test: _is_bridge_threatened
# ---------------------------------------------------------------------------

class TestIsBridgeThreatened:
    def test_bridge_with_nearby_enemy_is_threatened(self):
        ai = RetreatDecisionAI()
        gm = _make_map_with_bridge(bridge_x=20, bridge_y=15)
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=22, y=15)]
        vl = [(TileCoord(20, 15), "ALLIES", 10)]
        ctx = _make_context(enemy=enemies, game_map=gm, vl_positions=vl)
        assert ai._is_bridge_threatened(ctx) is True

    def test_bridge_with_distant_enemy_not_threatened(self):
        ai = RetreatDecisionAI()
        gm = _make_map_with_bridge(bridge_x=20, bridge_y=15)
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=35, y=15)]
        vl = [(TileCoord(20, 15), "ALLIES", 10)]
        ctx = _make_context(enemy=enemies, game_map=gm, vl_positions=vl)
        assert ai._is_bridge_threatened(ctx) is False

    def test_non_bridge_vl_not_threatened_even_with_enemies(self):
        ai = RetreatDecisionAI()
        gm = _make_map()  # all open terrain
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=22, y=15)]
        vl = [(TileCoord(20, 15), "ALLIES", 10)]
        ctx = _make_context(enemy=enemies, game_map=gm, vl_positions=vl)
        assert ai._is_bridge_threatened(ctx) is False

    def test_no_vls_not_threatened(self):
        ai = RetreatDecisionAI()
        gm = _make_map_with_bridge(bridge_x=20, bridge_y=15)
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=22, y=15)]
        ctx = _make_context(enemy=enemies, game_map=gm, vl_positions=[])
        assert ai._is_bridge_threatened(ctx) is False


# ---------------------------------------------------------------------------
# Test: _select_retreat_units
# ---------------------------------------------------------------------------

class TestSelectRetreatUnits:
    def test_low_hp_unit_selected(self):
        ai = RetreatDecisionAI()
        unit = _make_unit("f1", hp=30, max_hp=100)  # hp_ratio = 0.3 < 0.5
        ctx = _make_context(friendly=[unit])
        result = ai._select_retreat_units(ctx)
        assert len(result) == 1
        assert result[0].id == "f1"

    def test_low_morale_unit_selected(self):
        ai = RetreatDecisionAI()
        unit = _make_unit("f1", morale=20)  # < 30
        ctx = _make_context(friendly=[unit])
        result = ai._select_retreat_units(ctx)
        assert len(result) == 1
        assert result[0].id == "f1"

    def test_healthy_unit_not_selected(self):
        ai = RetreatDecisionAI()
        unit = _make_unit("f1", hp=80, max_hp=100, morale=70)
        ctx = _make_context(friendly=[unit])
        result = ai._select_retreat_units(ctx)
        assert len(result) == 0

    def test_dead_unit_not_selected(self):
        ai = RetreatDecisionAI()
        unit = _make_unit("f1", hp=0, morale=20)
        ctx = _make_context(friendly=[unit])
        result = ai._select_retreat_units(ctx)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Test: _select_covering_units
# ---------------------------------------------------------------------------

class TestSelectCoveringUnits:
    def test_mg_unit_selected(self):
        ai = RetreatDecisionAI()
        mg = _make_unit("mg1", unit_type=UnitType.MACHINE_GUN_SQUAD)
        ctx = _make_context(friendly=[mg])
        result = ai._select_covering_units(ctx)
        assert len(result) == 1
        assert result[0].id == "mg1"

    def test_infantry_not_selected_as_cover(self):
        ai = RetreatDecisionAI()
        inf = _make_unit("inf1", unit_type=UnitType.INFANTRY_SQUAD)
        ctx = _make_context(friendly=[inf])
        result = ai._select_covering_units(ctx)
        assert len(result) == 0

    def test_panicked_mg_not_selected(self):
        ai = RetreatDecisionAI()
        mg = _make_unit("mg1", unit_type=UnitType.MACHINE_GUN_SQUAD, morale=5)
        ctx = _make_context(friendly=[mg])
        result = ai._select_covering_units(ctx)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Test: _find_retreat_destination
# ---------------------------------------------------------------------------

class TestFindRetreatDestination:
    def test_prefers_safe_friendly_vl(self):
        ai = RetreatDecisionAI()
        gm = _make_map()
        unit = _make_unit("f1", x=10, y=10)
        # Friendly-held VL far from enemies
        vl = [(TileCoord(5, 5), "ALLIES", 10)]
        ctx = _make_context(
            friendly=[unit],
            enemy=[_make_unit("e1", faction=Faction.AXIS, x=30, y=10)],
            game_map=gm,
            vl_positions=vl,
        )
        dest = ai._find_retreat_destination(unit, ctx)
        assert dest == TileCoord(5, 5)

    def test_ignores_threatened_vl(self):
        ai = RetreatDecisionAI()
        gm = _make_map()
        unit = _make_unit("f1", x=10, y=10)
        # VL is held by friendlies but has enemies nearby
        vl = [(TileCoord(12, 10), "ALLIES", 10)]
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=14, y=10)]
        ctx = _make_context(friendly=[unit], enemy=enemies, game_map=gm, vl_positions=vl)
        dest = ai._find_retreat_destination(unit, ctx)
        # Should fall back to map edge since the VL is threatened
        assert dest is not None
        assert dest != TileCoord(12, 10)

    def test_fallback_to_map_edge(self):
        ai = RetreatDecisionAI()
        gm = _make_map(w=40, h=30)
        unit = _make_unit("f1", x=20, y=15)
        ctx = _make_context(friendly=[unit], game_map=gm, vl_positions=[])
        dest = ai._find_retreat_destination(unit, ctx)
        assert dest is not None
        # Should be one of the map edges
        assert gm.is_within_bounds(dest)

    def test_returns_none_if_no_valid_edge(self):
        """Edge case: map too small for margin — still returns something if possible."""
        ai = RetreatDecisionAI()
        gm = _make_map(w=5, h=5)
        unit = _make_unit("f1", x=2, y=2)
        ctx = _make_context(friendly=[unit], game_map=gm, vl_positions=[])
        dest = ai._find_retreat_destination(unit, ctx)
        # Should still find a valid edge point
        assert dest is not None


# ---------------------------------------------------------------------------
# Test: execute — full integration
# ---------------------------------------------------------------------------

class TestExecute:
    def test_retreat_intents_for_weak_units(self):
        ai = RetreatDecisionAI()
        weak = _make_unit("weak1", hp=30, max_hp=100, morale=80)
        strong = _make_unit("strong1", hp=90, max_hp=100, morale=80)
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=30, y=10)]
        ctx = _make_context(friendly=[weak, strong], enemy=enemies)
        intents = ai.execute(ctx)
        retreat_intents = [i for i in intents if i.tactic_type == TacticType.RETREAT]
        assert len(retreat_intents) >= 1
        assert retreat_intents[0].unit_id == "weak1"

    def test_covering_fire_for_mg_units(self):
        ai = RetreatDecisionAI()
        weak = _make_unit("weak1", hp=30, max_hp=100)
        mg = _make_unit("mg1", unit_type=UnitType.MACHINE_GUN_SQUAD)
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=15, y=10)]
        ctx = _make_context(friendly=[weak, mg], enemy=enemies)
        intents = ai.execute(ctx)
        suppress_intents = [
            i for i in intents if i.tactic_type == TacticType.SUPPRESS_FIRE
        ]
        assert len(suppress_intents) >= 1
        assert suppress_intents[0].unit_id == "mg1"

    def test_demolish_bridge_when_threatened(self):
        ai = RetreatDecisionAI()
        gm = _make_map_with_bridge(bridge_x=20, bridge_y=15)
        friendly = _make_unit("f1", x=20, y=15)
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=22, y=15)]
        vl = [(TileCoord(20, 15), "ALLIES", 10)]
        ctx = _make_context(
            friendly=[friendly], enemy=enemies, game_map=gm, vl_positions=vl
        )
        intents = ai.execute(ctx)
        demo_intents = [
            i for i in intents if i.tactic_type == TacticType.DEMOLISH_BRIDGE
        ]
        assert len(demo_intents) >= 1
        assert demo_intents[0].target_position == TileCoord(20, 15)

    def test_no_demolish_when_bridge_not_threatened(self):
        ai = RetreatDecisionAI()
        gm = _make_map_with_bridge(bridge_x=20, bridge_y=15)
        friendly = _make_unit("f1", x=10, y=10)
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=35, y=25)]
        vl = [(TileCoord(20, 15), "ALLIES", 10)]
        ctx = _make_context(
            friendly=[friendly], enemy=enemies, game_map=gm, vl_positions=vl
        )
        intents = ai.execute(ctx)
        demo_intents = [
            i for i in intents if i.tactic_type == TacticType.DEMOLISH_BRIDGE
        ]
        assert len(demo_intents) == 0

    def test_empty_context_returns_no_intents(self):
        ai = RetreatDecisionAI()
        ctx = _make_context(friendly=[], enemy=[])
        intents = ai.execute(ctx)
        assert intents == []

    def test_no_covering_fire_without_retreat_units(self):
        ai = RetreatDecisionAI()
        mg = _make_unit("mg1", unit_type=UnitType.MACHINE_GUN_SQUAD)
        enemies = [_make_unit("e1", faction=Faction.AXIS, x=30, y=10)]
        ctx = _make_context(friendly=[mg], enemy=enemies)
        intents = ai.execute(ctx)
        suppress_intents = [
            i for i in intents if i.tactic_type == TacticType.SUPPRESS_FIRE
        ]
        # No weak units to cover, so no suppress fire
        assert len(suppress_intents) == 0
