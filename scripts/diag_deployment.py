"""Diagnose the campaign deployment black-map report (aalsmeer_flank).

Reproduces the production campaign path with the real map, renders a few
deployment frames, and dumps:

* camera position / zoom / viewport vs. map world extent
* render-pipeline exceptions (normally swallowed by TD-039)
* deployment UI roster/zone state
* screenshots for evidence

Usage:
    .venv/bin/python scripts/diag_deployment.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")
logger = logging.getLogger("diag")

import pygame

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "docs" / "assets" / "diag_deployment"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    import traceback

    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.infrastructure.events.event_bus import EventBus
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.window_config import DisplayInfo, WindowManager
    from pycc2.services.ai_service import AIService
    from pycc2.services.game_loop import GameLoop, GameState

    pygame.init()
    wm = WindowManager(DisplayInfo(base_width=1280, base_height=720))
    screen = wm.initialize()

    map_path = ROOT / "data" / "maps" / "aalsmeer_flank.json"
    logger.info("Loading map: %s", map_path.stem)
    game_map = GameMap.from_json(map_path)
    logger.info("Map %dx%d tiles", game_map.width, game_map.height)

    # Reproduce main.py's camera math verbatim (16 px/tile at HEAD).
    camera = Camera(
        position=Vec2(game_map.width * 16.0, game_map.height * 16.0),
        viewport_width=1280,
        viewport_height=720,
    )
    logger.info(
        "Camera pos=(%.0f, %.0f) zoom=%.2f viewport=%dx%d",
        camera.position.x, camera.position.y, camera.zoom,
        camera.viewport_width, camera.viewport_height,
    )

    event_bus = EventBus()
    ai_service = AIService(event_bus=event_bus)

    # Import main's object factory for full fidelity.
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
        logger.info("Scenario loaded: %s", scenario.get("scenario_id"))

    # Real settings object matching what the menu produces.
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

    logger.info("Entering deployment phase")
    game_loop.start_deployment(map_data=map_data, faction="allied", game_settings=settings)

    dm = game_loop._deployment_manager
    ui = dm.deployment_ui if dm else None
    logger.info("deployment active=%s ui=%s", dm.is_active if dm else None, bool(ui))

    # Render three frames directly through the shared render path, catching
    # the TD-039-swallowed exceptions.
    for i in range(3):
        try:
            game_loop._render_scene(screen, alpha=1.0)
            pygame.display.flip()
            pygame.image.save(screen, str(OUT / f"frame_{i}.png"))
            logger.info("frame %d rendered", i)
        except Exception:
            logger.error("frame %d render raised:\n%s", i, traceback.format_exc())

    # PF-14 reproduction: run the REAL update+render cycle (deployment active).
    # Before the fix, _update_fog_of_war ran with 0 observers and the fog
    # overlay blacked out the whole map on the next render.
    game_loop.state.running = True
    for i in range(12):
        try:
            game_loop._update_logic(1 / 60.0)
            game_loop._render_scene(screen, alpha=1.0)
        except Exception:
            logger.error("loop step %d raised:\n%s", i, traceback.format_exc())
            break
    pygame.display.flip()
    pygame.image.save(screen, str(OUT / "frame_loop.png"))
    logger.info("loop frame rendered after _update_logic cycles")

    # Pixel evidence: the terrain around the friendly spawn must not be black.
    try:
        import pygame as pg

        center_px = (screen.get_width() // 2, screen.get_height() // 2)
        samples = [
            center_px,
            (center_px[0] - 100, center_px[1]),
            (center_px[0] + 100, center_px[1]),
        ]
        for px in samples:
            r, g, b, _ = screen.get_at(px)
            bright = max(r, g, b)
            logger.info("pixel %s rgb=(%d,%d,%d) brightness=%d", px, r, g, b, bright)
    except Exception:
        logger.error("pixel sampling failed:\n%s", traceback.format_exc())

    # Dump deployment UI internals.
    if ui is not None:
        roster = getattr(ui, "_roster_items", None) or getattr(ui, "roster", None)
        logger.info(
            "ui tile_size=%s map_offset=(%s,%s) roster_items=%s",
            getattr(ui, "tile_size", "?"),
            getattr(ui, "map_offset_x", "?"), getattr(ui, "map_offset_y", "?"),
            len(roster) if roster else "?",
        )
        zones = getattr(ui, "_zone_tiles", None)
        logger.info("zone tiles: %s", len(zones) if zones else zones)

    # Dump what camera sees in world px.
    tile_px = 48
    world_w = game_map.width * tile_px
    world_h = game_map.height * tile_px
    logger.info(
        "world extent at 48px/tile: %dx%d px; camera center=(%.0f, %.0f) -> "
        "camera is at %.0f%% x, %.0f%% y of the map",
        world_w, world_h, camera.position.x, camera.position.y,
        100.0 * camera.position.x / world_w, 100.0 * camera.position.y / world_h,
    )

    # Try the click chain: select first roster unit, place on a friendly tile.
    if ui is not None and dm is not None:
        try:
            from pycc2.presentation.ui.deployment_models import DeploymentUnit, ZoneType

            # PF-14 evidence: camera-aligned layout must exist and world (0,0)
            # must project onto the layout's map origin.
            layout = ui.map_layout
            assert layout is not None, "map_layout not set — align_camera_to_layout did not run"
            mox, moy, ts = layout
            origin = camera.world_to_screen(Vec2(0.0, 0.0))
            logger.info(
                "map_layout=(%d,%d,ts=%d); projected map origin=(%.1f,%.1f) "
                "expected=(%d,%d)",
                mox, moy, ts, origin[0], origin[1],
                ui.roster_width + mox, moy,
            )
            assert abs(origin[0] - (ui.roster_width + mox)) <= 1.0
            assert abs(origin[1] - moy) <= 1.0

            # 1. Find a draggable roster unit and its screen position.
            target_idx = next(
                (i for i, u in enumerate(ui.state.available_units) if not u.is_placed),
                None,
            )
            assert target_idx is not None, "no unplaced roster units"
            roster_x = ui.roster_width // 2
            roster_y = None
            for y in range(30, ui.height, 4):
                if ui._roster_index_at(roster_x, y) == target_idx:
                    roster_y = y
                    break
            assert roster_y is not None, "roster hit-test failed for unit"
            logger.info("roster unit %d at screen (%d,%d)", target_idx, roster_x, roster_y)

            # 2. Find a placeable friendly-zone tile and its screen position.
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
            assert drop_tile is not None, "no placeable friendly tile found"
            drop_x = ui.roster_width + mox + drop_tile[0] * ts + ts // 2
            drop_y = moy + drop_tile[1] * ts + ts // 2
            logger.info("drop tile %s at screen (%d,%d)", drop_tile, drop_x, drop_y)

            # 3. Simulate the real drag: mouse down on roster, move, drop on map.
            res_down = ui.handle_mouse_down(
                roster_x, roster_y, map_offset_x=mox, map_offset_y=moy, tile_size=ts
            )
            logger.info("handle_mouse_down -> %s", res_down)
            assert res_down == f"drag_start:{target_idx}"
            ui.handle_mouse_move(drop_x, drop_y, mox, moy, ts)
            res_up = ui.handle_mouse_up(
                drop_x, drop_y, map_offset_x=mox, map_offset_y=moy, tile_size=ts
            )
            logger.info("handle_mouse_up -> %s", res_up)
            assert res_up == f"place_unit:{target_idx}", (
                f"drop did not place on {drop_tile} (got {res_up})"
            )
            placed = ui.state.placed_units[-1]
            assert placed.position == drop_tile, f"placed at {placed.position}, want {drop_tile}"

            # 4. Click START through the full click handler.
            bx, by, bw, bh = ui._button_rect
            res_btn = ui.handle_click_full(
                bx + bw // 2, by + bh // 2, mox, moy, ts
            )
            logger.info("start-button click -> %s", res_btn)
            assert res_btn == "begin_battle"

            # 5. Complete deployment through the game loop; camera recenters.
            result = game_loop.complete_deployment()
            logger.info("complete_deployment -> %s", bool(result))
            assert result is not None, "complete_deployment returned None"
            assert not dm.is_active, "deployment still active after complete"
            logger.info(
                "battle camera center=(%.0f,%.0f) zoom=%.2f",
                camera.position.x, camera.position.y, camera.zoom,
            )
            logger.info("CLICK CHAIN PASS: select -> drag -> place -> START -> battle")
        except Exception:
            logger.error("click chain FAILED:\n%s", traceback.format_exc())
            pygame.quit()
            return 1

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
