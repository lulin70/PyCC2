from __future__ import annotations

import contextlib
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pygame

from pycc2.domain.entities.unit import UnitState
from pycc2.domain.interfaces import (
    IAchievementBridge,
    ICombatCamera,
    ICombatDirector,
    IDayNightCycle,
    IDeploymentManager,
    IDynamicShadowSystem,
    IEffectStack,
    IEnvironmentalAudio,
    IHUDManager,
    IInputRouter,
    IPauseMenu,
    IPopupManager,
    IProjectileTrailSystem,
    IRenderPipeline,
    ISaveController,
    IVictoryManager,
    IWeatherSystem,
)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces.camera_protocol import ICamera as Camera
    from pycc2.domain.interfaces.campaign_ui_protocol import ICampaignUI
    from pycc2.domain.interfaces.display_config import DisplayConfig
    from pycc2.domain.interfaces.input_handler_protocol import IInputHandler as PygameInputHandler
    from pycc2.domain.interfaces.interaction_controller_protocol import (
        IInteractionController as InteractionController,
    )
    from pycc2.domain.interfaces.renderer_protocol import IRenderer as EnhancedRenderer
    from pycc2.domain.interfaces.window_manager_protocol import IWindowManager as WindowManager
    from pycc2.presentation.audio.sound_system import SoundSystem
    from pycc2.presentation.ui.deployment_ui import DeploymentUI
    from pycc2.presentation.ui.time_control import TimeControlUI
    from pycc2.services.ai_service import AIService
    from pycc2.services.event_bus import EventBus

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
    _hud_manager: IHUDManager | None = field(init=False, default=None)
    _victory_manager: IVictoryManager | None = field(init=False, default=None)

    _combat_director: ICombatDirector | None = field(init=False, default=None)
    _render_pipeline: IRenderPipeline | None = field(init=False, default=None)
    _input_router: IInputRouter | None = field(init=False, default=None)
    _save_controller: ISaveController | None = field(init=False, default=None)
    _ai_update_interval: int = field(init=False, default=3)
    _ai_tick_counter: int = field(init=False, default=0)
    _pause_menu: IPauseMenu | None = field(init=False, default=None)
    _deployment_manager: IDeploymentManager = field(init=False, default=None)
    _deployment_ui_factory: object | None = None  # Callable[[int, int], IDeploymentUI]
    _event_dispatcher: EventDispatcher = field(init=False, default=None)
    _campaign_ui: ICampaignUI | None = field(init=False, default=None)
    time_control: TimeControlUI | None = field(init=False, default=None)
    _popup_manager: IPopupManager | None = field(init=False, default=None)
    _effect_stack: IEffectStack | None = field(init=False, default=None)
    _combat_camera: ICombatCamera | None = field(init=False, default=None)
    _achievement_bridge: IAchievementBridge | None = field(init=False, default=None)
    _projectile_trail_sys: IProjectileTrailSystem | None = field(init=False, default=None)
    _environmental_audio: IEnvironmentalAudio | None = field(init=False, default=None)
    _victory_delay: float = field(init=False, default=0.0)
    _weather_renderer: object | None = field(init=False, default=None)
    _weather_state: object | None = field(init=False, default=None)
    _day_night_time: float | None = field(init=False, default=None)
    _lighting_renderer: object | None = field(init=False, default=None)
    _weather_system: IWeatherSystem | None = field(init=False, default=None)
    _weather_effects: object | None = field(init=False, default=None)
    _day_night_cycle: IDayNightCycle | None = field(init=False, default=None)
    _dynamic_shadow_sys: IDynamicShadowSystem | None = field(init=False, default=None)

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
            camera_offset = self._apply_camera_effects(time_speed)

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
            elif screen:
                # Common render pipeline for both deployment and battle phases
                self._render_scene(screen, alpha)

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
                        selected_unit = next(
                            (u for u in self.state.units if u.id == selected_id), None
                        )
                        if selected_unit:
                            self.renderer.render_los_overlay(
                                screen, selected_unit, self.state.game_map, self.state.camera
                            )
                # Radial menu and other interaction overlays
                self.interaction_controller.render_overlay(screen, self.state.camera)

            # Draw pause menu overlay
            if self._pause_menu and self._pause_menu.is_active and screen:
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

    def _apply_camera_effects(self, time_speed: float) -> tuple[float, float]:
        """Apply cinematic camera effects and return the offset for later restoration."""
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
            time_scale = self._effect_stack.get_time_scale()
            if time_scale < 1.0:
                time_speed *= time_scale

        return camera_offset

    def _render_scene(self, screen, alpha: float) -> None:
        """Render the game scene — shared by both deployment and battle phases.

        This method eliminates the code duplication between deployment and battle
        rendering by extracting the common render pipeline + weather/lighting steps,
        then branching only for the phase-specific UI overlay.
        """
        # Step 1: Render map and units (common to both phases)
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

        # Step 2: Render weather/lighting effects (common to both phases)
        if self._weather_renderer is not None and self._weather_state is not None:
            self._weather_renderer.render(screen, self.state.camera, self._weather_state)
        if self._lighting_renderer is not None and self._day_night_time is not None:
            self._lighting_renderer.render(screen, self._day_night_time)

        # Step 3: Phase-specific UI overlay
        if (
            self._deployment_manager.is_active
            and self._deployment_manager.deployment_ui is not None
        ):
            # Deployment phase: render deployment UI
            deployment_ui = self._deployment_manager.deployment_ui
            dc = self.display_config
            tile_size = dc.base_tile_size if dc else 16
            deployment_ui.render(
                screen,
                font=None,
                map_offset_x=0,
                map_offset_y=0,
                tile_size=tile_size,
            )
        else:
            # Battle phase: render CC2 unified bottom HUD panel
            if self._hud_manager:
                self._hud_manager.render(screen, self.state.camera, self.state)
            elif self.use_full_hud:
                # HUD expected but missing — log warning for debugging
                logger.warning(
                    "[HUD] Battle phase active but _hud_manager is None. "
                    "Check GameLoopAssembler._init_hud() completed successfully."
                )

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
        if self._weather_effects is not None and self._weather_state is not None:
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
            with contextlib.suppress(Exception):
                self._environmental_audio.update(dt)

        # Sync environmental audio context with game state
        if self._environmental_audio is not None:
            try:
                # Sync time-of-day from day-night cycle
                if self._day_night_cycle is not None:
                    tod = self._day_night_cycle.time_of_day
                    if tod is not None:
                        hour = int(tod * 24) % 24
                        self._environmental_audio.set_time_of_day(hour)
                elif self._day_night_time is not None:
                    hour = int(self._day_night_time * 24) % 24
                    self._environmental_audio.set_time_of_day(hour)

                # Sync weather (rain)
                if self._weather_state is not None:
                    weather_type = self._weather_state.weather_type
                    if weather_type is not None:
                        is_raining = "rain" in str(weather_type).lower()
                        self._environmental_audio.set_weather_rain(is_raining)

                # Estimate combat intensity from unit states (single pass)
                attacking_count = 0
                total_alive = 0
                for u in self.state.units:
                    if u.is_alive:
                        total_alive += 1
                        if u.state_machine.current == UnitState.ATTACKING:
                            attacking_count += 1
                intensity = min(1.0, attacking_count / max(1, total_alive * 0.15))
                self._environmental_audio.set_combat_intensity(intensity)
            except (AttributeError, ValueError, TypeError):
                pass

    def _update_unit_movement(self, dt: float) -> None:
        # Update unit movements (smooth movement toward targets)
        for unit in self.state.units:
            # Update movement mode timers (Fast Move, Sneak, Defend)
            unit.update_movement_mode()

            if unit.move_target is not None:
                arrived = unit.update_movement(dt)
                if arrived:
                    logger.debug("[MOVEMENT] %s arrived at destination", unit.display_name)

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
        # Update camera screen shake
        self.state.camera.update_shake(dt)

    def _update_visual_effects(self, dt: float) -> None:
        # P2-03: Update screen flash overlay alpha (fade-out)
        self.renderer.update_flash(dt)
        self.renderer.update_weather(dt)
        self.renderer.update_shell_casings(dt)
        self.renderer.update_suppression_overlay(dt, self.state.units)
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
                tod = self._day_night_cycle.time_of_day
                self._dynamic_shadow_sys.set_time_of_day(tod)

    def _update_hud(self, dt: float) -> None:
        # P2-05: Update UI fade transitions (HUDManager panel/minimap fades)
        if self._hud_manager is not None:
            self._hud_manager.update(dt)

    def _ensure_ai_units_registered(self) -> None:
        """Safety net: auto-register non-player units that lack AI behavior trees.

        This handles cases where units are added directly to state.units
        without going through the deployment flow (e.g., test scripts,
        debug commands, or scenario editors).
        """
        if self.ai_service is None:
            return

        # Determine player faction from existing registrations or default
        player_faction = getattr(self.state, "player_faction", None)
        if player_faction is None:
            # Heuristic: if any ALLIES unit exists, player is ALLIES
            from pycc2.domain.entities.unit import Faction

            has_allies = any(u.faction == Faction.ALLIES for u in self.state.units)
            player_faction = Faction.ALLIES if has_allies else Faction.AXIS

        # Find unregistered enemy units
        registered_ids = set(self.ai_service._unit_entities.keys())
        unregistered_enemies = [
            u
            for u in self.state.units
            if u.id not in registered_ids
            and u.faction != player_faction
            and u.is_alive
        ]

        if not unregistered_enemies:
            return

        try:
            from pycc2.domain.ai.unit_bt_factory import UnitBTFactory
            from pycc2.domain.entities.unit import UnitType

            for unit in unregistered_enemies:
                # Select appropriate behavior tree by unit type
                if unit.unit_type == UnitType.MACHINE_GUN_SQUAD:
                    bt = UnitBTFactory.create_mg_squad_bt(unit_id=unit.id)
                elif unit.unit_type == UnitType.COMMANDER:
                    bt = UnitBTFactory.create_commander_bt(unit_id=unit.id)
                else:
                    bt = UnitBTFactory.create_infantry_bt(unit_id=unit.id)

                self.ai_service.register_ai_unit(unit, bt)
                logger.info(
                    "Auto-registered AI unit: %s [%s] (%s)",
                    unit.name,
                    unit.id,
                    unit.unit_type.name,
                )
        except ImportError as e:
            logger.warning("Could not auto-register AI units: %s", e)

    def _update_ai(self, dt: float) -> None:
        # Safety net: ensure enemy units are registered before ticking
        self._ensure_ai_units_registered()

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
            self.event_bus.publish_named(
                "BattleWon",
                {
                    "result": result.name,
                    "reason": reason,
                    "duration_seconds": self.state.tick * LOGIC_DT,
                },
            )

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
            if target and target.position is not None:
                pp = target.position.pixel_position
                self._popup_manager.add_taking_fire(pp.x, pp.y)

    def _on_unit_attacked_for_stats(self, data: dict) -> None:
        self._combat_director.record_stats(
            data, self.state.units, self._victory_manager.battle_stats
        )

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
        from pycc2.domain.systems.morale_system import MoraleState, MoraleSystem

        for unit in self.state.units:
            if not unit.is_alive:
                continue
            # Get pixel position for popup placement
            px, py = 0.0, 0.0
            if unit.position is not None:
                pp = unit.position.pixel_position
                px, py = pp.x, pp.y

            # Check morale state changes → popup
            if unit.morale is not None:
                morale_state = MoraleSystem.get_state(unit.morale.value)
                # Track previous state to detect transitions
                prev_state = getattr(unit, "_prev_morale_state", None)
                if prev_state is not None and prev_state != morale_state:
                    if morale_state == MoraleState.BROKEN:
                        self._popup_manager.add_breaking(px, py)
                    elif morale_state == MoraleState.PINNED:
                        self._popup_manager.add_pinned(px, py)
                unit._prev_morale_state = morale_state

            # Check for out-of-ammo
            if unit.weapon is not None:
                weapon_state = unit.weapon.state
                if weapon_state is not None:
                    if weapon_state.name == "EMPTY" and not getattr(
                        unit, "_ammo_popup_shown", False
                    ):
                        self._popup_manager.add_out_of_ammo(px, py)
                        unit._ammo_popup_shown = True
                    elif weapon_state.name != "EMPTY":
                        unit._ammo_popup_shown = False

        # Check for KIA (newly dead units)
        for unit in self.state.units:
            if not unit.is_alive and not getattr(unit, "_kia_popup_shown", False):
                px, py = 0.0, 0.0
                if unit.position is not None:
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
        dc = self.display_config
        width = dc.window_width if dc else 800
        height = dc.window_height if dc else 600

        if self._deployment_ui_factory is not None:
            deployment_ui = self._deployment_ui_factory(width, height)
        else:
            raise ValueError(
                "deployment_ui_factory not set — inject via GameLoopAssembler "
                "to avoid service→presentation coupling."
            )

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

    def set_campaign_ui(self, campaign_ui: ICampaignUI) -> None:
        """Set the CampaignUI instance for campaign flow integration."""
        self._campaign_ui = campaign_ui
        # Propagate reference to event dispatcher so it can route input
        if self._event_dispatcher is not None:
            self._event_dispatcher._campaign_ui_ref = campaign_ui

    @property
    def campaign_ui(self) -> ICampaignUI | None:
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
            with contextlib.suppress(Exception):
                self._environmental_audio.stop_all()
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
