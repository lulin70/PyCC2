"""Unit tests for V-01 visual_config.py (Wave C3a).

Verifies:
    1. All 5 dataclasses are frozen=True (immutability)
    2. All fields have correct default values
    3. Total parameter count ≥ 40 (V-01 design requirement)
    4. DEFAULT_VISUAL_CONFIG singleton is usable
    5. ThemeManager register/unregister/notify works correctly
    6. ThemeManager handles listener exceptions gracefully
    7. pygame.Color mutability trap is documented (Wave B-rev lesson 4)
"""

from __future__ import annotations

import logging
from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest
from pygame import Color

from pycc2.presentation.visual_config import (
    DEFAULT_VISUAL_CONFIG,
    AnimationTimings,
    ColorPalette,
    ThemeManager,
    VisualConfig,
    VisualDimensions,
    VisualEffects,
)

# ── 1. Frozen dataclass immutability ────────────────────────────────


@pytest.mark.parametrize(
    "dataclass_cls",
    [
        ColorPalette,
        VisualDimensions,
        AnimationTimings,
        VisualEffects,
        VisualConfig,
    ],
)
def test_dataclass_is_frozen(dataclass_cls) -> None:
    """All 5 dataclasses must be frozen=True (V-01 design)."""
    assert is_dataclass(dataclass_cls)
    # Frozen dataclasses raise FrozenInstanceError on attribute assignment.
    instance = dataclass_cls()
    first_field_name = next(iter(fields(dataclass_cls))).name
    with pytest.raises(FrozenInstanceError):
        setattr(instance, first_field_name, None)


def test_color_palette_frozen() -> None:
    """ColorPalette must be frozen (cannot rebind fields)."""
    palette = ColorPalette()
    with pytest.raises(FrozenInstanceError):
        palette.GRASS_PRIMARY = Color(0, 0, 0)  # type: ignore[misc]


def test_visual_dimensions_frozen() -> None:
    """VisualDimensions must be frozen."""
    dims = VisualDimensions()
    with pytest.raises(FrozenInstanceError):
        dims.TILE_SIZE = 64  # type: ignore[misc]


def test_animation_timings_frozen() -> None:
    """AnimationTimings must be frozen."""
    timings = AnimationTimings()
    with pytest.raises(FrozenInstanceError):
        timings.EXPLOSION_DURATION = 1.0  # type: ignore[misc]


def test_visual_effects_frozen() -> None:
    """VisualEffects must be frozen."""
    effects = VisualEffects()
    with pytest.raises(FrozenInstanceError):
        effects.SHADOW_ALPHA = 255  # type: ignore[misc]


def test_visual_config_frozen() -> None:
    """VisualConfig must be frozen."""
    config = VisualConfig()
    with pytest.raises(FrozenInstanceError):
        config.palette = ColorPalette()  # type: ignore[misc]


# ── 2. Default values are correct ────────────────────────────────────


def test_color_palette_defaults() -> None:
    """ColorPalette defaults match CC2-faithful RGB values."""
    palette = ColorPalette()
    assert Color(76, 124, 35) == palette.GRASS_PRIMARY
    assert Color(60, 100, 140) == palette.WATER_PRIMARY
    assert Color(40, 40, 50) == palette.UI_PANEL
    assert Color(100, 200, 100) == palette.UI_VICTORY
    assert Color(200, 80, 80) == palette.UI_DEFEAT


def test_visual_dimensions_defaults() -> None:
    """VisualDimensions defaults match v0.8.0 values (TILE_SIZE=48)."""
    dims = VisualDimensions()
    assert dims.TILE_SIZE == 48
    assert dims.SPRITE_SIZE == 48
    assert dims.UNIT_SIZE_INFANTRY == (18, 22)
    assert dims.UNIT_SIZE_TANK_HEAVY == (42, 42)
    assert dims.PANEL_WIDTH_BOTTOM == 1280
    assert dims.MINIMAP_SIZE == (200, 200)


def test_animation_timings_defaults() -> None:
    """AnimationTimings defaults match Wave B-rev values (CLICK=130ms)."""
    timings = AnimationTimings()
    assert timings.EXPLOSION_DURATION == 0.3
    assert timings.CLICK_TRANSITION == 0.13   # Wave B-rev: 100ms → 130ms
    assert timings.HOVER_TRANSITION == 0.2
    assert timings.EASING_CURVE == "ease_out_cubic"
    assert timings.SMOKE_GRENADE_DURATION == 45.0


def test_visual_effects_defaults() -> None:
    """VisualEffects defaults match v0.8.0 values."""
    effects = VisualEffects()
    assert effects.SHADOW_ALPHA == 128
    assert effects.SHADOW_OFFSET == (4, 4)
    assert effects.PARTICLE_COUNT_EXPLOSION == 40
    assert effects.LINE_THICKNESS_HIGHLIGHT == 2
    assert effects.FOG_ALPHA == 100


# ── 3. Total parameter count ≥ 40 (V-01 design requirement) ─────────


def test_total_parameter_count_meets_v01_requirement() -> None:
    """V-01 design requires ≥ 40 total parameters across all dataclasses."""
    palette_count = len(fields(ColorPalette))
    dims_count = len(fields(VisualDimensions))
    timings_count = len(fields(AnimationTimings))
    effects_count = len(fields(VisualEffects))

    total = palette_count + dims_count + timings_count + effects_count
    assert palette_count >= 24, f"ColorPalette needs ≥24 fields, has {palette_count}"
    assert dims_count >= 12, f"VisualDimensions needs ≥12 fields, has {dims_count}"
    assert timings_count >= 10, f"AnimationTimings needs ≥10 fields, has {timings_count}"
    assert effects_count >= 10, f"VisualEffects needs ≥10 fields, has {effects_count}"
    assert total >= 40, f"Total parameter count must be ≥40, got {total}"


# ── 4. DEFAULT_VISUAL_CONFIG singleton ──────────────────────────────


def test_default_visual_config_singleton() -> None:
    """DEFAULT_VISUAL_CONFIG must be a usable VisualConfig instance."""
    assert isinstance(DEFAULT_VISUAL_CONFIG, VisualConfig)
    assert isinstance(DEFAULT_VISUAL_CONFIG.palette, ColorPalette)
    assert isinstance(DEFAULT_VISUAL_CONFIG.dimensions, VisualDimensions)
    assert isinstance(DEFAULT_VISUAL_CONFIG.timings, AnimationTimings)
    assert isinstance(DEFAULT_VISUAL_CONFIG.effects, VisualEffects)


def test_default_visual_config_values() -> None:
    """DEFAULT_VISUAL_CONFIG values must match the documented defaults."""
    cfg = DEFAULT_VISUAL_CONFIG
    assert cfg.dimensions.TILE_SIZE == 48
    assert Color(76, 124, 35) == cfg.palette.GRASS_PRIMARY
    assert cfg.timings.CLICK_TRANSITION == 0.13
    assert cfg.effects.SHADOW_ALPHA == 128


# ── 5. ThemeManager register / unregister / notify ──────────────────


@pytest.fixture(autouse=True)
def _reset_theme_manager():
    """Clear all listeners before each test to isolate state."""
    ThemeManager._reset()
    yield
    ThemeManager._reset()


def test_theme_manager_register_and_notify() -> None:
    """register() + notify_theme_change() invokes the listener."""
    calls: list[int] = []

    def listener() -> None:
        calls.append(1)

    ThemeManager.register(listener)
    assert ThemeManager.listener_count() == 1

    ThemeManager.notify_theme_change()
    assert calls == [1]


def test_theme_manager_register_idempotent() -> None:
    """register() with the same listener twice has no effect."""
    calls: list[int] = []

    def listener() -> None:
        calls.append(1)

    ThemeManager.register(listener)
    ThemeManager.register(listener)  # duplicate — ignored
    assert ThemeManager.listener_count() == 1

    ThemeManager.notify_theme_change()
    assert calls == [1]  # invoked only once


def test_theme_manager_unregister() -> None:
    """unregister() removes the listener."""
    calls: list[int] = []

    def listener() -> None:
        calls.append(1)

    ThemeManager.register(listener)
    ThemeManager.unregister(listener)
    assert ThemeManager.listener_count() == 0

    ThemeManager.notify_theme_change()
    assert calls == []


def test_theme_manager_unregister_unknown_safe() -> None:
    """unregister() on an unknown listener is safe (no error)."""
    def listener() -> None:
        pass

    # Unregister without ever registering — should not raise.
    ThemeManager.unregister(listener)
    assert ThemeManager.listener_count() == 0


def test_theme_manager_multiple_listeners_called_in_order() -> None:
    """Multiple listeners are invoked in registration order."""
    order: list[str] = []

    def listener_a() -> None:
        order.append("a")

    def listener_b() -> None:
        order.append("b")

    def listener_c() -> None:
        order.append("c")

    ThemeManager.register(listener_a)
    ThemeManager.register(listener_b)
    ThemeManager.register(listener_c)

    ThemeManager.notify_theme_change()
    assert order == ["a", "b", "c"]


def test_theme_manager_listener_exception_does_not_block_others(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A listener raising an exception does not block subsequent listeners."""
    calls: list[str] = []

    def good_listener_1() -> None:
        calls.append("before")

    def bad_listener() -> None:
        raise RuntimeError("boom")

    def good_listener_2() -> None:
        calls.append("after")

    ThemeManager.register(good_listener_1)
    ThemeManager.register(bad_listener)
    ThemeManager.register(good_listener_2)

    with caplog.at_level(logging.WARNING):
        ThemeManager.notify_theme_change()

    assert calls == ["before", "after"]
    assert any("boom" in record.message for record in caplog.records)


# ── 6. pygame.Color mutability trap documentation ───────────────────


def test_pygame_color_mutability_trap_documented() -> None:
    """Wave B-rev lesson 4: pygame.Color is mutable even when frozen=True.

    frozen=True prevents rebinding the field name, but does NOT prevent
    mutating the Color object's r/g/b/a in place. This test documents
    the trap so future developers don't accidentally mutate shared colors.
    """
    palette = ColorPalette()
    original_color = Color(76, 124, 35)
    assert original_color == palette.GRASS_PRIMARY

    # frozen=True prevents reassignment of the field...
    with pytest.raises(FrozenInstanceError):
        palette.GRASS_PRIMARY = Color(0, 0, 0)  # type: ignore[misc]

    # ...but pygame.Color is mutable in place. ⚠️ DO NOT DO THIS in real code.
    palette.GRASS_PRIMARY.r = 0  # type: ignore[attr-defined]
    assert palette.GRASS_PRIMARY.r == 0  # Mutation propagated!
    assert original_color != palette.GRASS_PRIMARY

    # Restore for other tests (proves the trap is real).
    palette.GRASS_PRIMARY.r = 76  # type: ignore[attr-defined]


# ── 7. Module exports (__all__) ─────────────────────────────────────


def test_module_all_exports() -> None:
    """__all__ must list all public symbols for star-import correctness."""
    from pycc2.presentation import visual_config

    expected = {
        "ColorPalette",
        "VisualDimensions",
        "AnimationTimings",
        "VisualEffects",
        "VisualConfig",
        "DEFAULT_VISUAL_CONFIG",
        "ThemeManager",
    }
    assert set(visual_config.__all__) == expected
