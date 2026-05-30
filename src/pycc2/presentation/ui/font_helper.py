"""Safe font initialization with fallback for headless test environments.

P0-1 Fix: 解决pygame.font.SysFont在SDL_VIDEODRIVER=dummy下失败的问题
- 首选: pygame.font.SysFont (系统字体，支持中文)
- Fallback: pygame.font.Font(None, size) (bitmap字体，兼容所有环境)
"""

import logging
from typing import Optional
import pygame

logger = logging.getLogger(__name__)


def safe_init_font(size: int = 20, bold: bool = False,
                   font_name: str = "arial") -> Optional[pygame.font.Font]:
    """安全初始化字体，自动处理dummy driver等异常情况。

    Args:
        size: 字体大小(像素)
        bold: 是否粗体
        font_name: 系统字体名称(如'arial', 'consolas')

    Returns:
        Font对象或None(如果所有方法都失败)
    """
    # 尝试1: SysFont (系统字体，最佳质量)
    try:
        if not pygame.font.get_init():
            pygame.font.init()
        font = pygame.font.SysFont(font_name, size, bold=bold)
        if font is not None:
            return font
    except Exception as e:
        logger.debug(f"SysFont failed ({font_name}, {size}): {e}")

    # 尝试2: Bitmap font (兼容性最好)
    try:
        if not pygame.font.get_init():
            pygame.font.init()
        font = pygame.font.Font(None, size)
        if font is not None:
            logger.debug(f"Fallback to bitmap font size={size}")
            return font
    except Exception as e:
        logger.debug(f"Bitmap font failed: {e}")

    # 全部失败
    logger.warning(f"All font methods failed for size={size}")
    return None


def safe_render_text(font: Optional[pygame.font.Font],
                     text: str,
                     color: tuple[int, int, int] = (255, 255, 255),
                     antialias: bool = True) -> Optional[pygame.Surface]:
    """安全渲染文本到Surface。

    Args:
        font: 字体对象(可为None)
        text: 要渲染的文本
        color: 文本颜色(RGB)
        antialias: 是否抗锯齿

    Returns:
        文本Surface或None
    """
    if font is None:
        return None

    try:
        return font.render(text, antialias, color)
    except Exception as e:
        logger.debug(f"Text render failed: {e}")
        return None
