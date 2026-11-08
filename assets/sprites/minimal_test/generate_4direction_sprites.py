#!/usr/bin/env python3
"""
PyCC2 4方向精灵生成器 - Phase 2.2
为每个单位生成4个方向的精灵（N/S/E/W）
"""

from pathlib import Path

from PIL import Image, ImageDraw


def create_directional_sprite(
    output_path: Path,
    name: str,
    color: tuple,
    shape: str = "circle",
    direction: str = "N",
    style: str = "standard"
):
    """创建带方向的32x32精灵

    Args:
        output_path: 输出目录
        name: 基础名称
        color: 主颜色RGBA
        shape: 形状 (circle/square/triangle)
        direction: 方向 (N/S/E/W)
        style: 样式 (standard/shadow/gradient)
    """
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    outline_color = (0, 0, 0, 255)
    outline_width = 2

    # 阴影效果（根据方向调整偏移）
    shadow_offsets = {
        'N': (0, -2),  # 北：阴影在下方
        'S': (0, 2),   # 南：阴影在上方
        'E': (2, 0),   # 东：阴影在左侧
        'W': (-2, 0)   # 西：阴影在右侧
    }
    
    if style in ["shadow", "gradient"]:
        shadow_color = (0, 0, 0, 80)
        sx, sy = shadow_offsets.get(direction, (2, 2))

        if shape == "circle":
            draw.ellipse(
                [4 + sx, 4 + sy, 28 + sx, 28 + sy],
                fill=shadow_color
            )
        elif shape == "square":
            draw.rectangle(
                [4 + sx, 4 + sy, 28 + sx, 28 + sy],
                fill=shadow_color
            )
        elif shape == "triangle":
            # 三角形根据方向旋转
            triangles = {
                'N': [(16 + sx, 4 + sy), (28 + sx, 28 + sy), (4 + sx, 28 + sy)],
                'S': [(16 + sx, 28 + sy), (4 + sx, 4 + sy), (28 + sx, 4 + sy)],
                'E': [(28 + sx, 16 + sy), (4 + sx, 4 + sy), (4 + sx, 28 + sy)],
                'W': [(4 + sx, 16 + sy), (28 + sx, 28 + sy), (28 + sx, 4 + sy)]
            }
            draw.polygon(triangles[direction], fill=shadow_color)

    # 渐变效果（根据方向调整亮暗色位置）
    if style == "gradient":
        r, g, b, a = color
        light_color = (min(r + 40, 255), min(g + 40, 255), min(b + 40, 255), a)
        dark_color = (max(r - 30, 0), max(g - 30, 0), max(b - 30, 0), a)

        if shape == "circle":
            # 圆形：根据方向调整渐变方向
            gradient_angles = {
                'N': (180, 0),   # 上亮下暗
                'S': (0, 180),   # 下亮上暗
                'E': (270, 90),  # 右亮左暗
                'W': (90, 270)   # 左亮右暗
            }
            start, end = gradient_angles[direction]
            draw.pieslice([4, 4, 28, 28], start=start, end=end, fill=light_color)
            draw.pieslice([4, 4, 28, 28], start=end, end=start, fill=dark_color)
        
        elif shape == "square":
            # 方形：根据方向分块
            if direction == 'N':
                draw.rectangle([4, 4, 28, 16], fill=light_color)
                draw.rectangle([4, 16, 28, 28], fill=dark_color)
            elif direction == 'S':
                draw.rectangle([4, 4, 28, 16], fill=dark_color)
                draw.rectangle([4, 16, 28, 28], fill=light_color)
            elif direction == 'E':
                draw.rectangle([4, 4, 16, 28], fill=dark_color)
                draw.rectangle([16, 4, 28, 28], fill=light_color)
            elif direction == 'W':
                draw.rectangle([4, 4, 16, 28], fill=light_color)
                draw.rectangle([16, 4, 28, 28], fill=dark_color)
        
        elif shape == "triangle":
            # 三角形根据方向旋转
            triangles = {
                'N': [(16, 4), (28, 28), (4, 28)],
                'S': [(16, 28), (4, 4), (28, 4)],
                'E': [(28, 16), (4, 4), (4, 28)],
                'W': [(4, 16), (28, 28), (28, 4)]
            }
            draw.polygon(triangles[direction], fill=light_color)
    else:
        # 标准纯色（方向通过形状旋转体现）
        if shape == "circle":
            draw.ellipse([4, 4, 28, 28], fill=color)
        elif shape == "square":
            draw.rectangle([4, 4, 28, 28], fill=color)
        elif shape == "triangle":
            triangles = {
                'N': [(16, 4), (28, 28), (4, 28)],
                'S': [(16, 28), (4, 4), (28, 4)],
                'E': [(28, 16), (4, 4), (4, 28)],
                'W': [(4, 16), (28, 28), (28, 4)]
            }
            draw.polygon(triangles[direction], fill=color)

    # 绘制轮廓
    if shape == "circle":
        draw.ellipse([4, 4, 28, 28], outline=outline_color, width=outline_width)
    elif shape == "square":
        draw.rectangle([4, 4, 28, 28], outline=outline_color, width=outline_width)
    elif shape == "triangle":
        triangles = {
            'N': [(16, 4), (28, 28), (4, 28)],
            'S': [(16, 28), (4, 4), (28, 4)],
            'E': [(28, 16), (4, 4), (4, 28)],
            'W': [(4, 16), (28, 28), (28, 4)]
        }
        draw.polygon(triangles[direction], outline=outline_color, width=outline_width)

    # 保存
    output_file = output_path / f"{name}_{direction}.png"
    img.save(output_file)


def generate_4direction_sprites():
    """生成4方向精灵集 - 38个单位 × 4方向 = 152个精灵"""
    base_dir = Path(__file__).parent
    output_dir = base_dir / "generated_4dir"
    output_dir.mkdir(exist_ok=True)

    print("🎨 PyCC2 4-Direction Sprites Generation - Phase 2.2")
    print(f"📂 Output: {output_dir}")
    print("=" * 60)
    print()

    sprite_count = 0
    directions = ['N', 'S', 'E', 'W']

    # 颜色定义
    ALLY_INFANTRY = (107, 142, 35, 255)
    ALLY_VEHICLE = (79, 111, 82, 255)
    ALLY_SUPPORT = (139, 157, 89, 255)
    AXIS_INFANTRY = (220, 20, 60, 255)
    AXIS_VEHICLE = (178, 34, 34, 255)
    AXIS_SUPPORT = (200, 60, 80, 255)
    SPECIAL = (255, 215, 0, 255)
    BUILDING = (139, 69, 19, 255)
    ALLY_BUILDING = (90, 120, 70, 255)
    AXIS_BUILDING = (150, 50, 50, 255)
    UI_SELECT = (255, 255, 0, 255)
    UI_MOVE = (0, 255, 0, 255)
    UI_ATTACK = (255, 100, 100, 255)

    # 定义所有单位（名称，颜色，形状，样式）
    units = [
        # TIER 1: 盟军步兵（8个）
        ("rifleman", ALLY_INFANTRY, "circle", "gradient"),
        ("mg_team", ALLY_INFANTRY, "circle", "gradient"),
        ("officer", ALLY_SUPPORT, "circle", "gradient"),
        ("engineer", ALLY_SUPPORT, "circle", "gradient"),
        ("sniper", ALLY_SUPPORT, "circle", "gradient"),
        ("medic", ALLY_SUPPORT, "circle", "gradient"),
        ("at_team", ALLY_SUPPORT, "circle", "gradient"),
        ("mortar_team", ALLY_SUPPORT, "circle", "gradient"),
        
        # TIER 2: 盟军载具（4个）
        ("medium_tank", ALLY_VEHICLE, "square", "shadow"),
        ("light_tank", ALLY_VEHICLE, "square", "shadow"),
        ("heavy_tank", ALLY_VEHICLE, "square", "shadow"),
        ("halftrack", ALLY_VEHICLE, "square", "shadow"),
        
        # TIER 3: 轴心国（4个）
        ("axis_rifleman", AXIS_INFANTRY, "circle", "gradient"),
        ("axis_mg_team", AXIS_INFANTRY, "circle", "gradient"),
        ("axis_officer", AXIS_INFANTRY, "circle", "gradient"),
        ("axis_tank", AXIS_VEHICLE, "square", "shadow"),
        
        # TIER 4: 特殊单位（2个）
        ("commander", SPECIAL, "triangle", "gradient"),
        ("scout", SPECIAL, "triangle", "gradient"),
        
        # TIER 5: 盟军扩展载具（5个）
        ("m10_tank_destroyer", ALLY_VEHICLE, "square", "shadow"),
        ("m8_greyhound", ALLY_VEHICLE, "square", "shadow"),
        ("priest_artillery", ALLY_VEHICLE, "square", "shadow"),
        ("transport_truck", ALLY_VEHICLE, "square", "shadow"),
        ("ambulance", ALLY_SUPPORT, "square", "shadow"),
        
        # TIER 6: 轴心国扩展（5个）
        ("axis_engineer", AXIS_SUPPORT, "circle", "gradient"),
        ("axis_sniper", AXIS_SUPPORT, "circle", "gradient"),
        ("axis_mortar", AXIS_SUPPORT, "circle", "gradient"),
        ("panzer_iv", AXIS_VEHICLE, "square", "shadow"),
        ("stug_iii", AXIS_VEHICLE, "square", "shadow"),
        
        # TIER 7: 建筑（6个）
        ("hq_building", ALLY_BUILDING, "square", "gradient"),
        ("barracks", ALLY_BUILDING, "square", "gradient"),
        ("motor_pool", ALLY_BUILDING, "square", "gradient"),
        ("bunker", BUILDING, "square", "shadow"),
        ("supply_depot", ALLY_BUILDING, "square", "gradient"),
        ("axis_hq", AXIS_BUILDING, "square", "gradient"),
        
        # TIER 8: UI元素（4个）
        ("selection_box", UI_SELECT, "square", "standard"),
        ("movement_arrow", UI_MOVE, "triangle", "standard"),
        ("attack_cursor", UI_ATTACK, "circle", "standard"),
        ("waypoint_marker", UI_MOVE, "circle", "gradient"),
    ]

    # 生成所有单位的4方向精灵
    for idx, (name, color, shape, style) in enumerate(units, start=1):
        print(f"[{idx}/38] {name} (4 directions)...", end=" ")
        for direction in directions:
            create_directional_sprite(output_dir, name, color, shape, direction, style)
            sprite_count += 1
        print("✅")

    print()
    print("=" * 60)
    print("✅ 4-Direction Sprite Generation Complete!")
    print(f"📁 Total sprites: {sprite_count}")
    print(f"📊 Breakdown: 38 units × 4 directions = {sprite_count}")
    print(f"📂 Location: {output_dir.absolute()}")
    print()
    print("🚀 Next Steps:")
    print("1. ✅ 152 directional sprites generated")
    print("2. Update AssetLoader to support direction-based loading")
    print("3. Phase 2.3: Add animation states (idle/walk/attack)")
    print("=" * 60)


if __name__ == "__main__":
    try:
        generate_4direction_sprites()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
