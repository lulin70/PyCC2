"""Tests for AITickScheduler - hierarchical tick frequencies for AI decision-making."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from pycc2.domain.ai.tick_scheduler import AITickScheduler
from pycc2.domain.entities.unit import UnitType


# ---------------------------------------------------------------------------
# Lightweight mock unit – avoids constructing full Unit with all components
# ---------------------------------------------------------------------------
@dataclass
class MockUnit:
    id: str
    unit_type: UnitType
    squad_id: str | None = None
    is_squad_leader: bool = False
    is_alive: bool = True
    can_act: bool = True


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def scheduler() -> AITickScheduler:
    return AITickScheduler()


@pytest.fixture
def commander() -> MockUnit:
    return MockUnit(id="cmd1", unit_type=UnitType.COMMANDER)


@pytest.fixture
def squad_leader() -> MockUnit:
    return MockUnit(
        id="sl1",
        unit_type=UnitType.INFANTRY_SQUAD,
        squad_id="squad_a",
        is_squad_leader=True,
    )


@pytest.fixture
def regular_unit() -> MockUnit:
    return MockUnit(id="u1", unit_type=UnitType.INFANTRY_SQUAD, squad_id="squad_a")


@pytest.fixture
def lone_unit() -> MockUnit:
    """A unit with no squad_id – definitely a regular unit."""
    return MockUnit(id="u2", unit_type=UnitType.INFANTRY_SQUAD, squad_id=None)


# ===================================================================
# 1. Tick frequency constants
# ===================================================================
class TestTickFrequencyConstants:
    def test_commander_tick_hz(self) -> None:
        assert AITickScheduler.COMMANDER_TICK_HZ == 2

    def test_squad_leader_tick_hz(self) -> None:
        assert AITickScheduler.SQUAD_LEADER_TICK_HZ == 4

    def test_unit_tick_hz(self) -> None:
        assert AITickScheduler.UNIT_TICK_HZ == 8

    def test_game_ticks_per_second(self) -> None:
        assert AITickScheduler.GAME_TICKS_PER_SECOND == 30


# ===================================================================
# 2. _get_tick_hz returns correct frequency per role
# ===================================================================
class TestGetTickHz:
    def test_commander_frequency(self, scheduler: AITickScheduler, commander: MockUnit) -> None:
        assert scheduler._get_tick_hz(commander) == AITickScheduler.COMMANDER_TICK_HZ

    def test_squad_leader_frequency(
        self, scheduler: AITickScheduler, squad_leader: MockUnit
    ) -> None:
        assert scheduler._get_tick_hz(squad_leader) == AITickScheduler.SQUAD_LEADER_TICK_HZ

    def test_regular_unit_frequency(
        self, scheduler: AITickScheduler, regular_unit: MockUnit
    ) -> None:
        assert scheduler._get_tick_hz(regular_unit) == AITickScheduler.UNIT_TICK_HZ

    def test_lone_unit_frequency(self, scheduler: AITickScheduler, lone_unit: MockUnit) -> None:
        assert scheduler._get_tick_hz(lone_unit) == AITickScheduler.UNIT_TICK_HZ

    def test_tank_is_regular_unit(self, scheduler: AITickScheduler) -> None:
        tank = MockUnit(id="t1", unit_type=UnitType.TANK, squad_id="sq1")
        assert scheduler._get_tick_hz(tank) == AITickScheduler.UNIT_TICK_HZ


# ===================================================================
# 3. get_tick_interval
# ===================================================================
class TestGetTickInterval:
    def test_commander_interval(self, scheduler: AITickScheduler, commander: MockUnit) -> None:
        # 30 / 2 = 15
        assert scheduler.get_tick_interval(commander) == 15

    def test_squad_leader_interval(
        self, scheduler: AITickScheduler, squad_leader: MockUnit
    ) -> None:
        # 30 / 4 = 7 (floor)
        assert scheduler.get_tick_interval(squad_leader) == 7

    def test_regular_unit_interval(
        self, scheduler: AITickScheduler, regular_unit: MockUnit
    ) -> None:
        # 30 / 8 = 3 (floor)
        assert scheduler.get_tick_interval(regular_unit) == 3


# ===================================================================
# 4. should_tick
# ===================================================================
class TestShouldTick:
    def test_commander_ticks_at_interval(
        self, scheduler: AITickScheduler, commander: MockUnit
    ) -> None:
        interval = scheduler.get_tick_interval(commander)
        assert scheduler.should_tick(commander, 0) is True
        assert scheduler.should_tick(commander, interval) is True
        assert scheduler.should_tick(commander, interval * 2) is True

    def test_commander_does_not_tick_between_intervals(
        self, scheduler: AITickScheduler, commander: MockUnit
    ) -> None:
        assert scheduler.should_tick(commander, 1) is False
        assert scheduler.should_tick(commander, 7) is False
        assert scheduler.should_tick(commander, 14) is False

    def test_regular_unit_ticks_every_3_ticks(
        self, scheduler: AITickScheduler, regular_unit: MockUnit
    ) -> None:
        assert scheduler.should_tick(regular_unit, 0) is True
        assert scheduler.should_tick(regular_unit, 3) is True
        assert scheduler.should_tick(regular_unit, 6) is True
        assert scheduler.should_tick(regular_unit, 1) is False
        assert scheduler.should_tick(regular_unit, 2) is False

    def test_dead_unit_never_ticks(self, scheduler: AITickScheduler, commander: MockUnit) -> None:
        commander.is_alive = False
        assert scheduler.should_tick(commander, 0) is False

    def test_cannot_act_unit_never_ticks(
        self, scheduler: AITickScheduler, commander: MockUnit
    ) -> None:
        commander.can_act = False
        assert scheduler.should_tick(commander, 0) is False

    def test_tick_zero_always_ticks_for_alive_units(
        self, scheduler: AITickScheduler, regular_unit: MockUnit
    ) -> None:
        assert scheduler.should_tick(regular_unit, 0) is True


# ===================================================================
# 5. get_next_tick
# ===================================================================
class TestGetNextTick:
    def test_next_tick_from_zero(
        self, scheduler: AITickScheduler, commander: MockUnit
    ) -> None:
        assert scheduler.get_next_tick(commander, 0) == 0

    def test_next_tick_mid_interval(
        self, scheduler: AITickScheduler, commander: MockUnit
    ) -> None:
        # Commander interval = 15, at tick 7 next is 15
        assert scheduler.get_next_tick(commander, 7) == 15

    def test_next_tick_exactly_on_interval(
        self, scheduler: AITickScheduler, commander: MockUnit
    ) -> None:
        assert scheduler.get_next_tick(commander, 15) == 15

    def test_next_tick_for_regular_unit(
        self, scheduler: AITickScheduler, regular_unit: MockUnit
    ) -> None:
        # Regular interval = 3
        assert scheduler.get_next_tick(regular_unit, 1) == 3
        assert scheduler.get_next_tick(regular_unit, 2) == 3
        assert scheduler.get_next_tick(regular_unit, 4) == 6


# ===================================================================
# 6. Difficulty modifier
# ===================================================================
class TestDifficultyModifier:
    def test_higher_modifier_reduces_interval(self, commander: MockUnit) -> None:
        normal = AITickScheduler(difficulty_modifier=1.0)
        hard = AITickScheduler(difficulty_modifier=2.0)
        assert hard.get_tick_interval(commander) < normal.get_tick_interval(commander)

    def test_modifier_2x_halves_interval(self, commander: MockUnit) -> None:
        scheduler = AITickScheduler(difficulty_modifier=2.0)
        # Commander: 30 / (2*2) = 7 (floor)
        assert scheduler.get_tick_interval(commander) == 7

    def test_modifier_below_1_increases_interval(self, regular_unit: MockUnit) -> None:
        easy = AITickScheduler(difficulty_modifier=0.5)
        normal = AITickScheduler(difficulty_modifier=1.0)
        assert easy.get_tick_interval(regular_unit) > normal.get_tick_interval(regular_unit)

    def test_modifier_affects_should_tick(self, commander: MockUnit) -> None:
        hard = AITickScheduler(difficulty_modifier=2.0)
        # Commander interval = 7 with 2x modifier
        assert hard.should_tick(commander, 7) is True
        assert hard.should_tick(commander, 14) is True


# ===================================================================
# 7. tick_summary
# ===================================================================
class TestTickSummary:
    def test_summary_structure(
        self,
        scheduler: AITickScheduler,
        commander: MockUnit,
        squad_leader: MockUnit,
        regular_unit: MockUnit,
    ) -> None:
        summary = scheduler.tick_summary([commander, squad_leader, regular_unit], 0)
        assert "tick" in summary
        assert "total_units" in summary
        assert "ticking_ids" in summary
        assert "by_role" in summary
        assert summary["tick"] == 0
        assert summary["total_units"] == 3

    def test_all_tick_at_tick_zero(
        self,
        scheduler: AITickScheduler,
        commander: MockUnit,
        squad_leader: MockUnit,
        regular_unit: MockUnit,
    ) -> None:
        summary = scheduler.tick_summary([commander, squad_leader, regular_unit], 0)
        assert len(summary["ticking_ids"]) == 3

    def test_by_role_classification(
        self,
        scheduler: AITickScheduler,
        commander: MockUnit,
        squad_leader: MockUnit,
        regular_unit: MockUnit,
    ) -> None:
        summary = scheduler.tick_summary([commander, squad_leader, regular_unit], 0)
        assert commander.id in summary["by_role"]["commander"]
        assert squad_leader.id in summary["by_role"]["squad_leader"]
        assert regular_unit.id in summary["by_role"]["unit"]

    def test_dead_units_excluded_from_summary(
        self, scheduler: AITickScheduler, commander: MockUnit, regular_unit: MockUnit
    ) -> None:
        commander.is_alive = False
        summary = scheduler.tick_summary([commander, regular_unit], 0)
        assert commander.id not in summary["ticking_ids"]
        assert regular_unit.id in summary["ticking_ids"]

    def test_partial_tick_only_some_units(
        self,
        scheduler: AITickScheduler,
        commander: MockUnit,
        squad_leader: MockUnit,
        regular_unit: MockUnit,
    ) -> None:
        # At tick 3, regular_unit (interval=3) ticks, commander (interval=15) does not
        summary = scheduler.tick_summary([commander, squad_leader, regular_unit], 3)
        assert regular_unit.id in summary["ticking_ids"]
        assert commander.id not in summary["ticking_ids"]


# ===================================================================
# 8. Edge cases
# ===================================================================
class TestEdgeCases:
    def test_very_high_tick_number(self, scheduler: AITickScheduler, commander: MockUnit) -> None:
        interval = scheduler.get_tick_interval(commander)
        high_tick = interval * 10000
        assert scheduler.should_tick(commander, high_tick) is True
        assert scheduler.should_tick(commander, high_tick + 1) is False

    def test_empty_unit_list_summary(self, scheduler: AITickScheduler) -> None:
        summary = scheduler.tick_summary([], 5)
        assert summary["total_units"] == 0
        assert summary["ticking_ids"] == []
        assert summary["by_role"] == {"commander": [], "squad_leader": [], "unit": []}

    def test_unit_in_squad_but_not_leader_is_regular(
        self, scheduler: AITickScheduler
    ) -> None:
        unit = MockUnit(
            id="u3",
            unit_type=UnitType.MACHINE_GUN_SQUAD,
            squad_id="sq2",
            is_squad_leader=False,
        )
        assert scheduler._get_tick_hz(unit) == AITickScheduler.UNIT_TICK_HZ

    def test_squad_leader_without_squad_id_is_regular(
        self, scheduler: AITickScheduler
    ) -> None:
        unit = MockUnit(
            id="u4",
            unit_type=UnitType.INFANTRY_SQUAD,
            squad_id=None,
            is_squad_leader=True,
        )
        # squad_id is None, so not classified as squad leader
        assert scheduler._get_tick_hz(unit) == AITickScheduler.UNIT_TICK_HZ
