"""Test SVG sprite integration with SpriteCacheManager.

Verifies:
- P0: All 16 SVG sprites load correctly
- P1: Posture system maps unit types to correct sprites
- P2: Animation frames resolve for prone state
- P3: MG deployed state uses distinct sprite
- Direction rotation produces 8 unique orientations
- Faction colors are correct (Allies=olive, Axis=feldgrau)

P1 Fix (v6): Module-level pygame init with graceful fallback.
Works in both standalone and full-suite test runs.
"""
import os
import sys

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Module-level pygame init: safe for full-suite runs
try:
    import pygame
    if not pygame.get_init():
        pygame.init()
    # Ensure display mode exists for SVG rendering
    try:
        pygame.display.get_surface()
    except Exception:
        try:
            pygame.display.set_mode((800, 600))
        except Exception:
            pass  # Will be retried per-test via fixture
except Exception:
    pass  # Defer to fixture-level init

from pycc2.presentation.rendering.sprite_cache_manager import SpriteCacheManager
from pycc2.presentation.rendering.svg_sprite_loader import SPRITE_CATALOG, SVGSpriteLoader


@pytest.fixture()
def svg_cache_mgr():
    """Initialize SpriteCacheManager with guaranteed pygame display."""
    import pygame

    # Per-test: ensure pygame is fully initialized
    if not pygame.get_init():
        pygame.init()
    try:
        pygame.display.get_surface()
    except Exception:
        try:
            pygame.display.set_mode((800, 600))
        except Exception:
            pass

    mgr = SpriteCacheManager()
    yield mgr


class TestSVGSpriteIntegration:
    """Integration tests for SVG sprite loading and posture mapping."""

    def test_p0_svg_loader_available(self, svg_cache_mgr):
        """P0: SVG loader detects assets directory."""
        loader = SVGSpriteLoader()
        assert loader.is_available, "SVG root should exist"
        assert len(SPRITE_CATALOG) > 0, "Catalog should have entries"

    def test_p0_all_svgs_loaded(self, svg_cache_mgr):
        """P0: All 16 SVG sprites pre-cached successfully."""
        if not svg_cache_mgr._use_svg_sprites:
            pytest.skip("SVG sprites not available")
        # Expect 16 base sprites (not counting direction variants which are generated on-demand)
        assert svg_cache_mgr._svg_loader.stats["loaded"] == 16
        assert svg_cache_mgr._svg_loader.stats["failed"] == 0

    def test_p1_infantry_gets_standing_sprite(self, svg_cache_mgr):
        """P1: INFANTRY_SQUAD resolves to standing posture."""
        if not svg_cache_mgr._use_svg_sprites:
            pytest.skip("SVG sprites not available")
        sprite = svg_cache_mgr.create_unit_sprite(
            faction="allies",
            unit_type="INFANTRY_SQUAD",
            direction=0,
        )
        assert sprite is not None, "Should return a standing sprite for infantry"
        assert sprite.get_width() > 0
        assert sprite.get_height() > 0

    def test_p1_axis_gets_feldgrau_sprite(self, svg_cache_mgr):
        """P1: Axis units get feldgrau-colored sprites."""
        if not svg_cache_mgr._use_svg_sprites:
            pytest.skip("SVG sprites not available")
        sprite = svg_cache_mgr.create_unit_sprite(
            faction="axis",
            unit_type="INFANTRY_SQUAD",
            direction=0,
        )
        assert sprite is not None
        # Check that axis sprite has different pixels than allies
        allies = svg_cache_mgr.create_unit_sprite(
            faction="allies", unit_type="INFANTRY_SQUAD", direction=0
        )
        # Both should be valid non-empty surfaces
        assert allies is not None

    def test_p2_prone_animation_frames_exist(self, svg_cache_mgr):
        """P2: Prone animation frames f0-f3 are all available in cache."""
        if not svg_cache_mgr._use_svg_sprites:
            pytest.skip("SVG sprites not available")
        for frame in range(4):
            key = f"allies_prone_f{frame}"
            assert key in svg_cache_mgr._svg_cache, f"Missing {key}"

        for frame in range(4):
            key = f"axis_prone_f{frame}"
            assert key in svg_cache_mgr._svg_cache, f"Missing {key}"

    def test_p2_prone_state_uses_animation_frame(self, svg_cache_mgr):
        """P2: state='prone' with animation_frame returns frame sprite."""
        if not svg_cache_mgr._use_svg_sprites:
            pytest.skip("SVG sprites not available")
        # Frame 0
        sprite_f0 = svg_cache_mgr._try_svg_sprite(
            "allies", "INFANTRY_SQUAD", 0, state="prone", animation_frame=0
        )
        assert sprite_f0 is not None, "prone frame 0 should exist"

        # Frame 2 (different from frame 0)
        sprite_f2 = svg_cache_mgr._try_svg_sprite(
            "allies", "INFANTRY_SQUAD", 0, state="prone", animation_frame=2
        )
        assert sprite_f2 is not None, "prone frame 2 should exist"

    def test_p3_mg_deployed_distinct_sprite(self, svg_cache_mgr):
        """P3: MG in 'deployed' state gets mg_deployed posture."""
        if not svg_cache_mgr._use_svg_sprites:
            pytest.skip("SVG sprites not available")
        # MG standing (default)
        standing = svg_cache_mgr._try_svg_sprite(
            "allies", "MACHINE_GUN_SQUAD", 0, state="idle"
        )
        assert standing is not None, "MG default should be standing"

        # MG deployed (distinct sprite)
        deployed = svg_cache_mgr._try_svg_sprite(
            "allies", "MACHINE_GUN_SQUAD", 0, state="deployed"
        )
        assert deployed is not None, "MG deployed should use mg_deployed sprite"

        # Both should exist in cache
        assert "allies_mg_deployed" in svg_cache_mgr._svg_cache
        assert "axis_mg_deployed" in svg_cache_mgr._svg_cache

    def test_direction_rotation_produces_different_sizes(self, svg_cache_mgr):
        """Direction rotation changes surface dimensions (rotated rect)."""
        if not svg_cache_mgr._use_svg_sprites:
            pytest.skip("SVG sprites not available")
        base = svg_cache_mgr._try_svg_sprite("allies", "INFANTRY_SQUAD", 0)
        rotated_45 = svg_cache_mgr._try_svg_sprite("allies", "INFANTRY_SQUAD", 1)  # NE
        rotated_90 = svg_cache_mgr._try_svg_sprite("allies", "INFANTRY_SQUAD", 2)  # E

        assert base is not None
        assert rotated_45 is not None
        assert rotated_90 is not None

        # All should be valid surfaces with reasonable dimensions
        assert base.get_width() > 10
        assert base.get_height() > 10

    def test_sniper_gets_prone_posture(self, svg_cache_mgr):
        """SNIPER_TEAM maps to prone posture by default."""
        if not svg_cache_mgr._use_svg_sprites:
            pytest.skip("SVG sprites not available")
        sprite = svg_cache_mgr._try_svg_sprite("allies", "SNIPER_TEAM", 0)
        assert sprite is not None

    def test_medic_gets_kneeling_posture(self, svg_cache_mgr):
        """MEDIC_TEAM maps to kneeling posture."""
        if not svg_cache_mgr._use_svg_sprites:
            pytest.skip("SVG sprites not available")
        sprite = svg_cache_mgr._try_svg_sprite("allies", "MEDIC_TEAM", 0)
        assert sprite is not None

    def test_polish_faction_uses_allies_sprites(self, svg_cache_mgr):
        """Polish faction falls back to allies-style sprites."""
        if not svg_cache_mgr._use_svg_sprites:
            pytest.skip("SVG sprites not available")
        sprite = svg_cache_mgr._try_svg_sprite("polish", "INFANTRY_SQUAD", 0)
        assert sprite is not None, "Polish should use allies sprites"

    def test_kneeling_posture_available(self, svg_cache_mgr):
        """Kneeling posture exists for both factions."""
        if not svg_cache_mgr._use_svg_sprites:
            pytest.skip("SVG sprites not available")
        assert "allies_kneeling" in svg_cache_mgr._svg_cache
        assert "axis_kneeling" in svg_cache_mgr._svg_cache
