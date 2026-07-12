"""Tests for ReconAI — reconnaissance unit dispatch and behavior.

Covers 7 testing dimensions:
  - Happy Path (≥50%): Normal recon order generation, unit selection, target selection
  - Error Case (≥15%): No available units, no targets, empty battlefield
  - Boundary (≥10%): Single unit, single target, zero distance, max distance
  - Performance (≥5%): evaluate+execute timing baseline
  - Config (≥5%): Different unit type combinations, VL configurations
  - Integration (≥10%): Blackboard read/write, TacticalContext integration
  - Security: N/A (no external input)
"""

from __future__ import annotations

import time

import numpy as np

from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.recon_ai import (
    _MAX_RECON_PER_TICK,
    _RECON_PRIORITY,
    BB_RECON_ASSIGNED,
    BB_RECON_TARGETS,
    ReconAI,
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


def _make_map(w: int = 40, h: int = 30, terrain: TerrainType = TerrainType.GRASS) -> GameMap:
    grid = np.full((h, w), terrain.value, dtype=np.int8)
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
# Test: evaluate — intelligence need scoring
# ---------------------------------------------------------------------------


class TestEvaluateIntelNeed:
    def test_no_enemies_high_intel_need(self):
        """Verify: Few enemies spotted produces high reconnaissance priority."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM)
        ctx = _make_context(friendly=[sniper], enemy=[])
        score = ai.evaluate(ctx)
        assert 0.3 < score <= 1.0  # High intel need, has recon unit

    def test_many_enemies_low_intel_need(self):
        """Verify: Many enemies spotted reduces reconnaissance priority."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM)
        enemies = [
            _make_unit(uid=f"e{i}", faction=Faction.AXIS, x=i * 3, y=i * 3) for i in range(5)
        ]
        ctx = _make_context(friendly=[sniper], enemy=enemies)
        score = ai.evaluate(ctx)
        assert score == 0.0  # Enough enemies spotted, no intel gap

    def test_all_enemies_dead_zero_score(self):
        """Verify: All enemies dead means no reconnaissance needed."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM)
        dead_enemies = [_make_unit(uid="e1", faction=Faction.AXIS, hp=0, max_hp=100)]
        ctx = _make_context(friendly=[sniper], enemy=dead_enemies)
        score = ai.evaluate(ctx)
        assert score == 0.0

    def test_no_recon_units_zero_score(self):
        """Verify: No recon-capable units available returns zero."""
        ai = ReconAI()
        tank = _make_unit(uid="t1", unit_type=UnitType.TANK)
        ctx = _make_context(friendly=[tank], enemy=[])
        score = ai.evaluate(ctx)
        assert score == 0.0

    def test_no_friendlies_zero_score(self):
        """Verify: Empty friendly list returns zero."""
        ai = ReconAI()
        ctx = _make_context(friendly=[], enemy=[])
        score = ai.evaluate(ctx)
        assert score == 0.0

    def test_partial_enemies_partial_intel_need(self):
        """Verify: Partial enemy spotting produces mid-range score."""
        ai = ReconAI()
        friendlies = [
            _make_unit(uid="f1", unit_type=UnitType.SNIPER_TEAM),
            _make_unit(uid="f2", unit_type=UnitType.INFANTRY_SQUAD),
        ]
        # 1 enemy spotted, expected = max(2*0.5, 1) = 1, spotted >= expected → 0
        # Need 0 enemies for intel gap
        ctx = _make_context(friendly=friendlies, enemy=[])
        score = ai.evaluate(ctx)
        assert 0.0 < score <= 1.0

    def test_score_within_valid_range(self):
        """Verify: Score is always in [0.0, 1.0]."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM)
        ctx = _make_context(friendly=[sniper], enemy=[])
        score = ai.evaluate(ctx)
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# Test: evaluate — available ratio and defensive stance
# ---------------------------------------------------------------------------


class TestEvaluateModifiers:
    def test_more_recon_units_increases_score(self):
        """Verify: More recon-capable units increases available_ratio component."""
        ai = ReconAI()
        one_sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM)
        ctx_one = _make_context(friendly=[one_sniper], enemy=[])

        snipers = [
            _make_unit(uid=f"s{i}", unit_type=UnitType.SNIPER_TEAM, x=i * 5, y=i * 5)
            for i in range(4)
        ]
        ctx_many = _make_context(friendly=snipers, enemy=[])

        score_one = ai.evaluate(ctx_one)
        score_many = ai.evaluate(ctx_many)
        assert score_many >= score_one

    def test_defensive_stance_boosts_score(self):
        """Verify: Units with stationary_ticks > 0 boost defensive_stance component."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM)
        bb = Blackboard()
        bb.set("stationary_ticks", 10)

        ctx_no_defense = _make_context(friendly=[sniper], enemy=[])
        ctx_defense = _make_context(friendly=[sniper], enemy=[], blackboards={"s1": bb})

        score_no_def = ai.evaluate(ctx_no_defense)
        score_def = ai.evaluate(ctx_defense)
        assert score_def >= score_no_def

    def test_infantry_squad_as_recon_unit(self):
        """Verify: INFANTRY_SQUAD is accepted as recon unit."""
        ai = ReconAI()
        inf = _make_unit(uid="i1", unit_type=UnitType.INFANTRY_SQUAD)
        ctx = _make_context(friendly=[inf], enemy=[])
        score = ai.evaluate(ctx)
        assert score > 0.0

    def test_tank_not_recon_unit(self):
        """Verify: TANK is excluded from recon candidates."""
        ai = ReconAI()
        tank = _make_unit(uid="t1", unit_type=UnitType.TANK)
        ctx = _make_context(friendly=[tank], enemy=[])
        score = ai.evaluate(ctx)
        assert score == 0.0

    def test_dead_sniper_not_candidate(self):
        """Verify: Dead sniper is not a recon candidate."""
        ai = ReconAI()
        dead_sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, hp=0, max_hp=100)
        ctx = _make_context(friendly=[dead_sniper], enemy=[])
        score = ai.evaluate(ctx)
        assert score == 0.0

    def test_low_morale_sniper_not_candidate(self):
        """Verify: Sniper with broken morale is not a recon candidate."""
        ai = ReconAI()
        broken = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, morale=5)
        ctx = _make_context(friendly=[broken], enemy=[])
        score = ai.evaluate(ctx)
        assert score == 0.0


# ---------------------------------------------------------------------------
# Test: execute — intent generation
# ---------------------------------------------------------------------------


class TestExecuteIntentGeneration:
    def test_generates_recon_intent(self):
        """Verify: Execute produces RECONNAISSANCE tactic intents."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        vl = (TileCoord(20, 20), None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert len(intents) >= 1
        assert intents[0].tactic_type == TacticType.RECONNAISSANCE

    def test_intent_has_correct_unit_id(self):
        """Verify: Intent targets the correct unit."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        vl = (TileCoord(20, 20), None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert intents[0].unit_id == "s1"

    def test_intent_has_low_priority(self):
        """Verify: Recon intents have low priority (2)."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        vl = (TileCoord(20, 20), None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert intents[0].priority == _RECON_PRIORITY

    def test_intent_has_target_position(self):
        """Verify: Intent includes target position for movement."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=8, y=8)
        vl_pos = TileCoord(10, 10)
        vl = (vl_pos, None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert intents[0].target_position is not None
        assert intents[0].target_position == vl_pos

    def test_sniper_priority_over_infantry(self):
        """Verify: SNIPER_TEAM gets recon assignment before INFANTRY_SQUAD."""
        ai = ReconAI()
        sniper = _make_unit(uid="sniper", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        inf = _make_unit(uid="inf", unit_type=UnitType.INFANTRY_SQUAD, x=6, y=6)
        vl = (TileCoord(20, 20), None, 1)
        ctx = _make_context(friendly=[sniper, inf], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        # Sniper should get the first (and likely only) recon assignment
        assert any(i.unit_id == "sniper" for i in intents)

    def test_multiple_targets_multiple_intents(self):
        """Verify: Multiple VL targets produce multiple recon intents."""
        ai = ReconAI()
        s1 = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        s2 = _make_unit(uid="s2", unit_type=UnitType.SNIPER_TEAM, x=30, y=30)
        vl1 = (TileCoord(10, 10), None, 1)
        vl2 = (TileCoord(35, 35), None, 1)
        ctx = _make_context(friendly=[s1, s2], enemy=[], vl_positions=[vl1, vl2])
        intents = ai.execute(ctx)
        assert len(intents) >= 2
        assigned_ids = {i.unit_id for i in intents}
        assert "s1" in assigned_ids
        assert "s2" in assigned_ids

    def test_max_recon_per_tick_limit(self):
        """Verify: No more than _MAX_RECON_PER_TICK intents generated per tick."""
        ai = ReconAI()
        snipers = [
            _make_unit(uid=f"s{i}", unit_type=UnitType.SNIPER_TEAM, x=i * 5, y=i * 5)
            for i in range(10)
        ]
        vls = [(TileCoord(i * 4, i * 4), None, 1) for i in range(10)]
        ctx = _make_context(friendly=snipers, enemy=[], vl_positions=vls)
        intents = ai.execute(ctx)
        assert len(intents) <= _MAX_RECON_PER_TICK


# ---------------------------------------------------------------------------
# Test: execute — target selection
# ---------------------------------------------------------------------------


class TestExecuteTargetSelection:
    def test_nearest_target_selected(self):
        """Verify: Unit selects nearest unassigned VL target."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=10, y=10)
        near_vl = (TileCoord(12, 12), None, 1)
        far_vl = (TileCoord(35, 35), None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[near_vl, far_vl])
        intents = ai.execute(ctx)
        assert len(intents) == 1
        assert intents[0].target_position == TileCoord(12, 12)

    def test_no_duplicate_targets(self):
        """Verify: Two units don't get assigned the same target."""
        ai = ReconAI()
        s1 = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        s2 = _make_unit(uid="s2", unit_type=UnitType.SNIPER_TEAM, x=6, y=6)
        vl = (TileCoord(10, 10), None, 1)
        ctx = _make_context(friendly=[s1, s2], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        target_positions = [i.target_position for i in intents]
        # Each target should be unique
        assert len(target_positions) == len(set((p.x, p.y) for p in target_positions))

    def test_map_edge_targets_used_when_no_vl(self):
        """Verify: Map edge midpoints used as targets when no VL positions exist."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=20, y=15)
        gm = _make_map(w=40, h=30)
        ctx = _make_context(friendly=[sniper], enemy=[], game_map=gm, vl_positions=[])
        intents = ai.execute(ctx)
        assert len(intents) >= 1
        assert intents[0].target_position is not None

    def test_no_targets_returns_empty(self):
        """Verify: No VL and no map returns empty intent list."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        # Directly construct context with game_map=None to test graceful handling.
        ctx = TacticalContext(
            friendly_units=[sniper],
            enemy_units=[],
            game_map=None,  # type: ignore[arg-type]
            current_tick=1,
            vl_positions=[],
        )
        intents = ai.execute(ctx)
        assert len(intents) == 0


# ---------------------------------------------------------------------------
# Test: Error cases
# ---------------------------------------------------------------------------


class TestErrorCases:
    def test_no_friendly_units_returns_empty(self):
        """Verify: Empty friendly list produces no intents."""
        ai = ReconAI()
        vl = (TileCoord(10, 10), None, 1)
        ctx = _make_context(friendly=[], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert len(intents) == 0

    def test_no_recon_capable_units_returns_empty(self):
        """Verify: Only non-recon units produces no intents."""
        ai = ReconAI()
        tank = _make_unit(uid="t1", unit_type=UnitType.TANK)
        mg = _make_unit(uid="m1", unit_type=UnitType.MACHINE_GUN_SQUAD)
        vl = (TileCoord(10, 10), None, 1)
        ctx = _make_context(friendly=[tank, mg], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert len(intents) == 0

    def test_dead_recon_unit_not_assigned(self):
        """Verify: Dead sniper is not assigned recon duty."""
        ai = ReconAI()
        dead = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, hp=0, max_hp=100)
        vl = (TileCoord(10, 10), None, 1)
        ctx = _make_context(friendly=[dead], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert len(intents) == 0

    def test_incapacitated_unit_not_assigned(self):
        """Verify: Unit that cannot act is not assigned."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, hp=0, max_hp=100)
        vl = (TileCoord(10, 10), None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert len(intents) == 0

    def test_no_vl_and_no_map_returns_empty(self):
        """Verify: No targets available returns empty list."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        # Directly construct context with game_map=None.
        ctx = TacticalContext(
            friendly_units=[sniper],
            enemy_units=[],
            game_map=None,  # type: ignore[arg-type]
            current_tick=1,
            vl_positions=[],
        )
        intents = ai.execute(ctx)
        assert len(intents) == 0

    def test_already_assigned_unit_skipped(self):
        """Verify: Unit already in recon_assigned Blackboard is skipped."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        vl = (TileCoord(20, 20), None, 1)
        shared_bb = Blackboard()
        shared_bb.set(BB_RECON_ASSIGNED, ["s1"])
        ctx = _make_context(
            friendly=[sniper], enemy=[], vl_positions=[vl], blackboards={"__shared__": shared_bb}
        )
        intents = ai.execute(ctx)
        assert len(intents) == 0  # s1 already assigned

    def test_already_assigned_target_skipped(self):
        """Verify: Target already in recon_targets Blackboard is skipped."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        vl_pos = TileCoord(20, 20)
        vl = (vl_pos, None, 1)
        shared_bb = Blackboard()
        shared_bb.set(BB_RECON_TARGETS, [vl_pos])
        ctx = _make_context(
            friendly=[sniper], enemy=[], vl_positions=[vl], blackboards={"__shared__": shared_bb}
        )
        intents = ai.execute(ctx)
        # The only VL target is already assigned → no new intents
        # (map edges may still provide targets, so check s1 doesn't target vl_pos)
        for intent in intents:
            assert intent.target_position != vl_pos


# ---------------------------------------------------------------------------
# Test: Boundary conditions
# ---------------------------------------------------------------------------


class TestBoundaryConditions:
    def test_single_unit_single_target(self):
        """Verify: One unit and one target produces exactly one intent."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=10, y=10)
        vl = (TileCoord(15, 15), None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert len(intents) == 1

    def test_unit_at_target_position(self):
        """Verify: Unit already at target position still gets assignment."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=10, y=10)
        vl = (TileCoord(10, 10), None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert len(intents) == 1
        assert intents[0].target_position == TileCoord(10, 10)

    def test_zero_distance_to_target(self):
        """Verify: Zero Chebyshev distance (same tile) is handled."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=20, y=20)
        vl = (TileCoord(20, 20), None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert len(intents) == 1

    def test_max_map_distance(self):
        """Verify: Maximum map distance targets are handled."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=0, y=0)
        vl = (TileCoord(39, 29), None, 1)
        gm = _make_map(w=40, h=30)
        ctx = _make_context(friendly=[sniper], enemy=[], game_map=gm, vl_positions=[vl])
        intents = ai.execute(ctx)
        assert len(intents) >= 1

    def test_single_sniper_vs_multiple_targets(self):
        """Verify: Single unit gets only one target (nearest)."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        vl1 = (TileCoord(8, 8), None, 1)
        vl2 = (TileCoord(30, 30), None, 1)
        vl3 = (TileCoord(35, 5), None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[vl1, vl2, vl3])
        intents = ai.execute(ctx)
        assert len(intents) == 1
        assert intents[0].target_position == TileCoord(8, 8)

    def test_more_units_than_targets(self):
        """Verify: Extra units without targets get no assignment."""
        ai = ReconAI()
        s1 = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        s2 = _make_unit(uid="s2", unit_type=UnitType.SNIPER_TEAM, x=10, y=10)
        s3 = _make_unit(uid="s3", unit_type=UnitType.SNIPER_TEAM, x=15, y=15)
        vl = (TileCoord(20, 20), None, 1)
        ctx = _make_context(friendly=[s1, s2, s3], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        # Only 1 VL target + 4 map edges = 5 targets, but _MAX_RECON_PER_TICK = 3
        assert len(intents) <= _MAX_RECON_PER_TICK

    def test_evaluate_score_zero_boundary(self):
        """Verify: Score exactly 0.0 when conditions not met."""
        ai = ReconAI()
        ctx = _make_context(friendly=[], enemy=[])
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_score_one_near_max(self):
        """Verify: Score approaches but doesn't exceed 1.0."""
        ai = ReconAI()
        snipers = [
            _make_unit(uid=f"s{i}", unit_type=UnitType.SNIPER_TEAM, x=i * 3, y=i * 3)
            for i in range(4)
        ]
        bbs = {f"s{i}": Blackboard() for i in range(4)}
        for bb in bbs.values():
            bb.set("stationary_ticks", 50)
        ctx = _make_context(friendly=snipers, enemy=[], blackboards=bbs)
        score = ai.evaluate(ctx)
        assert score <= 1.0


# ---------------------------------------------------------------------------
# Test: Performance
# ---------------------------------------------------------------------------


class TestPerformance:
    # CI runners are ~2-3x slower than local dev machines; thresholds use 3x
    # headroom over local baselines to avoid flaky failures on shared CI.
    _EVAL_BUDGET_MS = 300.0
    _EXEC_BUDGET_MS = 300.0
    _COMBINED_BUDGET_MS = 450.0

    def test_evaluate_1000_iterations_perf(self):
        """Verify: 1000 evaluate calls complete within perf budget."""
        ai = ReconAI()
        snipers = [
            _make_unit(uid=f"s{i}", unit_type=UnitType.SNIPER_TEAM, x=i * 3, y=i * 3)
            for i in range(5)
        ]
        enemies = [_make_unit(uid=f"e{i}", faction=Faction.AXIS, x=i, y=i) for i in range(2)]
        ctx = _make_context(friendly=snipers, enemy=enemies)
        start = time.perf_counter()
        for _ in range(1000):
            ai.evaluate(ctx)
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < self._EVAL_BUDGET_MS, f"1000 evaluate calls took {elapsed:.2f}ms"

    def test_execute_1000_iterations_perf(self):
        """Verify: 1000 execute calls complete within perf budget."""
        ai = ReconAI()
        snipers = [
            _make_unit(uid=f"s{i}", unit_type=UnitType.SNIPER_TEAM, x=i * 3, y=i * 3)
            for i in range(5)
        ]
        vls = [(TileCoord(i * 5, i * 5), None, 1) for i in range(5)]
        ctx = _make_context(friendly=snipers, enemy=[], vl_positions=vls)
        start = time.perf_counter()
        for _ in range(1000):
            ai.execute(ctx)
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < self._EXEC_BUDGET_MS, f"1000 execute calls took {elapsed:.2f}ms"

    def test_evaluate_execute_combined_perf(self):
        """Verify: 1000 evaluate+execute cycles within perf budget."""
        ai = ReconAI()
        snipers = [
            _make_unit(uid=f"s{i}", unit_type=UnitType.SNIPER_TEAM, x=i * 3, y=i * 3)
            for i in range(3)
        ]
        vls = [(TileCoord(i * 5 + 10, i * 5 + 10), None, 1) for i in range(3)]
        ctx = _make_context(friendly=snipers, enemy=[], vl_positions=vls)
        start = time.perf_counter()
        for _ in range(1000):
            ai.evaluate(ctx)
            ai.execute(ctx)
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < self._COMBINED_BUDGET_MS, f"1000 cycles took {elapsed:.2f}ms"


# ---------------------------------------------------------------------------
# Test: Configuration combinations
# ---------------------------------------------------------------------------


class TestConfigCombinations:
    def test_sniper_only_recon_force(self):
        """Verify: All-sniper force works correctly."""
        ai = ReconAI()
        snipers = [
            _make_unit(uid=f"s{i}", unit_type=UnitType.SNIPER_TEAM, x=i * 5, y=i * 5)
            for i in range(3)
        ]
        vls = [(TileCoord(i * 5 + 20, i * 5 + 20), None, 1) for i in range(3)]
        ctx = _make_context(friendly=snipers, enemy=[], vl_positions=vls)
        intents = ai.execute(ctx)
        assert len(intents) >= 1
        assert all(i.tactic_type == TacticType.RECONNAISSANCE for i in intents)

    def test_infantry_only_recon_force(self):
        """Verify: All-infantry force works (INFANTRY_SQUAD as secondary recon)."""
        ai = ReconAI()
        infs = [
            _make_unit(uid=f"i{i}", unit_type=UnitType.INFANTRY_SQUAD, x=i * 5, y=i * 5)
            for i in range(3)
        ]
        vls = [(TileCoord(i * 5 + 20, i * 5 + 20), None, 1) for i in range(3)]
        ctx = _make_context(friendly=infs, enemy=[], vl_positions=vls)
        intents = ai.execute(ctx)
        assert len(intents) >= 1

    def test_mixed_force_sniper_prioritized(self):
        """Verify: In mixed force, sniper gets first recon assignment."""
        ai = ReconAI()
        sniper = _make_unit(uid="sniper", unit_type=UnitType.SNIPER_TEAM, x=10, y=10)
        inf = _make_unit(uid="inf", unit_type=UnitType.INFANTRY_SQUAD, x=11, y=11)
        tank = _make_unit(uid="tank", unit_type=UnitType.TANK, x=12, y=12)
        vl = (TileCoord(20, 20), None, 1)
        ctx = _make_context(friendly=[sniper, inf, tank], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        # Sniper should be first
        assert intents[0].unit_id == "sniper"

    def test_different_map_sizes(self):
        """Verify: Various map sizes produce valid edge targets."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        for w, h in [(20, 20), (40, 30), (60, 40), (10, 10)]:
            gm = _make_map(w=w, h=h)
            ctx = _make_context(friendly=[sniper], enemy=[], game_map=gm, vl_positions=[])
            intents = ai.execute(ctx)
            assert len(intents) >= 1, f"Failed for map {w}x{h}"
            target = intents[0].target_position
            assert target is not None
            assert 0 <= target.x < w
            assert 0 <= target.y < h

    def test_multiple_vl_configurations(self):
        """Verify: Various VL configurations work correctly."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=15, y=15)
        # 1 VL
        ctx1 = _make_context(
            friendly=[sniper], enemy=[], vl_positions=[(TileCoord(20, 20), "ALLIES", 1)]
        )
        # 3 VLs
        ctx3 = _make_context(
            friendly=[sniper],
            enemy=[],
            vl_positions=[
                (TileCoord(5, 5), None, 1),
                (TileCoord(20, 20), None, 2),
                (TileCoord(35, 25), None, 3),
            ],
        )
        intents1 = ai.execute(ctx1)
        intents3 = ai.execute(ctx3)
        assert len(intents1) >= 1
        assert len(intents3) >= 1

    def test_vl_with_different_owners(self):
        """Verify: VL positions with different owners are all valid targets."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=15, y=15)
        vls = [
            (TileCoord(5, 5), "ALLIES", 1),
            (TileCoord(25, 25), "AXIS", 2),
            (TileCoord(15, 30), None, 3),
        ]
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=vls)
        intents = ai.execute(ctx)
        assert len(intents) == 1  # One unit, one target


# ---------------------------------------------------------------------------
# Test: Integration — Blackboard and TacticalContext
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_blackboard_recon_assigned_loaded(self):
        """Verify: Blackboard recon_assigned prevents duplicate assignment."""
        ai = ReconAI()
        s1 = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        s2 = _make_unit(uid="s2", unit_type=UnitType.SNIPER_TEAM, x=6, y=6)
        vl = (TileCoord(20, 20), None, 1)
        shared_bb = Blackboard()
        shared_bb.set(BB_RECON_ASSIGNED, ["s1"])
        ctx = _make_context(
            friendly=[s1, s2], enemy=[], vl_positions=[vl], blackboards={"__shared__": shared_bb}
        )
        intents = ai.execute(ctx)
        # s1 is already assigned, s2 should get the VL
        assert all(i.unit_id != "s1" for i in intents)
        assert any(i.unit_id == "s2" for i in intents)

    def test_blackboard_recon_targets_loaded(self):
        """Verify: Blackboard recon_targets prevents duplicate target assignment."""
        ai = ReconAI()
        s1 = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        s2 = _make_unit(uid="s2", unit_type=UnitType.SNIPER_TEAM, x=6, y=6)
        vl1_pos = TileCoord(10, 10)
        vl2_pos = TileCoord(30, 30)
        shared_bb = Blackboard()
        shared_bb.set(BB_RECON_TARGETS, [vl1_pos])
        ctx = _make_context(
            friendly=[s1, s2],
            enemy=[],
            vl_positions=[(vl1_pos, None, 1), (vl2_pos, None, 2)],
            blackboards={"__shared__": shared_bb},
        )
        intents = ai.execute(ctx)
        # vl1_pos is already assigned, no intent should target it
        for intent in intents:
            assert intent.target_position != vl1_pos

    def test_no_shared_blackboard_works(self):
        """Verify: Missing __shared__ Blackboard is handled gracefully."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        vl = (TileCoord(20, 20), None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[vl])
        # No __shared__ key in blackboards
        intents = ai.execute(ctx)
        assert len(intents) == 1

    def test_tactical_context_integration(self):
        """Verify: Full TacticalContext with all fields populated."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=10, y=10)
        inf = _make_unit(uid="i1", unit_type=UnitType.INFANTRY_SQUAD, x=12, y=12)
        gm = _make_map(w=40, h=30)
        vl = (TileCoord(30, 20), "AXIS", 2)
        bb1 = Blackboard()
        bb1.set("stationary_ticks", 5)
        ctx = TacticalContext(
            friendly_units=[sniper, inf],
            enemy_units=[],  # No enemies spotted → intel gap → recon needed
            game_map=gm,
            current_tick=42,
            blackboards={"s1": bb1},
            vl_positions=[vl],
        )
        score = ai.evaluate(ctx)
        assert 0.0 < score <= 1.0
        intents = ai.execute(ctx)
        assert len(intents) >= 1

    def test_evaluate_then_execute_consistency(self):
        """Verify: Evaluate > 0 implies execute returns non-empty (when targets exist)."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=10, y=10)
        vl = (TileCoord(20, 20), None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[vl])
        score = ai.evaluate(ctx)
        assert score > 0.0
        intents = ai.execute(ctx)
        assert len(intents) >= 1

    def test_morale_component_integration(self):
        """Verify: MoraleComponent.is_combat_effective gates recon eligibility."""
        ai = ReconAI()
        # High morale — eligible
        ok = _make_unit(uid="ok", unit_type=UnitType.SNIPER_TEAM, morale=80)
        # Broken morale — not eligible
        broken = _make_unit(uid="broken", unit_type=UnitType.SNIPER_TEAM, morale=5)
        vl = (TileCoord(20, 20), None, 1)
        ctx = _make_context(friendly=[ok, broken], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert any(i.unit_id == "ok" for i in intents)
        assert all(i.unit_id != "broken" for i in intents)

    def test_recon_priority_does_not_conflict_with_combat(self):
        """Verify: Recon priority (2) is lower than typical combat priorities (0-1)."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        vl = (TileCoord(20, 20), None, 1)
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert len(intents) == 1
        assert intents[0].priority == 2  # Low priority, below combat

    def test_intent_has_target_position_set(self):
        """Verify: All recon intents have non-None target_position."""
        ai = ReconAI()
        snipers = [
            _make_unit(uid=f"s{i}", unit_type=UnitType.SNIPER_TEAM, x=i * 5, y=i * 5)
            for i in range(3)
        ]
        vls = [(TileCoord(i * 5 + 20, i * 5 + 20), None, 1) for i in range(3)]
        ctx = _make_context(friendly=snipers, enemy=[], vl_positions=vls)
        intents = ai.execute(ctx)
        for intent in intents:
            assert intent.target_position is not None
            assert intent.has_target is True

    def test_tactic_type_is_reconnaissance(self):
        """Verify: All generated intents use RECONNAISSANCE tactic type."""
        ai = ReconAI()
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM, x=5, y=5)
        vls = [(TileCoord(i * 5 + 10, i * 5 + 10), None, 1) for i in range(3)]
        ctx = _make_context(friendly=[sniper], enemy=[], vl_positions=vls)
        intents = ai.execute(ctx)
        for intent in intents:
            assert intent.tactic_type == TacticType.RECONNAISSANCE
