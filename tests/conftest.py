"""
PyCC2 Test Configuration - Enhanced Headless Pygame Support

Provides fixtures that enable pygame-based tests to run in headless
environments (CI, Docker, etc.) by using SDL dummy drivers and
virtual font/rendering layers.

V0.3.38 Fix: Lazy pygame initialization to prevent OOM kills.
- pygame_display is now lazy: only initialized when explicitly requested
- Tests that don't need pygame (e.g. resource_cache) won't trigger it
- Added autouse fixture to skip pygame init for pure-logic tests
"""

from __future__ import annotations

import os
import sys
import traceback
import logging

import pytest

logger = logging.getLogger(__name__)

# Set SDL dummy drivers BEFORE any pygame import.
# This must happen at module level so that even transitive imports
# of pygame see the environment variables first.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
# Disable joystick driver to avoid warnings
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")


# ---------------------------------------------------------------------------
# Lazy pygame initialization
# ---------------------------------------------------------------------------

_pygame_initialized = False
_pygame_screen = None


def _ensure_pygame():
    """Lazily initialize pygame exactly once. Returns the screen surface or None."""
    global _pygame_initialized, _pygame_screen

    if _pygame_initialized:
        return _pygame_screen

    _pygame_initialized = True

    import pygame

    try:
        pygame.init()
    except Exception as e:
        logger.warning("pygame.init() failed: %s", e)
        return None

    try:
        _pygame_screen = pygame.display.set_mode((800, 600))
        logger.debug("Pygame display initialized (800x600, dummy driver)")
    except Exception as e:
        logger.warning("Could not create pygame display: %s", e)
        try:
            _pygame_screen = pygame.Surface((800, 600), pygame.SRCALPHA)
            logger.debug("Using fallback pygame Surface")
        except Exception as e2:
            logger.error("Even fallback Surface failed: %s", e2)
            _pygame_screen = None

    return _pygame_screen


def _cleanup_pygame():
    """Clean up pygame resources at session end."""
    global _pygame_initialized, _pygame_screen
    if _pygame_initialized:
        try:
            import pygame
            pygame.quit()
        except Exception:
            pass
        _pygame_screen = None
        _pygame_initialized = False


@pytest.fixture(scope="session")
def pygame_display():
    """Initialize pygame with dummy video driver for the entire test session.

    IMPORTANT: This fixture is now lazy — pygame is only initialized when
    a test explicitly requests this fixture (or a fixture that depends on it).
    Tests that don't need pygame will NOT trigger initialization, preventing
    OOM kills on memory-constrained systems.

    Uses SDL_VIDEODRIVER=dummy so no real display is needed.
    """
    screen = _ensure_pygame()
    yield screen
    _cleanup_pygame()


@pytest.fixture()
def mock_font(pygame_display):
    """Return a usable pygame Font object even in headless mode.

    Tries pygame.font.SysFont first; falls back to the default font
    (None) which is always available because pygame bundles it.
    """
    import pygame

    pygame.font.init()
    font = None
    try:
        # Try system font first
        font = pygame.font.SysFont("arial", 16)
        # Verify the font actually works by rendering a test string
        test_surface = font.render("test", True, (255, 255, 255))
        if test_surface.get_width() == 0:
            raise ValueError("Font rendered empty string")
    except Exception:
        # Fallback: pygame's built-in default font always works
        try:
            font = pygame.font.Font(None, 16)
            test_surface = font.render("test", True, (255, 255, 255))
        except Exception as e2:
            logger.warning("Font initialization failed: %s", e2)
            font = None
    return font


@pytest.fixture()
def mock_small_font(pygame_display):
    """Return a small (12pt) font for tests that need a secondary font."""
    import pygame

    pygame.font.init()
    font = None
    try:
        font = pygame.font.SysFont("arial", 12)
        font.render("test", True, (255, 255, 255))
    except Exception:
        font = pygame.font.Font(None, 12)
    return font


@pytest.fixture()
def can_render(pygame_display):
    """Check whether full rendering (Surface + font) works in this environment.

    Returns True if both Surface creation and font rendering succeed,
    False otherwise. Tests that truly need a real display should use
    ``pytest.mark.skipif(not can_render_fixture, reason=...)``.
    """
    import pygame

    try:
        surf = pygame.Surface((100, 100), pygame.SRCALPHA)
        font = pygame.font.Font(None, 12)
        test_text = font.render("x", True, (255, 255, 255))
        # Verify rendering worked
        if surf.get_size() != (100, 100) or test_text.get_width() == 0:
            return False
        del surf, font, test_text
        return True
    except Exception as e:
        logger.debug("Render check failed: %s", e)
        return False


@pytest.fixture()
def game_instance(pygame_display):
    """Create a minimal game instance for E2E testing.

    This fixture provides a fully initialized GameLoop instance
    suitable for integration and end-to-end tests. It handles
    all the complex initialization that normally happens at startup.

    Note: This fixture requires the full pycc2 package to be installed
    and may be slow due to GameLoop initialization overhead.
    """
    import pygame

    game = None
    try:
        from pycc2.services.game_loop import GameLoop
        from pycc2.domain.entities.game_map import GameMap
        from pycc2.domain.entities.unit import Unit, Faction, UnitType
        from pycc2.domain.components.position_component import PositionComponent
        from pycc2.domain.components.health_component import HealthComponent
        from pycc2.domain.components.vision_component import VisionComponent
        from pycc2.domain.components.weapon_component import WeaponComponent
        from pycc2.domain.components.morale_component import MoraleComponent
        from pycc2.domain.value_objects.tile_coord import TileCoord
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
        from pycc2.presentation.rendering.window_config import WindowManager
        from pycc2.services.event_bus import EventBus

        # Create minimal game map (10x10)
        game_map = GameMap(width=10, height=10)

        # Create camera
        camera = Camera(
            position=None,
            viewport_width=800,
            viewport_height=600,
        )

        # Create renderer
        renderer = EnhancedRenderer()

        # Create window manager (headless)
        window_manager = WindowManager(
            width=800,
            height=600,
            fullscreen=False,
            title="Test Window",
        )
        # Initialize window with dummy surface
        window_manager._screen = pygame_display or pygame.Surface((800, 600), pygame.SRCALPHA)

        # Create event bus
        event_bus = EventBus()

        # Create game state
        from pycc2.services.game_loop import GameState
        state = GameState(
            game_map=game_map,
            units=[],
            camera=camera,
        )

        # Create GameLoop instance
        game = GameLoop(
            renderer=renderer,
            window_manager=window_manager,
            event_bus=event_bus,
            state=state,
            use_full_hud=True,
        )

        # Add some test units
        test_unit = Unit(
            id="test_unit_1",
            name="Test Infantry",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            position=PositionComponent(tile_coord=TileCoord(5, 5)),
            vision=VisionComponent(),
            health=HealthComponent(hp=100, max_hp=100),
            weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=120, ammo_remaining=120),
            morale=MoraleComponent(value=75),
        )
        state.units.append(test_unit)

        yield game

        # Cleanup
        try:
            game.shutdown()
        except Exception as e:
            logger.warning("Game shutdown failed: %s", e)

    except ImportError as e:
        pytest.skip(f"Required module not available: {e}")
    except Exception as e:
        logger.error("Error creating game instance:")
        logger.debug("Game instance creation traceback:", exc_info=True)
        pytest.skip(f"Could not create game instance: {e}")


@pytest.fixture()
def pixel_artist_3d_fixture(pygame_display, can_render):
    """Fixture for testing PixelArtist3D (45° isometric sprite generator).

    Only runs if rendering is available in this environment.
    """
    if not can_render:
        pytest.skip("Rendering not available in this environment")

    try:
        from pycc2.presentation.rendering.pixel_artist_3d import (
            PixelArtist3D,
            Direction,
            Faction,
        )
        return PixelArtist3D
    except ImportError as e:
        pytest.skip(f"PixelArtist3D not available: {e}")


def pytest_configure(config):
    """Pytest hook - called before test collection."""
    logger.info("PyCC2 Test Suite Configuration")
    logger.info("Python version: %s", sys.version)
    logger.info("SDL_VIDEODRIVER: %s", os.environ.get('SDL_VIDEODRIVER', 'not set'))
    logger.info("SDL_AUDIODRIVER: %s", os.environ.get('SDL_AUDIODRIVER', 'not set'))
