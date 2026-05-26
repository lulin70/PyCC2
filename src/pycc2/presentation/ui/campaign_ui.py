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

from dataclasses import dataclass, field
from typing import Callable

import pygame
from pygame import Rect, Surface, draw
from pygame.font import Font


@dataclass
class CampaignBattle:
    """A single battle entry in the campaign."""

    battle_id: str
    name: str
    map_file: str
    description: str = ""
    completed: bool = False
    locked: bool = False
    objectives: list[str] = field(default_factory=list)
    allied_forces: list[str] = field(default_factory=list)
    axis_forces: list[str] = field(default_factory=list)


@dataclass
class CampaignOperation:
    """Top-level campaign operation data."""

    operation_id: str
    name: str
    day: int
    description: str = ""
    historical_briefing: str = ""
    battles: list[CampaignBattle] = field(default_factory=list)


class CampaignUI:
    """Campaign screen UI with full flow.

    States:
    - "operation_select": Choose an operation
    - "briefing": Historical briefing for selected operation
    - "battle_select": Choose a battle within the operation
    - "preview": Pre-battle preview with map, objectives, forces
    - "report": Post-battle results
    """

    # Layout constants
    MARGIN = 20
    BATTLE_ITEM_HEIGHT = 36
    BATTLE_LIST_WIDTH = 400
    OP_LIST_WIDTH = 500
    BUTTON_WIDTH = 140
    BUTTON_HEIGHT = 36

    # Colors (CC2 military palette)
    BG_COLOR = (40, 44, 52)
    PANEL_COLOR = (50, 55, 45)
    BORDER_COLOR = (90, 96, 80)
    TEXT_COLOR = (220, 220, 220)
    HIGHLIGHT_COLOR = (255, 255, 100)
    SELECTED_BG = (60, 70, 55)
    LOCKED_COLOR = (100, 100, 100)
    COMPLETED_COLOR = (80, 180, 80)
    BUTTON_COLOR = (65, 75, 58)
    BUTTON_HOVER = (85, 95, 72)
    BUTTON_BORDER = (110, 120, 95)
    VICTORY_COLOR = (80, 200, 80)
    DEFEAT_COLOR = (200, 80, 80)
    MINIMAP_BG = (30, 35, 25)

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
        self._battle_rects: dict[str, Rect] = {}
        self._op_rects: dict[str, Rect] = {}
        self._start_button_rect: Rect | None = None
        self._back_button_rect: Rect | None = None
        self._proceed_button_rect: Rect | None = None
        self._deploy_button_rect: Rect | None = None
        self._continue_button_rect: Rect | None = None

        # Callbacks
        self._on_start_battle: Callable[[str], None] | None = None
        self._on_back: Callable[[], None] | None = None

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
        except Exception:
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
        self._state = "briefing"

    def show_battle_preview(self, battle: CampaignBattle) -> None:
        """Show battle preview with map and objectives."""
        self._current_battle = battle
        self._state = "preview"

    def show_post_battle_report(self, result: dict) -> None:
        """Show post-battle results."""
        self._battle_result = result
        self._state = "report"

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
                op = next((o for o in self._operations if o.operation_id == self._selected_op_id), None)
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
        if self._proceed_button_rect and self._proceed_button_rect.collidepoint(x, y):
            if self._current_operation:
                self.set_operation(self._current_operation)
                return f"battle_select:{self._current_operation.operation_id}"

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
                    (b for b in self._current_operation.battles if b.battle_id == self._selected_battle_id),
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

    def handle_scroll(self, dy: int) -> None:
        """Handle mouse scroll for lists."""
        if self._state == "operation_select":
            max_scroll = max(0, len(self._operations) - 6)
            self._scroll_offset = max(0, min(max_scroll, self._scroll_offset - dy))
        elif self._state in ("battle_select",) and self._current_operation:
            max_scroll = max(0, len(self._current_operation.battles) - 6)
            self._scroll_offset = max(0, min(max_scroll, self._scroll_offset - dy))

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, surface: Surface) -> None:
        """Render the campaign screen based on current state."""
        if not self._visible or not self._font_title:
            return

        if self._state == "operation_select":
            self._render_operation_select(surface)
        elif self._state == "briefing":
            self._render_briefing(surface)
        elif self._state == "battle_select":
            self._render_battle_select(surface)
        elif self._state == "preview":
            self._render_preview(surface)
        elif self._state == "report":
            self._render_report(surface)

    def _render_operation_select(self, surface: Surface) -> None:
        """Render operation selection screen."""
        sw, sh = surface.get_size()
        surface.fill(self.BG_COLOR)
        self._op_rects = {}

        # Header
        header_y = self.MARGIN
        title_surf = self._font_title.render("OPERATION MARKET GARDEN", True, self.HIGHLIGHT_COLOR)
        surface.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, header_y))

        sep_y = header_y + title_surf.get_height() + 8
        draw.line(surface, self.BORDER_COLOR, (self.MARGIN, sep_y), (sw - self.MARGIN, sep_y), 1)

        # Operation list
        list_y = sep_y + 10
        list_h = sh - list_y - self.BUTTON_HEIGHT - self.MARGIN * 2 - 10
        list_x = sw // 2 - self.OP_LIST_WIDTH // 2
        list_w = self.OP_LIST_WIDTH

        draw.rect(surface, self.PANEL_COLOR, Rect(list_x, list_y, list_w, list_h))
        draw.rect(surface, self.BORDER_COLOR, Rect(list_x, list_y, list_w, list_h), 1)

        list_title = self._font_normal.render("SELECT OPERATION", True, self.HIGHLIGHT_COLOR)
        surface.blit(list_title, (list_x + 8, list_y + 4))
        draw.line(surface, self.BORDER_COLOR, (list_x, list_y + 24), (list_x + list_w, list_y + 24), 1)

        item_y = list_y + 28
        for op in self._operations:
            if item_y + self.BATTLE_ITEM_HEIGHT > list_y + list_h:
                break

            item_rect = Rect(list_x + 4, item_y, list_w - 8, self.BATTLE_ITEM_HEIGHT - 4)
            self._op_rects[op.operation_id] = item_rect

            is_selected = op.operation_id == self._selected_op_id
            is_hovered = op.operation_id == self._hovered_op_id

            if is_selected:
                bg = self.SELECTED_BG
            elif is_hovered:
                bg = (55, 62, 50)
            else:
                bg = (45, 50, 42)

            draw.rect(surface, bg, item_rect, border_radius=3)
            if is_selected:
                draw.rect(surface, self.HIGHLIGHT_COLOR, Rect(item_rect.left, item_rect.top, 2, item_rect.height))

            # Day badge
            day_surf = self._font_small.render(f"Day {op.day}", True, (180, 180, 170))
            surface.blit(day_surf, (item_rect.left + 6, item_rect.top + 4))

            # Operation name
            name_surf = self._font_normal.render(op.name, True, self.TEXT_COLOR)
            surface.blit(name_surf, (item_rect.left + 60, item_rect.top + 4))

            # Completed count
            completed = sum(1 for b in op.battles if b.completed)
            total = len(op.battles)
            if total > 0:
                prog_surf = self._font_small.render(f"{completed}/{total}", True, self.COMPLETED_COLOR if completed == total else (180, 180, 170))
                surface.blit(prog_surf, (item_rect.right - 40, item_rect.top + 4))

            item_y += self.BATTLE_ITEM_HEIGHT

        # Buttons
        btn_y = sh - self.BUTTON_HEIGHT - self.MARGIN
        self._proceed_button_rect = Rect(sw // 2 - self.BUTTON_WIDTH - 5, btn_y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
        self._back_button_rect = Rect(sw // 2 + 5, btn_y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)

        self._draw_button(surface, self._proceed_button_rect, "Proceed", self._hovered_button == "proceed")
        self._draw_button(surface, self._back_button_rect, "Back", self._hovered_button == "back", self.TEXT_COLOR)

    def _render_briefing(self, surface: Surface) -> None:
        """Render operation briefing screen."""
        sw, sh = surface.get_size()
        surface.fill(self.BG_COLOR)

        if not self._current_operation:
            return

        op = self._current_operation

        # Header
        header_y = self.MARGIN
        title_surf = self._font_title.render(op.name, True, self.HIGHLIGHT_COLOR)
        surface.blit(title_surf, (self.MARGIN, header_y))

        day_surf = self._font_normal.render(f"Day {op.day}", True, self.TEXT_COLOR)
        surface.blit(day_surf, (sw - self.MARGIN - day_surf.get_width(), header_y + 6))

        sep_y = header_y + title_surf.get_height() + 8
        draw.line(surface, self.BORDER_COLOR, (self.MARGIN, sep_y), (sw - self.MARGIN, sep_y), 1)

        # Briefing panel
        panel_y = sep_y + 10
        panel_h = sh - panel_y - self.BUTTON_HEIGHT - self.MARGIN * 2 - 10
        panel_x = self.MARGIN
        panel_w = sw - self.MARGIN * 2

        draw.rect(surface, self.PANEL_COLOR, Rect(panel_x, panel_y, panel_w, panel_h))
        draw.rect(surface, self.BORDER_COLOR, Rect(panel_x, panel_y, panel_w, panel_h), 1)

        # Briefing title
        briefing_title = self._font_normal.render("HISTORICAL BRIEFING", True, self.HIGHLIGHT_COLOR)
        surface.blit(briefing_title, (panel_x + 10, panel_y + 8))
        draw.line(surface, self.BORDER_COLOR, (panel_x, panel_y + 30), (panel_x + panel_w, panel_y + 30), 1)

        # Briefing text (word-wrapped)
        text = op.historical_briefing or op.description or "No briefing available."
        dy = panel_y + 38
        for line in self._wrap_text(text, self._font_normal, panel_w - 30):
            if dy + 20 > panel_y + panel_h:
                break
            ls = self._font_normal.render(line, True, (200, 200, 190))
            surface.blit(ls, (panel_x + 10, dy))
            dy += 22

        # Buttons
        btn_y = sh - self.BUTTON_HEIGHT - self.MARGIN
        self._proceed_button_rect = Rect(sw - self.MARGIN - self.BUTTON_WIDTH * 2 - 10, btn_y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
        self._back_button_rect = Rect(sw - self.MARGIN - self.BUTTON_WIDTH, btn_y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)

        self._draw_button(surface, self._proceed_button_rect, "Proceed", self._hovered_button == "proceed")
        self._draw_button(surface, self._back_button_rect, "Back", self._hovered_button == "back", self.TEXT_COLOR)

    def _render_battle_select(self, surface: Surface) -> None:
        """Render battle selection screen (original layout)."""
        sw, sh = surface.get_size()
        surface.fill(self.BG_COLOR)
        self._battle_rects = {}

        if not self._current_operation:
            msg = self._font_normal.render("No campaign loaded", True, self.TEXT_COLOR)
            surface.blit(msg, (sw // 2 - msg.get_width() // 2, sh // 2))
            return

        op = self._current_operation

        # Header
        header_y = self.MARGIN
        title_surf = self._font_title.render(op.name, True, self.HIGHLIGHT_COLOR)
        surface.blit(title_surf, (self.MARGIN, header_y))

        day_surf = self._font_normal.render(f"Day {op.day}", True, self.TEXT_COLOR)
        surface.blit(day_surf, (sw - self.MARGIN - day_surf.get_width(), header_y + 6))

        sep_y = header_y + title_surf.get_height() + 8
        draw.line(surface, self.BORDER_COLOR, (self.MARGIN, sep_y), (sw - self.MARGIN, sep_y), 1)

        # Description
        desc_y = sep_y + 10
        if op.description:
            desc_surf = self._font_small.render(op.description, True, (180, 180, 170))
            surface.blit(desc_surf, (self.MARGIN, desc_y))
            desc_y += desc_surf.get_height() + 8

        # Battle list panel
        list_y = desc_y + 5
        list_h = sh - list_y - self.BUTTON_HEIGHT - self.MARGIN * 2 - 10
        list_x = self.MARGIN
        list_w = min(self.BATTLE_LIST_WIDTH, sw - self.MARGIN * 2)

        draw.rect(surface, self.PANEL_COLOR, Rect(list_x, list_y, list_w, list_h))
        draw.rect(surface, self.BORDER_COLOR, Rect(list_x, list_y, list_w, list_h), 1)

        list_title = self._font_normal.render("BATTLES", True, self.HIGHLIGHT_COLOR)
        surface.blit(list_title, (list_x + 8, list_y + 4))
        draw.line(surface, self.BORDER_COLOR, (list_x, list_y + 24), (list_x + list_w, list_y + 24), 1)

        item_y = list_y + 28
        visible_battles = op.battles[self._scroll_offset:]
        for battle in visible_battles:
            if item_y + self.BATTLE_ITEM_HEIGHT > list_y + list_h:
                break

            item_rect = Rect(list_x + 4, item_y, list_w - 8, self.BATTLE_ITEM_HEIGHT - 4)
            self._battle_rects[battle.battle_id] = item_rect

            is_selected = battle.battle_id == self._selected_battle_id
            is_hovered = battle.battle_id == self._hovered_battle_id

            if battle.locked:
                bg = (40, 42, 45)
            elif is_selected:
                bg = self.SELECTED_BG
            elif is_hovered:
                bg = (55, 62, 50)
            else:
                bg = (45, 50, 42)

            draw.rect(surface, bg, item_rect, border_radius=3)
            if is_selected:
                draw.rect(surface, self.HIGHLIGHT_COLOR, Rect(item_rect.left, item_rect.top, 2, item_rect.height))

            if battle.completed:
                icon = self._font_small.render("[OK]", True, self.COMPLETED_COLOR)
            elif battle.locked:
                icon = self._font_small.render("[--]", True, self.LOCKED_COLOR)
            else:
                icon = self._font_small.render("[>]", True, self.HIGHLIGHT_COLOR)
            surface.blit(icon, (item_rect.left + 6, item_rect.top + 4))

            name_color = self.LOCKED_COLOR if battle.locked else self.TEXT_COLOR
            name_surf = self._font_normal.render(battle.name, True, name_color)
            surface.blit(name_surf, (item_rect.left + 40, item_rect.top + 4))

            item_y += self.BATTLE_ITEM_HEIGHT

        # Right panel: selected battle description
        right_x = list_x + list_w + 15
        right_w = sw - right_x - self.MARGIN
        if right_w > 100:
            draw.rect(surface, self.PANEL_COLOR, Rect(right_x, list_y, right_w, list_h))
            draw.rect(surface, self.BORDER_COLOR, Rect(right_x, list_y, right_w, list_h), 1)

            sel_battle = None
            if self._selected_battle_id:
                sel_battle = next(
                    (b for b in op.battles if b.battle_id == self._selected_battle_id), None
                )

            if sel_battle:
                bt_title = self._font_normal.render(sel_battle.name, True, self.HIGHLIGHT_COLOR)
                surface.blit(bt_title, (right_x + 8, list_y + 8))

                if sel_battle.description:
                    dy = list_y + 32
                    for line in self._wrap_text(sel_battle.description, self._font_small, right_w - 20):
                        if dy + 16 > list_y + list_h:
                            break
                        ls = self._font_small.render(line, True, (180, 180, 170))
                        surface.blit(ls, (right_x + 8, dy))
                        dy += 16

                if sel_battle.map_file:
                    map_label = self._font_small.render(f"Map: {sel_battle.map_file}", True, (150, 150, 140))
                    surface.blit(map_label, (right_x + 8, list_y + list_h - 22))
            else:
                hint = self._font_small.render("Select a battle", True, (128, 128, 128))
                surface.blit(hint, (right_x + 8, list_y + 8))

        # Buttons
        btn_y = sh - self.BUTTON_HEIGHT - self.MARGIN
        self._start_button_rect = Rect(sw - self.MARGIN - self.BUTTON_WIDTH * 2 - 10, btn_y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
        self._back_button_rect = Rect(sw - self.MARGIN - self.BUTTON_WIDTH, btn_y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)

        self._draw_button(surface, self._start_button_rect, "Start Battle", self._hovered_button == "start")
        self._draw_button(surface, self._back_button_rect, "Back", self._hovered_button == "back", self.TEXT_COLOR)

    def _render_preview(self, surface: Surface) -> None:
        """Render pre-battle preview with mini map, objectives, and forces."""
        sw, sh = surface.get_size()
        surface.fill(self.BG_COLOR)

        if not self._current_battle:
            return

        battle = self._current_battle

        # Header
        header_y = self.MARGIN
        title_surf = self._font_title.render(battle.name, True, self.HIGHLIGHT_COLOR)
        surface.blit(title_surf, (self.MARGIN, header_y))

        sep_y = header_y + title_surf.get_height() + 8
        draw.line(surface, self.BORDER_COLOR, (self.MARGIN, sep_y), (sw - self.MARGIN, sep_y), 1)

        # Left panel: Mini map
        map_panel_size = min(280, sh - sep_y - 120)
        map_x = self.MARGIN
        map_y = sep_y + 10

        draw.rect(surface, self.MINIMAP_BG, Rect(map_x, map_y, map_panel_size, map_panel_size))
        draw.rect(surface, self.BORDER_COLOR, Rect(map_x, map_y, map_panel_size, map_panel_size), 1)

        map_label = self._font_small.render(f"Map: {battle.map_file}", True, (150, 150, 140))
        surface.blit(map_label, (map_x + 4, map_y + map_panel_size + 4))

        # Draw a simple terrain preview grid
        self._draw_mini_map(surface, map_x, map_y, map_panel_size, battle.map_file)

        # Right panel: Objectives and forces
        right_x = map_x + map_panel_size + 20
        right_w = sw - right_x - self.MARGIN
        right_y = map_y

        # Objectives section
        obj_panel_h = map_panel_size // 2 - 5
        draw.rect(surface, self.PANEL_COLOR, Rect(right_x, right_y, right_w, obj_panel_h))
        draw.rect(surface, self.BORDER_COLOR, Rect(right_x, right_y, right_w, obj_panel_h), 1)

        obj_title = self._font_normal.render("OBJECTIVES", True, self.HIGHLIGHT_COLOR)
        surface.blit(obj_title, (right_x + 8, right_y + 4))
        draw.line(surface, self.BORDER_COLOR, (right_x, right_y + 24), (right_x + right_w, right_y + 24), 1)

        dy = right_y + 28
        if battle.objectives:
            for obj in battle.objectives:
                if dy + 16 > right_y + obj_panel_h:
                    break
                obj_surf = self._font_small.render(f"  * {obj}", True, (200, 200, 190))
                surface.blit(obj_surf, (right_x + 8, dy))
                dy += 16
        else:
            obj_surf = self._font_small.render("  Secure the objective", True, (180, 180, 170))
            surface.blit(obj_surf, (right_x + 8, dy))

        # Forces section
        forces_y = right_y + obj_panel_h + 10
        forces_panel_h = map_panel_size // 2 - 5
        draw.rect(surface, self.PANEL_COLOR, Rect(right_x, forces_y, right_w, forces_panel_h))
        draw.rect(surface, self.BORDER_COLOR, Rect(right_x, forces_y, right_w, forces_panel_h), 1)

        forces_title = self._font_normal.render("AVAILABLE FORCES", True, self.HIGHLIGHT_COLOR)
        surface.blit(forces_title, (right_x + 8, forces_y + 4))
        draw.line(surface, self.BORDER_COLOR, (right_x, forces_y + 24), (right_x + right_w, forces_y + 24), 1)

        dy = forces_y + 28
        # Allied forces
        allied_label = self._font_small.render("Allied:", True, self.COMPLETED_COLOR)
        surface.blit(allied_label, (right_x + 8, dy))
        dy += 16
        for force in (battle.allied_forces or ["Standard Infantry Platoon"]):
            if dy + 14 > forces_y + forces_panel_h:
                break
            f_surf = self._font_small.render(f"  {force}", True, (180, 180, 170))
            surface.blit(f_surf, (right_x + 8, dy))
            dy += 14

        dy += 4
        # Axis forces
        axis_label = self._font_small.render("Axis:", True, self.DEFEAT_COLOR)
        surface.blit(axis_label, (right_x + 8, dy))
        dy += 16
        for force in (battle.axis_forces or ["German Garrison"]):
            if dy + 14 > forces_y + forces_panel_h:
                break
            f_surf = self._font_small.render(f"  {force}", True, (180, 180, 170))
            surface.blit(f_surf, (right_x + 8, dy))
            dy += 14

        # Description below
        desc_y = map_y + map_panel_size + 24
        if battle.description:
            for line in self._wrap_text(battle.description, self._font_small, sw - self.MARGIN * 2):
                desc_surf = self._font_small.render(line, True, (180, 180, 170))
                surface.blit(desc_surf, (self.MARGIN, desc_y))
                desc_y += 16

        # Buttons
        btn_y = sh - self.BUTTON_HEIGHT - self.MARGIN
        self._deploy_button_rect = Rect(sw - self.MARGIN - self.BUTTON_WIDTH * 2 - 10, btn_y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
        self._back_button_rect = Rect(sw - self.MARGIN - self.BUTTON_WIDTH, btn_y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)

        self._draw_button(surface, self._deploy_button_rect, "Deploy", self._hovered_button == "deploy")
        self._draw_button(surface, self._back_button_rect, "Back", self._hovered_button == "back", self.TEXT_COLOR)

    def _render_report(self, surface: Surface) -> None:
        """Render post-battle report with narrative elements."""
        sw, sh = surface.get_size()
        surface.fill(self.BG_COLOR)

        result = self._battle_result or {}

        # Victory/Defeat banner
        is_victory = result.get("victory", False)
        victor = result.get("winner", "allies" if is_victory else "axis")
        if is_victory or victor == "allies":
            banner_color = self.VICTORY_COLOR
            banner_text = "VICTORY"
        elif victor == "axis":
            banner_color = self.DEFEAT_COLOR
            banner_text = "DEFEAT"
        else:
            banner_color = self.HIGHLIGHT_COLOR
            banner_text = "DRAW"

        banner_y = self.MARGIN
        banner_surf = self._font_title.render(banner_text, True, banner_color)
        surface.blit(banner_surf, (sw // 2 - banner_surf.get_width() // 2, banner_y))

        sep_y = banner_y + banner_surf.get_height() + 8
        draw.line(surface, self.BORDER_COLOR, (self.MARGIN, sep_y), (sw - self.MARGIN, sep_y), 1)

        # Battle name
        battle_name = result.get("battle_name", "Unknown Battle")
        name_surf = self._font_normal.render(battle_name, True, self.HIGHLIGHT_COLOR)
        surface.blit(name_surf, (sw // 2 - name_surf.get_width() // 2, sep_y + 8))

        # Narrative summary section
        narrative_y = sep_y + 36
        narrative_h = sh - narrative_y - self.BUTTON_HEIGHT - self.MARGIN * 2 - 10

        # Left panel: Narrative battle summary
        left_w = (sw - self.MARGIN * 3) // 2
        left_x = self.MARGIN
        draw.rect(surface, self.PANEL_COLOR, Rect(left_x, narrative_y, left_w, narrative_h))
        draw.rect(surface, self.BORDER_COLOR, Rect(left_x, narrative_y, left_w, narrative_h), 1)

        nar_title = self._font_normal.render("BATTLE SUMMARY", True, self.HIGHLIGHT_COLOR)
        surface.blit(nar_title, (left_x + 8, narrative_y + 4))
        draw.line(surface, self.BORDER_COLOR, (left_x, narrative_y + 24), (left_x + left_w, narrative_y + 24), 1)

        dy = narrative_y + 30
        narrative_lines = self._generate_narrative_report(result)
        for line in narrative_lines:
            if dy + 16 > narrative_y + narrative_h:
                break
            if line.startswith("---"):
                # Section header
                line_surf = self._font_normal.render(line, True, self.HIGHLIGHT_COLOR)
            elif "Killed in Action" in line:
                line_surf = self._font_small.render(line, True, self.DEFEAT_COLOR)
            elif any(kw in line for kw in ["commendation", "heroic", "held the line", "rallied", "distinguished"]):
                line_surf = self._font_small.render(line, True, self.COMPLETED_COLOR)
            else:
                line_surf = self._font_small.render(line, True, (200, 200, 190))
            surface.blit(line_surf, (left_x + 8, dy))
            dy += 16

        # Right panel: Casualties & Experience
        right_x = self.MARGIN * 2 + left_w
        right_w = sw - right_x - self.MARGIN
        draw.rect(surface, self.PANEL_COLOR, Rect(right_x, narrative_y, right_w, narrative_h))
        draw.rect(surface, self.BORDER_COLOR, Rect(right_x, narrative_y, right_w, narrative_h), 1)

        # Casualties section
        cas_title = self._font_normal.render("CASUALTIES", True, self.HIGHLIGHT_COLOR)
        surface.blit(cas_title, (right_x + 8, narrative_y + 4))
        draw.line(surface, self.BORDER_COLOR, (right_x, narrative_y + 24), (right_x + right_w, narrative_y + 24), 1)

        dy = narrative_y + 30
        casualties = result.get("casualties", {})
        if casualties:
            for side, data in casualties.items():
                side_label = self._font_normal.render(f"{side}:", True, self.TEXT_COLOR)
                surface.blit(side_label, (right_x + 8, dy))
                dy += 20
                if isinstance(data, dict):
                    for key, val in data.items():
                        if dy + 16 > narrative_y + narrative_h:
                            break
                        entry = self._font_small.render(f"  {key}: {val}", True, (180, 180, 170))
                        surface.blit(entry, (right_x + 8, dy))
                        dy += 16
                else:
                    entry = self._font_small.render(f"  Total: {data}", True, (180, 180, 170))
                    surface.blit(entry, (right_x + 8, dy))
                    dy += 16
                dy += 6
        else:
            no_data = self._font_small.render("No casualty data available", True, (128, 128, 128))
            surface.blit(no_data, (right_x + 8, dy))
            dy += 16

        # Experience section
        dy += 10
        exp_title = self._font_normal.render("EXPERIENCE", True, self.HIGHLIGHT_COLOR)
        surface.blit(exp_title, (right_x + 8, dy))
        draw.line(surface, self.BORDER_COLOR, (right_x, dy + 20), (right_x + right_w, dy + 20), 1)
        dy += 26

        experience = result.get("experience", {})
        if experience:
            for key, val in experience.items():
                if dy + 16 > narrative_y + narrative_h:
                    break
                entry = self._font_small.render(f"  {key}: {val}", True, (180, 180, 170))
                surface.blit(entry, (right_x + 8, dy))
                dy += 16
        else:
            no_data = self._font_small.render("No experience data available", True, (128, 128, 128))
            surface.blit(no_data, (right_x + 8, dy))

        # Buttons
        btn_y = sh - self.BUTTON_HEIGHT - self.MARGIN
        self._continue_button_rect = Rect(sw - self.MARGIN - self.BUTTON_WIDTH * 2 - 10, btn_y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
        self._back_button_rect = Rect(sw - self.MARGIN - self.BUTTON_WIDTH, btn_y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)

        self._draw_button(surface, self._continue_button_rect, "Continue", self._hovered_button == "continue")
        self._draw_button(surface, self._back_button_rect, "Back", self._hovered_button == "back", self.TEXT_COLOR)

    def _generate_narrative_report(self, result: dict) -> list[str]:
        """Generate a narrative post-battle report."""
        lines = []

        # Header
        victor = result.get("winner", "unknown")
        is_victory = result.get("victory", False)
        if is_victory or victor == "allies":
            lines.append("Allied forces have secured the objective!")
        elif victor == "axis":
            lines.append("Axis forces have prevailed.")
        else:
            lines.append("Neither side achieved decisive victory.")

        lines.append("")

        # Key events narrative
        events = result.get("key_events", [])
        if events:
            lines.append("--- Key Events ---")
            for event in events:
                lines.append(f"  {event}")

        # Casualties with names
        allied_kia = result.get("allied_kia", [])
        if allied_kia:
            lines.append("")
            lines.append("--- Fallen ---")
            for name in allied_kia:
                lines.append(f"  {name} - Killed in Action")

        # Heroic actions
        heroic = result.get("heroic_actions", [])
        if heroic:
            lines.append("")
            lines.append("--- Commendations ---")
            for action in heroic:
                lines.append(f"  {action}")

        # If no narrative data, show basic summary
        if not events and not allied_kia and not heroic:
            lines.append("")
            lines.append("--- Summary ---")
            casualties = result.get("casualties", {})
            if casualties:
                for side, data in casualties.items():
                    if isinstance(data, dict):
                        kia = data.get("killed", data.get("KIA", 0))
                        wounded = data.get("wounded", data.get("Wounded", 0))
                        if kia or wounded:
                            lines.append(f"  {side}: {kia} KIA, {wounded} Wounded")
                    else:
                        lines.append(f"  {side}: {data} casualties")
            else:
                lines.append("  No significant casualties reported.")

        return lines

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def _draw_button(
        self, surface: Surface, rect: Rect, text: str, hovered: bool, text_color: tuple | None = None
    ) -> None:
        """Draw a styled button."""
        bg = self.BUTTON_HOVER if hovered else self.BUTTON_COLOR
        draw.rect(surface, bg, rect, border_radius=4)
        draw.rect(surface, self.BUTTON_BORDER, rect, 1, border_radius=4)
        color = text_color or self.HIGHLIGHT_COLOR
        txt = self._font_normal.render(text, True, color)
        surface.blit(
            txt,
            (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2),
        )

    def _wrap_text(self, text: str, font: Font, max_width: int) -> list[str]:
        """Word-wrap text to fit within max_width."""
        words = text.split()
        lines: list[str] = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if font.size(test)[0] < max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        return lines

    def _draw_mini_map(self, surface: Surface, x: int, y: int, size: int, map_file: str) -> None:
        """Draw a simple terrain preview for the given map file."""
        # Try to load the map and render a mini preview
        try:
            import json
            from pathlib import Path
            map_path = Path(f"data/maps/{map_file}.json")
            if not map_path.exists():
                # Try without extension
                map_path = Path(f"data/maps/{map_file}")
            if map_path.exists():
                with open(map_path) as f:
                    map_data = json.load(f)
                tiles = map_data.get("tiles", [])
                if tiles:
                    rows = len(tiles)
                    cols = len(tiles[0]) if tiles else 0
                    if rows > 0 and cols > 0:
                        tile_w = size / cols
                        tile_h = size / rows
                        terrain_colors = {
                            "grass": (76, 153, 0), "open": (200, 200, 180),
                            "road": (128, 128, 128), "woods": (34, 100, 34),
                            "forest": (34, 100, 34), "water": (65, 105, 225),
                            "building": (160, 140, 120), "building_enterable": (160, 140, 120),
                            "building_solid": (100, 80, 60), "hedge": (80, 120, 40),
                            "bridge": (139, 119, 101), "dirt": (154, 140, 125),
                            "rough": (154, 140, 125), "trench": (90, 75, 60),
                            "crater": (90, 75, 60), "wall": (105, 105, 105),
                            "shallow": (100, 149, 237), "swamp": (60, 80, 50),
                        }
                        for r, row in enumerate(tiles):
                            for c, tile in enumerate(row):
                                terrain_name = tile if isinstance(tile, str) else str(tile)
                                color = terrain_colors.get(terrain_name.lower(), (76, 153, 0))
                                rx = x + int(c * tile_w)
                                ry = y + int(r * tile_h)
                                rw = int((c + 1) * tile_w) - int(c * tile_w)
                                rh = int((r + 1) * tile_h) - int(r * tile_h)
                                draw.rect(surface, color, Rect(rx, ry, rw, rh))
                        return
        except Exception:
            pass

        # Fallback: placeholder grid
        grid_size = 10
        tile_w = size / grid_size
        tile_h = size / grid_size
        for r in range(grid_size):
            for c in range(grid_size):
                color = (76, 153, 0) if (r + c) % 3 != 0 else (128, 128, 128)
                rx = x + int(c * tile_w)
                ry = y + int(r * tile_h)
                rw = int((c + 1) * tile_w) - int(c * tile_w)
                rh = int((r + 1) * tile_h) - int(r * tile_h)
                draw.rect(surface, color, Rect(rx, ry, rw, rh))

    def cleanup(self) -> None:
        """Clean up resources."""
        pass
