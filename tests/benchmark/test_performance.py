"""
Performance Benchmark Tests for PyCC2

Measures critical path performance to catch regressions.
All tests are marked with @pytest.mark.benchmark for selective execution.

Run benchmarks only:
    pytest tests/benchmark/ -m benchmark

Run everything except benchmarks:
    pytest -m "not benchmark"
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.spatial_hash import SpatialHash
from pycc2.domain.value_objects.tile_coord import TileCoord

# ========================================================================
# Helpers
# ========================================================================


def _make_unit(unit_id: str, faction: Faction, x: int, y: int) -> Unit:
    """Create a minimal Unit for benchmarking."""
    return Unit(
        id=unit_id,
        name=f"Unit-{unit_id}",
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
    )


def _make_map(width: int, height: int) -> GameMap:
    """Create a GameMap with varied terrain for benchmarking."""
    rng = np.random.default_rng(42)
    grid = rng.integers(0, 12, size=(height, width), dtype=np.int8)
    return GameMap(
        id="bench_map",
        name="Benchmark Map",
        width=width,
        height=height,
        tile_grid=grid,
    )


# ========================================================================
# Benchmark: Map Load Performance
# ========================================================================


@pytest.mark.benchmark
def test_map_load_performance():
    """Loading a 50x42 map should complete in <100ms."""
    start = time.perf_counter()
    game_map = _make_map(50, 42)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert game_map.width == 50
    assert game_map.height == 42
    assert game_map.tile_grid.shape == (42, 50)
    assert elapsed_ms < 100, f"Map load took {elapsed_ms:.1f}ms (limit: 100ms)"


# ========================================================================
# Benchmark: Spatial Hash Query Performance
# ========================================================================


@pytest.mark.benchmark
def test_spatial_hash_query_performance():
    """Querying 5000 units in spatial hash should complete in <5ms."""
    spatial = SpatialHash(cell_size=10)
    rng = np.random.default_rng(123)

    # Insert 5000 units
    for i in range(5000):
        x = int(rng.integers(0, 50))
        y = int(rng.integers(0, 42))
        faction = Faction.ALLIES if i % 2 == 0 else Faction.AXIS
        spatial.insert(f"u{i}", TileCoord(x, y), faction)

    assert spatial.unit_count() == 5000

    # Benchmark 100 radius queries
    start = time.perf_counter()
    for _ in range(100):
        cx = int(rng.integers(0, 50))
        cy = int(rng.integers(0, 42))
        spatial.query_radius(TileCoord(cx, cy), radius=8, exclude_faction=Faction.ALLIES)
    elapsed_ms = (time.perf_counter() - start) * 1000

    avg_ms = elapsed_ms / 100
    assert avg_ms < 5, f"Average spatial query took {avg_ms:.2f}ms (limit: 5ms)"


# ========================================================================
# Benchmark: Combat Turn Performance
# ========================================================================


@pytest.mark.benchmark
def test_combat_turn_performance():
    """Resolving combat for 50 units should complete in <50ms."""
    from pycc2.domain.systems.ballistic import BallisticEngine
    from pycc2.domain.systems.combat_resolver import CombatResolver
    from pycc2.domain.systems.morale_system import MoraleCalculator
    from pycc2.services.event_bus import EventBus
    from pycc2.services.random_context import RandomContext

    rng = RandomContext.from_seed(42)
    game_map = _make_map(50, 42)
    allies = [_make_unit(f"ally_{i}", Faction.ALLIES, 5 + i % 20, 5 + i // 20) for i in range(25)]
    axis = [_make_unit(f"axis_{i}", Faction.AXIS, 30 + i % 20, 5 + i // 20) for i in range(25)]

    resolver = CombatResolver(
        ballistic_engine=BallisticEngine(rng=rng),
        morale_calc=MoraleCalculator(),
        rng=rng,
        event_bus=EventBus(),
    )

    start = time.perf_counter()
    results = resolver.resolve_combat_turn(allies, axis, game_map)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert isinstance(results, list)
    assert elapsed_ms < 50, f"Combat turn took {elapsed_ms:.1f}ms (limit: 50ms)"


# ========================================================================
# Benchmark: AI Tick Performance
# ========================================================================


@pytest.mark.benchmark
def test_ai_tick_performance():
    """AI tick for 30 units should complete in <10ms."""
    from pycc2.domain.ai.behavior_tree import BTNode, NodeStatus
    from pycc2.domain.ai.blackboard import Blackboard
    from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
    from pycc2.domain.ai.tick_scheduler import AITickScheduler

    # Create a simple behavior tree that always succeeds
    class SimpleAttackNode(BTNode):
        def tick(self, bb: Blackboard) -> NodeStatus:
            bb.set(
                "current_intent",
                TacticIntent(
                    unit_id=bb.get("unit_id", "unknown"),
                    tactic_type=TacticType.ATTACK,
                    priority=5,
                ),
            )
            return NodeStatus.SUCCESS

    units = [_make_unit(f"ai_{i}", Faction.AXIS, 10 + i % 10, 10 + i // 10) for i in range(30)]
    scheduler = AITickScheduler()

    # Pre-register units with their trees and blackboards
    trees = {}
    blackboards = {}
    for u in units:
        trees[u.id] = SimpleAttackNode()
        bb = Blackboard()
        bb.set("unit_id", u.id)
        blackboards[u.id] = bb

    start = time.perf_counter()

    # Simulate one AI tick: decide which units act, then tick their trees
    ticking = [u for u in units if scheduler.should_tick(u, current_tick=0)]
    for u in ticking:
        tree = trees[u.id]
        bb = blackboards[u.id]
        tree.tick(bb)

    elapsed_ms = (time.perf_counter() - start) * 1000

    assert len(ticking) >= 1, f"At least 1 unit should be scheduled to tick, got {len(ticking)}"
    assert elapsed_ms < 10, f"AI tick took {elapsed_ms:.2f}ms (limit: 10ms)"
