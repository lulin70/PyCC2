#!/usr/bin/env python3
"""
Generate Market Garden campaign map files.

Creates 20 map JSON files for Operation Market Garden:
Operation Eindhoven (101st Airborne) - 5 maps:
  1. son_bridge.json          - Bridge over Wilhelmina Canal
  2. best_village.json        - Village defense
  3. veghel_crossroads.json   - Road junction battle
  4. zonsche_forest.json      - Forest approach
  5. eindhoven_suburbs.json   - Urban fighting

Operation Nijmegen (82nd Airborne) - 5 maps:
  6. nijmegen_crossing.json   - Waal River crossing
  7. grave_bridge.json        - Bridge capture
  8. groesbeek_heights.json   - Elevated position defense
  9. mook_woods.json          - Forest patrol
 10. nijmegen_streets.json    - Street fighting

Operation Arnhem (British 1st Airborne) - 5 maps:
 11. arnhem_bridge.json       - Rhine River bridge
 12. oosterbeek_perimeter.json - Defensive perimeter
 13. arnhem_streets.json      - Urban assault
 14. hartenstein_hotel.json   - HQ defense
 15. rhine_crossing.json      - River evacuation

Operation Hell's Highway (XXX Corps) - 5 maps:
 16. hell_highway.json        - Road corridor
 17. vught_bridge.json        - Canal crossing
 18. s_hertogenbosch.json     - City assault
 19. overloon_battlefield.json - Open terrain tank battle
 20. meijel_woods.json        - Forest ambush

Each map is 20x20 tiles using the JSON format compatible with GameMap.from_json.
Terrain names match _TERRAIN_NAME_MAP: open, road, grass, woods, building_enterable,
building_solid, water, hedge, wall, rough, shallow, bridge.
"""

import json
import random
from pathlib import Path

MAP_SIZE = 20

# Valid terrain names matching GameMap._TERRAIN_NAME_MAP
TERRAIN_TYPES = [
    "open",
    "road",
    "grass",
    "woods",
    "building_enterable",
    "building_solid",
    "water",
    "hedge",
    "wall",
    "rough",
    "shallow",
    "bridge",
]


def _make_map(
    name: str,
    tiles: list[list[str]],
    objectives: list[dict] | None = None,
    spawn_points: list[dict] | None = None,
) -> dict:
    """Build a map dict in the same format as GameMap.from_json expects."""
    result = {"name": name, "width": MAP_SIZE, "height": MAP_SIZE, "tiles": tiles}
    if objectives:
        result["objectives"] = objectives
    if spawn_points:
        result["spawn_points"] = spawn_points
    return result


def _fill(terrain: str) -> list[list[str]]:
    """Create a 20x20 grid filled with one terrain type."""
    return [[terrain] * MAP_SIZE for _ in range(MAP_SIZE)]


def _horizontal_band(
    tiles: list[list[str]], row: int, terrain: str, col_start: int = 0, col_end: int = MAP_SIZE
) -> None:
    """Fill a horizontal band on one row."""
    for c in range(col_start, min(col_end, MAP_SIZE)):
        tiles[row][c] = terrain


def _vertical_band(
    tiles: list[list[str]], col: int, terrain: str, row_start: int = 0, row_end: int = MAP_SIZE
) -> None:
    """Fill a vertical band on one column."""
    for r in range(row_start, min(row_end, MAP_SIZE)):
        tiles[r][col] = terrain


def _scatter(
    tiles: list[list[str]],
    terrain: str,
    count: int,
    rng: random.Random,
    region: tuple[int, int, int, int] | None = None,
) -> None:
    """Scatter terrain patches randomly within an optional region (x, y, w, h)."""
    rx, ry, rw, rh = region or (0, 0, MAP_SIZE, MAP_SIZE)
    for _ in range(count):
        r = ry + rng.randint(0, rh - 1)
        c = rx + rng.randint(0, rw - 1)
        if 0 <= r < MAP_SIZE and 0 <= c < MAP_SIZE:
            tiles[r][c] = terrain


def _add_default_spawn_points() -> list[dict]:
    """Return default spawn points for a 20x20 map."""
    return [
        {"id": "allied_start", "side": "friendly", "position": [3, 10], "units_max": 9},
        {"id": "axis_start", "side": "enemy", "position": [16, 10], "units_max": 9},
    ]


# ======================================================================
# Operation Eindhoven (101st Airborne) - 5 maps
# ======================================================================


def generate_son_bridge() -> dict:
    """Son Bridge - Bridge over Wilhelmina Canal (101st Airborne sector)."""
    tiles = _fill("grass")
    rng = random.Random(101)

    # Wilhelmina Canal - horizontal water band rows 9-10
    for r in (9, 10):
        _horizontal_band(tiles, r, "water")

    # Bridge crossing at columns 9-10
    for r in (9, 10):
        for c in (9, 10):
            tiles[r][c] = "bridge"

    # Road approaching bridge from north
    for r in range(0, 9):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    # Road continuing south from bridge
    for r in range(11, MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    # Buildings on north bank
    for r, c in [(5, 5), (5, 6), (6, 5), (6, 6), (4, 13), (4, 14), (5, 13), (5, 14)]:
        tiles[r][c] = "building_enterable"

    # Buildings on south bank
    for r, c in [(13, 5), (13, 6), (14, 5), (14, 6), (13, 13), (13, 14), (14, 13), (14, 14)]:
        tiles[r][c] = "building_enterable"

    # Hedges along fields
    _scatter(tiles, "hedge", 12, rng, region=(0, 0, 9, 9))
    _scatter(tiles, "hedge", 12, rng, region=(11, 0, 9, 9))
    _scatter(tiles, "hedge", 12, rng, region=(0, 11, 9, 9))
    _scatter(tiles, "hedge", 12, rng, region=(11, 11, 9, 9))

    # Rough patches
    _scatter(tiles, "rough", 8, rng)

    return _make_map(
        "Son Bridge - Wilhelmina Canal",
        tiles,
        objectives=[
            {"id": "bridge", "name": "Son Bridge", "position": [9, 9], "type": "capture"},
            {"id": "north_bank", "name": "North Bank", "position": [5, 5], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_north", "side": "friendly", "position": [9, 2], "units_max": 9},
            {"id": "axis_south", "side": "enemy", "position": [10, 17], "units_max": 9},
        ],
    )


def generate_best_village() -> dict:
    """Best Village - Village defense (101st Airborne sector).

    Layout: Cluster of buildings surrounded by hedgerows, roads connecting buildings.
    """
    tiles = _fill("grass")
    rng = random.Random(102)

    # Main road through village
    for c in range(3, 17):
        tiles[10][c] = "road"
    for r in range(3, 17):
        tiles[r][10] = "road"

    # Village buildings cluster (8-15 buildings)
    buildings = [
        (7, 7),
        (7, 8),
        (8, 7),
        (8, 8),  # NW cluster
        (7, 12),
        (7, 13),
        (8, 12),  # NE cluster
        (12, 7),
        (12, 8),  # SW cluster
        (12, 12),
        (12, 13),
        (13, 12),
        (13, 13),  # SE cluster
    ]
    for r, c in buildings:
        tiles[r][c] = "building_enterable"

    # Church (solid building)
    tiles[10][10] = "building_solid"
    tiles[10][11] = "building_solid"

    # Hedgerows around fields
    _scatter(tiles, "hedge", 25, rng, region=(0, 0, 7, 7))
    _scatter(tiles, "hedge", 25, rng, region=(13, 0, 7, 7))
    _scatter(tiles, "hedge", 25, rng, region=(0, 13, 7, 7))
    _scatter(tiles, "hedge", 25, rng, region=(13, 13, 7, 7))

    # Woods patches on edges
    _scatter(tiles, "woods", 8, rng, region=(0, 0, 3, MAP_SIZE))
    _scatter(tiles, "woods", 8, rng, region=(17, 0, 3, MAP_SIZE))

    return _make_map(
        "Best Village - 101st Airborne Defense",
        tiles,
        objectives=[
            {
                "id": "village_center",
                "name": "Village Center",
                "position": [10, 10],
                "type": "defend",
            },
            {"id": "north_road", "name": "North Road", "position": [10, 3], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_village", "side": "friendly", "position": [10, 9], "units_max": 9},
            {"id": "axis_approach", "side": "enemy", "position": [3, 17], "units_max": 9},
        ],
    )


def generate_veghel_crossroads() -> dict:
    """Veghel Crossroads - Road junction battle (101st Airborne sector).

    Layout: Cross roads with buildings at the junction, hedgerows.
    """
    tiles = _fill("grass")
    rng = random.Random(103)

    # Cross roads
    for c in range(MAP_SIZE):
        tiles[10][c] = "road"
    for r in range(MAP_SIZE):
        tiles[r][10] = "road"

    # Junction buildings
    for r, c in [(8, 8), (8, 9), (9, 8), (11, 11), (11, 12), (12, 11)]:
        tiles[r][c] = "building_enterable"

    # Junction checkpoint
    tiles[10][10] = "building_solid"

    # Hedgerows along roads
    for r in range(MAP_SIZE):
        if r not in (8, 9, 10, 11, 12):
            tiles[r][8] = "hedge"
            tiles[r][12] = "hedge"
    for c in range(MAP_SIZE):
        if c not in (8, 9, 10, 11, 12):
            tiles[8][c] = "hedge"
            tiles[12][c] = "hedge"

    # Woods in corners
    _scatter(tiles, "woods", 15, rng, region=(0, 0, 8, 8))
    _scatter(tiles, "woods", 15, rng, region=(12, 0, 8, 8))
    _scatter(tiles, "woods", 10, rng, region=(0, 12, 8, 8))
    _scatter(tiles, "woods", 10, rng, region=(12, 12, 8, 8))

    return _make_map(
        "Veghel Crossroads - Road Junction",
        tiles,
        objectives=[
            {"id": "crossroads", "name": "Crossroads", "position": [10, 10], "type": "capture"},
            {"id": "south_road", "name": "South Road", "position": [10, 17], "type": "reach"},
        ],
        spawn_points=[
            {"id": "allied_north", "side": "friendly", "position": [10, 2], "units_max": 9},
            {"id": "axis_south", "side": "enemy", "position": [10, 17], "units_max": 9},
        ],
    )


def generate_zonsche_forest() -> dict:
    """Zonsche Forest - Forest approach (101st Airborne sector).

    Layout: Dense woods (40-60% coverage), paths/roads cutting through, clearings.
    """
    tiles = _fill("grass")
    rng = random.Random(104)

    # Main path through forest
    for c in range(2, 18):
        tiles[10][c] = "road"

    # Side path
    for r in range(5, 15):
        tiles[r][5] = "road"

    # Dense forest coverage
    _scatter(tiles, "woods", 80, rng)

    # Clear the road areas
    for c in range(2, 18):
        tiles[10][c] = "road"
        tiles[9][c] = "grass"
        tiles[11][c] = "grass"
    for r in range(5, 15):
        tiles[r][5] = "road"
        tiles[r][4] = "grass"
        tiles[r][6] = "grass"

    # Clearings
    for r in range(3, 7):
        for c in range(12, 17):
            tiles[r][c] = "grass"

    # Small building at crossroads
    tiles[10][5] = "building_enterable"

    # Hedges along clearings
    _scatter(tiles, "hedge", 8, rng, region=(12, 3, 5, 4))

    return _make_map(
        "Zonsche Forest - Forest Approach",
        tiles,
        objectives=[
            {"id": "forest_exit", "name": "Forest Exit", "position": [17, 10], "type": "reach"},
            {
                "id": "crossroads",
                "name": "Forest Crossroads",
                "position": [5, 10],
                "type": "capture",
            },
        ],
        spawn_points=[
            {"id": "allied_west", "side": "friendly", "position": [2, 10], "units_max": 9},
            {"id": "axis_east", "side": "enemy", "position": [17, 10], "units_max": 9},
        ],
    )


def generate_eindhoven_suburbs() -> dict:
    """Eindhoven Suburbs - Urban fighting (101st Airborne sector).

    Layout: Many buildings (15-25), roads forming grid, some rubble.
    """
    tiles = _fill("grass")
    rng = random.Random(105)

    # Grid roads
    for r in (5, 10, 15):
        for c in range(MAP_SIZE):
            tiles[r][c] = "road"
    for c in (5, 10, 15):
        for r in range(MAP_SIZE):
            tiles[r][c] = "road"

    # Urban buildings (15-25)
    building_positions = [
        (3, 3),
        (3, 4),
        (4, 3),
        (3, 7),
        (3, 8),
        (4, 8),
        (3, 12),
        (4, 12),
        (4, 13),
        (7, 3),
        (8, 3),
        (8, 4),
        (7, 7),
        (7, 8),
        (8, 7),
        (8, 8),
        (7, 12),
        (7, 13),
        (8, 12),
        (12, 3),
        (12, 4),
        (13, 3),
        (12, 7),
        (13, 7),
        (13, 8),
        (12, 12),
        (12, 13),
        (13, 12),
        (13, 13),
        (17, 7),
        (17, 8),
        (17, 12),
        (17, 13),
    ]
    for r, c in building_positions:
        if 0 <= r < MAP_SIZE and 0 <= c < MAP_SIZE:
            tiles[r][c] = "building_enterable"

    # Some solid (destroyed) buildings
    tiles[8][8] = "building_solid"
    tiles[13][13] = "building_solid"

    # Rubble/rough patches
    _scatter(tiles, "rough", 10, rng)

    # Hedges in suburban yards
    _scatter(tiles, "hedge", 8, rng)

    return _make_map(
        "Eindhoven Suburbs - Urban Fighting",
        tiles,
        objectives=[
            {"id": "town_center", "name": "Town Center", "position": [10, 10], "type": "capture"},
            {"id": "north_block", "name": "North Block", "position": [7, 3], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_south", "side": "friendly", "position": [10, 17], "units_max": 9},
            {"id": "axis_north", "side": "enemy", "position": [10, 2], "units_max": 9},
        ],
    )


# ======================================================================
# Operation Nijmegen (82nd Airborne) - 5 maps
# ======================================================================


def generate_nijmegen_crossing() -> dict:
    """Nijmegen Crossing - Waal River crossing (82nd Airborne sector)."""
    tiles = _fill("grass")
    rng = random.Random(82)

    # Waal River - wider water band rows 8-11
    for r in range(8, 12):
        _horizontal_band(tiles, r, "water")

    # Railway bridge (columns 5-6)
    for r in range(8, 12):
        for c in (5, 6):
            tiles[r][c] = "bridge"

    # Road bridge (columns 14-15)
    for r in range(8, 12):
        for c in (14, 15):
            tiles[r][c] = "bridge"

    # Roads approaching bridges
    for r in range(0, 8):
        tiles[r][5] = "road"
        tiles[r][6] = "road"
        tiles[r][14] = "road"
        tiles[r][15] = "road"

    for r in range(12, MAP_SIZE):
        tiles[r][5] = "road"
        tiles[r][6] = "road"
        tiles[r][14] = "road"
        tiles[r][15] = "road"

    # Cross road on south bank
    for c in range(5, 16):
        tiles[14][c] = "road"

    # Urban area on south bank (Nijmegen city)
    for r in range(12, MAP_SIZE):
        for c in range(0, 5):
            if rng.random() < 0.3:
                tiles[r][c] = "building_enterable"
    for r in range(12, MAP_SIZE):
        for c in range(16, MAP_SIZE):
            if rng.random() < 0.3:
                tiles[r][c] = "building_enterable"

    # Buildings along the road on south bank
    for r, c in [(13, 8), (13, 9), (15, 8), (15, 9), (16, 10), (16, 11)]:
        tiles[r][c] = "building_enterable"

    # North bank: open fields with hedges
    _scatter(tiles, "hedge", 15, rng, region=(0, 0, MAP_SIZE, 8))
    _scatter(tiles, "woods", 6, rng, region=(0, 0, MAP_SIZE, 8))

    return _make_map(
        "Nijmegen Crossing - Waal River",
        tiles,
        objectives=[
            {"id": "rail_bridge", "name": "Railway Bridge", "position": [5, 9], "type": "capture"},
            {"id": "road_bridge", "name": "Road Bridge", "position": [14, 9], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_north", "side": "friendly", "position": [10, 2], "units_max": 9},
            {"id": "axis_south", "side": "enemy", "position": [10, 17], "units_max": 9},
        ],
    )


def generate_grave_bridge() -> dict:
    """Grave Bridge - Bridge capture (82nd Airborne sector).

    Layout: River running through center, single bridge, buildings on both banks.
    """
    tiles = _fill("grass")
    rng = random.Random(821)

    # River running vertically through center (cols 9-10)
    for r in range(MAP_SIZE):
        tiles[r][9] = "water"
        tiles[r][10] = "water"

    # Bridge at row 10
    tiles[10][9] = "bridge"
    tiles[10][10] = "bridge"

    # Road approaching bridge from west
    for c in range(0, 9):
        tiles[10][c] = "road"

    # Road continuing east from bridge
    for c in range(11, MAP_SIZE):
        tiles[10][c] = "road"

    # North-south road on west bank
    for r in range(MAP_SIZE):
        tiles[r][5] = "road"

    # Buildings on west bank
    for r, c in [(7, 3), (7, 4), (8, 3), (13, 3), (13, 4), (14, 3)]:
        tiles[r][c] = "building_enterable"

    # Buildings on east bank
    for r, c in [(7, 14), (7, 15), (8, 14), (13, 14), (13, 15), (14, 14)]:
        tiles[r][c] = "building_enterable"

    # Hedges
    _scatter(tiles, "hedge", 15, rng, region=(0, 0, 9, MAP_SIZE))
    _scatter(tiles, "hedge", 15, rng, region=(11, 0, 9, MAP_SIZE))

    # Woods on edges
    _scatter(tiles, "woods", 6, rng, region=(0, 0, 3, MAP_SIZE))
    _scatter(tiles, "woods", 6, rng, region=(17, 0, 3, MAP_SIZE))

    return _make_map(
        "Grave Bridge - Maas River",
        tiles,
        objectives=[
            {"id": "bridge", "name": "Grave Bridge", "position": [9, 10], "type": "capture"},
            {"id": "east_bank", "name": "East Bank", "position": [14, 10], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_west", "side": "friendly", "position": [3, 10], "units_max": 9},
            {"id": "axis_east", "side": "enemy", "position": [17, 10], "units_max": 9},
        ],
    )


def generate_groesbeek_heights() -> dict:
    """Groesbeek Heights - Elevated position defense (82nd Airborne sector).

    Layout: Elevated terrain with good LOS, scattered buildings.
    Uses rough terrain to represent heights.
    """
    tiles = _fill("grass")
    rng = random.Random(822)

    # Heights represented by rough terrain in the center-north
    for r in range(3, 10):
        for c in range(4, 16):
            if rng.random() < 0.6:
                tiles[r][c] = "rough"

    # Road through the heights
    for c in range(MAP_SIZE):
        tiles[6][c] = "road"

    # Buildings on heights
    for r, c in [(4, 7), (4, 8), (5, 7), (5, 12), (5, 13), (4, 12)]:
        tiles[r][c] = "building_enterable"

    # Observation post (solid building)
    tiles[4][10] = "building_solid"

    # Lower ground to the south - hedgerows and fields
    _scatter(tiles, "hedge", 20, rng, region=(0, 10, MAP_SIZE, 10))

    # Woods on flanks
    _scatter(tiles, "woods", 12, rng, region=(0, 0, 4, 10))
    _scatter(tiles, "woods", 12, rng, region=(16, 0, 4, 10))

    # South approach road
    for r in range(10, MAP_SIZE):
        tiles[r][10] = "road"

    return _make_map(
        "Groesbeek Heights - Elevated Defense",
        tiles,
        objectives=[
            {"id": "heights", "name": "Groesbeek Heights", "position": [10, 5], "type": "defend"},
            {"id": "obs_post", "name": "Observation Post", "position": [10, 4], "type": "defend"},
        ],
        spawn_points=[
            {"id": "allied_heights", "side": "friendly", "position": [10, 5], "units_max": 9},
            {"id": "axis_south", "side": "enemy", "position": [10, 17], "units_max": 9},
        ],
    )


def generate_mook_woods() -> dict:
    """Mook Woods - Forest patrol (82nd Airborne sector).

    Layout: Dense woods with paths cutting through, clearings.
    """
    tiles = _fill("grass")
    rng = random.Random(823)

    # Main path
    for c in range(MAP_SIZE):
        tiles[10][c] = "road"

    # Secondary path
    for r in range(4, 16):
        tiles[r][14] = "road"

    # Dense forest
    _scatter(tiles, "woods", 100, rng)

    # Clear road areas
    for c in range(MAP_SIZE):
        tiles[10][c] = "road"
        tiles[9][c] = "grass"
        tiles[11][c] = "grass"
    for r in range(4, 16):
        tiles[r][14] = "road"
        tiles[r][13] = "grass"
        tiles[r][15] = "grass"

    # Clearings
    for r in range(2, 6):
        for c in range(2, 6):
            tiles[r][c] = "grass"
    for r in range(14, 18):
        for c in range(2, 6):
            tiles[r][c] = "grass"

    # Small buildings at crossroads
    tiles[10][14] = "building_enterable"

    # Hedges around clearings
    _scatter(tiles, "hedge", 6, rng, region=(2, 2, 4, 4))
    _scatter(tiles, "hedge", 6, rng, region=(2, 14, 4, 4))

    return _make_map(
        "Mook Woods - Forest Patrol",
        tiles,
        objectives=[
            {
                "id": "crossroads",
                "name": "Forest Crossroads",
                "position": [14, 10],
                "type": "capture",
            },
            {"id": "clearing", "name": "North Clearing", "position": [3, 3], "type": "reach"},
        ],
        spawn_points=[
            {"id": "allied_west", "side": "friendly", "position": [0, 10], "units_max": 9},
            {"id": "axis_east", "side": "enemy", "position": [19, 10], "units_max": 9},
        ],
    )


def generate_nijmegen_streets() -> dict:
    """Nijmegen Streets - Street fighting (82nd Airborne sector).

    Layout: Many buildings, roads forming grid, urban combat.
    """
    tiles = _fill("grass")
    rng = random.Random(824)

    # Grid roads
    for r in (4, 9, 14):
        for c in range(MAP_SIZE):
            tiles[r][c] = "road"
    for c in (4, 9, 14):
        for r in range(MAP_SIZE):
            tiles[r][c] = "road"

    # Dense urban buildings
    for r in range(MAP_SIZE):
        for c in range(MAP_SIZE):
            if tiles[r][c] == "grass" and rng.random() < 0.3:
                tiles[r][c] = "building_enterable"

    # Some solid/destroyed buildings
    tiles[6][6] = "building_solid"
    tiles[11][11] = "building_solid"
    tiles[16][6] = "building_solid"

    # Rubble
    _scatter(tiles, "rough", 8, rng)

    return _make_map(
        "Nijmegen Streets - Urban Combat",
        tiles,
        objectives=[
            {"id": "city_center", "name": "City Center", "position": [9, 9], "type": "capture"},
            {"id": "market", "name": "Market Square", "position": [4, 9], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_south", "side": "friendly", "position": [9, 17], "units_max": 9},
            {"id": "axis_north", "side": "enemy", "position": [9, 2], "units_max": 9},
        ],
    )


# ======================================================================
# Operation Arnhem (British 1st Airborne) - 5 maps
# ======================================================================


def generate_arnhem_bridge() -> dict:
    """Arnhem Bridge - Rhine River bridge (British 1st Airborne)."""
    tiles = _fill("grass")
    rng = random.Random(1)  # 1st Airborne

    # Rhine River - rows 9-12
    for r in range(9, 13):
        _horizontal_band(tiles, r, "water")

    # Arnhem road bridge (columns 9-11)
    for r in range(9, 13):
        for c in (9, 10, 11):
            tiles[r][c] = "bridge"

    # Main road north-south through bridge
    for r in range(0, 9):
        tiles[r][9] = "road"
        tiles[r][10] = "road"
        tiles[r][11] = "road"
    for r in range(13, MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"
        tiles[r][11] = "road"

    # Dense urban area on north bank (Arnhem)
    for r in range(0, 9):
        for c in range(0, 9):
            if rng.random() < 0.35:
                tiles[r][c] = "building_enterable"
        for c in range(12, MAP_SIZE):
            if rng.random() < 0.35:
                tiles[r][c] = "building_enterable"

    # South bank: more open, some buildings
    for r in range(13, MAP_SIZE):
        for c in range(6, 14):
            if rng.random() < 0.2:
                tiles[r][c] = "building_enterable"

    # Parks / woods patches in city
    _scatter(tiles, "woods", 5, rng, region=(0, 0, 9, 9))

    return _make_map(
        "Arnhem Bridge - Rhine River",
        tiles,
        objectives=[
            {
                "id": "bridge_north",
                "name": "Bridge North End",
                "position": [10, 8],
                "type": "capture",
            },
            {
                "id": "bridge_south",
                "name": "Bridge South End",
                "position": [10, 13],
                "type": "capture",
            },
        ],
        spawn_points=[
            {"id": "allied_north", "side": "friendly", "position": [10, 2], "units_max": 9},
            {"id": "axis_south", "side": "enemy", "position": [10, 17], "units_max": 9},
        ],
    )


def generate_oosterbeek_perimeter() -> dict:
    """Oosterbeek Perimeter - Defensive perimeter around Oosterbeek."""
    tiles = _fill("grass")
    rng = random.Random(1944)

    # Central perimeter road (oval-ish)
    for c in range(5, 15):
        tiles[4][c] = "road"
        tiles[15][c] = "road"
    for r in range(4, 16):
        tiles[r][5] = "road"
        tiles[r][14] = "road"

    # Cross roads
    for c in range(5, 15):
        tiles[9][c] = "road"
        tiles[10][c] = "road"

    # Dense buildings inside perimeter (Oosterbeek village)
    for r in range(5, 15):
        for c in range(6, 14):
            if rng.random() < 0.25:
                tiles[r][c] = "building_enterable"

    # Trenches along perimeter edges (represented by rough)
    for c in range(5, 15):
        if c % 2 == 0:
            tiles[3][c] = "rough"
            tiles[16][c] = "rough"
    for r in range(4, 16):
        if r % 2 == 0:
            tiles[r][4] = "rough"
            tiles[r][15] = "rough"

    # Hedgerows outside perimeter
    _scatter(tiles, "hedge", 20, rng, region=(0, 0, 5, MAP_SIZE))
    _scatter(tiles, "hedge", 20, rng, region=(15, 0, 5, MAP_SIZE))
    _scatter(tiles, "hedge", 10, rng, region=(5, 0, 10, 4))
    _scatter(tiles, "hedge", 10, rng, region=(5, 16, 10, 4))

    # Forest patches
    _scatter(tiles, "woods", 8, rng, region=(0, 0, 5, 10))
    _scatter(tiles, "woods", 8, rng, region=(15, 10, 5, 10))

    # Rough patches
    _scatter(tiles, "rough", 10, rng)

    # Hotel Hartenstein (HQ) - prominent building
    tiles[9][9] = "building_solid"
    tiles[9][10] = "building_solid"
    tiles[10][9] = "building_enterable"
    tiles[10][10] = "building_enterable"

    return _make_map(
        "Oosterbeek Perimeter",
        tiles,
        objectives=[
            {
                "id": "hartenstein",
                "name": "Hotel Hartenstein HQ",
                "position": [9, 9],
                "type": "defend",
            },
            {"id": "perimeter_n", "name": "North Perimeter", "position": [10, 4], "type": "defend"},
        ],
        spawn_points=[
            {"id": "allied_hq", "side": "friendly", "position": [10, 10], "units_max": 9},
            {"id": "axis_outside", "side": "enemy", "position": [2, 2], "units_max": 9},
        ],
    )


def generate_arnhem_streets() -> dict:
    """Arnhem Streets - Urban assault (British 1st Airborne).

    Layout: Dense urban grid, many buildings, roads, rubble.
    """
    tiles = _fill("grass")
    rng = random.Random(12)

    # Dense road grid
    for r in (3, 7, 11, 15):
        for c in range(MAP_SIZE):
            tiles[r][c] = "road"
    for c in (3, 7, 11, 15):
        for r in range(MAP_SIZE):
            tiles[r][c] = "road"

    # Dense urban buildings
    for r in range(MAP_SIZE):
        for c in range(MAP_SIZE):
            if tiles[r][c] == "grass" and rng.random() < 0.4:
                tiles[r][c] = "building_enterable"

    # Destroyed/solid buildings
    tiles[5][5] = "building_solid"
    tiles[9][9] = "building_solid"
    tiles[13][13] = "building_solid"
    tiles[5][13] = "building_solid"

    # Rubble
    _scatter(tiles, "rough", 15, rng)

    return _make_map(
        "Arnhem Streets - Urban Assault",
        tiles,
        objectives=[
            {"id": "town_hall", "name": "Town Hall", "position": [7, 7], "type": "capture"},
            {"id": "station", "name": "Railway Station", "position": [15, 11], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_west", "side": "friendly", "position": [2, 10], "units_max": 9},
            {"id": "axis_east", "side": "enemy", "position": [17, 10], "units_max": 9},
        ],
    )


def generate_hartenstein_hotel() -> dict:
    """Hartenstein Hotel - HQ defense (British 1st Airborne).

    Layout: Central building complex, surrounding gardens/park, perimeter defense.
    """
    tiles = _fill("grass")
    rng = random.Random(13)

    # Main road
    for c in range(MAP_SIZE):
        tiles[10][c] = "road"

    # Side road
    for r in range(MAP_SIZE):
        tiles[r][10] = "road"

    # Hartenstein Hotel complex (central)
    for r in range(8, 12):
        for c in range(8, 12):
            tiles[r][c] = "building_enterable"
    tiles[9][9] = "building_solid"
    tiles[9][10] = "building_solid"

    # Outbuildings
    for r, c in [
        (6, 6),
        (6, 7),
        (7, 6),
        (6, 13),
        (6, 14),
        (7, 14),
        (13, 6),
        (13, 7),
        (14, 6),
        (13, 13),
        (13, 14),
        (14, 14),
    ]:
        tiles[r][c] = "building_enterable"

    # Garden/park area (woods around hotel)
    _scatter(tiles, "woods", 15, rng, region=(5, 5, 10, 10))

    # Clear the road and buildings
    for c in range(MAP_SIZE):
        tiles[10][c] = "road"
    for r in range(MAP_SIZE):
        tiles[r][10] = "road"
    for r in range(8, 12):
        for c in range(8, 12):
            tiles[r][c] = "building_enterable"
    tiles[9][9] = "building_solid"
    tiles[9][10] = "building_solid"

    # Perimeter defenses (rough = trenches)
    for c in range(4, 16):
        tiles[5][c] = "rough"
        tiles[14][c] = "rough"
    for r in range(5, 15):
        tiles[r][4] = "rough"
        tiles[r][15] = "rough"

    # Hedges on outer edges
    _scatter(tiles, "hedge", 20, rng, region=(0, 0, 4, MAP_SIZE))
    _scatter(tiles, "hedge", 20, rng, region=(16, 0, 4, MAP_SIZE))

    return _make_map(
        "Hartenstein Hotel - HQ Defense",
        tiles,
        objectives=[
            {"id": "hotel", "name": "Hartenstein Hotel", "position": [9, 9], "type": "defend"},
            {"id": "perimeter", "name": "Defense Perimeter", "position": [10, 5], "type": "defend"},
        ],
        spawn_points=[
            {"id": "allied_hotel", "side": "friendly", "position": [10, 9], "units_max": 9},
            {"id": "axis_approach", "side": "enemy", "position": [2, 17], "units_max": 9},
        ],
    )


def generate_rhine_crossing() -> dict:
    """Rhine Crossing - River evacuation (British 1st Airborne).

    Layout: Wide river, one crossing point, north bank defensive, south bank evacuation.
    """
    tiles = _fill("grass")
    rng = random.Random(14)

    # Wide Rhine river rows 7-12
    for r in range(7, 13):
        _horizontal_band(tiles, r, "water")

    # Single crossing point (shallow water at cols 9-10)
    for r in range(7, 13):
        tiles[r][9] = "shallow"
        tiles[r][10] = "shallow"

    # Road to crossing from north
    for r in range(0, 7):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    # Road from crossing to south
    for r in range(13, MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    # North bank: defensive positions (rough = trenches)
    for c in range(6, 14):
        tiles[6][c] = "rough"

    # North bank buildings
    for r, c in [(3, 5), (3, 6), (4, 5), (3, 13), (3, 14), (4, 14)]:
        tiles[r][c] = "building_enterable"

    # South bank: evacuation point
    for r, c in [(15, 8), (15, 9), (15, 10), (15, 11), (16, 9), (16, 10)]:
        tiles[r][c] = "building_enterable"

    # Woods on flanks
    _scatter(tiles, "woods", 15, rng, region=(0, 0, 6, 7))
    _scatter(tiles, "woods", 15, rng, region=(14, 0, 6, 7))
    _scatter(tiles, "woods", 10, rng, region=(0, 13, 6, 7))
    _scatter(tiles, "woods", 10, rng, region=(14, 13, 6, 7))

    # Hedges
    _scatter(tiles, "hedge", 10, rng, region=(0, 0, 6, 7))
    _scatter(tiles, "hedge", 10, rng, region=(14, 13, 6, 7))

    return _make_map(
        "Rhine Crossing - River Evacuation",
        tiles,
        objectives=[
            {"id": "crossing", "name": "River Crossing", "position": [9, 9], "type": "reach"},
            {"id": "evac_point", "name": "Evacuation Point", "position": [10, 16], "type": "reach"},
        ],
        spawn_points=[
            {"id": "allied_north", "side": "friendly", "position": [10, 2], "units_max": 9},
            {"id": "axis_south", "side": "enemy", "position": [10, 17], "units_max": 9},
        ],
    )


# ======================================================================
# Operation Hell's Highway (XXX Corps) - 5 maps
# ======================================================================


def generate_hell_highway() -> dict:
    """Hell's Highway - Road corridor (XXX Corps advance)."""
    tiles = _fill("grass")
    rng = random.Random(30)  # XXX Corps

    # Main highway running north-south (columns 9-10)
    for r in range(MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    # Hedgerows flanking the road
    for r in range(MAP_SIZE):
        if r % 3 != 0:  # Leave gaps for cross-roads
            tiles[r][7] = "hedge"
            tiles[r][8] = "hedge"
            tiles[r][11] = "hedge"
            tiles[r][12] = "hedge"

    # Cross roads at intervals
    for row in (4, 9, 14):
        for c in range(3, 17):
            tiles[row][c] = "road"

    # Village 1 (north)
    for r, c in [(1, 3), (1, 4), (2, 3), (2, 4), (1, 15), (1, 16), (2, 15), (2, 16)]:
        tiles[r][c] = "building_enterable"

    # Village 2 (middle)
    for r, c in [(7, 3), (7, 4), (8, 3), (8, 4), (7, 15), (7, 16), (8, 15), (8, 16)]:
        tiles[r][c] = "building_enterable"

    # Village 3 (south)
    for r, c in [(12, 3), (12, 4), (13, 3), (13, 4), (12, 15), (12, 16), (13, 15), (13, 16)]:
        tiles[r][c] = "building_enterable"

    # Forest patches on outer edges
    _scatter(tiles, "woods", 10, rng, region=(0, 0, 3, MAP_SIZE))
    _scatter(tiles, "woods", 10, rng, region=(17, 0, 3, MAP_SIZE))

    # Rough patches
    _scatter(tiles, "rough", 12, rng)

    # Defensive positions along road (rough = trenches)
    for r in (3, 6, 11, 16):
        tiles[r][8] = "rough"
        tiles[r][11] = "rough"

    return _make_map(
        "Hell's Highway - XXX Corps Corridor",
        tiles,
        objectives=[
            {"id": "north_village", "name": "North Village", "position": [3, 1], "type": "capture"},
            {
                "id": "south_village",
                "name": "South Village",
                "position": [15, 13],
                "type": "capture",
            },
        ],
        spawn_points=[
            {"id": "allied_south", "side": "friendly", "position": [10, 18], "units_max": 9},
            {"id": "axis_north", "side": "enemy", "position": [10, 1], "units_max": 9},
        ],
    )


def generate_vught_bridge() -> dict:
    """Vught Bridge - Canal crossing (XXX Corps sector).

    Layout: Canal running through center, bridge crossing, buildings on both banks.
    """
    tiles = _fill("grass")
    rng = random.Random(301)

    # Canal (water) running horizontally rows 9-10
    for r in (9, 10):
        _horizontal_band(tiles, r, "water")

    # Bridge at columns 9-11
    for r in (9, 10):
        for c in (9, 10, 11):
            tiles[r][c] = "bridge"

    # Road approaching from south
    for r in range(11, MAP_SIZE):
        tiles[r][10] = "road"

    # Road continuing north
    for r in range(0, 9):
        tiles[r][10] = "road"

    # Cross road on north bank
    for c in range(5, 15):
        tiles[5][c] = "road"

    # Buildings on north bank
    for r, c in [
        (3, 5),
        (3, 6),
        (4, 5),
        (3, 13),
        (3, 14),
        (4, 14),
        (6, 7),
        (6, 8),
        (7, 7),
        (6, 12),
        (6, 13),
        (7, 13),
    ]:
        tiles[r][c] = "building_enterable"

    # Buildings on south bank
    for r, c in [(13, 7), (13, 8), (14, 7), (13, 12), (13, 13), (14, 13)]:
        tiles[r][c] = "building_enterable"

    # Hedges
    _scatter(tiles, "hedge", 15, rng, region=(0, 0, 9, 9))
    _scatter(tiles, "hedge", 15, rng, region=(11, 0, 9, 9))
    _scatter(tiles, "hedge", 15, rng, region=(0, 11, 9, 9))
    _scatter(tiles, "hedge", 15, rng, region=(11, 11, 9, 9))

    # Woods
    _scatter(tiles, "woods", 8, rng, region=(0, 0, 4, 9))
    _scatter(tiles, "woods", 8, rng, region=(16, 0, 4, 9))

    return _make_map(
        "Vught Bridge - Canal Crossing",
        tiles,
        objectives=[
            {"id": "bridge", "name": "Vught Bridge", "position": [10, 9], "type": "capture"},
            {"id": "north_bank", "name": "North Bank", "position": [10, 5], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_south", "side": "friendly", "position": [10, 17], "units_max": 9},
            {"id": "axis_north", "side": "enemy", "position": [10, 2], "units_max": 9},
        ],
    )


def generate_s_hertogenbosch() -> dict:
    """'s-Hertogenbosch - City assault (XXX Corps sector).

    Layout: Dense city with many buildings, roads forming grid, walls.
    """
    tiles = _fill("grass")
    rng = random.Random(302)

    # City wall (represented by wall tiles)
    for c in range(3, 17):
        tiles[5][c] = "wall"
        tiles[14][c] = "wall"
    for r in range(5, 15):
        tiles[r][3] = "wall"
        tiles[r][16] = "wall"

    # Gate openings
    tiles[5][9] = "road"
    tiles[5][10] = "road"
    tiles[14][9] = "road"
    tiles[14][10] = "road"
    tiles[9][3] = "road"
    tiles[10][3] = "road"
    tiles[9][16] = "road"
    tiles[10][16] = "road"

    # Internal road grid
    for c in range(3, 17):
        tiles[9][c] = "road"
        tiles[10][c] = "road"
    for r in range(5, 15):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    # Dense buildings inside walls
    for r in range(6, 14):
        for c in range(4, 16):
            if tiles[r][c] == "grass" and rng.random() < 0.4:
                tiles[r][c] = "building_enterable"

    # Cathedral (solid building)
    tiles[7][7] = "building_solid"
    tiles[7][8] = "building_solid"
    tiles[8][7] = "building_solid"
    tiles[8][8] = "building_solid"

    # Outside: hedges and rough
    _scatter(tiles, "hedge", 15, rng, region=(0, 0, 3, MAP_SIZE))
    _scatter(tiles, "hedge", 15, rng, region=(17, 0, 3, MAP_SIZE))
    _scatter(tiles, "rough", 8, rng, region=(0, 0, 3, 5))
    _scatter(tiles, "rough", 8, rng, region=(17, 15, 3, 5))

    # Approach roads
    for r in range(0, 5):
        tiles[r][9] = "road"
        tiles[r][10] = "road"
    for r in range(15, MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    return _make_map(
        "'s-Hertogenbosch - City Assault",
        tiles,
        objectives=[
            {"id": "cathedral", "name": "Cathedral", "position": [7, 7], "type": "capture"},
            {"id": "market", "name": "Market Square", "position": [10, 10], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_outside", "side": "friendly", "position": [10, 17], "units_max": 9},
            {"id": "axis_inside", "side": "enemy", "position": [10, 7], "units_max": 9},
        ],
    )


def generate_overloon_battlefield() -> dict:
    """Overloon Battlefield - Open terrain tank battle (XXX Corps sector).

    Layout: Mostly grass with scattered hedgerows, roads, some buildings.
    Open terrain favoring armor.
    """
    tiles = _fill("grass")
    rng = random.Random(303)

    # Main road east-west
    for c in range(MAP_SIZE):
        tiles[10][c] = "road"

    # Cross road
    for r in range(MAP_SIZE):
        tiles[r][10] = "road"

    # Scattered hedgerows
    _scatter(tiles, "hedge", 30, rng)

    # Clear road areas
    for c in range(MAP_SIZE):
        tiles[10][c] = "road"
    for r in range(MAP_SIZE):
        tiles[r][10] = "road"

    # Few buildings at crossroads
    tiles[8][8] = "building_enterable"
    tiles[8][12] = "building_enterable"
    tiles[12][8] = "building_enterable"
    tiles[12][12] = "building_enterable"

    # Rough patches (shell craters)
    _scatter(tiles, "rough", 12, rng)

    # Small woods patches
    _scatter(tiles, "woods", 8, rng, region=(0, 0, 5, 5))
    _scatter(tiles, "woods", 8, rng, region=(15, 15, 5, 5))

    return _make_map(
        "Overloon Battlefield - Open Terrain",
        tiles,
        objectives=[
            {"id": "crossroads", "name": "Crossroads", "position": [10, 10], "type": "capture"},
            {"id": "ridge", "name": "Overloon Ridge", "position": [10, 5], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_south", "side": "friendly", "position": [10, 17], "units_max": 9},
            {"id": "axis_north", "side": "enemy", "position": [10, 2], "units_max": 9},
        ],
    )


def generate_meijel_woods() -> dict:
    """Meijel Woods - Forest ambush (XXX Corps sector).

    Layout: Dense forest with paths, ambush positions.
    """
    tiles = _fill("grass")
    rng = random.Random(304)

    # Main path through forest
    for c in range(3, 17):
        tiles[10][c] = "road"

    # Side path
    for r in range(5, 15):
        tiles[r][15] = "road"

    # Very dense forest
    _scatter(tiles, "woods", 120, rng)

    # Clear road areas
    for c in range(3, 17):
        tiles[10][c] = "road"
        tiles[9][c] = "grass"
        tiles[11][c] = "grass"
    for r in range(5, 15):
        tiles[r][15] = "road"
        tiles[r][14] = "grass"
        tiles[r][16] = "grass"

    # Small clearing
    for r in range(3, 7):
        for c in range(3, 7):
            tiles[r][c] = "grass"

    # Ambush positions (rough = prepared positions)
    tiles[8][7] = "rough"
    tiles[8][12] = "rough"
    tiles[12][7] = "rough"
    tiles[12][12] = "rough"

    # Small building at path junction
    tiles[10][15] = "building_enterable"

    # Hedges at clearing
    _scatter(tiles, "hedge", 5, rng, region=(3, 3, 4, 4))

    return _make_map(
        "Meijel Woods - Forest Ambush",
        tiles,
        objectives=[
            {"id": "junction", "name": "Path Junction", "position": [15, 10], "type": "capture"},
            {"id": "clearing", "name": "Forest Clearing", "position": [4, 4], "type": "reach"},
        ],
        spawn_points=[
            {"id": "allied_west", "side": "friendly", "position": [3, 10], "units_max": 9},
            {"id": "axis_east", "side": "enemy", "position": [17, 10], "units_max": 9},
        ],
    )


def main() -> None:
    """Generate all Market Garden campaign maps."""
    project_root = Path(__file__).resolve().parent.parent
    maps_dir = project_root / "data" / "maps"
    maps_dir.mkdir(parents=True, exist_ok=True)

    generators = [
        # Operation Eindhoven (101st Airborne)
        ("son_bridge.json", generate_son_bridge),
        ("best_village.json", generate_best_village),
        ("veghel_crossroads.json", generate_veghel_crossroads),
        ("zonsche_forest.json", generate_zonsche_forest),
        ("eindhoven_suburbs.json", generate_eindhoven_suburbs),
        # Operation Nijmegen (82nd Airborne)
        ("nijmegen_crossing.json", generate_nijmegen_crossing),
        ("grave_bridge.json", generate_grave_bridge),
        ("groesbeek_heights.json", generate_groesbeek_heights),
        ("mook_woods.json", generate_mook_woods),
        ("nijmegen_streets.json", generate_nijmegen_streets),
        # Operation Arnhem (British 1st Airborne)
        ("arnhem_bridge.json", generate_arnhem_bridge),
        ("oosterbeek_perimeter.json", generate_oosterbeek_perimeter),
        ("arnhem_streets.json", generate_arnhem_streets),
        ("hartenstein_hotel.json", generate_hartenstein_hotel),
        ("rhine_crossing.json", generate_rhine_crossing),
        # Operation Hell's Highway (XXX Corps)
        ("hell_highway.json", generate_hell_highway),
        ("vught_bridge.json", generate_vught_bridge),
        ("s_hertogenbosch.json", generate_s_hertogenbosch),
        ("overloon_battlefield.json", generate_overloon_battlefield),
        ("meijel_woods.json", generate_meijel_woods),
    ]

    for filename, gen_func in generators:
        map_data = gen_func()
        filepath = maps_dir / filename
        with open(filepath, "w") as f:
            json.dump(map_data, f, indent=2)
        print(f"  Generated: {filepath}")

    print(f"\nDone! Generated {len(generators)} Market Garden campaign maps.")


if __name__ == "__main__":
    main()
