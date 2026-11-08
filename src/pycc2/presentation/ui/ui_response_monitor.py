"""UI Response Performance Monitor - Tracks UI interaction latency.

Ensures all UI interactions complete within 50ms target:
- Button clicks
- Menu openings
- Selection updates
- Building placements
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class UIPerformanceMetric:
    """UI performance measurement."""

    interaction_type: str
    duration_ms: float
    timestamp: float


class UIResponseMonitor:
    """Monitors UI response times and warns if exceeding threshold."""

    TARGET_MS: ClassVar[float] = 50.0  # 50ms target for UI responses
    HISTORY_SIZE: ClassVar[int] = 100  # Track last 100 interactions

    def __init__(self) -> None:
        """Initialize UI response monitor."""
        self._metrics: deque[UIPerformanceMetric] = deque(maxlen=self.HISTORY_SIZE)
        self._current_interaction: str | None = None
        self._start_time: float = 0.0

    def start_interaction(self, interaction_type: str) -> None:
        """Start timing a UI interaction.

        Args:
            interaction_type: Type of interaction (e.g., "button_click", "menu_open")
        """
        self._current_interaction = interaction_type
        self._start_time = time.perf_counter()

    def end_interaction(self) -> float:
        """End timing current interaction.

        Returns:
            Duration in milliseconds
        """
        if self._current_interaction is None:
            return 0.0

        duration_s = time.perf_counter() - self._start_time
        duration_ms = duration_s * 1000

        metric = UIPerformanceMetric(
            interaction_type=self._current_interaction,
            duration_ms=duration_ms,
            timestamp=time.time(),
        )
        self._metrics.append(metric)

        # Warn if exceeding target
        if duration_ms > self.TARGET_MS:
            print(
                f"⚠️ UI Performance Warning: {self._current_interaction} took {duration_ms:.2f}ms (target: {self.TARGET_MS}ms)"
            )

        self._current_interaction = None
        return duration_ms

    def get_average_response_time(self) -> float:
        """Get average UI response time across recent interactions.

        Returns:
            Average duration in milliseconds
        """
        if not self._metrics:
            return 0.0
        return sum(m.duration_ms for m in self._metrics) / len(self._metrics)

    def get_slowest_interactions(self, count: int = 5) -> list[UIPerformanceMetric]:
        """Get slowest UI interactions.

        Args:
            count: Number of slowest interactions to return

        Returns:
            List of slowest interactions
        """
        sorted_metrics = sorted(self._metrics, key=lambda m: m.duration_ms, reverse=True)
        return sorted_metrics[:count]

    def get_compliance_rate(self) -> float:
        """Get percentage of interactions meeting 50ms target.

        Returns:
            Compliance rate as percentage (0-100)
        """
        if not self._metrics:
            return 100.0

        compliant = sum(1 for m in self._metrics if m.duration_ms <= self.TARGET_MS)
        return (compliant / len(self._metrics)) * 100


class UIResponseOptimizer:
    """Provides tools for optimizing UI response times."""

    @staticmethod
    def debounce(func, delay_ms: float = 100):
        """Debounce decorator for UI functions.

        Args:
            func: Function to debounce
            delay_ms: Delay in milliseconds

        Returns:
            Debounced function
        """
        last_call = [0.0]

        def wrapper(*args, **kwargs):
            now = time.perf_counter()
            delay_s = delay_ms / 1000
            if now - last_call[0] >= delay_s:
                last_call[0] = now
                return func(*args, **kwargs)
            return None

        return wrapper

    @staticmethod
    def throttle(func, interval_ms: float = 16.67):
        """Throttle decorator for UI functions (60fps = 16.67ms).

        Args:
            func: Function to throttle
            interval_ms: Minimum interval between calls in milliseconds

        Returns:
            Throttled function
        """
        last_call = [0.0]

        def wrapper(*args, **kwargs):
            now = time.perf_counter()
            interval_s = interval_ms / 1000
            if now - last_call[0] >= interval_s:
                last_call[0] = now
                return func(*args, **kwargs)
            return None

        return wrapper
