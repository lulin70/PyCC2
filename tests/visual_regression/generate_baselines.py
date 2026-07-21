"""V-07 Wave C2: Visual regression baseline generator.

Renders 5 core scenarios and saves PNG baselines to
``tests/visual_regression/baselines/<platform>/``.

Usage::

    # Generate baselines for the current platform
    python tests/visual_regression/generate_baselines.py

    # Generate baselines for a specific platform (e.g. CI)
    python tests/visual_regression/generate_baselines.py --platform linux

    # Force overwrite existing baselines
    python tests/visual_regression/generate_baselines.py --force

The script enforces ``SDL_VIDEODRIVER=dummy`` for deterministic headless
rendering. Run it once on each supported platform (linux/macos/windows)
and commit the resulting PNGs.

Scenarios (per V-07 Wave B-rev design):
    1. main_menu            — title screen with version + start prompt
    2. grass_terrain         — 16x16 grass map with a single allied infantry
    3. urban_terrain         — 16x16 urban map with buildings + road grid
    4. post_battle_report    — campaign UI post-battle report (victory)
    5. minimap               — minimap rendering of mixed terrain

Intentional visual changes (V-01 refactor / V-10 Morandi skin) require
re-running this script to refresh baselines.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Set SDL dummy drivers BEFORE any pygame import (mirror conftest.py).
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

# Ensure project root is on sys.path for `python tests/.../script.py` invocation.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from pycc2.domain.components.health_component import HealthComponent  # noqa: E402
from pycc2.domain.components.morale_component import MoraleComponent  # noqa: E402
from pycc2.domain.components.position_component import PositionComponent  # noqa: E402
from pycc2.domain.components.vision_component import VisionComponent  # noqa: E402
from pycc2.domain.components.weapon_component import WeaponComponent  # noqa: E402
from pycc2.domain.entities.game_map import GameMap  # noqa: E402
from pycc2.domain.entities.unit import Faction, Unit, UnitType  # noqa: E402
from pycc2.domain.value_objects.tile_coord import TileCoord  # noqa: E402
from pycc2.domain.value_objects.vec2 import Vec2  # noqa: E402
from pycc2.presentation.rendering.camera import Camera  # noqa: E402
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer  # noqa: E402
from pycc2.presentation.rendering.minimap import Minimap  # noqa: E402
from pycc2.presentation.ui.campaign_ui import CampaignUI  # noqa: E402

logger = logging.getLogger(__name__)

# Constants
SCREEN_W, SCREEN_H = 800, 600
SCENARIO_NAMES = (
    "main_menu",
    "grass_terrain",
    "urban_terrain",
    "post_battle_report",
    "minimap",
)


def _detect_platform() -> str:
    """Map sys.platform to baseline subdirectory name."""
    p = sys.platform.lower()
    if p.startswith("linux"):
        return "linux"
    if p.startswith("darwin"):
        return "macos"
    if p.startswith("win"):
        return "windows"
    return "other"


def _make_screen() -> pygame.Surface:
    """Create a headless pygame screen for rendering."""
    pygame.init()
    pygame.font.init()
    try:
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    except pygame.error:
        screen = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    return screen


def _make_grass_map() -> GameMap:
    """Create a 16x16 grass map (terrain_type=0 = OPEN/GRASS)."""
    grid = np.zeros((16, 16), dtype=np.int8)
    return GameMap(id="grass", name="Grass Map", width=16, height=16, tile_grid=grid)


def _make_urban_map() -> GameMap:
    """Create a 16x16 urban map with roads (1) + buildings (4) pattern."""
    grid = np.zeros((16, 16), dtype=np.int8)
    # Roads in cross pattern
    grid[7, :] = 1
    grid[:, 7] = 1
    # Buildings (solid = 4) clusters
    grid[1:4, 1:4] = 4
    grid[1:4, 10:13] = 4
    grid[10:13, 1:4] = 4
    grid[10:13, 10:13] = 4
    return GameMap(id="urban", name="Urban Map", width=16, height=16, tile_grid=grid)


def _make_mixed_map() -> GameMap:
    """Create a 16x16 mixed terrain map (for minimap scenario)."""
    grid = np.zeros((16, 16), dtype=np.int8)
    grid[0:4, :] = 0  # grass
    grid[4:8, :] = 1  # road
    grid[8:12, :] = 3  # woods
    grid[12:16, :] = 6  # water
    return GameMap(id="mixed", name="Mixed Map", width=16, height=16, tile_grid=grid)


def _make_ally_unit(tile_x: int = 5, tile_y: int = 5) -> Unit:
    """Create a single allied infantry unit."""
    return Unit(
        id="ally_1",
        name="Test Infantry",
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
        vision=VisionComponent(),
        health=HealthComponent(hp=100, max_hp=100),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
        morale=MoraleComponent(value=75),
    )


# ── Scenario renderers ───────────────────────────────────────────────


def render_main_menu(screen: pygame.Surface) -> None:
    """Scenario 1: main menu title screen."""
    screen.fill((20, 25, 35))

    try:
        font_title = pygame.font.SysFont("consolas", 48, bold=True)
        font_normal = pygame.font.SysFont("consolas", 20)
        font_small = pygame.font.SysFont("consolas", 14)
    except (pygame.error, OSError):
        font_title = pygame.font.Font(None, 60)
        font_normal = pygame.font.Font(None, 28)
        font_small = pygame.font.Font(None, 20)

    title = font_title.render("PyCC2", True, (240, 200, 80))
    screen.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 180))

    subtitle = font_normal.render("Close Combat 2 — Python Tribute", True, (200, 200, 220))
    screen.blit(subtitle, (SCREEN_W // 2 - subtitle.get_width() // 2, 250))

    version = font_small.render("v0.8.0 — Test Baseline", True, (140, 140, 160))
    screen.blit(version, (SCREEN_W // 2 - version.get_width() // 2, 290))

    prompt = font_normal.render("Press SPACE to Start", True, (220, 220, 220))
    screen.blit(prompt, (SCREEN_W // 2 - prompt.get_width() // 2, 400))


def render_grass_terrain(screen: pygame.Surface) -> None:
    """Scenario 2: grass terrain with a single allied unit."""
    game_map = _make_grass_map()
    camera = Camera(
        position=Vec2(384.0, 384.0),
        viewport_width=SCREEN_W,
        viewport_height=SCREEN_H,
    )
    renderer = EnhancedRenderer()
    renderer.initialize(screen)
    units = [_make_ally_unit(tile_x=8, tile_y=8)]
    renderer.render(game_map, units, camera)


def render_urban_terrain(screen: pygame.Surface) -> None:
    """Scenario 3: urban terrain with roads and buildings."""
    game_map = _make_urban_map()
    camera = Camera(
        position=Vec2(384.0, 384.0),
        viewport_width=SCREEN_W,
        viewport_height=SCREEN_H,
    )
    renderer = EnhancedRenderer()
    renderer.initialize(screen)
    units = [
        _make_ally_unit(tile_x=5, tile_y=5),
        _make_ally_unit(tile_x=10, tile_y=10),
    ]
    renderer.render(game_map, units, camera)


def render_post_battle_report(screen: pygame.Surface) -> None:
    """Scenario 4: campaign UI post-battle report (victory)."""
    campaign_ui = CampaignUI()
    campaign_ui.initialize()
    # Set a sample battle result (victory) for rendering.
    campaign_ui._battle_result = {
        "victory": True,
        "winner": "allies",
        "battle_name": "Battle of the Bridges",
        "summary": (
            "Allied forces secured the bridge after a coordinated assault. "
            "Enemy resistance collapsed following the loss of their command "
            "post. XXX Corps was able to advance toward the next objective."
        ),
        "casualties": {
            "allies": {"kia": 4, "wounded": 7, "missing": 1},
            "axis": {"kia": 11, "wounded": 5, "missing": 2},
        },
    }
    campaign_ui._state = "report"
    # Directly invoke the report renderer (bypass state-machine dispatch).
    campaign_ui._renderer._render_report(screen)


def render_minimap(screen: pygame.Surface) -> None:
    """Scenario 5: minimap rendering of mixed terrain."""
    screen.fill((10, 12, 18))
    game_map = _make_mixed_map()
    minimap = Minimap(size=200)
    minimap.set_map(game_map)
    minimap.update_units([_make_ally_unit(tile_x=8, tile_y=8)])
    minimap.render(screen, x=SCREEN_W // 2 - 100, y=SCREEN_H // 2 - 100)


SCENARIO_RENDERERS = {
    "main_menu": render_main_menu,
    "grass_terrain": render_grass_terrain,
    "urban_terrain": render_urban_terrain,
    "post_battle_report": render_post_battle_report,
    "minimap": render_minimap,
}


def generate_baselines(
    output_dir: Path, scenarios: list[str], force: bool = False
) -> dict[str, str]:
    """Generate baseline PNGs for the specified scenarios.

    Returns a mapping of scenario -> status ("ok" | "skipped" | "error").
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    screen = _make_screen()
    results: dict[str, str] = {}

    for name in scenarios:
        out_path = output_dir / f"{name}.png"
        if out_path.exists() and not force:
            logger.info("SKIP %s (already exists; use --force to overwrite)", name)
            results[name] = "skipped"
            continue

        renderer_fn = SCENARIO_RENDERERS.get(name)
        if renderer_fn is None:
            logger.error("Unknown scenario: %s", name)
            results[name] = "error"
            continue

        try:
            screen.fill((0, 0, 0))
            renderer_fn(screen)
            pygame.image.save(screen, str(out_path))
            logger.info("OK %s -> %s", name, out_path)
            results[name] = "ok"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to render %s: %s", name, exc)
            results[name] = "error"

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate visual regression baselines for PyCC2 v0.9.0 (V-07)."
    )
    parser.add_argument(
        "--platform",
        default=None,
        help="Baseline platform subdir (linux/macos/windows). "
        "Defaults to auto-detected current platform.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing baseline PNGs.",
    )
    parser.add_argument(
        "--scenario",
        action="append",
        help="Specific scenario to regenerate (can be repeated). Defaults to all 5 scenarios.",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Override baseline root directory. Defaults to tests/visual_regression/baselines/.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    platform = args.platform or _detect_platform()
    output_root = (
        Path(args.output_root) if args.output_root else (Path(__file__).parent / "baselines")
    )
    output_dir = output_root / platform
    scenarios = args.scenario if args.scenario else list(SCENARIO_NAMES)

    logger.info("Platform: %s", platform)
    logger.info("Output dir: %s", output_dir)
    logger.info("Scenarios: %s", ", ".join(scenarios))

    results = generate_baselines(output_dir, scenarios, force=args.force)

    # Summary
    ok = sum(1 for v in results.values() if v == "ok")
    skipped = sum(1 for v in results.values() if v == "skipped")
    errored = sum(1 for v in results.values() if v == "error")
    logger.info("--- Summary ---")
    logger.info("OK: %d  Skipped: %d  Errored: %d", ok, skipped, errored)

    return 0 if errored == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
