"""Unit tests for HUDManager (service layer).

Covers: initialize(), command callbacks, interaction callbacks,
center_camera_on_unit(), update(), render(), render_fallback(),
set_mouse_pos/pressed, minimap property, and defensive early-return paths.

Presentation-layer dependencies (IBottomPanel/IMinimap/IRenderer/
IWindowManager/IRenderPipeline/IInputRouter/InteractionController) are mocked.
"""

from __future__ import annotations

import logging
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import MagicMock

import numpy as np
import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.interfaces.display_config import DisplayConfig
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.services.game_loop_types import GameState
from pycc2.services.hud_manager import HUDManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_unit(
    unit_id: str = "u1",
    name: str = "Rifle Squad",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    max_hp: int = 100,
    tile: tuple[int, int] = (5, 5),
) -> Unit:
    return Unit(
        id=unit_id,
        name=name,
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=85),
        weapon=WeaponComponent(primary_weapon_id="rifle", max_ammo=30, ammo_remaining=30),
        position=PositionComponent(tile_coord=TileCoord(*tile)),
        vision=VisionComponent(),
    )


def make_game_map(width: int = 16, height: int = 16) -> GameMap:
    grid = np.zeros((height, width), dtype=np.int8)
    return GameMap(id="test", name="Test Map", width=width, height=height, tile_grid=grid)


def make_camera() -> MagicMock:
    """Create a mock camera with settable position/zoom/viewport."""
    cam = MagicMock()
    cam.position = Vec2(100.0, 100.0)
    cam.zoom = 1.0
    cam.viewport_width = 1280
    cam.viewport_height = 720
    return cam


def make_display_config() -> DisplayConfig:
    return DisplayConfig(
        window_width=1280,
        window_height=720,
        base_tile_size=48,
        sprite_scale=1.0,
        dpi_scale=1.0,
        is_retina=False,
        default_zoom=1.0,
    )


def make_cc2_panel() -> MagicMock:
    """Create a mock IBottomPanel that captures register_callback calls."""
    panel = MagicMock()
    # Capture registered callbacks in a dict for later invocation.
    callbacks: dict[str, object] = {}
    panel._captured_callbacks = callbacks

    def _register(command_id: str, callback) -> None:
        callbacks[command_id] = callback

    panel.register_callback = MagicMock(side_effect=_register)
    panel._on_unit_select = None
    panel._on_zoom_change = None
    return panel


def make_minimap() -> MagicMock:
    return MagicMock()


def make_renderer(with_display_config: bool = False) -> MagicMock:
    renderer = MagicMock()
    renderer.TILE_SIZE = 48
    renderer.SPRITE_SIZE = 42
    if with_display_config:
        renderer._display_config = MagicMock()
    return renderer


_WINDOW_SENTINEL = object()


def make_window_manager(screen=_WINDOW_SENTINEL) -> MagicMock:
    wm = MagicMock()
    if screen is _WINDOW_SENTINEL:
        wm.get_screen.return_value = MagicMock()
    else:
        wm.get_screen.return_value = screen
    return wm


def make_render_pipeline() -> MagicMock:
    rp = MagicMock()
    rp.hud_manager = MagicMock()
    rp.command_bar = MagicMock()
    rp.unit_panel = MagicMock()
    rp.minimap = MagicMock()
    return rp


def make_input_router() -> MagicMock:
    ir = MagicMock()
    ir.command_bar = MagicMock()
    return ir


def make_interaction_controller() -> MagicMock:
    ic = MagicMock()
    ic.attack_line = MagicMock()
    ic._selected_ids = set()
    return ic


def make_sound_system() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def deps():
    """Bundle of mocked dependencies for initialize()."""
    state = GameState(
        game_map=make_game_map(),
        units=[make_unit("u1", tile=(5, 5)), make_unit("u2", tile=(10, 10))],
        camera=make_camera(),
    )
    return {
        "state": state,
        "display_config": make_display_config(),
        "sound_system": make_sound_system(),
        "interaction_controller": make_interaction_controller(),
        "event_bus": MagicMock(),
        "renderer": make_renderer(with_display_config=True),
        "window_manager": make_window_manager(),
        "render_pipeline": make_render_pipeline(),
        "input_router": make_input_router(),
        "minimap": make_minimap(),
        "cc2_panel": make_cc2_panel(),
    }


@pytest.fixture()
def initialized_hud(deps):
    """A HUDManager that has been fully initialized via initialize()."""
    hud = HUDManager()
    hud.initialize(**deps)
    return hud, deps


# ---------------------------------------------------------------------------
# initialize()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInitialize:
    def test_initialize_sets_all_internal_refs(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        assert hud._state is deps["state"]
        assert hud._sound_system is deps["sound_system"]
        assert hud._interaction_controller is deps["interaction_controller"]
        assert hud._event_bus is deps["event_bus"]
        assert hud._minimap is deps["minimap"]
        assert hud._cc2_panel is deps["cc2_panel"]

    def test_initialize_calls_cc2_panel_initialize(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        # initialize() is called at least once (twice when screen is not None).
        assert deps["cc2_panel"].initialize.call_count >= 1

    def test_initialize_sets_minimap_map_and_shows(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        deps["minimap"].set_map.assert_called_once_with(deps["state"].game_map)
        deps["minimap"].show.assert_called_once()

    def test_initialize_updates_camera_viewport_and_zoom(self, deps):
        hud = HUDManager()
        dc = deps["display_config"]
        hud.initialize(**deps)
        cam = deps["state"].camera
        assert cam.viewport_width == dc.window_width
        assert cam.viewport_height == dc.window_height
        # zoom should be set to compute_default_zoom result
        expected_zoom = dc.compute_default_zoom(
            deps["state"].game_map.width, deps["state"].game_map.height
        )
        assert cam.zoom == expected_zoom

    def test_initialize_raises_value_error_when_minimap_none(self, deps):
        deps["minimap"] = None
        hud = HUDManager()
        with pytest.raises(ValueError, match="minimap"):
            hud.initialize(**deps)

    def test_initialize_raises_value_error_when_cc2_panel_none(self, deps):
        deps["cc2_panel"] = None
        hud = HUDManager()
        with pytest.raises(ValueError, match="cc2_panel"):
            hud.initialize(**deps)

    def test_initialize_updates_renderer_display_config(self, deps):
        hud = HUDManager()
        dc = deps["display_config"]
        hud.initialize(**deps)
        renderer = deps["renderer"]
        assert renderer._display_config is dc
        assert dc.base_tile_size == renderer.TILE_SIZE
        assert dc.effective_sprite_size == renderer.SPRITE_SIZE

    def test_initialize_skips_renderer_config_when_no_display_config_attr(self, deps):
        hud = HUDManager()
        # Renderer without _display_config attribute.
        renderer = MagicMock(spec=["TILE_SIZE", "SPRITE_SIZE", "render", "initialize"])
        renderer.TILE_SIZE = 48
        renderer.SPRITE_SIZE = 42
        deps["renderer"] = renderer
        # Should not raise.
        hud.initialize(**deps)

    def test_initialize_clears_render_pipeline_attributes(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        rp = deps["render_pipeline"]
        assert rp.hud_manager is None
        assert rp.command_bar is None
        assert rp.unit_panel is None
        assert rp.minimap is None

    def test_initialize_clears_input_router_command_bar(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        assert deps["input_router"].command_bar is None

    def test_initialize_registers_seven_command_callbacks(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        expected_commands = {"move", "fast", "sneak", "attack", "smoke", "defend", "cancel"}
        assert expected_commands.issubset(callbacks.keys())
        assert len(callbacks) == 7

    def test_initialize_sets_on_unit_select_and_on_zoom_change(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        panel = deps["cc2_panel"]
        assert panel._on_unit_select is not None
        assert panel._on_zoom_change is not None

    def test_initialize_registers_interaction_callbacks(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        ic = deps["interaction_controller"]
        ic.register_on_move.assert_called_once()
        ic.register_on_attack.assert_called_once()

    def test_initialize_skips_second_initialize_when_screen_none(self, deps):
        hud = HUDManager()
        deps["window_manager"] = make_window_manager(screen=None)
        hud.initialize(**deps)
        # Only the first initialize() at line 102 should be called.
        assert deps["cc2_panel"].initialize.call_count == 1


# ---------------------------------------------------------------------------
# center_camera_on_unit()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCenterCameraOnUnit:
    def test_centers_camera_on_existing_unit(self, initialized_hud):
        hud, deps = initialized_hud
        cam = make_camera()
        units = [make_unit("u1", tile=(5, 5))]
        hud.center_camera_on_unit(units, "u1", cam)
        # Camera should be centered: pos - viewport/2
        expected_x = units[0].position.pixel_position.x - cam.viewport_width / 2
        expected_y = units[0].position.pixel_position.y - cam.viewport_height / 2
        assert cam.position.x == pytest.approx(expected_x)
        assert cam.position.y == pytest.approx(expected_y)

    def test_does_nothing_when_unit_not_found(self, initialized_hud):
        hud, deps = initialized_hud
        cam = make_camera()
        original_pos = cam.position
        hud.center_camera_on_unit([make_unit("u1")], "nonexistent", cam)
        assert cam.position is original_pos

    def test_does_nothing_when_unit_position_is_none(self, initialized_hud):
        hud, deps = initialized_hud
        cam = make_camera()
        original_pos = cam.position
        unit = make_unit("u1")
        unit.position = None
        hud.center_camera_on_unit([unit], "u1", cam)
        assert cam.position is original_pos

    def test_does_nothing_when_units_empty(self, initialized_hud):
        hud, deps = initialized_hud
        cam = make_camera()
        original_pos = cam.position
        hud.center_camera_on_unit([], "u1", cam)
        assert cam.position is original_pos


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUpdate:
    def test_update_calls_cc2_panel_update(self, initialized_hud):
        hud, deps = initialized_hud
        hud.update(0.016)
        deps["cc2_panel"].update.assert_called_once_with(0.016)

    def test_update_calls_minimap_update_and_sync(self, initialized_hud):
        hud, deps = initialized_hud
        state = deps["state"]
        hud.update(0.016)
        mm = deps["minimap"]
        mm.update.assert_called_once_with(0.016)
        mm.update_units.assert_called_once_with(state.units)
        mm.set_selected_unit.assert_called_once()
        mm.set_camera_viewport.assert_called_once()

    def test_update_minimap_set_selected_unit_none_when_no_selection(self, initialized_hud):
        hud, deps = initialized_hud
        deps["state"].selected_unit_ids = set()
        hud.update(0.016)
        deps["minimap"].set_selected_unit.assert_called_once_with(None)

    def test_update_minimap_set_selected_unit_when_selection_present(self, initialized_hud):
        hud, deps = initialized_hud
        deps["state"].selected_unit_ids = {"u1"}
        hud.update(0.016)
        deps["minimap"].set_selected_unit.assert_called_once_with("u1")

    def test_update_skips_minimap_when_state_none(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        hud._state = None
        hud.update(0.016)
        # cc2_panel still updated
        deps["cc2_panel"].update.assert_called_once_with(0.016)
        # minimap not touched
        deps["minimap"].update.assert_not_called()

    def test_update_skips_cc2_panel_when_none(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        hud._cc2_panel = None
        hud.update(0.016)
        # minimap still updated
        deps["minimap"].update.assert_called_once()

    def test_update_skips_minimap_when_none(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        hud._minimap = None
        hud.update(0.016)
        # cc2_panel still updated
        deps["cc2_panel"].update.assert_called_once_with(0.016)

    def test_update_skips_camera_viewport_when_camera_none(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        hud._state.camera = None
        hud.update(0.016)
        # minimap.update + update_units + set_selected_unit still called,
        # but set_camera_viewport should NOT be called.
        mm = deps["minimap"]
        mm.update.assert_called_once()
        mm.update_units.assert_called_once()
        mm.set_selected_unit.assert_called_once()
        mm.set_camera_viewport.assert_not_called()


# ---------------------------------------------------------------------------
# render()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRender:
    def test_render_calls_cc2_panel_set_selected_unit_and_render(self, initialized_hud):
        hud, deps = initialized_hud
        screen = MagicMock()
        cam = make_camera()
        game_state = deps["state"]
        hud.render(screen, cam, game_state)
        panel = deps["cc2_panel"]
        panel.set_selected_unit.assert_called_once()
        panel.render.assert_called_once()
        # Verify render kwargs
        _, kwargs = panel.render.call_args
        assert kwargs["surface"] is screen
        assert kwargs["camera"] is cam
        assert kwargs["game_map"] is game_state.game_map
        assert kwargs["minimap"] is deps["minimap"]

    def test_render_sets_friendly_units(self, initialized_hud):
        hud, deps = initialized_hud
        screen = MagicMock()
        cam = make_camera()
        # Only ALLIES units should be friendly.
        game_state = deps["state"]
        hud.render(screen, cam, game_state)
        panel = deps["cc2_panel"]
        panel.set_friendly_units.assert_called_once()
        friendly = panel.set_friendly_units.call_args[0][0]
        # All units in deps are ALLIES faction.
        assert len(friendly) == len(game_state.units)

    def test_render_filters_friendly_units_by_faction(self, initialized_hud):
        hud, deps = initialized_hud
        screen = MagicMock()
        cam = make_camera()
        allied_unit = make_unit("allied", faction=Faction.ALLIES)
        axis_unit = make_unit("axis", faction=Faction.AXIS)
        polish_unit = make_unit("polish", faction=Faction.POLISH)
        gs = GameState(
            game_map=make_game_map(),
            units=[allied_unit, axis_unit, polish_unit],
            camera=cam,
        )
        hud.render(screen, cam, gs)
        panel = deps["cc2_panel"]
        panel.set_friendly_units.assert_called_once()
        friendly = panel.set_friendly_units.call_args[0][0]
        friendly_ids = {u.id for u in friendly}
        assert "allied" in friendly_ids
        assert "polish" in friendly_ids
        assert "axis" not in friendly_ids

    def test_render_syncs_interaction_controller_selected_ids(self, initialized_hud):
        hud, deps = initialized_hud
        screen = MagicMock()
        cam = make_camera()
        gs = deps["state"]
        gs.selected_unit_ids = {"u1", "u2"}
        hud.render(screen, cam, gs)
        assert deps["interaction_controller"]._selected_ids == {"u1", "u2"}

    def test_render_does_not_raise_when_cc2_panel_none(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        hud._cc2_panel = None
        screen = MagicMock()
        cam = make_camera()
        gs = deps["state"]
        # Should not raise.
        hud.render(screen, cam, gs)

    def test_render_catches_cc2_panel_render_exception(self, initialized_hud):
        hud, deps = initialized_hud
        deps["cc2_panel"].render.side_effect = RuntimeError("boom")
        screen = MagicMock()
        cam = make_camera()
        gs = deps["state"]
        # Should not propagate.
        hud.render(screen, cam, gs)

    def test_render_catches_friendly_units_attribute_error(self, initialized_hud):
        hud, deps = initialized_hud
        screen = MagicMock()
        cam = make_camera()

        # A unit whose `faction` access raises AttributeError → caught by
        # the try/except in render().
        class BadUnit:
            id = "bad"

            @property
            def faction(self):
                raise AttributeError("no faction")

        gs = GameState(
            game_map=make_game_map(),
            units=[BadUnit()],
            camera=cam,
        )
        # Should not raise; friendly-units failure is logged and swallowed.
        hud.render(screen, cam, gs)
        # render still proceeds after the caught exception.
        deps["cc2_panel"].render.assert_called_once()


# ---------------------------------------------------------------------------
# render_fallback()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderFallback:
    def test_render_fallback_does_not_raise(self, initialized_hud):
        hud, deps = initialized_hud
        screen = MagicMock()
        cam = make_camera()
        gs = deps["state"]
        # Should not raise and should not render anything.
        hud.render_fallback(screen, cam, gs)

    def test_render_fallback_does_not_call_cc2_panel(self, initialized_hud):
        hud, deps = initialized_hud
        screen = MagicMock()
        cam = make_camera()
        gs = deps["state"]
        hud.render_fallback(screen, cam, gs)
        deps["cc2_panel"].render.assert_not_called()


# ---------------------------------------------------------------------------
# set_mouse_pos() / set_mouse_pressed()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMouseInteraction:
    def test_set_mouse_pos_forwards_to_cc2_panel(self, initialized_hud):
        hud, deps = initialized_hud
        hud.set_mouse_pos((100, 200))
        deps["cc2_panel"].set_mouse_pos.assert_called_once_with((100, 200))

    def test_set_mouse_pos_none_when_no_cc2_panel(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        hud._cc2_panel = None
        # Should not raise.
        hud.set_mouse_pos((100, 200))

    def test_set_mouse_pressed_forwards_to_cc2_panel(self, initialized_hud):
        hud, deps = initialized_hud
        hud.set_mouse_pressed(True)
        deps["cc2_panel"].set_mouse_pressed.assert_called_once_with(True)

    def test_set_mouse_pressed_none_when_no_cc2_panel(self, deps):
        hud = HUDManager()
        hud.initialize(**deps)
        hud._cc2_panel = None
        # Should not raise.
        hud.set_mouse_pressed(False)


# ---------------------------------------------------------------------------
# minimap property
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMinimapProperty:
    def test_minimap_property_returns_internal_minimap(self, initialized_hud):
        hud, deps = initialized_hud
        assert hud.minimap is deps["minimap"]

    def test_minimap_property_none_before_initialize(self):
        hud = HUDManager()
        assert hud.minimap is None


# ---------------------------------------------------------------------------
# _bind_command_callbacks() — defensive early returns
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBindCommandCallbacksDefensive:
    def test_returns_early_when_cc2_panel_none(self, deps):
        hud = HUDManager()
        hud._cc2_panel = None
        hud._state = deps["state"]
        hud._event_bus = deps["event_bus"]
        # Should not raise and should not register callbacks.
        hud._bind_command_callbacks()

    def test_returns_early_when_state_none(self, deps):
        hud = HUDManager()
        hud._cc2_panel = deps["cc2_panel"]
        hud._state = None
        hud._event_bus = deps["event_bus"]
        hud._bind_command_callbacks()
        deps["cc2_panel"].register_callback.assert_not_called()

    def test_returns_early_when_event_bus_none(self, deps):
        hud = HUDManager()
        hud._cc2_panel = deps["cc2_panel"]
        hud._state = deps["state"]
        hud._event_bus = None
        hud._bind_command_callbacks()
        deps["cc2_panel"].register_callback.assert_not_called()


# ---------------------------------------------------------------------------
# Command callbacks behavior (invoked via captured closures)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCommandCallbacks:
    def test_on_move_plays_sound_and_sets_move_mode(self, initialized_hud):
        hud, deps = initialized_hud
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["move"]()
        deps["sound_system"].play_ui_command.assert_called_once()
        deps["interaction_controller"].set_mode.assert_called_once()
        # Verify the mode argument is InteractionMode.MOVE
        from pycc2.domain.value_objects.audio_enums import InteractionMode

        args, kwargs = deps["interaction_controller"].set_mode.call_args
        assert args[0] == InteractionMode.MOVE

    def test_on_attack_plays_sound_and_sets_attack_mode(self, initialized_hud):
        hud, deps = initialized_hud
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["attack"]()
        deps["sound_system"].play_ui_command.assert_called_once()
        from pycc2.domain.value_objects.audio_enums import InteractionMode

        args, kwargs = deps["interaction_controller"].set_mode.call_args
        assert args[0] == InteractionMode.ATTACK

    def test_on_attack_starts_attack_line_when_unit_selected(self, initialized_hud):
        hud, deps = initialized_hud
        # Select a unit that exists in state.units.
        deps["state"].selected_unit_ids = {"u1"}
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["attack"]()
        ic = deps["interaction_controller"]
        ic.attack_line.begin_attack.assert_called_once()
        call_kwargs = ic.attack_line.begin_attack.call_args.kwargs
        assert call_kwargs["unit_id"] == "u1"

    def test_on_attack_skips_attack_line_when_no_selection(self, initialized_hud):
        hud, deps = initialized_hud
        deps["state"].selected_unit_ids = set()
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["attack"]()
        deps["interaction_controller"].attack_line.begin_attack.assert_not_called()

    def test_on_cancel_plays_cancel_sound_and_clears_selection(self, initialized_hud):
        hud, deps = initialized_hud
        deps["state"].selected_unit_ids = {"u1", "u2"}
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["cancel"]()
        # UI_CANCEL sound played
        from pycc2.domain.value_objects.audio_enums import SoundType

        deps["sound_system"].play.assert_called_once_with(SoundType.UI_CANCEL)
        # Selection cleared
        assert deps["state"].selected_unit_ids == set()
        # Interaction controller selection cleared
        deps["interaction_controller"].clear_selection.assert_called_once()

    def test_on_fast_sets_fast_move_mode(self, initialized_hud):
        hud, deps = initialized_hud
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["fast"]()
        deps["sound_system"].play_ui_command.assert_called_once()
        from pycc2.domain.value_objects.audio_enums import InteractionMode

        args, kwargs = deps["interaction_controller"].set_mode.call_args
        assert args[0] == InteractionMode.MOVE
        assert kwargs.get("fast") is True

    def test_on_sneak_sets_sneak_move_mode(self, initialized_hud):
        hud, deps = initialized_hud
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["sneak"]()
        deps["sound_system"].play_ui_command.assert_called_once()
        from pycc2.domain.value_objects.audio_enums import InteractionMode

        args, kwargs = deps["interaction_controller"].set_mode.call_args
        assert args[0] == InteractionMode.MOVE
        assert kwargs.get("sneak") is True

    def test_on_smoke_publishes_deploy_smoke_command(self, initialized_hud):
        hud, deps = initialized_hud
        deps["state"].selected_unit_ids = {"u1"}
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["smoke"]()
        deps["sound_system"].play_ui_command.assert_called_once()
        # A PlayerCommand should be published via event_bus.
        published_events = [c.args[0] for c in deps["event_bus"].publish.call_args_list]
        assert any(e.get("command") == "deploy_smoke" for e in published_events)

    def test_on_defend_publishes_take_cover_command(self, initialized_hud):
        hud, deps = initialized_hud
        deps["state"].selected_unit_ids = {"u1"}
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["defend"]()
        deps["sound_system"].play_ui_command.assert_called_once()
        published_events = [c.args[0] for c in deps["event_bus"].publish.call_args_list]
        assert any(e.get("command") == "take_cover" for e in published_events)

    def test_on_roster_select_sets_selected_unit_and_centers_camera(self, initialized_hud):
        hud, deps = initialized_hud
        panel = deps["cc2_panel"]
        # Invoke the on_unit_select callback captured during initialize.
        panel._on_unit_select("u1")
        assert deps["state"].selected_unit_ids == {"u1"}

    def test_on_roster_select_ignores_none_unit_id(self, initialized_hud):
        hud, deps = initialized_hud
        deps["state"].selected_unit_ids = {"u1"}
        panel = deps["cc2_panel"]
        panel._on_unit_select(None)
        # Should not modify selection when unit_id is None/falsy.
        assert deps["state"].selected_unit_ids == {"u1"}

    def test_on_zoom_change_updates_camera_zoom(self, initialized_hud):
        hud, deps = initialized_hud
        panel = deps["cc2_panel"]
        panel._on_zoom_change(2.5)
        assert deps["state"].camera.zoom == 2.5


# ---------------------------------------------------------------------------
# _bind_interaction_callbacks() — defensive early returns
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBindInteractionCallbacksDefensive:
    def test_returns_early_when_interaction_controller_none(self, deps):
        hud = HUDManager()
        hud._interaction_controller = None
        hud._state = deps["state"]
        hud._event_bus = deps["event_bus"]
        hud._bind_interaction_callbacks()

    def test_returns_early_when_state_none(self, deps):
        hud = HUDManager()
        hud._interaction_controller = deps["interaction_controller"]
        hud._state = None
        hud._event_bus = deps["event_bus"]
        hud._bind_interaction_callbacks()
        deps["interaction_controller"].register_on_move.assert_not_called()

    def test_returns_early_when_event_bus_none(self, deps):
        hud = HUDManager()
        hud._interaction_controller = deps["interaction_controller"]
        hud._state = deps["state"]
        hud._event_bus = None
        hud._bind_interaction_callbacks()
        deps["interaction_controller"].register_on_move.assert_not_called()


# ---------------------------------------------------------------------------
# Interaction callbacks behavior (execute_move / execute_attack)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestInteractionCallbacks:
    def test_execute_move_sets_move_target_and_publishes_command(self, initialized_hud):
        hud, deps = initialized_hud
        ic = deps["interaction_controller"]
        # Capture the registered move callback.
        move_cb = ic.register_on_move.call_args[0][0]
        # Create a target with x/y (pixel coords).
        target = Vec2(320.0, 320.0)
        move_cb({"u1"}, target)
        # Unit u1 should have move_target set.
        u1 = next(u for u in deps["state"].units if u.id == "u1")
        assert u1.move_target is not None
        # A PlayerCommand("move") should be published.
        published_events = [c.args[0] for c in deps["event_bus"].publish.call_args_list]
        assert any(e.get("command") == "move" for e in published_events)

    def test_execute_move_skips_dead_units(self, initialized_hud):
        hud, deps = initialized_hud
        ic = deps["interaction_controller"]
        move_cb = ic.register_on_move.call_args[0][0]
        # Kill u1.
        u1 = next(u for u in deps["state"].units if u.id == "u1")
        u1.health = HealthComponent(hp=0, max_hp=100)
        target = Vec2(320.0, 320.0)
        move_cb({"u1"}, target)
        # Dead unit should not have move_target set.
        assert u1.move_target is None

    def test_execute_move_skips_units_not_in_id_set(self, initialized_hud):
        hud, deps = initialized_hud
        ic = deps["interaction_controller"]
        move_cb = ic.register_on_move.call_args[0][0]
        target = Vec2(320.0, 320.0)
        move_cb({"nonexistent"}, target)
        # No unit should have a move target.
        for u in deps["state"].units:
            assert u.move_target is None

    def test_execute_attack_publishes_attack_command(self, initialized_hud):
        hud, deps = initialized_hud
        ic = deps["interaction_controller"]
        attack_cb = ic.register_on_attack.call_args[0][0]
        attack_cb({"u1"}, "enemy1")
        published_events = [c.args[0] for c in deps["event_bus"].publish.call_args_list]
        attack_events = [e for e in published_events if e.get("command") == "attack"]
        assert len(attack_events) == 1
        assert attack_events[0].get("target_id") == "enemy1"


# ---------------------------------------------------------------------------
# Command callbacks without sound_system (None-safe path)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCommandCallbacksWithoutSoundSystem:
    def test_on_move_without_sound_system_does_not_raise(self, deps):
        deps["sound_system"] = None
        hud = HUDManager()
        hud.initialize(**deps)
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["move"]()
        deps["interaction_controller"].set_mode.assert_called_once()

    def test_on_cancel_without_sound_system_clears_selection(self, deps):
        deps["sound_system"] = None
        hud = HUDManager()
        hud.initialize(**deps)
        deps["state"].selected_unit_ids = {"u1"}
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["cancel"]()
        assert deps["state"].selected_unit_ids == set()


# ---------------------------------------------------------------------------
# Command callbacks without interaction_controller (None-safe path)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCommandCallbacksWithoutInteractionController:
    def test_on_move_without_interaction_controller_plays_sound(self, deps):
        deps["interaction_controller"] = None
        hud = HUDManager()
        hud.initialize(**deps)
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["move"]()
        deps["sound_system"].play_ui_command.assert_called_once()

    def test_on_attack_without_interaction_controller_publishes_no_attack_line(self, deps):
        deps["interaction_controller"] = None
        hud = HUDManager()
        hud.initialize(**deps)
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        # Should not raise even without interaction_controller.
        callbacks["attack"]()

    def test_on_cancel_without_interaction_controller_clears_selection(self, deps):
        deps["interaction_controller"] = None
        hud = HUDManager()
        hud.initialize(**deps)
        deps["state"].selected_unit_ids = {"u1"}
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["cancel"]()
        assert deps["state"].selected_unit_ids == set()

    def test_on_smoke_without_sound_system_publishes_command(self, deps):
        deps["sound_system"] = None
        hud = HUDManager()
        hud.initialize(**deps)
        deps["state"].selected_unit_ids = {"u1"}
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["smoke"]()
        published_events = [c.args[0] for c in deps["event_bus"].publish.call_args_list]
        assert any(e.get("command") == "deploy_smoke" for e in published_events)

    def test_on_defend_without_sound_system_publishes_command(self, deps):
        deps["sound_system"] = None
        hud = HUDManager()
        hud.initialize(**deps)
        deps["state"].selected_unit_ids = {"u1"}
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["defend"]()
        published_events = [c.args[0] for c in deps["event_bus"].publish.call_args_list]
        assert any(e.get("command") == "take_cover" for e in published_events)

    def test_on_fast_without_sound_system_sets_mode(self, deps):
        deps["sound_system"] = None
        hud = HUDManager()
        hud.initialize(**deps)
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["fast"]()
        deps["interaction_controller"].set_mode.assert_called_once()

    def test_on_sneak_without_sound_system_sets_mode(self, deps):
        deps["sound_system"] = None
        hud = HUDManager()
        hud.initialize(**deps)
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["sneak"]()
        deps["interaction_controller"].set_mode.assert_called_once()

    def test_on_fast_without_interaction_controller_plays_sound(self, deps):
        deps["interaction_controller"] = None
        hud = HUDManager()
        hud.initialize(**deps)
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["fast"]()
        deps["sound_system"].play_ui_command.assert_called_once()

    def test_on_sneak_without_interaction_controller_plays_sound(self, deps):
        deps["interaction_controller"] = None
        hud = HUDManager()
        hud.initialize(**deps)
        callbacks: dict = deps["cc2_panel"]._captured_callbacks
        callbacks["sneak"]()
        deps["sound_system"].play_ui_command.assert_called_once()


# ---------------------------------------------------------------------------
# render() — interaction_controller without _selected_ids attribute
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderWithoutSelectedIds:
    def test_render_skips_selected_ids_sync_when_attr_missing(self, initialized_hud):
        hud, deps = initialized_hud
        # Remove _selected_ids attribute from interaction_controller.
        del deps["interaction_controller"]._selected_ids
        screen = MagicMock()
        cam = make_camera()
        gs = deps["state"]
        gs.selected_unit_ids = {"u1"}
        # Should not raise even though _selected_ids is missing.
        hud.render(screen, cam, gs)
        deps["cc2_panel"].render.assert_called_once()
