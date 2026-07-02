"""3D positional stereo sound system (D6)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StereoSoundSystem:
    """3D positional stereo sound system.

    Pan audio left/right based on source position.
    Volume attenuation with distance.
    """

    MAX_DISTANCE: float = 50.0  # tiles
    REFERENCE_DISTANCE: float = 10.0

    def calculate_stereo_pan(
        self,
        listener_pos: tuple[float, float],
        source_pos: tuple[float, float],
    ) -> float:
        """Calculate stereo pan value (-1.0 left to 1.0 right)."""
        dx = source_pos[0] - listener_pos[0]
        distance = (dx * dx + (source_pos[1] - listener_pos[1]) ** 2) ** 0.5

        if distance < 0.01:
            return 0.0

        normalized = dx / max(distance, 1.0)
        pan = max(-1.0, min(1.0, normalized))

        return pan

    def calculate_volume(
        self,
        listener_pos: tuple[float, float],
        source_pos: tuple[float, float],
        base_volume: float = 1.0,
    ) -> float:
        """Calculate volume with distance attenuation."""
        dx = source_pos[0] - listener_pos[0]
        dy = source_pos[1] - listener_pos[1]
        distance = (dx * dx + dy * dy) ** 0.5

        if distance >= self.MAX_DISTANCE:
            return 0.0

        attenuation = 1.0 - (distance / self.MAX_DISTANCE)
        return base_volume * attenuation
