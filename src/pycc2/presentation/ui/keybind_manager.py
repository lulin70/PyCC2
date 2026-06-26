"""Keybind Manager — customizable keybindings for PyCC2.

Manages action-to-key mappings with save/load to JSON.
Supports modifier key combinations and conflict detection.
"""

from __future__ import annotations

import json
import os
import warnings

import pygame

# Default keybindings (action_name -> tuple of pygame key constants)
# Single key: (pygame.K_m,)  |  Combo: (pygame.K_LCTRL, pygame.K_a)
DEFAULT_KEYBINDS: dict[str, tuple[int, ...]] = {
    "move": (pygame.K_z,),
    "move_fast": (pygame.K_x,),
    "sneak": (pygame.K_s,),
    "fire": (pygame.K_c,),
    "smoke": (pygame.K_v,),
    "defend": (pygame.K_d,),
    "hide": (pygame.K_h,),
    "cancel": (pygame.K_ESCAPE,),
    "select_all": (pygame.K_a,),
    "camera_up": (pygame.K_UP,),
    "camera_down": (pygame.K_DOWN,),
    "camera_left": (pygame.K_LEFT,),
    "camera_right": (pygame.K_RIGHT,),
}

# Human-readable labels for each action
ACTION_LABELS: dict[str, str] = {
    "move": "Move",
    "move_fast": "Move Fast",
    "sneak": "Sneak",
    "fire": "Fire / Attack",
    "smoke": "Smoke",
    "defend": "Defend",
    "hide": "Hide",
    "cancel": "Cancel / Deselect",
    "select_all": "Select All",
    "camera_up": "Camera Up",
    "camera_down": "Camera Down",
    "camera_left": "Camera Left",
    "camera_right": "Camera Right",
}

# Modifier key constants for detection
_MOD_KEYS = {
    pygame.K_LCTRL,
    pygame.K_RCTRL,
    pygame.K_LSHIFT,
    pygame.K_RSHIFT,
    pygame.K_LALT,
    pygame.K_RALT,
    pygame.K_LMETA,
    pygame.K_RMETA,
}

_SAVE_PATH = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "pycc2",
    "keybinds.json",
)


class KeybindManager:
    """Manages customizable keybindings with save/load support."""

    def __init__(self) -> None:
        self._bindings: dict[str, tuple[int, ...]] = {k: v for k, v in DEFAULT_KEYBINDS.items()}
        self._listening: str | None = None
        self._load_bindings()

    def get_key(self, action: str) -> tuple[int, ...]:
        """Get the key combo bound to an action."""
        return self._bindings.get(action, (0,))

    def get_action(self, key_combo: tuple[int, ...]) -> str | None:
        """Get the action bound to a key combo (first match)."""
        for action, bound_combo in self._bindings.items():
            if bound_combo == key_combo:
                return action
        return None

    def get_all_bindings(self) -> dict[str, tuple[int, ...]]:
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

        Detects modifier keys held down and creates a combo.
        Returns True if a binding was set.
        Emits a warning if the captured combo conflicts with another action.
        """
        if self._listening is None:
            return False
        # Don't allow binding ESC to anything — it cancels
        if key == pygame.K_ESCAPE:
            self._listening = None
            return False

        # Detect currently held modifier keys
        mod_state = pygame.key.get_mods()
        held_mods: list[int] = []
        if mod_state & pygame.KMOD_CTRL:
            held_mods.append(pygame.K_LCTRL)
        if mod_state & pygame.KMOD_SHIFT:
            held_mods.append(pygame.K_LSHIFT)
        if mod_state & pygame.KMOD_ALT:
            held_mods.append(pygame.K_LALT)

        # If the pressed key itself is a modifier, treat as single key
        combo: tuple[int, ...]
        if key in _MOD_KEYS:
            combo = (key,)
        elif held_mods:
            combo = tuple(held_mods) + (key,)
        else:
            combo = (key,)

        # Conflict detection
        for action, bound_combo in self._bindings.items():
            if action != self._listening and bound_combo == combo:
                warnings.warn(
                    f"Key combo {self.key_name(combo)} is already bound to '{action}'",
                    stacklevel=2,
                )
                break

        self._bindings[self._listening] = combo
        self._listening = None
        self._save_bindings()
        return True

    def get_conflicts(self) -> dict[str, list[str]]:
        """Detect and return all keybinding conflicts.

        Returns a dict mapping action names to lists of other actions
        that share the same key combo.
        """
        combo_to_actions: dict[tuple[int, ...], list[str]] = {}
        for action, combo in self._bindings.items():
            combo_to_actions.setdefault(combo, []).append(action)

        conflicts: dict[str, list[str]] = {}
        for _combo, actions in combo_to_actions.items():
            if len(actions) > 1:
                for action in actions:
                    others = [a for a in actions if a != action]
                    conflicts[action] = others
        return conflicts

    @property
    def is_listening(self) -> bool:
        return self._listening is not None

    @property
    def listening_action(self) -> str | None:
        return self._listening

    def reset_to_default(self) -> None:
        """Reset all bindings to defaults."""
        self._bindings = {k: v for k, v in DEFAULT_KEYBINDS.items()}
        self._listening = None
        self._save_bindings()

    @staticmethod
    def key_name(key_or_combo: int | tuple[int, ...]) -> str:
        """Return a human-readable name for a pygame key constant or combo."""
        if isinstance(key_or_combo, int):
            return pygame.key.name(key_or_combo).upper() if key_or_combo else "???"
        # tuple combo: join with +
        parts = [pygame.key.name(k).upper() if k else "???" for k in key_or_combo]
        return "+".join(parts) if parts else "???"

    def _save_bindings(self) -> None:
        """Save bindings to a JSON file."""
        data = {action: list(combo) for action, combo in self._bindings.items()}
        try:
            os.makedirs(os.path.dirname(_SAVE_PATH), exist_ok=True)
            with open(_SAVE_PATH, "w") as f:
                json.dump(data, f)
        except OSError:
            pass

    def _load_bindings(self) -> None:
        """Load bindings from JSON file.

        Supports backward compatibility with old format (single int per action).
        Old format: {"action": 123}  ->  converted to {"action": [123]}
        New format: {"action": [123, 456]}
        """
        if not os.path.exists(_SAVE_PATH):
            return
        try:
            with open(_SAVE_PATH) as f:
                data = json.load(f)
            for action, value in data.items():
                if action not in self._bindings:
                    continue
                # Backward compat: old format stored a single int
                if isinstance(value, int):
                    self._bindings[action] = (value,)
                elif isinstance(value, list):
                    self._bindings[action] = tuple(value)
        except (OSError, json.JSONDecodeError, ValueError):
            pass
