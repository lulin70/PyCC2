"""
Phase 4: 视觉效果升级 - 增强粒子系统、天气效果、屏幕后处理
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import pygame
from pygame import Surface

if TYPE_CHECKING:
    pass


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
            self.particles.append(WeatherParticle(
                x=random.uniform(0, self.screen_width),
                y=random.uniform(-self.screen_height, 0),
                vx=random.uniform(-2, -1),
                vy=random.uniform(15, 25),
                size=random.randint(1, 2),
                alpha=random.randint(100, 200)
            ))
    
    def _init_snow(self):
        """初始化雪花"""
        particle_count = int(150 * self.intensity)
        for _ in range(particle_count):
            self.particles.append(WeatherParticle(
                x=random.uniform(0, self.screen_width),
                y=random.uniform(-self.screen_height, 0),
                vx=random.uniform(-1, 1),
                vy=random.uniform(2, 5),
                size=random.randint(2, 4),
                alpha=random.randint(150, 255)
            ))
    
    def _init_fog(self):
        """初始化雾效"""
        self.fog_alpha = int(100 * self.intensity)
        if self.fog_surface is None or self.fog_surface.get_size() != (self.screen_width, self.screen_height):
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
            except:
                pass
    
    def _render_snow(self, surface: Surface):
        """渲染雪花"""
        for particle in self.particles:
            pos = (int(particle.x), int(particle.y))
            color = (255, 255, 255, particle.alpha)
            try:
                pygame.draw.circle(surface, color[:3], pos, particle.size)
            except:
                pass
    
    def _render_fog(self, surface: Surface):
        """渲染雾效"""
        if self.fog_surface:
            self.fog_surface.set_alpha(self.fog_alpha)
            surface.blit(self.fog_surface, (0, 0))


class PostProcessingEffects:
    """屏幕后处理效果"""
    
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.vignette_surface: Surface | None = None
        self.color_grading_enabled = False
        self.vignette_enabled = False
    
    def enable_vignette(self, intensity: float = 0.5):
        """启用暗角效果"""
        self.vignette_enabled = True
        self._create_vignette(intensity)
    
    def disable_vignette(self):
        """禁用暗角效果"""
        self.vignette_enabled = False
    
    def _create_vignette(self, intensity: float = 0.5):
        """创建暗角遮罩"""
        self.vignette_surface = Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.vignette_surface.fill((0, 0, 0, 0))  # 透明背景
        
        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        max_radius = math.sqrt(center_x**2 + center_y**2)
        
        # 创建径向渐变（简化版本，只绘制边缘）
        # 为了性能，使用圆形绘制而不是逐像素
        steps = 50
        for i in range(steps):
            progress = i / steps
            radius = int(max_radius * (1 - progress))
            alpha = int(255 * (progress ** 2) * intensity)
            alpha = max(0, min(255, alpha))
            color = (0, 0, 0, alpha)
            pygame.draw.circle(self.vignette_surface, color, (center_x, center_y), radius, 2)
    
    def enable_color_grading(self):
        """启用色彩分级"""
        self.color_grading_enabled = True
    
    def disable_color_grading(self):
        """禁用色彩分级"""
        self.color_grading_enabled = False
    
    def apply_color_grading(self, surface: Surface, style: str = "war") -> Surface:
        """
        应用色彩分级
        
        Args:
            surface: 原始surface
            style: 风格 ("war", "cold", "warm")
        """
        if not self.color_grading_enabled:
            return surface
        
        result = surface.copy()
        
        if style == "war":
            # 战争风格：降低饱和度，增加对比度
            self._apply_desaturation(result, 0.3)
        elif style == "cold":
            # 冷色调：增加蓝色
            self._apply_color_tint(result, (0, 0, 20))
        elif style == "warm":
            # 暖色调：增加红黄
            self._apply_color_tint(result, (20, 10, 0))
        
        return result
    
    def _apply_desaturation(self, surface: Surface, amount: float):
        """降低饱和度"""
        # 注意：这是简化版本，实际应用中可能需要使用shader
        pass
    
    def _apply_color_tint(self, surface: Surface, tint: tuple[int, int, int]):
        """应用色调"""
        # 创建色调层
        tint_surface = Surface(surface.get_size())
        tint_surface.fill(tint)
        tint_surface.set_alpha(30)
        surface.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    
    def apply_vignette(self, surface: Surface):
        """应用暗角效果"""
        if self.vignette_enabled and self.vignette_surface:
            surface.blit(self.vignette_surface, (0, 0))
    
    def apply_all(self, surface: Surface, color_style: str = "war") -> Surface:
        """应用所有后处理效果"""
        result = surface
        
        if self.color_grading_enabled:
            result = self.apply_color_grading(result, color_style)
        
        if self.vignette_enabled:
            self.apply_vignette(result)
        
        return result


class EnhancedParticleSystem:
    """增强粒子系统 - 多层爆炸效果"""
    
    @dataclass
    class Particle:
        x: float
        y: float
        vx: float
        vy: float
        life: int
        max_life: int
        size: int
        color: tuple[int, int, int]
        particle_type: str  # "fire", "smoke", "debris", "spark"
    
    def __init__(self):
        self.particles: list[EnhancedParticleSystem.Particle] = []
    
    def emit_explosion(self, x: float, y: float, intensity: float = 1.0):
        """发射多层爆炸效果"""
        # 第1层：火焰核心
        self._emit_fire_core(x, y, int(20 * intensity))
        
        # 第2层：烟雾
        self._emit_smoke_plume(x, y, int(15 * intensity))
        
        # 第3层：碎片
        self._emit_debris(x, y, int(10 * intensity))
        
        # 第4层：火花
        self._emit_sparks(x, y, int(25 * intensity))
    
    def _emit_fire_core(self, x: float, y: float, count: int):
        """火焰核心"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 8)
            self.particles.append(self.Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 2,  # 向上
                life=random.randint(15, 30),
                max_life=30,
                size=random.randint(4, 8),
                color=(255, random.randint(100, 200), 0),
                particle_type="fire"
            ))
    
    def _emit_smoke_plume(self, x: float, y: float, count: int):
        """烟雾羽流"""
        for _ in range(count):
            angle = random.uniform(-math.pi/4, math.pi/4)  # 主要向上
            speed = random.uniform(1, 3)
            self.particles.append(self.Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 3,
                life=random.randint(40, 60),
                max_life=60,
                size=random.randint(6, 12),
                color=(random.randint(80, 120), random.randint(80, 120), random.randint(80, 120)),
                particle_type="smoke"
            ))
    
    def _emit_debris(self, x: float, y: float, count: int):
        """碎片"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(5, 12)
            self.particles.append(self.Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(20, 40),
                max_life=40,
                size=random.randint(2, 4),
                color=(random.randint(100, 150), random.randint(80, 120), random.randint(60, 100)),
                particle_type="debris"
            ))
    
    def _emit_sparks(self, x: float, y: float, count: int):
        """火花"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(8, 15)
            self.particles.append(self.Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(10, 20),
                max_life=20,
                size=1,
                color=(255, 255, random.randint(100, 255)),
                particle_type="spark"
            ))
    
    def update(self):
        """更新所有粒子"""
        for particle in self.particles[:]:
            # 更新位置
            particle.x += particle.vx
            particle.y += particle.vy
            
            # 重力影响（除了烟雾）
            if particle.particle_type != "smoke":
                particle.vy += 0.3
            
            # 空气阻力
            particle.vx *= 0.98
            particle.vy *= 0.98
            
            # 烟雾扩散
            if particle.particle_type == "smoke":
                particle.size += 0.1
            
            # 生命周期
            particle.life -= 1
            if particle.life <= 0:
                self.particles.remove(particle)
    
    def render(self, surface: Surface, camera_offset: tuple[float, float] = (0, 0)):
        """渲染所有粒子"""
        for particle in self.particles:
            # 计算透明度
            alpha = int(255 * (particle.life / particle.max_life))
            
            # 屏幕坐标
            screen_x = int(particle.x - camera_offset[0])
            screen_y = int(particle.y - camera_offset[1])
            
            # 渲染粒子
            try:
                if particle.particle_type == "smoke":
                    # 烟雾使用圆形
                    s = Surface((int(particle.size * 2), int(particle.size * 2)), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*particle.color, alpha), (int(particle.size), int(particle.size)), int(particle.size))
                    surface.blit(s, (screen_x - int(particle.size), screen_y - int(particle.size)))
                else:
                    # 其他粒子使用小圆点
                    color = (*particle.color, alpha)
                    pygame.draw.circle(surface, color[:3], (screen_x, screen_y), particle.size)
            except:
                pass
    
    def clear(self):
        """清除所有粒子"""
        self.particles.clear()
