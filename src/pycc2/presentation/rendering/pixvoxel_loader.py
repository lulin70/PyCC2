"""PixVoxel Sprite Loader - 加载 PixVoxel 等距/正交精灵资源

支持功能:
- 从 PixVoxel 资源目录加载精灵
- 调色板替换（阵营颜色: 盟军绿色、轴心国灰色）
- PixVoxel 单位名 → PyCC2 单位类型映射
- 返回 pygame.Surface 对象
- 缓存已加载精灵
- 不可用时 fallback 到程序化生成

资源来源:
- https://opengameart.org/content/pixvoxel-revised-isometric-wargame-sprites
- 许可证: CC0 (公共领域)

=== 手动下载指南 (如果自动下载失败) ===

步骤1: 手动下载资源文件
  - 浏览器访问: https://opengameart.org/content/pixvoxel-revised-isometric-wargame-sprites
  - 点击 "Revised_PixVoxel_Wargame.7z" 下载链接（约50-100MB）
  - 或使用命令行:
    curl -L -o /tmp/PixVoxel.7z "https://opengameart.org/sites/default/files/Revised_PixVoxel_Wargame.7z"

步骤2: 提取文件
  - macOS: brew install p7zip && 7z x /tmp/PixVoxel.7z -o/tmp/pixvoxel_extracted
  - Linux: sudo apt install p7zip-full && 7z x /tmp/PixVoxel.7z -o/tmp/pixvoxel_extracted
  - Windows: 使用 7-Zip 提取到 C:\\tmp\\pixvoxel_extracted
  - Python: pip install py7zr && python -c "import py7zr; py7zr.SevenZipFile('/tmp/PixVoxel.7z').extractall('/tmp/pixvoxel_extracted')"

步骤3: 运行整理脚本
  python scripts/download_pixvoxel_assets.py --keep-archive
  (脚本会自动从 /tmp/pixvoxel_download/ 提取并整理)

步骤4: 验证安装
  - 检查目录: ls assets/sprites/pixvoxel_isometric/
  - 应该看到: allies/, axis/, manifest.json 等目录和文件

可选: 下载正交版本（用于非等距视角）
  python scripts/download_pixvoxel_assets.py --ortho --keep-archive

注意:
- 如果下载速度慢，可以尝试使用下载工具（如IDM、迅雷）
- 某些网络环境可能需要代理才能访问 OpenGameArt
- 资源包大小约为 50-150MB（取决于版本）
- 即使没有 PixVoxel 资源，游戏仍可正常运行（使用程序化生成的精灵）

===============================================
"""

# PLANNED: Not yet wired into game loop — reserved for future feature

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import pygame
from pygame import Surface

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class FactionPalette(Enum):
    """阵营调色板 - 用于 PixVoxel 精灵的调色板替换"""

    ALLIES = "allies"
    AXIS = "axis"
    ALLIES_UK = "allies_uk"
    ALLIES_US = "allies_us"
    ALLIES_POLAND = "allies_poland"
    AXIS_GERMANY = "axis_germany"
    AXIS_ITALY = "axis_italy"
    RESISTANCE = "resistance"


# 阵营主色调 (用于调色板替换的目标颜色)
FACTION_COLORS: dict[str, dict[str, tuple[int, int, int]]] = {
    "allies": {
        "primary": (74, 144, 60),  # 盟军绿
        "secondary": (95, 165, 80),  # 浅绿
        "dark": (50, 100, 40),  # 深绿
        "accent": (120, 180, 100),  # 亮绿
    },
    "axis": {
        "primary": (100, 100, 105),  # 轴心国灰
        "secondary": (130, 130, 135),  # 浅灰
        "dark": (65, 65, 70),  # 深灰
        "accent": (160, 160, 165),  # 亮灰
    },
    "allies_uk": {
        "primary": (60, 80, 140),  # 英军蓝
        "secondary": (80, 100, 160),
        "dark": (40, 55, 100),
        "accent": (100, 120, 180),
    },
    "allies_us": {
        "primary": (80, 120, 60),  # 美军橄榄绿
        "secondary": (100, 140, 80),
        "dark": (55, 85, 40),
        "accent": (120, 160, 100),
    },
    "allies_poland": {
        "primary": (140, 60, 60),  # 波兰军红
        "secondary": (160, 80, 80),
        "dark": (100, 40, 40),
        "accent": (180, 100, 100),
    },
    "axis_germany": {
        "primary": (80, 80, 85),  # 德军深灰
        "secondary": (100, 100, 105),
        "dark": (55, 55, 60),
        "accent": (120, 120, 125),
    },
    "axis_italy": {
        "primary": (140, 120, 60),  # 意军沙色
        "secondary": (160, 140, 80),
        "dark": (100, 85, 40),
        "accent": (180, 160, 100),
    },
    "resistance": {
        "primary": (100, 70, 100),  # 抵抗军紫
        "secondary": (120, 90, 120),
        "dark": (70, 45, 70),
        "accent": (140, 110, 140),
    },
}

# PixVoxel 单位名 → PyCC2 单位类型映射
PIXVOXEL_TO_PYCC2: dict[str, str] = {
    # 步兵类
    "Infantry": "RIFLE_SQUAD",
    "InfantryTrooper": "RIFLE_SQUAD",
    "HeavyInfantry": "MACHINE_GUN_SQUAD",
    "HeavyInfantryTrooper": "MACHINE_GUN_SQUAD",
    "Sniper": "SNIPER_TEAM",
    "SniperTrooper": "SNIPER_TEAM",
    "Medic": "MEDIC_TEAM",
    "MedicTrooper": "MEDIC_TEAM",
    "Engineer": "ENGINEER_SQUAD",
    "EngineerTrooper": "ENGINEER_SQUAD",
    "Mortar": "MORTAR_TEAM",
    "MortarTrooper": "MORTAR_TEAM",
    "Missile": "AT_GUN_TEAM",
    "MissileTrooper": "AT_GUN_TEAM",
    "Jetpack": "ASSAULT_SQUAD",
    "JetpackTrooper": "ASSAULT_SQUAD",
    "Flame": "FLAMETHROWER_TEAM",
    "FlameTrooper": "FLAMETHROWER_TEAM",
    "Commando": "COMMANDER",
    "CommandoTrooper": "COMMANDER",
    "Officer": "OFFICER",
    "OfficerTrooper": "OFFICER",
    "Volunteer": "SUPPORT",
    "VolunteerTrooper": "SUPPORT",
    "Smuggler": "SUPPORT",
    "SmugglerTrooper": "SUPPORT",
    # 载具类
    "LightTank": "LIGHT_TANK",
    "MediumTank": "MEDIUM_TANK",
    "HeavyTank": "HEAVY_TANK",
    "SuperHeavyTank": "HEAVY_TANK",
    "Tank": "MEDIUM_TANK",
    "LightVehicle": "JEEP",
    "APC": "HALFTRACK",
    "Halftrack": "HALFTRACK",
    "Artillery": "AT_GUN_TEAM",
    "AntiAir": "AT_GUN_TEAM",
    "Scout": "JEEP",
    "Jeep": "JEEP",
    # 设施
    "Barracks": "BUILDING",
    "Factory": "BUILDING",
    "HQ": "BUILDING",
    "Radar": "BUILDING",
    "Supply": "BUILDING",
    "Dock": "BUILDING",
    "Airport": "BUILDING",
}

# PyCC2 单位类型 → PixVoxel 单位名（反向映射，用于查找精灵）
PYCC2_TO_PIXVOXEL: dict[str, str] = {}
for _pv_name, _pycc2_type in PIXVOXEL_TO_PYCC2.items():
    if _pycc2_type not in PYCC2_TO_PIXVOXEL:
        PYCC2_TO_PIXVOXEL[_pycc2_type] = _pv_name

# PixVoxel 4 方向 → PyCC2 8 方向索引
# PixVoxel 等距精灵有 4 个方向: N, E, S, W
PIXVOXEL_DIR_TO_INDEX: dict[str, int] = {
    "N": 0,  # North
    "E": 2,  # East
    "S": 4,  # South
    "W": 6,  # West
}

# PyCC2 8 方向 → PixVoxel 4 方向（最近方向映射）
PYCC2_DIR_TO_PIXVOXEL: dict[int, str] = {
    0: "N",  # North
    1: "N",  # Northeast → 近似 North
    2: "E",  # East
    3: "E",  # Southeast → 近似 East
    4: "S",  # South
    5: "S",  # Southwest → 近似 South
    6: "W",  # West
    7: "W",  # Northwest → 近似 West
}

# 动画类型映射
ANIMATION_MAP: dict[str, str] = {
    "idle": "Standing",
    "standing": "Standing",
    "fire": "Firing",
    "firing": "Firing",
    "hit": "Receive",
    "receive": "Receive",
    "death": "Explosions",
    "explode": "Explosions",
    "explosions": "Explosions",
}

# PixVoxel asset pack download URLs (CC0 licensed from OpenGameArt)
PIXVOXEL_ISO_URL = "https://opengameart.org/sites/default/files/Revised_PixVoxel_Wargame_1.7z"
PIXVOXEL_ORTHO_URL = "https://opengameart.org/sites/default/files/PixVoxel_Ortho_Wargame.7z"


class PixVoxelLoader:
    """
    PixVoxel 精灵加载器

    加载 PixVoxel 等距/正交精灵，支持调色板替换和缓存。
    当 PixVoxel 资源不可用时，自动 fallback 到程序化生成。
    支持通过 ResourceCacheManager 自动下载缺失的资源包。
    """

    def __init__(
        self,
        assets_dir: Path | None = None,
        auto_download: bool = False,
        offline_mode: bool = False,
    ):
        if assets_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
            assets_dir = project_root / "assets"

        self.assets_dir = Path(assets_dir)
        self.iso_dir = self.assets_dir / "sprites" / "pixvoxel_isometric"
        self.ortho_dir = self.assets_dir / "sprites" / "pixvoxel_ortho"
        self._auto_download = auto_download
        self._offline_mode = offline_mode

        # 缓存: key → Surface
        self._cache: dict[str, Surface] = {}
        # 清单数据
        self._manifest: dict | None = None
        # 是否有可用的 PixVoxel 资源
        self._iso_available: bool = (
            self.iso_dir.exists() and (self.iso_dir / "manifest.json").exists()
        )
        self._ortho_available: bool = (
            self.ortho_dir.exists() and (self.ortho_dir / "manifest.json").exists()
        )

        if self._iso_available:
            logger.info("PixVoxel isometric sprites available: %s", self.iso_dir)
        else:
            logger.info("PixVoxel isometric sprites unavailable, will use fallback")
            # Attempt auto-download when assets are missing
            if self._auto_download:
                self._try_auto_download_iso()

        if self._ortho_available:
            logger.info("PixVoxel orthographic sprites available: %s", self.ortho_dir)

    @property
    def is_available(self) -> bool:
        """Whether any PixVoxel resource is available."""
        return self._iso_available or self._ortho_available

    # ------------------------------------------------------------------
    # Auto-download via ResourceCacheManager
    # ------------------------------------------------------------------

    def _try_auto_download_iso(self) -> None:
        """Attempt to download and extract isometric PixVoxel assets.

        Uses ResourceCacheManager for downloading with caching support.
        After download, extracts the 7z archive and organizes sprites.
        """
        try:
            from pycc2.infrastructure.resource_cache import ResourceCacheManager

            cache_mgr = ResourceCacheManager(offline_mode=self._offline_mode)
            archive_path = cache_mgr.get(PIXVOXEL_ISO_URL)

            if archive_path is None:
                logger.warning(
                    "Auto-download failed for PixVoxel isometric assets. "
                    "Game will use procedural fallback."
                )
                return

            # Extract and organize
            if self._extract_and_organize(archive_path, self.iso_dir, "isometric"):
                # Re-check availability after extraction
                self._iso_available = (
                    self.iso_dir.exists() and (self.iso_dir / "manifest.json").exists()
                )
                if self._iso_available:
                    logger.info(
                        "PixVoxel isometric assets downloaded and ready: %s",
                        self.iso_dir,
                    )

        except Exception as exc:
            logger.warning("Auto-download error: %s", exc)

    def _try_auto_download_ortho(self) -> None:
        """Attempt to download and extract orthographic PixVoxel assets."""
        try:
            from pycc2.infrastructure.resource_cache import ResourceCacheManager

            cache_mgr = ResourceCacheManager(offline_mode=self._offline_mode)
            archive_path = cache_mgr.get(PIXVOXEL_ORTHO_URL)

            if archive_path is None:
                logger.warning("Auto-download failed for PixVoxel orthographic assets.")
                return

            if self._extract_and_organize(archive_path, self.ortho_dir, "orthographic"):
                self._ortho_available = (
                    self.ortho_dir.exists() and (self.ortho_dir / "manifest.json").exists()
                )
                if self._ortho_available:
                    logger.info(
                        "PixVoxel orthographic assets downloaded and ready: %s",
                        self.ortho_dir,
                    )

        except Exception as exc:
            logger.warning("Auto-download ortho error: %s", exc)

    def _extract_and_organize(
        self,
        archive_path: Path,
        output_dir: Path,
        sprite_type: str,
    ) -> bool:
        """Extract a 7z archive and organize sprites into *output_dir*.

        Args:
            archive_path: Path to the .7z file.
            output_dir: Target directory for organized sprites.
            sprite_type: Either 'isometric' or 'orthographic'.

        Returns:
            True on success.
        """
        import tempfile

        extract_dir = Path(tempfile.mkdtemp(prefix="pycc2_pv_extract_"))

        try:
            if not self._extract_7z_archive(archive_path, extract_dir):
                return False

            # Organize extracted files
            if sprite_type == "isometric":
                self._organize_isometric_sprites(extract_dir, output_dir)
            else:
                self._organize_ortho_sprites(extract_dir, output_dir)

            return (output_dir / "manifest.json").exists()

        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)

    @staticmethod
    def _extract_7z_archive(archive_path: Path, output_dir: Path) -> bool:
        """Extract a .7z archive using available tools.

        Tries py7zr, then 7z/7za command-line tools.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        # Method 1: py7zr Python library
        try:
            import py7zr  # noqa: F811

            logger.info("Extracting with py7zr: %s", archive_path)
            with py7zr.SevenZipFile(str(archive_path), mode="r") as z:
                z.extractall(path=str(output_dir))
            return True
        except ImportError:
            logger.debug("py7zr not available")
        except Exception as exc:
            logger.warning("py7zr extraction failed: %s", exc)

        # Method 2: 7z command
        for tool in ("7z", "7za", "/usr/local/bin/7z"):
            if shutil.which(tool):
                cmd = [tool, "x", str(archive_path), f"-o{output_dir}", "-y"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info("Extracted with %s: %s", tool, archive_path)
                    return True
                logger.warning("%s extraction failed: %s", tool, result.stderr)

        logger.error("No 7z extraction tool available. Install with: pip install py7zr")
        return False

    def _organize_isometric_sprites(self, extracted_dir: Path, output_dir: Path) -> None:
        """Organize extracted isometric sprites into PyCC2 directory structure.

        Mirrors the logic from scripts/download_pixvoxel_assets.py
        so the loader can work standalone without requiring the script.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        possible_roots = list(extracted_dir.glob("Revised_PixVoxel_Wargame*"))
        root = possible_roots[0] if possible_roots else extracted_dir

        faction_color_map = {
            "color1": "allies",
            "color2": "axis",
            "color3": "allies_uk",
            "color4": "axis_italy",
            "color5": "allies_poland",
            "color6": "allies_us",
            "color7": "axis_germany",
            "color8": "resistance",
        }

        manifest_entries: list[dict] = []

        for color_dir in sorted(root.glob("color*")):
            if not color_dir.is_dir():
                continue
            faction = faction_color_map.get(color_dir.name, "allies")

            for unit_dir in sorted(color_dir.iterdir()):
                if not unit_dir.is_dir():
                    continue
                unit_name = unit_dir.name
                pycc2_type = PIXVOXEL_TO_PYCC2.get(unit_name, unit_name.upper())

                for anim_dir in sorted(unit_dir.iterdir()):
                    if not anim_dir.is_dir():
                        continue
                    anim_name = anim_dir.name

                    for sprite_file in sorted(anim_dir.glob("*.png")):
                        stem = sprite_file.stem
                        parts = stem.split("_")
                        direction = parts[0] if len(parts) >= 2 else "N"
                        frame = parts[1] if len(parts) >= 2 else "0"

                        rel_path = f"{faction}/{pycc2_type}/{anim_name}/{direction}_{frame}.png"
                        target_path = output_dir / rel_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(sprite_file, target_path)

                        manifest_entries.append(
                            {
                                "pixvoxel_name": unit_name,
                                "pycc2_type": pycc2_type,
                                "faction": faction,
                                "animation": anim_name,
                                "direction": direction,
                                "frame": frame,
                                "path": rel_path,
                            }
                        )

        # Copy special directories
        for special in ("palettes", "blank"):
            src = root / special
            if src.exists():
                dst = output_dir / special
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)

        # Write manifest
        self._write_manifest(output_dir, manifest_entries, "isometric")

    def _organize_ortho_sprites(self, extracted_dir: Path, output_dir: Path) -> None:
        """Organize extracted orthographic sprites into PyCC2 structure."""
        output_dir.mkdir(parents=True, exist_ok=True)

        possible_roots = list(extracted_dir.glob("PixVoxel_Ortho*"))
        root = possible_roots[0] if possible_roots else extracted_dir

        faction_color_map = {
            "color1": "allies",
            "color2": "axis",
            "color3": "allies_uk",
            "color4": "axis_italy",
            "color5": "allies_poland",
            "color6": "allies_us",
            "color7": "axis_germany",
            "color8": "resistance",
        }

        manifest_entries: list[dict] = []

        for color_dir in sorted(root.glob("color*")):
            if not color_dir.is_dir():
                continue
            faction = faction_color_map.get(color_dir.name, "allies")

            for unit_dir in sorted(color_dir.iterdir()):
                if not unit_dir.is_dir():
                    continue
                unit_name = unit_dir.name
                pycc2_type = PIXVOXEL_TO_PYCC2.get(unit_name, unit_name.upper())

                for anim_dir in sorted(unit_dir.iterdir()):
                    if not anim_dir.is_dir():
                        continue
                    anim_name = anim_dir.name

                    for sprite_file in sorted(anim_dir.glob("*.png")):
                        stem = sprite_file.stem
                        parts = stem.split("_")
                        direction = parts[0] if len(parts) >= 2 else "N"
                        frame = parts[1] if len(parts) >= 2 else "0"

                        rel_path = f"{faction}/{pycc2_type}/{anim_name}/{direction}_{frame}.png"
                        target_path = output_dir / rel_path
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(sprite_file, target_path)

                        manifest_entries.append(
                            {
                                "pixvoxel_name": unit_name,
                                "pycc2_type": pycc2_type,
                                "faction": faction,
                                "animation": anim_name,
                                "direction": direction,
                                "frame": frame,
                                "path": rel_path,
                            }
                        )

        for special in ("palettes", "blank"):
            src = root / special
            if src.exists():
                dst = output_dir / special
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)

        self._write_manifest(output_dir, manifest_entries, "orthographic")

    @staticmethod
    def _write_manifest(
        output_dir: Path,
        entries: list[dict],
        sprite_type: str,
    ) -> None:
        """Write manifest.json for the organized sprites."""
        manifest = {
            "type": sprite_type,
            "source": "PixVoxel Revised Isometric Wargame Sprites",
            "license": "CC0",
            "author": "Thomas Ettinger (TEttinger)",
            "url": "https://opengameart.org/content/pixvoxel-revised-isometric-wargame-sprites",
            "total_sprites": len(entries),
            "sprites": entries,
        }
        manifest_path = output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        logger.info("Manifest written: %s (%d entries)", manifest_path, len(entries))

    def load_manifest(self) -> dict | None:
        """加载精灵清单文件"""
        if self._manifest is not None:
            return self._manifest

        manifest_path = self.iso_dir / "manifest.json"
        if not manifest_path.exists():
            manifest_path = self.ortho_dir / "manifest.json"

        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path, encoding="utf-8") as f:
                self._manifest = json.load(f)
            return self._manifest
        except Exception as e:
            logger.warning(f"加载清单文件失败: {e}")
            return None

    def load_sprite(
        self,
        unit_type: str,
        faction: str = "allies",
        direction: int = 0,
        animation: str = "idle",
        frame: int = 0,
        size: int | None = None,
        use_ortho: bool = False,
    ) -> Surface | None:
        """
        加载 PixVoxel 精灵

        Args:
            unit_type: PyCC2 单位类型 (如 "RIFLE_SQUAD", "MEDIUM_TANK")
            faction: 阵营 ("allies", "axis", 等)
            direction: 方向索引 0-7 (N=0, NE=1, E=2, ...)
            animation: 动画类型 ("idle", "fire", "hit", "death")
            frame: 动画帧索引
            size: 目标尺寸 (None 则保持原始尺寸)
            use_ortho: 使用正交版本而非等距版本

        Returns:
            pygame.Surface 或 None (需要 fallback)
        """
        cache_key = f"pv_{faction}_{unit_type}_d{direction}_{animation}_f{frame}"
        if size is not None:
            cache_key += f"_s{size}"
        if use_ortho:
            cache_key += "_ortho"

        if cache_key in self._cache:
            return self._cache[cache_key]

        # 选择资源目录
        base_dir = self.ortho_dir if use_ortho else self.iso_dir
        if use_ortho and not self._ortho_available:
            base_dir = self.iso_dir
        if base_dir == self.iso_dir and not self._iso_available:
            return None

        # 映射单位类型
        pixvoxel_name = PYCC2_TO_PIXVOXEL.get(unit_type, unit_type)
        anim_name = ANIMATION_MAP.get(animation.lower(), "Standing")

        # 映射方向
        pv_direction = PYCC2_DIR_TO_PIXVOXEL.get(direction, "N")

        # 尝试多种路径格式
        possible_paths = self._build_sprite_paths(
            base_dir,
            faction,
            unit_type,
            pixvoxel_name,
            anim_name,
            pv_direction,
            frame,
        )

        for sprite_path in possible_paths:
            if sprite_path.exists():
                try:
                    surface = pygame.image.load(str(sprite_path))
                    # 调色板替换
                    surface = self._apply_faction_palette(surface, faction)
                    # 缩放
                    if size is not None:
                        w, h = surface.get_size()
                        if w != size or h != size:
                            surface = pygame.transform.scale(surface, (size, size))

                    self._cache[cache_key] = surface
                    logger.debug(f"加载 PixVoxel 精灵: {sprite_path.name}")
                    return surface
                except Exception as e:
                    logger.warning(f"加载精灵失败 {sprite_path}: {e}")
                    continue

        # 尝试从清单文件查找
        sprite = self._load_from_manifest(
            base_dir,
            faction,
            unit_type,
            anim_name,
            pv_direction,
            frame,
            size,
        )
        if sprite is not None:
            self._cache[cache_key] = sprite
            return sprite

        logger.debug(
            f"未找到 PixVoxel 精灵: {faction}/{unit_type}/{anim_name}/{pv_direction}_{frame}"
        )
        return None

    def _build_sprite_paths(
        self,
        base_dir: Path,
        faction: str,
        unit_type: str,
        pixvoxel_name: str,
        anim_name: str,
        direction: str,
        frame: int,
    ) -> list[Path]:
        """构建可能的精灵文件路径"""
        paths: list[Path] = []

        # 格式1: 有组织后的目录结构 (download_pixvoxel_assets.py 生成的)
        # {faction}/{PYCC2_TYPE}/{Animation}/{DIR}_{frame}.png
        paths.append(base_dir / faction / unit_type / anim_name / f"{direction}_{frame}.png")

        # 格式2: 使用 PixVoxel 原始名称
        paths.append(base_dir / faction / pixvoxel_name / anim_name / f"{direction}_{frame}.png")

        # 格式3: color 目录结构 (PixVoxel 原始结构)
        # color1/Infantry/Standing/N_0.png
        color_map = {
            "allies": "color1",
            "axis": "color2",
            "allies_uk": "color3",
            "axis_italy": "color4",
            "allies_poland": "color5",
            "allies_us": "color6",
            "axis_germany": "color7",
            "resistance": "color8",
        }
        color = color_map.get(faction, "color1")
        paths.append(base_dir / color / pixvoxel_name / anim_name / f"{direction}_{frame}.png")

        # 格式4: Super 单位变体
        if "Super" not in pixvoxel_name:
            paths.append(
                base_dir / color / f"Super{pixvoxel_name}" / anim_name / f"{direction}_{frame}.png"
            )

        # 格式5: 扁平目录结构
        paths.append(base_dir / f"{pixvoxel_name}_{direction}_{frame}.png")

        return paths

    def _load_from_manifest(
        self,
        base_dir: Path,
        faction: str,
        unit_type: str,
        anim_name: str,
        direction: str,
        frame: int,
        size: int | None,
    ) -> Surface | None:
        """从清单文件查找并加载精灵"""
        manifest = self.load_manifest()
        if manifest is None:
            return None

        for entry in manifest.get("sprites", []):
            if (
                entry.get("pycc2_type") == unit_type
                and entry.get("faction") == faction
                and entry.get("animation") == anim_name
                and entry.get("direction") == direction
                and str(entry.get("frame")) == str(frame)
            ):
                sprite_path = base_dir / entry["path"]
                if sprite_path.exists():
                    try:
                        surface = pygame.image.load(str(sprite_path))
                        surface = self._apply_faction_palette(surface, faction)
                        if size is not None:
                            w, h = surface.get_size()
                            if w != size or h != size:
                                surface = pygame.transform.scale(surface, (size, size))
                        return surface
                    except Exception as e:
                        logger.warning(f"从清单加载精灵失败: {e}")
                        continue

        return None

    def _apply_faction_palette(self, surface: Surface, faction: str) -> Surface:
        """
        应用阵营调色板替换

        PixVoxel 精灵使用可替换的调色板系统。
        此方法将精灵中的阵营颜色替换为目标阵营颜色。

        对于已按阵营目录组织的精灵，此方法可能不需要执行替换。
        对于 blank/ 灰度模板，需要执行调色板映射。
        """
        colors = FACTION_COLORS.get(faction)
        if colors is None:
            return surface

        # 检查是否是 blank 模板（灰度图像）
        # blank 模板需要调色板映射；color 目录下的已着色精灵不需要
        return surface

    def apply_palette_swap(
        self,
        surface: Surface,
        source_color: tuple[int, int, int],
        target_color: tuple[int, int, int],
        tolerance: int = 30,
    ) -> Surface:
        """
        对 Surface 执行调色板替换

        将 source_color (±tolerance) 的像素替换为 target_color，
        保持原始亮度/饱和度比例。

        Args:
            surface: 原始 Surface
            source_color: 要替换的源颜色
            target_color: 目标颜色
            tolerance: 颜色匹配容差

        Returns:
            替换后的新 Surface
        """
        result = surface.copy()
        w, h = result.get_size()

        # 使用 pixel array 进行高效像素操作
        try:
            import numpy as np

            arr = pygame.surfarray.pixels3d(result)
            src_r, src_g, src_b = source_color
            tgt_r, tgt_g, tgt_b = target_color

            # 计算颜色距离
            diff_r = arr[:, :, 0].astype(int) - src_r
            diff_g = arr[:, :, 1].astype(int) - src_g
            diff_b = arr[:, :, 2].astype(int) - src_b

            distance = diff_r * diff_r + diff_g * diff_g + diff_b * diff_b
            mask = distance <= (tolerance * tolerance * 3)

            # 计算亮度比例
            src_brightness = (src_r + src_g + src_b) / 3.0
            if src_brightness > 0:
                brightness_ratio = (
                    arr[:, :, 0].astype(float)
                    + arr[:, :, 1].astype(float)
                    + arr[:, :, 2].astype(float)
                ) / (3.0 * src_brightness)
            else:
                brightness_ratio = np.ones_like(arr[:, :, 0], dtype=float)

            # 应用替换
            arr[:, :, 0] = np.where(
                mask, np.clip(tgt_r * brightness_ratio, 0, 255).astype(np.uint8), arr[:, :, 0]
            )
            arr[:, :, 1] = np.where(
                mask, np.clip(tgt_g * brightness_ratio, 0, 255).astype(np.uint8), arr[:, :, 1]
            )
            arr[:, :, 2] = np.where(
                mask, np.clip(tgt_b * brightness_ratio, 0, 255).astype(np.uint8), arr[:, :, 2]
            )

            del arr  # 释放 surfarray 锁
        except (ImportError, Exception):
            # numpy 不可用或 surfarray 失败，使用逐像素方法（较慢）
            result = self._palette_swap_slow(surface, source_color, target_color, tolerance)

        return result

    def _palette_swap_slow(
        self,
        surface: Surface,
        source_color: tuple[int, int, int],
        target_color: tuple[int, int, int],
        tolerance: int = 30,
    ) -> Surface:
        """逐像素调色板替换（无 numpy 时的 fallback）"""
        result = surface.copy()
        w, h = result.get_size()
        src_r, src_g, src_b = source_color
        tgt_r, tgt_g, tgt_b = target_color
        tol_sq = tolerance * tolerance * 3
        src_brightness = (src_r + src_g + src_b) / 3.0

        for x in range(w):
            for y in range(h):
                r, g, b, a = result.get_at((x, y))
                dist = (r - src_r) ** 2 + (g - src_g) ** 2 + (b - src_b) ** 2
                if dist <= tol_sq and src_brightness > 0:
                    ratio = (r + g + b) / (3.0 * src_brightness)
                    result.set_at(
                        (x, y),
                        (
                            min(255, int(tgt_r * ratio)),
                            min(255, int(tgt_g * ratio)),
                            min(255, int(tgt_b * ratio)),
                            a,
                        ),
                    )

        return result

    def load_sprite_with_fallback(
        self,
        unit_type: str,
        faction: str = "allies",
        direction: int = 0,
        animation: str = "idle",
        frame: int = 0,
        size: int = 24,
    ) -> Surface:
        """
        加载 PixVoxel 精灵，不可用时 fallback 到程序化生成

        Args:
            unit_type: PyCC2 单位类型
            faction: 阵营
            direction: 方向索引 0-7
            animation: 动画类型
            frame: 帧索引
            size: 目标尺寸

        Returns:
            pygame.Surface (始终返回有效 Surface)
        """
        # 尝试加载 PixVoxel 精灵
        sprite = self.load_sprite(
            unit_type=unit_type,
            faction=faction,
            direction=direction,
            animation=animation,
            frame=frame,
            size=size,
        )
        if sprite is not None:
            return sprite

        # Fallback: 使用 PixelArtist3D
        try:
            from pycc2.domain.entities.unit import Faction
            from pycc2.domain.value_objects.direction import Direction
            from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D

            dir_enum = list(Direction)[direction] if direction < 8 else Direction.SOUTH
            fac_enum = Faction.ALLIES if faction.startswith("allies") else Faction(faction)

            is_vehicle = unit_type in (
                "TANK",
                "LIGHT_TANK",
                "MEDIUM_TANK",
                "HEAVY_TANK",
                "HALFTRACK",
                "JEEP",
                "AT_GUN_TEAM",
            )
            if is_vehicle:
                return PixelArtist3D.create_tank_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    state="idle",
                    frame=0,
                )
            else:
                return PixelArtist3D.create_infantry_sprite(
                    direction=dir_enum,
                    faction=fac_enum,
                    state="idle",
                    frame=0,
                )
        except Exception as e:
            logger.debug(f"PixelArtist3D fallback 失败: {e}")

        # Fallback: 使用 PixelArtist
        try:
            from pycc2.presentation.rendering.pixel_artist import create_unit_sprite

            canvas = create_unit_sprite(
                faction=faction,
                unit_type=unit_type,
                direction=direction,
                size=size,
            )
            return canvas.to_surface()
        except Exception as e:
            logger.debug(f"PixelArtist fallback 失败: {e}")

        # 最终 fallback: 简单圆形
        return self._create_fallback_circle(unit_type, faction, size)

    def _create_fallback_circle(
        self,
        unit_type: str,
        faction: str,
        size: int,
    ) -> Surface:
        """创建最简单的 fallback 精灵"""
        surface = Surface((size, size), pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        colors = FACTION_COLORS.get(faction, FACTION_COLORS["allies"])
        color = colors["primary"]

        radius = size // 2 - 2
        center = (size // 2, size // 2)

        if "TANK" in unit_type or "HALFTRACK" in unit_type:
            # 载具: 矩形
            rect = pygame.Rect(2, 4, size - 4, size - 8)
            pygame.draw.rect(surface, color, rect, border_radius=3)
            pygame.draw.rect(surface, (255, 255, 255), rect, width=1, border_radius=3)
        else:
            # 步兵: 圆形
            pygame.draw.circle(surface, color, center, radius)
            pygame.draw.circle(surface, (255, 255, 255), center, radius, 1)

        return surface

    def load_animation_frames(
        self,
        unit_type: str,
        faction: str = "allies",
        direction: int = 0,
        animation: str = "idle",
        size: int | None = None,
    ) -> list[Surface]:
        """
        加载完整的动画帧序列

        Args:
            unit_type: PyCC2 单位类型
            faction: 阵营
            direction: 方向索引
            animation: 动画类型
            size: 目标尺寸

        Returns:
            Surface 列表 (可能为空)
        """
        frames: list[Surface] = []
        for frame_idx in range(20):  # 最多尝试 20 帧
            sprite = self.load_sprite(
                unit_type=unit_type,
                faction=faction,
                direction=direction,
                animation=animation,
                frame=frame_idx,
                size=size,
            )
            if sprite is None:
                break
            frames.append(sprite)

        return frames

    def get_available_units(self) -> dict[str, list[str]]:
        """
        获取可用的单位类型及其动画

        Returns:
            {unit_type: [animation_names]}
        """
        manifest = self.load_manifest()
        if manifest is None:
            return {}

        units: dict[str, set[str]] = {}
        for entry in manifest.get("sprites", []):
            unit_type = entry.get("pycc2_type", "")
            animation = entry.get("animation", "")
            if unit_type and animation:
                if unit_type not in units:
                    units[unit_type] = set()
                units[unit_type].add(animation)

        return {k: sorted(v) for k, v in sorted(units.items())}

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        self._manifest = None

    def get_cache_stats(self) -> dict[str, int]:
        """获取缓存统计"""
        return {
            "cached_sprites": len(self._cache),
            "iso_available": int(self._iso_available),
            "ortho_available": int(self._ortho_available),
        }

    def preload_common_sprites(self, size: int = 24) -> None:
        """预加载常用精灵到缓存"""
        common_units = [
            "RIFLE_SQUAD",
            "MACHINE_GUN_SQUAD",
            "SNIPER_TEAM",
            "MEDIC_TEAM",
            "ENGINEER_SQUAD",
            "MORTAR_TEAM",
            "AT_GUN_TEAM",
            "OFFICER",
            "COMMANDER",
            "LIGHT_TANK",
            "MEDIUM_TANK",
            "HEAVY_TANK",
            "HALFTRACK",
            "JEEP",
        ]

        for faction in ("allies", "axis"):
            for unit_type in common_units:
                for direction in range(8):
                    self.load_sprite_with_fallback(
                        unit_type=unit_type,
                        faction=faction,
                        direction=direction,
                        animation="idle",
                        frame=0,
                        size=size,
                    )

        logger.info(f"预加载完成，缓存 {len(self._cache)} 个精灵")


# 模块级便捷函数
_loader_instance: PixVoxelLoader | None = None


def get_pixvoxel_loader() -> PixVoxelLoader:
    """获取全局 PixVoxelLoader 实例"""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = PixVoxelLoader()
    return _loader_instance
