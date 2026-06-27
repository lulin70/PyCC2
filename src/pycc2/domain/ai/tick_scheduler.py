"""AI Tick Scheduler - Hierarchical tick frequencies for AI decision-making.

Inspired by OpenCombat's soldier.rs design, different AI roles operate at
different decision frequencies to simulate command hierarchy:
- Commanders think slowly but strategically (2 Hz)
- Squad leaders think at medium rate (4 Hz)
- Individual soldiers react fastest (8 Hz)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class AITickScheduler:
    """Determines when each unit should make an AI decision based on its role.

    The scheduler implements hierarchical tick frequencies so that higher-level
    AI (commanders) decide less frequently than individual soldiers, reducing
    computational cost while preserving strategic depth.
    """

    COMMANDER_TICK_HZ: int = 2
    SQUAD_LEADER_TICK_HZ: int = 4
    UNIT_TICK_HZ: int = 8
    GAME_TICKS_PER_SECOND: int = 30

    def __init__(self, difficulty_modifier: float = 1.0) -> None:
        """Initialize the scheduler with a difficulty-based tick frequency modifier."""
        self.difficulty_modifier = difficulty_modifier

    def _get_tick_hz(self, unit: Unit) -> int:
        """Return the decision frequency (Hz) for the given unit based on its role."""
        from pycc2.domain.entities.unit import UnitType

        if unit.unit_type == UnitType.COMMANDER:
            return self.COMMANDER_TICK_HZ
        if unit.squad_id is not None and getattr(unit, "is_squad_leader", False):
            return self.SQUAD_LEADER_TICK_HZ
        return self.UNIT_TICK_HZ

    def get_tick_interval(self, unit: Unit) -> int:
        """Return the number of game ticks between decisions for this unit.

        The interval is derived from the unit's decision frequency scaled by
        the difficulty modifier.  A higher difficulty modifier means faster
        decisions (shorter interval).
        """
        effective_hz = self._get_tick_hz(unit) * self.difficulty_modifier
        effective_hz = max(effective_hz, 0.1)
        interval = self.GAME_TICKS_PER_SECOND / effective_hz
        return max(1, int(math.floor(interval)))

    def get_next_tick(self, unit: Unit, current_tick: int) -> int:
        """Return the next tick at which this unit will make a decision."""
        interval = self.get_tick_interval(unit)
        if interval <= 0:
            return current_tick
        remainder = current_tick % interval
        if remainder == 0:
            return current_tick
        return current_tick + (interval - remainder)

    def should_tick(self, unit: Unit, current_tick: int) -> bool:
        """Determine whether the unit should make a decision this tick.

        A unit ticks when the current tick is evenly divisible by its tick
        interval.  Dead or incapacitated units never tick.
        """
        if not unit.is_alive or not unit.can_act:
            return False
        interval = self.get_tick_interval(unit)
        if interval <= 0:
            return True
        return current_tick % interval == 0

    def tick_summary(self, all_units: list[Unit], current_tick: int) -> dict:
        """Return a summary of which units tick this frame.

        Returns a dict with:
            tick: the current tick number
            total_units: count of all units passed in
            ticking_ids: list of unit ids that should tick this frame
            by_role: dict mapping role name to list of ticking unit ids
        """
        ticking_ids: list[str] = []
        by_role: dict[str, list[str]] = {
            "commander": [],
            "squad_leader": [],
            "unit": [],
        }

        for u in all_units:
            if not self.should_tick(u, current_tick):
                continue
            ticking_ids.append(u.id)
            from pycc2.domain.entities.unit import UnitType

            if u.unit_type == UnitType.COMMANDER:
                by_role["commander"].append(u.id)
            elif u.squad_id is not None and getattr(u, "is_squad_leader", False):
                by_role["squad_leader"].append(u.id)
            else:
                by_role["unit"].append(u.id)

        return {
            "tick": current_tick,
            "total_units": len(all_units),
            "ticking_ids": ticking_ids,
            "by_role": by_role,
        }
