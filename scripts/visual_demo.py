#!/usr/bin/env python3
"""
PyCC2 视觉优化完整演示
展示所有Phase 1-4的优化效果
"""
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pygame
from pygame import Surface
from pycc2.presentation.rendering.asset_loader import AssetLoader
from pycc2.presentation.rendering.terrain_enhancer import TerrainEnhancer
from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer
from pycc2.presentation.rendering.visual_effects import (
    EnhancedWeatherSystem,
    PostProcessingEffects,
    EnhancedParticleSystem,
    WeatherType,
)


def main():
    pygame.init()
    
    # 窗口设置
    width, height = 1280, 800
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("PyCC2 视觉优化完整演示")
    clock = pygame.time.Clock()
    
    # 初始化所有系统
    asset_loader = AssetLoader()
    terrain_enhancer = TerrainEnhancer(seed=42)
    weather_system = EnhancedWeatherSystem(width, height)
    post_fx = PostProcessingEffects(width, height)
    particles = EnhancedParticleSystem()
    
    # 生成地形纹理
    grass = terrain_enhancer.generate_grass_texture(size=128)
    dirt = terrain_enhancer.generate_dirt_texture(size=128)
    water = terrain_enhancer.generate_water_texture(size=128)
    
    # 生成简单的精灵示例（128x128高分辨率）
    unit_sprite = Surface((128, 128), pygame.SRCALPHA)
    unit_sprite.fill((0, 0, 0, 0))
    pygame.draw.circle(unit_sprite, (100, 150, 100), (64, 64), 50)
    pygame.draw.circle(unit_sprite, (80, 120, 80), (64, 50), 20)
    pygame.draw.rect(unit_sprite, (60, 100, 60), (54, 70, 20, 40))
    
    vehicle_sprite = Surface((128, 128), pygame.SRCALPHA)
    vehicle_sprite.fill((0, 0, 0, 0))
    pygame.draw.rect(vehicle_sprite, (100, 100, 80), (20, 40, 88, 60))
    pygame.draw.rect(vehicle_sprite, (80, 80, 60), (30, 50, 68, 30))
    pygame.draw.circle(vehicle_sprite, (50, 50, 40), (40, 90), 12)
    pygame.draw.circle(vehicle_sprite, (50, 50, 40), (88, 90), 12)
    
    # 状态
    current_weather = WeatherType.CLEAR
    weather_intensity = 0.8
    vignette_enabled = True
    color_grading_enabled = True
    show_help = True
    
    # 启用后处理
    post_fx.enable_vignette(0.3)
    post_fx.enable_color_grading()
    
    # 字体
    font = pygame.font.Font(None, 24)
    title_font = pygame.font.Font(None, 48)
    
    running = True
    frame = 0
    
    print("\n" + "="*70)
    print("  PyCC2 视觉优化完整演示")
    print("="*70)
    print("\n控制:")
    print("  1-4: 切换天气 (1=晴天, 2=雨, 3=雪, 4=雾)")
    print("  SPACE: 触发爆炸效果")
    print("  V: 切换暗角效果")
    print("  C: 切换色彩分级")
    print("  H: 切换帮助显示")
    print("  ESC: 退出")
    print("="*70 + "\n")
    
    while running:
        frame += 1
        
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_1:
                    current_weather = WeatherType.CLEAR
                    weather_system.set_weather(current_weather, weather_intensity)
                    print("☀️  天气: 晴天")
                elif event.key == pygame.K_2:
                    current_weather = WeatherType.RAIN
                    weather_system.set_weather(current_weather, weather_intensity)
                    print("🌧️  天气: 雨天")
                elif event.key == pygame.K_3:
                    current_weather = WeatherType.SNOW
                    weather_system.set_weather(current_weather, weather_intensity)
                    print("❄️  天气: 雪天")
                elif event.key == pygame.K_4:
                    current_weather = WeatherType.FOG
                    weather_system.set_weather(current_weather, weather_intensity)
                    print("🌫️  天气: 雾天")
                elif event.key == pygame.K_SPACE:
                    # 在屏幕中心触发爆炸
                    particles.emit_explosion(width // 2, height // 2, 1.5)
                    print("💥 爆炸效果触发")
                elif event.key == pygame.K_v:
                    vignette_enabled = not vignette_enabled
                    if vignette_enabled:
                        post_fx.enable_vignette(0.3)
                        print("✅ 暗角效果: 开启")
                    else:
                        post_fx.disable_vignette()
                        print("❌ 暗角效果: 关闭")
                elif event.key == pygame.K_c:
                    color_grading_enabled = not color_grading_enabled
                    if color_grading_enabled:
                        post_fx.enable_color_grading()
                        print("✅ 色彩分级: 开启")
                    else:
                        post_fx.disable_color_grading()
                        print("❌ 色彩分级: 关闭")
                elif event.key == pygame.K_h:
                    show_help = not show_help
        
        # 清屏
        screen.fill((40, 40, 45))
        
        # ===== Phase 2: 地形展示 =====
        terrain_y = 100
        terrain_x = 50
        
        # 标题
        title = title_font.render("PyCC2 视觉优化演示", True, (255, 255, 255))
        screen.blit(title, (width // 2 - title.get_width() // 2, 20))
        
        # Phase 2标签
        label = font.render("Phase 2: 地形纹理 (Perlin噪声)", True, (200, 200, 200))
        screen.blit(label, (terrain_x, terrain_y - 30))
        
        # 绘制地形纹理
        screen.blit(grass, (terrain_x, terrain_y))
        screen.blit(dirt, (terrain_x + 150, terrain_y))
        screen.blit(water, (terrain_x + 300, terrain_y))
        
        # 地形标签
        grass_label = font.render("草地", True, (150, 255, 150))
        dirt_label = font.render("泥土", True, (200, 180, 140))
        water_label = font.render("水面", True, (150, 200, 255))
        screen.blit(grass_label, (terrain_x + 40, terrain_y + 135))
        screen.blit(dirt_label, (terrain_x + 190, terrain_y + 135))
        screen.blit(water_label, (terrain_x + 340, terrain_y + 135))
        
        # ===== Phase 3: 精灵展示 =====
        sprite_y = 280
        
        label = font.render("Phase 3: 高分辨率精灵 (128x128)", True, (200, 200, 200))
        screen.blit(label, (terrain_x, sprite_y - 30))
        
        # 绘制精灵
        screen.blit(unit_sprite, (terrain_x, sprite_y))
        screen.blit(vehicle_sprite, (terrain_x + 150, sprite_y))
        
        # 精灵标签
        unit_label = font.render("步兵", True, (150, 255, 150))
        vehicle_label = font.render("坦克", True, (200, 200, 140))
        screen.blit(unit_label, (terrain_x + 45, sprite_y + 135))
        screen.blit(vehicle_label, (terrain_x + 195, sprite_y + 135))
        
        # ===== Phase 4: 粒子效果展示区域 =====
        particle_area_x = 550
        particle_area_y = 100
        particle_area_w = width - particle_area_x - 50
        particle_area_h = 500
        
        label = font.render("Phase 4: 视觉效果", True, (200, 200, 200))
        screen.blit(label, (particle_area_x, particle_area_y - 30))
        
        # 绘制粒子区域边框
        pygame.draw.rect(screen, (80, 80, 90), 
                        (particle_area_x, particle_area_y, particle_area_w, particle_area_h), 2)
        
        # 更新和渲染粒子
        particles.update()
        particles.render(screen)
        
        # 更新和渲染天气
        weather_system.update()
        weather_system.render(screen)
        
        # ===== 应用后处理效果 =====
        if color_grading_enabled:
            post_fx.apply_color_grading(screen, "war")
        
        if vignette_enabled:
            post_fx.apply_vignette(screen)
        
        # ===== 状态信息 =====
        info_y = height - 150
        
        # 当前状态
        weather_names = {
            WeatherType.CLEAR: "☀️  晴天",
            WeatherType.RAIN: "🌧️  雨天",
            WeatherType.SNOW: "❄️  雪天",
            WeatherType.FOG: "🌫️  雾天",
        }
        
        status_texts = [
            f"天气: {weather_names[current_weather]}",
            f"暗角: {'✅ 开启' if vignette_enabled else '❌ 关闭'}",
            f"色彩分级: {'✅ 开启' if color_grading_enabled else '❌ 关闭'}",
            f"粒子数: {len(particles.particles)}",
            f"FPS: {int(clock.get_fps())}",
        ]
        
        for i, text in enumerate(status_texts):
            surf = font.render(text, True, (200, 200, 200))
            screen.blit(surf, (50, info_y + i * 25))
        
        # ===== 帮助信息 =====
        if show_help:
            help_x = width - 350
            help_y = height - 180
            
            # 半透明背景
            help_bg = Surface((330, 170), pygame.SRCALPHA)
            help_bg.fill((0, 0, 0, 180))
            screen.blit(help_bg, (help_x - 10, help_y - 10))
            
            help_texts = [
                "控制:",
                "  1-4: 切换天气",
                "  SPACE: 触发爆炸",
                "  V: 切换暗角",
                "  C: 切换色彩分级",
                "  H: 隐藏/显示帮助",
                "  ESC: 退出",
            ]
            
            for i, text in enumerate(help_texts):
                surf = font.render(text, True, (220, 220, 220))
                screen.blit(surf, (help_x, help_y + i * 23))
        
        # 更新显示
        pygame.display.flip()
        clock.tick(60)
    
    pygame.quit()
    print("\n演示结束")


if __name__ == "__main__":
    main()
