"""Weather effects: EnhancedWeatherSystem with rain, snow, and fog."""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from enum import Enum

import pygame
from pygame import Surface

logger = logging.getLogger(__name__)


class WeatherType(Enum):
    """天气类型"""

    CLEAR = "clear"
    RAIN = "rain"
    SNOW = "snow"
    FOG = "fog"


@dataclass
class WeatherParticle:
    """天气粒子"""

    x: float
    y: float
    vx: float
    vy: float
    size: int
    alpha: int
    lifetime: int = 0


class EnhancedWeatherSystem:
    """增强天气系统"""

    def __init__(self, screen_width: int, screen_height: int):
        """Initialize the EnhancedWeatherSystem."""
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.weather_type = WeatherType.CLEAR
        self.particles: list[WeatherParticle] = []
        self.intensity = 1.0  # 0.0 - 1.0
        self.fog_alpha = 0
        self.fog_surface: Surface | None = None

    def set_weather(self, weather_type: WeatherType, intensity: float = 1.0):
        """设置天气类型和强度"""
        self.weather_type = weather_type
        self.intensity = max(0.0, min(1.0, intensity))
        self.particles.clear()

        # 初始化天气粒子
        if weather_type == WeatherType.RAIN:
            self._init_rain()
        elif weather_type == WeatherType.SNOW:
            self._init_snow()
        elif weather_type == WeatherType.FOG:
            self._init_fog()

    def _init_rain(self):
        """初始化雨滴"""
        particle_count = int(200 * self.intensity)
        for _ in range(particle_count):
            self.particles.append(
                WeatherParticle(
                    x=random.uniform(0, self.screen_width),
                    y=random.uniform(-self.screen_height, 0),
                    vx=random.uniform(-2, -1),
                    vy=random.uniform(15, 25),
                    size=random.randint(1, 2),
                    alpha=random.randint(100, 200),
                )
            )

    def _init_snow(self):
        """初始化雪花"""
        particle_count = int(150 * self.intensity)
        for _ in range(particle_count):
            self.particles.append(
                WeatherParticle(
                    x=random.uniform(0, self.screen_width),
                    y=random.uniform(-self.screen_height, 0),
                    vx=random.uniform(-1, 1),
                    vy=random.uniform(2, 5),
                    size=random.randint(2, 4),
                    alpha=random.randint(150, 255),
                )
            )

    def _init_fog(self):
        """初始化雾效"""
        self.fog_alpha = int(100 * self.intensity)
        if self.fog_surface is None or self.fog_surface.get_size() != (
            self.screen_width,
            self.screen_height,
        ):
            self.fog_surface = Surface((self.screen_width, self.screen_height))
            self.fog_surface.fill((200, 200, 210))

    def update(self):
        """更新天气效果"""
        if self.weather_type == WeatherType.RAIN:
            self._update_rain()
        elif self.weather_type == WeatherType.SNOW:
            self._update_snow()
        elif self.weather_type == WeatherType.FOG:
            self._update_fog()

    def _update_rain(self):
        """更新雨滴"""
        for particle in self.particles:
            particle.x += particle.vx
            particle.y += particle.vy

            # 重置超出屏幕的粒子
            if particle.y > self.screen_height:
                particle.y = random.uniform(-50, 0)
                particle.x = random.uniform(0, self.screen_width)

    def _update_snow(self):
        """更新雪花"""
        for particle in self.particles:
            particle.lifetime += 1
            # 雪花飘动
            particle.x += particle.vx + math.sin(particle.lifetime * 0.1) * 0.5
            particle.y += particle.vy

            if particle.y > self.screen_height:
                particle.y = random.uniform(-50, 0)
                particle.x = random.uniform(0, self.screen_width)
                particle.lifetime = 0

    def _update_fog(self):
        """更新雾效（脉动效果）"""
        # 雾的透明度脉动
        pulse = math.sin(pygame.time.get_ticks() * 0.001) * 20
        self.fog_alpha = int((100 + pulse) * self.intensity)

    def render(self, surface: Surface):
        """渲染天气效果"""
        if self.weather_type == WeatherType.RAIN:
            self._render_rain(surface)
        elif self.weather_type == WeatherType.SNOW:
            self._render_snow(surface)
        elif self.weather_type == WeatherType.FOG:
            self._render_fog(surface)

    def _render_rain(self, surface: Surface):
        """渲染雨滴"""
        for particle in self.particles:
            # 雨滴是一条短线
            start_pos = (int(particle.x), int(particle.y))
            end_pos = (int(particle.x + particle.vx * 2), int(particle.y + particle.vy * 0.5))
            color = (180, 200, 220, particle.alpha)
            try:
                pygame.draw.line(surface, color[:3], start_pos, end_pos, particle.size)
            except (pygame.error, ValueError, TypeError) as e:
                logging.warning("Rain particle draw failed: %s", e, exc_info=True)

    def _render_snow(self, surface: Surface):
        """渲染雪花"""
        for particle in self.particles:
            pos = (int(particle.x), int(particle.y))
            color = (255, 255, 255, particle.alpha)
            try:
                pygame.draw.circle(surface, color[:3], pos, particle.size)
            except (pygame.error, ValueError, TypeError) as e:
                logging.warning("Snow particle draw failed: %s", e, exc_info=True)

    def _render_fog(self, surface: Surface):
        """渲染雾效"""
        if self.fog_surface:
            self.fog_surface.set_alpha(self.fog_alpha)
            surface.blit(self.fog_surface, (0, 0))
