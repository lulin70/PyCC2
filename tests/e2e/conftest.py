"""End-to-end test layer configuration.

D13 N-5 (P3): Layer-specific conftest for e2e tests.

E2E tests should:
- Verify complete user journeys (menu -> campaign -> deployment -> battle -> pause)
- Use the real GameLoop with headless pygame (SDL dummy drivers)
- Capture screenshots at each journey step for visual regression
- Be the slowest tier, run separately in CI (`e2e-tests` job)

Shared fixtures (pygame_display, mock_font, game_instance, FakeAIService,
FakeCombatDirector) remain in tests/conftest.py for backward compatibility.
This file is the entry point for future e2e-layer-specific fixtures
(e.g., screenshot helpers, journey step factories).
"""

from __future__ import annotations
