from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from pycc2.domain.interfaces import IEventPublisher
from pycc2.domain.interfaces.event_types import PlayerCommand

from pycc2.presentation.ui.cursor_manager import CursorManager, CursorType
from pycc2.presentation.ui.radial_menu import RadialMenu, RadialCommand

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.tile_coord import TileCoord
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.input.attack_line_system import AttackLineSystem
from pycc2.domain.value_objects.audio_enums import InteractionMode  # noqa: F401 — re-exported for backward compat


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
        event_bus: IEventPublisher,
    ) -> None:
        self._camera = camera
        self._game_map = game_map
        self._event_bus = event_bus
        self._mode = InteractionMode.SELECT
        self._move_fast = False
        self._move_sneak = False
        self._selected_ids: set[str] = set()
        self._selection_start: tuple[float, float] | None = None
        self._on_unit_selected: Callable[[set[str]], None] | None = None
        self._on_move_command: Callable[[set[str], "Vec2"], None] | None = None
        self._on_attack_command: Callable[[set[str], str], None] | None = None
        self._on_deselect: Callable[[], None] | None = None

        # Attack line system (CC2-style)
        from pycc2.presentation.input.attack_line_system import AttackLineSystem
        self.attack_line: AttackLineSystem = AttackLineSystem()

        # Radial menu and drag-style command interaction (CC2-style)
        self._radial_menu = RadialMenu()
        self._is_right_dragging: bool = False
        self._drag_start_pos: tuple[int, int] | None = None
        self._selected_command: RadialCommand | None = None
        self._ctrl_held: bool = False

        # Context-sensitive cursor (CC2-style)
        self.cursor_manager: CursorManager = CursorManager()

        # First-time operation guidance (PS-10)
        self._shown_hints: set[str] = set()
        self._hint_manager: object | None = None

        # Customizable keybindings (PS-11)
        self._keybind_manager: object | None = None

    def set_hint_manager(self, hint_manager: object) -> None:
        """Set the hint manager for first-time operation guidance."""
        self._hint_manager = hint_manager

    def set_keybind_manager(self, keybind_manager: object) -> None:
        """Set the keybind manager for customizable keybindings."""
        self._keybind_manager = keybind_manager

    def _show_first_time_hint(self, hint_id: str, text: str, x: float = 0.0, y: float = 0.0) -> None:
        """Show a first-time hint if not already shown this session."""
        if hint_id in self._shown_hints:
            return
        self._shown_hints.add(hint_id)
        if self._hint_manager and hasattr(self._hint_manager, 'show_hint'):
            self._hint_manager.show_hint(text, x, y, lifetime=240)

    @property
    def mode(self) -> InteractionMode:
        return self._mode

    @property
    def camera(self) -> Camera:
        return self._camera

    @property
    def selected_unit_ids(self) -> set[str]:
        return self._selected_ids

    def set_mode(self, mode: InteractionMode, fast: bool = False, sneak: bool = False) -> None:
        self._mode = mode
        self._move_fast = fast
        self._move_sneak = sneak
        # Update cursor based on new mode
        if mode == InteractionMode.MOVE:
            self.cursor_manager.set_cursor(CursorType.MOVE)
        elif mode == InteractionMode.ATTACK:
            self.cursor_manager.set_cursor(CursorType.ATTACK)
        else:
            self.cursor_manager.set_cursor(CursorType.DEFAULT)

    def screen_to_tile(self, screen_pos: tuple[float, float]) -> TileCoord:
        from pycc2.domain.value_objects.tile_coord import TileCoord

        if self._camera is None or self._game_map is None:
            return TileCoord(0, 0)
        world_vec = self._camera.screen_to_world(screen_pos)

        from pycc2.presentation.rendering.camera import ProjectionMode
        if self._camera.projection == ProjectionMode.ISOMETRIC:
            # In isometric mode, use isometric-aware tile picking
            # Camera.screen_to_world already handles the inverse isometric transform
            tile_x = int(world_vec.x // 32)
            tile_y = int(world_vec.y // 32)
        else:
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
                except Exception as e:
                    logging.debug(f"Unit click radius lookup failed: {e}")

                # Ensure minimum radius for easy clicking
                radius = max(radius, 15 * self._camera.zoom)

                # Check if within radius
                if dist_sq <= radius * radius and dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    hit_unit = unit

            except Exception as e:
                # CRITICAL: Never crash on a single unit - just skip it
                logger.warning("hit_test failed for unit %d: %s", idx, e)
                continue

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
            self.cursor_manager.set_cursor(CursorType.DEFAULT)
            if self._on_move_command and self._camera:
                # Convert screen position to WORLD pixel coordinates (not tile!)
                world_vec = self._camera.screen_to_world(screen_pos)
                self._on_move_command(self._selected_ids, world_vec)
                logger.info(f"[MOVE] Command: {len(self._selected_ids)} units -> ({world_vec.x:.0f}, {world_vec.y:.0f})")
            return set(self._selected_ids)

        if self._mode == InteractionMode.ATTACK:
            # CC2-style: Click confirms attack target
            if self.attack_line.state.active:
                # Confirm the current attack target
                if self.attack_line.state.target:
                    target = self.attack_line.state.target
                    selected_unit = next(
                        (u for u in units if u.id == next(iter(self._selected_ids), None)),
                        None,
                    )

                    # Evaluate final status
                    if selected_unit:
                        target.status = self.attack_line.evaluate_attack(
                            attacker=selected_unit,
                            target=target,
                            game_map=self._game_map,
                        )

                    # Lock in the attack
                    self.attack_line.confirm_attack(target)

                    logger.info(
                        f"[ATTACK] Confirmed: {len(self._selected_ids)} units -> "
                        f"{'unit '+target.unit_id if target.unit_id else 'ground'} "
                        f"({target.position.x:.0f},{target.position.y:.0f}) "
                        f"status={target.status.name}"
                    )

                    # Execute attack command
                    if target.status.name in ('CAN_ATTACK', 'TRACKING_UNIT', 'HIT_HIGH', 'HIT_MODERATE', 'HIT_LOW'):
                        if target.unit_id and self._on_attack_command:
                            self._on_attack_command(self._selected_ids, target.unit_id)
                        elif not target.unit_id:
                            # Ground target attack
                            if self._on_move_command:  # Reuse for ground attack
                                self._on_move_command(self._selected_ids, target.position)

                        self._event_bus.publish_named("AttackCommand", {
                            "command": "attack",
                            "unit_ids": list(self._selected_ids),
                            "target_id": target.unit_id,
                            "target_pos": (target.position.x, target.position.y),
                            "is_ground_target": target.is_ground_target,
                        })
                    else:
                        logger.warning(f"[ATTACK] Cannot attack - {target.status.name}")

                self._mode = InteractionMode.SELECT
                self.cursor_manager.set_cursor(CursorType.DEFAULT)
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

        # PS-10: First-time hint when selecting a unit
        if self._selected_ids:
            self._show_first_time_hint(
                "first_unit_selected",
                "Right-click and drag to issue commands via radial menu",
            )

        return set(self._selected_ids)

    def handle_mouse_move(
        self,
        screen_pos: tuple[float, float],
        units: list[Unit],
    ) -> None:
        """Handle mouse movement for attack line preview and cursor updates."""
        # Update cursor based on hover context when in SELECT mode
        if self._mode == InteractionMode.SELECT and self._selected_ids:
            result = self.hit_test(screen_pos, units)
            if result.is_unit_click and result.hit_unit:
                # Check if hoverable unit is friendly (selectable) or enemy
                selected_id = next(iter(self._selected_ids), None)
                if selected_id:
                    selected_unit = next((u for u in units if u.id == selected_id), None)
                    if selected_unit and result.hit_unit.faction != selected_unit.faction:
                        self.cursor_manager.set_cursor(CursorType.ATTACK)
                    else:
                        self.cursor_manager.set_cursor(CursorType.SELECT)
                else:
                    self.cursor_manager.set_cursor(CursorType.SELECT)
            else:
                self.cursor_manager.set_cursor(CursorType.DEFAULT)
        elif self._mode == InteractionMode.SELECT and not self._selected_ids:
            # No selection - check if hovering over a selectable unit
            result = self.hit_test(screen_pos, units)
            if result.is_unit_click and result.hit_unit:
                self.cursor_manager.set_cursor(CursorType.SELECT)
            else:
                self.cursor_manager.set_cursor(CursorType.DEFAULT)

        if self._mode != InteractionMode.ATTACK:
            return

        if not self.attack_line.state.active or not self._camera:
            return

        # Convert to world coordinates
        world_vec = self._camera.screen_to_world(screen_pos)

        # Get attacker faction
        attacker_faction = "allied"  # Default
        selected_id = next(iter(self._selected_ids), None)
        if selected_id:
            for u in units:
                if u.id == selected_id:
                    attacker_faction = u.faction
                    break

        # Update attack line target
        target = self.attack_line.update_mouse_position(
            screen_pos=screen_pos,
            world_pos=world_vec,
            units=units,
            attacker_faction=attacker_faction,
        )

        # Evaluate attack status (range, LOS)
        if selected_id:
            attacker = next((u for u in units if u.id == selected_id), None)
            if attacker:
                target.status = self.attack_line.evaluate_attack(
                    attacker=attacker,
                    target=target,
                    game_map=self._game_map,
                )

    def handle_right_click(self, screen_pos: tuple[float, float], units: list[Unit], shift_held: bool = False) -> None:
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
                if shift_held:
                    # Shift+right-click: queue attack command
                    for uid in self._selected_ids:
                        u = next((x for x in units if x.id == uid), None)
                        if u:
                            u.queue_command('attack', target_id=target.id)
                    logger.info(f"[QUEUE] Attack queued for {len(self._selected_ids)} units -> {target.id}")
                else:
                    if self._on_attack_command:
                        self._on_attack_command(self._selected_ids, target.id)
                # PS-10: First-time hint when attack is issued
                self._show_first_time_hint(
                    "first_attack",
                    "Green line = high hit chance, Red = low, Black = impossible",
                )
                self._event_bus.publish(
                    {
                        "command": "attack",
                        "unit_ids": list(self._selected_ids),
                        "target_id": target.id,
                        "queued": shift_held,
                    }
                )
            return

        if result.world_position:
            if shift_held:
                # Shift+right-click: queue move command
                for uid in self._selected_ids:
                    u = next((x for x in units if x.id == uid), None)
                    if u:
                        u.queue_command('move', target_x=result.world_position.x, target_y=result.world_position.y)
                logger.info(f"[QUEUE] Move queued for {len(self._selected_ids)} units -> ({result.world_position.x}, {result.world_position.y})")
            else:
                if self._on_move_command:
                    self._on_move_command(self._selected_ids, result.world_position)
            self._event_bus.publish(
                {
                    "command": "move",
                    "unit_ids": list(self._selected_ids),
                    "target": (result.world_position.x, result.world_position.y),
                    "queued": shift_held,
                }
            )

    def handle_shortcut_key(self, key: int) -> None:
        import pygame

        # PS-11: Use KeybindManager if available, otherwise fall back to hardcoded keys
        action = None
        if self._keybind_manager:
            action = self._keybind_manager.get_action(key)

        if action == 'move' or (not action and key == pygame.K_z):
            # Move: Z (CC2 standard) or custom key
            self._mode = InteractionMode.MOVE
            self.cursor_manager.set_cursor(CursorType.MOVE)
        elif action == 'fire' or (not action and key == pygame.K_c):
            # Fire/Attack: C (CC2 standard) or custom key
            self._mode = InteractionMode.ATTACK
            self.cursor_manager.set_cursor(CursorType.ATTACK)
        elif action == 'cancel' or key == pygame.K_ESCAPE:
            self._mode = InteractionMode.SELECT
            self.cursor_manager.set_cursor(CursorType.DEFAULT)
            self._selected_ids.clear()
            if self._on_deselect:
                self._on_deselect()
        elif action == 'sneak' or (not action and key == pygame.K_s):
            # Sneak command: S (CC2 standard) or custom key
            self.cursor_manager.set_cursor(CursorType.MOVE)
            self._event_bus.publish(
                {
                    "command": "sneak",
                    "unit_ids": list(self._selected_ids),
                }
            )
        elif action == 'smoke' or (not action and key == pygame.K_v):
            # Smoke: V (CC2 standard) or custom key
            self.cursor_manager.set_cursor(CursorType.SMOKE)
            self._event_bus.publish(
                {
                    "command": "smoke",
                    "unit_ids": list(self._selected_ids),
                }
            )
        elif action == 'defend' or (not action and key == pygame.K_d):
            # Defend command: D (CC2 standard) or custom key
            self._event_bus.publish(
                {
                    "command": "defend",
                    "unit_ids": list(self._selected_ids),
                }
            )
        elif action == 'move_fast' or (not action and key == pygame.K_x):
            # Fast Move: X (CC2 standard) or custom key
            self._event_bus.publish(
                {
                    "command": "fast_move",
                    "unit_ids": list(self._selected_ids),
                }
            )
        elif action == 'hide' or (not action and key == pygame.K_h):
            # Hide command: H (CC2 standard) or custom key
            self._event_bus.publish(
                {
                    "command": "hide",
                    "unit_ids": list(self._selected_ids),
                }
            )
        elif key == pygame.K_i:
            # Toggle between ORTHOGRAPHIC and ISOMETRIC projection
            from pycc2.presentation.rendering.camera import ProjectionMode
            if self._camera.projection == ProjectionMode.ORTHOGRAPHIC:
                self._camera.projection = ProjectionMode.ISOMETRIC
            else:
                self._camera.projection = ProjectionMode.ORTHOGRAPHIC

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
        self.cursor_manager.set_cursor(CursorType.DEFAULT)

    # ====== Radial menu drag-style command interaction (CC2-style) ======

    def handle_right_mouse_down(
        self,
        screen_pos: tuple[int, int],
        units: list[Unit],
    ) -> None:
        """Handle right mouse button DOWN on a selected unit → show radial menu."""
        if not self._selected_ids:
            return

        # Check if right-clicking on/near a selected unit
        result = self.hit_test(screen_pos, units)
        if result.is_unit_click and result.hit_unit and result.hit_unit.id in self._selected_ids:
            # Right-click-hold on selected unit → show radial menu
            self._is_right_dragging = True
            self._drag_start_pos = screen_pos
            self._selected_command = None
            self._radial_menu.show(screen_pos)

            # PS-10: First-time hint when radial menu is shown
            self._show_first_time_hint(
                "first_radial_menu",
                "Drag toward a command, then to a target location",
            )

    def handle_right_mouse_up(
        self,
        screen_pos: tuple[int, int],
        units: list[Unit],
    ) -> None:
        """Handle right mouse button UP → execute selected command, hide menu."""
        if self._is_right_dragging and self._radial_menu.is_visible:
            cmd = self._radial_menu.hovered_command
            if cmd is not None:
                self._execute_radial_command(cmd, screen_pos, units)
            self._radial_menu.hide()

        self._is_right_dragging = False
        self._drag_start_pos = None
        self._selected_command = None

    def handle_drag_motion(
        self,
        screen_pos: tuple[int, int],
    ) -> None:
        """Handle mouse MOTION while right button held → update radial menu hover."""
        if self._is_right_dragging and self._radial_menu.is_visible:
            self._radial_menu.update_hover(screen_pos)

    def _execute_radial_command(
        self,
        command: RadialCommand,
        screen_pos: tuple[int, int],
        units: list[Unit],
    ) -> None:
        """Execute a command selected from the radial menu."""
        if not self._selected_ids:
            return

        command_map = {
            RadialCommand.MOVE: "move",
            RadialCommand.MOVE_FAST: "fast_move",
            RadialCommand.SNEAK: "sneak",
            RadialCommand.FIRE: "attack",
            RadialCommand.SMOKE: "smoke",
            RadialCommand.DEFEND: "defend",
            RadialCommand.HIDE: "hide",
        }

        cmd_name = command_map.get(command, "move")

        if cmd_name in ("move", "fast_move", "sneak"):
            # Move-type commands: target is the terrain at release position
            result = self.hit_test(screen_pos, units)
            if result.world_position and self._on_move_command:
                self._on_move_command(self._selected_ids, result.world_position)
                # Set movement mode
                if cmd_name == "fast_move":
                    self._event_bus.publish(PlayerCommand(command="fast_move", unit_ids=list(self._selected_ids)))
                elif cmd_name == "sneak":
                    self._event_bus.publish(PlayerCommand(command="sneak", unit_ids=list(self._selected_ids)))
            self._event_bus.publish(PlayerCommand(
                command=cmd_name,
                unit_ids=list(self._selected_ids),
                target=(
                    result.world_position.x if result.world_position else 0,
                    result.world_position.y if result.world_position else 0,
                ),
            ))
        elif cmd_name == "attack":
            # Attack command: target is the unit at release position
            result = self.hit_test(screen_pos, units)
            if result.is_unit_click and result.hit_unit and self._on_attack_command:
                self._on_attack_command(self._selected_ids, result.hit_unit.id)
            self._event_bus.publish(PlayerCommand(
                command="attack",
                unit_ids=list(self._selected_ids),
                target_id=result.hit_unit.id if result.is_unit_click and result.hit_unit else None,
            ))
        else:
            # Instant commands (smoke, defend, hide) - no target needed
            self._event_bus.publish(PlayerCommand(
                command=cmd_name,
                unit_ids=list(self._selected_ids),
            ))

    # ====== Ctrl-key LOS visualization ======

    def set_ctrl_held(self, held: bool) -> None:
        """Set whether Ctrl key is held down."""
        self._ctrl_held = held

    @property
    def ctrl_held(self) -> bool:
        return self._ctrl_held

    # ====== Overlay rendering ======

    def render_overlay(self, surface, camera) -> None:
        """Render interaction overlays (radial menu, LOS, cursor)."""
        if self._radial_menu.is_visible:
            self._radial_menu.render(surface)
        # Render custom cursor
        mouse_pos = pygame.mouse.get_pos()
        self.cursor_manager.render(surface, mouse_pos)
