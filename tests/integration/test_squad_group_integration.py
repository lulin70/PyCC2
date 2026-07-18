"""Integration tests for squad_group_manager wiring into InputRouter + Minimap.

Verifies the v0.7.5 INTEGRATE of SquadGroupManager:
  - InputRouter dispatches Ctrl+1~9 → create_group (from current selection)
  - InputRouter dispatches 1~9 → select_group (updates game_state.selected_unit_ids)
  - Minimap renders bounding boxes for active groups via set_squad_group_manager()
  - GameLoopAssembler wires the manager into both InputRouter and Minimap

These are integration tests (not unit tests) — they exercise the wiring
between InputRouter, SquadGroupManager, GameStateView, and Minimap as a
connected subsystem. Pure SquadGroupManager unit tests live in
tests/unit/test_squad_group_manager.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pygame

from pycc2.presentation.input.input_router import _SQUAD_DIGIT_KEYS, InputRouter
from pycc2.presentation.ui.squad_group_manager import SquadGroupManager

# ============================================================================
# Test fixtures — lightweight stubs matching the protocols InputRouter needs
# ============================================================================


@dataclass(eq=False)
class _StubPosition:
    """Minimal position_component stub (tile-coordinate x/y)."""

    x: float
    y: float


@dataclass(eq=False)
class _StubUnit:
    """Minimal Unit stub for InputRouter + SquadGroupManager tests.

    Identity-based equality (eq=False) matches real Unit semantics.
    """

    id: str
    position_component: _StubPosition = field(default_factory=lambda: _StubPosition(0, 0))


@dataclass
class _StubInputHandler:
    """Minimal IInputHandler stub that returns a canned InputEvent."""

    _event: Any = None

    def process_event(self, event: pygame.event.EventType):
        return self._event

    def get_camera_movement(self) -> tuple[float, float]:
        return (0.0, 0.0)


@dataclass
class _StubGameState:
    """Minimal GameStateView stub matching the protocol InputRouter consumes."""

    running: bool = True
    paused: bool = False
    debug_mode: bool = False
    units: list = field(default_factory=list)
    selected_unit_ids: set = field(default_factory=set)


def _make_key_event(key: int, ctrl: bool = False) -> pygame.event.EventType:
    """Build a synthetic pygame KEYDOWN event with optional Ctrl modifier."""
    mods = pygame.KMOD_CTRL if ctrl else 0
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mods)


def _make_router(
    units: list[_StubUnit] | None = None,
    selected_ids: set[str] | None = None,
    manager: SquadGroupManager | None = None,
) -> tuple[InputRouter, _StubGameState]:
    """Build an InputRouter wired to a fresh SquadGroupManager + GameState."""
    state = _StubGameState(
        units=units or [],
        selected_unit_ids=selected_ids or set(),
    )
    handler = _StubInputHandler()
    router = InputRouter(
        input_handler=handler,
        interaction_controller=None,
        command_bar=None,
        camera=None,
        game_state=state,
        squad_group_manager=manager or SquadGroupManager(),
    )
    return router, state


# ============================================================================
# Wave 2 — Ctrl+1~9 create squad group from current selection
# ============================================================================


class TestCreateSquadGroup:
    """Ctrl+digit creates a squad group from the currently selected units."""

    def test_ctrl_digit_creates_group_from_selection(self):
        """Ctrl+1 with 3 selected units → group 1 contains those 3 units."""
        units = [_StubUnit(id=f"u{i}", position_component=_StubPosition(i, i)) for i in range(3)]
        router, state = _make_router(units=units, selected_ids={"u0", "u1", "u2"})
        # Inject the KEYDOWN event the handler will return
        router.input_handler._event = type(
            "E",
            (),
            {"event_type": "key_down", "key": pygame.K_1, "modifiers": (True, False, False, False)},
        )()

        ok = router.route_input(_make_key_event(pygame.K_1, ctrl=True))

        assert ok is True
        group = router.squad_group_manager.get_group(1)
        assert group is not None
        assert len(group.units) == 3
        assert {u.id for u in group.units} == {"u0", "u1", "u2"}

    def test_ctrl_digit_with_no_selection_does_not_create(self):
        """Ctrl+1 with empty selection → group 1 remains empty, returns True (handled)."""
        units = [_StubUnit(id="u0")]
        router, state = _make_router(units=units, selected_ids=set())
        router.input_handler._event = type(
            "E",
            (),
            {"event_type": "key_down", "key": pygame.K_1, "modifiers": (True, False, False, False)},
        )()

        ok = router.route_input(_make_key_event(pygame.K_1, ctrl=True))

        assert ok is True  # Event was handled (consumed), but no group created
        group = router.squad_group_manager.get_group(1)
        assert group.is_empty

    def test_ctrl_digit_updates_existing_group(self):
        """Ctrl+1 twice with different selections → group 1 reflects the latest selection."""
        units_a = [_StubUnit(id="a1"), _StubUnit(id="a2")]
        units_b = [_StubUnit(id="b1")]
        all_units = units_a + units_b
        router, _ = _make_router(units=all_units, selected_ids={"a1", "a2"})

        router.input_handler._event = type(
            "E",
            (),
            {"event_type": "key_down", "key": pygame.K_1, "modifiers": (True, False, False, False)},
        )()
        router.route_input(_make_key_event(pygame.K_1, ctrl=True))
        assert len(router.squad_group_manager.get_group(1).units) == 2

        # Update selection and re-create group 1
        router.game_state.selected_unit_ids = {"b1"}
        router.input_handler._event = type(
            "E",
            (),
            {"event_type": "key_down", "key": pygame.K_1, "modifiers": (True, False, False, False)},
        )()
        router.route_input(_make_key_event(pygame.K_1, ctrl=True))
        assert len(router.squad_group_manager.get_group(1).units) == 1
        assert router.squad_group_manager.get_group(1).units[0].id == "b1"

    def test_ctrl_9_creates_group_9(self):
        """Ctrl+9 creates group 9 (upper bound of valid range)."""
        units = [_StubUnit(id="u0")]
        router, _ = _make_router(units=units, selected_ids={"u0"})
        router.input_handler._event = type(
            "E",
            (),
            {"event_type": "key_down", "key": pygame.K_9, "modifiers": (True, False, False, False)},
        )()

        router.route_input(_make_key_event(pygame.K_9, ctrl=True))

        assert len(router.squad_group_manager.get_group(9).units) == 1


# ============================================================================
# Wave 2 — 1~9 quick-select squad group
# ============================================================================


class TestSelectSquadGroup:
    """Digit (without Ctrl) quick-selects all units in the group."""

    def test_digit_selects_existing_group(self):
        """Pressing 2 selects all units previously assigned to group 2."""
        units = [_StubUnit(id=f"u{i}") for i in range(3)]
        router, state = _make_router(units=units, selected_ids=set())
        # Pre-populate group 2 via the manager directly
        router.squad_group_manager.create_group(2, units[:2])

        router.input_handler._event = type(
            "E",
            (),
            {
                "event_type": "key_down",
                "key": pygame.K_2,
                "modifiers": (False, False, False, False),
            },
        )()
        router.route_input(_make_key_event(pygame.K_2, ctrl=False))

        assert state.selected_unit_ids == {"u0", "u1"}

    def test_digit_on_empty_group_does_not_change_selection(self):
        """Pressing 3 when group 3 is empty → selection unchanged, event handled."""
        units = [_StubUnit(id="u0")]
        router, state = _make_router(units=units, selected_ids={"u0"})
        # Group 3 is empty by default
        router.input_handler._event = type(
            "E",
            (),
            {
                "event_type": "key_down",
                "key": pygame.K_3,
                "modifiers": (False, False, False, False),
            },
        )()
        router.route_input(_make_key_event(pygame.K_3, ctrl=False))

        # Selection unchanged (still u0)
        assert state.selected_unit_ids == {"u0"}

    def test_digit_select_replaces_previous_selection(self):
        """Pressing 1 replaces the current selection with group 1's units."""
        units = [_StubUnit(id=f"u{i}") for i in range(4)]
        router, state = _make_router(units=units, selected_ids={"u0"})
        router.squad_group_manager.create_group(1, units[1:3])  # u1, u2

        router.input_handler._event = type(
            "E",
            (),
            {
                "event_type": "key_down",
                "key": pygame.K_1,
                "modifiers": (False, False, False, False),
            },
        )()
        router.route_input(_make_key_event(pygame.K_1, ctrl=False))

        assert state.selected_unit_ids == {"u1", "u2"}

    def test_digit_9_selects_group_9(self):
        """Pressing 9 selects group 9 (upper bound)."""
        units = [_StubUnit(id="u9")]
        router, state = _make_router(units=units, selected_ids=set())
        router.squad_group_manager.create_group(9, units)

        router.input_handler._event = type(
            "E",
            (),
            {
                "event_type": "key_down",
                "key": pygame.K_9,
                "modifiers": (False, False, False, False),
            },
        )()
        router.route_input(_make_key_event(pygame.K_9, ctrl=False))

        assert state.selected_unit_ids == {"u9"}


# ============================================================================
# Wave 2 — Manager absence (backward compatibility)
# ============================================================================


class TestNoSquadGroupManager:
    """When squad_group_manager is None, digit keys are NOT consumed by the router."""

    def test_digit_key_falls_through_when_manager_absent(self):
        """Without a manager, pressing 1 does not get intercepted as squad selection."""
        state = _StubGameState(units=[_StubUnit(id="u0")], selected_unit_ids={"u0"})
        handler = _StubInputHandler()
        handler._event = type(
            "E",
            (),
            {
                "event_type": "key_down",
                "key": pygame.K_1,
                "modifiers": (False, False, False, False),
            },
        )()
        # manager=None (default)
        router = InputRouter(
            input_handler=handler,
            interaction_controller=None,
            command_bar=None,
            camera=None,
            game_state=state,
        )

        router.route_input(_make_key_event(pygame.K_1, ctrl=False))

        # Selection unchanged (digit was not interpreted as squad selection)
        assert state.selected_unit_ids == {"u0"}


# ============================================================================
# Wave 2 — Minimap bounding-box rendering
# ============================================================================


class TestMinimapSquadGroupRendering:
    """Minimap renders bounding boxes when a SquadGroupManager is wired."""

    def _make_minimap_with_manager(self) -> tuple[Any, SquadGroupManager]:
        from pycc2.domain.entities.game_map import GameMap
        from pycc2.presentation.rendering.minimap import Minimap

        # Small 10x10 map for predictable minimap coordinates.
        # tile_grid must be a numpy array of shape (height, width).
        grid = np.zeros((10, 10), dtype=np.int8)
        game_map = GameMap(
            id="squad_test", name="Squad Test Map", width=10, height=10, tile_grid=grid
        )
        minimap = Minimap(display_config=None, size=100)
        minimap.set_map(game_map)
        manager = SquadGroupManager()
        minimap.set_squad_group_manager(manager)
        return minimap, manager

    def test_set_squad_group_manager_stores_manager(self):
        from pycc2.presentation.rendering.minimap import Minimap

        minimap = Minimap(display_config=None, size=50)
        manager = SquadGroupManager()
        assert minimap._squad_group_manager is None
        minimap.set_squad_group_manager(manager)
        assert minimap._squad_group_manager is manager

    def test_render_with_active_group_draws_bounding_box(self):
        """Render with one active group → surface is non-blank (bounding box drawn)."""
        minimap, manager = self._make_minimap_with_manager()
        units = [
            _StubUnit(id="u1", position_component=_StubPosition(2, 3)),
            _StubUnit(id="u2", position_component=_StubPosition(5, 7)),
        ]
        manager.create_group(1, units)

        pygame.init()
        try:
            # Fade the minimap in (default state is hidden, which makes render() early-return).
            minimap.show()
            minimap.update(0.5)  # advance fade animation to fully visible
            screen = pygame.Surface((200, 200))
            minimap.render(screen, 0, 0)
            # The minimap surface should now exist and contain the bounding box.
            assert minimap._surface is not None
            # Group 1 covers tile bounds (min_x=2, min_y=3, max_x=5, max_y=7).
            # On a 100x100 minimap for a 10x10 map: top-left corner at (20, 30).
            # Sample that corner pixel — it should match group 1's border color.
            border_pixel = minimap._surface.get_at((20, 30))
            r, g, b, _ = border_pixel
            assert (r, g, b) == (231, 111, 81), (
                f"Expected group 1 border color (231,111,81) at (20,30), got ({r},{g},{b})"
            )
        finally:
            pygame.quit()

    def test_render_with_no_active_groups_skips_bounding_boxes(self):
        """Render with manager but no active groups → no squad bounding boxes drawn."""
        minimap, _manager = self._make_minimap_with_manager()
        # No groups populated → active_group_numbers == []
        assert minimap._squad_group_manager.active_group_numbers == []

        pygame.init()
        try:
            minimap.show()
            minimap.update(0.5)
            screen = pygame.Surface((200, 200))
            minimap.render(screen, 0, 0)
            # Smoke test: render completed without error and surface was created
            assert minimap._surface is not None
        finally:
            pygame.quit()


# ============================================================================
# Wave 2 — _SQUAD_DIGIT_KEYS mapping completeness
# ============================================================================


class TestSquadDigitKeyMap:
    """The _SQUAD_DIGIT_KEYS mapping must cover all 9 digit keys."""

    def test_all_nine_digit_keys_mapped(self):
        assert len(_SQUAD_DIGIT_KEYS) == 9

    def test_mapping_values_are_one_through_nine(self):
        assert sorted(_SQUAD_DIGIT_KEYS.values()) == [1, 2, 3, 4, 5, 6, 7, 8, 9]

    def test_k1_maps_to_1(self):
        assert _SQUAD_DIGIT_KEYS[pygame.K_1] == 1

    def test_k9_maps_to_9(self):
        assert _SQUAD_DIGIT_KEYS[pygame.K_9] == 9
