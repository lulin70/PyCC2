"""
Ceasefire and Retreat Mechanism — CC2-Authentic Battle Termination Options

Implements two battle-termination systems from Close Combat 2:

CeasefireSystem:
  - Player can request ceasefire (1-7 hours, i.e., 60-420 ticks)
  - During ceasefire: all units stop firing, medics treat wounded on both
    sides, both sides recover morale (+5 per hour), no reinforcements
  - AI ceasefire decision based on force ratio, morale, VL status
  - Ceasefire can be broken by any unit firing
  - Max 1 ceasefire per battle

RetreatSystem:
  - Player can order retreat from battle
  - Only available after 60 ticks; must have retreat path
  - Retreating units move at double speed toward friendly map edge
  - Retreating units are EXPOSED (+30% hit chance for enemies)
  - Units that don't reach edge in 30 ticks are CAPTURED
  - 10% of retreating units captured even if they reach edge (stragglers)
  - Battle counted as DEFEAT; captured units lost permanently
  - AI retreats when force_ratio < 0.3 AND no VLs held AND morale < 20
  - AI retreat is gradual (units pull back one by one)

Historical basis: 2-hour truce at Oosterbeek (Sept 1944) for medical
evacuation — medics from both sides treated wounded under white flag.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


# ========================================================================
# Enums
# ========================================================================

class CeasefireState(Enum):
    """State of a ceasefire agreement."""
    NONE = auto()
    ACTIVE = auto()
    BROKEN = auto()
    EXPIRED = auto()


class RetreatState(Enum):
    """State of a retreat order."""
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()


# ========================================================================
# Constants
# ========================================================================

# Ceasefire
CEASEFIRE_MIN_TICKS: int = 60       # 1 hour
CEASEFIRE_MAX_TICKS: int = 420      # 7 hours
MORALE_RECOVERY_PER_HOUR: int = 5   # +5 morale per hour during ceasefire
MAX_CEASEFIRES_PER_BATTLE: int = 1

# AI ceasefire decision thresholds
AI_CEASEFIRE_AGREE_FORCE_RATIO: float = 0.5
AI_CEASEFIRE_AGREE_MORALE: float = 30.0
AI_CEASEFIRE_REQUEST_FORCE_RATIO: float = 0.3
AI_CEASEFIRE_BASE_PROBABILITY: float = 0.50
AI_CEASEFIRE_HOUR_BONUS: float = 0.10

# Retreat
RETREAT_MIN_BATTLE_TICKS: int = 60  # Must fight at least 60 ticks
RETREAT_SPEED_MULTIPLIER: float = 2.0
RETREAT_EXPOSURE_BONUS: float = 0.30  # +30% hit chance for enemies
RETREAT_ESCAPE_TICKS: int = 30        # Ticks to reach map edge
STRAGGLER_CAPTURE_RATE: float = 0.10  # 10% captured even on escape
RETREAT_MORALE_PENALTY: int = -10     # Morale penalty for survivors

# AI retreat thresholds
AI_RETREAT_FORCE_RATIO: float = 0.3
AI_RETREAT_MORALE: float = 20.0


# ========================================================================
# CeasefireSystem
# ========================================================================

@dataclass
class CeasefireRecord:
    """Tracks the state of a ceasefire during battle."""
    state: CeasefireState = CeasefireState.NONE
    start_tick: int = 0
    duration_ticks: int = 0
    requested_by: str = ""        # 'player' or 'ai'
    ceasefire_count: int = 0      # Number of ceasefires used this battle


class CeasefireSystem:
    """Manages ceasefire requests, enforcement, and AI decisions.

    Usage::

        cs = CeasefireSystem()
        # Player requests ceasefire
        cs.request_ceasefire(ticks=120, requested_by='player', current_tick=200)
        # Each tick, check enforcement
        cs.tick(current_tick, all_units)
        # If a unit fires
        cs.on_unit_fired(unit_id)
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._record = CeasefireRecord()

    @property
    def state(self) -> CeasefireState:
        return self._record.state

    @property
    def is_active(self) -> bool:
        return self._record.state == CeasefireState.ACTIVE

    @property
    def ceasefire_count(self) -> int:
        return self._record.ceasefire_count

    # ------------------------------------------------------------------
    # Player / AI request
    # ------------------------------------------------------------------

    def request_ceasefire(
        self,
        ticks: int,
        requested_by: str,
        current_tick: int,
    ) -> bool:
        """Request a ceasefire for *ticks* duration.

        Returns True if the ceasefire was established.
        """
        if self._record.ceasefire_count >= MAX_CEASEFIRES_PER_BATTLE:
            return False
        if self._record.state == CeasefireState.ACTIVE:
            return False
        if not (CEASEFIRE_MIN_TICKS <= ticks <= CEASEFIRE_MAX_TICKS):
            return False

        self._record.state = CeasefireState.ACTIVE
        self._record.start_tick = current_tick
        self._record.duration_ticks = ticks
        self._record.requested_by = requested_by
        self._record.ceasefire_count += 1
        return True

    # ------------------------------------------------------------------
    # AI ceasefire decision
    # ------------------------------------------------------------------

    def ai_should_agree_to_ceasefire(
        self,
        force_ratio: float,
        avg_morale: float,
        hours_offered: int = 1,
    ) -> bool:
        """Decide whether the AI agrees to a player-requested ceasefire.

        AI agrees if force_ratio < 0.5 AND morale < 30.
        Probability: 50% base + 10% per hour offered.
        """
        if force_ratio >= AI_CEASEFIRE_AGREE_FORCE_RATIO:
            return False
        if avg_morale >= AI_CEASEFIRE_AGREE_MORALE:
            return False

        probability = (
            AI_CEASEFIRE_BASE_PROBABILITY
            + AI_CEASEFIRE_HOUR_BONUS * hours_offered
        )
        return self._rng.random() < min(probability, 1.0)

    def ai_should_request_ceasefire(
        self,
        force_ratio: float,
        losing_vls: bool,
    ) -> bool:
        """Decide whether the AI should request a ceasefire.

        AI requests if force_ratio < 0.3 AND losing VLs.
        """
        if force_ratio >= AI_CEASEFIRE_REQUEST_FORCE_RATIO:
            return False
        if not losing_vls:
            return False
        return self._rng.random() < AI_CEASEFIRE_BASE_PROBABILITY

    # ------------------------------------------------------------------
    # Tick processing
    # ------------------------------------------------------------------

    def tick(self, current_tick: int, all_units: list[Unit]) -> None:
        """Process one tick of ceasefire logic.

        - If ceasefire is active, enforce firing restrictions
        - Recover morale for both sides
        - Check if ceasefire has expired
        """
        if self._record.state != CeasefireState.ACTIVE:
            return

        elapsed = current_tick - self._record.start_tick

        # Check expiry
        if elapsed >= self._record.duration_ticks:
            self._record.state = CeasefireState.EXPIRED
            return

        # Morale recovery: +5 per hour (60 ticks)
        if elapsed > 0 and elapsed % 60 == 0:
            for unit in all_units:
                if unit.is_alive:
                    unit.morale.apply_delta(MORALE_RECOVERY_PER_HOUR)

    # ------------------------------------------------------------------
    # Ceasefire breaking
    # ------------------------------------------------------------------

    def on_unit_fired(self, unit_id: str) -> bool:
        """Called when any unit fires. Breaks ceasefire immediately.

        Returns True if the ceasefire was broken by this shot.
        """
        if self._record.state != CeasefireState.ACTIVE:
            return False

        self._record.state = CeasefireState.BROKEN
        return True

    def can_unit_fire(self) -> bool:
        """Check whether units are allowed to fire under current ceasefire."""
        return self._record.state != CeasefireState.ACTIVE

    def can_unit_move_into_enemy_los(self) -> bool:
        """Check whether units can move into enemy LOS.

        During ceasefire, units can move but NOT into enemy LOS.
        """
        return self._record.state != CeasefireState.ACTIVE

    def can_reinforcements_arrive(self) -> bool:
        """No reinforcements arrive during ceasefire."""
        return self._record.state != CeasefireState.ACTIVE

    def can_medic_treat_both_sides(self) -> bool:
        """Medics can treat wounded on BOTH sides during ceasefire.

        Historical: 2-hour truce at Oosterbeek.
        """
        return self._record.state == CeasefireState.ACTIVE

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset ceasefire state for a new battle."""
        self._record = CeasefireRecord()


# ========================================================================
# RetreatSystem
# ========================================================================

@dataclass
class RetreatUnitStatus:
    """Tracks an individual unit's retreat progress."""
    unit_id: str
    retreating: bool = False
    ticks_retreating: int = 0
    reached_edge: bool = False
    captured: bool = False


class RetreatSystem:
    """Manages player/AI retreat from battle.

    Usage::

        rs = RetreatSystem()
        # Player orders retreat
        rs.order_retreat(current_tick=120, all_units=player_units)
        # Each tick
        rs.tick(current_tick, retreating_units, enemy_units, map_edge_check_fn)
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._state: RetreatState = RetreatState.NOT_STARTED
        self._start_tick: int = 0
        self._unit_statuses: dict[str, RetreatUnitStatus] = {}
        self._captured_unit_ids: list[str] = []
        self._survivor_unit_ids: list[str] = []

    @property
    def state(self) -> RetreatState:
        return self._state

    @property
    def captured_unit_ids(self) -> list[str]:
        return list(self._captured_unit_ids)

    @property
    def survivor_unit_ids(self) -> list[str]:
        return list(self._survivor_unit_ids)

    # ------------------------------------------------------------------
    # Player retreat
    # ------------------------------------------------------------------

    def can_order_retreat(self, current_tick: int) -> bool:
        """Check if retreat is available (must have fought 60+ ticks)."""
        return current_tick >= RETREAT_MIN_BATTLE_TICKS

    def order_retreat(
        self,
        current_tick: int,
        all_units: list[Unit],
        has_retreat_path: bool = True,
    ) -> bool:
        """Order a full retreat for all alive units.

        Returns True if the retreat was initiated.
        """
        if self._state != RetreatState.NOT_STARTED:
            return False
        if not self.can_order_retreat(current_tick):
            return False
        if not has_retreat_path:
            return False

        self._state = RetreatState.IN_PROGRESS
        self._start_tick = current_tick

        for unit in all_units:
            if unit.is_alive and unit.can_act:
                self._unit_statuses[unit.id] = RetreatUnitStatus(
                    unit_id=unit.id,
                    retreating=True,
                )

        return True

    # ------------------------------------------------------------------
    # AI retreat
    # ------------------------------------------------------------------

    def ai_should_retreat(
        self,
        force_ratio: float,
        holds_vls: bool,
        avg_morale: float,
    ) -> bool:
        """Decide whether the AI should retreat.

        AI retreats when: force_ratio < 0.3 AND no VLs held AND morale < 20.
        """
        if force_ratio >= AI_RETREAT_FORCE_RATIO:
            return False
        if holds_vls:
            return False
        return avg_morale < AI_RETREAT_MORALE

    def ai_retreat_next_unit(
        self,
        current_tick: int,
        friendly_units: list[Unit],
        has_retreat_path: bool = True,
    ) -> str | None:
        """AI gradual retreat: pull back one unit at a time.

        Returns the unit_id of the unit ordered to retreat, or None.
        """
        if not has_retreat_path:
            return None
        if not self.can_order_retreat(current_tick) and self._state == RetreatState.NOT_STARTED:
            return None

        # Pick the weakest unit to retreat first
        candidates: list[Unit] = [
            u for u in friendly_units
            if u.is_alive
            and u.can_act
            and u.id not in self._unit_statuses
        ]
        if not candidates:
            return None

        # Sort by morale ascending, then HP ratio ascending
        weakest = min(
            candidates,
            key=lambda u: (u.morale.value, u.health.hp_ratio),
        )

        self._unit_statuses[weakest.id] = RetreatUnitStatus(
            unit_id=weakest.id,
            retreating=True,
        )

        if self._state == RetreatState.NOT_STARTED:
            self._state = RetreatState.IN_PROGRESS
            self._start_tick = current_tick

        return str(weakest.id)

    # ------------------------------------------------------------------
    # Tick processing
    # ------------------------------------------------------------------

    def tick(
        self,
        current_tick: int,
        retreating_units: list[Unit],
        enemy_units: list[Unit],
        is_at_friendly_edge_fn: object,
    ) -> None:
        """Process one tick of retreat logic.

        Args:
            current_tick: Current game tick.
            retreating_units: Units currently retreating.
            enemy_units: Enemy units (for exposure calculation).
            is_at_friendly_edge_fn: Callable(unit) -> bool, returns True
                if the unit has reached the friendly map edge.
        """
        if self._state != RetreatState.IN_PROGRESS:
            return

        for unit in retreating_units:
            status = self._unit_statuses.get(unit.id)
            if status is None or not status.retreating:
                continue

            status.ticks_retreating += 1

            # Check if unit reached friendly map edge
            edge_check = is_at_friendly_edge_fn
            reached = (
                edge_check(unit) if callable(edge_check) else False
            )

            if reached:
                status.reached_edge = True
                status.retreating = False

                # Straggler capture: 10% chance even on escape
                if self._rng.random() < STRAGGLER_CAPTURE_RATE:
                    status.captured = True
                    self._captured_unit_ids.append(unit.id)
                else:
                    # Survivors get morale penalty
                    unit.morale.apply_delta(RETREAT_MORALE_PENALTY)
                    self._survivor_unit_ids.append(unit.id)

            elif status.ticks_retreating >= RETREAT_ESCAPE_TICKS:
                # Unit didn't reach edge in time — CAPTURED
                status.captured = True
                status.retreating = False
                self._captured_unit_ids.append(unit.id)

        # Check if all retreating units are done
        active = [
            s for s in self._unit_statuses.values()
            if s.retreating
        ]
        if not active:
            self._state = RetreatState.COMPLETED

    # ------------------------------------------------------------------
    # Exposure bonus
    # ------------------------------------------------------------------

    @staticmethod
    def get_enemy_hit_bonus_vs_retreating(unit_id: str, system: RetreatSystem) -> float:
        """Get the additional hit chance bonus against a retreating unit.

        Retreating units are EXPOSED: +30% hit chance for enemies.
        """
        status = system._unit_statuses.get(unit_id)
        if status is not None and status.retreating:
            return RETREAT_EXPOSURE_BONUS
        return 0.0

    # ------------------------------------------------------------------
    # Retreat consequences
    # ------------------------------------------------------------------

    def get_retreat_outcome(self) -> dict:
        """Get the outcome of a completed retreat.

        Returns dict with:
          - battle_result: 'DEFEAT'
          - captured_count: number of captured units
          - survivor_count: number of surviving units
          - captured_unit_ids: list of captured unit IDs
          - survivor_unit_ids: list of surviving unit IDs
        """
        return {
            'battle_result': 'DEFEAT',
            'captured_count': len(self._captured_unit_ids),
            'survivor_count': len(self._survivor_unit_ids),
            'captured_unit_ids': list(self._captured_unit_ids),
            'survivor_unit_ids': list(self._survivor_unit_ids),
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset retreat state for a new battle."""
        self._state = RetreatState.NOT_STARTED
        self._start_tick = 0
        self._unit_statuses.clear()
        self._captured_unit_ids.clear()
        self._survivor_unit_ids.clear()


# ========================================================================
# Demo
# ========================================================================

if __name__ == '__main__':
    print("=" * 80)
    print("CEASEFIRE & RETREAT MECHANISM — CC2-Authentic")
    print("=" * 80)

    # --- Ceasefire demo ---
    cs = CeasefireSystem()
    print(f"\n[Ceasefire] Initial state: {cs.state.name}")

    # Player requests 2-hour ceasefire
    ok = cs.request_ceasefire(ticks=120, requested_by='player', current_tick=100)
    print(f"[Ceasefire] Request 2hr ceasefire: {'Granted' if ok else 'Denied'}")
    print(f"[Ceasefire] State: {cs.state.name}")

    # AI ceasefire decision
    agree = cs.ai_should_agree_to_ceasefire(force_ratio=0.4, avg_morale=25, hours_offered=2)
    print(f"[Ceasefire] AI agrees (fr=0.4, morale=25, 2hr): {agree}")

    request = cs.ai_should_request_ceasefire(force_ratio=0.25, losing_vls=True)
    print(f"[Ceasefire] AI requests (fr=0.25, losing VLs): {request}")

    # Ceasefire broken
    broken = cs.on_unit_fired("unit_42")
    print(f"[Ceasefire] Unit fires -> ceasefire broken: {broken}")
    print(f"[Ceasefire] State: {cs.state.name}")

    # --- Retreat demo ---
    rs = RetreatSystem()
    print(f"\n[Retreat] Initial state: {rs.state.name}")
    print(f"[Retreat] Can retreat at tick 50: {rs.can_order_retreat(50)}")
    print(f"[Retreat] Can retreat at tick 100: {rs.can_order_retreat(100)}")

    # AI retreat decision
    should = rs.ai_should_retreat(force_ratio=0.2, holds_vls=False, avg_morale=15)
    print(f"[Retreat] AI should retreat (fr=0.2, no VLs, morale=15): {should}")

    # Retreat outcome
    rs._state = RetreatState.COMPLETED
    rs._captured_unit_ids = ['unit_1', 'unit_3']
    rs._survivor_unit_ids = ['unit_2', 'unit_4', 'unit_5']
    outcome = rs.get_retreat_outcome()
    print(f"[Retreat] Outcome: {outcome}")

    print("\n✅ Ceasefire & Retreat systems ready for integration!")
