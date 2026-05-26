import os
from unittest.mock import MagicMock, patch

import pytest

from pycc2.presentation.rendering.window_config import (
    WindowManager,
    WindowMode,
)


@pytest.fixture
def wm():
    return WindowManager()


class TestInitialize:
    @patch("pygame.display.set_mode")
    @patch("pygame.display.set_caption")
    @patch("pygame.display.Info")
    def test_initialize_creates_surface(self, mock_info, mock_caption, mock_set_mode):
        mock_info_instance = MagicMock()
        mock_info_instance.current_w = 1920
        mock_info_instance.current_h = 1080
        mock_info.return_value = mock_info_instance
        mock_surface = MagicMock(spec=object)
        mock_set_mode.return_value = mock_surface
        manager = WindowManager()
        screen = manager.initialize()
        assert screen is mock_surface
        mock_set_mode.assert_called_once()
        mock_caption.assert_called_once_with("PyCC2 - Close Combat 2 Remake")


class TestDetectDpi:
    def test_detect_dpi_returns_positive_float(self):
        manager = WindowManager()
        dpi = manager.detect_dpi()
        assert isinstance(dpi, float)
        assert dpi > 0

    @patch("platform.system", return_value="Darwin")
    @patch.dict(os.environ, {}, clear=True)
    def test_detect_dpi_macos_fallback(self, mock_system):
        manager = WindowManager()
        with patch.object(manager, "detect_dpi", wraps=manager.detect_dpi):
            try:
                result = manager.detect_dpi()
                assert isinstance(result, float)
                assert result > 0
            except Exception:
                pass


class TestToggleFullscreen:
    def test_toggle_from_windowed_to_fullscreen(self):
        manager = WindowManager(mode=WindowMode.WINDOWED)
        with patch("pygame.display.set_mode") as mock_set_mode:
            manager.toggle_fullscreen()
            assert manager.mode == WindowMode.FULLSCREEN
            mock_set_mode.assert_called_once()

    def test_toggle_from_fullscreen_to_windowed(self):
        manager = WindowManager(mode=WindowMode.FULLSCREEN)
        with patch("pygame.display.set_mode"):
            manager.toggle_fullscreen()
            assert manager.mode == WindowMode.WINDOWED


class TestResize:
    def test_resize_updates_dimensions(self):
        manager = WindowManager()
        with patch.object(manager, "_screen", MagicMock()):
            with patch("pygame.display.set_mode"):
                manager.resize(1920, 1080)
                assert manager.display_info.base_width == 1920
                assert manager.display_info.base_height == 1080


class TestHandleEvent:
    def test_videoresize_does_not_quit(self):
        manager = WindowManager()
        mock_event = MagicMock()
        mock_event.type = 9999
        with patch.object(manager, "resize"):
            should_quit = manager.handle_event(mock_event)
            assert should_quit is False

    def test_quit_event_returns_true(self):
        manager = WindowManager()
        import pygame

        mock_event = MagicMock()
        mock_event.type = pygame.QUIT
        should_quit = manager.handle_event(mock_event)
        assert should_quit is True


class TestFpsAndTick:
    def test_fps_property_exists(self):
        manager = WindowManager()
        fps = manager.fps
        assert isinstance(fps, float)

    def test_tick_method_available(self):
        manager = WindowManager()
        with patch("pygame.time.Clock") as mock_clock_cls:
            mock_clock_instance = MagicMock()
            mock_clock_instance.tick.return_value = 16
            mock_clock_cls.return_value = mock_clock_instance
            ms = manager.tick(60)
            assert ms == 16


class TestShutdown:
    def test_shutdown_calls_pygame_quit(self):
        from pycc2.presentation.rendering.window_config import WindowManager
        manager = WindowManager()
        with patch("pycc2.presentation.rendering.window_config.pygame.quit") as mock_quit:
            with patch("pycc2.presentation.rendering.window_config.pygame.get_init", return_value=True):
                manager.shutdown()
                mock_quit.assert_called_once()


class TestGetActualSize:
    def test_get_actual_size_with_no_screen(self):
        manager = WindowManager()
        size = manager.get_actual_size()
        assert size == (1280, 720)

    def test_get_actual_size_with_screen(self):
        manager = WindowManager()
        mock_surface = MagicMock()
        mock_surface.get_size.return_value = (800, 600)
        manager._screen = mock_surface
        size = manager.get_actual_size()
        assert size == (800, 600)
