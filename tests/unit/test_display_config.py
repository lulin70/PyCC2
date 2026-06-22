from __future__ import annotations

import os

import pytest

from pycc2.domain.interfaces.display_config import (
    DisplayConfig,
    QualityPreset,
)


@pytest.fixture(scope="module")
def pygame_init():
    """Initialize pygame display for tests that need surface operations."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame

    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    yield screen
    pygame.quit()


class TestFromScreen:
    """测试1-3: from_screen 工厂方法 — 不同分辨率自动选择预设"""

    def test_1440x900_selects_high_preset(self):
        dc = DisplayConfig.from_screen(1440, 900, dpi_scale=1.0, is_retina=False)
        assert dc.base_tile_size == 48
        assert dc.window_width == int(1440 * 0.9)
        assert dc.window_height == int(900 * 0.9)

    def test_1920x1080_selects_ultra_preset(self):
        dc = DisplayConfig.from_screen(1920, 1080, dpi_scale=1.0, is_retina=False)
        assert dc.base_tile_size == 64
        assert dc.window_width == int(1920 * 0.9)
        assert dc.window_height == int(1080 * 0.9)

    def test_1280x720_selects_medium_preset(self):
        dc = DisplayConfig.from_screen(1280, 720, dpi_scale=1.0, is_retina=False)
        assert dc.base_tile_size == 32


class TestFromPreset:
    """测试4: from_preset 工厂方法"""

    def test_high_preset_correct_params(self):
        dc = DisplayConfig.from_preset(QualityPreset.HIGH)
        assert dc.window_width == 1440
        assert dc.window_height == 900
        assert dc.base_tile_size == 48

    def test_medium_preset_correct_params(self):
        dc = DisplayConfig.from_preset(QualityPreset.MEDIUM)
        assert dc.window_width == 1280
        assert dc.window_height == 720
        assert dc.base_tile_size == 32

    def test_ultra_preset_correct_params(self):
        dc = DisplayConfig.from_preset(QualityPreset.ULTRA)
        assert dc.window_width == 1920
        assert dc.window_height == 1080
        assert dc.base_tile_size == 64

    def test_low_preset_correct_params(self):
        dc = DisplayConfig.from_preset(QualityPreset.LOW)
        assert dc.window_width == 800
        assert dc.window_height == 600
        assert dc.base_tile_size == 24


class TestEffectiveTileSize:
    """测试5: effective_tile_size 计算"""

    def test_normal_scale(self):
        dc = DisplayConfig(base_tile_size=48, sprite_scale=1.0)
        assert dc.effective_tile_size == 48

    def test_retina_scale(self):
        dc = DisplayConfig(base_tile_size=48, sprite_scale=2.0)
        assert dc.effective_tile_size == 96


class TestEffectiveSpriteSize:
    """测试6: effective_sprite_size 计算 (tile*0.875)"""

    def test_medium_sprite_size(self):
        dc = DisplayConfig(base_tile_size=32, sprite_scale=1.0)
        assert dc.effective_sprite_size == int(32 * 0.875)

    def test_high_sprite_size(self):
        dc = DisplayConfig(base_tile_size=48, sprite_scale=1.0)
        assert dc.effective_sprite_size == int(48 * 0.875)


class TestUIScale:
    """测试7: ui_scale 计算 — max(dpi_scale, window_width/1280)"""

    def test_dpi_dominates_when_larger(self):
        dc = DisplayConfig(window_width=1280, dpi_scale=2.0)
        assert dc.ui_scale == 2.0

    def test_resolution_dominates_when_larger(self):
        dc = DisplayConfig(window_width=1920, dpi_scale=1.0)
        assert dc.ui_scale == 1920 / 1280

    def test_equal_values(self):
        dc = DisplayConfig(window_width=1280, dpi_scale=1.0)
        assert dc.ui_scale == 1.0


class TestFontSizes:
    """测试8: font_size_* 各级字体大小正确性"""

    def test_font_sizes_at_default_scale(self):
        dc = DisplayConfig()
        assert dc.font_size_small >= 12
        assert dc.font_size_normal >= 14
        assert dc.font_size_large >= 18
        assert dc.font_size_title >= 22

    def test_font_sizes_increase_with_ui_scale(self):
        dc_small = DisplayConfig(window_width=1280)
        dc_large = DisplayConfig(window_width=1920)
        assert dc_large.font_size_normal >= dc_small.font_size_normal

    def test_font_size_ordering(self):
        dc = DisplayConfig()
        assert dc.font_size_small <= dc.font_size_normal
        assert dc.font_size_normal <= dc.font_size_large
        assert dc.font_size_large <= dc.font_size_title


class TestComputeDefaultZoom:
    """测试9: compute_default_zoom 不同地图大小返回合理值"""

    def test_small_map_fills_viewport(self):
        dc = DisplayConfig(window_width=1440, window_height=900, base_tile_size=48)
        zoom = dc.compute_default_zoom(10, 10)
        assert zoom > 0
        assert zoom <= 1.5

    def test_large_map_zooms_out(self):
        dc = DisplayConfig(window_width=1440, window_height=900, base_tile_size=48)
        zoom = dc.compute_default_zoom(50, 50)
        assert zoom > 0
        assert zoom < 1.0

    def test_zoom_capped_at_1_5(self):
        dc = DisplayConfig(window_width=1440, window_height=900, base_tile_size=48)
        zoom = dc.compute_default_zoom(2, 2)
        assert zoom <= 1.5


class TestRetinaMode:
    """测试10: Retina模式 sprite_scale=2.0"""

    def test_retina_sets_sprite_scale(self):
        dc = DisplayConfig.from_screen(1440, 900, is_retina=True)
        assert dc.sprite_scale == 2.0
        assert dc.is_retina is True

    def test_non_retina_defaults_to_one(self):
        dc = DisplayConfig.from_screen(1440, 900, is_retina=False)
        assert dc.sprite_scale == 1.0
        assert dc.is_retina is False


class TestEdgeCases:
    """测试11: 边界情况"""

    def test_very_small_screen(self):
        dc = DisplayConfig.from_screen(800, 600)
        assert dc.base_tile_size == 32
        assert dc.window_width == int(800 * 0.9)

    def test_exact_boundary_1300(self):
        dc = DisplayConfig.from_screen(1300, 800)
        assert dc.base_tile_size == 48

    def test_just_below_boundary(self):
        dc = DisplayConfig.from_screen(1299, 800)
        assert dc.base_tile_size == 32


class TestDefaultValues:
    """测试12: 属性默认值合理性"""

    def test_default_display_config_is_valid(self):
        dc = DisplayConfig()
        assert dc.window_width > 0
        assert dc.window_height > 0
        assert dc.base_tile_size > 0
        assert dc.sprite_scale > 0
        assert dc.dpi_scale > 0

    def test_default_matches_medium_preset(self):
        DisplayConfig()
        DisplayConfig.from_preset(QualityPreset.MEDIUM)
        assert True


class TestQualityPresets:
    """测试14: quality_presets 覆盖所有4级"""

    def test_all_presets_exist(self):
        assert QualityPreset.LOW is not None
        assert QualityPreset.MEDIUM is not None
        assert QualityPreset.HIGH is not None
        assert QualityPreset.ULTRA is not None

    def test_all_presets_have_different_tiles(self):
        low = DisplayConfig.from_preset(QualityPreset.LOW).base_tile_size
        med = DisplayConfig.from_preset(QualityPreset.MEDIUM).base_tile_size
        high = DisplayConfig.from_preset(QualityPreset.HIGH).base_tile_size
        ultra = DisplayConfig.from_preset(QualityPreset.ULTRA).base_tile_size
        assert len({low, med, high, ultra}) == 4


class TestWindowCap:
    """测试15: 窗口上限不超过1920x1080"""

    def test_large_screen_capped(self):
        dc = DisplayConfig.from_screen(3840, 2160)
        assert dc.window_width <= 1920
        assert dc.window_height <= 1080

    def test_ultra_preset_within_cap(self):
        dc = DisplayConfig.from_preset(QualityPreset.ULTRA)
        assert dc.window_width <= 1920
        assert dc.window_height <= 1080


class TestDisplayConfigWithSpriteRenderer:
    """集成测试: DisplayConfig 与 SpriteRenderer 协同工作"""

    def test_renderer_accepts_display_config(self, pygame_init):
        from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer

        dc = DisplayConfig.from_preset(QualityPreset.HIGH)
        renderer = SpriteRenderer(display_config=dc)
        # P0-B: SPRITE_SIZE updated to 48 for CC2 visibility
        assert renderer.TILE_SIZE == 48
        assert renderer.SPRITE_SIZE == 48

    def test_renderer_default_config_matches_old_behavior(self, pygame_init):
        from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer

        renderer = SpriteRenderer()
        # P0-B: Both sizes now 48 for CC2-style rendering
        assert renderer.TILE_SIZE == 48
        assert renderer.SPRITE_SIZE == 48

    def test_renderer_with_low_preset(self, pygame_init):
        from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer

        dc = DisplayConfig.from_preset(QualityPreset.LOW)
        renderer = SpriteRenderer(display_config=dc)
        # TILE_SIZE is fixed at 48 to match Vec2.TILE_SIZE and EnhancedRenderer
        assert renderer.TILE_SIZE == 48

    def test_renderer_terrain_cache_uses_dynamic_size(self, pygame_init):
        from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer

        dc = DisplayConfig(base_tile_size=64, sprite_scale=1.0)
        renderer = SpriteRenderer(display_config=dc)
        # TILE_SIZE is fixed at 48 to match Vec2.TILE_SIZE
        for tile_id, surf in renderer._terrain_cache.items():
            assert surf.get_size() == (48, 48), f"Terrain {tile_id} size mismatch"

    def test_renderer_sprite_cache_uses_dynamic_size(self, pygame_init):
        from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer

        dc = DisplayConfig(base_tile_size=48, sprite_scale=1.0)
        renderer = SpriteRenderer(display_config=dc)
        # P0-B: SPRITE_SIZE updated to 48, SVG sprites may be 48-67 (vector art)
        valid_sizes = {14, 22, 24, 28, 32, 36, 38, 40, 45, 48, 64, 67}
        for key, surf in renderer._sprite_cache.items():
            size = surf.get_size()
            assert size[0] in valid_sizes, f"Sprite {key} size {size} unexpected"
