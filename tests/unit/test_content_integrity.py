"""Content integrity tests for shipped scenario and unit data.

These tests read the real JSON data files and the real unit/weapon database.
They do not mock data: a broken scenario on disk must fail here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pycc2.domain.systems.cc2_authentic_units import (
    build_cc2_unit_database,
    get_cc2_weapons,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = PROJECT_ROOT / "data" / "scenarios"
MAP_DIR = PROJECT_ROOT / "data" / "maps"

REQUIRED_SCENARIO_KEYS = (
    "scenario_id",
    "name",
    "map_id",
    "forces",
    "victory_locations",
)


def _scenario_files() -> list[Path]:
    return sorted(p for p in SCENARIO_DIR.glob("*.json") if p.stem != "_schema")


SCENARIO_FILES = _scenario_files()
SCENARIO_IDS = [p.stem for p in SCENARIO_FILES]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _map_size(map_id: str) -> tuple[int, int]:
    data = _load(MAP_DIR / f"{map_id}.json")
    return data["width"], data["height"]


@pytest.fixture(scope="module")
def unit_db() -> dict:
    return build_cc2_unit_database()


@pytest.fixture(scope="module")
def weapon_db() -> dict:
    return get_cc2_weapons()


def test_scenario_directory_is_not_empty():
    assert SCENARIO_FILES, f"No scenario files found in {SCENARIO_DIR}"


def test_scenario_count_at_least_20():
    assert len(SCENARIO_FILES) >= 20, f"Expected >= 20 scenarios, found {len(SCENARIO_FILES)}"


@pytest.mark.parametrize("scenario_path", SCENARIO_FILES, ids=SCENARIO_IDS)
def test_scenario_parses_and_has_required_keys(scenario_path: Path):
    data = _load(scenario_path)

    for key in REQUIRED_SCENARIO_KEYS:
        assert key in data, f"{scenario_path.name}: missing required key '{key}'"

    assert data["scenario_id"] == scenario_path.stem, (
        f"{scenario_path.name}: scenario_id '{data['scenario_id']}' must match file name"
    )
    assert data["name"].strip(), f"{scenario_path.name}: empty name"

    forces = data["forces"]
    assert set(forces) >= {"allies", "axis"}, f"{scenario_path.name}: forces must define allies and axis"
    for side in ("allies", "axis"):
        assert forces[side].get("units"), f"{scenario_path.name}: side '{side}' has no units"


@pytest.mark.parametrize("scenario_path", SCENARIO_FILES, ids=SCENARIO_IDS)
def test_scenario_map_file_exists(scenario_path: Path):
    data = _load(scenario_path)
    map_path = MAP_DIR / f"{data['map_id']}.json"

    assert map_path.exists(), (
        f"{scenario_path.name}: map_id '{data['map_id']}' has no file at {map_path}"
    )


@pytest.mark.parametrize("scenario_path", SCENARIO_FILES, ids=SCENARIO_IDS)
def test_scenario_template_ids_exist_in_unit_database(scenario_path: Path, unit_db: dict):
    data = _load(scenario_path)
    dangling: list[tuple[str, str, str]] = []

    for side in ("allies", "axis"):
        force = data["forces"][side]
        entries = list(force.get("units", [])) + list(force.get("reinforcements", []))
        for entry in entries:
            template_id = entry["template_id"]
            if template_id not in unit_db:
                dangling.append((side, template_id, f"{scenario_path.name}"))
            assert entry.get("count", 1) >= 1

    assert not dangling, f"{scenario_path.name}: dangling template_id references {dangling}"


@pytest.mark.parametrize("scenario_path", SCENARIO_FILES, ids=SCENARIO_IDS)
def test_victory_locations_within_map_bounds(scenario_path: Path):
    data = _load(scenario_path)
    width, height = _map_size(data["map_id"])

    locations = data["victory_locations"]
    assert len(locations) >= 2, f"{scenario_path.name}: needs at least 2 victory locations"

    for location in locations:
        x, y = location["position"]
        assert 0 <= x < width, (
            f"{scenario_path.name}: VL '{location['id']}' x={x} outside map width {width}"
        )
        assert 0 <= y < height, (
            f"{scenario_path.name}: VL '{location['id']}' y={y} outside map height {height}"
        )


@pytest.mark.parametrize("scenario_path", SCENARIO_FILES, ids=SCENARIO_IDS)
def test_deployment_zones_within_map_bounds(scenario_path: Path):
    data = _load(scenario_path)
    width, height = _map_size(data["map_id"])

    for side in ("allies", "axis"):
        zone = data["forces"][side]["deployment_zone"]
        assert 0 <= zone["x_min"] <= zone["x_max"] < width, (
            f"{scenario_path.name}: side '{side}' x range {zone['x_min']}-{zone['x_max']} "
            f"outside map width {width}"
        )
        assert 0 <= zone["y_min"] <= zone["y_max"] < height, (
            f"{scenario_path.name}: side '{side}' y range {zone['y_min']}-{zone['y_max']} "
            f"outside map height {height}"
        )


def test_unit_weapon_references_exist_in_weapon_database(unit_db: dict, weapon_db: dict):
    missing: list[tuple[str, str, str]] = []

    for template_id, template in unit_db.items():
        if template.weapon_primary_id and template.weapon_primary_id not in weapon_db:
            missing.append((template_id, "primary", template.weapon_primary_id))
        if template.weapon_secondary_id and template.weapon_secondary_id not in weapon_db:
            missing.append((template_id, "secondary", template.weapon_secondary_id))

    assert not missing, f"Unit templates reference unknown weapons: {missing}"


def test_unit_template_ids_match_dictionary_keys(unit_db: dict):
    mismatched = [
        (key, template.template_id)
        for key, template in unit_db.items()
        if key != template.template_id
    ]
    assert not mismatched, f"Template id/key mismatch: {mismatched}"
