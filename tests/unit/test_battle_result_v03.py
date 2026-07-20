"""V-03 (Wave C5): Unit tests for BattleResult enhancements.

Tests the new fields (events, mvp_unit_id) and backward compatibility
of to_dict()/from_dict() with old save files.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()  # Required for BattleResult usage in rendering pipelines

import pytest  # noqa: E402

from pycc2.domain.systems.battle_result import (  # noqa: E402
    BattleEvent,
    BattleResult,
)
from tests.fixtures.battle_result_factory import (  # noqa: E402
    make_battle_result_with_events,
    make_battle_result_with_mvp,
    make_full_battle_result,
    make_minimal_battle_result,
    make_typical_event_list,
    make_victory_battle_result,
)

# ============================================================================
# BattleEvent dataclass tests
# ============================================================================


class TestBattleEvent:
    """Test BattleEvent frozen dataclass."""

    def test_battle_event_is_frozen(self):
        """BattleEvent must be frozen (immutable)."""
        event = BattleEvent(event_type="unit_killed", timestamp=30.0)
        with pytest.raises(AttributeError):
            event.event_type = "other"  # type: ignore[misc]

    def test_battle_event_default_values(self):
        """BattleEvent optional fields default to None/empty."""
        event = BattleEvent(event_type="unit_killed", timestamp=30.0)
        assert event.unit_id is None
        assert event.faction is None
        assert event.description == ""

    def test_battle_event_with_all_fields(self):
        """BattleEvent accepts all fields."""
        event = BattleEvent(
            event_type="morale_break",
            timestamp=45.0,
            unit_id="axis_2",
            faction="axis",
            description="Morale collapsed",
        )
        assert event.event_type == "morale_break"
        assert event.timestamp == 45.0
        assert event.unit_id == "axis_2"
        assert event.faction == "axis"
        assert event.description == "Morale collapsed"


# ============================================================================
# BattleResult new fields tests
# ============================================================================


class TestBattleResultNewFields:
    """Test V-03 new fields on BattleResult."""

    def test_battle_result_has_events_field(self):
        """BattleResult must have events field (V-03)."""
        result = make_minimal_battle_result()
        assert hasattr(result, "events")
        assert result.events == []

    def test_battle_result_has_mvp_unit_id_field(self):
        """BattleResult must have mvp_unit_id field (V-03)."""
        result = make_minimal_battle_result()
        assert hasattr(result, "mvp_unit_id")
        assert result.mvp_unit_id is None

    def test_battle_result_with_events(self):
        """BattleResult accepts events list."""
        events = make_typical_event_list()
        result = make_battle_result_with_events(events)
        assert len(result.events) == 7
        assert result.events[0].event_type == "unit_killed"
        assert result.events[0].timestamp == 15.0

    def test_battle_result_with_mvp(self):
        """BattleResult accepts mvp_unit_id."""
        result = make_battle_result_with_mvp(mvp_unit_id="ace_1")
        assert result.mvp_unit_id == "ace_1"


# ============================================================================
# Backward compatibility tests
# ============================================================================


class TestBattleResultBackwardCompat:
    """Test backward compatibility of to_dict()/from_dict()."""

    def test_to_dict_includes_new_fields(self):
        """to_dict() must include events and mvp_unit_id."""
        result = make_full_battle_result()
        data = result.to_dict()
        assert "events" in data
        assert "mvp_unit_id" in data
        assert isinstance(data["events"], list)
        assert len(data["events"]) == len(result.events)

    def test_from_dict_old_save_file_without_new_fields(self):
        """from_dict() must handle old save files without events/mvp_unit_id."""
        # Simulate an old save file (pre-V-03)
        old_data = {
            "mission_id": "old_mission",
            "mission_name": "Old Mission",
            "outcome": "VICTORY",
            "ticks_elapsed": 600,
            "date_in_campaign": 1,
            "allies_killed": 2,
            "axis_killed": 5,
            "allies_routed": 0,
            "axis_routed": 1,
            "victory_points": 100,
            "unit_records": [],
        }
        result = BattleResult.from_dict(old_data)
        assert result.events == []  # Default empty list
        assert result.mvp_unit_id is None  # Default None
        assert result.mission_id == "old_mission"

    def test_to_dict_from_dict_roundtrip(self):
        """to_dict() → from_dict() roundtrip preserves V-03 fields."""
        original = make_full_battle_result()
        data = original.to_dict()
        restored = BattleResult.from_dict(data)

        assert restored.mission_id == original.mission_id
        assert restored.mvp_unit_id == original.mvp_unit_id
        assert len(restored.events) == len(original.events)
        assert restored.events[0].event_type == original.events[0].event_type
        assert restored.events[0].timestamp == original.events[0].timestamp

    def test_from_dict_with_new_fields(self):
        """from_dict() correctly parses V-03 fields."""
        data = {
            "mission_id": "test",
            "mission_name": "Test",
            "outcome": "VICTORY",
            "ticks_elapsed": 600,
            "events": [
                {
                    "event_type": "unit_killed",
                    "timestamp": 30.0,
                    "unit_id": "unit_1",
                    "faction": "allies",
                    "description": "Kill event",
                },
            ],
            "mvp_unit_id": "unit_1",
        }
        result = BattleResult.from_dict(data)
        assert len(result.events) == 1
        assert result.events[0].event_type == "unit_killed"
        assert result.events[0].unit_id == "unit_1"
        assert result.mvp_unit_id == "unit_1"

    def test_from_dict_with_empty_events(self):
        """from_dict() handles empty events list."""
        data = {
            "mission_id": "test",
            "outcome": "VICTORY",
            "ticks_elapsed": 600,
            "events": [],
        }
        result = BattleResult.from_dict(data)
        assert result.events == []


# ============================================================================
# BattleResult to_dict full serialization tests
# ============================================================================


class TestBattleResultSerialization:
    """Test full serialization of BattleResult with V-03 fields."""

    def test_to_dict_includes_all_v03_fields(self):
        """to_dict() includes all V-03 fields with correct structure."""
        result = make_full_battle_result()
        data = result.to_dict()

        # Check events structure
        assert len(data["events"]) > 0
        event_dict = data["events"][0]
        assert "event_type" in event_dict
        assert "timestamp" in event_dict
        assert "unit_id" in event_dict
        assert "faction" in event_dict
        assert "description" in event_dict

        # Check mvp_unit_id
        assert data["mvp_unit_id"] is not None

    def test_to_dict_events_are_serialized_as_dicts(self):
        """to_dict() serializes BattleEvent as plain dicts."""
        result = make_battle_result_with_events()
        data = result.to_dict()
        for event_dict in data["events"]:
            assert isinstance(event_dict, dict)
            assert not isinstance(event_dict, BattleEvent)

    def test_existing_fields_still_serialized(self):
        """to_dict() still serializes pre-V-03 fields."""
        result = make_victory_battle_result()
        data = result.to_dict()
        # Pre-V-03 fields
        assert data["mission_id"] == "mission_victory"
        assert data["outcome"] == "VICTORY"
        assert data["allies_killed"] == 3
        assert data["axis_killed"] == 8
        assert data["victory_points"] == 250
