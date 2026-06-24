"""Unit sprite generator for CC2-style infantry/vehicle rendering."""

from __future__ import annotations

import math
from dataclasses import dataclass

from pycc2.presentation.rendering.pixel_canvas import (
    PaletteSet,
    PixelCanvas,
    add_noise,
)

# ============================================================
# 4. 单位精灵生成器
# ============================================================


@dataclass
class UnitSpriteSpec:
    """单位精灵规格"""

    faction: str
    unit_type: str
    direction: int
    size: int = 24
    is_moving: bool = False
    frame_offset: int = 0
    state: str = "idle"


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

        palette = PaletteSet.allies() if spec.faction == "allies" else PaletteSet.axis()
        canvas = PixelCanvas(spec.size, spec.size, bg=(0, 0, 0, 0))

        prone_states = {"crawl", "defend", "attack", "sneak", "hide"}
        if spec.state in prone_states and spec.unit_type not in ("TANK",):
            UnitSpriteGenerator._draw_infantry_prone(
                canvas, palette, spec.direction, spec.frame_offset
            )
        else:
            func = gen_map.get(spec.unit_type, UnitSpriteGenerator._draw_infantry)
            func(canvas, palette, spec.direction, spec.frame_offset)

        add_noise(canvas, intensity=8)

        return canvas

    @staticmethod
    def _draw_infantry_prone(c: PixelCanvas, pal: PaletteSet, direction: int, frame: int) -> None:
        """Top-down prone soldier — elongated oval lying flat on ground."""
        sz = c.width
        cx, cy = sz // 2, sz // 2

        dir_angles = [270, 292.5, 315, 337.5, 0, 22.5, 45, 67.5]
        angle = math.radians(dir_angles[direction % 8])

        body_len = sz - 4
        body_w = 3

        for i in range(body_len):
            t = i / max(body_len - 1, 1)
            perp_x = int(math.sin(angle) * (t - 0.5) * body_w)
            perp_y = int(-math.cos(angle) * (t - 0.5) * body_w)
            px = cx + int(math.cos(angle) * (i - body_len // 2)) + perp_x
            py = cy + int(math.sin(angle) * (i - body_len // 2)) + perp_y
            if 0 <= px < sz and 0 <= py < sz:
                c.set_pixel(px, py, pal.uniform)

        tip_x = cx + int(math.cos(angle) * (body_len // 2 + 4))
        tip_y = cy + int(math.sin(angle) * (body_len // 2 + 4))
        c.draw_line(cx, cy, tip_x, tip_y, pal.weapon, thickness=1)

    @staticmethod
    def _draw_infantry(c: PixelCanvas, pal: PaletteSet, direction: int, frame: int) -> None:
        """Pure top-down infantry — what you see looking STRAIGHT DOWN."""
        sz = c.width
        cx, cy = sz // 2, sz // 2

        helmet_r = max(2, sz // 8)
        c.fill_circle(cx, cy - 2, helmet_r, pal.helmet)
        hl_color = (
            min(255, pal.helmet[0] + 40),
            min(255, pal.helmet[1] + 40),
            min(255, pal.helmet[2] + 40),
        )
        c.set_pixel(cx - 1, cy - 3, hl_color)

        body_w, body_h = sz // 3, sz // 5
        c.fill_ellipse(cx - body_w // 2, cy, body_w, body_h, pal.uniform)

        dir_angles = [270, 292.5, 315, 337.5, 0, 22.5, 45, 67.5]
        angle = math.radians(dir_angles[direction % 8])

        weapon_len = sz // 2 + 2
        wx = cx + int(math.cos(angle) * weapon_len)
        wy = cy + int(math.sin(angle) * weapon_len)
        c.draw_line(cx, cy, wx, wy, pal.weapon, thickness=max(1, sz // 24))

        leg_len = sz // 6
        lx1 = cx + int(math.cos(angle + math.pi) * leg_len)
        ly1 = cy + int(math.sin(angle + math.pi) * leg_len)
        lx2 = cx + int(math.cos(angle + math.pi + 0.3) * leg_len * 0.7)
        ly2 = cy + int(math.sin(angle + math.pi + 0.3) * leg_len * 0.7)
        c.set_pixel(lx1, ly1, pal.boots)
        c.set_pixel(lx2, ly2, pal.boots)

    @staticmethod
    def _draw_tank(c: PixelCanvas, pal: PaletteSet, direction: int, frame: int) -> None:
        sz = c.width
        cx, cy = sz // 2, sz // 2

        if pal.is_allies:
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

        helmet_r = max(2, sz // 8)
        c.fill_circle(cx, cy - 2, helmet_r, pal.helmet)
        hl_color = (
            min(255, pal.helmet[0] + 40),
            min(255, pal.helmet[1] + 40),
            min(255, pal.helmet[2] + 40),
        )
        c.set_pixel(cx - 1, cy - 3, hl_color)

        body_w, body_h = sz // 3, sz // 5
        c.fill_ellipse(cx - body_w // 2, cy, body_w, body_h, pal.uniform)

        dir_angles = [270, 292.5, 315, 337.5, 0, 22.5, 45, 67.5]
        angle = math.radians(dir_angles[direction % 8])

        weapon_len = sz // 2 + 4
        wx = cx + int(math.cos(angle) * weapon_len)
        wy = cy + int(math.sin(angle) * weapon_len)
        c.draw_line(cx, cy, wx, wy, pal.weapon, thickness=max(1, sz // 24))

        scope_x = cx + int(math.cos(angle) * 2)
        scope_y = cy + int(math.sin(angle) * 2)
        c.fill_rect(scope_x - 1, scope_y - 1, 3, 2, (20, 20, 20))

        leg_len = sz // 6
        lx1 = cx + int(math.cos(angle + math.pi) * leg_len)
        ly1 = cy + int(math.sin(angle + math.pi) * leg_len)
        lx2 = cx + int(math.cos(angle + math.pi + 0.3) * leg_len * 0.7)
        ly2 = cy + int(math.sin(angle + math.pi + 0.3) * leg_len * 0.7)
        c.set_pixel(lx1, ly1, pal.boots)
        c.set_pixel(lx2, ly2, pal.boots)

    @staticmethod
    def _draw_medic(c: PixelCanvas, pal: PaletteSet, direction: int, frame: int) -> None:
        sz = c.width
        cx, cy = sz // 2, sz // 2

        helmet_r = max(2, sz // 8)
        c.fill_circle(cx, cy - 2, helmet_r, pal.helmet)
        hl_color = (
            min(255, pal.helmet[0] + 40),
            min(255, pal.helmet[1] + 40),
            min(255, pal.helmet[2] + 40),
        )
        c.set_pixel(cx - 1, cy - 3, hl_color)

        red_cross = (200, 40, 40)
        c.set_pixel(cx - 1, cy - 3, red_cross)

        body_w, body_h = sz // 3, sz // 5
        c.fill_ellipse(cx - body_w // 2, cy, body_w, body_h, pal.uniform)

        dir_angles = [270, 292.5, 315, 337.5, 0, 22.5, 45, 67.5]
        angle = math.radians(dir_angles[direction % 8])

        perp_angle = angle + math.pi / 2
        rx = cx + int(math.cos(perp_angle) * 3)
        ry = cy + int(math.sin(perp_angle) * 3)
        c.set_pixel(rx, ry - 1, red_cross)
        c.set_pixel(rx, ry, red_cross)
        c.set_pixel(rx, ry + 1, red_cross)
        c.set_pixel(rx - 1, ry, red_cross)
        c.set_pixel(rx + 1, ry, red_cross)

        weapon_len = sz // 2
        wx = cx + int(math.cos(angle) * weapon_len)
        wy = cy + int(math.sin(angle) * weapon_len)
        c.draw_line(cx, cy, wx, wy, pal.weapon, thickness=max(1, sz // 24))

        leg_len = sz // 6
        lx1 = cx + int(math.cos(angle + math.pi) * leg_len)
        ly1 = cy + int(math.sin(angle + math.pi) * leg_len)
        lx2 = cx + int(math.cos(angle + math.pi + 0.3) * leg_len * 0.7)
        ly2 = cy + int(math.sin(angle + math.pi + 0.3) * leg_len * 0.7)
        c.set_pixel(lx1, ly1, pal.boots)
        c.set_pixel(lx2, ly2, pal.boots)

    @staticmethod
    def _draw_mg_squad(c: PixelCanvas, pal: PaletteSet, direction: int, frame: int) -> None:
        sz = c.width
        cx, cy = sz // 2, sz // 2

        helmet_r = max(3, sz // 7)
        c.fill_circle(cx, cy - 2, helmet_r, pal.helmet)
        hl_color = (
            min(255, pal.helmet[0] + 40),
            min(255, pal.helmet[1] + 40),
            min(255, pal.helmet[2] + 40),
        )
        c.set_pixel(cx - 1, cy - 3, hl_color)

        body_w, body_h = sz // 2.5, sz // 4
        c.fill_ellipse(cx - body_w // 2, cy, body_w, body_h, pal.uniform)

        dir_angles = [270, 292.5, 315, 337.5, 0, 22.5, 45, 67.5]
        angle = math.radians(dir_angles[direction % 8])

        weapon_len = sz // 2 + 4
        wx = cx + int(math.cos(angle) * weapon_len)
        wy = cy + int(math.sin(angle) * weapon_len)
        c.draw_line(cx, cy, wx, wy, pal.weapon_metal, thickness=max(2, sz // 12))

        mid_x = (cx + wx) // 2
        mid_y = (cy + wy) // 2
        c.draw_line(mid_x - 1, mid_y, mid_x + 1, mid_y, (80, 70, 55), 1)

        pack_offset_x = int(math.cos(angle + math.pi) * 3)
        pack_offset_y = int(math.sin(angle + math.pi) * 3)
        c.fill_rect(cx + pack_offset_x - 2, cy + pack_offset_y - 1, 4, 3, (80, 70, 55))

        leg_len = sz // 6
        lx1 = cx + int(math.cos(angle + math.pi) * leg_len)
        ly1 = cy + int(math.sin(angle + math.pi) * leg_len)
        lx2 = cx + int(math.cos(angle + math.pi + 0.3) * leg_len * 0.7)
        ly2 = cy + int(math.sin(angle + math.pi + 0.3) * leg_len * 0.7)
        c.set_pixel(lx1, ly1, pal.boots)
        c.set_pixel(lx2, ly2, pal.boots)

    @staticmethod
    def _draw_commander(c: PixelCanvas, pal: PaletteSet, direction: int, frame: int) -> None:
        sz = c.width
        cx, cy = sz // 2, sz // 2

        helmet_r = max(3, sz // 7)
        c.fill_circle(cx, cy - 2, helmet_r, pal.helmet)
        hl_color = (
            min(255, pal.helmet[0] + 40),
            min(255, pal.helmet[1] + 40),
            min(255, pal.helmet[2] + 40),
        )
        c.set_pixel(cx - 1, cy - 3, hl_color)

        insignia_color = (220, 190, 50)
        c.set_pixel(cx, cy - 3, insignia_color)

        body_w, body_h = sz // 3, sz // 5
        c.fill_ellipse(cx - body_w // 2, cy, body_w, body_h, pal.uniform)

        dir_angles = [270, 292.5, 315, 337.5, 0, 22.5, 45, 67.5]
        angle = math.radians(dir_angles[direction % 8])

        pistol_len = sz // 4
        px = cx + int(math.cos(angle) * pistol_len)
        py = cy + int(math.sin(angle) * pistol_len)
        c.draw_line(cx, cy, px, py, pal.weapon_metal, thickness=max(1, sz // 24))

        rank_x = cx + int(math.cos(angle + math.pi / 2) * 3)
        rank_y = cy + int(math.sin(angle + math.pi / 2) * 3)
        c.set_pixel(rank_x, rank_y, (200, 170, 50))

        leg_len = sz // 6
        lx1 = cx + int(math.cos(angle + math.pi) * leg_len)
        ly1 = cy + int(math.sin(angle + math.pi) * leg_len)
        lx2 = cx + int(math.cos(angle + math.pi + 0.3) * leg_len * 0.7)
        ly2 = cy + int(math.sin(angle + math.pi + 0.3) * leg_len * 0.7)
        c.set_pixel(lx1, ly1, pal.boots)
        c.set_pixel(lx2, ly2, pal.boots)
