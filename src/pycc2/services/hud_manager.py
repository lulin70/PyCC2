"""HUD Manager — orchestrates the HUD system for the game loop.

Extracted from GameLoop to isolate HUD concerns: CC2 bottom panel,
minimap, command callbacks, and interaction callbacks.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame

    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.audio.sound_system import SoundSystem
    from pycc2.presentation.input.interaction_controller import InteractionController
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel
    from pycc2.domain.interfaces.display_config import DisplayConfig
    from pycc2.presentation.rendering.minimap import Minimap
    from pycc2.presentation.rendering.render_pipeline import RenderPipeline
    from pycc2.presentation.rendering.window_config import WindowManager
    from pycc2.services.event_bus import EventBus

    from .game_loop import GameState

logger = logging.getLogger(__name__)


@dataclass
class HUDManager:
    """Manages the HUD lifecycle: CC2 bottom panel, minimap, and callbacks.

    Public API
    ----------
    initialize(state, display_config, sound_system, interaction_controller,
               event_bus, renderer, window_manager, render_pipeline, input_router)
        Create and wire up the CC2 panel, minimap, and all callbacks.
    render(screen, camera, game_state)
        Render the CC2 bottom panel and UI overlays.
    render_fallback(screen, camera, game_state)
        Fallback renderer when the CC2 panel fails.
    center_camera_on_unit(units, unit_id, camera)
        Center camera (and minimap view) on a selected unit.
    """

    _cc2_panel: CC2BottomPanel | None = field(init=False, default=None)
    _minimap: Minimap | None = field(init=False, default=None)

    # Injected references (set in initialize)
    _state: GameState | None = field(init=False, default=None)
    _sound_system: SoundSystem | None = field(init=False, default=None)
    _interaction_controller: InteractionController | None = field(init=False, default=None)
    _event_bus: EventBus | None = field(init=False, default=None)

    def initialize(
        self,
        state: GameState,
        display_config: DisplayConfig,
        sound_system: SoundSystem | None,
        interaction_controller: InteractionController | None,
        event_bus: EventBus,
        renderer: object,
        window_manager: WindowManager,
        render_pipeline: RenderPipeline,
        input_router: object,
    ) -> None:
        from pycc2.presentation.rendering.minimap import Minimap

        from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel

        dc = display_config

        # Store references
        self._state = state
        self._sound_system = sound_system
        self._interaction_controller = interaction_controller
        self._event_bus = event_bus

        # === CC2统一UI系统（唯一UI） ===
        # 旧的分散式UI已弃用，不再创建
        self._minimap = Minimap(display_config=dc, size=int(140 * dc.ui_scale))

        # CC2-style bottom panel (唯一的HUD渲染器)
        self._cc2_panel = CC2BottomPanel()
        self._cc2_panel.initialize()  # 初始化字体

        state.camera.viewport_width = dc.window_width
        state.camera.viewport_height = dc.window_height

        optimal_zoom = dc.compute_default_zoom(
            state.game_map.width, state.game_map.height
        )
        state.camera.zoom = optimal_zoom

        if hasattr(renderer, "_display_config"):
            renderer._display_config = dc
            renderer.TILE_SIZE = dc.base_tile_size
            renderer.SPRITE_SIZE = dc.effective_sprite_size

        screen = window_manager.get_screen()
        if screen is not None:
            if self._cc2_panel:
                self._cc2_panel.initialize()

        # Render pipeline不再使用旧的分散式UI
        render_pipeline.hud_manager = None
        render_pipeline.command_bar = None
        render_pipeline.unit_panel = None
        render_pipeline.minimap = None  # Minimap由CC2面板内部管理

        # Input router使用CC2面板的命令系统（如果支持）
        input_router.command_bar = None  # 旧command_bar已禁用

        self._bind_command_callbacks()
        self._bind_interaction_callbacks()

        self._minimap.set_map(state.game_map)

    # ------------------------------------------------------------------
    # Command callbacks (CC2 7-command system + roster + zoom)
    # ------------------------------------------------------------------

    def _bind_command_callbacks(self) -> None:
        from pycc2.presentation.audio.sound_system import SoundType
        from pycc2.services.event_protocol import PlayerCommand

        if not self._cc2_panel:
            return

        state = self._state
        sound_system = self._sound_system
        interaction_controller = self._interaction_controller
        event_bus = self._event_bus

        def on_move():
            if sound_system:
                sound_system.play_ui_command()
            if interaction_controller:
                from pycc2.presentation.input.interaction_controller import InteractionMode

                interaction_controller.set_mode(InteractionMode.MOVE)

        def on_attack():
            if sound_system:
                sound_system.play_ui_command()
            if interaction_controller:
                from pycc2.presentation.input.interaction_controller import InteractionMode

                interaction_controller.set_mode(InteractionMode.ATTACK)

                # Begin attack line from selected unit(s)
                if state.selected_unit_ids:
                    selected_id = next(iter(state.selected_unit_ids), None)
                    selected_unit = next((u for u in state.units if u.id == selected_id), None)
                    if selected_unit:
                        source_pos = selected_unit.position.pixel_position
                        interaction_controller.attack_line.begin_attack(
                            unit_id=selected_id,
                            source_pos=source_pos,
                        )
                        logger.info(f"[ATTACK LINE] Started from {selected_unit.display_name} at ({source_pos.x:.0f},{source_pos.y:.0f})")

        def on_hold():
            if sound_system:
                sound_system.play_ui_command()
            event_bus.publish(
                PlayerCommand(
                    command="defend",
                    unit_ids=list(state.selected_unit_ids),
                )
            )

        def on_dig_in():
            if sound_system:
                sound_system.play_ui_command()
            event_bus.publish(
                PlayerCommand(
                    command="take_cover",
                    unit_ids=list(state.selected_unit_ids),
                )
            )

        def on_cancel():
            if sound_system:
                sound_system.play(SoundType.UI_CANCEL)
            state.selected_unit_ids.clear()
            if interaction_controller:
                interaction_controller.clear_selection()

        def on_fast():
            if sound_system:
                sound_system.play_ui_command()
            if interaction_controller:
                from pycc2.presentation.input.interaction_controller import InteractionMode
                interaction_controller.set_mode(InteractionMode.MOVE, fast=True)
                logger.info("[COMMAND] Fast Move activated")

        def on_sneak():
            if sound_system:
                sound_system.play_ui_command()
            if interaction_controller:
                from pycc2.presentation.input.interaction_controller import InteractionMode
                interaction_controller.set_mode(InteractionMode.MOVE, sneak=True)
                logger.info("[COMMAND] Sneak Move activated")

        def on_smoke():
            if sound_system:
                sound_system.play_ui_command()
            # Deploy smoke: use "take_cover" command with smoke flag
            event_bus.publish(
                PlayerCommand(
                    command="deploy_smoke",
                    unit_ids=list(state.selected_unit_ids),
                )
            )
            logger.info(f"[COMMAND] Smoke deployed by {state.selected_unit_ids}")

        def on_defend():
            if sound_system:
                sound_system.play_ui_command()
            # Defend command: find cover or dig in
            event_bus.publish(
                PlayerCommand(
                    command="take_cover",  # Use "take_cover" which CombatDirector handles
                    unit_ids=list(state.selected_unit_ids),
                )
            )
            logger.info(f"[COMMAND] Defend issued to {state.selected_unit_ids}")

        # Unit selection from roster
        def on_roster_select(unit_id: str):
            if unit_id:
                state.selected_unit_ids = {unit_id}
                logger.info(f"[CC2 PANEL] Selected unit: {unit_id}")
                # Center camera on selected unit
                self.center_camera_on_unit(state.units, unit_id, state.camera)

        self._cc2_panel._on_unit_select = on_roster_select

        # Command callbacks (CC2 complete 7-command system)
        self._cc2_panel.register_callback("move", on_move)
        self._cc2_panel.register_callback("fast", on_fast)
        self._cc2_panel.register_callback("sneak", on_sneak)
        self._cc2_panel.register_callback("attack", on_attack)
        self._cc2_panel.register_callback("smoke", on_smoke)
        self._cc2_panel.register_callback("defend", on_defend)
        self._cc2_panel.register_callback("cancel", on_cancel)

        # Zoom callback
        def on_zoom_change(zoom_level: float):
            state.camera.zoom = zoom_level
            logger.info(f"[CC2 PANEL] Zoom changed to {zoom_level:.2f}x")

        self._cc2_panel._on_zoom_change = on_zoom_change

    # ------------------------------------------------------------------
    # Interaction callbacks (move / attack execution)
    # ------------------------------------------------------------------

    def _bind_interaction_callbacks(self) -> None:
        from pycc2.services.event_protocol import PlayerCommand

        if not self._interaction_controller:
            return

        state = self._state
        event_bus = self._event_bus
        interaction_controller = self._interaction_controller

        def execute_move(unit_ids: set[str], target):
            from pycc2.domain.value_objects.tile_coord import TileCoord

            logger.info(f"[COMMAND] Move {len(unit_ids)} unit(s) to ({target.x:.0f}, {target.y:.0f})")

            # Set move targets (units will move each tick via update_movement)
            for unit in state.units:
                if unit.id in unit_ids and unit.is_alive:
                    tile_x = int(target.x // 32)
                    tile_y = int(target.y // 32)
                    tile = TileCoord(tile_x, tile_y)

                    old_tile = unit.position.tile_coord
                    unit.set_move_target(tile)  # Set target, don't teleport!

                    logger.info(
                        f"[MOVE TARGET] {unit.display_name}: "
                        f"({old_tile.x},{old_tile.y}) -> ({tile_x},{tile_y})"
                    )

            event_bus.publish(PlayerCommand(
                command="move",
                unit_ids=list(unit_ids),
                target=(target.x, target.y),
            ))

        def execute_attack(unit_ids: set[str], target_id: str):
            logger.info(f"[COMMAND] Attacking target {target_id} with {len(unit_ids)} unit(s)")
            event_bus.publish(PlayerCommand(
                command="attack",
                unit_ids=list(unit_ids),
                target_id=target_id,
            ))

        interaction_controller.register_on_move(execute_move)
        interaction_controller.register_on_attack(execute_attack)

    # ------------------------------------------------------------------
    # Camera
    # ------------------------------------------------------------------

    def center_camera_on_unit(self, units: list[Unit], unit_id: str, camera: Camera) -> None:
        """Center camera (and minimap view) on selected unit."""
        unit = next((u for u in units if u.id == unit_id), None)
        if unit and hasattr(unit, 'position') and unit.position is not None:
            # Center camera on unit's position
            pos = unit.position.pixel_position
            from pycc2.domain.value_objects.vec2 import Vec2
            viewport_w = camera.viewport_width
            viewport_h = camera.viewport_height

            # Set camera position to center on unit
            camera.position = Vec2(
                pos.x - viewport_w / 2,
                pos.y - viewport_h / 2,
            )

            logger.debug(f"[CAMERA] Centered on {unit.display_name} at ({pos.x:.0f}, {pos.y:.0f})")

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, screen: pygame.Surface, camera: Camera, game_state: GameState) -> None:
        """渲染CC2风格底部HUD面板和UI覆盖层"""
        try:
            # CC2统一底部面板（包含单位列表、详情、小地图、命令栏）
            if self._cc2_panel:
                # 同步选择状态：game_state → cc2_panel
                selected_id = None
                if game_state.selected_unit_ids:
                    selected_id = next(iter(game_state.selected_unit_ids), None)
                self._cc2_panel.set_selected_unit(selected_id)

                # 同步选择状态：game_state → interaction_controller
                if self._interaction_controller and hasattr(self._interaction_controller, '_selected_ids'):
                    self._interaction_controller._selected_ids = set(game_state.selected_unit_ids)

                # 显示友军单位（ALLIES + POLISH 都是盟军）
                try:
                    from pycc2.domain.entities.unit import Faction as UnitFaction
                    allied_factions = (UnitFaction.ALLIES, UnitFaction.POLISH) if hasattr(UnitFaction, 'POLISH') else (UnitFaction.ALLIES,)
                    friendly_units = [u for u in game_state.units if u.faction in allied_factions]
                    self._cc2_panel.set_friendly_units(friendly_units)
                except Exception as e:
                    logger.warning(f"Failed to set friendly units: {e}")

                # 渲染CC2统一底部面板
                self._cc2_panel.render(
                    surface=screen,
                    camera=camera,
                    game_map=game_state.game_map,
                    minimap=self._minimap,
                )

        except Exception as e:
            logger.error(f"HUDManager.render() crashed: {e}")
            import traceback
            traceback.print_exc()

    def render_fallback(self, screen: pygame.Surface, camera: Camera, game_state: GameState) -> None:
        """Fallback HUD renderer - CC2面板失败时的最后手段"""
        # 旧UI已完全禁用，此方法仅记录错误
        logger.error("CC2面板渲染失败且无可用Fallback！")
        # 不再渲染任何UI，避免混乱

    # ------------------------------------------------------------------
    # Minimap delegation (for click handling in game loop)
    # ------------------------------------------------------------------

    @property
    def minimap(self) -> Minimap | None:
        return self._minimap
