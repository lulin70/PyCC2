"""
CC2 Original Sprite Loader

加载CC2原版精灵PNG文件，提供与现有系统兼容的接口。
确保功能被实际调用，避免幽灵功能。

Version: 1.0
Date: 2026-06-16
"""

from __future__ import annotations

import logging
from pathlib import Path

import pygame

logger = logging.getLogger(__name__)


class CC2SpriteLoader:
    """
    加载CC2原版精灵素材

    当CC2原版精灵素材可用时，优先加载高质量的原版图像。
    如果素材不可用，返回None，系统会回退到程序化生成。

    特性:
    - 自动检测CC2素材是否可用
    - 按需加载和缓存精灵
    - 提供加载统计用于监控和测试
    - 支持多方向和多帧动画
    """

    def __init__(self, assets_root: Path):
        """
        初始化CC2精灵加载器

        参数:
            assets_root: 资源根目录（通常是 PyCC2/assets/）
        """
        self.assets_root = Path(assets_root)
        self.cc2_sprite_path = self.assets_root / "sprites" / "cc2_original"
        self.sprite_cache: dict[str, pygame.Surface] = {}
        self._load_stats = {
            "loaded": 0,  # 从文件加载的次数
            "failed": 0,  # 加载失败的次数
            "cached": 0,  # 从缓存返回的次数
            "initialized": True,  # 初始化标记
        }

        availability = "available" if self.is_available() else "not available"
        logger.info(
            "CC2SpriteLoader initialized - assets path: %s (%s)", self.cc2_sprite_path, availability
        )

    def is_available(self) -> bool:
        """
        检查CC2原版素材是否可用

        返回:
            True 如果 cc2_original 目录存在且不为空
        """
        if not self.cc2_sprite_path.exists():
            return False

        if not self.cc2_sprite_path.is_dir():
            logger.warning(
                "CC2 sprite path exists but is not a directory: %s", self.cc2_sprite_path
            )
            return False

        # 检查是否至少有一个子目录（infantry, vehicles等）
        subdirs = list(self.cc2_sprite_path.iterdir())
        return len(subdirs) > 0

    def load_sprite(
        self, unit_type: str, direction: str, animation: str = "idle", frame: int = 0
    ) -> pygame.Surface | None:
        """
        加载特定精灵

        参数:
            unit_type: 单位类型 (如 "rifle_squad", "sherman_tank")
            direction: 方向 ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
            animation: 动画类型 ("idle", "walk", "shoot", "death")
            frame: 帧号 (从0开始)

        返回:
            pygame.Surface 或 None（如果文件不存在或加载失败）

        示例:
            >>> loader = CC2SpriteLoader(Path("assets"))
            >>> sprite = loader.load_sprite("rifle_squad", "N", "idle", 0)
            >>> if sprite:
            ...     screen.blit(sprite, (x, y))
        """
        # 构建缓存键
        cache_key = f"{unit_type}_{direction}_{animation}_{frame}"

        # 1. 检查缓存
        if cache_key in self.sprite_cache:
            self._load_stats["cached"] += 1
            logger.debug("Cache hit for %s", cache_key)
            return self.sprite_cache[cache_key]

        # 2. 构建文件路径
        sprite_file = self._build_sprite_path(unit_type, direction, animation, frame)

        # 3. 检查文件是否存在
        if not sprite_file.exists():
            self._load_stats["failed"] += 1
            logger.debug("CC2 sprite not found: %s", sprite_file)
            return None

        # 4. 加载PNG文件
        try:
            surface = pygame.image.load(str(sprite_file)).convert_alpha()
            self.sprite_cache[cache_key] = surface
            self._load_stats["loaded"] += 1
            logger.debug(
                "Loaded CC2 sprite: %s (%dx%d)",
                sprite_file.name,
                surface.get_width(),
                surface.get_height(),
            )
            return surface

        except pygame.error as e:
            self._load_stats["failed"] += 1
            logger.error("Failed to load CC2 sprite %s: %s", sprite_file, e)
            return None
        except Exception as e:
            self._load_stats["failed"] += 1
            logger.error(
                "Unexpected error loading CC2 sprite %s: %s", sprite_file, e, exc_info=True
            )
            return None

    def _build_sprite_path(
        self, unit_type: str, direction: str, animation: str, frame: int
    ) -> Path:
        """
        构建精灵文件路径

        路径结构:
        cc2_original/
          ├── infantry/
          │   └── rifle_squad/
          │       └── N_idle_001.png
          └── vehicles/
              └── sherman_tank/
                  └── N_idle_001.png

        参数:
            unit_type: 单位类型
            direction: 方向
            animation: 动画类型
            frame: 帧号

        返回:
            完整的文件路径
        """
        # 判断单位类别
        category = self._get_unit_category(unit_type)

        # 文件命名约定: direction_animation_frame.png
        # 例如: N_walk_001.png
        filename = f"{direction}_{animation}_{frame:03d}.png"

        return self.cc2_sprite_path / category / unit_type / filename

    def _get_unit_category(self, unit_type: str) -> str:
        """
        根据单位类型判断所属类别

        参数:
            unit_type: 单位类型字符串

        返回:
            类别名称 ("infantry", "vehicles", "buildings")
        """
        unit_type_lower = unit_type.lower()

        # 车辆关键词
        vehicle_keywords = [
            "tank",
            "sherman",
            "panzer",
            "tiger",
            "stug",
            "halftrack",
            "sdkfz",
            "jeep",
            "truck",
            "car",
            "armored",
            "artillery",
        ]

        # 建筑关键词
        building_keywords = [
            "house",
            "building",
            "barn",
            "church",
            "bunker",
            "fortification",
            "wall",
            "bridge",
        ]

        # 检查是否为车辆
        for keyword in vehicle_keywords:
            if keyword in unit_type_lower:
                return "vehicles"

        # 检查是否为建筑
        for keyword in building_keywords:
            if keyword in unit_type_lower:
                return "buildings"

        # 默认为步兵
        return "infantry"

    def get_load_stats(self) -> dict[str, int]:
        """
        获取加载统计信息

        用于监控和测试，确保功能被实际调用。

        返回:
            包含加载统计的字典:
            - loaded: 从文件加载的精灵数
            - failed: 加载失败的次数
            - cached: 从缓存返回的次数
            - initialized: 是否已初始化

        示例:
            >>> stats = loader.get_load_stats()
            >>> print(f"Loaded: {stats['loaded']}, Cached: {stats['cached']}")
        """
        return self._load_stats.copy()

    def preload_unit(self, unit_type: str) -> int:
        """
        预加载某个单位的所有精灵

        预加载可以减少游戏运行时的加载延迟。

        参数:
            unit_type: 要预加载的单位类型

        返回:
            成功加载的精灵数量

        示例:
            >>> loaded = loader.preload_unit("rifle_squad")
            >>> print(f"Preloaded {loaded} sprites")
        """
        loaded_count = 0
        directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        animations = ["idle", "walk", "shoot", "death"]
        max_frames = 8  # 假设动画最多8帧

        for direction in directions:
            for animation in animations:
                for frame in range(max_frames):
                    sprite = self.load_sprite(unit_type, direction, animation, frame)
                    if sprite:
                        loaded_count += 1
                    else:
                        # 如果这一帧不存在，跳过该动画的剩余帧
                        break

        logger.info("Preloaded %d sprites for %s", loaded_count, unit_type)
        return loaded_count

    def clear_cache(self) -> int:
        """
        清空精灵缓存

        释放内存，适合在切换场景时调用。

        返回:
            清除的精灵数量
        """
        cache_size = len(self.sprite_cache)
        self.sprite_cache.clear()
        logger.info("Cleared sprite cache: %d sprites removed", cache_size)
        return cache_size

    def get_cache_size_mb(self) -> float:
        """
        获取缓存占用的内存大小（MB）

        返回:
            缓存大小（兆字节）
        """
        total_bytes = 0
        for surface in self.sprite_cache.values():
            # 估算: width * height * 4 bytes (RGBA)
            total_bytes += surface.get_width() * surface.get_height() * 4

        return total_bytes / (1024 * 1024)

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"CC2SpriteLoader("
            f"path={self.cc2_sprite_path}, "
            f"available={self.is_available()}, "
            f"cached={len(self.sprite_cache)} sprites)"
        )
