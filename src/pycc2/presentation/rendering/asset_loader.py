"""Asset Loader - 支持从文件加载CC2原版资源，fallback到程序化生成"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pygame
from pygame import Surface

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AssetLoader:
    """
    资产加载器 - 优先从assets目录加载PNG，不存在时fallback到程序化生成
    
    目录结构:
    assets/
    ├── sprites/
    │   ├── units/
    │   │   ├── allies/
    │   │   │   ├── infantry_d0.png (北)
    │   │   │   ├── infantry_d1.png (东北)
    │   │   │   └── ...
    │   │   └── axis/
    │   ├── vehicles/
    │   └── effects/
    └── terrain/
        ├── grass_01.png
        └── ...
    """

    def __init__(self, assets_dir: Path | None = None):
        if assets_dir is None:
            # 默认路径：PyCC2/assets
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
            assets_dir = project_root / "assets"
        
        self.assets_dir = Path(assets_dir)
        self._sprite_cache: dict[str, Surface] = {}
        self._terrain_cache: dict[str, Surface] = {}
        
        # 确保目录存在
        self._ensure_directories()
    
    def _ensure_directories(self) -> None:
        """创建必要的目录结构"""
        dirs = [
            self.assets_dir / "sprites" / "units" / "allies",
            self.assets_dir / "sprites" / "units" / "axis",
            self.assets_dir / "sprites" / "vehicles",
            self.assets_dir / "sprites" / "effects",
            self.assets_dir / "terrain",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    # 单位类型映射：游戏内部名称 -> 精灵文件名
    UNIT_TYPE_MAP = {
        # Infantry types -> WW2 soldier sprite
        "INFANTRY_SQUAD": "rifleman",
        "RIFLE_SQUAD": "rifleman",
        "MACHINE_GUN_SQUAD": "mg_team",
        "MG_TEAM": "mg_team",
        "COMMANDER": "officer",
        "OFFICER": "officer",
        # Support types
        "AT_GUN_TEAM": "engineer",
        "AT_TEAM": "engineer",
        "MORTAR_TEAM": "engineer",
        "SNIPER_TEAM": "rifleman",
        "MEDIC_TEAM": "engineer",
        "ENGINEER_SQUAD": "engineer",
        "ASSAULT_SQUAD": "rifleman",
        "FLAMETHROWER_TEAM": "engineer",
        "SCOUT_TEAM": "rifleman",
        # Vehicle types
        "TANK": "medium_tank",
        "SHERMAN_TANK": "medium_tank",
        "M4_SHERMAN": "medium_tank",
        "M5_STUART": "light_tank",
        "LIGHT_TANK": "light_tank",
        "HEAVY_TANK": "heavy_tank",
        "HALFTRACK": "halftrack",
        "JEEP": "jeep",
        # Generic fallbacks
        "INFANTRY": "rifleman",
        "SUPPORT": "engineer",
        "RECON": "rifleman",
        "ARMOR": "medium_tank",
        "VEHICLE": "medium_tank",
        "DEFAULT": "rifleman",  # Safe default
    }
    
    def load_unit_sprite(
        self,
        faction: str,
        unit_type: str,
        direction: int,
        size: int = 128,
    ) -> Surface | None:
        """
        加载单位精灵
        
        Args:
            faction: "allies" 或 "axis"
            unit_type: 单位类型名称（如 "INFANTRY_SQUAD"）
            direction: 方向索引 0-7 (N, NE, E, SE, S, SW, W, NW)
            size: 目标尺寸
        
        Returns:
            Surface 或 None（需要fallback到程序化生成）
        """
        cache_key = f"{faction}_{unit_type}_d{direction}_{size}"
        
        # 检查缓存
        if cache_key in self._sprite_cache:
            return self._sprite_cache[cache_key]
        
        # 映射单位类型到精灵文件名
        sprite_name = self.UNIT_TYPE_MAP.get(unit_type, "rifleman")
        
        # 尝试多种路径格式
        possible_paths = [
            # 格式1: 带方向的精灵 (infantry_squad_d0.png)
            self.assets_dir / "sprites" / "units" / faction / f"{unit_type.lower()}_d{direction}.png",
            # 格式2: 简单命名 (rifleman.png) - 我们生成的格式
            self.assets_dir / "sprites" / "units" / faction / f"{sprite_name}.png",
            # 格式3: 映射名称带方向
            self.assets_dir / "sprites" / "units" / faction / f"{sprite_name}_d{direction}.png",
        ]
        
        for sprite_path in possible_paths:
            if sprite_path.exists():
                try:
                    # 加载图像 - 不使用convert_alpha()以避免需要display初始化
                    surface = pygame.image.load(str(sprite_path))
                    print(f"[AssetLoader] ✅ 找到PNG: {sprite_path.name}")
                    
                    # 缩放到目标尺寸
                    if surface.get_width() != size or surface.get_height() != size:
                        surface = pygame.transform.scale(surface, (size, size))
                    
                    # 注意：我们的PNG已经是朝北的，所有方向使用同一个PNG
                    # 旋转由SpriteRenderer在渲染时处理
                    
                    self._sprite_cache[cache_key] = surface
                    print(f"[AssetLoader] ✅ 缓存PNG: {cache_key}")
                    return surface
                except Exception as e:
                    print(f"[AssetLoader] ❌ 加载失败 {sprite_path}: {e}")
                    continue
        
        # 所有路径都不存在，返回None让调用者使用程序化生成
        print(f"[AssetLoader] ⚠️  未找到PNG: {faction}/{unit_type}/d{direction}")
        return None

    def load_cc2_sprite(
        self,
        unit_type: str,
        direction: int = 0,
        faction: str = 'allies',
    ) -> pygame.Surface | None:
        """
        加载单位精灵 - 优先使用CC2写实像素艺术生成器

        Args:
            unit_type: 单位类型名称（如 "INFANTRY_SQUAD"）
            direction: 方向索引 0-7 (N, NE, E, SE, S, SW, W, NW)
            faction: "allies" 或 "axis"

        Returns:
            pygame.Surface 或 None
        """
        cache_key = f"cc2_{faction}_{unit_type}_d{direction}"

        if cache_key in self._sprite_cache:
            return self._sprite_cache[cache_key]

        try:
            from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D, Direction, Faction

            dir_enum = list(Direction)[direction] if direction < 8 else Direction.SOUTH
            fac_enum = Faction(faction)

            sprite = PixelArtist3D.create_infantry_sprite(
                direction=dir_enum,
                faction=fac_enum,
                state='idle',
                frame=0
            )

            self._sprite_cache[cache_key] = sprite
            print(f"[AssetLoader] ✅ Generated CC2 sprite: {cache_key}")
            return sprite

        except Exception as e:
            print(f"[AssetLoader] ❌ CC2 sprite generation failed: {e}, using fallback")
            return self.load_fallback_sprite(unit_type)

    def load_fallback_sprite(self, unit_type: str) -> pygame.Surface | None:
        """Fallback精灵生成器（当CC2生成失败时使用）"""
        import pygame

        surface = pygame.Surface((24, 24), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        color = (74, 144, 217) if 'allies' in unit_type.lower() else (217, 74, 74)
        pygame.draw.circle(surface, color, (12, 12), 8)
        pygame.draw.circle(surface, (255, 255, 255), (12, 12), 8, 1)

        print(f"[AssetLoader] ⚠️  Using fallback circle sprite for: {unit_type}")
        return surface
    
    def load_terrain_tile(self, tile_id: int, size: int = 32) -> Surface | None:
        """
        加载地形tile
        
        Args:
            tile_id: 地形ID (0-13)
            size: tile尺寸
        
        Returns:
            Surface 或 None
        """
        cache_key = f"terrain_{tile_id}_{size}"
        
        if cache_key in self._terrain_cache:
            return self._terrain_cache[cache_key]
        
        # 地形tile命名: terrain_00.png, terrain_01.png, ...
        tile_path = self.assets_dir / "terrain" / f"terrain_{tile_id:02d}.png"
        
        if tile_path.exists():
            try:
                surface = pygame.image.load(str(tile_path)).convert_alpha()
                if surface.get_width() != size or surface.get_height() != size:
                    surface = pygame.transform.scale(surface, (size, size))
                self._terrain_cache[cache_key] = surface
                return surface
            except Exception as e:
                print(f"[AssetLoader] 加载地形失败 {tile_path}: {e}")
        
        return None
    
    def load_effect_sprite(self, effect_name: str, frame: int = 0) -> Surface | None:
        """
        加载特效精灵（爆炸、烟雾等）
        
        Args:
            effect_name: 特效名称（如 "explosion", "smoke"）
            frame: 动画帧索引
        
        Returns:
            Surface 或 None
        """
        cache_key = f"effect_{effect_name}_f{frame}"
        
        if cache_key in self._sprite_cache:
            return self._sprite_cache[cache_key]
        
        effect_path = self.assets_dir / "sprites" / "effects" / f"{effect_name}_f{frame:02d}.png"
        
        if effect_path.exists():
            try:
                surface = pygame.image.load(str(effect_path)).convert_alpha()
                self._sprite_cache[cache_key] = surface
                return surface
            except Exception as e:
                logging.debug(f"Effect sprite load failed: {e}")
        
        return None
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self._sprite_cache.clear()
        self._terrain_cache.clear()
    
    def get_cache_stats(self) -> dict[str, int]:
        """获取缓存统计"""
        return {
            "sprites": len(self._sprite_cache),
            "terrain": len(self._terrain_cache),
            "total": len(self._sprite_cache) + len(self._terrain_cache),
        }
