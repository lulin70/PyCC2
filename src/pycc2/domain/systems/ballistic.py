from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import IRandomNumberGenerator

from pycc2.domain.systems.swiss_cheese_damage import SwissCheeseEngine, SwissCheeseResult
from pycc2.domain.value_objects.terrain_type import TerrainType


@dataclass(slots=True, frozen=True)
class ShotResult:
    hit: bool
    damage_dealt: float = 0.0
    is_killing_blow: bool = False
    was_blocked_by_cover: bool = False
    actual_accuracy: float = 0.0
    distance: float = 0.0
    reason: str = ""
    suppression_dealt: float = 0.0
    miss_position: tuple[float, float] | None = None


@dataclass
class BallisticEngine:
    rng: IRandomNumberGenerator

    _weapon_stats: dict[str, dict] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_weapon_stats",
            {
                "rifle": {
                    "base_accuracy": 0.85,
                    "effective_range": 12.0,
                    "base_damage": 25.0,
                    "penetration": 1.0,
                    "spread": 2.0,
                },
                "smg": {
                    "base_accuracy": 0.70,
                    "effective_range": 6.0,
                    "base_damage": 15.0,
                    "penetration": 0.8,
                    "spread": 4.0,
                },
                "sniper": {
                    "base_accuracy": 0.95,
                    "effective_range": 20.0,
                    "base_damage": 50.0,
                    "penetration": 1.5,
                    "spread": 0.5,
                },
                "mg": {
                    "base_accuracy": 0.75,
                    "effective_range": 15.0,
                    "base_damage": 30.0,
                    "penetration": 1.2,
                    "spread": 3.0,
                },
                "pistol": {
                    "base_accuracy": 0.65,
                    "effective_range": 4.0,
                    "base_damage": 12.0,
                    "penetration": 0.6,
                    "spread": 3.5,
                },
                "tank_cannon": {
                    "base_accuracy": 0.65,
                    "effective_range": 12.0,
                    "base_damage": 52.5,
                    "penetration": 2.5,
                    "spread": 3.0,
                    "anti_tank_bonus": 1.5,
                },
                "sniper_rifle": {
                    "base_accuracy": 0.85,
                    "effective_range": 15.0,
                    "base_damage": 37.5,
                    "penetration": 1.2,
                    "spread": 1.0,
                },
                "mortar": {
                    "base_accuracy": 0.40,
                    "effective_range": 10.0,
                    "base_damage": 32.5,
                    "penetration": 1.0,
                    "spread": 5.0,
                },
                "bazooka": {
                    "base_accuracy": 0.55,
                    "effective_range": 8.0,
                    "base_damage": 45.0,
                    "penetration": 3.0,
                    "spread": 4.0,
                    "anti_tank_bonus": 2.0,
                },
            },
        )
        object.__setattr__(self, "_swiss_cheese", None)

    @property
    def swiss_cheese(self) -> SwissCheeseEngine:
        if self._swiss_cheese is None:
            object.__setattr__(self, "_swiss_cheese", SwissCheeseEngine())
        return self._swiss_cheese

    def calculate_shot(
        self,
        attacker: Unit,
        target: Unit,
        weapon_slot: str = "primary",
        game_map: GameMap | None = None,
        environment=None,
    ) -> ShotResult:
        if not attacker.health.is_alive:
            return ShotResult(
                hit=False,
                distance=0.0,
                reason="attacker is dead",
            )

        if not target.health.is_alive:
            return ShotResult(
                hit=False,
                distance=0.0,
                reason="target is dead",
            )

        if attacker.weapon is None:
            return ShotResult(
                hit=False,
                distance=0.0,
                reason="no weapon equipped",
            )

        if not attacker.weapon.can_fire:
            if attacker.weapon.state.name == "OUT_OF_AMMO":
                return ShotResult(
                    hit=False,
                    distance=0.0,
                    reason="out of ammo",
                )
            return ShotResult(
                hit=False,
                distance=0.0,
                reason="weapon not ready",
            )

        dist = attacker.position.tile_coord.octile_distance(target.position.tile_coord)

        weapon_id = attacker.weapon.primary_weapon_id
        wstats = self._weapon_stats.get(weapon_id, self._weapon_stats["rifle"])

        if dist > wstats["effective_range"] * 2.5:
            return ShotResult(
                hit=False,
                distance=dist,
                actual_accuracy=max(0.05, 1.0 - (dist / wstats["effective_range"]) * 0.6),
                reason="out of range",
            )

        if game_map is not None and not game_map.has_line_of_sight(
            attacker.position.tile_coord, target.position.tile_coord
        ):
            return ShotResult(
                hit=False,
                distance=dist,
                actual_accuracy=0.0,
                reason="no line of sight",
            )

        # Vehicle passability check: vehicles cannot fire through or
        # occupy destroyed bridge tiles
        if game_map is not None and getattr(attacker, "is_vehicle", False):
            attacker_terrain = game_map.get_terrain(attacker.position.tile_coord)
            if attacker_terrain == TerrainType.BRIDGE_DESTROYED:
                return ShotResult(
                    hit=False,
                    distance=dist,
                    actual_accuracy=0.0,
                    reason="vehicle on destroyed bridge (impassable)",
                )

        base_acc = wstats["base_accuracy"]
        dist_penalty = self._calc_distance_penalty(dist, wstats["effective_range"])
        accuracy = base_acc * dist_penalty
        cover_mod = self._calc_cover_modifier(target, game_map)
        accuracy *= cover_mod
        # R1: Upper floor attacker gets LOS/accuracy bonus (better vantage point)
        attacker_floor = getattr(attacker, "building_floor", 0)
        if attacker_floor > 0:
            accuracy *= 1.0 + attacker_floor * 0.08  # +8% per floor above ground
        morale_mod = max(0.3, target.morale.accuracy_modifier)
        accuracy *= morale_mod
        if environment is not None:
            accuracy *= environment.get_accuracy_modifier()
        # R4: Weather accuracy modifier (rain reduces accuracy, fog reduces less)
        if game_map is not None:
            weather_state = getattr(game_map, "weather_state", None)
            if weather_state is not None:
                from pycc2.domain.systems.weather_effects import WeatherEffects

                weather_type = getattr(weather_state, "weather_type", None)
                if weather_type is not None:
                    accuracy = WeatherEffects().apply_to_accuracy(accuracy, weather_type)
        final_accuracy = min(0.98, max(0.02, accuracy))

        roll = self.rng.uniform(0.0, 1.0)
        is_hit = roll < final_accuracy

        if is_hit:
            spread_angle = self._calc_spread(wstats["spread"], dist, self.rng)

            dist_factor = max(0.3, 1.0 - (dist / (wstats["effective_range"] * 1.5)) * 0.4)
            armor_factor = self._calc_armor_factor(attacker, target, wstats.get("penetration", 1.0))
            damage, is_killing = self._calc_damage(
                wstats["base_damage"],
                dist_factor,
                wstats["penetration"],
                target.health.hp,
                self.rng,
                armor_factor=armor_factor,
            )
            suppression = self._calc_suppression(hit=True, damage=damage)

            attacker.weapon.fire()

            return ShotResult(
                hit=True,
                damage_dealt=damage,
                is_killing_blow=is_killing,
                actual_accuracy=final_accuracy,
                distance=dist,
                reason="hit",
                suppression_dealt=suppression,
                miss_position=None,
            )
        else:
            spread_angle = self._calc_spread(wstats["spread"], dist, self.rng)
            tx = target.position.tile_coord.x
            ty = target.position.tile_coord.y
            offset_x = math.tan(math.radians(spread_angle)) * dist * 0.5
            offset_y = math.tan(math.radians(spread_angle + 90.0)) * dist * 0.3
            miss_pos = (tx + offset_x, ty + offset_y)
            suppression = self._calc_suppression(hit=False)

            return ShotResult(
                hit=False,
                damage_dealt=0.0,
                actual_accuracy=final_accuracy,
                distance=dist,
                reason=f"miss (roll {roll:.3f} >= acc {final_accuracy:.3f})",
                suppression_dealt=suppression,
                miss_position=miss_pos,
            )

    def _calc_distance_penalty(self, distance_tiles: float, effective_range: float) -> float:
        return max(0.05, 1.0 - (distance_tiles / effective_range) * 0.6)

    def _calc_cover_modifier(self, target: Unit, game_map: GameMap | None) -> float:
        """Calculate hit chance modifier based on target's cover type.

        Hard cover (buildings, walls): chance to completely block the shot.
        Soft cover (hedges, woods, grass): reduces accuracy by concealment.
        Hybrid (enterable buildings): hard walls + soft windows.
        """
        if game_map is None:
            return 1.0
        terrain = game_map.get_terrain(target.position.tile_coord)
        from pycc2.domain.value_objects.terrain_type import CoverType

        cover_type = terrain.cover_type

        if cover_type == CoverType.HARD:
            # Hard cover: chance to completely block the shot
            block_chance = terrain.cover_bonus  # e.g., 0.50 for buildings, 0.70 for walls
            return 1.0 - block_chance
        elif cover_type == CoverType.SOFT:
            # Soft cover: reduces accuracy by concealment
            return 1.0 - terrain.concealment_modifier * 0.5
        elif cover_type == CoverType.HYBRID:
            # Enterable building: hard walls block, but windows provide firing arcs
            # Reduced block compared to solid buildings
            block_chance = terrain.cover_bonus * 0.6
            concealment = terrain.concealment_modifier * 0.3
            return 1.0 - block_chance - concealment
        else:
            # No cover
            return 1.0

    def _calc_armor_factor(
        self,
        attacker: Unit,
        target: Unit,
        penetration: float,
    ) -> float:
        target.unit_type.name if hasattr(target.unit_type, "name") else str(target.unit_type)

        armor = getattr(target, "armor_front", 0.1)
        armor_side = getattr(target, "armor_side", 0.08)
        armor_rear = getattr(target, "armor_rear", 0.08)

        dx = attacker.position.tile_coord.x - target.position.tile_coord.x
        dy = attacker.position.tile_coord.y - target.position.tile_coord.y

        target_facing = getattr(target.position, "facing", 0.0)
        if hasattr(target.position, "direction"):
            target_facing = (
                target.position.direction.value
                if hasattr(target.position.direction, "value")
                else 0.0
            )

        attack_angle = math.atan2(dy, dx)
        angle_diff = abs(attack_angle - target_facing)
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        angle_diff = abs(angle_diff)

        if angle_diff < math.pi / 4:
            armor_val = armor
        elif angle_diff < 3 * math.pi / 4:
            armor_val = armor_side
        else:
            armor_val = armor_rear

        if penetration >= armor_val:
            return 1.0

        armor_factor = penetration / armor_val
        return max(0.25, armor_factor)

    def _calc_damage(
        self,
        base_damage: float,
        distance_factor: float,
        penetration: float,
        target_hp: int,
        rng: IRandomNumberGenerator,
        armor_factor: float = 1.0,
    ) -> tuple[float, bool]:
        variance = rng.uniform(0.8, 1.2)
        damage = base_damage * penetration * distance_factor * variance * armor_factor
        damage = round(damage, 2)
        is_killing = (target_hp - damage <= 0) and (rng.uniform(0.0, 1.0) < 0.15)
        return damage, is_killing

    def _calc_spread(
        self, base_spread: float, distance: float, rng: IRandomNumberGenerator
    ) -> float:
        sigma = base_spread * math.sqrt(max(1.0, distance))
        return float(rng.gaussian(0.0, sigma))

    def _calc_suppression(
        self, hit: bool, damage: float = 0.0, base_suppression: float = 5.0
    ) -> float:
        if hit:
            return damage * 0.5 + base_suppression
        return base_suppression * 0.3

    def calculate_shot_swiss_cheese(
        self,
        attacker: Unit,
        target: Unit,
        weapon_slot: str = "primary",
        game_map: GameMap | None = None,
        environment=None,
        enable_sc: bool = True,
    ) -> tuple[ShotResult, SwissCheeseResult | None]:
        base_result = self.calculate_shot(attacker, target, weapon_slot, game_map, environment)

        if not enable_sc or not base_result.hit:
            return base_result, None

        sc_result = self.swiss_cheese.resolve(
            target=target,
            raw_damage=base_result.damage_dealt,
            is_armor_piercing=(base_result.damage_dealt > 40),
            cover_bonus=float(game_map.get_terrain(target.position.tile_coord).cover_bonus)
            if game_map
            else 0.0,
            target_morale=float(target.morale.value),
        )

        base_result = ShotResult(
            hit=True,
            damage_dealt=float(sc_result.total_hp_loss),
            is_killing_blow=(sc_result.ok_count == 0),
            actual_accuracy=base_result.actual_accuracy,
            distance=base_result.distance,
            reason=f"hit (SC: {sc_result.kia_count}K/{sc_result.wia_count}W/{sc_result.pinned_count}P)",
            suppression_dealt=base_result.suppression_dealt,
            miss_position=None,
        )

        return base_result, sc_result
