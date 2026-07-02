"""Morale Routing — extracted from morale_system.py (P5-1 batch 2).

Routing / flee behavior for broken and routing units:
  - check_routing_behavior: decide whether a unit should flee
  - _calculate_flee_target: compute nearest map edge as flee target
  - _play_morale_collapse_voice: trigger voice cry on morale collapse

All methods are static and operate on Unit instances passed in by the caller.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from typing import TYPE_CHECKING

from pycc2.domain.systems.morale_types import (
    FLEE_CHANCE_BROKEN,
    FLEE_CHANCE_ROUTING,
    PINNED_THRESHOLD,
    ROUTING_FLEE_DURATION,
    MoraleState,
    RoutingTarget,
    resolve_morale_state,
)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Faction, Unit

logger = logging.getLogger(__name__)


class MoraleRouting:
    """Static utility class for routing / flee behavior management."""

    @staticmethod
    def check_routing_behavior(unit: Unit, game_map: GameMap | None = None) -> tuple[bool, object]:
        """Check if unit should attempt to flee.

        Broken units may refuse orders and try to flee toward map edge.
        Already routing units continue fleeing until they reach safety or rally.

        Args:
            unit: Unit to check
            game_map: Optional game map for flee target calculation

        Returns:
            Tuple of (should_flee, flee_target_position_or_None)

        """
        if unit.morale is None:
            return (False, None)

        current_state = resolve_morale_state(unit.morale.value)

        # Only check for broken/routing units
        if current_state not in (MoraleState.BROKEN, MoraleState.ROUTING):
            return (False, None)

        should_flee = False
        target_pos = None

        if current_state == MoraleState.BROKEN:
            # Chance to start routing
            if random.random() < FLEE_CHANCE_BROKEN:
                should_flee = True
                # Set routing state
                if hasattr(unit, "_routing_target"):
                    unit._routing_target = RoutingTarget(
                        is_fleeing=True, flee_ticks_remaining=ROUTING_FLEE_DURATION
                    )

        elif current_state == MoraleState.ROUTING:
            # Continue routing or rally check
            if hasattr(unit, "_routing_target") and unit._routing_target.is_fleeing:
                if random.random() < FLEE_CHANCE_ROUTING:
                    should_flee = True
                    # Calculate flee direction (toward nearest map edge)
                    if unit.position is not None and unit.position:
                        target_pos = MoraleRouting._calculate_flee_target(unit, game_map)
                        unit._routing_target.position = target_pos

                        # Decrease remaining ticks
                        if unit._routing_target.flee_ticks_remaining > 0:
                            unit._routing_target.flee_ticks_remaining -= 1
                else:
                    # Chance to stop routing (rally attempt)
                    if unit.morale.value > PINNED_THRESHOLD + 10:
                        unit._routing_target.is_fleeing = False

        return (should_flee, target_pos)

    @staticmethod
    def _calculate_flee_target(
        unit: Unit, game_map: GameMap | None = None
    ) -> tuple[int, int] | None:
        """Calculate target position for fleeing unit.

        Units flee toward the nearest map edge, away from known enemies.

        Args:
            unit: The fleeing unit
            game_map: The game map (needed for edge calculation)

        Returns:
            Target tile coordinates as (x, y) tuple, or None if map unavailable

        """
        if game_map is None:
            # Fallback: try to get map from unit's position
            return None

        if unit.position is None:
            return None

        ux = unit.position.tile_coord.x
        uy = unit.position.tile_coord.y

        map_w = game_map.width
        map_h = game_map.height

        # Calculate distance to each edge
        dist_left = ux
        dist_right = map_w - ux
        dist_top = uy
        dist_bottom = map_h - uy

        # Find nearest edge
        min_dist = min(dist_left, dist_right, dist_top, dist_bottom)

        if min_dist == dist_left:
            return (0, uy)  # Flee left
        elif min_dist == dist_right:
            return (map_w - 1, uy)  # Flee right
        elif min_dist == dist_top:
            return (ux, 0)  # Flee up
        else:
            return (ux, map_h - 1)  # Flee down

    @staticmethod
    def play_morale_collapse_voice(
        unit: Unit,
        new_state: MoraleState,
        voice_callback: Callable[[str, Faction], None] | None = None,
    ) -> None:
        """Play a morale collapse voice cry for the unit's faction.

        Args:
            unit: The unit whose morale collapsed
            new_state: The new morale state (BROKEN or ROUTING)
            voice_callback: Optional callback(state_value, faction) for voice playback.
                           If None, voice playback is skipped.

        """
        if voice_callback is None:
            return
        try:
            faction = unit.faction
            if faction is not None:
                voice_callback(new_state.value, faction)
        except (AttributeError, TypeError, ValueError) as e:
            logging.info("Morale collapse voice playback error: %s", e)


__all__ = ["MoraleRouting"]
