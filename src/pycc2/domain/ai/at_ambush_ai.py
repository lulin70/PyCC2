"""ATAmbushAI — Anti-Tank Ambush Tactics

Implements CC2-authentic anti-tank ambush behavior:

  1. Identify enemy tanks/vehicles and their likely routes
  2. Position AT units in ambush positions along likely tank routes
  3. AT units hold fire until tanks are within effective range
  4. After first shot, AT units may reposition if still concealed

Evaluation heuristic:
  - Returns 0.0 if no enemy tanks/vehicles exist
  - Returns 0.0 if no friendly AT units exist
  - Higher score when enemy tanks are approaching (within 15 tiles)
  - Higher score when AT units are in good ambush positions
  - Lower score when AT units are already engaged
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalAIBase, TacticalContext
from pycc2.domain.entities.unit import UnitType
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ARMOR_TYPES: set[UnitType] = {UnitType.TANK}

_AT_WEAPON_IDS: set[str] = {"at_gun", "piat", "pak40", "bazooka", "panzerschreck"}

_APPROACH_RADIUS: int = 15

_AMBUSH_COVER_TYPES: set[TerrainType] = {
    TerrainType.WOODS,
    TerrainType.BUILDING_ENTERABLE,
    TerrainType.HEDGE,
    TerrainType.CRATER,
    TerrainType.ROUGH,
}

_TANK_ROUTE_TERRAIN: set[TerrainType] = {
    TerrainType.OPEN,
    TerrainType.ROAD,
    TerrainType.GRASS,
    TerrainType.BRIDGE,
    TerrainType.ROUGH,
}

_WEAPON_RANGE: dict[str, int] = {
    "piat": 8,
    "pak40": 12,
    "at_gun": 12,
    "bazooka": 8,
    "panzerschreck": 8,
}

_DEFAULT_AT_RANGE: int = 10


# ---------------------------------------------------------------------------
# ATAmbushAI
# ---------------------------------------------------------------------------


class ATAmbushAI(TacticalAIBase):
    """Anti-tank ambush tactical AI.

    Positions AT units in concealed locations along likely tank routes
    and coordinates ambush fire when enemy armor enters effective range.
    """

    # -- evaluate -----------------------------------------------------------

    def evaluate(self, context: TacticalContext) -> float:
        """Return ambush priority based on AT units, enemy armor proximity, and readiness."""
        at_units = self._find_at_units(context)
        enemy_armor = self._find_enemy_armor(context)

        if not at_units or not enemy_armor:
            return 0.0

        # Proximity factor: closer tanks → higher urgency
        closest_dist = min(
            at.position.tile_coord.chebyshev_distance(tank.position.tile_coord)
            for at in at_units
            for tank in enemy_armor
        )
        if closest_dist <= _APPROACH_RADIUS:
            proximity = 1.0 - (closest_dist / _APPROACH_RADIUS)
        else:
            proximity = 0.0

        # Ambush readiness: fraction of AT units already in good positions
        in_ambush = sum(1 for u in at_units if self._is_in_ambush_position(u, context))
        readiness = in_ambush / max(len(at_units), 1)

        # Engagement penalty: AT units already fighting are less available
        engaged = sum(1 for u in at_units if self._is_engaged(u, context))
        engagement_penalty = engaged / max(len(at_units), 1)

        score = 0.45 * proximity + 0.35 * readiness + 0.20 * 0.5
        score -= 0.3 * engagement_penalty

        diff_mod = 1.0
        if context.difficulty_config is not None:
            diff_mod = context.difficulty_config.aggressiveness

        return max(0.0, min(score * diff_mod, 1.0))

    # -- execute ------------------------------------------------------------

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Generate ambush intents for AT units engaging enemy armor."""
        at_units = self._find_at_units(context)
        enemy_armor = self._find_enemy_armor(context)

        if not at_units or not enemy_armor:
            return []

        intents: list[TacticIntent] = []
        assigned_targets: dict[str, str] = {}

        # Phase 1: Predict tank routes
        tank_routes: dict[str, list[TileCoord]] = {}
        for tank in enemy_armor:
            tank_routes[tank.id] = self._predict_tank_route(tank, context)

        # Phase 2 & 3: Position AT units and determine fire orders
        for at_unit in at_units:
            if not at_unit.can_act:
                continue

            # Find the best tank target for this AT unit
            best_tank = self._best_target_for(at_unit, enemy_armor, context)
            if best_tank is None:
                continue

            eff_range = self._effective_at_range(at_unit)
            dist = at_unit.position.tile_coord.chebyshev_distance(best_tank.position.tile_coord)

            # Check if AT unit is already in a good ambush position
            if self._is_in_ambush_position(at_unit, context):
                # Phase 3: Hold fire until tank is within effective range
                if dist <= eff_range and context.game_map.has_line_of_sight(
                    at_unit.position.tile_coord, best_tank.position.tile_coord
                ):
                    # Fire! Attack the tank
                    intents.append(
                        TacticIntent(
                            unit_id=at_unit.id,
                            tactic_type=TacticType.ATTACK,
                            priority=9,
                            target_unit_id=best_tank.id,
                            target_position=best_tank.position.tile_coord,
                        )
                    )
                    assigned_targets[at_unit.id] = best_tank.id
                else:
                    # Hold position — wait for tank to come into range
                    intents.append(
                        TacticIntent(
                            unit_id=at_unit.id,
                            tactic_type=TacticType.HOLD_POSITION,
                            priority=7,
                            target_position=at_unit.position.tile_coord,
                        )
                    )
            else:
                # Phase 2: Move to ambush position along likely tank route
                route = tank_routes.get(best_tank.id, [])
                ambush_pos = self._find_ambush_position(at_unit, route, context)
                if ambush_pos is not None:
                    intents.append(
                        TacticIntent(
                            unit_id=at_unit.id,
                            tactic_type=TacticType.MOVE_TO,
                            priority=8,
                            target_position=ambush_pos,
                        )
                    )
                else:
                    # No good ambush found — hold current position
                    intents.append(
                        TacticIntent(
                            unit_id=at_unit.id,
                            tactic_type=TacticType.HOLD_POSITION,
                            priority=5,
                            target_position=at_unit.position.tile_coord,
                        )
                    )

        # Phase 4: After engagement, check if repositioning is needed
        for at_unit in at_units:
            if at_unit.id in assigned_targets and not self._has_concealment(at_unit, context):
                # Find a nearby concealed position
                reposition = self._find_nearby_concealment(at_unit, context)
                if reposition is not None:
                    intents.append(
                        TacticIntent(
                            unit_id=at_unit.id,
                            tactic_type=TacticType.TAKE_COVER,
                            priority=6,
                            target_position=reposition,
                        )
                    )

        return intents

    # -- helper methods -----------------------------------------------------

    @staticmethod
    def _find_at_units(context: TacticalContext) -> list[Unit]:
        """Find friendly AT units (AT_GUN_TEAM or units with AT weapons)."""
        result: list[Unit] = []
        for u in context.friendly_units:
            if not u.is_alive or not u.can_act:
                continue
            if u.unit_type == UnitType.AT_GUN_TEAM or u.weapon.primary_weapon_id in _AT_WEAPON_IDS:
                result.append(u)
        return result

    @staticmethod
    def _find_enemy_armor(context: TacticalContext) -> list[Unit]:
        """Find enemy tanks and vehicles."""
        return [u for u in context.enemy_units if u.is_alive and u.unit_type in _ARMOR_TYPES]

    @staticmethod
    def _predict_tank_route(tank: Unit, context: TacticalContext) -> list[TileCoord]:
        """Predict likely tank movement path based on terrain.

        Tanks prefer roads and open terrain. The route extends forward
        from the tank's current position toward the nearest VL or the
        center of the map.
        """
        start = tank.position.tile_coord
        game_map = context.game_map

        # Determine direction: toward nearest VL or map center
        target = TileCoord(game_map.width // 2, game_map.height // 2)
        if context.vl_positions:
            nearest_vl = min(
                context.vl_positions,
                key=lambda v: start.chebyshev_distance(v[0]),
            )
            target = nearest_vl[0]

        route: list[TileCoord] = [start]
        current = start
        visited: set[tuple[int, int]] = {(current.x, current.y)}

        for _ in range(20):
            neighbors = current.neighbors_8
            best_next: TileCoord | None = None
            best_score = float("inf")

            for n in neighbors:
                if not game_map.is_within_bounds(n):
                    continue
                if (n.x, n.y) in visited:
                    continue
                if not game_map.is_passable(n):
                    continue

                terrain = game_map.get_terrain(n)
                # Tank-preferred terrain gets lower cost
                terrain_cost = terrain.movement_cost if terrain in _TANK_ROUTE_TERRAIN else 5.0

                # Distance to target
                dist_to_target = n.chebyshev_distance(target)
                score = dist_to_target + terrain_cost * 0.5

                if score < best_score:
                    best_score = score
                    best_next = n

            if best_next is None:
                break

            route.append(best_next)
            visited.add((best_next.x, best_next.y))
            current = best_next

            if current == target:
                break

        return route

    @staticmethod
    def _find_ambush_position(
        at_unit: Unit, tank_route: list[TileCoord], context: TacticalContext
    ) -> TileCoord | None:
        """Find the best ambush spot near a predicted tank route.

        Prefers positions with cover and concealment that have LOS
        to the route and are within effective AT range.
        """
        if not tank_route:
            return None

        eff_range = ATAmbushAI._effective_at_range(at_unit)
        game_map = context.game_map
        at_pos = at_unit.position.tile_coord

        best_pos: TileCoord | None = None
        best_score = -1.0

        # Search around each point on the tank route
        for route_point in tank_route:
            # Check positions within effective range of this route point
            search_radius = eff_range
            for dy in range(-search_radius, search_radius + 1):
                for dx in range(-search_radius, search_radius + 1):
                    candidate = TileCoord(route_point.x + dx, route_point.y + dy)
                    if not game_map.is_within_bounds(candidate):
                        continue
                    if not game_map.is_passable(candidate):
                        continue

                    # Must have LOS to the route point
                    if not game_map.has_line_of_sight(candidate, route_point):
                        continue

                    # Must be within effective range of the route point
                    dist_to_route = candidate.chebyshev_distance(route_point)
                    if dist_to_route > eff_range:
                        continue

                    # Score: cover + concealment + proximity to AT unit
                    terrain = game_map.get_terrain(candidate)
                    cover = terrain.cover_bonus
                    concealment = terrain.concealment_modifier

                    # Prefer positions closer to the AT unit (less movement)
                    dist_from_at = candidate.chebyshev_distance(at_pos)
                    proximity_bonus = max(0.0, 1.0 - dist_from_at / 20.0)

                    score = cover * 0.4 + concealment * 0.4 + proximity_bonus * 0.2

                    if score > best_score:
                        best_score = score
                        best_pos = candidate

        return best_pos

    @staticmethod
    def _is_in_ambush_position(unit: Unit, context: TacticalContext) -> bool:
        """Check if a unit is already in a good ambush spot.

        A good ambush position has cover and concealment.
        """
        pos = unit.position.tile_coord
        game_map = context.game_map

        if not game_map.is_within_bounds(pos):
            return False

        terrain = game_map.get_terrain(pos)
        has_cover = terrain.cover_bonus >= 0.15
        has_concealment = terrain.concealment_modifier >= 0.20

        return has_cover and has_concealment

    @staticmethod
    def _effective_at_range(at_unit: Unit) -> int:
        """Return effective range based on weapon type."""
        weapon_id = at_unit.weapon.primary_weapon_id
        return _WEAPON_RANGE.get(weapon_id, _DEFAULT_AT_RANGE)

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _is_engaged(unit: Unit, context: TacticalContext) -> bool:
        """Check if a unit is currently engaged in combat."""
        bb = context.blackboards.get(unit.id)
        if bb is not None and bb.get_current_intent() is not None:
            return True
        # Also check suppression as a sign of being engaged
        return unit.morale.suppression > 0

    @staticmethod
    def _has_concealment(unit: Unit, context: TacticalContext) -> bool:
        """Check if a unit has concealment at its current position."""
        pos = unit.position.tile_coord
        game_map = context.game_map
        if not game_map.is_within_bounds(pos):
            return False
        terrain = game_map.get_terrain(pos)
        return terrain.concealment_modifier >= 0.20

    @staticmethod
    def _find_nearby_concealment(unit: Unit, context: TacticalContext) -> TileCoord | None:
        """Find a nearby concealed position for repositioning after firing."""
        pos = unit.position.tile_coord
        game_map = context.game_map

        best: TileCoord | None = None
        best_score = -1.0

        for dy in range(-5, 6):
            for dx in range(-5, 6):
                if dx == 0 and dy == 0:
                    continue
                candidate = TileCoord(pos.x + dx, pos.y + dy)
                if not game_map.is_within_bounds(candidate):
                    continue
                if not game_map.is_passable(candidate):
                    continue

                terrain = game_map.get_terrain(candidate)
                concealment = terrain.concealment_modifier
                cover = terrain.cover_bonus
                dist = abs(dx) + abs(dy)

                if concealment < 0.20:
                    continue

                score = concealment * 0.5 + cover * 0.3 - dist * 0.05
                if score > best_score:
                    best_score = score
                    best = candidate

        return best

    @staticmethod
    def _best_target_for(
        at_unit: Unit, enemy_armor: list[Unit], context: TacticalContext
    ) -> Unit | None:
        """Select the best tank target for an AT unit.

        Prefers the closest tank that the AT unit can engage.
        """
        best: Unit | None = None
        best_dist = float("inf")

        for tank in enemy_armor:
            dist = at_unit.position.tile_coord.chebyshev_distance(tank.position.tile_coord)
            eff_range = ATAmbushAI._effective_at_range(at_unit)

            # Prefer tanks within or approaching effective range
            if (
                dist <= eff_range * 1.5
                and dist < best_dist
                and context.game_map.has_line_of_sight(
                    at_unit.position.tile_coord, tank.position.tile_coord
                )
            ):
                best_dist = dist
                best = tank

        # If no tank in range with LOS, pick the closest overall
        if best is None and enemy_armor:
            best = min(
                enemy_armor,
                key=lambda t: at_unit.position.tile_coord.chebyshev_distance(t.position.tile_coord),
            )

        return best
