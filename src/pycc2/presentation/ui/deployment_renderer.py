"""
Deployment Renderer — All rendering logic for DeploymentUI.

Extracted from deployment_ui.py God Class (v0.3.30 SRP refactoring).
Follows SRP: DeploymentRenderer handles ONLY rendering concerns.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.presentation.ui.deployment_ui import DeploymentUI

logger = logging.getLogger(__name__)

# Pygame – imported lazily so the module can be imported in headless tests
_pygame_available: bool = False
try:
    import pygame

    _pygame_available = True
except ImportError:
    pygame = None  # type: ignore[assignment]

# Import models and constants used by renderers
from pycc2.presentation.ui.deployment_los import DeploymentLOSSystem
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
from pycc2.presentation.ui.deployment_models import (
    VALID_PLACEMENT_COLOR as _VALID_PLACEMENT_COLOR,
)
from pycc2.presentation.ui.deployment_models import (
    ZONE_BORDER_COLORS as _ZONE_BORDER_COLORS,
)
from pycc2.presentation.ui.deployment_models import (
    ZONE_COLORS as _ZONE_COLORS,
)
from pycc2.presentation.ui.deployment_models import (
    DeploymentPhase,
    DeploymentUnit,
    UnitCategory,
    ZoneType,
)


class DeploymentRenderer:
    """Handles all rendering for the deployment phase UI.

    Extracted from DeploymentUI God Class to follow SRP.
    Accesses parent UI state via ``self._ui``.
    """

    def __init__(self, ui: DeploymentUI):
        """Store reference to parent UI for state access."""
        self._ui = ui
        # Surface caches – lazy init to avoid pygame-not-initialized issues
        self._zone_overlay_cache: pygame.Surface | None = None
        self._zone_overlay_cache_size: tuple[int, int] | None = None
        self._highlight_surf_cache: pygame.Surface | None = None
        self._highlight_surf_cache_size: tuple[int, int] | None = None
        self._roster_panel_cache: pygame.Surface | None = None
        self._roster_panel_cache_size: tuple[int, int] | None = None
        self._rp_bg_cache: pygame.Surface | None = None
        self._rp_bg_cache_size: tuple[int, int] | None = None
        self._unit_detail_panel_cache: pygame.Surface | None = None
        self._unit_detail_panel_cache_size: tuple[int, int] | None = None

    # ------------------------------------------------------------------
    # Public rendering entry points
    # ------------------------------------------------------------------

    def render_deployment_zones(
        self,
        surface: pygame.Surface,
        camera,  # Camera-like object with offset_x/offset_y
        game_map,  # GameMap-like object with width/height
        tile_size: int = 48,
    ) -> None:
        """Render deployment zone overlays on the map using camera/game_map objects.

        This is an alternative rendering entry point that works with external
        camera and game_map objects, suitable for integration with the main
        game loop's render pipeline.
        """
        if not _pygame_available or surface is None:
            return

        ui = self._ui
        if ui._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return

        map_w = getattr(game_map, "width", ui._map_width)
        map_h = getattr(game_map, "height", ui._map_height)

        overlay_size = (map_w * tile_size, map_h * tile_size)
        if self._zone_overlay_cache is None or self._zone_overlay_cache_size != overlay_size:
            self._zone_overlay_cache = pygame.Surface(overlay_size, pygame.SRCALPHA)
            self._zone_overlay_cache_size = overlay_size
        zone_overlay = self._zone_overlay_cache
        zone_overlay.fill((0, 0, 0, 0))

        for y in range(map_h):
            for x in range(map_w):
                zone = ui._get_zone_at(x, y)
                if zone == ZoneType.ENEMY_CONTROLLED:
                    pygame.draw.rect(
                        zone_overlay,
                        (60, 60, 60, 100),
                        (x * tile_size, y * tile_size, tile_size, tile_size),
                    )
                elif zone == ZoneType.NO_MANS_LAND:
                    pygame.draw.rect(
                        zone_overlay,
                        (120, 120, 120, 60),
                        (x * tile_size, y * tile_size, tile_size, tile_size),
                    )
                # FRIENDLY zone = no overlay

        cam_x = int(getattr(camera, "offset_x", 0))
        cam_y = int(getattr(camera, "offset_y", 0))
        surface.blit(zone_overlay, (-cam_x, -cam_y))

    def handle_deployment_drag(
        self,
        event: pygame.event.Event,
        camera,  # Camera-like object
        game_map,  # GameMap-like object
        tile_size: int = 48,
    ) -> None:
        """Handle drag-drop deployment interaction using pygame events directly.

        This is an alternative input entry point that works with raw pygame
        events and external camera/game_map objects.
        """
        if not _pygame_available:
            return

        ui = self._ui
        if ui._state.phase not in (DeploymentPhase.DEPLOYING, DeploymentPhase.READY):
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Check if clicking on force pool unit (left of roster)
            if event.pos[0] < ui._roster_width:
                idx = ui._roster_index_at(event.pos[0], event.pos[1])
                if idx is not None and 0 <= idx < len(ui._state.available_units):
                    unit = ui._state.available_units[idx]
                    if not unit.is_placed:
                        ui._dragging_unit = unit
                        ui._dragging_unit_index = idx
                        ui._drag_start_pos = event.pos
                        ui._drag_current_pos = event.pos
                        ui._is_dragging = True
                        ui._selected_unit_index = idx
                        try:
                            ui._ghost_surface = ui._create_ghost_surface(unit)
                        except (pygame.error, ValueError, TypeError) as e:
                            logging.debug(f"Ghost surface creation failed: {e}")
                            ui._ghost_surface = None

        elif event.type == pygame.MOUSEMOTION and ui._is_dragging:
            ui._drag_current_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if ui._is_dragging and ui._dragging_unit is not None:
                cam_x = int(getattr(camera, "offset_x", 0))
                cam_y = int(getattr(camera, "offset_y", 0))
                tile_x = int((event.pos[0] + cam_x) / tile_size)
                tile_y = int((event.pos[1] + cam_y) / tile_size)

                if ui._dragging_unit_index is not None:
                    terrain = ui._get_terrain_at(tile_x, tile_y)
                    if ui.can_place_at(ui._dragging_unit, tile_x, tile_y, terrain):
                        ui.place_unit(ui._dragging_unit_index, tile_x, tile_y)

                ui._clear_drag_state()

    # ------------------------------------------------------------------
    # Internal – zone overlays
    # ------------------------------------------------------------------

    def _render_zone_overlays(
        self,
        screen: pygame.Surface,
        ox: int,
        oy: int,
        ts: int,
    ) -> None:
        ui = self._ui
        if ui._zone_map is None:
            return

        # Build / rebuild overlay cache if tile size changed
        if ui._overlay_cache is None or ui._overlay_tile_size != ts:
            total_w = ui._map_width * ts
            total_h = ui._map_height * ts
            overlay = pygame.Surface((total_w, total_h), pygame.SRCALPHA)

            for y in range(ui._map_height):
                for x in range(ui._map_width):
                    zone = ui._zone_map[y][x]
                    color = _ZONE_COLORS[zone]
                    rect = pygame.Rect(x * ts, y * ts, ts, ts)

                    # Only draw fill if alpha > 0 (FRIENDLY zone has alpha=0, skip fill)
                    if color[3] > 0:
                        pygame.draw.rect(overlay, color, rect)

                    # Draw zone border for all zone types
                    border_color = _ZONE_BORDER_COLORS[zone]
                    border_alpha = 80 if zone != ZoneType.FRIENDLY else 40  # Subtler for friendly
                    pygame.draw.rect(overlay, (*border_color, border_alpha), rect, 1)

            ui._overlay_cache = overlay
            ui._overlay_tile_size = ts

        screen.blit(ui._overlay_cache, (ox, oy))

    # ------------------------------------------------------------------
    # Internal – placement highlights
    # ------------------------------------------------------------------

    def _render_placement_highlights(
        self,
        screen: pygame.Surface,
        ox: int,
        oy: int,
        ts: int,
    ) -> None:
        ui = self._ui
        if ui._selected_unit_index is None:
            return
        if ui._selected_unit_index >= len(ui._state.available_units):
            return

        unit = ui._state.available_units[ui._selected_unit_index]
        if unit.is_placed:
            return

        # Skip if not enough requisition points
        if unit.deployment_cost > ui.requisition_remaining:
            return

        highlight_size = (ts, ts)
        if self._highlight_surf_cache is None or self._highlight_surf_cache_size != highlight_size:
            self._highlight_surf_cache = pygame.Surface(highlight_size, pygame.SRCALPHA)
            self._highlight_surf_cache_size = highlight_size
        highlight_surf = self._highlight_surf_cache

        for y in range(ui._map_height):
            for x in range(ui._map_width):
                terrain = ui._get_terrain_at(x, y)
                if ui.can_place_at(unit, x, y, terrain):
                    # Check not already occupied
                    occupied = any(pu.position == (x, y) for pu in ui._state.placed_units)
                    if not occupied:
                        highlight_surf.fill(_VALID_PLACEMENT_COLOR)
                        screen.blit(highlight_surf, (ox + x * ts, oy + y * ts))

    # ------------------------------------------------------------------
    # Internal – placed unit markers
    # ------------------------------------------------------------------

    def _render_placed_units(
        self,
        screen: pygame.Surface,
        ox: int,
        oy: int,
        ts: int,
    ) -> None:
        """Render placed units with DISTINCT SHAPES for each type (CC2 style)."""
        ui = self._ui
        for pu in ui._state.placed_units:
            if pu.position is None:
                continue
            px, py = pu.position
            cx = ox + px * ts + ts // 2
            cy = oy + py * ts + ts // 2

            # Base size depends on unit type
            if pu.unit_type == "vehicle":
                radius = max(ts // 2, 8)  # Larger for vehicles
            elif pu.unit_type == "recon":
                radius = max(ts // 4, 4)  # Smaller for recon
            else:
                radius = max(ts // 3, 5)  # Normal for infantry/support

            # Draw shape based on unit type
            if pu.unit_type == "infantry":
                # CIRCLE - Infantry (green tones)
                color = (80, 200, 80)
                pygame.draw.circle(screen, color, (cx, cy), radius)
                pygame.draw.circle(screen, (255, 255, 255), (cx, cy), radius, 2)

                # Add soldier icon hint (small dot in center)
                pygame.draw.circle(screen, (40, 120, 40), (cx, cy), radius // 3)

            elif pu.unit_type == "support":
                # TRIANGLE - Support/MG/AT (blue tones)
                color = (100, 180, 220)
                points = []
                for i in range(3):
                    angle = math.pi / 3 * 2 * i - math.pi / 2
                    x = cx + int(radius * math.cos(angle))
                    y = cy + int(radius * math.sin(angle))
                    points.append((x, y))
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, (255, 255, 255), points, 2)

            elif pu.unit_type == "vehicle":
                # HEXAGON/DIAMOND - Armor/Tanks (orange/yellow tones)
                color = (220, 180, 50)
                points = []
                for i in range(6):
                    angle = math.pi / 3 * i
                    x = cx + int(radius * math.cos(angle))
                    y = cy + int(radius * math.sin(angle))
                    points.append((x, y))
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, (255, 220, 100), points, 2)

                # Add tank turret hint (small circle on top)
                pygame.draw.circle(screen, (180, 140, 30), (cx, cy - radius // 3), radius // 3)

            elif pu.unit_type == "recon":
                # SMALL DIAMOND - Recon/Sniper (purple tones)
                color = (180, 140, 220)
                half = radius // 2
                points = [
                    (cx, cy - radius),
                    (cx + half, cy),
                    (cx, cy + radius),
                    (cx - half, cy),
                ]
                pygame.draw.polygon(screen, color, points)
                pygame.draw.polygon(screen, (220, 180, 255), points, 1)
            else:
                # DEFAULT: Square for unknown types
                color = (200, 200, 200)
                rect = pygame.Rect(cx - radius // 2, cy - radius // 2, radius, radius)
                pygame.draw.rect(screen, color, rect)
                pygame.draw.rect(screen, (255, 255, 255), rect, 1)

            # Unit label (abbreviated name)
            if ui._font_small and ts >= 16:
                label_text = pu.display_name[:4] if len(pu.display_name) > 4 else pu.display_name
                label = ui._font_small.render(label_text, True, (255, 255, 255))
                label_x = cx - label.get_width() // 2
                label_y = cy + radius + 2
                # Background for readability
                bg_rect = pygame.Rect(
                    label_x - 2, label_y - 1, label.get_width() + 4, label.get_height() + 2
                )
                pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect, border_radius=2)
                screen.blit(label, (label_x, label_y))

    # ------------------------------------------------------------------
    # Internal – pending order arrows (GAP-8)
    # ------------------------------------------------------------------

    def _render_pending_orders(
        self,
        screen: pygame.Surface,
        ox: int,
        oy: int,
        ts: int,
    ) -> None:
        """Render arrows from placed units to their pending move targets."""
        ui = self._ui
        if not ui._pending_orders:
            return

        for pu in ui._state.placed_units:
            if pu.position is None:
                continue
            order = ui._pending_orders.get(pu.unit_template_id)
            if order is None:
                continue

            src_x, src_y = pu.position
            dst_x, dst_y = order

            # Source center
            sx = ox + src_x * ts + ts // 2
            sy = oy + src_y * ts + ts // 2
            # Destination center
            dx = ox + dst_x * ts + ts // 2
            dy = oy + dst_y * ts + ts // 2

            # Draw dashed line from source to destination
            line_color = (255, 200, 50, 180)  # Yellow-gold for orders
            self._draw_dashed_line(
                screen, line_color, (sx, sy), (dx, dy), dash_length=6, gap_length=4
            )

            # Draw target marker (X mark)
            mark_size = max(ts // 4, 4)
            pygame.draw.line(
                screen,
                (255, 200, 50),
                (dx - mark_size, dy - mark_size),
                (dx + mark_size, dy + mark_size),
                2,
            )
            pygame.draw.line(
                screen,
                (255, 200, 50),
                (dx + mark_size, dy - mark_size),
                (dx - mark_size, dy + mark_size),
                2,
            )

            # Draw small circle at target
            pygame.draw.circle(screen, (255, 200, 50), (dx, dy), mark_size + 2, 1)

            # Arrowhead at destination
            self._draw_arrowhead(screen, (255, 200, 50), (sx, sy), (dx, dy), size=8)

    # ------------------------------------------------------------------
    # Internal – LOS preview lines (G5)
    # ------------------------------------------------------------------

    # LOS preview color constants (matching AttackLineSystem 4-color scheme)
    _LOS_COLOR_HIGH: tuple[int, int, int, int] = (0, 255, 0, 160)  # Green (60-100% hit)
    _LOS_COLOR_MODERATE: tuple[int, int, int, int] = (255, 255, 0, 160)  # Yellow (30-59% hit)
    _LOS_COLOR_LOW: tuple[int, int, int, int] = (255, 50, 50, 160)  # Red (10-29% hit)
    _LOS_COLOR_IMPOSSIBLE: tuple[int, int, int, int] = (0, 0, 0, 160)  # Black (0-9% hit)
    _LOS_DEFAULT_RANGE: int = 15  # Default visual range in tiles

    def _render_los_preview(self, screen, ox: int, oy: int, ts: int) -> None:
        """Delegate to DeploymentLOSSystem for LOS preview rendering."""
        self._ui._los_system.render_los_preview(screen, ox, oy, ts)

    def _estimate_deployment_hit_probability(
        self,
        src_x: int,
        src_y: int,
        dst_x: int,
        dst_y: int,
        distance: float,
        unit: DeploymentUnit,
    ) -> float:
        """Delegate to DeploymentLOSSystem for hit probability estimation."""
        ui = self._ui
        return DeploymentLOSSystem.estimate_hit_probability(
            src_x,
            src_y,
            dst_x,
            dst_y,
            distance,
            unit,
            ui._tile_grid,
            ui._get_terrain_at,
        )

    def _hit_probability_to_los_color(self, hit_prob: float) -> tuple[int, int, int, int]:
        """Delegate to DeploymentLOSSystem for probability→color mapping."""
        return DeploymentLOSSystem.hit_probability_to_color(hit_prob)

    @staticmethod
    def _draw_dashed_line(
        surface,
        color: tuple[int, int, int, int],
        start: tuple[int, int],
        end: tuple[int, int],
        dash_length: int = 6,
        gap_length: int = 4,
    ) -> None:
        """Delegate to DeploymentLOSSystem.draw_dashed_line (via rendering_utils)."""
        from pycc2.presentation.rendering.rendering_utils import draw_dashed_line

        draw_dashed_line(surface, color, start, end, dash_length=dash_length, gap_length=gap_length)

    @staticmethod
    def _draw_arrowhead(
        surface,
        color: tuple[int, int, int],
        start: tuple[int, int],
        end: tuple[int, int],
        size: int = 8,
    ) -> None:
        """Delegate to DeploymentLOSSystem.draw_arrowhead."""
        DeploymentLOSSystem.draw_arrowhead(surface, color, start, end, size)

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

    # ------------------------------------------------------------------
    # Internal – drag visual feedback
    # ------------------------------------------------------------------

    def _render_drag_feedback(
        self,
        screen: pygame.Surface,
        map_offset_x: int = 0,
        map_offset_y: int = 0,
        tile_size: int = 16,
    ) -> None:
        """Render drag visual feedback: ghost unit + tile highlights."""
        ui = self._ui
        if not ui._is_dragging or ui._drag_current_pos is None:
            return

        if not _pygame_available or screen is None:
            return

        mx, my = ui._drag_current_pos

        # === 1. Highlight tile under cursor ===
        if mx >= ui._roster_width and ui._dragging_unit is not None:
            map_pos = ui.screen_to_map(mx, my, map_offset_x, map_offset_y, tile_size)

            if map_pos is not None:
                map_x, map_y = map_pos
                terrain = ui._get_terrain_at(map_x, map_y)
                can_place = ui.can_place_at(ui._dragging_unit, map_x, map_y, terrain)

                # Check if occupied
                occupied = any(pu.position == (map_x, map_y) for pu in ui._state.placed_units)

                # Check RP budget
                enough_rp = (
                    ui._dragging_unit is not None
                    and ui._dragging_unit.deployment_cost <= ui.requisition_remaining
                )

                is_valid = can_place and not occupied and enough_rp

                # CRITICAL FIX: Highlight box must use ACTUAL screen position (including roster width)
                tile_screen_x = ui._roster_width + map_offset_x + map_x * tile_size
                tile_screen_y = map_offset_y + map_y * tile_size

                if is_valid:
                    if tile_size not in ui._highlight_surface_cache:
                        ui._highlight_surface_cache[tile_size] = pygame.Surface(
                            (tile_size, tile_size), pygame.SRCALPHA
                        )
                    highlight = ui._highlight_surface_cache[tile_size]
                    highlight.fill((0, 255, 100, 70))
                    screen.blit(highlight, (tile_screen_x, tile_screen_y))

                    pygame.draw.rect(
                        screen,
                        (0, 255, 100),
                        (tile_screen_x, tile_screen_y, tile_size, tile_size),
                        2,
                    )
                else:
                    if tile_size not in ui._highlight_surface_cache:
                        ui._highlight_surface_cache[tile_size] = pygame.Surface(
                            (tile_size, tile_size), pygame.SRCALPHA
                        )
                    highlight = ui._highlight_surface_cache[tile_size]
                    highlight.fill((255, 60, 60, 50))
                    screen.blit(highlight, (tile_screen_x, tile_screen_y))

                    # Red border
                    pygame.draw.rect(
                        screen,
                        (255, 80, 80),
                        (tile_screen_x, tile_screen_y, tile_size, tile_size),
                        2,
                    )

        # === 2. Draw ghost unit following cursor ===
        if ui._ghost_surface is not None:
            ghost_x = mx - ui._ghost_surface.get_width() // 2
            ghost_y = my - ui._ghost_surface.get_height() // 2
            screen.blit(ui._ghost_surface, (ghost_x, ghost_y))

    # ------------------------------------------------------------------
    # Font initialization helper
    # ------------------------------------------------------------------

    def _ensure_fonts(self, font) -> None:
        """Initialise font objects if not already done."""
        if not _pygame_available:
            return
        ui = self._ui
        # CRITICAL FIX: Always create default fonts even if font param is None!
        if ui._font_normal is None:
            if font is not None:
                ui._font_normal = font
            else:
                # Create default normal font (was missing - caused button text to not render!)
                try:
                    ui._font_normal = pygame.font.Font(None, 20)
                except (pygame.error, ValueError) as e:
                    logging.debug(f"Normal font creation failed: {e}")
                    ui._font_normal = None
        if ui._font_small is None:
            try:
                ui._font_small = pygame.font.Font(None, 16)
            except (pygame.error, ValueError) as e:
                logging.debug(f"Small font creation failed: {e}")
                ui._font_small = None
        if ui._font_large is None:
            try:
                ui._font_large = pygame.font.Font(None, 32)
            except (pygame.error, ValueError) as e:
                logging.debug(f"Large font creation failed: {e}")
                ui._font_large = None
