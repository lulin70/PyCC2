"""
Top-Down Particle System for CC2-Style Visual Effects

All particles are top-down circular/ring effects (not 3D spherical particles).
CC2 Authentic Features:
- Explosion: Yellow/orange circular expanding rings
- Smoke: Circular gray-white clouds with drift
- Muzzle flash: White point + short line
- Hit marker: Red flash at target position
- Dirt splash: Radial scattering particles
- Blood pool: Persistent ground stain
"""

from __future__ import annotations

import contextlib
import logging
import math
import random
from collections import deque
from typing import TYPE_CHECKING

import pygame

from pycc2.presentation.rendering.surface_pool import SurfacePool

if TYPE_CHECKING:
    from .particle_pool import ParticlePool

logger = logging.getLogger(__name__)


class TopDownParticleSystem:
    """顶部视角专用粒子特效系统

    所有粒子都是俯视角度的圆形/环形效果，
    不是侧视角的球形/柱形粒子。

    CC2 Authentic Features:
    - 爆炸: 黄色/橙色圆形扩散环 (不是3D火球)
    - 烟雾: 圆形灰白色云团缓慢扩散+漂移
    - 枪口焰: 白点闪烁 + 短光线
    - 命中反馈: 目标位置红色闪现
    - 泥土飞溅: 圆形放射状散射颗粒
    - 血迹池: 持久性地面污渍
    """

    _MAX_RENDER_SURFACE_POOL = 30

    def __init__(self, max_particles: int = 256, pool: ParticlePool | None = None):
        self.particles: deque[dict] = deque()
        self.max_particles = max_particles
        self._pool: ParticlePool | None = pool
        self._render_surface_pool = SurfacePool(max_size=self._MAX_RENDER_SURFACE_POOL)
        self._enable_cc2_color_grading: bool = False
        if self._pool is None:
            try:
                from .particle_pool import ParticlePool as _PP

                self._pool = _PP(preallocate=max_particles)
            except (RuntimeError, ValueError, OSError) as e:
                logger.warning("ParticlePool creation failed: %s", e)
                self._pool = None

    def _get_render_surface(self, w: int, h: int) -> pygame.Surface:
        surf = self._render_surface_pool.get((w, h))
        surf.fill((0, 0, 0, 0))
        return surf

    def _add_particle(self, particle: dict) -> None:
        """添加粒子，超出上限时移除最老的"""
        if len(self.particles) >= self.max_particles:
            oldest = self.particles.popleft()
            if self._pool is not None:
                self._pool.release_dict(oldest)

        if self._pool is not None:
            pooled = self._pool.acquire_dict()
            pooled.update(particle)
            self.particles.append(pooled)
        else:
            self.particles.append(particle)

    def spawn_explosion_ring(self, x, y, max_radius=40, duration_ms=500, color=(255, 200, 50)):
        """爆炸冲击波 - 圆形扩散环（不是球形爆炸！）

        CC2真实特征：黄色/橙色圆形扩散环，多层同心圆
        """
        self._add_particle(
            {
                "type": "explosion_ring",
                "x": x,
                "y": y,
                "current_radius": 2,
                "max_radius": max_radius,
                "duration": duration_ms,
                "elapsed": 0,
                "color": color,
                "ring_width": 3,
                "layers": 3,
            }
        )

    def spawn_smoke_cloud(self, x, y, max_radius=25, duration_ms=2000, color=(180, 180, 170)):
        """烟雾云团 - 圆形灰白团块缓慢扩散+漂移

        CC2真实特征：圆形灰白色云团，边缘不规则湍流
        """
        turbulence = [(random.uniform(-5, 5), random.uniform(-5, 5)) for _ in range(8)]
        self._add_particle(
            {
                "type": "smoke",
                "x": x,
                "y": y,
                "current_radius": 3,
                "max_radius": max_radius,
                "duration": duration_ms,
                "elapsed": 0,
                "color": color,
                "drift_x": random.uniform(-0.5, 0.5),
                "drift_y": random.uniform(-0.5, 0.5),
                "turbulence": turbulence,
            }
        )

    def spawn_muzzle_flash(self, x, y, direction, duration_ms=80):
        """枪口焰 - 位置闪烁白点 + 短光线（沿射击方向）

        CC2真实特征：射击时单位位置出现小白点闪烁
        """
        self._add_particle(
            {
                "type": "muzzle_flash",
                "x": x,
                "y": y,
                "angle": direction,
                "length": 12,
                "duration": duration_ms,
                "elapsed": 0,
                "core_color": (255, 255, 240),
                "outer_color": (255, 220, 150),
            }
        )

    def spawn_hit_marker(self, x, y, damage_type="normal", duration_ms=300):
        """命中反馈 - 目标位置红色闪现（不同伤害类型不同颜色）

        damage_type:
        - normal: 红色
        - critical: 亮红色+更大
        - armor_penetrate: 金属色(银/蓝)
        - ricochet: 黄色(跳弹)
        """
        colors = {
            "normal": (255, 80, 80),
            "critical": (255, 50, 50),
            "armor_penetrate": (200, 200, 255),
            "ricochet": (255, 255, 100),
        }

        self._add_particle(
            {
                "type": "hit_marker",
                "x": x,
                "y": y,
                "color": colors.get(damage_type, colors["normal"]),
                "size": 15 if damage_type == "critical" else 10,
                "duration": duration_ms,
                "elapsed": 0,
            }
        )

    def spawn_dirt_splash(self, x, y, count=12):
        """泥土飞溅 - 着点周围小颗粒向外散射（俯视圆形分布）

        俯视特征：颗粒呈圆形放射状向外散射，无重力影响
        """
        for i in range(count):
            angle = (2 * math.pi * i) / count + random.uniform(-0.3, 0.3)
            speed = random.uniform(3, 8)
            self._add_particle(
                {
                    "type": "dirt_particle",
                    "x": x,
                    "y": y,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "size": random.randint(2, 4),
                    "color": random.choice([(139, 109, 59), (160, 130, 75), (110, 85, 45)]),
                    "gravity": 0,
                    "friction": 0.92,
                    "life_ms": random.randint(300, 600),
                    "elapsed": 0,
                }
            )

    _MAX_BLOOD_POOLS = 50

    def spawn_blood_pool(self, x, y, size=8):
        """血迹池 - 红色椭圆形污渍留在地面（持久，上限50个）"""
        # Evict oldest blood pool if at limit
        blood_count = sum(1 for p in self.particles if p.get("persistent", False))
        if blood_count >= self._MAX_BLOOD_POOLS:
            for p in list(self.particles):
                if p.get("persistent", False):
                    self.particles.remove(p)
                    if self._pool is not None:
                        self._pool.release_dict(p)
                    break

        self._add_particle(
            {
                "type": "blood_pool",
                "x": x,
                "y": y,
                "size": size,
                "duration": 30.0,  # Auto-expire after 30 seconds
                "elapsed": 0,
                "persistent": True,
                "color": (140, 20, 20),
            }
        )

    def update(self, dt_ms: int) -> None:
        """更新所有粒子状态"""
        alive = []
        for p in self.particles:
            p["elapsed"] += dt_ms

            if p["type"] == "explosion_ring":
                progress = min(1.0, p["elapsed"] / p["duration"])
                p["current_radius"] = 2 + (p["max_radius"] - 2) * progress

            elif p["type"] == "smoke":
                progress = min(1.0, p["elapsed"] / p["duration"])
                p["current_radius"] = 3 + (p["max_radius"] - 3) * progress
                p["x"] += p["drift_x"] * dt_ms * 0.05
                p["y"] += p["drift_y"] * dt_ms * 0.05

            elif p["type"] == "dirt_particle":
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["vx"] *= p["friction"]
                p["vy"] *= p["friction"]

            should_keep = (
                p.get("persistent", False)
                or p["elapsed"] < p.get("duration", 0)
                or p.get("life_ms", 0) > p["elapsed"]
            )

            if (
                should_keep
                and p.get("type") != "dirt_particle"
                or (p.get("type") == "dirt_particle" and p["elapsed"] < p.get("life_ms", 0))
            ):
                alive.append(p)
            elif self._pool is not None:
                self._pool.release_dict(p)

        self.particles = deque(alive)

    def render(self, surface: pygame.Surface) -> None:
        """渲染所有活跃粒子到目标surface"""
        if surface is None:
            return

        screen_rect = surface.get_rect()

        for p in self.particles:
            x, y = int(p["x"]), int(p["y"])

            if not screen_rect.collidepoint(x, y):
                continue

            if p["type"] == "explosion_ring":
                self._render_explosion_ring(surface, p)
            elif p["type"] == "smoke":
                self._render_smoke(surface, p)
            elif p["type"] == "muzzle_flash":
                self._render_muzzle_flash(surface, p)
            elif p["type"] == "hit_marker":
                self._render_hit_marker(surface, p)
            elif p["type"] == "dirt_particle":
                self._render_dirt_particle(surface, p)
            elif p["type"] == "blood_pool":
                self._render_blood_pool(surface, p)

        # 应用CC2色调分级（仅当配置启用时）
        if self._enable_cc2_color_grading:
            self._apply_cc2_color_grading(surface)

    def _apply_cc2_color_grading(self, surface: pygame.Surface) -> None:
        """Color grading placeholder — subclasses may override."""
        pass

    def _render_explosion_ring(self, surface: pygame.Surface, p: dict) -> None:
        """🔥 不规则爆炸火焰团（CC2战斗5.jpeg风格）

        CC2特征：
        - 形状不规则（像一团混乱的火球）
        - 颜色混合：外层黄→中层橙→内层红白核心
        - 边缘有锯齿状火焰舌头
        - 不是完美的几何圆形
        """
        cx, cy = int(p["x"]), int(p["y"])
        progress = p["elapsed"] / max(p["duration"], 1)
        current_radius = p["current_radius"]

        if current_radius < 0.5:
            return

        # 计算不规则的火焰形状（使用噪声扰动）
        num_points = 16
        points = []
        base_angle = 0
        for i in range(num_points):
            angle = base_angle + (2 * math.pi * i) / num_points
            # 添加随机噪声使形状不规则
            noise = 0.7 + 0.3 * math.sin(angle * 5 + progress * 10)  # 动态噪声
            r = current_radius * noise
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            points.append((px, py))

        # 绘制外层（黄橙色，低alpha）
        if len(points) >= 3:
            outer_color = (*p["color"], int(100 * (1 - progress)))
            pygame.draw.polygon(surface, outer_color, points)

        # 绘制中层（橙色，稍小）
        inner_points = []
        for i in range(num_points):
            angle = base_angle + (2 * math.pi * i) / num_points + math.pi / num_points
            noise = 0.5 + 0.2 * math.cos(angle * 7 + progress * 8)
            r = current_radius * 0.65 * noise
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            inner_points.append((px, py))

        if len(inner_points) >= 3:
            mid_color = (255, 140, 50, int(150 * (1 - progress)))
            pygame.draw.polygon(surface, mid_color, inner_points)

        # 绘制核心（红白色，最小）
        core_radius = max(int(current_radius * 0.25), 3)
        core_color = (255, 255, 200, int(220 * (1 - progress)))
        pygame.draw.circle(surface, core_color, (cx, cy), core_radius)

        # 添加随机火焰"舌头"（向外延伸的小三角形）
        num_tongues = 5
        for i in range(num_tongues):
            tongue_angle = (2 * math.pi * i) / num_tongues + progress * 2
            tongue_len = current_radius * (0.3 + 0.2 * random.random())
            tx = cx + tongue_len * 1.2 * math.cos(tongue_angle)
            ty = cy + tongue_len * 1.2 * math.sin(tongue_angle)
            tongue_color = (255, 200, 50, int(80 * (1 - progress)))
            # 绘制小三角形作为火焰舌头
            perp_angle = tongue_angle + math.pi / 2
            base_dist = current_radius * 0.6
            bx1 = cx + base_dist * math.cos(perp_angle)
            by1 = cy + base_dist * math.sin(perp_angle)
            bx2 = cx - base_dist * math.cos(perp_angle) * 0.5
            by2 = cy - base_dist * math.sin(perp_angle) * 0.5
            with contextlib.suppress(ValueError, TypeError):
                pygame.draw.polygon(surface, tongue_color, [(bx1, by1), (tx, ty), (bx2, by2)])

    def _render_smoke(self, surface: pygame.Surface, p: dict) -> None:
        progress = min(1.0, p["elapsed"] / p["duration"])
        radius = p["current_radius"]

        if radius < 0.5:
            return

        alpha = int(180 * (1 - progress * 0.7))
        base_color = p["color"]
        x, y = int(p["x"]), int(p["y"])
        turbulence = p.get("turbulence", [])

        for i in range(5):
            circle_radius = radius * (1 - i * 0.15)
            if circle_radius < 1:
                continue

            if turbulence:
                offset_idx = i % len(turbulence)
                turb_x, turb_y = turbulence[offset_idx]
                cx = x + int(turb_x * progress * 0.5)
                cy = y + int(turb_y * progress * 0.5)
            else:
                cx, cy = x, y

            shade = 1 - (i / 5) * 0.4
            color = (
                int(base_color[0] * shade),
                int(base_color[1] * shade),
                int(base_color[2] * shade),
                alpha,
            )

            size = int(circle_radius * 2 + 4)
            temp_surf = self._get_render_surface(size, size)
            center = int(circle_radius + 2)
            pygame.draw.circle(temp_surf, color, (center, center), int(circle_radius))
            surface.blit(temp_surf, (cx - center, cy - center))

    def _render_muzzle_flash(self, surface: pygame.Surface, p: dict) -> None:
        """渲染枪口焰 - 白点 + 方向线"""
        progress = min(1.0, p["elapsed"] / p["duration"])
        alpha = int(255 * (1 - progress))

        if alpha < 10:
            return

        core_color = (*p["core_color"], alpha)
        outer_color = (*p["outer_color"], alpha // 2)

        try:
            temp_surf = self._get_render_surface(30, 30)
            center = 15

            pygame.draw.circle(temp_surf, core_color, (center, center), 4)
            pygame.draw.circle(temp_surf, outer_color, (center, center), 6, 2)

            end_x = center + int(math.cos(p["angle"]) * p["length"])
            end_y = center + int(math.sin(p["angle"]) * p["length"])
            pygame.draw.line(temp_surf, outer_color, (center, center), (end_x, end_y), 2)

            surface.blit(temp_surf, (int(p["x"]) - center, int(p["y"]) - center))
        except (ValueError, TypeError):
            pass

    def _render_hit_marker(self, surface: pygame.Surface, p: dict) -> None:
        """渲染命中反馈 - X形或圆形标记"""
        progress = min(1.0, p["elapsed"] / p["duration"])
        alpha = int(255 * (1 - progress))
        size = p["size"]

        if alpha < 10 or size < 1:
            return

        color = (*p["color"], alpha)

        try:
            temp_surf = self._get_render_surface(size * 2 + 4, size * 2 + 4)
            center = size + 2

            pygame.draw.circle(temp_surf, color, (center, center), size, 2)

            cross_size = size * 0.7
            pygame.draw.line(
                temp_surf,
                color,
                (center - cross_size, center - cross_size),
                (center + cross_size, center + cross_size),
                2,
            )
            pygame.draw.line(
                temp_surf,
                color,
                (center + cross_size, center - cross_size),
                (center - cross_size, center + cross_size),
                2,
            )

            surface.blit(temp_surf, (int(p["x"]) - center, int(p["y"]) - center))
        except (ValueError, TypeError):
            pass

    def _render_dirt_particle(self, surface: pygame.Surface, p: dict) -> None:
        """渲染泥土颗粒 - 小实心圆"""
        progress = min(1.0, p["elapsed"] / p.get("life_ms", 500))
        alpha = int(255 * (1 - progress))
        size = p["size"]

        if alpha < 10 or size < 1:
            return

        color = (*p["color"], alpha)

        try:
            temp_surf = self._get_render_surface(size * 2 + 2, size * 2 + 2)
            center = size + 1
            pygame.draw.circle(temp_surf, color, (center, center), size)
            surface.blit(temp_surf, (int(p["x"]) - center, int(p["y"]) - center))
        except (ValueError, TypeError):
            pass

    def _render_blood_pool(self, surface: pygame.Surface, p: dict) -> None:
        """渲染血迹池 - 椭圆形污渍"""
        size = p["size"]
        color = p["color"]

        try:
            temp_surf = self._get_render_surface(size * 2 + 4, size * 2 + 2)
            center_x = size + 2
            center_y = size + 1

            pygame.draw.ellipse(temp_surf, (*color, 180), (2, 2, size * 2, size))

            for _i in range(3):
                splash_x = center_x + random.randint(-size // 2, size // 2)
                splash_y = center_y + random.randint(-size // 3, size // 3)
                splash_size = random.randint(1, 3)
                pygame.draw.circle(temp_surf, (*color, 150), (splash_x, splash_y), splash_size)

            surface.blit(temp_surf, (int(p["x"]) - center_x, int(p["y"]) - center_y))
        except (ValueError, TypeError):
            pass

    @property
    def active_count(self) -> int:
        """当前活跃粒子数量"""
        return len(self.particles)

    def get_dirty_rects(self) -> list[pygame.Rect]:
        """Return bounding rects for all active particles (for dirty-rect tracking).

        Each particle contributes a rect centered at (x, y) with size based on
        its current radius.  The list is suitable for passing to
        ``DirtyRectTracker.mark_dirty()``.
        """
        rects: list[pygame.Rect] = []
        for p in self.particles:
            x, y = int(p["x"]), int(p["y"])
            r = int(p.get("current_radius", p.get("max_radius", 10)))
            if r < 1:
                r = 10  # minimum bounding size for point-like particles
            rects.append(pygame.Rect(x - r, y - r, r * 2, r * 2))
        return rects
