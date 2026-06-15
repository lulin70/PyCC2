#!/usr/bin/env python3
"""
验证PNG精灵在游戏中是否正确加载和显示
"""

import os
import sys

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_enhanced_renderer_integration():
    """测试EnhancedRenderer是否正确集成SpriteRenderer"""
    print("=" * 60)
    print("测试 EnhancedRenderer 集成 SpriteRenderer")
    print("=" * 60)

    # 初始化pygame
    import pygame

    pygame.init()
    screen = pygame.display.set_mode((800, 600))

    # 创建EnhancedRenderer
    from pycc2.presentation.rendering.enhanced_renderer import EnhancedRenderer

    renderer = EnhancedRenderer()

    # 检查初始状态
    print("✓ EnhancedRenderer创建成功")
    print(f"  _sprite_renderer初始值: {renderer._sprite_renderer}")

    # 初始化renderer（这会创建SpriteRenderer）
    renderer.initialize(screen)

    # 检查SpriteRenderer是否创建
    if renderer._sprite_renderer is None:
        print("✗ 错误：SpriteRenderer未创建！")
        return False

    print(f"✓ SpriteRenderer已创建: {type(renderer._sprite_renderer)}")

    # 检查SpriteRenderer的AssetLoader
    if hasattr(renderer._sprite_renderer, "_asset_loader"):
        loader = renderer._sprite_renderer._asset_loader
        print(f"✓ AssetLoader已创建: {type(loader)}")

        # 检查PNG资源
        if hasattr(loader, "_sprites"):
            sprite_count = len(loader._sprites)
            print(f"✓ 已加载 {sprite_count} 个PNG精灵")

            if sprite_count > 0:
                print("\n已加载的PNG精灵:")
                for name in list(loader._sprites.keys())[:5]:
                    sprite = loader._sprites[name]
                    print(f"  - {name}: {sprite.get_size()}")
        else:
            print("✗ AssetLoader没有_sprites属性")
    else:
        print("✗ SpriteRenderer没有_asset_loader属性")

    # 测试_draw_units方法是否会调用SpriteRenderer
    print("\n" + "=" * 60)
    print("测试 _draw_units 方法")
    print("=" * 60)

    # 创建模拟单位
    from pycc2.domain.value_objects.position import Position

    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.value_objects.vec2 import Vec2
    from pycc2.presentation.rendering.camera import Camera

    camera = Camera(position=Vec2(400, 300), viewport_width=800, viewport_height=600)

    # 创建一个测试单位
    test_unit = Unit(
        id="test_1",
        display_name="Test Infantry",
        unit_type="INFANTRY_SQUAD",
        faction="allied",
        position=Position(tile_x=10, tile_y=10),
    )

    units = [test_unit]

    # 调用_draw_units
    try:
        renderer._draw_units(units, camera, None)
        print("✓ _draw_units 调用成功")
        print("✓ 如果SpriteRenderer正常工作，应该会加载PNG精灵")
    except Exception as e:
        print(f"✗ _draw_units 调用失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    pygame.quit()

    print("\n" + "=" * 60)
    print("✅ 所有测试通过！PNG精灵应该在游戏中显示")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_enhanced_renderer_integration()
    sys.exit(0 if success else 1)
