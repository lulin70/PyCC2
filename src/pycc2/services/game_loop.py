from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.audio.sound_system import SoundSystem
    from pycc2.presentation.input.handler import PygameInputHandler
    from pycc2.presentation.input.interaction_controller import InteractionController
    from pycc2.presentation.rendering.camera import Camera
    from pycc2.presentation.rendering.display_config import DisplayConfig
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
    from pycc2.presentation.rendering.window_config import WindowManager
    from pycc2.presentation.ui.deployment_ui import DeploymentUI
    from pycc2.presentation.ui.time_control import TimeControlUI
    from pycc2.services.ai_service import AIService
    from pycc2.services.event_bus import EventBus

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
    deployment_ui: DeploymentUI | None = None
    deployment_phase_active: bool = False

    _accumulator: float = 0.0
    _current_time: float = field(default_factory=time.perf_counter)
    _fps: float = 0.0
    _total_ticks: int = 0
    _hud_manager: object | None = field(init=False, default=None)
    _command_bar: object | None = field(init=False, default=None)
    _unit_panel: object | None = field(init=False, default=None)
    _minimap: object | None = field(init=False, default=None)
    _victory_evaluator: object | None = field(init=False, default=None)
    _battle_stats: object | None = field(init=False, default=None)
    _game_result: object | None = field(init=False, default=None)
    _game_over_tick: int = field(init=False, default=0)
    _show_post_battle: bool = field(init=False, default=False)

    _combat_director: object | None = field(init=False, default=None)
    _render_pipeline: object | None = field(init=False, default=None)
    _input_router: object | None = field(init=False, default=None)
    _save_controller: object | None = field(init=False, default=None)
    _ai_update_interval: int = field(init=False, default=3)
    _ai_tick_counter: int = field(init=False, default=0)
    _pause_menu_active: bool = field(init=False, default=False)
    _pause_menu_buttons: dict = field(init=False, default_factory=dict)
    _pause_menu_mouse: tuple[int, int] = field(init=False, default=(0, 0))
    _pause_menu_result: str | None = field(init=False, default=None)
    time_control: TimeControlUI | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        from pycc2.presentation.audio.sound_system import SoundSystem as SS
        from pycc2.presentation.input.input_router import InputRouter
        from pycc2.presentation.rendering.display_config import DisplayConfig as DC
        from pycc2.presentation.rendering.render_pipeline import RenderPipeline
        from pycc2.services.combat_director import CombatDirector
        from pycc2.services.save_controller import SaveController
        from pycc2.presentation.ui.time_control import TimeControlUI

        if self.display_config is None:
            self.display_config = DC()

        if self.sound_system is None:
            self.sound_system = SS()
        self.sound_system.initialize()

        self._combat_director = CombatDirector(
            event_bus=self.event_bus,
            display_config=self.display_config,
            sound_system=self.sound_system,
        )
        self._combat_director.initialize()

        self._render_pipeline = RenderPipeline(
            renderer=self.renderer,
            window_manager=self.window_manager,
            display_config=self.display_config,
            ai_service=self.ai_service,
            use_full_hud=self.use_full_hud,
        )

        self._input_router = InputRouter(
            input_handler=self.input_handler,
            interaction_controller=self.interaction_controller,
            camera=self.state.camera,
            game_state=self.state,
        )

        self._save_controller = SaveController()
        self._save_controller.initialize()

        self._init_victory_system()

        self.time_control = TimeControlUI()

        if self.use_full_hud:
            self._init_hud_system()

    def _init_victory_system(self) -> None:
        import time as _time

        from pycc2.domain.systems.victory_conditions import (
            BattleStats,
            VictoryConditionEvaluator,
            VictoryConditionType,
        )

        self._battle_stats = BattleStats(start_time=_time.perf_counter())
        self._victory_evaluator = VictoryConditionEvaluator(
            conditions=[
                VictoryConditionType.ELIMINATE_ENEMY_COMMANDER,
                VictoryConditionType.ELIMINATE_ALL_ENEMIES,
                VictoryConditionType.MORALE_COLLAPSE,
            ],
            time_limit_ticks=0,
            morale_threshold=10,
        )
        self._game_result = None

        from pycc2.services.event_protocol import UnitAttacked

        self.event_bus.subscribe(UnitAttacked, self._on_unit_attacked_for_stats)

    def _get_time_speed(self) -> float:
        if self.time_control is not None:
            return self.time_control.speed_multiplier
        return 1.0

    def _init_hud_system(self) -> None:
        from pycc2.presentation.audio.sound_system import SoundType
        from pycc2.presentation.rendering.command_bar import CommandBar
        from pycc2.presentation.rendering.hud import HUDManager
        from pycc2.presentation.rendering.minimap import Minimap
        from pycc2.presentation.rendering.unit_panel import UnitPanel
        from pycc2.services.event_protocol import PlayerCommand

        dc = self.display_config

        self._hud_manager = HUDManager(display_config=dc)
        self._command_bar = CommandBar(display_config=dc)
        self._unit_panel = UnitPanel(display_config=dc)
        self._minimap = Minimap(display_config=dc, size=int(140 * dc.ui_scale))

        self.state.camera.viewport_width = dc.window_width
        self.state.camera.viewport_height = dc.window_height

        optimal_zoom = dc.compute_default_zoom(
            self.state.game_map.width, self.state.game_map.height
        )
        self.state.camera.zoom = optimal_zoom

        if hasattr(self.renderer, "_display_config"):
            self.renderer._display_config = dc
            self.renderer.TILE_SIZE = dc.base_tile_size
            self.renderer.SPRITE_SIZE = dc.effective_sprite_size

        screen = self.window_manager.get_screen()
        if screen is not None:
            self._hud_manager.initialize()
            self._command_bar.initialize()
            self._unit_panel.initialize()

        self._render_pipeline.hud_manager = self._hud_manager
        self._render_pipeline.command_bar = self._command_bar
        self._render_pipeline.unit_panel = self._unit_panel
        self._render_pipeline.minimap = self._minimap
        self._input_router.command_bar = self._command_bar

        def on_move():
            if self.sound_system:
                self.sound_system.play_ui_command()
            if self.interaction_controller:
                from pycc2.presentation.input.interaction_controller import InteractionMode

                self.interaction_controller.set_mode(InteractionMode.MOVE)

        def on_attack():
            if self.sound_system:
                self.sound_system.play_ui_command()
            if self.interaction_controller:
                from pycc2.presentation.input.interaction_controller import InteractionMode

                self.interaction_controller.set_mode(InteractionMode.ATTACK)

        def on_hold():
            if self.sound_system:
                self.sound_system.play_ui_command()
            self.event_bus.publish(
                PlayerCommand(
                    command="defend",
                    unit_ids=list(self.state.selected_unit_ids),
                )
            )

        def on_dig_in():
            if self.sound_system:
                self.sound_system.play_ui_command()
            self.event_bus.publish(
                PlayerCommand(
                    command="take_cover",
                    unit_ids=list(self.state.selected_unit_ids),
                )
            )

        def on_cancel():
            if self.sound_system:
                self.sound_system.play(SoundType.UI_CANCEL)
            self.state.selected_unit_ids.clear()
            if self.interaction_controller:
                self.interaction_controller.clear_selection()

        self._command_bar.register_callback("move", on_move)
        self._command_bar.register_callback("attack", on_attack)
        self._command_bar.register_callback("hold", on_hold)
        self._command_bar.register_callback("dig_in", on_dig_in)
        self._command_bar.register_callback("cancel", on_cancel)

        # Register command execution callbacks to interaction_controller
        if self.interaction_controller:
            def execute_move(unit_ids: set[str], target):
                logger.info(f"[COMMAND] Moving {len(unit_ids)} unit(s) to ({target.x:.0f}, {target.y:.0f})")
                # Actually move the units!
                for unit in self.state.units:
                    if unit.id in unit_ids and unit.is_alive:
                        from pycc2.domain.value_objects.vec2 import Vec2
                        # Update position to target
                        if hasattr(unit, 'position') and unit.position is not None:
                            old_pos = unit.position.pixel_position
                            unit.position.pixel_position = Vec2(target.x, target.y)
                            logger.info(f"[MOVE] {unit.display_name}: ({old_pos.x:.0f},{old_pos.y:.0f}) -> ({target.x:.0f},{target.y:.0f})")
                self.event_bus.publish(PlayerCommand(
                    command="move",
                    unit_ids=list(unit_ids),
                    target=(target.x, target.y),
                ))

            def execute_attack(unit_ids: set[str], target_id: str):
                logger.info(f"[COMMAND] Attacking target {target_id} with {len(unit_ids)} unit(s)")
                self.event_bus.publish(PlayerCommand(
                    command="attack",
                    unit_ids=list(unit_ids),
                    target_id=target_id,
                ))

            self.interaction_controller.register_on_move(execute_move)
            self.interaction_controller.register_on_attack(execute_attack)

        self._minimap.set_map(self.state.game_map)

    def run(self) -> None:
        while self.state.running:
            new_time = time.perf_counter()
            frame_time = min(new_time - self._current_time, MAX_FRAME_TIME)
            self._current_time = new_time

            if frame_time > MAX_FRAME_TIME * 4:
                logger.debug("Long pause detected (%.2fs), resetting time base", frame_time)
                continue

            for event in pygame.event.get():
                should_quit = self.window_manager.handle_event(event)
                if should_quit:
                    self.state.running = False
                    break

                if self.settings_menu and self.settings_menu.visible:
                    mouse_pos = pygame.mouse.get_pos()
                    result = self.settings_menu.handle_input(event, mouse_pos)
                    if result == "applied":
                        if hasattr(self.settings_menu, "apply_to_systems"):
                            self.settings_menu.apply_to_systems(sound_system=self.sound_system)
                    continue

                if event.type == pygame.KEYDOWN and event.key == pygame.K_F10:
                    if self.settings_menu:
                        self.settings_menu.toggle()
                    continue

                if event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
                    # Quick Save
                    self.quick_save(0)
                    continue

                if event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
                    # Quick Load
                    self.quick_load(0)
                    continue

                if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                    if self.tutorial_overlay:
                        self.tutorial_overlay.toggle()
                    continue

                if self.tutorial_overlay and self.tutorial_overlay.visible:
                    self.tutorial_overlay.handle_input(event)
                    continue

                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.settings_menu and self.settings_menu.visible:
                        self.settings_menu.toggle()
                        continue
                    # Toggle pause menu
                    self._pause_menu_active = not self._pause_menu_active
                    if self._pause_menu_active:
                        self.state.paused = True
                    continue

                # Handle pause menu interactions
                if self._pause_menu_active:
                    if event.type == pygame.MOUSEMOTION:
                        self._pause_menu_mouse = event.pos
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        action = self._handle_pause_menu_click(event.pos)
                        if action == "resume":
                            self._pause_menu_active = False
                            self.state.paused = False
                        elif action == "save":
                            self.quick_save(0)
                        elif action == "load":
                            self.quick_load(0)
                            self._pause_menu_active = False
                        elif action == "quit_to_menu":
                            self.state.running = False
                    continue

                if self.deployment_phase_active and self.deployment_ui is not None:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = pygame.mouse.get_pos()
                        dc = self.display_config
                        tile_size = dc.base_tile_size if dc else 16
                        if event.button == 1:  # Left click
                            # Start drag or handle click
                            drag_result = self.deployment_ui.handle_mouse_down(
                                mouse_pos[0], mouse_pos[1],
                                map_offset_x=0, map_offset_y=0,
                                tile_size=tile_size,
                            )
                            if drag_result and drag_result.startswith("drag_start"):
                                # Drag started - will handle on MOUSEBUTTONUP
                                pass
                            else:
                                # Normal click handling
                                result = self.deployment_ui.handle_click_full(
                                    mouse_pos[0], mouse_pos[1],
                                    map_offset_x=0, map_offset_y=0,
                                    tile_size=tile_size,
                                )
                                if result == "begin_battle":
                                    self.complete_deployment()
                        elif event.button == 3:  # Right click
                            self.deployment_ui.handle_click_full(
                                mouse_pos[0], mouse_pos[1],
                                map_offset_x=0, map_offset_y=0,
                                tile_size=tile_size,
                                right_click=True,
                            )
                    elif event.type == pygame.MOUSEMOTION:
                        mouse_pos = pygame.mouse.get_pos()
                        self.deployment_ui.update_button_hover(*mouse_pos)
                        # Update drag position
                        dc = self.display_config
                        tile_size = dc.base_tile_size if dc else 16
                        self.deployment_ui.handle_mouse_move(
                            mouse_pos[0], mouse_pos[1],
                            map_offset_x=0, map_offset_y=0,
                            tile_size=tile_size,
                        )
                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        # Complete drag operation
                        mouse_pos = pygame.mouse.get_pos()
                        dc = self.display_config
                        tile_size = dc.base_tile_size if dc else 16
                        drop_result = self.deployment_ui.handle_mouse_up(
                            mouse_pos[0], mouse_pos[1],
                            map_offset_x=0, map_offset_y=0,
                            tile_size=tile_size,
                        )
                        # Handle drop result if needed
                        if drop_result == "place_unit":
                            pass  # Unit was placed successfully
                    continue

                self._input_router.show_post_battle = self._show_post_battle

                # Check for minimap click before routing to input
                if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                        and self._minimap is not None):
                    mouse_pos = pygame.mouse.get_pos()
                    if self._minimap.contains_point(mouse_pos):
                        self._minimap.handle_click(mouse_pos, self.state.camera)
                        continue

                # DEBUG: Log ALL mouse events in battle mode
                if not self.deployment_phase_active:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        logger.info(f"[BATTLE MODE] Mouse button {event.button} down at {event.pos}")
                    elif event.type == pygame.MOUSEBUTTONUP:
                        logger.info(f"[BATTLE MODE] Mouse button {event.button} up at {event.pos}")

                # Route to input router
                try:
                    result = self._input_router.route_input(event)
                    if not self.deployment_phase_active and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        logger.info(f"[BATTLE MODE] route_input returned: {result}")
                except Exception as e:
                    logger.error(f"[BATTLE MODE] Error in route_input: {e}")

                if event.type == pygame.KEYDOWN:
                    if self.time_control and self.time_control.handle_key(event.key):
                        continue

            self._accumulator += frame_time
            catchup_count = 0
            max_catchup = 5

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

            self._render_pipeline.update_fps(self._fps)

            if self.tutorial_overlay:
                self.tutorial_overlay.update()
            if self.hint_manager:
                self.hint_manager.update()

            screen = self.window_manager._screen

            if self.tutorial_overlay and self.tutorial_overlay.visible and screen:
                self.tutorial_overlay.render(screen)

            if self.settings_menu and self.settings_menu.visible:
                if screen:
                    self.settings_menu.render(screen)
            elif self.deployment_phase_active and self.deployment_ui is not None and screen:
                self._render_pipeline.render(
                    game_map=self.state.game_map,
                    units=self.state.units,
                    camera=self.state.camera,
                    alpha=alpha,
                    selected_unit_ids=self.state.selected_unit_ids,
                    debug_mode=self.state.debug_mode,
                    paused=self.state.paused,
                    tick=self.state.tick,
                    show_post_battle=self._show_post_battle,
                    game_result=self._game_result,
                    battle_stats=self._battle_stats,
                )
                dc = self.display_config
                tile_size = dc.base_tile_size if dc else 16
                self.deployment_ui.render(
                    screen, font=None,
                    map_offset_x=0, map_offset_y=0,
                    tile_size=tile_size,
                )
            else:
                if self._command_bar and self.state.selected_unit_ids:
                    selected_id = next(iter(self.state.selected_unit_ids), None)
                    selected_unit = next((u for u in self.state.units if u.id == selected_id), None)
                    self._command_bar.set_selected_unit(selected_unit)
                elif self._command_bar:
                    self._command_bar.set_selected_unit(None)

                self._render_pipeline.render(
                    game_map=self.state.game_map,
                    units=self.state.units,
                    camera=self.state.camera,
                    alpha=alpha,
                    selected_unit_ids=self.state.selected_unit_ids,
                    debug_mode=self.state.debug_mode,
                    paused=self.state.paused,
                    tick=self.state.tick,
                    show_post_battle=self._show_post_battle,
                    game_result=self._game_result,
                    battle_stats=self._battle_stats,
                )

            if self.hint_manager and screen:
                self.hint_manager.render(screen)

            # Draw pause menu overlay
            if self._pause_menu_active and screen:
                self._render_pause_menu(screen)

            pygame.display.flip()
            self.window_manager.tick(TARGET_FPS)
            self._fps = self.window_manager.fps

        self.shutdown()

    def _update_logic(self, dt: float) -> None:
        if self.state.paused:
            return

        self._combat_director.update(
            units=self.state.units,
            game_map=self.state.game_map,
            dt=dt,
            battle_stats=self._battle_stats,
        )
        self._combat_director.process_effects(renderer=self.renderer)

        if self.ai_service is not None and self.ai_service.managed_unit_count > 0:
            self._ai_tick_counter += 1
            if self._ai_tick_counter >= self._ai_update_interval:
                context: dict = {
                    "game_map": self.state.game_map,
                    "units": self.state.units,
                    "tick": self.state.tick,
                }
                intents = self.ai_service.update_all(dt, context)
                if intents:
                    self.ai_service.execute_intents(intents)
                self._ai_tick_counter = 0

        if self._victory_evaluator and self._battle_stats:
            self._battle_stats.ticks_elapsed = self.state.tick
            # 防止战斗刚开始就判定失败 - 至少等待5秒（300 ticks）
            if self.state.tick % 30 == 0 and self.state.tick >= 300:
                result, reason = self._victory_evaluator.evaluate(
                    self.state.units, self.state.tick, self._battle_stats
                )
                if result.name != "ONGOING":
                    self._game_result = result
                    self._game_over_tick = self.state.tick
                    self.state.paused = True
                    self._show_post_battle = True
                    if self.sound_system:
                        from pycc2.presentation.audio.sound_system import SoundType

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

    def _on_unit_attacked_for_stats(self, data: dict) -> None:
        self._combat_director.record_stats(data, self.state.units, self._battle_stats)

    def _handle_input(self, event) -> None:
        if self._input_router and self._input_router.input_handler != self.input_handler:
            self._input_router.input_handler = self.input_handler
        self._input_router.route_input(event)

    def _render_hud(self) -> None:
        pass

    def start_deployment(
        self,
        map_data: dict,
        faction: str = "ally",
        game_settings: GameSettings | None = None,
    ) -> None:
        """Create a DeploymentUI and activate the deployment phase.

        Parameters
        ----------
        map_data : dict
            Map data dict with width, height, tiles, spawn_points, etc.
        faction : str
            Player faction ("ally" or "axis").
        game_settings : GameSettings | None
            If provided, used to calculate requisition points and force pool.
        """
        from pycc2.domain.systems.game_settings import SUPPLY_EFFECTS
        from pycc2.presentation.ui.deployment_ui import DeploymentUI as DUI

        dc = self.display_config
        width = dc.window_width if dc else 800
        height = dc.window_height if dc else 600

        self.deployment_ui = DUI(width=width, height=height)

        # Calculate requisition points from game settings
        requisition_points = 2000
        max_infantry = 15   # Increased for better gameplay
        max_support = 10    # Increased for better gameplay
        force_pool = None

        if game_settings is not None:
            # Determine player side settings
            if faction in ("ally", "allied"):
                side_settings = game_settings.allied_settings
                enemy_side = "axis"
            else:
                side_settings = game_settings.axis_settings
                enemy_side = "allied"

            supply_effects = SUPPLY_EFFECTS[side_settings.supply_level]
            requisition_points = int(2000 * supply_effects.requisition_point_modifier)

            # Build force pool based on faction
            force_pool = DUI.build_force_pool_from_settings(
                faction=faction, requisition_points=requisition_points,
            )

        self.deployment_ui.start_deployment_with_settings(
            map_data=map_data,
            faction=faction,
            requisition_points=requisition_points,
            max_infantry=max_infantry,
            max_support=max_support,
            force_pool=force_pool,
        )
        self.deployment_phase_active = True

        # Generate AI deployment for enemy side
        self._ai_deployments: list[dict] = []
        if game_settings is not None:
            enemy_faction = "axis" if faction in ("ally", "allied") else "allied"
            if enemy_faction == "allied":
                enemy_supply = game_settings.allied_settings.supply_level
            else:
                enemy_supply = game_settings.axis_settings.supply_level
            enemy_supply_effects = SUPPLY_EFFECTS[enemy_supply]
            enemy_rp = int(1500 * enemy_supply_effects.requisition_point_modifier)

            self._ai_deployments = DUI.generate_ai_deployment(
                map_data=map_data,
                faction=enemy_faction,
                requisition_points=enemy_rp,
            )

        logger.info(
            "Deployment phase started — faction=%s, RP=%d, AI units=%d",
            faction, requisition_points, len(self._ai_deployments),
        )

    def complete_deployment(self) -> dict | None:
        """Finalize deployment and deactivate the deployment phase.

        Creates Unit entities from player placements and AI deployments,
        adds them to the game state, and initializes the AI service.

        Returns the deployment result dict from DeploymentUI.begin_battle(),
        or None if deployment is not active.
        """
        if not self.deployment_phase_active or self.deployment_ui is None:
            return None

        result = self.deployment_ui.begin_battle()
        self.deployment_phase_active = False

        # Create Unit entities from player deployments
        from pycc2.domain.components.health_component import HealthComponent
        from pycc2.domain.components.morale_component import MoraleComponent
        from pycc2.domain.components.position_component import PositionComponent
        from pycc2.domain.components.vision_component import VisionComponent
        from pycc2.domain.components.weapon_component import WeaponComponent
        from pycc2.domain.entities.unit import Faction, Unit, UnitType
        from pycc2.domain.value_objects.tile_coord import TileCoord

        player_faction = Faction.ALLIES
        ai_faction = Faction.AXIS

        # Map unit_type strings to UnitType enums
        _TYPE_MAP: dict[str, UnitType] = {
            "infantry": UnitType.INFANTRY_SQUAD,
            "support": UnitType.MACHINE_GUN_SQUAD,
            "vehicle": UnitType.TANK,
            "recon": UnitType.SNIPER_TEAM,
        }

        # More specific mapping based on template_id
        _TEMPLATE_TYPE_MAP: dict[str, UnitType] = {
            "us_at_team": UnitType.AT_GUN_TEAM,
            "ger_at_team": UnitType.AT_GUN_TEAM,
            "us_mortar_light": UnitType.MORTAR_TEAM,
            "us_mortar_heavy": UnitType.MORTAR_TEAM,
            "ger_mortar_light": UnitType.MORTAR_TEAM,
            "ger_mortar_heavy": UnitType.MORTAR_TEAM,
            "us_officer": UnitType.COMMANDER,
            "ger_officer": UnitType.COMMANDER,
        }

        # Weapon mapping
        _WEAPON_MAP: dict[str, tuple[str, int]] = {
            "infantry": ("rifle", 120),
            "support": ("mg", 250),
            "vehicle": ("tank_cannon", 30),
            "recon": ("sniper_rifle", 15),
        }
        _TEMPLATE_WEAPON_MAP: dict[str, tuple[str, int]] = {
            "us_at_team": ("at_gun", 8),
            "ger_at_team": ("at_gun", 8),
            "us_mortar_light": ("mortar", 6),
            "us_mortar_heavy": ("mortar", 6),
            "ger_mortar_light": ("mortar", 6),
            "ger_mortar_heavy": ("mortar", 6),
            "us_officer": ("pistol", 14),
            "ger_officer": ("pistol", 14),
        }

        # HP mapping
        _HP_MAP: dict[str, int] = {
            "infantry": 100,
            "support": 80,
            "vehicle": 200,
            "recon": 60,
        }

        unit_counter = 0

        # Create player units from deployment placements
        for placement in result.get("placements", []):
            template_id = placement["unit_template_id"]
            display_name = placement.get("display_name", template_id)
            unit_type_str = placement.get("unit_type", "infantry")
            pos = placement.get("position")
            if pos is None:
                continue

            unit_type = _TEMPLATE_TYPE_MAP.get(template_id, _TYPE_MAP.get(unit_type_str, UnitType.INFANTRY_SQUAD))
            weapon_id, max_ammo = _TEMPLATE_WEAPON_MAP.get(template_id, _WEAPON_MAP.get(unit_type_str, ("rifle", 120)))
            max_hp = _HP_MAP.get(unit_type_str, 100)

            unit = Unit(
                id=f"player_{unit_counter}",
                name=display_name,
                faction=player_faction,
                unit_type=unit_type,
                position=PositionComponent(tile_coord=TileCoord(pos[0], pos[1])),
                vision=VisionComponent(),
                health=HealthComponent(hp=max_hp, max_hp=max_hp),
                weapon=WeaponComponent(
                    primary_weapon_id=weapon_id,
                    max_ammo=max_ammo,
                    ammo_remaining=max_ammo,
                ),
                morale=MoraleComponent(value=75),
            )
            self.state.units.append(unit)
            unit_counter += 1

        # Create AI units from generated deployments
        for ai_placement in self._ai_deployments:
            template_id = ai_placement["unit_template_id"]
            display_name = ai_placement.get("display_name", template_id)
            unit_type_str = ai_placement.get("unit_type", "infantry")
            pos = ai_placement.get("position")
            if pos is None:
                continue

            unit_type = _TEMPLATE_TYPE_MAP.get(template_id, _TYPE_MAP.get(unit_type_str, UnitType.INFANTRY_SQUAD))
            weapon_id, max_ammo = _TEMPLATE_WEAPON_MAP.get(template_id, _WEAPON_MAP.get(unit_type_str, ("rifle", 120)))
            max_hp = _HP_MAP.get(unit_type_str, 100)

            unit = Unit(
                id=f"ai_{unit_counter}",
                name=display_name,
                faction=ai_faction,
                unit_type=unit_type,
                position=PositionComponent(tile_coord=TileCoord(pos[0], pos[1])),
                vision=VisionComponent(),
                health=HealthComponent(hp=max_hp, max_hp=max_hp),
                weapon=WeaponComponent(
                    primary_weapon_id=weapon_id,
                    max_ammo=max_ammo,
                    ammo_remaining=max_ammo,
                ),
                morale=MoraleComponent(value=75),
            )
            self.state.units.append(unit)
            unit_counter += 1

        # Initialize AI service with deployed AI units
        if self.ai_service is not None:
            try:
                from pycc2.domain.ai.behavior_tree import Selector, Sequence
                from pycc2.domain.ai.tactical_ai import AttackNearestAI, MoveToObjectiveAI

                for u in self.state.units:
                    if u.faction == ai_faction:
                        # Create a simple behavior tree for each AI unit
                        bt = Selector([
                            Sequence([AttackNearestAI()]),
                            Sequence([MoveToObjectiveAI()]),
                        ])
                        self.ai_service.register_ai_unit(u, bt)
            except ImportError as e:
                logger.warning(f"Could not initialize AI behavior tree: {e}")
                logger.info("Continuing without AI behavior trees (units will use default AI)")

        logger.info(
            "Deployment complete — player units=%d, AI units=%d, total=%d",
            result.get("infantry_count", 0) + result.get("support_count", 0),
            len(self._ai_deployments),
            len(self.state.units),
        )

        return result

    def get_deployment_state(self) -> object | None:
        """Return the current deployment state, or None if not in deployment."""
        if self.deployment_ui is None:
            return None
        return self.deployment_ui.state

    def shutdown(self) -> None:
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
            self._game_result = None
            self._show_post_battle = False
        return result

    def list_saves(self) -> list:
        return self._save_controller.list_saves()

    def _render_pause_menu(self, screen: pygame.Surface) -> None:
        """Render the pause menu overlay."""
        sw, sh = screen.get_size()

        # Semi-transparent overlay
        overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Menu panel
        panel_w, panel_h = 360, 320
        panel_x = (sw - panel_w) // 2
        panel_y = (sh - panel_h) // 2
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        pygame.draw.rect(screen, (38, 42, 34), panel_rect, border_radius=10)
        pygame.draw.rect(screen, (80, 85, 60), panel_rect, width=2, border_radius=10)

        # Title
        font = pygame.font.Font(None, 42)
        title_surf = font.render("PAUSED", True, (218, 195, 130))
        screen.blit(title_surf, ((sw - title_surf.get_width()) // 2, panel_y + 20))

        # Buttons
        self._pause_menu_buttons = {}
        btn_w, btn_h = 260, 48
        btn_x = (sw - btn_w) // 2
        btn_start_y = panel_y + 80
        gap = 58

        menu_items = [
            ("resume", "Resume"),
            ("save", "Save Game"),
            ("load", "Load Game"),
            ("quit_to_menu", "Quit to Menu"),
        ]

        font_btn = pygame.font.Font(None, 30)
        for i, (key, label) in enumerate(menu_items):
            rect = pygame.Rect(btn_x, btn_start_y + i * gap, btn_w, btn_h)
            self._pause_menu_buttons[key] = rect

            hovered = rect.collidepoint(self._pause_menu_mouse)
            bg = (70, 78, 55) if hovered else (50, 55, 42)
            pygame.draw.rect(screen, bg, rect, border_radius=6)
            pygame.draw.rect(screen, (90, 95, 65), rect, width=2, border_radius=6)

            txt_surf = font_btn.render(label, True, (220, 220, 210))
            screen.blit(txt_surf, txt_surf.get_rect(center=rect.center))

    def _handle_pause_menu_click(self, pos: tuple[int, int]) -> str | None:
        """Handle a click on the pause menu. Returns action string or None."""
        for key, rect in self._pause_menu_buttons.items():
            if rect.collidepoint(pos):
                return key
        return None
