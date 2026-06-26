"""
CC2-Style Bottom Panel

Complete bottom UI bar mimicking original Close Combat 2 layout:
- Left: Unit roster (all friendly units)
- Center: Selected unit details (morale, ammo, smoke, casualties)
- Right: Minimap with zoom controls

The internal rendering logic has been split into specialized modules under
`bottom_panel/`.  This module remains the public facade and keeps the original
`CC2BottomPanel` API unchanged.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pygame
from pygame import Rect, Surface, draw, font
from pygame.font import Font

from pycc2.presentation.rendering.bottom_panel_command_bar import CommandBarRenderer
from pycc2.presentation.rendering.bottom_panel_icons import (
    create_command_icons,
    create_commander_portrait,
    create_roster_icons,
)
from pycc2.presentation.rendering.bottom_panel_input_handler import (
    BottomPanelInputHandler,
)
from pycc2.presentation.rendering.bottom_panel_minimap_section import MinimapSectionRenderer
from pycc2.presentation.rendering.bottom_panel_roster import RosterRenderer
from pycc2.presentation.rendering.bottom_panel_unit_detail import UnitDetailRenderer
from pycc2.presentation.rendering.bottom_panel_urgency import UrgencyIndicatorRenderer
from pycc2.presentation.rendering.fade_transition import FadeTransition
from pycc2.presentation.rendering.tooltip_manager import TooltipManager
from pycc2.presentation.ui.theme import ThemeManager

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IEventPublisher
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.minimap import Minimap


class CC2BottomPanel:
    """
    CC2-style bottom panel with complete unit management UI.

    Layout (left to right):
    1. Unit Roster - scrollable list of all friendly units
    2. Unit Details - selected unit's full status
    3. Command Bar - 7 commands (Move/Fast/Sneak/Attack/Smoke/Defend/Cancel)
    4. Urgency Indicator - color-coded threat level
    5. Minimap - with +/- zoom buttons
    """

    # Dimensions (scaled to screen)
    PANEL_HEIGHT: int = 130  # Total height of bottom panel (CC2 original: ~120-130px)
    ROSTER_WIDTH: int = 170  # Left unit list width
    DETAIL_WIDTH: int = 240  # Center detail panel width
    COMMAND_WIDTH: int = 180  # Command bar width (next to details)
    URGENCY_WIDTH: int = 60  # Urgency indicator width
    MINIMAP_SIZE: int = 120  # Minimap square size
    COMMAND_BAR_HEIGHT: int = 40  # Command button row height

    # Colors (CC2 military style - Deep Olive Green)
    # Theme-managed: falls back to CC2 originals if ThemeManager not initialized
    _BG_COLOR_DEFAULT = (58, 64, 48)  # Deep olive green (#3A4030) - CC2 original
    _BORDER_COLOR_DEFAULT = (90, 96, 80)  # Olive border (#5A6050) - CC2 original
    _TEXT_COLOR_DEFAULT = (220, 220, 220)
    _HIGHLIGHT_COLOR_DEFAULT = (255, 255, 100)
    _SELECTED_BG_DEFAULT = (40, 45, 55)

    @property
    def BG_COLOR(self) -> tuple[int, int, int]:
        """Panel background color from current theme."""
        return getattr(ThemeManager.get_current().colors, "surface", self._BG_COLOR_DEFAULT)

    @property
    def BORDER_COLOR(self) -> tuple[int, int, int]:
        """Panel border color from current theme."""
        return getattr(ThemeManager.get_current().colors, "border", self._BORDER_COLOR_DEFAULT)

    @property
    def TEXT_COLOR(self) -> tuple[int, int, int]:
        """Primary text color from current theme."""
        return getattr(ThemeManager.get_current().colors, "text_primary", self._TEXT_COLOR_DEFAULT)

    @property
    def HIGHLIGHT_COLOR(self) -> tuple[int, int, int]:
        """Highlight/accent color from current theme."""
        return getattr(ThemeManager.get_current().colors, "warning", self._HIGHLIGHT_COLOR_DEFAULT)

    @property
    def SELECTED_BG(self) -> tuple[int, int, int]:
        """Selected item background color from current theme."""
        return getattr(ThemeManager.get_current().colors, "surface", self._SELECTED_BG_DEFAULT)

    # 3D border colors for raised buttons
    BORDER_LIGHT = (90, 95, 105)  # Top/left highlight
    BORDER_DARK = (20, 22, 28)  # Bottom/right shadow

    # Urgency colors (red=critical -> white=safe)
    URGENCY_COLORS = {
        "CRITICAL": (255, 50, 50),  # Red
        "HIGH": (255, 140, 0),  # Orange
        "MEDIUM": (255, 220, 0),  # Yellow
        "LOW": (100, 200, 100),  # Green
        "SAFE": (200, 200, 200),  # White/Gray
    }

    def __init__(self) -> None:
        self._font_small: Font = None  # type: ignore[assignment]
        self._font_normal: Font = None  # type: ignore[assignment]
        self._font_title: Font = None  # type: ignore[assignment]
        self._font_large: Font = None  # type: ignore[assignment]  # Large font for timer display

        # State
        self._visible: bool = True
        self._selected_unit_id: str | None = None
        self._friendly_units: list[Unit] = []
        self._roster_scroll_offset: int = 0
        self._roster_item_height: int = 26  # P2-A: Increased from 24 for better readability
        self._visible_roster_items: int = 5

        # Battle timer (seconds)
        self._battle_timer: int = 0

        # EventBus reference (set via set_event_bus)
        self._event_bus: IEventPublisher | None = None

        # Zoom levels for minimap
        self._zoom_levels: list[float] = [0.5, 0.75, 1.0, 1.5, 2.0]
        self._current_zoom_index: int = 2  # Default 1.0x

        # Callbacks
        self._on_unit_select: Callable[..., Any] | None = None
        self._on_command: Callable[..., Any] | None = None
        self._on_zoom_change: Callable[..., Any] | None = None

        # Command buttons - CC2 complete 7-command system + Hide + End Battle
        self._commands: list[dict] = [
            {"id": "move", "label": "Move", "key": "Z", "enabled_when_selected": True},
            {"id": "fast", "label": "Fast", "key": "X", "enabled_when_selected": True},
            {"id": "sneak", "label": "Sneak", "key": "S", "enabled_when_selected": True},
            {"id": "attack", "label": "Attack", "key": "C", "enabled_when_selected": True},
            {
                "id": "smoke",
                "label": "Smoke",
                "key": "V",
                "enabled_when_selected": True,
                "needs_smoke_ammo": True,
            },
            {"id": "defend", "label": "Defend", "key": "D", "enabled_when_selected": True},
            {"id": "hide", "label": "Hide", "key": "H", "enabled_when_selected": True},
            {
                "id": "cancel",
                "label": "Cancel",
                "key": "ESC",
                "enabled_when_selected": False,
            },  # Always available
            {
                "id": "end_battle",
                "label": "END BATTLE",
                "key": "E",
                "enabled_when_selected": False,
            },  # Always available
        ]
        self._hovered_command: str | None = None
        self._command_callbacks: dict[str, Callable[..., Any]] = {}

        # Button rects for click detection
        self._button_rects: dict[str, Rect] = {}
        self._roster_item_rects: list[tuple[Rect, str]] = []  # (rect, unit_id)
        self._zoom_in_rect: Rect | None = None
        self._zoom_out_rect: Rect | None = None

        # Icon caches (populated in initialize)
        self._command_icons: dict[str, Surface] = {}
        self._roster_icons: dict[str, Surface] = {}
        self._commander_portrait: Surface | None = None

        # Info toggle buttons state (ALL/STYLE/OUTLINE)
        self._info_mode: str = "ALL"
        self._info_button_rects: dict[str, Rect] = {}

        # Soldier monitor right-click popup state
        self._soldier_member_rects: list[tuple[Rect, object]] = []  # (rect, SquadMember)
        self._active_popup_member: object | None = None  # SquadMember for detail popup
        self._active_popup_rect: Rect | None = None

        # Fade transition for smooth show/hide
        self._fade = FadeTransition(fade_duration=0.2)

        # Mouse interaction state (for hover / click-press feedback)
        self._mouse_pos: tuple[int, int] | None = None
        self._mouse_pressed: bool = False

        # Tooltip manager for button hints
        self._tooltip = TooltipManager(font_size=11, delay=0.4)

        # Tooltip text for each command button
        self._command_tooltips: dict[str, str] = {
            "move": "Move unit to target location [Z]",
            "fast": "Fast move — double speed, lower stealth [X]",
            "sneak": "Sneak move — slow, avoids detection [S]",
            "attack": "Attack mode — fire at enemies [C]",
            "smoke": "Deploy smoke grenade for cover [V]",
            "defend": "Defend / Take cover position [D]",
            "hide": "Hide unit from enemy view [H]",
            "cancel": "Cancel current selection [ESC]",
            "end_battle": "End battle and retreat [E]",
        }

        # Sub-renderers (created in initialize once fonts are ready)
        self._roster_renderer = RosterRenderer(self)
        self._unit_detail_renderer = UnitDetailRenderer(self)
        self._command_bar_renderer = CommandBarRenderer(self)
        self._urgency_renderer = UrgencyIndicatorRenderer(self)
        self._minimap_section_renderer = MinimapSectionRenderer(self)
        self._input_handler = BottomPanelInputHandler(self)

    def initialize(self) -> None:
        """Initialize fonts and icons."""
        if not font.get_init():
            font.init()
        try:
            self._font_small = pygame.font.SysFont("consolas", 13)
            self._font_normal = pygame.font.SysFont("consolas", 15)
            self._font_title = pygame.font.SysFont("consolas", 17)
            self._font_large = pygame.font.SysFont("consolas", 22, bold=True)
        except (pygame.error, OSError, ValueError) as e:
            logging.debug("SysFont fallback to default fonts: %s", e)
            self._font_small = pygame.font.Font(None, 16)
            self._font_normal = pygame.font.Font(None, 20)
            self._font_title = pygame.font.Font(None, 22)
            self._font_large = pygame.font.Font(None, 28)

        self._command_icons = create_command_icons(self.BG_COLOR)
        self._roster_icons = create_roster_icons(self.BG_COLOR)
        self._commander_portrait = create_commander_portrait(self.BG_COLOR, self.BORDER_COLOR)

        # Ensure fade is fully visible immediately (skip animation on init)
        # Without this, render() returns early because _fade.is_visible=False (alpha=0)
        self._fade.reset(visible=True)
        self._visible = True

    def show(self) -> None:
        """Show the panel with fade-in effect."""
        self._visible = True
        self._fade.show()

    def hide(self) -> None:
        """Hide the panel with fade-out effect."""
        self._fade.hide()

    def update(self, dt: float) -> None:
        """Update fade transition animation state.

        Args:
            dt: Delta time in seconds since last frame.
        """
        self._fade.update(dt)
        if not self._fade.is_visible:
            self._visible = False
        # Update tooltip timer
        self._tooltip.update(dt)

    def set_mouse_pos(self, pos: tuple[int, int] | None) -> None:
        """Set current mouse position for hover / click-press rendering.

        Args:
            pos: Screen-space (x, y) coordinates, or None if unavailable.
        """
        self._mouse_pos = pos
        # Also update internal hover tracking for backward compat
        if pos is not None:
            self.handle_mouse_move(pos)

    def set_mouse_pressed(self, pressed: bool) -> None:
        """Set whether the primary mouse button is currently held down.

        Args:
            pressed: True when mouse button is depressed.
        """
        self._mouse_pressed = pressed

    @property
    def is_fading(self) -> bool:
        return self._fade.is_fading

    def set_battle_timer(self, seconds: int) -> None:
        """Update the battle countdown timer."""
        self._battle_timer = seconds

    def set_event_bus(self, event_bus: IEventPublisher | None) -> None:
        """Set the EventBus reference for publishing events."""
        self._event_bus = event_bus

    def set_friendly_units(self, units: list[Unit]) -> None:
        """Set the list of friendly units for the roster."""
        self._friendly_units = sorted(units, key=lambda u: (u.unit_type.value, u.name))

    def set_selected_unit(self, unit_id: str | None) -> None:
        """Set selected unit ID."""
        self._selected_unit_id = unit_id
        # Auto-scroll roster to show selected unit
        if unit_id:
            for i, unit in enumerate(self._friendly_units):
                if unit.id == unit_id:
                    if i < self._roster_scroll_offset:
                        self._roster_scroll_offset = i
                    elif i >= self._roster_scroll_offset + self._visible_roster_items:
                        self._roster_scroll_offset = i - self._visible_roster_items + 1
                    break

    def register_callback(self, command_id: str, callback: Callable[..., Any]) -> None:
        """Register command callback."""
        self._command_callbacks[command_id] = callback

    def get_zoom_level(self) -> float:
        """Get current zoom level."""
        return self._zoom_levels[self._current_zoom_index]

    def zoom_in(self) -> float:
        """Increase zoom level."""
        if self._current_zoom_index < len(self._zoom_levels) - 1:
            self._current_zoom_index += 1
            zoom = self.get_zoom_level()
            if self._on_zoom_change:
                self._on_zoom_change(zoom)
            return zoom
        return self.get_zoom_level()

    def zoom_out(self) -> float:
        """Decrease zoom level."""
        if self._current_zoom_index > 0:
            self._current_zoom_index -= 1
            zoom = self.get_zoom_level()
            if self._on_zoom_change:
                self._on_zoom_change(zoom)
            return zoom
        return self.get_zoom_level()

    def get_info_mode(self) -> str:
        """Get current info display mode.

        Returns:
            One of "ALL", "STYLE", or "OUTLINE"
        """
        return self._info_mode

    def set_info_mode(self, mode: str) -> None:
        """Set active info display mode.

        Args:
            mode: One of "ALL", "STYLE", or "OUTLINE"

        Raises:
            ValueError: If mode is not valid
        """
        valid_modes = {"ALL", "STYLE", "OUTLINE"}
        if mode.upper() not in valid_modes:
            raise ValueError(f"Invalid info mode '{mode}'. Must be one of {valid_modes}")
        self._info_mode = mode.upper()

    def handle_click(self, screen_pos: tuple[int, int]) -> str | None:
        """Handle click on panel. Returns action or None."""
        return self._input_handler.handle_click(screen_pos)

    def handle_right_click(self, screen_pos: tuple[int, int]) -> str | None:
        """Handle right-click on panel. Shows soldier detail popup if clicked on a squad member.

        Returns action string or None.
        """
        return self._input_handler.handle_right_click(screen_pos)

    def handle_mouse_move(self, screen_pos: tuple[int, int]) -> None:
        """Handle mouse move for hover effects."""
        self._input_handler.handle_mouse_move(screen_pos)

    def render(
        self,
        surface: Surface,
        camera: Camera,
        game_map: GameMap,
        minimap: Minimap | None = None,
        time_remaining: float | None = None,
    ) -> None:
        """Render the complete CC2-style bottom panel.

        Args:
            surface: Target surface to render on
            camera: Camera for coordinate transformation
            game_map: Game map data
            minimap: Optional minimap renderer
            time_remaining: Optional battle timer in seconds (None = hide timer)
        """
        if not self._visible or not self._font_small:
            return

        sw, sh = surface.get_size()
        panel_y = sh - self.PANEL_HEIGHT

        # Apply fade transition: render to temp surface, then blit with alpha
        alpha = self._fade.alpha
        use_fade_surface = alpha < 1.0
        if use_fade_surface:
            panel_surface = Surface((sw, self.PANEL_HEIGHT), pygame.SRCALPHA)
            target = panel_surface
            offset_y = 0
        else:
            target = surface
            offset_y = panel_y

        # Draw main background
        panel_rect = Rect(0, offset_y, sw, self.PANEL_HEIGHT)
        draw.rect(target, self.BG_COLOR, panel_rect)
        # Fine 1px bright top border (CC2 style)
        draw.line(target, self.BORDER_COLOR, (0, offset_y), (sw, offset_y), 1)

        # === TIMER DISPLAY (Top-center of panel, CC2 style) ===
        timer_height = 0
        if self._battle_timer > 0:
            timer_height = 26
            minutes = self._battle_timer // 60
            secs = self._battle_timer % 60
            timer_text = f"{minutes}:{secs:02d}"
            # Color based on remaining time
            if self._battle_timer < 30:
                timer_color = (255, 68, 68)  # Red - critical
            elif self._battle_timer < 60:
                timer_color = (255, 255, 0)  # Yellow - warning
            else:
                timer_color = (255, 255, 255)  # White - normal
            # Render centered at top of panel
            timer_surf = self._font_large.render(timer_text, True, timer_color)
            timer_x = (sw - timer_surf.get_width()) // 2
            surface.blit(timer_surf, (timer_x, offset_y + 2))

        # Calculate section positions (shift down if timer is shown)
        section_y = offset_y + 5 + timer_height
        content_height = self.PANEL_HEIGHT - 15 - timer_height

        # === SECTION 1: Unit Roster (Left) ===
        self._roster_renderer.render(target, 5, section_y, self.ROSTER_WIDTH, content_height)

        # === SECTION 2: Unit Details (Center-Left) ===
        detail_x = self.ROSTER_WIDTH + 10
        self._unit_detail_renderer.render(
            target, detail_x, section_y, self.DETAIL_WIDTH, content_height
        )

        # === SECTION 3: Command Bar (Center-Right, next to details) ===
        cmd_x = detail_x + self.DETAIL_WIDTH + 10
        self._command_bar_renderer.render(
            target, cmd_x, section_y, self.COMMAND_WIDTH, content_height, time_remaining
        )

        # === SECTION 4: Urgency Indicator (Right of commands) ===
        urgency_x = cmd_x + self.COMMAND_WIDTH + 5
        self._urgency_renderer.render(
            target, urgency_x, section_y, self.URGENCY_WIDTH, content_height
        )

        # === SECTION 5: Minimap (Far Right) ===
        minimap_x = urgency_x + self.URGENCY_WIDTH + 5
        self._minimap_section_renderer.render(
            target, minimap_x, section_y, self.MINIMAP_SIZE, minimap, camera, game_map
        )

        # Blit the faded panel surface onto the target surface with alpha
        if use_fade_surface:
            panel_surface.set_alpha(int(alpha * 255))
            surface.blit(panel_surface, (0, panel_y))

        # Render tooltip on top of everything (always on main surface)
        self._tooltip.render(surface)
