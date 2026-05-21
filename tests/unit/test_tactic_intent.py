from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.value_objects.tile_coord import TileCoord


class TestTacticIntentCreation:
    def test_create_minimal_intent(self):
        intent = TacticIntent(unit_id="unit_1", tactic_type=TacticType.IDLE)
        assert intent.unit_id == "unit_1"
        assert intent.tactic_type == TacticType.IDLE
        assert intent.priority == 0
        assert intent.target_position is None
        assert intent.target_unit_id is None
        assert intent.path is None

    def test_create_move_to_intent(self):
        pos = TileCoord(5, 10)
        intent = TacticIntent(
            unit_id="unit_2",
            tactic_type=TacticType.MOVE_TO,
            target_position=pos,
            priority=5,
        )
        assert intent.target_position == pos
        assert intent.priority == 5

    def test_create_attack_intent(self):
        intent = TacticIntent(
            unit_id="unit_3",
            tactic_type=TacticType.ATTACK,
            target_unit_id="enemy_1",
            priority=8,
        )
        assert intent.target_unit_id == "enemy_1"
        assert intent.has_target is True


class TestTacticTypeEnum:
    def test_all_tactic_types_exist(self):
        expected_types = [
            TacticType.IDLE,
            TacticType.PATROL,
            TacticType.MOVE_TO,
            TacticType.ATTACK,
            TacticType.RETREAT,
            TacticType.SUPPRESS_FIRE,
            TacticType.DEFEND,
            TacticType.HOLD_POSITION,
            TacticType.TAKE_COVER,
            TacticType.REGROUP,
            TacticType.FLANKING,
            TacticType.COORDINATED_ADVANCE,
            TacticType.CAPTURE_VL,
            TacticType.DEFEND_VL,
            TacticType.DEMOLISH_BRIDGE,
            TacticType.DEPLOY_SMOKE,
        ]
        assert len(TacticType) >= len(expected_types)
        for t in expected_types:
            assert t in TacticType


class TestTacticIntentProperties:
    def test_has_target_with_position(self):
        intent = TacticIntent(
            unit_id="u", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(1, 1)
        )
        assert intent.has_target is True

    def test_has_target_with_unit_id(self):
        intent = TacticIntent(unit_id="u", tactic_type=TacticType.ATTACK, target_unit_id="e1")
        assert intent.has_target is True

    def test_has_no_target(self):
        intent = TacticIntent(unit_id="u", tactic_type=TacticType.IDLE)
        assert intent.has_target is False
