"""Morandi Color Palette (V-10 Wave E2)

Morandi-style color palette for PyCC2 — low-saturation, gray-toned colors
inspired by Giorgio Morandi's still-life paintings. Provides an alternative
"soft" skin to the default CC2-faithful palette, addressing user preference
for comfortable color schemes over high-saturation visuals.

Design principles (Morandi palette):
  - Saturation ≤ 30% (muted, no vivid colors)
  - Lightness ≈ 50-70% (soft, non-fatiguing)
  - Warm gray undertone (harmonious across palette)
  - Distinct hue families preserved (blue/green/red/yellow still readable)

Reference: docs/VISUAL_POLISH_PLAN.md V-10 章节 (v2.1, Wave B-rev)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Color

from pycc2.presentation.rendering.visual_spec import VisualSpec

if TYPE_CHECKING:
    from pycc2.presentation.visual_config import ColorPalette

# ──────────────────────────────────────────────────────────────────────
# Morandi palette constants (RGB tuples)
# ──────────────────────────────────────────────────────────────────────

# Faction colors (Morandi muted)
MORANDI_ALLIED_BLUE: tuple[int, int, int] = (110, 130, 155)  # 雾蓝 (dusty blue)
MORANDI_ALLIED_OUTLINE: tuple[int, int, int] = (140, 160, 180)  # lighter dusty blue
MORANDI_AXIS_GREEN: tuple[int, int, int] = (130, 145, 115)  # 雾绿 (sage green)
MORANDI_AXIS_OUTLINE: tuple[int, int, int] = (155, 170, 140)  # lighter sage
MORANDI_NEUTRAL_GRAY: tuple[int, int, int] = (140, 135, 130)  # 暖灰 (warm gray)
MORANDI_SELECTION: tuple[int, int, int] = (200, 175, 130)  # 米黄 (cream yellow)
MORANDI_DANGER: tuple[int, int, int] = (170, 110, 105)  # 豆沙红 (muted red)
MORANDI_FOG: tuple[int, int, int] = (60, 58, 62)  # 深暖灰
MORANDI_PANEL_BG: tuple[int, int, int, int] = (55, 52, 58, 220)  # 深暖灰半透明
MORANDI_HUD_TEXT: tuple[int, int, int] = (225, 220, 215)  # 米白
MORANDI_TILE_BORDER: tuple[int, int, int] = (75, 72, 78)  # 中暖灰

# Terrain colors (Morandi muted)
MORANDI_TERRAIN_OPEN: tuple[int, int, int] = (180, 175, 160)  # 米色
MORANDI_TERRAIN_ROAD: tuple[int, int, int] = (150, 140, 125)  # 暖灰棕
MORANDI_TERRAIN_GRASS: tuple[int, int, int] = (130, 145, 110)  # 雾绿
MORANDI_TERRAIN_WOODS: tuple[int, int, int] = (95, 110, 85)  # 深雾绿
MORANDI_TERRAIN_BUILDING_ENTERABLE: tuple[int, int, int] = (160, 145, 130)  # 暖米棕
MORANDI_TERRAIN_BUILDING_SOLID: tuple[int, int, int] = (110, 100, 90)  # 深暖棕
MORANDI_TERRAIN_WATER: tuple[int, int, int] = (110, 130, 150)  # 雾蓝
MORANDI_TERRAIN_HEDGE: tuple[int, int, int] = (120, 135, 100)  # 暗雾绿
MORANDI_TERRAIN_WALL: tuple[int, int, int] = (130, 125, 120)  # 中暖灰
MORANDI_TERRAIN_ROUGH: tuple[int, int, int] = (170, 155, 140)  # 暖米
MORANDI_TERRAIN_SHALLOW: tuple[int, int, int] = (140, 155, 170)  # 浅雾蓝
MORANDI_TERRAIN_BRIDGE: tuple[int, int, int] = (155, 135, 115)  # 暖棕

# UI / panel / button colors (Morandi muted)
MORANDI_MINIMAP_BG: tuple[int, int, int] = (45, 43, 48)  # 深暖灰
MORANDI_MINIMAP_BORDER: tuple[int, int, int] = (90, 86, 92)  # 中暖灰
MORANDI_COMMAND_BAR_BG: tuple[int, int, int] = (50, 48, 55)
MORANDI_COMMAND_BAR_BORDER: tuple[int, int, int] = (85, 82, 90)
MORANDI_BUTTON_NORMAL: tuple[int, int, int] = (75, 72, 80)
MORANDI_BUTTON_HOVER: tuple[int, int, int] = (95, 92, 100)
MORANDI_BUTTON_DISABLED: tuple[int, int, int] = (55, 53, 60)
MORANDI_BUTTON_BORDER: tuple[int, int, int] = (110, 105, 115)
MORANDI_BUTTON_TEXT: tuple[int, int, int] = (210, 205, 200)
MORANDI_BUTTON_DISABLED_TEXT: tuple[int, int, int] = (130, 125, 120)

# Combat feedback colors (Morandi muted)
MORANDI_PROJECTILE_HIT: tuple[int, int, int] = (200, 130, 120)  # 暖红
MORANDI_PROJECTILE_MISS: tuple[int, int, int] = (200, 175, 130)  # 米黄
MORANDI_HEALTH_GREEN: tuple[int, int, int] = (130, 165, 120)  # 雾绿
MORANDI_HEALTH_YELLOW: tuple[int, int, int] = (200, 180, 120)  # 米黄
MORANDI_HEALTH_RED: tuple[int, int, int] = (180, 120, 115)  # 豆沙红
MORANDI_MORALE_BLUE: tuple[int, int, int] = (130, 150, 175)  # 雾蓝
MORANDI_SUPPRESSION_OVERLAY: tuple[int, int, int, int] = (100, 50, 50, 100)


def apply_morandi_palette(spec: VisualSpec) -> None:
    """Apply Morandi color palette to a VisualSpec instance in-place.

    Mutates the given ``VisualSpec`` instance to use Morandi-style colors.
    The original CC2-faithful colors are overwritten. To revert, create a
    fresh ``VisualSpec()`` instance.

    Args:
        spec: VisualSpec instance to mutate in-place.
    """
    # Faction colors
    spec.allied_unit_color = MORANDI_ALLIED_BLUE
    spec.allied_outline_color = MORANDI_ALLIED_OUTLINE
    spec.axis_unit_color = MORANDI_AXIS_GREEN
    spec.axis_outline_color = MORANDI_AXIS_OUTLINE
    spec.neutral_color = MORANDI_NEUTRAL_GRAY
    spec.selection_color = MORANDI_SELECTION
    spec.danger_color = MORANDI_DANGER
    spec.fog_color = MORANDI_FOG
    spec.panel_background_color = MORANDI_PANEL_BG
    spec.hud_text_color = MORANDI_HUD_TEXT
    spec.tile_border_color = MORANDI_TILE_BORDER
    spec.hud_background_color = (55, 52, 58, 200)
    spec.hud_border_color = MORANDI_COMMAND_BAR_BORDER
    spec.panel_border_color = MORANDI_COMMAND_BAR_BORDER
    spec.minimap_background_color = MORANDI_MINIMAP_BG
    spec.minimap_border_color = MORANDI_MINIMAP_BORDER
    spec.command_bar_bg_color = MORANDI_COMMAND_BAR_BG
    spec.command_bar_border_color = MORANDI_COMMAND_BAR_BORDER
    spec.button_normal_color = MORANDI_BUTTON_NORMAL
    spec.button_hover_color = MORANDI_BUTTON_HOVER
    spec.button_disabled_color = MORANDI_BUTTON_DISABLED
    spec.button_border_color = MORANDI_BUTTON_BORDER
    spec.button_text_color = MORANDI_BUTTON_TEXT
    spec.button_disabled_text_color = MORANDI_BUTTON_DISABLED_TEXT
    spec.projectile_hit_color = MORANDI_PROJECTILE_HIT
    spec.projectile_miss_color = MORANDI_PROJECTILE_MISS
    spec.health_bar_green = MORANDI_HEALTH_GREEN
    spec.health_bar_yellow = MORANDI_HEALTH_YELLOW
    spec.health_bar_red = MORANDI_HEALTH_RED
    spec.morale_bar_blue = MORANDI_MORALE_BLUE
    spec.suppression_overlay = MORANDI_SUPPRESSION_OVERLAY

    # Terrain colors
    spec.terrain_colors = {
        # Import locally to avoid module-level dependency cycle.
        # TerrainType is an enum; import at call time is cheap.
        _get_terrain_type("OPEN"): MORANDI_TERRAIN_OPEN,
        _get_terrain_type("ROAD"): MORANDI_TERRAIN_ROAD,
        _get_terrain_type("GRASS"): MORANDI_TERRAIN_GRASS,
        _get_terrain_type("WOODS"): MORANDI_TERRAIN_WOODS,
        _get_terrain_type("BUILDING_ENTERABLE"): MORANDI_TERRAIN_BUILDING_ENTERABLE,
        _get_terrain_type("BUILDING_SOLID"): MORANDI_TERRAIN_BUILDING_SOLID,
        _get_terrain_type("WATER"): MORANDI_TERRAIN_WATER,
        _get_terrain_type("HEDGE"): MORANDI_TERRAIN_HEDGE,
        _get_terrain_type("WALL"): MORANDI_TERRAIN_WALL,
        _get_terrain_type("ROUGH"): MORANDI_TERRAIN_ROUGH,
        _get_terrain_type("SHALLOW"): MORANDI_TERRAIN_SHALLOW,
        _get_terrain_type("BRIDGE"): MORANDI_TERRAIN_BRIDGE,
    }


def _get_terrain_type(name: str):
    """Lookup TerrainType enum member by name (lazy import to avoid cycle)."""
    from pycc2.domain.value_objects.terrain_type import TerrainType

    return TerrainType[name]


def is_morandi_applied(spec: VisualSpec) -> bool:
    """Check whether Morandi palette has been applied to a VisualSpec.

    Args:
        spec: VisualSpec instance to check.

    Returns:
        True if the spec's ``allied_unit_color`` matches Morandi palette.
    """
    return tuple(spec.allied_unit_color[:3]) == MORANDI_ALLIED_BLUE


# ──────────────────────────────────────────────────────────────────────
# ColorPalette (visual_config.py) Morandi adapter
# ──────────────────────────────────────────────────────────────────────


def morandi_color_palette() -> ColorPalette:
    """Build a ColorPalette (visual_config.py) with Morandi-styled Colors.

    Returns a new ``ColorPalette`` instance with all 24 color fields set
    to Morandi-style values. Used by V-10 ThemeManager to swap the
    ``DEFAULT_VISUAL_CONFIG.palette`` when the user toggles the Morandi skin.

    Returns:
        ColorPalette: Morandi-styled palette instance.
    """
    from pycc2.presentation.visual_config import ColorPalette as _ColorPalette

    return _ColorPalette(
        GRASS_PRIMARY=Color(*MORANDI_TERRAIN_GRASS),
        GRASS_HIGHLIGHT=Color(145, 160, 125),
        GRASS_SHADOW=Color(95, 110, 80),
        DIRT_PRIMARY=Color(155, 135, 115),
        SAND_PRIMARY=Color(190, 175, 155),
        SNOW_PRIMARY=Color(230, 225, 220),
        WATER_PRIMARY=Color(*MORANDI_TERRAIN_WATER),
        FOREST_PRIMARY=Color(*MORANDI_TERRAIN_WOODS),
        URBAN_PRIMARY=Color(135, 130, 130),
        ROAD_PRIMARY=Color(*MORANDI_TERRAIN_ROAD),
        ALLIES_PRIMARY=Color(*MORANDI_ALLIED_BLUE),
        AMERICAN_PRIMARY=Color(120, 140, 165),
        BRITISH_PRIMARY=Color(130, 145, 125),
        POLISH_PRIMARY=Color(155, 130, 110),
        AXIS_PRIMARY=Color(*MORANDI_AXIS_GREEN),
        GERMAN_PRIMARY=Color(115, 130, 100),
        HIGHLIGHT_ALLIES=Color(140, 160, 180),
        HIGHLIGHT_AXIS=Color(155, 170, 140),
        UI_PANEL=Color(55, 52, 58),
        UI_BORDER=Color(85, 82, 90),
        UI_TEXT=Color(*MORANDI_HUD_TEXT),
        UI_HIGHLIGHT=Color(*MORANDI_SELECTION),
        UI_VICTORY=Color(*MORANDI_HEALTH_GREEN),
        UI_DEFEAT=Color(*MORANDI_DANGER),
    )


__all__ = [
    # Morandi color constants
    "MORANDI_ALLIED_BLUE",
    "MORANDI_ALLIED_OUTLINE",
    "MORANDI_AXIS_GREEN",
    "MORANDI_AXIS_OUTLINE",
    "MORANDI_NEUTRAL_GRAY",
    "MORANDI_SELECTION",
    "MORANDI_DANGER",
    "MORANDI_FOG",
    "MORANDI_PANEL_BG",
    "MORANDI_HUD_TEXT",
    "MORANDI_TILE_BORDER",
    "MORANDI_MINIMAP_BG",
    "MORANDI_MINIMAP_BORDER",
    "MORANDI_COMMAND_BAR_BG",
    "MORANDI_COMMAND_BAR_BORDER",
    "MORANDI_BUTTON_NORMAL",
    "MORANDI_BUTTON_HOVER",
    "MORANDI_BUTTON_DISABLED",
    "MORANDI_BUTTON_BORDER",
    "MORANDI_BUTTON_TEXT",
    "MORANDI_BUTTON_DISABLED_TEXT",
    "MORANDI_PROJECTILE_HIT",
    "MORANDI_PROJECTILE_MISS",
    "MORANDI_HEALTH_GREEN",
    "MORANDI_HEALTH_YELLOW",
    "MORANDI_HEALTH_RED",
    "MORANDI_MORALE_BLUE",
    "MORANDI_SUPPRESSION_OVERLAY",
    "MORANDI_TERRAIN_OPEN",
    "MORANDI_TERRAIN_ROAD",
    "MORANDI_TERRAIN_GRASS",
    "MORANDI_TERRAIN_WOODS",
    "MORANDI_TERRAIN_BUILDING_ENTERABLE",
    "MORANDI_TERRAIN_BUILDING_SOLID",
    "MORANDI_TERRAIN_WATER",
    "MORANDI_TERRAIN_HEDGE",
    "MORANDI_TERRAIN_WALL",
    "MORANDI_TERRAIN_ROUGH",
    "MORANDI_TERRAIN_SHALLOW",
    "MORANDI_TERRAIN_BRIDGE",
    # Functions
    "apply_morandi_palette",
    "is_morandi_applied",
    "morandi_color_palette",
]
