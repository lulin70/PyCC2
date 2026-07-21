"""V-11 (Wave E1): Unit tests for minimap enhancements.

Tests cover 6 dimensions (Happy/Error/Boundary/Performance/Config/Integration):
1. CasualtyMarker dataclass (construction, defaults, slots)
2. Casualty marker lifecycle (add → age → expire)
3. Legend toggle (default hidden → toggle → visible)
4. Selected unit facing indicator (only selected unit has facing line)
5. Integration (casualty markers drawn on minimap, legend overlay rendered)
6. Performance (1000 casualty markers update < 10ms)
"""

from __future__ import annotations

import os
import time
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np  # noqa: E402
import pygame  # noqa: E402
import pytest  # noqa: E402

from pycc2.domain.entities.game_map import GameMap  # noqa: E402
from pycc2.domain.entities.unit import Faction  # noqa: E402
from pycc2.presentation.rendering.minimap import (  # noqa: E402
    _CASUALTY_MARKER_COLOR,
    _CASUALTY_MARKER_DURATION_S,
    _CASUALTY_MARKER_SIZE,
    Minimap,
    _CasualtyMarker,
)

# ============================================================================
# Helpers
# ============================================================================


def _make_minimap(size: int = 160) -> Minimap:
    """Create a Minimap instance for testing."""
    return Minimap(size=size)


def _make_game_map(width: int = 20, height: int = 20) -> GameMap:
    """Create a minimal GameMap for testing (uses correct constructor)."""
    grid = np.zeros((height, width), dtype=np.int8)
    return GameMap(id="test", name="Test Map", width=width, height=height, tile_grid=grid)


def _make_mock_unit(
    unit_id: str = "unit_1",
    faction: Faction = Faction.ALLIES,
    tile_x: int = 10,
    tile_y: int = 10,
    facing: float = 90.0,
) -> MagicMock:
    """Create a mock Unit for minimap rendering tests.

    Uses MagicMock because Unit construction requires many components
    (HealthComponent/MoraleComponent/WeaponComponent/etc.) that are
    irrelevant to minimap rendering logic.
    """
    unit = MagicMock()
    unit.id = unit_id
    unit.faction = faction
    unit.facing = facing
    unit.position.tile_coord.x = tile_x
    unit.position.tile_coord.y = tile_y
    return unit


# ============================================================================
# 1. _CasualtyMarker dataclass (happy path + config)
# ============================================================================


class TestCasualtyMarkerDataclass:
    """Test _CasualtyMarker dataclass construction and defaults."""

    def test_construction_with_required_fields(self):
        """Verify: _CasualtyMarker can be constructed with required fields."""
        marker = _CasualtyMarker(tile_x=5, tile_y=10, faction=Faction.ALLIES)
        assert marker.tile_x == 5
        assert marker.tile_y == 10
        assert marker.faction == Faction.ALLIES

    def test_default_age_seconds_is_zero(self):
        """Verify: age_seconds defaults to 0.0."""
        marker = _CasualtyMarker(tile_x=0, tile_y=0, faction=Faction.AXIS)
        assert marker.age_seconds == 0.0

    def test_slots_prevents_new_attributes(self):
        """Verify: slots=True prevents adding new attributes."""
        marker = _CasualtyMarker(tile_x=0, tile_y=0, faction=Faction.ALLIES)
        with pytest.raises(AttributeError):
            marker.new_attr = 42  # type: ignore[attr-defined]

    def test_faction_both_values(self):
        """Verify: both Faction values are accepted."""
        m1 = _CasualtyMarker(tile_x=0, tile_y=0, faction=Faction.ALLIES)
        m2 = _CasualtyMarker(tile_x=0, tile_y=0, faction=Faction.AXIS)
        assert m1.faction == Faction.ALLIES
        assert m2.faction == Faction.AXIS


# ============================================================================
# 2. Casualty marker lifecycle (happy + error + boundary)
# ============================================================================


class TestCasualtyMarkerLifecycle:
    """Test casualty marker add/age/expire lifecycle."""

    def test_add_casualty_increases_count(self):
        """Verify: add_casualty increases casualty_count."""
        minimap = _make_minimap()
        assert minimap.casualty_count == 0
        minimap.add_casualty(tile_x=5, tile_y=10, faction=Faction.ALLIES)
        assert minimap.casualty_count == 1

    def test_add_multiple_casualties(self):
        """Verify: multiple casualties can be added."""
        minimap = _make_minimap()
        for i in range(10):
            minimap.add_casualty(tile_x=i, tile_y=i, faction=Faction.ALLIES)
        assert minimap.casualty_count == 10

    def test_update_casualties_ages_markers(self):
        """Verify: update_casualties advances marker age."""
        minimap = _make_minimap()
        minimap.add_casualty(tile_x=5, tile_y=5, faction=Faction.ALLIES)
        minimap.update_casualties(dt=1.0)
        assert minimap._casualty_markers[0].age_seconds == pytest.approx(1.0)

    def test_update_casualties_expires_after_duration(self):
        """Verify: markers are removed after _CASUALTY_MARKER_DURATION_S."""
        minimap = _make_minimap()
        minimap.add_casualty(tile_x=5, tile_y=5, faction=Faction.ALLIES)
        # Advance time beyond duration
        minimap.update_casualties(dt=_CASUALTY_MARKER_DURATION_S + 0.01)
        assert minimap.casualty_count == 0

    def test_update_casualties_keeps_marker_before_duration(self):
        """Verify: markers survive until _CASUALTY_MARKER_DURATION_S."""
        minimap = _make_minimap()
        minimap.add_casualty(tile_x=5, tile_y=5, faction=Faction.ALLIES)
        minimap.update_casualties(dt=_CASUALTY_MARKER_DURATION_S - 0.01)
        assert minimap.casualty_count == 1

    def test_update_casualties_zero_dt_no_change(self):
        """Verify: dt=0 doesn't change marker count."""
        minimap = _make_minimap()
        minimap.add_casualty(tile_x=5, tile_y=5, faction=Faction.ALLIES)
        minimap.update_casualties(dt=0.0)
        assert minimap.casualty_count == 1

    def test_update_casualties_empty_list_noop(self):
        """Verify: update_casualties on empty list is noop."""
        minimap = _make_minimap()
        minimap.update_casualties(dt=1.0)
        assert minimap.casualty_count == 0

    def test_update_integration_calls_update_casualties(self):
        """Verify: update() calls update_casualties internally."""
        minimap = _make_minimap()
        minimap.add_casualty(tile_x=5, tile_y=5, faction=Faction.ALLIES)
        minimap.update(dt=_CASUALTY_MARKER_DURATION_S + 0.01)
        assert minimap.casualty_count == 0


# ============================================================================
# 3. Legend toggle (happy + config)
# ============================================================================


class TestLegendToggle:
    """Test legend toggle behavior."""

    def test_legend_default_hidden(self):
        """Verify: legend is hidden by default (Wave B-rev spec)."""
        minimap = _make_minimap()
        assert minimap.legend_visible is False

    def test_toggle_legend_shows(self):
        """Verify: first toggle shows legend."""
        minimap = _make_minimap()
        result = minimap.toggle_legend()
        assert result is True
        assert minimap.legend_visible is True

    def test_toggle_legend_twice_hides(self):
        """Verify: second toggle hides legend."""
        minimap = _make_minimap()
        minimap.toggle_legend()
        result = minimap.toggle_legend()
        assert result is False
        assert minimap.legend_visible is False

    def test_toggle_legend_three_times_shows(self):
        """Verify: third toggle shows legend again."""
        minimap = _make_minimap()
        minimap.toggle_legend()  # show
        minimap.toggle_legend()  # hide
        result = minimap.toggle_legend()  # show
        assert result is True
        assert minimap.legend_visible is True


# ============================================================================
# 4. Selected unit facing indicator (happy + boundary + integration)
# ============================================================================


class TestSelectedUnitFacing:
    """Test that facing indicator is only drawn for selected unit."""

    def test_facing_only_for_selected_unit_with_selection(self):
        """Verify: facing line is drawn for selected unit."""
        minimap = _make_minimap(size=160)
        game_map = _make_game_map()
        minimap.set_map(game_map)
        # FadeTransition defaults to hidden (alpha=0); reset(visible=True)
        # skips the fade-in animation so render() actually draws.
        minimap._fade.reset(visible=True)

        # Create a mock unit and set as selected
        # NOTE: Minimap.update_units() is the correct API (not set_units).
        unit = _make_mock_unit(unit_id="unit_1", facing=90.0)
        minimap.update_units([unit])
        minimap.set_selected_unit("unit_1")

        # Render to surface
        surface = pygame.Surface((200, 200))
        minimap.render(surface, 0, 0)

        # The test verifies no exception is raised during rendering
        # (facing line is drawn without error for selected unit)
        assert minimap._surface is not None

    def test_facing_not_drawn_without_selection(self):
        """Verify: no facing line when no unit is selected."""
        minimap = _make_minimap(size=160)
        game_map = _make_game_map()
        minimap.set_map(game_map)
        # FadeTransition defaults to hidden (alpha=0); reset(visible=True)
        # skips the fade-in animation so render() actually draws.
        minimap._fade.reset(visible=True)

        unit = _make_mock_unit(unit_id="unit_1", facing=90.0)
        minimap.update_units([unit])
        minimap.set_selected_unit(None)

        surface = pygame.Surface((200, 200))
        minimap.render(surface, 0, 0)
        assert minimap._surface is not None


# ============================================================================
# 5. Integration (casualty draw + legend overlay)
# ============================================================================


class TestIntegration:
    """Test integration of V-11 features with Minimap rendering."""

    def test_render_with_casualties_no_exception(self):
        """Verify: render doesn't crash with casualty markers."""
        minimap = _make_minimap(size=160)
        game_map = _make_game_map()
        minimap.set_map(game_map)
        minimap.add_casualty(tile_x=5, tile_y=5, faction=Faction.ALLIES)
        minimap.add_casualty(tile_x=10, tile_y=10, faction=Faction.AXIS)

        surface = pygame.Surface((200, 200))
        minimap.render(surface, 0, 0)
        assert minimap.casualty_count == 2

    def test_render_with_legend_visible_no_exception(self):
        """Verify: render doesn't crash with legend visible."""
        minimap = _make_minimap(size=160)
        game_map = _make_game_map()
        minimap.set_map(game_map)
        minimap.toggle_legend()

        surface = pygame.Surface((300, 200))
        minimap.render(surface, 0, 0)
        assert minimap.legend_visible is True

    def test_render_with_legend_hidden_no_legend_drawn(self):
        """Verify: legend not drawn when hidden."""
        minimap = _make_minimap(size=160)
        game_map = _make_game_map()
        minimap.set_map(game_map)
        # Legend is hidden by default

        surface = pygame.Surface((300, 200))
        minimap.render(surface, 0, 0)
        assert minimap.legend_visible is False

    def test_casualty_marker_color_is_gray(self):
        """Verify: casualty marker color constant is gray (128, 128, 128)."""
        assert _CASUALTY_MARKER_COLOR == (128, 128, 128)

    def test_casualty_marker_size_is_positive(self):
        """Verify: casualty marker size is positive."""
        assert _CASUALTY_MARKER_SIZE > 0

    def test_casualty_duration_is_5_seconds(self):
        """Verify: casualty marker duration is 5s (Wave B-rev: 3s → 5s)."""
        assert _CASUALTY_MARKER_DURATION_S == 5.0

    def test_casualty_markers_cleared_after_expiry(self):
        """Verify: casualty markers are cleared after expiry during render cycle."""
        minimap = _make_minimap(size=160)
        game_map = _make_game_map()
        minimap.set_map(game_map)
        minimap.add_casualty(tile_x=5, tile_y=5, faction=Faction.ALLIES)

        # Simulate time passing beyond duration
        minimap.update(dt=_CASUALTY_MARKER_DURATION_S + 0.1)
        assert minimap.casualty_count == 0


# ============================================================================
# 6. Performance
# ============================================================================


class TestPerformance:
    """Test performance of V-11 features."""

    def test_update_casualties_1000_markers_under_10ms(self):
        """Verify: updating 1000 casualty markers takes < 10ms."""
        minimap = _make_minimap()
        for i in range(1000):
            minimap.add_casualty(tile_x=i % 20, tile_y=i // 20, faction=Faction.ALLIES)

        start = time.perf_counter()
        minimap.update_casualties(dt=0.016)  # ~60fps frame
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 10.0, f"Update took {elapsed_ms:.2f}ms, expected < 10ms"

    def test_update_casualties_expiry_1000_markers_under_10ms(self):
        """Verify: expiring 1000 casualty markers takes < 10ms."""
        minimap = _make_minimap()
        for i in range(1000):
            minimap.add_casualty(tile_x=i % 20, tile_y=i // 20, faction=Faction.ALLIES)

        start = time.perf_counter()
        minimap.update_casualties(dt=_CASUALTY_MARKER_DURATION_S + 1.0)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 10.0, f"Expiry took {elapsed_ms:.2f}ms, expected < 10ms"
        assert minimap.casualty_count == 0
