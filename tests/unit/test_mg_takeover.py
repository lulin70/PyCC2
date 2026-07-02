"""Tests for MGTakeoverSystem — CC2-authentic MG gunner death behavior.

When an MG gunner is killed, a nearby squad member takes over the weapon
after a 5-tick delay, incurring a -15% accuracy penalty. If no replacement
is available, the MG is abandoned (registered in FallenUnitCache).

Real components are used (EventBus, Unit, FallenUnitCache) — no mocks.
"""

from __future__ import annotations

from pycc2.domain.ai.ammo_pickup import FallenUnitCache
from pycc2.domain.ai.mg_takeover import (
    MG_ACCURACY_PENALTY,
    TAKEOVER_RANGE,
    TAKEOVER_TICKS,
    MGTakeoverSystem,
    TakeoverRecord,
    TakeoverState,
)
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.infrastructure.events.event_bus import EventBus

# ---------------------------------------------------------------------------
# Helpers — real components, no mocks
# ---------------------------------------------------------------------------


def _make_unit(
    uid: str = "u1",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    x: int = 10,
    y: int = 10,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 80,
    weapon_id: str = "rifle",
) -> Unit:
    return Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id=weapon_id, ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
    )


def _kill_unit(unit: Unit) -> None:
    """Force a unit into the DEAD state without going through take_damage."""
    unit.health.hp = 0
    unit.health._update_state()
    unit.die()


# ---------------------------------------------------------------------------
# Smoke / construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_construct_with_real_event_bus(self):
        """Verify: MGTakeoverSystem can be instantiated with a real EventBus.

        Scenario: Caller constructs the system with no active takeovers.
        Expected: active_takeover_count == 0, event_bus stored.
        """
        bus = EventBus()
        sys = MGTakeoverSystem(event_bus=bus)
        assert sys.event_bus is bus
        assert sys.active_takeover_count == 0

    def test_construct_creates_default_fallen_cache(self):
        """Verify: When fallen_cache is None, a default FallenUnitCache is created.

        Scenario: Construct without explicit fallen_cache.
        Expected: An internal FallenUnitCache is available (used when MG abandoned).
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        # The internal cache should be a FallenUnitCache instance
        assert isinstance(sys._fallen_cache, FallenUnitCache)
        assert sys._fallen_cache.entry_count == 0

    def test_construct_accepts_custom_fallen_cache(self):
        """Verify: A caller-supplied FallenUnitCache is used directly.

        Scenario: Pass a pre-existing FallenUnitCache to the constructor.
        Expected: The same cache instance is stored.
        """
        cache = FallenUnitCache()
        sys = MGTakeoverSystem(event_bus=EventBus(), fallen_cache=cache)
        assert sys._fallen_cache is cache


# ---------------------------------------------------------------------------
# Happy path — MG gunner killed, replacement found
# ---------------------------------------------------------------------------


class TestOnMGGunnerKilledHappyPath:
    def test_mg_death_returns_takeover_record(self):
        """Verify: Killing an MG gunner with a nearby replacement returns a record.

        Scenario: MG dies, an infantry squad member is 1 tile away.
        Expected: TakeoverRecord returned with replacement_id, ticks_remaining=5,
                  state=IN_PROGRESS.
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10, morale=85)
        replacement = _make_unit("rep", unit_type=UnitType.INFANTRY_SQUAD, x=11, y=10)

        record = sys.on_mg_gunner_killed(mg, [mg, replacement])

        assert record is not None
        assert isinstance(record, TakeoverRecord)
        assert record.dead_gunner_id == "mg"
        assert record.replacement_id == "rep"
        assert record.ticks_remaining == TAKEOVER_TICKS
        assert record.state == TakeoverState.IN_PROGRESS
        assert record.mg_position_x == 10
        assert record.mg_position_y == 10

    def test_mg_death_increments_active_count(self):
        """Verify: After starting a takeover, active_takeover_count increases.

        Scenario: One MG killed with replacement available.
        Expected: active_takeover_count == 1.
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("rep", x=11, y=10)

        sys.on_mg_gunner_killed(mg, [mg, replacement])

        assert sys.active_takeover_count == 1

    def test_get_takeover_state_returns_active_record(self):
        """Verify: get_takeover_state returns the record for a dead gunner.

        Scenario: After starting a takeover, query the gunner id.
        Expected: Same TakeoverRecord instance returned.
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("rep", x=11, y=10)

        sys.on_mg_gunner_killed(mg, [mg, replacement])
        record = sys.get_takeover_state("mg")

        assert record is not None
        assert record.replacement_id == "rep"

    def test_nearest_replacement_is_chosen(self):
        """Verify: When multiple candidates exist, the nearest is picked.

        Scenario: MG at (10,10); near candidate at (11,10) dist=1; far at (13,10) dist=3.
        Expected: replacement_id == 'near'.
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        near = _make_unit("near", x=11, y=10)
        far = _make_unit("far", x=13, y=10)

        record = sys.on_mg_gunner_killed(mg, [mg, near, far])

        assert record is not None
        assert record.replacement_id == "near"


# ---------------------------------------------------------------------------
# Error cases — non-MG, no replacement, already-processed
# ---------------------------------------------------------------------------


class TestOnMGGunnerKilledErrorCases:
    def test_non_mg_unit_returns_none(self):
        """Verify: A non-MG unit death does not trigger takeover.

        Scenario: An infantry squad unit is killed.
        Expected: Returns None, no takeover started.
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        infantry = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        replacement = _make_unit("rep", x=11, y=10)

        record = sys.on_mg_gunner_killed(infantry, [infantry, replacement])

        assert record is None
        assert sys.active_takeover_count == 0

    def test_no_replacement_in_range_abandons_mg(self):
        """Verify: When no replacement is within TAKEOVER_RANGE, MG is abandoned.

        Scenario: MG dies; the only candidate is 10 tiles away (> TAKEOVER_RANGE=3).
        Expected: Returns None, MG registered in FallenUnitCache, 'MGAbandoned' event fired.
        """
        bus = EventBus()
        captured: list[dict] = []
        bus.subscribe_to("MGAbandoned", captured.append)

        sys = MGTakeoverSystem(event_bus=bus)
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        far_unit = _make_unit("far", x=20, y=20)  # 10 tiles away, out of range

        record = sys.on_mg_gunner_killed(mg, [mg, far_unit], current_tick=5)

        assert record is None
        assert sys.active_takeover_count == 0
        # MG should be registered in the fallen cache
        assert sys._fallen_cache.entry_count == 1
        # MGAbandoned event should have been published
        assert len(captured) == 1
        assert captured[0]["action"] == "mg_abandoned"
        assert captured[0]["unit_id"] == "mg"
        assert captured[0]["position"] == (10, 10)

    def test_already_processed_gunner_returns_none(self):
        """Verify: A gunner already in active takeovers is not re-processed.

        Scenario: First call starts a takeover; second call for same gunner returns None.
        Expected: Second call returns None, count stays at 1.
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("rep", x=11, y=10)

        first = sys.on_mg_gunner_killed(mg, [mg, replacement])
        second = sys.on_mg_gunner_killed(mg, [mg, replacement])

        assert first is not None
        assert second is None
        assert sys.active_takeover_count == 1

    def test_dead_replacement_is_skipped(self):
        """Verify: A dead candidate is not chosen as a replacement.

        Scenario: MG dies; the only candidate is already dead.
        Expected: Returns None (no living replacement).
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        dead_candidate = _make_unit("dead", x=11, y=10)
        _kill_unit(dead_candidate)

        record = sys.on_mg_gunner_killed(mg, [mg, dead_candidate])

        assert record is None

    def test_panicked_replacement_is_skipped(self):
        """Verify: A panicked (non-combat-effective) candidate is skipped.

        Scenario: MG dies; the only candidate has morale 5 (BROKEN state, not combat effective).
        Expected: Returns None.
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        panicked = _make_unit("panic", x=11, y=10, morale=5)

        record = sys.on_mg_gunner_killed(mg, [mg, panicked])

        assert record is None

    def test_other_mg_unit_is_skipped(self):
        """Verify: Another MG unit is not chosen as a replacement.

        Scenario: MG dies; the only candidate is itself an MG squad.
        Expected: Returns None (don't transfer MG to MG).
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        other_mg = _make_unit("mg2", unit_type=UnitType.MACHINE_GUN_SQUAD, x=11, y=10)

        record = sys.on_mg_gunner_killed(mg, [mg, other_mg])

        assert record is None


# ---------------------------------------------------------------------------
# Tick lifecycle — completion and abandonment
# ---------------------------------------------------------------------------


class TestTickLifecycle:
    def test_tick_completes_after_takeover_ticks(self):
        """Verify: A takeover completes after exactly TAKEOVER_TICKS ticks.

        Scenario: Start a 5-tick takeover; tick 4 times → not complete; 5th → complete.
        Expected: First 4 ticks return []; 5th returns record with state=COMPLETED.
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("rep", x=11, y=10, morale=85)

        sys.on_mg_gunner_killed(mg, [mg, replacement])

        # Ticks 1..4 should not complete
        for _ in range(TAKEOVER_TICKS - 1):
            completed = sys.tick([replacement])
            assert completed == []

        # 5th tick completes
        completed = sys.tick([replacement])
        assert len(completed) == 1
        assert completed[0].state == TakeoverState.COMPLETED
        assert sys.active_takeover_count == 0

    def test_completion_applies_mg_to_replacement(self):
        """Verify: On completion, the replacement receives the MG weapon and penalty.

        Scenario: Takeover completes; check replacement's weapon and combat_state.
        Expected: weapon.primary_weapon_id == 'mg42', ammo == 50,
                  combat_state.captured_weapon == True,
                  captured_accuracy_penalty == MG_ACCURACY_PENALTY,
                  unit_type == MACHINE_GUN_SQUAD.
        """
        bus = EventBus()
        captured: list[dict] = []
        bus.subscribe_to("MGTakeover", captured.append)

        sys = MGTakeoverSystem(event_bus=bus)
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("rep", x=11, y=10, morale=85)

        sys.on_mg_gunner_killed(mg, [mg, replacement])

        # Advance to completion
        for _ in range(TAKEOVER_TICKS):
            sys.tick([replacement])

        assert replacement.weapon.primary_weapon_id == "mg42"
        assert replacement.weapon.ammo_remaining == 50
        assert replacement.weapon.max_ammo == 50
        assert replacement.unit_type == UnitType.MACHINE_GUN_SQUAD
        # Penalty applied via combat_state
        assert replacement.combat_state is not None
        assert replacement.combat_state.captured_weapon is True
        assert replacement.combat_state.captured_accuracy_penalty == MG_ACCURACY_PENALTY
        # MGTakeover event published
        assert len(captured) == 1
        assert captured[0]["action"] == "mg_takeover"
        assert captured[0]["replacement_id"] == "rep"
        assert captured[0]["dead_gunner_id"] == "mg"

    def test_replacement_dies_during_takeover_abandons(self):
        """Verify: If the replacement dies mid-takeover, the takeover is abandoned.

        Scenario: Takeover starts; after 2 ticks the replacement is killed.
        Expected: tick returns a record with state=ABANDONED, active count drops to 0.
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("rep", x=11, y=10, morale=85)

        sys.on_mg_gunner_killed(mg, [mg, replacement])

        # Tick twice while replacement is alive
        sys.tick([replacement])
        sys.tick([replacement])

        # Now kill the replacement
        _kill_unit(replacement)

        completed = sys.tick([replacement])
        assert len(completed) == 1
        assert completed[0].state == TakeoverState.ABANDONED
        assert sys.active_takeover_count == 0

    def test_tick_with_no_active_takeovers_returns_empty(self):
        """Verify: tick returns [] when there are no active takeovers.

        Scenario: Call tick on a fresh system.
        Expected: empty list, no exception.
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        assert sys.tick([]) == []

    def test_replacement_not_in_all_units_abandons(self):
        """Verify: If the replacement is missing from all_units during tick, abandon.

        Scenario: Takeover in progress; tick called with an empty unit list.
        Expected: state == ABANDONED (replacement treated as dead/missing).
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        replacement = _make_unit("rep", x=11, y=10, morale=85)

        sys.on_mg_gunner_killed(mg, [mg, replacement])

        # Tick with empty list — replacement not found
        completed = sys.tick([])
        assert len(completed) == 1
        assert completed[0].state == TakeoverState.ABANDONED


# ---------------------------------------------------------------------------
# Boundary — range and constants
# ---------------------------------------------------------------------------


class TestBoundary:
    def test_replacement_at_exactly_takeover_range(self):
        """Verify: A replacement exactly TAKEOVER_RANGE tiles away is accepted.

        Scenario: MG at (10,10); candidate at (13,10) — distance 3 == TAKEOVER_RANGE.
        Expected: Takeover starts (boundary inclusive).
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        boundary = _make_unit("bound", x=10 + TAKEOVER_RANGE, y=10, morale=85)

        record = sys.on_mg_gunner_killed(mg, [mg, boundary])

        assert record is not None
        assert record.replacement_id == "bound"

    def test_replacement_just_outside_range_is_skipped(self):
        """Verify: A replacement TAKEOVER_RANGE+1 tiles away is rejected.

        Scenario: MG at (10,10); candidate at (14,10) — distance 4 > TAKEOVER_RANGE=3.
        Expected: Returns None (out of range).
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        mg = _make_unit("mg", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        too_far = _make_unit("far", x=10 + TAKEOVER_RANGE + 1, y=10, morale=85)

        record = sys.on_mg_gunner_killed(mg, [mg, too_far])

        assert record is None

    def test_get_takeover_state_returns_none_for_unknown_gunner(self):
        """Verify: get_takeover_state returns None for an unknown gunner id.

        Scenario: Query a gunner id with no active takeover.
        Expected: None returned.
        """
        sys = MGTakeoverSystem(event_bus=EventBus())
        assert sys.get_takeover_state("nobody") is None


# ---------------------------------------------------------------------------
# Module invariants
# ---------------------------------------------------------------------------


class TestModuleInvariants:
    def test_constants_have_expected_values(self):
        """Verify: Module constants match the CC2 design values."""
        assert TAKEOVER_RANGE == 3
        assert TAKEOVER_TICKS == 5
        assert MG_ACCURACY_PENALTY == 0.15

    def test_takeover_state_has_four_distinct_members(self):
        """Verify: TakeoverState enum has the four expected lifecycle states."""
        states = {
            TakeoverState.PENDING,
            TakeoverState.IN_PROGRESS,
            TakeoverState.COMPLETED,
            TakeoverState.ABANDONED,
        }
        assert len(states) == 4
