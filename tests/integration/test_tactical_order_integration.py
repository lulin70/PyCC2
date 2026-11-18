"""Integration tests for the unified TacticalOrder command layer (MC2-01).

Covers the design §4 test matrix:
  - PlayerCommand old path (handle_player_command) vs new path (issue_order)
    produce identical results.
  - AI ATTACK intents route through CombatDirector.issue_order as
    TacticalOrder(origin=COMMANDER), keeping the TacticExecutor morale gate.
  - Replay: issuing the same order sequence twice yields identical unit
    states and identical _order_log entries.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

# Headless pygame guard — the import chain pulls in pygame.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.ai.unit_bt_factory import UnitBTFactory
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.interfaces.event_types import PlayerCommand
from pycc2.domain.value_objects.tactical_order import OrderOrigin, TacticalOrder
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.services.ai_service import AIService
from pycc2.services.combat_director import CombatDirector


def _capture_player_commands(bus: EventBus) -> list[dict]:
    """Subscribe a recorder for PlayerCommand events published on the bus."""
    captured: list[dict] = []
    bus.subscribe(PlayerCommand, lambda event: captured.append(dict(event)))
    return captured


class _RecordingBus:
    """Minimal event bus double: records published events, no dispatch."""

    def __init__(self) -> None:
        self.published: list[Any] = []

    def subscribe(self, event_type: Any, handler: Any) -> None:
        self._handlers = getattr(self, "_handlers", {})
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: Any) -> None:
        self.published.append(event)
        handlers = getattr(self, "_handlers", {}).get(type(event), [])
        for handler in handlers:
            handler(event)

    def publish_named(self, name: str, data: dict) -> None:
        self.published.append({"named": name, **data})


def _map(width: int = 16, height: int = 16) -> GameMap:
    return GameMap(
        id="order_test",
        name="Order Test Map",
        width=width,
        height=height,
        tile_grid=np.zeros((height, width), dtype=np.int8),
    )


def _unit(
    unit_id: str = "u1",
    faction: Faction = Faction.ALLIES,
    x: int = 5,
    y: int = 5,
    morale_value: int = 80,
) -> Unit:
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=morale_value),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=8),
    )


def _director(bus: _RecordingBus | None = None) -> CombatDirector:
    return CombatDirector(event_bus=bus or _RecordingBus(), display_config=object())


# ============================================================================
# PlayerCommand old path vs issue_order new path — result equivalence
# ============================================================================


class TestPlayerCommandEquivalence:
    def test_defend_command_equivalent(self):
        old_unit, new_unit = _unit(), _unit()
        old_director, new_director = _director(), _director()

        old_director.handle_player_command(
            {"command": "defend", "unit_ids": ["u1"]}, [old_unit], _map()
        )
        issued = new_director.issue_order(
            TacticalOrder(command="defend", unit_ids=("u1",), origin=OrderOrigin.PLAYER),
            unit_map={"u1": new_unit},
            units=[new_unit],
            game_map=_map(),
        )

        assert issued is True
        assert old_unit.movement_mode == new_unit.movement_mode == "defend"

    def test_set_fire_mode_param_equivalent(self):
        old_unit, new_unit = _unit(), _unit()
        old_director, new_director = _director(), _director()

        old_director.handle_player_command(
            {"command": "set_fire_mode", "unit_ids": ["u1"], "fire_mode": "hold"},
            [old_unit],
            _map(),
        )
        new_director.issue_order(
            TacticalOrder(
                command="set_fire_mode",
                unit_ids=("u1",),
                origin=OrderOrigin.PLAYER,
                params={"fire_mode": "hold"},
            ),
            unit_map={"u1": new_unit},
            units=[new_unit],
            game_map=_map(),
        )

        assert old_unit.fire_mode == new_unit.fire_mode == "hold"

    def test_multi_unit_equivalent(self):
        old_units = [_unit("u1"), _unit("u2", x=6)]
        new_units = [_unit("u1"), _unit("u2", x=6)]
        old_director, new_director = _director(), _director()

        old_director.handle_player_command(
            {"command": "stop", "unit_ids": ["u1", "u2"]}, old_units, _map()
        )
        new_director.issue_order(
            TacticalOrder(command="stop", unit_ids=("u1", "u2"), origin=OrderOrigin.PLAYER),
            unit_map={u.id: u for u in new_units},
            units=new_units,
            game_map=_map(),
        )

        for old, new in zip(old_units, new_units, strict=True):
            assert old.movement_mode == new.movement_mode == "normal"

    def test_attack_routes_into_execute_attack(self):
        bus = _RecordingBus()
        director = CombatDirector(event_bus=bus, display_config=object())
        attacker = _unit("a1", Faction.AXIS)
        target = _unit("t1", Faction.ALLIES, x=6)
        director.execute_attack = lambda attacker_unit, target_unit: bus.published.append(
            ("executed", attacker_unit.id, target_unit.id)
        )

        result = director.issue_order(
            TacticalOrder(
                command="attack",
                unit_ids=("a1",),
                origin=OrderOrigin.PLAYER,
                params={"target_id": "t1"},
            ),
            unit_map={"a1": attacker, "t1": target},
            units=[attacker, target],
            game_map=_map(),
        )

        assert result is True
        assert bus.published == [("executed", "a1", "t1")]

    def test_unknown_command_returns_false_and_not_logged(self):
        director = _director()
        unit = _unit()
        result = director.issue_order(
            TacticalOrder(command="teleport", unit_ids=("u1",), origin=OrderOrigin.PLAYER),
            unit_map={"u1": unit},
            units=[unit],
            game_map=_map(),
        )
        assert result is False
        assert list(director._order_log) == []

    def test_order_log_records_origin_from_event(self):
        director = _director()
        player_unit = _unit("p1")
        commander_unit = _unit("c1")

        director.handle_player_command(
            {"command": "defend", "unit_ids": ["p1"]}, [player_unit], _map()
        )
        director.handle_player_command(
            {"command": "defend", "unit_ids": ["c1"], "origin": "commander"},
            [commander_unit],
            _map(),
        )
        director.handle_player_command(
            {"command": "defend", "unit_ids": ["p1"], "origin": "bogus"}, [player_unit], _map()
        )

        origins = [order.origin for order in director._order_log]
        assert origins == [OrderOrigin.PLAYER, OrderOrigin.COMMANDER, OrderOrigin.PLAYER]


# ============================================================================
# AI intent routing through issue_order
# ============================================================================


def _ai_with_director(
    units: list[Unit], game_map: GameMap, with_director: bool = True
) -> tuple[AIService, CombatDirector | None, EventBus]:
    bus = EventBus()
    director = _director() if with_director else None
    ai = AIService(event_bus=bus)
    if director is not None:
        ai.set_combat_director(director)
    for unit in units:
        ai.register_ai_unit(unit, UnitBTFactory.create_infantry_bt(unit_id=unit.id))
    # tick() captures the battlefield context needed by the issue_order path.
    ai.tick(1.0 / 30.0, game_map=game_map, all_units=list(units))
    return ai, director, bus


class TestAIIntentRouting:
    def test_attack_intent_routes_via_issue_order(self):
        attacker = _unit("a1", Faction.AXIS)
        target = _unit("t1", Faction.ALLIES, x=6)
        game_map = _map()
        ai, director, _bus = _ai_with_director([attacker, target], game_map)
        assert director is not None
        baseline = len(director._order_log)

        results = ai.execute_intents(
            [TacticIntent(unit_id="a1", tactic_type=TacticType.ATTACK, target_unit_id="t1")]
        )

        assert results == {"a1": True}
        commander_orders = [
            order
            for order in list(director._order_log)[baseline:]
            if order.command == "attack" and order.origin == OrderOrigin.COMMANDER
        ]
        assert len(commander_orders) == 1
        assert commander_orders[0].unit_ids == ("a1",)
        assert commander_orders[0].params == {"target_id": "t1"}

    def test_attack_intent_without_director_keeps_executor_path(self):
        attacker = _unit("a1", Faction.AXIS)
        target = _unit("t1", Faction.ALLIES, x=6)
        game_map = _map()
        ai, director, bus = _ai_with_director([attacker, target], game_map, with_director=False)
        captured = _capture_player_commands(bus)

        assert director is None
        results = ai.execute_intents(
            [TacticIntent(unit_id="a1", tactic_type=TacticType.ATTACK, target_unit_id="t1")]
        )

        assert results == {"a1": True}
        published_attacks = [event for event in captured if event.get("command") == "attack"]
        assert len(published_attacks) == 1

    def test_attack_intent_without_tick_context_falls_back_to_executor(self):
        bus = EventBus()
        director = _director()
        ai = AIService(event_bus=bus)
        ai.set_combat_director(director)
        attacker = _unit("a1", Faction.AXIS)
        target = _unit("t1", Faction.ALLIES, x=6)
        for unit in (attacker, target):
            ai.register_ai_unit(unit, UnitBTFactory.create_infantry_bt(unit_id=unit.id))
        # No tick() call: battlefield context is missing.
        captured = _capture_player_commands(bus)

        results = ai.execute_intents(
            [TacticIntent(unit_id="a1", tactic_type=TacticType.ATTACK, target_unit_id="t1")]
        )

        assert results == {"a1": True}
        published_attacks = [event for event in captured if event.get("command") == "attack"]
        assert len(published_attacks) == 1
        assert list(director._order_log) == []

    def test_routing_preserves_morale_gate(self, mocker):
        attacker = _unit("a1", Faction.AXIS, morale_value=10)  # BROKEN range
        target = _unit("t1", Faction.ALLIES, x=6)
        game_map = _map()
        ai, director, _bus = _ai_with_director([attacker, target], game_map)
        assert director is not None

        # TacticExecutor rolls random.random() < 0.3 for BROKEN units.
        mocker.patch("random.random", return_value=0.0)  # refuse the order
        baseline = len(director._order_log)
        results = ai.execute_intents(
            [TacticIntent(unit_id="a1", tactic_type=TacticType.ATTACK, target_unit_id="t1")]
        )
        assert results == {"a1": False}
        assert len(director._order_log) == baseline

        mocker.patch("random.random", return_value=1.0)  # accept the order
        baseline = len(director._order_log)
        results = ai.execute_intents(
            [TacticIntent(unit_id="a1", tactic_type=TacticType.ATTACK, target_unit_id="t1")]
        )
        assert results == {"a1": True}
        new_orders = list(director._order_log)[baseline:]
        assert any(order.origin == OrderOrigin.COMMANDER for order in new_orders)


# ============================================================================
# Replay consistency: same order sequence → same results + same _order_log
# ============================================================================


def _replay_sequence() -> list[TacticalOrder]:
    return [
        TacticalOrder(
            command="defend",
            unit_ids=("u1",),
            origin=OrderOrigin.PLAYER,
            timestamp=1.0,
            issued_tick=10,
        ),
        TacticalOrder(
            command="set_fire_mode",
            unit_ids=("u1",),
            origin=OrderOrigin.PLAYER,
            params={"fire_mode": "hold"},
            timestamp=2.0,
            issued_tick=20,
        ),
        TacticalOrder(
            command="stop",
            unit_ids=("u1",),
            origin=OrderOrigin.PLAYER,
            timestamp=3.0,
            issued_tick=30,
        ),
        TacticalOrder(
            command="fast_move",
            unit_ids=("u1",),
            origin=OrderOrigin.PLAYER,
            timestamp=4.0,
            issued_tick=40,
        ),
        TacticalOrder(
            command="set_fire_mode",
            unit_ids=("u1",),
            origin=OrderOrigin.PLAYER,  # cycle fire mode (no explicit mode)
            timestamp=5.0,
            issued_tick=50,
        ),
    ]


class TestOrderReplayConsistency:
    def test_same_sequence_replays_identically(self):
        final_states: list[SimpleNamespace] = []
        logs: list[list[TacticalOrder]] = []

        for _run in range(2):
            director = _director()
            unit = _unit("u1")
            game_map = _map()
            for order in _replay_sequence():
                assert director.issue_order(
                    order,
                    unit_map={unit.id: unit},
                    units=[unit],
                    game_map=game_map,
                )
            final_states.append(
                SimpleNamespace(movement_mode=unit.movement_mode, fire_mode=unit.fire_mode)
            )
            logs.append(list(director._order_log))

        assert final_states[0].movement_mode == final_states[1].movement_mode
        assert final_states[0].fire_mode == final_states[1].fire_mode
        assert logs[0] == logs[1]
        assert len(logs[0]) == len(_replay_sequence())

    def test_replayed_log_reproduces_same_results_on_fresh_director(self):
        reference_unit = _unit("u1")
        reference_director = _director()
        game_map = _map()
        for order in _replay_sequence():
            reference_director.issue_order(
                order,
                unit_map={"u1": reference_unit},
                units=[reference_unit],
                game_map=game_map,
            )

        replay_unit = _unit("u1")
        replay_director = _director()
        for logged_order in reference_director._order_log:
            replay_director.issue_order(
                logged_order,
                unit_map={"u1": replay_unit},
                units=[replay_unit],
                game_map=game_map,
            )

        assert replay_unit.movement_mode == reference_unit.movement_mode
        assert replay_unit.fire_mode == reference_unit.fire_mode


@pytest.mark.integration
class TestOrderLogRingBuffer:
    def test_order_log_respects_maxlen(self):
        director = _director()
        unit = _unit("u1")
        game_map = _map()
        for tick in range(1001):
            director.issue_order(
                TacticalOrder(
                    command="set_fire_mode",
                    unit_ids=("u1",),
                    origin=OrderOrigin.PLAYER,
                    issued_tick=tick,
                ),
                unit_map={"u1": unit},
                units=[unit],
                game_map=game_map,
            )
        assert len(director._order_log) == 1000
        assert director._order_log[0].issued_tick == 1  # oldest entry evicted
