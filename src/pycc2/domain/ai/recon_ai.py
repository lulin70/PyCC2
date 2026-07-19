"""Reconnaissance AI — CC2-Authentic Scouting Behavior

In Close Combat 2, reconnaissance is a critical tactical activity. Light,
stealthy units (sniper teams, infantry squads) are dispatched to strategic
locations to gather intelligence on enemy positions before committing main
forces to action.

Components:
  - ReconAI: Evaluates when reconnaissance is needed and issues
    RECONNAISSANCE orders to suitable units.

Reconnaissance conditions (CC2-authentic):
  - Enemy information is incomplete (few enemies spotted relative to expected)
  - Suitable recon units are available (SNIPER_TEAM preferred)
  - Strategic locations exist that need scouting (VL positions, unexplored areas)
  - Unit is not already assigned a recon mission (Blackboard tracking)

Reconnaissance execution:
  - SNIPER_TEAM gets priority for recon assignments (high stealth)
  - INFANTRY_SQUAD used as secondary recon unit
  - Target selection: nearest unexplored VL position
  - Low priority (2) — does not override combat orders
  - One recon unit per target (no duplication via Blackboard tracking)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai_types import TacticalAIBase, TacticalContext
from pycc2.domain.entities.unit import UnitType

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.tile_coord import TileCoord


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Unit types suitable for reconnaissance, ordered by preference.
_RECON_UNIT_PRIORITY: list[UnitType] = [
    UnitType.SNIPER_TEAM,
    UnitType.INFANTRY_SQUAD,
]

# Expected enemy count heuristic: assume at least as many enemies as friendlies.
_MIN_EXPECTED_ENEMY_FACTOR: float = 0.5

# Recon order priority (low — background intelligence gathering).
_RECON_PRIORITY: int = 2

# Maximum recon assignments per tick (avoid sending all units scouting).
_MAX_RECON_PER_TICK: int = 3

# Blackboard keys for tracking recon assignments.
BB_RECON_ASSIGNED: str = "recon_assigned_unit_ids"
BB_RECON_TARGETS: str = "recon_target_positions"


# ---------------------------------------------------------------------------
# Difficulty-scaled parameters (v0.8.0)
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class ReconParams:
    """Difficulty-scaled recon parameters computed per evaluation.

    Falls back to hardcoded constants when difficulty_config is None.
    """

    min_expected_enemy_factor: float
    max_recon_per_tick: int
    intel_weight: float
    available_weight: float
    defensive_weight: float


# ---------------------------------------------------------------------------
# ReconAI
# ---------------------------------------------------------------------------


class ReconAI(TacticalAIBase):
    """Evaluate reconnaissance needs and issue RECONNAISSANCE orders.

    CC2 behaviour: When enemy information is incomplete, light units are
    dispatched to strategic locations (VL positions, unexplored areas) to
    gather intelligence. This is a low-priority background action that
    supports main combat operations.

    Evaluation heuristic:
      - Higher score when few enemies have been spotted (intelligence gap)
      - Higher score when recon-capable units are available
      - Higher score when friendly units are in defensive positions
      - Zero when all enemies are known or no recon units available
    """

    def evaluate(self, context: TacticalContext) -> float:
        """Return reconnaissance priority based on intelligence gaps and unit availability."""
        recon_units = self._recon_candidates(context)
        if not recon_units:
            return 0.0

        params = self._get_recon_params(context)

        intel_need = self._intel_need(context, params.min_expected_enemy_factor)
        if intel_need <= 0.0:
            return 0.0

        available_ratio = self._available_ratio(context, recon_units)
        defensive_stance = self._defensive_stance(context)

        # Difficulty-scaled scoring weights (v0.8.0):
        # - Low aggressiveness → more defensive weighting
        # - High aggressiveness → more intel weighting
        score = (
            params.intel_weight * intel_need
            + params.available_weight * available_ratio
            + params.defensive_weight * defensive_stance
        )
        return max(0.0, min(score, 1.0))

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Generate RECONNAISSANCE intents for available recon units."""
        recon_units = self._recon_candidates(context)
        if not recon_units:
            return []

        targets = self._recon_targets(context)
        if not targets:
            return []

        assigned_ids: set[str] = self._load_assigned(context)
        assigned_targets: set[tuple[int, int]] = self._load_assigned_targets(context)

        params = self._get_recon_params(context)
        max_recon_per_tick = params.max_recon_per_tick

        intents: list[TacticIntent] = []
        for unit in recon_units:
            if len(intents) >= max_recon_per_tick:
                break
            if unit.id in assigned_ids:
                continue

            target = self._nearest_unassigned_target(
                unit.position.tile_coord, targets, assigned_targets
            )
            if target is None:
                continue

            intents.append(
                TacticIntent(
                    unit_id=unit.id,
                    tactic_type=TacticType.RECONNAISSANCE,
                    priority=_RECON_PRIORITY,
                    target_position=target,
                )
            )
            assigned_ids.add(unit.id)
            assigned_targets.add((target.x, target.y))

        return intents

    # -- helpers --

    @staticmethod
    def _get_recon_params(context: TacticalContext) -> ReconParams:
        """Compute difficulty-scaled recon parameters (v0.8.0).

        Falls back to original hardcoded values when difficulty_config is None,
        preserving backward compatibility with pre-v0.8.0 behavior.
        """
        cfg = context.difficulty_config
        if cfg is None:
            return ReconParams(
                min_expected_enemy_factor=_MIN_EXPECTED_ENEMY_FACTOR,
                max_recon_per_tick=_MAX_RECON_PER_TICK,
                intel_weight=0.5,
                available_weight=0.3,
                defensive_weight=0.2,
            )

        # Low perception_accuracy → fewer expected enemies → less recon urgency
        min_expected_enemy = _MIN_EXPECTED_ENEMY_FACTOR * cfg.perception_accuracy
        # Low tactical_variety (VETERAN) → fewer, more focused recon missions
        max_recon_per_tick = max(1, int(_MAX_RECON_PER_TICK * cfg.tactical_variety))
        # Low aggressiveness → more defensive weighting
        intel_weight = 0.5 * (1.0 - cfg.aggressiveness * 0.3)
        defensive_weight = 0.2 + cfg.aggressiveness * 0.3
        available_weight = max(0.0, 1.0 - intel_weight - defensive_weight)

        return ReconParams(
            min_expected_enemy_factor=min_expected_enemy,
            max_recon_per_tick=max_recon_per_tick,
            intel_weight=intel_weight,
            available_weight=available_weight,
            defensive_weight=defensive_weight,
        )

    @staticmethod
    def _recon_candidates(context: TacticalContext) -> list[Unit]:
        """Find units suitable for reconnaissance, ordered by type priority."""
        candidates = [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.unit_type in _RECON_UNIT_PRIORITY
            and u.morale.is_combat_effective
        ]
        # Sort by recon priority: SNIPER_TEAM first, then INFANTRY_SQUAD.
        type_order = {t: i for i, t in enumerate(_RECON_UNIT_PRIORITY)}
        candidates.sort(key=lambda u: type_order.get(u.unit_type, 99))
        return candidates

    @staticmethod
    def _intel_need(context: TacticalContext, min_expected_enemy_factor: float) -> float:
        """Measure intelligence gap (0.0 = full intel, 1.0 = no intel).

        Args:
            context: Tactical context.
            min_expected_enemy_factor: Difficulty-scaled factor (v0.8.0).
                Lower factor (low perception_accuracy) → fewer expected enemies
                → less recon urgency.
        """
        alive_enemies = [e for e in context.enemy_units if e.is_alive]
        alive_friendlies = [u for u in context.friendly_units if u.is_alive]
        if not alive_friendlies:
            return 0.0

        # All enemies eliminated — no reconnaissance needed.
        if context.enemy_units and not alive_enemies:
            return 0.0

        expected_enemies = max(int(len(alive_friendlies) * min_expected_enemy_factor), 1)
        spotted = len(alive_enemies)
        if spotted >= expected_enemies:
            return 0.0

        return 1.0 - (spotted / expected_enemies)

    @staticmethod
    def _available_ratio(context: TacticalContext, recon_units: list[Unit]) -> float:
        """Ratio of recon-capable units to total friendly units."""
        alive_friendlies = [u for u in context.friendly_units if u.is_alive]
        if not alive_friendlies:
            return 0.0
        return min(len(recon_units) / len(alive_friendlies), 1.0)

    @staticmethod
    def _defensive_stance(context: TacticalContext) -> float:
        """Measure how many friendly units are in defensive positions.

        Uses Blackboard 'stationary_ticks' as a proxy for defensive posture.
        """
        alive_friendlies = [u for u in context.friendly_units if u.is_alive]
        if not alive_friendlies:
            return 0.0

        defensive = 0
        for u in alive_friendlies:
            bb = context.blackboards.get(u.id)
            if bb is not None and bb.get("stationary_ticks", 0) > 0:
                defensive += 1

        return defensive / len(alive_friendlies)

    @staticmethod
    def _recon_targets(context: TacticalContext) -> list[TileCoord]:
        """Collect strategic locations worth scouting.

        Priority sources:
          1. VL positions (victory locations — contested objectives)
          2. Map edge midpoints (likely enemy approach routes)
        """
        targets: list[TileCoord] = []

        # VL positions from context.
        for vl_pos, _owner, _value in context.vl_positions:
            targets.append(vl_pos)

        # Map edge midpoints as secondary targets.
        game_map = context.game_map
        if game_map is not None:
            w = game_map.width
            h = game_map.height
            if w > 0 and h > 0:
                from pycc2.domain.value_objects.tile_coord import TileCoord

                targets.append(TileCoord(w // 2, 0))  # Top edge
                targets.append(TileCoord(w // 2, h - 1))  # Bottom edge
                targets.append(TileCoord(0, h // 2))  # Left edge
                targets.append(TileCoord(w - 1, h // 2))  # Right edge

        return targets

    @staticmethod
    def _load_assigned(context: TacticalContext) -> set[str]:
        """Load already-assigned recon unit IDs from shared Blackboard."""
        bb = context.blackboards.get("__shared__")
        if bb is None:
            return set()
        ids = bb.get(BB_RECON_ASSIGNED, [])
        return set(ids) if isinstance(ids, list) else set()

    @staticmethod
    def _load_assigned_targets(context: TacticalContext) -> set[tuple[int, int]]:
        """Load already-assigned recon target positions from shared Blackboard."""
        bb = context.blackboards.get("__shared__")
        if bb is None:
            return set()
        targets = bb.get(BB_RECON_TARGETS, [])
        if not isinstance(targets, list):
            return set()
        result: set[tuple[int, int]] = set()
        for t in targets:
            if hasattr(t, "x") and hasattr(t, "y"):
                result.add((t.x, t.y))
            elif isinstance(t, (list, tuple)) and len(t) == 2:
                result.add((int(t[0]), int(t[1])))
        return result

    @staticmethod
    def _nearest_unassigned_target(
        origin: TileCoord,
        targets: list[TileCoord],
        assigned: set[tuple[int, int]],
    ) -> TileCoord | None:
        """Find the nearest target not already assigned to another unit."""
        best: TileCoord | None = None
        best_dist = float("inf")
        for target in targets:
            key = (target.x, target.y)
            if key in assigned:
                continue
            dist = origin.chebyshev_distance(target)
            if dist < best_dist:
                best_dist = dist
                best = target
        return best
