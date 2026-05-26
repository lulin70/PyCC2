"""Visual demo: launch PyCC2 with isometric rendering for visual verification.

Press I to toggle between Orthographic and Isometric projection.
Press ESC to quit.
"""
import os
import sys

import pygame

# Add project to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Unit
from pycc2.presentation.rendering.camera import Camera, ProjectionMode
from pycc2.presentation.rendering.isometric_renderer import IsometricRenderer
from pycc2.presentation.rendering.isometric_transform import TILE_W, TILE_H


def create_demo_map(width=20, height=15):
    """Create a small demo map with varied terrain."""
    import numpy as np
    # Start with all grass (terrain_id=2)
    grid = np.full((height, width), 2, dtype=np.int8)

    # Add roads (terrain_id=1)
    grid[7, :] = 1
    grid[:, 10] = 1

    # Add water (terrain_id=6)
    grid[3:6, 3:7] = 6

    # Add woods (terrain_id=3)
    grid[10:13, 2:6] = 3

    # Add buildings (terrain_id=4)
    grid[4:6, 14:16] = 4

    # Add hedges (terrain_id=7)
    grid[9, 8:12] = 7

    # Add rough (terrain_id=9)
    grid[12:14, 12:16] = 9

    game_map = GameMap(
        id="demo_iso",
        name="Isometric Demo",
        width=width,
        height=height,
        tile_grid=grid,
    )
    return game_map


def create_demo_units():
    """Create a few demo units using simple mock objects."""
    from unittest.mock import MagicMock

    units = []
    for uid, name, side, tx, ty in [
        ("allies_1", "Rifle Squad", "allies", 8, 5),
        ("allies_2", "MG Team", "allies", 9, 6),
        ("axis_1", "Grenadiers", "axis", 12, 8),
        ("axis_2", "Panzer", "axis", 14, 10),
    ]:
        u = MagicMock()
        u.id = uid
        u.name = name
        u.side = side
        u.position = MagicMock()
        u.position.tile_coord = MagicMock()
        u.position.tile_coord.x = tx
        u.position.tile_coord.y = ty
        units.append(u)
    return units


def main():
    pygame.init()
    screen = pygame.display.set_mode((1280, 720))
    pygame.display.set_caption("PyCC2 Isometric Demo - Press I to toggle projection, ESC to quit")
    clock = pygame.time.Clock()

    # Create demo data
    game_map = create_demo_map()
    units = create_demo_units()

    # Camera
    cam = Camera(
        position=Vec2(10 * TILE_W / 2, 7 * TILE_H / 2),
        zoom=1.0,
        viewport_width=1280,
        viewport_height=720,
        projection=ProjectionMode.ISOMETRIC,
    )

    # Isometric renderer
    iso_renderer = IsometricRenderer()
    iso_renderer.initialize(screen)

    # Font for HUD
    font = pygame.font.SysFont("consolas", 16)

    running = True
    while running:
        dt = clock.tick(30) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_i:
                    # Toggle projection
                    if cam.projection == ProjectionMode.ORTHOGRAPHIC:
                        cam.projection = ProjectionMode.ISOMETRIC
                    else:
                        cam.projection = ProjectionMode.ORTHOGRAPHIC
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    cam.adjust_zoom(1.2)
                elif event.key == pygame.K_MINUS:
                    cam.adjust_zoom(1 / 1.2)

        # Camera movement with arrow keys
        keys = pygame.key.get_pressed()
        move_speed = 200
        camera_moved = False
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            cam.move(-move_speed * dt, 0)
            camera_moved = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            cam.move(move_speed * dt, 0)
            camera_moved = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            cam.move(0, -move_speed * dt)
            camera_moved = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            cam.move(0, move_speed * dt)
            camera_moved = True

        # Mark dirty when camera moves so renderer redraws
        if camera_moved:
            iso_renderer.mark_dirty()

        # Render
        screen.fill((34, 40, 48))

        if cam.projection == ProjectionMode.ISOMETRIC:
            iso_renderer.render(game_map, units, cam, debug_mode=True)
        else:
            # Simple orthographic fallback
            tile_size = 32
            vx, vy = cam.position.x, cam.position.y
            for y in range(game_map.height):
                for x in range(game_map.width):
                    sx = (x * tile_size - vx) * cam.zoom + 640
                    sy = (y * tile_size - vy) * cam.zoom + 360
                    if -tile_size < sx < 1280 and -tile_size < sy < 720:
                        terrain = game_map.get_tile(x, y)
                        colors = {
                            0: (76, 132, 52),   # GRASS
                            1: (149, 126, 94),  # ROAD
                            2: (56, 104, 36),   # GRASS
                            3: (34, 72, 30),    # WOODS
                            4: (180, 170, 155), # BUILDING
                            6: (64, 120, 172),  # WATER
                        }
                        color = colors.get(terrain, (100, 100, 100))
                        rect = pygame.Rect(int(sx), int(sy),
                                         int(tile_size * cam.zoom),
                                         int(tile_size * cam.zoom))
                        pygame.draw.rect(screen, color, rect)
                        pygame.draw.rect(screen, (40, 40, 40), rect, 1)

        # HUD
        mode_text = f"Projection: {cam.projection.value.upper()}"
        mode_surf = font.render(mode_text, True, (255, 255, 255))
        screen.blit(mode_surf, (10, 10))

        help_text = "I=Toggle | WASD=Move | +/-=Zoom | ESC=Quit"
        help_surf = font.render(help_text, True, (180, 180, 180))
        screen.blit(help_surf, (10, 30))

        fps_text = f"FPS: {clock.get_fps():.0f}"
        fps_surf = font.render(fps_text, True, (180, 180, 180))
        screen.blit(fps_surf, (10, 50))

        # Performance stats from isometric renderer
        if cam.projection == ProjectionMode.ISOMETRIC:
            stats = iso_renderer.get_performance_stats()
            perf_lines = [
                f"Tiles: {stats['tile_count']}",
                f"Draw: {stats['draw_time_ms']:.1f}ms",
                f"Cache Hit: {stats['cache_hit_rate']:.0%}",
                f"Base Cache: {stats['base_cache_size']}",
                f"Scaled Cache: {stats['scaled_cache_size']}",
                f"Frames: {stats['frame_count']}",
            ]
            for i, line in enumerate(perf_lines):
                color = (255, 100, 100) if stats['draw_time_ms'] > 33.0 else (140, 200, 140)
                perf_surf = font.render(line, True, color)
                screen.blit(perf_surf, (10, 70 + i * 18))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
