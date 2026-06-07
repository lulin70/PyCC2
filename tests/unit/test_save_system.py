from __future__ import annotations

import json
from dataclasses import asdict
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
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.infrastructure.save_system import (
    SaveMetaData,
    SaveSlotStatus,
    SecureSaveManager,
)
from pycc2.presentation.rendering.camera import Camera


@pytest.fixture
def tmp_save_dir(tmp_path):
    d = tmp_path / "test_saves"
    return d


@pytest.fixture
def manager(tmp_save_dir):
    return SecureSaveManager(base_dir=tmp_save_dir)


@pytest.fixture
def sample_state_dict():
    return {
        "tick": 1234,
        "paused": False,
        "side_turn": "allies",
        "camera": {"position": {"x": 100.0, "y": 200.0}, "zoom": 1.5},
        "selected_unit_ids": ["unit_1", "unit_2"],
        "units": [
            {
                "id": "unit_1",
                "name": "Rifle Squad",
                "faction": "ALLIES",
                "unit_type": "INFANTRY_SQUAD",
                "health": {"hp": 100, "max_hp": 100, "state": "HEALTHY"},
                "morale": {"value": 85, "panic_threshold": 20, "suppression": 0, "state": "STEADY"},
                "weapon": {
                    "primary_weapon_id": "rifle",
                    "ammo_remaining": 10,
                    "max_ammo": 10,
                    "reload_ticks_left": 0,
                    "state": "READY",
                },
                "position": {
                    "tile_coord": {"x": 3, "y": 3},
                    "pixel_offset": {"x": 0, "y": 0},
                    "facing_rad": 0.0,
                },
                "vision": {"range_tiles": 5, "angle_rad": 1.57},
                "squad_id": None,
                "is_alive": True,
            }
        ],
        "battle_stats": {"allies_kills": 5, "axis_kills": 2, "ticks_elapsed": 1234},
    }


class TestSecureSaveManager:
    def test_init_creates_saves_directory(self, tmp_save_dir):
        mgr = SecureSaveManager(base_dir=tmp_save_dir)
        assert mgr._save_dir.exists()
        assert mgr._save_dir.is_dir()

    def test_save_and_load_returns_ok_status(self, manager, sample_state_dict):
        result = manager.save_game(0, sample_state_dict)
        assert result is True
        _, meta, status = manager.load_game(0)
        assert status == SaveSlotStatus.OK

    def test_saved_data_matches_loaded_data(self, manager, sample_state_dict):
        manager.save_game(0, sample_state_dict)
        loaded_state, _, _ = manager.load_game(0)
        assert loaded_state is not None
        assert loaded_state["tick"] == sample_state_dict["tick"]
        assert loaded_state["side_turn"] == sample_state_dict["side_turn"]
        assert len(loaded_state["units"]) == len(sample_state_dict["units"])
        assert loaded_state["camera"]["zoom"] == sample_state_dict["camera"]["zoom"]

    def test_load_nonexistent_slot_returns_empty(self, manager):
        _, _, status = manager.load_game(5)
        assert status == SaveSlotStatus.EMPTY

    def test_delete_save_works(self, manager, sample_state_dict):
        manager.save_game(0, sample_state_dict)
        assert manager.delete_save(0) is True
        _, _, status = manager.load_game(0)
        assert status == SaveSlotStatus.EMPTY

    def test_delete_nonexistent_returns_false(self, manager):
        assert manager.delete_save(7) is False

    def test_invalid_slot_raises_valueerror(self, manager):
        with pytest.raises(ValueError, match="Slot must be"):
            manager._slot_path(-1)
        with pytest.raises(ValueError, match="Slot must be"):
            manager._slot_path(8)
        with pytest.raises(ValueError, match="Slot must be"):
            manager._slot_path(100)

    def test_hmac_prevents_tampering_detect(self, manager, sample_state_dict):
        manager.save_game(0, sample_state_dict)
        filepath = manager._slot_path(0)
        with open(filepath, encoding="utf-8") as f:
            content = json.loads(f.read())
        content["state"]["tick"] = 99999
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content, f)
        _, _, status = manager.load_game(0)
        assert status == SaveSlotStatus.CORRUPTED

    def test_hmac_missing_returns_corrupted(self, manager, sample_state_dict):
        manager.save_game(0, sample_state_dict)
        filepath = manager._slot_path(0)
        with open(filepath, encoding="utf-8") as f:
            content = json.loads(f.read())
        del content["hmac"]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content, f)
        _, _, status = manager.load_game(0)
        assert status == SaveSlotStatus.CORRUPTED

    def test_version_mismatch_returns_incompatible(self, manager, sample_state_dict):
        manager.save_game(0, sample_state_dict)
        filepath = manager._slot_path(0)
        with open(filepath, encoding="utf-8") as f:
            content = json.loads(f.read())
        content["meta"]["version"] = "0.99"
        payload_for_check = {"meta": content["meta"], "state": content["state"]}
        payload_json = manager._serialize_state(payload_for_check)
        new_hmac = manager._compute_hmac(payload_json.encode("utf-8"))
        content["hmac"] = new_hmac
        final_json = manager._serialize_state(content)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_json)
        _, _, status = manager.load_game(0)
        assert status == SaveSlotStatus.INCOMPATIBLE

    def test_metadata_is_populated_on_save(self, manager, sample_state_dict):
        manager.save_game(0, sample_state_dict)
        _, meta, _ = manager.load_game(0)
        assert meta is not None
        assert meta.version == "0.1.1"
        assert meta.saved_at != ""
        assert "T" in meta.saved_at or "t" in meta.saved_at.lower() or len(meta.saved_at) > 10

    def test_find_empty_slot_when_space(self, manager):
        slot = manager.find_empty_slot()
        assert slot == 0
        manager.save_game(0, {"tick": 1})
        slot = manager.find_empty_slot()
        assert slot == 1

    def test_find_none_when_full(self, manager):
        for i in range(manager.MAX_SLOTS):
            manager.save_game(i, {"tick": i})
        assert manager.find_empty_slot() is None

    def test_list_all_slots_returns_max_entries(self, manager):
        slots = manager.list_all_slots()
        assert len(slots) == SecureSaveManager.MAX_SLOTS
        for i, (idx, meta, status) in enumerate(slots):
            assert idx == i
            assert status == SaveSlotStatus.EMPTY

    def test_multiple_slots_independent(self, manager):
        state_a = {"tick": 100, "data": "alpha"}
        state_b = {"tick": 200, "data": "beta"}
        manager.save_game(0, state_a)
        manager.save_game(1, state_b)
        loaded_a, _, _ = manager.load_game(0)
        loaded_b, _, _ = manager.load_game(1)
        assert loaded_a["data"] == "alpha"
        assert loaded_b["data"] == "beta"

    def test_overwrite_existing_slot(self, manager):
        manager.save_game(0, {"tick": 100, "val": "old"})
        manager.save_game(0, {"tick": 200, "val": "new"})
        loaded, _, _ = manager.load_game(0)
        assert loaded["tick"] == 200
        assert loaded["val"] == "new"

    def test_save_with_custom_metadata(self, manager, sample_state_dict):
        custom_meta = SaveMetaData(
            tick=5000,
            mission_id="mission_01",
            allies_alive=6,
            axis_alive=4,
            game_result="ongoing",
            playtime_seconds=300.5,
            notes="Before final assault",
        )
        manager.save_game(0, sample_state_dict, meta=custom_meta)
        _, meta, _ = manager.load_game(0)
        assert meta.tick == 5000
        assert meta.mission_id == "mission_01"
        assert meta.allies_alive == 6
        assert meta.axis_alive == 4
        assert meta.notes == "Before final assault"

    def test_unicode_in_metadata(self, manager, sample_state_dict):
        unicode_meta = SaveMetaData(notes="存档测试 — 中文描述 🎮")
        manager.save_game(0, sample_state_dict, meta=unicode_meta)
        _, meta, _ = manager.load_game(0)
        assert "中文" in meta.notes


class TestSaveMetaData:
    def test_default_values(self):
        meta = SaveMetaData()
        assert meta.version == "0.1.1"
        assert meta.saved_at == ""
        assert meta.tick == 0
        assert meta.mission_id == ""
        assert meta.allies_alive == 0
        assert meta.axis_alive == 0
        assert meta.game_result == ""
        assert meta.playtime_seconds == 0.0
        assert meta.notes == ""

    def test_all_fields_serializable(self):
        meta = SaveMetaData(
            version="0.1.1",
            saved_at="2025-01-15T12:00:00+00:00",
            tick=9999,
            mission_id="mission_x",
            allies_alive=10,
            axis_alive=5,
            game_result="allies_victory",
            playtime_seconds=3600.25,
            notes="Test note",
        )
        d = asdict(meta)
        assert isinstance(d, dict)
        assert len(d) == 9
        for v in d.values():
            assert v is not None

    def test_asdict_roundtrip(self):
        original = SaveMetaData(tick=42, allies_alive=7, axis_alive=3, notes="hello")
        d = asdict(original)
        restored = SaveMetaData(**{k: v for k, v in d.items()})
        assert restored.tick == original.tick
        assert restored.allies_alive == original.allies_alive
        assert restored.notes == original.notes


class TestExportState:
    @pytest.fixture
    def mock_game_loop(self):
        grid = np.zeros((16, 16), dtype=np.int8)
        game_map = GameMap(id="test", name="Test Map", width=16, height=16, tile_grid=grid)
        camera = Camera(position=Vec2(256.0, 256.0), viewport_width=1280, viewport_height=720)
        units = [
            Unit(
                id="u1",
                name="Rifle Squad Alpha",
                faction=Faction.ALLIES,
                unit_type=UnitType.INFANTRY_SQUAD,
                health=HealthComponent(hp=95, max_hp=100),
                morale=MoraleComponent(value=80),
                weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=8, max_ammo=10),
                position=PositionComponent(tile_coord=TileCoord(5, 5)),
                vision=VisionComponent(range_tiles=5),
            ),
            Unit(
                id="u2",
                name="MG Team Bravo",
                faction=Faction.AXIS,
                unit_type=UnitType.MACHINE_GUN_SQUAD,
                health=HealthComponent(hp=60, max_hp=80),
                morale=MoraleComponent(value=70),
                weapon=WeaponComponent(primary_weapon_id="mg42", ammo_remaining=40, max_ammo=50),
                position=PositionComponent(tile_coord=TileCoord(10, 8)),
                vision=VisionComponent(range_tiles=6),
            ),
        ]
        from pycc2.services.game_loop import GameState

        state = GameState(game_map=game_map, units=units, camera=camera, tick=5678)

        loop = MagicMock()
        loop.state = state
        loop.victory_manager = MagicMock()
        loop.victory_manager.battle_stats = MagicMock()
        loop.victory_manager.battle_stats.allies_kills = 3
        loop.victory_manager.battle_stats.axis_kills = 1
        loop.victory_manager.battle_stats.ticks_elapsed = 5678
        return loop

    def test_export_produces_valid_dict(self, manager, mock_game_loop):
        exported = manager.export_state_from_game_loop(mock_game_loop)
        assert isinstance(exported, dict)
        assert "version" in exported
        assert "tick" in exported
        assert "units" in exported
        assert "camera" in exported

    def test_export_contains_units(self, manager, mock_game_loop):
        exported = manager.export_state_from_game_loop(mock_game_loop)
        assert len(exported["units"]) == 2
        unit_ids = {u["id"] for u in exported["units"]}
        assert unit_ids == {"u1", "u2"}

    def test_export_contains_camera(self, manager, mock_game_loop):
        exported = manager.export_state_from_game_loop(mock_game_loop)
        cam = exported["camera"]
        assert cam["position"]["x"] == 256.0
        assert cam["position"]["y"] == 256.0
        assert "zoom" in cam

    def test_export_contains_tick(self, manager, mock_game_loop):
        exported = manager.export_state_from_game_loop(mock_game_loop)
        assert exported["tick"] == 5678

    def test_export_handles_no_battle_stats(self, manager, mock_game_loop):
        mock_game_loop.victory_manager = None
        exported = manager.export_state_from_game_loop(mock_game_loop)
        assert exported["battle_stats"] == {}
