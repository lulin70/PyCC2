"""Infantry pose drawing helpers (prone topdown / death topdown).

Extracted from infantry_pixel_renderer.py during Phase 2 P0-1 large file split (2026-07-04).
Each function operates on a pygame Surface passed in by the caller; stateless.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pycc2.domain.value_objects.direction import Direction
from pycc2.presentation.rendering.pixel_artist_enums import InfantryType

if TYPE_CHECKING:
    pass


def _draw_infantry_prone_topdown(
    surface,
    direction,
    state,
    frame,
    palette,
    infantry_type,
    body_color,
    weapon_color,
    weapon_metal,
    boots_color,
):
    """Enhanced top-down prone soldier with state-specific details.

    States handled:
    - crawl: crawling animation with moving limbs
    - defend: stable prone firing position
    - attack: aggressive prone advance
    - sneak: low-profile infiltration
    - hide: camouflaged/ambush position

    Args:
        surface: pygame.Surface to draw on (modified in place).
        direction: Facing direction.
        state: Prone state ("crawl"/"defend"/"attack"/"sneak"/"hide").
        frame: Animation frame index.
        palette: Faction color palette dict.
        infantry_type: InfantryType enum.
        body_color: Body uniform color.
        weapon_color: Weapon base color.
        weapon_metal: Weapon metal accent color.
        boots_color: Boots color.

    Returns:
        The modified surface.
    """
    import pygame

    cx, cy = 12, 12

    dir_angles = {
        Direction.NORTH: 270,
        Direction.NORTHEAST: 315,
        Direction.EAST: 0,
        Direction.SOUTHEAST: 45,
        Direction.SOUTH: 90,
        Direction.SOUTHWEST: 135,
        Direction.WEST: 180,
        Direction.NORTHWEST: 225,
    }
    angle = math.radians(dir_angles.get(direction, 0))

    # 根据状态调整参数
    if state == "crawl":
        body_len = 18
        body_w = 4
        helmet_size = 2
        weapon_offset = 6
        # 爬行动画：交替移动肘部/膝盖
        limb_offset = 2 if frame % 2 == 1 else -2
    elif state == "defend":
        body_len = 16
        body_w = 5  # 更宽 - 稳定射击姿态
        helmet_size = 3
        weapon_offset = 8  # 武器向前延伸
        limb_offset = 0  # 稳定姿态
    elif state in ["attack", "sneak"]:
        body_len = 17
        body_w = 3
        helmet_size = 2
        weapon_offset = 7
        limb_offset = 1 if frame % 2 == 1 else -1
    else:  # hide
        body_len = 15
        body_w = 4
        helmet_size = 2
        weapon_offset = 5
        limb_offset = 0
        # 隐蔽时颜色变暗
        body_color = tuple(int(c * 0.85) for c in body_color)

    # 绘制更大的阴影（卧倒时阴影更分散）
    shadow_surface = pygame.Surface((24, 24), pygame.SRCALPHA)
    shadow_width = body_len + 4
    shadow_height = body_w + 2
    shadow_x = cx - shadow_width // 2
    shadow_y = cy - shadow_height // 2
    pygame.draw.ellipse(
        shadow_surface, (0, 0, 0, 35), (shadow_x, shadow_y, shadow_width, shadow_height)
    )
    surface.blit(shadow_surface, (0, 0))

    # 绘制身体（增强的椭圆形）
    body_dark = tuple(max(0, c - 25) for c in body_color)
    for i in range(body_len):
        t = i / max(body_len - 1, 1)
        # 身体中间最宽
        width_factor = 1.0 - abs(t - 0.5) * 0.4
        current_w = int(body_w * width_factor)

        perp_x = int(math.sin(angle) * (t - 0.5) * current_w)
        perp_y = int(-math.cos(angle) * (t - 0.5) * current_w)
        px = cx + int(math.cos(angle) * (i - body_len // 2)) + perp_x
        py = cy + int(math.sin(angle) * (i - body_len // 2)) + perp_y

        # 使用渐变色增加立体感
        if 0 <= px < 24 and 0 <= py < 24:
            color = body_color if i % 3 != 1 else body_dark
            surface.set_at((px, py), color)

    # 绘制钢盔（在身体前端）
    helmet_color = palette.get("helmet", (85, 85, 75))
    helmet_x = cx + int(math.cos(angle) * (body_len // 2 - 2))
    helmet_y = cy + int(math.sin(angle) * (body_len // 2 - 2))
    pygame.draw.circle(surface, helmet_color, (helmet_x, helmet_y), helmet_size)

    # 钢盔高光
    hl_color = tuple(min(255, c + 40) for c in helmet_color)
    hl_x = helmet_x + int(math.cos(angle - math.pi / 4))
    hl_y = helmet_y + int(math.sin(angle - math.pi / 4))
    if 0 <= hl_x < 24 and 0 <= hl_y < 24:
        surface.set_at((hl_x, hl_y), hl_color)

    # 绘制四肢（肘部和膝盖）
    if state == "crawl":
        # 爬行时显示弯曲的肘部
        elbow_dist = body_len // 3
        perp_angle = angle + math.pi / 2
        elbow1_x = (
            cx + int(math.cos(angle) * elbow_dist) + int(math.cos(perp_angle) * (2 + limb_offset))
        )
        elbow1_y = (
            cy + int(math.sin(angle) * elbow_dist) + int(math.sin(perp_angle) * (2 + limb_offset))
        )
        elbow2_x = (
            cx + int(math.cos(angle) * elbow_dist) - int(math.cos(perp_angle) * (2 - limb_offset))
        )
        elbow2_y = (
            cy + int(math.sin(angle) * elbow_dist) - int(math.sin(perp_angle) * (2 - limb_offset))
        )

        pygame.draw.circle(surface, body_dark, (elbow1_x, elbow1_y), 1)
        pygame.draw.circle(surface, body_dark, (elbow2_x, elbow2_y), 1)

        # 膝盖
        knee_dist = -body_len // 4
        knee1_x = (
            cx + int(math.cos(angle) * knee_dist) + int(math.cos(perp_angle) * (2 - limb_offset))
        )
        knee1_y = (
            cy + int(math.sin(angle) * knee_dist) + int(math.sin(perp_angle) * (2 - limb_offset))
        )
        knee2_x = (
            cx + int(math.cos(angle) * knee_dist) - int(math.cos(perp_angle) * (2 + limb_offset))
        )
        knee2_y = (
            cy + int(math.sin(angle) * knee_dist) - int(math.sin(perp_angle) * (2 + limb_offset))
        )

        pygame.draw.circle(surface, boots_color, (knee1_x, knee1_y), 1)
        pygame.draw.circle(surface, boots_color, (knee2_x, knee2_y), 1)

    elif state == "defend":
        # 防御姿态：双腿分开稳定
        leg_spread = 4
        perp_angle = angle + math.pi / 2
        foot1_x = (
            cx - int(math.cos(angle) * (body_len // 3)) + int(math.cos(perp_angle) * leg_spread)
        )
        foot1_y = (
            cy - int(math.sin(angle) * (body_len // 3)) + int(math.sin(perp_angle) * leg_spread)
        )
        foot2_x = (
            cx - int(math.cos(angle) * (body_len // 3)) - int(math.cos(perp_angle) * leg_spread)
        )
        foot2_y = (
            cy - int(math.sin(angle) * (body_len // 3)) - int(math.sin(perp_angle) * leg_spread)
        )

        pygame.draw.circle(surface, boots_color, (foot1_x, foot1_y), 1)
        pygame.draw.circle(surface, boots_color, (foot2_x, foot2_y), 1)

    # 绘制武器
    tip_x = cx + int(math.cos(angle) * (body_len // 2 + weapon_offset))
    tip_y = cy + int(math.sin(angle) * (body_len // 2 + weapon_offset))
    weapon_start_x = cx + int(math.cos(angle) * (body_len // 4))
    weapon_start_y = cy + int(math.sin(angle) * (body_len // 4))

    w_width = 2 if infantry_type == InfantryType.MG else 1
    pygame.draw.line(
        surface, weapon_color, (weapon_start_x, weapon_start_y), (tip_x, tip_y), w_width
    )

    # 机枪双脚架
    if infantry_type == InfantryType.MG:
        bipod_x = tip_x - int(math.cos(angle) * 2)
        bipod_y = tip_y - int(math.sin(angle) * 2)
        perp = angle + math.pi / 2
        pygame.draw.line(
            surface,
            weapon_metal,
            (bipod_x, bipod_y),
            (bipod_x + int(math.cos(perp) * 2), bipod_y + int(math.sin(perp) * 2)),
            1,
        )
        pygame.draw.line(
            surface,
            weapon_metal,
            (bipod_x, bipod_y),
            (bipod_x - int(math.cos(perp) * 2), bipod_y - int(math.sin(perp) * 2)),
            1,
        )

    # 绘制装备（背包在背部可见）
    equipment_color = palette.get("equipment", tuple(max(0, c - 20) for c in body_color))
    pack_x = cx - int(math.cos(angle) * 3)
    pack_y = cy - int(math.sin(angle) * 3)
    pygame.draw.ellipse(surface, equipment_color, (pack_x - 2, pack_y - 1, 4, 3))

    return surface


def _draw_infantry_death_topdown(
    surface,
    direction,
    frame,
    palette,
    infantry_type,
    body_color,
    helmet_color,
    weapon_color,
    boots_color,
):
    """Pure top-down death animation - flattened body, no weapon after frame 0.

    Args:
        surface: pygame.Surface to draw on (modified in place).
        direction: Facing direction.
        frame: Death animation frame (0=just hit, 1=folding, 2=down, 3=darkened).
        palette: Faction color palette dict.
        infantry_type: InfantryType enum (unused but kept for API symmetry).
        body_color: Body uniform color.
        helmet_color: Helmet color.
        weapon_color: Weapon base color (only used at frame 0).
        boots_color: Boots color (unused but kept for API symmetry).

    Returns:
        The modified surface.
    """
    import pygame

    cx, cy = 12, 12

    if frame == 0:
        pygame.draw.circle(surface, helmet_color, (cx, cy - 2), 3)
        pygame.draw.ellipse(surface, body_color, (cx - 4, cy, 8, 5))
        dir_angles = {
            Direction.NORTH: 270,
            Direction.NORTHEAST: 315,
            Direction.EAST: 0,
            Direction.SOUTHEAST: 45,
            Direction.SOUTH: 90,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 180,
            Direction.NORTHWEST: 225,
        }
        angle = math.radians(dir_angles.get(direction, 0))
        wx = cx + int(math.cos(angle) * 10)
        wy = cy + int(math.sin(angle) * 10)
        pygame.draw.line(surface, weapon_color, (cx, cy), (wx, wy), 1)

    elif frame == 1:
        pygame.draw.circle(surface, helmet_color, (cx, cy - 1), 2)
        pygame.draw.ellipse(surface, body_color, (cx - 5, cy + 1, 10, 4))

    elif frame == 2:
        ground_y = cy + 6
        pygame.draw.ellipse(surface, body_color, (cx - 7, ground_y - 2, 14, 3))
        pygame.draw.circle(surface, helmet_color, (cx - 6, ground_y), 2)

    else:
        ground_y = cy + 8
        pygame.draw.ellipse(surface, body_color, (cx - 8, ground_y - 2, 16, 3))
        pygame.draw.circle(surface, helmet_color, (cx - 7, ground_y), 2)
        pygame.draw.circle(surface, (140, 20, 20), (cx + 2, ground_y), 1)

        dark_overlay = pygame.Surface((24, 24), pygame.SRCALPHA)
        dark_overlay.fill((100, 100, 100, 150))
        surface.blit(dark_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    return surface
