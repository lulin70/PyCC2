"""Morale Calculator — extracted from morale_system.py (P5-1 batch 2).

Pure event-driven morale calculator with configurable weights. Calculates
morale changes from discrete events (ally killed, leader killed, etc.) and
provides panic contagion / natural recovery helpers.

This module contains pure calculation logic with no IO or unit-state side
effects (the MoraleComponent is read but not mutated beyond what the caller
passes in).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pycc2.domain.systems.morale_types import (
    MoraleCalculationResult,
    MoraleEvent,
)

if TYPE_CHECKING:
    from pycc2.domain.ai.squad_degradation import SquadDegradationManager
    from pycc2.domain.components.morale_component import MoraleComponent
    from pycc2.domain.entities.unit import Unit


@dataclass
class MoraleCalculator:
    """Event-driven morale calculator with configurable weights.

    Calculates morale changes from discrete events (ally killed, leader
    killed, etc.) and provides panic contagion / natural recovery helpers.
    """

    EVENT_WEIGHTS: dict[MoraleEvent, int] = field(
        default_factory=lambda: {
            MoraleEvent.ALLY_KILLED: -15,
            MoraleEvent.LEADER_KILLED: -25,
            MoraleEvent.UNDER_HEAVY_FIRE: -5,
            MoraleEvent.NEAR_EXPLOSION: -20,
            MoraleEvent.KILL_CONFIRMED: 8,
            MoraleEvent.RALLY: 3,
            MoraleEvent.IN_COVER: 5,
            MoraleEvent.COMMANDER_NEARBY: 10,
            MoraleEvent.PANIC_CONTAGION: -10,
        }
    )
    degradation_manager: SquadDegradationManager | None = field(default=None)

    def calculate_event_effect(
        self,
        unit_morale: MoraleComponent,
        event: MoraleEvent,
        context: dict | None = None,
    ) -> MoraleCalculationResult:
        """Compute the morale effect of a discrete event on a unit."""
        delta = self.EVENT_WEIGHTS.get(event, 0)
        old_value = unit_morale.value
        new_value = max(0, min(100, old_value + delta))
        old_state_name = unit_morale.state.name
        new_state_name = self.predict_state(new_value, 0)
        state_changed = old_state_name != new_state_name
        contagion_targets: list[str] = []
        if new_state_name in ("BROKEN", "ROUTING") and state_changed:
            contagion_targets = (context or {}).get("contagion_targets", [])
        return MoraleCalculationResult(
            morale_delta=delta,
            suppression_delta=0,
            state_changed=state_changed,
            old_state=old_state_name if state_changed else None,
            new_state=new_state_name if state_changed else None,
            contagion_targets=contagion_targets,
        )

    def calculate_natural_recovery(self, current_value: int, ticks_since_combat: int) -> int:
        """Return the morale value after passive recovery when out of combat."""
        if ticks_since_combat >= 30:
            return min(100, current_value + 5)
        return current_value

    def calculate_panic_contagion(
        self,
        squad_units: list[tuple[str, MoraleComponent]],
        panicked_unit_id: str,
    ) -> dict[str, int]:
        """Return per-unit morale deltas for panic contagion within a squad."""
        result: dict[str, int] = {}
        for unit_id, mc in squad_units:
            if unit_id == panicked_unit_id:
                continue
            if mc.state.name in ("BROKEN", "ROUTING"):
                continue
            result[unit_id] = -10
        return result

    def should_panic_contagion(self, unit: MoraleComponent) -> bool:
        """Return True if the unit's morale state can trigger panic contagion."""
        return unit.state.name in ("BROKEN", "ROUTING")

    def notify_leader_killed(self, killed_unit: Unit, squad_units: list[Unit]) -> None:
        """Forward a leader-killed event to the squad degradation manager."""
        if self.degradation_manager is not None:
            self.degradation_manager.on_leader_killed(killed_unit, squad_units)

    @staticmethod
    def predict_state(
        current_value: int,
        delta: int,
    ) -> str:
        """Predict the morale state name resulting from applying a delta."""
        new_val = max(0, min(100, current_value + delta))
        if new_val > 70:
            return "RALLIED"
        elif new_val > 40:
            return "WAVERING"
        elif new_val > 20:
            return "PINNED"
        else:
            return "BROKEN"


__all__ = ["MoraleCalculator"]
