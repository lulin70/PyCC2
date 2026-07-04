"""Deployment LOS (Line-of-Sight) helpers mixin — extracted from deployment_renderer.py.

Contains LOS-related helper methods and class constants used by the
DeploymentRenderer facade:

  - ``_LOS_COLOR_HIGH`` / ``_LOS_COLOR_MODERATE`` / ``_LOS_COLOR_LOW`` /
    ``_LOS_COLOR_IMPOSSIBLE``: 4-color hit-probability scheme (matching
    AttackLineSystem).
  - ``_LOS_DEFAULT_RANGE``: default visual range in tiles.
  - ``_estimate_deployment_hit_probability``: delegate to DeploymentLOSSystem.
  - ``_hit_probability_to_los_color``: delegate to DeploymentLOSSystem.
  - ``_draw_dashed_line`` (staticmethod): delegate to rendering_utils.
  - ``_draw_arrowhead`` (staticmethod): delegate to DeploymentLOSSystem.

This is a mixin — do not instantiate directly. The DeploymentRenderer facade
inherits this mixin and provides all required attributes via its ``__init__``.
Class-level attribute declarations below tell mypy which facade fields the
mixin methods rely on.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycc2.presentation.ui.deployment_los import DeploymentLOSSystem
from pycc2.presentation.ui.deployment_models import DeploymentUnit

if TYPE_CHECKING:
    from pycc2.presentation.ui.deployment_ui import DeploymentUI

__all__ = ["DeploymentLOSHelpersMixin"]


class DeploymentLOSHelpersMixin:
    """Line-of-Sight helper methods. Inherited by the DeploymentRenderer
    facade, not instantiated.
    """

    # -- Facade attributes used by LOS helper methods (no defaults; set by DeploymentRenderer.__init__) --
    _ui: DeploymentUI

    # ------------------------------------------------------------------
    # LOS preview color constants (matching AttackLineSystem 4-color scheme)
    # ------------------------------------------------------------------

    _LOS_COLOR_HIGH: tuple[int, int, int, int] = (0, 255, 0, 160)  # Green (60-100% hit)
    _LOS_COLOR_MODERATE: tuple[int, int, int, int] = (255, 255, 0, 160)  # Yellow (30-59% hit)
    _LOS_COLOR_LOW: tuple[int, int, int, int] = (255, 50, 50, 160)  # Red (10-29% hit)
    _LOS_COLOR_IMPOSSIBLE: tuple[int, int, int, int] = (0, 0, 0, 160)  # Black (0-9% hit)
    _LOS_DEFAULT_RANGE: int = 15  # Default visual range in tiles

    # ------------------------------------------------------------------
    # LOS helpers (delegate to DeploymentLOSSystem)
    # ------------------------------------------------------------------

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
