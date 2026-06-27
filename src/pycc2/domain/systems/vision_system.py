"""Cone vision domain system (D9)."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class ConeVisionSystem:
    """Conical (cone) vision system instead of circular.

    Default vision cone: 120 degree arc
    Different stances affect cone angle:
    - Standing: 120
    - Crouching: 90
    - Prone: 60
    """

    DEFAULT_CONE_ANGLE: float = 120.0  # degrees
    STANCE_ANGLES = {
        "standing": 120.0,
        "crouching": 90.0,
        "prone": 60.0,
    }

    def is_in_cone(
        self,
        observer_pos: tuple[float, float],
        observer_facing: float,  # degrees
        target_pos: tuple[float, float],
        stance: str = "standing",
        max_range: float = 15.0,
    ) -> bool:
        """Check if target is within vision cone."""
        dx = target_pos[0] - observer_pos[0]
        dy = target_pos[1] - observer_pos[1]
        distance = (dx * dx + dy * dy) ** 0.5

        if distance > max_range:
            return False

        angle_to_target = math.degrees(math.atan2(dy, dx))
        relative_angle = abs(angle_to_target - observer_facing)

        if relative_angle > 180:
            relative_angle = 360 - relative_angle

        cone_angle = self.STANCE_ANGLES.get(stance, self.DEFAULT_CONE_ANGLE)
        half_cone = cone_angle / 2.0

        return relative_angle <= half_cone

    def get_cone_angle(self, stance: str) -> float:
        """Get vision cone angle for stance."""
        return self.STANCE_ANGLES.get(stance, self.DEFAULT_CONE_ANGLE)
