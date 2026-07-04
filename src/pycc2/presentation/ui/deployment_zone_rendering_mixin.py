"""Deployment zone rendering mixin — extracted from deployment_renderer.py.

Contains zone/map overlay rendering methods used by the DeploymentRenderer
facade:

  - ``render_deployment_zones`` (public): render deployment zone overlays on
    the map using external camera/game_map objects.
  - ``_render_zone_overlays``: build/rebuild zone overlay cache and blit to
    screen.
  - ``_render_placement_highlights``: highlight tiles where the selected
    unit can be placed.
  - ``_render_placed_units``: render placed units with distinct shapes per
    type (CC2 style).
  - ``_render_pending_orders``: render dashed arrows from placed units to
    their pending move targets (GAP-8).
  - ``_render_los_preview``: delegate to DeploymentLOSSystem for LOS preview.

This is a mixin — do not instantiate directly. The DeploymentRenderer facade
inherits this mixin and provides all required attributes via its ``__init__``.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on. Cross-mixin helpers (``_draw_dashed_line`` /
``_draw_arrowhead``) are provided by DeploymentLOSHelpersMixin via MRO.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

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
    ZoneType,
)

# Pygame – imported lazily so the module can be imported in headless tests
_pygame_available: bool = False
try:
    import pygame

    _pygame_available = True
except ImportError:
    pygame = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from pycc2.presentation.ui.deployment_ui import DeploymentUI

__all__ = ["DeploymentZoneRenderingMixin"]


class DeploymentZoneRenderingMixin:
    """Zone/map overlay rendering methods. Inherited by the
    DeploymentRenderer facade, not instantiated.
    """

    # -- Facade attributes used by zone rendering methods (no defaults; set by DeploymentRenderer.__init__) --
    _ui: DeploymentUI
    _zone_overlay_cache: pygame.Surface | None
    _zone_overlay_cache_size: tuple[int, int] | None
    _highlight_surf_cache: pygame.Surface | None
    _highlight_surf_cache_size: tuple[int, int] | None

    if TYPE_CHECKING:
        # -- Cross-mixin methods provided by DeploymentLOSHelpersMixin via MRO
        # (declared for typing only, so they do not shadow the real
        # implementation at runtime via MRO). Declared as plain instance
        # methods because @staticmethod cannot be used inside TYPE_CHECKING
        # at class scope; runtime calls work either way. --
        def _draw_dashed_line(
            self,
            surface,
            color: tuple[int, int, int, int],
            start: tuple[int, int],
            end: tuple[int, int],
            dash_length: int = 6,
            gap_length: int = 4,
        ) -> None: ...

        def _draw_arrowhead(
            self,
            surface,
            color: tuple[int, int, int],
            start: tuple[int, int],
            end: tuple[int, int],
            size: int = 8,
        ) -> None: ...

    # ------------------------------------------------------------------
    # Public rendering entry point
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

    def _render_los_preview(self, screen, ox: int, oy: int, ts: int) -> None:
        """Delegate to DeploymentLOSSystem for LOS preview rendering."""
        self._ui._los_system.render_los_preview(screen, ox, oy, ts)
