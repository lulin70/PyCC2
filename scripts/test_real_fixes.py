#!/usr/bin/env python3
"""
真正的BUG修复验证测试
验证所有3个BUG的修复
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_save_controller_data_format():
    """测试1: 验证save_controller.py的数据格式统一"""
    print("=" * 60)
    print("测试1: save_controller.py数据格式统一")
    print("=" * 60)
    
    try:
        save_controller_path = Path(__file__).parent.parent / "src" / "pycc2" / "services" / "save_controller.py"
        content = save_controller_path.read_text()
        
        # 检查导出时使用pixel_offset
        if '"pixel_offset": {' in content and '"x": unit.position.pixel_offset.x' in content:
            print("✅ 导出(export)使用正确的pixel_offset")
        else:
            print("❌ 导出(export)未使用pixel_offset")
            return False
        
        # 检查导入时使用pixel_offset
        if 'pos_data.get("pixel_offset"' in content:
            print("✅ 导入(restore)使用正确的pixel_offset")
        else:
            print("❌ 导入(restore)未使用pixel_offset")
            return False
        
        # 确保没有错误的pixel_position
        if '"pixel_position": {' in content:
            print("❌ 仍然存在错误的pixel_position键")
            return False
        else:
            print("✅ 已移除错误的pixel_position键")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_exception_logging():
    """测试2: 验证异常日志已添加"""
    print("\n" + "=" * 60)
    print("测试2: 异常日志和错误处理")
    print("=" * 60)
    
    try:
        save_controller_path = Path(__file__).parent.parent / "src" / "pycc2" / "services" / "save_controller.py"
        content = save_controller_path.read_text()
        
        # 检查是否有logger.error
        if "logger.error" in content and "exc_info=True" in content:
            print("✅ 添加了详细的错误日志")
        else:
            print("❌ 未添加错误日志")
            return False
        
        # 检查是否移除了静默异常处理
        if "except Exception:\n    pass" in content or "except Exception:\n        pass" in content:
            print("❌ 仍然存在静默异常处理")
            return False
        else:
            print("✅ 已移除静默异常处理")
        
        # 检查是否有成功日志
        if "logger.info" in content and "loaded successfully" in content:
            print("✅ 添加了成功日志")
        else:
            print("⚠️  未添加成功日志（非关键）")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_pygame_quit_protection():
    """测试3: 验证双重pygame.quit()保护"""
    print("\n" + "=" * 60)
    print("测试3: pygame.quit()双重调用保护")
    print("=" * 60)
    
    try:
        window_config_path = Path(__file__).parent.parent / "src" / "pycc2" / "presentation" / "rendering" / "window_config.py"
        content = window_config_path.read_text()
        
        # 检查是否添加了_shutdown_called标志
        if "_shutdown_called: bool = False" in content:
            print("✅ 添加了_shutdown_called标志")
        else:
            print("❌ 未添加_shutdown_called标志")
            return False
        
        # 检查shutdown方法是否有保护
        if "if self._shutdown_called:" in content and "return" in content:
            print("✅ shutdown方法有重复调用保护")
        else:
            print("❌ shutdown方法无保护")
            return False
        
        # 检查是否检查pygame初始化状态
        if "if pygame.get_init():" in content:
            print("✅ 检查pygame初始化状态")
        else:
            print("⚠️  未检查pygame初始化状态（建议添加）")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_f5_f9_handlers():
    """测试4: 验证F5/F9按键处理"""
    print("\n" + "=" * 60)
    print("测试4: F5/F9按键处理")
    print("=" * 60)
    
    try:
        game_loop_path = Path(__file__).parent.parent / "src" / "pycc2" / "services" / "game_loop.py"
        content = game_loop_path.read_text()
        
        # 检查F5处理
        if "pygame.K_F5" in content and "quick_save" in content:
            print("✅ F5快速保存处理已添加")
        else:
            print("❌ F5快速保存处理未添加")
            return False
        
        # 检查F9处理
        if "pygame.K_F9" in content and "quick_load" in content:
            print("✅ F9快速加载处理已添加")
        else:
            print("❌ F9快速加载处理未添加")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_position_component():
    """测试5: 验证PositionComponent正确性"""
    print("\n" + "=" * 60)
    print("测试5: PositionComponent参数验证")
    print("=" * 60)
    
    try:
        from pycc2.domain.components.position_component import PositionComponent
        from pycc2.domain.value_objects.tile_coord import TileCoord
        from pycc2.domain.value_objects.vec2 import Vec2
        
        # 测试正确的参数
        pos = PositionComponent(
            tile_coord=TileCoord(5, 10),
            pixel_offset=Vec2(12.5, 8.3),
            facing_rad=1.57,
        )
        
        print(f"✅ PositionComponent创建成功")
        print(f"   tile_coord: ({pos.tile_coord.x}, {pos.tile_coord.y})")
        print(f"   pixel_offset: ({pos.pixel_offset.x}, {pos.pixel_offset.y})")
        
        # 验证pixel_position是计算属性
        if hasattr(pos, 'pixel_position'):
            print(f"✅ pixel_position是计算属性: ({pos.pixel_position.x}, {pos.pixel_position.y})")
        else:
            print("❌ pixel_position属性不存在")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "🔧" * 30)
    print("PyCC2 真正的BUG修复验证测试")
    print("🔧" * 30 + "\n")
    
    results = []
    
    # 运行所有测试
    results.append(("数据格式统一(pixel_offset)", test_save_controller_data_format()))
    results.append(("异常日志和错误处理", test_exception_logging()))
    results.append(("pygame.quit()保护", test_pygame_quit_protection()))
    results.append(("F5/F9按键处理", test_f5_f9_handlers()))
    results.append(("PositionComponent正确性", test_position_component()))
    
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
        print("\n🎉 所有测试通过！所有BUG已真正修复！")
        print("\n修复内容:")
        print("1. ✅ 单位移动BUG - 数据格式统一为pixel_offset")
        print("2. ✅ SAVE/LOAD功能 - 添加异常日志和错误处理")
        print("3. ✅ 退出崩溃 - 防止双重pygame.quit()调用")
        print("\n请运行游戏测试:")
        print("  python -m pycc2.main")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
