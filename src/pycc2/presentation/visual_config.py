"""Visual configuration central module — single source of truth for visual params.

PyCC2 v0.9.0 V-01 (Wave C3): Extracted from scattered hardcoded values across
9 renderers. All visual params (colors / sizes / animation durations / alpha)
should reference this module instead of local magic numbers.

⚠️ IMPORTANT — pygame.Color mutability trap (Wave B-rev lesson 4):
    While ``ColorPalette`` is ``frozen=True`` (prevents attribute rebinding),
    ``pygame.Color`` objects themselves are MUTABLE (``Color.r/g/b/a`` can be
    modified in place). Callers MUST treat all Color fields as READ-ONLY.
    Mutating a shared Color instance will affect all references across the
    codebase.

Theme hot-reload (V-10 Morandi skin):
    When the user toggles the Morandi skin, call
    ``ThemeManager.notify_theme_change()`` to broadcast to all registered
    renderers so they re-read ``DEFAULT_VISUAL_CONFIG`` and invalidate any
    cached sprites / surfaces.

Reference: docs/VISUAL_POLISH_PLAN.md V-01 章节 (v2.1, Wave B-rev)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from pygame import Color

# ──────────────────────────────────────────────────────────────────────
# 1. ColorPalette — centralized color palette (CC2-faithful, ≥24 colors)
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ColorPalette:
    """Centralized color palette (CC2-faithful base; Morandi skin optional).

    ⚠️ Color fields are internally mutable (pygame.Color). Callers must
    NOT modify ``.r/.g/.b/.a`` of any Color instance retrieved from this
    palette. Treat all fields as READ-ONLY.

    Total fields: 24 (terrain 10 + faction 8 + UI 6)

    Note: ``default_factory`` is used for every Color field because
    ``pygame.Color`` is mutable; dataclass forbids mutable defaults.
    """

    # --- Terrain colors (10) ---
    GRASS_PRIMARY: Color = field(default_factory=lambda: Color(76, 124, 35))  # #4C7C23
    GRASS_HIGHLIGHT: Color = field(default_factory=lambda: Color(90, 142, 43))  # #5A8E2B
    GRASS_SHADOW: Color = field(default_factory=lambda: Color(58, 100, 24))  # #3A6418
    DIRT_PRIMARY: Color = field(default_factory=lambda: Color(101, 67, 33))  # #654321
    SAND_PRIMARY: Color = field(default_factory=lambda: Color(194, 178, 128))  # #C2B280
    SNOW_PRIMARY: Color = field(default_factory=lambda: Color(240, 240, 245))  # #F0F0F5
    WATER_PRIMARY: Color = field(default_factory=lambda: Color(60, 100, 140))  # #3C648C
    FOREST_PRIMARY: Color = field(default_factory=lambda: Color(34, 80, 26))  # #22501A
    URBAN_PRIMARY: Color = field(default_factory=lambda: Color(120, 120, 125))  # #78787D
    ROAD_PRIMARY: Color = field(default_factory=lambda: Color(140, 130, 110))  # #8C826E

    # --- Faction colors (8) ---
    ALLIES_PRIMARY: Color = field(
        default_factory=lambda: Color(76, 124, 35)
    )  # #4C7C23 (olive drab)
    AMERICAN_PRIMARY: Color = field(default_factory=lambda: Color(60, 110, 30))  # #3C6E1E
    BRITISH_PRIMARY: Color = field(default_factory=lambda: Color(80, 100, 40))  # #506428
    POLISH_PRIMARY: Color = field(default_factory=lambda: Color(120, 80, 30))  # #78501E
    AXIS_PRIMARY: Color = field(default_factory=lambda: Color(120, 100, 60))  # #78643C (field gray)
    GERMAN_PRIMARY: Color = field(default_factory=lambda: Color(100, 90, 50))  # #645A32
    HIGHLIGHT_ALLIES: Color = field(default_factory=lambda: Color(100, 160, 60))  # selection tint
    HIGHLIGHT_AXIS: Color = field(default_factory=lambda: Color(160, 120, 80))  # selection tint

    # --- UI colors (6) ---
    UI_PANEL: Color = field(default_factory=lambda: Color(40, 40, 50))  # #282832
    UI_BORDER: Color = field(default_factory=lambda: Color(80, 80, 90))  # #50505A
    UI_TEXT: Color = field(default_factory=lambda: Color(220, 220, 220))  # #DCDCDC
    UI_HIGHLIGHT: Color = field(default_factory=lambda: Color(255, 200, 100))  # #FFC864
    UI_VICTORY: Color = field(default_factory=lambda: Color(100, 200, 100))  # #64C864
    UI_DEFEAT: Color = field(default_factory=lambda: Color(200, 80, 80))  # #C85050


# ──────────────────────────────────────────────────────────────────────
# 2. VisualDimensions — visual size / dimension constants (≥12 fields)
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class VisualDimensions:
    """Visual size / dimension constants.

    Total fields: 12 (tile 1 + sprite 1 + unit sizes 7 + panels 3)
    """

    # --- Tile / sprite base ---
    TILE_SIZE: int = 48  # P0-4: 32 → 48 in v0.7.x
    SPRITE_SIZE: int = 48  # sprite canvas size

    # --- Unit sprite sizes (per unit type) ---
    UNIT_SIZE_INFANTRY: tuple[int, int] = (18, 22)
    UNIT_SIZE_TANK_MEDIUM: tuple[int, int] = (36, 36)
    UNIT_SIZE_TANK_HEAVY: tuple[int, int] = (42, 42)
    UNIT_SIZE_HALFTRACK: tuple[int, int] = (32, 28)
    UNIT_SIZE_JEEP: tuple[int, int] = (28, 22)
    UNIT_SIZE_AT_GUN: tuple[int, int] = (30, 20)
    UNIT_SIZE_MORTAR: tuple[int, int] = (24, 20)

    # --- Panels ---
    PANEL_WIDTH_BOTTOM: int = 1280
    PANEL_HEIGHT_BOTTOM: int = 200
    MINIMAP_SIZE: tuple[int, int] = (200, 200)


# ──────────────────────────────────────────────────────────────────────
# 3. AnimationTimings — animation duration constants in seconds (≥10 fields)
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class AnimationTimings:
    """Animation duration constants (seconds) and easing curve names.

    Wave B-rev adjustments:
        - CLICK_TRANSITION: 0.10 → 0.13 (Wave B P1: 120-150ms target)
        - HOVER_TRANSITION: 0.20 (unchanged)
        - EASING_CURVE: unified to ease_out_cubic (Wave B P1)

    Total fields: 10
    """

    EXPLOSION_DURATION: float = 0.3
    MUZZLE_FLASH_DURATION: float = 0.05
    SMOKE_GRENADE_DURATION: float = 45.0  # in-game seconds
    BLOOD_HIT_DURATION: float = 0.4
    DEATH_ANIMATION_DURATION: float = 0.6
    HOVER_TRANSITION: float = 0.2  # 200ms
    CLICK_TRANSITION: float = 0.13  # 130ms (Wave B: 100ms→120-150ms)
    SELECTION_PULSE_PERIOD: float = 1.0
    ERROR_FLASH_DURATION: float = 0.3
    EASING_CURVE: str = "ease_out_cubic"  # Wave B: unified easing


# ──────────────────────────────────────────────────────────────────────
# 4. VisualEffects — visual effect parameters (≥10 fields)
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class VisualEffects:
    """Visual effect parameters (alpha / particle counts / line thickness).

    Total fields: 11
    """

    # --- Shadows ---
    SHADOW_ALPHA: int = 128
    SHADOW_OFFSET: tuple[int, int] = (4, 4)  # (+x, +y) — SE direction

    # --- Particle counts ---
    PARTICLE_COUNT_EXPLOSION: int = 40
    PARTICLE_COUNT_BLOOD: int = 8
    PARTICLE_COUNT_MUZZLE: int = 3

    # --- Lines / outlines ---
    LINE_THICKNESS_DEFAULT: int = 1
    LINE_THICKNESS_HIGHLIGHT: int = 2

    # --- Overlays ---
    SELECTION_BOX_ALPHA: int = 150
    HIGHLIGHT_GLOW_RADIUS: int = 6
    FOG_ALPHA: int = 100
    NIGHT_OVERLAY_ALPHA: int = 80


# ──────────────────────────────────────────────────────────────────────
# 5. VisualConfig — top-level container (≥40 params total)
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class VisualConfig:
    """Single source of truth for all visual parameters.

    Total parameter count: 24 + 12 + 10 + 11 = 57 (exceeds V-01 ≥40 requirement).

    Renderers should read from ``DEFAULT_VISUAL_CONFIG`` rather than
    constructing their own ``VisualConfig`` instance, so that theme
    hot-reload (V-10) propagates correctly.
    """

    palette: ColorPalette = field(default_factory=ColorPalette)
    dimensions: VisualDimensions = field(default_factory=VisualDimensions)
    timings: AnimationTimings = field(default_factory=AnimationTimings)
    effects: VisualEffects = field(default_factory=VisualEffects)


# Default singleton instance — renderers reference this.
DEFAULT_VISUAL_CONFIG: VisualConfig = VisualConfig()


# ──────────────────────────────────────────────────────────────────────
# 6. ThemeManager — theme hot-reload broadcaster (V-10 Morandi skin)
# ──────────────────────────────────────────────────────────────────────


class ThemeManager:
    """Theme hot-reload manager for V-10 Morandi skin switching.

    Notifies all registered renderers to re-read ``DEFAULT_VISUAL_CONFIG``
    and invalidate sprite caches when the theme changes.

    Usage::

        # Renderer registration (during __init__)
        ThemeManager.register(self._on_theme_change)

        # Theme switch (V-10 palette swap, then broadcast)
        DEFAULT_VISUAL_CONFIG = VisualConfig(palette=MORANDI_PALETTE, ...)
        ThemeManager.notify_theme_change()

    Wave B-rev P1-12 note: All renderers that maintain sprite / surface
    caches MUST register a listener so V-10 skin switch invalidates
    stale caches. Failing to register will leave stale sprites on screen.
    """

    _listeners: list[Callable[[], None]] = []

    @classmethod
    def register(cls, listener: Callable[[], None]) -> None:
        """Register a theme change listener.

        Args:
            listener: A callable that takes no arguments. Will be invoked
                on ``notify_theme_change()``. Idempotent — registering
                the same listener twice has no effect.
        """
        if listener not in cls._listeners:
            cls._listeners.append(listener)

    @classmethod
    def unregister(cls, listener: Callable[[], None]) -> None:
        """Unregister a previously registered listener.

        Safe to call even if the listener was never registered.
        """
        try:
            cls._listeners.remove(listener)
        except ValueError:
            pass

    @classmethod
    def notify_theme_change(cls) -> None:
        """Broadcast theme change to all registered listeners.

        Listeners are invoked synchronously in registration order.
        Exceptions in one listener do not prevent subsequent listeners
        from being notified (errors are logged but swallowed).
        """
        import logging

        logger = logging.getLogger(__name__)
        for listener in list(cls._listeners):
            try:
                listener()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Theme change listener %r raised: %s", listener, exc)

    @classmethod
    def listener_count(cls) -> int:
        """Return the number of registered listeners (for testing / debug)."""
        return len(cls._listeners)

    @classmethod
    def _reset(cls) -> None:
        """Clear all listeners. Intended for unit test isolation only."""
        cls._listeners.clear()


__all__ = [
    "ColorPalette",
    "VisualDimensions",
    "AnimationTimings",
    "VisualEffects",
    "VisualConfig",
    "DEFAULT_VISUAL_CONFIG",
    "ThemeManager",
]
