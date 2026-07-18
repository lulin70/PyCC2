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

import logging
from dataclasses import dataclass

from pycc2.domain.ai.cover_seek_ai import CoverScoringSystem, CoverSeekAI
from pycc2.domain.ai.tactic_intent import TacticIntent
from pycc2.domain.ai.tactical_ai_types import PrioritizedIntent, TacticalAIBase, TacticalContext
from pycc2.domain.systems.psychology_system import PsychologySystem

logger = logging.getLogger(__name__)


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
        """Initialize the orchestrator with no registered AIs and empty order history."""
        self._ais: list[TacticalAIBase] = []
        self._last_scores: dict[str, float] = {}
        self._last_orders: list[TacticIntent] = []

    def register(self, ai: TacticalAIBase) -> None:
        """Register a tactical AI subsystem to participate in orchestration."""
        self._ais.append(ai)

    @property
    def registered_ais(self) -> list[str]:
        """Return the class names of all registered AI subsystems."""
        return [type(ai).__name__ for ai in self._ais]

    @property
    def last_scores(self) -> dict[str, float]:
        """Return a copy of the most recent evaluation scores per AI."""
        return dict(self._last_scores)

    @property
    def last_orders(self) -> list[TacticIntent]:
        """Return a copy of the orders produced by the most recent tick."""
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

        # Phase 5: Psychology evaluation — filter orders by unit psychological state (v0.7.5)
        final = self._evaluate_psychology(final, context)

        # Phase 6: Cover seeking — suppressed units without orders auto-seek cover (v0.7.6)
        final = self._seek_cover(final, context)

        self._last_orders = final
        return final

    def _evaluate_psychology(
        self, intents: list[TacticIntent], context: TacticalContext
    ) -> list[TacticIntent]:
        """Filter orders by unit psychological state (v0.7.5 INTEGRATE).

        Uses PsychologySystem.evaluate_order() to check whether each unit
        will accept, delay, or refuse the order based on morale, suppression,
        and fatigue. Rejected orders are filtered out; delayed orders are kept
        (the delay_ticks field is preserved for the executor).
        """
        filtered: list[TacticIntent] = []
        for intent in intents:
            unit = next((u for u in context.friendly_units if u.id == intent.unit_id), None)
            if unit is None:
                # Unit not found in friendly_units — preserve the order
                filtered.append(intent)
                continue
            acceptance = PsychologySystem.evaluate_order(unit, intent.tactic_type)
            if acceptance.accepted:
                filtered.append(intent)
            else:
                logger.debug(
                    "Order rejected: unit=%s tactic=%s reason=%s",
                    intent.unit_id,
                    intent.tactic_type,
                    acceptance.reason,
                )
        return filtered

    def _seek_cover(
        self, intents: list[TacticIntent], context: TacticalContext
    ) -> list[TacticIntent]:
        """Generate cover-seeking orders for suppressed units without orders (v0.7.6 INTEGRATE).

        Units whose orders were filtered out by Phase 5 (psychology rejected
        their offensive order) but are still under heavy suppression will
        auto-seek cover. Intents are only generated for units not already
        present in ``intents`` to avoid overriding Phase 1-5 decisions.

        Uses ``CoverSeekAI.execute(context)`` which internally checks each
        friendly unit's suppression state via ``CoverSeekAI._evaluate_unit``
        and generates ``TacticType.MOVE_TO`` intents targeting the best
        available cover tile.
        """
        scorer = CoverScoringSystem(game_map=context.game_map)
        cover_ai = CoverSeekAI(scoring_system=scorer)
        cover_intents = cover_ai.execute(context)
        if not cover_intents:
            return intents

        result = list(intents)
        existing_unit_ids = {intent.unit_id for intent in result}
        for cover_intent in cover_intents:
            if cover_intent.unit_id not in existing_unit_ids:
                result.append(cover_intent)
                existing_unit_ids.add(cover_intent.unit_id)
        return result
