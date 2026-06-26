from __future__ import annotations

import logging
import time as _time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.interfaces.combat_director_protocol import ICombatDirector
    from pycc2.domain.systems.victory_conditions import (
        BattleStats,
        GameResult,
        VictoryConditionEvaluator,
    )
    from pycc2.services.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class VictoryManager:
    """Manages victory condition evaluation, battle stats, and game-over state."""

    _victory_evaluator: VictoryConditionEvaluator | None = field(init=False, default=None)
    _battle_stats: BattleStats | None = field(init=False, default=None)
    _game_result: GameResult | None = field(init=False, default=None)
    _game_over_tick: int = field(init=False, default=0)
    _show_post_battle: bool = field(init=False, default=False)
    _victory_detected: bool = field(init=False, default=False)
    _victory_time: float = field(init=False, default=0.0)
    _post_battle_delay: float = field(init=False, default=2.0)
    _event_bus: EventBus | None = field(init=False, default=None)
    _combat_director: ICombatDirector | None = field(init=False, default=None)

    def initialize(self, event_bus: EventBus, combat_director: ICombatDirector | None = None) -> None:
        from pycc2.domain.systems.victory_conditions import (
            BattleStats,
            VictoryConditionEvaluator,
            VictoryConditionType,
        )
        from pycc2.services.event_protocol import UnitAttacked

        self._event_bus = event_bus
        self._combat_director = combat_director

        self._battle_stats = BattleStats(start_time=_time.perf_counter())
        self._victory_evaluator = VictoryConditionEvaluator(
            conditions=[
                VictoryConditionType.OCCUPY_OBJECTIVE,
                VictoryConditionType.ELIMINATE_ALL_ENEMIES,
                VictoryConditionType.FORCE_MORALE_COLLAPSE,
            ],
            objectives=self._build_objectives_from_map(),
            time_limit_ticks=36000,  # 20 minutes at 30 UPS
            force_morale_threshold=10,
        )
        self._game_result = None

        self._event_bus.subscribe(UnitAttacked, self._on_unit_attacked_for_stats)

    def _build_objectives_from_map(self) -> list:
        """Build objective list from the game map's victory locations."""
        from pycc2.domain.systems.victory_conditions import Objective

        objectives = []
        # Try to get objectives from the combat_director's game_map
        if self._combat_director is not None:
            game_map = getattr(self._combat_director, "_game_map", None)
            if game_map is None:
                game_map = getattr(self._combat_director, "game_map", None)
            if game_map is not None and hasattr(game_map, "objectives"):
                for obj in game_map.objectives:
                    pos = getattr(obj, "position", None) or getattr(obj, "tile_coord", None)
                    if pos is not None:
                        x = getattr(pos, "x", pos[0]) if not isinstance(pos, (int, float)) else pos
                        y = getattr(pos, "y", pos[1]) if not isinstance(pos, (int, float)) else 0
                        objectives.append(
                            Objective(
                                id=getattr(obj, "id", f"vl_{x}_{y}"),
                                name=getattr(obj, "name", "Victory Location"),
                                position=(int(x), int(y)),
                                radius=getattr(obj, "radius", 3),
                                points=getattr(obj, "points", 100),
                            )
                        )
        # Fallback: if no map objectives, create a center objective
        if not objectives:
            objectives.append(
                Objective(
                    id="vl_center",
                    name="Center Victory Location",
                    position=(15, 15),
                    radius=3,
                    points=100,
                )
            )
        return objectives

    def _on_unit_attacked_for_stats(self, data: dict) -> None:
        if self._combat_director is not None and self._battle_stats is not None:
            units: list[Unit] = getattr(self._combat_director, "_units", [])
            self._combat_director.record_stats(data, units, self._battle_stats)

    def evaluate(self, units: list[Unit], tick: int) -> tuple | None:
        """Evaluate victory conditions. Returns (result, reason) tuple if game over, else None."""
        if not self._victory_evaluator or not self._battle_stats:
            return None

        self._battle_stats.ticks_elapsed = tick
        # Prevent early defeat - wait at least 20 seconds (600 ticks) for battle to develop
        if tick % 30 == 0 and tick >= 600:
            result, reason = self._victory_evaluator.evaluate(units, tick, self._battle_stats)
            if result.name != "ONGOING":
                self._game_result = result
                self._game_over_tick = tick
                self._victory_detected = True
                self._victory_time = _time.monotonic()
                self._show_post_battle = True
                return (result, reason)
        return None

    def update(self) -> None:
        """Check if post-battle delay has elapsed and auto-show post-battle screen."""
        if self._victory_detected and not self._show_post_battle:
            elapsed = _time.monotonic() - self._victory_time
            if elapsed >= self._post_battle_delay:
                self._show_post_battle = True

    def reset(self) -> None:
        self._game_result = None
        self._game_over_tick = 0
        self._show_post_battle = False
        self._victory_detected = False
        self._victory_time = 0.0

    @property
    def game_result(self):
        return self._game_result

    @property
    def show_post_battle(self) -> bool:
        return self._show_post_battle

    @property
    def battle_stats(self):
        return self._battle_stats
