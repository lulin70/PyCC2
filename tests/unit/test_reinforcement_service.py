"""Tests for scenario reinforcement scheduling (P0-2)."""

from __future__ import annotations

from types import SimpleNamespace

from pycc2.domain.entities.unit import Faction
from pycc2.services.reinforcement_service import TICKS_PER_TURN, ReinforcementService


class _FakeMap:
    def __init__(self, width: int = 10, height: int = 10, blocked: set[tuple[int, int]] | None = None):
        self.width = width
        self.height = height
        self._blocked = blocked or set()

    def is_passable(self, coord) -> bool:
        return (coord.x, coord.y) not in self._blocked


def _unit(x: int, y: int):
    return SimpleNamespace(
        position=SimpleNamespace(tile_coord=SimpleNamespace(x=x, y=y)),
        is_alive=True,
    )


def _scenario() -> dict:
    return {
        "forces": {
            "allies": {
                "reinforcements": [
                    {"template_id": "us_rifle_squad", "arrival_turn": 2, "from_direction": "west"}
                ]
            },
            "axis": {
                "reinforcements": [
                    {"template_id": "de_rifle_squad", "arrival_turn": 3, "from_direction": "east"}
                ]
            },
        }
    }


def test_from_scenario_collects_both_sides():
    service = ReinforcementService.from_scenario(_scenario())

    assert len(service.schedule) == 2
    assert {entry["side"] for entry in service.schedule} == {"allies", "axis"}


def test_current_turn_is_one_based():
    assert ReinforcementService.current_turn(0) == 1
    assert ReinforcementService.current_turn(TICKS_PER_TURN) == 2
    assert ReinforcementService.current_turn(TICKS_PER_TURN - 1) == 1


def test_not_due_before_arrival_turn():
    service = ReinforcementService.from_scenario(_scenario())
    calls: list[tuple] = []

    spawned = service.update(
        tick=TICKS_PER_TURN,  # turn 2
        units=[],
        game_map=_FakeMap(),
        factory=lambda *args: calls.append(args) or _unit(0, 0),
    )

    assert len(spawned) == 1
    assert spawned[0][1] == "allies"
    assert len(calls) == 1


def test_spawns_each_entry_only_once():
    service = ReinforcementService.from_scenario(_scenario())
    calls: list[tuple] = []

    def factory(*args):
        calls.append(args)
        return _unit(0, 0)

    service.update(TICKS_PER_TURN, [], _FakeMap(), factory)
    service.update(TICKS_PER_TURN * 2, [], _FakeMap(), factory)

    # Turn 2 allies spawned once; turn 3 axis spawned once.
    assert len(calls) == 2
    assert service.update(TICKS_PER_TURN * 3, [], _FakeMap(), factory) == []


def test_spawn_position_is_passable_and_unoccupied():
    service = ReinforcementService.from_scenario(_scenario())
    blocked = {(0, 0)}
    occupied = _unit(0, 1)
    captured: list[tuple[int, int]] = []

    def factory(template_id, faction, position, counter):
        captured.append(position)
        return _unit(*position)

    service.update(
        tick=TICKS_PER_TURN,  # turn 2, allies from west
        units=[occupied],
        game_map=_FakeMap(blocked=blocked),
        factory=factory,
    )

    assert captured
    position = captured[0]
    assert position not in blocked
    assert position != (0, 1)
    assert position[0] >= 0 and position[1] >= 0


def test_factory_creates_real_unit_via_deployment_manager():
    from pycc2.services.deployment_manager import DeploymentManager

    manager = DeploymentManager()
    unit = manager.create_reinforcement_unit(
        "us_rifle_squad", Faction.ALLIES, (0, 2), 42
    )

    assert unit is not None
    assert unit.id == "reinforcement_42"
    assert unit.squad_ref is not None


def test_faction_mapping():
    service = ReinforcementService.from_scenario(_scenario())
    factions: list = []

    def factory(template_id, faction, position, counter):
        factions.append(faction)
        return _unit(*position)

    service.update(TICKS_PER_TURN * 2, [], _FakeMap(), factory)

    assert Faction.ALLIES in factions
    assert Faction.AXIS in factions
