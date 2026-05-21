"""
Application Services Layer - Layer 2
Orchestrates domain logic and coordinates between layers.
Contains use case implementations but no business rules.
"""

import importlib

_service_modules = [
    ("pycc2.services.game_loop", "GameLoop"),
    ("pycc2.services.combat_service", "CombatService"),
    ("pycc2.services.ai_service", "AIService"),
    ("pycc2.services.turn_service", "TurnService"),
    ("pycc2.services.event_bus", "EventBus"),
]

_all_exports: list[str] = []

for _module_path, _name in _service_modules:
    try:
        _mod = importlib.import_module(_module_path)
        globals()[_name] = getattr(_mod, _name)
        _all_exports.append(_name)
    except (ImportError, ModuleNotFoundError):
        pass

__all__ = _all_exports
