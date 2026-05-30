"""
CC2-Style Programmatic Sprite Generator

Generates pixel art sprites for decorations and units programmatically.
Each decoration type has a drawing function that creates recognizable
icons at small sizes (up to 32x32 pixels).
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    pass


class SpriteGenerator:
    """
    Generates pixel art sprites for decorations programmatically.

    Each decoration type has a drawing function that creates
    recognizable icons at small sizes (up to 32x32 pixels).
    """

    @staticmethod
    def generate_sprite(deco_type_name: str, variant: int = 0) -> pygame.Surface:
        """Generate sprite surface for a decoration type."""
        size = 32
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))  # Transparent background

        sprite_funcs = {
            'BUSH_SMALL': SpriteGenerator._draw_bush_small,
            'BUSH_DENSE': SpriteGenerator._draw_bush_dense,
            'TREE_OAK': SpriteGenerator._draw_tree_oak,
            'TREE_PINE': SpriteGenerator._draw_tree_pine,
            'ROCK_LARGE': SpriteGenerator._draw_rock_large,
            'ROCK_SMALL': SpriteGenerator._draw_rock_small,
            'RUBBLE_PILE': SpriteGenerator._draw_rubble,
            'CRATER_SMALL': SpriteGenerator._draw_crater_small,
            'CRATER_LARGE': SpriteGenerator._draw_crater_large,
            'TRENCH_SECTION': SpriteGenerator._draw_trench,
            'SANDBAG_WALL': SpriteGenerator._draw_sandbag,
            'BARBED_WIRE': SpriteGenerator._draw_barbed_wire,  # P1-4 Fix: New
            'WRECKAGE_VEHICLE': SpriteGenerator._draw_wreckage,
            'CAMOUFLAGE_NET': SpriteGenerator._draw_camo_net,

            # CC2特色装饰物 (STEP B - 对照CC2截图新增)
            'WRECKAGE_PLANE': SpriteGenerator._draw_plane_wreckage,      # ✈️ 飞机残骸
            'BARRICADE_CONCRETE': SpriteGenerator._draw_concrete_barricade,  # 🚧 混凝土路障
            'BARRICADE_SANDBAG': SpriteGenerator._draw_sandbag_barricade,   # 🛡️ 沙袋路障
            'CRATER_CLUSTER': SpriteGenerator._draw_crater_cluster,         # 💣 弹坑群
            'DEBRIS_FIELD': SpriteGenerator._draw_debris_field,             # 🗑️ 碎片场
            'BURNING_WRECKAGE': SpriteGenerator._draw_burning_wreckage,     # 🔥 燃烧残骸
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
                dist = math.sqrt((x-cx)**2 + (y-cy)**2)
                if dist < 7:
                    surface.set_at((x, y), color if dist > 4 else dark)

    @staticmethod
    def _draw_bush_dense(surface: pygame.Surface, variant: int) -> None:
        """Draw dense bush (larger, irregular shape)."""
        color = (28, 100, 28)
        dark = (18, 70, 18)
        points = [
            (10, 22), (13, 18), (16, 16), (19, 17), (22, 20),
            (23, 24), (20, 26), (16, 27), (12, 26), (9, 24)
        ]

        # Fill polygon
        for y in range(16, 28):
            for x in range(9, 24):
                if SpriteGenerator._point_in_polygon(x, y, points):
                    shade = color if (x+y+variant) % 3 != 0 else dark
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
        # Trunk (brown)
        trunk_color = (101, 67, 33)
        for y in range(18, 28):
            for x in range(14, 18):
                surface.set_at((x, y), trunk_color)

        # Canopy (green circle)
        canopy_colors = [(46, 125, 50), (36, 105, 40), (56, 145, 60)]
        cx, cy = 16, 12
        for y in range(2, 20):
            for x in range(4, 28):
                dist = math.sqrt((x-cx)**2 + (y-cy)**2)
                if dist < 10:
                    color_idx = int(dist / 3) % 3
                    surface.set_at((x, y), canopy_colors[color_idx])

    @staticmethod
    def _draw_tree_pine(surface: pygame.Surface, variant: int) -> None:
        """Draw coniferous tree (triangular)."""
        # Trunk
        trunk_color = (87, 53, 23)
        for y in range(22, 28):
            for x in range(14, 18):
                surface.set_at((x, y), trunk_color)

        # Triangular foliage (layered triangles)
        foliage_colors = [(20, 90, 25), (30, 110, 35), (25, 100, 30)]
        layers = [(16, 18, 10), (16, 12, 7), (16, 6, 4)]  # (cx, cy, half_width)

        for idx, (lcx, lcy, lw) in enumerate(layers):
            color = foliage_colors[idx]
            for y in range(lcy - lw*2, lcy + 2):
                width_at_y = int(lw * (1 - abs(y - lcy) / (lw*2 + 1)))
                for x in range(lcx - width_at_y, lcx + width_at_y + 1):
                    if 0 <= x < 32 and 0 <= y < 32:
                        surface.set_at((x, y), color)

    @staticmethod
    def _draw_rock_large(surface: pygame.Surface, variant: int) -> None:
        """Draw large boulder."""
        colors = [(128, 128, 128), (108, 108, 108), (148, 148, 148)]
        points = [
            (8, 24), (10, 18), (14, 14), (18, 12), (22, 14),
            (25, 18), (26, 23), (24, 26), (18, 27), (12, 26), (9, 25)
        ]

        for y in range(12, 28):
            for x in range(8, 27):
                if SpriteGenerator._point_in_polygon(x, y, points):
                    color_idx = (x + y + variant) % 3
                    surface.set_at((x, y), colors[color_idx])

        # Highlight
        surface.set_at((16, 14), (180, 180, 180))
        surface.set_at((17, 15), (170, 170, 170))

    @staticmethod
    def _draw_rock_small(surface: pygame.Surface, variant: int) -> None:
        """Draw small rock cluster."""
        color = (118, 118, 118)
        # Main rock
        points = [(12, 24), (14, 20), (18, 19), (21, 21), (22, 25), (19, 26), (14, 25)]
        for y in range(19, 27):
            for x in range(12, 23):
                if SpriteGenerator._point_in_polygon(x, y, points):
                    surface.set_at((x, y), color)

        # Small adjacent rock
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
                    if 0 <= px+dx < 32 and 0 <= py+dy < 32:
                        surface.set_at((px+dx, py+dy), color)

    @staticmethod
    def _draw_crater_small(surface: pygame.Surface, variant: int) -> None:
        """Draw small shell crater (ellipse with shadow)."""
        # Dark interior
        cx, cy = 16, 20
        for y in range(16, 26):
            for x in range(10, 22):
                norm_dist = ((x-cx)/6)**2 + ((y-cy)/4)**2
                if norm_dist < 1:
                    shade = int(40 + norm_dist * 30)
                    surface.set_at((x, y), (shade, shade-5, shade-10))

        # Raised rim (lighter)
        rim_color = (140, 135, 130)
        for angle in range(0, 360, 20):
            rad = math.radians(angle)
            rx = int(cx + 7 * math.cos(rad))
            ry = int(cy + 5 * math.sin(rad))
            if 0 <= rx < 32 and 0 <= ry < 32:
                surface.set_at((rx, ry), rim_color)

    @staticmethod
    def _draw_crater_large(surface: pygame.Surface, variant: int) -> None:
        """Draw large bomb crater."""
        # Dark center
        cx, cy = 16, 18
        for y in range(8, 28):
            for x in range(4, 28):
                norm_dist = ((x-cx)/12)**2 + ((y-cy)/8)**2
                if norm_dist < 1:
                    shade = int(35 + norm_dist * 40)
                    surface.set_at((x, y), (shade, shade-8, shade-15))

        # Rim
        rim_color = (130, 125, 120)
        for angle in range(0, 360, 12):
            rad = math.radians(angle)
            rx = int(cx + 13 * math.cos(rad))
            ry = int(cy + 10 * math.sin(rad))
            if 0 <= rx < 32 and 0 <= ry < 32:
                surface.set_at((rx, ry), rim_color)
                if 0 <= rx+1 < 32:
                    surface.set_at((rx+1, ry), rim_color)

    @staticmethod
    def _draw_trench(surface: pygame.Surface, variant: int) -> None:
        """Draw trench section (rectangular depression)."""
        # Dark interior
        for y in range(20, 28):
            for x in range(4, 28):
                surface.set_at((x, y), (70, 60, 50))

        # Sandbag wall on top edge
        bag_color = (180, 160, 120)
        for x in range(4, 28, 3):
            for y in range(18, 21):
                surface.set_at((x, y), bag_color)
                if x+1 < 28:
                    surface.set_at((x+1, y), bag_color)
                if x+2 < 28:
                    surface.set_at((x+2, y), (160, 140, 100))

    @staticmethod
    def _draw_sandbag(surface: pygame.Surface, variant: int) -> None:
        """Draw sandbag wall (P1-4 Fix: Enhanced with texture detail)."""
        bag_color = (190, 170, 130)
        shadow = (150, 130, 90)
        highlight = (210, 195, 160)

        for y in range(14, 26):
            for x in range(2, 30):
                is_bag = (x // 4 + y // 2) % 2 == 0
                if is_bag:
                    # P1-4: Add texture variation
                    if (x * y + variant) % 5 == 0:
                        color = highlight
                    elif (x + y) % 7 == 0:
                        color = shadow
                    else:
                        color = bag_color
                    surface.set_at((x, y), color)
                elif y in [15, 17, 19, 21, 23, 25]:
                    # Shadow between bags
                    surface.set_at((x, y), (120, 110, 85))

    @staticmethod
    def _draw_barbed_wire(surface: pygame.Surface, variant: int) -> None:
        """Draw barbed wire obstacle (P1-4 Fix: New decoration type)."""
        wire_color = (180, 180, 180)
        dark_wire = (120, 120, 120)

        # Horizontal wires (3 strands)
        for strand_y in [10, 16, 22]:
            for x in range(4, 28):
                # P1-4: Wavy wire pattern
                wave = math.sin(x * 0.5 + variant) * 2
                y = int(strand_y + wave)
                if 0 <= y < 32:
                    surface.set_at((x, y), wire_color if x % 3 != 0 else dark_wire)

        # Barbs (small V-shapes every 6 pixels)
        for barb_x in range(6, 28, 6):
            barb_y_base = 16 + int(math.sin(barb_x * 0.5 + variant) * 2)
            # Up-pointing barb
            surface.set_at((barb_x, barb_y_base - 2), dark_wire)
            surface.set_at((barb_x - 1, barb_y_base - 1), dark_wire)
            surface.set_at((barb_x + 1, barb_y_base - 1), dark_wire)
            # Down-pointing barb (offset)
            if barb_x % 12 == 0:
                surface.set_at((barb_x, barb_y_base + 2), dark_wire)
                surface.set_at((barb_x - 1, barb_y_base + 1), dark_wire)
                surface.set_at((barb_x + 1, barb_y_base + 1), dark_wire)

        # Posts (every 12 pixels)
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

        # Main hull shape (irregular)
        hull_points = [
            (6, 22), (8, 18), (12, 16), (18, 15), (24, 16),
            (26, 19), (27, 23), (25, 26), (18, 27), (10, 26), (7, 24)
        ]

        for y in range(15, 28):
            for x in range(6, 28):
                if SpriteGenerator._point_in_polygon(x, y, hull_points):
                    color = hull_color
                    if (x+y+variant) % 7 == 0:
                        color = rust
                    elif (x*y) % 11 == 0:
                        color = dark
                    surface.set_at((x, y), color)

        # Gun barrel stub
        for x in range(20, 28):
            surface.set_at((x, 17), dark)

    @staticmethod
    def _draw_camo_net(surface: pygame.Surface, variant: int) -> None:
        """Draw camouflage netting."""
        colors = [(45, 90, 45), (60, 75, 35), (35, 65, 40)]
        rng = random.Random(variant * 373)

        # Net pattern (grid with holes)
        for y in range(8, 24):
            for x in range(4, 28):
                if (x + y) % 3 == 0:
                    surface.set_at((x, y), (80, 75, 70))  # Net string
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
                if (x+y) % 2 == 0:
                    surface.set_at((x, y), color)

    # ===================================================================
    # CC2特色装饰物 (STEP B - 对照CC2截图实现)
    # ===================================================================

    @staticmethod
    def _draw_plane_wreckage(surface: pygame.Surface, variant: int) -> None:
        """Draw crashed aircraft wreckage (✈️ 飞机残骸).

        Based on CC2 screenshots: irregular wing+fuselage shape,
        dark metal color with rust patches, larger than vehicle wreckage.
        Common near airfields and drop zones.
        """
        fuselage_color = (55, 50, 45)
        wing_color = (60, 55, 50)
        rust = (110, 65, 25)
        dark_rust = (80, 45, 15)
        shadow = (35, 30, 25)

        # Fuselage (机身 - central elongated shape)
        fuselage_points = [
            (14, 8), (16, 7), (18, 8), (19, 12), (18, 20),
            (17, 24), (15, 26), (13, 24), (12, 20), (13, 12), (14, 8)
        ]

        for y in range(7, 27):
            for x in range(11, 21):
                if SpriteGenerator._point_in_polygon(x, y, fuselage_points):
                    # Rust variation
                    if (x + y + variant) % 9 == 0:
                        surface.set_at((x, y), rust)
                    elif (x * y) % 13 == 0:
                        surface.set_at((x, y), dark_rust)
                    else:
                        surface.set_at((x, y), fuselage_color)

        # Left wing (左翼 - swept back shape)
        left_wing = [
            (6, 14), (9, 13), (12, 14), (13, 16), (12, 18),
            (9, 17), (6, 16), (5, 15)
        ]
        for y in range(13, 19):
            for x in range(5, 14):
                if SpriteGenerator._point_in_polygon(x, y, left_wing):
                    shade = wing_color if (x + y) % 3 != 0 else shadow
                    surface.set_at((x, y), shade)

        # Right wing (右翼 - mirror of left)
        right_wing = [
            (26, 14), (23, 13), (20, 14), (19, 16), (20, 18),
            (23, 17), (26, 16), (27, 15)
        ]
        for y in range(13, 19):
            for x in range(19, 28):
                if SpriteGenerator._point_in_polygon(x, y, right_wing):
                    shade = wing_color if (x + y) % 3 != 0 else shadow
                    surface.set_at((x, y), shade)

        # Tail section (尾翼)
        for x in range(14, 19):
            surface.set_at((x, 6), dark_rust)

    @staticmethod
    def _draw_concrete_barricade(surface: pygame.Surface, variant: int) -> None:
        """Draw concrete anti-tank barricade (🚧 混凝土路障).

        Based on CC2 urban combat: X-shaped or angled concrete blocks,
        gray color with weathering, provides heavy cover.
        """
        concrete = (140, 135, 130)
        dark_concrete = (110, 105, 100)
        highlight = (160, 155, 150)
        shadow_edge = (90, 85, 80)

        # Main block (X-shaped barricade from top-down view looks like diamond)
        center_x, center_y = 16, 16

        # Diagonal bar 1 (top-left to bottom-right)
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

        # Diagonal bar 2 (bottom-left to top-right)
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
        """Draw sandbag defensive position (🛡️ 沙袋路障).

        Smaller than SANDBAG_WALL, used for individual firing positions.
        L-shaped or U-shaped layout visible from above.
        """
        bag_color = (160, 145, 110)
        bag_dark = (130, 115, 85)
        bag_shadow = (100, 90, 65)

        # U-shaped sandbag wall (3 sides)
        walls = [
            # Top wall (horizontal)
            [(8, 10), (8, 13), (24, 13), (24, 10)],
            # Left wall (vertical)
            [(8, 13), (11, 13), (11, 24), (8, 24)],
            # Right wall (vertical)
            [(21, 13), (24, 13), (24, 24), (21, 24)],
        ]

        for wall_idx, wall in enumerate(walls):
            for y in range(min(p[1] for p in wall), max(p[1] for p in wall)):
                for x in range(min(p[0] for p in wall), max(p[0] for p in wall)):
                    if SpriteGenerator._point_in_polygon(x, y, wall):
                        # Bag texture (individual bags ~3px each)
                        bag_idx = ((x - 8) // 3 + (y - 10) // 3 + variant) % 3
                        if bag_idx == 0:
                            color = bag_color
                        elif bag_idx == 1:
                            color = bag_dark
                        else:
                            color = bag_shadow

                        # Edge highlight
                        is_edge = (y == min(p[1] for p in wall) or
                                 y == max(p[1] for p in wall) - 1 or
                                 x == min(p[0] for p in wall) or
                                 x == max(p[0] for p in wall) - 1)
                        if is_edge:
                            color = tuple(min(255, c + 20) for c in color)

                        surface.set_at((x, y), color)

    @staticmethod
    def _draw_crater_cluster(surface: pygame.Surface, variant: int) -> None:
        """💣 增强版弹坑群 - 立体凹陷效果（参考CC2战斗8.jpeg）

        CC2特征：
        - 外圈边缘有亮色高光（模拟隆起的泥土边缘）
        - 内部是深色渐变（模拟凹陷阴影）
        - 形状略不规则（非完美圆形）
        - 可能有多个小坑聚集
        """
        cx, cy = 16, 16

        # 步骤1: 绘制外圈隆起边缘（亮棕色）
        rim_color = (90, 75, 55)  # 亮棕（隆起泥土）
        pygame.draw.ellipse(surface, rim_color,
                           (cx-14, cy-12, 28, 24))  # 外椭圆

        # 步骤2: 绘制主凹陷（深色渐变）
        # 使用多层圆模拟深度
        for i in range(5, 0, -1):
            depth_factor = i / 5.0
            radius = int(10 * depth_factor)
            darkness = int(25 + (1-depth_factor) * 35)  # 中心更深
            color = (darkness, darkness-5, darkness-8)  # 深灰褐
            offset_x = random.randint(-2, 2) * (6-i) // 3  # 不规则偏移
            offset_y = random.randint(-2, 2) * (6-i) // 3
            if radius > 0:
                pygame.draw.circle(surface, color,
                                 (cx+offset_x, cy+offset_y), radius)

        # 步骤3: 绘制高光边缘（左上角亮线模拟光照）
        highlight_color = (120, 105, 85)  # 边缘高光
        pygame.draw.arc(surface, highlight_color,
                       (cx-13, cy-11, 26, 22),
                       math.pi*1.2, math.pi*1.8, 2)  # 左上弧线

        # 步骤4: 添加随机碎石细节（3-5个小深色点）
        for _ in range(random.randint(3, 5)):
            rx = cx + random.randint(-10, 10)
            ry = cy + random.randint(-8, 8)
            r_size = random.randint(1, 3)
            debris_color = (60, 50, 40)
            pygame.draw.circle(surface, debris_color, (rx, ry), r_size)

        # 如果variant > 0，绘制额外的附属小坑
        if variant >= 1:
            offsets = [(8, -6), (-7, 4), (5, 8)]
            for i, (ox, oy) in enumerate(offsets[:min(variant, len(offsets))]):
                small_r = random.randint(4, 7)
                pygame.draw.ellipse(surface, (35, 30, 25),
                                  (cx+ox-small_r, oy+cy-int(small_r*0.7),
                                   small_r*2, int(small_r*1.4)))

    @staticmethod
    def _draw_debris_field(surface: pygame.Surface, variant: int) -> None:
        """Draw scattered debris field (🗑️ 碎片场).

        Small irregular fragments from destroyed structures/vehicles.
        Random pixel noise with some structure.
        """
        debris_colors = [
            (80, 75, 70),   # Metal
            (100, 95, 88),  # Light metal
            (120, 110, 100),# Wood/plastic
            (60, 55, 50),   # Dark debris
            (90, 85, 75),   # Mixed material
        ]
        bg = (0, 0, 0, 0)  # Transparent

        rng = random.Random(variant * 137)

        # Scatter 40-60 debris pixels
        num_debris = 40 + (variant % 20)
        for _ in range(num_debris):
            x = rng.randint(4, 27)
            y = rng.randint(4, 27)
            color = debris_colors[rng.randint(0, len(debris_colors) - 1)]

            # Draw 1-3 pixel clusters
            size = rng.randint(1, 3)
            for dx in range(size):
                for dy in range(size):
                    px, py = x + dx, y + dy
                    if 4 <= px < 28 and 4 <= py < 28:
                        # Slight color variation per pixel
                        variation = rng.randint(-8, 8)
                        final_color = tuple(
                            max(0, min(255, c + variation)) for c in color
                        )
                        surface.set_at((px, py), final_color)

        # Add a few larger structural pieces (2-3 per debris field)
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
        """Draw burning/destroyed wreckage (🔥 燃烧残骸).

        Vehicle or structure actively on fire.
        Dark hull with orange/red/yellow flame overlay.
        """
        hull_color = (50, 45, 40)
        flame_orange = (220, 120, 20)
        flame_red = (180, 50, 10)
        flame_yellow = (240, 200, 50)
        smoke_gray = (120, 120, 120)

        # Base wreckage hull (similar to _draw_wreckage but more damaged)
        hull_points = [
            (5, 20), (7, 16), (11, 14), (17, 13), (23, 14),
            (26, 17), (27, 22), (25, 26), (17, 27), (9, 26), (6, 23)
        ]

        for y in range(13, 28):
            for x in range(5, 28):
                if SpriteGenerator._point_in_polygon(x, y, hull_points):
                    surface.set_at((x, y), hull_color)

        # Flame areas (multiple fire points)
        fire_centers = [
            (12, 18), (18, 17), (22, 20)
        ]
        rng = random.Random(variant * 99)  # FIX: varant → variant

        for fcx, fcy in fire_centers[:2 + (variant % 2)]:
            # Flickering flames (irregular shapes)
            for y in range(fcy - 4, fcy + 5):
                for x in range(fcx - 4, fcx + 5):
                    dist = math.sqrt((x - fcx)**2 + (y - fcy)**2)
                    if dist <= 4.5 and rng.random() > 0.3:
                        # Color gradient: yellow core → orange → red edge
                        if dist < 1.5:
                            color = flame_yellow
                        elif dist < 2.8:
                            color = flame_orange
                        else:
                            color = flame_red

                        # Random flicker (some pixels transparent for flicker effect)
                        if rng.random() > 0.15:
                            surface.set_at((x, y), color)

        # Smoke plume (light gray pixels rising from fires)
        for smoke_y in range(8, 14):
            for smoke_x in range(10, 24):
                if rng.random() > 0.85:
                    alpha_smoke = (*smoke_gray, 150 - (smoke_y - 8) * 10)
                    surface.set_at((smoke_x, smoke_y), alpha_smoke)
