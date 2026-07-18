"""输入路由模块，将原始输入事件分发到对应控制器与命令栏。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pygame

if TYPE_CHECKING:
    from pycc2.domain.interfaces.camera_protocol import ICamera
    from pycc2.domain.interfaces.game_state_view import GameStateView
    from pycc2.domain.interfaces.input_handler_protocol import IInputHandler
    from pycc2.domain.interfaces.interaction_controller_protocol import IInteractionController
    from pycc2.presentation.ui.squad_group_manager import SquadGroupManager

logger = logging.getLogger(__name__)

# Digit keys 1-9 mapped to squad group numbers (CC2-style quick selection).
_SQUAD_DIGIT_KEYS: dict[int, int] = {
    pygame.K_1: 1,
    pygame.K_2: 2,
    pygame.K_3: 3,
    pygame.K_4: 4,
    pygame.K_5: 5,
    pygame.K_6: 6,
    pygame.K_7: 7,
    pygame.K_8: 8,
    pygame.K_9: 9,
}


@dataclass
class InputRouter:
    """输入事件路由器，将输入分派到交互控制器、命令栏与相机。"""

    input_handler: IInputHandler | None = None
    interaction_controller: IInteractionController | None = None
    command_bar: Any | None = None
    camera: ICamera | None = None
    game_state: GameStateView | None = None
    show_post_battle: bool = False
    # v0.7.5 INTEGRATE: Squad group manager for Ctrl+1~9 create / 1~9 select.
    squad_group_manager: SquadGroupManager | None = field(default=None)

    def route_input(self, event: pygame.event.EventType) -> bool:
        """Route input."""
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
            # v0.7.5 INTEGRATE: Squad group quick create/select (CC2-style).
            # Ctrl+1~9 → create/update group from current selection.
            # 1~9       → quick-select all units in that group.
            if (
                self.squad_group_manager is not None
                and input_event.key in _SQUAD_DIGIT_KEYS
                and self.game_state is not None
            ):
                group_num = _SQUAD_DIGIT_KEYS[input_event.key]
                ctrl_held = input_event.modifiers[0] if hasattr(input_event, "modifiers") else False
                if ctrl_held:
                    self._create_squad_group(group_num)
                else:
                    self._select_squad_group(group_num)
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

    # ------------------------------------------------------------------
    # v0.7.5 INTEGRATE: Squad group helpers (CC2-style Ctrl+1~9 / 1~9)
    # ------------------------------------------------------------------

    def _create_squad_group(self, group_num: int) -> bool:
        """Create/update a squad group from the currently selected units.

        Returns True if the group was created/updated, False otherwise
        (e.g. no units selected or invalid group number).
        """
        assert self.squad_group_manager is not None  # narrowed by caller
        assert self.game_state is not None  # narrowed by caller
        units = getattr(self.game_state, "units", [])
        selected_ids: set[str] = getattr(self.game_state, "selected_unit_ids", set())
        selected_units = [u for u in units if u.id in selected_ids]
        if not selected_units:
            logger.info("Cannot create squad group %d: no units selected", group_num)
            return False
        ok = self.squad_group_manager.create_group(group_num, selected_units)
        if ok:
            logger.info(
                "Squad group %d created with %d unit(s)",
                group_num,
                len(selected_units),
            )
        return ok

    def _select_squad_group(self, group_num: int) -> bool:
        """Quick-select all units in the given squad group.

        Returns True if the group had units and selection was updated,
        False if the group was empty or invalid.
        """
        assert self.squad_group_manager is not None  # narrowed by caller
        assert self.game_state is not None  # narrowed by caller
        units = self.squad_group_manager.select_group(group_num)
        if not units:
            logger.info("Squad group %d is empty — no selection made", group_num)
            return False
        # GameStateView protocol declares selected_unit_ids as set[str]
        self.game_state.selected_unit_ids = {u.id for u in units}
        logger.info("Squad group %d selected: %d unit(s)", group_num, len(units))
        return True
