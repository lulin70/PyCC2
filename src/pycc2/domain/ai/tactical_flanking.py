"""FlankingAI — Move units around the side of enemy positions.

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

from __future__ import annotations

from typing import TYPE_CHECKING

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai_types import (
    _INFANTRY_TYPES,
    FlankSide,
    TacticalAIBase,
    TacticalContext,
    _flank_position,
    _infer_facing,
    _threat_score,
)
from pycc2.domain.value_objects.tile_coord import TileCoord

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit


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
        """Return flanking priority based on enemy concentration and mobile unit availability."""
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
        """Generate flanking move intents for mobile units around enemy positions."""
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
            dest = _flank_position(target_pos, facing, FlankSide.LEFT, self.FLANK_OFFSET)
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
            dest = _flank_position(target_pos, facing, FlankSide.RIGHT, self.FLANK_OFFSET)
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
            if hasattr(game_map, "has_line_of_sight"):
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
            cover = getattr(terrain, "cover_modifier", 0.0)
            if cover < 0.1:
                return False  # No cover at destination

        return True
