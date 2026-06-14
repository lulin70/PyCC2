"""
CC2-Style Bottom Panel

Complete bottom UI bar mimicking original Close Combat 2 layout:
- Left: Unit roster (all friendly units)
- Center: Selected unit details (morale, ammo, smoke, casualties)
- Right: Minimap with zoom controls

Reference: Original CC2 screenshot provided by user.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

import pygame
from pygame import Rect, Surface, draw, font
from pygame.font import Font

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.minimap import Minimap
from pycc2.presentation.rendering.fade_transition import FadeTransition
from pycc2.presentation.ui.theme import ThemeManager


# ------------------------------------------------------------------
# Tooltip Manager — lightweight tooltip display for UI buttons
# ------------------------------------------------------------------

class TooltipManager:
    """Simple tooltip display manager for UI elements.

    Provides timed hover-tooltips with a short delay to avoid flickering.
    Designed for CC2 dark-toned UI (deep gray background, off-white text).
    """

    def __init__(self, font_size: int = 11, delay: float = 0.4) -> None:
        self._text: str = ""
        self._pos: tuple[int, int] = (0, 0)
        self._visible: bool = False
        self._delay: float = delay
        self._hover_start: float = 0.0
        self._font_size: int = font_size

    def begin_hover(self, text: str, pos: tuple[int, int]) -> None:
        """Called when mouse enters a tooltippable area."""
        if text != self._text:
            self._text = text
            self._pos = pos
            self._hover_start = time.monotonic()
            self._visible = False

    def end_hover(self) -> None:
        """Called when mouse leaves the area."""
        self._text = ""
        self._visible = False

    def update(self, dt: float) -> None:
        """Advance tooltip timer; show after delay elapsed."""
        if self._text and not self._visible:
            elapsed = time.monotonic() - self._hover_start
            if elapsed >= self._delay:
                self._visible = True

    def render(self, surface: Surface) -> None:
        """Render the tooltip above the stored position if visible."""
        if not self._visible or not self._text:
            return
        try:
            font_obj = font.SysFont('arial', self._font_size)
            text_surf = font_obj.render(self._text, True, (240, 235, 220))
            padding = 4
            bg_rect = text_surf.get_rect.inflate(padding * 2, padding * 2)
            bg_rect.topleft = (self._pos[0], self._pos[1] - bg_rect.height - 8)
            # Keep on screen
            bg_rect.clamp_ip(surface.get_rect())
            bg_surf = Surface(bg_rect.size, pygame.SRCALPHA)
            bg_surf.fill((30, 28, 25, 230))  # dark semi-transparent
            surface.blit(bg_surf, bg_rect.topleft)
            surface.blit(text_surf, (bg_rect.x + padding, bg_rect.y + padding))
        except Exception:
            pass  # Silently skip if font/render fails


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
    _BG_COLOR_DEFAULT = (58, 64, 48)       # Deep olive green (#3A4030) - CC2 original
    _BORDER_COLOR_DEFAULT = (90, 96, 80)   # Olive border (#5A6050) - CC2 original
    _TEXT_COLOR_DEFAULT = (220, 220, 220)
    _HIGHLIGHT_COLOR_DEFAULT = (255, 255, 100)
    _SELECTED_BG_DEFAULT = (40, 45, 55)

    @property
    def BG_COLOR(self) -> tuple[int, int, int]:
        """Panel background color from current theme."""
        return getattr(ThemeManager.get_current().colors, 'surface', self._BG_COLOR_DEFAULT)

    @property
    def BORDER_COLOR(self) -> tuple[int, int, int]:
        """Panel border color from current theme."""
        return getattr(ThemeManager.get_current().colors, 'border', self._BORDER_COLOR_DEFAULT)

    @property
    def TEXT_COLOR(self) -> tuple[int, int, int]:
        """Primary text color from current theme."""
        return getattr(ThemeManager.get_current().colors, 'text_primary', self._TEXT_COLOR_DEFAULT)

    @property
    def HIGHLIGHT_COLOR(self) -> tuple[int, int, int]:
        """Highlight/accent color from current theme."""
        return getattr(ThemeManager.get_current().colors, 'warning', self._HIGHLIGHT_COLOR_DEFAULT)

    @property
    def SELECTED_BG(self) -> tuple[int, int, int]:
        """Selected item background color from current theme."""
        return getattr(ThemeManager.get_current().colors, 'surface', self._SELECTED_BG_DEFAULT)

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

        # Command buttons - CC2 complete 7-command system + Hide + End Battle
        self._commands: list[dict] = [
            {"id": "move", "label": "Move", "key": "Z", "enabled_when_selected": True},
            {"id": "fast", "label": "Fast", "key": "X", "enabled_when_selected": True},
            {"id": "sneak", "label": "Sneak", "key": "S", "enabled_when_selected": True},
            {"id": "attack", "label": "Attack", "key": "C", "enabled_when_selected": True},
            {"id": "smoke", "label": "Smoke", "key": "V", "enabled_when_selected": True, "needs_smoke_ammo": True},
            {"id": "defend", "label": "Defend", "key": "D", "enabled_when_selected": True},
            {"id": "hide", "label": "Hide", "key": "H", "enabled_when_selected": True},
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

    def initialize(self) -> None:
        """Initialize fonts and icons."""
        if not font.get_init():
            font.init()
        try:
            self._font_small = pygame.font.SysFont('consolas', 13)
            self._font_normal = pygame.font.SysFont('consolas', 15)
            self._font_title = pygame.font.SysFont('consolas', 17)
            self._font_large = pygame.font.SysFont('consolas', 22, bold=True)
        except Exception as e:
            logging.debug(f"SysFont fallback to default fonts: {e}")
            self._font_small = pygame.font.Font(None, 16)
            self._font_normal = pygame.font.Font(None, 20)
            self._font_title = pygame.font.Font(None, 22)
            self._font_large = pygame.font.Font(None, 28)

        self._command_icons = self._create_command_icons()
        self._roster_icons = self._create_roster_icons()
        self._commander_portrait = self._create_commander_portrait()

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

    def set_event_bus(self, event_bus: object) -> None:
        """Set the EventBus reference for publishing events."""
        self._event_bus = event_bus

    # ------------------------------------------------------------------
    # Icon generation (procedural, no external assets)
    # ------------------------------------------------------------------

    def _create_command_icons(self) -> dict[str, Surface]:
        """Create 24x24 command button icons procedurally - enhanced recognizable versions."""
        icons: dict[str, Surface] = {}
        bg = self.BG_COLOR

        # Move (Z): Boot/footprint icon
        s = Surface((24, 24))
        s.fill(bg)
        green = (80, 220, 80)
        # Boot sole (horizontal rectangle)
        draw.rect(s, green, Rect(6, 14, 12, 5))
        # Boot upper (angled shape)
        draw.polygon(s, green, [(8, 14), (14, 14), (12, 6), (10, 6)])
        # Boot heel
        draw.rect(s, green, Rect(6, 10, 4, 4))
        # Sole tread lines
        draw.line(s, (60, 180, 60), (7, 16), (17, 16), 1)
        draw.line(s, (60, 180, 60), (7, 18), (17, 18), 1)
        icons["move"] = s

        # Fast (X): Running figure with double arrows
        s = Surface((24, 24))
        s.fill(bg)
        bright_green = (100, 255, 100)
        # Running figure - head
        draw.circle(s, bright_green, (10, 4), 3)
        # Body leaning forward
        draw.line(s, bright_green, (10, 7), (12, 14), 2)
        # Arms swinging
        draw.line(s, bright_green, (10, 9), (6, 11), 2)
        draw.line(s, bright_green, (10, 9), (15, 8), 2)
        # Legs in running pose
        draw.line(s, bright_green, (12, 14), (7, 19), 2)
        draw.line(s, bright_green, (12, 14), (17, 19), 2)
        # Speed lines
        draw.line(s, (80, 200, 80), (3, 8), (3, 12), 1)
        draw.line(s, (80, 200, 80), (5, 6), (5, 10), 1)
        # Double arrow indicating speed
        draw.polygon(s, bright_green, [(18, 10), (22, 13), (18, 16)])
        draw.polygon(s, bright_green, [(20, 10), (24, 13), (20, 16)])
        icons["fast"] = s

        # Sneak (S): Crouching figure
        s = Surface((24, 24))
        s.fill(bg)
        olive = (140, 180, 80)
        # Crouching head (lower position)
        draw.circle(s, olive, (8, 10), 3)
        # Crouched body (horizontal)
        draw.line(s, olive, (8, 12), (16, 12), 2)
        # Bent legs
        draw.line(s, olive, (8, 12), (6, 16), 2)
        draw.line(s, olive, (6, 16), (8, 19), 2)
        # Arm reaching forward
        draw.line(s, olive, (14, 12), (19, 10), 2)
        # Stealth dots (quiet movement)
        draw.circle(s, (100, 140, 60), (20, 18), 1)
        draw.circle(s, (100, 140, 60), (22, 16), 1)
        icons["sneak"] = s

        # Attack/Fire (C): Crosshair with center dot
        s = Surface((24, 24))
        s.fill(bg)
        red = (255, 60, 60)
        cx, cy = 12, 12
        # Outer circle
        draw.circle(s, red, (cx, cy), 9, 1)
        # Inner circle
        draw.circle(s, red, (cx, cy), 4, 1)
        # Center dot
        draw.circle(s, red, (cx, cy), 1)
        # Crosshair lines extending beyond circles
        draw.line(s, red, (cx, cy - 11), (cx, cy - 5), 1)
        draw.line(s, red, (cx, cy + 5), (cx, cy + 11), 1)
        draw.line(s, red, (cx - 11, cy), (cx - 5, cy), 1)
        draw.line(s, red, (cx + 5, cy), (cx + 11, cy), 1)
        icons["attack"] = s

        # Smoke (V): Cloud/smoke puff shape
        s = Surface((24, 24))
        s.fill(bg)
        gray = (180, 180, 180)
        dark_gray = (140, 140, 140)
        light_gray = (210, 210, 210)
        # Multiple overlapping circles for cloud effect
        draw.circle(s, gray, (8, 15), 5)
        draw.circle(s, light_gray, (14, 13), 6)
        draw.circle(s, dark_gray, (11, 9), 5)
        draw.circle(s, gray, (6, 11), 4)
        draw.circle(s, light_gray, (18, 11), 3)
        # Wispy top
        draw.circle(s, dark_gray, (13, 6), 3)
        # Base line (ground)
        draw.line(s, (100, 100, 100), (3, 20), (21, 20), 1)
        icons["smoke"] = s

        # Defend (D): Shield with horizontal line
        s = Surface((24, 24))
        s.fill(bg)
        shield_color = (100, 160, 255)
        shield_dark = (50, 80, 140)
        # Shield outline (wider shape)
        shield_pts = [(12, 1), (22, 6), (22, 14), (12, 22), (2, 14), (2, 6)]
        draw.polygon(s, shield_color, shield_pts)
        # Inner fill
        inner_pts = [(12, 4), (19, 8), (19, 13), (12, 19), (5, 13), (5, 8)]
        draw.polygon(s, shield_dark, inner_pts)
        # Chevron (V-shape pointing up) on shield
        draw.polygon(s, (200, 220, 255), [(7, 7), (12, 13), (17, 7)])
        draw.polygon(s, (200, 220, 255), [(7, 7), (12, 13), (17, 7)], 1)
        # Shield border
        draw.polygon(s, (140, 190, 255), shield_pts, 1)
        icons["defend"] = s

        # Cancel: Red X
        s = Surface((24, 24))
        s.fill(bg)
        x_red = (255, 50, 50)
        draw.line(s, x_red, (5, 5), (19, 19), 3)
        draw.line(s, x_red, (19, 5), (5, 19), 3)
        icons["cancel"] = s

        # End battle: Olive flag on pole
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

        # Hide (H): Eye with slash
        s = Surface((24, 24))
        s.fill(bg)
        eye_color = (180, 200, 220)
        # Eye outline (almond shape)
        eye_pts = [(2, 12), (6, 7), (12, 6), (18, 7), (22, 12), (18, 17), (12, 18), (6, 17)]
        draw.polygon(s, eye_color, eye_pts, 2)
        # Pupil
        draw.circle(s, (100, 150, 200), (12, 12), 3)
        draw.circle(s, (40, 40, 40), (12, 12), 1)
        # Slash through eye
        draw.line(s, (255, 60, 60), (4, 4), (20, 20), 2)
        icons["hide"] = s

        return icons

    def _create_roster_icons(self) -> dict[str, Surface]:
        """Create 16x16 unit type thumbnail icons procedurally - visually distinct per unit type."""
        icons: dict[str, Surface] = {}
        bg = self.BG_COLOR

        # Infantry: Soldier silhouette (16x16)
        s = Surface((16, 16))
        s.fill(bg)
        green = (80, 200, 80)
        dark_green = (50, 150, 50)
        # Helmet (semi-circle)
        draw.ellipse(s, dark_green, (5, 1, 6, 4))
        # Helmet brim
        draw.line(s, dark_green, (4, 4), (12, 4), 1)
        # Face
        draw.rect(s, (200, 170, 140), (6, 4, 4, 2))
        # Body/torso
        draw.rect(s, green, (5, 6, 6, 5))
        # Arms
        draw.line(s, green, (5, 7), (3, 9), 1)
        draw.line(s, green, (10, 7), (12, 9), 1)
        # Legs
        draw.line(s, dark_green, (6, 11), (5, 14), 2)
        draw.line(s, dark_green, (9, 11), (10, 14), 2)
        # Boots
        draw.rect(s, (45, 38, 28), (4, 13, 2, 2))
        draw.rect(s, (45, 38, 28), (9, 13, 2, 2))
        # Rifle
        draw.line(s, (60, 60, 60), (11, 6), (14, 3), 1)
        icons["infantry"] = s

        # MG: Gun shape (16x16)
        s = Surface((16, 16))
        s.fill(bg)
        mg_green = (80, 200, 80)
        mg_yellow = (200, 200, 80)
        # Gunner silhouette (small)
        draw.circle(s, mg_green, (5, 4), 2)
        draw.rect(s, mg_green, (4, 6, 3, 4))
        # MG barrel (thick horizontal line)
        draw.line(s, mg_yellow, (7, 7), (15, 5), 2)
        # MG body
        draw.rect(s, (100, 100, 60), (7, 6, 4, 3))
        # Bipod legs
        draw.line(s, (80, 80, 50), (13, 6), (14, 10), 1)
        draw.line(s, (80, 80, 50), (15, 5), (15, 10), 1)
        # Ammo belt
        draw.rect(s, (55, 50, 38), (3, 8, 3, 2))
        icons["mg"] = s

        # Sniper: Soldier with long rifle (16x16)
        s = Surface((16, 16))
        s.fill(bg)
        green = (80, 200, 80)
        dark_green = (50, 150, 50)
        # Helmet (semi-circle)
        draw.ellipse(s, dark_green, (4, 0, 6, 4))
        draw.line(s, dark_green, (3, 3), (11, 3), 1)
        # Face
        draw.rect(s, (200, 170, 140), (5, 3, 4, 2))
        # Body/torso (slightly hunched)
        draw.rect(s, green, (4, 5, 6, 4))
        # Arms - one forward holding rifle
        draw.line(s, green, (4, 6), (2, 8), 1)
        draw.line(s, green, (9, 6), (11, 5), 1)
        # Long rifle extending far forward
        draw.line(s, (60, 60, 60), (11, 5), (15, 1), 1)
        # Scope on rifle
        draw.rect(s, (100, 180, 255), (12, 3, 3, 2))
        # Legs (kneeling/prone)
        draw.line(s, dark_green, (5, 9), (4, 12), 2)
        draw.line(s, dark_green, (8, 9), (10, 12), 2)
        # Boots
        draw.rect(s, (45, 38, 28), (3, 11, 2, 2))
        draw.rect(s, (45, 38, 28), (9, 11, 2, 2))
        icons["sniper"] = s

        # Commander: Soldier with radio antenna (16x16)
        s = Surface((16, 16))
        s.fill(bg)
        green = (80, 200, 80)
        dark_green = (50, 150, 50)
        gold = (255, 230, 80)
        # Officer cap (flat top with brim)
        draw.rect(s, dark_green, (4, 0, 7, 3))
        draw.line(s, dark_green, (3, 3), (12, 3), 1)
        # Cap badge (small gold dot)
        draw.rect(s, gold, (7, 1, 2, 1))
        # Face
        draw.rect(s, (200, 170, 140), (5, 3, 4, 2))
        # Body/torso
        draw.rect(s, green, (4, 5, 6, 5))
        # Arms - one raised holding radio
        draw.line(s, green, (4, 6), (2, 8), 1)
        draw.line(s, green, (9, 6), (12, 4), 1)
        # Radio backpack
        draw.rect(s, (70, 70, 80), (10, 4, 4, 5))
        # Radio antenna (tall line from backpack)
        draw.line(s, (180, 180, 190), (12, 4), (12, 0), 1)
        # Antenna tip
        draw.circle(s, (255, 230, 80), (12, 0), 1)
        # Legs
        draw.line(s, dark_green, (5, 10), (5, 13), 2)
        draw.line(s, dark_green, (8, 10), (9, 13), 2)
        # Boots
        draw.rect(s, (45, 38, 28), (4, 12, 2, 2))
        draw.rect(s, (45, 38, 28), (8, 12, 2, 2))
        icons["commander"] = s

        # Engineer: Wrench (16x16)
        s = Surface((16, 16))
        s.fill(bg)
        wrench_silver = (180, 180, 190)
        wrench_dark = (120, 120, 130)
        # Wrench handle (diagonal)
        draw.line(s, wrench_dark, (3, 13), (10, 6), 2)
        # Wrench head (open end)
        draw.line(s, wrench_silver, (8, 4), (10, 6), 2)
        draw.line(s, wrench_silver, (10, 6), (12, 4), 2)
        draw.line(s, wrench_silver, (8, 4), (9, 3), 1)
        draw.line(s, wrench_silver, (12, 4), (13, 3), 1)
        # Small figure
        draw.circle(s, (80, 200, 80), (4, 3), 2)
        draw.line(s, (80, 200, 80), (4, 5), (4, 8), 1)
        icons["engineer"] = s

        # AT: Rocket shape (16x16)
        s = Surface((16, 16))
        s.fill(bg)
        rocket_red = (200, 80, 60)
        rocket_dark = (150, 50, 40)
        # Rocket body (horizontal)
        draw.rect(s, rocket_red, (2, 6, 10, 4))
        # Nose cone
        draw.polygon(s, rocket_dark, [(12, 6), (15, 8), (12, 10)])
        # Fins
        draw.polygon(s, rocket_dark, [(2, 6), (4, 3), (5, 6)])
        draw.polygon(s, rocket_dark, [(2, 10), (4, 13), (5, 10)])
        # Exhaust flame
        draw.line(s, (255, 200, 50), (1, 8), (0, 7), 1)
        draw.line(s, (255, 200, 50), (1, 8), (0, 9), 1)
        icons["at"] = s

        # Mortar: Tube shape (16x16)
        s = Surface((16, 16))
        s.fill(bg)
        tube_gray = (140, 140, 150)
        tube_dark = (100, 100, 110)
        # Tube (angled)
        draw.line(s, tube_gray, (4, 14), (10, 4), 3)
        # Muzzle opening
        draw.circle(s, tube_dark, (10, 4), 2)
        # Base plate
        draw.rect(s, tube_dark, (2, 13, 4, 2))
        # Bipod
        draw.line(s, tube_dark, (6, 10), (3, 12), 1)
        draw.line(s, tube_dark, (6, 10), (8, 13), 1)
        icons["mortar"] = s

        # Tank: Gray rectangle with turret (16x16)
        s = Surface((16, 16))
        s.fill(bg)
        tank_gray = (160, 160, 170)
        tank_dark = (120, 120, 130)
        # Hull
        draw.rect(s, tank_gray, (2, 8, 12, 5))
        # Turret
        draw.rect(s, tank_dark, (4, 5, 6, 4))
        # Barrel
        draw.line(s, (100, 100, 110), (10, 7), (15, 5), 2)
        # Tracks
        draw.rect(s, (80, 80, 90), (1, 12, 14, 2))
        # Track details
        for tx in range(2, 14, 3):
            draw.line(s, (60, 60, 70), (tx, 12), (tx, 14), 1)
        icons["tank"] = s

        # Medic: White cross on green (16x16)
        s = Surface((16, 16))
        s.fill(bg)
        white = (240, 240, 240)
        green_bg = (60, 120, 60)
        # Green background circle
        draw.circle(s, green_bg, (8, 8), 6)
        # White cross
        draw.rect(s, white, (6, 3, 4, 10))  # vertical bar
        draw.rect(s, white, (3, 6, 10, 4))  # horizontal bar
        icons["medic"] = s

        return icons

    def _create_commander_portrait(self) -> Surface:
        """Create 24x24 commander portrait - pixel art face with beret/cap."""
        s = Surface((24, 24))
        bg = self.BG_COLOR
        s.fill(bg)
        skin = (210, 180, 150)
        skin_dark = (185, 155, 125)
        beret = (50, 80, 50)
        beret_dark = (35, 55, 35)
        eye_color = (40, 40, 40)
        lip = (180, 130, 120)

        # Beret (flat cap tilted to one side)
        draw.ellipse(s, beret, (4, 1, 16, 6))
        # Beret band
        draw.rect(s, beret_dark, (5, 5, 14, 2))
        # Beret badge (small gold circle)
        draw.circle(s, (255, 230, 80), (8, 3), 1)

        # Face (oval)
        draw.ellipse(s, skin, (6, 5, 12, 12))
        # Face shadow on right side
        draw.ellipse(s, skin_dark, (13, 7, 4, 8))

        # Eyes (two small dots)
        draw.rect(s, eye_color, (8, 9, 2, 2))
        draw.rect(s, eye_color, (14, 9, 2, 2))
        # Eye whites (tiny highlight)
        draw.rect(s, (240, 240, 240), (8, 9, 1, 1))
        draw.rect(s, (240, 240, 240), (14, 9, 1, 1))

        # Nose (small line)
        draw.line(s, skin_dark, (11, 10), (11, 13), 1)

        # Mouth
        draw.line(s, lip, (9, 15), (13, 15), 1)

        # Collar/shoulders
        draw.rect(s, beret_dark, (4, 17, 16, 3))
        # Collar V-neck
        draw.polygon(s, skin, [(10, 17), (12, 17), (11, 20)])

        # Rank insignia on collar (small gold bars)
        draw.rect(s, (255, 230, 80), (5, 17, 3, 1))
        draw.rect(s, (255, 230, 80), (16, 17, 3, 1))

        # Border
        draw.rect(s, self.BORDER_COLOR, (0, 0, 24, 24), 1)

        return s

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
                    self._event_bus.publish_named("EndBattle", {"event_type": "end_battle"})
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

        # If click is outside any soldier member rect, dismiss popup
        if self._active_popup_member is not None:
            self._active_popup_member = None
            self._active_popup_rect = None

        return None

    def handle_right_click(self, screen_pos: tuple[int, int]) -> str | None:
        """Handle right-click on panel. Shows soldier detail popup if clicked on a squad member.

        Returns action string or None.
        """
        if not self._visible:
            return None

        x, y = screen_pos

        # Check soldier monitor member rects
        for rect, member in self._soldier_member_rects:
            if rect.collidepoint(x, y):
                self._active_popup_member = member
                self._active_popup_rect = Rect(x, y, 1, 1)  # Position for popup
                return f"soldier_detail:{getattr(member, 'member_id', '?')}"

        # Click elsewhere dismisses popup
        if self._active_popup_member is not None:
            self._active_popup_member = None
            self._active_popup_rect = None

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
                timer_color = (255, 68, 68)    # Red - critical
            elif self._battle_timer < 60:
                timer_color = (255, 255, 0)    # Yellow - warning
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
        self._render_roster(target, 5, section_y, self.ROSTER_WIDTH, content_height)

        # === SECTION 2: Unit Details (Center-Left) ===
        detail_x = self.ROSTER_WIDTH + 10
        self._render_unit_details(target, detail_x, section_y, self.DETAIL_WIDTH, content_height)

        # === SECTION 3: Command Bar (Center-Right, next to details) ===
        cmd_x = detail_x + self.DETAIL_WIDTH + 10
        self._render_command_bar(target, cmd_x, section_y, self.COMMAND_WIDTH, content_height, time_remaining)

        # === SECTION 4: Urgency Indicator (Right of commands) ===
        urgency_x = cmd_x + self.COMMAND_WIDTH + 5
        self._render_urgency_indicator(target, urgency_x, section_y, self.URGENCY_WIDTH, content_height)

        # === SECTION 5: Minimap (Far Right) ===
        minimap_x = urgency_x + self.URGENCY_WIDTH + 5
        self._render_minimap_section(target, minimap_x, section_y, self.MINIMAP_SIZE, minimap, camera, game_map)

        # Blit the faded panel surface onto the target surface with alpha
        if use_fade_surface:
            panel_surface.set_alpha(int(alpha * 255))
            surface.blit(panel_surface, (0, panel_y))

        # Render tooltip on top of everything (always on main surface)
        self._tooltip.render(surface)

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

            # Unit type thumbnail icon (16x16)
            icon_key = self._map_unit_type_to_icon_key(unit)
            roster_icon = self._roster_icons.get(icon_key)
            if roster_icon:
                surface.blit(roster_icon, (x + 5, item_y + 4))

            # Unit name (truncated) — Unit uses .name, not .display_name
            name = getattr(unit, 'display_name', None) or getattr(unit, 'name', 'Unknown')
            name = str(name)[:12]
            text_color = self.HIGHLIGHT_COLOR if is_selected else self.TEXT_COLOR
            name_surf = self._font_small.render(name, True, text_color)
            surface.blit(name_surf, (x + 23, item_y + 5))

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

        # Commander portrait (24x24) if unit is commander/officer type
        portrait_offset = 0
        icon_key = self._map_unit_type_to_icon_key(unit)
        if icon_key == 'commander' and self._commander_portrait:
            surface.blit(self._commander_portrait, (x + 8, line_y))
            portrait_offset = 28  # Shift title right to make room for portrait

        # Title — Unit uses .name, not .display_name
        display_name = getattr(unit, 'display_name', None) or getattr(unit, 'name', 'Unknown')
        title = self._font_title.render(str(display_name), True, self.HIGHLIGHT_COLOR)
        surface.blit(title, (x + 8 + portrait_offset, line_y))
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

        # AP/AT Resource Bars (Action Points / Attack Points) - CC2 style
        ap_current = getattr(unit, 'action_points', getattr(unit, 'ap', 10))
        ap_max = getattr(unit, 'max_action_points', getattr(unit, 'max_ap', 10))
        at_current = getattr(unit, 'attack_points', getattr(unit, 'at', 5))
        at_max = getattr(unit, 'max_attack_points', getattr(unit, 'max_at', 5))

        # AP Bar (Green - movement resource)
        ap_text = f"AP: {ap_current}/{ap_max}"
        surface.blit(self._font_normal.render(ap_text, True, (100, 255, 150)), (x + 8, line_y))
        draw.rect(surface, (40, 42, 48), Rect(x + 109, line_y + 1, bar_w + 2, 14))
        draw.rect(surface, (60, 60, 60), Rect(x + 110, line_y + 2, bar_w, 12))
        ap_ratio = ap_current / max(ap_max, 1)
        # AP color: Green (full) -> Yellow (mid) -> Red (low)
        if ap_ratio > 0.6:
            ap_color = (80, 220, 80)
        elif ap_ratio > 0.3:
            ap_color = (220, 200, 50)
        else:
            ap_color = (220, 80, 80)
        draw.rect(surface, ap_color, Rect(x + 110, line_y + 2, int(bar_w * ap_ratio), 12))
        line_y += line_height + 3

        # AT Bar (Orange - attack resource)
        at_text = f"AT: {at_current}/{at_max}"
        surface.blit(self._font_normal.render(at_text, True, (255, 180, 100)), (x + 8, line_y))
        draw.rect(surface, (40, 42, 48), Rect(x + 109, line_y + 1, bar_w + 2, 14))
        draw.rect(surface, (60, 60, 60), Rect(x + 110, line_y + 2, bar_w, 12))
        at_ratio = at_current / max(at_max, 1)
        # AT color: Orange (full) -> Yellow (mid) -> Red (low)
        if at_ratio > 0.6:
            at_color = (255, 180, 80)
        elif at_ratio > 0.3:
            at_color = (220, 180, 50)
        else:
            at_color = (220, 80, 80)
        draw.rect(surface, at_color, Rect(x + 110, line_y + 2, int(bar_w * at_ratio), 12))
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
        - Personal name (e.g., "Pvt. Johnson")
        - Weapon type name (e.g., "M1 Garand", "Thompson")
        - HP bar for each member
        - Ammo bar showing remaining ammo percentage
        - Morale status text (Rallied/Wavering/Pinned/Broken/Routing)
        - Experience level
        """
        # Weapon name mapping by role
        WEAPON_NAMES = {
            "rifleman": "M1 Garand",
            "grenadier": "M1 Carbine",
            "mg_gunner": "MG42",
            "mg_assistant": "MG42",
            "ammo_bearer": "M1 Garand",
            "sniper": "Springfield",
            "spotter": "M1 Garand",
            "at_gunner": "Bazooka",
            "at_assistant": "M1 Garand",
            "mortar_gunner": "60mm Mortar",
            "team_leader": "Thompson",
            "commander": "Colt .45",
            "officer": "Colt .45",
            "gunner": "Thompson",
            "loader": "M1 Garand",
            "driver": "M1 Garand",
            "assistant_driver": "M1 Garand",
            "radioman": "M1 Garand",
            "runner": "M1 Garand",
        }

        # Morale status text mapping
        MORALE_STATUS = {
            "healthy": "Rallied",
            "wounded": "Wavering",
            "pinned": "Pinned",
            "dead": "Dead",
            "surrendered": "Routing",
        }

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

        # Experience level labels
        XP_LEVELS = [
            (80, "Vet", (255, 215, 0)),
            (50, "Reg", (100, 200, 255)),
            (25, "Trn", (180, 180, 180)),
            (0, "Rct", (150, 150, 150)),
        ]

        # Track member rects for right-click interaction
        self._soldier_member_rects = []
        start_y = y

        for member in members:
            if y + member_line_h > start_y + h:
                break

            state_name = member.state.value if hasattr(member.state, 'value') else str(member.state)
            icon = state_icons.get(state_name, "?")
            icon_color = state_colors.get(state_name, (180, 180, 180))

            # Track clickable rect for this member
            member_rect = Rect(x + 2, y, w - 4, member_line_h)
            self._soldier_member_rects.append((member_rect, member))

            # Highlight if this is the popup member
            if member is self._active_popup_member:
                draw.rect(surface, (50, 55, 70), member_rect)

            # State icon
            icon_surf = self._font_small.render(icon, True, icon_color)
            surface.blit(icon_surf, (x + 5, y))

            # Personal name (e.g., "Pvt. Johnson") — fall back to role if no name
            personal_name = getattr(member, 'name', '')
            if not personal_name:
                personal_name = getattr(member, 'role', '?')
            display_name = personal_name[:12]
            name_surf = self._font_small.render(display_name, True, self.TEXT_COLOR)
            surface.blit(name_surf, (x + 18, y))

            # Weapon type name
            role = getattr(member, 'role', 'rifleman')
            weapon_name = WEAPON_NAMES.get(role, "M1 Garand")
            weapon_surf = self._font_small.render(weapon_name[:10], True, (150, 180, 210))
            surface.blit(weapon_surf, (x + 95, y))

            # HP bar
            hp = getattr(member, 'hp', 0)
            hp_bar_x = x + 155
            hp_bar_w = 30
            hp_ratio = max(0, min(1, hp / 100))
            draw.rect(surface, (40, 42, 48), Rect(hp_bar_x, y + 2, hp_bar_w, 9))
            hp_color = (80, 200, 80) if hp_ratio > 0.5 else (255, 200, 50) if hp_ratio > 0.25 else (220, 60, 60)
            draw.rect(surface, hp_color, Rect(hp_bar_x, y + 2, int(hp_bar_w * hp_ratio), 9))

            # Ammo bar (small bar showing remaining ammo percentage)
            ammo_bar_x = hp_bar_x + hp_bar_w + 3
            ammo_bar_w = 20
            # Estimate ammo based on role and state
            ammo_ratio = 1.0 if state_name == "healthy" else 0.6 if state_name == "wounded" else 0.0
            draw.rect(surface, (40, 42, 48), Rect(ammo_bar_x, y + 2, ammo_bar_w, 9))
            ammo_color = (100, 150, 255) if ammo_ratio > 0.5 else (200, 150, 50) if ammo_ratio > 0.2 else (200, 60, 60)
            draw.rect(surface, ammo_color, Rect(ammo_bar_x, y + 2, int(ammo_bar_w * ammo_ratio), 9))

            # Morale status text
            morale_text = MORALE_STATUS.get(state_name, "?")
            morale_color = state_colors.get(state_name, (180, 180, 180))
            morale_surf = self._font_small.render(morale_text[:5], True, morale_color)
            surface.blit(morale_surf, (x + w - 38, y))

            # Experience level indicator
            xp = getattr(member, 'experience', 0)
            xp_label = "Rct"
            xp_color = (150, 150, 150)
            for threshold, label, color in XP_LEVELS:
                if xp >= threshold:
                    xp_label = label
                    xp_color = color
                    break
            xp_surf = self._font_small.render(xp_label, True, xp_color)
            surface.blit(xp_surf, (x + w - 60, y))

            y += member_line_h

        # Render soldier detail popup if active
        if self._active_popup_member is not None and self._active_popup_rect is not None:
            self._render_soldier_detail_popup(surface, self._active_popup_member, self._active_popup_rect)

    def _render_soldier_detail_popup(
        self, surface: Surface, member: object, popup_pos: Rect
    ) -> None:
        """Render a detail popup for a right-clicked soldier.

        Shows:
        - Full name and rank
        - Weapon and ammo count
        - Health and morale status
        - Experience level
        """
        popup_w = 180
        popup_h = 90
        # Position popup near the click, but keep it on screen
        px = min(popup_pos.x, surface.get_width() - popup_w - 5)
        py = min(popup_pos.y, surface.get_height() - popup_h - 5)
        py = max(py, 5)

        # Popup background
        popup_rect = Rect(px, py, popup_w, popup_h)
        draw.rect(surface, (25, 28, 35), popup_rect)
        draw.rect(surface, (120, 130, 150), popup_rect, 1)
        # Inner border
        draw.rect(surface, (40, 44, 55), Rect(px + 1, py + 1, popup_w - 2, popup_h - 2), 1)

        line_y = py + 5
        line_h = 15

        # Full name and rank
        personal_name = getattr(member, 'name', '')
        if not personal_name:
            personal_name = getattr(member, 'role', 'Unknown')
        name_surf = self._font_normal.render(str(personal_name), True, self.HIGHLIGHT_COLOR)
        surface.blit(name_surf, (px + 8, line_y))
        line_y += line_h

        # Role
        role = getattr(member, 'role', 'rifleman')
        role_surf = self._font_small.render(f"Role: {role}", True, (180, 180, 180))
        surface.blit(role_surf, (px + 8, line_y))
        line_y += line_h

        # Weapon
        WEAPON_NAMES = {
            "rifleman": "M1 Garand", "grenadier": "M1 Carbine",
            "mg_gunner": "MG42", "mg_assistant": "MG42",
            "ammo_bearer": "M1 Garand", "sniper": "Springfield",
            "spotter": "M1 Garand", "at_gunner": "Bazooka",
            "at_assistant": "M1 Garand", "mortar_gunner": "60mm Mortar",
            "team_leader": "Thompson", "commander": "Colt .45",
            "officer": "Colt .45", "gunner": "Thompson",
            "loader": "M1 Garand", "driver": "M1 Garand",
            "assistant_driver": "M1 Garand", "radioman": "M1 Garand",
            "runner": "M1 Garand",
        }
        weapon_name = WEAPON_NAMES.get(role, "M1 Garand")
        weapon_surf = self._font_small.render(f"Weapon: {weapon_name}", True, (150, 180, 210))
        surface.blit(weapon_surf, (px + 8, line_y))
        line_y += line_h

        # Health
        hp = getattr(member, 'hp', 0)
        hp_color = (80, 200, 80) if hp > 50 else (255, 200, 50) if hp > 25 else (220, 60, 60)
        hp_surf = self._font_small.render(f"HP: {hp}/100", True, hp_color)
        surface.blit(hp_surf, (px + 8, line_y))
        line_y += line_h

        # State / Morale
        state_name = member.state.value if hasattr(member.state, 'value') else str(member.state)
        MORALE_STATUS = {
            "healthy": "Rallied", "wounded": "Wavering",
            "pinned": "Pinned", "dead": "Dead", "surrendered": "Routing",
        }
        morale_text = MORALE_STATUS.get(state_name, "?")
        state_colors = {
            "healthy": (80, 200, 80), "wounded": (255, 200, 50),
            "pinned": (255, 220, 50), "dead": (200, 60, 60),
            "surrendered": (150, 150, 150),
        }
        morale_color = state_colors.get(state_name, (180, 180, 180))
        morale_surf = self._font_small.render(f"Morale: {morale_text}", True, morale_color)
        surface.blit(morale_surf, (px + 8, line_y))
        line_y += line_h

        # Experience level
        xp = getattr(member, 'experience', 0)
        XP_LEVELS = [
            (80, "Veteran"), (50, "Regular"), (25, "Trained"), (0, "Recruit"),
        ]
        xp_label = "Recruit"
        for threshold, label in XP_LEVELS:
            if xp >= threshold:
                xp_label = label
                break
        xp_surf = self._font_small.render(f"XP: {xp} ({xp_label})", True, (200, 200, 200))
        surface.blit(xp_surf, (px + 8, line_y))

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

        # Minimap title label
        title = self._font_small.render("MAP", True, (150, 150, 150))
        surface.blit(title, (x + 4, minimap_y + 2))

        # Render minimap if available
        if minimap:
            minimap.render(surface, x + 2, minimap_y + 2)

        # Zoom controls (+/- buttons)
        btn_size = 20
        btn_y = minimap_y + minimap_size - btn_size - 2

        # Helper to check if a rect is hovered/pressed
        mp = self._mouse_pos

        # Zoom out (-)
        self._zoom_out_rect = Rect(x + 2, btn_y, btn_size, btn_size)
        zo_hovered = mp is not None and self._zoom_out_rect.collidepoint(mp)
        zo_pressed = zo_hovered and self._mouse_pressed
        zo_bg = (45, 45, 55) if zo_pressed else ((80, 85, 100) if zo_hovered else (60, 60, 70))
        draw.rect(surface, zo_bg, self._zoom_out_rect)
        draw.rect(surface, (140, 150, 170) if zo_hovered else self.BORDER_COLOR, self._zoom_out_rect, 1)
        minus = self._font_normal.render("-", True, self.TEXT_COLOR)
        surface.blit(minus, (x + 7, btn_y + 2))
        if zo_hovered:
            self._tooltip.begin_hover("Zoom out [-]", (self._zoom_out_rect.centerx, self._zoom_out_rect.top))

        # Zoom in (+)
        self._zoom_in_rect = Rect(x + size - btn_size - 2, btn_y, btn_size, btn_size)
        zi_hovered = mp is not None and self._zoom_in_rect.collidepoint(mp)
        zi_pressed = zi_hovered and self._mouse_pressed
        zi_bg = (45, 45, 55) if zi_pressed else ((80, 85, 100) if zi_hovered else (60, 60, 70))
        draw.rect(surface, zi_bg, self._zoom_in_rect)
        draw.rect(surface, (140, 150, 170) if zi_hovered else self.BORDER_COLOR, self._zoom_in_rect, 1)
        plus = self._font_normal.render("+", True, self.TEXT_COLOR)
        surface.blit(plus, (x + size - btn_size + 5, btn_y + 2))
        if zi_hovered:
            self._tooltip.begin_hover("Zoom in [+]", (self._zoom_in_rect.centerx, self._zoom_in_rect.top))

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

            # Check hover/press state
            mp = self._mouse_pos
            btn_hovered = mp is not None and btn_rect.collidepoint(mp)
            btn_pressed = btn_hovered and self._mouse_pressed

            # Button background color based on state
            if is_active:
                bg_color = (55, 65, 48) if btn_pressed else (70, 80, 60)  # Active
                text_color = self.HIGHLIGHT_COLOR
            elif btn_pressed:
                bg_color = (35, 40, 32)   # Inactive + pressed
                text_color = (140, 140, 130)
            elif btn_hovered:
                bg_color = (58, 65, 50)   # Inactive + hovered
                text_color = (190, 190, 170)
            else:
                bg_color = (45, 50, 40)    # Inactive normal
                text_color = (160, 160, 150)   # Dimmed text

            draw.rect(surface, bg_color, btn_rect)

            # 3D border effect based on state
            if is_active or btn_pressed:
                # Active/pressed button: sunken look (inverted borders)
                draw.line(surface, self.BORDER_DARK, (btn_rect.left, btn_rect.top), (btn_rect.right, btn_rect.top), 1)
                draw.line(surface, self.BORDER_DARK, (btn_rect.left, btn_rect.top), (btn_rect.left, btn_rect.bottom), 1)
                draw.line(surface, self.BORDER_LIGHT, (btn_rect.left, btn_rect.bottom), (btn_rect.right, btn_rect.bottom), 1)
                draw.line(surface, self.BORDER_LIGHT, (btn_rect.right, btn_rect.top), (btn_rect.right, btn_rect.bottom), 1)
            else:
                # Inactive button: raised look
                border_c = (130, 140, 120) if btn_hovered else self.BORDER_LIGHT
                draw.line(surface, border_c, (btn_rect.left, btn_rect.top), (btn_rect.right, btn_rect.top), 1)
                draw.line(surface, border_c, (btn_rect.left, btn_rect.top), (btn_rect.left, btn_rect.bottom), 1)
                draw.line(surface, self.BORDER_DARK, (btn_rect.left, btn_rect.bottom), (btn_rect.right, btn_rect.bottom), 1)
                draw.line(surface, self.BORDER_DARK, (btn_rect.right, btn_rect.top), (btn_rect.right, btn_rect.bottom), 1)

            # Hover highlight border for inactive hovered buttons
            if btn_hovered and not is_active and not btn_pressed:
                hl_rect = Rect(btn_rect.x + 1, btn_rect.y + 1, btn_rect.width - 2, btn_rect.height - 2)
                hl_surf = Surface((hl_rect.width, hl_rect.height), pygame.SRCALPHA)
                draw.rect(hl_surf, (120, 150, 100, 150), hl_surf.get_rect(), 1)
                surface.blit(hl_surf, hl_rect.topleft)

            # Button label (small font)
            label = self._font_small.render(mode, True, text_color)
            label_x = btn_x + (btn_width - label.get_width()) // 2
            label_y = y + 2 + (btn_height - label.get_height()) // 2
            surface.blit(label, (label_x, label_y))

            # Tooltip for info toggle buttons
            if btn_hovered:
                tip_map = {"ALL": "Show all unit information",
                           "STYLE": "Show visual style info only",
                           "OUTLINE": "Show outline info only"}
                self._tooltip.begin_hover(tip_map.get(mode, f"Switch to {mode} mode"),
                                          (btn_rect.centerx, btn_rect.top))

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
        except Exception as e:
            logging.debug(f"Timer font fallback: {e}")
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

        # Reset tooltip at start of each frame; buttons will re-trigger if hovered
        self._tooltip.end_hover()

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
                has_smoke = getattr(selected_unit, 'has_smoke_grenades', False)
                if not has_smoke:
                    cmd_enabled = False

            self._button_rects[cmd["id"]] = btn_rect

            is_hovered = cmd["id"] == self._hovered_command
            is_pressed = is_hovered and self._mouse_pressed

            # Button background color based on state
            if not cmd_enabled:
                bg_color = (35, 38, 43)  # Disabled: dark gray
                text_color = (100, 100, 100)  # Dimmed text
            elif cmd["id"] == "end_battle":
                # End Battle: olive green color scheme (CC2 style)
                if is_pressed:
                    bg_color = (50, 58, 38)   # Pressed: darker olive
                    text_color = (200, 200, 130)
                elif is_hovered:
                    bg_color = (90, 100, 70)  # Hovered: lighter olive
                    text_color = (255, 255, 150)
                else:
                    bg_color = (60, 68, 50)  # Normal: olive green
                    text_color = (220, 220, 180)
            elif is_pressed:
                bg_color = (40, 48, 62)    # Pressed: darkened ~20%
                text_color = (200, 210, 230)
            elif is_hovered:
                bg_color = (80, 90, 110)  # Hovered: lighter
                text_color = self.HIGHLIGHT_COLOR
            else:
                bg_color = (50, 58, 70)  # Normal: military blue-gray
                text_color = self.TEXT_COLOR

            draw.rect(surface, bg_color, btn_rect)

            # 3D raised border effect: top/left bright, bottom/right dark
            if cmd_enabled:
                if is_pressed:
                    # Pressed: inverted borders (sunken look)
                    draw.line(surface, self.BORDER_DARK, (btn_rect.left, btn_rect.top), (btn_rect.right, btn_rect.top), 1)
                    draw.line(surface, self.BORDER_DARK, (btn_rect.left, btn_rect.top), (btn_rect.left, btn_rect.bottom), 1)
                    draw.line(surface, self.BORDER_LIGHT, (btn_rect.left, btn_rect.bottom), (btn_rect.right, btn_rect.bottom), 1)
                    draw.line(surface, self.BORDER_LIGHT, (btn_rect.right, btn_rect.top), (btn_rect.right, btn_rect.bottom), 1)
                else:
                    # Top edge
                    draw.line(surface, self.BORDER_LIGHT, (btn_rect.left, btn_rect.top), (btn_rect.right, btn_rect.top), 1)
                    # Left edge
                    draw.line(surface, self.BORDER_LIGHT, (btn_rect.left, btn_rect.top), (btn_rect.left, btn_rect.bottom), 1)
                    # Bottom edge
                    draw.line(surface, self.BORDER_DARK, (btn_rect.left, btn_rect.bottom), (btn_rect.right, btn_rect.bottom), 1)
                    # Right edge
                    draw.line(surface, self.BORDER_DARK, (btn_rect.right, btn_rect.top), (btn_rect.right, btn_rect.bottom), 1)

                # Hover highlight: bright inner border glow when hovered (not pressed)
                if is_hovered and not is_pressed:
                    highlight_color = (140, 160, 200, 180)
                    highlight_rect = Rect(btn_rect.x + 1, btn_rect.y + 1, btn_rect.width - 2, btn_rect.height - 2)
                    hl_surf = Surface((highlight_rect.width, highlight_rect.height), pygame.SRCALPHA)
                    draw.rect(hl_surf, highlight_color, hl_surf.get_rect(), 1)
                    surface.blit(hl_surf, highlight_rect.topleft)
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

            # Trigger tooltip on hovered enabled button
            if is_hovered and cmd_enabled and self._mouse_pos is not None:
                tip_text = self._command_tooltips.get(cmd["id"], "")
                if tip_text:
                    self._tooltip.begin_hover(tip_text, (btn_rect.centerx, btn_rect.top))

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
