from __future__ import annotations

import pytest

from pycc2.domain.ai.behavior_tree import (
    Action,
    Condition,
    Inverter,
    NodeStatus,
    Parallel,
    Repeater,
    Selector,
    Sequence,
    WaitUntil,
)
from pycc2.domain.ai.blackboard import Blackboard


@pytest.fixture
def bb() -> Blackboard:
    return Blackboard()


class TestSequence:
    def test_empty_children_returns_success(self, bb: Blackboard):
        seq = Sequence()
        assert seq.tick(bb) == NodeStatus.SUCCESS

    def test_all_success_returns_success(self, bb: Blackboard):
        call_count = 0

        def success_fn(b):
            nonlocal call_count
            call_count += 1
            return NodeStatus.SUCCESS

        seq = Sequence(children=[Action(action_fn=success_fn), Action(action_fn=success_fn)])
        assert seq.tick(bb) == NodeStatus.SUCCESS
        assert call_count == 2

    def test_first_failure_stops_execution(self, bb: Blackboard):
        call_count = 0

        def success_fn(b):
            nonlocal call_count
            call_count += 1
            return NodeStatus.SUCCESS

        def failure_fn(b):
            nonlocal call_count
            call_count += 1
            return NodeStatus.FAILURE

        seq = Sequence(children=[Action(action_fn=failure_fn), Action(action_fn=success_fn)])
        assert seq.tick(bb) == NodeStatus.FAILURE
        assert call_count == 1

    def test_running_propagates(self, bb: Blackboard):
        def running_fn(b):
            return NodeStatus.RUNNING

        def success_fn(b):
            return NodeStatus.SUCCESS

        seq = Sequence(children=[Action(action_fn=running_fn), Action(action_fn=success_fn)])
        assert seq.tick(bb) == NodeStatus.RUNNING


class TestSelector:
    def test_empty_children_returns_failure(self, bb: Blackboard):
        sel = Selector()
        assert sel.tick(bb) == NodeStatus.FAILURE

    def test_first_success_stops_execution(self, bb: Blackboard):
        call_count = 0

        def success_fn(b):
            nonlocal call_count
            call_count += 1
            return NodeStatus.SUCCESS

        def failure_fn(b):
            nonlocal call_count
            call_count += 1
            return NodeStatus.FAILURE

        sel = Selector(children=[Action(action_fn=success_fn), Action(action_fn=failure_fn)])
        assert sel.tick(bb) == NodeStatus.SUCCESS
        assert call_count == 1

    def test_all_failure_returns_failure(self, bb: Blackboard):
        def failure_fn(b):
            return NodeStatus.FAILURE

        sel = Selector(children=[Action(action_fn=failure_fn), Action(action_fn=failure_fn)])
        assert sel.tick(bb) == NodeStatus.FAILURE

    def test_running_propagates(self, bb: Blackboard):
        def running_fn(b):
            return NodeStatus.RUNNING

        def failure_fn(b):
            return NodeStatus.FAILURE

        sel = Selector(children=[Action(action_fn=running_fn), Action(action_fn=failure_fn)])
        assert sel.tick(bb) == NodeStatus.RUNNING


class TestParallel:
    def test_all_policy_all_success(self, bb: Blackboard):
        def success_fn(b):
            return NodeStatus.SUCCESS

        par = Parallel(
            policy="ALL", children=[Action(action_fn=success_fn), Action(action_fn=success_fn)]
        )
        assert par.tick(bb) == NodeStatus.SUCCESS

    def test_all_policy_one_failure(self, bb: Blackboard):
        def success_fn(b):
            return NodeStatus.SUCCESS

        def failure_fn(b):
            return NodeStatus.FAILURE

        par = Parallel(
            policy="ALL", children=[Action(action_fn=success_fn), Action(action_fn=failure_fn)]
        )
        assert par.tick(bb) == NodeStatus.FAILURE

    def test_any_policy_one_success(self, bb: Blackboard):
        def success_fn(b):
            return NodeStatus.SUCCESS

        def failure_fn(b):
            return NodeStatus.FAILURE

        par = Parallel(
            policy="ANY", children=[Action(action_fn=failure_fn), Action(action_fn=success_fn)]
        )
        assert par.tick(bb) == NodeStatus.SUCCESS

    def test_any_policy_all_failure(self, bb: Blackboard):
        def failure_fn(b):
            return NodeStatus.FAILURE

        par = Parallel(
            policy="ANY", children=[Action(action_fn=failure_fn), Action(action_fn=failure_fn)]
        )
        assert par.tick(bb) == NodeStatus.FAILURE

    def test_empty_children_all_success_any_failure(self, bb: Blackboard):
        par_all = Parallel(policy="ALL")
        par_any = Parallel(policy="ANY")
        assert par_all.tick(bb) == NodeStatus.SUCCESS
        assert par_any.tick(bb) == NodeStatus.FAILURE


class TestCondition:
    def test_predicate_true_returns_success(self, bb: Blackboard):
        cond = Condition(predicate=lambda b: True)
        assert cond.tick(bb) == NodeStatus.SUCCESS

    def test_predicate_false_returns_failure(self, bb: Blackboard):
        cond = Condition(predicate=lambda b: False)
        assert cond.tick(bb) == NodeStatus.FAILURE


class TestAction:
    def test_action_returns_success(self, bb: Blackboard):
        action = Action(action_fn=lambda b: NodeStatus.SUCCESS)
        assert action.tick(bb) == NodeStatus.SUCCESS

    def test_action_returns_failure_or_running(self, bb: Blackboard):
        action_fail = Action(action_fn=lambda b: NodeStatus.FAILURE)
        action_run = Action(action_fn=lambda b: NodeStatus.RUNNING)

        assert action_fail.tick(bb) == NodeStatus.FAILURE
        assert action_run.tick(bb) == NodeStatus.RUNNING


class TestInverter:
    def test_inverts_success_to_failure(self, bb: Blackboard):
        inv = Inverter(child=Action(action_fn=lambda b: NodeStatus.SUCCESS))
        assert inv.tick(bb) == NodeStatus.FAILURE

    def test_inverts_failure_to_success(self, bb: Blackboard):
        inv = Inverter(child=Action(action_fn=lambda b: NodeStatus.FAILURE))
        assert inv.tick(bb) == NodeStatus.SUCCESS

    def test_running_passes_through(self, bb: Blackboard):
        inv = Inverter(child=Action(action_fn=lambda b: NodeStatus.RUNNING))
        assert inv.tick(bb) == NodeStatus.RUNNING


class TestRepeater:
    def test_repeats_n_times_then_stops(self, bb: Blackboard):
        call_count = 0

        def success_fn(b):
            nonlocal call_count
            call_count += 1
            return NodeStatus.SUCCESS

        rep = Repeater(child=Action(action_fn=success_fn), max_repeats=3)
        result = rep.tick(bb)
        assert result == NodeStatus.SUCCESS
        assert call_count == 3

    def test_infinite_loop_with_negative_one(self, bb: Blackboard):
        call_count = 0

        def success_fn(b):
            nonlocal call_count
            call_count += 1
            if call_count >= 5:
                return NodeStatus.FAILURE
            return NodeStatus.SUCCESS

        rep = Repeater(child=Action(action_fn=success_fn), max_repeats=-1)
        result = rep.tick(bb)
        assert result == NodeStatus.FAILURE
        assert call_count == 5


class TestWaitUntil:
    def test_condition_met_returns_success(self, bb: Blackboard):
        bb.set("ready", True)
        wait = WaitUntil(condition=lambda b: b.get("ready", False), timeout_ticks=10)
        assert wait.tick(bb) == NodeStatus.SUCCESS

    def test_condition_not_met_returns_running(self, bb: Blackboard):
        bb.set("_tick", 0)
        bb.set("ready", False)
        wait = WaitUntil(condition=lambda b: b.get("ready", False), timeout_ticks=10)
        assert wait.tick(bb) == NodeStatus.RUNNING

    def test_timeout_returns_failure(self, bb: Blackboard):
        bb.set("_tick", 0)
        bb.set("ready", False)
        wait = WaitUntil(condition=lambda b: b.get("ready", False), timeout_ticks=5)

        assert wait.tick(bb) == NodeStatus.RUNNING

        bb.set("_tick", 3)
        assert wait.tick(bb) == NodeStatus.RUNNING

        bb.set("_tick", 6)
        assert wait.tick(bb) == NodeStatus.FAILURE
