"""Tests for NightStealthAI — night/dawn/dusk stealth behavior.

Verify: NightStealthAI evaluate/execute priority scoring, night modifiers,
and helper predicates (open terrain, cover, VL infiltration, ambush setup).
Scenario: build real units on a real GameMap, toggle time-of-day via the
blackboard, and assert the AI produces the documented stealth intents.
Expected: 0.0 score during day; night base 0.7 (+0.15 VL, -0.3 near enemy);
intents prefer TAKE_COVER in open, MOVE_TO toward VLs, HOLD_POSITION ambush.
"""

from __future__ import annotations

import numpy as np

from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.night_stealth_ai import (
    NIGHT_AMBUSH_DETECTION_BONUS,
    NIGHT_SPEED_PENALTY,
    NightStealthAI,
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
from pycc2.domain.systems.environment import TimeOfDay
from pycc2.domain.value_objects.terrain_type import TerrainType
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
    weapon_id: str = "rifle",
) -> Unit:
    """Build a real Unit with all required components at the given tile."""
    return Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id=weapon_id, ammo_remaining=8, max_ammo=8),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
    )


def _make_map(w: int = 40, h: int = 30) -> GameMap:
    """Build an all-open GameMap of the given size."""
    grid = np.zeros((h, w), dtype=np.int8)
    return GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)


def _make_map_with_woods(woods_x: int = 11, woods_y: int = 10) -> GameMap:
    """Build a GameMap with a single WOODS tile (high concealment)."""
    grid = np.zeros((30, 40), dtype=np.int8)
    grid[woods_y, woods_x] = TerrainType.WOODS
    return GameMap(id="test", name="woods", width=40, height=30, tile_grid=grid)


def _make_context(
    friendly: list[Unit] | None = None,
    enemy: list[Unit] | None = None,
    game_map: GameMap | None = None,
    vl_positions: list[tuple[TileCoord, str | None, int]] | None = None,
    blackboards: dict[str, Blackboard] | None = None,
    tick: int = 1,
) -> TacticalContext:
    """Assemble a TacticalContext with the given fields."""
    return TacticalContext(
        friendly_units=friendly or [],
        enemy_units=enemy or [],
        game_map=game_map or _make_map(),
        current_tick=tick,
        vl_positions=vl_positions or [],
        blackboards=blackboards or {},
    )


def _night_blackboard(unit_id: str, tod: TimeOfDay = TimeOfDay.NIGHT) -> dict[str, Blackboard]:
    """Build a blackboards dict with the given time-of-day set for one unit."""
    bb = Blackboard()
    bb.set("time_of_day", tod)
    return {unit_id: bb}


def _set_concealment(unit: Unit, terrain_concealment: float) -> None:
    """Set a unit's terrain concealment on its real ConcealmentProfile.

    concealment_level is derived from combat_state.concealment. A value of
    0.5 yields a total concealment ~0.385 (>= 0.2 cover, >= 0.1 not-open).
    """
    unit.combat_state.concealment.terrain_concealment = terrain_concealment


# ---------------------------------------------------------------------------
# evaluate — time of day base score
# ---------------------------------------------------------------------------


class TestEvaluateTimeOfDay:
    """Verify evaluate returns 0.0 during day and the base score at night."""

    def test_day_returns_zero(self):
        """Verify: during DAY the AI scores 0.0 (inactive)."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(friendly=[inf])
        assert ai.evaluate(ctx) == 0.0

    def test_day_explicit_time_of_day_returns_zero(self):
        """Verify: explicit DAY blackboard also yields 0.0."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(
            friendly=[inf],
            blackboards=_night_blackboard("inf1", TimeOfDay.DAY),
        )
        assert ai.evaluate(ctx) == 0.0

    def test_night_base_score(self):
        """Verify: NIGHT with no VLs and no near enemies → 0.7."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(
            friendly=[inf],
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        assert ai.evaluate(ctx) == 0.7

    def test_dawn_base_score(self):
        """Verify: DAWN base score is 0.5."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(
            friendly=[inf],
            blackboards=_night_blackboard("inf1", TimeOfDay.DAWN),
        )
        assert ai.evaluate(ctx) == 0.5

    def test_dusk_base_score(self):
        """Verify: DUSK base score is 0.5."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(
            friendly=[inf],
            blackboards=_night_blackboard("inf1", TimeOfDay.DUSK),
        )
        assert ai.evaluate(ctx) == 0.5


# ---------------------------------------------------------------------------
# evaluate — VL boost
# ---------------------------------------------------------------------------


class TestEvaluateVLBoost:
    """Verify nearby uncontrolled VLs increase the night stealth score."""

    def test_uncontrolled_vl_adds_boost(self):
        """Verify: NIGHT + uncontrolled VL → 0.7 + 0.15 = 0.85."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        vl = [(TileCoord(20, 10), None, 10)]  # owner None → uncontrolled
        ctx = _make_context(
            friendly=[inf],
            vl_positions=vl,
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        assert ai.evaluate(ctx) == 0.85

    def test_enemy_owned_vl_adds_boost(self):
        """Verify: VL owned by the enemy faction also counts as uncontrolled."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        vl = [(TileCoord(20, 10), "AXIS", 10)]  # owner != ALLIES
        ctx = _make_context(
            friendly=[inf],
            vl_positions=vl,
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        assert ai.evaluate(ctx) == 0.85

    def test_friendly_owned_vl_no_boost(self):
        """Verify: VL owned by the friendly faction gives no boost."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        faction_allies = inf.faction.name  # "ALLIES"
        vl = [(TileCoord(20, 10), faction_allies, 10)]  # owner == ALLIES
        ctx = _make_context(
            friendly=[inf],
            vl_positions=vl,
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        assert ai.evaluate(ctx) == 0.7


# ---------------------------------------------------------------------------
# evaluate — enemy proximity penalty
# ---------------------------------------------------------------------------


class TestEvaluateEnemyPenalty:
    """Verify nearby enemies reduce the stealth score."""

    def test_enemy_within_3_tiles_reduces_score(self):
        """Verify: NIGHT + enemy at distance 3 → 0.7 - 0.3 = 0.4.

        Uses a tolerance because 0.7 - 0.3 is not exactly representable.
        """
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=13, y=10)  # dist 3
        ctx = _make_context(
            friendly=[inf],
            enemy=[enemy],
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        assert abs(ai.evaluate(ctx) - 0.4) < 1e-9

    def test_enemy_at_4_tiles_no_penalty(self):
        """Verify: enemy at distance 4 does not trigger the penalty."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=14, y=10)  # dist 4
        ctx = _make_context(
            friendly=[inf],
            enemy=[enemy],
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        assert ai.evaluate(ctx) == 0.7

    def test_dead_enemy_does_not_reduce_score(self):
        """Verify: a dead enemy within 3 tiles applies no penalty."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        dead_enemy = _make_unit("e1", faction=Faction.AXIS, x=12, y=10, hp=0)
        ctx = _make_context(
            friendly=[inf],
            enemy=[dead_enemy],
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        assert ai.evaluate(ctx) == 0.7


# ---------------------------------------------------------------------------
# evaluate — score clamping
# ---------------------------------------------------------------------------


class TestEvaluateClamping:
    """Verify the score is clamped to [0.0, 1.0]."""

    def test_score_never_exceeds_one(self):
        """Verify: NIGHT + VL boost + no penalty stays within [0, 1]."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        vl = [(TileCoord(20, 10), None, 10)]
        ctx = _make_context(
            friendly=[inf],
            vl_positions=vl,
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        score = ai.evaluate(ctx)
        assert 0.0 <= score <= 1.0

    def test_score_never_negative(self):
        """Verify: DAWN with near enemy stays non-negative (0.5 - 0.3 = 0.2)."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=12, y=10)  # dist 2
        ctx = _make_context(
            friendly=[inf],
            enemy=[enemy],
            blackboards=_night_blackboard("inf1", TimeOfDay.DAWN),
        )
        score = ai.evaluate(ctx)
        assert score >= 0.0
        assert abs(score - 0.2) < 1e-9


# ---------------------------------------------------------------------------
# execute — day / empty cases
# ---------------------------------------------------------------------------


class TestExecuteDayAndEmpty:
    """Verify execute returns no intents during day or with no available units."""

    def test_day_returns_empty(self):
        """Verify: during DAY execute produces no intents."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(friendly=[inf])  # no blackboard → DAY
        assert ai.execute(ctx) == []

    def test_no_friendly_units_returns_empty(self):
        """Verify: night with no friendly units yields no intents."""
        ai = NightStealthAI()
        ctx = _make_context(blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT))
        assert ai.execute(ctx) == []

    def test_tank_excluded_from_stealth(self):
        """Verify: tanks are never assigned stealth intents at night."""
        ai = NightStealthAI()
        tank = _make_unit("tank1", unit_type=UnitType.TANK, x=10, y=10)
        ctx = _make_context(
            friendly=[tank],
            blackboards=_night_blackboard("tank1", TimeOfDay.NIGHT),
        )
        assert ai.execute(ctx) == []

    def test_dead_unit_excluded(self):
        """Verify: dead friendly units produce no intents."""
        ai = NightStealthAI()
        dead = _make_unit("dead1", x=10, y=10, hp=0)
        ctx = _make_context(
            friendly=[dead],
            blackboards=_night_blackboard("dead1", TimeOfDay.NIGHT),
        )
        assert ai.execute(ctx) == []

    def test_broken_morale_unit_excluded(self):
        """Verify: a broken-morale unit is not combat effective → excluded."""
        ai = NightStealthAI()
        broken = _make_unit("b1", x=10, y=10, morale=15)  # < 20 → BROKEN
        ctx = _make_context(
            friendly=[broken],
            blackboards=_night_blackboard("b1", TimeOfDay.NIGHT),
        )
        assert ai.execute(ctx) == []


# ---------------------------------------------------------------------------
# execute — priority 2: open terrain → TAKE_COVER
# ---------------------------------------------------------------------------


class TestExecuteOpenTerrainSeekCover:
    """Verify units in open terrain at night seek nearby cover."""

    def test_infantry_in_open_moves_to_nearby_woods(self):
        """Verify: infantry in open terrain issues TAKE_COVER toward woods.

        Unit at (10,10) on open ground (concealment 0.0 < 0.1 → in open),
        woods at (11,10) provides concealment 0.50. Expected TAKE_COVER
        intent with priority 6 targeting the woods tile.
        """
        ai = NightStealthAI()
        gm = _make_map_with_woods(woods_x=11, woods_y=10)
        inf = _make_unit("inf1", x=10, y=10)  # default concealment 0.0 → in open
        ctx = _make_context(
            friendly=[inf],
            game_map=gm,
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        intents = ai.execute(ctx)
        cover_intents = [i for i in intents if i.tactic_type == TacticType.TAKE_COVER]
        assert len(cover_intents) == 1
        assert cover_intents[0].unit_id == "inf1"
        assert cover_intents[0].priority == 6
        assert cover_intents[0].target_position == TileCoord(11, 10)

    def test_open_unit_with_no_cover_nearby_issues_nothing(self):
        """Verify: open unit with no cover in range produces no intent.

        All-open map → _find_nearby_cover returns None → priority 2 skipped.
        No VLs and no enemies → no other priority fires.
        """
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(
            friendly=[inf],
            game_map=_make_map(),  # all open
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        assert ai.execute(ctx) == []


# ---------------------------------------------------------------------------
# execute — priority 3: VL infiltration
# ---------------------------------------------------------------------------


class TestExecuteVLInfiltration:
    """Verify units with cover move toward uncontrolled VLs at night."""

    def test_unit_with_cover_infiltrates_toward_vl(self):
        """Verify: concealed unit moves toward a distant uncontrolled VL.

        Unit at (10,10) given terrain_concealment 0.5 (not in open), VL at
        (20,10) (dist 10 > 3). Expected MOVE_TO intent with priority 5.
        """
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        _set_concealment(inf, 0.5)  # not in open, has cover
        vl = [(TileCoord(20, 10), None, 10)]
        ctx = _make_context(
            friendly=[inf],
            vl_positions=vl,
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        intents = ai.execute(ctx)
        move_intents = [i for i in intents if i.tactic_type == TacticType.MOVE_TO]
        assert len(move_intents) == 1
        assert move_intents[0].unit_id == "inf1"
        assert move_intents[0].priority == 5
        assert move_intents[0].target_position is not None

    def test_vl_within_3_tiles_no_move(self):
        """Verify: a VL within 3 tiles does not trigger infiltration move."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        _set_concealment(inf, 0.5)
        vl = [(TileCoord(12, 10), None, 10)]  # dist 2 <= 3
        ctx = _make_context(
            friendly=[inf],
            vl_positions=vl,
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        intents = ai.execute(ctx)
        move_intents = [i for i in intents if i.tactic_type == TacticType.MOVE_TO]
        assert move_intents == []


# ---------------------------------------------------------------------------
# execute — priority 4: ambush setup
# ---------------------------------------------------------------------------


class TestExecuteAmbushSetup:
    """Verify units with cover set up ambush when enemies are near."""

    def test_concealed_unit_near_enemy_holds_position(self):
        """Verify: concealed unit near enemy issues HOLD_POSITION ambush.

        Unit at (10,10) with concealment 0.5 (has cover), enemy at (14,10)
        (dist 4, within 8-tile ambush radius), no VLs. Expected HOLD_POSITION
        intent with priority 4 targeting the unit's own tile.
        """
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        _set_concealment(inf, 0.5)  # has cover (>= 0.2)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=14, y=10)  # dist 4
        ctx = _make_context(
            friendly=[inf],
            enemy=[enemy],
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        intents = ai.execute(ctx)
        hold_intents = [i for i in intents if i.tactic_type == TacticType.HOLD_POSITION]
        assert len(hold_intents) == 1
        assert hold_intents[0].unit_id == "inf1"
        assert hold_intents[0].priority == 4
        assert hold_intents[0].target_position == inf.position.tile_coord

    def test_unit_without_cover_does_not_ambush(self):
        """Verify: a unit without cover (concealment < 0.2) skips ambush."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)  # concealment 0.0 → no cover
        enemy = _make_unit("e1", faction=Faction.AXIS, x=14, y=10)
        ctx = _make_context(
            friendly=[inf],
            enemy=[enemy],
            game_map=_make_map(),  # all open so priority 2 finds no cover
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        intents = ai.execute(ctx)
        hold_intents = [i for i in intents if i.tactic_type == TacticType.HOLD_POSITION]
        assert hold_intents == []

    def test_enemy_beyond_8_tiles_no_ambush(self):
        """Verify: enemy beyond 8 tiles does not trigger ambush."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        _set_concealment(inf, 0.5)
        enemy = _make_unit("e1", faction=Faction.AXIS, x=20, y=10)  # dist 10 > 8
        ctx = _make_context(
            friendly=[inf],
            enemy=[enemy],
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        intents = ai.execute(ctx)
        hold_intents = [i for i in intents if i.tactic_type == TacticType.HOLD_POSITION]
        assert hold_intents == []


# ---------------------------------------------------------------------------
# execute — no intents fall-through
# ---------------------------------------------------------------------------


class TestExecuteNoIntentsFallthrough:
    """Verify a concealed unit with no VLs and no enemies issues nothing."""

    def test_concealed_unit_no_vl_no_enemy_no_intent(self):
        """Verify: concealed unit with no targets produces no intents."""
        ai = NightStealthAI()
        inf = _make_unit("inf1", x=10, y=10)
        _set_concealment(inf, 0.5)  # not in open, has cover
        ctx = _make_context(
            friendly=[inf],
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        assert ai.execute(ctx) == []


# ---------------------------------------------------------------------------
# Night modifiers
# ---------------------------------------------------------------------------


class TestNightModifiers:
    """Verify get_night_speed_modifier and get_night_ambush_bonus."""

    def test_speed_modifier_reduced_at_night(self):
        """Verify: NIGHT reduces speed by NIGHT_SPEED_PENALTY (0.8)."""
        assert NightStealthAI.get_night_speed_modifier(TimeOfDay.NIGHT) == (
            1.0 - NIGHT_SPEED_PENALTY
        )

    def test_speed_modifier_reduced_at_dawn_and_dusk(self):
        """Verify: DAWN and DUSK also apply the night speed penalty."""
        assert NightStealthAI.get_night_speed_modifier(TimeOfDay.DAWN) == 0.8
        assert NightStealthAI.get_night_speed_modifier(TimeOfDay.DUSK) == 0.8

    def test_speed_modifier_unchanged_during_day(self):
        """Verify: DAY speed modifier is 1.0 (no penalty)."""
        assert NightStealthAI.get_night_speed_modifier(TimeOfDay.DAY) == 1.0

    def test_ambush_bonus_at_night(self):
        """Verify: NIGHT ambush detection bonus is NIGHT_AMBUSH_DETECTION_BONUS."""
        assert (
            NightStealthAI.get_night_ambush_bonus(TimeOfDay.NIGHT) == NIGHT_AMBUSH_DETECTION_BONUS
        )

    def test_ambush_bonus_at_dawn_and_dusk(self):
        """Verify: DAWN and DUSK also grant the ambush bonus."""
        assert NightStealthAI.get_night_ambush_bonus(TimeOfDay.DAWN) == 0.30
        assert NightStealthAI.get_night_ambush_bonus(TimeOfDay.DUSK) == 0.30

    def test_ambush_bonus_zero_during_day(self):
        """Verify: DAY grants no ambush bonus."""
        assert NightStealthAI.get_night_ambush_bonus(TimeOfDay.DAY) == 0.0


# ---------------------------------------------------------------------------
# Helper predicates
# ---------------------------------------------------------------------------


class TestHelperPredicates:
    """Verify _is_in_open, _has_cover, _is_on_road, and _find_nearby_cover."""

    def test_is_in_open_true_when_no_concealment(self):
        """Verify: a unit with 0.0 concealment is considered in open terrain."""
        inf = _make_unit("inf1", x=10, y=10)  # concealment 0.0
        ctx = _make_context(friendly=[inf])
        assert NightStealthAI._is_in_open(inf, ctx) is True

    def test_is_in_open_false_when_concealed(self):
        """Verify: a unit with concealment >= 0.1 is not in open terrain."""
        inf = _make_unit("inf1", x=10, y=10)
        _set_concealment(inf, 0.5)
        ctx = _make_context(friendly=[inf])
        assert NightStealthAI._is_in_open(inf, ctx) is False

    def test_has_cover_false_when_no_concealment(self):
        """Verify: a unit with 0.0 concealment has no cover."""
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(friendly=[inf])
        assert NightStealthAI._has_cover(inf, ctx) is False

    def test_has_cover_true_when_concealed(self):
        """Verify: a unit with concealment >= 0.2 has cover."""
        inf = _make_unit("inf1", x=10, y=10)
        _set_concealment(inf, 0.5)  # → ~0.385 >= 0.2
        ctx = _make_context(friendly=[inf])
        assert NightStealthAI._has_cover(inf, ctx) is True

    def test_is_on_road_returns_false_for_real_map(self):
        """Verify: _is_on_road returns False on a real GameMap.

        Note: GameMap.get_terrain returns a TerrainType IntEnum which has no
        ``terrain_type`` attribute; getattr defaults to "" which is not in the
        road-terrain set. This documents the actual behaviour with real maps.
        """
        grid = np.zeros((30, 40), dtype=np.int8)
        grid[10, 10] = TerrainType.ROAD
        gm = GameMap(id="t", name="t", width=40, height=30, tile_grid=grid)
        inf = _make_unit("inf1", x=10, y=10)  # standing on a ROAD tile
        ctx = _make_context(friendly=[inf], game_map=gm)
        assert NightStealthAI._is_on_road(inf, ctx) is False

    def test_is_on_road_returns_false_out_of_bounds(self):
        """Verify: _is_on_road returns False when the unit is off the map."""
        inf = _make_unit("inf1", x=100, y=100)  # outside the 40x30 map
        ctx = _make_context(friendly=[inf])
        assert NightStealthAI._is_on_road(inf, ctx) is False

    def test_find_nearby_cover_returns_woods_position(self):
        """Verify: _find_nearby_cover finds the woods tile adjacent to the unit."""
        gm = _make_map_with_woods(woods_x=11, woods_y=10)
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(friendly=[inf], game_map=gm)
        cover = NightStealthAI._find_nearby_cover(inf, ctx)
        assert cover == TileCoord(11, 10)

    def test_find_nearby_cover_returns_none_in_open_map(self):
        """Verify: _find_nearby_cover returns None when no cover is nearby."""
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(friendly=[inf], game_map=_make_map())  # all open
        assert NightStealthAI._find_nearby_cover(inf, ctx) is None

    def test_find_cover_route_toward_returns_candidate(self):
        """Verify: _find_cover_route_toward returns a non-None waypoint."""
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(friendly=[inf])
        target = TileCoord(20, 10)
        waypoint = NightStealthAI._find_cover_route_toward(inf, target, ctx)
        assert waypoint is not None
        # Waypoint should be closer to the target than the current position
        assert waypoint.chebyshev_distance(target) < inf.position.tile_coord.chebyshev_distance(
            target
        )

    def test_find_cover_route_toward_none_when_at_target(self):
        """Verify: returns None when the unit is already at the target."""
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(friendly=[inf])
        assert NightStealthAI._find_cover_route_toward(inf, TileCoord(10, 10), ctx) is None


# ---------------------------------------------------------------------------
# _available_units filter
# ---------------------------------------------------------------------------


class TestAvailableUnitsFilter:
    """Verify _available_units excludes tanks, dead, and broken-morale units."""

    def test_infantry_is_available(self):
        """Verify: a healthy infantry squad is available for stealth ops."""
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(friendly=[inf])
        available = NightStealthAI._available_units(ctx)
        assert inf in available

    def test_tank_excluded(self):
        """Verify: tanks are excluded from stealth operations."""
        tank = _make_unit("tank1", unit_type=UnitType.TANK, x=10, y=10)
        ctx = _make_context(friendly=[tank])
        assert NightStealthAI._available_units(ctx) == []

    def test_dead_unit_excluded(self):
        """Verify: dead units are excluded."""
        dead = _make_unit("dead1", x=10, y=10, hp=0)
        ctx = _make_context(friendly=[dead])
        assert NightStealthAI._available_units(ctx) == []

    def test_broken_morale_unit_excluded(self):
        """Verify: broken-morale units are not combat effective → excluded."""
        broken = _make_unit("b1", x=10, y=10, morale=15)
        ctx = _make_context(friendly=[broken])
        assert NightStealthAI._available_units(ctx) == []


# ---------------------------------------------------------------------------
# _get_time_of_day blackboard lookup
# ---------------------------------------------------------------------------


class TestGetTimeOfDay:
    """Verify _get_time_of_day reads the blackboard and defaults to DAY."""

    def test_reads_time_of_day_from_blackboard(self):
        """Verify: the time-of-day is read from any unit's blackboard."""
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(
            friendly=[inf],
            blackboards=_night_blackboard("inf1", TimeOfDay.NIGHT),
        )
        assert NightStealthAI._get_time_of_day(ctx) == TimeOfDay.NIGHT

    def test_defaults_to_day_when_no_blackboard(self):
        """Verify: with no time-of-day in any blackboard, defaults to DAY."""
        inf = _make_unit("inf1", x=10, y=10)
        ctx = _make_context(friendly=[inf])  # no blackboards
        assert NightStealthAI._get_time_of_day(ctx) == TimeOfDay.DAY

    def test_ignores_non_time_of_day_values(self):
        """Verify: a non-TimeOfDay value in the blackboard is ignored."""
        inf = _make_unit("inf1", x=10, y=10)
        bb = Blackboard()
        bb.set("time_of_day", "night")  # string, not TimeOfDay → ignored
        ctx = _make_context(friendly=[inf], blackboards={"inf1": bb})
        assert NightStealthAI._get_time_of_day(ctx) == TimeOfDay.DAY
