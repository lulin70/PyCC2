"""Behavior tree primitives for tactical AI decision making."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.ai.blackboard import Blackboard


class NodeStatus(Enum):
    """Return states for behavior tree node execution."""

    SUCCESS = auto()
    FAILURE = auto()
    RUNNING = auto()


class BTNode(ABC):
    """Abstract base class for all behavior tree nodes."""

    @abstractmethod
    def tick(self, blackboard: Blackboard) -> NodeStatus: ...


@dataclass(slots=True)
class Sequence(BTNode):
    """Composite that ticks children in order, failing on the first non-success."""

    children: list[BTNode] = field(default_factory=list)

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        for child in self.children:
            status = child.tick(blackboard)
            if status != NodeStatus.SUCCESS:
                return status
        return NodeStatus.SUCCESS


@dataclass(slots=True)
class Selector(BTNode):
    """Composite that ticks children in order, succeeding on the first non-failure."""

    children: list[BTNode] = field(default_factory=list)

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        for child in self.children:
            status = child.tick(blackboard)
            if status != NodeStatus.FAILURE:
                return status
        return NodeStatus.FAILURE


@dataclass(slots=True)
class Parallel(BTNode):
    """Composite that ticks all children each step under ALL or ANY success policy."""

    children: list[BTNode] = field(default_factory=list)
    policy: str = "ALL"

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        if not self.children:
            return NodeStatus.SUCCESS if self.policy == "ALL" else NodeStatus.FAILURE

        results = [child.tick(blackboard) for child in self.children]

        if self.policy == "ALL":
            if all(r == NodeStatus.SUCCESS for r in results):
                return NodeStatus.SUCCESS
            return NodeStatus.FAILURE
        elif self.policy == "ANY":
            if any(r == NodeStatus.SUCCESS for r in results):
                return NodeStatus.SUCCESS
            return NodeStatus.FAILURE

        return NodeStatus.FAILURE


@dataclass(slots=True)
class Condition(BTNode):
    """Leaf node that succeeds or fails based on a predicate over the blackboard."""

    predicate: Callable[[Blackboard], bool]

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        return NodeStatus.SUCCESS if self.predicate(blackboard) else NodeStatus.FAILURE


@dataclass(slots=True)
class Action(BTNode):
    """Leaf node that delegates execution to a caller-supplied action function."""

    action_fn: Callable[[Blackboard], NodeStatus]

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        return self.action_fn(blackboard)


@dataclass(slots=True)
class Inverter(BTNode):
    """Decorator that swaps success and failure status of its single child."""

    child: BTNode

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        status = self.child.tick(blackboard)
        if status == NodeStatus.SUCCESS:
            return NodeStatus.FAILURE
        elif status == NodeStatus.FAILURE:
            return NodeStatus.SUCCESS
        return status


@dataclass(slots=True)
class Repeater(BTNode):
    """Decorator that re-ticks its child up to a configured repeat limit."""

    child: BTNode
    max_repeats: int = -1
    _count: int = field(default=0, init=False)

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        if self.max_repeats == 0:
            return NodeStatus.SUCCESS

        while True:
            status = self.child.tick(blackboard)
            self._count += 1

            if self.max_repeats > 0 and self._count >= self.max_repeats:
                self._count = 0
                return status

            if status != NodeStatus.SUCCESS:
                self._count = 0
                return status


@dataclass(slots=True)
class WaitUntil(BTNode):
    """Decorator that runs until a condition holds or an optional timeout expires."""

    condition: Callable[[Blackboard], bool]
    timeout_ticks: int = -1
    _start_tick: int = field(default=0, init=False)
    _initialized: bool = field(default=False, init=False)

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        if not self._initialized:
            self._start_tick = blackboard.get("_tick", 0)
            self._initialized = True

        current_tick = blackboard.get("_tick", 0)
        elapsed = current_tick - self._start_tick

        if self.condition(blackboard):
            self._initialized = False
            return NodeStatus.SUCCESS

        if self.timeout_ticks >= 0 and elapsed >= self.timeout_ticks:
            self._initialized = False
            return NodeStatus.FAILURE

        if self.timeout_ticks >= 0 and elapsed > self.timeout_ticks:
            self._initialized = False
            return NodeStatus.FAILURE

        return NodeStatus.RUNNING
