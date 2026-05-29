"""Verification: render REAL CC2 map scenes for visual comparison.

Renders actual game maps (not test grids) through the full EnhancedRenderer.
"""
import os, sys
os.environ['SDL_VIDEODRIVER'] = 'dummy'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pygame
from pathlib import Path

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

OUT = Path(__file__).parent.parent / 'screenshots' / 'verification'
OUT.mkdir(parents=True, exist_ok=True)

pygame.init()
screen = pygame.display.set_mode((1280, 720))

MAPS = [
    ("oosterbeek_church.json", "church"),
    ("overloon_battlefield.json", "battlefield"),
    ("arnhem_bridge.json", "bridge"),
    ("hell_highway.json", "highway"),
    ("zonsche_forest.json", "forest"),
    ("eindhoven_city.json", "city"),
]


def render_map(map_name: str, label: str) -> bool:
    """Render one map at multiple zoom levels."""
    game_map = GameMap.from_json(Path("data/maps") / map_name)
    print(f"    {game_map.width}x{game_map.height}")

    camera = Camera(
        position=Vec2(game_map.width * 16.0 / 2, game_map.height * 16.0 / 2),
        viewport_width=1280, viewport_height=720,
    )
    renderer = EnhancedRenderer()
    renderer.initialize(screen)
    ok = True

    for zoom_name, zoom_mult in [("1x", 1.0), ("2x", 2.0), ("debug", 1.0)]:
        if zoom_name == "2x":
            camera.zoom = zoom_mult
        try:
            screen.fill((0, 0, 0))
            renderer.render(
                game_map=game_map, units=[], camera=camera,
                alpha=1.0, selected_unit_ids=set(),
                debug_mode=(zoom_name == "debug"),
            )
            fname = f"{label}_{zoom_name}.png"
            pygame.image.save(screen, str(OUT / fname))
            print(f"      OK: {fname}")
        except Exception as e:
            print(f"      FAIL {zoom_name}: {e}")
            ok = False
        finally:
            if zoom_name == "2x":
                camera.zoom = 1.0
    return ok


def main():
    print("=" * 60)
    print("CC2 Real Map Verification")
    print("=" * 60)
    results = []
    for map_name, label in MAPS:
        print(f"\n[{label}] {map_name}")
        try:
            ok = render_map(map_name, label)
            results.append((label, ok))
        except Exception as e:
            print(f"  FATAL: {e}")
            results.append((label, False))

    print(f"\n{'=' * 60}")
    passed = sum(1 for _, o in results if o)
    print(f"{passed}/{len(results)} maps rendered")
    files = sorted(OUT.glob("*.png"))
    print(f"\n{len(files)} screenshots in verification/:")
    for f in files:
        print(f"  {f.name} ({f.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    main()
