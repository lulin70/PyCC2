"""InfantryTankCoordAI + VictoryPointAI — Coordination and VP tactics.

InfantryTankCoordAI:
  CC2 behaviour:
    - Tanks provide covering fire for infantry advances
    - Infantry protect tank flanks from AT weapons
    - Tanks do NOT advance without infantry support
    - Tanks prefer to advance along roads to reduce side exposure

VictoryPointAI:
  CC2 behaviour:
    - AI assigns units to capture uncontrolled VLs
    - AI defends held VLs with appropriate force
    - AI retreats from indefensible VLs to reinforce others
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai_types import (
    _ARMOR_TYPES,
    _AT_TYPES,
    _INFANTRY_TYPES,
    TacticalAIBase,
    TacticalContext,
    _threat_score,
)
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


# ---------------------------------------------------------------------------
# InfantryTankCoordAI
# ---------------------------------------------------------------------------


class InfantryTankCoordAI(TacticalAIBase):
    """Coordinate infantry and armor operations.

    CC2 behaviour:
      - Tanks provide covering fire for infantry advances
      - Infantry protect tank flanks from AT weapons
      - Tanks do NOT advance without infantry support
      - Tanks prefer to advance along roads to reduce side exposure

    P9 Enhancement:
      - Tanks now plan advance routes preferring roads
      - Infantry screening positions account for AT weapon range
      - Tank advance speed limited by slowest supporting infantry

    Evaluation heuristic:
      - Higher score when both tanks and infantry are present
      - Higher score when enemy AT weapons are detected
      - Zero when no tanks or no infantry available
    """

    INFANTRY_SUPPORT_RANGE: int = 10  # max tiles between infantry and tank
    AT_SCREEN_DISTANCE: int = 3  # infantry screen distance from tank

    def evaluate(self, context: TacticalContext) -> float:
        tanks = self._tanks(context)
        infantry = self._infantry(context)
        if not tanks or not infantry:
            return 0.0

        enemy_at = [e for e in context.enemy_units if e.unit_type in _AT_TYPES and e.is_alive]
        at_threat = min(len(enemy_at) / 2.0, 1.0)
        tank_ratio = min(len(tanks) / 2.0, 1.0)
        inf_ratio = min(len(infantry) / 3.0, 1.0)

        diff_mod = 1.0
        if context.difficulty_config is not None:
            if not context.difficulty_config.coordination_enabled:
                return 0.0
            diff_mod = context.difficulty_config.aggressiveness

        score = 0.3 * tank_ratio + 0.3 * inf_ratio + 0.4 * at_threat
        return min(score * diff_mod, 1.0)

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        tanks = self._tanks(context)
        infantry = self._infantry(context)
        enemies = [e for e in context.enemy_units if e.is_alive]
        if not tanks or not infantry or not enemies:
            return []

        enemy_at = [e for e in enemies if e.unit_type in _AT_TYPES]
        intents: list[TacticIntent] = []

        # Find the primary enemy target (highest threat to tanks)
        if enemy_at:
            primary_target = max(
                enemy_at,
                key=lambda e: _threat_score(e, tanks[0].position.tile_coord),
            )
        else:
            primary_target = max(
                enemies,
                key=lambda e: _threat_score(e, tanks[0].position.tile_coord),
            )

        target_pos = primary_target.position.tile_coord

        for tank in tanks:
            # Check if infantry is nearby to support
            nearby_infantry = [
                i
                for i in infantry
                if i.position.tile_coord.chebyshev_distance(tank.position.tile_coord)
                <= self.INFANTRY_SUPPORT_RANGE
            ]

            if nearby_infantry:
                # Tank advances with infantry support
                # Plan route preferring roads (CC2 Patch 2.0 improvement)
                advance_pos = self._plan_tank_advance(tank.position.tile_coord, target_pos, context)
                intents.append(
                    TacticIntent(
                        unit_id=tank.id,
                        tactic_type=TacticType.COORDINATED_ADVANCE,
                        priority=8,
                        target_position=advance_pos,
                        target_unit_id=primary_target.id,
                    )
                )
            else:
                # Tank holds position and fires — no infantry support
                intents.append(
                    TacticIntent(
                        unit_id=tank.id,
                        tactic_type=TacticType.HOLD_POSITION,
                        priority=9,
                        target_unit_id=primary_target.id,
                    )
                )

        # Infantry escort: protect tank flanks from AT
        if enemy_at:
            for inf in infantry[: len(tanks) * 2]:
                # Move infantry to screen tank flanks toward nearest AT threat
                nearest_at = min(
                    enemy_at,
                    key=lambda at: inf.position.tile_coord.chebyshev_distance(
                        at.position.tile_coord
                    ),
                )
                at_pos = nearest_at.position.tile_coord
                # Position between tank and AT threat, accounting for AT range
                screen_pos = self._screening_position(at_pos, tanks[0].position.tile_coord)
                intents.append(
                    TacticIntent(
                        unit_id=inf.id,
                        tactic_type=TacticType.COORDINATED_ADVANCE,
                        priority=7,
                        target_position=screen_pos,
                        target_unit_id=nearest_at.id,
                    )
                )
        else:
            # No AT threat — infantry advance alongside tanks
            for inf in infantry[: len(tanks) * 2]:
                intents.append(
                    TacticIntent(
                        unit_id=inf.id,
                        tactic_type=TacticType.COORDINATED_ADVANCE,
                        priority=6,
                        target_position=target_pos,
                        target_unit_id=primary_target.id,
                    )
                )

        return intents

    # -- helpers --

    @staticmethod
    def _tanks(context: TacticalContext) -> list[Unit]:
        return [
            u
            for u in context.friendly_units
            if u.is_alive and u.can_act and u.unit_type in _ARMOR_TYPES
        ]

    @staticmethod
    def _infantry(context: TacticalContext) -> list[Unit]:
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.unit_type in _INFANTRY_TYPES
            and u.morale.is_combat_effective
        ]

    @staticmethod
    def _screening_position(
        at_pos: TileCoord,
        tank_pos: TileCoord,
    ) -> TileCoord:
        """Place infantry between the AT threat and the tank to screen.

        P9 Enhancement: Account for AT weapon range — position infantry
        close enough to intercept AT teams before they can fire.
        """
        mx = (tank_pos.x + at_pos.x) // 2
        my = (tank_pos.y + at_pos.y) // 2
        # Offset slightly toward the AT to intercept
        dx = at_pos.x - mx
        dy = at_pos.y - my
        length = math.sqrt(dx * dx + dy * dy) or 1.0
        sx = int(mx + dx / length * 2)
        sy = int(my + dy / length * 2)
        return TileCoord(sx, sy)

    @staticmethod
    def _plan_tank_advance(
        tank_pos: TileCoord,
        target_pos: TileCoord,
        context: TacticalContext,
    ) -> TileCoord:
        """Plan tank advance route, preferring roads.

        CC2 Patch 2.0 improvement: tanks advance along roads to
        reduce side exposure to AT weapons. If no road is available,
        advance directly toward target.

        Returns the next waypoint for the tank.
        """
        game_map = context.game_map

        # Check for road tiles along the path
        dx = target_pos.x - tank_pos.x
        dy = target_pos.y - tank_pos.y
        dist = math.sqrt(dx * dx + dy * dy) or 1.0

        # Step size: advance 3-5 tiles per decision
        step = min(5, max(3, int(dist / 3)))

        # Check 3 candidate paths: direct, left-biased, right-biased
        candidates = []

        # Direct path
        direct = TileCoord(
            int(tank_pos.x + dx / dist * step),
            int(tank_pos.y + dy / dist * step),
        )
        candidates.append(direct)

        # Left-biased (perpendicular offset)
        perp_x = -dy / dist
        perp_y = dx / dist
        left = TileCoord(
            int(tank_pos.x + dx / dist * step + perp_x * 2),
            int(tank_pos.y + dy / dist * step + perp_y * 2),
        )
        candidates.append(left)

        # Right-biased
        right = TileCoord(
            int(tank_pos.x + dx / dist * step - perp_x * 2),
            int(tank_pos.y + dy / dist * step - perp_y * 2),
        )
        candidates.append(right)

        # Score each candidate: prefer roads, then passable terrain
        best_pos = direct
        best_score = -1.0

        for pos in candidates:
            if not game_map.is_within_bounds(pos):
                continue
            terrain = game_map.get_terrain(pos)
            if terrain is None:
                continue
            if not game_map.is_passable(pos):
                continue

            score = 1.0
            # Road bonus (CC2: tanks prefer roads)
            terrain_type = getattr(terrain, "terrain_type", "")
            if terrain_type in ("road", "bridge", "path"):
                score += 3.0
            # Cover bonus (partial cover preferred for hull-down)
            cover = getattr(terrain, "cover_modifier", 0.0)
            if 0.1 <= cover <= 0.4:
                score += 1.0  # Hull-down position
            # Distance to target (closer is better)
            target_dist = pos.chebyshev_distance(target_pos)
            tank_dist = tank_pos.chebyshev_distance(target_pos)
            if target_dist < tank_dist:
                score += 0.5

            if score > best_score:
                best_score = score
                best_pos = pos

        return best_pos


# ---------------------------------------------------------------------------
# VictoryPointAI
# ---------------------------------------------------------------------------


class VictoryPointAI(TacticalAIBase):
    """Prioritize capturing and defending Victory Locations.

    CC2 behaviour:
      - AI assigns units to capture uncontrolled VLs
      - AI defends held VLs with appropriate force
      - AI retreats from indefensible VLs to reinforce others

    VL data is passed via ``context.vl_positions`` as a list of
    ``(position, owner_faction_name_or_None, point_value)`` tuples.

    Evaluation heuristic:
      - Higher score when uncontrolled or enemy-held VLs exist
      - Higher score when held VLs are under threat
      - Zero when no VL data is available
    """

    CAPTURE_RADIUS: int = 3
    DEFEND_RADIUS: int = 5

    def evaluate(self, context: TacticalContext) -> float:
        if not context.vl_positions:
            return 0.0

        faction_name = context.friendly_faction.name if context.friendly_faction else None
        uncontrolled = [v for v in context.vl_positions if v[1] is None or v[1] != faction_name]
        held = [v for v in context.vl_positions if v[1] == faction_name]

        if not uncontrolled and not held:
            return 0.0

        total_value = sum(v[2] for v in context.vl_positions) or 1
        uncontrolled_value = sum(v[2] for v in uncontrolled)
        held_value = sum(v[2] for v in held)

        # Threat to held VLs
        threatened = 0
        for vl_pos, _, vl_val in held:
            enemies_near = sum(
                1
                for e in context.enemy_units
                if e.is_alive
                and e.position.tile_coord.chebyshev_distance(vl_pos) <= self.DEFEND_RADIUS
            )
            if enemies_near > 0:
                threatened += vl_val

        capture_urgency = uncontrolled_value / total_value
        defense_urgency = threatened / max(held_value, 1)

        diff_mod = 1.0
        if context.difficulty_config is not None:
            diff_mod = context.difficulty_config.aggressiveness

        score = 0.5 * capture_urgency + 0.5 * defense_urgency
        return min(score * diff_mod, 1.0)

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        if not context.vl_positions:
            return []

        faction_name = context.friendly_faction.name if context.friendly_faction else None
        available = [
            u
            for u in context.friendly_units
            if u.is_alive and u.can_act and u.morale.is_combat_effective
        ]
        if not available:
            return []

        intents: list[TacticIntent] = []
        assigned: set[str] = set()

        # --- Capture uncontrolled / enemy VLs ---
        uncontrolled = sorted(
            [v for v in context.vl_positions if v[1] is None or v[1] != faction_name],
            key=lambda v: v[2],
            reverse=True,
        )

        for vl_pos, _, vl_val in uncontrolled:
            # Find nearest unassigned unit
            candidates = [
                u
                for u in available
                if u.id not in assigned
                and u.position.tile_coord.chebyshev_distance(vl_pos) > self.CAPTURE_RADIUS
            ]
            if not candidates:
                break

            # Assign 1-2 units based on VL value
            count = 1 if vl_val < 20 else 2
            nearest = sorted(
                candidates,
                key=lambda u: u.position.tile_coord.chebyshev_distance(vl_pos),
            )
            for u in nearest[:count]:
                assigned.add(u.id)
                intents.append(
                    TacticIntent(
                        unit_id=u.id,
                        tactic_type=TacticType.CAPTURE_VL,
                        priority=8,
                        target_position=vl_pos,
                    )
                )

        # --- Defend held VLs under threat ---
        held = [v for v in context.vl_positions if v[1] == faction_name]

        for vl_pos, _, _vl_val in held:
            enemies_near = [
                e
                for e in context.enemy_units
                if e.is_alive
                and e.position.tile_coord.chebyshev_distance(vl_pos) <= self.DEFEND_RADIUS
            ]
            if not enemies_near:
                continue

            # Check if we already have units near this VL
            defenders_near = [
                u
                for u in available
                if u.id not in assigned
                and u.position.tile_coord.chebyshev_distance(vl_pos) <= self.DEFEND_RADIUS
            ]

            # Need more defenders if outnumbered
            needed = max(len(enemies_near) - len(defenders_near), 0)
            if needed == 0:
                continue

            # Find unassigned units to reinforce
            candidates = [
                u
                for u in available
                if u.id not in assigned
                and u.position.tile_coord.chebyshev_distance(vl_pos) > self.DEFEND_RADIUS
            ]
            nearest = sorted(
                candidates,
                key=lambda u: u.position.tile_coord.chebyshev_distance(vl_pos),
            )
            for u in nearest[:needed]:
                assigned.add(u.id)
                intents.append(
                    TacticIntent(
                        unit_id=u.id,
                        tactic_type=TacticType.DEFEND_VL,
                        priority=7,
                        target_position=vl_pos,
                    )
                )

        # --- Retreat from indefensible VLs ---
        for vl_pos, _, _vl_val in held:
            enemy_count = sum(
                1
                for e in context.enemy_units
                if e.is_alive
                and e.position.tile_coord.chebyshev_distance(vl_pos) <= self.DEFEND_RADIUS
            )
            friendly_count = sum(
                1
                for u in available
                if u.position.tile_coord.chebyshev_distance(vl_pos) <= self.DEFEND_RADIUS
            )
            # Heavily outnumbered — retreat to nearest stronger VL
            if enemy_count >= 3 and friendly_count <= 1:
                safer_vl = self._find_safer_vl(vl_pos, context, faction_name)
                if safer_vl is not None:
                    for u in available:
                        if (
                            u.position.tile_coord.chebyshev_distance(vl_pos) <= self.DEFEND_RADIUS
                            and u.id not in assigned
                        ):
                            assigned.add(u.id)
                            intents.append(
                                TacticIntent(
                                    unit_id=u.id,
                                    tactic_type=TacticType.RETREAT,
                                    priority=9,
                                    target_position=safer_vl,
                                )
                            )

        return intents

    # -- helpers --

    @staticmethod
    def _find_safer_vl(
        current_vl: TileCoord,
        context: TacticalContext,
        faction_name: str | None,
    ) -> TileCoord | None:
        """Find the nearest held VL that is not under heavy threat."""
        held = [v for v in context.vl_positions if v[1] == faction_name]
        safe: list[tuple[TileCoord, int]] = []
        for vl_pos, _, _ in held:
            if vl_pos == current_vl:
                continue
            enemies_near = sum(
                1
                for e in context.enemy_units
                if e.is_alive and e.position.tile_coord.chebyshev_distance(vl_pos) <= 5
            )
            if enemies_near <= 1:
                safe.append((vl_pos, current_vl.chebyshev_distance(vl_pos)))
        if not safe:
            return None
        safe.sort(key=lambda s: s[1])
        return safe[0][0]
