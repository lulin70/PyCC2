"""World renderer - orchestrates terrain, units, and world-space overlays.

Extracted from EnhancedRenderer to keep the coordinator focused on public API
and high-level delegation. This module composes the work of the specialized
sub-rendering systems.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.building_renderer import BuildingRenderer
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.decoration_renderer import DecorationRenderer
    from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem
    from pycc2.presentation.rendering.environment_renderer import EnvironmentRenderer
    from pycc2.presentation.rendering.shadow_rendering_system import ShadowRenderingSystem
    from pycc2.presentation.rendering.terrain_rendering_system import TerrainRenderingSystem
    from pycc2.presentation.rendering.ui_overlay_renderer import UIOverlayRenderer
    from pycc2.presentation.rendering.unit_fade_renderer import UnitFadeRenderer
    from pycc2.presentation.rendering.unit_renderer import UnitRenderer

logger = logging.getLogger(__name__)


class WorldRenderer:
    """Composes terrain, decorations, buildings, units, and world overlays."""

    def __init__(
        self,
        terrain_rendering_sys: TerrainRenderingSystem,
        decoration_renderer: DecorationRenderer,
        shadow_rendering_sys: ShadowRenderingSystem,
        dynamic_shadow_sys: DynamicShadowSystem | None,
        building_renderer: BuildingRenderer,
        ui_overlay_renderer: UIOverlayRenderer,
        environment_renderer: EnvironmentRenderer,
        unit_renderer: UnitRenderer,
        unit_fade_renderer: UnitFadeRenderer,
    ) -> None:
        self._terrain_rendering_sys = terrain_rendering_sys
        self._decoration_renderer = decoration_renderer
        self._shadow_rendering_sys = shadow_rendering_sys
        self._dynamic_shadow_sys = dynamic_shadow_sys
        self._building_renderer = building_renderer
        self._ui_overlay_renderer = ui_overlay_renderer
        self._environment_renderer = environment_renderer
        self._unit_renderer = unit_renderer
        self._unit_fade_renderer = unit_fade_renderer

    def render_terrain(
        self,
        offscreen: pygame.Surface | None,
        game_map: GameMap,
        camera: Camera,
        debug_mode: bool,
        units: list[Unit] | None,
        dirty_tracker,
    ) -> None:
        """Render terrain tiles, decorations, shadows, buildings, and environment lighting."""
        if offscreen is None:
            return

        # STEP 2: Draw terrain — use enhanced texturing with simple fallback
        try:
            self._terrain_rendering_sys.draw_enhanced_terrain(game_map, camera, debug_mode)
        except RuntimeError as e:
            logger.warning("Enhanced terrain failed, falling back to simple: %s", e)
            self._terrain_rendering_sys.draw_simple_terrain(game_map, camera)

        # PERF: Terrain covers the entire visible viewport; camera movement or
        # tile redraw invalidates all pixels. Keeping full-dirty here is correct
        # because the terrain pass touches every on-screen tile.
        if dirty_tracker is not None:
            dirty_tracker.mark_full_dirty()

        # STEP 3: Draw grid ONLY in debug mode
        if debug_mode:
            self._ui_overlay_renderer.draw_grid(game_map, camera)

        # STEP 4: Draw decorations (minimal)
        self._decoration_renderer.draw_decorations(game_map, camera)

        # STEP 4.0: Draw ALL shadows FIRST (under everything - correct Z-order)
        self._shadow_rendering_sys.render_building_shadows(offscreen, game_map, camera)
        self._shadow_rendering_sys.render_tree_shadows(offscreen, game_map, camera)

        # STEP 4.0-DYN: Dynamic shadow overlay (time-of-day aware)
        if self._dynamic_shadow_sys is not None:
            self._dynamic_shadow_sys.render_dynamic_shadows(
                offscreen, game_map, camera, game_map.width, game_map.height
            )

        # STEP 4.4: Draw building roofs
        self._building_renderer.draw_building_roofs(game_map, camera)

        # STEP 4.5: Draw building interiors (auto-switch when units are inside)
        self._building_renderer.draw_building_interiors(game_map, units or [], camera)

        # STEP 4.6: Draw building floor numbers on roof
        self._building_renderer.draw_building_floor_numbers(game_map, camera)

        # STEP 4.7: Draw Victory Location flags and edge arrows
        self._ui_overlay_renderer.draw_vl_flags(game_map, camera)

        # STEP 4.8: Environment lighting pass (after terrain/buildings, before units)
        self._environment_renderer.apply_environment_lighting(game_map, camera, units)

    def render_units(
        self,
        offscreen: pygame.Surface | None,
        units: list[Unit],
        camera: Camera,
        selected_unit_ids: set[str] | None,
        position_overrides: dict[str, tuple[float, float]] | None,
        dirty_tracker,
        attack_line_system,
    ) -> None:
        """Render all units, fading ghosts, unit shadows, attack and command lines."""
        if offscreen is None:
            return

        # STEP 5: Draw units (positions already smoothed by update phase)
        self._unit_renderer.draw_units(units, camera, selected_unit_ids, position_overrides)

        # PERF: Mark unit screen regions as dirty
        if dirty_tracker is not None and not dirty_tracker._full_redraw:
            for unit in units:
                if not hasattr(unit, "position") or unit.position is None:
                    continue
                try:
                    px = unit.position.pixel_position.x
                    py = unit.position.pixel_position.y
                except (AttributeError, TypeError):
                    continue
                sx = int(px - camera.x + offscreen.get_width() // 2)
                sy = int(py - camera.y + offscreen.get_height() // 2)
                # Bounding box with margin for unit sprite + selection ring
                dirty_tracker.mark_dirty(pygame.Rect(sx - 20, sy - 20, 40, 40))

        # STEP 5.05: Draw death fade-out ghosts
        self._unit_fade_renderer.render_fading_units(offscreen, camera)

        # STEP 5.1: Draw unit and vehicle shadows (AFTER units rendered)
        self._shadow_rendering_sys.render_unit_shadows(offscreen, units, camera)

        # STEP 5.5: Draw attack lines (CC2-style)
        self._ui_overlay_renderer.draw_attack_lines(camera)

        # STEP 5.6: Draw queued command lines (Shift+right-click)
        self._ui_overlay_renderer.draw_queued_commands(units, camera)
