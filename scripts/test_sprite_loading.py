#!/usr/bin/env python3
"""
测试精灵加载功能
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_sprite_loading():
    """测试精灵是否被正确加载"""
    print("=" * 60)
    print("测试精灵加载功能")
    print("=" * 60)
    
    try:
        from pycc2.presentation.rendering.asset_loader import AssetLoader
        
        # 初始化AssetLoader
        loader = AssetLoader()
        print(f"\n✅ AssetLoader初始化成功")
        print(f"   Assets目录: {loader.assets_dir}")
        
        # 测试加载盟军步兵
        print("\n测试加载盟军单位精灵:")
        for unit_type in ["INFANTRY_SQUAD", "MACHINE_GUN_SQUAD", "COMMANDER", "TANK"]:
            sprite = loader.load_unit_sprite(
                faction="allies",
                unit_type=unit_type,
                direction=0,
                size=128
            )
            if sprite:
                print(f"  ✅ {unit_type}: 加载成功 ({sprite.get_width()}x{sprite.get_height()})")
            else:
                print(f"  ❌ {unit_type}: 加载失败（将使用程序化生成）")
        
        # 测试加载轴心国单位精灵
        print("\n测试加载轴心国单位精灵:")
        for unit_type in ["INFANTRY_SQUAD", "MACHINE_GUN_SQUAD", "COMMANDER", "TANK"]:
            sprite = loader.load_unit_sprite(
                faction="axis",
                unit_type=unit_type,
                direction=0,
                size=128
            )
            if sprite:
                print(f"  ✅ {unit_type}: 加载成功 ({sprite.get_width()}x{sprite.get_height()})")
            else:
                print(f"  ❌ {unit_type}: 加载失败（将使用程序化生成）")
        
        # 获取缓存统计
        stats = loader.get_cache_stats()
        print(f"\n缓存统计:")
        print(f"  精灵缓存: {stats['sprites']} 个")
        print(f"  地形缓存: {stats['terrain']} 个")
        print(f"  总计: {stats['total']} 个")
        
        if stats['sprites'] > 0:
            print(f"\n🎉 成功！已加载 {stats['sprites']} 个精灵到缓存")
            print("\n精灵加载功能正常工作！")
            print("游戏应该会使用这些PNG精灵而不是程序化生成的精灵。")
            return True
        else:
            print("\n⚠️  警告：没有精灵被加载到缓存")
            print("可能的原因：")
            print("  1. 精灵文件路径不正确")
            print("  2. 精灵文件命名不匹配")
            print("  3. 文件权限问题")
            return False
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sprite_renderer_integration():
    """测试SpriteRenderer是否使用AssetLoader"""
    print("\n" + "=" * 60)
    print("测试SpriteRenderer集成")
    print("=" * 60)
    
    try:
        import pygame
        pygame.init()
        
        from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer
        from pycc2.presentation.rendering.display_config import DisplayConfig
        
        # 创建渲染器
        config = DisplayConfig()
        renderer = SpriteRenderer(config)
        
        print(f"\n✅ SpriteRenderer初始化成功")
        print(f"   TILE_SIZE: {renderer.TILE_SIZE}")
        print(f"   SPRITE_SIZE: {renderer.SPRITE_SIZE}")
        
        # 检查是否有AssetLoader
        if hasattr(renderer, '_asset_loader'):
            print(f"   ✅ AssetLoader已集成")
            
            # 检查精灵缓存
            cache_size = len(renderer._sprite_cache)
            print(f"   精灵缓存大小: {cache_size} 个")
            
            # 列出一些缓存的精灵
            if cache_size > 0:
                print(f"\n   缓存的精灵示例:")
                for i, key in enumerate(list(renderer._sprite_cache.keys())[:5]):
                    sprite = renderer._sprite_cache[key]
                    print(f"     {i+1}. {key}: {sprite.get_width()}x{sprite.get_height()}")
                
                if cache_size > 5:
                    print(f"     ... 还有 {cache_size - 5} 个精灵")
            
            return True
        else:
            print(f"   ❌ AssetLoader未集成")
            return False
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "🎨" * 30)
    print("PyCC2 精灵加载功能测试")
    print("🎨" * 30 + "\n")
    
    results = []
    
    # 测试1: AssetLoader
    results.append(("AssetLoader功能", test_sprite_loading()))
    
    # 测试2: SpriteRenderer集成
    results.append(("SpriteRenderer集成", test_sprite_renderer_integration()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！精灵加载功能正常工作！")
        print("\n现在运行游戏应该会看到:")
        print("  1. 使用PNG精灵而不是程序化生成的圆点")
        print("  2. 更清晰、更详细的单位图像")
        print("  3. 符合CC2风格的视觉效果")
        print("\n运行游戏测试:")
        print("  python -m pycc2.main")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        print("\n可能需要:")
        print("  1. 检查精灵文件是否存在")
        print("  2. 检查文件命名是否正确")
        print("  3. 检查文件权限")
        return 1


if __name__ == "__main__":
    sys.exit(main())
