from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ============================================================
# 1. 调色板 — CC2风格军事色调
# ============================================================


class CCPalette(Enum):
    """Close Combat 2 风格军事调色板"""

    ALLIES_HELMET = (85, 107, 47)
    ALLIES_UNIFORM = (120, 140, 90)
    ALLIES_SKIN = (222, 184, 135)
    ALLIES_WEAPON = (75, 65, 55)
    ALLIES_METAL = (110, 110, 115)

    AXIS_HELMET = (55, 58, 50)
    AXIS_UNIFORM = (75, 72, 65)
    AXIS_SKIN = (218, 180, 132)
    AXIS_WEAPON = (80, 70, 60)
    AXIS_METAL = (105, 105, 110)

    GRASS_LIGHT = (96, 143, 48)
    GRASS_DARK = (68, 112, 34)
    DIRT = (166, 138, 95)
    ROAD = (149, 126, 94)
    WATER = (64, 120, 172)
    WOOD_TRUNK = (101, 67, 33)
    WOOD_LEAF_DARK = (34, 85, 37)
    WOOD_LEAF_LIGHT = (52, 120, 52)

    BUILDING_WALL = (95, 92, 88)
    BUILDING_ROOF = (70, 68, 65)
    BUILDING_WINDOW = (180, 210, 220)
    BUILDING_DOOR = (60, 45, 35)
    BUILDING_SHADOW = (50, 48, 45)

    BLOOD = (139, 0, 0)
    MUZZLE_FLASH = (255, 230, 130)
    SMOKE = (160, 160, 155)
    SELECTION_GLOW = (255, 220, 80)


@dataclass(slots=True)
class PaletteSet:
    """一套完整调色板（区分阵营）"""

    helmet: tuple[int, int, int]
    uniform: tuple[int, int, int]
    uniform_dark: tuple[int, int, int]
    skin: tuple[int, int, int]
    skin_shadow: tuple[int, int, int]
    weapon: tuple[int, int, int]
    weapon_metal: tuple[int, int, int]
    boots: tuple[int, int, int]

    @classmethod
    def allies(cls) -> PaletteSet:
        return cls(
            helmet=CCPalette.ALLIES_HELMET.value,
            uniform=CCPalette.ALLIES_UNIFORM.value,
            uniform_dark=(90, 110, 65),
            skin=CCPalette.ALLIES_SKIN.value,
            skin_shadow=(195, 160, 115),
            weapon=CCPalette.ALLIES_WEAPON.value,
            weapon_metal=CCPalette.ALLIES_METAL.value,
            boots=(55, 42, 30),
        )

    @classmethod
    def axis(cls) -> PaletteSet:
        return cls(
            helmet=CCPalette.AXIS_HELMET.value,
            uniform=CCPalette.AXIS_UNIFORM.value,
            uniform_dark=(55, 55, 48),
            skin=CCPalette.AXIS_SKIN.value,
            skin_shadow=(190, 155, 110),
            weapon=CCPalette.AXIS_WEAPON.value,
            weapon_metal=CCPalette.AXIS_METAL.value,
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
    def pixels(self):
        return self._pixels  # type: ignore[return-value]

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
            return tuple(self._pixels[y, x])  # type: ignore[return-value]
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


# ============================================================
# 4. 单位精灵生成器
# ============================================================


@dataclass
class UnitSpriteSpec:
    """单位精灵规格"""

    faction: str
    unit_type: str
    direction: int
    size: int = 56
    is_moving: bool = False
    frame_offset: int = 0


class UnitSpriteGenerator:
    """
    单位精灵生成器 — 生成CC2风格的像素士兵。

    关键设计原则：
    - 每个像素都经过精心设计位置
    - 有明确的轮廓线和阴影
    - 不同unit_type有明显视觉差异
    - 8方向朝向通过旋转/重绘实现
    """

    @staticmethod
    def generate(spec: UnitSpriteSpec) -> PixelCanvas:
        gen_map = {
            "INFANTRY_SQUAD": UnitSpriteGenerator._draw_infantry,
            "MACHINE_GUN_SQUAD": UnitSpriteGenerator._draw_mg_squad,
            "COMMANDER": UnitSpriteGenerator._draw_commander,
            "TANK": UnitSpriteGenerator._draw_tank,
            "SNIPER_TEAM": UnitSpriteGenerator._draw_sniper,
            "MEDIC_TEAM": UnitSpriteGenerator._draw_medic,
        }
        func = gen_map.get(spec.unit_type, UnitSpriteGenerator._draw_infantry)

        palette = PaletteSet.allies() if spec.faction == "allies" else PaletteSet.axis()
        canvas = PixelCanvas(spec.size, spec.size, bg=(0, 0, 0, 0))

        func(canvas, palette, spec.direction, spec.frame_offset)

        add_noise(canvas, intensity=8)

        return canvas

    @staticmethod
    def _draw_infantry(c: PixelCanvas, pal: PaletteSet, direction: int, frame: int) -> None:
        """
        绘制步兵精灵。

        设计（56x56画布，中心为脚底）：
        ┌─────────────────┐
        │    ○ 头盔(圆)   │  y=8-14
        │    ● 头部(圆)   │  y=14-20
        │   ╭──╮ 制服躯干 │  y=20-36 (梯形上窄下宽)
        │   │  │          │
        │   ╰──╯ 腿部    │  y=36-48 (两条分开腿)
        │   ╱  ╲          │
        │  步枪 →→       │  y=22-38 (右侧斜向)
        └─────────────────┘
        """
        sz = c.width
        cx = sz // 2

        helmet_r = 7
        hy = 10
        c.fill_circle(cx, hy - 2, helmet_r, pal.helmet)
        c.fill_circle(cx, hy - 3, helmet_r - 1, tuple(max(0, v - 20) for v in pal.helmet))

        c.draw_line(
            cx - helmet_r + 1,
            hy - 3,
            cx + helmet_r - 1,
            hy - 3,
            tuple(max(0, v - 25) for v in pal.helmet),
            1,
        )

        head_r = 5
        c.fill_circle(cx, hy + 3, head_r, pal.skin)
        c.fill_circle(cx - 1, hy + 2, head_r - 1, pal.skin_shadow)

        body_top_w = 9
        body_bot_w = 12
        body_top_y = hy + 9
        body_h = 17

        for row in range(body_h):
            progress = row / body_h
            bw = int(
                body_top_w + (body_top_w - body_top_w) * 0.3 + (body_bot_w - body_top_w) * progress
            )
            by = body_top_y + row
            left = cx - bw // 2
            mid_color = pal.uniform
            edge_color = pal.uniform_dark

            c.fill_rect(left + 1, by, int(bw) - 2, 1, mid_color)
            if row % 3 == 0:
                c.set_pixel(left, by, edge_color)
                c.set_pixel(left + bw - 1, by, edge_color)

        belt_y = body_top_y + 13
        c.fill_rect(cx - 5, belt_y, 10, 1, pal.uniform_dark)
        ep_y = body_top_y + 2
        c.fill_rect(
            cx + 4,
            ep_y,
            2,
            2,
            (200, 180, 50) if pal.helmet == CCPalette.ALLIES_HELMET.value else (40, 40, 40),
        )

        leg_top_y = body_top_y + body_h
        leg_sep = 5
        leg_w = 4
        leg_h = 10

        ll_x = cx - leg_sep // 2 - leg_w
        for ly in range(leg_h):
            lw = leg_w - (ly // 3)
            c.fill_rect(ll_x, leg_top_y + ly, max(2, lw), 1, pal.uniform_dark)
        boot_y = leg_top_y + leg_h
        c.fill_rect(ll_x - 1, boot_y, max(2, leg_w) + 2, 3, pal.boots)

        rl_x = cx + leg_sep // 2
        for ly in range(leg_h):
            lw = leg_w - (ly // 3)
            c.fill_rect(rl_x, leg_top_y + ly, max(2, lw), 1, pal.uniform_dark)
        c.fill_rect(rl_x - 1, boot_y, max(2, leg_w) + 2, 3, pal.boots)

        gun_x = cx + 10
        gun_top_y = hy + 12
        gun_len = 20
        gun_angle = -0.15

        gx0, gy0 = gun_x, gun_top_y
        gx1 = gun_x + int(gun_len * math.cos(gun_angle))
        gy1 = gun_top_y + int(gun_len * math.sin(gun_angle))
        c.draw_line(gx0, gy0, gx1, gy1, pal.weapon_metal, 2)
        c.draw_line(gx0 + 1, gy0, gx1 + 1, gy1, pal.weapon, 1)

        stock_x = gun_x - 2
        stock_y = gun_top_y + 8
        c.fill_rect(stock_x, stock_y, 6, 3, (139, 90, 43))
        c.draw_line(stock_x, stock_y + 3, gun_x - 1, gun_top_y + 12, pal.weapon_metal, 1)

        dir_angles = [0, 45, 90, 135, 180, 225, 270, 315]
        angle_rad = math.radians(dir_angles[direction % 8])
        arr_base_y = hy - helmet_r - 3
        arr_len = 4
        tip_x = cx + int(math.cos(angle_rad) * arr_len)
        tip_y = arr_base_y + int(math.sin(angle_rad) * arr_len)
        perp = angle_rad + math.pi / 2
        p1x = tip_x - int(math.cos(perp) * 2)
        p1y = tip_y - int(math.sin(perp) * 2)
        p2x = tip_x + int(math.cos(perp) * 2)
        p2y = tip_y + int(math.sin(perp) * 2)
        c.set_pixel(int(tip_x), int(tip_y), (255, 255, 200))

    @staticmethod
    def _draw_tank(c: PixelCanvas, pal: PaletteSet, direction: int, frame: int) -> None:
        sz = c.width
        cx, cy = sz // 2, sz // 2

        if pal.helmet == CCPalette.ALLIES_HELMET.value:
            body_color = (85, 107, 47)
            dark_color = (60, 80, 30)
            turret_color = (100, 125, 55)
            track_color = (45, 45, 45)
        else:
            body_color = (55, 58, 50)
            dark_color = (40, 42, 38)
            turret_color = (70, 73, 65)
            track_color = (35, 35, 35)

        track_h = sz // 4
        c.fill_rect(2, sz - track_h - 1, 4, track_h, track_color)
        c.fill_rect(sz - 6, sz - track_h - 1, 4, track_h, track_color)

        body_top = sz // 3
        for row in range(body_top, sz - track_h - 1):
            t = (row - body_top) / max(sz - track_h - 1 - body_top, 1)
            left = int(4 + t * 2)
            right = int(sz - 4 - t * 2)
            c.fill_rect(left, row, right - left, 1, body_color)

        tw, th = sz // 2, sz // 3
        tx = (sz - tw) // 2
        ty = 2
        c.fill_rect(tx, ty, tw, th, turret_color)
        c.fill_ellipse(tx + 1, ty + 1, tw - 2, th - 2, dark_color)

        dir_idx = direction % 8
        gun_lengths = [th, th + 2, th + 4, th + 3, th + 2, th + 3, th + 4, th + 2]
        gl = gun_lengths[dir_idx]
        dx = [0, 2, 4, 2, 0, -2, -4, -2][dir_idx]
        dy = [-1, -1, 0, 1, 1, 1, 0, -1][dir_idx]
        gx = cx + dx * 2
        gy = cy - 2
        c.draw_line(gx, gy, gx + dx * (gl // 3), gy + dy * (gl // 3), (30, 30, 30), 2)

    @staticmethod
    def _draw_sniper(c: PixelCanvas, pal: PaletteSet, direction: int, frame: int) -> None:
        sz = c.width
        cx, cy = sz // 2, sz // 2

        helmet = pal.helmet
        uniform = pal.uniform
        skin = pal.skin

        head_cx = cx + 1
        head_cy = cy - sz // 4
        c.fill_circle(head_cx, head_cy, sz // 6, helmet)
        c.fill_circle(head_cx, head_cy + 1, sz // 7, skin)

        scope_x = head_cx + sz // 8
        c.fill_rect(scope_x - 1, head_cy - 1, 3, 2, (20, 20, 20))

        body_top = head_cy + sz // 5
        body_bot = sz - 2
        body_l = cx - sz // 3
        body_r = cx + sz // 3
        for row in range(body_top, body_bot):
            t = (row - body_top) / max(body_bot - body_top, 1)
            sl = int(body_l + t * 1)
            sr = int(body_r - t * 1)
            c.fill_rect(sl, row, sr - sl, 1, uniform)

        gun_y = body_top + 2
        dir_idx = direction % 8
        gun_dx = [0, 3, 5, 3, 0, -3, -5, -3][dir_idx]
        gun_dy = [-1, -1, 0, 1, 1, 1, 0, -1][dir_idx]
        c.draw_line(cx - 2, gun_y, cx - 2 + gun_dx, gun_y + gun_dy, (60, 50, 40), 2)
        c.fill_rect(cx - 4, gun_y - 1, 3, 3, (80, 55, 30))
        bx = cx + gun_dx * 2
        by = gun_y + gun_dy
        c.draw_line(bx, by, bx + gun_dx * 2, by + gun_dy, (40, 35, 30), 1)

    @staticmethod
    def _draw_medic(c: PixelCanvas, pal: PaletteSet, direction: int, frame: int) -> None:
        sz = c.width
        cx, cy = sz // 2, sz // 2

        if pal.helmet == CCPalette.ALLIES_HELMET.value:
            helmet = (220, 220, 200)
            uniform = pal.uniform
            skin = pal.skin
        else:
            helmet = (100, 105, 95)
            uniform = pal.uniform
            skin = pal.skin

        red_cross = (200, 40, 40)

        c.fill_circle(cx, cy - sz // 4, sz // 5, helmet)
        c.fill_circle(cx, cy - sz // 4 + 1, sz // 6, skin)
        c.fill_rect(cx - 1, cy - sz // 4 - 2, 3, 1, red_cross)
        c.fill_rect(cx, cy - sz // 4 - 3, 1, 3, red_cross)

        body_top = cy - sz // 6
        body_bot = sz - 2
        body_l = cx - sz // 4
        body_r = cx + sz // 4
        for row in range(body_top, body_bot):
            t = (row - body_top) / max(body_bot - body_top, 1)
            sl = int(body_l + t * (sz // 8))
            sr = int(body_r - t * (sz // 8))
            c.fill_rect(sl, row, sr - sl, 1, uniform)

        leg_w = sz // 6
        leg_sep = sz // 5
        c.fill_rect(cx - leg_sep - leg_w // 2, body_bot, leg_w, sz - body_bot, uniform)
        c.fill_rect(cx + leg_sep - leg_w // 2, body_bot, leg_w, sz - body_bot, uniform)

        armband_x = body_l + 1
        armband_y = body_top + sz // 5
        c.fill_rect(armband_x, armband_y, 3, 4, red_cross)
        c.fill_rect(armband_x + 1, armband_y + 1, 1, 2, (255, 255, 255))

        kit_x = body_r - 4
        kit_y = body_top + sz // 4
        c.fill_rect(kit_x, kit_y, 3, 3, (180, 180, 180))
        c.fill_rect(kit_x + 1, kit_y + 1, 1, 1, red_cross)

    @staticmethod
    def _draw_mg_squad(c: PixelCanvas, pal: PaletteSet, direction: int, frame: int) -> None:
        """
        绘制MG机枪组。

        与步兵的区别：
        - 更宽的身躯（两人并排暗示）
        - 双管武器造型
        - 三脚架底座
        - 更深的姿势（蹲姿）
        """
        sz = c.width
        cx = sz // 2

        helmet_r = 8
        hy = 12
        c.fill_circle(cx, hy - 2, helmet_r, pal.helmet)
        c.fill_circle(cx, hy - 3, helmet_r - 1, tuple(max(0, v - 18) for v in pal.helmet))

        c.fill_circle(cx, hy + 4, 5, pal.skin)

        body_w = 15
        body_h = 14
        body_top_y = hy + 10

        for row in range(body_h):
            progress = row / body_h
            bw = int(body_w * (1.0 - progress * 0.2))
            by = body_top_y + row
            left = cx - bw // 2
            c.fill_rect(left, by, bw, 1, pal.uniform)
            if row % 4 == 0:
                c.set_pixel(left, by, pal.uniform_dark)
                c.set_pixel(left + bw - 1, by, pal.uniform_dark)

        pack_y = body_top_y + 3
        c.fill_rect(cx - 6, pack_y, 5, 5, (80, 70, 55))
        c.draw_outline_rect(cx - 6, pack_y, 5, 5, (60, 50, 40), 1)

        mg_x = cx + 9
        mg_top = hy + 10
        mg_len = 18

        c.draw_line(mg_x, mg_top, mg_x + mg_len, mg_top + 2, pal.weapon_metal, 3)
        c.draw_line(mg_x + 1, mg_top + 3, mg_x + mg_len, mg_top + 5, pal.weapon_metal, 3)
        c.fill_rect(mg_x + 2, mg_top + 1, mg_len - 4, 4, (100, 80, 60))

        tripod_y = body_top_y + body_h
        c.draw_line(cx - 4, tripod_y, cx - 8, tripod_y + 8, pal.weapon_metal, 1)
        c.draw_line(cx + 4, tripod_y, cx + 8, tripod_y + 8, pal.weapon_metal, 1)
        c.fill_rect(cx - 9, tripod_y + 7, 18, 2, (70, 65, 55))

        leg_y = tripod_y + 2
        c.fill_rect(cx - 7, leg_y, 4, 6, pal.uniform_dark)
        c.fill_rect(cx + 3, leg_y, 4, 6, pal.uniform_dark)
        c.fill_rect(cx - 8, leg_y + 5, 5, 2, pal.boots)
        c.fill_rect(cx + 2, leg_y + 5, 5, 2, pal.boots)

        dir_angles = [0, 45, 90, 135, 180, 225, 270, 315]
        angle_rad = math.radians(dir_angles[direction % 8])
        base_y = hy - helmet_r - 3
        tip_x = cx + int(math.cos(angle_rad) * 4)
        tip_y = base_y + int(math.sin(angle_rad) * 4)
        c.set_pixel(int(tip_x), int(tip_y), (255, 255, 200))

    @staticmethod
    def _draw_commander(c: PixelCanvas, pal: PaletteSet, direction: int, frame: int) -> None:
        """
        绘制指挥官。

        与普通步兵的区别：
        - 军帽(平顶非半圆)
        - 双筒望远镜/望远镜挂在胸前
        - 站姿更挺拔
        - 可能有一根指挥棒或手枪
        """
        sz = c.width
        cx = sz // 2

        hat_w = 11
        hat_h = 5
        hat_y = 5
        c.fill_rect(cx - hat_w // 2, hat_y, hat_w, hat_h, pal.helmet)
        c.fill_rect(
            cx - hat_w // 2,
            hat_y + hat_h - 1,
            hat_w,
            1,
            tuple(max(0, v - 20) for v in pal.helmet),
        )
        insignia_y = hat_y + 1
        c.fill_rect(cx - 1, insignia_y, 3, 2, (220, 190, 50))

        head_y = hat_y + hat_h + 1
        c.fill_circle(cx, head_y + 3, 5, pal.skin)
        c.fill_circle(cx - 1, head_y + 2, 4, pal.skin_shadow)

        body_top_y = head_y + 9
        body_h = 19
        body_top_w = 10
        body_bot_w = 11

        for row in range(body_h):
            progress = row / body_h
            bw = int(body_top_w + (body_bot_w - body_top_w) * progress * 0.7)
            by = body_top_y + row
            left = cx - bw // 2
            c.fill_rect(left, by, bw, 1, pal.uniform)

        rank_y = body_top_y + 3
        c.fill_rect(cx + 4, rank_y, 3, 3, (200, 170, 50))
        c.fill_rect(cx - 5, body_top_y + 14, 10, 1, pal.uniform_dark)

        binoc_y = body_top_y + 7
        binoc_x = cx - 6
        c.fill_rect(binoc_x, binoc_y, 6, 3, (40, 40, 45))
        c.fill_rect(binoc_x - 1, binoc_y + 1, 2, 1, (180, 180, 190))
        c.fill_rect(binoc_x + 3, binoc_y + 1, 2, 1, (180, 180, 190))
        c.draw_line(binoc_x + 3, binoc_y - 2, cx - 2, body_top_y + 4, (139, 115, 65), 1)

        pistol_x = cx + 8
        pistol_y = body_top_y + 15
        c.fill_rect(pistol_x, pistol_y, 6, 4, pal.weapon_metal)
        c.fill_rect(pistol_x + 5, pistol_y + 1, 3, 2, (40, 35, 30))

        leg_top_y = body_top_y + body_h
        leg_sep = 5
        leg_w = 4
        leg_h = 11

        for side in [-1, 1]:
            lx = cx + (leg_sep // 2) * side - leg_w // 2
            for ly in range(leg_h):
                lw = leg_w - (ly // 4)
                c.fill_rect(lx, leg_top_y + ly, max(2, lw), 1, pal.uniform_dark)
            boot_y = leg_top_y + leg_h
            c.fill_rect(lx - 1, boot_y, max(2, leg_w) + 2, 3, pal.boots)

        dir_angles = [0, 45, 90, 135, 180, 225, 270, 315]
        angle_rad = math.radians(dir_angles[direction % 8])
        tip_x = cx + int(math.cos(angle_rad) * 4)
        tip_y = hat_y - 2 + int(math.sin(angle_rad) * 4)
        c.set_pixel(int(tip_x), int(tip_y), (255, 255, 200))


# ============================================================
# 5. 地形瓦片生成器
# ============================================================


class TerrainTileGenerator:
    """
    地形瓦片生成器 — 生成CC2风格的地形tile。

    特点：
    - 多层细节（基础色+纹理+高光+阴影）
    - 自然不规则感（不是完美的几何形状）
    - 可配置大小（32/48/64px自适应）
    """

    @staticmethod
    def generate_grass(size: int, variant: int = 0) -> PixelCanvas:
        """生成草地瓦片"""
        c = PixelCanvas(size, size)

        base = CCPalette.GRASS_LIGHT.value if variant % 2 == 0 else CCPalette.GRASS_DARK.value
        dark = CCPalette.GRASS_DARK.value

        c.fill_rect(0, 0, size, size, base)

        rng = random.Random(123 + variant)
        grass_count = max(15, size * size // 20)
        for _ in range(grass_count):
            gx = rng.randint(1, size - 2)
            gy = rng.randint(1, size - 2)
            gr = rng.randint(1, max(2, size // 24))
            c.fill_circle(gx, gy, gr, dark)

        for _ in range(max(3, size // 16)):
            lx = rng.randint(2, size - 3)
            ly = rng.randint(2, size - 3)
            lh = rng.randint(2, max(3, size // 12))
            angle = rng.uniform(-0.3, 0.3)
            ex = lx + int(lh * math.cos(angle))
            ey = ly + int(lh * math.sin(angle))
            c.draw_line(lx, ly, ex, ey, (dark[0] - 15, dark[1] - 12, dark[2] - 10), 1)

        edge_color = tuple(max(0, v - 20) for v in base)
        for i in range(max(1, size // 16)):
            c.draw_outline_rect(i, i, size - i * 2, size - i * 2, edge_color, 1)

        add_noise(c, intensity=6)
        return c

    @staticmethod
    def generate_road(size: int, orientation: str = "horizontal") -> PixelCanvas:
        """生成道路瓦片"""
        c = PixelCanvas(size, size)

        c.fill_rect(0, 0, size, size, CCPalette.DIRT.value)

        road_color = CCPalette.ROAD.value
        road_margin = max(3, size // 10)

        if orientation == "horizontal":
            c.fill_rect(0, size // 2 - road_margin // 2, size, road_margin, road_color)
            rut_y1 = size // 2 - road_margin // 4
            rut_y2 = size // 2 + road_margin // 4
            rut_color = tuple(max(0, v - 20) for v in road_color)
            c.fill_rect(0, rut_y1, size, max(1, size // 32), rut_color)
            c.fill_rect(0, rut_y2, size, max(1, size // 32), rut_color)
            rng = random.Random(77)
            for _ in range(max(5, size // 8)):
                sx = rng.randint(road_margin, size - road_margin)
                sy = rng.randint(size // 2 - road_margin // 2, size // 2 + road_margin // 2)
                sr = rng.randint(1, max(2, size // 40))
                c.fill_circle(sx, sy, sr, (rut_color[0] + 20, rut_color[1] + 15, rut_color[2] + 10))
        else:
            c.fill_rect(size // 2 - road_margin // 2, 0, road_margin, size, road_color)

        edge_color = CCPalette.DIRT.value
        for i in range(road_margin):
            alpha = i / road_margin
            blended = tuple(
                int(edge_color[j] * (1 - alpha) + road_color[j] * alpha) for j in range(3)
            )
            if orientation == "horizontal":
                c.set_pixel(i, size // 2, blended)
                c.set_pixel(size - 1 - i, size // 2, blended)
            else:
                c.set_pixel(size // 2, i, blended)
                c.set_pixel(size // 2, size - 1 - i, blended)

        add_noise(c, intensity=10)
        return c

    @staticmethod
    def generate_woods(size: int, density: str = "medium") -> PixelCanvas:
        """生成树林瓦片"""
        c = PixelCanvas(size, size)

        c.fill_rect(0, 0, size, size, CCPalette.GRASS_DARK.value)

        trunk_color = CCPalette.WOOD_TRUNK.value
        leaf_dark = CCPalette.WOOD_LEAF_DARK.value
        leaf_light = CCPalette.WOOD_LEAF_LIGHT.value

        if density == "light":
            trees = [(size // 4, size // 3, size // 5), (size * 3 // 4, size * 2 // 3, size // 6)]
        elif density == "dense":
            trees = [
                (size // 5, size // 4, size // 4),
                (size * 2 // 5, size // 5, size // 5),
                (size * 3 // 5, size * 3 // 5, size // 4),
                (size * 4 // 5, size * 2 // 3, size // 5),
                (size // 2, size * 3 // 4, size // 6),
            ]
        else:
            trees = [(size // 4, size // 3, size // 4), (size * 3 // 4, size * 2 // 3, size // 5)]

        for tx, ty, tr in trees:
            tw = max(3, tr // 5)
            th = max(6, tr // 3)
            c.fill_rect(tx - tw // 2, ty + tr // 2, tw, th, trunk_color)
            c.draw_line(
                tx - tw // 2,
                ty + tr // 2,
                tx - tw // 2,
                ty + tr // 2 + th,
                tuple(max(0, v - 20) for v in trunk_color),
                1,
            )

            layers = 3
            for layer in range(layers):
                lr = tr - layer * (tr // 6)
                ly_offset = -layer * (tr // 8)
                lc = leaf_dark if layer % 2 == 0 else leaf_light
                c.fill_circle(tx, ty + ly_offset, lr, lc)
                hl_r = lr // 2
                c.fill_circle(
                    tx - lr // 4,
                    ty + ly_offset - lr // 4,
                    hl_r,
                    tuple(min(255, v + 35) for v in lc),
                )
                sh_r = lr // 3
                c.fill_circle(
                    tx + lr // 4,
                    ty + ly_offset + lr // 4,
                    sh_r,
                    tuple(max(0, v - 25) for v in lc),
                )

        for tx, ty, tr in trees:
            shadow_r = tr // 2
            shadow_y = ty + tr // 2 + max(6, tr // 3)
            c.fill_circle(tx, shadow_y, shadow_r, (40, 55, 30))

        add_noise(c, intensity=5)
        return c

    @staticmethod
    def generate_building(size: int, building_type: str = "solid") -> PixelCanvas:
        """生成建筑瓦片"""
        c = PixelCanvas(size, size)

        wall = CCPalette.BUILDING_WALL.value
        roof = CCPalette.BUILDING_ROOF.value
        window = CCPalette.BUILDING_WINDOW.value
        door = CCPalette.BUILDING_DOOR.value
        shadow = CCPalette.BUILDING_SHADOW.value

        margin = max(2, size // 16)

        if building_type == "solid":
            c.fill_rect(margin, margin, size - margin * 2, size - margin * 2, wall)

            roof_margin = margin - max(1, size // 32)
            c.fill_rect(
                roof_margin, roof_margin, size - roof_margin * 2, size - roof_margin * 2, roof
            )

            shadow_w = max(2, size // 16)
            for i in range(shadow_w):
                shade = tuple(int(wall[j] * (1 - i / shadow_w * 0.4)) for j in range(3))
                c.fill_rect(
                    size - margin - shadow_w + i,
                    margin + i,
                    1,
                    size - margin * 2 - i * 2,
                    shade,
                )

            win_sz = max(6, size // 8)
            win_margin = max(4, size // 8)
            c.fill_rect(margin + win_margin, margin + win_margin, win_sz, win_sz, (60, 60, 65))
            c.draw_outline_rect(
                margin + win_margin,
                margin + win_margin,
                win_sz,
                win_sz,
                (80, 80, 85),
                1,
            )
            c.fill_rect(
                size - margin - win_margin - win_sz,
                margin + win_margin * 2,
                win_sz,
                win_sz,
                (60, 60, 65),
            )
            c.draw_outline_rect(
                size - margin - win_margin - win_sz,
                margin + win_margin * 2,
                win_sz,
                win_sz,
                (80, 80, 85),
                1,
            )

        else:
            inner_margin = margin + max(2, size // 20)
            c.fill_rect(margin, margin, size - margin * 2, size - margin * 2, wall)
            c.fill_rect(
                inner_margin,
                inner_margin,
                size - inner_margin * 2,
                size - inner_margin * 2,
                tuple(min(255, v + 25) for v in wall),
            )

            door_w = max(6, size // 8)
            door_h = max(10, size // 6)
            door_x = size // 2 - door_w // 2
            door_y = size - margin - door_h
            c.fill_rect(door_x, door_y, door_w, door_h, (35, 28, 22))
            c.draw_outline_rect(door_x, door_y, door_w, door_h, door, 1)

            win_sz = max(6, size // 8)
            c.fill_rect(inner_margin + 2, inner_margin + 2, win_sz, win_sz, window)
            c.fill_rect(
                size - inner_margin - win_sz - 2,
                inner_margin + 4,
                win_sz,
                win_sz,
                window,
            )
            c.draw_outline_rect(
                inner_margin + 2,
                inner_margin + 2,
                win_sz,
                win_sz,
                (100, 100, 110),
                1,
            )
            c.draw_outline_rect(
                size - inner_margin - win_sz - 2,
                inner_margin + 4,
                win_sz,
                win_sz,
                (100, 100, 110),
                1,
            )

            roof_margin = margin - 1
            c.fill_rect(
                roof_margin,
                roof_margin,
                size - roof_margin * 2,
                size // 2 - roof_margin,
                roof,
            )
            eave_color = tuple(max(0, v - 15) for v in roof)
            c.fill_rect(
                roof_margin,
                size // 2 - roof_margin - 1,
                size - roof_margin * 2,
                2,
                eave_color,
            )

        shadow_h = max(2, size // 16)
        c.fill_rect(margin, size - margin, size - margin * 2, shadow_h, shadow)

        add_noise(c, intensity=4)
        return c

    @staticmethod
    def generate_bridge(size: int) -> PixelCanvas:
        """生成桥梁瓦片"""
        c = PixelCanvas(size, size)

        water = CCPalette.WATER.value
        deck = (160, 140, 90)
        rail = (100, 80, 60)

        c.fill_rect(0, 0, size, size, water)
        rng = random.Random(99)
        for _ in range(max(5, size // 10)):
            wx = rng.randint(2, size - 3)
            wy = rng.randint(2, size - 3)
            ww = rng.randint(3, size // 6)
            c.fill_rect(wx, wy, ww, 1, tuple(min(255, v + 25) for v in water))

        deck_margin = max(3, size // 10)
        deck_h = max(size // 5, 8)
        c.fill_rect(0, size // 2 - deck_h // 2, size, deck_h, deck)
        plank_gap = max(8, size // 6)
        for px in range(0, size, plank_gap):
            gap_color = tuple(max(0, v - 25) for v in deck)
            c.fill_rect(px, size // 2 - deck_h // 2, 2, deck_h, gap_color)
        nail_spacing = max(12, size // 5)
        for nx in range(nail_spacing // 2, size, nail_spacing):
            c.set_pixel(nx, size // 2 - deck_h // 2 + 1, (80, 70, 55))
            c.set_pixel(nx, size // 2 + deck_h // 2 - 1, (80, 70, 55))

        rail_y_top = size // 2 - deck_h // 2 - max(2, size // 24)
        rail_y_bot = size // 2 + deck_h // 2 + max(2, size // 24)
        rail_h = max(2, size // 24)
        c.fill_rect(0, rail_y_top, size, rail_h, rail)
        c.fill_rect(0, rail_y_bot, size, rail_h, rail)
        post_spacing = max(10, size // 8)
        for px in range(post_spacing // 2, size, post_spacing):
            c.fill_rect(px, rail_y_top - 1, 2, rail_h + 2, (120, 100, 70))
            c.fill_rect(px, rail_y_bot - 1, 2, rail_h + 2, (120, 100, 70))

        add_noise(c, intensity=5)
        return c

    @staticmethod
    def generate_water(size: int) -> PixelCanvas:
        """生成水面瓦片"""
        c = PixelCanvas(size, size)
        base = CCPalette.WATER.value
        c.fill_rect(0, 0, size, size, base)

        rng = random.Random(44)
        for _ in range(max(8, size // 6)):
            wy = rng.randint(2, size - 3)
            ww = rng.randint(size // 4, size // 2)
            wave_color = tuple(min(255, base[i] + rng.randint(10, 25)) for i in range(3))
            c.fill_rect(0, wy, size, 1, wave_color)

        for _ in range(max(3, size // 12)):
            rx = rng.randint(2, size - 3)
            ry = rng.randint(2, size - 3)
            rr = rng.randint(1, max(2, size // 20))
            c.fill_circle(rx, ry, rr, (140, 185, 220))

        add_noise(c, intensity=3)
        return c

    @staticmethod
    def generate_hedge(size: int) -> PixelCanvas:
        """生成树篱瓦片"""
        c = PixelCanvas(size, size)
        hedge_color = (121, 85, 72)
        c.fill_rect(0, 0, size, size, (139, 119, 66))

        margin = max(2, size // 12)
        c.fill_rect(margin, margin, size - margin * 2, size - margin * 2, hedge_color)

        rng = random.Random(55)
        for _ in range(max(10, size // 4)):
            hx = rng.randint(margin, size - margin - 1)
            hy = rng.randint(margin, size - margin - 1)
            hr = rng.randint(1, max(2, size // 20))
            c.fill_circle(hx, hy, hr, tuple(max(0, v - 15) for v in hedge_color))
            c.fill_circle(hx + 1, hy + 1, hr // 2, tuple(min(255, v + 12) for v in hedge_color))

        c.fill_rect(
            margin,
            margin,
            size - margin * 2,
            max(2, size // 16),
            tuple(min(255, v + 20) for v in hedge_color),
        )

        add_noise(c, intensity=8)
        return c

    @staticmethod
    def generate_wall(size: int) -> PixelCanvas:
        """生成墙壁瓦片"""
        c = PixelCanvas(size, size)
        wall_color = (80, 78, 74)
        c.fill_rect(0, 0, size, size, (139, 119, 66))

        margin = max(3, size // 10)
        c.fill_rect(margin, margin, size - margin * 2, size - margin * 2, wall_color)
        brick_h = max(3, size // 16)
        brick_color = tuple(max(0, v - 8) for v in wall_color)
        mortar_color = tuple(min(255, v + 15) for v in wall_color)
        for by in range(margin, size - margin, brick_h):
            for bx in range(margin, size - margin, max(8, size // 8)):
                offset = (by // brick_h) % 2 * (max(4, size // 16) // 2)
                if (bx + offset) % (max(8, size // 8)) < max(4, size // 16):
                    c.set_pixel(bx, by, mortar_color)
                else:
                    c.set_pixel(bx, by, brick_color)

        c.fill_rect(
            margin,
            margin,
            size - margin * 2,
            max(1, size // 32),
            tuple(min(255, v + 18) for v in wall_color),
        )

        add_noise(c, intensity=6)
        return c

    @staticmethod
    def generate_open(size: int) -> PixelCanvas:
        """生成开阔地瓦片"""
        return TerrainTileGenerator.generate_grass(size, variant=1)

    @staticmethod
    def generate_shallow(size: int) -> PixelCanvas:
        """生成浅水瓦片"""
        c = TerrainTileGenerator.generate_grass(size, variant=2)
        water = CCPalette.WATER.value
        rng = random.Random(33)
        for _ in range(max(5, size // 8)):
            wx = rng.randint(2, size - 3)
            wy = rng.randint(2, size - 3)
            wr = rng.randint(3, max(5, size // 10))
            shallow_color = tuple(
                int(water[i] * 0.5 + CCPalette.GRASS_LIGHT.value[i] * 0.5) for i in range(3)
            )
            c.fill_circle(wx, wy, wr, shallow_color)
        return c

    @staticmethod
    def generate_rough(size: int) -> PixelCanvas:
        """生成崎岖地形瓦片"""
        c = TerrainTileGenerator.generate_grass(size, variant=3)
        rough_color = (160, 140, 90)
        rng = random.Random(66)
        for _ in range(max(8, size // 6)):
            rx = rng.randint(2, size - 3)
            ry = rng.randint(2, size - 3)
            rr = rng.randint(2, max(4, size // 12))
            c.fill_circle(rx, ry, rr, rough_color)
        add_noise(c, intensity=12)
        return c

    @staticmethod
    def generate_crater(size: int, variant: int = 0) -> PixelCanvas:
        c = PixelCanvas(size, size, bg=(90, 75, 60))
        cx, cy = size // 2, size // 2
        rng = random.Random(variant * 137 + 42)

        r = size // 3
        c.fill_ellipse(cx - r, cy - r, r * 2, r * 2, (65, 52, 40))
        inner_r = r // 2
        c.fill_ellipse(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2, (50, 40, 32))

        for _ in range(size // 2):
            angle = rng.uniform(0, 2 * math.pi)
            dist = r + rng.randint(-2, 3)
            px = int(cx + math.cos(angle) * dist)
            py = int(cy + math.sin(angle) * dist)
            if 0 <= px < size and 0 <= py < size:
                shade = rng.randint(35, 55)
                c.set_pixel(px, py, (shade, shade - 10, shade - 20))

        for _ in range(size // 4):
            rx = rng.randint(2, size - 3)
            ry = rng.randint(2, size - 3)
            rock_color = (rng.randint(70, 110), rng.randint(65, 100), rng.randint(55, 85))
            c.set_pixel(rx, ry, rock_color)
            if rng.random() > 0.5:
                c.set_pixel(rx + 1, ry, rock_color)

        return c

    @staticmethod
    def generate_swamp(size: int, variant: int = 0) -> PixelCanvas:
        c = PixelCanvas(size, size, bg=(60, 80, 50))
        rng = random.Random(variant * 199 + 7)

        for _ in range(size // 2):
            wx = rng.randint(1, size - 2)
            wy = rng.randint(1, size - 2)
            wr = rng.randint(1, 3)
            shade = rng.randint(40, 65)
            g = rng.randint(55, 80)
            c.fill_circle(wx, wy, wr, (shade, g, shade - 15))

        for _ in range(size // 3):
            tx = rng.randint(0, size - 1)
            ty = rng.randint(0, size - 1)
            th = rng.randint(2, 4)
            for i in range(th):
                offset = rng.randint(-1, 1)
                gc = rng.randint(25, 55)
                if 0 <= ty + i < size and 0 <= tx + offset < size:
                    c.set_pixel(tx + offset, ty + i, (gc, gc + 30, gc))

        for _ in range(3):
            bx = rng.randint(3, size - 4)
            by = rng.randint(3, size - 4)
            c.set_pixel(bx, by, (80, 100, 70))
            c.set_pixel(bx + 1, by, (75, 95, 65))

        return c


# ============================================================
# 6. 工厂函数 — 对外统一接口
# ============================================================


def create_unit_sprite(
    faction: str,
    unit_type: str,
    direction: int = 0,
    size: int = 56,
    frame: int = 0,
) -> PixelCanvas:
    """便捷函数：创建单位精灵"""
    spec = UnitSpriteSpec(
        faction=faction,
        unit_type=unit_type,
        direction=direction,
        size=size,
        frame_offset=frame,
    )
    return UnitSpriteGenerator.generate(spec)


def create_terrain_tile(terrain_id: int, size: int = 48) -> PixelCanvas:
    """便捷函数：创建地形瓦片"""
    generators = {
        0: lambda s: TerrainTileGenerator.generate_open(s),
        1: lambda s: TerrainTileGenerator.generate_road(s),
        2: lambda s: TerrainTileGenerator.generate_grass(s, variant=2),
        3: lambda s: TerrainTileGenerator.generate_woods(s, "medium"),
        4: lambda s: TerrainTileGenerator.generate_building(s, "enterable"),
        5: lambda s: TerrainTileGenerator.generate_building(s, "solid"),
        6: lambda s: TerrainTileGenerator.generate_water(s),
        7: lambda s: TerrainTileGenerator.generate_hedge(s),
        8: lambda s: TerrainTileGenerator.generate_wall(s),
        9: lambda s: TerrainTileGenerator.generate_rough(s),
        10: lambda s: TerrainTileGenerator.generate_shallow(s),
        11: lambda s: TerrainTileGenerator.generate_bridge(s),
        12: lambda s: TerrainTileGenerator.generate_crater(s),
        13: lambda s: TerrainTileGenerator.generate_swamp(s),
    }
    gen = generators.get(terrain_id, lambda s: TerrainTileGenerator.generate_open(s))
    return gen(size)
