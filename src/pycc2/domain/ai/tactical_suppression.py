"""SuppressionAI — Prioritize MG fire on high-threat targets.

CC2 behaviour: MG42 teams lay down suppressive fire on the most
dangerous enemy before infantry assaults.  Suppression is maintained
until friendly infantry are in assault position.

P9 Enhancement: MG42 now continues firing the same target until it
is pinned/panicked, then switches to the next highest-threat target.
Moving enemies are prioritized over stationary ones.

Evaluation heuristic:
  - Higher score when MG units are available and enemies are visible
  - Higher score when high-threat enemies (MG, AT, officer) exist
  - Lower score when no MG units or no enemies in range
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai_types import (
    _HIGH_THREAT_TYPES,
    _INFANTRY_TYPES,
    TacticalAIBase,
    TacticalContext,
    _threat_score,
)
from pycc2.domain.entities.unit import UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


class SuppressionAI(TacticalAIBase):
    """Prioritize MG fire on high-threat targets.

    CC2 behaviour: MG42 teams lay down suppressive fire on the most
    dangerous enemy before infantry assaults.  Suppression is maintained
    until friendly infantry are in assault position.

    P9 Enhancement: MG42 now continues firing the same target until it
    is pinned/panicked, then switches to the next highest-threat target.
    Moving enemies are prioritized over stationary ones.

    Evaluation heuristic:
      - Higher score when MG units are available and enemies are visible
      - Higher score when high-threat enemies (MG, AT, officer) exist
      - Lower score when no MG units or no enemies in range
    """

    def evaluate(self, context: TacticalContext) -> float:
        """Return suppression priority based on MG availability and high-threat enemies."""
        mg_units = self._mg_units(context)
        enemies = [e for e in context.enemy_units if e.is_alive]
        if not mg_units or not enemies:
            return 0.0

        high_threat_count = sum(1 for e in enemies if e.unit_type in _HIGH_THREAT_TYPES)
        threat_ratio = min(high_threat_count / max(len(enemies), 1), 1.0)
        mg_ratio = min(len(mg_units) / 2.0, 1.0)

        diff_mod = 1.0
        if context.difficulty_config is not None:
            if not context.difficulty_config.use_suppression_tactics:
                return 0.0
            diff_mod = context.difficulty_config.suppress_effectiveness

        score = 0.5 * threat_ratio + 0.3 * mg_ratio + 0.2 * 0.6
        return min(score * diff_mod, 1.0)

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Generate suppress-fire intents assigning MG units to high-threat enemies."""
        mg_units = self._mg_units(context)
        enemies = [e for e in context.enemy_units if e.is_alive]
        if not mg_units or not enemies:
            return []

        # Rank enemies by threat, with moving enemies getting a bonus
        centroid = TileCoord(
            sum(u.position.tile_coord.x for u in mg_units) // max(len(mg_units), 1),
            sum(u.position.tile_coord.y for u in mg_units) // max(len(mg_units), 1),
        )
        ranked = sorted(
            enemies,
            key=lambda e: self._suppression_target_score(e, centroid, context),
            reverse=True,
        )

        intents: list[TacticIntent] = []

        # Assign each MG to the highest-threat target not already suppressed
        assigned_targets: set[str] = set()
        for mg in mg_units:
            target = self._pick_target(mg, ranked, assigned_targets, context)
            if target is None:
                continue
            assigned_targets.add(target.id)

            # Check if we should continue suppressing this target or switch
            if not self._should_continue_suppression(mg, target, context):
                # Target is already pinned/panicked — find next unpinned target
                alt = self._find_next_unsuppressed(mg, ranked, assigned_targets, context)
                if alt is not None:
                    target = alt
                    assigned_targets.add(target.id)

            # Check if friendly infantry is advancing toward this target
            infantry_advancing = self._infantry_advancing_on(target, context.friendly_units)

            if infantry_advancing:
                # Maintain suppression while infantry closes
                intents.append(
                    TacticIntent(
                        unit_id=mg.id,
                        tactic_type=TacticType.SUPPRESS_FIRE,
                        priority=9,
                        target_unit_id=target.id,
                        target_position=target.position.tile_coord,
                    )
                )
            else:
                # Suppress first, then signal readiness
                intents.append(
                    TacticIntent(
                        unit_id=mg.id,
                        tactic_type=TacticType.SUPPRESS_FIRE,
                        priority=7,
                        target_unit_id=target.id,
                        target_position=target.position.tile_coord,
                    )
                )

        return intents

    # -- helpers --

    @staticmethod
    def _mg_units(context: TacticalContext) -> list[Unit]:
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.unit_type == UnitType.MACHINE_GUN_SQUAD
            and u.morale.is_combat_effective
        ]

    @staticmethod
    def _pick_target(
        mg: Unit,
        ranked_enemies: list[Unit],
        already_assigned: set[str],
        context: TacticalContext,
    ) -> Unit | None:
        for e in ranked_enemies:
            if e.id in already_assigned:
                continue
            dist = mg.position.tile_coord.chebyshev_distance(e.position.tile_coord)
            if dist <= 12:
                return e
        return ranked_enemies[0] if ranked_enemies else None

    @staticmethod
    def _infantry_advancing_on(target: Unit, friendlies: list[Unit]) -> bool:
        target_pos = target.position.tile_coord
        advancing = 0
        for u in friendlies:
            if u.unit_type not in _INFANTRY_TYPES:
                continue
            if not u.is_alive or not u.can_act:
                continue
            dist = u.position.tile_coord.chebyshev_distance(target_pos)
            if dist <= 8:
                advancing += 1
        return advancing >= 1

    @staticmethod
    def _should_continue_suppression(
        mg: Unit,
        target: Unit,
        context: TacticalContext,
    ) -> bool:
        """MG42 should continue firing until the target is pinned/panicked.

        Returns False (switch targets) when:
          - Target morale is already PANICKED or ROUTING
          - Target is already pinned (suppression at max)
          - A higher-priority moving enemy exists
        """
        # Check if target is already neutralized
        morale_val = getattr(target.morale, "value", 100)
        if morale_val < 15:
            return False  # Target is panicked/routing

        # Check if target is pinned via suppression state
        suppression = getattr(target, "suppression_state", None)
        if suppression is not None:
            is_pinned = getattr(suppression, "is_pinned", False)
            if is_pinned:
                return False  # Target already pinned

        # Check for higher-priority moving enemies
        moving_enemies = [
            e
            for e in context.enemy_units
            if e.is_alive and e.id != target.id and SuppressionAI._is_moving(e, context)
        ]
        if moving_enemies:
            # Moving enemies are higher priority — switch if current target isn't moving
            if not SuppressionAI._is_moving(target, context):
                return False

        return True  # Continue suppressing current target

    @staticmethod
    def _is_moving(unit: Unit, context: TacticalContext) -> bool:
        """Determine if a unit is currently moving.

        Checks the unit's blackboard for movement state, or infers
        from position change between ticks.
        """
        bb = context.blackboards.get(unit.id)
        if bb is not None:
            return bool(bb.get("is_moving", False))
        # Fallback: check if unit has a pending move order
        return getattr(unit, "_is_moving", False)

    @staticmethod
    def _suppression_target_score(
        enemy: Unit,
        reference_pos: TileCoord,
        context: TacticalContext,
    ) -> float:
        """Score an enemy for suppression targeting.

        Moving enemies get a 1.5x bonus (they're more dangerous when mobile).
        High-threat types get their standard weight.
        """
        base = _threat_score(enemy, reference_pos)
        if SuppressionAI._is_moving(enemy, context):
            base *= 1.5
        return base

    @staticmethod
    def _find_next_unsuppressed(
        mg: Unit,
        ranked_enemies: list[Unit],
        already_assigned: set[str],
        context: TacticalContext,
    ) -> Unit | None:
        """Find the next enemy that isn't already pinned/suppressed."""
        for e in ranked_enemies:
            if e.id in already_assigned:
                continue
            morale_val = getattr(e.morale, "value", 100)
            if morale_val < 15:
                continue  # Already panicked
            suppression = getattr(e, "suppression_state", None)
            if suppression is not None and getattr(suppression, "is_pinned", False):
                continue  # Already pinned
            dist = mg.position.tile_coord.chebyshev_distance(e.position.tile_coord)
            if dist <= 12:
                return e
        return None
