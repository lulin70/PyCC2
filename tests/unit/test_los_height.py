"""Unit tests for the terrain height / elevation data pipeline.

Covers the three defects fixed in the height-system data pipeline:
  1. ``GameMap.from_json`` now reads ``tiles_enhanced[].height`` into
     ``height_grid`` (and ``elevation`` into ``elevation_grid`` when present).
  2. ``LOSSystem._get_elevation`` reads terrain altitude from
     ``GameMap.elevation_grid`` instead of the absent ``enhanced["elevation"]``
     dict field.
  3. LOS is blocked when the height difference along the ray exceeds
     ``LOSSystem.HEIGHT_BLOCK_THRESHOLD`` (1.5).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.systems.los_system import LosStatus, LOSSystem
from pycc2.domain.value_objects.tile_coord import TileCoord


def _write_map_json(
    tmp_path: Path,
    tiles: list,
    tiles_enhanced: list,
    width: int,
    height: int,
) -> Path:
    """Write a minimal scenario JSON file and return its path."""
    data = {
        "id": "height_test",
        "name": "Height Test",
        "width": width,
        "height": height,
        "tiles": tiles,
        "tiles_enhanced": tiles_enhanced,
        "objectives": [],
        "spawn_points": [],
    }
    path = tmp_path / "height_test.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.unit
class TestLosHeightPipeline:
    """Validate the from_json → height_grid → LOS data pipeline."""

    def test_from_json_reads_tiles_enhanced_height_into_height_grid(
        self,
        tmp_path: Path,
    ) -> None:
        """tiles_enhanced.height must populate height_grid (building floors).

        Also verifies backward compatibility: when tiles_enhanced has no
        ``elevation`` field, elevation_grid stays all-zero.
        """
        # 3x2 integer-terrain grid (mimics night_map.json / tutorial.json).
        tiles = [
            [0, 0, 0],
            [0, 0, 0],
        ]
        tiles_enhanced = [
            [
                {"base_terrain": 0, "height": 1, "variation": 0, "decorations": []},
                {"base_terrain": 0, "height": 3, "variation": 0, "decorations": []},
                {"base_terrain": 0, "height": 0, "variation": 0, "decorations": []},
            ],
            [
                {"base_terrain": 0, "height": 2, "variation": 0, "decorations": []},
                {"base_terrain": 0, "height": 0, "variation": 0, "decorations": []},
                {"base_terrain": 0, "height": 1, "variation": 0, "decorations": []},
            ],
        ]
        path = _write_map_json(tmp_path, tiles, tiles_enhanced, width=3, height=2)

        m = GameMap.from_json(path)

        # height_grid must mirror tiles_enhanced.height exactly.
        assert m.height_grid is not None
        assert m.height_grid.shape == (2, 3)
        assert [int(v) for v in m.height_grid[0]] == [1, 3, 0]
        assert [int(v) for v in m.height_grid[1]] == [2, 0, 1]

        # Backward compat: no elevation field → elevation_grid stays zero.
        assert m.elevation_grid is not None
        assert int(m.elevation_grid.sum()) == 0

    def test_los_reads_elevation_from_elevation_grid(self) -> None:
        """LOSSystem._get_elevation must read from GameMap.elevation_grid."""
        grid = np.zeros((5, 5), dtype=np.int8)  # all OPEN terrain
        m = GameMap(id="t", name="t", width=5, height=5, tile_grid=grid)

        # Place a hill of elevation 4 at (2, 0); leave everything else flat.
        m.set_elevation(TileCoord(2, 0), 4.0)

        los = LOSSystem(m)

        assert los._get_elevation(TileCoord(2, 0)) == 4.0
        assert los._get_elevation(TileCoord(0, 0)) == 0.0
        # Out-of-bounds defensively returns 0.0 (no IndexError leak).
        assert los._get_elevation(TileCoord(99, 99)) == 0.0

    def test_los_blocked_when_height_diff_exceeds_threshold(self) -> None:
        """A tall obstacle between observer and target must block LOS by height.

        Observer at (0, 0) on flat ground; a 3-floor building at (3, 0) rises
        ``height_diff = 3 > 1.5`` → LosStatus.BLOCKED_HEIGHT.
        """
        grid = np.zeros((1, 7), dtype=np.int8)  # 7x1 row, all OPEN terrain
        m = GameMap(id="t", name="t", width=7, height=1, tile_grid=grid)
        m.set_building_height(TileCoord(3, 0), 3)

        los = LOSSystem(m)
        can_see, result = los.check_los(TileCoord(0, 0), TileCoord(6, 0))

        assert can_see is False
        assert result.status == LosStatus.BLOCKED_HEIGHT
        assert result.blocking_coord == TileCoord(3, 0)
