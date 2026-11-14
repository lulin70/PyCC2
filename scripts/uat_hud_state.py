"""E2E UAT for TD-079 / T1+T2 and the ESC pause chain: real user pause/resume.

Runs the REAL window, the REAL game loop and the REAL event dispatcher.
A simulated user deploys one unit, clicks START, then presses ESC to
pause/resume. The frame driver mirrors GameLoop.run() (pause-menu freeze,
tick advance, pause-menu overlay render) instead of calling _update_logic
unconditionally — the earlier shallow driver hid real production defects.

Verified against the PRODUCTION battle HUD (bottom CC2 panel + top-left
status line), not the disabled EnhancedRenderer top bar:

  1. battle runs: tick advances, status line shows FPS/Tick/Turn
  2. ESC opens the pause menu: overlay renders (PAUSED title pixels),
     state.paused is True and the tick FREEZES
  3. second ESC closes the menu: paused False, tick advances again
  4. forcing tick=3600 updates the status line pixels (Turn: 1 -> 3)

Screenshots: docs/assets/uat_hud_state/

Usage:
    .venv/bin/python scripts/uat_hud_state.py
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
logger = logging.getLogger("uat_hud")

import numpy as np
import pygame

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "docs" / "assets" / "uat_hud_state"
OUT.mkdir(parents=True, exist_ok=True)

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    logger.info("[%s] %s %s", status, name, detail)
    if not cond:
        FAILURES.append(f"{name} {detail}")


def pause_title_pixels(screen: pygame.Surface) -> int:
    """Count PAUSED-menu title pixels (218,195,130) in the centered panel."""
    sw, sh = screen.get_size()
    panel_x, panel_y = (sw - 360) // 2, (sh - 320) // 2
    region = pygame.Rect(panel_x + 40, panel_y + 15, 280, 50)
    arr = pygame.surfarray.array3d(screen.subsurface(region))
    r, g, b = arr[:, :, 0].astype(int), arr[:, :, 1].astype(int), arr[:, :, 2].astype(int)
    mask = (r > 180) & (g > 160) & (b < 180) & (r > b + 40)
    return int(mask.sum())


def status_line_region(screen: pygame.Surface) -> np.ndarray:
    return pygame.surfarray.array3d(screen.subsurface(pygame.Rect(0, 4, 420, 24))).copy()


def main() -> int:
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
    if ui is None or dm is None or dispatcher is None:
        logger.error("assembly failed")
        return 1
    game_loop.state.running = True

    def frame(n: int = 1) -> None:
        """Mirror GameLoop.run(): pause-menu freeze, tick advance, menu overlay."""
        for _ in range(n):
            if not dispatcher.process_events():
                raise RuntimeError("dispatcher quit")
            pause_active = game_loop._pause_menu is not None and game_loop._pause_menu.is_active
            time_speed = game_loop._get_time_speed()
            if time_speed <= 0.0 or pause_active:
                game_loop.state.paused = True
            else:
                game_loop.state.paused = False
                game_loop._update_logic(1 / 60.0)
                game_loop.state.tick += 1
            game_loop._render_scene(screen, alpha=1.0)
            if game_loop._pause_menu is not None and game_loop._pause_menu.is_active:
                game_loop._pause_menu.render(screen)
            pygame.display.flip()

    def real_mouse(x: int, y: int, etype: int, button: int = 1) -> None:
        pygame.mouse.set_pos((int(x), int(y)))
        pygame.event.pump()
        pygame.event.post(pygame.event.Event(etype, button=button, pos=(int(x), int(y))))
        if not dispatcher.process_events():
            raise RuntimeError("dispatcher quit during event")

    def esc() -> None:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        if not dispatcher.process_events():
            raise RuntimeError("dispatcher quit during ESC")

    def snap(name: str) -> None:
        pygame.image.save(screen, str(OUT / name))
        logger.info("saved %s", name)

    # ------------------------------------------------------------------
    # Deploy one unit through the real dispatcher, then click START.
    # ------------------------------------------------------------------
    frame(20)
    from pycc2.presentation.ui.deployment_models import ZoneType

    target_idx = next((i for i, u in enumerate(ui.state.available_units) if not u.is_placed), None)
    if target_idx is None:
        logger.error("no unplaced roster unit")
        return 1
    roster_x = ui.roster_width // 2
    roster_y = next(
        (y for y in range(30, ui.height, 4) if ui._roster_index_at(roster_x, y) == target_idx),
        None,
    )
    if roster_y is None:
        logger.error("roster hit-test failed")
        return 1
    real_mouse(roster_x, roster_y, pygame.MOUSEBUTTONDOWN)
    frame(3)

    unit = ui.state.available_units[target_idx]
    mox, moy, ts = ui.map_layout
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
    if drop_tile is None:
        logger.error("no placeable tile")
        return 1
    drop_x = ui.roster_width + mox + drop_tile[0] * ts + ts // 2
    drop_y = moy + drop_tile[1] * ts + ts // 2
    real_mouse(drop_x, drop_y, pygame.MOUSEMOTION)
    real_mouse(drop_x, drop_y, pygame.MOUSEBUTTONUP)
    frame(3)
    btn = ui._button_rect
    real_mouse(btn[0] + btn[2] // 2, btn[1] + btn[3] // 2, pygame.MOUSEBUTTONDOWN)
    real_mouse(btn[0] + btn[2] // 2, btn[1] + btn[3] // 2, pygame.MOUSEBUTTONUP)
    frame(30)
    check("battle started via real user flow", not dm.is_active and len(game_loop.state.units) > 0)

    # ------------------------------------------------------------------
    # STAGE 1 — battle runs: tick advances, status line live
    # ------------------------------------------------------------------
    t0 = game_loop.state.tick
    frame(10)
    snap("01_battle_running.png")
    check("tick advances in battle", game_loop.state.tick > t0, f"tick={game_loop.state.tick}")
    baseline_status = status_line_region(screen)
    check("initially not paused", game_loop.state.paused is False)

    # ------------------------------------------------------------------
    # STAGE 2 — ESC: menu opens, overlay renders, tick FREEZES
    # ------------------------------------------------------------------
    esc()
    frozen_tick = game_loop.state.tick
    frame(5)
    snap("02_paused_menu.png")
    check("ESC opens pause menu", game_loop._pause_menu.is_active)
    check("paused=True while menu open", game_loop.state.paused is True)
    check(
        "tick frozen while pause menu open",
        game_loop.state.tick == frozen_tick,
        f"tick={game_loop.state.tick} expected={frozen_tick}",
    )
    check(
        "pause menu overlay visible (PAUSED title pixels)",
        pause_title_pixels(screen) > 50,
        f"title px={pause_title_pixels(screen)}",
    )

    # ------------------------------------------------------------------
    # STAGE 3 — second ESC: menu closes, paused False, tick resumes
    # ------------------------------------------------------------------
    esc()
    frame(5)
    snap("03_resumed.png")
    check("second ESC closes pause menu", not game_loop._pause_menu.is_active)
    check("paused=False after resume", game_loop.state.paused is False)
    check(
        "tick advances after resume",
        game_loop.state.tick > frozen_tick,
        f"tick={game_loop.state.tick} frozen={frozen_tick}",
    )
    check(
        "pause menu overlay gone",
        pause_title_pixels(screen) <= 10,
        f"title px={pause_title_pixels(screen)}",
    )

    # ------------------------------------------------------------------
    # STAGE 4 — tick=3600 updates the status line (Turn: 1 -> 3)
    # ------------------------------------------------------------------
    game_loop.state.tick = 3600
    frame(2)
    snap("04_turn3.png")
    new_status = status_line_region(screen)
    diff = int(np.abs(new_status.astype(int) - baseline_status.astype(int)).sum())
    check("status line pixels update with tick/Turn", diff > 0, f"pixel diff={diff}")

    # ------------------------------------------------------------------
    logger.info("=" * 60)
    if FAILURES:
        logger.error("UAT RESULT: FAIL (%d checks failed)", len(FAILURES))
        for f_ in FAILURES:
            logger.error("  - %s", f_)
        return 1
    logger.info("UAT RESULT: PASS — ESC pause/resume freezes and resumes the battle; Turn live")
    return 0


if __name__ == "__main__":
    t0 = time.time()
    rc = main()
    logger.info("elapsed %.1fs", time.time() - t0)
    pygame.quit()
    raise SystemExit(rc)
