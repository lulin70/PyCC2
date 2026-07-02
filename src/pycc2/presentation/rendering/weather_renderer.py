"""Enhanced Weather Renderer — particle systems for rain, fog, snow, and overlays."""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame


from pycc2.domain.systems.weather_effects import WeatherState, WeatherType


class WeatherRenderer:
    """天气渲染器，以粒子系统呈现雨、雪、雾等天气效果。"""

    RAIN_DROP_COUNT = 80
    SNOW_FLAKE_COUNT = 60
    FOG_ALPHA_BASE = 100
    NIGHT_DARKEN_ALPHA = 140
    MAX_PARTICLES = 1000

    def __init__(self, screen_width: int, screen_height: int):
        """初始化天气渲染器，按屏幕尺寸创建雨滴与雪花粒子。"""
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._rain_drops: list[dict] = []
        self._snow_flakes: list[dict] = []
        self._dark_surf: pygame.Surface | None = None
        self._fog_surf: pygame.Surface | None = None
        self._weather_surf_size: tuple[int, int] = (0, 0)
        self._init_rain()
        self._init_snow()

    def _init_rain(self) -> None:
        self._rain_drops = [
            {
                "x": random.randint(0, self.screen_width),
                "y": random.randint(-self.screen_height, 0),
                "speed": random.uniform(8, 15),
                "length": random.randint(8, 18),
                "alpha": random.randint(40, 100),
            }
            for _ in range(self.RAIN_DROP_COUNT)
        ]

    def _init_snow(self) -> None:
        self._snow_flakes = [
            {
                "x": random.uniform(0, self.screen_width),
                "y": random.uniform(-self.screen_height, 0),
                "speed": random.uniform(1, 3),
                "size": random.uniform(1, 4),
                "drift": random.uniform(-1, 1),
                "alpha": random.randint(150, 255),
                "wobble_phase": random.uniform(0, 2 * math.pi),
                "wobble_speed": random.uniform(1, 3),
            }
            for _ in range(self.SNOW_FLAKE_COUNT)
        ]

    def update(self, dt: float = 1.0 / 60.0) -> None:
        """Update internal state."""
        for drop in self._rain_drops:
            drop["y"] += drop["speed"]
            drop["x"] += 1
            if drop["y"] > self.screen_height:
                drop["y"] = random.randint(-50, 0)
                drop["x"] = random.randint(0, self.screen_width)

        for flake in self._snow_flakes:
            flake["wobble_phase"] += flake["wobble_speed"] * dt
            wobble = math.sin(flake["wobble_phase"]) * 0.5
            flake["x"] += (flake["drift"] + wobble) * dt * 60
            flake["y"] += flake["speed"] * dt * 60
            if flake["y"] > self.screen_height:
                flake["y"] = random.randint(-50, 0)
                flake["x"] = random.uniform(0, self.screen_width)

    def render(
        self,
        screen,
        weather_state: WeatherState,
        time_of_day=None,
        camera_offset_x: int = 0,
        camera_offset_y: int = 0,
    ) -> None:
        """Render to the screen."""
        import pygame

        weather = weather_state.weather_type
        intensity = weather_state.intensity

        if time_of_day is not None:
            from pycc2.domain.systems.environment import TimeOfDay

            if time_of_day in (TimeOfDay.NIGHT, TimeOfDay.DAWN, TimeOfDay.DUSK):
                # Lazy-init or resize dark surface
                cur_size = (self.screen_width, self.screen_height)
                if self._dark_surf is None or self._weather_surf_size != cur_size:
                    self._dark_surf = pygame.Surface(cur_size, pygame.SRCALPHA)
                    self._fog_surf = pygame.Surface(cur_size, pygame.SRCALPHA)
                    self._weather_surf_size = cur_size
                alpha = self.NIGHT_DARKEN_ALPHA
                if time_of_day in (TimeOfDay.DAWN, TimeOfDay.DUSK):
                    alpha = 70
                self._dark_surf.fill((0, 0, 15, alpha))
                screen.blit(self._dark_surf, (0, 0))

        if weather == WeatherType.RAIN:
            self._render_rain(screen, intensity, camera_offset_x, camera_offset_y)
        elif weather == WeatherType.FOG:
            self._render_fog(screen, intensity)
        elif weather == WeatherType.SNOW:
            self._render_snow(screen, intensity, camera_offset_x, camera_offset_y)

    def _render_rain(self, screen, intensity: float, cam_x: int, cam_y: int) -> None:
        import pygame

        active_drops = self._rain_drops[: int(self.RAIN_DROP_COUNT * intensity)]
        for drop in active_drops:
            sx = int(drop["x"] - cam_x * 0.3)
            sy = int(drop["y"] - cam_y * 0.3)
            color = (180, 200, 220, int(drop["alpha"] * intensity))
            start_pos = (sx, sy)
            end_pos = (sx + 1, sy + drop["length"])
            pygame.draw.line(screen, color, start_pos, end_pos, 1)

    def _render_fog(self, screen, intensity: float) -> None:
        import pygame

        # Lazy-init or resize fog surface
        cur_size = (self.screen_width, self.screen_height)
        if self._fog_surf is None or self._weather_surf_size != cur_size:
            self._fog_surf = pygame.Surface(cur_size, pygame.SRCALPHA)
            self._dark_surf = pygame.Surface(cur_size, pygame.SRCALPHA)
            self._weather_surf_size = cur_size
        self._fog_surf.fill((0, 0, 0, 0))
        base_alpha = int(self.FOG_ALPHA_BASE * intensity)
        self._fog_surf.fill((200, 200, 210, base_alpha))
        noise_count = int(20 * intensity)
        for _ in range(noise_count):
            fx = random.randint(0, self.screen_width)
            fy = random.randint(0, self.screen_height)
            fr = random.randint(50, 150)
            pygame.draw.circle(self._fog_surf, (220, 220, 230, 30), (fx, fy), fr)
        screen.blit(self._fog_surf, (0, 0))

    def _render_snow(self, screen, intensity: float, cam_x: int, cam_y: int) -> None:
        import pygame

        active_flakes = self._snow_flakes[: int(self.SNOW_FLAKE_COUNT * intensity)]
        for flake in active_flakes:
            sx = int(flake["x"] - cam_x * 0.2)
            sy = int(flake["y"] - cam_y * 0.2)
            size = int(flake["size"])
            alpha = int(flake["alpha"] * intensity)
            color = (255, 255, 255, alpha)
            if size <= 2:
                screen.set_at((sx, sy), color[:3])
            else:
                pygame.draw.circle(screen, color[:3], (sx, sy), size)

    def resize(self, width: int, height: int) -> None:
        """Handle screen resize and rebuild rain surfaces."""
        self.screen_width = width
        self.screen_height = height
        self._init_rain()
        self._init_snow()

    @property
    def particle_count(self) -> int:
        """Get the particle count."""
        return len(self._rain_drops) + len(self._snow_flakes)
