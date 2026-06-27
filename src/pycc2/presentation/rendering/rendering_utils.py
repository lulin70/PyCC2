"""渲染工具函数集合，提供虚线、几何绘制等通用辅助。"""

from __future__ import annotations

from typing import Any

import pygame


def draw_dashed_line(
    surface: Any,
    color: tuple[int, ...],
    start: tuple[int, int],
    end: tuple[int, int],
    dash_length: int = 6,
    gap_length: int = 4,
) -> None:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dist = (dx * dx + dy * dy) ** 0.5
    if dist < 1:
        return

    nx, ny = dx / dist, dy / dist
    drawn = 0.0
    drawing = True

    while drawn < dist:
        seg_len = dash_length if drawing else gap_length
        seg_len = min(seg_len, dist - drawn)

        if drawing:
            sx = start[0] + nx * drawn
            sy = start[1] + ny * drawn
            ex = start[0] + nx * (drawn + seg_len)
            ey = start[1] + ny * (drawn + seg_len)
            pygame.draw.line(surface, color[:3], (int(sx), int(sy)), (int(ex), int(ey)), 2)

        drawn += seg_len
        drawing = not drawing
