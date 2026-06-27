"""Presentation Layer - Layer 1

Handles all rendering, input handling, and UI components.
This layer depends on domain layer but domain layer has zero dependency on this.
"""

from pycc2.presentation.input.handler import InputEvent, PygameInputHandler
from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

__all__ = [
    "EnhancedRenderer",
    "PygameInputHandler",
    "InputEvent",
]
