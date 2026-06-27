"""Enhanced Pixel Artist - 基于CC2历史和二战常识的高质量精灵生成器

根据Close Combat 2历史背景和二战真实装备创建精灵：
- 符合1944-1945年欧洲战场的装备和色调
- 基于真实的单位尺寸比例和视觉特征
- 增强的细节层次和阴影效果

Version: 1.0
Date: 2026-06-16
"""

from __future__ import annotations

import pygame
from pygame import Surface

# CC2历史色彩方案 - 基于1944-1945年欧洲战场
CC2_COLORS = {
    # 盟军色彩 (美军/英军)
    "allies_helmet": (85, 85, 75),  # 橄榄绿钢盔
    "allies_uniform": (110, 105, 85),  # 卡其色军服
    "allies_equipment": (75, 70, 60),  # 深色装备
    "allies_skin": (210, 180, 140),  # 肤色
    # 德军色彩
    "axis_helmet": (95, 95, 85),  # 灰绿色钢盔
    "axis_uniform": (105, 110, 95),  # 野战灰军服
    "axis_equipment": (70, 75, 65),  # 装备色
    # 载具色彩
    "us_vehicle": (95, 90, 70),  # 美军橄榄绿
    "british_vehicle": (85, 80, 65),  # 英军沙漠色
    "german_vehicle": (100, 100, 85),  # 德军灰绿色
    # 坦克特定色彩
    "sherman_base": (95, 90, 70),  # M4谢尔曼
    "panzer_base": (100, 100, 85),  # 四号坦克
    "churchill_base": (85, 80, 65),  # 丘吉尔
    # 通用色彩
    "track_dark": (45, 45, 40),  # 履带
    "metal_highlight": (140, 140, 130),  # 金属高光
    "shadow": (30, 30, 25),  # 阴影
    "ground_dust": (160, 150, 130),  # 地面扬尘
}

# 二战装备尺寸数据 (像素，基于32x32画布)
UNIT_SIZES = {
    "infantry_height": 28,  # 步兵高度
    "infantry_width": 8,  # 步兵宽度
    "tank_length": 26,  # 坦克长度
    "tank_width": 18,  # 坦克宽度
    "halftrack_length": 22,  # 半履带车长度
    "jeep_length": 14,  # 吉普车长度
}


class EnhancedPixelArtist:
    """基于CC2历史和二战常识的增强型像素艺术家"""

    @staticmethod
    def create_historical_infantry(
        faction: str, direction: str, state: str = "idle", frame: int = 0, size: int = 32
    ) -> Surface:
        """创建符合历史的步兵精灵

        基于真实二战步兵装备：
        - 美军: M1钢盔, M1941野战服, M1加兰德步枪
        - 德军: M35钢盔, M36野战服, Kar98k步枪
        """
        surface = Surface((size, size), pygame.SRCALPHA)

        # 根据阵营选择颜色
        if faction in ("allies", "american", "british"):
            helmet_color = CC2_COLORS["allies_helmet"]
            uniform_color = CC2_COLORS["allies_uniform"]
            equipment_color = CC2_COLORS["allies_equipment"]
        else:
            helmet_color = CC2_COLORS["axis_helmet"]
            uniform_color = CC2_COLORS["axis_uniform"]
            equipment_color = CC2_COLORS["axis_equipment"]

        # 计算方向角度
        direction_angles = {
            "N": 0,
            "NE": 45,
            "E": 90,
            "SE": 135,
            "S": 180,
            "SW": 225,
            "W": 270,
            "NW": 315,
        }
        angle = direction_angles.get(direction, 0)

        center_x, center_y = size // 2, size // 2

        # 根据状态绘制
        leg_offset = 2 if state == "walk" and frame % 2 == 1 else 0

        # 绘制阴影
        shadow_color = CC2_COLORS["shadow"]
        pygame.draw.ellipse(surface, shadow_color, (center_x - 6, center_y + 10, 12, 4))

        # 绘制身体（考虑方向）
        if angle < 90 or angle > 270:  # 朝北方向
            # 腿部
            pygame.draw.rect(
                surface, uniform_color, (center_x - 3, center_y + 2, 2, 8 + leg_offset)
            )
            pygame.draw.rect(
                surface, uniform_color, (center_x + 1, center_y + 2, 2, 8 - leg_offset)
            )
            # 身体
            pygame.draw.rect(surface, uniform_color, (center_x - 3, center_y - 4, 6, 8))
            # 装备（背包）
            pygame.draw.rect(surface, equipment_color, (center_x - 2, center_y - 3, 4, 5))
            # 钢盔
            pygame.draw.circle(surface, helmet_color, (center_x, center_y - 8), 4)
            # 武器（步枪）
            pygame.draw.line(
                surface,
                equipment_color,
                (center_x + 3, center_y - 2),
                (center_x + 5, center_y + 6),
                2,
            )
        else:  # 朝南方向
            # 腿部
            pygame.draw.rect(
                surface, uniform_color, (center_x - 3, center_y + 2, 2, 8 + leg_offset)
            )
            pygame.draw.rect(
                surface, uniform_color, (center_x + 1, center_y + 2, 2, 8 - leg_offset)
            )
            # 钢盔
            pygame.draw.circle(surface, helmet_color, (center_x, center_y - 8), 4)
            # 身体
            pygame.draw.rect(surface, uniform_color, (center_x - 3, center_y - 4, 6, 8))
            # 武器（步枪）
            pygame.draw.line(
                surface, equipment_color, (center_x - 5, center_y), (center_x + 5, center_y), 2
            )

        # 添加高光
        pygame.draw.circle(surface, CC2_COLORS["metal_highlight"], (center_x - 1, center_y - 9), 1)

        return surface

    @staticmethod
    def create_historical_tank(
        faction: str,
        tank_type: str,
        direction: str,
        turret_direction: str | None = None,
        size: int = 32,
    ) -> Surface:
        """创建符合历史的坦克精灵

        真实坦克型号：
        - 美军: M4 Sherman (中型坦克)
        - 英军: Churchill Mk VII (重型步兵坦克)
        - 德军: Panzer IV (中型坦克), Tiger I (重型坦克)
        """
        surface = Surface((size, size), pygame.SRCALPHA)

        # 根据阵营和型号选择颜色
        if faction in ("american", "allies"):
            base_color = CC2_COLORS["sherman_base"]
            tank_name = "Sherman"
        elif faction == "british":
            base_color = CC2_COLORS["churchill_base"]
            tank_name = "Churchill"
        else:
            base_color = CC2_COLORS["panzer_base"]
            tank_name = "Panzer IV"

        center_x, center_y = size // 2, size // 2

        # 计算方向
        direction_angles = {
            "N": 0,
            "NE": 45,
            "E": 90,
            "SE": 135,
            "S": 180,
            "SW": 225,
            "W": 270,
            "NW": 315,
        }
        angle = direction_angles.get(direction, 0)

        # 绘制阴影
        shadow_color = CC2_COLORS["shadow"]
        pygame.draw.ellipse(surface, shadow_color, (center_x - 10, center_y + 8, 20, 6))

        # 根据方向绘制坦克
        if 45 <= angle <= 135:  # 侧面视角 (东)
            # 履带
            track_color = CC2_COLORS["track_dark"]
            pygame.draw.rect(surface, track_color, (center_x - 11, center_y + 3, 22, 4))
            pygame.draw.rect(surface, track_color, (center_x - 11, center_y - 5, 22, 4))

            # 车体
            pygame.draw.rect(surface, base_color, (center_x - 10, center_y - 4, 20, 7))

            # 炮塔
            turret_x = center_x - 2
            pygame.draw.rect(surface, base_color, (turret_x, center_y - 8, 8, 6))

            # 主炮
            gun_length = 15 if tank_name == "Sherman" else 18
            pygame.draw.rect(surface, (60, 60, 55), (turret_x + 7, center_y - 6, gun_length, 2))

            # 高光
            pygame.draw.line(
                surface,
                CC2_COLORS["metal_highlight"],
                (center_x - 9, center_y - 3),
                (center_x + 9, center_y - 3),
                1,
            )

        elif 225 <= angle <= 315:  # 侧面视角 (西)
            # 履带
            track_color = CC2_COLORS["track_dark"]
            pygame.draw.rect(surface, track_color, (center_x - 11, center_y + 3, 22, 4))
            pygame.draw.rect(surface, track_color, (center_x - 11, center_y - 5, 22, 4))

            # 车体
            pygame.draw.rect(surface, base_color, (center_x - 10, center_y - 4, 20, 7))

            # 炮塔
            turret_x = center_x - 2
            pygame.draw.rect(surface, base_color, (turret_x, center_y - 8, 8, 6))

            # 主炮（朝左）
            gun_length = 15 if tank_name == "Sherman" else 18
            pygame.draw.rect(
                surface, (60, 60, 55), (turret_x - gun_length, center_y - 6, gun_length, 2)
            )

            # 高光
            pygame.draw.line(
                surface,
                CC2_COLORS["metal_highlight"],
                (center_x - 9, center_y - 3),
                (center_x + 9, center_y - 3),
                1,
            )

        else:  # 正面/背面视角
            # 履带
            track_color = CC2_COLORS["track_dark"]
            pygame.draw.rect(surface, track_color, (center_x - 10, center_y, 4, 10))
            pygame.draw.rect(surface, track_color, (center_x + 6, center_y, 4, 10))

            # 车体
            pygame.draw.rect(surface, base_color, (center_x - 9, center_y - 2, 18, 12))

            # 炮塔
            pygame.draw.rect(surface, base_color, (center_x - 5, center_y - 6, 10, 8))

            # 主炮
            if angle < 90 or angle > 270:  # 朝北
                pygame.draw.rect(surface, (60, 60, 55), (center_x - 1, center_y - 14, 2, 8))
            else:  # 朝南
                pygame.draw.rect(surface, (60, 60, 55), (center_x - 1, center_y + 2, 2, 8))

            # 高光
            pygame.draw.rect(
                surface, CC2_COLORS["metal_highlight"], (center_x - 4, center_y - 5, 1, 6)
            )

        return surface

    @staticmethod
    def create_historical_halftrack(faction: str, direction: str, size: int = 32) -> Surface:
        """创建符合历史的半履带车精灵

        真实型号：
        - 美军: M3 Half-track
        - 德军: Sd.Kfz. 251
        """
        surface = Surface((size, size), pygame.SRCALPHA)

        # 选择颜色
        if faction in ("american", "allies"):
            base_color = CC2_COLORS["us_vehicle"]
        else:
            base_color = CC2_COLORS["german_vehicle"]

        center_x, center_y = size // 2, size // 2

        # 方向角度
        direction_angles = {
            "N": 0,
            "NE": 45,
            "E": 90,
            "SE": 135,
            "S": 180,
            "SW": 225,
            "W": 270,
            "NW": 315,
        }
        angle = direction_angles.get(direction, 0)

        # 阴影
        pygame.draw.ellipse(surface, CC2_COLORS["shadow"], (center_x - 8, center_y + 7, 16, 5))

        # 根据方向绘制
        if 45 <= angle <= 135 or 225 <= angle <= 315:  # 侧面
            # 履带
            pygame.draw.rect(surface, CC2_COLORS["track_dark"], (center_x - 8, center_y + 2, 16, 4))

            # 车体
            pygame.draw.rect(surface, base_color, (center_x - 7, center_y - 4, 14, 8))

            # 驾驶舱
            pygame.draw.rect(surface, base_color, (center_x - 6, center_y - 7, 6, 4))

            # 车轮（前部）
            pygame.draw.circle(surface, (40, 40, 35), (center_x - 5, center_y + 4), 2)
            pygame.draw.circle(surface, (40, 40, 35), (center_x + 5, center_y + 4), 2)

            # 高光
            pygame.draw.line(
                surface,
                CC2_COLORS["metal_highlight"],
                (center_x - 6, center_y - 3),
                (center_x + 6, center_y - 3),
                1,
            )
        else:  # 正面/背面
            # 履带
            pygame.draw.rect(surface, CC2_COLORS["track_dark"], (center_x - 8, center_y + 1, 3, 8))
            pygame.draw.rect(surface, CC2_COLORS["track_dark"], (center_x + 5, center_y + 1, 3, 8))

            # 车体
            pygame.draw.rect(surface, base_color, (center_x - 7, center_y - 2, 14, 10))

            # 驾驶舱
            pygame.draw.rect(surface, base_color, (center_x - 4, center_y - 6, 8, 5))

            # 挡风玻璃
            pygame.draw.rect(surface, (80, 100, 120), (center_x - 2, center_y - 5, 4, 2))

        return surface


def create_historical_sprite(
    unit_type: str,
    faction: str,
    direction: str,
    state: str = "idle",
    frame: int = 0,
    size: int = 32,
) -> Surface:
    """统一接口：根据单位类型创建历史精灵"""
    unit_type_lower = unit_type.lower()

    if "infantry" in unit_type_lower or "squad" in unit_type_lower:
        return EnhancedPixelArtist.create_historical_infantry(
            faction, direction, state, frame, size
        )
    elif "tank" in unit_type_lower or "panzer" in unit_type_lower:
        return EnhancedPixelArtist.create_historical_tank(faction, "medium", direction, None, size)
    elif "halftrack" in unit_type_lower:
        return EnhancedPixelArtist.create_historical_halftrack(faction, direction, size)
    else:
        # 默认返回步兵
        return EnhancedPixelArtist.create_historical_infantry(
            faction, direction, state, frame, size
        )
