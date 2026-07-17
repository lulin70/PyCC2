"""Main game loop driving update, rendering, and event handling each frame.

Facade that wires together all subsystems (input, AI, rendering, audio,
combat) into a fixed-timestep simulation with variable-rate rendering.

Behavior is split across focused mixin modules (P5-1 batch 2):
  - game_loop_types.py: GameState dataclass + LOGIC_DT/TARGET_FPS/MAX_FRAME_TIME
  - game_loop_rendering.py: GameLoopRenderingMixin (_apply_camera_effects, _render_scene)
  - game_loop_updating.py: GameLoopUpdatingMixin (_update_logic + 10 _update_* + _ensure_ai_units_registered)
  - game_loop_combat.py: GameLoopCombatMixin (_handle_player_command, _execute_attack, _on_*, _process_combat_popups)
  - game_loop.py (this facade): GameLoop dataclass + run() + deployment + save/load

Public API (100% backward-compatible):
  - GameState, GameLoop, LOGIC_DT, MAX_FRAME_TIME, TARGET_FPS
"""

from __future__ import annotations

import contextlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pygame

from pycc2.domain.interfaces import (
    IAchievementBridge,
    ICombatCamera,
    ICombatDirector,
    IDayNightCycle,
    IDeploymentManager,
    IDynamicShadowSystem,
    IEffectStack,
    IEnvironmentalAudio,
    IHintManager,
    IHUDManager,
    IInputRouter,
    ILightingRenderer,
    IPauseMenu,
    IPopupManager,
    IProjectileTrailSystem,
    IRenderPipeline,
    ISaveController,
    ISettingsMenu,
    ITutorialOverlay,
    IVictoryManager,
    IWeatherRenderer,
    IWeatherState,
    IWeatherSystem,
)
from pycc2.services.game_loop_combat import GameLoopCombatMixin
from pycc2.services.game_loop_rendering import GameLoopRenderingMixin
from pycc2.services.game_loop_types import (
    LOGIC_DT,
    MAX_FRAME_TIME,
    TARGET_FPS,
    GameState,
)
from pycc2.services.game_loop_updating import GameLoopUpdatingMixin

if TYPE_CHECKING:
    from pycc2.domain.interfaces.campaign_ui_protocol import ICampaignUI
    from pycc2.domain.interfaces.deployment_ui_protocol import IDeploymentUI
    from pycc2.domain.interfaces.display_config import DisplayConfig
    from pycc2.domain.interfaces.input_handler_protocol import IInputHandler as PygameInputHandler
    from pycc2.domain.interfaces.interaction_controller_protocol import (
        IInteractionController as InteractionController,
    )
    from pycc2.domain.interfaces.renderer_protocol import IRenderer as EnhancedRenderer
    from pycc2.domain.interfaces.window_manager_protocol import IWindowManager as WindowManager
    from pycc2.domain.systems.campaign_persistence import CampaignPersistenceManager
    from pycc2.infrastructure.events.event_bus import EventBus
    from pycc2.infrastructure.events.event_dispatcher import EventDispatcher
    from pycc2.presentation.audio.sound_system import SoundSystem
    from pycc2.presentation.ui.time_control import TimeControlUI
    from pycc2.services.ai_service import AIService

logger = logging.getLogger(__name__)

__all__ = [
    "LOGIC_DT",
    "MAX_FRAME_TIME",
    "TARGET_FPS",
    "GameLoop",
    "GameState",
]


@dataclass
class GameLoop(GameLoopRenderingMixin, GameLoopUpdatingMixin, GameLoopCombatMixin):
    """Top-level game loop wiring subsystems into a fixed-timestep simulation.

    Inherits rendering/update/combat methods from focused mixins. This facade
    retains the dataclass fields, main run() loop, deployment, save/load,
    and property accessors.
    """

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
    settings_menu: ISettingsMenu | None = None
    tutorial_overlay: ITutorialOverlay | None = None
    hint_manager: IHintManager | None = None

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
    # TD-076d (v0.7.0): Campaign persistence for cross-battle state inheritance
    _campaign_persistence: CampaignPersistenceManager | None = field(init=False, default=None)
    _ai_update_interval: int = field(init=False, default=3)
    _ai_tick_counter: int = field(init=False, default=0)
    _pause_menu: IPauseMenu | None = field(init=False, default=None)
    _deployment_manager: IDeploymentManager | None = field(init=False, default=None)
    _deployment_ui_factory: Callable[[int, int], Any] | None = None
    _event_dispatcher: EventDispatcher | None = field(init=False, default=None)
    _campaign_ui: ICampaignUI | None = field(init=False, default=None)
    time_control: TimeControlUI | None = field(init=False, default=None)
    _popup_manager: IPopupManager | None = field(init=False, default=None)
    _effect_stack: IEffectStack | None = field(init=False, default=None)
    _combat_camera: ICombatCamera | None = field(init=False, default=None)
    _achievement_bridge: IAchievementBridge | None = field(init=False, default=None)
    _projectile_trail_sys: IProjectileTrailSystem | None = field(init=False, default=None)
    _environmental_audio: IEnvironmentalAudio | None = field(init=False, default=None)
    _victory_delay: float = field(init=False, default=0.0)
    _weather_renderer: IWeatherRenderer | None = field(init=False, default=None)
    _weather_state: IWeatherState | None = field(init=False, default=None)
    _day_night_time: float | None = field(init=False, default=None)
    _lighting_renderer: ILightingRenderer | None = field(init=False, default=None)
    _weather_system: IWeatherSystem | None = field(init=False, default=None)
    _weather_effects: object | None = field(init=False, default=None)
    _day_night_cycle: IDayNightCycle | None = field(init=False, default=None)
    _dynamic_shadow_sys: IDynamicShadowSystem | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        from pycc2.services.game_loop_assembler import GameLoopAssembler

        GameLoopAssembler(self).assemble()

    # -- Backward-compatible properties delegating to DeploymentManager --

    @property
    def deployment_ui(self) -> IDeploymentUI | None:
        """Return the active deployment UI, or None if not in deployment."""
        if self._deployment_manager is None:
            return None
        return self._deployment_manager.deployment_ui

    @property
    def deployment_phase_active(self) -> bool:
        """Return whether the deployment phase is currently active."""
        return self._deployment_manager.is_active if self._deployment_manager else False

    def _get_time_speed(self) -> float:
        if self.time_control is not None:
            return self.time_control.speed_multiplier
        return 1.0

    def run(self) -> int:
        """Run the game loop. Returns 0 for normal exit, 1 for restart request."""
        from pycc2.infrastructure.diagnostics.preflight_check import run_preflight_check

        preflight = run_preflight_check(self)
        if not preflight.ok:
            logger.critical(
                "Preflight check failed, aborting startup: %s",
                preflight.failures,
            )
            return 1

        while self.state.running:
            new_time = time.perf_counter()
            frame_time = min(new_time - self._current_time, MAX_FRAME_TIME)
            self._current_time = new_time

            if frame_time > MAX_FRAME_TIME * 4:
                logger.debug("Long pause detected (%.2fs), resetting time base", frame_time)
                continue

            if self._event_dispatcher is None or not self._event_dispatcher.process_events():
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

            if self._render_pipeline is not None:
                self._render_pipeline.update_fps(self._fps)

            if self.tutorial_overlay:
                self.tutorial_overlay.update()
            if self.hint_manager:
                self.hint_manager.update()

            screen = self.window_manager.get_screen()

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
            elif screen and self._render_pipeline is not None:
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

    def _handle_input(self, event) -> None:
        if self._input_router is None:
            return
        if self._input_router.input_handler != self.input_handler:
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
        if self._deployment_manager is None:
            raise RuntimeError("DeploymentManager not initialized")

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
        if self._deployment_manager is None:
            return None
        return self._deployment_manager.complete(
            ai_service=self.ai_service,
            state=self.state,
        )

    def get_deployment_state(self) -> object | None:
        """Return the current deployment state, or None if not in deployment."""
        if self._deployment_manager is None:
            return None
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

    @property
    def campaign_persistence(self) -> CampaignPersistenceManager | None:
        """Public access to campaign persistence for cross-battle saves (TD-076d)."""
        return self._campaign_persistence

    def shutdown(self) -> None:
        """Tear down all subsystems and stop the game loop."""
        self.state.running = False
        if self._achievement_bridge is not None:
            self._achievement_bridge.save()
        if self._environmental_audio is not None:
            with contextlib.suppress(Exception):
                self._environmental_audio.stop_all()
        if self.sound_system is not None:
            self.sound_system.shutdown()
        if self.ai_service is not None:
            self.ai_service.shutdown()
        self.window_manager.shutdown()

    def quick_save(self, slot: int = 0) -> bool:
        """Save the current game state to the given slot."""
        if self._save_controller is None:
            return False
        return self._save_controller.quick_save(slot, self)

    def quick_load(self, slot: int = 0) -> bool:
        """Load game state from the given slot and reset victory manager."""
        if self._save_controller is None:
            return False
        result = self._save_controller.quick_load(slot, self)
        if result and self._victory_manager is not None:
            self._victory_manager.reset()
        return result

    def list_saves(self) -> list:
        """Return a list of available save slot metadata."""
        if self._save_controller is None:
            return []
        return self._save_controller.list_saves()
