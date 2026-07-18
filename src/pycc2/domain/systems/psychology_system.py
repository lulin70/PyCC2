"""STATUS: INTEGRATED v0.7.5 — wired into TacticalOrchestrator.tick() Phase 5. Psychology System — CC2-authentic order acceptance evaluation (P3-5).

Provides fine-grained, per-tactic-type evaluation of whether a unit will
accept, delay, or refuse an order based on its psychological state:

  - MoraleComponent.state  (RALLIED / WAVERING / PINNED / BROKEN / ROUTING)
  - SuppressionEffect      (NONE / LIGHT / MODERATE / HEAVY / PINNED / PANIC)
  - FatigueLevel           (FRESH / TIRED / WEARY / EXHAUSTED / SPENT)

This module is intentionally additive — it does NOT modify the existing
MoraleComponent / FatigueComponent / UnitMoraleMixin. Callers that need the
legacy binary can_accept_orders() should continue to use UnitMoraleMixin;
callers that need tactic-aware granularity should use PsychologySystem.

Design reference: docs/VISUAL_FIDELITY_IMPROVEMENT_PLAN.md §5.6
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.components.fatigue_component import FatigueLevel
from pycc2.domain.components.morale_component import MoraleState
from pycc2.domain.systems.combat_mechanics_enhanced import SuppressionEffect

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

__all__ = [
    "OrderAcceptance",
    "OrderRejectionReason",
    "PsychologySystem",
]


# ========================================================================
# Command classification — frozensets for O(1) membership tests
# ========================================================================

# Tactic types that preserve the unit's life — always accepted regardless of
# psychological state. A routing soldier will still try to retreat.
_SURVIVAL_COMMANDS: frozenset[TacticType] = frozenset(
    {
        TacticType.RETREAT,
        TacticType.TAKE_COVER,
        TacticType.SURRENDER,
        TacticType.RALLY_NCO,
    }
)

# Defensive orders — generally accepted; only panic/routing refuses.
_DEFENSIVE_COMMANDS: frozenset[TacticType] = frozenset(
    {
        TacticType.DEFEND,
        TacticType.HOLD_POSITION,
        TacticType.DIG_TRENCH,
        TacticType.DEFEND_VL,
    }
)

# Movement orders — conditional acceptance based on suppression & fatigue.
_MOVEMENT_COMMANDS: frozenset[TacticType] = frozenset(
    {
        TacticType.MOVE_TO,
        TacticType.PATROL,
        TacticType.FLANKING,
        TacticType.COORDINATED_ADVANCE,
        TacticType.CAPTURE_VL,
        TacticType.RECONNAISSANCE,
    }
)

# Offensive orders — strictest acceptance criteria.
_OFFENSIVE_COMMANDS: frozenset[TacticType] = frozenset(
    {
        TacticType.ATTACK,
        TacticType.SUPPRESS_FIRE,
        TacticType.MELEE_ATTACK,
        TacticType.ASSAULT_FORTIFIED,
        TacticType.COUNTER_ATTACK,
        TacticType.BREAK_AMBUSH,
    }
)

# Fatigue levels that impede movement (delayed, not refused)
_MOVE_IMPEDING_FATIGUE: frozenset[FatigueLevel] = frozenset(
    {FatigueLevel.EXHAUSTED, FatigueLevel.SPENT}
)

# Fatigue levels that block offense entirely
_OFFENSE_BLOCKING_FATIGUE: frozenset[FatigueLevel] = frozenset(
    {FatigueLevel.EXHAUSTED, FatigueLevel.SPENT}
)


# ========================================================================
# Public types
# ========================================================================


class OrderRejectionReason(Enum):
    """Why an order was accepted, delayed, or refused."""

    OK = auto()  # Accepted without modification
    SUPPRESSED = auto()  # HEAVY suppression blocks the order
    PINNED = auto()  # PINNED suppression blocks the order
    PANIC = auto()  # PANIC suppression blocks the order
    BROKEN = auto()  # Morale collapsed (< 20)
    ROUTING = auto()  # Unit is actively fleeing
    EXHAUSTED = auto()  # Fatigue >= 75 — movement delayed, offense refused
    SPENT = auto()  # Fatigue >= 100 — same as EXHAUSTED but more severe


@dataclass(frozen=True, slots=True)
class OrderAcceptance:
    """Result of evaluating whether a unit will follow an order.

    Attributes:
        accepted: True if the unit will execute the order this tick.
        reason: Why the order was accepted or refused (OK when accepted).
        delay_ticks: When > 0, the unit will hold the order for this many
            ticks before executing. Only set when accepted=True and the
            unit needs time to comply (e.g. EXHAUSTED movement).

    """

    accepted: bool
    reason: OrderRejectionReason = OrderRejectionReason.OK
    delay_ticks: int = 0

    @staticmethod
    def accept() -> OrderAcceptance:
        """Shorthand for an unmodified acceptance."""
        return OrderAcceptance(accepted=True, reason=OrderRejectionReason.OK, delay_ticks=0)

    @staticmethod
    def reject(reason: OrderRejectionReason) -> OrderAcceptance:
        """Shorthand for a flat refusal."""
        return OrderAcceptance(accepted=False, reason=reason, delay_ticks=0)

    @staticmethod
    def delay(reason: OrderRejectionReason, ticks: int) -> OrderAcceptance:
        """Shorthand for a delayed acceptance."""
        return OrderAcceptance(accepted=True, reason=reason, delay_ticks=ticks)


# ========================================================================
# PsychologySystem — pure static evaluation, no side effects
# ========================================================================


class PsychologySystem:
    """Evaluates whether a unit will accept a specific order.

    Unlike MoraleSystem.can_accept_orders() (binary, random), this system
    provides deterministic, tactic-aware evaluation:

    - Survival commands (RETREAT/TAKE_COVER/SURRENDER/RALLY_NCO) are always
      accepted — even a routing soldier tries to survive.
    - Defensive commands are refused only by PANIC/ROUTING units.
    - Movement commands are refused by HEAVY/PINNED/PANIC suppression or
      ROUTING morale; EXHAUSTED/SPENT fatigue delays them.
    - Offensive commands are the strictest — WAVERING delays, and any
      HEAVY+ suppression, BROKEN/ROUTING morale, or EXHAUSTED+ fatigue
      causes refusal.

    The system reads but never mutates unit state, making it safe to call
    from AI planning loops without side effects.
    """

    # Delay constants (ticks) — CC2 authentic pacing
    OFFENSIVE_WAVERING_DELAY: int = 3
    MOVEMENT_FATIGUE_DELAY: int = 5

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def evaluate_order(unit: Unit, tactic_type: TacticType) -> OrderAcceptance:
        """Evaluate whether *unit* will accept *tactic_type*.

        Evaluation proceeds in 6 short-circuit steps (see §5.6.2):
          1. Alive check         — dead units refuse everything
          2. Survival shortcut   — RETREAT/TAKE_COVER/SURRENDER/RALLY_NCO
          3. Morale state        — BROKEN/ROUTING refuse by category
          4. Suppression effect  — HEAVY/PINNED/PANIC refuse by category
          5. Fatigue level       — EXHAUSTED/SPENT delay or refuse
          6. Default accept

        Args:
            unit: The unit whose psychological state is evaluated.
            tactic_type: The order being considered.

        Returns:
            OrderAcceptance with accepted/reason/delay_ticks.

        """
        # Step 1: alive check
        if not unit.is_alive:
            return OrderAcceptance.reject(OrderRejectionReason.BROKEN)

        # Step 2: survival commands — always accepted
        if tactic_type in _SURVIVAL_COMMANDS:
            return OrderAcceptance.accept()

        # Read psychological state once (defensive against missing components)
        morale_state = PsychologySystem._morale_state(unit)
        suppression_effect = PsychologySystem._suppression_effect(unit)
        fatigue_level = PsychologySystem._fatigue_level(unit)

        # Step 3: morale gate — BROKEN/ROUTING refuse everything except
        # survival commands (already handled in Step 2).
        if morale_state == MoraleState.ROUTING:
            return OrderAcceptance.reject(OrderRejectionReason.ROUTING)
        if morale_state == MoraleState.BROKEN:
            return OrderAcceptance.reject(OrderRejectionReason.BROKEN)

        # Step 4-5: category-specific evaluation
        if tactic_type in _OFFENSIVE_COMMANDS:
            return PsychologySystem._evaluate_offensive(
                morale_state, suppression_effect, fatigue_level
            )

        if tactic_type in _MOVEMENT_COMMANDS:
            return PsychologySystem._evaluate_movement(suppression_effect, fatigue_level)

        if tactic_type in _DEFENSIVE_COMMANDS:
            return PsychologySystem._evaluate_defensive(suppression_effect)

        # Step 6: default — non-categorized commands (IDLE, HEAL_WOUNDED,
        # SCAVENGE_AMMO, DEPLOY_SMOKE, etc.) are always accepted.
        return OrderAcceptance.accept()

    # ------------------------------------------------------------------
    # Category-specific evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_offensive(
        morale_state: MoraleState,
        suppression_effect: SuppressionEffect,
        fatigue_level: FatigueLevel,
    ) -> OrderAcceptance:
        """Offensive orders: strictest criteria.

        - WAVERING morale → delay 3 ticks
        - HEAVY/PINNED/PANIC suppression → refuse
        - EXHAUSTED/SPENT fatigue → refuse
        """
        # WAVERING delays offense (morale动摇, needs time to steady)
        if morale_state == MoraleState.WAVERING:
            return OrderAcceptance.delay(
                OrderRejectionReason.OK, PsychologySystem.OFFENSIVE_WAVERING_DELAY
            )

        # Suppression refusals — map each effect to its specific reason
        supp_reason = _suppression_rejection(suppression_effect)
        if supp_reason is not None:
            return OrderAcceptance.reject(supp_reason)

        # Fatigue refusals
        if fatigue_level in _OFFENSE_BLOCKING_FATIGUE:
            return OrderAcceptance.reject(
                OrderRejectionReason.SPENT
                if fatigue_level == FatigueLevel.SPENT
                else OrderRejectionReason.EXHAUSTED
            )

        return OrderAcceptance.accept()

    @staticmethod
    def _evaluate_movement(
        suppression_effect: SuppressionEffect,
        fatigue_level: FatigueLevel,
    ) -> OrderAcceptance:
        """Movement orders: moderate criteria.

        - HEAVY/PINNED/PANIC suppression → refuse
        - EXHAUSTED/SPENT fatigue → delay 5 ticks
        """
        supp_reason = _suppression_rejection(suppression_effect)
        if supp_reason is not None:
            return OrderAcceptance.reject(supp_reason)

        if fatigue_level in _MOVE_IMPEDING_FATIGUE:
            return OrderAcceptance.delay(
                OrderRejectionReason.SPENT
                if fatigue_level == FatigueLevel.SPENT
                else OrderRejectionReason.EXHAUSTED,
                PsychologySystem.MOVEMENT_FATIGUE_DELAY,
            )

        return OrderAcceptance.accept()

    @staticmethod
    def _evaluate_defensive(suppression_effect: SuppressionEffect) -> OrderAcceptance:
        """Defensive orders: lenient criteria.

        Only PANIC suppression refuses (hunkering down is still possible
        under HEAVY fire). ROUTING morale was already handled in Step 3.
        """
        if suppression_effect == SuppressionEffect.PANIC:
            return OrderAcceptance.reject(OrderRejectionReason.PANIC)

        return OrderAcceptance.accept()

    # ------------------------------------------------------------------
    # Component accessors — defensive against missing optional components
    # ------------------------------------------------------------------

    @staticmethod
    def _morale_state(unit: Unit) -> MoraleState:
        """Read the unit's MoraleComponent.state safely.

        Returns MoraleState.RALLIED when morale is absent (treated as
        full combat effectiveness — e.g. vehicles without morale).
        """
        morale = getattr(unit, "morale", None)
        if morale is None:
            return MoraleState.RALLIED
        return morale.state

    @staticmethod
    def _suppression_effect(unit: Unit) -> SuppressionEffect:
        """Read the unit's current SuppressionEffect safely.

        Returns SuppressionEffect.NONE when the unit has no
        suppression_state attribute (not all units track suppression).
        """
        supp_state = getattr(unit, "suppression_state", None)
        if supp_state is None:
            return SuppressionEffect.NONE
        get_effect = getattr(supp_state, "get_current_effect", None)
        if get_effect is None:
            return SuppressionEffect.NONE
        return get_effect()

    @staticmethod
    def _fatigue_level(unit: Unit) -> FatigueLevel:
        """Read the unit's FatigueComponent.level safely.

        Returns FatigueLevel.FRESH when the unit has no fatigue
        component (e.g. vehicles, fresh spawns).
        """
        fatigue = getattr(unit, "fatigue", None)
        if fatigue is None:
            return FatigueLevel.FRESH
        return fatigue.level


# ========================================================================
# Helper — map suppression effect to rejection reason (None = no rejection)
# ========================================================================


_SUPPRESSION_REJECTION_MAP: dict[SuppressionEffect, OrderRejectionReason] = {
    SuppressionEffect.HEAVY: OrderRejectionReason.SUPPRESSED,
    SuppressionEffect.PINNED: OrderRejectionReason.PINNED,
    SuppressionEffect.PANIC: OrderRejectionReason.PANIC,
}


def _suppression_rejection(effect: SuppressionEffect) -> OrderRejectionReason | None:
    """Return the rejection reason for a blocking suppression effect, or None."""
    return _SUPPRESSION_REJECTION_MAP.get(effect)
