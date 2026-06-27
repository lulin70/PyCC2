"""Sprite Generator for PyCC2 - Programmatic Pixel Art Sprites

Generates CC2-authentic pixel art sprites for decorations programmatically.
Each decoration type has a drawing function that creates recognizable
icons at small sizes (up to 32x32 pixels).

Extracted from enhanced_renderer.py (v0.3.7 refactoring).
Original location: L83-L851 (769 lines)
"""

from __future__ import annotations

import math
import random

import pygame


class SpriteGenerator:
    """Generates pixel art sprites for decorations programmatically.

    Each decoration type has a drawing function that creates
    recognizable icons at small sizes (up to 32x32 pixels).
    """

    TILE_SIZE = 32

    @staticmethod
    def generate_sprite(deco_type_name: str, variant: int = 0) -> pygame.Surface:
        """Generate sprite surface for a decoration type."""
        size = 32
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))  # Transparent background

        sprite_funcs = {
            "BUSH_SMALL": SpriteGenerator._draw_bush_small,
            "BUSH_DENSE": SpriteGenerator._draw_bush_dense,
            "TREE_OAK": SpriteGenerator._draw_tree_oak,
            "TREE_PINE": SpriteGenerator._draw_tree_pine,
            "ROCK_LARGE": SpriteGenerator._draw_rock_large,
            "ROCK_SMALL": SpriteGenerator._draw_rock_small,
            "RUBBLE_PILE": SpriteGenerator._draw_rubble,
            "CRATER_SMALL": SpriteGenerator._draw_crater_small,
            "CRATER_LARGE": SpriteGenerator._draw_crater_large,
            "TRENCH_SECTION": SpriteGenerator._draw_trench,
            "SANDBAG_WALL": SpriteGenerator._draw_sandbag,
            "BARBED_WIRE": SpriteGenerator._draw_barbed_wire,
            "WRECKAGE_VEHICLE": SpriteGenerator._draw_wreckage,
            "CAMOUFLAGE_NET": SpriteGenerator._draw_camo_net,
            # CC2特色装饰物
            "WRECKAGE_PLANE": SpriteGenerator._draw_plane_wreckage,
            "BARRICADE_CONCRETE": SpriteGenerator._draw_concrete_barricade,
            "BARRICADE_SANDBAG": SpriteGenerator._draw_sandbag_barricade,
            "CRATER_CLUSTER": SpriteGenerator._draw_crater_cluster,
            "DEBRIS_FIELD": SpriteGenerator._draw_debris_field,
            "BURNING_WRECKAGE": SpriteGenerator._draw_burning_wreckage,
        }

        draw_func = sprite_funcs.get(deco_type_name, SpriteGenerator._draw_placeholder)
        draw_func(surface, variant)

        return surface

    @staticmethod
    def _draw_bush_small(surface: pygame.Surface, variant: int) -> None:
        """Draw small bush (circle of green pixels)."""
        color = (34, 120, 34)
        dark = (24, 90, 24)
        cx, cy = 16, 20
        for y in range(8, 24):
            for x in range(8, 24):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < 7:
                    surface.set_at((x, y), color if dist > 4 else dark)

    @staticmethod
    def _draw_bush_dense(surface: pygame.Surface, variant: int) -> None:
        """Draw dense bush (larger, irregular shape)."""
        color = (28, 100, 28)
        dark = (18, 70, 18)
        points = [
            (10, 22),
            (13, 18),
            (16, 16),
            (19, 17),
            (22, 20),
            (23, 24),
            (20, 26),
            (16, 27),
            (12, 26),
            (9, 24),
        ]

        for y in range(16, 28):
            for x in range(9, 24):
                if SpriteGenerator._point_in_polygon(x, y, points):
                    shade = color if (x + y + variant) % 3 != 0 else dark
                    surface.set_at((x, y), shade)

    @staticmethod
    def _point_in_polygon(x: int, y: int, polygon: list[tuple[int, int]]) -> bool:
        """Check if point is inside polygon (ray casting)."""
        n = len(polygon)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    @staticmethod
    def _draw_tree_oak(surface: pygame.Surface, variant: int) -> None:
        """Draw deciduous tree (trunk + round canopy)."""
        trunk_color = (101, 67, 33)
        for y in range(18, 28):
            for x in range(14, 18):
                surface.set_at((x, y), trunk_color)

        canopy_colors = [(46, 125, 50), (36, 105, 40), (56, 145, 60)]
        cx, cy = 16, 12
        for y in range(2, 20):
            for x in range(4, 28):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist < 10:
                    color_idx = int(dist / 3) % 3
                    surface.set_at((x, y), canopy_colors[color_idx])

    @staticmethod
    def _draw_tree_pine(surface: pygame.Surface, variant: int) -> None:
        """Draw coniferous tree (triangular)."""
        trunk_color = (87, 53, 23)
        for y in range(22, 28):
            for x in range(14, 18):
                surface.set_at((x, y), trunk_color)

        foliage_colors = [(20, 90, 25), (30, 110, 35), (25, 100, 30)]
        layers = [(16, 18, 10), (16, 12, 7), (16, 6, 4)]

        for idx, (lcx, lcy, lw) in enumerate(layers):
            color = foliage_colors[idx]
            for y in range(lcy - lw * 2, lcy + 2):
                width_at_y = int(lw * (1 - abs(y - lcy) / (lw * 2 + 1)))
                for x in range(lcx - width_at_y, lcx + width_at_y + 1):
                    if 0 <= x < 32 and 0 <= y < 32:
                        surface.set_at((x, y), color)

    @staticmethod
    def _draw_rock_large(surface: pygame.Surface, variant: int) -> None:
        """Draw large boulder."""
        colors = [(128, 128, 128), (108, 108, 108), (148, 148, 148)]
        points = [
            (8, 24),
            (10, 18),
            (14, 14),
            (18, 12),
            (22, 14),
            (25, 18),
            (26, 23),
            (24, 26),
            (18, 27),
            (12, 26),
            (9, 25),
        ]

        for y in range(12, 28):
            for x in range(8, 27):
                if SpriteGenerator._point_in_polygon(x, y, points):
                    color_idx = (x + y + variant) % 3
                    surface.set_at((x, y), colors[color_idx])

        surface.set_at((16, 14), (180, 180, 180))
        surface.set_at((17, 15), (170, 170, 170))

    @staticmethod
    def _draw_rock_small(surface: pygame.Surface, variant: int) -> None:
        """Draw small rock cluster."""
        color = (118, 118, 118)
        points = [(12, 24), (14, 20), (18, 19), (21, 21), (22, 25), (19, 26), (14, 25)]
        for y in range(19, 27):
            for x in range(12, 23):
                if SpriteGenerator._point_in_polygon(x, y, points):
                    surface.set_at((x, y), color)

        surface.set_at((22, 23), (138, 138, 138))
        surface.set_at((23, 24), (128, 128, 128))

    @staticmethod
    def _draw_rubble(surface: pygame.Surface, variant: int) -> None:
        """Draw rubble pile (debris)."""
        rng = random.Random(variant * 313)
        colors = [(100, 95, 90), (80, 75, 70), (120, 115, 110), (60, 55, 50)]

        for _ in range(15):
            px = rng.randint(8, 24)
            py = rng.randint(18, 28)
            size = rng.randint(1, 3)
            color = rng.choice(colors)
            for dy in range(size):
                for dx in range(size):
                    if 0 <= px + dx < 32 and 0 <= py + dy < 32:
                        surface.set_at((px + dx, py + dy), color)

    @staticmethod
    def _draw_crater_small(surface: pygame.Surface, variant: int) -> None:
        """Draw small shell crater with multi-layer depth and irregular shape."""
        cx, cy = 16, 20
        rng = random.Random(variant * 137 + 42)

        num_points = 16

        def generate_irregular_shape(base_radius, noise_strength=0.15):
            points = []
            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                noise = noise_strength + noise_strength * math.sin(angle * 3 + variant)
                r = base_radius * noise
                px = cx + r * math.cos(angle)
                py = cy + r * math.sin(angle)
                points.append((px, py))
            return points

        layer_configs = [
            (7.0, (70, 65, 58), 0.15),
            (5.5, (50, 48, 42), 0.12),
            (4.0, (35, 33, 28), 0.10),
            (2.5, (25, 24, 20), 0.08),
            (1.0, (90, 85, 75), 0.05),
        ]

        for idx, (radius, color, noise) in enumerate(layer_configs):
            if idx == 4:
                highlight_angle = math.pi * 1.25
                hx = cx + radius * 0.7 * math.cos(highlight_angle)
                hy = cy + radius * 0.7 * math.sin(highlight_angle)
                pygame.draw.circle(surface, color, (int(hx), int(hy)), max(1, int(radius * 0.6)))
            else:
                points = generate_irregular_shape(radius, noise)
                int_points = [(int(x), int(y)) for x, y in points]
                if len(int_points) >= 3:
                    pygame.draw.polygon(surface, color, int_points)

        shadow_angle = math.pi * 0.25
        shadow_points = []
        for i in range(8):
            angle = shadow_angle + (i - 4) * 0.15
            r = 3.0 + abs(i - 4) * 0.3
            sx = cx + r * math.cos(angle)
            sy = cy + r * math.sin(angle)
            shadow_points.append((sx, sy))
        if len(shadow_points) >= 3:
            int_shadow = [(int(x), int(y)) for x, y in shadow_points]
            pygame.draw.polygon(surface, (20, 18, 15), int_shadow)

        for _ in range(rng.randint(6, 10)):
            debris_angle = rng.uniform(0, 2 * math.pi)
            debris_dist = rng.uniform(6.5, 8.5)
            dx = int(cx + debris_dist * math.cos(debris_angle))
            dy = int(cy + debris_dist * math.sin(debris_angle))
            if 0 <= dx < 32 and 0 <= dy < 32:
                debris_size = rng.randint(2, 3)
                debris_color = (rng.randint(55, 75), rng.randint(50, 68), rng.randint(45, 60))
                pygame.draw.circle(surface, debris_color, (dx, dy), debris_size)

        center_dark_radius = 2
        for r in range(center_dark_radius, 0, -1):
            darkness = 22 + (center_dark_radius - r) * 5
            pygame.draw.circle(surface, (darkness, darkness - 3, darkness - 5), (cx, cy), r)

    @staticmethod
    def _draw_crater_large(surface: pygame.Surface, variant: int) -> None:
        """Draw large bomb crater with multi-layer depth and realistic depression."""
        cx, cy = 16, 18
        rng = random.Random(variant * 137 + 99)

        num_points = 20

        def generate_irregular_shape(base_radius, noise_strength=0.12):
            points = []
            for i in range(num_points):
                angle = 2 * math.pi * i / num_points
                noise = noise_strength + noise_strength * math.sin(angle * 4 + variant * 1.5)
                r = base_radius * noise
                px = cx + r * math.cos(angle)
                py = cy + r * math.sin(angle)
                points.append((px, py))
            return points

        layer_configs = [
            (13.0, (70, 65, 58), 0.14),
            (10.5, (50, 48, 42), 0.11),
            (8.0, (35, 33, 28), 0.09),
            (5.0, (25, 24, 20), 0.07),
            (2.0, (90, 85, 75), 0.05),
        ]

        for idx, (radius, color, noise) in enumerate(layer_configs):
            if idx == 4:
                highlight_angle = math.pi * 1.25
                hx = cx + radius * 0.6 * math.cos(highlight_angle)
                hy = cy + radius * 0.6 * math.sin(highlight_angle)
                pygame.draw.circle(surface, color, (int(hx), int(hy)), max(1, int(radius * 0.7)))
            else:
                points = generate_irregular_shape(radius, noise)
                int_points = [(int(x), int(y)) for x, y in points]
                if len(int_points) >= 3:
                    pygame.draw.polygon(surface, color, int_points)

        shadow_angle = math.pi * 0.35
        shadow_points = []
        for i in range(12):
            angle = shadow_angle + (i - 6) * 0.12
            r = 5.0 + abs(i - 6) * 0.4
            sx = cx + r * math.cos(angle)
            sy = cy + r * math.sin(angle)
            shadow_points.append((sx, sy))
        if len(shadow_points) >= 3:
            int_shadow = [(int(x), int(y)) for x, y in shadow_points]
            pygame.draw.polygon(surface, (18, 16, 13), int_shadow)

        for _ in range(rng.randint(12, 18)):
            debris_angle = rng.uniform(0, 2 * math.pi)
            debris_dist = rng.uniform(12.0, 15.0)
            dx = int(cx + debris_dist * math.cos(debris_angle))
            dy = int(cy + debris_dist * math.sin(debris_angle))
            if 0 <= dx < 32 and 0 <= dy < 32:
                debris_size = rng.randint(2, 3)
                debris_color = (rng.randint(50, 70), rng.randint(45, 65), rng.randint(40, 55))
                pygame.draw.circle(surface, debris_color, (dx, dy), debris_size)

        center_dark_radius = 3
        for r in range(center_dark_radius, 0, -1):
            darkness = 20 + (center_dark_radius - r) * 6
            pygame.draw.circle(surface, (darkness, darkness - 4, darkness - 6), (cx, cy), r)

        rim_thickness = 2
        for t in range(rim_thickness):
            rim_radius = 13.5 + t * 0.3
            rim_noise = 0.08 - t * 0.02
            rim_points = generate_irregular_shape(rim_radius, rim_noise)
            int_rim = [(int(x), int(y)) for x, y in rim_points]
            if len(int_rim) >= 3:
                brightness = 125 - t * 15
                rim_color = (brightness, brightness - 5, brightness - 10)
                pygame.draw.polygon(surface, rim_color, int_rim)

    @staticmethod
    def _draw_trench(surface: pygame.Surface, variant: int) -> None:
        """Draw trench section (rectangular depression)."""
        for y in range(20, 28):
            for x in range(4, 28):
                surface.set_at((x, y), (70, 60, 50))

        bag_color = (180, 160, 120)
        for x in range(4, 28, 3):
            for y in range(18, 21):
                surface.set_at((x, y), bag_color)
                if x + 1 < 28:
                    surface.set_at((x + 1, y), bag_color)
                if x + 2 < 28:
                    surface.set_at((x + 2, y), (160, 140, 100))

    @staticmethod
    def _draw_sandbag(surface: pygame.Surface, variant: int) -> None:
        """Draw sandbag wall with texture detail."""
        bag_color = (190, 170, 130)
        shadow = (150, 130, 90)
        highlight = (210, 195, 160)

        for y in range(14, 26):
            for x in range(2, 30):
                is_bag = (x // 4 + y // 2) % 2 == 0
                if is_bag:
                    if (x * y + variant) % 5 == 0:
                        color = highlight
                    elif (x + y) % 7 == 0:
                        color = shadow
                    else:
                        color = bag_color
                    surface.set_at((x, y), color)
                elif y in [15, 17, 19, 21, 23, 25]:
                    surface.set_at((x, y), (120, 110, 85))

    @staticmethod
    def _draw_barbed_wire(surface: pygame.Surface, variant: int) -> None:
        """Draw barbed wire obstacle."""
        wire_color = (180, 180, 180)
        dark_wire = (120, 120, 120)

        for strand_y in [10, 16, 22]:
            for x in range(4, 28):
                wave = math.sin(x * 0.5 + variant) * 2
                y = int(strand_y + wave)
                if 0 <= y < 32:
                    surface.set_at((x, y), wire_color if x % 3 != 0 else dark_wire)

        for barb_x in range(6, 28, 6):
            barb_y_base = 16 + int(math.sin(barb_x * 0.5 + variant) * 2)
            surface.set_at((barb_x, barb_y_base - 2), dark_wire)
            surface.set_at((barb_x - 1, barb_y_base - 1), dark_wire)
            surface.set_at((barb_x + 1, barb_y_base - 1), dark_wire)
            if barb_x % 12 == 0:
                surface.set_at((barb_x, barb_y_base + 2), dark_wire)
                surface.set_at((barb_x - 1, barb_y_base + 1), dark_wire)
                surface.set_at((barb_x + 1, barb_y_base + 1), dark_wire)

        for post_x in range(4, 28, 12):
            post_color = (100, 90, 80)
            for post_y in range(8, 24):
                surface.set_at((post_x, post_y), post_color)
                surface.set_at((post_x + 1, post_y), (120, 110, 100))

    @staticmethod
    def _draw_wreckage(surface: pygame.Surface, variant: int) -> None:
        """Draw destroyed vehicle hull."""
        hull_color = (60, 55, 50)
        dark = (40, 35, 30)
        rust = (100, 60, 30)

        hull_points = [
            (6, 22),
            (8, 18),
            (12, 16),
            (18, 15),
            (24, 16),
            (26, 19),
            (27, 23),
            (25, 26),
            (18, 27),
            (10, 26),
            (7, 24),
        ]

        for y in range(15, 28):
            for x in range(6, 28):
                if SpriteGenerator._point_in_polygon(x, y, hull_points):
                    color = hull_color
                    if (x + y + variant) % 7 == 0:
                        color = rust
                    elif (x * y) % 11 == 0:
                        color = dark
                    surface.set_at((x, y), color)

        for x in range(20, 28):
            surface.set_at((x, 17), dark)

    @staticmethod
    def _draw_camo_net(surface: pygame.Surface, variant: int) -> None:
        """Draw camouflage netting."""
        colors = [(45, 90, 45), (60, 75, 35), (35, 65, 40)]
        rng = random.Random(variant * 373)

        for y in range(8, 24):
            for x in range(4, 28):
                if (x + y) % 3 == 0:
                    surface.set_at((x, y), (80, 75, 70))
                else:
                    color = colors[rng.randint(0, 2)]
                    if rng.random() > 0.3:
                        surface.set_at((x, y), color)

    @staticmethod
    def _draw_placeholder(surface: pygame.Surface, variant: int) -> None:
        """Generic placeholder sprite."""
        color = (150, 150, 150)
        for y in range(10, 22):
            for x in range(10, 22):
                if (x + y) % 2 == 0:
                    surface.set_at((x, y), color)

    # ===================================================================
    # CC2特色装饰物
    # ===================================================================

    @staticmethod
    def _draw_plane_wreckage(surface: pygame.Surface, variant: int) -> None:
        """Draw crashed aircraft wreckage (✈️ 飞机残骸)."""
        fuselage_color = (55, 50, 45)
        wing_color = (60, 55, 50)
        rust = (110, 65, 25)
        dark_rust = (80, 45, 15)
        shadow = (35, 30, 25)

        fuselage_points = [
            (14, 8),
            (16, 7),
            (18, 8),
            (19, 12),
            (18, 20),
            (17, 24),
            (15, 26),
            (13, 24),
            (12, 20),
            (13, 12),
            (14, 8),
        ]

        for y in range(7, 27):
            for x in range(11, 21):
                if SpriteGenerator._point_in_polygon(x, y, fuselage_points):
                    if (x + y + variant) % 9 == 0:
                        surface.set_at((x, y), rust)
                    elif (x * y) % 13 == 0:
                        surface.set_at((x, y), dark_rust)
                    else:
                        surface.set_at((x, y), fuselage_color)

        left_wing = [(6, 14), (9, 13), (12, 14), (13, 16), (12, 18), (9, 17), (6, 16), (5, 15)]
        for y in range(13, 19):
            for x in range(5, 14):
                if SpriteGenerator._point_in_polygon(x, y, left_wing):
                    shade = wing_color if (x + y) % 3 != 0 else shadow
                    surface.set_at((x, y), shade)

        right_wing = [
            (26, 14),
            (23, 13),
            (20, 14),
            (19, 16),
            (20, 18),
            (23, 17),
            (26, 16),
            (27, 15),
        ]
        for y in range(13, 19):
            for x in range(19, 28):
                if SpriteGenerator._point_in_polygon(x, y, right_wing):
                    shade = wing_color if (x + y) % 3 != 0 else shadow
                    surface.set_at((x, y), shade)

        for x in range(14, 19):
            surface.set_at((x, 6), dark_rust)

    @staticmethod
    def _draw_concrete_barricade(surface: pygame.Surface, variant: int) -> None:
        """Draw concrete anti-tank barricade (🚧 混凝土路障)."""
        concrete = (140, 135, 130)
        dark_concrete = (110, 105, 100)
        highlight = (160, 155, 150)
        shadow_edge = (90, 85, 80)

        center_x, center_y = 16, 16

        for i in range(-6, 7):
            offset = abs(i)
            width = max(3, 5 - offset // 2)
            for w in range(-width, width + 1):
                px = center_x + i + w // 2
                py = center_y - i + w // 2
                if 4 <= px < 28 and 4 <= py < 28:
                    if w == -width or w == width:
                        surface.set_at((px, py), shadow_edge)
                    elif w == -width + 1 or w == width - 1:
                        surface.set_at((px, py), dark_concrete)
                    else:
                        surface.set_at((px, py), concrete if (i + w) % 4 != 0 else highlight)

        for i in range(-6, 7):
            offset = abs(i)
            width = max(3, 5 - offset // 2)
            for w in range(-width, width + 1):
                px = center_x + i + w // 2
                py = center_y + i + w // 2
                if 4 <= px < 28 and 4 <= py < 28:
                    if w == -width or w == width:
                        surface.set_at((px, py), shadow_edge)
                    elif w == -width + 1 or w == width - 1:
                        surface.set_at((px, py), dark_concrete)
                    else:
                        surface.set_at((px, py), concrete if (i - w) % 4 != 0 else highlight)

    @staticmethod
    def _draw_sandbag_barricade(surface: pygame.Surface, variant: int) -> None:
        """Draw sandbag defensive position (🛡️ 沙袋路障)."""
        bag_color = (160, 145, 110)
        bag_dark = (130, 115, 85)
        bag_shadow = (100, 90, 65)

        walls = [
            [(8, 10), (8, 13), (24, 13), (24, 10)],
            [(8, 13), (11, 13), (11, 24), (8, 24)],
            [(21, 13), (24, 13), (24, 24), (21, 24)],
        ]

        for _wall_idx, wall in enumerate(walls):
            for y in range(min(p[1] for p in wall), max(p[1] for p in wall)):
                for x in range(min(p[0] for p in wall), max(p[0] for p in wall)):
                    if SpriteGenerator._point_in_polygon(x, y, wall):
                        bag_idx = ((x - 8) // 3 + (y - 10) // 3 + variant) % 3
                        if bag_idx == 0:
                            color = bag_color
                        elif bag_idx == 1:
                            color = bag_dark
                        else:
                            color = bag_shadow

                        is_edge = (
                            y == min(p[1] for p in wall)
                            or y == max(p[1] for p in wall) - 1
                            or x == min(p[0] for p in wall)
                            or x == max(p[0] for p in wall) - 1
                        )
                        if is_edge:
                            color = (
                                min(255, color[0] + 20),
                                min(255, color[1] + 20),
                                min(255, color[2] + 20),
                            )

                        surface.set_at((x, y), color)

    @staticmethod
    def _draw_crater_cluster(surface: pygame.Surface, variant: int) -> None:
        """💣 增强版弹坑群 - 立体凹陷效果"""
        cx, cy = 16, 16

        rim_color = (90, 75, 55)
        pygame.draw.ellipse(surface, rim_color, (cx - 14, cy - 12, 28, 24))

        for i in range(5, 0, -1):
            depth_factor = i / 5.0
            radius = int(10 * depth_factor)
            darkness = int(25 + (1 - depth_factor) * 35)
            color = (darkness, darkness - 5, darkness - 8)
            offset_x = random.randint(-2, 2) * (6 - i) // 3
            offset_y = random.randint(-2, 2) * (6 - i) // 3
            if radius > 0:
                pygame.draw.circle(surface, color, (cx + offset_x, cy + offset_y), radius)

        highlight_color = (120, 105, 85)
        pygame.draw.arc(
            surface, highlight_color, (cx - 13, cy - 11, 26, 22), math.pi * 1.2, math.pi * 1.8, 2
        )

        for _ in range(random.randint(3, 5)):
            rx = cx + random.randint(-10, 10)
            ry = cy + random.randint(-8, 8)
            r_size = random.randint(1, 3)
            debris_color = (60, 50, 40)
            pygame.draw.circle(surface, debris_color, (rx, ry), r_size)

        if variant >= 1:
            offsets = [(8, -6), (-7, 4), (5, 8)]
            for _i, (ox, oy) in enumerate(offsets[: min(variant, len(offsets))]):
                small_r = random.randint(4, 7)
                pygame.draw.ellipse(
                    surface,
                    (35, 30, 25),
                    (
                        cx + ox - small_r,
                        oy + cy - int(small_r * 0.7),
                        small_r * 2,
                        int(small_r * 1.4),
                    ),
                )

    @staticmethod
    def _draw_debris_field(surface: pygame.Surface, variant: int) -> None:
        """Draw scattered debris field (🗑️ 碎片场)."""
        debris_colors = [
            (80, 75, 70),
            (100, 95, 88),
            (120, 110, 100),
            (60, 55, 50),
            (90, 85, 75),
        ]

        rng = random.Random(variant * 137)

        num_debris = 40 + (variant % 20)
        for _ in range(num_debris):
            x = rng.randint(4, 27)
            y = rng.randint(4, 27)
            color = debris_colors[rng.randint(0, len(debris_colors) - 1)]

            size = rng.randint(1, 3)
            for dx in range(size):
                for dy in range(size):
                    px, py = x + dx, y + dy
                    if 4 <= px < 28 and 4 <= py < 28:
                        variation = rng.randint(-8, 8)
                        final_color = tuple(max(0, min(255, c + variation)) for c in color)
                        surface.set_at((px, py), final_color)

        for _ in range(2 + (variant % 2)):
            start_x = rng.randint(6, 22)
            start_y = rng.randint(6, 22)
            length = rng.randint(3, 7)
            angle = rng.uniform(0, math.pi * 2)

            for i in range(length):
                px = int(start_x + i * math.cos(angle))
                py = int(start_y + i * math.sin(angle))
                if 4 <= px < 28 and 4 <= py < 28:
                    surface.set_at((px, py), (70, 65, 58))

    @staticmethod
    def _draw_burning_wreckage(surface: pygame.Surface, variant: int) -> None:
        """Draw burning/destroyed wreckage (🔥 燃烧残骸)."""
        hull_color = (50, 45, 40)
        flame_orange = (220, 120, 20)
        flame_red = (180, 50, 10)
        flame_yellow = (240, 200, 50)
        smoke_gray = (120, 120, 120)

        hull_points = [
            (5, 20),
            (7, 16),
            (11, 14),
            (17, 13),
            (23, 14),
            (26, 17),
            (27, 22),
            (25, 26),
            (17, 27),
            (9, 26),
            (6, 23),
        ]

        for y in range(13, 28):
            for x in range(5, 28):
                if SpriteGenerator._point_in_polygon(x, y, hull_points):
                    surface.set_at((x, y), hull_color)

        fire_centers = [(12, 18), (18, 17), (22, 20)]
        rng = random.Random(variant * 99)

        for fcx, fcy in fire_centers[: 2 + (variant % 2)]:
            for y in range(fcy - 4, fcy + 5):
                for x in range(fcx - 4, fcx + 5):
                    dist = math.sqrt((x - fcx) ** 2 + (y - fcy) ** 2)
                    if dist <= 4.5 and rng.random() > 0.3:
                        if dist < 1.5:
                            color = flame_yellow
                        elif dist < 2.8:
                            color = flame_orange
                        else:
                            color = flame_red

                        if rng.random() > 0.15:
                            surface.set_at((x, y), color)

        for smoke_y in range(8, 14):
            for smoke_x in range(10, 24):
                if rng.random() > 0.85:
                    alpha_smoke = (*smoke_gray, 150 - (smoke_y - 8) * 10)
                    surface.set_at((smoke_x, smoke_y), alpha_smoke)
