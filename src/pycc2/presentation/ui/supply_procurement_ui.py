"""Supply Procurement UI — CC2 Daily Supply Allocation Phase (P4-4).

Implements the pre-battle-day supply procurement screen where the player
allocates the day's supply points across the three Market Garden sectors
(Arnhem, Nijmegen, Eindhoven).  Each procured point boosts the sector's
ammunition, reinforcement, and morale recovery rates for the coming day.

Design (SRP, modelled on ``deployment_ui.py``):
  - :class:`SupplyProcurementState` — pure state dataclass (no behaviour)
  - :class:`SupplyProcurementUI`    — interaction + rendering, delegating
    all supply math to the real :class:`SupplyLineManager`.

Interaction model:
  - Click ``[+]`` on a sector row to allocate ``ALLOCATE_STEP`` points.
  - Click ``[-]`` to revoke points (returns them to the available pool).
  - Click ``Confirm`` to finalise the allocation and advance to the day's
    battles.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from pycc2.domain.systems.supply_line import (
    SupplyLevel,
    SupplyLineManager,
    SupplyType,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pygame – imported lazily so the module can be imported in headless tests
# ---------------------------------------------------------------------------
_pygame_available: bool = False
try:
    import pygame

    _pygame_available = True
except ImportError:  # pragma: no cover - pygame is a hard runtime dep
    pygame = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Points added/removed per click of the [+] / [-] buttons.
ALLOCATE_STEP: int = 10

# Display labels for supply levels.
_SUPPLY_LEVEL_LABELS: dict[SupplyLevel, str] = {
    SupplyLevel.FULL: "FULL",
    SupplyLevel.REDUCED: "REDUCED",
    SupplyLevel.MINIMAL: "MINIMAL",
    SupplyLevel.NONE: "NONE",
}

# Display labels for supply types.
_SUPPLY_TYPE_LABELS: dict[SupplyType, str] = {
    SupplyType.LAND: "Land",
    SupplyType.AIRDROP: "Airdrop",
    SupplyType.BLOCKED: "Blocked",
}

# Layout constants (pixels).
_HEADER_HEIGHT: int = 60
_POOL_BAR_HEIGHT: int = 40
_SECTOR_ROW_HEIGHT: int = 80
_BUTTON_WIDTH: int = 44
_BUTTON_HEIGHT: int = 32
_CONFIRM_BUTTON_WIDTH: int = 160
_BACK_BUTTON_WIDTH: int = 120
_MARGIN: int = 20

# CC2 military palette (mirrors campaign_ui_types.py).
_BG_COLOR: tuple[int, int, int] = (40, 44, 52)
_PANEL_COLOR: tuple[int, int, int] = (50, 55, 45)
_BORDER_COLOR: tuple[int, int, int] = (90, 96, 80)
_TEXT_COLOR: tuple[int, int, int] = (220, 220, 220)
_TEXT_DIM: tuple[int, int, int] = (180, 180, 170)
_HIGHLIGHT_COLOR: tuple[int, int, int] = (255, 255, 100)
_BUTTON_COLOR: tuple[int, int, int] = (65, 75, 58)
_BUTTON_HOVER: tuple[int, int, int] = (85, 95, 72)
_BUTTON_BORDER: tuple[int, int, int] = (110, 120, 95)
_BUTTON_DISABLED: tuple[int, int, int] = (45, 48, 55)
_GOOD_COLOR: tuple[int, int, int] = (80, 200, 80)
_BAD_COLOR: tuple[int, int, int] = (200, 80, 80)
_WARN_COLOR: tuple[int, int, int] = (220, 180, 80)
_POOL_COLOR: tuple[int, int, int] = (200, 180, 100)


# ---------------------------------------------------------------------------
# State (SRP: pure data, no behaviour)
# ---------------------------------------------------------------------------


@dataclass
class SupplyProcurementState:
    """Mutable state of the supply procurement phase.

    Attributes
    ----------
    day:
        Campaign day this procurement phase is for (1-9).
    confirmed:
        True once the player has clicked Confirm and the allocation is
        frozen for the day.
    allocations:
        Snapshot of points allocated per sector — kept in sync with the
        :class:`SupplyLineManager`'s ``procured_points`` for display.

    """

    day: int = 1
    confirmed: bool = False
    allocations: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# SupplyProcurementUI
# ---------------------------------------------------------------------------


class SupplyProcurementUI:
    """Daily supply procurement screen.

    Holds a back-reference to the real :class:`SupplyLineManager` and
    mutates it directly via :meth:`SupplyLineManager.procure_supply` so
    that the domain state is the single source of truth.  The UI's own
    :class:`SupplyProcurementState` only tracks display concerns
    (current day, confirmation flag, cached allocation snapshot).

    """

    def __init__(self, width: int = 800, height: int = 600) -> None:
        """Initialize the SupplyProcurementUI."""
        self.width = width
        self.height = height

        self._state = SupplyProcurementState()
        self._manager: SupplyLineManager | None = None

        # Cached sector ordering (deterministic display order).
        self._sectors: list[str] = []

        # Clickable regions populated during render.
        self._inc_button_rects: dict[str, pygame.Rect] = {}
        self._dec_button_rects: dict[str, pygame.Rect] = {}
        self._sector_row_rects: dict[str, pygame.Rect] = {}
        self._confirm_button_rect: pygame.Rect | None = None
        self._back_button_rect: pygame.Rect | None = None

        # Hover state for visual feedback.
        self._hovered_sector: str | None = None
        self._hovered_button: str | None = None

        # Fonts (initialised lazily on first render).
        self._font_title: pygame.font.Font | None = None
        self._font_normal: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> SupplyProcurementState:
        """Return the current procurement state (read-only reference)."""
        return self._state

    @property
    def manager(self) -> SupplyLineManager | None:
        """Return the bound SupplyLineManager, or None if not started."""
        return self._manager

    @property
    def is_confirmed(self) -> bool:
        """True if the player has confirmed the day's allocation."""
        return self._state.confirmed

    def start_procurement(self, manager: SupplyLineManager, day: int) -> None:
        """Begin a procurement phase for the given day.

        Binds the real :class:`SupplyLineManager` and snapshots the
        current per-sector allocation (which may be non-zero if a phase
        was resumed mid-day).

        """
        self._manager = manager
        self._state.day = day
        self._state.confirmed = False
        # Deterministic display order: arnhem, nijmegen, eindhoven
        # (matches SupplyLineManager.create_default insertion order).
        self._sectors = list(manager.sector_supply.keys())
        self._refresh_allocations()
        # Reset hover state for a fresh phase.
        self._hovered_sector = None
        self._hovered_button = None

    def allocate(self, sector_id: str, delta: int) -> bool:
        """Apply an allocation delta to a sector.

        Delegates to :meth:`SupplyLineManager.procure_supply` so the
        domain state stays authoritative.  Returns True if the change
        was applied.

        """
        if self._manager is None or self._state.confirmed:
            return False
        applied = self._manager.procure_supply(sector_id, delta)
        if applied:
            self._refresh_allocations()
        return applied

    def confirm(self) -> dict[str, int]:
        """Finalise the allocation and return the per-sector point map.

        After confirmation the UI refuses further allocation clicks.

        """
        if self._manager is None:
            return {}
        self._state.confirmed = True
        return dict(self._state.allocations)

    def get_allocation(self, sector_id: str) -> int:
        """Return the points currently allocated to a sector."""
        return self._state.allocations.get(sector_id, 0)

    def get_available_points(self) -> int:
        """Return supply points still available for allocation today."""
        if self._manager is None:
            return 0
        return self._manager.available_supply_points

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def handle_click(self, x: int, y: int) -> str | None:
        """Handle a mouse click at screen coordinates (x, y).

        Returns an action string or None:
          - ``"allocate:<sector_id>,<delta>"`` — allocation changed
          - ``"confirm"`` — confirm button clicked
          - ``"back"`` — back button clicked
          - ``None`` — click did nothing

        """
        if self._manager is None:
            return None

        # [+] buttons
        for sector_id, rect in self._inc_button_rects.items():
            if rect.collidepoint(x, y):
                if self.allocate(sector_id, ALLOCATE_STEP):
                    return f"allocate:{sector_id},{ALLOCATE_STEP}"
                return None

        # [-] buttons
        for sector_id, rect in self._dec_button_rects.items():
            if rect.collidepoint(x, y):
                if self.allocate(sector_id, -ALLOCATE_STEP):
                    return f"allocate:{sector_id},{-ALLOCATE_STEP}"
                return None

        # Clicking a sector row selects it (visual feedback only).
        for sector_id, rect in self._sector_row_rects.items():
            if rect.collidepoint(x, y):
                return f"select:{sector_id}"

        # Confirm button
        if self._confirm_button_rect and self._confirm_button_rect.collidepoint(x, y):
            if not self._state.confirmed:
                self.confirm()
                return "confirm"
            return None

        # Back button
        if self._back_button_rect and self._back_button_rect.collidepoint(x, y):
            return "back"

        return None

    def handle_mouse_move(self, x: int, y: int) -> None:
        """Track hover state for visual feedback."""
        self._hovered_sector = None
        self._hovered_button = None

        for sector_id, rect in self._sector_row_rects.items():
            if rect.collidepoint(x, y):
                self._hovered_sector = sector_id
                break

        if self._confirm_button_rect and self._confirm_button_rect.collidepoint(x, y):
            self._hovered_button = "confirm"
        elif self._back_button_rect and self._back_button_rect.collidepoint(x, y):
            self._hovered_button = "back"

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, screen: pygame.Surface, font: pygame.font.Font | None = None) -> None:
        """Render the supply procurement screen.

        No-op when pygame is unavailable or no manager is bound, so the
        method is safe to call from headless tests.

        """
        if not _pygame_available or screen is None or self._manager is None:
            return

        self._ensure_fonts(font)

        sw, sh = screen.get_size()
        self.width, self.height = sw, sh

        screen.fill(_BG_COLOR)

        self._render_header(screen, sw)
        self._render_pool_bar(screen, sw)
        self._render_sector_rows(screen, sw)
        self._render_buttons(screen, sw, sh)

    # -- render helpers -------------------------------------------------

    def _render_header(self, screen: pygame.Surface, sw: int) -> None:
        assert self._font_title is not None and self._font_normal is not None
        title = self._font_title.render("SUPPLY PROCUREMENT", True, _HIGHLIGHT_COLOR)
        screen.blit(title, (sw // 2 - title.get_width() // 2, _MARGIN))

        day_text = f"Day {self._state.day} of 9"
        day_surf = self._font_normal.render(day_text, True, _HIGHLIGHT_COLOR)
        screen.blit(day_surf, (sw - _MARGIN - day_surf.get_width(), _MARGIN + 8))

        sep_y = _MARGIN + title.get_height() + 8
        pygame.draw.line(screen, _BORDER_COLOR, (_MARGIN, sep_y), (sw - _MARGIN, sep_y), 1)

    def _render_pool_bar(self, screen: pygame.Surface, sw: int) -> None:
        assert self._font_normal is not None and self._font_small is not None
        manager = self._manager
        assert manager is not None

        bar_y = _HEADER_HEIGHT
        bar_h = _POOL_BAR_HEIGHT
        bar_rect = pygame.Rect(_MARGIN, bar_y, sw - _MARGIN * 2, bar_h)
        pygame.draw.rect(screen, _PANEL_COLOR, bar_rect)
        pygame.draw.rect(screen, _BORDER_COLOR, bar_rect, 1)

        available = manager.available_supply_points
        total = manager.daily_supply_points
        label = self._font_normal.render(
            f"AVAILABLE SUPPLY POINTS: {available} / {total}",
            True,
            _POOL_COLOR,
        )
        screen.blit(label, (bar_rect.left + 10, bar_rect.top + 8))

        # Allocation summary on the right.
        spent = total - available
        spent_label = self._font_small.render(f"Allocated: {spent}", True, _TEXT_DIM)
        screen.blit(
            spent_label,
            (bar_rect.right - spent_label.get_width() - 10, bar_rect.top + 12),
        )

    def _render_sector_rows(self, screen: pygame.Surface, sw: int) -> None:
        assert (
            self._font_normal is not None
            and self._font_small is not None
            and self._font_title is not None
        )
        manager = self._manager
        assert manager is not None

        # Reset click rects for this frame.
        self._inc_button_rects = {}
        self._dec_button_rects = {}
        self._sector_row_rects = {}

        rows_y = _HEADER_HEIGHT + _POOL_BAR_HEIGHT + _MARGIN
        row_w = sw - _MARGIN * 2

        for sector_id in self._sectors:
            supply = manager.sector_supply.get(sector_id)
            if supply is None:
                continue

            row_rect = pygame.Rect(_MARGIN, rows_y, row_w, _SECTOR_ROW_HEIGHT)
            self._sector_row_rects[sector_id] = row_rect

            is_hovered = self._hovered_sector == sector_id
            bg = (55, 62, 50) if is_hovered else _PANEL_COLOR
            pygame.draw.rect(screen, bg, row_rect, border_radius=3)
            pygame.draw.rect(screen, _BORDER_COLOR, row_rect, 1)

            # Sector name (capitalised).
            name_surf = self._font_title.render(sector_id.upper(), True, _HIGHLIGHT_COLOR)
            screen.blit(name_surf, (row_rect.left + 10, row_rect.top + 6))

            # Supply type + level.
            type_label = _SUPPLY_TYPE_LABELS.get(supply.supply_type, "?")
            level_label = _SUPPLY_LEVEL_LABELS.get(supply.supply_level, "?")
            level_color = self._level_color(supply.supply_level)

            type_surf = self._font_small.render(f"Type: {type_label}", True, _TEXT_DIM)
            screen.blit(type_surf, (row_rect.left + 10, row_rect.top + 34))

            level_surf = self._font_small.render(f"Level: {level_label}", True, level_color)
            screen.blit(level_surf, (row_rect.left + 10, row_rect.top + 52))

            # Rates (ammo / reinforce / morale).
            rates_x = row_rect.left + 200
            rates_text = (
                f"Ammo {supply.ammo_replenishment_rate:.0%}  |  "
                f"Reinf {supply.reinforcement_rate:.0%}  |  "
                f"Morale {supply.morale_recovery_rate:.0%}"
            )
            rates_surf = self._font_small.render(rates_text, True, _TEXT_DIM)
            screen.blit(rates_surf, (rates_x, row_rect.top + 34))

            # Allocated points (large, prominent).
            allocated = self._state.allocations.get(sector_id, 0)
            alloc_label = self._font_normal.render(f"Allocated: {allocated}", True, _POOL_COLOR)
            screen.blit(
                alloc_label,
                (rates_x, row_rect.top + 8),
            )

            # [-] and [+] buttons on the right edge.
            btn_y = row_rect.top + (_SECTOR_ROW_HEIGHT - _BUTTON_HEIGHT) // 2
            dec_rect = pygame.Rect(
                row_rect.right - _BUTTON_WIDTH * 2 - 16,
                btn_y,
                _BUTTON_WIDTH,
                _BUTTON_HEIGHT,
            )
            inc_rect = pygame.Rect(
                row_rect.right - _BUTTON_WIDTH - 8,
                btn_y,
                _BUTTON_WIDTH,
                _BUTTON_HEIGHT,
            )
            self._dec_button_rects[sector_id] = dec_rect
            self._inc_button_rects[sector_id] = inc_rect

            dec_disabled = allocated <= 0 or self._state.confirmed
            inc_disabled = manager.available_supply_points < ALLOCATE_STEP or self._state.confirmed

            self._draw_button(screen, dec_rect, "-", disabled=dec_disabled)
            self._draw_button(screen, inc_rect, "+", disabled=inc_disabled)

            rows_y += _SECTOR_ROW_HEIGHT + 6

    def _render_buttons(self, screen: pygame.Surface, sw: int, sh: int) -> None:
        assert self._font_normal is not None
        btn_y = sh - _BUTTON_HEIGHT - _MARGIN

        # Confirm button (right).
        confirm_w = _CONFIRM_BUTTON_WIDTH
        self._confirm_button_rect = pygame.Rect(
            sw - _MARGIN - confirm_w, btn_y, confirm_w, _BUTTON_HEIGHT
        )
        confirm_label = "Confirmed" if self._state.confirmed else "Confirm"
        self._draw_button(
            screen,
            self._confirm_button_rect,
            confirm_label,
            disabled=self._state.confirmed,
            hover=self._hovered_button == "confirm",
        )

        # Back button (left of confirm).
        back_w = _BACK_BUTTON_WIDTH
        self._back_button_rect = pygame.Rect(
            self._confirm_button_rect.left - back_w - 10,
            btn_y,
            back_w,
            _BUTTON_HEIGHT,
        )
        self._draw_button(
            screen,
            self._back_button_rect,
            "Back",
            hover=self._hovered_button == "back",
            text_color=_TEXT_COLOR,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_allocations(self) -> None:
        """Snapshot the manager's procured_points into the UI state."""
        if self._manager is None:
            self._state.allocations = {}
            return
        self._state.allocations = {
            sector_id: self._manager.procured_points.get(sector_id, 0)
            for sector_id in self._sectors
        }

    def _ensure_fonts(self, font: pygame.font.Font | None) -> None:
        """Initialise font objects if not already done."""
        if self._font_title is not None and self._font_normal is not None:
            return
        if not _pygame_available:
            return
        if not pygame.font.get_init():
            pygame.font.init()
        if font is not None:
            # Seed the normal font from the caller; derive others from it.
            self._font_normal = font
            try:
                size = font.get_height()
                self._font_title = pygame.font.SysFont("consolas", size + 8, bold=True)
                self._font_small = pygame.font.SysFont("consolas", max(12, size - 4))
            except (pygame.error, ValueError, OSError):
                self._font_title = font
                self._font_small = font
        else:
            try:
                self._font_title = pygame.font.SysFont("consolas", 26, bold=True)
                self._font_normal = pygame.font.SysFont("consolas", 18)
                self._font_small = pygame.font.SysFont("consolas", 14)
            except (pygame.error, ValueError, OSError) as e:
                logger.debug("Supply procurement UI font fallback: %s", e)
                self._font_title = pygame.font.Font(None, 32)
                self._font_normal = pygame.font.Font(None, 22)
                self._font_small = pygame.font.Font(None, 18)

    @staticmethod
    def _level_color(level: SupplyLevel) -> tuple[int, int, int]:
        if level == SupplyLevel.FULL:
            return _GOOD_COLOR
        if level == SupplyLevel.REDUCED:
            return _WARN_COLOR
        if level == SupplyLevel.MINIMAL:
            return _WARN_COLOR
        return _BAD_COLOR

    def _draw_button(
        self,
        screen: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        disabled: bool = False,
        hover: bool = False,
        text_color: tuple[int, int, int] | None = None,
    ) -> None:
        assert self._font_normal is not None
        if disabled:
            bg = _BUTTON_DISABLED
            fg = (120, 120, 120)
        elif hover:
            bg = _BUTTON_HOVER
            fg = text_color or _TEXT_COLOR
        else:
            bg = _BUTTON_COLOR
            fg = text_color or _TEXT_COLOR

        pygame.draw.rect(screen, bg, rect, border_radius=3)
        pygame.draw.rect(screen, _BUTTON_BORDER, rect, 1)

        label_surf = self._font_normal.render(label, True, fg)
        screen.blit(
            label_surf,
            (
                rect.centerx - label_surf.get_width() // 2,
                rect.centery - label_surf.get_height() // 2,
            ),
        )
