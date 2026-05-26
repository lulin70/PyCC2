"""CC2-style Radial Command Menu.

Appears when right-click-holding on a selected unit.
7 commands arranged in a circle around the unit.
"""

from __future__ import annotations

import math

import pygame
from enum import Enum, auto


class RadialCommand(Enum):
    MOVE = auto()
    MOVE_FAST = auto()
    SNEAK = auto()
    FIRE = auto()
    SMOKE = auto()
    DEFEND = auto()
    HIDE = auto()


# Command display properties
COMMAND_PROPS = {
    RadialCommand.MOVE:      {"label": "MOVE",  "hotkey": "Z", "color": (100, 200, 100)},
    RadialCommand.MOVE_FAST: {"label": "FAST",  "hotkey": "X", "color": (200, 200, 100)},
    RadialCommand.SNEAK:     {"label": "SNEAK", "hotkey": "S", "color": (100, 150, 200)},
    RadialCommand.FIRE:      {"label": "FIRE",  "hotkey": "C", "color": (200, 100, 100)},
    RadialCommand.SMOKE:     {"label": "SMOKE", "hotkey": "V", "color": (180, 180, 180)},
    RadialCommand.DEFEND:    {"label": "DEFEND","hotkey": "D", "color": (150, 150, 200)},
    RadialCommand.HIDE:      {"label": "HIDE",  "hotkey": "H", "color": (120, 120, 120)},
}

# Commands arranged in order around the circle (clockwise from top)
COMMAND_ORDER = [
    RadialCommand.MOVE,
    RadialCommand.MOVE_FAST,
    RadialCommand.SNEAK,
    RadialCommand.FIRE,
    RadialCommand.SMOKE,
    RadialCommand.DEFEND,
    RadialCommand.HIDE,
]


class RadialMenu:
    """CC2-style radial command menu that appears around a selected unit."""

    def __init__(self, radius: int = 60, item_radius: int = 22):
        self._center: tuple[int, int] | None = None
        self._visible: bool = False
        self._hovered_command: RadialCommand | None = None
        self._radius = radius  # Distance from center to item centers
        self._item_radius = item_radius  # Size of each command circle
        self._font: pygame.font.Font | None = None
        self._available_commands: list[RadialCommand] = list(COMMAND_ORDER)

    def show(self, center: tuple[int, int], available_commands: list[RadialCommand] | None = None) -> None:
        """Show the radial menu at the given screen position."""
        self._center = center
        self._visible = True
        self._hovered_command = None
        self._available_commands = available_commands or list(COMMAND_ORDER)
        if self._font is None:
            self._font = pygame.font.SysFont("arial", 11, bold=True)

    def hide(self) -> None:
        """Hide the radial menu."""
        self._visible = False
        self._center = None
        self._hovered_command = None

    @property
    def is_visible(self) -> bool:
        return self._visible

    @property
    def hovered_command(self) -> RadialCommand | None:
        return self._hovered_command

    def update_hover(self, mouse_pos: tuple[int, int]) -> RadialCommand | None:
        """Update which command is hovered based on mouse position.

        Returns the hovered command, or None if mouse is in the center (cancel).
        """
        if not self._visible or self._center is None:
            return None

        mx, my = mouse_pos
        cx, cy = self._center
        dx = mx - cx
        dy = my - cy
        dist = math.sqrt(dx * dx + dy * dy)

        # If mouse is very close to center, no command selected
        if dist < 15:
            self._hovered_command = None
            return None

        # Calculate angle (0 = up, clockwise)
        angle = math.atan2(dx, -dy)  # Note: dx first for clockwise
        if angle < 0:
            angle += 2 * math.pi

        # Determine which sector the mouse is in
        n = len(self._available_commands)
        sector_angle = 2 * math.pi / n

        # Check if mouse is far enough to select
        if dist < self._radius - self._item_radius:
            self._hovered_command = None
            return None

        sector_idx = int(angle / sector_angle) % n
        self._hovered_command = self._available_commands[sector_idx]
        return self._hovered_command

    def render(self, surface: pygame.Surface) -> None:
        """Render the radial menu on the given surface."""
        if not self._visible or self._center is None:
            return

        cx, cy = self._center
        n = len(self._available_commands)

        for i, cmd in enumerate(self._available_commands):
            angle = (2 * math.pi * i / n) - math.pi / 2  # Start from top
            ix = cx + int(self._radius * math.cos(angle))
            iy = cy + int(self._radius * math.sin(angle))

            props = COMMAND_PROPS[cmd]
            is_hovered = (cmd == self._hovered_command)

            # Draw command circle
            color = props["color"]
            if is_hovered:
                # Brighten when hovered
                color = tuple(min(255, c + 60) for c in color)
                pygame.draw.circle(surface, color, (ix, iy), self._item_radius + 3)
                pygame.draw.circle(surface, (255, 255, 255), (ix, iy), self._item_radius + 3, 2)
            else:
                pygame.draw.circle(surface, (40, 40, 30), (ix, iy), self._item_radius)
                pygame.draw.circle(surface, color, (ix, iy), self._item_radius, 2)

            # Draw label
            if self._font:
                text_surf = self._font.render(props["label"], True, (255, 255, 255) if is_hovered else (200, 200, 200))
                text_rect = text_surf.get_rect(center=(ix, iy))
                surface.blit(text_surf, text_rect)

        # Draw center cancel indicator
        pygame.draw.circle(surface, (60, 60, 50), (cx, cy), 12)
        pygame.draw.circle(surface, (120, 120, 100), (cx, cy), 12, 1)
