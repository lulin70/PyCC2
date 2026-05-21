from pycc2.domain.ai.behavior_tree import Action, Condition, NodeStatus, Selector, Sequence
from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.tactic_intent import TacticType
from pycc2.domain.ai.unit_bt_factory import UnitBTFactory


class TestInfantryBT:
    def test_create_infantry_bt_returns_selector(self):
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        assert isinstance(tree, Selector)

    def test_infantry_bt_has_four_branches(self):
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        assert len(tree.children) == 4

    def test_infantry_first_branch_is_retreat_sequence(self):
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        first_branch = tree.children[0]
        assert isinstance(first_branch, Sequence)
        assert isinstance(first_branch.children[0], Condition)
        assert isinstance(first_branch.children[1], Action)

    def test_infantry_low_health_triggers_retreat(self):
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        bb = Blackboard()
        bb.set("health_ratio", 0.2)
        status = tree.tick(bb)
        assert status == NodeStatus.SUCCESS
        intent = bb.get_current_intent()
        assert intent is not None
        assert intent.tactic_type == TacticType.RETREAT

    def test_infantry_visible_enemy_triggers_combat(self):
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        bb = Blackboard()
        bb.set("health_ratio", 0.8)
        bb.set("visible_enemies", ["enemy_1"])
        bb.set("nearest_enemy_distance", 3.0)
        bb.set("nearest_enemy_position", None)
        bb.set("nearest_enemy_id", "enemy_1")
        status = tree.tick(bb)
        assert status == NodeStatus.SUCCESS
        intent = bb.get_current_intent()
        assert intent is not None
        assert intent.tactic_type in (TacticType.ATTACK, TacticType.MOVE_TO)

    def test_infantry_no_enemies_patrols(self):
        tree = UnitBTFactory.create_infantry_bt(unit_id="inf_1")
        bb = Blackboard()
        bb.set("health_ratio", 0.9)
        bb.set("visible_enemies", [])
        status = tree.tick(bb)
        assert status == NodeStatus.SUCCESS
        intent = bb.get_current_intent()
        assert intent is not None
        assert intent.tactic_type == TacticType.PATROL


class TestMGSquadBT:
    def test_create_mg_squad_bt_returns_selector(self):
        tree = UnitBTFactory.create_mg_squad_bt(unit_id="mg_1")
        assert isinstance(tree, Selector)

    def test_mg_bt_prefers_suppress_fire(self):
        tree = UnitBTFactory.create_mg_squad_bt(unit_id="mg_1")
        bb = Blackboard()
        bb.set("health_ratio", 0.8)
        bb.set("visible_enemies", ["enemy_1"])
        bb.set("nearest_enemy_distance", 6.0)
        bb.set("nearest_enemy_id", "enemy_1")
        status = tree.tick(bb)
        assert status == NodeStatus.SUCCESS
        intent = bb.get_current_intent()
        assert intent is not None
        assert intent.tactic_type == TacticType.SUPPRESS_FIRE

    def test_mg_low_health_retreats(self):
        tree = UnitBTFactory.create_mg_squad_bt(unit_id="mg_1")
        bb = Blackboard()
        bb.set("health_ratio", 0.2)
        status = tree.tick(bb)
        assert status == NodeStatus.SUCCESS
        intent = bb.get_current_intent()
        assert intent.tactic_type == TacticType.RETREAT


class TestCommanderBT:
    def test_create_commander_bt_returns_selector(self):
        tree = UnitBTFactory.create_commander_bt(unit_id="cmd_1")
        assert isinstance(tree, Selector)

    def test_commander_prefers_hold_position_in_combat(self):
        tree = UnitBTFactory.create_commander_bt(unit_id="cmd_1")
        bb = Blackboard()
        bb.set("health_ratio", 0.8)
        bb.set("visible_enemies", ["enemy_1"])
        bb.set("allies_nearby", 5)
        status = tree.tick(bb)
        assert status == NodeStatus.SUCCESS
        intent = bb.get_current_intent()
        assert intent is not None
        assert intent.tactic_type == TacticType.HOLD_POSITION

    def test_commander_critical_health_regroups(self):
        tree = UnitBTFactory.create_commander_bt(unit_id="cmd_1")
        bb = Blackboard()
        bb.set("health_ratio", 0.15)
        status = tree.tick(bb)
        assert status == NodeStatus.SUCCESS
        intent = bb.get_current_intent()
        assert intent.tactic_type == TacticType.REGROUP

    def test_commander_supports_allies(self):
        tree = UnitBTFactory.create_commander_bt(unit_id="cmd_1")
        bb = Blackboard()
        bb.set("health_ratio", 0.7)
        bb.set("visible_enemies", ["enemy_1"])
        bb.set("allies_nearby", 1)
        status = tree.tick(bb)
        assert status == NodeStatus.SUCCESS
        intent = bb.get_current_intent()
        assert intent is not None
        assert intent.tactic_type == TacticType.REGROUP
