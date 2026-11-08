#!/usr/bin/env python3
"""
PyCC2 动画精灵生成器 - Phase 2.3
为每个单位生成idle/walk/attack三种动画状态（简化版：每状态1帧）
"""

from pathlib import Path

from PIL import Image, ImageDraw


def create_animated_sprite(
    output_path: Path,
    name: str,
    color: tuple,
    shape: str = "circle",
    direction: str = "N",
    state: str = "idle",
    style: str = "standard"
):
    """创建带动画状态的32x32精灵

    Args:
        output_path: 输出目录
        name: 基础名称
        color: 主颜色RGBA
        shape: 形状 (circle/square/triangle)
        direction: 方向 (N/S/E/W)
        state: 动画状态 (idle/walk/attack)
        style: 样式 (standard/shadow/gradient)
    """
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    outline_color = (0, 0, 0, 255)
    outline_width = 2

    # 根据状态调整视觉效果
    state_effects = {
        'idle': {'offset': (0, 0), 'brightness': 0},
        'walk': {'offset': (1, 0), 'brightness': 10},  # 轻微位移
        'attack': {'offset': (0, 0), 'brightness': 30}  # 亮色闪烁
    }
    
    effect = state_effects.get(state, state_effects['idle'])
    offset_x, offset_y = effect['offset']
    brightness = effect['brightness']

    # 调整颜色亮度（attack状态）
    r, g, b, a = color
    if state == 'attack':
        r = min(r + brightness, 255)
        g = min(g + brightness, 255)
        b = min(b + brightness, 255)
    adjusted_color = (r, g, b, a)

    # 阴影效果
    shadow_offsets = {
        'N': (0, -2), 'S': (0, 2), 'E': (2, 0), 'W': (-2, 0)
    }
    
    if style in ["shadow", "gradient"]:
        shadow_color = (0, 0, 0, 80)
        sx, sy = shadow_offsets.get(direction, (2, 2))
        sx += offset_x
        sy += offset_y

        if shape == "circle":
            draw.ellipse([4 + sx, 4 + sy, 28 + sx, 28 + sy], fill=shadow_color)
        elif shape == "square":
            draw.rectangle([4 + sx, 4 + sy, 28 + sx, 28 + sy], fill=shadow_color)
        elif shape == "triangle":
            triangles = {
                'N': [(16 + sx, 4 + sy), (28 + sx, 28 + sy), (4 + sx, 28 + sy)],
                'S': [(16 + sx, 28 + sy), (4 + sx, 4 + sy), (28 + sx, 4 + sy)],
                'E': [(28 + sx, 16 + sy), (4 + sx, 4 + sy), (4 + sx, 28 + sy)],
                'W': [(4 + sx, 16 + sy), (28 + sx, 28 + sy), (28 + sx, 4 + sy)]
            }
            draw.polygon(triangles[direction], fill=shadow_color)

    # 渐变效果
    if style == "gradient":
        light_color = (min(r + 40, 255), min(g + 40, 255), min(b + 40, 255), a)
        dark_color = (max(r - 30, 0), max(g - 30, 0), max(b - 30, 0), a)

        if shape == "circle":
            gradient_angles = {
                'N': (180, 0), 'S': (0, 180), 'E': (270, 90), 'W': (90, 270)
            }
            start, end = gradient_angles[direction]
            draw.pieslice([4 + offset_x, 4 + offset_y, 28 + offset_x, 28 + offset_y],
                         start=start, end=end, fill=light_color)
            draw.pieslice([4 + offset_x, 4 + offset_y, 28 + offset_x, 28 + offset_y],
                         start=end, end=start, fill=dark_color)
        
        elif shape == "square":
            if direction == 'N':
                draw.rectangle([4 + offset_x, 4 + offset_y, 28 + offset_x, 16 + offset_y], fill=light_color)
                draw.rectangle([4 + offset_x, 16 + offset_y, 28 + offset_x, 28 + offset_y], fill=dark_color)
            elif direction == 'S':
                draw.rectangle([4 + offset_x, 4 + offset_y, 28 + offset_x, 16 + offset_y], fill=dark_color)
                draw.rectangle([4 + offset_x, 16 + offset_y, 28 + offset_x, 28 + offset_y], fill=light_color)
            elif direction == 'E':
                draw.rectangle([4 + offset_x, 4 + offset_y, 16 + offset_x, 28 + offset_y], fill=dark_color)
                draw.rectangle([16 + offset_x, 4 + offset_y, 28 + offset_x, 28 + offset_y], fill=light_color)
            elif direction == 'W':
                draw.rectangle([4 + offset_x, 4 + offset_y, 16 + offset_x, 28 + offset_y], fill=light_color)
                draw.rectangle([16 + offset_x, 4 + offset_y, 28 + offset_x, 28 + offset_y], fill=dark_color)
        
        elif shape == "triangle":
            triangles = {
                'N': [(16 + offset_x, 4 + offset_y), (28 + offset_x, 28 + offset_y), (4 + offset_x, 28 + offset_y)],
                'S': [(16 + offset_x, 28 + offset_y), (4 + offset_x, 4 + offset_y), (28 + offset_x, 4 + offset_y)],
                'E': [(28 + offset_x, 16 + offset_y), (4 + offset_x, 4 + offset_y), (4 + offset_x, 28 + offset_y)],
                'W': [(4 + offset_x, 16 + offset_y), (28 + offset_x, 28 + offset_y), (28 + offset_x, 4 + offset_y)]
            }
            draw.polygon(triangles[direction], fill=light_color)
    else:
        if shape == "circle":
            draw.ellipse([4 + offset_x, 4 + offset_y, 28 + offset_x, 28 + offset_y], fill=adjusted_color)
        elif shape == "square":
            draw.rectangle([4 + offset_x, 4 + offset_y, 28 + offset_x, 28 + offset_y], fill=adjusted_color)
        elif shape == "triangle":
            triangles = {
                'N': [(16 + offset_x, 4 + offset_y), (28 + offset_x, 28 + offset_y), (4 + offset_x, 28 + offset_y)],
                'S': [(16 + offset_x, 28 + offset_y), (4 + offset_x, 4 + offset_y), (28 + offset_x, 4 + offset_y)],
                'E': [(28 + offset_x, 16 + offset_y), (4 + offset_x, 4 + offset_y), (4 + offset_x, 28 + offset_y)],
                'W': [(4 + offset_x, 16 + offset_y), (28 + offset_x, 28 + offset_y), (28 + offset_x, 4 + offset_y)]
            }
            draw.polygon(triangles[direction], fill=adjusted_color)

    # 绘制轮廓
    if shape == "circle":
        draw.ellipse([4 + offset_x, 4 + offset_y, 28 + offset_x, 28 + offset_y],
                    outline=outline_color, width=outline_width)
    elif shape == "square":
        draw.rectangle([4 + offset_x, 4 + offset_y, 28 + offset_x, 28 + offset_y],
                      outline=outline_color, width=outline_width)
    elif shape == "triangle":
        triangles = {
            'N': [(16 + offset_x, 4 + offset_y), (28 + offset_x, 28 + offset_y), (4 + offset_x, 28 + offset_y)],
            'S': [(16 + offset_x, 28 + offset_y), (4 + offset_x, 4 + offset_y), (28 + offset_x, 4 + offset_y)],
            'E': [(28 + offset_x, 16 + offset_y), (4 + offset_x, 4 + offset_y), (4 + offset_x, 28 + offset_y)],
            'W': [(4 + offset_x, 16 + offset_y), (28 + offset_x, 28 + offset_y), (28 + offset_x, 4 + offset_y)]
        }
        draw.polygon(triangles[direction], outline=outline_color, width=outline_width)

    # 保存
    output_file = output_path / f"{name}_{direction}_{state}.png"
    img.save(output_file)


def generate_animated_sprites():
    """生成动画精灵集 - 38单位 × 4方向 × 3状态 = 456精灵"""
    base_dir = Path(__file__).parent
    output_dir = base_dir / "generated_animated"
    output_dir.mkdir(exist_ok=True)

    print("🎨 PyCC2 Animated Sprites Generation - Phase 2.3")
    print(f"📂 Output: {output_dir}")
    print("=" * 60)
    print()

    sprite_count = 0
    directions = ['N', 'S', 'E', 'W']
    states = ['idle', 'walk', 'attack']

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

    # 定义所有单位
    units = [
        # TIER 1-4 (18个)
        ("rifleman", ALLY_INFANTRY, "circle", "gradient"),
        ("mg_team", ALLY_INFANTRY, "circle", "gradient"),
        ("officer", ALLY_SUPPORT, "circle", "gradient"),
        ("engineer", ALLY_SUPPORT, "circle", "gradient"),
        ("sniper", ALLY_SUPPORT, "circle", "gradient"),
        ("medic", ALLY_SUPPORT, "circle", "gradient"),
        ("at_team", ALLY_SUPPORT, "circle", "gradient"),
        ("mortar_team", ALLY_SUPPORT, "circle", "gradient"),
        ("medium_tank", ALLY_VEHICLE, "square", "shadow"),
        ("light_tank", ALLY_VEHICLE, "square", "shadow"),
        ("heavy_tank", ALLY_VEHICLE, "square", "shadow"),
        ("halftrack", ALLY_VEHICLE, "square", "shadow"),
        ("axis_rifleman", AXIS_INFANTRY, "circle", "gradient"),
        ("axis_mg_team", AXIS_INFANTRY, "circle", "gradient"),
        ("axis_officer", AXIS_INFANTRY, "circle", "gradient"),
        ("axis_tank", AXIS_VEHICLE, "square", "shadow"),
        ("commander", SPECIAL, "triangle", "gradient"),
        ("scout", SPECIAL, "triangle", "gradient"),
        
        # TIER 5-8 (20个)
        ("m10_tank_destroyer", ALLY_VEHICLE, "square", "shadow"),
        ("m8_greyhound", ALLY_VEHICLE, "square", "shadow"),
        ("priest_artillery", ALLY_VEHICLE, "square", "shadow"),
        ("transport_truck", ALLY_VEHICLE, "square", "shadow"),
        ("ambulance", ALLY_SUPPORT, "square", "shadow"),
        ("axis_engineer", AXIS_SUPPORT, "circle", "gradient"),
        ("axis_sniper", AXIS_SUPPORT, "circle", "gradient"),
        ("axis_mortar", AXIS_SUPPORT, "circle", "gradient"),
        ("panzer_iv", AXIS_VEHICLE, "square", "shadow"),
        ("stug_iii", AXIS_VEHICLE, "square", "shadow"),
        ("hq_building", ALLY_BUILDING, "square", "gradient"),
        ("barracks", ALLY_BUILDING, "square", "gradient"),
        ("motor_pool", ALLY_BUILDING, "square", "gradient"),
        ("bunker", BUILDING, "square", "shadow"),
        ("supply_depot", ALLY_BUILDING, "square", "gradient"),
        ("axis_hq", AXIS_BUILDING, "square", "gradient"),
        ("selection_box", UI_SELECT, "square", "standard"),
        ("movement_arrow", UI_MOVE, "triangle", "standard"),
        ("attack_cursor", UI_ATTACK, "circle", "standard"),
        ("waypoint_marker", UI_MOVE, "circle", "gradient"),
    ]

    # 生成所有单位的动画精灵
    for idx, (name, color, shape, style) in enumerate(units, start=1):
        print(f"[{idx}/38] {name} (4dir × 3states)...", end=" ")
        for direction in directions:
            for state in states:
                create_animated_sprite(output_dir, name, color, shape, direction, state, style)
                sprite_count += 1
        print("✅")

    print()
    print("=" * 60)
    print("✅ Animated Sprite Generation Complete!")
    print(f"📁 Total sprites: {sprite_count}")
    print(f"📊 Breakdown: 38 units × 4 directions × 3 states = {sprite_count}")
    print(f"📂 Location: {output_dir.absolute()}")
    print()
    print("🚀 Phase 2 Complete!")
    print("1. ✅ Phase 2.1: 38 enhanced sprites")
    print("2. ✅ Phase 2.2: 152 directional sprites")
    print("3. ✅ Phase 2.3: 456 animated sprites")
    print()
    print("📦 Total cartoon assets: 646 sprites")
    print("=" * 60)


if __name__ == "__main__":
    try:
        generate_animated_sprites()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
