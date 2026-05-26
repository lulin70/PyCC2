"""
CC2-Style Bottom Panel

Complete bottom UI bar mimicking original Close Combat 2 layout:
- Left: Unit roster (all friendly units)
- Center: Selected unit details (morale, ammo, smoke, casualties)
- Right: Minimap with zoom controls

Reference: Original CC2 screenshot provided by user.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame
from pygame import Rect, Surface, draw, font
from pygame.font import Font

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.entities.game_map import GameMap
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
    BG_COLOR = (58, 64, 48)  # Deep olive green (#3A4030) - CC2 original
    BORDER_COLOR = (90, 96, 80)  # Olive border (#5A6050) - CC2 original
    TEXT_COLOR = (220, 220, 220)
    HIGHLIGHT_COLOR = (255, 255, 100)
    SELECTED_BG = (40, 45, 55)

    # 3D border colors for raised buttons
    BORDER_LIGHT = (90, 95, 105)  # Top/left highlight
    BORDER_DARK = (20, 22, 28)    # Bottom/right shadow

    # Urgency colors (red=critical -> white=safe)
    URGENCY_COLORS = {
        'CRITICAL': (255, 50, 50),    # Red
        'HIGH': (255, 140, 0),         # Orange
        'MEDIUM': (255, 220, 0),       # Yellow
        'LOW': (100, 200, 100),        # Green
        'SAFE': (200, 200, 200),       # White/Gray
    }

    def __init__(self) -> None:
        self._font_small: Font | None = None
        self._font_normal: Font | None = None
        self._font_title: Font | None = None
        self._font_large: Font | None = None  # Large font for timer display

        # State
        self._visible: bool = True
        self._selected_unit_id: str | None = None
        self._friendly_units: list[Unit] = []
        self._roster_scroll_offset: int = 0
        self._roster_item_height: int = 24
        self._visible_roster_items: int = 5

        # Battle timer (seconds)
        self._battle_timer: int = 0

        # EventBus reference (set via set_event_bus)
        self._event_bus: object | None = None

        # Zoom levels for minimap
        self._zoom_levels: list[float] = [0.5, 0.75, 1.0, 1.5, 2.0]
        self._current_zoom_index: int = 2  # Default 1.0x

        # Callbacks
        self._on_unit_select: callable | None = None
        self._on_command: callable | None = None
        self._on_zoom_change: callable | None = None

        # Command buttons - CC2 complete 7-command system + End Battle
        self._commands: list[dict] = [
            {"id": "move", "label": "Move", "key": "Z", "enabled_when_selected": True},
            {"id": "fast", "label": "Fast", "key": "X", "enabled_when_selected": True},
            {"id": "sneak", "label": "Sneak", "key": "S", "enabled_when_selected": True},
            {"id": "attack", "label": "Attack", "key": "C", "enabled_when_selected": True},
            {"id": "smoke", "label": "Smoke", "key": "V", "enabled_when_selected": True, "needs_smoke_ammo": True},
            {"id": "defend", "label": "Defend", "key": "D", "enabled_when_selected": True},
            {"id": "cancel", "label": "Cancel", "key": "ESC", "enabled_when_selected": False},  # Always available
            {"id": "end_battle", "label": "END BATTLE", "key": "E", "enabled_when_selected": False},  # Always available
        ]
        self._hovered_command: str | None = None
        self._command_callbacks: dict[str, callable] = {}

        # Button rects for click detection
        self._button_rects: dict[str, Rect] = {}
        self._roster_item_rects: list[tuple[Rect, str]] = []  # (rect, unit_id)
        self._zoom_in_rect: Rect | None = None
        self._zoom_out_rect: Rect | None = None

        # Icon caches (populated in initialize)
        self._command_icons: dict[str, Surface] = {}
        self._roster_icons: dict[str, Surface] = {}

        # Info toggle buttons state (ALL/STYLE/OUTLINE)
        self._info_mode: str = "ALL"
        self._info_button_rects: dict[str, Rect] = {}

    def initialize(self) -> None:
        """Initialize fonts and icons."""
        if not font.get_init():
            font.init()
        try:
            self._font_small = pygame.font.SysFont('consolas', 13)
            self._font_normal = pygame.font.SysFont('consolas', 15)
            self._font_title = pygame.font.SysFont('consolas', 17)
            self._font_large = pygame.font.SysFont('consolas', 22, bold=True)
        except Exception:
            self._font_small = pygame.font.Font(None, 16)
            self._font_normal = pygame.font.Font(None, 20)
            self._font_title = pygame.font.Font(None, 22)
            self._font_large = pygame.font.Font(None, 28)

        self._command_icons = self._create_command_icons()
        self._roster_icons = self._create_roster_icons()

    def set_battle_timer(self, seconds: int) -> None:
        """Update the battle countdown timer."""
        self._battle_timer = seconds

    def set_event_bus(self, event_bus: object) -> None:
        """Set the EventBus reference for publishing events."""
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Icon generation (procedural, no external assets)
    # ------------------------------------------------------------------

    def _create_command_icons(self) -> dict[str, Surface]:
        """Create 24x24 command button icons procedurally."""
        icons: dict[str, Surface] = {}
        bg = self.BG_COLOR

        # move: green arrow pointing right
        s = Surface((24, 24))
        s.fill(bg)
        green = (80, 220, 80)
        # Arrow shaft
        draw.rect(s, green, Rect(4, 10, 12, 4))
        # Arrow head (triangle)
        draw.polygon(s, green, [(16, 5), (22, 12), (16, 19)])
        icons["move"] = s

        # fast: double arrow right
        s = Surface((24, 24))
        s.fill(bg)
        bright_green = (100, 255, 100)
        draw.rect(s, bright_green, Rect(2, 9, 8, 3))
        draw.polygon(s, bright_green, [(10, 4), (16, 10), (10, 17)])
        draw.rect(s, bright_green, Rect(12, 9, 5, 3))
        draw.polygon(s, bright_green, [(17, 4), (23, 10), (17, 17)])
        icons["fast"] = s

        # sneak: curved arrow (stealth)
        s = Surface((24, 24))
        s.fill(bg)
        olive = (140, 180, 80)
        # Curved path (approximated with line segments)
        pts = [(4, 18), (6, 14), (9, 11), (13, 9), (17, 9)]
        for i in range(len(pts) - 1):
            draw.line(s, olive, pts[i], pts[i + 1], 2)
        # Small arrowhead at end
        draw.polygon(s, olive, [(17, 5), (22, 9), (17, 12)])
        icons["sneak"] = s

        # attack: red crosshair
        s = Surface((24, 24))
        s.fill(bg)
        red = (255, 60, 60)
        cx, cy = 12, 12
        draw.circle(s, red, (cx, cy), 8, 1)
        draw.circle(s, red, (cx, cy), 3, 1)
        draw.line(s, red, (cx, cy - 10), (cx, cy - 4), 1)
        draw.line(s, red, (cx, cy + 4), (cx, cy + 10), 1)
        draw.line(s, red, (cx - 10, cy), (cx - 4, cy), 1)
        draw.line(s, red, (cx + 4, cy), (cx + 10, cy), 1)
        icons["attack"] = s

        # smoke: gray cloud
        s = Surface((24, 24))
        s.fill(bg)
        gray = (180, 180, 180)
        dark_gray = (140, 140, 140)
        draw.circle(s, gray, (9, 14), 5)
        draw.circle(s, gray, (15, 13), 6)
        draw.circle(s, dark_gray, (12, 9), 5)
        draw.circle(s, gray, (7, 10), 4)
        icons["smoke"] = s

        # defend: shield shape
        s = Surface((24, 24))
        s.fill(bg)
        shield_color = (100, 160, 255)
        # Shield outline
        shield_pts = [(12, 2), (21, 7), (21, 14), (12, 22), (3, 14), (3, 7)]
        draw.polygon(s, shield_color, shield_pts, 2)
        # Inner fill (slightly transparent look via darker shade)
        inner_pts = [(12, 5), (18, 9), (18, 13), (12, 19), (6, 13), (6, 9)]
        draw.polygon(s, (50, 80, 140), inner_pts)
        icons["defend"] = s

        # cancel: red X
        s = Surface((24, 24))
        s.fill(bg)
        x_red = (255, 50, 50)
        draw.line(s, x_red, (5, 5), (19, 19), 3)
        draw.line(s, x_red, (19, 5), (5, 19), 3)
        icons["cancel"] = s

        # end_battle: olive flag on pole
        s = Surface((24, 24))
        s.fill(bg)
        olive = (120, 140, 80)
        # Pole
        draw.line(s, (180, 170, 140), (6, 3), (6, 21), 2)
        # Flag (waving)
        draw.polygon(s, olive, [(7, 3), (20, 5), (19, 13), (7, 11)])
        # Border on flag
        draw.polygon(s, (80, 100, 50), [(7, 3), (20, 5), (19, 13), (7, 11)], 1)
        icons["end_battle"] = s

        return icons

    def _create_roster_icons(self) -> dict[str, Surface]:
        """Create 8x8 unit type thumbnail icons procedurally."""
        icons: dict[str, Surface] = {}
        bg = self.BG_COLOR

        # Infantry: green stick figure
        s = Surface((8, 8))
        s.fill(bg)
        green = (80, 200, 80)
        draw.circle(s, green, (4, 1), 1)       # head
        draw.line(s, green, (4, 2), (4, 5), 1)  # body
        draw.line(s, green, (2, 3), (6, 3), 1)  # arms
        draw.line(s, green, (4, 5), (2, 7), 1)  # left leg
        draw.line(s, green, (4, 5), (6, 7), 1)  # right leg
        icons["infantry"] = s

        # MG: green stick figure + thick line (weapon)
        s = Surface((8, 8))
        s.fill(bg)
        draw.circle(s, green, (3, 1), 1)
        draw.line(s, green, (3, 2), (3, 5), 1)
        draw.line(s, green, (1, 3), (5, 3), 1)
        draw.line(s, green, (3, 5), (1, 7), 1)
        draw.line(s, green, (3, 5), (5, 7), 1)
        draw.line(s, (200, 200, 80), (5, 3), (7, 3), 2)  # MG barrel
        icons["mg"] = s

        # Tank: gray rectangle
        s = Surface((8, 8))
        s.fill(bg)
        gray = (160, 160, 170)
        draw.rect(s, gray, Rect(1, 2, 6, 4))   # hull
        draw.rect(s, gray, Rect(3, 1, 3, 2))    # turret
        draw.line(s, (200, 200, 210), (5, 2), (7, 2), 1)  # barrel
        icons["tank"] = s

        # Commander: yellow diamond
        s = Surface((8, 8))
        s.fill(bg)
        yellow = (255, 230, 80)
        draw.polygon(s, yellow, [(4, 0), (7, 4), (4, 7), (1, 4)])
        icons["commander"] = s

        # AT: green stick figure + long line (anti-tank weapon)
        s = Surface((8, 8))
        s.fill(bg)
        draw.circle(s, green, (3, 1), 1)
        draw.line(s, green, (3, 2), (3, 5), 1)
        draw.line(s, green, (1, 3), (5, 3), 1)
        draw.line(s, green, (3, 5), (1, 7), 1)
        draw.line(s, green, (3, 5), (5, 7), 1)
        draw.line(s, (200, 100, 80), (5, 3), (7, 1), 1)  # AT launcher
        icons["at"] = s

        # Mortar: green stick figure + arc
        s = Surface((8, 8))
        s.fill(bg)
        draw.circle(s, green, (3, 2), 1)
        draw.line(s, green, (3, 3), (3, 6), 1)
        draw.line(s, green, (1, 4), (5, 4), 1)
        draw.line(s, green, (3, 6), (1, 7), 1)
        draw.line(s, green, (3, 6), (5, 7), 1)
        draw.arc(s, (200, 200, 80), Rect(4, 0, 4, 6), 0, math.pi / 2, 1)  # mortar arc
        icons["mortar"] = s

        # Sniper: green stick figure + long thin line
        s = Surface((8, 8))
        s.fill(bg)
        draw.circle(s, green, (3, 1), 1)
        draw.line(s, green, (3, 2), (3, 5), 1)
        draw.line(s, green, (1, 3), (5, 3), 1)
        draw.line(s, green, (3, 5), (1, 7), 1)
        draw.line(s, green, (3, 5), (5, 7), 1)
        draw.line(s, (180, 220, 255), (5, 3), (7, 2), 1)  # sniper rifle
        icons["sniper"] = s

        # Medic: white cross
        s = Surface((8, 8))
        s.fill(bg)
        white = (240, 240, 240)
        draw.rect(s, white, Rect(3, 1, 2, 6))  # vertical bar
        draw.rect(s, white, Rect(1, 3, 6, 2))  # horizontal bar
        icons["medic"] = s

        return icons

    def set_friendly_units(self, units: list[Unit]) -> None:
        """Set the list of friendly units for the roster."""
        self._friendly_units = sorted(
            units,
            key=lambda u: (u.unit_type.value if hasattr(u.unit_type, 'value') else 0, u.name)
        )

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

    def register_callback(self, command_id: str, callback: callable) -> None:
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
        if not self._visible:
            return None

        x, y = screen_pos

        # Check roster items
        for rect, unit_id in self._roster_item_rects:
            if rect.collidepoint(x, y):
                if self._on_unit_select:
                    self._on_unit_select(unit_id)
                return f"select_unit:{unit_id}"

        # Check command buttons
        for cmd_id, rect in self._button_rects.items():
            if rect.collidepoint(x, y):
                # End Battle button: publish event to EventBus
                if cmd_id == "end_battle" and self._event_bus is not None:
                    self._event_bus.publish({"event_type": "end_battle"})
                callback = self._command_callbacks.get(cmd_id)
                if callback:
                    callback()
                return f"command:{cmd_id}"

        # Check zoom buttons
        if self._zoom_in_rect and self._zoom_in_rect.collidepoint(x, y):
            return f"zoom:{self.zoom_in()}"
        if self._zoom_out_rect and self._zoom_out_rect.collidepoint(x, y):
            return f"zoom:{self.zoom_out()}"

        # Check info toggle buttons
        for mode, rect in self._info_button_rects.items():
            if rect.collidepoint(x, y):
                self._info_mode = mode
                return f"info_mode:{mode}"

        return None

    def handle_mouse_move(self, screen_pos: tuple[int, int]) -> None:
        """Handle mouse move for hover effects."""
        x, y = screen_pos
        self._hovered_command = None

        for cmd_id, rect in self._button_rects.items():
            if rect.collidepoint(x, y):
                self._hovered_command = cmd_id
                break

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

        # Draw main background
        panel_rect = Rect(0, panel_y, sw, self.PANEL_HEIGHT)
        draw.rect(surface, self.BG_COLOR, panel_rect)
        # Fine 1px bright top border (CC2 style)
        draw.line(surface, self.BORDER_COLOR, (0, panel_y), (sw, panel_y), 1)

        # === TIMER DISPLAY (Top-center of panel, CC2 style) ===
        timer_height = 0
        if self._battle_timer > 0:
            timer_height = 26
            minutes = self._battle_timer // 60
            secs = self._battle_timer % 60
            timer_text = f"{minutes}:{secs:02d}"
            # Color based on remaining time
            if self._battle_timer < 30:
                timer_color = (255, 68, 68)    # Red - critical
            elif self._battle_timer < 60:
                timer_color = (255, 255, 0)    # Yellow - warning
            else:
                timer_color = (255, 255, 255)  # White - normal
            # Render centered at top of panel
            timer_surf = self._font_large.render(timer_text, True, timer_color)
            timer_x = (sw - timer_surf.get_width()) // 2
            surface.blit(timer_surf, (timer_x, panel_y + 2))

        # Calculate section positions (shift down if timer is shown)
        section_y = panel_y + 5 + timer_height
        content_height = self.PANEL_HEIGHT - 15 - timer_height

        # === SECTION 1: Unit Roster (Left) ===
        self._render_roster(surface, 5, section_y, self.ROSTER_WIDTH, content_height)

        # === SECTION 2: Unit Details (Center-Left) ===
        detail_x = self.ROSTER_WIDTH + 10
        self._render_unit_details(surface, detail_x, section_y, self.DETAIL_WIDTH, content_height)

        # === SECTION 3: Command Bar (Center-Right, next to details) ===
        cmd_x = detail_x + self.DETAIL_WIDTH + 10
        self._render_command_bar(surface, cmd_x, section_y, self.COMMAND_WIDTH, content_height, time_remaining)

        # === SECTION 4: Urgency Indicator (Right of commands) ===
        urgency_x = cmd_x + self.COMMAND_WIDTH + 5
        self._render_urgency_indicator(surface, urgency_x, section_y, self.URGENCY_WIDTH, content_height)

        # === SECTION 5: Minimap (Far Right) ===
        minimap_x = urgency_x + self.URGENCY_WIDTH + 5
        self._render_minimap_section(surface, minimap_x, section_y, self.MINIMAP_SIZE, minimap, camera, game_map)

    def _render_roster(
        self, surface: Surface, x: int, y: int, w: int, h: int
    ) -> None:
        """Render the unit roster list."""
        # Background
        draw.rect(surface, (30, 33, 38), Rect(x, y, w, h))
        draw.rect(surface, self.BORDER_COLOR, Rect(x, y, w, h), 1)

        # Title
        title = self._font_title.render("TROOPS", True, self.HIGHLIGHT_COLOR)
        surface.blit(title, (x + 5, y + 2))

        # Separator line under title
        draw.line(surface, (45, 48, 55), (x, y + 18), (x + w, y + 18), 1)

        # Unit list
        self._roster_item_rects = []
        visible_units = self._friendly_units[
            self._roster_scroll_offset:self._roster_scroll_offset + self._visible_roster_items
        ]

        item_y = y + 22
        for unit in visible_units:
            is_selected = unit.id == self._selected_unit_id
            item_rect = Rect(x + 2, item_y, w - 4, self._roster_item_height)

            # Background
            bg_color = self.SELECTED_BG if is_selected else (35, 38, 43)
            draw.rect(surface, bg_color, item_rect)

            # Selection highlight: 2px bright left indicator bar
            if is_selected:
                draw.rect(surface, self.HIGHLIGHT_COLOR, Rect(x + 2, item_y, 2, self._roster_item_height))

            # Unit type thumbnail icon (8x8)
            icon_key = self._map_unit_type_to_icon_key(unit)
            roster_icon = self._roster_icons.get(icon_key)
            if roster_icon:
                surface.blit(roster_icon, (x + 7, item_y + 4))

            # Unit name (truncated) — Unit uses .name, not .display_name
            name = getattr(unit, 'display_name', None) or getattr(unit, 'name', 'Unknown')
            name = str(name)[:14]
            text_color = self.HIGHLIGHT_COLOR if is_selected else self.TEXT_COLOR
            name_surf = self._font_small.render(name, True, text_color)
            surface.blit(name_surf, (x + 18, item_y + 5))

            # Health bar with 1px dark border — HealthComponent uses .hp/.max_hp, not .current/.max
            hp_current = getattr(unit.health, 'hp', getattr(unit.health, 'current', 0))
            hp_max = getattr(unit.health, 'max_hp', getattr(unit.health, 'max', 1))
            hp_ratio = hp_current / max(hp_max, 1)
            bar_width = 50
            bar_x = x + w - bar_width - 30
            # Dark border around health bar
            draw.rect(surface, (40, 42, 48), Rect(bar_x - 1, item_y + 7, bar_width + 2, 10))
            draw.rect(surface, (60, 60, 60), Rect(bar_x, item_y + 8, bar_width, 8))
            hp_color = (
                (255, 50, 50) if hp_ratio < 0.3 else
                (255, 200, 0) if hp_ratio < 0.6 else
                (50, 200, 50)
            )
            draw.rect(surface, hp_color, Rect(bar_x, item_y + 8, int(bar_width * hp_ratio), 8))

            self._roster_item_rects.append((item_rect, unit.id))
            item_y += self._roster_item_height

        # Scroll indicator
        total_items = len(self._friendly_units)
        if total_items > self._visible_roster_items:
            scroll_bar_h = h * (self._visible_roster_items / total_items)
            scroll_bar_y = y + 22 + (h - 22) * (self._roster_scroll_offset / (total_items - self._visible_roster_items))
            draw.rect(surface, (80, 80, 80), Rect(x + w - 4, scroll_bar_y, 3, scroll_bar_h))

    def _map_unit_type_to_icon_key(self, unit: Unit) -> str:
        """Map a unit's type to the roster icon key."""
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
        else:
            return 'infantry'

    def _render_unit_details(
        self, surface: Surface, x: int, y: int, w: int, h: int
    ) -> None:
        """Render detailed info for selected unit."""
        # Background
        draw.rect(surface, (30, 33, 38), Rect(x, y, w, h))
        draw.rect(surface, self.BORDER_COLOR, Rect(x, y, w, h), 1)

        if not self._selected_unit_id:
            no_sel = self._font_normal.render("No unit selected", True, (128, 128, 128))
            surface.blit(no_sel, (x + 10, y + h // 2 - 10))
            return

        # Find selected unit
        unit = next((u for u in self._friendly_units if u.id == self._selected_unit_id), None)
        if not unit:
            return

        line_y = y + 5
        line_height = 18

        # Title — Unit uses .name, not .display_name
        display_name = getattr(unit, 'display_name', None) or getattr(unit, 'name', 'Unknown')
        title = self._font_title.render(str(display_name), True, self.HIGHLIGHT_COLOR)
        surface.blit(title, (x + 8, line_y))
        line_y += line_height + 5

        # Separator line under title
        draw.line(surface, (45, 48, 55), (x, line_y - 3), (x + w, line_y - 3), 1)

        # Type and faction
        type_str = f"Type: {unit.unit_type.name[:15]}"
        faction_str = f"Faction: {unit.faction.name}"
        surface.blit(self._font_small.render(type_str, True, self.TEXT_COLOR), (x + 8, line_y))
        line_y += line_height
        surface.blit(self._font_small.render(faction_str, True, self.TEXT_COLOR), (x + 8, line_y))
        line_y += line_height + 5

        # Health — HealthComponent uses .hp/.max_hp
        hp_current = getattr(unit.health, 'hp', getattr(unit.health, 'current', 0))
        hp_max = getattr(unit.health, 'max_hp', getattr(unit.health, 'max', 1))
        hp_text = f"HP: {hp_current}/{hp_max}"
        hp_color = (255, 80, 80) if hp_current < hp_max * 0.3 else self.TEXT_COLOR
        surface.blit(self._font_normal.render(hp_text, True, hp_color), (x + 8, line_y))
        # Health bar with 1px dark border
        bar_w = w - 120
        draw.rect(surface, (40, 42, 48), Rect(x + 109, line_y + 1, bar_w + 2, 14))
        draw.rect(surface, (60, 60, 60), Rect(x + 110, line_y + 2, bar_w, 12))
        hp_ratio = hp_current / max(hp_max, 1)
        draw.rect(surface, (50, 180, 50), Rect(x + 110, line_y + 2, int(bar_w * hp_ratio), 12))
        line_y += line_height + 3

        # Morale — MoraleComponent uses .value, not .current
        morale_val = getattr(unit.morale, 'value', getattr(unit.morale, 'current', 75)) if hasattr(unit, 'morale') else 75
        morale_text = f"Morale: {morale_val}%"
        morale_color = (
            (255, 80, 80) if morale_val < 30 else
            (255, 200, 0) if morale_val < 60 else
            (80, 200, 80)
        )
        surface.blit(self._font_normal.render(morale_text, True, morale_color), (x + 8, line_y))
        # Morale bar with 1px dark border
        draw.rect(surface, (40, 42, 48), Rect(x + 109, line_y + 1, bar_w + 2, 14))
        draw.rect(surface, (60, 60, 60), Rect(x + 110, line_y + 2, bar_w, 12))
        draw.rect(surface, morale_color, Rect(x + 110, line_y + 2, int(bar_w * morale_val / 100), 12))
        line_y += line_height + 3

        # Ammo
        # Ammo — WeaponComponent uses .ammo_remaining/.max_ammo
        ammo_current = getattr(unit.weapon, 'ammo_remaining', getattr(unit.weapon, 'ammo', 30)) if hasattr(unit, 'weapon') else 30
        ammo_max = getattr(unit.weapon, 'max_ammo', 30) if hasattr(unit, 'weapon') else 30
        ammo_text = f"Ammo: {ammo_current}/{ammo_max}"
        surface.blit(self._font_normal.render(ammo_text, True, self.TEXT_COLOR), (x + 8, line_y))
        # Ammo bar with 1px dark border
        draw.rect(surface, (40, 42, 48), Rect(x + 109, line_y + 1, bar_w + 2, 14))
        draw.rect(surface, (60, 60, 60), Rect(x + 110, line_y + 2, bar_w, 12))
        ammo_ratio = ammo_current / max(ammo_max, 1)
        draw.rect(surface, (100, 150, 255), Rect(x + 110, line_y + 2, int(bar_w * ammo_ratio), 12))
        line_y += line_height + 3

        # Smoke grenades (if applicable)
        smoke_count = getattr(unit, 'smoke_grenades', 2)
        smoke_text = f"Smoke: {smoke_count}"
        surface.blit(self._font_normal.render(smoke_text, True, (200, 200, 100)), (x + 8, line_y))
        line_y += line_height + 3

        # Casualties
        squad_size = getattr(unit, 'squad_size', 10)
        casualties = getattr(unit, 'casualties', 0)
        alive = squad_size - casualties
        cas_text = f"Squad: {alive}/{squad_size} ({casualties} KIA)"
        cas_color = (255, 100, 100) if casualties > 0 else self.TEXT_COLOR
        surface.blit(self._font_small.render(cas_text, True, cas_color), (x + 8, line_y))
        line_y += line_height + 3

        # Status
        state_name = unit.state_machine.current.name if hasattr(unit, 'state_machine') else "IDLE"
        status_text = f"Status: {state_name}"
        surface.blit(self._font_small.render(status_text, True, (180, 180, 180)), (x + 8, line_y))
        line_y += line_height + 3

        # Soldier Monitor (when unit has squad_ref)
        squad_ref = getattr(unit, 'squad_ref', None)
        if squad_ref is not None and line_y < y + h - 10:
            self._render_soldier_monitor(surface, x, line_y, w, y + h - line_y, squad_ref)

    def _render_soldier_monitor(
        self, surface: Surface, x: int, y: int, w: int, h: int, squad: object
    ) -> None:
        """Render soldier monitor showing individual squad member details.

        Displays:
        - State icon (✓ healthy, ⚠ wounded, ✗ dead, ◉ pinned, ⚿ surrendered)
        - HP bar for each member
        - Role name (rifleman, mg_gunner, etc.)
        - Experience level
        """
        # Separator line
        draw.line(surface, (45, 48, 55), (x, y), (x + w, y), 1)
        y += 3

        # Title
        title = self._font_small.render("SQUAD MEMBERS", True, self.HIGHLIGHT_COLOR)
        surface.blit(title, (x + 5, y))
        y += 16

        members = getattr(squad, 'members', [])
        member_line_h = 14
        # State icon mapping
        state_icons = {
            "healthy": "✓",
            "wounded": "⚠",
            "pinned": "◉",
            "dead": "✗",
            "surrendered": "⚯",
        }
        state_colors = {
            "healthy": (80, 200, 80),
            "wounded": (255, 200, 50),
            "pinned": (255, 220, 50),
            "dead": (200, 60, 60),
            "surrendered": (150, 150, 150),
        }

        for member in members:
            if y + member_line_h > y + h:
                break

            state_name = member.state.value if hasattr(member.state, 'value') else str(member.state)
            icon = state_icons.get(state_name, "?")
            icon_color = state_colors.get(state_name, (180, 180, 180))

            # State icon
            icon_surf = self._font_small.render(icon, True, icon_color)
            surface.blit(icon_surf, (x + 5, y))

            # Personal name (e.g., "Pvt. Johnson") — fall back to role if no name
            personal_name = getattr(member, 'name', '')
            if not personal_name:
                personal_name = getattr(member, 'role', '?')
            display_name = personal_name[:14]
            name_surf = self._font_small.render(display_name, True, self.TEXT_COLOR)
            surface.blit(name_surf, (x + 20, y))

            # HP bar
            hp = getattr(member, 'hp', 0)
            hp_bar_x = x + 80
            hp_bar_w = w - 115
            hp_ratio = max(0, min(1, hp / 100))
            draw.rect(surface, (40, 42, 48), Rect(hp_bar_x, y + 2, hp_bar_w, 9))
            hp_color = (80, 200, 80) if hp_ratio > 0.5 else (255, 200, 50) if hp_ratio > 0.25 else (220, 60, 60)
            draw.rect(surface, hp_color, Rect(hp_bar_x, y + 2, int(hp_bar_w * hp_ratio), 9))

            # Experience level
            exp = getattr(member, 'experience', 0)
            exp_grade = "G5" if exp >= 80 else "G4" if exp >= 60 else "G3" if exp >= 40 else "G2" if exp >= 20 else "G1"
            exp_surf = self._font_small.render(exp_grade, True, (150, 150, 180))
            surface.blit(exp_surf, (x + w - 30, y))

            y += member_line_h

    def _render_urgency_indicator(
        self, surface: Surface, x: int, y: int, w: int, h: int
    ) -> None:
        """Render color-coded urgency/threat indicator."""
        # Background
        draw.rect(surface, (30, 33, 38), Rect(x, y, w, h))
        draw.rect(surface, self.BORDER_COLOR, Rect(x, y, w, h), 1)

        # Title
        title = self._font_small.render("URGENCY", True, self.TEXT_COLOR)
        surface.blit(title, (x + 5, y + 3))

        # Determine urgency level based on selected unit
        urgency = 'SAFE'
        urgency_value = 0

        if self._selected_unit_id:
            unit = next((u for u in self._friendly_units if u.id == self._selected_unit_id), None)
            if unit:
                hp_current = getattr(unit.health, 'hp', getattr(unit.health, 'current', 0))
                hp_max = getattr(unit.health, 'max_hp', getattr(unit.health, 'max', 1))
                hp_ratio = hp_current / max(hp_max, 1)
                morale = getattr(unit.morale, 'value', getattr(unit.morale, 'current', 75)) if hasattr(unit, 'morale') else 75

                # Calculate urgency (0-100)
                urgency_value = int((1 - hp_ratio) * 50 + (1 - morale / 100) * 50)

                if urgency_value >= 80:
                    urgency = 'CRITICAL'
                elif urgency_value >= 60:
                    urgency = 'HIGH'
                elif urgency_value >= 40:
                    urgency = 'MEDIUM'
                elif urgency_value >= 20:
                    urgency = 'LOW'

        # Draw vertical urgency bar
        bar_x = x + w // 2 - 15
        bar_y = y + 25
        bar_h = h - 35
        bar_w = 30

        # Background
        draw.rect(surface, (40, 40, 40), Rect(bar_x, bar_y, bar_w, bar_h))

        # Filled portion (bottom-up)
        fill_h = int(bar_h * urgency_value / 100)
        color = self.URGENCY_COLORS.get(urgency, self.URGENCY_COLORS['SAFE'])
        draw.rect(surface, color, Rect(bar_x, bar_y + bar_h - fill_h, bar_w, fill_h))

        # Border
        draw.rect(surface, self.BORDER_COLOR, Rect(bar_x, bar_y, bar_w, bar_h), 1)

        # Labels
        labels = ['!', '!!', '!!!', '', '']
        label_idx = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'SAFE'].index(urgency)
        label = self._font_small.render(labels[label_idx], True, color)
        surface.blit(label, (bar_x + 8, bar_y + bar_h - fill_h - 15 if fill_h > 15 else bar_y + 5))

    def _render_minimap_section(
        self,
        surface: Surface,
        x: int,
        y: int,
        size: int,
        minimap: Minimap | None,
        camera: Camera,
        game_map: GameMap,
    ) -> None:
        """Render minimap with zoom controls and info toggle buttons."""
        # Info toggle buttons (above minimap)
        self._render_info_toggle_buttons(surface, x, y, size)

        # Adjust minimap position to account for info buttons (22px height for buttons)
        minimap_y = y + 24
        minimap_size = size - 24

        # Background for minimap area
        draw.rect(surface, (30, 33, 38), Rect(x, minimap_y, size, minimap_size))
        draw.rect(surface, self.BORDER_COLOR, Rect(x, minimap_y, size, minimap_size), 1)

        # Render minimap if available
        if minimap:
            minimap.render(surface, x + 2, minimap_y + 2)

        # Zoom controls (+/- buttons)
        btn_size = 20
        btn_y = minimap_y + minimap_size - btn_size - 2

        # Zoom out (-)
        self._zoom_out_rect = Rect(x + 2, btn_y, btn_size, btn_size)
        draw.rect(surface, (60, 60, 70), self._zoom_out_rect)
        draw.rect(surface, self.BORDER_COLOR, self._zoom_out_rect, 1)
        minus = self._font_normal.render("-", True, self.TEXT_COLOR)
        surface.blit(minus, (x + 7, btn_y + 2))

        # Zoom in (+)
        self._zoom_in_rect = Rect(x + size - btn_size - 2, btn_y, btn_size, btn_size)
        draw.rect(surface, (60, 60, 70), self._zoom_in_rect)
        draw.rect(surface, self.BORDER_COLOR, self._zoom_in_rect, 1)
        plus = self._font_normal.render("+", True, self.TEXT_COLOR)
        surface.blit(plus, (x + size - btn_size + 5, btn_y + 2))

        # Zoom level indicator
        zoom_lvl = self._current_zoom_index + 1
        zoom_text = self._font_small.render(f"{zoom_lvl}/5", True, (150, 150, 150))
        surface.blit(zoom_text, (x + size // 2 - 10, btn_y + 4))

    def _render_info_toggle_buttons(
        self, surface: Surface, x: int, y: int, width: int
    ) -> None:
        """Render info mode toggle buttons (ALL/Style/Outline) above minimap.

        Args:
            surface: Target surface
            x, y: Top-left position for button row
            width: Total width available for buttons
        """
        # Button configuration
        modes = ["ALL", "STYLE", "OUTLINE"]
        btn_width = 35
        btn_height = 20
        spacing = 3

        # Calculate total width and center the buttons
        total_width = len(modes) * btn_width + (len(modes) - 1) * spacing
        start_x = x + (width - total_width) // 2

        self._info_button_rects = {}

        for i, mode in enumerate(modes):
            btn_x = start_x + i * (btn_width + spacing)
            btn_rect = Rect(btn_x, y + 2, btn_width, btn_height)

            # Store rect for click detection
            self._info_button_rects[mode] = btn_rect

            is_active = (mode == self._info_mode)

            # Button background color based on state
            if is_active:
                bg_color = (70, 80, 60)       # Active: lighter olive
                text_color = self.HIGHLIGHT_COLOR
            else:
                bg_color = (45, 50, 40)        # Inactive: darker olive
                text_color = (160, 160, 150)   # Dimmed text

            draw.rect(surface, bg_color, btn_rect)

            # 3D raised border effect (same style as command buttons but smaller)
            if is_active:
                # Active button: pressed look (inverted borders)
                draw.line(surface, self.BORDER_DARK, (btn_rect.left, btn_rect.top), (btn_rect.right, btn_rect.top), 1)
                draw.line(surface, self.BORDER_DARK, (btn_rect.left, btn_rect.top), (btn_rect.left, btn_rect.bottom), 1)
                draw.line(surface, self.BORDER_LIGHT, (btn_rect.left, btn_rect.bottom), (btn_rect.right, btn_rect.bottom), 1)
                draw.line(surface, self.BORDER_LIGHT, (btn_rect.right, btn_rect.top), (btn_rect.right, btn_rect.bottom), 1)
            else:
                # Inactive button: raised look
                draw.line(surface, self.BORDER_LIGHT, (btn_rect.left, btn_rect.top), (btn_rect.right, btn_rect.top), 1)
                draw.line(surface, self.BORDER_LIGHT, (btn_rect.left, btn_rect.top), (btn_rect.left, btn_rect.bottom), 1)
                draw.line(surface, self.BORDER_DARK, (btn_rect.left, btn_rect.bottom), (btn_rect.right, btn_rect.bottom), 1)
                draw.line(surface, self.BORDER_DARK, (btn_rect.right, btn_rect.top), (btn_rect.right, btn_rect.bottom), 1)

            # Button label (small font)
            label = self._font_small.render(mode, True, text_color)
            label_x = btn_x + (btn_width - label.get_width()) // 2
            label_y = y + 2 + (btn_height - label.get_height()) // 2
            surface.blit(label, (label_x, label_y))

    def _render_timer(
        self, surface: Surface, x: int, y: int, w: int, h: int,
        time_remaining: float
    ) -> None:
        """Render battle countdown timer display.

        Args:
            surface: Target surface
            x, y: Top-left position of timer area
            w, h: Width and height of timer area
            time_remaining: Remaining time in seconds
        """
        # Timer background (slightly darker than panel)
        timer_rect = Rect(x + 2, y + 2, w - 4, h - 4)
        draw.rect(surface, (45, 50, 38), timer_rect)
        draw.rect(surface, self.BORDER_COLOR, timer_rect, 1)

        # Format time as MM:SS
        total_seconds = int(time_remaining)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        time_str = f"{minutes:02d}:{seconds:02d}"

        # Determine color based on remaining time
        if time_remaining < 30:
            timer_color = (255, 68, 68)    # Red (#FF4444) - critical
        elif time_remaining < 60:
            timer_color = (255, 255, 0)    # Yellow (#FFFF00) - warning
        else:
            timer_color = (255, 255, 255)  # White - normal

        # Render timer text (monospace bold, centered)
        try:
            timer_font = pygame.font.SysFont('consolas', 18, bold=True)
        except Exception:
            timer_font = pygame.font.Font(None, 24)

        timer_text = timer_font.render(time_str, True, timer_color)
        text_x = x + (w - timer_text.get_width()) // 2
        text_y = y + (h - timer_text.get_height()) // 2
        surface.blit(timer_text, (text_x, text_y))

    def _render_command_bar(
        self, surface: Surface, x: int, y: int, w: int, h: int,
        time_remaining: float | None = None
    ) -> None:
        """Render command buttons in vertical layout (right of unit details).

        Args:
            surface: Target surface
            x, y: Top-left position
            w, h: Width and height
            time_remaining: Optional battle timer in seconds for countdown display
        """
        # === TIMER DISPLAY (Top of command bar) ===
        timer_height = 0
        if time_remaining is not None and time_remaining > 0:
            timer_height = 28  # Space for timer display
            self._render_timer(surface, x, y, w, timer_height, time_remaining)

        # Adjust command button area to account for timer
        cmd_y = y + timer_height + (4 if timer_height > 0 else 0)
        cmd_h = h - timer_height - (4 if timer_height > 0 else 0)

        num_cmds = len(self._commands)
        btn_height = (cmd_h - (num_cmds - 1) * 4) // num_cmds if num_cmds > 0 else 0
        btn_width = w - 10

        self._button_rects = {}

        # Check if we have a selected unit for enabling/disabling commands
        has_selection = self._selected_unit_id is not None

        # Get selected unit to check smoke ammo
        selected_unit = None
        if has_selection:
            selected_unit = next((u for u in self._friendly_units if u.id == self._selected_unit_id), None)

        for i, cmd in enumerate(self._commands):
            btn_y = cmd_y + i * (btn_height + 4)
            btn_rect = Rect(x + 5, btn_y, btn_width, btn_height)

            # Determine if this command should be enabled
            cmd_enabled = True

            # Cancel and End Battle are always enabled
            if cmd["id"] in ("cancel", "end_battle"):
                cmd_enabled = True
            # Other commands require selection
            elif not has_selection:
                cmd_enabled = False
            # Smoke requires smoke ammunition
            elif cmd.get("needs_smoke_ammo") and selected_unit:
                # TODO: Check if unit has smoke grenades
                has_smoke = getattr(selected_unit, 'has_smoke_grenades', False)
                if not has_smoke:
                    cmd_enabled = False

            self._button_rects[cmd["id"]] = btn_rect

            is_hovered = cmd["id"] == self._hovered_command

            # Button background color based on state
            if not cmd_enabled:
                bg_color = (35, 38, 43)  # Disabled: dark gray
                text_color = (100, 100, 100)  # Dimmed text
            elif cmd["id"] == "end_battle":
                # End Battle: olive green color scheme (CC2 style)
                if is_hovered:
                    bg_color = (90, 100, 70)  # Hovered: lighter olive
                    text_color = (255, 255, 150)
                else:
                    bg_color = (60, 68, 50)  # Normal: olive green
                    text_color = (220, 220, 180)
            elif is_hovered:
                bg_color = (80, 90, 110)  # Hovered: lighter
                text_color = self.HIGHLIGHT_COLOR
            else:
                bg_color = (50, 58, 70)  # Normal: military blue-gray
                text_color = self.TEXT_COLOR

            draw.rect(surface, bg_color, btn_rect)

            # 3D raised border effect: top/left bright, bottom/right dark
            if cmd_enabled:
                # Top edge
                draw.line(surface, self.BORDER_LIGHT, (btn_rect.left, btn_rect.top), (btn_rect.right, btn_rect.top), 1)
                # Left edge
                draw.line(surface, self.BORDER_LIGHT, (btn_rect.left, btn_rect.top), (btn_rect.left, btn_rect.bottom), 1)
                # Bottom edge
                draw.line(surface, self.BORDER_DARK, (btn_rect.left, btn_rect.bottom), (btn_rect.right, btn_rect.bottom), 1)
                # Right edge
                draw.line(surface, self.BORDER_DARK, (btn_rect.right, btn_rect.top), (btn_rect.right, btn_rect.bottom), 1)
            else:
                draw.rect(surface, (45, 48, 53), btn_rect, 1)

            # Command icon (24x24, drawn left of text)
            icon = self._command_icons.get(cmd["id"])
            icon_x = btn_rect.left + 4
            icon_y = btn_y + (btn_height - 24) // 2
            if icon:
                if not cmd_enabled:
                    # Dim the icon for disabled state
                    dimmed = icon.copy()
                    dimmed.set_alpha(80)
                    surface.blit(dimmed, (icon_x, icon_y))
                else:
                    surface.blit(icon, (icon_x, icon_y))

            # Label with key binding (shifted right to make room for icon)
            label = f'{cmd["label"]} [{cmd["key"]}]'
            text_surf = self._font_small.render(label, True, text_color)
            text_x = icon_x + 26
            text_y = btn_y + (btn_height - text_surf.get_height()) // 2
            surface.blit(text_surf, (text_x, text_y))

    def _get_unit_type_color(self, unit: Unit) -> tuple[int, int, int]:
        """Get color for unit type icon."""
        type_name = unit.unit_type.name.lower() if hasattr(unit.unit_type, 'name') else ''
        if 'tank' in type_name or 'armor' in type_name or 'vehicle' in type_name:
            return (255, 180, 0)  # Gold for vehicles
        elif 'mg' in type_name or 'machine' in type_name:
            return (255, 100, 100)  # Red for MG
        elif 'sniper' in type_name or 'scout' in type_name:
            return (200, 100, 255)  # Purple for recon
        elif 'officer' in type_name or 'commander' in type_name:
            return (100, 200, 255)  # Blue for leaders
        elif 'engineer' in type_name or 'flame' in type_name:
            return (255, 150, 50)  # Orange for support
        else:
            return (100, 200, 100)  # Green for infantry
