"""
Tests for Squad Entity
"""

from __future__ import annotations

from pycc2.domain.entities.squad import (
    FormationType,
    Squad,
)
from pycc2.domain.entities.unit import Faction


def _make_squad(
    id: str = "s1",
    name: str = "Alpha Squad",
    side: Faction = Faction.ALLIES,
    unit_ids: list[str] | None = None,
    commander_unit_id: str | None = None,
) -> Squad:
    return Squad(
        id=id,
        name=name,
        side=side,
        unit_ids=unit_ids if unit_ids is not None else [],
        commander_unit_id=commander_unit_id,
    )


class TestSquadConstruction:
    def test_basic_construction(self):
        s = _make_squad()
        assert s.id == "s1"
        assert s.name == "Alpha Squad"
        assert s.side == Faction.ALLIES

    def test_default_formation_is_line(self):
        s = _make_squad()
        assert s.formation_type == FormationType.LINE

    def test_commander_default_none_when_empty(self):
        s = _make_squad()
        assert s.commander_unit_id is None

    def test_with_initial_units(self):
        s = _make_squad(unit_ids=["u1", "u2"])
        assert s.unit_count == 2


class TestAddUnit:
    def test_add_unit_increases_count(self):
        s = _make_squad()
        s.add_unit("u1")
        assert s.unit_count == 1

    def test_add_first_unit_becomes_commander(self):
        s = _make_squad()
        s.add_unit("u1")
        assert s.commander_unit_id == "u1"

    def test_duplicate_unit_not_added(self):
        s = _make_squad()
        s.add_unit("u1")
        s.add_unit("u1")
        assert s.unit_count == 1


class TestRemoveUnit:
    def test_remove_unit_decreases_count(self):
        s = _make_squad(unit_ids=["u1", "u2"])
        s.remove_unit("u1")
        assert s.unit_count == 1
        assert "u1" not in s.unit_ids

    def test_remove_commander_reassigns(self):
        s = _make_squad(unit_ids=["u1", "u2"], commander_unit_id="u1")
        s.remove_unit("u1")
        assert s.commander_unit_id == "u2"

    def test_remove_last_unit_clears_commander(self):
        s = _make_squad(unit_ids=["u1"], commander_unit_id="u1")
        s.remove_unit("u1")
        assert s.commander_unit_id is None


class TestSetCommander:
    def test_set_commander_updates(self):
        s = _make_squad(unit_ids=["u1", "u2"])
        s.set_commander("u2")
        assert s.commander_unit_id == "u2"

    def test_set_commander_nonexistent_ignored(self):
        s = _make_squad(unit_ids=["u1"])
        original = s.commander_unit_id
        s.set_commander("u99")
        assert s.commander_unit_id == original


class TestUnitCount:
    def test_empty_squad_zero(self):
        s = _make_squad()
        assert s.unit_count == 0

    def test_with_units(self):
        s = _make_squad(unit_ids=["u1", "u2", "u3"])
        assert s.unit_count == 3


class TestIsAlive:
    def test_alive_with_units(self):
        s = _make_squad(unit_ids=["u1"])
        assert s.is_alive is True

    def test_not_alive_when_empty(self):
        s = _make_squad()
        assert s.is_alive is False


class TestAverageMorale:
    def test_returns_placeholder(self):
        s = _make_squad()
        assert s.average_morale == 50.0
