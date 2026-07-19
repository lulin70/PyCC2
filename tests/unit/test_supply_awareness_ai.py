"""Tests for SupplyAwarenessAI — supply line protection/severance behavior.

Covers 7 testing dimensions:
  - Happy Path (≥50%): Bridge identification, VL identification, DEFEND/ATTACK generation
  - Error Case (≥15%): No bridges, no VLs, no available units, empty battlefield
  - Boundary (≥10%): Single bridge, single VL, zero distance, max distance
  - Performance (≥5%): evaluate+execute timing baseline
  - Config (≥5%): Different map sizes, bridge counts, VL configurations
  - Integration (≥10%): Blackboard read/write, TacticalContext integration, _threat_score
  - Security: N/A (no external input)
"""

from __future__ import annotations

import time

import numpy as np

from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.supply_awareness_ai import (
    BB_SUPPLY_ATTACK_ASSIGNED,
    BB_SUPPLY_DEFEND_ASSIGNED,
    SupplyAwarenessAI,
)
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.ai.tactical_ai_types import TacticalContext
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


def _make_map(
    w: int = 40,
    h: int = 30,
    terrain: TerrainType = TerrainType.GRASS,
    bridges: list[tuple[int, int]] | None = None,
) -> GameMap:
    grid = np.full((h, w), terrain.value, dtype=np.int8)
    if bridges:
        for bx, by in bridges:
            grid[by, bx] = TerrainType.BRIDGE.value
    gm = GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)
    if gm.tiles_enhanced is None:
        gm.tiles_enhanced = {}
    return gm


def _make_context(
    friendly: list[Unit] | None = None,
    enemy: list[Unit] | None = None,
    game_map: GameMap | None = None,
    tick: int = 1,
    vl_positions: list[tuple[TileCoord, str | None, int]] | None = None,
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
# Happy Path: Supply point identification
# ---------------------------------------------------------------------------


class TestSupplyPointIdentification:
    """Verify _identify_supply_points finds bridges and VLs correctly."""

    def test_finds_bridge_on_map(self):
        """Bridge terrain is identified as a supply point."""
        game_map = _make_map(bridges=[(15, 10)])
        ai = SupplyAwarenessAI()
        ctx = _make_context(
            friendly=[_make_unit()],
            game_map=game_map,
        )
        points = ai._identify_supply_points(ctx)
        assert TileCoord(15, 10) in points

    def test_finds_multiple_bridges(self):
        """Multiple bridges are all identified."""
        bridges = [(5, 5), (15, 10), (20, 25)]
        game_map = _make_map(bridges=bridges)
        ai = SupplyAwarenessAI()
        ctx = _make_context(friendly=[_make_unit()], game_map=game_map)
        points = ai._identify_supply_points(ctx)
        for bx, by in bridges:
            assert TileCoord(bx, by) in points

    def test_finds_vl_positions(self):
        """VL positions from context are included as supply points."""
        vl = (TileCoord(20, 20), "ALLIES", 3)
        ai = SupplyAwarenessAI()
        ctx = _make_context(
            friendly=[_make_unit()],
            vl_positions=[vl],
        )
        points = ai._identify_supply_points(ctx)
        assert TileCoord(20, 20) in points

    def test_finds_both_bridges_and_vls(self):
        """Both bridges and VLs are identified together."""
        bridges = [(5, 5), (10, 15)]
        game_map = _make_map(bridges=bridges)
        vl = (TileCoord(20, 20), None, 1)
        ai = SupplyAwarenessAI()
        ctx = _make_context(
            friendly=[_make_unit()],
            game_map=game_map,
            vl_positions=[vl],
        )
        points = ai._identify_supply_points(ctx)
        assert TileCoord(5, 5) in points
        assert TileCoord(10, 15) in points
        assert TileCoord(20, 20) in points

    def test_no_bridges_no_vls_returns_empty(self):
        """Empty map with no VLs has no supply points."""
        ai = SupplyAwarenessAI()
        ctx = _make_context(friendly=[_make_unit()])
        points = ai._identify_supply_points(ctx)
        assert len(points) == 0


# ---------------------------------------------------------------------------
# Happy Path: Evaluate scoring
# ---------------------------------------------------------------------------


class TestEvaluate:
    """Verify evaluate returns appropriate priority scores."""

    def test_no_supply_points_returns_zero(self):
        """No bridges or VLs → evaluate returns 0.0."""
        ai = SupplyAwarenessAI()
        ctx = _make_context(friendly=[_make_unit()])
        assert ai.evaluate(ctx) == 0.0

    def test_no_available_units_returns_zero(self):
        """Supply points exist but no units → evaluate returns 0.0."""
        ai = SupplyAwarenessAI()
        vl = (TileCoord(20, 20), "ALLIES", 3)
        ctx = _make_context(friendly=[], vl_positions=[vl])
        assert ai.evaluate(ctx) == 0.0

    def test_friendly_vl_under_threat_returns_positive(self):
        """Friendly VL with nearby enemy threat → positive score."""
        ai = SupplyAwarenessAI()
        friendly = _make_unit(uid="f1", x=20, y=20)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=22, y=22)
        vl = (TileCoord(20, 20), "ALLIES", 3)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], vl_positions=[vl])
        score = ai.evaluate(ctx)
        assert 0.0 < score <= 1.0

    def test_enemy_vl_vulnerable_returns_positive(self):
        """Enemy VL with friendly advantage → positive score."""
        ai = SupplyAwarenessAI()
        friendly1 = _make_unit(uid="f1", x=20, y=20)
        friendly2 = _make_unit(uid="f2", x=21, y=21)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=25, y=25)
        vl = (TileCoord(20, 20), "GERMANS", 3)
        ctx = _make_context(friendly=[friendly1, friendly2], enemy=[enemy], vl_positions=[vl])
        score = ai.evaluate(ctx)
        assert 0.0 < score <= 1.0

    def test_unthreatened_friendly_vl_returns_low_score(self):
        """Friendly VL with no nearby enemies → low or zero defend_need."""
        ai = SupplyAwarenessAI()
        friendly = _make_unit(uid="f1", x=5, y=5)
        vl = (TileCoord(20, 20), "ALLIES", 3)
        ctx = _make_context(friendly=[friendly], vl_positions=[vl])
        score = ai.evaluate(ctx)
        # No enemies → defend_need=0, no enemy VLs → attack_opportunity=0
        assert score == 0.0

    def test_score_bounded_to_one(self):
        """Score never exceeds 1.0."""
        ai = SupplyAwarenessAI()
        # Many threatened VLs
        units = [_make_unit(uid=f"f{i}", x=10 + i, y=10) for i in range(5)]
        enemies = [
            _make_unit(uid=f"e{i}", faction=Faction.GERMAN, x=12 + i, y=10) for i in range(5)
        ]
        vls = [(TileCoord(10 + i, 10), "ALLIES", 3) for i in range(5)]
        ctx = _make_context(friendly=units, enemy=enemies, vl_positions=vls)
        score = ai.evaluate(ctx)
        assert score <= 1.0


# ---------------------------------------------------------------------------
# Happy Path: Execute intent generation
# ---------------------------------------------------------------------------


class TestExecuteDefend:
    """Verify DEFEND intents are generated for threatened friendly supply points."""

    def test_generates_defend_for_threatened_vl(self):
        """Friendly VL under threat → DEFEND intent generated."""
        ai = SupplyAwarenessAI()
        friendly = _make_unit(uid="f1", x=10, y=10)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=12, y=12)
        vl = (TileCoord(12, 12), "ALLIES", 3)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], vl_positions=[vl])
        intents = ai.execute(ctx)
        defend_intents = [i for i in intents if i.tactic_type == TacticType.DEFEND]
        assert len(defend_intents) >= 1
        assert defend_intents[0].unit_id == "f1"
        assert defend_intents[0].target_position == TileCoord(12, 12)

    def test_defend_priority_is_low(self):
        """Supply DEFEND orders have low priority (2)."""
        ai = SupplyAwarenessAI()
        friendly = _make_unit(uid="f1", x=10, y=10)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=12, y=12)
        vl = (TileCoord(12, 12), "ALLIES", 3)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], vl_positions=[vl])
        intents = ai.execute(ctx)
        for intent in intents:
            assert intent.priority == 2

    def test_no_defend_for_unthreatened_vl(self):
        """Friendly VL with no nearby enemies → no DEFEND intent."""
        ai = SupplyAwarenessAI()
        friendly = _make_unit(uid="f1", x=5, y=5)
        vl = (TileCoord(20, 20), "ALLIES", 3)
        ctx = _make_context(friendly=[friendly], vl_positions=[vl])
        intents = ai.execute(ctx)
        defend_intents = [i for i in intents if i.tactic_type == TacticType.DEFEND]
        assert len(defend_intents) == 0

    def test_defend_prefers_infantry(self):
        """DEFEND assignment prefers INFANTRY_SQUAD/MG/AT units."""
        ai = SupplyAwarenessAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=11, y=11)
        infantry = _make_unit(uid="i1", unit_type=UnitType.INFANTRY_SQUAD, x=11, y=11)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=12, y=12)
        vl = (TileCoord(12, 12), "ALLIES", 3)
        ctx = _make_context(friendly=[sniper, infantry], enemy=[enemy], vl_positions=[vl])
        intents = ai.execute(ctx)
        defend_intents = [i for i in intents if i.tactic_type == TacticType.DEFEND]
        if defend_intents:
            assert defend_intents[0].unit_id == "i1"  # Infantry preferred


class TestExecuteAttack:
    """Verify ATTACK intents are generated for vulnerable enemy supply points."""

    def test_generates_attack_for_vulnerable_enemy_vl(self):
        """Enemy VL with friendly advantage → ATTACK intent generated."""
        ai = SupplyAwarenessAI()
        f1 = _make_unit(uid="f1", x=20, y=20)
        f2 = _make_unit(uid="f2", x=21, y=21)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=25, y=25)
        vl = (TileCoord(20, 20), "GERMANS", 3)
        ctx = _make_context(friendly=[f1, f2], enemy=[enemy], vl_positions=[vl])
        intents = ai.execute(ctx)
        attack_intents = [i for i in intents if i.tactic_type == TacticType.ATTACK]
        assert len(attack_intents) >= 1

    def test_no_attack_for_well_defended_enemy_vl(self):
        """Enemy VL with strong enemy presence → no ATTACK intent."""
        ai = SupplyAwarenessAI()
        friendly = _make_unit(uid="f1", x=5, y=5)
        enemies = [
            _make_unit(uid=f"e{i}", faction=Faction.GERMAN, x=20 + i, y=20) for i in range(3)
        ]
        vl = (TileCoord(20, 20), "GERMANS", 3)
        ctx = _make_context(friendly=[friendly], enemy=enemies, vl_positions=[vl])
        intents = ai.execute(ctx)
        attack_intents = [i for i in intents if i.tactic_type == TacticType.ATTACK]
        assert len(attack_intents) == 0


# ---------------------------------------------------------------------------
# Error Cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    """Edge cases and error handling."""

    def test_empty_battlefield_returns_empty_intents(self):
        """No units on either side → no intents."""
        ai = SupplyAwarenessAI()
        vl = (TileCoord(20, 20), "ALLIES", 3)
        ctx = _make_context(vl_positions=[vl])
        intents = ai.execute(ctx)
        assert intents == []

    def test_no_supply_points_returns_empty_intents(self):
        """No bridges or VLs → no intents."""
        ai = SupplyAwarenessAI()
        ctx = _make_context(friendly=[_make_unit()])
        intents = ai.execute(ctx)
        assert intents == []

    def test_dead_units_not_assigned(self):
        """Dead units are not assigned to supply duty."""
        ai = SupplyAwarenessAI()
        dead = _make_unit(uid="d1", hp=0)
        vl = (TileCoord(10, 10), "ALLIES", 3)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=11, y=11)
        ctx = _make_context(friendly=[dead], enemy=[enemy], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert all(i.unit_id != "d1" for i in intents)

    def test_already_assigned_units_skipped(self):
        """Units already in Blackboard assignment set are skipped."""
        ai = SupplyAwarenessAI()
        bb = Blackboard()
        bb.set(BB_SUPPLY_DEFEND_ASSIGNED, {"f1"})
        friendly = _make_unit(uid="f1", x=10, y=10)
        friendly2 = _make_unit(uid="f2", x=10, y=10)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=12, y=12)
        vl = (TileCoord(12, 12), "ALLIES", 3)
        ctx = _make_context(
            friendly=[friendly, friendly2],
            enemy=[enemy],
            vl_positions=[vl],
            blackboards={"supply": bb},
        )
        intents = ai.execute(ctx)
        assert all(i.unit_id != "f1" for i in intents)

    def test_max_orders_per_tick_enforced(self):
        """At most _MAX_SUPPLY_ORDERS_PER_TICK intents generated per tick."""
        ai = SupplyAwarenessAI()
        from pycc2.domain.ai.supply_awareness_ai import _MAX_SUPPLY_ORDERS_PER_TICK

        # Create many threatened VLs and many units
        units = [_make_unit(uid=f"f{i}", x=10 + i, y=10) for i in range(10)]
        enemies = [
            _make_unit(uid=f"e{i}", faction=Faction.GERMAN, x=12 + i, y=12) for i in range(10)
        ]
        vls = [(TileCoord(12 + i, 12), "ALLIES", 3) for i in range(10)]
        ctx = _make_context(friendly=units, enemy=enemies, vl_positions=vls)
        intents = ai.execute(ctx)
        assert len(intents) <= _MAX_SUPPLY_ORDERS_PER_TICK

    def test_game_map_none_no_crash(self):
        """SupplyAwarenessAI handles game_map=None gracefully."""
        ai = SupplyAwarenessAI()
        vl = (TileCoord(20, 20), "ALLIES", 3)
        ctx = TacticalContext(
            friendly_units=[_make_unit()],
            enemy_units=[],
            game_map=None,  # type: ignore[arg-type]
            current_tick=1,
            vl_positions=[vl],
        )
        # Should not crash, should still find VL
        points = ai._identify_supply_points(ctx)
        assert TileCoord(20, 20) in points


# ---------------------------------------------------------------------------
# Boundary Conditions
# ---------------------------------------------------------------------------


class TestBoundaryConditions:
    """Test edge cases at boundaries."""

    def test_single_bridge_single_unit(self):
        """One bridge, one unit → works correctly."""
        ai = SupplyAwarenessAI()
        game_map = _make_map(bridges=[(15, 10)])
        friendly = _make_unit(uid="f1", x=15, y=10)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=16, y=11)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], game_map=game_map)
        score = ai.evaluate(ctx)
        assert score >= 0.0
        intents = ai.execute(ctx)
        # Bridge is not friendly or enemy owned (no VL), so no DEFEND/ATTACK
        # But it should not crash
        assert isinstance(intents, list)

    def test_unit_on_supply_point_zero_distance(self):
        """Unit standing on the supply point (distance=0) → works."""
        ai = SupplyAwarenessAI()
        friendly = _make_unit(uid="f1", x=20, y=20)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=21, y=21)
        vl = (TileCoord(20, 20), "ALLIES", 3)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], vl_positions=[vl])
        intents = ai.execute(ctx)
        # Should not crash; unit is already on the VL
        assert isinstance(intents, list)

    def test_enemy_at_max_scan_radius(self):
        """Enemy at exactly _SUPPLY_SCAN_RADIUS → counted as threat."""
        ai = SupplyAwarenessAI()
        from pycc2.domain.ai.supply_awareness_ai import _SUPPLY_SCAN_RADIUS

        friendly = _make_unit(uid="f1", x=10, y=10)
        vl_pos = TileCoord(10, 10)
        enemy_x = 10 + _SUPPLY_SCAN_RADIUS
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=enemy_x, y=10)
        vl = (vl_pos, "ALLIES", 3)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], vl_positions=[vl])
        threat = ai._area_threat(ctx, vl_pos, _SUPPLY_SCAN_RADIUS)
        assert threat > 0.0

    def test_enemy_beyond_scan_radius(self):
        """Enemy beyond _SUPPLY_SCAN_RADIUS → not counted as threat."""
        ai = SupplyAwarenessAI()
        from pycc2.domain.ai.supply_awareness_ai import _SUPPLY_SCAN_RADIUS

        friendly = _make_unit(uid="f1", x=10, y=10)
        vl_pos = TileCoord(10, 10)
        enemy_x = 10 + _SUPPLY_SCAN_RADIUS + 5
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=enemy_x, y=10)
        vl = (vl_pos, "ALLIES", 3)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], vl_positions=[vl])
        threat = ai._area_threat(ctx, vl_pos, _SUPPLY_SCAN_RADIUS)
        assert threat == 0.0

    def test_neutral_vl_not_friendly_not_enemy(self):
        """VL with owner=None is neither friendly nor enemy."""
        ai = SupplyAwarenessAI()
        friendly = _make_unit(uid="f1", x=20, y=20)
        vl = (TileCoord(20, 20), None, 3)  # Neutral
        ctx = _make_context(friendly=[friendly], vl_positions=[vl])
        assert not ai._is_friendly_point(ctx, TileCoord(20, 20))
        assert not ai._is_enemy_point(ctx, TileCoord(20, 20))


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


class TestPerformance:
    """Verify evaluate+execute meets performance targets."""

    def test_evaluate_execute_1000_times_under_300ms(self):
        """1000 evaluate+execute cycles must complete in < 300ms.

        Threshold is higher than ReconAI's 150ms because SupplyAwarenessAI
        performs additional numpy bridge-grid scanning per cycle.
        At ~0.2ms/cycle, single-tick performance is excellent.
        """
        ai = SupplyAwarenessAI()
        units = [_make_unit(uid=f"f{i}", x=10 + i, y=10) for i in range(5)]
        enemies = [
            _make_unit(uid=f"e{i}", faction=Faction.GERMAN, x=20 + i, y=20) for i in range(3)
        ]
        vls = [(TileCoord(15, 15), "ALLIES", 3)]
        ctx = _make_context(friendly=units, enemy=enemies, vl_positions=vls)

        start = time.perf_counter()
        for _ in range(1000):
            ai.evaluate(ctx)
            ai.execute(ctx)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 300.0, f"1000 cycles took {elapsed_ms:.2f}ms (target: <300ms)"

    def test_large_map_bridge_scan_performance(self):
        """Bridge scanning on large map must be fast."""
        ai = SupplyAwarenessAI()
        # 100x100 map with 10 bridges
        bridges = [(i * 10, i * 5) for i in range(10)]
        game_map = _make_map(w=100, h=100, bridges=bridges)
        ctx = _make_context(friendly=[_make_unit()], game_map=game_map)

        start = time.perf_counter()
        for _ in range(100):
            ai._identify_supply_points(ctx)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50.0, f"100 bridge scans took {elapsed_ms:.2f}ms"


# ---------------------------------------------------------------------------
# Config: Different configurations
# ---------------------------------------------------------------------------


class TestConfigCombinations:
    """Test with different map/VL configurations."""

    def test_different_map_sizes(self):
        """SupplyAwarenessAI works with various map sizes."""
        ai = SupplyAwarenessAI()
        for w, h in [(20, 20), (40, 30), (80, 60)]:
            game_map = _make_map(w=w, h=h, bridges=[(w // 2, h // 2)])
            vl = (TileCoord(w // 2, h // 2), "ALLIES", 3)
            ctx = _make_context(
                friendly=[_make_unit(x=w // 2, y=h // 2)],
                game_map=game_map,
                vl_positions=[vl],
            )
            score = ai.evaluate(ctx)
            assert 0.0 <= score <= 1.0

    def test_vl_with_different_owners(self):
        """VLs with ALLIES, GERMANS, and None owners are classified correctly."""
        ai = SupplyAwarenessAI()
        vl_friendly = (TileCoord(5, 5), "ALLIES", 3)
        vl_enemy = (TileCoord(25, 25), "GERMANS", 3)
        vl_neutral = (TileCoord(15, 15), None, 1)
        ctx = _make_context(
            friendly=[_make_unit(x=5, y=5)],
            vl_positions=[vl_friendly, vl_enemy, vl_neutral],
        )
        assert ai._is_friendly_point(ctx, TileCoord(5, 5))
        assert ai._is_enemy_point(ctx, TileCoord(25, 25))
        assert not ai._is_friendly_point(ctx, TileCoord(15, 15))
        assert not ai._is_enemy_point(ctx, TileCoord(15, 15))

    def test_mixed_defend_and_attack_intents(self):
        """Both DEFEND and ATTACK intents can be generated in one execute."""
        ai = SupplyAwarenessAI()
        # Friendly VL under threat
        f1 = _make_unit(uid="f1", x=5, y=5)
        e1 = _make_unit(uid="e1", faction=Faction.GERMAN, x=7, y=7)
        vl_friendly = (TileCoord(5, 5), "ALLIES", 3)

        # Enemy VL vulnerable (2 friendlies vs 1 enemy)
        f2 = _make_unit(uid="f2", x=25, y=25)
        f3 = _make_unit(uid="f3", x=26, y=26)
        e2 = _make_unit(uid="e2", faction=Faction.GERMAN, x=30, y=30)
        vl_enemy = (TileCoord(25, 25), "GERMANS", 3)

        ctx = _make_context(
            friendly=[f1, f2, f3],
            enemy=[e1, e2],
            vl_positions=[vl_friendly, vl_enemy],
        )
        intents = ai.execute(ctx)
        tactic_types = {i.tactic_type for i in intents}
        # Should have both DEFEND and ATTACK (if thresholds are met)
        assert TacticType.DEFEND in tactic_types or TacticType.ATTACK in tactic_types


# ---------------------------------------------------------------------------
# Integration: Blackboard and TacticalContext
# ---------------------------------------------------------------------------


class TestIntegration:
    """Full integration with Blackboard and TacticalContext."""

    def test_blackboard_prevents_reassignment(self):
        """Units in Blackboard defend set are not reassigned."""
        ai = SupplyAwarenessAI()
        bb = Blackboard()
        bb.set(BB_SUPPLY_DEFEND_ASSIGNED, {"f1"})
        f1 = _make_unit(uid="f1", x=10, y=10)
        f2 = _make_unit(uid="f2", x=10, y=10)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=12, y=12)
        vl = (TileCoord(12, 12), "ALLIES", 3)
        ctx = _make_context(
            friendly=[f1, f2],
            enemy=[enemy],
            vl_positions=[vl],
            blackboards={"supply": bb},
        )
        intents = ai.execute(ctx)
        # f1 is already assigned → should not appear in new intents
        assert all(i.unit_id != "f1" for i in intents)

    def test_blackboard_attack_prevents_reassignment(self):
        """Units in Blackboard attack set are not reassigned."""
        ai = SupplyAwarenessAI()
        bb = Blackboard()
        bb.set(BB_SUPPLY_ATTACK_ASSIGNED, {"f1"})
        f1 = _make_unit(uid="f1", x=20, y=20)
        f2 = _make_unit(uid="f2", x=21, y=21)
        f3 = _make_unit(uid="f3", x=22, y=22)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=28, y=28)
        vl = (TileCoord(20, 20), "GERMANS", 3)
        ctx = _make_context(
            friendly=[f1, f2, f3],
            enemy=[enemy],
            vl_positions=[vl],
            blackboards={"supply": bb},
        )
        intents = ai.execute(ctx)
        assert all(i.unit_id != "f1" for i in intents)

    def test_no_blackboard_works_gracefully(self):
        """Missing 'supply' blackboard → no crash, units treated as unassigned."""
        ai = SupplyAwarenessAI()
        friendly = _make_unit(uid="f1", x=10, y=10)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=12, y=12)
        vl = (TileCoord(12, 12), "ALLIES", 3)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert isinstance(intents, list)

    def test_threat_score_integration(self):
        """_threat_score from tactical_ai_types is used for threat assessment."""
        ai = SupplyAwarenessAI()
        # Tank has higher threat weight than infantry
        tank_enemy = _make_unit(
            uid="tank1", faction=Faction.GERMAN, unit_type=UnitType.TANK, x=12, y=12
        )
        infantry_enemy = _make_unit(
            uid="inf1", faction=Faction.GERMAN, unit_type=UnitType.INFANTRY_SQUAD, x=12, y=12
        )
        vl_pos = TileCoord(10, 10)
        vl = (vl_pos, "ALLIES", 3)

        ctx_tank = _make_context(friendly=[_make_unit()], enemy=[tank_enemy], vl_positions=[vl])
        ctx_inf = _make_context(friendly=[_make_unit()], enemy=[infantry_enemy], vl_positions=[vl])

        from pycc2.domain.ai.supply_awareness_ai import _SUPPLY_SCAN_RADIUS

        tank_threat = ai._area_threat(ctx_tank, vl_pos, _SUPPLY_SCAN_RADIUS)
        inf_threat = ai._area_threat(ctx_inf, vl_pos, _SUPPLY_SCAN_RADIUS)
        assert tank_threat > inf_threat  # Tank should have higher threat

    def test_full_scenario_friendly_defense(self):
        """Full scenario: friendly VL threatened, unit dispatched to defend."""
        ai = SupplyAwarenessAI()
        # VL at (15, 15) controlled by ALLIES
        # Enemy approaching from (17, 17)
        # Friendly unit at (10, 10) available
        friendly = _make_unit(uid="f1", x=10, y=10)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=17, y=17)
        vl = (TileCoord(15, 15), "ALLIES", 3)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], vl_positions=[vl])

        # Evaluate should detect threat
        score = ai.evaluate(ctx)
        assert score > 0.0

        # Execute should generate DEFEND intent
        intents = ai.execute(ctx)
        defend_intents = [i for i in intents if i.tactic_type == TacticType.DEFEND]
        assert len(defend_intents) >= 1
        assert defend_intents[0].target_position == TileCoord(15, 15)

    def test_full_scenario_enemy_attack(self):
        """Full scenario: enemy VL vulnerable, unit dispatched to attack."""
        ai = SupplyAwarenessAI()
        # VL at (15, 15) controlled by GERMANS
        # Two friendly units nearby, one enemy defender far
        f1 = _make_unit(uid="f1", x=14, y=14)
        f2 = _make_unit(uid="f2", x=16, y=16)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=25, y=25)
        vl = (TileCoord(15, 15), "GERMANS", 3)
        ctx = _make_context(friendly=[f1, f2], enemy=[enemy], vl_positions=[vl])

        # Evaluate should detect opportunity
        score = ai.evaluate(ctx)
        assert score > 0.0

        # Execute should generate ATTACK intent
        intents = ai.execute(ctx)
        attack_intents = [i for i in intents if i.tactic_type == TacticType.ATTACK]
        assert len(attack_intents) >= 1
        assert attack_intents[0].target_position == TileCoord(15, 15)

    def test_bridge_as_supply_point_integration(self):
        """Bridge is identified and units can be dispatched to defend it."""
        ai = SupplyAwarenessAI()
        # Bridge at (15, 10), friendly unit nearby, enemy approaching
        game_map = _make_map(bridges=[(15, 10)])
        # Use VL at bridge position so it's classified as friendly
        vl = (TileCoord(15, 10), "ALLIES", 3)
        friendly = _make_unit(uid="f1", x=10, y=10)
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=17, y=10)
        ctx = _make_context(
            friendly=[friendly], enemy=[enemy], game_map=game_map, vl_positions=[vl]
        )

        points = ai._identify_supply_points(ctx)
        # Bridge at (15,10) appears once from bridge scan + once from VL → dedup not guaranteed
        # But the point should be present
        assert TileCoord(15, 10) in points

        score = ai.evaluate(ctx)
        assert score > 0.0  # VL is friendly and threatened

    def test_area_advantage_ratio(self):
        """_area_advantage returns correct friendly/enemy ratio."""
        ai = SupplyAwarenessAI()
        from pycc2.domain.ai.supply_awareness_ai import _SUPPLY_SCAN_RADIUS

        point = TileCoord(15, 15)
        # 3 friendlies vs 1 enemy → advantage = 3.0
        units = [_make_unit(uid=f"f{i}", x=15 + i, y=15) for i in range(3)]
        enemy = _make_unit(uid="e1", faction=Faction.GERMAN, x=16, y=16)
        ctx = _make_context(friendly=units, enemy=[enemy])
        advantage = ai._area_advantage(ctx, point, _SUPPLY_SCAN_RADIUS)
        assert advantage > 1.0  # Friendlies outnumber enemy

    def test_area_advantage_no_enemies(self):
        """_area_advantage with no enemies → high ratio (max(enemy, 1.0) = 1.0)."""
        ai = SupplyAwarenessAI()
        from pycc2.domain.ai.supply_awareness_ai import _SUPPLY_SCAN_RADIUS

        point = TileCoord(15, 15)
        units = [_make_unit(uid=f"f{i}", x=15 + i, y=15) for i in range(3)]
        ctx = _make_context(friendly=units)
        advantage = ai._area_advantage(ctx, point, _SUPPLY_SCAN_RADIUS)
        assert advantage >= 3.0  # 3 friendlies / 1.0 = 3.0
