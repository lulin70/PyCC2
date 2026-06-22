"""CC2原版UI配色方案

基于对CC2原版游戏和PyCC2现有配色的分析，
提取的暖色调军事风格配色方案。

用于替换现有的冷色调（蓝灰）配色，实现更接近CC2原版的视觉风格。
"""

from dataclasses import dataclass

# 类型别名
RGB = tuple[int, int, int]


@dataclass(frozen=True)
class CC2UIColors:
    """CC2原版UI配色方案 - 暖色调军事风格"""

    # === 主要背景色 (暖色调军绿棕) ===
    BG_COLOR: RGB = (58, 64, 48)  # 深橄榄绿 #3A4030 (原: 冷蓝灰)
    BG_DARK: RGB = (38, 42, 34)  # 深橄榄绿阴影 #262A22
    BG_LIGHT: RGB = (78, 84, 68)  # 浅橄榄绿 #4E5444

    # === 边框和分隔线 ===
    BORDER_COLOR: RGB = (90, 96, 80)  # 橄榄边框 #5A6050 (原: 中灰)
    BORDER_HIGHLIGHT: RGB = (120, 126, 100)  # 高亮边框 #787E64
    DIVIDER_COLOR: RGB = (70, 76, 60)  # 分隔线 #464C3C

    # === 面板和按钮 ===
    PANEL_BG_DARK: RGB = (48, 52, 40)  # 深面板 #303428
    PANEL_BG_MID: RGB = (58, 64, 48)  # 中面板 #3A4030
    PANEL_BG_LIGHT: RGB = (68, 74, 58)  # 浅面板 #444A3A

    BUTTON_BG: RGB = (50, 55, 42)  # 按钮背景 #32372A
    BUTTON_HOVER: RGB = (70, 76, 58)  # 按钮悬停 #464C3A
    BUTTON_PRESSED: RGB = (35, 40, 30)  # 按钮按下 #23281E
    BUTTON_DISABLED: RGB = (40, 44, 35)  # 按钮禁用 #282C23

    # === 文字颜色 ===
    TEXT_COLOR: RGB = (220, 220, 210)  # 主文字 - 米白色 #DCDCD2
    TEXT_SECONDARY: RGB = (180, 180, 170)  # 次要文字 #B4B4AA
    TEXT_DIM: RGB = (140, 140, 130)  # 暗淡文字 #8C8C82
    TEXT_DISABLED: RGB = (100, 100, 90)  # 禁用文字 #64645A

    # === 高亮和强调 ===
    HIGHLIGHT_COLOR: RGB = (255, 255, 100)  # 金黄色高亮 #FFFF64
    ACCENT_GOLD: RGB = (200, 180, 80)  # 黄金强调 #C8B450
    ACCENT_BRASS: RGB = (170, 150, 70)  # 黄铜强调 #AA9646

    # === 状态颜色 (保持CC2原版) ===
    STATUS_HEALTHY: RGB = (80, 180, 80)  # 健康 - 绿色
    STATUS_WOUNDED: RGB = (200, 180, 60)  # 受伤 - 黄色
    STATUS_CRITICAL: RGB = (200, 80, 60)  # 危急 - 红色
    STATUS_DEAD: RGB = (100, 100, 100)  # 阵亡 - 灰色

    # === 派系颜色 ===
    ALLIES_BLUE: RGB = (70, 140, 200)  # 盟军蓝
    AXIS_RED: RGB = (200, 70, 70)  # 轴心国红
    NEUTRAL_GRAY: RGB = (120, 120, 120)  # 中立灰

    # === 小地图颜色 ===
    MINIMAP_BG: RGB = (40, 44, 35)  # 小地图背景
    MINIMAP_BORDER: RGB = (90, 96, 80)  # 小地图边框
    MINIMAP_GRID: RGB = (60, 65, 52)  # 小地图网格

    # === 地形基础色 (用于小地图) ===
    TERRAIN_GRASS: RGB = (56, 104, 36)  # 草地
    TERRAIN_DIRT: RGB = (140, 110, 60)  # 土路
    TERRAIN_FOREST: RGB = (34, 72, 30)  # 森林
    TERRAIN_WATER: RGB = (50, 100, 150)  # 水域
    TERRAIN_BUILDING: RGB = (140, 90, 50)  # 建筑


# 全局单例
CC2_UI_COLORS = CC2UIColors()


# === 便捷访问函数 ===


def get_bg_color() -> RGB:
    """获取主背景色"""
    return CC2_UI_COLORS.BG_COLOR


def get_text_color() -> RGB:
    """获取主文字色"""
    return CC2_UI_COLORS.TEXT_COLOR


def get_border_color() -> RGB:
    """获取边框色"""
    return CC2_UI_COLORS.BORDER_COLOR


def get_button_colors() -> dict:
    """获取按钮颜色集"""
    return {
        "normal": CC2_UI_COLORS.BUTTON_BG,
        "hover": CC2_UI_COLORS.BUTTON_HOVER,
        "pressed": CC2_UI_COLORS.BUTTON_PRESSED,
        "disabled": CC2_UI_COLORS.BUTTON_DISABLED,
    }


def get_status_color(health_percent: float) -> RGB:
    """根据生命值百分比获取状态颜色

    Args:
        health_percent: 生命值百分比 (0.0-1.0)

    Returns:
        对应的RGB颜色
    """
    if health_percent <= 0:
        return CC2_UI_COLORS.STATUS_DEAD
    elif health_percent < 0.33:
        return CC2_UI_COLORS.STATUS_CRITICAL
    elif health_percent < 0.66:
        return CC2_UI_COLORS.STATUS_WOUNDED
    else:
        return CC2_UI_COLORS.STATUS_HEALTHY


def get_faction_color(faction: str) -> RGB:
    """获取派系颜色

    Args:
        faction: 'allies', 'axis', 或 'neutral'

    Returns:
        对应的RGB颜色
    """
    faction_lower = faction.lower()
    if faction_lower == "allies":
        return CC2_UI_COLORS.ALLIES_BLUE
    elif faction_lower == "axis":
        return CC2_UI_COLORS.AXIS_RED
    else:
        return CC2_UI_COLORS.NEUTRAL_GRAY


# === 颜色对比表 ===
COLOR_COMPARISON = {
    "旧配色 (冷色调蓝灰)": {
        "BG_COLOR": (20, 22, 26),
        "BORDER_COLOR": (60, 65, 70),
        "TEXT_COLOR": (200, 200, 190),
    },
    "新配色 (暖色调军绿棕)": {
        "BG_COLOR": (58, 64, 48),
        "BORDER_COLOR": (90, 96, 80),
        "TEXT_COLOR": (220, 220, 210),
    },
}


if __name__ == "__main__":
    # 测试和诊断
    print("CC2 UI Color Palette")
    print("=" * 60)
    print(f"Background: {CC2_UI_COLORS.BG_COLOR}")
    print(f"Border: {CC2_UI_COLORS.BORDER_COLOR}")
    print(f"Text: {CC2_UI_COLORS.TEXT_COLOR}")
    print(f"Highlight: {CC2_UI_COLORS.HIGHLIGHT_COLOR}")
    print()

    print("Status Colors:")
    for percent in [1.0, 0.8, 0.5, 0.2, 0.0]:
        color = get_status_color(percent)
        print(f"  {percent * 100:3.0f}% health: {color}")
    print()

    print("Button Colors:")
    for state, color in get_button_colors().items():
        print(f"  {state:10s}: {color}")
    print()

    print("Color Comparison (Old vs New):")
    for category, colors in COLOR_COMPARISON.items():
        print(f"\n{category}:")
        for name, rgb in colors.items():
            print(f"  {name:15s}: {rgb}")
