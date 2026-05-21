from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.ai.squad_degradation import SquadDegradationManager
    from pycc2.domain.components.morale_component import MoraleComponent
    from pycc2.domain.entities.unit import Unit


class MoraleEvent(Enum):
    ALLY_KILLED = auto()
    LEADER_KILLED = auto()
    UNDER_HEAVY_FIRE = auto()
    NEAR_EXPLOSION = auto()
    KILL_CONFIRMED = auto()
    RALLY = auto()
    IN_COVER = auto()
    COMMANDER_NEARBY = auto()
    PANIC_CONTAGION = auto()


@dataclass(slots=True)
class MoraleCalculationResult:
    morale_delta: int
    suppression_delta: int
    state_changed: bool
    old_state: str | None
    new_state: str | None
    contagion_targets: list[str] = field(default_factory=list)


@dataclass
class MoraleCalculator:
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
        delta = self.EVENT_WEIGHTS.get(event, 0)
        old_value = unit_morale.value
        new_value = max(0, min(100, old_value + delta))
        old_state_name = unit_morale.state.name
        new_state_name = self.predict_state(
            new_value, 0, unit_morale.panic_threshold, unit_morale.rout_threshold
        )
        state_changed = old_state_name != new_state_name
        contagion_targets: list[str] = []
        if new_state_name == "PANICED" and state_changed:
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
        if ticks_since_combat >= 30:
            return min(100, current_value + 5)
        return current_value

    def calculate_panic_contagion(
        self,
        squad_units: list[tuple[str, MoraleComponent]],
        panicked_unit_id: str,
    ) -> dict[str, int]:
        result: dict[str, int] = {}
        for unit_id, mc in squad_units:
            if unit_id == panicked_unit_id:
                continue
            if mc.state.name in ("PANICED", "ROUTING"):
                continue
            result[unit_id] = -10
        return result

    def should_panic_contagion(self, unit: MoraleComponent) -> bool:
        return unit.state.name == "PANICED"

    def notify_leader_killed(self, killed_unit: Unit, squad_units: list[Unit]) -> None:
        if self.degradation_manager is not None:
            self.degradation_manager.on_leader_killed(killed_unit, squad_units)

    @staticmethod
    def predict_state(
        current_value: int,
        delta: int,
        panic_thr: int = 30,
        rout_thr: int = 10,
    ) -> str:
        new_val = max(0, min(100, current_value + delta))
        if new_val < rout_thr:
            return "ROUTING"
        if new_val < panic_thr:
            return "PANICED"
        return "NORMAL"
