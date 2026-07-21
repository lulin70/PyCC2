"""In-game keybindings help overlay (V-08 Wave D3).

Shows a semi-transparent panel listing all current keybindings when the user
presses the ``?`` key. The panel auto-pauses the game on show and resumes on
hide, matching the Wave B-rev UX requirement that the player can read
keybindings without the battlefield continuing to evolve behind it.

Design decisions (2026-07-21):
- ``GameLoop`` does NOT expose ``pause()/resume()`` methods (P0-NEW-C).
  We directly toggle ``game_state.paused`` which is the existing pattern
  used by ``game_loop.py:232``.
- Transparency: panel alpha = 180 (70% opacity), text background alpha =
  153 (60% opacity). Values per Wave B-rev UX P1.
- Dismiss: any key except ``?`` itself (prevents toggle flicker).
- Keybinding source: reuses ``DEFAULT_KEYBINDS`` + ``ACTION_LABELS`` from
  ``keybind_manager.py`` (single source of truth — no duplication).

Reference: docs/VISUAL_POLISH_PLAN.md V-08 章节 (v2.1, Wave B-rev)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
from pygame import Rect, Surface, draw
from pygame.font import Font

from pycc2.presentation.ui.keybind_manager import ACTION_LABELS, DEFAULT_KEYBINDS

if TYPE_CHECKING:
    from pycc2.services.game_loop_types import GameState


# ---------------------------------------------------------------------------
# Visual constants (Wave B-rev P1)
# ---------------------------------------------------------------------------

PANEL_ALPHA: int = 180  # 70% opacity — panel background
TEXT_BG_ALPHA: int = 153  # 60% opacity — text row background
PANEL_BORDER_COLOR: tuple[int, int, int] = (110, 120, 95)
PANEL_BG_COLOR: tuple[int, int, int] = (20, 24, 30)
HEADER_COLOR: tuple[int, int, int] = (255, 200, 100)
LABEL_COLOR: tuple[int, int, int] = (220, 220, 220)
KEY_COLOR: tuple[int, int, int] = (255, 255, 100)
CATEGORY_COLOR: tuple[int, int, int] = (180, 200, 150)

PANEL_MARGIN: int = 60
PANEL_PADDING: int = 20
ROW_HEIGHT: int = 22
CATEGORY_SPACING: int = 12
HEADER_HEIGHT: int = 40


# ---------------------------------------------------------------------------
# Keybinding categorization
# ---------------------------------------------------------------------------

# Mapping of action name → category for display grouping.
# Actions not in this map fall back to "Other".
ACTION_CATEGORIES: dict[str, str] = {
    # Movement / orders
    "move": "Orders",
    "move_fast": "Orders",
    "sneak": "Orders",
    "fire": "Orders",
    "smoke": "Orders",
    "defend": "Orders",
    "hide": "Orders",
    "cancel": "Orders",
    "select_all": "Orders",
    # Camera
    "camera_up": "Camera",
    "camera_down": "Camera",
    "camera_left": "Camera",
    "camera_right": "Camera",
}

DEFAULT_CATEGORY_ORDER: tuple[str, ...] = ("Orders", "Camera", "Other")


def categorize_action(action: str) -> str:
    """Return the display category for an action name."""
    return ACTION_CATEGORIES.get(action, "Other")


def key_combo_to_text(key_combo: tuple[int, ...]) -> str:
    """Convert a pygame key combo tuple to a human-readable string.

    Single key: ``K_m`` → ``"M"``
    Combo: ``(K_LCTRL, K_a)`` → ``"Ctrl+A"``
    """
    if not key_combo:
        return "—"

    parts: list[str] = []
    for key in key_combo:
        parts.append(_key_to_text(key))
    return "+".join(parts)


def _key_to_text(key: int) -> str:
    """Convert a single pygame key constant to a readable label."""
    # Modifier keys
    if key in (pygame.K_LCTRL, pygame.K_RCTRL):
        return "Ctrl"
    if key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
        return "Shift"
    if key in (pygame.K_LALT, pygame.K_RALT):
        return "Alt"
    if key in (pygame.K_LMETA, pygame.K_RMETA):
        return "Meta"

    # Arrow keys
    arrow_map = {
        pygame.K_UP: "Up",
        pygame.K_DOWN: "Down",
        pygame.K_LEFT: "Left",
        pygame.K_RIGHT: "Right",
    }
    if key in arrow_map:
        return arrow_map[key]

    # Escape / space / special
    if key == pygame.K_ESCAPE:
        return "Esc"
    if key == pygame.K_SPACE:
        return "Space"
    if key == pygame.K_RETURN:
        return "Enter"
    if key == pygame.K_TAB:
        return "Tab"

    # Single printable character (letters / digits / punctuation)
    try:
        name = pygame.key.name(key)
    except (ValueError, TypeError):
        return f"Key{key}"

    # pygame.key.name returns lowercase like 'a', '1', '/' etc.
    # Uppercase single letters for display
    if len(name) == 1 and name.isalpha():
        return name.upper()
    return name.capitalize() if name else f"Key{key}"


def is_toggle_key(key: int, mod: int) -> bool:
    """Return True if the key event should toggle the overlay.

    Accepts both ``K_QUESTION`` (reported on some layouts) and
    ``K_SLASH`` with SHIFT modifier (standard US keyboard: ``?`` = Shift+/).
    """
    if key == pygame.K_QUESTION:
        return True
    return key == pygame.K_SLASH and bool(mod & pygame.KMOD_SHIFT)


# ---------------------------------------------------------------------------
# Overlay class
# ---------------------------------------------------------------------------


class KeybindingsOverlay:
    """In-game keybindings help overlay (V-08 Wave D3).

    Auto-pauses the game on show; any key (except ``?`` itself) dismisses.
    Reads keybindings from ``keybind_manager.DEFAULT_KEYBINDS`` (single source
    of truth) and groups them by category for display.

    Attributes:
        panel_alpha: Panel background opacity (0-255). Default 180 (70%).
        text_bg_alpha: Text row background opacity (0-255). Default 153 (60%).
    """

    def __init__(
        self,
        game_state: GameState,
        panel_alpha: int = PANEL_ALPHA,
        text_bg_alpha: int = TEXT_BG_ALPHA,
    ) -> None:
        """Initialize the overlay (hidden by default).

        Args:
            game_state: Mutable game state; ``.paused`` field toggled on show/hide.
            panel_alpha: Override for panel background opacity.
            text_bg_alpha: Override for text row background opacity.
        """
        self._game_state = game_state
        self._visible: bool = False
        self._was_paused_before: bool = False  # remember prior pause state
        self.panel_alpha = panel_alpha
        self.text_bg_alpha = text_bg_alpha

    # ------ State queries ------

    @property
    def visible(self) -> bool:
        """Return True if the overlay is currently shown."""
        return self._visible

    # ------ Show / Hide / Toggle ------

    def show(self) -> None:
        """Show the overlay and pause the game.

        Remembers the prior ``paused`` state so ``hide()`` can restore it
        rather than unconditionally unpausing (which could break players
        who had the game already paused for other reasons).
        """
        if self._visible:
            return
        self._visible = True
        self._was_paused_before = self._game_state.paused
        self._game_state.paused = True

    def hide(self) -> None:
        """Hide the overlay and restore the prior pause state."""
        if not self._visible:
            return
        self._visible = False
        # Restore prior pause state (don't force-unpause if user had it paused)
        self._game_state.paused = self._was_paused_before

    def toggle(self, key: int = pygame.K_QUESTION, mod: int = 0) -> None:
        """Toggle visibility if the key matches the ``?`` toggle key.

        Args:
            key: pygame key constant from the KEYDOWN event.
            mod: pygame modifier bitmask from the KEYDOWN event.
        """
        if is_toggle_key(key, mod):
            if self._visible:
                self.hide()
            else:
                self.show()

    def on_key_down(self, key: int, mod: int = 0) -> None:
        """Handle a KEYDOWN event.

        - ``?`` toggles visibility.
        - Any other key (when visible) dismisses the overlay.

        Args:
            key: pygame key constant from the KEYDOWN event.
            mod: pygame modifier bitmask from the KEYDOWN event.
        """
        if is_toggle_key(key, mod):
            self.toggle(key=key, mod=mod)
            return

        # Any other key dismisses the overlay (Wave B-rev P1)
        if self._visible:
            self.hide()

    # ------ Rendering ------

    def render(
        self,
        surface: Surface,
        font_title: Font,
        font_category: Font,
        font_key: Font,
    ) -> None:
        """Render the overlay onto ``surface`` if visible.

        Layout:
        - Centered panel covering ~60% of screen width, ~70% height.
        - Header: "KEYBINDINGS" (yellow, centered)
        - Body: grouped by category, each row shows action label + key combo.
        - Footer: "Press any key to close" hint.

        Args:
            surface: Target surface (typically the screen).
            font_title: Font for the panel header.
            font_category: Font for category sub-headers.
            font_key: Font for keybinding rows.
        """
        if not self._visible:
            return

        sw, sh = surface.get_size()
        panel_w = max(400, sw - 2 * PANEL_MARGIN)
        panel_h = max(300, sh - 2 * PANEL_MARGIN)
        panel_x = (sw - panel_w) // 2
        panel_y = (sh - panel_h) // 2
        panel_rect = Rect(panel_x, panel_y, panel_w, panel_h)

        # --- Panel background (semi-transparent) ---
        panel_surface = Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surface.fill((*PANEL_BG_COLOR, self.panel_alpha))
        surface.blit(panel_surface, (panel_x, panel_y))
        draw.rect(surface, PANEL_BORDER_COLOR, panel_rect, 2)

        # --- Header ---
        header_y = panel_y + PANEL_PADDING
        header_text = font_title.render("KEYBINDINGS", True, HEADER_COLOR)
        surface.blit(
            header_text,
            (panel_x + (panel_w - header_text.get_width()) // 2, header_y),
        )
        draw.line(
            surface,
            PANEL_BORDER_COLOR,
            (panel_x + PANEL_PADDING, header_y + HEADER_HEIGHT - 8),
            (panel_x + panel_w - PANEL_PADDING, header_y + HEADER_HEIGHT - 8),
            1,
        )

        # --- Body: keybindings grouped by category ---
        body_y = header_y + HEADER_HEIGHT
        body_x = panel_x + PANEL_PADDING
        body_w = panel_w - 2 * PANEL_PADDING

        grouped = _group_bindings_by_category()

        for category in DEFAULT_CATEGORY_ORDER:
            if category not in grouped:
                continue

            # Category sub-header
            cat_surf = font_category.render(category, True, CATEGORY_COLOR)
            surface.blit(cat_surf, (body_x, body_y))
            body_y += ROW_HEIGHT

            # Rows in this category
            for action in grouped[category]:
                label = ACTION_LABELS.get(action, action)
                key_text = key_combo_to_text(DEFAULT_KEYBINDS.get(action, ()))
                _render_binding_row(
                    surface,
                    body_x,
                    body_y,
                    body_w,
                    label,
                    key_text,
                    font_key,
                    self.text_bg_alpha,
                )
                body_y += ROW_HEIGHT

                if body_y > panel_y + panel_h - 2 * ROW_HEIGHT:
                    break

            body_y += CATEGORY_SPACING // 2

            if body_y > panel_y + panel_h - 2 * ROW_HEIGHT:
                break

        # --- Footer ---
        footer_y = panel_y + panel_h - ROW_HEIGHT - PANEL_PADDING // 2
        footer_text = font_key.render(
            "Press any key to close (? to toggle)", True, LABEL_COLOR
        )
        surface.blit(
            footer_text,
            (panel_x + (panel_w - footer_text.get_width()) // 2, footer_y),
        )


# ---------------------------------------------------------------------------
# Module-private helpers
# ---------------------------------------------------------------------------


def _group_bindings_by_category() -> dict[str, list[str]]:
    """Group DEFAULT_KEYBINDS actions by display category.

    Returns:
        Dict mapping category name → list of action names (in DEFAULT_KEYBINDS order).
    """
    grouped: dict[str, list[str]] = {cat: [] for cat in DEFAULT_CATEGORY_ORDER}
    for action in DEFAULT_KEYBINDS:
        category = categorize_action(action)
        grouped.setdefault(category, []).append(action)
    return grouped


def _render_binding_row(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    label: str,
    key_text: str,
    font: Font,
    bg_alpha: int,
) -> None:
    """Render a single keybinding row (label on left, key combo on right)."""
    # Row background (subtle alternating row for readability)
    row_bg = Surface((width, ROW_HEIGHT - 2), pygame.SRCALPHA)
    row_bg.fill((50, 55, 60, bg_alpha))
    surface.blit(row_bg, (x, y))

    # Label (left)
    label_surf = font.render(label, True, LABEL_COLOR)
    surface.blit(label_surf, (x + 8, y + 2))

    # Key combo (right)
    key_surf = font.render(key_text, True, KEY_COLOR)
    surface.blit(key_surf, (x + width - key_surf.get_width() - 12, y + 2))


__all__ = [
    "ACTION_CATEGORIES",
    "DEFAULT_CATEGORY_ORDER",
    "HEADER_HEIGHT",
    "KEY_COLOR",
    "LABEL_COLOR",
    "PANEL_ALPHA",
    "PANEL_BG_COLOR",
    "PANEL_BORDER_COLOR",
    "PANEL_MARGIN",
    "PANEL_PADDING",
    "ROW_HEIGHT",
    "TEXT_BG_ALPHA",
    "KeybindingsOverlay",
    "categorize_action",
    "is_toggle_key",
    "key_combo_to_text",
]
