"""Event Dispatcher — handles all pygame event routing for the game loop.

Extracted from GameLoop to isolate event-handling concerns: global hotkeys,
settings menu, tutorial overlay, pause menu, deployment input, and battle
input are each delegated to dedicated private methods.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.domain.interfaces.deployment_manager_protocol import IDeploymentManager
    from pycc2.domain.interfaces.display_config import DisplayConfig
    from pycc2.domain.interfaces.hud_manager_protocol import IHUDManager
    from pycc2.domain.interfaces.input_router_protocol import IInputRouter
    from pycc2.domain.interfaces.pause_menu_protocol import IPauseMenu
    from pycc2.domain.interfaces.ui_overlay_protocol import ISettingsMenu, ITutorialOverlay
    from pycc2.domain.interfaces.victory_manager_protocol import IVictoryManager
    from pycc2.domain.interfaces.window_manager_protocol import IWindowManager
    from pycc2.infrastructure.events.event_bus import EventBus
    from pycc2.presentation.audio.sound_system import SoundSystem
    from pycc2.presentation.ui.time_control import TimeControlUI
    from pycc2.services.game_loop import GameState

logger = logging.getLogger(__name__)


@dataclass
class EventDispatcher:
    """Routes pygame events to the appropriate handler.

    Public API
    ----------
    process_events() -> bool
        Drain the pygame event queue and dispatch each event.
        Returns *True* to keep running, *False* when a quit was requested.
    """

    state: GameState
    pause_menu: IPauseMenu
    deployment_manager: IDeploymentManager
    input_router: IInputRouter
    time_control: TimeControlUI | None
    window_manager: IWindowManager
    settings_menu: ISettingsMenu | None
    tutorial_overlay: ITutorialOverlay | None
    hud_manager: IHUDManager | None
    sound_system: SoundSystem | None
    event_bus: EventBus
    display_config: DisplayConfig | None
    victory_manager: IVictoryManager | None = None
    _campaign_ui_ref: object | None = field(default=None, repr=False)
    quick_save_fn: Callable[[int], bool] | None = None
    quick_load_fn: Callable[[int], bool] | None = None
    complete_deployment_fn: Callable[[], object | None] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_events(self) -> bool:
        """Process all pending pygame events.

        Returns *True* if the game should keep running, *False* on quit.
        """
        for event in pygame.event.get():
            should_quit = self.window_manager.handle_event(event)
            if should_quit:
                self.state.running = False
                return False

            if self._handle_campaign_ui(event):
                continue

            if self._handle_settings_menu(event):
                continue

            if self._handle_global_keys(event):
                continue

            if self._handle_tutorial(event):
                continue

            if self._handle_pause_menu(event):
                continue

            if self._handle_deployment_input(event):
                continue

            self._handle_battle_input(event)

        return True

    # ------------------------------------------------------------------
    # Private handlers
    # ------------------------------------------------------------------

    def _handle_campaign_ui(self, event) -> bool:
        """Handle events when the campaign UI is visible.

        Returns *True* if the event was consumed.
        """
        # Access campaign_ui via the game_loop reference if available
        campaign_ui = getattr(self, "_campaign_ui_ref", None)
        if campaign_ui is None or not campaign_ui.is_visible:
            return False

        if event.type == pygame.MOUSEMOTION:
            campaign_ui.handle_mouse_move(event.pos)
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            campaign_ui.handle_click(event.pos)
            return True
        if event.type == pygame.MOUSEWHEEL:
            campaign_ui.handle_scroll(event.y)
            return True

        return True  # Consume all events while campaign UI is visible

    def _handle_settings_menu(self, event) -> bool:
        """Handle events when the settings menu is visible.

        Returns *True* if the event was consumed.
        """
        if self.settings_menu and self.settings_menu.visible:
            mouse_pos = pygame.mouse.get_pos()
            result = self.settings_menu.handle_input(event, mouse_pos)
            if result == "applied" and hasattr(self.settings_menu, "apply_to_systems"):
                self.settings_menu.apply_to_systems(sound_system=self.sound_system)
            return True
        return False

    def _handle_global_keys(self, event) -> bool:
        """Handle global keyboard shortcuts (F-keys, ESC).

        Returns *True* if the event was consumed.
        """
        if event.type != pygame.KEYDOWN:
            return False

        if event.key == pygame.K_F10:
            if self.settings_menu:
                self.settings_menu.toggle()
            return True

        if event.key == pygame.K_F5:
            if self.quick_save_fn is not None:
                self.quick_save_fn(0)
            return True

        if event.key == pygame.K_F9:
            if self.quick_load_fn is not None:
                self.quick_load_fn(0)
            return True

        if event.key == pygame.K_F1:
            if self.tutorial_overlay:
                self.tutorial_overlay.toggle()
            return True

        if event.key == pygame.K_ESCAPE:
            if self.settings_menu and self.settings_menu.visible:
                self.settings_menu.toggle()
                return True
            # Toggle pause menu
            self.pause_menu.toggle()
            if self.pause_menu.is_active:
                self.state.paused = True
            return True

        return False

    def _handle_tutorial(self, event) -> bool:
        """Handle events when the tutorial overlay is visible.

        Returns *True* if the event was consumed.
        """
        if self.tutorial_overlay and self.tutorial_overlay.visible:
            self.tutorial_overlay.handle_input(event)
            return True
        return False

    def _handle_pause_menu(self, event) -> bool:
        """Handle events when the pause menu is active.

        Returns *True* if the event was consumed.
        """
        if not self.pause_menu.is_active:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.pause_menu.update_mouse(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = self.pause_menu.handle_click(event.pos)
            if action == "resume":
                self.pause_menu.deactivate()
                self.state.paused = False
            elif action == "save":
                if self.quick_save_fn is not None:
                    self.quick_save_fn(0)
            elif action == "load":
                if self.quick_load_fn is not None:
                    self.quick_load_fn(0)
                self.pause_menu.deactivate()
            elif action == "quit_to_menu":
                self.state.running = False
        return True

    def _handle_deployment_input(self, event) -> bool:
        """Handle mouse events during the deployment phase.

        Returns *True* if the event was consumed (deployment is active).
        """
        if not self.deployment_manager.is_active:
            return False
        deployment_ui = self.deployment_manager.deployment_ui
        if deployment_ui is None:
            return False

        dc = self.display_config
        tile_size = dc.base_tile_size if dc else 16

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if event.button == 1:  # Left click
                drag_result = deployment_ui.handle_mouse_down(
                    mouse_pos[0],
                    mouse_pos[1],
                    map_offset_x=0,
                    map_offset_y=0,
                    tile_size=tile_size,
                )
                if drag_result and drag_result.startswith("drag_start"):
                    pass  # Drag started — will handle on MOUSEBUTTONUP
                else:
                    result = deployment_ui.handle_click_full(
                        mouse_pos[0],
                        mouse_pos[1],
                        map_offset_x=0,
                        map_offset_y=0,
                        tile_size=tile_size,
                    )
                    if result == "begin_battle":
                        if self.complete_deployment_fn is not None:
                            self.complete_deployment_fn()
            elif event.button == 3:  # Right click
                result = deployment_ui.handle_click_full(
                    mouse_pos[0],
                    mouse_pos[1],
                    map_offset_x=0,
                    map_offset_y=0,
                    tile_size=tile_size,
                    right_click=True,
                )
                # Handle pre-battle order (GAP-8)
                if result and result.startswith("set_order:"):
                    # Format: "set_order:<unit_id>,<tx>,<ty>"
                    try:
                        parts = result.split(":", 1)[1].split(",")
                        unit_id = parts[0]
                        tx, ty = int(parts[1]), int(parts[2])
                        self.deployment_manager.set_pending_order(unit_id, tx, ty)
                    except (IndexError, ValueError):
                        pass
        elif event.type == pygame.MOUSEMOTION:
            mouse_pos = pygame.mouse.get_pos()
            deployment_ui.update_button_hover(*mouse_pos)
            deployment_ui.handle_mouse_move(
                mouse_pos[0],
                mouse_pos[1],
                map_offset_x=0,
                map_offset_y=0,
                tile_size=tile_size,
            )
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()
            deployment_ui.handle_mouse_up(
                mouse_pos[0],
                mouse_pos[1],
                map_offset_x=0,
                map_offset_y=0,
                tile_size=tile_size,
            )

        return True

    def _handle_battle_input(self, event) -> None:
        """Route input events during the battle phase."""
        # Forward mouse state to HUD manager for hover/press/tooltip feedback
        if self.hud_manager is not None:
            if event.type == pygame.MOUSEMOTION:
                self.hud_manager.set_mouse_pos(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.hud_manager.set_mouse_pressed(True)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.hud_manager.set_mouse_pressed(False)

        if self.victory_manager is not None:
            self.input_router.show_post_battle = self.victory_manager.show_post_battle

        # Check for minimap click before routing to input
        if (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.hud_manager is not None
            and self.hud_manager.minimap is not None
        ):
            mouse_pos = pygame.mouse.get_pos()
            if self.hud_manager.minimap.contains_point(mouse_pos):
                self.hud_manager.minimap.handle_click(mouse_pos, self.state.camera)
                return

        # Route to input router
        try:
            result = self.input_router.route_input(event)
            if (
                not self.deployment_manager.is_active
                and event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
            ):
                logger.info(f"[BATTLE MODE] route_input returned: {result}")
        except (RuntimeError, ValueError, AttributeError) as e:
            logger.error("[BATTLE MODE] Error in route_input: %s", e)

        if event.type == pygame.KEYDOWN:
            if self.time_control and self.time_control.handle_key(event.key):
                return
