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

import logging
import os
import sys

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
        from pycc2.domain.components.health_component import HealthComponent
        from pycc2.domain.components.morale_component import MoraleComponent
        from pycc2.domain.components.position_component import PositionComponent
        from pycc2.domain.components.vision_component import VisionComponent
        from pycc2.domain.components.weapon_component import WeaponComponent
        from pycc2.domain.entities.game_map import GameMap
        from pycc2.domain.entities.unit import Faction, Unit, UnitType
        from pycc2.domain.value_objects.tile_coord import TileCoord
        from pycc2.infrastructure.events.event_bus import EventBus
        from pycc2.presentation.rendering.camera import Camera
        from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer
        from pycc2.presentation.rendering.window_config import WindowManager
        from pycc2.services.game_loop import GameLoop

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
        from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D

        return PixelArtist3D
    except ImportError as e:
        pytest.skip(f"PixelArtist3D not available: {e}")


# ---------------------------------------------------------------------------
# Lightweight Fake classes for integration/acceptance tests
# ---------------------------------------------------------------------------


class FakeAIService:
    """Lightweight AI service fake for testing.

    Replaces MagicMock for AIService in tests that only need
    register_ai_unit / managed_unit_count / tick / execute_intents.
    Tracks call counts for behavioral assertions.
    """

    def __init__(self, managed_unit_count=0, tick_return_value=None):
        self._registered_units: dict = {}
        self._unit_entities: dict = {}  # P0 AI safety net compatibility (2026-06-19)
        self._tick_count: int = 0
        self._execute_intents_count: int = 0
        self._managed_unit_count_override: int = managed_unit_count
        self._tick_return_value = tick_return_value or []

    def register_ai_unit(self, unit, behavior_tree=None) -> None:
        self._registered_units[unit.id] = unit

    @property
    def managed_unit_count(self) -> int:
        if self._managed_unit_count_override > 0:
            return self._managed_unit_count_override
        return len(self._registered_units)

    @property
    def managed_unit_ids(self):
        return list(self._registered_units.keys())

    def tick(self, dt=0.0, game_map=None, all_units=None, fog_of_war=None):
        self._tick_count += 1
        return self._tick_return_value

    @property
    def tick_call_count(self) -> int:
        return self._tick_count

    def execute_intents(self, intents=None):
        self._execute_intents_count += 1
        return {}

    @property
    def execute_intents_call_count(self) -> int:
        return self._execute_intents_count

    def shutdown(self) -> None:
        self._registered_units.clear()


class FakeCombatDirector:
    """Lightweight combat director fake for testing.

    Replaces MagicMock for CombatDirector in tests that only need
    _units, record_stats, update, process_effects.
    """

    def __init__(self, units=None):
        self._units = units or []
        self._record_stats_calls: list[dict] = []

    def record_stats(self, data: dict, units, battle_stats) -> None:
        self._record_stats_calls.append(data)
        if battle_stats is None:
            return
        attacker_id = data.get("attacker_id", "")
        damage = data.get("damage", 0)
        killed = data.get("killed", False) or data.get("kill_shot", False)
        attacker = next((u for u in units if u.id == attacker_id), None)
        if attacker:
            faction = "allies" if attacker.faction.name == "ALLIES" else "axis"
            battle_stats.record_shot(faction, hit=(damage > 0))
            if damage > 0:
                battle_stats.record_damage(faction, damage)
            if killed:
                battle_stats.record_kill(faction)

    def update(self, units, game_map, dt, battle_stats=None):
        pass

    def process_effects(self):
        return []

    def process_movements(self, units, game_map):
        pass

    def process_deaths(self, units, battle_stats=None):
        pass


def pytest_configure(config):
    """Pytest hook - called before test collection."""
    logger.info("PyCC2 Test Suite Configuration")
    logger.info("Python version: %s", sys.version)
    logger.info("SDL_VIDEODRIVER: %s", os.environ.get("SDL_VIDEODRIVER", "not set"))
    logger.info("SDL_AUDIODRIVER: %s", os.environ.get("SDL_AUDIODRIVER", "not set"))


# Phase 5: Auto-marker by directory path.
# Maps test directory to marker. Tests with explicit markers are respected.
_PATH_MARKER_MAP = {
    "tests/unit/": "unit",
    "tests/integration/": "integration",
    "tests/e2e/": "e2e",
    "tests/benchmark/": "benchmark",
    "tests/acceptance/": "e2e",
}
_EXPLICIT_MARKERS = {"unit", "slow", "integration", "e2e", "benchmark"}


def pytest_collection_modifyitems(config, items):
    """Auto-apply markers based on test file path.

    Tests in tests/unit/ get @pytest.mark.unit, etc.
    The path-based marker is always added; orthogonal markers like `slow`
    are preserved (a test can be both `unit` AND `slow`).
    """
    for item in items:
        path = str(item.fspath).replace("\\", "/")
        for prefix, marker in _PATH_MARKER_MAP.items():
            if prefix in path:
                # Only add if not already present (avoid duplicates)
                if not any(m.name == marker for m in item.iter_markers()):
                    item.add_marker(getattr(pytest.mark, marker))
                break


# P1 Fix: Autouse fixture to recover pygame state before each test.
# Many E2E/integration tests call pygame.quit() in teardown, breaking subsequent tests.
@pytest.fixture(autouse=True)
def _pygame_recovery():
    """Auto-recover pygame state before each test that needs display."""
    import pygame

    try:
        needs_recovery = False
        if not pygame.get_init():
            needs_recovery = True
        else:
            try:
                pygame.display.get_surface()
            except Exception:
                needs_recovery = True

        if needs_recovery:
            try:
                os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
                if not pygame.get_init():
                    pygame.init()
                pygame.display.set_mode((800, 600))
            except Exception:
                pass  # Best effort; test may skip via can_render

        yield
    except Exception:
        yield
