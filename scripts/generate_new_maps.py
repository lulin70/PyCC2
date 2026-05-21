#!/usr/bin/env python3
"""Generate 5 new historically-accurate CC2 map JSON files for Operation Market Garden."""

import json
import random
import math
from pathlib import Path

# Terrain type codes (matching PyCC2 TerrainType enum)
OPEN = 0
ROAD = 1
GRASS = 2
WOODS = 3
BUILDING_ENTERABLE = 4
BUILDING_SOLID = 5
WATER = 6
HEDGE = 7
WALL = 8
ROUGH = 9
SHALLOW = 10
BRIDGE = 11
CRATER = 12
SWAMP = 13

# Terrain type name mapping for tile objects
TERRAIN_NAMES = {
    OPEN: "open",
    ROAD: "road",
    GRASS: "grass",
    WOODS: "forest",
    BUILDING_ENTERABLE: "building",
    BUILDING_SOLID: "building",
    WATER: "water",
    HEDGE: "hedge",
    WALL: "wall",
    ROUGH: "rubble",
    SHALLOW: "marsh",
    BRIDGE: "bridge",
    CRATER: "rubble",
    SWAMP: "marsh",
}

# Terrain properties: (elevation, cover_modifier, movement_cost, is_passable)
TERRAIN_PROPS = {
    OPEN:       (0, 0.0, 1.0, True),
    ROAD:       (0, 0.0, 0.8, True),
    GRASS:      (0, 0.05, 1.2, True),
    WOODS:      (2, 0.20, 2.0, True),
    BUILDING_ENTERABLE: (3, 0.50, 1.5, True),
    BUILDING_SOLID:     (4, 0.80, 99.0, False),
    WATER:      (0, 0.0, 99.0, False),
    HEDGE:      (1, 0.15, 2.5, True),
    WALL:       (3, 0.70, 99.0, False),
    ROUGH:      (1, 0.10, 1.8, True),
    SHALLOW:    (0, 0.0, 3.0, True),
    BRIDGE:     (1, 0.0, 0.9, True),
    CRATER:     (-1, 0.30, 2.5, True),
    SWAMP:      (0, 0.0, 4.0, True),
}


def make_tile(terrain_code):
    """Create a tile object with terrain_type, elevation, cover_modifier, movement_cost, is_passable."""
    elev, cover, cost, passable = TERRAIN_PROPS[terrain_code]
    return {
        "terrain_type": TERRAIN_NAMES[terrain_code],
        "elevation": elev,
        "cover_modifier": cover,
        "movement_cost": cost,
        "is_passable": passable,
    }


def make_grid(width, height, default=GRASS):
    """Create a 2D grid filled with default terrain."""
    return [[default for _ in range(width)] for _ in range(height)]


def fill_rect(grid, x, y, w, h, terrain):
    """Fill a rectangular area with terrain."""
    for row in range(y, min(y + h, len(grid))):
        for col in range(x, min(x + w, len(grid[0]))):
            grid[row][col] = terrain


def fill_column(grid, x, y1, y2, terrain):
    """Fill a vertical strip."""
    for row in range(y1, min(y2, len(grid))):
        if 0 <= x < len(grid[0]):
            grid[row][x] = terrain


def fill_row(grid, y, x1, x2, terrain):
    """Fill a horizontal strip."""
    if 0 <= y < len(grid):
        for col in range(x1, min(x2, len(grid[0]))):
            grid[y][col] = terrain


def scatter_terrain(grid, x, y, w, h, terrain, density=0.3, rng=None):
    """Randomly scatter terrain in a rectangular area."""
    if rng is None:
        rng = random.Random(42)
    for row in range(y, min(y + h, len(grid))):
        for col in range(x, min(x + w, len(grid[0]))):
            if rng.random() < density:
                grid[row][col] = terrain


def add_road_v(grid, x, y1, y2, width=1):
    """Add a vertical road."""
    for offset in range(width):
        fill_column(grid, x + offset, y1, y2, ROAD)


def add_road_h(grid, y, x1, x2, width=1):
    """Add a horizontal road."""
    for offset in range(width):
        fill_row(grid, y + offset, x1, x2, ROAD)


def add_building_cluster(grid, cx, cy, size=2, rng=None):
    """Add a cluster of buildings around center point."""
    if rng is None:
        rng = random.Random(42)
    for dy in range(-size, size + 1):
        for dx in range(-size, size + 1):
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < len(grid) and 0 <= nx < len(grid[0]):
                if rng.random() < 0.6:
                    grid[ny][nx] = BUILDING_ENTERABLE if rng.random() < 0.7 else BUILDING_SOLID


def add_river_h(grid, y, x1, x2, width=3):
    """Add a horizontal river with shallow edges."""
    for offset in range(width):
        row = y + offset
        if 0 <= row < len(grid):
            for col in range(x1, min(x2, len(grid[0]))):
                if offset == 0 or offset == width - 1:
                    grid[row][col] = SHALLOW
                else:
                    grid[row][col] = WATER


def add_river_v(grid, x, y1, y2, width=3):
    """Add a vertical river with shallow edges."""
    for offset in range(width):
        col = x + offset
        for row in range(y1, min(y2, len(grid))):
            if 0 <= col < len(grid[0]):
                if offset == 0 or offset == width - 1:
                    grid[row][col] = SHALLOW
                else:
                    grid[row][col] = WATER


def add_bridge_h(grid, y, x1, x2, width=3):
    """Add a horizontal bridge over river."""
    for offset in range(width):
        row = y + offset
        if 0 <= row < len(grid):
            for col in range(x1, min(x2, len(grid[0]))):
                grid[row][col] = BRIDGE


def add_bridge_v(grid, x, y1, y2, width=3):
    """Add a vertical bridge over river."""
    for offset in range(width):
        col = x + offset
        for row in range(y1, min(y2, len(grid))):
            if 0 <= col < len(grid[0]):
                grid[row][col] = BRIDGE


def add_street_grid(grid, x, y, w, h, spacing=4, rng=None):
    """Add a grid of streets in an urban area."""
    if rng is None:
        rng = random.Random(42)
    # Horizontal streets
    for row in range(y, min(y + h, len(grid)), spacing):
        fill_row(grid, row, x, min(x + w, len(grid[0])), ROAD)
    # Vertical streets
    for col in range(x, min(x + w, len(grid[0])), spacing):
        fill_column(grid, col, y, min(y + h, len(grid)), ROAD)


def add_wall_rect(grid, x, y, w, h):
    """Add a wall rectangle (perimeter only)."""
    fill_row(grid, y, x, x + w, WALL)
    fill_row(grid, y + h - 1, x, x + w, WALL)
    fill_column(grid, x, y, y + h, WALL)
    fill_column(grid, x + w - 1, y, y + h, WALL)


def convert_tiles_to_objects(grid):
    """Convert numeric grid to tile object grid."""
    return [[make_tile(grid[row][col]) for col in range(len(grid[0]))] for row in range(len(grid))]


def build_map(id_str, name, width, height, grid, metadata, victory_locations, deployment_zones, objectives, spawn_points, rng=None):
    """Build the complete map JSON structure."""
    return {
        "id": id_str,
        "name": name,
        "width": width,
        "height": height,
        "metadata": metadata,
        "tiles": convert_tiles_to_objects(grid),
        "victory_locations": victory_locations,
        "deployment_zones": deployment_zones,
        "objectives": objectives,
        "spawn_points": spawn_points,
    }


# ============================================================
# Map 1: Arnhem Zoo (阿纳姆动物园)
# ============================================================
def generate_arnhem_zoo():
    W, H = 40, 35
    rng = random.Random(2001)
    grid = make_grid(W, H, GRASS)

    # Open park areas surrounding the zoo
    fill_rect(grid, 0, 0, W, H, OPEN)
    scatter_terrain(grid, 0, 0, W, H, GRASS, density=0.35, rng=rng)

    # Main road running north-south through center (cols 19-20)
    add_road_v(grid, 19, 0, H, width=2)

    # Cross roads
    add_road_h(grid, 10, 5, 35, width=1)
    add_road_h(grid, 24, 5, 35, width=1)

    # Zoo perimeter walls (cols 10-30, rows 6-28)
    add_wall_rect(grid, 10, 6, 20, 22)

    # Zoo gate on south wall (break in wall at road intersection)
    fill_row(grid, 27, 19, 21, ROAD)
    fill_row(grid, 28, 19, 21, ROAD)

    # Zoo gate on north wall
    fill_row(grid, 6, 19, 21, ROAD)
    fill_row(grid, 7, 19, 21, ROAD)

    # Animal enclosures inside zoo (buildings)
    # Large cat enclosure (north part)
    fill_rect(grid, 12, 8, 5, 4, BUILDING_SOLID)
    fill_rect(grid, 13, 9, 3, 2, BUILDING_ENTERABLE)

    # Elephant house (center)
    fill_rect(grid, 22, 13, 6, 5, BUILDING_ENTERABLE)
    fill_rect(grid, 23, 14, 4, 3, BUILDING_SOLID)

    # Bird house (east side)
    fill_rect(grid, 26, 8, 3, 4, BUILDING_ENTERABLE)
    fill_rect(grid, 27, 9, 1, 2, BUILDING_SOLID)

    # Reptile house (west side)
    fill_rect(grid, 12, 18, 4, 3, BUILDING_ENTERABLE)
    fill_rect(grid, 13, 19, 2, 1, BUILDING_SOLID)

    # Small mammal house
    fill_rect(grid, 24, 21, 4, 3, BUILDING_ENTERABLE)
    fill_rect(grid, 25, 22, 2, 1, BUILDING_SOLID)

    # Internal zoo paths
    add_road_h(grid, 12, 11, 29, width=1)
    add_road_h(grid, 20, 11, 29, width=1)
    add_road_v(grid, 15, 7, 27, width=1)
    add_road_v(grid, 24, 7, 27, width=1)

    # Open park areas inside zoo
    fill_rect(grid, 16, 8, 3, 3, GRASS)
    fill_rect(grid, 16, 14, 5, 4, GRASS)
    fill_rect(grid, 16, 21, 4, 3, GRASS)

    # Residential streets west of zoo (cols 0-9, rows 4-30)
    add_street_grid(grid, 0, 4, 9, 26, spacing=4, rng=rng)
    scatter_terrain(grid, 0, 4, 9, 26, BUILDING_ENTERABLE, density=0.35, rng=rng)
    scatter_terrain(grid, 0, 4, 9, 26, BUILDING_SOLID, density=0.1, rng=rng)

    # Residential streets east of zoo (cols 31-39, rows 4-30)
    add_street_grid(grid, 31, 4, 9, 26, spacing=4, rng=rng)
    scatter_terrain(grid, 31, 4, 9, 26, BUILDING_ENTERABLE, density=0.35, rng=rng)
    scatter_terrain(grid, 31, 4, 9, 26, BUILDING_SOLID, density=0.1, rng=rng)

    # Hedges around residential areas
    scatter_terrain(grid, 0, 0, 10, 4, HEDGE, density=0.15, rng=rng)
    scatter_terrain(grid, 30, 0, 10, 4, HEDGE, density=0.15, rng=rng)
    scatter_terrain(grid, 0, 30, 10, 5, HEDGE, density=0.15, rng=rng)
    scatter_terrain(grid, 30, 30, 10, 5, HEDGE, density=0.15, rng=rng)

    # Some craters/rubble from fighting
    scatter_terrain(grid, 10, 6, 20, 22, CRATER, density=0.08, rng=rng)

    return build_map(
        id_str="arnhem_zoo",
        name="Arnhem Zoo — 阿纳姆动物园",
        width=W, height=H, grid=grid,
        metadata={
            "name": "Arnhem Zoo",
            "description": "The Arnhem Zoo area was the site of intense fighting on Day 1-2 of Market Garden. The zoo's thick walls provided excellent defensive positions for British paratroopers as German forces attempted to dislodge them.",
            "sector": "Arnhem",
            "historical_day": "1944-09-18",
            "historical_battle": "Battle of Arnhem - Zoo Sector",
        },
        victory_locations=[
            {"id": "vl_zoo_gate", "name": "Zoo Gate", "position": [20, 27], "value": 15, "type": "regular"},
            {"id": "vl_zoo_walls", "name": "Zoo Walls", "position": [15, 17], "value": 19, "type": "regular"},
            {"id": "vl_park_road", "name": "Park Road", "position": [20, 10], "value": 10, "type": "road"},
        ],
        deployment_zones={
            "allies": {"x": 5, "y": 28, "width": 30, "height": 6},
            "axis": {"x": 5, "y": 0, "width": 30, "height": 5},
        },
        objectives=[
            {"id": "obj_zoo_gate", "name": "Zoo Gate", "position": [20, 27], "radius": 3, "required": True, "owner": None},
            {"id": "obj_zoo_walls", "name": "Zoo Walls", "position": [15, 17], "radius": 5, "required": True, "owner": None},
            {"id": "obj_park_road", "name": "Park Road", "position": [20, 10], "radius": 3, "required": False, "owner": None},
        ],
        spawn_points=[
            {"id": "spawn_allies", "side": "allies", "position": [20, 32], "units_max": 25},
            {"id": "spawn_axis", "side": "axis", "position": [20, 2], "units_max": 22},
        ],
    )


# ============================================================
# Map 2: Arnhem Koepel (阿纳姆穹顶教堂)
# ============================================================
def generate_arnhem_koepel():
    W, H = 36, 30
    rng = random.Random(2002)
    grid = make_grid(W, H, GRASS)

    # Base: open/residential area
    fill_rect(grid, 0, 0, W, H, OPEN)
    scatter_terrain(grid, 0, 0, W, H, GRASS, density=0.3, rng=rng)

    # Streets radiating from church square
    # Main east-west road
    add_road_h(grid, 14, 0, W, width=2)
    # Main north-south road
    add_road_v(grid, 17, 0, H, width=2)
    # Diagonal-ish roads (represented as L-shaped)
    add_road_h(grid, 8, 5, 18, width=1)
    add_road_v(grid, 10, 8, 14, width=1)
    add_road_h(grid, 20, 18, 32, width=1)
    add_road_v(grid, 26, 14, 20, width=1)
    # Secondary roads
    add_road_h(grid, 5, 0, 36, width=1)
    add_road_h(grid, 24, 0, 36, width=1)

    # Koepel (dome church) in center - large building complex
    # Main dome building
    fill_rect(grid, 14, 11, 8, 6, BUILDING_SOLID)
    # Church interior (enterable)
    fill_rect(grid, 15, 12, 6, 4, BUILDING_ENTERABLE)
    # Church tower (solid, tall)
    fill_rect(grid, 17, 10, 2, 1, BUILDING_SOLID)
    # Church annex
    fill_rect(grid, 22, 12, 3, 3, BUILDING_ENTERABLE)
    fill_rect(grid, 23, 13, 1, 1, BUILDING_SOLID)
    # Church entrance
    fill_rect(grid, 17, 17, 2, 1, ROAD)

    # Church square (open area around church)
    fill_rect(grid, 12, 9, 14, 10, OPEN)

    # Small park northeast of church
    fill_rect(grid, 26, 5, 6, 5, GRASS)
    scatter_terrain(grid, 26, 5, 6, 5, WOODS, density=0.3, rng=rng)

    # Residential blocks - northwest
    add_street_grid(grid, 1, 1, 10, 7, spacing=3, rng=rng)
    scatter_terrain(grid, 1, 1, 10, 7, BUILDING_ENTERABLE, density=0.4, rng=rng)
    scatter_terrain(grid, 1, 1, 10, 7, BUILDING_SOLID, density=0.12, rng=rng)

    # Residential blocks - southwest
    add_street_grid(grid, 1, 18, 10, 10, spacing=3, rng=rng)
    scatter_terrain(grid, 1, 18, 10, 10, BUILDING_ENTERABLE, density=0.4, rng=rng)
    scatter_terrain(grid, 1, 18, 10, 10, BUILDING_SOLID, density=0.12, rng=rng)

    # Residential blocks - northeast
    add_street_grid(grid, 26, 1, 9, 7, spacing=3, rng=rng)
    scatter_terrain(grid, 26, 1, 9, 7, BUILDING_ENTERABLE, density=0.4, rng=rng)
    scatter_terrain(grid, 26, 1, 9, 7, BUILDING_SOLID, density=0.12, rng=rng)

    # Residential blocks - southeast
    add_street_grid(grid, 26, 18, 9, 10, spacing=3, rng=rng)
    scatter_terrain(grid, 26, 18, 9, 10, BUILDING_ENTERABLE, density=0.4, rng=rng)
    scatter_terrain(grid, 26, 18, 9, 10, BUILDING_SOLID, density=0.12, rng=rng)

    # Hedges in residential areas
    scatter_terrain(grid, 1, 1, 10, 7, HEDGE, density=0.08, rng=rng)
    scatter_terrain(grid, 1, 18, 10, 10, HEDGE, density=0.08, rng=rng)

    # Craters from artillery
    scatter_terrain(grid, 12, 9, 14, 10, CRATER, density=0.06, rng=rng)

    # Wall segments around some properties
    fill_row(grid, 8, 1, 11, WALL)
    fill_row(grid, 18, 1, 11, WALL)

    return build_map(
        id_str="arnhem_koepel",
        name="Arnhem Koepel — 阿纳姆穹顶教堂",
        width=W, height=H, grid=grid,
        metadata={
            "name": "Arnhem Koepel",
            "description": "The Koepel (dome church) was a major landmark and strongpoint in central Arnhem. German forces used its tower as an observation post to direct artillery fire on British positions.",
            "sector": "Arnhem",
            "historical_day": "1944-09-19",
            "historical_battle": "Battle of Arnhem - Central Sector",
        },
        victory_locations=[
            {"id": "vl_koepel_church", "name": "Koepel Church", "position": [18, 14], "value": 19, "type": "regular"},
            {"id": "vl_church_square", "name": "Church Square", "position": [18, 9], "value": 15, "type": "regular"},
            {"id": "vl_north_approach", "name": "North Approach", "position": [18, 5], "value": 10, "type": "road"},
        ],
        deployment_zones={
            "allies": {"x": 0, "y": 8, "width": 6, "height": 14},
            "axis": {"x": 30, "y": 8, "width": 6, "height": 14},
        },
        objectives=[
            {"id": "obj_koepel", "name": "Koepel Church", "position": [18, 14], "radius": 4, "required": True, "owner": None},
            {"id": "obj_square", "name": "Church Square", "position": [18, 9], "radius": 3, "required": True, "owner": None},
            {"id": "obj_north", "name": "North Approach", "position": [18, 5], "radius": 3, "required": False, "owner": None},
        ],
        spawn_points=[
            {"id": "spawn_allies", "side": "allies", "position": [2, 14], "units_max": 22},
            {"id": "spawn_axis", "side": "axis", "position": [34, 14], "units_max": 20},
        ],
    )


# ============================================================
# Map 3: Best (贝斯特)
# ============================================================
def generate_arnhem_best():
    W, H = 44, 38
    rng = random.Random(2003)
    grid = make_grid(W, H, GRASS)

    # Farmland base
    fill_rect(grid, 0, 0, W, H, OPEN)
    scatter_terrain(grid, 0, 0, W, H, GRASS, density=0.3, rng=rng)

    # Wilhelmina Canal running east-west through center (rows 17-20)
    add_river_h(grid, 17, 0, W, width=4)

    # Bridge site (destroyed) - represented as rubble/crater where bridge was
    fill_rect(grid, 18, 17, 5, 4, CRATER)
    # Bridge remnants
    fill_rect(grid, 19, 18, 3, 2, BRIDGE)

    # Road to Eindhoven running north-south (cols 20-21)
    add_road_v(grid, 20, 0, 17, width=2)
    add_road_v(grid, 20, 21, H, width=2)

    # Village center with buildings (cols 14-30, rows 8-15)
    add_street_grid(grid, 14, 8, 16, 7, spacing=3, rng=rng)
    scatter_terrain(grid, 14, 8, 16, 7, BUILDING_ENTERABLE, density=0.4, rng=rng)
    scatter_terrain(grid, 14, 8, 16, 7, BUILDING_SOLID, density=0.12, rng=rng)

    # Village church (solid building)
    fill_rect(grid, 20, 10, 3, 3, BUILDING_SOLID)
    fill_rect(grid, 21, 11, 1, 1, BUILDING_ENTERABLE)

    # Village houses south of canal (cols 14-30, rows 22-30)
    add_street_grid(grid, 14, 22, 16, 8, spacing=3, rng=rng)
    scatter_terrain(grid, 14, 22, 16, 8, BUILDING_ENTERABLE, density=0.35, rng=rng)
    scatter_terrain(grid, 14, 22, 16, 8, BUILDING_SOLID, density=0.1, rng=rng)

    # Canal lock on west side (cols 4-8, rows 16-21)
    fill_rect(grid, 4, 16, 4, 5, BUILDING_SOLID)
    fill_rect(grid, 5, 17, 2, 3, BUILDING_ENTERABLE)
    # Lock mechanism
    fill_rect(grid, 8, 18, 1, 2, ROUGH)

    # Cross roads in village
    add_road_h(grid, 11, 14, 30, width=1)
    add_road_h(grid, 26, 14, 30, width=1)
    add_road_v(grid, 16, 8, 15, width=1)
    add_road_v(grid, 26, 8, 15, width=1)

    # Farmland hedges (field boundaries)
    for y in range(2, 17, 4):
        fill_row(grid, y, 0, 14, HEDGE)
    for y in range(22, 36, 4):
        fill_row(grid, y, 0, 14, HEDGE)
    for y in range(2, 17, 4):
        fill_row(grid, y, 30, 14, HEDGE)
    for y in range(22, 36, 4):
        fill_row(grid, y, 30, 14, HEDGE)

    # Woods on flanks
    scatter_terrain(grid, 0, 0, 6, 17, WOODS, density=0.5, rng=rng)
    scatter_terrain(grid, 38, 0, 6, 17, WOODS, density=0.5, rng=rng)
    scatter_terrain(grid, 0, 21, 6, 17, WOODS, density=0.5, rng=rng)
    scatter_terrain(grid, 38, 21, 6, 17, WOODS, density=0.5, rng=rng)

    # German defensive positions on south bank
    fill_rect(grid, 16, 22, 2, 2, BUILDING_SOLID)  # Bunker
    fill_rect(grid, 24, 22, 2, 2, BUILDING_SOLID)  # Bunker
    fill_rect(grid, 14, 24, 6, 1, ROUGH)  # Trench
    fill_rect(grid, 22, 24, 6, 1, ROUGH)  # Trench

    # Craters from fighting around bridge
    scatter_terrain(grid, 16, 15, 8, 6, CRATER, density=0.15, rng=rng)

    return build_map(
        id_str="arnhem_best",
        name="Best — 贝斯特",
        width=W, height=H, grid=grid,
        metadata={
            "name": "Best",
            "description": "The village of Best west of Eindhoven, where the 101st Airborne fought to secure the bridge over the Wilhelmina Canal. The bridge was blown by the Germans before it could be captured.",
            "sector": "Best",
            "historical_day": "1944-09-17",
            "historical_battle": "101st Airborne - Best Sector",
        },
        victory_locations=[
            {"id": "vl_canal_bridge", "name": "Canal Bridge Site", "position": [20, 19], "value": 30, "type": "bridge"},
            {"id": "vl_village_center", "name": "Village Center", "position": [22, 11], "value": 15, "type": "regular"},
            {"id": "vl_canal_lock", "name": "Canal Lock", "position": [6, 18], "value": 10, "type": "road"},
        ],
        deployment_zones={
            "allies": {"x": 8, "y": 0, "width": 28, "height": 6},
            "axis": {"x": 8, "y": 31, "width": 28, "height": 6},
        },
        objectives=[
            {"id": "obj_bridge", "name": "Canal Bridge Site", "position": [20, 19], "radius": 4, "required": True, "owner": None},
            {"id": "obj_village", "name": "Village Center", "position": [22, 11], "radius": 4, "required": True, "owner": None},
            {"id": "obj_lock", "name": "Canal Lock", "position": [6, 18], "radius": 3, "required": False, "owner": None},
        ],
        spawn_points=[
            {"id": "spawn_allies", "side": "allies", "position": [22, 2], "units_max": 26},
            {"id": "spawn_axis", "side": "axis", "position": [22, 35], "units_max": 24},
            {"id": "spawn_axis_reinforce", "side": "axis", "position": [6, 34], "units_max": 10},
        ],
    )


# ============================================================
# Map 4: St. Elizabeth Hospital (圣伊丽莎白医院)
# ============================================================
def generate_arnhem_st_elizabeth():
    W, H = 38, 32
    rng = random.Random(2004)
    grid = make_grid(W, H, GRASS)

    # Base: residential area
    fill_rect(grid, 0, 0, W, H, OPEN)
    scatter_terrain(grid, 0, 0, W, H, GRASS, density=0.25, rng=rng)

    # Road network
    # Main north-south road (cols 18-19)
    add_road_v(grid, 18, 0, H, width=2)
    # East-west roads
    add_road_h(grid, 8, 0, W, width=1)
    add_road_h(grid, 16, 0, W, width=1)
    add_road_h(grid, 24, 0, W, width=1)

    # Hospital complex (center, cols 10-28, rows 8-22)
    # Main hospital building
    fill_rect(grid, 12, 10, 14, 10, BUILDING_ENTERABLE)
    # Hospital solid walls/structure
    fill_rect(grid, 12, 10, 14, 1, BUILDING_SOLID)  # North wall
    fill_rect(grid, 12, 19, 14, 1, BUILDING_SOLID)  # South wall
    fill_rect(grid, 12, 10, 1, 10, BUILDING_SOLID)  # West wall
    fill_rect(grid, 25, 10, 1, 10, BUILDING_SOLID)  # East wall

    # Hospital main entrance (break in south wall)
    fill_row(grid, 19, 18, 20, ROAD)

    # Hospital wing A (north extension)
    fill_rect(grid, 14, 8, 6, 2, BUILDING_ENTERABLE)
    fill_rect(grid, 14, 8, 6, 1, BUILDING_SOLID)

    # Hospital wing B (east extension)
    fill_rect(grid, 26, 12, 3, 6, BUILDING_ENTERABLE)
    fill_rect(grid, 28, 12, 1, 6, BUILDING_SOLID)

    # Hospital courtyard (open area inside complex)
    fill_rect(grid, 16, 12, 4, 4, OPEN)

    # Hospital garden/park (south of hospital)
    fill_rect(grid, 12, 21, 14, 4, GRASS)
    scatter_terrain(grid, 12, 21, 14, 4, WOODS, density=0.2, rng=rng)

    # Access road to hospital
    add_road_v(grid, 18, 19, 25, width=2)
    add_road_h(grid, 21, 12, 26, width=1)

    # Residential streets - northwest
    add_street_grid(grid, 1, 1, 10, 7, spacing=3, rng=rng)
    scatter_terrain(grid, 1, 1, 10, 7, BUILDING_ENTERABLE, density=0.35, rng=rng)
    scatter_terrain(grid, 1, 1, 10, 7, BUILDING_SOLID, density=0.1, rng=rng)

    # Residential streets - northeast
    add_street_grid(grid, 27, 1, 10, 7, spacing=3, rng=rng)
    scatter_terrain(grid, 27, 1, 10, 7, BUILDING_ENTERABLE, density=0.35, rng=rng)
    scatter_terrain(grid, 27, 1, 10, 7, BUILDING_SOLID, density=0.1, rng=rng)

    # Residential streets - southwest
    add_street_grid(grid, 1, 22, 10, 9, spacing=3, rng=rng)
    scatter_terrain(grid, 1, 22, 10, 9, BUILDING_ENTERABLE, density=0.35, rng=rng)
    scatter_terrain(grid, 1, 22, 10, 9, BUILDING_SOLID, density=0.1, rng=rng)

    # Residential streets - southeast
    add_street_grid(grid, 27, 22, 10, 9, spacing=3, rng=rng)
    scatter_terrain(grid, 27, 22, 10, 9, BUILDING_ENTERABLE, density=0.35, rng=rng)
    scatter_terrain(grid, 27, 22, 10, 9, BUILDING_SOLID, density=0.1, rng=rng)

    # Hedges around residential properties
    scatter_terrain(grid, 1, 1, 10, 7, HEDGE, density=0.1, rng=rng)
    scatter_terrain(grid, 27, 1, 10, 7, HEDGE, density=0.1, rng=rng)

    # Craters from artillery bombardment
    scatter_terrain(grid, 10, 8, 18, 14, CRATER, density=0.1, rng=rng)

    # Wall segments around hospital grounds
    add_wall_rect(grid, 10, 7, 20, 18)
    # Break walls for access
    fill_row(grid, 7, 18, 20, OPEN)
    fill_row(grid, 24, 18, 20, OPEN)
    fill_column(grid, 10, 15, 17, OPEN)
    fill_column(grid, 29, 15, 17, OPEN)

    return build_map(
        id_str="arnhem_st_elizabeth",
        name="St. Elizabeth Hospital — 圣伊丽莎白医院",
        width=W, height=H, grid=grid,
        metadata={
            "name": "St. Elizabeth Hospital",
            "description": "St. Elizabeth Hospital was a key strongpoint during the Arnhem fighting. Both sides fought bitterly for control of this large building complex which dominated the surrounding area.",
            "sector": "Arnhem",
            "historical_day": "1944-09-19",
            "historical_battle": "Battle of Arnhem - Hospital Sector",
        },
        victory_locations=[
            {"id": "vl_hospital_main", "name": "Hospital Main", "position": [19, 14], "value": 19, "type": "regular"},
            {"id": "vl_hospital_wing", "name": "Hospital Wing", "position": [27, 15], "value": 15, "type": "regular"},
            {"id": "vl_access_road", "name": "Access Road", "position": [19, 21], "value": 10, "type": "road"},
        ],
        deployment_zones={
            "allies": {"x": 3, "y": 25, "width": 32, "height": 6},
            "axis": {"x": 3, "y": 0, "width": 32, "height": 5},
        },
        objectives=[
            {"id": "obj_hospital_main", "name": "Hospital Main", "position": [19, 14], "radius": 5, "required": True, "owner": None},
            {"id": "obj_hospital_wing", "name": "Hospital Wing", "position": [27, 15], "radius": 3, "required": True, "owner": None},
            {"id": "obj_access_road", "name": "Access Road", "position": [19, 21], "radius": 3, "required": False, "owner": None},
        ],
        spawn_points=[
            {"id": "spawn_allies", "side": "allies", "position": [19, 29], "units_max": 24},
            {"id": "spawn_axis", "side": "axis", "position": [19, 2], "units_max": 22},
        ],
    )


# ============================================================
# Map 5: Eindhoven City (埃因霍温市区)
# ============================================================
def generate_eindhoven_city():
    W, H = 48, 40
    rng = random.Random(2005)
    grid = make_grid(W, H, GRASS)

    # Base: open/suburban
    fill_rect(grid, 0, 0, W, H, OPEN)
    scatter_terrain(grid, 0, 0, W, H, GRASS, density=0.25, rng=rng)

    # Canal through east side (cols 40-43)
    add_river_v(grid, 40, 0, H, width=4)

    # Canal bridge (cols 40-43, rows 19-22)
    add_bridge_v(grid, 40, 18, 23, width=4)

    # Hell's Highway - main road running north-south (cols 22-24)
    add_road_v(grid, 22, 0, H, width=3)

    # Cross roads
    add_road_h(grid, 10, 5, 42, width=2)
    add_road_h(grid, 20, 5, 42, width=2)
    add_road_h(grid, 30, 5, 42, width=2)

    # Dense urban center (cols 8-38, rows 8-32)
    add_street_grid(grid, 8, 8, 30, 24, spacing=4, rng=rng)
    scatter_terrain(grid, 8, 8, 30, 24, BUILDING_ENTERABLE, density=0.4, rng=rng)
    scatter_terrain(grid, 8, 8, 30, 24, BUILDING_SOLID, density=0.15, rng=rng)

    # City center - large buildings (market square area)
    fill_rect(grid, 18, 16, 8, 8, BUILDING_ENTERABLE)
    fill_rect(grid, 19, 17, 6, 6, BUILDING_SOLID)
    # City hall (large solid building)
    fill_rect(grid, 20, 18, 4, 4, BUILDING_SOLID)
    fill_rect(grid, 21, 19, 2, 2, BUILDING_ENTERABLE)

    # Industrial area in north (cols 5-20, rows 2-8)
    fill_rect(grid, 5, 2, 15, 6, BUILDING_ENTERABLE)
    fill_rect(grid, 6, 3, 5, 4, BUILDING_SOLID)  # Factory
    fill_rect(grid, 14, 3, 5, 4, BUILDING_SOLID)  # Warehouse
    add_road_h(grid, 5, 5, 20, width=1)  # Industrial access road

    # Residential suburbs - southwest
    add_street_grid(grid, 1, 25, 8, 12, spacing=3, rng=rng)
    scatter_terrain(grid, 1, 25, 8, 12, BUILDING_ENTERABLE, density=0.3, rng=rng)
    scatter_terrain(grid, 1, 25, 8, 12, BUILDING_SOLID, density=0.08, rng=rng)

    # Residential suburbs - southeast (between urban and canal)
    add_street_grid(grid, 35, 25, 5, 12, spacing=3, rng=rng)
    scatter_terrain(grid, 35, 25, 5, 12, BUILDING_ENTERABLE, density=0.3, rng=rng)
    scatter_terrain(grid, 35, 25, 5, 12, BUILDING_SOLID, density=0.08, rng=rng)

    # Residential suburbs - northwest
    add_street_grid(grid, 1, 2, 5, 6, spacing=3, rng=rng)
    scatter_terrain(grid, 1, 2, 5, 6, BUILDING_ENTERABLE, density=0.3, rng=rng)

    # Hedges in suburban areas
    scatter_terrain(grid, 0, 33, 40, 7, HEDGE, density=0.12, rng=rng)
    scatter_terrain(grid, 0, 0, 5, 8, HEDGE, density=0.12, rng=rng)

    # Craters from German counterattack artillery
    scatter_terrain(grid, 8, 8, 30, 24, CRATER, density=0.08, rng=rng)

    # Rubble near city center
    scatter_terrain(grid, 16, 14, 12, 12, CRATER, density=0.12, rng=rng)

    # Road to canal bridge
    add_road_h(grid, 20, 38, 44, width=2)

    return build_map(
        id_str="eindhoven_city",
        name="Eindhoven City — 埃因霍温市区",
        width=W, height=H, grid=grid,
        metadata={
            "name": "Eindhoven City",
            "description": "Eindhoven was liberated by the 101st Airborne on Day 1 of Market Garden, but the city became a crucial supply corridor for XXX Corps. German counterattacks targeted the city to sever the vital supply route.",
            "sector": "Eindhoven",
            "historical_day": "1944-09-18",
            "historical_battle": "Defense of Eindhoven - Hell's Highway",
        },
        victory_locations=[
            {"id": "vl_city_center", "name": "City Center", "position": [22, 20], "value": 15, "type": "regular"},
            {"id": "vl_hells_highway", "name": "Hell's Highway", "position": [23, 10], "value": 30, "type": "road"},
            {"id": "vl_canal_bridge", "name": "Canal Bridge", "position": [42, 20], "value": 30, "type": "bridge"},
        ],
        deployment_zones={
            "allies": {"x": 5, "y": 33, "width": 30, "height": 6},
            "axis": {"x": 5, "y": 0, "width": 30, "height": 5},
        },
        objectives=[
            {"id": "obj_city_center", "name": "City Center", "position": [22, 20], "radius": 5, "required": True, "owner": None},
            {"id": "obj_hells_highway", "name": "Hell's Highway", "position": [23, 10], "radius": 4, "required": True, "owner": None},
            {"id": "obj_canal_bridge", "name": "Canal Bridge", "position": [42, 20], "radius": 3, "required": True, "owner": None},
        ],
        spawn_points=[
            {"id": "spawn_allies", "side": "allies", "position": [23, 37], "units_max": 30},
            {"id": "spawn_axis", "side": "axis", "position": [23, 2], "units_max": 26},
            {"id": "spawn_axis_reinforce", "side": "axis", "position": [42, 2], "units_max": 12},
        ],
    )


# ============================================================
# Main: Generate all 5 maps
# ============================================================
def main():
    output_dir = Path("/Users/lin/trae_projects/PyCC2/data/maps")
    output_dir.mkdir(parents=True, exist_ok=True)

    generators = [
        ("arnhem_zoo.json", generate_arnhem_zoo),
        ("arnhem_koepel.json", generate_arnhem_koepel),
        ("arnhem_best.json", generate_arnhem_best),
        ("arnhem_st_elizabeth.json", generate_arnhem_st_elizabeth),
        ("eindhoven_city.json", generate_eindhoven_city),
    ]

    for filename, gen_func in generators:
        map_data = gen_func()
        filepath = output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(map_data, f, indent=2, ensure_ascii=False)
        print(f"Generated: {filepath} ({map_data['width']}x{map_data['height']})")

    print(f"\nAll {len(generators)} maps generated successfully!")


if __name__ == "__main__":
    main()
