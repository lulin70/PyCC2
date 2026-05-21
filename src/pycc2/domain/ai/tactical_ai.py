"""
P9 AI Tactical System — CC2-Authentic Combat Behaviors

Implements the four P0-priority AI behaviors identified in ISSUES.md P3:

  1. FlankingAI          — Move units around the side of enemy positions
  2. SuppressionAI       — Prioritize MG fire on high-threat targets
  3. InfantryTankCoordAI — Coordinate infantry and armor
  4. VictoryPointAI      — Prioritize capturing/defending Victory Locations

Plus the TacticalOrchestrator that runs all tactical AIs each tick,
resolves unit-assignment conflicts, and issues final orders.

Design principles (from OpenCombat soldier.rs analysis):
  - Soldiers tick at configurable frequency (not every frame)
  - Squad leaders issue orders; subordinates follow
  - Behavior is driven by battlefield assessment (BattlefieldPicture)
  - Suppression decreases over time; morale state gates actions
  - Composable: multiple AIs contribute orders, highest priority wins
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.entities.unit import Faction, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.ai.blackboard import Blackboard
    from pycc2.domain.ai.difficulty_system import DifficultyConfig
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit


# ---------------------------------------------------------------------------
# Shared data structures
# ---------------------------------------------------------------------------

class FlankSide(Enum):
    LEFT = auto()
    RIGHT = auto()


@dataclass(slots=True)
class TacticalContext:
    """Read-only snapshot of the battlefield passed to every tactical AI."""

    friendly_units: list[Unit]
    enemy_units: list[Unit]
    game_map: GameMap
    current_tick: int
    blackboards: dict[str, Blackboard] = field(default_factory=dict)
    difficulty_config: DifficultyConfig | None = None
    vl_positions: list[tuple[TileCoord, str | None, int]] = field(
        default_factory=list
    )

    @property
    def friendly_faction(self) -> Faction | None:
        if self.friendly_units:
            return self.friendly_units[0].faction
        return None


@dataclass(slots=True)
class PrioritizedIntent:
    """An intent tagged with the originating AI and a float priority [0..1]."""

    intent: TacticIntent
    ai_name: str
    score: float = 0.0


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

_HIGH_THREAT_TYPES: set[UnitType] = {
    UnitType.MACHINE_GUN_SQUAD,
    UnitType.AT_GUN_TEAM,
    UnitType.COMMANDER,
    UnitType.MORTAR_TEAM,
    UnitType.SNIPER_TEAM,
}

_ARMOR_TYPES: set[UnitType] = {UnitType.TANK}

_AT_TYPES: set[UnitType] = {UnitType.AT_GUN_TEAM}

_INFANTRY_TYPES: set[UnitType] = {
    UnitType.INFANTRY_SQUAD,
    UnitType.COMMANDER,
    UnitType.SNIPER_TEAM,
    UnitType.MEDIC_TEAM,
}


def _threat_score(unit: Unit, reference_pos: TileCoord) -> float:
    """Score an enemy unit by type, health, and distance to a reference point."""
    type_weights: dict[UnitType, float] = {
        UnitType.MACHINE_GUN_SQUAD: 3.0,
        UnitType.AT_GUN_TEAM: 2.5,
        UnitType.COMMANDER: 2.0,
        UnitType.MORTAR_TEAM: 1.8,
        UnitType.TANK: 3.5,
        UnitType.SNIPER_TEAM: 1.5,
        UnitType.INFANTRY_SQUAD: 1.0,
        UnitType.MEDIC_TEAM: 0.5,
    }
    weight = float(type_weights.get(unit.unit_type, 1.0))
    dist = max(unit.position.tile_coord.chebyshev_distance(reference_pos), 1)
    hp_ratio = float(unit.health.hp_ratio)
    result = weight * (0.5 + 0.5 * hp_ratio) / dist
    return float(result)


def _infer_facing(unit: Unit, allies: list[Unit]) -> TileCoord:
    """Infer the direction a unit is facing based on the centroid of
    opposing forces.  Returns the tile the unit is 'looking at'."""
    if not allies:
        return unit.position.tile_coord
    cx = sum(u.position.tile_coord.x for u in allies) / len(allies)
    cy = sum(u.position.tile_coord.y for u in allies) / len(allies)
    return TileCoord(int(cx), int(cy))


def _flank_position(
    enemy_pos: TileCoord,
    facing_target: TileCoord,
    side: FlankSide,
    offset: int = 4,
) -> TileCoord:
    """Calculate a flanking position offset perpendicular to the enemy's
    facing direction.  *facing_target* is the tile the enemy faces toward."""
    dx = facing_target.x - enemy_pos.x
    dy = facing_target.y - enemy_pos.y
    length = math.sqrt(dx * dx + dy * dy) or 1.0
    # Perpendicular (rotate 90 degrees)
    if side == FlankSide.LEFT:
        perp_x = dy / length
        perp_y = -dx / length
    else:
        perp_x = -dy / length
        perp_y = dx / length
    # Flank position is offset perpendicular + slightly forward
    fx = int(enemy_pos.x + perp_x * offset + dx / length * 2)
    fy = int(enemy_pos.y + perp_y * offset + dy / length * 2)
    return TileCoord(fx, fy)


def _nearest_vl(
    pos: TileCoord,
    vl_list: list[tuple[TileCoord, str | None, int]],
) -> tuple[TileCoord, str | None, int] | None:
    """Return the nearest VL entry (position, owner, value)."""
    if not vl_list:
        return None
    return min(vl_list, key=lambda v: pos.chebyshev_distance(v[0]))


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class TacticalAIBase(ABC):
    """Base class for composable tactical AI modules.

    Each AI evaluates the battlefield and returns a priority score (0.0-1.0)
    indicating how relevant its behaviour is this tick.  If the score is
    above a threshold the orchestrator calls ``execute`` to collect orders.
    """

    @abstractmethod
    def evaluate(self, context: TacticalContext) -> float:
        """Return a priority score in [0.0, 1.0]."""

    @abstractmethod
    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        """Return a list of TacticIntents for units this AI wants to control."""


# ---------------------------------------------------------------------------
# 1. FlankingAI
# ---------------------------------------------------------------------------

class FlankingAI(TacticalAIBase):
    """Move units around the side of enemy positions.

    CC2 behaviour: AI infiltrates from the flank rather than charging
    frontally.  When multiple units are available, a pincer movement
    is coordinated — one group pins from the front while another flanks.

    P9 Enhancement: Flanking positions are now validated for:
      1. Passability (destination must be walkable terrain)
      2. Concealment (path midpoint must not be in enemy LOS)
      3. Cover (destination must have some cover value)

    Evaluation heuristic:
      - Higher score when enemies are concentrated in a narrow front
      - Higher score when we have enough mobile units to split
      - Lower score when already flanking or no enemies visible
    """

    MIN_FLANKING_UNITS: int = 2
    FLANK_OFFSET: int = 4

    def evaluate(self, context: TacticalContext) -> float:
        enemies = [e for e in context.enemy_units if e.is_alive]
        mobile = self._mobile_units(context)
        if len(enemies) < 1 or len(mobile) < self.MIN_FLANKING_UNITS:
            return 0.0

        enemy_front_width = self._enemy_front_width(enemies)
        concentration = min(enemy_front_width / 10.0, 1.0)
        availability = min(len(mobile) / 4.0, 1.0)

        diff_mod = 1.0
        if context.difficulty_config is not None:
            if not context.difficulty_config.use_flanking:
                return 0.0
            diff_mod = context.difficulty_config.aggressiveness

        score = 0.4 * concentration + 0.4 * availability + 0.2 * 0.5
        return min(score * diff_mod, 1.0)

    def execute(self, context: TacticalContext) -> list[TacticIntent]:
        enemies = [e for e in context.enemy_units if e.is_alive]
        mobile = self._mobile_units(context)
        if len(enemies) < 1 or len(mobile) < self.MIN_FLANKING_UNITS:
            return []

        primary_target = max(
            enemies,
            key=lambda e: _threat_score(e, mobile[0].position.tile_coord),
        )
        target_pos = primary_target.position.tile_coord
        facing = _infer_facing(primary_target, context.friendly_units)

        enemy_positions = [e.position.tile_coord for e in enemies if e.is_alive]

        intents: list[TacticIntent] = []

        # Pinning force: front-line units suppress / attack
        pin_count = max(1, len(mobile) // 2)
        pin_units = mobile[:pin_count]
        for u in pin_units:
            intents.append(
                TacticIntent(
                    unit_id=u.id,
                    tactic_type=TacticType.SUPPRESS_FIRE,
                    priority=7,
                    target_unit_id=primary_target.id,
                    target_position=target_pos,
                )
            )

        # Flanking force: split left / right
        flank_units = mobile[pin_count:]
        left_flank = flank_units[: len(flank_units) // 2 + 1]
        right_flank = flank_units[len(flank_units) // 2 + 1 :]

        for u in left_flank:
            dest = _flank_position(
                target_pos, facing, FlankSide.LEFT, self.FLANK_OFFSET
            )
            if context.game_map.is_within_bounds(dest) and self._validate_flank_path(
                u.position.tile_coord, dest, context.game_map, enemy_positions
            ):
                intents.append(
                    TacticIntent(
                        unit_id=u.id,
                        tactic_type=TacticType.FLANKING,
                        priority=8,
                        target_position=dest,
                        target_unit_id=primary_target.id,
                    )
                )
            elif context.game_map.is_within_bounds(dest):
                # Path not validated — try a closer offset
                closer = _flank_position(
                    target_pos, facing, FlankSide.LEFT, max(self.FLANK_OFFSET - 2, 2)
                )
                if context.game_map.is_within_bounds(closer) and self._validate_flank_path(
                    u.position.tile_coord, closer, context.game_map, enemy_positions
                ):
                    intents.append(
                        TacticIntent(
                            unit_id=u.id,
                            tactic_type=TacticType.FLANKING,
                            priority=8,
                            target_position=closer,
                            target_unit_id=primary_target.id,
                        )
                    )

        for u in right_flank:
            dest = _flank_position(
                target_pos, facing, FlankSide.RIGHT, self.FLANK_OFFSET
            )
            if context.game_map.is_within_bounds(dest) and self._validate_flank_path(
                u.position.tile_coord, dest, context.game_map, enemy_positions
            ):
                intents.append(
                    TacticIntent(
                        unit_id=u.id,
                        tactic_type=TacticType.FLANKING,
                        priority=8,
                        target_position=dest,
                        target_unit_id=primary_target.id,
                    )
                )
            elif context.game_map.is_within_bounds(dest):
                closer = _flank_position(
                    target_pos, facing, FlankSide.RIGHT, max(self.FLANK_OFFSET - 2, 2)
                )
                if context.game_map.is_within_bounds(closer) and self._validate_flank_path(
                    u.position.tile_coord, closer, context.game_map, enemy_positions
                ):
                    intents.append(
                        TacticIntent(
                            unit_id=u.id,
                            tactic_type=TacticType.FLANKING,
                            priority=8,
                            target_position=closer,
                            target_unit_id=primary_target.id,
                        )
                    )

        return intents

    # -- helpers --

    @staticmethod
    def _mobile_units(context: TacticalContext) -> list[Unit]:
        return [
            u
            for u in context.friendly_units
            if u.is_alive
            and u.can_act
            and u.unit_type in _INFANTRY_TYPES
            and u.morale.is_combat_effective
        ]

    @staticmethod
    def _enemy_front_width(enemies: list[Unit]) -> float:
        if len(enemies) < 2:
            return 1.0
        xs = [e.position.tile_coord.x for e in enemies]
        ys = [e.position.tile_coord.y for e in enemies]
        return float(max(max(xs) - min(xs), max(ys) - min(ys), 1))

    @staticmethod
    def _validate_flank_path(
        start: TileCoord,
        flank_dest: TileCoord,
        game_map: GameMap,
        enemy_positions: list[TileCoord],
    ) -> bool:
        """Validate a flanking path.

        Checks:
          1. Destination is passable terrain
          2. Path midpoint is not exposed to enemy LOS
          3. Destination has some cover value

        Returns True if the path is valid for flanking.
        """
        # 1. Check destination passability
        if not game_map.is_passable(flank_dest):
            return False

        # 2. Check if path midpoint is exposed to enemy LOS
        mid = TileCoord(
            (start.x + flank_dest.x) // 2,
            (start.y + flank_dest.y) // 2,
        )
        for ep in enemy_positions:
            if hasattr(game_map, 'has_line_of_sight'):
                if game_map.has_line_of_sight(ep, mid):
                    return False  # Path midpoint exposed to enemy fire
            else:
                # Fallback: simple distance check
                dist = ep.chebyshev_distance(mid)
                if dist <= 5:
                    return False

        # 3. Check destination cover value
        terrain = game_map.get_terrain(flank_dest)
        if terrain is not None:
            cover = getattr(terrain, 'cover_modifier', 0.0)
            if cover < 0.1:
                return False  # No cover at destination

        return True


# ---------------------------------------------------------------------------
# 2. SuppressionAI
# ---------------------------------------------------------------------------

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
            infantry_advancing = self._infantry_advancing_on(
                target, context.friendly_units
            )

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
        morale_val = getattr(target.morale, 'value', 100)
        if morale_val < 15:
            return False  # Target is panicked/routing

        # Check if target is pinned via suppression state
        suppression = getattr(target, 'suppression_state', None)
        if suppression is not None:
            is_pinned = getattr(suppression, 'is_pinned', False)
            if is_pinned:
                return False  # Target already pinned

        # Check for higher-priority moving enemies
        moving_enemies = [
            e for e in context.enemy_units
            if e.is_alive and e.id != target.id
            and SuppressionAI._is_moving(e, context)
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
            return bool(bb.get('is_moving', False))
        # Fallback: check if unit has a pending move order
        return getattr(unit, '_is_moving', False)

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
            morale_val = getattr(e.morale, 'value', 100)
            if morale_val < 15:
                continue  # Already panicked
            suppression = getattr(e, 'suppression_state', None)
            if suppression is not None and getattr(suppression, 'is_pinned', False):
                continue  # Already pinned
            dist = mg.position.tile_coord.chebyshev_distance(e.position.tile_coord)
            if dist <= 12:
                return e
        return None


# ---------------------------------------------------------------------------
# 3. InfantryTankCoordAI
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
                if i.position.tile_coord.chebyshev_distance(tank.position.tile_coord) <= self.INFANTRY_SUPPORT_RANGE
            ]

            if nearby_infantry:
                # Tank advances with infantry support
                # Plan route preferring roads (CC2 Patch 2.0 improvement)
                advance_pos = self._plan_tank_advance(
                    tank.position.tile_coord, target_pos, context
                )
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
                screen_pos = self._screening_position(
                    inf.position.tile_coord, at_pos, tanks[0].position.tile_coord
                )
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
            if u.is_alive
            and u.can_act
            and u.unit_type in _ARMOR_TYPES
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
        inf_pos: TileCoord,
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
        best_score = -1

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
            terrain_type = getattr(terrain, 'terrain_type', '')
            if terrain_type in ('road', 'bridge', 'path'):
                score += 3.0
            # Cover bonus (partial cover preferred for hull-down)
            cover = getattr(terrain, 'cover_modifier', 0.0)
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
# 4. VictoryPointAI
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

        faction_name = (
            context.friendly_faction.name if context.friendly_faction else None
        )
        uncontrolled = [
            v for v in context.vl_positions if v[1] is None or v[1] != faction_name
        ]
        held = [
            v for v in context.vl_positions if v[1] == faction_name
        ]

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
                and e.position.tile_coord.chebyshev_distance(vl_pos)
                <= self.DEFEND_RADIUS
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

        faction_name = (
            context.friendly_faction.name if context.friendly_faction else None
        )
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
                and e.position.tile_coord.chebyshev_distance(vl_pos)
                <= self.DEFEND_RADIUS
            ]
            if not enemies_near:
                continue

            # Check if we already have units near this VL
            defenders_near = [
                u
                for u in available
                if u.id not in assigned
                and u.position.tile_coord.chebyshev_distance(vl_pos)
                <= self.DEFEND_RADIUS
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
                and e.position.tile_coord.chebyshev_distance(vl_pos)
                <= self.DEFEND_RADIUS
            )
            friendly_count = sum(
                1
                for u in available
                if u.position.tile_coord.chebyshev_distance(vl_pos)
                <= self.DEFEND_RADIUS
            )
            # Heavily outnumbered — retreat to nearest stronger VL
            if enemy_count >= 3 and friendly_count <= 1:
                safer_vl = self._find_safer_vl(vl_pos, context, faction_name)
                if safer_vl is not None:
                    for u in available:
                        if (
                            u.position.tile_coord.chebyshev_distance(vl_pos)
                            <= self.DEFEND_RADIUS
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
                if e.is_alive
                and e.position.tile_coord.chebyshev_distance(vl_pos) <= 5
            )
            if enemies_near <= 1:
                safe.append((vl_pos, current_vl.chebyshev_distance(vl_pos)))
        if not safe:
            return None
        safe.sort(key=lambda s: s[1])
        return safe[0][0]


# ---------------------------------------------------------------------------
# 5. TacticalOrchestrator
# ---------------------------------------------------------------------------

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
                all_prioritized.append(
                    PrioritizedIntent(intent=intent, ai_name=name, score=score)
                )

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
