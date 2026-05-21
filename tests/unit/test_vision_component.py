"""
Unit tests for VisionComponent
"""

from __future__ import annotations

import math

from pycc2.domain.components.vision_component import VisionComponent


class TestVisionComponentConstruction:
    def test_default_construction(self):
        vc = VisionComponent()
        assert vc.range_tiles == 6
        assert vc.angle_rad == math.pi
        assert vc.last_update_tick == 0
        assert len(vc.visible_tiles) == 0

    def test_custom_range(self):
        vc = VisionComponent(range_tiles=10)
        assert vc.range_tiles == 10

    def test_custom_angle(self):
        vc = VisionComponent(angle_rad=math.pi / 2)
        assert vc.angle_rad == math.pi / 2


class TestVisionComponentNeedsUpdate:
    def test_needs_update_on_first_tick(self):
        vc = VisionComponent()
        assert vc.needs_update(0) is True

    def test_needs_update_within_interval(self):
        vc = VisionComponent()
        vc.mark_updated(5)
        assert vc.needs_update(6) is False
        assert vc.needs_update(9) is False

    def test_needs_update_after_interval(self):
        vc = VisionComponent()
        vc.mark_updated(5)
        assert vc.needs_update(10) is True

    def test_custom_interval(self):
        vc = VisionComponent()
        vc.mark_updated(0)
        assert vc.needs_update(2, interval=3) is False
        assert vc.needs_update(3, interval=3) is True


class TestVisionComponentMarkUpdated:
    def test_mark_updated_changes_tick(self):
        vc = VisionComponent()
        vc.mark_updated(42)
        assert vc.last_update_tick == 42

    def test_mark_updated_prevents_update(self):
        vc = VisionComponent()
        vc.mark_updated(100)
        assert vc.needs_update(101) is False
        assert vc.needs_update(104) is False
        assert vc.needs_update(105) is True


class TestVisionComponentCanSeeTile:
    def test_can_see_visible_tile(self):
        vc = VisionComponent()
        vc.visible_tiles.add((5, 3))
        assert vc.can_see_tile(5, 3) is True

    def test_cannot_see_invisible_tile(self):
        vc = VisionComponent()
        assert vc.can_see_tile(10, 10) is False

    def test_can_see_multiple_tiles(self):
        vc = VisionComponent()
        tiles = {(1, 1), (2, 2), (3, 3)}
        vc.visible_tiles.update(tiles)
        for tile in tiles:
            assert vc.can_see_tile(*tile) is True


class TestVisionComponentRevealTiles:
    def test_reveal_new_tiles(self):
        vc = VisionComponent()
        new_tiles = {(1, 1), (2, 2), (3, 3)}
        revealed = vc.reveal_tiles(new_tiles)
        assert revealed == new_tiles
        assert len(vc.visible_tiles) == 3

    def test_reveal_partial_new(self):
        vc = VisionComponent()
        vc.visible_tiles.add((1, 1))
        new_tiles = {(1, 1), (2, 2), (3, 3)}
        revealed = vc.reveal_tiles(new_tiles)
        assert revealed == {(2, 2), (3, 3)}

    def test_reveal_empty_set(self):
        vc = VisionComponent()
        revealed = vc.reveal_tiles(set())
        assert revealed == set()


class TestVisionComponentClearVision:
    def test_clear_vision_removes_all(self):
        vc = VisionComponent()
        vc.visible_tiles = {(1, 1), (2, 2), (3, 3)}
        vc.clear_vision()
        assert len(vc.visible_tiles) == 0

    def test_clear_vision_can_see_becomes_false(self):
        vc = VisionComponent()
        vc.visible_tiles.add((5, 5))
        vc.clear_vision()
        assert vc.can_see_tile(5, 5) is False
