#!/usr/bin/env python3
"""
创建CC2风格的像素艺术精灵
生成高质量的单位和地形精灵，模仿Close Combat 2的视觉风格
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np


class CC2StyleSpriteGenerator:
    """生成CC2风格的像素艺术精灵"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # CC2风格的颜色调色板
        self.colors = {
            # 盟军（美军/英军）- 橄榄绿
            'allied_dark': (45, 66, 35),
            'allied_mid': (78, 104, 56),
            'allied_light': (120, 140, 80),
            'allied_highlight': (160, 180, 120),
            
            # 轴心国（德军）- 灰绿色
            'axis_dark': (50, 55, 45),
            'axis_mid': (85, 90, 75),
            'axis_light': (120, 125, 105),
            'axis_highlight': (155, 160, 140),
            
            # 皮肤色
            'skin_dark': (120, 80, 60),
            'skin_mid': (180, 130, 100),
            'skin_light': (220, 180, 150),
            
            # 武器/金属
            'metal_dark': (40, 40, 45),
            'metal_mid': (80, 80, 90),
            'metal_light': (140, 140, 150),
            
            # 载具
            'tank_dark': (30, 35, 30),
            'tank_mid': (60, 70, 60),
            'tank_light': (100, 110, 95),
            
            # 通用
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'brown': (101, 67, 33),
        }
    
    def create_infantry_sprite(self, faction: str, size: int = 32) -> Image.Image:
        """创建步兵精灵（俯视图）"""
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 选择颜色
        if faction == 'allied':
            uniform_dark = self.colors['allied_dark']
            uniform_mid = self.colors['allied_mid']
            uniform_light = self.colors['allied_light']
        else:
            uniform_dark = self.colors['axis_dark']
            uniform_mid = self.colors['axis_mid']
            uniform_light = self.colors['axis_light']
        
        center_x, center_y = size // 2, size // 2
        
        # 头盔（圆形）
        helmet_radius = size // 6
        draw.ellipse([
            center_x - helmet_radius, center_y - helmet_radius - 2,
            center_x + helmet_radius, center_y + helmet_radius - 2
        ], fill=uniform_dark)
        
        # 身体（椭圆）
        body_width = size // 4
        body_height = size // 3
        draw.ellipse([
            center_x - body_width, center_y,
            center_x + body_width, center_y + body_height
        ], fill=uniform_mid)
        
        # 背包
        pack_size = size // 8
        draw.rectangle([
            center_x - pack_size, center_y + 2,
            center_x + pack_size, center_y + pack_size + 2
        ], fill=self.colors['brown'])
        
        # 武器（步枪）
        weapon_length = size // 3
        draw.line([
            (center_x + body_width, center_y + 4),
            (center_x + body_width + weapon_length, center_y - 2)
        ], fill=self.colors['metal_dark'], width=2)
        
        # 高光
        draw.ellipse([
            center_x - helmet_radius // 2, center_y - helmet_radius - 1,
            center_x, center_y - 1
        ], fill=uniform_light)
        
        return img
    
    def create_tank_sprite(self, faction: str, size: int = 48) -> Image.Image:
        """创建坦克精灵（俯视图）"""
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center_x, center_y = size // 2, size // 2
        
        # 车体（矩形）
        hull_width = size // 2
        hull_height = int(size * 0.6)
        hull_rect = [
            center_x - hull_width // 2, center_y - hull_height // 2,
            center_x + hull_width // 2, center_y + hull_height // 2
        ]
        draw.rectangle(hull_rect, fill=self.colors['tank_mid'], outline=self.colors['tank_dark'])
        
        # 炮塔（圆形）
        turret_radius = size // 5
        draw.ellipse([
            center_x - turret_radius, center_y - turret_radius,
            center_x + turret_radius, center_y + turret_radius
        ], fill=self.colors['tank_dark'], outline=self.colors['black'])
        
        # 炮管
        barrel_length = size // 3
        barrel_width = 3
        draw.rectangle([
            center_x - barrel_width // 2, center_y - turret_radius - barrel_length,
            center_x + barrel_width // 2, center_y - turret_radius
        ], fill=self.colors['metal_mid'], outline=self.colors['metal_dark'])
        
        # 履带（两侧）
        track_width = 4
        track_offset = hull_width // 2 + 2
        # 左履带
        draw.rectangle([
            center_x - track_offset, center_y - hull_height // 2 - 2,
            center_x - track_offset + track_width, center_y + hull_height // 2 + 2
        ], fill=self.colors['black'])
        # 右履带
        draw.rectangle([
            center_x + track_offset - track_width, center_y - hull_height // 2 - 2,
            center_x + track_offset, center_y + hull_height // 2 + 2
        ], fill=self.colors['black'])
        
        # 高光
        draw.ellipse([
            center_x - turret_radius // 2, center_y - turret_radius // 2,
            center_x, center_y
        ], fill=self.colors['tank_light'])
        
        return img
    
    def create_vehicle_sprite(self, vehicle_type: str, size: int = 40) -> Image.Image:
        """创建载具精灵（吉普/半履带车）"""
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center_x, center_y = size // 2, size // 2
        
        if vehicle_type == 'jeep':
            # 吉普车身
            body_width = size // 3
            body_height = int(size * 0.5)
            draw.rectangle([
                center_x - body_width // 2, center_y - body_height // 2,
                center_x + body_width // 2, center_y + body_height // 2
            ], fill=self.colors['allied_mid'], outline=self.colors['allied_dark'])
            
            # 驾驶舱
            cabin_size = size // 5
            draw.rectangle([
                center_x - cabin_size, center_y - cabin_size,
                center_x + cabin_size, center_y + cabin_size
            ], fill=self.colors['allied_dark'])
            
            # 车轮（4个）
            wheel_radius = 3
            wheel_positions = [
                (center_x - body_width // 2 - 2, center_y - body_height // 3),
                (center_x + body_width // 2 + 2, center_y - body_height // 3),
                (center_x - body_width // 2 - 2, center_y + body_height // 3),
                (center_x + body_width // 2 + 2, center_y + body_height // 3),
            ]
            for wx, wy in wheel_positions:
                draw.ellipse([
                    wx - wheel_radius, wy - wheel_radius,
                    wx + wheel_radius, wy + wheel_radius
                ], fill=self.colors['black'])
        
        else:  # halftrack
            # 半履带车身
            body_width = size // 2
            body_height = int(size * 0.6)
            draw.rectangle([
                center_x - body_width // 2, center_y - body_height // 2,
                center_x + body_width // 2, center_y + body_height // 2
            ], fill=self.colors['tank_mid'], outline=self.colors['tank_dark'])
            
            # 前轮
            wheel_radius = 3
            draw.ellipse([
                center_x - wheel_radius, center_y - body_height // 2 - wheel_radius - 2,
                center_x + wheel_radius, center_y - body_height // 2 + wheel_radius - 2
            ], fill=self.colors['black'])
            
            # 后履带
            track_width = 4
            track_offset = body_width // 2 + 2
            draw.rectangle([
                center_x - track_offset, center_y,
                center_x - track_offset + track_width, center_y + body_height // 2 + 2
            ], fill=self.colors['black'])
            draw.rectangle([
                center_x + track_offset - track_width, center_y,
                center_x + track_offset, center_y + body_height // 2 + 2
            ], fill=self.colors['black'])
        
        return img
    
    def create_building_sprite(self, building_type: str, size: int = 64) -> Image.Image:
        """创建建筑精灵"""
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if building_type == 'house':
            # 房屋墙体
            wall_color = (180, 160, 140)
            roof_color = (120, 80, 60)
            
            wall_rect = [size // 6, size // 3, size * 5 // 6, size * 5 // 6]
            draw.rectangle(wall_rect, fill=wall_color, outline=(100, 90, 80))
            
            # 屋顶（三角形）
            roof_points = [
                (size // 6, size // 3),
                (size // 2, size // 8),
                (size * 5 // 6, size // 3)
            ]
            draw.polygon(roof_points, fill=roof_color, outline=(80, 50, 40))
            
            # 窗户
            window_size = size // 10
            window_color = (100, 120, 150)
            draw.rectangle([
                size // 3, size // 2,
                size // 3 + window_size, size // 2 + window_size
            ], fill=window_color)
            draw.rectangle([
                size * 2 // 3 - window_size, size // 2,
                size * 2 // 3, size // 2 + window_size
            ], fill=window_color)
            
            # 门
            door_width = size // 6
            door_height = size // 4
            draw.rectangle([
                size // 2 - door_width // 2, size * 5 // 6 - door_height,
                size // 2 + door_width // 2, size * 5 // 6
            ], fill=(80, 50, 30))
        
        return img
    
    def create_tree_sprite(self, size: int = 48) -> Image.Image:
        """创建树木精灵"""
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        center_x, center_y = size // 2, size // 2
        
        # 树干
        trunk_width = size // 8
        trunk_height = size // 3
        draw.rectangle([
            center_x - trunk_width // 2, center_y + size // 6,
            center_x + trunk_width // 2, center_y + size // 6 + trunk_height
        ], fill=(80, 50, 30))
        
        # 树冠（3层圆形）
        foliage_colors = [(40, 80, 30), (60, 100, 45), (80, 120, 60)]
        radii = [size // 3, size // 4, size // 5]
        y_offsets = [0, -size // 8, -size // 6]
        
        for color, radius, y_offset in zip(foliage_colors, radii, y_offsets):
            draw.ellipse([
                center_x - radius, center_y + y_offset - radius,
                center_x + radius, center_y + y_offset + radius
            ], fill=color)
        
        return img
    
    def generate_all_sprites(self):
        """生成所有精灵"""
        print("🎨 开始生成CC2风格精灵...")
        
        # 创建目录结构
        units_dir = self.output_dir / 'units'
        allies_dir = units_dir / 'allies'
        axis_dir = units_dir / 'axis'
        vehicles_dir = units_dir / 'vehicles'
        buildings_dir = self.output_dir / 'buildings'
        terrain_dir = self.output_dir / 'terrain'
        
        for dir_path in [allies_dir, axis_dir, vehicles_dir, buildings_dir, terrain_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 生成盟军步兵
        print("  生成盟军步兵...")
        for i, unit_type in enumerate(['rifleman', 'mg_team', 'officer', 'engineer']):
            sprite = self.create_infantry_sprite('allied', size=32)
            sprite.save(allies_dir / f'{unit_type}.png')
        
        # 生成轴心国步兵
        print("  生成轴心国步兵...")
        for i, unit_type in enumerate(['rifleman', 'mg_team', 'officer', 'engineer']):
            sprite = self.create_infantry_sprite('axis', size=32)
            sprite.save(axis_dir / f'{unit_type}.png')
        
        # 生成坦克
        print("  生成坦克...")
        for faction in ['allied', 'axis']:
            for tank_type in ['light_tank', 'medium_tank', 'heavy_tank']:
                sprite = self.create_tank_sprite(faction, size=48)
                faction_dir = allies_dir if faction == 'allied' else axis_dir
                sprite.save(faction_dir / f'{tank_type}.png')
        
        # 生成载具
        print("  生成载具...")
        for vehicle_type in ['jeep', 'halftrack']:
            sprite = self.create_vehicle_sprite(vehicle_type, size=40)
            sprite.save(vehicles_dir / f'{vehicle_type}.png')
        
        # 生成建筑
        print("  生成建筑...")
        for building_type in ['house', 'barn', 'church']:
            sprite = self.create_building_sprite('house', size=64)
            sprite.save(buildings_dir / f'{building_type}.png')
        
        # 生成树木
        print("  生成树木...")
        tree = self.create_tree_sprite(size=48)
        tree.save(terrain_dir / 'tree.png')
        
        print(f"✅ 精灵生成完成！保存在: {self.output_dir}")


def main():
    """主函数"""
    # 输出到assets目录
    output_dir = Path(__file__).parent.parent / 'assets' / 'sprites'
    
    generator = CC2StyleSpriteGenerator(str(output_dir))
    generator.generate_all_sprites()
    
    print("\n📊 生成统计:")
    print(f"  - 盟军单位: 7个")
    print(f"  - 轴心国单位: 7个")
    print(f"  - 载具: 2个")
    print(f"  - 建筑: 3个")
    print(f"  - 地形: 1个")
    print(f"  总计: 20个精灵")


if __name__ == '__main__':
    main()
