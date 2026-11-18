"""TriggerSystem — registry of condition/action triggers ticked per frame (MC2-02).

Consolidates scenario-rule effects that previously lived as inline blocks in
the game-loop update methods. Each :class:`Trigger` pairs a boolean condition
with an action; :meth:`TriggerSystem.tick` evaluates registered triggers in
registration order, honoring ``once`` and ``cooldown_ticks`` gates, and
returns the ids of the triggers that fired this tick for observability.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Trigger:
    """One declarative trigger: condition met → action runs.

    ``once`` fires the trigger at most once; ``cooldown_ticks`` suppresses
    re-firing for that many ticks after a fire (0 = fire every time the
    condition holds). ``group`` lets callers tick disjoint trigger sets
    (e.g. logistics vs scenario effects) independently.
    """

    trigger_id: str
    condition: Callable[[Any], bool]
    action: Callable[[Any], None]
    once: bool = False
    cooldown_ticks: int = 0
    group: str = "default"


@dataclass
class TriggerSystem:
    """Evaluates registered triggers each tick; per-trigger stats are observable."""

    _triggers: list[Trigger] = field(default_factory=list)
    _fire_counts: dict[str, int] = field(default_factory=dict)
    _last_fire_ticks: dict[str, int] = field(default_factory=dict)
    _tick: int = 0

    def register(self, trigger: Trigger) -> None:
        """Append a trigger to the registry (registration order = execution order)."""
        self._triggers.append(trigger)

    def tick(self, state: Any, group: str | None = None) -> list[str]:
        """Evaluate triggers for one frame; return the ids that fired.

        ``group`` restricts evaluation to triggers registered in that group
        (``None`` evaluates every trigger).
        """
        self._tick += 1
        fired: list[str] = []
        for trigger in self._triggers:
            if group is not None and trigger.group != group:
                continue
            if trigger.once and self._fire_counts.get(trigger.trigger_id, 0) > 0:
                continue
            last_fire = self._last_fire_ticks.get(trigger.trigger_id)
            if (
                trigger.cooldown_ticks > 0
                and last_fire is not None
                and self._tick - last_fire < trigger.cooldown_ticks
            ):
                continue
            if not trigger.condition(state):
                continue
            trigger.action(state)
            self._fire_counts[trigger.trigger_id] = self._fire_counts.get(trigger.trigger_id, 0) + 1
            self._last_fire_ticks[trigger.trigger_id] = self._tick
            fired.append(trigger.trigger_id)
        return fired

    def list_triggers(self) -> list[tuple[str, int, int | None]]:
        """Return ``(trigger_id, fire_count, last_fire_tick)`` per registered trigger."""
        return [
            (
                trigger.trigger_id,
                self._fire_counts.get(trigger.trigger_id, 0),
                self._last_fire_ticks.get(trigger.trigger_id),
            )
            for trigger in self._triggers
        ]
