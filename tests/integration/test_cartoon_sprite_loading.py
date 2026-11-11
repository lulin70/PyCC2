#!/usr/bin/env python3
"""
测试新生成的卡通精灵是否能被PyCC2正确加载和渲染
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

import pygame


def test_sprite_loading():
    """测试精灵加载"""
    print("=" * 60)
    print("🎨 PyCC2 Cartoon Sprite Integration Test")
    print("=" * 60)
    print()

    # 初始化Pygame（必须先初始化才能加载图像）
    pygame.init()
    pygame.display.set_mode((1, 1))  # 最小窗口

    # 创建AssetLoader
    assets_dir = project_root / "assets"
    # Note: loader not used here, direct file loading for test

    print(f"📂 Assets directory: {assets_dir}")
    print(f"📂 Sprites directory: {assets_dir / 'sprites'}")
    print()

    # 测试加载新生成的精灵
    test_sprites = [
        ("rifleman", "INFANTRY_SQUAD", "allies"),
        ("mg_team", "MACHINE_GUN_SQUAD", "allies"),
        ("officer", "OFFICER", "allies"),
        ("sherman_tank", "SHERMAN_TANK", "allies"),
        ("halftrack", "HALFTRACK", "allies"),
        ("jeep", "JEEP", "allies"),
    ]

    success_count = 0
    fail_count = 0

    print("🔍 Testing sprite loading...")
    print()

    for sprite_name, unit_type, faction in test_sprites:
        # 尝试从minimal_test/generated目录加载
        sprite_path = assets_dir / "sprites" / "minimal_test" / "generated" / f"{sprite_name}.png"

        if sprite_path.exists():
            try:
                surface = pygame.image.load(str(sprite_path))
                w, h = surface.get_size()

                if w == 32 and h == 32:
                    print(f"  ✅ {sprite_name:20s} → {w}x{h} pixels → PASS")
                    success_count += 1
                else:
                    print(
                        f"  ⚠️  {sprite_name:20s} → {w}x{h} pixels (expected 32x32) → SIZE_MISMATCH"
                    )
                    fail_count += 1
            except Exception as e:
                print(f"  ❌ {sprite_name:20s} → LOAD_ERROR: {e}")
                fail_count += 1
        else:
            print(f"  ❌ {sprite_name:20s} → FILE_NOT_FOUND: {sprite_path}")
            fail_count += 1

    print()
    print("=" * 60)
    print(f"📊 Test Results: {success_count} passed, {fail_count} failed")

    if fail_count == 0:
        print("✅ All sprites loaded successfully!")
        print()
        print("🚀 Next steps:")
        print("1. Update AssetLoader to use minimal_test/generated/ directory")
        print("2. Integrate into sprite renderer")
        print("3. Run full E2E test")
    else:
        print(f"⚠️  {fail_count} sprites failed to load")
        print("Please check the error messages above")

    print("=" * 60)

    pygame.quit()
    return fail_count == 0


if __name__ == "__main__":
    success = test_sprite_loading()
    sys.exit(0 if success else 1)
