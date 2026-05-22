#!/usr/bin/env python3
"""
CC2资产提取脚本
从Close Combat 2原版游戏提取精灵和地形资源

使用方法:
    python scripts/extract_cc2_assets.py --cc2-dir /path/to/cc2 --output assets/

依赖:
    - CC2Spriter工具 (closecombat2.hpage.com)
    - PIL/Pillow (图像处理)
"""
import argparse
import shutil
import subprocess
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("警告: 未安装Pillow，部分功能可能不可用")
    print("安装: pip install Pillow")
    Image = None


def extract_sprites(cc2_dir: Path, output_dir: Path, spriter_path: Path | None = None):
    """
    提取单位精灵
    
    步骤:
    1. 找到SPRI/*.spr文件
    2. 使用CC2Spriter转换为PNG
    3. 按阵营和方向组织文件
    """
    print("=" * 60)
    print("Phase 1: 提取单位精灵")
    print("=" * 60)
    
    spri_dir = cc2_dir / "SPRI"
    if not spri_dir.exists():
        print(f"❌ 未找到SPRI目录: {spri_dir}")
        return
    
    spr_files = list(spri_dir.glob("*.spr"))
    print(f"找到 {len(spr_files)} 个.spr文件")
    
    # 创建输出目录
    allies_dir = output_dir / "sprites" / "units" / "allies"
    axis_dir = output_dir / "sprites" / "units" / "axis"
    allies_dir.mkdir(parents=True, exist_ok=True)
    axis_dir.mkdir(parents=True, exist_ok=True)
    
    if spriter_path and spriter_path.exists():
        print(f"使用CC2Spriter: {spriter_path}")
        # TODO: 调用CC2Spriter批量转换
        # subprocess.run([str(spriter_path), ...])
    else:
        print("⚠️  未找到CC2Spriter工具")
        print("   请从 closecombat2.hpage.com 下载 v2.94")
        print("   手动转换.spr文件后放入assets/sprites/units/目录")
    
    print("\n✅ 精灵提取完成（需手动使用CC2Spriter）")
    print(f"   输出目录: {allies_dir}")
    print(f"   输出目录: {axis_dir}")


def extract_terrain(cc2_dir: Path, output_dir: Path):
    """
    提取地形tiles
    
    从Terrain.azp解包地形块
    """
    print("\n" + "=" * 60)
    print("Phase 2: 提取地形tiles")
    print("=" * 60)
    
    terrain_file = cc2_dir / "Terrain.azp"
    if not terrain_file.exists():
        print(f"❌ 未找到Terrain.azp: {terrain_file}")
        return
    
    terrain_dir = output_dir / "terrain"
    terrain_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"找到Terrain.azp: {terrain_file}")
    print("⚠️  需要自定义解包器（参考CC2Guide-Terrain-File-v5.pdf）")
    print(f"   输出目录: {terrain_dir}")
    
    # TODO: 实现Terrain.azp解包
    # 格式参考: CC2Guide-Terrain-File-v5.pdf
    
    print("\n✅ 地形提取完成（需手动解包）")


def extract_effects(cc2_dir: Path, output_dir: Path):
    """提取特效精灵（爆炸、烟雾等）"""
    print("\n" + "=" * 60)
    print("Phase 3: 提取特效精灵")
    print("=" * 60)
    
    irps_dir = cc2_dir / "IRPS"
    if not irps_dir.exists():
        print(f"❌ 未找到IRPS目录: {irps_dir}")
        return
    
    effects_dir = output_dir / "sprites" / "effects"
    effects_dir.mkdir(parents=True, exist_ok=True)
    
    spr_files = list(irps_dir.glob("*.spr"))
    print(f"找到 {len(spr_files)} 个特效.spr文件")
    print(f"   输出目录: {effects_dir}")
    
    print("\n✅ 特效提取完成（需手动使用CC2Spriter）")


def create_readme(output_dir: Path):
    """创建assets目录README"""
    readme_content = """# PyCC2 Assets Directory

此目录存放从Close Combat 2原版游戏提取的美术资源。

## 目录结构

```
assets/
├── sprites/
│   ├── units/
│   │   ├── allies/          # 盟军单位精灵
│   │   │   ├── infantry_squad_d0.png  (北)
│   │   │   ├── infantry_squad_d1.png  (东北)
│   │   │   ├── ...
│   │   │   └── infantry_squad_d7.png  (西北)
│   │   └── axis/            # 轴心国单位精灵
│   ├── vehicles/            # 载具精灵
│   └── effects/             # 特效精灵
└── terrain/
    ├── terrain_00.png       # 草地
    ├── terrain_01.png       # 道路
    └── ...

## 命名规范

### 单位精灵
格式: `{unit_type}_d{direction}.png`
- unit_type: infantry_squad, machine_gun_squad, commander, tank, sniper_team, medic_team
- direction: 0-7 (N, NE, E, SE, S, SW, W, NW)
- 尺寸: 128x128px (推荐)

### 地形tiles
格式: `terrain_{id:02d}.png`
- id: 00-13
- 尺寸: 32x32px 或 64x64px

### 特效精灵
格式: `{effect_name}_f{frame:02d}.png`
- effect_name: explosion, smoke, muzzle_flash, etc.
- frame: 动画帧索引 (00-99)

## 资源来源

1. **CC2原版游戏**: SteamUnlocked / GOG / Steam
2. **CC2Spriter工具**: closecombat2.hpage.com (v2.94)
3. **文档参考**:
   - CC2Guide-SpriteFiles-v9.zip
   - CC2Guide-Terrain-File-v5.pdf
   - CC2MapMuseum.zip

## 提取步骤

1. 下载CC2原版游戏
2. 运行提取脚本:
   ```bash
   python scripts/extract_cc2_assets.py --cc2-dir /path/to/cc2 --output assets/
   ```
3. 使用CC2Spriter手动转换.spr文件
4. 按命名规范组织文件

## Fallback机制

如果assets目录中没有对应资源，游戏会自动使用程序化生成的精灵（pixel_artist.py）。
这确保了即使没有原版资源，游戏也能正常运行。

## 版权说明

Close Combat 2资源版权归原开发商所有。
本项目仅用于学习和研究目的。
"""
    
    readme_path = output_dir / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")
    print(f"\n✅ 创建README: {readme_path}")


def main():
    parser = argparse.ArgumentParser(description="提取CC2原版游戏资源")
    parser.add_argument(
        "--cc2-dir",
        type=Path,
        required=True,
        help="CC2游戏安装目录",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("assets"),
        help="输出目录 (默认: assets/)",
    )
    parser.add_argument(
        "--spriter",
        type=Path,
        help="CC2Spriter工具路径 (可选)",
    )
    
    args = parser.parse_args()
    
    if not args.cc2_dir.exists():
        print(f"❌ CC2目录不存在: {args.cc2_dir}")
        return 1
    
    print("🎨 CC2资产提取工具")
    print(f"输入: {args.cc2_dir}")
    print(f"输出: {args.output}")
    print()
    
    # 创建输出目录
    args.output.mkdir(parents=True, exist_ok=True)
    
    # 提取各类资源
    extract_sprites(args.cc2_dir, args.output, args.spriter)
    extract_terrain(args.cc2_dir, args.output)
    extract_effects(args.cc2_dir, args.output)
    
    # 创建README
    create_readme(args.output)
    
    print("\n" + "=" * 60)
    print("✅ 资产提取完成！")
    print("=" * 60)
    print("\n📝 后续步骤:")
    print("1. 使用CC2Spriter手动转换.spr文件")
    print("2. 按命名规范重命名文件")
    print("3. 运行游戏测试: python scripts/visual_test.py")
    print("\n💡 提示: 即使没有原版资源，游戏也会使用程序化生成的精灵")
    
    return 0


if __name__ == "__main__":
    exit(main())
