"""CC2 HUD layout constants, color palette, and command definitions."""

from __future__ import annotations

# === Layout Constants (CC2 Authentic) ===
PANEL_HEIGHT: int = 140
LEFT_PANEL_RATIO: float = 0.25
CENTER_PANEL_RATIO: float = 0.45
RIGHT_PANEL_RATIO: float = 0.30

# === Spacing & Sizing ===
PADDING: int = 6
ROW_HEIGHT: int = 18
BUTTON_MIN_WIDTH: int = 70
BUTTON_MIN_HEIGHT: int = 22
ICON_SIZE: int = 16
MINIMAP_SIZE: int = 100

# === Color Palette (CC2 Authentic - Warm Military Tone) ===
BG_COLOR = (58, 64, 48)  # Deep olive-green background
BORDER_COLOR = (90, 96, 80)  # Olive border
TEXT_COLOR = (220, 220, 210)  # Off-white text (slightly warmer)
HIGHLIGHT_COLOR = (255, 220, 100)  # Gold highlight (selected)

# Status colors (CC2 original)
STATUS_HEALTHY = (80, 180, 80)  # Green
STATUS_WOUNDED = (200, 180, 60)  # Yellow
STATUS_CRITICAL = (200, 80, 60)  # Red
STATUS_DEAD = (40, 40, 40)  # Black

# Resource bar colors
AP_BAR_COLOR = (60, 160, 60)  # Green for AP
AT_BAR_COLOR = (160, 120, 60)  # Orange-brown for AT

# Panel backgrounds (warm olive tones)
PANEL_BG_DARK = (48, 52, 40)  # Deep olive panel
PANEL_BG_MID = (58, 64, 48)  # Mid olive panel
PANEL_BG_LIGHT = (68, 74, 58)  # Light olive panel


def get_default_commands() -> list[dict]:
    """Return the CC2 authentic command definitions template.

    Returns:
        List of command dicts with id, label, key marker, and color.
        Callers should resolve color references against the constants above.

    """
    return [
        {"id": "move", "label": "Move", "key": "\u25cf", "color": STATUS_HEALTHY},
        {"id": "move_fast", "label": "Move Fast", "key": "\u25cf", "color": STATUS_HEALTHY},
        {"id": "crawl", "label": "Crawl", "key": "\u25cb", "color": TEXT_COLOR},
        {"id": "fire", "label": "Fire", "key": "\u25cf", "color": STATUS_WOUNDED},
        {"id": "smoke", "label": "Smoke", "key": "\u25cb", "color": TEXT_COLOR},
        {"id": "defend", "label": "Defend", "key": "\u25cb", "color": TEXT_COLOR},
        {"id": "hide", "label": "Hide", "key": "\u25cb", "color": TEXT_COLOR},
    ]
