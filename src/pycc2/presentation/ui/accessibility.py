"""Accessibility Manager (V-12 Wave E3)

Provides color-blind mode and font scaling for PyCC2. Color-blind mode
applies a daltonism color transformation to UI and terrain layers only
(unit sprites keep faction colors for tactical readability).

Wave B-rev design safeguards:
  - **Color-blind scope**: UI + terrain only (NOT unit sprites)
    Preserves faction color readability for tactical clarity.
  - **Font 4 levels**: small/medium/large/extra-large (3 → 4 in B-rev)
    Covers 1366×768 compact to 4K vision-assist scenarios.
  - **Live preview**: Font scale changes apply immediately, no restart.

Color-blind transform matrices (Brettel et al. 1997 approach):
    Each mode applies a 3×3 matrix to RGB values to simulate how the
    scene appears to a viewer with that color vision deficiency.
    Matrices are based on Machado et al. 2009 (precomputed for severity=1.0).

Reference: docs/VISUAL_POLISH_PLAN.md V-12 章节 (v2.1, Wave B-rev)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

# Font scale factors (4 levels, Wave B-rev: 3 → 4)
FONT_SCALE_FACTORS: tuple[float, ...] = (0.85, 1.0, 1.25, 1.5)
FONT_SCALE_LABELS: tuple[str, ...] = ("小", "中", "大", "特大")
FONT_SCALE_LABELS_EN: tuple[str, ...] = ("Small", "Medium", "Large", "Extra Large")
DEFAULT_FONT_SCALE_INDEX: int = 1  # Medium

# Color-blind mode application layers (Wave B-rev: NOT "units")
APPLICABLE_LAYERS: tuple[str, ...] = ("ui", "terrain")
EXCLUDED_LAYERS: tuple[str, ...] = ("units",)  # Faction colors preserved


class ColorBlindMode(Enum):
    """Color-blind simulation mode (V-12 Wave B-rev).

    Values:
        NONE: Normal color vision (no transformation).
        PROTANOPIA: Red-blind (missing L-cone).
        DEUTERANOPIA: Green-blind (missing M-cone).
        TRITANOPIA: Blue-blind (missing S-cone).
    """

    NONE = "none"
    PROTANOPIA = "protanopia"
    DEUTERANOPIA = "deuteranopia"
    TRITANOPIA = "tritanopia"


# Daltonism transform matrices (Machado et al. 2009, severity=1.0)
# Each 3×3 matrix transforms RGB: new_rgb = matrix × old_rgb
# Source: https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html
_COLOR_BLIND_MATRICES: dict[ColorBlindMode, tuple[tuple[float, float, float], ...]] = {
    ColorBlindMode.NONE: (
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    ),
    ColorBlindMode.PROTANOPIA: (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    ColorBlindMode.DEUTERANOPIA: (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    ColorBlindMode.TRITANOPIA: (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}


@dataclass(slots=True)
class AccessibilityState:
    """Snapshot of accessibility settings (for persistence / undo).

    Attributes:
        color_blind_mode: Active color-blind simulation mode.
        font_scale_index: Index into FONT_SCALE_FACTORS (0-3).
    """

    color_blind_mode: ColorBlindMode = ColorBlindMode.NONE
    font_scale_index: int = DEFAULT_FONT_SCALE_INDEX


class AccessibilityManager:
    """Accessibility manager: color-blind mode + font scaling (V-12 Wave B-rev).

    Color-blind mode applies ONLY to UI + terrain layers (NOT unit sprites),
    preserving faction color readability for tactical clarity. Font scaling
    supports 4 levels (small/medium/large/extra-large) for 1366×768 to 4K.
    """

    APPLICABLE_LAYERS: tuple[str, ...] = APPLICABLE_LAYERS
    EXCLUDED_LAYERS: tuple[str, ...] = EXCLUDED_LAYERS
    FONT_SCALE_FACTORS: tuple[float, ...] = FONT_SCALE_FACTORS
    FONT_SCALE_LABELS: tuple[str, ...] = FONT_SCALE_LABELS

    def __init__(self) -> None:
        """Initialize the AccessibilityManager with default settings."""
        self._color_blind_mode: ColorBlindMode = ColorBlindMode.NONE
        self._font_scale_index: int = DEFAULT_FONT_SCALE_INDEX
        self._listeners: list[Callable[[], None]] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def color_blind_mode(self) -> ColorBlindMode:
        """Active color-blind simulation mode."""
        return self._color_blind_mode

    @property
    def font_scale_index(self) -> int:
        """Font scale index (0-3)."""
        return self._font_scale_index

    @property
    def font_scale_factor(self) -> float:
        """Font scale factor (0.85 / 1.0 / 1.25 / 1.5)."""
        return FONT_SCALE_FACTORS[self._font_scale_index]

    @property
    def font_scale_label(self) -> str:
        """Font scale label in Chinese (小/中/大/特大)."""
        return FONT_SCALE_LABELS[self._font_scale_index]

    @property
    def font_scale_label_en(self) -> str:
        """Font scale label in English (Small/Medium/Large/Extra Large)."""
        return FONT_SCALE_LABELS_EN[self._font_scale_index]

    @property
    def state(self) -> AccessibilityState:
        """Snapshot of current accessibility state."""
        return AccessibilityState(
            color_blind_mode=self._color_blind_mode,
            font_scale_index=self._font_scale_index,
        )

    # ------------------------------------------------------------------
    # Configuration setters
    # ------------------------------------------------------------------

    def set_color_blind_mode(self, mode: ColorBlindMode) -> None:
        """Set color-blind simulation mode.

        Notifies all registered listeners. Only UI + terrain layers should
        re-render with the transformed palette (Wave B-rev: unit sprites
        keep faction colors for tactical readability).

        Args:
            mode: Color-blind mode to activate.
        """
        if mode == self._color_blind_mode:
            return  # No-op: already on this mode
        self._color_blind_mode = mode
        self._notify_listeners()

    def set_font_scale(self, index: int) -> None:
        """Set font scale by index (0-3).

        Args:
            index: Font scale index (0=small, 1=medium, 2=large, 3=extra-large).

        Raises:
            ValueError: If index is out of range [0, len(FONT_SCALE_FACTORS)-1].
        """
        if not 0 <= index < len(FONT_SCALE_FACTORS):
            raise ValueError(
                f"Font scale index must be 0-{len(FONT_SCALE_FACTORS) - 1}, got {index}"
            )
        if index == self._font_scale_index:
            return  # No-op: already on this scale
        self._font_scale_index = index
        self._notify_listeners()

    def set_font_scale_by_factor(self, factor: float) -> None:
        """Set font scale by matching factor value (closest match).

        Args:
            factor: Target scale factor (e.g., 1.25). The closest matching
                index in FONT_SCALE_FACTORS will be selected.
        """
        closest_index = min(
            range(len(FONT_SCALE_FACTORS)),
            key=lambda i: abs(FONT_SCALE_FACTORS[i] - factor),
        )
        self.set_font_scale(closest_index)

    def restore_state(self, state: AccessibilityState) -> None:
        """Restore accessibility settings from a saved state.

        Args:
            state: Previously saved AccessibilityState snapshot.
        """
        self._color_blind_mode = state.color_blind_mode
        self._font_scale_index = max(0, min(len(FONT_SCALE_FACTORS) - 1, state.font_scale_index))
        self._notify_listeners()

    def reset(self) -> None:
        """Reset to default settings (no color-blind, medium font)."""
        self._color_blind_mode = ColorBlindMode.NONE
        self._font_scale_index = DEFAULT_FONT_SCALE_INDEX
        self._notify_listeners()

    # ------------------------------------------------------------------
    # Color transformation
    # ------------------------------------------------------------------

    def transform_color(self, rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        """Apply color-blind transformation to an RGB color.

        Uses the Machado et al. 2009 matrix for the active color-blind mode.
        For NONE mode, returns the input color unchanged.

        Args:
            rgb: Input RGB color (each channel 0-255).

        Returns:
            Transformed RGB color (each channel clamped to 0-255).
        """
        if self._color_blind_mode == ColorBlindMode.NONE:
            return rgb
        matrix = _COLOR_BLIND_MATRICES[self._color_blind_mode]
        r, g, b = rgb
        new_r = matrix[0][0] * r + matrix[0][1] * g + matrix[0][2] * b
        new_g = matrix[1][0] * r + matrix[1][1] * g + matrix[1][2] * b
        new_b = matrix[2][0] * r + matrix[2][1] * g + matrix[2][2] * b
        return (
            max(0, min(255, int(round(new_r)))),
            max(0, min(255, int(round(new_g)))),
            max(0, min(255, int(round(new_b)))),
        )

    def transform_color_batch(
        self, colors: list[tuple[int, int, int]]
    ) -> list[tuple[int, int, int]]:
        """Apply color-blind transformation to a batch of RGB colors.

        Args:
            colors: List of input RGB colors.

        Returns:
            List of transformed RGB colors (same order as input).
        """
        return [self.transform_color(c) for c in colors]

    def is_layer_affected(self, layer: str) -> bool:
        """Check if a rendering layer is affected by color-blind mode.

        Wave B-rev: UI and terrain layers are affected; unit sprites are NOT.

        Args:
            layer: Layer name ("ui", "terrain", "units", etc.).

        Returns:
            True if the layer should have color-blind transformation applied.
        """
        return layer in APPLICABLE_LAYERS

    # ------------------------------------------------------------------
    # Listener management
    # ------------------------------------------------------------------

    def register_listener(self, listener: Callable[[], None]) -> None:
        """Register a listener to be notified on setting changes.

        Args:
            listener: Callable that takes no arguments. Idempotent.
        """
        if listener not in self._listeners:
            self._listeners.append(listener)

    def unregister_listener(self, listener: Callable[[], None]) -> None:
        """Unregister a previously registered listener.

        Safe to call even if the listener was never registered.
        """
        try:
            self._listeners.remove(listener)
        except ValueError:
            pass

    def listener_count(self) -> int:
        """Return the number of registered listeners."""
        return len(self._listeners)

    def _notify_listeners(self) -> None:
        """Notify all registered listeners of a setting change."""
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:  # noqa: BLE001
                # Listener errors are swallowed to avoid blocking other listeners
                import logging

                logging.getLogger(__name__).warning(
                    "Accessibility listener %r raised an exception", listener
                )


__all__ = [
    "FONT_SCALE_FACTORS",
    "FONT_SCALE_LABELS",
    "FONT_SCALE_LABELS_EN",
    "DEFAULT_FONT_SCALE_INDEX",
    "APPLICABLE_LAYERS",
    "EXCLUDED_LAYERS",
    "ColorBlindMode",
    "AccessibilityState",
    "AccessibilityManager",
]
