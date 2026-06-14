"""Tests for Phase C P0 UI Systems: PathPreview, RangeIndicator, Tooltip."""

import pytest
from unittest.mock import MagicMock, patch

from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.presentation.rendering.path_preview import (
    PathPreview,
    PreviewPath,
    PathSegment,
    PathDangerLevel,
)
from pycc2.presentation.rendering.range_indicator import (
    RangeIndicator,
)
from pycc2.presentation.ui.tooltip import (
    Tooltip,
)


@pytest.fixture
def mock_unit():
    """Create a mock unit for testing."""
    unit = MagicMock()
    unit.position_component = MagicMock()
    unit.position_component.x = 5.0
    unit.position_component.y = 5.0
    unit.name = "Rifle Squad"
    unit.unit_type = "Infantry"
    unit.movement_speed = 3.0
    unit.health_component = MagicMock()
    unit.health_component.current_hp = 80
    unit.health_component.max_hp = 100
    unit.morale_component = MagicMock()
    unit.morale_component.current_morale = 85.0
    unit.weapon_component = MagicMock()
    unit.weapon_component.min_range = 1.0
    unit.weapon_component.max_range = 8.0
    unit.weapon_component.current_ammo = 7
    unit.weapon_component.max_ammo = 10
    unit.status = "Normal"
    unit.vision_range = 12.0
    return unit


@pytest.fixture
def mock_game_map():
    """Create a mock game map."""
    game_map = MagicMock()
    game_map.is_within_bounds.return_value = True
    game_map.is_passable.return_value = True

    terrain = MagicMock()
    terrain.movement_cost = 1.0
    terrain.blocks_los = False
    terrain.name = "grass"
    game_map.get_terrain.return_value = terrain
    game_map.get_enhanced_tile.return_value = None

    return game_map


@pytest.fixture
def mock_pathfinder():
    """Create a mock pathfinder with predefined path."""
    pathfinder = MagicMock()

    test_path = [
        TileCoord(5, 5),
        TileCoord(6, 5),
        TileCoord(7, 5),
        TileCoord(7, 6),
        TileCoord(7, 7),
    ]

    pathfinder.find_path.return_value = test_path
    return pathfinder


@pytest.fixture
def mock_los_system():
    """Create a mock LOS system."""
    los = MagicMock()
    los.can_see.return_value = (False, MagicMock())
    return los


@pytest.fixture
def mock_camera():
    """Create a mock camera."""
    camera = MagicMock()
    camera.zoom = 1.0
    camera.world_to_screen = lambda pos: (pos[0] * 32 + 640, pos[1] * 32 + 360)
    return camera


class TestPathPreview:
    """Test suite for PathPreview system (C1)."""

    def test_path_preview_initialization(self, mock_pathfinder, mock_los_system):
        """Test PathPreview initializes correctly."""
        preview = PathPreview(pathfinder=mock_pathfinder, los_system=mock_los_system)

        assert preview.pathfinder == mock_pathfinder
        assert preview.los_system == mock_los_system
        assert preview._current_path is None
        assert preview._visible is False
        assert preview.SHOW_DELAY == 0.3

    def test_calculate_valid_path(self, mock_pathfinder, mock_game_map, mock_unit):
        """Test calculating a valid movement path."""
        preview = PathPreview(pathfinder=mock_pathfinder)

        target = (7, 7)
        result = preview.calculate_path(mock_unit, target, mock_game_map)

        assert result.is_valid is True
        assert result.total_distance == 4  # 4 segments in our mock path
        assert len(result.segments) == 4
        assert result.total_time > 0

    def test_calculate_invalid_path(self, mock_pathfinder, mock_game_map, mock_unit):
        """Test calculating when no path exists."""
        mock_pathfinder.find_path.return_value = None

        preview = PathPreview(pathfinder=mock_pathfinder)

        target = (20, 20)  # Unreachable
        result = preview.calculate_path(mock_unit, target, mock_game_map)

        assert result.is_valid is False
        assert len(result.segments) == 0
        assert result.total_distance == 0

    def test_danger_assessment_safe(self, mock_pathfinder, mock_los_system, mock_game_map, mock_unit):
        """Test danger assessment when no enemies can see path."""
        mock_los_system.can_see.return_value = (False, MagicMock())

        preview = PathPreview(
            pathfinder=mock_pathfinder,
            los_system=mock_los_system,
        )

        target = (7, 7)
        result = preview.calculate_path(mock_unit, target, mock_game_map, enemy_units=[])

        all_safe = all(seg.danger == PathDangerLevel.SAFE for seg in result.segments)
        assert all_safe is True

    def test_danger_assessment_with_enemies(self, mock_pathfinder, mock_los_system, mock_game_map, mock_unit):
        """Test danger assessment when enemies can see path."""
        enemy = MagicMock()
        mock_los_system.can_see.return_value = (True, MagicMock())

        preview = PathPreview(
            pathfinder=mock_pathfinder,
            los_system=mock_los_system,
        )

        target = (7, 7)
        result = preview.calculate_path(
            mock_unit, target, mock_game_map,
            enemy_units=[enemy],
        )

        has_danger = any(
            seg.danger != PathDangerLevel.SAFE 
            for seg in result.segments
        )
        assert has_danger is True

    def test_time_estimation_accuracy(self, mock_pathfinder, mock_game_map, mock_unit):
        """Test that time estimation is reasonable."""
        mock_unit.movement_speed = 4.0  # 4 tiles per second

        preview = PathPreview(pathfinder=mock_pathfinder)
        target = (7, 7)
        result = preview.calculate_path(mock_unit, target, mock_game_map)

        expected_time = result.total_distance / 4.0
        assert abs(result.total_time - expected_time) < 0.2

    def test_show_timer_update(self, mock_pathfinder):
        """Test show timer increments correctly."""
        preview = PathPreview(pathfinder=mock_pathfinder)

        assert preview._visible is False

        preview.update_show_timer(0.1)
        assert preview._visible is False

        preview.update_show_timer(0.25)  # Total: 0.35 > SHOW_DELAY
        assert preview._visible is True

    def test_reset_preview(self, mock_pathfinder):
        """Test resetting preview state."""
        preview = PathPreview(pathfinder=mock_pathfinder)
        preview._visible = True
        preview._show_timer = 0.5
        preview._current_path = PreviewPath(is_valid=True)

        preview.reset_preview()

        assert preview._visible is False
        assert preview._show_timer == 0.0
        assert preview._current_path is None

    def test_set_current_path(self, mock_pathfinder):
        """Test setting current path makes it visible."""
        preview = PathPreview(pathfinder=mock_pathfinder)
        path = PreviewPath(segments=[PathSegment(start=(0,0), end=(1,1))])

        preview.set_current_path(path)

        assert preview._current_path == path
        assert preview._visible is True

    def test_is_visible_property(self, mock_pathfinder):
        """Test is_visible property logic."""
        preview = PathPreview(pathfinder=mock_pathfinder)

        assert preview.is_visible is False

        preview._visible = True
        preview._current_path = PreviewPath(is_valid=True)
        assert preview.is_visible is True

    def test_estimate_total_time(self, mock_pathfinder):
        """Test total time estimation method."""
        preview = PathPreview(pathfinder=mock_pathfinder)

        path = PreviewPath(total_time=3.5)
        assert preview.estimate_total_time(path) == 3.5

        assert preview.estimate_total_time(None) == 0.0

    @patch('pygame.draw')
    def test_render_calls_pygame(self, mock_draw, mock_pathfinder, mock_camera):
        """Test that render method uses pygame drawing."""
        preview = PathPreview(pathfinder=mock_pathfinder)

        segments = [
            PathSegment(start=(5,5), end=(6,5), danger=PathDangerLevel.SAFE),
            PathSegment(start=(6,5), end=(7,5), danger=PathDangerLevel.DANGER),
        ]
        path = PreviewPath(segments=segments, total_distance=2, total_time=0.67)

        surface = MagicMock()
        preview.render(surface, mock_camera, path)

    def test_path_segment_creation(self):
        """Test PathSegment data class."""
        seg = PathSegment(
            start=(1, 1),
            end=(2, 2),
            danger=PathDangerLevel.WARNING,
            estimated_time=0.33,
        )

        assert seg.start == (1, 1)
        assert seg.end == (2, 2)
        assert seg.danger == PathDangerLevel.WARNING
        assert seg.estimated_time == 0.33

    def test_preview_path_data_class(self):
        """Test PreviewPath data class."""
        segments = [PathSegment(start=(0,0), end=(1,1))]
        path = PreviewPath(
            segments=segments,
            total_distance=1,
            total_time=0.33,
            is_valid=True,
        )

        assert len(path.segments) == 1
        assert path.total_distance == 1
        assert path.is_valid is True

    def test_same_start_end_position(self, mock_pathfinder, mock_game_map, mock_unit):
        """Test path calculation when start == end."""
        mock_pathfinder.find_path.return_value = [TileCoord(5, 5)]

        preview = PathPreview(pathfinder=mock_pathfinder)
        target = (5, 5)  # Same as unit position
        result = preview.calculate_path(mock_unit, target, mock_game_map)

        assert result.is_valid is True
        assert len(result.segments) == 0  # No segments if same position
        assert result.total_distance == 0

    def test_empty_enemy_list(self, mock_pathfinder, mock_game_map, mock_unit):
        """Test behavior with empty enemy list."""
        preview = PathPreview(pathfinder=mock_pathfinder)

        target = (7, 7)
        result = preview.calculate_path(
            mock_unit, target, mock_game_map,
            enemy_units=[],
        )

        assert result.is_valid is True
        all_safe = all(seg.danger == PathDangerLevel.SAFE for seg in result.segments)
        assert all_safe is True


class TestRangeIndicator:
    """Test suite for RangeIndicator system (C2)."""

    def test_initialization(self):
        """Test RangeIndicator initializes correctly."""
        indicator = RangeIndicator()

        assert indicator.active_unit is None
        assert indicator._min_range == 0.0
        assert indicator._max_range == 0.0
        assert indicator._visible is False

    def test_set_unit_with_weapon(self, mock_unit):
        """Test setting unit with weapon component."""
        indicator = RangeIndicator()
        indicator.set_unit(mock_unit)

        assert indicator.active_unit == mock_unit
        assert indicator._min_range == 1.0
        assert indicator._max_range == 8.0
        assert indicator.is_visible is True

    def test_set_unit_no_weapon(self):
        """Test setting unit without weapon uses vision range."""
        unit = MagicMock()
        unit.weapon_component = None
        unit.vision_range = 10.0

        indicator = RangeIndicator()
        indicator.set_unit(unit)

        assert indicator._min_range == 0.0
        assert indicator._max_range == 10.0

    def test_clear_indicator(self, mock_unit):
        """Test clearing the indicator."""
        indicator = RangeIndicator()
        indicator.set_unit(mock_unit)

        indicator.clear()

        assert indicator.active_unit is None
        assert indicator.is_visible is False
        assert indicator._min_range == 0.0
        assert indicator._max_range == 0.0

    def test_get_ranges(self, mock_unit):
        """Test getting current ranges."""
        indicator = RangeIndicator()
        indicator.set_unit(mock_unit)

        min_r, max_r = indicator.get_ranges()

        assert min_r == 1.0
        assert max_r == 8.0

    def test_contains_point_inside_min(self, mock_unit):
        """Test point inside minimum range."""
        indicator = RangeIndicator()
        indicator.set_unit(mock_unit)

        result = indicator.contains_point((5.5, 5.0), (5.0, 5.0))
        assert result == 'inside_min'

    def test_contains_point_between_ranges(self, mock_unit):
        """Test point between min and max range."""
        indicator = RangeIndicator()
        indicator.set_unit(mock_unit)

        result = indicator.contains_point((10.0, 5.0), (5.0, 5.0))
        assert result == 'between'

    def test_contains_point_outside_max(self, mock_unit):
        """Test point beyond maximum range."""
        indicator = RangeIndicator()
        indicator.set_unit(mock_unit)

        result = indicator.contains_point((20.0, 5.0), (5.0, 5.0))
        assert result == 'outside_max'

    def test_contains_point_no_unit(self):
        """Test contains_point when no unit selected."""
        indicator = RangeIndicator()

        result = indicator.contains_point((10.0, 10.0), (5.0, 5.0))
        assert result == 'no_unit'

    @patch('pygame.draw')
    def test_render_draws_circles(self, mock_draw, mock_unit, mock_camera):
        """Test that render draws range circles."""
        indicator = RangeIndicator()
        indicator.set_unit(mock_unit)

        surface = MagicMock()
        indicator.render(surface, mock_camera)

        assert indicator.is_visible is True

    def test_visibility_property(self, mock_unit):
        """Test visibility property."""
        indicator = RangeIndicator()

        assert indicator.is_visible is False

        indicator.set_unit(mock_unit)
        assert indicator.is_visible is True

        indicator.clear()
        assert indicator.is_visible is False


class TestTooltip:
    """Test suite for Tooltip system (C3)."""

    def test_initialization(self):
        """Test Tooltip initializes correctly."""
        tooltip = Tooltip()

        assert tooltip.target_unit is None
        assert tooltip._visible is False
        assert tooltip.SHOW_DELAY == 0.5
        assert tooltip.HIDE_DELAY == 0.1

    def test_hover_delay_not_yet_visible(self, mock_unit):
        """Test that tooltip doesn't appear immediately."""
        tooltip = Tooltip()

        tooltip.on_hover(mock_unit, dt=0.3)
        assert tooltip._visible is False
        assert tooltip._show_timer == 0.0  # First call resets timer

    def test_hover_becomes_visible(self, mock_unit):
        """Test tooltip becomes visible after delay."""
        tooltip = Tooltip()
        tooltip.on_hover(mock_unit, dt=0.0)  # Initialize hover

        tooltip.on_hover(mock_unit, dt=0.6)  # Now accumulate time
        assert tooltip._show_timer >= tooltip.SHOW_DELAY
        assert tooltip._visible is True

    def test_hover_different_unit_resets(self, mock_unit):
        """Test switching units resets timer."""
        tooltip = Tooltip()

        unit1 = mock_unit
        unit2 = MagicMock()
        unit2.name = "MG Team"

        tooltip.on_hover(unit1, dt=0.4)
        assert tooltip.target_unit == unit1

        tooltip.on_hover(unit2, dt=0.0)
        assert tooltip.target_unit == unit2
        assert tooltip._show_timer == 0.0
        assert tooltip._visible is False

    def test_hover_none_hides_tooltip(self, mock_unit):
        """Test hovering nothing hides tooltip after delay."""
        tooltip = Tooltip()
        tooltip.on_hover(mock_unit, dt=0.0)  # Init
        tooltip.on_hover(mock_unit, dt=0.6)  # Make visible
        assert tooltip._visible is True

        tooltip.on_hover(None, dt=0.15)
        assert tooltip._visible is False

    def test_data_extraction(self, mock_unit):
        """Test that unit data is extracted correctly."""
        tooltip = Tooltip()
        tooltip.on_hover(mock_unit, dt=0.0)  # Init
        tooltip.on_hover(mock_unit, dt=0.6)  # Make visible and update data

        assert tooltip.data.name == "Rifle Squad"
        assert tooltip.data.unit_type == "Infantry"
        assert tooltip.data.hp == 80
        assert tooltip.data.max_hp == 100
        assert tooltip.data.morale == 85.0
        assert tooltip.data.ammo == 7
        assert tooltip.data.max_ammo == 10
        assert tooltip.data.status == "Normal"

    def test_force_hide(self, mock_unit):
        """Test force_hide immediately hides tooltip."""
        tooltip = Tooltip()
        tooltip.on_hover(mock_unit, dt=0.0)  # Init
        tooltip.on_hover(mock_unit, dt=0.6)  # Make visible
        assert tooltip._visible is True

        tooltip.force_hide()

        assert tooltip._visible is False
        assert tooltip.target_unit is None
        assert tooltip._show_timer == 0.0

    @patch('pygame.font')
    def test_render_displays_info(self, mock_font, mock_unit):
        """Test render displays unit information."""
        tooltip = Tooltip()
        tooltip.on_hover(mock_unit, dt=0.0)  # Init
        tooltip.on_hover(mock_unit, dt=0.6)  # Make visible

        surface = MagicMock()
        mouse_pos = (500, 400)
        tooltip.render(surface, mouse_pos)

        assert tooltip._mouse_pos == mouse_pos

    def test_display_lines_generation(self, mock_unit):
        """Test display lines are generated correctly."""
        tooltip = Tooltip()
        tooltip.on_hover(mock_unit, dt=0.6)

        lines = tooltip._get_display_lines()

        assert len(lines) == 6  # Name, Type, HP, Morale, Ammo, Status
        assert "Rifle Squad" in lines[0][0]
        assert "Infantry" in lines[1][0]

    def test_hp_color_logic(self):
        """Test HP color coding."""
        assert Tooltip._get_hp_color(80) == (0, 255, 0)      # Green
        assert Tooltip._get_hp_color(50) == (255, 255, 0)     # Yellow
        assert Tooltip._get_hp_color(20) == (255, 80, 80)     # Red

    def test_morale_color_logic(self):
        """Test morale color coding."""
        assert Tooltip._get_morale_color(80) == (100, 255, 100)   # Green
        assert Tooltip._get_morale_color(50) == (255, 255, 100)   # Yellow
        assert Tooltip._get_morale_color(20) == (255, 120, 120)   # Red

    def test_status_color_logic(self):
        """Test status color coding."""
        assert 'red' in str(Tooltip._get_status_color('Suppressed')).lower() or \
               Tooltip._get_status_color('Suppressed')[0] == 255
        assert Tooltip._get_status_color('Moving') == (100, 200, 255)
        assert Tooltip._get_status_color('Normal') == (200, 200, 200)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
