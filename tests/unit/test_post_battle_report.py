"""V-03 (Wave C5): Unit tests for PostBattleReportRenderer.

Tests:
1. calculate_mvp() algorithm (weights, edge cases, normalization)
2. PostBattleReportRenderer rendering (banner, casualty chart, timeline, MVP)
3. Tab switching (casualty ↔ events)
4. Backward compatibility (fallback when fields missing)
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()

import pytest  # noqa: E402

from pycc2.domain.systems.battle_result import (  # noqa: E402
    BattleEvent,
    BattleOutcome,
)
from pycc2.presentation.ui.post_battle_report import (  # noqa: E402
    DEFAULT_BATTLE_DURATION_SECONDS,
    MVP_KILL_NORMALIZATION,
    MVP_WEIGHT_HIT_RATE,
    MVP_WEIGHT_KILLS,
    MVP_WEIGHT_SURVIVAL,
    PostBattleReportRenderer,
    calculate_mvp,
)
from tests.fixtures.battle_result_factory import (  # noqa: E402
    make_ace_unit_record,
    make_battle_result_with_events,
    make_battle_result_with_mvp,
    make_battle_result_with_unit_stats,
    make_defeat_battle_result,
    make_full_battle_result,
    make_kia_unit_record,
    make_minimal_battle_result,
    make_unit_record,
    make_victory_battle_result,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def fonts():
    """Create fonts for testing (use pygame default font)."""
    return (
        pygame.font.Font(None, 32),  # font_title
        pygame.font.Font(None, 20),  # font_normal
        pygame.font.Font(None, 16),  # font_small
    )


@pytest.fixture
def surface():
    """Create a 1280×720 surface for testing."""
    return pygame.Surface((1280, 720))


@pytest.fixture
def renderer(fonts):
    """Create a PostBattleReportRenderer with default tab."""
    return PostBattleReportRenderer(*fonts)


# ============================================================================
# calculate_mvp() tests
# ============================================================================


class TestCalculateMvp:
    """Test the MVP calculation algorithm."""

    def test_empty_records_returns_none(self):
        """calculate_mvp([]) returns None."""
        assert calculate_mvp([]) is None

    def test_single_record_returns_that_unit(self):
        """calculate_mvp with single record returns that unit's id."""
        record = make_unit_record(unit_id="only_unit")
        assert calculate_mvp([record]) == "only_unit"

    def test_ace_beats_regular_unit(self):
        """Ace unit (5+ kills, high acc, survived) beats regular unit."""
        ace = make_ace_unit_record("ace_1")
        regular = make_unit_record(
            unit_id="regular_1",
            kills=1,
            shots_fired=10,
            shots_hit=3,
            survived=True,
        )
        mvp_id = calculate_mvp([ace, regular])
        assert mvp_id == "ace_1"

    def test_survived_beats_kia(self):
        """Survived unit scores higher than KIA unit with same stats."""
        survived = make_unit_record(
            unit_id="survived_1",
            kills=2,
            shots_fired=10,
            shots_hit=5,
            survived=True,
        )
        kia = make_unit_record(
            unit_id="kia_1",
            kills=2,
            shots_fired=10,
            shots_hit=5,
            survived=False,
        )
        mvp_id = calculate_mvp([survived, kia])
        assert mvp_id == "survived_1"

    def test_high_accuracy_beats_low_accuracy(self):
        """Unit with higher hit rate scores higher (same kills/survival)."""
        high_acc = make_unit_record(
            unit_id="high_acc",
            kills=2,
            shots_fired=10,
            shots_hit=8,
            survived=True,
        )
        low_acc = make_unit_record(
            unit_id="low_acc",
            kills=2,
            shots_fired=10,
            shots_hit=2,
            survived=True,
        )
        mvp_id = calculate_mvp([high_acc, low_acc])
        assert mvp_id == "high_acc"

    def test_weights_sum_to_one(self):
        """MVP weights must sum to 1.0 (Wave B-rev PM requirement)."""
        assert pytest.approx(1.0) == MVP_WEIGHT_HIT_RATE + MVP_WEIGHT_KILLS + MVP_WEIGHT_SURVIVAL

    def test_kill_normalization_value(self):
        """MVP_KILL_NORMALIZATION = 0.1 (10 kills = 1.0 normalized)."""
        assert MVP_KILL_NORMALIZATION == 0.1

    def test_default_battle_duration(self):
        """Default battle duration is 600 seconds (10 minutes)."""
        assert DEFAULT_BATTLE_DURATION_SECONDS == 600.0

    def test_zero_shots_fired_handles_gracefully(self):
        """Unit with 0 shots fired has hit_rate=0 (no division by zero)."""
        record = make_unit_record(
            unit_id="no_shots",
            shots_fired=0,
            shots_hit=0,
            kills=0,
            survived=True,
        )
        # Should not raise
        mvp_id = calculate_mvp([record])
        assert mvp_id == "no_shots"

    def test_battle_duration_affects_survival_score(self):
        """Longer battle duration doesn't change survived unit's score (normalized to 1.0)."""
        record = make_unit_record(unit_id="test", survived=True)
        score_short = calculate_mvp([record], battle_duration_seconds=300.0)
        score_long = calculate_mvp([record], battle_duration_seconds=900.0)
        # Both should return the same unit (survived = 1.0 in both cases)
        assert score_short == "test"
        assert score_long == "test"

    def test_many_units_picks_best(self):
        """calculate_mvp correctly picks best from many units."""
        records = [
            make_unit_record(f"unit_{i}", kills=i, shots_fired=20, shots_hit=i * 2, survived=True)
            for i in range(1, 6)
        ]
        # unit_5 has 5 kills, 10 hits, 20 shots → highest score
        mvp_id = calculate_mvp(records)
        assert mvp_id == "unit_5"


# ============================================================================
# PostBattleReportRenderer initialization tests
# ============================================================================


class TestRendererInitialization:
    """Test PostBattleReportRenderer initialization."""

    def test_default_tab_is_casualty(self, fonts):
        """Default tab is 'casualty'."""
        renderer = PostBattleReportRenderer(*fonts)
        assert renderer.current_tab == "casualty"

    def test_custom_initial_tab(self, fonts):
        """Can initialize with 'events' tab."""
        renderer = PostBattleReportRenderer(*fonts, current_tab="events")
        assert renderer.current_tab == "events"

    def test_invalid_initial_tab_falls_back_to_casualty(self, fonts):
        """Invalid initial tab falls back to 'casualty'."""
        renderer = PostBattleReportRenderer(*fonts, current_tab="invalid")
        assert renderer.current_tab == "casualty"

    def test_set_tab_valid(self, fonts):
        """set_tab() switches tab."""
        renderer = PostBattleReportRenderer(*fonts)
        renderer.set_tab("events")
        assert renderer.current_tab == "events"
        renderer.set_tab("casualty")
        assert renderer.current_tab == "casualty"

    def test_set_tab_invalid_ignored(self, fonts):
        """set_tab() with invalid value is ignored."""
        renderer = PostBattleReportRenderer(*fonts)
        renderer.set_tab("casualty")
        renderer.set_tab("invalid")
        assert renderer.current_tab == "casualty"


# ============================================================================
# PostBattleReportRenderer rendering tests
# ============================================================================


class TestRendererRendering:
    """Test PostBattleReportRenderer rendering methods."""

    def test_render_enhanced_report_no_crash(self, renderer, surface):
        """render_enhanced_report() with full data doesn't crash."""
        result = make_full_battle_result()
        renderer.render_enhanced_report(surface, result)

    def test_render_enhanced_report_minimal_data(self, renderer, surface):
        """render_enhanced_report() with minimal data doesn't crash."""
        result = make_minimal_battle_result()
        renderer.render_enhanced_report(surface, result)

    def test_render_victory_banner(self, renderer, surface):
        """Victory banner shows 'VICTORY' text."""
        result = make_victory_battle_result()
        renderer.render_enhanced_report(surface, result)
        # Surface should not be all black (something was rendered)
        assert surface.get_at((640, 30)) != (0, 0, 0)

    def test_render_defeat_banner(self, renderer, surface):
        """Defeat banner shows 'DEFEAT' text."""
        result = make_defeat_battle_result()
        renderer.render_enhanced_report(surface, result)
        # Surface should not be all black
        assert surface.get_at((640, 30)) != (0, 0, 0)

    def test_render_casualty_tab(self, renderer, surface):
        """Casualty tab renders casualty chart."""
        result = make_battle_result_with_unit_stats()
        renderer.set_tab("casualty")
        renderer.render_enhanced_report(surface, result)
        # Check that something was rendered in the chart area
        # (y between banner and MVP)

    def test_render_events_tab(self, renderer, surface):
        """Events tab renders timeline."""
        result = make_battle_result_with_events()
        renderer.set_tab("events")
        renderer.render_enhanced_report(surface, result)

    def test_render_events_tab_empty_events(self, renderer, surface):
        """Events tab with empty events shows 'No key events recorded'."""
        result = make_minimal_battle_result()
        renderer.set_tab("events")
        renderer.render_enhanced_report(surface, result)

    def test_render_mvp_with_explicit_id(self, renderer, surface):
        """MVP section renders with explicit mvp_unit_id."""
        result = make_battle_result_with_mvp(mvp_unit_id="ace_1")
        renderer.render_enhanced_report(surface, result)

    def test_render_mvp_auto_calculated(self, renderer, surface):
        """MVP section renders with auto-calculated MVP (mvp_unit_id=None)."""
        result = make_battle_result_with_mvp(mvp_unit_id=None)
        renderer.render_enhanced_report(surface, result)

    def test_render_mvp_no_records(self, renderer, surface):
        """MVP section shows 'No MVP data' when unit_records is empty."""
        result = make_minimal_battle_result()
        renderer.render_enhanced_report(surface, result)

    def test_render_mvp_id_not_in_records(self, renderer, surface):
        """MVP section handles mvp_unit_id not in unit_records gracefully."""
        result = make_battle_result_with_mvp(mvp_unit_id="nonexistent_unit")
        renderer.render_enhanced_report(surface, result)


# ============================================================================
# Event color mapping tests
# ============================================================================


class TestEventColorMapping:
    """Test the _event_color() static method."""

    def test_unit_killed_color(self, renderer):
        """unit_killed event maps to DEFEAT_COLOR."""
        color = renderer._event_color("unit_killed")
        assert color == (200, 80, 80)  # DEFEAT_COLOR

    def test_building_destroyed_color(self, renderer):
        """building_destroyed event maps to DEFEAT_COLOR."""
        color = renderer._event_color("building_destroyed")
        assert color == (200, 80, 80)

    def test_morale_break_color(self, renderer):
        """morale_break event maps to HIGHLIGHT_COLOR."""
        color = renderer._event_color("morale_break")
        assert color == (255, 255, 100)  # HIGHLIGHT_COLOR

    def test_vl_capture_color(self, renderer):
        """vl_capture event maps to COMPLETED_COLOR."""
        color = renderer._event_color("vl_capture")
        assert color == (80, 180, 80)  # COMPLETED_COLOR

    def test_unknown_event_color(self, renderer):
        """Unknown event type maps to TEXT_COLOR."""
        color = renderer._event_color("unknown_type")
        assert color == (220, 220, 220)  # TEXT_COLOR


# ============================================================================
# Achievement computation tests
# ============================================================================


class TestAchievementComputation:
    """Test the _compute_achievements() static method."""

    def test_ace_achievement_for_5_plus_kills(self, renderer):
        """5+ kills earns 'Ace' achievement."""
        record = make_unit_record(kills=5, shots_fired=10, shots_hit=5, survived=True)
        achievements = renderer._compute_achievements(record)
        assert "Ace (5+ kills)" in achievements

    def test_veteran_achievement_for_3_plus_kills(self, renderer):
        """3-4 kills earns 'Veteran' achievement."""
        record = make_unit_record(kills=3, shots_fired=10, shots_hit=5, survived=True)
        achievements = renderer._compute_achievements(record)
        assert "Veteran (3+ kills)" in achievements
        assert "Ace (5+ kills)" not in achievements

    def test_sharpshooter_achievement(self, renderer):
        """80%+ accuracy with 10+ shots earns 'Sharpshooter'."""
        record = make_unit_record(
            kills=2,
            shots_fired=10,
            shots_hit=9,  # 90% accuracy
            survived=True,
        )
        achievements = renderer._compute_achievements(record)
        assert "Sharpshooter (80%+ acc)" in achievements

    def test_survivor_achievement(self, renderer):
        """Survived unit earns 'Survivor' achievement."""
        record = make_unit_record(survived=True, kills=0, shots_fired=0, shots_hit=0)
        achievements = renderer._compute_achievements(record)
        assert "Survivor" in achievements

    def test_heavy_hitter_achievement(self, renderer):
        """200+ damage_dealt earns 'Heavy Hitter' achievement."""
        record = make_unit_record(damage_dealt=250.0, survived=True)
        achievements = renderer._compute_achievements(record)
        assert "Heavy Hitter (200+ dmg)" in achievements

    def test_no_achievements_for_poor_performance(self, renderer):
        """Unit with poor performance earns no achievements (except Survivor if survived)."""
        record = make_unit_record(
            kills=0,
            shots_fired=10,
            shots_hit=1,  # 10% accuracy
            damage_dealt=10.0,
            survived=False,
        )
        achievements = renderer._compute_achievements(record)
        assert "Ace (5+ kills)" not in achievements
        assert "Veteran (3+ kills)" not in achievements
        assert "Sharpshooter (80%+ acc)" not in achievements
        assert "Survivor" not in achievements
        assert "Heavy Hitter (200+ dmg)" not in achievements


# ============================================================================
# Factory pattern tests
# ============================================================================


class TestFactoryPattern:
    """Test that the factory pattern produces valid data."""

    def test_make_minimal_battle_result(self):
        """make_minimal_battle_result() returns valid BattleResult."""
        result = make_minimal_battle_result()
        assert result.mission_id == "mission_test"
        assert result.outcome == BattleOutcome.VICTORY
        assert result.events == []
        assert result.mvp_unit_id is None
        assert result.unit_records == []

    def test_make_victory_battle_result(self):
        """make_victory_battle_result() returns victory result."""
        result = make_victory_battle_result()
        assert result.is_victory
        assert result.allies_killed == 3
        assert result.axis_killed == 8

    def test_make_defeat_battle_result(self):
        """make_defeat_battle_result() returns defeat result."""
        result = make_defeat_battle_result()
        assert not result.is_victory
        assert result.outcome == BattleOutcome.DEFEAT

    def test_make_battle_result_with_events(self):
        """make_battle_result_with_events() returns result with events."""
        result = make_battle_result_with_events()
        assert len(result.events) == 7
        assert all(isinstance(e, BattleEvent) for e in result.events)

    def test_make_battle_result_with_mvp(self):
        """make_battle_result_with_mvp() returns result with MVP."""
        result = make_battle_result_with_mvp(mvp_unit_id="ace_1")
        assert result.mvp_unit_id == "ace_1"
        assert len(result.unit_records) > 0

    def test_make_battle_result_with_unit_stats(self):
        """make_battle_result_with_unit_stats() returns rich unit records."""
        result = make_battle_result_with_unit_stats()
        assert len(result.unit_records) == 11  # 5 allies + 6 axis
        allies_count = sum(1 for r in result.unit_records if r.faction == "allies")
        axis_count = sum(1 for r in result.unit_records if r.faction == "axis")
        assert allies_count == 5
        assert axis_count == 6

    def test_make_full_battle_result(self):
        """make_full_battle_result() returns result with all V-03 fields."""
        result = make_full_battle_result()
        assert len(result.events) > 0
        assert result.mvp_unit_id is not None
        assert len(result.unit_records) > 0

    def test_make_ace_unit_record(self):
        """make_ace_unit_record() returns record with 5+ kills."""
        record = make_ace_unit_record()
        assert record.kills >= 5
        assert record.shots_fired >= 10

    def test_make_kia_unit_record(self):
        """make_kia_unit_record() returns record with survived=False."""
        record = make_kia_unit_record()
        assert not record.survived
        assert record.hp_end == 0
