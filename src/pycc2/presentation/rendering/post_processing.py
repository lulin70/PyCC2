"""Post-processing effects: vignette, color grading."""

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

        PF-01: grading now runs in place on the screen surface. The previous
        version copied the full frame and allocated several float arrays. That
        cost ~18 ms per frame at 1024x768.

        Args:
            surface: 原始surface
            style: 风格 ("war", "cold", "warm")

        """
        if not self.color_grading_enabled:
            return surface

        if style == "war":
            # 战争风格：降低饱和度，增加对比度
            self._apply_desaturation(surface, 0.3)
        elif style == "cold":
            # 冷色调：增加蓝色
            self._apply_color_tint(surface, (0, 0, 20))
        elif style == "warm":
            # 暖色调：增加红黄
            self._apply_color_tint(surface, (20, 10, 0))

        return surface

    def _apply_desaturation(self, surface: Surface, amount: float):
        """降低饱和度，模拟CC2灰暗战争氛围。

        PF-01: use pygame's C-level grayscale + alpha blend when available.

        Args:
            surface: 目标Surface
            amount: 去饱和度程度 0.0(原色) ~ 1.0(完全灰度)，推荐值 0.3-0.5

        """
        alpha = int(round(max(0.0, min(1.0, amount)) * 255))
        grayscale = getattr(pygame.transform, "grayscale", None)
        if grayscale is not None:
            width, height = surface.get_size()
            # PF-01: grayscale of a 1024x768 frame costs ~8 ms. Computing it at
            # quarter resolution costs ~1 ms. The result is blended at low
            # opacity, so the difference is not visible.
            if width >= 512 and height >= 384:
                small = pygame.transform.smoothscale(surface, (width // 8, height // 8))
                gray = grayscale(small)
                gray = pygame.transform.smoothscale(gray, (width, height))
            else:
                gray = grayscale(surface)
            gray.set_alpha(alpha)
            surface.blit(gray, (0, 0))
            return

        # Fallback for older pygame builds without transform.grayscale.
        pixels = pygame.surfarray.pixels3d(surface)
        # 使用人眼感知加权灰度公式
        gray_arr = 0.299 * pixels[:, :, 0] + 0.587 * pixels[:, :, 1] + 0.114 * pixels[:, :, 2]
        # 按amount混合原色和灰色
        result = pixels * (1 - amount) + gray_arr[:, :, np.newaxis] * amount
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
