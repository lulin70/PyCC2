"""
CC2风格正交俯视投影像素艺术生成器

基于2026-05-22 CC2原版截图分析：
- 视角: Orthographic Top-Down (正交俯视，非等距投影)
- 尺寸: 24×24像素 (步兵)
- 风格: 像素级写实，非卡通/非几何形状
- 配色: 深绿/灰绿色军事色调 (低饱和度, CC2精确调色板)
"""

from __future__ import annotations

import logging
import math
import random
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Import extracted enums
from pycc2.domain.value_objects.direction import Direction
from pycc2.domain.entities.unit import Faction
from pycc2.presentation.rendering.pixel_artist_enums import (
    InfantryAnimState,
    InfantryType,
    TankType,
)

# Import extracted color palettes
from pycc2.presentation.rendering.pixel_artist_color_palette import (
    CC2_PALETTE,
    TANK_PALETTES,
    TANK_SIZES,
)

if TYPE_CHECKING:
    pass


class PixelArtist3D:
    """
    CC2风格正交俯视投影像素艺术生成器
    基于原版截图分析的视觉特征

    方向差异化系统:
    - 每个方向(0-7)有独特的外观特征
    - 头盔高光位置随方向变化
    - 身体宽度根据视角调整
    - 武器角度明确区分各方向
    - 阴影偏移增强立体感
    """

    ISOMETRIC_ANGLE = 30
    PIXEL_SCALE = 1

    @staticmethod
    def create_infantry_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
        infantry_type: InfantryType | None = None,
    ):
        """创建步兵精灵 (24×24 px) - 纯俯视图 (Pure Top-Down Orthographic)

        CC2俯视特征:
        - 头盔: 圆形（从上方看到头盔顶部像圆盘）
        - 身体: 椭圆形（肩膀/背部从上方看）
        - 武器: 细线（朝向方向延伸）
        - 腿部: 小点（朝向相反方向，几乎不可见）
        - 无面部、无手臂、无侧视图部件
        """
        import pygame

        if infantry_type is None:
            infantry_type = InfantryType.RIFLEMAN

        surface = pygame.Surface((24, 24), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        faction_key = faction.name.lower()  # Faction is Enum — always has .name
        palette = CC2_PALETTE.get(faction_key, CC2_PALETTE.get("allies"))
        body_color = palette['uniform']
        body_dark = palette['uniform_dark']
        helmet_color = palette['helmet']
        weapon_color = palette['weapon']
        weapon_metal = palette['weapon_metal']
        boots_color = palette['boots']

        prone_states = {'crawl', 'defend', 'attack', 'sneak', 'hide'}
        is_prone = state in prone_states

        if is_prone and state != "die":
            return PixelArtist3D._draw_infantry_prone_topdown(
                surface, direction, state, frame, palette, infantry_type,
                body_color, weapon_color, weapon_metal, boots_color,
            )

        if state == "die":
            return PixelArtist3D._draw_infantry_death_topdown(
                surface, direction, frame, palette, infantry_type,
                body_color, helmet_color, weapon_color, boots_color,
            )

        cx, cy = 12, 12

        if state == "walk":
            walk_offsets = [0, -1, 0, 1]
            offset = walk_offsets[frame % 4]
        else:
            offset = 0

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

        helmet_r = 3
        hx = cx + int(math.cos(angle + math.pi / 2) * offset * 0.3)
        hy = cy - 2 + int(math.sin(angle + math.pi / 2) * offset * 0.3)
        pygame.draw.circle(surface, helmet_color, (hx, hy), helmet_r)

        hl_color = palette.get('helmet_highlight', tuple(min(255, c + 40) for c in helmet_color))
        pygame.draw.circle(surface, hl_color, (hx - 1, hy - 1), 1)

        body_w, body_h = 8, 5
        bx = cx - body_w // 2 + int(math.cos(angle + math.pi / 2) * offset * 0.5)
        by = cy + int(math.sin(angle + math.pi / 2) * offset * 0.5)
        pygame.draw.ellipse(surface, body_color, (bx, by, body_w, body_h))
        pygame.draw.ellipse(surface, body_dark, (bx + 1, by + 1, body_w - 2, body_h - 2))

        weapon_len = 10
        wx = cx + int(math.cos(angle) * weapon_len)
        wy = cy + int(math.sin(angle) * weapon_len)
        weapon_width = 2 if infantry_type in [InfantryType.MG, InfantryType.AT] else 1
        pygame.draw.line(surface, weapon_color, (cx, cy), (wx, wy), weapon_width)

        if infantry_type == InfantryType.MG:
            mid_x = (cx + wx) // 2
            mid_y = (cy + wy) // 2
            pygame.draw.line(surface, weapon_metal, (mid_x - 1, mid_y), (mid_x + 1, mid_y), 1)
        elif infantry_type == InfantryType.OFFICER:
            pistol_len = 5
            px = cx + int(math.cos(angle) * pistol_len)
            py = cy + int(math.sin(angle) * pistol_len)
            pygame.draw.line(surface, weapon_color, (cx, cy), (px, py), 1)
        elif infantry_type == InfantryType.MEDIC:
            red_cross = (220, 40, 40)
            perp_angle = angle + math.pi / 2
            rx = cx + int(math.cos(perp_angle) * 3)
            ry = cy + int(math.sin(perp_angle) * 3)
            pygame.draw.line(surface, red_cross, (rx, ry - 1), (rx, ry + 1), 1)
            pygame.draw.line(surface, red_cross, (rx - 1, ry), (rx + 1, ry), 1)

        leg_len = 4
        lx1 = cx + int(math.cos(angle + math.pi) * leg_len)
        ly1 = cy + int(math.sin(angle + math.pi) * leg_len)
        lx2 = cx + int(math.cos(angle + math.pi + 0.4) * leg_len * 0.7)
        ly2 = cy + int(math.sin(angle + math.pi + 0.4) * leg_len * 0.7)
        pygame.draw.circle(surface, boots_color, (lx1, ly1), 1)
        pygame.draw.circle(surface, boots_color, (lx2, ly2), 1)

        shadow_surface = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 35), (cx - 4, cy + 5, 8, 3))
        surface.blit(shadow_surface, (0, 0))

        if state == "shoot" and frame == 1:
            flash_x = wx + int(math.cos(angle) * 2)
            flash_y = wy + int(math.sin(angle) * 2)
            pygame.draw.ellipse(surface, (255, 255, 100), (flash_x - 2, flash_y - 1, 4, 3))

        if state == "hit":
            overlay = surface.copy()
            overlay.fill((255, 0, 0, 100))
            surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        return surface

    @staticmethod
    def apply_wounded_overlay(surface, hp_ratio: float) -> 'pygame.Surface':
        """根据HP比例添加受伤视觉状态叠加层。

        HP < 50%: 头顶显示小红十字/绷带图标
        HP < 25%: 红色色调叠加

        Args:
            surface: 原始精灵Surface
            hp_ratio: HP比例 (0.0-1.0)

        Returns:
            添加了受伤效果的Surface
        """
        import pygame

        if hp_ratio >= 0.5:
            return surface

        result = surface.copy()
        w, h = result.get_size()

        # HP < 50%: 颜色去饱和 (与灰色混合, 模拟受伤虚弱感)
        desat_alpha = int(255 * (0.3 if hp_ratio < 0.25 else 0.15))
        gray_overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        gray_overlay.fill((128, 128, 128, desat_alpha))
        result.blit(gray_overlay, (0, 0))

        if hp_ratio < 0.25:
            # HP < 25%: 红色色调叠加
            red_overlay = pygame.Surface((w, h), pygame.SRCALPHA)
            red_overlay.fill((180, 0, 0, 70))
            result.blit(red_overlay, (0, 0))

        # HP < 50%: 头顶红十字/绷带图标
        # 绘制3x3红十字
        cross_x = w // 2
        cross_y = 2  # 顶部位置
        red = (220, 40, 40)
        # 竖线
        pygame.draw.line(result, red, (cross_x, cross_y), (cross_x, cross_y + 3), 1)
        # 横线
        pygame.draw.line(result, red, (cross_x - 1, cross_y + 1), (cross_x + 1, cross_y + 1), 1)

        return result

    @staticmethod
    def _get_direction_params(direction: Direction) -> dict:
        """
        获取方向特定的视觉参数 - 增强版（目标: >30%相邻方向像素差异）

        每个方向有独特的视觉特征以区分相邻方向:
        - helmet_highlight_offset: 头盔高光位置偏移
        - body_width_mod: 身体宽度修正 (N/S=-2→6px, NE/SE/SW/NW=-1→7px, E/W=0→8px)
        - body_height_mod: 身体高度修正 (-2 到 +1)
        - weapon_angle_mod: 武器角度修正 (度)
        - shadow_offset: 阴影偏移 (dx, dy)
        - visibility_factor: 可见性因子 (0.0-1.0)
        - helmet_size_mod: 头盔尺寸修正 (-1 到 +1)
        - leg_spread_mod: 腿部张开程度 (0-3)
        - shoulder_tilt: 肩膀倾斜角度 (度)
        - equipment_visibility: 装备可见性 (0.0-1.0)
        - helmet_shape: 头盔形状 ('circle'=N/S, 'oval'=NE/SE/SW/NW, 'side_oval'=E/W)
        - weapon_base_angle: 武器基础角度 (0°/45°/90°/135°/180°/225°/270°/315°)
        """
        params = {
            Direction.NORTH: {
                # 正面视图: 面朝观察者, 武器指向上, 窄身体
                'helmet_highlight_offset': (0, -2),
                'body_width_mod': -2,       # 6px - 最窄(正面)
                'body_height_mod': 1,
                'weapon_angle_mod': -20,
                'shadow_offset': (0, 4),
                'visibility_factor': 1.0,
                'helmet_size_mod': 1,
                'leg_spread_mod': 3,        # 双腿明显分开(正面可见)
                'shoulder_tilt': -10,
                'equipment_visibility': 0.9,
                'helmet_shape': 'circle',    # 正圆(正面)
                'weapon_base_angle': 0,      # 武器朝上(0°)
                'description': '正面视图: 头盔正圆最大可见,肩膀水平,双腿分开,武器指向上方'
            },
            Direction.NORTHEAST: {
                # 右前45°: 3/4视图, 武器45°, 稍宽身体
                'helmet_highlight_offset': (2, -2),
                'body_width_mod': -1,       # 7px - 中等(3/4视角)
                'body_height_mod': 0,
                'weapon_angle_mod': -5,
                'shadow_offset': (-3, 3),
                'visibility_factor': 0.9,
                'helmet_size_mod': 0,
                'leg_spread_mod': 1,        # 一前一后(斜向)
                'shoulder_tilt': -5,
                'equipment_visibility': 0.7,
                'helmet_shape': 'oval',      # 椭圆(3/4视角)
                'weapon_base_angle': 45,     # 武器45°
                'description': '右前45°: 身体旋转,左肩后退,右腿前伸,武器45°角'
            },
            Direction.EAST: {
                # 右侧轮廓: 侧视图, 武器水平右指, 最宽身体
                'helmet_highlight_offset': (3, 0),
                'body_width_mod': 0,        # 8px - 最宽(侧面)
                'body_height_mod': -1,
                'weapon_angle_mod': 15,
                'shadow_offset': (-4, 0),
                'visibility_factor': 0.8,
                'helmet_size_mod': -1,
                'leg_spread_mod': 0,        # 前后排列(侧面)
                'shoulder_tilt': 0,
                'equipment_visibility': 0.5,
                'helmet_shape': 'side_oval', # 侧椭圆(侧面)
                'weapon_base_angle': 90,     # 武器水平右指
                'description': '右侧轮廓: 身体最宽,头盔侧视椭圆,武器水平指向右方'
            },
            Direction.SOUTHEAST: {
                # 右后45°: 3/4背面视图, 武器135°
                'helmet_highlight_offset': (2, 2),
                'body_width_mod': -1,       # 7px - 中等(3/4视角)
                'body_height_mod': -1,
                'weapon_angle_mod': 25,
                'shadow_offset': (-3, -3),
                'visibility_factor': 0.7,
                'helmet_size_mod': -1,
                'leg_spread_mod': 1,        # 一前一后(斜向)
                'shoulder_tilt': 8,
                'equipment_visibility': 0.4,
                'helmet_shape': 'oval',      # 椭圆(3/4视角)
                'weapon_base_angle': 135,    # 武器135°
                'description': '右后45°: 背部开始可见,右肩前进,身体缩短,武器135°角'
            },
            Direction.SOUTH: {
                # 背面视图: 背对观察者, 武器指向下, 窄身体
                'helmet_highlight_offset': (0, 3),
                'body_width_mod': -2,       # 6px - 最窄(背面)
                'body_height_mod': -2,
                'weapon_angle_mod': 35,
                'shadow_offset': (0, -4),
                'visibility_factor': 0.6,
                'helmet_size_mod': 0,
                'leg_spread_mod': 3,        # 双腿明显分开(背面可见)
                'shoulder_tilt': 12,
                'equipment_visibility': 1.0,
                'helmet_shape': 'circle',    # 正圆(背面)
                'weapon_base_angle': 180,    # 武器朝下(180°)
                'description': '背面视图: 头盔/背部可见,武器在肩上指向下方,装备全可见'
            },
            Direction.SOUTHWEST: {
                # 左后45°: 3/4背面视图, 武器225°
                'helmet_highlight_offset': (-2, 2),
                'body_width_mod': -1,       # 7px - 中等(3/4视角)
                'body_height_mod': -1,
                'weapon_angle_mod': 155,
                'shadow_offset': (3, -3),
                'visibility_factor': 0.7,
                'helmet_size_mod': -1,
                'leg_spread_mod': 1,        # 一前一后(斜向)
                'shoulder_tilt': 8,
                'equipment_visibility': 0.4,
                'helmet_shape': 'oval',      # 椭圆(3/4视角)
                'weapon_base_angle': 225,    # 武器225°
                'description': '左后45°: SE镜像,左肩前进,武器225°角'
            },
            Direction.WEST: {
                # 左侧轮廓: 侧视图, 武器水平左指, 最宽身体
                'helmet_highlight_offset': (-3, 0),
                'body_width_mod': 0,        # 8px - 最宽(侧面)
                'body_height_mod': -1,
                'weapon_angle_mod': 165,
                'shadow_offset': (4, 0),
                'visibility_factor': 0.8,
                'helmet_size_mod': -1,
                'leg_spread_mod': 0,        # 前后排列(侧面)
                'shoulder_tilt': 0,
                'equipment_visibility': 0.5,
                'helmet_shape': 'side_oval', # 侧椭圆(侧面)
                'weapon_base_angle': 270,    # 武器水平左指
                'description': '左侧轮廓: E的完全镜像,身体最宽,武器水平指向左方'
            },
            Direction.NORTHWEST: {
                # 左前45°: 3/4视图, 武器315°
                'helmet_highlight_offset': (-2, -2),
                'body_width_mod': -1,       # 7px - 中等(3/4视角)
                'body_height_mod': 0,
                'weapon_angle_mod': 200,
                'shadow_offset': (3, 3),
                'visibility_factor': 0.9,
                'helmet_size_mod': 0,
                'leg_spread_mod': 1,        # 一前一后(斜向)
                'shoulder_tilt': -5,
                'equipment_visibility': 0.7,
                'helmet_shape': 'oval',      # 椭圆(3/4视角)
                'weapon_base_angle': 315,    # 武器315°
                'description': '左前45°: NE完全镜像,右肩后退,武器315°角'
            },
        }
        return params.get(direction, params[Direction.NORTH])

    @staticmethod
    def _get_isometric_offset(direction: Direction) -> tuple:
        """
        计算45°伪3D的方向偏移
        使不同方向看起来有不同的"深度"
        """
        offsets = {
            Direction.NORTH: (0, -2),
            Direction.NORTHEAST: (2, -1),
            Direction.EAST: (3, 0),
            Direction.SOUTHEAST: (2, 1),
            Direction.SOUTH: (0, 2),
            Direction.SOUTHWEST: (-2, 1),
            Direction.WEST: (-3, 0),
            Direction.NORTHWEST: (-2, -1),
        }
        return offsets.get(direction, (0, 0))

    @staticmethod
    def _get_weapon_position(direction, cx, cy) -> tuple:
        """根据方向计算武器位置"""
        length = 10
        angles = {
            Direction.NORTH: 270,
            Direction.NORTHEAST: 315,
            Direction.EAST: 0,
            Direction.SOUTHEAST: 45,
            Direction.SOUTH: 90,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 180,
            Direction.NORTHWEST: 225,
        }
        angle_rad = math.radians(angles.get(direction, 0))

        start = (cx + math.cos(angle_rad) * 3, cy + math.sin(angle_rad) * 3)
        end = (
            cx + math.cos(angle_rad) * (3 + length),
            cy + math.sin(angle_rad) * (3 + length),
        )
        return start, end

    @staticmethod
    def _draw_infantry_weapon(
        surface, direction, infantry_type, cx, cy,
        weapon_color, weapon_metal, weapon_wood, equip_color, equip_dark,
    ):
        """根据步兵类型绘制差异化武器"""
        import pygame

        weapon_start, weapon_end = PixelArtist3D._get_weapon_position(direction, cx, cy)

        if infantry_type == InfantryType.MG:
            # MG：加粗枪管 + 三脚架线条
            pygame.draw.line(surface, weapon_color, weapon_start, weapon_end, 3)
            # 枪管细节线
            mid_x = (weapon_start[0] + weapon_end[0]) / 2
            mid_y = (weapon_start[1] + weapon_end[1]) / 2
            pygame.draw.line(surface, weapon_metal,
                             (int(mid_x) - 1, int(mid_y)), (int(mid_x) + 1, int(mid_y)), 1)
            # 弹药箱 (腰部侧面)
            ammo_box_x = cx + (4 if direction.value <= 4 else -4)
            ammo_box_y = cy + 1
            pygame.draw.rect(surface, equip_color, (ammo_box_x - 2, ammo_box_y - 1, 4, 3))
            pygame.draw.rect(surface, equip_dark, (ammo_box_x - 2, ammo_box_y - 1, 4, 3), 1)
            # 三脚架线条
            tripod_base_x = int(weapon_end[0])
            tripod_base_y = int(weapon_end[1])
            pygame.draw.line(surface, weapon_metal,
                             (tripod_base_x, tripod_base_y),
                             (tripod_base_x - 2, tripod_base_y + 3), 1)
            pygame.draw.line(surface, weapon_metal,
                             (tripod_base_x, tripod_base_y),
                             (tripod_base_x + 2, tripod_base_y + 3), 1)

        elif infantry_type == InfantryType.AT:
            # AT手：火箭筒（长管+肩扛）
            at_length = 12
            angles = {
                Direction.NORTH: 270, Direction.NORTHEAST: 315,
                Direction.EAST: 0, Direction.SOUTHEAST: 45,
                Direction.SOUTH: 90, Direction.SOUTHWEST: 135,
                Direction.WEST: 180, Direction.NORTHWEST: 225,
            }
            angle_rad = math.radians(angles.get(direction, 0))
            at_start = (cx + math.cos(angle_rad) * 2, cy - 2 + math.sin(angle_rad) * 2)
            at_end = (
                cx + math.cos(angle_rad) * (2 + at_length),
                cy - 2 + math.sin(angle_rad) * (2 + at_length),
            )
            pygame.draw.line(surface, weapon_color, at_start, at_end, 3)
            # 火箭筒开口端
            end_x, end_y = int(at_end[0]), int(at_end[1])
            pygame.draw.circle(surface, weapon_metal, (end_x, end_y), 2)
            # 肩扛支撑线
            shoulder_x = int(at_start[0])
            shoulder_y = int(at_start[1])
            pygame.draw.line(surface, weapon_wood,
                             (shoulder_x, shoulder_y),
                             (shoulder_x, shoulder_y + 3), 1)

        elif infantry_type == InfantryType.OFFICER:
            # 军官手枪：更短的武器线条
            pistol_length = 5
            angles = {
                Direction.NORTH: 270, Direction.NORTHEAST: 315,
                Direction.EAST: 0, Direction.SOUTHEAST: 45,
                Direction.SOUTH: 90, Direction.SOUTHWEST: 135,
                Direction.WEST: 180, Direction.NORTHWEST: 225,
            }
            angle_rad = math.radians(angles.get(direction, 0))
            p_start = (cx + math.cos(angle_rad) * 3, cy + math.sin(angle_rad) * 3)
            p_end = (
                cx + math.cos(angle_rad) * (3 + pistol_length),
                cy + math.sin(angle_rad) * (3 + pistol_length),
            )
            pygame.draw.line(surface, weapon_color, p_start, p_end, 2)
            # 手枪握把
            grip_x = int((p_start[0] + p_end[0]) / 2)
            grip_y = int((p_start[1] + p_end[1]) / 2)
            pygame.draw.line(surface, weapon_wood,
                             (grip_x, grip_y), (grip_x, grip_y + 2), 1)

        elif infantry_type == InfantryType.SNIPER:
            # 狙击手：长步枪+瞄准镜线
            sniper_length = 12
            angles = {
                Direction.NORTH: 270, Direction.NORTHEAST: 315,
                Direction.EAST: 0, Direction.SOUTHEAST: 45,
                Direction.SOUTH: 90, Direction.SOUTHWEST: 135,
                Direction.WEST: 180, Direction.NORTHWEST: 225,
            }
            angle_rad = math.radians(angles.get(direction, 0))
            s_start = (cx + math.cos(angle_rad) * 3, cy + math.sin(angle_rad) * 3)
            s_end = (
                cx + math.cos(angle_rad) * (3 + sniper_length),
                cy + math.sin(angle_rad) * (3 + sniper_length),
            )
            pygame.draw.line(surface, weapon_color, s_start, s_end, 2)
            # 枪托
            stock_x = int(s_start[0])
            stock_y = int(s_start[1])
            pygame.draw.line(surface, weapon_wood,
                             (stock_x, stock_y), (stock_x - 1, stock_y + 2), 2)
            # 瞄准镜线 (枪管中部上方小凸起)
            mid_x = int((s_start[0] + s_end[0]) / 2)
            mid_y = int((s_start[1] + s_end[1]) / 2)
            pygame.draw.line(surface, weapon_metal,
                             (mid_x, mid_y), (mid_x, mid_y - 2), 1)
            pygame.draw.circle(surface, weapon_metal, (mid_x, mid_y - 2), 1)

        elif infantry_type == InfantryType.MEDIC:
            # 医疗兵：卡宾枪（短步枪）
            carbine_length = 7
            angles = {
                Direction.NORTH: 270, Direction.NORTHEAST: 315,
                Direction.EAST: 0, Direction.SOUTHEAST: 45,
                Direction.SOUTH: 90, Direction.SOUTHWEST: 135,
                Direction.WEST: 180, Direction.NORTHWEST: 225,
            }
            angle_rad = math.radians(angles.get(direction, 0))
            c_start = (cx + math.cos(angle_rad) * 3, cy + math.sin(angle_rad) * 3)
            c_end = (
                cx + math.cos(angle_rad) * (3 + carbine_length),
                cy + math.sin(angle_rad) * (3 + carbine_length),
            )
            pygame.draw.line(surface, weapon_color, c_start, c_end, 2)
            stock_x = int(c_start[0])
            stock_y = int(c_start[1])
            pygame.draw.line(surface, weapon_wood,
                             (stock_x, stock_y), (stock_x - 1, stock_y + 2), 1)

        elif infantry_type == InfantryType.ENGINEER:
            # 工兵：标准步枪（已有铲子细节在主渲染中）
            pygame.draw.line(surface, weapon_color, weapon_start, weapon_end, 2)
            stock_x = int(weapon_start[0])
            stock_y = int(weapon_start[1])
            pygame.draw.line(surface, weapon_wood,
                             (stock_x, stock_y), (stock_x - 1, stock_y + 2), 2)
            mid_x = int((weapon_start[0] + weapon_end[0]) / 2)
            mid_y = int((weapon_start[1] + weapon_end[1]) / 2)
            pygame.draw.line(surface, weapon_metal,
                             (mid_x - 1, mid_y), (mid_x + 1, mid_y), 1)

        elif infantry_type == InfantryType.SCOUT:
            # 侦察兵：轻武器（冲锋枪/手枪）
            scout_length = 6
            angles = {
                Direction.NORTH: 270, Direction.NORTHEAST: 315,
                Direction.EAST: 0, Direction.SOUTHEAST: 45,
                Direction.SOUTH: 90, Direction.SOUTHWEST: 135,
                Direction.WEST: 180, Direction.NORTHWEST: 225,
            }
            angle_rad = math.radians(angles.get(direction, 0))
            sc_start = (cx + math.cos(angle_rad) * 3, cy + math.sin(angle_rad) * 3)
            sc_end = (
                cx + math.cos(angle_rad) * (3 + scout_length),
                cy + math.sin(angle_rad) * (3 + scout_length),
            )
            pygame.draw.line(surface, weapon_color, sc_start, sc_end, 2)
            grip_x = int((sc_start[0] + sc_end[0]) / 2)
            grip_y = int((sc_start[1] + sc_end[1]) / 2)
            pygame.draw.line(surface, weapon_wood,
                             (grip_x, grip_y), (grip_x, grip_y + 2), 1)

        else:
            # 步枪手：步枪+枪托和枪管细节线
            pygame.draw.line(surface, weapon_color, weapon_start, weapon_end, 2)
            # 枪托
            stock_x = int(weapon_start[0])
            stock_y = int(weapon_start[1])
            pygame.draw.line(surface, weapon_wood,
                             (stock_x, stock_y), (stock_x - 1, stock_y + 2), 2)
            # 枪管细节线
            mid_x = int((weapon_start[0] + weapon_end[0]) / 2)
            mid_y = int((weapon_start[1] + weapon_end[1]) / 2)
            pygame.draw.line(surface, weapon_metal,
                             (mid_x - 1, mid_y), (mid_x + 1, mid_y), 1)
            # 枪口
            pygame.draw.circle(surface, weapon_metal, (int(weapon_end[0]), int(weapon_end[1])), 1)

    @staticmethod
    def _draw_infantry_prone_topdown(
        surface, direction, state, frame, palette, infantry_type,
        body_color, weapon_color, weapon_metal, boots_color,
    ):
        """纯俯视趴姿士兵 — 长椭圆形身体沿朝向方向延伸"""
        import pygame
        import math

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

        body_len = 20
        body_w = 3

        for i in range(body_len):
            t = i / max(body_len - 1, 1)
            perp_x = int(math.sin(angle) * (t - 0.5) * body_w)
            perp_y = int(-math.cos(angle) * (t - 0.5) * body_w)
            px = cx + int(math.cos(angle) * (i - body_len // 2)) + perp_x
            py = cy + int(math.sin(angle) * (i - body_len // 2)) + perp_y
            if 0 <= px < 24 and 0 <= py < 24:
                surface.set_at((px, py), body_color)

        tip_x = cx + int(math.cos(angle) * (body_len // 2 + 4))
        tip_y = cy + int(math.sin(angle) * (body_len // 2 + 4))
        w_width = 2 if infantry_type == InfantryType.MG else 1
        pygame.draw.line(surface, weapon_color, (cx, cy), (tip_x, tip_y), w_width)

        shadow_surface = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 30), (cx - 6, cy - 3, 12, 6))
        surface.blit(shadow_surface, (0, 0))

        return surface

    @staticmethod
    def _draw_infantry_death_topdown(
        surface, direction, frame, palette, infantry_type,
        body_color, helmet_color, weapon_color, boots_color,
    ):
        """纯俯视死亡动画 — 扁平化身体，无武器"""
        import pygame
        import math

        cx, cy = 12, 12

        if frame == 0:
            pygame.draw.circle(surface, helmet_color, (cx, cy - 2), 3)
            pygame.draw.ellipse(surface, body_color, (cx - 4, cy, 8, 5))
            dir_angles = {
                Direction.NORTH: 270, Direction.NORTHEAST: 315,
                Direction.EAST: 0, Direction.SOUTHEAST: 45,
                Direction.SOUTH: 90, Direction.SOUTHWEST: 135,
                Direction.WEST: 180, Direction.NORTHWEST: 225,
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

    @staticmethod
    def create_tank_sprite(
        direction: Direction,
        faction: Faction,
        turret_direction: Direction | None = None,
        state: str = "idle",
        frame: int = 0,
        tank_type: TankType | None = None,
    ):
        """
        创建坦克精灵 - 历史准确性版本，支持尺寸差异化

        支持三种二战诺曼底战役主要坦克:
        - Sherman M4 (美军中型坦克): 36×36px, 圆润车体, 小炮塔, VVSS悬挂
        - Panther Ausf.G (德军中型偏重): 38×38px, 大倾角装甲, 长炮管L/70, 交错负重轮
        - Tiger I (德军超重型坦克): 44×44px, 方正箱体, 大矩形炮塔, 88mm KwK36

        Args:
            direction: 车体朝向
            faction: ALLIES 或 AXIS
            turret_direction: 炮塔朝向 (默认与车体同向)
            state: idle/move/shoot/die
            frame: 动画帧号
            tank_type: 坦克类型 (默认根据阵营自动选择)

        Returns:
            pygame.Surface (带alpha通道, 尺寸根据tank_type变化)
        """
        import pygame

        if turret_direction is None:
            turret_direction = direction

        # 自动选择坦克类型（如果未指定）
        if tank_type is None:
            tank_type = TankType.SHERMAN_M4 if faction == Faction.ALLIES else TankType.PANTHER_AUSFG

        # 根据坦克类型获取差异化尺寸
        tank_w, tank_h = TANK_SIZES[tank_type]

        surface = pygame.Surface((tank_w, tank_h), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        # 获取历史准确性的调色板
        tp = TANK_PALETTES[tank_type]

        # 动态中心点（根据尺寸调整）
        cx, cy = tank_w // 2, tank_h // 2

        # 根据坦克类型调用专门的渲染方法
        if tank_type == TankType.SHERMAN_M4:
            PixelArtist3D._draw_sherman_m4(surface, direction, turret_direction, state, frame, tp, cx, cy)
        elif tank_type == TankType.PANTHER_AUSFG:
            PixelArtist3D._draw_panther_ausfg(surface, direction, turret_direction, state, frame, tp, cx, cy)
        elif tank_type == TankType.TIGER_I:
            PixelArtist3D._draw_tiger_i(surface, direction, turret_direction, state, frame, tp, cx, cy)

        return surface

    @staticmethod
    def create_turret_overlay(
        faction: Faction,
        turret_direction: Direction,
        tank_type: TankType | None = None,
    ):
        """创建独立的炮塔覆盖层精灵 - 纯俯视角度 (TOP-DOWN VIEW!)

        炮塔朝北绘制，然后根据炮塔方向旋转。

        Args:
            faction: ALLIES 或 AXIS
            turret_direction: 炮塔朝向
            tank_type: 坦克类型

        Returns:
            pygame.Surface (带alpha通道, 尺寸根据tank_type变化)
        """
        import pygame

        if tank_type is None:
            tank_type = TankType.SHERMAN_M4 if faction == Faction.ALLIES else TankType.PANTHER_AUSFG

        tank_w, tank_h = TANK_SIZES[tank_type]
        tp = TANK_PALETTES[tank_type]

        overlay_size = max(tank_w, tank_h)
        surface = pygame.Surface((overlay_size, overlay_size), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        cx, cy = overlay_size // 2, overlay_size // 2

        if tank_type == TankType.SHERMAN_M4:
            tw, th = 12, 10
            tx = cx - tw // 2
            ty = cy - th // 2
            pygame.draw.rect(surface, tp['turret_base'], (tx, ty, tw, th), border_radius=3)
            pygame.draw.ellipse(surface, tp['turret_dark'], (tx + 2, ty + 2, tw - 4, th - 4))
            pygame.draw.circle(surface, tp['cupola'], (cx + 2, cy), 2)
            pygame.draw.circle(surface, tp['mg_mount'], (cx - 3, cy - 3), 1)
        elif tank_type == TankType.PANTHER_AUSFG:
            tw, th = 14, 12
            tx = cx - tw // 2
            ty = cy - th // 2
            pygame.draw.rect(surface, tp['turret_base'], (tx, ty, tw, th), border_radius=2)
            pygame.draw.ellipse(surface, tp['turret_dark'], (tx + 3, ty + 3, tw - 6, th - 5))
            schurzen_y = ty + 4
            pygame.draw.line(surface, tp['schurzen'], (tx - 1, schurzen_y), (tx - 1, schurzen_y + 5), 1)
            pygame.draw.line(surface, tp['schurzen'], (tx + tw, schurzen_y), (tx + tw, schurzen_y + 5), 1)
        elif tank_type == TankType.TIGER_I:
            tw, th = 16, 14
            tx = cx - tw // 2
            ty = cy - th // 2
            pygame.draw.rect(surface, tp['turret_base'], (tx, ty, tw, th), border_radius=1)
            pygame.draw.rect(surface, tp['turret_dark'], (tx + 2, ty + 2, tw - 4, th - 4), 1)
            pygame.draw.circle(surface, tp['porte_cupola'], (cx, cy), 3)
            pygame.draw.circle(surface, tp['turret_dark'], (cx, cy), 3, 1)

        gun_length = 12 if tank_type == TankType.SHERMAN_M4 else 16 if tank_type == TankType.PANTHER_AUSFG else 14
        gun_width = 2 if tank_type != TankType.TIGER_I else 3
        gun_end_y = ty - gun_length
        pygame.draw.line(surface, tp['gun_barrel'], (cx, ty), (cx, gun_end_y), gun_width)

        if tank_type == TankType.TIGER_I:
            pygame.draw.circle(surface, (60, 60, 60), (cx, gun_end_y), 3)
        else:
            pygame.draw.rect(surface, (60, 60, 60), (cx - 2, gun_end_y - 1, 4, 2))

        direction_angles = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: -45,
            Direction.EAST: -90,
            Direction.SOUTHEAST: -135,
            Direction.SOUTH: 180,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 90,
            Direction.NORTHWEST: 45,
        }
        angle = direction_angles.get(turret_direction, 0)
        if angle != 0:
            surface = pygame.transform.rotate(surface, angle)

        return surface

    @staticmethod
    def _draw_sherman_m4(
        surface, direction, turret_direction, state, frame, tp, cx, cy
    ):
        """绘制Sherman M4中型坦克 - 纯俯视角度 (TOP-DOWN VIEW!)

        俯视特征:
        - 矩形车体 (从上方看，前后长左右窄)
        - 两侧履带矩形 (4-6px宽)
        - 中心偏前圆形/圆角矩形炮塔
        - 炮管从炮塔延伸向朝向方向 (8-12px长, 2px宽)
        - 车体装甲板接缝线 (1px暗线)
        - 后部引擎甲板 (更暗矩形)
        """
        import pygame

        size = 36

        hull_temp = pygame.Surface((size, size), pygame.SRCALPHA)
        hull_temp.fill((0, 0, 0, 0))
        tcx, tcy = size // 2, size // 2

        hull_w, hull_h = 18, 26
        hull_x = tcx - hull_w // 2
        hull_y = tcy - hull_h // 2

        track_w = 5
        track_h = hull_h + 2
        pygame.draw.rect(hull_temp, tp['track_color'], (hull_x - track_w, hull_y - 1, track_w, track_h))
        pygame.draw.rect(hull_temp, tp['track_color'], (hull_x + hull_w, hull_y - 1, track_w, track_h))

        for ty in range(hull_y - 1, hull_y + track_h, 2):
            pygame.draw.line(hull_temp, (55, 55, 55), (hull_x - track_w, ty), (hull_x, ty), 1)
            pygame.draw.line(hull_temp, (55, 55, 55), (hull_x + hull_w, ty), (hull_x + hull_w + track_w, ty), 1)

        pygame.draw.rect(hull_temp, tp['body_base'], (hull_x, hull_y, hull_w, hull_h))

        seam = tuple(max(0, c - 15) for c in tp['body_dark'])
        pygame.draw.line(hull_temp, seam, (hull_x + 1, hull_y + 7), (hull_x + hull_w - 1, hull_y + 7), 1)
        pygame.draw.line(hull_temp, seam, (hull_x + 1, hull_y + hull_h - 7), (hull_x + hull_w - 1, hull_y + hull_h - 7), 1)
        pygame.draw.line(hull_temp, seam, (tcx, hull_y + 1), (tcx, hull_y + hull_h - 1), 1)

        engine_h = 6
        pygame.draw.rect(hull_temp, tp['body_dark'], (hull_x + 2, hull_y + hull_h - engine_h, hull_w - 4, engine_h))
        for vy in range(hull_y + hull_h - engine_h + 1, hull_y + hull_h - 1, 2):
            pygame.draw.line(hull_temp, seam, (hull_x + 4, vy), (hull_x + hull_w - 4, vy), 1)

        PixelArtist3D._draw_star(hull_temp, tcx, hull_y + hull_h // 2 + 2, 3, tp['white_star'])

        pygame.draw.rect(hull_temp, tp['body_dark'], (hull_x, hull_y, hull_w, hull_h), 1)

        turret_temp = pygame.Surface((size, size), pygame.SRCALPHA)
        turret_temp.fill((0, 0, 0, 0))

        tw, th = 12, 10
        tx = tcx - tw // 2
        ty = tcy - th // 2 - 2
        pygame.draw.rect(turret_temp, tp['turret_base'], (tx, ty, tw, th), border_radius=3)
        pygame.draw.ellipse(turret_temp, tp['turret_dark'], (tx + 2, ty + 2, tw - 4, th - 4))

        pygame.draw.circle(turret_temp, tp['cupola'], (tcx + 2, ty + th // 2), 2)
        pygame.draw.circle(turret_temp, tp['mg_mount'], (tcx - 3, ty + 3), 1)

        gun_length = 12
        gun_end_y = ty - gun_length
        pygame.draw.line(turret_temp, tp['gun_barrel'], (tcx, ty), (tcx, gun_end_y), 2)
        pygame.draw.rect(turret_temp, (60, 60, 60), (tcx - 2, gun_end_y - 1, 4, 2))

        direction_angles = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: -45,
            Direction.EAST: -90,
            Direction.SOUTHEAST: -135,
            Direction.SOUTH: 180,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 90,
            Direction.NORTHWEST: 45,
        }

        hull_angle = direction_angles.get(direction, 0)
        turret_angle = direction_angles.get(turret_direction, 0)

        if hull_angle != 0:
            hull_temp = pygame.transform.rotate(hull_temp, hull_angle)
        if turret_angle != 0:
            turret_temp = pygame.transform.rotate(turret_temp, turret_angle)

        hull_rect = hull_temp.get_rect(center=(cx, cy))
        surface.blit(hull_temp, hull_rect)

        turret_rect = turret_temp.get_rect(center=(cx, cy))
        surface.blit(turret_temp, turret_rect)

        if state == "shoot" and frame == 1:
            direction_vectors = {
                Direction.NORTH: (0, -1),
                Direction.NORTHEAST: (0.707, -0.707),
                Direction.EAST: (1, 0),
                Direction.SOUTHEAST: (0.707, 0.707),
                Direction.SOUTH: (0, 1),
                Direction.SOUTHWEST: (-0.707, 0.707),
                Direction.WEST: (-1, 0),
                Direction.NORTHWEST: (-0.707, -0.707),
            }
            dvx, dvy = direction_vectors.get(turret_direction, (0, -1))
            flash_dist = 18
            flash_x = cx + int(dvx * flash_dist)
            flash_y = cy + int(dvy * flash_dist)
            pygame.draw.ellipse(surface, (255, 255, 100), (flash_x - 4, flash_y - 3, 8, 6))

        if state == "move":
            direction_vectors = {
                Direction.NORTH: (0, 1),
                Direction.NORTHEAST: (-0.707, 0.707),
                Direction.EAST: (-1, 0),
                Direction.SOUTHEAST: (-0.707, -0.707),
                Direction.SOUTH: (0, -1),
                Direction.SOUTHWEST: (0.707, -0.707),
                Direction.WEST: (1, 0),
                Direction.NORTHWEST: (0.707, 0.707),
            }
            dvx, dvy = direction_vectors.get(direction, (0, 1))
            for i in range(3):
                dust_dist = 16 + i * 3
                dust_x = cx + int(dvx * dust_dist)
                dust_y = cy + int(dvy * dust_dist)
                pygame.draw.circle(surface, (139, 119, 66), (dust_x, dust_y), 1 + i % 2)

    @staticmethod
    def _draw_panther_ausfg(
        surface, direction, turret_direction, state, frame, tp, cx, cy
    ):
        """绘制Panther Ausf.G坦克 - 纯俯视角度 (TOP-DOWN VIEW!)

        俯视特征:
        - 更宽的车体矩形
        - 两侧更宽履带矩形
        - 大型弧形炮塔
        - 超长炮管 (75mm KwK42 L/70)
        - Schürzen侧裙甲 (炮塔两侧细线)
        - Dunkelgelb暗黄底色 + 迷彩条纹
        """
        import pygame

        size = 38

        hull_temp = pygame.Surface((size, size), pygame.SRCALPHA)
        hull_temp.fill((0, 0, 0, 0))
        tcx, tcy = size // 2, size // 2

        hull_w, hull_h = 20, 28
        hull_x = tcx - hull_w // 2
        hull_y = tcy - hull_h // 2

        track_w = 6
        track_h = hull_h + 2
        pygame.draw.rect(hull_temp, tp['track_color'], (hull_x - track_w, hull_y - 1, track_w, track_h))
        pygame.draw.rect(hull_temp, tp['track_color'], (hull_x + hull_w, hull_y - 1, track_w, track_h))

        for ty in range(hull_y - 1, hull_y + track_h, 2):
            pygame.draw.line(hull_temp, (48, 48, 48), (hull_x - track_w, ty), (hull_x, ty), 1)
            pygame.draw.line(hull_temp, (48, 48, 48), (hull_x + hull_w, ty), (hull_x + hull_w + track_w, ty), 1)

        pygame.draw.rect(hull_temp, tp['body_base'], (hull_x, hull_y, hull_w, hull_h))

        camo_rng = random.Random(42)
        if camo_rng.random() > 0.5:
            for stripe_y in range(hull_y + 4, hull_y + hull_h - 4, 3):
                stripe_start = camo_rng.randint(hull_x + 2, hull_x + hull_w // 2)
                stripe_len = camo_rng.randint(4, 10)
                pygame.draw.line(hull_temp, tp['camo_red_brown'],
                               (stripe_start, stripe_y), (stripe_start + stripe_len, stripe_y), 1)

        panther_seam = tuple(max(0, c - 18) for c in tp['body_dark'])
        pygame.draw.line(hull_temp, panther_seam, (hull_x + 1, hull_y + 8), (hull_x + hull_w - 1, hull_y + 8), 1)
        pygame.draw.line(hull_temp, panther_seam, (hull_x + 1, hull_y + hull_h - 8), (hull_x + hull_w - 1, hull_y + hull_h - 8), 1)
        pygame.draw.line(hull_temp, panther_seam, (tcx, hull_y + 1), (tcx, hull_y + hull_h - 1), 1)

        engine_h = 7
        pygame.draw.rect(hull_temp, tp['body_dark'], (hull_x + 2, hull_y + hull_h - engine_h, hull_w - 4, engine_h))
        for vy in range(hull_y + hull_h - engine_h + 1, hull_y + hull_h - 1, 2):
            pygame.draw.line(hull_temp, panther_seam, (hull_x + 4, vy), (hull_x + hull_w - 4, vy), 1)

        pygame.draw.rect(hull_temp, tp['exhaust_pipe'], (hull_x + 1, hull_y + hull_h - 5, 3, 2))
        pygame.draw.rect(hull_temp, tp['exhaust_pipe'], (hull_x + 1, hull_y + hull_h - 3, 3, 2))

        PixelArtist3D._draw_iron_cross(hull_temp, tcx, hull_y + hull_h // 2 + 2, tp['iron_cross'])

        pygame.draw.rect(hull_temp, tp['body_dark'], (hull_x, hull_y, hull_w, hull_h), 1)

        turret_temp = pygame.Surface((size, size), pygame.SRCALPHA)
        turret_temp.fill((0, 0, 0, 0))

        tw, th = 14, 12
        tx = tcx - tw // 2
        ty = tcy - th // 2 - 2
        pygame.draw.rect(turret_temp, tp['turret_base'], (tx, ty, tw, th), border_radius=2)
        pygame.draw.ellipse(turret_temp, tp['turret_dark'], (tx + 3, ty + 3, tw - 6, th - 5))

        schurzen_y = ty + 4
        pygame.draw.line(turret_temp, tp['schurzen'], (tx - 1, schurzen_y), (tx - 1, schurzen_y + 5), 1)
        pygame.draw.line(turret_temp, tp['schurzen'], (tx + tw, schurzen_y), (tx + tw, schurzen_y + 5), 1)

        gun_length = 16
        gun_end_y = ty - gun_length
        pygame.draw.line(turret_temp, tp['gun_barrel'], (tcx, ty), (tcx, gun_end_y), 2)
        pygame.draw.rect(turret_temp, (55, 55, 55), (tcx - 2, gun_end_y - 1, 4, 3))

        direction_angles = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: -45,
            Direction.EAST: -90,
            Direction.SOUTHEAST: -135,
            Direction.SOUTH: 180,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 90,
            Direction.NORTHWEST: 45,
        }

        hull_angle = direction_angles.get(direction, 0)
        turret_angle = direction_angles.get(turret_direction, 0)

        if hull_angle != 0:
            hull_temp = pygame.transform.rotate(hull_temp, hull_angle)
        if turret_angle != 0:
            turret_temp = pygame.transform.rotate(turret_temp, turret_angle)

        hull_rect = hull_temp.get_rect(center=(cx, cy))
        surface.blit(hull_temp, hull_rect)

        turret_rect = turret_temp.get_rect(center=(cx, cy))
        surface.blit(turret_temp, turret_rect)

        if state == "shoot" and frame == 1:
            direction_vectors = {
                Direction.NORTH: (0, -1),
                Direction.NORTHEAST: (0.707, -0.707),
                Direction.EAST: (1, 0),
                Direction.SOUTHEAST: (0.707, 0.707),
                Direction.SOUTH: (0, 1),
                Direction.SOUTHWEST: (-0.707, 0.707),
                Direction.WEST: (-1, 0),
                Direction.NORTHWEST: (-0.707, -0.707),
            }
            dvx, dvy = direction_vectors.get(turret_direction, (0, -1))
            flash_dist = 20
            flash_x = cx + int(dvx * flash_dist)
            flash_y = cy + int(dvy * flash_dist)
            pygame.draw.ellipse(surface, (255, 255, 100), (flash_x - 5, flash_y - 4, 10, 8))

        if state == "move":
            direction_vectors = {
                Direction.NORTH: (0, 1),
                Direction.NORTHEAST: (-0.707, 0.707),
                Direction.EAST: (-1, 0),
                Direction.SOUTHEAST: (-0.707, -0.707),
                Direction.SOUTH: (0, -1),
                Direction.SOUTHWEST: (0.707, -0.707),
                Direction.WEST: (1, 0),
                Direction.NORTHWEST: (0.707, 0.707),
            }
            dvx, dvy = direction_vectors.get(direction, (0, 1))
            for i in range(4):
                dust_dist = 18 + i * 3
                dust_x = cx + int(dvx * dust_dist)
                dust_y = cy + int(dvy * dust_dist)
                pygame.draw.circle(surface, (139, 119, 66), (dust_x, dust_y), 1 + i % 2)

    @staticmethod
    def _draw_tiger_i(
        surface, direction, turret_direction, state, frame, tp, cx, cy
    ):
        """绘制Tiger I型重型坦克 - 纯俯视角度 (TOP-DOWN VIEW!)

        俯视特征:
        - 方正宽大车体矩形
        - 超宽履带矩形
        - 大矩形炮塔 (低圆角，方正造型)
        - 88mm KwK36炮管 (粗，3px宽)
        - Portée装甲指挥塔 (炮塔中心)
        - "移动碉堡"外观
        """
        import pygame

        size = 44

        hull_temp = pygame.Surface((size, size), pygame.SRCALPHA)
        hull_temp.fill((0, 0, 0, 0))
        tcx, tcy = size // 2, size // 2

        hull_w, hull_h = 24, 32
        hull_x = tcx - hull_w // 2
        hull_y = tcy - hull_h // 2

        track_w = 6
        track_h = hull_h + 2
        pygame.draw.rect(hull_temp, tp['track_color'], (hull_x - track_w, hull_y - 1, track_w, track_h))
        pygame.draw.rect(hull_temp, tp['track_color'], (hull_x + hull_w, hull_y - 1, track_w, track_h))

        for ty in range(hull_y - 1, hull_y + track_h, 2):
            pygame.draw.line(hull_temp, (42, 42, 42), (hull_x - track_w, ty), (hull_x, ty), 1)
            pygame.draw.line(hull_temp, (42, 42, 42), (hull_x + hull_w, ty), (hull_x + hull_w + track_w, ty), 1)

        pygame.draw.rect(hull_temp, tp['body_base'], (hull_x, hull_y, hull_w, hull_h))

        tiger_seam = tuple(max(0, c - 20) for c in tp['body_dark'])
        pygame.draw.line(hull_temp, tiger_seam, (hull_x + 1, hull_y + 8), (hull_x + hull_w - 1, hull_y + 8), 1)
        pygame.draw.line(hull_temp, tiger_seam, (hull_x + 1, hull_y + hull_h - 8), (hull_x + hull_w - 1, hull_y + hull_h - 8), 1)
        pygame.draw.line(hull_temp, tiger_seam, (tcx - 4, hull_y + 1), (tcx - 4, hull_y + hull_h - 1), 1)
        pygame.draw.line(hull_temp, tiger_seam, (tcx + 4, hull_y + 1), (tcx + 4, hull_y + hull_h - 1), 1)

        engine_h = 8
        pygame.draw.rect(hull_temp, tp['body_dark'], (hull_x + 2, hull_y + hull_h - engine_h, hull_w - 4, engine_h))
        for vy in range(hull_y + hull_h - engine_h + 1, hull_y + hull_h - 1, 2):
            pygame.draw.line(hull_temp, tiger_seam, (hull_x + 4, vy), (hull_x + hull_w - 4, vy), 1)

        primer_rng = random.Random(77)
        if primer_rng.random() > 0.6:
            primer_x = primer_rng.randint(hull_x + 3, hull_x + hull_w - 5)
            primer_y = primer_rng.randint(hull_y + 10, hull_y + hull_h - 10)
            pygame.draw.rect(hull_temp, tp['red_primer'], (primer_x, primer_y, 3, 2))

        PixelArtist3D._draw_iron_cross(hull_temp, tcx, hull_y + hull_h // 2 + 2, tp['iron_cross'])

        pygame.draw.rect(hull_temp, tp['body_dark'], (hull_x, hull_y, hull_w, hull_h), 2)

        turret_temp = pygame.Surface((size, size), pygame.SRCALPHA)
        turret_temp.fill((0, 0, 0, 0))

        tw, th = 16, 14
        tx = tcx - tw // 2
        ty = tcy - th // 2 - 2
        pygame.draw.rect(turret_temp, tp['turret_base'], (tx, ty, tw, th), border_radius=1)
        pygame.draw.rect(turret_temp, tp['turret_dark'], (tx + 2, ty + 2, tw - 4, th - 4), 1)

        pygame.draw.circle(turret_temp, tp['porte_cupola'], (tcx, ty + th // 2), 3)
        pygame.draw.circle(turret_temp, tp['turret_dark'], (tcx, ty + th // 2), 3, 1)

        gun_length = 14
        gun_end_y = ty - gun_length
        pygame.draw.line(turret_temp, tp['gun_barrel'], (tcx, ty), (tcx, gun_end_y), 3)
        pygame.draw.circle(turret_temp, (60, 60, 60), (tcx, gun_end_y), 3)
        pygame.draw.circle(turret_temp, tp['gun_barrel'], (tcx, gun_end_y), 2, 1)

        direction_angles = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: -45,
            Direction.EAST: -90,
            Direction.SOUTHEAST: -135,
            Direction.SOUTH: 180,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 90,
            Direction.NORTHWEST: 45,
        }

        hull_angle = direction_angles.get(direction, 0)
        turret_angle = direction_angles.get(turret_direction, 0)

        if hull_angle != 0:
            hull_temp = pygame.transform.rotate(hull_temp, hull_angle)
        if turret_angle != 0:
            turret_temp = pygame.transform.rotate(turret_temp, turret_angle)

        hull_rect = hull_temp.get_rect(center=(cx, cy))
        surface.blit(hull_temp, hull_rect)

        turret_rect = turret_temp.get_rect(center=(cx, cy))
        surface.blit(turret_temp, turret_rect)

        if state == "shoot" and frame == 1:
            direction_vectors = {
                Direction.NORTH: (0, -1),
                Direction.NORTHEAST: (0.707, -0.707),
                Direction.EAST: (1, 0),
                Direction.SOUTHEAST: (0.707, 0.707),
                Direction.SOUTH: (0, 1),
                Direction.SOUTHWEST: (-0.707, 0.707),
                Direction.WEST: (-1, 0),
                Direction.NORTHWEST: (-0.707, -0.707),
            }
            dvx, dvy = direction_vectors.get(turret_direction, (0, -1))
            flash_dist = 20
            flash_x = cx + int(dvx * flash_dist)
            flash_y = cy + int(dvy * flash_dist)
            pygame.draw.ellipse(surface, (255, 255, 100), (flash_x - 6, flash_y - 4, 12, 8))

        if state == "move":
            direction_vectors = {
                Direction.NORTH: (0, 1),
                Direction.NORTHEAST: (-0.707, 0.707),
                Direction.EAST: (-1, 0),
                Direction.SOUTHEAST: (-0.707, -0.707),
                Direction.SOUTH: (0, -1),
                Direction.SOUTHWEST: (0.707, -0.707),
                Direction.WEST: (1, 0),
                Direction.NORTHWEST: (0.707, 0.707),
            }
            dvx, dvy = direction_vectors.get(direction, (0, 1))
            for i in range(5):
                dust_dist = 20 + i * 3
                dust_x = cx + int(dvx * dust_dist)
                dust_y = cy + int(dvy * dust_dist)
                pygame.draw.circle(surface, (139, 119, 66), (dust_x, dust_y), 2 if i % 2 == 0 else 1)

    @staticmethod
    def _draw_star(surface, cx, cy, radius, color):
        """绘制五角星（阵营标识-盟军）"""
        import pygame

        points = []
        for i in range(5):
            angle = math.radians(-90 + i * 72)
            points.append((
                cx + int(radius * math.cos(angle)),
                cy + int(radius * math.sin(angle)),
            ))
            angle_inner = math.radians(-90 + i * 72 + 36)
            inner_r = radius * 0.4
            points.append((
                cx + int(inner_r * math.cos(angle_inner)),
                cy + int(inner_r * math.sin(angle_inner)),
            ))
        if len(points) >= 3:
            pygame.draw.polygon(surface, color, points)

    @staticmethod
    def _draw_iron_cross(surface, cx, cy, color):
        """绘制铁十字（阵营标识-轴心国）"""
        import pygame

        # 铁十字：中心圆 + 四个方向延伸
        pygame.draw.circle(surface, color, (cx, cy), 2)
        pygame.draw.line(surface, color, (cx - 3, cy), (cx + 3, cy), 1)
        pygame.draw.line(surface, color, (cx, cy - 3), (cx, cy + 3), 1)

    @staticmethod
    def create_halftrack_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """创建半履带车精灵 - 纯俯视角度 (TOP-DOWN VIEW!)

        P2-10 Enhanced Version:
        - Enhanced track texture lines (dark lines every 2px for tread detail)
        - Prominent gun barrel (front MG mount with longer barrel)
        - Body seam lines (panel gaps and armor plate seams)

        俯视特征:
        - 矩形车身
        - 后部履带 (更宽矩形)
        - 前部两个车轮圆 (从上方可见为圆形)
        - 后部开放货舱 (较亮颜色)
        - 前部机枪点
        """
        import pygame

        surface = pygame.Surface((40, 44), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        if faction == Faction.ALLIES:
            body_color = (74, 93, 35)
            dark_color = (56, 70, 26)
            track_color = (40, 45, 35)
            wheel_color = (30, 30, 30)
            cargo_color = (82, 100, 42)
        else:
            body_color = (85, 93, 80)
            dark_color = (65, 72, 62)
            track_color = (50, 55, 48)
            wheel_color = (35, 35, 35)
            cargo_color = (92, 100, 88)

        cx, cy = 20, 22

        size = 44
        temp = pygame.Surface((size, size), pygame.SRCALPHA)
        temp.fill((0, 0, 0, 0))
        tcx, tcy = size // 2, size // 2

        body_w, body_h = 16, 28
        body_x = tcx - body_w // 2
        body_y = tcy - body_h // 2
        pygame.draw.rect(temp, body_color, (body_x, body_y, body_w, body_h), border_radius=2)

        # ===== P2-10 Enhancement 1: Track Texture Lines (every 2px) =====
        track_w = 20
        track_h = 12
        track_x = tcx - track_w // 2
        track_y = body_y + body_h - track_h
        pygame.draw.rect(temp, track_color, (track_x, track_y, track_w, track_h))

        # Main track lines (every 2px - prominent tread pattern)
        track_line_dark = (30, 35, 28)  # Darker than base track
        for ty in range(track_y, track_y + track_h, 2):
            pygame.draw.line(temp, track_line_dark, (track_x, ty), (track_x + track_w, ty), 1)

        # Secondary fine track detail (every 4px for variation)
        track_line_fine = (35, 40, 32)  # Slightly lighter dark
        for ty in range(track_y + 1, track_y + track_h - 1, 4):
            if ty < track_y + track_h:
                pygame.draw.line(temp, track_line_fine, (track_x + 1, ty), (track_x + track_w - 1, ty), 1)

        # Track edge highlights (side borders for 3D effect)
        track_edge_light = (55, 60, 50)
        pygame.draw.line(temp, track_edge_light, (track_x, track_y), (track_x, track_y + track_h), 1)
        pygame.draw.line(temp, track_edge_light, (track_x + track_w - 1, track_y), (track_x + track_w - 1, track_y + track_h), 1)

        wheel_radius = 3
        wheel_y = body_y + 4
        pygame.draw.circle(temp, wheel_color, (tcx - 5, wheel_y), wheel_radius)
        pygame.draw.circle(temp, dark_color, (tcx - 5, wheel_y), wheel_radius, 1)
        pygame.draw.circle(temp, wheel_color, (tcx + 5, wheel_y), wheel_radius)
        pygame.draw.circle(temp, dark_color, (tcx + 5, wheel_y), wheel_radius, 1)

        # Wheel hub details (center dot for axle)
        hub_color = (50, 50, 50)
        pygame.draw.circle(temp, hub_color, (tcx - 5, wheel_y), 1)
        pygame.draw.circle(temp, hub_color, (tcx + 5, wheel_y), 1)

        cargo_w = body_w - 4
        cargo_h = track_h - 2
        cargo_x = tcx - cargo_w // 2
        cargo_y = track_y + 1
        pygame.draw.rect(temp, cargo_color, (cargo_x, cargo_y, cargo_w, cargo_h), 1)

        # Cargo area internal detail (cross-bracing lines)
        cargo_brace = (70, 88, 36)
        pygame.draw.line(temp, cargo_brace, (cargo_x + 2, cargo_y + 2), (cargo_x + cargo_w - 2, cargo_y + cargo_h - 2), 1)
        pygame.draw.line(temp, cargo_brace, (cargo_x + cargo_w - 2, cargo_y + 2), (cargo_x + 2, cargo_y + cargo_h - 2), 1)

        # ===== P2-10 Enhancement 2: Prominent Gun Barrel (Front MG Mount) =====
        mg_mount_color = (45, 45, 45)
        mg_barrel_color = (35, 35, 35)
        mg_barrel_length = 6  # Longer barrel for prominence

        # MG mount base (circular platform)
        pygame.draw.circle(temp, mg_mount_color, (tcx, body_y + 1), 2)

        # MG barrel (extending forward from mount)
        barrel_start_y = body_y + 1
        barrel_end_y = barrel_start_y - mg_barrel_length
        pygame.draw.line(temp, mg_barrel_color, (tcx, barrel_start_y), (tcx, barrel_end_y), 2)

        # Muzzle brake (barrel end detail)
        muzzle_color = (25, 25, 25)
        pygame.draw.circle(temp, muzzle_color, (tcx, barrel_end_y), 2)
        pygame.draw.circle(temp, mg_barrel_color, (tcx, barrel_end_y), 2, 1)

        # ===== P2-10 Enhancement 3: Body Seam Lines (Panel Gaps) =====
        seam_color = tuple(max(0, c - 18) for c in dark_color)  # Darker seam

        # Hood/engine compartment seam (front third of body)
        hood_seam_y = body_y + body_h // 3
        pygame.draw.line(temp, seam_color, (body_x + 1, hood_seam_y), (body_x + body_w - 1, hood_seam_y), 1)

        # Center vertical seam (body panel division)
        center_seam_x = tcx
        pygame.draw.line(temp, seam_color, (center_seam_x, body_y + 2), (center_seam_x, body_y + body_h - track_h - 2), 1)

        # Door seam lines (side access panels)
        door_seam_offset = body_w // 4
        pygame.draw.line(temp, seam_color, (body_x + door_seam_offset, hood_seam_y + 2), (body_x + door_seam_offset, body_y + body_h - track_h - 2), 1)
        pygame.draw.line(temp, seam_color, (body_x + body_w - door_seam_offset, hood_seam_y + 2), (body_x + body_w - door_seam_offset, body_y + body_h - track_h - 2), 1)

        # Fender line (above wheels)
        fender_y = wheel_y + wheel_radius + 1
        if fender_y < body_y + body_h:
            pygame.draw.line(temp, dark_color, (body_x, fender_y), (body_x + body_w, fender_y), 1)

        pygame.draw.rect(temp, dark_color, (body_x, body_y, body_w, body_h), 1)

        if faction == Faction.ALLIES:
            PixelArtist3D._draw_star(temp, tcx, tcy - 2, 3, (200, 200, 200))
        else:
            PixelArtist3D._draw_iron_cross(temp, tcx, tcy - 2, (180, 180, 180))

        direction_angles = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: -45,
            Direction.EAST: -90,
            Direction.SOUTHEAST: -135,
            Direction.SOUTH: 180,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 90,
            Direction.NORTHWEST: 45,
        }
        angle = direction_angles.get(direction, 0)
        if angle != 0:
            temp = pygame.transform.rotate(temp, angle)

        rect = temp.get_rect(center=(cx, cy))
        surface.blit(temp, rect)

        if state == "move":
            direction_vectors = {
                Direction.NORTH: (0, 1),
                Direction.NORTHEAST: (-0.707, 0.707),
                Direction.EAST: (-1, 0),
                Direction.SOUTHEAST: (-0.707, -0.707),
                Direction.SOUTH: (0, -1),
                Direction.SOUTHWEST: (0.707, -0.707),
                Direction.WEST: (1, 0),
                Direction.NORTHWEST: (0.707, 0.707),
            }
            dvx, dvy = direction_vectors.get(direction, (0, 1))
            for i in range(3):
                dust_dist = 18 + i * 3
                dust_x = cx + int(dvx * dust_dist)
                dust_y = cy + int(dvy * dust_dist)
                if 0 <= dust_x < 40 and 0 <= dust_y < 44:
                    pygame.draw.circle(surface, (139, 119, 66), (dust_x, dust_y), 1 + i % 2)

        return surface

    @staticmethod
    def create_jeep_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """创建吉普/侦察车精灵 - 纯俯视角度 (TOP-DOWN VIEW!)

        P2-10 Enhanced Version:
        - Body seam lines (hood, door, panel gaps)
        - Enhanced windshield V-shape detail
        - Wheel hub details

        俯视特征:
        - 小矩形车身
        - V型挡风玻璃线 (从上方可见为V形)
        - 4个车轮点在四角
        - 方向盘点
        """
        import pygame

        surface = pygame.Surface((28, 20), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        if faction == Faction.ALLIES:
            body_color = (92, 107, 53)
            dark_color = (72, 84, 41)
        else:
            body_color = (96, 104, 88)
            dark_color = (76, 82, 70)

        cx, cy = 14, 10

        size = 28
        temp = pygame.Surface((size, size), pygame.SRCALPHA)
        temp.fill((0, 0, 0, 0))
        tcx, tcy = size // 2, size // 2

        body_w, body_h = 12, 18
        body_x = tcx - body_w // 2
        body_y = tcy - body_h // 2
        pygame.draw.rect(temp, body_color, (body_x, body_y, body_w, body_h), border_radius=1)
        pygame.draw.rect(temp, dark_color, (body_x, body_y, body_w, body_h), 1)

        # Enhanced windshield V-shape (more prominent)
        windshield_v_color = (60, 68, 35) if faction == Faction.ALLIES else (65, 70, 62)
        pygame.draw.line(temp, windshield_v_color, (body_x + 2, body_y + 5), (tcx, body_y + 2), 1)
        pygame.draw.line(temp, windshield_v_color, (tcx, body_y + 2), (body_x + body_w - 2, body_y + 5), 1)

        # Windshield frame (slightly thicker V outline)
        pygame.draw.line(temp, dark_color, (body_x + 3, body_y + 6), (tcx, body_y + 3), 1)
        pygame.draw.line(temp, dark_color, (tcx, body_y + 3), (body_x + body_w - 3, body_y + 6), 1)

        wheel_color = (30, 30, 30)
        wheel_offset_x = body_w // 2 + 1
        wheel_offset_y_front = 3
        wheel_offset_y_rear = body_h - 3
        for wx_off in [-wheel_offset_x, wheel_offset_x]:
            for wy_off in [wheel_offset_y_front, wheel_offset_y_rear]:
                pygame.draw.circle(temp, wheel_color, (tcx + wx_off, body_y + wy_off), 2)

                # ===== P2-10 Enhancement: Wheel Hub Details =====
                hub_color = (50, 50, 50)
                pygame.draw.circle(temp, hub_color, (tcx + wx_off, body_y + wy_off), 1)

        # Steering wheel position (direction indicator)
        steering_color = (55, 55, 55)
        pygame.draw.circle(temp, steering_color, (tcx, body_y + 4), 1)

        # ===== P2-10 Enhancement: Body Seam Lines =====
        seam_color = tuple(max(0, c - 15) for c in dark_color)  # Darker seam lines

        # Hood/bonnet seam (front third separation)
        hood_seam_y = body_y + body_h // 3
        pygame.draw.line(temp, seam_color, (body_x + 1, hood_seam_y), (body_x + body_w - 1, hood_seam_y), 1)

        # Door seam line (vertical center division)
        door_seam_x = tcx
        pygame.draw.line(temp, seam_color, (door_seam_x, hood_seam_y + 2), (door_seam_x, body_y + body_h - 3), 1)

        # Rear cargo bed seam (back quarter separation)
        rear_seam_y = body_y + int(0.75 * body_h)
        pygame.draw.line(temp, seam_color, (body_x + 1, rear_seam_y), (body_x + body_w - 1, rear_seam_y), 1)

        # Side panel seams (door edges)
        side_seam_offset = body_w // 4
        pygame.draw.line(temp, seam_color, (body_x + side_seam_offset, hood_seam_y + 1), (body_x + side_seam_offset, rear_seam_y - 1), 1)
        pygame.draw.line(temp, seam_color, (body_x + body_w - side_seam_offset, hood_seam_y + 1), (body_x + body_w - side_seam_offset, rear_seam_y - 1), 1)

        # Fender line above front wheels
        fender_y_front = body_y + wheel_offset_y_front + 3
        if fender_y_front < body_y + body_h:
            pygame.draw.line(temp, dark_color, (body_x, fender_y_front), (body_x + body_w, fender_y_front), 1)

        # Tailgate seam (rear edge detail)
        tailgate_y = body_y + body_h - 2
        pygame.draw.line(temp, seam_color, (body_x + 2, tailgate_y), (body_x + body_w - 2, tailgate_y), 1)

        direction_angles = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: -45,
            Direction.EAST: -90,
            Direction.SOUTHEAST: -135,
            Direction.SOUTH: 180,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 90,
            Direction.NORTHWEST: 45,
        }
        angle = direction_angles.get(direction, 0)
        if angle != 0:
            temp = pygame.transform.rotate(temp, angle)

        rect = temp.get_rect(center=(cx, cy))
        surface.blit(temp, rect)

        return surface

    @staticmethod
    def create_at_gun_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """创建反坦克炮精灵 - 纯俯视角度 (TOP-DOWN VIEW!)

        俯视特征:
        - 小矩形底座
        - 长炮管延伸向朝向方向
        - 矩形炮盾在炮管后方
        - 两条架腿向后延伸 (V形)
        """
        import pygame

        surface = pygame.Surface((28, 20), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        body_color = (60, 65, 55)
        dark_color = (45, 50, 42)
        barrel_color = (40, 40, 40)
        shield_color = (55, 58, 52)

        cx, cy = 14, 10

        size = 28
        temp = pygame.Surface((size, size), pygame.SRCALPHA)
        temp.fill((0, 0, 0, 0))
        tcx, tcy = size // 2, size // 2

        base_w, base_h = 6, 4
        base_x = tcx - base_w // 2
        base_y = tcy - base_h // 2
        pygame.draw.rect(temp, body_color, (base_x, base_y, base_w, base_h))
        pygame.draw.rect(temp, dark_color, (base_x, base_y, base_w, base_h), 1)

        shield_w, shield_h = 8, 4
        shield_x = tcx - shield_w // 2
        shield_y = base_y - shield_h
        pygame.draw.rect(temp, shield_color, (shield_x, shield_y, shield_w, shield_h))
        pygame.draw.rect(temp, dark_color, (shield_x, shield_y, shield_w, shield_h), 1)

        barrel_length = 14
        barrel_start_y = shield_y
        barrel_end_y = barrel_start_y - barrel_length
        pygame.draw.line(temp, barrel_color, (tcx, barrel_start_y), (tcx, barrel_end_y), 2)
        pygame.draw.circle(temp, (30, 30, 30), (tcx, barrel_end_y), 2)

        leg_length = 8
        leg_spread = 5
        pygame.draw.line(temp, dark_color, (tcx - 1, base_y + base_h), (tcx - leg_spread, base_y + base_h + leg_length), 2)
        pygame.draw.line(temp, dark_color, (tcx + 1, base_y + base_h), (tcx + leg_spread, base_y + base_h + leg_length), 2)

        direction_angles = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: -45,
            Direction.EAST: -90,
            Direction.SOUTHEAST: -135,
            Direction.SOUTH: 180,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 90,
            Direction.NORTHWEST: 45,
        }
        angle = direction_angles.get(direction, 0)
        if angle != 0:
            temp = pygame.transform.rotate(temp, angle)

        rect = temp.get_rect(center=(cx, cy))
        surface.blit(temp, rect)

        if state == "shoot" and frame == 1:
            direction_vectors = {
                Direction.NORTH: (0, -1),
                Direction.NORTHEAST: (0.707, -0.707),
                Direction.EAST: (1, 0),
                Direction.SOUTHEAST: (0.707, 0.707),
                Direction.SOUTH: (0, 1),
                Direction.SOUTHWEST: (-0.707, 0.707),
                Direction.WEST: (-1, 0),
                Direction.NORTHWEST: (-0.707, -0.707),
            }
            dvx, dvy = direction_vectors.get(direction, (0, -1))
            flash_dist = 16
            flash_x = cx + int(dvx * flash_dist)
            flash_y = cy + int(dvy * flash_dist)
            pygame.draw.ellipse(surface, (255, 255, 100), (flash_x - 2, flash_y - 2, 4, 4))

        return surface

    @staticmethod
    def create_mortar_team_sprite(
        direction: Direction,
        faction: Direction,
        state: str = "idle",
        frame: int = 0,
    ):
        """
        创建迫击炮队精灵 (22×20 px, 含武器和操作员)

        CC2视觉规格:
        - 尺寸: ~22×20像素
        - 形状: 底座板 (小方形) + 炮管 (倾斜矩形~45°) + 2名操作员
        - 炮管倾斜约45°向上
        - 操作员: 迫击炮附近2个小点/圆
        - 颜色: 同步兵制服色调

        Args:
            direction: 8方向之一
            faction: ALLIES 或 AXIS
            state: idle/shoot
            frame: 动画帧号

        Returns:
            22×20 pygame.Surface (带alpha通道)
        """
        import pygame

        surface = pygame.Surface((22, 20), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        palette = CC2_PALETTE["allies" if faction == Faction.ALLIES else "axis"]
        uniform_color = palette['uniform']
        helmet_color = palette['helmet']
        weapon_color = palette['weapon']

        cx, cy = 11, 12

        # --- 底座板 (小方形) ---
        plate_size = 4
        plate_x = cx - plate_size // 2
        plate_y = cy + 4
        pygame.draw.rect(surface, (50, 50, 50), (plate_x, plate_y, plate_size, plate_size))
        pygame.draw.rect(surface, (35, 35, 35), (plate_x, plate_y, plate_size, plate_size), 1)

        # --- 炮管 (倾斜约45°) ---
        tube_length = 8
        tube_width = 2
        tube_angle = math.radians(-45)  # 向上倾斜45°

        # 根据方向微调角度
        direction_offsets = {
            Direction.NORTH: 0,
            Direction.NORTHEAST: 0.2,
            Direction.EAST: 0.4,
            Direction.SOUTHEAST: 0.6,
            Direction.SOUTH: 0.8,
            Direction.SOUTHWEST: -0.6,
            Direction.WEST: -0.4,
            Direction.NORTHWEST: -0.2,
        }
        tube_angle += direction_offsets.get(direction, 0)

        tube_start_x = cx
        tube_start_y = cy
        tube_end_x = tube_start_x + math.cos(tube_angle) * tube_length
        tube_end_y = tube_start_y + math.sin(tube_angle) * tube_length

        pygame.draw.line(surface, weapon_color,
                        (int(tube_start_x), int(tube_start_y)),
                        (int(tube_end_x), int(tube_end_y)),
                        tube_width)

        # 炮口 (开口端)
        pygame.draw.circle(surface, (60, 60, 60),
                          (int(tube_end_x), int(tube_end_y)), 2)

        # --- 两脚架 (支撑线) ---
        leg1_end_x = cx - 3
        leg1_end_y = cy + 5
        leg2_end_x = cx + 3
        leg2_end_y = cy + 5
        pygame.draw.line(surface, (60, 60, 60),
                        (int(tube_start_x), int(tube_start_y)),
                        (leg1_end_x, leg1_end_y), 1)
        pygame.draw.line(surface, (60, 60, 60),
                        (int(tube_start_x), int(tube_start_y)),
                        (leg2_end_x, leg2_end_y), 1)

        # --- 操作员1 (主射手) ---
        crew1_x = cx - 5
        crew1_y = cy + 2
        # 头盔
        pygame.draw.circle(surface, helmet_color, (crew1_x, crew1_y), 2)
        # 身体
        pygame.draw.rect(surface, uniform_color, (crew1_x - 2, crew1_y + 2, 4, 5))

        # --- 操作员2 (弹药手) ---
        crew2_x = cx + 5
        crew2_y = cy + 3
        # 头盔
        pygame.draw.circle(surface, helmet_color, (crew2_x, crew2_y), 2)
        # 身体
        pygame.draw.rect(surface, uniform_color, (crew2_x - 2, crew2_y + 2, 4, 4))

        # --- 射击闪光 ---
        if state == "shoot" and frame == 1:
            flash_size = 3
            pygame.draw.ellipse(surface, (255, 255, 100),
                              (int(tube_end_x) - flash_size // 2,
                               int(tube_end_y) - flash_size // 2,
                               flash_size, flash_size))

        return surface

    @staticmethod
    def create_tree_sprite(variant: int = 0, size: str = "medium"):
        """
        创建树木精灵 (CC2风格多色调树冠 + 不规则边缘)

        Phase 1 Fix 0.3 + Fix 0.5 升级版:
        - 多色调树冠: 4种绿色层次（基础+高光+阴影+强调）
        - 不规则边缘: 扰动半径±2px每30度（非完美圆形）
        - 光源模拟: 左上角高光，右下角阴影
        - 尺寸变化: small(20×20)/medium(28×28)/large(36×36)

        Args:
            variant: 变体编号 (0-2)
            size: 树木尺寸 ("small", "medium", "large")

        Returns:
            pygame.Surface (带alpha通道，尺寸根据size参数变化)
        """
        import pygame

        # *** 尺寸配置 ***
        size_config = {
            "small": {"canvas": 20, "radius": 10},
            "medium": {"canvas": 28, "radius": 14},
            "large": {"canvas": 36, "radius": 18},
        }
        config = size_config.get(size, size_config["medium"])
        canvas_size = config["canvas"]
        canopy_radius = config["radius"]

        surface = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        cx, cy = canvas_size // 2, canvas_size // 2 - 1

        # *** 阴影层 (东南偏移) ***
        shadow_surface = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
        shadow_offset_x, shadow_offset_y = 3, 3
        shadow_w = canopy_radius * 2 - 4
        shadow_h = canopy_radius * 1.5 - 2
        pygame.draw.ellipse(
            shadow_surface, (0, 0, 0, 50),
            (cx - shadow_w // 2 + shadow_offset_x,
             cy - shadow_h // 2 + shadow_offset_y,
             shadow_w, shadow_h),
        )
        surface.blit(shadow_surface, (0, 0))

        # *** 多色调调色板 (Fix 0.3) ***
        base_canopy = (34, 68, 28)           # 基础深绿色
        accent_light = (45, 90, 38)          # 强调绿色1（较亮）
        highlight = (55, 110, 48)             # 高光色（最亮）
        shadow_green = (22, 50, 18)          # 阴影色（最暗）
        trunk_color = (60, 40, 20)           # 暗棕色树干

        # *** 1. 绘制基础树冠 (不规则圆) ***
        # 使用扰动半径创建不规则边缘（每30度±2px）
        import math
        points = []
        num_points = 36  # 每10度一个点
        rng_edge = random.Random(variant * 73 + 11)

        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            # 半径扰动: ±2px随机偏移
            radius_perturb = canopy_radius + rng_edge.randint(-2, 2)
            px = cx + int(math.cos(angle) * radius_perturb)
            py = cy + int(math.sin(angle) * radius_perturb)
            points.append((px, py))

        if len(points) >= 3:
            pygame.draw.polygon(surface, base_canopy, points)

        # *** 2. 填充内部基础色 ***
        pygame.draw.circle(surface, base_canopy, (cx, cy), canopy_radius - 1)

        # *** 3. 强调绿色1 (散布15-20个中等亮度点) ***
        rng_accent1 = random.Random(variant * 41 + 3)
        accent1_count = rng_accent1.randint(15, 20)
        for _ in range(accent1_count):
            angle = rng_accent1.uniform(0, 2 * math.pi)
            dist = rng_accent1.uniform(0, canopy_radius - 3)
            ax = int(cx + math.cos(angle) * dist)
            ay = int(cy + math.sin(angle) * dist)
            if 0 <= ax < canvas_size and 0 <= ay < canvas_size:
                surface.set_at((ax, ay), accent_light)

        # *** 4. 高光点 (左上角5-8个点 - 光源模拟) ***
        rng_highlight = random.Random(variant * 59 + 7)
        highlight_count = rng_highlight.randint(5, 8)
        for _ in range(highlight_count):
            # 偏向左上象限 (-135° 到 -45°)
            angle = rng_highlight.uniform(-3 * math.pi / 4, -math.pi / 4)
            dist = rng_highlight.uniform(canopy_radius * 0.2, canopy_radius * 0.6)
            hx = int(cx + math.cos(angle) * dist)
            hy = int(cy + math.sin(angle) * dist)
            if 0 <= hx < canvas_size and 0 <= hy < canvas_size:
                surface.set_at((hx, hy), highlight)

        # *** 5. 阴影点 (右下角8-10个点 - 背光面) ***
        rng_shadow = random.Random(variant * 83 + 13)
        shadow_count = rng_shadow.randint(8, 10)
        for _ in range(shadow_count):
            # 偏向右下象限 (45° 到 135°)
            angle = rng_shadow.uniform(math.pi / 4, 3 * math.pi / 4)
            dist = rng_shadow.uniform(canopy_radius * 0.3, canopy_radius * 0.7)
            sx = int(cx + math.cos(angle) * dist)
            sy = int(cy + math.sin(angle) * dist)
            if 0 <= sx < canvas_size and 0 <= sy < canvas_size:
                surface.set_at((sx, sy), shadow_green)

        # *** 6. 树干 (中心2px暗棕色点) ***
        trunk_y = cy + canopy_radius // 3
        if 0 <= trunk_y < canvas_size:
            pygame.draw.circle(surface, trunk_color, (cx, trunk_y), 2)

        # *** 7. 边缘描深 (不规则轮廓线) ***
        edge_color = (28, 58, 24)
        if len(points) >= 3:
            for i in range(len(points)):
                p1 = points[i]
                p2 = points[(i + 1) % len(points)]
                pygame.draw.line(surface, edge_color, p1, p2, 1)

        return surface

    @staticmethod
    def create_building_sprite(
        building_type: str = "house",
        roof_color: tuple | None = None,
        wall_color: tuple | None = None,
    ):
        """
        创建建筑精灵 (40×40 px, 正交俯视)

        CC2使用Orthographic Top-Down投影，建筑显示为:
        - 矩形屋顶平面（屋顶颜色）
        - 南/东边缘2-4px阴影条（模拟墙体高度）
        - 屋顶表面窗户点
        - 南边缘门标记

        Args:
            building_type: house/church/barn
            roof_color: 自定义屋顶颜色
            wall_color: 自定义墙壁颜色（用于阴影条）

        Returns:
            40×40 pygame.Surface (带alpha通道)
        """
        import pygame

        surface = pygame.Surface((40, 40), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        if roof_color is None:
            roof_colors = {
                "house": (160, 50, 40),
                "church": (100, 100, 100),
                "barn": (140, 90, 50),
            }
            roof_color = roof_colors.get(building_type, (140, 90, 50))

        if wall_color is None:
            shadow_color = tuple(max(0, v - 50) for v in roof_color)
        else:
            shadow_color = tuple(max(0, v - 30) for v in wall_color)

        margin = 4
        footprint_w = 32
        footprint_h = 28
        fp_x = margin
        fp_y = margin

        pygame.draw.rect(surface, roof_color, (fp_x, fp_y, footprint_w, footprint_h))

        # *** 屋顶瓦片图案（网格纹理）***
        import random as _random
        tile_rng = _random.Random(hash(building_type + "_roof_tiles"))
        tile_dark = tuple(max(0, int(v * 0.9)) for v in roof_color)
        tile_spacing = tile_rng.randint(8, 12)
        # 横向瓦片线
        for ty in range(fp_y + tile_spacing, fp_y + footprint_h - 2, tile_spacing):
            pygame.draw.line(surface, tile_dark,
                           (fp_x + 2, ty),
                           (fp_x + footprint_w - 2, ty), 1)
        # 纵向瓦片线（偶尔）
        for _ in range(tile_rng.randint(1, 2)):
            vx = tile_rng.randint(fp_x + footprint_w // 4, fp_x + 3 * footprint_w // 4)
            pygame.draw.line(surface, tile_dark,
                           (vx, fp_y + 2),
                           (vx, fp_y + footprint_h - 2), 1)

        # *** 屋脊线（屋顶中央隆起线）***
        ridge_y = fp_y + footprint_h // 2
        ridge_color = tuple(max(0, v - 25) for v in roof_color)
        pygame.draw.line(surface, ridge_color,
                        (fp_x + 3, ridge_y),
                        (fp_x + footprint_w - 3, ridge_y), 1)

        shadow_depth = 3
        for i in range(shadow_depth):
            factor = 1.0 - (i / shadow_depth) * 0.5
            strip_col = tuple(int(c * factor) for c in shadow_color)
            pygame.draw.line(
                surface, strip_col,
                (fp_x, fp_y + footprint_h + i),
                (fp_x + footprint_w, fp_y + footprint_h + i), 1)
            pygame.draw.line(
                surface, strip_col,
                (fp_x + footprint_w + i, fp_y),
                (fp_x + footprint_w + i, fp_y + footprint_h), 1)

        window_color = (80, 120, 160)
        window_dark = (40, 50, 65)
        window_blue = (60, 80, 120)

        # 根据建筑类型决定窗户数量和大小
        win_rng = _random.Random(hash(building_type + "_windows"))
        if building_type == "house":
            num_windows = win_rng.randint(3, 4)
            win_size = 3
        elif building_type == "church":
            num_windows = win_rng.randint(2, 3)
            win_size = 3
        elif building_type == "barn":
            num_windows = win_rng.randint(1, 2)
            win_size = 3
        else:
            num_windows = win_rng.randint(2, 3)
            win_size = 3

        # 窗户位置（散布排列，避免屋脊线）
        window_positions = []
        placed_count = 0
        for _ in range(num_windows * 3):  # 尝试多次
            wx = win_rng.randint(fp_x + 5, fp_x + footprint_w - 6)
            wy = win_rng.randint(fp_y + 5, fp_y + footprint_h - 6)
            # 避免在屋脊线上
            if abs(wy - ridge_y) > 4:
                # 检查距离
                too_close = False
                for px, py in window_positions:
                    if abs(wx - px) < 5 and abs(wy - py) < 5:
                        too_close = True
                        break
                if not too_close:
                    window_positions.append((wx, wy))
                    placed_count += 1
                    if placed_count >= num_windows:
                        break

        # 绘制窗户
        for wx, wy in window_positions:
            win_col = win_rng.choice([window_color, window_blue, window_dark])
            pygame.draw.rect(surface, win_col, (wx - 1, wy - 1, win_size, win_size))

        # *** 烟囱（住宅建筑）***
        chimney_rng = _random.Random(hash(building_type + "_chimney"))
        if building_type in ["house", "farmhouse"] and chimney_rng.random() > 0.4:
            chimney_w = 6
            chimney_h = 8
            chimney_x = fp_x + footprint_w - chimney_w - 4
            chimney_y = fp_y + 4
            chimney_stone = (100, 95, 88)
            chimney_dark = (80, 75, 68)
            pygame.draw.rect(surface, chimney_stone, (chimney_x, chimney_y, chimney_w, chimney_h))
            pygame.draw.rect(surface, chimney_dark, (chimney_x + chimney_w - 1, chimney_y, 1, chimney_h))
            pygame.draw.rect(surface, chimney_dark, (chimney_x, chimney_y + chimney_h - 1, chimney_w, 1))

        door_color = (100, 65, 35)
        door_w = 6
        door_h = 3
        door_x = fp_x + footprint_w // 2 - door_w // 2
        door_y = fp_y + footprint_h - 1
        pygame.draw.rect(surface, door_color, (door_x, door_y, door_w, door_h))

        darker_roof = tuple(max(0, v - 25) for v in roof_color)
        pygame.draw.rect(surface, darker_roof, (fp_x, fp_y, footprint_w, footprint_h), 1)

        if building_type == "church":
            cross_x = fp_x + footprint_w // 2
            cross_y = fp_y + footprint_h // 2
            pygame.draw.line(surface, (220, 220, 200), (cross_x, cross_y - 3), (cross_x, cross_y + 3), 2)
            pygame.draw.line(surface, (220, 220, 200), (cross_x - 2, cross_y - 1), (cross_x + 2, cross_y - 1), 2)
            dot_offset = 6
            pygame.draw.circle(surface, (60, 80, 160), (cross_x - dot_offset, cross_y - dot_offset // 2), 2)
            pygame.draw.circle(surface, (160, 60, 60), (cross_x + dot_offset, cross_y - dot_offset // 2), 2)
            pygame.draw.circle(surface, (160, 60, 60), (cross_x - dot_offset, cross_y + dot_offset // 2), 2)
            pygame.draw.circle(surface, (60, 80, 160), (cross_x + dot_offset, cross_y + dot_offset // 2), 2)

        return surface

    @staticmethod
    def _anim_state_to_params(anim_state: InfantryAnimState) -> tuple[str, int]:
        """将 InfantryAnimState 转换为 (state, frame) 参数供 create_infantry_sprite 使用"""
        mapping = {
            InfantryAnimState.IDLE: ("idle", 0),
            InfantryAnimState.WALK_1: ("walk", 1),
            InfantryAnimState.WALK_2: ("walk", 3),
            InfantryAnimState.SHOOT: ("shoot", 1),
            InfantryAnimState.PRONE: ("crawl", 0),
            InfantryAnimState.DIE_1: ("die", 1),
            InfantryAnimState.DIE_2: ("die", 2),
            InfantryAnimState.DEAD: ("die", 3),
        }
        return mapping.get(anim_state, ("idle", 0))

    @staticmethod
    def create_infantry_animation_sheet(
        faction: Faction,
        infantry_type: InfantryType | None = None,
    ):
        """
        生成步兵全动画帧精灵表

        生成所有8个方向 × 所有8个动画状态的精灵，排列为精灵表。
        布局: 行=方向(N,NE,E,SE,S,SW,W,NW), 列=动画状态(IDLE,WALK_1,WALK_2,SHOOT,PRONE,DIE_1,DIE_2,DEAD)
        每个精灵 24×24px

        Args:
            faction: ALLIES 或 AXIS
            infantry_type: 步兵类型 (默认RIFLEMAN)

        Returns:
            (sprite_sheet, direction_order, anim_state_order) 元组
            sprite_sheet: pygame.Surface (192×192, 8列×8行)
            direction_order: 方向顺序列表
            anim_state_order: 动画状态顺序列表
        """
        import pygame

        if infantry_type is None:
            infantry_type = InfantryType.RIFLEMAN

        sprite_size = 24
        cols = 8  # 8个动画状态
        rows = 8  # 8个方向

        sheet = pygame.Surface((cols * sprite_size, rows * sprite_size), pygame.SRCALPHA)
        sheet.fill((0, 0, 0, 0))

        direction_order = [
            Direction.NORTH, Direction.NORTHEAST, Direction.EAST, Direction.SOUTHEAST,
            Direction.SOUTH, Direction.SOUTHWEST, Direction.WEST, Direction.NORTHWEST,
        ]
        anim_state_order = [
            InfantryAnimState.IDLE, InfantryAnimState.WALK_1, InfantryAnimState.WALK_2,
            InfantryAnimState.SHOOT, InfantryAnimState.PRONE, InfantryAnimState.DIE_1,
            InfantryAnimState.DIE_2, InfantryAnimState.DEAD,
        ]

        for row, direction in enumerate(direction_order):
            for col, anim_state in enumerate(anim_state_order):
                state, frame = PixelArtist3D._anim_state_to_params(anim_state)
                sprite = PixelArtist3D.create_infantry_sprite(
                    direction=direction,
                    faction=faction,
                    state=state,
                    frame=frame,
                    infantry_type=infantry_type,
                )
                sheet.blit(sprite, (col * sprite_size, row * sprite_size))

        return sheet, direction_order, anim_state_order


class InfantryAnimator:
    """
    步兵动画状态管理器 - 管理帧循环和状态转换

    根据单位行为(移动/射击/死亡)自动切换动画状态，
    并按固定时间间隔循环行走帧。
    """

    WALK_CYCLE_INTERVAL = 0.2  # 行走帧切换间隔(秒), 约5FPS

    def __init__(self):
        self._frame: int = 0
        self._state: InfantryAnimState = InfantryAnimState.IDLE
        self._walk_timer: float = 0.0
        self._walk_cycle: list[InfantryAnimState] = [
            InfantryAnimState.WALK_1,
            InfantryAnimState.IDLE,
            InfantryAnimState.WALK_2,
            InfantryAnimState.IDLE,
        ]
        self._shoot_timer: float = 0.0
        self._shoot_duration: float = 0.15  # 射击动画持续时间
        self._die_timer: float = 0.0
        self._die_duration: float = 0.3  # 每帧死亡动画持续时间

    @property
    def state(self) -> InfantryAnimState:
        """当前动画状态"""
        return self._state

    def update(
        self,
        dt: float,
        is_moving: bool = False,
        is_firing: bool = False,
        is_dead: bool = False,
        is_prone: bool = False,
    ) -> InfantryAnimState:
        """
        根据单位行为更新动画状态

        Args:
            dt: 距上次更新的时间(秒)
            is_moving: 是否正在移动
            is_firing: 是否正在射击
            is_dead: 是否已死亡
            is_prone: 是否趴下

        Returns:
            当前 InfantryAnimState
        """
        # 死亡状态优先级最高，不可逆
        if self._state == InfantryAnimState.DEAD:
            return self._state

        if is_dead:
            self._die_timer += dt
            if self._die_timer < self._die_duration:
                self._state = InfantryAnimState.DIE_1
            elif self._die_timer < self._die_duration * 2:
                self._state = InfantryAnimState.DIE_2
            else:
                self._state = InfantryAnimState.DEAD
            return self._state

        # 射击状态
        if is_firing:
            self._shoot_timer += dt
            self._state = InfantryAnimState.SHOOT
            if self._shoot_timer > self._shoot_duration:
                self._shoot_timer = 0.0
            return self._state
        else:
            self._shoot_timer = 0.0

        # 趴下状态
        if is_prone:
            self._state = InfantryAnimState.PRONE
            return self._state

        # 行走状态
        if is_moving:
            self._walk_timer += dt
            if self._walk_timer > self.WALK_CYCLE_INTERVAL:
                self._walk_timer = 0.0
                self._frame = (self._frame + 1) % len(self._walk_cycle)
            self._state = self._walk_cycle[self._frame]
        else:
            self._walk_timer = 0.0
            self._frame = 0
            self._state = InfantryAnimState.IDLE

        return self._state

    def reset(self):
        """重置动画状态"""
        self._frame = 0
        self._state = InfantryAnimState.IDLE
        self._walk_timer = 0.0
        self._shoot_timer = 0.0
        self._die_timer = 0.0


def create_cc2_infantry_sprite(direction: int, faction: str = "allies", state: str = "idle", frame: int = 0, infantry_type: str = "rifleman"):
    """
    便捷函数：创建CC2风格步兵精灵

    Args:
        direction: 0-7 (N, NE, E, SE, S, SW, W, NW)
        faction: "allies" 或 "axis"
        state: idle/walk/shoot/die/hit
        frame: 动画帧号
        infantry_type: rifleman/mg/at/officer/sniper/medic/engineer/scout

    Returns:
        pygame.Surface (24×24)
    """
    dir_enum = list(Direction)[direction % 8]
    faction_enum = Faction.ALLIES if faction == "allies" else Faction.AXIS
    type_map = {t.value: t for t in InfantryType}
    type_enum = type_map.get(infantry_type, InfantryType.RIFLEMAN)
    return PixelArtist3D.create_infantry_sprite(dir_enum, faction_enum, state, frame, type_enum)


def create_cc2_tank_sprite(
    direction: int,
    faction: str = "allies",
    turret_direction: int | None = None,
    state: str = "idle",
    frame: int = 0,
):
    """
    便捷函数：创建CC2风格坦克精灵

    Args:
        direction: 车体朝向 0-7
        faction: "allies" 或 "axis"
        turret_direction: 炮塔朝向 0-7 (可选)
        state: idle/move/shoot
        frame: 动画帧号

    Returns:
        pygame.Surface (36×36)
    """
    dir_enum = list(Direction)[direction % 8]
    faction_enum = Faction.ALLIES if faction == "allies" else Faction.AXIS
    turret_enum = list(Direction)[turret_direction % 8] if turret_direction is not None else None
    return PixelArtist3D.create_tank_sprite(dir_enum, faction_enum, turret_enum, state, frame)


if __name__ == "__main__":
    import pygame

    pygame.init()

    print("CC2 45° Isometric Pixel Artist - Test Generation")
    print("=" * 50)

    test_surface = pygame.Surface((400, 300), pygame.SRCALPHA)
    test_surface.fill((40, 80, 28))

    directions = list(Direction)
    for i, direction in enumerate(directions):
        sprite = PixelArtist3D.create_infantry_sprite(
            direction=direction,
            faction=Faction.ALLIES,
            state="idle",
            frame=0,
        )
        x = (i % 4) * 90 + 20
        y = (i // 4) * 100 + 20
        test_surface.blit(sprite, (x, y))

        font = pygame.font.Font(None, 16)
        text = font.render(direction.name[:2], True, (240, 220, 40))
        test_surface.blit(text, (x + 6, y + 26))

    tank_sprite = PixelArtist3D.create_tank_sprite(
        direction=Direction.SOUTH,
        faction=Faction.ALLIES,
        state="idle",
    )
    test_surface.blit(tank_sprite, (320, 200))

    tree_sprite = PixelArtist3D.create_tree_sprite(variant=0)
    test_surface.blit(tree_sprite, (350, 240))

    building_sprite = PixelArtist3D.create_building_sprite(building_type="house")
    test_surface.blit(building_sprite, (180, 200))

    pygame.image.save(test_surface, "/tmp/cc2_style_preview.png")
    print("✅ Preview saved to /tmp/cc2_style_preview.png")
    print(f"   Generated {len(directions)} infantry sprites + tank + tree + building")

    pygame.quit()
