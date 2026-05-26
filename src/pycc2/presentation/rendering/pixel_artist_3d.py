"""
CC2风格正交俯视投影像素艺术生成器

基于2026-05-22 CC2原版截图分析：
- 视角: Orthographic Top-Down (正交俯视，非等距投影)
- 尺寸: 24×24像素 (步兵)
- 风格: 像素级写实，非卡通/非几何形状
- 配色: 深绿/灰绿色军事色调 (低饱和度, CC2精确调色板)
"""

from __future__ import annotations

import math
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class Direction(Enum):
    """8方向枚举"""
    NORTH = 0
    NORTHEAST = 1
    EAST = 2
    SOUTHEAST = 3
    SOUTH = 4
    SOUTHWEST = 5
    WEST = 6
    NORTHWEST = 7


class Faction(Enum):
    """阵营枚举"""
    ALLIES = "allies"
    AXIS = "axis"


class InfantryType(Enum):
    """步兵类型枚举"""
    RIFLEMAN = "rifleman"
    MG = "mg"
    AT = "at"
    OFFICER = "officer"
    SNIPER = "sniper"


class TankType(Enum):
    """坦克类型枚举 - 基于二战诺曼底战役历史参考"""
    SHERMAN_M4 = "sherman_m4"       # 美军M4谢尔曼中型坦克
    PANTHER_AUSFG = "panther_ausfg"  # 德军豹式G型坦克
    TIGER_I = "tiger_i"              # 德军虎式I型重型坦克


class InfantryAnimState(Enum):
    """步兵动画状态枚举 - 支持多帧行走/射击/死亡动画"""
    IDLE = auto()       # 站立静止
    WALK_1 = auto()     # 左脚前迈
    WALK_2 = auto()     # 右脚前迈
    SHOOT = auto()      # 射击姿态
    PRONE = auto()      # 趴下/匍匐
    DIE_1 = auto()      # 倒地中
    DIE_2 = auto()      # 已倒地
    DEAD = auto()       # 死亡精灵


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

    CC2_PALETTE = {
        'allies': {
            # WWII US Olive Drab (历史修正版): 偏棕橄榄褐, 非亮绿色
            # 参考: Steve Zaloga(装甲史学家) + Tamiya XF62模型漆
            # CC2截图验证: 盟军制服为暗沉的土褐色调
            'uniform': (112, 108, 76),
            'uniform_dark': (88, 84, 58),
            'uniform_light': (132, 128, 94),
            'helmet': (72, 76, 72),           # M1钢盔，暗橄榄褐钢色（历史修正）
            'helmet_dark': (56, 58, 56),
            'helmet_highlight': (100, 104, 100),
            'skin': (200, 170, 140),
            'skin_shadow': (180, 150, 120),
            'weapon': (60, 60, 60),
            'weapon_metal': (75, 75, 75),
            'weapon_wood': (90, 65, 35),
            'boots': (45, 38, 28),
            'equipment': (50, 55, 40),
            'equipment_dark': (35, 38, 28),
            'canteen': (70, 90, 55),
            'ammo_belt': (55, 50, 38),
            'beret': (60, 80, 45),
        },
        'axis': {
            # German Field Gray (Feldgrau) - 基于1944年照片的实际颜色:
            # 非纯灰色！是带轻微棕色调的绿灰色
            # 参考: Bundesarchiv照片 + Osprey Publishing色彩分析
            'uniform': (75, 78, 70),
            'uniform_dark': (58, 62, 54),
            'uniform_light': (90, 93, 85),
            'helmet': (56, 58, 56),           # 德军Stahlhelm钢盔，暗金属灰绿色（历史修正）
            'helmet_dark': (42, 44, 42),
            'helmet_highlight': (78, 80, 78),
            'skin': (200, 170, 140),
            'skin_shadow': (180, 150, 120),
            'weapon': (60, 60, 60),
            'weapon_metal': (75, 75, 75),
            'weapon_wood': (90, 65, 35),
            'boots': (40, 35, 25),
            'equipment': (55, 55, 48),
            'equipment_dark': (38, 38, 32),
            'canteen': (65, 65, 58),
            'ammo_belt': (50, 48, 40),
            'beret': (50, 50, 44),
        },
    }

    # 历史准确性坦克调色板 - 基于Kenney CC0资源+二战照片
    TANK_PALETTES = {
        TankType.SHERMAN_M4: {
            # M4谢尔曼中型坦克 - 美军橄榄绿+泥污风化效果
            # 参考: US Army Ordnance Corps FM 9-2075 + Tamiya模型漆标准
            'body_base': (112, 108, 76),       # Olive Drab #706C4C (已修正)
            'body_dark': (88, 84, 58),          # 暗部阴影
            'body_light': (132, 128, 94),       # 高光区域
            'turret_base': (118, 114, 82),      # 炮塔稍亮
            'turret_dark': (92, 88, 62),        # 炮塔暗部
            'track_color': (45, 45, 45),        # 履带黑
            'track_rust': (65, 50, 35),         # 履带锈迹
            'gun_barrel': (55, 55, 55),         # 75mm M3炮管
            'mud_dirt': (85, 72, 48),           # 泥土污渍（诺曼底特征）
            'white_star': (220, 220, 220),      # 白色星标
            'cupola': (100, 96, 68),            # 车长指挥塔
            'mg_mount': (50, 50, 50),           # .50 cal机枪座
            'side_skirt': (105, 100, 70),       # 侧裙甲（部分型号）
        },
        TankType.PANTHER_AUSFG: {
            # 豹式G型坦克 - Dunkelgelb（暗黄）底色+迷彩条纹选项
            # 参考: Germany Tigerfibel手册 + Jentz/Doyle《豹式坦克》技术规格
            'body_base': (85, 88, 30),          # Dunkelgelb RAL 7028 暗黄 #55581E
            'body_dark': (65, 68, 22),           # 暗黄暗部
            'body_light': (100, 104, 40),        # 暗黄高光
            'camo_red_brown': (95, 45, 28),     # Rotbraun RAL 8017 迷彩红棕
            'turret_base': (90, 94, 35),         # 炮塔暗黄
            'turret_dark': (70, 74, 26),         # 炮塔暗部
            'track_color': (35, 35, 35),         # 履带（更暗）
            'gun_barrel': (40, 40, 40),          # 75mm KwK42 L/70长炮管
            'schurzen': (80, 83, 28),            # 炮塔侧裙甲5mm薄板
            'exhaust_pipe': (45, 42, 38),        # 排气管（左侧多出口）
            'mud_dirt': (75, 68, 45),            # 泥污
            'iron_cross': (200, 200, 200),       # 铁十字标识
        },
        TankType.TIGER_I: {
            # 虎式I型重型坦克 - 方正箱体造型，"移动碉堡"
            # 参考: Tiger I Ausf.E Sd.Kfz.181技术手册 + Bovington博物馆实测
            'body_base': (80, 80, 64),           # Dark Yellow #505040 或红底漆 #8B3030
            'body_dark': (60, 60, 48),            # 暗部
            'body_light': (95, 95, 78),          # 高光
            'red_primer': (139, 48, 48),         # 红色底漆（部分车辆可见）
            'turret_base': (85, 85, 68),          # 大矩形炮塔
            'turret_dark': (65, 65, 52),          # 炮塔暗部
            'track_color': (32, 32, 32),          # 宽履带
            'gun_barrel': (45, 45, 45),           # 88mm KwK36 L/56
            'porte_cupola': (90, 90, 74),         # 装甲指挥塔（炮塔中心）
            'boxy_detail': (70, 70, 56),          # 方形细节线
            'iron_cross': (195, 195, 195),        # 铁十字
        }
    }

    @staticmethod
    def create_infantry_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
        infantry_type: InfantryType | None = None,
    ):
        """
        创建步兵精灵 (24×24 px) - 支持姿态差异化

        姿态系统 (基于CC2原版 + WWII战术观察):
        - idle/walk/run: 站立/行走姿态，看到头顶+身体+手脚
        - crawl/defend/attack: **趴姿** - 长条形轮廓贴地，方向性极明显!
          (爬行、防守、进攻时士兵趴下以减小受弹面积)

        Args:
            direction: 8方向之一
            faction: ALLIES 或 AXIS
            state: idle/walk/shoot/die/hit/crawl/defend/attack
            frame: 动画帧号
            infantry_type: 步兵类型 (rifleman/mg/at/officer/sniper)

        Returns:
            24×24 pygame.Surface (带alpha通道)
        """
        import pygame

        if infantry_type is None:
            infantry_type = InfantryType.RIFLEMAN

        surface = pygame.Surface((24, 24), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        palette = PixelArtist3D.CC2_PALETTE[faction.value]
        body_color = palette['uniform']
        body_dark = palette['uniform_dark']
        body_light = palette['uniform_light']
        helmet_color = palette['helmet']
        helmet_dark = palette['helmet_dark']
        helmet_highlight = palette['helmet_highlight']
        skin_color = palette['skin']
        skin_shadow = palette['skin_shadow']
        weapon_color = palette['weapon']
        weapon_metal = palette['weapon_metal']
        weapon_wood = palette['weapon_wood']
        boots_color = palette['boots']
        equip_color = palette['equipment']
        equip_dark = palette['equipment_dark']
        canteen_color = palette['canteen']
        ammo_color = palette['ammo_belt']
        beret_color = palette['beret']

        # *** 姿态判断: 趴姿状态列表 ***
        prone_states = {'crawl', 'defend', 'attack'}
        is_prone = state in prone_states

        # 如果是趴姿，使用专门的趴姿渲染路径（长条形轮廓!）
        if is_prone and state != "die":
            return PixelArtist3D._draw_infantry_prone(
                surface, direction, state, frame, palette, infantry_type,
                body_color, body_dark, body_light, helmet_color, helmet_dark,
                helmet_highlight, skin_color, skin_shadow, weapon_color,
                weapon_metal, weapon_wood, boots_color, equip_color,
                equip_dark, canteen_color, ammo_color, beret_color,
            )

        dx, dy = PixelArtist3D._get_isometric_offset(direction)
        dir_params = PixelArtist3D._get_direction_params(direction)

        center_x, center_y = 12 + dx, 14 + dy

        # --- 死亡动画4帧序列 ---
        if state == "die":
            return PixelArtist3D._draw_infantry_death(
                surface, direction, frame, palette, infantry_type,
                body_color, body_dark, body_light, helmet_color, helmet_dark,
                helmet_highlight, skin_color, skin_shadow, weapon_color,
                weapon_metal, weapon_wood, boots_color, equip_color,
                equip_dark, canteen_color, ammo_color, beret_color,
                center_x, center_y, dx, dy,
            )

        # --- 4帧行走动画 ---
        # 帧0: 站立, 帧1: 左脚前, 帧2: 站立, 帧3: 右脚前
        if state == "walk":
            walk_offsets = [0, -2, 0, 2]
            leg_offset = walk_offsets[frame % 4]
        else:
            leg_offset = 0

        # --- 腿部 - 根据方向调整腿部张开程度 ---
        leg_spread = dir_params.get('leg_spread_mod', 2)
        left_foot_x = center_x - leg_spread + (leg_offset if leg_offset < 0 else 0)
        right_foot_x = center_x + leg_spread + (leg_offset if leg_offset > 0 else 0)
        left_hip = (center_x - leg_spread, center_y + 5)
        right_hip = (center_x + leg_spread, center_y + 5)
        left_foot = (left_foot_x, center_y + 9)
        right_foot = (right_foot_x, center_y + 9)

        pygame.draw.line(surface, body_dark, left_hip, left_foot, 2)
        pygame.draw.line(surface, body_dark, right_hip, right_foot, 2)

        # 靴子
        pygame.draw.circle(surface, boots_color, (int(left_foot[0]), int(left_foot[1])), 2)
        pygame.draw.circle(surface, boots_color, (int(right_foot[0]), int(right_foot[1])), 2)

        # --- 背包 (背部矩形凸起) ---
        # 根据方向决定背包可见性
        if direction in [Direction.NORTH, Direction.NORTHEAST, Direction.NORTHWEST]:
            bp_x = center_x - 3
            bp_y = center_y - 3
            pygame.draw.rect(surface, equip_color, (bp_x, bp_y, 6, 5))
            pygame.draw.rect(surface, equip_dark, (bp_x, bp_y, 6, 5), 1)
            # 背包带
            pygame.draw.line(surface, equip_dark, (bp_x + 1, bp_y), (bp_x + 1, bp_y - 2), 1)
            pygame.draw.line(surface, equip_dark, (bp_x + 4, bp_y), (bp_x + 4, bp_y - 2), 1)
        elif direction in [Direction.WEST, Direction.NORTHWEST]:
            bp_x = center_x - 5
            bp_y = center_y - 2
            pygame.draw.rect(surface, equip_color, (bp_x, bp_y, 3, 5))
            pygame.draw.rect(surface, equip_dark, (bp_x, bp_y, 3, 5), 1)
        elif direction in [Direction.EAST, Direction.NORTHEAST]:
            bp_x = center_x + 2
            bp_y = center_y - 2
            pygame.draw.rect(surface, equip_color, (bp_x, bp_y, 3, 5))
            pygame.draw.rect(surface, equip_dark, (bp_x, bp_y, 3, 5), 1)

        # --- 身体 (躯干) - 椭圆形增强版 ---
        body_width_mod = dir_params['body_width_mod']
        body_height_mod = dir_params.get('body_height_mod', 0)
        base_body_width = 8
        base_body_height = 9
        adjusted_body_width = max(4, min(14, base_body_width + body_width_mod))
        adjusted_body_height = max(6, min(12, base_body_height + body_height_mod))

        # *** 椭圆形身体 (替代矩形 - 更自然的CC2风格!) ***
        torso_ellipse = (
            center_x - adjusted_body_width // 2,
            center_y - 4 - (body_height_mod // 2),
            adjusted_body_width,
            adjusted_body_height
        )
        pygame.draw.ellipse(surface, body_color, torso_ellipse)

        # 肩部 (根据方向调整宽度和倾斜)
        shoulder_width = 10 + body_width_mod
        shoulder_tilt = dir_params.get('shoulder_tilt', 0)
        shoulder_y_offset = int(shoulder_tilt * 0.1)  # 倾斜导致的垂直偏移
        pygame.draw.ellipse(surface, body_light,
                           (center_x - shoulder_width // 2,
                            center_y - 5 + shoulder_y_offset,
                            shoulder_width, 4))

        # --- 弹药带 (胸前横线) - 根据equipment_visibility控制可见性 ---
        equip_vis = dir_params.get('equipment_visibility', 1.0)
        if direction in [Direction.SOUTH, Direction.SOUTHEAST, Direction.SOUTHWEST] and equip_vis > 0.6:
            pygame.draw.line(surface, ammo_color,
                             (center_x - 3, center_y - 1), (center_x + 3, center_y - 1), 1)
            pygame.draw.line(surface, ammo_color,
                             (center_x - 2, center_y + 1), (center_x + 2, center_y + 1), 1)

        # --- 水壶 (腰部小圆) - 根据equipment_visibility控制可见性 ---
        if equip_vis > 0.5 and direction in [Direction.SOUTH, Direction.SOUTHEAST, Direction.SOUTHWEST, Direction.EAST, Direction.WEST]:
            canteen_x = center_x + (3 if direction in [Direction.EAST, Direction.SOUTHEAST] else -3)
            canteen_y = center_y + 2
            canteen_size = max(1, int(2 * equip_vis))
            pygame.draw.circle(surface, canteen_color, (canteen_x, canteen_y), canteen_size)
            if canteen_size > 1:
                pygame.draw.circle(surface, equip_dark, (canteen_x, canteen_y), canteen_size, 1)

        # --- 头部 - CC2比例修正: 头小身大 (头:身 ≈ 1:3) ---
        head_center = (center_x, center_y - 6)
        helmet_size_mod = dir_params.get('helmet_size_mod', 0)
        # *** 修复: 基础头盔半径 4→3px (CC2标准比例) ***
        base_helmet_radius = 3
        helmet_radius = max(2, min(5, base_helmet_radius + helmet_size_mod))

        if infantry_type == InfantryType.OFFICER:
            # 军官：贝雷帽（圆形无檐帽）
            pygame.draw.circle(surface, beret_color, head_center, helmet_radius)
            if helmet_radius > 2:
                pygame.draw.circle(surface, body_dark, (head_center[0], head_center[1] - int(helmet_radius * 0.5)), max(1, helmet_radius - 2))
        else:
            # 钢盔 - 根据方向使用不同形状
            helmet_shape = dir_params.get('helmet_shape', 'circle')
            if helmet_shape == 'side_oval':
                # 侧面椭圆 (E/W方向) - 横向更宽
                oval_w = helmet_radius * 2 + 2
                oval_h = helmet_radius * 2 - 2
                pygame.draw.ellipse(surface, helmet_color,
                                   (head_center[0] - oval_w // 2, head_center[1] - oval_h // 2, oval_w, oval_h))
            elif helmet_shape == 'oval':
                # 3/4视角椭圆 (NE/SE/SW/NW方向) - 略宽
                oval_w = helmet_radius * 2 + 1
                oval_h = helmet_radius * 2
                pygame.draw.ellipse(surface, helmet_color,
                                   (head_center[0] - oval_w // 2, head_center[1] - oval_h // 2, oval_w, oval_h))
            else:
                # 正圆 (N/S方向)
                pygame.draw.circle(surface, helmet_color, head_center, helmet_radius)

            # 钢盔边缘高光线（1px亮色线）- 根据方向调整位置
            highlight_offset = dir_params['helmet_highlight_offset']
            adjusted_head_center = (
                head_center[0] + highlight_offset[0],
                head_center[1] + highlight_offset[1]
            )
            highlight_diameter = helmet_radius * 2
            if highlight_diameter >= 4:
                pygame.draw.arc(
                    surface, helmet_highlight,
                    (adjusted_head_center[0] - helmet_radius, adjusted_head_center[1] - helmet_radius, highlight_diameter, highlight_diameter),
                    math.radians(200), math.radians(340), 1,
                )
            # 面部阴影（头盔下方的暗色区域）
            if helmet_radius >= 3:
                pygame.draw.arc(
                    surface, helmet_dark,
                    (head_center[0] - helmet_radius, head_center[1] - helmet_radius, highlight_diameter, highlight_diameter),
                    0, math.pi, 1,
                )

        # 面部（根据face_visible参数决定可见性）
        face_visible = dir_params.get('face_visible', False)
        if face_visible or direction in [Direction.SOUTH, Direction.SOUTHEAST, Direction.SOUTHWEST]:
            pygame.draw.arc(
                surface, skin_color,
                (head_center[0] - 3, head_center[1] - 2, 6, 4),
                0, math.pi, 1,
            )
            # 面部阴影
            pygame.draw.line(surface, skin_shadow,
                             (head_center[0] - 2, head_center[1] + 1),
                             (head_center[0] + 2, head_center[1] + 1), 1)

        # --- 武器绘制（根据步兵类型差异化） ---
        PixelArtist3D._draw_infantry_weapon(
            surface, direction, infantry_type, center_x, center_y,
            weapon_color, weapon_metal, weapon_wood, equip_color, equip_dark,
        )

        # --- 方向阴影 (根据方向偏移) ---
        shadow_offset = dir_params['shadow_offset']
        shadow_color = (0, 0, 0, 50)
        shadow_surface = pygame.Surface((24, 24), pygame.SRCALPHA)
        shadow_surface.fill(shadow_color)

        # 在角色底部绘制椭圆形阴影
        shadow_cx = center_x + shadow_offset[0]
        shadow_cy = center_y + 9 + shadow_offset[1]
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 40),
                           (shadow_cx - 4, shadow_cy - 2, 8, 4))
        surface.blit(shadow_surface, (0, 0))

        # --- 射击闪光 ---
        if state == "shoot" and frame == 1:
            weapon_start, weapon_end = PixelArtist3D._get_weapon_position(
                direction, center_x, center_y
            )
            flash_pos = (
                weapon_end[0] + (weapon_end[0] - weapon_start[0]) * 0.2,
                weapon_end[1] + (weapon_end[1] - weapon_start[1]) * 0.2,
            )
            pygame.draw.ellipse(surface, (255, 255, 100), (flash_pos[0] - 3, flash_pos[1] - 2, 6, 4))

        # --- 受击效果 ---
        if state == "hit":
            overlay = surface.copy()
            overlay.fill((255, 0, 0, 100))
            surface.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

        return surface

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
        - face_visible: 面部是否可见 (N/NE/NW=True, 其余=False)
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
                'face_visible': True,
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
                'face_visible': True,
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
                'face_visible': False,
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
                'face_visible': False,
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
                'face_visible': False,
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
                'face_visible': False,
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
                'face_visible': False,
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
                'face_visible': True,
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
    def _draw_infantry_prone(
        surface, direction, state, frame, palette, infantry_type,
        body_color, body_dark, body_light, helmet_color, helmet_dark,
        helmet_highlight, skin_color, skin_shadow, weapon_color,
        weapon_metal, weapon_wood, boots_color, equip_color,
        equip_dark, canteen_color, ammo_color, beret_color,
    ):
        """
        趴姿渲染（长条形轮廓）- 用于crawl/defend/attack状态

        基于CC2原版 + WWII战术观察:
        - 爬行/防守/进攻时士兵趴下以减小受弹面积
        - 身体呈长条形（长度>>宽度），贴地
        - 方向性极明显：长轴对准朝向方向
        - 头部在一端，脚在另一端
        - 武器根据方向伸出

        视觉特征:
        - 身体: 14-18px长 × 4-6px宽的椭圆
        - 头部: 3px圆形，位于"前"端
        - 武器: 从身体前端伸出
        - 腿部: 简化为身体后端的延伸
        """
        import pygame
        import math

        cx, cy = 12, 12  # 中心点

        # 方向角度映射（用于计算趴姿朝向）
        direction_angles = {
            Direction.NORTH: 270,      # 头朝上
            Direction.NORTHEAST: 315,   # 头朝右上
            Direction.EAST: 0,          # 头朝右
            Direction.SOUTHEAST: 45,    # 头朝右下
            Direction.SOUTH: 90,        # 头朝下
            Direction.SOUTHWEST: 135,   # 头朝左下
            Direction.WEST: 180,        # 头朝左
            Direction.NORTHWEST: 225,   # 头朝左上
        }
        angle_rad = math.radians(direction_angles.get(direction, 0))

        # *** 身体参数（长条形!）***
        body_length = 16  # 长度（沿方向轴）
        body_width = 5     # 宽度（垂直于方向轴）

        # 计算身体椭圆的偏移量
        half_len = body_length // 2
        half_wid = body_width // 2

        # 身体中心到头部的向量
        head_offset_x = int(math.cos(angle_rad) * (half_len - 2))
        head_offset_y = int(math.sin(angle_rad) * (half_len - 2))

        # 头部位置（身体"前"端）
        head_x = cx + head_offset_x
        head_y = cy + head_offset_y

        # 脚部位置（身体"后"端）
        foot_x = cx - head_offset_x
        foot_y = cy - head_offset_y

        # *** 绘制长条形身体（使用旋转的椭圆近似）***
        # 由于pygame不直接支持旋转椭圆，我们用多边形模拟
        num_points = 12
        body_points = []
        for i in range(num_points):
            t = 2 * math.pi * i / num_points
            # 椭圆参数方程
            px = (body_length // 2) * math.cos(t)
            py = (body_width // 2) * math.sin(t)
            # 旋转变换
            rx = px * math.cos(angle_rad) - py * math.sin(angle_rad)
            ry = px * math.sin(angle_rad) + py * math.cos(angle_rad)
            body_points.append((cx + int(rx), cy + int(ry)))

        if len(body_points) >= 3:
            pygame.draw.polygon(surface, body_color, body_points)
            # 身体边缘暗线（增强立体感）
            pygame.draw.polygon(surface, body_dark, body_points, 1)

        # *** 头部（小圆，位于身体前端）- 俯视视角下头部更小 ***
        # *** 修复: 趴姿头部 3→2px (俯视比例: 头部只是一个小点) ***
        head_radius = 2 if infantry_type != InfantryType.OFFICER else 1
        if infantry_type == InfantryType.OFFICER:
            pygame.draw.circle(surface, beret_color, (head_x, head_y), head_radius)
        else:
            pygame.draw.circle(surface, helmet_color, (head_x, head_y), head_radius)
            # 头盔高光（1px亮点）
            highlight_offset_x = int(math.cos(angle_rad - 0.5) * 1)
            highlight_offset_y = int(math.sin(angle_rad - 0.5) * 1)
            pygame.draw.circle(surface, helmet_highlight,
                               (head_x + highlight_offset_x, head_y + highlight_offset_y), 1)

        # *** 武器（从头部位置向前伸出）***
        weapon_length = 8 if infantry_type not in [InfantryType.OFFICER, InfantryType.MG] else 6
        weapon_end_x = head_x + int(math.cos(angle_rad) * weapon_length)
        weapon_end_y = head_y + int(math.sin(angle_rad) * weapon_length)

        if infantry_type == InfantryType.MG:
            # 机枪：更粗的武器线
            pygame.draw.line(surface, weapon_metal, (head_x, head_y), (weapon_end_x, weapon_end_y), 2)
            # 两脚架（趴姿特有！）
            bipod_len = 3
            perp_angle = angle_rad + math.pi / 2
            bipod1_x = head_x + int(math.cos(perp_angle) * bipod_len)
            bipod1_y = head_y + int(math.sin(perp_angle) * bipod_len)
            bipod2_x = head_x - int(math.cos(perp_angle) * bipod_len)
            bipod2_y = head_y - int(math.sin(perp_angle) * bipod_len)
            pygame.draw.line(surface, weapon_wood, (head_x, head_y), (bipod1_x, bipod1_y), 1)
            pygame.draw.line(surface, weapon_wood, (head_x, head_y), (bipod2_x, bipod2_y), 1)
        elif infantry_type == InfantryType.AT:
            # 反坦克武器：短粗火箭筒
            pygame.draw.line(surface, weapon_color, (head_x, head_y), (weapon_end_x, weapon_end_y), 3)
            # 火箭筒后座标记
            rear_x = head_x - int(math.cos(angle_rad) * 2)
            rear_y = head_y - int(math.sin(angle_rad) * 2)
            pygame.draw.circle(surface, (60, 60, 60), (rear_x, rear_y), 2)
        elif infantry_type == InfantryType.OFFICER:
            # 军官手枪：短武器
            pistol_end_x = head_x + int(math.cos(angle_rad) * 5)
            pistol_end_y = head_y + int(math.sin(angle_rad) * 5)
            pygame.draw.line(surface, weapon_color, (head_x, head_y), (pistol_end_x, pistol_end_y), 1)
        else:
            # 步枪手/狙击手：标准步枪
            pygame.draw.line(surface, weapon_color, (head_x, head_y), (weapon_end_x, weapon_end_y), 2)
            # 枪托
            stock_x = head_x - int(math.cos(angle_rad) * 2)
            stock_y = head_y - int(math.sin(angle_rad) * 2)
            pygame.draw.line(surface, weapon_wood, (stock_x, stock_y), (head_x, head_y), 2)

        # *** 腿部（简化为身体后端的小延伸）***
        leg_extend = 3
        leg_end_x = foot_x - int(math.cos(angle_rad) * leg_extend)
        leg_end_y = foot_y - int(math.sin(angle_rad) * leg_extend)
        pygame.draw.line(surface, body_dark, (foot_x, foot_y), (leg_end_x, leg_end_y), 2)
        # 靴子
        pygame.draw.circle(surface, boots_color, (leg_end_x, leg_end_y), 2)

        # *** 趴姿特有细节：肘部支撑 ***
        elbow_offset = 4
        perp_angle = angle_rad + math.pi / 2
        elbow_x = cx + int(math.cos(perp_angle) * elbow_offset)
        elbow_y = cy + int(math.sin(perp_angle) * elbow_offset)
        pygame.draw.circle(surface, skin_color, (elbow_x, elbow_y), 2)
        # 前臂（支撑地面）
        forearm_end_x = elbow_x + int(math.cos(angle_rad) * 3)
        forearm_end_y = elbow_y + int(math.sin(angle_rad) * 3)
        pygame.draw.line(surface, skin_color, (elbow_x, elbow_y), (forearm_end_x, forearm_end_y), 1)

        return surface

    @staticmethod
    def _draw_infantry_death(
        surface, direction, frame, palette, infantry_type,
        body_color, body_dark, body_light, helmet_color, helmet_dark,
        helmet_highlight, skin_color, skin_shadow, weapon_color,
        weapon_metal, weapon_wood, boots_color, equip_color,
        equip_dark, canteen_color, ammo_color, beret_color,
        center_x, center_y, dx, dy,
    ):
        """
        死亡动画4帧序列：
        帧0: 正常站立
        帧1: 身体前倾
        帧2: 倒地一半
        帧3: 完全倒地
        """
        import pygame

        if frame == 0:
            # 帧0: 正常站立 - 绘制完整角色
            # 腿部
            left_hip = (center_x - 2, center_y + 5)
            right_hip = (center_x + 2, center_y + 5)
            left_foot = (center_x - 2, center_y + 9)
            right_foot = (center_x + 2, center_y + 9)
            pygame.draw.line(surface, body_dark, left_hip, left_foot, 2)
            pygame.draw.line(surface, body_dark, right_hip, right_foot, 2)
            pygame.draw.circle(surface, boots_color, (int(left_foot[0]), int(left_foot[1])), 2)
            pygame.draw.circle(surface, boots_color, (int(right_foot[0]), int(right_foot[1])), 2)

            # 身体
            torso_rect = pygame.Rect(center_x - 4, center_y - 4, 8, 9)
            pygame.draw.rect(surface, body_color, torso_rect, border_radius=2)
            pygame.draw.ellipse(surface, body_light, (center_x - 5, center_y - 5, 10, 4))

            # 头部
            head_center = (center_x, center_y - 6)
            if infantry_type == InfantryType.OFFICER:
                pygame.draw.circle(surface, beret_color, head_center, 4)
            else:
                pygame.draw.circle(surface, helmet_color, head_center, 4)

            # 武器
            PixelArtist3D._draw_infantry_weapon(
                surface, direction, infantry_type, center_x, center_y,
                weapon_color, weapon_metal, weapon_wood, equip_color, equip_dark,
            )

        elif frame == 1:
            # 帧1: 身体前倾 - 整体向下倾斜
            lean_offset = 3
            # 腿部（微曲）
            left_hip = (center_x - 2, center_y + 5)
            right_hip = (center_x + 2, center_y + 5)
            left_foot = (center_x - 1, center_y + 8)
            right_foot = (center_x + 1, center_y + 8)
            pygame.draw.line(surface, body_dark, left_hip, left_foot, 2)
            pygame.draw.line(surface, body_dark, right_hip, right_foot, 2)

            # 身体前倾
            lean_cx = center_x + dx
            lean_cy = center_y + lean_offset
            torso_rect = pygame.Rect(lean_cx - 4, lean_cy - 3, 8, 8)
            pygame.draw.rect(surface, body_color, torso_rect, border_radius=2)

            # 头部下移
            head_center = (lean_cx, lean_cy - 4)
            if infantry_type == InfantryType.OFFICER:
                pygame.draw.circle(surface, beret_color, head_center, 3)
            else:
                pygame.draw.circle(surface, helmet_color, head_center, 3)

            # 武器下垂
            weapon_start, weapon_end = PixelArtist3D._get_weapon_position(direction, lean_cx, lean_cy + 2)
            pygame.draw.line(surface, weapon_color, weapon_start, weapon_end, 1)

        elif frame == 2:
            # 帧2: 倒地一半 - 身体横向
            ground_y = center_y + 6
            # 身体横躺
            body_left = center_x - 5
            body_right = center_x + 5
            pygame.draw.line(surface, body_color, (body_left, ground_y), (body_right, ground_y), 4)

            # 头部在地面
            head_x = body_left - 2
            if infantry_type == InfantryType.OFFICER:
                pygame.draw.circle(surface, beret_color, (head_x, ground_y), 3)
            else:
                pygame.draw.circle(surface, helmet_color, (head_x, ground_y), 3)

            # 腿部弯曲
            pygame.draw.line(surface, body_dark, (body_right, ground_y), (body_right + 3, ground_y - 2), 2)
            pygame.draw.line(surface, body_dark, (body_right, ground_y), (body_right + 2, ground_y + 1), 2)

            # 武器掉落
            pygame.draw.line(surface, weapon_color, (body_left - 3, ground_y + 2), (body_left + 2, ground_y + 2), 1)

        elif frame >= 3:
            # 帧3: 完全倒地 - 平躺在地面
            ground_y = center_y + 8
            # 身体完全横躺
            body_left = center_x - 6
            body_right = center_x + 6
            pygame.draw.line(surface, body_color, (body_left, ground_y), (body_right, ground_y), 3)

            # 头部
            head_x = body_left - 2
            if infantry_type == InfantryType.OFFICER:
                pygame.draw.circle(surface, beret_color, (head_x, ground_y), 3)
            else:
                pygame.draw.circle(surface, helmet_color, (head_x, ground_y), 3)

            # 腿部伸展
            pygame.draw.line(surface, body_dark, (body_right, ground_y), (body_right + 4, ground_y), 2)
            pygame.draw.line(surface, body_dark, (body_right, ground_y), (body_right + 3, ground_y + 1), 2)

            # 靴子
            pygame.draw.circle(surface, boots_color, (body_right + 4, ground_y), 1)

            # 武器掉落
            pygame.draw.line(surface, weapon_color, (body_left - 4, ground_y + 2), (body_left + 1, ground_y + 2), 1)

            # 暗化效果
            dark_overlay = pygame.Surface((24, 24), pygame.SRCALPHA)
            dark_overlay.fill((100, 100, 100, 150))
            surface.blit(dark_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        return surface

    # 坦克尺寸差异化系统 - 基于历史重量分级
    # 参考: WWII坦克实际尺寸比例 + CC2视觉层次需求
    TANK_SIZES = {
        TankType.SHERMAN_M4: (36, 36),      # 中型坦克: 标准尺寸
        TankType.PANTHER_AUSFG: (38, 38),    # 中型偏重: 稍大（大倾角装甲+宽车体）
        TankType.TIGER_I: (44, 44),          # 重型坦克: 明显更大（"移动碉堡"）
    }

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
        tank_w, tank_h = PixelArtist3D.TANK_SIZES[tank_type]

        surface = pygame.Surface((tank_w, tank_h), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        # 获取历史准确性的调色板
        tp = PixelArtist3D.TANK_PALETTES[tank_type]

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
    def _draw_sherman_m4(
        surface, direction, turret_direction, state, frame, tp, cx, cy
    ):
        """绘制Sherman M4中型坦克 - 基于历史参考的精确渲染

        历史特征:
        - 圆润前部车体 + 平直侧面上部（独特轮廓）
        - 小型圆形炮塔（非豹式大炮塔）
        - 75mm M3中长炮管（非虎式88mm长炮管）
        - VVSS悬挂系统：每侧3个可见负重轮，后部抬高回程轮
        - 车长指挥塔（右侧小圆顶）
        - .50 cal M2机枪（炮塔顶部圆形基座）
        - 白色星标（炮塔顶部，~8px）
        - 泥土风化效果（诺曼底战场特征）
        """
        import pygame

        dir_idx = direction.value % 8
        turret_dir_idx = turret_direction.value % 8

        # --- 履带 (VVSS特征: 较窄, 3组负重轮) ---
        track_h = 9
        track_left_x = 2
        track_right_x = 30

        pygame.draw.rect(surface, tp['track_color'], (track_left_x, 27, 4, track_h))
        pygame.draw.rect(surface, tp['track_color'], (track_right_x, 27, 4, track_h))

        # 履带纹理（横线条纹 + 锐迹点缀 + ***履带齿***）
        for ty in range(27, 27 + track_h, 2):
            pygame.draw.line(surface, (55, 55, 55), (track_left_x, ty), (track_left_x + 4, ty), 1)
            pygame.draw.line(surface, (55, 55, 55), (track_right_x, ty), (track_right_x + 4, ty), 1)

        # *** 履带齿 (Track Teeth - CC2特征!) ***
        tooth_color = (70, 68, 60)
        for tx in range(track_left_x - 1, track_left_x + 5, 3):
            pygame.draw.line(surface, tooth_color, (tx, 26), (tx, 27 + track_h), 1)
        for tx in range(track_right_x - 1, track_right_x + 5, 3):
            pygame.draw.line(surface, tooth_color, (tx, 26), (tx, 27 + track_h), 1)

        # VVSS负重轮: 3个可见轮子（历史准确性！）
        wheel_y = 29
        wheel_positions = [7, 13, 19, 25]  # 4个位置但中间2-3个可见
        for i, wx in enumerate(wheel_positions[1:4]):  # 显示3个中间轮
            pygame.draw.circle(surface, (30, 30, 30), (wx, wheel_y), 2)
            pygame.draw.circle(surface, tp['track_rust'], (wx, wheel_y), 1)  # 锈迹轮毂

        # 后部回程轮（VVSS特征: 抬高位置）
        return_roller_y = 25
        pygame.draw.circle(surface, (35, 35, 35), (10, return_roller_y), 1)
        pygame.draw.circle(surface, (35, 35, 35), (26, return_roller_y), 1)

        # --- 车体 (圆润前部 + 平直侧面) ---
        body_top = 12
        for row in range(body_top, 26):
            t = (row - body_top) / max(26 - body_top, 1)
            left = int(4 + t * 2)  # 圆润前缘
            right = int(32 - 4 - t * 2)
            pygame.draw.rect(surface, tp['body_base'], (left, row, right - left, 1))

        # 车体边框
        pygame.draw.rect(surface, tp['body_dark'], (6, 13, 24, 12), 1)

        # *** 装甲板接缝线 (1px深色线条 - 增强立体感和历史真实性!) ***
        # 参考: WWII坦克制造工艺 - 铆接/焊接装甲板之间的可见接缝
        seam_color = (max(0, tp['body_dark'][0] - 15),
                      max(0, tp['body_dark'][1] - 15),
                      max(0, tp['body_dark'][2] - 15))
        # 前装甲板上沿接缝
        pygame.draw.line(surface, seam_color, (8, 14), (28, 14), 1)
        # 车体侧面垂直接缝（引擎舱隔板位置）
        pygame.draw.line(surface, seam_color, (18, 14), (18, 25), 1)
        # 炮塔座圈接缝线（车体与炮塔连接处）
        pygame.draw.ellipse(surface, seam_color, (10, 11, 16, 3), 1)

        # 泥土污渍效果（诺曼底战场特征）- 车体下部暗色条纹
        mud_line_y = 24
        for mx in range(6, 30, 3):
            mud_length = __import__('random').randint(2, 4)
            pygame.draw.line(surface, tp['mud_dirt'],
                           (mx, mud_line_y), (mx + mud_length, mud_line_y + 1), 1)

        # --- 前机枪 ---
        mg_positions = {
            Direction.NORTH: (cx, 12),
            Direction.NORTHEAST: (cx + 5, 13),
            Direction.EAST: (cx + 8, cy),
            Direction.SOUTHEAST: (cx + 5, 24),
            Direction.SOUTH: (cx, 25),
            Direction.SOUTHWEST: (cx - 5, 24),
            Direction.WEST: (cx - 8, cy),
            Direction.NORTHWEST: (cx - 5, 13),
        }
        mg_pos = mg_positions.get(direction, (cx, 12))
        pygame.draw.circle(surface, (40, 40, 40), mg_pos, 1)

        # --- 排气管 ---
        exhaust_positions = {
            Direction.NORTH: (28, 20),
            Direction.NORTHEAST: (29, 22),
            Direction.EAST: (30, 20),
            Direction.SOUTHEAST: (29, 18),
            Direction.SOUTH: (28, 18),
            Direction.SOUTHWEST: (7, 18),
            Direction.WEST: (5, 20),
            Direction.NORTHWEST: (7, 22),
        }
        exh_pos = exhaust_positions.get(direction, (28, 20))
        pygame.draw.rect(surface, (50, 50, 50), (exh_pos[0], exh_pos[1], 3, 2))
        pygame.draw.rect(surface, tp['body_dark'], (exh_pos[0], exh_pos[1], 3, 2), 1)

        # --- 炮塔 (小型圆形炮塔 - Sherman特征!) ---
        tw, th = 16, 11  # 比通用版稍小（Sherman小炮塔）
        tx = (36 - tw) // 2
        ty = 4
        pygame.draw.rect(surface, tp['turret_base'], (tx, ty, tw, th), border_radius=3)  # 更圆角
        pygame.draw.ellipse(surface, tp['turret_dark'], (tx + 2, ty + 2, tw - 4, th - 4))

        # *** 炮塔装甲板缝线 (增强炮塔独立性和立体感!) ***
        # 炮塔顶部中线接缝（铸造炮塔的合模线）
        pygame.draw.line(surface, seam_color, (cx, ty + 2), (cx, ty + th - 2), 1)
        # 炮塔侧面弧形接缝
        pygame.draw.arc(surface, seam_color, (tx + 1, ty + 1, tw - 2, th - 2), 0.5, 2.6, 1)

        # --- 车长指挥塔 (右侧小圆顶 - Sherman特有!) ---
        cupola_cx = cx + 4
        cupola_cy = ty + th // 2
        pygame.draw.circle(surface, tp['cupola'], (cupola_cx, cupola_cy), 2)
        pygame.draw.circle(surface, tp['turret_dark'], (cupola_cx, cupola_cy), 2, 1)

        # --- .50 cal机枪座 (炮塔顶部 - Sherman特征!) ---
        mg_mount_cx = cx - 3
        mg_mount_cy = ty + 3
        pygame.draw.circle(surface, tp['mg_mount'], (mg_mount_cx, mg_mount_cy), 1)

        # --- 炮管 (75mm M3 中等长度!) ---
        gun_lengths = [th + 2, th + 3, th + 4, th + 3, th + 2, th + 3, th + 4, th + 3]
        gl = gun_lengths[turret_dir_idx]
        dx = [0, 2, 4, 2, 0, -2, -4, -2][turret_dir_idx]
        dy = [-1, -1, 0, 1, 1, 1, 0, -1][turret_dir_idx]

        gx = cx + dx * 2
        gy = ty + th // 2 - 2
        gun_end_x = gx + dx * (gl // 3)
        gun_end_y = gy + dy * (gl // 3)
        pygame.draw.line(surface, tp['gun_barrel'], (gx, gy), (gun_end_x, gun_end_y), 2)

        # 制退器
        muzzle_x = gun_end_x
        muzzle_y = gun_end_y
        if dx == 0:
            pygame.draw.rect(surface, (60, 60, 60), (muzzle_x - 2, muzzle_y - 1, 4, 2))
        elif dy == 0:
            pygame.draw.rect(surface, (60, 60, 60), (muzzle_x - 1, muzzle_y - 2, 2, 4))
        else:
            pygame.draw.rect(surface, (60, 60, 60), (muzzle_x - 1, muzzle_y - 1, 3, 2))

        # --- 白色星标 (炮塔顶部, ~6px - 盟军标识!) ---
        star_cx, star_cy = cx, 21
        PixelArtist3D._draw_star(surface, star_cx, star_cy, 3, tp['white_star'])

        # --- 射击闪光 ---
        if state == "shoot" and frame == 1:
            pygame.draw.ellipse(surface, (255, 255, 100), (muzzle_x - 4, muzzle_y - 3, 8, 6))

        # --- 移动尘土 ---
        if state == "move":
            dust_offset = frame % 2
            for i in range(3):
                dust_x = 6 + i * 10 + dust_offset
                dust_y = 33
                pygame.draw.circle(surface, (139, 119, 66), (dust_x, dust_y), 1 + i % 2)

    @staticmethod
    def _draw_panther_ausfg(
        surface, direction, turret_direction, state, frame, tp, cx, cy
    ):
        """绘制Panther Ausf.G坦克 - 基于历史参考的精确渲染

        历史特征:
        - 大倾角前装甲（80°倾斜角）- 非常宽的车体
        - 好装甲弧形炮塔（Mantlet形状+曲线防盾）
        - 75mm KwK42 L/70超长炮管（比Sherman长得多! ~16px on sprite）
        - Schürzen（炮塔侧面薄装甲裙板5mm，显示为细线）
        - 交错负重轮（每侧8个重叠轮 - 最显著的特征!）
        - 排气管（左侧多出口设计）
        - Dunkelgelb暗黄底色 + 可选红棕迷彩条纹
        """
        import pygame

        dir_idx = direction.value % 8
        turret_dir_idx = turret_direction.value % 8

        # --- 履带 (更宽 + 交错负重轮特征!) ---
        track_h = 10
        track_left_x = 1
        track_right_x = 31

        pygame.draw.rect(surface, tp['track_color'], (track_left_x, 26, 5, track_h))
        pygame.draw.rect(surface, tp['track_color'], (track_right_x, 26, 5, track_h))

        # 履带纹理 + ***履带齿***
        for ty in range(26, 26 + track_h, 2):
            pygame.draw.line(surface, (48, 48, 48), (track_left_x, ty), (track_left_x + 5, ty), 1)
            pygame.draw.line(surface, (48, 48, 48), (track_right_x, ty), (track_right_x + 5, ty), 1)

        # *** Panther履带齿 (更密集!) ***
        panther_tooth = (55, 53, 45)
        for tx in range(track_left_x - 2, track_left_x + 6, 2):
            pygame.draw.line(surface, panther_tooth, (tx, 25), (tx, 26 + track_h), 1)
        for tx in range(track_right_x - 2, track_right_x + 6, 2):
            pygame.draw.line(surface, panther_tooth, (tx, 25), (tx, 26 + track_h), 1)

        # 交错负重轮 (8个重叠轮 - Panther最显著特征!)
        wheel_y = 29
        wheel_base_positions = [5, 9, 13, 17, 21, 25, 29]  # 7个基础位置
        for i, wx in enumerate(wheel_base_positions[:6]):  # 显示6个可见轮（交错排列）
            offset_y = 1 if i % 2 == 0 else -1  # 交错上下偏移
            pygame.draw.circle(surface, (28, 28, 28), (wx, wheel_y + offset_y), 2)
            pygame.draw.circle(surface, (45, 45, 45), (wx, wheel_y + offset_y), 1)

        # --- 车体 (大倾角前装甲!) ---
        body_top = 10  # 更高车体（Panter更庞大）
        for row in range(body_top, 27):
            t = (row - body_top) / max(27 - body_top, 1)
            left = int(3 + t * 3.5)  # 更陡峭的前缘斜坡
            right = int(33 - 3 - t * 3.5)
            pygame.draw.rect(surface, tp['body_base'], (left, row, right - left, 1))

        # 迷彩条纹（可选红棕色条纹 - Normandy战场常见）
        camo_rng = __import__('random').Random(dir_idx * 42)
        if camo_rng.random() > 0.5:
            for stripe_y in range(14, 24, 3):
                stripe_start = camo_rng.randint(5, 15)
                stripe_len = camo_rng.randint(4, 10)
                pygame.draw.line(surface, tp['camo_red_brown'],
                               (stripe_start, stripe_y), (stripe_start + stripe_len, stripe_y), 1)

        # 车体边框
        pygame.draw.rect(surface, tp['body_dark'], (5, 12, 26, 14), 1)

        # *** 装甲板接缝线 (Panther特有的大倾角装甲接缝!) ***
        panther_seam = (max(0, tp['body_dark'][0] - 18),
                        max(0, tp['body_dark'][1] - 18),
                        max(0, tp['body_dark'][2] - 18))
        # 前上倾斜装甲板接缝（80°倾角的可见边缘）
        pygame.draw.line(surface, panther_seam, (8, 13), (28, 13), 1)
        # 车体侧面垂直装甲接缝（驾驶员舱/战斗室分隔）
        pygame.draw.line(surface, panther_seam, (17, 13), (17, 25), 1)
        # 炮塔座圈椭圆形接缝（宽车体的特征）
        pygame.draw.ellipse(surface, panther_seam, (8, 10, 20, 4), 1)
        # 前下装甲板斜接缝（首下装甲板的倾斜线）
        pygame.draw.line(surface, panther_seam, (6 + int(3.5 * 0.3), 22), (30 - int(3.5 * 0.3), 22), 1)

        # --- 排气管 (左侧多出口 - Panther特征!) ---
        exhaust_positions = {
            Direction.NORTH: (29, 22),
            Direction.NORTHEAST: (30, 23),
            Direction.EAST: (31, 22),
            Direction.SOUTHEAST: (30, 20),
            Direction.SOUTH: (29, 19),
            Direction.SOUTHWEST: (6, 19),
            Direction.WEST: (4, 22),
            Direction.NORTHWEST: (6, 23),
        }
        exh_pos = exhaust_positions.get(direction, (29, 22))
        # 多出口排气管（矩形+多个小圆点表示出口）
        pygame.draw.rect(surface, tp['exhaust_pipe'], (exh_pos[0], exh_pos[1], 4, 3))
        pygame.draw.circle(surface, (55, 52, 48), (exh_pos[0] + 1, exh_pos[1] + 1), 1)
        pygame.draw.circle(surface, (55, 52, 48), (exh_pos[0] + 3, exh_pos[1] + 1), 1)

        # --- 炮塔 (好装甲弧形炮塔!) ---
        tw, th = 20, 13  # 更大的炮塔（Panther特征）
        tx = (36 - tw) // 2
        ty = 2
        pygame.draw.rect(surface, tp['turret_base'], (tx, ty, tw, th), border_radius=2)
        # 弧形防盾曲线（Mantlet形状）
        pygame.draw.ellipse(surface, tp['turret_dark'], (tx + 3, ty + 3, tw - 6, th - 5))

        # *** 炮塔装甲板缝线 (Panther弧形炮塔特有!) ***
        # 炮塔顶部铸造合模线
        pygame.draw.line(surface, panther_seam, (cx, ty + 3), (cx, ty + th - 3), 1)
        # 防盾弧形接缝（Mantlet与炮塔本体连接处）
        pygame.draw.arc(surface, panther_seam, (tx + 2, ty + 2, tw - 4, th - 4), 0.8, 2.4, 1)

        # Schürzen（炮塔侧面薄装甲板 - 细线表示5mm板）
        schurzen_y = ty + 4
        pygame.draw.line(surface, tp['schurzen'], (tx - 1, schurzen_y), (tx - 1, schurzen_y + 5), 1)
        pygame.draw.line(surface, tp['schurzen'], (tx + tw, schurzen_y), (tx + tw, schurzen_y + 5), 1)

        # --- 超长炮管 (75mm KwK42 L/70 - 比Sherman长得多!) ---
        gun_lengths = [th + 4, th + 5, th + 8, th + 6, th + 4, th + 6, th + 8, th + 5]
        gl = gun_lengths[turret_dir_idx]
        dx = [0, 2, 5, 2, 0, -2, -5, -2][turret_dir_idx]
        dy = [-1, -1, 0, 1, 1, 1, 0, -1][turret_dir_idx]

        gx = cx + dx * 2
        gy = ty + th // 2 - 2
        gun_end_x = gx + dx * (gl // 3)
        gun_end_y = gy + dy * (gl // 3)
        pygame.draw.line(surface, tp['gun_barrel'], (gx, gy), (gun_end_x, gun_end_y), 2)

        # 制退器（双室制退器 - Panther特征）
        muzzle_x = gun_end_x
        muzzle_y = gun_end_y
        if abs(dx) >= abs(dy):
            pygame.draw.rect(surface, (55, 55, 55), (muzzle_x - 3, muzzle_y - 1, 6, 2))
        else:
            pygame.draw.rect(surface, (55, 55, 55), (muzzle_x - 1, muzzle_y - 3, 2, 6))

        # --- 铁十字标识 (轴心国标识!) ---
        cross_cx, cross_cy = cx, 20
        PixelArtist3D._draw_iron_cross(surface, cross_cx, cross_cy, tp['iron_cross'])

        # --- 射击闪光 ---
        if state == "shoot" and frame == 1:
            pygame.draw.ellipse(surface, (255, 255, 100), (muzzle_x - 5, muzzle_y - 4, 10, 8))

        # --- 移动尘土 ---
        if state == "move":
            dust_offset = frame % 2
            for i in range(4):  # 更多尘土（更重车辆）
                dust_x = 5 + i * 8 + dust_offset
                dust_y = 34
                pygame.draw.circle(surface, (139, 119, 66), (dust_x, dust_y), 1 + i % 2)

    @staticmethod
    def _draw_tiger_i(
        surface, direction, turret_direction, state, frame, tp, cx, cy
    ):
        """绘制Tiger I型重型坦克 - 基于历史参考的精确渲染

        历史特征:
        - 方正垂直装甲（无倾斜！）- 非常宽的箱体造型
        - 大矩形炮塔（平坦侧面 - 与Panther弧形形成鲜明对比）
        - 88mm KwK36 L/56长炮管（长但短于Panther L/70）
        - Portée（装甲指挥塔 - 炮塔中心位置）
        - "移动碉堡"外观（boxy shape使其看起来像行走的堡垒）
        - 宽履带（适应重量的超宽履带设计）
        """
        import pygame

        dir_idx = direction.value % 8
        turret_dir_idx = turret_direction.value % 8

        # --- 履带 (超宽 - Tiger特征!) ---
        track_h = 11
        track_left_x = 0
        track_right_x = 32

        pygame.draw.rect(surface, tp['track_color'], (track_left_x, 25, 6, track_h))
        pygame.draw.rect(surface, tp['track_color'], (track_right_x, 25, 4, track_h))

        # 履带纹理（更粗犷 + ***履带齿***）
        for ty in range(25, 25 + track_h, 2):
            pygame.draw.line(surface, (42, 42, 42), (track_left_x, ty), (track_left_x + 6, ty), 1)
            pygame.draw.line(surface, (42, 42, 42), (track_right_x, ty), (track_right_x + 4, ty), 1)

        # *** Tiger I 履带齿 (宽间距 - 重型坦克特征!) ***
        tiger_tooth = (58, 56, 48)
        for tx in range(track_left_x - 2, track_left_x + 7, 4):
            pygame.draw.line(surface, tiger_tooth, (tx, 24), (tx, 25 + track_h), 1)
        for tx in range(track_right_x - 2, track_right_x + 5, 4):
            pygame.draw.line(surface, tiger_tooth, (tx, 24), (tx, 25 + track_h), 1)

        # 负重轮（Tiger使用较简单的轮布局）
        wheel_y = 30
        wheel_positions = [8, 14, 20, 26]
        for wx in wheel_positions:
            pygame.draw.circle(surface, (25, 25, 25), (wx, wheel_y), 3)  # 更大的轮子
            pygame.draw.circle(surface, (45, 45, 45), (wx, wheel_y), 1)

        # --- 车体 (方正垂直装甲 - Tiger最显著特征!) ---
        body_top = 9  # 更高车体
        body_left = 5
        body_right = 31
        body_bottom = 26

        # 垂直侧边（无倾斜!）
        pygame.draw.rect(surface, tp['body_base'], (body_left, body_top, body_right - body_left, body_bottom - body_top))

        # 方形细节线（boxy detail lines）
        pygame.draw.rect(surface, tp['body_dark'], (body_left, body_top, body_right - body_left, body_bottom - body_top), 2)

        # *** 装甲板接缝线 (Tiger I方正箱体特有 - 强调"移动碉堡"外观!) ***
        tiger_seam = (max(0, tp['body_dark'][0] - 20),
                      max(0, tp['body_dark'][1] - 20),
                      max(0, tp['body_dark'][2] - 20))
        # 前上装甲板水平接缝（垂直装甲板的可见边缘）
        pygame.draw.line(surface, tiger_seam, (body_left + 1, body_top + 4), (body_right - 1, body_top + 4), 1)
        # 前下装甲板水平接缝（驾驶员舱盖位置）
        pygame.draw.line(surface, tiger_seam, (body_left + 2, body_top + 10), (body_right - 2, body_top + 10), 1)
        # 车体侧面垂直接缝（驾驶员/无线电员/炮手舱位分隔）
        pygame.draw.line(surface, tiger_seam, (body_left + 10, body_top + 2), (body_left + 10, body_bottom - 2), 1)
        pygame.draw.line(surface, tiger_seam, (body_right - 12, body_top + 2), (body_right - 12, body_bottom - 2), 1)
        # 炮塔座圈方形接缝（方正车体的特征）
        pygame.draw.rect(surface, tiger_seam, (body_left + 3, body_top, body_right - body_left - 6, 5), 1)
        # 引擎舱后部接缝
        pygame.draw.line(surface, tiger_seam, (body_left + 2, body_bottom - 5), (body_right - 2, body_bottom - 5), 1)

        # 前装甲板（垂直但略呈矩形）
        front_armor_points = [
            (body_left, body_top + 3),
            (body_right, body_top + 3),
            (body_right, body_top + 8),
            (body_left + 3, body_top + 8),
        ]
        pygame.draw.polygon(surface, tp['body_light'], front_armor_points)
        pygame.draw.polygon(surface, tp['boxy_detail'], front_armor_points, 1)

        # 可见红色底漆区域（部分Tiger在磨损处露出红底漆）
        primer_rng = __import__('random').Random(dir_idx * 77)
        if primer_rng.random() > 0.6:
            primer_x = primer_rng.randint(body_left + 2, body_right - 4)
            primer_y = primer_rng.randint(body_top + 10, body_bottom - 3)
            pygame.draw.rect(surface, tp['red_primer'], (primer_x, primer_y, 3, 2))

        # --- 排气管 ---
        exhaust_positions = {
            Direction.NORTH: (28, 20),
            Direction.NORTHEAST: (29, 22),
            Direction.EAST: (30, 20),
            Direction.SOUTHEAST: (29, 18),
            Direction.SOUTH: (28, 17),
            Direction.SOUTHWEST: (7, 17),
            Direction.WEST: (5, 20),
            Direction.NORTHWEST: (7, 22),
        }
        exh_pos = exhaust_positions.get(direction, (28, 20))
        pygame.draw.rect(surface, (50, 50, 50), (exh_pos[0], exh_pos[1], 4, 2))
        pygame.draw.rect(surface, tp['body_dark'], (exh_pos[0], exh_pos[1], 4, 2), 1)

        # --- 炮塔 (大矩形炮塔 - Tiger最显著特征!) ---
        tw, th = 22, 14  # 最大炮塔（Tiger特征）
        tx = (36 - tw) // 2
        ty = 1
        pygame.draw.rect(surface, tp['turret_base'], (tx, ty, tw, th), border_radius=1)  # 低圆角=方正
        # 平坦侧面（与Panther弧形对比!）
        pygame.draw.rect(surface, tp['turret_dark'], (tx + 2, ty + 2, tw - 4, th - 4), 1)

        # *** 炮塔装甲板缝线 (Tiger I矩形炮塔特有 - 强调方正造型!) ***
        # 炮塔顶部中线接缝（矩形铸造炮塔的合模线）
        pygame.draw.line(surface, tiger_seam, (cx, ty + 2), (cx, ty + th - 2), 1)
        # 炮塔侧面垂直接缝（炮手/装填手舱盖位置）
        pygame.draw.line(surface, tiger_seam, (tx + tw // 3, ty + 3), (tx + tw // 3, ty + th - 3), 1)
        pygame.draw.line(surface, tiger_seam, (tx + 2 * tw // 3, ty + 3), (tx + 2 * tw // 3, ty + th - 3), 1)
        # 炮塔底部座圈方形接缝
        pygame.draw.rect(surface, tiger_seam, (tx + 1, ty + th - 3, tw - 2, 3), 1)

        # Portée（装甲指挥塔 - 炮塔中心!）
        porte_cx = cx
        porte_cy = ty + th // 2
        pygame.draw.circle(surface, tp['porte_cupola'], (porte_cx, porte_cy), 3)
        pygame.draw.circle(surface, tp['turret_dark'], (porte_cx, porte_cy), 3, 1)
        # 指挥塔舱盖线
        pygame.draw.line(surface, (60, 60, 56), (porte_cx - 1, porte_cy - 2), (porte_cx + 1, porte_cy - 2), 1)

        # --- 88mm KwK36 L/56炮管 (长但短于Panther!) ---
        gun_lengths = [th + 3, th + 4, th + 6, th + 5, th + 3, th + 5, th + 6, th + 4]
        gl = gun_lengths[turret_dir_idx]
        dx = [0, 2, 5, 2, 0, -2, -5, -2][turret_dir_idx]
        dy = [-1, -1, 0, 1, 1, 1, 0, -1][turret_dir_idx]

        gx = cx + dx * 2
        gy = ty + th // 2 - 2
        gun_end_x = gx + dx * (gl // 3)
        gun_end_y = gy + dy * (gl // 3)
        pygame.draw.line(surface, tp['gun_barrel'], (gx, gy), (gun_end_x, gun_end_y), 3)  # 更粗炮管!

        # 双室制退器（球形制退器 - Tiger特征）
        muzzle_x = gun_end_x
        muzzle_y = gun_end_y
        pygame.draw.circle(surface, (60, 60, 60), (int(muzzle_x), int(muzzle_y)), 3)
        pygame.draw.circle(surface, tp['gun_barrel'], (int(muzzle_x), int(muzzle_y)), 2, 1)

        # --- 铁十字标识 (轴心国标识!) ---
        cross_cx, cross_cy = cx, 19
        PixelArtist3D._draw_iron_cross(surface, cross_cx, cross_cy, tp['iron_cross'])

        # --- 射击闪光 ---
        if state == "shoot" and frame == 1:
            pygame.draw.ellipse(surface, (255, 255, 100), (muzzle_x - 6, muzzle_y - 4, 12, 8))

        # --- 移动尘土（大量尘土 - 超重型车辆！）---
        if state == "move":
            dust_offset = frame % 2
            for i in range(5):  # 最多尘土（最重车辆）
                dust_x = 4 + i * 7 + dust_offset
                dust_y = 35
                if dust_x < 36:
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
        """
        创建半履带车精灵 (32×40 px, 正交俯视)

        CC2视觉规格:
        - 尺寸: ~32×40像素 (宽大于高)
        - 形状: 矩形车身 + 开放式后部货舱
        - 前部: 两轮可见 (小圆，~4px直径)
        - 后部: 单条宽履带 (矩形~6px宽)
        - 车身: 开顶货舱 (可见内部轮廓)
        - MG位置: 前右侧小枪管

        Args:
            direction: 8方向之一
            faction: ALLIES 或 AXIS
            state: idle/move/shoot
            frame: 动画帧号

        Returns:
            32×40 pygame.Surface (带alpha通道)
        """
        import pygame

        surface = pygame.Surface((32, 40), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        if faction == Faction.ALLIES:
            body_color = (74, 93, 35)      # OD green #4A5D23
            dark_color = (56, 70, 26)      # Darker tracks
            track_color = (40, 45, 35)     # Track color
            wheel_color = (30, 30, 30)     # Wheel
        else:
            body_color = (85, 93, 80)      # Field gray #555D50
            dark_color = (65, 72, 62)      # Darker
            track_color = (50, 55, 48)     # Track
            wheel_color = (35, 35, 35)     # Wheel

        cx, cy = 16, 20

        dir_idx = direction.value % 8

        # --- 履带 (后部宽矩形) ---
        # 根据方向调整位置和大小
        if direction in [Direction.NORTH, Direction.SOUTH]:
            track_w, track_h = 6, 12
            track_x_left = cx - 14
            track_x_right = cx + 8
            track_y = cy + 8
            pygame.draw.rect(surface, track_color, (track_x_left, track_y, track_w, track_h))
            pygame.draw.rect(surface, track_color, (track_x_right, track_y, track_w, track_h))
            # 履带纹理
            for ty_offset in range(0, track_h, 2):
                pygame.draw.line(surface, dark_color,
                               (track_x_left, track_y + ty_offset),
                               (track_x_left + track_w, track_y + ty_offset), 1)
                pygame.draw.line(surface, dark_color,
                               (track_x_right, track_y + ty_offset),
                               (track_x_right + track_w, track_y + ty_offset), 1)
        elif direction in [Direction.EAST, Direction.WEST]:
            track_w, track_h = 10, 6
            track_y_top = cy - 12
            track_y_bottom = cy + 8
            track_x = cx - 5 if direction == Direction.EAST else cx - 5
            pygame.draw.rect(surface, track_color, (track_x, track_y_top, track_w, track_h))
            pygame.draw.rect(surface, track_color, (track_x, track_y_bottom, track_w, track_h))
        else:
            # 对角方向: 斜向的履带
            track_w, track_h = 7, 9
            offset_x = 3 if direction in [Direction.NORTHEAST, Direction.EAST] else -3
            offset_y = 3 if direction in [Direction.SOUTHEAST, Direction.SOUTH] else -3
            pygame.draw.rect(surface, track_color,
                           (cx - 12 + offset_x, cy + 6 + offset_y, track_w, track_h))
            pygame.draw.rect(surface, track_color,
                           (cx + 5 + offset_x, cy + 6 + offset_y, track_w, track_h))

        # --- 前轮 (两个小圆) ---
        wheel_radius = 2
        wheel_positions = {
            Direction.NORTH: [(cx - 5, cy + 14), (cx + 3, cy + 14)],
            Direction.NORTHEAST: [(cx - 2, cy + 12), (cx + 6, cy + 14)],
            Direction.EAST: [(cx + 6, cy + 4), (cx + 6, cy + 12)],
            Direction.SOUTHEAST: [(cx + 4, cy - 4), (cx + 8, cy + 4)],
            Direction.SOUTH: [(cx - 5, cy - 10), (cx + 3, cy - 10)],
            Direction.SOUTHWEST: [(cx - 8, cy - 4), (cx - 4, cy + 4)],
            Direction.WEST: [(cx - 10, cy + 4), (cx - 10, cy + 12)],
            Direction.NORTHWEST: [(cx - 8, cy - 4), (cx - 2, cy + 4)],
        }

        for wx, wy in wheel_positions.get(direction, [(cx - 5, cy + 14), (cx + 3, cy + 14)]):
            pygame.draw.circle(surface, wheel_color, (int(wx), int(wy)), wheel_radius)
            pygame.draw.circle(surface, dark_color, (int(wx), int(wy)), wheel_radius, 1)

        # --- 车身主体 (矩形) ---
        body_width, body_height = 24, 16
        body_x = cx - body_width // 2
        body_y = cy - body_height // 2

        # 根据方向调整车身形状
        if direction in [Direction.NORTH, Direction.SOUTH]:
            pygame.draw.rect(surface, body_color, (body_x, body_y, body_width, body_height),
                           border_radius=2)
            # 开顶货舱轮廓 (内部深色线)
            cargo_inner_x = body_x + 3
            cargo_inner_y = body_y + 3
            cargo_inner_w = body_width - 6
            cargo_inner_h = body_height - 6
            pygame.draw.rect(surface, dark_color,
                           (cargo_inner_x, cargo_inner_y, cargo_inner_w, cargo_inner_h), 1)
        else:
            # 侧面视图: 更窄的车身
            side_body_w = 18 if direction in [Direction.EAST, Direction.WEST] else 20
            side_body_h = 14
            side_body_x = cx - side_body_w // 2
            side_body_y = cy - side_body_h // 2
            pygame.draw.rect(surface, body_color,
                           (side_body_x, side_body_y, side_body_w, side_body_h),
                           border_radius=2)

        # 车身边框
        pygame.draw.rect(surface, dark_color, (body_x, body_y, body_width, body_height), 1)

        # --- 前机枪位置 (小圆点) ---
        mg_positions = {
            Direction.NORTH: (cx, body_y + 2),
            Direction.NORTHEAST: (cx + 8, body_y + 4),
            Direction.EAST: (body_x + body_width - 2, cy),
            Direction.SOUTHEAST: (cx + 8, body_y + body_height - 4),
            Direction.SOUTH: (cx, body_y + body_height - 2),
            Direction.SOUTHWEST: (cx - 8, body_y + body_height - 4),
            Direction.WEST: (body_x + 2, cy),
            Direction.NORTHWEST: (cx - 8, body_y + 4),
        }
        mg_pos = mg_positions.get(direction, (cx, body_y + 2))
        pygame.draw.circle(surface, (40, 40, 40), mg_pos, 1)

        # --- 阵营标识 ---
        if faction == Faction.ALLIES:
            PixelArtist3D._draw_star(surface, cx, cy, 2, (200, 200, 200))
        else:
            PixelArtist3D._draw_iron_cross(surface, cx, cy, (180, 180, 180))

        # --- 移动尘土效果 ---
        if state == "move":
            dust_offset = frame % 2
            for i in range(2):
                dust_x = cx - 8 + i * 12 + dust_offset
                dust_y = cy + 18
                if 0 <= dust_x < 32 and 0 <= dust_y < 40:
                    pygame.draw.circle(surface, (139, 119, 66), (int(dust_x), int(dust_y)), 1)

        return surface

    @staticmethod
    def create_jeep_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """
        创建吉普/侦察车精灵 (24×18 px, 正交俯视)

        CC2视觉规格:
        - 尺寸: ~24×18像素 (最小车辆)
        - 形状: 紧凑矩形 + V型挡风玻璃线
        - 轮子: 2-4个小圆 (取决于角度)
        - 细节: 后备胎 (可选，2px圆)

        Args:
            direction: 8方向之一
            faction: ALLIES 或 AXIS
            state: idle/move
            frame: 动画帧号

        Returns:
            24×18 pygame.Surface (带alpha通道)
        """
        import pygame

        surface = pygame.Surface((24, 18), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        if faction == Faction.ALLIES:
            body_color = (92, 107, 53)      # Olive drab #5C6B35
            dark_color = (72, 84, 41)       # Darker shade
        else:
            body_color = (96, 104, 88)      # Field gray #606858
            dark_color = (76, 82, 70)       # Darker

        cx, cy = 12, 9

        # --- 车身主体 (紧凑矩形) ---
        body_w, body_h = 18, 12
        body_x = cx - body_w // 2
        body_y = cy - body_h // 2

        pygame.draw.rect(surface, body_color, (body_x, body_y, body_w, body_h),
                         border_radius=1)
        pygame.draw.rect(surface, dark_color, (body_x, body_y, body_w, body_h), 1)

        # --- V型挡风玻璃线 ---
        windshield_points = [
            (body_x + 4, body_y + 2),
            (cx, body_y + 5),
            (body_x + body_w - 4, body_y + 2),
        ]
        pygame.draw.lines(surface, dark_color, False, windshield_points, 1)

        # --- 轮子 (根据方向显示2-4个) ---
        wheel_radius = 2
        wheel_color = (30, 30, 30)

        if direction in [Direction.NORTH, Direction.SOUTH]:
            # 前/后视图: 显示4个轮子
            wheels = [
                (body_x + 3, body_y + body_h),
                (body_x + body_w - 3, body_y + body_h),
                (body_x + 3, body_y),
                (body_x + body_w - 3, body_y),
            ]
        elif direction in [Direction.EAST, Direction.WEST]:
            # 侧视图: 显示2个轮子
            offset = 4 if direction == Direction.EAST else -4
            wheels = [
                (cx - offset, body_y + 2),
                (cx - offset, body_y + body_h - 2),
            ]
        else:
            # 对角视图: 显示3个轮子
            wheels = [
                (body_x + 2, body_y + body_h - 1),
                (cx, body_y + body_h),
                (body_x + body_w - 2, body_y + body_h - 1),
            ]

        for wx, wy in wheels:
            if 0 <= wx < 24 and 0 <= wy < 18:
                pygame.draw.circle(surface, wheel_color, (int(wx), int(wy)), wheel_radius)

        # --- 可选后备轮胎 (后部小圆) ---
        spare_wheel_pos = {
            Direction.NORTH: (cx, body_y + body_h + 1),
            Direction.SOUTH: (cx, body_y - 1),
            Direction.EAST: (body_x - 1, cy),
            Direction.WEST: (body_x + body_w + 1, cy),
        }
        if direction in spare_wheel_pos:
            swx, swy = spare_wheel_pos[direction]
            if 0 <= swx < 24 and 0 <= swy < 18:
                pygame.draw.circle(surface, (40, 40, 40), (int(swx), int(swy)), 1)

        return surface

    @staticmethod
    def create_at_gun_sprite(
        direction: Direction,
        faction: Faction,
        state: str = "idle",
        frame: int = 0,
    ):
        """
        创建反坦克炮精灵 (28×20 px, 已部署/不可移动)

        CC2视觉规格:
        - 尺寸: ~28×20像素
        - 形状: 枪管 (长细矩形10-14px长, 2px宽) + 盾牌 (弧形) + 底座
        - 枪管指向朝向方向
        - 盾牌: 弧形在枪管后方
        - 底座: 小矩形 + 两条后伸的架腿

        Args:
            direction: 枪管朝向 (主要4或8方向)
            faction: ALLIES 或 AXIS
            state: idle/shoot
            frame: 动画帧号

        Returns:
            28×20 pygame.Surface (带alpha通道)
        """
        import pygame

        surface = pygame.Surface((28, 20), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        # 军事暗灰绿色调色板
        body_color = (60, 65, 55)
        dark_color = (45, 50, 42)
        barrel_color = (40, 40, 40)
        shield_color = (55, 58, 52)

        cx, cy = 14, 12

        # 计算枪管角度和长度
        angles_deg = {
            Direction.NORTH: 270,
            Direction.NORTHEAST: 315,
            Direction.EAST: 0,
            Direction.SOUTHEAST: 45,
            Direction.SOUTH: 90,
            Direction.SOUTHWEST: 135,
            Direction.WEST: 180,
            Direction.NORTHWEST: 225,
        }
        angle_rad = math.radians(angles_deg.get(direction, 0))

        # *** 增强炮管长度 (12→16px, 更接近CC2原版!) ***
        barrel_length = 16
        barrel_width = 2

        # --- 底座 (中心小矩形) ---
        base_w, base_h = 6, 4
        base_x = cx - base_w // 2
        base_y = cy
        pygame.draw.rect(surface, body_color, (base_x, base_y, base_w, base_h))
        pygame.draw.rect(surface, dark_color, (base_x, base_y, base_w, base_h), 1)

        # --- 架腿 (向后延伸的两条线) ---
        leg_length = 6
        leg_spread = 4
        leg_angle_base = angle_rad + math.pi  # 向后

        # 左腿
        left_leg_angle = leg_angle_base - 0.3
        left_leg_end_x = cx + math.cos(left_leg_angle) * leg_length
        left_leg_end_y = cy + math.sin(left_leg_angle) * leg_length
        pygame.draw.line(surface, dark_color, (cx - leg_spread // 2, cy + base_h // 2),
                        (int(left_leg_end_x), int(left_leg_end_y)), 2)

        # 右腿
        right_leg_angle = leg_angle_base + 0.3
        right_leg_end_x = cx + math.cos(right_leg_angle) * leg_length
        right_leg_end_y = cy + math.sin(right_leg_angle) * leg_length
        pygame.draw.line(surface, dark_color, (cx + leg_spread // 2, cy + base_h // 2),
                        (int(right_leg_end_x), int(right_leg_end_y)), 2)

        # --- 枪盾 (弧形) ---
        shield_radius = 5
        shield_center_x = cx - math.cos(angle_rad) * 3
        shield_center_y = cy - math.sin(angle_rad) * 3 - 2

        # 绘制弧形盾牌
        start_angle = angle_rad + math.pi * 0.6
        end_angle = angle_rad - math.pi * 0.6
        try:
            pygame.draw.arc(surface, shield_color,
                          (int(shield_center_x - shield_radius),
                           int(shield_center_y - shield_radius),
                           shield_radius * 2, shield_radius * 2),
                          start_angle, end_angle, 2)
        except Exception:
            pass

        # --- 枪管 (长细矩形) ---
        barrel_start_x = cx
        barrel_start_y = cy - 2
        barrel_end_x = barrel_start_x + math.cos(angle_rad) * barrel_length
        barrel_end_y = barrel_start_y + math.sin(angle_rad) * barrel_length

        pygame.draw.line(surface, barrel_color,
                        (int(barrel_start_x), int(barrel_start_y)),
                        (int(barrel_end_x), int(barrel_end_y)),
                        barrel_width)

        # 枪口 (末端圆点)
        pygame.draw.circle(surface, (30, 30, 30),
                          (int(barrel_end_x), int(barrel_end_y)), 2)

        # --- 射击闪光 ---
        if state == "shoot" and frame == 1:
            flash_size = 4
            pygame.draw.ellipse(surface, (255, 255, 100),
                              (int(barrel_end_x) - flash_size // 2,
                               int(barrel_end_y) - flash_size // 2,
                               flash_size, flash_size))

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

        palette = PixelArtist3D.CC2_PALETTE["allies" if faction == Faction.ALLIES else "axis"]
        uniform_color = palette['uniform']
        helmet_color = palette['helmet']
        skin_color = palette['skin']
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
    def create_tree_sprite(variant: int = 0):
        """
        创建树木精灵 (14×14 px, 45°伪3D)

        Args:
            variant: 变体编号 (0-2)

        Returns:
            14×14 pygame.Surface (带alpha通道)
        """
        import pygame

        surface = pygame.Surface((14, 14), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        crown_colors = [
            (34, 72, 30),
            (40, 82, 35),
            (30, 68, 28),
        ]
        shadow_color = (20, 48, 18)
        trunk_color = (101, 67, 33)

        crown_color = crown_colors[variant % 3]

        cx, cy = 7, 8

        trunk_w, trunk_h = 2, 4
        pygame.draw.rect(
            surface,
            trunk_color,
            (cx - trunk_w // 2, cy - 1, trunk_w, trunk_h),
        )

        shadow_cy = cy + 2
        pygame.draw.ellipse(
            surface, shadow_color, (cx - 5, shadow_cy - 2, 10, 4)
        )

        layers = 3
        for layer in range(layers):
            radius = 5 - layer
            layer_cy = cy - 2 - layer * 2
            layer_color = (
                min(255, crown_color[0] + layer * 8),
                min(255, crown_color[1] + layer * 10),
                min(255, crown_color[2] + layer * 5),
            )
            pygame.draw.circle(surface, layer_color, (cx, layer_cy), radius)

        highlight_r = 2
        pygame.draw.circle(
            surface,
            (min(255, crown_color[0] + 20), min(255, crown_color[1] + 25), min(255, crown_color[2] + 15)),
            (cx - 1, cy - 4),
            highlight_r,
        )

        return surface

    @staticmethod
    def create_building_sprite(
        building_type: str = "house",
        roof_color: tuple | None = None,
        wall_color: tuple | None = None,
    ):
        """
        创建建筑精灵 (40×40 px, 45°伪3D等距投影)

        Args:
            building_type: house/church/barn
            roof_color: 自定义屋顶颜色
            wall_color: 自定义墙壁颜色

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
            wall_light = (180, 170, 155)
            wall_dark = (120, 115, 105)
        else:
            wall_light = wall_color
            wall_dark = tuple(max(0, v - 30) for v in wall_color)

        base_x, base_y = 20, 28

        wall_w, wall_h = 16, 12
        left_wall_points = [
            (base_x - wall_w // 2, base_y),
            (base_x - wall_w // 2, base_y - wall_h),
            (base_x - wall_w // 2 - 6, base_y - wall_h - 6),
            (base_x - wall_w // 2 - 6, base_y - 6),
        ]
        pygame.draw.polygon(surface, wall_dark, left_wall_points)
        pygame.draw.polygon(surface, (80, 75, 65), left_wall_points, 1)

        right_wall_points = [
            (base_x + wall_w // 2, base_y),
            (base_x + wall_w // 2, base_y - wall_h),
            (base_x + wall_w // 2 + 6, base_y - wall_h - 6),
            (base_x + wall_w // 2 + 6, base_y - 6),
        ]
        pygame.draw.polygon(surface, wall_light, right_wall_points)
        pygame.draw.polygon(surface, (100, 95, 85), right_wall_points, 1)

        roof_points = [
            (base_x, base_y - wall_h - 10),
            (base_x - wall_w // 2 - 4, base_y - wall_h - 4),
            (base_x + wall_w // 2 + 4, base_y - wall_h - 4),
        ]
        pygame.draw.polygon(surface, roof_color, roof_points)
        darker_roof = tuple(max(0, v - 25) for v in roof_color)
        pygame.draw.polygon(surface, darker_roof, roof_points, 1)

        if building_type == "church":
            steeple_points = [
                (base_x, base_y - wall_h - 18),
                (base_x - 2, base_y - wall_h - 10),
                (base_x + 2, base_y - wall_h - 10),
            ]
            pygame.draw.polygon(surface, (80, 80, 80), steeple_points)
            pygame.draw.circle(surface, (220, 220, 200), (int(base_x), int(base_y - wall_h - 19)), 1)

        window_left = (base_x - wall_w // 2 - 3, base_y - wall_h // 2 - 2)
        pygame.draw.rect(surface, (180, 210, 220), (*window_left, 3, 4))
        window_right = (base_x + wall_w // 2, base_y - wall_h // 2 - 2)
        pygame.draw.rect(surface, (180, 210, 220), (*window_right, 3, 4))

        door_rect = pygame.Rect(base_x - 2, base_y - 5, 4, 5)
        pygame.draw.rect(surface, (60, 45, 35), door_rect)

        shadow_points = [
            (base_x - wall_w // 2 - 6, base_y - 6),
            (base_x + wall_w // 2 + 6, base_y - 6),
            (base_x + wall_w // 2 + 8, base_y - 4),
            (base_x - wall_w // 2 - 4, base_y - 4),
        ]
        shadow_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
        shadow_surf.fill((50, 48, 45, 100))
        pygame.draw.polygon(shadow_surf, (50, 48, 45, 100), shadow_points)
        surface.blit(shadow_surf, (0, 0))

        return surface

    @staticmethod
    def create_terrain_tile_isometric(
        terrain_type: str = "grass",
        size: int = 64,
        variant: int = 0,
    ):
        """
       创建等距投影地形瓦片 (菱形)

        Args:
            terrain_type: grass/dirt/road/water
            size: 瓦片大小 (默认64)
            variant: 变体编号

        Returns:
            size×(size//2) 的pygame.Surface (菱形)
        """
        import pygame

        height = size // 2
        surface = pygame.Surface((size, height), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        colors = {
            'grass': ((56, 104, 36), (76, 132, 52), (40, 80, 28)),
            'dirt': ((140, 110, 60), (160, 130, 75), (120, 90, 45)),
            'road': ((149, 126, 94), (165, 142, 110), (130, 108, 78)),
            'water': ((64, 120, 172), (84, 140, 192), (44, 100, 152)),
        }

        base_color, light_color, dark_color = colors.get(terrain_type, colors['grass'])

        center_x = size // 2
        center_y = height // 2

        diamond_points = [
            (center_x, 0),
            (size, center_y),
            (center_x, height),
            (0, center_y),
        ]
        pygame.draw.polygon(surface, base_color, diamond_points)

        import random
        rng = random.Random(variant * 42 + 123)

        for _ in range(size // 4):
            px = rng.randint(2, size - 2)
            py = rng.randint(2, height - 2)

            if PixelArtist3D._point_in_diamond(px, py, center_x, center_y, size // 2 - 2, height // 2 - 2):
                color_choice = rng.choice([light_color, dark_color, base_color])
                pygame.draw.circle(surface, color_choice, (px, py), rng.randint(1, 2))

        if terrain_type == "grass":
            for _ in range(size // 8):
                gx = rng.randint(center_x - 5, center_x + 5)
                gy = rng.randint(center_y - 3, center_y + 3)
                if PixelArtist3D._point_in_diamond(gx, gy, center_x, center_y, size // 2 - 4, height // 2 - 4):
                    grass_height = rng.randint(2, 4)
                    pygame.draw.line(
                        surface,
                        dark_color,
                        (gx, gy),
                        (gx + rng.randint(-1, 1), gy - grass_height),
                        1,
                    )

        pygame.draw.polygon(surface, tuple(max(0, c - 20) for c in base_color), diamond_points, 1)

        return surface

    @staticmethod
    def _point_in_diamond(px, py, cx, cy, rx, ry) -> bool:
        """检查点是否在菱形内"""
        return abs(px - cx) / rx + abs(py - cy) / ry <= 1.0

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
        infantry_type: rifleman/mg/at/officer/sniper

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
