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
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

import pygame
from pygame import Rect, Surface, draw, font
from pygame.font import Font

from pycc2.presentation.rendering.minimap import Minimap

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera


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

    # === Layout Constants (CC2 Authentic) ===
    PANEL_HEIGHT: int = 140
    LEFT_PANEL_RATIO: float = 0.25
    CENTER_PANEL_RATIO: float = 0.45
    RIGHT_PANEL_RATIO: float = 0.30

    # === Spacing & Sizing ===
    PADDING: int = 6
    ROW_HEIGHT: int = 18
    BUTTON_MIN_WIDTH: int = 70
    BUTTON_MIN_HEIGHT: int = 22
    ICON_SIZE: int = 16
    MINIMAP_SIZE: int = 100

    # === Color Palette (CC2 Authentic) ===
    BG_COLOR = (20, 22, 26)           # Deep blue-gray background
    BORDER_COLOR = (60, 65, 70)        # Medium gray border
    TEXT_COLOR = (200, 200, 190)       # Off-white text (CC2 font color)
    HIGHLIGHT_COLOR = (255, 220, 100)  # Gold highlight (selected)

    # Status colors
    STATUS_HEALTHY = (80, 180, 80)     # Green
    STATUS_WOUNDED = (200, 180, 60)    # Yellow
    STATUS_CRITICAL = (200, 80, 60)    # Red
    STATUS_DEAD = (40, 40, 40)         # Black

    # Resource bar colors
    AP_BAR_COLOR = (60, 160, 60)       # Green for AP
    AT_BAR_COLOR = (160, 120, 60)      # Orange-brown for AT

    # Panel backgrounds
    PANEL_BG_DARK = (15, 17, 21)
    PANEL_BG_MID = (25, 28, 33)
    PANEL_BG_LIGHT = (35, 38, 45)

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
        self._font_title: Font | None = None      # 14px bold
        self._font_normal: Font | None = None     # 11px normal
        self._font_small: Font | None = None      # 9px normal

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
        self._unit_rects: list[tuple[Rect, str]] = []
        self._hide_button_rects: dict[str, Rect] = {}
        self._command_button_rects: dict[str, Rect] = {}
        self._info_mode_rects: dict[str, Rect] = {}

        # Command definitions (CC2 authentic set)
        self._commands: list[dict] = [
            {"id": "move", "label": "Move", "key": "●", "color": self.STATUS_HEALTHY},
            {"id": "move_fast", "label": "Move Fast", "key": "●", "color": self.STATUS_HEALTHY},
            {"id": "crawl", "label": "Crawl", "key": "○", "color": self.TEXT_COLOR},
            {"id": "fire", "label": "Fire", "key": "●", "color": self.STATUS_WOUNDED},
            {"id": "smoke", "label": "Smoke", "key": "○", "color": self.TEXT_COLOR},
            {"id": "defend", "label": "Defend", "key": "○", "color": self.TEXT_COLOR},
            {"id": "hide", "label": "Hide", "key": "○", "color": self.TEXT_COLOR},
        ]

        # Icon caches
        self._unit_icons: dict[str, Surface] = {}
        self._command_icons: dict[str, Surface] = {}

        # Cached HUD surface (rebuilt on resize)
        self._hud_surface: Surface | None = None
        self._cached_hud_width: int = 0

        # Callbacks
        self._on_unit_select: callable | None = None
        self._on_command: callable | None = None
        self._on_hide_toggle: callable | None = None

    def initialize(self) -> None:
        """Initialize fonts and generate procedural icons."""
        if not font.get_init():
            font.init()

        try:
            self._font_title = font.SysFont('consolas', 14, bold=True)
            self._font_normal = font.SysFont('consolas', 11)
            self._font_small = font.SysFont('consolas', 9)
        except (OSError, ValueError, RuntimeError) as e:
            logger.debug(f"Font initialization fallback: {e}")
            self._font_title = font.Font(None, 18)
            self._font_normal = font.Font(None, 14)
            self._font_small = font.Font(None, 12)

        self._unit_icons = self._create_unit_icons()
        self._command_icons = self._create_command_icons()

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

    def register_callback(self, event_type: str, callback: callable) -> None:
        """Register event callback.

        Args:
            event_type: One of 'unit_select', 'command', 'hide_toggle'
            callback: Callable to invoke on event
        """
        if event_type == 'unit_select':
            self._on_unit_select = callback
        elif event_type == 'command':
            self._on_command = callback
        elif event_type == 'hide_toggle':
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

        # Reuse cached HUD surface
        self._hud_surface.fill((*self.BG_COLOR, 245))

        # Draw top border line
        draw.line(self._hud_surface, self.BORDER_COLOR, (0, 0), (sw, 0), 1)

        # Calculate panel positions
        left_x = 0
        center_x = self._left_width + self.PADDING
        right_x = center_x + self._center_width + self.PADDING

        content_y = self.PADDING + 2
        content_h = self.PANEL_HEIGHT - (self.PADDING * 2) - 2

        # Render three panels
        self._render_left_panel(self._hud_surface, left_x + 2, content_y,
                                self._left_width - 4, content_h)
        self._render_center_panel(self._hud_surface, center_x, content_y,
                                  self._center_width, content_h)
        self._render_right_panel(self._hud_surface, right_x, content_y,
                                 self._right_width - 2, content_h)

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
        if not self._visible:
            return None

        if game_state:
            self._apply_game_state(game_state)

        x, y = pos
        panel_y = self._screen_height - self.PANEL_HEIGHT

        # Convert to HUD-local coordinates
        local_y = y - panel_y
        if local_y < 0 or local_y > self.PANEL_HEIGHT:
            return None

        # Check unit roster items
        for rect, unit_id in self._unit_rects:
            if rect.collidepoint(x, local_y):
                if self._on_unit_select:
                    self._on_unit_select(unit_id)
                return f"select_unit:{unit_id}"

        # Check hide buttons
        for unit_id, rect in self._hide_button_rects.items():
            if rect.collidepoint(x, local_y):
                if self._on_hide_toggle:
                    self._on_hide_toggle(unit_id)
                return f"hide_toggle:{unit_id}"

        # Check command buttons
        for cmd_id, rect in self._command_button_rects.items():
            if rect.collidepoint(x, local_y):
                if self._on_command:
                    self._on_command(cmd_id)
                return f"command:{cmd_id}"

        # Check info mode buttons
        for mode, rect in self._info_mode_rects.items():
            if rect.collidepoint(x, local_y):
                self._info_mode = mode
                return f"info_mode:{mode}"

        return None

    def handle_mouse_move(self, pos: tuple[int, int]) -> None:
        """Update hover states for visual feedback.

        Args:
            pos: Current mouse position
        """
        x, y = pos
        panel_y = self._screen_height - self.PANEL_HEIGHT
        local_y = y - panel_y

        self._hovered_command = None
        self._hovered_unit = None

        if local_y < 0 or local_y > self.PANEL_HEIGHT:
            return

        for cmd_id, rect in self._command_button_rects.items():
            if rect.collidepoint(x, local_y):
                self._hovered_command = cmd_id
                break

        for rect, unit_id in self._unit_rects:
            if rect.collidepoint(x, local_y):
                self._hovered_unit = unit_id
                break

    # ==================================================================
    # PRIVATE RENDERING METHODS
    # ==================================================================

    def _render_left_panel(self, surface: Surface, x: int, y: int,
                           w: int, h: int) -> None:
        """Render left panel: unit roster with status indicators.

        Layout:
        - [Hide] button at top
        - Scrollable unit list (8-10 rows)
        - Each row: status dot + icon + name + Hide button
        """
        # Panel background
        draw.rect(surface, self.PANEL_BG_DARK, Rect(x, y, w, h))
        draw.rect(surface, self.BORDER_COLOR, Rect(x, y, w, h), 1)

        # Title bar with [Hide] button
        title_rect = Rect(x + 4, y + 2, w - 8, 20)
        title_text = "[Hide]"
        title_surf = self._font_normal.render(title_text, True, self.HIGHLIGHT_COLOR)
        surface.blit(title_surf, (title_rect.x + 4, title_rect.y + 3))

        # Separator
        sep_y = y + 22
        draw.line(surface, self.BORDER_COLOR, (x + 4, sep_y), (x + w - 4, sep_y), 1)

        # Unit list
        self._unit_rects = []
        self._hide_button_rects = {}
        list_y = sep_y + 4
        list_h = h - 26
        row_h = self.ROW_HEIGHT

        visible_units = self._units[
            self._scroll_offset:self._scroll_offset + self._max_visible_units
        ]

        for i, unit in enumerate(visible_units):
            row_y = list_y + i * row_h
            if row_y + row_h > y + h - 4:
                break

            is_selected = unit.id == self._selected_unit_id
            row_rect = Rect(x + 4, row_y, w - 8, row_h - 2)

            # Row background (highlighted if selected)
            if is_selected:
                draw.rect(surface, (*self.HIGHLIGHT_COLOR, 30), row_rect)
                draw.rect(surface, self.HIGHLIGHT_COLOR,
                         (row_rect.x, row_rect.y, 2, row_rect.height))

            # Status dot (health indicator)
            status_color = self._get_status_color(unit)
            dot_x = x + 8
            dot_y = row_y + row_h // 2
            draw.circle(surface, status_color, (dot_x, dot_y), 4)
            draw.circle(surface, (*status_color, 180), (dot_x, dot_y), 4, 1)

            # Unit type icon (16x16)
            icon_key = self._get_unit_icon_key(unit)
            icon = self._unit_icons.get(icon_key)
            icon_x = dot_x + 10
            icon_y = row_y + 1
            if icon:
                surface.blit(icon, (icon_x, icon_y))

            # Unit name (truncated to fit)
            name = getattr(unit, 'name', 'Unknown')[:14]
            name_color = self.HIGHLIGHT_COLOR if is_selected else self.TEXT_COLOR
            name_surf = self._font_normal.render(name, True, name_color)
            surface.blit(name_surf, (icon_x + self.ICON_SIZE + 4, row_y + 3))

            # Hide button (text button on right)
            hide_text = "Hide"
            hide_surf = self._font_small.render(hide_text, True, (150, 150, 140))
            hide_w = max(hide_surf.get_width() + 8, self.BUTTON_MIN_WIDTH // 2)
            hide_rect = Rect(x + w - hide_w - 6, row_y + 2, hide_w, row_h - 4)
            draw.rect(surface, (45, 48, 55), hide_rect)
            draw.rect(surface, (70, 73, 80), hide_rect, 1)
            surface.blit(hide_surf,
                        (hide_rect.x + (hide_rect.w - hide_surf.get_width()) // 2,
                         hide_rect.y + (hide_rect.h - hide_surf.get_height()) // 2))

            # Store interaction rects
            self._unit_rects.append((row_rect, unit.id))
            self._hide_button_rects[unit.id] = hide_rect

        # Scrollbar indicator
        total = len(self._units)
        if total > self._max_visible_units:
            scroll_h = max(20, int(list_h * (self._max_visible_units / total)))
            scroll_y = list_y + int((list_h - scroll_h) *
                                   (self._scroll_offset / (total - self._max_visible_units)))
            draw.rect(surface, (80, 80, 90),
                     Rect(x + w - 6, scroll_y, 3, scroll_h))

    def _render_center_panel(self, surface: Surface, x: int, y: int,
                             w: int, h: int) -> None:
        """Render center panel: detailed unit status display.

        Layout:
        - Top: AP/AT/Troop Status/TIMER bar
        - Info mode toggle (ALL/Style/OFF)
        - Morale/AP/AT status bars (green)
        - Selected unit details:
          - Large icon + Name + AP dots
          - Operational status
          - Morale/AMMO/AT bars
          - Weapon info
          - Crew composition
          - Target/Commander/Vehicle/Position
        """
        # Panel background
        draw.rect(surface, self.PANEL_BG_MID, Rect(x, y, w, h))
        draw.rect(surface, self.BORDER_COLOR, Rect(x, y, w, h), 1)

        line_y = y + 4
        line_h = 16

        # === Resource Bar Row ===
        ap_text = f"AP:{'█' * min(self._ap_remaining, 10)}"
        at_text = f"AT:{'█' * min(self._at_remaining, 5)}"
        timer_text = f"TIMER {self._timer}"
        troop_text = "Troop Status"

        resources = f"{ap_text}  {at_text}  {troop_text}  {timer_text}"
        res_surf = self._font_small.render(resources, True, self.TEXT_COLOR)
        surface.blit(res_surf, (x + 6, line_y))
        line_y += line_h + 4

        # === Info Mode Toggle ===
        modes = ["ALL", "STYLE", "OFF"]
        mode_spacing = 50
        mode_start_x = x + 6
        self._info_mode_rects = {}

        for i, mode in enumerate(modes):
            mx = mode_start_x + i * mode_spacing
            mrect = Rect(mx, line_y, 40, 18)
            self._info_mode_rects[mode] = mrect

            is_active = (mode == self._info_mode.upper())
            bg = (60, 65, 75) if is_active else (40, 43, 50)
            tc = self.HIGHLIGHT_COLOR if is_active else (140, 140, 135)
            draw.rect(surface, bg, mrect)
            draw.rect(surface, self.BORDER_COLOR if is_active else (50, 53, 60),
                     mrect, 1)
            msurf = self._font_small.render(mode, True, tc)
            surface.blit(msurf,
                        (mx + (40 - msurf.get_width()) // 2,
                         line_y + (18 - msurf.get_height()) // 2))

        line_y += 22

        # Separator with green tint
        draw.line(surface, (*self.STATUS_HEALTHY, 150),
                 (x + 4, line_y), (x + w - 4, line_y), 1)
        line_y += 6

        # === Status Bars Section (Morale/AP/AT) ===
        if self._selected_unit_id:
            unit = next((u for u in self._units if u.id == self._selected_unit_id), None)
            if unit:
                # Morale value from unit
                morale_val = getattr(getattr(unit, 'morale', None), 'value', 75)
                morale_pct = max(0, min(100, morale_val))

                # Morale bar
                self._draw_status_bar(surface, x + 6, line_y, w - 12, 14,
                                     "Morale", morale_pct,
                                     self._get_morale_color(morale_pct))
                line_y += 18

                # AP bar
                ap_pct = (self._ap_remaining / 10) * 100
                self._draw_status_bar(surface, x + 6, line_y, w - 12, 14,
                                     "AP", ap_pct, self.AP_BAR_COLOR)
                line_y += 18

                # AT bar
                at_pct = (self._at_remaining / 5) * 100
                self._draw_status_bar(surface, x + 6, line_y, w - 12, 14,
                                     "AT", at_pct, self.AT_BAR_COLOR)
                line_y += 20
            else:
                line_y += 54
        else:
            no_sel = self._font_normal.render("No unit selected",
                                              True, (120, 120, 115))
            surface.blit(no_sel, (x + w // 2 - 50, line_y + 20))
            line_y += 54

        # Separator
        draw.line(surface, (50, 53, 60), (x + 4, line_y), (x + w - 4, line_y), 1)
        line_y += 6

        # === Selected Unit Details ===
        if self._selected_unit_id:
            unit = next((u for u in self._units if u.id == self._selected_unit_id), None)
            if unit:
                self._render_unit_details(surface, x + 6, line_y, w - 12, unit)

    def _render_right_panel(self, surface: Surface, x: int, y: int,
                            w: int, h: int) -> None:
        """Render right panel: command menu and minimap.

        Layout:
        - Command menu (expandable list with ●/○ markers)
        - Current unit name (large text)
        - Minimap with terrain preview
        - Large command buttons with icons and previews
        """
        # Panel background
        draw.rect(surface, self.PANEL_BG_LIGHT, Rect(x, y, w, h))
        draw.rect(surface, self.BORDER_COLOR, Rect(x, y, w, h), 1)

        line_y = y + 4

        # === Command Menu (compact list) ===
        menu_h = len(self._commands) * 18 + 4
        menu_rect = Rect(x + 4, line_y, w - 8, menu_h)
        draw.rect(surface, (30, 33, 38), menu_rect)
        draw.rect(surface, (50, 53, 60), menu_rect, 1)

        self._command_button_rects = {}
        for i, cmd in enumerate(self._commands):
            cmd_y = line_y + 4 + i * 18
            cmd_rect = Rect(x + 6, cmd_y, w - 12, 16)
            self._command_button_rects[cmd["id"]] = cmd_rect

            is_hovered = cmd["id"] == self._hovered_command
            bg = (50, 55, 68) if is_hovered else (35, 38, 45)

            draw.rect(surface, bg, cmd_rect)

            # Key marker (● or ○)
            key_color = cmd.get("color", self.TEXT_COLOR)
            key_surf = self._font_normal.render(cmd["key"], True, key_color)
            surface.blit(key_surf, (cmd_rect.x + 4, cmd_y + 1))

            # Command label
            label_surf = self._font_normal.render(cmd["label"], True,
                                                   self.TEXT_COLOR)
            surface.blit(label_surf, (cmd_rect.x + 20, cmd_y + 1))

        line_y += menu_h + 8

        # === Current Unit Name (Large) ===
        if self._selected_unit_id:
            unit = next((u for u in self._units if u.id == self._selected_unit_id), None)
            if unit:
                unit_name = getattr(unit, 'name', 'Unknown')[:16]
                name_surf = self._font_title.render(unit_name, True,
                                                    self.HIGHLIGHT_COLOR)
                # Center the name
                name_x = x + (w - name_surf.get_width()) // 2
                surface.blit(name_surf, (name_x, line_y))
        line_y += 22

        # Separator
        draw.line(surface, (50, 53, 60), (x + 4, line_y), (x + w - 4, line_y), 1)
        line_y += 6

        # === Minimap Preview Area ===
        minimap_size = min(self.MINIMAP_SIZE, w - 16, h - line_y + y - 80)
        if minimap_size > 40:
            mm_x = x + (w - minimap_size) // 2

            # Sync minimap data before rendering
            self._minimap.update_units(self._units)
            self._minimap.set_selected_unit(self._selected_unit_id)
            if self._camera:
                cam = self._camera
                viewport = (
                    cam.position.x,
                    cam.position.y,
                    cam.viewport_width,
                    cam.viewport_height,
                )
                self._minimap.set_camera_viewport(viewport)

            # Render the real minimap (terrain + units + viewport)
            self._minimap.render(surface, mm_x, line_y)

            line_y += minimap_size + 8

        # === Large Command Buttons (bottom section) ===
        if line_y < y + h - 30:
            big_btn_h = 24
            big_cmds = self._commands[:5]
            btn_w = (w - 12 - (len(big_cmds) - 1) * 4) // len(big_cmds)

            for i, cmd in enumerate(big_cmds):
                btn_x = x + 6 + i * (btn_w + 4)
                btn_y = line_y
                btn_rect = Rect(btn_x, btn_y, btn_w, big_btn_h)

                # Store rect (override compact menu rect)
                self._command_button_rects[f"{cmd['id']}_large"] = btn_rect

                is_hovered = cmd["id"] == self._hovered_command
                key_color = cmd.get("color", self.STATUS_HEALTHY)

                # Button background
                bg_color = (45, 50, 62) if is_hovered else (35, 40, 50)
                draw.rect(surface, bg_color, btn_rect)
                draw.rect(surface, key_color if is_hovered else (60, 65, 75),
                         btn_rect, 1)

                # Status dot
                draw.circle(surface, key_color,
                           (btn_x + 10, btn_y + big_btn_h // 2), 5)

                # Label
                lbl_surf = self._font_small.render(cmd["label"][:8], True,
                                                    self.TEXT_COLOR)
                surface.blit(lbl_surf, (btn_x + 20, btn_y + 6))

                # Mini preview rectangle (right side)
                prev_rect = Rect(btn_x + btn_w - 22, btn_y + 3, 18, 18)
                draw.rect(surface, (30, 33, 38), prev_rect)
                draw.rect(surface, (55, 58, 65), prev_rect, 1)

    def _render_unit_details(self, surface: Surface, x: int, y: int,
                             w: int, unit: Unit) -> None:
        """Render detailed information for selected unit.

        Args:
            surface: Target surface
            x, y: Position to start rendering
            w: Available width
            unit: Unit object to display
        """
        line_y = y
        line_h = 15
        small_line_h = 13

        # Unit header: icon + name + AP dots
        icon_key = self._get_unit_icon_key(unit)
        icon = self._unit_icons.get(icon_key)
        if icon:
            surface.blit(icon, (x, line_y))

        name = getattr(unit, 'name', 'Unknown')[:18]
        name_surf = self._font_normal.render(name, True, self.HIGHLIGHT_COLOR)
        surface.blit(name_surf, (x + self.ICON_SIZE + 4, line_y + 2))

        # AP dots indicator
        ap_dots = "●" * min(self._ap_remaining, 5) + "○" * max(0, 5 - self._ap_remaining)
        ap_dot_surf = self._font_small.render(ap_dots, True, self.AP_BAR_COLOR)
        surface.blit(ap_dot_surf, (x + w - 50, line_y + 3))
        line_y += line_h + 4

        # Separator
        draw.line(surface, (50, 53, 60), (x, line_y), (x + w, line_y), 1)
        line_y += 4

        # Operational status
        state_name = getattr(getattr(unit, 'state_machine', None), 'current',
                            type('obj', (object,), {'name': 'IDLE'})).name
        op_text = f"Operational: {state_name}"
        op_surf = self._font_small.render(op_text, True, (180, 180, 175))
        surface.blit(op_surf, (x, line_y))
        line_y += small_line_h + 2

        # Attribute bars (Morale, AMMO, AT)
        morale_val = getattr(getattr(unit, 'morale', None), 'value', 75)
        ammo_val = getattr(getattr(unit, 'weapon', None), 'ammo_remaining', 30)
        ammo_max = getattr(getattr(unit, 'weapon', None), 'max_ammo', 30)
        ammo_pct = (ammo_val / max(ammo_max, 1)) * 100

        # Compact inline bars
        bar_w = (w - 100) // 3

        # Morale
        m_text = f"Morale:"
        m_surf = self._font_small.render(m_text, True, self.TEXT_COLOR)
        surface.blit(m_surf, (x, line_y))
        self._draw_mini_bar(surface, x + 48, line_y, bar_w, 10,
                           morale_val, self._get_morale_color(morale_val))

        # AMMO
        a_text = f"AMMO:"
        a_surf = self._font_small.render(a_text, True, self.TEXT_COLOR)
        surface.blit(a_surf, (x + bar_w + 52, line_y))
        self._draw_mini_bar(surface, x + bar_w + 90, line_y, bar_w, 10,
                           ammo_pct, (100, 150, 255))

        # AT
        at_text = f"AT:"
        at_surf = self._font_small.render(at_text, True, self.TEXT_COLOR)
        surface.blit(at_surf, (x + (bar_w + 38) * 2, line_y))
        self._draw_mini_bar(surface, x + (bar_w + 38) * 2 + 18, line_y,
                           bar_w - 10, 10,
                           (self._at_remaining / 5) * 100, self.AT_BAR_COLOR)
        line_y += 14

        # Weapon info
        weapon_name = getattr(getattr(unit, 'weapon', None), 'name', 'M1 Garand')
        wpn_text = f"Weapon: {weapon_name[:20]}"
        wpn_surf = self._font_small.render(wpn_text, True, (170, 175, 170))
        surface.blit(wpn_surf, (x, line_y))
        line_y += small_line_h

        # Crew composition (if squad)
        crew = self._get_crew_string(unit)
        crew_surf = self._font_small.render(crew, True, (155, 160, 155))
        surface.blit(crew_surf, (x + 8, line_y))
        line_y += small_line_h

        # Additional info lines (if space permits)
        max_y = y + 85
        if line_y < max_y:
            # Target
            target = getattr(unit, 'target_name', None)
            if target:
                tgt_text = f"Target: {target[:15]}"
                tgt_surf = self._font_small.render(tgt_text, True, (160, 165, 160))
                surface.blit(tgt_surf, (x, line_y))
                line_y += small_line_h

        if line_y < max_y:
            # Commander status
            cmdr_health = "Healthy"
            hp_ratio = getattr(getattr(unit, 'health', None), 'hp', 100) / \
                       max(getattr(getattr(unit, 'health', None), 'max_hp', 100), 1)
            if hp_ratio < 0.3:
                cmdr_health = "Wounded"
            elif hp_ratio < 0.6:
                cmdr_health = "Injured"

            cmdr_text = f"Commander: {cmdr_health}  Status: Ready"
            cmdr_surf = self._font_small.render(cmdr_text, True, (155, 160, 155))
            surface.blit(cmdr_surf, (x, line_y))
            line_y += small_line_h

        if line_y < max_y:
            # Vehicle (if applicable)
            vehicle = getattr(unit, 'vehicle_name', None)
            if vehicle:
                veh_text = f"Vehicle: {vehicle[:18]}"
                veh_surf = self._font_small.render(veh_text, True, (155, 160, 155))
                surface.blit(veh_surf, (x, line_y))
                line_y += small_line_h

        if line_y < max_y:
            # Position
            pos = getattr(unit, 'location_name', 'Unknown')
            pos_text = f"Position: {pos[:18]}"
            pos_surf = self._font_small.render(pos_text, True, (155, 160, 155))
            surface.blit(pos_surf, (x, line_y))

    # ==================================================================
    # HELPER METHODS
    # ==================================================================

    def _apply_game_state(self, game_state: dict) -> None:
        """Extract and apply values from game_state dict.

        Args:
            game_state: Dict with optional keys: units, selected_unit,
                       ap_remaining, at_remaining, timer, game_map, camera
        """
        if 'units' in game_state:
            self.set_units(game_state['units'])
        if 'selected_unit' in game_state:
            self.set_selected_unit(game_state['selected_unit'])
        if 'ap_remaining' in game_state:
            self._ap_remaining = game_state['ap_remaining']
        if 'at_remaining' in game_state:
            self._at_remaining = game_state['at_remaining']
        if 'timer' in game_state:
            self._timer = game_state['timer']
        if 'game_map' in game_state:
            self.set_game_map(game_state['game_map'])
        if 'camera' in game_state:
            self.set_camera(game_state['camera'])

    def _get_status_color(self, unit: Unit) -> tuple[int, int, int]:
        """Get status dot color based on unit health.

        Returns:
            RGB tuple: Green/Yellow/Red/Black based on HP ratio
        """
        try:
            hp = getattr(getattr(unit, 'health', None), 'hp', 100)
            hp_max = getattr(getattr(unit, 'health', None), 'max_hp', 100)
            ratio = hp / max(hp_max, 1)

            if ratio >= 0.8:
                return self.STATUS_HEALTHY
            elif ratio >= 0.5:
                return self.STATUS_WOUNDED
            elif ratio > 0:
                return self.STATUS_CRITICAL
            else:
                return self.STATUS_DEAD
        except (TypeError, AttributeError, ZeroDivisionError):
            return self.STATUS_HEALTHY

    def _get_morale_color(self, value: int) -> tuple[int, int, int]:
        """Get morale bar color based on value.

        Args:
            value: Morale percentage (0-100)

        Returns:
            RGB tuple appropriate for morale level
        """
        if value >= 70:
            return self.STATUS_HEALTHY
        elif value >= 45:
            return self.STATUS_WOUNDED
        elif value >= 20:
            return (255, 140, 50)  # Orange
        else:
            return self.STATUS_CRITICAL

    def _get_unit_icon_key(self, unit: Unit) -> str:
        """Map unit type to icon cache key.

        Args:
            unit: Unit object

        Returns:
            String key for icon lookup
        """
        type_name = unit.unit_type.name.lower() if hasattr(unit.unit_type, 'name') else ''
        if 'tank' in type_name or 'armor' in type_name or 'vehicle' in type_name:
            return 'tank'
        elif 'mg' in type_name or 'machine' in type_name:
            return 'mg'
        elif 'sniper' in type_name or 'scout' in type_name:
            return 'sniper'
        elif 'officer' in type_name or 'commander' in type_name:
            return 'commander'
        elif 'at' in type_name or 'anti' in type_name:
            return 'at'
        elif 'mortar' in type_name:
            return 'mortar'
        elif 'medic' in type_name or 'aid' in type_name:
            return 'medic'
        elif 'engineer' in type_name:
            return 'engineer'
        else:
            return 'infantry'

    def _get_crew_string(self, unit: Unit) -> str:
        """Generate crew composition string.

        Args:
            unit: Unit with potential squad_ref attribute

        Returns:
            Formatted crew string like "Crew: Smith MG, AA MG, Mortar"
        """
        squad = getattr(unit, 'squad_ref', None)
        if squad:
            members = getattr(squad, 'members', [])
            if members:
                roles = []
                for m in members[:4]:
                    role = getattr(m, 'role', '?')
                    roles.append(role.replace('_', ' ').title())
                return f"Crew: {', '.join(roles)}"

        return "Crew: Single operator"

    def _draw_status_bar(self, surface: Surface, x: int, y: int,
                         w: int, h: int, label: str, pct: int,
                         color: tuple[int, int, int]) -> None:
        """Draw a labeled status bar with border.

        Args:
            surface: Target surface
            x, y: Position
            w, h: Dimensions
            label: Text label (e.g., "Morale")
            pct: Fill percentage (0-100)
            color: Bar fill color
        """
        # Label
        label_surf = self._font_small.render(f"{label}:", True, self.TEXT_COLOR)
        surface.blit(label_surf, (x, y + (h - label_surf.get_height()) // 2))

        # Bar background with border
        bar_x = x + label_surf.get_width() + 6
        bar_w = w - label_surf.get_width() - 10
        draw.rect(surface, (35, 38, 43), Rect(bar_x - 1, y - 1, bar_w + 2, h + 2))
        draw.rect(surface, (50, 53, 60), Rect(bar_x, y, bar_w, h))

        # Fill
        fill_w = int(bar_w * pct / 100)
        if fill_w > 0:
            draw.rect(surface, color, Rect(bar_x, y, fill_w, h))

    def _draw_mini_bar(self, surface: Surface, x: int, y: int,
                       w: int, h: int, pct: int,
                       color: tuple[int, int, int]) -> None:
        """Draw a compact mini bar without label.

        Args:
            surface: Target surface
            x, y: Position
            w, h: Dimensions
            pct: Fill percentage (0-100)
            color: Fill color
        """
        draw.rect(surface, (35, 38, 43), Rect(x, y, w, h))
        fill_w = int(w * pct / 100)
        if fill_w > 0:
            draw.rect(surface, color, Rect(x, y, fill_w, h))

    def _create_unit_icons(self) -> dict[str, Surface]:
        """Generate 16x16 procedural unit type icons.

        Returns:
            Dict mapping icon keys to pygame Surfaces
        """
        icons: dict[str, Surface] = {}
        bg = self.BG_COLOR

        # Infantry
        s = Surface((16, 16))
        s.fill(bg)
        green = (80, 200, 80)
        dark_green = (50, 150, 50)
        draw.ellipse(s, dark_green, (5, 1, 6, 4))
        draw.line(s, dark_green, (4, 4), (12, 4), 1)
        draw.rect(s, green, (5, 6, 6, 5))
        draw.line(s, green, (5, 7), (3, 9), 1)
        draw.line(s, green, (10, 7), (12, 9), 1)
        draw.line(s, dark_green, (6, 11), (5, 14), 2)
        draw.line(s, dark_green, (9, 11), (10, 14), 2)
        icons['infantry'] = s

        # Tank
        s = Surface((16, 16))
        s.fill(bg)
        tank_gray = (160, 160, 170)
        tank_dark = (120, 120, 130)
        draw.rect(s, tank_gray, (2, 8, 12, 5))
        draw.rect(s, tank_dark, (4, 5, 6, 4))
        draw.line(s, (100, 100, 110), (10, 7), (15, 5), 2)
        draw.rect(s, (80, 80, 90), (1, 12, 14, 2))
        icons['tank'] = s

        # MG
        s = Surface((16, 16))
        s.fill(bg)
        draw.circle(s, (80, 200, 80), (5, 4), 2)
        draw.rect(s, (80, 200, 80), (4, 6, 3, 4))
        draw.line(s, (200, 200, 80), (7, 7), (15, 5), 2)
        draw.rect(s, (100, 100, 60), (7, 6, 4, 3))
        icons['mg'] = s

        # Sniper
        s = Surface((16, 16))
        s.fill(bg)
        draw.ellipse(s, (50, 150, 50), (4, 0, 6, 4))
        draw.line(s, (50, 150, 50), (3, 3), (11, 3), 1)
        draw.rect(s, (80, 200, 80), (4, 5, 6, 4))
        draw.line(s, (60, 60, 60), (11, 5), (15, 1), 1)
        draw.rect(s, (100, 180, 255), (12, 3, 3, 2))
        icons['sniper'] = s

        # Commander
        s = Surface((16, 16))
        s.fill(bg)
        draw.rect(s, (50, 80, 50), (4, 0, 7, 3))
        draw.line(s, (50, 80, 50), (3, 3), (12, 3), 1)
        draw.rect(s, (255, 230, 80), (7, 1, 2, 1))
        draw.rect(s, (80, 200, 80), (4, 5, 6, 5))
        draw.rect(s, (70, 70, 80), (10, 4, 4, 5))
        draw.line(s, (180, 180, 190), (12, 4), (12, 0), 1)
        icons['commander'] = s

        # AT
        s = Surface((16, 16))
        s.fill(bg)
        draw.rect(s, (200, 80, 60), (2, 6, 10, 4))
        draw.polygon(s, (150, 50, 40), [(12, 6), (15, 8), (12, 10)])
        draw.polygon(s, (150, 50, 40), [(2, 6), (4, 3), (5, 6)])
        draw.polygon(s, (150, 50, 40), [(2, 10), (4, 13), (5, 10)])
        icons['at'] = s

        # Mortar
        s = Surface((16, 16))
        s.fill(bg)
        draw.line(s, (140, 140, 150), (4, 14), (10, 4), 3)
        draw.circle(s, (100, 100, 110), (10, 4), 2)
        draw.rect(s, (100, 100, 110), (2, 13, 4, 2))
        icons['mortar'] = s

        # Medic
        s = Surface((16, 16))
        s.fill(bg)
        draw.circle(s, (60, 120, 60), (8, 8), 6)
        draw.rect(s, (240, 240, 240), (6, 3, 4, 10))
        draw.rect(s, (240, 240, 240), (3, 6, 10, 4))
        icons['medic'] = s

        # Engineer
        s = Surface((16, 16))
        s.fill(bg)
        draw.line(s, (120, 120, 130), (3, 13), (10, 6), 2)
        draw.line(s, (180, 180, 190), (8, 4), (10, 6), 2)
        draw.line(s, (180, 180, 190), (10, 6), (12, 4), 2)
        draw.circle(s, (80, 200, 80), (4, 3), 2)
        draw.line(s, (80, 200, 80), (4, 5), (4, 8), 1)
        icons['engineer'] = s

        return icons

    def _create_command_icons(self) -> dict[str, Surface]:
        """Generate 24x24 procedural command icons.

        Returns:
            Dict mapping command IDs to pygame Surfaces
        """
        icons: dict[str, Surface] = {}
        bg = self.BG_COLOR

        # Move
        s = Surface((24, 24))
        s.fill(bg)
        green = (80, 220, 80)
        draw.rect(s, green, (6, 14, 12, 5))
        draw.polygon(s, green, [(8, 14), (14, 14), (12, 6), (10, 6)])
        draw.rect(s, green, (6, 10, 4, 4))
        icons['move'] = s

        # Move Fast
        s = Surface((24, 24))
        s.fill(bg)
        bright = (100, 255, 100)
        draw.circle(s, bright, (10, 4), 3)
        draw.line(s, bright, (10, 7), (12, 14), 2)
        draw.line(s, bright, (10, 9), (6, 11), 2)
        draw.line(s, bright, (10, 9), (15, 8), 2)
        draw.line(s, bright, (12, 14), (7, 19), 2)
        draw.line(s, bright, (12, 14), (17, 19), 2)
        draw.polygon(s, bright, [(18, 10), (22, 13), (18, 16)])
        icons['move_fast'] = s

        # Crawl
        s = Surface((24, 24))
        s.fill(bg)
        olive = (140, 180, 80)
        draw.circle(s, olive, (8, 10), 3)
        draw.line(s, olive, (8, 12), (16, 12), 2)
        draw.line(s, olive, (8, 12), (6, 16), 2)
        draw.line(s, olive, (6, 16), (8, 19), 2)
        draw.line(s, olive, (14, 12), (19, 10), 2)
        icons['crawl'] = s

        # Fire
        s = Surface((24, 24))
        s.fill(bg)
        red = (255, 60, 60)
        cx, cy = 12, 12
        draw.circle(s, red, (cx, cy), 9, 1)
        draw.circle(s, red, (cx, cy), 4, 1)
        draw.circle(s, red, (cx, cy), 1)
        draw.line(s, red, (cx, cy - 11), (cx, cy - 5), 1)
        draw.line(s, red, (cx, cy + 5), (cx, cy + 11), 1)
        draw.line(s, red, (cx - 11, cy), (cx - 5, cy), 1)
        draw.line(s, red, (cx + 5, cy), (cx + 11, cy), 1)
        icons['fire'] = s

        # Smoke
        s = Surface((24, 24))
        s.fill(bg)
        gray = (180, 180, 180)
        draw.circle(s, gray, (8, 15), 5)
        draw.circle(s, (210, 210, 210), (14, 13), 6)
        draw.circle(s, (140, 140, 140), (11, 9), 5)
        draw.circle(s, gray, (6, 11), 4)
        icons['smoke'] = s

        # Defend
        s = Surface((24, 24))
        s.fill(bg)
        shield = (100, 160, 255)
        pts = [(12, 1), (22, 6), (22, 14), (12, 22), (2, 14), (2, 6)]
        draw.polygon(s, shield, pts)
        inner = [(12, 4), (19, 8), (19, 13), (12, 19), (5, 13), (5, 8)]
        draw.polygon(s, (50, 80, 140), inner)
        draw.polygon(s, (200, 220, 255), [(7, 7), (12, 13), (17, 7)])
        icons['defend'] = s

        # Hide
        s = Surface((24, 24))
        s.fill(bg)
        eye = (180, 200, 220)
        epts = [(2, 12), (6, 7), (12, 6), (18, 7), (22, 12),
               (18, 17), (12, 18), (6, 17)]
        draw.polygon(s, eye, epts, 2)
        draw.circle(s, (100, 150, 200), (12, 12), 3)
        draw.circle(s, (40, 40, 40), (12, 12), 1)
        draw.line(s, (255, 60, 60), (4, 4), (20, 20), 2)
        icons['hide'] = s

        return icons
