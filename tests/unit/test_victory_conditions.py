from __future__ import annotations

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.victory_conditions import (
    BattleStats,
    GameResult,
    Objective,
    VictoryConditionEvaluator,
    VictoryConditionType,
)
from pycc2.domain.value_objects.tile_coord import TileCoord


def _make_unit(
    id: str = "u1",
    name: str = "Test Unit",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    max_hp: int = 100,
    morale_value: int = 80,
    tile_x: int = 0,
    tile_y: int = 0,
) -> Unit:
    return Unit(
        id=id,
        name=name,
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale_value),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=TileCoord(x=tile_x, y=tile_y)),
        vision=VisionComponent(range_tiles=5),
    )


class TestBattleStats:
    def test_initial_state(self):
        stats = BattleStats()
        assert stats.allies_kills == 0
        assert stats.axis_kills == 0
        assert stats.allies_damage_dealt == 0.0
        assert stats.axis_damage_dealt == 0.0
        assert stats.allies_units_lost == 0
        assert stats.axis_units_lost == 0
        assert stats.shots_fired_allies == 0
        assert stats.shots_fired_axis == 0
        assert stats.shots_hit_allies == 0
        assert stats.shots_hit_axis == 0
        assert stats.ticks_elapsed == 0

    def test_record_kill_allies(self):
        stats = BattleStats()
        stats.record_kill("allies")
        assert stats.allies_kills == 1
        assert stats.axis_kills == 0

    def test_record_kill_axis(self):
        stats = BattleStats()
        stats.record_kill("axis")
        assert stats.axis_kills == 1
        assert stats.allies_kills == 0

    def test_record_damage_tracking(self):
        stats = BattleStats()
        stats.record_damage("allies", 25.5)
        stats.record_damage("axis", 15.0)
        assert stats.allies_damage_dealt == 25.5
        assert stats.axis_damage_dealt == 15.0

    def test_record_shot_hit(self):
        stats = BattleStats()
        stats.record_shot("allies", hit=True)
        assert stats.shots_fired_allies == 1
        assert stats.shots_hit_allies == 1

    def test_record_shot_miss(self):
        stats = BattleStats()
        stats.record_shot("axis", hit=False)
        assert stats.shots_fired_axis == 1
        assert stats.shots_hit_axis == 0

    def test_record_unit_lost_allies(self):
        stats = BattleStats()
        stats.record_unit_lost("allies")
        assert stats.allies_units_lost == 1
        assert stats.axis_units_lost == 0

    def test_record_unit_lost_axis(self):
        stats = BattleStats()
        stats.record_unit_lost("axis")
        assert stats.axis_units_lost == 1
        assert stats.allies_units_lost == 0

    def test_allies_accuracy_calculation(self):
        stats = BattleStats()
        stats.record_shot("allies", hit=True)
        stats.record_shot("allies", hit=True)
        stats.record_shot("allies", hit=False)
        assert abs(stats.allies_accuracy - 2 / 3) < 1e-9

    def test_allies_accuracy_zero_when_no_shots(self):
        stats = BattleStats()
        assert stats.allies_accuracy == 0.0

    def test_axis_accuracy_calculation(self):
        stats = BattleStats()
        stats.record_shot("axis", hit=True)
        stats.record_shot("axis", hit=False)
        stats.record_shot("axis", hit=False)
        assert abs(stats.axis_accuracy - 1 / 3) < 1e-9

    def test_axis_accuracy_zero_when_no_shots(self):
        stats = BattleStats()
        assert stats.axis_accuracy == 0.0

    def test_kill_ratio_normal(self):
        stats = BattleStats()
        stats.record_kill("allies")
        stats.record_kill("allies")
        stats.record_kill("allies")
        stats.record_kill("axis")
        stats.record_kill("axis")
        assert abs(stats.kill_ratio - 3 / 2) < 1e-9

    def test_kill_ratio_zero_axis_kills(self):
        stats = BattleStats()
        stats.record_kill("allies")
        stats.record_kill("allies")
        assert stats.kill_ratio == 2.0

    def test_kill_ratio_both_zero(self):
        stats = BattleStats()
        assert stats.kill_ratio == 0.0

    def test_summary_dict_contents(self):
        stats = BattleStats()
        stats.record_kill("allies")
        stats.record_damage("axis", 10.0)
        stats.record_shot("allies", hit=True)
        d = stats.summary_dict()
        assert isinstance(d, dict)
        assert d["allies_kills"] == 1
        assert d["axis_damage_dealt"] == 10.0
        assert "allies_accuracy" in d
        assert "axis_accuracy" in d
        assert "kill_ratio" in d
        assert "ticks_elapsed" in d


class TestVictoryConditionEvaluator:
    def _make_evaluator(
        self,
        conditions: list[VictoryConditionType] | None = None,
        objectives: list[Objective] | None = None,
        time_limit_ticks: int = 0,
        morale_threshold: int = 10,
    ) -> VictoryConditionEvaluator:
        return VictoryConditionEvaluator(
            conditions=conditions,
            objectives=objectives,
            time_limit_ticks=time_limit_ticks,
            morale_threshold=morale_threshold,
        )

    def test_default_conditions(self):
        ev = self._make_evaluator()
        assert VictoryConditionType.ELIMINATE_ENEMY_COMMANDER in ev.conditions
        assert VictoryConditionType.ELIMINATE_ALL_ENEMIES in ev.conditions

    def test_eliminate_commander_allies_win(self):
        ev = self._make_evaluator(conditions=[VictoryConditionType.ELIMINATE_ENEMY_COMMANDER])
        allies_cmd = _make_unit(id="ac", unit_type=UnitType.COMMANDER, faction=Faction.ALLIES)
        allies_inf = _make_unit(id="ai", faction=Faction.ALLIES)
        axis_inf = _make_unit(id="xi", faction=Faction.AXIS)
        units = [allies_cmd, allies_inf, axis_inf]
        result, reason = ev.evaluate(units, tick=0)
        assert result == GameResult.ALLIES_VICTORY
        assert "commander" in reason.lower()

    def test_eliminate_commander_axis_win(self):
        ev = self._make_evaluator(conditions=[VictoryConditionType.ELIMINATE_ENEMY_COMMANDER])
        axis_cmd = _make_unit(id="xc", unit_type=UnitType.COMMANDER, faction=Faction.AXIS)
        allies_inf = _make_unit(id="ai", faction=Faction.ALLIES)
        axis_inf = _make_unit(id="xi", faction=Faction.AXIS)
        units = [axis_cmd, allies_inf, axis_inf]
        result, reason = ev.evaluate(units, tick=0)
        assert result == GameResult.AXIS_VICTORY
        assert "commander" in reason.lower()

    def test_eliminate_all_enemies_allies_win(self):
        ev = self._make_evaluator(conditions=[VictoryConditionType.ELIMINATE_ALL_ENEMIES])
        allies_cmd = _make_unit(id="ac", unit_type=UnitType.COMMANDER, faction=Faction.ALLIES)
        allies_inf = _make_unit(id="ai", faction=Faction.ALLIES)
        axis_dead = _make_unit(id="xd", faction=Faction.AXIS, hp=0)
        units = [allies_cmd, allies_inf, axis_dead]
        result, reason = ev.evaluate(units, tick=0)
        assert result == GameResult.ALLIES_VICTORY
        assert "destroyed" in reason.lower()

    def test_eliminate_all_enemies_axis_win(self):
        ev = self._make_evaluator(conditions=[VictoryConditionType.ELIMINATE_ALL_ENEMIES])
        axis_cmd = _make_unit(id="xc", unit_type=UnitType.COMMANDER, faction=Faction.AXIS)
        axis_inf = _make_unit(id="xi", faction=Faction.AXIS)
        allies_dead = _make_unit(id="ad", faction=Faction.ALLIES, hp=0)
        units = [axis_cmd, axis_inf, allies_dead]
        result, reason = ev.evaluate(units, tick=0)
        assert result == GameResult.AXIS_VICTORY
        assert "destroyed" in reason.lower()

    def test_both_sides_dead_is_draw(self):
        ev = self._make_evaluator(
            conditions=[
                VictoryConditionType.ELIMINATE_ENEMY_COMMANDER,
                VictoryConditionType.ELIMINATE_ALL_ENEMIES,
            ]
        )
        allies_dead = _make_unit(id="ad", faction=Faction.ALLIES, hp=0)
        axis_dead = _make_unit(id="xd", faction=Faction.AXIS, hp=0)
        units = [allies_dead, axis_dead]
        result, _ = ev.evaluate(units, tick=0)
        assert result == GameResult.ONGOING

    def test_no_one_dead_is_ongoing(self):
        ev = self._make_evaluator()
        allies_inf = _make_unit(id="ai", faction=Faction.ALLIES)
        axis_inf = _make_unit(id="xi", faction=Faction.AXIS)
        units = [allies_inf, axis_inf]
        result, reason = ev.evaluate(units, tick=0)
        assert result == GameResult.ONGOING
        assert reason == ""

    def test_morale_collapse_allies_win(self):
        ev = self._make_evaluator(
            conditions=[VictoryConditionType.MORALE_COLLAPSE],
            morale_threshold=10,
        )
        allies_inf = _make_unit(id="ai", faction=Faction.ALLIES, morale_value=80)
        axis_low = _make_unit(id="xl", faction=Faction.AXIS, morale_value=5)
        units = [allies_inf, axis_low]
        result, reason = ev.evaluate(units, tick=0)
        assert result == GameResult.ALLIES_VICTORY
        assert "morale" in reason.lower()

    def test_morale_collapse_axis_win(self):
        ev = self._make_evaluator(
            conditions=[VictoryConditionType.MORALE_COLLAPSE],
            morale_threshold=10,
        )
        allies_low = _make_unit(id="al", faction=Faction.ALLIES, morale_value=3)
        axis_inf = _make_unit(id="xi", faction=Faction.AXIS, morale_value=80)
        units = [allies_low, axis_inf]
        result, reason = ev.evaluate(units, tick=0)
        assert result == GameResult.AXIS_VICTORY
        assert "morale" in reason.lower()

    def test_time_limit_allies_win(self):
        ev = self._make_evaluator(
            time_limit_ticks=100,
        )
        allies_inf = _make_unit(id="a1", faction=Faction.ALLIES)
        allies_inf2 = _make_unit(id="a2", faction=Faction.ALLIES)
        axis_inf = _make_unit(id="x1", faction=Faction.AXIS)
        units = [allies_inf, allies_inf2, axis_inf]
        result, reason = ev.evaluate(units, tick=100)
        assert result == GameResult.ALLIES_VICTORY
        assert "time" in reason.lower()

    def test_time_limit_axis_win(self):
        ev = self._make_evaluator(
            time_limit_ticks=100,
        )
        allies_inf = _make_unit(id="a1", faction=Faction.ALLIES)
        axis_inf1 = _make_unit(id="x1", faction=Faction.AXIS)
        axis_inf2 = _make_unit(id="x2", faction=Faction.AXIS)
        units = [allies_inf, axis_inf1, axis_inf2]
        result, reason = ev.evaluate(units, tick=100)
        assert result == GameResult.AXIS_VICTORY
        assert "time" in reason.lower()

    def test_time_limit_draw(self):
        ev = self._make_evaluator(
            time_limit_ticks=100,
        )
        allies_inf = _make_unit(id="a1", faction=Faction.ALLIES)
        axis_inf = _make_unit(id="x1", faction=Faction.AXIS)
        units = [allies_inf, axis_inf]
        result, reason = ev.evaluate(units, tick=100)
        assert result == GameResult.DRAW

    def test_time_limit_zero_means_no_limit(self):
        ev = self._make_evaluator(
            time_limit_ticks=0,
        )
        allies_inf = _make_unit(id="a1", faction=Faction.ALLIES)
        axis_inf = _make_unit(id="x1", faction=Faction.AXIS)
        units = [allies_inf, axis_inf]
        result, _ = ev.evaluate(units, tick=999999)
        assert result == GameResult.ONGOING

    def test_objective_capture_by_allies(self):
        obj = Objective(id="o1", name="Bridge", position=(5, 5), required_ticks=0)
        ev = self._make_evaluator(
            conditions=[VictoryConditionType.OCCUPY_OBJECTIVE],
            objectives=[obj],
        )
        allies_at_obj = _make_unit(id="a1", faction=Faction.ALLIES, tile_x=5, tile_y=5)
        axis_far = _make_unit(id="x1", faction=Faction.AXIS, tile_x=0, tile_y=0)
        units = [allies_at_obj, axis_far]
        result, reason = ev.evaluate(units, tick=0)
        assert result == GameResult.ALLIES_VICTORY
        assert "Bridge" in reason

    def test_objective_capture_by_axis(self):
        obj = Objective(id="o1", name="Hill", position=(3, 3), required_ticks=0)
        ev = self._make_evaluator(
            conditions=[VictoryConditionType.OCCUPY_OBJECTIVE],
            objectives=[obj],
        )
        axis_at_obj = _make_unit(id="x1", faction=Faction.AXIS, tile_x=3, tile_y=3)
        allies_far = _make_unit(id="a1", faction=Faction.ALLIES, tile_x=0, tile_y=0)
        units = [axis_at_obj, allies_far]
        result, reason = ev.evaluate(units, tick=0)
        assert result == GameResult.AXIS_VICTORY
        assert "Hill" in reason

    def test_objective_requires_time_accumulation(self):
        obj = Objective(id="o1", name="Town", position=(5, 5), required_ticks=3)
        ev = self._make_evaluator(
            conditions=[VictoryConditionType.OCCUPY_OBJECTIVE],
            objectives=[obj],
        )
        allies_at_obj = _make_unit(id="a1", faction=Faction.ALLIES, tile_x=5, tile_y=5)
        axis_far = _make_unit(id="x1", faction=Faction.AXIS, tile_x=0, tile_y=0)
        units = [allies_at_obj, axis_far]

        result, _ = ev.evaluate(units, tick=0)
        assert result == GameResult.ONGOING
        result, _ = ev.evaluate(units, tick=1)
        assert result == GameResult.ONGOING
        result, reason = ev.evaluate(units, tick=2)
        assert result == GameResult.ALLIES_VICTORY
        assert "Town" in reason

    def test_objective_contested_resets_progress(self):
        obj = Objective(id="o1", name="Crossroad", position=(5, 5), required_ticks=5)
        ev = self._make_evaluator(
            conditions=[VictoryConditionType.OCCUPY_OBJECTIVE],
            objectives=[obj],
        )
        allies_at_obj = _make_unit(id="a1", faction=Faction.ALLIES, tile_x=5, tile_y=5)
        axis_far = _make_unit(id="x1", faction=Faction.AXIS, tile_x=0, tile_y=0)
        units_allies = [allies_at_obj, axis_far]

        for t in range(3):
            result, _ = ev.evaluate(units_allies, tick=t)
            assert result == GameResult.ONGOING

        axis_arrives = _make_unit(id="x2", faction=Faction.AXIS, tile_x=5, tile_y=5)
        units_contested = [allies_at_obj, axis_arrives]
        result, _ = ev.evaluate(units_contested, tick=3)
        assert result == GameResult.ONGOING

        occupancy = ev._objective_occupancy.get("o1")
        assert occupancy is not None
        assert occupancy[1] == 0

    def test_multiple_conditions_first_match_wins(self):
        ev = self._make_evaluator(
            conditions=[
                VictoryConditionType.ELIMINATE_ENEMY_COMMANDER,
                VictoryConditionType.ELIMINATE_ALL_ENEMIES,
            ],
        )
        allies_cmd = _make_unit(id="ac", unit_type=UnitType.COMMANDER, faction=Faction.ALLIES)
        allies_inf = _make_unit(id="ai", faction=Faction.ALLIES)
        axis_inf = _make_unit(id="xi", faction=Faction.AXIS)
        units = [allies_cmd, allies_inf, axis_inf]
        result, reason = ev.evaluate(units, tick=0)
        assert result == GameResult.ALLIES_VICTORY
        assert "commander" in reason.lower()

    def test_reset_clears_objective_occupancy(self):
        obj = Objective(id="o1", name="Base", position=(5, 5), required_ticks=10)
        ev = self._make_evaluator(
            conditions=[VictoryConditionType.OCCUPY_OBJECTIVE],
            objectives=[obj],
        )
        u = _make_unit(id="a1", faction=Faction.ALLIES, tile_x=5, tile_y=5)
        ev.evaluate([u], tick=0)
        assert len(ev._objective_occupancy) > 0
        ev.reset()
        assert len(ev._objective_occupancy) == 0

    def test_objective_radius_includes_adjacent_tiles(self):
        obj = Objective(id="o1", name="Zone", position=(5, 5), radius=2, required_ticks=0)
        ev = self._make_evaluator(
            conditions=[VictoryConditionType.OCCUPY_OBJECTIVE],
            objectives=[obj],
        )
        allies_near = _make_unit(id="a1", faction=Faction.ALLIES, tile_x=6, tile_y=6)
        axis_far = _make_unit(id="x1", faction=Faction.AXIS, tile_x=0, tile_y=0)
        units = [allies_near, axis_far]
        result, _ = ev.evaluate(units, tick=0)
        assert result == GameResult.ALLIES_VICTORY

    def test_objective_outside_radius_not_counted(self):
        obj = Objective(id="o1", name="Zone", position=(5, 5), radius=1, required_ticks=0)
        ev = self._make_evaluator(
            conditions=[VictoryConditionType.OCCUPY_OBJECTIVE],
            objectives=[obj],
        )
        allies_far = _make_unit(id="a1", faction=Faction.ALLIES, tile_x=7, tile_y=7)
        axis_far = _make_unit(id="x1", faction=Faction.AXIS, tile_x=0, tile_y=0)
        units = [allies_far, axis_far]
        result, _ = ev.evaluate(units, tick=0)
        assert result == GameResult.ONGOING

    def test_morale_collapse_no_alive_units_is_ongoing(self):
        ev = self._make_evaluator(
            conditions=[VictoryConditionType.MORALE_COLLAPSE],
            morale_threshold=10,
        )
        allies_dead = _make_unit(id="ad", faction=Faction.ALLIES, hp=0)
        axis_dead = _make_unit(id="xd", faction=Faction.AXIS, hp=0)
        units = [allies_dead, axis_dead]
        result, _ = ev.evaluate(units, tick=0)
        assert result == GameResult.ONGOING

    def test_stats_parameter_optional(self):
        ev = self._make_evaluator()
        u1 = _make_unit(id="a1", faction=Faction.ALLIES)
        u2 = _make_unit(id="x1", faction=Faction.AXIS)
        result, _ = ev.evaluate([u1, u2], tick=0, stats=None)
        assert result == GameResult.ONGOING
