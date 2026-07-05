"""Integration test layer configuration.

D13 N-5 (P3): Layer-specific conftest for integration tests.

Integration tests should:
- Verify inter-module collaboration (e.g., combat service + event bus + achievement bridge)
- Use real components where feasible, fakes only for external dependencies
- Be slower than unit tests but faster than e2e tests

Shared fixtures (pygame_display, mock_font, game_instance, FakeAIService,
FakeCombatDirector) remain in tests/conftest.py for backward compatibility.
This file is the entry point for future integration-layer-specific fixtures.
"""

from __future__ import annotations
