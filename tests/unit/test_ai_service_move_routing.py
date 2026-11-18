"""MC2 Wave 4 unit tests: AI move-family intent routing through issue_order.

Design §4 unit matrix:
  - MOVE_TO → TacticalOrder(command="move", origin=COMMANDER) mapping
    (parametrized over the full move-family intent list);
  - pathfinder unreachable → fallback to the executor one-step move;
  - no director → fallback to the executor one-step move;
  - missing tick context / unknown unit in unit_map → fallback;
  - RETREAT keeps its (x-3, y-3) safe-position decision logic;
  - morale gate on the original intent (pinned units refuse move orders).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pytest

from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.services.ai_service import _COMMANDER_MOVE_INTENTS, AIService


def _make_unit(
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


def _map(width: int = 16, height: int = 16) -> GameMap:
    return GameMap(
        id="move_routing_test",
        name="Move Routing Test Map",
        width=width,
        height=height,
        tile_grid=np.zeros((height, width), dtype=np.int8),
    )


@dataclass
class StubPathfinder:
    """Pathfinder double: returns a straight line, or None when unreachable."""

    reachable: bool = True

    def find_path(self, start: Any, goal: Any, game_map: Any, unit: Any = None):
        if not self.reachable:
            return None
        return [start, goal]


@dataclass
class IssuedOrder:
    command: str
    origin: Any
    unit_ids: tuple
    params: dict
    unit_map: dict
    units: list
    game_map: GameMap


@dataclass
class StubDirector:
    """Minimal CombatDirector double: records issued orders."""

    pathfinder: StubPathfinder | None = field(default_factory=StubPathfinder)
    issued: list[IssuedOrder] = field(default_factory=list)

    def issue_order(self, order, *, unit_map, units, game_map) -> bool:
        self.issued.append(
            IssuedOrder(
                command=order.command,
                origin=order.origin,
                unit_ids=order.unit_ids,
                params=dict(order.params),
                unit_map=unit_map,
                units=units,
                game_map=game_map,
            )
        )
        return True


def _ai_with_move_context(
    units: list[Unit],
    game_map: GameMap,
    director: StubDirector | None = None,
    pathfinder: StubPathfinder | None = None,
) -> AIService:
    """Build an AIService whose tick() has captured the battlefield context."""
    ai = AIService(event_bus=EventBus(), pathfinder=pathfinder)
    if director is not None:
        ai.set_combat_director(director)  # type: ignore[arg-type]
    for unit in units:
        from pycc2.domain.ai.unit_bt_factory import UnitBTFactory

        ai.register_ai_unit(unit, UnitBTFactory.create_infantry_bt(unit_id=unit.id))
    ai.tick(1.0 / 30.0, game_map=game_map, all_units=list(units))
    return ai


class TestMoveIntentMapping:
    """Design §4 unit: MOVE_TO → TacticalOrder(command="move") mapping."""

    @pytest.mark.parametrize(
        "tactic_type",
        sorted(_COMMANDER_MOVE_INTENTS, key=lambda t: t.name),
        ids=lambda t: t.name,
    )
    def test_move_family_intent_maps_to_move_order(self, tactic_type):
        unit = _make_unit("u1")
        game_map = _map()
        director = StubDirector()
        ai = _ai_with_move_context([unit], game_map, director=director)
        baseline = len(director.issued)

        results = ai.execute_intents(
            [TacticIntent(unit_id="u1", tactic_type=tactic_type, target_position=TileCoord(8, 8))]
        )

        assert results == {"u1": True}
        assert len(director.issued) == baseline + 1
        issued = director.issued[baseline]
        assert issued.command == "move"
        assert issued.unit_ids == ("u1",)
        assert issued.params == {"target": (8, 8)}
        assert issued.unit_map["u1"] is unit
        assert issued.game_map is game_map

    def test_move_order_origin_is_commander(self):
        from pycc2.domain.value_objects.tactical_order import OrderOrigin

        unit = _make_unit("u1")
        director = StubDirector()
        ai = _ai_with_move_context([unit], _map(), director=director)
        baseline = len(director.issued)

        ai.execute_intents(
            [
                TacticIntent(
                    unit_id="u1", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(9, 9)
                )
            ]
        )

        assert director.issued[baseline].origin == OrderOrigin.COMMANDER

    def test_retreat_without_target_computes_safe_position(self):
        """RETREAT decision logic preserved: no explicit target → (x-3, y-3)."""
        unit = _make_unit("u1", x=10, y=10)
        director = StubDirector()
        ai = _ai_with_move_context([unit], _map(), director=director)
        baseline = len(director.issued)

        results = ai.execute_intents([TacticIntent(unit_id="u1", tactic_type=TacticType.RETREAT)])

        assert results == {"u1": True}
        assert director.issued[baseline].params == {"target": (7, 7)}

    def test_retreat_with_explicit_target_uses_it(self):
        unit = _make_unit("u1", x=10, y=10)
        director = StubDirector()
        ai = _ai_with_move_context([unit], _map(), director=director)
        baseline = len(director.issued)

        ai.execute_intents(
            [
                TacticIntent(
                    unit_id="u1", tactic_type=TacticType.RETREAT, target_position=TileCoord(2, 2)
                )
            ]
        )

        assert director.issued[baseline].params == {"target": (2, 2)}

    @pytest.mark.parametrize(
        "tactic_type",
        [
            TacticType.PATROL,
            TacticType.REGROUP,
            TacticType.FLANKING,
            TacticType.COORDINATED_ADVANCE,
        ],
        ids=lambda t: t.name,
    )
    def test_no_target_intent_falls_back_to_executor_noop(self, tactic_type):
        """Without a destination the executor handlers are no-ops returning True;
        the routing must fall back so the result stays identical."""
        unit = _make_unit("u1")
        director = StubDirector()
        ai = _ai_with_move_context([unit], _map(), director=director)
        baseline = len(director.issued)

        results = ai.execute_intents([TacticIntent(unit_id="u1", tactic_type=tactic_type)])

        assert results == {"u1": True}
        assert len(director.issued) == baseline
        assert unit.position.tile_coord == TileCoord(5, 5)

    def test_move_to_without_target_falls_back_and_returns_false(self):
        unit = _make_unit("u1")
        director = StubDirector()
        ai = _ai_with_move_context([unit], _map(), director=director)
        baseline = len(director.issued)

        results = ai.execute_intents([TacticIntent(unit_id="u1", tactic_type=TacticType.MOVE_TO)])

        assert results == {"u1": False}
        assert len(director.issued) == baseline

    def test_capture_vl_without_target_falls_back_and_returns_false(self):
        unit = _make_unit("u1")
        director = StubDirector()
        ai = _ai_with_move_context([unit], _map(), director=director)
        baseline = len(director.issued)

        results = ai.execute_intents(
            [TacticIntent(unit_id="u1", tactic_type=TacticType.CAPTURE_VL)]
        )

        assert results == {"u1": False}
        assert len(director.issued) == baseline


class TestMoveRoutingFallbacks:
    """Design §4 unit: unreachable pathfinder / no director fallbacks."""

    def test_unreachable_target_falls_back_to_executor_one_step(self):
        """find_path failure → executor one-step move (teleport), no order."""
        unit = _make_unit("u1")
        director = StubDirector(pathfinder=StubPathfinder(reachable=False))
        ai = _ai_with_move_context([unit], _map(), director=director, pathfinder=None)
        baseline = len(director.issued)

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="u1", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(8, 8)
                )
            ]
        )

        assert results == {"u1": True}
        assert len(director.issued) == baseline
        # Executor fallback: AIService's executor has no pathfinder → teleport.
        assert unit.position.tile_coord == TileCoord(8, 8)

    def test_director_without_pathfinder_falls_back_to_executor(self):
        """A director that cannot path (pathfinder=None) must not strand the AI."""
        unit = _make_unit("u1")
        director = StubDirector(pathfinder=None)
        ai = _ai_with_move_context([unit], _map(), director=director)
        baseline = len(director.issued)

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="u1", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(8, 8)
                )
            ]
        )

        assert results == {"u1": True}
        assert len(director.issued) == baseline
        assert unit.position.tile_coord == TileCoord(8, 8)

    def test_no_director_keeps_executor_path(self):
        unit = _make_unit("u1")
        ai = _ai_with_move_context([unit], _map(), director=None)

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="u1", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(8, 8)
                )
            ]
        )

        assert results == {"u1": True}
        assert unit.position.tile_coord == TileCoord(8, 8)

    def test_missing_tick_context_falls_back_to_executor(self):
        """No tick() call → no battlefield context → executor path."""
        from pycc2.domain.ai.unit_bt_factory import UnitBTFactory

        unit = _make_unit("u1")
        director = StubDirector()
        ai = AIService(event_bus=EventBus())
        ai.set_combat_director(director)  # type: ignore[arg-type]
        ai.register_ai_unit(unit, UnitBTFactory.create_infantry_bt(unit_id="u1"))

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="u1", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(8, 8)
                )
            ]
        )

        assert results == {"u1": True}
        assert director.issued == []
        assert unit.position.tile_coord == TileCoord(8, 8)

    def test_unit_not_in_unit_map_falls_back_to_executor(self):
        """Unit registered with the AI service but absent from all_units."""
        from pycc2.domain.ai.unit_bt_factory import UnitBTFactory

        unit = _make_unit("u1")
        bystander = _make_unit("u2", x=2, y=2)
        director = StubDirector()
        ai = AIService(event_bus=EventBus())
        ai.set_combat_director(director)  # type: ignore[arg-type]
        ai.register_ai_unit(unit, UnitBTFactory.create_infantry_bt(unit_id="u1"))
        # tick captures context WITHOUT the moved unit.
        ai.tick(1.0 / 30.0, game_map=_map(), all_units=[bystander])

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="u1", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(8, 8)
                )
            ]
        )

        assert results == {"u1": True}
        assert director.issued == []
        assert unit.position.tile_coord == TileCoord(8, 8)

    def test_unknown_unit_falls_back_and_returns_false(self):
        unit = _make_unit("u1")
        director = StubDirector()
        ai = _ai_with_move_context([unit], _map(), director=director)
        baseline = len(director.issued)

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="ghost", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(8, 8)
                )
            ]
        )

        assert results == {"ghost": False}
        assert len(director.issued) == baseline


class TestMoveRoutingMoraleGate:
    """Morale gate applied to the ORIGINAL intent (executor refusal subsets)."""

    @pytest.mark.parametrize(
        "tactic_type",
        sorted(_COMMANDER_MOVE_INTENTS, key=lambda t: t.name),
        ids=lambda t: t.name,
    )
    def test_pinned_unit_refuses_every_move_family_intent(self, tactic_type):
        """PINNED refusal parity: the executor blocks movement_commands outright
        and every other non-defensive command, so all move-family intents are
        refused — the routed path gates on the ORIGINAL intent, reproducing
        this exactly (mapping to MOVE_TO would refuse for the same reason, but
        gating on the original keeps the executor's refusal reasons intact)."""
        unit = _make_unit("u1", morale_value=30)  # >20 → PINNED
        director = StubDirector()
        ai = _ai_with_move_context([unit], _map(), director=director)
        baseline = len(director.issued)

        results = ai.execute_intents(
            [TacticIntent(unit_id="u1", tactic_type=tactic_type, target_position=TileCoord(8, 8))]
        )

        assert results == {"u1": False}
        assert len(director.issued) == baseline

    def test_broken_unit_refusal_result_matches_executor(self, mocker):
        """BROKEN 30% refusal: gate False → routed False (no fallback re-roll)."""
        unit = _make_unit("u1", morale_value=10)  # ≤20 → BROKEN
        director = StubDirector()
        ai = _ai_with_move_context([unit], _map(), director=director)
        baseline = len(director.issued)

        mocker.patch("random.random", return_value=0.0)  # refuse the order

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="u1", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(8, 8)
                )
            ]
        )

        assert results == {"u1": False}
        assert len(director.issued) == baseline


class TestRoutingDoesNotTouchUnmappedIntents:
    """Mixed-semantics intents keep the executor path (no issue_order)."""

    def test_attack_still_routes_via_issue_order(self):
        """Wave 1 behavior preserved: ATTACK maps with target_id params."""
        mover = _make_unit("a1", faction=Faction.AXIS)
        target = _make_unit("t1", faction=Faction.ALLIES, x=6)
        director = StubDirector()
        ai = _ai_with_move_context([mover, target], _map(), director=director)
        baseline = len(director.issued)

        results = ai.execute_intents(
            [TacticIntent(unit_id="a1", tactic_type=TacticType.ATTACK, target_unit_id="t1")]
        )

        assert results == {"a1": True}
        assert len(director.issued) == baseline + 1
        assert director.issued[baseline].command == "attack"
        assert director.issued[baseline].params == {"target_id": "t1"}

    @pytest.mark.parametrize(
        ("tactic_type", "expected"),
        [
            pytest.param(TacticType.TAKE_COVER, True, id="TAKE_COVER"),
            pytest.param(TacticType.DEFEND_VL, True, id="DEFEND_VL"),
            pytest.param(TacticType.CLEAR_BUILDING, False, id="CLEAR_BUILDING"),
        ],
    )
    def test_mixed_semantics_intents_stay_on_executor(self, tactic_type, expected):
        """Intents with a non-move branch must not issue move orders even with
        a target_position (their extra semantics run on the executor path)."""
        unit = _make_unit("u1")
        director = StubDirector()
        ai = _ai_with_move_context([unit], _map(20, 20), director=director)
        baseline = len(director.issued)

        results = ai.execute_intents(
            [TacticIntent(unit_id="u1", tactic_type=tactic_type, target_position=TileCoord(8, 8))]
        )

        # Executor reproduces its own result (TAKE_COVER moves one step, etc.).
        assert results == {"u1": expected}
        assert len(director.issued) == baseline
