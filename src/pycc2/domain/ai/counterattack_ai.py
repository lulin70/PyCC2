"""CounterattackAI — Strategic Counterattack After Reinforcement

Implements CC2-authentic strategic counterattack behaviour:

  1. Detect when reinforcements have shifted the force ratio in our favour
  2. Select the weakest enemy unit as the primary target
  3. Commit 2-3 fresh (HP > 60%, non-routing) units to a coordinated assault
  4. Route any additional units to flank the enemy position

Evaluation heuristic:
  - Returns 0.0 when outnumbered (force_ratio < 1.0)
  - Base score 0.8 once force_ratio > 1.2 (reinforcements have arrived)
  - +0.1 when the enemy is in an offensive posture (>60% on the front line)
  - +0.1 when friendly average morale > 50
  - Capped at 1.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.components.morale_component import MoraleState

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FORCE_RATIO_THRESHOLD: float = 1.2  # Reinforcements have reversed the balance
_OUTNUMBERED_THRESHOLD: float = 1.0  # Below this → no counterattack
_BASE_SCORE: float = 0.8
_OFFENSIVE_POSTURE_BONUS: float = 0.1
_MORALE_BONUS: float = 0.1
_MORALE_THRESHOLD: int = 50
_OFFENSIVE_POSTURE_RATIO: float = 0.6  # >60% enemies on the front line

# Attacker selection
_ATTACKER_HP_RATIO: float = 0.6  # HP > 60% required to join the assault
_MAX_ATTACKERS: int = 3
_MAX_FLANKERS: int = 2
_COUNTERATTACK_PRIORITY: int = 9
_FLANKING_PRIORITY: int = 7


# ---------------------------------------------------------------------------
# CounterattackAI
# ---------------------------------------------------------------------------


class CounterattackAI(TacticalAIBase):
    """Strategic counterattack AI — triggers coordinated assault when reinforcements arrive."""

    # -- evaluate -----------------------------------------------------------

    def evaluate(self, context: TacticalContext) -> float:
        """Return counterattack priority based on force ratio, posture, and morale."""
        alive_friendly = [u for u in context.friendly_units if u.is_alive]
        alive_enemies = [u for u in context.enemy_units if u.is_alive]

        force_ratio = len(alive_friendly) / max(len(alive_enemies), 1)

        # Outnumbered — no counterattack
        if force_ratio < _OUTNUMBERED_THRESHOLD:
            return 0.0

        # Reinforcements have not yet decisively reversed the balance
        if force_ratio <= _FORCE_RATIO_THRESHOLD:
            return 0.0

        score = _BASE_SCORE

        # Enemy offensive posture bonus
        if self._enemy_in_offensive_posture(alive_friendly, alive_enemies):
            score += _OFFENSIVE_POSTURE_BONUS

        # Friendly morale bonus
        if alive_friendly:
            avg_morale = sum(u.morale.value for u in alive_friendly) / len(alive_friendly)
            if avg_morale > _MORALE_THRESHOLD:
                score += _MORALE_BONUS

        return min(score, 1.0)

    # -- execute ------------------------------------------------------------

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Generate coordinated counterattack intents against the weakest enemy."""
        alive_friendly = [u for u in context.friendly_units if u.is_alive]
        alive_enemies = [u for u in context.enemy_units if u.is_alive]

        if not alive_friendly or not alive_enemies:
            return []

        weakest = self._find_weakest_enemy(alive_enemies)
        if weakest is None:
            return []

        target_pos = weakest.position.tile_coord

        # Select eligible attackers: HP > 60%, non-routing, able to act
        eligible = self._select_attackers(alive_friendly)
        if not eligible:
            return []

        attackers = eligible[:_MAX_ATTACKERS]
        flankers = eligible[_MAX_ATTACKERS : _MAX_ATTACKERS + _MAX_FLANKERS]

        intents: list[TacticIntent] = []

        # Primary counterattack — concentrate fire on the weakest enemy
        for unit in attackers:
            intents.append(
                TacticIntent(
                    unit_id=unit.id,
                    tactic_type=TacticType.COUNTER_ATTACK,
                    priority=_COUNTERATTACK_PRIORITY,
                    target_unit_id=weakest.id,
                    target_position=target_pos,
                )
            )

        # Flanking maneuver for any extra units beyond the assault team
        for unit in flankers:
            intents.append(
                TacticIntent(
                    unit_id=unit.id,
                    tactic_type=TacticType.FLANKING,
                    priority=_FLANKING_PRIORITY,
                    target_position=target_pos,
                )
            )

        return intents

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _find_weakest_enemy(enemies: list[Unit]) -> Unit | None:
        """Return the enemy with the lowest current HP, or None when empty."""
        if not enemies:
            return None
        return min(enemies, key=lambda e: e.health.hp)

    @staticmethod
    def _select_attackers(friendly: list[Unit]) -> list[Unit]:
        """Return eligible counterattack units sorted strongest-first.

        Eligible units are alive, able to act, have HP ratio > 60%, and
        are not currently routing.  The freshest units lead the charge.
        """
        eligible = [
            u
            for u in friendly
            if u.is_alive
            and u.can_act
            and u.health.hp_ratio > _ATTACKER_HP_RATIO
            and u.morale.state != MoraleState.ROUTING
        ]
        # Strongest HP first — lead with the freshest units
        eligible.sort(key=lambda u: u.health.hp_ratio, reverse=True)
        return eligible

    @staticmethod
    def _enemy_in_offensive_posture(
        friendly: list[Unit], enemies: list[Unit]
    ) -> bool:
        """Return True when >60% of enemies have advanced to the front line.

        The front line is the midpoint between the friendly and enemy
        centroids.  An enemy is considered 'on the front line' when it
        has advanced to (or past) that midpoint toward the friendly
        disposition — i.e. it is attacking rather than holding back.
        """
        if not friendly or not enemies:
            return False

        fcx = sum(u.position.tile_coord.x for u in friendly) / len(friendly)
        fcy = sum(u.position.tile_coord.y for u in friendly) / len(friendly)
        ecx = sum(u.position.tile_coord.x for u in enemies) / len(enemies)
        ecy = sum(u.position.tile_coord.y for u in enemies) / len(enemies)

        # Distance between centroids — enemies past the halfway point
        # are considered to be on the front line (offensive posture).
        centroid_dist = ((fcx - ecx) ** 2 + (fcy - ecy) ** 2) ** 0.5
        half_dist = centroid_dist / 2.0

        if half_dist < 1.0:
            # Forces are effectively intermingled — treat as offensive.
            return True

        on_front = 0
        for e in enemies:
            dx = e.position.tile_coord.x - fcx
            dy = e.position.tile_coord.y - fcy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= half_dist:
                on_front += 1

        ratio = on_front / max(len(enemies), 1)
        return ratio > _OFFENSIVE_POSTURE_RATIO
