"""
Environment Pixel Renderer - Extracted from PixelArtist3D God Class (P3-3).

Contains environment sprite generation logic:
- Tree (multi-tone canopy with irregular edges, size variants)
- Building (house / factory / bunker with type-specific detailing)

Public API delegates through PixelArtist3D for backward compatibility.
"""

from __future__ import annotations

import logging
import math
import random

logger = logging.getLogger(__name__)


class EnvironmentPixelRenderer:
    """
    Environment sprite renderer for map decorations and structures.

    Generates top-down sprites for terrain and building features:
    - Tree: 20x20 / 28x28 / 36x36 px (small/medium/large), multi-tone canopy
      with irregular perturbed edges and upper-left highlight simulation
    - Building: 32x32 px, supports three variants:
        * house: residential with gabled roof, door, windows
        * factory: industrial with chimney and animated smoke
        * bunker: fortified concrete with sandbag emplacement

    All sprites use deterministic per-variant RNG seeds to ensure
    reproducible visuals across save/load cycles.
    """

    # ================================================================== #
    #  ENVIRONMENT SPRITES
    # ================================================================== #

    @staticmethod
    def create_tree_sprite(variant: int = 0, size: str = "medium"):
        """Create a CC2-style multi-tone canopy tree sprite with irregular edges.

        Phase 1 Fix 0.3 + Fix 0.5 enhanced version:
        - Multi-tone canopy: 4 green layers (base/highlight/shadow/accent)
        - Irregular edges: perturbed radius +/-2px per 30 degrees
        - Light source simulation: upper-left highlight, lower-right shadow
        - Size variants: small(20x20)/medium(28x28)/large(36x36)
        """
        import pygame

        size_config = {
            "small": {"canvas": 20, "radius": 10},
            "medium": {"canvas": 28, "radius": 14},
            "large": {"canvas": 36, "radius": 18},
        }
        config = size_config.get(size, size_config["medium"])
        canvas_size = config["canvas"]
        canopy_radius = config["radius"]

        surface = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        cx, cy = canvas_size // 2, canvas_size // 2 - 1

        shadow_surface = pygame.Surface((canvas_size, canvas_size), pygame.SRCALPHA)
        shadow_offset_x, shadow_offset_y = 3, 3
        shadow_w = canopy_radius * 2 - 4
        shadow_h = canopy_radius * 1.5 - 2
        pygame.draw.ellipse(
            shadow_surface,
            (0, 0, 0, 50),
            (
                cx - shadow_w // 2 + shadow_offset_x,
                cy - shadow_h // 2 + shadow_offset_y,
                shadow_w,
                shadow_h,
            ),
        )
        surface.blit(shadow_surface, (0, 0))

        base_canopy = (34, 68, 28)
        accent_light = (45, 90, 38)
        highlight = (55, 110, 48)
        shadow_green = (22, 50, 18)
        trunk_color = (60, 40, 20)

        points = []
        num_points = 36
        rng_edge = random.Random(variant * 73 + 11)

        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            radius_perturb = canopy_radius + rng_edge.randint(-2, 2)
            px = cx + int(math.cos(angle) * radius_perturb)
            py = cy + int(math.sin(angle) * radius_perturb)
            points.append((px, py))

        if len(points) >= 3:
            pygame.draw.polygon(surface, base_canopy, points)

        pygame.draw.circle(surface, base_canopy, (cx, cy), canopy_radius - 1)

        rng_accent1 = random.Random(variant * 41 + 3)
        accent1_count = rng_accent1.randint(15, 20)
        for _ in range(accent1_count):
            angle = rng_accent1.uniform(0, 2 * math.pi)
            dist = rng_accent1.uniform(0, canopy_radius - 3)
            ax = int(cx + math.cos(angle) * dist)
            ay = int(cy + math.sin(angle) * dist)
            if 0 <= ax < canvas_size and 0 <= ay < canvas_size:
                surface.set_at((ax, ay), accent_light)

        rng_highlight = random.Random(variant * 59 + 7)
        highlight_count = rng_highlight.randint(5, 8)
        for _ in range(highlight_count):
            angle = rng_highlight.uniform(-3 * math.pi / 4, -math.pi / 4)
            dist = rng_highlight.uniform(canopy_radius * 0.2, canopy_radius * 0.6)
            hx = int(cx + math.cos(angle) * dist)
            hy = int(cy + math.sin(angle) * dist)
            if 0 <= hx < canvas_size and 0 <= hy < canvas_size:
                surface.set_at((hx, hy), highlight)

        rng_shadow = random.Random(variant * 83 + 13)
        shadow_count = rng_shadow.randint(8, 10)
        for _ in range(shadow_count):
            angle = rng_shadow.uniform(math.pi / 4, 3 * math.pi / 4)
            dist = rng_shadow.uniform(canopy_radius * 0.3, canopy_radius * 0.7)
            sx = int(cx + math.cos(angle) * dist)
            sy = int(cy + math.sin(angle) * dist)
            if 0 <= sx < canvas_size and 0 <= sy < canvas_size:
                surface.set_at((sx, sy), shadow_green)

        trunk_y = cy + canopy_radius // 3
        if 0 <= trunk_y < canvas_size:
            pygame.draw.circle(surface, trunk_color, (cx, trunk_y), 2)

        edge_color = (28, 58, 24)
        if len(points) >= 3:
            for i in range(len(points)):
                p1 = points[i]
                p2 = points[(i + 1) % len(points)]
                pygame.draw.line(surface, edge_color, p1, p2, 1)

        return surface

    @staticmethod
    def create_building_sprite(building_type: str = "house", variant: int = 0):
        """Create a CC2-style building sprite (32x32 px).

        Supports multiple building types with visual differentiation:
        - house: residential building with roof detail
        - factory: industrial building with chimney/smoke
        - bunker: fortified concrete structure
        """
        import pygame

        surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        cx, cy = 16, 16

        if building_type == "house":
            wall_color = (140, 120, 95)
            roof_color = (110, 75, 50)
            dark_color = (100, 85, 68)

            wall_w, wall_h = 20, 16
            wall_x = cx - wall_w // 2
            wall_y = cy - wall_h // 2
            pygame.draw.rect(surface, wall_color, (wall_x, wall_y, wall_w, wall_h))
            pygame.draw.rect(surface, dark_color, (wall_x, wall_y, wall_w, wall_h), 1)

            roof_points = [
                (wall_x - 2, wall_y + 2),
                (cx, wall_y - 6),
                (wall_x + wall_w + 2, wall_y + 2),
            ]
            pygame.draw.polygon(surface, roof_color, roof_points)
            pygame.draw.polygon(surface, dark_color, roof_points, 1)

            door_w, door_h = 4, 6
            door_x = cx - door_w // 2
            door_y = wall_y + wall_h - door_h
            pygame.draw.rect(surface, (80, 55, 35), (door_x, door_y, door_w, door_h))

            for win_y in [wall_y + 3, wall_y + wall_h - 8]:
                for win_x_off in [-6, 6]:
                    win_x = cx + win_x_off
                    pygame.draw.rect(surface, (180, 200, 220), (win_x, win_y, 4, 4))
                    pygame.draw.rect(surface, dark_color, (win_x, win_y, 4, 4), 1)

                    cross_x = win_x + 2
                    cross_y = win_y + 2
                    pygame.draw.line(
                        surface, dark_color, (cross_x, cross_y - 1), (cross_x, cross_y + 1), 1
                    )
                    pygame.draw.line(
                        surface, dark_color, (cross_x - 1, cross_y), (cross_x + 1, cross_y), 1
                    )

        elif building_type == "factory":
            wall_color = (120, 115, 105)
            roof_color = (85, 80, 75)
            dark_color = (90, 85, 78)

            wall_w, wall_h = 24, 14
            wall_x = cx - wall_w // 2
            wall_y = cy - wall_h // 2 + 2
            pygame.draw.rect(surface, wall_color, (wall_x, wall_y, wall_w, wall_h))
            pygame.draw.rect(surface, dark_color, (wall_x, wall_y, wall_w, wall_h), 1)

            pygame.draw.rect(surface, roof_color, (wall_x, wall_y - 3, wall_w, 3))
            pygame.draw.line(surface, dark_color, (wall_x, wall_y), (wall_x + wall_w, wall_y), 1)

            chimney_x = cx + 6
            chimney_y = wall_y - 8
            pygame.draw.rect(surface, (70, 65, 60), (chimney_x, chimney_y, 4, 6))
            pygame.draw.rect(surface, dark_color, (chimney_x, chimney_y, 4, 6), 1)

            smoke_rng = random.Random(variant + 42)
            for i in range(3):
                smoke_r = 2 + i
                smoke_x = chimney_x + 2 + smoke_rng.randint(-2, 2)
                smoke_y = chimney_y - 3 - i * 3
                smoke_alpha = max(20, 80 - i * 25)
                smoke_surf = pygame.Surface((smoke_r * 2, smoke_r * 2), pygame.SRCALPHA)
                smoke_surf.fill((0, 0, 0, 0))
                pygame.draw.circle(
                    smoke_surf, (180, 180, 175, smoke_alpha), (smoke_r, smoke_r), smoke_r
                )
                surface.blit(smoke_surf, (smoke_x - smoke_r, smoke_y - smoke_r))

            for bx in range(wall_x + 2, wall_x + wall_w - 2, 6):
                pygame.draw.rect(surface, (150, 155, 140), (bx, wall_y + 3, 4, 5))
                pygame.draw.line(surface, dark_color, (bx, wall_y + 3), (bx, wall_y + 8), 1)
                pygame.draw.line(surface, dark_color, (bx + 4, wall_y + 3), (bx + 4, wall_y + 8), 1)
                pygame.draw.line(surface, dark_color, (bx, wall_y + 5), (bx + 4, wall_y + 5), 1)

        elif building_type == "bunker":
            wall_color = (130, 125, 118)
            dark_color = (95, 90, 83)

            bunker_w, bunker_h = 22, 18
            bunker_x = cx - bunker_w // 2
            bunker_y = cy - bunker_h // 2
            pygame.draw.rect(
                surface, wall_color, (bunker_x, bunker_y, bunker_w, bunker_h), border_radius=2
            )
            pygame.draw.rect(surface, dark_color, (bunker_x, bunker_y, bunker_w, bunker_h), 2)

            bagstone_rng = random.Random(variant + 99)
            for _ in range(15):
                sx = bagstone_rng.randint(bunker_x + 2, bunker_x + bunker_w - 3)
                sy = bagstone_rng.randint(bunker_y + 2, bunker_y + bunker_h - 3)
                stone_dark = tuple(max(0, c - 20) for c in wall_color)
                pygame.draw.circle(surface, stone_dark, (sx, sy), 1)

            emplacement_w, emplacement_h = 10, 6
            emp_x = cx - emplacement_w // 2
            emp_y = bunker_y + bunker_h - emplacement_h - 2
            emp_inner_color = (50, 48, 45)
            pygame.draw.rect(surface, emp_inner_color, (emp_x, emp_y, emplacement_w, emplacement_h))
            pygame.draw.rect(surface, dark_color, (emp_x, emp_y, emplacement_w, emplacement_h), 1)

            sandbag_y = emp_y - 2
            for sb_x in range(emp_x - 1, emp_x + emplacement_w + 1, 3):
                sb_color = (150, 140, 115)
                pygame.draw.rect(surface, sb_color, (sb_x, sandbag_y, 3, 2))
                pygame.draw.rect(surface, dark_color, (sb_x, sandbag_y, 3, 2), 1)

        else:
            wall_color = (128, 128, 128)
            dark_color = (96, 96, 96)
            pygame.draw.rect(surface, wall_color, (cx - 10, cy - 8, 20, 16))
            pygame.draw.rect(surface, dark_color, (cx - 10, cy - 8, 20, 16), 1)

        shadow_surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, 40), (cx - 12, cy + 10, 24, 6))
        surface.blit(shadow_surface, (0, 0))

        return surface
