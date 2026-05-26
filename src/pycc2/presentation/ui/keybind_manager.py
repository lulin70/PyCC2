"""Keybind Manager — customizable keybindings for PyCC2.

Manages action-to-key mappings with save/load to JSON.
"""
from __future__ import annotations

import json
import os

import pygame


# Default keybindings (action_name -> pygame key constant)
DEFAULT_KEYBINDS: dict[str, int] = {
    'move': pygame.K_z,
    'move_fast': pygame.K_x,
    'sneak': pygame.K_s,
    'fire': pygame.K_c,
    'smoke': pygame.K_v,
    'defend': pygame.K_d,
    'hide': pygame.K_h,
    'cancel': pygame.K_ESCAPE,
    'select_all': pygame.K_a,
    'camera_up': pygame.K_UP,
    'camera_down': pygame.K_DOWN,
    'camera_left': pygame.K_LEFT,
    'camera_right': pygame.K_RIGHT,
}

# Human-readable labels for each action
ACTION_LABELS: dict[str, str] = {
    'move': 'Move',
    'move_fast': 'Move Fast',
    'sneak': 'Sneak',
    'fire': 'Fire / Attack',
    'smoke': 'Smoke',
    'defend': 'Defend',
    'hide': 'Hide',
    'cancel': 'Cancel / Deselect',
    'select_all': 'Select All',
    'camera_up': 'Camera Up',
    'camera_down': 'Camera Down',
    'camera_left': 'Camera Left',
    'camera_right': 'Camera Right',
}

_SAVE_PATH = os.path.expanduser('~/.pycc2_keybinds.json')


class KeybindManager:
    """Manages customizable keybindings with save/load support."""

    def __init__(self) -> None:
        self._bindings: dict[str, int] = dict(DEFAULT_KEYBINDS)
        self._listening: str | None = None
        self._load_bindings()

    def get_key(self, action: str) -> int:
        """Get the key bound to an action."""
        return self._bindings.get(action, 0)

    def get_action(self, key: int) -> str | None:
        """Get the action bound to a key (first match)."""
        for action, bound_key in self._bindings.items():
            if bound_key == key:
                return action
        return None

    def get_all_bindings(self) -> dict[str, int]:
        """Return a copy of all current bindings."""
        return dict(self._bindings)

    def start_listening(self, action: str) -> None:
        """Start listening for a key press to bind to an action."""
        if action in self._bindings:
            self._listening = action

    def cancel_listening(self) -> None:
        """Cancel the current listening state."""
        self._listening = None

    def handle_key(self, key: int) -> bool:
        """Handle a key press during rebind listening.

        Returns True if a binding was set.
        """
        if self._listening is None:
            return False
        # Don't allow binding ESC to anything — it cancels
        if key == pygame.K_ESCAPE:
            self._listening = None
            return False
        self._bindings[self._listening] = key
        self._listening = None
        self._save_bindings()
        return True

    @property
    def is_listening(self) -> bool:
        return self._listening is not None

    @property
    def listening_action(self) -> str | None:
        return self._listening

    def reset_to_default(self) -> None:
        """Reset all bindings to defaults."""
        self._bindings = dict(DEFAULT_KEYBINDS)
        self._listening = None
        self._save_bindings()

    @staticmethod
    def key_name(key: int) -> str:
        """Return a human-readable name for a pygame key constant."""
        return pygame.key.name(key).upper() if key else '???'

    def _save_bindings(self) -> None:
        """Save bindings to a JSON file."""
        data = {action: key for action, key in self._bindings.items()}
        try:
            with open(_SAVE_PATH, 'w') as f:
                json.dump(data, f)
        except OSError:
            pass

    def _load_bindings(self) -> None:
        """Load bindings from JSON file."""
        if not os.path.exists(_SAVE_PATH):
            return
        try:
            with open(_SAVE_PATH) as f:
                data = json.load(f)
            for action, key in data.items():
                if action in self._bindings:
                    self._bindings[action] = int(key)
        except (OSError, json.JSONDecodeError, ValueError):
            pass
