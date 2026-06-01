from __future__ import annotations

import os
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.infrastructure.save_system import SaveSlotStatus, SecureSaveManager
from pycc2.presentation.input.interaction_controller import (
    InteractionController,
)
from pycc2.presentation.rendering.camera import Camera
from pycc2.services.event_bus import EventBus


@pytest.fixture
def tmp_save_dir(tmp_path):
    return tmp_path / "test_saves"


@pytest.fixture
def camera():
    return Camera(position=Vec2(256.0, 256.0), viewport_width=1280, viewport_height=720)


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def game_map():
    gm = MagicMock()
    gm.width = 50
    gm.height = 50
    return gm


@pytest.fixture
def interaction_controller(camera, game_map, event_bus):
    return InteractionController(camera=camera, game_map=game_map, event_bus=event_bus)


class TestHmacKeyFromEnvVar:
    def test_hmac_key_loads_from_env_var(self, tmp_save_dir):
        expected_key = b"test-env-hmac-key-12345"
        with patch.dict(os.environ, {"PYCC2_SAVE_HMAC_KEY": expected_key.decode()}):
            mgr = SecureSaveManager(base_dir=tmp_save_dir)
            assert mgr._hmac_key == expected_key

    def test_hmac_key_env_var_takes_priority_over_file(self, tmp_save_dir):
        expected_key = b"env-wins-over-file-999"
        with patch.dict(os.environ, {"PYCC2_SAVE_HMAC_KEY": expected_key.decode()}):
            mgr = SecureSaveManager(base_dir=tmp_save_dir)
            assert mgr._hmac_key == expected_key


class TestHmacKeyFallbackToFile:
    def test_hmac_key_falls_back_to_config_file(self, tmp_path):
        config_dir = tmp_path / "pycc2" / "config"
        config_dir.mkdir(parents=True)
        secrets_file = config_dir / "secrets.toml"
        secrets_file.write_text('hmac_key = "my-file-based-secret-key-abc123"\n')
        with patch.object(SecureSaveManager, "_get_hmac_key", SecureSaveManager._get_hmac_key):
            with patch.object(
                Path,
                "resolve",
                return_value=tmp_path / "pycc2" / "infrastructure" / "save_system.py",
            ):
                key = SecureSaveManager._get_hmac_key()
        assert key == b"my-file-based-secret-key-abc123"

    def test_get_hmac_key_returns_bytes_even_without_file(self):
        key = SecureSaveManager._get_hmac_key()
        assert isinstance(key, bytes)
        assert len(key) >= 1, f"HMAC key should have at least 1 byte, got {len(key)}"


class TestHmacKeyDefaultWithWarning:
    def test_default_key_warns_when_no_env_or_file(self, tmp_save_dir):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Path, "exists", return_value=False):
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    mgr = SecureSaveManager(base_dir=tmp_save_dir)
                    hmac_warnings = [
                        warning for warning in w if "HMAC key" in str(warning.message)
                    ]
                    assert len(hmac_warnings) >= 1
                    assert mgr._hmac_key is not None
                    assert len(mgr._hmac_key) == 32  # Random key is 32 bytes
                    assert mgr._using_default_key is True

    def test_get_hmac_key_static_method_returns_bytes(self):
        key = SecureSaveManager._get_hmac_key()
        assert isinstance(key, bytes)
        assert len(key) >= 1, f"HMAC key (static) should have at least 1 byte, got {len(key)}"


class TestScreenToTileClamping:
    def test_clamps_negative_x_to_zero(self, interaction_controller):
        tile = interaction_controller.screen_to_tile((-10000.0, 100.0))
        assert tile.x == 0

    def test_clamps_negative_y_to_zero(self, interaction_controller):
        tile = interaction_controller.screen_to_tile((100.0, -10000.0))
        assert tile.y == 0

    def test_clamps_exceeding_max_x(self, interaction_controller):
        tile = interaction_controller.screen_to_tile((99999.0, 100.0))
        assert tile.x <= interaction_controller._game_map.width - 1

    def test_clamps_exceeding_max_y(self, interaction_controller):
        tile = interaction_controller.screen_to_tile((100.0, 99999.0))
        assert tile.y <= interaction_controller._game_map.height - 1

    def test_normal_values_pass_through(self, interaction_controller):
        tile = interaction_controller.screen_to_tile((300.0, 300.0))
        assert 0 <= tile.x < interaction_controller._game_map.width
        assert 0 <= tile.y < interaction_controller._game_map.height

    def test_clamped_tile_is_within_bounds(self, interaction_controller):
        tile = interaction_controller.screen_to_tile((-500.0, -500.0))
        assert tile.is_within_bounds(
            interaction_controller._game_map.width, interaction_controller._game_map.height
        )


class TestHitTestEdgeCoordinates:
    def test_hit_test_with_extreme_coordinates(self, interaction_controller):
        units = []
        result = interaction_controller.hit_test((-5000.0, -5000.0), units)
        assert result is not None
        assert result.world_position.x >= 0
        assert result.world_position.y >= 0

    def test_hit_test_radius_always_positive(self, camera, event_bus):
        gm = MagicMock()
        gm.width = 10
        gm.height = 10
        ic = InteractionController(camera=camera, game_map=gm, event_bus=event_bus)
        unit = Unit(
            id="u_edge",
            name="Edge",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=100),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(0, 0)),
            vision=VisionComponent(range_tiles=3),
        )
        units = [unit]
        upos = unit.position.pixel_position
        screen_pos = camera.world_to_screen(upos)
        result = ic.hit_test(screen_pos, units)
        assert result.is_unit_click is True
        assert result.hit_unit.id == "u_edge"

    def test_hit_test_at_map_boundary_clamps_result(self, camera, event_bus):
        gm = MagicMock()
        gm.width = 20
        gm.height = 20
        ic = InteractionController(camera=camera, game_map=gm, event_bus=event_bus)
        boundary_pos = Vec2(19 * 32 + 16, 19 * 32 + 16)
        screen_pos = camera.world_to_screen(boundary_pos)
        result = ic.hit_test(screen_pos, [])
        assert result.world_position.x <= gm.width - 1
        assert result.world_position.y <= gm.height - 1


class TestSaveLoadWithDynamicKey:
    def test_save_load_works_with_dynamic_key(self, tmp_save_dir):
        custom_key = b"dynamic-test-hmac-for-integration"
        with patch.dict(os.environ, {"PYCC2_SAVE_HMAC_KEY": custom_key.decode()}):
            mgr = SecureSaveManager(base_dir=tmp_save_dir)
            state = {"tick": 42, "test": "data"}
            assert mgr.save_game(0, state) is True
            loaded, meta, status = mgr.load_game(0)
            assert status == SaveSlotStatus.OK
            assert loaded["tick"] == 42

    def test_different_keys_detect_tampering(self, tmp_save_dir):
        key_a = b"hmac-key-alpha-version"
        key_b = b"hmac-key-beta-version"
        with patch.dict(os.environ, {"PYCC2_SAVE_HMAC_KEY": key_a.decode()}):
            mgr_a = SecureSaveManager(base_dir=tmp_save_dir)
            mgr_a.save_game(0, {"tick": 99})
        with patch.dict(os.environ, {"PYCC2_SAVE_HMAC_KEY": key_b.decode()}):
            mgr_b = SecureSaveManager(base_dir=tmp_save_dir)
            _, _, status = mgr_b.load_game(0)
            assert status == SaveSlotStatus.CORRUPTED

    def test_dynamic_key_save_load_roundtrip(self, tmp_save_dir):
        custom_key = b"roundtrip-hmac-key-testing-12345"
        with patch.dict(os.environ, {"PYCC2_SAVE_HMAC_KEY": custom_key.decode()}):
            mgr = SecureSaveManager(base_dir=tmp_save_dir)
            state = {"tick": 777, "data": "hello", "nested": {"a": 1}}
            assert mgr.save_game(3, state) is True
            loaded, meta, status = mgr.load_game(3)
            assert status == SaveSlotStatus.OK
            assert loaded["tick"] == 777
            assert loaded["data"] == "hello"
