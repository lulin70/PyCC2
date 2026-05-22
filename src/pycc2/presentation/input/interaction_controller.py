from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.tile_coord import TileCoord
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.services.event_bus import EventBus


class InteractionMode(Enum):
    SELECT = auto()
    MOVE = auto()
    ATTACK = auto()
    PAN_ONLY = auto()


@dataclass(slots=True)
class ClickResult:
    hit_unit: Unit | None = None
    world_position: TileCoord | None = None
    screen_position: tuple[float, float] = (0.0, 0.0)
    is_terrain_click: bool = False
    is_unit_click: bool = False


class InteractionController:
    def __init__(
        self,
        camera: Camera,
        game_map: GameMap,
        event_bus: EventBus,
    ) -> None:
        self._camera = camera
        self._game_map = game_map
        self._event_bus = event_bus
        self._mode = InteractionMode.SELECT
        self._selected_ids: set[str] = set()
        self._selection_start: tuple[float, float] | None = None
        self._on_unit_selected: Callable[[set[str]], None] | None = None
        self._on_move_command: Callable[[set[str], TileCoord], None] | None = None
        self._on_attack_command: Callable[[set[str], str], None] | None = None
        self._on_deselect: Callable[[], None] | None = None

    @property
    def mode(self) -> InteractionMode:
        return self._mode

    @property
    def camera(self) -> Camera:
        return self._camera

    @property
    def selected_unit_ids(self) -> set[str]:
        return self._selected_ids

    def set_mode(self, mode: InteractionMode) -> None:
        self._mode = mode

    def screen_to_tile(self, screen_pos: tuple[float, float]) -> TileCoord:
        from pycc2.domain.value_objects.tile_coord import TileCoord

        if self._camera is None or self._game_map is None:
            return TileCoord(0, 0)
        world_vec = self._camera.screen_to_world(screen_pos)
        tile_x = int(world_vec.x // 32)
        tile_y = int(world_vec.y // 32)
        tile_x = max(0, min(tile_x, self._game_map.width - 1))
        tile_y = max(0, min(tile_y, self._game_map.height - 1))
        return TileCoord(tile_x, tile_y)

    def hit_test(self, screen_pos: tuple[float, float], units: list[Unit]) -> ClickResult:
        """Test if click hits any unit - with EXTREME defensive coding."""
        if self._camera is None or not units:
            return ClickResult(
                hit_unit=None,
                world_position=self.screen_to_tile(screen_pos),
                screen_position=screen_pos,
                is_terrain_click=True,
                is_unit_click=False,
            )

        # DEBUG: Log hit test call
        print(f"[HIT_TEST] Testing click at {screen_pos} against {len(units)} units")

        world_vec = self._camera.screen_to_world(screen_pos)
        tile_coord = self.screen_to_tile(screen_pos)

        hit_unit = None
        min_dist_sq = float("inf")

        # Type → radius mapping (use string keys for safety)
        type_radius = {
            "INFANTRY_SQUAD": 20,      # Increased for easier clicking
            "RIFLE_SQUAD": 20,
            "MACHINE_GUN_SQUAD": 24,
            "MG_TEAM": 24,
            "AT_GUN_TEAM": 22,
            "AT_TEAM": 22,
            "COMMANDER": 18,
            "MORTAR_TEAM": 22,
            "SNIPER_TEAM": 16,
            "SCOUT_TEAM": 16,
            "ENGINEER_SQUAD": 20,
            "ASSAULT_SQUAD": 20,
            "FLAMETHROWER_TEAM": 20,
            # Vehicle types (larger radius for easier selection)
            "SHERMAN_TANK": 30,
            "M4_SHERMAN": 30,
            "M5_STUART": 28,
            "TANK": 30,
            "VEHICLE": 28,
            "HALFTRACK": 26,
            # Generic fallbacks
            "INFANTRY": 20,
            "SUPPORT": 22,
            "RECON": 18,
            "ARMOR": 28,
            "DEFAULT": 20,  # Safe default
        }

        for idx, unit in enumerate(units):
            try:
                # Skip dead units
                is_alive = getattr(unit, 'is_alive', True)
                if not is_alive:
                    continue

                # Get unit position with fallbacks
                upos = None
                if hasattr(unit, 'position') and unit.position is not None:
                    if hasattr(unit.position, 'pixel_position'):
                        upos = unit.position.pixel_position
                    elif hasattr(unit.position, 'tile_position'):
                        # Convert tile to pixel position
                        from pycc2.domain.value_objects.vec2 import Vec2
                        tile_x = getattr(unit.position, 'tile_x', 0) or 0
                        tile_y = getattr(unit.position, 'tile_y', 0) or 0
                        upos = Vec2(tile_x * 32, tile_y * 32)

                if upos is None:
                    continue  # Skip units without valid position

                # Calculate distance
                dx = world_vec.x - upos.x
                dy = world_vec.y - upos.y
                dist_sq = dx * dx + dy * dy

                # Get radius with multiple fallback strategies
                radius = 20 * self._camera.zoom  # Default safe radius

                # Try to get type-specific radius
                try:
                    unit_type_str = str(unit.unit_type).upper() if hasattr(unit, 'unit_type') else ""
                    
                    # Try .name first (for enum types), then direct string match
                    if hasattr(unit.unit_type, 'name'):
                        type_key = unit.unit_type.name.upper()
                    else:
                        type_key = unit_type_str
                    
                    radius = type_radius.get(type_key, 20) * self._camera.zoom
                except Exception:
                    pass  # Use default radius

                # Ensure minimum radius for easy clicking
                radius = max(radius, 15 * self._camera.zoom)

                # Check if within radius
                if dist_sq <= radius * radius and dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    hit_unit = unit

            except Exception as e:
                # CRITICAL: Never crash on a single unit - just skip it
                print(f"[WARN] hit_test failed for unit {idx}: {e}")
                continue

        # DEBUG: Log result
        if hit_unit:
            print(f"[HIT_TEST] ✓ HIT unit: {getattr(hit_unit, 'display_name', hit_unit.id)}")
        else:
            print(f"[HIT_TEST] ✗ No unit hit (min_dist_sq={min_dist_sq:.1f})")

        return ClickResult(
            hit_unit=hit_unit,
            world_position=tile_coord,
            screen_position=screen_pos,
            is_terrain_click=hit_unit is None,
            is_unit_click=hit_unit is not None,
        )

    def handle_left_click(
        self,
        screen_pos: tuple[float, float],
        units: list[Unit],
        modifiers: tuple[bool, ...] = (False, False, False, False),
    ) -> set[str]:
        result = self.hit_test(screen_pos, units)

        # In MOVE or ATTACK mode, execute command on left click
        if self._mode == InteractionMode.MOVE:
            self._mode = InteractionMode.SELECT
            if self._on_move_command and self._camera:
                # Convert screen position to WORLD pixel coordinates (not tile!)
                world_vec = self._camera.screen_to_world(screen_pos)
                self._on_move_command(self._selected_ids, world_vec)
                logger.info(f"[MOVE] Command: {len(self._selected_ids)} units -> ({world_vec.x:.0f}, {world_vec.y:.0f})")
            return set(self._selected_ids)

        if self._mode == InteractionMode.ATTACK:
            self._mode = InteractionMode.SELECT
            if result.is_unit_click and result.hit_unit:
                target = result.hit_unit
                selected_unit = next(
                    (u for u in units if u.id == next(iter(self._selected_ids), None)),
                    None,
                )
                if selected_unit and target.faction != selected_unit.faction:
                    if self._on_attack_command:
                        self._on_attack_command(self._selected_ids, target.id)
                    self._event_bus.publish({
                        "command": "attack",
                        "unit_ids": list(self._selected_ids),
                        "target_id": target.id,
                    })
            return set(self._selected_ids)

        shift_held = modifiers[1]

        if result.is_unit_click and result.hit_unit:
            uid = result.hit_unit.id
            if shift_held:
                if uid in self._selected_ids:
                    self._selected_ids.discard(uid)
                else:
                    self._selected_ids.add(uid)
            else:
                self._selected_ids = {uid}
        else:
            if not shift_held:
                self._selected_ids.clear()

        if self._on_unit_selected:
            self._on_unit_selected(self._selected_ids)

        return set(self._selected_ids)

    def handle_right_click(self, screen_pos: tuple[float, float], units: list[Unit]) -> None:
        if not self._selected_ids:
            return

        result = self.hit_test(screen_pos, units)

        if result.is_unit_click and result.hit_unit:
            target = result.hit_unit
            selected_unit = next(
                (u for u in units if u.id == next(iter(self._selected_ids), None)),
                None,
            )
            if selected_unit and target.faction != selected_unit.faction:
                if self._on_attack_command:
                    self._on_attack_command(self._selected_ids, target.id)
                self._event_bus.publish(
                    {
                        "command": "attack",
                        "unit_ids": list(self._selected_ids),
                        "target_id": target.id,
                    }
                )
            return

        if result.world_position and self._on_move_command:
            self._on_move_command(self._selected_ids, result.world_position)
            self._event_bus.publish(
                {
                    "command": "move",
                    "unit_ids": list(self._selected_ids),
                    "target": (result.world_position.x, result.world_position.y),
                }
            )

    def handle_shortcut_key(self, key: int) -> None:
        import pygame

        if key == pygame.K_m:
            self._mode = InteractionMode.MOVE
        elif key == pygame.K_a:
            self._mode = InteractionMode.ATTACK
        elif key == pygame.K_ESCAPE:
            self._mode = InteractionMode.SELECT
            self._selected_ids.clear()
            if self._on_deselect:
                self._on_deselect()
        elif key == pygame.K_s:
            self._event_bus.publish(
                {
                    "command": "stop",
                    "unit_ids": list(self._selected_ids),
                }
            )
        elif key == pygame.K_k:
            self._event_bus.publish(
                {
                    "command": "smoke",
                    "unit_ids": list(self._selected_ids),
                }
            )
        elif key == pygame.K_d:
            self._event_bus.publish(
                {
                    "command": "defend",
                    "unit_ids": list(self._selected_ids),
                }
            )

    def register_on_selected(self, callback: Callable[[set[str]], None]) -> None:
        self._on_unit_selected = callback

    def register_on_move(self, callback: Callable[[set[str], TileCoord], None]) -> None:
        self._on_move_command = callback

    def register_on_attack(self, callback: Callable[[set[str], str], None]) -> None:
        self._on_attack_command = callback

    def register_on_deselect(self, callback: Callable[[], None]) -> None:
        self._on_deselect = callback

    def clear_selection(self) -> None:
        self._selected_ids.clear()
        self._mode = InteractionMode.SELECT
