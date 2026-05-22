#!/usr/bin/env python3
"""测试PNG精灵加载"""

import sys
from pathlib import Path

# 添加src到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import pygame
pygame.init()

from pycc2.presentation.rendering.asset_loader import AssetLoader

def main():
    print("=" * 60)
    print("测试PNG精灵加载")
    print("=" * 60)
    
    loader = AssetLoader()
    print(f"\n📁 Assets目录: {loader.assets_dir}")
    print(f"   存在: {loader.assets_dir.exists()}")
    
    # 检查精灵文件
    sprites_dir = loader.assets_dir / "sprites" / "units"
    print(f"\n📁 Sprites目录: {sprites_dir}")
    print(f"   存在: {sprites_dir.exists()}")
    
    if sprites_dir.exists():
        allies_dir = sprites_dir / "allies"
        axis_dir = sprites_dir / "axis"
        print(f"\n   盟军目录: {allies_dir.exists()}")
        if allies_dir.exists():
            files = list(allies_dir.glob("*.png"))
            print(f"   盟军PNG文件: {len(files)}个")
            for f in files[:5]:
                print(f"     - {f.name}")
        
        print(f"\n   轴心国目录: {axis_dir.exists()}")
        if axis_dir.exists():
            files = list(axis_dir.glob("*.png"))
            print(f"   轴心国PNG文件: {len(files)}个")
            for f in files[:5]:
                print(f"     - {f.name}")
    
    # 测试加载
    print("\n" + "=" * 60)
    print("测试加载单位精灵")
    print("=" * 60)
    
    test_cases = [
        ("allies", "INFANTRY_SQUAD", 0),
        ("allies", "MACHINE_GUN_SQUAD", 0),
        ("allies", "COMMANDER", 0),
        ("allies", "TANK", 0),
        ("axis", "INFANTRY_SQUAD", 0),
    ]
    
    for faction, unit_type, direction in test_cases:
        print(f"\n测试: {faction}/{unit_type}/d{direction}")
        sprite = loader.load_unit_sprite(faction, unit_type, direction, size=128)
        if sprite:
            print(f"  ✅ 加载成功: {sprite.get_width()}x{sprite.get_height()}")
        else:
            print(f"  ❌ 加载失败")
    
    # 缓存统计
    stats = loader.get_cache_stats()
    print("\n" + "=" * 60)
    print(f"缓存统计: {stats}")
    print("=" * 60)

if __name__ == "__main__":
    main()
