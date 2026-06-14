from __future__ import annotations

import json
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
from pycc2.infrastructure.save_system import SaveSlotStatus, SecureSaveManager
from pycc2.presentation.rendering.camera import Camera
from pycc2.services.game_loop import GameLoop, GameState
from pycc2.services.save_controller import SaveController


@pytest.fixture
def tmp_save_dir(tmp_path):
    d = tmp_path / "e2e_saves"
    return d


@pytest.fixture
def secure_manager(tmp_save_dir):
    return SecureSaveManager(base_dir=tmp_save_dir)


@pytest.fixture
def save_controller(secure_manager):
    controller = SaveController(save_manager=secure_manager)
    return controller


@pytest.fixture
def sample_game_map():
    grid = np.zeros((16, 16), dtype=np.int8)
    grid[4:6, 4:8] = 3
    grid[8:10, 8:12] = 5
    return GameMap(id="save_test", name="Save Test Map", width=16, height=16, tile_grid=grid)


@pytest.fixture
def sample_units():
    return [
        Unit(
            id="ally_inf_1",
            name="Alpha Squad",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=85, max_hp=100),
            morale=MoraleComponent(value=80),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=7, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(3, 5)),
            vision=VisionComponent(range_tiles=5),
        ),
        Unit(
            id="axis_mg_1",
            name="Enemy MG",
            faction=Faction.AXIS,
            unit_type=UnitType.MACHINE_GUN_SQUAD,
            health=HealthComponent(hp=45, max_hp=80),
            morale=MoraleComponent(value=60),
            weapon=WeaponComponent(primary_weapon_id="mg42", ammo_remaining=30, max_ammo=50),
            position=PositionComponent(tile_coord=TileCoord(10, 12)),
            vision=VisionComponent(range_tiles=6),
        ),
        Unit(
            id="ally_cmd_1",
            name="Cpt. Miller",
            faction=Faction.ALLIES,
            unit_type=UnitType.COMMANDER,
            health=HealthComponent(hp=100, max_hp=120),
            morale=MoraleComponent(value=92),
            weapon=WeaponComponent(primary_weapon_id="pistol", ammo_remaining=12, max_ammo=14),
            position=PositionComponent(tile_coord=TileCoord(5, 3)),
            vision=VisionComponent(range_tiles=7),
        ),
    ]


@pytest.fixture
def mock_game_loop(sample_game_map, sample_units):
    camera = Camera(position=Vec2(300.0, 250.0), viewport_width=1280, viewport_height=720)
    state = GameState(
        game_map=sample_game_map,
        units=sample_units,
        camera=camera,
        tick=5678,
        paused=False,
    )
    loop = MagicMock(spec=GameLoop)
    loop.state = state
    loop.sound_system = None
    loop.renderer = MagicMock()
    loop._victory_manager = MagicMock()
    loop._victory_manager.battle_stats = MagicMock()
    loop._victory_manager.battle_stats.allies_kills = 5
    loop._victory_manager.battle_stats.axis_kills = 2
    loop._victory_manager.battle_stats.ticks_elapsed = 5678
    return loop


class TestSaveGameCreatesFile:
    def test_save_game_creates_file(self, save_controller, mock_game_loop, tmp_save_dir):
        result = save_controller.quick_save(slot=0, game_loop=mock_game_loop)
        assert result is True, "存档操作应成功"
        slot_path = tmp_save_dir / "save_slot_0.json"
        assert slot_path.exists(), "存档文件应被创建"
        assert slot_path.stat().st_size > 0, "存档文件不应为空"

    def test_save_file_contains_valid_json(self, save_controller, mock_game_loop, tmp_save_dir):
        save_controller.quick_save(slot=1, game_loop=mock_game_loop)
        slot_path = tmp_save_dir / "save_slot_1.json"
        with open(slot_path, encoding="utf-8") as f:
            content = json.load(f)
        assert isinstance(content, dict), "存档文件应为有效的JSON字典"
        assert "meta" in content, "存档应包含meta字段"
        assert "state" in content, "存档应包含state字段"
        assert "hmac" in content, "存档应包含HMAC校验字段"

    def test_save_metadata_populated(self, save_controller, mock_game_loop, tmp_save_dir):
        save_controller.quick_save(slot=2, game_loop=mock_game_loop)
        slot_path = tmp_save_dir / "save_slot_2.json"
        with open(slot_path, encoding="utf-8") as f:
            content = json.load(f)
        meta = content["meta"]
        assert meta["tick"] == 5678, "元数据中的tick值应正确"
        assert meta["allies_alive"] == 2, "元数据中盟军存活数应正确"
        assert meta["axis_alive"] == 1, "元数据中轴心国存活数应正确"


class TestLoadGameRestoresState:
    def test_save_produces_valid_state_dict(self, save_controller, mock_game_loop, tmp_save_dir):
        save_controller.quick_save(slot=0, game_loop=mock_game_loop)
        state_dict, meta, status = save_controller.save_manager.load_game(0)
        assert status.name in ("OK", "INCOMPATIBLE"), "存档应能被成功加载"
        assert state_dict is not None, "加载的状态字典不应为空"
        assert "tick" in state_dict, "状态字典应包含tick字段"
        assert "units" in state_dict, "状态字典应包含units字段"
        assert "camera" in state_dict, "状态字典应包含camera字段"

    def test_saved_state_preserves_tick(self, save_controller, mock_game_loop, tmp_save_dir):
        original_tick = mock_game_loop.state.tick
        save_controller.quick_save(slot=0, game_loop=mock_game_loop)
        state_dict, _, _ = save_controller.save_manager.load_game(0)
        assert state_dict["tick"] == original_tick, "存档中的tick值应与保存时一致"

    def test_saved_state_preserves_unit_count(self, save_controller, mock_game_loop, tmp_save_dir):
        original_count = len(mock_game_loop.state.units)
        save_controller.quick_save(slot=0, game_loop=mock_game_loop)
        state_dict, _, _ = save_controller.save_manager.load_game(0)
        assert len(state_dict["units"]) == original_count, "存档中的单位数量应与保存时一致"

    def test_saved_state_preserves_unit_positions(
        self, save_controller, mock_game_loop, tmp_save_dir
    ):
        original_positions = {
            u.id: (u.position.tile_coord.x, u.position.tile_coord.y)
            for u in mock_game_loop.state.units
        }
        save_controller.quick_save(slot=0, game_loop=mock_game_loop)
        state_dict, _, _ = save_controller.save_manager.load_game(0)
        for unit_data in state_dict["units"]:
            saved_pos = (
                unit_data["position"]["tile_coord"]["x"],
                unit_data["position"]["tile_coord"]["y"],
            )
            assert saved_pos == original_positions[unit_data["id"]], (
                f"单位 {unit_data['id']} 的位置应被正确保存"
            )

    def test_saved_state_preserves_unit_hp(self, save_controller, mock_game_loop, tmp_save_dir):
        original_hp = {u.id: u.health.hp for u in mock_game_loop.state.units}
        save_controller.quick_save(slot=0, game_loop=mock_game_loop)
        state_dict, _, _ = save_controller.save_manager.load_game(0)
        for unit_data in state_dict["units"]:
            assert unit_data["health"]["hp"] == original_hp[unit_data["id"]], (
                f"单位 {unit_data['id']} 的HP应被正确保存"
            )

    def test_saved_state_preserves_camera(self, save_controller, mock_game_loop, tmp_save_dir):
        original_zoom = mock_game_loop.state.camera.zoom
        original_x = mock_game_loop.state.camera.position.x
        original_y = mock_game_loop.state.camera.position.y
        save_controller.quick_save(slot=0, game_loop=mock_game_loop)
        state_dict, _, _ = save_controller.save_manager.load_game(0)
        assert state_dict["camera"]["zoom"] == original_zoom, "相机缩放应被正确保存"
        assert state_dict["camera"]["position"]["x"] == original_x, "相机X位置应被正确保存"
        assert state_dict["camera"]["position"]["y"] == original_y, "相机Y位置应被正确保存"


class TestQuickSaveQuickLoadCycle:
    def test_quick_save_quick_load_cycle(self, secure_manager, mock_game_loop, tmp_save_dir):
        initial_tick = mock_game_loop.state.tick
        initial_units_data = [
            {
                "id": u.id,
                "hp": u.health.hp,
                "pos": (u.position.tile_coord.x, u.position.tile_coord.y),
                "ammo": u.weapon.ammo_remaining,
            }
            for u in mock_game_loop.state.units
        ]
        from pycc2.infrastructure.save_system import SaveMetaData

        state_dict = (
            save_controller.export_state(mock_game_loop) if "save_controller" in dir() else None
        )
        if state_dict is None:
            from pycc2.services.save_controller import SaveController

            ctrl = SaveController(save_manager=secure_manager)
            state_dict = ctrl.export_state(mock_game_loop)
        meta = SaveMetaData(
            tick=mock_game_loop.state.tick,
            allies_alive=sum(
                1 for u in mock_game_loop.state.units if u.faction.name == "ALLIES" and u.is_alive
            ),
            axis_alive=sum(
                1 for u in mock_game_loop.state.units if u.faction.name == "AXIS" and u.is_alive
            ),
        )
        secure_manager.save_game(0, state_dict, meta)

        for unit in mock_game_loop.state.units:
            unit.take_damage(30)
            unit.weapon.ammo_remaining = max(0, unit.weapon.ammo_remaining - 3)
        mock_game_loop.state.tick += 1000

        loaded_state, _, status = secure_manager.load_game(0)
        assert status.name in ("OK", "INCOMPATIBLE"), "快存的数据应能被成功读取"
        assert loaded_state["tick"] == initial_tick, "快存快读循环：tick应恢复原值"
        for i, expected in enumerate(initial_units_data):
            unit_data = loaded_state["units"][i]
            assert unit_data["health"]["hp"] == expected["hp"], "快存快读循环：单位HP应匹配"
            assert unit_data["weapon"]["ammo_remaining"] == expected["ammo"], (
                "快存快读循环：弹药应匹配"
            )

    def test_multiple_cycles_preserve_integrity(self, secure_manager, mock_game_loop, tmp_save_dir):
        from pycc2.infrastructure.save_system import SaveMetaData
        from pycc2.services.save_controller import SaveController

        ctrl = SaveController(save_manager=secure_manager)
        for cycle in range(5):
            tick_before = mock_game_loop.state.tick
            hp_before = [u.health.hp for u in mock_game_loop.state.units]
            state_dict = ctrl.export_state(mock_game_loop)
            meta = SaveMetaData(tick=tick_before)
            secure_manager.save_game(0, state_dict, meta)

            for unit in mock_game_loop.state.units:
                unit.take_damage(10)
            mock_game_loop.state.tick += 500

            loaded_state, _, status = secure_manager.load_game(0)
            assert status.name in ("OK", "INCOMPATIBLE"), f"第{cycle + 1}轮：数据应可读"
            assert loaded_state["tick"] == tick_before, f"第{cycle + 1}轮循环：tick应恢复"
            for i, unit_data in enumerate(loaded_state["units"]):
                assert unit_data["health"]["hp"] == hp_before[i], (
                    f"第{cycle + 1}轮循环：单位HP应恢复"
                )

    def test_quick_save_overwrites_previous(self, secure_manager, mock_game_loop, tmp_save_dir):
        from pycc2.infrastructure.save_system import SaveMetaData
        from pycc2.services.save_controller import SaveController

        ctrl = SaveController(save_manager=secure_manager)
        mock_game_loop.state.tick = 1000
        state_dict = ctrl.export_state(mock_game_loop)
        secure_manager.save_game(0, state_dict, SaveMetaData(tick=1000))
        mock_game_loop.state.tick = 2000
        state_dict = ctrl.export_state(mock_game_loop)
        secure_manager.save_game(0, state_dict, SaveMetaData(tick=2000))
        mock_game_loop.state.tick = 9999

        loaded_state, _, status = secure_manager.load_game(0)
        assert loaded_state["tick"] == 2000, "快存应覆盖之前的存档"


class TestCorruptedSaveRejected:
    def test_corrupted_save_rejected(self, secure_manager, tmp_save_dir):

        sample_state = {"tick": 1234, "units": [{"id": "u1", "faction": "ALLIES"}]}
        secure_manager.save_game(0, sample_state)
        filepath = secure_manager._slot_path(0)
        with open(filepath, encoding="utf-8") as f:
            content = json.loads(f.read())
        content["state"]["tick"] = 99999
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content, f)
        _, _, status = secure_manager.load_game(0)
        assert status == SaveSlotStatus.CORRUPTED, "被篡改的存档应被拒绝（HMAC校验失败）"

    def test_corrupted_save_rejected_by_controller(
        self, save_controller, mock_game_loop, tmp_save_dir
    ):
        save_controller.quick_save(slot=0, game_loop=mock_game_loop)
        filepath = tmp_save_dir / "save_slot_0.json"
        with open(filepath, encoding="utf-8") as f:
            content = json.loads(f.read())
        content["state"]["tick"] = 77777
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content, f)
        result = save_controller.quick_load(slot=0, game_loop=mock_game_loop)
        assert result is False, "控制器应拒绝被篡改的存档并返回False"

    def test_tampered_unit_data_rejected(self, secure_manager, tmp_save_dir):
        tampered_state = {
            "tick": 100,
            "units": [
                {
                    "id": "hacked_unit",
                    "name": "God Mode",
                    "faction": "ALLIES",
                    "unit_type": "COMMANDER",
                    "health": {"hp": 99999, "max_hp": 99999},
                    "position": {"tile_coord": {"x": 0, "y": 0}},
                }
            ],
        }
        secure_manager.save_game(0, tampered_state)
        filepath = secure_manager._slot_path(0)
        with open(filepath, encoding="utf-8") as f:
            content = json.loads(f.read())
        content["state"]["units"][0]["health"]["hp"] = 999999
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content, f)
        _, _, status = secure_manager.load_game(0)
        assert status == SaveSlotStatus.CORRUPTED, "篡改单位数据的存档应被拒绝"

    def test_missing_hmac_rejected(self, secure_manager, tmp_save_dir):
        sample_state = {"tick": 111}
        secure_manager.save_game(0, sample_state)
        filepath = secure_manager._slot_path(0)
        with open(filepath, encoding="utf-8") as f:
            content = json.loads(f.read())
        del content["hmac"]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(content, f)
        _, _, status = secure_manager.load_game(0)
        assert status == SaveSlotStatus.CORRUPTED, "缺少HMAC字段的存档应被视为损坏"


class TestSaveLoadEdgeCases:
    def test_load_nonexistent_slot_returns_false(self, save_controller, mock_game_loop):
        result = save_controller.quick_load(slot=5, game_loop=mock_game_loop)
        assert result is False, "加载不存在的存档槽位应返回False"

    def test_save_without_game_loop_returns_false(self, save_controller):
        result = save_controller.quick_save(slot=0, game_loop=None)
        assert result is False, "不传入game_loop时保存应返回False"

    def test_load_without_game_loop_returns_false(self, save_controller):
        result = save_controller.quick_load(slot=0, game_loop=None)
        assert result is False, "不传入game_loop时加载应返回False"

    def test_list_saves_returns_list(self, save_controller):
        saves = save_controller.list_saves()
        assert isinstance(saves, list), "list_saves应返回列表"

    def test_uninitialized_controller_fails_gracefully(self):
        controller = SaveController(save_manager=None)
        mock_loop = MagicMock()
        assert controller.quick_save(slot=0, game_loop=mock_loop) is False
        assert controller.quick_load(slot=0, game_loop=mock_loop) is False

    def test_save_load_with_minimal_unit_data(self, secure_manager, tmp_save_dir):
        minimal_state = {
            "tick": 100,
            "paused": False,
            "side_turn": "allies",
            "camera": {"position": {"x": 0.0, "y": 0.0}, "zoom": 1.0},
            "selected_unit_ids": [],
            "units": [
                {
                    "id": "minimal_unit",
                    "name": "Minimal",
                    "faction": "ALLIES",
                    "unit_type": "INFANTRY_SQUAD",
                    "health": {"hp": 50, "max_hp": 100},
                    "morale": {"value": 70},
                    "weapon": {"primary_weapon_id": "rifle", "ammo_remaining": 5, "max_ammo": 10},
                    "position": {"tile_coord": {"x": 1, "y": 1}},
                    "vision": {"range_tiles": 5},
                }
            ],
        }
        result = secure_manager.save_game(0, minimal_state)
        assert result is True, "保存最小化单位数据应成功"
        loaded, _, status = secure_manager.load_game(0)
        assert status.name in ("OK", "INCOMPATIBLE"), "最小化数据应能被加载"
        assert loaded is not None
        assert len(loaded["units"]) == 1
        assert loaded["units"][0]["id"] == "minimal_unit"
