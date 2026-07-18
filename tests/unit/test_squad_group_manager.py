"""Tests for SquadGroupManager — CC2-authentic squad grouping and quick selection.

This module extends the 5 smoke tests in test_orphan_modules_smoke.py with
full unit test coverage across 6 dimensions (per DevSquad Testing Iron Rules
§Iron Rule 3): Happy Path / Error Case / Boundary / Performance /
Configuration / Integration.

v0.7.4 INTEGRATE prep: psychology_system + squad_group_manager test enhancement.
The squad_group_manager module is ORPHAN (TD-077) pending v0.8.0+ integration.
These tests establish a quality baseline so v0.8.0 INTEGRATE only needs to
focus on game_loop wiring, not test backfill.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from pycc2.presentation.ui.squad_group_manager import (
    SquadGroup,
    SquadGroupManager,
)

# ============================================================================
# Test fixtures — lightweight Unit stub (only position_component.x/y needed)
# ============================================================================


@dataclass(eq=False)
class _StubPosition:
    """Minimal position stub matching Unit.position_component interface."""

    x: float
    y: float


@dataclass(eq=False)
class _StubUnit:
    """Minimal Unit stub for squad_group_manager tests.

    squad_group_manager only accesses unit.position_component.x/y (in bounds
    calculation) and uses `in` / `remove` on the units list (identity-based).
    A full Unit instance requires too many dependencies (components, mixins,
    templates) to be practical for these unit tests.

    `eq=False` ensures identity-based comparison (matching real Unit semantics
    where each instance is a distinct entity, even if field values coincide).
    """

    position_component: _StubPosition


def _make_unit(x: float = 0.0, y: float = 0.0) -> _StubUnit:
    """Create a stub unit at the given position."""
    return _StubUnit(position_component=_StubPosition(x=x, y=y))


def _make_units(n: int) -> list[_StubUnit]:
    """Create n stub units at distinct positions."""
    return [_make_unit(x=float(i), y=float(i * 2)) for i in range(n)]


# ============================================================================
# TestSquadGroup — SquadGroup dataclass unit tests
# ============================================================================


class TestSquadGroup:
    """Tests for SquadGroup dataclass behavior."""

    def test_add_units_copies_list(self):
        """Verify: add_units stores a copy of the input list.

        Scenario: Caller mutates the original list after add_units.
        Expected: SquadGroup.units is unaffected.
        """
        group = SquadGroup(group_number=1)
        original = [_make_unit(1.0, 2.0), _make_unit(3.0, 4.0)]
        group.add_units(original)
        # Mutate original — group must be unaffected
        original.append(_make_unit(5.0, 6.0))
        assert len(group.units) == 2

    def test_clear_empties_units(self):
        """Verify: clear() empties the units list."""
        group = SquadGroup(group_number=1)
        group.add_units([_make_unit(), _make_unit()])
        assert not group.is_empty
        group.clear()
        assert group.units == []
        assert group.is_empty is True

    def test_is_empty_true_after_clear(self):
        """Verify: is_empty is True after clear, False with units."""
        group = SquadGroup(group_number=1)
        assert group.is_empty is True
        group.add_units([_make_unit()])
        assert group.is_empty is False
        group.clear()
        assert group.is_empty is True

    def test_bounds_none_for_empty_group(self):
        """Verify: bounds is None when group has no units."""
        group = SquadGroup(group_number=1)
        assert group.bounds is None

    def test_bounds_single_unit(self):
        """Verify: bounds of a single unit collapses to (x, y, x, y)."""
        group = SquadGroup(group_number=1)
        group.add_units([_make_unit(x=5.0, y=7.0)])
        assert group.bounds == (5, 7, 5, 7)

    def test_bounds_multiple_units(self):
        """Verify: bounds computes min/max across all units."""
        group = SquadGroup(group_number=1)
        group.add_units(
            [
                _make_unit(x=1.0, y=2.0),
                _make_unit(x=5.0, y=8.0),
                _make_unit(x=3.0, y=4.0),
            ]
        )
        # min_x=1, min_y=2, max_x=5, max_y=8
        assert group.bounds == (1, 2, 5, 8)

    def test_bounds_with_float_positions(self):
        """Verify: bounds truncates float positions to int via int()."""
        group = SquadGroup(group_number=1)
        group.add_units(
            [
                _make_unit(x=1.7, y=2.3),
                _make_unit(x=5.9, y=8.1),
            ]
        )
        # int(1.7)=1, int(2.3)=2, int(5.9)=5, int(8.1)=8
        assert group.bounds == (1, 2, 5, 8)


# ============================================================================
# TestSquadGroupManagerCreate — create_group tests
# ============================================================================


class TestSquadGroupManagerCreate:
    """Tests for SquadGroupManager.create_group."""

    def test_create_group_valid_numbers_1_to_9(self):
        """Verify: group_num 1-9 are all valid (boundary test)."""
        manager = SquadGroupManager()
        for num in range(1, 10):
            assert manager.create_group(num, []) is True, f"group_num={num} should be valid"

    def test_create_group_invalid_zero(self):
        """Verify: group_num=0 returns False."""
        manager = SquadGroupManager()
        assert manager.create_group(0, []) is False

    def test_create_group_invalid_ten(self):
        """Verify: group_num=10 (MAX_GROUPS+1) returns False."""
        manager = SquadGroupManager()
        assert manager.create_group(10, []) is False

    def test_create_group_invalid_negative(self):
        """Verify: negative group_num returns False."""
        manager = SquadGroupManager()
        assert manager.create_group(-1, []) is False

    def test_create_group_empty_list(self):
        """Verify: empty units list is accepted (returns True)."""
        manager = SquadGroupManager()
        assert manager.create_group(1, []) is True
        assert manager.select_group(1) == []

    def test_create_group_overwrite_existing(self):
        """Verify: creating an existing group overwrites its units."""
        manager = SquadGroupManager()
        units_v1 = _make_units(3)
        manager.create_group(1, units_v1)
        units_v2 = _make_units(5)
        manager.create_group(1, units_v2)
        # Should have 5 units (v2), not 3+5=8
        assert len(manager.select_group(1)) == 5


# ============================================================================
# TestSquadGroupManagerSelect — select_group tests
# ============================================================================


class TestSquadGroupManagerSelect:
    """Tests for SquadGroupManager.select_group."""

    def test_select_group_valid_returns_copy(self):
        """Verify: select_group returns a copy, not the internal list.

        Scenario: Caller mutates the returned list.
        Expected: Internal state is unaffected.
        """
        manager = SquadGroupManager()
        units = _make_units(3)
        manager.create_group(1, units)
        selected = manager.select_group(1)
        assert len(selected) == 3
        # Mutate returned list — internal must be unaffected
        selected.clear()
        assert len(manager.select_group(1)) == 3

    def test_select_group_invalid_returns_empty(self):
        """Verify: invalid group_num returns empty list."""
        manager = SquadGroupManager()
        assert manager.select_group(0) == []
        assert manager.select_group(10) == []
        assert manager.select_group(-1) == []

    def test_select_group_after_clear(self):
        """Verify: select after clear returns empty list."""
        manager = SquadGroupManager()
        manager.create_group(1, _make_units(3))
        assert len(manager.select_group(1)) == 3
        manager.clear_group(1)
        assert manager.select_group(1) == []


# ============================================================================
# TestSquadGroupManagerClear — clear_group / clear_all_groups tests
# ============================================================================


class TestSquadGroupManagerClear:
    """Tests for SquadGroupManager clear operations."""

    def test_clear_group_valid(self):
        """Verify: clear_group on a valid group returns True and empties it."""
        manager = SquadGroupManager()
        manager.create_group(1, _make_units(2))
        assert manager.clear_group(1) is True
        assert manager.select_group(1) == []

    def test_clear_group_invalid(self):
        """Verify: clear_group on invalid num returns False."""
        manager = SquadGroupManager()
        assert manager.clear_group(0) is False
        assert manager.clear_group(10) is False

    def test_clear_all_groups_resets_all(self):
        """Verify: clear_all_groups empties all 9 groups."""
        manager = SquadGroupManager()
        # Populate groups 1, 3, 5
        manager.create_group(1, _make_units(2))
        manager.create_group(3, _make_units(3))
        manager.create_group(5, _make_units(1))
        assert manager.total_units_in_groups == 6
        manager.clear_all_groups()
        assert manager.total_units_in_groups == 0
        assert manager.active_group_numbers == []

    def test_clear_group_then_select_empty(self):
        """Verify: after clear_group, select returns empty list."""
        manager = SquadGroupManager()
        manager.create_group(2, _make_units(4))
        manager.clear_group(2)
        assert manager.select_group(2) == []
        assert manager.get_group(2) is not None  # group object still exists
        assert manager.get_group(2).is_empty is True


# ============================================================================
# TestSquadGroupManagerUnitOps — unit-level operations
# ============================================================================


class TestSquadGroupManagerUnitOps:
    """Tests for add_unit_to_group / remove_unit_from_all_groups."""

    def test_add_unit_to_group_new(self):
        """Verify: adding a new unit to an existing group."""
        manager = SquadGroupManager()
        unit = _make_unit()
        assert manager.add_unit_to_group(1, unit) is True
        assert unit in manager.select_group(1)
        assert manager.total_units_in_groups == 1

    def test_add_unit_to_group_duplicate(self):
        """Verify: adding the same unit twice does not duplicate it."""
        manager = SquadGroupManager()
        unit = _make_unit()
        manager.add_unit_to_group(1, unit)
        manager.add_unit_to_group(1, unit)
        assert len(manager.select_group(1)) == 1

    def test_add_unit_to_group_invalid_num(self):
        """Verify: invalid group_num returns False."""
        manager = SquadGroupManager()
        assert manager.add_unit_to_group(0, _make_unit()) is False
        assert manager.add_unit_to_group(10, _make_unit()) is False

    def test_remove_unit_from_all_groups(self):
        """Verify: remove_unit_from_all_groups removes from every group."""
        manager = SquadGroupManager()
        unit = _make_unit()
        manager.add_unit_to_group(1, unit)
        manager.add_unit_to_group(3, unit)
        manager.add_unit_to_group(5, unit)
        assert manager.total_units_in_groups == 3
        manager.remove_unit_from_all_groups(unit)
        assert manager.total_units_in_groups == 0
        assert unit not in manager.select_group(1)
        assert unit not in manager.select_group(3)
        assert unit not in manager.select_group(5)

    def test_remove_unit_not_in_groups(self):
        """Verify: removing a unit not in any group is a no-op."""
        manager = SquadGroupManager()
        manager.create_group(1, _make_units(2))
        orphan_unit = _make_unit()
        # Should not raise and should not affect existing groups
        manager.remove_unit_from_all_groups(orphan_unit)
        assert manager.total_units_in_groups == 2


# ============================================================================
# TestSquadGroupManagerProperties — property + accessor tests
# ============================================================================


class TestSquadGroupManagerProperties:
    """Tests for total_units_in_groups / active_group_numbers / get_group / get_group_bounds."""

    def test_total_units_in_groups_empty(self):
        """Verify: total_units_in_groups is 0 for a fresh manager."""
        manager = SquadGroupManager()
        assert manager.total_units_in_groups == 0

    def test_total_units_in_groups_multi(self):
        """Verify: total_units_in_groups sums across all groups."""
        manager = SquadGroupManager()
        manager.create_group(1, _make_units(3))
        manager.create_group(2, _make_units(5))
        manager.create_group(9, _make_units(2))
        assert manager.total_units_in_groups == 10

    def test_active_group_numbers_empty(self):
        """Verify: active_group_numbers is [] for a fresh manager."""
        manager = SquadGroupManager()
        assert manager.active_group_numbers == []

    def test_active_group_numbers_multi(self):
        """Verify: active_group_numbers lists only non-empty groups."""
        manager = SquadGroupManager()
        manager.create_group(1, _make_units(2))
        manager.create_group(3, _make_units(1))
        manager.create_group(5, _make_units(1))
        # Groups 2, 4, 6, 7, 8, 9 are empty
        assert manager.active_group_numbers == [1, 3, 5]

    def test_get_group_valid(self):
        """Verify: get_group returns SquadGroup for valid num."""
        manager = SquadGroupManager()
        group = manager.get_group(1)
        assert group is not None
        assert isinstance(group, SquadGroup)
        assert group.group_number == 1

    def test_get_group_invalid(self):
        """Verify: get_group returns None for invalid num."""
        manager = SquadGroupManager()
        assert manager.get_group(0) is None
        assert manager.get_group(10) is None
        assert manager.get_group(-1) is None

    def test_get_group_bounds_empty(self):
        """Verify: get_group_bounds returns None for empty group."""
        manager = SquadGroupManager()
        assert manager.get_group_bounds(1) is None

    def test_get_group_bounds_valid(self):
        """Verify: get_group_bounds returns bounds tuple for populated group."""
        manager = SquadGroupManager()
        manager.create_group(
            1,
            [
                _make_unit(x=2.0, y=3.0),
                _make_unit(x=8.0, y=5.0),
            ],
        )
        bounds = manager.get_group_bounds(1)
        assert bounds == (2, 3, 8, 5)


# ============================================================================
# TestSquadGroupManagerPerformance — performance baselines
# ============================================================================


class TestSquadGroupManagerPerformance:
    """Performance baseline tests for squad_group_manager.

    These establish timing baselines so v0.8.0 INTEGRATE can detect
    regressions if game_loop wiring adds unexpected overhead.
    """

    @pytest.mark.slow
    def test_create_1000_units_performance(self):
        """Verify: creating a group with 1000 units completes under 100ms.

        Scenario: Player selects 1000 units and presses Ctrl+1.
        Expected: Group creation completes in <100ms (CC2 auth pacing).
        """
        import time

        manager = SquadGroupManager()
        units = _make_units(1000)
        start = time.perf_counter()
        manager.create_group(1, units)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100.0, f"create_group(1000 units) took {elapsed_ms:.2f}ms"
        assert len(manager.select_group(1)) == 1000

    @pytest.mark.slow
    def test_select_1000_units_performance(self):
        """Verify: selecting a 1000-unit group completes under 50ms.

        Scenario: Player presses '1' to select group 1 (1000 units).
        Expected: Selection completes in <50ms (responsive UI).
        """
        import time

        manager = SquadGroupManager()
        manager.create_group(1, _make_units(1000))
        start = time.perf_counter()
        selected = manager.select_group(1)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50.0, f"select_group(1000 units) took {elapsed_ms:.2f}ms"
        assert len(selected) == 1000
