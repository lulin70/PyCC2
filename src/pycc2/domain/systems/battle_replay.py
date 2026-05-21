"""
Battle Replay — Record and replay battles frame-by-frame.

A "beyond CC2" feature: the original Close Combat 2 had no replay
capability.  This module records unit states and combat events at
regular intervals so that an entire battle can be played back with
pause, step, speed control, and seek.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

# ========================================================================
# Replay event types
# ========================================================================

class ReplayEventType(Enum):
    SHOT_FIRED = auto()
    HIT = auto()
    KILL = auto()
    MORALE_CHANGE = auto()
    SUPPRESSED = auto()
    RALLIED = auto()
    SURRENDERED = auto()
    JAM = auto()
    UNJAM = auto()
    SMOKE_DEPLOYED = auto()
    ARTILLERY = auto()
    MELEE = auto()


# ========================================================================
# Data classes
# ========================================================================

@dataclass(frozen=True, slots=True)
class UnitSnapshot:
    unit_id: str
    position: tuple[int, int]
    health: float
    state: str
    ammo: int
    morale: int
    suppression: float


@dataclass(frozen=True, slots=True)
class ReplayEvent:
    tick: int
    event_type: ReplayEventType
    source_id: str
    target_id: str | None
    position: tuple[int, int]
    detail: str


@dataclass(frozen=True, slots=True)
class ReplayFrame:
    tick: int
    unit_states: dict[str, UnitSnapshot]
    events: tuple[ReplayEvent, ...]


@dataclass
class ReplayData:
    map_id: str
    scenario_name: str
    total_ticks: int
    frames: list[ReplayFrame] = field(default_factory=list)
    result: str = 'draw'   # 'victory' / 'defeat' / 'draw'
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'map_id': self.map_id,
            'scenario_name': self.scenario_name,
            'total_ticks': self.total_ticks,
            'result': self.result,
            'metadata': self.metadata,
            'frame_count': len(self.frames),
        }


# ========================================================================
# ReplayRecorder
# ========================================================================

# Record one frame every 6 ticks (~10 fps at 60 tps)
_FRAME_INTERVAL: int = 6


class ReplayRecorder:
    """Records battle state into ReplayFrame objects."""

    def __init__(self, frame_interval: int = _FRAME_INTERVAL) -> None:
        self._frame_interval = frame_interval
        self._recording = False
        self._frames: list[ReplayFrame] = []
        self._pending_events: list[ReplayEvent] = []
        self._last_tick: int = -1

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start_recording(self) -> None:
        self._recording = True
        self._frames.clear()
        self._pending_events.clear()
        self._last_tick = -1

    def record_event(self, event: ReplayEvent) -> None:
        """Buffer a combat event for the current or next frame."""
        if not self._recording:
            return
        self._pending_events.append(event)

    def capture_frame(
        self,
        tick: int,
        units: dict[str, UnitSnapshot],
    ) -> ReplayFrame | None:
        """Capture a frame if the interval has elapsed.

        Call this every tick.  Returns a ReplayFrame when one is
        captured, or ``None`` otherwise.
        """
        if not self._recording:
            return None

        # Always flush pending events even if not a frame tick
        if tick % self._frame_interval != 0 and tick != 0:
            # Accumulate events for the next frame
            return None

        frame = ReplayFrame(
            tick=tick,
            unit_states=dict(units),
            events=tuple(self._pending_events),
        )
        self._frames.append(frame)
        self._pending_events.clear()
        self._last_tick = tick
        return frame

    def stop_recording(
        self,
        map_id: str = '',
        scenario_name: str = '',
        result: str = 'draw',
        metadata: dict[str, Any] | None = None,
    ) -> ReplayData:
        """Finalize recording and return the complete replay data."""
        self._recording = False
        return ReplayData(
            map_id=map_id,
            scenario_name=scenario_name,
            total_ticks=max(self._last_tick, 0),
            frames=list(self._frames),
            result=result,
            metadata=metadata or {},
        )


# ========================================================================
# ReplayPlayer
# ========================================================================

class ReplayPlayer:
    """Plays back a recorded battle with VCR-style controls."""

    _SPEEDS: tuple[float, ...] = (0.5, 1.0, 2.0, 4.0)

    def __init__(self) -> None:
        self._data: ReplayData | None = None
        self._frame_index: int = 0
        self._playing: bool = False
        self._speed: float = 1.0
        # Tick-to-frame-index lookup for fast seeking
        self._tick_to_index: dict[int, int] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, data: ReplayData) -> None:
        self._data = data
        self._frame_index = 0
        self._playing = False
        self._speed = 1.0
        self._tick_to_index = {
            frame.tick: idx for idx, frame in enumerate(data.frames)
        }

    # ------------------------------------------------------------------
    # Playback controls
    # ------------------------------------------------------------------

    def play(self) -> None:
        if self._data is None:
            return
        self._playing = True

    def pause(self) -> None:
        self._playing = False

    def step_forward(self) -> ReplayFrame | None:
        """Advance one frame. Returns the new frame or None at end."""
        if self._data is None:
            return None
        self._playing = False
        if self._frame_index < len(self._data.frames) - 1:
            self._frame_index += 1
        return self.get_current_frame()

    def step_backward(self) -> ReplayFrame | None:
        """Go back one frame. Returns the new frame or None at start."""
        if self._data is None:
            return None
        self._playing = False
        if self._frame_index > 0:
            self._frame_index -= 1
        return self.get_current_frame()

    def set_speed(self, speed: float) -> None:
        """Set playback speed. Clamps to nearest supported value."""
        if speed in self._SPEEDS:
            self._speed = speed
        else:
            # Pick closest supported speed
            self._speed = min(self._SPEEDS, key=lambda s: abs(s - speed))

    def seek_to(self, tick: int) -> ReplayFrame | None:
        """Jump to the frame closest to the given tick."""
        if self._data is None:
            return None

        # Exact match
        if tick in self._tick_to_index:
            self._frame_index = self._tick_to_index[tick]
            return self.get_current_frame()

        # Find closest frame by tick
        best_idx = 0
        best_diff = abs(self._data.frames[0].tick - tick) if self._data.frames else 0
        for idx, frame in enumerate(self._data.frames):
            diff = abs(frame.tick - tick)
            if diff < best_diff:
                best_diff = diff
                best_idx = idx

        self._frame_index = best_idx
        return self.get_current_frame()

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def current_tick(self) -> int:
        frame = self.get_current_frame()
        return frame.tick if frame else 0

    @property
    def total_frames(self) -> int:
        if self._data is None:
            return 0
        return len(self._data.frames)

    def get_current_frame(self) -> ReplayFrame | None:
        if self._data is None or not self._data.frames:
            return None
        if 0 <= self._frame_index < len(self._data.frames):
            return self._data.frames[self._frame_index]
        return None

    def advance(self, delta_ticks: int) -> ReplayFrame | None:
        """Advance playback by *delta_ticks* simulation ticks.

        Accounts for current speed.  Called once per real-time frame
        by the game loop.
        """
        if not self._playing or self._data is None:
            return self.get_current_frame()

        # How many replay frames to skip (1 frame = _FRAME_INTERVAL ticks)
        frames_to_advance = max(1, int(self._speed * delta_ticks / _FRAME_INTERVAL))
        self._frame_index = min(
            self._frame_index + frames_to_advance,
            len(self._data.frames) - 1,
        )

        # Auto-pause at end
        if self._frame_index >= len(self._data.frames) - 1:
            self._playing = False

        return self.get_current_frame()
