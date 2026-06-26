import os

import numpy as np
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import (
    Faction,
    Unit,
    UnitType,
)
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
from pycc2.presentation.rendering.window_config import WindowManager


def _can_create_display() -> bool:
    """Check if pygame can create a scaled/double-buffered display.

    WindowManager.initialize() uses SCALED | RESIZABLE | DOUBLEBUF + vsync=1
    which fails in CI's SDL dummy driver even though basic set_mode() succeeds.
    In headless mode we test with vsync=0 (the configuration the test uses).
    """
    try:
        if not pygame.get_init():
            pygame.init()
        flags = pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF
        # Headless dummy driver cannot use vsync=1; test with vsync=0 which
        # is what the test uses in headless mode.
        vsync = 0 if os.environ.get("SDL_VIDEODRIVER") == "dummy" else 1
        surf = pygame.display.set_mode((320, 240), flags, vsync=vsync)  # noqa: F841
        pygame.display.quit()
        return True
    except Exception:
        return False


def _make_unit(unit_id: str = "u1") -> Unit:
    return Unit(
        id=unit_id,
        name="TestUnit",
        faction=Faction.ALLIES,
        unit_type=UnitType.INFANTRY_SQUAD,
        health=HealthComponent(hp=100, max_hp=100),
        morale=MoraleComponent(value=80),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(8, 8)),
        vision=VisionComponent(range_tiles=5),
    )


@pytest.fixture(autouse=True)
def setup_pygame():
    if not pygame.get_init():
        pygame.init()
    yield
    # Don't quit — conftest _pygame_recovery handles cleanup


@pytest.mark.skipif(
    not _can_create_display(), reason="Requires display renderer (unavailable in CI)"
)
class TestVisualSmoke:
    def test_full_render_pipeline_no_crash(self):
        grid = np.zeros((16, 16), dtype=np.int8)
        game_map = GameMap(
            id="smoke_test",
            name="Smoke Test Map",
            width=16,
            height=16,
            tile_grid=grid,
        )
        units = [_make_unit("unit_001")]
        wm = WindowManager()
        # Headless (SDL dummy driver) cannot use vsync=1 (raises
        # "failed to create renderer"); use vsync=0 in headless mode.
        if os.environ.get("SDL_VIDEODRIVER") == "dummy":
            screen = pygame.display.set_mode(
                (wm.display_info.base_width, wm.display_info.base_height),
                pygame.SCALED | pygame.RESIZABLE | pygame.DOUBLEBUF,
                vsync=0,
            )
        else:
            screen = wm.initialize()
        camera = Camera(position=Vec2(256.0, 256.0))
        renderer = EnhancedRenderer()
        renderer.initialize(screen)
        renderer.render(
            game_map,
            units,
            camera,
            alpha=1.0,
            selected_unit_ids={"unit_001"},
            debug_mode=False,
        )
        wm.shutdown()
        renderer.shutdown()
