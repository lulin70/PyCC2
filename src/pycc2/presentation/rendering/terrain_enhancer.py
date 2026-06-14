"""
Phase 2: 地形改进 - Perlin噪声生成器和边缘混合
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

from pygame import Surface

if TYPE_CHECKING:
    pass


class PerlinNoise:
    """Perlin噪声生成器 - 用于生成自然地形纹理"""

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        # 生成256个随机排列
        self.p = list(range(256))
        self.rng.shuffle(self.p)
        self.p = self.p + self.p  # 复制以避免溢出

    def fade(self, t: float) -> float:
        """平滑插值函数"""
        return t * t * t * (t * (t * 6 - 15) + 10)

    def lerp(self, t: float, a: float, b: float) -> float:
        """线性插值"""
        return a + t * (b - a)

    def grad(self, hash: int, x: float, y: float) -> float:
        """梯度函数"""
        h = hash & 3
        u = x if h < 2 else y
        v = y if h < 2 else x
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

    def noise(self, x: float, y: float) -> float:
        """
        生成2D Perlin噪声
        返回值范围: [-1, 1]
        """
        # 找到单位网格的坐标
        X = int(math.floor(x)) & 255
        Y = int(math.floor(y)) & 255

        # 找到相对坐标
        x -= math.floor(x)
        y -= math.floor(y)

        # 计算淡化曲线
        u = self.fade(x)
        v = self.fade(y)

        # 哈希坐标
        a = self.p[X] + Y
        aa = self.p[a]
        ab = self.p[a + 1]
        b = self.p[X + 1] + Y
        ba = self.p[b]
        bb = self.p[b + 1]

        # 混合结果
        return self.lerp(
            v,
            self.lerp(u, self.grad(self.p[aa], x, y), self.grad(self.p[ba], x - 1, y)),
            self.lerp(u, self.grad(self.p[ab], x, y - 1), self.grad(self.p[bb], x - 1, y - 1)),
        )

    def octave_noise(
        self,
        x: float,
        y: float,
        octaves: int = 4,
        persistence: float = 0.5,
        lacunarity: float = 2.0,
    ) -> float:
        """
        多层Perlin噪声（分形噪声）

        Args:
            x, y: 坐标
            octaves: 层数（越多越细节）
            persistence: 振幅衰减（0-1）
            lacunarity: 频率增长（通常2.0）

        Returns:
            噪声值 [-1, 1]
        """
        total = 0.0
        frequency = 1.0
        amplitude = 1.0
        max_value = 0.0

        for _ in range(octaves):
            total += self.noise(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= lacunarity

        return total / max_value


class TerrainEnhancer:
    """地形增强器 - 使用Perlin噪声生成更精细的地形纹理"""

    def __init__(self, seed: int | None = None):
        self.perlin = PerlinNoise(seed)
        self.rng = random.Random(seed)

    def generate_grass_texture(self, size: int = 32) -> Surface:
        """生成草地纹理（使用Perlin噪声）"""
        surface = Surface((size, size))
        surface.fill((96, 143, 48))  # 基础草绿色

        # 使用Perlin噪声添加变化
        for y in range(size):
            for x in range(size):
                # 多层噪声
                noise_val = self.perlin.octave_noise(x / 8.0, y / 8.0, octaves=3, persistence=0.5)

                # 映射到颜色变化 [-20, +20]
                variation = int(noise_val * 20)
                base_color = (96, 143, 48)
                new_color = (
                    max(0, min(255, base_color[0] + variation)),
                    max(0, min(255, base_color[1] + variation)),
                    max(0, min(255, base_color[2] + variation)),
                )
                surface.set_at((x, y), new_color)

        # 添加草叶细节
        for _ in range(size // 4):
            gx = self.rng.randint(0, size - 1)
            gy = self.rng.randint(0, size - 1)
            grass_color = (68, 112, 34)
            surface.set_at((gx, gy), grass_color)

        return surface

    def generate_dirt_texture(self, size: int = 32) -> Surface:
        """生成泥土纹理"""
        surface = Surface((size, size))
        surface.fill((166, 138, 95))

        for y in range(size):
            for x in range(size):
                noise_val = self.perlin.octave_noise(x / 6.0, y / 6.0, octaves=4, persistence=0.6)
                variation = int(noise_val * 25)
                base_color = (166, 138, 95)
                new_color = (
                    max(0, min(255, base_color[0] + variation)),
                    max(0, min(255, base_color[1] + variation)),
                    max(0, min(255, base_color[2] + variation)),
                )
                surface.set_at((x, y), new_color)

        return surface

    def generate_water_texture(self, size: int = 32, frame: int = 0) -> Surface:
        """生成水面纹理（带动画）"""
        surface = Surface((size, size))
        surface.fill((64, 120, 172))

        # 水波动画偏移
        wave_offset = frame * 0.1

        for y in range(size):
            for x in range(size):
                # 水波噪声
                noise_val = self.perlin.octave_noise(
                    (x + wave_offset) / 10.0, (y + wave_offset) / 10.0, octaves=2, persistence=0.4
                )
                variation = int(noise_val * 15)
                base_color = (64, 120, 172)
                new_color = (
                    max(0, min(255, base_color[0] + variation)),
                    max(0, min(255, base_color[1] + variation)),
                    max(0, min(255, base_color[2] + variation)),
                )
                surface.set_at((x, y), new_color)

        return surface

    def blend_terrain_edges(
        self, tile_surface: Surface, neighbors: dict[str, int], current_terrain: int
    ) -> Surface:
        """
        地形边缘混合 - 平滑不同地形类型的过渡

        Args:
            tile_surface: 当前tile的surface
            neighbors: 邻居地形 {'n': terrain_id, 'e': ..., 's': ..., 'w': ...}
            current_terrain: 当前地形ID

        Returns:
            混合后的surface
        """
        size = tile_surface.get_width()
        result = tile_surface.copy()

        # 边缘混合宽度
        blend_width = size // 8

        # 北边混合
        if neighbors.get("n", current_terrain) != current_terrain:
            neighbor_color = self._get_terrain_base_color(neighbors.get("n", 0))
            for y in range(blend_width):
                alpha = y / blend_width  # 0 -> 1
                for x in range(size):
                    current = result.get_at((x, y))
                    blended = (
                        int(current[0] * alpha + neighbor_color[0] * (1 - alpha)),
                        int(current[1] * alpha + neighbor_color[1] * (1 - alpha)),
                        int(current[2] * alpha + neighbor_color[2] * (1 - alpha)),
                    )
                    result.set_at((x, y), blended)

        # 南边混合
        if neighbors.get("s", current_terrain) != current_terrain:
            neighbor_color = self._get_terrain_base_color(neighbors.get("s", 0))
            for y in range(size - blend_width, size):
                alpha = (size - y) / blend_width
                for x in range(size):
                    current = result.get_at((x, y))
                    blended = (
                        int(current[0] * alpha + neighbor_color[0] * (1 - alpha)),
                        int(current[1] * alpha + neighbor_color[1] * (1 - alpha)),
                        int(current[2] * alpha + neighbor_color[2] * (1 - alpha)),
                    )
                    result.set_at((x, y), blended)

        # 东边混合
        if neighbors.get("e", current_terrain) != current_terrain:
            neighbor_color = self._get_terrain_base_color(neighbors.get("e", 0))
            for x in range(size - blend_width, size):
                alpha = (size - x) / blend_width
                for y in range(size):
                    current = result.get_at((x, y))
                    blended = (
                        int(current[0] * alpha + neighbor_color[0] * (1 - alpha)),
                        int(current[1] * alpha + neighbor_color[1] * (1 - alpha)),
                        int(current[2] * alpha + neighbor_color[2] * (1 - alpha)),
                    )
                    result.set_at((x, y), blended)

        # 西边混合
        if neighbors.get("w", current_terrain) != current_terrain:
            neighbor_color = self._get_terrain_base_color(neighbors.get("w", 0))
            for x in range(blend_width):
                alpha = x / blend_width
                for y in range(size):
                    current = result.get_at((x, y))
                    blended = (
                        int(current[0] * alpha + neighbor_color[0] * (1 - alpha)),
                        int(current[1] * alpha + neighbor_color[1] * (1 - alpha)),
                        int(current[2] * alpha + neighbor_color[2] * (1 - alpha)),
                    )
                    result.set_at((x, y), blended)

        return result

    def _get_terrain_base_color(self, terrain_id: int) -> tuple[int, int, int]:
        """获取地形基础颜色"""
        terrain_colors = {
            0: (96, 143, 48),  # 草地
            1: (149, 126, 94),  # 道路
            2: (96, 143, 48),  # 开阔地
            3: (52, 120, 52),  # 树林
            4: (52, 120, 52),  # 密林
            5: (95, 92, 88),  # 建筑
            6: (95, 92, 88),  # 建筑
            7: (64, 120, 172),  # 水
            8: (68, 112, 34),  # 树篱
            9: (110, 110, 110),  # 墙
            10: (149, 126, 94),  # 桥
            11: (166, 138, 95),  # 粗糙地形
            12: (120, 100, 70),  # 弹坑
            13: (90, 120, 90),  # 沼泽
        }
        return terrain_colors.get(terrain_id, (96, 143, 48))
