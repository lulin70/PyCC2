import pytest

from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.combat_engagement import (
    CombatEngagement,
    EngagementDecision,
    EngagementRule,
)
from pycc2.domain.ai.difficulty_system import DifficultyLevel, DifficultySystem
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent, MoraleState
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord


def _make_unit(
    unit_id: str = "u1",
    utype: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    max_hp: int = 100,
    morale_val: int = 80,
    ammo: int = 30,
    max_ammo: int = 30,
    reload_ticks: int = 0,
    morale_state: MoraleState = MoraleState.NORMAL,
    pos: TileCoord | None = None,
) -> Unit:
    wc = WeaponComponent(
        primary_weapon_id="rifle",
        ammo_remaining=ammo,
        max_ammo=max_ammo,
        reload_ticks_left=reload_ticks,
    )
    if morale_state != MoraleState.NORMAL:
        mc = MoraleComponent(value=morale_val)
        mc.state = morale_state
        if morale_state == MoraleState.SUPPRESSED:
            mc.suppression = 10
        elif morale_state in (MoraleState.PANICED, MoraleState.ROUTING):
            mc.value = morale_val
    else:
        mc = MoraleComponent(value=morale_val)
    return Unit(
        id=unit_id,
        name=f"Unit_{unit_id}",
        faction=Faction.ALLIES,
        unit_type=utype,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=mc,
        weapon=wc,
        position=PositionComponent(tile_coord=pos or TileCoord(0, 0)),
        vision=None,
    )


@pytest.fixture
def engagement() -> CombatEngagement:
    return CombatEngagement()


class TestEvaluateEngagement_Distance:
    def test_too_close(self, engagement: CombatEngagement):
        unit = _make_unit(pos=TileCoord(5, 5))
        target = _make_unit(unit_id="e1", pos=TileCoord(5, 4))
        result = engagement.evaluate_engagement(unit, target, distance=0.5)
        assert result.decision == EngagementDecision.CLOSE_DISTANCE

    def test_too_far(self, engagement: CombatEngagement):
        unit = _make_unit(pos=TileCoord(0, 0))
        target = _make_unit(unit_id="e1", pos=TileCoord(20, 20))
        result = engagement.evaluate_engagement(unit, target, distance=15.0)
        assert result.decision == EngagementDecision.CLOSE_DISTANCE


class TestEvaluateEngagement_Ammo:
    def test_low_ammo_reloads_when_immediate(self):
        rule = EngagementRule(reload_preference="immediate")
        ce = CombatEngagement(rule=rule)
        unit = _make_unit(ammo=2, max_ammo=30)
        target = _make_unit(unit_id="e1", pos=TileCoord(10, 10))
        result = ce.evaluate_engagement(unit, target, distance=6.0)
        assert result.decision == EngagementDecision.RELOAD

    def test_low_ammo_holds_when_safe(self, engagement: CombatEngagement):
        unit = _make_unit(ammo=3, max_ammo=30)
        target = _make_unit(unit_id="e1", pos=TileCoord(8, 8))
        result = engagement.evaluate_engagement(unit, target, distance=6.0)
        assert result.decision == EngagementDecision.HOLD_POSITION


class TestEvaluateEngagement_WeaponState:
    def test_reloading_holds(self, engagement: CombatEngagement):
        unit = _make_unit(reload_ticks=5)
        target = _make_unit(unit_id="e1", pos=TileCoord(7, 7))
        result = engagement.evaluate_engagement(unit, target, distance=5.0)
        assert result.decision == EngagementDecision.HOLD_POSITION

    def test_jammed_holds(self, engagement: CombatEngagement):
        unit = _make_unit(ammo=0)
        target = _make_unit(unit_id="e1", pos=TileCoord(7, 7))
        result = engagement.evaluate_engagement(unit, target, distance=5.0)
        assert result.decision == EngagementDecision.HOLD_POSITION


class TestEvaluateEngagement_CeaseFire:
    def test_low_hp_target_causes_hold(self, engagement: CombatEngagement):
        unit = _make_unit()
        target = _make_unit(unit_id="e1", hp=2, max_hp=100)
        result = engagement.evaluate_engagement(unit, target, distance=6.0)
        assert result.decision == EngagementDecision.HOLD_POSITION
        assert "cease fire" in result.reason.lower()


class TestEvaluateEngagement_Morale:
    def test_suppressed_takes_cover(self, engagement: CombatEngagement):
        unit = _make_unit(morale_state=MoraleState.SUPPRESSED)
        target = _make_unit(unit_id="e1", pos=TileCoord(6, 6))
        result = engagement.evaluate_engagement(unit, target, distance=5.0)
        assert result.decision == EngagementDecision.TAKE_COVER

    def test_paniced_retreats(self, engagement: CombatEngagement):
        unit = _make_unit(morale_val=15, morale_state=MoraleState.PANICED)
        target = _make_unit(unit_id="e1", pos=TileCoord(6, 6))
        result = engagement.evaluate_engagement(unit, target, distance=5.0)
        assert result.decision == EngagementDecision.RETREAT


class TestEvaluateEngagement_NoCover:
    def test_exposed_at_close_range_seeks_cover(self, engagement: CombatEngagement):
        bb = Blackboard()
        bb.set("has_cover", False)
        unit = _make_unit()
        target = _make_unit(unit_id="e1", pos=TileCoord(4, 4))
        result = engagement.evaluate_engagement(unit, target, distance=2.5, blackboard=bb)
        assert result.decision == EngagementDecision.TAKE_COVER


class TestEvaluateEngagement_OptimalRange:
    def test_optimal_range_engages(self, engagement: CombatEngagement):
        unit = _make_unit()
        target = _make_unit(unit_id="e1", pos=TileCoord(8, 8))
        result = engagement.evaluate_engagement(unit, target, distance=6.0)
        assert result.decision == EngagementDecision.ENGAGE


class TestCustomRule:
    def test_custom_rule_overrides_defaults(self):
        rule = EngagementRule(
            min_engagement_distance=3.0,
            max_engagement_distance=20.0,
            cease_fire_threshold=0.1,
        )
        ce = CombatEngagement(rule=rule)
        assert ce.rule.min_engagement_distance == 3.0
        assert ce.rule.max_engagement_distance == 20.0
        unit = _make_unit()
        target = _make_unit(unit_id="e1", hp=25, max_hp=100)
        result = ce.evaluate_engagement(unit, target, distance=6.0)
        assert result.decision == EngagementDecision.ENGAGE


class TestSelectBestTarget:
    def test_selects_nearest(self, engagement: CombatEngagement):
        unit = _make_unit(pos=TileCoord(5, 5))
        near = _make_unit(unit_id="e_near", pos=TileCoord(6, 5))
        far = _make_unit(unit_id="e_far", pos=TileCoord(15, 15))
        best = engagement.select_best_target(unit, [far, near])
        assert best is not None
        assert best.id == "e_near"

    def test_prefers_low_hp_when_same_distance(self, engagement: CombatEngagement):
        unit = _make_unit(pos=TileCoord(5, 5))
        healthy = _make_unit(unit_id="e_healthy", pos=TileCoord(7, 5), hp=100, max_hp=100)
        wounded = _make_unit(unit_id="e_wounded", pos=TileCoord(7, 6), hp=20, max_hp=100)
        best = engagement.select_best_target(unit, [healthy, wounded])
        assert best is not None
        assert best.id == "e_wounded"

    def test_prioritizes_threat(self, engagement: CombatEngagement):
        unit = _make_unit(pos=TileCoord(5, 5))
        infantry = _make_unit(
            unit_id="e_inf",
            utype=UnitType.INFANTRY_SQUAD,
            pos=TileCoord(7, 5),
        )
        mg = _make_unit(
            unit_id="e_mg",
            utype=UnitType.MACHINE_GUN_SQUAD,
            pos=TileCoord(7, 6),
        )
        best = engagement.select_best_target(unit, [infantry, mg])
        assert best is not None
        assert best.id == "e_mg"

    def test_protects_allies_under_attack(self, engagement: CombatEngagement):
        bb = Blackboard()
        bb.set("allies_under_attack", ["e_attacker"])
        unit = _make_unit(pos=TileCoord(5, 5))
        normal_enemy = _make_unit(unit_id="e_normal", pos=TileCoord(7, 5))
        attacker = _make_unit(unit_id="e_attacker", pos=TileCoord(7, 6))
        best = engagement.select_best_target(unit, [normal_enemy, attacker], blackboard=bb)
        assert best is not None
        assert best.id == "e_attacker"

    def test_returns_none_for_empty_list(self, engagement: CombatEngagement):
        unit = _make_unit()
        assert engagement.select_best_target(unit, []) is None


class TestDetermineFireMode:
    def test_mg_uses_suppress(self, engagement: CombatEngagement):
        unit = _make_unit(utype=UnitType.MACHINE_GUN_SQUAD)
        target = _make_unit(unit_id="e1")
        assert engagement.determine_fire_mode(unit, target, 6.0) == "suppress"

    def test_low_ammo_single(self, engagement: CombatEngagement):
        unit = _make_unit(ammo=3, max_ammo=30)
        target = _make_unit(unit_id="e1")
        assert engagement.determine_fire_mode(unit, target, 6.0) == "single"

    def test_far_distance_single(self, engagement: CombatEngagement):
        unit = _make_unit()
        target = _make_unit(unit_id="e1")
        mode = engagement.determine_fire_mode(unit, target, 12.0)
        assert mode == "single"

    def test_close_distance_burst(self, engagement: CombatEngagement):
        unit = _make_unit()
        target = _make_unit(unit_id="e1")
        mode = engagement.determine_fire_mode(unit, target, 2.0)
        assert mode == "burst"

    def test_hard_difficulty_burst_at_far(self):
        ce = CombatEngagement()
        unit = _make_unit()
        target = _make_unit(unit_id="e1")
        dc = DifficultySystem(DifficultyLevel.HARD).config
        mode = ce.determine_fire_mode(unit, target, 10.0, difficulty_config=dc)
        assert mode == "burst"


class TestShouldReloadNow:
    def test_full_ammo_no_reload(self, engagement: CombatEngagement):
        unit = _make_unit(ammo=30, max_ammo=30)
        assert engagement.should_reload_now(unit, in_combat=False, has_cover=False) is False

    def test_out_of_ammo_reloads(self, engagement: CombatEngagement):
        unit = _make_unit(ammo=0, max_ammo=30)
        assert engagement.should_reload_now(unit, in_combat=True, has_cover=False) is True

    def test_reloads_with_cover_and_low_ammo(self, engagement: CombatEngagement):
        unit = _make_unit(ammo=4, max_ammo=30)
        assert engagement.should_reload_now(unit, in_combat=True, has_cover=True) is True

    def test_reloads_out_of_combat(self, engagement: CombatEngagement):
        unit = _make_unit(ammo=4, max_ammo=30)
        assert engagement.should_reload_now(unit, in_combat=False, has_cover=False) is True

    def test_immediate_preference_critical_ammo(self):
        rule = EngagementRule(reload_preference="immediate")
        ce = CombatEngagement(rule=rule)
        unit = _make_unit(ammo=1, max_ammo=30)
        assert ce.should_reload_now(unit, in_combat=True, has_cover=False) is True


class TestDifficultyIntegration:
    def test_conservative_difficulty_holds_at_long_range(self):
        ce = CombatEngagement()
        unit = _make_unit()
        target = _make_unit(unit_id="e1", pos=TileCoord(12, 5))
        dc = DifficultySystem(DifficultyLevel.EASY).config
        holds = sum(
            1
            for _ in range(50)
            if ce.evaluate_engagement(unit, target, distance=7.0, difficulty_config=dc).decision
            == EngagementDecision.HOLD_POSITION
        )
        assert holds > 10
