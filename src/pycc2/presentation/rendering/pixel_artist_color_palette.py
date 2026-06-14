"""
CC2风格颜色调色板定义模块

包含所有像素艺术生成器使用的颜色常量和调色板：
- CC2_PALETTE: 步兵制服/装备颜色（盟军/轴心国）
- TANK_PALETTES: 坦克历史准确性调色板（Sherman/Panther/Tiger）
- TANK_SIZES: 坦克尺寸差异化配置

基于2026-05-22 CC2原版截图分析和历史资料：
- 盟军: WWII US Olive Drab (Steve Zaloga + Tamiya XF62)
- 轴心国: German Field Gray (Bundesarchiv + Osprey Publishing)
- 坦克: Kenney CC0资源 + 二战照片 + 技术手册
"""

from __future__ import annotations

from pycc2.presentation.rendering.pixel_artist_enums import TankType

# ============================================================================
# 步兵制服调色板 (CC2_PALETTE)
# ============================================================================
CC2_PALETTE = {
    "allies": {
        # WWII US Olive Drab (历史修正版): 偏棕橄榄褐, 非亮绿色
        # 参考: Steve Zaloga(装甲史学家) + Tamiya XF62模型漆
        # CC2截图验证: 盟军制服为暗沉的土褐色调
        "uniform": (75, 83, 32),
        "uniform_dark": (56, 62, 24),
        "uniform_light": (98, 108, 42),
        "helmet": (72, 76, 72),  # M1钢盔，暗橄榄褐钢色（历史修正）
        "helmet_dark": (56, 58, 56),
        "helmet_highlight": (100, 104, 100),
        "weapon": (60, 60, 60),
        "weapon_metal": (75, 75, 75),
        "weapon_wood": (90, 65, 35),
        "boots": (45, 38, 28),
        "equipment": (50, 55, 40),
        "equipment_dark": (35, 38, 28),
        "canteen": (70, 90, 55),
        "ammo_belt": (55, 50, 38),
        "beret": (60, 80, 45),
    },
    "axis": {
        # German Field Gray (Feldgrau) - 基于1944年照片的实际颜色:
        # 非纯灰色！是带轻微棕色调的绿灰色
        # 参考: Bundesarchiv照片 + Osprey Publishing色彩分析
        "uniform": (85, 93, 80),
        "uniform_dark": (64, 70, 60),
        "uniform_light": (98, 107, 92),
        "helmet": (56, 58, 56),  # 德军Stahlhelm钢盔，暗金属灰绿色（历史修正）
        "helmet_dark": (42, 44, 42),
        "helmet_highlight": (78, 80, 78),
        "weapon": (60, 60, 60),
        "weapon_metal": (75, 75, 75),
        "weapon_wood": (90, 65, 35),
        "boots": (40, 35, 25),
        "equipment": (55, 55, 48),
        "equipment_dark": (38, 38, 32),
        "canteen": (65, 65, 58),
        "ammo_belt": (50, 48, 40),
        "beret": (50, 50, 44),
    },
}


# ============================================================================
# 历史准确性坦克调色板 (TANK_PALETTES)
# 基于Kenney CC0资源 + 二战照片 + 技术手册
# ============================================================================
TANK_PALETTES = {
    TankType.SHERMAN_M4: {
        # M4谢尔曼中型坦克 - 美军橄榄绿+泥污风化效果
        # 参考: US Army Ordnance Corps FM 9-2075 + Tamiya模型漆标准
        "body_base": (112, 108, 76),  # Olive Drab #706C4C (已修正)
        "body_dark": (88, 84, 58),  # 暗部阴影
        "body_light": (132, 128, 94),  # 高光区域
        "turret_base": (118, 114, 82),  # 炮塔稍亮
        "turret_dark": (92, 88, 62),  # 炮塔暗部
        "track_color": (45, 45, 45),  # 履带黑
        "track_rust": (65, 50, 35),  # 履带锈迹
        "gun_barrel": (55, 55, 55),  # 75mm M3炮管
        "mud_dirt": (85, 72, 48),  # 泥土污渍（诺曼底特征）
        "white_star": (220, 220, 220),  # 白色星标
        "cupola": (100, 96, 68),  # 车长指挥塔
        "mg_mount": (50, 50, 50),  # .50 cal机枪座
        "side_skirt": (105, 100, 70),  # 侧裙甲（部分型号）
    },
    TankType.PANTHER_AUSFG: {
        # 豹式G型坦克 - Dunkelgelb（暗黄）底色+迷彩条纹选项
        # 参考: Germany Tigerfibel手册 + Jentz/Doyle《豹式坦克》技术规格
        "body_base": (85, 88, 30),  # Dunkelgelb RAL 7028 暗黄 #55581E
        "body_dark": (65, 68, 22),  # 暗黄暗部
        "body_light": (100, 104, 40),  # 暗黄高光
        "camo_red_brown": (95, 45, 28),  # Rotbraun RAL 8017 迷彩红棕
        "turret_base": (90, 94, 35),  # 炮塔暗黄
        "turret_dark": (70, 74, 26),  # 炮塔暗部
        "track_color": (35, 35, 35),  # 履带（更暗）
        "gun_barrel": (40, 40, 40),  # 75mm KwK42 L/70长炮管
        "schurzen": (80, 83, 28),  # 炮塔侧裙甲5mm薄板
        "exhaust_pipe": (45, 42, 38),  # 排气管（左侧多出口）
        "mud_dirt": (75, 68, 45),  # 泥污
        "iron_cross": (200, 200, 200),  # 铁十字标识
    },
    TankType.TIGER_I: {
        # 虎式I型重型坦克 - 方正箱体造型，"移动碉堡"
        # 参考: Tiger I Ausf.E Sd.Kfz.181技术手册 + Bovington博物馆实测
        "body_base": (80, 80, 64),  # Dark Yellow #505040 或红底漆 #8B3030
        "body_dark": (60, 60, 48),  # 暗部
        "body_light": (95, 95, 78),  # 高光
        "red_primer": (139, 48, 48),  # 红色底漆（部分车辆可见）
        "turret_base": (85, 85, 68),  # 大矩形炮塔
        "turret_dark": (65, 65, 52),  # 炮塔暗部
        "track_color": (32, 32, 32),  # 宽履带
        "gun_barrel": (45, 45, 45),  # 88mm KwK36 L/56
        "porte_cupola": (90, 90, 74),  # 装甲指挥塔（炮塔中心）
        "boxy_detail": (70, 70, 56),  # 方形细节线
        "iron_cross": (195, 195, 195),  # 铁十字
    },
}


# ============================================================================
# 坦克尺寸差异化系统 - 基于历史重量分级
# 参考: WWII坦克实际尺寸比例 + CC2视觉层次需求
# ============================================================================
TANK_SIZES = {
    TankType.SHERMAN_M4: (36, 36),  # 中型坦克: 标准尺寸
    TankType.PANTHER_AUSFG: (38, 38),  # 中型偏重: 稍大（大倾角装甲+宽车体）
    TankType.TIGER_I: (44, 44),  # 重型坦克: 明显更大（"移动碉堡"）
}
