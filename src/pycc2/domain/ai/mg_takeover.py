"""
MG Takeover System — CC2-Authentic MG Gunner Death Behavior

When the MG gunner in a squad is killed, another squad member
automatically takes over the weapon.  This mirrors CC2's behaviour
where losing an MG team is devastating, but nearby squad members
can salvage the weapon if they reach it in time.

Rules:
  - On MG gunner death, find nearest living squad member within 3 tiles
  - Transfer weapon to that member (they drop their current weapon)
  - New gunner gets -15% accuracy penalty (unfamiliar with MG)
  - Takes 5 ticks to take over (not instant — unit is vulnerable)
  - If no squad member nearby, MG is abandoned (creates FallenUnitCache)
  - Integration: hooks into existing morale system's ALLY_KILLED event
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.ai.ammo_pickup import FallenUnitCache
from pycc2.domain.entities.unit import UnitType

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IEventPublisher

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TAKEOVER_RANGE: int = 3  # Max tiles to search for a replacement
TAKEOVER_TICKS: int = 5  # Ticks to complete the takeover
MG_ACCURACY_PENALTY: float = 0.15  # -15% accuracy for unfamiliar MG


# ---------------------------------------------------------------------------
# Takeover state
# ---------------------------------------------------------------------------


class TakeoverState(Enum):
    PENDING = auto()  # Waiting to start (unit moving to MG)
    IN_PROGRESS = auto()  # Unit is taking over the MG
    COMPLETED = auto()  # Takeover finished
    ABANDONED = auto()  # No one could take over; MG abandoned


@dataclass(slots=True)
class TakeoverRecord:
    """Tracks an in-progress MG takeover."""

    dead_gunner_id: str
    mg_position_x: int
    mg_position_y: int
    replacement_id: str
    ticks_remaining: int
    state: TakeoverState = TakeoverState.IN_PROGRESS


# ---------------------------------------------------------------------------
# MGTakeoverSystem
# ---------------------------------------------------------------------------


class MGTakeoverSystem:
    """When an MG gunner dies, find a nearby squad member to take over.

    Usage::

        takeover = MGTakeoverSystem(event_bus=event_bus, fallen_cache=cache)
        # When an MG unit dies:
        takeover.on_mg_gunner_killed(dead_mg_unit, squad_members)
        # Each tick:
        takeover.tick(all_units)
    """

    def __init__(
        self,
        event_bus: IEventPublisher,
        fallen_cache: FallenUnitCache | None = None,
    ) -> None:
        self.event_bus = event_bus
        self._fallen_cache = fallen_cache or FallenUnitCache()
        self._active_takeovers: dict[str, TakeoverRecord] = {}
        self._logger = logging.getLogger("pycc2.ai.mg_takeover")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on_mg_gunner_killed(
        self,
        dead_gunner: Unit,
        squad_members: list[Unit],
        current_tick: int = 0,
    ) -> TakeoverRecord | None:
        """Handle MG gunner death event.

        Finds the nearest living squad member within TAKEOVER_RANGE tiles
        and initiates the takeover process.  If no suitable replacement is
        found, the MG is abandoned and registered in the FallenUnitCache.

        Returns the TakeoverRecord if a replacement was found, or None
        if the MG is abandoned.
        """
        if dead_gunner.unit_type != UnitType.MACHINE_GUN_SQUAD:
            return None

        # Already dead gunner should not be processed again
        if dead_gunner.id in self._active_takeovers:
            return None

        mg_pos = dead_gunner.position.tile_coord

        # Find nearest living squad member within range
        replacement = self._find_nearest_replacement(dead_gunner, squad_members)

        if replacement is None:
            # Abandon the MG — register in fallen cache
            self._abandon_mg(dead_gunner, current_tick)
            return None

        # Start the takeover process
        record = TakeoverRecord(
            dead_gunner_id=dead_gunner.id,
            mg_position_x=mg_pos.x,
            mg_position_y=mg_pos.y,
            replacement_id=replacement.id,
            ticks_remaining=TAKEOVER_TICKS,
            state=TakeoverState.IN_PROGRESS,
        )
        self._active_takeovers[dead_gunner.id] = record

        self._logger.info(
            f"MG takeover started: unit {replacement.id} will take over "
            f"MG from {dead_gunner.id} in {TAKEOVER_TICKS} ticks"
        )
        return record

    def tick(self, all_units: list[Unit]) -> list[TakeoverRecord]:
        """Advance all active takeovers by one tick.

        Returns a list of TakeoverRecord entries that completed this tick.
        The caller should apply the takeover effects for completed entries.
        """
        completed: list[TakeoverRecord] = []

        for gunner_id, record in list(self._active_takeovers.items()):
            # Check if replacement is still alive
            replacement = self._find_unit(record.replacement_id, all_units)
            if replacement is None or not replacement.is_alive:
                # Replacement died during takeover — abandon
                record.state = TakeoverState.ABANDONED
                completed.append(record)
                del self._active_takeovers[gunner_id]
                self._logger.info(
                    f"MG takeover abandoned: replacement {record.replacement_id} died"
                )
                continue

            record.ticks_remaining -= 1
            if record.ticks_remaining <= 0:
                record.state = TakeoverState.COMPLETED
                completed.append(record)
                del self._active_takeovers[gunner_id]
                self._apply_takeover(replacement, record)
                self._logger.info(f"MG takeover completed: unit {replacement.id} now operates MG")

        return completed

    def get_takeover_state(self, gunner_id: str) -> TakeoverRecord | None:
        """Return the active takeover record for a dead gunner, if any."""
        return self._active_takeovers.get(gunner_id)

    @property
    def active_takeover_count(self) -> int:
        return len(self._active_takeovers)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _find_nearest_replacement(
        self,
        dead_gunner: Unit,
        squad_members: list[Unit],
    ) -> Unit | None:
        """Find the nearest living squad member within TAKEOVER_RANGE."""
        mg_pos = dead_gunner.position.tile_coord
        candidates: list[tuple[Unit, int]] = []

        for unit in squad_members:
            if unit.id == dead_gunner.id:
                continue
            if not unit.is_alive or not unit.can_act:
                continue
            if unit.unit_type == UnitType.MACHINE_GUN_SQUAD:
                continue  # Already an MG unit
            if not unit.morale.is_combat_effective:
                continue  # Panicked/routing units can't take over

            dist = mg_pos.chebyshev_distance(unit.position.tile_coord)
            if dist <= TAKEOVER_RANGE:
                candidates.append((unit, dist))

        if not candidates:
            return None

        # Pick nearest
        candidates.sort(key=lambda c: c[1])
        return candidates[0][0]

    def _abandon_mg(self, dead_gunner: Unit, current_tick: int) -> None:
        """Register the MG as abandoned in the FallenUnitCache."""
        self._fallen_cache.register(dead_gunner, current_tick)

        self.event_bus.publish_named(
            "MGAbandoned",
            {
                "action": "mg_abandoned",
                "unit_id": dead_gunner.id,
                "position": (
                    dead_gunner.position.tile_coord.x,
                    dead_gunner.position.tile_coord.y,
                ),
            },
        )

        self._logger.info(f"MG abandoned: no replacement found for {dead_gunner.id}")

    def _apply_takeover(self, replacement: Unit, record: TakeoverRecord) -> None:
        """Apply the effects of a completed MG takeover.

        The replacement unit:
          - Drops their current weapon (registered in fallen cache)
          - Receives the MG weapon
          - Gets -15% accuracy penalty (unfamiliar with MG)
          - Unit type changes to MACHINE_GUN_SQUAD
        """
        # Transfer weapon: replacement gets the MG

        # Replace weapon with MG
        replacement.weapon.primary_weapon_id = "mg42"
        replacement.weapon.ammo_remaining = 50  # MG standard ammo
        replacement.weapon.max_ammo = 50
        if hasattr(replacement.weapon, "_update_state"):
            replacement.weapon._update_state()

        # Apply accuracy penalty for unfamiliar MG
        if replacement.combat_state is not None:
            replacement.combat_state.captured_weapon = True
            replacement.combat_state.captured_accuracy_penalty = MG_ACCURACY_PENALTY
        else:
            replacement.weapon.is_captured = True
            replacement.weapon.captured_accuracy_penalty = MG_ACCURACY_PENALTY

        # Change unit type to MG
        replacement.unit_type = UnitType.MACHINE_GUN_SQUAD

        # Publish takeover event
        self.event_bus.publish_named(
            "MGTakeover",
            {
                "action": "mg_takeover",
                "replacement_id": replacement.id,
                "dead_gunner_id": record.dead_gunner_id,
                "position": (record.mg_position_x, record.mg_position_y),
            },
        )

    @staticmethod
    def _find_unit(unit_id: str, all_units: list[Unit]) -> Unit | None:
        for u in all_units:
            if u.id == unit_id:
                return u
        return None
