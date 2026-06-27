"""SmokeTacticalAI — Active Smoke Screen Usage for CC2 Fidelity

Implements CC2-authentic smoke screen tactics:

  1. SmokeTacticalAI   — Evaluates when to deploy smoke and issues orders
  2. SmokeDeployment   — Dataclass tracking an active smoke cloud
  3. SmokeManager      — Manages all active smoke deployments on the battlefield
  4. SmokeGrenadeCapability — Tracks smoke grenade/round availability per unit

Evaluation triggers:
  - Friendly units SUPPRESSED in open terrain
  - Friendly units crossing a bridge/road under enemy LOS
  - Covering a retreat (RetreatDecisionAI is active)
  - Screening tank movement past AT positions

Smoke properties (CC2-authentic):
  - Duration: 180 ticks (~30 seconds at 6 ticks/sec)
  - Radius: 3 tiles
  - Drift: 1 tile per 60 ticks in wind direction
  - Blocks LOS completely within radius
  - Reduces accuracy by 50% for units shooting through smoke
"""

from __future__ import annotations

import math
from dataclasses import dataclass
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

_OPEN_TERRAIN: set[TerrainType] = {
    TerrainType.OPEN,
    TerrainType.ROAD,
    TerrainType.GRASS,
    TerrainType.BRIDGE,
}

_DANGER_ZONE_TERRAIN: set[TerrainType] = {
    TerrainType.BRIDGE,
    TerrainType.ROAD,
}

_ARMOR_TYPES: set[UnitType] = {UnitType.TANK}

_AT_TYPES: set[UnitType] = {UnitType.AT_GUN_TEAM}

_SMOKE_CAPABLE_TYPES: set[UnitType] = {
    UnitType.INFANTRY_SQUAD,
    UnitType.MORTAR_TEAM,
    UnitType.COMMANDER,
}

# Smoke grenade weapon IDs (units carrying smoke capability)
_SMOKE_WEAPON_IDS: set[str] = {"smoke_grenade", "smoke_mortar"}

# German Nebeltrupp (smoke troop) — extra smoke capacity
_NEBELTRUPP_WEAPON_ID: str = "nebeltrupp_smoke"


# ---------------------------------------------------------------------------
# SmokeDeployment
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SmokeDeployment:
    """Tracks an active smoke cloud on the battlefield."""

    position: tuple[int, int]
    radius: int = 3
    duration_ticks: int = 180
    remaining_ticks: int = 180
    drift_direction: tuple[int, int] = (0, 0)  # wind direction (dx, dy) per drift
    deployed_by: str = ""  # unit_id

    # Drift timing: smoke drifts 1 tile every 60 ticks
    DRIFT_INTERVAL: int = 60

    def tick(self) -> None:
        """Advance smoke by one tick: decay duration and apply drift."""
        self.remaining_ticks -= 1
        if self.remaining_ticks > 0 and self.duration_ticks > 0:
            elapsed = self.duration_ticks - self.remaining_ticks
            if elapsed > 0 and elapsed % self.DRIFT_INTERVAL == 0:
                x, y = self.position
                dx, dy = self.drift_direction
                self.position = (x + dx, y + dy)

    @property
    def is_expired(self) -> bool:
        return self.remaining_ticks <= 0

    def contains(self, pos: tuple[int, int]) -> bool:
        """Check if a position is within the smoke radius (Chebyshev)."""
        sx, sy = self.position
        px, py = pos
        return max(abs(sx - px), abs(sy - py)) <= self.radius


# ---------------------------------------------------------------------------
# SmokeManager
# ---------------------------------------------------------------------------


class SmokeManager:
    """Manages all active smoke deployments on the battlefield.

    Responsibilities:
      - Track all active smoke deployments
      - Update smoke positions (drift) each tick
      - Remove expired smoke
      - Query whether a position is in smoke
      - Integration with ConcealmentProfile.in_smoke
    """

    def __init__(self) -> None:
        """Initialize the smoke manager with an empty deployment list."""
        self._deployments: list[SmokeDeployment] = []

    @property
    def active_deployments(self) -> list[SmokeDeployment]:
        return list(self._deployments)

    def deploy(self, smoke: SmokeDeployment) -> None:
        """Add a new smoke deployment to the battlefield."""
        self._deployments.append(smoke)

    def tick(self) -> None:
        """Advance all smoke deployments by one tick and remove expired ones."""
        for smoke in self._deployments:
            smoke.tick()
        self._deployments = [s for s in self._deployments if not s.is_expired]

    def is_position_in_smoke(self, pos: tuple[int, int]) -> bool:
        """Check if a position is obscured by any active smoke cloud."""
        return any(s.contains(pos) for s in self._deployments)

    def get_smoke_at(self, pos: tuple[int, int]) -> list[SmokeDeployment]:
        """Return all smoke deployments covering the given position."""
        return [s for s in self._deployments if s.contains(pos)]

    def blocks_los(self, pos_a: tuple[int, int], pos_b: tuple[int, int]) -> bool:
        """Check if any smoke cloud blocks LOS between two positions.

        A smoke cloud blocks LOS if the line between the two positions
        passes through the cloud's radius.
        """
        return any(self._line_intersects_smoke(pos_a, pos_b, smoke) for smoke in self._deployments)

    @staticmethod
    def _line_intersects_smoke(
        pos_a: tuple[int, int],
        pos_b: tuple[int, int],
        smoke: SmokeDeployment,
    ) -> bool:
        """Check if the line segment from pos_a to pos_b intersects the smoke."""
        ax, ay = pos_a
        bx, by = pos_b
        sx, sy = smoke.position

        # If either endpoint is inside the smoke, LOS is blocked
        if smoke.contains(pos_a) or smoke.contains(pos_b):
            return True

        # Sample points along the line and check if any fall within the smoke
        dx = bx - ax
        dy = by - ay
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1.0:
            return False

        steps = max(int(length), 1)
        for i in range(1, steps):
            t = i / steps
            px = ax + dx * t
            py = ay + dy * t
            if max(abs(px - sx), abs(py - sy)) <= smoke.radius:
                return True

        return False

    def accuracy_modifier_through_smoke(
        self,
        pos_a: tuple[int, int],
        pos_b: tuple[int, int],
    ) -> float:
        """Return accuracy modifier for shots from pos_a to pos_b.

        Returns 0.5 (50% reduction) if any smoke blocks the LOS,
        otherwise 1.0 (no penalty).
        """
        if self.blocks_los(pos_a, pos_b):
            return 0.5
        return 1.0


# ---------------------------------------------------------------------------
# SmokeGrenadeCapability
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SmokeGrenadeCapability:
    """Tracks smoke grenade/round availability for a unit.

    Infantry squads carry 2 smoke grenades each.
    Mortar teams can fire smoke rounds (separate from HE).
    German Nebeltrupp (smoke troop) carries extra smoke grenades.
    """

    smoke_count: int = 0
    max_smoke: int = 0
    is_mortar_smoke: bool = False  # True for mortar smoke rounds

    @property
    def has_smoke(self) -> bool:
        return self.smoke_count > 0

    def use_smoke(self) -> bool:
        """Consume one smoke charge. Returns True if successful."""
        if self.smoke_count <= 0:
            return False
        self.smoke_count -= 1
        return True

    @classmethod
    def for_infantry_squad(cls) -> SmokeGrenadeCapability:
        """Standard infantry squad: 2 smoke grenades."""
        return cls(smoke_count=2, max_smoke=2, is_mortar_smoke=False)

    @classmethod
    def for_mortar_team(cls) -> SmokeGrenadeCapability:
        """Mortar team: 3 smoke rounds (separate from HE)."""
        return cls(smoke_count=3, max_smoke=3, is_mortar_smoke=True)

    @classmethod
    def for_nebeltrupp(cls) -> SmokeGrenadeCapability:
        """German Nebeltrupp (smoke troop): 6 smoke grenades."""
        return cls(smoke_count=6, max_smoke=6, is_mortar_smoke=False)


# ---------------------------------------------------------------------------
# SmokeTacticalAI
# ---------------------------------------------------------------------------


class SmokeTacticalAI(TacticalAIBase):
    """Evaluate when to deploy smoke screens and issue deployment orders.

    CC2 behaviour: AI uses smoke to cover movement through open ground,
    protect units crossing danger zones, screen retreats, and mask tank
    movements past AT positions.

    Evaluation heuristic:
      - Base: 0.0
      - +0.3 if friendly units are SUPPRESSED in open terrain
      - +0.4 if friendly units need to cross a bridge/road under enemy LOS
      - +0.2 if covering retreat (RetreatDecisionAI is active)
      - +0.3 if tank needs to pass AT position
      - -0.2 if no smoke-capable units available
      - -0.3 if wind would blow smoke away from intended position
    """

    SMOKE_RADIUS: int = 3
    SMOKE_DURATION: int = 180
    DRIFT_INTERVAL: int = 60

    def evaluate(self, context: TacticalContext) -> float:
        score = 0.0

        friendly_alive = [u for u in context.friendly_units if u.is_alive]
        enemies_alive = [e for e in context.enemy_units if e.is_alive]
        if not friendly_alive or not enemies_alive:
            return 0.0

        # +0.3 if friendly units are SUPPRESSED in open terrain
        if self._has_suppressed_in_open(context):
            score += 0.3

        # +0.4 if friendly units need to cross a bridge/road under enemy LOS
        if self._needs_crossing_under_fire(context):
            score += 0.4

        # +0.2 if covering retreat (RetreatDecisionAI is active)
        if self._is_retreat_active(context):
            score += 0.2

        # +0.3 if tank needs to pass AT position
        if self._tank_needs_smoke_past_at(context):
            score += 0.3

        # -0.2 if no smoke-capable units available
        smoke_units = self._smoke_capable_units(context)
        if not smoke_units:
            score -= 0.2

        # -0.3 if wind would blow smoke away from intended position
        if self._wind_adverse(context):
            score -= 0.3

        # Difficulty modifier
        diff_mod = 1.0
        if context.difficulty_config is not None:
            diff_mod = context.difficulty_config.aggressiveness

        return max(0.0, min(score * diff_mod, 1.0))

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        smoke_units = self._smoke_capable_units(context)
        if not smoke_units:
            return []

        intents: list[TacticIntent] = []
        assigned: set[str] = set()

        # Priority 1: Cover suppressed units in open terrain
        for target in self._suppressed_in_open_units(context):
            if target.id in assigned:
                continue
            deployer = self._best_deployer_for(smoke_units, target, assigned)
            if deployer is None:
                continue
            assigned.add(deployer.id)
            smoke_pos = self._calculate_smoke_position(deployer, target, context)
            intents.append(
                TacticIntent(
                    unit_id=deployer.id,
                    tactic_type=TacticType.DEPLOY_SMOKE,
                    priority=8,
                    target_position=smoke_pos,
                )
            )

        # Priority 2: Cover units crossing danger zones
        for target in self._units_crossing_danger_zone(context):
            if target.id in assigned:
                continue
            deployer = self._best_deployer_for(smoke_units, target, assigned)
            if deployer is None:
                continue
            assigned.add(deployer.id)
            smoke_pos = self._calculate_smoke_position(deployer, target, context)
            intents.append(
                TacticIntent(
                    unit_id=deployer.id,
                    tactic_type=TacticType.DEPLOY_SMOKE,
                    priority=9,
                    target_position=smoke_pos,
                )
            )

        # Priority 3: Screen tanks past AT positions
        for tank in self._tanks_near_at(context):
            if tank.id in assigned:
                continue
            deployer = self._best_deployer_for(smoke_units, tank, assigned)
            if deployer is None:
                continue
            assigned.add(deployer.id)
            # Place smoke between tank and nearest AT
            nearest_at = self._nearest_at_to(tank, context)
            if nearest_at is not None:
                smoke_pos = self._midpoint_smoke_position(
                    tank.position.tile_coord,
                    nearest_at.position.tile_coord,
                    context,
                )
            else:
                smoke_pos = self._calculate_smoke_position(deployer, tank, context)
            intents.append(
                TacticIntent(
                    unit_id=deployer.id,
                    tactic_type=TacticType.DEPLOY_SMOKE,
                    priority=8,
                    target_position=smoke_pos,
                )
            )

        # Priority 4: Cover retreat
        if self._is_retreat_active(context):
            retreat_units = self._retreating_units(context)
            for target in retreat_units:
                if target.id in assigned:
                    continue
                deployer = self._best_deployer_for(smoke_units, target, assigned)
                if deployer is None:
                    continue
                assigned.add(deployer.id)
                smoke_pos = self._calculate_smoke_position(deployer, target, context)
                intents.append(
                    TacticIntent(
                        unit_id=deployer.id,
                        tactic_type=TacticType.DEPLOY_SMOKE,
                        priority=7,
                        target_position=smoke_pos,
                    )
                )

        return intents

    # ------------------------------------------------------------------
    # Evaluate helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _has_suppressed_in_open(context: TacticalContext) -> bool:
        """Check if any friendly unit is suppressed in open terrain."""
        for u in context.friendly_units:
            if not u.is_alive:
                continue
            pos = u.position.tile_coord
            game_map = context.game_map
            if not game_map.is_within_bounds(pos):
                continue
            terrain = game_map.get_terrain(pos)
            if terrain not in _OPEN_TERRAIN:
                continue
            if u.morale.suppression > 0:
                return True
            # Also check combat_state suppression
            combat_state = getattr(u, "combat_state", None)
            if combat_state is not None:
                supp = getattr(combat_state, "suppression", None)
                if supp is not None and getattr(supp, "current_suppression", 0) > 25:
                    return True
        return False

    @staticmethod
    def _needs_crossing_under_fire(context: TacticalContext) -> bool:
        """Check if friendly units need to cross a bridge/road under enemy LOS."""
        for u in context.friendly_units:
            if not u.is_alive or not u.can_act:
                continue
            pos = u.position.tile_coord
            game_map = context.game_map
            if not game_map.is_within_bounds(pos):
                continue
            terrain = game_map.get_terrain(pos)
            if terrain not in _DANGER_ZONE_TERRAIN:
                continue
            # Check if any enemy has LOS to this position
            for e in context.enemy_units:
                if not e.is_alive:
                    continue
                if hasattr(game_map, "has_line_of_sight"):
                    if game_map.has_line_of_sight(e.position.tile_coord, pos):
                        return True
                else:
                    dist = e.position.tile_coord.chebyshev_distance(pos)
                    if dist <= 10:
                        return True
        return False

    @staticmethod
    def _is_retreat_active(context: TacticalContext) -> bool:
        """Check if RetreatDecisionAI is active by examining blackboards."""
        return any(bb.get("retreat_active", False) for bb in context.blackboards.values())

    @staticmethod
    def _tank_needs_smoke_past_at(context: TacticalContext) -> bool:
        """Check if a friendly tank needs to pass near an AT position."""
        tanks = [u for u in context.friendly_units if u.is_alive and u.unit_type in _ARMOR_TYPES]
        at_units = [e for e in context.enemy_units if e.is_alive and e.unit_type in _AT_TYPES]
        if not tanks or not at_units:
            return False
        for tank in tanks:
            for at in at_units:
                dist = tank.position.tile_coord.chebyshev_distance(at.position.tile_coord)
                if dist <= 12:
                    return True
        return False

    @staticmethod
    def _wind_adverse(context: TacticalContext) -> bool:
        """Check if wind would blow smoke away from intended position.

        Uses environment wind data if available; otherwise returns False.
        """
        env = getattr(context, "environment", None)
        if env is None:
            return False
        getattr(env, "wind_direction", (0, 0))
        wind_speed = getattr(env, "wind_speed", 0)
        # If wind speed is significant (> 2), smoke drifts noticeably
        return wind_speed > 2

    # ------------------------------------------------------------------
    # Execute helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _smoke_capable_units(context: TacticalContext) -> list[Unit]:
        """Find friendly units capable of deploying smoke."""
        result: list[Unit] = []
        for u in context.friendly_units:
            if not u.is_alive or not u.can_act:
                continue
            if u.unit_type in _SMOKE_CAPABLE_TYPES:
                result.append(u)
                continue
            # Check weapon for smoke capability
            weapon_id = u.weapon.primary_weapon_id
            if weapon_id in _SMOKE_WEAPON_IDS or weapon_id == _NEBELTRUPP_WEAPON_ID:
                result.append(u)
        return result

    @staticmethod
    def _suppressed_in_open_units(context: TacticalContext) -> list[Unit]:
        """Find friendly units that are suppressed in open terrain."""
        result: list[Unit] = []
        for u in context.friendly_units:
            if not u.is_alive:
                continue
            pos = u.position.tile_coord
            game_map = context.game_map
            if not game_map.is_within_bounds(pos):
                continue
            terrain = game_map.get_terrain(pos)
            if terrain not in _OPEN_TERRAIN:
                continue
            if u.morale.suppression > 0:
                result.append(u)
                continue
            combat_state = getattr(u, "combat_state", None)
            if combat_state is not None:
                supp = getattr(combat_state, "suppression", None)
                if supp is not None and getattr(supp, "current_suppression", 0) > 25:
                    result.append(u)
        return result

    @staticmethod
    def _units_crossing_danger_zone(context: TacticalContext) -> list[Unit]:
        """Find friendly units on bridge/road terrain under enemy LOS."""
        result: list[Unit] = []
        for u in context.friendly_units:
            if not u.is_alive or not u.can_act:
                continue
            pos = u.position.tile_coord
            game_map = context.game_map
            if not game_map.is_within_bounds(pos):
                continue
            terrain = game_map.get_terrain(pos)
            if terrain not in _DANGER_ZONE_TERRAIN:
                continue
            for e in context.enemy_units:
                if not e.is_alive:
                    continue
                if hasattr(game_map, "has_line_of_sight"):
                    if game_map.has_line_of_sight(e.position.tile_coord, pos):
                        result.append(u)
                        break
                else:
                    dist = e.position.tile_coord.chebyshev_distance(pos)
                    if dist <= 10:
                        result.append(u)
                        break
        return result

    @staticmethod
    def _tanks_near_at(context: TacticalContext) -> list[Unit]:
        """Find friendly tanks near enemy AT positions."""
        result: list[Unit] = []
        for u in context.friendly_units:
            if not u.is_alive or u.unit_type not in _ARMOR_TYPES:
                continue
            for e in context.enemy_units:
                if not e.is_alive or e.unit_type not in _AT_TYPES:
                    continue
                dist = u.position.tile_coord.chebyshev_distance(e.position.tile_coord)
                if dist <= 12:
                    result.append(u)
                    break
        return result

    @staticmethod
    def _nearest_at_to(tank: Unit, context: TacticalContext) -> Unit | None:
        """Find the nearest enemy AT unit to a tank."""
        at_units = [e for e in context.enemy_units if e.is_alive and e.unit_type in _AT_TYPES]
        if not at_units:
            return None
        return min(
            at_units,
            key=lambda e: tank.position.tile_coord.chebyshev_distance(e.position.tile_coord),
        )

    @staticmethod
    def _retreating_units(context: TacticalContext) -> list[Unit]:
        """Find friendly units that are retreating."""
        result: list[Unit] = []
        for u in context.friendly_units:
            if not u.is_alive:
                continue
            bb = context.blackboards.get(u.id)
            if bb is not None and bb.get("is_retreating", False):
                result.append(u)
        return result

    @staticmethod
    def _best_deployer_for(
        deployers: list[Unit],
        target: Unit,
        assigned: set[str],
    ) -> Unit | None:
        """Select the best smoke-capable unit to deploy smoke for a target.

        Prefers the closest unassigned deployer to the target.
        """
        candidates = [d for d in deployers if d.id not in assigned]
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda d: d.position.tile_coord.chebyshev_distance(target.position.tile_coord),
        )

    def _calculate_smoke_position(
        self,
        deployer: Unit,
        target: Unit,
        context: TacticalContext,
    ) -> TileCoord:
        """Calculate optimal smoke placement position.

        Places smoke between friendly units and enemy fire,
        covering the movement path, and downwind if possible.
        """
        target_pos = target.position.tile_coord

        # Find the nearest enemy that threatens the target
        nearest_enemy = self._nearest_enemy_to(target, context)
        if nearest_enemy is not None:
            enemy_pos = nearest_enemy.position.tile_coord
            # Place smoke between the target and the enemy
            mid_x = (target_pos.x + enemy_pos.x) // 2
            mid_y = (target_pos.y + enemy_pos.y) // 2
            # Bias slightly toward the target to ensure coverage
            dx = target_pos.x - enemy_pos.x
            dy = target_pos.y - enemy_pos.y
            length = math.sqrt(dx * dx + dy * dy) or 1.0
            bias_x = int(mid_x + dx / length * 1)
            bias_y = int(mid_y + dy / length * 1)
            smoke_pos = TileCoord(bias_x, bias_y)
        else:
            # No specific enemy — place smoke near the target
            smoke_pos = TileCoord(target_pos.x, target_pos.y)

        # Adjust for wind: shift smoke downwind so it drifts over the target
        wind_dir = self._get_wind_direction(context)
        if wind_dir != (0, 0):
            wx, wy = wind_dir
            # Place smoke upwind of the intended position so drift carries it
            smoke_pos = TileCoord(smoke_pos.x - wx, smoke_pos.y - wy)

        # Ensure within map bounds
        game_map = context.game_map
        if not game_map.is_within_bounds(smoke_pos):
            smoke_pos = TileCoord(
                max(0, min(game_map.width - 1, smoke_pos.x)),
                max(0, min(game_map.height - 1, smoke_pos.y)),
            )

        return smoke_pos

    @staticmethod
    def _midpoint_smoke_position(
        pos_a: TileCoord,
        pos_b: TileCoord,
        context: TacticalContext,
    ) -> TileCoord:
        """Place smoke at the midpoint between two positions."""
        mid_x = (pos_a.x + pos_b.x) // 2
        mid_y = (pos_a.y + pos_b.y) // 2
        return TileCoord(mid_x, mid_y)

    @staticmethod
    def _nearest_enemy_to(unit: Unit, context: TacticalContext) -> Unit | None:
        """Find the nearest alive enemy to a unit."""
        enemies = [e for e in context.enemy_units if e.is_alive]
        if not enemies:
            return None
        return min(
            enemies,
            key=lambda e: unit.position.tile_coord.chebyshev_distance(e.position.tile_coord),
        )

    @staticmethod
    def _get_wind_direction(context: TacticalContext) -> tuple[int, int]:
        """Get the current wind direction from the environment.

        Returns (dx, dy) where each component is -1, 0, or 1.
        """
        env = getattr(context, "environment", None)
        if env is None:
            return (0, 0)
        wind = getattr(env, "wind_direction", (0, 0))
        # Normalize to unit direction
        wx, wy = wind
        length = math.sqrt(wx * wx + wy * wy)
        if length < 0.01:
            return (0, 0)
        return (int(round(wx / length)), int(round(wy / length)))
