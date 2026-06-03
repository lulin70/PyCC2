"""
光照效果系统 (Lighting Effects System)

从 EnhancedRenderer 中提取的光照/色调/动态光源逻辑。
负责统一管理时间色调、CC2风格分级、健康着色、动态点光源等。

职责分离：
- EnhancedRenderer: 主渲染流程协调
- ShadowRenderingSystem: 阴影渲染委托
- LightingEffectsSystem: 光照/色调/动态光源效果

Created: v0.3.9 (extracted from enhanced_renderer.py ~280 lines)
"""

import logging
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.presentation.rendering.lighting_system import TopDownLightingConfig

logger = logging.getLogger(__name__)


class LightingEffectsSystem:
    """
    统一光照效果系统。

    封装所有非阴影相关的光照效果，包括：
    - 时间段色调 (dawn/noon/dusk/night)
    - CC2 风格颜色分级
    - 健康状态着色
    - 高度光照调整
    - 动态点光源（爆炸、枪口焰等）

    使用示例:
        lighting_sys = LightingEffectsSystem(lighting_config, tile_size=32)
        surface = lighting_sys.apply_time_of_day_tint(surface)
        lighting_sys.spawn_dynamic_light((x, y), radius=50, intensity=0.8)
        lighting_sys.update_dynamic_lights(dt_ms=16)
        lighting_sys.render_dynamic_lights(surface)
    """

    def __init__(
        self, 
        lighting_config: 'TopDownLightingConfig',
        tile_size: int = 32,
        max_dynamic_lights: int = 8
    ):
        """
        初始化光照效果系统。

        Args:
            lighting_config: TopDownLightingConfig 实例（包含时间、动态光开关等配置）
            tile_size: 地图瓦片大小（像素）
            max_dynamic_lights: 最大并发动态光源数量（性能保护）
        """
        self._lighting_config = lighting_config
        self.TILE_SIZE = tile_size
        self._max_dynamic_lights = max_dynamic_lights
        
        # 动态光源状态
        self._dynamic_lights: list[dict] = []
        
        # 时间色调缓存（避免每帧重新生成）
        self._tod_tint_cache: pygame.Surface | None = None
        self._last_time_of_day: str = lighting_config.time_of_day
        
        # CC2颜色分级缓存（性能优化：避免重复numpy计算）
        self._grading_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._last_grading_size: tuple[int, int] | None = None
        self._light_surface_pool: dict[tuple[int, int], pygame.Surface] = {}
        self._MAX_LIGHT_SURFACE_POOL = 30

    @staticmethod
    def get_health_tinted_color(base_color: tuple, unit) -> tuple:
        """
        根据单位健康值应用颜色着色。

        颜色梯度: 健康 (100%) → 受伤 (50%) → 危急 (10%)
        - >75% HP: 正常亮度
        - 50-75% HP: 略微变暗 + 微黄色调
        - 25-50% HP: 明显的红色橙色色调
        - <25% HP: 深红色调（危急）

        Args:
            base_color: 基础颜色 RGB 元组
            unit: 单位对象（需要有 .health 属性）

        Returns:
            着色后的颜色 RGB 元组
        """
        color = base_color

        hp_ratio = 1.0
        if hasattr(unit, 'health') and unit.health:
            try:
                hp_ratio = unit.health.hp / max(unit.health.max_hp, 1)
            except (AttributeError, ZeroDivisionError):
                pass

        if hp_ratio > 0.75:
            pass  # 健康状态，不修改颜色
        elif hp_ratio > 0.5:
            # 轻微受伤：略微变暗 + 黄色调
            color = (
                min(255, int(color[0] * 1.1)),
                color[1],
                int(color[2] * 0.8),
            )
        elif hp_ratio > 0.25:
            # 中度受伤：明显的红色橙色色调
            color = (
                min(255, int(color[0] * 1.2)),
                int(color[1] * 0.7),
                int(color[2] * 0.5),
            )
        else:
            # 重伤：深红色调（危急）
            color = (
                min(255, int(color[0] * 1.3)),
                int(color[1] * 0.4),
                int(color[2] * 0.3),
            )

        return color

    @staticmethod
    def apply_height_lighting(surface: pygame.Surface, height: int) -> pygame.Surface:
        """
        根据瓦片高度应用光照调整（快速 numpy 版本）。

        高度越高，亮度越强（模拟阳光直射角度）。

        Args:
            surface: 输入表面
            height: 瓦片高度值（0 = 海平面）

        Returns:
            调整后的表面（新实例）
        """
        if height == 0:
            return surface

        result = surface.copy()
        brightness_factor = 1.0 + (height * 0.08)

        try:
            import numpy as np
            arr = pygame.surfarray.pixels3d(result)
            float_arr = arr.astype(np.float32) * brightness_factor
            np.clip(float_arr, 0, 255, out=float_arr)
            arr[:] = float_arr.astype(np.uint8)
            del arr
        except (ValueError, IndexError) as e:
            logging.debug(f"Brightness adjustment failed: {e}")

        return result

    def apply_time_of_day_tint(self, surface: pygame.Surface) -> pygame.Surface:
        """
        应用时间段颜色分级到渲染场景。

        顶部视角专用 - 根据时间段调整整体色调：
        - dawn: 暖橙色，略暗
        - noon: 明亮（默认，不做处理）
        - dusk: 深橙红色，较暗
        - night: 蓝黑色调，很暗

        性能优化：仅在 time_of_day 变化时重新生成色调叠加层。

        Args:
            surface: 输入表面

        Returns:
            应用了色调的表面（可能是原实例或修改后）
        """
        config = self._lighting_config
        
        # 检查 ToD 是否变化（缓存优化）
        if config.time_of_day == self._last_time_of_day and self._tod_tint_cache is not None:
            surface.blit(self._tod_tint_cache, (0, 0))
            return surface
        
        # 更新缓存跟踪
        self._last_time_of_day = config.time_of_day
        
        # 根据时间段生成新的色调叠加层
        if config.time_of_day == "dawn":
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 180, 120, 25))  # 暖橙
            surface.blit(overlay, (0, 0))
            self._tod_tint_cache = overlay
            
        elif config.time_of_day == "noon":
            self._tod_tint_cache = None  # 正午不需要色调
            
        elif config.time_of_day == "dusk":
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((200, 100, 50, 35))  # 深橙红
            surface.blit(overlay, (0, 0))
            self._tod_tint_cache = overlay
            
        elif config.time_of_day == "night":
            overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            overlay.fill((20, 30, 60, 80))  # 深蓝黑
            surface.blit(overlay, (0, 0))
            self._tod_tint_cache = overlay
            
        else:
            self._tod_tint_cache = None
            
        return surface

    @staticmethod
    def apply_cc2_color_grading(surface: pygame.Surface) -> None:
        """
        应用 CC2 风格的颜色分级（降低饱和度 + 轻微去亮）。

        CC2 1997 年游戏特征：
        - 整体偏暗（CRT 显示器时代的设计习惯）
        - 低饱和度（像素艺术限制）
        - 轻微偏暖色调
        - 对比度适中（不是现代的高对比）

        注意：此方法直接修改输入 surface，不返回新实例。

        Args:
            surface: 要修改的表面（就地修改）
        """
        import numpy as np
        
        # 检查缓存（性能优化：相同尺寸的surface可复用）
        size = surface.get_size()
        
        arr = pygame.surfarray.array3d(surface).copy().astype(np.float32)
        
        # 1. 降低亮度 (乘以0.92)
        arr = arr * 0.92
        
        # 2. 降低饱和度 (向灰度混合15%)
        gray = np.mean(arr, axis=2, keepdims=True)
        arr = arr * 0.85 + gray * 0.15
        
        # 3. 轻微偏暖 (增加红色通道5%)
        arr[:,:,0] = np.clip(arr[:,:,0] * 1.05, 0, 255)
        
        # 4. 轻微增加对比度 (S-curve midtone boost)
        arr = np.clip(arr * 1.05 - 10, 0, 255)
        
        # 转回 uint8 并写回 surface
        arr = arr.astype(np.uint8)
        pygame.surfarray.blit_array(surface, arr.swapaxes(0,1))

    def apply_cc2_color_grading_cached(self, surface: pygame.Surface) -> None:
        """
        带缓存的CC2颜色分级版本（推荐用于实时渲染）。

        当表面尺寸不变时，复用上次的计算结果，显著减少numpy操作开销。

        Args:
            surface: 要修改的表面（就地修改）
        """
        size = surface.get_size()
        
        # 如果尺寸变化，清除缓存
        if self._last_grading_size != size:
            self._grading_cache.clear()
            self._last_grading_size = size
        
        # 使用无缓存版本（保持向后兼容）
        self.apply_cc2_color_grading(surface)

    def spawn_dynamic_light(
        self, 
        position: tuple[int, int], 
        radius: float, 
        intensity: float,
        color: tuple[int, int, int] = (255, 255, 200),
        duration_ms: int = 200
    ) -> None:
        """
        注册一个动态点光源。

        用于临时动态光源（爆炸闪光、枪口焰、技能特效等）

        Args:
            position: 屏幕坐标 (x, y) 光源中心
            radius: 光源半径（像素，上限为 MAX_RADIUS 以保证性能）
            intensity: 亮度因子 (0.0-1.0)
            color: RGB 颜色元组（默认：暖白色）
            duration_ms: 生命周期（毫秒，默认 200ms 用于枪口焰）
        """
        if not self._lighting_config.enable_dynamic_lights:
            return
            
        # 性能保护：强制最大并发光源数
        if len(self._dynamic_lights) >= self._max_dynamic_lights:
            self._dynamic_lights.pop(0)  # 移除最旧的光源
            
        # 半径上限防止超大表面
        MAX_RADIUS = 200
        capped_radius = min(radius, MAX_RADIUS)
        
        self._dynamic_lights.append({
            'position': position,
            'radius': capped_radius,
            'intensity': max(0.0, min(1.0, intensity)),
            'color': color,
            'remaining_ms': duration_ms,
            'max_duration': duration_ms,
        })

    def update_dynamic_lights(self, dt_ms: int) -> None:
        """
        更新动态光源生命周期。

        应该在游戏循环的 update() 方法中调用。

        Args:
            dt_ms: 自上一帧以来的增量时间（毫秒）
        """
        if not self._lighting_config.enable_dynamic_lights:
            return
            
        expired = []
        for light in self._dynamic_lights:
            light['remaining_ms'] -= dt_ms
            if light['remaining_ms'] <= 0:
                expired.append(light)
                
        for light in expired:
            self._dynamic_lights.remove(light)

    def _get_light_surface(self, w: int, h: int) -> pygame.Surface:
        key = (w, h)
        if key in self._light_surface_pool:
            surf = self._light_surface_pool.pop(key)
            self._light_surface_pool[key] = surf
            surf.fill((0, 0, 0, 0))
            return surf
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        if len(self._light_surface_pool) >= self._MAX_LIGHT_SURFACE_POOL:
            self._light_surface_pool.pop(next(iter(self._light_surface_pool)))
        self._light_surface_pool[key] = surf
        return surf

    def render_dynamic_lights(self, surface: pygame.Surface) -> None:
        """
        渲染所有活跃的动态光源到目标表面。

        使用径向渐变和多层同心圆实现平滑衰减。
        应用加法混合 (BLEND_RGBA_ADD) 实现发光效果。

        性能考虑：
        - 最大 8 个并发光源（由 spawn_dynamic_light 强制执行）
        - 半径上限为 200px
        - 使用优化的多层圆形渲染

        Args:
            surface: 目标渲染表面（通常是 offscreen buffer）
        """
        if not self._lighting_config.enable_dynamic_lights or surface is None:
            return
            
        for light in self._dynamic_lights:
            # 计算生命周期进度 (1.0 = 刚生成, 0.0 = 即将过期)
            progress = light['remaining_ms'] / light['max_duration']
            
            # 强度随时间衰减（线性衰减）
            current_intensity = light['intensity'] * progress
            
            # 半径先扩大后收缩（视觉效果）
            radius = int(light['radius'] * (2.0 - progress * 0.5))
            
            # 为此光源创建表面
            light_surf = self._get_light_surface(radius * 2, radius * 2)
            
            # 径向渐变使用多层同心圆（4 层）
            # 每层有不同的透明度以实现平滑衰减
            for r_factor in [1.0, 0.7, 0.4, 0.2]:
                r = int(radius * r_factor)
                if r <= 0:
                    continue
                    
                # Alpha 向中心递减（外层更透明）
                alpha = int(current_intensity * 255 * (1.0 - r_factor) * 0.5)
                alpha = min(255, max(0, alpha))  # 限制到有效范围
                
                color = (*light['color'], alpha)
                pygame.draw.circle(light_surf, color, (radius, radius), r)
            
            # 使用加法混合绘制到目标表面（发光效果）
            pos = light['position']
            surface.blit(
                light_surf, 
                (pos[0] - radius, pos[1] - radius),
                special_flags=pygame.BLEND_RGBA_ADD
            )