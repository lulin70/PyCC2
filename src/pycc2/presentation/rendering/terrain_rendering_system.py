"""
地形渲染系统 (Terrain Rendering System)

从 EnhancedRenderer 中提取的地形渲染逻辑。
负责统一管理简单地形、增强地形、地形过渡、边缘平滑等。

职责分离：
- EnhancedRenderer: 主渲染流程协调
- TerrainRenderingSystem: 地形细节渲染委托
- ProceduralTextureGenerator: 程序化纹理生成
- TerrainTileCache: 地形瓦片缓存

Created: v0.3.10 (extracted from enhanced_renderer.py ~620 lines)
"""

import logging
from typing import TYPE_CHECKING

import pygame

from pycc2.domain.value_objects.vec2 import Vec2

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.presentation.rendering.camera import Camera

logger = logging.getLogger(__name__)


class TerrainRenderingSystem:
    """
    统一地形渲染系统。

    封装所有地形相关的渲染逻辑，包括：
    - 简单纯色地形（稳定性优先）
    - 增强程序化地形（带纹理和光照）
    - 地形过渡渐变（不同地形类型间平滑过渡）
    - 边缘平滑处理（CC2风格自然边界）
    - 地形边框绘制（调试模式）

    使用示例:
        terrain_sys = TerrainRenderingSystem(renderer, tile_size=32)
        terrain_sys.draw_enhanced_terrain(game_map, camera, debug_mode=False)
    """

    # CC2 Classic Color Palette (verified accurate)
    TERRAIN_COLORS = {
        0: (76, 124, 35),    # OPEN/GRASS - CC2 exact military green #4C7C23
        1: (139, 119, 101),  # ROAD - dirt brown
        2: (58, 100, 24),     # GRASS - darker green #3A6418
        3: (45, 68, 33),      # WOODS - very dark forest green
        4: (139, 115, 85),    # BUILDING_ENTERABLE - earthy brown
        5: (120, 118, 115),   # BUILDING_SOLID - gray stone
        6: (62, 87, 117),     # WATER - muted blue
        7: (85, 70, 55),      # HEDGE - dark brown-green
        8: (110, 108, 105),   # WALL - gray brick
        9: (135, 115, 80),    # ROUGH - tan/brown
        10: (95, 145, 165),   # SHALLOW - light blue-green
        11: (160, 140, 100),  # BRIDGE - wooden brown
        12: (90, 85, 75),     # CRATER - dark gray-brown
    }

    # Base colors for terrain transition rendering
    TERRAIN_BASE_COLORS = {
        0: (76, 124, 35),     # GRASS
        1: (139, 119, 101),   # ROAD
        2: (58, 100, 24),     # DARK_GRASS
        3: (34, 51, 25),      # WOODS
        4: (139, 115, 85),    # BUILDING_ENTERABLE
        5: (120, 118, 115),   # BUILDING_SOLID
        6: (62, 87, 117),     # WATER
        7: (85, 70, 55),      # HEDGE
        8: (110, 108, 105),   # WALL
        9: (135, 115, 80),    # ROUGH
        10: (95, 145, 165),   # SHALLOW_WATER
        11: (160, 140, 100),  # BRIDGE
        12: (90, 85, 75),     # CRATER
    }

    def __init__(self, renderer, tile_size: int = 32):
        """
        初始化地形渲染系统。

        Args:
            renderer: EnhancedRenderer 实例（用于访问缓存和生成器）
            tile_size: 地图瓦片大小（像素）
        """
        self._renderer = renderer
        self.TILE_SIZE = tile_size
        
        # 缓存引用（从 renderer 获取）
        self._texture_cache = getattr(renderer, '_texture_cache', {})
        self._autotile_cache = getattr(renderer, '_autotile_cache', None)
        self._scaled_texture_cache = getattr(renderer, '_scaled_texture_cache', {})
        self._terrain_tile_cache = getattr(renderer, '_terrain_tile_cache', None)
        self._transition_cache = getattr(renderer, '_transition_cache', {})
        self._overlay_surface_pool: dict[tuple[int, int], pygame.Surface] = {}
        self._MAX_OVERLAY_SURFACE_POOL = 30

    def _get_overlay_surface(self, w: int, h: int) -> pygame.Surface:
        key = (w, h)
        if key in self._overlay_surface_pool:
            surf = self._overlay_surface_pool.pop(key)
            self._overlay_surface_pool[key] = surf
            surf.fill((0, 0, 0, 0))
            return surf
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        if len(self._overlay_surface_pool) >= self._MAX_OVERLAY_SURFACE_POOL:
            self._overlay_surface_pool.pop(next(iter(self._overlay_surface_pool)))
        self._overlay_surface_pool[key] = surf
        return surf

    def draw_simple_terrain(
        self, 
        game_map: 'GameMap', 
        camera: 'Camera',
        surface: pygame.Surface | None = None
    ) -> None:
        """
        使用简单纯色绘制地形 - 最大稳定性模式。

        使用预定义的 CC2 精确颜色，无任何程序化生成。
        这是经典的"256色时代"外观，非常稳定可靠。

        Args:
            game_map: 游戏地图
            camera: 相机对象
            surface: 目标渲染表面（可选，默认使用 offscreen）
        """
        target_surface = surface or self._renderer._offscreen
        if target_surface is None:
            return

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        tile_screen_size = int(self.TILE_SIZE * camera.zoom)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                try:
                    etile = self._get_enhanced_tile(game_map, tx, ty)
                    if etile is not None:
                        terrain_val = etile.base_terrain
                    else:
                        terrain_val = int(game_map.tile_grid[ty, tx])

                    terrain_val = max(0, min(12, terrain_val))
                    color = self.TERRAIN_COLORS.get(terrain_val, (128, 128, 128))

                    world_x = tx * self.TILE_SIZE
                    world_y = ty * self.TILE_SIZE

                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))

                    rect = pygame.Rect(
                        int(screen_pos[0]),
                        int(screen_pos[1]),
                        tile_screen_size,
                        tile_screen_size
                    )
                    pygame.draw.rect(target_surface, color, rect)

                except (AttributeError, ValueError) as e:
                    continue

    def get_cached_texture(self, terrain_id: int, variation: int) -> pygame.Surface:
        """获取或生成缓存的地形纹理。"""
        key = (terrain_id, variation)
        if key not in self._texture_cache:
            from pycc2.presentation.rendering.procedural_texture_generator import ProceduralTextureGenerator
            palette_gen = getattr(self._renderer, '_palette_gen', None)
            self._texture_cache[key] = ProceduralTextureGenerator.generate_terrain_texture(
                terrain_id, variation, palette_gen
            )
        return self._texture_cache[key]

    def get_cached_sprite(self, deco_type_name: str, variant: int = 0) -> pygame.Surface:
        """获取或生成缓存的装饰精灵。"""
        key = (deco_type_name, variant)
        sprite_cache = getattr(self._renderer, '_sprite_cache', {})
        
        if key not in sprite_cache:
            from pycc2.presentation.rendering.sprite_generator import SpriteGenerator
            sprite = SpriteGenerator.generate_decoration_sprite(deco_type_name, variant)
            sprite_cache[key] = sprite
            
        return sprite_cache[key]

    def draw_enhanced_terrain(
        self, 
        game_map: 'GameMap', 
        camera: 'Camera',
        debug_mode: bool = False,
        surface: pygame.Surface | None = None
    ) -> None:
        """
        使用增强的纹理化地形绘制（带高度光照和 autotile 支持）。

        这是主要的游戏画面地形渲染方法，支持：
        - 程序化纹理生成（12种地形类型 × 多种变体）
        - Autotile bitmask 连续地形连接
        - 高度基础光照调整
        - 缓存优化（避免重复生成）

        Args:
            game_map: 游戏地图
            camera: 相机对象
            debug_mode: 是否显示调试信息
            surface: 目标渲染表面（可选）
        """
        target_surface = surface or self._renderer._offscreen
        if target_surface is None:
            return

        bounds = camera.view_bounds
        start_x = max(0, int(bounds[0].x // self.TILE_SIZE))
        end_x = min(game_map.width, int((bounds[1].x // self.TILE_SIZE) + 2))
        start_y = max(0, int(bounds[0].y // self.TILE_SIZE))
        end_y = min(game_map.height, int((bounds[1].y // self.TILE_SIZE) + 2))

        tile_screen_size = int(self.TILE_SIZE * camera.zoom)

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                try:
                    enhanced_tile = self._get_enhanced_tile(game_map, tx, ty)
                    
                    if enhanced_tile is not None and hasattr(enhanced_tile, 'base_terrain'):
                        terrain_val = enhanced_tile.base_terrain
                        height = getattr(enhanced_tile, 'height', 0) or 0
                    else:
                        terrain_val = int(game_map.tile_grid[ty, tx])
                        height = 0

                    # Calculate autotile bitmask for continuous terrains
                    from pycc2.presentation.rendering.autotile_system import (
                        is_autotile_terrain,
                        get_neighbor_bitmap
                    )
                    
                    bitmask = 0
                    if is_autotile_terrain(terrain_val):
                        try:
                            bitmask = get_neighbor_bitmap(game_map, tx, ty, terrain_val)
                        except Exception as e:
                            logger.debug(f"Autotile bitmask failed: {e}")

                    # Use TerrainTileCache for pre-computed tiles with edge smoothing
                    texture = None
                    if self._terrain_tile_cache is not None:
                        texture = self._terrain_tile_cache.get_tile(
                            terrain_type=terrain_val,
                            variation=(tx * 7919 + ty * 104729 + terrain_val * 17) % 8,
                            height=height,
                            size=tile_screen_size,
                            bitmask=bitmask if is_autotile_terrain(terrain_val) else None
                        )

                    if texture is None:
                        # Fallback to procedural generation with caching
                        variation = (tx * 7919 + ty * 104729 + terrain_val * 17) % 8
                        
                        if is_autotile_terrain(terrain_val):
                            cache_key = (terrain_val, variation, bitmask)
                            
                            cached = self._autotile_cache.get_variant(terrain_val, bitmask, variation) \
                                if self._autotile_cache else None
                                
                            if cached is None:
                                texture = self._generate_cc2_style_tile(terrain_val, tx, ty, bitmask)
                                if self._autotile_cache:
                                    self._autotile_cache.set_variant(terrain_val, bitmask, variation, texture)
                            else:
                                texture = cached
                            
                            scale_key = (terrain_val, variation, bitmask, tile_screen_size)
                            if scale_key not in self._scaled_texture_cache and texture is not None:
                                base_texture = self._autotile_cache.get_variant(terrain_val, bitmask, variation) \
                                    if self._autotile_cache else None
                                if base_texture is not None:
                                    import math
                                    scale_factor = tile_screen_size / base_texture.get_width()
                                    new_size = (int(base_texture.get_width() * scale_factor),
                                              int(base_texture.get_height() * scale_factor))
                                    self._scaled_texture_cache[scale_key] = pygame.transform.smoothscale(base_texture, new_size)
                                texture = self._scaled_texture_cache.get(scale_key)
                        else:
                            cache_key = (terrain_val, variation, height, tile_screen_size)
                            
                            if cache_key not in self._scaled_texture_cache:
                                base_texture = self.get_cached_texture(terrain_val, variation)
                                
                                if height > 0:
                                    lighting_sys = getattr(self._renderer, '_lighting_effects_sys', None)
                                    if lighting_sys:
                                        base_texture = lighting_sys.apply_height_lighting(base_texture, height)
                                
                                import math
                                scale_factor = tile_screen_size / base_texture.get_width()
                                new_size = (int(base_texture.get_width() * scale_factor),
                                          int(base_texture.get_height() * scale_factor))
                                self._scaled_texture_cache[cache_key] = pygame.transform.smoothscale(base_texture, new_size)
                            
                            texture = self._scaled_texture_cache.get(cache_key)
                        
                        if texture is None:
                            texture = self.get_cached_texture(terrain_val, variation)

                    # Blit terrain tile to screen
                    if texture is not None:
                        world_x = tx * self.TILE_SIZE
                        world_y = ty * self.TILE_SIZE

                        screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        target_surface.blit(texture, (sx, sy))

                except Exception as e:
                    logger.debug(f"Terrain render failed at ({tx},{ty}): {e}")
                    continue

        # Apply terrain edge smoothing
        self.apply_terrain_edge_smoothing(game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size)
        
        # Render terrain transitions between different types
        self.render_terrain_transitions(game_map, camera, start_x, end_x, start_y, end_y, tile_screen_size)
        
        # Draw terrain borders only in debug mode
        if debug_mode:
            self.draw_terrain_borders(game_map, camera, start_x, end_x, start_y, end_y)

    def _get_enhanced_tile(self, game_map: 'GameMap', x: int, y: int):
        """获取增强地形瓦片数据（兼容新旧格式）。"""
        try:
            if hasattr(game_map, 'get_enhanced_tile'):
                return game_map.get_enhanced_tile(x, y)
            
            terrain_id = int(game_map.tile_grid[y, x])
            height = 0
            if hasattr(game_map, 'height_map') and game_map.height_map is not None:
                height = int(game_map.height_map[y, x])
                
            from pycc2.domain.entities.enhanced_tile import EnhancedTile
            return EnhancedTile(
                base_terrain=terrain_id,
                height=height,
                variation=0,
                decoration=None
            )
        except (IndexError, AttributeError) as e:
            logger.debug(f"Failed to get enhanced tile at ({x},{y}): {e}")
            return None

    def get_terrain_at(self, game_map: 'GameMap', x: int, y: int) -> int:
        """获取指定坐标的地形类型，越界返回 -1。"""
        if x < 0 or y < 0 or x >= game_map.width or y >= game_map.height:
            return -1
            
        etile = self._get_enhanced_tile(game_map, x, y)
        if etile is not None and hasattr(etile, 'base_terrain'):
            return etile.base_terrain
            
        try:
            return int(game_map.tile_grid[y, x])
        except (IndexError, AttributeError):
            return -1

    def _generate_cc2_style_tile(
        self, 
        terrain_id: int, 
        tile_x: int, 
        tile_y: int, 
        bitmask: int = 0
    ) -> pygame.Surface:
        """
        生成 CC2 风格的 48×48 地形瓦片（支持 autotile）。

        Args:
            terrain_id: 地形类型 ID (0-12)
            tile_x: 瓦片 X 坐标（用于种子变化）
            tile_y: 瓦片 Y 坐标（用于种子变化）
            bitmask: Autotile 位掩码（0 = 无 autotile）

        Returns:
            48×48 像素的 Pygame Surface
        """
        variation = tile_x * 7919 + tile_y * 104729 + terrain_id * 17
        
        from pycc2.presentation.rendering.procedural_texture_generator import ProceduralTextureGenerator
        palette_gen = getattr(self._renderer, '_palette_gen', None)
        
        return ProceduralTextureGenerator.generate_terrain_texture(
            terrain_id,
            variation % 8,
            palette_gen,
            size=48,
            bitmask=bitmask if bitmask > 0 else None
        )

    def render_terrain_transitions(
        self, 
        game_map: 'GameMap', 
        camera: 'Camera',
        start_x: int, end_x: int, start_y: int, end_y: int,
        tile_screen_size: int
    ) -> None:
        """
        渲染不同地形类型间的梯度过渡条带。

        在相邻的不同地形类型之间绘制 4-6px 的渐变条，
        使地形边界看起来更自然，而不是生硬的直线。

        性能优化：使用缓存避免重复计算。

        Args:
            game_map: 游戏地图
            camera: 相机对象
            start_x/end_x/start_y/end_y: 可见区域范围
            tile_screen_size: 屏幕上瓦片的大小
        """
        target_surface = self._renderer._offscreen
        if target_surface is None:
            return

        directions = [
            ('right', 1, 0),
            ('bottom', 0, 1),
            ('left', -1, 0),
            ('top', 0, -1)
        ]

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                current = self.get_terrain_at(game_map, tx, ty)
                if current < 0:
                    continue

                for direction_name, dx, dy in directions:
                    nx, ny = tx + dx, ty + dy
                    
                    if nx < start_x or nx >= end_x or ny < start_y or ny >= end_y:
                        continue
                    
                    neighbor = self.get_terrain_at(game_map, nx, ny)
                    if neighbor < 0 or neighbor == current:
                        continue

                    cache_key = (tx, ty, current, neighbor, direction_name)
                    
                    if cache_key in self._transition_cache:
                        strip, rect = self._transition_cache[cache_key]
                        target_surface.blit(strip, rect.topleft)
                        continue

                    color_from = self.TERRAIN_BASE_COLORS.get(current, (128, 128, 128))
                    color_to = self.TERRAIN_BASE_COLORS.get(neighbor, (128, 128, 128))

                    middle_color = (
                        (color_from[0] + color_to[0]) // 2,
                        (color_from[1] + color_to[1]) // 2,
                        (color_from[2] + color_to[2]) // 2
                    )

                    world_x = tx * self.TILE_SIZE
                    world_y = ty * self.TILE_SIZE
                    screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                    sx, sy = int(screen_pos[0]), int(screen_pos[1])

                    strip_width = max(4, tile_screen_size // 8)
                    strip = pygame.Surface((strip_width, tile_screen_size), pygame.SRCALPHA)

                    for i in range(strip_width):
                        t = i / strip_width
                        r = int(color_from[0] * (1-t) + middle_color[0] * t)
                        g = int(color_from[1] * (1-t) + middle_color[1] * t)
                        b = int(color_from[2] * (1-t) + middle_color[2] * t)
                        pygame.draw.line(strip, (r, g, b, 180), (i, 0), (i, tile_screen_size))

                    if direction_name == 'right':
                        rect = pygame.Rect(sx + tile_screen_size - strip_width, sy, strip_width, tile_screen_size)
                    elif direction_name == 'bottom':
                        strip = pygame.transform.rotate(strip, 90)
                        rect = pygame.Rect(sx, sy + tile_screen_size - strip_width, tile_screen_size, strip_width)
                    elif direction_name == 'left':
                        strip = pygame.transform.flip(strip, True, False)
                        rect = pygame.Rect(sx, sy, strip_width, tile_screen_size)
                    else:  # top
                        strip = pygame.transform.rotate(strip, -90)
                        rect = pygame.Rect(sx, sy, tile_screen_size, strip_width)

                    target_surface.blit(strip, rect.topleft)
                    self._transition_cache[cache_key] = (strip, rect)

    def apply_terrain_edge_smoothing(
        self,
        game_map: 'GameMap',
        camera: 'Camera',
        start_x: int, end_x: int, start_y: int, end_y: int,
        tile_screen_size: int
    ) -> None:
        """
        在不同地形类型之间应用微妙的边缘平滑处理。

        创建 2-3 像素宽的半透明叠加层在地形边界处，
        使地形过渡更自然（类似 CC2 的视觉效果）。

        只处理非 autotile 地形边界（草地-泥土、草地-道路等），
        跳过 autotile 地形（它们自己处理边缘）。

        Args:
            game_map: 游戏地图
            camera: 相机对象
            start_x/end_x/start_y/end_y: 可见范围
            tile_screen_size: 瓦片屏幕尺寸
        """
        target_surface = self._renderer._offscreen
        if target_surface is None:
            return

        from pycc2.presentation.rendering.autotile_system import is_autotile_terrain
        
        autotile_terrains = {5, 6, 7}
        smooth_transitions = [(0, 1), (0, 9), (1, 9), (2, 0)]

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                current = self.get_terrain_at(game_map, tx, ty)
                if current < 0 or current in autotile_terrains:
                    continue

                for neighbor_terrain, target_terrain in smooth_transitions:
                    if current != neighbor_terrain:
                        continue

                    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                        nx, ny = tx + dx, ty + dy
                        
                        if nx < start_x or nx >= end_x or ny < start_y or ny >= end_y:
                            continue
                            
                        neighbor = self.get_terrain_at(game_map, nx, ny)
                        if neighbor != target_terrain:
                            continue

                        world_x = tx * self.TILE_SIZE
                        world_y = ty * self.TILE_SIZE
                        screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                        sx, sy = int(screen_pos[0]), int(screen_pos[1])

                        edge_width = max(2, tile_screen_size // 16)
                        overlay = self._get_overlay_surface(edge_width, tile_screen_size)
                        overlay.fill((255, 255, 255, 30))

                        if dx == 1:
                            target_surface.blit(overlay, (sx + tile_screen_size - edge_width, sy),
                                               special_flags=pygame.BLEND_RGBA_MULT)
                        elif dx == -1:
                            target_surface.blit(overlay, (sx, sy),
                                               special_flags=pygame.BLEND_RGBA_MULT)
                        elif dy == 1:
                            overlay = self._get_overlay_surface(tile_screen_size, edge_width)
                            overlay.fill((255, 255, 255, 30))
                            target_surface.blit(overlay, (sx, sy + tile_screen_size - edge_width),
                                               special_flags=pygame.BLEND_RGBA_MULT)
                        else:
                            overlay = self._get_overlay_surface(tile_screen_size, edge_width)
                            overlay.fill((255, 255, 255, 30))
                            target_surface.blit(overlay, (sx, sy),
                                               special_flags=pygame.BLEND_RGBA_MULT)

    def draw_terrain_borders(
        self,
        game_map: 'GameMap',
        camera: 'Camera',
        start_x: int, end_x: int, start_y: int, end_y: int
    ) -> None:
        """
        在调试模式下绘制地形类型边界线。

        用于可视化验证地形分配是否正确。
        仅在 debug_mode=True 时调用。

        Args:
            game_map: 游戏地图
            camera: 相机对象
            start_x/end_x/start_y/end_y: 可见范围
        """
        target_surface = self._renderer._offscreen
        if target_surface is None:
            return

        for ty in range(start_y, end_y):
            for tx in range(start_x, end_x):
                current = self.get_terrain_at(game_map, tx, ty)
                if current < 0:
                    continue

                neighbors_different = False
                for dx, dy in [(1, 0), (0, 1)]:
                    nx, ny = tx + dx, ty + dy
                    if 0 <= nx < game_map.width and 0 <= ny < game_map.height:
                        neighbor = self.get_terrain_at(game_map, nx, ny)
                        if neighbor >= 0 and neighbor != current:
                            neighbors_different = True
                            break
                
                if not neighbors_different:
                    continue

                world_x = tx * self.TILE_SIZE
                world_y = ty * self.TILE_SIZE
                screen_pos = camera.world_to_screen(Vec2(world_x, world_y))
                sx, sy = int(screen_pos[0]), int(screen_pos[1])

                tile_screen_size = int(self.TILE_SIZE * camera.zoom)
                
                border_color = {
                    0: (50, 150, 50),   # Grass: Green
                    1: (150, 100, 50),   # Road: Brown
                    2: (40, 120, 40),    # Dark grass: Dark green
                    6: (50, 80, 150),    # Water: Blue
                }.get(current, (200, 200, 200))

                border_rect = pygame.Rect(sx, sy, tile_screen_size, tile_screen_size)
                pygame.draw.rect(target_surface, border_color, border_rect, 1)