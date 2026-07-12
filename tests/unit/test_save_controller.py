"""Unit tests for SaveController.

Covers initialize, quick_save, quick_load, list_saves, export_state, and
restore_state. Prefers real domain components (HealthComponent, MoraleComponent,
PositionComponent, VisionComponent, WeaponComponent, Unit, Faction, GameState)
and a real SecureSaveManager where feasible; uses lightweight stubs/mocks only
for game_loop scaffolding and sound_system.
"""

from __future__ import annotations

import os

# Headless pygame support — must be set before any pygame import.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import MagicMock

import numpy as np
import pytest

from pycc2.domain.components.health_component import HealthComponent, HealthState
from pycc2.domain.components.morale_component import MoraleComponent, MoraleState
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent, WeaponState
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.audio_enums import SoundType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.infrastructure.save_system import SaveMetaData, SaveSlotStatus, SecureSaveManager
from pycc2.presentation.rendering.camera import Camera
from pycc2.services.game_loop_types import GameState
from pycc2.services.save_controller import SaveController

# ---------------------------------------------------------------------------
# Stubs & helpers
# ---------------------------------------------------------------------------


class StubGameLoop:
    """Minimal game loop stub with explicit state/sound_system/renderer.

    Using a plain class (not MagicMock) gives precise ``hasattr`` semantics
    so restore_state's renderer-clearing branch is only entered when we
    explicitly attach a renderer.
    """

    def __init__(self, state, sound_system=None, renderer=None, victory_manager=None):
        self.state = state
        self.sound_system = sound_system
        self.renderer = renderer
        self.victory_manager = victory_manager


class StubRenderer:
    """Renderer stub exposing the animator/emitter collections restore_state clears."""

    def __init__(self):
        self._unit_animators = [1, 2, 3]
        self._particle_emitter = [4, 5]


def _make_map(width=16, height=16):
    grid = np.zeros((width, height), dtype=np.int8)
    return GameMap(id="test", name="Test Map", width=width, height=height, tile_grid=grid)


def _make_unit(
    unit_id="u1",
    faction=Faction.ALLIES,
    unit_type=UnitType.INFANTRY_SQUAD,
    hp=100,
    max_hp=100,
    tile=(5, 5),
    alive=True,
):
    """Build a real Unit with sensible component defaults."""
    return Unit(
        id=unit_id,
        name=f"Unit {unit_id}",
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp if alive else 0, max_hp=max_hp),
        morale=MoraleComponent(value=80),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=8, max_ammo=10),
        position=PositionComponent(tile_coord=TileCoord(tile[0], tile[1])),
        vision=VisionComponent(range_tiles=5),
    )


def _make_game_state(
    units=None,
    tick=42,
    paused=False,
    camera_pos=(100.0, 200.0),
    zoom=1.5,
    selected=None,
):
    game_map = _make_map()
    camera = Camera(
        position=Vec2(camera_pos[0], camera_pos[1]),
        viewport_width=1280,
        viewport_height=720,
    )
    camera.zoom = zoom
    return GameState(
        game_map=game_map,
        units=units if units is not None else [],
        camera=camera,
        tick=tick,
        paused=paused,
        selected_unit_ids=set(selected) if selected else set(),
    )


def _sample_state_dict():
    """A complete, valid state dict consumable by restore_state."""
    return {
        "tick": 999,
        "paused": True,
        "camera": {"position": {"x": 50.0, "y": 60.0}, "zoom": 2.0},
        "selected_unit_ids": ["u1", "u2"],
        "units": [
            {
                "id": "u1",
                "name": "Rifle Squad",
                "faction": "ALLIES",
                "unit_type": "INFANTRY_SQUAD",
                "health": {"hp": 80, "max_hp": 100, "state": "WOUNDED"},
                "morale": {
                    "value": 50,
                    "panic_threshold": 20,
                    "suppression": 10,
                    "state": "WAVERING",
                },
                "weapon": {
                    "primary_weapon_id": "rifle",
                    "ammo_remaining": 5,
                    "max_ammo": 10,
                    "reload_ticks_left": 0,
                    "state": "READY",
                },
                "position": {
                    "tile_coord": {"x": 3, "y": 4},
                    "pixel_offset": {"x": 1.0, "y": 2.0},
                    "facing_rad": 0.5,
                },
                "vision": {"range_tiles": 6, "angle_rad": 3.14},
                "squad_id": "squad_1",
            }
        ],
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_manager(tmp_path):
    """A real SecureSaveManager backed by a temporary directory."""
    return SecureSaveManager(base_dir=tmp_path / "saves")


# ===========================================================================
# initialize
# ===========================================================================


@pytest.mark.unit
class TestInitialize:
    def test_initialize_creates_secure_save_manager(self):
        controller = SaveController()
        assert controller.save_manager is None

        controller.initialize()

        assert isinstance(controller.save_manager, SecureSaveManager)

    def test_initialize_replaces_existing_manager(self, tmp_manager):
        controller = SaveController(save_manager=tmp_manager)
        controller.initialize()
        # New instance, still a SecureSaveManager
        assert isinstance(controller.save_manager, SecureSaveManager)
        assert controller.save_manager is not tmp_manager


# ===========================================================================
# quick_save
# ===========================================================================


@pytest.mark.unit
class TestQuickSave:
    def test_no_save_manager_returns_false(self):
        controller = SaveController(save_manager=None)
        loop = StubGameLoop(_make_game_state(), sound_system=MagicMock())
        assert controller.quick_save(slot=0, game_loop=loop) is False

    def test_no_game_loop_returns_false(self, tmp_manager):
        controller = SaveController(save_manager=tmp_manager)
        assert controller.quick_save(slot=0, game_loop=None) is False

    def test_success_path_saves_meta_and_plays_sound(self):
        """Verify export + SaveMetaData(tick/allies/axis) + save_game True + sound."""
        save_manager = MagicMock()
        save_manager.save_game.return_value = True
        save_manager.export_state_from_game_loop.return_value = {"tick": 42, "units": []}
        controller = SaveController(save_manager=save_manager)

        ally1 = _make_unit("a1", Faction.ALLIES, alive=True)
        ally2 = _make_unit("a2", Faction.ALLIES, alive=True)
        axis1 = _make_unit("e1", Faction.AXIS, alive=True)
        dead_ally = _make_unit("da", Faction.ALLIES, alive=False)
        state = _make_game_state(units=[ally1, ally2, axis1, dead_ally], tick=42)
        sound = MagicMock()
        loop = StubGameLoop(state, sound_system=sound)

        result = controller.quick_save(slot=2, game_loop=loop)

        assert result is True
        save_manager.export_state_from_game_loop.assert_called_once_with(loop)
        save_manager.save_game.assert_called_once()
        call = save_manager.save_game.call_args
        assert call.args[0] == 2  # slot
        assert call.args[1] == {"tick": 42, "units": []}  # exported state
        meta = call.args[2]
        assert isinstance(meta, SaveMetaData)
        assert meta.tick == 42
        assert meta.allies_alive == 2  # ally1 + ally2 (dead_ally excluded)
        assert meta.axis_alive == 1
        sound.play_ui_command.assert_called_once()

    def test_save_game_returns_false_propagates_false(self):
        save_manager = MagicMock()
        save_manager.save_game.return_value = False
        save_manager.export_state_from_game_loop.return_value = {"tick": 1}
        controller = SaveController(save_manager=save_manager)
        sound = MagicMock()
        loop = StubGameLoop(_make_game_state(units=[_make_unit()]), sound_system=sound)

        result = controller.quick_save(slot=0, game_loop=loop)

        assert result is False
        sound.play_ui_command.assert_not_called()

    def test_no_sound_system_does_not_crash(self):
        save_manager = MagicMock()
        save_manager.save_game.return_value = True
        save_manager.export_state_from_game_loop.return_value = {"tick": 1}
        controller = SaveController(save_manager=save_manager)
        loop = StubGameLoop(_make_game_state(units=[_make_unit()]), sound_system=None)

        result = controller.quick_save(slot=0, game_loop=loop)

        assert result is True

    def test_real_manager_persists_state(self, tmp_manager):
        """Integration: real SecureSaveManager actually writes the slot."""
        controller = SaveController(save_manager=tmp_manager)
        unit = _make_unit("u1", Faction.ALLIES, tile=(3, 3))
        state = _make_game_state(units=[unit], tick=777)
        loop = StubGameLoop(state, sound_system=None)

        assert controller.quick_save(slot=0, game_loop=loop) is True
        # Confirm the slot is now populated.
        _, _, status = tmp_manager.load_game(0)
        assert status == SaveSlotStatus.OK


# ===========================================================================
# quick_load
# ===========================================================================


@pytest.mark.unit
class TestQuickLoad:
    def test_no_save_manager_returns_false(self):
        controller = SaveController(save_manager=None)
        loop = StubGameLoop(_make_game_state(), sound_system=MagicMock())
        assert controller.quick_load(slot=0, game_loop=loop) is False

    def test_no_game_loop_returns_false(self, tmp_manager):
        controller = SaveController(save_manager=tmp_manager)
        assert controller.quick_load(slot=0, game_loop=None) is False

    def test_status_not_ok_plays_cancel_and_returns_false(self):
        save_manager = MagicMock()
        save_manager.load_game.return_value = (None, None, SaveSlotStatus.EMPTY)
        controller = SaveController(save_manager=save_manager)
        sound = MagicMock()
        loop = StubGameLoop(_make_game_state(), sound_system=sound)

        result = controller.quick_load(slot=0, game_loop=loop)

        assert result is False
        sound.play.assert_called_once_with(SoundType.UI_CANCEL)

    def test_status_not_ok_without_sound_returns_false(self):
        save_manager = MagicMock()
        save_manager.load_game.return_value = (None, None, SaveSlotStatus.CORRUPTED)
        controller = SaveController(save_manager=save_manager)
        loop = StubGameLoop(_make_game_state(), sound_system=None)

        assert controller.quick_load(slot=0, game_loop=loop) is False

    def test_state_dict_none_returns_false(self):
        """status OK but state_dict None → treat as failure."""
        save_manager = MagicMock()
        save_manager.load_game.return_value = (None, SaveMetaData(), SaveSlotStatus.OK)
        controller = SaveController(save_manager=save_manager)
        sound = MagicMock()
        loop = StubGameLoop(_make_game_state(), sound_system=sound)

        result = controller.quick_load(slot=0, game_loop=loop)

        assert result is False
        sound.play.assert_called_once_with(SoundType.UI_CANCEL)

    def test_restore_success_plays_command_and_returns_true(self, tmp_manager):
        """Real round-trip: quick_save then quick_load restores state."""
        controller = SaveController(save_manager=tmp_manager)
        unit = _make_unit("u1", Faction.ALLIES, tile=(3, 3))
        state = _make_game_state(units=[unit], tick=555, paused=True, selected=["u1"])
        sound = MagicMock()
        loop = StubGameLoop(state, sound_system=sound)

        controller.quick_save(slot=0, game_loop=loop)
        # Reset mock so we only observe quick_load's sound calls.
        sound.reset_mock()
        # Mutate state to prove restore overwrites it.
        state.tick = 0
        state.units = []

        result = controller.quick_load(slot=0, game_loop=loop)

        assert result is True
        sound.play_ui_command.assert_called_once()
        assert state.tick == 555
        assert state.paused is True
        assert len(state.units) == 1
        assert state.units[0].id == "u1"

    def test_restore_returns_false_plays_cancel(self):
        """restore_state returns False (empty units) → cancel + False."""
        save_manager = MagicMock()
        empty_state = {"tick": 1, "units": []}
        save_manager.load_game.return_value = (empty_state, SaveMetaData(), SaveSlotStatus.OK)
        controller = SaveController(save_manager=save_manager)
        sound = MagicMock()
        loop = StubGameLoop(_make_game_state(), sound_system=sound)

        result = controller.quick_load(slot=0, game_loop=loop)

        assert result is False
        sound.play.assert_called_once_with(SoundType.UI_CANCEL)
        sound.play_ui_command.assert_not_called()

    def test_restore_raises_value_error_plays_cancel(self, monkeypatch):
        """restore_state raising ValueError is caught → cancel + False."""
        save_manager = MagicMock()
        save_manager.load_game.return_value = (
            {"tick": 1, "units": [{"id": "u1"}]},
            SaveMetaData(),
            SaveSlotStatus.OK,
        )
        controller = SaveController(save_manager=save_manager)
        sound = MagicMock()
        loop = StubGameLoop(_make_game_state(), sound_system=sound)

        def _raise(data, game_loop):
            raise ValueError("simulated restore failure")

        monkeypatch.setattr(controller, "restore_state", _raise)

        result = controller.quick_load(slot=0, game_loop=loop)

        assert result is False
        sound.play.assert_called_once_with(SoundType.UI_CANCEL)

    def test_restore_raises_runtime_error_plays_cancel(self, monkeypatch):
        save_manager = MagicMock()
        save_manager.load_game.return_value = (
            {"tick": 1, "units": [{"id": "u1"}]},
            SaveMetaData(),
            SaveSlotStatus.OK,
        )
        controller = SaveController(save_manager=save_manager)
        sound = MagicMock()
        loop = StubGameLoop(_make_game_state(), sound_system=sound)

        def _raise(data, game_loop):
            raise RuntimeError("boom")

        monkeypatch.setattr(controller, "restore_state", _raise)

        result = controller.quick_load(slot=0, game_loop=loop)

        assert result is False
        sound.play.assert_called_once_with(SoundType.UI_CANCEL)

    def test_restore_raises_oserror_plays_cancel(self, monkeypatch):
        save_manager = MagicMock()
        save_manager.load_game.return_value = (
            {"tick": 1, "units": [{"id": "u1"}]},
            SaveMetaData(),
            SaveSlotStatus.OK,
        )
        controller = SaveController(save_manager=save_manager)
        sound = MagicMock()
        loop = StubGameLoop(_make_game_state(), sound_system=sound)

        def _raise(data, game_loop):
            raise OSError("io fail")

        monkeypatch.setattr(controller, "restore_state", _raise)

        result = controller.quick_load(slot=0, game_loop=loop)

        assert result is False
        sound.play.assert_called_once_with(SoundType.UI_CANCEL)

    def test_load_without_sound_does_not_crash_on_failure(self):
        save_manager = MagicMock()
        save_manager.load_game.return_value = (None, None, SaveSlotStatus.EMPTY)
        controller = SaveController(save_manager=save_manager)
        loop = StubGameLoop(_make_game_state(), sound_system=None)

        assert controller.quick_load(slot=0, game_loop=loop) is False


# ===========================================================================
# list_saves
# ===========================================================================


@pytest.mark.unit
class TestListSaves:
    def test_no_save_manager_returns_empty_list(self):
        controller = SaveController(save_manager=None)
        assert controller.list_saves() == []

    def test_returns_manager_slots(self, tmp_manager):
        controller = SaveController(save_manager=tmp_manager)
        # Populate slot 0 so at least one slot is non-empty.
        tmp_manager.save_game(0, {"tick": 1})

        result = controller.list_saves()

        assert isinstance(result, list)
        assert len(result) == SecureSaveManager.MAX_SLOTS
        # Slot 0 should be OK, others EMPTY.
        idx0, _, status0 = result[0]
        assert idx0 == 0
        assert status0 == SaveSlotStatus.OK
        _, _, status1 = result[1]
        assert status1 == SaveSlotStatus.EMPTY

    def test_delegates_to_mock_manager(self):
        save_manager = MagicMock()
        expected = [(0, None, SaveSlotStatus.EMPTY)]
        save_manager.list_all_slots.return_value = expected
        controller = SaveController(save_manager=save_manager)

        assert controller.list_saves() is expected
        save_manager.list_all_slots.assert_called_once()


# ===========================================================================
# export_state
# ===========================================================================


@pytest.mark.unit
class TestExportState:
    def test_delegates_to_manager_export(self):
        """When save_manager has export_state_from_game_loop, controller delegates."""
        save_manager = MagicMock()
        exported = {"tick": 10, "units": []}
        save_manager.export_state_from_game_loop.return_value = exported
        controller = SaveController(save_manager=save_manager)
        loop = StubGameLoop(_make_game_state())

        result = controller.export_state(loop)

        assert result is exported
        save_manager.export_state_from_game_loop.assert_called_once_with(loop)

    def test_manual_serialization_structure(self):
        """Without export_state_from_game_loop, controller serializes manually."""
        controller = SaveController(save_manager=None)
        ally = _make_unit("u1", Faction.ALLIES, hp=90, max_hp=100, tile=(3, 4))
        axis = _make_unit(
            "u2",
            Faction.AXIS,
            unit_type=UnitType.MACHINE_GUN_SQUAD,
            hp=60,
            max_hp=80,
            tile=(10, 8),
        )
        state = _make_game_state(
            units=[ally, axis],
            tick=1234,
            paused=True,
            camera_pos=(256.0, 512.0),
            zoom=2.0,
            selected=["u1"],
        )
        loop = StubGameLoop(state)

        result = controller.export_state(loop)

        assert result["tick"] == 1234
        assert result["paused"] is True
        assert result["camera"]["position"]["x"] == 256.0
        assert result["camera"]["position"]["y"] == 512.0
        assert result["camera"]["zoom"] == 2.0
        assert result["selected_unit_ids"] == ["u1"]
        assert len(result["units"]) == 2

    def test_manual_serialization_unit_fields(self):
        """Each manually-serialized unit dict contains all required keys."""
        controller = SaveController(save_manager=None)
        unit = _make_unit("u1", Faction.ALLIES, hp=90, max_hp=100, tile=(3, 4))
        # Give the weapon a non-default reload state for thorough coverage.
        unit.weapon.start_reload(reload_ticks=3)
        state = _make_game_state(units=[unit], tick=1)
        loop = StubGameLoop(state)

        result = controller.export_state(loop)

        ud = result["units"][0]
        assert ud["id"] == "u1"
        assert ud["name"] == "Unit u1"
        assert ud["faction"] == "ALLIES"
        assert ud["unit_type"] == "INFANTRY_SQUAD"
        assert ud["health"] == {"hp": 90, "max_hp": 100, "state": "HEALTHY"}
        assert ud["morale"]["value"] == 80
        assert "panic_threshold" in ud["morale"]
        assert "suppression" in ud["morale"]
        assert "state" in ud["morale"]
        assert ud["weapon"]["primary_weapon_id"] == "rifle"
        assert ud["weapon"]["ammo_remaining"] == 8
        assert ud["weapon"]["max_ammo"] == 10
        assert ud["weapon"]["reload_ticks_left"] == 3
        assert ud["weapon"]["state"] == "RELOADING"
        assert ud["position"]["tile_coord"] == {"x": 3, "y": 4}
        assert "pixel_offset" in ud["position"]
        assert "x" in ud["position"]["pixel_offset"]
        assert "y" in ud["position"]["pixel_offset"]
        assert "facing_rad" in ud["position"]
        assert ud["vision"]["range_tiles"] == 5
        assert "angle_rad" in ud["vision"]
        assert "squad_id" in ud

    def test_manual_serialization_no_units(self):
        controller = SaveController(save_manager=None)
        loop = StubGameLoop(_make_game_state(units=[], tick=0))

        result = controller.export_state(loop)

        assert result["units"] == []
        assert result["tick"] == 0


# ===========================================================================
# restore_state
# ===========================================================================


@pytest.mark.unit
class TestRestoreState:
    def test_success_rebuilds_state_fields(self):
        controller = SaveController()
        state = _make_game_state(units=[], tick=0, paused=False)
        loop = StubGameLoop(state)

        result = controller.restore_state(_sample_state_dict(), loop)

        assert result is True
        assert state.tick == 999
        assert state.paused is True
        assert state.camera.position.x == 50.0
        assert state.camera.position.y == 60.0
        assert state.camera.zoom == 2.0
        assert state.selected_unit_ids == {"u1", "u2"}
        assert len(state.units) == 1

    def test_success_rebuilds_unit_components(self):
        controller = SaveController()
        state = _make_game_state(units=[])
        loop = StubGameLoop(state)

        controller.restore_state(_sample_state_dict(), loop)

        unit = state.units[0]
        assert unit.id == "u1"
        assert unit.name == "Rifle Squad"
        assert unit.faction == Faction.ALLIES
        assert unit.unit_type == UnitType.INFANTRY_SQUAD
        assert unit.health.hp == 80
        assert unit.health.max_hp == 100
        assert unit.health.state == HealthState.WOUNDED
        assert unit.morale.value == 50
        assert unit.morale.suppression == 10
        assert unit.morale.state == MoraleState.WAVERING
        assert unit.weapon.primary_weapon_id == "rifle"
        assert unit.weapon.ammo_remaining == 5
        assert unit.weapon.state == WeaponState.READY
        assert unit.position.tile_coord == TileCoord(3, 4)
        assert unit.position.pixel_offset == Vec2(1.0, 2.0)
        assert unit.position.facing_rad == 0.5
        assert unit.vision.range_tiles == 6
        assert unit.squad_id == "squad_1"

    def test_empty_units_returns_false(self):
        controller = SaveController()
        state = _make_game_state(units=[_make_unit("existing")])
        loop = StubGameLoop(state)

        result = controller.restore_state({"tick": 5, "units": []}, loop)

        assert result is False
        # Tick is still set even when units empty (set before the units check).
        assert state.tick == 5

    def test_all_units_invalid_returns_false(self):
        """Every unit dict raises KeyError → new_units empty → False."""
        controller = SaveController()
        state = _make_game_state(units=[])
        loop = StubGameLoop(state)

        data = {
            "tick": 1,
            "units": [
                {"faction": "INVALID_FACTION", "unit_type": "INFANTRY_SQUAD"},
                {"faction": "ALLIES", "unit_type": "INVALID_UNIT_TYPE"},
            ],
        }
        result = controller.restore_state(data, loop)

        assert result is False
        assert state.units == []

    def test_partial_failure_keeps_valid_units(self):
        """Invalid units are skipped; valid ones are restored."""
        controller = SaveController()
        state = _make_game_state(units=[])
        loop = StubGameLoop(state)

        data = {
            "tick": 1,
            "units": [
                {"id": "bad", "faction": "NOPE"},  # KeyError → skipped
                {
                    "id": "good",
                    "name": "Good Squad",
                    "faction": "AXIS",
                    "unit_type": "INFANTRY_SQUAD",
                    "health": {"hp": 100, "max_hp": 100, "state": "HEALTHY"},
                    "morale": {"value": 85, "panic_threshold": 20, "suppression": 0, "state": "RALLIED"},
                    "weapon": {
                        "primary_weapon_id": "rifle",
                        "ammo_remaining": 10,
                        "max_ammo": 10,
                        "reload_ticks_left": 0,
                        "state": "READY",
                    },
                    "position": {
                        "tile_coord": {"x": 1, "y": 2},
                        "pixel_offset": {"x": 0.0, "y": 0.0},
                        "facing_rad": 0.0,
                    },
                    "vision": {"range_tiles": 5, "angle_rad": 3.0},
                    "squad_id": None,
                },
            ],
        }
        result = controller.restore_state(data, loop)

        assert result is True
        assert len(state.units) == 1
        assert state.units[0].id == "good"
        assert state.units[0].faction == Faction.AXIS

    def test_renderer_animators_and_emitter_cleared(self):
        controller = SaveController()
        state = _make_game_state(units=[])
        renderer = StubRenderer()
        loop = StubGameLoop(state, renderer=renderer)

        assert renderer._unit_animators == [1, 2, 3]
        assert renderer._particle_emitter == [4, 5]

        controller.restore_state(_sample_state_dict(), loop)

        assert renderer._unit_animators == []
        assert renderer._particle_emitter == []

    def test_missing_camera_data_uses_defaults(self):
        """When camera key absent, camera is not mutated beyond Vec2 default."""
        controller = SaveController()
        state = _make_game_state(units=[], camera_pos=(10.0, 20.0), zoom=1.0)
        loop = StubGameLoop(state)

        data = {"tick": 7, "units": [
            {
                "id": "x",
                "faction": "ALLIES",
                "unit_type": "INFANTRY_SQUAD",
                "health": {"hp": 100, "max_hp": 100, "state": "HEALTHY"},
                "morale": {"value": 80, "panic_threshold": 20, "suppression": 0, "state": "RALLIED"},
                "weapon": {
                    "primary_weapon_id": "rifle",
                    "ammo_remaining": 10,
                    "max_ammo": 10,
                    "reload_ticks_left": 0,
                    "state": "READY",
                },
                "position": {
                    "tile_coord": {"x": 0, "y": 0},
                    "pixel_offset": {"x": 0.0, "y": 0.0},
                    "facing_rad": 0.0,
                },
                "vision": {"range_tiles": 5, "angle_rad": 3.0},
                "squad_id": None,
            }
        ]}
        result = controller.restore_state(data, loop)

        assert result is True
        assert state.tick == 7
        # Camera data absent → camera unchanged from initial state.
        assert state.camera.position.x == 10.0
        assert state.camera.zoom == 1.0

    def test_round_trip_export_then_restore(self):
        """Manual export_state output is consumable by restore_state."""
        controller = SaveController(save_manager=None)
        original_unit = _make_unit("rt", Faction.ALLIES, hp=70, max_hp=100, tile=(7, 8))
        original_state = _make_game_state(
            units=[original_unit], tick=321, paused=True, selected=["rt"]
        )
        loop = StubGameLoop(original_state)

        exported = controller.export_state(loop)

        # Fresh state to restore into.
        target_state = _make_game_state(units=[])
        target_loop = StubGameLoop(target_state)

        result = controller.restore_state(exported, target_loop)

        assert result is True
        assert target_state.tick == 321
        assert target_state.paused is True
        assert target_state.selected_unit_ids == {"rt"}
        assert len(target_state.units) == 1
        assert target_state.units[0].id == "rt"
        assert target_state.units[0].health.hp == 70
        assert target_state.units[0].position.tile_coord == TileCoord(7, 8)
