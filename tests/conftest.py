"""
PyCC2 Test Configuration - Headless Pygame Support

Provides fixtures that enable pygame-based tests to run in headless
environments (CI, Docker, etc.) by using SDL dummy drivers and
virtual font/rendering layers.
"""

from __future__ import annotations

import os

import pytest

# Set SDL dummy drivers BEFORE any pygame import.
# This must happen at module level so that even transitive imports
# of pygame see the environment variables first.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture(scope="session")
def pygame_display():
    """Initialize pygame with dummy video driver for the entire test session.

    Uses SDL_VIDEODRIVER=dummy so no real display is needed.
    The display is created once per session and quit at session end.
    """
    import pygame

    pygame.init()
    try:
        screen = pygame.display.set_mode((800, 600))
    except Exception:
        # Some environments may still fail; provide a fallback surface
        screen = pygame.Surface((800, 600), pygame.SRCALPHA)
    yield screen
    pygame.quit()


@pytest.fixture()
def mock_font(pygame_display):
    """Return a usable pygame Font object even in headless mode.

    Tries pygame.font.SysFont first; falls back to the default font
    (None) which is always available because pygame bundles it.
    """
    import pygame

    pygame.font.init()
    try:
        font = pygame.font.SysFont("arial", 16)
        # Verify the font actually works by rendering a test string
        font.render("test", True, (255, 255, 255))
    except Exception:
        # Fallback: pygame's built-in default font always works
        font = pygame.font.Font(None, 16)
    return font


@pytest.fixture()
def mock_small_font(pygame_display):
    """Return a small (12pt) font for tests that need a secondary font."""
    import pygame

    pygame.font.init()
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
        font.render("x", True, (255, 255, 255))
        del surf, font
        return True
    except Exception:
        return False
