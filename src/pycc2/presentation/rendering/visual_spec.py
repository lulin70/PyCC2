"""
Visual Specification Constants

Centralized visual design constants for consistent rendering across all components.
Defines colors, sizes, and other visual properties used by the rendering system.
"""

from pycc2.domain.value_objects.terrain_type import TerrainType


class VisualSpec:
    """Container for all visual specification constants."""

    ALLIED_BLUE: tuple[int, int, int] = (65, 105, 225)
    AXIS_GREEN: tuple[int, int, int] = (34, 139, 34)
    NEUTRAL_GRAY: tuple[int, int, int] = (128, 128, 128)
    SELECTION_YELLOW: tuple[int, int, int] = (255, 215, 0)
    DANGER_RED: tuple[int, int, int] = (220, 20, 60)
    FOG_GRAY: tuple[int, int, int] = (30, 30, 35)
    PANEL_BG: tuple[int, int, int] = (40, 44, 52, 220)
    HUD_TEXT_WHITE: tuple[int, int, int] = (240, 240, 240)
    TILE_BORDER_DARK: tuple[int, int, int] = (60, 64, 72)

    def __init__(self):
        self.allied_unit_color = self.ALLIED_BLUE
        self.allied_outline_color = (100, 149, 237)
        self.axis_unit_color = self.AXIS_GREEN
        self.axis_outline_color = (46, 139, 87)
        self.neutral_color = self.NEUTRAL_GRAY
        self.selection_color = self.SELECTION_YELLOW
        self.danger_color = self.DANGER_RED
        self.fog_color = self.FOG_GRAY
        self.panel_background_color = self.PANEL_BG
        self.hud_text_color = self.HUD_TEXT_WHITE
        self.tile_border_color = self.TILE_BORDER_DARK
        self.hud_background_color = (40, 44, 52, 200)
        self.hud_border_color = (80, 84, 92)
        self.panel_border_color = (80, 84, 92)
        self.minimap_background_color = (25, 28, 33)
        self.minimap_border_color = (80, 84, 92)
        self.command_bar_bg_color = (35, 38, 45)
        self.command_bar_border_color = (70, 74, 82)
        self.button_normal_color = (55, 58, 67)
        self.button_hover_color = (75, 78, 87)
        self.button_disabled_color = (40, 43, 50)
        self.button_border_color = (90, 94, 102)
        self.button_text_color = (220, 220, 220)
        self.button_disabled_text_color = (120, 120, 120)
        self.projectile_hit_color = (255, 80, 80)
        self.projectile_miss_color = (255, 200, 80)
        self.health_bar_green = (80, 200, 80)
        self.health_bar_yellow = (230, 200, 60)
        self.health_bar_red = (230, 80, 80)
        self.morale_bar_blue = (80, 150, 255)
        self.suppression_overlay = (128, 0, 0, 100)

        self.terrain_colors: dict[TerrainType, tuple[int, int, int]] = {
            TerrainType.OPEN: (200, 200, 180),
            TerrainType.ROAD: (128, 128, 128),
            TerrainType.GRASS: (76, 153, 0),
            TerrainType.WOODS: (34, 100, 34),
            TerrainType.BUILDING_ENTERABLE: (160, 140, 120),
            TerrainType.BUILDING_SOLID: (100, 80, 60),
            TerrainType.WATER: (65, 105, 225),
            TerrainType.HEDGE: (80, 120, 40),
            TerrainType.WALL: (105, 105, 105),
            TerrainType.ROUGH: (154, 140, 125),
            TerrainType.SHALLOW: (100, 149, 237),
            TerrainType.BRIDGE: (139, 119, 101),
        }

    def get_terrain_color(self, terrain_type: TerrainType) -> tuple[int, int, int]:
        """Get color for terrain type."""
        return self.terrain_colors.get(terrain_type, self.NEUTRAL_GRAY)

    def get_health_color(self, percentage: float) -> tuple[int, int, int]:
        """Get health bar color based on percentage."""
        if percentage > 60:
            return self.health_bar_green
        elif percentage > 30:
            return self.health_bar_yellow
        else:
            return self.health_bar_red
