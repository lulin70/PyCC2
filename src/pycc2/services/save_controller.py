from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.services.game_loop import GameLoop

logger = logging.getLogger(__name__)


@dataclass
class SaveController:
    save_manager: object | None = None

    def initialize(self) -> None:
        from pycc2.infrastructure.save_system import SecureSaveManager

        self.save_manager = SecureSaveManager()

    def quick_save(self, slot: int = 0, game_loop: GameLoop | None = None) -> bool:
        if self.save_manager is None or game_loop is None:
            return False
        from pycc2.infrastructure.save_system import SaveMetaData

        state_dict = self.export_state(game_loop)
        meta = SaveMetaData(
            tick=game_loop.state.tick,
            allies_alive=sum(
                1 for u in game_loop.state.units if u.faction.name == "ALLIES" and u.is_alive
            ),
            axis_alive=sum(
                1 for u in game_loop.state.units if u.faction.name == "AXIS" and u.is_alive
            ),
        )
        result = self.save_manager.save_game(slot, state_dict, meta)
        if result and game_loop.sound_system:
            game_loop.sound_system.play_ui_command()
        return result

    def quick_load(self, slot: int = 0, game_loop: GameLoop | None = None) -> bool:
        if self.save_manager is None or game_loop is None:
            return False
        state_dict, meta, status = self.save_manager.load_game(slot)
        if status.name not in ("OK", "INCOMPATIBLE") or state_dict is None:
            if game_loop.sound_system:
                from pycc2.presentation.audio.sound_system import SoundType

                game_loop.sound_system.play(SoundType.UI_CANCEL)
            return False

        try:
            restored = self.restore_state(state_dict, game_loop)
            if restored:
                if game_loop.sound_system:
                    game_loop.sound_system.play_ui_command()
                return True
        except Exception:
            pass

        if game_loop.sound_system:
            from pycc2.presentation.audio.sound_system import SoundType

            game_loop.sound_system.play(SoundType.UI_CANCEL)
        return False

    def list_saves(self) -> list:
        if self.save_manager is None:
            return []
        return self.save_manager.list_all_slots()

    def export_state(self, game_loop: GameLoop) -> dict:
        if hasattr(self.save_manager, "export_state_from_game_loop"):
            return self.save_manager.export_state_from_game_loop(game_loop)

        state = game_loop.state
        units_data = []
        for unit in state.units:
            unit_dict = {
                "id": unit.id,
                "name": unit.name,
                "faction": unit.faction.name,
                "unit_type": unit.unit_type.name,
                "health": {
                    "hp": unit.health.hp,
                    "max_hp": unit.health.max_hp,
                    "state": unit.health.state.name,
                },
                "morale": {
                    "value": unit.morale.value,
                    "panic_threshold": unit.morale.panic_threshold,
                    "suppression": unit.morale.suppression,
                    "state": unit.morale.state.name,
                },
                "weapon": {
                    "primary_weapon_id": unit.weapon.primary_weapon_id,
                    "ammo_remaining": unit.weapon.ammo_remaining,
                    "max_ammo": unit.weapon.max_ammo,
                    "reload_ticks_left": unit.weapon.reload_ticks_left,
                    "state": unit.weapon.state.name,
                },
                "position": {
                    "tile_coord": {
                        "x": unit.position.tile_coord.x,
                        "y": unit.position.tile_coord.y,
                    },
                    "pixel_position": {
                        "x": unit.position.pixel_position.x,
                        "y": unit.position.pixel_position.y,
                    },
                    "facing_rad": unit.position.facing_rad,
                },
                "vision": {
                    "range_tiles": unit.vision.range_tiles,
                    "angle_rad": unit.vision.angle_rad,
                },
                "squad_id": unit.squad_id,
            }
            units_data.append(unit_dict)

        cam = state.camera
        return {
            "tick": state.tick,
            "paused": state.paused,
            "camera": {
                "position": {"x": cam.position.x, "y": cam.position.y},
                "zoom": cam.zoom,
            },
            "selected_unit_ids": list(state.selected_unit_ids),
            "units": units_data,
        }

    def restore_state(self, data: dict, game_loop: GameLoop) -> bool:
        """Reconstruct game state from a saved state dictionary."""

        from pycc2.domain.components.health_component import HealthComponent, HealthState
        from pycc2.domain.components.morale_component import MoraleComponent, MoraleState
        from pycc2.domain.components.position_component import PositionComponent
        from pycc2.domain.components.vision_component import VisionComponent
        from pycc2.domain.components.weapon_component import WeaponComponent, WeaponState
        from pycc2.domain.entities.unit import Faction, Unit, UnitType
        from pycc2.domain.value_objects.tile_coord import TileCoord
        from pycc2.domain.value_objects.vec2 import Vec2

        state = game_loop.state
        state.tick = data.get("tick", 0)
        state.paused = data.get("paused", False)

        cam_data = data.get("camera", {})
        if cam_data:
            state.camera.position = Vec2(
                cam_data.get("position", {}).get("x", 0.0),
                cam_data.get("position", {}).get("y", 0.0),
            )
            state.camera.zoom = cam_data.get("zoom", 1.0)

        state.selected_unit_ids = set(data.get("selected_unit_ids", []))

        units_data = data.get("units", [])
        if not units_data:
            return False

        new_units = []
        for ud in units_data:
            try:
                faction = Faction[ud.get("faction", "ALLIES")]
                unit_type = UnitType[ud.get("unit_type", "INFANTRY_SQUAD")]

                hp_data = ud.get("health", {})
                health = HealthComponent(
                    hp=hp_data.get("hp", 100),
                    max_hp=hp_data.get("max_hp", 100),
                    state=HealthState[hp_data.get("state", "HEALTHY")],
                )

                morale_data = ud.get("morale", {})
                morale = MoraleComponent(
                    value=morale_data.get("value", 85),
                    panic_threshold=morale_data.get("panic_threshold", 20),
                    suppression=morale_data.get("suppression", 0),
                    state=MoraleState[morale_data.get("state", "NORMAL")],
                )

                weapon_data = ud.get("weapon", {})
                weapon = WeaponComponent(
                    primary_weapon_id=weapon_data.get("primary_weapon_id", "rifle"),
                    ammo_remaining=weapon_data.get("ammo_remaining", 10),
                    max_ammo=weapon_data.get("max_ammo", 10),
                    reload_ticks_left=weapon_data.get("reload_ticks_left", 0),
                    state=WeaponState[weapon_data.get("state", "READY")],
                )

                pos_data = ud.get("position", {})
                tc = pos_data.get("tile_coord", {"x": 0, "y": 0})
                po = pos_data.get("pixel_offset", {"x": 0.0, "y": 0.0})
                position = PositionComponent(
                    tile_coord=TileCoord(tc["x"], tc["y"]),
                    pixel_position=Vec2(
                        tc["x"] * 48 + po.get("x", 0.0),
                        tc["y"] * 48 + po.get("y", 0.0),
                    ),
                    facing_rad=pos_data.get("facing_rad", 0.0),
                )

                vis_data = ud.get("vision", {})
                vision = VisionComponent(
                    range_tiles=vis_data.get("range_tiles", 5),
                    angle_rad=vis_data.get("angle_rad", math.pi * 0.6),
                )

                unit = Unit(
                    id=ud.get("id", f"restored_{len(new_units)}"),
                    name=ud.get("name", "Restored Unit"),
                    faction=faction,
                    unit_type=unit_type,
                    health=health,
                    morale=morale,
                    weapon=weapon,
                    position=position,
                    vision=vision,
                    squad_id=ud.get("squad_id"),
                )
                new_units.append(unit)
            except (KeyError, ValueError):
                continue

        if not new_units:
            return False

        state.units = new_units

        if hasattr(game_loop, "renderer") and hasattr(game_loop.renderer, "_unit_animators"):
            game_loop.renderer._unit_animators.clear()
        if hasattr(game_loop, "renderer") and hasattr(game_loop.renderer, "_particle_emitter"):
            game_loop.renderer._particle_emitter.clear()

        return True
