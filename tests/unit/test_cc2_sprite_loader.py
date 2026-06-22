"""
Tests for CC2SpriteLoader

测试CC2精灵加载器，确保功能被实际调用，避免幽灵功能。

Version: 1.0
Date: 2026-06-16
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pygame
import pytest

from pycc2.presentation.rendering.cc2_sprite_loader import CC2SpriteLoader


class TestCC2SpriteLoaderInitialization:
    """测试加载器初始化"""

    def test_loader_initialization(self, tmp_path):
        """测试加载器正确初始化"""
        loader = CC2SpriteLoader(tmp_path)

        assert loader.assets_root == tmp_path
        assert loader.cc2_sprite_path == tmp_path / "sprites" / "cc2_original"
        assert isinstance(loader.sprite_cache, dict)
        assert len(loader.sprite_cache) == 0

        # 验证统计已初始化
        stats = loader.get_load_stats()
        assert stats["initialized"] is True
        assert stats["loaded"] == 0
        assert stats["failed"] == 0
        assert stats["cached"] == 0

    def test_initialization_logging(self, tmp_path, caplog):
        """测试初始化时的日志输出 - 确保功能被调用"""
        with caplog.at_level("INFO"):
            CC2SpriteLoader(tmp_path)

        # 验证日志包含初始化信息
        assert any("CC2SpriteLoader initialized" in record.message
                  for record in caplog.records)
        assert any("not available" in record.message
                  for record in caplog.records)


class TestCC2SpriteLoaderAvailability:
    """测试素材可用性检查"""

    def test_availability_when_not_exists(self, tmp_path):
        """测试目录不存在时不可用"""
        loader = CC2SpriteLoader(tmp_path)
        assert not loader.is_available()

    def test_availability_when_empty_directory(self, tmp_path):
        """测试空目录时不可用"""
        cc2_path = tmp_path / "sprites" / "cc2_original"
        cc2_path.mkdir(parents=True)

        loader = CC2SpriteLoader(tmp_path)
        assert not loader.is_available()

    def test_availability_when_has_content(self, tmp_path):
        """测试有内容时可用"""
        # 创建假的CC2素材目录结构
        cc2_path = tmp_path / "sprites" / "cc2_original"
        infantry_path = cc2_path / "infantry"
        infantry_path.mkdir(parents=True)

        loader = CC2SpriteLoader(tmp_path)
        assert loader.is_available()

    def test_availability_when_is_file_not_directory(self, tmp_path, caplog):
        """测试路径是文件而非目录时的处理"""
        cc2_path = tmp_path / "sprites" / "cc2_original"
        cc2_path.parent.mkdir(parents=True)
        cc2_path.write_text("not a directory")

        with caplog.at_level("WARNING"):
            loader = CC2SpriteLoader(tmp_path)
            result = loader.is_available()

        assert not result
        assert any("not a directory" in record.message
                  for record in caplog.records)


class TestCC2SpriteLoaderPathBuilding:
    """测试路径构建逻辑"""

    def test_build_infantry_sprite_path(self, tmp_path):
        """测试步兵精灵路径构建"""
        loader = CC2SpriteLoader(tmp_path)

        path = loader._build_sprite_path("rifle_squad", "N", "walk", 1)

        assert "infantry" in str(path)
        assert "rifle_squad" in str(path)
        assert "N_walk_001.png" in str(path)

    def test_build_vehicle_sprite_path(self, tmp_path):
        """测试车辆精灵路径构建"""
        loader = CC2SpriteLoader(tmp_path)

        path = loader._build_sprite_path("sherman_tank", "E", "idle", 0)

        assert "vehicles" in str(path)
        assert "sherman_tank" in str(path)
        assert "E_idle_000.png" in str(path)

    def test_build_building_sprite_path(self, tmp_path):
        """测试建筑精灵路径构建"""
        loader = CC2SpriteLoader(tmp_path)

        path = loader._build_sprite_path("house", "S", "idle", 0)

        assert "buildings" in str(path)
        assert "house" in str(path)
        assert "S_idle_000.png" in str(path)

    @pytest.mark.parametrize("unit_type,expected_category", [
        ("rifle_squad", "infantry"),
        ("sherman_tank", "vehicles"),
        ("panzer_iv", "vehicles"),
        ("halftrack", "vehicles"),
        ("church", "buildings"),
        ("bunker", "buildings"),
        ("unknown_unit", "infantry"),  # 默认分类
    ])
    def test_unit_category_detection(self, tmp_path, unit_type, expected_category):
        """测试单位类别自动检测"""
        loader = CC2SpriteLoader(tmp_path)
        category = loader._get_unit_category(unit_type)
        assert category == expected_category


class TestCC2SpriteLoaderLoading:
    """测试精灵加载功能"""

    def test_load_nonexistent_sprite(self, tmp_path):
        """测试加载不存在的精灵"""
        loader = CC2SpriteLoader(tmp_path)

        result = loader.load_sprite("test_unit", "N", "idle", 0)

        assert result is None
        stats = loader.get_load_stats()
        assert stats["failed"] == 1
        assert stats["loaded"] == 0

    def test_load_stats_tracking(self, tmp_path):
        """测试加载统计跟踪 - 验证功能被调用"""
        loader = CC2SpriteLoader(tmp_path)

        # 尝试加载3次不存在的精灵
        loader.load_sprite("unit1", "N", "idle", 0)
        loader.load_sprite("unit2", "E", "walk", 1)
        loader.load_sprite("unit3", "S", "shoot", 2)

        stats = loader.get_load_stats()
        assert stats["failed"] == 3
        assert stats["loaded"] == 0
        assert stats["cached"] == 0

    @patch('pygame.image.load')
    def test_load_sprite_success(self, mock_load, tmp_path):
        """测试成功加载精灵"""
        # 设置mock - 需要mock convert_alpha()的返回值
        mock_surface = MagicMock()
        mock_surface.get_width.return_value = 32
        mock_surface.get_height.return_value = 32
        mock_surface.convert_alpha.return_value = mock_surface
        mock_load.return_value = mock_surface

        # 创建目录结构和文件
        sprite_path = tmp_path / "sprites" / "cc2_original" / "infantry" / "test_unit"
        sprite_path.mkdir(parents=True)
        sprite_file = sprite_path / "N_idle_000.png"
        sprite_file.write_bytes(b"fake png data")

        loader = CC2SpriteLoader(tmp_path)
        result = loader.load_sprite("test_unit", "N", "idle", 0)

        assert result is not None
        assert result == mock_surface

        # 验证统计
        stats = loader.get_load_stats()
        assert stats["loaded"] == 1
        assert stats["failed"] == 0

    @patch('pygame.image.load')
    def test_sprite_caching(self, mock_load, tmp_path):
        """测试精灵缓存功能 - 确保第二次调用使用缓存"""
        # 设置mock
        mock_surface = MagicMock()
        mock_load.return_value = mock_surface

        # 创建文件
        sprite_path = tmp_path / "sprites" / "cc2_original" / "infantry" / "test_unit"
        sprite_path.mkdir(parents=True)
        sprite_file = sprite_path / "N_idle_000.png"
        sprite_file.write_bytes(b"fake png data")

        loader = CC2SpriteLoader(tmp_path)

        # 第一次加载
        result1 = loader.load_sprite("test_unit", "N", "idle", 0)
        stats1 = loader.get_load_stats()

        # 第二次加载（应该使用缓存）
        result2 = loader.load_sprite("test_unit", "N", "idle", 0)
        stats2 = loader.get_load_stats()

        # 验证返回同一对象
        assert result1 is result2

        # 验证统计：loaded不增加，但cached增加
        assert stats2["loaded"] == stats1["loaded"]
        assert stats2["cached"] == stats1["cached"] + 1

        # 验证mock只被调用一次
        assert mock_load.call_count == 1

    @patch('pygame.image.load')
    def test_load_sprite_with_pygame_error(self, mock_load, tmp_path, caplog):
        """测试加载失败时的错误处理"""
        # 设置mock抛出异常
        mock_load.side_effect = pygame.error("Failed to load image")

        # 创建文件
        sprite_path = tmp_path / "sprites" / "cc2_original" / "infantry" / "test_unit"
        sprite_path.mkdir(parents=True)
        sprite_file = sprite_path / "N_idle_000.png"
        sprite_file.write_bytes(b"invalid data")

        with caplog.at_level("ERROR"):
            loader = CC2SpriteLoader(tmp_path)
            result = loader.load_sprite("test_unit", "N", "idle", 0)

        assert result is None
        assert any("Failed to load CC2 sprite" in record.message
                  for record in caplog.records)

        stats = loader.get_load_stats()
        assert stats["failed"] == 1


class TestCC2SpriteLoaderPreloading:
    """测试预加载功能"""

    @patch('pygame.image.load')
    def test_preload_unit(self, mock_load, tmp_path):
        """测试单位预加载"""
        # 设置mock
        mock_surface = MagicMock()
        mock_load.return_value = mock_surface

        # 创建一些精灵文件
        sprite_path = tmp_path / "sprites" / "cc2_original" / "infantry" / "rifle_squad"
        sprite_path.mkdir(parents=True)

        # 创建3个方向 x 2个动画 x 1帧 = 6个文件
        for direction in ["N", "E", "S"]:
            for animation in ["idle", "walk"]:
                sprite_file = sprite_path / f"{direction}_{animation}_000.png"
                sprite_file.write_bytes(b"fake png data")

        loader = CC2SpriteLoader(tmp_path)
        loaded_count = loader.preload_unit("rifle_squad")

        # 验证加载了6个精灵
        assert loaded_count == 6

        stats = loader.get_load_stats()
        assert stats["loaded"] == 6

    def test_preload_nonexistent_unit(self, tmp_path, caplog):
        """测试预加载不存在的单位"""
        with caplog.at_level("INFO"):
            loader = CC2SpriteLoader(tmp_path)
            loaded_count = loader.preload_unit("nonexistent_unit")

        assert loaded_count == 0
        assert any("Preloaded 0 sprites" in record.message
                  for record in caplog.records)


class TestCC2SpriteLoaderCacheManagement:
    """测试缓存管理功能"""

    def test_clear_cache(self, tmp_path):
        """测试清空缓存"""
        loader = CC2SpriteLoader(tmp_path)

        # 手动添加一些缓存项
        mock_surface = MagicMock()
        loader.sprite_cache["test1"] = mock_surface
        loader.sprite_cache["test2"] = mock_surface
        loader.sprite_cache["test3"] = mock_surface

        assert len(loader.sprite_cache) == 3

        cleared = loader.clear_cache()

        assert cleared == 3
        assert len(loader.sprite_cache) == 0

    def test_get_cache_size(self, tmp_path):
        """测试获取缓存大小"""
        loader = CC2SpriteLoader(tmp_path)

        # 创建mock surface (32x32 RGBA = 4096 bytes)
        mock_surface = MagicMock()
        mock_surface.get_width.return_value = 32
        mock_surface.get_height.return_value = 32

        loader.sprite_cache["test"] = mock_surface

        size_mb = loader.get_cache_size_mb()

        # 32 * 32 * 4 = 4096 bytes = 0.00390625 MB
        assert size_mb == pytest.approx(0.00390625, rel=1e-3)


class TestCC2SpriteLoaderIntegration:
    """集成测试 - 验证与实际游戏循环的集成"""

    @pytest.mark.skipif(
        not Path("assets/sprites/cc2_original").exists(),
        reason="CC2 original sprites not available"
    )
    def test_load_real_cc2_sprite_if_available(self):
        """如果CC2原版精灵可用，测试加载真实精灵"""
        loader = CC2SpriteLoader(Path("assets"))

        if not loader.is_available():
            pytest.skip("CC2 sprites not available in assets/")

        # 尝试加载常见单位
        sprite = loader.load_sprite("rifle_squad", "N", "idle", 0)

        if sprite:
            assert sprite.get_width() > 0
            assert sprite.get_height() > 0

            stats = loader.get_load_stats()
            assert stats["loaded"] >= 1

    def test_repr_string(self, tmp_path):
        """测试字符串表示"""
        loader = CC2SpriteLoader(tmp_path)
        repr_str = repr(loader)

        assert "CC2SpriteLoader" in repr_str
        assert str(tmp_path) in repr_str
        assert "available=False" in repr_str
        assert "cached=0" in repr_str


class TestCC2SpriteLoaderCallVerification:
    """验证功能被实际调用 - 防止幽灵功能"""

    def test_initialization_is_called(self, tmp_path, caplog):
        """验证__init__被调用"""
        with caplog.at_level("INFO"):
            loader = CC2SpriteLoader(tmp_path)

        # 通过日志验证初始化被执行
        assert any("CC2SpriteLoader initialized" in record.message
                  for record in caplog.records)

        # 通过统计验证初始化被执行
        stats = loader.get_load_stats()
        assert stats["initialized"] is True

    def test_load_sprite_increments_stats(self, tmp_path):
        """验证load_sprite调用会更新统计"""
        loader = CC2SpriteLoader(tmp_path)
        initial_stats = loader.get_load_stats()

        # 调用load_sprite
        loader.load_sprite("test", "N", "idle", 0)

        # 验证统计发生变化（说明函数被执行）
        new_stats = loader.get_load_stats()
        assert new_stats["failed"] > initial_stats["failed"]

    def test_preload_calls_load_sprite_multiple_times(self, tmp_path):
        """验证preload会多次调用load_sprite"""
        loader = CC2SpriteLoader(tmp_path)

        # preload会尝试加载多个精灵
        loader.preload_unit("test_unit")

        stats = loader.get_load_stats()
        # 应该尝试了多次加载（8方向 x 4动画 x 最多8帧）
        assert stats["failed"] > 0  # 都失败了，但确实被调用了


# 性能测试
class TestCC2SpriteLoaderPerformance:
    """性能测试 - 确保不影响游戏帧率"""

    @patch('pygame.image.load')
    def test_cache_performance(self, mock_load, tmp_path):
        """测试缓存性能（简化版，不依赖benchmark插件）"""
        mock_surface = MagicMock()
        mock_surface.convert_alpha.return_value = mock_surface
        mock_load.return_value = mock_surface

        # 创建文件
        sprite_path = tmp_path / "sprites" / "cc2_original" / "infantry" / "test"
        sprite_path.mkdir(parents=True)
        (sprite_path / "N_idle_000.png").write_bytes(b"data")

        loader = CC2SpriteLoader(tmp_path)

        # 第一次加载（会缓存）
        loader.load_sprite("test", "N", "idle", 0)

        # 多次从缓存加载
        import time
        start = time.time()
        for _ in range(1000):
            result = loader.load_sprite("test", "N", "idle", 0)
            assert result is not None
        elapsed = time.time() - start

        # 1000次缓存查找应该在0.1秒内完成
        assert elapsed < 0.1, f"Cache too slow: {elapsed}s for 1000 lookups"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
