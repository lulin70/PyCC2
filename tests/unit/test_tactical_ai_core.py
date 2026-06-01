"""
Tests for tactical_ai module — CC2-Authentic Combat Behaviors.

Covers:
  - FlankingAI evaluate/execute with various scenarios
  - SuppressionAI evaluate/execute with various scenarios
  - InfantryTankCoordAI evaluate/execute with various scenarios
  - VictoryPointAI evaluate/execute with various scenarios
  - TacticalOrchestrator registration and tick
  - _threat_score helper
  - _infer_facing helper
  - _flank_position helper
  - FlankSide enum
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from pycc2.domain.ai.tactical_ai import (
    FlankSide,
    FlankingAI,
    InfantryTankCoordAI,
    SuppressionAI,
    TacticalAIBase,
    TacticalContext,
    TacticalOrchestrator,
    VictoryPointAI,
    _flank_position,
    _infer_facing,
    _threat_score,
)
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.blackboard import Blackboard
from pycc2.domain.ai.difficulty_system import DifficultyConfig, DifficultyLevel
from pycc2.domain.entities.unit import Faction, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord


# ---------------------------------------------------------------------------
# Helpers — lightweight mock objects
# ---------------------------------------------------------------------------

def _make_mock_unit(
    uid: str = "u1",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    x: int = 10,
    y: int = 10,
    alive: bool = True,
    can_act: bool = True,
    hp_ratio: float = 1.0,
    morale_value: int = 80,
    is_moving: bool = False,
) -> MagicMock:
    """Create a mock Unit with sensible defaults."""
    unit = MagicMock(spec=[])
    unit.id = uid
    unit.faction = faction
    unit.unit_type = unit_type
    unit.is_alive = alive
    unit.can_act = can_act
    unit._is_moving = is_moving

    # position
    pos = MagicMock()
    pos.tile_coord = TileCoord(x, y)
    unit.position = pos

    # health
    health = MagicMock()
    health.hp_ratio = hp_ratio
    unit.health = health

    # morale
    morale = MagicMock()
    morale.is_combat_effective = morale_value >= 30
    morale.value = morale_value
    unit.morale = morale

    # suppression state (optional)
    unit.suppression_state = None

    return unit


def _make_mock_game_map(
    width: int = 50,
    height: int = 50,
    passable: bool = True,
    has_los: bool = False,
    cover_modifier: float = 0.3,
    terrain_type_str: str = "woods",
) -> MagicMock:
    """Create a mock GameMap."""
    gmap = MagicMock()
    gmap.width = width
    gmap.height = height

    def is_within_bounds(coord: TileCoord) -> bool:
        return 0 <= coord.x < width and 0 <= coord.y < height

    gmap.is_within_bounds = MagicMock(side_effect=is_within_bounds)
    gmap.is_passable = MagicMock(return_value=passable)
    gmap.has_line_of_sight = MagicMock(return_value=has_los)

    terrain = MagicMock()
    terrain.cover_modifier = cover_modifier
    terrain.terrain_type = terrain_type_str
    gmap.get_terrain = MagicMock(return_value=terrain)

    return gmap


def _make_context(
    friendlies: list | None = None,
    enemies: list | None = None,
    game_map: MagicMock | None = None,
    tick: int = 1,
    blackboards: dict | None = None,
    difficulty: DifficultyConfig | None = None,
    vl_positions: list | None = None,
) -> TacticalContext:
    """Create a TacticalContext with defaults."""
    return TacticalContext(
        friendly_units=friendlies or [],
        enemy_units=enemies or [],
        game_map=game_map or _make_mock_game_map(),
        current_tick=tick,
        blackboards=blackboards or {},
        difficulty_config=difficulty,
        vl_positions=vl_positions or [],
    )


# ---------------------------------------------------------------------------
# FlankSide enum
# ---------------------------------------------------------------------------

class TestFlankSide:

    def test_has_left(self):
        assert FlankSide.LEFT == FlankSide.LEFT, "FlankSide.LEFT should be defined and equal to itself"

    def test_has_right(self):
        assert FlankSide.RIGHT == FlankSide.RIGHT, "FlankSide.RIGHT should be defined and equal to itself"

    def test_two_values(self):
        assert len(FlankSide) == 2


# ---------------------------------------------------------------------------
# _threat_score helper
# ---------------------------------------------------------------------------

class TestThreatScore:

    def test_mg_squad_high_weight(self):
        unit = _make_mock_unit(unit_type=UnitType.MACHINE_GUN_SQUAD, x=10, y=10)
        ref = TileCoord(10, 10)
        score = _threat_score(unit, ref)
        assert score >= 1.0, f"MG squad at same position should have high threat score (>= 1.0), got {score}"

    def test_tank_highest_weight(self):
        tank = _make_mock_unit(unit_type=UnitType.TANK, x=10, y=10)
        inf = _make_mock_unit(unit_type=UnitType.INFANTRY_SQUAD, x=10, y=10)
        ref = TileCoord(10, 10)
        assert _threat_score(tank, ref) > _threat_score(inf, ref)

    def test_medic_lowest_weight(self):
        medic = _make_mock_unit(unit_type=UnitType.MEDIC_TEAM, x=10, y=10)
        ref = TileCoord(10, 10)
        score = _threat_score(medic, ref)
        assert 0 < score < 1.0, (
            f"Medic should have low but positive threat score (0 < score < 1.0), got {score}"
        )

    def test_distance_reduces_score(self):
        unit_near = _make_mock_unit(unit_type=UnitType.INFANTRY_SQUAD, x=11, y=10)
        unit_far = _make_mock_unit(unit_type=UnitType.INFANTRY_SQUAD, x=20, y=10)
        ref = TileCoord(10, 10)
        assert _threat_score(unit_near, ref) > _threat_score(unit_far, ref)

    def test_low_hp_reduces_score(self):
        unit_full = _make_mock_unit(unit_type=UnitType.INFANTRY_SQUAD, hp_ratio=1.0)
        unit_hurt = _make_mock_unit(unit_type=UnitType.INFANTRY_SQUAD, hp_ratio=0.2)
        ref = TileCoord(10, 10)
        assert _threat_score(unit_full, ref) > _threat_score(unit_hurt, ref)

    def test_same_position_dist_1(self):
        """When unit is at reference position, chebyshev distance is 0, clamped to 1."""
        unit = _make_mock_unit(unit_type=UnitType.INFANTRY_SQUAD, x=5, y=5)
        ref = TileCoord(5, 5)
        score = _threat_score(unit, ref)
        assert score >= 1.0, (
            f"Infantry squad at same position should have threat score >= 1.0 "
            f"(distance clamped to 1), got {score}"
        )


# ---------------------------------------------------------------------------
# _infer_facing helper
# ---------------------------------------------------------------------------

class TestInferFacing:

    def test_no_allies_returns_own_position(self):
        unit = _make_mock_unit(x=5, y=5)
        result = _infer_facing(unit, [])
        assert result == TileCoord(5, 5)

    def test_single_ally_centroid(self):
        unit = _make_mock_unit(x=5, y=5)
        ally = _make_mock_unit(x=10, y=10)
        result = _infer_facing(unit, [ally])
        assert result == TileCoord(10, 10)

    def test_multiple_allies_centroid(self):
        unit = _make_mock_unit(x=5, y=5)
        allies = [_make_mock_unit(x=10, y=10), _make_mock_unit(x=20, y=20)]
        result = _infer_facing(unit, allies)
        assert result == TileCoord(15, 15)


# ---------------------------------------------------------------------------
# _flank_position helper
# ---------------------------------------------------------------------------

class TestFlankPosition:

    def test_left_flank_offset(self):
        enemy = TileCoord(10, 10)
        facing = TileCoord(15, 10)  # Facing right
        left = _flank_position(enemy, facing, FlankSide.LEFT, offset=4)
        # Perpendicular to right is up (negative y) for left flank
        assert left != enemy

    def test_right_flank_offset(self):
        enemy = TileCoord(10, 10)
        facing = TileCoord(15, 10)
        right = _flank_position(enemy, facing, FlankSide.RIGHT, offset=4)
        assert right != enemy

    def test_left_and_right_are_different(self):
        enemy = TileCoord(10, 10)
        facing = TileCoord(15, 10)
        left = _flank_position(enemy, facing, FlankSide.LEFT, offset=4)
        right = _flank_position(enemy, facing, FlankSide.RIGHT, offset=4)
        assert left != right

    def test_zero_length_facing(self):
        """When facing_target == enemy_pos, length is 0, clamped to 1.0."""
        enemy = TileCoord(10, 10)
        facing = TileCoord(10, 10)
        result = _flank_position(enemy, facing, FlankSide.LEFT, offset=4)
        # Should not raise, and returns a TileCoord
        assert isinstance(result, TileCoord)


# ---------------------------------------------------------------------------
# FlankingAI
# ---------------------------------------------------------------------------

class TestFlankingAI:

    def test_evaluate_no_enemies(self):
        ai = FlankingAI()
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid=f"f{i}") for i in range(3)],
            enemies=[],
        )
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_no_mobile_units(self):
        ai = FlankingAI()
        # Tanks are not infantry, so not mobile for flanking
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="t1", unit_type=UnitType.TANK)],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
        )
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_single_mobile_unit(self):
        ai = FlankingAI()
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="f1", unit_type=UnitType.INFANTRY_SQUAD)],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
        )
        assert ai.evaluate(ctx) == 0.0  # Need MIN_FLANKING_UNITS=2

    def test_evaluate_sufficient_units(self):
        ai = FlankingAI()
        ctx = _make_context(
            friendlies=[
                _make_mock_unit(uid=f"f{i}", unit_type=UnitType.INFANTRY_SQUAD)
                for i in range(4)
            ],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
        )
        score = ai.evaluate(ctx)
        assert 0.0 < score <= 1.0

    def test_evaluate_difficulty_disables_flanking(self):
        ai = FlankingAI()
        diff = DifficultyConfig(level=DifficultyLevel.EASY, use_flanking=False)
        ctx = _make_context(
            friendlies=[
                _make_mock_unit(uid=f"f{i}", unit_type=UnitType.INFANTRY_SQUAD)
                for i in range(4)
            ],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
            difficulty=diff,
        )
        assert ai.evaluate(ctx) == 0.0

    def test_execute_returns_intents(self):
        ai = FlankingAI()
        gmap = _make_mock_game_map(passable=True, cover_modifier=0.3)
        ctx = _make_context(
            friendlies=[
                _make_mock_unit(uid=f"f{i}", unit_type=UnitType.INFANTRY_SQUAD, x=5 + i, y=5)
                for i in range(4)
            ],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS, x=20, y=10)],
            game_map=gmap,
        )
        intents = ai.execute(ctx)
        assert len(intents) >= 2, (
            f"FlankingAI with 4 mobile units and 1 enemy should produce at least 2 intents "
            f"(pinning + flanking), got {len(intents)}"
        )
        assert all(isinstance(i, TacticIntent) for i in intents), "All intents should be TacticIntent instances"

    def test_execute_no_enemies_returns_empty(self):
        ai = FlankingAI()
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="f1", unit_type=UnitType.INFANTRY_SQUAD)],
            enemies=[],
        )
        assert ai.execute(ctx) == []

    def test_execute_pinning_and_flanking(self):
        ai = FlankingAI()
        gmap = _make_mock_game_map(passable=True, cover_modifier=0.3)
        ctx = _make_context(
            friendlies=[
                _make_mock_unit(uid=f"f{i}", unit_type=UnitType.INFANTRY_SQUAD, x=5 + i, y=5)
                for i in range(6)
            ],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS, x=20, y=10)],
            game_map=gmap,
        )
        intents = ai.execute(ctx)
        suppress_intents = [i for i in intents if i.tactic_type == TacticType.SUPPRESS_FIRE]
        flank_intents = [i for i in intents if i.tactic_type == TacticType.FLANKING]
        assert len(suppress_intents) >= 1, (
            f"With 6 units, FlankingAI should produce at least 1 suppress intent for pinning force, "
            f"got {len(suppress_intents)}"
        )
        # Flank intents may or may not appear depending on map validation


# ---------------------------------------------------------------------------
# SuppressionAI
# ---------------------------------------------------------------------------

class TestSuppressionAI:

    def test_evaluate_no_mg_units(self):
        ai = SuppressionAI()
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="f1", unit_type=UnitType.INFANTRY_SQUAD)],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
        )
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_no_enemies(self):
        ai = SuppressionAI()
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="mg1", unit_type=UnitType.MACHINE_GUN_SQUAD)],
            enemies=[],
        )
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_mg_and_enemies(self):
        ai = SuppressionAI()
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="mg1", unit_type=UnitType.MACHINE_GUN_SQUAD)],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
        )
        score = ai.evaluate(ctx)
        assert 0.0 < score <= 1.0

    def test_evaluate_high_threat_enemies(self):
        ai = SuppressionAI()
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="mg1", unit_type=UnitType.MACHINE_GUN_SQUAD)],
            enemies=[
                _make_mock_unit(uid="e_mg", faction=Faction.AXIS, unit_type=UnitType.MACHINE_GUN_SQUAD),
                _make_mock_unit(uid="e_at", faction=Faction.AXIS, unit_type=UnitType.AT_GUN_TEAM),
            ],
        )
        score = ai.evaluate(ctx)
        assert score > 0.0

    def test_evaluate_difficulty_disables(self):
        ai = SuppressionAI()
        diff = DifficultyConfig(level=DifficultyLevel.EASY, use_suppression_tactics=False)
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="mg1", unit_type=UnitType.MACHINE_GUN_SQUAD)],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
            difficulty=diff,
        )
        assert ai.evaluate(ctx) == 0.0

    def test_execute_returns_suppress_intents(self):
        ai = SuppressionAI()
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="mg1", unit_type=UnitType.MACHINE_GUN_SQUAD, x=5, y=5)],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS, x=15, y=5)],
        )
        intents = ai.execute(ctx)
        assert len(intents) >= 1, (
            f"SuppressionAI with MG unit and enemy should produce at least 1 suppress intent, "
            f"got {len(intents)}"
        )
        assert all(i.tactic_type == TacticType.SUPPRESS_FIRE for i in intents), (
            "All SuppressionAI intents should be of type SUPPRESS_FIRE"
        )

    def test_execute_no_mg_returns_empty(self):
        ai = SuppressionAI()
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="f1", unit_type=UnitType.INFANTRY_SQUAD)],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
        )
        assert ai.execute(ctx) == []

    def test_execute_infantry_advancing_gets_priority_9(self):
        ai = SuppressionAI()
        mg = _make_mock_unit(uid="mg1", unit_type=UnitType.MACHINE_GUN_SQUAD, x=5, y=5)
        inf = _make_mock_unit(uid="inf1", unit_type=UnitType.INFANTRY_SQUAD, x=12, y=5)
        enemy = _make_mock_unit(uid="e1", faction=Faction.AXIS, x=15, y=5)
        ctx = _make_context(friendlies=[mg, inf], enemies=[enemy])
        intents = ai.execute(ctx)
        # Infantry within 8 tiles of enemy → advancing, so priority 9
        high_priority = [i for i in intents if i.priority == 9]
        assert len(high_priority) > 0

    def test_should_continue_suppression_panicked_target(self):
        ai = SuppressionAI()
        mg = _make_mock_unit(uid="mg1", unit_type=UnitType.MACHINE_GUN_SQUAD)
        target = _make_mock_unit(uid="e1", faction=Faction.AXIS, morale_value=10)
        ctx = _make_context(friendlies=[mg], enemies=[target])
        result = SuppressionAI._should_continue_suppression(mg, target, ctx)
        assert result is False  # Target panicked, switch

    def test_should_continue_suppression_pinned_target(self):
        ai = SuppressionAI()
        mg = _make_mock_unit(uid="mg1", unit_type=UnitType.MACHINE_GUN_SQUAD)
        target = _make_mock_unit(uid="e1", faction=Faction.AXIS, morale_value=50)
        target.suppression_state = MagicMock()
        target.suppression_state.is_pinned = True
        ctx = _make_context(friendlies=[mg], enemies=[target])
        result = SuppressionAI._should_continue_suppression(mg, target, ctx)
        assert result is False  # Target pinned, switch


# ---------------------------------------------------------------------------
# InfantryTankCoordAI
# ---------------------------------------------------------------------------

class TestInfantryTankCoordAI:

    def test_evaluate_no_tanks(self):
        ai = InfantryTankCoordAI()
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="f1", unit_type=UnitType.INFANTRY_SQUAD)],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
        )
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_no_infantry(self):
        ai = InfantryTankCoordAI()
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="t1", unit_type=UnitType.TANK)],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
        )
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_both_tanks_and_infantry(self):
        ai = InfantryTankCoordAI()
        ctx = _make_context(
            friendlies=[
                _make_mock_unit(uid="t1", unit_type=UnitType.TANK),
                _make_mock_unit(uid="f1", unit_type=UnitType.INFANTRY_SQUAD),
            ],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
        )
        score = ai.evaluate(ctx)
        assert 0.0 < score <= 1.0

    def test_evaluate_difficulty_disables_coordination(self):
        ai = InfantryTankCoordAI()
        diff = DifficultyConfig(level=DifficultyLevel.EASY, coordination_enabled=False)
        ctx = _make_context(
            friendlies=[
                _make_mock_unit(uid="t1", unit_type=UnitType.TANK),
                _make_mock_unit(uid="f1", unit_type=UnitType.INFANTRY_SQUAD),
            ],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
            difficulty=diff,
        )
        assert ai.evaluate(ctx) == 0.0

    def test_execute_tank_with_infantry_support_advances(self):
        ai = InfantryTankCoordAI()
        gmap = _make_mock_game_map(passable=True, terrain_type_str="road")
        tank = _make_mock_unit(uid="t1", unit_type=UnitType.TANK, x=5, y=5)
        inf = _make_mock_unit(uid="f1", unit_type=UnitType.INFANTRY_SQUAD, x=6, y=5)
        enemy = _make_mock_unit(uid="e1", faction=Faction.AXIS, x=20, y=5)
        ctx = _make_context(friendlies=[tank, inf], enemies=[enemy], game_map=gmap)
        intents = ai.execute(ctx)
        tank_intents = [i for i in intents if i.unit_id == "t1"]
        assert len(tank_intents) > 0
        assert tank_intents[0].tactic_type == TacticType.COORDINATED_ADVANCE

    def test_execute_tank_without_infantry_holds(self):
        ai = InfantryTankCoordAI()
        gmap = _make_mock_game_map(passable=True)
        tank = _make_mock_unit(uid="t1", unit_type=UnitType.TANK, x=5, y=5)
        inf_far = _make_mock_unit(uid="f1", unit_type=UnitType.INFANTRY_SQUAD, x=30, y=30)
        enemy = _make_mock_unit(uid="e1", faction=Faction.AXIS, x=20, y=5)
        ctx = _make_context(friendlies=[tank, inf_far], enemies=[enemy], game_map=gmap)
        intents = ai.execute(ctx)
        tank_intents = [i for i in intents if i.unit_id == "t1"]
        assert len(tank_intents) > 0
        assert tank_intents[0].tactic_type == TacticType.HOLD_POSITION

    def test_execute_no_enemies_returns_empty(self):
        ai = InfantryTankCoordAI()
        ctx = _make_context(
            friendlies=[
                _make_mock_unit(uid="t1", unit_type=UnitType.TANK),
                _make_mock_unit(uid="f1", unit_type=UnitType.INFANTRY_SQUAD),
            ],
            enemies=[],
        )
        assert ai.execute(ctx) == []

    def test_screening_position_between_tank_and_at(self):
        inf_pos = TileCoord(10, 10)
        at_pos = TileCoord(20, 10)
        tank_pos = TileCoord(5, 10)
        result = InfantryTankCoordAI._screening_position(inf_pos, at_pos, tank_pos)
        assert isinstance(result, TileCoord)
        # Should be between tank and AT, closer to AT
        assert result.x > tank_pos.x


# ---------------------------------------------------------------------------
# VictoryPointAI
# ---------------------------------------------------------------------------

class TestVictoryPointAI:

    def test_evaluate_no_vl_data(self):
        ai = VictoryPointAI()
        ctx = _make_context(vl_positions=[])
        assert ai.evaluate(ctx) == 0.0

    def test_evaluate_uncontrolled_vls(self):
        ai = VictoryPointAI()
        vl = (TileCoord(10, 10), None, 30)
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="f1", faction=Faction.ALLIES)],
            enemies=[],
            vl_positions=[vl],
        )
        score = ai.evaluate(ctx)
        assert score > 0.0

    def test_evaluate_all_vls_held_no_threat(self):
        ai = VictoryPointAI()
        vl = (TileCoord(10, 10), "ALLIES", 30)
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="f1", faction=Faction.ALLIES)],
            enemies=[],
            vl_positions=[vl],
        )
        score = ai.evaluate(ctx)
        # No uncontrolled and no threats, defense_urgency = 0
        assert score >= 0.0

    def test_evaluate_held_vl_under_threat(self):
        ai = VictoryPointAI()
        vl = (TileCoord(10, 10), "ALLIES", 30)
        enemy = _make_mock_unit(uid="e1", faction=Faction.AXIS, x=12, y=10)
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="f1", faction=Faction.ALLIES)],
            enemies=[enemy],
            vl_positions=[vl],
        )
        score = ai.evaluate(ctx)
        assert score > 0.0

    def test_execute_capture_uncontrolled_vl(self):
        ai = VictoryPointAI()
        vl = (TileCoord(20, 20), None, 30)
        friendly = _make_mock_unit(uid="f1", faction=Faction.ALLIES, unit_type=UnitType.INFANTRY_SQUAD, x=5, y=5)
        ctx = _make_context(friendlies=[friendly], enemies=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        assert len(intents) > 0
        assert intents[0].tactic_type == TacticType.CAPTURE_VL

    def test_execute_no_available_units(self):
        ai = VictoryPointAI()
        vl = (TileCoord(10, 10), None, 30)
        # Dead unit
        dead = _make_mock_unit(uid="f1", alive=False)
        ctx = _make_context(friendlies=[dead], enemies=[], vl_positions=[vl])
        assert ai.execute(ctx) == []

    def test_execute_no_vl_data(self):
        ai = VictoryPointAI()
        ctx = _make_context(vl_positions=[])
        assert ai.execute(ctx) == []

    def test_execute_high_value_vl_gets_two_units(self):
        ai = VictoryPointAI()
        vl = (TileCoord(20, 20), None, 40)  # High value
        friendlies = [
            _make_mock_unit(uid=f"f{i}", faction=Faction.ALLIES, unit_type=UnitType.INFANTRY_SQUAD, x=5 + i, y=5)
            for i in range(5)
        ]
        ctx = _make_context(friendlies=friendlies, enemies=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        capture_intents = [i for i in intents if i.tactic_type == TacticType.CAPTURE_VL]
        assert len(capture_intents) == 2  # High value gets 2 units

    def test_execute_low_value_vl_gets_one_unit(self):
        ai = VictoryPointAI()
        vl = (TileCoord(20, 20), None, 10)  # Low value
        friendlies = [
            _make_mock_unit(uid=f"f{i}", faction=Faction.ALLIES, unit_type=UnitType.INFANTRY_SQUAD, x=5 + i, y=5)
            for i in range(5)
        ]
        ctx = _make_context(friendlies=friendlies, enemies=[], vl_positions=[vl])
        intents = ai.execute(ctx)
        capture_intents = [i for i in intents if i.tactic_type == TacticType.CAPTURE_VL]
        assert len(capture_intents) == 1

    def test_find_safer_vl_returns_none_when_no_safe(self):
        vl_pos = TileCoord(10, 10)
        # All held VLs are under heavy threat
        vl_list = [
            (TileCoord(10, 10), "ALLIES", 20),
            (TileCoord(20, 20), "ALLIES", 20),
        ]
        enemies = [
            _make_mock_unit(uid="e1", faction=Faction.AXIS, x=21, y=21),
            _make_mock_unit(uid="e2", faction=Faction.AXIS, x=22, y=22),
        ]
        ctx = _make_context(friendlies=[], enemies=enemies, vl_positions=vl_list)
        result = VictoryPointAI._find_safer_vl(vl_pos, ctx, "ALLIES")
        # Both VLs have enemies nearby, so no safe VL
        assert result is None

    def test_find_safer_vl_returns_safe_vl(self):
        vl_pos = TileCoord(10, 10)
        vl_list = [
            (TileCoord(10, 10), "ALLIES", 20),
            (TileCoord(50, 50), "ALLIES", 20),  # Far from enemies
        ]
        enemies = [_make_mock_unit(uid="e1", faction=Faction.AXIS, x=12, y=10)]
        ctx = _make_context(friendlies=[], enemies=enemies, vl_positions=vl_list)
        result = VictoryPointAI._find_safer_vl(vl_pos, ctx, "ALLIES")
        assert result == TileCoord(50, 50)


# ---------------------------------------------------------------------------
# TacticalOrchestrator
# ---------------------------------------------------------------------------

class TestTacticalOrchestrator:

    def test_register_ai(self):
        orch = TacticalOrchestrator()
        orch.register(FlankingAI())
        assert "FlankingAI" in orch.registered_ais

    def test_register_multiple_ais(self):
        orch = TacticalOrchestrator()
        orch.register(FlankingAI())
        orch.register(SuppressionAI())
        orch.register(InfantryTankCoordAI())
        orch.register(VictoryPointAI())
        assert len(orch.registered_ais) == 4

    def test_tick_returns_orders(self):
        orch = TacticalOrchestrator()
        orch.register(FlankingAI())
        gmap = _make_mock_game_map(passable=True, cover_modifier=0.3)
        ctx = _make_context(
            friendlies=[
                _make_mock_unit(uid=f"f{i}", unit_type=UnitType.INFANTRY_SQUAD, x=5 + i, y=5)
                for i in range(4)
            ],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS, x=20, y=10)],
            game_map=gmap,
        )
        orders = orch.tick(ctx)
        assert isinstance(orders, list)

    def test_tick_no_ais_returns_empty(self):
        orch = TacticalOrchestrator()
        ctx = _make_context()
        orders = orch.tick(ctx)
        assert orders == []

    def test_tick_stores_scores(self):
        orch = TacticalOrchestrator()
        orch.register(FlankingAI())
        orch.register(SuppressionAI())
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="f1", unit_type=UnitType.INFANTRY_SQUAD)],
            enemies=[_make_mock_unit(uid="e1", faction=Faction.AXIS)],
        )
        orch.tick(ctx)
        assert "FlankingAI" in orch.last_scores
        assert "SuppressionAI" in orch.last_scores

    def test_tick_stores_orders(self):
        orch = TacticalOrchestrator()
        orch.register(SuppressionAI())
        mg = _make_mock_unit(uid="mg1", unit_type=UnitType.MACHINE_GUN_SQUAD, x=5, y=5)
        enemy = _make_mock_unit(uid="e1", faction=Faction.AXIS, x=15, y=5)
        ctx = _make_context(friendlies=[mg], enemies=[enemy])
        orch.tick(ctx)
        assert len(orch.last_orders) > 0

    def test_tick_conflict_resolution_highest_priority_wins(self):
        """When two AIs want the same unit, higher score*priority wins."""
        orch = TacticalOrchestrator()
        orch.register(SuppressionAI())
        orch.register(VictoryPointAI())
        mg = _make_mock_unit(uid="mg1", unit_type=UnitType.MACHINE_GUN_SQUAD, x=5, y=5)
        enemy = _make_mock_unit(uid="e1", faction=Faction.AXIS, x=15, y=5)
        vl = (TileCoord(20, 20), None, 40)
        ctx = _make_context(friendlies=[mg], enemies=[enemy], vl_positions=[vl])
        orders = orch.tick(ctx)
        # mg1 should be assigned to only one AI
        unit_ids = [o.unit_id for o in orders]
        assert unit_ids.count("mg1") <= 1

    def test_tick_below_threshold_excluded(self):
        """AIs with score < 0.1 should not produce intents."""
        orch = TacticalOrchestrator()
        orch.register(FlankingAI())
        # No mobile infantry → score 0.0
        ctx = _make_context(
            friendlies=[_make_mock_unit(uid="t1", unit_type=UnitType.TANK)],
            enemies=[],
        )
        orders = orch.tick(ctx)
        assert orders == []

    def test_last_scores_empty_before_tick(self):
        orch = TacticalOrchestrator()
        assert orch.last_scores == {}

    def test_last_orders_empty_before_tick(self):
        orch = TacticalOrchestrator()
        assert orch.last_orders == []


# ---------------------------------------------------------------------------
# TacticalContext
# ---------------------------------------------------------------------------

class TestTacticalContext:

    def test_friendly_faction_from_units(self):
        ctx = _make_context(friendlies=[_make_mock_unit(uid="f1", faction=Faction.ALLIES)])
        assert ctx.friendly_faction == Faction.ALLIES

    def test_friendly_faction_none_when_empty(self):
        ctx = _make_context(friendlies=[])
        assert ctx.friendly_faction is None

    def test_default_vl_positions_empty(self):
        ctx = _make_context()
        assert ctx.vl_positions == []

    def test_default_blackboards_empty(self):
        ctx = _make_context()
        assert ctx.blackboards == {}
