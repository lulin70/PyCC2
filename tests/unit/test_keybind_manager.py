from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from pycc2.presentation.ui.keybind_manager import (
    ACTION_LABELS,
    DEFAULT_KEYBINDS,
    KeybindManager,
)


@pytest.fixture
def mock_save_path(tmp_path):
    """Provide a temporary save path for keybinds."""
    path = str(tmp_path / "keybinds.json")
    with patch("pycc2.presentation.ui.keybind_manager._SAVE_PATH", path):
        yield path


@pytest.fixture
def manager(mock_save_path):
    """Create a KeybindManager with a temp save path."""
    return KeybindManager()


class TestDefaultKeybinds:
    def test_all_defaults_are_tuples(self):
        for action, combo in DEFAULT_KEYBINDS.items():
            assert isinstance(combo, tuple), f"{action} should be tuple, got {type(combo)}"

    def test_all_defaults_have_at_least_one_key(self):
        for action, combo in DEFAULT_KEYBINDS.items():
            assert len(combo) >= 1, f"{action} should have at least one key"

    def test_all_actions_have_labels(self):
        for action in DEFAULT_KEYBINDS:
            assert action in ACTION_LABELS, f"Missing label for action '{action}'"


class TestGetKey:
    def test_get_key_returns_tuple(self, manager):
        result = manager.get_key("move")
        assert isinstance(result, tuple)

    def test_get_key_unknown_action_returns_empty(self, manager):
        result = manager.get_key("nonexistent")
        assert result == (0,)


class TestGetAction:
    def test_get_action_finds_binding(self, manager):
        import pygame

        result = manager.get_action((pygame.K_z,))
        assert result == "move"

    def test_get_action_unknown_combo_returns_none(self, manager):
        result = manager.get_action((99999,))
        assert result is None


class TestGetAllBindings:
    def test_returns_dict_of_tuples(self, manager):
        bindings = manager.get_all_bindings()
        assert isinstance(bindings, dict)
        for _action, combo in bindings.items():
            assert isinstance(combo, tuple)


class TestListening:
    def test_start_listening(self, manager):
        manager.start_listening("move")
        assert manager.is_listening is True
        assert manager.listening_action == "move"

    def test_cancel_listening(self, manager):
        manager.start_listening("move")
        manager.cancel_listening()
        assert manager.is_listening is False
        assert manager.listening_action is None

    def test_start_listening_unknown_action_ignored(self, manager):
        manager.start_listening("nonexistent")
        assert manager.is_listening is False


class TestHandleKey:
    def test_handle_key_sets_binding(self, manager):
        import pygame

        manager.start_listening("move")
        with patch.object(pygame.key, "get_mods", return_value=0):
            result = manager.handle_key(pygame.K_m)
        assert result is True
        assert manager.get_key("move") == (pygame.K_m,)

    def test_handle_key_esc_cancels(self, manager):
        import pygame

        manager.start_listening("move")
        result = manager.handle_key(pygame.K_ESCAPE)
        assert result is False
        assert manager.is_listening is False

    def test_handle_key_not_listening_returns_false(self, manager):
        import pygame

        result = manager.handle_key(pygame.K_m)
        assert result is False

    def test_handle_key_with_ctrl_modifier(self, manager):
        import pygame

        manager.start_listening("move")
        with patch.object(pygame.key, "get_mods", return_value=pygame.KMOD_CTRL):
            result = manager.handle_key(pygame.K_a)
        assert result is True
        combo = manager.get_key("move")
        assert pygame.K_LCTRL in combo
        assert pygame.K_a in combo

    def test_handle_key_with_shift_modifier(self, manager):
        import pygame

        manager.start_listening("fire")
        with patch.object(pygame.key, "get_mods", return_value=pygame.KMOD_SHIFT):
            result = manager.handle_key(pygame.K_f)
        assert result is True
        combo = manager.get_key("fire")
        assert pygame.K_LSHIFT in combo
        assert pygame.K_f in combo

    def test_handle_key_modifier_alone_is_single_key(self, manager):
        import pygame

        manager.start_listening("move")
        with patch.object(pygame.key, "get_mods", return_value=0):
            result = manager.handle_key(pygame.K_LCTRL)
        assert result is True
        assert manager.get_key("move") == (pygame.K_LCTRL,)

    def test_handle_key_conflict_emits_warning(self, manager):
        import pygame

        # Bind 'move' to K_z (default), then try to bind 'fire' to same key
        manager.start_listening("fire")
        with patch.object(pygame.key, "get_mods", return_value=0):
            with pytest.warns(UserWarning, match="already bound"):
                manager.handle_key(pygame.K_z)


class TestGetConflicts:
    def test_no_conflicts_by_default(self, manager):
        conflicts = manager.get_conflicts()
        assert conflicts == {}

    def test_detects_conflict(self, manager):
        import pygame

        # Manually set two actions to the same key
        manager._bindings["move"] = (pygame.K_m,)
        manager._bindings["fire"] = (pygame.K_m,)
        conflicts = manager.get_conflicts()
        assert "move" in conflicts
        assert "fire" in conflicts["move"]
        assert "fire" in conflicts
        assert "move" in conflicts["fire"]


class TestResetToDefault:
    def test_reset_restores_defaults(self, manager):
        import pygame

        manager._bindings["move"] = (pygame.K_p,)
        manager.reset_to_default()
        assert manager.get_key("move") == DEFAULT_KEYBINDS["move"]


class TestKeyName:
    def test_key_name_int(self):
        import pygame

        result = KeybindManager.key_name(pygame.K_a)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_key_name_tuple(self):
        import pygame

        result = KeybindManager.key_name((pygame.K_LCTRL, pygame.K_a))
        assert "+" in result

    def test_key_name_zero_returns_unknown(self):
        result = KeybindManager.key_name(0)
        assert result == "???"


class TestSaveLoad:
    def test_save_creates_file(self, manager, mock_save_path):
        manager._save_bindings()
        assert os.path.exists(mock_save_path)

    def test_save_load_roundtrip(self, manager, mock_save_path):
        import pygame

        manager._bindings["move"] = (pygame.K_LCTRL, pygame.K_p)
        manager._save_bindings()

        # Create new manager to trigger load
        mgr2 = KeybindManager()
        assert mgr2.get_key("move") == (pygame.K_LCTRL, pygame.K_p)

    def test_load_old_format_single_int(self, mock_save_path):
        """Backward compat: old format stored single int per action."""
        # Write old-format data
        old_data = {"move": 122}  # 122 = pygame.K_z
        with open(mock_save_path, "w") as f:
            json.dump(old_data, f)

        mgr = KeybindManager()
        assert mgr.get_key("move") == (122,)

    def test_load_new_format_list(self, mock_save_path):
        """New format stores list of ints per action."""
        import pygame

        new_data = {"move": [pygame.K_LCTRL, pygame.K_p]}
        with open(mock_save_path, "w") as f:
            json.dump(new_data, f)

        mgr = KeybindManager()
        assert mgr.get_key("move") == (pygame.K_LCTRL, pygame.K_p)

    def test_load_corrupt_file_falls_back(self, mock_save_path):
        """Corrupt JSON should not crash, just use defaults."""
        with open(mock_save_path, "w") as f:
            f.write("not valid json{{{")
        mgr = KeybindManager()
        assert mgr.get_key("move") == DEFAULT_KEYBINDS["move"]

    def test_load_missing_file_uses_defaults(self, mock_save_path):
        """Missing file should use defaults."""
        # Don't create the file
        if os.path.exists(mock_save_path):
            os.remove(mock_save_path)
        mgr = KeybindManager()
        assert mgr.get_key("move") == DEFAULT_KEYBINDS["move"]
