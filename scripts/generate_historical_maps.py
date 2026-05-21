#!/usr/bin/env python3
"""Generate 6 historically-accurate CC2 map JSON files for Operation Market Garden."""

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
# Map 1: Arnhem Tree Road (林荫道)
# ============================================================
def generate_arnhem_tree_road():
    W, H = 48, 40
    rng = random.Random(1944)
    grid = make_grid(W, H, GRASS)

    # River on east edge (4 columns: cols 44-47)
    add_river_v(grid, 44, 0, H, width=4)

    # Main road running north-south through center (col 22-23)
    add_road_v(grid, 22, 0, H, width=2)

    # Cross roads
    add_road_h(grid, 10, 10, 35, width=1)
    add_road_h(grid, 20, 8, 38, width=1)
    add_road_h(grid, 30, 10, 35, width=1)

    # Dense trees on both sides of road
    # West side forest (cols 6-20)
    scatter_terrain(grid, 6, 0, 15, H, WOODS, density=0.55, rng=rng)
    # East side forest (cols 26-42)
    scatter_terrain(grid, 26, 0, 16, H, WOODS, density=0.55, rng=rng)

    # Hedges along road edges
    fill_column(grid, 21, 0, H, HEDGE)
    fill_column(grid, 24, 0, H, HEDGE)

    # Small village at north end (rows 2-8, cols 18-28)
    add_building_cluster(grid, 20, 3, size=3, rng=rng)
    add_building_cluster(grid, 26, 4, size=2, rng=rng)
    add_street_grid(grid, 18, 1, 12, 8, spacing=3, rng=rng)

    # Open fields at south
    fill_rect(grid, 0, 32, 22, 8, OPEN)

    # Some rough terrain near river bank
    scatter_terrain(grid, 42, 5, 2, 30, ROUGH, density=0.4, rng=rng)

    return build_map(
        id_str="arnhem_tree_road",
        name="Arnhem Tree Road — 林荫道",
        width=W, height=H, grid=grid,
        metadata={
            "name": "Arnhem Tree Road",
            "description": "Tree-lined road approach to Arnhem from the south. The Rhine river flanks the east side as British paratroopers advance along the shaded avenue toward the city.",
            "sector": "Arnhem",
            "historical_day": "1944-09-18",
            "historical_battle": "Battle of Arnhem - Southern Approach",
        },
        victory_locations=[
            {"id": "vl_junction", "name": "Tree Road Junction", "position": [23, 20], "value": 3, "type": "capture"},
            {"id": "vl_south_approach", "name": "South Approach", "position": [22, 35], "value": 2, "type": "capture"},
            {"id": "vl_north_village", "name": "North Village", "position": [23, 4], "value": 3, "type": "capture"},
        ],
        deployment_zones={
            "allies": {"x": 5, "y": 33, "width": 18, "height": 6},
            "axis": {"x": 15, "y": 0, "width": 20, "height": 5},
        },
        objectives=[
            {"id": "obj_junction", "name": "Tree Road Junction", "position": [23, 20], "radius": 4, "required": True, "owner": None},
            {"id": "obj_south", "name": "South Approach", "position": [22, 35], "radius": 3, "required": False, "owner": None},
            {"id": "obj_village", "name": "North Village", "position": [23, 4], "radius": 4, "required": True, "owner": None},
        ],
        spawn_points=[
            {"id": "spawn_allies", "side": "allies", "position": [12, 36], "units_max": 25},
            {"id": "spawn_axis", "side": "axis", "position": [22, 2], "units_max": 20},
        ],
    )


# ============================================================
# Map 2: Arnhem West Approach (西部通道)
# ============================================================
def generate_arnhem_west_approach():
    W, H = 50, 42
    rng = random.Random(1945)
    grid = make_grid(W, H, GRASS)

    # Open fields in west (cols 0-15)
    fill_rect(grid, 0, 0, 16, H, OPEN)
    scatter_terrain(grid, 0, 0, 16, H, GRASS, density=0.3, rng=rng)

    # Road network
    # Main east-west road
    add_road_h(grid, 20, 0, W, width=2)
    # North-south road
    add_road_v(grid, 25, 0, H, width=2)
    # Secondary roads
    add_road_h(grid, 10, 15, 45, width=1)
    add_road_h(grid, 30, 15, 45, width=1)
    add_road_v(grid, 35, 5, 38, width=1)
    add_road_v(grid, 15, 15, 35, width=1)

    # Train station complex (center-west, cols 18-28, rows 17-24)
    fill_rect(grid, 18, 17, 10, 7, BUILDING_ENTERABLE)
    fill_rect(grid, 20, 18, 6, 2, BUILDING_SOLID)  # Main station building
    fill_rect(grid, 19, 22, 8, 1, ROAD)  # Platform area
    # Rail tracks (represented as road)
    add_road_h(grid, 21, 10, 45, width=1)

    # Hotel (large building, cols 30-34, rows 15-19)
    fill_rect(grid, 30, 15, 5, 4, BUILDING_SOLID)
    fill_rect(grid, 31, 16, 3, 2, BUILDING_ENTERABLE)

    # Dense urban area in east half (cols 30-49, rows 5-40)
    add_street_grid(grid, 30, 5, 20, 35, spacing=4, rng=rng)
    scatter_terrain(grid, 30, 5, 20, 35, BUILDING_ENTERABLE, density=0.45, rng=rng)
    scatter_terrain(grid, 30, 5, 20, 35, BUILDING_SOLID, density=0.15, rng=rng)

    # West Gate area (cols 15-20, rows 18-22)
    add_building_cluster(grid, 17, 20, size=2, rng=rng)

    # Some hedges in the open fields
    scatter_terrain(grid, 2, 5, 12, 15, HEDGE, density=0.1, rng=rng)
    scatter_terrain(grid, 2, 25, 12, 15, HEDGE, density=0.1, rng=rng)

    # Rubble near station
    scatter_terrain(grid, 18, 17, 10, 7, CRATER, density=0.15, rng=rng)

    return build_map(
        id_str="arnhem_west_approach",
        name="Arnhem West Approach — 西部通道",
        width=W, height=H, grid=grid,
        metadata={
            "name": "Arnhem West Approach",
            "description": "Western approach to Arnhem through the train station district. House-to-house fighting rages as British paratroopers push toward the city center past the railway hotel.",
            "sector": "Arnhem",
            "historical_day": "1944-09-19",
            "historical_battle": "Battle of Arnhem - Western Sector",
        },
        victory_locations=[
            {"id": "vl_train_station", "name": "Train Station", "position": [23, 20], "value": 3, "type": "capture"},
            {"id": "vl_hotel", "name": "Hotel", "position": [32, 17], "value": 3, "type": "capture"},
            {"id": "vl_west_gate", "name": "West Gate", "position": [17, 20], "value": 2, "type": "capture"},
        ],
        deployment_zones={
            "allies": {"x": 0, "y": 15, "width": 10, "height": 12},
            "axis": {"x": 38, "y": 5, "width": 10, "height": 10},
        },
        objectives=[
            {"id": "obj_station", "name": "Train Station", "position": [23, 20], "radius": 5, "required": True, "owner": None},
            {"id": "obj_hotel", "name": "Hotel", "position": [32, 17], "radius": 3, "required": True, "owner": None},
            {"id": "obj_west_gate", "name": "West Gate", "position": [17, 20], "radius": 3, "required": False, "owner": None},
        ],
        spawn_points=[
            {"id": "spawn_allies", "side": "allies", "position": [3, 20], "units_max": 30},
            {"id": "spawn_axis", "side": "axis", "position": [45, 8], "units_max": 28},
            {"id": "spawn_axis_reinforce", "side": "axis", "position": [40, 35], "units_max": 12},
        ],
    )


# ============================================================
# Map 3: Oosterbeek North (奥斯特贝克北部)
# ============================================================
def generate_oosterbeek_north():
    W, H = 40, 35
    rng = random.Random(1946)
    grid = make_grid(W, H, GRASS)

    # River running east-west across north (rows 4-7)
    add_river_h(grid, 4, 0, W, width=4)

    # Rail bridge (cols 10-14, crossing river at rows 4-7)
    add_bridge_h(grid, 4, 10, 15, width=4)

    # Road bridge (cols 26-30, crossing river at rows 4-7)
    add_bridge_h(grid, 4, 26, 31, width=4)

    # Rail embankment approaching bridges from north
    fill_rect(grid, 10, 0, 5, 4, ROUGH)  # Raised embankment
    add_road_h(grid, 1, 10, 15, width=1)  # Rail line on embankment

    # Road approaching road bridge from north
    add_road_v(grid, 28, 0, 4, width=2)

    # Roads from bridges going south
    add_road_v(grid, 12, 8, H, width=1)  # From rail bridge
    add_road_v(grid, 28, 8, H, width=2)  # From road bridge

    # Cross road
    add_road_h(grid, 18, 5, 38, width=1)
    add_road_h(grid, 26, 5, 38, width=1)

    # Residential area in south (rows 12-33, cols 5-38)
    add_street_grid(grid, 5, 12, 33, 22, spacing=4, rng=rng)
    scatter_terrain(grid, 5, 12, 33, 22, BUILDING_ENTERABLE, density=0.35, rng=rng)
    scatter_terrain(grid, 5, 12, 33, 22, BUILDING_SOLID, density=0.1, rng=rng)

    # Open ground between bridges (rows 8-11)
    fill_rect(grid, 15, 8, 11, 4, OPEN)

    # Junction area where roads meet
    fill_rect(grid, 11, 16, 4, 4, OPEN)

    # Hedges in residential area
    scatter_terrain(grid, 5, 12, 33, 22, HEDGE, density=0.08, rng=rng)

    # Some woods on the edges
    scatter_terrain(grid, 0, 10, 5, 25, WOODS, density=0.4, rng=rng)
    scatter_terrain(grid, 35, 10, 5, 25, WOODS, density=0.4, rng=rng)

    return build_map(
        id_str="oosterbeek_north",
        name="Oosterbeek North — 奥斯特贝克北部",
        width=W, height=H, grid=grid,
        metadata={
            "name": "Oosterbeek North",
            "description": "Rail and road bridge junction north of the Oosterbeek perimeter. British paratroopers must hold both crossings against German armored counterattacks.",
            "sector": "Oosterbeek",
            "historical_day": "1944-09-20",
            "historical_battle": "Battle of Oosterbeek Perimeter - North",
        },
        victory_locations=[
            {"id": "vl_rail_bridge", "name": "Rail Bridge", "position": [12, 5], "value": 3, "type": "capture"},
            {"id": "vl_road_bridge", "name": "Road Bridge", "position": [28, 5], "value": 3, "type": "capture"},
            {"id": "vl_junction", "name": "Junction", "position": [20, 18], "value": 2, "type": "capture"},
        ],
        deployment_zones={
            "allies": {"x": 8, "y": 25, "width": 24, "height": 8},
            "axis": {"x": 5, "y": 0, "width": 30, "height": 4},
        },
        objectives=[
            {"id": "obj_rail_bridge", "name": "Rail Bridge", "position": [12, 5], "radius": 3, "required": True, "owner": None},
            {"id": "obj_road_bridge", "name": "Road Bridge", "position": [28, 5], "radius": 3, "required": True, "owner": None},
            {"id": "obj_junction", "name": "Junction", "position": [20, 18], "radius": 4, "required": False, "owner": None},
        ],
        spawn_points=[
            {"id": "spawn_allies", "side": "allies", "position": [20, 30], "units_max": 22},
            {"id": "spawn_axis", "side": "axis", "position": [12, 1], "units_max": 18},
            {"id": "spawn_axis_reinforce", "side": "axis", "position": [28, 1], "units_max": 10},
        ],
    )


# ============================================================
# Map 4: Oosterbeek Rail Bridge (奥斯特贝克铁路桥)
# ============================================================
def generate_oosterbeek_rail_bridge():
    W, H = 36, 30
    rng = random.Random(1947)
    grid = make_grid(W, H, GRASS)

    # River running east-west across center (rows 12-15)
    add_river_h(grid, 12, 0, W, width=4)

    # Rail bridge (cols 14-18, crossing river)
    add_bridge_h(grid, 12, 14, 19, width=4)

    # Rail embankment on south bank (elevated rough terrain)
    fill_rect(grid, 13, 16, 10, 3, ROUGH)
    add_road_h(grid, 17, 13, 24, width=1)  # Rail line

    # Rail embankment on north bank
    fill_rect(grid, 13, 8, 10, 4, ROUGH)
    add_road_h(grid, 10, 13, 24, width=1)

    # Road on south side
    add_road_h(grid, 22, 0, 36, width=1)
    add_road_h(grid, 26, 0, 36, width=1)

    # Suburban area on south bank (rows 20-29, cols 3-33)
    add_street_grid(grid, 3, 20, 30, 9, spacing=4, rng=rng)
    scatter_terrain(grid, 3, 20, 30, 9, BUILDING_ENTERABLE, density=0.3, rng=rng)
    scatter_terrain(grid, 3, 20, 30, 9, BUILDING_SOLID, density=0.08, rng=rng)

    # Open field on north bank (rows 0-11)
    fill_rect(grid, 0, 0, 36, 12, OPEN)
    scatter_terrain(grid, 0, 0, 36, 12, GRASS, density=0.3, rng=rng)

    # Some hedges on north bank
    scatter_terrain(grid, 5, 2, 26, 8, HEDGE, density=0.12, rng=rng)

    # Woods on flanks
    scatter_terrain(grid, 0, 0, 5, 30, WOODS, density=0.5, rng=rng)
    scatter_terrain(grid, 31, 0, 5, 30, WOODS, density=0.5, rng=rng)

    # Approach road to bridge on south side
    add_road_v(grid, 16, 16, 30, width=2)

    return build_map(
        id_str="oosterbeek_rail_bridge",
        name="Oosterbeek Rail Bridge — 奥斯特贝克铁路桥",
        width=W, height=H, grid=grid,
        metadata={
            "name": "Oosterbeek Rail Bridge",
            "description": "Railway bridge at Oosterbeek, a vital crossing point. The elevated rail embankment provides commanding positions while the suburban south bank offers cover for the defenders.",
            "sector": "Oosterbeek",
            "historical_day": "1944-09-21",
            "historical_battle": "Battle of Oosterbeek Perimeter - Rail Bridge",
        },
        victory_locations=[
            {"id": "vl_rail_bridge", "name": "Rail Bridge", "position": [16, 13], "value": 3, "type": "capture"},
            {"id": "vl_south_bank", "name": "South Bank", "position": [16, 24], "value": 2, "type": "capture"},
            {"id": "vl_embankment", "name": "Embankment", "position": [16, 17], "value": 2, "type": "capture"},
        ],
        deployment_zones={
            "allies": {"x": 8, "y": 0, "width": 20, "height": 5},
            "axis": {"x": 5, "y": 24, "width": 26, "height": 5},
        },
        objectives=[
            {"id": "obj_bridge", "name": "Rail Bridge", "position": [16, 13], "radius": 3, "required": True, "owner": None},
            {"id": "obj_south_bank", "name": "South Bank", "position": [16, 24], "radius": 4, "required": True, "owner": None},
            {"id": "obj_embankment", "name": "Embankment", "position": [16, 17], "radius": 3, "required": False, "owner": None},
        ],
        spawn_points=[
            {"id": "spawn_allies", "side": "allies", "position": [16, 2], "units_max": 20},
            {"id": "spawn_axis", "side": "axis", "position": [18, 27], "units_max": 18},
        ],
    )


# ============================================================
# Map 5: Son Town (松镇)
# ============================================================
def generate_son_town():
    W, H = 40, 35
    rng = random.Random(1948)
    grid = make_grid(W, H, GRASS)

    # Open fields surrounding town
    fill_rect(grid, 0, 0, W, H, OPEN)
    scatter_terrain(grid, 0, 0, W, H, GRASS, density=0.3, rng=rng)

    # Canal on south edge (rows 30-33)
    add_river_h(grid, 30, 0, W, width=3)
    # Shallow edges
    fill_row(grid, 29, 0, W, SHALLOW)

    # Bridge over canal (cols 18-21)
    add_bridge_h(grid, 30, 18, 22, width=3)

    # Town center with dense buildings (cols 10-30, rows 8-26)
    add_street_grid(grid, 10, 8, 20, 18, spacing=3, rng=rng)
    scatter_terrain(grid, 10, 8, 20, 18, BUILDING_ENTERABLE, density=0.4, rng=rng)
    scatter_terrain(grid, 10, 8, 20, 18, BUILDING_SOLID, density=0.12, rng=rng)

    # Market square (open area in town center)
    fill_rect(grid, 18, 15, 5, 4, OPEN)

    # Warehouse complex in north (cols 12-20, rows 3-8)
    fill_rect(grid, 12, 3, 8, 5, BUILDING_ENTERABLE)
    fill_rect(grid, 14, 4, 4, 3, BUILDING_SOLID)  # Main warehouse building
    add_road_h(grid, 5, 10, 25, width=1)  # Access road

    # School in east (cols 28-34, rows 10-16)
    fill_rect(grid, 28, 10, 6, 6, BUILDING_ENTERABLE)
    fill_rect(grid, 29, 11, 4, 4, BUILDING_SOLID)
    add_road_v(grid, 32, 8, 18, width=1)

    # Mayor's residence (cols 14-18, rows 12-15)
    fill_rect(grid, 14, 12, 4, 3, BUILDING_SOLID)
    fill_rect(grid, 15, 13, 2, 1, BUILDING_ENTERABLE)

    # Main roads
    add_road_h(grid, 16, 5, 38, width=1)  # East-west main road
    add_road_v(grid, 20, 0, 30, width=1)  # North-south main road

    # Hedges around fields
    scatter_terrain(grid, 0, 0, 10, 30, HEDGE, density=0.08, rng=rng)
    scatter_terrain(grid, 30, 0, 10, 30, HEDGE, density=0.08, rng=rng)

    # Some woods on the edges
    scatter_terrain(grid, 0, 0, 6, 8, WOODS, density=0.5, rng=rng)
    scatter_terrain(grid, 34, 0, 6, 8, WOODS, density=0.5, rng=rng)

    return build_map(
        id_str="son_town",
        name="Son Town — 松镇",
        width=W, height=H, grid=grid,
        metadata={
            "name": "Son Town",
            "description": "Son town center during the 101st Airborne's advance. The warehouse, school, and mayor's residence are key objectives as American paratroopers fight through the streets.",
            "sector": "Son",
            "historical_day": "1944-09-17",
            "historical_battle": "101st Airborne - Son Sector",
        },
        victory_locations=[
            {"id": "vl_warehouse", "name": "Warehouse", "position": [16, 5], "value": 3, "type": "capture"},
            {"id": "vl_school", "name": "School", "position": [31, 13], "value": 2, "type": "capture"},
            {"id": "vl_town_square", "name": "Town Square", "position": [20, 17], "value": 3, "type": "capture"},
        ],
        deployment_zones={
            "allies": {"x": 2, "y": 0, "width": 8, "height": 8},
            "axis": {"x": 25, "y": 20, "width": 12, "height": 8},
        },
        objectives=[
            {"id": "obj_warehouse", "name": "Warehouse", "position": [16, 5], "radius": 4, "required": True, "owner": None},
            {"id": "obj_school", "name": "School", "position": [31, 13], "radius": 3, "required": True, "owner": None},
            {"id": "obj_square", "name": "Town Square", "position": [20, 17], "radius": 3, "required": True, "owner": None},
        ],
        spawn_points=[
            {"id": "spawn_allies", "side": "allies", "position": [5, 3], "units_max": 24},
            {"id": "spawn_axis", "side": "axis", "position": [30, 25], "units_max": 20},
        ],
    )


# ============================================================
# Map 6: Schijndel Road (斯欣德尔公路)
# ============================================================
def generate_schijndel_road():
    W, H = 44, 38
    rng = random.Random(1949)
    grid = make_grid(W, H, GRASS)

    # Open farmland base
    fill_rect(grid, 0, 0, W, H, OPEN)
    scatter_terrain(grid, 0, 0, W, H, GRASS, density=0.25, rng=rng)

    # Main road running north-south (cols 18-19)
    add_road_v(grid, 18, 0, H, width=2)

    # Canal/river running east-west in center (rows 16-19)
    add_river_h(grid, 16, 0, W, width=4)

    # Bridge over canal (cols 17-20)
    add_bridge_h(grid, 16, 17, 21, width=4)

    # Road approaching bridge from north and south
    add_road_v(grid, 18, 0, 16, width=2)
    add_road_v(grid, 18, 20, H, width=2)

    # Village on east side (cols 22-38, rows 10-28)
    add_street_grid(grid, 22, 10, 16, 18, spacing=4, rng=rng)
    scatter_terrain(grid, 22, 10, 16, 18, BUILDING_ENTERABLE, density=0.3, rng=rng)
    scatter_terrain(grid, 22, 10, 16, 18, BUILDING_SOLID, density=0.08, rng=rng)

    # Village crossroads
    add_road_h(grid, 18, 18, 38, width=1)
    add_road_v(grid, 30, 10, 28, width=1)

    # Defensive positions (bunkers/trenches) - represented as BUILDING_SOLID and ROUGH
    # Bunker near bridge on north bank
    fill_rect(grid, 14, 14, 2, 2, BUILDING_SOLID)
    fill_rect(grid, 22, 14, 2, 2, BUILDING_SOLID)

    # Trenches on south bank
    fill_rect(grid, 10, 20, 8, 1, ROUGH)
    fill_rect(grid, 10, 22, 8, 1, ROUGH)
    fill_rect(grid, 24, 20, 8, 1, ROUGH)
    fill_rect(grid, 24, 22, 8, 1, ROUGH)

    # Canal lock on west side (cols 4-8)
    fill_rect(grid, 4, 16, 4, 4, BUILDING_SOLID)
    fill_rect(grid, 5, 17, 2, 2, BUILDING_ENTERABLE)

    # Hedges dividing farmland
    for y in range(2, 16, 4):
        fill_row(grid, y, 0, 18, HEDGE)
    for y in range(20, 36, 4):
        fill_row(grid, y, 0, 18, HEDGE)

    # Some woods
    scatter_terrain(grid, 0, 0, 8, 10, WOODS, density=0.5, rng=rng)
    scatter_terrain(grid, 36, 28, 8, 10, WOODS, density=0.5, rng=rng)
    scatter_terrain(grid, 0, 28, 8, 10, WOODS, density=0.4, rng=rng)

    # Farmland patches
    scatter_terrain(grid, 0, 2, 18, 14, GRASS, density=0.4, rng=rng)
    scatter_terrain(grid, 0, 20, 18, 16, GRASS, density=0.4, rng=rng)

    return build_map(
        id_str="schijndel_road",
        name="Schijndel Road — 斯欣德尔公路",
        width=W, height=H, grid=grid,
        metadata={
            "name": "Schijndel Road",
            "description": "Road and bridge at Schijndel, a key defensive position. German forces have fortified the canal crossing with bunkers and trenches while the village provides urban cover.",
            "sector": "Schijndel",
            "historical_day": "1944-09-22",
            "historical_battle": "Defense of Schijndel - Canal Line",
        },
        victory_locations=[
            {"id": "vl_bridge", "name": "Bridge", "position": [19, 18], "value": 3, "type": "capture"},
            {"id": "vl_crossroads", "name": "Village Crossroads", "position": [30, 18], "value": 2, "type": "capture"},
            {"id": "vl_canal_lock", "name": "Canal Lock", "position": [6, 18], "value": 2, "type": "capture"},
        ],
        deployment_zones={
            "allies": {"x": 8, "y": 0, "width": 12, "height": 6},
            "axis": {"x": 22, "y": 30, "width": 16, "height": 6},
        },
        objectives=[
            {"id": "obj_bridge", "name": "Bridge", "position": [19, 18], "radius": 3, "required": True, "owner": None},
            {"id": "obj_crossroads", "name": "Village Crossroads", "position": [30, 18], "radius": 4, "required": True, "owner": None},
            {"id": "obj_lock", "name": "Canal Lock", "position": [6, 18], "radius": 3, "required": False, "owner": None},
        ],
        spawn_points=[
            {"id": "spawn_allies", "side": "allies", "position": [14, 2], "units_max": 24},
            {"id": "spawn_axis", "side": "axis", "position": [30, 34], "units_max": 22},
            {"id": "spawn_axis_defense", "side": "axis", "position": [18, 22], "units_max": 8},
        ],
    )


# ============================================================
# Main: Generate all 6 maps
# ============================================================
def main():
    output_dir = Path("/Users/lin/trae_projects/PyCC2/data/maps")
    output_dir.mkdir(parents=True, exist_ok=True)

    generators = [
        ("arnhem_tree_road.json", generate_arnhem_tree_road),
        ("arnhem_west_approach.json", generate_arnhem_west_approach),
        ("oosterbeek_north.json", generate_oosterbeek_north),
        ("oosterbeek_rail_bridge.json", generate_oosterbeek_rail_bridge),
        ("son_town.json", generate_son_town),
        ("schijndel_road.json", generate_schijndel_road),
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
