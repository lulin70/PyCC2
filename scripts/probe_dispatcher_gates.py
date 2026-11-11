"""Probe: which dispatcher pre-handlers consume events during deployment?"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "src"))

import json
import logging

logging.basicConfig(level=logging.WARNING)

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.systems.game_settings import (
    ExperienceLevel,
    GameSettings,
    SideSettings,
    SupplyLevelSetting,
)
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.main import _create_game_objects
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.window_config import DisplayInfo, WindowManager
from pycc2.services.ai_service import AIService


def main() -> None:
    pygame.init()
    wm = WindowManager(DisplayInfo(base_width=1280, base_height=720))
    screen = wm.initialize()
    game_map = GameMap.from_json(ROOT / "data" / "maps" / "aalsmeer_flank.json")
    camera = Camera(
        position=Vec2(game_map.width * 16.0, game_map.height * 16.0),
        viewport_width=1280,
        viewport_height=720,
    )
    event_bus = EventBus()
    objects = _create_game_objects(
        game_map, camera, screen, wm, event_bus, AIService(event_bus=event_bus)
    )
    game_loop = objects["game_loop"]
    d = game_loop._event_dispatcher

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
    scen = ROOT / "data" / "scenarios" / "aalsmeer_flank.json"
    if scen.exists():
        s = json.loads(scen.read_text())
        map_data.update(
            victory_locations=s.get("victory_locations", []),
            forces=s.get("forces", {}),
            special_rules=s.get("special_rules", []),
            scenario_id=s.get("scenario_id", ""),
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

    print("=== dispatcher gates during deployment ===")
    print(f"deployment_manager.is_active = {d.deployment_manager.is_active}")
    print(f"deployment_ui present      = {d.deployment_manager.deployment_ui is not None}")
    t = d.tutorial_overlay
    print(f"tutorial_overlay           = {t!r}")
    print(f"tutorial visible           = {t.visible if t else None}")
    print(f"tutorial system enabled    = {t.system.enabled if t else None}")
    print(f"pause_menu.is_active       = {d.pause_menu.is_active}")
    sm = d.settings_menu
    print(f"settings_menu.visible      = {sm.visible if sm else None}")
    cu = getattr(d, "_campaign_ui_ref", None)
    print(f"campaign_ui ref            = {cu!r}, is_visible={cu.is_visible if cu else None}")

    # Feed one left-click at the roster area and see what each gate returns.
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(120, 62))
    print("\n=== per-handler verdicts for MOUSEBUTTONDOWN(120,62) ===")
    print(f"_handle_campaign_ui   -> {d._handle_campaign_ui(ev)}")
    print(f"_handle_settings_menu -> {d._handle_settings_menu(ev)}")
    print(f"_handle_global_keys   -> {d._handle_global_keys(ev)}")
    print(f"_handle_tutorial      -> {d._handle_tutorial(ev)}")
    print(f"_handle_pause_menu    -> {d._handle_pause_menu(ev)}")
    ui = d.deployment_manager.deployment_ui
    print(f"ui._drag_drop.is_dragging after full chain = {ui._drag_drop.is_dragging}")
    pygame.quit()


if __name__ == "__main__":
    main()
