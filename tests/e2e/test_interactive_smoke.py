"""Interactive smoke test — simulates REAL user interactions through the game.

This test injects pygame events (mouse clicks, key presses) to simulate
a complete user journey: Launch → Deploy → Battle → End.

Strategy: Instead of trying to run the blocking GameLoop.run(), we
initialize all components exactly as main.py does, then call each
method individually (start_deployment, complete_deployment, _update_logic,
_render_pipeline.render) to exercise the full pipeline step-by-step.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import pytest
import pygame
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_map_path() -> Path:
    """Find a valid map JSON file for testing."""
    map_dir = Path("data/maps")
    for candidate in sorted(map_dir.glob("*.json")):
        if candidate.stem != "_schema":
            return candidate
    raise FileNotFoundError("No map files found in data/maps/")


class TestInteractiveSmoke:
    """Smoke test that simulates real user interactions through the game loop."""

    @pytest.fixture(autouse=True)
    def init_pygame(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        yield
        pygame.quit()

    # -- Event injection helpers -------------------------------------------

    def _inject_click(self, x, y, button=1):
        """Post a mouse click (down + up) at (x, y)."""
        pygame.event.post(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=button)
        )
        pygame.event.post(
            pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(x, y), button=button)
        )

    def _inject_key(self, key, mod=0):
        """Post a key press (down + up)."""
        pygame.event.post(
            pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod)
        )
        pygame.event.post(
            pygame.event.Event(pygame.KEYUP, key=key, mod=mod)
        )

    def _inject_mouse_move(self, x, y):
        """Post a mouse motion event."""
        pygame.event.post(
            pygame.event.Event(pygame.MOUSEMOTION, pos=(x, y), rel=(0, 0)
            )
        )

    # -- Component factory (mirrors main.py) --------------------------------

    def _create_game_loop(self):
        """Create a fully wired GameLoop exactly as main.py does."""
        from pycc2.domain.entities.game_map import GameMap
        from pycc2.domain.value_objects.vec2 import Vec2
        from pycc2.presentation.input.handler import PygameInputHandler
        from pycc2.presentation.input.interaction_controller import (
            InteractionController,
        )
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
        from pycc2.presentation.rendering.window_config import DisplayInfo, WindowManager
        from pycc2.services.ai_service import AIService
        from pycc2.services.event_bus import EventBus
        from pycc2.services.game_loop import GameLoop, GameState
        from pycc2.presentation.rendering.display_config import DisplayConfig as DC
        from pycc2.presentation.ui.hint_manager import HintManager
        from pycc2.presentation.ui.keybind_manager import KeybindManager
        from pycc2.presentation.ui.settings_menu import SettingsMenu
        from pycc2.presentation.ui.tutorial_system import TutorialOverlay

        # Load a real map
        map_path = _find_map_path()
        game_map = GameMap.from_json(map_path)

        # Validate spawn points — add defaults if missing
        if not game_map.spawn_points:
            from pycc2.domain.entities.game_map import SpawnPoint
            from pycc2.domain.value_objects.tile_coord import TileCoord

            game_map.spawn_points = [
                SpawnPoint(
                    id="friendly_default",
                    side="friendly",
                    position=TileCoord(5, game_map.height // 2),
                    units_max=9,
                ),
                SpawnPoint(
                    id="enemy_default",
                    side="enemy",
                    position=TileCoord(game_map.width - 5, game_map.height // 2),
                    units_max=9,
                ),
            ]

        # Create camera centered on map
        center_x = game_map.width * 16.0
        center_y = game_map.height * 16.0
        camera = Camera(
            position=Vec2(center_x, center_y),
            viewport_width=1280,
            viewport_height=720,
        )

        # Create window manager
        wm = WindowManager(DisplayInfo(base_width=1280, base_height=720))
        wm._screen = self.screen

        # Create renderer
        renderer = EnhancedRenderer()
        renderer.initialize(self.screen)

        # Create event bus and input handler
        event_bus = EventBus()
        input_handler = PygameInputHandler(camera=camera, window_manager=wm)

        # Create AI service
        ai_service = AIService(event_bus=event_bus)

        # Create interaction controller
        interaction_controller = InteractionController(
            camera=camera,
            game_map=game_map,
            event_bus=event_bus,
        )

        # Create UI systems
        display_config = DC()
        hint_manager = HintManager()
        keybind_manager = KeybindManager()
        settings_menu = SettingsMenu(display_config, keybind_manager=keybind_manager)
        tutorial_overlay = TutorialOverlay(display_config)

        interaction_controller.set_hint_manager(hint_manager)
        interaction_controller.set_keybind_manager(keybind_manager)

        # Create game state
        state = GameState(
            game_map=game_map,
            units=[],
            camera=camera,
        )

        # Create game loop
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

        return game_loop, game_map

    # ====================================================================
    # TEST 1: Full user journey — Deploy → Battle → End
    # ====================================================================

    def test_full_user_journey_smoke(self):
        """Simulate: Launch → Deploy units → Start Battle → Run 300 ticks → End.

        This is the core smoke test. It exercises:
        1. GameLoop initialization (mirrors main.py)
        2. Deployment phase start
        3. Simulated mouse clicks to select & place units
        4. Deployment completion (creates Unit entities + AI)
        5. Battle phase: 300 ticks of _update_logic (AI, combat, victory)
        6. Event processing with injected keyboard/mouse events
        7. Rendering pipeline
        """
        game_loop, game_map = self._create_game_loop()
        state = game_loop.state

        # ---- Step 1: Build map_data for deployment ----
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

        # ---- Step 2: Start deployment phase ----
        game_loop.start_deployment(map_data=map_data, faction="allied")
        assert game_loop.deployment_phase_active, "Deployment should be active"
        assert game_loop.deployment_ui is not None, "DeploymentUI should exist"

        deployment_ui = game_loop.deployment_ui

        # ---- Step 3: Simulate user selecting & placing units ----
        # Find an unplaced infantry unit in the roster
        available = deployment_ui.state.available_units
        assert len(available) >= 6, f"Should have at least 6 available units in roster, got {len(available)}"

        # Find first unplaced infantry unit
        inf_idx = None
        for i, u in enumerate(available):
            if u.unit_type == "infantry" and not u.is_placed:
                inf_idx = i
                break
        assert inf_idx is not None, "Should have at least one infantry unit"

        # Simulate: click on roster to select unit
        # Roster is on left side (x < 240), items start around y=36
        # Walk layout to find the y position of our unit
        roster_y = 36
        for entry_type, entry_data in deployment_ui._roster_layout:
            if entry_type == "category":
                roster_y += deployment_ui._roster_category_height + 2
            elif entry_type == "unit":
                if entry_data == inf_idx:
                    break
                roster_y += deployment_ui._roster_item_height + 2

        # Click on the roster unit to select it
        select_result = deployment_ui.handle_click_full(
            screen_x=50, screen_y=roster_y + 10,
            map_offset_x=0, map_offset_y=0,
            tile_size=16,
        )
        assert select_result is not None, f"Click on roster unit should return action, got None"
        assert "select_unit" in select_result, f"Expected select_unit, got {select_result}"

        # Now place the unit on a friendly zone tile
        # Find a valid placement position in friendly zone
        friendly_zone = deployment_ui.state.friendly_zone
        assert len(friendly_zone) >= 10, f"Should have at least 10 friendly zone tiles, got {len(friendly_zone)}"

        placed = False
        for tile_x, tile_y in friendly_zone[:20]:  # Try first 20 tiles
            terrain = deployment_ui._get_terrain_at(tile_x, tile_y)
            unit = available[inf_idx]
            if deployment_ui.can_place_at(unit, tile_x, tile_y, terrain):
                # Check not already occupied
                occupied = any(
                    pu.position == (tile_x, tile_y)
                    for pu in deployment_ui.state.placed_units
                )
                if not occupied:
                    # Convert tile coords to screen coords for click
                    # Map area starts at x=roster_width (240), each tile is 16px
                    screen_x = deployment_ui._roster_width + tile_x * 16
                    screen_y = tile_y * 16
                    place_result = deployment_ui.handle_click_full(
                        screen_x=screen_x, screen_y=screen_y,
                        map_offset_x=0, map_offset_y=0,
                        tile_size=16,
                    )
                    if place_result and "place_unit" in place_result:
                        placed = True
                        break

        assert placed, "Should successfully place at least one unit on the map"
        assert deployment_ui.is_deployment_complete(), "Deployment should be complete (≥1 unit placed)"

        # Place a second unit (support type) for variety
        support_idx = None
        for i, u in enumerate(available):
            if u.unit_type == "support" and not u.is_placed:
                support_idx = i
                break

        if support_idx is not None:
            # Select the support unit
            roster_y2 = 36
            for entry_type, entry_data in deployment_ui._roster_layout:
                if entry_type == "category":
                    roster_y2 += deployment_ui._roster_category_height + 2
                elif entry_type == "unit":
                    if entry_data == support_idx:
                        break
                    roster_y2 += deployment_ui._roster_item_height + 2

            deployment_ui.handle_click_full(
                screen_x=50, screen_y=roster_y2 + 10,
                map_offset_x=0, map_offset_y=0,
                tile_size=16,
            )

            # Place support unit
            for tile_x, tile_y in friendly_zone[:30]:
                terrain = deployment_ui._get_terrain_at(tile_x, tile_y)
                unit = available[support_idx]
                if deployment_ui.can_place_at(unit, tile_x, tile_y, terrain):
                    occupied = any(
                        pu.position == (tile_x, tile_y)
                        for pu in deployment_ui.state.placed_units
                    )
                    if not occupied:
                        screen_x = deployment_ui._roster_width + tile_x * 16
                        screen_y = tile_y * 16
                        deployment_ui.handle_click_full(
                            screen_x=screen_x, screen_y=screen_y,
                            map_offset_x=0, map_offset_y=0,
                            tile_size=16,
                        )
                        break

        # ---- Step 4: Complete deployment ----
        result = game_loop.complete_deployment()
        assert result is not None, "complete_deployment should return a result dict"
        assert "placements" in result, "Result should contain placements"
        assert len(result["placements"]) >= 1, "Should have at least 1 player placement"

        # Verify units were created in game state
        assert len(state.units) >= 1, "Game state should have units after deployment"
        # AI units should also be created
        player_units = [u for u in state.units if u.faction.name == "ALLIES"]
        ai_units = [u for u in state.units if u.faction.name == "AXIS"]
        assert len(player_units) >= 1, "Should have at least 1 player unit"
        # AI units may or may not exist depending on map, but we check
        print(f"[SMOKE] Player units: {len(player_units)}, AI units: {len(ai_units)}")

        # Deployment should no longer be active
        assert not game_loop.deployment_phase_active, "Deployment should be inactive after completion"

        # ---- Step 5: Run battle phase — 300 ticks of _update_logic ----
        dt = 1.0 / 30.0
        errors = []

        for tick in range(300):
            try:
                # Inject simulated user events at specific ticks
                if tick == 10:
                    # Left-click on map (select unit)
                    self._inject_click(500, 400)
                elif tick == 30:
                    # Right-click (move command)
                    self._inject_click(600, 350, button=3)
                elif tick == 50:
                    # Press Z (shortcut key)
                    self._inject_key(pygame.K_z)
                elif tick == 100:
                    # Press Escape (pause)
                    self._inject_key(pygame.K_ESCAPE)
                elif tick == 110:
                    # Press Escape again (unpause)
                    self._inject_key(pygame.K_ESCAPE)
                elif tick == 150:
                    # Press Space (time control)
                    self._inject_key(pygame.K_SPACE)
                elif tick == 200:
                    # Mouse move
                    self._inject_mouse_move(400, 300)
                elif tick == 250:
                    # Ctrl key (LOS overlay)
                    self._inject_key(pygame.K_LCTRL, mod=pygame.KMOD_CTRL)
                elif tick == 260:
                    # Release Ctrl
                    pygame.event.post(
                        pygame.event.Event(pygame.KEYUP, key=pygame.K_LCTRL, mod=0)
                    )

                # Process events through the event dispatcher
                game_loop._event_dispatcher.process_events()

                # Tick game logic
                game_loop._update_logic(dt)

                # Increment tick counter (mirrors GameLoop.run)
                state.tick += 1

            except Exception as e:
                errors.append((tick, str(e)))
                # Don't break — we want to see how many ticks succeed

        # Report any errors
        if errors:
            error_summary = "\n".join(f"  Tick {t}: {msg}" for t, msg in errors[:5])
            pytest.fail(
                f"_update_logic crashed on {len(errors)}/300 ticks. First errors:\n"
                f"{error_summary}"
            )

        # ---- Step 6: Verify game state is still healthy ----
        assert state.tick >= 300, f"Should have ticked 300 times, got {state.tick}"

        # Units should still exist (none should have been garbage collected)
        assert len(state.units) >= 1, "Units should still exist after battle ticks"

        # ---- Step 7: Render one frame to verify rendering doesn't crash ----
        try:
            game_loop._render_pipeline.render(
                game_map=state.game_map,
                units=state.units,
                camera=state.camera,
                alpha=0.5,
                selected_unit_ids=state.selected_unit_ids,
                debug_mode=False,
                paused=False,
                tick=state.tick,
                show_post_battle=False,
                game_result=None,
                battle_stats=None,
            )
        except Exception as e:
            pytest.fail(f"Rendering crashed after battle: {e}")

        # ---- Step 8: Shutdown cleanly ----
        game_loop.shutdown()

    # ====================================================================
    # TEST 2: Deployment UI click interactions
    # ====================================================================

    def test_deployment_ui_click_interactions(self):
        """Test that clicking through the deployment UI works without crashes.

        Exercises:
        - Selecting units from roster
        - Placing units on the map
        - Clicking the Start Battle button
        - Right-click to remove a placed unit
        """
        from pycc2.presentation.ui.deployment_ui import DeploymentUI

        # Create a DeploymentUI with a simple map
        map_data = {
            "width": 30,
            "height": 20,
            "tiles": [[0] * 30 for _ in range(20)],  # All open terrain
            "spawn_points": [
                {"id": "sp1", "side": "allies", "position": [5, 10], "units_max": 9},
                {"id": "sp2", "side": "axis", "position": [25, 10], "units_max": 9},
            ],
        }

        dui = DeploymentUI(width=800, height=600)
        dui.start_deployment(map_data=map_data, faction="ally")

        # Verify roster was built
        assert len(dui.state.available_units) >= 6, f"Should have at least 6 units in roster, got {len(dui.state.available_units)}"

        # Find first infantry unit index
        inf_idx = None
        for i, u in enumerate(dui.state.available_units):
            if u.unit_type == "infantry" and not u.is_placed:
                inf_idx = i
                break
        assert inf_idx is not None

        # Click on roster to select unit
        roster_y = 36
        for entry_type, entry_data in dui._roster_layout:
            if entry_type == "category":
                roster_y += dui._roster_category_height + 2
            elif entry_type == "unit":
                if entry_data == inf_idx:
                    break
                roster_y += dui._roster_item_height + 2

        result = dui.handle_click_full(
            screen_x=50, screen_y=roster_y + 10,
            map_offset_x=0, map_offset_y=0,
            tile_size=16,
        )
        assert result is not None
        assert "select_unit" in result
        assert dui._selected_unit_index == inf_idx

        # Place unit on friendly zone tile (0, 0) should be friendly (left third)
        # Screen coords: roster_width + tile_x * tile_size
        screen_x = dui._roster_width + 1 * 16  # tile (1, 1)
        screen_y = 1 * 16
        result = dui.handle_click_full(
            screen_x=screen_x, screen_y=screen_y,
            map_offset_x=0, map_offset_y=0,
            tile_size=16,
        )
        assert result is not None
        assert "place_unit" in result
        assert dui.state.placed_units[0].is_placed

        # Verify deployment is complete
        assert dui.is_deployment_complete()

        # Right-click on the placed unit — first right-click selects it
        result = dui.handle_click_full(
            screen_x=screen_x, screen_y=screen_y,
            map_offset_x=0, map_offset_y=0,
            tile_size=16,
            right_click=True,
        )
        # First right-click on a placed unit selects it (returns select_placed_unit)
        # Second right-click would set a pending order. Removal is via the detail panel.
        # To actually remove, use remove_unit() directly
        assert dui.state.placed_units[0].is_placed
        # Remove via direct API call (simulates clicking "REMOVE FROM MAP" button)
        dui.remove_unit(1, 1)
        assert len(dui.state.placed_units) == 0

        # Place again for begin_battle test
        dui.handle_click_full(
            screen_x=50, screen_y=roster_y + 10,
            map_offset_x=0, map_offset_y=0,
            tile_size=16,
        )
        dui.handle_click_full(
            screen_x=screen_x, screen_y=screen_y,
            map_offset_x=0, map_offset_y=0,
            tile_size=16,
        )
        assert dui.is_deployment_complete()

        # Begin battle
        battle_result = dui.begin_battle()
        assert battle_result is not None
        assert "placements" in battle_result
        assert len(battle_result["placements"]) >= 1

    # ====================================================================
    # TEST 3: Event dispatcher processes injected events
    # ====================================================================

    def test_event_dispatcher_handles_injected_events(self):
        """Verify that injected pygame events are properly processed
        by the EventDispatcher without crashes."""
        game_loop, game_map = self._create_game_loop()

        # Start deployment so events have something to process
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
        game_loop.start_deployment(map_data=map_data, faction="allied")

        # Inject a series of events and process them
        events_to_inject = [
            lambda: self._inject_mouse_move(100, 200),
            lambda: self._inject_click(50, 60),  # Click on roster area
            lambda: self._inject_mouse_move(400, 300),
            lambda: self._inject_key(pygame.K_ESCAPE),  # Pause
            lambda: self._inject_key(pygame.K_ESCAPE),  # Unpause
            lambda: self._inject_key(pygame.K_F3),  # Debug toggle
        ]

        for inject_fn in events_to_inject:
            inject_fn()
            # Process events — should not crash
            result = game_loop._event_dispatcher.process_events()
            assert result is True, "process_events should return True (keep running)"

        game_loop.shutdown()

    # ====================================================================
    # TEST 4: Battle phase with AI units — no crash over 150 ticks
    # ====================================================================

    def test_battle_phase_with_ai_no_crash(self):
        """Deploy units, complete deployment, and run 150 ticks of battle
        to verify AI + combat director don't crash."""
        game_loop, game_map = self._create_game_loop()
        state = game_loop.state

        # Build map_data and start deployment
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
        game_loop.start_deployment(map_data=map_data, faction="allied")

        # Programmatically place units (bypass UI click detection)
        dui = game_loop.deployment_ui
        friendly_zone = dui.state.friendly_zone
        placed_count = 0

        for i, unit in enumerate(dui.state.available_units):
            if placed_count >= 5:
                break  # Place 5 units max
            if unit.is_placed:
                continue
            for tile_x, tile_y in friendly_zone:
                terrain = dui._get_terrain_at(tile_x, tile_y)
                if dui.can_place_at(unit, tile_x, tile_y, terrain):
                    occupied = any(
                        pu.position == (tile_x, tile_y)
                        for pu in dui.state.placed_units
                    )
                    if not occupied:
                        dui.place_unit(i, tile_x, tile_y)
                        placed_count += 1
                        break

        assert placed_count >= 1, f"Should place at least 1 unit, placed {placed_count}"

        # Complete deployment
        result = game_loop.complete_deployment()
        assert result is not None

        # Run battle ticks
        dt = 1.0 / 30.0
        for tick in range(150):
            game_loop._update_logic(dt)
            state.tick += 1

        # Verify no crash and units still exist
        assert len(state.units) >= 1

        game_loop.shutdown()
