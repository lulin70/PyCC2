#!/usr/bin/env python3
"""
测试脚本：验证PyCC2的BUG修复
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_position_component_fix():
    """测试1: 验证PositionComponent参数修复"""
    print("=" * 60)
    print("测试1: PositionComponent参数修复")
    print("=" * 60)
    
    from pycc2.domain.components.position_component import PositionComponent
    from pycc2.domain.value_objects.tile_coord import TileCoord
    from pycc2.domain.value_objects.vec2 import Vec2
    
    # 测试正确的参数名
    try:
        pos = PositionComponent(
            tile_coord=TileCoord(5, 10),
            pixel_offset=Vec2(12.5, 8.3),  # 正确参数名
            facing_rad=1.57,
        )
        print(f"✅ PositionComponent创建成功")
        print(f"   tile_coord: ({pos.tile_coord.x}, {pos.tile_coord.y})")
        print(f"   pixel_offset: ({pos.pixel_offset.x}, {pos.pixel_offset.y})")
        print(f"   pixel_position: ({pos.pixel_position.x}, {pos.pixel_position.y})")
        print(f"   facing_rad: {pos.facing_rad}")
        
        # 验证pixel_position是计算属性
        expected_x = 5 * 48 + 12.5
        expected_y = 10 * 48 + 8.3
        assert abs(pos.pixel_position.x - expected_x) < 0.01, "X坐标计算错误"
        assert abs(pos.pixel_position.y - expected_y) < 0.01, "Y坐标计算错误"
        print(f"✅ pixel_position计算正确: ({expected_x}, {expected_y})")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_save_controller_fix():
    """测试2: 验证save_controller.py中的修复"""
    print("\n" + "=" * 60)
    print("测试2: save_controller.py修复验证")
    print("=" * 60)
    
    try:
        # 读取save_controller.py文件
        save_controller_path = Path(__file__).parent.parent / "src" / "pycc2" / "services" / "save_controller.py"
        content = save_controller_path.read_text()
        
        # 检查是否使用了正确的参数名
        if "pixel_offset=Vec2" in content:
            print("✅ save_controller.py使用正确的参数名: pixel_offset")
            
            # 检查是否移除了错误的pixel_position参数
            if "pixel_position=Vec2" not in content:
                print("✅ 已移除错误的pixel_position参数")
                return True
            else:
                print("⚠️  警告: 仍然存在pixel_position参数")
                return False
        else:
            print("❌ save_controller.py未使用pixel_offset参数")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_game_loop_keys():
    """测试3: 验证game_loop.py中的F5/F9按键处理"""
    print("\n" + "=" * 60)
    print("测试3: game_loop.py F5/F9按键处理")
    print("=" * 60)
    
    try:
        # 读取game_loop.py文件
        game_loop_path = Path(__file__).parent.parent / "src" / "pycc2" / "services" / "game_loop.py"
        content = game_loop_path.read_text()
        
        # 检查F5按键处理
        if "pygame.K_F5" in content and "quick_save" in content:
            print("✅ 找到F5快速保存处理")
        else:
            print("❌ 未找到F5快速保存处理")
            return False
        
        # 检查F9按键处理
        if "pygame.K_F9" in content and "quick_load" in content:
            print("✅ 找到F9快速加载处理")
        else:
            print("❌ 未找到F9快速加载处理")
            return False
        
        # 检查quick_save和quick_load方法
        if "def quick_save" in content and "def quick_load" in content:
            print("✅ quick_save和quick_load方法已定义")
            return True
        else:
            print("❌ quick_save或quick_load方法未定义")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_sprite_assets():
    """测试4: 验证生成的精灵资源"""
    print("\n" + "=" * 60)
    print("测试4: CC2风格精灵资源验证")
    print("=" * 60)
    
    try:
        assets_path = Path(__file__).parent.parent / "assets" / "sprites"
        
        # 检查单位精灵
        unit_types = [
            "units/allies/rifleman.png",
            "units/allies/mg_team.png",
            "units/allies/engineer.png",
            "units/allies/officer.png",
            "units/allies/light_tank.png",
            "units/allies/medium_tank.png",
            "units/allies/heavy_tank.png",
            "units/axis/rifleman.png",
            "units/axis/mg_team.png",
            "units/axis/engineer.png",
            "units/axis/officer.png",
            "units/axis/light_tank.png",
            "units/axis/medium_tank.png",
            "units/axis/heavy_tank.png",
        ]
        
        found_count = 0
        for sprite in unit_types:
            sprite_path = assets_path / sprite
            if sprite_path.exists():
                found_count += 1
        
        print(f"✅ 找到 {found_count}/{len(unit_types)} 个单位精灵")
        
        # 检查建筑精灵
        building_types = ["buildings/house.png", "buildings/barn.png", "buildings/church.png"]
        building_count = sum(1 for b in building_types if (assets_path / b).exists())
        print(f"✅ 找到 {building_count}/{len(building_types)} 个建筑精灵")
        
        # 检查载具精灵
        vehicle_types = ["units/vehicles/jeep.png", "units/vehicles/halftrack.png"]
        vehicle_count = sum(1 for v in vehicle_types if (assets_path / v).exists())
        print(f"✅ 找到 {vehicle_count}/{len(vehicle_types)} 个载具精灵")
        
        total_expected = len(unit_types) + len(building_types) + len(vehicle_types)
        total_found = found_count + building_count + vehicle_count
        
        print(f"\n总计: {total_found}/{total_expected} 个精灵文件")
        
        return total_found >= 15  # 至少要有15个精灵
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "🔧" * 30)
    print("PyCC2 BUG修复验证测试")
    print("🔧" * 30 + "\n")
    
    results = []
    
    # 运行所有测试
    results.append(("PositionComponent参数修复", test_position_component_fix()))
    results.append(("save_controller.py修复", test_save_controller_fix()))
    results.append(("F5/F9按键处理", test_game_loop_keys()))
    results.append(("CC2精灵资源", test_sprite_assets()))
    
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
        print("\n🎉 所有测试通过！BUG修复成功！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，需要进一步检查")
        return 1


if __name__ == "__main__":
    sys.exit(main())
