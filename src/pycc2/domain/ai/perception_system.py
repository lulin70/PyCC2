"""Perception system that populates the AI blackboard with sensed combat data."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.ai.blackboard import Blackboard
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit


class PerceptionSystem:
    """Populates AI blackboards with sensed combat data like health and enemies."""

    def update_blackboard(
        self,
        blackboard: Blackboard,
        unit: Unit,
        game_map: GameMap | None = None,
        all_units: list[Unit] | None = None,
        fog_of_war: dict[tuple[int, int], bool] | None = None,
    ) -> None:
        """Populate the blackboard with sensed combat data for the given unit."""
        blackboard.set("health_ratio", unit.health.hp_ratio)
        blackboard.set("is_suppressed", unit.morale.state.value >= 2)
        blackboard.set("current_tile", unit.position.tile_coord)
        if all_units is not None:
            visible_enemies: list[str] = []
            nearest_dist: float = float("inf")
            nearest_pos = None
            nearest_id: str | None = None
            allies_nearby: int = 0
            for other in all_units:
                if other.id == unit.id or not other.is_alive:
                    continue
                dist = unit.position.tile_coord.chebyshev_distance(other.position.tile_coord)
                if other.faction != unit.faction:
                    is_visible = True
                    if fog_of_war is not None:
                        key = (other.position.tile_coord.x, other.position.tile_coord.y)
                        is_visible = fog_of_war.get(key, False)
                    if is_visible and (
                        game_map is None
                        or game_map.has_line_of_sight(
                            unit.position.tile_coord, other.position.tile_coord
                        )
                    ):
                        visible_enemies.append(other.id)
                        if dist < nearest_dist:
                            nearest_dist = dist
                            nearest_pos = other.position.tile_coord
                            nearest_id = other.id
                elif other.faction == unit.faction and dist <= 5.0:
                    allies_nearby += 1
            blackboard.set("visible_enemies", visible_enemies)
            if nearest_pos is not None:
                blackboard.set("nearest_enemy_distance", nearest_dist)
                blackboard.set("nearest_enemy_position", nearest_pos)
                blackboard.set("nearest_enemy_id", nearest_id)
            else:
                blackboard.set("nearest_enemy_distance", float("inf"))
                blackboard.remove("nearest_enemy_position")
                blackboard.remove("nearest_enemy_id")
            blackboard.set("allies_nearby", allies_nearby)
