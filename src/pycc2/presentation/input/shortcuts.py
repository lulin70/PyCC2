"""
Default Keyboard Shortcuts Configuration

Defines default keybindings for all game actions.
Can be customized by users or overridden per-platform.
"""

import pygame

from pycc2.presentation.input.handler import InputAction

DEFAULT_SHORTCUTS: dict[InputAction, list[tuple[int, str]]] = {
    InputAction.MOVE_CAMERA_UP: [
        (119, "W"),
        (pygame.K_UP, "Up Arrow"),
    ],
    InputAction.MOVE_CAMERA_DOWN: [
        (115, "S"),
        (pygame.K_DOWN, "Down Arrow"),
    ],
    InputAction.MOVE_CAMERA_LEFT: [
        (97, "A"),
        (pygame.K_LEFT, "Left Arrow"),
    ],
    InputAction.MOVE_CAMERA_RIGHT: [
        (100, "D"),
        (pygame.K_RIGHT, "Right Arrow"),
    ],
    InputAction.ZOOM_IN: [
        (61, "="),
        (270, "Numpad +"),
        (pygame.K_EQUALS, "Plus"),
    ],
    InputAction.ZOOM_OUT: [
        (45, "-"),
        (269, "Numpad -"),
        (pygame.K_MINUS, "Minus"),
    ],
    InputAction.SELECT: [
        (1, "Left Mouse"),
    ],
    InputAction.COMMAND_MOVE: [
        (109, "M"),
    ],
    InputAction.COMMAND_ATTACK: [
        (97, "A"),  # Note: conflicts with camera left when not in command mode
    ],
    InputAction.COMMAND_HOLD: [
        (104, "H"),
    ],
    InputAction.COMMAND_DIG_IN: [
        (100, "D"),
    ],
    InputAction.CANCEL: [
        (27, "Escape"),
        (3, "Right Mouse"),
    ],
    InputAction.END_TURN: [
        (32, "Space"),
    ],
    InputAction.TOGGLE_DEBUG: [
        (286, "F3"),
    ],
    InputAction.TOGGLE_GRID: [
        (103, "G"),
    ],
    InputAction.SAVE_GAME: [
        (288, "F5"),
    ],
    InputAction.LOAD_GAME: [
        (292, "F9"),
    ],
    InputAction.QUIT: [
        (113, "Q"),
    ],
}


def get_shortcut_string(action: InputAction) -> str:
    """Get human-readable shortcut string for an action."""
    shortcuts = DEFAULT_SHORTCUTS.get(action, [])
    if not shortcuts:
        return "Unbound"
    _, name = shortcuts[0]
    return name


def get_all_shortcuts() -> dict[str, str]:
    """Get dictionary of all action names to their primary shortcut."""
    result = {}
    for action, bindings in DEFAULT_SHORTCUTS.items():
        if bindings:
            _, name = bindings[0]
            result[action.name] = name
    return result
