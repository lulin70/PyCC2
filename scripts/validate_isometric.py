"""Quick validation script for isometric rendering pipeline."""

import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame

pygame.init()
pygame.display.set_mode((640, 480))

from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.camera import Camera, ProjectionMode
from pycc2.presentation.rendering.isometric_depth_sorter import (
    IsometricRenderable,
    RenderLayer,
    sort_for_isometric,
)
from pycc2.presentation.rendering.isometric_tile_generator import (
    generate_building_tile,
    generate_crater_tile,
    generate_dirt_tile,
    generate_grass_tile,
    generate_hedgerow_tile,
    generate_road_tile,
    generate_water_tile,
)
from pycc2.presentation.rendering.isometric_transform import (
    is_point_in_diamond,
    isometric_to_world,
    tile_diamond_corners,
    world_to_isometric,
)

print("=" * 60)
print("PyCC2 Isometric Pipeline Validation")
print("=" * 60)

# Test 1: Camera dual mode
cam = Camera(position=Vec2(0, 0), zoom=1.0)
pos = Vec2(5.0, 3.0)

ortho_screen = cam.world_to_screen(pos)
print(f"[1] Ortho: world(5,3) -> screen{ortho_screen}")

cam.projection = ProjectionMode.ISOMETRIC
iso_screen = cam.world_to_screen(pos)
print(f"[1] Iso:   world(5,3) -> screen{iso_screen}")

recovered = cam.screen_to_world(iso_screen)
print(f"[1] Iso roundtrip: -> world({recovered.x:.2f},{recovered.y:.2f})")
assert abs(recovered.x - 5.0) < 0.01, f"Roundtrip X failed: {recovered.x}"
assert abs(recovered.y - 3.0) < 0.01, f"Roundtrip Y failed: {recovered.y}"

# Test 2: Coordinate transforms
for wx, wy in [(0, 0), (1, 0), (0, 1), (1, 1), (10, 5)]:
    sx, sy = world_to_isometric(wx, wy)
    rwx, rwy = isometric_to_world(sx, sy)
    assert abs(rwx - wx) < 0.01 and abs(rwy - wy) < 0.01
print("[2] Coordinate roundtrips: ALL PASS")

# Test 3: Tile generation
tiles = {
    "grass": generate_grass_tile(),
    "dirt": generate_dirt_tile(),
    "water": generate_water_tile(),
    "road": generate_road_tile(),
    "crater": generate_crater_tile(),
    "hedgerow": generate_hedgerow_tile(),
    "building": generate_building_tile(2),
}
for name, tile in tiles.items():
    print(f"[3] {name}: {tile.get_size()}")
assert tiles["grass"].get_size() == (64, 32)
assert tiles["building"].get_size()[1] > 32  # Building is taller than flat tile

# Test 4: Depth sorting
renderables = [
    IsometricRenderable(5, 5, 0, RenderLayer.UNIT, "unit_front"),
    IsometricRenderable(0, 0, 0, RenderLayer.TERRAIN, "tile_back"),
    IsometricRenderable(3, 3, 0, RenderLayer.TERRAIN, "tile_mid"),
    IsometricRenderable(3, 3, 0, RenderLayer.UNIT, "unit_mid"),
    IsometricRenderable(2, 2, 1, RenderLayer.BUILDING, "building"),
]
sorted_ren = sort_for_isometric(renderables)
order = [r.data for r in sorted_ren]
print(f"[4] Depth sort: {order}")
assert order.index("tile_back") < order.index("unit_front")
assert order.index("tile_mid") < order.index("unit_mid")

# Test 5: Diamond geometry
corners = tile_diamond_corners(32, 16)
print(f"[5] Diamond corners: {corners}")
assert is_point_in_diamond(32, 16, 32, 16)
assert not is_point_in_diamond(0, 0, 32, 16)

# Test 6: IsometricRenderer
from pycc2.presentation.rendering.isometric_renderer import IsometricRenderer

renderer = IsometricRenderer()
screen = pygame.display.get_surface()
renderer.initialize(screen)
print("[6] IsometricRenderer: OK")

# Test 7: Building renderer
from pycc2.presentation.rendering.isometric_building_renderer import (
    BuildingType,
    DamageState,
    render_building,
)

for bt in BuildingType:
    for ds in DamageState:
        surf = render_building(bt, damage=ds)
        print(f"[7] {bt.name}/{ds.name}: {surf.get_size()}")

# Test 8: PixVoxelLoader (without actual assets)
from pycc2.presentation.rendering.pixvoxel_loader import PixVoxelLoader

loader = PixVoxelLoader()
print("[8] PixVoxelLoader: OK (fallback mode)")

# Test 9: Projection toggle
cam.projection = ProjectionMode.ORTHOGRAPHIC
ortho_pos = cam.world_to_screen(Vec2(5, 3))
cam.projection = ProjectionMode.ISOMETRIC
iso_pos = cam.world_to_screen(Vec2(5, 3))
assert ortho_pos != iso_pos, "Ortho and Iso should produce different screen positions"
print(f"[9] Projection toggle: Ortho{ortho_pos} != Iso{iso_pos}")

print()
print("=" * 60)
print("ALL ISOMETRIC VALIDATION PASSED")
print("=" * 60)
