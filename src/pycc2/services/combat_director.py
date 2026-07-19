"""Combat director orchestrating unit movement, attacks, and visual effects.

Coordinates game-map state, unit orders, and pending combat effects, bridging
domain combat systems with presentation-layer rendering and audio cues.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pycc2.domain.interfaces import ISoundSystem

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces import DisplayConfig
    from pycc2.domain.systems.ballistic import BallisticEngine
    from pycc2.domain.systems.pathfinder import PathFinder
    from pycc2.domain.systems.victory_conditions import BattleStats
    from pycc2.infrastructure.events.event_bus import EventBus
    from pycc2.presentation.rendering.camera import Camera

logger = logging.getLogger(__name__)

# Dispatch table mapping player command names to CombatDirector handler methods.
# Each handler has the uniform signature (data, unit_map, units, game_map) so it
# can be invoked polymorphically from ``handle_player_command``.
_CMD_DISPATCH: dict[str, str] = {
    "attack": "_cmd_attack",
    "move": "_cmd_move",
    "take_cover": "_cmd_take_cover",
    "stop": "_cmd_stop",
    "defend": "_cmd_defend",
    "fast_move": "_cmd_fast_move",
    "sneak": "_cmd_sneak",
    "hide": "_cmd_hide",
    "deploy_smoke": "_cmd_deploy_smoke",
}


@dataclass
class CombatDirector:
    """Orchestrates real-time combat presentation, unit orders, and effects."""

    event_bus: EventBus
    display_config: DisplayConfig
    sound_system: ISoundSystem | None = None
    ballistic_engine: BallisticEngine | None = None
    pathfinder: PathFinder | None = None

    _units: list[Unit] = field(init=False, default_factory=list)
    _game_map: GameMap | None = field(init=False, default=None)
    _pending_effects: list[dict] = field(init=False, default_factory=list)
    _move_orders: dict[str, dict] = field(init=False, default_factory=dict)
    _camera_position: Any | None = field(
        init=False, default=None
    )  # R10: Camera position for sound falloff

    def initialize(self) -> None:
        """Initialize ballistic engine, pathfinder, and event subscriptions."""
        from pycc2.domain.systems.ballistic import BallisticEngine
        from pycc2.domain.systems.pathfinder import PathFinder
        from pycc2.infrastructure.events.event_protocol import PlayerCommand, UnitAttacked
        from pycc2.services.random_context import RandomContext

        self.ballistic_engine = BallisticEngine(rng=RandomContext())
        self.pathfinder = PathFinder()

        self.event_bus.subscribe(PlayerCommand, self._on_player_command_event)
        self.event_bus.subscribe(UnitAttacked, self._on_unit_attacked_event)

    def set_context(self, units: list[Unit], game_map: GameMap) -> None:
        """Cache the current units and game map for combat processing."""
        self._units = units
        self._game_map = game_map

    def update(
        self,
        units: list[Unit],
        game_map: GameMap,
        dt: float,
        battle_stats: BattleStats | None = None,
    ) -> None:
        """Advance weapon reloads, movement, and death processing for one tick."""
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
        """Dispatch a player command (attack, move, defend, smoke, etc.) to units."""
        cmd = data.get("command")

        # Pre-build unit lookup for O(1) access instead of O(n) linear scan
        unit_map = {u.id: u for u in units}

        handler_name = _CMD_DISPATCH.get(cmd) if isinstance(cmd, str) else None
        if handler_name is None:
            return
        getattr(self, handler_name)(data, unit_map, units, game_map)

    def _cmd_attack(
        self,
        data: dict,
        unit_map: dict[str, Unit],
        units: list[Unit],
        game_map: GameMap,
    ) -> None:
        """Process 'attack' command: dispatch attackers against a target unit."""
        if "target_id" not in data:
            return
        target_id = data["target_id"]
        target = unit_map.get(target_id)
        unit_ids = data.get("unit_ids", [])

        for uid in unit_ids:
            attacker = unit_map.get(uid)
            if attacker and target and attacker.faction != target.faction:
                self.execute_attack(attacker, target)

    def _cmd_move(
        self,
        data: dict,
        unit_map: dict[str, Unit],
        units: list[Unit],
        game_map: GameMap,
    ) -> None:
        """Process 'move' command: compute pathfinder path for each unit."""
        if "target" not in data:
            return
        tx, ty = data["target"]
        from pycc2.domain.value_objects.tile_coord import TileCoord

        target_tc = TileCoord(tx, ty)
        unit_ids = data.get("unit_ids", [])
        for uid in unit_ids:
            unit = unit_map.get(uid)
            if unit and self.pathfinder:
                path = self.pathfinder.find_path(unit.position.tile_coord, target_tc, game_map)
                if path:
                    self._move_orders[uid] = {"path": deque(list(path)[1:]), "current_idx": 0}

    def _cmd_take_cover(
        self,
        data: dict,
        unit_map: dict[str, Unit],
        units: list[Unit],
        game_map: GameMap,
    ) -> None:
        """Process 'take_cover' command: cancel any pending move orders."""
        unit_ids = data.get("unit_ids", [])
        for uid in unit_ids:
            if uid in self._move_orders:
                del self._move_orders[uid]

    def _cmd_stop(
        self,
        data: dict,
        unit_map: dict[str, Unit],
        units: list[Unit],
        game_map: GameMap,
    ) -> None:
        """Process 'stop' command: cancel orders and reset movement mode to normal."""
        unit_ids = data.get("unit_ids", [])
        for uid in unit_ids:
            if uid in self._move_orders:
                del self._move_orders[uid]
            # Reset movement mode to normal
            unit = unit_map.get(uid)
            if unit and hasattr(unit, "set_movement_mode"):
                unit.set_movement_mode("normal")

    def _cmd_defend(
        self,
        data: dict,
        unit_map: dict[str, Unit],
        units: list[Unit],
        game_map: GameMap,
    ) -> None:
        """Process 'defend' command: reduces mobility, improves accuracy."""
        unit_ids = data.get("unit_ids", [])
        for uid in unit_ids:
            unit = unit_map.get(uid)
            if unit and hasattr(unit, "set_movement_mode"):
                # Toggle defend mode (or set if not already defending)
                if unit.movement_mode != "defend":
                    unit.set_movement_mode("defend", duration_ticks=-1)  # Indefinite
                    # Stop any current movement
                    if uid in self._move_orders:
                        del self._move_orders[uid]
                    logger.info(
                        "[COMMAND] %s entering DEFEND mode (+25%% accuracy, -50%% speed)",
                        unit.name or uid,
                    )
                else:
                    # Cancel defend mode
                    unit.set_movement_mode("normal")
                    logger.info("[COMMAND] %s exiting DEFEND mode", unit.name or uid)

    def _cmd_fast_move(
        self,
        data: dict,
        unit_map: dict[str, Unit],
        units: list[Unit],
        game_map: GameMap,
    ) -> None:
        """Process 'fast_move' command: faster movement but more visible to enemies."""
        unit_ids = data.get("unit_ids", [])
        for uid in unit_ids:
            unit = unit_map.get(uid)
            if unit and hasattr(unit, "set_movement_mode"):
                # Toggle fast move mode
                if unit.movement_mode != "fast_move":
                    unit.set_movement_mode("fast_move", duration_ticks=-1)
                    logger.info(
                        "[COMMAND] %s entering FAST MOVE mode (1.5x speed, +50%% detection)",
                        unit.name or uid,
                    )
                else:
                    unit.set_movement_mode("normal")
                    logger.info("[COMMAND] %s exiting FAST MOVE mode", unit.name or uid)

    def _cmd_sneak(
        self,
        data: dict,
        unit_map: dict[str, Unit],
        units: list[Unit],
        game_map: GameMap,
    ) -> None:
        """Process 'sneak' command: slower movement but harder to detect."""
        unit_ids = data.get("unit_ids", [])
        for uid in unit_ids:
            unit = unit_map.get(uid)
            if unit and hasattr(unit, "set_movement_mode") and getattr(unit, "can_sneak", False):
                # Toggle sneak mode
                if unit.movement_mode != "sneak":
                    unit.set_movement_mode("sneak", duration_ticks=-1)
                    logger.info(
                        "[COMMAND] %s entering SNEAK mode (0.6x speed, -50%% detection)",
                        unit.name or uid,
                    )
                else:
                    unit.set_movement_mode("normal")
                    logger.info("[COMMAND] %s exiting SNEAK mode", unit.name or uid)
            elif unit:
                logger.warning(
                    "[COMMAND] %s cannot use SNEAK mode (unit type not supported)",
                    unit.name or uid,
                )

    def _cmd_hide(
        self,
        data: dict,
        unit_map: dict[str, Unit],
        units: list[Unit],
        game_map: GameMap,
    ) -> None:
        """Process 'hide' command: similar to defend but with concealment bonus."""
        unit_ids = data.get("unit_ids", [])
        for uid in unit_ids:
            unit = unit_map.get(uid)
            if unit and hasattr(unit, "set_movement_mode") and getattr(unit, "can_hide", False):
                if unit.movement_mode != "defend":
                    unit.set_movement_mode("defend", duration_ticks=-1)
                    # Apply concealment bonus if available
                    if hasattr(unit, "combat_state") and unit.combat_state:
                        unit.combat_state.concealment.special_bonus += 0.2
                    if uid in self._move_orders:
                        del self._move_orders[uid]
                    logger.info("[COMMAND] %s HIDING (+concealment)", unit.name or uid)

    def _cmd_deploy_smoke(
        self,
        data: dict,
        unit_map: dict[str, Unit],
        units: list[Unit],
        game_map: GameMap,
    ) -> None:
        """Process 'deploy_smoke' command: deploy a smoke grenade at unit position."""
        unit_ids = data.get("unit_ids", [])
        for uid in unit_ids:
            unit = unit_map.get(uid)

            # Verify unit can use smoke
            if not unit:
                continue
            if not getattr(unit, "can_use_smoke", False):
                logger.warning(
                    "[SMOKE] %s cannot deploy smoke (no capability)",
                    unit.name or uid,
                )
                continue

            # Check ammo
            if hasattr(unit, "weapon") and unit.weapon:
                # Deploy smoke effect
                try:
                    ammo_inv = getattr(unit, "ammo_inventory", None)
                    if ammo_inv is not None and hasattr(ammo_inv, "deploy_smoke"):
                        tc = unit.position.tile_coord
                        success = ammo_inv.deploy_smoke((tc.x, tc.y))
                        if not success:
                            logger.warning(
                                "[SMOKE] Failed to deploy smoke for %s",
                                unit.name or uid,
                            )
                            continue
                except (ImportError, AttributeError, ValueError, RuntimeError) as e:
                    logger.warning("[SMOKE] Error deploying smoke: %s", e)
                    # Continue with visual effect even if system call fails

                # Trigger visual smoke screen effect
                self._pending_effects.append(
                    {
                        "type": "smoke",
                        "position": unit.position.pixel_position,
                        "radius": 144.0,
                    }
                )

                # Apply smoke to concealment system if available
                if hasattr(unit, "combat_state") and unit.combat_state:
                    unit.combat_state.concealment.in_smoke = True
                    # Smoke fades after some time (handled by combat_state turn processing)

                logger.info("[SMOKE] %s deployed smoke grenade", unit.name or uid)
            else:
                logger.warning("[SMOKE] %s has no weapon system", unit.name or uid)

    def execute_attack(self, attacker, target) -> None:
        """Resolve an attack: fire weapon, apply damage, and emit combat events."""
        from pycc2.infrastructure.events.event_protocol import UnitAttacked, UnitKilled

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

        if attacker.weapon.fire() and self.sound_system:
            weapon_type = "rifle"
            if "mg" in (attacker.weapon.primary_weapon_id or "").lower():
                weapon_type = "mg"
            elif "pistol" in (attacker.weapon.primary_weapon_id or "").lower():
                weapon_type = "pistol"
            # R10: Battle sound distance falloff — use distance-based volume
            source_pos = attacker.position.pixel_position
            camera_pos = getattr(self, "_camera_position", None)
            if camera_pos is not None and hasattr(self.sound_system, "play_sound_with_distance"):
                sound_id = (
                    "RIFLE_SHOT"
                    if weapon_type == "rifle"
                    else ("MG_BURST" if weapon_type == "mg" else "PISTOL_SHOT")
                )
                self.sound_system.play_sound_with_distance(
                    sound_id, source_pos, camera_pos, max_distance=500.0
                )
            else:
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

        weapon_type = "bullet"
        weapon_id = attacker.weapon.primary_weapon_id or ""
        if any(k in weapon_id.lower() for k in ("mg", "machine")):
            weapon_type = "bullet"
        elif any(k in weapon_id.lower() for k in ("tank", "at", "cannon", "gun_")):
            weapon_type = "shell"
        elif any(k in weapon_id.lower() for k in ("bazooka", "piat", "panzer", "rocket")):
            weapon_type = "rocket"
        elif any(k in weapon_id.lower() for k in ("mortar", "howitzer", "artillery")):
            weapon_type = "mortar"

        attacker_pos = attacker.position.pixel_position
        target_pos = target.position.pixel_position
        self.event_bus.publish_named(
            "ProjectileFired",
            {
                "attacker_id": attacker.id,
                "target_id": target.id,
                "weapon_type": weapon_type,
                "start_x": attacker_pos.x,
                "start_y": attacker_pos.y,
                "end_x": target_pos.x,
                "end_y": target_pos.y,
                "damage": result.damage_dealt if result else 0,
                "is_hit": result.hit if result else False,
            },
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
                    "weapon_id": attacker.weapon.primary_weapon_id,
                }
            )
            self._pending_effects.append(
                {
                    "type": "muzzle",
                    "position": attacker.position.pixel_position,
                    "direction": attacker.position.facing_rad,
                }
            )

            if result.is_killing_blow or not target.is_alive:
                self.event_bus.publish(
                    UnitKilled(
                        unit_id=target.id,
                        faction=target.faction.name
                        if hasattr(target.faction, "name")
                        else str(target.faction),
                        attacker_id=attacker.id,
                        attacker_role=getattr(attacker, "role", ""),
                        unit_type=getattr(target, "unit_type", ""),
                        position=(
                            target.position.tile_coord.x,
                            target.position.tile_coord.y,
                        ),
                    )
                )

    def on_unit_attacked(self, data: dict) -> None:
        """Queue visual effects (hit/death) for an attacked unit event."""
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

    def record_stats(self, data: dict, units: list[Unit], battle_stats: BattleStats) -> None:
        """Record shot, damage, and kill statistics into the battle stats."""
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

    def process_effects(self, renderer: Any | None = None, camera: Camera | None = None) -> None:
        """Flush pending visual effects to the renderer and clear the queue."""
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
                # P3-02: Spawn shell casing at hit position (ejected brass)
                if hasattr(renderer, "spawn_shell_casing"):
                    position = effect["position"]
                    renderer.spawn_shell_casing(position.x, position.y)
                # P2-01: Enriched combat particles — dirt splash, blood pool, hit marker
                position = effect["position"]
                is_kill = effect.get("is_kill", False)
                if hasattr(renderer, "spawn_dirt_splash"):
                    renderer.spawn_dirt_splash(position.x, position.y, count=8)
                if is_kill and hasattr(renderer, "spawn_blood_pool"):
                    renderer.spawn_blood_pool(position.x, position.y, size=10)
                if hasattr(renderer, "spawn_hit_marker"):
                    renderer.spawn_hit_marker(
                        position.x, position.y, damage_type="critical" if is_kill else "normal"
                    )
                # 爆炸武器触发大爆炸 + 屏幕震动
                weapon_id = effect.get("weapon_id", "")
                if weapon_id and self._is_explosive_weapon(weapon_id):
                    renderer.spawn_explosion(effect["position"], "large")
                    if camera and hasattr(camera, "shake"):
                        camera.shake(3.0, 0.15)
                    # P2-03: Warm white flash for large explosions
                    if hasattr(renderer, "trigger_flash"):
                        renderer.trigger_flash((255, 240, 200), 0.5, 0.15)
                    self.event_bus.publish_named(
                        "Explosion",
                        {
                            "intensity": 4.0,
                            "position": (
                                effect["position"].x if hasattr(effect["position"], "x") else 0,
                                effect["position"].y if hasattr(effect["position"], "y") else 0,
                            ),
                            "weapon_id": weapon_id,
                        },
                    )
                else:
                    renderer.spawn_explosion(effect["position"], "small")
                    if camera and hasattr(camera, "shake"):
                        camera.shake(1.5, 0.1)
                # P2-03: Pale red flash for fatal / killing blows
                if is_kill and hasattr(renderer, "trigger_flash"):
                    renderer.trigger_flash((255, 100, 100), 0.3, 0.12)
                if self.sound_system:
                    self.sound_system.play_hit(is_critical=effect.get("is_kill", False))
            elif etype == "muzzle":
                renderer.spawn_muzzle_flash(effect["position"], effect.get("direction", 0))
            elif etype == "death":
                renderer.spawn_death_effect(effect["unit_id"], effect["position"])
                if self.sound_system:
                    self.sound_system.play_death()
            elif etype == "smoke":
                renderer.spawn_smoke_screen(effect["position"], radius=effect.get("radius", 64.0))

        self._pending_effects.clear()

    @staticmethod
    def _is_explosive_weapon(weapon_id: str) -> bool:
        explosive_keywords = (
            "tank_cannon",
            "mortar",
            "at_gun",
            "bazooka",
            "piat",
            "panzerschreck",
            "panzerfaust",
        )
        wid_lower = weapon_id.lower()
        return any(kw in wid_lower for kw in explosive_keywords)

    def process_deaths(self, units: list[Unit], battle_stats: BattleStats | None = None) -> None:
        """Record casualties for dead units into the battle stats."""
        dead_units = [u for u in units if not u.is_alive]
        for unit in dead_units:
            if battle_stats:
                faction = "allies" if unit.faction.name == "ALLIES" else "axis"
                battle_stats.record_unit_lost(faction)

    def process_movements(self, units: list[Unit], game_map: GameMap) -> None:
        """Advance pending unit movements along their queued paths."""
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
            # Use Vec2.TILE_SIZE (32) for consistent coordinate system
            ts = Vec2.TILE_SIZE
            target_vec = Vec2(target_tc.x * ts + ts // 2, target_tc.y * ts + ts // 2)
            current_vec = unit.position.pixel_position

            diff_x = target_vec.x - current_vec.x
            diff_y = target_vec.y - current_vec.y
            dist = math.sqrt(diff_x * diff_x + diff_y * diff_y)

            move_pixels = moved * ts

            if dist <= move_pixels:
                unit.position.tile_coord = target_tc
                unit.update_garrison_status(game_map)
                path.popleft()
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
                else:
                    self._move_orders[unit.id]["path"] = path
            else:
                ratio = move_pixels / dist
                new_x = current_vec.x + diff_x * ratio
                new_y = current_vec.y + diff_y * ratio
                tile_x = int(new_x // ts)
                tile_y = int(new_y // ts)
                unit.position.tile_coord = TileCoord(tile_x, tile_y)
                unit.update_garrison_status(game_map)
                unit.position.set_pixel_offset(Vec2(new_x - tile_x * ts, new_y - tile_y * ts))
                unit.position.set_facing_toward(target_tc)

    def tick_weapon_reload(self, units: list[Unit]) -> None:
        """Advance weapon reload progress for all currently reloading units."""
        for unit in units:
            if unit.weapon.state.name == "RELOADING":
                unit.weapon.tick()
