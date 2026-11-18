"""Contact memory — last-known-position ghosts for units that left vision (MC2-04).

MC2 ``Contact.cpp`` spirit: each observing faction keeps a "last sighting" table
of enemy units. While a unit is inside the observer's VISIBLE tiles the unit
itself is rendered, so no ghost is recorded; the moment it drops out of vision a
ghost is pinned at its last sighted tile/tick. Ghosts expire after
``CONTACT_DECAY_TICKS`` (default 600 ticks ≈ 10 s of logic time) and are cleared
on mission start / save load.

Tables are keyed per *observing* faction, so the ALLIES and AXIS memories are
fully isolated. Rendering only reads :meth:`ContactMemory.ghosts` — it never
writes back.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.systems.fog_of_war import FogOfWar

CONTACT_DECAY_TICKS = 600


@dataclass(slots=True)
class UnitContact:
    """A last-known sighting of one enemy unit, from one observer faction."""

    unit_id: str
    faction: str
    last_seen_tile: tuple[int, int]
    last_seen_tick: int


def _faction_key(faction: object) -> str:
    """Normalize a Faction enum or string into the table key."""
    name = getattr(faction, "name", None)
    return name if isinstance(name, str) else str(faction)


class ContactMemory:
    """Per-observer-faction table of last-seen enemy units (MC2-04).

    ``observe`` runs on the fog update rhythm (every 5 ticks) right after
    ``FogOfWarService.update`` succeeded. A visible→invisible transition pins a
    ghost at the last sighted tile/tick; re-acquiring the unit drops the ghost;
    ghosts older than ``decay_ticks`` expire.
    """

    CONTACT_DECAY_TICKS = CONTACT_DECAY_TICKS

    def __init__(self, decay_ticks: int = CONTACT_DECAY_TICKS) -> None:
        self._decay_ticks = decay_ticks
        # observer faction -> {unit_id: UnitContact}
        self._ghosts: dict[str, dict[str, UnitContact]] = {}
        # observer faction -> {unit_id: (tile, tick)} while the unit is visible
        self._last_seen: dict[str, dict[str, tuple[tuple[int, int], int]]] = {}
        self._current_tick: int = 0

    def observe(
        self,
        units: list[Unit],
        visible_grid: FogOfWar,
        tick: int,
        observer_faction: object,
    ) -> None:
        """Update the observer's table from the freshly recomputed fog grid.

        ``visible_grid`` is the observer faction's ``FogOfWar`` grid (anything
        exposing ``is_visible(TileCoord)`` works). Own-faction and dead units
        never become contacts.
        """
        self._current_tick = tick
        key = _faction_key(observer_faction)
        ghosts = self._ghosts.setdefault(key, {})
        last_seen = self._last_seen.setdefault(key, {})

        for unit in units:
            if _faction_key(unit.faction) == key:
                continue  # own units never become enemy contacts
            if not unit.is_alive:
                ghosts.pop(unit.id, None)  # a dead unit is not a contact anymore
                last_seen.pop(unit.id, None)
                continue
            if unit.position is None:
                continue
            tile = unit.position.tile_coord
            tile_xy = (tile.x, tile.y)
            if visible_grid.is_visible(TileCoord(tile.x, tile.y)):
                # VISIBLE: the unit itself renders — refresh the sighting and
                # drop any stale ghost (target re-acquired).
                last_seen[unit.id] = (tile_xy, tick)
                ghosts.pop(unit.id, None)
            elif unit.id in last_seen:
                # Visible → invisible transition: pin the ghost at the last
                # sighting (tile/tick frozen at the moment it was seen).
                seen_tile, seen_tick = last_seen.pop(unit.id)
                ghosts[unit.id] = UnitContact(
                    unit_id=unit.id,
                    faction=_faction_key(unit.faction),
                    last_seen_tile=seen_tile,
                    last_seen_tick=seen_tick,
                )

        self._prune(key, tick)

    def ghosts(self, faction: object, tick: int | None = None) -> list[UnitContact]:
        """Return the observer faction's non-expired ghosts (read-only query)."""
        key = _faction_key(faction)
        now = self._current_tick if tick is None else tick
        entries = self._ghosts.get(key, {})
        return [c for c in entries.values() if now - c.last_seen_tick <= self._decay_ticks]

    def clear(self) -> None:
        """Drop every table (mission start / save load)."""
        self._ghosts.clear()
        self._last_seen.clear()
        self._current_tick = 0

    def _prune(self, key: str, tick: int) -> None:
        """Expire ghosts and stale sightings older than the decay window."""
        ghosts = self._ghosts.get(key)
        if ghosts:
            expired = [
                unit_id
                for unit_id, contact in ghosts.items()
                if tick - contact.last_seen_tick > self._decay_ticks
            ]
            for unit_id in expired:
                del ghosts[unit_id]
        last_seen = self._last_seen.get(key)
        if last_seen:
            stale = [
                unit_id
                for unit_id, (_, seen_tick) in last_seen.items()
                if tick - seen_tick > self._decay_ticks
            ]
            for unit_id in stale:
                del last_seen[unit_id]


__all__ = ["CONTACT_DECAY_TICKS", "ContactMemory", "UnitContact"]
