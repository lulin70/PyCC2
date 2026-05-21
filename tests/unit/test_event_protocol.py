from __future__ import annotations

import time

from pycc2.services.event_protocol import (
    DebugCommand,
    ErrorOccurred,
    FogOfWarUpdated,
    GamePaused,
    GameResumed,
    MoraleChanged,
    ProjectileHit,
    ProjectileSpawned,
    SaveCompleted,
    SaveLoaded,
    SaveRequested,
    TurnEnded,
    TurnStarted,
    UnitAttacked,
    UnitKilled,
    UnitMoved,
    VictoryConditionMet,
    WeaponFired,
    WeaponJammed,
    WeaponReloaded,
)

ALL_EVENTS = [
    UnitMoved,
    UnitAttacked,
    UnitKilled,
    MoraleChanged,
    WeaponFired,
    WeaponReloaded,
    WeaponJammed,
    ProjectileSpawned,
    ProjectileHit,
    FogOfWarUpdated,
    TurnStarted,
    TurnEnded,
    GamePaused,
    GameResumed,
    SaveRequested,
    SaveCompleted,
    SaveLoaded,
    ErrorOccurred,
    VictoryConditionMet,
    DebugCommand,
]


class TestEventProtocolExistence:
    def test_all_18_events_defined(self):
        assert len(ALL_EVENTS) == 20


class TestEventConstruction:
    def test_unit_moved_required_fields(self):
        event: UnitMoved = {
            "unit_id": "u1",
            "from_tile": (0, 0),
            "to_tile": (1, 1),
        }
        assert event["unit_id"] == "u1"
        assert event["from_tile"] == (0, 0)
        assert event["to_tile"] == (1, 1)

    def test_unit_attacked_with_optional_kill_shot(self):
        event: UnitAttacked = {
            "attacker_id": "a1",
            "target_id": "t1",
            "is_hit": True,
            "damage": 25.5,
            "kill_shot": True,
        }
        assert event["kill_shot"] is True

    def test_unit_killed_without_killer(self):
        event: UnitKilled = {
            "unit_id": "u1",
            "position": (5, 5),
            "faction": "allies",
        }
        assert "killer_id" not in event

    def test_morale_changed_with_state_change(self):
        event: MoraleChanged = {
            "unit_id": "u1",
            "old_value": 80,
            "new_value": 60,
            "event_type": "friendly casualty",
            "state_changed": True,
            "new_state": "shaken",
        }
        assert event["new_state"] == "shaken"

    def test_error_occurred_with_context(self):
        event: ErrorOccurred = {
            "source": "pathfinder",
            "error_type": "NoPathError",
            "message": "no valid path found",
            "severity": "error",
            "context": {"start": (0, 0), "end": (10, 10)},
        }
        assert event["context"]["start"] == (0, 0)


class TestOptionalFields:
    def test_timestamp_is_optional(self):
        event: UnitMoved = {
            "unit_id": "u1",
            "from_tile": (0, 0),
            "to_tile": (1, 1),
        }
        assert "timestamp" not in event

    def test_timestamp_can_be_added(self):
        now = time.time()
        event: UnitMoved = {
            "unit_id": "u1",
            "from_tile": (0, 0),
            "to_tile": (1, 1),
            "timestamp": now,
        }
        assert abs(event["timestamp"] - now) < 0.001

    def test_game_resumed_minimal(self):
        event: GameResumed = {}
        assert isinstance(event, dict)

    def test_game_paused_with_reason(self):
        event: GamePaused = {"reason": "user request"}
        assert event["reason"] == "user request"

    def test_debug_command_with_args_and_result(self):
        event: DebugCommand = {
            "command": "teleport",
            "args": ["u1", 5, 5],
            "result": "ok",
        }
        assert event["args"] == ["u1", 5, 5]
