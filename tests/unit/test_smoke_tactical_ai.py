"""Tests for SmokeTacticalAI — active smoke screen usage tactical behavior.

Covers SmokeDeployment, SmokeManager, SmokeGrenadeCapability, and
SmokeTacticalAI evaluate/execute paths using real domain components.
"""

from __future__ import annotations

import numpy as np

from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.difficulty_system import DifficultyConfig, DifficultyLevel
from pycc2.domain.ai.smoke_tactical_ai import (
    SmokeDeployment,
    SmokeGrenadeCapability,
    SmokeManager,
    SmokeTacticalAI,
)
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.ai.tactical_ai import TacticalContext
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.terrain_type import TerrainType
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
    max_ammo: int = 8,
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


def _make_map(w: int = 40, h: int = 30) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    return GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)


def _make_map_with_terrain(
    terrain: TerrainType,
    tx: int = 10,
    ty: int = 10,
    w: int = 40,
    h: int = 30,
) -> GameMap:
    grid = np.zeros((h, w), dtype=np.int8)
    grid[ty, tx] = terrain
    return GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)


def _make_context(
    friendly: list[Unit] | None = None,
    enemy: list[Unit] | None = None,
    game_map: GameMap | None = None,
    tick: int = 1,
    blackboards: dict[str, Blackboard] | None = None,
    difficulty_config: DifficultyConfig | None = None,
) -> TacticalContext:
    return TacticalContext(
        friendly_units=friendly or [],
        enemy_units=enemy or [],
        game_map=game_map or _make_map(),
        current_tick=tick,
        blackboards=blackboards or {},
        difficulty_config=difficulty_config,
    )


# ---------------------------------------------------------------------------
# SmokeDeployment
# ---------------------------------------------------------------------------


class TestSmokeDeployment:
    def test_tick_decrements_remaining_ticks(self):
        """Verify: tick() reduces remaining_ticks by 1.
        Scenario: A fresh smoke deployment with 180 remaining ticks.
        Expected: After one tick, remaining_ticks == 179.
        """
        smoke = SmokeDeployment(position=(5, 5))
        assert smoke.remaining_ticks == 180
        smoke.tick()
        assert smoke.remaining_ticks == 179

    def test_tick_applies_drift_at_interval(self):
        """Verify: smoke drifts 1 tile per DRIFT_INTERVAL ticks.
        Scenario: Smoke with drift_direction (1, 0) and DRIFT_INTERVAL=60.
        Expected: After 60 ticks, position.x advances by 1.
        """
        smoke = SmokeDeployment(position=(5, 5), drift_direction=(1, 0))
        for _ in range(60):
            smoke.tick()
        assert smoke.position == (6, 5)

    def test_tick_no_drift_when_zero_direction(self):
        """Verify: smoke does not drift when drift_direction is (0,0).
        Scenario: Smoke with no wind drift.
        Expected: Position unchanged after DRIFT_INTERVAL ticks.
        """
        smoke = SmokeDeployment(position=(5, 5), drift_direction=(0, 0))
        for _ in range(60):
            smoke.tick()
        assert smoke.position == (5, 5)

    def test_is_expired_when_zero(self):
        """Verify: is_expired is True when remaining_ticks <= 0.
        Scenario: Smoke fully decayed.
        Expected: is_expired returns True.
        """
        smoke = SmokeDeployment(position=(5, 5), remaining_ticks=0)
        assert smoke.is_expired is True

    def test_is_not_expired_when_positive(self):
        """Verify: is_expired is False when remaining_ticks > 0.
        Scenario: Fresh smoke deployment.
        Expected: is_expired returns False.
        """
        smoke = SmokeDeployment(position=(5, 5), remaining_ticks=10)
        assert smoke.is_expired is False

    def test_contains_within_radius(self):
        """Verify: contains() returns True for position within Chebyshev radius.
        Scenario: Smoke at (5,5) with radius 3, target at (7,7).
        Expected: Chebyshev distance 2 <= 3, so contains returns True.
        """
        smoke = SmokeDeployment(position=(5, 5), radius=3)
        assert smoke.contains((7, 7)) is True

    def test_contains_outside_radius(self):
        """Verify: contains() returns False for position beyond radius.
        Scenario: Smoke at (5,5) with radius 3, target at (9,9).
        Expected: Chebyshev distance 4 > 3, so contains returns False.
        """
        smoke = SmokeDeployment(position=(5, 5), radius=3)
        assert smoke.contains((9, 9)) is False

    def test_contains_at_exact_radius(self):
        """Verify: contains() returns True at exact radius boundary.
        Scenario: Smoke at (5,5) with radius 3, target at (8,5).
        Expected: Chebyshev distance 3 == 3, so contains returns True.
        """
        smoke = SmokeDeployment(position=(5, 5), radius=3)
        assert smoke.contains((8, 5)) is True

    def test_contains_at_center(self):
        """Verify: contains() returns True at the smoke center.
        Scenario: Target exactly at smoke position.
        Expected: Distance 0, contains returns True.
        """
        smoke = SmokeDeployment(position=(5, 5), radius=3)
        assert smoke.contains((5, 5)) is True


# ---------------------------------------------------------------------------
# SmokeManager
# ---------------------------------------------------------------------------


class TestSmokeManagerDeploy:
    def test_deploy_adds_smoke(self):
        """Verify: deploy() appends a smoke deployment to the manager.
        Scenario: Empty manager, deploy one smoke cloud.
        Expected: active_deployments contains 1 entry.
        """
        mgr = SmokeManager()
        smoke = SmokeDeployment(position=(5, 5))
        mgr.deploy(smoke)
        assert len(mgr.active_deployments) == 1

    def test_active_deployments_returns_copy(self):
        """Verify: active_deployments returns a copy, not the internal list.
        Scenario: Deploy one smoke, get active_deployments, deploy another.
        Expected: The previously returned list is not affected by new deploy.
        """
        mgr = SmokeManager()
        mgr.deploy(SmokeDeployment(position=(1, 1)))
        snapshot = mgr.active_deployments
        mgr.deploy(SmokeDeployment(position=(2, 2)))
        assert len(snapshot) == 1
        assert len(mgr.active_deployments) == 2


class TestSmokeManagerTick:
    def test_tick_removes_expired_smoke(self):
        """Verify: tick() removes deployments that have expired.
        Scenario: One smoke with 1 tick remaining, one with 10.
        Expected: After tick, only the 10-tick smoke remains.
        """
        mgr = SmokeManager()
        expired = SmokeDeployment(position=(1, 1), remaining_ticks=1)
        alive = SmokeDeployment(position=(2, 2), remaining_ticks=10)
        mgr.deploy(expired)
        mgr.deploy(alive)
        mgr.tick()
        assert len(mgr.active_deployments) == 1
        assert mgr.active_deployments[0].position == (2, 2)

    def test_tick_advances_all_smoke(self):
        """Verify: tick() advances decay on all deployments.
        Scenario: Two smoke clouds with 180 and 100 ticks.
        Expected: After one tick, both have decremented remaining_ticks.
        """
        mgr = SmokeManager()
        s1 = SmokeDeployment(position=(1, 1), remaining_ticks=180)
        s2 = SmokeDeployment(position=(2, 2), remaining_ticks=100)
        mgr.deploy(s1)
        mgr.deploy(s2)
        mgr.tick()
        assert s1.remaining_ticks == 179
        assert s2.remaining_ticks == 99


class TestSmokeManagerQuery:
    def test_is_position_in_smoke_true(self):
        """Verify: is_position_in_smoke returns True when position is covered.
        Scenario: Smoke at (5,5) radius 3, query (6,6).
        Expected: Returns True.
        """
        mgr = SmokeManager()
        mgr.deploy(SmokeDeployment(position=(5, 5), radius=3))
        assert mgr.is_position_in_smoke((6, 6)) is True

    def test_is_position_in_smoke_false(self):
        """Verify: is_position_in_smoke returns False when no smoke covers position.
        Scenario: Smoke at (5,5) radius 3, query (20,20).
        Expected: Returns False.
        """
        mgr = SmokeManager()
        mgr.deploy(SmokeDeployment(position=(5, 5), radius=3))
        assert mgr.is_position_in_smoke((20, 20)) is False

    def test_is_position_in_smoke_empty_manager(self):
        """Verify: is_position_in_smoke returns False when no deployments exist.
        Scenario: Empty manager.
        Expected: Returns False.
        """
        mgr = SmokeManager()
        assert mgr.is_position_in_smoke((5, 5)) is False

    def test_get_smoke_at_returns_covering(self):
        """Verify: get_smoke_at returns all deployments covering a position.
        Scenario: Two overlapping smoke clouds at (5,5), query (5,5).
        Expected: Returns both deployments.
        """
        mgr = SmokeManager()
        mgr.deploy(SmokeDeployment(position=(5, 5), radius=3))
        mgr.deploy(SmokeDeployment(position=(5, 5), radius=2))
        result = mgr.get_smoke_at((5, 5))
        assert len(result) == 2

    def test_get_smoke_at_returns_empty_when_none(self):
        """Verify: get_smoke_at returns empty list when no smoke covers position.
        Scenario: Smoke at (5,5), query (20,20).
        Expected: Returns empty list.
        """
        mgr = SmokeManager()
        mgr.deploy(SmokeDeployment(position=(5, 5), radius=3))
        assert mgr.get_smoke_at((20, 20)) == []


class TestSmokeManagerBlocksLOS:
    def test_blocks_los_when_endpoint_in_smoke(self):
        """Verify: blocks_los returns True when an endpoint is inside smoke.
        Scenario: Smoke at (5,5) radius 3, LOS from (5,5) to (10,10).
        Expected: Returns True (endpoint A is in smoke).
        """
        mgr = SmokeManager()
        mgr.deploy(SmokeDeployment(position=(5, 5), radius=3))
        assert mgr.blocks_los((5, 5), (10, 10)) is True

    def test_blocks_los_when_line_passes_through(self):
        """Verify: blocks_los returns True when the line passes through smoke.
        Scenario: Smoke at (5,5) radius 3, LOS from (1,5) to (9,5).
        Expected: The horizontal line passes through the smoke cloud.
        """
        mgr = SmokeManager()
        mgr.deploy(SmokeDeployment(position=(5, 5), radius=3))
        assert mgr.blocks_los((1, 5), (9, 5)) is True

    def test_blocks_los_clear_path(self):
        """Verify: blocks_los returns False when no smoke blocks the line.
        Scenario: Smoke at (5,5) radius 2, LOS from (1,1) to (1,10).
        Expected: Vertical line at x=1 does not pass through smoke at (5,5).
        """
        mgr = SmokeManager()
        mgr.deploy(SmokeDeployment(position=(5, 5), radius=2))
        assert mgr.blocks_los((1, 1), (1, 10)) is False

    def test_blocks_los_same_position_no_smoke(self):
        """Verify: blocks_los returns False for identical positions with no smoke.
        Scenario: pos_a == pos_b, no smoke.
        Expected: Returns False (length < 1.0, no smoke).
        """
        mgr = SmokeManager()
        assert mgr.blocks_los((5, 5), (5, 5)) is False


class TestSmokeManagerAccuracyModifier:
    def test_accuracy_modifier_through_smoke(self):
        """Verify: accuracy_modifier_through_smoke returns 0.5 when smoke blocks LOS.
        Scenario: Smoke blocks the line between shooter and target.
        Expected: Returns 0.5 (50% accuracy reduction).
        """
        mgr = SmokeManager()
        mgr.deploy(SmokeDeployment(position=(5, 5), radius=3))
        assert mgr.accuracy_modifier_through_smoke((1, 5), (9, 5)) == 0.5

    def test_accuracy_modifier_no_smoke(self):
        """Verify: accuracy_modifier_through_smoke returns 1.0 with no smoke.
        Scenario: Clear LOS, no smoke deployments.
        Expected: Returns 1.0 (no penalty).
        """
        mgr = SmokeManager()
        assert mgr.accuracy_modifier_through_smoke((1, 5), (9, 5)) == 1.0


# ---------------------------------------------------------------------------
# SmokeGrenadeCapability
# ---------------------------------------------------------------------------


class TestSmokeGrenadeCapability:
    def test_has_smoke_when_count_positive(self):
        """Verify: has_smoke returns True when smoke_count > 0.
        Scenario: Capability with 2 smoke charges.
        Expected: has_smoke is True.
        """
        cap = SmokeGrenadeCapability(smoke_count=2, max_smoke=2)
        assert cap.has_smoke is True

    def test_has_no_smoke_when_zero(self):
        """Verify: has_smoke returns False when smoke_count == 0.
        Scenario: Capability with 0 smoke charges.
        Expected: has_smoke is False.
        """
        cap = SmokeGrenadeCapability(smoke_count=0, max_smoke=2)
        assert cap.has_smoke is False

    def test_use_smoke_succeeds(self):
        """Verify: use_smoke decrements count and returns True when charges remain.
        Scenario: Capability with 2 charges.
        Expected: use_smoke returns True, count becomes 1.
        """
        cap = SmokeGrenadeCapability(smoke_count=2, max_smoke=2)
        assert cap.use_smoke() is True
        assert cap.smoke_count == 1

    def test_use_smoke_fails_when_empty(self):
        """Verify: use_smoke returns False when no charges remain.
        Scenario: Capability with 0 charges.
        Expected: use_smoke returns False, count stays 0.
        """
        cap = SmokeGrenadeCapability(smoke_count=0, max_smoke=2)
        assert cap.use_smoke() is False
        assert cap.smoke_count == 0

    def test_use_smoke_until_exhausted(self):
        """Verify: use_smoke can be called until all charges are consumed.
        Scenario: Capability with 2 charges, call use_smoke 3 times.
        Expected: First two succeed, third fails.
        """
        cap = SmokeGrenadeCapability(smoke_count=2, max_smoke=2)
        assert cap.use_smoke() is True
        assert cap.use_smoke() is True
        assert cap.use_smoke() is False
        assert cap.smoke_count == 0

    def test_for_infantry_squad(self):
        """Verify: for_infantry_squad creates 2-charge non-mortar capability.
        Scenario: Factory for standard infantry squad.
        Expected: smoke_count=2, max_smoke=2, is_mortar_smoke=False.
        """
        cap = SmokeGrenadeCapability.for_infantry_squad()
        assert cap.smoke_count == 2
        assert cap.max_smoke == 2
        assert cap.is_mortar_smoke is False

    def test_for_mortar_team(self):
        """Verify: for_mortar_team creates 3-charge mortar capability.
        Scenario: Factory for mortar team.
        Expected: smoke_count=3, is_mortar_smoke=True.
        """
        cap = SmokeGrenadeCapability.for_mortar_team()
        assert cap.smoke_count == 3
        assert cap.is_mortar_smoke is True

    def test_for_nebeltrupp(self):
        """Verify: for_nebeltrupp creates 6-charge non-mortar capability.
        Scenario: Factory for German Nebeltrupp smoke troop.
        Expected: smoke_count=6, is_mortar_smoke=False.
        """
        cap = SmokeGrenadeCapability.for_nebeltrupp()
        assert cap.smoke_count == 6
        assert cap.is_mortar_smoke is False


# ---------------------------------------------------------------------------
# SmokeTacticalAI — evaluate
# ---------------------------------------------------------------------------


class TestSmokeTacticalAIEvaluate:
    def test_evaluate_returns_zero_no_friendlies(self):
        """Verify: evaluate returns 0.0 when no friendly units are alive.
        Scenario: Empty friendly list, enemy present.
        Expected: Returns 0.0.
        """
        ai = SmokeTacticalAI()
        enemy = _make_unit("e1", faction=Faction.AXIS, x=14, y=10)
        ctx = _make_context(friendly=[], enemy=[enemy])
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_returns_zero_no_enemies(self):
        """Verify: evaluate returns 0.0 when no enemy units are alive.
        Scenario: Friendly present, empty enemy list.
        Expected: Returns 0.0.
        """
        ai = SmokeTacticalAI()
        friendly = _make_unit("f1", x=10, y=10)
        ctx = _make_context(friendly=[friendly], enemy=[])
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_returns_zero_no_alive_friendlies(self):
        """Verify: evaluate returns 0.0 when all friendlies are dead.
        Scenario: Friendly with 0 HP, enemy present.
        Expected: Returns 0.0 (no alive friendlies).
        """
        ai = SmokeTacticalAI()
        friendly = _make_unit("f1", hp=0, x=10, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=14, y=10)
        ctx = _make_context(friendly=[friendly], enemy=[enemy])
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_suppressed_in_open_terrain(self):
        """Verify: evaluate adds +0.3 when friendly is suppressed in open terrain.
        Scenario: Infantry squad (smoke-capable) in open terrain with suppression > 0.
        Expected: Score = 0.3 (suppressed) — no penalty since infantry is smoke-capable.
        """
        ai = SmokeTacticalAI()
        gm = _make_map_with_terrain(TerrainType.OPEN, tx=10, ty=10)
        friendly = _make_unit("f1", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        friendly.morale.suppression = 10  # > 0 triggers suppressed check
        enemy = _make_unit("e1", faction=Faction.AXIS, x=14, y=10)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], game_map=gm)
        score = ai.evaluate(ctx)
        # +0.3 (suppressed in open); infantry is smoke-capable so no -0.2 penalty
        assert abs(score - 0.3) < 1e-6

    def test_evaluate_crossing_danger_zone_under_fire(self):
        """Verify: evaluate adds +0.4 for unit crossing bridge under enemy LOS.
        Scenario: Friendly on bridge tile, enemy within 10 tiles (no has_line_of_sight
                  fallback uses distance check). Infantry is smoke-capable.
        Expected: +0.4 (crossing) — no penalty since infantry is smoke-capable.
        """
        ai = SmokeTacticalAI()
        gm = _make_map_with_terrain(TerrainType.BRIDGE, tx=10, ty=10)
        friendly = _make_unit("f1", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=14, y=10)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], game_map=gm)
        score = ai.evaluate(ctx)
        # +0.4 (crossing danger); infantry is smoke-capable so no -0.2 penalty
        assert abs(score - 0.4) < 1e-6

    def test_evaluate_retreat_active(self):
        """Verify: evaluate adds +0.2 when retreat is active in blackboard.
        Scenario: Blackboard has retreat_active=True for a smoke-capable unit.
        Expected: +0.2 (retreat) with smoke-capable commander present.
        """
        ai = SmokeTacticalAI()
        bb = Blackboard()
        bb.set("retreat_active", True)
        friendly = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], blackboards={"cmd": bb})
        score = ai.evaluate(ctx)
        # +0.2 (retreat active), commander is smoke-capable so no -0.2
        assert abs(score - 0.2) < 1e-6

    def test_evaluate_tank_near_at(self):
        """Verify: evaluate adds +0.3 when a friendly tank is near an enemy AT.
        Scenario: Friendly tank within 12 tiles of enemy AT_GUN_TEAM,
                  with a smoke-capable commander present.
        Expected: +0.3 (tank near AT) +0.2 (retreat) if both triggered.
        """
        ai = SmokeTacticalAI()
        tank = _make_unit("tank", unit_type=UnitType.TANK, x=10, y=10)
        commander = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=11)
        at_gun = _make_unit("at1", faction=Faction.AXIS, unit_type=UnitType.AT_GUN_TEAM, x=15, y=10)
        ctx = _make_context(friendly=[tank, commander], enemy=[at_gun])
        score = ai.evaluate(ctx)
        # +0.3 (tank near AT), commander is smoke-capable (no penalty)
        assert abs(score - 0.3) < 1e-6

    def test_evaluate_no_smoke_units_penalty(self):
        """Verify: evaluate applies -0.2 when no smoke-capable units are available.
        Scenario: Only a tank (non-smoke) friendly, enemy present.
        Expected: -0.2 penalty clamped to 0.0.
        """
        ai = SmokeTacticalAI()
        tank = _make_unit("tank", unit_type=UnitType.TANK, x=10, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        ctx = _make_context(friendly=[tank], enemy=[enemy])
        score = ai.evaluate(ctx)
        # No triggers, -0.2 for no smoke units → clamped to 0.0
        assert score == 0.0

    def test_evaluate_with_difficulty_modifier(self):
        """Verify: difficulty_config.aggressiveness scales the final score.
        Scenario: Suppressed infantry in open with difficulty aggressiveness=2.0.
        Expected: Raw score 0.3 * 2.0 = 0.6 (clamped to 1.0 max).
        """
        ai = SmokeTacticalAI()
        gm = _make_map_with_terrain(TerrainType.OPEN, tx=10, ty=10)
        friendly = _make_unit("f1", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        friendly.morale.suppression = 10
        enemy = _make_unit("e1", faction=Faction.AXIS, x=14, y=10)
        diff = DifficultyConfig(level=DifficultyLevel.HARD, aggressiveness=2.0)
        ctx = _make_context(friendly=[friendly], enemy=[enemy], game_map=gm, difficulty_config=diff)
        score = ai.evaluate(ctx)
        # Raw 0.3 (suppressed, smoke-capable) * 2.0 = 0.6
        assert abs(score - 0.6) < 1e-6


# ---------------------------------------------------------------------------
# SmokeTacticalAI — execute
# ---------------------------------------------------------------------------


class TestSmokeTacticalAIExecute:
    def test_execute_no_smoke_units_returns_empty(self):
        """Verify: execute returns [] when no smoke-capable units exist.
        Scenario: Only a tank friendly, suppressed in open.
        Expected: Empty intent list (no deployers available).
        """
        ai = SmokeTacticalAI()
        gm = _make_map_with_terrain(TerrainType.OPEN, tx=10, ty=10)
        tank = _make_unit("tank", unit_type=UnitType.TANK, x=10, y=10)
        tank.morale.suppression = 10
        enemy = _make_unit("e1", faction=Faction.AXIS, x=14, y=10)
        ctx = _make_context(friendly=[tank], enemy=[enemy], game_map=gm)
        assert ai.execute(ctx) == []

    def test_execute_covers_suppressed_unit(self):
        """Verify: execute issues DEPLOY_SMOKE for a suppressed unit in open terrain.
        Scenario: Commander (smoke-capable) near suppressed MG squad (non-smoke) in open.
        Expected: A DEPLOY_SMOKE intent from the commander targeting a position
                  between the suppressed unit and the enemy.
        """
        ai = SmokeTacticalAI()
        gm = _make_map_with_terrain(TerrainType.OPEN, tx=10, ty=10)
        suppressed = _make_unit("sup", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        suppressed.morale.suppression = 10
        deployer = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=11, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=20, y=10)
        ctx = _make_context(friendly=[suppressed, deployer], enemy=[enemy], game_map=gm)
        intents = ai.execute(ctx)
        smoke_intents = [i for i in intents if i.tactic_type == TacticType.DEPLOY_SMOKE]
        assert len(smoke_intents) >= 1
        assert smoke_intents[0].unit_id == "cmd"
        assert smoke_intents[0].target_position is not None

    def test_execute_covers_crossing_danger_zone(self):
        """Verify: execute issues DEPLOY_SMOKE for a unit crossing a bridge.
        Scenario: Commander near infantry on a bridge tile, enemy nearby.
        Expected: A DEPLOY_SMOKE intent is generated.
        """
        ai = SmokeTacticalAI()
        gm = _make_map_with_terrain(TerrainType.BRIDGE, tx=10, ty=10)
        crosser = _make_unit("cross", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        deployer = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=11, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=14, y=10)
        ctx = _make_context(friendly=[crosser, deployer], enemy=[enemy], game_map=gm)
        intents = ai.execute(ctx)
        smoke_intents = [i for i in intents if i.tactic_type == TacticType.DEPLOY_SMOKE]
        assert len(smoke_intents) >= 1

    def test_execute_screens_tank_past_at(self):
        """Verify: execute issues DEPLOY_SMOKE between a tank and enemy AT.
        Scenario: Friendly tank near enemy AT, commander available as deployer.
        Expected: DEPLOY_SMOKE intent targeting midpoint between tank and AT.
        """
        ai = SmokeTacticalAI()
        tank = _make_unit("tank", unit_type=UnitType.TANK, x=10, y=10)
        deployer = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=11, y=10)
        at_gun = _make_unit("at1", faction=Faction.AXIS, unit_type=UnitType.AT_GUN_TEAM, x=16, y=10)
        ctx = _make_context(friendly=[tank, deployer], enemy=[at_gun])
        intents = ai.execute(ctx)
        smoke_intents = [i for i in intents if i.tactic_type == TacticType.DEPLOY_SMOKE]
        assert len(smoke_intents) >= 1
        # Smoke should be placed between tank (10) and AT (16) → midpoint ~13
        assert smoke_intents[0].target_position.x in (12, 13, 14)

    def test_execute_covers_retreat(self):
        """Verify: execute issues DEPLOY_SMOKE for retreating units.
        Scenario: Commander near a retreating unit, retreat_active in blackboard.
        Expected: A DEPLOY_SMOKE intent is generated for the retreating unit.
        """
        ai = SmokeTacticalAI()
        retreating = _make_unit("ret", unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        deployer = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=11, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=20, y=10)
        bb = Blackboard()
        bb.set("retreat_active", True)
        bb.set("is_retreating", True)
        ctx = _make_context(
            friendly=[retreating, deployer],
            enemy=[enemy],
            blackboards={"ret": bb},
        )
        intents = ai.execute(ctx)
        smoke_intents = [i for i in intents if i.tactic_type == TacticType.DEPLOY_SMOKE]
        assert len(smoke_intents) >= 1

    def test_execute_empty_context_returns_empty(self):
        """Verify: execute returns [] with no friendly units.
        Scenario: Empty friendly list.
        Expected: Empty intent list.
        """
        ai = SmokeTacticalAI()
        enemy = _make_unit("e1", faction=Faction.AXIS, x=14, y=10)
        ctx = _make_context(friendly=[], enemy=[enemy])
        assert ai.execute(ctx) == []

    def test_execute_assigns_deployer_only_once(self):
        """Verify: execute does not assign the same deployer to multiple targets.
        Scenario: Two suppressed MG squads (non-smoke), one commander deployer.
        Expected: Only one DEPLOY_SMOKE intent (deployer assigned once).
        """
        ai = SmokeTacticalAI()
        gm = _make_map_with_terrain(TerrainType.OPEN, tx=10, ty=10)
        sup1 = _make_unit("s1", unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        sup1.morale.suppression = 10
        sup2 = _make_unit("s2", unit_type=UnitType.MACHINE_GUN_SQUAD, x=12, y=10)
        sup2.morale.suppression = 10
        deployer = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=11, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=20, y=10)
        ctx = _make_context(friendly=[sup1, sup2, deployer], enemy=[enemy], game_map=gm)
        intents = ai.execute(ctx)
        smoke_intents = [i for i in intents if i.tactic_type == TacticType.DEPLOY_SMOKE]
        # Only one deployer (commander), so only one smoke intent
        assert len(smoke_intents) == 1
        assert smoke_intents[0].unit_id == "cmd"
