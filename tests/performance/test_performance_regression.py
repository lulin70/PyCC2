"""Performance regression guards for CC2 tactical systems.

These tests use generous budgets. They catch large regressions
(for example an accidental O(n^2) loop), not small timing noise.
"""

from __future__ import annotations

import os
import time

import numpy as np

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pycc2.domain.entities.game_map import GameMap  # noqa: E402
from pycc2.domain.systems.combat_system import CombatSystem, SimpleCombatUnit  # noqa: E402
from pycc2.domain.systems.fog_of_war import FogOfWar  # noqa: E402
from pycc2.domain.systems.los_system import LOSSystem  # noqa: E402
from pycc2.domain.value_objects.tile_coord import TileCoord  # noqa: E402


def _open_map(width: int = 64, height: int = 64) -> GameMap:
    """Build an open map with no blocking terrain."""
    return GameMap(
        id="perf_open",
        name="perf_open",
        width=width,
        height=height,
        tile_grid=np.zeros((height, width), dtype=np.int8),
    )


def _combat_units(count: int) -> list[SimpleCombatUnit]:
    units = []
    for i in range(count):
        faction = "allied" if i % 2 == 0 else "axis"
        units.append(
            SimpleCombatUnit(
                id=f"u{i}",
                faction=faction,
                position_x=320.0 + (i % 10) * 40.0,
                position_y=320.0 + (i // 10) * 40.0,
                hp=100,
                max_hp=100,
                attack_damage=5,
                attack_range=300.0,
                attack_cooldown=1.0,
            )
        )
    return units


class TestCombatPerformance:
    def test_100_units_60_ticks_under_1s(self):
        system = CombatSystem()
        for unit in _combat_units(100):
            system.add_unit(unit)

        start = time.perf_counter()
        for _ in range(60):
            system.update(delta_time=0.016)
        elapsed = time.perf_counter() - start

        assert elapsed < 1.0, f"60 ticks with 100 units took {elapsed:.3f}s"


class TestLineOfSightPerformance:
    def test_500_los_checks_under_2s(self):
        game_map = _open_map()
        los = LOSSystem(game_map)
        coords = [TileCoord(i % 60, (i * 7) % 60) for i in range(25)]

        start = time.perf_counter()
        for a in coords:
            for b in coords:
                los.check_los(a, b)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"625 LOS checks took {elapsed:.3f}s"


class TestFogOfWarPerformance:
    def test_20_visibility_updates_under_3s(self):
        game_map = _open_map()
        fog = FogOfWar(game_map.width, game_map.height)

        start = time.perf_counter()
        for i in range(20):
            fog.update_visibility(
                observer_pos=TileCoord(10 + i, 10 + i),
                vision_range=8,
                vision_angle=90.0,
                facing_direction=0.0,
                game_map=game_map,
                current_tick=i,
            )
        elapsed = time.perf_counter() - start

        assert elapsed < 3.0, f"20 fog updates took {elapsed:.3f}s"
        assert any(
            fog.is_visible(TileCoord(x, y))
            for x in range(game_map.width)
            for y in range(game_map.height)
        ), "At least one tile must be visible after the updates"
