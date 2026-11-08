#!/usr/bin/env python3
"""
PyCC2 测试精灵生成器
快速生成32x32像素的测试精灵，用于验证代码集成流程
"""

from pathlib import Path

from PIL import Image, ImageDraw


def create_test_sprite(output_path: Path, name: str, color: tuple, shape: str = "circle"):
    """创建一个32x32的测试精灵

    Args:
        output_path: 输出目录
        name: 文件名（不含扩展名）
        color: RGB颜色元组
        shape: 形状类型 ("circle", "square", "triangle")
    """
    # 创建32x32透明背景图像
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 黑色轮廓
    outline_color = (0, 0, 0, 255)
    outline_width = 2

    if shape == "circle":
        # 圆形 (步兵单位)
        draw.ellipse([4, 4, 28, 28], fill=color, outline=outline_color, width=outline_width)
    elif shape == "square":
        # 方形 (载具)
        draw.rectangle([4, 4, 28, 28], fill=color, outline=outline_color, width=outline_width)
    elif shape == "triangle":
        # 三角形 (特殊单位)
        draw.polygon([(16, 4), (28, 28), (4, 28)], fill=color, outline=outline_color, width=outline_width)

    # 保存
    output_file = output_path / f"{name}.png"
    img.save(output_file)
    print(f"✅ Created: {output_file}")

def generate_test_sprites():
    """生成完整的测试精灵集 - 覆盖20个核心单位"""
    # 创建输出目录
    base_dir = Path(__file__).parent
    output_dir = base_dir / "generated"
    output_dir.mkdir(exist_ok=True)

    print("🎨 Generating PyCC2 Cartoon Sprites (20 Core Units)")
    print(f"📂 Output directory: {output_dir}")
    print("=" * 60)
    print()

    # 颜色定义
    ALLY_INFANTRY = (107, 142, 35, 255)      # 军绿色
    ALLY_VEHICLE = (79, 111, 82, 255)        # 深绿色
    ALLY_SUPPORT = (139, 157, 89, 255)       # 浅绿色
    AXIS_INFANTRY = (220, 20, 60, 255)       # 深红色
    AXIS_VEHICLE = (178, 34, 34, 255)        # 火砖红
    SPECIAL = (255, 215, 0, 255)             # 金色
    UI_SELECT = (255, 255, 0, 255)           # 黄色
    UI_MOVE = (0, 255, 0, 255)               # 绿色

    sprite_count = 0

    # === TIER 1: 盟军核心步兵 (圆形) ===
    print("👤 TIER 1: Allied Infantry (8 units)")
    create_test_sprite(output_dir, "rifleman", ALLY_INFANTRY, "circle")
    create_test_sprite(output_dir, "mg_team", ALLY_INFANTRY, "circle")
    create_test_sprite(output_dir, "officer", ALLY_SUPPORT, "circle")
    create_test_sprite(output_dir, "engineer", ALLY_SUPPORT, "circle")
    create_test_sprite(output_dir, "sniper", ALLY_SUPPORT, "circle")
    create_test_sprite(output_dir, "medic", ALLY_SUPPORT, "circle")
    create_test_sprite(output_dir, "at_team", ALLY_SUPPORT, "circle")
    create_test_sprite(output_dir, "mortar_team", ALLY_SUPPORT, "circle")
    sprite_count += 8

    # === TIER 2: 盟军载具 (方形) ===
    print("\n🚗 TIER 2: Allied Vehicles (4 units)")
    create_test_sprite(output_dir, "medium_tank", ALLY_VEHICLE, "square")
    create_test_sprite(output_dir, "light_tank", ALLY_VEHICLE, "square")
    create_test_sprite(output_dir, "heavy_tank", ALLY_VEHICLE, "square")
    create_test_sprite(output_dir, "halftrack", ALLY_VEHICLE, "square")
    sprite_count += 4

    # === TIER 3: 轴心国单位 (红色) ===
    print("\n⚔️  TIER 3: Axis Units (4 units)")
    create_test_sprite(output_dir, "axis_rifleman", AXIS_INFANTRY, "circle")
    create_test_sprite(output_dir, "axis_mg_team", AXIS_INFANTRY, "circle")
    create_test_sprite(output_dir, "axis_tank", AXIS_VEHICLE, "square")
    create_test_sprite(output_dir, "axis_officer", AXIS_INFANTRY, "circle")
    sprite_count += 4

    # === TIER 4: 特殊单位 (三角形/金色) ===
    print("\n⭐ TIER 4: Special Units (2 units)")
    create_test_sprite(output_dir, "commander", SPECIAL, "triangle")
    create_test_sprite(output_dir, "scout", SPECIAL, "triangle")
    sprite_count += 2

    # === UI元素 ===
    print("\n🎯 UI Elements (2 units)")
    create_test_sprite(output_dir, "selection_box", UI_SELECT, "square")
    create_test_sprite(output_dir, "movement_arrow", UI_MOVE, "triangle")
    sprite_count += 2

    print()
    print("=" * 60)
    print("✅ PyCC2 Cartoon Sprite Generation Complete!")
    print(f"📁 Total sprites: {sprite_count}")
    print("📊 Breakdown:")
    print("   - Allied Infantry: 8")
    print("   - Allied Vehicles: 4")
    print("   - Axis Units: 4")
    print("   - Special: 2")
    print("   - UI Elements: 2")
    print(f"📂 Location: {output_dir.absolute()}")
    print()
    print("🚀 Next Steps:")
    print("1. ✅ All 20 core units generated")
    print("2. Run integration test: pytest tests/integration/test_cartoon_sprite_*.py")
    print("3. Evaluate Kenney/Stonebit professional assets")
    print("=" * 60)

if __name__ == "__main__":
    try:
        generate_test_sprites()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
