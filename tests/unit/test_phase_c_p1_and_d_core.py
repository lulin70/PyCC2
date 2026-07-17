"""Tests for Phase C P1+Phase D Core: SquadGroups."""

from unittest.mock import MagicMock

import pytest

from pycc2.presentation.ui.squad_group_manager import (
    SquadGroupManager,
)


@pytest.fixture
def make_unit():
    """Factory to create mock units."""

    def _make_unit(name: str, x: float = 0.0, y: float = 0.0):
        unit = MagicMock()
        unit.name = name
        unit.position_component = MagicMock()
        unit.position_component.x = x
        unit.position_component.y = y
        return unit

    return _make_unit


class TestSquadGroupManager:
    """Test suite for C4 Squad Group Manager (10 tests)."""

    def test_initialization(self):
        """Test manager initializes with 9 empty groups."""
        mgr = SquadGroupManager()

        assert mgr.MAX_GROUPS == 9
        assert len(mgr._groups) == 9
        assert mgr.total_units_in_groups == 0

    def test_create_group_valid(self, make_unit):
        """Test creating a valid group."""
        mgr = SquadGroupManager()
        units = [make_unit("Unit1", 1, 1), make_unit("Unit2", 5, 5)]

        result = mgr.create_group(1, units)

        assert result is True
        assert len(mgr.select_group(1)) == 2

    def test_create_group_invalid_number(self, make_unit):
        """Test creating group with invalid number."""
        mgr = SquadGroupManager()

        assert mgr.create_group(0, []) is False
        assert mgr.create_group(10, []) is False
        assert mgr.create_group(-1, []) is False

    def test_select_group(self, make_unit):
        """Test selecting units from group."""
        mgr = SquadGroupManager()
        units = [make_unit("U1"), make_unit("U2")]
        mgr.create_group(3, units)

        selected = mgr.select_group(3)

        assert len(selected) == 2
        assert selected[0].name == "U1"

    def test_select_empty_group(self):
        """Test selecting empty group returns empty list."""
        mgr = SquadGroupManager()

        assert mgr.select_group(5) == []

    def test_get_group_bounds(self, make_unit):
        """Test getting bounding box for group."""
        mgr = SquadGroupManager()
        units = [
            make_unit("U1", 2, 3),
            make_unit("U2", 8, 9),
            make_unit("U3", 5, 5),
        ]
        mgr.create_group(2, units)

        bounds = mgr.get_group_bounds(2)

        assert bounds == (2, 3, 8, 9)

    def test_get_group_bounds_empty(self):
        """Test bounds of empty group is None."""
        mgr = SquadGroupManager()

        assert mgr.get_group_bounds(7) is None

    def test_clear_group(self, make_unit):
        """Test clearing a specific group."""
        mgr = SquadGroupManager()
        mgr.create_group(1, [make_unit("U1")])

        assert mgr.clear_group(1) is True
        assert mgr.select_group(1) == []

    def test_clear_all_groups(self, make_unit):
        """Test clearing all groups."""
        mgr = SquadGroupManager()
        mgr.create_group(1, [make_unit("U1")])
        mgr.create_group(2, [make_unit("U2")])

        mgr.clear_all_groups()

        assert mgr.total_units_in_groups == 0

    def test_remove_unit_from_all(self, make_unit):
        """Test removing unit from all groups."""
        mgr = SquadGroupManager()
        u1 = make_unit("Shared")
        mgr.create_group(1, [u1, make_unit("Other")])
        mgr.create_group(2, [u1])

        mgr.remove_unit_from_all_groups(u1)

        assert u1 not in mgr.select_group(1)
        assert u1 not in mgr.select_group(2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
