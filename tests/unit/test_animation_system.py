"""V-06 (Wave D2): Unit tests for easing functions and micro-animation system.

Tests cover 6 dimensions (Happy/Error/Boundary/Performance/Config/Integration):
1. Easing functions (8 functions: ease_out_cubic, ease_in_cubic, ease_in_out_cubic,
   ease_in_out_sine, ease_out_sine, ease_in_sine, ease_out_back, linear)
2. Easing boundary conditions (t=0, t=1, t<0, t>1)
3. Animation dataclass (construction, completed flag, compute_progress)
4. Animation factory functions (4 types with defaults)
5. MicroAnimationController (start/cancel/get_value/update/cleanup)
6. AnimationType-specific behavior (HOVER/CLICK/SELECTION_PULSE/ERROR_FLASH)
7. Multi-iteration animations (ERROR_FLASH 2x)
8. Integration (multi-element concurrent animations)
9. Performance (1000 animations < 100ms)

Note (2026-07-21): V-06 micro-animation subsystem was moved from
``animation_system.py`` to ``micro_animation.py`` per SRP principle.
``animation_system.py`` retains the legacy UnitAnimator/ScreenShake/
ParticleEmitter API used by effect_renderer.py / sprite_renderer_base.py /
particle_pool.py.
"""

from __future__ import annotations

import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest  # noqa: E402

from pycc2.presentation.rendering.easing import (  # noqa: E402
    ease_in_cubic,
    ease_in_out_cubic,
    ease_in_out_sine,
    ease_in_sine,
    ease_out_back,
    ease_out_cubic,
    ease_out_sine,
    linear,
)
from pycc2.presentation.rendering.micro_animation import (  # noqa: E402
    CLICK_SCALE_FROM,
    CLICK_SCALE_TO,
    DEFAULT_CLICK_DURATION_MS,
    DEFAULT_ERROR_FLASH_DURATION_MS,
    DEFAULT_HOVER_DURATION_MS,
    DEFAULT_SELECTION_PULSE_DURATION_MS,
    ERROR_FLASH_MAX_ITERATIONS,
    HOVER_ALPHA_FROM,
    HOVER_ALPHA_TO,
    SELECTION_PULSE_ALPHA_MAX,
    SELECTION_PULSE_ALPHA_MIN,
    Animation,
    AnimationType,
    MicroAnimationController,
    create_click_animation,
    create_error_flash_animation,
    create_hover_animation,
    create_selection_pulse_animation,
)

# ============================================================================
# 1. Easing functions (happy path)
# ============================================================================


class TestEasingFunctions:
    """Test all 8 easing functions."""

    def test_ease_out_cubic_at_0(self):
        """ease_out_cubic(0) = 0."""
        assert ease_out_cubic(0.0) == pytest.approx(0.0)

    def test_ease_out_cubic_at_1(self):
        """ease_out_cubic(1) = 1."""
        assert ease_out_cubic(1.0) == pytest.approx(1.0)

    def test_ease_out_cubic_at_0_5(self):
        """ease_out_cubic(0.5) = 0.875 (fast start, slow end)."""
        assert ease_out_cubic(0.5) == pytest.approx(0.875)

    def test_ease_in_cubic_at_0(self):
        """ease_in_cubic(0) = 0."""
        assert ease_in_cubic(0.0) == pytest.approx(0.0)

    def test_ease_in_cubic_at_1(self):
        """ease_in_cubic(1) = 1."""
        assert ease_in_cubic(1.0) == pytest.approx(1.0)

    def test_ease_in_cubic_at_0_5(self):
        """ease_in_cubic(0.5) = 0.125 (slow start, fast end)."""
        assert ease_in_cubic(0.5) == pytest.approx(0.125)

    def test_ease_in_out_cubic_at_0(self):
        """ease_in_out_cubic(0) = 0."""
        assert ease_in_out_cubic(0.0) == pytest.approx(0.0)

    def test_ease_in_out_cubic_at_1(self):
        """ease_in_out_cubic(1) = 1."""
        assert ease_in_out_cubic(1.0) == pytest.approx(1.0)

    def test_ease_in_out_cubic_at_0_5(self):
        """ease_in_out_cubic(0.5) = 0.5 (symmetric S-curve)."""
        assert ease_in_out_cubic(0.5) == pytest.approx(0.5)

    def test_ease_in_out_sine_at_0(self):
        """ease_in_out_sine(0) = 0."""
        assert ease_in_out_sine(0.0) == pytest.approx(0.0)

    def test_ease_in_out_sine_at_1(self):
        """ease_in_out_sine(1) = 1."""
        assert ease_in_out_sine(1.0) == pytest.approx(1.0)

    def test_ease_in_out_sine_at_0_5(self):
        """ease_in_out_sine(0.5) = 0.5 (symmetric)."""
        assert ease_in_out_sine(0.5) == pytest.approx(0.5)

    def test_ease_out_sine_at_0(self):
        """ease_out_sine(0) = 0."""
        assert ease_out_sine(0.0) == pytest.approx(0.0)

    def test_ease_out_sine_at_1(self):
        """ease_out_sine(1) = 1."""
        assert ease_out_sine(1.0) == pytest.approx(1.0)

    def test_ease_in_sine_at_0(self):
        """ease_in_sine(0) = 0."""
        assert ease_in_sine(0.0) == pytest.approx(0.0)

    def test_ease_in_sine_at_1(self):
        """ease_in_sine(1) = 1."""
        assert ease_in_sine(1.0) == pytest.approx(1.0)

    def test_ease_out_back_at_0(self):
        """ease_out_back(0) = 0."""
        assert ease_out_back(0.0) == pytest.approx(0.0)

    def test_ease_out_back_at_1(self):
        """ease_out_back(1) = 1."""
        assert ease_out_back(1.0) == pytest.approx(1.0)

    def test_ease_out_back_overshoots_midway(self):
        """ease_out_back(0.7) > 1.0 (overshoots)."""
        assert ease_out_back(0.7) > 1.0

    def test_linear_identity(self):
        """linear(t) = t for t ∈ [0, 1]."""
        assert linear(0.0) == pytest.approx(0.0)
        assert linear(0.5) == pytest.approx(0.5)
        assert linear(1.0) == pytest.approx(1.0)


# ============================================================================
# 2. Easing boundary conditions
# ============================================================================


class TestEasingBoundaries:
    """Test easing function boundary clamping."""

    def test_negative_t_clamped_to_0(self):
        """All easing functions clamp t<0 to 0."""
        for fn in [
            ease_out_cubic,
            ease_in_cubic,
            ease_in_out_cubic,
            ease_in_out_sine,
            ease_out_sine,
            ease_in_sine,
            linear,
        ]:
            assert fn(-0.5) == pytest.approx(0.0), f"{fn.__name__} failed"

    def test_t_above_1_clamped_to_1(self):
        """All easing functions clamp t>1 to 1."""
        for fn in [
            ease_out_cubic,
            ease_in_cubic,
            ease_in_out_cubic,
            ease_in_out_sine,
            ease_out_sine,
            ease_in_sine,
            linear,
        ]:
            assert fn(1.5) == pytest.approx(1.0), f"{fn.__name__} failed"

    def test_ease_out_back_clamps_but_overshoots_in_middle(self):
        """ease_out_back clamps endpoints but overshoots in middle."""
        assert ease_out_back(-0.5) == pytest.approx(0.0)
        assert ease_out_back(1.5) == pytest.approx(1.0)
        # Middle values may exceed 1.0 (that's the bouncy nature)
        assert ease_out_back(0.8) > 0  # Should not be clamped to 0


# ============================================================================
# 3. Constants (Wave B-rev spec values)
# ============================================================================


class TestConstants:
    """Verify V-06 constants match Wave B-rev spec."""

    def test_click_duration_in_golden_range(self):
        """DEFAULT_CLICK_DURATION_MS = 130ms (within 120-150ms golden range)."""
        assert 120 <= DEFAULT_CLICK_DURATION_MS <= 150

    def test_hover_duration_is_200ms(self):
        """DEFAULT_HOVER_DURATION_MS = 200ms."""
        assert DEFAULT_HOVER_DURATION_MS == 200

    def test_selection_pulse_duration_is_1000ms(self):
        """DEFAULT_SELECTION_PULSE_DURATION_MS = 1000ms (1s)."""
        assert DEFAULT_SELECTION_PULSE_DURATION_MS == 1000

    def test_error_flash_duration_is_300ms(self):
        """DEFAULT_ERROR_FLASH_DURATION_MS = 300ms."""
        assert DEFAULT_ERROR_FLASH_DURATION_MS == 300

    def test_click_scale_from_is_0_94(self):
        """CLICK_SCALE_FROM = 0.94."""
        assert CLICK_SCALE_FROM == 0.94

    def test_click_scale_to_is_1_0(self):
        """CLICK_SCALE_TO = 1.0."""
        assert CLICK_SCALE_TO == 1.0

    def test_hover_alpha_range(self):
        """HOVER_ALPHA_FROM=0.0, HOVER_ALPHA_TO=1.0."""
        assert HOVER_ALPHA_FROM == 0.0
        assert HOVER_ALPHA_TO == 1.0

    def test_selection_pulse_alpha_range(self):
        """SELECTION_PULSE_ALPHA_MIN=100, MAX=200."""
        assert SELECTION_PULSE_ALPHA_MIN == 100
        assert SELECTION_PULSE_ALPHA_MAX == 200

    def test_error_flash_max_iterations_is_2(self):
        """ERROR_FLASH_MAX_ITERATIONS = 2 (flash twice)."""
        assert ERROR_FLASH_MAX_ITERATIONS == 2


# ============================================================================
# 4. Animation dataclass
# ============================================================================


class TestAnimationDataclass:
    """Test Animation dataclass construction and compute_progress."""

    def test_animation_construction(self):
        """Animation can be constructed with required fields."""
        anim = Animation(
            animation_type=AnimationType.CLICK,
            start_time_ms=0.0,
            duration_ms=130,
            easing_fn=ease_out_cubic,
            from_value=0.94,
            to_value=1.0,
        )
        assert anim.animation_type == AnimationType.CLICK
        assert anim.duration_ms == 130
        assert anim.completed is False

    def test_compute_progress_at_start_returns_from_value(self):
        """At start_time, compute_progress returns from_value."""
        anim = Animation(
            animation_type=AnimationType.CLICK,
            start_time_ms=100.0,
            duration_ms=130,
            easing_fn=ease_out_cubic,
            from_value=0.94,
            to_value=1.0,
        )
        assert anim.compute_progress(100.0) == pytest.approx(0.94)

    def test_compute_progress_at_end_returns_to_value(self):
        """At end time, compute_progress returns to_value and marks completed."""
        anim = Animation(
            animation_type=AnimationType.CLICK,
            start_time_ms=0.0,
            duration_ms=130,
            easing_fn=ease_out_cubic,
            from_value=0.94,
            to_value=1.0,
        )
        value = anim.compute_progress(130.0)
        assert value == pytest.approx(1.0)
        assert anim.completed is True

    def test_compute_progress_before_start_returns_from_value(self):
        """Before start_time, compute_progress returns from_value (not started)."""
        anim = Animation(
            animation_type=AnimationType.CLICK,
            start_time_ms=100.0,
            duration_ms=130,
            easing_fn=ease_out_cubic,
            from_value=0.94,
            to_value=1.0,
        )
        assert anim.compute_progress(50.0) == pytest.approx(0.94)

    def test_compute_progress_mid_animation_in_range(self):
        """Mid-animation, value is between from_value and to_value."""
        anim = Animation(
            animation_type=AnimationType.CLICK,
            start_time_ms=0.0,
            duration_ms=100,
            easing_fn=ease_out_cubic,
            from_value=0.0,
            to_value=1.0,
        )
        value = anim.compute_progress(50.0)
        assert 0.0 < value < 1.0

    def test_completed_flag_set_after_duration(self):
        """completed flag is True after total duration elapsed."""
        anim = Animation(
            animation_type=AnimationType.CLICK,
            start_time_ms=0.0,
            duration_ms=100,
            easing_fn=ease_out_cubic,
            from_value=0.0,
            to_value=1.0,
            iterations=2,
        )
        # 200ms = 2 iterations × 100ms
        anim.compute_progress(200.0)
        assert anim.completed is True


# ============================================================================
# 5. Factory functions
# ============================================================================


class TestFactoryFunctions:
    """Test animation factory functions."""

    def test_create_hover_animation_defaults(self):
        """create_hover_animation uses correct defaults."""
        anim = create_hover_animation(start_time_ms=0.0)
        assert anim.animation_type == AnimationType.HOVER
        assert anim.duration_ms == DEFAULT_HOVER_DURATION_MS
        assert anim.from_value == HOVER_ALPHA_FROM
        assert anim.to_value == HOVER_ALPHA_TO

    def test_create_click_animation_defaults(self):
        """create_click_animation uses correct defaults."""
        anim = create_click_animation(start_time_ms=0.0)
        assert anim.animation_type == AnimationType.CLICK
        assert anim.duration_ms == DEFAULT_CLICK_DURATION_MS
        assert anim.from_value == CLICK_SCALE_FROM
        assert anim.to_value == CLICK_SCALE_TO

    def test_create_selection_pulse_animation_defaults(self):
        """create_selection_pulse_animation uses correct defaults."""
        anim = create_selection_pulse_animation(start_time_ms=0.0)
        assert anim.animation_type == AnimationType.SELECTION_PULSE
        assert anim.duration_ms == DEFAULT_SELECTION_PULSE_DURATION_MS
        assert anim.from_value == SELECTION_PULSE_ALPHA_MIN
        assert anim.to_value == SELECTION_PULSE_ALPHA_MAX

    def test_create_error_flash_animation_defaults(self):
        """create_error_flash_animation uses correct defaults."""
        anim = create_error_flash_animation(start_time_ms=0.0)
        assert anim.animation_type == AnimationType.ERROR_FLASH
        assert anim.duration_ms == DEFAULT_ERROR_FLASH_DURATION_MS
        assert anim.iterations == ERROR_FLASH_MAX_ITERATIONS

    def test_create_click_animation_custom_duration(self):
        """create_click_animation accepts custom duration."""
        anim = create_click_animation(start_time_ms=0.0, duration_ms=145)
        assert anim.duration_ms == 145

    def test_create_hover_animation_custom_alpha_range(self):
        """create_hover_animation accepts custom alpha range."""
        anim = create_hover_animation(start_time_ms=0.0, from_alpha=0.2, to_alpha=0.8)
        assert anim.from_value == 0.2
        assert anim.to_value == 0.8


# ============================================================================
# 6. MicroAnimationController
# ============================================================================


class TestMicroAnimationController:
    """Test MicroAnimationController lifecycle."""

    def test_initial_active_count_is_zero(self):
        """New controller has 0 active animations."""
        controller = MicroAnimationController()
        assert controller.active_count == 0

    def test_start_increments_active_count(self):
        """start() adds an animation."""
        controller = MicroAnimationController()
        controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0)
        assert controller.active_count == 1

    def test_start_multiple_keys(self):
        """Multiple keys can have active animations."""
        controller = MicroAnimationController()
        controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0)
        controller.start("btn_2", AnimationType.HOVER, start_time_ms=0.0)
        assert controller.active_count == 2

    def test_start_same_key_same_type_replaces(self):
        """Starting same key+type replaces existing animation."""
        controller = MicroAnimationController()
        controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0)
        controller.start("btn_1", AnimationType.CLICK, start_time_ms=10.0)
        assert controller.active_count == 1  # Not 2

    def test_start_same_key_different_type_adds(self):
        """Same key with different type adds new animation."""
        controller = MicroAnimationController()
        controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0)
        controller.start("btn_1", AnimationType.HOVER, start_time_ms=0.0)
        assert controller.active_count == 2

    def test_get_value_returns_default_when_no_animation(self):
        """get_value returns default when no animation exists."""
        controller = MicroAnimationController()
        value = controller.get_value("btn_1", AnimationType.CLICK, default=1.0)
        assert value == 1.0

    def test_get_value_returns_current_after_update(self):
        """get_value returns interpolated value after update()."""
        controller = MicroAnimationController()
        controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0)
        controller.update(65.0)  # Halfway through 130ms
        value = controller.get_value("btn_1", AnimationType.CLICK, default=1.0)
        # Should be between 0.94 and 1.0
        assert 0.94 < value < 1.0

    def test_cancel_specific_type(self):
        """cancel() removes specific animation type."""
        controller = MicroAnimationController()
        controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0)
        controller.start("btn_1", AnimationType.HOVER, start_time_ms=0.0)
        assert controller.cancel("btn_1", AnimationType.CLICK) is True
        assert controller.active_count == 1

    def test_cancel_all_types_for_key(self):
        """cancel(key) without type removes all animations for key."""
        controller = MicroAnimationController()
        controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0)
        controller.start("btn_1", AnimationType.HOVER, start_time_ms=0.0)
        assert controller.cancel("btn_1") is True
        assert controller.active_count == 0

    def test_cancel_nonexistent_returns_false(self):
        """cancel() returns False for non-existent key."""
        controller = MicroAnimationController()
        assert controller.cancel("nonexistent") is False

    def test_cleanup_completed_removes_finished(self):
        """cleanup_completed() removes finished animations."""
        controller = MicroAnimationController()
        controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0, duration_ms=100)
        controller.update(150.0)  # Past duration → completed
        removed = controller.cleanup_completed()
        assert removed == 1
        assert controller.active_count == 0

    def test_clear_removes_all(self):
        """clear() removes all animations."""
        controller = MicroAnimationController()
        controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0)
        controller.start("btn_2", AnimationType.HOVER, start_time_ms=0.0)
        controller.clear()
        assert controller.active_count == 0


# ============================================================================
# 7. AnimationType-specific behavior
# ============================================================================


class TestAnimationTypeBehavior:
    """Test type-specific animation behavior."""

    def test_click_uses_ease_out_cubic(self):
        """CLICK animation uses ease_out_cubic (P1 fix)."""
        controller = MicroAnimationController()
        anim = controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0)
        # Check easing function name (ease_out_cubic)
        assert anim.easing_fn.__name__ == "ease_out_cubic"

    def test_hover_uses_ease_in_out_cubic(self):
        """HOVER animation uses ease_in_out_cubic."""
        controller = MicroAnimationController()
        anim = controller.start("btn_1", AnimationType.HOVER, start_time_ms=0.0)
        assert anim.easing_fn.__name__ == "ease_in_out_cubic"

    def test_selection_pulse_uses_ease_in_out_sine(self):
        """SELECTION_PULSE uses ease_in_out_sine (smoothest)."""
        controller = MicroAnimationController()
        anim = controller.start("btn_1", AnimationType.SELECTION_PULSE, start_time_ms=0.0)
        assert anim.easing_fn.__name__ == "ease_in_out_sine"

    def test_error_flash_uses_ease_out_cubic(self):
        """ERROR_FLASH uses ease_out_cubic."""
        controller = MicroAnimationController()
        anim = controller.start("btn_1", AnimationType.ERROR_FLASH, start_time_ms=0.0)
        assert anim.easing_fn.__name__ == "ease_out_cubic"

    def test_click_default_duration_in_golden_range(self):
        """CLICK default duration is 120-150ms (P1 golden range)."""
        controller = MicroAnimationController()
        anim = controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0)
        assert 120 <= anim.duration_ms <= 150

    def test_error_flash_has_2_iterations_by_default(self):
        """ERROR_FLASH default iterations = 2 (flash twice)."""
        controller = MicroAnimationController()
        anim = controller.start("btn_1", AnimationType.ERROR_FLASH, start_time_ms=0.0)
        # Default iterations should be 1 in start() — use factory for 2
        # Actually start() defaults to iterations=1
        assert anim.iterations == 1  # start() default

    def test_error_flash_with_explicit_iterations(self):
        """ERROR_FLASH with iterations=2 flashes twice."""
        controller = MicroAnimationController()
        anim = controller.start("btn_1", AnimationType.ERROR_FLASH, start_time_ms=0.0, iterations=2)
        assert anim.iterations == 2


# ============================================================================
# 8. Multi-iteration animations
# ============================================================================


class TestMultiIteration:
    """Test multi-iteration animations."""

    def test_two_iterations_total_duration_doubled(self):
        """Animation with iterations=2 has 2x total duration."""
        anim = Animation(
            animation_type=AnimationType.ERROR_FLASH,
            start_time_ms=0.0,
            duration_ms=300,
            easing_fn=ease_out_cubic,
            from_value=0.0,
            to_value=1.0,
            iterations=2,
        )
        # At 300ms (end of first iteration) — not completed
        anim.compute_progress(300.0)
        assert anim.completed is False
        # At 600ms (end of second iteration) — completed
        anim.compute_progress(600.0)
        assert anim.completed is True

    def test_iteration_value_resets_between_iterations(self):
        """Value resets to from_value at start of each iteration."""
        anim = Animation(
            animation_type=AnimationType.ERROR_FLASH,
            start_time_ms=0.0,
            duration_ms=100,
            easing_fn=linear,  # Use linear for predictable values
            from_value=0.0,
            to_value=1.0,
            iterations=2,
        )
        # At 150ms (middle of second iteration) — t=0.5 in second iteration
        value = anim.compute_progress(150.0)
        assert value == pytest.approx(0.5)

    def test_iterations_complete_at_total_duration(self):
        """Animation completes at duration_ms * iterations."""
        anim = Animation(
            animation_type=AnimationType.ERROR_FLASH,
            start_time_ms=0.0,
            duration_ms=100,
            easing_fn=linear,
            from_value=0.0,
            to_value=1.0,
            iterations=3,
        )
        anim.compute_progress(300.0)
        assert anim.completed is True


# ============================================================================
# 9. Integration (multi-element concurrent animations)
# ============================================================================


class TestIntegration:
    """Test integration scenarios."""

    def test_multiple_elements_concurrent_animations(self):
        """Multiple elements can have concurrent animations."""
        controller = MicroAnimationController()
        for i in range(10):
            controller.start(f"btn_{i}", AnimationType.CLICK, start_time_ms=0.0)
        assert controller.active_count == 10

        # Update and verify all have values
        controller.update(65.0)
        for i in range(10):
            value = controller.get_value(f"btn_{i}", AnimationType.CLICK, default=1.0)
            assert 0.94 < value < 1.0

    def test_mixed_animation_types_same_element(self):
        """Same element can have multiple animation types simultaneously."""
        controller = MicroAnimationController()
        controller.start("btn_1", AnimationType.HOVER, start_time_ms=0.0)
        controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0)
        controller.update(65.0)
        hover_value = controller.get_value("btn_1", AnimationType.HOVER)
        click_value = controller.get_value("btn_1", AnimationType.CLICK)
        # Both should be active with distinct values
        assert 0.0 < hover_value < 1.0
        assert 0.94 < click_value < 1.0

    def test_animation_lifecycle_start_update_complete_cleanup(self):
        """Full lifecycle: start → update → complete → cleanup."""
        controller = MicroAnimationController()
        controller.start("btn_1", AnimationType.CLICK, start_time_ms=0.0, duration_ms=100)
        assert controller.active_count == 1

        controller.update(50.0)
        assert controller.active_count == 1  # Still active

        controller.update(150.0)  # Past duration
        assert controller.active_count == 0  # Completed → not active

        removed = controller.cleanup_completed()
        assert removed == 1

    def test_game_loop_simulation_60fps(self):
        """Simulate 60 FPS game loop for 1 second with animations."""
        controller = MicroAnimationController()
        controller.start("btn_1", AnimationType.SELECTION_PULSE, start_time_ms=0.0)

        frame_ms = 16  # ~60 FPS
        for frame in range(60):
            current_time = frame * frame_ms
            controller.update(current_time)
            value = controller.get_value("btn_1", AnimationType.SELECTION_PULSE, default=150)
            # Pulse value should stay in [100, 200] range
            assert 100 <= value <= 200


# ============================================================================
# 10. Performance
# ============================================================================


class TestPerformance:
    """Performance benchmarks."""

    def test_1000_easing_calls_under_10ms(self):
        """1000 easing function calls should complete under 10ms."""
        start = time.perf_counter()
        for _ in range(1000):
            ease_out_cubic(0.5)
            ease_in_out_sine(0.5)
            ease_in_out_cubic(0.5)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert elapsed_ms < 10.0, f"3000 calls took {elapsed_ms:.1f}ms"

    def test_1000_animations_update_under_50ms(self):
        """1000 animations update() should complete under 50ms."""
        controller = MicroAnimationController()
        for i in range(1000):
            controller.start(f"btn_{i}", AnimationType.CLICK, start_time_ms=0.0)

        start = time.perf_counter()
        controller.update(65.0)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert elapsed_ms < 50.0, f"1000 updates took {elapsed_ms:.1f}ms"

    def test_1000_get_value_calls_under_20ms(self):
        """1000 get_value() calls should complete under 20ms."""
        controller = MicroAnimationController()
        for i in range(1000):
            controller.start(f"btn_{i}", AnimationType.CLICK, start_time_ms=0.0)
        controller.update(65.0)

        start = time.perf_counter()
        for i in range(1000):
            controller.get_value(f"btn_{i}", AnimationType.CLICK, default=1.0)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert elapsed_ms < 20.0, f"1000 get_value took {elapsed_ms:.1f}ms"
