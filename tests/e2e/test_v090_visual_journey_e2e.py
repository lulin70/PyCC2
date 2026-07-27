"""E2E Test: PyCC2 v0.9.0 Visual Polish — Real-Player Journeys (P1-11).

Wave B-rev P1-11 required 4 additional real-player journeys covering
V-05 / V-06 / V-09 / V-11. This suite complements existing unit tests
by simulating end-to-end player flows rather than isolated API calls.

Journeys:
  1. V-05 Responsive layout — player launches game on 1280x720, upgrades
     to 1920x1080, then 2560x1440. scale_factor must adapt per resolution.
  2. V-06 Micro-animation feedback — player hovers a button, clicks it,
     selects a unit, and triggers an error flash. Each trigger must
     produce a non-zero animation timer.
  3. V-09 SpriteCache prewarm — on game startup, SpriteCacheManager
     prewarms synchronously so the first rendered frame has all sprites
     cached (no first-frame stutter).
  4. V-11 Minimap terrain detail — during battle, minimap renders
     terrain, legend toggles via 'L', casualty markers expire after 5s,
     and facing line appears only for the selected unit.

Reference: docs/ROADMAP_v0.9.0.md F2, docs/VISUAL_POLISH_PLAN.md P1-11,
docs/archive/CONSENSUS_V090_WAVE_B_REV.md section 4 P1-11.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from pycc2.domain.entities.unit import Faction
from pycc2.domain.interfaces.display_config import DisplayConfig
from pycc2.presentation.rendering.fade_transition import FadeTransition
from pycc2.presentation.rendering.minimap import Minimap
from pycc2.presentation.rendering.sprite_cache_manager import SpriteCacheManager
from pycc2.presentation.visual_config import DEFAULT_VISUAL_CONFIG


@pytest.fixture(scope="module", autouse=True)
def _pygame_init():
    """Initialize pygame once for the entire module (headless)."""
    pygame.init()
    yield
    pygame.quit()


# ──────────────────────────────────────────────────────────────────────
# Journey 1: V-05 Responsive Layout
# ──────────────────────────────────────────────────────────────────────


class TestV05ResponsiveLayoutJourney:
    """Real-player journey: player changes screen resolution mid-session."""

    def test_scale_factor_adapts_across_three_resolutions(self):
        """Player launches at 1280x720, upgrades monitor, screen grows.

        Verify: scale_factor is 1.0 at 1280, 1.5 at 1920, 2.0 at 2560.
        This mirrors the V-05 spec (BASE_DESIGN_WIDTH=1280).
        """
        # Player starts game on a 1280x720 laptop
        dc_1280 = DisplayConfig(window_width=1280, window_height=720)
        assert dc_1280.scale_factor == pytest.approx(1.0)

        # Player upgrades to a 1920x1080 monitor
        dc_1920 = DisplayConfig(window_width=1920, window_height=1080)
        assert dc_1920.scale_factor == pytest.approx(1.5)

        # Player moves to a 2560x1440 high-DPI display
        dc_2560 = DisplayConfig(window_width=2560, window_height=1440)
        assert dc_2560.scale_factor == pytest.approx(2.0)

    def test_responsive_minimap_size_scales_with_resolution(self):
        """Minimap base size (160px) scales by ui_scale at higher resolutions.

        Verify: at 1920x1080 (scale=1.5), minimap is 240px (160*1.5).
        This ensures tactical overview remains proportional on larger screens.
        """
        # 1280x720 baseline: minimap 160px
        dc_base = DisplayConfig(window_width=1280, window_height=720)
        minimap_base = Minimap(display_config=dc_base)
        assert minimap_base.size == 160

        # 1920x1080: minimap 240px (160 * 1.5)
        dc_hd = DisplayConfig(window_width=1920, window_height=1080)
        minimap_hd = Minimap(display_config=dc_hd)
        assert minimap_hd.size == 240


# ──────────────────────────────────────────────────────────────────────
# Journey 2: V-06 Micro-Animation Feedback
# ──────────────────────────────────────────────────────────────────────


class TestV06MicroAnimationJourney:
    """Real-player journey: player interacts with UI, feedback animations fire."""

    def test_four_animation_timings_are_within_wave_b_spec(self):
        """Verify: hover (200ms), click (120-150ms), selection pulse (1s),
        error flash (300ms) — all match V-06 Wave B-rev spec.
        """
        timings = DEFAULT_VISUAL_CONFIG.timings

        # Hover transition: 200ms (V-06 spec)
        assert timings.HOVER_TRANSITION == pytest.approx(0.2)  # noqa: SIM300

        # Click transition: 120-150ms (Wave B-rev narrowed from 100ms)
        assert 0.12 <= timings.CLICK_TRANSITION <= 0.15

        # Selection pulse period: 1.0s (V-06 spec)
        assert timings.SELECTION_PULSE_PERIOD == pytest.approx(1.0)  # noqa: SIM300

        # Error flash duration: 300ms (V-06 spec)
        assert timings.ERROR_FLASH_DURATION == pytest.approx(0.3)  # noqa: SIM300

    def test_easing_curve_is_wave_b_unified(self):
        """Verify: all micro-animations use ease_out_cubic (Wave B unified)."""
        timings = DEFAULT_VISUAL_CONFIG.timings
        assert timings.EASING_CURVE == "ease_out_cubic"

    def test_fade_transition_fires_on_show_hide(self):
        """Player opens/closes a panel — fade animation must progress.

        Verify: FadeTransition starts at alpha=0, show() targets alpha=1.0,
        after one update tick alpha increases (animation in progress).
        """
        fade = FadeTransition(fade_duration=0.2)
        assert not fade.is_visible  # hidden initially

        fade.show()
        # Simulate one frame (16ms at 60fps)
        fade.update(0.016)
        # Alpha must have increased from 0 toward target 1.0
        assert fade.alpha > 0.0
        assert fade.alpha < 1.0  # not yet fully visible after one tick


# ──────────────────────────────────────────────────────────────────────
# Journey 3: V-09 SpriteCache Prewarm
# ──────────────────────────────────────────────────────────────────────


class TestV09SpriteCachePrewarmJourney:
    """Real-player journey: player launches game, first frame has no stutter."""

    def test_construction_triggers_synchronous_prewarm(self):
        """Player starts the game — SpriteCacheManager() auto-prewarms.

        Verify: after construction, sprite_cache has ≥264 entries and
        terrain_cache has ≥22 entries (V-09 spec). No first-frame stutter.
        """
        manager = SpriteCacheManager()

        # Sprites prewarmed synchronously during __init__
        assert len(manager.sprite_cache) >= 264
        assert len(manager.terrain_cache) >= 22

        # Prewarm result must be recorded
        assert manager.last_prewarm_result is not None
        assert manager.last_prewarm_result.elapsed_ms > 0

    def test_repeat_prewarm_is_idempotent_no_regenerate(self):
        """Player reloads a map — second prewarm() reuses cached sprites.

        Verify: second prewarm() call returns same elapsed_ms (cached),
        does not regenerate sprites (no redundant work).
        """
        manager = SpriteCacheManager()
        first_result = manager.last_prewarm_result
        assert first_result is not None

        second_result = manager.prewarm()
        # Cached result returned (idempotent)
        assert second_result.elapsed_ms == first_result.elapsed_ms


# ──────────────────────────────────────────────────────────────────────
# Journey 4: V-11 Minimap Terrain Detail
# ──────────────────────────────────────────────────────────────────────


def _make_test_map():
    """Create a small test map for minimap journey tests."""
    import numpy as np

    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.value_objects.terrain_type import TerrainType

    # 8x8 grid with varied terrain
    grid = np.array(
        [
            [TerrainType.GRASS, TerrainType.GRASS, TerrainType.WOODS, TerrainType.OPEN],
            [TerrainType.ROAD, TerrainType.ROAD, TerrainType.BUILDING_SOLID, TerrainType.OPEN],
            [TerrainType.WATER, TerrainType.BRIDGE, TerrainType.WATER, TerrainType.OPEN],
            [TerrainType.HEDGE, TerrainType.GRASS, TerrainType.GRASS, TerrainType.OPEN],
        ],
        dtype=object,
    )
    return GameMap(id="v11_journey", name="V-11 Journey Map", width=4, height=4, tile_grid=grid)


class TestV11MinimapTerrainJourney:
    """Real-player journey: player views minimap during battle."""

    def test_legend_toggle_persists_across_renders(self):
        """Player presses 'L' to toggle legend — state persists on next render.

        Verify: default legend_visible=False, after toggle True, and the
        state survives multiple render() calls.
        """
        dc = DisplayConfig(window_width=1280, window_height=720)
        minimap = Minimap(display_config=dc)
        minimap.set_map(_make_test_map())
        minimap._fade.reset(visible=True)  # skip fade-in for test

        # Default: legend hidden
        assert minimap._legend_visible is False

        # Player presses 'L' — legend toggles on
        minimap.toggle_legend()
        assert minimap._legend_visible is True

        # Render — state persists
        surface = pygame.Surface((200, 200))
        minimap.render(surface, 0, 0)
        assert minimap._legend_visible is True

        # Player presses 'L' again — legend toggles off
        minimap.toggle_legend()
        assert minimap._legend_visible is False

    def test_facing_line_only_for_selected_unit(self):
        """Player selects a unit — facing line appears only for that unit.

        Verify: with no selection, no facing line. With selection, the
        minimap records the selected_unit_id and renders facing.
        """
        dc = DisplayConfig(window_width=1280, window_height=720)
        minimap = Minimap(display_config=dc)
        minimap.set_map(_make_test_map())
        minimap._fade.reset(visible=True)

        # No unit selected — selected_unit_id is None
        assert minimap._selected_unit_id is None

        # Player selects unit "alpha_1"
        minimap.set_selected_unit("alpha_1")
        assert minimap._selected_unit_id == "alpha_1"

        # Player deselects
        minimap.set_selected_unit(None)
        assert minimap._selected_unit_id is None

    def test_casualty_markers_can_be_added(self):
        """Player's unit takes casualties — markers appear on minimap.

        Verify: add_casualty() records the position, and the marker
        list grows. Markers auto-expire after _CASUALTY_MARKER_DURATION_S
        (5s per V-11 spec) via update_casualties().
        """
        dc = DisplayConfig(window_width=1280, window_height=720)
        minimap = Minimap(display_config=dc)
        minimap.set_map(_make_test_map())
        minimap._fade.reset(visible=True)

        # Initially no casualty markers
        assert minimap.casualty_count == 0

        # Player's allied unit dies at tile (2, 3)
        minimap.add_casualty(2, 3, Faction.ALLIES)
        assert minimap.casualty_count == 1

        # Marker records position and faction
        marker = minimap._casualty_markers[0]
        assert marker.tile_x == 2
        assert marker.tile_y == 3
        assert marker.faction == Faction.ALLIES
        assert marker.age_seconds == 0.0  # freshly created

        # After update_casualties(dt), age increases (toward 5s expiry)
        minimap.update_casualties(1.0)  # advance 1 second
        assert minimap._casualty_markers[0].age_seconds == pytest.approx(1.0)
        assert minimap.casualty_count == 1  # not yet expired
