"""Tests for tank_riders module — TankRiderSystem and TankRiderAI.

Covers mount/dismount lifecycle, capacity limits, auto-dismount on enemy
approach, tank-hit throw-off injury logic, and AI evaluate/execute paths
for pairing infantry with friendly tanks.
"""

from __future__ import annotations

import numpy as np

from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext
from pycc2.domain.ai.tank_riders import (
    DISMOUNT_TICKS,
    MAX_RIDERS_PER_TANK,
    MOUNT_RANGE,
    MOUNT_TICKS,
    RiderSlot,
    RiderStatus,
    TankRiderAI,
    TankRiderManifest,
    TankRiderSystem,
)
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord

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
) -> Unit:
    return Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
    )


def _make_tank(
    uid: str = "tank1",
    faction: Faction = Faction.ALLIES,
    x: int = 10,
    y: int = 10,
    hp: int = 200,
    max_hp: int = 200,
    morale: int = 90,
) -> Unit:
    return _make_unit(
        uid=uid,
        faction=faction,
        unit_type=UnitType.TANK,
        x=x,
        y=y,
        hp=hp,
        max_hp=max_hp,
        morale=morale,
    )


def _make_map(w: int = 40, h: int = 30) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    return GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)


def _make_context(
    friendly: list[Unit] | None = None,
    enemy: list[Unit] | None = None,
    game_map: GameMap | None = None,
    vl_positions: list[tuple[TileCoord, str | None, int]] | None = None,
    tick: int = 1,
) -> TacticalContext:
    return TacticalContext(
        friendly_units=friendly or [],
        enemy_units=enemy or [],
        game_map=game_map or _make_map(),
        current_tick=tick,
        vl_positions=vl_positions or [],
    )


# ---------------------------------------------------------------------------
# TankRiderManifest dataclass
# ---------------------------------------------------------------------------


class TestTankRiderManifest:
    def test_empty_manifest_has_capacity(self):
        """Verify: empty manifest reports active_rider_count=0 and has_capacity=True."""
        m = TankRiderManifest(tank_id="t1")
        assert m.active_rider_count == 0
        assert m.has_capacity is True

    def test_active_rider_count_excludes_dismounted(self):
        """Verify: only MOUNTING/RIDING slots count toward active_rider_count."""
        m = TankRiderManifest(tank_id="t1")
        m.riders.append(RiderSlot("r1", "t1", RiderStatus.RIDING))
        m.riders.append(RiderSlot("r2", "t1", RiderStatus.MOUNTING))
        m.riders.append(RiderSlot("r3", "t1", RiderStatus.APPROACHING))
        m.riders.append(RiderSlot("r4", "t1", RiderStatus.DISMOUNTED))
        assert m.active_rider_count == 2

    def test_has_capacity_false_at_max(self):
        """Verify: at MAX_RIDERS_PER_TANK active riders, has_capacity is False."""
        m = TankRiderManifest(tank_id="t1")
        for i in range(MAX_RIDERS_PER_TANK):
            m.riders.append(RiderSlot(f"r{i}", "t1", RiderStatus.RIDING))
        assert m.active_rider_count == MAX_RIDERS_PER_TANK
        assert m.has_capacity is False


# ---------------------------------------------------------------------------
# TankRiderSystem.can_mount
# ---------------------------------------------------------------------------


class TestCanMount:
    def test_happy_path_infantry_adjacent_to_tank(self):
        """Verify: alive infantry within range of friendly tank can mount."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=11, y=10)
        assert system.can_mount(inf, tank, [inf, tank]) is True

    def test_false_when_rider_dead(self):
        """Verify: dead infantry cannot mount."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10, hp=0)
        tank = _make_tank("tank1", x=10, y=10)
        assert system.can_mount(inf, tank, [inf, tank]) is False

    def test_false_when_rider_is_tank(self):
        """Verify: non-infantry unit type cannot mount."""
        system = TankRiderSystem()
        mg = _make_unit("mg1", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        assert system.can_mount(mg, tank, [mg, tank]) is False

    def test_false_when_tank_dead(self):
        """Verify: cannot mount a dead tank."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10, hp=0)
        assert system.can_mount(inf, tank, [inf, tank]) is False

    def test_false_when_target_is_not_tank(self):
        """Verify: target unit must be UnitType.TANK."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        other = _make_unit("inf2", x=10, y=10)
        assert system.can_mount(inf, other, [inf, other]) is False

    def test_false_when_different_faction(self):
        """Verify: cannot mount enemy tank."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", faction=Faction.ALLIES, x=10, y=10)
        tank = _make_tank("tank1", faction=Faction.AXIS, x=10, y=10)
        assert system.can_mount(inf, tank, [inf, tank]) is False

    def test_false_when_outside_mount_range(self):
        """Verify: infantry beyond MOUNT_RANGE cannot mount."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=0, y=0)
        tank = _make_tank("tank1", x=MOUNT_RANGE + 5, y=0)
        assert system.can_mount(inf, tank, [inf, tank]) is False

    def test_false_when_tank_at_capacity(self):
        """Verify: full tank refuses further mounts."""
        system = TankRiderSystem()
        tank = _make_tank("tank1", x=10, y=10)
        # Fill the tank to capacity first
        for i in range(MAX_RIDERS_PER_TANK):
            rider = _make_unit(f"r{i}", x=10, y=10)
            system.start_mount(rider, tank)
            # Force to RIDING so they count as active
            manifest = system._manifests[tank.id]
            manifest.riders[i].status = RiderStatus.RIDING
        new_inf = _make_unit("new_inf", x=10, y=10)
        assert system.can_mount(new_inf, tank, [tank, new_inf]) is False

    def test_false_when_enemy_nearby(self):
        """Verify: nearby enemy blocks mounting (combat-free radius)."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=12, y=10)
        assert system.can_mount(inf, tank, [inf, tank, enemy]) is False


# ---------------------------------------------------------------------------
# TankRiderSystem.start_mount / start_dismount
# ---------------------------------------------------------------------------


class TestStartMount:
    def test_happy_path_creates_manifest_and_slot(self):
        """Verify: start_mount creates manifest, slot, and rider mapping."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        assert system.start_mount(inf, tank) is True
        assert tank.id in system._manifests
        assert system._rider_to_tank[inf.id] == tank.id
        slot = system._manifests[tank.id].riders[0]
        assert slot.status == RiderStatus.MOUNTING
        assert slot.mount_progress == 0

    def test_double_mount_returns_false(self):
        """Verify: cannot mount a rider that is already riding."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        assert system.start_mount(inf, tank) is False

    def test_mount_at_capacity_returns_false(self):
        """Verify: start_mount fails when tank is full."""
        system = TankRiderSystem()
        tank = _make_tank("tank1", x=10, y=10)
        riders = []
        for i in range(MAX_RIDERS_PER_TANK):
            r = _make_unit(f"r{i}", x=10, y=10)
            riders.append(r)
            system.start_mount(r, tank)
        extra = _make_unit("extra", x=10, y=10)
        assert system.start_mount(extra, tank) is False


class TestStartDismount:
    def test_happy_path_sets_dismounting_status(self):
        """Verify: start_dismount transitions slot to DISMOUNTING."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        assert system.start_dismount(inf.id) is True
        slot = system._find_slot(system._manifests[tank.id], inf.id)
        assert slot.status == RiderStatus.DISMOUNTING
        assert slot.dismount_progress == 0

    def test_instant_dismount_removes_slot(self):
        """Verify: instant=True completes dismount immediately.

        Note: _complete_dismount removes the slot from the manifest's riders
        list and clears the rider mapping, but does NOT pop the now-empty
        manifest from _manifests — that cleanup only happens during tick().
        Verify the slot is gone and the rider is unmapped, then tick to
        confirm the empty manifest is cleaned up.
        """
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        assert system.start_dismount(inf.id, instant=True) is True
        # Rider mapping cleared immediately
        assert inf.id not in system._rider_to_tank
        # Slot removed from manifest's riders list
        manifest = system._manifests[tank.id]
        assert manifest.riders == []
        # Empty manifest cleanup deferred to tick()
        system.tick([inf, tank])
        assert tank.id not in system._manifests

    def test_dismount_unknown_rider_returns_false(self):
        """Verify: dismounting a non-riding unit returns False."""
        system = TankRiderSystem()
        assert system.start_dismount("nonexistent") is False


# ---------------------------------------------------------------------------
# TankRiderSystem.tick
# ---------------------------------------------------------------------------


class TestTick:
    def test_mounting_completes_after_mount_ticks(self):
        """Verify: MOUNTING -> RIDING after MOUNT_TICKS ticks."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        units = [inf, tank]
        completed = []
        for _ in range(MOUNT_TICKS):
            completed.extend(system.tick(units))
        # Last tick should have completed the mount
        slot = system._find_slot(system._manifests[tank.id], inf.id)
        assert slot.status == RiderStatus.RIDING
        assert slot.mount_progress == MOUNT_TICKS
        assert any(s.rider_id == inf.id for s in completed)

    def test_riding_unit_follows_tank(self):
        """Verify: RIDING rider's position tracks tank position."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        units = [inf, tank]
        # Complete mount
        for _ in range(MOUNT_TICKS):
            system.tick(units)
        # Move tank to a new position and tick
        tank.move_to_tile(TileCoord(15, 15))
        system.tick(units)
        assert inf.position.tile_coord == TileCoord(15, 15)

    def test_auto_dismount_when_enemy_approaches(self):
        """Verify: RIDING unit auto-dismounts (instant) when enemy within radius."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        units = [inf, tank]
        for _ in range(MOUNT_TICKS):
            system.tick(units)
        # Spawn enemy close enough to trigger auto-dismount
        enemy = _make_unit("e1", faction=Faction.AXIS, x=12, y=10)
        units.append(enemy)
        system.tick(units)
        assert system.is_riding(inf.id) is False
        assert inf.id not in system._rider_to_tank

    def test_dismounting_completes_after_dismount_ticks(self):
        """Verify: DISMOUNTING -> DISMOUNTED after DISMOUNT_TICKS."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        units = [inf, tank]
        for _ in range(MOUNT_TICKS):
            system.tick(units)
        system.start_dismount(inf.id)
        for _ in range(DISMOUNT_TICKS):
            system.tick(units)
        assert inf.id not in system._rider_to_tank

    def test_dead_rider_cleaned_up_on_tick(self):
        """Verify: dead rider is removed during tick."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        # Kill the rider
        inf.take_damage(200)
        assert not inf.is_alive
        system.tick([inf, tank])
        assert inf.id not in system._rider_to_tank

    def test_dead_tank_cleans_up_riders(self):
        """Verify: dead tank removes its riders during tick."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        tank.take_damage(300)
        assert not tank.is_alive
        system.tick([inf, tank])
        assert inf.id not in system._rider_to_tank


# ---------------------------------------------------------------------------
# TankRiderSystem.handle_tank_hit
# ---------------------------------------------------------------------------


class TestHandleTankHit:
    def test_thrown_riders_removed_from_manifest(self):
        """Verify: tank hit throws off all mounting/riding units."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        thrown = system.handle_tank_hit(tank.id, [inf, tank])
        assert inf.id in thrown
        assert inf.id not in system._rider_to_tank

    def test_unknown_tank_returns_empty(self):
        """Verify: handle_tank_hit on unknown tank returns empty list."""
        system = TankRiderSystem()
        assert system.handle_tank_hit("nope", []) == []

    def test_no_thrown_for_dismounted_slots(self):
        """Verify: DISMOUNTED/DISMOUNTING/APPROACHING slots are not thrown."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        # Move slot to DISMOUNTED (already gone) — simulate by removing
        manifest = system._manifests[tank.id]
        manifest.riders[0].status = RiderStatus.DISMOUNTED
        thrown = system.handle_tank_hit(tank.id, [inf, tank])
        # DISMOUNTED slots aren't thrown (filter is MOUNTING/RIDING)
        assert inf.id not in thrown


# ---------------------------------------------------------------------------
# TankRiderSystem queries
# ---------------------------------------------------------------------------


class TestTankRiderQueries:
    def test_is_riding_true_only_when_riding(self):
        """Verify: is_riding is True only when status == RIDING."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        assert system.is_riding(inf.id) is False
        # Force to RIDING
        system._manifests[tank.id].riders[0].status = RiderStatus.RIDING
        assert system.is_riding(inf.id) is True

    def test_is_riding_false_for_unknown_rider(self):
        """Verify: is_riding returns False for unknown rider."""
        system = TankRiderSystem()
        assert system.is_riding("unknown") is False

    def test_get_rider_tank_returns_tank_id(self):
        """Verify: get_rider_tank returns associated tank id."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        assert system.get_rider_tank(inf.id) == tank.id

    def test_get_rider_tank_none_for_unknown(self):
        """Verify: get_rider_tank returns None for unknown rider."""
        system = TankRiderSystem()
        assert system.get_rider_tank("unknown") is None

    def test_get_tank_riders_returns_active_only(self):
        """Verify: get_tank_riders returns MOUNTING/RIDING ids only."""
        system = TankRiderSystem()
        tank = _make_tank("tank1", x=10, y=10)
        inf1 = _make_unit("inf1", x=10, y=10)
        inf2 = _make_unit("inf2", x=10, y=10)
        system.start_mount(inf1, tank)
        system.start_mount(inf2, tank)
        riders = system.get_tank_riders(tank.id)
        assert inf1.id in riders
        assert inf2.id in riders

    def test_get_tank_riders_empty_for_unknown_tank(self):
        """Verify: get_tank_riders returns [] for unknown tank."""
        system = TankRiderSystem()
        assert system.get_tank_riders("unknown") == []

    def test_active_manifests_returns_list(self):
        """Verify: active_manifests property returns current manifests."""
        system = TankRiderSystem()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=10, y=10)
        system.start_mount(inf, tank)
        manifests = system.active_manifests
        assert len(manifests) == 1
        assert manifests[0].tank_id == tank.id


# ---------------------------------------------------------------------------
# TankRiderAI.evaluate
# ---------------------------------------------------------------------------


class TestTankRiderAIEvaluate:
    def test_zero_when_no_tanks(self):
        """Verify: evaluate returns 0.0 when no friendly tanks."""
        ai = TankRiderAI()
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(friendly=[inf])
        assert ai.evaluate(ctx) == 0.0

    def test_zero_when_no_infantry(self):
        """Verify: evaluate returns 0.0 when no available infantry."""
        ai = TankRiderAI()
        tank = _make_tank("tank1", x=10, y=10)
        ctx = _make_context(friendly=[tank])
        assert ai.evaluate(ctx) == 0.0

    def test_positive_when_tank_and_infantry_available(self):
        """Verify: evaluate returns positive score with tank + infantry + distant VLs."""
        ai = TankRiderAI()
        inf = _make_unit("inf1", x=5, y=5)
        tank = _make_tank("tank1", x=6, y=5)
        vl_positions = [(TileCoord(35, 25), None, 10)]
        ctx = _make_context(friendly=[inf, tank], vl_positions=vl_positions)
        score = ai.evaluate(ctx)
        assert 0.0 < score <= 1.0

    def test_zero_score_when_enemy_close(self):
        """Verify: nearby enemy pressure drives score toward 0."""
        ai = TankRiderAI()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=11, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=12, y=10)
        ctx = _make_context(friendly=[inf, tank], enemy=[enemy])
        # Enemy within 5 tiles -> enemy_pressure=1.0 -> score 0
        assert ai.evaluate(ctx) == 0.0


# ---------------------------------------------------------------------------
# TankRiderAI.execute
# ---------------------------------------------------------------------------


class TestTankRiderAIExecute:
    def test_issues_mount_tank_for_adjacent_infantry(self):
        """Verify: execute issues MOUNT_TANK intent for nearby infantry."""
        ai = TankRiderAI()
        inf = _make_unit("inf1", x=10, y=10)
        tank = _make_tank("tank1", x=11, y=10)
        ctx = _make_context(friendly=[inf, tank])
        intents = ai.execute(ctx)
        mount_intents = [i for i in intents if i.tactic_type == TacticType.MOUNT_TANK]
        assert len(mount_intents) == 1
        assert mount_intents[0].unit_id == inf.id
        assert mount_intents[0].target_unit_id == tank.id

    def test_issues_move_to_for_distant_infantry(self):
        """Verify: execute issues MOVE_TO intent for infantry far from tank."""
        ai = TankRiderAI()
        inf = _make_unit("inf1", x=0, y=0)
        tank = _make_tank("tank1", x=15, y=15)
        ctx = _make_context(friendly=[inf, tank])
        intents = ai.execute(ctx)
        move_intents = [i for i in intents if i.tactic_type == TacticType.MOVE_TO]
        assert len(move_intents) == 1
        assert move_intents[0].target_unit_id == tank.id

    def test_no_intents_when_no_tanks(self):
        """Verify: execute returns [] with no tanks."""
        ai = TankRiderAI()
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(friendly=[inf])
        assert ai.execute(ctx) == []

    def test_no_intents_when_no_infantry(self):
        """Verify: execute returns [] with no infantry."""
        ai = TankRiderAI()
        tank = _make_tank("tank1", x=10, y=10)
        ctx = _make_context(friendly=[tank])
        assert ai.execute(ctx) == []

    def test_skips_full_tank(self):
        """Verify: execute skips a tank whose manifest is at capacity."""
        ai = TankRiderAI()
        tank = _make_tank("tank1", x=10, y=10)
        # Pre-fill the manifest
        for i in range(MAX_RIDERS_PER_TANK):
            r = _make_unit(f"r{i}", x=10, y=10)
            ai.system.start_mount(r, tank)
            ai.system._manifests[tank.id].riders[i].status = RiderStatus.RIDING
        new_inf = _make_unit("new_inf", x=10, y=10)
        ctx = _make_context(friendly=[tank, new_inf])
        intents = ai.execute(ctx)
        # New infantry can't mount full tank; should get MOVE_TO instead (or nothing)
        assert all(
            i.unit_id != new_inf.id or i.tactic_type != TacticType.MOUNT_TANK for i in intents
        )
