"""Tests for artillery_callin module — ArtilleryManager and ArtilleryCallinAI.

Covers mission lifecycle (CALLING -> INCOMING -> COMPLETE), ammo budget,
impact-area calculation with scatter, damage/suppression application,
weather scatter, and AI evaluate/execute paths for issuing
CALL_ARTILLERY intents with minimum-range and friendly-fire safety checks.
"""

from __future__ import annotations

import numpy as np

from pycc2.domain.ai.artillery_callin import (
    CALL_DELAY_TICKS,
    CORRECTION_DELAY_TICKS,
    DAMAGE_PER_TILE,
    FIRE_DELAY_TICKS,
    FOG_SCATTER,
    MAX_FIRE_MISSIONS,
    MINIMUM_RANGE,
    RAIN_SCATTER,
    SUPPRESSION_PER_TILE,
    ArtilleryCallinAI,
    ArtilleryManager,
    ArtilleryMission,
    ArtilleryPhase,
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
from pycc2.domain.systems.environment import EnvironmentState, TimeOfDay, WeatherCondition
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


def _make_observer(
    uid: str = "obs1",
    faction: Faction = Faction.ALLIES,
    x: int = 5,
    y: int = 5,
) -> Unit:
    return _make_unit(
        uid=uid,
        faction=faction,
        unit_type=UnitType.COMMANDER,
        x=x,
        y=y,
        hp=100,
        max_hp=100,
        morale=90,
    )


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


# ---------------------------------------------------------------------------
# ArtilleryMission.advance
# ---------------------------------------------------------------------------


class TestArtilleryMissionAdvance:
    def test_calling_phase_transitions_to_incoming(self):
        """Verify: CALLING -> INCOMING after CALL_DELAY_TICKS ticks."""
        mission = ArtilleryMission(
            observer_id="obs1",
            target_pos=TileCoord(20, 20),
        )
        assert mission.phase == ArtilleryPhase.CALLING
        for _ in range(CALL_DELAY_TICKS):
            mission.advance()
        assert mission.phase == ArtilleryPhase.INCOMING
        assert mission.timer == 0

    def test_incoming_phase_transitions_to_complete(self):
        """Verify: INCOMING -> COMPLETE after FIRE_DELAY_TICKS, increments salvos."""
        mission = ArtilleryMission(
            observer_id="obs1",
            target_pos=TileCoord(20, 20),
            phase=ArtilleryPhase.INCOMING,
        )
        assert mission.salvos_fired == 0
        for _ in range(FIRE_DELAY_TICKS):
            mission.advance()
        assert mission.phase == ArtilleryPhase.COMPLETE
        assert mission.salvos_fired == 1

    def test_correction_phase_transitions_to_incoming(self):
        """Verify: CORRECTION -> INCOMING after CORRECTION_DELAY_TICKS."""
        mission = ArtilleryMission(
            observer_id="obs1",
            target_pos=TileCoord(20, 20),
            phase=ArtilleryPhase.CORRECTION,
        )
        for _ in range(CORRECTION_DELAY_TICKS):
            mission.advance()
        assert mission.phase == ArtilleryPhase.INCOMING
        assert mission.timer == 0

    def test_advance_before_threshold_keeps_phase(self):
        """Verify: advance before threshold does not change phase."""
        mission = ArtilleryMission(
            observer_id="obs1",
            target_pos=TileCoord(20, 20),
        )
        mission.advance()
        assert mission.phase == ArtilleryPhase.CALLING
        assert mission.timer == 1


# ---------------------------------------------------------------------------
# ArtilleryManager.can_call_mission / start_mission
# ---------------------------------------------------------------------------


class TestCanCallAndStartMission:
    def test_fresh_manager_can_call(self):
        """Verify: new manager with ammo budget allows a mission."""
        m = ArtilleryManager()
        assert m.missions_remaining == MAX_FIRE_MISSIONS
        assert m.can_call_mission("obs1") is True

    def test_cannot_call_when_no_ammo(self):
        """Verify: zero remaining missions blocks new calls."""
        m = ArtilleryManager(max_missions=0)
        assert m.can_call_mission("obs1") is False

    def test_cannot_call_when_observer_already_active(self):
        """Verify: observer with an active mission cannot call again."""
        m = ArtilleryManager()
        m.start_mission("obs1", TileCoord(20, 20))
        assert m.can_call_mission("obs1") is False

    def test_start_mission_decrements_ammo(self):
        """Verify: start_mission reduces remaining missions and registers mission."""
        m = ArtilleryManager()
        before = m.missions_remaining
        mission = m.start_mission("obs1", TileCoord(20, 20))
        assert mission is not None
        assert m.missions_remaining == before - 1
        assert mission in m.active_missions
        assert mission.observer_id == "obs1"
        assert mission.target_pos == TileCoord(20, 20)

    def test_start_mission_returns_none_when_blocked(self):
        """Verify: start_mission returns None when cannot_call_mission."""
        m = ArtilleryManager(max_missions=0)
        assert m.start_mission("obs1", TileCoord(20, 20)) is None

    def test_start_mission_with_scatter(self):
        """Verify: start_mission preserves the scatter argument."""
        m = ArtilleryManager()
        mission = m.start_mission("obs1", TileCoord(20, 20), scatter=3)
        assert mission is not None
        assert mission.scatter == 3


# ---------------------------------------------------------------------------
# ArtilleryManager.tick
# ---------------------------------------------------------------------------


class TestManagerTick:
    def test_tick_returns_completed_missions(self):
        """Verify: tick returns missions that reached COMPLETE."""
        m = ArtilleryManager()
        m.start_mission("obs1", TileCoord(20, 20))
        impacted = []
        # CALLING -> INCOMING -> COMPLETE
        for _ in range(CALL_DELAY_TICKS + FIRE_DELAY_TICKS):
            impacted.extend(m.tick())
        assert len(impacted) == 1
        assert impacted[0].phase == ArtilleryPhase.COMPLETE

    def test_tick_removes_completed_from_active(self):
        """Verify: completed missions are removed from active_missions."""
        m = ArtilleryManager()
        m.start_mission("obs1", TileCoord(20, 20))
        for _ in range(CALL_DELAY_TICKS + FIRE_DELAY_TICKS):
            m.tick()
        assert m.active_missions == []

    def test_tick_returns_empty_when_no_active(self):
        """Verify: tick with no active missions returns empty list."""
        m = ArtilleryManager()
        assert m.tick() == []


# ---------------------------------------------------------------------------
# ArtilleryManager.calculate_impact_area
# ---------------------------------------------------------------------------


class TestCalculateImpactArea:
    def test_no_scatter_returns_centered_3x3(self):
        """Verify: zero scatter produces a 3x3 area centered on target."""
        m = ArtilleryManager()
        gm = _make_map(w=40, h=30)
        mission = ArtilleryMission(
            observer_id="obs1",
            target_pos=TileCoord(20, 20),
            scatter=0,
        )
        tiles = m.calculate_impact_area(mission, gm)
        # 3x3 = 9 tiles
        assert len(tiles) == 9
        # Center included
        assert TileCoord(20, 20) in tiles
        # Corners included
        assert TileCoord(19, 19) in tiles
        assert TileCoord(21, 21) in tiles

    def test_scatter_produces_within_bounds_tiles(self):
        """Verify: scatter still produces 9 tiles within map bounds."""
        m = ArtilleryManager()
        gm = _make_map(w=40, h=30)
        mission = ArtilleryMission(
            observer_id="obs1",
            target_pos=TileCoord(20, 20),
            scatter=2,
        )
        tiles = m.calculate_impact_area(mission, gm)
        assert len(tiles) == 9
        for t in tiles:
            assert gm.is_within_bounds(t)

    def test_impact_area_clipped_at_map_edge(self):
        """Verify: tiles outside map bounds are excluded (corner target)."""
        m = ArtilleryManager()
        gm = _make_map(w=10, h=10)
        mission = ArtilleryMission(
            observer_id="obs1",
            target_pos=TileCoord(0, 0),  # corner
            scatter=0,
        )
        tiles = m.calculate_impact_area(mission, gm)
        # Only 4 tiles in-bounds (0,0),(1,0),(0,1),(1,1)
        assert len(tiles) == 4
        assert TileCoord(0, 0) in tiles


# ---------------------------------------------------------------------------
# ArtilleryManager.apply_impact
# ---------------------------------------------------------------------------


class TestApplyImpact:
    def test_damages_units_in_impact_zone(self):
        """Verify: units on impact tiles take DAMAGE_PER_TILE damage."""
        m = ArtilleryManager()
        gm = _make_map()
        u1 = _make_unit("u1", x=20, y=20, hp=100)
        u2 = _make_unit("u2", x=25, y=25, hp=100)  # outside zone
        impact_tiles = [TileCoord(20, 20)]
        effects = m.apply_impact(impact_tiles, [u1, u2], gm)
        assert len(effects) == 1
        assert effects[0]["unit_id"] == "u1"
        assert effects[0]["damage"] == DAMAGE_PER_TILE
        assert effects[0]["source"] == "artillery"
        assert u1.health.hp == 100 - DAMAGE_PER_TILE
        assert u2.health.hp == 100  # untouched

    def test_skips_dead_units(self):
        """Verify: dead units in impact zone are not affected."""
        m = ArtilleryManager()
        gm = _make_map()
        dead = _make_unit("dead", x=20, y=20, hp=0)
        effects = m.apply_impact([TileCoord(20, 20)], [dead], gm)
        assert effects == []

    def test_applies_suppression_to_affected_units(self):
        """Verify: affected units gain SUPPRESSION_PER_TILE suppression."""
        m = ArtilleryManager()
        gm = _make_map()
        u = _make_unit("u1", x=20, y=20, hp=100)
        before = u.combat_state.suppression.current_suppression
        m.apply_impact([TileCoord(20, 20)], [u], gm)
        after = u.combat_state.suppression.current_suppression
        assert after >= before + SUPPRESSION_PER_TILE

    def test_empty_impact_zone_returns_empty(self):
        """Verify: empty impact tile list produces no effects."""
        m = ArtilleryManager()
        gm = _make_map()
        u = _make_unit("u1", x=20, y=20, hp=100)
        assert m.apply_impact([], [u], gm) == []


# ---------------------------------------------------------------------------
# ArtilleryManager.calculate_weather_scatter
# ---------------------------------------------------------------------------


class TestCalculateWeatherScatter:
    def test_none_environment_returns_zero(self):
        """Verify: None environment yields zero scatter."""
        assert ArtilleryManager.calculate_weather_scatter(None) == 0

    def test_clear_weather_returns_zero(self):
        """Verify: CLEAR weather yields zero scatter."""
        env = EnvironmentState(weather=WeatherCondition.CLEAR)
        assert ArtilleryManager.calculate_weather_scatter(env) == 0

    def test_fog_returns_fog_scatter(self):
        """Verify: FOG weather returns FOG_SCATTER."""
        env = EnvironmentState(weather=WeatherCondition.FOG)
        assert ArtilleryManager.calculate_weather_scatter(env) == FOG_SCATTER

    def test_rain_returns_rain_scatter(self):
        """Verify: RAIN weather returns RAIN_SCATTER."""
        env = EnvironmentState(weather=WeatherCondition.RAIN)
        assert ArtilleryManager.calculate_weather_scatter(env) == RAIN_SCATTER

    def test_overcast_returns_zero(self):
        """Verify: OVERCAST weather yields zero scatter (no defined penalty)."""
        env = EnvironmentState(
            time_of_day=TimeOfDay.DAY,
            weather=WeatherCondition.OVERCAST,
        )
        assert ArtilleryManager.calculate_weather_scatter(env) == 0


# ---------------------------------------------------------------------------
# ArtilleryCallinAI.evaluate
# ---------------------------------------------------------------------------


class TestAIEvaluate:
    def test_zero_when_no_observers(self):
        """Verify: evaluate returns 0.0 with no eligible observers."""
        ai = ArtilleryCallinAI()
        inf = _make_unit("inf1", x=10, y=10)  # not an observer type
        enemy = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        ctx = _make_context(friendly=[inf], enemy=[enemy])
        assert ai.evaluate(ctx) == 0.0

    def test_zero_when_no_missions_remaining(self):
        """Verify: evaluate returns 0.0 when manager has no ammo left."""
        ai = ArtilleryCallinAI(artillery_manager=ArtilleryManager(max_missions=0))
        obs = _make_observer("obs1", x=5, y=5)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        ctx = _make_context(friendly=[obs], enemy=[enemy])
        assert ai.evaluate(ctx) == 0.0

    def test_zero_when_enemy_not_concentrated(self):
        """Verify: evaluate returns 0.0 when enemies are scattered (<2)."""
        ai = ArtilleryCallinAI()
        obs = _make_observer("obs1", x=5, y=5)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        ctx = _make_context(friendly=[obs], enemy=[enemy])
        assert ai.evaluate(ctx) == 0.0

    def test_positive_when_concentrated_enemies_and_observer_with_los(self):
        """Verify: evaluate returns positive score with concentrated enemies + LOS."""
        ai = ArtilleryCallinAI()
        obs = _make_observer("obs1", x=5, y=5)
        # Cluster of 3 enemies within impact radius
        e1 = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        e2 = _make_unit("e2", faction=Faction.AXIS, x=21, y=20)
        e3 = _make_unit("e3", faction=Faction.AXIS, x=20, y=21)
        ctx = _make_context(friendly=[obs], enemy=[e1, e2, e3])
        score = ai.evaluate(ctx)
        assert 0.0 < score <= 1.0


# ---------------------------------------------------------------------------
# ArtilleryCallinAI.execute
# ---------------------------------------------------------------------------


class TestAIExecute:
    def test_issues_call_artillery_intent_for_concentrated_target(self):
        """Verify: execute issues CALL_ARTILLERY intent on densest enemy cluster."""
        ai = ArtilleryCallinAI()
        gm = _make_map(w=40, h=30)
        obs = _make_observer("obs1", x=5, y=5)
        # Cluster at (20,20) with 3 enemies
        e1 = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        e2 = _make_unit("e2", faction=Faction.AXIS, x=21, y=20)
        e3 = _make_unit("e3", faction=Faction.AXIS, x=20, y=21)
        ctx = _make_context(friendly=[obs], enemy=[e1, e2, e3], game_map=gm)
        intents = ai.execute(ctx)
        call_intents = [i for i in intents if i.tactic_type == TacticType.CALL_ARTILLERY]
        assert len(call_intents) == 1
        assert call_intents[0].unit_id == "obs1"
        assert call_intents[0].target_position in (
            TileCoord(20, 20),
            TileCoord(21, 20),
            TileCoord(20, 21),
        )
        assert call_intents[0].priority == 9

    def test_no_intent_when_target_too_close(self):
        """Verify: execute returns [] when target within MINIMUM_RANGE of observer."""
        ai = ArtilleryCallinAI()
        gm = _make_map(w=40, h=30)
        obs = _make_observer("obs1", x=5, y=5)
        # Cluster only 3 tiles away — below MINIMUM_RANGE
        e1 = _make_unit("e1", faction=Faction.AXIS, x=8, y=5)
        e2 = _make_unit("e2", faction=Faction.AXIS, x=8, y=6)
        e3 = _make_unit("e3", faction=Faction.AXIS, x=9, y=5)
        ctx = _make_context(friendly=[obs], enemy=[e1, e2, e3], game_map=gm)
        intents = ai.execute(ctx)
        call_intents = [i for i in intents if i.tactic_type == TacticType.CALL_ARTILLERY]
        assert call_intents == []

    def test_no_intent_when_no_observers(self):
        """Verify: execute returns [] when no eligible observers available."""
        ai = ArtilleryCallinAI()
        inf = _make_unit("inf1", x=10, y=10)  # not an observer
        e1 = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        e2 = _make_unit("e2", faction=Faction.AXIS, x=21, y=20)
        ctx = _make_context(friendly=[inf], enemy=[e1, e2])
        assert ai.execute(ctx) == []

    def test_no_intent_when_no_missions_remaining(self):
        """Verify: execute returns [] when manager has zero ammo."""
        ai = ArtilleryCallinAI(artillery_manager=ArtilleryManager(max_missions=0))
        obs = _make_observer("obs1", x=5, y=5)
        e1 = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        e2 = _make_unit("e2", faction=Faction.AXIS, x=21, y=20)
        ctx = _make_context(friendly=[obs], enemy=[e1, e2])
        assert ai.execute(ctx) == []

    def test_no_intent_when_friendly_in_impact_zone(self):
        """Verify: execute returns [] when friendly units are in the impact zone."""
        ai = ArtilleryCallinAI()
        gm = _make_map(w=40, h=30)
        obs = _make_observer("obs1", x=5, y=5)
        # Enemy cluster
        e1 = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        e2 = _make_unit("e2", faction=Faction.AXIS, x=21, y=20)
        # Friendly unit too close to target — friendly fire risk
        friendly_near = _make_unit("fnear", x=20, y=21)
        ctx = _make_context(friendly=[obs, friendly_near], enemy=[e1, e2], game_map=gm)
        intents = ai.execute(ctx)
        call_intents = [i for i in intents if i.tactic_type == TacticType.CALL_ARTILLERY]
        assert call_intents == []

    def test_no_intent_when_no_enemies(self):
        """Verify: execute returns [] when there are no enemies."""
        ai = ArtilleryCallinAI()
        obs = _make_observer("obs1", x=5, y=5)
        ctx = _make_context(friendly=[obs], enemy=[])
        assert ai.execute(ctx) == []


# ---------------------------------------------------------------------------
# ArtilleryCallinAI manager property / shared state
# ---------------------------------------------------------------------------


class TestAIManagerProperty:
    def test_default_manager_created(self):
        """Verify: ArtilleryCallinAI creates a default ArtilleryManager."""
        ai = ArtilleryCallinAI()
        assert isinstance(ai.manager, ArtilleryManager)
        assert ai.manager.missions_remaining == MAX_FIRE_MISSIONS

    def test_shared_manager_used(self):
        """Verify: a passed-in manager is reused (shared state)."""
        shared = ArtilleryManager(max_missions=1)
        ai = ArtilleryCallinAI(artillery_manager=shared)
        assert ai.manager is shared
        assert ai.manager.missions_remaining == 1


# ---------------------------------------------------------------------------
# ArtilleryCallinAI._enemy_concentration / _find_best_target
# ---------------------------------------------------------------------------


class TestEnemyConcentrationAndTarget:
    def test_concentration_zero_with_fewer_than_two_enemies(self):
        """Verify: concentration is 0.0 with 0 or 1 enemies."""
        ai = ArtilleryCallinAI()
        ctx0 = _make_context(enemy=[])
        assert ai._enemy_concentration(ctx0) == 0.0
        e1 = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        ctx1 = _make_context(enemy=[e1])
        assert ai._enemy_concentration(ctx1) == 0.0

    def test_concentration_increases_with_cluster_size(self):
        """Verify: tighter cluster yields higher concentration score."""
        ai = ArtilleryCallinAI()
        # 5 enemies all on the same tile = max density
        dense = [_make_unit(f"e{i}", faction=Faction.AXIS, x=20, y=20) for i in range(5)]
        ctx_dense = _make_context(enemy=dense)
        score_dense = ai._enemy_concentration(ctx_dense)
        assert score_dense == 1.0  # 5/5 normalized to 1.0

    def test_find_best_target_returns_densest_position(self):
        """Verify: _find_best_target returns the tile with most neighbors."""
        ai = ArtilleryCallinAI()
        # Cluster of 3 at (20,20), loner at (5,5)
        e1 = _make_unit("e1", faction=Faction.AXIS, x=20, y=20)
        e2 = _make_unit("e2", faction=Faction.AXIS, x=21, y=20)
        e3 = _make_unit("e3", faction=Faction.AXIS, x=20, y=21)
        loner = _make_unit("loner", faction=Faction.AXIS, x=5, y=5)
        ctx = _make_context(enemy=[e1, e2, e3, loner])
        target = ai._find_best_target(ctx)
        assert target == TileCoord(20, 20)

    def test_find_best_target_none_when_no_enemies(self):
        """Verify: _find_best_target returns None when no enemies."""
        ai = ArtilleryCallinAI()
        ctx = _make_context(enemy=[])
        assert ai._find_best_target(ctx) is None


# ---------------------------------------------------------------------------
# ArtilleryCallinAI._best_observer_for / _friendly_in_impact_zone
# ---------------------------------------------------------------------------


class TestBestObserverAndFriendlyCheck:
    def test_best_observer_chooses_closest_with_los(self):
        """Verify: _best_observer_for returns the closest observer with LOS."""
        ai = ArtilleryCallinAI()
        gm = _make_map(w=40, h=30)
        obs_near = _make_observer("near", x=10, y=10)
        obs_far = _make_observer("far", x=2, y=2)
        target = TileCoord(25, 25)
        ctx = _make_context(friendly=[obs_near, obs_far], game_map=gm)
        best = ai._best_observer_for([obs_near, obs_far], target, ctx)
        # Both have LOS on open map; near (distance 15) beats far (distance ~23)
        assert best is not None
        assert best.id == "near"

    def test_best_observer_excludes_below_minimum_range(self):
        """Verify: observer within MINIMUM_RANGE of target is excluded."""
        ai = ArtilleryCallinAI()
        gm = _make_map(w=40, h=30)
        obs = _make_observer("obs", x=10, y=10)
        # Target only MINIMUM_RANGE-2 tiles away — well below the minimum
        target = TileCoord(10 + MINIMUM_RANGE - 2, 10)
        assert obs.position.tile_coord.chebyshev_distance(target) < MINIMUM_RANGE
        ctx = _make_context(friendly=[obs], game_map=gm)
        assert ai._best_observer_for([obs], target, ctx) is None

    def test_best_observer_none_when_no_los(self):
        """Verify: observer without LOS is excluded.

        Scenario: place a BUILDING_SOLID wall between observer and target.
        Expected: no candidate with LOS, returns None.
        """
        ai = ArtilleryCallinAI()
        h, w = 5, 30
        grid = np.zeros((h, w), dtype=np.int8)
        # Solid wall at column 15 blocks LOS from (0,2) to (25,2)
        grid[0, 15] = 5  # BUILDING_SOLID
        grid[1, 15] = 5
        grid[2, 15] = 5
        grid[3, 15] = 5
        grid[4, 15] = 5
        gm = GameMap(id="t", name="t", width=w, height=h, tile_grid=grid)
        obs = _make_observer("obs", x=0, y=2)
        target = TileCoord(25, 2)
        ctx = _make_context(friendly=[obs], game_map=gm)
        assert ai._best_observer_for([obs], target, ctx) is None

    def test_friendly_in_impact_zone_true_when_close(self):
        """Verify: _friendly_in_impact_zone True when friendly within radius."""
        ai = ArtilleryCallinAI()
        target = TileCoord(20, 20)
        friendly_close = _make_unit("fc", x=21, y=20)
        ctx = _make_context(friendly=[friendly_close])
        assert ai._friendly_in_impact_zone(target, ctx) is True

    def test_friendly_in_impact_zone_false_when_far(self):
        """Verify: _friendly_in_impact_zone False when friendly far away."""
        ai = ArtilleryCallinAI()
        target = TileCoord(20, 20)
        friendly_far = _make_unit("ff", x=5, y=5)
        ctx = _make_context(friendly=[friendly_far])
        assert ai._friendly_in_impact_zone(target, ctx) is False
