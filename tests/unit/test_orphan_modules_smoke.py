"""Smoke tests for ORPHAN modules pending v0.8.0+ INTEGRATE (TD-077).

These tests verify that the 3 ORPHAN modules without dedicated test files can
be imported and their main classes instantiated. They do NOT validate business
logic — that will be added when the modules are integrated into the game loop
in v0.8.0+ (MINOR version bump).

Modules covered (all marked STATUS: ORPHAN — pending v0.8.0+ integration):
    - squad_group_manager  (presentation/ui)
    - path_preview         (presentation/rendering)
    - range_indicator      (presentation/rendering)

The other 5 ORPHAN modules already have dedicated test files:
    - test_cover_seek_ai.py
    - test_psychology_system.py
    - test_day_night_cycle.py
    - test_variant_generators.py (shared for vehicle + faction generators)
"""

from __future__ import annotations

# ============================================================================
# squad_group_manager — SquadGroup + SquadGroupManager
# ============================================================================


class TestSquadGroupManagerSmoke:
    """Smoke tests for squad_group_manager ORPHAN module."""

    def test_import_squad_group_manager(self):
        """Module can be imported."""
        from pycc2.presentation.ui.squad_group_manager import (
            SquadGroup,
            SquadGroupManager,
        )

        assert SquadGroup is not None
        assert SquadGroupManager is not None

    def test_squad_group_instantiation(self):
        """SquadGroup can be instantiated with group_number."""
        from pycc2.presentation.ui.squad_group_manager import SquadGroup

        group = SquadGroup(group_number=1)
        assert group.group_number == 1
        assert group.units == []
        assert group.is_empty is True
        assert group.bounds is None  # empty group has no bounds

    def test_squad_group_manager_instantiation(self):
        """SquadGroupManager can be instantiated with default MAX_GROUPS=9."""
        from pycc2.presentation.ui.squad_group_manager import SquadGroupManager

        manager = SquadGroupManager()
        assert manager.MAX_GROUPS == 9
        assert manager.total_units_in_groups == 0
        assert manager.active_group_numbers == []

    def test_squad_group_manager_create_and_select_empty(self):
        """create_group + select_group on empty group works."""
        from pycc2.presentation.ui.squad_group_manager import SquadGroupManager

        manager = SquadGroupManager()
        # Invalid group numbers return False
        assert manager.create_group(0, []) is False
        assert manager.create_group(10, []) is False
        # Valid group number with empty list succeeds
        assert manager.create_group(1, []) is True
        assert manager.select_group(1) == []
        assert manager.get_group(1) is not None
        assert manager.get_group(0) is None  # invalid number

    def test_squad_group_manager_clear_all(self):
        """clear_all_groups resets state."""
        from pycc2.presentation.ui.squad_group_manager import SquadGroupManager

        manager = SquadGroupManager()
        manager.clear_all_groups()
        assert manager.total_units_in_groups == 0


# ============================================================================
# path_preview — PathDangerLevel + PathSegment + PreviewPath + PathPreview
# ============================================================================


class TestPathPreviewSmoke:
    """Smoke tests for path_preview ORPHAN module."""

    def test_import_path_preview(self):
        """Module can be imported."""
        from pycc2.presentation.rendering.path_preview import (
            PathDangerLevel,
            PathPreview,
            PathSegment,
            PreviewPath,
        )

        assert PathDangerLevel is not None
        assert PathSegment is not None
        assert PreviewPath is not None
        assert PathPreview is not None

    def test_path_danger_level_enum(self):
        """PathDangerLevel enum has expected members."""
        from pycc2.presentation.rendering.path_preview import PathDangerLevel

        assert PathDangerLevel.SAFE is not None
        assert PathDangerLevel.WARNING is not None
        assert PathDangerLevel.DANGER is not None

    def test_path_segment_instantiation(self):
        """PathSegment can be instantiated with start/end tuples."""
        from pycc2.presentation.rendering.path_preview import (
            PathDangerLevel,
            PathSegment,
        )

        segment = PathSegment(start=(0, 0), end=(1, 1))
        assert segment.start == (0, 0)
        assert segment.end == (1, 1)
        assert segment.danger is PathDangerLevel.SAFE  # default
        assert segment.estimated_time == 0.0  # default

    def test_preview_path_instantiation(self):
        """PreviewPath can be instantiated with defaults."""
        from pycc2.presentation.rendering.path_preview import PreviewPath

        path = PreviewPath()
        assert path.segments == []
        assert path.total_distance == 0
        assert path.total_time == 0.0
        assert path.is_valid is True

    def test_path_preview_instantiation_with_mock_pathfinder(self):
        """PathPreview can be instantiated with a pathfinder object.

        Uses a simple object as mock pathfinder since pathfinder is stored
        as an opaque reference (only used in calculate_path which is not
        exercised in this smoke test).
        """
        from pycc2.presentation.rendering.path_preview import PathPreview

        class _StubPathfinder:
            """Minimal stub for pathfinder interface."""

        preview = PathPreview(pathfinder=_StubPathfinder())
        assert preview.pathfinder is not None
        assert preview._current_path is None
        assert preview._show_timer == 0.0
        assert preview._visible is False

    def test_path_preview_show_delay_constant(self):
        """SHOW_DELAY class constant exists and is positive."""
        from pycc2.presentation.rendering.path_preview import PathPreview

        assert PathPreview.SHOW_DELAY > 0


# ============================================================================
# range_indicator — RangeType + RangeIndicator
# ============================================================================


class TestRangeIndicatorSmoke:
    """Smoke tests for range_indicator ORPHAN module.

    Note: module imports pygame at top level, so these tests require pygame
    to be importable (provided by pytest fixture in conftest.py).
    """

    def test_import_range_indicator(self):
        """Module can be imported."""
        from pycc2.presentation.rendering.range_indicator import (
            RangeIndicator,
            RangeType,
        )

        assert RangeIndicator is not None
        assert RangeType is not None

    def test_range_type_enum(self):
        """RangeType enum has expected members."""
        from pycc2.presentation.rendering.range_indicator import RangeType

        assert RangeType.MIN_RANGE is not None
        assert RangeType.MAX_RANGE is not None

    def test_range_indicator_instantiation(self):
        """RangeIndicator can be instantiated with no active unit."""
        from pycc2.presentation.rendering.range_indicator import RangeIndicator

        indicator = RangeIndicator()
        assert indicator.active_unit is None
        assert indicator._min_range == 0.0
        assert indicator._max_range == 0.0
        assert indicator._visible is False
        assert indicator.is_visible is False  # no active unit

    def test_range_indicator_get_ranges_default(self):
        """get_ranges returns (0.0, 0.0) when no unit set."""
        from pycc2.presentation.rendering.range_indicator import RangeIndicator

        indicator = RangeIndicator()
        assert indicator.get_ranges() == (0.0, 0.0)

    def test_range_indicator_clear(self):
        """clear() resets state."""
        from pycc2.presentation.rendering.range_indicator import RangeIndicator

        indicator = RangeIndicator()
        indicator.clear()
        assert indicator.active_unit is None
        assert indicator._visible is False
        assert indicator._min_range == 0.0
        assert indicator._max_range == 0.0

    def test_range_indicator_set_unit_none(self):
        """set_unit(None) clears visibility and ranges."""
        from pycc2.presentation.rendering.range_indicator import RangeIndicator

        indicator = RangeIndicator()
        indicator.set_unit(None)
        assert indicator.active_unit is None
        assert indicator._visible is False
        assert indicator._min_range == 0.0
        assert indicator._max_range == 0.0
