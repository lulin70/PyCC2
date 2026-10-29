"""CombatLog Panel - Right-bottom combat log UI display.

Bug 2 修复：战斗日志面板（显示最近 20 条事件，支持滚动）
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2._archive.combat_log import CombatEvent


class CombatLogPanel:
    """右下角战斗日志面板。
    
    Features:
    - 显示最近 20 条战斗事件
    - 支持鼠标滚轮滚动查看历史
    - 半透明背景 + 小号字体
    - 自动裁剪超长文本
    
    CC2 Style:
    - 右下角固定位置
    - 黑色半透明背景（alpha 200）
    - 白色文本 + 彩色事件类型标记
    - 可滚动（鼠标滚轮）
    """
    
    # 布局常量
    PANEL_WIDTH = 350
    PANEL_HEIGHT = 200
    PANEL_PADDING = 10
    LINE_HEIGHT = 16
    FONT_SIZE = 11
    
    # 颜色
    BG_COLOR = (20, 20, 20)
    BG_ALPHA = 200
    TEXT_COLOR = (220, 220, 220)
    HEADER_COLOR = (255, 200, 50)
    
    # 事件类型颜色
    EVENT_COLORS = {
        "ATTACK": (255, 150, 0),    # 橙色
        "HIT": (255, 255, 100),     # 黄色
        "KILL": (255, 50, 50),      # 红色
        "MISS": (150, 150, 150),    # 灰色
        "SUPPRESSION": (200, 100, 200),  # 紫色
        "MORALE_CHANGE": (100, 200, 255),  # 蓝色
        "MOVEMENT": (100, 255, 100),  # 绿色
        "STATUS_CHANGE": (255, 255, 255),  # 白色
        "SPECIAL": (255, 200, 0),   # 金色
    }
    
    def __init__(self, screen_width: int, screen_height: int):
        """Initialize CombatLogPanel.
        
        Args:
            screen_width: Game screen width
            screen_height: Game screen height
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # 定位（右下角）
        self.x = screen_width - self.PANEL_WIDTH - 10
        self.y = screen_height - self.PANEL_HEIGHT - 10
        
        # 滚动状态
        self._scroll_offset = 0  # 向上滚动的行数
        self._max_visible_lines = (self.PANEL_HEIGHT - 2 * self.PANEL_PADDING - 20) // self.LINE_HEIGHT
        
        # 字体（lazy init）
        self._font: pygame.font.Font | None = None
        self._header_font: pygame.font.Font | None = None
        
        logger.info("CombatLogPanel initialized at (%d, %d)", self.x, self.y)
    
    def _ensure_fonts(self):
        """Ensure fonts are initialized."""
        if self._font is None:
            try:
                self._font = pygame.font.SysFont("monospace", self.FONT_SIZE, bold=False)
            except Exception:
                self._font = pygame.font.Font(None, self.FONT_SIZE)
        
        if self._header_font is None:
            try:
                self._header_font = pygame.font.SysFont("monospace", self.FONT_SIZE + 2, bold=True)
            except Exception:
                self._header_font = pygame.font.Font(None, self.FONT_SIZE + 2)
    
    def render(self, screen: pygame.Surface, events: list[CombatEvent]):
        """Render combat log panel.
        
        Args:
            screen: Pygame surface to render on
            events: List of CombatEvent to display (newest last)
        """
        self._ensure_fonts()
        
        # 绘制半透明背景
        panel_surf = pygame.Surface((self.PANEL_WIDTH, self.PANEL_HEIGHT))
        panel_surf.fill(self.BG_COLOR)
        panel_surf.set_alpha(self.BG_ALPHA)
        screen.blit(panel_surf, (self.x, self.y))
        
        # 绘制边框
        pygame.draw.rect(
            screen,
            (100, 100, 100),
            (self.x, self.y, self.PANEL_WIDTH, self.PANEL_HEIGHT),
            2
        )
        
        # 绘制标题
        header_text = self._header_font.render("COMBAT LOG", True, self.HEADER_COLOR)
        screen.blit(header_text, (self.x + self.PANEL_PADDING, self.y + 5))
        
        # 绘制事件列表（从下往上，最新的在最下面）
        if not events:
            no_events_text = self._font.render("No combat events yet", True, (150, 150, 150))
            screen.blit(
                no_events_text,
                (self.x + self.PANEL_PADDING, self.y + self.PANEL_PADDING + 25)
            )
            return
        
        # 计算可见事件范围（考虑滚动）
        total_events = len(events)
        start_idx = max(0, total_events - self._max_visible_lines - self._scroll_offset)
        end_idx = total_events - self._scroll_offset
        visible_events = events[start_idx:end_idx]
        
        # 渲染事件文本
        y_offset = self.y + self.PANEL_PADDING + 25
        for event in visible_events:
            # 获取事件类型颜色
            event_color = self.EVENT_COLORS.get(event.event_type.name, self.TEXT_COLOR)
            
            # 格式化事件文本
            text = event.format_short()
            
            # 裁剪超长文本
            max_chars = (self.PANEL_WIDTH - 2 * self.PANEL_PADDING) // 7  # 估算字符宽度
            if len(text) > max_chars:
                text = text[:max_chars - 3] + "..."
            
            # 渲染文本
            text_surf = self._font.render(text, True, event_color)
            screen.blit(text_surf, (self.x + self.PANEL_PADDING, y_offset))
            
            y_offset += self.LINE_HEIGHT
            
            # 防止溢出面板
            if y_offset > self.y + self.PANEL_HEIGHT - self.PANEL_PADDING:
                break
        
        # 绘制滚动指示器（如果有更多事件）
        if total_events > self._max_visible_lines:
            scroll_text = f"↑{self._scroll_offset}/{total_events - self._max_visible_lines}↓"
            scroll_surf = self._font.render(scroll_text, True, (200, 200, 200))
            screen.blit(
                scroll_surf,
                (self.x + self.PANEL_WIDTH - 60, self.y + 5)
            )
    
    def handle_scroll(self, delta: int):
        """Handle mouse scroll wheel.
        
        Args:
            delta: Scroll delta (positive = scroll up, negative = scroll down)
        """
        # 向上滚动（查看更早的事件）
        if delta > 0:
            self._scroll_offset = min(self._scroll_offset + 1, 100)  # 最多滚动 100 行
        # 向下滚动（返回最新事件）
        elif delta < 0:
            self._scroll_offset = max(self._scroll_offset - 1, 0)
    
    def reset_scroll(self):
        """Reset scroll to bottom (show latest events)."""
        self._scroll_offset = 0
    
    def is_mouse_over(self, mouse_pos: tuple[int, int]) -> bool:
        """Check if mouse is over the panel.
        
        Args:
            mouse_pos: Mouse position (x, y)
            
        Returns:
            True if mouse is inside panel bounds
        """
        mx, my = mouse_pos
        return (
            self.x <= mx <= self.x + self.PANEL_WIDTH
            and self.y <= my <= self.y + self.PANEL_HEIGHT
        )
