"""V-12 (Wave E3): Unit tests for AccessibilityManager.

Tests cover 6 dimensions (Happy/Error/Boundary/Performance/Config/Integration):
1. Color-blind mode setting (set_color_blind_mode, no-op on same mode)
2. Font scale setting (4 levels, error on out-of-range, closest-match by factor)
3. Color transformation (Protanopia/Deuteranopia/Tritanopia matrices, NONE identity)
4. Layer scoping (UI/terrain affected, units excluded — Wave B-rev)
5. Listener notification (register/unregister/notify on changes)
6. State persistence (snapshot/restore/reset)
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest  # noqa: E402

from pycc2.presentation.ui.accessibility import (  # noqa: E402
    APPLICABLE_LAYERS,
    DEFAULT_FONT_SCALE_INDEX,
    EXCLUDED_LAYERS,
    FONT_SCALE_FACTORS,
    FONT_SCALE_LABELS,
    AccessibilityManager,
    AccessibilityState,
    ColorBlindMode,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_manager() -> AccessibilityManager:
    return AccessibilityManager()


# ============================================================================
# 1. Color-blind mode setting (happy + boundary + config)
# ============================================================================


class TestColorBlindModeSetting:
    """Test set_color_blind_mode method."""

    def test_default_mode_is_none(self):
        """Verify: default color-blind mode is NONE."""
        manager = _make_manager()
        assert manager.color_blind_mode == ColorBlindMode.NONE

    def test_set_mode_to_protanopia(self):
        """Verify: set_color_blind_mode to PROTANOPIA."""
        manager = _make_manager()
        manager.set_color_blind_mode(ColorBlindMode.PROTANOPIA)
        assert manager.color_blind_mode == ColorBlindMode.PROTANOPIA

    def test_set_mode_to_deuteranopia(self):
        """Verify: set_color_blind_mode to DEUTERANOPIA."""
        manager = _make_manager()
        manager.set_color_blind_mode(ColorBlindMode.DEUTERANOPIA)
        assert manager.color_blind_mode == ColorBlindMode.DEUTERANOPIA

    def test_set_mode_to_tritanopia(self):
        """Verify: set_color_blind_mode to TRITANOPIA."""
        manager = _make_manager()
        manager.set_color_blind_mode(ColorBlindMode.TRITANOPIA)
        assert manager.color_blind_mode == ColorBlindMode.TRITANOPIA

    def test_set_same_mode_is_noop(self):
        """Verify: setting same mode is a no-op (no listener notification)."""
        manager = _make_manager()
        call_count = [0]

        def listener() -> None:
            call_count[0] += 1

        manager.register_listener(listener)
        manager.set_color_blind_mode(ColorBlindMode.NONE)  # Same as default
        assert call_count[0] == 0  # No notification

    def test_set_different_mode_notifies_listener(self):
        """Verify: setting different mode notifies listeners."""
        manager = _make_manager()
        call_count = [0]

        def listener() -> None:
            call_count[0] += 1

        manager.register_listener(listener)
        manager.set_color_blind_mode(ColorBlindMode.PROTANOPIA)
        assert call_count[0] == 1


# ============================================================================
# 2. Font scale setting (happy + error + boundary + config)
# ============================================================================


class TestFontScaleSetting:
    """Test set_font_scale method."""

    def test_default_font_scale_is_medium(self):
        """Verify: default font scale is index 1 (medium)."""
        manager = _make_manager()
        assert manager.font_scale_index == DEFAULT_FONT_SCALE_INDEX
        assert manager.font_scale_index == 1
        assert manager.font_scale_factor == 1.0

    def test_set_font_scale_to_small(self):
        """Verify: set_font_scale(0) sets to small (0.85)."""
        manager = _make_manager()
        manager.set_font_scale(0)
        assert manager.font_scale_index == 0
        assert manager.font_scale_factor == 0.85

    def test_set_font_scale_to_large(self):
        """Verify: set_font_scale(2) sets to large (1.25)."""
        manager = _make_manager()
        manager.set_font_scale(2)
        assert manager.font_scale_index == 2
        assert manager.font_scale_factor == 1.25

    def test_set_font_scale_to_extra_large(self):
        """Verify: set_font_scale(3) sets to extra-large (1.5)."""
        manager = _make_manager()
        manager.set_font_scale(3)
        assert manager.font_scale_index == 3
        assert manager.font_scale_factor == 1.5

    def test_set_font_scale_negative_raises_value_error(self):
        """Verify: set_font_scale(-1) raises ValueError."""
        manager = _make_manager()
        with pytest.raises(ValueError, match="Font scale index"):
            manager.set_font_scale(-1)

    def test_set_font_scale_out_of_range_raises_value_error(self):
        """Verify: set_font_scale(4) raises ValueError (only 0-3 allowed)."""
        manager = _make_manager()
        with pytest.raises(ValueError, match="Font scale index"):
            manager.set_font_scale(4)

    def test_set_same_font_scale_is_noop(self):
        """Verify: setting same font scale is a no-op."""
        manager = _make_manager()
        call_count = [0]

        def listener() -> None:
            call_count[0] += 1

        manager.register_listener(listener)
        manager.set_font_scale(DEFAULT_FONT_SCALE_INDEX)  # Same as default
        assert call_count[0] == 0

    def test_set_font_scale_by_factor_closest_match(self):
        """Verify: set_font_scale_by_factor selects closest match."""
        manager = _make_manager()
        # 1.3 should match index 2 (1.25) closer than index 1 (1.0)
        manager.set_font_scale_by_factor(1.3)
        assert manager.font_scale_index == 2
        assert manager.font_scale_factor == 1.25

    def test_set_font_scale_by_factor_exact_match(self):
        """Verify: set_font_scale_by_factor with exact value."""
        manager = _make_manager()
        manager.set_font_scale_by_factor(1.5)
        assert manager.font_scale_index == 3

    def test_font_scale_label_chinese(self):
        """Verify: font_scale_label returns Chinese label."""
        manager = _make_manager()
        manager.set_font_scale(0)
        assert manager.font_scale_label == "小"
        manager.set_font_scale(1)
        assert manager.font_scale_label == "中"
        manager.set_font_scale(2)
        assert manager.font_scale_label == "大"
        manager.set_font_scale(3)
        assert manager.font_scale_label == "特大"

    def test_font_scale_factors_has_4_levels(self):
        """Verify: FONT_SCALE_FACTORS has exactly 4 levels (Wave B-rev)."""
        assert len(FONT_SCALE_FACTORS) == 4
        assert FONT_SCALE_FACTORS == (0.85, 1.0, 1.25, 1.5)

    def test_font_scale_labels_has_4_levels(self):
        """Verify: FONT_SCALE_LABELS has 4 entries."""
        assert len(FONT_SCALE_LABELS) == 4


# ============================================================================
# 3. Color transformation (happy + config + integration)
# ============================================================================


class TestColorTransformation:
    """Test transform_color method."""

    def test_transform_none_mode_returns_input_unchanged(self):
        """Verify: NONE mode returns input color unchanged."""
        manager = _make_manager()
        assert manager.transform_color((100, 150, 200)) == (100, 150, 200)

    def test_transform_protanopia_changes_red_heavy_color(self):
        """Verify: PROTANOPIA mode transforms red-heavy colors."""
        manager = _make_manager()
        manager.set_color_blind_mode(ColorBlindMode.PROTANOPIA)
        original = (255, 0, 0)  # Pure red
        transformed = manager.transform_color(original)
        # Pure red should NOT stay as pure red under protanopia
        assert transformed != original

    def test_transform_deuteranopia_changes_green_heavy_color(self):
        """Verify: DEUTERANOPIA mode transforms green-heavy colors."""
        manager = _make_manager()
        manager.set_color_blind_mode(ColorBlindMode.DEUTERANOPIA)
        original = (0, 255, 0)  # Pure green
        transformed = manager.transform_color(original)
        assert transformed != original

    def test_transform_tritanopia_changes_blue_heavy_color(self):
        """Verify: TRITANOPIA mode transforms blue-heavy colors."""
        manager = _make_manager()
        manager.set_color_blind_mode(ColorBlindMode.TRITANOPIA)
        original = (0, 0, 255)  # Pure blue
        transformed = manager.transform_color(original)
        assert transformed != original

    def test_transform_clamps_to_0_255(self):
        """Verify: transformed values are clamped to 0-255 range."""
        manager = _make_manager()
        manager.set_color_blind_mode(ColorBlindMode.PROTANOPIA)
        # Test extreme values
        for original in [(0, 0, 0), (255, 255, 255), (255, 0, 0), (0, 255, 0), (0, 0, 255)]:
            transformed = manager.transform_color(original)
            for channel in transformed:
                assert 0 <= channel <= 255

    def test_transform_batch_returns_all_transformed(self):
        """Verify: transform_color_batch transforms all colors in list."""
        manager = _make_manager()
        manager.set_color_blind_mode(ColorBlindMode.PROTANOPIA)
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
        transformed = manager.transform_color_batch(colors)
        assert len(transformed) == 3
        # All should be different from original (since all are pure primary colors)
        for orig, trans in zip(colors, transformed, strict=True):
            assert trans != orig

    def test_transform_returns_3_tuple(self):
        """Verify: transform_color returns a 3-tuple of ints."""
        manager = _make_manager()
        manager.set_color_blind_mode(ColorBlindMode.DEUTERANOPIA)
        result = manager.transform_color((100, 150, 200))
        assert isinstance(result, tuple)
        assert len(result) == 3
        for channel in result:
            assert isinstance(channel, int)


# ============================================================================
# 4. Layer scoping (Wave B-rev: UI/terrain only, NOT units)
# ============================================================================


class TestLayerScoping:
    """Test Wave B-rev layer scoping for color-blind mode."""

    def test_ui_layer_is_affected(self):
        """Verify: UI layer is affected by color-blind mode."""
        manager = _make_manager()
        assert manager.is_layer_affected("ui") is True

    def test_terrain_layer_is_affected(self):
        """Verify: terrain layer is affected by color-blind mode."""
        manager = _make_manager()
        assert manager.is_layer_affected("terrain") is True

    def test_units_layer_is_not_affected(self):
        """Verify: units layer is NOT affected (Wave B-rev safeguard)."""
        manager = _make_manager()
        assert manager.is_layer_affected("units") is False

    def test_applicable_layers_contains_ui_and_terrain(self):
        """Verify: APPLICABLE_LAYERS contains ui and terrain."""
        assert "ui" in APPLICABLE_LAYERS
        assert "terrain" in APPLICABLE_LAYERS

    def test_excluded_layers_contains_units(self):
        """Verify: EXCLUDED_LAYERS contains units."""
        assert "units" in EXCLUDED_LAYERS

    def test_unknown_layer_is_not_affected(self):
        """Verify: unknown layer names are not affected."""
        manager = _make_manager()
        assert manager.is_layer_affected("unknown") is False
        assert manager.is_layer_affected("") is False


# ============================================================================
# 5. Listener notification (happy + integration)
# ============================================================================


class TestListenerNotification:
    """Test listener notification on setting changes."""

    def test_register_listener(self):
        """Verify: register_listener adds a listener."""
        manager = _make_manager()
        assert manager.listener_count() == 0

        def listener() -> None:
            pass

        manager.register_listener(listener)
        assert manager.listener_count() == 1

    def test_register_same_listener_twice_is_idempotent(self):
        """Verify: registering same listener twice is idempotent."""
        manager = _make_manager()

        def listener() -> None:
            pass

        manager.register_listener(listener)
        manager.register_listener(listener)
        assert manager.listener_count() == 1

    def test_unregister_listener(self):
        """Verify: unregister_listener removes a listener."""
        manager = _make_manager()

        def listener() -> None:
            pass

        manager.register_listener(listener)
        assert manager.listener_count() == 1
        manager.unregister_listener(listener)
        assert manager.listener_count() == 0

    def test_unregister_unknown_listener_is_safe(self):
        """Verify: unregistering an unknown listener is safe (no error)."""
        manager = _make_manager()

        def listener() -> None:
            pass

        # Should not raise
        manager.unregister_listener(listener)
        assert manager.listener_count() == 0

    def test_color_blind_change_notifies_listener(self):
        """Verify: color-blind mode change notifies listener."""
        manager = _make_manager()
        notifications = [0]

        def listener() -> None:
            notifications[0] += 1

        manager.register_listener(listener)
        manager.set_color_blind_mode(ColorBlindMode.PROTANOPIA)
        assert notifications[0] == 1

    def test_font_scale_change_notifies_listener(self):
        """Verify: font scale change notifies listener."""
        manager = _make_manager()
        notifications = [0]

        def listener() -> None:
            notifications[0] += 1

        manager.register_listener(listener)
        manager.set_font_scale(2)
        assert notifications[0] == 1

    def test_listener_exception_does_not_block_others(self):
        """Verify: a failing listener doesn't block subsequent listeners."""
        manager = _make_manager()
        call_count = [0, 0]

        def failing_listener() -> None:
            call_count[0] += 1
            raise RuntimeError("Test failure")

        def healthy_listener() -> None:
            call_count[1] += 1

        manager.register_listener(failing_listener)
        manager.register_listener(healthy_listener)
        # Should not raise, and healthy_listener should still be called
        manager.set_color_blind_mode(ColorBlindMode.PROTANOPIA)
        assert call_count[0] == 1
        assert call_count[1] == 1


# ============================================================================
# 6. State persistence (happy + config + integration)
# ============================================================================


class TestStatePersistence:
    """Test state snapshot, restore, and reset."""

    def test_state_snapshot_captures_current_settings(self):
        """Verify: state property captures current settings."""
        manager = _make_manager()
        manager.set_color_blind_mode(ColorBlindMode.DEUTERANOPIA)
        manager.set_font_scale(3)
        state = manager.state
        assert state.color_blind_mode == ColorBlindMode.DEUTERANOPIA
        assert state.font_scale_index == 3

    def test_restore_state_applies_saved_settings(self):
        """Verify: restore_state applies previously saved settings."""
        manager = _make_manager()
        state = AccessibilityState(
            color_blind_mode=ColorBlindMode.TRITANOPIA,
            font_scale_index=2,
        )
        manager.restore_state(state)
        assert manager.color_blind_mode == ColorBlindMode.TRITANOPIA
        assert manager.font_scale_index == 2

    def test_reset_returns_to_defaults(self):
        """Verify: reset() returns to default settings."""
        manager = _make_manager()
        manager.set_color_blind_mode(ColorBlindMode.PROTANOPIA)
        manager.set_font_scale(3)
        manager.reset()
        assert manager.color_blind_mode == ColorBlindMode.NONE
        assert manager.font_scale_index == DEFAULT_FONT_SCALE_INDEX
        assert manager.font_scale_factor == 1.0

    def test_restore_state_clamps_out_of_range_index(self):
        """Verify: restore_state clamps out-of-range font_scale_index."""
        manager = _make_manager()
        state = AccessibilityState(
            color_blind_mode=ColorBlindMode.NONE,
            font_scale_index=99,  # Out of range
        )
        manager.restore_state(state)
        # Should be clamped to max valid index (3)
        assert manager.font_scale_index == 3

    def test_restore_state_clamps_negative_index(self):
        """Verify: restore_state clamps negative font_scale_index."""
        manager = _make_manager()
        state = AccessibilityState(
            color_blind_mode=ColorBlindMode.NONE,
            font_scale_index=-5,  # Negative
        )
        manager.restore_state(state)
        # Should be clamped to min valid index (0)
        assert manager.font_scale_index == 0

    def test_state_dataclass_has_required_fields(self):
        """Verify: AccessibilityState has color_blind_mode and font_scale_index."""
        state = AccessibilityState()
        assert hasattr(state, "color_blind_mode")
        assert hasattr(state, "font_scale_index")
        assert state.color_blind_mode == ColorBlindMode.NONE
        assert state.font_scale_index == DEFAULT_FONT_SCALE_INDEX
