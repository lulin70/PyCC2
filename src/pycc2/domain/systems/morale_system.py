"""Morale System — CC2-Authentic State Machine (facade, P5-1 batch 2).

Thin facade re-exporting types and delegating behavior to focused sub-modules:
  - morale_types.py: enums + dataclasses + threshold constants + resolve_morale_state()
  - morale_calculator.py: MoraleCalculator (pure event-driven calculation)
  - morale_effects.py: MoraleEffects (suppression / recovery / contagion / rally)
  - morale_routing.py: MoraleRouting (routing / flee / voice collapse)

Public API (100% backward-compatible):
  - MoraleEvent, MoraleState, RoutingTarget, MoraleCalculationResult (types)
  - MoraleCalculator (class)
  - MoraleSystem (class with all original static methods + threshold constants)
  - demo_morale_system() (function)
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from pycc2.domain.systems.morale_calculator import MoraleCalculator
from pycc2.domain.systems.morale_effects import MoraleEffects
from pycc2.domain.systems.morale_routing import MoraleRouting
from pycc2.domain.systems.morale_types import (
    BASE_RECOVERY_RATE,
    BROKEN_THRESHOLD,
    COMMANDER_BONUS_MULTIPLIER,
    COVER_BONUS,
    FLEE_CHANCE_BROKEN,
    FLEE_CHANCE_ROUTING,
    PINNED_THRESHOLD,
    RALLYED_THRESHOLD,
    ROUTING_CHECK_INTERVAL,
    ROUTING_FLEE_DURATION,
    SUPPRESSION_TO_MORALE_RATIO,
    WAVERING_THRESHOLD,
    MoraleCalculationResult,
    MoraleEvent,
    MoraleState,
    RoutingTarget,
    resolve_morale_state,
)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Faction, Unit

logger = logging.getLogger(__name__)

__all__ = [
    "MoraleCalculator",
    "MoraleCalculationResult",
    "MoraleEvent",
    "MoraleState",
    "MoraleSystem",
    "RoutingTarget",
    "demo_morale_system",
]


class MoraleSystem:
    """Static utility class for morale state management.

    Provides CC2-authentic morale mechanics including:
    - State mapping from numeric values
    - Suppression application with morale impact
    - Passive recovery when not under fire
    - Routing/flight behavior detection

    Delegates to:
    - resolve_morale_state() for state mapping
    - MoraleEffects for suppression/recovery/contagion/rally
    - MoraleRouting for routing/flee/voice
    """

    # Threshold constants (CC2 authentic) — kept as class attrs for backward compat
    RALLYED_THRESHOLD: int = RALLYED_THRESHOLD
    WAVERING_THRESHOLD: int = WAVERING_THRESHOLD
    PINNED_THRESHOLD: int = PINNED_THRESHOLD
    BROKEN_THRESHOLD: int = BROKEN_THRESHOLD

    # Recovery rates
    BASE_RECOVERY_RATE: float = BASE_RECOVERY_RATE
    COMMANDER_BONUS_MULTIPLIER: float = COMMANDER_BONUS_MULTIPLIER
    COVER_BONUS: float = COVER_BONUS

    # Suppression impact on morale
    SUPPRESSION_TO_MORALE_RATIO: float = SUPPRESSION_TO_MORALE_RATIO

    # Routing behavior
    ROUTING_CHECK_INTERVAL: int = ROUTING_CHECK_INTERVAL
    ROUTING_FLEE_DURATION: int = ROUTING_FLEE_DURATION
    FLEE_CHANCE_BROKEN: float = FLEE_CHANCE_BROKEN
    FLEE_CHANCE_ROUTING: float = FLEE_CHANCE_ROUTING

    @staticmethod
    def get_state(morale_value: int) -> MoraleState:
        """Map numeric morale value to state enum.

        Args:
            morale_value: Current morale (0-100)

        Returns:
            Corresponding MoraleState enum value

        """
        return resolve_morale_state(morale_value)

    @staticmethod
    def _play_morale_collapse_voice(
        unit: Unit,
        new_state: MoraleState,
        voice_callback: Callable[[str, Faction], None] | None = None,
    ) -> None:
        """Play a morale collapse voice cry for the unit's faction.

        Delegates to MoraleRouting.play_morale_collapse_voice.
        Kept for backward compatibility — external callers may reference
        MoraleSystem._play_morale_collapse_voice.
        """
        MoraleRouting.play_morale_collapse_voice(unit, new_state, voice_callback)

    @staticmethod
    def apply_suppression(unit: Unit, amount: float, dt: float) -> dict:
        """Apply enemy fire suppression to unit's morale.

        Delegates to MoraleEffects.apply_suppression.
        """
        return MoraleEffects.apply_suppression(unit, amount, dt)

    @staticmethod
    def update_morale_recovery(
        unit: Unit, dt: float, near_commander: bool = False, in_cover: bool = True
    ) -> dict:
        """Passive morale recovery when not under fire.

        Delegates to MoraleEffects.update_morale_recovery.
        """
        return MoraleEffects.update_morale_recovery(unit, dt, near_commander, in_cover)

    @staticmethod
    def check_routing_behavior(unit: Unit, game_map: GameMap | None = None) -> tuple[bool, object]:
        """Check if unit should attempt to flee.

        Delegates to MoraleRouting.check_routing_behavior.
        """
        return MoraleRouting.check_routing_behavior(unit, game_map)

    @staticmethod
    def _calculate_flee_target(
        unit: Unit, game_map: GameMap | None = None
    ) -> tuple[int, int] | None:
        """Calculate target position for fleeing unit.

        Delegates to MoraleRouting._calculate_flee_target.
        """
        return MoraleRouting._calculate_flee_target(unit, game_map)

    @staticmethod
    def get_accuracy_modifier(morale_state: MoraleState) -> float:
        """Get accuracy modifier based on morale state.

        Args:
            morale_state: Current morale state

        Returns:
            Accuracy multiplier (1.0 = normal, <1.0 = penalty, >1.0 = bonus)

        """
        modifiers = {
            MoraleState.RALLYED: 1.05,  # Slight bonus
            MoraleState.WAVERING: 0.95,  # Slight penalty
            MoraleState.PINNED: 0.60,  # Major penalty (can still fire)
            MoraleState.BROKEN: 0.30,  # Severe penalty
            MoraleState.ROUTING: 0.10,  # Minimal (fleeing)
        }
        return modifiers.get(morale_state, 1.0)

    @staticmethod
    def get_movement_modifier(morale_state: MoraleState) -> float:
        """Get movement speed modifier based on morale state.

        Args:
            morale_state: Current morale state

        Returns:
            Speed multiplier (0.0 = cannot move, 1.5 = fleeing speed)

        """
        modifiers = {
            MoraleState.RALLYED: 1.0,  # Normal
            MoraleState.WAVERING: 0.85,  # Slower response
            MoraleState.PINNED: 0.0,  # Cannot move!
            MoraleState.BROKEN: 0.50,  # Reluctant movement
            MoraleState.ROUTING: 1.5,  # Running away fast
        }
        return modifiers.get(morale_state, 1.0)

    @staticmethod
    def can_move(unit: Unit) -> bool:
        """Check if unit is capable of moving.

        Pinned units cannot move at all.
        Broken units may refuse movement orders.

        Args:
            unit: Unit to check

        Returns:
            True if unit can move, False otherwise

        """
        if unit.morale is None:
            return True  # No morale system = can always move

        current_state = resolve_morale_state(unit.morale.value)

        if current_state == MoraleState.PINNED:
            return False  # Definitely cannot move

        if current_state == MoraleState.BROKEN:
            # 70% chance to refuse orders
            import random

            return random.random() > 0.7

        return True

    @staticmethod
    def can_accept_orders(unit: Unit) -> bool:
        """Check if unit will accept player/AI orders.

        Broken and routing units may ignore commands.
        Routing units are completely uncontrollable regardless of
        their numeric morale value.

        Args:
            unit: Unit to check

        Returns:
            True if unit accepts orders, False if refusing

        """
        if unit.morale is None:
            return True

        # Check component-level routing state first — overrides numeric mapping.
        # A unit in active routing mode (via start_routing()) must refuse orders
        # even when its numeric morale value would map to BROKEN or another state.
        if getattr(unit.morale, "_is_routing", False):
            return False

        current_state = resolve_morale_state(unit.morale.value)

        if current_state == MoraleState.ROUTING:
            return False  # Completely uncontrollable

        if current_state == MoraleState.BROKEN:
            # High chance to refuse
            import random

            return random.random() > 0.6

        return True

    @staticmethod
    def apply_panic_contagion(unit: Unit, all_units: list[Unit]) -> None:
        """Apply morale penalty to nearby friendly units when this unit breaks.

        Delegates to MoraleEffects.apply_panic_contagion.
        """
        MoraleEffects.apply_panic_contagion(unit, all_units)

    @staticmethod
    def apply_nco_rally(all_units: list[Unit]) -> None:
        """Apply NCO rally bonus to nearby friendly units.

        Delegates to MoraleEffects.apply_nco_rally.
        """
        MoraleEffects.apply_nco_rally(all_units)


def demo_morale_system():
    """Demonstrate the morale system functionality."""
    logger.info("=" * 80)
    logger.info("🎖️  MORALE SYSTEM DEMO — CC2 Authentic State Machine")
    logger.info("=" * 80)

    # Test state mapping
    logger.info("📊 State Mapping Tests:")
    test_values = [85, 72, 55, 30, 15]
    for val in test_values:
        state = MoraleSystem.get_state(val)
        acc_mod = MoraleSystem.get_accuracy_modifier(state)
        move_mod = MoraleSystem.get_movement_modifier(state)
        logger.info(
            "   Morale %3d → %-10s | Accuracy: %.2fx | Movement: %.2fx",
            val,
            state.value,
            acc_mod,
            move_mod,
        )

    logger.info("✅ Morale System Ready for Integration!")


if __name__ == "__main__":
    demo_morale_system()
