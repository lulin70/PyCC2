"""PF-03: real-window FPS measurement (no SDL dummy driver).

Opens the real game window through ``WindowManager`` (SCALED + DOUBLEBUF +
vsync, base 1280x720) and measures render+flip throughput on the same
normal/heavy scenes used by ``tests/benchmark/test_fps_baseline.py``.

Usage:
    .venv/bin/python scripts/real_window_perf.py
    .venv/bin/python scripts/real_window_perf.py --width 1024 --height 768 \
        --rounds 5 --frames 600

The script never sets ``SDL_VIDEODRIVER``; if the session has no display it
exits with a clear error instead of silently measuring the dummy driver.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np
import pygame

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

BASELINE_FILE = Path(__file__).parent.parent / "tests" / "benchmark" / "perf_baseline.json"
REGRESSION_THRESHOLD = 0.75


def _make_unit(unit_id: str, faction: Faction, x: int, y: int) -> Unit:
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
    rng = np.random.default_rng(42)
    grid = rng.integers(0, 12, size=(height, width), dtype=np.int8)
    return GameMap(
        id="real_window_map",
        name="Real window map",
        width=width,
        height=height,
        tile_grid=grid,
    )


def _make_units(count: int, faction: Faction, prefix: str, x_offset: int) -> list[Unit]:
    return [
        _make_unit(f"{prefix}_{i}", faction, x_offset + (i % 10), (i // 10) % 20)
        for i in range(count)
    ]


def _build_scene(name: str, size: tuple[int, int]) -> tuple[object, object, object]:
    if name == "normal_load":
        game_map = _make_map(20, 20)
        units = _make_units(25, Faction.ALLIES, "ally", 2) + _make_units(
            25, Faction.AXIS, "axis", 10
        )
    else:
        game_map = _make_map(50, 50)
        units = _make_units(100, Faction.ALLIES, "ally", 2) + _make_units(
            100, Faction.AXIS, "axis", 25
        )
    renderer = EnhancedRenderer()
    renderer.initialize(pygame.display.get_surface())
    camera = Camera(position=Vec2(0, 0), viewport_width=size[0], viewport_height=size[1])
    return game_map, units, (renderer, camera)


def _measure(render_fn, frames: int) -> float:
    start = time.perf_counter()
    for _ in range(frames):
        render_fn()
    elapsed = time.perf_counter() - start
    return frames / elapsed if elapsed > 0 else float("inf")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--frames", type=int, default=600)
    args = parser.parse_args()

    from pycc2.presentation.rendering.window_config import DisplayInfo, WindowManager

    pygame.init()
    driver = pygame.display.get_driver()
    if driver == "dummy":
        print(f"ERROR: dummy video driver ({driver}); no real window available")
        return 2

    wm = WindowManager(DisplayInfo(base_width=args.width, base_height=args.height))
    screen = wm.initialize()
    size = (screen.get_width(), screen.get_height())
    pygame.display.set_caption("PyCC2 PF-03 real-window FPS")
    print(
        f"driver={driver} window={size[0]}x{size[1]} "
        f"dpi_scale={wm.display_info.dpi_scale:.2f} rounds={args.rounds} frames={args.frames}"
    )

    baseline = {}
    if BASELINE_FILE.exists():
        baseline = json.loads(BASELINE_FILE.read_text())

    results: dict[str, dict[str, float]] = {}
    for scene_name in ("normal_load", "heavy_load"):
        game_map, units, (renderer, camera) = _build_scene(scene_name, size)
        samples: list[float] = []

        def draw(_map=game_map, _units=units, _renderer=renderer, _camera=camera) -> None:
            _renderer.render(_map, _units, _camera)
            pygame.display.flip()

        # Warm-up round, then measured rounds.
        _measure(draw, max(30, args.frames // 10))
        for _ in range(args.rounds):
            pygame.event.pump()
            samples.append(_measure(draw, args.frames))

        results[scene_name] = {
            "median_fps": statistics.median(samples),
            "worst_fps": min(samples),
            "best_fps": max(samples),
        }

    print("\nscene         median    worst     best   baseline  verdict")
    for scene_name, data in results.items():
        key = "normal_load" if scene_name == "normal_load" else "heavy_load_worst"
        ref = baseline.get(key)
        value = data["median_fps"] if scene_name == "normal_load" else data["worst_fps"]
        if ref is None:
            verdict = "n/a"
        else:
            verdict = "PASS" if value >= float(ref) * REGRESSION_THRESHOLD else "FAIL"
        ref_text = f"{float(ref):.1f}" if ref is not None else "-"
        print(
            f"{scene_name:<12} {data['median_fps']:8.1f} {data['worst_fps']:8.1f} "
            f"{data['best_fps']:8.1f} {ref_text:>9}   {verdict}"
        )

    out = {
        "driver": driver,
        "window": list(size),
        "rounds": args.rounds,
        "frames_per_round": args.frames,
        "results": results,
        "baseline": baseline,
    }
    out_path = Path(__file__).parent.parent / "tmp" / "real_window_perf.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nsaved: {out_path}")

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
