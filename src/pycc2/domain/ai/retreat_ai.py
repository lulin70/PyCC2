"""Retreat Decision AI — CC2-Authentic Retreat & Bridge Demolition

Handles the decision to retreat units and demolish bridges when the
battlefield situation is unfavorable.  Inspired by CC2's behaviour where
the AI pulls back weakened units, uses MG teams for covering fire, and
destroys bridges to slow enemy advances.

Evaluation heuristic:
  - Force ratio (friendly_alive / enemy_alive) drives base priority
  - Low average morale boosts retreat urgency
  - Bridge VLs under threat boost priority for demolition

Execution phases:
  1. Identify units to retreat (low HP, low morale, non-essential)
  2. Assign covering fire (MG units suppress while others retreat)
  3. Calculate retreat destination (toward nearest safe VL or map edge)
  4. If bridge VL is about to fall, issue DEMOLISH_BRIDGE intent
"""

from __future__ import annotations

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.entities.unit import Unit, UnitType
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord


class RetreatDecisionAI(TacticalAIBase):
    """Decide when to retreat units and demolish bridges.

    Priority is driven by the force ratio between friendly and enemy
    alive units, with boosts for low morale and threatened bridge VLs.
    """

    BRIDGE_THREAT_RADIUS: int = 5
    LOW_MORALE_THRESHOLD: int = 30
    LOW_HP_RATIO: float = 0.5
    MAP_EDGE_MARGIN: int = 2

    # ------------------------------------------------------------------
    # TacticalAIBase interface
    # ------------------------------------------------------------------

    def evaluate(self, context: TacticalContext) -> float:
        """Return retreat priority based on force ratio, morale, and VL threats."""
        force_ratio = self._calculate_force_ratio(context)

        if force_ratio < 0.5:
            base = 0.7 + 0.2 * (0.5 - force_ratio) / 0.5
        elif force_ratio < 0.7:
            base = 0.3 + 0.2 * (0.7 - force_ratio) / 0.2
        else:
            base = 0.0 + 0.1 * max(0.0, 1.0 - force_ratio)

        # Boost for low average morale
        alive_friendly = [u for u in context.friendly_units if u.is_alive]
        if alive_friendly:
            avg_morale = sum(u.morale.value for u in alive_friendly) / len(alive_friendly)
            if avg_morale < self.LOW_MORALE_THRESHOLD:
                base += 0.15

        # Boost for threatened bridge VLs
        if self._is_bridge_threatened(context):
            base += 0.1

        return min(max(base, 0.0), 1.0)

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Generate retreat intents with covering fire for falling-back units."""
        intents: list[TacticIntent] = []

        # Phase 1: Identify units to retreat
        retreat_units = self._select_retreat_units(context)
        # Phase 2: Assign covering fire
        covering_units = self._select_covering_units(context)

        # Phase 3: Retreat weak units toward safe destinations
        for unit in retreat_units:
            dest = self._find_retreat_destination(unit, context)
            if dest is not None:
                intents.append(
                    TacticIntent(
                        unit_id=unit.id,
                        tactic_type=TacticType.RETREAT,
                        priority=8,
                        target_position=dest,
                    )
                )

        # Phase 2 (emit): MG covering fire while others retreat
        if retreat_units and covering_units:
            # Find nearest enemy to suppress
            alive_enemies = [e for e in context.enemy_units if e.is_alive]
            if alive_enemies:
                # Suppress the closest enemy to the retreating group
                retreat_centroid_x = sum(u.position.tile_coord.x for u in retreat_units) / len(
                    retreat_units
                )
                retreat_centroid_y = sum(u.position.tile_coord.y for u in retreat_units) / len(
                    retreat_units
                )
                retreat_centroid = TileCoord(int(retreat_centroid_x), int(retreat_centroid_y))
                nearest_enemy = min(
                    alive_enemies,
                    key=lambda e: e.position.tile_coord.chebyshev_distance(retreat_centroid),
                )
                for mg in covering_units:
                    intents.append(
                        TacticIntent(
                            unit_id=mg.id,
                            tactic_type=TacticType.SUPPRESS_FIRE,
                            priority=9,
                            target_unit_id=nearest_enemy.id,
                            target_position=nearest_enemy.position.tile_coord,
                        )
                    )

        # Phase 4: Bridge demolition
        if self._is_bridge_threatened(context):
            bridge_vls = self._find_threatened_bridge_vls(context)
            for vl_pos, _, _ in bridge_vls:
                # Find the nearest alive friendly unit that can act to carry
                # out the demolition (prefer engineers/infantry near the bridge)
                candidates = [
                    u
                    for u in context.friendly_units
                    if u.is_alive
                    and u.can_act
                    and u.position.tile_coord.chebyshev_distance(vl_pos)
                    <= self.BRIDGE_THREAT_RADIUS
                ]
                if candidates:
                    demolisher = min(
                        candidates,
                        key=lambda u: u.position.tile_coord.chebyshev_distance(vl_pos),
                    )
                    intents.append(
                        TacticIntent(
                            unit_id=demolisher.id,
                            tactic_type=TacticType.DEMOLISH_BRIDGE,
                            priority=10,
                            target_position=vl_pos,
                        )
                    )

        return intents

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_force_ratio(context: TacticalContext) -> float:
        """Return friendly_alive / max(enemy_alive, 1)."""
        friendly_alive = sum(1 for u in context.friendly_units if u.is_alive)
        enemy_alive = sum(1 for u in context.enemy_units if u.is_alive)
        return friendly_alive / max(enemy_alive, 1)

    def _is_bridge_threatened(self, context: TacticalContext) -> bool:
        """Check if any bridge VL has enemies within BRIDGE_THREAT_RADIUS tiles."""
        return len(self._find_threatened_bridge_vls(context)) > 0

    def _find_threatened_bridge_vls(
        self, context: TacticalContext
    ) -> list[tuple[TileCoord, str | None, int]]:
        """Return VL entries that are on bridge terrain and have nearby enemies."""
        threatened: list[tuple[TileCoord, str | None, int]] = []
        for vl_pos, owner, vl_val in context.vl_positions:
            if not context.game_map.is_within_bounds(vl_pos):
                continue
            terrain = context.game_map.get_terrain(vl_pos)
            if terrain != TerrainType.BRIDGE:
                continue
            enemies_near = sum(
                1
                for e in context.enemy_units
                if e.is_alive
                and e.position.tile_coord.chebyshev_distance(vl_pos) <= self.BRIDGE_THREAT_RADIUS
            )
            if enemies_near > 0:
                threatened.append((vl_pos, owner, vl_val))
        return threatened

    def _select_retreat_units(self, context: TacticalContext) -> list[Unit]:
        """Select units to retreat: HP < 50% or morale < 30."""
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and (
                u.health.hp_ratio < self.LOW_HP_RATIO or u.morale.value < self.LOW_MORALE_THRESHOLD
            )
        ]

    @staticmethod
    def _select_covering_units(context: TacticalContext) -> list[Unit]:
        """Select MG units for covering fire during retreat."""
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.unit_type == UnitType.MACHINE_GUN_SQUAD
            and u.morale.is_combat_effective
        ]

    def _find_retreat_destination(self, unit: Unit, context: TacticalContext) -> TileCoord | None:
        """Find the nearest safe point: friendly-held VL or map edge."""
        faction_name = context.friendly_units[0].faction.name if context.friendly_units else None

        # Prefer nearest friendly-held VL that is not under threat
        safe_vls: list[tuple[TileCoord, int]] = []
        for vl_pos, owner, _ in context.vl_positions:
            if owner != faction_name:
                continue
            enemies_near = sum(
                1
                for e in context.enemy_units
                if e.is_alive
                and e.position.tile_coord.chebyshev_distance(vl_pos) <= self.BRIDGE_THREAT_RADIUS
            )
            if enemies_near == 0:
                dist = unit.position.tile_coord.chebyshev_distance(vl_pos)
                safe_vls.append((vl_pos, dist))

        if safe_vls:
            safe_vls.sort(key=lambda v: v[1])
            return safe_vls[0][0]

        # Fallback: retreat toward the nearest map edge
        gm = context.game_map
        unit_pos = unit.position.tile_coord
        candidates = [
            TileCoord(self.MAP_EDGE_MARGIN, unit_pos.y),  # left edge
            TileCoord(gm.width - 1 - self.MAP_EDGE_MARGIN, unit_pos.y),  # right edge
            TileCoord(unit_pos.x, self.MAP_EDGE_MARGIN),  # top edge
            TileCoord(unit_pos.x, gm.height - 1 - self.MAP_EDGE_MARGIN),  # bottom edge
        ]
        # Pick the closest edge point that is within bounds
        valid = [c for c in candidates if gm.is_within_bounds(c)]
        if not valid:
            return None
        return min(valid, key=lambda c: unit_pos.chebyshev_distance(c))
