import json

width, height = 20, 20
tiles = []
for y in range(height):
    row = []
    for x in range(width):
        if x == 4 or x == 14:
            row.append("hedge")
        elif 9 <= x <= 10:
            row.append("road")
        elif 7 <= x <= 8 and 2 <= y <= 4:
            row.append("building")
        elif 11 <= x <= 12 and 10 <= y <= 12:
            row.append("trench")
        elif 15 <= x <= 16 and 5 <= y <= 8:
            row.append("forest")
        elif 17 <= x <= 19 and 16 <= y <= 19:
            row.append("water")
        elif 1 <= x <= 2 and 1 <= y <= 3:
            row.append("dirt")
        else:
            row.append("grass")
    tiles.append(row)

map_data = {
    "name": "Test Map Normandy",
    "width": width,
    "height": height,
    "tiles": tiles,
    "spawn_points": [
        {"id": "sp1", "side": "allies", "position": [2, 10], "units_max": 6},
        {"id": "sp2", "side": "axis", "position": [17, 10], "units_max": 6},
    ],
    "objectives": [
        {"id": "obj1", "name": "Bridge", "position": [10, 10]},
        {"id": "obj2", "name": "Village", "position": [8, 3]},
    ],
}

with open("data/maps/test_normandy.json", "w") as f:
    json.dump(map_data, f)

print(f"Created {width}x{height} map: {len(tiles)} rows x {len(tiles[0])} cols")
