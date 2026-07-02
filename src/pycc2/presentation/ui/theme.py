"""UI Theme System

Centralized theme management for consistent UI appearance.
Supports multiple themes and runtime theme switching.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ColorScheme:
    """Color scheme container."""

    primary: tuple = (65, 105, 225)
    secondary: tuple = (34, 139, 34)
    background: tuple = (40, 44, 52)
    surface: tuple = (55, 59, 67)
    text_primary: tuple = (240, 240, 240)
    text_secondary: tuple = (180, 180, 180)
    text_disabled: tuple = (120, 120, 120)
    success: tuple = (80, 200, 80)
    warning: tuple = (230, 180, 50)
    error: tuple = (230, 80, 80)
    info: tuple = (100, 149, 237)
    border: tuple = (80, 84, 92)
    border_light: tuple = (100, 104, 112)


@dataclass
class ThemeMetrics:
    """Theme measurement constants."""

    font_size_small: int = 16
    font_size_normal: int = 20
    font_size_large: int = 28
    font_size_title: int = 36
    padding_small: int = 4
    padding_normal: int = 8
    padding_large: int = 16
    border_radius_small: int = 4
    border_radius_normal: int = 8
    border_radius_large: int = 12
    animation_duration_fast: float = 0.1
    animation_duration_normal: float = 0.2
    animation_duration_slow: float = 0.4


@dataclass
class Theme:
    """Complete UI theme definition.

    Attributes:
        name: Theme identifier
        colors: Color scheme for all UI elements
        metrics: Sizing and spacing constants

    """

    name: str = "default"
    colors: ColorScheme = field(default_factory=ColorScheme)
    metrics: ThemeMetrics = field(default_factory=ThemeMetrics)

    def to_dict(self) -> dict:
        """Serialize theme to dictionary."""
        return {
            "name": self.name,
            "colors": {
                k: list(v) if isinstance(v, tuple) else v for k, v in self.colors.__dict__.items()
            },
            "metrics": self.metrics.__dict__,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Theme":
        """Deserialize theme from dictionary."""
        colors_data = data.get("colors", {})
        colors = ColorScheme(
            **{k: tuple(v) if isinstance(v, list) else v for k, v in colors_data.items()}
        )
        metrics_data = data.get("metrics", {})
        metrics = ThemeMetrics(**metrics_data)
        return cls(name=data.get("name", "default"), colors=colors, metrics=metrics)

    @classmethod
    def load_from_file(cls, path: Path) -> "Theme":
        """Load theme from JSON file."""
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)

    def save_to_file(self, path: Path) -> None:
        """Save theme to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


DEFAULT_THEME = Theme(name="default")
DARK_THEME = Theme(
    name="dark",
    colors=ColorScheme(
        background=(25, 28, 33),
        surface=(35, 38, 45),
        text_primary=(235, 235, 235),
        border=(60, 64, 72),
    ),
)
LIGHT_THEME = Theme(
    name="light",
    colors=ColorScheme(
        background=(250, 250, 250),
        surface=(240, 240, 240),
        text_primary=(30, 30, 30),
        text_secondary=(80, 80, 80),
        border=(200, 200, 200),
        primary=(41, 98, 255),
        secondary=(16, 185, 129),
    ),
)


class ThemeManager:
    """Manages UI themes and provides global access."""

    _instance: Optional["ThemeManager"] = None
    _current_theme: Theme = DEFAULT_THEME
    _themes: dict[str, Theme] = {}

    def __new__(cls) -> "ThemeManager":
        """new  ."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_default_themes()
        return cls._instance

    def _initialize_default_themes(self) -> None:
        """Register default themes."""
        self._themes["default"] = DEFAULT_THEME
        self._themes["dark"] = DARK_THEME
        self._themes["light"] = LIGHT_THEME

    @classmethod
    def get_current(cls) -> Theme:
        """Get currently active theme."""
        return cls._current_theme

    @classmethod
    def set_theme(cls, theme_name: str) -> bool:
        """Set active theme by name.

        Returns:
            True if theme was found and applied, False otherwise

        """
        theme = cls._themes.get(theme_name)
        if theme:
            cls._current_theme = theme
            return True
        return False

    @classmethod
    def register_theme(cls, theme: Theme) -> None:
        """Register a new custom theme."""
        cls._themes[theme.name] = theme

    @classmethod
    def get_available_themes(cls) -> list:
        """Get list of available theme names."""
        return list(cls._themes.keys())

    @classmethod
    def reset(cls) -> None:
        """Reset to default theme."""
        cls._current_theme = DEFAULT_THEME
