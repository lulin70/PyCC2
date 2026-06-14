from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pygame

from pycc2.domain.entities.unit import UnitState

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.audio.sound_system import SoundSystem
    from pycc2.presentation.input.handler import PygameInputHandler
    from pycc2.presentation.input.interaction_controller import InteractionController
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.domain.interfaces.display_config import DisplayConfig
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
    from pycc2.presentation.rendering.window_config import WindowManager
    from pycc2.presentation.ui.deployment_ui import DeploymentUI
    from pycc2.presentation.ui.time_control import TimeControlUI
    from pycc2.services.ai_service import AIService
    from pycc2.services.deployment_manager import DeploymentManager
    from pycc2.services.event_bus import EventBus
    from pycc2.services.hud_manager import HUDManager
    from pycc2.services.pause_menu_controller import PauseMenuController

    from .event_dispatcher import EventDispatcher

logger = logging.getLogger(__name__)

LOGIC_DT: float = 1.0 / 30.0
TARGET_FPS: int = 60
MAX_FRAME_TIME: float = 0.25


@dataclass(slots=True)
class GameState:
    game_map: GameMap
    units: list[Unit]
    camera: Camera
    selected_unit_ids: set[str] = field(default_factory=set)
    tick: int = 0
    running: bool = True
    paused: bool = False
    debug_mode: bool = False
    side_turn: str = "allies"
    time_speed: float = 1.0
    current_weather: object | None = None  # WeatherType enum


@dataclass
class GameLoop:
    renderer: EnhancedRenderer
    window_manager: WindowManager
    event_bus: EventBus
    state: GameState
    input_handler: PygameInputHandler | None = None
    ai_service: AIService | None = None
    interaction_controller: InteractionController | None = None
    sound_system: SoundSystem | None = None
    use_full_hud: bool = True
    display_config: DisplayConfig | None = None
    settings_menu: object | None = None
    tutorial_overlay: object | None = None
    hint_manager: object | None = None

    _accumulator: float = 0.0
    _current_time: float = field(default_factory=time.perf_counter)
    _fps: float = 0.0
    _total_ticks: int = 0
    _hud_manager: HUDManager | None = field(init=False, default=None)
    _victory_manager: object | None = field(init=False, default=None)

    _combat_director: object | None = field(init=False, default=None)
    _render_pipeline: object | None = field(init=False, default=None)
    _input_router: object | None = field(init=False, default=None)
    _save_controller: object | None = field(init=False, default=None)
    _ai_update_interval: int = field(init=False, default=3)
    _ai_tick_counter: int = field(init=False, default=0)
    _pause_menu: object | None = field(init=False, default=None)
    _deployment_manager: DeploymentManager = field(init=False, default=None)
    _event_dispatcher: EventDispatcher = field(init=False, default=None)
    _campaign_ui: object | None = field(init=False, default=None)
    time_control: TimeControlUI | None = field(init=False, default=None)
    _popup_manager: object | None = field(init=False, default=None)
    _effect_stack: object | None = field(init=False, default=None)
    _combat_camera: object | None = field(init=False, default=None)
    _achievement_bridge: object | None = field(init=False, default=None)
    _projectile_trail_sys: object | None = field(init=False, default=None)
    _environmental_audio: object | None = field(init=False, default=None)
    _victory_delay: float = field(init=False, default=0.0)
    _weather_renderer: object | None = field(init=False, default=None)
    _weather_state: object | None = field(init=False, default=None)
    _day_night_time: float | None = field(init=False, default=None)
    _lighting_renderer: object | None = field(init=False, default=None)
    _weather_system: object | None = field(init=False, default=None)
    _weather_effects: object | None = field(init=False, default=None)
    _day_night_cycle: object | None = field(init=False, default=None)
    _dynamic_shadow_sys: object | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        from pycc2.services.game_loop_assembler import GameLoopAssembler

        GameLoopAssembler(self).assemble()

    # -- Backward-compatible properties delegating to DeploymentManager --

    @property
    def deployment_ui(self) -> DeploymentUI | None:
        return self._deployment_manager.deployment_ui if self._deployment_manager else None

    @property
    def deployment_phase_active(self) -> bool:
        return self._deployment_manager.is_active if self._deployment_manager else False

    def _get_time_speed(self) -> float:
        if self.time_control is not None:
            return self.time_control.speed_multiplier
        return 1.0

    def run(self) -> int:
        """Run the game loop. Returns 0 for normal exit, 1 for restart request."""
        while self.state.running:
            new_time = time.perf_counter()
            frame_time = min(new_time - self._current_time, MAX_FRAME_TIME)
            self._current_time = new_time

            if frame_time > MAX_FRAME_TIME * 4:
                logger.debug("Long pause detected (%.2fs), resetting time base", frame_time)
                continue

            if not self._event_dispatcher.process_events():
                break

            self._accumulator += frame_time
            catchup_count = 0
            max_catchup = 5

            # Update victory manager delay timer even when paused (for post-battle auto-transition)
            if self._victory_manager is not None:
                self._victory_manager.update()

            time_speed = self._get_time_speed()
            if time_speed <= 0.0:
                self.state.paused = True
            else:
                self.state.paused = False
                self.state.time_speed = time_speed
                effective_dt = LOGIC_DT * time_speed
                while self._accumulator >= LOGIC_DT and catchup_count < max_catchup:
                    self._update_logic(effective_dt)
                    self._accumulator -= LOGIC_DT
                    self.state.tick += 1
                    self._total_ticks += 1
                    catchup_count += 1

            alpha = self._accumulator / LOGIC_DT if LOGIC_DT > 0 else 0.0

            # Constrain camera to map bounds every frame
            tile_size = self.renderer.TILE_SIZE
            if not isinstance(tile_size, int):
                tile_size = 32
            map_w = self.state.game_map.width * tile_size
            map_h = self.state.game_map.height * tile_size
            self.state.camera.constrain_to_map(map_w, map_h)

            # Apply cinematic camera effects (shake, zoom, push-pull)
            camera_offset = (0.0, 0.0)
            if self._effect_stack is not None and not self._effect_stack.is_empty():
                camera_offset = self._effect_stack.get_total_offset()
                if camera_offset != (0.0, 0.0):
                    from pycc2.domain.value_objects.vec2 import Vec2
                    self.state.camera.position = Vec2(
                        self.state.camera.position.x + camera_offset[0],
                        self.state.camera.position.y + camera_offset[1],
                    )

            # Apply slow-motion time scale from EffectStack
            if self._effect_stack is not None and not self._effect_stack.is_empty():
                time_scale = self._effect_stack.get_time_scale()
                if time_scale < 1.0:
                    time_speed *= time_scale

            self._render_pipeline.update_fps(self._fps)

            if self.tutorial_overlay:
                self.tutorial_overlay.update()
            if self.hint_manager:
                self.hint_manager.update()

            screen = self.window_manager._screen

            # Campaign UI overlay — if visible, render it on top and skip normal rendering
            if self._campaign_ui is not None and self._campaign_ui.is_visible and screen:
                self._campaign_ui.render(screen)
                pygame.display.flip()
                self.window_manager.tick(TARGET_FPS)
                self._fps = self.window_manager.fps
                continue

            if self.tutorial_overlay and self.tutorial_overlay.visible and screen:
                self.tutorial_overlay.render(screen)

            if self.settings_menu and self.settings_menu.visible:
                if screen:
                    self.settings_menu.render(screen)
            elif self._deployment_manager.is_active and self._deployment_manager.deployment_ui is not None and screen:
                # === 部署阶段渲染 ===
                deployment_ui = self._deployment_manager.deployment_ui
                
                # Step 1: 渲染地图和单位
                self._render_pipeline.render(
                    game_map=self.state.game_map,
                    units=self.state.units,
                    camera=self.state.camera,
                    alpha=alpha,
                    selected_unit_ids=self.state.selected_unit_ids,
                    debug_mode=self.state.debug_mode,
                    paused=self.state.paused,
                    tick=self.state.tick,
                    show_post_battle=self._victory_manager.show_post_battle,
                    game_result=self._victory_manager.game_result,
                    battle_stats=self._victory_manager.battle_stats,
                )

                # Step 2: 渲染天气/光照效果
                if self._weather_renderer is not None:
                    if self._weather_state is not None:
                        self._weather_renderer.render(screen, self.state.camera, self._weather_state)
                if self._lighting_renderer is not None:
                    if self._day_night_time is not None:
                        self._lighting_renderer.render(screen, self._day_night_time)

                # Step 3: 渲染部署UI（包含单位列表、详情、命令栏）
                dc = self.display_config
                tile_size = dc.base_tile_size if dc else 16
                deployment_ui.render(
                    screen, font=None,
                    map_offset_x=0, map_offset_y=0,
                    tile_size=tile_size,
                )

            else:
                # === 战斗阶段渲染 ===

                # Step 1: 渲染地图和单位
                self._render_pipeline.render(
                    game_map=self.state.game_map,
                    units=self.state.units,
                    camera=self.state.camera,
                    alpha=alpha,
                    selected_unit_ids=self.state.selected_unit_ids,
                    debug_mode=self.state.debug_mode,
                    paused=self.state.paused,
                    tick=self.state.tick,
                    show_post_battle=self._victory_manager.show_post_battle,
                    game_result=self._victory_manager.game_result,
                    battle_stats=self._victory_manager.battle_stats,
                )

                # Step 2: 渲染天气/光照效果
                if self._weather_renderer is not None:
                    if self._weather_state is not None:
                        self._weather_renderer.render(screen, self.state.camera, self._weather_state)
                if self._lighting_renderer is not None:
                    if self._day_night_time is not None:
                        self._lighting_renderer.render(screen, self._day_night_time)

                # Step 3: 渲染CC2统一底部HUD面板（单位列表+详情+小地图+命令栏）
                if screen:
                    if self._hud_manager:
                        self._hud_manager.render(screen, self.state.camera, self.state)

            if self.hint_manager and screen:
                self.hint_manager.render(screen)

            # Render combat popups (CC2-style floating text)
            if self._popup_manager and screen:
                self._popup_manager.render(screen, self.state.camera)

            # Render interaction overlays (radial menu, LOS)
            if self.interaction_controller and screen:
                # CC2-style: Ctrl-key LOS visualization
                if self.interaction_controller.ctrl_held and self.state.selected_unit_ids:
                    selected_id = next(iter(self.state.selected_unit_ids), None)
                    if selected_id:
                        selected_unit = next((u for u in self.state.units if u.id == selected_id), None)
                        if selected_unit:
                            self.renderer.render_los_overlay(screen, selected_unit, self.state.game_map, self.state.camera)
                # Radial menu and other interaction overlays
                self.interaction_controller.render_overlay(screen, self.state.camera)

            # Draw pause menu overlay
            if self._pause_menu.is_active and screen:
                self._pause_menu.render(screen)

            # Restore camera position after cinematic effects
            if camera_offset != (0.0, 0.0):
                from pycc2.domain.value_objects.vec2 import Vec2
                self.state.camera.position = Vec2(
                    self.state.camera.position.x - camera_offset[0],
                    self.state.camera.position.y - camera_offset[1],
                )

            pygame.display.flip()
            self.window_manager.tick(TARGET_FPS)
            self._fps = self.window_manager.fps

        self.shutdown()
        return 0

    def _update_logic(self, dt: float) -> None:
        if self.state.paused:
            return

        self._update_weather(dt)
        self._update_audio_sync(dt)
        self._update_unit_movement(dt)
        self._update_fatigue(dt)
        self._update_combat(dt)
        self._update_popups()
        self._update_camera(dt)
        self._update_visual_effects(dt)
        self._update_hud(dt)
        self._update_ai(dt)
        self._update_victory()

    def _update_weather(self, dt: float) -> None:
        # Update weather system
        if self._weather_system is not None:
            self._weather_system.update(dt)

        # Apply weather effects to game state
        if self._weather_effects is not None:
            if self._weather_state is not None:
                # Weather modifiers are read by Unit.get_accuracy_modifier() etc.
                # Store current weather type for unit queries
                self.state.current_weather = self._weather_state.weather_type

        # Update day-night cycle
        if self._day_night_cycle is not None:
            self._day_night_cycle.advance(dt)

    def _update_audio_sync(self, dt: float) -> None:
        # Process audio event queue
        if self.sound_system:
            try:
                self.sound_system.process_event_queue()
            except AttributeError:
                pass  # SoundSystem may not have process_event_queue method

        # Update environmental ambient audio system
        if self._environmental_audio is not None:
            try:
                self._environmental_audio.update(dt)
            except Exception:
                pass

        # Sync environmental audio context with game state
        if self._environmental_audio is not None:
            try:
                # Sync time-of-day from day-night cycle
                if self._day_night_cycle is not None:
                    tod = getattr(self._day_night_cycle, 'time_of_day', None)
                    if tod is not None:
                        hour = int(tod * 24) % 24
                        self._environmental_audio.set_time_of_day(hour)
                elif self._day_night_time is not None:
                    hour = int(self._day_night_time * 24) % 24
                    self._environmental_audio.set_time_of_day(hour)

                # Sync weather (rain)
                if self._weather_state is not None:
                    weather_type = getattr(self._weather_state, 'weather_type', None)
                    if weather_type is not None:
                        is_raining = 'rain' in str(weather_type).lower()
                        self._environmental_audio.set_weather_rain(is_raining)

                # Estimate combat intensity from unit states
                attacking_count = sum(
                    1 for u in self.state.units
                    if u.is_alive and u.state_machine.current == UnitState.ATTACKING
                )
                total_alive = sum(1 for u in self.state.units if u.is_alive)
                intensity = min(1.0, attacking_count / max(1, total_alive * 0.15))
                self._environmental_audio.set_combat_intensity(intensity)
            except Exception:
                pass

    def _update_unit_movement(self, dt: float) -> None:
        # Update unit movements (smooth movement toward targets)
        for unit in self.state.units:
            # Update movement mode timers (Fast Move, Sneak, Defend)
            if hasattr(unit, 'update_movement_mode'):
                unit.update_movement_mode()

            if hasattr(unit, 'move_target') and unit.move_target is not None:
                arrived = unit.update_movement(dt)
                if arrived:
                    logger.debug(f"[MOVEMENT] {unit.display_name} arrived at destination")

    def _update_fatigue(self, dt: float) -> None:
        # Update unit fatigue, veterancy, and weather effects
        for unit in self.state.units:
            # Fatigue accumulation
            if unit.fatigue is not None:
                if unit.move_target is not None:
                    activity = "fast_move" if unit.is_fast_moving else "moving"
                    unit.fatigue.accumulate(activity)
                elif unit.state_machine.current == UnitState.ATTACKING:
                    unit.fatigue.accumulate("firing")
                else:
                    unit.fatigue.recover()

            # Veterancy: record shots (integration point for combat)
            # (actual XP from kills is handled in combat_director)

        # Update attack line tracking (unit targets follow movement)
        if self.interaction_controller:
            self.interaction_controller.attack_line.update_tracking(self.state.units)

    def _update_combat(self, dt: float) -> None:
        self._combat_director.update(
            units=self.state.units,
            game_map=self.state.game_map,
            dt=dt,
            battle_stats=self._victory_manager.battle_stats,
        )
        self._combat_director.process_effects(renderer=self.renderer, camera=self.state.camera)

        # Process queued commands for units that completed their current command
        # (movement arrival is handled in Unit.update_movement(); this handles
        # attack/reload completion and other IDLE transitions with queued commands)
        for unit in self.state.units:
            if not unit.is_alive:
                continue
            if unit.state_machine.current == UnitState.IDLE and unit.has_queued_commands:
                next_cmd = unit.get_next_queued_command()
                if next_cmd is not None:
                    unit._execute_queued_command(next_cmd)

    def _update_popups(self) -> None:
        # Trigger combat popups for significant events
        self._process_combat_popups()

    def _update_camera(self, dt: float) -> None:
        # 更新相机屏幕震动
        self.state.camera.update_shake(dt)

    def _update_visual_effects(self, dt: float) -> None:
        # P2-03: Update screen flash overlay alpha (fade-out)
        if hasattr(self.renderer, 'update_flash'):
            self.renderer.update_flash(dt)

        # P3-01: Update weather atmosphere animation
        if hasattr(self.renderer, 'update_weather'):
            self.renderer.update_weather(dt)

        # P3-02: Update shell casing physics
        if hasattr(self.renderer, 'update_shell_casings'):
            self.renderer.update_shell_casings(dt)

        # Suppression overlay: update red edge flash for pinned/broken player units
        if hasattr(self.renderer, 'update_suppression_overlay'):
            self.renderer.update_suppression_overlay(dt, self.state.units)

        # P2-04: Smooth unit position interpolation (lerp toward real positions)
        if hasattr(self.renderer, '_smooth_positions'):
            self.renderer._smooth_positions(self.state.units, dt)

        # Update cinematic camera effect stack
        if self._effect_stack is not None:
            self._effect_stack.update(dt)

        # Update projectile trail system
        if self._projectile_trail_sys is not None:
            self._projectile_trail_sys.update(dt)

        # Update dynamic shadow time-of-day
        if self._dynamic_shadow_sys is not None:
            if self._day_night_time is not None:
                self._dynamic_shadow_sys.set_time_of_day(self._day_night_time)
            elif self._day_night_cycle is not None:
                tod = getattr(self._day_night_cycle, 'time_of_day', 0.5)
                self._dynamic_shadow_sys.set_time_of_day(tod)

    def _update_hud(self, dt: float) -> None:
        # P2-05: Update UI fade transitions (HUDManager panel/minimap fades)
        if self._hud_manager is not None:
            if hasattr(self._hud_manager, 'update'):
                self._hud_manager.update(dt)

    def _update_ai(self, dt: float) -> None:
        if self.ai_service is not None and self.ai_service.managed_unit_count > 0:
            self._ai_tick_counter += 1
            if self._ai_tick_counter >= self._ai_update_interval:
                intents = self.ai_service.tick(
                    dt,
                    game_map=self.state.game_map,
                    all_units=self.state.units,
                )
                if intents:
                    self.ai_service.execute_intents(intents)
                self._ai_tick_counter = 0

    def _update_victory(self) -> None:
        victory_outcome = self._victory_manager.evaluate(self.state.units, self.state.tick)
        if victory_outcome is not None:
            result, reason = victory_outcome
            self.state.paused = True

            # Publish BattleWon named event for camera effects and achievement tracking
            self.event_bus.publish_named("BattleWon", {
                "result": result.name,
                "reason": reason,
                "duration_seconds": self.state.tick * LOGIC_DT,
            })

            if self.sound_system:
                from pycc2.domain.value_objects.audio_enums import SoundType

                if result.name == "ALLIES_VICTORY":
                    self.sound_system.play(SoundType.UI_COMMAND)
                else:
                    self.sound_system.play(SoundType.UI_CANCEL)

    def _handle_player_command(self, data: dict) -> None:
        self._combat_director.handle_player_command(data, self.state.units, self.state.game_map)

    def _execute_attack(self, attacker, target) -> None:
        self._combat_director.execute_attack(attacker, target)

    def _on_unit_attacked(self, data: dict) -> None:
        self._combat_director.on_unit_attacked(data)
        # Trigger "Taking fire!" popup on the target unit
        target_id = data.get("target_id")
        if target_id and self._popup_manager:
            target = next((u for u in self.state.units if u.id == target_id), None)
            if target and hasattr(target, 'position') and target.position is not None:
                pp = target.position.pixel_position
                self._popup_manager.add_taking_fire(pp.x, pp.y)

    def _on_unit_attacked_for_stats(self, data: dict) -> None:
        self._combat_director.record_stats(data, self.state.units, self._victory_manager.battle_stats)

    def _on_projectile_fired(self, data: dict) -> None:
        """Handle ProjectileFired event — add trail to ProjectileTrailSystem."""
        if self._projectile_trail_sys is None:
            return
        weapon_type = data.get("weapon_type", "bullet")
        sx = data.get("start_x", 0.0)
        sy = data.get("start_y", 0.0)
        ex = data.get("end_x", 0.0)
        ey = data.get("end_y", 0.0)

        if weapon_type == "shell":
            self._projectile_trail_sys.add_shell_trail(sx, sy, ex, ey)
        elif weapon_type == "rocket":
            self._projectile_trail_sys.add_rocket_trail(sx, sy, ex, ey)
        elif weapon_type == "mortar":
            self._projectile_trail_sys.add_mortar_trail(sx, sy, ex, ey)
        else:
            self._projectile_trail_sys.add_bullet_trail(sx, sy, ex, ey)

    def _process_combat_popups(self) -> None:
        """Scan units for combat events and trigger floating popups."""
        from pycc2.domain.systems.morale_system import MoraleSystem, MoraleState

        for unit in self.state.units:
            if not unit.is_alive:
                continue
            # Get pixel position for popup placement
            px, py = 0.0, 0.0
            if hasattr(unit, 'position') and unit.position is not None:
                pp = unit.position.pixel_position
                px, py = pp.x, pp.y

            # Check morale state changes → popup
            if hasattr(unit, 'morale') and unit.morale is not None:
                morale_state = MoraleSystem.get_state(unit.morale.value)
                # Track previous state to detect transitions
                prev_state = getattr(unit, '_prev_morale_state', None)
                if prev_state is not None and prev_state != morale_state:
                    if morale_state == MoraleState.BROKEN:
                        self._popup_manager.add_breaking(px, py)
                    elif morale_state == MoraleState.PINNED:
                        self._popup_manager.add_pinned(px, py)
                unit._prev_morale_state = morale_state

            # Check for out-of-ammo
            if hasattr(unit, 'weapon') and unit.weapon is not None:
                weapon_state = getattr(unit.weapon, 'state', None)
                if weapon_state is not None and hasattr(weapon_state, 'name'):
                    if weapon_state.name == 'EMPTY' and not getattr(unit, '_ammo_popup_shown', False):
                        self._popup_manager.add_out_of_ammo(px, py)
                        unit._ammo_popup_shown = True
                    elif weapon_state.name != 'EMPTY':
                        unit._ammo_popup_shown = False

        # Check for KIA (newly dead units)
        for unit in self.state.units:
            if not unit.is_alive and not getattr(unit, '_kia_popup_shown', False):
                px, py = 0.0, 0.0
                if hasattr(unit, 'position') and unit.position is not None:
                    pp = unit.position.pixel_position
                    px, py = pp.x, pp.y
                self._popup_manager.add_kia(px, py)
                unit._kia_popup_shown = True

    def _handle_input(self, event) -> None:
        if self._input_router and self._input_router.input_handler != self.input_handler:
            self._input_router.input_handler = self.input_handler
        self._input_router.route_input(event)

    def start_deployment(
        self,
        map_data: dict,
        faction: str = "ally",
        game_settings: object | None = None,
    ) -> None:
        """Create a DeploymentUI and activate the deployment phase.

        Delegates to DeploymentManager.start().
        """
        from pycc2.presentation.ui.deployment_ui import DeploymentUI as DUI

        dc = self.display_config
        width = dc.window_width if dc else 800
        height = dc.window_height if dc else 600
        deployment_ui = DUI(width=width, height=height)
        self._deployment_manager.start(
            map_data=map_data,
            faction=faction,
            game_settings=game_settings,
            display_config=self.display_config,
            deployment_ui=deployment_ui,
        )

    def complete_deployment(self) -> dict | None:
        """Finalize deployment and deactivate the deployment phase.

        Delegates to DeploymentManager.complete().
        """
        return self._deployment_manager.complete(
            ai_service=self.ai_service,
            state=self.state,
        )

    def get_deployment_state(self) -> object | None:
        """Return the current deployment state, or None if not in deployment."""
        return self._deployment_manager.get_state()

    def set_campaign_ui(self, campaign_ui: object) -> None:
        """Set the CampaignUI instance for campaign flow integration.

        When a campaign UI is active, the game loop renders it and
        delegates input to it.  The campaign UI drives state transitions
        (operation select -> briefing -> battle select -> preview ->
        deploy -> battle -> report).
        """
        self._campaign_ui = campaign_ui
        # Propagate reference to event dispatcher so it can route input
        if self._event_dispatcher is not None:
            self._event_dispatcher._campaign_ui_ref = campaign_ui

    @property
    def campaign_ui(self) -> object | None:
        """Return the current CampaignUI, if any."""
        return self._campaign_ui

    @property
    def victory_manager(self):
        """Public access to victory manager for save/export operations."""
        return self._victory_manager

    def shutdown(self) -> None:
        self.state.running = False
        if self._achievement_bridge is not None:
            self._achievement_bridge._manager.save()
        if self._environmental_audio is not None:
            try:
                self._environmental_audio.stop_all()
            except Exception:
                pass
        if self.sound_system is not None:
            self.sound_system.shutdown()
        if self.ai_service is not None:
            self.ai_service.shutdown()
        self.window_manager.shutdown()

    def quick_save(self, slot: int = 0) -> bool:
        return self._save_controller.quick_save(slot, self)

    def quick_load(self, slot: int = 0) -> bool:
        result = self._save_controller.quick_load(slot, self)
        if result:
            self._victory_manager.reset()
        return result

    def list_saves(self) -> list:
        return self._save_controller.list_saves()
