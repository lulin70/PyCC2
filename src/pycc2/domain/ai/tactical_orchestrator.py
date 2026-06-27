"""TacticalOrchestrator — Runs all tactical AIs each tick, resolves conflicts,
and issues final orders.

Conflict resolution rule: when two AIs want the same unit, the one
with the higher ``score * intent.priority`` product wins.  This
ensures that both the AI's situational relevance and the order's
intrinsic urgency are considered.

Usage::

    orchestrator = TacticalOrchestrator()
    orchestrator.register(FlankingAI())
    orchestrator.register(SuppressionAI())
    orchestrator.register(InfantryTankCoordAI())
    orchestrator.register(VictoryPointAI())

    context = TacticalContext(...)
    orders = orchestrator.tick(context)
    # orders is a list[TacticIntent] ready for TacticExecutor
"""

from __future__ import annotations

from dataclasses import dataclass

from pycc2.domain.ai.tactic_intent import TacticIntent
from pycc2.domain.ai.tactical_ai_types import PrioritizedIntent, TacticalAIBase, TacticalContext


@dataclass(slots=True)
class _UnitAssignment:
    """Tracks which AI has claimed a unit and at what priority."""

    unit_id: str
    ai_name: str
    score: float
    intent: TacticIntent


class TacticalOrchestrator:
    """Runs all tactical AIs each tick, resolves conflicts, and issues
    final orders.

    Conflict resolution rule: when two AIs want the same unit, the one
    with the higher ``score * intent.priority`` product wins.  This
    ensures that both the AI's situational relevance and the order's
    intrinsic urgency are considered.

    Usage::

        orchestrator = TacticalOrchestrator()
        orchestrator.register(FlankingAI())
        orchestrator.register(SuppressionAI())
        orchestrator.register(InfantryTankCoordAI())
        orchestrator.register(VictoryPointAI())

        context = TacticalContext(...)
        orders = orchestrator.tick(context)
        # orders is a list[TacticIntent] ready for TacticExecutor
    """

    def __init__(self) -> None:
        self._ais: list[TacticalAIBase] = []
        self._last_scores: dict[str, float] = {}
        self._last_orders: list[TacticIntent] = []

    def register(self, ai: TacticalAIBase) -> None:
        self._ais.append(ai)

    @property
    def registered_ais(self) -> list[str]:
        return [type(ai).__name__ for ai in self._ais]

    @property
    def last_scores(self) -> dict[str, float]:
        return dict(self._last_scores)

    @property
    def last_orders(self) -> list[TacticIntent]:
        return list(self._last_orders)

    def tick(self, context: TacticalContext) -> list[TacticIntent]:
        """Run all AIs, resolve conflicts, return final orders."""
        # Phase 1: Evaluate all AIs
        scores: dict[str, float] = {}
        for ai in self._ais:
            name = type(ai).__name__
            scores[name] = ai.evaluate(context)
        self._last_scores = scores

        # Phase 2: Collect intents from AIs above threshold
        all_prioritized: list[PrioritizedIntent] = []
        for ai in self._ais:
            name = type(ai).__name__
            score = scores[name]
            if score < 0.1:
                continue
            intents = ai.execute(context)
            for intent in intents:
                all_prioritized.append(PrioritizedIntent(intent=intent, ai_name=name, score=score))

        # Phase 3: Resolve conflicts — each unit assigned to at most one AI
        assignments: dict[str, _UnitAssignment] = {}
        for pi in all_prioritized:
            uid = pi.intent.unit_id
            combined = pi.score * (pi.intent.priority / 10.0)
            existing = assignments.get(uid)
            if existing is None or combined > existing.score:
                assignments[uid] = _UnitAssignment(
                    unit_id=uid,
                    ai_name=pi.ai_name,
                    score=combined,
                    intent=pi.intent,
                )

        # Phase 4: Build final order list sorted by priority
        final: list[TacticIntent] = [
            a.intent for a in sorted(assignments.values(), key=lambda a: -a.score)
        ]
        self._last_orders = final
        return final
