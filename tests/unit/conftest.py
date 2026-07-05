"""Unit test layer configuration.

D13 N-5 (P3): Layer-specific conftest for unit tests.

Unit tests should be:
- Fast (no I/O, no pygame display unless explicitly needed)
- Isolated (each test manages its own fixtures)
- Deterministic (no random, no network, no time-dependent behavior)

Shared fixtures (pygame_display, mock_font, game_instance, FakeAIService,
FakeCombatDirector) remain in tests/conftest.py for backward compatibility.
This file is the entry point for future unit-layer-specific fixtures.
"""

from __future__ import annotations
