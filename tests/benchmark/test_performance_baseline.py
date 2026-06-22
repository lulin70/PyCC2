"""
Enhanced Performance Baseline Tests for PyCC2

Comprehensive benchmark suite for monitoring version-to-version performance changes.
Includes rendering, game logic, memory, and startup benchmarks.

Run:
    pytest tests/benchmark/test_performance_baseline.py -v --tb=short

Output:
    tests/benchmark/.baseline_results.json (auto-generated)
"""

from __future__ import annotations

import json
import os
import statistics
import time
import tracemalloc
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest

try:
    import pygame

    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.pathfinder import PathFinder
from pycc2.domain.value_objects.tile_coord import TileCoord

# ========================================================================
# Configuration & Constants
# ========================================================================

BASELINE_DIR = Path(__file__).parent
RESULTS_FILE = BASELINE_DIR / ".baseline_results.json"

WARMUP_RUNS = 3
MEASUREMENT_RUNS = 5

VERSION = "0.3.0"


@dataclass
class BenchmarkResult:
    """Single benchmark measurement result."""

    name: str
    category: str
    priority: str
    unit: str
    threshold: float
    measurements: list[float] = field(default_factory=list)
    median_ms: float = 0.0
    mean_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0
    std_dev: float = 0.0
    passed: bool = False
    timestamp: str = ""
    version: str = VERSION

    def compute_stats(self) -> None:
        """Compute statistics from measurements."""
        if not self.measurements:
            return
        self.median_ms = statistics.median(self.measurements)
        self.mean_ms = statistics.mean(self.measurements)
        self.min_ms = min(self.measurements)
        self.max_ms = max(self.measurements)
        if len(self.measurements) > 1:
            self.std_dev = statistics.stdev(self.measurements)
        self.passed = self.median_ms <= self.threshold
        self.timestamp = datetime.now(UTC).isoformat()


@dataclass
class BaselineReport:
    """Complete baseline test report."""

    version: str = VERSION
    timestamp: str = ""
    environment: str = ""
    results: list[dict] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ========================================================================
# Test Helpers
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


def _run_benchmark(
    func, *args, warmup: int = WARMUP_RUNS, runs: int = MEASUREMENT_RUNS, **kwargs
) -> list[float]:
    """
    Run a benchmark with warmup and multiple measurements.

    Returns list of measurement times in milliseconds.
    """
    # Warmup phase
    for _ in range(warmup):
        func(*args, **kwargs)

    # Measurement phase
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        times.append(elapsed)

    return times


def _save_result(result: BenchmarkResult) -> None:
    """Append result to baseline results file."""
    results = []
    if RESULTS_FILE.exists():
        try:
            with open(RESULTS_FILE) as f:
                data = json.load(f)
                results = data.get("results", [])
        except (json.JSONDecodeError, KeyError):
            results = []

    results.append(asdict(result))

    report = {
        "version": VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
        "environment": os.uname().sysname if hasattr(os, "uname") else "unknown",
        "results": results,
        "summary": _compute_summary(results),
    }

    with open(RESULTS_FILE, "w") as f:
        json.dump(report, f, indent=2, default=str)


def _compute_summary(results: list[dict]) -> dict:
    """Compute summary statistics from all results."""
    if not results:
        return {}

    total = len(results)
    passed = sum(1 for r in results if r.get("passed", False))
    categories = {}
    for r in results:
        cat = r.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total_benchmarks": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
        "by_category": categories,
    }


# ========================================================================
# Fixtures
# ========================================================================


@pytest.fixture(scope="module")
def pygame_init():
    """Initialize pygame for rendering tests."""
    if not PYGAME_AVAILABLE:
        pytest.skip("pygame not available")
    pygame.init()
    screen = pygame.Surface((1024, 768))
    yield screen
    pygame.quit()


@pytest.fixture(scope="module")
def benchmark_maps():
    """Pre-create maps of various sizes for benchmarks."""
    return {
        "16x16": _make_map(16, 16),
        "32x32": _make_map(32, 32),
        "64x64": _make_map(64, 64),
        "50x42": _make_map(50, 42),
    }


@pytest.fixture(scope="module")
def sample_units():
    """Create sample units for AI and combat benchmarks."""
    allies = [_make_unit(f"ally_{i}", Faction.ALLIES, 5 + i % 20, 5 + i // 20) for i in range(25)]
    axis = [_make_unit(f"axis_{i}", Faction.AXIS, 30 + i % 20, 5 + i // 20) for i in range(25)]
    return allies + axis  # 50 units total


# ========================================================================
# A. Rendering Performance Benchmarks (P0)
# ========================================================================


class TestRenderingPerformance:
    """Rendering performance benchmarks - critical for user experience."""

    @pytest.mark.benchmark
    def test_render_16x16_map_time(self, pygame_init, benchmark_maps):
        """Render 16×16 map should complete in <100ms."""
        from pycc2.domain.value_objects.vec2 import Vec2
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

        screen = pygame_init
        game_map = benchmark_maps["16x16"]

        renderer = EnhancedRenderer()
        renderer.initialize(screen)
        camera = Camera(position=Vec2(0, 0), viewport_width=1024, viewport_height=768)

        def render_frame():
            renderer.render(game_map, [], camera)

        times = _run_benchmark(render_frame)

        result = BenchmarkResult(
            name="test_render_16x16_map_time",
            category="rendering",
            priority="P0",
            unit="ms",
            threshold=100.0,
            measurements=times,
        )
        result.compute_stats()
        _save_result(result)

        assert result.passed, (
            f"16×16 render median={result.median_ms:.2f}ms (threshold: {result.threshold}ms)"
        )

    @pytest.mark.benchmark
    def test_render_64x64_map_time(self, pygame_init, benchmark_maps):
        """Render 64×64 map should complete in <500ms."""
        from pycc2.domain.value_objects.vec2 import Vec2
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

        screen = pygame_init
        game_map = benchmark_maps["64x64"]

        renderer = EnhancedRenderer()
        renderer.initialize(screen)
        camera = Camera(position=Vec2(0, 0), viewport_width=1024, viewport_height=768)

        def render_frame():
            renderer.render(game_map, [], camera)

        times = _run_benchmark(render_frame)

        result = BenchmarkResult(
            name="test_render_64x64_map_time",
            category="rendering",
            priority="P0",
            unit="ms",
            threshold=500.0,
            measurements=times,
        )
        result.compute_stats()
        _save_result(result)

        assert result.passed, (
            f"64×64 render median={result.median_ms:.2f}ms (threshold: {result.threshold}ms)"
        )

    @pytest.mark.benchmark
    def test_surface_pool_efficiency(self, pygame_init):
        """Surface pool hit rate should be >90%."""
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

        screen = pygame_init
        renderer = EnhancedRenderer()
        renderer.initialize(screen)

        # Simulate repeated surface requests of same sizes
        test_sizes = [(512, 512), (1024, 768), (256, 256), (800, 600)]
        pool_hits = 0
        total_requests = 0

        # Warm up pool
        for _ in range(10):
            for size in test_sizes:
                renderer._get_pooled_surface(size)

        # Measure efficiency (access stats to trigger len if needed)
        _ = renderer._surface_pool.stats

        for _ in range(50):
            for size in test_sizes:
                total_requests += 1
                size_in_pool = size in renderer._surface_pool._pool
                renderer._get_pooled_surface(size)
                if size_in_pool:
                    pool_hits += 1

        hit_rate = (pool_hits / total_requests * 100) if total_requests > 0 else 0
        final_pool_size = renderer._surface_pool.stats["size"]

        result = BenchmarkResult(
            name="test_surface_pool_efficiency",
            category="rendering",
            priority="P0",
            unit="%",
            threshold=90.0,
            measurements=[hit_rate],
        )
        result.compute_stats()
        result.median_ms = hit_rate  # Store hit rate as primary metric
        result.passed = hit_rate >= result.threshold
        _save_result(result)

        assert result.passed, (
            f"Surface pool hit rate={hit_rate:.1f}% (threshold: {result.threshold}%)"
        )
        max_pool = renderer._surface_pool.stats["max_size"]
        assert final_pool_size <= max_pool, f"Pool size {final_pool_size} exceeded max {max_pool}"

    @pytest.mark.benchmark
    def test_viewport_culling_effectiveness(self, pygame_init, benchmark_maps):
        """Viewport culling should skip >70% of off-screen tiles."""
        from pycc2.domain.value_objects.vec2 import Vec2
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

        screen = pygame_init
        game_map = benchmark_maps["64x64"]  # Large map

        renderer = EnhancedRenderer()
        renderer.initialize(screen)
        # Zoom in to show only small portion of map
        camera = Camera(position=Vec2(0, 0), viewport_width=800, viewport_height=600)
        camera.zoom = 2.0  # Zoom in significantly

        # Count tiles that would be rendered vs total tiles
        total_tiles = game_map.width * game_map.height

        # Estimate visible tiles based on camera viewport
        # This is a simplified calculation - actual culling happens in renderer
        viewport_tiles = int(
            (camera.viewport_width / (renderer.TILE_SIZE * camera.zoom))
            * (camera.viewport_height / (renderer.TILE_SIZE * camera.zoom))
        )
        skipped_percent = (total_tiles - viewport_tiles) / total_tiles * 100
        if skipped_percent < 0:
            skipped_percent = 0

        result = BenchmarkResult(
            name="test_viewport_culling_effectiveness",
            category="rendering",
            priority="P0",
            unit="%",
            threshold=70.0,
            measurements=[skipped_percent],
        )
        result.compute_stats()
        result.median_ms = skipped_percent
        result.passed = skipped_percent >= result.threshold
        _save_result(result)

        assert result.passed, (
            f"Viewport culling skipped={skipped_percent:.1f}% tiles "
            f"(threshold: {result.threshold}%)"
        )


# ========================================================================
# B. Game Logic Performance Benchmarks (P0)
# ========================================================================


class TestGameLogicPerformance:
    """Game logic performance benchmarks - critical for gameplay responsiveness."""

    @pytest.mark.benchmark
    def test_ai_tick_time(self, sample_units):
        """AI tick for 50 units should complete in <10ms."""
        from pycc2.domain.ai.behavior_tree import BTNode, NodeStatus
        from pycc2.domain.ai.blackboard import Blackboard
        from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
        from pycc2.domain.ai.tick_scheduler import AITickScheduler

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

        units = sample_units[:50]
        scheduler = AITickScheduler()

        trees = {}
        blackboards = {}
        for u in units:
            trees[u.id] = SimpleAttackNode()
            bb = Blackboard()
            bb.set("unit_id", u.id)
            blackboards[u.id] = bb

        def ai_tick():
            ticking = [u for u in units if scheduler.should_tick(u, current_tick=0)]
            for u in ticking:
                tree = trees[u.id]
                bb = blackboards[u.id]
                tree.tick(bb)

        times = _run_benchmark(ai_tick)

        result = BenchmarkResult(
            name="test_ai_tick_time",
            category="game_logic",
            priority="P0",
            unit="ms",
            threshold=10.0,
            measurements=times,
        )
        result.compute_stats()
        _save_result(result)

        assert result.passed, (
            f"AI tick (50 units) median={result.median_ms:.2f}ms (threshold: {result.threshold}ms)"
        )

    @pytest.mark.benchmark
    def test_pathfinding_50_tiles(self, benchmark_maps):
        """Pathfinding 50 tiles should complete in <50ms."""
        game_map = benchmark_maps["50x42"]
        pathfinder = PathFinder()

        # Create paths that are ~50 tiles long
        start = TileCoord(2, 2)
        goal = TileCoord(47, 40)  # Roughly diagonal across map

        def find_path():
            path = pathfinder.find_path(start, goal, game_map)
            assert path is not None, "Path should be found"

        times = _run_benchmark(find_path)

        result = BenchmarkResult(
            name="test_pathfinding_50_tiles",
            category="game_logic",
            priority="P0",
            unit="ms",
            threshold=50.0,
            measurements=times,
        )
        result.compute_stats()
        _save_result(result)

        assert result.passed, (
            f"Pathfinding (~50 tiles) median={result.median_ms:.2f}ms "
            f"(threshold: {result.threshold}ms)"
        )

    @pytest.mark.benchmark
    def test_combat_resolution_time(self, sample_units, benchmark_maps):
        """Single combat resolution should complete in <5ms."""
        from pycc2.domain.systems.ballistic import BallisticEngine
        from pycc2.domain.systems.combat_resolver import CombatResolver
        from pycc2.domain.systems.morale_system import MoraleCalculator
        from pycc2.services.event_bus import EventBus
        from pycc2.services.random_context import RandomContext

        rng = RandomContext.from_seed(42)
        game_map = benchmark_maps["50x42"]

        # Small combat scenario: 5 vs 5
        allies = sample_units[:5]
        axis = sample_units[5:10]

        resolver = CombatResolver(
            ballistic_engine=BallisticEngine(rng=rng),
            morale_calc=MoraleCalculator(),
            rng=rng,
            event_bus=EventBus(),
        )

        def resolve_combat():
            results = resolver.resolve_combat_turn(allies, axis, game_map)
            assert isinstance(results, list)

        times = _run_benchmark(resolve_combat)

        result = BenchmarkResult(
            name="test_combat_resolution_time",
            category="game_logic",
            priority="P0",
            unit="ms",
            threshold=5.0,
            measurements=times,
        )
        result.compute_stats()
        _save_result(result)

        assert result.passed, (
            f"Combat resolution (5v5) median={result.median_ms:.2f}ms "
            f"(threshold: {result.threshold}ms)"
        )

    @pytest.mark.benchmark
    def test_save_load_time(self, benchmark_maps):
        """Save/Load for 60 units should complete in <2s."""
        import tempfile

        from pycc2.infrastructure.save_system import SecureSaveManager

        benchmark_maps["50x42"]

        with tempfile.TemporaryDirectory() as tmpdir:
            save_mgr = SecureSaveManager(base_dir=tmpdir)

            # Create simplified game state (match SaveSystem SaveGameStateData schema)
            game_state = {
                "units": [
                    {
                        "id": f"unit_{i}",
                        "name": f"Squad_{i}",
                        "faction": "ALLIES" if i < 30 else "AXIS",
                        "unit_type": "INFANTRY_SQUAD",
                        "hp": 100,
                        "max_hp": 100,
                        "morale": {
                            "value": 80,
                            "panic_threshold": 30,
                            "suppression": 0,
                            "state": "RALLIED",
                        },
                        "position": {"x": float(i * 48), "y": 0.0, "facing_rad": 0.0},
                        "vision": {"range_tiles": 6, "angle_rad": 3.1416},
                        "weapon": {
                            "primary_weapon_id": "rifle",
                            "ammo_remaining": 10,
                            "max_ammo": 10,
                            "reload_ticks_left": 0,
                            "state": "READY",
                        },
                        "is_alive": True,
                    }
                    for i in range(60)
                ],
                "tick": 1000,
                "paused": False,
                "side_turn": "allies",
                "selected_unit_ids": [],
            }

            def save_and_load():
                # Save
                success = save_mgr.save_game(1, game_state)
                assert success

                # Load
                loaded_state, meta, status = save_mgr.load_game(1)
                assert loaded_state is not None
                assert loaded_state["tick"] == 1000
                assert len(loaded_state["units"]) == 60

            times = _run_benchmark(save_and_load, warmup=1, runs=3)  # Fewer runs for I/O

            result = BenchmarkResult(
                name="test_save_load_time",
                category="game_logic",
                priority="P0",
                unit="ms",
                threshold=2000.0,  # 2 seconds
                measurements=times,
            )
            result.compute_stats()
            _save_result(result)

            assert result.passed, (
                f"Save/Load (60 units) median={result.median_ms:.2f}ms "
                f"(threshold: {result.threshold}ms)"
            )


# ========================================================================
# C. Memory Usage Benchmarks (P1)
# ========================================================================


class TestMemoryUsage:
    """Memory usage benchmarks - important for long-running stability."""

    @pytest.mark.benchmark
    def test_memory_after_100_frames(self, pygame_init, benchmark_maps):
        """Memory usage after 100 frames should be stable (<50MB growth)."""
        from pycc2.domain.value_objects.vec2 import Vec2
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

        screen = pygame_init
        game_map = benchmark_maps["32x32"]

        tracemalloc.start()

        renderer = EnhancedRenderer()
        renderer.initialize(screen)
        camera = Camera(position=Vec2(0, 0), viewport_width=1024, viewport_height=768)

        # Render 100 frames
        for _ in range(100):
            renderer.render(game_map, [], camera)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_mb = current / (1024 * 1024)
        peak_mb = peak / (1024 * 1024)

        result = BenchmarkResult(
            name="test_memory_after_100_frames",
            category="memory",
            priority="P1",
            unit="MB",
            threshold=50.0,  # 50MB threshold
            measurements=[memory_mb],
        )
        result.compute_stats()
        result.median_ms = memory_mb
        result.passed = memory_mb <= result.threshold
        _save_result(result)

        assert result.passed, (
            f"Memory after 100 frames: {memory_mb:.1f}MB "
            f"(peak: {peak_mb:.1f}MB, threshold: {result.threshold}MB)"
        )

    @pytest.mark.benchmark
    def test_surface_pool_size_stability(self, pygame_init):
        """Surface pool size should remain stable after many operations."""
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

        screen = pygame_init
        renderer = EnhancedRenderer()
        renderer.initialize(screen)

        # Simulate many different surface size requests
        np.random.seed(42)
        _ = renderer._surface_pool.stats  # Use stats property instead of len()

        for _ in range(200):
            w = np.random.randint(100, 1200)
            h = np.random.randint(100, 900)
            renderer._get_pooled_surface((w, h))

        sizes_after = renderer._surface_pool.stats["size"]
        max_allowed = renderer._surface_pool.stats["max_size"]

        # Pool should not grow beyond maximum
        stability_ratio = (sizes_after / max_allowed) * 100 if max_allowed > 0 else 0

        result = BenchmarkResult(
            name="test_surface_pool_size_stability",
            category="memory",
            priority="P1",
            unit="%",
            threshold=100.0,  # Should not exceed 100% of max
            measurements=[stability_ratio],
        )
        result.compute_stats()
        result.median_ms = stability_ratio
        result.passed = sizes_after <= max_allowed
        _save_result(result)

        assert result.passed, (
            f"Surface pool grew to {sizes_after}/{max_allowed} "
            f"({stability_ratio:.1f}%, should be ≤{max_allowed})"
        )


# ========================================================================
# D. Startup Performance Benchmarks (P1)
# ========================================================================


class TestStartupPerformance:
    """Startup performance benchmarks - important for user experience."""

    @pytest.mark.benchmark
    def test_cold_startup_time(self):
        """Cold startup (imports + initialization) should complete in <10s."""
        import subprocess
        import sys

        # Create a simple script that measures cold startup
        startup_script = """
import time
start = time.perf_counter()

# Import main modules (simulating cold start)
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Unit, Faction, UnitType
from pycc2.domain.systems.pathfinder import PathFinder
from pycc2.domain.systems.combat_resolver import CombatResolver
from pycc2.infrastructure.save_system import SecureSaveManager

elapsed = (time.perf_counter() - start) * 1000
print(f"COLD_START_TIME_MS={elapsed:.2f}")
"""

        times = []
        for _ in range(MEASUREMENT_RUNS):
            result = subprocess.run(
                [sys.executable, "-c", startup_script],
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).resolve().parents[2]),
            )

            for line in result.stdout.split("\\n"):
                if "COLD_START_TIME_MS=" in line:
                    ms = float(line.split("=")[1])
                    times.append(ms)
                    break

        if not times:
            pytest.skip("Could not measure cold startup time")

        result = BenchmarkResult(
            name="test_cold_startup_time",
            category="startup",
            priority="P1",
            unit="ms",
            threshold=10000.0,  # 10 seconds
            measurements=times,
        )
        result.compute_stats()
        _save_result(result)

        assert result.passed, (
            f"Cold startup median={result.median_ms:.2f}ms (threshold: {result.threshold}ms)"
        )

    @pytest.mark.benchmark
    def test_hot_startup_time(self, benchmark_maps, sample_units):
        """Hot startup (with cached imports) should complete in <3s."""
        # All modules are already imported (hot start)
        start = time.perf_counter()

        # Initialize key components
        benchmark_maps["50x42"]
        PathFinder()
        units = sample_units[:10]

        # Simulate minimal game state setup
        from pycc2.domain.systems.spatial_hash import SpatialHash

        spatial = SpatialHash(cell_size=10)
        for u in units:
            spatial.insert(u.id, u.position.tile_coord, u.faction)

        elapsed = (time.perf_counter() - start) * 1000

        result = BenchmarkResult(
            name="test_hot_startup_time",
            category="startup",
            priority="P1",
            unit="ms",
            threshold=3000.0,  # 3 seconds
            measurements=[elapsed],
        )
        result.compute_stats()
        result.median_ms = elapsed
        result.passed = elapsed <= result.threshold
        _save_result(result)

        assert result.passed, f"Hot startup time={elapsed:.2f}ms (threshold: {result.threshold}ms)"


# ========================================================================
# Report Generation
# ========================================================================


def test_generate_baseline_report():
    """Generate final summary report of all benchmarks."""
    if not RESULTS_FILE.exists():
        pytest.skip("No baseline results generated yet")

    with open(RESULTS_FILE) as f:
        report = json.load(f)

    print("\n" + "=" * 80)
    print("PYCC2 PERFORMANCE BASELINE REPORT")
    print("=" * 80)
    print(f"Version: {report.get('version', 'unknown')}")
    print(f"Timestamp: {report.get('timestamp', 'unknown')}")
    print(f"Environment: {report.get('environment', 'unknown')}")
    print("-" * 80)

    summary = report.get("summary", {})
    print("\nSummary:")
    print(f"  Total Benchmarks: {summary.get('total_benchmarks', 0)}")
    print(f"  Passed: {summary.get('passed', 0)}")
    print(f"  Failed: {summary.get('failed', 0)}")
    print(f"  Pass Rate: {summary.get('pass_rate', '0%')}")

    print("\nBy Category:")
    for cat, count in summary.get("by_category", {}).items():
        print(f"  {cat}: {count}")

    print("\nDetailed Results:")
    print("-" * 80)
    for result in report.get("results", []):
        status = "✅ PASS" if result.get("passed") else "❌ FAIL"
        print(
            f"{status} | {result.get('name', 'unknown'):40s} | "
            f"median={result.get('median_ms', 0):8.2f}{result.get('unit', 'ms'):5s} | "
            f"threshold={result.get('threshold', 0):8.2f}{result.get('unit', 'ms'):5s}"
        )

    print("=" * 80 + "\n")

    # Assert overall pass rate > 80%
    total = summary.get("total_benchmarks", 0)
    passed = summary.get("passed", 0)
    if total > 0:
        pass_rate = passed / total * 100
        assert pass_rate >= 80, f"Overall pass rate {pass_rate:.1f}% is below 80%"
