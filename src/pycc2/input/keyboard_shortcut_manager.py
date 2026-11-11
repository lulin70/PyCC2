"""Keyboard Shortcut Manager - 键盘快捷键管理器

集中管理游戏快捷键：
- 快捷键注册和绑定
- 事件处理和分发
- 可配置的按键映射
- 冲突检测

设计：
- 单例模式（全局唯一实例）
- 事件驱动（pygame.event监听）
- 回调机制（按键→Action→Handler）
- 支持修饰键（Shift/Ctrl/Alt）
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from enum import Enum, auto

logger = logging.getLogger(__name__)


class ShortcutAction(Enum):
    """快捷键动作枚举"""

    # 游戏控制
    PAUSE_RESUME = auto()
    QUIT_GAME = auto()

    # 单位选择
    SELECT_NEXT_UNIT = auto()
    SELECT_PREV_UNIT = auto()
    SELECT_UNIT_GROUP_1 = auto()
    SELECT_UNIT_GROUP_2 = auto()
    SELECT_UNIT_GROUP_3 = auto()
    SELECT_UNIT_GROUP_4 = auto()
    SELECT_UNIT_GROUP_5 = auto()
    SELECT_UNIT_GROUP_6 = auto()
    SELECT_UNIT_GROUP_7 = auto()
    SELECT_UNIT_GROUP_8 = auto()
    SELECT_UNIT_GROUP_9 = auto()

    # 相机控制
    CAMERA_MOVE_LEFT = auto()
    CAMERA_MOVE_RIGHT = auto()
    CAMERA_MOVE_UP = auto()
    CAMERA_MOVE_DOWN = auto()
    CAMERA_ZOOM_IN = auto()
    CAMERA_ZOOM_OUT = auto()
    CAMERA_RESET = auto()

    # UI切换
    TOGGLE_HELP = auto()
    TOGGLE_MINIMAP = auto()
    TOGGLE_STATUS_BAR = auto()
    CLOSE_OVERLAYS = auto()

    # 调试
    TOGGLE_DEBUG_MODE = auto()
    TOGGLE_FPS_DISPLAY = auto()


class KeyModifier(Enum):
    """键盘修饰键"""

    NONE = 0
    SHIFT = 1
    CTRL = 2
    ALT = 4
    SHIFT_CTRL = 3
    SHIFT_ALT = 5
    CTRL_ALT = 6
    SHIFT_CTRL_ALT = 7


class KeyboardShortcutManager:
    """键盘快捷键管理器 - 单例模式"""

    _instance: KeyboardShortcutManager | None = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化快捷键管理器"""
        if self._initialized:
            return

        # 快捷键映射：(key_code, modifier) -> action
        self._shortcuts: dict[tuple[int, KeyModifier], ShortcutAction] = {}

        # 动作处理器：action -> callback
        self._handlers: dict[ShortcutAction, list[Callable]] = {}

        # 启用/禁用状态
        self._enabled = True

        # 注册默认快捷键
        self._register_default_shortcuts()

        self._initialized = True

        logger.info("KeyboardShortcutManager initialized")

    def _register_default_shortcuts(self) -> None:
        """注册默认快捷键映射"""
        # 导入pygame常量（延迟导入）
        import pygame

        # 游戏控制
        self.register_shortcut(pygame.K_SPACE, KeyModifier.NONE, ShortcutAction.PAUSE_RESUME)
        self.register_shortcut(pygame.K_ESCAPE, KeyModifier.NONE, ShortcutAction.CLOSE_OVERLAYS)
        self.register_shortcut(pygame.K_q, KeyModifier.CTRL, ShortcutAction.QUIT_GAME)

        # 单位选择
        self.register_shortcut(pygame.K_TAB, KeyModifier.NONE, ShortcutAction.SELECT_NEXT_UNIT)
        self.register_shortcut(pygame.K_TAB, KeyModifier.SHIFT, ShortcutAction.SELECT_PREV_UNIT)

        # 单位组快捷键（1-9）
        for i in range(1, 10):
            key_code = getattr(pygame, f"K_{i}")
            action = getattr(ShortcutAction, f"SELECT_UNIT_GROUP_{i}")
            self.register_shortcut(key_code, KeyModifier.NONE, action)

        # 相机控制
        self.register_shortcut(pygame.K_LEFT, KeyModifier.NONE, ShortcutAction.CAMERA_MOVE_LEFT)
        self.register_shortcut(pygame.K_RIGHT, KeyModifier.NONE, ShortcutAction.CAMERA_MOVE_RIGHT)
        self.register_shortcut(pygame.K_UP, KeyModifier.NONE, ShortcutAction.CAMERA_MOVE_UP)
        self.register_shortcut(pygame.K_DOWN, KeyModifier.NONE, ShortcutAction.CAMERA_MOVE_DOWN)
        self.register_shortcut(pygame.K_PLUS, KeyModifier.NONE, ShortcutAction.CAMERA_ZOOM_IN)
        self.register_shortcut(pygame.K_MINUS, KeyModifier.NONE, ShortcutAction.CAMERA_ZOOM_OUT)
        self.register_shortcut(pygame.K_HOME, KeyModifier.NONE, ShortcutAction.CAMERA_RESET)

        # UI切换
        self.register_shortcut(pygame.K_h, KeyModifier.NONE, ShortcutAction.TOGGLE_HELP)
        self.register_shortcut(pygame.K_m, KeyModifier.NONE, ShortcutAction.TOGGLE_MINIMAP)
        self.register_shortcut(pygame.K_F1, KeyModifier.NONE, ShortcutAction.TOGGLE_DEBUG_MODE)
        self.register_shortcut(pygame.K_F2, KeyModifier.NONE, ShortcutAction.TOGGLE_FPS_DISPLAY)

    def register_shortcut(
        self,
        key_code: int,
        modifier: KeyModifier,
        action: ShortcutAction,
    ) -> None:
        """注册快捷键

        Args:
            key_code: pygame按键码（如pygame.K_SPACE）
            modifier: 修饰键（如KeyModifier.SHIFT）
            action: 动作（如ShortcutAction.PAUSE_RESUME）
        """
        shortcut_key = (key_code, modifier)

        # 冲突检测
        if shortcut_key in self._shortcuts:
            existing_action = self._shortcuts[shortcut_key]
            logger.warning(
                f"Shortcut conflict: {shortcut_key} already mapped to "
                f"{existing_action.name}, overriding with {action.name}"
            )

        self._shortcuts[shortcut_key] = action
        logger.debug(f"Registered shortcut: {shortcut_key} -> {action.name}")

    def unregister_shortcut(self, key_code: int, modifier: KeyModifier) -> None:
        """注销快捷键

        Args:
            key_code: pygame按键码
            modifier: 修饰键
        """
        shortcut_key = (key_code, modifier)
        if shortcut_key in self._shortcuts:
            action = self._shortcuts.pop(shortcut_key)
            logger.debug(f"Unregistered shortcut: {shortcut_key} -> {action.name}")

    def register_handler(self, action: ShortcutAction, handler: Callable) -> None:
        """注册动作处理器

        Args:
            action: 动作类型
            handler: 回调函数（无参数）
        """
        if action not in self._handlers:
            self._handlers[action] = []

        self._handlers[action].append(handler)
        logger.debug(f"Registered handler for action: {action.name}")

    def unregister_handler(self, action: ShortcutAction, handler: Callable) -> None:
        """注销动作处理器

        Args:
            action: 动作类型
            handler: 回调函数
        """
        if action in self._handlers and handler in self._handlers[action]:
            self._handlers[action].remove(handler)
            logger.debug(f"Unregistered handler for action: {action.name}")

    def handle_event(self, event) -> bool:
        """处理pygame事件

        Args:
            event: pygame.event.Event对象

        Returns:
            True表示事件已处理，False表示未处理
        """
        if not self._enabled:
            return False

        # 只处理KEYDOWN事件
        import pygame

        if event.type != pygame.KEYDOWN:
            return False

        # 获取修饰键状态
        modifier = self._get_current_modifier()

        # 查找对应的动作
        shortcut_key = (event.key, modifier)
        action = self._shortcuts.get(shortcut_key)

        if action is None:
            return False

        # 触发所有注册的处理器
        if action in self._handlers:
            logger.debug(f"Triggering action: {action.name}")
            for handler in self._handlers[action]:
                try:
                    handler()
                except Exception as e:
                    logger.error(
                        f"Handler for {action.name} failed: {e}",
                        exc_info=True,
                    )
            return True

        return False

    def _get_current_modifier(self) -> KeyModifier:
        """获取当前修饰键状态

        Returns:
            当前按下的修饰键组合
        """
        import pygame

        mods = pygame.key.get_mods()

        shift = bool(mods & pygame.KMOD_SHIFT)
        ctrl = bool(mods & pygame.KMOD_CTRL)
        alt = bool(mods & pygame.KMOD_ALT)

        if shift and ctrl and alt:
            return KeyModifier.SHIFT_CTRL_ALT
        elif shift and ctrl:
            return KeyModifier.SHIFT_CTRL
        elif shift and alt:
            return KeyModifier.SHIFT_ALT
        elif ctrl and alt:
            return KeyModifier.CTRL_ALT
        elif shift:
            return KeyModifier.SHIFT
        elif ctrl:
            return KeyModifier.CTRL
        elif alt:
            return KeyModifier.ALT
        else:
            return KeyModifier.NONE

    def enable(self) -> None:
        """启用快捷键管理器"""
        self._enabled = True
        logger.info("KeyboardShortcutManager enabled")

    def disable(self) -> None:
        """禁用快捷键管理器"""
        self._enabled = False
        logger.info("KeyboardShortcutManager disabled")

    def is_enabled(self) -> bool:
        """检查快捷键管理器是否启用"""
        return self._enabled

    def get_shortcuts_by_action(self, action: ShortcutAction) -> list[tuple[int, KeyModifier]]:
        """获取指定动作的所有快捷键

        Args:
            action: 动作类型

        Returns:
            快捷键列表
        """
        return [key for key, act in self._shortcuts.items() if act == action]

    def get_all_shortcuts(self) -> dict[str, list[str]]:
        """获取所有快捷键（用于显示帮助）

        Returns:
            字典：动作名称 -> 按键组合列表
        """
        import pygame

        result: dict[str, list[str]] = {}
        for (key_code, modifier), action in self._shortcuts.items():
            # 转换按键码为可读字符串
            key_name = pygame.key.name(key_code).upper()

            # 添加修饰键前缀
            if modifier == KeyModifier.SHIFT:
                key_name = f"Shift+{key_name}"
            elif modifier == KeyModifier.CTRL:
                key_name = f"Ctrl+{key_name}"
            elif modifier == KeyModifier.ALT:
                key_name = f"Alt+{key_name}"
            elif modifier == KeyModifier.SHIFT_CTRL:
                key_name = f"Shift+Ctrl+{key_name}"
            elif modifier == KeyModifier.SHIFT_ALT:
                key_name = f"Shift+Alt+{key_name}"
            elif modifier == KeyModifier.CTRL_ALT:
                key_name = f"Ctrl+Alt+{key_name}"
            elif modifier == KeyModifier.SHIFT_CTRL_ALT:
                key_name = f"Shift+Ctrl+Alt+{key_name}"

            action_name = action.name.replace("_", " ").title()

            if action_name not in result:
                result[action_name] = []
            result[action_name].append(key_name)

        return result

    @classmethod
    def get_instance(cls) -> KeyboardShortcutManager:
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例（用于测试）"""
        cls._instance = None
