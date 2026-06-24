"""Pixel canvas, color palette, and noise/dither utilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


# ============================================================
# 1. 调色板 — CC2风格军事色调
# ============================================================


class CCPalette(Enum):
    """Close Combat 2 风格军事调色板 — 基于CC2截图精确分析

    2026-05-29更新: Phase 5 Fix — 草地再降暗8%匹配CC2原版(A1)
    CC2截图显示草地为极暗军绿色(#3A5F0F级别)，之前仍偏亮
    排除: BLOOD颜色（保持鲜艳用于视觉效果）
    """

    # Grass — DARK military olive green (exact from CC2 screenshot)
    # 2026-05-29 Phase 5 Fix: 再降8%到CC2精确值（对比12张CC2截图确认）
    GRASS_BASE = (68, 110, 32)  # 原(76,122,37) → 再降8%→#6E6E20
    GRASS_LIGHT = (82, 126, 39)  # 原(90,139,45) → 再降8%→#527E27
    GRASS_DARK = (52, 88, 23)  # 原(58,98,26) → 再降8%→#345817

    # Road — grey-brown, NOT orange-brown
    ROAD = (105, 89, 65)  # 原始(105,89,64) → 去饱和5%
    DIRT_ROAD = (93, 79, 56)  # 原始(93,79,55) → 去饱和5%
    DIRT = (128, 100, 59)  # 原始(129,100,58) → 去饱和5%

    # Water — dark blue-grey, semi-transparent
    WATER_DEEP = (25, 55, 95)  # 原始(25,54,94) → 去饱和5%
    WATER_SHALLOW = (46, 93, 157)  # 原始(47,94,158) → 去饱和5%
    WATER_FOAM = (121, 159, 197)  # 原始(123,160,198) → 去饱和5%

    TREE_CROWN = (37, 73, 34)  # 原始(37,73,33) → 去饱和5%
    TREE_CROWN_DARK = (28, 58, 26)  # 原始(27,58,25) → 去饱和5%
    TREE_CROWN_MID = (48, 88, 42)  # A4: 新增中间色调 (介于dark和light之间)
    TREE_TRUNK = (80, 57, 35)  # 原始(80,57,34) → 去饱和5%
    HEDGE_GREEN = (44, 83, 35)  # 原始(44,83,34) → 去饱和5%

    # Building roofs — match CC2 exactly (with 5% desaturation)
    BUILDING_WALL = (173, 165, 148)  # 原始(175,166,148) → 去饱和5%
    BUILDING_ROOF = (136, 95, 64)  # 原始(137,95,63) → 去饱和5%
    BUILDING_SHADOW = (89, 55, 38)  # A3: 再降10%增强对比度 (原99,62,43)
    ROAD_MARK = (118, 96, 54)  # 原始(119,96,53) → 去饱和5%
    CONCRETE = (160, 156, 145)  # A3: +4亮度增强对比 (原154,150,140)
    SAND = (178, 164, 122)  # A3: +4亮度增强对比 (原174,160,119)
    MUD = (134, 104, 25)  # 原始(136,104,24) → 去饱和5%
    SNOW = (228, 233, 238)  # A3: +4亮度增强对比 (原224,229,234)
    WIRE = (100, 100, 100)  # 原始(100,100,100) → 无变化（灰色）
    BUNKER = (117, 112, 103)  # 原始(118,113,104) → 去饱和5%
    ALLIES_HELMET = (89, 107, 53)  # A3: +4亮度增强对比 (原85,103,51)
    ALLIES_UNIFORM = (80, 86, 38)  # A3: +4亮度增强对比 (原76,82,35)
    AXIS_HELMET = (60, 62, 56)  # A3: +4亮度增强对比 (原56,58,52)
    AXIS_UNIFORM = (89, 95, 84)  # A3: +4亮度增强对比 (原85,91,80)
    WATER = (33, 66, 114)  # A3: 再降5%更深 (原35,70,120)
    WOOD_TRUNK = (84, 59, 37)  # A3: +4亮度增强对比 (原80,57,35)
    WOOD_LEAF_DARK = (33, 69, 30)  # A3: 再降10%增强对比 (原37,73,34)
    WOOD_LEAF_LIGHT = (79, 125, 39)  # A3: +4亮度增强对比 (原75,121,36)
    BUILDING_WINDOW = (87, 121, 160)  # A3: +4亮度增强对比 (原83,117,156)
    BUILDING_DOOR = (103, 68, 40)  # A3: +4亮度增强对比 (原99,65,37)
    BLOOD = (140, 20, 20)  # *** 保持不变！排除去饱和 ***


@dataclass(slots=True)
class PaletteSet:
    """一套完整调色板（区分阵营）"""

    is_allies: bool
    helmet: tuple[int, int, int]
    uniform: tuple[int, int, int]
    uniform_dark: tuple[int, int, int]
    weapon: tuple[int, int, int]
    weapon_metal: tuple[int, int, int]
    boots: tuple[int, int, int]

    @classmethod
    def allies(cls) -> PaletteSet:
        return cls(
            is_allies=True,
            helmet=CCPalette.ALLIES_HELMET.value,
            uniform=CCPalette.ALLIES_UNIFORM.value,
            uniform_dark=(55, 63, 22),
            weapon=(75, 65, 55),
            weapon_metal=(110, 110, 115),
            boots=(55, 42, 30),
        )

    @classmethod
    def axis(cls) -> PaletteSet:
        return cls(
            is_allies=False,
            helmet=CCPalette.AXIS_HELMET.value,
            uniform=CCPalette.AXIS_UNIFORM.value,
            uniform_dark=(65, 73, 60),
            weapon=(80, 70, 60),
            weapon_metal=(105, 105, 110),
            boots=(45, 38, 28),
        )


# ============================================================
# 2. PixelCanvas — 像素画布操作
# ============================================================


class PixelCanvas:
    """
    像素画布 — 提供像素级绘图操作。

    这是核心引擎：所有精灵都在这个画布上逐像素绘制。
    使用numpy数组作为后端以获得最佳性能。
    """

    def __init__(self, width: int, height: int, bg: tuple[int, int, int] | None = None):
        import numpy as np

        self.width = width
        self.height = height
        self._bg = bg or (0, 0, 0, 0)
        if len(self._bg) == 3:
            self._bg = (*self._bg, 0)
        self._pixels: np.ndarray = np.full((height, width, 4), self._bg, dtype=np.uint8)

    @property
    def pixels(self) -> np.ndarray:
        return self._pixels

    def set_pixel(self, x: int, y: int, color: tuple[int, ...]) -> None:
        """设置单个像素"""
        if 0 <= x < self.width and 0 <= y < self.height:
            if len(color) == 3:
                self._pixels[y, x] = (*color, 255)
            else:
                self._pixels[y, x] = color

    def get_pixel(self, x: int, y: int) -> tuple[int, int, int, int]:
        """获取像素"""
        if 0 <= x < self.width and 0 <= y < self.height:
            px = self._pixels[y, x]
            return (int(px[0]), int(px[1]), int(px[2]), int(px[3]))
        return (0, 0, 0, 0)

    def fill_rect(self, x: int, y: int, w: int, h: int, color: tuple[int, ...]) -> None:
        """填充矩形"""
        r = max(0, y)
        r2 = min(self.height, y + h)
        c = max(0, x)
        c2 = min(self.width, x + w)
        if len(color) == 3:
            color = (*color, 255)
        self._pixels[r:r2, c:c2] = color

    def fill_circle(self, cx: int, cy: int, radius: int, color: tuple[int, ...]) -> None:
        """填充圆（改进版：无锯齿）"""
        import numpy as np

        if len(color) == 3:
            color = (*color, 255)
        yy, xx = np.ogrid[: self.height, : self.width]
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        mask = dist <= radius
        aa_mask = (dist > radius) & (dist <= radius + 1)
        alpha = (radius + 1 - dist[aa_mask]) * 255
        existing = self._pixels[aa_mask].astype(float)
        new_c = np.array(color, dtype=float)
        blend = existing + (new_c - existing) * (alpha[:, None] / 255.0)
        self._pixels[aa_mask] = np.clip(blend, 0, 255).astype(np.uint8)
        self._pixels[mask & ~aa_mask] = color

    def fill_ellipse(self, cx: int, cy: int, rx: int, ry: int, color: tuple[int, ...]) -> None:
        """填充椭圆"""
        import numpy as np

        if len(color) == 3:
            color = (*color, 255)
        yy, xx = np.ogrid[: self.height, : self.width]
        if rx == 0 or ry == 0:
            return
        dist = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        mask = dist <= 1.0
        self._pixels[mask] = color

    def draw_line(
        self, x0: int, y0: int, x1: int, y1: int, color: tuple[int, ...], thickness: int = 1
    ) -> None:
        """画线（Bresenham改进版）"""
        if len(color) == 3:
            color = (*color, 255)
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        t = thickness // 2
        while True:
            for ty in range(-t, t + 1):
                for tx in range(-t, t + 1):
                    if tx * tx + ty * ty <= t * t:
                        self.set_pixel(x0 + tx, y0 + ty, color)

            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
            y0 += sy

    def draw_outline_rect(
        self, x: int, y: int, w: int, h: int, color: tuple[int, ...], thickness: int = 1
    ) -> None:
        """矩形描边"""
        self.fill_rect(x, y, w, thickness, color)
        self.fill_rect(x, y + h - thickness, w, thickness, color)
        self.fill_rect(x, y, thickness, h, color)
        self.fill_rect(x + w - thickness, y, thickness, h, color)

    def to_surface(self):
        """转换为pygame Surface"""
        import pygame

        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        rgb = self._pixels[:, :, :3].swapaxes(0, 1)
        pygame.surfarray.blit_array(surf, rgb)
        alpha_arr = self._pixels[:, :, 3].swapaxes(0, 1).copy()
        pygame.surfarray.pixels_alpha(surf)[:, :] = alpha_arr
        return surf

    def copy(self) -> PixelCanvas:
        """复制画布"""
        new = PixelCanvas.__new__(PixelCanvas)
        new.width = self.width
        new.height = self.height
        new._pixels = self._pixels.copy()
        new._bg = self._bg
        return new


# ============================================================
# 3. 噪点/抖动工具 — 增加像素艺术质感
# ============================================================


def add_noise(canvas: PixelCanvas, intensity: float = 15, area: tuple | None = None) -> None:
    """
    为画布添加噪点 — 增加像素艺术颗粒感。

    intensity: 噪点强度(0-50)，值越大越粗糙
    area: (x,y,w,h) 限制区域，None=全图
    """
    import numpy as np

    if area:
        ax, ay, aw, ah = area
        region = canvas._pixels[ay : ay + ah, ax : ax + aw].copy().astype(np.int16)
    else:
        region = canvas._pixels.astype(np.int16)

    rng = np.random.RandomState(42)
    noise = rng.randint(-int(intensity), int(intensity) + 1, size=region.shape[:2], dtype=np.int16)
    for ch in range(3):
        region[:, :, ch] = np.clip(region[:, :, ch] + noise, 0, 255)

    if area:
        canvas._pixels[ay : ay + ah, ax : ax + aw] = region.astype(np.uint8)
    else:
        canvas._pixels = region.astype(np.uint8)


def dither_pattern(
    canvas: PixelCanvas,
    color_a: tuple,
    color_b: tuple,
    x: int,
    y: int,
    w: int,
    h: int,
) -> None:
    """
    Bayer有序抖动 — 在区域内用两种颜色产生过渡效果。
    用于地形渐变、阴影等。
    """
    bayer = [
        [0, 8, 2, 10],
        [12, 4, 14, 6],
        [3, 11, 1, 9],
        [15, 7, 13, 5],
    ]
    threshold = 16

    for py in range(h):
        for px in range(w):
            bx = (x + px) % 4
            by = (y + py) % 4
            if bayer[by][bx] >= threshold // 2:
                canvas.set_pixel(x + px, y + py, color_b)
            else:
                canvas.set_pixel(x + px, y + py, color_a)
