#!/usr/bin/env python3
"""
测试defeat画面和R键崩溃的BUG修复
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_victory_condition_delay():
    """测试1: 验证胜利条件评估延迟"""
    print("=" * 60)
    print("测试1: 胜利条件评估延迟（防止刚开始就defeat）")
    print("=" * 60)
    
    try:
        game_loop_path = Path(__file__).parent.parent / "src" / "pycc2" / "services" / "game_loop.py"
        content = game_loop_path.read_text()
        
        # 检查是否添加了tick >= 300的保护
        if "self.state.tick >= 300" in content:
            print("✅ 添加了最小战斗时间保护（300 ticks = 5秒）")
        else:
            print("❌ 未添加最小战斗时间保护")
            return False
        
        # 检查注释
        if "防止战斗刚开始就判定失败" in content:
            print("✅ 添加了说明注释")
        else:
            print("⚠️  未添加说明注释（非关键）")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_r_key_crash_fix():
    """测试2: 验证R键崩溃修复"""
    print("\n" + "=" * 60)
    print("测试2: R键崩溃修复")
    print("=" * 60)
    
    try:
        input_router_path = Path(__file__).parent.parent / "src" / "pycc2" / "presentation" / "input" / "input_router.py"
        content = input_router_path.read_text()
        
        # 检查是否移除了错误的show_post_battle赋值
        if "self.show_post_battle = False" in content:
            print("❌ 仍然存在错误的show_post_battle赋值")
            return False
        else:
            print("✅ 已移除错误的show_post_battle赋值")
        
        # 检查是否保留了running = False
        if "self.game_state.running = False" in content:
            print("✅ 保留了正确的running = False逻辑")
        else:
            print("❌ 缺少running = False逻辑")
            return False
        
        # 检查注释
        if "按ESC或R键退出战斗结果画面" in content:
            print("✅ 添加了说明注释")
        else:
            print("⚠️  未添加说明注释（非关键）")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "🔧" * 30)
    print("PyCC2 Defeat画面和R键崩溃BUG修复验证")
    print("🔧" * 30 + "\n")
    
    results = []
    
    # 运行所有测试
    results.append(("胜利条件评估延迟", test_victory_condition_delay()))
    results.append(("R键崩溃修复", test_r_key_crash_fix()))
    
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
        print("\n🎉 所有测试通过！Defeat和R键BUG已修复！")
        print("\n修复内容:")
        print("1. ✅ 防止战斗刚开始就显示defeat - 添加300 ticks延迟")
        print("2. ✅ 修复R键崩溃 - 移除错误的状态修改")
        print("\n请运行游戏测试:")
        print("  python -m pycc2.main")
        print("\n测试步骤:")
        print("  1. 进入战斗，确认不会立即显示defeat")
        print("  2. 等待战斗结束（或按ESC退出）")
        print("  3. 在结果画面按R键，确认不崩溃")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
