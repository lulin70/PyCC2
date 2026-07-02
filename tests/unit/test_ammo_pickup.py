"""Tests for Ammo Pickup & Weapon Scavenging System.

Covers FallenUnitCache, AmmoPickupSystem, and WeaponScavengeAI using real
domain components. Tests exercise Happy Path, Error Case, and Boundary
conditions for each public method.
"""

from __future__ import annotations

import numpy as np

from pycc2.domain.ai.ammo_pickup import (
    AmmoPickupSystem,
    AmmoSourceType,
    FallenUnitCache,
    FallenUnitEntry,
    PickupResult,
    PickupState,
    WeaponScavengeAI,
)
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent, WeaponState
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.combat_mechanics_enhanced import Stance
from pycc2.domain.value_objects.tile_coord import TileCoord

# ---------------------------------------------------------------------------
# Helpers
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
    ammo: int = 8,
    max_ammo: int = 10,
) -> Unit:
    return Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id=weapon_id, ammo_remaining=ammo, max_ammo=max_ammo),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
    )


def _set_prone(unit: Unit) -> Unit:
    """Set the unit's stance to PRONE."""
    unit.combat_state.concealment.current_stance = Stance.PRONE
    return unit


def _set_crouching(unit: Unit) -> Unit:
    """Set the unit's stance to CROUCHING."""
    unit.combat_state.concealment.current_stance = Stance.CROUCHING
    return unit


def _suppress(unit: Unit, amount: float = 50.0) -> Unit:
    """Apply suppression >= MODERATE threshold (45) to the unit."""
    unit.combat_state.suppression.apply_suppression(amount)
    return unit


def _make_map(w: int = 40, h: int = 30) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    return GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)


def _make_context(
    friendly: list[Unit] | None = None,
    enemy: list[Unit] | None = None,
    game_map: GameMap | None = None,
    tick: int = 1,
) -> TacticalContext:
    return TacticalContext(
        friendly_units=friendly or [],
        enemy_units=enemy or [],
        game_map=game_map or _make_map(),
        current_tick=tick,
    )


def _make_fallen_entry(
    uid: str = "dead1",
    x: int = 10,
    y: int = 10,
    faction: Faction = Faction.ALLIES,
    weapon_type: str = "rifle",
    ammo: int = 8,
    max_ammo: int = 10,
    death_tick: int = 0,
    source_type: AmmoSourceType = AmmoSourceType.FALLEN_COMRADE,
) -> FallenUnitEntry:
    return FallenUnitEntry(
        unit_id=uid,
        position=TileCoord(x, y),
        faction=faction,
        weapon_type=weapon_type,
        ammo_remaining=ammo,
        max_ammo=max_ammo,
        death_tick=death_tick,
        source_type=source_type,
    )


# ---------------------------------------------------------------------------
# FallenUnitEntry
# ---------------------------------------------------------------------------


class TestFallenUnitEntry:
    def test_default_ammo_claimed_is_zero(self):
        """Verify: ammo_claimed defaults to 0.
        Scenario: Create a FallenUnitEntry with only required fields.
        Expected: ammo_claimed == 0.
        """
        entry = _make_fallen_entry()
        assert entry.ammo_claimed == 0

    def test_default_weapon_claimed_is_false(self):
        """Verify: weapon_claimed defaults to False.
        Scenario: Create a FallenUnitEntry with only required fields.
        Expected: weapon_claimed is False.
        """
        entry = _make_fallen_entry()
        assert entry.weapon_claimed is False

    def test_entry_stores_all_fields(self):
        """Verify: entry stores all provided field values.
        Scenario: Create entry with specific values.
        Expected: All fields match.
        """
        entry = _make_fallen_entry(
            uid="d2",
            x=5,
            y=7,
            faction=Faction.AXIS,
            weapon_type="mg42",
            ammo=20,
            max_ammo=50,
            death_tick=100,
            source_type=AmmoSourceType.ENEMY_CORPSE,
        )
        assert entry.unit_id == "d2"
        assert entry.position == TileCoord(5, 7)
        assert entry.faction == Faction.AXIS
        assert entry.weapon_type == "mg42"
        assert entry.ammo_remaining == 20
        assert entry.max_ammo == 50
        assert entry.death_tick == 100
        assert entry.source_type == AmmoSourceType.ENEMY_CORPSE


# ---------------------------------------------------------------------------
# FallenUnitCache — register
# ---------------------------------------------------------------------------


class TestFallenUnitCacheRegister:
    def test_register_creates_entry(self):
        """Verify: register adds an entry to the cache.
        Scenario: Register a dead unit.
        Expected: entry_count == 1.
        """
        cache = FallenUnitCache()
        dead = _make_unit("dead1", ammo=5, max_ammo=10)
        cache.register(dead, current_tick=0)
        assert cache.entry_count == 1

    def test_register_stores_unit_data(self):
        """Verify: register stores the unit's position, faction, and weapon data.
        Scenario: Register a unit with specific weapon and ammo.
        Expected: Entry fields match the unit's data.
        """
        cache = FallenUnitCache()
        dead = _make_unit(
            "dead1", faction=Faction.AXIS, x=5, y=7, weapon_id="mg42", ammo=15, max_ammo=50
        )
        cache.register(dead, current_tick=42)
        assert cache.entry_count == 1
        # Access internal entry to verify stored data
        entries = cache._entries  # noqa: SLF001
        assert entries[0].unit_id == "dead1"
        assert entries[0].position == TileCoord(5, 7)
        assert entries[0].faction == Faction.AXIS
        assert entries[0].weapon_type == "mg42"
        assert entries[0].ammo_remaining == 15
        assert entries[0].max_ammo == 50
        assert entries[0].death_tick == 42

    def test_register_multiple_units(self):
        """Verify: register can add multiple entries.
        Scenario: Register 3 dead units.
        Expected: entry_count == 3.
        """
        cache = FallenUnitCache()
        for i in range(3):
            cache.register(_make_unit(f"d{i}"), current_tick=0)
        assert cache.entry_count == 3


# ---------------------------------------------------------------------------
# FallenUnitCache — find_sources_near
# ---------------------------------------------------------------------------


class TestFallenUnitCacheFindSources:
    def test_find_friendly_source_within_range(self):
        """Verify: find_sources_near returns friendly sources within 5-tile range.
        Scenario: ALLIES seeker at (10,10), ALLIES fallen at (12,10) — distance 2.
        Expected: Source found and source_type is FALLEN_COMRADE.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", faction=Faction.ALLIES, x=12, y=10), current_tick=0)
        sources = cache.find_sources_near(
            position=TileCoord(10, 10), seeker_faction=Faction.ALLIES, current_tick=10
        )
        assert len(sources) == 1
        assert sources[0].unit_id == "dead1"
        assert sources[0].source_type == AmmoSourceType.FALLEN_COMRADE

    def test_find_enemy_source_within_range(self):
        """Verify: find_sources_near returns enemy sources within 3-tile range.
        Scenario: ALLIES seeker at (10,10), AXIS fallen at (12,10) — distance 2.
        Expected: Source found and source_type is ENEMY_CORPSE.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", faction=Faction.AXIS, x=12, y=10), current_tick=0)
        sources = cache.find_sources_near(
            position=TileCoord(10, 10), seeker_faction=Faction.ALLIES, current_tick=10
        )
        assert len(sources) == 1
        assert sources[0].source_type == AmmoSourceType.ENEMY_CORPSE

    def test_find_friendly_source_out_of_range(self):
        """Verify: find_sources_near excludes friendly sources beyond 5 tiles.
        Scenario: ALLIES seeker at (10,10), ALLIES fallen at (16,10) — distance 6 > 5.
        Expected: No sources found.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", faction=Faction.ALLIES, x=16, y=10), current_tick=0)
        sources = cache.find_sources_near(
            position=TileCoord(10, 10), seeker_faction=Faction.ALLIES, current_tick=10
        )
        assert sources == []

    def test_find_enemy_source_out_of_range(self):
        """Verify: find_sources_near excludes enemy sources beyond 3 tiles.
        Scenario: ALLIES seeker at (10,10), AXIS fallen at (14,10) — distance 4 > 3.
        Expected: No sources found.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", faction=Faction.AXIS, x=14, y=10), current_tick=0)
        sources = cache.find_sources_near(
            position=TileCoord(10, 10), seeker_faction=Faction.ALLIES, current_tick=10
        )
        assert sources == []

    def test_find_sources_filters_no_ammo_unclaimed_weapon(self):
        """Verify: find_sources_near skips sources with no ammo when weapon is unclaimed.
        Scenario: Source with all ammo claimed, weapon_claimed == False.
        Expected: Source excluded (filter: no ammo AND weapon not claimed → skip).
        Note: Source filter logic `if remaining_ammo <= 0 and not weapon_claimed`
              appears inverted — it skips when weapon is still available but not when
              already claimed. Reported as a bug.
        """
        cache = FallenUnitCache()
        dead = _make_unit("dead1", ammo=8, max_ammo=10)
        cache.register(dead, current_tick=0)
        cache.claim_ammo("dead1", 8)  # All ammo claimed, weapon NOT claimed
        sources = cache.find_sources_near(
            position=TileCoord(10, 10), seeker_faction=Faction.ALLIES, current_tick=10
        )
        assert sources == []

    def test_find_sources_sorted_by_distance(self):
        """Verify: find_sources_near returns sources sorted nearest-first.
        Scenario: Two sources at distances 2 and 1 from seeker.
        Expected: Nearest source (distance 1) appears first.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("far", faction=Faction.ALLIES, x=12, y=10), current_tick=0)
        cache.register(_make_unit("near", faction=Faction.ALLIES, x=11, y=10), current_tick=0)
        sources = cache.find_sources_near(
            position=TileCoord(10, 10), seeker_faction=Faction.ALLIES, current_tick=10
        )
        assert len(sources) == 2
        assert sources[0].unit_id == "near"
        assert sources[1].unit_id == "far"

    def test_find_sources_boundary_at_max_friendly_range(self):
        """Verify: find_sources_near includes friendly source exactly at range 5.
        Scenario: ALLIES seeker at (10,10), ALLIES fallen at (15,10) — distance 5.
        Expected: Source found (boundary inclusive).
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", faction=Faction.ALLIES, x=15, y=10), current_tick=0)
        sources = cache.find_sources_near(
            position=TileCoord(10, 10), seeker_faction=Faction.ALLIES, current_tick=10
        )
        assert len(sources) == 1

    def test_find_sources_boundary_at_max_enemy_range(self):
        """Verify: find_sources_near includes enemy source exactly at range 3.
        Scenario: ALLIES seeker at (10,10), AXIS fallen at (13,10) — distance 3.
        Expected: Source found (boundary inclusive).
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", faction=Faction.AXIS, x=13, y=10), current_tick=0)
        sources = cache.find_sources_near(
            position=TileCoord(10, 10), seeker_faction=Faction.ALLIES, current_tick=10
        )
        assert len(sources) == 1


# ---------------------------------------------------------------------------
# FallenUnitCache — claim_ammo / claim_weapon
# ---------------------------------------------------------------------------


class TestFallenUnitCacheClaims:
    def test_claim_ammo_increments_claimed(self):
        """Verify: claim_ammo increments the ammo_claimed counter.
        Scenario: Source with 8 ammo, claim 3.
        Expected: ammo_claimed == 3, remaining = 5.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", ammo=8), current_tick=0)
        cache.claim_ammo("dead1", 3)
        entry = cache._entries[0]  # noqa: SLF001
        assert entry.ammo_claimed == 3

    def test_claim_ammo_accumulates(self):
        """Verify: claim_ammo accumulates across multiple calls.
        Scenario: Claim 2, then 3 from same source.
        Expected: ammo_claimed == 5.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", ammo=8), current_tick=0)
        cache.claim_ammo("dead1", 2)
        cache.claim_ammo("dead1", 3)
        entry = cache._entries[0]  # noqa: SLF001
        assert entry.ammo_claimed == 5

    def test_claim_ammo_nonexistent_unit_noop(self):
        """Verify: claim_ammo on a nonexistent unit is a silent no-op.
        Scenario: No entries in cache, claim from "ghost".
        Expected: No error raised, entry_count stays 0.
        """
        cache = FallenUnitCache()
        cache.claim_ammo("ghost", 5)
        assert cache.entry_count == 0

    def test_claim_weapon_sets_flag(self):
        """Verify: claim_weapon sets weapon_claimed to True.
        Scenario: Register a unit, claim its weapon.
        Expected: weapon_claimed is True.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1"), current_tick=0)
        cache.claim_weapon("dead1")
        entry = cache._entries[0]  # noqa: SLF001
        assert entry.weapon_claimed is True

    def test_claim_weapon_nonexistent_unit_noop(self):
        """Verify: claim_weapon on a nonexistent unit is a silent no-op.
        Scenario: No entries, claim weapon from "ghost".
        Expected: No error raised.
        """
        cache = FallenUnitCache()
        cache.claim_weapon("ghost")
        assert cache.entry_count == 0


# ---------------------------------------------------------------------------
# FallenUnitCache — prune
# ---------------------------------------------------------------------------


class TestFallenUnitCachePrune:
    def test_prune_removes_expired_entries(self):
        """Verify: entries older than CACHE_EXPIRY_TICKS are pruned.
        Scenario: Entry with death_tick=0, current_tick=301 (> 300).
        Expected: entry_count == 0 after find_sources_near triggers prune.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", x=10, y=10), current_tick=0)
        # find_sources_near calls _prune_expired internally
        cache.find_sources_near(
            position=TileCoord(10, 10), seeker_faction=Faction.ALLIES, current_tick=301
        )
        assert cache.entry_count == 0

    def test_prune_keeps_recent_entries(self):
        """Verify: entries within CACHE_EXPIRY_TICKS are retained.
        Scenario: Entry with death_tick=0, current_tick=299 (< 300).
        Expected: entry_count == 1 after prune.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", x=10, y=10), current_tick=0)
        cache.find_sources_near(
            position=TileCoord(10, 10), seeker_faction=Faction.ALLIES, current_tick=299
        )
        assert cache.entry_count == 1

    def test_prune_boundary_at_exact_expiry(self):
        """Verify: entry at exactly CACHE_EXPIRY_TICKS is pruned.
        Scenario: death_tick=0, current_tick=300 (300 - 0 = 300, not < 300).
        Expected: entry_count == 0 (pruned, since condition is < not <=).
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", x=10, y=10), current_tick=0)
        cache.find_sources_near(
            position=TileCoord(10, 10), seeker_faction=Faction.ALLIES, current_tick=300
        )
        assert cache.entry_count == 0


# ---------------------------------------------------------------------------
# AmmoPickupSystem — can_pickup
# ---------------------------------------------------------------------------


class TestAmmoPickupSystemCanPickup:
    def test_can_pickup_true_prone(self):
        """Verify: can_pickup returns True for a prone, unsuppressed, alive unit.
        Scenario: INFANTRY_SQUAD in PRONE stance, no suppression.
        Expected: Returns True.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1"))
        assert system.can_pickup(unit) is True

    def test_can_pickup_true_crouching(self):
        """Verify: can_pickup returns True for a crouching unit.
        Scenario: INFANTRY_SQUAD in CROUCHING stance, no suppression.
        Expected: Returns True.
        """
        system = AmmoPickupSystem()
        unit = _set_crouching(_make_unit("u1"))
        assert system.can_pickup(unit) is True

    def test_can_pickup_false_standing(self):
        """Verify: can_pickup returns False for a standing unit.
        Scenario: Unit in default STANDING stance.
        Expected: Returns False (must be PRONE or CROUCHING).
        """
        system = AmmoPickupSystem()
        unit = _make_unit("u1")  # Default stance is STANDING
        assert system.can_pickup(unit) is False

    def test_can_pickup_false_dead(self):
        """Verify: can_pickup returns False for a dead unit.
        Scenario: Unit with 0 HP in PRONE stance.
        Expected: Returns False.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", hp=0))
        assert system.can_pickup(unit) is False

    def test_can_pickup_false_suppressed_moderate(self):
        """Verify: can_pickup returns False when suppression >= MODERATE.
        Scenario: Prone unit with 50 suppression (>= 45 moderate threshold).
        Expected: Returns False.
        """
        system = AmmoPickupSystem()
        unit = _suppress(_set_prone(_make_unit("u1")))
        assert system.can_pickup(unit) is False

    def test_can_pickup_false_already_picking_up(self):
        """Verify: can_pickup returns False when unit already has an active pickup.
        Scenario: Start a pickup, then call can_pickup again.
        Expected: Returns False (already picking up).
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", x=10, y=10))
        source = _make_fallen_entry("dead1", x=10, y=10, faction=Faction.ALLIES)
        system.start_pickup(unit, source, current_tick=0)
        assert system.can_pickup(unit) is False


# ---------------------------------------------------------------------------
# AmmoPickupSystem — start_pickup
# ---------------------------------------------------------------------------


class TestAmmoPickupSystemStartPickup:
    def test_start_pickup_success_friendly(self):
        """Verify: start_pickup returns SUCCESS for a valid friendly source.
        Scenario: Prone unit, friendly source at same position.
        Expected: Returns SUCCESS, pickup state created.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", x=10, y=10))
        source = _make_fallen_entry("dead1", x=10, y=10, faction=Faction.ALLIES)
        result = system.start_pickup(unit, source, current_tick=0)
        assert result == PickupResult.SUCCESS
        assert system.get_pickup_state("u1") is not None

    def test_start_pickup_success_enemy(self):
        """Verify: start_pickup returns SUCCESS for a valid enemy source.
        Scenario: Prone unit, enemy source at same position.
        Expected: Returns SUCCESS.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", x=10, y=10))
        source = _make_fallen_entry("dead1", x=10, y=10, faction=Faction.AXIS)
        result = system.start_pickup(unit, source, current_tick=0)
        assert result == PickupResult.SUCCESS

    def test_start_pickup_already_picking_up(self):
        """Verify: start_pickup returns ALREADY_PICKING_UP for a second attempt.
        Scenario: Unit already has an active pickup, tries again.
        Expected: Returns ALREADY_PICKING_UP.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", x=10, y=10))
        source = _make_fallen_entry("dead1", x=10, y=10)
        system.start_pickup(unit, source, current_tick=0)
        result = system.start_pickup(unit, source, current_tick=1)
        assert result == PickupResult.ALREADY_PICKING_UP

    def test_start_pickup_wrong_stance(self):
        """Verify: start_pickup returns WRONG_STANCE for a standing unit.
        Scenario: Unit in STANDING stance.
        Expected: Returns WRONG_STANCE.
        """
        system = AmmoPickupSystem()
        unit = _make_unit("u1", x=10, y=10)  # STANDING
        source = _make_fallen_entry("dead1", x=10, y=10)
        result = system.start_pickup(unit, source, current_tick=0)
        assert result == PickupResult.WRONG_STANCE

    def test_start_pickup_suppressed(self):
        """Verify: start_pickup returns SUPPRESSED for a heavily suppressed unit.
        Scenario: Prone unit with 50 suppression (MODERATE).
        Expected: Returns SUPPRESSED.
        """
        system = AmmoPickupSystem()
        unit = _suppress(_set_prone(_make_unit("u1", x=10, y=10)))
        source = _make_fallen_entry("dead1", x=10, y=10)
        result = system.start_pickup(unit, source, current_tick=0)
        assert result == PickupResult.SUPPRESSED

    def test_start_pickup_no_source_friendly_too_far(self):
        """Verify: start_pickup returns NO_SOURCE when friendly source is beyond 5 tiles.
        Scenario: Unit at (10,10), friendly source at (16,10) — distance 6 > 5.
        Expected: Returns NO_SOURCE.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", x=10, y=10))
        source = _make_fallen_entry("dead1", x=16, y=10, faction=Faction.ALLIES)
        result = system.start_pickup(unit, source, current_tick=0)
        assert result == PickupResult.NO_SOURCE

    def test_start_pickup_no_source_enemy_too_far(self):
        """Verify: start_pickup returns NO_SOURCE when enemy source is beyond 3 tiles.
        Scenario: Unit at (10,10), enemy source at (14,10) — distance 4 > 3.
        Expected: Returns NO_SOURCE.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", x=10, y=10))
        source = _make_fallen_entry("dead1", x=14, y=10, faction=Faction.AXIS)
        result = system.start_pickup(unit, source, current_tick=0)
        assert result == PickupResult.NO_SOURCE

    def test_start_pickup_creates_correct_pickup_state(self):
        """Verify: start_pickup creates a PickupState with correct fields.
        Scenario: Start pickup from a friendly source.
        Expected: PickupState has correct source_id, source_type, ticks_remaining.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", x=10, y=10))
        source = _make_fallen_entry("dead1", x=10, y=10, faction=Faction.ALLIES)
        system.start_pickup(unit, source, current_tick=0)
        state = system.get_pickup_state("u1")
        assert state is not None
        assert state.unit_id == "u1"
        assert state.source_id == "dead1"
        assert state.source_type == AmmoSourceType.FALLEN_COMRADE
        assert state.ticks_remaining == AmmoPickupSystem.PICKUP_DURATION_TICKS
        assert state.target_position == TileCoord(10, 10)


# ---------------------------------------------------------------------------
# AmmoPickupSystem — tick
# ---------------------------------------------------------------------------


class TestAmmoPickupSystemTick:
    def test_tick_returns_completed_after_duration(self):
        """Verify: tick returns completed pickups after PICKUP_DURATION_TICKS.
        Scenario: Start pickup, tick PICKUP_DURATION_TICKS times.
        Expected: Completed list has 1 entry, active_pickup_count == 0.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", x=10, y=10))
        source = _make_fallen_entry("dead1", x=10, y=10)
        system.start_pickup(unit, source, current_tick=0)

        completed = []
        for _ in range(AmmoPickupSystem.PICKUP_DURATION_TICKS):
            completed = system.tick(current_tick=1)

        assert len(completed) == 1
        assert completed[0].unit_id == "u1"
        assert system.active_pickup_count == 0

    def test_tick_in_progress_returns_empty(self):
        """Verify: tick returns empty list before duration is reached.
        Scenario: Start pickup (2 ticks), tick once.
        Expected: completed list is empty.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", x=10, y=10))
        source = _make_fallen_entry("dead1", x=10, y=10)
        system.start_pickup(unit, source, current_tick=0)
        completed = system.tick(current_tick=1)
        assert completed == []
        assert system.active_pickup_count == 1

    def test_tick_no_pickups_returns_empty(self):
        """Verify: tick returns empty list when no pickups are active.
        Scenario: No active pickups, call tick.
        Expected: Returns empty list.
        """
        system = AmmoPickupSystem()
        completed = system.tick(current_tick=0)
        assert completed == []

    def test_tick_multiple_pickups_complete_simultaneously(self):
        """Verify: tick can complete multiple pickups in the same tick.
        Scenario: Two active pickups, tick until both complete.
        Expected: Both returned in completed list.
        """
        system = AmmoPickupSystem()
        u1 = _set_prone(_make_unit("u1", x=10, y=10))
        u2 = _set_prone(_make_unit("u2", x=20, y=20))
        s1 = _make_fallen_entry("d1", x=10, y=10)
        s2 = _make_fallen_entry("d2", x=20, y=20)
        system.start_pickup(u1, s1, current_tick=0)
        system.start_pickup(u2, s2, current_tick=0)

        completed = []
        for _ in range(AmmoPickupSystem.PICKUP_DURATION_TICKS):
            completed = system.tick(current_tick=1)
        assert len(completed) == 2

    def test_get_pickup_state_returns_none_when_absent(self):
        """Verify: get_pickup_state returns None when no pickup is active.
        Scenario: No pickup started for the unit.
        Expected: Returns None.
        """
        system = AmmoPickupSystem()
        assert system.get_pickup_state("nonexistent") is None


# ---------------------------------------------------------------------------
# AmmoPickupSystem — apply_pickup (friendly)
# ---------------------------------------------------------------------------


class TestAmmoPickupApplyFriendly:
    def test_friendly_same_weapon_transfers_50_percent(self):
        """Verify: friendly pickup with same weapon transfers 50% of available ammo.
        Scenario: Source has 8 ammo, same weapon as seeker. Seeker has 2/10.
        Expected: Transfer = int(8 * 0.5) = 4. Seeker ammo = 2 + 4 = 6.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", weapon_id="rifle", ammo=2, max_ammo=10))
        source = _make_fallen_entry("d1", weapon_type="rifle", ammo=8, max_ammo=10)
        pickup = PickupState(
            unit_id="u1",
            source_id="d1",
            source_type=AmmoSourceType.FALLEN_COMRADE,
            ticks_remaining=0,
            target_position=TileCoord(10, 10),
        )
        system.apply_pickup(unit, pickup, source)
        assert unit.weapon.ammo_remaining == 6  # 2 + 4

    def test_friendly_different_weapon_transfers_25_percent(self):
        """Verify: friendly pickup with different weapon transfers 25% of available ammo.
        Scenario: Source has 8 ammo, different weapon. Seeker has 2/10.
        Expected: Transfer = int(8 * 0.5 * 0.5) = 2. Seeker ammo = 2 + 2 = 4.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", weapon_id="rifle", ammo=2, max_ammo=10))
        source = _make_fallen_entry("d1", weapon_type="mg42", ammo=8, max_ammo=10)
        pickup = PickupState(
            unit_id="u1",
            source_id="d1",
            source_type=AmmoSourceType.FALLEN_COMRADE,
            ticks_remaining=0,
            target_position=TileCoord(10, 10),
        )
        system.apply_pickup(unit, pickup, source)
        assert unit.weapon.ammo_remaining == 4  # 2 + 2

    def test_friendly_transfer_caps_at_max_ammo(self):
        """Verify: friendly transfer is capped at the seeker's max_ammo.
        Scenario: Source has 20 ammo, seeker has 8/10 (space=2). Same weapon.
        Expected: Transfer = min(int(20*0.5), 2) = min(10, 2) = 2. Ammo = 8+2 = 10.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", weapon_id="rifle", ammo=8, max_ammo=10))
        source = _make_fallen_entry("d1", weapon_type="rifle", ammo=20, max_ammo=20)
        pickup = PickupState(
            unit_id="u1",
            source_id="d1",
            source_type=AmmoSourceType.FALLEN_COMRADE,
            ticks_remaining=0,
            target_position=TileCoord(10, 10),
        )
        system.apply_pickup(unit, pickup, source)
        assert unit.weapon.ammo_remaining == 10  # Capped at max

    def test_friendly_no_ammo_available_noop(self):
        """Verify: friendly pickup does nothing when source has no ammo left.
        Scenario: Source ammo_claimed == ammo_remaining (all claimed).
        Expected: Unit ammo unchanged.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", weapon_id="rifle", ammo=2, max_ammo=10))
        source = _make_fallen_entry("d1", weapon_type="rifle", ammo=8, max_ammo=10)
        source.ammo_claimed = 8  # All ammo already claimed
        pickup = PickupState(
            unit_id="u1",
            source_id="d1",
            source_type=AmmoSourceType.FALLEN_COMRADE,
            ticks_remaining=0,
            target_position=TileCoord(10, 10),
        )
        system.apply_pickup(unit, pickup, source)
        assert unit.weapon.ammo_remaining == 2  # Unchanged

    def test_friendly_updates_out_of_ammo_state(self):
        """Verify: pickup restores OUT_OF_AMMO weapon to READY.
        Scenario: Unit has 0 ammo (OUT_OF_AMMO), picks up from friendly.
        Expected: Weapon state becomes READY after pickup.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", weapon_id="rifle", ammo=0, max_ammo=10))
        assert unit.weapon.state == WeaponState.OUT_OF_AMMO
        source = _make_fallen_entry("d1", weapon_type="rifle", ammo=8, max_ammo=10)
        pickup = PickupState(
            unit_id="u1",
            source_id="d1",
            source_type=AmmoSourceType.FALLEN_COMRADE,
            ticks_remaining=0,
            target_position=TileCoord(10, 10),
        )
        system.apply_pickup(unit, pickup, source)
        assert unit.weapon.ammo_remaining > 0
        assert unit.weapon.state == WeaponState.READY

    def test_friendly_transfer_minimum_one(self):
        """Verify: friendly transfer is at least 1 when ammo is available.
        Scenario: Source has 1 ammo, same weapon. Transfer = max(1, int(1*0.5)) = max(1, 0) = 1.
        Expected: Seeker gains 1 ammo.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", weapon_id="rifle", ammo=5, max_ammo=10))
        source = _make_fallen_entry("d1", weapon_type="rifle", ammo=1, max_ammo=10)
        pickup = PickupState(
            unit_id="u1",
            source_id="d1",
            source_type=AmmoSourceType.FALLEN_COMRADE,
            ticks_remaining=0,
            target_position=TileCoord(10, 10),
        )
        system.apply_pickup(unit, pickup, source)
        assert unit.weapon.ammo_remaining == 6  # 5 + 1 (minimum transfer)


# ---------------------------------------------------------------------------
# AmmoPickupSystem — apply_pickup (enemy)
# ---------------------------------------------------------------------------


class TestAmmoPickupApplyEnemy:
    def test_enemy_transfers_all_ammo(self):
        """Verify: enemy pickup transfers all available ammo (capped at max).
        Scenario: Source has 8 ammo, seeker has 2/10 (space=8).
        Expected: Transfer = min(8, 8) = 8. Seeker ammo = 2 + 8 = 10.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", weapon_id="rifle", ammo=2, max_ammo=10))
        source = _make_fallen_entry(
            "d1", weapon_type="mg42", ammo=8, max_ammo=10, faction=Faction.AXIS
        )
        pickup = PickupState(
            unit_id="u1",
            source_id="d1",
            source_type=AmmoSourceType.ENEMY_CORPSE,
            ticks_remaining=0,
            target_position=TileCoord(10, 10),
        )
        system.apply_pickup(unit, pickup, source)
        assert unit.weapon.ammo_remaining == 10  # 2 + 8

    def test_enemy_marks_weapon_captured_in_combat_state(self):
        """Verify: enemy pickup marks the weapon as captured in combat_state.
        Scenario: Unit with combat_state picks up from enemy corpse.
        Expected: combat_state.captured_weapon is True, penalties applied.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", weapon_id="rifle", ammo=2, max_ammo=10))
        source = _make_fallen_entry(
            "d1", weapon_type="mg42", ammo=8, max_ammo=10, faction=Faction.AXIS
        )
        pickup = PickupState(
            unit_id="u1",
            source_id="d1",
            source_type=AmmoSourceType.ENEMY_CORPSE,
            ticks_remaining=0,
            target_position=TileCoord(10, 10),
        )
        system.apply_pickup(unit, pickup, source)
        assert unit.combat_state.captured_weapon is True
        assert (
            unit.combat_state.captured_accuracy_penalty
            == AmmoPickupSystem.CAPTURED_ACCURACY_PENALTY
        )
        assert unit.combat_state.captured_reload_penalty == AmmoPickupSystem.CAPTURED_RELOAD_PENALTY

    def test_enemy_marks_weapon_captured_fallback(self):
        """Verify: enemy pickup marks weapon on weapon component when combat_state is None.
        Scenario: Unit with combat_state=None picks up from enemy.
        Expected: weapon.is_captured is True, penalties on weapon.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", weapon_id="rifle", ammo=2, max_ammo=10))
        unit.combat_state = None  # Force fallback path
        source = _make_fallen_entry(
            "d1", weapon_type="mg42", ammo=8, max_ammo=10, faction=Faction.AXIS
        )
        pickup = PickupState(
            unit_id="u1",
            source_id="d1",
            source_type=AmmoSourceType.ENEMY_CORPSE,
            ticks_remaining=0,
            target_position=TileCoord(10, 10),
        )
        system.apply_pickup(unit, pickup, source)
        assert unit.weapon.is_captured is True
        assert unit.weapon.captured_accuracy_penalty == AmmoPickupSystem.CAPTURED_ACCURACY_PENALTY
        assert unit.weapon.captured_reload_penalty == AmmoPickupSystem.CAPTURED_RELOAD_PENALTY

    def test_enemy_transfer_caps_at_max_ammo(self):
        """Verify: enemy transfer is capped at seeker's max_ammo.
        Scenario: Source has 20 ammo, seeker has 8/10 (space=2).
        Expected: Transfer = min(20, 2) = 2. Ammo = 8 + 2 = 10.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", weapon_id="rifle", ammo=8, max_ammo=10))
        source = _make_fallen_entry(
            "d1", weapon_type="mg42", ammo=20, max_ammo=20, faction=Faction.AXIS
        )
        pickup = PickupState(
            unit_id="u1",
            source_id="d1",
            source_type=AmmoSourceType.ENEMY_CORPSE,
            ticks_remaining=0,
            target_position=TileCoord(10, 10),
        )
        system.apply_pickup(unit, pickup, source)
        assert unit.weapon.ammo_remaining == 10  # Capped

    def test_enemy_no_ammo_available_does_nothing(self):
        """Verify: enemy pickup does nothing when source has no ammo available.
        Scenario: Source has all ammo claimed (available=0).
        Expected: No ammo transferred, weapon NOT marked captured (early return).
        Note: _apply_enemy_pickup returns early when available <= 0, before
              reaching _mark_weapon_captured. This means a weapon cannot be
              scavenged from an enemy corpse if all ammo was already claimed.
        """
        system = AmmoPickupSystem()
        unit = _set_prone(_make_unit("u1", weapon_id="rifle", ammo=5, max_ammo=10))
        source = _make_fallen_entry(
            "d1", weapon_type="mg42", ammo=8, max_ammo=10, faction=Faction.AXIS
        )
        source.ammo_claimed = 8  # All claimed
        pickup = PickupState(
            unit_id="u1",
            source_id="d1",
            source_type=AmmoSourceType.ENEMY_CORPSE,
            ticks_remaining=0,
            target_position=TileCoord(10, 10),
        )
        system.apply_pickup(unit, pickup, source)
        assert unit.weapon.ammo_remaining == 5  # Unchanged
        assert unit.combat_state.captured_weapon is False  # NOT marked (early return)


# ---------------------------------------------------------------------------
# AmmoPickupSystem — properties
# ---------------------------------------------------------------------------


class TestAmmoPickupSystemProperties:
    def test_active_pickup_count_zero_initially(self):
        """Verify: active_pickup_count is 0 when no pickups are active.
        Scenario: Fresh system with no active pickups.
        Expected: Returns 0.
        """
        system = AmmoPickupSystem()
        assert system.active_pickup_count == 0

    def test_active_pickup_count_tracks_active(self):
        """Verify: active_pickup_count reflects active pickups.
        Scenario: Start 2 pickups.
        Expected: Count == 2.
        """
        system = AmmoPickupSystem()
        u1 = _set_prone(_make_unit("u1", x=10, y=10))
        u2 = _set_prone(_make_unit("u2", x=20, y=20))
        s1 = _make_fallen_entry("d1", x=10, y=10)
        s2 = _make_fallen_entry("d2", x=20, y=20)
        system.start_pickup(u1, s1, current_tick=0)
        system.start_pickup(u2, s2, current_tick=0)
        assert system.active_pickup_count == 2


# ---------------------------------------------------------------------------
# WeaponScavengeAI — evaluate
# ---------------------------------------------------------------------------


class TestWeaponScavengeAIEvaluate:
    def test_evaluate_zero_no_low_ammo_units(self):
        """Verify: evaluate returns 0.0 when no units are low on ammo.
        Scenario: All friendly units have ammo_ratio >= 0.2.
        Expected: Returns 0.0.
        """
        cache = FallenUnitCache()
        ai = WeaponScavengeAI(fallen_cache=cache)
        unit = _make_unit("u1", ammo=8, max_ammo=10)  # ratio = 0.8
        ctx = _make_context(friendly=[unit])
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_zero_no_sources_available(self):
        """Verify: evaluate returns 0.0 when low-ammo units exist but no sources.
        Scenario: Unit with ammo_ratio=0.05, no fallen units in cache.
        Expected: Returns 0.0.
        """
        cache = FallenUnitCache()
        ai = WeaponScavengeAI(fallen_cache=cache)
        unit = _make_unit("u1", ammo=0, max_ammo=10)  # ratio = 0.0
        ctx = _make_context(friendly=[unit])
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_positive_with_low_ammo_and_sources(self):
        """Verify: evaluate returns >0 when low-ammo units and sources exist.
        Scenario: Unit with 0 ammo, a fallen comrade nearby.
        Expected: Returns a positive score.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", x=10, y=10, ammo=8), current_tick=0)
        ai = WeaponScavengeAI(fallen_cache=cache)
        unit = _make_unit("u1", ammo=0, max_ammo=10)  # ratio = 0.0
        ctx = _make_context(friendly=[unit], tick=10)
        assert ai.evaluate(ctx) > 0.0

    def test_evaluate_higher_score_with_more_critical_units(self):
        """Verify: evaluate score increases with more critically low units.
        Scenario: 1 critical unit vs 2 critical units.
        Expected: Score with 2 critical units > score with 1.
        """
        cache1 = FallenUnitCache()
        cache1.register(_make_unit("d1", x=10, y=10, ammo=8), current_tick=0)
        cache2 = FallenUnitCache()
        cache2.register(_make_unit("d1", x=10, y=10, ammo=8), current_tick=0)
        cache2.register(_make_unit("d2", x=10, y=10, ammo=8), current_tick=0)

        ai1 = WeaponScavengeAI(fallen_cache=cache1)
        ai2 = WeaponScavengeAI(fallen_cache=cache2)

        unit1 = _make_unit("u1", ammo=0, max_ammo=10)
        ctx1 = _make_context(friendly=[unit1], tick=10)

        unit2a = _make_unit("u1", ammo=0, max_ammo=10)
        unit2b = _make_unit("u2", ammo=0, max_ammo=10)
        ctx2 = _make_context(friendly=[unit2a, unit2b], tick=10)

        score1 = ai1.evaluate(ctx1)
        score2 = ai2.evaluate(ctx2)
        assert score2 > score1

    def test_evaluate_zero_unit_not_combat_effective(self):
        """Verify: evaluate returns 0.0 when low-ammo unit is not combat effective.
        Scenario: Unit with 0 ammo but morale < 20 (BROKEN, not combat effective).
        Expected: Returns 0.0.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", x=10, y=10, ammo=8), current_tick=0)
        ai = WeaponScavengeAI(fallen_cache=cache)
        unit = _make_unit("u1", ammo=0, max_ammo=10, morale=10)  # BROKEN
        ctx = _make_context(friendly=[unit], tick=10)
        assert ai.evaluate(ctx) == 0.0


# ---------------------------------------------------------------------------
# WeaponScavengeAI — execute
# ---------------------------------------------------------------------------


class TestWeaponScavengeAIExecute:
    def test_execute_no_low_ammo_returns_empty(self):
        """Verify: execute returns [] when no units are low on ammo.
        Scenario: All units have sufficient ammo.
        Expected: Empty intent list.
        """
        cache = FallenUnitCache()
        ai = WeaponScavengeAI(fallen_cache=cache)
        unit = _make_unit("u1", ammo=8, max_ammo=10)
        ctx = _make_context(friendly=[unit])
        assert ai.execute(ctx) == []

    def test_execute_no_sources_returns_empty(self):
        """Verify: execute returns [] when low-ammo units exist but no sources.
        Scenario: Unit with 0 ammo, no fallen units in cache.
        Expected: Empty intent list.
        """
        cache = FallenUnitCache()
        ai = WeaponScavengeAI(fallen_cache=cache)
        unit = _make_unit("u1", ammo=0, max_ammo=10)
        ctx = _make_context(friendly=[unit])
        assert ai.execute(ctx) == []

    def test_execute_issues_scavenge_intent(self):
        """Verify: execute issues a SCAVENGE_AMMO intent for a low-ammo unit.
        Scenario: Unit with 0 ammo, fallen comrade nearby.
        Expected: One SCAVENGE_AMMO intent targeting the source.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", x=11, y=10, ammo=8), current_tick=0)
        ai = WeaponScavengeAI(fallen_cache=cache)
        unit = _make_unit("u1", x=10, y=10, ammo=0, max_ammo=10)
        ctx = _make_context(friendly=[unit], tick=10)
        intents = ai.execute(ctx)
        assert len(intents) == 1
        assert intents[0].tactic_type == TacticType.SCAVENGE_AMMO
        assert intents[0].unit_id == "u1"
        assert intents[0].target_position == TileCoord(11, 10)
        assert intents[0].target_unit_id == "dead1"

    def test_execute_priority_10_for_critical_ammo(self):
        """Verify: execute assigns priority 10 for ammo_ratio < 0.1 (critical).
        Scenario: Unit with 0/10 ammo (ratio=0.0 < 0.1).
        Expected: Intent priority == 10.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", x=11, y=10, ammo=8), current_tick=0)
        ai = WeaponScavengeAI(fallen_cache=cache)
        unit = _make_unit("u1", x=10, y=10, ammo=0, max_ammo=10)
        ctx = _make_context(friendly=[unit], tick=10)
        intents = ai.execute(ctx)
        assert intents[0].priority == 10

    def test_execute_priority_7_for_low_ammo(self):
        """Verify: execute assigns priority 7 for 0.1 <= ammo_ratio < 0.2.
        Scenario: Unit with 1/10 ammo (ratio=0.1, not < 0.1).
        Expected: Intent priority == 7.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", x=11, y=10, ammo=8), current_tick=0)
        ai = WeaponScavengeAI(fallen_cache=cache)
        unit = _make_unit("u1", x=10, y=10, ammo=1, max_ammo=10)  # ratio = 0.1
        ctx = _make_context(friendly=[unit], tick=10)
        intents = ai.execute(ctx)
        assert intents[0].priority == 7

    def test_execute_assigns_sources_uniquely(self):
        """Verify: execute assigns each source to at most one unit.
        Scenario: 2 low-ammo units, 1 source. Only first unit gets an intent.
        Expected: 1 intent (not 2).
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("dead1", x=10, y=10, ammo=8), current_tick=0)
        ai = WeaponScavengeAI(fallen_cache=cache)
        u1 = _make_unit("u1", x=10, y=10, ammo=0, max_ammo=10)
        u2 = _make_unit("u2", x=10, y=10, ammo=0, max_ammo=10)
        ctx = _make_context(friendly=[u1, u2], tick=10)
        intents = ai.execute(ctx)
        assert len(intents) == 1
        assert intents[0].target_unit_id == "dead1"

    def test_execute_picks_nearest_source(self):
        """Verify: execute picks the nearest source for each unit.
        Scenario: Two sources at distances 1 and 3. Unit should pick nearest.
        Expected: Intent targets the nearest source.
        """
        cache = FallenUnitCache()
        cache.register(_make_unit("far", x=13, y=10, ammo=8), current_tick=0)
        cache.register(_make_unit("near", x=11, y=10, ammo=8), current_tick=0)
        ai = WeaponScavengeAI(fallen_cache=cache)
        unit = _make_unit("u1", x=10, y=10, ammo=0, max_ammo=10)
        ctx = _make_context(friendly=[unit], tick=10)
        intents = ai.execute(ctx)
        assert len(intents) == 1
        assert intents[0].target_unit_id == "near"
