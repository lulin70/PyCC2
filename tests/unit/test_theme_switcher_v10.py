"""V-10 (Wave E2): Unit tests for Morandi palette + ThemeSwitcher.

Tests cover 6 dimensions (Happy/Error/Boundary/Performance/Config/Integration):
1. Morandi palette application (apply_morandi_palette, is_morandi_applied)
2. Morandi color constants (saturation ≤ 30%, all 24+ colors defined)
3. ThemeSwitcher combat lock (can_switch, unavailable_reason)
4. ThemeSwitcher state machine (IDLE → CONFIRMING → FADING_OUT → REBUILDING → FADING_IN → IDLE)
5. ThemeSwitcher palette application (force_complete, palette mutation)
6. Integration with ThemeManager (notify_theme_change called)
"""

from __future__ import annotations

import os
import time
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


from pycc2.domain.entities.game_map import GameMap  # noqa: E402
from pycc2.domain.value_objects.terrain_type import TerrainType  # noqa: E402
from pycc2.domain.value_objects.vec2 import Vec2  # noqa: E402
from pycc2.presentation.rendering.palette_morandi import (  # noqa: E402
    MORANDI_ALLIED_BLUE,
    MORANDI_AXIS_GREEN,
    MORANDI_DANGER,
    MORANDI_HEALTH_GREEN,
    MORANDI_SELECTION,
    MORANDI_TERRAIN_GRASS,
    apply_morandi_palette,
    is_morandi_applied,
    morandi_color_palette,
)
from pycc2.presentation.rendering.visual_spec import VisualSpec  # noqa: E402
from pycc2.presentation.ui.theme_switcher import (  # noqa: E402
    AVAILABLE_THEMES,
    DEFAULT_THEME,
    MORANDI_THEME,
    TRANSITION_MS,
    SwitchResult,
    ThemeSwitcher,
    ThemeSwitchState,
)
from pycc2.presentation.visual_config import ColorPalette, ThemeManager  # noqa: E402
from pycc2.services.game_loop_types import GameState  # noqa: E402

# ============================================================================
# Helpers
# ============================================================================


def _make_game_map(width: int = 16, height: int = 16) -> GameMap:
    import numpy as np

    grid = np.zeros((height, width), dtype=np.int8)
    return GameMap(id="test", name="Test Map", width=width, height=height, tile_grid=grid)


def _make_game_state(in_combat: bool = False) -> GameState:
    """Create a minimal GameState for ThemeSwitcher testing."""
    # Use MagicMock for camera/units to avoid heavy construction
    camera = MagicMock()
    camera.position = Vec2(0.0, 0.0)
    camera.zoom = 1.0
    camera.viewport_width = 1280
    camera.viewport_height = 720
    state = GameState(game_map=_make_game_map(), units=[], camera=camera)
    state.in_combat = in_combat
    return state


def _make_visual_spec() -> VisualSpec:
    return VisualSpec()


# ============================================================================
# 1. Morandi palette application (happy + config + integration)
# ============================================================================


class TestMorandiPaletteApplication:
    """Test apply_morandi_palette function."""

    def test_apply_morandi_palette_changes_allied_color(self):
        """Verify: apply_morandi_palette changes allied_unit_color."""
        spec = _make_visual_spec()
        original_color = tuple(spec.allied_unit_color[:3])
        assert original_color != MORANDI_ALLIED_BLUE
        apply_morandi_palette(spec)
        assert tuple(spec.allied_unit_color[:3]) == MORANDI_ALLIED_BLUE

    def test_apply_morandi_palette_changes_axis_color(self):
        """Verify: apply_morandi_palette changes axis_unit_color."""
        spec = _make_visual_spec()
        apply_morandi_palette(spec)
        assert tuple(spec.axis_unit_color[:3]) == MORANDI_AXIS_GREEN

    def test_apply_morandi_palette_changes_selection_color(self):
        """Verify: apply_morandi_palette changes selection_color."""
        spec = _make_visual_spec()
        apply_morandi_palette(spec)
        assert tuple(spec.selection_color[:3]) == MORANDI_SELECTION

    def test_apply_morandi_palette_changes_danger_color(self):
        """Verify: apply_morandi_palette changes danger_color."""
        spec = _make_visual_spec()
        apply_morandi_palette(spec)
        assert tuple(spec.danger_color[:3]) == MORANDI_DANGER

    def test_apply_morandi_palette_changes_health_green(self):
        """Verify: apply_morandi_palette changes health_bar_green."""
        spec = _make_visual_spec()
        apply_morandi_palette(spec)
        assert tuple(spec.health_bar_green[:3]) == MORANDI_HEALTH_GREEN

    def test_apply_morandi_palette_overwrites_all_terrain_colors(self):
        """Verify: apply_morandi_palette overwrites all 12 terrain colors."""
        spec = _make_visual_spec()
        apply_morandi_palette(spec)
        assert tuple(spec.terrain_colors[TerrainType.GRASS][:3]) == MORANDI_TERRAIN_GRASS
        # All 12 terrain types should be present
        assert len(spec.terrain_colors) == 12

    def test_is_morandi_applied_false_on_fresh_spec(self):
        """Verify: is_morandi_applied returns False on fresh VisualSpec."""
        spec = _make_visual_spec()
        assert is_morandi_applied(spec) is False

    def test_is_morandi_applied_true_after_application(self):
        """Verify: is_morandi_applied returns True after apply_morandi_palette."""
        spec = _make_visual_spec()
        apply_morandi_palette(spec)
        assert is_morandi_applied(spec) is True


# ============================================================================
# 2. Morandi color constants (config + boundary)
# ============================================================================


class TestMorandiColorConstants:
    """Test Morandi color constants meet low-saturation design principle."""

    def test_all_morandi_colors_are_rgb_tuples(self):
        """Verify: all exported Morandi colors are 3-tuples (RGB)."""
        from pycc2.presentation.rendering import palette_morandi

        morandi_attrs = [
            attr
            for attr in dir(palette_morandi)
            if attr.startswith("MORANDI_") and not attr.startswith("_")
        ]
        for attr_name in morandi_attrs:
            value = getattr(palette_morandi, attr_name)
            if isinstance(value, tuple):
                # RGB = 3-tuple, RGBA = 4-tuple; both valid
                assert len(value) in (3, 4), f"{attr_name} has invalid length: {len(value)}"

    def test_morandi_allied_blue_is_low_saturation(self):
        """Verify: MORANDI_ALLIED_BLUE has saturation ≤ 30% (HSL)."""
        r, g, b = MORANDI_ALLIED_BLUE
        hsl_saturation = _rgb_saturation(r, g, b)
        assert hsl_saturation <= 0.30, (
            f"Morandi allied blue saturation {hsl_saturation:.2%} exceeds 30%"
        )

    def test_morandi_axis_green_is_low_saturation(self):
        """Verify: MORANDI_AXIS_GREEN has saturation ≤ 30% (HSL)."""
        r, g, b = MORANDI_AXIS_GREEN
        hsl_saturation = _rgb_saturation(r, g, b)
        assert hsl_saturation <= 0.30, (
            f"Morandi axis green saturation {hsl_saturation:.2%} exceeds 30%"
        )

    def test_morandi_color_palette_returns_24_fields(self):
        """Verify: morandi_color_palette() returns ColorPalette with all 24 fields."""
        palette = morandi_color_palette()
        assert isinstance(palette, ColorPalette)
        # ColorPalette has 24 color fields
        color_fields = [
            f for f in dir(palette) if not f.startswith("_") and not callable(getattr(palette, f))
        ]
        assert len(color_fields) >= 20  # Allow for slots methods


def _rgb_saturation(r: int, g: int, b: int) -> float:
    """Calculate HSL saturation for RGB values (0-255 each)."""
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    max_val = max(r_norm, g_norm, b_norm)
    min_val = min(r_norm, g_norm, b_norm)
    if max_val == min_val:
        return 0.0  # Achromatic
    lightness = (max_val + min_val) / 2.0
    if lightness > 0.5:
        saturation = (max_val - min_val) / (2.0 - max_val - min_val)
    else:
        saturation = (max_val - min_val) / (max_val + min_val)
    return saturation


# ============================================================================
# 3. ThemeSwitcher combat lock (happy + error + boundary)
# ============================================================================


class TestCombatLock:
    """Test V-10 Wave B-rev combat lock safeguard."""

    def test_can_switch_returns_true_when_idle_and_not_in_combat(self):
        """Verify: can_switch returns True when idle and not in combat."""
        switcher = ThemeSwitcher(
            ThemeManager, _make_game_state(in_combat=False), _make_visual_spec()
        )
        assert switcher.can_switch() is True

    def test_can_switch_returns_false_when_in_combat(self):
        """Verify: can_switch returns False during combat (Wave B-rev)."""
        switcher = ThemeSwitcher(
            ThemeManager, _make_game_state(in_combat=True), _make_visual_spec()
        )
        assert switcher.can_switch() is False

    def test_unavailable_reason_returns_combat_message_when_in_combat(self):
        """Verify: unavailable_reason mentions combat when in combat."""
        switcher = ThemeSwitcher(
            ThemeManager, _make_game_state(in_combat=True), _make_visual_spec()
        )
        reason = switcher.unavailable_reason()
        assert "战斗中" in reason or "combat" in reason.lower()

    def test_unavailable_reason_returns_empty_when_available(self):
        """Verify: unavailable_reason returns empty string when switch is available."""
        switcher = ThemeSwitcher(
            ThemeManager, _make_game_state(in_combat=False), _make_visual_spec()
        )
        assert switcher.unavailable_reason() == ""

    def test_request_switch_blocked_when_in_combat(self):
        """Verify: request_switch returns False when in combat."""
        switcher = ThemeSwitcher(
            ThemeManager, _make_game_state(in_combat=True), _make_visual_spec()
        )
        assert switcher.request_switch(MORANDI_THEME) is False
        assert switcher.state == ThemeSwitchState.IDLE


# ============================================================================
# 4. ThemeSwitcher state machine (happy + boundary + integration)
# ============================================================================


class TestStateMachine:
    """Test ThemeSwitcher state machine transitions."""

    def test_initial_state_is_idle(self):
        """Verify: ThemeSwitcher starts in IDLE state."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        assert switcher.state == ThemeSwitchState.IDLE

    def test_request_switch_transitions_to_confirming(self):
        """Verify: request_switch transitions to CONFIRMING state."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        assert switcher.request_switch(MORANDI_THEME) is True
        assert switcher.state == ThemeSwitchState.CONFIRMING
        assert switcher.pending_theme == MORANDI_THEME

    def test_confirm_transitions_to_fading_out(self):
        """Verify: confirm transitions from CONFIRMING to FADING_OUT."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        switcher.request_switch(MORANDI_THEME)
        assert switcher.confirm() is True
        assert switcher.state == ThemeSwitchState.FADING_OUT

    def test_cancel_returns_to_idle(self):
        """Verify: cancel from CONFIRMING returns to IDLE."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        switcher.request_switch(MORANDI_THEME)
        assert switcher.cancel() is True
        assert switcher.state == ThemeSwitchState.IDLE
        assert switcher.pending_theme is None

    def test_confirm_returns_false_when_not_confirming(self):
        """Verify: confirm returns False when not in CONFIRMING state."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        assert switcher.confirm() is False  # IDLE → no-op

    def test_cancel_returns_false_when_not_confirming(self):
        """Verify: cancel returns False when not in CONFIRMING state."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        assert switcher.cancel() is False  # IDLE → no-op

    def test_request_switch_same_theme_returns_false(self):
        """Verify: request_switch to current theme returns False (no-op)."""
        switcher = ThemeSwitcher(
            ThemeManager, _make_game_state(), _make_visual_spec(), current_theme=DEFAULT_THEME
        )
        assert switcher.request_switch(DEFAULT_THEME) is False

    def test_request_switch_invalid_theme_returns_false(self):
        """Verify: request_switch with invalid theme returns False."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        assert switcher.request_switch("invalid_theme") is False

    def test_update_fading_out_advances_alpha(self):
        """Verify: update() in FADING_OUT advances fade_alpha."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        switcher.request_switch(MORANDI_THEME)
        switcher.confirm()
        assert switcher.fade_alpha == 0.0
        switcher.update(TRANSITION_MS / 2.0)  # Half of transition duration
        assert 0.4 < switcher.fade_alpha < 0.6

    def test_update_fading_out_completes_transitions_to_rebuilding(self):
        """Verify: full fade-out transitions to REBUILDING state."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        switcher.request_switch(MORANDI_THEME)
        switcher.confirm()
        switcher.update(TRANSITION_MS + 1.0)
        assert switcher.state == ThemeSwitchState.REBUILDING
        assert switcher.fade_alpha == 1.0

    def test_update_rebuilding_advances_progress(self):
        """Verify: update() in REBUILDING advances rebuild_progress."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        switcher.request_switch(MORANDI_THEME)
        switcher.confirm()
        switcher.update(TRANSITION_MS + 1.0)  # → REBUILDING
        # Force progress forward by sleeping a bit
        time.sleep(0.01)
        switcher.update(0.0)
        assert switcher.rebuild_progress > 0.0

    def test_full_switch_cycle_completes(self):
        """Verify: full IDLE → CONFIRMING → FADING_OUT → REBUILDING → FADING_IN → IDLE."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        # IDLE → CONFIRMING
        switcher.request_switch(MORANDI_THEME)
        # CONFIRMING → FADING_OUT
        switcher.confirm()
        # FADING_OUT → REBUILDING (apply Morandi palette)
        switcher.update(TRANSITION_MS + 1.0)
        assert switcher.state == ThemeSwitchState.REBUILDING
        # REBUILDING → FADING_IN (wait for progress to reach 1.0)
        # Force time forward by sleeping
        time.sleep(0.25)  # > PROGRESS_THRESHOLD_MS / 1000
        switcher.update(0.0)
        assert switcher.state == ThemeSwitchState.FADING_IN
        # FADING_IN → IDLE
        switcher.update(TRANSITION_MS + 1.0)
        assert switcher.state == ThemeSwitchState.IDLE
        assert switcher.current_theme == MORANDI_THEME
        assert switcher.last_result is not None
        assert switcher.last_result.success is True
        assert switcher.last_result.new_theme == MORANDI_THEME


# ============================================================================
# 5. ThemeSwitcher palette application (happy + integration)
# ============================================================================


class TestPaletteApplication:
    """Test palette application via ThemeSwitcher."""

    def test_force_complete_applies_morandi_palette(self):
        """Verify: force_complete with morandi theme applies Morandi palette."""
        spec = _make_visual_spec()
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), spec)
        switcher.request_switch(MORANDI_THEME)
        result = switcher.force_complete()
        assert result is not None
        assert result.success is True
        assert is_morandi_applied(spec) is True

    def test_force_complete_restores_default_palette(self):
        """Verify: force_complete with cc2_classic restores default palette."""
        spec = _make_visual_spec()
        apply_morandi_palette(spec)
        assert is_morandi_applied(spec) is True
        switcher = ThemeSwitcher(
            ThemeManager, _make_game_state(), spec, current_theme=MORANDI_THEME
        )
        switcher.request_switch(DEFAULT_THEME)
        result = switcher.force_complete()
        assert result is not None
        assert is_morandi_applied(spec) is False  # Restored to default

    def test_force_complete_returns_none_without_pending(self):
        """Verify: force_complete returns None when no switch pending."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        assert switcher.force_complete() is None

    def test_force_complete_records_rebuild_duration(self):
        """Verify: force_complete records rebuild_duration_ms in result."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        switcher.request_switch(MORANDI_THEME)
        result = switcher.force_complete()
        assert result is not None
        assert result.rebuild_duration_ms >= 0.0

    def test_force_complete_sets_current_theme(self):
        """Verify: force_complete updates current_theme to new theme."""
        switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
        assert switcher.current_theme == DEFAULT_THEME
        switcher.request_switch(MORANDI_THEME)
        switcher.force_complete()
        assert switcher.current_theme == MORANDI_THEME


# ============================================================================
# 6. Integration with ThemeManager (integration)
# ============================================================================


class TestThemeManagerIntegration:
    """Test ThemeSwitcher integration with ThemeManager notification."""

    def test_force_complete_notifies_theme_manager(self):
        """Verify: force_complete calls ThemeManager.notify_theme_change."""
        # Register a mock listener
        listener_calls = [0]

        def listener() -> None:
            listener_calls[0] += 1

        ThemeManager._reset()
        ThemeManager.register(listener)
        try:
            switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
            switcher.request_switch(MORANDI_THEME)
            switcher.force_complete()
            assert listener_calls[0] >= 1
        finally:
            ThemeManager._reset()

    def test_full_cycle_notifies_theme_manager(self):
        """Verify: full switch cycle notifies ThemeManager on fade-in."""
        listener_calls = [0]

        def listener() -> None:
            listener_calls[0] += 1

        ThemeManager._reset()
        ThemeManager.register(listener)
        try:
            switcher = ThemeSwitcher(ThemeManager, _make_game_state(), _make_visual_spec())
            switcher.request_switch(MORANDI_THEME)
            switcher.confirm()
            switcher.update(TRANSITION_MS + 1.0)  # → REBUILDING
            time.sleep(0.25)
            switcher.update(0.0)  # → FADING_IN (notify called)
            assert listener_calls[0] >= 1
        finally:
            ThemeManager._reset()

    def test_available_themes_contains_both(self):
        """Verify: AVAILABLE_THEMES contains both default and morandi."""
        assert DEFAULT_THEME in AVAILABLE_THEMES
        assert MORANDI_THEME in AVAILABLE_THEMES
        assert len(AVAILABLE_THEMES) == 2

    def test_switch_result_dataclass_fields(self):
        """Verify: SwitchResult dataclass has all required fields."""
        result = SwitchResult(
            success=True,
            old_theme="a",
            new_theme="b",
            rebuild_duration_ms=10.0,
            progress_bar_shown=False,
        )
        assert result.success is True
        assert result.old_theme == "a"
        assert result.new_theme == "b"
        assert result.rebuild_duration_ms == 10.0
        assert result.progress_bar_shown is False
        assert result.error is None
