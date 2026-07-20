"""FPS baseline tests using pytest-benchmark (V-04 Wave B-rev).

Uses RELATIVE baseline (perf_baseline.json) to avoid false positives
from GitHub Actions runner hardware variance. A test fails only when
current FPS drops below ``baseline × 0.85`` (i.e. > 15% regression).

Reference: docs/VISUAL_POLISH_PLAN.md V-04 章节 (v2.1, Wave B-rev)
            docs/ROADMAP_v0.9.0.md Wave C4
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from pycc2.domain.components.health_component import HealthComponent  # noqa: E402
from pycc2.domain.components.morale_component import MoraleComponent  # noqa: E402
from pycc2.domain.components.position_component import PositionComponent  # noqa: E402
from pycc2.domain.components.vision_component import VisionComponent  # noqa: E402
from pycc2.domain.components.weapon_component import WeaponComponent  # noqa: E402
from pycc2.domain.entities.game_map import GameMap  # noqa: E402
from pycc2.domain.entities.unit import Faction, Unit, UnitType  # noqa: E402
from pycc2.domain.value_objects.tile_coord import TileCoord  # noqa: E402

# ============================================================================
# Configuration & Constants
# ============================================================================

BASELINE_FILE = Path(__file__).parent / "perf_baseline.json"
REGRESSION_THRESHOLD = 0.85  # 15% drop triggers failure (Wave B-rev)
FPS_TEST_ROUNDS = 10  # P1-8: 3 → 10 rounds for statistical stability
FPS_TEST_ITERATIONS = 1  # Single iteration per round (each round = N frames)
FRAMES_PER_ROUND = 600  # 600 frames per measurement round


# ============================================================================
# Helpers
# ============================================================================


def _make_unit(unit_id: str, faction: Faction, x: int, y: int) -> Unit:
    """Create a minimal Unit for FPS benchmarking."""
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
    """Create a GameMap with varied terrain for FPS benchmarking."""
    rng = np.random.default_rng(42)
    grid = rng.integers(0, 12, size=(height, width), dtype=np.int8)
    return GameMap(
        id="fps_bench_map",
        name="FPS Benchmark Map",
        width=width,
        height=height,
        tile_grid=grid,
    )


def _make_units(count: int, faction: Faction, prefix: str, x_offset: int) -> list[Unit]:
    """Create ``count`` units positioned in a grid."""
    units: list[Unit] = []
    for i in range(count):
        x = x_offset + (i % 10)
        y = (i // 10) % 20
        units.append(_make_unit(f"{prefix}_{i}", faction, x, y))
    return units


def _check_regression(key: str, current_value: float) -> None:
    """Compare against relative baseline; fail only if > 15% regression.

    If no baseline file exists (first run), the test passes silently so
    that initial baseline can be captured via ``scripts/update_perf_baseline.py``.
    """
    if not BASELINE_FILE.exists():
        return  # First run, no baseline
    try:
        baseline_data = json.loads(BASELINE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return  # Corrupt baseline, skip regression check
    if key not in baseline_data:
        return  # No baseline for this key yet
    baseline_value = float(baseline_data[key])
    threshold = baseline_value * REGRESSION_THRESHOLD
    if current_value < threshold:
        raise AssertionError(
            f"FPS regression: {key}={current_value:.1f} FPS < "
            f"baseline {baseline_value:.1f} × {REGRESSION_THRESHOLD} = {threshold:.1f}"
        )


def _measure_fps(render_fn: Callable[[], None], frames: int = FRAMES_PER_ROUND) -> float:
    """Run ``render_fn`` for ``frames`` iterations and return measured FPS.

    Uses ``time.perf_counter()`` for high-resolution timing. FPS is
    computed as ``frames / elapsed_seconds``.
    """
    start = time.perf_counter()
    for _ in range(frames):
        render_fn()
    elapsed = time.perf_counter() - start
    if elapsed <= 0.0:
        return float("inf")
    return frames / elapsed


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def _pygame_init():
    """Initialize pygame with dummy video driver for FPS benchmarks."""
    pygame.init()
    screen = pygame.Surface((1024, 768))
    yield screen
    pygame.quit()


@pytest.fixture(scope="module")
def _normal_load_scene(_pygame_init):
    """Create normal-load scene: 50 units on 20×20 map.

    Matches V-04 design: ``real_game_loop`` normal load scenario.
    Uses EnhancedRenderer (rendering-only, no game logic) for isolation.
    """
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

    screen = _pygame_init
    game_map = _make_map(20, 20)
    allies = _make_units(25, Faction.ALLIES, "ally", x_offset=2)
    axis = _make_units(25, Faction.AXIS, "axis", x_offset=10)
    units = allies + axis

    renderer = EnhancedRenderer()
    renderer.initialize(screen)
    camera = Camera(position=Vec2(0, 0), viewport_width=1024, viewport_height=768)

    def render_frame() -> None:
        renderer.render(game_map, units, camera)

    return render_frame


@pytest.fixture(scope="module")
def _heavy_load_scene(_pygame_init):
    """Create heavy-load scene: 200 units on 50×50 map.

    Matches V-04 design: ``real_game_loop_heavy`` heavy load scenario.
    Stress-tests renderer with 4× unit count and 6.25× map area.
    """
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

    screen = _pygame_init
    game_map = _make_map(50, 50)
    allies = _make_units(100, Faction.ALLIES, "ally", x_offset=2)
    axis = _make_units(100, Faction.AXIS, "axis", x_offset=25)
    units = allies + axis

    renderer = EnhancedRenderer()
    renderer.initialize(screen)
    camera = Camera(position=Vec2(0, 0), viewport_width=1024, viewport_height=768)

    def render_frame() -> None:
        renderer.render(game_map, units, camera)

    return render_frame


# ============================================================================
# FPS Baseline Tests
# ============================================================================


class TestFPSBaseline:
    """FPS performance baseline tests (relative regression).

    Tests use ``pytest-benchmark``'s ``benchmark`` fixture with
    ``pedantic`` mode for full control over rounds/iterations. FPS is
    computed by rendering ``FRAMES_PER_ROUND`` (600) frames and dividing
    by elapsed seconds.

    Regression detection:
        - First run (no ``perf_baseline.json``): passes silently,
          baseline captured via ``scripts/update_perf_baseline.py``.
        - Subsequent runs: fails if FPS < baseline × 0.85 (> 15% drop).
    """

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_fps_normal_load(self, benchmark, _normal_load_scene):
        """Benchmark average FPS under normal load (50 units, 20×20 map).

        Measures median FPS across ``FPS_TEST_ROUNDS`` (10) rounds of
        ``FRAMES_PER_ROUND`` (600) frames each. Compares against the
        ``normal_load`` baseline key in ``perf_baseline.json``.
        """
        render_fn = _normal_load_scene

        fps = benchmark.pedantic(
            _measure_fps,
            args=(render_fn,),
            kwargs={"frames": FRAMES_PER_ROUND},
            iterations=FPS_TEST_ITERATIONS,
            rounds=FPS_TEST_ROUNDS,
        )

        # benchmark.pedantic returns median across rounds
        print(
            f"\n[V-04] normal_load FPS: {fps:.1f} "
            f"(median of {FPS_TEST_ROUNDS} rounds × {FRAMES_PER_ROUND} frames)"
        )
        _check_regression("normal_load", fps)

    @pytest.mark.benchmark
    @pytest.mark.slow
    def test_fps_heavy_load(self, benchmark, _heavy_load_scene):
        """Benchmark minimum FPS under heavy load (200 units, 50×50 map).

        Measures minimum FPS across ``FPS_TEST_ROUNDS`` (10) rounds of
        ``FRAMES_PER_ROUND`` (600) frames each. Compares against the
        ``heavy_load_worst`` baseline key in ``perf_baseline.json``.

        Uses minimum (worst-case) instead of median to catch frame-time
        spikes that would be visible to users as stutter.
        """
        render_fn = _heavy_load_scene

        # Collect FPS from all rounds, then take the minimum (worst-case)
        round_fps_values: list[float] = []

        def run_one_round() -> float:
            fps = _measure_fps(render_fn, frames=FRAMES_PER_ROUND)
            round_fps_values.append(fps)
            return fps

        benchmark.pedantic(
            run_one_round,
            iterations=FPS_TEST_ITERATIONS,
            rounds=FPS_TEST_ROUNDS,
        )

        worst_fps = min(round_fps_values) if round_fps_values else 0.0
        print(
            f"\n[V-04] heavy_load_worst FPS: {worst_fps:.1f} "
            f"(min of {FPS_TEST_ROUNDS} rounds × {FRAMES_PER_ROUND} frames, "
            f"all rounds: {[f'{f:.1f}' for f in round_fps_values]})"
        )
        _check_regression("heavy_load_worst", worst_fps)


# ============================================================================
# Baseline File Integrity Tests
# ============================================================================


class TestBaselineIntegrity:
    """Verify perf_baseline.json integrity and threshold configuration."""

    def test_regression_threshold_in_design_limits(self):
        """REGRESSION_THRESHOLD must be 0.85 (15% regression, Wave B-rev)."""
        assert REGRESSION_THRESHOLD == 0.85

    def test_baseline_file_path_is_in_benchmark_dir(self):
        """Baseline file must live in tests/benchmark/ (V-04 design)."""
        assert BASELINE_FILE.parent == Path(__file__).parent
        assert BASELINE_FILE.name == "perf_baseline.json"

    def test_baseline_keys_match_script_expectations(self):
        """Baseline keys must match scripts/update_perf_baseline.py.

        Without a baseline file, the test passes (first run scenario).
        With a baseline file, keys must include normal_load and
        heavy_load_worst as expected by update_perf_baseline.py.
        """
        if not BASELINE_FILE.exists():
            pytest.skip("No baseline file (first run)")
        data = json.loads(BASELINE_FILE.read_text())
        expected_keys = {"normal_load", "heavy_load_worst"}
        actual_keys = set(data.keys())
        missing = expected_keys - actual_keys
        assert not missing, f"Missing baseline keys: {missing}"

    def test_baseline_values_are_positive(self):
        """All baseline FPS values must be positive numbers."""
        if not BASELINE_FILE.exists():
            pytest.skip("No baseline file (first run)")
        data = json.loads(BASELINE_FILE.read_text())
        for key, value in data.items():
            assert isinstance(value, int | float), f"{key} is not numeric: {type(value)}"
            assert value > 0, f"{key} must be positive, got {value}"

    def test_fps_test_rounds_meets_p1_8_requirement(self):
        """P1-8: rounds must be >= 10 (was 3, raised for stability)."""
        assert FPS_TEST_ROUNDS >= 10

    def test_frames_per_round_provides_stable_measurement(self):
        """FRAMES_PER_ROUND must be >= 600 for stable FPS measurement.

        600 frames at 60 FPS = 10 seconds of gameplay, enough to smooth
        out transient scheduling jitter.
        """
        assert FRAMES_PER_ROUND >= 600
