from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

# V-05 Wave D1: Base design resolution for responsive layout scaling.
# 1280×720 is the canonical "1.0x" baseline; wider screens scale up.
BASE_DESIGN_WIDTH: int = 1280
BASE_DESIGN_HEIGHT: int = 720


def compute_scale_factor(
    screen_width: int,
    base_width: int = BASE_DESIGN_WIDTH,
    dpi_scale: float = 1.0,
) -> float:
    """Compute responsive layout scale factor (V-05 Wave D1).

    Returns the maximum of:
    - ``dpi_scale`` (HiDPI/Retina compensation, e.g. 2.0 on macOS Retina)
    - ``screen_width / base_width`` ( widescreen compensation, e.g. 1.5 at 1920px )

    This is the standalone helper form of ``DisplayConfig.ui_scale`` /
    ``DisplayConfig.scale_factor``. Use this when you need the scale factor
    without constructing a full ``DisplayConfig`` instance (e.g. in tests
    or in presentation-layer components that receive screen_width only).

    Args:
        screen_width: Actual screen / window width in pixels.
        base_width: Design baseline width (default 1280 per V-05 spec).
        dpi_scale: HiDPI backing scale factor (default 1.0).

    Returns:
        Scale factor ≥ 1.0 (never shrinks below 1.0 unless dpi_scale < 1.0,
        which only happens on misconfigured systems).

    Examples:
        >>> compute_scale_factor(1280)
        1.0
        >>> compute_scale_factor(1920)
        1.5
        >>> compute_scale_factor(1280, dpi_scale=2.0)
        2.0
        >>> compute_scale_factor(2560)
        2.0

    """
    if base_width <= 0:
        raise ValueError(f"base_width must be > 0, got {base_width}")
    if screen_width < 0:
        raise ValueError(f"screen_width must be >= 0, got {screen_width}")
    if dpi_scale < 0:
        raise ValueError(f"dpi_scale must be >= 0, got {dpi_scale}")
    width_scale = screen_width / base_width if screen_width > 0 else 1.0
    return max(dpi_scale, width_scale)


class QualityPreset(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    ULTRA = auto()


@dataclass(slots=True)
class DisplayConfig:
    window_width: int = 1440
    window_height: int = 900
    base_tile_size: int = 48
    sprite_scale: float = 1.0
    dpi_scale: float = 1.0
    is_retina: bool = False
    default_zoom: float = 1.0

    @property
    def effective_tile_size(self) -> int:
        return int(self.base_tile_size * self.sprite_scale)

    @property
    def effective_sprite_size(self) -> int:
        return int(self.base_tile_size * 0.875 * self.sprite_scale)

    @property
    def ui_scale(self) -> float:
        return max(self.dpi_scale, self.window_width / 1280)

    @property
    def scale_factor(self) -> float:
        """Responsive layout scale factor (V-05 Wave D1 alias for ui_scale).

        Returns the same value as ``ui_scale``. This alias exists for API
        clarity: ``scale_factor`` matches the V-05 design doc naming, while
        ``ui_scale`` is the legacy name preserved for backward compatibility
        with the 30+ existing call sites (hud.py / unit_panel.py / minimap.py
        / render_pipeline.py / unit_overlay_rendering_mixin.py /
        game_loop_assembler.py).

        Callers writing new code should prefer ``scale_factor``. Existing
        code does NOT need to migrate — both properties return identical
        values by design.
        """
        return self.ui_scale

    @property
    def font_size_small(self) -> int:
        return max(12, int(14 * self.ui_scale))

    @property
    def font_size_normal(self) -> int:
        return max(14, int(18 * self.ui_scale))

    @property
    def font_size_large(self) -> int:
        return max(18, int(24 * self.ui_scale))

    @property
    def font_size_title(self) -> int:
        return max(22, int(30 * self.ui_scale))

    def compute_default_zoom(self, map_width_tiles: int, map_height_tiles: int) -> float:
        map_px_w = map_width_tiles * self.base_tile_size
        map_px_h = map_height_tiles * self.base_tile_size
        zoom_x = self.window_width / map_px_w
        zoom_y = self.window_height / map_px_h
        return min(zoom_x, zoom_y, 1.5)

    @classmethod
    def from_screen(
        cls, screen_width: int, screen_height: int, dpi_scale: float = 1.0, is_retina: bool = False
    ) -> DisplayConfig:
        if screen_width >= 1800:
            tile_size = 64
        elif screen_width >= 1300:
            tile_size = 48
        else:
            tile_size = 32
        w = min(int(screen_width * 0.9), 1920)
        h = min(int(screen_height * 0.9), 1080)
        sprite_scale = 2.0 if is_retina else 1.0
        return cls(
            window_width=w,
            window_height=h,
            base_tile_size=tile_size,
            sprite_scale=sprite_scale,
            dpi_scale=dpi_scale,
            is_retina=is_retina,
        )

    @classmethod
    def from_preset(
        cls, preset: QualityPreset, dpi_scale: float = 1.0, is_retina: bool = False
    ) -> DisplayConfig:
        sizes = {
            QualityPreset.LOW: (800, 600, 24),
            QualityPreset.MEDIUM: (1280, 720, 32),
            QualityPreset.HIGH: (1440, 900, 48),
            QualityPreset.ULTRA: (1920, 1080, 64),
        }
        w, h, ts = sizes[preset]
        return cls(
            window_width=w,
            window_height=h,
            base_tile_size=ts,
            sprite_scale=2.0 if is_retina else 1.0,
            dpi_scale=dpi_scale,
            is_retina=is_retina,
        )
