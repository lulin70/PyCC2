"""Campaign UI helper functions (drawing utilities)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame
from pygame import Rect, Surface, draw
from pygame.font import Font

if TYPE_CHECKING:
    from pycc2.presentation.ui.campaign_ui import CampaignUI


def draw_button(
    ui: CampaignUI,
    surface: Surface,
    rect: Rect,
    text: str,
    hovered: bool,
    text_color: tuple | None = None,
) -> None:
    """Draw a styled button."""
    assert ui._font_normal is not None
    bg = ui.BUTTON_HOVER if hovered else ui.BUTTON_COLOR
    draw.rect(surface, bg, rect, border_radius=4)
    draw.rect(surface, ui.BUTTON_BORDER, rect, 1, border_radius=4)
    color = text_color or ui.HIGHLIGHT_COLOR
    txt = ui._font_normal.render(text, True, color)
    surface.blit(
        txt,
        (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2),
    )


def wrap_text(text: str, font: Font, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        if font.size(test)[0] < max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


def draw_strategic_map(
    ui: CampaignUI,
    surface: Surface,
    x: int,
    y: int,
    size: int,
    sector: str,
    current_day: int,
) -> None:
    """Draw a strategic map showing the three Market Garden sectors with current position."""
    assert ui._font_small is not None
    # Map background
    draw.rect(surface, ui.MINIMAP_BG, Rect(x, y, size, size))
    draw.rect(surface, ui.BORDER_COLOR, Rect(x, y, size, size), 1)

    # Sector layout: three vertical strips (Eindhoven bottom, Nijmegen middle, Arnhem top)
    sector_h = size // 3
    sector_colors = {
        "arnhem": (50, 70, 50),
        "nijmegen": (50, 65, 55),
        "eindhoven": (55, 60, 50),
    }
    sector_labels = {
        "arnhem": "ARNHEM",
        "nijmegen": "NIJMEGEN",
        "eindhoven": "EINDHOVEN",
    }
    sector_order = ["arnhem", "nijmegen", "eindhoven"]

    for i, sec_id in enumerate(sector_order):
        sy = y + i * sector_h
        bg = sector_colors.get(sec_id, (50, 60, 50))
        draw.rect(surface, bg, Rect(x + 1, sy + 1, size - 2, sector_h - 2))

        # Highlight current sector
        if sec_id == sector:
            draw.rect(surface, ui.HIGHLIGHT_COLOR, Rect(x + 1, sy + 1, size - 2, sector_h - 2), 2)

        # Sector label
        label = ui._font_small.render(
            sector_labels.get(sec_id, sec_id.upper()), True, (200, 200, 190)
        )
        surface.blit(label, (x + 5, sy + 4))

    # Draw "Hell's Highway" road line connecting sectors
    road_x = x + size // 2
    draw.line(surface, (128, 128, 128), (road_x, y + sector_h), (road_x, y + 2 * sector_h), 2)
    draw.line(surface, (128, 128, 128), (road_x, y + 2 * sector_h), (road_x, y + 3 * sector_h), 2)

    # Day progress indicator
    day_pct = min(current_day / 9.0, 1.0)
    progress_w = int((size - 4) * day_pct)
    draw.rect(surface, (60, 60, 60), Rect(x + 2, y + size - 8, size - 4, 6))
    draw.rect(surface, ui.COMPLETED_COLOR, Rect(x + 2, y + size - 8, progress_w, 6))

    day_label = ui._font_small.render(f"D{current_day}", True, ui.HIGHLIGHT_COLOR)
    surface.blit(day_label, (x + size - 25, y + size - 22))


def draw_mini_map(
    ui: CampaignUI, surface: Surface, x: int, y: int, size: int, map_file: str
) -> None:
    """Draw a simple terrain preview for the given map file."""
    # Try to load the map and render a mini preview
    try:
        import json
        from pathlib import Path

        map_path = Path(f"data/maps/{map_file}.json")
        if not map_path.exists():
            # Try without extension
            map_path = Path(f"data/maps/{map_file}")
        if map_path.exists():
            with open(map_path) as f:
                map_data = json.load(f)
            tiles = map_data.get("tiles", [])
            if tiles:
                rows = len(tiles)
                cols = len(tiles[0]) if tiles else 0
                if rows > 0 and cols > 0:
                    tile_w = size / cols
                    tile_h = size / rows
                    terrain_colors = {
                        "grass": (76, 153, 0),
                        "open": (200, 200, 180),
                        "road": (128, 128, 128),
                        "woods": (34, 100, 34),
                        "forest": (34, 100, 34),
                        "water": (65, 105, 225),
                        "building": (160, 140, 120),
                        "building_enterable": (160, 140, 120),
                        "building_solid": (100, 80, 60),
                        "hedge": (80, 120, 40),
                        "bridge": (139, 119, 101),
                        "dirt": (154, 140, 125),
                        "rough": (154, 140, 125),
                        "trench": (90, 75, 60),
                        "crater": (90, 75, 60),
                        "wall": (105, 105, 105),
                        "shallow": (100, 149, 237),
                        "swamp": (60, 80, 50),
                    }
                    for r, row in enumerate(tiles):
                        for c, tile in enumerate(row):
                            terrain_name = tile if isinstance(tile, str) else str(tile)
                            color = terrain_colors.get(terrain_name.lower(), (76, 153, 0))
                            rx = x + int(c * tile_w)
                            ry = y + int(r * tile_h)
                            rw = int((c + 1) * tile_w) - int(c * tile_w)
                            rh = int((r + 1) * tile_h) - int(r * tile_h)
                            draw.rect(surface, color, Rect(rx, ry, rw, rh))
                    return
    except (pygame.error, ValueError, TypeError) as e:
        logging.debug("Campaign map rendering failed: %s", e)

    # Fallback: placeholder grid
    grid_size = 10
    tile_w = size / grid_size
    tile_h = size / grid_size
    for r in range(grid_size):
        for c in range(grid_size):
            color = (76, 153, 0) if (r + c) % 3 != 0 else (128, 128, 128)
            rx = x + int(c * tile_w)
            ry = y + int(r * tile_h)
            rw = int((c + 1) * tile_w) - int(c * tile_w)
            rh = int((r + 1) * tile_h) - int(r * tile_h)
            draw.rect(surface, color, Rect(rx, ry, rw, rh))
