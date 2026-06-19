from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pygame
import pytest

from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.input.handler import PygameInputHandler
from pycc2.presentation.rendering.camera import Camera
from pycc2.presentation.rendering.window_config import WindowManager


@pytest.fixture
def camera():
    return Camera(position=Vec2(256.0, 256.0), viewport_width=1280, viewport_height=720)


@pytest.fixture
def window_manager():
    wm = Mock(spec=WindowManager)
    wm.get_actual_size.return_value = (1280, 720)
    return wm


@pytest.fixture
def input_handler(camera, window_manager):
    return PygameInputHandler(camera=camera, window_manager=window_manager)


class TestMouseEvents:
    def test_mousemotion_returns_mouse_move_event(self, input_handler):
        event = MagicMock()
        event.type = pygame.MOUSEMOTION
        event.pos = (100, 200)
        result = input_handler.process_event(event)
        assert result is not None
        assert result.event_type == "mouse_move"
        assert result.position == (100.0, 200.0)

    def test_mousebutton_left_returns_click_left(self, input_handler):
        event = MagicMock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 1
        event.pos = (150, 250)
        with patch("pygame.key.get_mods", return_value=0):
            result = input_handler.process_event(event)
        assert result is not None
        assert result.event_type == "mouse_click_left"
        assert result.button == 1

    def test_mousebutton_right_returns_click_right(self, input_handler):
        event = MagicMock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 3
        event.pos = (200, 300)
        with patch("pygame.key.get_mods", return_value=0):
            result = input_handler.process_event(event)
        assert result is not None
        assert result.event_type == "mouse_click_right"
        assert result.button == 3

    def test_mousebutton_4_zoom_in_increases_zoom(self, input_handler):
        """Scroll wheel zoom was disabled in favor of HUD-only zoom controls (2026-06-19)."""
        initial_zoom = input_handler.camera.zoom
        event = MagicMock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 4
        event.pos = (640, 360)
        result = input_handler.process_event(event)
        assert result is None
        # Zoom should NOT change — scroll wheel zoom disabled
        assert input_handler.camera.zoom == initial_zoom

    def test_mousebutton_5_zoom_out_decreases_zoom(self, input_handler):
        """Scroll wheel zoom was disabled in favor of HUD-only zoom controls (2026-06-19)."""
        input_handler.camera.zoom = 2.0
        event = MagicMock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 5
        event.pos = (640, 360)
        result = input_handler.process_event(event)
        assert result is None
        # Zoom should NOT change — scroll wheel zoom disabled
        assert input_handler.camera.zoom == 2.0


class TestKeyboardEvents:
    def test_keydown_wasd_returns_nonzero_movement(self, input_handler):
        pygame.init()
        try:
            with patch("pygame.key.get_pressed") as mock_pressed:

                class KeyList(list):
                    def __getitem__(self, index):
                        try:
                            return super().__getitem__(index)
                        except IndexError:
                            return False

                keys = KeyList([False] * 512)
                keys[pygame.K_w] = True
                mock_pressed.return_value = keys
                dx, dy = input_handler.get_camera_movement()
                assert dy < 0
        finally:
            pygame.quit()

    def test_keydown_f11_toggles_fullscreen(self, input_handler):
        event = MagicMock()
        event.type = pygame.KEYDOWN
        event.key = pygame.K_F11
        result = input_handler.process_event(event)
        assert result is None
        input_handler.window_manager.toggle_fullscreen.assert_called_once()

    def test_keydown_escape_returns_quit_event(self, input_handler):
        event = MagicMock()
        event.type = pygame.KEYDOWN
        event.key = pygame.K_ESCAPE
        with patch("pygame.key.get_mods", return_value=0):
            result = input_handler.process_event(event)
        assert result is not None
        assert result.event_type == "key_down"
        assert result.key == pygame.K_ESCAPE


class TestSystemEvents:
    def test_videoresize_calls_resize(self, input_handler):
        event = MagicMock()
        event.type = pygame.VIDEORESIZE
        event.w = 1920
        event.h = 1080
        result = input_handler.process_event(event)
        assert result is None
        input_handler.window_manager.resize.assert_called_once_with(1920, 1080)

    def test_quit_event_returns_quit(self, input_handler):
        event = MagicMock()
        event.type = pygame.QUIT
        result = input_handler.process_event(event)
        assert result is not None
        assert result.event_type == "quit"


class TestEdgeScroll:
    def test_edge_scroll_left_edge_returns_negative_dx(self, input_handler):
        class KeyList(list):
            def __getitem__(self, index):
                try:
                    return super().__getitem__(index)
                except IndexError:
                    return False

        with patch("pygame.mouse.get_pos", return_value=(5, 400)):
            with patch("pygame.key.get_pressed", return_value=KeyList([False] * 512)):
                dx, dy = input_handler.get_camera_movement()
                assert dx < 0

    def test_no_keys_no_edge_returns_zero(self, input_handler):
        class KeyList(list):
            def __getitem__(self, index):
                try:
                    return super().__getitem__(index)
                except IndexError:
                    return False

        with patch("pygame.mouse.get_pos", return_value=(640, 360)):
            with patch("pygame.key.get_pressed", return_value=KeyList([False] * 512)):
                dx, dy = input_handler.get_camera_movement()
                assert dx == pytest.approx(0.0, abs=1e-9)
                assert dy == pytest.approx(0.0, abs=1e-9)


class TestModifiers:
    def test_modifiers_record_ctrl_shift(self, input_handler):
        with patch("pygame.key.get_mods", return_value=pygame.KMOD_CTRL | pygame.KMOD_SHIFT):
            mods = input_handler._get_modifiers()
            assert mods[0] is True
            assert mods[1] is True
            assert mods[2] is False
            assert mods[3] is False
