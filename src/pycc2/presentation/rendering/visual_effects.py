"""
Phase 4: 视觉效果升级 - 增强粒子系统、天气效果、屏幕后处理
"""
from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

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
            except Exception as e:
                logging.warning(f"Rain particle draw failed: {e}", exc_info=True)
    
    def _render_snow(self, surface: Surface):
        """渲染雪花"""
        for particle in self.particles:
            pos = (int(particle.x), int(particle.y))
            color = (255, 255, 255, particle.alpha)
            try:
                pygame.draw.circle(surface, color[:3], pos, particle.size)
            except Exception as e:
                logging.warning(f"Snow particle draw failed: {e}", exc_info=True)
    
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
        self._emit_sparks(x, y, random.randint(3, 5))
    
    def _emit_fire_core(self, x: float, y: float, count: int):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 8)
            self.particles.append(self.Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(15, 30),
                max_life=30,
                size=random.randint(4, 8),
                color=(255, random.randint(100, 200), 0),
                particle_type="fire"
            ))
    
    def _emit_smoke_plume(self, x: float, y: float, count: int):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.5, 2.0)
            self.particles.append(self.Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
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
            speed = random.uniform(2, 3)
            self.particles.append(self.Particle(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                life=random.randint(3, 5),
                max_life=5,
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
            
            if particle.particle_type not in ("smoke", "spark"):
                particle.vx *= 0.95
                particle.vy *= 0.95
            
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
            except Exception as e:
                logging.warning(f"Particle draw failed: {e}", exc_info=True)
    
    def clear(self):
        """清除所有粒子"""
        self.particles.clear()


class SurrenderFlagEffect:
    """White flag indicator for surrendered units — top-down view: white circle dot above unit."""

    def __init__(self):
        self._active_flags: dict[str, dict] = {}

    def show(self, unit_id: str, x: float, y: float, duration: int = 120) -> None:
        self._active_flags[unit_id] = {
            'x': x, 'y': y, 'tick': 0, 'duration': duration,
        }

    def remove(self, unit_id: str) -> None:
        self._active_flags.pop(unit_id, None)

    def update(self) -> None:
        to_remove = []
        for uid, flag in self._active_flags.items():
            flag['tick'] += 1
            if flag['tick'] > flag['duration']:
                to_remove.append(uid)
        for uid in to_remove:
            del self._active_flags[uid]

    def render(self, surface: Surface, camera_offset: tuple[float, float] = (0, 0)) -> None:
        for uid, flag in self._active_flags.items():
            sx = int(flag['x'] - camera_offset[0])
            sy = int(flag['y'] - camera_offset[1])
            tick = flag['tick']

            remaining = flag['duration'] - tick
            alpha = min(255, int(255 * remaining / 60)) if remaining < 60 else 255

            pulse = 1.0 + 0.15 * math.sin(tick * 0.15)
            r = int(4 * pulse)

            s = Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 255, 255, alpha), (r + 1, r + 1), r)
            inner_r = max(1, r - 2)
            pygame.draw.circle(s, (240, 240, 240, alpha), (r + 1, r + 1), inner_r)
            surface.blit(s, (sx - r - 1, sy - r - 8))


class CC2ExplosionEffect:
    """CC2-style explosion: 3-frame core flash + lingering smoke cloud + camera shake."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.tick = 0
        self.duration = random.randint(18, 23)
        self.shake_duration = 9
        self.shake_offset = (0.0, 0.0)
        self._smoke_particles: list[dict] = []
        self._init_smoke()

    def _init_smoke(self):
        for _ in range(8):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(0.3, 1.2)
            self._smoke_particles.append({
                'ox': 0.0, 'oy': 0.0,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'radius': random.uniform(4, 7),
                'alpha': random.randint(140, 200),
            })

    @property
    def alive(self) -> bool:
        return self.tick < self.duration

    def update(self):
        if not self.alive:
            return
        self.tick += 1
        if self.tick <= self.shake_duration:
            self.shake_offset = (
                random.uniform(-3, 3),
                random.uniform(-3, 3),
            )
        else:
            self.shake_offset = (0.0, 0.0)
        for p in self._smoke_particles:
            p['ox'] += p['vx']
            p['oy'] += p['vy']
            p['vx'] *= 0.98
            p['vy'] *= 0.98
            p['radius'] += 0.15

    def render(self, surface: Surface, camera_offset: tuple[float, float] = (0, 0)):
        if not self.alive:
            return
        sx = int(self.x - camera_offset[0])
        sy = int(self.y - camera_offset[1])

        if self.tick < 3:
            progress = self.tick / 3
            outer_r = int(10 + progress * 15)
            alpha = max(0, 255 - int(progress * 80))
            if self.tick == 0:
                color = (255, 255, 200)
            elif self.tick == 1:
                color = (255, 140, 40)
            else:
                color = (220, 80, 20)
            s = Surface((outer_r * 2, outer_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*color, alpha), (outer_r, outer_r), outer_r)
            mid_r = max(1, int(outer_r * 0.65))
            pygame.draw.circle(s, (255, 200, 100, min(255, alpha + 30)), (outer_r, outer_r), mid_r)
            inner_r = max(1, outer_r // 3)
            pygame.draw.circle(s, (255, 255, 220, min(255, alpha + 40)), (outer_r, outer_r), inner_r)
            surface.blit(s, (sx - outer_r, sy - outer_r))
        else:
            fade = max(0.0, 1.0 - (self.tick - 3) / (self.duration - 3))
            for p in self._smoke_particles:
                px = sx + int(p['ox'])
                py = sy + int(p['oy'])
                r = int(p['radius'])
                alpha = int(p['alpha'] * fade)
                if alpha < 5 or r < 1:
                    continue
                s = Surface((r * 2, r * 2), pygame.SRCALPHA)
                gray = random.randint(90, 130)
                pygame.draw.circle(s, (gray, gray, gray, alpha), (r, r), r)
                surface.blit(s, (px - r, py - r))


class CC2SmokeEffect:
    """Large-area smoke cloud seen from above: flat circular blobs expanding on ground plane."""

    def __init__(self, x: float, y: float, tile_size: int = 48):
        self.x = x
        self.y = y
        self.tick = 0
        self.duration = 120
        self.tile_size = tile_size
        self.base_radius = tile_size * 4.0
        self._blobs: list[dict] = []
        self._init_blobs()

    def _init_blobs(self):
        num_blobs = random.randint(10, 16)
        for _ in range(num_blobs):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(0, self.base_radius * 0.6)
            blob_r = random.uniform(self.base_radius * 0.3, self.base_radius * 0.55)
            self._blobs.append({
                'angle': angle,
                'dist': dist,
                'radius': blob_r,
                'jagged_offsets': [random.uniform(-0.2, 0.2) for _ in range(12)],
                'alpha': random.randint(150, 200),
                'expand_speed': random.uniform(0.15, 0.35),
            })

    @property
    def alive(self) -> bool:
        return self.tick < self.duration

    def update(self):
        if not self.alive:
            return
        self.tick += 1
        for b in self._blobs:
            b['radius'] += b['expand_speed']
            b['dist'] += 0.03

    def render(self, surface: Surface, camera_offset: tuple[float, float] = (0, 0)):
        if not self.alive:
            return
        sx = int(self.x - camera_offset[0])
        sy = int(self.y - camera_offset[1])
        fade = max(0.0, 1.0 - (self.tick / self.duration) ** 0.7)

        for b in self._blobs:
            cx = sx + int(math.cos(b['angle']) * b['dist'])
            cy = sy + int(math.sin(b['angle']) * b['dist'])
            r = int(b['radius'])
            alpha = int(b['alpha'] * fade)
            if alpha < 5 or r < 2:
                continue

            size = r * 2 + 4
            s = Surface((size, size), pygame.SRCALPHA)
            center = (size // 2, size // 2)
            num_pts = len(b['jagged_offsets'])
            points = []
            for i in range(num_pts):
                a = (2 * math.pi * i) / num_pts
                jag = 1.0 + b['jagged_offsets'][i]
                pr = r * jag
                points.append((
                    center[0] + int(math.cos(a) * pr),
                    center[1] + int(math.sin(a) * pr),
                ))
            gray = random.randint(160, 200)
            pygame.draw.polygon(s, (gray, gray, gray, alpha), points)
            surface.blit(s, (cx - size // 2, cy - size // 2))


class CC2HitSparkEffect:
    """Short-lived hit spark: 3-5 yellow/white dots scattering radially."""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.tick = 0
        self.duration = random.randint(3, 5)
        self._sparks: list[dict] = []
        self._init_sparks()

    def _init_sparks(self):
        count = random.randint(3, 5)
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 3)
            self._sparks.append({
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'ox': 0.0,
                'oy': 0.0,
                'color': random.choice([
                    (255, 255, 100),
                    (255, 255, 200),
                    (255, 240, 80),
                ]),
            })

    @property
    def alive(self) -> bool:
        return self.tick < self.duration

    def update(self):
        if not self.alive:
            return
        self.tick += 1
        for sp in self._sparks:
            sp['ox'] += sp['vx']
            sp['oy'] += sp['vy']
            sp['vx'] *= 0.85
            sp['vy'] *= 0.85

    def render(self, surface: Surface, camera_offset: tuple[float, float] = (0, 0)):
        if not self.alive:
            return
        sx = int(self.x - camera_offset[0])
        sy = int(self.y - camera_offset[1])
        fade = max(0.0, 1.0 - self.tick / self.duration)
        for sp in self._sparks:
            px = sx + int(sp['ox'])
            py = sy + int(sp['oy'])
            alpha = int(255 * fade)
            if alpha < 10:
                continue
            s = Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(s, (*sp['color'], alpha), (3, 3), 2)
            surface.blit(s, (px - 3, py - 3))


class CC2MuzzleFlashEffect:
    """Brief muzzle flash at weapon tip: top-down bright dot on ground plane, 1-2 frames."""

    def __init__(self, x: float, y: float, angle: float = 0.0):
        self.x = x
        self.y = y
        self.angle = angle
        self.tick = 0
        self.duration = random.randint(1, 2)
        self._colors = [
            (255, 255, 100),
            (255, 180, 50),
            (255, 255, 255),
        ]

    @property
    def alive(self) -> bool:
        return self.tick < self.duration

    def update(self):
        if not self.alive:
            return
        self.tick += 1

    def render(self, surface: Surface, camera_offset: tuple[float, float] = (0, 0)):
        if not self.alive:
            return
        sx = int(self.x - camera_offset[0])
        sy = int(self.y - camera_offset[1])
        color = self._colors[min(self.tick, len(self._colors) - 1)]
        r = 4
        s = Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, 240), (r, r), r)
        inner_r = max(1, r // 2)
        pygame.draw.circle(s, (255, 255, 255, 255), (r, r), inner_r)
        surface.blit(s, (sx - r, sy - r))
