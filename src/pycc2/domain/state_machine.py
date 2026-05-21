"""
Generic Finite State Machine
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Generic, TypeVar

S = TypeVar("S", bound=Enum)


class TransitionError(Exception):
    pass


class StateMachine(Generic[S]):
    def __init__(self, initial: S, transitions: dict[S, set[S]]):
        if not isinstance(initial, Enum):
            raise TypeError(f"initial_state must be an Enum, got {type(initial)}")
        self._current = initial
        self._transitions = transitions
        self._history: list[tuple[S, S]] = []
        self._enter_callbacks: dict[S, list[Callable]] = {}
        self._exit_callbacks: dict[S, list[Callable]] = {}

    @property
    def current(self) -> S:
        return self._current

    @property
    def history(self) -> list[tuple[S, S]]:
        return self._history

    def can_transition_to(self, target: S) -> bool:
        return target in self._transitions.get(self._current, set())

    def try_transition(self, target: S) -> bool:
        if not self.can_transition_to(target):
            return False
        self._execute_transition(target)
        return True

    def transition_or_raise(self, target: S) -> None:
        if not self.can_transition_to(target):
            raise TransitionError(f"Cannot transition from {self._current.name} to {target.name}")
        self._execute_transition(target)

    def force_transition(self, target: S) -> None:
        self._execute_transition(target)

    def reset(self, state: S | None = None) -> None:
        if state is None:
            state = self._current
        self._current = state
        self._history.clear()

    def on_enter(self, state: S, callback: Callable) -> None:
        if state not in self._enter_callbacks:
            self._enter_callbacks[state] = []
        self._enter_callbacks[state].append(callback)

    def on_exit(self, state: S, callback: Callable) -> None:
        if state not in self._exit_callbacks:
            self._exit_callbacks[state] = []
        self._exit_callbacks[state].append(callback)

    def _execute_transition(self, target: S) -> None:
        old_state = self._current
        self._fire_exit_callbacks(old_state)
        self._current = target
        self._history.append((old_state, target))
        self._fire_enter_callbacks(target)

    def _fire_exit_callbacks(self, state: S) -> None:
        for cb in self._exit_callbacks.get(state, []):
            cb(state)

    def _fire_enter_callbacks(self, state: S) -> None:
        for cb in self._enter_callbacks.get(state, []):
            cb(state)
