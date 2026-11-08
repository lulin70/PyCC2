"""Unit tests for KeyboardShortcutManager (singleton, dispatch, modifiers)."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import logging

import pygame
import pytest

from pycc2.input.keyboard_shortcut_manager import (
    KeyboardShortcutManager,
    KeyModifier,
    ShortcutAction,
)


@pytest.fixture()
def manager() -> KeyboardShortcutManager:
    KeyboardShortcutManager.reset_instance()
    instance = KeyboardShortcutManager()
    yield instance
    KeyboardShortcutManager.reset_instance()


def _keydown(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


# ===========================================================================
# Singleton behaviour
# ===========================================================================


@pytest.mark.unit
class TestSingleton:
    def test_direct_construction_returns_singleton(self):
        KeyboardShortcutManager.reset_instance()
        try:
            assert KeyboardShortcutManager() is KeyboardShortcutManager()
        finally:
            KeyboardShortcutManager.reset_instance()

    def test_get_instance_returns_same_object(self):
        KeyboardShortcutManager.reset_instance()
        try:
            first = KeyboardShortcutManager.get_instance()
            assert KeyboardShortcutManager.get_instance() is first
        finally:
            KeyboardShortcutManager.reset_instance()

    def test_reset_instance_creates_new_object(self):
        KeyboardShortcutManager.reset_instance()
        try:
            first = KeyboardShortcutManager.get_instance()
            KeyboardShortcutManager.reset_instance()
            second = KeyboardShortcutManager.get_instance()
            assert first is not second
        finally:
            KeyboardShortcutManager.reset_instance()

    def test_second_construction_keeps_existing_bindings(self, manager):
        manager.register_shortcut(pygame.K_z, KeyModifier.ALT, ShortcutAction.TOGGLE_STATUS_BAR)
        same = KeyboardShortcutManager()
        assert same.get_shortcuts_by_action(ShortcutAction.TOGGLE_STATUS_BAR) == [
            (pygame.K_z, KeyModifier.ALT)
        ]


# ===========================================================================
# Default registrations
# ===========================================================================


@pytest.mark.unit
class TestDefaultShortcuts:
    def test_registers_expected_count(self, manager):
        assert len(manager.get_all_shortcuts()) > 0
        total = sum(len(v) for v in manager.get_all_shortcuts().values())
        assert total == 25

    @pytest.mark.parametrize(
        ("action", "expected"),
        [
            (ShortcutAction.PAUSE_RESUME, [(pygame.K_SPACE, KeyModifier.NONE)]),
            (ShortcutAction.CLOSE_OVERLAYS, [(pygame.K_ESCAPE, KeyModifier.NONE)]),
            (ShortcutAction.QUIT_GAME, [(pygame.K_q, KeyModifier.CTRL)]),
            (ShortcutAction.SELECT_NEXT_UNIT, [(pygame.K_TAB, KeyModifier.NONE)]),
            (ShortcutAction.SELECT_PREV_UNIT, [(pygame.K_TAB, KeyModifier.SHIFT)]),
            (ShortcutAction.CAMERA_RESET, [(pygame.K_HOME, KeyModifier.NONE)]),
            (ShortcutAction.TOGGLE_HELP, [(pygame.K_h, KeyModifier.NONE)]),
            (ShortcutAction.TOGGLE_FPS_DISPLAY, [(pygame.K_F2, KeyModifier.NONE)]),
        ],
    )
    def test_common_default_bindings(self, manager, action, expected):
        assert manager.get_shortcuts_by_action(action) == expected

    @pytest.mark.parametrize("group", range(1, 10))
    def test_unit_group_bindings(self, manager, group):
        action = getattr(ShortcutAction, f"SELECT_UNIT_GROUP_{group}")
        key_code = getattr(pygame, f"K_{group}")
        assert manager.get_shortcuts_by_action(action) == [(key_code, KeyModifier.NONE)]


# ===========================================================================
# register / unregister shortcuts
# ===========================================================================


@pytest.mark.unit
class TestShortcutRegistration:
    def test_register_adds_new_binding(self, manager):
        manager.register_shortcut(pygame.K_x, KeyModifier.ALT, ShortcutAction.TOGGLE_STATUS_BAR)
        assert manager.get_shortcuts_by_action(ShortcutAction.TOGGLE_STATUS_BAR) == [
            (pygame.K_x, KeyModifier.ALT)
        ]

    def test_conflict_overrides_and_logs_warning(self, manager, caplog):
        with caplog.at_level(logging.WARNING):
            manager.register_shortcut(
                pygame.K_SPACE, KeyModifier.NONE, ShortcutAction.TOGGLE_STATUS_BAR
            )

        assert manager.get_shortcuts_by_action(ShortcutAction.PAUSE_RESUME) == []
        assert manager.get_shortcuts_by_action(ShortcutAction.TOGGLE_STATUS_BAR) == [
            (pygame.K_SPACE, KeyModifier.NONE)
        ]
        assert any("Shortcut conflict" in record.message for record in caplog.records)

    def test_unregister_removes_binding(self, manager):
        manager.unregister_shortcut(pygame.K_SPACE, KeyModifier.NONE)
        assert manager.get_shortcuts_by_action(ShortcutAction.PAUSE_RESUME) == []

    def test_unregister_unknown_binding_is_noop(self, manager):
        before = manager.get_all_shortcuts()
        manager.unregister_shortcut(pygame.K_F12, KeyModifier.SHIFT_ALT)
        assert manager.get_all_shortcuts() == before

    def test_get_shortcuts_by_action_unknown_returns_empty(self, manager):
        manager.unregister_shortcut(pygame.K_SPACE, KeyModifier.NONE)
        assert manager.get_shortcuts_by_action(ShortcutAction.PAUSE_RESUME) == []


# ===========================================================================
# Handler registration
# ===========================================================================


@pytest.mark.unit
class TestHandlerRegistration:
    def test_register_appends_handlers(self, manager):
        first = lambda: None  # noqa: E731
        second = lambda: None  # noqa: E731

        manager.register_handler(ShortcutAction.PAUSE_RESUME, first)
        manager.register_handler(ShortcutAction.PAUSE_RESUME, second)

        assert manager._handlers[ShortcutAction.PAUSE_RESUME] == [first, second]

    def test_unregister_removes_only_matching_handler(self, manager):
        first = lambda: None  # noqa: E731
        second = lambda: None  # noqa: E731
        manager.register_handler(ShortcutAction.PAUSE_RESUME, first)
        manager.register_handler(ShortcutAction.PAUSE_RESUME, second)

        manager.unregister_handler(ShortcutAction.PAUSE_RESUME, first)

        assert manager._handlers[ShortcutAction.PAUSE_RESUME] == [second]

    def test_unregister_unknown_action_is_noop(self, manager):
        manager.unregister_handler(ShortcutAction.TOGGLE_STATUS_BAR, lambda: None)
        assert ShortcutAction.TOGGLE_STATUS_BAR not in manager._handlers

    def test_unregister_handler_not_registered_is_noop(self, manager):
        kept = lambda: None  # noqa: E731
        manager.register_handler(ShortcutAction.PAUSE_RESUME, kept)

        manager.unregister_handler(ShortcutAction.PAUSE_RESUME, lambda: None)

        assert manager._handlers[ShortcutAction.PAUSE_RESUME] == [kept]


# ===========================================================================
# Modifier detection
# ===========================================================================


@pytest.mark.unit
class TestGetCurrentModifier:
    @pytest.mark.parametrize(
        ("mods", "expected"),
        [
            (0, KeyModifier.NONE),
            (pygame.KMOD_SHIFT, KeyModifier.SHIFT),
            (pygame.KMOD_CTRL, KeyModifier.CTRL),
            (pygame.KMOD_ALT, KeyModifier.ALT),
            (pygame.KMOD_SHIFT | pygame.KMOD_CTRL, KeyModifier.SHIFT_CTRL),
            (pygame.KMOD_SHIFT | pygame.KMOD_ALT, KeyModifier.SHIFT_ALT),
            (pygame.KMOD_CTRL | pygame.KMOD_ALT, KeyModifier.CTRL_ALT),
            (
                pygame.KMOD_SHIFT | pygame.KMOD_CTRL | pygame.KMOD_ALT,
                KeyModifier.SHIFT_CTRL_ALT,
            ),
        ],
    )
    def test_all_combinations(self, manager, monkeypatch, mods, expected):
        monkeypatch.setattr(pygame.key, "get_mods", lambda: mods)
        assert manager._get_current_modifier() is expected


# ===========================================================================
# Event handling
# ===========================================================================


@pytest.mark.unit
class TestHandleEvent:
    def test_disabled_manager_ignores_events(self, manager):
        called = []
        manager.register_handler(ShortcutAction.PAUSE_RESUME, lambda: called.append(True))
        manager.disable()

        assert manager.handle_event(_keydown(pygame.K_SPACE)) is False
        assert called == []

    def test_non_keydown_event_ignored(self, manager):
        called = []
        manager.register_handler(ShortcutAction.PAUSE_RESUME, lambda: called.append(True))
        event = pygame.event.Event(pygame.KEYUP, key=pygame.K_SPACE)

        assert manager.handle_event(event) is False
        assert called == []

    def test_unbound_key_returns_false(self, manager, monkeypatch):
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        assert manager.handle_event(_keydown(pygame.K_F12)) is False

    def test_bound_key_without_handler_returns_false(self, manager, monkeypatch):
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        assert manager.handle_event(_keydown(pygame.K_SPACE)) is False

    def test_bound_key_calls_all_handlers_and_returns_true(self, manager, monkeypatch):
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        called = []
        manager.register_handler(ShortcutAction.PAUSE_RESUME, lambda: called.append(1))
        manager.register_handler(ShortcutAction.PAUSE_RESUME, lambda: called.append(2))

        assert manager.handle_event(_keydown(pygame.K_SPACE)) is True
        assert called == [1, 2]

    def test_handler_exception_is_logged_and_does_not_stop_others(
        self, manager, monkeypatch, caplog
    ):
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
        called = []

        def broken():
            raise RuntimeError("boom")

        manager.register_handler(ShortcutAction.PAUSE_RESUME, broken)
        manager.register_handler(ShortcutAction.PAUSE_RESUME, lambda: called.append("ok"))

        with caplog.at_level(logging.ERROR):
            assert manager.handle_event(_keydown(pygame.K_SPACE)) is True

        assert called == ["ok"]
        assert any("Handler for" in record.message for record in caplog.records)

    def test_modifier_is_required_for_modified_binding(self, manager, monkeypatch):
        called = []
        manager.register_handler(ShortcutAction.SELECT_PREV_UNIT, lambda: called.append("prev"))
        monkeypatch.setattr(pygame.key, "get_mods", lambda: pygame.KMOD_SHIFT)

        assert manager.handle_event(_keydown(pygame.K_TAB)) is True
        assert called == ["prev"]

    def test_unmodified_key_does_not_trigger_modified_binding(self, manager, monkeypatch):
        called = []
        manager.register_handler(ShortcutAction.SELECT_PREV_UNIT, lambda: called.append("prev"))
        monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)

        assert manager.handle_event(_keydown(pygame.K_TAB)) is False
        assert called == []


# ===========================================================================
# enable / disable
# ===========================================================================


@pytest.mark.unit
class TestEnableDisable:
    def test_enabled_by_default(self, manager):
        assert manager.is_enabled() is True

    def test_disable_then_enable(self, manager):
        manager.disable()
        assert manager.is_enabled() is False
        manager.enable()
        assert manager.is_enabled() is True

    def test_enable_is_idempotent(self, manager):
        manager.enable()
        manager.enable()
        assert manager.is_enabled() is True


# ===========================================================================
# Help display helpers
# ===========================================================================


@pytest.mark.unit
class TestGetAllShortcuts:
    def test_default_labels(self, manager):
        result = manager.get_all_shortcuts()

        assert result["Pause Resume"] == ["SPACE"]
        assert result["Quit Game"] == ["Ctrl+Q"]
        assert result["Select Prev Unit"] == ["Shift+TAB"]

    def test_all_modifier_prefixes_rendered(self, manager):
        action = ShortcutAction.TOGGLE_STATUS_BAR
        manager.register_shortcut(pygame.K_a, KeyModifier.ALT, action)
        manager.register_shortcut(pygame.K_b, KeyModifier.SHIFT_CTRL, action)
        manager.register_shortcut(pygame.K_c, KeyModifier.SHIFT_ALT, action)
        manager.register_shortcut(pygame.K_d, KeyModifier.CTRL_ALT, action)
        manager.register_shortcut(pygame.K_e, KeyModifier.SHIFT_CTRL_ALT, action)

        labels = set(manager.get_all_shortcuts()["Toggle Status Bar"])

        assert labels == {
            "Alt+A",
            "Shift+Ctrl+B",
            "Shift+Alt+C",
            "Ctrl+Alt+D",
            "Shift+Ctrl+Alt+E",
        }
