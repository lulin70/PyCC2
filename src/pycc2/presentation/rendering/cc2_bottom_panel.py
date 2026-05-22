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
    3. Urgency Indicator - color-coded threat level
    4. Minimap - with +/- zoom buttons
    5. Command Bar - Move/Attack/Hold/DigIn/Cancel
    """

    # Dimensions (scaled to screen)
    PANEL_HEIGHT: int = 140  # Total height of bottom panel
    ROSTER_WIDTH: int = 200  # Left unit list width
    DETAIL_WIDTH: int = 280  # Center detail panel width
    URGENCY_WIDTH: int = 80  # Urgency indicator width
    MINIMAP_SIZE: int = 130  # Minimap square size
    COMMAND_BAR_HEIGHT: int = 35  # Bottom command bar

    # Colors (CC2 military style)
    BG_COLOR = (25, 28, 33)  # Dark background
    BORDER_COLOR = (60, 64, 72)
    TEXT_COLOR = (220, 220, 220)
    HIGHLIGHT_COLOR = (255, 255, 100)
    SELECTED_BG = (40, 45, 55)

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

        # State
        self._visible: bool = True
        self._selected_unit_id: str | None = None
        self._friendly_units: list[Unit] = []
        self._roster_scroll_offset: int = 0
        self._roster_item_height: int = 24
        self._visible_roster_items: int = 5

        # Zoom levels for minimap
        self._zoom_levels: list[float] = [0.5, 0.75, 1.0, 1.5, 2.0]
        self._current_zoom_index: int = 2  # Default 1.0x

        # Callbacks
        self._on_unit_select: callable | None = None
        self._on_command: callable | None = None
        self._on_zoom_change: callable | None = None

        # Command buttons
        self._commands: list[dict] = [
            {"id": "move", "label": "Move", "key": "M"},
            {"id": "attack", "label": "Attack", "key": "A"},
            {"id": "hold", "label": "Hold", "key": "H"},
            {"id": "dig_in", "label": "Dig In", "key": "D"},
            {"id": "cancel", "label": "Cancel", "key": "ESC"},
        ]
        self._hovered_command: str | None = None
        self._command_callbacks: dict[str, callable] = {}

        # Button rects for click detection
        self._button_rects: dict[str, Rect] = {}
        self._roster_item_rects: list[tuple[Rect, str]] = []  # (rect, unit_id)
        self._zoom_in_rect: Rect | None = None
        self._zoom_out_rect: Rect | None = None

    def initialize(self) -> None:
        """Initialize fonts."""
        if not font.get_init():
            font.init()
        self._font_small = pygame.font.Font(None, 16)
        self._font_normal = pygame.font.Font(None, 20)
        self._font_title = pygame.font.Font(None, 22)

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
                callback = self._command_callbacks.get(cmd_id)
                if callback:
                    callback()
                return f"command:{cmd_id}"

        # Check zoom buttons
        if self._zoom_in_rect and self._zoom_in_rect.collidepoint(x, y):
            return f"zoom:{self.zoom_in()}"
        if self._zoom_out_rect and self._zoom_out_rect.collidepoint(x, y):
            return f"zoom:{self.zoom_out()}"

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
    ) -> None:
        """Render the complete CC2-style bottom panel."""
        if not self._visible or not self._font_small:
            return

        sw, sh = surface.get_size()
        panel_y = sh - self.PANEL_HEIGHT

        # Draw main background
        panel_rect = Rect(0, panel_y, sw, self.PANEL_HEIGHT)
        draw.rect(surface, self.BG_COLOR, panel_rect)
        draw.line(surface, self.BORDER_COLOR, (0, panel_y), (sw, panel_y), 2)

        # Calculate section positions
        section_y = panel_y + 5
        content_height = self.PANEL_HEIGHT - self.COMMAND_BAR_HEIGHT - 10

        # === SECTION 1: Unit Roster (Left) ===
        self._render_roster(surface, 5, section_y, self.ROSTER_WIDTH, content_height)

        # === SECTION 2: Unit Details (Center-Left) ===
        detail_x = self.ROSTER_WIDTH + 10
        self._render_unit_details(surface, detail_x, section_y, self.DETAIL_WIDTH, content_height)

        # === SECTION 3: Urgency Indicator (Center) ===
        urgency_x = detail_x + self.DETAIL_WIDTH + 5
        self._render_urgency_indicator(surface, urgency_x, section_y, self.URGENCY_WIDTH, content_height)

        # === SECTION 4: Minimap (Right) ===
        minimap_x = urgency_x + self.URGENCY_WIDTH + 5
        self._render_minimap_section(surface, minimap_x, section_y, self.MINIMAP_SIZE, minimap, camera, game_map)

        # === SECTION 5: Command Bar (Bottom) ===
        cmd_y = panel_y + self.PANEL_HEIGHT - self.COMMAND_BAR_HEIGHT - 5
        self._render_command_bar(surface, 5, cmd_y, sw - 10)

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

            # Selection highlight
            if is_selected:
                draw.rect(surface, self.HIGHLIGHT_COLOR, item_rect, 1)

            # Unit type icon (colored square based on type)
            icon_color = self._get_unit_type_color(unit)
            draw.rect(surface, icon_color, Rect(x + 5, item_y + 4, 16, 16))

            # Unit name (truncated)
            name = unit.display_name[:14]
            text_color = self.HIGHLIGHT_COLOR if is_selected else self.TEXT_COLOR
            name_surf = self._font_small.render(name, True, text_color)
            surface.blit(name_surf, (x + 26, item_y + 5))

            # Health bar
            hp_ratio = unit.health.current / max(unit.health.max, 1)
            bar_width = 50
            bar_x = x + w - bar_width - 30
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

        # Title
        title = self._font_title.render(unit.display_name, True, self.HIGHLIGHT_COLOR)
        surface.blit(title, (x + 8, line_y))
        line_y += line_height + 5

        # Type and faction
        type_str = f"Type: {unit.unit_type.name[:15]}"
        faction_str = f"Faction: {unit.faction.name}"
        surface.blit(self._font_small.render(type_str, True, self.TEXT_COLOR), (x + 8, line_y))
        line_y += line_height
        surface.blit(self._font_small.render(faction_str, True, self.TEXT_COLOR), (x + 8, line_y))
        line_y += line_height + 5

        # Health
        hp_text = f"HP: {unit.health.current}/{unit.health.max}"
        hp_color = (255, 80, 80) if unit.health.current < unit.health.max * 0.3 else self.TEXT_COLOR
        surface.blit(self._font_normal.render(hp_text, True, hp_color), (x + 8, line_y))
        # Health bar
        bar_w = w - 120
        draw.rect(surface, (60, 60, 60), Rect(x + 110, line_y + 2, bar_w, 12))
        hp_ratio = unit.health.current / max(unit.health.max, 1)
        draw.rect(surface, (50, 180, 50), Rect(x + 110, line_y + 2, int(bar_w * hp_ratio), 12))
        line_y += line_height + 3

        # Morale
        morale_val = getattr(unit.morale, 'current', 75) if hasattr(unit, 'morale') else 75
        morale_text = f"Morale: {morale_val}%"
        morale_color = (
            (255, 80, 80) if morale_val < 30 else
            (255, 200, 0) if morale_val < 60 else
            (80, 200, 80)
        )
        surface.blit(self._font_normal.render(morale_text, True, morale_color), (x + 8, line_y))
        # Morale bar
        draw.rect(surface, (60, 60, 60), Rect(x + 110, line_y + 2, bar_w, 12))
        draw.rect(surface, morale_color, Rect(x + 110, line_y + 2, int(bar_w * morale_val / 100), 12))
        line_y += line_height + 3

        # Ammo
        ammo_current = getattr(unit.weapon, 'ammo', 30) if hasattr(unit, 'weapon') else 30
        ammo_max = getattr(unit.weapon, 'max_ammo', 30) if hasattr(unit, 'weapon') else 30
        ammo_text = f"Ammo: {ammo_current}/{ammo_max}"
        surface.blit(self._font_normal.render(ammo_text, True, self.TEXT_COLOR), (x + 8, line_y))
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
        state_name = unit.state_machine.current_state.name if hasattr(unit, 'state_machine') else "IDLE"
        status_text = f"Status: {state_name}"
        surface.blit(self._font_small.render(status_text, True, (180, 180, 180)), (x + 8, line_y))

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
                hp_ratio = unit.health.current / max(unit.health.max, 1)
                morale = getattr(unit.morale, 'current', 75) if hasattr(unit, 'morale') else 75

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
        """Render minimap with zoom controls."""
        # Background
        draw.rect(surface, (30, 33, 38), Rect(x, y, size, size))
        draw.rect(surface, self.BORDER_COLOR, Rect(x, y, size, size), 1)

        # Render minimap if available
        if minimap:
            minimap.render(surface, x + 2, y + 2)

        # Zoom controls (+/- buttons)
        btn_size = 20
        btn_y = y + size - btn_size - 2

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

    def _render_command_bar(
        self, surface: Surface, x: int, y: int, w: int
    ) -> None:
        """Render command buttons at bottom of panel."""
        num_cmds = len(self._commands)
        btn_width = (w - (num_cmds - 1) * 8) // num_cmds
        btn_height = self.COMMAND_BAR_HEIGHT - 5

        self._button_rects = {}

        for i, cmd in enumerate(self._commands):
            btn_x = x + i * (btn_width + 8)
            btn_rect = Rect(btn_x, y, btn_width, btn_height)
            self._button_rects[cmd["id"]] = btn_rect

            is_hovered = cmd["id"] == self._hovered_command

            # Button background
            bg_color = (70, 75, 85) if is_hovered else (50, 55, 65)
            draw.rect(surface, bg_color, btn_rect)
            draw.rect(surface, self.BORDER_COLOR, btn_rect, 1)

            # Label
            label = f'{cmd["label"]} [{cmd["key"]}]'
            text_surf = self._font_small.render(label, True, self.TEXT_COLOR if not is_hovered else self.HIGHLIGHT_COLOR)
            text_x = btn_x + (btn_width - text_surf.get_width()) // 2
            text_y = y + (btn_height - text_surf.get_height()) // 2
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
