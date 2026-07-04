"""Deployment Renderer facade — composes the SRP-split rendering mixins.

This module is the public entry point for deployment-phase rendering. The
original monolithic ``DeploymentRenderer`` class (1170 lines) was split during
Phase 2 P0-1 (2026-07-04) into a facade plus four function-specific mixins:

  - ``deployment_zone_rendering_mixin.DeploymentZoneRenderingMixin``
      ``render_deployment_zones`` (public), ``_render_zone_overlays``,
      ``_render_placement_highlights``, ``_render_placed_units``,
      ``_render_pending_orders``, ``_render_los_preview``.
  - ``deployment_roster_rendering_mixin.DeploymentRosterRenderingMixin``
      ``_rebuild_roster_layout``, ``_render_roster``, ``_render_rp_header``,
      ``_render_requisition_points``, ``_render_unit_counts``,
      ``_render_start_battle_button``, ``_render_unit_details_panel``.
  - ``deployment_los_helpers_mixin.DeploymentLOSHelpersMixin``
      ``_estimate_deployment_hit_probability``,
      ``_hit_probability_to_los_color``, ``_draw_dashed_line`` (staticmethod),
      ``_draw_arrowhead`` (staticmethod), and the 5 LOS color/range class
      constants.
  - ``deployment_drag_mixin.DeploymentDragMixin``
      ``handle_deployment_drag`` (public), ``_render_drag_feedback``,
      ``_ensure_fonts``.

The facade ``DeploymentRenderer`` inherits all of the above (zone, roster,
LOS, drag — mixin-first order in MRO) and keeps the ``__init__`` that
initializes ``self._ui`` plus the 5 surface caches. Public API is 100%
backward-compatible.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycc2.presentation.ui.deployment_drag_mixin import DeploymentDragMixin
from pycc2.presentation.ui.deployment_los_helpers_mixin import DeploymentLOSHelpersMixin
from pycc2.presentation.ui.deployment_roster_rendering_mixin import (
    DeploymentRosterRenderingMixin,
)
from pycc2.presentation.ui.deployment_zone_rendering_mixin import (
    DeploymentZoneRenderingMixin,
)

# Pygame – imported lazily so the module can be imported in headless tests.
# Only needed for the surface-cache type annotations in __init__; the actual
# pygame calls live in the mixins.
_pygame_available: bool = False
try:
    import pygame

    _pygame_available = True
except ImportError:
    pygame = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from pycc2.presentation.ui.deployment_ui import DeploymentUI

__all__ = ["DeploymentRenderer"]


class DeploymentRenderer(
    DeploymentZoneRenderingMixin,
    DeploymentRosterRenderingMixin,
    DeploymentLOSHelpersMixin,
    DeploymentDragMixin,
):
    """Handles all rendering for the deployment phase UI.

    Composes 4 function-specific mixins (zone/roster/LOS/drag) split out
    during Phase 2 P0-1 (2026-07-04). Each mixin holds the rendering /
    interaction methods for its functional group; the facade provides
    ``__init__`` and the 5 surface caches. Public API 100% backward-compatible.

    Extracted from DeploymentUI God Class to follow SRP.
    Accesses parent UI state via ``self._ui``.
    """

    def __init__(self, ui: DeploymentUI):
        """Store reference to parent UI for state access.

        Initializes the 5 surface caches lazily — they are populated on first
        use by the mixin rendering methods to avoid pygame-not-initialized
        issues in headless tests.
        """
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
