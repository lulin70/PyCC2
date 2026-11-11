#!/usr/bin/env python3
"""
视觉质量对比测试：基础版 vs 增强版精灵
生成并排对比截图，实际判断视觉提升效果
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

import pygame


def create_comparison_image():
    """创建基础版vs增强版的对比图"""
    pygame.init()

    # 创建画布（两列对比）
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("PyCC2 Sprite Quality Comparison")

    # 字体
    title_font = pygame.font.Font(None, 36)
    label_font = pygame.font.Font(None, 24)

    # 背景
    screen.fill((240, 240, 240))

    # 标题
    title = title_font.render("Sprite Quality Comparison", True, (0, 0, 0))
    screen.blit(title, (200, 20))

    # 列标题
    basic_title = label_font.render("Basic (Current)", True, (0, 0, 0))
    enhanced_title = label_font.render("Enhanced (New)", True, (0, 0, 0))
    screen.blit(basic_title, (150, 70))
    screen.blit(enhanced_title, (500, 70))

    # 加载并显示精灵对
    sprite_pairs = [
        ("rifleman", "Infantry"),
        ("mg_team", "MG Team"),
        ("medium_tank", "Tank"),
        ("axis_rifleman", "Enemy"),
        ("commander", "Commander"),
    ]

    y_offset = 120
    basic_dir = project_root / "assets/sprites/minimal_test/generated"
    enhanced_dir = project_root / "assets/sprites/minimal_test/generated_enhanced"

    comparison_results = []

    for i, (sprite_name, label) in enumerate(sprite_pairs):
        # 标签
        label_surf = label_font.render(label, True, (80, 80, 80))
        screen.blit(label_surf, (20, y_offset + 20))

        # 基础版
        basic_path = basic_dir / f"{sprite_name}.png"
        if basic_path.exists():
            basic_sprite = pygame.image.load(str(basic_path))
            # 放大4倍显示
            basic_scaled = pygame.transform.scale(basic_sprite, (128, 128))
            screen.blit(basic_scaled, (150, y_offset))
        else:
            print(f"⚠️  Missing: {basic_path}")

        # 增强版
        enhanced_path = enhanced_dir / f"{sprite_name}_enhanced.png"
        if enhanced_path.exists():
            enhanced_sprite = pygame.image.load(str(enhanced_path))
            enhanced_scaled = pygame.transform.scale(enhanced_sprite, (128, 128))
            screen.blit(enhanced_scaled, (500, y_offset))
        else:
            print(f"⚠️  Missing: {enhanced_path}")

        # 对比判断（基于文件大小和像素复杂度粗略估计）
        if basic_path.exists() and enhanced_path.exists():
            basic_size = basic_path.stat().st_size
            enhanced_size = enhanced_path.stat().st_size
            size_diff = enhanced_size - basic_size

            # 简单判断：增强版应该更大（有更多像素数据）
            if size_diff > 50:
                comparison_results.append(
                    {
                        "sprite": sprite_name,
                        "label": label,
                        "verdict": "ENHANCED",
                        "size_diff": size_diff,
                    }
                )
            else:
                comparison_results.append(
                    {
                        "sprite": sprite_name,
                        "label": label,
                        "verdict": "NO_DIFF",
                        "size_diff": size_diff,
                    }
                )

        y_offset += 100

    # 更新显示
    pygame.display.flip()

    # 保存截图
    screenshot_path = project_root / "tests/integration/sprite_comparison.png"
    pygame.image.save(screen, str(screenshot_path))
    print(f"\n📸 Comparison screenshot saved: {screenshot_path}")

    # 等待3秒
    pygame.time.wait(3000)
    pygame.quit()

    return comparison_results, screenshot_path


def analyze_comparison_results(results):
    """分析对比结果并给出结论"""
    print("\n" + "=" * 60)
    print("VISUAL QUALITY COMPARISON RESULTS")
    print("=" * 60)

    print("\n📊 Individual Sprite Analysis:")
    for r in results:
        status_icon = "✅" if r["verdict"] == "ENHANCED" else "⚠️"
        print(
            f"  {status_icon} {r['label']:15s}: {r['verdict']:10s} (size +{r['size_diff']} bytes)"
        )

    enhanced_count = sum(1 for r in results if r["verdict"] == "ENHANCED")
    total = len(results)

    print("\n📈 Summary:")
    print(f"  • Enhanced: {enhanced_count}/{total} sprites ({enhanced_count * 100 // total}%)")
    print(f"  • No Change: {total - enhanced_count}/{total} sprites")

    # 最终判断
    print("\n🎯 FINAL VERDICT:")
    if enhanced_count >= total * 0.7:
        print("  ✅ SIGNIFICANT IMPROVEMENT - Enhanced version is better")
        print("  → Recommendation: Replace basic sprites with enhanced version")
        return "UPGRADE"
    elif enhanced_count >= total * 0.4:
        print("  ⚠️  MODERATE IMPROVEMENT - Some sprites are better")
        print("  → Recommendation: Selective upgrade for improved sprites only")
        return "PARTIAL"
    else:
        print("  ❌ MINIMAL IMPROVEMENT - Enhancement not worth the complexity")
        print("  → Recommendation: Keep basic sprites, wait for professional assets")
        return "KEEP_BASIC"


def main():
    print("🎨 PyCC2 Sprite Quality Comparison Test")
    print("=" * 60)
    print()

    # 生成对比图
    results, screenshot_path = create_comparison_image()

    # 分析结果
    verdict = analyze_comparison_results(results)

    print("\n" + "=" * 60)
    print("📋 ACTION ITEMS:")
    if verdict == "UPGRADE":
        print("  1. Update AssetLoader to use generated_enhanced/ directory")
        print("  2. Run integration tests")
        print("  3. Update documentation")
    elif verdict == "PARTIAL":
        print("  1. Cherry-pick improved sprites")
        print("  2. Keep basic version for others")
        print("  3. Document the hybrid approach")
    else:
        print("  1. Keep current basic sprites")
        print("  2. Wait for Kenney/professional assets when network available")
        print("  3. Enhancement effort not justified")

    print("\n📸 Visual Evidence:")
    print(f"   Review screenshot: {screenshot_path}")
    print("=" * 60)

    return verdict


if __name__ == "__main__":
    try:
        verdict = main()
        sys.exit(0 if verdict in ["UPGRADE", "PARTIAL"] else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(2)
