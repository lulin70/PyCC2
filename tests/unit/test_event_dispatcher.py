"""Unit tests for EventDispatcher (event_dispatcher module).

Verify that pygame events are routed to the correct handler based on the
current UI/game state, and that each private handler consumes or forwards
events according to its contract.

Uses real pygame event objects (constructed via ``pygame.event.Event``) and
lightweight fake classes for the dispatcher's collaborators (pause menu,
deployment manager, input router, etc.). The real ``EventBus`` and
``DisplayConfig`` domain objects are used directly.

Covers dimensions: Happy Path, Error Case, Boundary, Performance, Integration.
"""

from __future__ import annotations

import os
import time

# Ensure headless pygame before any pygame import.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from pycc2.domain.interfaces.display_config import DisplayConfig  # noqa: E402
from pycc2.infrastructure.events.event_bus import EventBus  # noqa: E402
from pycc2.infrastructure.events.event_dispatcher import EventDispatcher  # noqa: E402

# Ensure pygame is initialized so pygame.event.Event construction and the
# event queue (post/get) work in the headless environment.
if not pygame.get_init():
    pygame.init()
try:
    pygame.display.set_mode((1, 1))
except Exception:
    pass


# ===========================================================================
# Lightweight fake collaborators
# ===========================================================================


class FakeCamera:
    """Minimal camera stand-in passed to minimap.handle_click."""


class FakeGameState:
    """Minimal game-state fake with running/pauted/camera attributes."""

    def __init__(self):
        self.running = True
        self.paused = False
        self.camera = FakeCamera()


class FakePauseMenu:
    """Fake pause menu tracking toggle/deactivate/click calls."""

    def __init__(self, is_active: bool = False, click_action: str | None = None):
        self._is_active = is_active
        self.click_action = click_action
        self.toggle_count = 0
        self.deactivate_count = 0
        self.mouse_updates: list = []

    @property
    def is_active(self) -> bool:
        return self._is_active

    def toggle(self) -> None:
        self._is_active = not self._is_active
        self.toggle_count += 1

    def deactivate(self) -> None:
        self._is_active = False
        self.deactivate_count += 1

    def update_mouse(self, mouse_pos) -> None:
        self.mouse_updates.append(mouse_pos)

    def handle_click(self, mouse_pos) -> str | None:
        return self.click_action


class FakeDeploymentUI:
    """Fake deployment UI tracking all mouse handler calls."""

    def __init__(
        self,
        mouse_down_result: str | None = None,
        click_full_result: str | None = None,
        mouse_up_result: str | None = None,
    ):
        self.mouse_down_result = mouse_down_result
        self.click_full_result = click_full_result
        self.mouse_up_result = mouse_up_result
        self.mouse_down_calls: list[dict] = []
        self.click_full_calls: list[dict] = []
        self.mouse_up_calls: list[dict] = []
        self.mouse_move_calls: list[dict] = []
        self.hover_calls: list[tuple] = []

    def handle_mouse_down(self, x, y, map_offset_x=0, map_offset_y=0, tile_size=16):
        self.mouse_down_calls.append({"x": x, "y": y, "tile_size": tile_size})
        return self.mouse_down_result

    def handle_click_full(
        self, x, y, map_offset_x=0, map_offset_y=0, tile_size=16, right_click=False
    ):
        self.click_full_calls.append(
            {"x": x, "y": y, "tile_size": tile_size, "right_click": right_click}
        )
        return self.click_full_result

    def handle_mouse_up(self, x, y, map_offset_x=0, map_offset_y=0, tile_size=16):
        self.mouse_up_calls.append({"x": x, "y": y, "tile_size": tile_size})
        return self.mouse_up_result

    def handle_mouse_move(self, x, y, map_offset_x=0, map_offset_y=0, tile_size=16):
        self.mouse_move_calls.append({"x": x, "y": y, "tile_size": tile_size})

    def update_button_hover(self, mouse_x, mouse_y) -> None:
        self.hover_calls.append((mouse_x, mouse_y))


class FakeDeploymentManager:
    """Fake deployment manager with settable active state and UI."""

    def __init__(self, is_active: bool = False, deployment_ui=None):
        self._is_active = is_active
        self.deployment_ui = deployment_ui
        self.pending_orders: list[tuple] = []

    @property
    def is_active(self) -> bool:
        return self._is_active

    def set_pending_order(self, unit_id, tx, ty) -> None:
        self.pending_orders.append((unit_id, tx, ty))


class FakeInputRouter:
    """Fake input router tracking route_input calls and show_post_battle."""

    def __init__(self, route_result=None, raise_exc: Exception | None = None):
        self._route_result = route_result
        self._raise_exc = raise_exc
        self.show_post_battle = False
        self.route_calls: list = []

    def route_input(self, event):
        self.route_calls.append(event)
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._route_result


class FakeWindowManager:
    """Fake window manager; handle_event returns configurable quit flag."""

    def __init__(self, should_quit: bool = False):
        self._should_quit = should_quit
        self.handle_calls: list = []

    def handle_event(self, event) -> bool:
        self.handle_calls.append(event)
        return self._should_quit


class FakeSettingsMenu:
    """Fake settings menu tracking toggle/handle_input/apply_to_systems."""

    def __init__(self, visible: bool = False, input_result: str | None = None):
        self._visible = visible
        self.input_result = input_result
        self.toggle_count = 0
        self.input_calls: list = []
        self.apply_calls: list = []

    @property
    def visible(self) -> bool:
        return self._visible

    def toggle(self) -> None:
        self._visible = not self._visible
        self.toggle_count += 1

    def handle_input(self, event, mouse_pos):
        self.input_calls.append((event, mouse_pos))
        return self.input_result

    def apply_to_systems(self, sound_system=None, display_config=None):
        self.apply_calls.append({"sound": sound_system, "display": display_config})
        return None


class FakeTutorialOverlay:
    """Fake tutorial overlay tracking toggle/handle_input."""

    def __init__(self, visible: bool = False):
        self._visible = visible
        self.toggle_count = 0
        self.input_calls: list = []

    @property
    def visible(self) -> bool:
        return self._visible

    def toggle(self) -> None:
        self._visible = not self._visible
        self.toggle_count += 1

    def handle_input(self, event):
        self.input_calls.append(event)
        return None


class FakeMinimap:
    """Fake minimap tracking contains_point/handle_click."""

    def __init__(self, contains: bool = False):
        self._contains = contains
        self.contains_calls: list = []
        self.click_calls: list = []

    def contains_point(self, screen_pos) -> bool:
        self.contains_calls.append(screen_pos)
        return self._contains

    def handle_click(self, screen_pos, camera) -> bool:
        self.click_calls.append((screen_pos, camera))
        return True


class FakeHUDManager:
    """Fake HUD manager tracking mouse pos/pressed and minimap delegation."""

    def __init__(self, minimap=None):
        self._minimap = minimap
        self.mouse_pos_calls: list = []
        self.mouse_pressed_calls: list[bool] = []

    @property
    def minimap(self):
        return self._minimap

    def set_mouse_pos(self, mouse_pos) -> None:
        self.mouse_pos_calls.append(mouse_pos)

    def set_mouse_pressed(self, pressed: bool) -> None:
        self.mouse_pressed_calls.append(pressed)


class FakeTimeControlUI:
    """Fake time-control UI tracking handle_key calls."""

    def __init__(self, handled: bool = False):
        self._handled = handled
        self.key_calls: list[int] = []

    def handle_key(self, key) -> bool:
        self.key_calls.append(key)
        return self._handled


class FakeCampaignUI:
    """Fake campaign UI tracking mouse/scroll/click calls."""

    def __init__(self, is_visible: bool = True):
        self._is_visible = is_visible
        self.mouse_move_calls: list = []
        self.click_calls: list = []
        self.scroll_calls: list = []

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    def handle_mouse_move(self, pos) -> None:
        self.mouse_move_calls.append(pos)

    def handle_click(self, pos) -> None:
        self.click_calls.append(pos)

    def handle_scroll(self, y) -> None:
        self.scroll_calls.append(y)


class FakeVictoryManager:
    """Fake victory manager exposing show_post_battle."""

    def __init__(self, show_post_battle: bool = False):
        self._show_post_battle = show_post_battle

    @property
    def show_post_battle(self) -> bool:
        return self._show_post_battle


# ===========================================================================
# Event construction helpers
# ===========================================================================


def _key_event(key: int):
    """Construct a KEYDOWN pygame event with the given key."""
    return pygame.event.Event(pygame.KEYDOWN, {"key": key})


def _mouse_down(pos=(10, 10), button: int = 1):
    """Construct a MOUSEBUTTONDOWN event."""
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": button})


def _mouse_up(pos=(10, 10), button: int = 1):
    """Construct a MOUSEBUTTONUP event."""
    return pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": button})


def _mouse_motion(pos=(10, 10)):
    """Construct a MOUSEMOTION event."""
    return pygame.event.Event(pygame.MOUSEMOTION, {"pos": pos})


def _mouse_wheel(y: int = 1):
    """Construct a MOUSEWHEEL event."""
    return pygame.event.Event(pygame.MOUSEWHEEL, {"y": y})


def _quit_event():
    """Construct a QUIT event."""
    return pygame.event.Event(pygame.QUIT)


def _user_event():
    """Construct a neutral USEREVENT that no handler claims."""
    return pygame.event.Event(pygame.USEREVENT)


# ===========================================================================
# Dispatcher factory
# ===========================================================================


def _make_dispatcher(**overrides) -> tuple[EventDispatcher, dict]:
    """Build an EventDispatcher with all fake collaborators.

    Returns the dispatcher and a dict of the fakes for assertions.
    Any keyword in ``overrides`` replaces the corresponding fake.
    """
    state = overrides.get("state", FakeGameState())
    pause_menu = overrides.get("pause_menu", FakePauseMenu())
    deployment_ui = overrides.get("deployment_ui", FakeDeploymentUI())
    deployment_manager = overrides.get(
        "deployment_manager", FakeDeploymentManager(deployment_ui=deployment_ui)
    )
    input_router = overrides.get("input_router", FakeInputRouter())
    time_control = overrides.get("time_control")
    window_manager = overrides.get("window_manager", FakeWindowManager())
    settings_menu = overrides.get("settings_menu")
    tutorial_overlay = overrides.get("tutorial_overlay")
    hud_manager = overrides.get("hud_manager")
    sound_system = overrides.get("sound_system")
    event_bus = overrides.get("event_bus", EventBus())
    display_config = overrides.get("display_config")
    victory_manager = overrides.get("victory_manager")
    campaign_ui = overrides.get("campaign_ui")

    dispatcher = EventDispatcher(
        state=state,
        pause_menu=pause_menu,
        deployment_manager=deployment_manager,
        input_router=input_router,
        time_control=time_control,
        window_manager=window_manager,
        settings_menu=settings_menu,
        tutorial_overlay=tutorial_overlay,
        hud_manager=hud_manager,
        sound_system=sound_system,
        event_bus=event_bus,
        display_config=display_config,
        victory_manager=victory_manager,
        _campaign_ui_ref=campaign_ui,
        quick_save_fn=overrides.get("quick_save_fn"),
        quick_load_fn=overrides.get("quick_load_fn"),
        complete_deployment_fn=overrides.get("complete_deployment_fn"),
    )
    fakes = {
        "state": state,
        "pause_menu": pause_menu,
        "deployment_ui": deployment_ui,
        "deployment_manager": deployment_manager,
        "input_router": input_router,
        "window_manager": window_manager,
    }
    return dispatcher, fakes


# ===========================================================================
# process_events (public API)
# ===========================================================================


@pytest.mark.unit
class TestProcessEvents:
    """Verify the public process_events dispatch loop."""

    def test_empty_queue_returns_true(self, monkeypatch):
        """Verify: no events → returns True (keep running), running unchanged."""
        d, _ = _make_dispatcher()
        monkeypatch.setattr(pygame.event, "get", lambda: [])
        assert d.process_events() is True
        assert d.state.running is True

    def test_quit_event_stops_loop(self, monkeypatch):
        """Verify: window_manager signals quit → running=False, returns False."""
        wm = FakeWindowManager(should_quit=True)
        d, _ = _make_dispatcher(window_manager=wm)
        monkeypatch.setattr(pygame.event, "get", lambda: [_quit_event()])
        assert d.process_events() is False
        assert d.state.running is False

    def test_campaign_ui_consumes_event(self, monkeypatch):
        """Verify: visible campaign UI consumes the event and continues."""
        campaign = FakeCampaignUI(is_visible=True)
        d, _ = _make_dispatcher(campaign_ui=campaign)
        monkeypatch.setattr(pygame.event, "get", lambda: [_mouse_motion(pos=(5, 5))])
        assert d.process_events() is True
        assert campaign.mouse_move_calls == [(5, 5)]

    def test_battle_input_fallthrough_returns_true(self, monkeypatch):
        """Verify: unclaimed event falls through to battle input, returns True."""
        d, fakes = _make_dispatcher()
        monkeypatch.setattr(pygame.event, "get", lambda: [_user_event()])
        assert d.process_events() is True
        # battle input routed the event
        assert len(fakes["input_router"].route_calls) == 1

    def test_multiple_events_all_processed(self, monkeypatch):
        """Verify: multiple events are each dispatched in order."""
        d, fakes = _make_dispatcher()
        events = [_user_event(), _user_event(), _user_event()]
        monkeypatch.setattr(pygame.event, "get", lambda: events)
        assert d.process_events() is True
        assert len(fakes["input_router"].route_calls) == 3

    def test_quit_in_middle_stops_immediately(self, monkeypatch):
        """Verify: a quit event mid-queue stops processing remaining events."""
        wm = FakeWindowManager(should_quit=True)
        d, fakes = _make_dispatcher(window_manager=wm)
        # The first event triggers quit; the second should never be processed.
        events = [_quit_event(), _user_event()]
        monkeypatch.setattr(pygame.event, "get", lambda: events)
        assert d.process_events() is False
        assert len(fakes["input_router"].route_calls) == 0


# ===========================================================================
# _handle_campaign_ui
# ===========================================================================


@pytest.mark.unit
class TestHandleCampaignUI:
    """Verify campaign UI event consumption."""

    def test_none_campaign_ui_returns_false(self):
        """Verify: no campaign UI → event not consumed."""
        d, _ = _make_dispatcher(campaign_ui=None)
        assert d._handle_campaign_ui(_mouse_motion()) is False

    def test_hidden_campaign_ui_returns_false(self):
        """Verify: invisible campaign UI → event not consumed."""
        campaign = FakeCampaignUI(is_visible=False)
        d, _ = _make_dispatcher(campaign_ui=campaign)
        assert d._handle_campaign_ui(_mouse_motion()) is False

    def test_mouse_motion_consumed(self):
        """Verify: MOUSEMOTION on visible campaign UI is forwarded and consumed."""
        campaign = FakeCampaignUI(is_visible=True)
        d, _ = _make_dispatcher(campaign_ui=campaign)
        assert d._handle_campaign_ui(_mouse_motion(pos=(3, 4))) is True
        assert campaign.mouse_move_calls == [(3, 4)]

    def test_left_click_consumed(self):
        """Verify: left MOUSEBUTTONDOWN on visible campaign UI is forwarded."""
        campaign = FakeCampaignUI(is_visible=True)
        d, _ = _make_dispatcher(campaign_ui=campaign)
        assert d._handle_campaign_ui(_mouse_down(pos=(7, 8), button=1)) is True
        assert campaign.click_calls == [(7, 8)]

    def test_mousewheel_consumed(self):
        """Verify: MOUSEWHEEL on visible campaign UI is forwarded."""
        campaign = FakeCampaignUI(is_visible=True)
        d, _ = _make_dispatcher(campaign_ui=campaign)
        assert d._handle_campaign_ui(_mouse_wheel(y=2)) is True
        assert campaign.scroll_calls == [2]

    def test_other_event_still_consumed(self):
        """Verify: visible campaign UI consumes ALL events (even unhandled ones)."""
        campaign = FakeCampaignUI(is_visible=True)
        d, _ = _make_dispatcher(campaign_ui=campaign)
        assert d._handle_campaign_ui(_user_event()) is True

    def test_right_click_not_forwarded_but_consumed(self):
        """Verify: right-click is not handled_click but still consumed (falls to True)."""
        campaign = FakeCampaignUI(is_visible=True)
        d, _ = _make_dispatcher(campaign_ui=campaign)
        assert d._handle_campaign_ui(_mouse_down(button=3)) is True
        assert campaign.click_calls == []  # right click not forwarded


# ===========================================================================
# _handle_settings_menu
# ===========================================================================


@pytest.mark.unit
class TestHandleSettingsMenu:
    """Verify settings menu event consumption."""

    def test_none_settings_menu_returns_false(self):
        """Verify: no settings menu → event not consumed."""
        d, _ = _make_dispatcher(settings_menu=None)
        assert d._handle_settings_menu(_user_event()) is False

    def test_hidden_settings_menu_returns_false(self):
        """Verify: invisible settings menu → event not consumed."""
        menu = FakeSettingsMenu(visible=False)
        d, _ = _make_dispatcher(settings_menu=menu)
        assert d._handle_settings_menu(_user_event()) is False

    def test_visible_menu_consumes_and_forwards(self):
        """Verify: visible menu forwards event+mouse_pos to handle_input."""
        menu = FakeSettingsMenu(visible=True, input_result="ignored")
        d, _ = _make_dispatcher(settings_menu=menu)
        assert d._handle_settings_menu(_user_event()) is True
        assert len(menu.input_calls) == 1

    def test_applied_result_calls_apply_to_systems(self):
        """Verify: handle_input returns 'applied' → apply_to_systems invoked with sound."""
        menu = FakeSettingsMenu(visible=True, input_result="applied")
        sound = object()
        d, _ = _make_dispatcher(settings_menu=menu, sound_system=sound)
        assert d._handle_settings_menu(_user_event()) is True
        assert menu.apply_calls == [{"sound": sound, "display": None}]

    def test_non_applied_result_skips_apply(self):
        """Verify: result other than 'applied' does not call apply_to_systems."""
        menu = FakeSettingsMenu(visible=True, input_result="cancelled")
        d, _ = _make_dispatcher(settings_menu=menu)
        d._handle_settings_menu(_user_event())
        assert menu.apply_calls == []


# ===========================================================================
# _handle_global_keys
# ===========================================================================


@pytest.mark.unit
class TestHandleGlobalKeys:
    """Verify global keyboard shortcut routing."""

    def test_non_keydown_returns_false(self):
        """Verify: non-keyboard events are not consumed."""
        d, _ = _make_dispatcher()
        assert d._handle_global_keys(_mouse_motion()) is False

    def test_f10_toggles_settings_menu(self):
        """Verify: F10 toggles the settings menu when present."""
        menu = FakeSettingsMenu(visible=False)
        d, _ = _make_dispatcher(settings_menu=menu)
        assert d._handle_global_keys(_key_event(pygame.K_F10)) is True
        assert menu.toggle_count == 1

    def test_f10_without_settings_menu_still_consumed(self):
        """Verify: F10 with no settings menu is still consumed (returns True)."""
        d, _ = _make_dispatcher(settings_menu=None)
        assert d._handle_global_keys(_key_event(pygame.K_F10)) is True

    def test_f5_triggers_quick_save(self):
        """Verify: F5 calls quick_save_fn(0)."""
        saved: list[int] = []
        d, _ = _make_dispatcher(quick_save_fn=lambda slot: saved.append(slot) or True)
        assert d._handle_global_keys(_key_event(pygame.K_F5)) is True
        assert saved == [0]

    def test_f5_without_save_fn_still_consumed(self):
        """Verify: F5 with no quick_save_fn is still consumed."""
        d, _ = _make_dispatcher(quick_save_fn=None)
        assert d._handle_global_keys(_key_event(pygame.K_F5)) is True

    def test_f9_triggers_quick_load(self):
        """Verify: F9 calls quick_load_fn(0)."""
        loaded: list[int] = []
        d, _ = _make_dispatcher(quick_load_fn=lambda slot: loaded.append(slot) or True)
        assert d._handle_global_keys(_key_event(pygame.K_F9)) is True
        assert loaded == [0]

    def test_f9_without_load_fn_still_consumed(self):
        """Verify: F9 with no quick_load_fn is still consumed."""
        d, _ = _make_dispatcher(quick_load_fn=None)
        assert d._handle_global_keys(_key_event(pygame.K_F9)) is True

    def test_f1_toggles_tutorial(self):
        """Verify: F1 toggles the tutorial overlay when present."""
        tut = FakeTutorialOverlay(visible=False)
        d, _ = _make_dispatcher(tutorial_overlay=tut)
        assert d._handle_global_keys(_key_event(pygame.K_F1)) is True
        assert tut.toggle_count == 1

    def test_f1_without_tutorial_still_consumed(self):
        """Verify: F1 with no tutorial overlay is still consumed."""
        d, _ = _make_dispatcher(tutorial_overlay=None)
        assert d._handle_global_keys(_key_event(pygame.K_F1)) is True

    def test_escape_closes_visible_settings_menu(self):
        """Verify: ESC closes settings menu when it is visible."""
        menu = FakeSettingsMenu(visible=True)
        d, _ = _make_dispatcher(settings_menu=menu)
        assert d._handle_global_keys(_key_event(pygame.K_ESCAPE)) is True
        assert menu.toggle_count == 1
        # Pause menu NOT toggled when settings menu handles ESC
        assert d.pause_menu.toggle_count == 0

    def test_escape_toggles_pause_menu_when_settings_closed(self):
        """Verify: ESC toggles pause menu when settings menu is absent."""
        pause = FakePauseMenu(is_active=False)
        d, _ = _make_dispatcher(pause_menu=pause, settings_menu=None)
        assert d._handle_global_keys(_key_event(pygame.K_ESCAPE)) is True
        assert pause.toggle_count == 1

    def test_escape_sets_paused_when_pause_menu_activates(self):
        """Verify: ESC activating the pause menu sets state.paused=True."""
        # toggle() flips False→True
        pause = FakePauseMenu(is_active=False)
        state = FakeGameState()
        d, _ = _make_dispatcher(state=state, pause_menu=pause)
        d._handle_global_keys(_key_event(pygame.K_ESCAPE))
        assert state.paused is True

    def test_escape_does_not_set_paused_when_pause_menu_inactive(self):
        """Verify: ESC when pause menu ends up inactive leaves paused unchanged."""
        # toggle() flips True→False, so is_active ends False
        pause = FakePauseMenu(is_active=True)
        state = FakeGameState()
        d, _ = _make_dispatcher(state=state, pause_menu=pause)
        state.paused = True
        d._handle_global_keys(_key_event(pygame.K_ESCAPE))
        assert state.paused is True  # unchanged because pause_menu.is_active is now False
        assert pause.is_active is False

    def test_unmapped_key_returns_false(self):
        """Verify: an unmapped key is not consumed by global keys."""
        d, _ = _make_dispatcher()
        assert d._handle_global_keys(_key_event(pygame.K_SPACE)) is False


# ===========================================================================
# _handle_tutorial
# ===========================================================================


@pytest.mark.unit
class TestHandleTutorial:
    """Verify tutorial overlay event consumption."""

    def test_none_tutorial_returns_false(self):
        """Verify: no tutorial overlay → not consumed."""
        d, _ = _make_dispatcher(tutorial_overlay=None)
        assert d._handle_tutorial(_user_event()) is False

    def test_hidden_tutorial_returns_false(self):
        """Verify: invisible tutorial → not consumed."""
        tut = FakeTutorialOverlay(visible=False)
        d, _ = _make_dispatcher(tutorial_overlay=tut)
        assert d._handle_tutorial(_user_event()) is False

    def test_visible_tutorial_consumes_and_forwards(self):
        """Verify: visible tutorial forwards event to handle_input and consumes."""
        tut = FakeTutorialOverlay(visible=True)
        d, _ = _make_dispatcher(tutorial_overlay=tut)
        ev = _user_event()
        assert d._handle_tutorial(ev) is True
        assert tut.input_calls == [ev]


# ===========================================================================
# _handle_pause_menu
# ===========================================================================


@pytest.mark.unit
class TestHandlePauseMenu:
    """Verify pause menu click/action routing."""

    def test_inactive_pause_menu_returns_false(self):
        """Verify: inactive pause menu → not consumed."""
        d, _ = _make_dispatcher(pause_menu=FakePauseMenu(is_active=False))
        assert d._handle_pause_menu(_user_event()) is False

    def test_active_menu_mouse_motion_updates_mouse(self):
        """Verify: MOUSEMOTION on active pause menu updates mouse hover."""
        pause = FakePauseMenu(is_active=True)
        d, _ = _make_dispatcher(pause_menu=pause)
        assert d._handle_pause_menu(_mouse_motion(pos=(1, 2))) is True
        assert pause.mouse_updates == [(1, 2)]

    def test_resume_action_deactivates_and_unpauses(self):
        """Verify: 'resume' action deactivates menu and clears paused."""
        pause = FakePauseMenu(is_active=True, click_action="resume")
        state = FakeGameState()
        d, _ = _make_dispatcher(state=state, pause_menu=pause)
        state.paused = True
        assert d._handle_pause_menu(_mouse_down(button=1)) is True
        assert pause.deactivate_count == 1
        assert state.paused is False

    def test_save_action_calls_quick_save(self):
        """Verify: 'save' action calls quick_save_fn(0)."""
        pause = FakePauseMenu(is_active=True, click_action="save")
        saved: list[int] = []
        d, _ = _make_dispatcher(pause_menu=pause, quick_save_fn=lambda s: saved.append(s) or True)
        d._handle_pause_menu(_mouse_down(button=1))
        assert saved == [0]

    def test_save_action_without_save_fn_no_crash(self):
        """Error case: 'save' with no quick_save_fn does not raise."""
        pause = FakePauseMenu(is_active=True, click_action="save")
        d, _ = _make_dispatcher(pause_menu=pause, quick_save_fn=None)
        d._handle_pause_menu(_mouse_down(button=1))  # should not raise

    def test_load_action_calls_quick_load_and_deactivates(self):
        """Verify: 'load' action calls quick_load_fn(0) then deactivates."""
        pause = FakePauseMenu(is_active=True, click_action="load")
        loaded: list[int] = []
        d, _ = _make_dispatcher(pause_menu=pause, quick_load_fn=lambda s: loaded.append(s) or True)
        d._handle_pause_menu(_mouse_down(button=1))
        assert loaded == [0]
        assert pause.deactivate_count == 1

    def test_load_action_without_load_fn_deactivates(self):
        """Verify: 'load' with no quick_load_fn still deactivates."""
        pause = FakePauseMenu(is_active=True, click_action="load")
        d, _ = _make_dispatcher(pause_menu=pause, quick_load_fn=None)
        d._handle_pause_menu(_mouse_down(button=1))
        assert pause.deactivate_count == 1

    def test_quit_to_menu_action_stops_running(self):
        """Verify: 'quit_to_menu' action sets running=False."""
        pause = FakePauseMenu(is_active=True, click_action="quit_to_menu")
        state = FakeGameState()
        d, _ = _make_dispatcher(state=state, pause_menu=pause)
        d._handle_pause_menu(_mouse_down(button=1))
        assert state.running is False

    def test_unknown_action_still_consumed(self):
        """Verify: unknown click action is still consumed (returns True)."""
        pause = FakePauseMenu(is_active=True, click_action="noop")
        d, _ = _make_dispatcher(pause_menu=pause)
        assert d._handle_pause_menu(_mouse_down(button=1)) is True

    def test_none_click_action_consumed(self):
        """Boundary: handle_click returning None is still consumed by active menu."""
        pause = FakePauseMenu(is_active=True, click_action=None)
        d, _ = _make_dispatcher(pause_menu=pause)
        assert d._handle_pause_menu(_mouse_down(button=1)) is True


# ===========================================================================
# _handle_deployment_input
# ===========================================================================


@pytest.mark.unit
class TestHandleDeploymentInput:
    """Verify deployment-phase mouse routing."""

    def test_inactive_deployment_returns_false(self):
        """Verify: inactive deployment → not consumed."""
        d, _ = _make_dispatcher(deployment_manager=FakeDeploymentManager(is_active=False))
        assert d._handle_deployment_input(_mouse_down()) is False

    def test_active_but_no_ui_returns_false(self):
        """Verify: active deployment with no UI → not consumed."""
        dm = FakeDeploymentManager(is_active=True, deployment_ui=None)
        d, _ = _make_dispatcher(deployment_manager=dm)
        assert d._handle_deployment_input(_mouse_down()) is False

    def test_left_click_drag_start_skips_click_full(self, monkeypatch):
        """Verify: drag_start result skips handle_click_full (drag handled on MOUSEUP)."""
        ui = FakeDeploymentUI(mouse_down_result="drag_start:unit1")
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        d, _ = _make_dispatcher(deployment_manager=dm)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (20, 30))
        d._handle_deployment_input(_mouse_down(button=1))
        assert len(ui.mouse_down_calls) == 1
        assert ui.click_full_calls == []  # skipped because drag_start

    def test_left_click_begin_battle_calls_complete(self, monkeypatch):
        """Verify: 'begin_battle' result triggers complete_deployment_fn."""
        ui = FakeDeploymentUI(mouse_down_result=None, click_full_result="begin_battle")
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        completed: list[bool] = []
        d, _ = _make_dispatcher(
            deployment_manager=dm, complete_deployment_fn=lambda: completed.append(True)
        )
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (5, 5))
        d._handle_deployment_input(_mouse_down(button=1))
        assert completed == [True]
        assert len(ui.click_full_calls) == 1

    def test_left_click_other_result_no_complete(self, monkeypatch):
        """Verify: non-begin_battle result does not call complete_deployment_fn."""
        ui = FakeDeploymentUI(click_full_result="select_unit")
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        completed: list[bool] = []
        d, _ = _make_dispatcher(
            deployment_manager=dm, complete_deployment_fn=lambda: completed.append(True)
        )
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (5, 5))
        d._handle_deployment_input(_mouse_down(button=1))
        assert completed == []

    def test_left_click_without_complete_fn_no_crash(self, monkeypatch):
        """Error case: begin_battle with no complete_deployment_fn does not raise."""
        ui = FakeDeploymentUI(click_full_result="begin_battle")
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        d, _ = _make_dispatcher(deployment_manager=dm, complete_deployment_fn=None)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (5, 5))
        d._handle_deployment_input(_mouse_down(button=1))  # should not raise

    def test_right_click_set_order_parses_and_sets(self, monkeypatch):
        """Verify: 'set_order:unit_id,tx,ty' result parses and sets pending order."""
        ui = FakeDeploymentUI(click_full_result="set_order:u1,5,10")
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        d, _ = _make_dispatcher(deployment_manager=dm)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (5, 5))
        d._handle_deployment_input(_mouse_down(button=3))
        assert dm.pending_orders == [("u1", 5, 10)]

    def test_right_click_set_order_malformed_no_crash(self, monkeypatch):
        """Error case: malformed 'set_order:bad' raises IndexError, caught silently."""
        ui = FakeDeploymentUI(click_full_result="set_order:bad")
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        d, _ = _make_dispatcher(deployment_manager=dm)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (5, 5))
        d._handle_deployment_input(_mouse_down(button=3))  # should not raise
        assert dm.pending_orders == []

    def test_right_click_set_order_non_integer_no_crash(self, monkeypatch):
        """Error case: non-integer coords raise ValueError, caught silently."""
        ui = FakeDeploymentUI(click_full_result="set_order:u1,abc,def")
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        d, _ = _make_dispatcher(deployment_manager=dm)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (5, 5))
        d._handle_deployment_input(_mouse_down(button=3))  # should not raise
        assert dm.pending_orders == []

    def test_mouse_motion_updates_hover_and_move(self, monkeypatch):
        """Verify: MOUSEMOTION updates button hover and ghost position."""
        ui = FakeDeploymentUI()
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        d, _ = _make_dispatcher(deployment_manager=dm)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (15, 25))
        d._handle_deployment_input(_mouse_motion())
        assert ui.hover_calls == [(15, 25)]
        assert len(ui.mouse_move_calls) == 1

    def test_mouse_up_calls_handle_mouse_up(self, monkeypatch):
        """Verify: MOUSEBUTTONUP (left) calls handle_mouse_up."""
        ui = FakeDeploymentUI()
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        d, _ = _make_dispatcher(deployment_manager=dm)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (40, 50))
        d._handle_deployment_input(_mouse_up(button=1))
        assert len(ui.mouse_up_calls) == 1

    def test_other_event_still_consumed(self):
        """Verify: any event during active deployment is consumed (returns True)."""
        ui = FakeDeploymentUI()
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        d, _ = _make_dispatcher(deployment_manager=dm)
        assert d._handle_deployment_input(_user_event()) is True

    def test_display_config_none_uses_default_tile_size(self, monkeypatch):
        """Boundary: no display_config → tile_size defaults to 16."""
        ui = FakeDeploymentUI(click_full_result="begin_battle")
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        d, _ = _make_dispatcher(deployment_manager=dm, complete_deployment_fn=lambda: None)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (5, 5))
        d._handle_deployment_input(_mouse_down(button=1))
        assert ui.click_full_calls[0]["tile_size"] == 16

    def test_display_config_provides_tile_size(self, monkeypatch):
        """Verify: display_config.base_tile_size is forwarded as tile_size."""
        ui = FakeDeploymentUI(click_full_result="begin_battle")
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        dc = DisplayConfig(base_tile_size=48)
        d, _ = _make_dispatcher(
            deployment_manager=dm, display_config=dc, complete_deployment_fn=lambda: None
        )
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (5, 5))
        d._handle_deployment_input(_mouse_down(button=1))
        assert ui.click_full_calls[0]["tile_size"] == 48


# ===========================================================================
# _handle_battle_input
# ===========================================================================


@pytest.mark.unit
class TestHandleBattleInput:
    """Verify battle-phase input routing to HUD, minimap, and input router."""

    def test_mouse_motion_forwards_to_hud(self):
        """Verify: MOUSEMOTION updates HUD mouse position."""
        hud = FakeHUDManager()
        d, _ = _make_dispatcher(hud_manager=hud)
        d._handle_battle_input(_mouse_motion(pos=(7, 8)))
        assert hud.mouse_pos_calls == [(7, 8)]

    def test_mouse_down_forwards_pressed_true(self):
        """Verify: left MOUSEBUTTONDOWN sets HUD mouse pressed True."""
        hud = FakeHUDManager()
        d, _ = _make_dispatcher(hud_manager=hud)
        d._handle_battle_input(_mouse_down(button=1))
        assert hud.mouse_pressed_calls == [True]

    def test_mouse_up_forwards_pressed_false(self):
        """Verify: left MOUSEBUTTONUP sets HUD mouse pressed False."""
        hud = FakeHUDManager()
        d, _ = _make_dispatcher(hud_manager=hud)
        d._handle_battle_input(_mouse_up(button=1))
        assert hud.mouse_pressed_calls == [False]

    def test_no_hud_manager_no_crash(self):
        """Verify: absent HUD manager does not raise on battle input."""
        d, _ = _make_dispatcher(hud_manager=None)
        d._handle_battle_input(_mouse_motion())  # should not raise

    def test_victory_manager_sets_show_post_battle(self):
        """Verify: victory_manager.show_post_battle propagates to input_router."""
        vm = FakeVictoryManager(show_post_battle=True)
        router = FakeInputRouter()
        d, _ = _make_dispatcher(input_router=router, victory_manager=vm)
        d._handle_battle_input(_user_event())
        assert router.show_post_battle is True

    def test_minimap_click_consumed_early(self, monkeypatch):
        """Verify: left-click on minimap is handled and route_input is skipped."""
        minimap = FakeMinimap(contains=True)
        hud = FakeHUDManager(minimap=minimap)
        router = FakeInputRouter()
        d, _ = _make_dispatcher(hud_manager=hud, input_router=router)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (100, 100))
        d._handle_battle_input(_mouse_down(button=1))
        assert minimap.click_calls == [((100, 100), d.state.camera)]
        assert router.route_calls == []  # not routed

    def test_minimap_click_miss_falls_through_to_router(self, monkeypatch):
        """Verify: click not on minimap is routed to input_router."""
        minimap = FakeMinimap(contains=False)
        hud = FakeHUDManager(minimap=minimap)
        router = FakeInputRouter()
        d, _ = _make_dispatcher(hud_manager=hud, input_router=router)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (100, 100))
        d._handle_battle_input(_mouse_down(button=1))
        assert len(router.route_calls) == 1

    def test_no_minimap_routes_normally(self, monkeypatch):
        """Verify: HUD without minimap routes click to input_router."""
        hud = FakeHUDManager(minimap=None)
        router = FakeInputRouter()
        d, _ = _make_dispatcher(hud_manager=hud, input_router=router)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (100, 100))
        d._handle_battle_input(_mouse_down(button=1))
        assert len(router.route_calls) == 1

    def test_route_input_runtime_error_swallowed(self):
        """Error case: route_input raising RuntimeError is caught and logged."""
        router = FakeInputRouter(raise_exc=RuntimeError("boom"))
        d, _ = _make_dispatcher(input_router=router)
        d._handle_battle_input(_user_event())  # should not raise

    def test_route_input_value_error_swallowed(self):
        """Error case: route_input raising ValueError is caught."""
        router = FakeInputRouter(raise_exc=ValueError("bad"))
        d, _ = _make_dispatcher(input_router=router)
        d._handle_battle_input(_user_event())  # should not raise

    def test_route_input_attribute_error_swallowed(self):
        """Error case: route_input raising AttributeError is caught."""
        router = FakeInputRouter(raise_exc=AttributeError("missing"))
        d, _ = _make_dispatcher(input_router=router)
        d._handle_battle_input(_user_event())  # should not raise

    def test_keydown_handled_by_time_control_calls_handle_key(self):
        """Verify: KEYDOWN is routed AND time_control.handle_key is called.

        Documented actual behavior: ``_handle_battle_input`` routes the event to
        ``input_router.route_input`` FIRST, then checks the KEYDOWN/time_control
        branch at the end. So route_input is always called for KEYDOWN events;
        time_control.handle_key is additionally called for KEYDOWN events.
        """
        tc = FakeTimeControlUI(handled=True)
        router = FakeInputRouter()
        d, _ = _make_dispatcher(time_control=tc, input_router=router)
        d._handle_battle_input(_key_event(pygame.K_SPACE))
        assert tc.key_calls == [pygame.K_SPACE]
        # Event is routed before the time_control check
        assert len(router.route_calls) == 1

    def test_keydown_not_handled_by_time_control_still_routes(self):
        """Verify: KEYDOWN not handled by time_control is still routed to router."""
        tc = FakeTimeControlUI(handled=False)
        router = FakeInputRouter()
        d, _ = _make_dispatcher(time_control=tc, input_router=router)
        d._handle_battle_input(_key_event(pygame.K_SPACE))
        assert tc.key_calls == [pygame.K_SPACE]
        assert len(router.route_calls) == 1

    def test_keydown_without_time_control_routes(self):
        """Verify: KEYDOWN with no time_control routes normally."""
        router = FakeInputRouter()
        d, _ = _make_dispatcher(time_control=None, input_router=router)
        d._handle_battle_input(_key_event(pygame.K_SPACE))
        assert len(router.route_calls) == 1


# ===========================================================================
# Integration: end-to-end event flows
# ===========================================================================


@pytest.mark.unit
class TestEventDispatcherIntegration:
    """End-to-end event-flow scenarios through process_events."""

    def test_full_quit_flow_via_window_manager(self, monkeypatch):
        """Integration: QUIT event → window_manager → running=False → return False."""
        wm = FakeWindowManager(should_quit=True)
        state = FakeGameState()
        d, _ = _make_dispatcher(state=state, window_manager=wm)
        monkeypatch.setattr(pygame.event, "get", lambda: [_quit_event()])
        result = d.process_events()
        assert result is False
        assert state.running is False

    def test_escape_opens_pause_then_resume_flow(self, monkeypatch):
        """Integration: ESC opens pause menu (paused=True); click resume unpauses.

        Scenario: process two event batches:
          1. ESC → pause menu toggles active, paused=True.
          2. Left click on active pause menu returning 'resume' → paused=False.
        """
        pause = FakePauseMenu(is_active=False)
        state = FakeGameState()
        d, _ = _make_dispatcher(state=state, pause_menu=pause)

        # Batch 1: ESC opens pause
        monkeypatch.setattr(pygame.event, "get", lambda: [_key_event(pygame.K_ESCAPE)])
        d.process_events()
        assert pause.is_active is True
        assert state.paused is True

        # Batch 2: click resume
        pause.click_action = "resume"
        monkeypatch.setattr(pygame.event, "get", lambda: [_mouse_down(button=1)])
        d.process_events()
        assert pause.deactivate_count == 1
        assert state.paused is False

    def test_deployment_right_click_sets_pre_battle_order(self, monkeypatch):
        """Integration: right-click during deployment sets a pending order end-to-end."""
        ui = FakeDeploymentUI(click_full_result="set_order:inf1,3,7")
        dm = FakeDeploymentManager(is_active=True, deployment_ui=ui)
        d, _ = _make_dispatcher(deployment_manager=dm)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (5, 5))
        monkeypatch.setattr(pygame.event, "get", lambda: [_mouse_down(pos=(5, 5), button=3)])
        d.process_events()
        assert dm.pending_orders == [("inf1", 3, 7)]

    def test_battle_minimap_click_does_not_route(self, monkeypatch):
        """Integration: minimap click during battle is consumed, not routed to units."""
        minimap = FakeMinimap(contains=True)
        hud = FakeHUDManager(minimap=minimap)
        router = FakeInputRouter()
        d, _ = _make_dispatcher(hud_manager=hud, input_router=router)
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda: (50, 50))
        monkeypatch.setattr(pygame.event, "get", lambda: [_mouse_down(pos=(50, 50), button=1)])
        d.process_events()
        assert len(minimap.click_calls) == 1
        assert router.route_calls == []


# ===========================================================================
# Performance baselines
# ===========================================================================


@pytest.mark.unit
class TestEventDispatcherPerformance:
    """Timing baselines for the event-dispatch hot path."""

    def test_process_empty_queue_under_50ms(self, monkeypatch):
        """Performance: processing an empty event queue is well under 50ms."""
        d, _ = _make_dispatcher()
        monkeypatch.setattr(pygame.event, "get", lambda: [])
        start = time.perf_counter()
        for _ in range(1000):
            d.process_events()
        elapsed = time.perf_counter() - start
        assert elapsed < 2.0  # generous baseline

    def test_handle_global_keys_fast(self):
        """Performance: 5000 global-key checks complete well under 1s."""
        d, _ = _make_dispatcher()
        ev = _key_event(pygame.K_F5)
        start = time.perf_counter()
        for _ in range(5000):
            d._handle_global_keys(ev)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0
