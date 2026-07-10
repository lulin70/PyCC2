#!/usr/bin/env python3
"""
下载 PixVoxel Revised Isometric Wargame Sprites

从 OpenGameArt 下载 CC0 许可的等距战争游戏精灵资源，
提取到 PyCC2 项目的 assets 目录，并生成清单文件。

资源来源:
- OpenGameArt: https://opengameart.org/content/pixvoxel-revised-isometric-wargame-sprites
- GitHub: https://github.com/tommyettinger/PixVoxelAssets
- 许可证: CC0 (公共领域)

用法:
    python scripts/download_pixvoxel_assets.py
    python scripts/download_pixvoxel_assets.py --ortho  # 同时下载正交版本
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# === 配置 ===
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets" / "sprites"
DOWNLOAD_DIR = PROJECT_ROOT / "tmp" / "pixvoxel_download"

ISO_OUTPUT_DIR = ASSETS_DIR / "pixvoxel_isometric"
ORTHO_OUTPUT_DIR = ASSETS_DIR / "pixvoxel_ortho"

# 下载链接
ISO_URL = "https://opengameart.org/sites/default/files/Revised_PixVoxel_Wargame_1.7z"
ORTHO_URL = "https://opengameart.org/sites/default/files/Blank_PixVoxel_Wargame_Ortho_A.7z"

ISO_ARCHIVE = DOWNLOAD_DIR / "Revised_PixVoxel_Wargame.7z"
ORTHO_ARCHIVE = DOWNLOAD_DIR / "Blank_PixVoxel_Wargame_Ortho_A.7z"

# PixVoxel 单位名称 → PyCC2 单位类型映射
UNIT_NAME_MAP: dict[str, str] = {
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

# PixVoxel 方向名称 → PyCC2 方向索引 (4方向 → 8方向映射)
# PixVoxel 使用 4 个等距方向: N, E, S, W
DIRECTION_MAP: dict[str, int] = {
    "N": 0,  # North
    "NE": 1,  # Northeast (通过翻转 W 得到)
    "E": 2,  # East
    "SE": 3,  # Southeast (通过翻转 SW 得到)
    "S": 4,  # South
    "SW": 5,  # Southwest
    "W": 6,  # West
    "NW": 7,  # Northwest (通过翻转 NE 得到)
}

# PixVoxel 4 方向 → 8 方向补全规则
# PixVoxel 原始只有 N, E, S, W 四个方向
ISO_DIRECTION_MAP: dict[str, list[str]] = {
    "N": ["N", "NE"],  # NE 由 N 翻转或近似
    "E": ["E", "SE"],  # SE 由 E 近似
    "S": ["S", "SW"],  # SW 由 S 翻转或近似
    "W": ["W", "NW"],  # NW 由 W 翻转或近似
}


# === Blank 版本常量 (Blank_PixVoxel_Wargame_Ortho_A) ===

# Blank 版本单位名 → PyCC2 单位类型 (基于 UNIT_INFO.txt)
BLANK_UNIT_NAME_MAP: dict[str, str] = {
    # 步兵类 (UNIT_INFO.txt: Infantry → Infantry, Infantry_P → Bazooka, etc.)
    "Infantry": "RIFLE_SQUAD",
    "Infantry_P": "AT_GUN_TEAM",  # Bazooka
    "Infantry_S": "RIFLE_SQUAD",  # Bike (近似步兵)
    "Infantry_T": "SNIPER_TEAM",  # Sniper
    "Infantry_PS": "AT_GUN_TEAM",  # Missile Trooper
    "Infantry_PT": "MORTAR_TEAM",  # Mortar Trooper
    "Infantry_ST": "ASSAULT_SQUAD",  # Jetpack Trooper
    "Flamethrower": "FLAMETHROWER_TEAM",
    "Recon": "JEEP",  # Recon (近似载具)
    # 炮兵类
    "Artillery": "AT_GUN_TEAM",  # Light Artillery
    "Artillery_P": "AT_GUN_TEAM",  # Defensive Artillery
    "Artillery_S": "AT_GUN_TEAM",  # AA Artillery
    "Artillery_T": "AT_GUN_TEAM",  # Stealth Artillery
    # 载具类
    "Tank": "LIGHT_TANK",  # Light Tank
    "Tank_P": "HEAVY_TANK",  # Heavy Tank
    "Tank_S": "LIGHT_TANK",  # AA Tank (近似)
    "Tank_T": "LIGHT_TANK",  # Recon Tank (近似)
    "Truck": "JEEP",  # Supply Truck
    "Truck_P": "HALFTRACK",  # Build Rig (近似)
    "Truck_S": "JEEP",  # Amphi Transport
    "Truck_T": "JEEP",  # Jammer
    # 志愿兵类
    "Volunteer": "SUPPORT",
    "Volunteer_P": "ENGINEER_SQUAD",  # Engineer
    "Volunteer_S": "SUPPORT",  # Smuggler
    "Volunteer_T": "MEDIC_TEAM",  # Medic
    # 设施
    "City": "BUILDING",
    "Factory": "BUILDING",
    "Airport": "BUILDING",
    "Dock": "BUILDING",
    "Laboratory": "BUILDING",
    "Castle": "BUILDING",
    "Estate": "BUILDING",
    # 平民
    "Civilian": "SUPPORT",  # 近似
}

# Blank 版本 face0-3 → PyCC2 方向索引
# 假设: face0=S(4), face1=E(2), face2=N(0), face3=W(6) — 最常见精灵排列
BLANK_FACE_TO_DIRECTION: dict[int, int] = {
    0: 4,  # face0 → South
    1: 2,  # face1 → East
    2: 0,  # face2 → North
    3: 6,  # face3 → West
}

# 阵营 → PixVoxel 调色板编号
# 基于 PALETTE_INFO.txt: 8n+0=Dark, 8n+1=White, 8n+2=Red, 8n+3=Orange,
#                         8n+4=Yellow, 8n+5=Green, 8n+6=Blue, 8n+7=Purple
FACTION_PALETTE_MAP: dict[str, int] = {
    "allies": 5,  # Green (盟军绿)
    "axis": 0,  # Dark (轴心国灰)
    "allies_uk": 6,  # Blue (英军蓝)
    "allies_us": 13,  # Green, 第二组皮肤 (美军橄榄绿)
    "allies_poland": 2,  # Red (波兰军红)
    "axis_germany": 8,  # Dark, 第二组皮肤 (德军深灰)
    "axis_italy": 3,  # Orange (意军沙色, 近似)
    "resistance": 7,  # Purple (抵抗军紫)
}


def download_file(url: str, output_path: Path) -> bool:
    """使用多种方法下载文件"""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        logger.info(f"文件已存在，跳过下载: {output_path}")
        return True

    # 方法1: curl
    if shutil.which("curl"):
        logger.info(f"使用 curl 下载: {url}")
        cmd = [
            "curl",
            "-L",
            "-C",
            "-",
            "--retry",
            "5",
            "--retry-delay",
            "2",
            "--max-time",
            "600",
            "-o",
            str(output_path),
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and output_path.exists():
            logger.info(f"下载成功: {output_path}")
            return True
        logger.warning(f"curl 下载失败: {result.stderr}")

    # 方法2: wget
    if shutil.which("wget"):
        logger.info(f"使用 wget 下载: {url}")
        cmd = [
            "wget",
            "--continue",
            "--timeout=30",
            "--tries=5",
            "-O",
            str(output_path),
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and output_path.exists():
            logger.info(f"下载成功: {output_path}")
            return True
        logger.warning(f"wget 下载失败: {result.stderr}")

    # 方法3: Python urllib
    logger.info(f"使用 Python urllib 下载: {url}")
    try:
        import urllib.request

        urllib.request.urlretrieve(url, str(output_path))
        if output_path.exists():
            logger.info(f"下载成功: {output_path}")
            return True
    except Exception as e:
        logger.warning(f"urllib 下载失败: {e}")

    logger.error(f"所有下载方法均失败: {url}")
    return False


def extract_7z(archive_path: Path, output_dir: Path) -> bool:
    """提取 7z 压缩包"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 方法1: py7zr
    try:
        import py7zr

        logger.info(f"使用 py7zr 提取: {archive_path}")
        with py7zr.SevenZipFile(str(archive_path), mode="r") as z:
            z.extractall(path=str(output_dir))
        logger.info(f"提取成功: {output_dir}")
        return True
    except ImportError:
        logger.info("py7zr 未安装，尝试其他方法")
    except Exception as e:
        logger.warning(f"py7zr 提取失败: {e}")

    # 方法2: 7z 命令行
    if shutil.which("7z"):
        logger.info(f"使用 7z 命令提取: {archive_path}")
        cmd = ["7z", "x", str(archive_path), f"-o{output_dir}", "-y"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"提取成功: {output_dir}")
            return True
        logger.warning(f"7z 提取失败: {result.stderr}")

    # 方法3: 7za (p7zip)
    if shutil.which("7za"):
        logger.info(f"使用 7za 命令提取: {archive_path}")
        cmd = ["7za", "x", str(archive_path), f"-o{output_dir}", "-y"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"提取成功: {output_dir}")
            return True
        logger.warning(f"7za 提取失败: {result.stderr}")

    # 方法4: Homebrew p7zip
    if shutil.which("/usr/local/bin/7z"):
        cmd = ["/usr/local/bin/7z", "x", str(archive_path), f"-o{output_dir}", "-y"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"提取成功: {output_dir}")
            return True

    logger.error(
        "无法提取 7z 文件。请安装以下任一工具:\n"
        "  pip install py7zr\n"
        "  brew install p7zip\n"
        "  或安装 7-Zip"
    )
    return False


def organize_isometric_sprites(extracted_dir: Path, output_dir: Path) -> None:
    """
    整理等距精灵到 PyCC2 目录结构

    PixVoxel 原始目录结构:
    Revised_PixVoxel_Wargame/
    ├── color1/   (白色军队)
    ├── color2/   (红色军队)
    ├── color3/   (蓝色军队)
    ├── ...
    ├── blank/    (灰度模板)
    ├── palettes/ (调色板文件)
    └── UNIT_INFO.txt

    每个颜色目录下:
    ├── Infantry/
    │   ├── Standing/
    │   │   ├── N_0.png, N_1.png, ...
    │   │   ├── E_0.png, E_1.png, ...
    │   │   ├── S_0.png, S_1.png, ...
    │   │   └── W_0.png, W_1.png, ...
    │   ├── Firing/
    │   └── Receive/
    ├── HeavyTank/
    └── ...
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 查找提取后的根目录
    possible_roots = list(extracted_dir.glob("Revised_PixVoxel_Wargame*"))
    if not possible_roots:
        possible_roots = [extracted_dir]

    root = possible_roots[0]
    logger.info(f"整理等距精灵，源目录: {root}")

    # 阵营颜色映射: PixVoxel color → PyCC2 faction
    faction_color_map = {
        "color1": "allies",  # 白色 → 盟军 (后续通过调色板换为绿色)
        "color2": "axis",  # 红色 → 轴心国 (后续通过调色板换为灰色)
        "color3": "allies_uk",  # 蓝色 → 英军
        "color4": "axis_italy",  # 黄色 → 意军
        "color5": "allies_poland",  # 紫色 → 波兰军
        "color6": "allies_us",  # 青色 → 美军
        "color7": "axis_germany",  # 橙色 → 德军
        "color8": "resistance",  # 粉色 → 抵抗军
    }

    manifest_entries: list[dict] = []

    for color_dir in sorted(root.glob("color*")):
        if not color_dir.is_dir():
            continue

        color_name = color_dir.name
        faction = faction_color_map.get(color_name, "allies")

        for unit_dir in sorted(color_dir.iterdir()):
            if not unit_dir.is_dir():
                continue

            unit_name = unit_dir.name
            pycc2_type = UNIT_NAME_MAP.get(unit_name, unit_name.upper())

            for anim_dir in sorted(unit_dir.iterdir()):
                if not anim_dir.is_dir():
                    continue

                anim_name = anim_dir.name  # Standing, Firing, Receive, etc.

                for sprite_file in sorted(anim_dir.glob("*.png")):
                    # 解析方向: 文件名格式为 {DIR}_{frame}.png
                    # 例如: N_0.png, E_1.png, S_0.png
                    stem = sprite_file.stem
                    parts = stem.split("_")
                    if len(parts) >= 2:
                        direction = parts[0]
                        frame = parts[1]
                    else:
                        direction = "N"
                        frame = "0"

                    # 构建目标路径
                    rel_path = f"{faction}/{pycc2_type}/{anim_name}/{direction}_{frame}.png"
                    target_path = output_dir / rel_path
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    # 复制文件
                    shutil.copy2(sprite_file, target_path)

                    manifest_entries.append(
                        {
                            "pixvoxel_name": unit_name,
                            "pycc2_type": pycc2_type,
                            "faction": faction,
                            "animation": anim_name,
                            "direction": direction,
                            "direction_index": DIRECTION_MAP.get(direction, 0),
                            "frame": frame,
                            "path": rel_path,
                        }
                    )

    # 同时复制调色板和空白模板
    for special_dir in ["palettes", "blank"]:
        src = root / special_dir
        if src.exists():
            dst = output_dir / special_dir
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            logger.info(f"复制 {special_dir} → {dst}")

    # 复制 UNIT_INFO.txt
    info_file = root / "UNIT_INFO.txt"
    if info_file.exists():
        shutil.copy2(info_file, output_dir / "UNIT_INFO.txt")

    # 写入清单文件
    _write_manifest(output_dir, manifest_entries, "isometric")
    logger.info(f"等距精灵整理完成，共 {len(manifest_entries)} 个文件")


def organize_ortho_sprites(extracted_dir: Path, output_dir: Path) -> None:
    """整理正交精灵到 PyCC2 目录结构"""
    output_dir.mkdir(parents=True, exist_ok=True)

    possible_roots = list(extracted_dir.glob("PixVoxel_Ortho*"))
    if not possible_roots:
        possible_roots = [extracted_dir]

    root = possible_roots[0]
    logger.info(f"整理正交精灵，源目录: {root}")

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
            pycc2_type = UNIT_NAME_MAP.get(unit_name, unit_name.upper())

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
                            "direction_index": DIRECTION_MAP.get(direction, 0),
                            "frame": frame,
                            "path": rel_path,
                        }
                    )

    for special_dir in ["palettes", "blank"]:
        src = root / special_dir
        if src.exists():
            dst = output_dir / special_dir
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    _write_manifest(output_dir, manifest_entries, "orthographic")
    logger.info(f"正交精灵整理完成，共 {len(manifest_entries)} 个文件")


def organize_ortho_blank_sprites(extracted_dir: Path, output_dir: Path) -> None:
    """整理 Blank 版本正交精灵到 PyCC2 目录结构

    Blank 版本结构 (Blank_PixVoxel_Wargame_Ortho_A):
    ├── standing_frames/{Unit}/{Unit}_Large_face{0-3}_{0-3}.png  (idle, 4 frames)
    ├── animation_frames/{Unit}/{Unit}_Large_face{0-3}_{attack|death}_{...}.png
    ├── Palettes/color{0-325}.png  (256x1 索引调色板)
    ├── UNIT_INFO.txt
    └── PALETTE_INFO.txt

    文件名格式:
      standing: {Zombie_}{Unit}_{Alt_}Large_face{0-3}_{frame}.png
      animation: {Zombie_}{Unit}_{Alt_}Large_face{0-3}_{attack|death}_{weapon}_{frame}.png

    只整理标准 male 版本 (跳过 Zombie_ 和 _Alt_ 变体)。

    输出结构:
    ├── standing_frames/{Unit}/  (保持原始 Blank PNG, 索引调色板)
    ├── animation_frames/{Unit}/
    ├── palettes/{faction}.png   (8 个阵营调色板)
    └── manifest.json
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 查找提取后的根目录
    possible_roots = list(extracted_dir.glob("Blank_PixVoxel_Wargame_Ortho*"))
    if not possible_roots:
        possible_roots = [extracted_dir]

    root = possible_roots[0]
    logger.info(f"整理 Blank 正交精灵，源目录: {root}")

    manifest_entries: list[dict] = []

    # === 1. 复制 standing_frames (idle 动画) ===
    standing_src = root / "standing_frames"
    if standing_src.exists():
        for unit_dir in sorted(standing_src.iterdir()):
            if not unit_dir.is_dir():
                continue

            unit_name = unit_dir.name
            pycc2_type = BLANK_UNIT_NAME_MAP.get(unit_name)
            if pycc2_type is None:
                logger.debug(f"跳过未映射的单位: {unit_name}")
                continue

            for sprite_file in sorted(unit_dir.glob("*.png")):
                stem = sprite_file.stem

                # 跳过 Zombie_ 和 _Alt_ 变体
                if stem.startswith("Zombie_") or "_Alt_" in stem:
                    continue

                # 解析文件名: {Unit}_Large_face{N}_{frame}
                # 去掉 Large_ 后分割
                cleaned = stem.replace("_Large_", "_")
                parts = cleaned.split("_")

                # 找到 face 部分
                face_idx = None
                for i, p in enumerate(parts):
                    if p.startswith("face"):
                        face_idx = i
                        break

                if face_idx is None or face_idx + 1 >= len(parts):
                    continue

                face_num = int(parts[face_idx].replace("face", ""))
                frame = int(parts[face_idx + 1])

                if face_num not in BLANK_FACE_TO_DIRECTION:
                    continue

                direction = BLANK_FACE_TO_DIRECTION[face_num]

                # 目标路径: standing_frames/{Unit}/{Unit}_face{N}_{frame}.png
                rel_path = f"standing_frames/{unit_name}/{stem}.png"
                target_path = output_dir / rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sprite_file, target_path)

                manifest_entries.append(
                    {
                        "unit_name": unit_name,
                        "pycc2_type": pycc2_type,
                        "animation": "idle",
                        "face": face_num,
                        "direction": direction,
                        "frame": frame,
                        "path": rel_path,
                    }
                )

    logger.info(f"standing_frames: {len(manifest_entries)} 个文件")

    # === 2. 复制 animation_frames (attack/death 动画) ===
    anim_count_before = len(manifest_entries)
    anim_src = root / "animation_frames"
    if anim_src.exists():
        for unit_dir in sorted(anim_src.iterdir()):
            if not unit_dir.is_dir():
                continue

            unit_name = unit_dir.name
            pycc2_type = BLANK_UNIT_NAME_MAP.get(unit_name)
            if pycc2_type is None:
                continue

            for sprite_file in sorted(unit_dir.glob("*.png")):
                stem = sprite_file.stem

                if stem.startswith("Zombie_") or "_Alt_" in stem:
                    continue

                cleaned = stem.replace("_Large_", "_")
                parts = cleaned.split("_")

                face_idx = None
                for i, p in enumerate(parts):
                    if p.startswith("face"):
                        face_idx = i
                        break

                if face_idx is None or face_idx + 2 >= len(parts):
                    continue

                face_num = int(parts[face_idx].replace("face", ""))
                anim_type = parts[face_idx + 1]  # attack or death

                if face_num not in BLANK_FACE_TO_DIRECTION:
                    continue

                direction = BLANK_FACE_TO_DIRECTION[face_num]

                # PyCC2 动画映射: attack → fire, death → death
                pycc2_anim = "fire" if anim_type == "attack" else anim_type

                # 提取帧号 (最后一个数字部分)
                frame = int(parts[-1])

                rel_path = f"animation_frames/{unit_name}/{stem}.png"
                target_path = output_dir / rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sprite_file, target_path)

                manifest_entries.append(
                    {
                        "unit_name": unit_name,
                        "pycc2_type": pycc2_type,
                        "animation": pycc2_anim,
                        "face": face_num,
                        "direction": direction,
                        "frame": frame,
                        "path": rel_path,
                    }
                )

    logger.info(f"animation_frames: {len(manifest_entries) - anim_count_before} 个文件")

    # === 3. 复制阵营调色板 ===
    palettes_src = root / "Palettes"
    palettes_dst = output_dir / "palettes"
    palettes_dst.mkdir(parents=True, exist_ok=True)

    for faction, palette_num in FACTION_PALETTE_MAP.items():
        palette_file = palettes_src / f"color{palette_num}.png"
        if palette_file.exists():
            shutil.copy2(palette_file, palettes_dst / f"{faction}.png")
            logger.info(f"调色板: {faction} ← color{palette_num}.png")
        else:
            logger.warning(f"调色板文件不存在: color{palette_num}.png (faction={faction})")

    # === 4. 复制信息文件 ===
    for info_file in ("UNIT_INFO.txt", "PALETTE_INFO.txt", "LICENSE.txt"):
        src = root / info_file
        if src.exists():
            shutil.copy2(src, output_dir / info_file)

    # === 5. 写入 manifest.json ===
    manifest = {
        "type": "orthographic_blank",
        "source": "PixVoxel Very Diverse Ortho Wargame Sprites (Blank version)",
        "license": "CC0",
        "author": "Thomas Ettinger (TEttinger)",
        "url": "https://opengameart.org/content/pixvoxel-very-diverse-ortho-wargame-sprites",
        "total_sprites": len(manifest_entries),
        "unit_name_map": BLANK_UNIT_NAME_MAP,
        "face_to_direction": BLANK_FACE_TO_DIRECTION,
        "faction_palette_map": FACTION_PALETTE_MAP,
        "animation_map": {"idle": "standing_frames", "fire": "attack", "death": "death"},
        "note": "Blank PNG 使用索引调色板, 需运行时调色板替换 (_apply_faction_palette)",
        "sprites": manifest_entries,
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Blank 正交精灵整理完成: {len(manifest_entries)} 个文件, manifest: {manifest_path}"
    )


def _write_manifest(
    output_dir: Path,
    entries: list[dict],
    sprite_type: str,
) -> None:
    """写入精灵清单文件"""
    manifest = {
        "type": sprite_type,
        "source": "PixVoxel Revised Isometric Wargame Sprites",
        "license": "CC0",
        "author": "Thomas Ettinger (TEttinger)",
        "url": "https://opengameart.org/content/pixvoxel-revised-isometric-wargame-sprites",
        "total_sprites": len(entries),
        "unit_name_map": UNIT_NAME_MAP,
        "direction_map": DIRECTION_MAP,
        "sprites": entries,
    }

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    logger.info(f"清单文件已写入: {manifest_path}")


def main() -> int:
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="下载并整理 PixVoxel 等距战争游戏精灵")
    parser.add_argument(
        "--ortho",
        action="store_true",
        help="同时下载正交版本精灵",
    )
    parser.add_argument(
        "--iso-only",
        action="store_true",
        help="仅下载等距版本（默认行为）",
    )
    parser.add_argument(
        "--keep-archive",
        action="store_true",
        help="下载后保留压缩包",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("PixVoxel Revised Isometric Wargame Sprites 下载器")
    logger.info("许可证: CC0 (公共领域)")
    logger.info("=" * 60)

    # === 下载等距版本 ===
    logger.info("\n--- 下载等距精灵 ---")
    if not download_file(ISO_URL, ISO_ARCHIVE):
        logger.error("等距精灵下载失败！")
        logger.info(f"请手动下载:\n  URL: {ISO_URL}\n  保存到: {ISO_ARCHIVE}\n然后重新运行此脚本。")
        return 1

    # 提取
    iso_extract_dir = DOWNLOAD_DIR / "iso_extracted"
    if not extract_7z(ISO_ARCHIVE, iso_extract_dir):
        logger.error("等距精灵提取失败！")
        return 1

    # 整理
    organize_isometric_sprites(iso_extract_dir, ISO_OUTPUT_DIR)

    # === 下载正交版本（可选）===
    if args.ortho:
        logger.info("\n--- 下载正交精灵 ---")
        if download_file(ORTHO_URL, ORTHO_ARCHIVE):
            ortho_extract_dir = DOWNLOAD_DIR / "ortho_extracted"
            if extract_7z(ORTHO_ARCHIVE, ortho_extract_dir):
                # Blank 版本使用 organize_ortho_blank_sprites (索引调色板结构)
                organize_ortho_blank_sprites(ortho_extract_dir, ORTHO_OUTPUT_DIR)
            else:
                logger.warning("正交精灵提取失败")
        else:
            logger.warning("正交精灵下载失败，跳过")

    # === 清理 ===
    if not args.keep_archive:
        logger.info("\n--- 清理临时文件 ---")
        if DOWNLOAD_DIR.exists():
            shutil.rmtree(DOWNLOAD_DIR)
            logger.info(f"已删除临时目录: {DOWNLOAD_DIR}")

    logger.info("\n" + "=" * 60)
    logger.info("完成！精灵已安装到:")
    logger.info(f"  等距: {ISO_OUTPUT_DIR}")
    if args.ortho:
        logger.info(f"  正交: {ORTHO_OUTPUT_DIR}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
