"""Deployment roster rendering mixin — extracted from deployment_renderer.py.

Contains force-pool roster panel rendering methods used by the
DeploymentRenderer facade:

  - ``_rebuild_roster_layout``: rebuild roster layout with category headers.
  - ``_render_roster``: render the force pool panel (left side).
  - ``_render_rp_header``: render requisition points header with progress bar.
  - ``_render_requisition_points``: render prominent RP counter at top of
    screen.
  - ``_render_unit_counts``: render infantry/support unit counts.
  - ``_render_start_battle_button``: render prominent START BATTLE button.
  - ``_render_unit_details_panel``: render detailed unit info panel (right
    side).

This is a mixin — do not instantiate directly. The DeploymentRenderer facade
inherits this mixin and provides all required attributes via its ``__init__``.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from pycc2.presentation.ui.deployment_models import (
    CATEGORY_INFO as _CATEGORY_INFO,
)
from pycc2.presentation.ui.deployment_models import (
    ROSTER_BG as _ROSTER_BG,
)
from pycc2.presentation.ui.deployment_models import (
    ROSTER_BORDER as _ROSTER_BORDER,
)
from pycc2.presentation.ui.deployment_models import (
    ROSTER_CATEGORY_BG as _ROSTER_CATEGORY_BG,
)
from pycc2.presentation.ui.deployment_models import (
    ROSTER_CATEGORY_TEXT as _ROSTER_CATEGORY_TEXT,
)
from pycc2.presentation.ui.deployment_models import (
    ROSTER_PLACED_BG as _ROSTER_PLACED_BG,
)
from pycc2.presentation.ui.deployment_models import (
    ROSTER_SELECTED_BG as _ROSTER_SELECTED_BG,
)
from pycc2.presentation.ui.deployment_models import (
    ROSTER_TEXT as _ROSTER_TEXT,
)
from pycc2.presentation.ui.deployment_models import (
    ROSTER_TEXT_DIM as _ROSTER_TEXT_DIM,
)
from pycc2.presentation.ui.deployment_models import (
    RP_COLOR as _RP_COLOR,
)
from pycc2.presentation.ui.deployment_models import (
    RP_SPENT_COLOR as _RP_SPENT_COLOR,
)
from pycc2.presentation.ui.deployment_models import UnitCategory

# Pygame – imported lazily so the module can be imported in headless tests
_pygame_available: bool = False
try:
    import pygame

    _pygame_available = True
except ImportError:
    pygame = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from pycc2.presentation.ui.deployment_ui import DeploymentUI

logger = logging.getLogger(__name__)

__all__ = ["DeploymentRosterRenderingMixin"]


class DeploymentRosterRenderingMixin:
    """Force-pool roster panel rendering methods. Inherited by the
    DeploymentRenderer facade, not instantiated.
    """

    # -- Facade attributes used by roster rendering methods (no defaults; set by DeploymentRenderer.__init__) --
    _ui: DeploymentUI
    _roster_panel_cache: pygame.Surface | None
    _roster_panel_cache_size: tuple[int, int] | None
    _rp_bg_cache: pygame.Surface | None
    _rp_bg_cache_size: tuple[int, int] | None
    _unit_detail_panel_cache: pygame.Surface | None
    _unit_detail_panel_cache_size: tuple[int, int] | None

    # ------------------------------------------------------------------
    # Internal – force pool panel (LEFT side)
    # ------------------------------------------------------------------

    def _rebuild_roster_layout(self) -> None:
        """Rebuild the roster layout with category headers."""
        ui = self._ui
        ui._roster_layout = []

        # Group units by category
        categories_order = [
            UnitCategory.INFANTRY,
            UnitCategory.SUPPORT,
            UnitCategory.ARMOR,
            UnitCategory.RECON,
        ]
        units_by_category: dict[UnitCategory, list[int]] = {cat: [] for cat in categories_order}

        for i, unit in enumerate(ui._state.available_units):
            cat = unit.category
            units_by_category[cat].append(i)

        for cat in categories_order:
            indices = units_by_category[cat]
            if not indices:
                continue
            ui._roster_layout.append(("category", cat))
            for idx in indices:
                ui._roster_layout.append(("unit", idx))

    def _render_roster(self, screen: pygame.Surface) -> None:
        ui = self._ui
        roster_h = ui.height

        # Background – reuse cached surface
        panel_size = (ui._roster_width, roster_h)
        if self._roster_panel_cache is None or self._roster_panel_cache_size != panel_size:
            self._roster_panel_cache = pygame.Surface(panel_size, pygame.SRCALPHA)
            self._roster_panel_cache_size = panel_size
        panel_surf = self._roster_panel_cache
        panel_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(
            panel_surf,
            _ROSTER_BG,
            (0, 0, ui._roster_width, roster_h),
            border_radius=0,
        )
        pygame.draw.rect(
            panel_surf,
            _ROSTER_BORDER,
            (0, 0, ui._roster_width, roster_h),
            width=1,
        )

        # Title
        if ui._font_normal:
            title = ui._font_normal.render("FORCE POOL", True, _ROSTER_TEXT)
            panel_surf.blit(title, (ui._roster_padding, 8))

        # DISABLED: RP header moved to TOP of screen (more prominent)
        # self._render_rp_header(panel_surf)

        # Scrollable unit list with category headers (start right after title)
        y_offset = 30  # Start early, no RP header taking space
        for entry_type, entry_data in ui._roster_layout:
            if entry_type == "category":
                assert isinstance(entry_data, UnitCategory)
                cat = entry_data
                label_text, icon = _CATEGORY_INFO[cat]
                cat_rect = pygame.Rect(
                    ui._roster_padding,
                    y_offset,
                    ui._roster_width - 2 * ui._roster_padding,
                    ui._roster_category_height,
                )
                pygame.draw.rect(panel_surf, _ROSTER_CATEGORY_BG, cat_rect, border_radius=3)
                if ui._font_small:
                    cat_label = ui._font_small.render(
                        f" {icon} {label_text}", True, _ROSTER_CATEGORY_TEXT
                    )
                    panel_surf.blit(cat_label, (cat_rect.x + 2, cat_rect.y + 4))
                y_offset += ui._roster_category_height + 2

            elif entry_type == "unit":
                assert isinstance(entry_data, int)
                idx = entry_data
                unit = ui._state.available_units[idx]
                item_rect = pygame.Rect(
                    ui._roster_padding,
                    y_offset,
                    ui._roster_width - 2 * ui._roster_padding,
                    ui._roster_item_height,
                )

                # Background
                if idx == ui._selected_unit_index:
                    bg = _ROSTER_SELECTED_BG
                elif unit.is_placed:
                    bg = _ROSTER_PLACED_BG
                else:
                    bg = (50, 54, 62, 150)

                pygame.draw.rect(panel_surf, bg, item_rect, border_radius=4)

                # Text
                if ui._font_small:
                    name_color = _ROSTER_TEXT if not unit.is_placed else _ROSTER_TEXT_DIM
                    prefix = "✓ " if unit.is_placed else "  "
                    text = f"{prefix}{unit.display_name}"
                    label = ui._font_small.render(text, True, name_color)
                    panel_surf.blit(label, (item_rect.x + 4, item_rect.y + 6))

                    # Cost
                    cost_text = f"{unit.deployment_cost}pts"
                    cost_color = _RP_COLOR if not unit.is_placed else _RP_SPENT_COLOR
                    cost_label = ui._font_small.render(cost_text, True, cost_color)
                    panel_surf.blit(
                        cost_label,
                        (item_rect.right - cost_label.get_width() - 4, item_rect.y + 6),
                    )

                y_offset += ui._roster_item_height + 2

        screen.blit(panel_surf, (0, 0))

    # ------------------------------------------------------------------
    # Internal – requisition points HEADER with progress bar (Issue 2)
    # ------------------------------------------------------------------

    def _render_rp_header(self, panel_surf: pygame.Surface) -> None:
        """Render prominent requisition points display with visual progress bar."""
        if not _pygame_available or panel_surf is None:
            return

        ui = self._ui
        remaining = ui.requisition_remaining
        total = ui._state.requisition_points

        if total <= 0:
            return

        # Section background
        header_bg_y = 32
        header_h = 80
        pygame.draw.rect(
            panel_surf,
            (40, 44, 52, 240),
            (4, header_bg_y, ui._roster_width - 8, header_h),
            border_radius=6,
        )
        pygame.draw.rect(
            panel_surf,
            (70, 74, 82),
            (4, header_bg_y, ui._roster_width - 8, header_h),
            width=1,
            border_radius=6,
        )

        # "REQUISITION POINTS" label
        if ui._font_small:
            label = ui._font_small.render("REQUISITION POINTS", True, (180, 170, 130))
            panel_surf.blit(label, (ui._roster_padding + 4, header_bg_y + 6))

        # Large RP value: "RP: 850 / 1200"
        if ui._font_large:
            rp_text = f"RP: {remaining} / {total}"

            # Color based on remaining percentage
            ratio = remaining / total
            if ratio > 0.5:
                rp_color = (100, 220, 100)  # Green - plenty
            elif ratio > 0.25:
                rp_color = (230, 200, 80)  # Yellow - getting low
            elif ratio > 0:
                rp_color = (230, 140, 80)  # Orange - very low
            else:
                rp_color = (230, 80, 80)  # Red - over budget!

            rp_label = ui._font_large.render(rp_text, True, rp_color)
            panel_surf.blit(rp_label, (ui._roster_padding + 4, header_bg_y + 26))

        # === Visual Progress Bar (200px wide, 20px tall) ===
        bar_x = ui._roster_padding + 4
        bar_y = header_bg_y + 58
        bar_w = min(200, ui._roster_width - 16)
        bar_h = 20

        # Bar background (dark)
        pygame.draw.rect(
            panel_surf,
            (30, 30, 35),
            (bar_x, bar_y, bar_w, bar_h),
            border_radius=4,
        )

        # Calculate filled width
        spent = total - remaining
        fill_ratio = min(1.0, max(0.0, spent / total)) if total > 0 else 0
        fill_w = int(bar_w * fill_ratio)

        if fill_w > 0:
            # Bar color based on remaining ratio
            ratio = remaining / total if total > 0 else 0
            if ratio > 0.5:
                bar_color = (60, 180, 60)  # Green
                bar_border = (80, 220, 80)
            elif ratio > 0.25:
                bar_color = (200, 180, 50)  # Yellow
                bar_border = (230, 210, 70)
            elif ratio > 0:
                bar_color = (210, 130, 50)  # Orange
                bar_border = (240, 160, 70)
            else:
                bar_color = (200, 60, 60)  # Red
                bar_border = (230, 90, 90)

            # Filled portion
            pygame.draw.rect(
                panel_surf,
                bar_color,
                (bar_x, bar_y, fill_w, bar_h),
                border_radius=4,
            )

            # Shine effect (lighter top edge)
            if fill_w > 2:
                pygame.draw.line(
                    panel_surf,
                    bar_border,
                    (bar_x + 1, bar_y + 1),
                    (bar_x + fill_w - 1, bar_y + 1),
                    2,
                )

        # Border around entire bar
        pygame.draw.rect(
            panel_surf,
            (90, 94, 102),
            (bar_x, bar_y, bar_w, bar_h),
            width=1,
            border_radius=4,
        )

    # ------------------------------------------------------------------
    # Internal – requisition points (original simple version, now supplemental)
    # ------------------------------------------------------------------

    def _render_requisition_points(self, screen: pygame.Surface) -> None:
        """Render a prominent RP counter at the top of the screen (above roster panel)."""
        if not _pygame_available or screen is None:
            return

        ui = self._ui
        remaining = ui.requisition_remaining
        total = ui._state.requisition_points

        if total <= 0 or not ui._font_large:
            return

        # Create a prominent top bar for RP display
        bar_height = 50
        bar_y = 5  # Near top of screen

        # Background panel
        panel_w = min(350, ui._roster_width + 20)
        panel_x = (ui._roster_width - panel_w) // 2 + 5
        if panel_x < 0:
            panel_x = 5

        # Semi-transparent background – reuse cached surface
        bg_size = (panel_w, bar_height)
        if self._rp_bg_cache is None or self._rp_bg_cache_size != bg_size:
            self._rp_bg_cache = pygame.Surface(bg_size, pygame.SRCALPHA)
            self._rp_bg_cache_size = bg_size
        bg_surf = self._rp_bg_cache
        bg_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(bg_surf, (30, 35, 45, 230), (0, 0, panel_w, bar_height), border_radius=8)
        pygame.draw.rect(
            bg_surf, (80, 85, 100), (0, 0, panel_w, bar_height), width=2, border_radius=8
        )

        # "REQUISITION POINTS" label (small, top)
        if ui._font_small:
            label = ui._font_small.render("◆ REQUISITION POINTS", True, (200, 190, 140))
            bg_surf.blit(label, ((panel_w - label.get_width()) // 2, 6))

        # Large RP value: "850 / 1200"
        rp_text = f"⬢ {remaining} / {total}"

        # Color based on remaining percentage
        ratio = remaining / total if total > 0 else 0
        if ratio > 0.6:
            rp_color = (100, 230, 100)  # Green - plenty
        elif ratio > 0.3:
            rp_color = (240, 220, 80)  # Yellow - getting low
        elif ratio > 0.1:
            rp_color = (245, 150, 70)  # Orange - very low
        elif ratio > 0:
            rp_color = (245, 90, 90)  # Red - critical!
        else:
            rp_color = (255, 60, 60)  # Dark red - over budget!

        rp_label = ui._font_large.render(rp_text, True, rp_color)
        bg_surf.blit(rp_label, ((panel_w - rp_label.get_width()) // 2, 26))

        # Blit to screen
        screen.blit(bg_surf, (panel_x, bar_y))

    # ------------------------------------------------------------------
    # Internal – unit counts
    # ------------------------------------------------------------------

    def _render_unit_counts(self, screen: pygame.Surface) -> None:
        ui = self._ui
        infantry_count = sum(1 for u in ui._state.placed_units if u.unit_type == "infantry")
        support_count = sum(
            1 for u in ui._state.placed_units if u.unit_type in ("support", "vehicle")
        )

        if not ui._font_small:
            return

        inf_color = _ROSTER_TEXT if infantry_count < ui._state.max_infantry else _RP_SPENT_COLOR
        sup_color = _ROSTER_TEXT if support_count < ui._state.max_support else _RP_SPENT_COLOR

        inf_label = ui._font_small.render(
            f"Infantry: {infantry_count}/{ui._state.max_infantry}", True, inf_color
        )
        sup_label = ui._font_small.render(
            f"Support: {support_count}/{ui._state.max_support}", True, sup_color
        )

        screen.blit(inf_label, (ui._roster_padding, ui.height - 75))
        screen.blit(sup_label, (ui._roster_padding + 110, ui.height - 75))

    # ------------------------------------------------------------------
    # Internal – Start Battle button
    # ------------------------------------------------------------------

    def _render_start_battle_button(self, screen: pygame.Surface) -> None:
        """Render prominent START BATTLE button - make it VERY visible and accessible."""
        ui = self._ui
        btn_w = ui._roster_width - 2 * ui._roster_padding
        btn_h = 52  # Extra tall for visibility
        btn_x = ui._roster_padding

        # Position at bottom of roster panel, but ensure it's on screen
        # Leave some margin from actual screen bottom
        max_y = screen.get_height() - 70 if screen.get_height() > 0 else 500
        btn_y = min(ui.height - 60, max_y)

        ui._button_rect = (btn_x, btn_y, btn_w, btn_h)

        enabled = ui.is_deployment_complete()

        if enabled:
            # Bright green when ready - hard to miss
            bg = (40, 160, 60) if not ui._button_hovered else (50, 200, 70)
            border_color = (100, 255, 120)
            # Pulsing effect when enabled (draw attention)
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.003)) * 20
            bg = (int(40 + pulse), int(160 + pulse), 60)
        else:
            bg = (60, 60, 65)  # Dark gray when disabled
            border_color = (90, 90, 95)

        rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        # Draw shadow for depth
        shadow_rect = pygame.Rect(btn_x + 3, btn_y + 3, btn_w, btn_h)
        pygame.draw.rect(screen, (15, 15, 20), shadow_rect, border_radius=10)

        # Draw main button with gradient-like effect
        pygame.draw.rect(screen, bg, rect, border_radius=10)

        # Highlight top edge for 3D effect
        highlight_rect = pygame.Rect(btn_x + 2, btn_y + 2, btn_w - 4, btn_h // 3)
        highlight_color = tuple(min(255, c + 30) for c in bg) if enabled else bg
        pygame.draw.rect(screen, highlight_color, highlight_rect, border_radius=8)

        # Border
        pygame.draw.rect(screen, border_color, rect, width=3, border_radius=10)

        if ui._font_normal:
            text_color = (255, 255, 255) if enabled else (140, 140, 145)

            # Large bold text
            try:
                battle_font = pygame.font.Font(None, 26)
            except (pygame.error, ValueError) as e:
                logging.debug(f"Battle font fallback: {e}")
                battle_font = ui._font_normal

            label = battle_font.render("⚔ START BATTLE", True, text_color)

            # Center text
            text_x = btn_x + (btn_w - label.get_width()) // 2
            text_y = btn_y + (btn_h - label.get_height()) // 2
            screen.blit(label, (text_x, text_y))

        # Show placement count hint below button
        if ui._font_small:
            placed_count = len(ui._state.placed_units)
            len(ui._state.available_units)
            hint_text = f"Units: {placed_count} placed"
            if not enabled:
                hint_text += " (need ≥1)"
            hint_label = ui._font_small.render(hint_text, True, (150, 150, 155))
            screen.blit(hint_label, (btn_x, btn_y + btn_h + 5))

    # ------------------------------------------------------------------
    # Internal – unit details panel (right side)
    # ------------------------------------------------------------------

    def _render_unit_details_panel(self, screen: pygame.Surface) -> None:
        """Render detailed unit information panel on the RIGHT side of screen."""
        ui = self._ui
        if ui._selected_unit_index is None or ui._selected_unit_index >= len(
            ui._state.available_units
        ):
            return

        unit = ui._state.available_units[ui._selected_unit_index]

        # Panel dimensions (right side of screen)
        panel_w = 220
        panel_h = 300
        panel_x = screen.get_width() - panel_w - 10
        panel_y = 80

        # Background – reuse cached surface
        panel_size = (panel_w, panel_h)
        if (
            self._unit_detail_panel_cache is None
            or self._unit_detail_panel_cache_size != panel_size
        ):
            self._unit_detail_panel_cache = pygame.Surface(panel_size, pygame.SRCALPHA)
            self._unit_detail_panel_cache_size = panel_size
        panel_surf = self._unit_detail_panel_cache
        panel_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(panel_surf, (25, 28, 35, 240), (0, 0, panel_w, panel_h), border_radius=8)
        pygame.draw.rect(
            panel_surf, (70, 75, 90), (0, 0, panel_w, panel_h), width=2, border_radius=8
        )

        # Title bar (simple rectangle - pygame doesn't support per-corner radius)
        title_bar_rect = pygame.Rect(0, 0, panel_w, 32)
        pygame.draw.rect(panel_surf, (40, 45, 55), title_bar_rect)

        # Unit name (title)
        if ui._font_normal:
            name_text = (
                unit.display_name[:18] + "..." if len(unit.display_name) > 18 else unit.display_name
            )
            title_label = ui._font_normal.render(name_text, True, (255, 230, 150))
            panel_surf.blit(title_label, (10, 7))

        y_offset = 40
        line_height = 22

        # Unit type badge
        if ui._font_small:
            type_badge = f"[{unit.unit_type.upper()}]"
            type_color = {
                "infantry": (100, 220, 100),
                "support": (100, 180, 220),
                "vehicle": (220, 180, 50),
                "recon": (180, 140, 220),
            }.get(unit.unit_type, (200, 200, 200))
            type_label = ui._font_small.render(type_badge, True, type_color)
            panel_surf.blit(type_label, (10, y_offset))
            y_offset += line_height + 5

        # Separator
        pygame.draw.line(panel_surf, (60, 65, 75), (10, y_offset), (panel_w - 10, y_offset), 1)
        y_offset += 10

        # Unit details
        details = [
            ("Cost", f"{unit.deployment_cost} RP"),
            ("Status", "PLACED" if unit.is_placed else "AVAILABLE"),
            ("Position", f"({unit.position[0]}, {unit.position[1]})" if unit.position else "None"),
            (
                "Category",
                unit.category.value if hasattr(unit.category, "value") else str(unit.category),
            ),
        ]

        for label, value in details:
            if ui._font_small:
                # Label (left side, dimmed)
                lbl = ui._font_small.render(f"{label}:", True, (160, 165, 175))
                panel_surf.blit(lbl, (10, y_offset))

                # Value (right side, bright)
                val = ui._font_small.render(value, True, (220, 225, 235))
                panel_surf.blit(val, (120, y_offset))

                y_offset += line_height

        # Action buttons at bottom - SAVE BUTTON RECT FOR CLICK DETECTION!
        y_offset = panel_h - 60

        btn_w = panel_w - 20
        btn_h = 30

        if not unit.is_placed:
            btn_color = (50, 130, 70)
            btn_text = "PLACE ON MAP"
            btn_action = "place"
        else:
            btn_color = (150, 60, 60)
            btn_text = "REMOVE FROM MAP"
            btn_action = "remove"

        btn_rect = pygame.Rect(10, y_offset, btn_w, btn_h)

        # CRITICAL: Save button rect for click detection in handle_click_full!
        ui._detail_panel_btn_rect = (
            panel_x + btn_rect.x,
            panel_y + btn_rect.y,
            btn_rect.width,
            btn_rect.height,
        )
        ui._detail_panel_btn_action = btn_action

        pygame.draw.rect(panel_surf, btn_color, btn_rect, border_radius=5)
        pygame.draw.rect(panel_surf, (100, 105, 115), btn_rect, width=1, border_radius=5)

        if ui._font_small:
            btn_label = ui._font_small.render(btn_text, True, (255, 255, 255))
            btn_x = 10 + (btn_w - btn_label.get_width()) // 2
            btn_y = y_offset + (btn_h - btn_label.get_height()) // 2
            panel_surf.blit(btn_label, (btn_x, btn_y))

        # Blit panel to screen
        screen.blit(panel_surf, (panel_x, panel_y))
