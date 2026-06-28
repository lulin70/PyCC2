"""Morale Effects — extracted from morale_system.py (P5-1 batch 2).

Side-effecting morale operations that mutate unit state:
  - apply_suppression: apply incoming fire suppression to morale
  - update_morale_recovery: passive morale recovery when not under fire
  - apply_panic_contagion: spread panic to nearby friendly units
  - apply_nco_rally: NCO/commander rally bonus to nearby units

All methods are static and operate on Unit instances passed in by the caller.
Depends on morale_types (constants + state resolver) and morale_routing
(voice callback on collapse).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pycc2.domain.systems.morale_routing import MoraleRouting
from pycc2.domain.systems.morale_types import (
    BASE_RECOVERY_RATE,
    COMMANDER_BONUS_MULTIPLIER,
    COVER_BONUS,
    PINNED_THRESHOLD,
    SUPPRESSION_TO_MORALE_RATIO,
    MoraleState,
    resolve_morale_state,
)

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

logger = logging.getLogger(__name__)


class MoraleEffects:
    """Static utility class for morale side-effect operations."""

    @staticmethod
    def apply_suppression(unit: Unit, amount: float, dt: float) -> dict:
        """Apply enemy fire suppression to unit's morale.

        Suppression from incoming fire reduces morale over time.
        Heavy suppression can push units into pinned/broken states.

        Args:
            unit: Target unit
            amount: Suppression points to apply
            dt: Delta time in seconds

        Returns:
            Dict with effects applied:
            - morale_delta: Change in morale value
            - state_changed: Whether state changed
            - new_state: New morale state (if changed)
            - current_morale: Updated morale value

        """
        if unit.morale is None:
            return {
                "morale_delta": 0,
                "state_changed": False,
                "new_state": None,
                "current_morale": 0,
            }

        old_state = resolve_morale_state(unit.morale.value)

        # Calculate morale reduction from suppression
        # Scale by delta time for frame-rate independence
        morale_reduction = int(amount * SUPPRESSION_TO_MORALE_RATIO * dt * 60)

        # Apply to morale component
        unit.morale.apply_delta(-morale_reduction)

        # Also add to suppression tracker if available
        if unit.morale is not None and hasattr(unit.morale, "add_suppression"):
            suppr_amount = int(amount * dt * 60)
            unit.morale.add_suppression(suppr_amount)

        new_state = resolve_morale_state(unit.morale.value)
        state_changed = old_state != new_state

        result = {
            "morale_delta": -morale_reduction,
            "state_changed": state_changed,
            "new_state": new_state if state_changed else None,
            "current_morale": unit.morale.value,
        }

        # Log significant state changes
        if state_changed:
            logger.warning(
                f"[MORALE] {unit.name or unit.id} state change: "
                f"{old_state.value} -> {new_state.value} "
                f"(morale={unit.morale.value})"
            )

            # Trigger morale collapse voice when entering BROKEN/ROUTING
            if new_state in (MoraleState.BROKEN, MoraleState.ROUTING):
                MoraleRouting.play_morale_collapse_voice(unit, new_state)

        return result

    @staticmethod
    def update_morale_recovery(
        unit: Unit, dt: float, near_commander: bool = False, in_cover: bool = True
    ) -> dict:
        """Passive morale recovery when not under fire.

        Units naturally recover morale over time, faster when:
        - Near commander (leadership bonus)
        - In good cover (safety feeling)
        - Not recently taking damage

        Args:
            unit: Unit to recover
            dt: Delta time in seconds
            near_commander: Whether commander is nearby
            in_cover: Whether unit is in good cover

        Returns:
            Dict with recovery info:
            - recovered: Amount recovered
            - current_morale: Updated morale
            - state_changed: Whether state improved

        """
        if unit.morale is None:
            return {"recovered": 0, "current_morale": 0, "state_changed": False}

        # Don't recover if currently routing or broken below threshold
        current_state = resolve_morale_state(unit.morale.value)
        if current_state in (MoraleState.ROUTING, MoraleState.BROKEN):
            if unit.morale.value < PINNED_THRESHOLD:
                return {"recovered": 0, "current_morale": unit.morale.value, "state_changed": False}

        old_state = current_state

        # Calculate base recovery
        recovery = BASE_RECOVERY_RATE * dt

        # Apply bonuses
        if near_commander:
            recovery *= COMMANDER_BONUS_MULTIPLIER

        if in_cover:
            recovery += COVER_BONUS * dt

        # Faster recovery from low suppression
        if hasattr(unit.morale, "suppression") and unit.morale.suppression == 0:
            recovery *= 1.5  # Bonus when fully recovered from suppression

        # Apply recovery (use natural_recovery if available for fractional tracking)
        if hasattr(unit.morale, "natural_recovery"):
            unit.morale.natural_recovery()
            recovered_int = 1 if recovery >= 1.0 else 0
        else:
            recovered_int = int(recovery)
            if recovered_int > 0:
                unit.morale.apply_delta(recovered_int)

        # Decay suppression
        if hasattr(unit.morale, "decay_suppression"):
            decay_amount = int(5 * dt * 60)  # 5 points per second at 60 FPS
            unit.morale.decay_suppression(decay_amount)

        new_state = resolve_morale_state(unit.morale.value)

        return {
            "recovered": recovered_int,
            "current_morale": unit.morale.value,
            "state_changed": old_state != new_state and new_state.value > old_state.value,
        }

    @staticmethod
    def apply_panic_contagion(unit: Unit, all_units: list[Unit]) -> None:
        """Apply morale penalty to nearby friendly units when this unit breaks.

        When a squad member enters BROKEN or ROUTING state, nearby friendly
        units (within 10 tiles) suffer a morale penalty of -5.
        """
        if unit.morale is None:
            return

        # Only apply if this unit is in BROKEN or ROUTING state
        state = resolve_morale_state(unit.morale.value)
        if state not in (MoraleState.BROKEN, MoraleState.ROUTING):
            return

        ux = unit.position.tile_coord.x
        uy = unit.position.tile_coord.y

        for other in all_units:
            if other.id == unit.id:
                continue
            if other.faction != unit.faction:
                continue
            if other.morale is None:
                continue

            ox = other.position.tile_coord.x
            oy = other.position.tile_coord.y
            dist = ((ux - ox) ** 2 + (uy - oy) ** 2) ** 0.5

            if dist <= 10:  # Within 10 tiles
                other.morale.apply_delta(-5)

    @staticmethod
    def apply_nco_rally(all_units: list[Unit]) -> None:
        """Apply NCO rally bonus to nearby friendly units.

        When a COMMANDER or officer-type unit is within 5 tiles of a
        broken/wavering unit, that unit gets +15 morale per tick.
        """
        from pycc2.domain.entities.unit import UnitType

        # Find all NCO/commander units
        ncos = [
            u
            for u in all_units
            if u.is_alive and u.unit_type == UnitType.COMMANDER and u.morale is not None
        ]

        for nco in ncos:
            nx = nco.position.tile_coord.x
            ny = nco.position.tile_coord.y

            for unit in all_units:
                if unit.id == nco.id:
                    continue
                if unit.faction != nco.faction:
                    continue
                if not unit.is_alive:
                    continue
                if unit.morale is None:
                    continue

                ux = unit.position.tile_coord.x
                uy = unit.position.tile_coord.y
                dist = ((nx - ux) ** 2 + (ny - uy) ** 2) ** 0.5

                if dist <= 5:  # Within 5 tiles
                    state = resolve_morale_state(unit.morale.value)
                    if state in (MoraleState.WAVERING, MoraleState.BROKEN):
                        unit.morale.apply_delta(15)


__all__ = ["MoraleEffects"]
