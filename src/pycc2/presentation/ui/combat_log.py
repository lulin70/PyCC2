"""Combat Event Log System - Real-time combat event display."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import pygame


class CombatEventType(Enum):
    """Types of combat events for logging."""

    ATTACK = auto()
    HIT = auto()
    KILL = auto()
    MISS = auto()
    SUPPRESSION = auto()
    MORALE_CHANGE = auto()
    MOVEMENT = auto()
    STATUS_CHANGE = auto()
    SPECIAL = auto()


@dataclass
class CombatEvent:
    """A single combat event entry."""

    timestamp: float
    event_type: CombatEventType
    source_name: str = ""
    target_name: str = ""
    details: str = ""
    position: tuple[int, int] | None = None
    damage: int = 0
    morale_change: float = 0.0

    def format_short(self) -> str:
        """Format event for minimal log display."""
        t = time.strftime("%M:%S", time.localtime(self.timestamp))

        type_icons = {
            CombatEventType.ATTACK: "→",
            CombatEventType.HIT: "•",
            CombatEventType.KILL: "†",
            CombatEventType.MISS: "○",
            CombatEventType.SUPPRESSION: "▽",
            CombatEventType.MORALE_CHANGE: "◇",
            CombatEventType.MOVEMENT: "»",
            CombatEventType.STATUS_CHANGE: "*",
            CombatEventType.SPECIAL: "!",
        }

        type_icons.get(self.event_type, "?")

        if self.event_type == CombatEventType.KILL:
            return f"[{t}] {self.source_name} → {self.target_name} (-{self.damage} KIA)"
        elif self.event_type == CombatEventType.HIT:
            return f"[{t}] {self.source_name} hits {self.target_name} (-{self.damage})"
        elif self.event_type == CombatEventType.MISS:
            return f"[{t}] {self.source_name} misses {self.target_name}"
        elif self.event_type == CombatEventType.SUPPRESSION:
            return f"[{t}] {self.target_name} suppressed"
        else:
            return f"[{t}] {self.details or f'{self.source_name}: {self.event_type.name}'}"

    def format_full(self) -> str:
        """Format event for detailed log view."""
        t = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        lines = [
            f"[{t}] {self.event_type.name}",
            f"  Source: {self.source_name}",
            f"  Target: {self.target_name}",
        ]

        if self.damage > 0:
            lines.append(f"  Damage: {self.damage}")
        if self.morale_change != 0.0:
            lines.append(f"  Morale: {self.morale_change:+.0f}")
        if self.position:
            lines.append(f"  Position: {self.position}")
        if self.details:
            lines.append(f"  Details: {self.details}")

        return "\n".join(lines)


@dataclass
class CombatLog:
    """Real-time combat event logging and display system.

    Features:
    - Scrollable event list in corner of screen
    - Color-coded by event type
    - Expandable detailed view
    - Auto-scroll to latest events
    - Max 100 events retained

    CC2 Behavior:
    - Shows recent combat activity at a glance
    - Helps player track battle progress
    - Different colors for different event types
    """

    MAX_VISIBLE: int = 8
    MAX_EVENTS: int = 100
    events: list[CombatEvent] = field(default_factory=list)
    scroll_offset: int = 0
    expanded: bool = False
    # Surface cache – lazy init
    _panel_cache: pygame.Surface | None = field(default=None, init=False, repr=False)
    _panel_cache_size: tuple[int, int] | None = field(default=None, init=False, repr=False)

    def add_event(self, event: CombatEvent) -> None:
        """Add new event and auto-scroll to latest."""
        self.events.append(event)

        if len(self.events) > self.MAX_EVENTS:
            self.events = self.events[-self.MAX_EVENTS :]

        if not self.expanded:
            max_scroll = max(0, len(self.events) - self.MAX_VISIBLE)
            self.scroll_offset = max_scroll

    def create_event(
        self,
        event_type: CombatEventType,
        source_name: str = "",
        target_name: str = "",
        details: str = "",
        damage: int = 0,
        morale_change: float = 0.0,
        position: tuple[int, int] | None = None,
    ) -> CombatEvent:
        """Create and add a new combat event."""
        event = CombatEvent(
            timestamp=time.time(),
            event_type=event_type,
            source_name=source_name,
            target_name=target_name,
            details=details,
            damage=damage,
            morale_change=morale_change,
            position=position,
        )
        self.add_event(event)
        return event

    def get_recent_events(self, count: int | None = None) -> list[CombatEvent]:
        """Get most recent events."""
        n = count or self.MAX_VISIBLE
        return self.events[-n:]

    def get_visible_events(self) -> list[CombatEvent]:
        """Get events currently visible based on scroll position."""
        if self.expanded:
            start = self.scroll_offset
            end = start + self.MAX_VISIBLE * 3  # More when expanded
            return self.events[start:end]
        else:
            return self.get_recent_events(self.MAX_VISIBLE)

    def render_minimal(self, surface, position: tuple[int, int]) -> None:
        """Render compact scrolling log overlay.

        Args:
            surface: Pygame surface to draw on
            position: Screen position (x, y) for top-left corner

        """
        try:
            import pygame

            visible = self.get_visible_events()

            font = pygame.font.SysFont("arial", 11)
            line_height = 16
            padding = 5

            y_offset = 0
            for event in reversed(visible[-self.MAX_VISIBLE :]):
                text = event.format_short()
                color = self._get_event_color(event.event_type)

                text_surf = font.render(text, True, color)
                surface.blit(text_surf, (position[0] + padding, position[1] + y_offset))
                y_offset += line_height

        except (pygame.error, ValueError, TypeError) as e:
            logging.debug("Combat log rendering failed: %s", e)

    def render_fullscreen(self, surface, screen_size: tuple[int, int]) -> None:
        """Render expanded full log panel.

        Semi-transparent panel covering right half of screen.
        """
        try:
            import pygame

            panel_width = screen_size[0] // 2
            panel_height = screen_size[1]
            x = screen_size[0] - panel_width

            font = pygame.font.SysFont("arial", 12)
            line_height = 18
            padding = 10

            # Panel – reuse cached surface
            panel_size = (panel_width, panel_height)
            if self._panel_cache is None or self._panel_cache_size != panel_size:
                self._panel_cache = pygame.Surface(panel_size, pygame.SRCALPHA)
                self._panel_cache_size = panel_size
            panel = self._panel_cache
            panel.fill((0, 0, 0, 0))
            pygame.draw.rect(panel, (20, 20, 30, 230), (0, 0, panel_width, panel_height))
            pygame.draw.rect(panel, (100, 100, 120), (0, 0, panel_width, panel_height), width=1)

            title = font.render("COMBAT LOG", True, (255, 215, 0))
            panel.blit(title, (padding, padding))

            y = padding + 30
            visible_events = self.events[self.scroll_offset : self.scroll_offset + 25]

            for event in visible_events:
                text = event.format_full()
                color = self._get_event_color(event.event_type)

                for line in text.split("\n"):
                    if y < panel_height - padding:
                        line_surf = font.render(line, True, color)
                        panel.blit(line_surf, (padding, y))
                        y += line_height

            surface.blit(panel, (x, 0))

        except (pygame.error, ValueError, TypeError) as e:
            logging.debug("Combat log fullscreen rendering failed: %s", e)

    @staticmethod
    def _get_event_color(event_type: CombatEventType) -> tuple[int, int, int]:
        """Get display color for event type."""
        colors = {
            CombatEventType.KILL: (255, 80, 80),
            CombatEventType.HIT: (255, 180, 50),
            CombatEventType.ATTACK: (255, 220, 100),
            CombatEventType.MISS: (150, 150, 150),
            CombatEventType.SUPPRESSION: (255, 100, 255),
            CombatEventType.MORALE_CHANGE: (100, 200, 255),
            CombatEventType.MOVEMENT: (150, 200, 150),
            CombatEventType.STATUS_CHANGE: (200, 200, 100),
            CombatEventType.SPECIAL: (255, 215, 0),
        }
        return colors.get(event_type, (200, 200, 200))

    def clear(self) -> None:
        """Clear all events."""
        self.events = []
        self.scroll_offset = 0

    @property
    def event_count(self) -> int:
        return len(self.events)

    def scroll_up(self, amount: int = 1) -> None:
        """Scroll log up (show older events)."""
        self.scroll_offset = max(0, self.scroll_offset - amount)

    def scroll_down(self, amount: int = 1) -> None:
        """Scroll log down (show newer events)."""
        max_scroll = max(0, len(self.events) - self.MAX_VISIBLE)
        self.scroll_offset = min(max_scroll, self.scroll_offset + amount)

    def toggle_expanded(self) -> None:
        """Toggle between minimal and expanded view."""
        self.expanded = not self.expanded
        if self.expanded:
            self.scroll_offset = 0
