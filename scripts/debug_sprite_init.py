#!/usr/bin/env python3
"""调试SpriteRenderer初始化时的精灵生成"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import pygame
pygame.init()
pygame.display.set_mode((800, 600))  # 初始化display

from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer

def main():
    print("=" * 60)
    print("调试SpriteRenderer初始化")
    print("=" * 60)
    
    print("\n创建SpriteRenderer...")
    renderer = SpriteRenderer()
    
    print(f"\n精灵缓存大小: {len(renderer._sprite_cache)}")
    
    # 检查几个关键精灵
    test_keys = [
        "allies_INFANTRY_SQUAD_d0",
        "allies_MACHINE_GUN_SQUAD_d0",
        "allies_COMMANDER_d0",
        "allies_TANK_d0",
        "axis_INFANTRY_SQUAD_d0",
    ]
    
    print("\n检查缓存的精灵:")
    for key in test_keys:
        if key in renderer._sprite_cache:
            sprite = renderer._sprite_cache[key]
            print(f"  ✅ {key}: {sprite.get_width()}x{sprite.get_height()}")
        else:
            print(f"  ❌ {key}: 不存在")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
