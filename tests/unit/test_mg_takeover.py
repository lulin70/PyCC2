"""Tests for MGTakeoverSystem — MG gunner death and squad member takeover.

Covers TakeoverState lifecycle (IN_PROGRESS/COMPLETED/ABANDONED), replacement
selection, abandonment to FallenUnitCache, and tick advancement.
"""

from __future__ import annotations

import pytest

from pycc2.domain.ai.ammo_pickup import FallenUnitCache
from pycc2.domain.ai.mg_takeover import (
    TAKEOVER_TICKS,
    MGTakeoverSystem,
    TakeoverState,
)
from pycc2.domain.components.health_component import HealthComponent, HealthState
from pycc2.domain.components.morale_component import MoraleComponent, MoraleState
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord


class _StubEventBus:
    """Minimal event bus stub recording publish_named calls."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    def publish(self, event: object) -> None:
        pass

    def subscribe(self, event_type: type, handler: object) -> None:
        pass

    def subscribe_to(self, event_name: str, handler: object) -> None:
        pass

    def publish_named(self, event_name: str, data: dict) -> None:
        self.published.append((event_name, data))


def _make_unit(
    uid: str = "u1",
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    max_hp: int = 100,
    morale_value: int = 80,
    morale_state: MoraleState = MoraleState.RALLIED,
    weapon_id: str = "rifle",
    x: int = 10,
    y: int = 10,
) -> Unit:
    unit = Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=Faction.ALLIES,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale_value, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id=weapon_id, ammo_remaining=8, max_ammo=8),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
    )
    unit.morale.state = morale_state
    return unit


@pytest.mark.unit
class TestMGTakeoverOnGunnerKilled:
    """on_mg_gunner_killed: replacement selection and abandonment."""

    def test_non_mg_unit_returns_none(self):
        """Verify: killing a non-MG unit does not trigger takeover.

        Scenario: dead_gunner is INFANTRY_SQUAD.
        Expected: Returns None, no takeover record created.
        """
        bus = _StubEventBus()
        sys = MGTakeoverSystem(event_bus=bus)
        gunner = _make_unit("g1", UnitType.INFANTRY_SQUAD)
        record = sys.on_mg_gunner_killed(gunner, [])
        assert record is None
        assert sys.active_takeover_count == 0

    def test_mg_gunner_with_nearby_replacement_starts_takeover(self):
        """Verify: MG gunner death with replacement in range starts IN_PROGRESS.

        Scenario: MG gunner dies, infantry 1 tile away can take over.
        Expected: TakeoverRecord returned with state=IN_PROGRESS, replacement_id set.
        """
        bus = _StubEventBus()
        sys = MGTakeoverSystem(event_bus=bus)
        gunner = _make_unit("mg1", UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("r1", UnitType.INFANTRY_SQUAD, x=11, y=10)
        record = sys.on_mg_gunner_killed(gunner, [gunner, replacement])
        assert record is not None
        assert record.state == TakeoverState.IN_PROGRESS
        assert record.replacement_id == "r1"
        assert record.ticks_remaining == TAKEOVER_TICKS
        assert sys.active_takeover_count == 1

    def test_mg_gunner_no_replacement_abandons(self):
        """Verify: MG gunner death with no replacement abandons to FallenUnitCache.

        Scenario: MG gunner dies, no squad members in range.
        Expected: Returns None, MGAbandoned event published, fallen_cache registers.
        """
        bus = _StubEventBus()
        cache = FallenUnitCache()
        sys = MGTakeoverSystem(event_bus=bus, fallen_cache=cache)
        gunner = _make_unit("mg1", UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        # Replacement too far away (distance > TAKEOVER_RANGE=3)
        far_unit = _make_unit("far", UnitType.INFANTRY_SQUAD, x=20, y=20)
        record = sys.on_mg_gunner_killed(gunner, [gunner, far_unit])
        assert record is None
        assert sys.active_takeover_count == 0
        assert len(bus.published) == 1
        assert bus.published[0][0] == "MGAbandoned"

    def test_mg_gunner_already_processed_returns_none(self):
        """Verify: calling on_mg_gunner_killed twice for same gunner is idempotent.

        Scenario: First call starts takeover, second call returns None.
        Expected: Second call returns None, active_takeover_count stays 1.
        """
        bus = _StubEventBus()
        sys = MGTakeoverSystem(event_bus=bus)
        gunner = _make_unit("mg1", UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("r1", UnitType.INFANTRY_SQUAD, x=11, y=10)
        first = sys.on_mg_gunner_killed(gunner, [gunner, replacement])
        second = sys.on_mg_gunner_killed(gunner, [gunner, replacement])
        assert first is not None
        assert second is None
        assert sys.active_takeover_count == 1

    def test_replacement_skips_mg_units_and_dead_and_panicked(self):
        """Verify: replacement filter excludes MG units, dead, and panicked units.

        Scenario: Nearby units are all MG/dead/panicked.
        Expected: No replacement found, MG abandoned.
        """
        bus = _StubEventBus()
        sys = MGTakeoverSystem(event_bus=bus)
        gunner = _make_unit("mg1", UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        other_mg = _make_unit("mg2", UnitType.MACHINE_GUN_SQUAD, x=11, y=10)
        dead = _make_unit("d1", UnitType.INFANTRY_SQUAD, hp=0, x=11, y=10)
        panicked = _make_unit(
            "p1", UnitType.INFANTRY_SQUAD, morale_state=MoraleState.BROKEN, x=11, y=10
        )
        record = sys.on_mg_gunner_killed(gunner, [gunner, other_mg, dead, panicked])
        assert record is None


@pytest.mark.unit
class TestMGTakeoverTick:
    """tick: advancement, completion, and abandonment during takeover."""

    def test_tick_completes_takeover_when_timer_expires(self):
        """Verify: tick decrements timer; on expiry, applies takeover and returns record.

        Scenario: Takeover with TAKEOVER_TICKS=5, tick 5 times.
        Expected: Last tick returns [record] with state=COMPLETED, replacement becomes MG.
        """
        bus = _StubEventBus()
        sys = MGTakeoverSystem(event_bus=bus)
        gunner = _make_unit("mg1", UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("r1", UnitType.INFANTRY_SQUAD, x=11, y=10)
        sys.on_mg_gunner_killed(gunner, [gunner, replacement])

        completed: list = []
        for _ in range(TAKEOVER_TICKS):
            completed = sys.tick([replacement])
        assert len(completed) == 1
        assert completed[0].state == TakeoverState.COMPLETED
        assert sys.active_takeover_count == 0
        # Replacement should now be MG type
        assert replacement.unit_type == UnitType.MACHINE_GUN_SQUAD
        # MGAbandoned not published; MGTakeover published
        assert any(name == "MGTakeover" for name, _ in bus.published)

    def test_tick_aborts_when_replacement_dies(self):
        """Verify: if replacement dies during takeover, state becomes ABANDONED.

        Scenario: Takeover in progress, replacement killed (hp=0) before completion.
        Expected: tick returns [record] with state=ABANDONED.
        """
        bus = _StubEventBus()
        sys = MGTakeoverSystem(event_bus=bus)
        gunner = _make_unit("mg1", UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("r1", UnitType.INFANTRY_SQUAD, x=11, y=10)
        sys.on_mg_gunner_killed(gunner, [gunner, replacement])

        # Kill replacement mid-takeover (set DEAD state directly since is_alive checks state, not hp)
        replacement.health.state = HealthState.DEAD
        completed = sys.tick([replacement])
        assert len(completed) == 1
        assert completed[0].state == TakeoverState.ABANDONED
        assert sys.active_takeover_count == 0

    def test_tick_no_active_takeovers_returns_empty(self):
        """Verify: tick with no active takeovers returns empty list.

        Scenario: No prior on_mg_gunner_killed calls.
        Expected: tick returns [].
        """
        bus = _StubEventBus()
        sys = MGTakeoverSystem(event_bus=bus)
        assert sys.tick([]) == []

    def test_tick_replacement_not_in_unit_list_aborts(self):
        """Verify: if replacement is missing from all_units list, takeover aborts.

        Scenario: Takeover in progress, but tick called with empty unit list.
        Expected: tick returns [record] with state=ABANDONED (replacement treated as dead/missing).
        """
        bus = _StubEventBus()
        sys = MGTakeoverSystem(event_bus=bus)
        gunner = _make_unit("mg1", UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("r1", UnitType.INFANTRY_SQUAD, x=11, y=10)
        sys.on_mg_gunner_killed(gunner, [gunner, replacement])

        completed = sys.tick([])  # replacement not in list
        assert len(completed) == 1
        assert completed[0].state == TakeoverState.ABANDONED


@pytest.mark.unit
class TestMGTakeoverQueries:
    """Query methods: get_takeover_state, active_takeover_count."""

    def test_get_takeover_state_returns_none_for_unknown(self):
        """Verify: get_takeover_state returns None for unknown gunner_id.

        Scenario: No active takeover for 'unknown'.
        Expected: Returns None.
        """
        bus = _StubEventBus()
        sys = MGTakeoverSystem(event_bus=bus)
        assert sys.get_takeover_state("unknown") is None

    def test_get_takeover_state_returns_record_after_initiation(self):
        """Verify: get_takeover_state returns the active record.

        Scenario: on_mg_gunner_killed started a takeover.
        Expected: get_takeover_state returns the same record.
        """
        bus = _StubEventBus()
        sys = MGTakeoverSystem(event_bus=bus)
        gunner = _make_unit("mg1", UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("r1", UnitType.INFANTRY_SQUAD, x=11, y=10)
        created = sys.on_mg_gunner_killed(gunner, [gunner, replacement])
        assert created is not None
        fetched = sys.get_takeover_state("mg1")
        assert fetched is created

    def test_active_takeover_count_reflects_state(self):
        """Verify: active_takeover_count tracks active records.

        Scenario: Start with 0, initiate takeover → 1, complete → 0.
        Expected: Count transitions 0 → 1 → 0.
        """
        bus = _StubEventBus()
        sys = MGTakeoverSystem(event_bus=bus)
        assert sys.active_takeover_count == 0
        gunner = _make_unit("mg1", UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("r1", UnitType.INFANTRY_SQUAD, x=11, y=10)
        sys.on_mg_gunner_killed(gunner, [gunner, replacement])
        assert sys.active_takeover_count == 1
        for _ in range(TAKEOVER_TICKS):
            sys.tick([replacement])
        assert sys.active_takeover_count == 0
