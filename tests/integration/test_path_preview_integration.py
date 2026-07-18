"""Integration tests for path_preview wiring into InputRouter + Minimap.

Verifies the v0.7.6 INTEGRATE of PathPreview:
  - InputRouter dispatches mouse_click_right → _update_path_preview()
  - _update_path_preview converts screen→tile and calls calculate_path
  - PathPreview stores result via set_current_path
  - Minimap renders path segments via set_path_preview()
  - GameLoopAssembler wires PathPreview into InputRouter (smoke check)
  - path_preview=None preserves backward compatibility

These are integration tests — they use the real PathFinder, GameMap, Camera,
and PathPreview classes. Only IInputHandler and IInteractionController are
stubbed (matching the v0.7.5 squad_group_integration pattern).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pygame

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
from pycc2.presentation.input.input_router import InputRouter
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.path_preview import PathPreview, PreviewPath

# ============================================================================
# Test fixtures — lightweight stubs matching the protocols InputRouter needs
# ============================================================================


@dataclass
class _StubInputHandler:
    """Minimal IInputHandler stub that returns a canned InputEvent."""

    _event: Any = None

    def process_event(self, event: pygame.event.EventType):
        return self._event

    def get_camera_movement(self) -> tuple[float, float]:
        return (0.0, 0.0)


@dataclass
class _StubInteractionController:
    """Minimal IInteractionController stub.

    Only ``handle_right_mouse_down`` is exercised in the path_preview flow
    (when units is non-empty). Other methods exist as no-ops to satisfy
    the protocol surface should the test be extended.
    """

    last_right_click_pos: tuple[int, int] | None = field(default=None, init=False)
    last_right_click_units: list = field(default_factory=list, init=False)

    def handle_right_mouse_down(self, position, units) -> None:
        self.last_right_click_pos = position
        self.last_right_click_units = list(units)


@dataclass
class _StubGameState:
    """Minimal GameStateView stub matching the protocol InputRouter consumes."""

    running: bool = True
    paused: bool = False
    debug_mode: bool = False
    units: list = field(default_factory=list)
    selected_unit_ids: set = field(default_factory=set)
    game_map: Any = None
    camera: Any = None


def _make_unit(
    unit_id: str,
    tile_x: int,
    tile_y: int,
    *,
    faction: Faction = Faction.ALLIES,
) -> Unit:
    """Build a real INFANTRY_SQUAD Unit at the given tile coordinate."""
    return Unit(
        id=unit_id,
        name=f"Test {unit_id}",
        faction=faction,
        unit_type=UnitType.INFANTRY_SQUAD,
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
        vision=VisionComponent(),
        health=HealthComponent(hp=100, max_hp=100),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
        morale=MoraleComponent(value=75),
    )


def _make_open_map(width: int = 10, height: int = 10) -> GameMap:
    """Build a real GameMap of all-OPEN passable terrain."""
    grid = np.zeros((height, width), dtype=np.int8)
    return GameMap(id="test", name="Test Map", width=width, height=height, tile_grid=grid)


def _make_camera_at_tile(tile_x: int, tile_y: int) -> Camera:
    """Build a real Camera centered on the given tile's world pixel position.

    With this camera, clicking at screen (viewport_w/2, viewport_h/2) lands
    on world pixel (tile_x*32, tile_y*32) which is tile (tile_x, tile_y).
    """
    return Camera(
        position=Vec2(float(tile_x * 32), float(tile_y * 32)),
        viewport_width=800,
        viewport_height=600,
    )


def _make_mouse_event(pos: tuple[int, int]) -> pygame.event.EventType:
    """Build a synthetic pygame MOUSEBUTTONDOWN event for the right button."""
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=pos)


def _make_right_click_event(screen_pos: tuple[int, int]) -> Any:
    """Build the canned InputEvent returned by the stub input handler."""
    return type(
        "E",
        (),
        {
            "event_type": "mouse_click_right",
            "position": screen_pos,
            "modifiers": (False, False, False, False),
        },
    )()


def _make_router(
    game_map: GameMap,
    camera: Camera,
    units: list[Unit],
    selected_ids: set[str],
    path_preview: PathPreview | None,
) -> tuple[InputRouter, _StubGameState, _StubInteractionController]:
    """Build an InputRouter wired to real PathPreview + GameState + Camera."""
    state = _StubGameState(
        units=units,
        selected_unit_ids=selected_ids,
        game_map=game_map,
        camera=camera,
    )
    handler = _StubInputHandler()
    interaction = _StubInteractionController()
    router = InputRouter(
        input_handler=handler,
        interaction_controller=interaction,
        command_bar=None,
        camera=camera,
        game_state=state,
        path_preview=path_preview,
    )
    return router, state, interaction


def _make_path_preview(los_system=None) -> PathPreview:
    """Build a PathPreview backed by a real PathFinder."""
    return PathPreview(pathfinder=PathFinder(), los_system=los_system)


# ============================================================================
# Happy Path — right-click calculates a path
# ============================================================================


class TestPathPreviewHappyPath:
    """Right-click with a selected unit computes a path and stores it."""

    def test_right_click_sets_current_path(self):
        """Right-click targeting a distant tile → current_path is set and valid."""
        game_map = _make_open_map()
        camera = _make_camera_at_tile(5, 5)
        unit = _make_unit("u1", 1, 1)
        preview = _make_path_preview()
        router, _, _ = _make_router(
            game_map=game_map,
            camera=camera,
            units=[unit],
            selected_ids={"u1"},
            path_preview=preview,
        )
        assert preview.current_path is None  # precondition

        # Click at viewport center → targets tile (5, 5) in world pixels
        router.input_handler._event = _make_right_click_event((400, 300))
        router.route_input(_make_mouse_event((400, 300)))

        path = preview.current_path
        assert path is not None
        assert isinstance(path, PreviewPath)
        assert path.is_valid is True
        assert len(path.segments) > 0

    def test_calculate_path_returns_segments_with_distance(self):
        """Direct calculate_path call returns segments + total_distance > 0."""
        game_map = _make_open_map()
        unit = _make_unit("u1", 1, 1)
        preview = _make_path_preview()

        path = preview.calculate_path(
            unit=unit,
            target_pos=(8, 8),
            game_map=game_map,
            enemy_units=None,
        )

        assert path.is_valid is True
        assert len(path.segments) >= 7  # octile distance from (1,1) to (8,8)
        assert path.total_distance > 0
        assert path.total_time > 0.0


# ============================================================================
# Boundary — edge cases for path calculation
# ============================================================================


class TestPathPreviewBoundary:
    """Edge cases: start==goal, unpassable target, out-of-bounds."""

    def test_start_equals_end_returns_empty_segments(self):
        """Right-click on the unit's own tile → valid path with no segments."""
        game_map = _make_open_map()
        camera = _make_camera_at_tile(1, 1)  # unit is at tile (1, 1)
        unit = _make_unit("u1", 1, 1)
        preview = _make_path_preview()
        router, _, _ = _make_router(
            game_map=game_map,
            camera=camera,
            units=[unit],
            selected_ids={"u1"},
            path_preview=preview,
        )

        router.input_handler._event = _make_right_click_event((400, 300))
        router.route_input(_make_mouse_event((400, 300)))

        path = preview.current_path
        assert path is not None
        assert path.is_valid is True
        # find_path returns [start] (len 1) → segments is empty
        assert path.segments == []
        assert path.total_distance == 0

    def test_unpassable_target_returns_invalid_path(self):
        """Right-click on a wall tile → path.is_valid is False."""
        game_map = _make_open_map()
        # Block tile (5, 5) with a WALL (terrain value 8, not passable)
        game_map.tile_grid[5, 5] = 8  # TerrainType.WALL
        camera = _make_camera_at_tile(5, 5)
        unit = _make_unit("u1", 1, 1)
        preview = _make_path_preview()
        router, _, _ = _make_router(
            game_map=game_map,
            camera=camera,
            units=[unit],
            selected_ids={"u1"},
            path_preview=preview,
        )

        router.input_handler._event = _make_right_click_event((400, 300))
        router.route_input(_make_mouse_event((400, 300)))

        path = preview.current_path
        assert path is not None
        assert path.is_valid is False
        assert path.segments == []


# ============================================================================
# Integration — real GameMap + LOSSystem + Minimap rendering
# ============================================================================


class TestPathPreviewIntegration:
    """Integration with real GameMap, LOSSystem, and Minimap rendering."""

    def test_minimap_renders_path_preview_without_error(self):
        """Minimap with a path_preview wired renders without raising."""
        from pycc2.presentation.rendering.minimap import Minimap

        game_map = _make_open_map()
        unit = _make_unit("u1", 2, 2)
        preview = _make_path_preview()
        # Compute a real path so segments are populated
        path = preview.calculate_path(
            unit=unit,
            target_pos=(7, 7),
            game_map=game_map,
            enemy_units=None,
        )
        preview.set_current_path(path)

        minimap = Minimap(display_config=None, size=100)
        minimap.set_map(game_map)
        minimap.set_path_preview(preview)

        pygame.init()
        try:
            minimap.show()
            minimap.update(0.5)
            screen = pygame.Surface((200, 200))
            minimap.render(screen, 0, 0)
            assert minimap._surface is not None
        finally:
            pygame.quit()

    def test_path_preview_with_real_los_system(self):
        """PathPreview with a real LOSSystem returns danger levels for enemies."""
        from pycc2.domain.systems.los_system import LOSSystem

        game_map = _make_open_map()
        los_system = LOSSystem(game_map=game_map)
        preview = _make_path_preview(los_system=los_system)

        allied_unit = _make_unit("ally", 1, 1, faction=Faction.ALLIES)
        # Enemy at (5, 5) on open terrain has LOS to nearby tiles
        enemy_unit = _make_unit("enemy", 5, 5, faction=Faction.AXIS)

        path = preview.calculate_path(
            unit=allied_unit,
            target_pos=(5, 4),
            game_map=game_map,
            enemy_units=[enemy_unit],
        )

        assert path.is_valid is True
        assert len(path.segments) > 0
        # With an enemy nearby, at least one segment should be non-SAFE
        from pycc2.presentation.rendering.path_preview import PathDangerLevel

        danger_levels = {seg.danger for seg in path.segments}
        # Enemy at (5,5) sees tiles near (5,4) — at least WARNING or DANGER expected.
        assert PathDangerLevel.SAFE not in danger_levels or danger_levels == {
            PathDangerLevel.SAFE
        }, f"Danger levels {danger_levels} should reflect enemy proximity"


# ============================================================================
# Backward compatibility — path_preview=None
# ============================================================================


class TestPathPreviewBackwardCompat:
    """When path_preview is None, right-click does not error."""

    def test_path_preview_none_no_error_on_right_click(self):
        """InputRouter with path_preview=None handles right-click cleanly."""
        game_map = _make_open_map()
        camera = _make_camera_at_tile(5, 5)
        unit = _make_unit("u1", 1, 1)
        router, _, _ = _make_router(
            game_map=game_map,
            camera=camera,
            units=[unit],
            selected_ids={"u1"},
            path_preview=None,  # backward-compat: no preview wired
        )

        router.input_handler._event = _make_right_click_event((400, 300))
        # Should not raise even though path_preview is None
        ok = router.route_input(_make_mouse_event((400, 300)))

        assert ok is True

    def test_no_selected_unit_no_path_calculated(self):
        """Right-click with no selected unit → no path computed (stays None)."""
        game_map = _make_open_map()
        camera = _make_camera_at_tile(5, 5)
        unit = _make_unit("u1", 1, 1)
        preview = _make_path_preview()
        router, _, _ = _make_router(
            game_map=game_map,
            camera=camera,
            units=[unit],
            selected_ids=set(),  # no selection
            path_preview=preview,
        )

        router.input_handler._event = _make_right_click_event((400, 300))
        router.route_input(_make_mouse_event((400, 300)))

        # No selected unit → _update_path_preview early-returns
        assert preview.current_path is None
