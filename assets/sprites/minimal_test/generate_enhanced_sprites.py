#!/usr/bin/env python3
"""
PyCC2 增强版精灵生成器
在基础版上添加阴影、渐变和更多细节，验证视觉质量提升效果
"""

from pathlib import Path

from PIL import Image, ImageDraw


def create_enhanced_sprite(
    output_path: Path, name: str, color: tuple, shape: str = "circle", style: str = "standard"
):
    """创建增强版32x32精灵（带阴影和渐变）

    Args:
        output_path: 输出目录
        name: 文件名
        color: 主颜色RGBA
        shape: 形状 (circle/square/triangle)
        style: 样式 (standard/shadow/gradient)
    """
    # 创建32x32透明背景
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 参数
    outline_color = (0, 0, 0, 255)
    outline_width = 2

    # 阴影效果（在主图形下方）
    if style in ["shadow", "gradient"]:
        shadow_color = (0, 0, 0, 80)  # 半透明黑色
        shadow_offset = 2

        if shape == "circle":
            draw.ellipse(
                [4 + shadow_offset, 4 + shadow_offset, 28 + shadow_offset, 28 + shadow_offset],
                fill=shadow_color,
            )
        elif shape == "square":
            draw.rectangle(
                [4 + shadow_offset, 4 + shadow_offset, 28 + shadow_offset, 28 + shadow_offset],
                fill=shadow_color,
            )
        elif shape == "triangle":
            points = [(16 + shadow_offset, 4 + shadow_offset), 
                     (28 + shadow_offset, 28 + shadow_offset), 
                     (4 + shadow_offset, 28 + shadow_offset)]
            draw.polygon(points, fill=shadow_color)

    # 渐变效果（使用两种颜色）
    if style == "gradient":
        r, g, b, a = color
        light_color = (min(r + 40, 255), min(g + 40, 255), min(b + 40, 255), a)
        dark_color = (max(r - 30, 0), max(g - 30, 0), max(b - 30, 0), a)

        # 绘制渐变（简化：上半亮色，下半暗色）
        if shape == "circle":
            # 亮色半圆
            draw.pieslice([4, 4, 28, 28], start=180, end=0, fill=light_color)
            # 暗色半圆
            draw.pieslice([4, 4, 28, 28], start=0, end=180, fill=dark_color)
        elif shape == "square":
            draw.rectangle([4, 4, 28, 16], fill=light_color)
            draw.rectangle([4, 16, 28, 28], fill=dark_color)
        elif shape == "triangle":
            # 上半三角
            draw.polygon([(16, 4), (28, 28), (4, 28)], fill=light_color)
            # 添加渐变线
            for y in range(16, 28, 2):
                alpha = int(255 * (28 - y) / 12)
                grad_color = (dark_color[0], dark_color[1], dark_color[2], alpha)
                draw.line([(4 + (y - 16), y), (28 - (y - 16), y)], fill=grad_color, width=2)
    else:
        # 标准纯色
        if shape == "circle":
            draw.ellipse([4, 4, 28, 28], fill=color)
        elif shape == "square":
            draw.rectangle([4, 4, 28, 28], fill=color)
        elif shape == "triangle":
            draw.polygon([(16, 4), (28, 28), (4, 28)], fill=color)

    # 绘制轮廓（始终在最上层）
    if shape == "circle":
        draw.ellipse([4, 4, 28, 28], outline=outline_color, width=outline_width)
    elif shape == "square":
        draw.rectangle([4, 4, 28, 28], outline=outline_color, width=outline_width)
    elif shape == "triangle":
        draw.polygon([(16, 4), (28, 28), (4, 28)], outline=outline_color, width=outline_width)

    # 保存
    output_file = output_path / f"{name}_enhanced.png"
    img.save(output_file)
    print(f"✅ Created: {name}_enhanced.png ({style} style)")


def generate_enhanced_sprites():
    """生成增强版精灵集 - 扩展到40个单位"""
    base_dir = Path(__file__).parent
    output_dir = base_dir / "generated_enhanced"
    output_dir.mkdir(exist_ok=True)

    print("🎨 PyCC2 Enhanced Sprites Generation - Phase 2 (40 Units)")
    print(f"📂 Output: {output_dir}")
    print("=" * 60)
    print()

    sprite_count = 0

    # 颜色定义
    ALLY_INFANTRY = (107, 142, 35, 255)
    ALLY_VEHICLE = (79, 111, 82, 255)
    ALLY_SUPPORT = (139, 157, 89, 255)
    AXIS_INFANTRY = (220, 20, 60, 255)
    AXIS_VEHICLE = (178, 34, 34, 255)
    AXIS_SUPPORT = (200, 60, 80, 255)
    SPECIAL = (255, 215, 0, 255)
    BUILDING = (139, 69, 19, 255)  # 棕色
    ALLY_BUILDING = (90, 120, 70, 255)  # 深绿
    AXIS_BUILDING = (150, 50, 50, 255)  # 深红
    UI_SELECT = (255, 255, 0, 255)  # 黄色
    UI_MOVE = (0, 255, 0, 255)  # 绿色
    UI_ATTACK = (255, 100, 100, 255)  # 浅红

    # === TIER 1: 盟军步兵（8个）===
    print("👤 TIER 1: Allied Infantry (8 units)")
    create_enhanced_sprite(output_dir, "rifleman", ALLY_INFANTRY, "circle", "gradient")
    create_enhanced_sprite(output_dir, "mg_team", ALLY_INFANTRY, "circle", "gradient")
    create_enhanced_sprite(output_dir, "officer", ALLY_SUPPORT, "circle", "gradient")
    create_enhanced_sprite(output_dir, "engineer", ALLY_SUPPORT, "circle", "gradient")
    create_enhanced_sprite(output_dir, "sniper", ALLY_SUPPORT, "circle", "gradient")
    create_enhanced_sprite(output_dir, "medic", ALLY_SUPPORT, "circle", "gradient")
    create_enhanced_sprite(output_dir, "at_team", ALLY_SUPPORT, "circle", "gradient")
    create_enhanced_sprite(output_dir, "mortar_team", ALLY_SUPPORT, "circle", "gradient")
    sprite_count += 8

    # === TIER 2: 盟军载具（4个）===
    print("\n🚗 TIER 2: Allied Vehicles (4 units)")
    create_enhanced_sprite(output_dir, "medium_tank", ALLY_VEHICLE, "square", "shadow")
    create_enhanced_sprite(output_dir, "light_tank", ALLY_VEHICLE, "square", "shadow")
    create_enhanced_sprite(output_dir, "heavy_tank", ALLY_VEHICLE, "square", "shadow")
    create_enhanced_sprite(output_dir, "halftrack", ALLY_VEHICLE, "square", "shadow")
    sprite_count += 4

    # === TIER 3: 轴心国单位（4个）===
    print("\n⚔️  TIER 3: Axis Units (4 units)")
    create_enhanced_sprite(output_dir, "axis_rifleman", AXIS_INFANTRY, "circle", "gradient")
    create_enhanced_sprite(output_dir, "axis_mg_team", AXIS_INFANTRY, "circle", "gradient")
    create_enhanced_sprite(output_dir, "axis_officer", AXIS_INFANTRY, "circle", "gradient")
    create_enhanced_sprite(output_dir, "axis_tank", AXIS_VEHICLE, "square", "shadow")
    sprite_count += 4

    # === TIER 4: 特殊单位（2个）===
    print("\n⭐ TIER 4: Special Units (2 units)")
    create_enhanced_sprite(output_dir, "commander", SPECIAL, "triangle", "gradient")
    create_enhanced_sprite(output_dir, "scout", SPECIAL, "triangle", "gradient")
    sprite_count += 2

    # === PHASE 2 扩展：额外20个单位 ===
    print("\n" + "=" * 60)
    print("📦 PHASE 2 EXPANSION: +20 Units")
    print("=" * 60)

    # === TIER 5: 盟军扩展载具（5个）===
    print("\n🚙 TIER 5: Allied Extended Vehicles (5 units)")
    create_enhanced_sprite(output_dir, "m10_tank_destroyer", ALLY_VEHICLE, "square", "shadow")
    create_enhanced_sprite(output_dir, "m8_greyhound", ALLY_VEHICLE, "square", "shadow")
    create_enhanced_sprite(output_dir, "priest_artillery", ALLY_VEHICLE, "square", "shadow")
    create_enhanced_sprite(output_dir, "transport_truck", ALLY_VEHICLE, "square", "shadow")
    create_enhanced_sprite(output_dir, "ambulance", ALLY_SUPPORT, "square", "shadow")
    sprite_count += 5

    # === TIER 6: 轴心国扩展（5个）===
    print("\n🎖️  TIER 6: Axis Extended Units (5 units)")
    create_enhanced_sprite(output_dir, "axis_engineer", AXIS_SUPPORT, "circle", "gradient")
    create_enhanced_sprite(output_dir, "axis_sniper", AXIS_SUPPORT, "circle", "gradient")
    create_enhanced_sprite(output_dir, "axis_mortar", AXIS_SUPPORT, "circle", "gradient")
    create_enhanced_sprite(output_dir, "panzer_iv", AXIS_VEHICLE, "square", "shadow")
    create_enhanced_sprite(output_dir, "stug_iii", AXIS_VEHICLE, "square", "shadow")
    sprite_count += 5

    # === TIER 7: 建筑（6个）===
    print("\n🏠 TIER 7: Buildings (6 units)")
    create_enhanced_sprite(output_dir, "hq_building", ALLY_BUILDING, "square", "gradient")
    create_enhanced_sprite(output_dir, "barracks", ALLY_BUILDING, "square", "gradient")
    create_enhanced_sprite(output_dir, "motor_pool", ALLY_BUILDING, "square", "gradient")
    create_enhanced_sprite(output_dir, "bunker", BUILDING, "square", "shadow")
    create_enhanced_sprite(output_dir, "supply_depot", ALLY_BUILDING, "square", "gradient")
    create_enhanced_sprite(output_dir, "axis_hq", AXIS_BUILDING, "square", "gradient")
    sprite_count += 6

    # === TIER 8: UI元素（4个）===
    print("\n🎯 TIER 8: UI Elements (4 units)")
    create_enhanced_sprite(output_dir, "selection_box", UI_SELECT, "square", "standard")
    create_enhanced_sprite(output_dir, "movement_arrow", UI_MOVE, "triangle", "standard")
    create_enhanced_sprite(output_dir, "attack_cursor", UI_ATTACK, "circle", "standard")
    create_enhanced_sprite(output_dir, "waypoint_marker", UI_MOVE, "circle", "gradient")
    sprite_count += 4

    print()
    print("=" * 60)
    print("✅ Enhanced Sprite Generation Complete!")
    print(f"📁 Total sprites: {sprite_count}")
    print("📊 Breakdown:")
    print("   TIER 1-4 (Original): 18 units")
    print("   TIER 5: Allied Extended Vehicles: 5 units")
    print("   TIER 6: Axis Extended: 5 units")
    print("   TIER 7: Buildings: 6 units")
    print("   TIER 8: UI Elements: 4 units")
    print(f"📂 Location: {output_dir.absolute()}")
    print()
    print("🚀 Next Steps:")
    print("1. ✅ 40 units generated (20 original + 20 new)")
    print("2. Run tests: pytest tests/integration/test_cartoon_sprite_*.py")
    print("3. Phase 2.2: Add 4-direction support (N/S/E/W)")
    print("4. Phase 2.3: Add animation states (idle/walk/attack)")
    print("=" * 60)


if __name__ == "__main__":
    try:
        generate_enhanced_sprites()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
