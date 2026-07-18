"""Integration tests for range_indicator wiring into Minimap.

Verifies the v0.7.6 INTEGRATE of RangeIndicator:
  - set_unit(unit) computes _min_range/_max_range from weapon + vision
  - set_unit(None) clears state (boundary)
  - Minimap.set_selected_unit triggers range_indicator.set_unit (integration)
  - Minimap.render() draws range circles without error
  - range_indicator=None preserves backward compatibility

These are integration tests — they use the real RangeIndicator, Minimap,
GameMap, and Unit classes. Only the weapon_component is occasionally stubbed
to exercise the explicit min_range/max_range code path (real WeaponComponent
does not declare those attributes, so the default-via-vision_range fallback
is the production path).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pygame

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.presentation.rendering.minimap import Minimap
from pycc2.presentation.rendering.range_indicator import RangeIndicator

# ============================================================================
# Test fixtures
# ============================================================================


@dataclass
class _StubWeaponWithRanges:
    """Weapon-like stub that exposes explicit min_range/max_range attributes.

    Real WeaponComponent does not declare these, so RangeIndicator's
    ``getattr(...)`` falls back to 0.0 and then to vision_range. This stub
    exercises the alternate branch where the weapon itself provides ranges.
    """

    min_range: float = 2.0
    max_range: float = 8.0


@dataclass
class _StubUnitForRanges:
    """Minimal Unit stub exposing the attributes RangeIndicator queries.

    Used only for the explicit-ranges happy-path test where a real Unit
    (whose WeaponComponent lacks min_range/max_range) cannot exercise the
    branch. All other tests use real Unit instances.
    """

    id: str
    position_component: Any
    weapon_component: Any
    vision_range: int = 6


def _make_unit(
    unit_id: str,
    tile_x: int,
    tile_y: int,
    *,
    faction: Faction = Faction.ALLIES,
    vision_range: int = 6,
) -> Unit:
    """Build a real INFANTRY_SQUAD Unit at the given tile coordinate."""
    return Unit(
        id=unit_id,
        name=f"Test {unit_id}",
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
        vision=VisionComponent(range_tiles=vision_range),
        health=HealthComponent(hp=100, max_hp=100),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
        morale=MoraleComponent(value=75),
    )


def _make_open_map(width: int = 10, height: int = 10) -> GameMap:
    """Build a real GameMap of all-OPEN passable terrain."""
    grid = np.zeros((height, width), dtype=np.int8)
    return GameMap(id="test", name="Test Map", width=width, height=height, tile_grid=grid)


def _make_minimap_with_indicator(
    game_map: GameMap | None = None,
) -> tuple[Minimap, RangeIndicator]:
    """Build a Minimap with a RangeIndicator wired in.

    Returns (minimap, indicator) so the test can assert on indicator state.
    """
    game_map = game_map or _make_open_map()
    minimap = Minimap(display_config=None, size=100)
    minimap.set_map(game_map)
    indicator = RangeIndicator()
    minimap.set_range_indicator(indicator)
    return minimap, indicator


# ============================================================================
# Happy Path — set_unit computes ranges
# ============================================================================


class TestRangeIndicatorHappyPath:
    """set_unit(unit) populates _min_range/_max_range correctly."""

    def test_set_unit_with_real_unit_uses_vision_range_fallback(self):
        """Real Unit (WeaponComponent has no min/max_range) → fallback to vision_range."""
        unit = _make_unit("u1", 3, 3, vision_range=6)
        indicator = RangeIndicator()

        indicator.set_unit(unit)

        assert indicator.active_unit is unit
        assert indicator.is_visible is True
        # WeaponComponent has no min_range/max_range → both default to 0.0,
        # then max_range falls back to unit.vision_range (6).
        assert indicator._min_range == 0.0
        assert indicator._max_range == 6.0
        assert indicator.get_ranges() == (0.0, 6.0)

    def test_set_unit_with_explicit_weapon_ranges(self):
        """Stub weapon with min_range/max_range → those values are used directly."""
        unit = _StubUnitForRanges(
            id="u2",
            position_component=PositionComponent(tile_coord=TileCoord(2, 2)),
            weapon_component=_StubWeaponWithRanges(min_range=2.0, max_range=8.0),
            vision_range=6,
        )
        indicator = RangeIndicator()

        indicator.set_unit(unit)

        assert indicator.is_visible is True
        assert indicator._min_range == 2.0
        assert indicator._max_range == 8.0  # not the vision_range fallback
        assert indicator.get_ranges() == (2.0, 8.0)


# ============================================================================
# Boundary — None and edge cases
# ============================================================================


class TestRangeIndicatorBoundary:
    """Edge cases: None unit, clear(), visibility."""

    def test_set_unit_none_clears_state(self):
        """set_unit(None) clears visibility and resets ranges to 0.0."""
        unit = _make_unit("u1", 3, 3)
        indicator = RangeIndicator()
        indicator.set_unit(unit)
        assert indicator.is_visible is True  # precondition

        indicator.set_unit(None)

        assert indicator.active_unit is None
        assert indicator.is_visible is False
        assert indicator._min_range == 0.0
        assert indicator._max_range == 0.0

    def test_clear_resets_state(self):
        """clear() resets all state even after a unit was set."""
        unit = _make_unit("u1", 3, 3)
        indicator = RangeIndicator()
        indicator.set_unit(unit)
        assert indicator.is_visible is True

        indicator.clear()

        assert indicator.active_unit is None
        assert indicator._visible is False
        assert indicator._min_range == 0.0
        assert indicator._max_range == 0.0
        assert indicator.is_visible is False

    def test_contains_point_returns_no_unit_when_inactive(self):
        """contains_point returns 'no_unit' when no unit is active."""
        indicator = RangeIndicator()
        result = indicator.contains_point((1.0, 1.0), (0.0, 0.0))
        assert result == "no_unit"


# ============================================================================
# Integration — Minimap rendering and selection sync
# ============================================================================


class TestRangeIndicatorIntegration:
    """Integration with Minimap: rendering and selected_unit sync."""

    def test_minimap_render_with_range_indicator_no_error(self):
        """Minimap.render() with an active range_indicator does not raise."""
        game_map = _make_open_map()
        unit = _make_unit("u1", 5, 5, vision_range=4)
        minimap, indicator = _make_minimap_with_indicator(game_map)
        minimap.update_units([unit])
        minimap.set_selected_unit("u1")  # triggers indicator.set_unit(unit)

        assert indicator.active_unit is unit
        assert indicator.is_visible is True

        pygame.init()
        try:
            minimap.show()
            minimap.update(0.5)
            screen = pygame.Surface((200, 200))
            minimap.render(screen, 0, 0)
            assert minimap._surface is not None
        finally:
            pygame.quit()

    def test_set_selected_unit_triggers_range_indicator_update(self):
        """Minimap.set_selected_unit pushes the unit to the range_indicator."""
        game_map = _make_open_map()
        unit_a = _make_unit("a", 2, 2, vision_range=5)
        unit_b = _make_unit("b", 7, 7, vision_range=8)
        minimap, indicator = _make_minimap_with_indicator(game_map)
        minimap.update_units([unit_a, unit_b])

        assert indicator.active_unit is None  # precondition

        minimap.set_selected_unit("a")
        assert indicator.active_unit is unit_a
        assert indicator._max_range == 5.0

        minimap.set_selected_unit("b")
        assert indicator.active_unit is unit_b
        assert indicator._max_range == 8.0

        minimap.set_selected_unit(None)
        assert indicator.active_unit is None
        assert indicator.is_visible is False

    def test_set_selected_unit_unknown_id_clears_indicator(self):
        """Selecting an unknown unit_id → indicator.set_unit(None) is called."""
        game_map = _make_open_map()
        unit = _make_unit("u1", 2, 2)
        minimap, indicator = _make_minimap_with_indicator(game_map)
        minimap.update_units([unit])
        minimap.set_selected_unit("u1")
        assert indicator.active_unit is unit

        # Unknown id → lookup returns None → set_unit(None)
        minimap.set_selected_unit("does-not-exist")
        assert indicator.active_unit is None
        assert indicator.is_visible is False


# ============================================================================
# Backward compatibility — range_indicator=None
# ============================================================================


class TestRangeIndicatorBackwardCompat:
    """When range_indicator is None, Minimap operations do not error."""

    def test_set_selected_unit_without_indicator_no_error(self):
        """set_selected_unit does not raise when no indicator is wired."""
        minimap = Minimap(display_config=None, size=50)
        # No set_range_indicator() call → indicator stays None
        assert minimap._range_indicator is None

        # Should not raise
        minimap.set_selected_unit("any-id")

    def test_render_without_indicator_no_error(self):
        """Minimap.render() does not raise when range_indicator is None."""
        game_map = _make_open_map()
        minimap = Minimap(display_config=None, size=50)
        minimap.set_map(game_map)
        # No set_range_indicator() call
        assert minimap._range_indicator is None

        pygame.init()
        try:
            minimap.show()
            minimap.update(0.5)
            screen = pygame.Surface((100, 100))
            minimap.render(screen, 0, 0)
            assert minimap._surface is not None
        finally:
            pygame.quit()
