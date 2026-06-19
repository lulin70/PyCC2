from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.domain.interfaces.game_state_view import GameStateView
    from pycc2.presentation.input.handler import PygameInputHandler
    from pycc2.presentation.input.interaction_controller import InteractionController
    from pycc2.presentation.rendering.camera import Camera

logger = logging.getLogger(__name__)


@dataclass
class InputRouter:
    input_handler: PygameInputHandler | None = None
    interaction_controller: InteractionController | None = None
    command_bar: object | None = None
    camera: Camera | None = None
    game_state: GameStateView | None = None
    show_post_battle: bool = False

    def route_input(self, event: pygame.event.EventType) -> bool:
        if self.input_handler is None:
            return False
        input_event = self.input_handler.process_event(event)
        if input_event is None:
            return False

        if input_event.event_type == "quit":
            if self.game_state:
                self.game_state.running = False
            return True
        elif input_event.event_type == "key_down":
            if input_event.key == pygame.K_ESCAPE:
                if self.game_state:
                    self.game_state.paused = not self.game_state.paused
                return True
            elif input_event.key == pygame.K_F3:
                if self.game_state:
                    self.game_state.debug_mode = not self.game_state.debug_mode
                return True
            if self.show_post_battle:
                if input_event.key in (pygame.K_ESCAPE, pygame.K_r):
                    if self.game_state:
                        # 按ESC或R键退出战斗结果画面，返回主菜单
                        self.game_state.running = False
                    return True
            if self.interaction_controller:
                # CC2-style: Track Ctrl key press for LOS overlay
                if input_event.key in (pygame.K_LCTRL, pygame.K_RCTRL):
                    self.interaction_controller.set_ctrl_held(True)
                else:
                    self.interaction_controller.handle_shortcut_key(input_event.key)

        elif input_event.event_type == "key_up":
            # CC2-style: Track Ctrl key release for LOS overlay
            if self.interaction_controller and input_event.key in (pygame.K_LCTRL, pygame.K_RCTRL):
                self.interaction_controller.set_ctrl_held(False)

        if self.command_bar and input_event.event_type == "mouse_click_left":
            cmd_id = self.command_bar.handle_click(input_event.position)
            if cmd_id:
                return True

        if self.command_bar and input_event.event_type == "mouse_move":
            self.command_bar.handle_mouse_move(input_event.position)

        if self.interaction_controller and self.game_state:
            if input_event.event_type == "mouse_click_left":
                # CRITICAL FIX: Pass actual unit list (not empty list!)
                # Get units from game_state for hit testing
                units = getattr(self.game_state, "units", [])

                logger.debug("Left click at %s, units count: %d", input_event.position, len(units))

                if units:
                    new_selection = self.interaction_controller.handle_left_click(
                        input_event.position, units, input_event.modifiers
                    )
                    self.game_state.selected_unit_ids = new_selection

                    logger.info("Selected %d unit(s): %s", len(new_selection), new_selection)
                else:
                    logger.warning("[BATTLE CLICK] No units in game_state.units - cannot select!")

            elif input_event.event_type == "mouse_click_right":
                # CRITICAL FIX: Pass actual unit list for right-click commands
                units = getattr(self.game_state, "units", [])
                logger.debug(
                    f"[BATTLE RIGHT-CLICK] Right click at {input_event.position}, units count: {len(units)}"
                )

                if units:
                    # CC2-style: Right-click DOWN on selected unit shows radial menu
                    self.interaction_controller.handle_right_mouse_down(input_event.position, units)

            elif input_event.event_type == "mouse_up_right":
                # CC2-style: Right-click UP → execute command from radial menu
                units = getattr(self.game_state, "units", [])
                shift_held = (
                    input_event.modifiers[1] if hasattr(input_event, "modifiers") else False
                )
                if units:
                    # P4 fix: Save drag state BEFORE handle_right_mouse_up resets it
                    was_dragging = self.interaction_controller._is_right_dragging

                    self.interaction_controller.handle_right_mouse_up(input_event.position, units)

                    # Only call handle_right_click for simple right-clicks (no radial menu used)
                    # handle_right_mouse_up() internally resets _is_right_dragging to False,
                    # so we must check the saved state to avoid double execution
                    if not was_dragging:
                        self.interaction_controller.handle_right_click(
                            input_event.position, units, shift_held=shift_held
                        )

            elif input_event.event_type == "mouse_move":
                # Handle attack line preview (CC2-style)
                if self.interaction_controller:
                    units = getattr(self.game_state, "units", [])
                    if units and hasattr(self.interaction_controller, "attack_line"):
                        self.interaction_controller.handle_mouse_move(
                            input_event.position,
                            units,
                        )
                    # CC2-style: Update radial menu hover during drag
                    self.interaction_controller.handle_drag_motion(input_event.position)

        if input_event.event_type in ("mouse_move", "mouse_click_left", "mouse_click_right"):
            dx, dy = self.input_handler.get_camera_movement()
            if (dx != 0 or dy != 0) and self.camera:
                self.camera.move(dx, dy)

        return True
