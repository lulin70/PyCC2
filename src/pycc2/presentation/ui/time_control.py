"""Time Control — pause, slow-mo, normal, fast-forward game speed."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    import pygame


class _SpeedConfig(TypedDict):
    label: str
    ups_mult: float
    color: tuple[int, int, int]


class TimeSpeed(Enum):
    PAUSED = auto()
    SLOW = auto()
    NORMAL = auto()
    FAST = auto()
    VERY_FAST = auto()


TIME_SPEED_CONFIG: dict[TimeSpeed, _SpeedConfig] = {
    TimeSpeed.PAUSED: {"label": "⏸ PAUSED", "ups_mult": 0.0, "color": (200, 180, 50)},
    TimeSpeed.SLOW: {"label": "▶ SLOW 0.5x", "ups_mult": 0.5, "color": (100, 160, 220)},
    TimeSpeed.NORMAL: {"label": "▶▶ NORMAL 1x", "ups_mult": 1.0, "color": (100, 200, 100)},
    TimeSpeed.FAST: {"label": "▶▶▶ FAST 2x", "ups_mult": 2.0, "color": (220, 180, 80)},
    TimeSpeed.VERY_FAST: {"label": "▶▶▶▶ 4x", "ups_mult": 4.0, "color": (220, 100, 80)},
}

SPEED_ORDER = [
    TimeSpeed.PAUSED,
    TimeSpeed.SLOW,
    TimeSpeed.NORMAL,
    TimeSpeed.FAST,
    TimeSpeed.VERY_FAST,
]

HOTKEY_SPEED = {
    "pause": TimeSpeed.PAUSED,
    "slow": TimeSpeed.SLOW,
    "normal": TimeSpeed.NORMAL,
    "fast": TimeSpeed.FAST,
}


@dataclass
class TimeControlConfig:
    x: int = 10
    y: int = 560
    button_width: int = 95
    button_height: int = 28
    spacing: int = 4
    bg_alpha: int = 200


class TimeControlUI:
    def __init__(self, config: TimeControlConfig | None = None):
        """Initialize the TimeControlUI."""
        self.config = config or TimeControlConfig()
        self._current_speed: TimeSpeed = TimeSpeed.NORMAL
        self._button_rects: dict[TimeSpeed, pygame.Rect] = {}
        self._button_surf: pygame.Surface | None = None
        self._button_surf_size: tuple[int, int] = (0, 0)

    @property
    def current_speed(self) -> TimeSpeed:
        """Get the current speed."""
        return self._current_speed

    @property
    def speed_multiplier(self) -> float:
        """Get the speed multiplier."""
        return TIME_SPEED_CONFIG[self._current_speed]["ups_mult"]

    @property
    def is_paused(self) -> bool:
        """Get the is paused."""
        return self._current_speed == TimeSpeed.PAUSED

    def set_speed(self, speed: TimeSpeed) -> None:
        """Set the speed."""
        if speed in TIME_SPEED_CONFIG:
            self._current_speed = speed

    def toggle_pause(self) -> None:
        """Toggle pause."""
        if self._current_speed == TimeSpeed.PAUSED:
            self._current_speed = TimeSpeed.NORMAL
        else:
            self._current_speed = TimeSpeed.PAUSED

    def speed_up(self) -> TimeSpeed:
        """Speed up."""
        idx = SPEED_ORDER.index(self._current_speed)
        if idx < len(SPEED_ORDER) - 1:
            self._current_speed = SPEED_ORDER[idx + 1]
        return self._current_speed

    def speed_down(self) -> TimeSpeed:
        """Speed down."""
        idx = SPEED_ORDER.index(self._current_speed)
        if idx > 0:
            self._current_speed = SPEED_ORDER[idx - 1]
        return self._current_speed

    def handle_key(self, key: int) -> bool:
        """Handle key."""
        import pygame

        if key == pygame.K_SPACE:
            self.toggle_pause()
            return True
        elif key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
            self.speed_up()
            return True
        elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self.speed_down()
            return True
        return False

    def render(
        self, screen: pygame.Surface, font=None, tick: int = 0, fps: float = 0.0
    ) -> list[dict]:
        """Render to the screen."""
        import pygame

        cfg = self.config
        clickable = []

        for i, speed in enumerate(SPEED_ORDER):
            info = TIME_SPEED_CONFIG[speed]
            bx = cfg.x + i * (cfg.button_width + cfg.spacing)
            by = cfg.y
            rect = pygame.Rect(bx, by, cfg.button_width, cfg.button_height)

            is_active = speed == self._current_speed
            bg_color = (*info["color"], 220) if is_active else (50, 55, 65, cfg.bg_alpha)
            border_color = (255, 255, 255) if is_active else (80, 85, 95)

            # Lazy-init or resize button surface
            btn_size = (cfg.button_width, cfg.button_height)
            if self._button_surf is None or self._button_surf_size != btn_size:
                self._button_surf = pygame.Surface(btn_size, pygame.SRCALPHA)
                self._button_surf_size = btn_size
            self._button_surf.fill((0, 0, 0, 0))
            self._button_surf.fill(bg_color)
            pygame.draw.rect(
                self._button_surf,
                border_color,
                (0, 0, cfg.button_width, cfg.button_height),
                1,
                border_radius=4,
            )

            if font:
                label = font.render(info["label"], True, (230, 230, 230))
                self._button_surf.blit(label, (cfg.button_width // 2 - label.get_width() // 2, 5))

            screen.blit(self._button_surf, (bx, by))
            self._button_rects[speed] = rect
            clickable.append({"speed": speed, "rect": rect})

        if font:
            mult = self.speed_multiplier
            if mult > 0:
                tick_info = f"Tick:{tick} | {fps:.0f}FPS | {mult:.1f}x"
            else:
                tick_info = f"Tick:{tick} (PAUSED)"
            info_surf = font.render(tick_info, True, (150, 150, 160))
            screen.blit(
                info_surf,
                (cfg.x + len(SPEED_ORDER) * (cfg.button_width + cfg.spacing) + 20, cfg.y + 7),
            )

        return clickable

    def handle_click(self, x: int, y: int) -> bool:
        """Handle click."""
        for speed, rect in self._button_rects.items():
            if rect.collidepoint(x, y):
                self._current_speed = speed
                return True
        return False
