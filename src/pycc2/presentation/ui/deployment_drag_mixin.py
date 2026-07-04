"""Deployment drag interaction mixin — extracted from deployment_renderer.py.

Contains drag-related interaction and visual feedback methods used by the
DeploymentRenderer facade:

  - ``handle_deployment_drag`` (public): handle drag-drop deployment
    interaction using raw pygame events.
  - ``_render_drag_feedback``: render ghost unit + tile highlights during
    active drag.
  - ``_ensure_fonts``: initialize font objects if not already done.

This is a mixin — do not instantiate directly. The DeploymentRenderer facade
inherits this mixin and provides all required attributes via its ``__init__``.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pycc2.presentation.ui.deployment_models import DeploymentPhase

if TYPE_CHECKING:
    from pycc2.presentation.ui.deployment_ui import DeploymentUI

# Pygame – imported lazily so the module can be imported in headless tests
_pygame_available: bool = False
try:
    import pygame

    _pygame_available = True
except ImportError:
    pygame = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

__all__ = ["DeploymentDragMixin"]


class DeploymentDragMixin:
    """Drag interaction and visual feedback methods. Inherited by the
    DeploymentRenderer facade, not instantiated.
    """

    # -- Facade attributes used by drag methods (no defaults; set by DeploymentRenderer.__init__) --
    _ui: DeploymentUI

    # ------------------------------------------------------------------
    # Public drag entry point
    # ------------------------------------------------------------------

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
