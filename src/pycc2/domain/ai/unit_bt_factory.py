"""Factory that assembles behavior trees for individual unit types and roles."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pycc2.domain.ai.behavior_tree import (
    Action,
    BTNode,
    Condition,
    NodeStatus,
    Selector,
    Sequence,
)
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType

if TYPE_CHECKING:
    from pycc2.domain.ai.blackboard import Blackboard


class UnitBTFactory:
    """Static factory assembling behavior trees tailored to each unit type."""

    @staticmethod
    def create_infantry_bt(unit_id: str) -> BTNode:
        def _check_low_health(bb: Blackboard) -> bool:
            return float(bb.get("health_ratio", 1.0)) < 0.3

        def _do_retreat(bb: Blackboard) -> NodeStatus:
            bb.set(
                "current_intent",
                TacticIntent(unit_id=unit_id, tactic_type=TacticType.RETREAT, priority=10),
            )
            return NodeStatus.SUCCESS

        def _has_visible_enemies(bb: Blackboard) -> bool:
            enemies = bb.get("visible_enemies", [])
            return len(enemies) > 0

        def _is_close_range(bb: Blackboard) -> bool:
            dist = bb.get("nearest_enemy_distance", 999)
            return float(dist) <= 5.0

        def _do_attack(bb: Blackboard) -> NodeStatus:
            target_id = bb.get("nearest_enemy_id")
            pos = bb.get("nearest_enemy_position")
            bb.set(
                "current_intent",
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.ATTACK,
                    target_unit_id=target_id,
                    target_position=pos,
                    priority=8,
                ),
            )
            return NodeStatus.SUCCESS

        def _has_cover(bb: Blackboard) -> bool:
            return bool(bb.get("has_cover_nearby", False))

        def _do_take_cover(bb: Blackboard) -> NodeStatus:
            cover_pos = bb.get("nearest_cover_position")
            bb.set(
                "current_intent",
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.TAKE_COVER,
                    target_position=cover_pos,
                    priority=6,
                ),
            )
            return NodeStatus.SUCCESS

        def _do_move_to_enemy(bb: Blackboard) -> NodeStatus:
            pos = bb.get("nearest_enemy_position")
            bb.set(
                "current_intent",
                TacticIntent(
                    unit_id=unit_id, tactic_type=TacticType.MOVE_TO, target_position=pos, priority=5
                ),
            )
            return NodeStatus.SUCCESS

        def _has_order(bb: Blackboard) -> bool:
            return bool(bb.get("pending_order", None))

        def _execute_order(bb: Blackboard) -> NodeStatus:
            order = bb.get("pending_order")
            if isinstance(order, TacticIntent):
                bb.set("current_intent", order)
            else:
                return NodeStatus.FAILURE
            return NodeStatus.SUCCESS

        def _do_patrol(bb: Blackboard) -> NodeStatus:
            patrol_pos = bb.get("patrol_target")
            bb.set(
                "current_intent",
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.PATROL,
                    target_position=patrol_pos,
                    priority=2,
                ),
            )
            return NodeStatus.SUCCESS

        return Selector(
            children=[
                Sequence(
                    children=[
                        Condition(predicate=_check_low_health),
                        Action(action_fn=_do_retreat),
                    ]
                ),
                Sequence(
                    children=[
                        Condition(predicate=_has_visible_enemies),
                        Selector(
                            children=[
                                Sequence(
                                    children=[
                                        Condition(predicate=_is_close_range),
                                        Action(action_fn=_do_attack),
                                    ]
                                ),
                                Sequence(
                                    children=[
                                        Condition(predicate=_has_cover),
                                        Action(action_fn=_do_take_cover),
                                    ]
                                ),
                                Action(action_fn=_do_move_to_enemy),
                            ]
                        ),
                    ]
                ),
                Sequence(
                    children=[
                        Condition(predicate=_has_order),
                        Action(action_fn=_execute_order),
                    ]
                ),
                Action(action_fn=_do_patrol),
            ]
        )

    @staticmethod
    def create_mg_squad_bt(unit_id: str) -> BTNode:
        def _check_low_health(bb: Blackboard) -> bool:
            return float(bb.get("health_ratio", 1.0)) < 0.25

        def _do_retreat(bb: Blackboard) -> NodeStatus:
            bb.set(
                "current_intent",
                TacticIntent(unit_id=unit_id, tactic_type=TacticType.RETREAT, priority=12),
            )
            return NodeStatus.SUCCESS

        def _has_visible_enemies(bb: Blackboard) -> bool:
            enemies = bb.get("visible_enemies", [])
            return len(enemies) > 0

        def _do_suppress_fire(bb: Blackboard) -> NodeStatus:
            target_id = bb.get("nearest_enemy_id")
            pos = bb.get("nearest_enemy_position")
            bb.set(
                "current_intent",
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.SUPPRESS_FIRE,
                    target_unit_id=target_id,
                    target_position=pos,
                    priority=9,
                ),
            )
            return NodeStatus.SUCCESS

        def _is_close_range(bb: Blackboard) -> bool:
            dist = bb.get("nearest_enemy_distance", 999)
            return float(dist) <= 4.0

        def _do_attack(bb: Blackboard) -> NodeStatus:
            target_id = bb.get("nearest_enemy_id")
            pos = bb.get("nearest_enemy_position")
            bb.set(
                "current_intent",
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.ATTACK,
                    target_unit_id=target_id,
                    target_position=pos,
                    priority=8,
                ),
            )
            return NodeStatus.SUCCESS

        def _do_hold_and_suppress(bb: Blackboard) -> NodeStatus:
            bb.set(
                "current_intent",
                TacticIntent(unit_id=unit_id, tactic_type=TacticType.HOLD_POSITION, priority=7),
            )
            return NodeStatus.SUCCESS

        def _has_order(bb: Blackboard) -> bool:
            return bool(bb.get("pending_order", None))

        def _execute_order(bb: Blackboard) -> NodeStatus:
            order = bb.get("pending_order")
            if isinstance(order, TacticIntent):
                bb.set("current_intent", order)
            else:
                return NodeStatus.FAILURE
            return NodeStatus.SUCCESS

        def _do_patrol(bb: Blackboard) -> NodeStatus:
            patrol_pos = bb.get("patrol_target")
            bb.set(
                "current_intent",
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.PATROL,
                    target_position=patrol_pos,
                    priority=2,
                ),
            )
            return NodeStatus.SUCCESS

        return Selector(
            children=[
                Sequence(
                    children=[
                        Condition(predicate=_check_low_health),
                        Action(action_fn=_do_retreat),
                    ]
                ),
                Sequence(
                    children=[
                        Condition(predicate=_has_visible_enemies),
                        Selector(
                            children=[
                                Action(action_fn=_do_suppress_fire),
                                Sequence(
                                    children=[
                                        Condition(predicate=_is_close_range),
                                        Action(action_fn=_do_attack),
                                    ]
                                ),
                                Action(action_fn=_do_hold_and_suppress),
                            ]
                        ),
                    ]
                ),
                Sequence(
                    children=[
                        Condition(predicate=_has_order),
                        Action(action_fn=_execute_order),
                    ]
                ),
                Action(action_fn=_do_patrol),
            ]
        )

    @staticmethod
    def create_commander_bt(unit_id: str) -> BTNode:
        def _check_critical_health(bb: Blackboard) -> bool:
            return float(bb.get("health_ratio", 1.0)) < 0.2

        def _do_regroup(bb: Blackboard) -> NodeStatus:
            regroup_pos = bb.get("regroup_point")
            bb.set(
                "current_intent",
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.REGROUP,
                    target_position=regroup_pos,
                    priority=15,
                ),
            )
            return NodeStatus.SUCCESS

        def _has_visible_enemies(bb: Blackboard) -> bool:
            enemies = bb.get("visible_enemies", [])
            return len(enemies) > 0

        def _allies_need_support(bb: Blackboard) -> bool:
            allies = bb.get("allies_nearby", 0)
            return int(allies) < 2

        def _do_hold_position(bb: Blackboard) -> NodeStatus:
            bb.set(
                "current_intent",
                TacticIntent(unit_id=unit_id, tactic_type=TacticType.HOLD_POSITION, priority=10),
            )
            return NodeStatus.SUCCESS

        def _do_defend(bb: Blackboard) -> NodeStatus:
            bb.set(
                "current_intent",
                TacticIntent(unit_id=unit_id, tactic_type=TacticType.DEFEND, priority=9),
            )
            return NodeStatus.SUCCESS

        def _do_regroup_allies(bb: Blackboard) -> NodeStatus:
            regroup_pos = bb.get("regroup_point")
            bb.set(
                "current_intent",
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.REGROUP,
                    target_position=regroup_pos,
                    priority=12,
                ),
            )
            return NodeStatus.SUCCESS

        def _has_order(bb: Blackboard) -> bool:
            return bool(bb.get("pending_order", None))

        def _execute_order(bb: Blackboard) -> NodeStatus:
            order = bb.get("pending_order")
            if isinstance(order, TacticIntent):
                bb.set("current_intent", order)
            else:
                return NodeStatus.FAILURE
            return NodeStatus.SUCCESS

        def _do_patrol(bb: Blackboard) -> NodeStatus:
            patrol_pos = bb.get("patrol_target")
            bb.set(
                "current_intent",
                TacticIntent(
                    unit_id=unit_id,
                    tactic_type=TacticType.PATROL,
                    target_position=patrol_pos,
                    priority=3,
                ),
            )
            return NodeStatus.SUCCESS

        return Selector(
            children=[
                Sequence(
                    children=[
                        Condition(predicate=_check_critical_health),
                        Action(action_fn=_do_regroup),
                    ]
                ),
                Sequence(
                    children=[
                        Condition(predicate=_has_visible_enemies),
                        Selector(
                            children=[
                                Sequence(
                                    children=[
                                        Condition(predicate=_allies_need_support),
                                        Action(action_fn=_do_regroup_allies),
                                    ]
                                ),
                                Action(action_fn=_do_hold_position),
                                Action(action_fn=_do_defend),
                            ]
                        ),
                    ]
                ),
                Sequence(
                    children=[
                        Condition(predicate=_has_order),
                        Action(action_fn=_execute_order),
                    ]
                ),
                Action(action_fn=_do_patrol),
            ]
        )
