"""Unit tests for ScenarioRules value object (TD-069 coverage close-out).

Covers ``pycc2.domain.value_objects.scenario_rules`` — the only wired module
from the 2026-11-14 zero-coverage re-audit (used by game_loop.py and
deployment_ui.py at runtime).
"""

from __future__ import annotations

import dataclasses

import pytest

from pycc2.domain.value_objects.scenario_rules import ScenarioRules


class TestFromMapData:
    """Verify: from_map_data parses every accepted special_rules shape."""

    def test_default_rules_empty(self):
        """Verify: default construction yields an empty rule set."""
        rules = ScenarioRules()
        assert rules.rules == frozenset()
        assert rules.has("no_fog") is False

    def test_missing_key_yields_empty(self):
        """Verify: map_data without special_rules yields an empty set."""
        assert ScenarioRules.from_map_data({}).rules == frozenset()

    def test_list_rules_normalized(self):
        """Verify: list entries are stripped and lowercased."""
        rules = ScenarioRules.from_map_data({"special_rules": [" No_Fog ", "nIGHT_OPS"]})
        assert rules.rules == frozenset({"no_fog", "night_ops"})

    def test_single_string_wrapped(self):
        """Verify: a bare string is treated as a one-element list."""
        rules = ScenarioRules.from_map_data({"special_rules": "  NoFog  "})
        assert rules.rules == frozenset({"nofog"})

    def test_dict_rules_keep_truthy_keys(self):
        """Verify: dict form keeps only keys with truthy values."""
        rules = ScenarioRules.from_map_data(
            {"special_rules": {"no_fog": True, "night_ops": False, "reinforcements": 1}}
        )
        assert rules.rules == frozenset({"no_fog", "reinforcements"})

    def test_non_dict_map_data_yields_empty(self):
        """Verify: non-dict map_data degrades to an empty rule set."""
        assert ScenarioRules.from_map_data(None).rules == frozenset()  # type: ignore[arg-type]

    def test_non_string_and_blank_entries_dropped(self):
        """Verify: non-string entries and blank strings are filtered out."""
        rules = ScenarioRules.from_map_data({"special_rules": ["no_fog", 42, "   ", None]})  # type: ignore[list-item]
        assert rules.rules == frozenset({"no_fog"})


class TestHas:
    """Verify: has() lookup is normalized (strip + lowercase)."""

    def test_has_exact_match(self):
        rules = ScenarioRules.from_map_data({"special_rules": ["no_fog"]})
        assert rules.has("no_fog") is True

    def test_has_case_and_space_insensitive(self):
        rules = ScenarioRules.from_map_data({"special_rules": ["no_fog"]})
        assert rules.has("  NO_FOG ") is True

    def test_has_absent_rule(self):
        rules = ScenarioRules.from_map_data({"special_rules": ["no_fog"]})
        assert rules.has("night_ops") is False


class TestImmutability:
    """Verify: ScenarioRules is frozen (value-object contract)."""

    def test_frozen_dataclass_rejects_mutation(self):
        rules = ScenarioRules.from_map_data({"special_rules": ["no_fog"]})
        with pytest.raises(dataclasses.FrozenInstanceError):
            rules.rules = frozenset()  # type: ignore[misc]
