"""Fog-of-war service driving per-faction visibility from unit observers.

Wraps the domain ``FogOfWar`` grid and recomputes it from the units of one
faction. CC2 keeps three tile states (hidden / explored / currently visible),
so tiles demoted from visible stay explored rather than reverting to hidden.
Recomputation runs every ``FogOfWar.UPDATE_INTERVAL_TICKS`` (5) ticks.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.fog_of_war import FogOfWar

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.tile_coord import TileCoord


class FogOfWarService:
    """Recomputes the fog-of-war grid from the observers of one faction."""

    def __init__(
        self,
        map_width: int,
        map_height: int,
        faction: Faction | None = None,
        enabled: bool = True,
    ) -> None:
        """Create the visibility grid and select the observing faction."""
        self.fog = FogOfWar(map_width, map_height)
        self._faction = faction if faction is not None else Faction.ALLIES
        self.enabled = enabled
        self._last_update_tick = -1

    def update(self, units: list[Unit], game_map: GameMap, current_tick: int) -> bool:
        """Recompute visibility if enabled and this tick is an update tick.

        Returns True when the grid was recomputed, False otherwise.
        """
        if not self.enabled:
            return False
        if current_tick % FogOfWar.UPDATE_INTERVAL_TICKS != 0:
            return False
        if current_tick == self._last_update_tick:
            return False

        observers: list[tuple[TileCoord, int, float, float]] = []
        for unit in units:
            if not unit.is_alive:
                continue
            if unit.faction != self._faction:
                continue
            if unit.position is None or unit.vision is None:
                continue
            observers.append((unit.position.tile_coord, unit.vision.range_tiles, math.tau, 0.0))

        self.fog.reveal_from_observers(observers, game_map, current_tick)
        self._last_update_tick = current_tick
        return True

    def toggle(self) -> bool:
        """Flip the enabled flag and return the new state."""
        self.enabled = not self.enabled
        return self.enabled

    def set_enabled(self, value: bool) -> None:
        """Explicitly enable or disable visibility updates."""
        self.enabled = value


__all__ = ["FogOfWarService"]
