"""Tests for TrenchDiggingSystem & TrenchDiggingAI — foxhole digging behavior."""

from __future__ import annotations

import numpy as np

from pycc2.domain.ai.trench_digging import (
    DIG_DURATION,
    STATIONARY_THRESHOLD,
    DigProgress,
    TrenchDiggingAI,
    TrenchDiggingSystem,
)
from pycc2.domain.ai.tactical_ai import TacticalContext
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.enhanced_tile import DecorationType
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


def _make_map(w: int = 40, h: int = 30, terrain: TerrainType = TerrainType.GRASS) -> GameMap:
    grid = np.full((h, w), terrain.value, dtype=np.int8)
    gm = GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)
    # Initialize tiles_enhanced as dict to avoid None returns from get_enhanced_tile
    if gm.tiles_enhanced is None:
        gm.tiles_enhanced = {}
    return gm


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
        vl_positions=[],
    )


# ---------------------------------------------------------------------------
# Test: DigProgress dataclass
# ---------------------------------------------------------------------------

class TestDigProgress:
    def test_initial_state(self):
        dp = DigProgress(unit_id="u1")
        assert dp.unit_id == "u1"
        assert dp.progress == 0
        assert dp.position is None
        assert dp.interrupted is False
        assert dp.is_complete is False
        assert dp.progress_ratio == 0.0

    def test_partial_progress(self):
        dp = DigProgress(unit_id="u1", progress=45)
        assert dp.is_complete is False
        assert abs(dp.progress_ratio - 0.5) < 0.01

    def test_complete_at_duration(self):
        dp = DigProgress(unit_id="u1", progress=DIG_DURATION)
        assert dp.is_complete is True
        assert dp.progress_ratio == 1.0

    def test_exceeds_duration_still_complete(self):
        dp = DigProgress(unit_id="u1", progress=DIG_DURATION + 10)
        assert dp.is_complete is True
        assert dp.progress_ratio == 1.0  # capped at 1.0


# ---------------------------------------------------------------------------
# Test: TrenchDiggingSystem — can_dig conditions
# ---------------------------------------------------------------------------

class TestCanDig:
    def test_infantry_on_grass_can_dig(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit()
        gm = _make_map(terrain=TerrainType.GRASS)
        assert sys.can_dig(unit, gm) is True

    def test_tank_cannot_dig(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit(unit_type=UnitType.TANK)
        gm = _make_map()
        assert sys.can_dig(unit, gm) is False

    def test_dead_unit_cannot_dig(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit(hp=0)
        gm = _make_map()
        assert sys.can_dig(unit, gm) is False

    def test_on_water_terrain_cannot_dig(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit()
        gm = _make_map(terrain=TerrainType.WATER)
        assert sys.can_dig(unit, gm) is False

    def test_on_road_terrain_cannot_dig(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit()
        gm = _make_map(terrain=TerrainType.ROAD)
        assert sys.can_dig(unit, gm) is False

    def test_on_open_terrain_can_dig(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit()
        gm = _make_map(terrain=TerrainType.OPEN)
        assert sys.can_dig(unit, gm) is True

    def test_on_rough_terrain_can_dig(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit()
        gm = _make_map(terrain=TerrainType.ROUGH)
        assert sys.can_dig(unit, gm) is True

    def test_already_in_trench_cannot_dig(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit()
        gm = _make_map()
        # Manually add trench decoration to simulate existing trench
        gm.tiles_enhanced["10,10"] = {'decorations': [{'type': DecorationType.TRENCH_SECTION.name}]}
        assert sys.can_dig(unit, gm) is False

    def test_sniper_can_dig(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit(unit_type=UnitType.SNIPER_TEAM)
        gm = _make_map()
        assert sys.can_dig(unit, gm) is True

    def test_mg_squad_can_dig(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit(unit_type=UnitType.MACHINE_GUN_SQUAD)
        gm = _make_map()
        assert sys.can_dig(unit, gm) is True


# ---------------------------------------------------------------------------
# Test: TrenchDiggingSystem — start_digging / tick / interrupt
# ---------------------------------------------------------------------------

class TestDiggingProcess:
    def test_start_digging_creates_progress(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit()
        _make_map()
        assert sys.start_digging(unit) is True
        prog = sys.get_progress("u1")
        assert prog is not None
        assert prog.progress == 0
        assert prog.position == TileCoord(10, 10)

    def test_double_start_returns_false(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit()
        sys.start_digging(unit)
        assert sys.start_digging(unit) is False

    def test_tick_advances_progress(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit()
        gm = _make_map()
        sys.start_digging(unit)
        for _ in range(10):
            sys.tick(unit, gm)
        prog = sys.get_progress("u1")
        assert prog is not None
        assert prog.progress == 10

    def test_completion_after_duration_ticks(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit()
        gm = _make_map()
        sys.start_digging(unit)
        completed = False
        for i in range(DIG_DURATION + 5):
            if sys.tick(unit, gm):
                completed = True
                break
        assert completed is True
        # Progress should be removed after completion
        assert sys.get_progress("u1") is None

    def test_interrupt_resets_progress(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit()
        gm = _make_map()
        sys.start_digging(unit)
        # Advance some progress
        for _ in range(30):
            sys.tick(unit, gm)
        assert sys.get_progress("u1") is not None
        # Interrupt
        sys.interrupt("u1")
        assert sys.get_progress("u1") is None

    def test_movement_interrupts_digging(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit(x=10, y=10)
        gm = _make_map()
        sys.start_digging(unit)
        # Simulate movement by changing position
        unit.position.tile_coord = TileCoord(11, 11)
        result = sys.tick(unit, gm)
        assert result is False  # Not completed
        assert sys.get_progress("u1") is None  # Interrupted

    def test_completion_creates_trench_decoration(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit(x=15, y=20)
        gm = _make_map()
        # Pre-initialize enhanced tile data so completion can write to it
        gm.tiles_enhanced["15,20"] = {'decorations': []}
        sys.start_digging(unit)
        for _ in range(DIG_DURATION):
            sys.tick(unit, gm)
        # Check that trench decoration was added
        enhanced = gm.get_enhanced_tile(15, 20)
        assert enhanced is not None
        decorations = enhanced.get('decorations', [])
        trench_types = [d for d in decorations if d.get('type') == DecorationType.TRENCH_SECTION.name]
        assert len(trench_types) >= 1

    def test_tick_without_start_returns_false(self):
        sys = TrenchDiggingSystem()
        unit = _make_unit()
        gm = _make_map()
        assert sys.tick(unit, gm) is False

    def test_active_digs_property(self):
        sys = TrenchDiggingSystem()
        u1 = _make_unit(uid="u1", x=5, y=5)
        u2 = _make_unit(uid="u2", x=10, y=10)
        _make_map()
        sys.start_digging(u1)
        sys.start_digging(u2)
        assert len(sys.active_digs) == 2


# ---------------------------------------------------------------------------
# Test: TrenchDiggingAI — evaluate heuristic
# ---------------------------------------------------------------------------

class TestTrenchDiggingAIEvaluate:
    def test_no_infantry_returns_zero(self):
        ai = TrenchDiggingAI()
        tank = _make_unit(unit_type=UnitType.TANK)
        ctx = _make_context(friendly=[tank])
        assert ai.evaluate(ctx) == 0.0

    def test_dead_infantry_returns_zero(self):
        ai = TrenchDiggingAI()
        dead = _make_unit(hp=0)
        ctx = _make_context(friendly=[dead])
        assert ai.evaluate(ctx) == 0.0

    def test_stationary_infantry_positive_score(self):
        ai = TrenchDiggingAI()
        inf = _make_unit()
        ctx = _make_context(friendly=[inf])
        score = ai.evaluate(ctx)
        assert score > 0.0

    def test_enemy_nearby_reduces_score(self):
        ai = TrenchDiggingAI()
        inf = _make_unit(x=5, y=5)
        enemy = _make_unit(uid="e1", faction=Faction.AXIS, x=6, y=5)  # Very close!
        ctx_far = _make_context(friendly=[inf])
        ctx_near = _make_context(friendly=[inf], enemy=[enemy])
        score_far = ai.evaluate(ctx_far)
        score_near = ai.evaluate(ctx_near)
        assert score_near < score_far  # Enemy pressure reduces digging priority

    def test_multiple_candidates_increases_score(self):
        ai = TrenchDiggingAI()
        infs = [_make_unit(uid=f"u{i}", x=i*3, y=i*3) for i in range(4)]
        ctx_few = _make_context(friendly=[infs[0]])
        ctx_many = _make_context(friendly=infs)
        assert ai.evaluate(ctx_many) > ai.evaluate(ctx_few)


# ---------------------------------------------------------------------------
# Test: TrenchDiggingAI — execute issues dig orders
# ---------------------------------------------------------------------------

class TestTrenchDiggingAIExecute:
    def test_issues_dig_intent_for_stationary_unit(self):
        ai = TrenchDiggingAI()
        inf = _make_unit()
        # Create context with blackboard showing stationary > threshold
        ctx = _make_context(friendly=[inf])
        from pycc2.domain.ai.blackboard import Blackboard
        bb = Blackboard()
        bb.set('stationary_ticks', STATIONARY_THRESHOLD + 10)
        ctx.blackboards = {"u1": bb}
        intents = ai.execute(ctx)
        assert len(intents) >= 1
        assert intents[0].tactic_type.name == 'DIG_TRENCH'

    def test_no_intent_if_not_stationary_long_enough(self):
        ai = TrenchDiggingAI()
        inf = _make_unit()
        ctx = _make_context(friendly=[inf])
        from pycc2.domain.ai.blackboard import Blackboard
        bb = Blackboard()
        bb.set('stationary_ticks', STATIONARY_THRESHOLD - 5)  # Not enough
        ctx.blackboards = {"u1": bb}
        intents = ai.execute(ctx)
        assert len(intents) == 0

    def test_low_priority_background_action(self):
        ai = TrenchDiggingAI()
        inf = _make_unit()
        ctx = _make_context(friendly=[inf])
        from pycc2.domain.ai.blackboard import Blackboard
        bb = Blackboard()
        bb.set('stationary_ticks', STATIONARY_THRESHOLD + 10)
        ctx.blackboards = {"u1": bb}
        intents = ai.execute(ctx)
        assert intents[0].priority == 3  # Low priority as specified


# ---------------------------------------------------------------------------
# Integration: Full digging lifecycle
# ---------------------------------------------------------------------------

class TestFullLifecycle:
    def test_dig_lifecycle_from_ai_to_completion(self):
        """Simulate full cycle: AI evaluates → issues order → system digs → completes."""
        # Setup
        sys = TrenchDiggingSystem()
        ai = TrenchDiggingAI()
        unit = _make_unit(x=8, y=12)
        gm = _make_map()

        # Phase 1: AI evaluation (should want to dig)
        ctx = _make_context(friendly=[unit], game_map=gm)
        from pycc2.domain.ai.blackboard import Blackboard
        bb = Blackboard()
        bb.set('stationary_ticks', STATIONARY_THRESHOLD + 50)
        ctx.blackboards = {unit.id: bb}

        score = ai.evaluate(ctx)
        assert score > 0.0  # AI wants to dig

        # Phase 2: AI executes → produces DIG_TRENCH intent
        intents = ai.execute(ctx)
        assert len(intents) >= 1

        # Phase 3: System starts digging
        assert sys.can_dig(unit, gm) is True
        # Pre-initialize enhanced tile data for completion to write to
        gm.tiles_enhanced["8,12"] = {'decorations': []}
        sys.start_digging(unit)

        # Phase 4: Tick until complete
        completed = False
        for _ in range(DIG_DURATION + 1):
            if sys.tick(unit, gm):
                completed = True
                break
        assert completed is True

        # Phase 5: Verify trench exists on map
        enhanced = gm.get_enhanced_tile(8, 12)
        assert enhanced is not None
        decorations = enhanced.get('decorations', [])
        assert any(d['type'] == DecorationType.TRENCH_SECTION.name for d in decorations)

    def test_multiple_units_dig_simultaneously(self):
        sys = TrenchDiggingSystem()
        units = [
            _make_unit(uid=f"u{i}", x=i*5, y=i*5) for i in range(3)
        ]
        gm = _make_map()

        # Pre-initialize enhanced tile data for all unit positions
        for u in units:
            key = f"{u.position.tile_coord.x},{u.position.tile_coord.y}"
            gm.tiles_enhanced[key] = {'decorations': []}

        for u in units:
            sys.start_digging(u)

        # Advance all simultaneously
        completions = 0
        for _ in range(DIG_DURATION + 1):
            for u in units:
                if sys.tick(u, gm):
                    completions += 1

        assert completions == 3  # All three should complete
        # All should have trenches
        for u in units:
            enhanced = gm.get_enhanced_tile(u.position.tile_coord.x, u.position.tile_coord.y)
            assert enhanced is not None
            decorations = enhanced.get('decorations', [])
            assert any(d['type'] == DecorationType.TRENCH_SECTION.name for d in decorations)
