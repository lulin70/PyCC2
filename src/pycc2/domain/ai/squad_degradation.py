"""Squad Degradation and NCO Rally System

Implements CC2-fidelity AI behavior for squad leadership loss effects
and NCO rally mechanics for panicked/routing units.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.components.morale_component import MoraleState
from pycc2.domain.entities.unit import UnitType

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)


class SquadState(Enum):
    """Degradation tiers tracking how a squad's effectiveness has eroded."""

    COMBAT_READY = auto()
    DEGRADED_MILD = auto()
    DEGRADED_MODERATE = auto()
    DEGRADED_SEVERE = auto()


class LeaderRank(Enum):
    """Ranks used to scale degradation severity when a leader is killed."""

    PLATOON_COMMANDER = auto()
    SQUAD_LEADER = auto()


@dataclass(slots=True)
class DegradationModifiers:
    """Per-state penalty values applied to accuracy, reaction, and morale."""

    accuracy_penalty: float = 0.0
    reaction_delay_pct: float = 0.0
    coordination_penalty: float = 0.0
    morale_penalty: int = 0
    panic_contagion_risk: bool = False


SQUAD_STATE_MODIFIERS: dict[SquadState, DegradationModifiers] = {
    SquadState.COMBAT_READY: DegradationModifiers(),
    SquadState.DEGRADED_MILD: DegradationModifiers(
        accuracy_penalty=0.10,
        reaction_delay_pct=0.20,
        coordination_penalty=0.0,
        morale_penalty=0,
        panic_contagion_risk=False,
    ),
    SquadState.DEGRADED_MODERATE: DegradationModifiers(
        accuracy_penalty=0.30,
        reaction_delay_pct=0.50,
        coordination_penalty=0.20,
        morale_penalty=15,
        panic_contagion_risk=False,
    ),
    SquadState.DEGRADED_SEVERE: DegradationModifiers(
        accuracy_penalty=0.50,
        reaction_delay_pct=1.00,
        coordination_penalty=0.30,
        morale_penalty=15,
        panic_contagion_risk=True,
    ),
}

ADVANCED_TACTICS: set[str] = {
    "BOUNDING_OVERWATCH",
    "CROSSFIRE",
    "FLANKING",
}

BASIC_TACTICS: set[str] = {
    "FIRE_CONCENTRATION",
    "DEFENSIVE_LINE",
}

NCO_RECOVERY_TICKS = 30
RALLY_RANGE = 5
RALLY_SENSE_RANGE = 8
RALLY_COOLDOWN_TICKS = 60
RALLY_MORALE_THRESHOLD = 50
RALLY_RESTORE_MORALE = 40


@dataclass(slots=True)
class SquadDegradationRecord:
    """Per-squad degradation state and recovery tracking."""

    squad_id: str
    state: SquadState = SquadState.COMBAT_READY
    recovery_ticks_remaining: int = 0
    pending_nco_id: str | None = None


class SquadDegradationManager:
    """Tracks squad degradation states and coordinates NCO-led recovery."""

    def __init__(self) -> None:
        """Initialize the manager with empty squad records and unit-to-squad mapping."""
        self._squad_records: dict[str, SquadDegradationRecord] = {}
        self._unit_squad_map: dict[str, str] = {}
        self._logger = logging.getLogger("pycc2.ai.squad_degradation")

    def register_squad(self, squad_id: str, unit_ids: list[str]) -> None:
        """Map each unit id to the squad and create its degradation record."""
        for uid in unit_ids:
            self._unit_squad_map[uid] = squad_id
        if squad_id not in self._squad_records:
            self._squad_records[squad_id] = SquadDegradationRecord(squad_id=squad_id)

    def unregister_squad(self, squad_id: str) -> None:
        """Remove a squad and clear all its unit mappings and degradation state."""
        to_remove = [uid for uid, sid in self._unit_squad_map.items() if sid == squad_id]
        for uid in to_remove:
            del self._unit_squad_map[uid]
        self._squad_records.pop(squad_id, None)

    def get_squad_state(self, squad_id: str) -> SquadState:
        """Return the current degradation state of the squad, defaulting to COMBAT_READY."""
        record = self._squad_records.get(squad_id)
        if record is None:
            return SquadState.COMBAT_READY
        return record.state

    def get_modifiers(self, squad_id: str) -> DegradationModifiers:
        """Return the modifiers (penalties) for the squad's current degradation state."""
        state = self.get_squad_state(squad_id)
        return SQUAD_STATE_MODIFIERS[state]

    def get_accuracy_modifier(self, squad_id: str) -> float:
        """Return the accuracy multiplier (1 minus penalty) for the squad."""
        return 1.0 - self.get_modifiers(squad_id).accuracy_penalty

    def get_reaction_delay_multiplier(self, squad_id: str) -> float:
        """Return the reaction time multiplier (1 plus delay) for the squad."""
        return 1.0 + self.get_modifiers(squad_id).reaction_delay_pct

    def is_tactic_available(self, squad_id: str, tactic_name: str) -> bool:
        """Return whether the named tactic is currently allowed for the squad's state."""
        state = self.get_squad_state(squad_id)
        if state == SquadState.COMBAT_READY:
            return True
        if state == SquadState.DEGRADED_MILD:
            return True
        if state in (SquadState.DEGRADED_MODERATE, SquadState.DEGRADED_SEVERE):
            if tactic_name in ADVANCED_TACTICS:
                return False
            return tactic_name in BASIC_TACTICS
        return False

    def get_available_tactics(self, squad_id: str) -> set[str]:
        """Return the set of tactic names allowed for the squad's degradation state."""
        state = self.get_squad_state(squad_id)
        if state == SquadState.COMBAT_READY or state == SquadState.DEGRADED_MILD:
            return ADVANCED_TACTICS | BASIC_TACTICS
        return BASIC_TACTICS.copy()

    def on_leader_killed(
        self,
        killed_unit: Unit,
        squad_units: list[Unit],
    ) -> None:
        """Apply degradation and start NCO recovery when a squad leader is killed."""
        squad_id = killed_unit.squad_id
        if squad_id is None:
            return

        leader_rank = self._determine_leader_rank(killed_unit)
        if leader_rank is None:
            return

        record = self._squad_records.get(squad_id)
        if record is None:
            record = SquadDegradationRecord(squad_id=squad_id)
            self._squad_records[squad_id] = record

        if leader_rank == LeaderRank.PLATOON_COMMANDER:
            record.state = SquadState.DEGRADED_SEVERE
            self._logger.info(
                f"Platoon commander killed: squad {squad_id} enters SEVERE degradation"
            )
        elif leader_rank == LeaderRank.SQUAD_LEADER:
            if record.state.value < SquadState.DEGRADED_MODERATE.value:
                record.state = SquadState.DEGRADED_MODERATE
            self._logger.info(f"Squad leader killed: squad {squad_id} enters MODERATE degradation")

        modifiers = SQUAD_STATE_MODIFIERS[record.state]
        for unit in squad_units:
            if unit.id != killed_unit.id and unit.is_alive:
                unit.morale.apply_delta(-modifiers.morale_penalty)

        nco = self._find_available_nco(squad_units, killed_unit.id)
        if nco is not None:
            record.pending_nco_id = nco.id
            record.recovery_ticks_remaining = NCO_RECOVERY_TICKS
            self._logger.info(
                f"NCO {nco.id} will assume command of squad {squad_id} "
                f"in {NCO_RECOVERY_TICKS} ticks"
            )
        else:
            record.pending_nco_id = None
            record.recovery_ticks_remaining = 0
            self._logger.warning(
                f"No NCO available for squad {squad_id}, remaining in {record.state.name}"
            )

    def tick(self, all_units: list[Unit]) -> None:
        """Advance recovery timers and reassign NCOs for squads each tick."""
        for record in self._squad_records.values():
            if record.recovery_ticks_remaining > 0:
                record.recovery_ticks_remaining -= 1
                if record.recovery_ticks_remaining == 0 and record.pending_nco_id is not None:
                    nco_alive = any(u.id == record.pending_nco_id and u.is_alive for u in all_units)
                    if nco_alive:
                        old_state = record.state
                        record.state = SquadState.DEGRADED_MILD
                        self._logger.info(
                            f"NCO {record.pending_nco_id} assumed command of squad "
                            f"{record.squad_id}: {old_state.name} -> DEGRADED_MILD"
                        )
                    else:
                        self._logger.warning(
                            f"NCO {record.pending_nco_id} died before assuming command "
                            f"of squad {record.squad_id}"
                        )
                    record.pending_nco_id = None

            if record.state == SquadState.DEGRADED_SEVERE:
                squad_units = [u for u in all_units if u.squad_id == record.squad_id]
                alive_count = sum(1 for u in squad_units if u.is_alive)
                if alive_count == 0:
                    continue
                nco = self._find_available_nco(squad_units, exclude_id="")
                if nco is not None and record.pending_nco_id is None:
                    record.pending_nco_id = nco.id
                    record.recovery_ticks_remaining = NCO_RECOVERY_TICKS

    def _determine_leader_rank(self, unit: Unit) -> LeaderRank | None:
        if unit.unit_type == UnitType.COMMANDER:
            return LeaderRank.PLATOON_COMMANDER
        if getattr(unit, "is_squad_leader", False):
            return LeaderRank.SQUAD_LEADER
        return None

    def _find_available_nco(self, squad_units: list[Unit], exclude_id: str = "") -> Unit | None:
        for unit in squad_units:
            if unit.id == exclude_id or not unit.is_alive:
                continue
            if unit.unit_type == UnitType.COMMANDER:
                continue
            if getattr(unit, "is_squad_leader", False):
                continue
            if unit.morale.is_combat_effective:
                return unit
        return None


@dataclass(slots=True)
class RallyRecord:
    """Tracks per-NCO rally cooldown state."""

    nco_id: str
    cooldown_remaining: int = 0


class NCORallyBehavior:
    """Allows NCO units to rally nearby panicked or routing units back to effectiveness."""

    def __init__(self) -> None:
        """Initialize the rally behavior with empty per-NCO cooldown records."""
        self._rally_cooldowns: dict[str, RallyRecord] = {}
        self._logger = logging.getLogger("pycc2.ai.nco_rally")

    def is_nco(self, unit: Unit) -> bool:
        """Return whether the unit is an NCO (squad leader or commander)."""
        if not unit.is_alive:
            return False
        if getattr(unit, "is_squad_leader", False):
            return True
        return unit.unit_type == UnitType.COMMANDER

    def can_rally(self, nco: Unit) -> bool:
        """Return whether the NCO can rally (alive, off cooldown, high morale, unsuppressed)."""
        if not self.is_nco(nco):
            return False
        record = self._rally_cooldowns.get(nco.id)
        if record is not None and record.cooldown_remaining > 0:
            return False
        if nco.morale.value < RALLY_MORALE_THRESHOLD:
            return False
        return nco.suppression_level.name == "NONE"

    def find_panicked_units(
        self,
        nco: Unit,
        all_units: list[Unit],
        sense_range: int = RALLY_SENSE_RANGE,
    ) -> list[Unit]:
        """Return friendly broken or routing units within sense range of the NCO."""
        panicked: list[Unit] = []
        nco_pos = nco.position.tile_coord
        for unit in all_units:
            if unit.id == nco.id or not unit.is_alive:
                continue
            if unit.faction != nco.faction:
                continue
            if unit.morale.state not in (MoraleState.BROKEN, MoraleState.ROUTING):
                continue
            dist = nco_pos.chebyshev_distance(unit.position.tile_coord)
            if dist <= sense_range:
                panicked.append(unit)
        return panicked

    def rally_unit(self, nco: Unit, target: Unit) -> bool:
        """Attempt to rally a single panicked target, restoring its morale and starting cooldown."""
        if not self.can_rally(nco):
            return False
        nco_pos = nco.position.tile_coord
        target_pos = target.position.tile_coord
        if nco_pos.chebyshev_distance(target_pos) > RALLY_RANGE:
            return False
        if target.morale.state not in (MoraleState.BROKEN, MoraleState.ROUTING):
            return False

        target.morale.value = RALLY_RESTORE_MORALE
        target.morale.state = MoraleState.WAVERING
        target.morale.suppression = 1

        self._rally_cooldowns[nco.id] = RallyRecord(
            nco_id=nco.id,
            cooldown_remaining=RALLY_COOLDOWN_TICKS,
        )
        self._logger.info(
            f"NCO {nco.id} rallied unit {target.id}: "
            f"morale restored to {RALLY_RESTORE_MORALE}, state -> SUPPRESSED"
        )
        return True

    def should_move_toward_panicked(self, nco: Unit, all_units: list[Unit]) -> Unit | None:
        """Return the nearest out-of-range panicked unit to move toward, or None if already in range."""
        if not self.can_rally(nco):
            return None
        panicked = self.find_panicked_units(nco, all_units)
        if not panicked:
            return None
        nco_pos = nco.position.tile_coord
        in_range = [
            u for u in panicked if nco_pos.chebyshev_distance(u.position.tile_coord) <= RALLY_RANGE
        ]
        if in_range:
            return None
        nearest = min(
            panicked,
            key=lambda u: nco_pos.chebyshev_distance(u.position.tile_coord),
        )
        return nearest

    def tick(self) -> None:
        """Decrement rally cooldowns and remove expired records each tick."""
        expired: list[str] = []
        for nco_id, record in self._rally_cooldowns.items():
            if record.cooldown_remaining > 0:
                record.cooldown_remaining -= 1
            if record.cooldown_remaining == 0:
                expired.append(nco_id)
        for nco_id in expired:
            del self._rally_cooldowns[nco_id]

    def get_cooldown(self, nco_id: str) -> int:
        """Return the remaining rally cooldown ticks for the NCO, or 0 if none."""
        record = self._rally_cooldowns.get(nco_id)
        if record is None:
            return 0
        return record.cooldown_remaining
