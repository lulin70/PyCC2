"""V-05 Wave D1: Responsive layout scale factor tests.

Covers 6 dimensions per DevSquad Testing Iron Rule 3:
- Happy Path (≥50%): Normal inputs → expected outputs
- Error Case (≥15%): Invalid inputs → ValueError
- Boundary (≥10%): Zero, baseline, 4K screen widths
- Performance (≥5%): <1ms per call
- Configuration (≥5%): Different DisplayConfig presets
- Integration (≥10%): DisplayConfig ↔ Camera ↔ compute_scale_factor

Components under test:
- ``compute_scale_factor()`` module-level helper (display_config.py)
- ``DisplayConfig.scale_factor`` property (alias for ``ui_scale``)
- ``DisplayConfig.ui_scale`` property (existing, now explicitly tested)
- ``Camera.apply_scale_factor()`` method (new, presentation/rendering/camera.py)
- ``BASE_DESIGN_WIDTH`` / ``BASE_DESIGN_HEIGHT`` constants

Reference: docs/VISUAL_POLISH_PLAN.md V-05 章节 (v2.1, Wave D1 修订)
"""

from __future__ import annotations

import time

import pytest

from pycc2.domain.interfaces.display_config import (
    BASE_DESIGN_HEIGHT,
    BASE_DESIGN_WIDTH,
    DisplayConfig,
    QualityPreset,
    compute_scale_factor,
)
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.camera import Camera

# ──────────────────────────────────────────────────────────────────────
# 1. TestConstants — module-level constants (5 tests)
# ──────────────────────────────────────────────────────────────────────


class TestConstants:
    """Verify V-05 design constants are locked to spec values."""

    def test_base_design_width_is_1280(self) -> None:
        """Verify: BASE_DESIGN_WIDTH is 1280 per V-05 spec."""
        assert BASE_DESIGN_WIDTH == 1280

    def test_base_design_height_is_720(self) -> None:
        """Verify: BASE_DESIGN_HEIGHT is 720 per V-05 spec."""
        assert BASE_DESIGN_HEIGHT == 720

    def test_base_aspect_ratio_is_16_9(self) -> None:
        """Verify: Base design is 16:9 aspect ratio."""
        assert pytest.approx(16.0 / 9.0) == BASE_DESIGN_WIDTH / BASE_DESIGN_HEIGHT

    def test_constants_are_int(self) -> None:
        """Verify: Constants are int (not float) for pixel precision."""
        assert isinstance(BASE_DESIGN_WIDTH, int)
        assert isinstance(BASE_DESIGN_HEIGHT, int)

    def test_constants_are_positive(self) -> None:
        """Verify: Constants are positive values."""
        assert BASE_DESIGN_WIDTH > 0
        assert BASE_DESIGN_HEIGHT > 0


# ──────────────────────────────────────────────────────────────────────
# 2. TestComputeScaleFactor — module-level helper (16 tests)
#   Happy Path: 6, Error: 3, Boundary: 5, Performance: 2
# ──────────────────────────────────────────────────────────────────────


class TestComputeScaleFactor:
    """Test compute_scale_factor() standalone helper."""

    # --- Happy Path (6 tests) ---

    def test_baseline_1280_returns_1_0(self) -> None:
        """Verify: 1280px screen → scale_factor 1.0 (baseline)."""
        assert compute_scale_factor(1280) == 1.0

    def test_1920_returns_1_5(self) -> None:
        """Verify: 1920px screen → scale_factor 1.5 (50% wider than baseline)."""
        assert compute_scale_factor(1920) == pytest.approx(1.5)

    def test_2560_returns_2_0(self) -> None:
        """Verify: 2560px screen → scale_factor 2.0 (double baseline)."""
        assert compute_scale_factor(2560) == pytest.approx(2.0)

    def test_retina_dpi_scale_2_0_at_baseline_width(self) -> None:
        """Verify: dpi_scale=2.0 dominates at 1280px width."""
        assert compute_scale_factor(1280, dpi_scale=2.0) == 2.0

    def test_dpi_scale_dominates_when_higher_than_width_scale(self) -> None:
        """Verify: dpi_scale wins when > width_scale.

        Scenario: 1280px width (scale 1.0) + dpi_scale 1.5 → 1.5
        """
        assert compute_scale_factor(1280, dpi_scale=1.5) == 1.5

    def test_width_scale_dominates_when_higher_than_dpi_scale(self) -> None:
        """Verify: width_scale wins when > dpi_scale.

        Scenario: 2560px width (scale 2.0) + dpi_scale 1.0 → 2.0
        """
        assert compute_scale_factor(2560, dpi_scale=1.0) == 2.0

    # --- Error Case (3 tests) ---

    def test_negative_screen_width_raises_value_error(self) -> None:
        """Verify: negative screen_width raises ValueError."""
        with pytest.raises(ValueError, match="screen_width must be >= 0"):
            compute_scale_factor(-1)

    def test_negative_dpi_scale_raises_value_error(self) -> None:
        """Verify: negative dpi_scale raises ValueError."""
        with pytest.raises(ValueError, match="dpi_scale must be >= 0"):
            compute_scale_factor(1280, dpi_scale=-0.5)

    def test_zero_base_width_raises_value_error(self) -> None:
        """Verify: base_width=0 raises ValueError (division by zero guard)."""
        with pytest.raises(ValueError, match="base_width must be > 0"):
            compute_scale_factor(1280, base_width=0)

    # --- Boundary (5 tests) ---

    def test_zero_screen_width_returns_1_0(self) -> None:
        """Verify: screen_width=0 returns 1.0 (headless/CI safe fallback)."""
        assert compute_scale_factor(0) == 1.0

    def test_exact_base_width_returns_1_0(self) -> None:
        """Verify: exact base_width returns 1.0 (no scaling)."""
        assert compute_scale_factor(BASE_DESIGN_WIDTH) == 1.0

    def test_custom_base_width_800(self) -> None:
        """Verify: custom base_width=800 + screen 1600 → 2.0."""
        assert compute_scale_factor(1600, base_width=800) == 2.0

    def test_4k_screen_3840_returns_3_0(self) -> None:
        """Verify: 4K screen 3840px → scale_factor 3.0."""
        assert compute_scale_factor(3840) == 3.0

    def test_dpi_scale_zero_with_baseline_width(self) -> None:
        """Verify: dpi_scale=0 is allowed (degenerate but not invalid).

        Scenario: 1280px width + dpi_scale 0.0 → width_scale 1.0 wins.
        """
        assert compute_scale_factor(1280, dpi_scale=0.0) == 1.0

    # --- Performance (2 tests) ---

    def test_compute_scale_factor_under_1ms(self) -> None:
        """Verify: compute_scale_factor() completes in <1ms."""
        start = time.perf_counter()
        for _ in range(1000):
            compute_scale_factor(1920, dpi_scale=1.5)
        elapsed_ms = (time.perf_counter() - start) * 1000
        per_call_ms = elapsed_ms / 1000
        assert per_call_ms < 1.0, f"Per-call {per_call_ms:.3f}ms exceeds 1ms budget"

    def test_compute_scale_factor_scales_linearly(self) -> None:
        """Verify: 10000 calls complete in <50ms (linear scaling).

        Threshold is 50ms (not 10ms) to accommodate CI runners which are
        typically slower than local dev machines. 10000 calls at ~1.6μs/call
        on a slow runner is still well under 50ms, confirming O(1) behavior.
        """
        start = time.perf_counter()
        for _ in range(10000):
            compute_scale_factor(2560, dpi_scale=2.0)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50.0, f"10000 calls took {elapsed_ms:.2f}ms (>50ms)"


# ──────────────────────────────────────────────────────────────────────
# 3. TestDisplayConfigScaleFactor — property alias (12 tests)
#   Happy Path: 5, Configuration: 5, Integration: 2
# ──────────────────────────────────────────────────────────────────────


class TestDisplayConfigScaleFactor:
    """Test DisplayConfig.scale_factor property (alias for ui_scale)."""

    # --- Happy Path (5 tests) ---

    def test_scale_factor_equals_ui_scale(self) -> None:
        """Verify: scale_factor property returns same value as ui_scale."""
        dc = DisplayConfig(window_width=1920, window_height=1080)
        assert dc.scale_factor == dc.ui_scale

    def test_default_config_scale_factor(self) -> None:
        """Verify: default DisplayConfig (1440×900) → scale 1.125.

        Scenario: 1440 / 1280 = 1.125, dpi_scale default 1.0 → max(1.0, 1.125) = 1.125
        """
        dc = DisplayConfig()  # defaults: 1440×900, dpi_scale=1.0
        assert dc.scale_factor == pytest.approx(1.125)

    def test_1920_width_scale_factor_1_5(self) -> None:
        """Verify: 1920px width → scale_factor 1.5."""
        dc = DisplayConfig(window_width=1920, window_height=1080)
        assert dc.scale_factor == pytest.approx(1.5)

    def test_retina_config_scale_factor_2_0(self) -> None:
        """Verify: Retina (dpi_scale=2.0) at 1280px → scale_factor 2.0."""
        dc = DisplayConfig(window_width=1280, window_height=720, dpi_scale=2.0)
        assert dc.scale_factor == 2.0

    def test_scale_factor_property_is_read_only(self) -> None:
        """Verify: scale_factor is a property (no setter)."""
        dc = DisplayConfig()
        with pytest.raises(AttributeError):
            dc.scale_factor = 2.0  # type: ignore[misc]

    # --- Configuration (5 tests) ---

    def test_from_screen_1280(self) -> None:
        """Verify: from_screen(1280, 720) → scale_factor ~1.0.

        Note: from_screen caps window_width at int(screen_width * 0.9) = 1152.
        So scale_factor = max(1.0, 1152/1280) = 1.0 (dpi_scale dominates).
        """
        dc = DisplayConfig.from_screen(1280, 720)
        assert dc.scale_factor == 1.0

    def test_from_screen_1920(self) -> None:
        """Verify: from_screen(1920, 1080) → scale_factor ~1.35.

        window_width = min(int(1920*0.9), 1920) = 1728.
        scale_factor = max(1.0, 1728/1280) = 1.35.
        """
        dc = DisplayConfig.from_screen(1920, 1080)
        assert dc.scale_factor == pytest.approx(1.35)

    def test_from_preset_low(self) -> None:
        """Verify: LOW preset (800×600) → scale_factor 1.0.

        800/1280 = 0.625, but max(1.0, 0.625) = 1.0 (dpi_scale default).
        """
        dc = DisplayConfig.from_preset(QualityPreset.LOW)
        assert dc.scale_factor == 1.0

    def test_from_preset_ultra(self) -> None:
        """Verify: ULTRA preset (1920×1080) → scale_factor 1.5."""
        dc = DisplayConfig.from_preset(QualityPreset.ULTRA)
        assert dc.scale_factor == pytest.approx(1.5)

    def test_from_preset_ultra_retina(self) -> None:
        """Verify: ULTRA + Retina (dpi_scale=2.0) → scale_factor 2.0."""
        dc = DisplayConfig.from_preset(QualityPreset.ULTRA, dpi_scale=2.0)
        assert dc.scale_factor == 2.0

    # --- Integration (2 tests) ---

    def test_font_sizes_scale_with_scale_factor(self) -> None:
        """Verify: font_size_* properties scale proportionally with scale_factor."""
        dc_baseline = DisplayConfig(window_width=1280, window_height=720)
        dc_2x = DisplayConfig(window_width=2560, window_height=1440)

        # scale_factor doubles (1.0 → 2.0)
        assert dc_2x.scale_factor == pytest.approx(2.0 * dc_baseline.scale_factor)

        # font_size_normal: max(14, int(18 * scale_factor))
        # baseline: max(14, 18*1.0) = 18; 2x: max(14, 18*2.0) = 36
        assert dc_baseline.font_size_normal == 18
        assert dc_2x.font_size_normal == 36

    def test_scale_factor_consistent_across_multiple_reads(self) -> None:
        """Verify: repeated property reads return identical values (no side effects)."""
        dc = DisplayConfig(window_width=1920, window_height=1080, dpi_scale=1.5)
        values = [dc.scale_factor for _ in range(10)]
        assert all(v == values[0] for v in values), "scale_factor inconsistent across reads"


# ──────────────────────────────────────────────────────────────────────
# 4. TestCameraApplyScaleFactor — Camera method (14 tests)
#   Happy Path: 4, Error: 2, Boundary: 3, Integration: 4, Performance: 1
# ──────────────────────────────────────────────────────────────────────


class TestCameraApplyScaleFactor:
    """Test Camera.apply_scale_factor() method."""

    def _make_camera(self) -> Camera:
        """Create a Camera at origin with default zoom for testing."""
        return Camera(position=Vec2(0.0, 0.0))

    # --- Happy Path (4 tests) ---

    def test_default_viewport_is_1280x720(self) -> None:
        """Verify: fresh Camera has 1280×720 viewport (baseline)."""
        cam = self._make_camera()
        assert cam.viewport_width == 1280
        assert cam.viewport_height == 720

    def test_apply_1_0_keeps_viewport_at_baseline(self) -> None:
        """Verify: scale_factor=1.0 leaves viewport at 1280×720."""
        cam = self._make_camera()
        cam.apply_scale_factor(1.0)
        assert cam.viewport_width == 1280
        assert cam.viewport_height == 720

    def test_apply_1_5_scales_viewport_to_1920x1080(self) -> None:
        """Verify: scale_factor=1.5 → 1920×1080 viewport."""
        cam = self._make_camera()
        cam.apply_scale_factor(1.5)
        assert cam.viewport_width == 1920
        assert cam.viewport_height == 1080

    def test_apply_2_0_doubles_viewport_to_2560x1440(self) -> None:
        """Verify: scale_factor=2.0 → 2560×1440 viewport."""
        cam = self._make_camera()
        cam.apply_scale_factor(2.0)
        assert cam.viewport_width == 2560
        assert cam.viewport_height == 1440

    # --- Error Case (2 tests) ---

    def test_zero_scale_factor_raises_value_error(self) -> None:
        """Verify: scale_factor=0 raises ValueError."""
        cam = self._make_camera()
        with pytest.raises(ValueError, match="scale_factor must be > 0"):
            cam.apply_scale_factor(0.0)

    def test_negative_scale_factor_raises_value_error(self) -> None:
        """Verify: negative scale_factor raises ValueError."""
        cam = self._make_camera()
        with pytest.raises(ValueError, match="scale_factor must be > 0"):
            cam.apply_scale_factor(-1.5)

    # --- Boundary (3 tests) ---

    def test_small_scale_factor_0_5_halves_viewport(self) -> None:
        """Verify: scale_factor=0.5 → 640×360 viewport (below baseline).

        Allowed by the API (only >0 required). Useful for testing
        sub-baseline rendering or small windows.
        """
        cam = self._make_camera()
        cam.apply_scale_factor(0.5)
        assert cam.viewport_width == 640
        assert cam.viewport_height == 360

    def test_large_scale_factor_4_0_quadruples_viewport(self) -> None:
        """Verify: scale_factor=4.0 → 5120×2880 viewport (8K)."""
        cam = self._make_camera()
        cam.apply_scale_factor(4.0)
        assert cam.viewport_width == 5120
        assert cam.viewport_height == 2880

    def test_very_small_scale_factor_0_01(self) -> None:
        """Verify: scale_factor=0.01 → 12×7 viewport (minimal)."""
        cam = self._make_camera()
        cam.apply_scale_factor(0.01)
        assert cam.viewport_width == 12  # int(1280 * 0.01) = 12
        assert cam.viewport_height == 7  # int(720 * 0.01) = 7

    # --- Integration (4 tests) ---

    def test_world_to_screen_uses_scaled_viewport(self) -> None:
        """Verify: world_to_screen centers on scaled viewport dimensions.

        After apply_scale_factor(2.0), viewport is 2560×1440.
        world_to_screen(origin) should return (1280, 720) — the new center.
        """
        cam = self._make_camera()
        cam.apply_scale_factor(2.0)
        screen_x, screen_y = cam.world_to_screen(Vec2(0.0, 0.0))
        assert screen_x == pytest.approx(1280.0)  # 2560 / 2
        assert screen_y == pytest.approx(720.0)  # 1440 / 2

    def test_view_bounds_reflect_scaled_viewport(self) -> None:
        """Verify: view_bounds uses scaled viewport dimensions.

        After apply_scale_factor(2.0) with zoom=1.0, view_bounds span
        2560×1440 world units centered on camera position.
        """
        cam = self._make_camera()
        cam.apply_scale_factor(2.0)
        top_left, bottom_right = cam.view_bounds
        # zoom=1.0, so view_w = viewport_width / zoom = 2560
        assert (bottom_right.x - top_left.x) == pytest.approx(2560.0)
        assert (bottom_right.y - top_left.y) == pytest.approx(1440.0)

    def test_zoom_unaffected_by_apply_scale_factor(self) -> None:
        """Verify: apply_scale_factor does NOT modify zoom field.

        zoom controls world-to-screen coordinate scaling and is
        orthogonal to viewport size.
        """
        cam = self._make_camera()
        original_zoom = cam.zoom
        cam.apply_scale_factor(2.0)
        assert cam.zoom == original_zoom

    def test_apply_scale_factor_multiple_calls_overwrite(self) -> None:
        """Verify: calling apply_scale_factor twice uses the latest value."""
        cam = self._make_camera()
        cam.apply_scale_factor(2.0)
        cam.apply_scale_factor(1.0)
        assert cam.viewport_width == 1280
        assert cam.viewport_height == 720

    # --- Performance (1 test) ---

    def test_apply_scale_factor_under_1ms(self) -> None:
        """Verify: apply_scale_factor() completes in <1ms."""
        cam = self._make_camera()
        start = time.perf_counter()
        for _ in range(1000):
            cam.apply_scale_factor(1.5)
        elapsed_ms = (time.perf_counter() - start) * 1000
        per_call_ms = elapsed_ms / 1000
        assert per_call_ms < 1.0, f"Per-call {per_call_ms:.3f}ms exceeds 1ms budget"


# ──────────────────────────────────────────────────────────────────────
# 5. TestIntegration — cross-component (6 tests)
#   Integration: DisplayConfig ↔ Camera ↔ compute_scale_factor
# ──────────────────────────────────────────────────────────────────────


class TestIntegration:
    """Integration tests across DisplayConfig + Camera + compute_scale_factor."""

    def test_display_config_scale_factor_matches_compute_helper(self) -> None:
        """Verify: DisplayConfig.scale_factor == compute_scale_factor(window_width).

        Both should return identical values for the same inputs.
        """
        dc = DisplayConfig(window_width=1920, window_height=1080, dpi_scale=1.0)
        helper_value = compute_scale_factor(1920, dpi_scale=1.0)
        assert dc.scale_factor == pytest.approx(helper_value)

    def test_camera_viewport_matches_display_config_window(self) -> None:
        """Verify: Camera viewport matches DisplayConfig window after apply.

        Scenario: DisplayConfig 1920×1080 → Camera viewport 1920×1080.
        """
        dc = DisplayConfig(window_width=1920, window_height=1080)
        cam = Camera(position=Vec2(0.0, 0.0))
        cam.apply_scale_factor(dc.scale_factor)
        assert cam.viewport_width == 1920
        assert cam.viewport_height == 1080

    def test_full_pipeline_display_config_to_camera(self) -> None:
        """Verify: Full pipeline DisplayConfig → Camera → world_to_screen.

        Scenario:
        1. Create DisplayConfig for 1920×1080 screen
        2. scale_factor = 1.5
        3. Camera.apply_scale_factor(1.5) → viewport 1920×1080
        4. world_to_screen(origin) → (960, 540) — center of 1920×1080
        """
        dc = DisplayConfig(window_width=1920, window_height=1080, dpi_scale=1.0)
        cam = Camera(position=Vec2(0.0, 0.0))
        cam.apply_scale_factor(dc.scale_factor)

        # Camera viewport should match DisplayConfig window
        assert cam.viewport_width == dc.window_width
        assert cam.viewport_height == dc.window_height

        # World origin should map to screen center
        screen_x, screen_y = cam.world_to_screen(Vec2(0.0, 0.0))
        assert screen_x == pytest.approx(dc.window_width / 2)
        assert screen_y == pytest.approx(dc.window_height / 2)

    def test_retina_pipeline_dpi_scale_2_0(self) -> None:
        """Verify: Retina pipeline (dpi_scale=2.0) doubles viewport.

        Scenario: DisplayConfig 1280×720 + dpi_scale=2.0
        → scale_factor=2.0 → Camera viewport 2560×1440
        """
        dc = DisplayConfig(
            window_width=1280,
            window_height=720,
            dpi_scale=2.0,
            is_retina=True,
        )
        assert dc.scale_factor == 2.0

        cam = Camera(position=Vec2(0.0, 0.0))
        cam.apply_scale_factor(dc.scale_factor)
        assert cam.viewport_width == 2560
        assert cam.viewport_height == 1440

    def test_4k_pipeline_3840_width(self) -> None:
        """Verify: 4K pipeline (3840px width) → scale_factor 3.0.

        Scenario: DisplayConfig 3840×2160 + dpi_scale=1.0
        → scale_factor=3.0 → Camera viewport 3840×2160
        """
        dc = DisplayConfig(window_width=3840, window_height=2160)
        assert dc.scale_factor == 3.0

        cam = Camera(position=Vec2(0.0, 0.0))
        cam.apply_scale_factor(dc.scale_factor)
        assert cam.viewport_width == 3840
        assert cam.viewport_height == 2160

    def test_from_screen_pipeline_to_camera(self) -> None:
        """Verify: from_screen() → Camera pipeline end-to-end.

        Scenario: User has 1920×1080 monitor.
        1. dc = DisplayConfig.from_screen(1920, 1080)
        2. window_width = min(int(1920*0.9), 1920) = 1728
        3. scale_factor = max(1.0, 1728/1280) = 1.35
        4. Camera viewport = int(1280*1.35) × int(720*1.35) = 1728 × 972
        """
        dc = DisplayConfig.from_screen(1920, 1080)
        cam = Camera(position=Vec2(0.0, 0.0))
        cam.apply_scale_factor(dc.scale_factor)

        # Camera viewport should match DisplayConfig window_width
        assert cam.viewport_width == dc.window_width
        # Height: int(720 * 1.35) = 972, dc.window_height = min(int(1080*0.9), 1080) = 972
        assert cam.viewport_height == dc.window_height
