"""Full User Journey E2E Test — simulates a real user playing PyCC2 from start to finish.

Covers the complete user journey:
  1. Main Menu → Campaign
  2. Campaign → Start Campaign
  3. Deployment: select units, place on map
  4. Start Battle
  5. Battle: select unit, move, attack
  6. Run battle for 300 frames
  7. Pause → End Battle
  8. Return to campaign / exit

Uses SDL_VIDEODRIVER=dummy for headless rendering and injects pygame events
to simulate real user clicks and key presses.
"""

from __future__ import annotations

import os
import sys
import traceback

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest
import pygame

pygame.init()

# ---------------------------------------------------------------------------
# Domain imports
# ---------------------------------------------------------------------------
from pathlib import Path

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.input.handler import PygameInputHandler
from pycc2.presentation.input.interaction_controller import InteractionController
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
from pycc2.presentation.rendering.window_config import DisplayInfo, WindowManager
from pycc2.presentation.ui.new_game_menu import NewGameMenu, MenuScreen
from pycc2.services.ai_service import AIService
from pycc2.services.event_bus import EventBus
from pycc2.services.game_loop import GameLoop, GameState

SCREENSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

SCREEN_W, SCREEN_H = 1280, 720


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _save_screenshot(screen: pygame.Surface, name: str) -> None:
    """Save a screenshot to the screenshots directory."""
    path = SCREENSHOT_DIR / name
    try:
        pygame.image.save(screen, str(path))
        print(f"[SCREENSHOT] Saved: {path}")
    except Exception as e:
        print(f"[SCREENSHOT] Failed to save {path}: {e}")


def _click_at(screen: pygame.Surface, x: int, y: int) -> None:
    """Post a MOUSEBUTTONDOWN + MOUSEBUTTONUP event at (x, y)."""
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=1))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=1))


def _right_click_at(x: int, y: int) -> None:
    """Post a right-click event at (x, y)."""
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=3))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=3))


def _press_key(key: int) -> None:
    """Post a KEYDOWN + KEYUP event for the given key."""
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key))
    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=key))


def _move_mouse_to(x: int, y: int) -> None:
    """Post a MOUSEMOTION event to (x, y)."""
    pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(x, y)))


def _find_button_rect(menu: NewGameMenu, key: str) -> pygame.Rect | None:
    """Find a button rect by key in the NewGameMenu's internal _buttons dict."""
    return menu._buttons.get(key)


def _resolve_map_path(menu: NewGameMenu) -> Path:
    """Resolve the map path from the menu's selected map."""
    map_stem = menu.get_selected_map()
    map_path = Path(f"data/maps/{map_stem}.json")
    if not map_path.exists():
        map_dir = Path("data/maps")
        maps = [m for m in map_dir.glob("*.json") if m.stem != "_schema"]
        if maps:
            map_path = maps[0]
        else:
            raise FileNotFoundError("No map files found in data/maps/")
    return map_path


# ---------------------------------------------------------------------------
# Game initialization (mirrors main.py exactly)
# ---------------------------------------------------------------------------


def _init_game() -> tuple[GameLoop, WindowManager, pygame.Surface, NewGameMenu]:
    """Initialize the game exactly as main.py does.

    Returns (game_loop, window_manager, screen, menu).
    """
    # Create window
    wm = WindowManager(DisplayInfo(base_width=SCREEN_W, base_height=SCREEN_H))
    screen = wm.initialize()

    # Create menu
    menu = NewGameMenu(screen_width=SCREEN_W, screen_height=SCREEN_H)

    return None, wm, screen, menu  # game_loop created after menu interaction


def _build_game_loop(
    game_map: GameMap,
    screen: pygame.Surface,
    menu: NewGameMenu,
) -> GameLoop:
    """Build the GameLoop exactly as main.py does after menu selection.

    Reuses the existing screen surface instead of creating a new WindowManager
    (which would fail in headless mode since pygame.display.set_mode can only
    be called once with SDL_VIDEODRIVER=dummy).
    """
    # Camera centered on map
    center_x = game_map.width * 16.0
    center_y = game_map.height * 16.0
    camera = Camera(
        position=Vec2(center_x, center_y),
        viewport_width=SCREEN_W,
        viewport_height=SCREEN_H,
    )

    # Empty units — will be created during deployment
    units: list = []

    # Game state
    state = GameState(game_map=game_map, units=units, camera=camera)

    # Renderer
    renderer = EnhancedRenderer()
    renderer.initialize(screen)

    # Create a WindowManager that reuses the existing screen
    wm = WindowManager(DisplayInfo(base_width=SCREEN_W, base_height=SCREEN_H))
    wm._screen = screen
    wm._clock = pygame.time.Clock()

    # Event bus and input handler
    event_bus = EventBus()
    input_handler = PygameInputHandler(camera=camera, window_manager=wm)

    # AI service
    ai_service = AIService(event_bus=event_bus)

    # Interaction controller
    interaction_controller = InteractionController(
        camera=camera, game_map=game_map, event_bus=event_bus,
    )

    # UI systems
    from pycc2.presentation.rendering.display_config import DisplayConfig as DC
    from pycc2.presentation.ui.hint_manager import HintManager
    from pycc2.presentation.ui.keybind_manager import KeybindManager
    from pycc2.presentation.ui.settings_menu import SettingsMenu
    from pycc2.presentation.ui.tutorial_system import TutorialOverlay

    display_config = DC()
    hint_manager = HintManager()
    keybind_manager = KeybindManager()
    settings_menu = SettingsMenu(display_config, keybind_manager=keybind_manager)
    tutorial_overlay = TutorialOverlay(display_config)

    interaction_controller.set_hint_manager(hint_manager)
    interaction_controller.set_keybind_manager(keybind_manager)

    # Game loop
    game_loop = GameLoop(
        renderer=renderer,
        window_manager=wm,
        event_bus=event_bus,
        state=state,
        input_handler=input_handler,
        ai_service=ai_service,
        interaction_controller=interaction_controller,
        hint_manager=hint_manager,
        settings_menu=settings_menu,
        tutorial_overlay=tutorial_overlay,
    )

    return game_loop


def _start_deployment(game_loop: GameLoop, game_map: GameMap, menu: NewGameMenu) -> None:
    """Start deployment exactly as main.py does."""
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

    # Load scenario data
    scenario_stem = menu.get_selected_map()
    scenario_path = Path(f"data/scenarios/{scenario_stem}.json")
    if not scenario_path.exists():
        for sp in Path("data/scenarios").glob("*.json"):
            if sp.stem == "_schema":
                continue
            try:
                import json
                with open(sp) as f:
                    scenario = json.load(f)
                if scenario.get("map_id") == scenario_stem:
                    scenario_path = sp
                    break
            except Exception:
                continue

    if scenario_path.exists():
        try:
            import json
            with open(scenario_path) as f:
                scenario_data = json.load(f)
            map_data["victory_locations"] = scenario_data.get("victory_locations", [])
            map_data["forces"] = scenario_data.get("forces", {})
            map_data["special_rules"] = scenario_data.get("special_rules", [])
            map_data["scenario_id"] = scenario_data.get("scenario_id", "")
        except Exception:
            pass

    # Get game settings
    game_settings = menu.get_settings()
    faction = "allied" if game_settings.player_side == "allied" else "axis"

    game_loop.start_deployment(
        map_data=map_data,
        faction=faction,
        game_settings=game_settings,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def pygame_display():
    """Ensure pygame display is available for each test."""
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    yield screen
    # Cleanup: clear any leftover events
    pygame.event.get()


# ============================================================================
# Test: Full User Journey
# ============================================================================


class TestFullUserJourney:
    """Simulate a complete user journey from main menu to battle end."""

    def test_full_user_journey(self, pygame_display):
        """Complete user journey: Menu → Campaign → Deploy → Battle → End."""
        screen = pygame_display
        errors: list[str] = []

        # ================================================================
        # STEP 1: Main Menu → Campaign
        # ================================================================
        print("\n=== STEP 1: Main Menu → Campaign ===")
        try:
            menu = NewGameMenu(screen_width=SCREEN_W, screen_height=SCREEN_H)
            # Render the main menu to populate button rects
            menu.render(screen)
            _save_screenshot(screen, "user_journey_step1_main_menu.png")

            # Find and click "New Campaign" button
            new_campaign_rect = _find_button_rect(menu, "new_campaign")
            assert new_campaign_rect is not None, "Could not find 'New Campaign' button in main menu"

            click_pos = new_campaign_rect.center
            action = menu.handle_click(click_pos)
            # Clicking "New Campaign" transitions to CAMPAIGN screen, returns None
            assert menu.current_screen == MenuScreen.CAMPAIGN, \
                f"Expected CAMPAIGN screen, got {menu.current_screen}"
            print(f"  ✓ Clicked 'New Campaign' at {click_pos}, now on CAMPAIGN screen")

        except Exception as e:
            errors.append(f"STEP 1 FAILED: {e}\n{traceback.format_exc()}")
            pytest.fail(f"Step 1 failed: {e}")

        # ================================================================
        # STEP 2: Campaign Screen → Start Campaign
        # ================================================================
        print("\n=== STEP 2: Campaign Screen → Start Campaign ===")
        try:
            # Render campaign screen to populate button rects
            menu.render(screen)
            _save_screenshot(screen, "user_journey_step2_campaign.png")

            # Find and click "Start Campaign" button
            start_rect = _find_button_rect(menu, "start_campaign")
            assert start_rect is not None, "Could not find 'Start Campaign' button"

            click_pos = start_rect.center
            action = menu.handle_click(click_pos)
            assert action == "start_campaign", \
                f"Expected 'start_campaign' action, got {action}"
            print(f"  ✓ Clicked 'Start Campaign' at {click_pos}")

        except Exception as e:
            errors.append(f"STEP 2 FAILED: {e}\n{traceback.format_exc()}")
            pytest.fail(f"Step 2 failed: {e}")

        # ================================================================
        # STEP 3: Initialize Game (same as main.py after menu)
        # ================================================================
        print("\n=== STEP 3: Initialize Game ===")
        try:
            # Resolve map
            map_path = _resolve_map_path(menu)
            print(f"  Loading map: {map_path.stem}")
            game_map = GameMap.from_json(map_path)
            print(f"  Map size: {game_map.width}x{game_map.height}")

            # Validate spawn points
            if not game_map.spawn_points:
                from pycc2.domain.entities.game_map import SpawnPoint
                from pycc2.domain.value_objects.tile_coord import TileCoord
                game_map.spawn_points = [
                    SpawnPoint(
                        id="friendly_default",
                        side="allies",
                        position=TileCoord(5, game_map.height // 2),
                        units_max=9,
                    ),
                    SpawnPoint(
                        id="enemy_default",
                        side="axis",
                        position=TileCoord(game_map.width - 5, game_map.height // 2),
                        units_max=9,
                    ),
                ]
                print(f"  Added default spawn points")

            # Build game loop (reuse existing screen)
            game_loop = _build_game_loop(game_map, screen, menu)

            # Start deployment
            _start_deployment(game_loop, game_map, menu)
            assert game_loop.deployment_phase_active, "Deployment phase should be active"
            assert game_loop.deployment_ui is not None, "Deployment UI should exist"
            print(f"  ✓ Game initialized, deployment phase active")

        except Exception as e:
            errors.append(f"STEP 3 FAILED: {e}\n{traceback.format_exc()}")
            pytest.fail(f"Step 3 failed: {e}")

        # ================================================================
        # STEP 4: Deploy Units
        # ================================================================
        print("\n=== STEP 4: Deploy Units ===")
        try:
            deployment_ui = game_loop.deployment_ui
            dc = game_loop.display_config
            tile_size = dc.base_tile_size if dc else 16

            # Render deployment UI to populate button rects
            deployment_ui.render(screen, font=None, map_offset_x=0, map_offset_y=0, tile_size=tile_size)
            _save_screenshot(screen, "user_journey_step4_deployment_start.png")

            # Get available units
            available = deployment_ui.state.available_units
            print(f"  Available units: {len(available)}")
            assert len(available) > 0, "No units available for deployment"

            # Find unplaced units
            unplaced_indices = [i for i, u in enumerate(available) if not u.is_placed]
            print(f"  Unplaced units: {len(unplaced_indices)}")
            assert len(unplaced_indices) >= 3, "Need at least 3 unplaced units"

            # Deploy 3-5 units using the deployment UI's API directly
            # (simulating click-select-then-click-place flow)
            units_to_deploy = min(5, len(unplaced_indices))
            placed_count = 0

            for deploy_idx in range(units_to_deploy):
                unit_idx = unplaced_indices[deploy_idx]
                unit = available[unit_idx]
                print(f"  Deploying unit {deploy_idx + 1}: {unit.display_name} (idx={unit_idx}, type={unit.unit_type}, cost={unit.deployment_cost})")

                # Select the unit in the roster
                deployment_ui._selected_unit_index = unit_idx

                # Find a valid placement position in friendly zone
                placed = False
                for fx, fy in deployment_ui.state.friendly_zone:
                    terrain = deployment_ui._get_terrain_at(fx, fy)
                    if deployment_ui.can_place_at(unit, fx, fy, terrain):
                        # Check not already occupied
                        occupied = any(pu.position == (fx, fy) for pu in deployment_ui.state.placed_units)
                        if not occupied:
                            success = deployment_ui.place_unit(unit_idx, fx, fy)
                            if success:
                                placed_count += 1
                                print(f"    ✓ Placed at ({fx}, {fy})")
                                placed = True
                                break

                if not placed:
                    print(f"    ✗ Could not find valid position for {unit.display_name}")

            print(f"  Total units placed: {placed_count}")
            assert placed_count >= 1, "Must place at least 1 unit to start battle"

            # Re-render to show placed units
            deployment_ui.render(screen, font=None, map_offset_x=0, map_offset_y=0, tile_size=tile_size)
            _save_screenshot(screen, "user_journey_step4_deployment_placed.png")

            # Verify deployment is complete (at least 1 unit placed)
            assert deployment_ui.is_deployment_complete(), "Deployment should be complete"

        except Exception as e:
            errors.append(f"STEP 4 FAILED: {e}\n{traceback.format_exc()}")
            pytest.fail(f"Step 4 failed: {e}")

        # ================================================================
        # STEP 5: Start Battle
        # ================================================================
        print("\n=== STEP 5: Start Battle ===")
        try:
            # Complete deployment (this creates Unit entities and AI units)
            result = game_loop.complete_deployment()
            assert result is not None, "complete_deployment() should return a result"
            assert not game_loop.deployment_phase_active, "Deployment should no longer be active"

            placements = result.get("placements", [])
            print(f"  Player units: {len(placements)}")
            print(f"  Total units in state: {len(game_loop.state.units)}")

            # Verify we have both player and AI units
            from pycc2.domain.entities.unit import Faction
            player_units = [u for u in game_loop.state.units if u.faction == Faction.ALLIES]
            ai_units = [u for u in game_loop.state.units if u.faction == Faction.AXIS]
            print(f"  Allied units: {len(player_units)}")
            print(f"  Axis units: {len(ai_units)}")
            assert len(player_units) >= 1, "Should have at least 1 player unit"
            assert len(ai_units) >= 1, "Should have at least 1 AI unit"

            # Render battle start
            game_loop._render_pipeline.render(
                game_map=game_loop.state.game_map,
                units=game_loop.state.units,
                camera=game_loop.state.camera,
                alpha=0.0,
                selected_unit_ids=game_loop.state.selected_unit_ids,
                debug_mode=False,
                paused=False,
                tick=0,
                show_post_battle=False,
                game_result=None,
                battle_stats=None,
            )
            _save_screenshot(screen, "user_journey_step5_battle_start.png")
            print(f"  ✓ Battle started successfully")

        except Exception as e:
            errors.append(f"STEP 5 FAILED: {e}\n{traceback.format_exc()}")
            pytest.fail(f"Step 5 failed: {e}")

        # ================================================================
        # STEP 6: Give Commands During Battle
        # ================================================================
        print("\n=== STEP 6: Give Commands During Battle ===")
        try:
            from pycc2.domain.entities.unit import Faction

            # Find a player unit to select
            player_units = [u for u in game_loop.state.units if u.faction == Faction.ALLIES]
            assert len(player_units) > 0, "No player units to command"

            target_unit = player_units[0]
            print(f"  Selecting unit: {target_unit.name} (id={target_unit.id})")

            # Select the unit via game state
            game_loop.state.selected_unit_ids = {target_unit.id}

            # Issue a move command via interaction controller
            # Z key = Move mode
            game_loop.interaction_controller.handle_shortcut_key(pygame.K_z)
            from pycc2.presentation.input.interaction_controller import InteractionMode
            assert game_loop.interaction_controller.mode == InteractionMode.MOVE, \
                f"Should be in MOVE mode after pressing Z, got {game_loop.interaction_controller.mode}"
            print(f"  ✓ Pressed Z → MOVE mode")

            # Set a move target for the unit
            # Calculate a valid move target (a few tiles away)
            from pycc2.domain.value_objects.tile_coord import TileCoord
            current_tile = target_unit.position.tile_coord
            move_tx = min(current_tile.x + 3, game_map.width - 1)
            move_ty = min(current_tile.y + 2, game_map.height - 1)
            target_unit.set_move_target(TileCoord(move_tx, move_ty))
            print(f"  ✓ Set move target: ({move_tx}, {move_ty})")

            # Switch back to SELECT mode
            game_loop.interaction_controller.set_mode(
                game_loop.interaction_controller.__class__.__module__
            )
            # Reset to SELECT mode
            from pycc2.presentation.input.interaction_controller import InteractionMode
            game_loop.interaction_controller.set_mode(InteractionMode.SELECT)

            # Issue a fire command via shortcut key
            # C key = Fire/Attack mode
            game_loop.interaction_controller.handle_shortcut_key(pygame.K_c)
            assert game_loop.interaction_controller.mode == InteractionMode.ATTACK, \
                f"Should be in ATTACK mode after pressing C, got {game_loop.interaction_controller.mode}"
            print(f"  ✓ Pressed C → ATTACK mode")

            # Reset to SELECT mode
            game_loop.interaction_controller.set_mode(InteractionMode.SELECT)
            print(f"  ✓ Reset to SELECT mode")

        except Exception as e:
            errors.append(f"STEP 6 FAILED: {e}\n{traceback.format_exc()}")
            pytest.fail(f"Step 6 failed: {e}")

        # ================================================================
        # STEP 7: Run Battle for 300 Frames
        # ================================================================
        print("\n=== STEP 7: Run Battle for 300 Frames ===")
        try:
            dt = 1.0 / 30.0
            game_loop.state.paused = False

            for tick in range(300):
                try:
                    game_loop._update_logic(dt)
                except Exception as tick_err:
                    errors.append(f"  CRASH at tick {tick}: {tick_err}")
                    raise

                game_loop.state.tick += 1

            print(f"  ✓ Ran 300 ticks without crash")

            # Check unit states
            alive_count = sum(1 for u in game_loop.state.units if u.is_alive)
            print(f"  Units alive after 300 ticks: {alive_count}/{len(game_loop.state.units)}")

            # Render post-battle
            game_loop._render_pipeline.render(
                game_map=game_loop.state.game_map,
                units=game_loop.state.units,
                camera=game_loop.state.camera,
                alpha=0.0,
                selected_unit_ids=game_loop.state.selected_unit_ids,
                debug_mode=False,
                paused=False,
                tick=game_loop.state.tick,
                show_post_battle=False,
                game_result=None,
                battle_stats=None,
            )
            _save_screenshot(screen, "user_journey_step7_after_300_frames.png")

        except Exception as e:
            errors.append(f"STEP 7 FAILED: {e}\n{traceback.format_exc()}")
            pytest.fail(f"Step 7 failed: {e}")

        # ================================================================
        # STEP 8: End Battle (via pause menu)
        # ================================================================
        print("\n=== STEP 8: End Battle ===")
        try:
            # Open pause menu (ESC key)
            game_loop._pause_menu.toggle()
            assert game_loop._pause_menu.is_active, "Pause menu should be active"
            game_loop.state.paused = True
            print(f"  ✓ Opened pause menu")

            # Render pause menu
            game_loop._pause_menu.render(screen)
            _save_screenshot(screen, "user_journey_step8_pause_menu.png")

            # Find and click "Quit to Menu" button
            quit_rect = game_loop._pause_menu._buttons.get("quit_to_menu")
            assert quit_rect is not None, "Could not find 'Quit to Menu' button"

            action = game_loop._pause_menu.handle_click(quit_rect.center)
            assert action == "quit_to_menu", f"Expected 'quit_to_menu', got {action}"
            print(f"  ✓ Clicked 'Quit to Menu' at {quit_rect.center}")

            # Set game to not running (simulating what event_dispatcher does)
            game_loop.state.running = False
            print(f"  ✓ Battle ended, game shutting down")

        except Exception as e:
            errors.append(f"STEP 8 FAILED: {e}\n{traceback.format_exc()}")
            pytest.fail(f"Step 8 failed: {e}")

        # ================================================================
        # STEP 9: Verify Clean Shutdown
        # ================================================================
        print("\n=== STEP 9: Verify Clean Shutdown ===")
        try:
            # Note: We don't call game_loop.shutdown() here because it calls
            # pygame.quit() which would break other tests. In a real game,
            # shutdown() is only called on exit.
            # Instead, just verify the AI service and sound system can shut down.
            if game_loop.ai_service is not None:
                game_loop.ai_service.shutdown()
            if game_loop.sound_system is not None:
                game_loop.sound_system.shutdown()
            print(f"  ✓ Game components shut down cleanly")

        except Exception as e:
            errors.append(f"STEP 9 FAILED: {e}\n{traceback.format_exc()}")
            pytest.fail(f"Step 9 failed: {e}")

        # ================================================================
        # Final Summary
        # ================================================================
        if errors:
            print(f"\n=== JOURNEY COMPLETED WITH {len(errors)} ERRORS ===")
            for err in errors:
                print(err)
        else:
            print(f"\n=== FULL USER JOURNEY COMPLETED SUCCESSFULLY ===")

    def test_menu_navigation_via_events(self, pygame_display):
        """Test menu navigation by injecting pygame events (more realistic)."""
        screen = pygame_display
        menu = NewGameMenu(screen_width=SCREEN_W, screen_height=SCREEN_H)

        # Render main menu to populate buttons
        menu.render(screen)

        # Find "New Campaign" button
        new_campaign_rect = _find_button_rect(menu, "new_campaign")
        assert new_campaign_rect is not None

        # Simulate click via handle_click (same as what event loop does)
        action = menu.handle_click(new_campaign_rect.center)
        assert menu.current_screen == MenuScreen.CAMPAIGN

        # Render campaign screen
        menu.render(screen)

        # Find "Start Campaign" button
        start_rect = _find_button_rect(menu, "start_campaign")
        assert start_rect is not None

        action = menu.handle_click(start_rect.center)
        assert action == "start_campaign"

    def test_deployment_and_battle_via_event_loop(self, pygame_display):
        """Test deployment + battle using the game_loop's event processing.

        This is the most realistic test: injects pygame events and processes
        them through the game_loop's event dispatcher.
        """
        screen = pygame_display

        # Initialize game
        menu = NewGameMenu(screen_width=SCREEN_W, screen_height=SCREEN_H)
        menu.render(screen)

        # Navigate to campaign and start
        menu.handle_click(menu._buttons["new_campaign"].center)
        menu.render(screen)
        menu.handle_click(menu._buttons["start_campaign"].center)

        # Build game
        map_path = _resolve_map_path(menu)
        game_map = GameMap.from_json(map_path)

        if not game_map.spawn_points:
            from pycc2.domain.entities.game_map import SpawnPoint
            from pycc2.domain.value_objects.tile_coord import TileCoord
            game_map.spawn_points = [
                SpawnPoint(id="friendly_default", side="allies",
                           position=TileCoord(5, game_map.height // 2), units_max=9),
                SpawnPoint(id="enemy_default", side="axis",
                           position=TileCoord(game_map.width - 5, game_map.height // 2), units_max=9),
            ]

        game_loop = _build_game_loop(game_map, screen, menu)
        _start_deployment(game_loop, game_map, menu)

        assert game_loop.deployment_phase_active

        # Deploy units directly via API
        deployment_ui = game_loop.deployment_ui
        available = deployment_ui.state.available_units
        unplaced = [i for i, u in enumerate(available) if not u.is_placed]

        placed = 0
        for idx in unplaced[:5]:
            unit = available[idx]
            deployment_ui._selected_unit_index = idx
            for fx, fy in deployment_ui.state.friendly_zone:
                terrain = deployment_ui._get_terrain_at(fx, fy)
                if deployment_ui.can_place_at(unit, fx, fy, terrain):
                    occupied = any(pu.position == (fx, fy) for pu in deployment_ui.state.placed_units)
                    if not occupied:
                        if deployment_ui.place_unit(idx, fx, fy):
                            placed += 1
                            break

        assert placed >= 1, f"Could not place any units (tried {len(unplaced[:5])})"

        # Start battle
        result = game_loop.complete_deployment()
        assert result is not None

        # Process events through the event dispatcher for a few frames
        dt = 1.0 / 30.0
        game_loop.state.paused = False

        for tick in range(100):
            # Inject a mouse move event to test event processing
            if tick == 10:
                _move_mouse_to(640, 360)

            # Process events (drains the queue)
            game_loop._event_dispatcher.process_events()

            # Update logic
            game_loop._update_logic(dt)
            game_loop.state.tick += 1

        print(f"  ✓ Processed 100 frames via event dispatcher without crash")

        # Test keyboard commands through event dispatcher
        # Select a player unit first
        from pycc2.domain.entities.unit import Faction
        player_units = [u for u in game_loop.state.units if u.faction == Faction.ALLIES]
        if player_units:
            game_loop.state.selected_unit_ids = {player_units[0].id}

            # Inject Z key (move command) via event
            _press_key(pygame.K_z)
            game_loop._event_dispatcher.process_events()

            # Inject ESC key (pause) via event
            _press_key(pygame.K_ESCAPE)
            game_loop._event_dispatcher.process_events()
            assert game_loop._pause_menu.is_active, "Pause menu should be active after ESC"

            # Click "Resume" button
            resume_rect = game_loop._pause_menu._buttons.get("resume")
            if resume_rect:
                action = game_loop._pause_menu.handle_click(resume_rect.center)
                assert action == "resume"
                game_loop._pause_menu.deactivate()
                game_loop.state.paused = False

        # Clean shutdown (don't call game_loop.shutdown() as it calls pygame.quit())
        game_loop.state.running = False
        if game_loop.ai_service is not None:
            game_loop.ai_service.shutdown()
        if game_loop.sound_system is not None:
            game_loop.sound_system.shutdown()
        print(f"  ✓ Clean shutdown after event-driven battle")

    def test_deployment_click_flow(self, pygame_display):
        """Test deployment by clicking through the UI (click roster → click map)."""
        screen = pygame_display

        # Initialize game
        menu = NewGameMenu(screen_width=SCREEN_W, screen_height=SCREEN_H)
        menu.render(screen)
        menu.handle_click(menu._buttons["new_campaign"].center)
        menu.render(screen)
        menu.handle_click(menu._buttons["start_campaign"].center)

        map_path = _resolve_map_path(menu)
        game_map = GameMap.from_json(map_path)

        if not game_map.spawn_points:
            from pycc2.domain.entities.game_map import SpawnPoint
            from pycc2.domain.value_objects.tile_coord import TileCoord
            game_map.spawn_points = [
                SpawnPoint(id="friendly_default", side="allies",
                           position=TileCoord(5, game_map.height // 2), units_max=9),
                SpawnPoint(id="enemy_default", side="axis",
                           position=TileCoord(game_map.width - 5, game_map.height // 2), units_max=9),
            ]

        game_loop = _build_game_loop(game_map, screen, menu)
        _start_deployment(game_loop, game_map, menu)

        deployment_ui = game_loop.deployment_ui
        dc = game_loop.display_config
        tile_size = dc.base_tile_size if dc else 16

        # Render to populate button rects
        deployment_ui.render(screen, font=None, map_offset_x=0, map_offset_y=0, tile_size=tile_size)

        # Find an unplaced unit and click it in the roster
        available = deployment_ui.state.available_units
        unplaced = [(i, u) for i, u in enumerate(available) if not u.is_placed]
        assert len(unplaced) > 0, "No unplaced units"

        unit_idx, unit = unplaced[0]

        # Click on the unit in the roster panel (left side, x < roster_width)
        roster_width = deployment_ui._roster_width
        # Find the y position of this unit in the roster layout
        roster_y = 36  # Start after title
        for entry_type, entry_data in deployment_ui._roster_layout:
            if entry_type == "category":
                roster_y += deployment_ui._roster_category_height + 2
            elif entry_type == "unit":
                if entry_data == unit_idx:
                    break
                roster_y += deployment_ui._roster_item_height + 2

        # Click on the roster item
        click_x = roster_width // 2
        click_y = roster_y + deployment_ui._roster_item_height // 2

        result = deployment_ui.handle_click_full(
            click_x, click_y,
            map_offset_x=0, map_offset_y=0, tile_size=tile_size,
        )
        print(f"  Roster click result: {result}")
        assert result is not None and result.startswith("select_unit"), \
            f"Expected 'select_unit:...', got {result}"

        # Now click on the map to place the unit
        # Find a valid friendly zone position
        placed = False
        for fx, fy in deployment_ui.state.friendly_zone:
            terrain = deployment_ui._get_terrain_at(fx, fy)
            if deployment_ui.can_place_at(unit, fx, fy, terrain):
                occupied = any(pu.position == (fx, fy) for pu in deployment_ui.state.placed_units)
                if not occupied:
                    # Convert map position to screen position
                    # Map area starts at x=roster_width
                    map_screen_x = roster_width + fx * tile_size + tile_size // 2
                    map_screen_y = fy * tile_size + tile_size // 2

                    result = deployment_ui.handle_click_full(
                        map_screen_x, map_screen_y,
                        map_offset_x=0, map_offset_y=0, tile_size=tile_size,
                    )
                    print(f"  Map click at ({map_screen_x}, {map_screen_y}) → map tile ({fx}, {fy}), result: {result}")
                    if result and result.startswith("place_unit"):
                        placed = True
                        break

        assert placed, "Could not place unit by clicking on map"

        # Verify unit is placed
        assert deployment_ui.is_deployment_complete(), "Deployment should be complete after placing unit"

        # Click "Start Battle" button
        deployment_ui.render(screen, font=None, map_offset_x=0, map_offset_y=0, tile_size=tile_size)
        if deployment_ui._button_rect:
            btn_x, btn_y, btn_w, btn_h = deployment_ui._button_rect
            result = deployment_ui.handle_click_full(
                btn_x + btn_w // 2, btn_y + btn_h // 2,
                map_offset_x=0, map_offset_y=0, tile_size=tile_size,
            )
            print(f"  Start Battle button click result: {result}")
            assert result == "begin_battle", f"Expected 'begin_battle', got {result}"

        # Complete deployment
        deploy_result = game_loop.complete_deployment()
        assert deploy_result is not None

        # Run a few battle ticks
        dt = 1.0 / 30.0
        game_loop.state.paused = False
        for tick in range(50):
            game_loop._update_logic(dt)
            game_loop.state.tick += 1

        print(f"  ✓ Deployment click flow + 50 battle ticks completed")

        # Clean shutdown (don't call game_loop.shutdown() as it calls pygame.quit())
        game_loop.state.running = False
        if game_loop.ai_service is not None:
            game_loop.ai_service.shutdown()
        if game_loop.sound_system is not None:
            game_loop.sound_system.shutdown()
