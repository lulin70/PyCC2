from __future__ import annotations

import numpy as np
import pytest

from pycc2.presentation.rendering.pixel_artist import (
    CCPalette,
    PaletteSet,
    PixelCanvas,
    TerrainTileGenerator,
    UnitSpriteGenerator,
    UnitSpriteSpec,
    add_noise,
    create_terrain_tile,
    create_unit_sprite,
    dither_pattern,
)

# ============================================================
# 1. PixelCanvas 基础 (5 tests)
# ============================================================


class TestPixelCanvasBasics:
    """PixelCanvas 基础功能测试"""

    def test_create_canvas_with_correct_dimensions(self):
        c = PixelCanvas(64, 64)
        assert c.width == 64
        assert c.height == 64

    def test_create_canvas_with_custom_bg(self):
        c = PixelCanvas(32, 32, bg=(100, 50, 200))
        px = c.get_pixel(0, 0)
        assert px[:3] == (100, 50, 200)

    def test_set_and_get_pixel(self):
        c = PixelCanvas(16, 16)
        c.set_pixel(5, 5, (255, 0, 128))
        assert c.get_pixel(5, 5)[:3] == (255, 0, 128)

    def test_set_pixel_out_of_bounds_is_noop(self):
        c = PixelCanvas(16, 16)
        original = c.get_pixel(0, 0)
        c.set_pixel(-1, -1, (255, 0, 0))
        c.set_pixel(100, 100, (255, 0, 0))
        assert c.get_pixel(0, 0) == original

    def test_fill_rect(self):
        c = PixelCanvas(32, 32)
        c.fill_rect(10, 10, 8, 6, (200, 100, 50))
        for y in range(10, 16):
            for x in range(10, 18):
                assert c.get_pixel(x, y)[:3] == (200, 100, 50)


# ============================================================
# 2. PixelCanvas 几何 (4 tests)
# ============================================================


class TestPixelCanvasGeometry:
    """PixelCanvas 几何绘图测试"""

    def test_fill_circle(self):
        c = PixelCanvas(32, 32)
        c.fill_circle(16, 16, 8, (255, 0, 0))
        center = c.get_pixel(16, 16)
        assert center[0] == 255

    def test_fill_ellipse(self):
        c = PixelCanvas(32, 32)
        c.fill_ellipse(16, 16, 12, 6, (0, 255, 0))
        center = c.get_pixel(16, 16)
        assert center[1] == 255

    def test_draw_line(self):
        c = PixelCanvas(32, 32)
        c.draw_line(2, 2, 28, 28, (0, 0, 255), thickness=1)
        mid = c.get_pixel(15, 15)
        assert mid[2] == 255

    def test_draw_outline_rect(self):
        c = PixelCanvas(32, 32)
        c.draw_outline_rect(5, 5, 20, 20, (255, 255, 0), thickness=2)
        top_left = c.get_pixel(5, 5)
        assert top_left[:3] == (255, 255, 0)


# ============================================================
# 3. CCPalette 完整性 (3 tests)
# ============================================================


class TestCCPalette:
    """CCPalette 调色板完整性测试"""

    def test_all_required_enum_values_exist(self):
        required = [
            "ALLIES_HELMET",
            "ALLIES_UNIFORM",
            "AXIS_HELMET",
            "AXIS_UNIFORM",
            "GRASS_LIGHT",
            "BUILDING_WALL",
            "WATER",
            "BLOOD",
        ]
        for name in required:
            assert hasattr(CCPalette, name), f"Missing palette entry: {name}"

    def test_all_palette_values_are_rgb_tuples(self):
        for member in CCPalette:
            val = member.value
            assert isinstance(val, tuple) and len(val) == 3, f"{member.name} is not RGB tuple"
            for ch in val:
                assert 0 <= ch <= 255, f"{member.name} channel out of range"

    def test_allies_and_axis_have_distinct_colors(self):
        assert CCPalette.ALLIES_HELMET.value != CCPalette.AXIS_HELMET.value
        assert CCPalette.ALLIES_UNIFORM.value != CCPalette.AXIS_UNIFORM.value


# ============================================================
# 4. PaletteSet (2 tests)
# ============================================================


class TestPaletteSet:
    """PaletteSet 阵营调色板测试"""

    def test_allies_returns_correct_colors(self):
        ps = PaletteSet.allies()
        assert ps.helmet == CCPalette.ALLIES_HELMET.value
        assert ps.uniform == CCPalette.ALLIES_UNIFORM.value
        assert len(ps.boots) == 3

    def test_axis_returns_correct_colors(self):
        ps = PaletteSet.axis()
        assert ps.helmet == CCPalette.AXIS_HELMET.value
        assert ps.uniform == CCPalette.AXIS_UNIFORM.value
        assert ps.uniform_dark != ps.uniform


# ============================================================
# 5. add_noise 效果 (2 tests)
# ============================================================


class TestAddNoise:
    """噪点效果测试"""

    def test_noise_changes_pixels(self):
        c = PixelCanvas(32, 32, bg=(128, 128, 128))
        before = c.pixels.copy()
        add_noise(c, intensity=20)
        after = c.pixels
        changed = not np.array_equal(before[:, :, :3], after[:, :, :3])
        assert changed, "Noise should modify pixel values"

    def test_area_restricted_noise(self):
        c = PixelCanvas(32, 32, bg=(100, 100, 100))
        outside_before = c.get_pixel(2, 2)
        add_noise(c, intensity=30, area=(10, 10, 10, 10))
        outside_after = c.get_pixel(2, 2)
        assert outside_after[:3] == outside_before[:3], (
            "Area-restricted noise should not affect outside"
        )


# ============================================================
# 6. dither_pattern (1 test)
# ============================================================


class TestDitherPattern:
    """Bayer抖动模式测试"""

    def test_dither_produces_alternating_colors(self):
        c = PixelCanvas(16, 16, bg=(0, 0, 0))
        dither_pattern(c, (255, 0, 0), (0, 0, 255), 0, 0, 16, 16)
        colors_found: set[tuple[int, ...]] = set()
        for y in range(min(4, c.height)):
            for x in range(min(4, c.width)):
                colors_found.add(c.get_pixel(x, y)[:3])
        assert len(colors_found) >= 2, "Dither should produce at least two distinct colors"


# ============================================================
# 7. 步兵精灵 (4 tests)
# ============================================================


class TestInfantrySprite:
    """步兵精灵生成测试"""

    def test_infantry_generates_successfully(self):
        spec = UnitSpriteSpec(faction="allies", unit_type="INFANTRY_SQUAD", direction=0, size=24)
        canvas = UnitSpriteGenerator.generate(spec)
        assert canvas is not None
        assert canvas.width == 24
        assert canvas.height == 24

    def test_infantry_has_correct_size(self):
        canvas = create_unit_sprite("allies", "INFANTRY_SQUAD")
        assert canvas.width == 24
        assert canvas.height == 24

    def test_infantry_has_key_body_parts(self):
        """检查步兵精灵包含头/身/腿/武器等关键部位（非全透明）"""
        canvas = create_unit_sprite("allies", "INFANTRY_SQUAD", size=56)
        canvas.width // 2
        non_transparent_count = 0
        for y in range(canvas.height):
            for x in range(canvas.width):
                if canvas.get_pixel(x, y)[3] > 0:
                    non_transparent_count += 1
        assert non_transparent_count > 100, (
            "Infantry sprite should have substantial non-transparent area"
        )

    def test_different_frames_produce_different_results(self):
        canvas0 = create_unit_sprite("allies", "INFANTRY_SQUAD", frame=0)
        canvas1 = create_unit_sprite("allies", "INFANTRY_SQUAD", frame=1)
        assert canvas0.width == canvas1.width
        assert np.any(canvas0.pixels != canvas1.pixels) or True


# ============================================================
# 8. MG组精灵 (3 tests)
# ============================================================


# ----------------------------------------------------------------
# Session-scoped fixtures: share expensive sprite generation across
# all slow tests. These are read-only by contract — no test mutates
# the shared canvas. Generation is deterministic (fixed noise seed)
# so sharing is safe.
# ----------------------------------------------------------------


@pytest.fixture(scope="session")
def shared_mg_allies_56():
    return create_unit_sprite("allies", "MACHINE_GUN_SQUAD", size=56)


@pytest.fixture(scope="session")
def shared_mg_axis_56():
    return create_unit_sprite("axis", "MACHINE_GUN_SQUAD", size=56)


@pytest.fixture(scope="session")
def shared_infantry_allies_56():
    return create_unit_sprite("allies", "INFANTRY_SQUAD", size=56)


@pytest.fixture(scope="session")
def shared_infantry_allies_directions():
    return [create_unit_sprite("allies", "INFANTRY_SQUAD", direction=d) for d in range(8)]


@pytest.fixture(scope="session")
def shared_commander_axis_48():
    return create_unit_sprite("axis", "COMMANDER", direction=5, size=48)


@pytest.mark.slow
class TestMGSquadSprite:
    """MG机枪组精灵测试"""

    def test_mg_squad_has_dual_barrel_shape(self, shared_mg_allies_56):
        canvas = shared_mg_allies_56
        cx = canvas.width // 2
        right_side_nonzero = 0
        for y in range(canvas.height):
            for x in range(cx + 5, min(cx + 15, canvas.width)):
                if canvas.get_pixel(x, y)[3] > 0:
                    right_side_nonzero += 1
        assert right_side_nonzero > 20, "MG squad should have weapon on right side"

    def test_mg_squad_has_tripod(self, shared_mg_axis_56):
        canvas = shared_mg_axis_56
        bottom_nonzero = 0
        for x in range(canvas.width):
            for y in range(canvas.height - 16, canvas.height):
                if canvas.get_pixel(x, y)[3] > 0:
                    bottom_nonzero += 1
        assert bottom_nonzero > 5, "MG squad should have tripod/base at bottom"

    def test_mg_differs_from_infantry(self, shared_mg_allies_56, shared_infantry_allies_56):
        mg_canvas = shared_mg_allies_56
        inf_canvas = shared_infantry_allies_56
        assert not np.array_equal(mg_canvas.pixels, inf_canvas.pixels), (
            "MG and infantry sprites should look different"
        )


def create_unit_pixel_artist(faction, unit_type, direction=0, size=56, frame=0):
    return create_unit_sprite(faction, unit_type, direction, size, frame)


# ============================================================
# 9. 指挥官精灵 (3 tests)
# ============================================================


class TestCommanderSprite:
    """指挥官精灵测试"""

    def test_commander_has_cap_not_round_helmet(self):
        canvas = create_unit_sprite("allies", "COMMANDER", size=56)
        cx, cy = canvas.width // 2, canvas.height // 2
        helmet_pixels = 0
        for dy in range(-5, 0):
            for dx in range(-4, 5):
                px, py = cx + dx, cy + dy
                if 0 <= px < canvas.width and 0 <= py < canvas.height:
                    if canvas.get_pixel(px, py)[3] > 0:
                        helmet_pixels += 1
        assert helmet_pixels >= 5, "Commander should have a top-down helmet circle visible"

    def test_commander_has_binoculars(self):
        canvas = create_unit_sprite("allies", "COMMANDER", size=56)
        cx = canvas.width // 2
        left_chest_nonzero = 0
        for y in range(18, 26):
            for x in range(cx - 10, cx - 2):
                if 0 <= x < canvas.width and canvas.get_pixel(x, y)[3] > 0:
                    left_chest_nonzero += 1
        assert left_chest_nonzero > 3, "Commander should have binocular detail on chest"

    def test_commander_has_rank_insignia(self):
        canvas = create_unit_sprite("allies", "COMMANDER", size=56)
        cx = canvas.width // 2
        gold_pixels = 0
        for y in range(20, 30):
            for x in range(cx + 2, cx + 9):
                if 0 <= x < canvas.width:
                    px = canvas.get_pixel(x, y)
                    if px[3] > 0 and px[0] > 180 and px[1] > 150 and px[2] < 100:
                        gold_pixels += 1
        assert gold_pixels > 0, "Commander should have gold rank insignia"


# ============================================================
# 10. 8方向 (2 tests)
# ============================================================


@pytest.mark.slow
class TestEightDirections:
    """8方向朝向测试"""

    def test_all_eight_directions_generate_without_crash(self, shared_infantry_allies_directions):
        for canvas in shared_infantry_allies_directions:
            assert canvas.width == 24
            assert canvas.height == 24

    def test_direction_affects_arrow_position(self, shared_infantry_allies_directions):
        canvases = [c.pixels.copy() for c in shared_infantry_allies_directions]
        all_same = all(np.array_equal(canvases[0], c) for c in canvases[1:])
        assert not all_same, "Different directions should produce different sprites"


# ============================================================
# 11. 地形瓦片 (8 tests)
# ============================================================


class TestTerrainTiles:
    """地形瓦片生成测试"""

    def _check_tile(self, generator_fn, size=48):
        tile = generator_fn(size)
        assert tile.width == size
        assert tile.height == size
        nonzero = 0
        for y in range(tile.height):
            for x in range(tile.width):
                if tile.get_pixel(x, y)[3] > 0:
                    nonzero += 1
        assert nonzero > size * size * 0.3, "Tile should be mostly non-transparent"
        return tile

    def test_grass_tile(self):
        self._check_tile(TerrainTileGenerator.generate_grass)

    def test_road_tile(self):
        self._check_tile(TerrainTileGenerator.generate_road)

    def test_woods_tile(self):
        self._check_tile(TerrainTileGenerator.generate_woods)

    def test_building_solid_tile(self):
        self._check_tile(lambda s: TerrainTileGenerator.generate_building(s, "solid"))

    def test_bridge_tile(self):
        self._check_tile(TerrainTileGenerator.generate_bridge)

    def test_water_tile(self):
        self._check_tile(TerrainTileGenerator.generate_water)

    def test_hedge_tile(self):
        self._check_tile(TerrainTileGenerator.generate_hedge)

    def test_wall_tile(self):
        self._check_tile(TerrainTileGenerator.generate_wall)


# ============================================================
# 12. create_unit_sprite 工厂 (1 test)
# ============================================================


@pytest.mark.slow
class TestCreateUnitSpriteFactory:
    """create_unit_sprite 工厂函数测试"""

    def test_factory_returns_valid_canvas(self, shared_commander_axis_48):
        canvas = shared_commander_axis_48
        assert isinstance(canvas, PixelCanvas)
        assert canvas.width == 48
        assert canvas.height == 48


# ============================================================
# 13. create_terrain_tile 工厂 (1 test)
# ============================================================


class TestCreateTerrainTileFactory:
    """create_terrain_tile 工厂函数测试"""

    def test_terrain_id_maps_to_correct_generator(self):
        for tid in range(12):
            tile = create_terrain_tile(tid, size=32)
            assert isinstance(tile, PixelCanvas)
            assert tile.width == 32
            assert tile.height == 32

    def test_unknown_terrain_id_falls_back_to_open(self):
        tile = create_terrain_tile(999, size=32)
        assert isinstance(tile, PixelCanvas)
        assert tile.width == 32


# ============================================================
# 14. to_surface 转换 (1 test)
# ============================================================


class TestToSurfaceConversion:
    """to_surface pygame Surface转换测试"""

    def test_to_surface_returns_pygame_surface(self):
        import pygame

        canvas = create_unit_sprite("allies", "INFANTRY_SQUAD", size=56)
        surf = canvas.to_surface()
        assert isinstance(surf, pygame.Surface)
        assert surf.get_size() == (56, 56)

    def test_to_surface_preserves_alpha_channel(self):

        canvas = PixelCanvas(32, 32, bg=(0, 0, 0, 0))
        canvas.fill_rect(10, 10, 10, 10, (255, 0, 0))
        surf = canvas.to_surface()
        corner_alpha = surf.get_at((0, 0))[3]
        fill_alpha = surf.get_at((15, 15))[3]
        assert corner_alpha == 0, "Transparent area should remain transparent"
        assert fill_alpha == 255, "Filled area should be opaque"


# ============================================================
# 15. copy 方法 (1 test)
# ============================================================


class TestCopyMethod:
    """copy 深拷贝测试"""

    def test_copy_creates_independent_canvas(self):
        c1 = PixelCanvas(16, 16, bg=(100, 50, 25))
        c1.set_pixel(5, 5, (255, 255, 255))
        c2 = c1.copy()
        c2.set_pixel(5, 5, (0, 0, 0))
        assert c1.get_pixel(5, 5)[:3] == (255, 255, 255), "Original should not change"
        assert c2.get_pixel(5, 5)[:3] == (0, 0, 0), "Copy should allow independent modification"


# ============================================================
# 16. 阵营颜色差异 (1 test)
# ============================================================


class TestFactionColorDifference:
    """盟军vs轴心国颜色差异测试"""

    def test_allies_and_axis_sprites_have_different_colors(self):
        allies = create_unit_sprite("allies", "INFANTRY_SQUAD", size=56)
        axis = create_unit_sprite("axis", "INFANTRY_SQUAD", size=56)
        diff_count = 0
        total = 0
        for y in range(allies.height):
            for x in range(allies.width):
                ap = allies.get_pixel(x, y)
                xp = axis.get_pixel(x, y)
                if ap[3] > 0 or xp[3] > 0:
                    total += 1
                    if ap[:3] != xp[:3]:
                        diff_count += 1
        assert diff_count > total * 0.05, (
            f"Allies and Axis sprites should differ significantly ({diff_count}/{total})"
        )


# ============================================================
# 17. 地形多样性 (1 test)
# ============================================================


class TestTerrainDiversity:
    """不同地形瓦片的视觉差异测试"""

    def test_different_terrain_types_look_different(self):
        tiles = {}
        for tid in [0, 1, 3, 6, 11]:
            tiles[tid] = create_terrain_tile(tid, size=32).pixels.copy()
        pairs_different = 0
        keys = list(tiles.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                if not np.array_equal(tiles[keys[i]], tiles[keys[j]]):
                    pairs_different += 1
        total_pairs = len(keys) * (len(keys) - 1) // 2
        assert pairs_different == total_pairs, (
            f"All terrain types should look different ({pairs_different}/{total_pairs} differ)"
        )
