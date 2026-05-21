from __future__ import annotations

import math

import numpy as np

from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.systems.fog_of_war import FogOfWar, TileVisibility
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord


def _make_map(width: int = 20, height: int = 20, fill: TerrainType = TerrainType.OPEN) -> GameMap:
    grid = np.full((height, width), fill.value, dtype=np.int8)
    return GameMap(id="test", name="Test", width=width, height=height, tile_grid=grid)


def _make_fow(width: int = 20, height: int = 20) -> FogOfWar:
    return FogOfWar(map_width=width, map_height=height)


class TestFowBasic:
    def test_init_all_hidden(self):
        fow = _make_fow(10, 10)
        for y in range(10):
            for x in range(10):
                assert fow.get_visibility(TileCoord(x, y)) == TileVisibility.HIDDEN

    def test_update_observer_visible(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        obs = TileCoord(5, 5)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=6,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
            current_tick=0,
        )
        assert fow.is_visible(obs)

    def test_out_of_range_stays_hidden(self):
        fow = _make_fow(30, 30)
        m = _make_map(30, 30)
        obs = TileCoord(5, 5)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=3,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        far = TileCoord(25, 25)
        assert fow.is_hidden(far)
        assert not fow.is_visible(far)
        assert not fow.is_explored(far)

    def test_visibility_consistency(self):
        fow = _make_fow(15, 15)
        m = _make_map(15, 15)
        obs = TileCoord(7, 7)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=5,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        for y in range(15):
            for x in range(15):
                c = TileCoord(x, y)
                v = fow.get_visibility(c)
                if v == TileVisibility.VISIBLE:
                    assert fow.is_visible(c)
                    assert not fow.is_hidden(c)
                elif v == TileVisibility.EXPLORED:
                    assert fow.is_explored(c)
                    assert not fow.is_visible(c)
                    assert not fow.is_hidden(c)
                else:
                    assert fow.is_hidden(c)
                    assert not fow.is_visible(c)
                    assert not fow.is_explored(c)

    def test_reset_all_hidden(self):
        fow = _make_fow(10, 10)
        m = _make_map(10, 10)
        fow.update_visibility(
            observer_pos=TileCoord(5, 5),
            vision_range=6,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        fow.reset()
        for y in range(10):
            for x in range(10):
                assert fow.get_visibility(TileCoord(x, y)) == TileVisibility.HIDDEN

    def test_clear_current_visibility(self):
        fow = _make_fow(15, 15)
        m = _make_map(15, 15)
        obs = TileCoord(7, 7)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=5,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        cleared = fow.clear_current_visibility()
        assert len(cleared) > 0
        for c in cleared:
            assert fow.is_explored(c)
            assert not fow.is_visible(c)


class TestFowRay:
    def test_36_rays_full_circle(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        obs = TileCoord(10, 10)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=6,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        visible = fow.get_visible_tiles()
        assert len(visible) > 20

    def test_ray_blocked_by_wall(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        m.set_terrain(TileCoord(10, 8), TerrainType.WALL)
        obs = TileCoord(10, 10)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=6,
            vision_angle=math.pi,
            facing_direction=math.pi / 2,
            game_map=m,
        )
        behind_wall = TileCoord(10, 6)
        if m.is_within_bounds(behind_wall):
            assert not fow.is_visible(behind_wall)

    def test_ray_blocked_by_woods(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        m.set_terrain(TileCoord(12, 10), TerrainType.WOODS)
        obs = TileCoord(10, 10)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=6,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        behind_woods = TileCoord(14, 10)
        if m.is_within_bounds(behind_woods):
            assert not fow.is_visible(behind_woods)

    def test_open_terrain_no_block(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20, fill=TerrainType.OPEN)
        obs = TileCoord(5, 5)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=8,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        far_visible = TileCoord(13, 5)
        if m.is_within_bounds(far_visible):
            assert fow.is_visible(far_visible)

    def test_zero_range_only_origin(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        obs = TileCoord(10, 10)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=0,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        visible = fow.get_visible_tiles()
        assert visible == {obs}


class TestFowLos:
    def test_wall_blocks_tile_behind(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        m.set_terrain(TileCoord(11, 10), TerrainType.WALL)
        obs = TileCoord(10, 10)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=6,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        behind = TileCoord(12, 10)
        assert not fow.is_visible(behind)

    def test_woods_blocks_tile_behind(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        m.set_terrain(TileCoord(11, 10), TerrainType.WOODS)
        obs = TileCoord(10, 10)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=6,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        behind = TileCoord(12, 10)
        assert not fow.is_visible(behind)

    def test_open_allows_tile_behind(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        obs = TileCoord(3, 10)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=10,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        target = TileCoord(13, 10)
        assert fow.is_visible(target)

    def test_adjacent_tile_even_if_blocking(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        m.set_terrain(TileCoord(11, 10), TerrainType.BUILDING_SOLID)
        obs = TileCoord(10, 10)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=6,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        adjacent = TileCoord(11, 10)
        assert fow.is_visible(adjacent)

    def test_concealment_does_not_block_los(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        m.set_terrain(TileCoord(11, 10), TerrainType.ROUGH)
        obs = TileCoord(10, 10)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=6,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
        )
        behind = TileCoord(12, 10)
        assert fow.is_visible(behind)


class TestFowPersist:
    def test_visible_to_explored_on_next_update(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        obs1 = TileCoord(5, 5)
        fow.update_visibility(
            observer_pos=obs1,
            vision_range=5,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
            current_tick=0,
        )
        first_visible = set(fow.get_visible_tiles())
        obs2 = TileCoord(15, 15)
        fow.update_visibility(
            observer_pos=obs2,
            vision_range=5,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
            current_tick=5,
        )
        for c in first_visible:
            if not fow.is_visible(c):
                assert fow.is_explored(c)

    def test_explored_never_reverts_to_hidden(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        obs = TileCoord(5, 5)
        fow.update_visibility(
            observer_pos=obs,
            vision_range=5,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
            current_tick=0,
        )
        explored = {
            c for c in [TileCoord(x, y) for y in range(20) for x in range(20)] if fow.is_explored(c)
        }
        fow.update_visibility(
            observer_pos=TileCoord(18, 18),
            vision_range=2,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
            current_tick=10,
        )
        for c in explored:
            assert not fow.is_hidden(c)

    def test_move_observer_old_explored_new_visible(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        old_pos = TileCoord(5, 5)
        fow.update_visibility(
            observer_pos=old_pos,
            vision_range=4,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
            current_tick=0,
        )
        assert fow.is_visible(old_pos)
        new_pos = TileCoord(15, 15)
        fow.update_visibility(
            observer_pos=new_pos,
            vision_range=4,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
            current_tick=5,
        )
        assert fow.is_explored(old_pos)
        assert not fow.is_visible(old_pos)
        assert fow.is_visible(new_pos)

    def test_newly_revealed_only_hidden_to_visible(self):
        fow = _make_fow(20, 20)
        m = _make_map(20, 20)
        obs = TileCoord(10, 10)
        revealed_first = fow.update_visibility(
            observer_pos=obs,
            vision_range=5,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
            current_tick=0,
        )
        revealed_second = fow.update_visibility(
            observer_pos=obs,
            vision_range=5,
            vision_angle=math.pi,
            facing_direction=0,
            game_map=m,
            current_tick=5,
        )
        for c in revealed_second:
            assert c not in revealed_first
