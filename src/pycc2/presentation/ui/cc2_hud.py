"""
CC2-Style Three-Panel HUD

Close Combat 2 authentic bottom HUD with three-column layout:
- Left (25%): Unit roster with status indicators and hide buttons
- Center (45%): Detailed unit status with AP/AT bars, morale, weapon info
- Right (30%): Command menu with minimap and large action buttons

Reference: Original CC2 screenshot layout specifications.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

import pygame
from pygame import Surface, font
from pygame.font import Font

from pycc2.presentation.rendering.minimap import Minimap
from pycc2.presentation.ui.hud_constants import (
    AP_BAR_COLOR,
    AT_BAR_COLOR,
    BG_COLOR,
    BORDER_COLOR,
    BUTTON_MIN_HEIGHT,
    BUTTON_MIN_WIDTH,
    CENTER_PANEL_RATIO,
    HIGHLIGHT_COLOR,
    ICON_SIZE,
    LEFT_PANEL_RATIO,
    MINIMAP_SIZE,
    PADDING,
    PANEL_BG_DARK,
    PANEL_BG_LIGHT,
    PANEL_BG_MID,
    PANEL_HEIGHT,
    RIGHT_PANEL_RATIO,
    ROW_HEIGHT,
    STATUS_CRITICAL,
    STATUS_DEAD,
    STATUS_HEALTHY,
    STATUS_WOUNDED,
    TEXT_COLOR,
    get_default_commands,
)
from pycc2.presentation.ui.hud_input import CC2HUDInputHandler
from pycc2.presentation.ui.hud_renderer import CC2HUDRenderer

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera


# Enhanced UI rendering feature flag
try:
    from config.rendering_features import is_enhanced_ui_enabled

    _ENHANCED_UI_AVAILABLE = True
    if is_enhanced_ui_enabled():
        from pycc2.presentation.ui.enhanced_ui_renderer import (
            EnhancedUIRenderer,  # noqa: F401
            draw_button,  # noqa: F401
            draw_icon,  # noqa: F401
            draw_panel,  # noqa: F401
        )
except ImportError:
    _ENHANCED_UI_AVAILABLE = False


class CC2HUD:
    """Close Combat 2 style three-panel HUD.

    Implements the classic CC2 bottom panel layout with:
    - Left panel: Scrollable unit roster with health indicators
    - Center panel: Selected unit details with resource bars
    - Right panel: Command buttons and minimap preview

    Usage:
        hud = CC2HUD(screen_width=1024, screen_height=768)
        hud.initialize()
        hud.render(surface, game_state)
        result = hud.handle_click((x, y), game_state)
    """

    # === Layout Constants (CC2 Authentic) — re-exported for backward compat ===
    PANEL_HEIGHT: int = PANEL_HEIGHT
    LEFT_PANEL_RATIO: float = LEFT_PANEL_RATIO
    CENTER_PANEL_RATIO: float = CENTER_PANEL_RATIO
    RIGHT_PANEL_RATIO: float = RIGHT_PANEL_RATIO

    # === Spacing & Sizing ===
    PADDING: int = PADDING
    ROW_HEIGHT: int = ROW_HEIGHT
    BUTTON_MIN_WIDTH: int = BUTTON_MIN_WIDTH
    BUTTON_MIN_HEIGHT: int = BUTTON_MIN_HEIGHT
    ICON_SIZE: int = ICON_SIZE
    MINIMAP_SIZE: int = MINIMAP_SIZE

    # === Color Palette (CC2 Authentic - Warm Military Tone) ===
    BG_COLOR = BG_COLOR
    BORDER_COLOR = BORDER_COLOR
    TEXT_COLOR = TEXT_COLOR
    HIGHLIGHT_COLOR = HIGHLIGHT_COLOR

    # Status colors (CC2 original)
    STATUS_HEALTHY = STATUS_HEALTHY
    STATUS_WOUNDED = STATUS_WOUNDED
    STATUS_CRITICAL = STATUS_CRITICAL
    STATUS_DEAD = STATUS_DEAD

    # Resource bar colors
    AP_BAR_COLOR = AP_BAR_COLOR
    AT_BAR_COLOR = AT_BAR_COLOR

    # Panel backgrounds
    PANEL_BG_DARK = PANEL_BG_DARK
    PANEL_BG_MID = PANEL_BG_MID
    PANEL_BG_LIGHT = PANEL_BG_LIGHT

    def __init__(self, screen_width: int, screen_height: int):
        """Initialize HUD with screen dimensions.

        Args:
            screen_width: Total screen width in pixels
            screen_height: Total screen height in pixels
        """
        self._screen_width = screen_width
        self._screen_height = screen_height

        # Calculate panel widths based on ratios
        self._left_width = int(screen_width * self.LEFT_PANEL_RATIO)
        self._center_width = int(screen_width * self.CENTER_PANEL_RATIO)
        self._right_width = screen_width - self._left_width - self._center_width

        # Font instances (initialized in initialize())
        self._font_title: Font | None = None  # 14px bold
        self._font_normal: Font | None = None  # 11px normal
        self._font_small: Font | None = None  # 9px normal

        # State tracking
        self._visible: bool = True
        self._selected_unit_id: str | None = None
        self._units: list[Unit] = []
        self._scroll_offset: int = 0
        self._max_visible_units: int = 8

        # Game state references
        self._ap_remaining: int = 10
        self._at_remaining: int = 5
        self._timer: str = "00:00"
        self._info_mode: str = "ALL"
        self._game_map: GameMap | None = None
        self._camera: Camera | None = None

        # Minimap component
        self._minimap: Minimap = Minimap(size=self.MINIMAP_SIZE)

        # Interaction state
        self._hovered_command: str | None = None
        self._hovered_unit: str | None = None

        # Click detection rects
        self._unit_rects: list[tuple[pygame.Rect, str]] = []
        self._hide_button_rects: dict[str, pygame.Rect] = {}
        self._command_button_rects: dict[str, pygame.Rect] = {}
        self._info_mode_rects: dict[str, pygame.Rect] = {}

        # Command definitions (CC2 authentic set)
        self._commands: list[dict] = get_default_commands()

        # Icon caches
        self._unit_icons: dict[str, Surface] = {}
        self._command_icons: dict[str, Surface] = {}

        # Cached HUD surface (rebuilt on resize)
        self._hud_surface: Surface | None = None
        self._cached_hud_width: int = 0

        # Callbacks
        self._on_unit_select: Callable[..., Any] | None = None
        self._on_command: Callable[..., Any] | None = None
        self._on_hide_toggle: Callable[..., Any] | None = None

        # Delegated sub-components
        self._renderer = CC2HUDRenderer()
        self._input_handler = CC2HUDInputHandler()

    def initialize(self) -> None:
        """Initialize fonts and generate procedural icons."""
        if not font.get_init():
            font.init()

        try:
            self._font_title = font.SysFont("consolas", 14, bold=True)
            self._font_normal = font.SysFont("consolas", 11)
            self._font_small = font.SysFont("consolas", 9)
        except (OSError, ValueError, RuntimeError) as e:
            logger.debug(f"Font initialization fallback: {e}")
            self._font_title = font.Font(None, 18)
            self._font_normal = font.Font(None, 14)
            self._font_small = font.Font(None, 12)

        self._unit_icons = CC2HUDRenderer.create_unit_icons(self)
        self._command_icons = CC2HUDRenderer.create_command_icons(self)

    def set_visible(self, visible: bool) -> None:
        """Set HUD visibility."""
        self._visible = visible

    def is_visible(self) -> bool:
        """Get current visibility state."""
        return self._visible

    def set_units(self, units: list[Unit]) -> None:
        """Set the complete unit list for the roster.

        Args:
            units: List of all friendly units to display
        """
        self._units = sorted(units, key=lambda u: u.name)

    def set_selected_unit(self, unit_id: str | None) -> None:
        """Set the currently selected unit.

        Args:
            unit_id: Unit ID or None to clear selection
        """
        self._selected_unit_id = unit_id
        if unit_id:
            for i, unit in enumerate(self._units):
                if unit.id == unit_id:
                    if i < self._scroll_offset:
                        self._scroll_offset = i
                    elif i >= self._scroll_offset + self._max_visible_units:
                        self._scroll_offset = i - self._max_visible_units + 1
                    break

    def set_ap(self, ap: int) -> None:
        """Set remaining action points."""
        self._ap_remaining = ap

    def set_at(self, at: int) -> None:
        """Set remaining attack turns."""
        self._at_remaining = at

    def set_timer(self, timer_str: str) -> None:
        """Set timer display string (format: 'MM:SS')."""
        self._timer = timer_str

    def set_game_map(self, game_map: GameMap) -> None:
        """Set the game map for minimap terrain rendering."""
        self._game_map = game_map
        self._minimap.set_map(game_map)

    def set_camera(self, camera: Camera) -> None:
        """Set the camera reference for minimap viewport rendering."""
        self._camera = camera

    def register_callback(self, event_type: str, callback: Callable[..., Any]) -> None:
        """Register event callback.

        Args:
            event_type: One of 'unit_select', 'command', 'hide_toggle'
            callback: Callable to invoke on event
        """
        if event_type == "unit_select":
            self._on_unit_select = callback
        elif event_type == "command":
            self._on_command = callback
        elif event_type == "hide_toggle":
            self._on_hide_toggle = callback

    def render(self, surface: Surface, game_state: dict | None = None) -> None:
        """Render the complete three-panel HUD.

        Args:
            surface: Target pygame surface to render onto
            game_state: Optional dict with units, selected_unit, ap_remaining,
                       at_remaining, timer keys
        """
        if not self._visible or not self._font_normal:
            return

        if game_state:
            self._apply_game_state(game_state)

        sw = surface.get_width()
        panel_y = self._screen_height - self.PANEL_HEIGHT

        # Rebuild HUD surface if width changed
        if sw != self._cached_hud_width:
            self._hud_surface = Surface((sw, self.PANEL_HEIGHT), pygame.SRCALPHA)
            self._cached_hud_width = sw

        assert self._hud_surface is not None

        # Reuse cached HUD surface
        self._hud_surface.fill((*self.BG_COLOR, 245))

        # Draw top border line
        pygame.draw.line(self._hud_surface, self.BORDER_COLOR, (0, 0), (sw, 0), 1)

        # Delegate rendering to renderer
        self._renderer.render(self, self._hud_surface)

        # Blit HUD to main surface
        surface.blit(self._hud_surface, (0, panel_y))

    def handle_click(self, pos: tuple[int, int], game_state: dict | None = None) -> str | None:
        """Process mouse click and return action string or None.

        Args:
            pos: Screen coordinates (x, y)
            game_state: Optional game state for context

        Returns:
            Action string like 'select_unit:xxx', 'command:xxx', or None
        """
        if game_state:
            self._apply_game_state(game_state)

        return self._input_handler.handle_click(self, pos)

    def handle_mouse_move(self, pos: tuple[int, int]) -> None:
        """Update hover states for visual feedback.

        Args:
            pos: Current mouse position
        """
        self._input_handler.handle_mouse_move(self, pos)

    def handle_scroll(self, direction: int) -> None:
        """Handle mouse wheel scrolling for the unit roster.

        Args:
            direction: Scroll direction (+1 or -1)
        """
        self._input_handler.handle_scroll(self, direction)

    def update(self, dt: float) -> None:
        """Update HUD state (called each frame).

        Args:
            dt: Delta time since last update in seconds
        """
        pass

    def show(self) -> None:
        """Show the HUD."""
        self._visible = True

    def hide(self) -> None:
        """Hide the HUD."""
        self._visible = False

    def resize(self, width: int, height: int) -> None:
        """Handle screen resize.

        Args:
            width: New screen width
            height: New screen height
        """
        self._screen_width = width
        self._screen_height = height
        self._left_width = int(width * self.LEFT_PANEL_RATIO)
        self._center_width = int(width * self.CENTER_PANEL_RATIO)
        self._right_width = width - self._left_width - self._center_width
        self._cached_hud_width = 0  # Force rebuild

    def cleanup(self) -> None:
        """Release resources."""
        self._hud_surface = None
        self._unit_icons.clear()
        self._command_icons.clear()

    # ------------------------------------------------------------------
    # Getters for external access
    # ------------------------------------------------------------------

    def get_selected_unit_id(self) -> str | None:
        """Get currently selected unit ID."""
        return self._selected_unit_id

    def get_minimap(self) -> Minimap:
        """Get the minimap component for external use."""
        return self._minimap

    # ------------------------------------------------------------------
    # Backward-compatible delegations to renderer
    # ------------------------------------------------------------------

    def _get_status_color(self, unit: Unit) -> tuple[int, int, int]:
        """Delegate status color lookup to the renderer."""
        return self._renderer._get_status_color(self, unit)

    def _get_morale_color(self, value: int) -> tuple[int, int, int]:
        """Delegate morale color lookup to the renderer."""
        return self._renderer._get_morale_color(self, value)

    def _get_unit_icon_key(self, unit: Unit) -> str:
        """Delegate unit icon key lookup to the renderer."""
        return self._renderer._get_unit_icon_key(unit)

    def _get_crew_string(self, unit: Unit) -> str:
        """Delegate crew string generation to the renderer."""
        return self._renderer._get_crew_string(unit)

    # ==================================================================
    # PRIVATE HELPERS
    # ==================================================================

    def _apply_game_state(self, game_state: dict) -> None:
        """Extract and apply values from game_state dict.

        Args:
            game_state: Dict with optional keys: units, selected_unit,
                       ap_remaining, at_remaining, timer, game_map, camera
        """
        if "units" in game_state:
            self.set_units(game_state["units"])
        if "selected_unit" in game_state:
            self.set_selected_unit(game_state["selected_unit"])
        if "ap_remaining" in game_state:
            self._ap_remaining = game_state["ap_remaining"]
        if "at_remaining" in game_state:
            self._at_remaining = game_state["at_remaining"]
        if "timer" in game_state:
            self._timer = game_state["timer"]
        if "game_map" in game_state:
            self.set_game_map(game_state["game_map"])
        if "camera" in game_state:
            self.set_camera(game_state["camera"])
