"""Tests for pycc2.main entry point and helpers.

Uses SDL dummy driver for headless pygame. Helper functions are tested
directly; main() control flow is tested via monkeypatching heavy
dependencies (WindowManager, _show_main_menu, _start_new_game, etc.).
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from pycc2.main import _resolve_map_path, _run_game_loop, main

# ===========================================================================
# _resolve_map_path
# ===========================================================================


@pytest.mark.unit
class TestResolveMapPath:
    def test_returns_path_when_map_exists(self, tmp_path, monkeypatch):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "arnhem.json").write_text("{}")
        monkeypatch.chdir(tmp_path)

        result = _resolve_map_path("arnhem")

        assert result is not None
        assert result.name == "arnhem.json"

    def test_falls_back_to_first_available_map(self, tmp_path, monkeypatch):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "other_map.json").write_text("{}")
        (maps_dir / "_schema.json").write_text("{}")
        monkeypatch.chdir(tmp_path)

        result = _resolve_map_path("nonexistent")

        assert result is not None
        assert result.name == "other_map.json"
        assert result.stem != "_schema"

    def test_returns_none_when_no_maps(self, tmp_path, monkeypatch):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        result = _resolve_map_path("nonexistent")

        assert result is None

    def test_falls_back_skips_schema_file(self, tmp_path, monkeypatch):
        maps_dir = tmp_path / "data" / "maps"
        maps_dir.mkdir(parents=True)
        (maps_dir / "_schema.json").write_text("{}")
        (maps_dir / "real_map.json").write_text("{}")
        monkeypatch.chdir(tmp_path)

        result = _resolve_map_path("missing")

        assert result is not None
        assert result.stem == "real_map"


# ===========================================================================
# _run_game_loop
# ===========================================================================


class StubGameLoop:
    def __init__(self, return_value=0, raise_exc=None):
        self._return_value = return_value
        self._raise_exc = raise_exc
        self.run_called = False

    def run(self):
        self.run_called = True
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._return_value


@pytest.mark.unit
class TestRunGameLoop:
    def test_returns_game_loop_result(self):
        loop = StubGameLoop(return_value=0)
        assert _run_game_loop(loop) == 0
        assert loop.run_called

    def test_runtime_error_returns_1(self):
        loop = StubGameLoop(raise_exc=RuntimeError("boom"))
        assert _run_game_loop(loop) == 1

    def test_value_error_returns_1(self):
        loop = StubGameLoop(raise_exc=ValueError("bad"))
        assert _run_game_loop(loop) == 1

    def test_type_error_returns_1(self):
        loop = StubGameLoop(raise_exc=TypeError("wrong"))
        assert _run_game_loop(loop) == 1


# ===========================================================================
# _create_game_objects
# ===========================================================================


@pytest.fixture
def real_game_map():
    from pathlib import Path

    from pycc2.domain.entities.game_map import GameMap

    return GameMap.from_json(Path("data/maps/arnhem.json"))


@pytest.fixture
def real_camera(real_game_map):
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.presentation.rendering.camera import Camera

    return Camera(
        position=Vec2(real_game_map.width * 16.0, real_game_map.height * 16.0),
        viewport_width=1280,
        viewport_height=720,
    )


@pytest.fixture
def real_event_bus():
    from pycc2.infrastructure.events.event_bus import EventBus

    return EventBus()


class StubWindowManagerForFactory:
    def __init__(self):
        self._screen = pygame.Surface((1280, 720))

    def get_screen(self):
        return self._screen

    def get_actual_size(self):
        return self._screen.get_size()

    def get_surface(self, *a, **kw):
        return self._screen


@pytest.mark.unit
class TestCreateGameObjects:
    def test_creates_all_expected_keys(self, real_game_map, real_camera, real_event_bus):
        from pycc2.main import _create_game_objects

        screen = pygame.Surface((1280, 720))
        wm = StubWindowManagerForFactory()
        objects = _create_game_objects(real_game_map, real_camera, screen, wm, real_event_bus)

        expected_keys = {
            "state", "renderer", "event_bus", "input_handler",
            "interaction_controller", "display_config", "hint_manager",
            "keybind_manager", "settings_menu", "tutorial_overlay", "game_loop",
        }
        assert expected_keys.issubset(objects.keys())

    def test_game_loop_is_game_loop(self, real_game_map, real_camera, real_event_bus):
        from pycc2.main import _create_game_objects
        from pycc2.services.game_loop import GameLoop

        screen = pygame.Surface((1280, 720))
        wm = StubWindowManagerForFactory()
        objects = _create_game_objects(real_game_map, real_camera, screen, wm, real_event_bus)

        assert isinstance(objects["game_loop"], GameLoop)

    def test_with_ai_service(self, real_game_map, real_camera, real_event_bus):
        from pycc2.main import _create_game_objects
        from pycc2.services.ai_service import AIService

        ai = AIService(event_bus=real_event_bus)
        screen = pygame.Surface((1280, 720))
        wm = StubWindowManagerForFactory()
        objects = _create_game_objects(
            real_game_map, real_camera, screen, wm, real_event_bus, ai_service=ai
        )

        assert objects["game_loop"] is not None

    def test_state_has_map_and_camera(self, real_game_map, real_camera, real_event_bus):
        from pycc2.main import _create_game_objects

        screen = pygame.Surface((1280, 720))
        wm = StubWindowManagerForFactory()
        objects = _create_game_objects(real_game_map, real_camera, screen, wm, real_event_bus)

        assert objects["state"].game_map is real_game_map
        assert objects["state"].camera is real_camera


# ===========================================================================
# main() control flow
# ===========================================================================


class StubWindowManager:
    """Minimal WindowManager stub returning a real Surface."""

    def __init__(self, *args, **kwargs):
        pass

    def initialize(self):
        return pygame.Surface((1280, 720))


@pytest.fixture
def patched_main_deps(monkeypatch):
    """Patch heavy dependencies so main() control flow can be tested."""
    import pycc2.main as main_mod

    monkeypatch.setattr(pygame, "init", lambda: None)
    monkeypatch.setattr(pygame, "quit", lambda: None)
    monkeypatch.setattr(pygame.time, "Clock", lambda: _StubClock())

    monkeypatch.setattr(
        "pycc2.presentation.rendering.window_config.WindowManager", StubWindowManager
    )
    monkeypatch.setattr(
        "pycc2.presentation.rendering.window_config.DisplayInfo",
        lambda **kw: None,
    )

    return main_mod


class _StubClock:
    def tick(self, fps):
        return 16


@pytest.mark.unit
class TestMainControlFlow:
    def test_quit_returns_0(self, patched_main_deps, monkeypatch):
        monkeypatch.setattr(
            patched_main_deps, "_show_main_menu", lambda screen, clock: ("quit", None)
        )
        assert main() == 0

    def test_start_campaign_success(self, patched_main_deps, monkeypatch):
        monkeypatch.setattr(
            patched_main_deps,
            "_show_main_menu",
            lambda screen, clock: ("start_campaign", _StubMenu()),
        )
        stub_loop = StubGameLoop(return_value=0)
        monkeypatch.setattr(
            patched_main_deps, "_start_new_game", lambda *a, **kw: stub_loop
        )
        monkeypatch.setattr(
            patched_main_deps,
            "_run_game_loop",
            lambda gl: gl.run(),
        )
        assert main() == 0
        assert stub_loop.run_called

    def test_start_skirmish_success(self, patched_main_deps, monkeypatch):
        monkeypatch.setattr(
            patched_main_deps,
            "_show_main_menu",
            lambda screen, clock: ("start_skirmish", _StubMenu()),
        )
        stub_loop = StubGameLoop(return_value=0)
        monkeypatch.setattr(
            patched_main_deps, "_start_new_game", lambda *a, **kw: stub_loop
        )
        monkeypatch.setattr(patched_main_deps, "_run_game_loop", lambda gl: gl.run())
        assert main() == 0

    def test_load_game_valid_slot(self, patched_main_deps, monkeypatch):
        monkeypatch.setattr(
            patched_main_deps,
            "_show_main_menu",
            lambda screen, clock: ("load_game:3", None),
        )
        stub_loop = StubGameLoop(return_value=0)
        monkeypatch.setattr(
            patched_main_deps, "_load_saved_game", lambda slot, screen, wm: stub_loop
        )
        monkeypatch.setattr(patched_main_deps, "_run_game_loop", lambda gl: gl.run())
        assert main() == 0
        assert stub_loop.run_called

    def test_load_game_invalid_slot_returns_1(self, patched_main_deps, monkeypatch):
        monkeypatch.setattr(
            patched_main_deps,
            "_show_main_menu",
            lambda screen, clock: ("load_game:abc", None),
        )
        assert main() == 1

    def test_load_game_returns_none_returns_1(self, patched_main_deps, monkeypatch):
        monkeypatch.setattr(
            patched_main_deps,
            "_show_main_menu",
            lambda screen, clock: ("load_game:1", None),
        )
        monkeypatch.setattr(
            patched_main_deps, "_load_saved_game", lambda slot, screen, wm: None
        )
        assert main() == 1

    def test_start_new_game_returns_none_returns_1(self, patched_main_deps, monkeypatch):
        monkeypatch.setattr(
            patched_main_deps,
            "_show_main_menu",
            lambda screen, clock: ("start_campaign", _StubMenu()),
        )
        monkeypatch.setattr(patched_main_deps, "_start_new_game", lambda *a, **kw: None)
        assert main() == 1

    def test_unknown_menu_action_defaults_to_campaign(
        self, patched_main_deps, monkeypatch
    ):
        captured = {}

        def fake_start_new_game(menu, action, screen, wm):
            captured["action"] = action
            return StubGameLoop(return_value=0)

        monkeypatch.setattr(
            patched_main_deps,
            "_show_main_menu",
            lambda screen, clock: ("weird_action", _StubMenu()),
        )
        monkeypatch.setattr(patched_main_deps, "_start_new_game", fake_start_new_game)
        monkeypatch.setattr(patched_main_deps, "_run_game_loop", lambda gl: gl.run())
        assert main() == 0
        assert captured["action"] == "start_campaign"

    def test_keyboard_interrupt_returns_130(self, patched_main_deps, monkeypatch):
        def raise_kb(screen, clock):
            raise KeyboardInterrupt

        monkeypatch.setattr(patched_main_deps, "_show_main_menu", raise_kb)
        assert main() == 130

    def test_pygame_error_returns_1(self, patched_main_deps, monkeypatch):
        def raise_pg_err(screen, clock):
            raise pygame.error("display fail")

        monkeypatch.setattr(patched_main_deps, "_show_main_menu", raise_pg_err)
        assert main() == 1

    def test_os_error_returns_1(self, patched_main_deps, monkeypatch):
        def raise_os(screen, clock):
            raise OSError("io fail")

        monkeypatch.setattr(patched_main_deps, "_show_main_menu", raise_os)
        assert main() == 1


class _StubMenu:
    """Minimal menu stub for main() tests."""

    def get_selected_map(self):
        return "arnhem"

    def get_settings(self):
        class S:
            player_side = "allied"

        return S()
