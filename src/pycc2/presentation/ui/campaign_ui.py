"""
Campaign UI Component

Full campaign screen flow:
- Operation Selection: Show available operations with historical briefings
- Battle Selection: Within an operation, show available battles
- Pre-Battle Briefing: Show map preview, objectives, available forces
- Start Battle: Transition to deployment/battle
- Post-Battle Report: Show results, casualties, experience gained, next battle
"""

from __future__ import annotations

import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)

import pygame
from pygame.font import Font

from .campaign_ui_rendering import CampaignUIRenderer

# Re-export public types for backward compatibility  # noqa: F401
from .campaign_ui_types import (  # noqa: F401
    BATTLE_ITEM_HEIGHT,
    BATTLE_LIST_WIDTH,
    BG_COLOR,
    BORDER_COLOR,
    BUTTON_BORDER,
    BUTTON_COLOR,
    BUTTON_HEIGHT,
    BUTTON_HOVER,
    BUTTON_WIDTH,
    COMPLETED_COLOR,
    DEFEAT_COLOR,
    HIGHLIGHT_COLOR,
    LOCKED_COLOR,
    MARGIN,
    MINIMAP_BG,
    OP_LIST_WIDTH,
    PANEL_COLOR,
    SELECTED_BG,
    TEXT_COLOR,
    VICTORY_COLOR,
    CampaignBattle,
    CampaignOperation,
)


class CampaignUI:
    """Campaign screen UI with full flow.

    States:
    - "operation_select": Choose an operation
    - "briefing": Historical briefing for selected operation
    - "battle_select": Choose a battle within the operation
    - "preview": Pre-battle preview with map, objectives, forces
    - "report": Post-battle results
    """

    # Layout constants (re-exported from types module for backward compat)
    MARGIN = MARGIN
    BATTLE_ITEM_HEIGHT = BATTLE_ITEM_HEIGHT
    BATTLE_LIST_WIDTH = BATTLE_LIST_WIDTH
    OP_LIST_WIDTH = OP_LIST_WIDTH
    BUTTON_WIDTH = BUTTON_WIDTH
    BUTTON_HEIGHT = BUTTON_HEIGHT

    # Colors (CC2 military palette)
    BG_COLOR = BG_COLOR
    PANEL_COLOR = PANEL_COLOR
    BORDER_COLOR = BORDER_COLOR
    TEXT_COLOR = TEXT_COLOR
    HIGHLIGHT_COLOR = HIGHLIGHT_COLOR
    SELECTED_BG = SELECTED_BG
    LOCKED_COLOR = LOCKED_COLOR
    COMPLETED_COLOR = COMPLETED_COLOR
    BUTTON_COLOR = BUTTON_COLOR
    BUTTON_HOVER = BUTTON_HOVER
    BUTTON_BORDER = BUTTON_BORDER
    VICTORY_COLOR = VICTORY_COLOR
    DEFEAT_COLOR = DEFEAT_COLOR
    MINIMAP_BG = MINIMAP_BG

    def __init__(self) -> None:
        self._font_title: Font | None = None
        self._font_normal: Font | None = None
        self._font_small: Font | None = None

        self._visible: bool = False
        self._state: str = "operation_select"
        self._operations: list[CampaignOperation] = []
        self._current_operation: CampaignOperation | None = None
        self._current_battle: CampaignBattle | None = None
        self._battle_result: dict | None = None
        self._selected_battle_id: str | None = None
        self._selected_op_id: str | None = None
        self._scroll_offset: int = 0
        self._hovered_battle_id: str | None = None
        self._hovered_button: str | None = None
        self._hovered_op_id: str | None = None

        # Clickable regions populated during render
        self._battle_rects: dict[str, pygame.Rect] = {}
        self._op_rects: dict[str, pygame.Rect] = {}
        self._start_button_rect: pygame.Rect | None = None
        self._back_button_rect: pygame.Rect | None = None
        self._proceed_button_rect: pygame.Rect | None = None
        self._deploy_button_rect: pygame.Rect | None = None
        self._continue_button_rect: pygame.Rect | None = None
        self._new_campaign_button_rect: pygame.Rect | None = None
        self._main_menu_button_rect: pygame.Rect | None = None

        # Campaign end summary data
        self._campaign_summary: dict | None = None

        # Callbacks
        self._on_start_battle: Callable[[str], None] | None = None
        self._on_back: Callable[[], None] | None = None

        # Renderer (holds all render logic)
        self._renderer = CampaignUIRenderer(self)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize fonts."""
        if not pygame.font.get_init():
            pygame.font.init()
        try:
            self._font_title = pygame.font.SysFont("consolas", 28, bold=True)
            self._font_normal = pygame.font.SysFont("consolas", 18)
            self._font_small = pygame.font.SysFont("consolas", 14)
        except (pygame.error, ValueError, OSError) as e:
            logging.debug("Campaign UI font fallback: %s", e)
            self._font_title = pygame.font.Font(None, 36)
            self._font_normal = pygame.font.Font(None, 24)
            self._font_small = pygame.font.Font(None, 18)

    def set_operations(self, operations: list[CampaignOperation]) -> None:
        """Set available campaign operations."""
        self._operations = operations
        self._selected_op_id = None
        self._scroll_offset = 0
        if operations:
            self._selected_op_id = operations[0].operation_id

    def set_operation(self, operation: CampaignOperation) -> None:
        """Set the campaign operation to display (battle_select state)."""
        self._current_operation = operation
        self._selected_battle_id = None
        self._scroll_offset = 0
        self._state = "battle_select"
        # Auto-select first unlocked battle
        for b in operation.battles:
            if not b.locked:
                self._selected_battle_id = b.battle_id
                break

    def show_operation_briefing(self, operation: CampaignOperation) -> None:
        """Show historical briefing for the selected operation."""
        self._current_operation = operation
        self._selected_battle_id = None
        self._scroll_offset = 0
        self._state = "briefing"
        # Auto-select first unlocked battle
        for b in operation.battles:
            if not b.locked:
                self._selected_battle_id = b.battle_id
                break

    def show_battle_preview(self, battle: CampaignBattle) -> None:
        """Show battle preview with map and objectives."""
        self._current_battle = battle
        self._state = "preview"

    def show_post_battle_report(self, result: dict) -> None:
        """Show post-battle results."""
        self._battle_result = result
        self._state = "report"

    def show_campaign_end(self, summary: dict) -> None:
        """Show campaign end screen with historical outcome.

        Args:
            summary: Dict from FourLayerCampaignManager.get_campaign_summary()
              - result: 'ALLIES_VICTORY' / 'AXIS_VICTORY' / 'DRAW'
              - day_ended: int (1-9)
              - allied_casualties: {'kia': int, 'wia': int}
              - axis_casualties: {'kia': int, 'wia': int}
              - bridge_status: {bridge_name: 'captured_allied'|'captured_axis'|'contested'}
        """
        self._campaign_summary = summary
        self._state = "campaign_end"

    def set_callbacks(
        self,
        on_start_battle: Callable[[str], None] | None = None,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        """Register UI callbacks."""
        self._on_start_battle = on_start_battle
        self._on_back = on_back

    def show(self) -> None:
        self._visible = True

    def hide(self) -> None:
        self._visible = False

    @property
    def is_visible(self) -> bool:
        return self._visible

    @property
    def state(self) -> str:
        return self._state

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def handle_click(self, screen_pos: tuple[int, int]) -> str | None:
        """Handle a mouse click. Returns an action string or None."""
        if not self._visible:
            return None

        x, y = screen_pos

        if self._state == "operation_select":
            return self._handle_click_operation_select(x, y)
        elif self._state == "briefing":
            return self._handle_click_briefing(x, y)
        elif self._state == "battle_select":
            return self._handle_click_battle_select(x, y)
        elif self._state == "preview":
            return self._handle_click_preview(x, y)
        elif self._state == "report":
            return self._handle_click_report(x, y)
        elif self._state == "campaign_end":
            return self._handle_click_campaign_end(x, y)

        return None

    def _handle_click_operation_select(self, x: int, y: int) -> str | None:
        """Handle clicks in operation selection state."""
        for op_id, rect in self._op_rects.items():
            if rect.collidepoint(x, y):
                self._selected_op_id = op_id
                return f"select_operation:{op_id}"

        # Proceed button
        if self._proceed_button_rect and self._proceed_button_rect.collidepoint(x, y):
            if self._selected_op_id:
                op = next(
                    (o for o in self._operations if o.operation_id == self._selected_op_id), None
                )
                if op:
                    self.show_operation_briefing(op)
                    return f"briefing:{self._selected_op_id}"

        # Back button
        if self._back_button_rect and self._back_button_rect.collidepoint(x, y):
            if self._on_back:
                self._on_back()
            return "back"

        return None

    def _handle_click_briefing(self, x: int, y: int) -> str | None:
        """Handle clicks in briefing state."""
        # Battle selection in briefing
        for battle_id, rect in self._battle_rects.items():
            if rect.collidepoint(x, y):
                self._selected_battle_id = battle_id
                return f"select_battle:{battle_id}"

        # Start Battle button
        if self._start_button_rect and self._start_button_rect.collidepoint(x, y):
            if self._selected_battle_id and self._current_operation:
                battle = next(
                    (
                        b
                        for b in self._current_operation.battles
                        if b.battle_id == self._selected_battle_id
                    ),
                    None,
                )
                if battle:
                    self.show_battle_preview(battle)
                    return f"preview:{self._selected_battle_id}"

        if self._back_button_rect and self._back_button_rect.collidepoint(x, y):
            self._state = "operation_select"
            return "back_to_operations"

        return None

    def _handle_click_battle_select(self, x: int, y: int) -> str | None:
        """Handle clicks in battle selection state."""
        for battle_id, rect in self._battle_rects.items():
            if rect.collidepoint(x, y):
                self._selected_battle_id = battle_id
                return f"select_battle:{battle_id}"

        # Start Battle button
        if self._start_button_rect and self._start_button_rect.collidepoint(x, y):
            if self._selected_battle_id:
                battle = next(
                    (
                        b
                        for b in self._current_operation.battles
                        if b.battle_id == self._selected_battle_id
                    ),
                    None,
                )
                if battle:
                    self.show_battle_preview(battle)
                    return f"preview:{self._selected_battle_id}"

        # Back button
        if self._back_button_rect and self._back_button_rect.collidepoint(x, y):
            if self._current_operation:
                self._state = "briefing"
                return "back_to_briefing"
            if self._on_back:
                self._on_back()
            return "back"

        return None

    def _handle_click_preview(self, x: int, y: int) -> str | None:
        """Handle clicks in preview state."""
        if self._deploy_button_rect and self._deploy_button_rect.collidepoint(x, y):
            if self._current_battle:
                if self._on_start_battle:
                    self._on_start_battle(self._current_battle.battle_id)
                return f"start_battle:{self._current_battle.battle_id}"

        if self._back_button_rect and self._back_button_rect.collidepoint(x, y):
            self._state = "battle_select"
            return "back_to_battles"

        return None

    def _handle_click_report(self, x: int, y: int) -> str | None:
        """Handle clicks in report state."""
        if self._continue_button_rect and self._continue_button_rect.collidepoint(x, y):
            # Mark current battle as completed and advance
            if self._current_battle:
                self._current_battle.completed = True
            self._state = "battle_select"
            return "continue_campaign"

        if self._back_button_rect and self._back_button_rect.collidepoint(x, y):
            self._state = "battle_select"
            return "back_to_battles"

        return None

    def _handle_click_campaign_end(self, x: int, y: int) -> str | None:
        """Handle clicks in campaign_end state."""
        if self._new_campaign_button_rect and self._new_campaign_button_rect.collidepoint(x, y):
            return "new_campaign"

        if self._main_menu_button_rect and self._main_menu_button_rect.collidepoint(x, y):
            if self._on_back:
                self._on_back()
            return "main_menu"

        return None

    def handle_mouse_move(self, screen_pos: tuple[int, int]) -> None:
        """Track hover state for visual feedback."""
        if not self._visible:
            return
        x, y = screen_pos
        self._hovered_battle_id = None
        self._hovered_button = None
        self._hovered_op_id = None

        for bid, rect in self._battle_rects.items():
            if rect.collidepoint(x, y):
                self._hovered_battle_id = bid
                break

        for op_id, rect in self._op_rects.items():
            if rect.collidepoint(x, y):
                self._hovered_op_id = op_id
                break

        if self._start_button_rect and self._start_button_rect.collidepoint(x, y):
            self._hovered_button = "start"
        elif self._back_button_rect and self._back_button_rect.collidepoint(x, y):
            self._hovered_button = "back"
        elif self._proceed_button_rect and self._proceed_button_rect.collidepoint(x, y):
            self._hovered_button = "proceed"
        elif self._deploy_button_rect and self._deploy_button_rect.collidepoint(x, y):
            self._hovered_button = "deploy"
        elif self._continue_button_rect and self._continue_button_rect.collidepoint(x, y):
            self._hovered_button = "continue"
        elif self._new_campaign_button_rect and self._new_campaign_button_rect.collidepoint(x, y):
            self._hovered_button = "new_campaign"
        elif self._main_menu_button_rect and self._main_menu_button_rect.collidepoint(x, y):
            self._hovered_button = "main_menu"

    def handle_scroll(self, dy: int) -> None:
        """Handle mouse scroll for lists."""
        if self._state == "operation_select":
            max_scroll = max(0, len(self._operations) - 6)
            self._scroll_offset = max(0, min(max_scroll, self._scroll_offset - dy))
        elif self._state in ("battle_select", "briefing") and self._current_operation:
            max_scroll = max(0, len(self._current_operation.battles) - 6)
            self._scroll_offset = max(0, min(max_scroll, self._scroll_offset - dy))

    # ------------------------------------------------------------------
    # Rendering (delegates to renderer)
    # ------------------------------------------------------------------

    def render(self, surface: pygame.Surface) -> None:
        """Render the campaign screen based on current state."""
        self._renderer.render(surface)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """Clean up resources."""
        pass
