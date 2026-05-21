"""
Weather Rendering System — overlays rain, fog, darkness effects.
"""

from __future__ import annotations
import math
import random
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame

from pycc2.domain.systems.environment import WeatherCondition, TimeOfDay


class WeatherRenderer:
    RAIN_DROP_COUNT = 80
    FOG_ALPHA_BASE = 100
    NIGHT_DARKEN_ALPHA = 140
    
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._rain_drops: list[dict] = []
        self._init_rain()
    
    def _init_rain(self) -> None:
        import random
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
    
    def update(self) -> None:
        for drop in self._rain_drops:
            drop["y"] += drop["speed"]
            drop["x"] += 1  # Slight wind drift
            if drop["y"] > self.screen_height:
                drop["y"] = random.randint(-50, 0)
                drop["x"] = random.randint(0, self.screen_width)
    
    def render(
        self, 
        screen,  # pygame.Surface
        weather: WeatherCondition,
        time_of_day: TimeOfDay,
        camera_offset_x: int = 0,
        camera_offset_y: int = 0,
    ) -> None:
        import pygame
        
        # Night darkness overlay
        if time_of_day in (TimeOfDay.NIGHT, TimeOfDay.DAWN, TimeOfDay.DUSK):
            dark_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            alpha = self.NIGHT_DARKEN_ALPHA
            if time_of_day == TimeOfDay.DAWN or time_of_day == TimeOfDay.DUSK:
                alpha = 70  # Twilight is lighter
            dark_surf.fill((0, 0, 15, alpha))
            screen.blit(dark_surf, (0, 0))
        
        # Rain effect
        if weather == WeatherCondition.RAIN:
            for drop in self._rain_drops:
                sx = int(drop["x"] - camera_offset_x * 0.3)  # Parallax
                sy = int(drop["y"] - camera_offset_y * 0.3)
                color = (180, 200, 220, drop["alpha"])
                start_pos = (sx, sy)
                end_pos = (sx + 1, sy + drop["length"])
                pygame.draw.line(screen, color, start_pos, end_pos, 1)
        
        # Fog effect
        elif weather == WeatherCondition.FOG:
            fog_surf = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            fog_surf.fill((200, 200, 210, self.FOG_ALPHA_BASE))
            # Add some noise variation
            for _ in range(20):
                fx = np.random.randint(0, self.screen_width)
                fy = np.random.randint(0, self.screen_height)
                fr = np.random.randint(50, 150)
                pygame.draw.circle(fog_surf, (220, 220, 230, 30), (fx, fy), fr)
            screen.blit(fog_surf, (0, 0))
