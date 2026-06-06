"""GameLoop subsystem assembler — extracts 140-line __post_init__ from God Class.

``GameLoop`` had grown to 724 lines with a 140-line ``__post_init__`` that
assembled 15+ subsystems.  This module moves that assembly into a dedicated
class so ``GameLoop`` can focus on the game-loop *logic* (update, render,
event handling) rather than *wiring*.

**Architecture Note — Composition Root**
This module is the **Composition Root** for PyCC2.  It is the *only* place
where services layer code may reference presentation layer concrete classes
for instantiation.  All 9 ``from pycc2.presentation.*`` imports below are:

1. **Local (method-level) lazy imports** — never triggered at module load time
2. **Single responsibility** — each ``_init_*()`` method creates exactly one
   or two related objects and injects them into ``GameLoop``
3. **Not propagating** — no other service file imports from presentation at
   runtime; they receive objects via constructor/setter injection

This follows the `Dependency Rule` of Clean Architecture: the Composition Root
is the outermost shell that knows about all inner layers and wires them together.
See: https://blog.ploeh.dk/2011/07/28/CompositionRoot/

Usage inside ``GameLoop.__post_init__``::

    GameLoopAssembler(self).assemble()
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class GameLoopAssembler:
    """Wires all subsystems into a GameLoop instance.

    Call :meth:`assemble` once during ``GameLoop.__post_init__``.
    """

    def __init__(self, loop: "GameLoop") -> None:
        self._loop = loop

    def assemble(self) -> None:
        """Full initialization: sound, combat, rendering, input, UI, events, FX."""
        self._init_sound()
        self._init_core_services()
        self._init_combat_render_input()
        self._init_persistence()
        self._init_victory()
        self._init_ui_overlays()
        self._init_hud()
        self._init_event_dispatcher()
        self._init_camera_effects()
        self._init_achievements()
        self._init_visual_fx()

    # ------------------------------------------------------------------
    # Private helpers — each one initialises one logical group
    # ------------------------------------------------------------------

    def _init_sound(self) -> None:
        from pycc2.presentation.audio.sound_system import SoundSystem as SS
        from pycc2.domain.interfaces.display_config import DisplayConfig as DC

        if self._loop.display_config is None:
            self._loop.display_config = DC()
        if self._loop.sound_system is None:
            self._loop.sound_system = SS()
        self._loop.sound_system.initialize()

    def _init_core_services(self) -> None:
        from pycc2.services.deployment_manager import DeploymentManager
        from pycc2.services.pause_menu_controller import PauseMenuController

        self._loop._deployment_manager = DeploymentManager()
        self._loop._pause_menu = PauseMenuController()

    def _init_combat_render_input(self) -> None:
        from pycc2.services.combat_director import CombatDirector
        from pycc2.presentation.rendering.render_pipeline import RenderPipeline
        from pycc2.presentation.input.input_router import InputRouter

        self._loop._combat_director = CombatDirector(
            event_bus=self._loop.event_bus,
            display_config=self._loop.display_config,
            sound_system=self._loop.sound_system,
        )
        self._loop._combat_director.initialize()

        self._loop._render_pipeline = RenderPipeline(
            renderer=self._loop.renderer,
            window_manager=self._loop.window_manager,
            display_config=self._loop.display_config,
            ai_service=self._loop.ai_service,
            use_full_hud=self._loop.use_full_hud,
        )

        self._loop._input_router = InputRouter(
            input_handler=self._loop.input_handler,
            interaction_controller=self._loop.interaction_controller,
            camera=self._loop.state.camera,
            game_state=self._loop.state,
        )

    def _init_persistence(self) -> None:
        from pycc2.services.save_controller import SaveController

        self._loop._save_controller = SaveController()
        self._loop._save_controller.initialize()

    def _init_victory(self) -> None:
        from pycc2.services.victory_manager import VictoryManager

        self._loop._victory_manager = VictoryManager()
        self._loop._victory_manager.initialize(
            self._loop.event_bus, combat_director=self._loop._combat_director,
        )

        # Pass attack_line_system to renderer via DI setter (P0-2 Fix)
        if self._loop.interaction_controller:
            self._loop.renderer.set_attack_line_system(
                self._loop.interaction_controller.attack_line,
            )

    def _init_ui_overlays(self) -> None:
        from pycc2.presentation.ui.time_control import TimeControlUI
        from pycc2.presentation.ui.combat_popup import CombatPopupManager

        self._loop.time_control = TimeControlUI()
        self._loop._popup_manager = CombatPopupManager()

    def _init_hud(self) -> None:
        if not self._loop.use_full_hud:
            return
        from pycc2.services.hud_manager import HUDManager as HM

        from pycc2.presentation.rendering.minimap import Minimap
        from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel

        self._loop._hud_manager = HM()
        dc = self._loop.display_config
        # Create presentation objects here (Composition Root) and inject into service
        minimap = Minimap(display_config=dc, size=int(140 * dc.ui_scale))
        cc2_panel = CC2BottomPanel()
        cc2_panel.initialize()
        self._loop._hud_manager.initialize(
            state=self._loop.state,
            display_config=dc,
            sound_system=self._loop.sound_system,
            interaction_controller=self._loop.interaction_controller,
            event_bus=self._loop.event_bus,
            renderer=self._loop.renderer,
            window_manager=self._loop.window_manager,
            render_pipeline=self._loop._render_pipeline,
            input_router=self._loop._input_router,
            minimap=minimap,
            cc2_panel=cc2_panel,
        )

    def _init_event_dispatcher(self) -> None:
        from pycc2.services.event_dispatcher import EventDispatcher as ED

        self._loop._event_dispatcher = ED(
            state=self._loop.state,
            pause_menu=self._loop._pause_menu,
            deployment_manager=self._loop._deployment_manager,
            input_router=self._loop._input_router,
            time_control=self._loop.time_control,
            window_manager=self._loop.window_manager,
            settings_menu=self._loop.settings_menu,
            tutorial_overlay=self._loop.tutorial_overlay,
            hud_manager=self._loop._hud_manager,
            sound_system=self._loop.sound_system,
            event_bus=self._loop.event_bus,
            display_config=self._loop.display_config,
            victory_manager=self._loop._victory_manager,
            quick_save_fn=self._loop.quick_save,
            quick_load_fn=self._loop.quick_load,
            complete_deployment_fn=self._loop.complete_deployment,
        )

    def _init_camera_effects(self) -> None:
        from pycc2.presentation.rendering.camera_effects import EffectStack
        from pycc2.presentation.rendering.combat_camera_controller import CombatCameraController

        self._loop._effect_stack = EffectStack()
        self._loop._combat_camera = CombatCameraController(camera=self._loop.state.camera)
        self._loop._combat_camera.set_effect_stack(self._loop._effect_stack)
        self._loop._combat_camera.subscribe(self._loop.event_bus)

    def _init_achievements(self) -> None:
        from pycc2.domain.systems.achievement_system import (
            AchievementManager,
            create_default_achievements,
        )
        from pycc2.services.achievement_event_bridge import AchievementEventBridge

        achievement_mgr = AchievementManager()
        for ach in create_default_achievements():
            achievement_mgr.register(ach)
        achievement_mgr.load()
        self._loop._achievement_bridge = AchievementEventBridge(achievement_mgr)
        self._loop._achievement_bridge.subscribe(self._loop.event_bus)

    def _init_visual_fx(self) -> None:
        from pycc2.presentation.rendering.projectile_trail_system import ProjectileTrailSystem
        from pycc2.presentation.rendering.dynamic_shadow_system import DynamicShadowSystem

        self._loop._projectile_trail_sys = ProjectileTrailSystem()

        tile_size = (
            self._loop.renderer.TILE_SIZE
            if isinstance(self._loop.renderer.TILE_SIZE, int)
            else 48
        )
        self._loop._dynamic_shadow_sys = DynamicShadowSystem(tile_size=tile_size)

        # Wire trail and shadow systems into renderer
        if hasattr(self._loop.renderer, "set_projectile_trail_system"):
            self._loop.renderer.set_projectile_trail_system(self._loop._projectile_trail_sys)
        if hasattr(self._loop.renderer, "set_dynamic_shadow_system"):
            self._loop.renderer.set_dynamic_shadow_system(self._loop._dynamic_shadow_sys)

        self._loop.event_bus.subscribe_to("ProjectileFired", self._loop._on_projectile_fired)
