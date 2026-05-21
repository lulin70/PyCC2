from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.audio.sound_system import SoundSystem
    from pycc2.presentation.rendering.display_config import DisplayConfig
    from pycc2.services.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class CombatDirector:
    event_bus: EventBus
    display_config: DisplayConfig
    sound_system: SoundSystem | None = None
    ballistic_engine: object | None = None
    pathfinder: object | None = None

    _units: list[Unit] = field(init=False, default_factory=list)
    _game_map: GameMap | None = field(init=False, default=None)
    _pending_effects: list[dict] = field(init=False, default_factory=list)
    _move_orders: dict[str, dict] = field(init=False, default_factory=dict)

    def initialize(self) -> None:
        from pycc2.domain.systems.ballistic import BallisticEngine
        from pycc2.domain.systems.pathfinder import PathFinder
        from pycc2.services.event_protocol import PlayerCommand, UnitAttacked
        from pycc2.services.random_context import RandomContext

        self.ballistic_engine = BallisticEngine(rng=RandomContext())
        self.pathfinder = PathFinder()

        self.event_bus.subscribe(PlayerCommand, self._on_player_command_event)
        self.event_bus.subscribe(UnitAttacked, self._on_unit_attacked_event)

    def set_context(self, units: list[Unit], game_map: GameMap) -> None:
        self._units = units
        self._game_map = game_map

    def update(
        self,
        units: list[Unit],
        game_map: GameMap,
        dt: float,
        battle_stats: object | None = None,
    ) -> None:
        self.set_context(units, game_map)

        for unit in units:
            if unit.weapon.state.name == "RELOADING":
                unit.weapon.tick()

        self.process_movements(units, game_map)
        self.process_deaths(units, battle_stats)

    def _on_player_command_event(self, data: dict) -> None:
        if self._units and self._game_map:
            self.handle_player_command(data, self._units, self._game_map)

    def _on_unit_attacked_event(self, data: dict) -> None:
        self.on_unit_attacked(data)

    def handle_player_command(self, data: dict, units: list[Unit], game_map: GameMap) -> None:
        cmd = data.get("command")
        unit_ids = data.get("unit_ids", [])

        if cmd == "attack" and "target_id" in data:
            target_id = data["target_id"]
            target = next((u for u in units if u.id == target_id), None)

            for uid in unit_ids:
                attacker = next((u for u in units if u.id == uid), None)
                if attacker and target and attacker.faction != target.faction:
                    self.execute_attack(attacker, target)

        elif cmd == "move" and "target" in data:
            tx, ty = data["target"]
            from pycc2.domain.value_objects.tile_coord import TileCoord

            target_tc = TileCoord(tx, ty)
            for uid in unit_ids:
                unit = next((u for u in units if u.id == uid), None)
                if unit and self.pathfinder:
                    path = self.pathfinder.find_path(unit.position.tile_coord, target_tc, game_map)
                    if path:
                        self._move_orders[uid] = {"path": path[1:], "current_idx": 0}

        elif cmd in ("stop", "defend", "take_cover"):
            for uid in unit_ids:
                if uid in self._move_orders:
                    del self._move_orders[uid]

    def execute_attack(self, attacker, target) -> None:
        from pycc2.services.event_protocol import UnitAttacked

        if self.ballistic_engine is None:
            return
        if attacker.weapon.state.name not in ("READY",):
            return
        dist = attacker.position.tile_coord.chebyshev_distance(target.position.tile_coord)
        max_range = 15
        if dist > max_range:
            return

        result = self.ballistic_engine.calculate_shot(
            attacker=attacker,
            target=target,
            game_map=self._game_map,
        )

        if attacker.weapon.fire():
            if self.sound_system:
                weapon_type = "rifle"
                if "mg" in (attacker.weapon.primary_weapon_id or "").lower():
                    weapon_type = "mg"
                elif "pistol" in (attacker.weapon.primary_weapon_id or "").lower():
                    weapon_type = "pistol"
                self.sound_system.play_shot(weapon_type)

        self.event_bus.publish(
            UnitAttacked(
                attacker_id=attacker.id,
                target_id=target.id,
                is_hit=result.hit if result else False,
                damage=result.damage_dealt if result else 0,
                kill_shot=result.is_killing_blow if result else False,
            )
        )

        if result and result.hit:
            target.take_damage(int(result.damage_dealt))
            self._pending_effects.append(
                {
                    "type": "hit",
                    "target_id": target.id,
                    "position": target.position.pixel_position,
                    "damage": result.damage_dealt,
                    "is_kill": result.is_killing_blow,
                }
            )
            self._pending_effects.append(
                {
                    "type": "muzzle",
                    "position": attacker.position.pixel_position,
                    "direction": attacker.position.facing_rad,
                }
            )

    def on_unit_attacked(self, data: dict) -> None:
        target_id = data.get("target_id")
        damage = data.get("damage", 0)
        killed = data.get("killed", False) or data.get("kill_shot", False)

        position = data.get("position")
        if position is None and self._units:
            target = next((u for u in self._units if u.id == target_id), None)
            if target:
                position = target.position.pixel_position

        if damage > 0:
            self._pending_effects.append(
                {
                    "type": "hit",
                    "target_id": target_id,
                    "position": position,
                    "damage": damage,
                    "is_kill": killed,
                }
            )

        if killed:
            self._pending_effects.append(
                {
                    "type": "death",
                    "unit_id": target_id,
                    "position": position,
                }
            )

    def record_stats(self, data: dict, units: list[Unit], battle_stats: object) -> None:
        if battle_stats is None:
            return
        attacker_id = data.get("attacker_id", "")
        target_id = data.get("target_id", "")
        damage = data.get("damage", 0)
        killed = data.get("killed", False) or data.get("kill_shot", False)

        attacker = next((u for u in units if u.id == attacker_id), None)
        target = next((u for u in units if u.id == target_id), None)

        if attacker:
            faction = "allies" if attacker.faction.name == "ALLIES" else "axis"
            battle_stats.record_shot(faction, hit=(damage > 0))
            if damage > 0:
                battle_stats.record_damage(faction, damage)
            if killed and target:
                battle_stats.record_kill(faction)
                target_faction = "axis" if target.faction.name == "AXIS" else "allies"
                battle_stats.record_unit_lost(target_faction)

    def process_effects(self, renderer: object | None = None) -> None:
        if renderer is None or not hasattr(renderer, "spawn_hit_flash"):
            self._pending_effects.clear()
            return

        for effect in self._pending_effects:
            etype = effect["type"]
            if etype == "hit":
                renderer.spawn_hit_flash(effect["target_id"])
                renderer.spawn_damage_number(
                    effect["position"], effect["damage"], effect.get("is_kill", False)
                )
                if self.sound_system:
                    self.sound_system.play_hit(is_critical=effect.get("is_kill", False))
            elif etype == "muzzle":
                renderer.spawn_muzzle_flash(effect["position"], effect.get("direction", 0))
            elif etype == "death":
                renderer.spawn_death_effect(effect["unit_id"], effect["position"])
                if self.sound_system:
                    self.sound_system.play_death()

        self._pending_effects.clear()

    def process_deaths(self, units: list[Unit], battle_stats: object | None = None) -> None:
        dead_units = [u for u in units if not u.is_alive]
        for unit in dead_units:
            if battle_stats:
                faction = "allies" if unit.faction.name == "ALLIES" else "axis"
                battle_stats.record_unit_lost(faction)

    def process_movements(self, units: list[Unit], game_map: GameMap) -> None:

        from pycc2.domain.value_objects.tile_coord import TileCoord
        from pycc2.domain.value_objects.vec2 import Vec2

        for unit in units:
            move_order = self._move_orders.get(unit.id)
            if move_order is None:
                continue

            path = move_order.get("path", [])
            if not path:
                del self._move_orders[unit.id]
                continue

            speed_tiles_per_sec = 3.0
            moved = speed_tiles_per_sec * 1.0 / 30.0

            target_tc = path[0]
            ts = self.display_config.base_tile_size
            target_vec = Vec2(target_tc.x * ts + ts // 2, target_tc.y * ts + ts // 2)
            current_vec = unit.position.pixel_position

            diff_x = target_vec.x - current_vec.x
            diff_y = target_vec.y - current_vec.y
            dist = math.sqrt(diff_x * diff_x + diff_y * diff_y)

            move_pixels = moved * ts

            if dist <= move_pixels:
                unit.position.tile_coord = target_tc
                path.pop(0)
                if self.sound_system:
                    tc = unit.position.tile_coord
                    terrain = "grass"
                    if 0 <= tc.x < game_map.width and 0 <= tc.y < game_map.height:
                        tile_val = game_map.tile_grid[tc.y, tc.x]
                        if tile_val == 1:
                            terrain = "road"
                        elif tile_val == 2:
                            terrain = "wood"
                    self.sound_system.play_footstep(terrain)
                if not path:
                    del self._move_orders[unit.id]
                    self.event_bus.publish("UnitArrived", {"unit_id": unit.id})
                else:
                    self._move_orders[unit.id]["path"] = path
            else:
                ratio = move_pixels / dist
                new_x = current_vec.x + diff_x * ratio
                new_y = current_vec.y + diff_y * ratio
                new_pixel_pos = Vec2(new_x, new_y)
                tile_x = int(new_x // ts)
                tile_y = int(new_y // ts)
                unit.position.tile_coord = TileCoord(tile_x, tile_y)
                unit.position.set_pixel_offset(Vec2(new_x - tile_x * ts, new_y - tile_y * ts))
                unit.position.set_facing_toward(target_tc)

    def tick_weapon_reload(self, units: list[Unit]) -> None:
        for unit in units:
            if unit.weapon.state.name == "RELOADING":
                unit.weapon.tick()
