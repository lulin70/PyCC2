"""Trench digging AI domain system (D10)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TrenchDiggingAI:
    """
    Extended trench digging AI behavior.

    Units automatically dig after stationary 3 turns undetected.
    Progress bar over 3 turns.
    Permanent cover bonus upon completion.
    """

    DIG_DURATION_TURNS: int = 3
    DETECTION_RESET_TIME: float = 5.0  # seconds

    _dig_progress: dict[int, float] = field(init=False)
    _stationary_time: dict[int, float] = field(init=False)

    def __post_init__(self):
        self._dig_progress = {}
        self._stationary_time = {}

    def update_unit(
        self,
        unit_id: int,
        is_stationary: bool,
        is_detected: bool,
        dt: float,
    ) -> str | None:
        """
        Update digging progress for unit.

        Returns:
            'digging', 'completed', or None
        """
        if not is_stationary or is_detected:
            self._stationary_time[unit_id] = 0.0
            self._dig_progress[unit_id] = 0.0
            return None

        if unit_id not in self._stationary_time:
            self._stationary_time[unit_id] = 0.0
            self._dig_progress[unit_id] = 0.0

        self._stationary_time[unit_id] += dt

        if self._stationary_time[unit_id] >= 2.0:  # 2 sec stationary
            turn_duration = 5.0  # seconds per turn
            progress_per_sec = 1.0 / (self.DIG_DURATION_TURNS * turn_duration)
            self._dig_progress[unit_id] += dt * progress_per_sec

            if self._dig_progress[unit_id] >= 1.0:
                return "completed"
            return "digging"

        return None

    def get_dig_progress(self, unit_id: int) -> float:
        """Get dig progress (0.0 to 1.0)."""
        return self._dig_progress.get(unit_id, 0.0)
