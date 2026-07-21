"""V-03 (Wave C5): Factory for BattleResult test data.

Provides builder functions for various BattleResult scenarios used by
PostBattleReportRenderer tests. Follows the factory pattern (Wave B-rev
Tester suggestion) to keep test data construction DRY and readable.

Reference: docs/VISUAL_POLISH_PLAN.md V-03 章节 (Wave B-rev Tester 建议)
"""

from __future__ import annotations

from pycc2.domain.systems.battle_result import (
    BattleEvent,
    BattleOutcome,
    BattleResult,
    UnitBattleRecord,
)

# ============================================================================
# UnitBattleRecord factories
# ============================================================================


def make_unit_record(
    unit_id: str = "unit_1",
    unit_type: str = "infantry",
    faction: str = "allies",
    survived: bool = True,
    hp_start: int = 100,
    hp_end: int = 80,
    damage_dealt: float = 50.0,
    damage_taken: int = 20,
    kills: int = 2,
    shots_fired: int = 10,
    shots_hit: int = 5,
    xp_gained: int = 100,
) -> UnitBattleRecord:
    """Create a single UnitBattleRecord with sensible defaults."""
    return UnitBattleRecord(
        unit_id=unit_id,
        unit_type=unit_type,
        faction=faction,
        survived=survived,
        hp_start=hp_start,
        hp_end=hp_end,
        damage_dealt=damage_dealt,
        damage_taken=damage_taken,
        kills=kills,
        shots_fired=shots_fired,
        shots_hit=shots_hit,
        xp_gained=xp_gained,
    )


def make_ace_unit_record(unit_id: str = "ace_1", faction: str = "allies") -> UnitBattleRecord:
    """Create an ace unit record (5+ kills, high accuracy, survived)."""
    return make_unit_record(
        unit_id=unit_id,
        unit_type="tank_medium",
        faction=faction,
        survived=True,
        kills=7,
        shots_fired=20,
        shots_hit=16,
        damage_dealt=350.0,
        hp_end=70,
    )


def make_kia_unit_record(unit_id: str = "kia_1", faction: str = "axis") -> UnitBattleRecord:
    """Create a KIA unit record (killed in action)."""
    return make_unit_record(
        unit_id=unit_id,
        unit_type="infantry",
        faction=faction,
        survived=False,
        hp_end=0,
        kills=1,
        shots_fired=8,
        shots_hit=3,
        damage_dealt=15.0,
        damage_taken=100,
    )


# ============================================================================
# BattleEvent factories
# ============================================================================


def make_battle_event(
    event_type: str = "unit_killed",
    timestamp: float = 30.0,
    unit_id: str | None = "unit_1",
    faction: str | None = "allies",
    description: str = "Test event",
) -> BattleEvent:
    """Create a single BattleEvent with sensible defaults."""
    return BattleEvent(
        event_type=event_type,
        timestamp=timestamp,
        unit_id=unit_id,
        faction=faction,
        description=description,
    )


def make_typical_event_list() -> list[BattleEvent]:
    """Create a typical list of 5-10 battle events for timeline tests."""
    return [
        make_battle_event(
            event_type="unit_killed",
            timestamp=15.0,
            unit_id="allies_1",
            faction="allies",
            description="First blood: allies_1 killed enemy_scout",
        ),
        make_battle_event(
            event_type="morale_break",
            timestamp=45.0,
            unit_id="axis_2",
            faction="axis",
            description="axis_2's morale collapsed — BROKEN!",
        ),
        make_battle_event(
            event_type="vl_capture",
            timestamp=120.0,
            unit_id="allies_3",
            faction="allies",
            description="allies_3 captured North Bridge",
        ),
        make_battle_event(
            event_type="building_destroyed",
            timestamp=180.0,
            unit_id="axis_1",
            faction="axis",
            description="axis_1 destroyed allied bunker",
        ),
        make_battle_event(
            event_type="unit_killed",
            timestamp=240.0,
            unit_id="axis_3",
            faction="axis",
            description="axis_3 killed by allied sniper",
        ),
        make_battle_event(
            event_type="bridge_destroyed",
            timestamp=300.0,
            unit_id="axis_4",
            faction="axis",
            description="axis_4 blew up South Bridge",
        ),
        make_battle_event(
            event_type="vl_capture",
            timestamp=420.0,
            unit_id="allies_2",
            faction="allies",
            description="allies_2 captured Church",
        ),
    ]


# ============================================================================
# BattleResult factories
# ============================================================================


def make_minimal_battle_result() -> BattleResult:
    """Create a minimal valid BattleResult (no events, no MVP, no unit_records)."""
    return BattleResult(
        mission_id="mission_test",
        mission_name="Test Mission",
        outcome=BattleOutcome.VICTORY,
        ticks_elapsed=600,
    )


def make_victory_battle_result() -> BattleResult:
    """Create a victory BattleResult with typical stats."""
    return BattleResult(
        mission_id="mission_victory",
        mission_name="Victory at Arnhem",
        outcome=BattleOutcome.VICTORY,
        ticks_elapsed=1200,
        allies_killed=3,
        allies_routed=2,
        axis_killed=8,
        axis_routed=5,
        total_shots_fired_allies=150,
        total_shots_hit_allies=75,
        total_shots_fired_axis=120,
        total_shots_hit_axis=40,
        total_damage_dealt_allies=450.0,
        total_damage_dealt_axis=180.0,
        objectives_completed=3,
        objectives_total=3,
        victory_points=250,
    )


def make_defeat_battle_result() -> BattleResult:
    """Create a defeat BattleResult with typical stats."""
    return BattleResult(
        mission_id="mission_defeat",
        mission_name="Defeat at Nijmegen",
        outcome=BattleOutcome.DEFEAT,
        ticks_elapsed=900,
        allies_killed=7,
        allies_routed=4,
        axis_killed=2,
        axis_routed=1,
        total_shots_fired_allies=80,
        total_shots_hit_allies=20,
        total_shots_fired_axis=200,
        total_shots_hit_axis=120,
        total_damage_dealt_allies=100.0,
        total_damage_dealt_axis=500.0,
        objectives_completed=1,
        objectives_total=3,
        victory_points=0,
    )


def make_battle_result_with_events(events: list[BattleEvent] | None = None) -> BattleResult:
    """Create a BattleResult with events list (for timeline tests)."""
    if events is None:
        events = make_typical_event_list()
    result = make_victory_battle_result()
    result.events = events
    return result


def make_battle_result_with_mvp(
    unit_records: list[UnitBattleRecord] | None = None,
    mvp_unit_id: str | None = None,
) -> BattleResult:
    """Create a BattleResult with MVP unit and detailed unit records.

    If ``mvp_unit_id`` is None, it will be calculated via ``calculate_mvp()``
    when the renderer processes it.
    """
    if unit_records is None:
        unit_records = [
            make_ace_unit_record("ace_1", "allies"),
            make_unit_record("unit_2", "infantry", "allies", kills=1, shots_fired=8, shots_hit=3),
            make_kia_unit_record("kia_1", "axis"),
            make_unit_record("unit_4", "infantry", "axis", kills=0, shots_fired=5, shots_hit=1),
        ]
    result = make_victory_battle_result()
    result.unit_records = unit_records
    result.mvp_unit_id = mvp_unit_id
    return result


def make_battle_result_with_unit_stats() -> BattleResult:
    """Create a BattleResult with rich unit_records (for casualty chart tests)."""
    unit_records = [
        # Allies: 5 total (3 survived, 1 KIA, 1 routed)
        make_unit_record("ally_1", "infantry", "allies", survived=True, kills=2),
        make_unit_record("ally_2", "infantry", "allies", survived=True, kills=1),
        make_unit_record("ally_3", "tank", "allies", survived=True, kills=3),
        make_unit_record("ally_4", "infantry", "allies", survived=False, hp_end=0, kills=0),
        make_unit_record("ally_5", "infantry", "allies", survived=False, hp_end=0, kills=0),
        # Axis: 6 total (1 survived, 4 KIA, 1 routed)
        make_unit_record("axis_1", "infantry", "axis", survived=True, kills=1),
        make_unit_record("axis_2", "infantry", "axis", survived=False, hp_end=0, kills=0),
        make_unit_record("axis_3", "infantry", "axis", survived=False, hp_end=0, kills=0),
        make_unit_record("axis_4", "infantry", "axis", survived=False, hp_end=0, kills=0),
        make_unit_record("axis_5", "infantry", "axis", survived=False, hp_end=0, kills=0),
        make_unit_record("axis_6", "infantry", "axis", survived=False, hp_end=0, kills=0),
    ]
    result = make_victory_battle_result()
    result.unit_records = unit_records
    result.allies_killed = 2  # 2 allies died (ally_4, ally_5)
    result.allies_routed = 0
    result.axis_killed = 5  # 5 axis died
    result.axis_routed = 0
    return result


def make_full_battle_result() -> BattleResult:
    """Create a BattleResult with all V-03 fields populated (events + MVP + unit_records)."""
    result = make_battle_result_with_unit_stats()
    result.events = make_typical_event_list()
    # Pre-calculate MVP for testing
    from pycc2.presentation.ui.post_battle_report import calculate_mvp

    result.mvp_unit_id = calculate_mvp(result.unit_records)
    return result


__all__ = [
    # UnitBattleRecord factories
    "make_unit_record",
    "make_ace_unit_record",
    "make_kia_unit_record",
    # BattleEvent factories
    "make_battle_event",
    "make_typical_event_list",
    # BattleResult factories
    "make_minimal_battle_result",
    "make_victory_battle_result",
    "make_defeat_battle_result",
    "make_battle_result_with_events",
    "make_battle_result_with_mvp",
    "make_battle_result_with_unit_stats",
    "make_full_battle_result",
]
