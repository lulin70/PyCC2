#!/usr/bin/env python3
"""
Generate additional historically accurate Market Garden campaign map files.

Creates 16 new map JSON files based on detailed historical research of
Operation Market Garden (September 17-25, 1944). These maps complement the
existing 20 maps from gen_campaign_maps.py, covering battles not previously
represented.

Historical sources:
- 101st Airborne: Son bridge destruction, St. Oedenrode Dommel bridges,
  Koevering crossroads defense (Sept 23-24 corridor cut), Wilhelmina Canal
  Bailey bridge, Driel Polish landing zone.
- 82nd Airborne: Maas-Waal Canal crossing (504th PIR), Molenhoek ridge
  fighting, Honinghutie road block, Devil's Hill near Groesbeek.
- British 1st Airborne: Westerbouwing heights (key terrain south of
  Oosterbeek), Arnhem railway bridge, Oosterbeek church strongpoint,
  Driel Polish crossing of the Rhine.
- XXX Corps: Valkenswaard woods (Irish Guards first engagement),
  Aalsmeer flank attack, Venray tank battle, Nederweert canal defense.

Each map is 20x20 tiles using the JSON format compatible with GameMap.from_json.
Terrain names match _TERRAIN_NAME_MAP: open, road, grass, woods, building_enterable,
building_solid, water, hedge, wall, rough, shallow, bridge.
"""

import json
import random
from pathlib import Path

MAP_SIZE = 20

TERRAIN_TYPES = [
    "open", "road", "grass", "woods", "building_enterable",
    "building_solid", "water", "hedge", "wall", "rough", "shallow", "bridge",
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


# ======================================================================
# 101st Airborne - Additional Maps (4)
# ======================================================================


def generate_koevering_crossroads() -> dict:
    """Koevering Crossroads - Corridor defense (101st Airborne sector).

    Historical: On Sept 23-24, German forces cut the Hell's Highway corridor
    near Koevering between Veghel and St. Oedenrode. The 506th PIR and 502nd PIR
    fought to reopen the road. Terrain: rural crossroads with hedgerows, woods,
    and a single highway running through.

    Terrain: Rural crossroads, hedgerows, scattered woods
    Forces: Infantry vs infantry with artillery support
    Time: Day battle
    """
    tiles = _fill("grass")
    rng = random.Random(201)

    # Main highway north-south (Hell's Highway)
    for r in range(MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    # Cross road east-west
    for c in range(MAP_SIZE):
        tiles[10][c] = "road"

    # Junction buildings (Koevering hamlet)
    for r, c in [(8, 7), (8, 8), (9, 7), (11, 11), (11, 12), (12, 11), (12, 12)]:
        tiles[r][c] = "building_enterable"

    # Farmhouse cluster north
    for r, c in [(3, 4), (3, 5), (4, 4), (4, 5)]:
        tiles[r][c] = "building_enterable"

    # Farmhouse cluster south
    for r, c in [(15, 14), (15, 15), (16, 14), (16, 15)]:
        tiles[r][c] = "building_enterable"

    # Dense hedgerows along fields (Dutch polder landscape)
    for r in range(MAP_SIZE):
        if r not in (8, 9, 10, 11, 12):
            tiles[r][6] = "hedge"
            tiles[r][13] = "hedge"
    for c in range(MAP_SIZE):
        if c not in (8, 9, 10, 11, 12):
            tiles[7][c] = "hedge"
            tiles[13][c] = "hedge"

    # Woods patches (Zonsche Forest approach)
    _scatter(tiles, "woods", 12, rng, region=(0, 0, 6, 7))
    _scatter(tiles, "woods", 12, rng, region=(14, 0, 6, 7))
    _scatter(tiles, "woods", 10, rng, region=(0, 14, 6, 6))
    _scatter(tiles, "woods", 10, rng, region=(14, 14, 6, 6))

    # German defensive positions (rough = trenches/foxholes)
    tiles[6][8] = "rough"
    tiles[6][11] = "rough"
    tiles[14][8] = "rough"
    tiles[14][11] = "rough"

    return _make_map(
        "Koevering Crossroads - Corridor Defense",
        tiles,
        objectives=[
            {"id": "crossroads", "name": "Koevering Crossroads", "position": [9, 10], "type": "capture"},
            {"id": "highway_north", "name": "Highway North", "position": [10, 3], "type": "reach"},
        ],
        spawn_points=[
            {"id": "allied_south", "side": "friendly", "position": [10, 17], "units_max": 9},
            {"id": "axis_north", "side": "enemy", "position": [10, 2], "units_max": 9},
        ],
    )


def generate_st_oedenrode_bridge() -> dict:
    """St. Oedenrode Bridge - Dommel River bridges (101st Airborne sector).

    Historical: The 506th PIR was tasked with capturing two bridges over the
    Dommel River at St. Oedenrode. The town sits astride the highway with the
    river running through it. The bridges were captured intact on Sept 17.

    Terrain: Small river town, two bridges, urban buildings along riverbank
    Forces: Airborne infantry vs German garrison
    Time: Afternoon, Sept 17
    """
    tiles = _fill("grass")
    rng = random.Random(202)

    # Dommel River - winding horizontal water band rows 9-10
    for c in range(MAP_SIZE):
        tiles[9][c] = "water"
        tiles[10][c] = "water"

    # River bends slightly
    for c in range(0, 5):
        tiles[8][c] = "water"
    for c in range(15, MAP_SIZE):
        tiles[11][c] = "water"

    # Bridge 1 (western, road bridge) at columns 5-6
    for r in (9, 10):
        for c in (5, 6):
            tiles[r][c] = "bridge"

    # Bridge 2 (eastern, secondary bridge) at columns 14-15
    for r in (9, 10):
        for c in (14, 15):
            tiles[r][c] = "bridge"

    # Main road (Hell's Highway) north-south through western bridge
    for r in range(0, 9):
        tiles[r][5] = "road"
        tiles[r][6] = "road"
    for r in range(11, MAP_SIZE):
        tiles[r][5] = "road"
        tiles[r][6] = "road"

    # Secondary road through eastern bridge
    for r in range(0, 9):
        tiles[r][14] = "road"
        tiles[r][15] = "road"
    for r in range(11, MAP_SIZE):
        tiles[r][14] = "road"
        tiles[r][15] = "road"

    # Cross road on north bank connecting both bridges
    for c in range(5, 16):
        tiles[7][c] = "road"

    # Cross road on south bank
    for c in range(5, 16):
        tiles[12][c] = "road"

    # St. Oedenrode buildings on north bank
    for r, c in [(4, 3), (4, 4), (5, 3), (5, 4), (4, 8), (4, 9), (5, 8),
                 (5, 9), (4, 11), (4, 12), (5, 11), (5, 12)]:
        tiles[r][c] = "building_enterable"

    # Buildings on south bank
    for r, c in [(13, 3), (13, 4), (14, 3), (14, 4), (13, 8), (13, 9), (14, 8),
                 (14, 9), (13, 11), (13, 12), (14, 11), (14, 12)]:
        tiles[r][c] = "building_enterable"

    # Church (solid building)
    tiles[5][6] = "building_solid"
    tiles[5][7] = "building_solid"

    # Hedgerows along fields
    _scatter(tiles, "hedge", 15, rng, region=(0, 0, 5, 9))
    _scatter(tiles, "hedge", 15, rng, region=(15, 0, 5, 9))
    _scatter(tiles, "hedge", 15, rng, region=(0, 11, 5, 9))
    _scatter(tiles, "hedge", 15, rng, region=(15, 11, 5, 9))

    # Woods on edges
    _scatter(tiles, "woods", 8, rng, region=(0, 0, 3, 9))
    _scatter(tiles, "woods", 8, rng, region=(17, 0, 3, 9))

    return _make_map(
        "St. Oedenrode - Dommel River Bridges",
        tiles,
        objectives=[
            {"id": "west_bridge", "name": "West Bridge", "position": [5, 9], "type": "capture"},
            {"id": "east_bridge", "name": "East Bridge", "position": [14, 9], "type": "capture"},
            {"id": "town_center", "name": "Town Center", "position": [7, 5], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_north", "side": "friendly", "position": [6, 2], "units_max": 9},
            {"id": "axis_south", "side": "enemy", "position": [14, 17], "units_max": 9},
        ],
    )


def generate_willys_canal_crossing() -> dict:
    """Wilhelmina Canal Bailey Bridge - Emergency crossing (101st Airborne sector).

    Historical: After the Son bridge was destroyed by German demolition, XXX Corps
    engineers had to build a Bailey bridge across the Wilhelmina Canal. This took
    crucial hours, delaying the advance. The 506th PIR defended the crossing site
    while engineers worked under fire.

    Terrain: Canal with destroyed bridge remnants, construction area, defended perimeter
    Forces: Engineers + infantry defenders vs German harassing attacks
    Time: Night, Sept 17-18
    """
    tiles = _fill("grass")
    rng = random.Random(203)

    # Wilhelmina Canal - horizontal water band rows 8-11
    for r in range(8, 12):
        _horizontal_band(tiles, r, "water")

    # Destroyed bridge remnants (rough = rubble in water)
    tiles[9][9] = "rough"
    tiles[9][10] = "rough"
    tiles[10][9] = "rough"
    tiles[10][10] = "rough"

    # New Bailey bridge site at columns 12-13
    for r in range(8, 12):
        tiles[r][12] = "bridge"
        tiles[r][13] = "bridge"

    # Road approaching from north to new bridge
    for r in range(0, 8):
        tiles[r][12] = "road"
        tiles[r][13] = "road"

    # Road continuing south from new bridge
    for r in range(12, MAP_SIZE):
        tiles[r][12] = "road"
        tiles[r][13] = "road"

    # Old road to destroyed bridge (partially blocked)
    for r in range(0, 8):
        tiles[r][9] = "road"
        tiles[r][10] = "road"
    tiles[7][9] = "rough"  # Rubble blocking old road
    tiles[7][10] = "rough"

    # South bank old road
    for r in range(12, MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"
    tiles[12][9] = "rough"
    tiles[12][10] = "rough"

    # North bank buildings (Son village)
    for r, c in [(3, 5), (3, 6), (4, 5), (4, 6), (3, 15), (3, 16), (4, 15), (4, 16)]:
        tiles[r][c] = "building_enterable"

    # South bank buildings
    for r, c in [(14, 5), (14, 6), (15, 5), (15, 6), (14, 15), (14, 16), (15, 15), (15, 16)]:
        tiles[r][c] = "building_enterable"

    # Engineer equipment area (rough = construction materials)
    tiles[6][12] = "rough"
    tiles[6][13] = "rough"
    tiles[7][12] = "rough"

    # Defensive perimeter (rough = foxholes)
    for c in range(10, 16):
        tiles[7][c] = "rough"
    for c in range(10, 16):
        tiles[12][c] = "rough"

    # Hedges along canal banks
    _scatter(tiles, "hedge", 10, rng, region=(0, 0, 8, 8))
    _scatter(tiles, "hedge", 10, rng, region=(12, 0, 8, 8))
    _scatter(tiles, "hedge", 10, rng, region=(0, 12, 8, 8))
    _scatter(tiles, "hedge", 10, rng, region=(12, 12, 8, 8))

    # Woods
    _scatter(tiles, "woods", 8, rng, region=(0, 0, 4, 8))
    _scatter(tiles, "woods", 8, rng, region=(16, 0, 4, 8))

    return _make_map(
        "Wilhelmina Canal - Bailey Bridge",
        tiles,
        objectives=[
            {"id": "bailey_bridge", "name": "Bailey Bridge", "position": [12, 9], "type": "defend"},
            {"id": "construction", "name": "Construction Site", "position": [13, 7], "type": "defend"},
        ],
        spawn_points=[
            {"id": "allied_north", "side": "friendly", "position": [12, 2], "units_max": 9},
            {"id": "axis_south", "side": "enemy", "position": [12, 17], "units_max": 9},
        ],
    )


def generate_driel_landing_zone() -> dict:
    """Driel Landing Zone - Polish brigade drop (101st/1st Airborne sector).

    Historical: The Polish 1st Independent Parachute Brigade was dropped near
    Driel on the south bank of the Rhine on Sept 21, but could not cross to
    reinforce the British at Oosterbeek. The landing zone was under German fire.

    Terrain: Open fields (landing zone), river to north, village, scattered woods
    Forces: Polish airborne infantry vs German units blocking river crossing
    Time: Afternoon, Sept 21
    """
    tiles = _fill("grass")
    rng = random.Random(204)

    # Rhine River on north edge (rows 0-3)
    for r in range(0, 4):
        _horizontal_band(tiles, r, "water")

    # Shallow crossing attempt point
    tiles[3][9] = "shallow"
    tiles[3][10] = "shallow"

    # South bank road (running east-west)
    for c in range(MAP_SIZE):
        tiles[8][c] = "road"

    # North-south road to river
    for r in range(4, MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    # Driel village buildings
    for r, c in [(10, 4), (10, 5), (11, 4), (11, 5),
                 (10, 14), (10, 15), (11, 14), (11, 15)]:
        tiles[r][c] = "building_enterable"

    # Church in Driel
    tiles[10][9] = "building_solid"
    tiles[10][10] = "building_solid"

    # Landing zone markers (open = flat drop zone, already grass)
    # Clear the landing zone area (rows 5-7, cols 3-16)
    for r in range(5, 8):
        for c in range(3, 17):
            tiles[r][c] = "open"

    # German positions on north bank (rough = entrenchments)
    for c in range(6, 14):
        tiles[4][c] = "rough"

    # Hedges along fields
    _scatter(tiles, "hedge", 15, rng, region=(0, 9, 9, 11))
    _scatter(tiles, "hedge", 15, rng, region=(11, 9, 9, 11))

    # Woods patches
    _scatter(tiles, "woods", 10, rng, region=(0, 9, 3, 11))
    _scatter(tiles, "woods", 10, rng, region=(17, 9, 3, 11))

    # Rough patches (shell craters on LZ)
    _scatter(tiles, "rough", 6, rng, region=(3, 5, 14, 3))

    return _make_map(
        "Driel Landing Zone - Polish Brigade",
        tiles,
        objectives=[
            {"id": "river_crossing", "name": "River Crossing Point", "position": [9, 3], "type": "reach"},
            {"id": "driel_village", "name": "Driel Village", "position": [9, 10], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_south", "side": "friendly", "position": [10, 17], "units_max": 9},
            {"id": "axis_north", "side": "enemy", "position": [10, 4], "units_max": 9},
        ],
    )


# ======================================================================
# 82nd Airborne - Additional Maps (4)
# ======================================================================


def generate_maas_waal_canal() -> dict:
    """Maas-Waal Canal Crossing - 504th PIR assault (82nd Airborne sector).

    Historical: On Sept 17, the 504th PIR captured bridges over the Maas-Waal
    Canal at Heumen. The canal is a significant water obstacle with multiple
    bridges. German defenders had prepared demolitions but the paratroopers
    arrived too quickly.

    Terrain: Linear canal with multiple bridges, flat polder land, approach roads
    Forces: Airborne infantry assault vs German defenders with demo charges
    Time: Afternoon, Sept 17
    """
    tiles = _fill("grass")
    rng = random.Random(205)

    # Maas-Waal Canal running diagonally (simplified as horizontal rows 8-10)
    for r in (8, 9, 10):
        _horizontal_band(tiles, r, "water")

    # Bridge 1 at columns 4-5 (Heumen bridge)
    for r in (8, 9, 10):
        for c in (4, 5):
            tiles[r][c] = "bridge"

    # Bridge 2 at columns 14-15 (secondary crossing)
    for r in (8, 9, 10):
        for c in (14, 15):
            tiles[r][c] = "bridge"

    # Road to bridge 1 from south
    for r in range(11, MAP_SIZE):
        tiles[r][4] = "road"
        tiles[r][5] = "road"

    # Road from bridge 1 to north
    for r in range(0, 8):
        tiles[r][4] = "road"
        tiles[r][5] = "road"

    # Road to bridge 2 from south
    for r in range(11, MAP_SIZE):
        tiles[r][14] = "road"
        tiles[r][15] = "road"

    # Road from bridge 2 to north
    for r in range(0, 8):
        tiles[r][14] = "road"
        tiles[r][15] = "road"

    # Cross road on north bank
    for c in range(4, 16):
        tiles[5][c] = "road"

    # Cross road on south bank
    for c in range(4, 16):
        tiles[13][c] = "road"

    # Heumen buildings near bridge 1
    for r, c in [(3, 2), (3, 3), (4, 2), (4, 3), (3, 7), (3, 8), (4, 7)]:
        tiles[r][c] = "building_enterable"

    # Buildings near bridge 2
    for r, c in [(3, 12), (3, 13), (4, 12), (3, 17), (3, 18), (4, 17)]:
        tiles[r][c] = "building_enterable"

    # South bank buildings
    for r, c in [(15, 2), (15, 3), (16, 2), (15, 12), (15, 13), (16, 12)]:
        tiles[r][c] = "building_enterable"

    # German demo preparation positions (rough)
    tiles[8][3] = "rough"
    tiles[8][6] = "rough"
    tiles[8][13] = "rough"
    tiles[8][16] = "rough"

    # Flat polder fields (hedges)
    _scatter(tiles, "hedge", 12, rng, region=(0, 0, 4, 8))
    _scatter(tiles, "hedge", 12, rng, region=(16, 0, 4, 8))
    _scatter(tiles, "hedge", 12, rng, region=(0, 11, 4, 9))
    _scatter(tiles, "hedge", 12, rng, region=(16, 11, 4, 9))

    return _make_map(
        "Maas-Waal Canal - 504th PIR Crossing",
        tiles,
        objectives=[
            {"id": "heumen_bridge", "name": "Heumen Bridge", "position": [4, 9], "type": "capture"},
            {"id": "secondary_bridge", "name": "Secondary Bridge", "position": [14, 9], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_south", "side": "friendly", "position": [5, 17], "units_max": 9},
            {"id": "axis_north", "side": "enemy", "position": [5, 2], "units_max": 9},
        ],
    )


def generate_molenhoek_ridge() -> dict:
    """Molenhoek Ridge - Height defense (82nd Airborne sector).

    Historical: German counterattacks from the Reichswald forest toward
    Groesbeek threatened the 82nd's positions. The Molenhoek area saw
    fighting as the 505th PIR defended the southern approaches to the
    Groesbeek heights.

    Terrain: Ridge/heights with rough terrain, forest on one side, open fields
    Forces: Infantry defense vs German infantry with armor support
    Time: Day, Sept 18-19
    """
    tiles = _fill("grass")
    rng = random.Random(206)

    # Ridge running east-west (rough terrain = elevated)
    for c in range(2, 18):
        tiles[6][c] = "rough"
        tiles[7][c] = "rough"
    # Ridge peak
    for c in range(4, 16):
        tiles[5][c] = "rough"

    # Road along ridge
    for c in range(MAP_SIZE):
        tiles[6][c] = "road"
        tiles[7][c] = "road"

    # Reichswald Forest on the east side (dense woods)
    for r in range(0, 6):
        for c in range(14, MAP_SIZE):
            if rng.random() < 0.7:
                tiles[r][c] = "woods"
    for r in range(8, MAP_SIZE):
        for c in range(14, MAP_SIZE):
            if rng.random() < 0.5:
                tiles[r][c] = "woods"

    # Molenhoek village on ridge
    for r, c in [(5, 7), (5, 8), (6, 7), (8, 7), (8, 8), (9, 7)]:
        tiles[r][c] = "building_enterable"

    # Observation post on ridge
    tiles[5][10] = "building_solid"

    # Defensive positions on ridge (rough = trenches)
    tiles[5][4] = "rough"
    tiles[5][13] = "rough"
    tiles[8][4] = "rough"
    tiles[8][13] = "rough"

    # South approach - open fields with hedges
    _scatter(tiles, "hedge", 20, rng, region=(0, 10, 14, 10))

    # West woods
    _scatter(tiles, "woods", 10, rng, region=(0, 0, 4, 6))
    _scatter(tiles, "woods", 10, rng, region=(0, 8, 4, 12))

    # South road approach
    for r in range(10, MAP_SIZE):
        tiles[r][7] = "road"
        tiles[r][8] = "road"

    return _make_map(
        "Molenhoek Ridge - Height Defense",
        tiles,
        objectives=[
            {"id": "ridge", "name": "Molenhoek Ridge", "position": [10, 6], "type": "defend"},
            {"id": "obs_post", "name": "Observation Post", "position": [10, 5], "type": "defend"},
        ],
        spawn_points=[
            {"id": "allied_ridge", "side": "friendly", "position": [8, 6], "units_max": 9},
            {"id": "axis_south", "side": "enemy", "position": [8, 17], "units_max": 9},
        ],
    )


def generate_honinghutie_road() -> dict:
    """Honinghutie Road Block - Corridor defense (82nd Airborne sector).

    Historical: German forces repeatedly attempted to cut the Hell's Highway
    corridor. Near Honinghutie/Mook, the 82nd defended against attacks from
    the west. The road was the lifeline for XXX Corps supplies.

    Terrain: Single highway, woods on both sides, defensive positions
    Forces: Infantry defense vs German probing attacks
    Time: Night, Sept 20-21
    """
    tiles = _fill("grass")
    rng = random.Random(207)

    # Main highway (Hell's Highway) north-south
    for r in range(MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    # Dense woods on both sides of highway (ambush terrain)
    _scatter(tiles, "woods", 60, rng, region=(0, 0, 8, MAP_SIZE))
    _scatter(tiles, "woods", 60, rng, region=(12, 0, 8, MAP_SIZE))

    # Clear road corridor
    for r in range(MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"
        tiles[r][8] = "grass"
        tiles[r][11] = "grass"

    # Roadblock position (rough)
    tiles[10][8] = "rough"
    tiles[10][11] = "rough"
    tiles[9][8] = "rough"
    tiles[9][11] = "rough"

    # Small clearing for checkpoint
    for r in range(8, 12):
        for c in range(7, 13):
            if tiles[r][c] == "woods":
                tiles[r][c] = "grass"

    # Checkpoint building
    tiles[9][7] = "building_enterable"
    tiles[10][12] = "building_enterable"

    # Cross path through woods (German approach)
    for r in range(5, 15):
        tiles[r][4] = "grass"
        tiles[r][15] = "grass"

    # Hedges along road
    for r in range(MAP_SIZE):
        if r not in (8, 9, 10, 11):
            tiles[r][7] = "hedge"
            tiles[r][12] = "hedge"

    return _make_map(
        "Honinghutie Road Block - Corridor Defense",
        tiles,
        objectives=[
            {"id": "roadblock", "name": "Road Block", "position": [9, 10], "type": "defend"},
            {"id": "highway_north", "name": "Highway North", "position": [10, 3], "type": "reach"},
        ],
        spawn_points=[
            {"id": "allied_road", "side": "friendly", "position": [10, 15], "units_max": 9},
            {"id": "axis_west", "side": "enemy", "position": [2, 5], "units_max": 9},
        ],
    )


def generate_devils_hill() -> dict:
    """Devil's Hill - Key terrain near Groesbeek (82nd Airborne sector).

    Historical: The Groesbeek heights were critical terrain that the 82nd
    was ordered to hold. The high ground provided observation over the
    Reichswald forest and the Maas river valley. German counterattacks
    sought to recapture this key terrain.

    Terrain: Prominent hill with steep slopes, observation posts, surrounding forest
    Forces: Infantry holding heights vs German counterattack with armor
    Time: Day, Sept 19
    """
    tiles = _fill("grass")
    rng = random.Random(208)

    # Hill in center (rough terrain = elevated/stony ground)
    for r in range(5, 12):
        for c in range(5, 15):
            if rng.random() < 0.65:
                tiles[r][c] = "rough"

    # Hill peak area (concentrated rough)
    for r in range(6, 10):
        for c in range(7, 13):
            tiles[r][c] = "rough"

    # Road through the heights
    for c in range(MAP_SIZE):
        tiles[8][c] = "road"

    # Approach road from south
    for r in range(12, MAP_SIZE):
        tiles[r][10] = "road"
        tiles[r][11] = "road"

    # Observation posts on peak
    tiles[6][9] = "building_solid"
    tiles[6][10] = "building_solid"

    # Farm buildings on heights
    for r, c in [(7, 6), (7, 7), (9, 12), (9, 13)]:
        tiles[r][c] = "building_enterable"

    # Reichswald Forest to the east
    for r in range(0, 5):
        for c in range(14, MAP_SIZE):
            tiles[r][c] = "woods"
    for r in range(12, MAP_SIZE):
        for c in range(14, MAP_SIZE):
            tiles[r][c] = "woods"

    # Woods on west flank
    _scatter(tiles, "woods", 15, rng, region=(0, 0, 5, 5))
    _scatter(tiles, "woods", 15, rng, region=(0, 12, 5, 8))

    # Hedgerows on lower ground
    _scatter(tiles, "hedge", 20, rng, region=(0, 12, 14, 8))

    # German approach from east through forest
    for r in range(3, 8):
        tiles[r][16] = "grass"  # Path through woods

    return _make_map(
        "Devil's Hill - Groesbeek Heights",
        tiles,
        objectives=[
            {"id": "summit", "name": "Hill Summit", "position": [10, 7], "type": "defend"},
            {"id": "obs_post", "name": "Observation Post", "position": [9, 6], "type": "defend"},
        ],
        spawn_points=[
            {"id": "allied_heights", "side": "friendly", "position": [10, 8], "units_max": 9},
            {"id": "axis_east", "side": "enemy", "position": [17, 3], "units_max": 9},
        ],
    )


# ======================================================================
# British 1st Airborne - Additional Maps (4)
# ======================================================================


def generate_westerbouwing_heights() -> dict:
    """Westerbouwing Heights - Key terrain south of Oosterbeek (British 1st Airborne).

    Historical: The Westerbouwing heights overlooked the Oosterbeek perimeter
    from the south. This high ground was supposed to be held but was lost to
    German forces, giving them observation over the British positions and the
    Rhine crossing points. Its loss severely compromised the perimeter defense.

    Terrain: Elevated plateau with steep slopes, river on one side, woods
    Forces: British infantry (understrength) vs German assault
    Time: Day, Sept 22-23
    """
    tiles = _fill("grass")
    rng = random.Random(209)

    # Rhine River along the north edge (rows 0-2)
    for r in range(0, 3):
        _horizontal_band(tiles, r, "water")

    # Westerbouwing heights - elevated terrain (rough) in center-south
    for r in range(5, 14):
        for c in range(3, 17):
            if rng.random() < 0.55:
                tiles[r][c] = "rough"

    # Steep slopes on north side of heights
    for c in range(4, 16):
        tiles[4][c] = "rough"

    # Road along the ridge
    for c in range(2, 18):
        tiles[8][c] = "road"

    # Restaurant/building on heights (famous Westerbouwing restaurant)
    tiles[7][9] = "building_solid"
    tiles[7][10] = "building_solid"
    tiles[7][11] = "building_solid"
    tiles[8][9] = "building_enterable"
    tiles[8][10] = "building_enterable"

    # British defensive positions (rough = trenches)
    for c in range(5, 15):
        tiles[5][c] = "rough"

    # Woods on the heights
    _scatter(tiles, "woods", 12, rng, region=(3, 5, 6, 5))
    _scatter(tiles, "woods", 12, rng, region=(11, 5, 6, 5))

    # Woods at base of heights
    _scatter(tiles, "woods", 10, rng, region=(0, 14, 10, 6))
    _scatter(tiles, "woods", 10, rng, region=(10, 14, 10, 6))

    # South approach road
    for r in range(14, MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    # Hedges on lower ground
    _scatter(tiles, "hedge", 15, rng, region=(0, 14, 10, 6))
    _scatter(tiles, "hedge", 15, rng, region=(10, 14, 10, 6))

    return _make_map(
        "Westerbouwing Heights - Overlook Position",
        tiles,
        objectives=[
            {"id": "heights", "name": "Westerbouwing Heights", "position": [10, 7], "type": "defend"},
            {"id": "restaurant", "name": "Westerbouwing Restaurant", "position": [10, 7], "type": "defend"},
        ],
        spawn_points=[
            {"id": "allied_north", "side": "friendly", "position": [10, 5], "units_max": 9},
            {"id": "axis_south", "side": "enemy", "position": [10, 17], "units_max": 9},
        ],
    )


def generate_arnhem_railway_bridge() -> dict:
    """Arnhem Railway Bridge - Bridge capture attempt (British 1st Airborne).

    Historical: The 1st Airborne was tasked with capturing three bridges:
    the road bridge, the railway bridge, and a pontoon bridge. The railway
    bridge was reached by elements of 1st Parachute Brigade but was blown
    by the Germans as they approached.

    Terrain: Railway bridge over Rhine, rail yards, urban approach
    Forces: British paratroopers vs German demolition guards
    Time: Evening, Sept 17
    """
    tiles = _fill("grass")
    rng = random.Random(210)

    # Rhine River rows 8-11
    for r in range(8, 12):
        _horizontal_band(tiles, r, "water")

    # Railway bridge at columns 5-6
    for r in range(8, 12):
        for c in (5, 6):
            tiles[r][c] = "bridge"

    # Railway line approaching bridge (north bank)
    for r in range(0, 8):
        tiles[r][5] = "road"  # Using road for rail line
        tiles[r][6] = "road"

    # Railway line south of bridge
    for r in range(12, MAP_SIZE):
        tiles[r][5] = "road"
        tiles[r][6] = "road"

    # Rail yard buildings (north bank)
    for r, c in [(3, 3), (3, 4), (4, 3), (4, 4), (3, 8), (3, 9), (4, 8), (4, 9)]:
        tiles[r][c] = "building_solid"

    # Rail yard buildings (south bank)
    for r, c in [(14, 3), (14, 4), (15, 3), (15, 4), (14, 8), (14, 9), (15, 8), (15, 9)]:
        tiles[r][c] = "building_solid"

    # Urban buildings near rail approach
    for r, c in [(2, 11), (2, 12), (3, 11), (3, 12), (5, 11), (5, 12), (6, 11), (6, 12)]:
        tiles[r][c] = "building_enterable"

    # German demo positions (rough = prepared positions)
    tiles[7][4] = "rough"
    tiles[7][7] = "rough"
    tiles[12][4] = "rough"
    tiles[12][7] = "rough"

    # Rubble from demolished sections
    tiles[8][5] = "rough"
    tiles[8][6] = "rough"

    # Hedges
    _scatter(tiles, "hedge", 10, rng, region=(0, 0, 5, 8))
    _scatter(tiles, "hedge", 10, rng, region=(13, 0, 7, 8))
    _scatter(tiles, "hedge", 10, rng, region=(0, 12, 5, 8))
    _scatter(tiles, "hedge", 10, rng, region=(13, 12, 7, 8))

    # Woods
    _scatter(tiles, "woods", 8, rng, region=(14, 0, 6, 8))
    _scatter(tiles, "woods", 8, rng, region=(14, 12, 6, 8))

    return _make_map(
        "Arnhem Railway Bridge - Demolition",
        tiles,
        objectives=[
            {"id": "rail_bridge", "name": "Railway Bridge", "position": [5, 9], "type": "capture"},
            {"id": "north_approach", "name": "North Rail Approach", "position": [6, 4], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_north", "side": "friendly", "position": [6, 2], "units_max": 9},
            {"id": "axis_south", "side": "enemy", "position": [6, 17], "units_max": 9},
        ],
    )


def generate_oosterbeek_church() -> dict:
    """Oosterbeek Church - Last strongpoint (British 1st Airborne).

    Historical: During the Oosterbeek perimeter defense, the church in
    Oosterbeek served as a key strongpoint and aid post. The perimeter
    shrank steadily under German pressure. The church area saw intense
    fighting as one of the last defensible positions before the Rhine.

    Terrain: Village center with church, surrounding buildings, perimeter trenches
    Forces: British infantry (exhausted) vs German methodical assault
    Time: Day, Sept 24-25
    """
    tiles = _fill("grass")
    rng = random.Random(211)

    # Main road through Oosterbeek
    for c in range(MAP_SIZE):
        tiles[10][c] = "road"

    # Cross road
    for r in range(MAP_SIZE):
        tiles[r][10] = "road"

    # Church complex (prominent solid buildings)
    tiles[8][9] = "building_solid"
    tiles[8][10] = "building_solid"
    tiles[9][9] = "building_solid"
    tiles[9][10] = "building_solid"

    # Church yard (open area around church)
    for r in range(7, 11):
        for c in range(8, 12):
            if tiles[r][c] not in ("building_solid", "road"):
                tiles[r][c] = "open"

    # Surrounding village buildings
    for r, c in [(5, 5), (5, 6), (6, 5), (6, 6),
                 (5, 13), (5, 14), (6, 13), (6, 14),
                 (13, 5), (13, 6), (14, 5), (14, 6),
                 (13, 13), (13, 14), (14, 13), (14, 14)]:
        tiles[r][c] = "building_enterable"

    # Destroyed buildings (rubble)
    tiles[7][7] = "building_solid"
    tiles[7][12] = "building_solid"
    tiles[12][7] = "building_solid"
    tiles[12][12] = "building_solid"

    # Perimeter trenches (rough)
    for c in range(3, 17):
        tiles[3][c] = "rough"
        tiles[16][c] = "rough"
    for r in range(3, 17):
        tiles[r][3] = "rough"
        tiles[r][16] = "rough"

    # Rubble in streets
    _scatter(tiles, "rough", 12, rng)

    # Hedges
    _scatter(tiles, "hedge", 15, rng, region=(0, 0, 3, MAP_SIZE))
    _scatter(tiles, "hedge", 15, rng, region=(17, 0, 3, MAP_SIZE))

    # Woods at edges
    _scatter(tiles, "woods", 8, rng, region=(0, 0, 3, 3))
    _scatter(tiles, "woods", 8, rng, region=(17, 0, 3, 3))
    _scatter(tiles, "woods", 8, rng, region=(0, 17, 3, 3))
    _scatter(tiles, "woods", 8, rng, region=(17, 17, 3, 3))

    return _make_map(
        "Oosterbeek Church - Last Strongpoint",
        tiles,
        objectives=[
            {"id": "church", "name": "Oosterbeek Church", "position": [9, 8], "type": "defend"},
            {"id": "village_center", "name": "Village Center", "position": [10, 10], "type": "defend"},
        ],
        spawn_points=[
            {"id": "allied_church", "side": "friendly", "position": [10, 9], "units_max": 9},
            {"id": "axis_outside", "side": "enemy", "position": [3, 3], "units_max": 9},
        ],
    )


def generate_driel_polish_crossing() -> dict:
    """Driel Polish Crossing - River assault (British 1st Airborne / Polish Brigade).

    Historical: On the night of Sept 24-25, the Polish 1st Independent Parachute
    Brigade attempted to cross the Rhine at Driel to reinforce the Oosterbeek
    perimeter. Only a small number made it across under intense German fire.
    This was part of the final evacuation effort.

    Terrain: Wide river, single crossing point, defended far bank, village on near bank
    Forces: Polish infantry vs German defenders on far bank
    Time: Night, Sept 24-25
    """
    tiles = _fill("grass")
    rng = random.Random(212)

    # Wide Rhine River rows 6-13
    for r in range(6, 14):
        _horizontal_band(tiles, r, "water")

    # Crossing point (shallow water at cols 9-10)
    for r in range(6, 14):
        tiles[r][9] = "shallow"
        tiles[r][10] = "shallow"

    # North bank - German defensive positions
    for c in range(5, 15):
        tiles[5][c] = "rough"  # German trenches overlooking river

    # German bunkers on north bank
    tiles[4][8] = "building_solid"
    tiles[4][11] = "building_solid"
    tiles[5][9] = "building_solid"
    tiles[5][10] = "building_solid"

    # North bank road
    for c in range(MAP_SIZE):
        tiles[3][c] = "road"

    # North bank buildings
    for r, c in [(1, 5), (1, 6), (2, 5), (2, 6), (1, 13), (1, 14), (2, 13), (2, 14)]:
        tiles[r][c] = "building_enterable"

    # South bank - Driel village
    for r, c in [(15, 5), (15, 6), (16, 5), (16, 6),
                 (15, 13), (15, 14), (16, 13), (16, 14)]:
        tiles[r][c] = "building_enterable"

    # South bank road to crossing
    for r in range(14, MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    # South bank cross road
    for c in range(MAP_SIZE):
        tiles[16][c] = "road"

    # Woods on south bank flanks
    _scatter(tiles, "woods", 12, rng, region=(0, 14, 5, 6))
    _scatter(tiles, "woods", 12, rng, region=(15, 14, 5, 6))

    # Hedges on south bank
    _scatter(tiles, "hedge", 10, rng, region=(0, 14, 5, 6))
    _scatter(tiles, "hedge", 10, rng, region=(15, 14, 5, 6))

    # Rough patches (shell craters near crossing)
    _scatter(tiles, "rough", 6, rng, region=(7, 14, 6, 2))

    return _make_map(
        "Driel Polish Crossing - Rhine Assault",
        tiles,
        objectives=[
            {"id": "north_bank", "name": "North Bank Landing", "position": [9, 5], "type": "reach"},
            {"id": "crossing", "name": "River Crossing", "position": [9, 9], "type": "reach"},
        ],
        spawn_points=[
            {"id": "allied_south", "side": "friendly", "position": [10, 17], "units_max": 9},
            {"id": "axis_north", "side": "enemy", "position": [10, 2], "units_max": 9},
        ],
    )


# ======================================================================
# XXX Corps - Additional Maps (4)
# ======================================================================


def generate_valkenswaard_woods() -> dict:
    """Valkenswaard Woods - Irish Guards engagement (XXX Corps sector).

    Historical: On Sept 17, the Irish Guards Group spearheaded XXX Corps'
    advance from Joe's Bridge. The 7-mile advance to Valkenswaard took all
    afternoon due to German anti-tank positions in the dense woods flanking
    the road. Tanks could not deploy off-road in the marshy, wooded terrain.

    Terrain: Single road through dense woods, marshy ground, anti-tank positions
    Forces: Armor + infantry vs German anti-tank guns in woods
    Time: Afternoon, Sept 17
    """
    tiles = _fill("grass")
    rng = random.Random(213)

    # Main highway (Hell's Highway) running north-south
    for r in range(MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"

    # Dense woods on both sides of road
    _scatter(tiles, "woods", 100, rng, region=(0, 0, 8, MAP_SIZE))
    _scatter(tiles, "woods", 100, rng, region=(12, 0, 8, MAP_SIZE))

    # Clear road corridor
    for r in range(MAP_SIZE):
        tiles[r][9] = "road"
        tiles[r][10] = "road"
        tiles[r][8] = "grass"
        tiles[r][11] = "grass"

    # Valkenswaard village at north end
    for r, c in [(2, 7), (2, 8), (3, 7), (3, 8), (2, 11), (2, 12), (3, 11), (3, 12)]:
        tiles[r][c] = "building_enterable"

    # Church in Valkenswaard
    tiles[1][9] = "building_solid"
    tiles[1][10] = "building_solid"

    # German anti-tank positions in woods (rough = prepared positions)
    tiles[6][6] = "rough"
    tiles[6][13] = "rough"
    tiles[10][5] = "rough"
    tiles[10][14] = "rough"
    tiles[14][6] = "rough"
    tiles[14][13] = "rough"

    # Marshy ground near road (shallow = marshy polder)
    tiles[8][7] = "shallow"
    tiles[8][12] = "shallow"
    tiles[12][7] = "shallow"
    tiles[12][12] = "shallow"

    # Small clearings in woods
    for r in range(4, 7):
        for c in range(3, 6):
            tiles[r][c] = "grass"
    for r in range(13, 16):
        for c in range(14, 17):
            tiles[r][c] = "grass"

    # Hedges at village edge
    _scatter(tiles, "hedge", 8, rng, region=(6, 0, 6, 4))

    return _make_map(
        "Valkenswaard Woods - Irish Guards Advance",
        tiles,
        objectives=[
            {"id": "village", "name": "Valkenswaard Village", "position": [9, 2], "type": "capture"},
            {"id": "road_south", "name": "Road South", "position": [10, 17], "type": "reach"},
        ],
        spawn_points=[
            {"id": "allied_south", "side": "friendly", "position": [10, 18], "units_max": 9},
            {"id": "axis_north", "side": "enemy", "position": [9, 1], "units_max": 9},
        ],
    )


def generate_aalsmeer_flank() -> dict:
    """Aalsmeer Flank - Corridor side attack (XXX Corps sector).

    Historical: German forces repeatedly attacked the flanks of the Hell's
    Highway corridor. From positions west of the road, German units would
    cross the corridor, cut the road, and isolate units. These flank attacks
    were a constant threat throughout the operation.

    Terrain: Open farmland with drainage ditches, single road, scattered farms
    Forces: Infantry + armor vs German flank attack
    Time: Day, Sept 22
    """
    tiles = _fill("grass")
    rng = random.Random(214)

    # Main highway north-south
    for r in range(MAP_SIZE):
        tiles[r][10] = "road"
        tiles[r][11] = "road"

    # Drainage ditches (shallow water) running east-west
    for c in range(MAP_SIZE):
        tiles[5][c] = "shallow"
        tiles[14][c] = "shallow"

    # Crossing points on ditches (road crosses)
    tiles[5][10] = "road"
    tiles[5][11] = "road"
    tiles[14][10] = "road"
    tiles[14][11] = "road"

    # Farm buildings (west side)
    for r, c in [(3, 3), (3, 4), (4, 3), (4, 4), (8, 2), (8, 3), (9, 2), (9, 3)]:
        tiles[r][c] = "building_enterable"

    # Farm buildings (east side)
    for r, c in [(3, 15), (3, 16), (4, 15), (4, 16), (8, 16), (8, 17), (9, 16), (9, 17)]:
        tiles[r][c] = "building_enterable"

    # Cross roads connecting farms to highway
    for r in range(3, 6):
        tiles[r][3] = "road"
    for r in range(6, 15):
        tiles[r][2] = "road"
    for r in range(3, 6):
        tiles[r][16] = "road"
    for r in range(6, 15):
        tiles[r][17] = "road"

    # Hedgerows along field boundaries
    _scatter(tiles, "hedge", 25, rng, region=(0, 0, 10, 5))
    _scatter(tiles, "hedge", 25, rng, region=(12, 0, 8, 5))
    _scatter(tiles, "hedge", 25, rng, region=(0, 6, 10, 8))
    _scatter(tiles, "hedge", 25, rng, region=(12, 6, 8, 8))
    _scatter(tiles, "hedge", 20, rng, region=(0, 15, 10, 5))
    _scatter(tiles, "hedge", 20, rng, region=(12, 15, 8, 5))

    # Woods patches
    _scatter(tiles, "woods", 8, rng, region=(0, 0, 3, 5))
    _scatter(tiles, "woods", 8, rng, region=(17, 0, 3, 5))

    # German approach from west
    tiles[10][0] = "rough"
    tiles[10][1] = "rough"

    return _make_map(
        "Aalsmeer Flank - Corridor Side Attack",
        tiles,
        objectives=[
            {"id": "highway", "name": "Highway Crossing", "position": [10, 10], "type": "defend"},
            {"id": "west_farm", "name": "West Farm", "position": [3, 8], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_east", "side": "friendly", "position": [16, 10], "units_max": 9},
            {"id": "axis_west", "side": "enemy", "position": [1, 10], "units_max": 9},
        ],
    )


def generate_venray_tank_battle() -> dict:
    """Venray Tank Battle - Armor engagement (XXX Corps sector).

    Historical: After the Overloon battle (Oct 1944, outside Market Garden
    timeframe but on the same front), XXX Corps continued pushing toward
    Venray. The terrain was open polder land with scattered villages,
    favorable for tank engagements but with minefields and anti-tank ditches.

    Terrain: Open polder farmland, scattered buildings, anti-tank obstacles
    Forces: British armor + infantry vs German armor + anti-tank
    Time: Day
    """
    tiles = _fill("grass")
    rng = random.Random(215)

    # Main road east-west
    for c in range(MAP_SIZE):
        tiles[10][c] = "road"

    # Cross road north-south
    for r in range(MAP_SIZE):
        tiles[r][10] = "road"

    # Anti-tank ditch (rough terrain) running parallel to main road
    for c in range(2, 18):
        tiles[7][c] = "rough"

    # Crossing points over anti-tank ditch
    tiles[7][10] = "road"

    # Venray village buildings (north)
    for r, c in [(3, 8), (3, 9), (4, 8), (4, 9),
                 (3, 12), (3, 13), (4, 12), (4, 13)]:
        tiles[r][c] = "building_enterable"

    # Church in Venray
    tiles[2][10] = "building_solid"
    tiles[2][11] = "building_solid"

    # South hamlet
    for r, c in [(15, 8), (15, 9), (16, 8), (16, 9),
                 (15, 12), (15, 13), (16, 12), (16, 13)]:
        tiles[r][c] = "building_enterable"

    # Minefields (rough patches)
    _scatter(tiles, "rough", 15, rng, region=(0, 8, 10, 2))
    _scatter(tiles, "rough", 15, rng, region=(0, 12, 10, 2))

    # Scattered hedgerows (Dutch polder)
    _scatter(tiles, "hedge", 20, rng, region=(0, 0, 8, 7))
    _scatter(tiles, "hedge", 20, rng, region=(12, 0, 8, 7))
    _scatter(tiles, "hedge", 20, rng, region=(0, 13, 8, 7))
    _scatter(tiles, "hedge", 20, rng, region=(12, 13, 8, 7))

    # Small woods
    _scatter(tiles, "woods", 6, rng, region=(0, 0, 3, 7))
    _scatter(tiles, "woods", 6, rng, region=(17, 0, 3, 7))
    _scatter(tiles, "woods", 6, rng, region=(0, 13, 3, 7))
    _scatter(tiles, "woods", 6, rng, region=(17, 13, 3, 7))

    return _make_map(
        "Venray Tank Battle - Armor Engagement",
        tiles,
        objectives=[
            {"id": "village", "name": "Venray Village", "position": [10, 3], "type": "capture"},
            {"id": "crossroads", "name": "Crossroads", "position": [10, 10], "type": "capture"},
        ],
        spawn_points=[
            {"id": "allied_south", "side": "friendly", "position": [10, 17], "units_max": 9},
            {"id": "axis_north", "side": "enemy", "position": [10, 2], "units_max": 9},
        ],
    )


def generate_nederweert_canal() -> dict:
    """Nederweert Canal - Canal defense (XXX Corps sector).

    Historical: The corridor west of Hell's Highway needed protection.
    At Nederweert, canals provided natural defensive positions. German
    probes from the west sought weak points in the Allied line along
    these water obstacles.

    Terrain: Canal with limited crossings, flat farmland, defensive positions
    Forces: Infantry defense vs German probe
    Time: Day, Sept 21
    """
    tiles = _fill("grass")
    rng = random.Random(216)

    # Canal running north-south through center (cols 8-9)
    for r in range(MAP_SIZE):
        tiles[r][8] = "water"
        tiles[r][9] = "water"

    # Bridge at row 5
    tiles[5][8] = "bridge"
    tiles[5][9] = "bridge"

    # Bridge at row 14
    tiles[14][8] = "bridge"
    tiles[14][9] = "bridge"

    # Road approaching north bridge from west
    for c in range(0, 8):
        tiles[5][c] = "road"

    # Road from north bridge to east
    for c in range(10, MAP_SIZE):
        tiles[5][c] = "road"

    # Road approaching south bridge from west
    for c in range(0, 8):
        tiles[14][c] = "road"

    # Road from south bridge to east
    for c in range(10, MAP_SIZE):
        tiles[14][c] = "road"

    # East bank road (Hell's Highway direction)
    for r in range(MAP_SIZE):
        tiles[r][12] = "road"
        tiles[r][13] = "road"

    # Cross roads connecting bridges to main road
    for r in range(5, 15):
        tiles[r][10] = "road"
        tiles[r][11] = "road"

    # Nederweert village on east bank
    for r, c in [(3, 14), (3, 15), (4, 14), (4, 15),
                 (7, 15), (7, 16), (8, 15), (8, 16)]:
        tiles[r][c] = "building_enterable"

    # West bank farmhouses
    for r, c in [(3, 3), (3, 4), (4, 3), (4, 4),
                 (10, 2), (10, 3), (11, 2), (11, 3)]:
        tiles[r][c] = "building_enterable"

    # Defensive positions along canal (rough = trenches)
    tiles[4][7] = "rough"
    tiles[6][7] = "rough"
    tiles[13][7] = "rough"
    tiles[15][7] = "rough"

    # East bank defensive positions
    tiles[4][10] = "rough"
    tiles[6][10] = "rough"
    tiles[13][10] = "rough"
    tiles[15][10] = "rough"

    # Hedgerows on both banks
    _scatter(tiles, "hedge", 15, rng, region=(0, 0, 8, MAP_SIZE))
    _scatter(tiles, "hedge", 15, rng, region=(14, 0, 6, MAP_SIZE))

    # Woods
    _scatter(tiles, "woods", 8, rng, region=(0, 0, 3, MAP_SIZE))
    _scatter(tiles, "woods", 8, rng, region=(17, 0, 3, MAP_SIZE))

    return _make_map(
        "Nederweert Canal - Canal Defense",
        tiles,
        objectives=[
            {"id": "north_bridge", "name": "North Bridge", "position": [8, 5], "type": "defend"},
            {"id": "south_bridge", "name": "South Bridge", "position": [8, 14], "type": "defend"},
        ],
        spawn_points=[
            {"id": "allied_east", "side": "friendly", "position": [15, 10], "units_max": 9},
            {"id": "axis_west", "side": "enemy", "position": [2, 10], "units_max": 9},
        ],
    )


def main() -> None:
    """Generate all additional historically accurate Market Garden maps."""
    project_root = Path(__file__).resolve().parent.parent
    maps_dir = project_root / "data" / "maps"
    maps_dir.mkdir(parents=True, exist_ok=True)

    generators = [
        # 101st Airborne - Additional
        ("koevering_crossroads.json", generate_koevering_crossroads),
        ("st_oedenrode_bridge.json", generate_st_oedenrode_bridge),
        ("willys_canal_crossing.json", generate_willys_canal_crossing),
        ("driel_landing_zone.json", generate_driel_landing_zone),
        # 82nd Airborne - Additional
        ("maas_waal_canal.json", generate_maas_waal_canal),
        ("molenhoek_ridge.json", generate_molenhoek_ridge),
        ("honinghutie_road.json", generate_honinghutie_road),
        ("devils_hill.json", generate_devils_hill),
        # British 1st Airborne - Additional
        ("westerbouwing_heights.json", generate_westerbouwing_heights),
        ("arnhem_railway_bridge.json", generate_arnhem_railway_bridge),
        ("oosterbeek_church.json", generate_oosterbeek_church),
        ("driel_polish_crossing.json", generate_driel_polish_crossing),
        # XXX Corps - Additional
        ("valkenswaard_woods.json", generate_valkenswaard_woods),
        ("aalsmeer_flank.json", generate_aalsmeer_flank),
        ("venray_tank_battle.json", generate_venray_tank_battle),
        ("nederweert_canal.json", generate_nederweert_canal),
    ]

    for filename, gen_func in generators:
        map_data = gen_func()
        filepath = maps_dir / filename
        with open(filepath, "w") as f:
            json.dump(map_data, f, indent=2)
        print(f"  Generated: {filepath}")

    print(f"\nDone! Generated {len(generators)} additional historical Market Garden maps.")


if __name__ == "__main__":
    main()
