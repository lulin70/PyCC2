"""Unit tests for scenario JSON validation (GAP-14)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from pycc2.domain.value_objects.scenario_validation import validate_scenario


def _valid_scenario() -> dict:
    force = {
        "faction": "BRITISH",
        "deployment_zone": {"x_min": 0, "x_max": 5, "y_min": 0, "y_max": 5},
        "units": [{"template_id": "uk_rifle_squad", "count": 1, "deployment_cost": 100}],
        "reinforcements": [
            {"template_id": "uk_rifle_squad", "arrival_turn": 3, "from_direction": "west"}
        ],
        "max_infantry": 9,
        "max_support": 6,
    }
    axis = copy.deepcopy(force)
    axis["faction"] = "GERMAN"
    return {
        "scenario_id": "test_scenario",
        "name": "Test Scenario",
        "description": "Test description",
        "map_id": "test_map",
        "time_of_day": "day",
        "weather": "clear",
        "day": 1,
        "sector": "arnhem",
        "operation_id": "test_operation",
        "forces": {"allies": force, "axis": axis},
        "victory_locations": [
            {"id": "vl_test", "position": [1, 1], "value": 10, "type": "bridge"}
        ],
        "special_rules": ["night_fighting"],
    }


def test_valid_scenario_passes() -> None:
    assert validate_scenario(_valid_scenario()) == []


def test_missing_required_key_is_reported() -> None:
    data = _valid_scenario()
    del data["map_id"]
    errors = validate_scenario(data)
    assert any("map_id" in error for error in errors)


def test_unknown_special_rule_is_reported() -> None:
    data = _valid_scenario()
    data["special_rules"] = ["not_a_real_rule"]
    errors = validate_scenario(data)
    assert any("unknown special rule" in error for error in errors)


def test_invalid_victory_location_value_is_reported() -> None:
    data = _valid_scenario()
    data["victory_locations"][0]["value"] = 15
    errors = validate_scenario(data)
    assert any("victory_locations[0].value" in error for error in errors)


def test_inverted_deployment_zone_is_reported() -> None:
    data = _valid_scenario()
    data["forces"]["allies"]["deployment_zone"]["x_min"] = 9
    errors = validate_scenario(data)
    assert any("x_min must not exceed x_max" in error for error in errors)


def test_all_shipped_scenarios_are_valid() -> None:
    scenario_dir = Path("data/scenarios")
    files = sorted(p for p in scenario_dir.glob("*.json") if p.name != "_schema.json")
    assert files, "no scenario files found"
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_scenario(data)
        assert errors == [], f"{path.name}: {errors}"
