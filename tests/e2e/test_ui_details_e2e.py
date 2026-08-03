"""E2E tests for UI interaction details (TC-080~089).

Validates Minimap click navigation, Camera zoom/pan, RadialMenu, Tooltip,
KeybindingsOverlay, PauseMenuController, and CombatLog availability at
the UI-component level using real pygame surfaces.

Coverage (场景八 UI 交互细节):
  - TC-080: Minimap click navigation
  - TC-081/TC-082: Camera zoom & pan
  - TC-084: Keybind hint display (KeybindingsOverlay)
  - TC-086: Pause menu (ESC)
  - TC-087: Tooltip display
  - TC-088: Combat log (skip — module archived in v0.6.x)
  - TC-089: Radial menu
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

import pygame
import pytest
from conftest import GameLoopFactory

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.minimap import Minimap
from pycc2.presentation.ui.keybind_manager import KeybindManager
from pycc2.presentation.ui.keybindings_overlay import KeybindingsOverlay
from pycc2.presentation.ui.radial_menu import RadialMenu
from pycc2.presentation.ui.tooltip import Tooltip
from pycc2.services.pause_menu_controller import PauseMenuController


def _make_unit(
    unit_id: str = "u",
    name: str = "Unit",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 80,
    x: int = 5,
    y: int = 5,
) -> Unit:
    """Create a Unit for UI tests (tooltip needs a real unit)."""
    return Unit(
        id=unit_id,
        name=name,
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale),
        weapon=WeaponComponent(
            primary_weapon_id="rifle",
            ammo_remaining=10,
            max_ammo=10,
        ),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=5),
    )


# ===========================================================================
# TEST SUITE
# ===========================================================================


class TestUIDetailsE2E:
    """E2E tests for UI interaction details (TC-080~089)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize headless pygame for each test."""
        pygame.init()
        self.screen = pygame.display.set_mode((1280, 720))
        yield
        pygame.quit()

    def _factory(self):
        return GameLoopFactory(self.screen)

    # ---------- TC-080: Minimap click navigation ----------

    def test_minimap_click_navigation(self):
        """Clicking the minimap centers the camera on the clicked world position.

        Minimap.handle_click converts screen -> minimap-local -> world coords,
        then calls camera.focus_on(world_pos).  After a click within the
        minimap bounds, camera.position must change from its initial value.
        """
        f = self._factory()
        try:
            mini = Minimap(size=160)
            mini.set_map(f.game_map)
            # Set render position (normally done by minimap.render).
            # We set _render_x/_render_y directly to isolate the click
            # navigation logic from the full render pipeline.
            mini._render_x = 10
            mini._render_y = 10

            cam = f.camera
            original_pos = (cam.position.x, cam.position.y)

            # Click at a non-center point on the minimap.
            # The camera starts at map center (width*16, height*16) = (320, 320);
            # clicking at minimap-local (40, 40) maps to world (160, 160),
            # which is different from the initial camera position.
            click_x = 10 + 40  # render_x + 40
            click_y = 10 + 40
            handled = mini.handle_click((click_x, click_y), cam)
            assert handled, "Click within minimap should be handled"

            new_pos = (cam.position.x, cam.position.y)
            assert new_pos != original_pos, (
                f"Camera must move after minimap click: {new_pos} == {original_pos}"
            )

            # Click outside minimap bounds — should not be handled
            assert mini.handle_click((500, 500), cam) is False
        finally:
            f.shutdown()

    # ---------- TC-081 / TC-082: Camera zoom & pan ----------

    def test_camera_zoom_pan(self):
        """Camera.move pans position; adjust_zoom clamps to [MIN_ZOOM, MAX_ZOOM].

        move(dx, dy) translates by dx/zoom, dy/zoom in world units.
        adjust_zoom(factor) multiplies zoom, clamped to [0.25, 4.0].
        screen_to_world / world_to_screen form a consistent round-trip.
        """
        cam = Camera(
            position=Vec2(100.0, 100.0),
            viewport_width=1280,
            viewport_height=720,
        )
        # Pan (move) — zoom=1.0 so delta = (50, -30)
        cam.move(50.0, -30.0)
        assert cam.position.x == pytest.approx(150.0)
        assert cam.position.y == pytest.approx(70.0)

        # Zoom in (factor 2.0)
        cam.adjust_zoom(2.0)
        assert cam.zoom == pytest.approx(2.0)

        # Zoom clamped to MAX_ZOOM (4.0)
        cam.adjust_zoom(10.0)
        assert cam.zoom == cam.MAX_ZOOM

        # Zoom out, clamped to MIN_ZOOM (0.25)
        cam.adjust_zoom(0.001)
        assert cam.zoom == cam.MIN_ZOOM

        # screen_to_world returns a Vec2
        world = cam.screen_to_world((640, 360))
        assert isinstance(world, Vec2)

    # ---------- TC-089: Radial menu ----------

    def test_radial_menu(self):
        """RadialMenu shows at center, tracks hovered command, hides on demand.

        v0.9.0 visual polish replaced context_menu.py with radial_menu.py
        (TD-076a).  The menu appears on right-click-hold with 7 commands
        arranged in a circle.  Hovering on the ring selects a command;
        hovering at center cancels.
        """
        menu = RadialMenu(radius=60, item_radius=22)
        assert menu.is_visible is False
        assert menu.hovered_command is None

        center = (640, 360)
        menu.show(center)
        assert menu.is_visible is True

        # Hover on the ring (dist=55, within [radius-item_radius, radius+item_radius])
        # Ring inner edge = 60-22 = 38; 55 > 38 so a command is selected.
        ring_pos = (center[0] + 55, center[1])
        hovered = menu.update_hover(ring_pos)
        assert hovered is not None, "Hovering on the ring should select a command"
        assert menu.hovered_command is not None

        # Hover at center (dist < 15) → cancel, no command
        menu.update_hover(center)
        assert menu.hovered_command is None

        menu.hide()
        assert menu.is_visible is False

    # ---------- TC-087: Tooltip display ----------

    def test_tooltip_display(self):
        """Tooltip shows after SHOW_DELAY (0.5s) of sustained hover.

        First on_hover(unit, dt) starts the timer.  After accumulating
        >= SHOW_DELAY seconds on the same unit, _visible becomes True.
        Moving away (on_hover(None, dt)) immediately hides the tooltip.

        Note: HIDE_DELAY (0.1s) logic in Tooltip.on_hover else-branch is
        effectively unreachable because switching from a unit to None
        triggers the `unit != target_unit` branch which sets _visible=False
        immediately.  This appears to be a pre-existing design quirk.
        """
        unit = _make_unit("u1", name="Rifle Squad", x=10, y=10)
        tip = Tooltip()
        assert tip._visible is False

        # First hover — starts timer, not yet visible
        tip.on_hover(unit, 0.0)
        assert tip._visible is False

        # Accumulate hover time past SHOW_DELAY (0.5s)
        tip.on_hover(unit, 0.6)
        assert tip._visible is True, "Tooltip should be visible after 0.5s hover"
        assert tip.target_unit is unit

        # Move away — target changes from unit to None, immediately hides
        tip.on_hover(None, 0.0)
        assert tip._visible is False, "Tooltip should hide when mouse leaves unit"

    # ---------- TC-088: Combat log ----------

    def test_combat_log(self):
        """Combat log UI component — skip (module archived in v0.6.x).

        The combat_log.py module was moved to _archive/ during the v0.6.x
        ghost-module cleanup.  No active CombatLog UI component exists in
        the current codebase.  This test is a placeholder until a new
        combat event log is designed (TC-088 marked as not implemented
        in TC_MAPPING.md).
        """
        pytest.skip(
            "CombatLog module archived in v0.6.x; "
            "no active combat_log UI component (TC-088 not implemented)"
        )

    # ---------- TC-084: Keybind hint display ----------

    def test_keybind_hint_display(self):
        """KeybindingsOverlay shows all keybindings and pauses the game.

        Pressing '?' toggles the overlay (V-08 Wave D3).  While visible,
        the game is auto-paused.  KeybindManager provides the binding data
        (DEFAULT_KEYBINDS + ACTION_LABELS) that the overlay renders.
        """
        f = self._factory()
        try:
            # Verify KeybindManager has binding data for the overlay
            kbm = KeybindManager()
            bindings = kbm.get_all_bindings()
            assert "move" in bindings
            assert "cancel" in bindings
            assert bindings["cancel"] == (pygame.K_ESCAPE,)

            # KeybindingsOverlay toggles visibility and pauses the game
            state = f.state
            state.paused = False
            overlay = KeybindingsOverlay(state)
            assert overlay.visible is False

            # Show — should pause the game
            overlay.show()
            assert overlay.visible is True
            assert state.paused is True, "Overlay must pause game while visible"

            # Hide — should restore prior pause state (was False)
            overlay.hide()
            assert overlay.visible is False
            assert state.paused is False
        finally:
            f.shutdown()

    # ---------- TC-086: Pause menu ----------

    def test_pause_menu(self):
        """PauseMenuController toggles active state and renders without crash.

        ESC triggers toggle() in the game loop; the overlay shows Resume /
        Save / Load / Quit buttons.  render() populates button rects;
        clicks on buttons return the action key.
        """
        menu = PauseMenuController()
        assert menu.is_active is False

        # Toggle on (ESC press)
        menu.toggle()
        assert menu.is_active is True

        # Toggle off
        menu.toggle()
        assert menu.is_active is False

        # Activate and render — must not crash, populates button rects
        menu.toggle()
        assert menu.is_active is True
        menu.render(self.screen)

        # Click outside any button → None
        assert menu.handle_click((0, 0)) is None

        # Click on each known button position → return action key
        actions_found = set()
        for key in ("resume", "save", "load", "quit_to_menu"):
            rect = menu._buttons.get(key)
            if rect:
                action = menu.handle_click(rect.center)
                if action:
                    actions_found.add(action)
        assert len(actions_found) > 0, "At least one menu button should be clickable"

        menu.deactivate()
        assert menu.is_active is False
