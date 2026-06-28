"""Post-processing effects: vignette, color grading.
"""

from __future__ import annotations

import logging
import math

import numpy as np
import pygame
from pygame import Surface

logger = logging.getLogger(__name__)


class PostProcessingEffects:
    """屏幕后处理效果"""

    def __init__(self, screen_width: int, screen_height: int):
        """Initialize the PostProcessingEffects."""
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.vignette_surface: Surface | None = None
        self.color_grading_enabled = False
        self.vignette_enabled = False

    def enable_vignette(self, intensity: float = 0.5):
        """启用暗角效果"""
        self.vignette_enabled = True
        self._create_vignette(intensity)

    def disable_vignette(self):
        """禁用暗角效果"""
        self.vignette_enabled = False

    def _create_vignette(self, intensity: float = 0.5):
        """创建暗角遮罩"""
        self.vignette_surface = Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
        self.vignette_surface.fill((0, 0, 0, 0))  # 透明背景

        center_x = self.screen_width // 2
        center_y = self.screen_height // 2
        max_radius = math.sqrt(center_x**2 + center_y**2)

        # 创建径向渐变（简化版本，只绘制边缘）
        # 为了性能，使用圆形绘制而不是逐像素
        steps = 50
        for i in range(steps):
            progress = i / steps
            radius = int(max_radius * (1 - progress))
            alpha = int(255 * (progress**2) * intensity)
            alpha = max(0, min(255, alpha))
            color = (0, 0, 0, alpha)
            pygame.draw.circle(self.vignette_surface, color, (center_x, center_y), radius, 2)

    def enable_color_grading(self):
        """启用色彩分级"""
        self.color_grading_enabled = True

    def disable_color_grading(self):
        """禁用色彩分级"""
        self.color_grading_enabled = False

    def apply_color_grading(self, surface: Surface, style: str = "war") -> Surface:
        """应用色彩分级

        Args:
            surface: 原始surface
            style: 风格 ("war", "cold", "warm")

        """
        if not self.color_grading_enabled:
            return surface

        result = surface.copy()

        if style == "war":
            # 战争风格：降低饱和度，增加对比度
            self._apply_desaturation(result, 0.3)
        elif style == "cold":
            # 冷色调：增加蓝色
            self._apply_color_tint(result, (0, 0, 20))
        elif style == "warm":
            # 暖色调：增加红黄
            self._apply_color_tint(result, (20, 10, 0))

        return result

    def _apply_desaturation(self, surface: Surface, amount: float):
        """降低饱和度，模拟CC2灰暗战争氛围。

        Args:
            surface: 目标Surface
            amount: 去饱和度程度 0.0(原色) ~ 1.0(完全灰度)，推荐值 0.3-0.5

        """
        pixels = pygame.surfarray.pixels3d(surface)
        # 使用人眼感知加权灰度公式
        gray = 0.299 * pixels[:, :, 0] + 0.587 * pixels[:, :, 1] + 0.114 * pixels[:, :, 2]
        # 按amount混合原色和灰色
        result = pixels * (1 - amount) + gray[:, :, np.newaxis] * amount
        pixels[:] = np.clip(result, 0, 255).astype(np.uint8)
        del pixels  # 释放锁

    def _apply_color_tint(self, surface: Surface, tint: tuple[int, int, int]):
        """应用色调"""
        # 创建色调层
        tint_surface = Surface(surface.get_size())
        tint_surface.fill(tint)
        tint_surface.set_alpha(30)
        surface.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def apply_vignette(self, surface: Surface):
        """应用暗角效果"""
        if self.vignette_enabled and self.vignette_surface:
            surface.blit(self.vignette_surface, (0, 0))

    def apply_all(self, surface: Surface, color_style: str = "war") -> Surface:
        """应用所有后处理效果"""
        result = surface

        if self.color_grading_enabled:
            result = self.apply_color_grading(result, color_style)

        if self.vignette_enabled:
            self.apply_vignette(result)

        return result
