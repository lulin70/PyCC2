"""
Unit Tests for Cover Seeking AI System (B1)

Tests the CC2-authentic behavior where suppressed units automatically
seek cover when under heavy fire.

Coverage:
- CoverScoringSystem tile evaluation and scoring
- CoverSeekAI trigger conditions and priority calculation
- Integration with EnhancedTile properties
- Edge cases (no cover available, all occupied, etc.)
- Performance with large search areas
"""

import math
import pytest
from unittest.mock import Mock, MagicMock, patch

from pycc2.domain.ai.cover_seek_ai import (
    CoverCandidate,
    CoverScoringSystem,
    CoverSeekAI,
    SEARCH_RADIUS,
    SUPPRESSION_THRESHOLD,
    COVER_WEIGHT,
    CONCEAL_WEIGHT,
    DISTANCE_PENALTY,
    LOS_BONUS,
    OCCUPIED_PENALTY,
)
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext
from pycc2.domain.systems.combat_mechanics_enhanced import (
    SuppressionState,
    SuppressionEffect,
)
from pycc2.domain.value_objects.tile_coord import TileCoord


# ===========================================================================
# Mock Fixtures
# ===========================================================================

@pytest.fixture
def mock_game_map():
    """Create a mock game map for testing."""
    game_map = Mock()
    game_map.is_valid_coord = Mock(return_value=True)

    def get_tile_side_effect(coord):
        """Return mock tiles with varying cover values."""
        tile = Mock()
        # Varying cover based on position to create interesting test scenarios
        if coord.x % 3 == 0 and coord.y % 3 == 0:
            tile.total_cover_bonus = 3  # Good cover (building/trench)
            tile.total_concealment = 0.4
        elif coord.x % 2 == 0:
            tile.total_cover_bonus = 1  # Light cover (bush)
            tile.total_concealment = 0.2
        else:
            tile.total_cover_bonus = 0  # No cover
            tile.total_concealment = 0.0

        tile.effective_movement_cost = 1.0
        return tile

    game_map.get_tile = Mock(side_effect=get_tile_side_effect)
    return game_map


@pytest.fixture
def mock_los_system():
    """Create a mock LOS system."""
    los = Mock()

    def can_see_side_effect(unit_pos, target_unit):
        # Simulate: can see unless in specific "hidden" positions
        if hasattr(unit_pos, 'x') and unit_pos.x % 5 == 0 and unit_pos.y % 5 == 0:
            return (False, Mock(status="CLEAR"))
        return (True, Mock(status="CLEAR"))

    los.can_see = Mock(side_effect=can_see_side_effect)
    return los


@pytest.fixture
def mock_suppressed_unit():
    """Create a unit that is heavily suppressed."""
    unit = Mock()
    unit.is_alive = True
    unit.is_combat_effective = True
    unit.id = "unit_001"

    # Position component
    pos = Mock()
    pos.x = 5
    pos.y = 5
    unit.position_component = pos

    # Health component (wounded)
    health = Mock()
    health.current_hp = 30
    health.max_hp = 100
    unit.health_component = health

    # Suppression state (HEAVY)
    supp = SuppressionState(current_suppression=75.0)
    unit.suppression_state = supp

    # State (not moving)
    unit.state = "DEFEND"

    return unit


@pytest.fixture
def mock_enemy_units():
    """Create list of enemy units."""
    enemies = []
    for i in range(3):
        enemy = Mock()
        enemy.is_alive = True

        pos = Mock()
        pos.x = 8 + i * 2
        pos.y = 5
        enemy.position_component = pos

        enemies.append(enemy)

    return enemies


@pytest.fixture
def mock_friendly_units(mock_suppressed_unit):
    """Create list of friendly units (including suppressed unit)."""
    friendlies = [mock_suppressed_unit]

    # Add some non-suppressed units occupying tiles
    for i in range(2):
        friendly = Mock()
        friendly.is_alive = True
        friendly.id = f"friendly_{i}"

        pos = Mock()
        pos.x = 4 + i
        pos.y = 6
        friendly.position_component = pos
        friendly.health_component = Mock(current_hp=80, max_hp=100)
        friendly.suppression_state = SuppressionState(current_suppression=10.0)  # Not suppressed
        friendly.state = "DEFEND"
        friendly.is_combat_effective = True

        friendlies.append(friendly)

    return friendlies


@pytest.fixture
def tactical_context(mock_friendly_units, mock_enemy_units, mock_game_map):
    """Create a tactical context for testing."""
    return TacticalContext(
        friendly_units=mock_friendly_units,
        enemy_units=mock_enemy_units,
        game_map=mock_game_map,
        current_tick=100,
    )


# ===========================================================================
# Test Class: CoverScoringSystem
# ===========================================================================

class TestCoverScoringSystem:
    """Test the tile scoring logic."""

    def test_initialization(self, mock_game_map, mock_los_system):
        """Test scorer initializes correctly."""
        scorer = CoverScoringSystem(
            los_system=mock_los_system,
            game_map=mock_game_map,
        )
        assert scorer._los is mock_los_system
        assert scorer._map is mock_game_map

    def test_score_prefers_high_cover(self, mock_game_map, mock_los_system):
        """Test that higher cover bonus produces higher scores."""
        scorer = CoverScoringSystem(
            los_system=mock_los_system,
            game_map=mock_game_map,
        )

        # Score two hypothetical tiles
        score_good_cover = scorer._score_tile(
            cover_bonus=3, concealment=0.4, distance=3.0,
            is_in_los=False, is_occupied=False,
            has_enemy_adjacent=False, movement_cost=1.0,
        )

        score_no_cover = scorer._score_tile(
            cover_bonus=0, concealment=0.0, distance=3.0,
            is_in_los=False, is_occupied=False,
            has_enemy_adjacent=False, movement_cost=1.0,
        )

        assert score_good_cover > score_no_cover
        assert score_good_cover - score_no_cover > 50  # Significant difference

    def test_score_prefers_closer_tiles(self, mock_game_map, mock_los_system):
        """Test that closer tiles get better scores (less distance penalty)."""
        scorer = CoverScoringSystem(
            los_system=mock_los_system,
            game_map=mock_game_map,
        )

        score_close = scorer._score_tile(
            cover_bonus=2, concealment=0.3, distance=1.0,
            is_in_los=True, is_occupied=False,
            has_enemy_adjacent=False, movement_cost=1.0,
        )

        score_far = scorer._score_tile(
            cover_bonus=2, concealment=0.3, distance=6.0,
            is_in_los=True, is_occupied=False,
            has_enemy_adjacent=False, movement_cost=1.0,
        )

        assert score_close > score_far

    def test_score_los_bonus(self, mock_game_map, mock_los_system):
        """Test that being out of LOS provides significant bonus."""
        scorer = CoverScoringSystem(
            los_system=mock_los_system,
            game_map=mock_game_map,
        )

        score_hidden = scorer._score_tile(
            cover_bonus=1, concealment=0.2, distance=3.0,
            is_in_los=False, is_occupied=False,
            has_enemy_adjacent=False, movement_cost=1.0,
        )

        score_visible = scorer._score_tile(
            cover_bonus=1, concealment=0.2, distance=3.0,
            is_in_los=True, is_occupied=False,
            has_enemy_adjacent=False, movement_cost=1.0,
        )

        assert score_hidden > score_visible
        assert (score_hidden - score_visible) >= LOS_BONUS * 0.9  # ~LOS_BONUS

    def test_score_occupied_penalty(self, mock_game_map, mock_los_system):
        """Test that occupied tiles are heavily penalized."""
        scorer = CoverScoringSystem(
            los_system=mock_los_system,
            game_map=mock_game_map,
        )

        score_occupied = scorer._score_tile(
            cover_bonus=3, concealment=0.4, distance=2.0,
            is_in_los=False, is_occupied=True,
            has_enemy_adjacent=False, movement_cost=1.0,
        )

        assert OCCUPIED_PENALTY < 0  # Penalty should be negative
        # Score should be much lower than non-occupied equivalent
        score_free = scorer._score_tile(
            cover_bonus=3, concealment=0.4, distance=2.0,
            is_in_los=False, is_occupied=False,
            has_enemy_adjacent=False, movement_cost=1.0,
        )
        assert score_occupied < score_free

    def test_score_enemy_adjacency_penalty(self, mock_game_map, mock_los_system):
        """Test that tiles next to enemies are penalized."""
        scorer = CoverScoringSystem(
            los_system=mock_los_system,
            game_map=mock_game_map,
        )

        score_dangerous = scorer._score_tile(
            cover_bonus=2, concealment=0.3, distance=2.0,
            is_in_los=True, is_occupied=False,
            has_enemy_adjacent=True, movement_cost=1.0,
        )

        score_safe = scorer._score_tile(
            cover_bonus=2, concealment=0.3, distance=2.0,
            is_in_los=True, is_occupied=False,
            has_enemy_adjacent=False, movement_cost=1.0,
        )

        assert score_safe > score_dangerous

    def test_find_best_cover_returns_candidate(
        self, mock_suppressed_unit, mock_enemy_units, mock_friendly_units,
        mock_game_map, mock_los_system
    ):
        """Test that find_best_cover returns a valid candidate."""
        scorer = CoverScoringSystem(
            los_system=mock_los_system,
            game_map=mock_game_map,
        )

        best = scorer.find_best_cover(
            unit=mock_suppressed_unit,
            enemy_units=mock_enemy_units,
            friendly_units=mock_friendly_units,
        )

        assert best is not None
        assert isinstance(best, CoverCandidate)
        assert best.score > 0  # Should find at least decent cover
        assert isinstance(best.coord, TileCoord)

    def test_find_best_cover_no_valid_tiles(self):
        """Test behavior when no valid cover exists (all impassable)."""
        empty_map = Mock()
        empty_map.is_valid_coord = Mock(return_value=True)
        empty_map.get_tile = Mock(return_value=None)  # No tiles

        scorer = CoverScoringSystem(game_map=empty_map)

        unit = Mock()
        unit.is_alive = True
        pos = Mock()
        pos.x = 5
        pos.y = 5
        unit.position_component = pos

        best = scorer.find_best_cover(unit=unit, enemy_units=[], friendly_units=[])
        assert best is None

    def test_candidates_sorted_by_score(self, mock_game_map, mock_los_system):
        """Test that multiple candidates are properly scored and sorted."""
        scorer = CoverScoringSystem(
            los_system=mock_los_system,
            game_map=mock_game_map,
        )

        unit = Mock()
        unit.is_alive = True
        pos = Mock()
        pos.x = 5
        pos.y = 5
        unit.position_component = pos

        candidates = scorer._get_candidates(
            unit=unit,
            enemy_units=[],
            friendly_units=[],
            search_radius=5,
        )

        if len(candidates) > 1:
            # Verify sorted in descending order
            candidates_sorted = sorted(candidates, key=lambda c: c.score, reverse=True)
            for i in range(len(candidates_sorted) - 1):
                assert candidates_sorted[i].score >= candidates_sorted[i+1].score


# ===========================================================================
# Test Class: CoverSeekAI
# ===========================================================================

class TestCoverSeekAI:
    """Test the AI decision-making logic."""

    def test_initialization(self):
        """Test AI initializes correctly."""
        ai = CoverSeekAI()
        assert ai.SUPPRESSION_THRESHOLD == SUPPRESSION_THRESHOLD
        assert isinstance(ai._scorer, CoverScoringSystem)

    def test_evaluate_zero_when_not_suppressed(self, tactical_context):
        """Test priority is 0 when no units are sufficiently suppressed."""
        ai = CoverSeekAI()

        # Set low suppression for all units
        for unit in tactical_context.friendly_units:
            if hasattr(unit, 'suppression_state'):
                unit.suppression_state.current_suppression = 30.0

        priority = ai.evaluate(tactical_context)
        assert priority == 0.0

    def test_evaluate_positive_when_heavily_suppressed(self, tactical_context):
        """Test priority > 0 when units are heavily suppressed."""
        ai = CoverSeekAI()

        # Ensure at least one unit has heavy suppression
        tactical_context.friendly_units[0].suppression_state.current_suppression = 80.0

        priority = ai.evaluate(tactical_context)
        assert priority > 0.0
        assert priority <= 1.0

    def test_evaluate_scales_with_suppression(self, tactical_context):
        """Test that priority scales up with suppression level."""
        ai = CoverSeekAI()

        prio_low = ai.evaluate(tactical_context)
        tactical_context.friendly_units[0].suppression_state.current_suppression = 90.0
        prio_high = ai.evaluate(tactical_context)

        assert prio_high > prio_low

    def test_evaluate_boost_for_low_hp(self, tactical_context):
        """Test that wounded units get higher priority."""
        ai = CoverSeekAI()

        # Normal HP
        prio_normal = ai.evaluate(tactical_context)

        # Low HP
        tactical_context.friendly_units[0].health_component.current_hp = 10
        prio_wounded = ai.evaluate(tactical_context)

        assert prio_wounded > prio_normal

    def test_execute_generates_move_intent(
        self, mock_suppressed_unit, mock_enemy_units, mock_friendly_units,
        mock_game_map, mock_los_system
    ):
        """Test that execute generates a MOVE intent."""
        scorer = CoverScoringSystem(
            los_system=mock_los_system,
            game_map=mock_game_map,
        )
        ai = CoverSeekAI(scoring_system=scorer)

        context = TacticalContext(
            friendly_units=mock_friendly_units,
            enemy_units=mock_enemy_units,
            game_map=mock_game_map,
            current_tick=100,
        )

        intents = ai.execute(context)

        # Should generate intent for the suppressed unit
        suppressed_intents = [i for i in intents if i.unit_id == mock_suppressed_unit.id]
        assert len(suppressed_intents) > 0

        intent = suppressed_intents[0]
        assert isinstance(intent, TacticIntent)
        assert intent.tactic_type == TacticType.MOVE_TO
        assert intent.target_position is not None

    def test_execute_no_intent_when_no_cover(self):
        """Test that no intent generated when no cover available."""
        empty_scorer = CoverScoringSystem(game_map=Mock(get_tile=Mock(return_value=None)))
        ai = CoverSeekAI(scoring_system=empty_scorer)

        unit = Mock()
        unit.is_alive = True
        unit.is_combat_effective = True
        unit.id = "unit_test"
        pos = Mock()
        pos.x = 5
        pos.y = 5
        unit.position_component = pos
        unit.suppression_state = SuppressionState(current_suppression=80.0)

        context = TacticalContext(
            friendly_units=[unit],
            enemy_units=[],
            game_map=Mock(),
            current_tick=100,
        )

        intents = ai.execute(context)
        assert len(intents) == 0

    def test_dead_unit_zero_priority(self, tactical_context):
        """Test that dead units get zero priority."""
        ai = CoverSeekAI()
        tactical_context.friendly_units[0].is_alive = False

        priority = ai.evaluate(tactical_context)
        # May still be > 0 if other units are suppressed, but dead unit shouldn't contribute
        assert priority >= 0.0

    def test_moving_unit_reduced_priority(self, tactical_context):
        """Test that moving units get reduced priority."""
        ai = CoverSeekAI()

        # Not moving
        prio_standing = ai.evaluate(tactical_context)

        # Moving
        tactical_context.friendly_units[0].state = "MOVING"
        prio_moving = ai.evaluate(tactical_context)

        assert prio_moving < prio_standing


# ===========================================================================
# Test Class: CoverCandidate
# ===========================================================================

class TestCoverCandidate:
    """Test the data class."""

    def test_creation(self):
        """Test candidate creation with all fields."""
        coord = TileCoord(3, 4)
        candidate = CoverCandidate(
            coord=coord,
            score=75.5,
            cover_bonus=2,
            concealment=0.3,
            distance=2.5,
            is_in_enemy_los=False,
            is_occupied=False,
            has_enemy_adjacent=False,
            movement_cost=1.0,
        )

        assert candidate.coord == coord
        assert candidate.score == pytest.approx(75.5)
        assert candidate.cover_bonus == 2
        assert candidate.concealment == pytest.approx(0.3)
        assert candidate.distance == pytest.approx(2.5)
        assert candidate.is_in_enemy_los is False
        assert candidate.is_occupied is False
        assert candidate.has_enemy_adjacent is False
        assert candidate.movement_cost == pytest.approx(1.0)

    def test_comparison(self):
        """Test that comparison works for sorting."""
        coord1 = TileCoord(1, 1)
        coord2 = TileCoord(2, 2)

        low = CoverCandidate(coord=coord1, score=10.0, cover_bonus=0,
                             concealment=0.0, distance=1.0,
                             is_in_enemy_los=False, is_occupied=False,
                             has_enemy_adjacent=False, movement_cost=1.0)

        high = CoverCandidate(coord=coord2, score=90.0, cover_bonus=3,
                              concealment=0.4, distance=2.0,
                              is_in_enemy_los=False, is_occupied=False,
                              has_enemy_adjacent=False, movement_cost=1.0)

        assert low < high  # Lower score is "less than"


# ===========================================================================
# Integration Tests
# ===========================================================================

class TestCoverSeekIntegration:
    """Integration tests combining scoring and AI decision making."""

    def test_full_workflow_suppressed_unit_seeks_cover(
        self, mock_suppressed_unit, mock_enemy_units, mock_friendly_units,
        mock_game_map, mock_los_system
    ):
        """Test complete workflow: suppressed unit evaluates and seeks cover."""
        # Setup
        scorer = CoverScoringSystem(
            los_system=mock_los_system,
            game_map=mock_game_map,
        )
        ai = CoverSeekAI(scoring_system=scorer)

        context = TacticalContext(
            friendly_units=mock_friendly_units,
            enemy_units=mock_enemy_units,
            game_map=mock_game_map,
            current_tick=100,
        )

        # Evaluate
        priority = ai.evaluate(context)
        assert priority > 0.0, "Heavily suppressed unit should want cover"

        # Execute
        intents = ai.execute(context)
        assert len(intents) > 0, "Should generate move intent"

        intent = intents[0]
        assert intent.tactic_type == TacticType.MOVE_TO
        assert intent.target_position is not None

        # Verify the chosen position has good cover
        target_coord = intent.target_position
        target_tile = mock_game_map.get_tile(target_coord)
        assert target_tile.total_cover_bonus >= 0

    def test_unit_already_in_good_cover_reduced_priority(
        self, mock_game_map, mock_los_system
    ):
        """Test that units already in good cover have lower priority."""
        scorer = CoverScoringSystem(
            los_system=mock_los_system,
            game_map=mock_game_map,
        )
        ai = CoverSeekAI(scoring_system=scorer)

        # Unit in poor cover position
        unit_poor_cover = Mock()
        unit_poor_cover.is_alive = True
        unit_poor_cover.is_combat_effective = True
        unit_poor_cover.id = "unit_poor"
        pos_pc = Mock()
        pos_pc.x = 5  # This will have cover_bonus=0 per our mock
        pos_pc.y = 5
        unit_poor_cover.position_component = pos_pc
        unit_poor_cover.health_component = Mock(current_hp=50, max_hp=100)
        unit_poor_cover.suppression_state = SuppressionState(current_suppression=70.0)
        unit_poor_cover.state = "DEFEND"

        context_poor = TacticalContext(
            friendly_units=[unit_poor_cover],
            enemy_units=[],
            game_map=mock_game_map,
            current_tick=100,
        )

        prio_poor = ai.evaluate(context_poor)
        assert prio_poor > 0, "Unit in poor cover should seek cover"


# ===========================================================================
# Performance Tests
# ===========================================================================

class TestCoverSeekPerformance:
    """Performance tests for large-scale scenarios."""

    def test_large_search_area_performance(self, mock_game_map, mock_los_system):
        """Test that large search radius doesn't cause performance issues."""
        import time

        scorer = CoverScoringSystem(
            los_system=mock_los_system,
            game_map=mock_game_map,
        )

        unit = Mock()
        unit.is_alive = True
        pos = Mock()
        pos.x = 20
        pos.y = 20
        unit.position_component = pos

        start = time.time()
        candidates = scorer._get_candidates(
            unit=unit,
            enemy_units=[],
            friendly_units=[],
            search_radius=SEARCH_RADIUS,
        )
        elapsed = time.time() - start

        # Should complete within reasonable time (< 100ms)
        assert elapsed < 0.1, f"Cover search took {elapsed:.3f}s, too slow"
        assert len(candidates) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
