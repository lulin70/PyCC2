"""Unit position interpolator for smooth visual movement.

Extracted from EnhancedRenderer to isolate the P2-04 smooth unit position
interpolation logic. The coordinator retains a thin wrapper method to
satisfy the IRenderer protocol.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)


class UnitPositionInterpolator:
    """Lerps displayed unit positions toward real pixel positions per frame."""

    LERP_SPEED = 12.0  # units per second — higher = snappier tracking

    def __init__(self) -> None:
        self._unit_positions: dict[str, tuple[float, float]] = {}

    def smooth_positions(self, units: list[Unit], dt: float) -> None:
        """Lerp displayed unit positions toward real pixel positions.

        Call this once per frame before rendering units so they glide
        smoothly instead of snapping grid-to-grid.
        """
        alive_ids: set[str] = set()
        for unit in units:
            if not hasattr(unit, "id") or not hasattr(unit, "position"):
                continue
            if unit.position is None or not hasattr(unit.position, "pixel_position"):
                continue

            alive_ids.add(unit.id)

            try:
                real_x = float(unit.position.pixel_position.x)
                real_y = float(unit.position.pixel_position.y)
            except (AttributeError, TypeError):
                continue

            if unit.id not in self._unit_positions:
                # First seen — snap to real position immediately
                self._unit_positions[unit.id] = (real_x, real_y)
            else:
                dx = real_x - self._unit_positions[unit.id][0]
                dy = real_y - self._unit_positions[unit.id][1]
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > 0.1:
                    step = min(self.LERP_SPEED * dt, dist)
                    self._unit_positions[unit.id] = (
                        self._unit_positions[unit.id][0] + dx * step / dist,
                        self._unit_positions[unit.id][1] + dy * step / dist,
                    )
                else:
                    # Close enough — snap to avoid endless micro-movement
                    self._unit_positions[unit.id] = (real_x, real_y)

        # Clean up dead / removed units
        self._unit_positions = {k: v for k, v in self._unit_positions.items() if k in alive_ids}

    def get_smooth_position(self, unit_id: str) -> tuple[float, float] | None:
        """Return the smoothed (lerped) position for a unit, or None if not tracked."""
        return self._unit_positions.get(unit_id)

    def get_all_positions(self) -> dict[str, tuple[float, float]]:
        """Return the entire position override map (for rendering delegation)."""
        return self._unit_positions

    def clear(self) -> None:
        """Clear all tracked positions."""
        self._unit_positions.clear()
