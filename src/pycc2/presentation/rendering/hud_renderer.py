"""HUD Renderer - 游戏抬头显示(Head-Up Display)渲染

负责：
- Status Bar（顶部状态栏：FPS、单位信息、回合数）
- Minimap（右下角战术地图）
- Keyboard Shortcuts Help（按H显示）

设计：
- 与UIOverlayRenderer分离（不影响现有VL/攻击线渲染）
- 性能预算：< 5ms/frame
- 组件可独立开关
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.camera import Camera

logger = logging.getLogger(__name__)


class HUDRenderer:
    """HUD渲染器 - 管理Status Bar、Minimap、Shortcuts Help"""

    def __init__(self):
        """初始化HUD渲染器"""
        # UI组件开关
        self.enable_minimap = True
        self.enable_status_bar = True
        self.enable_shortcuts_help = False  # 默认关闭，按H显示

        # 性能统计
        self._ui_render_time_ms = 0.0

        # 字体（延迟初始化）
        self._font_small = None
        self._font_medium = None
        self._font_large = None
        self._fonts_initialized = False

        # P0-2 Phase 2: Minimap渲染器
        from pycc2.presentation.rendering.minimap_renderer import MinimapRenderer

        self._minimap_renderer = MinimapRenderer(size=200)

    def _init_fonts(self) -> None:
        """延迟初始化字体（避免pygame未初始化错误）"""
        if self._fonts_initialized:
            return

        try:
            self._font_small = pygame.font.Font(None, 16)
            self._font_medium = pygame.font.Font(None, 20)
            self._font_large = pygame.font.Font(None, 24)
            self._fonts_initialized = True
        except Exception as e:
            logger.warning(f"Failed to load fonts: {e}, using default")
            self._font_small = pygame.font.Font(None, 16)
            self._font_medium = self._font_small
            self._font_large = self._font_small
            self._fonts_initialized = True

    def render(
        self,
        screen: pygame.Surface,
        camera: Camera | None,
        units: list[Unit],
        selected_unit: Unit | None,
        fps: float,
        game_paused: bool,
        current_turn: int = 0,
        game_map=None,  # P0-2 Phase 2: 新增game_map参数
    ) -> None:
        """渲染所有HUD组件

        Args:
            screen: 主屏幕Surface
            camera: 相机对象（用于Minimap）
            units: 所有单位列表（用于Minimap）
            selected_unit: 当前选中单位（用于Status Bar）
            fps: 当前FPS
            game_paused: 游戏是否暂停
            current_turn: 当前回合数
            game_map: 游戏地图（用于Minimap地形渲染）
        """
        import time

        start_time = time.perf_counter()

        self._init_fonts()

        try:
            # 1. Status Bar（顶部，优先级最高）
            if self.enable_status_bar:
                self._render_status_bar(screen, selected_unit, fps, game_paused, current_turn)

            # 2. Minimap（右下角）- P0-2 Phase 2: 使用MinimapRenderer
            if self.enable_minimap and camera and game_map:
                self._minimap_renderer.render(screen, game_map, camera, units)

            # 3. Keyboard Shortcuts Help（覆盖层，按需显示）
            if self.enable_shortcuts_help:
                self._render_shortcuts_help(screen)

        except Exception as e:
            logger.error(f"HUD rendering failed: {e}", exc_info=True)

        finally:
            # 性能统计
            elapsed = (time.perf_counter() - start_time) * 1000
            self._ui_render_time_ms = elapsed

            # 性能预算检查（5ms）
            if elapsed > 5.0:
                logger.warning(f"HUD rendering exceeded budget: {elapsed:.2f}ms > 5ms")

    def _render_status_bar(
        self,
        screen: pygame.Surface,
        selected_unit: Unit | None,
        fps: float,
        game_paused: bool,
        current_turn: int,
    ) -> None:
        """渲染Status Bar（顶部40px）"""
        screen_width = screen.get_width()

        # 背景（半透明黑色）
        overlay = pygame.Surface((screen_width, 40), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # 左侧：FPS + 暂停状态
        fps_color = (255, 0, 0) if fps < 15 else (0, 255, 0) if fps > 30 else (255, 255, 0)
        fps_text = self._font_medium.render(f"FPS: {fps:.1f}", True, fps_color)
        screen.blit(fps_text, (10, 10))

        if game_paused:
            pause_text = self._font_large.render("⏸ PAUSED", True, (255, 200, 0))
            screen.blit(pause_text, (120, 8))

        # 中间：选中单位信息
        if selected_unit:
            unit_name = getattr(selected_unit, "display_name", "Unit")
            hp_current = (
                getattr(selected_unit.health, "current", 100)
                if hasattr(selected_unit, "health")
                else 100
            )
            hp_max = (
                getattr(selected_unit.health, "maximum", 100)
                if hasattr(selected_unit, "health")
                else 100
            )
            hp_percent = (hp_current / hp_max * 100) if hp_max > 0 else 0

            # HP颜色（根据血量）
            hp_color = (
                (0, 255, 0)
                if hp_percent > 70
                else (255, 255, 0)
                if hp_percent > 30
                else (255, 0, 0)
            )

            unit_info = f"{unit_name} | HP: {hp_current}/{hp_max}"
            unit_text = self._font_medium.render(unit_info, True, (255, 255, 255))

            # 居中显示
            center_x = screen_width // 2 - unit_text.get_width() // 2
            screen.blit(unit_text, (center_x, 10))

            # HP条（在文字下方）
            bar_width = 200
            bar_height = 8
            bar_x = center_x
            bar_y = 28

            pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(
                screen, hp_color, (bar_x, bar_y, int(bar_width * hp_percent / 100), bar_height)
            )
            pygame.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_width, bar_height), 1)

        # 右侧：回合数 + 快捷键提示
        turn_text = self._font_medium.render(f"Turn: {current_turn}", True, (200, 200, 200))
        screen.blit(turn_text, (screen_width - 120, 10))

        help_text = self._font_small.render("Press H for help", True, (150, 150, 150))
        screen.blit(help_text, (screen_width - 120, 26))

    def _render_minimap(
        self,
        screen: pygame.Surface,
        camera: Camera,
        units: list[Unit],
    ) -> None:
        """渲染Minimap（右下角200x200px）"""
        screen_width = screen.get_width()
        screen_height = screen.get_height()

        minimap_size = 200
        margin = 10
        minimap_x = screen_width - minimap_size - margin
        minimap_y = screen_height - minimap_size - margin

        # 背景（半透明黑色）
        overlay = pygame.Surface((minimap_size, minimap_size), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (minimap_x, minimap_y))

        # 边框
        pygame.draw.rect(
            screen, (100, 100, 100), (minimap_x, minimap_y, minimap_size, minimap_size), 2
        )

        # TODO: 实际Minimap渲染（显示地形+单位）
        # 当前版本：占位符
        placeholder_text = self._font_small.render("Minimap", True, (150, 150, 150))
        text_x = minimap_x + minimap_size // 2 - placeholder_text.get_width() // 2
        text_y = minimap_y + minimap_size // 2 - placeholder_text.get_height() // 2
        screen.blit(placeholder_text, (text_x, text_y))

        # 显示单位数量
        unit_count_text = self._font_small.render(f"{len(units)} units", True, (200, 200, 200))
        screen.blit(unit_count_text, (minimap_x + 5, minimap_y + minimap_size - 20))

    def _render_shortcuts_help(self, screen: pygame.Surface) -> None:
        """渲染快捷键帮助（覆盖层，按H显示）

        P0-2 Phase 3: 使用KeyboardShortcutManager动态获取快捷键
        """
        screen_width = screen.get_width()
        screen_height = screen.get_height()

        # 半透明黑色背景
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        # 帮助面板（居中，调整高度以适应更多快捷键）
        panel_width = 500
        panel_height = 400
        panel_x = screen_width // 2 - panel_width // 2
        panel_y = screen_height // 2 - panel_height // 2

        panel_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surf.fill((40, 40, 40, 240))
        pygame.draw.rect(panel_surf, (100, 100, 100), (0, 0, panel_width, panel_height), 2)

        # 标题
        title_text = self._font_large.render("Keyboard Shortcuts", True, (255, 255, 255))
        panel_surf.blit(title_text, (panel_width // 2 - title_text.get_width() // 2, 20))

        # P0-2 Phase 3: 从KeyboardShortcutManager获取快捷键
        try:
            from pycc2.input.keyboard_shortcut_manager import KeyboardShortcutManager

            manager = KeyboardShortcutManager.get_instance()
            all_shortcuts = manager.get_all_shortcuts()

            # 筛选最重要的快捷键显示（避免太多）
            important_actions = [
                "Pause Resume",
                "Select Next Unit",
                "Select Prev Unit",
                "Toggle Help",
                "Toggle Minimap",
                "Close Overlays",
                "Camera Move Left",
                "Camera Move Right",
                "Quit Game",
            ]

            shortcuts = []
            for action_name in important_actions:
                if action_name in all_shortcuts:
                    keys = all_shortcuts[action_name]
                    shortcuts.append((keys[0], action_name))
        except Exception as e:
            logger.warning(f"Failed to load shortcuts from manager: {e}")
            # 降级到硬编码列表
            shortcuts = [
                ("SPACE", "Pause/Resume Game"),
                ("TAB", "Next Unit"),
                ("Shift+TAB", "Previous Unit"),
                ("1-9", "Select Unit Group"),
                ("H", "Toggle Help"),
                ("Esc", "Close Overlays"),
            ]

        # 渲染快捷键列表
        y_offset = 60
        for key, desc in shortcuts[:10]:  # 最多显示10个
            key_text = self._font_medium.render(key, True, (255, 200, 0))
            desc_text = self._font_small.render(desc, True, (200, 200, 200))

            panel_surf.blit(key_text, (40, y_offset))
            panel_surf.blit(desc_text, (200, y_offset + 2))
            y_offset += 32

        # 关闭提示
        close_text = self._font_small.render("Press H or Esc to close", True, (150, 150, 150))
        panel_surf.blit(
            close_text, (panel_width // 2 - close_text.get_width() // 2, panel_height - 30)
        )

        screen.blit(panel_surf, (panel_x, panel_y))

    def toggle_shortcuts_help(self) -> None:
        """切换快捷键帮助显示"""
        self.enable_shortcuts_help = not self.enable_shortcuts_help

    def handle_minimap_click(
        self,
        click_x: int,
        click_y: int,
        screen_width: int,
        screen_height: int,
        game_map,
        camera,
    ) -> tuple[int, int] | None:
        """处理Minimap点击事件（FUNC-01实现）

        Args:
            click_x: 屏幕点击X坐标
            click_y: 屏幕点击Y坐标
            screen_width: 屏幕宽度
            screen_height: 屏幕高度
            game_map: 游戏地图
            camera: 相机对象

        Returns:
            (world_x, world_y) 世界坐标用于跳转相机，或None如果未点击Minimap
        """
        if not self.enable_minimap:
            return None

        # 计算Minimap位置（右下角）
        minimap_size = 200
        margin = 10
        minimap_position = (
            screen_width - minimap_size - margin,
            screen_height - minimap_size - margin,
        )

        # 委托给MinimapRenderer处理
        return self._minimap_renderer.handle_click(
            click_x, click_y, minimap_position, game_map, camera
        )

    def get_ui_render_time_ms(self) -> float:
        """获取UI渲染时间（毫秒）"""
        return self._ui_render_time_ms
