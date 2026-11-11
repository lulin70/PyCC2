"""E2E verification of the campaign deployment screen (PF-14 fix).

Runs the REAL window (no dummy video driver), the REAL map, the REAL game
loop, and simulates a REAL user through the production event dispatcher:

  1. deployment screen renders with a visible map (not black)
  2. mouse down on a roster unit starts a drag
  3. drag and release on a friendly tile places the unit
  4. click START -> dispatcher fires complete_deployment -> battle begins

User input is injected with pygame.mouse.set_pos + pygame.event.post so the
whole chain goes through EventDispatcher.process_events() (production path),
NOT direct UI method calls (the blind spot that missed PF-14).

Screenshots are saved to docs/assets/uat_deploy_e2e/ at every stage.

Usage:
    .venv/bin/python scripts/uat_deploy_e2e.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

# REAL window — no SDL_VIDEODRIVER override here on purpose.

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")
logger = logging.getLogger("uat_e2e")

import pygame

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "docs" / "assets" / "uat_deploy_e2e"
OUT.mkdir(parents=True, exist_ok=True)

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    logger.info("[%s] %s %s", status, name, detail)
    if not cond:
        FAILURES.append(f"{name} {detail}")


def main() -> int:
    import traceback

    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.infrastructure.events.event_bus import EventBus
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.window_config import DisplayInfo, WindowManager
    from pycc2.services.ai_service import AIService
    from pycc2.services.game_loop import GameLoop

    pygame.init()
    wm = WindowManager(DisplayInfo(base_width=1280, base_height=720))
    screen = wm.initialize()
    logger.info("real window opened %dx%d", screen.get_width(), screen.get_height())

    map_path = ROOT / "data" / "maps" / "aalsmeer_flank.json"
    game_map = GameMap.from_json(map_path)
    camera = Camera(
        position=Vec2(game_map.width * 16.0, game_map.height * 16.0),
        viewport_width=1280,
        viewport_height=720,
    )
    event_bus = EventBus()
    ai_service = AIService(event_bus=event_bus)

    from pycc2.main import _create_game_objects

    objects = _create_game_objects(game_map, camera, screen, wm, event_bus, ai_service=ai_service)
    game_loop = objects["game_loop"]
    assert isinstance(game_loop, GameLoop)

    map_data = {
        "width": game_map.width,
        "height": game_map.height,
        "tiles": game_map.tile_grid.tolist(),
        "spawn_points": [
            {
                "id": sp.id,
                "side": sp.side,
                "position": [sp.position.x, sp.position.y],
                "units_max": sp.units_max,
            }
            for sp in game_map.spawn_points
        ],
    }
    scenario_path = ROOT / "data" / "scenarios" / "aalsmeer_flank.json"
    if scenario_path.exists():
        with open(scenario_path) as f:
            scenario = json.load(f)
        map_data["victory_locations"] = scenario.get("victory_locations", [])
        map_data["forces"] = scenario.get("forces", {})
        map_data["special_rules"] = scenario.get("special_rules", [])
        map_data["scenario_id"] = scenario.get("scenario_id", "")

    from pycc2.domain.systems.game_settings import (
        ExperienceLevel,
        GameSettings,
        SideSettings,
        SupplyLevelSetting,
    )

    settings = GameSettings(
        allied_settings=SideSettings(
            experience_level=ExperienceLevel.REGULAR,
            supply_level=SupplyLevelSetting.ADEQUATE,
        ),
        axis_settings=SideSettings(
            experience_level=ExperienceLevel.REGULAR,
            supply_level=SupplyLevelSetting.ADEQUATE,
        ),
        player_side="allied",
    )

    game_loop.start_deployment(map_data=map_data, faction="allied", game_settings=settings)
    dm = game_loop._deployment_manager
    ui = dm.deployment_ui if dm else None
    dispatcher = game_loop._event_dispatcher
    check("deployment started", dm is not None and dm.is_active and ui is not None)
    if ui is None or dm is None or dispatcher is None:
        logger.error("assembly failed:\n%s", traceback.format_exc())
        return 1

    game_loop.state.running = True

    def frame(n: int = 1) -> None:
        for _ in range(n):
            if not dispatcher.process_events():
                raise RuntimeError("dispatcher quit")
            game_loop._update_logic(1 / 60.0)
            game_loop._render_scene(screen, alpha=1.0)
            pygame.display.flip()

    def real_mouse(x: int, y: int, etype: int, button: int = 1) -> None:
        """Simulate a physical user: warp OS cursor, then inject the event."""
        pygame.mouse.set_pos((int(x), int(y)))
        pygame.event.pump()
        got = pygame.mouse.get_pos()
        check(
            f"cursor warp ({x},{y})",
            abs(got[0] - x) <= 2 and abs(got[1] - y) <= 2,
            f"get_pos={got}",
        )
        ev = pygame.event.Event(etype, button=button, pos=(int(x), int(y)))
        pygame.event.post(ev)
        if not dispatcher.process_events():
            raise RuntimeError("dispatcher quit during event")

    def snap(name: str) -> Path:
        p = OUT / name
        pygame.image.save(screen, str(p))
        logger.info("saved %s", p.name)
        return p

    # ------------------------------------------------------------------
    # STAGE A — deployment screen visible, map not black
    # ------------------------------------------------------------------
    frame(20)
    snap("01_deployment.png")

    layout = ui.map_layout
    check("map_layout aligned", layout is not None, f"layout={layout}")
    mox, moy, ts = layout

    # Sample pixels across the map area (right of roster) for brightness.
    bright_min = 999
    for fx in (0.4, 0.5, 0.6, 0.75):
        for fy in (0.3, 0.5, 0.7):
            px = int(240 + mox + ui._map_width * ts * fx)
            py = int(moy + ui._map_height * ts * fy)
            if px >= screen.get_width() or py >= screen.get_height():
                continue
            r, g, b, _ = screen.get_at((px, py))
            bright_min = min(bright_min, max(r, g, b))
    check("map pixels visible (not black)", bright_min > 25, f"min brightness={bright_min}")

    # ------------------------------------------------------------------
    # STAGE B — mouse down on a roster unit starts a drag
    # ------------------------------------------------------------------
    from pycc2.presentation.ui.deployment_models import ZoneType

    target_idx = next(
        (i for i, u in enumerate(ui.state.available_units) if not u.is_placed), None
    )
    check("roster has unplaced units", target_idx is not None)
    if target_idx is None:
        return 1
    roster_x = ui.roster_width // 2
    roster_y = None
    for y in range(30, ui.height, 4):
        if ui._roster_index_at(roster_x, y) == target_idx:
            roster_y = y
            break
    check("roster hit-test resolves unit", roster_y is not None, f"y={roster_y}")
    if roster_y is None:
        return 1

    real_mouse(roster_x, roster_y, pygame.MOUSEBUTTONDOWN)
    frame(5)
    snap("02_drag_started.png")
    check(
        "drag started via dispatcher",
        ui._drag_drop.is_dragging and ui._drag_drop.dragging_unit_index == target_idx,
        f"dragging={ui._drag_drop.is_dragging}",
    )

    # ------------------------------------------------------------------
    # STAGE C — drag onto a friendly tile and release: unit placed
    # ------------------------------------------------------------------
    unit = ui.state.available_units[target_idx]
    drop_tile = None
    for ty in range(ui._map_height):
        for tx in range(ui._map_width):
            if ui._zone_map is not None and ui._zone_map[ty][tx] != ZoneType.FRIENDLY:
                continue
            if any(pu.position == (tx, ty) for pu in ui.state.placed_units):
                continue
            if ui.can_place_at(unit, tx, ty, ui._get_terrain_at(tx, ty)):
                drop_tile = (tx, ty)
                break
        if drop_tile:
            break
    check("placeable friendly tile found", drop_tile is not None, f"tile={drop_tile}")
    if drop_tile is None:
        return 1
    drop_x = ui.roster_width + mox + drop_tile[0] * ts + ts // 2
    drop_y = moy + drop_tile[1] * ts + ts // 2

    placed_before = len(ui.state.placed_units)
    real_mouse(drop_x, drop_y, pygame.MOUSEMOTION)
    real_mouse(drop_x, drop_y, pygame.MOUSEBUTTONUP)
    frame(5)
    snap("03_unit_placed.png")
    placed = ui.state.placed_units
    check(
        "unit placed via dispatcher drag",
        len(placed) == placed_before + 1 and placed[-1].position == drop_tile,
        f"placed at {placed[-1].position if placed else None}, want {drop_tile}",
    )

    # ------------------------------------------------------------------
    # STAGE D — click START: dispatcher triggers complete_deployment
    # ------------------------------------------------------------------
    frame(3)
    btn = ui._button_rect
    check("start button rect exists", btn is not None, f"rect={btn}")
    if btn is None:
        return 1
    bx, by, bw, bh = btn
    real_mouse(bx + bw // 2, by + bh // 2, pygame.MOUSEBUTTONDOWN)
    real_mouse(bx + bw // 2, by + bh // 2, pygame.MOUSEBUTTONUP)
    frame(30)
    snap("04_battle.png")
    check("deployment closed after START", not dm.is_active)
    check("units spawned into battle", len(game_loop.state.units) > 0, f"units={len(game_loop.state.units)}")

    # ------------------------------------------------------------------
    logger.info("=" * 60)
    if FAILURES:
        logger.error("E2E RESULT: FAIL (%d checks failed)", len(FAILURES))
        for f_ in FAILURES:
            logger.error("  - %s", f_)
        return 1
    logger.info(
        "E2E RESULT: PASS — visible map, selectable roster unit, drag-place "
        "on %s, START -> battle with %d units",
        drop_tile,
        len(game_loop.state.units),
    )
    return 0


if __name__ == "__main__":
    t0 = time.time()
    rc = main()
    logger.info("elapsed %.1fs", time.time() - t0)
    pygame.quit()
    raise SystemExit(rc)
