"""Lightweight validation for scenario JSON files (GAP-14).

The repository ships ``data/scenarios/_schema.json`` (JSON Schema draft-07).
Runtime code did not validate scenarios, so a malformed file could enter the
game loop and fail later in an unrelated place. This module performs the
checks needed by the runtime without adding a new dependency.
"""

from __future__ import annotations

REQUIRED_KEYS = (
    "scenario_id",
    "name",
    "description",
    "map_id",
    "time_of_day",
    "weather",
    "day",
    "sector",
    "operation_id",
    "forces",
    "victory_locations",
    "special_rules",
)

TIME_OF_DAY_VALUES = frozenset({"dawn", "day", "dusk", "night"})
WEATHER_VALUES = frozenset({"clear", "overcast", "rain", "fog"})
SECTOR_VALUES = frozenset({"arnhem", "nijmegen", "eindhoven"})
SPECIAL_RULES = frozenset(
    {
        "bridge_destructible",
        "no_air_support",
        "limited_air_support",
        "defender_advantage",
        "limited_reinforcements",
        "supply_dwindling",
        "amphibious_crossing_available",
        "combined_arms_bonus",
        "corridor_must_remain_open",
        "xxx_corps_linkup",
        "airdrop_deployment",
        "initial_scatter",
        "lz_must_hold_for_reinforcements",
        "night_fighting",
        "fortified_positions",
        "fanatic_defenders",
    }
)
VICTORY_LOCATION_TYPES = frozenset(
    {"bridge", "road_junction", "building", "landing_zone", "crossroads", "hill"}
)
VICTORY_LOCATION_VALUES = frozenset({10, 20, 30, 40})
DEPLOYMENT_DIRECTIONS = frozenset({"north", "south", "east", "west"})


def validate_scenario(data: object) -> list[str]:
    """Return a list of validation errors. An empty list means valid."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["scenario root must be an object"]

    for key in REQUIRED_KEYS:
        if key not in data:
            errors.append(f"missing required key: {key}")

    _check_str(data, "scenario_id", errors)
    _check_str(data, "name", errors)
    _check_str(data, "description", errors)
    _check_str(data, "map_id", errors)
    _check_str(data, "operation_id", errors)
    _check_enum(data, "time_of_day", TIME_OF_DAY_VALUES, errors)
    _check_enum(data, "weather", WEATHER_VALUES, errors)
    _check_enum(data, "sector", SECTOR_VALUES, errors)

    day = data.get("day")
    if not isinstance(day, int) or isinstance(day, bool) or not 1 <= day <= 9:
        errors.append("day must be an integer from 1 to 9")

    forces = data.get("forces")
    if not isinstance(forces, dict):
        errors.append("forces must be an object")
    else:
        for side in ("allies", "axis"):
            if side not in forces:
                errors.append(f"forces.{side} is required")
            else:
                errors.extend(_validate_force(forces[side], f"forces.{side}"))
        unexpected = set(forces) - {"allies", "axis"}
        if unexpected:
            errors.append(f"forces has unexpected keys: {sorted(unexpected)}")

    locations = data.get("victory_locations")
    if not isinstance(locations, list):
        errors.append("victory_locations must be a list")
    elif not 1 <= len(locations) <= 8:
        errors.append("victory_locations must contain 1 to 8 entries")
    else:
        for index, location in enumerate(locations):
            errors.extend(_validate_victory_location(location, f"victory_locations[{index}]"))

    rules = data.get("special_rules")
    if not isinstance(rules, list):
        errors.append("special_rules must be a list")
    else:
        for rule in rules:
            if not isinstance(rule, str):
                errors.append(f"special_rules contains non-string value: {rule!r}")
            elif rule not in SPECIAL_RULES:
                errors.append(f"unknown special rule: {rule}")

    return errors


def _check_str(data: dict, key: str, errors: list[str]) -> None:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{key} must be a non-empty string")


def _check_enum(data: dict, key: str, allowed: frozenset[str], errors: list[str]) -> None:
    value = data.get(key)
    if value not in allowed:
        errors.append(f"{key} must be one of {sorted(allowed)}")


def _validate_force(force: object, path: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(force, dict):
        return [f"{path} must be an object"]

    faction = force.get("faction")
    if faction not in {"BRITISH", "AMERICAN", "GERMAN"}:
        errors.append(f"{path}.faction must be BRITISH, AMERICAN, or GERMAN")

    zone = force.get("deployment_zone")
    if not isinstance(zone, dict):
        errors.append(f"{path}.deployment_zone must be an object")
    else:
        for edge in ("x_min", "x_max", "y_min", "y_max"):
            value = zone.get(edge)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"{path}.deployment_zone.{edge} must be a non-negative integer")
        if all(isinstance(zone.get(edge), int) for edge in ("x_min", "x_max")):
            if zone["x_min"] > zone["x_max"]:
                errors.append(f"{path}.deployment_zone.x_min must not exceed x_max")
        if all(isinstance(zone.get(edge), int) for edge in ("y_min", "y_max")):
            if zone["y_min"] > zone["y_max"]:
                errors.append(f"{path}.deployment_zone.y_min must not exceed y_max")

    units = force.get("units")
    if not isinstance(units, list) or not units:
        errors.append(f"{path}.units must be a non-empty list")
    else:
        for index, unit in enumerate(units):
            errors.extend(_validate_unit_entry(unit, f"{path}.units[{index}]"))

    reinforcements = force.get("reinforcements")
    if not isinstance(reinforcements, list):
        errors.append(f"{path}.reinforcements must be a list")
    else:
        for index, entry in enumerate(reinforcements):
            errors.extend(_validate_reinforcement(entry, f"{path}.reinforcements[{index}]"))

    for key in ("max_infantry", "max_support"):
        value = force.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            errors.append(f"{path}.{key} must be a non-negative integer")

    return errors


def _validate_unit_entry(unit: object, path: str) -> list[str]:
    if not isinstance(unit, dict):
        return [f"{path} must be an object"]
    errors: list[str] = []
    if not isinstance(unit.get("template_id"), str) or not unit["template_id"]:
        errors.append(f"{path}.template_id must be a non-empty string")
    count = unit.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        errors.append(f"{path}.count must be a positive integer")
    cost = unit.get("deployment_cost")
    if not isinstance(cost, int) or isinstance(cost, bool) or cost < 0:
        errors.append(f"{path}.deployment_cost must be a non-negative integer")
    return errors


def _validate_reinforcement(entry: object, path: str) -> list[str]:
    if not isinstance(entry, dict):
        return [f"{path} must be an object"]
    errors: list[str] = []
    if not isinstance(entry.get("template_id"), str) or not entry["template_id"]:
        errors.append(f"{path}.template_id must be a non-empty string")
    turn = entry.get("arrival_turn")
    if not isinstance(turn, int) or isinstance(turn, bool) or turn < 1:
        errors.append(f"{path}.arrival_turn must be a positive integer")
    if entry.get("from_direction") not in DEPLOYMENT_DIRECTIONS:
        errors.append(f"{path}.from_direction must be one of {sorted(DEPLOYMENT_DIRECTIONS)}")
    return errors


def _validate_victory_location(location: object, path: str) -> list[str]:
    if not isinstance(location, dict):
        return [f"{path} must be an object"]
    errors: list[str] = []
    location_id = location.get("id")
    if not isinstance(location_id, str) or not location_id.startswith("vl_"):
        errors.append(f"{path}.id must be a string prefixed with 'vl_'")

    position = location.get("position")
    if (
        not isinstance(position, list)
        or len(position) != 2
        or any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in position)
    ):
        errors.append(f"{path}.position must be [x, y] non-negative integers")

    if location.get("value") not in VICTORY_LOCATION_VALUES:
        errors.append(f"{path}.value must be one of {sorted(VICTORY_LOCATION_VALUES)}")
    if location.get("type") not in VICTORY_LOCATION_TYPES:
        errors.append(f"{path}.type must be one of {sorted(VICTORY_LOCATION_TYPES)}")
    return errors
