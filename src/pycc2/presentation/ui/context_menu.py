"""Context Menu - CC2-style right-click command menu."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

logger = logging.getLogger(__name__)

import pygame

if TYPE_CHECKING:
    pass


class ContextAction(Enum):
    """Available context menu actions."""
    MOVE = auto()
    ATTACK = auto()
    STOP = auto()
    SMOKE = auto()
    HIDE = auto()
    SNEAK = auto()
    CANCEL = auto()


@dataclass(slots=True)
class MenuItem:
    """Single menu item with icon and shortcut hint."""
    action: ContextAction
    label: str
    shortcut: str = ""
    icon_char: str = ""
    enabled: bool = True


class ContextMenu:
    """
    CC2-style right-click context menu.

    Features:
    - Appears on right-click near cursor
    - Shows Move/Attack/Stop/Smoke/Hide/Sneak/Cancel options
    - Each item has icon and keyboard shortcut hint
    - Closes on ESC or click outside
    - Executes callback when item selected
    """

    BG_COLOR: tuple[int, int, int, int] = (40, 40, 48, 240)
    BORDER_COLOR: tuple[int, int, int] = (120, 120, 130)
    ITEM_COLOR: tuple[int, int, int] = (220, 220, 220)
    HOVER_COLOR: tuple[int, int, int] = (255, 255, 255)
    DISABLED_COLOR: tuple[int, int, int] = (100, 100, 100)
    SHORTCUT_COLOR: tuple[int, int, int] = (140, 140, 150)
    ITEM_HEIGHT: int = 28
    ITEM_PADDING: int = 8
    FONT_SIZE: int = 14
    ICON_WIDTH: int = 24

    def __init__(self) -> None:
        self._visible = False
        self._position: tuple[int, int] = (0, 0)
        self._hovered_index: int = -1
        self._items: list[MenuItem] = []
        self._on_action: Callable[[ContextAction, tuple[int, int]], None] | None = None
        self._surface: pygame.Surface | None = None
        self._rect: pygame.Rect | None = None
        self._font: pygame.font.Font | None = None
        self._init_items()

    def _init_items(self) -> None:
        """Initialize default menu items in CC2 order."""
        self._items = [
            MenuItem(ContextAction.MOVE, "Move", "Z", "→"),
            MenuItem(ContextAction.ATTACK, "Attack", "C", "✶"),
            MenuItem(ContextAction.STOP, "Stop", "D", "■"),
            MenuItem(ContextAction.SMOKE, "Smoke", "V", "☁"),
            MenuItem(ContextAction.HIDE, "Hide", "H", "▽"),
            MenuItem(ContextAction.SNEAK, "Sneak", "S", "◇"),
            MenuItem(ContextAction.CANCEL, "Cancel", "Esc", "✕"),
        ]

    def show(self, position: tuple[int, int],
             on_action: Callable[[ContextAction, tuple[int, int]], None],
             enabled_actions: set[ContextAction] | None = None) -> None:
        """
        Show context menu at position.

        Args:
            position: Screen position (x, y)
            on_action: Callback when action selected
            enabled_actions: Set of actions to enable (all if None)
        """
        self._position = position
        self._on_action = on_action
        self._visible = True
        self._hovered_index = -1

        if enabled_actions is not None:
            for item in self._items:
                item.enabled = item.action in enabled_actions
        else:
            for item in self._items:
                item.enabled = True

        self._build_surface()

    def hide(self) -> None:
        """Hide the menu."""
        self._visible = False
        self._hovered_index = -1

    @property
    def visible(self) -> bool:
        return self._visible

    def _build_surface(self) -> None:
        """Build the menu surface with all items."""
        try:
            self._font = pygame.font.SysFont("arial", self.FONT_SIZE)
        except Exception as e:
            logging.debug(f"Context menu font fallback: {e}")
            self._font = pygame.font.Font(None, self.FONT_SIZE)

        width = 180
        height = len(self._items) * self.ITEM_HEIGHT + 8

        self._surface = pygame.Surface((width, height), pygame.SRCALPHA)
        self._surface.fill(self.BG_COLOR)

        pygame.draw.rect(
            self._surface,
            self.BORDER_COLOR,
            self._surface.get_rect(),
            width=1,
        )

        for i, item in enumerate(self._items):
            y = 4 + i * self.ITEM_HEIGHT
            item_rect = pygame.Rect(4, y, width - 8, self.ITEM_HEIGHT - 2)

            color = self.HOVER_COLOR if i == self._hovered_index else (
                self.ITEM_COLOR if item.enabled else self.DISABLED_COLOR
            )

            if i == self._hovered_index and item.enabled:
                pygame.draw.rect(
                    self._surface,
                    (70, 70, 90),
                    item_rect,
                    border_radius=3,
                )

            icon_text = f"{item.icon_char}"
            icon_surface = self._font.render(icon_text, True, color)
            self._surface.blit(icon_surface, (item_rect.x + 4, y + 4))

            label_surface = self._font.render(item.label, True, color)
            self._surface.blit(label_surface, (item_rect.x + self.ICON_WIDTH + 4, y + 4))

            if item.shortcut:
                shortcut_surface = self._font.render(
                    f"[{item.shortcut}]",
                    True,
                    self.SHORTCUT_COLOR if item.enabled else self.DISABLED_COLOR,
                )
                self._surface.blit(
                    shortcut_surface,
                    (width - shortcut_surface.get_width() - 12, y + 4),
                )

        self._rect = pygame.Rect(
            self._position[0],
            self._position[1],
            width,
            height,
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle input event for context menu.

        Returns:
            True if event was consumed
        """
        if not self._visible:
            return False

        if event.type == pygame.MOUSEMOTION:
            return self._handle_mouse_move(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                return self._handle_click(event.pos)
            elif event.button == 3:
                self.hide()
                return True

        elif event.type == pygame.KEYDOWN:
            return self._handle_key(event.key)

        return False

    def _handle_mouse_move(self, pos: tuple[int, int]) -> bool:
        if not self._rect:
            return False

        if self._rect.collidepoint(pos):
            index = (pos[1] - self._position[1] - 4) // self.ITEM_HEIGHT
            if 0 <= index < len(self._items):
                if index != self._hovered_index:
                    self._hovered_index = index
                    self._build_surface()
            return True
        else:
            if self._hovered_index != -1:
                self._hovered_index = -1
                self._build_surface()
            return False

    def _handle_click(self, pos: tuple[int, int]) -> bool:
        if not self._rect:
            self.hide()
            return True

        if self._rect.collidepoint(pos):
            index = (pos[1] - self._position[1] - 4) // self.ITEM_HEIGHT
            if 0 <= index < len(self._items):
                item = self._items[index]
                if item.enabled and self._on_action:
                    self._on_action(item.action, self._position)
            self.hide()
            return True
        else:
            self.hide()
            return True

    def _handle_key(self, key: int) -> bool:
        key_map = {
            pygame.K_z: ContextAction.MOVE,
            pygame.K_c: ContextAction.ATTACK,
            pygame.K_d: ContextAction.STOP,
            pygame.K_v: ContextAction.SMOKE,
            pygame.K_h: ContextAction.HIDE,
            pygame.K_s: ContextAction.SNEAK,
            pygame.K_ESCAPE: ContextAction.CANCEL,
        }

        action = key_map.get(key)
        if action == ContextAction.CANCEL:
            self.hide()
            return True
        elif action is not None:
            for item in self._items:
                if item.action == action and item.enabled:
                    if self._on_action:
                        self._on_action(action, self._position)
                    self.hide()
                    return True
        return False

    def draw(self, screen: pygame.Surface) -> None:
        """Draw the context menu on screen."""
        if not self._visible or not self._surface or not self._rect:
            return

        screen.blit(self._surface, self._rect.topleft)

    def get_enabled_actions(self, unit=None) -> set[ContextAction]:
        """
        Get set of actions that should be enabled for current context.

        Args:
            unit: Currently selected unit (if any)

        Returns:
            Set of enabled ContextAction values
        """
        always_enabled = {
            ContextAction.STOP,
            ContextAction.CANCEL,
        }

        if unit is None:
            return always_enabled

        unit_actions = {ContextAction.MOVE, ContextAction.ATTACK}

        if hasattr(unit, 'can_use_smoke') and unit.can_use_smoke:
            unit_actions.add(ContextAction.SMOKE)

        if hasattr(unit, 'can_hide') and unit.can_hide:
            unit_actions.add(ContextAction.HIDE)

        if hasattr(unit, 'can_sneak') and unit.can_sneak:
            unit_actions.add(ContextAction.SNEAK)

        return always_enabled | unit_actions
