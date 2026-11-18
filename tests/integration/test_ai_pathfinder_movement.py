"""MC2 Wave 4 integration tests: AI movement through the CombatDirector pipeline.

Design §4 integration matrix:
  - AI move intents route through CombatDirector.issue_order as
    TacticalOrder(command="move", origin=COMMANDER) — visible in _order_log;
  - the issued order lands in director._move_orders and process_movements
    advances the unit continuously along the pathfinder path;
  - AI head-on swap scenario takes part in the Wave 3 yield negotiation
    (same pattern as tests/integration/test_movement_yield_negotiation.py);
  - after arrival the AI can attack through issue_order (full chain: move →
    arrive → attack order → execute_attack fires the weapon).
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np

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
from pycc2.domain.systems.pathfinder import PathFinder
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.infrastructure.events.event_bus import EventBus
from pycc2.services.ai_service import AIService
from pycc2.services.combat_director import CombatDirector


def _make_unit(
    unit_id: str,
    faction: Faction,
    x: int,
    y: int,
    *,
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


def _place_at_tile_center(unit: Unit, tile_x: int, tile_y: int) -> None:
    unit.position.tile_coord = TileCoord(tile_x, tile_y)
    unit.position.set_pixel_offset(Vec2(24.0, 24.0))


def _map() -> GameMap:
    return GameMap(
        id="ai_move_pipeline_test",
        name="AI Move Pipeline Test Map",
        width=16,
        height=16,
        tile_grid=np.zeros((16, 16), dtype=np.int8),
    )


def _director_with_pathfinder() -> CombatDirector:
    """Real CombatDirector with a live pathfinder (initialize() pulls pygame-
    dependent subsystems; only the pathfinder is needed for move dispatch)."""
    director = CombatDirector(event_bus=EventBus(), display_config=object())  # type: ignore[arg-type]
    director.pathfinder = PathFinder()
    return director


class _RecordingBus:
    """Minimal event bus double: records published events, no dispatch."""

    def __init__(self) -> None:
        self.published: list[Any] = []

    def subscribe(self, event_type: Any, handler: Any) -> None:
        self._handlers = getattr(self, "_handlers", {})
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: Any) -> None:
        self.published.append(event)
        for handler in getattr(self, "_handlers", {}).get(type(event), []):
            handler(event)

    def publish_named(self, name: str, data: dict) -> None:
        self.published.append({"named": name, **data})


def _ai_with_director(
    units: list[Unit],
    game_map: GameMap,
    director: CombatDirector,
    bus: EventBus | None = None,
) -> AIService:
    ai = AIService(event_bus=bus or EventBus())
    ai.set_combat_director(director)
    for unit in units:
        ai.register_ai_unit(unit, UnitBTFactory.create_infantry_bt(unit_id=unit.id))
    # tick() captures the battlefield context needed by the issue_order path.
    ai.tick(1.0 / 30.0, game_map=game_map, all_units=list(units))
    return ai


def _commander_move_orders(director: CombatDirector, baseline: int) -> list:
    return [
        order
        for order in list(director._order_log)[baseline:]
        if order.command == "move" and order.origin.value == "commander"
    ]


class TestAIMoveRoutesThroughIssueOrder:
    """AI 移动经 issue_order：_order_log 含 origin=COMMANDER 的 move 单。"""

    def test_move_intent_logged_with_commander_origin(self):
        mover = _make_unit("m1", Faction.AXIS, 4, 4)
        game_map = _map()
        director = _director_with_pathfinder()
        ai = _ai_with_director([mover], game_map, director)
        baseline = len(director._order_log)

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="m1", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(8, 4)
                )
            ]
        )

        assert results == {"m1": True}
        moves = _commander_move_orders(director, baseline)
        assert len(moves) == 1
        assert moves[0].unit_ids == ("m1",)
        assert moves[0].params == {"target": (8, 4)}

    def test_patrol_and_retreat_intents_also_logged_as_move(self):
        mover = _make_unit("m2", Faction.AXIS, 4, 4)
        game_map = _map()
        director = _director_with_pathfinder()
        ai = _ai_with_director([mover], game_map, director)
        baseline = len(director._order_log)

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="m2", tactic_type=TacticType.PATROL, target_position=TileCoord(6, 4)
                ),
                TacticIntent(
                    unit_id="m2", tactic_type=TacticType.RETREAT, target_position=TileCoord(2, 4)
                ),
            ]
        )

        assert results == {"m2": True}
        moves = _commander_move_orders(director, baseline)
        assert [order.params["target"] for order in moves] == [(6, 4), (2, 4)]

    def test_unreachable_goal_falls_back_to_executor_no_order(self):
        """Goal outside the map bounds → find_path None → executor one-step."""
        mover = _make_unit("m3", Faction.AXIS, 4, 4)
        game_map = _map()
        director = _director_with_pathfinder()
        ai = _ai_with_director([mover], game_map, director)
        baseline = len(director._order_log)

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="m3", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(60, 60)
                )
            ]
        )

        assert results == {"m3": True}
        assert list(director._order_log)[baseline:] == []
        # Executor one-step fallback (AIService executor has no pathfinder).
        assert mover.position.tile_coord == TileCoord(60, 60)


class TestAIMoveAdvancesAlongPath:
    """Issued move orders land in _move_orders and advance continuously."""

    def test_ai_unit_walks_path_tile_by_tile(self):
        mover = _make_unit("w1", Faction.AXIS, 2, 2)
        game_map = _map()
        director = _director_with_pathfinder()
        ai = _ai_with_director([mover], game_map, director)
        _place_at_tile_center(mover, 2, 2)

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="w1", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(5, 2)
                )
            ]
        )
        assert results == {"w1": True}
        # The pathfinder path is queued for continuous advancement.
        assert "w1" in director._move_orders
        queued = director._move_orders["w1"]["path"]
        assert list(queued) == [TileCoord(3, 2), TileCoord(4, 2), TileCoord(5, 2)]

        units = [mover]
        for _tick in range(60):
            director.process_movements(units, game_map)

        assert "w1" not in director._move_orders
        assert mover.position.tile_coord == TileCoord(5, 2)

    def test_ai_head_on_swap_enters_yield_negotiation(self):
        """对冲场景：两个 AI 单位互换目标 tile，双方 yield（Wave 3 模式），
        超时阀放行后双方到达——不换机制时 AI 瞬移根本进不了协商。"""
        ally = _make_unit("swap_a", Faction.ALLIES, 5, 5)
        axis = _make_unit("swap_b", Faction.AXIS, 6, 5)
        game_map = _map()
        director = _director_with_pathfinder()
        ai = _ai_with_director([ally, axis], game_map, director)
        _place_at_tile_center(ally, 5, 5)
        _place_at_tile_center(axis, 6, 5)

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="swap_a",
                    tactic_type=TacticType.MOVE_TO,
                    target_position=TileCoord(6, 5),
                ),
                TacticIntent(
                    unit_id="swap_b",
                    tactic_type=TacticType.MOVE_TO,
                    target_position=TileCoord(5, 5),
                ),
            ]
        )
        assert results == {"swap_a": True, "swap_b": True}

        units = [ally, axis]
        for _tick in range(12):
            director.process_movements(units, game_map)

        # Negotiation active: both sides are yielding, neither has committed.
        assert director._move_orders["swap_a"]["yield_ticks"] >= 1
        assert director._move_orders["swap_b"]["yield_ticks"] >= 1
        assert list(director._move_orders["swap_a"]["path"]) == [TileCoord(6, 5)]
        assert list(director._move_orders["swap_b"]["path"]) == [TileCoord(5, 5)]

        # The 90-tick valve releases the deadlock: both arrive, orders clear.
        for _tick in range(200):
            director.process_movements(units, game_map)
        assert "swap_a" not in director._move_orders
        assert "swap_b" not in director._move_orders
        assert ally.position.tile_coord == TileCoord(6, 5)
        assert axis.position.tile_coord == TileCoord(5, 5)


class TestAIArriveThenAttackChain:
    """AI 到达后可攻击（链路）：move → arrive → attack order → weapon fires."""

    def test_move_arrive_then_attack_via_issue_order(self):
        bus = _RecordingBus()
        mover = _make_unit("chain_m", Faction.AXIS, 2, 2)
        enemy = _make_unit("chain_e", Faction.ALLIES, 6, 2)
        game_map = _map()
        director = _director_with_pathfinder()
        director.event_bus = bus  # type: ignore[assignment]
        from pycc2.domain.systems.ballistic import BallisticEngine
        from pycc2.services.random_context import RandomContext

        director.ballistic_engine = BallisticEngine(rng=RandomContext())
        director.set_context([mover, enemy], game_map)

        ai = _ai_with_director([mover, enemy], game_map, director, bus=bus)
        _place_at_tile_center(mover, 2, 2)
        _place_at_tile_center(enemy, 6, 2)
        baseline = len(director._order_log)
        initial_ammo = mover.weapon.ammo_remaining

        # 1. MOVE: AI walks from (2,2) to (5,2), adjacent to the enemy.
        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="chain_m",
                    tactic_type=TacticType.MOVE_TO,
                    target_position=TileCoord(5, 2),
                )
            ]
        )
        assert results == {"chain_m": True}
        for _tick in range(60):
            director.process_movements([mover, enemy], game_map)
        assert mover.position.tile_coord == TileCoord(5, 2)

        # 2. ATTACK: routed through issue_order like Wave 1.
        attack_results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="chain_m", tactic_type=TacticType.ATTACK, target_unit_id="chain_e"
                )
            ]
        )
        assert attack_results == {"chain_m": True}

        new_orders = list(director._order_log)[baseline:]
        move_orders = [
            o for o in new_orders if o.command == "move" and o.origin.value == "commander"
        ]
        attack_orders = [
            o for o in new_orders if o.command == "attack" and o.origin.value == "commander"
        ]
        assert len(move_orders) == 1
        assert move_orders[0].params == {"target": (5, 2)}
        assert len(attack_orders) == 1
        assert attack_orders[0].unit_ids == ("chain_m",)
        assert attack_orders[0].params == {"target_id": "chain_e"}

        # 3. The attack pipeline actually fired the weapon.
        # UnitAttacked is a TypedDict — published instances are plain dicts.
        attacks = [
            e
            for e in bus.published
            if isinstance(e, dict)
            and e.get("attacker_id") == "chain_m"
            and e.get("target_id") == "chain_e"
            and "kill_shot" in e  # UnitAttacked (ProjectileFired lacks it)
        ]
        assert len(attacks) == 1
        assert mover.weapon.ammo_remaining < initial_ammo


class TestAIYieldAgainstStaticBlocker:
    """AI mover yields behind a stationary unit (Wave 3 static-blocker pattern)."""

    def test_ai_mover_yields_then_passes_static_sentry(self):
        mover = _make_unit("blk_m", Faction.AXIS, 5, 5)
        sentry = _make_unit("blk_s", Faction.AXIS, 6, 5)
        game_map = _map()
        director = _director_with_pathfinder()
        ai = _ai_with_director([mover, sentry], game_map, director)
        _place_at_tile_center(mover, 5, 5)
        _place_at_tile_center(sentry, 6, 5)

        results = ai.execute_intents(
            [
                TacticIntent(
                    unit_id="blk_m", tactic_type=TacticType.MOVE_TO, target_position=TileCoord(7, 5)
                )
            ]
        )
        assert results == {"blk_m": True}
        # Sanity: the queued path passes through the sentry tile.
        assert list(director._move_orders["blk_m"]["path"]) == [TileCoord(6, 5), TileCoord(7, 5)]

        units = [mover, sentry]
        for _tick in range(20):
            director.process_movements(units, game_map)

        order = director._move_orders["blk_m"]
        assert order["yield_ticks"] >= 10
        assert list(order["path"]) == [TileCoord(6, 5), TileCoord(7, 5)]
        assert mover.position.pixel_offset.x < 24.0

        for _tick in range(200):
            director.process_movements(units, game_map)
        assert "blk_m" not in director._move_orders
        assert mover.position.tile_coord == TileCoord(7, 5)
        assert sentry.position.tile_coord == TileCoord(6, 5)
