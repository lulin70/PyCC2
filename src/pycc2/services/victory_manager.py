from __future__ import annotations

import logging
import time as _time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.systems.victory_conditions import BattleStats, GameResult
    from pycc2.services.event_bus import EventBus

logger = logging.getLogger(__name__)


@dataclass
class VictoryManager:
    """Manages victory condition evaluation, battle stats, and game-over state."""

    _victory_evaluator: object | None = field(init=False, default=None)
    _battle_stats: BattleStats | None = field(init=False, default=None)
    _game_result: GameResult | None = field(init=False, default=None)
    _game_over_tick: int = field(init=False, default=0)
    _show_post_battle: bool = field(init=False, default=False)
    _event_bus: EventBus | None = field(init=False, default=None)
    _combat_director: object | None = field(init=False, default=None)

    def initialize(self, event_bus: EventBus, combat_director: object | None = None) -> None:
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
                VictoryConditionType.ELIMINATE_ENEMY_COMMANDER,
                VictoryConditionType.ELIMINATE_ALL_ENEMIES,
                VictoryConditionType.MORALE_COLLAPSE,
            ],
            time_limit_ticks=0,
            morale_threshold=10,
        )
        self._game_result = None

        self._event_bus.subscribe(UnitAttacked, self._on_unit_attacked_for_stats)

    def _on_unit_attacked_for_stats(self, data: dict) -> None:
        if self._combat_director is not None:
            from pycc2.domain.entities.unit import Unit

            units: list[Unit] = getattr(self._combat_director, "_units", [])
            self._combat_director.record_stats(data, units, self._battle_stats)

    def evaluate(self, units: list[Unit], tick: int) -> tuple | None:
        """Evaluate victory conditions. Returns (result, reason) tuple if game over, else None."""
        if not self._victory_evaluator or not self._battle_stats:
            return None

        self._battle_stats.ticks_elapsed = tick
        # Prevent early defeat - wait at least 5 seconds (300 ticks)
        if tick % 30 == 0 and tick >= 300:
            result, reason = self._victory_evaluator.evaluate(
                units, tick, self._battle_stats
            )
            if result.name != "ONGOING":
                self._game_result = result
                self._game_over_tick = tick
                self._show_post_battle = True
                return (result, reason)
        return None

    def reset(self) -> None:
        self._game_result = None
        self._game_over_tick = 0
        self._show_post_battle = False

    @property
    def game_result(self):
        return self._game_result

    @property
    def show_post_battle(self) -> bool:
        return self._show_post_battle

    @property
    def battle_stats(self):
        return self._battle_stats
