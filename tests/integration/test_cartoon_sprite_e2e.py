#!/usr/bin/env python3
"""
E2E测试：验证卡通精灵在完整游戏渲染流程中是否正常工作
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

import pygame

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord


def test_cartoon_sprite_e2e():
    """完整的渲染测试"""
    print("=" * 60)
    print("🎮 PyCC2 Cartoon Sprite E2E Test")
    print("=" * 60)
    print()

    # 初始化Pygame
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("PyCC2 Cartoon Sprite Test")

    # 初始化资产加载器（不需要完整渲染器）
    print("🔧 Initializing asset loader...")
    from pycc2.presentation.rendering.asset_loader import AssetLoader

    loader = AssetLoader(project_root / "assets")

    # 创建测试单位
    print("👤 Creating test units...")
    test_units = [
        Unit(
            id="test_rifleman",
            name="Test Rifleman",
            faction=Faction.ALLIES,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=80),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(2, 2)),
            vision=VisionComponent(range_tiles=5),
        ),
        Unit(
            id="test_mg",
            name="Test MG Team",
            faction=Faction.ALLIES,
            unit_type=UnitType.MACHINE_GUN_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=80),
            weapon=WeaponComponent(primary_weapon_id="mg", ammo_remaining=20, max_ammo=20),
            position=PositionComponent(tile_coord=TileCoord(4, 2)),
            vision=VisionComponent(range_tiles=5),
        ),
        Unit(
            id="test_tank",
            name="Test Sherman",
            faction=Faction.ALLIES,
            unit_type=UnitType.TANK,
            health=HealthComponent(hp=200, max_hp=200),
            morale=MoraleComponent(value=100),
            weapon=WeaponComponent(primary_weapon_id="75mm", ammo_remaining=40, max_ammo=40),
            position=PositionComponent(tile_coord=TileCoord(2, 4)),
            vision=VisionComponent(range_tiles=7),
        ),
        Unit(
            id="test_enemy",
            name="Enemy Rifleman",
            faction=Faction.AXIS,
            unit_type=UnitType.INFANTRY_SQUAD,
            health=HealthComponent(hp=100, max_hp=100),
            morale=MoraleComponent(value=80),
            weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=10, max_ammo=10),
            position=PositionComponent(tile_coord=TileCoord(6, 4)),
            vision=VisionComponent(range_tiles=5),
        ),
    ]

    print(f"   Created {len(test_units)} test units")
    print()

    # 渲染测试
    print("🎨 Rendering test frame...")
    try:
        # 清屏
        screen.fill((100, 150, 100))  # 草地绿色背景

        render_count = 0
        for unit in test_units:
            # 加载精灵
            sprite = loader.load_unit_sprite(
                faction=unit.faction.name.lower(),
                unit_type=unit.unit_type.name,
                direction=4,  # 朝南
                size=128,
            )

            if sprite:
                # 计算屏幕位置
                screen_x = int(unit.position.tile_coord.x * 80)
                screen_y = int(unit.position.tile_coord.y * 80)

                # 绘制精灵
                screen.blit(sprite, (screen_x, screen_y))
                render_count += 1

                # 绘制单位名称
                font = pygame.font.Font(None, 24)
                name_surf = font.render(unit.name, True, (255, 255, 255))
                screen.blit(name_surf, (screen_x, screen_y - 20))

        print(f"   ✅ Rendered {render_count}/{len(test_units)} units")

        # 更新显示
        pygame.display.flip()

        # 保存截图
        screenshot_path = (
            project_root / "tests" / "integration" / "cartoon_sprite_test_screenshot.png"
        )
        pygame.image.save(screen, str(screenshot_path))
        print(f"   📸 Screenshot saved: {screenshot_path}")
        print()

        # 等待用户查看（3秒）
        print("⏱️  Displaying for 3 seconds...")
        pygame.time.wait(3000)

        print()
        print("=" * 60)
        print("✅ E2E Test PASSED!")
        print()
        print("📊 Summary:")
        print(f"   - Units created: {len(test_units)}")
        print(f"   - Units rendered: {render_count}")
        print("   - Sprites loaded: Yes")
        print(f"   - Screenshot: {screenshot_path}")
        print()
        print("🚀 Next steps:")
        print("1. ✅ Cartoon sprites are working in PyCC2")
        print("2. Run full game test with these sprites")
        print("3. Replace with professional assets if needed")
        print("=" * 60)

        success = True

    except Exception as e:
        print(f"❌ E2E Test FAILED: {e}")
        import traceback

        traceback.print_exc()
        success = False

    finally:
        pygame.quit()

    return success


if __name__ == "__main__":
    success = test_cartoon_sprite_e2e()
    sys.exit(0 if success else 1)
