"""
Input Handling Subsystem

Processes user input from keyboard, mouse, and other devices.
Translates raw input into game commands.
"""

from pycc2.presentation.input.handler import InputEvent, PygameInputHandler

__all__ = [
    "PygameInputHandler",
    "InputEvent",
]
