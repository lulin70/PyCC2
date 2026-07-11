"""Unit tests for P3-3: Foxhole/Trench terrain type verification.

Tests that FOXHOLE and TRENCH terrain types have correct properties for
CC2 authentic infantry combat: cover bonus, concealment, movement cost,
LOS blocking, passability, and combat integration.

CC2 Rules:
  Foxhole: dug by infantry, cover_bonus=0.30, concealment=0.25, SOFT cover
  Trench: deeper entrenchment, cover_bonus=0.40, concealment=0.35, SOFT cover
  Both: passable by infantry & vehicles, do not block LOS, height=0
"""

from __future__ import annotations

import time

import pytest

from pycc2.domain.value_objects.terrain_type import CoverType, TerrainType

# ===========================================================================
# Happy Path — property values match CC2 spec
# ===========================================================================


class TestFoxholeProperties:
    """Verify FOXHOLE terrain properties."""

    def test_foxhole_cover_bonus(self) -> None:
        """Verify: foxhole provides 30% cover bonus."""
        assert TerrainType.FOXHOLE.cover_bonus == pytest.approx(0.30)

    def test_foxhole_concealment(self) -> None:
        """Verify: foxhole provides 25% concealment."""
        assert TerrainType.FOXHOLE.concealment_modifier == pytest.approx(0.25)

    def test_foxhole_movement_cost(self) -> None:
        """Verify: foxhole has 1.3x movement cost (slightly slows infantry)."""
        assert TerrainType.FOXHOLE.movement_cost == pytest.approx(1.3)

    def test_foxhole_does_not_block_los(self) -> None:
        """Verify: foxhole does not block line of sight."""
        assert TerrainType.FOXHOLE.blocks_los is False

    def test_foxhole_passable_by_infantry(self) -> None:
        """Verify: foxhole is passable by infantry."""
        assert TerrainType.FOXHOLE.is_passable is True

    def test_foxhole_passable_by_vehicle(self) -> None:
        """Verify: foxhole is passable by vehicles (unlike crater)."""
        assert TerrainType.FOXHOLE.is_passable_by_vehicle is True

    def test_foxhole_height_zero(self) -> None:
        """Verify: foxhole has height 0 (ground level, dug in)."""
        assert TerrainType.FOXHOLE.height == 0

    def test_foxhole_cover_type_soft(self) -> None:
        """Verify: foxhole is classified as SOFT cover."""
        assert TerrainType.FOXHOLE.cover_type == CoverType.SOFT

    def test_foxhole_display_name(self) -> None:
        """Verify: foxhole display name."""
        assert TerrainType.FOXHOLE.display_name == "Foxhole"

    def test_foxhole_color_defined(self) -> None:
        """Verify: foxhole has a valid RGB color."""
        r, g, b = TerrainType.FOXHOLE.color
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255


class TestTrenchProperties:
    """Verify TRENCH terrain properties."""

    def test_trench_cover_bonus(self) -> None:
        """Verify: trench provides 40% cover bonus (better than foxhole)."""
        assert TerrainType.TRENCH.cover_bonus == pytest.approx(0.40)

    def test_trench_concealment(self) -> None:
        """Verify: trench provides 35% concealment."""
        assert TerrainType.TRENCH.concealment_modifier == pytest.approx(0.35)

    def test_trench_movement_cost(self) -> None:
        """Verify: trench has 1.5x movement cost (more disruptive than foxhole)."""
        assert TerrainType.TRENCH.movement_cost == pytest.approx(1.5)

    def test_trench_does_not_block_los(self) -> None:
        """Verify: trench does not block line of sight."""
        assert TerrainType.TRENCH.blocks_los is False

    def test_trench_passable_by_infantry(self) -> None:
        """Verify: trench is passable by infantry."""
        assert TerrainType.TRENCH.is_passable is True

    def test_trench_passable_by_vehicle(self) -> None:
        """Verify: trench is passable by vehicles."""
        assert TerrainType.TRENCH.is_passable_by_vehicle is True

    def test_trench_height_zero(self) -> None:
        """Verify: trench has height 0 (ground level)."""
        assert TerrainType.TRENCH.height == 0

    def test_trench_cover_type_soft(self) -> None:
        """Verify: trench is classified as SOFT cover."""
        assert TerrainType.TRENCH.cover_type == CoverType.SOFT

    def test_trench_display_name(self) -> None:
        """Verify: trench display name."""
        assert TerrainType.TRENCH.display_name == "Trench"


# ===========================================================================
# Config — comparative analysis between cover types
# ===========================================================================


class TestCoverComparison:
    """Verify cover bonus ordering between terrain types."""

    def test_trench_better_cover_than_foxhole(self) -> None:
        """Verify: trench provides more cover than foxhole (deeper)."""
        assert TerrainType.TRENCH.cover_bonus > TerrainType.FOXHOLE.cover_bonus

    def test_trench_better_concealment_than_foxhole(self) -> None:
        """Verify: trench provides more concealment than foxhole."""
        assert TerrainType.TRENCH.concealment_modifier > TerrainType.FOXHOLE.concealment_modifier

    def test_foxhole_better_than_crater(self) -> None:
        """Verify: foxhole provides more cover than natural crater."""
        assert TerrainType.FOXHOLE.cover_bonus > TerrainType.CRATER.cover_bonus

    def test_bunker_better_than_trench(self) -> None:
        """Verify: bunker provides more cover than trench (fortified)."""
        assert TerrainType.BUNKER.cover_bonus > TerrainType.TRENCH.cover_bonus

    def test_foxhole_trench_both_soft_cover(self) -> None:
        """Verify: both foxhole and trench are SOFT cover (not HARD)."""
        assert TerrainType.FOXHOLE.cover_type == CoverType.SOFT
        assert TerrainType.TRENCH.cover_type == CoverType.SOFT

    def test_foxhole_trench_do_not_block_los(self) -> None:
        """Verify: neither foxhole nor trench blocks LOS (unlike walls)."""
        assert not TerrainType.FOXHOLE.blocks_los
        assert not TerrainType.TRENCH.blocks_los

    @pytest.mark.parametrize(
        ("terrain", "expected_cover", "expected_concealment"),
        [
            (TerrainType.FOXHOLE, 0.30, 0.25),
            (TerrainType.TRENCH, 0.40, 0.35),
            (TerrainType.CRATER, 0.25, 0.20),
            (TerrainType.BUNKER, 0.60, 0.80),
        ],
    )
    def test_cover_hierarchy(
        self,
        terrain: TerrainType,
        expected_cover: float,
        expected_concealment: float,
    ) -> None:
        """Verify: cover and concealment values for defensive positions."""
        assert terrain.cover_bonus == pytest.approx(expected_cover)
        assert terrain.concealment_modifier == pytest.approx(expected_concealment)


# ===========================================================================
# Boundary — edge cases
# ===========================================================================


class TestBoundaryConditions:
    """Verify boundary conditions for foxhole/trench."""

    def test_cover_bonus_in_valid_range(self) -> None:
        """Verify: cover_bonus is between 0.0 and 1.0."""
        for tt in [TerrainType.FOXHOLE, TerrainType.TRENCH]:
            assert 0.0 <= tt.cover_bonus <= 1.0

    def test_concealment_in_valid_range(self) -> None:
        """Verify: concealment_modifier is between 0.0 and 1.0."""
        for tt in [TerrainType.FOXHOLE, TerrainType.TRENCH]:
            assert 0.0 <= tt.concealment_modifier <= 1.0

    def test_movement_cost_positive(self) -> None:
        """Verify: movement_cost is positive and finite."""
        for tt in [TerrainType.FOXHOLE, TerrainType.TRENCH]:
            assert tt.movement_cost > 0
            assert tt.movement_cost != float("inf")


# ===========================================================================
# Performance — property access latency
# ===========================================================================


class TestPerformance:
    """Verify terrain property access performance."""

    def test_10000_property_lookups_under_50ms(self) -> None:
        """Verify: 10000 property lookups complete in under 50ms."""
        start = time.perf_counter()
        for _ in range(10000):
            _ = TerrainType.FOXHOLE.cover_bonus
            _ = TerrainType.TRENCH.cover_bonus
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 50.0, f"10000 lookups took {elapsed_ms:.1f}ms (expected <50ms)"


# ===========================================================================
# Integration — all 22 terrain types have consistent properties
# ===========================================================================


class TestTerrainConsistency:
    """Verify all terrain types have consistent property definitions."""

    @pytest.mark.parametrize("tt", list(TerrainType))
    def test_all_terrains_have_cover_bonus(self, tt: TerrainType) -> None:
        """Verify: every terrain type has a cover_bonus value."""
        assert 0.0 <= tt.cover_bonus <= 1.0

    @pytest.mark.parametrize("tt", list(TerrainType))
    def test_all_terrains_have_movement_cost(self, tt: TerrainType) -> None:
        """Verify: every terrain type has a movement_cost value."""
        assert tt.movement_cost > 0

    @pytest.mark.parametrize("tt", list(TerrainType))
    def test_all_terrains_have_display_name(self, tt: TerrainType) -> None:
        """Verify: every terrain type has a display name."""
        assert len(tt.display_name) > 0

    @pytest.mark.parametrize("tt", list(TerrainType))
    def test_all_terrains_have_color(self, tt: TerrainType) -> None:
        """Verify: every terrain type has a valid RGB color."""
        r, g, b = tt.color
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255

    @pytest.mark.parametrize("tt", list(TerrainType))
    def test_all_terrains_have_cover_type(self, tt: TerrainType) -> None:
        """Verify: every terrain type has a cover_type classification."""
        assert tt.cover_type in CoverType
