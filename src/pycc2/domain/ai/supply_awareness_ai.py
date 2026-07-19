"""Supply Awareness AI — CC2-Authentic Supply Line Protection/Severance

In Close Combat 2, supply lines are the lifeblood of military operations.
Bridges, road junctions, and Victory Locations (VLs) serve as critical
chokepoints on supply routes. An AI with supply line awareness will:

  - Defend friendly supply chokepoints under threat (DEFEND orders)
  - Attack enemy supply chokepoints when opportunity arises (ATTACK orders)

Components:
  - SupplyAwarenessAI: Evaluates supply line threats and opportunities,
    issues DEFEND/ATTACK orders to protect or sever supply routes.

CC2 authentic behaviour:
  - Bridges are supply line chokepoints — destroying or controlling them
    cuts off enemy reinforcements and ammunition
  - VL positions often sit astride key supply routes
  - AI prioritises defending threatened friendly supply points
  - AI attacks vulnerable enemy supply points when forces are available
  - Low priority (2) — supports but does not override core combat orders
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai_types import TacticalAIBase, TacticalContext, _threat_score
from pycc2.domain.entities.unit import UnitType
from pycc2.domain.value_objects.terrain_type import TerrainType

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.tile_coord import TileCoord

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Supply point types
_SUPPLY_DEFEND_TYPES: set[UnitType] = {
    UnitType.INFANTRY_SQUAD,
    UnitType.MACHINE_GUN_SQUAD,
    UnitType.AT_GUN_TEAM,
}

_SUPPLY_ATTACK_TYPES: set[UnitType] = {
    UnitType.INFANTRY_SQUAD,
    UnitType.MACHINE_GUN_SQUAD,
    UnitType.TANK,
}

# Threat threshold: enemy threat score above this means supply point is endangered.
# At 0.3, a full-HP infantry squad (weight=1.0) within 3 tiles counts as a threat,
# and heavier units (tank=3.5) register from ~11 tiles away.
_THREAT_THRESHOLD: float = 0.3

# Attack opportunity threshold: friendly advantage above this means attack is viable.
_ATTACK_ADVANTAGE_THRESHOLD: float = 1.5

# Detection radius (tiles) for threats/opportunities around supply points.
_SUPPLY_SCAN_RADIUS: int = 8

# Supply order priority (low — background supply security).
_SUPPLY_PRIORITY: int = 2

# Maximum supply orders per tick (avoid committing too many units to supply duty).
_MAX_SUPPLY_ORDERS_PER_TICK: int = 3

# Blackboard keys for tracking supply assignments.
BB_SUPPLY_DEFEND_ASSIGNED: str = "supply_defend_assigned_unit_ids"
BB_SUPPLY_ATTACK_ASSIGNED: str = "supply_attack_assigned_unit_ids"


# ---------------------------------------------------------------------------
# Difficulty-scaled parameters (v0.8.0)
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class SupplyParams:
    """Difficulty-scaled supply-awareness parameters computed per evaluation.

    Falls back to hardcoded constants when difficulty_config is None.
    """

    threat_threshold: float
    attack_advantage_threshold: float
    scan_radius: int
    max_orders_per_tick: int


# ---------------------------------------------------------------------------
# SupplyAwarenessAI
# ---------------------------------------------------------------------------


class SupplyAwarenessAI(TacticalAIBase):
    """Evaluate supply line threats and issue DEFEND/ATTACK orders.

    CC2 behaviour: Supply chokepoints (bridges, VL positions) are critical
    to sustaining combat operations. This AI:

      - Identifies supply chokepoints on the map (bridges + VL positions)
      - Assesses threat to friendly-controlled chokepoints
      - Identifies attack opportunities on enemy-controlled chokepoints
      - Dispatches units to defend or attack as needed

    Evaluation heuristic:
      - Higher score when friendly supply points are threatened
      - Higher score when enemy supply points are vulnerable
      - Zero when no supply points exist or no units are available
    """

    def evaluate(self, context: TacticalContext) -> float:
        """Return supply awareness priority based on threats and opportunities."""
        supply_points = self._identify_supply_points(context)
        if not supply_points:
            return 0.0

        available_units = self._available_units(context)
        if not available_units:
            return 0.0

        params = self._get_supply_params(context)

        defend_need = self._defend_need(context, supply_points, params)
        attack_opportunity = self._attack_opportunity(context, supply_points, params)

        score = 0.5 * defend_need + 0.5 * attack_opportunity
        return max(0.0, min(score, 1.0))

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Generate DEFEND/ATTACK intents for supply line security."""
        available_units = self._available_units(context)
        if not available_units:
            return []

        supply_points = self._identify_supply_points(context)
        if not supply_points:
            return []

        defend_assigned: set[str] = self._load_assigned(context, BB_SUPPLY_DEFEND_ASSIGNED)
        attack_assigned: set[str] = self._load_assigned(context, BB_SUPPLY_ATTACK_ASSIGNED)

        params = self._get_supply_params(context)
        max_orders = params.max_orders_per_tick

        intents: list[TacticIntent] = []
        all_assigned = defend_assigned | attack_assigned

        # Generate DEFEND intents for threatened friendly supply points
        for point in self._threatened_friendly_points(context, supply_points, params):
            if len(intents) >= max_orders:
                break
            unit = self._nearest_available_unit(
                point, available_units, all_assigned, _SUPPLY_DEFEND_TYPES
            )
            if unit is None:
                continue
            intents.append(
                TacticIntent(
                    unit_id=unit.id,
                    tactic_type=TacticType.DEFEND,
                    priority=_SUPPLY_PRIORITY,
                    target_position=point,
                )
            )
            all_assigned.add(unit.id)
            defend_assigned.add(unit.id)

        # Generate ATTACK intents for vulnerable enemy supply points
        for point in self._vulnerable_enemy_points(context, supply_points, params):
            if len(intents) >= max_orders:
                break
            unit = self._nearest_available_unit(
                point, available_units, all_assigned, _SUPPLY_ATTACK_TYPES
            )
            if unit is None:
                continue
            intents.append(
                TacticIntent(
                    unit_id=unit.id,
                    tactic_type=TacticType.ATTACK,
                    priority=_SUPPLY_PRIORITY,
                    target_position=point,
                )
            )
            all_assigned.add(unit.id)
            attack_assigned.add(unit.id)

        return intents

    # ------------------------------------------------------------------
    # Supply point identification
    # ------------------------------------------------------------------

    @staticmethod
    def _get_supply_params(context: TacticalContext) -> SupplyParams:
        """Compute difficulty-scaled supply parameters (v0.8.0).

        Falls back to original hardcoded values when difficulty_config is None,
        preserving backward compatibility with pre-v0.8.0 behavior.
        """
        cfg = context.difficulty_config
        if cfg is None:
            return SupplyParams(
                threat_threshold=_THREAT_THRESHOLD,
                attack_advantage_threshold=_ATTACK_ADVANTAGE_THRESHOLD,
                scan_radius=_SUPPLY_SCAN_RADIUS,
                max_orders_per_tick=_MAX_SUPPLY_ORDERS_PER_TICK,
            )

        # Low perception_accuracy → higher threat threshold (slower to react)
        threat_threshold = _THREAT_THRESHOLD / max(cfg.perception_accuracy, 0.1)
        # Low aggressiveness → higher attack threshold (more conservative)
        attack_threshold = _ATTACK_ADVANTAGE_THRESHOLD * (1.5 - cfg.aggressiveness)
        # Vision range determines scan radius
        scan_radius = max(3, int(_SUPPLY_SCAN_RADIUS * cfg.vision_range_multiplier))
        # Tactical variety determines max orders
        max_orders = max(1, int(_MAX_SUPPLY_ORDERS_PER_TICK * cfg.tactical_variety))

        return SupplyParams(
            threat_threshold=threat_threshold,
            attack_advantage_threshold=attack_threshold,
            scan_radius=scan_radius,
            max_orders_per_tick=max_orders,
        )

    @staticmethod
    def _identify_supply_points(context: TacticalContext) -> list[TileCoord]:
        """Find all supply chokepoints: bridges + VL positions.

        Bridges are found by scanning the map tile grid for TerrainType.BRIDGE.
        VL positions are taken from the tactical context.
        """
        points: list[TileCoord] = []

        # VL positions from context
        for vl_pos, _owner, _value in context.vl_positions:
            points.append(vl_pos)

        # Bridge positions from map
        game_map = context.game_map
        if game_map is not None:
            import numpy as np

            bridge_mask = game_map.tile_grid == TerrainType.BRIDGE.value
            ys, xs = np.where(bridge_mask)
            from pycc2.domain.value_objects.tile_coord import TileCoord as TC

            for y, x in zip(ys, xs, strict=True):
                points.append(TC(int(x), int(y)))

        return points

    # ------------------------------------------------------------------
    # Threat / opportunity assessment
    # ------------------------------------------------------------------

    @staticmethod
    def _defend_need(
        context: TacticalContext,
        supply_points: list[TileCoord],
        params: SupplyParams,
    ) -> float:
        """Assess how many friendly supply points are under threat.

        Returns a ratio [0.0, 1.0] of threatened un-defended points.
        """
        if not supply_points or not context.enemy_units:
            return 0.0

        threatened = 0
        for point in supply_points:
            if SupplyAwarenessAI._is_friendly_point(context, point):
                threat = SupplyAwarenessAI._area_threat(context, point, params.scan_radius)
                if threat > params.threat_threshold:
                    threatened += 1

        friendly_points = SupplyAwarenessAI._friendly_point_count(context, supply_points)
        if friendly_points == 0:
            return 0.0
        return min(threatened / friendly_points, 1.0)

    @staticmethod
    def _attack_opportunity(
        context: TacticalContext,
        supply_points: list[TileCoord],
        params: SupplyParams,
    ) -> float:
        """Assess how many enemy supply points are vulnerable to attack.

        Returns a ratio [0.0, 1.0] of vulnerable enemy points.
        """
        if not supply_points or not context.friendly_units:
            return 0.0

        vulnerable = 0
        for point in supply_points:
            if SupplyAwarenessAI._is_enemy_point(context, point):
                advantage = SupplyAwarenessAI._area_advantage(context, point, params.scan_radius)
                if advantage > params.attack_advantage_threshold:
                    vulnerable += 1

        enemy_points = SupplyAwarenessAI._enemy_point_count(context, supply_points)
        if enemy_points == 0:
            return 0.0
        return min(vulnerable / enemy_points, 1.0)

    @staticmethod
    def _threatened_friendly_points(
        context: TacticalContext,
        supply_points: list[TileCoord],
        params: SupplyParams,
    ) -> list[TileCoord]:
        """Return friendly supply points that are under threat."""
        result: list[TileCoord] = []
        for point in supply_points:
            if SupplyAwarenessAI._is_friendly_point(context, point):
                threat = SupplyAwarenessAI._area_threat(context, point, params.scan_radius)
                if threat > params.threat_threshold:
                    result.append(point)
        return result

    @staticmethod
    def _vulnerable_enemy_points(
        context: TacticalContext,
        supply_points: list[TileCoord],
        params: SupplyParams,
    ) -> list[TileCoord]:
        """Return enemy supply points that are vulnerable to attack."""
        result: list[TileCoord] = []
        for point in supply_points:
            if SupplyAwarenessAI._is_enemy_point(context, point):
                advantage = SupplyAwarenessAI._area_advantage(context, point, params.scan_radius)
                if advantage > params.attack_advantage_threshold:
                    result.append(point)
        return result

    # ------------------------------------------------------------------
    # Area scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _area_threat(context: TacticalContext, point: TileCoord, scan_radius: int) -> float:
        """Sum enemy threat scores within scan radius of *point*."""
        total = 0.0
        for enemy in context.enemy_units:
            if not enemy.is_alive:
                continue
            dist = enemy.position.tile_coord.chebyshev_distance(point)
            if dist <= scan_radius:
                total += _threat_score(enemy, point)
        return total

    @staticmethod
    def _area_advantage(context: TacticalContext, point: TileCoord, scan_radius: int) -> float:
        """Compute friendly-to-enemy advantage ratio around *point*.

        Returns (friendly_strength / max(enemy_strength, 1.0)).
        A value > 1.0 means friendlies outnumber enemies.
        """
        friendly_strength = 0.0
        enemy_strength = 0.0

        for unit in context.friendly_units:
            if not unit.is_alive:
                continue
            dist = unit.position.tile_coord.chebyshev_distance(point)
            if dist <= scan_radius:
                friendly_strength += 1.0 * (0.5 + 0.5 * unit.health.hp_ratio)

        for enemy in context.enemy_units:
            if not enemy.is_alive:
                continue
            dist = enemy.position.tile_coord.chebyshev_distance(point)
            if dist <= scan_radius:
                enemy_strength += 1.0 * (0.5 + 0.5 * enemy.health.hp_ratio)

        return friendly_strength / max(enemy_strength, 1.0)

    # ------------------------------------------------------------------
    # Point ownership classification
    # ------------------------------------------------------------------

    @staticmethod
    def _is_friendly_point(context: TacticalContext, point: TileCoord) -> bool:
        """Check if *point* is a VL controlled by the friendly faction."""
        friendly_faction = context.friendly_faction
        for vl_pos, owner, _value in context.vl_positions:
            if vl_pos == point and owner is not None:
                if friendly_faction is not None and owner == friendly_faction.name:
                    return True
        return False

    @staticmethod
    def _is_enemy_point(context: TacticalContext, point: TileCoord) -> bool:
        """Check if *point* is a VL controlled by the enemy faction."""
        friendly_faction = context.friendly_faction
        for vl_pos, owner, _value in context.vl_positions:
            if vl_pos == point and owner is not None:
                if friendly_faction is None or owner != friendly_faction.name:
                    return True
        return False

    @staticmethod
    def _friendly_point_count(context: TacticalContext, supply_points: list[TileCoord]) -> int:
        """Count supply points controlled by the friendly faction."""
        count = 0
        for point in supply_points:
            if SupplyAwarenessAI._is_friendly_point(context, point):
                count += 1
        return count

    @staticmethod
    def _enemy_point_count(context: TacticalContext, supply_points: list[TileCoord]) -> int:
        """Count supply points controlled by the enemy faction."""
        count = 0
        for point in supply_points:
            if SupplyAwarenessAI._is_enemy_point(context, point):
                count += 1
        return count

    # ------------------------------------------------------------------
    # Unit selection
    # ------------------------------------------------------------------

    @staticmethod
    def _available_units(context: TacticalContext) -> list[Unit]:
        """Return alive friendly units not already assigned to supply duty."""
        defend_assigned = SupplyAwarenessAI._load_assigned(context, BB_SUPPLY_DEFEND_ASSIGNED)
        attack_assigned = SupplyAwarenessAI._load_assigned(context, BB_SUPPLY_ATTACK_ASSIGNED)
        all_assigned = defend_assigned | attack_assigned

        return [u for u in context.friendly_units if u.is_alive and u.id not in all_assigned]

    @staticmethod
    def _nearest_available_unit(
        target: TileCoord,
        units: list[Unit],
        assigned_ids: set[str],
        preferred_types: set[UnitType],
    ) -> Unit | None:
        """Find the nearest unassigned unit, preferring specific types."""
        # First try preferred types
        preferred = [
            u for u in units if u.id not in assigned_ids and u.unit_type in preferred_types
        ]
        if preferred:
            return min(preferred, key=lambda u: u.position.tile_coord.chebyshev_distance(target))

        # Fallback: any unassigned unit
        fallback = [u for u in units if u.id not in assigned_ids]
        if fallback:
            return min(fallback, key=lambda u: u.position.tile_coord.chebyshev_distance(target))

        return None

    # ------------------------------------------------------------------
    # Blackboard helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_assigned(context: TacticalContext, key: str) -> set[str]:
        """Load a set of assigned unit IDs from the blackboard."""
        bb = context.blackboards.get("supply")
        if bb is None:
            return set()
        stored = bb.get(key)
        if stored is None:
            return set()
        if isinstance(stored, set):
            return stored
        if isinstance(stored, list):
            return set(stored)
        return set()
