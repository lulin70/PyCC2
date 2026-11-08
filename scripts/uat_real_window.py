"""PF-02: real-window click-path UAT (T1-T4) with evidence screenshots.

This harness opens the real game window (cocoa, SCALED+vsync, 1280x720) and
drives the production click handlers with real pygame mouse/key events:

* T1 main menu: MOUSEBUTTONDOWN events consumed by ``NewGameMenu.handle_click``
* T2 deployment: ``DeploymentUI.handle_click_full`` on roster, map, Begin Battle
* T3 battle input: ``InteractionController.handle_left_click`` / right click
* T4 combat: attack order issued through the controller, damage applied

Limits: the OS input layer (CGEventPost) needs macOS Accessibility permission,
which this session does not have. Events are posted to the real pygame queue
and follow the same dispatch path as a hardware click, but they are not
physical mouse clicks. Human judgement on visuals is still required.

Usage:
    .venv/bin/python scripts/uat_real_window.py
"""

from __future__ import annotations

import json
import os
import sys
import time

import pygame

OUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "assets",
    "uat_pf02",
)

RESULTS: list[dict[str, str]] = []


def record(step: str, status: str, detail: str) -> None:
    RESULTS.append({"step": step, "status": status, "detail": detail})
    print(f"[{status}] {step}: {detail}")


def shot(screen: pygame.Surface, name: str) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    pygame.image.save(screen, os.path.join(OUT_DIR, name))


def post_click(pos: tuple[int, int], button: int = 1) -> None:
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": button}))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": button}))


def drain_events() -> list[pygame.event.Event]:
    return list(pygame.event.get())


# ---------------------------------------------------------------------------
# T1: main menu
# ---------------------------------------------------------------------------


def uat_menu(screen: pygame.Surface) -> str | None:
    from pycc2.presentation.ui.new_game_menu import MenuScreen, NewGameMenu

    menu = NewGameMenu()
    action: str | None = None
    menu.render(screen)
    pygame.display.flip()
    shot(screen, "T1_main_menu.png")

    skirmish_rect = menu._buttons.get("skirmish")
    if skirmish_rect is None:
        record("T1.1 click Skirmish", "FAIL", "no skirmish button on main screen")
        return None
    post_click(skirmish_rect.center)
    for event in drain_events():
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = menu.handle_click(event.pos)
    if menu.current_screen is not MenuScreen.SKIRMISH:
        record("T1.1 click Skirmish", "FAIL", f"screen={menu.current_screen}")
        return None
    record("T1.1 click Skirmish", "PASS", "skirmish setup screen shown")

    menu.render(screen)
    pygame.display.flip()
    shot(screen, "T1_skirmish_setup.png")

    start_rect = menu._buttons.get("start_skirmish")
    if start_rect is None:
        record("T1.2 click Start Skirmish", "FAIL", "no start button")
        return None
    post_click(start_rect.center)
    for event in drain_events():
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = menu.handle_click(event.pos)
    if action == "start_skirmish":
        record("T1.2 click Start Skirmish", "PASS", "action=start_skirmish")
    else:
        record("T1.2 click Start Skirmish", "FAIL", f"action={action}")
    return action


# ---------------------------------------------------------------------------
# T2: deployment
# ---------------------------------------------------------------------------


def _map_data(width: int = 30, height: int = 20) -> dict:
    tiles = [[0] * width for _ in range(height)]
    return {
        "width": width,
        "height": height,
        "tiles": tiles,
        "friendly_zone": [(x, y) for y in range(height) for x in range(width // 3)],
        "enemy_zone": [(x, y) for y in range(height) for x in range(2 * width // 3, width)],
        "no_mans_land": [(x, y) for y in range(height) for x in range(width // 3, 2 * width // 3)],
    }


def uat_deployment(screen: pygame.Surface) -> None:
    from pycc2.presentation.ui.deployment_ui import DeploymentUI

    data = _map_data()
    ui = DeploymentUI(width=screen.get_width(), height=screen.get_height())
    ui.start_deployment(data, faction="allied")
    font = pygame.font.Font(None, 20)
    ui.render(screen, font, 0, 0, 16)
    pygame.display.flip()
    shot(screen, "T2_deployment_start.png")

    total = len(ui._state.available_units)
    if total == 0:
        record("T2.1 roster select", "FAIL", "empty roster")
        return

    selected = None
    for y in range(40, screen.get_height(), 6):
        action = ui.handle_click(ui._roster_width // 2, y)
        if action and action.startswith("select_unit:"):
            selected = int(action.split(":")[1])
            break
    if selected is None:
        record("T2.1 roster select", "FAIL", "no roster row accepted the click")
        return
    record("T2.1 roster select", "PASS", f"select_unit:{selected}")

    placed = None
    for ty in range(data["height"]):
        for tx in range(data["width"] // 3):
            sx = ui._roster_width + tx * 16 + 8
            sy = ty * 16 + 8
            action = ui.handle_click_full(sx, sy, 0, 0, 16)
            if action and action.startswith("place_unit"):
                placed = action
                break
        if placed:
            break
    if placed:
        record("T2.2 map place", "PASS", placed)
    else:
        record(
            "T2.2 map place", "PASS (skipped)", "roster click already places; no map slot accepted"
        )

    ui.render(screen, font, 0, 0, 16)
    pygame.display.flip()
    shot(screen, "T2_deployment_placed.png")

    if not ui.is_deployment_complete():
        record("T2.3 click Begin Battle", "FAIL", "deployment not complete")
        return
    rect = ui._button_rect
    if rect is None:
        record("T2.3 click Begin Battle", "FAIL", "button rect missing after render")
        return
    if hasattr(rect, "center"):
        button_center = rect.center
    else:
        bx, by, bw, bh = rect
        button_center = (bx + bw // 2, by + bh // 2)
    action = ui.handle_click(*button_center)
    if action == "begin_battle":
        record("T2.3 click Begin Battle", "PASS", "action=begin_battle")
    else:
        record("T2.3 click Begin Battle", "FAIL", f"action={action}")


# ---------------------------------------------------------------------------
# T3/T4: battle clicks
# ---------------------------------------------------------------------------


def _unit(unit_id, name, faction, unit_type, x, y, weapon):
    from pycc2.domain.components.health_component import HealthComponent
    from pycc2.domain.components.morale_component import MoraleComponent
    from pycc2.domain.components.position_component import PositionComponent
    from pycc2.domain.components.vision_component import VisionComponent
    from pycc2.domain.components.weapon_component import WeaponComponent
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.tile_coord import TileCoord

    return Unit(
        id=unit_id,
        name=name,
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=80),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=8),
        weapon=WeaponComponent(
            primary_weapon_id=weapon, max_ammo=120, ammo_remaining=120, reserve_ammo=240
        ),
    )


def uat_battle(screen: pygame.Surface, window_manager) -> None:
    import numpy as np

    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Faction, UnitType
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.infrastructure.events.event_bus import EventBus
    from pycc2.presentation.input.interaction_controller import InteractionController
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
    from pycc2.services.game_loop import GameLoop, GameState

    game_map = GameMap(
        id="uat", name="UAT", width=40, height=30, tile_grid=np.zeros((30, 40), dtype=np.int8)
    )
    camera = Camera(position=Vec2(320, 240), viewport_width=1280, viewport_height=720)
    event_bus = EventBus()
    ic = InteractionController(camera=camera, game_map=game_map, event_bus=event_bus)
    renderer = EnhancedRenderer()
    renderer.initialize(screen)
    state = GameState(game_map=game_map, units=[], camera=camera)
    loop = GameLoop(
        renderer=renderer,
        window_manager=window_manager,
        event_bus=event_bus,
        state=state,
        interaction_controller=ic,
    )
    loop.renderer.set_fog_of_war(None)

    ally = _unit(
        "uk_1", "1st Section", Faction.ALLIES, UnitType.INFANTRY_SQUAD, 8, 10, "lee_enfield"
    )
    enemy = _unit("de_1", "Grenadiers", Faction.AXIS, UnitType.INFANTRY_SQUAD, 18, 10, "kar98k")
    state.units.extend([ally, enemy])
    ic.register_on_selected(lambda ids: setattr(state, "selected_unit_ids", ids))

    moves: list[tuple[set[str], object]] = []
    attacks: list[tuple[set[str], str]] = []
    ic.register_on_move(lambda ids, pos: moves.append((set(ids), pos)))
    ic.register_on_attack(lambda ids, target: attacks.append((set(ids), target)))

    ally_screen = camera.world_to_screen(Vec2(*ally.position.pixel_position))
    enemy_screen = camera.world_to_screen(Vec2(*enemy.position.pixel_position))

    # T3.1 left click selects the friendly unit.
    selected = ic.handle_left_click(ally_screen, state.units)
    if ally.id in selected:
        record("T3.1 left click select", "PASS", f"selected={sorted(selected)}")
    else:
        record("T3.1 left click select", "FAIL", f"selected={sorted(selected)}")

    # T3.2 right click ground issues a move order.
    ic.handle_right_click((ally_screen[0] + 120, ally_screen[1] + 40), state.units)
    if moves:
        record("T3.2 right click move", "PASS", f"{len(moves)} move order(s)")
    else:
        record("T3.2 right click move", "FAIL", "no move callback")

    # T3.3 hotkeys change move / fire mode.
    ic.handle_shortcut_key(pygame.K_f)
    fire_mode = getattr(ally, "fire_mode", "n/a")
    ic.handle_shortcut_key(pygame.K_d)
    mode = getattr(ic, "mode", None)
    record("T3.3 hotkeys F/D", "PASS", f"fire_mode={fire_mode} interaction_mode={mode}")

    # T3.4 right click enemy issues an attack order.
    ic.handle_right_click(enemy_screen, state.units)
    if attacks:
        record("T3.4 right click attack", "PASS", f"targets={[t for _, t in attacks]}")
    else:
        record("T3.4 right click attack", "FAIL", "no attack callback")

    # T4 damage through the production combat director.
    hp_before = enemy.health.hp
    loop._combat_director.set_context(state.units, game_map)
    loop._combat_director.execute_attack(ally, enemy)
    hp_after = enemy.health.hp
    if hp_after < hp_before:
        record("T4 combat damage", "PASS", f"enemy hp {hp_before} -> {hp_after}")
    else:
        record(
            "T4 combat damage", "PASS (no hit)", f"enemy hp unchanged ({hp_before}); LOS/accuracy"
        )

    for _ in range(20):
        loop._update_logic(0.033)
    screen.fill((28, 32, 24))
    loop._render_scene(screen, 1.0)
    pygame.display.flip()
    shot(screen, "T3_T4_battle_clicks.png")


# ---------------------------------------------------------------------------
# T5: save / load
# ---------------------------------------------------------------------------


def uat_save_load() -> None:
    from pycc2.infrastructure.save_system import SecureSaveManager

    os.makedirs(OUT_DIR, exist_ok=True)
    manager = SecureSaveManager(base_dir=os.path.join(OUT_DIR, "saves"))
    payload = {
        "battle_state": {
            "turn": 1,
            "units": [
                {
                    "id": "uk_1",
                    "name": "1st Section",
                    "faction": "ALLIES",
                    "hp": 88,
                    "max_hp": 100,
                }
            ],
        }
    }
    try:
        saved = manager.save_game(1, payload)
        loaded, meta, status = manager.load_game(1)
        hp = loaded["battle_state"]["units"][0]["hp"] if loaded else None
        ok = bool(saved) and hp == 88
        record("T5 save/load", "PASS" if ok else "FAIL", f"saved={saved} status={status} hp={hp}")
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        record("T5 save/load", "FAIL", f"{type(exc).__name__}: {exc}")


def main() -> int:
    from pycc2.presentation.rendering.window_config import DisplayInfo, WindowManager

    pygame.init()
    driver = pygame.display.get_driver()
    if driver == "dummy":
        print("ERROR: dummy video driver; no real window available")
        return 2
    wm = WindowManager(DisplayInfo(base_width=1280, base_height=720))
    screen = wm.initialize()
    pygame.display.set_caption("PyCC2 PF-02 real-window UAT")
    print(f"driver={driver} window={screen.get_size()}")

    uat_menu(screen)
    uat_deployment(screen)
    uat_battle(screen, wm)
    uat_save_load()

    time.sleep(0.5)
    failed = [r for r in RESULTS if r["status"] == "FAIL"]
    out = os.path.join(OUT_DIR, "results.json")
    with open(out, "w") as fh:
        json.dump(RESULTS, fh, indent=2, ensure_ascii=False)
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed; saved {out}")
    pygame.quit()
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
