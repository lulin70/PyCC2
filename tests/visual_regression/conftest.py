"""Visual regression test configuration (V-07 Wave C2 baseline).

Enforces SDL_VIDEODRIVER=dummy for deterministic headless rendering.
All baselines are generated against the same dummy driver to avoid
platform-specific GPU rendering differences.

Threshold (per V-07 Wave B-rev design):
    - Default diff threshold: 3.0%  (Pillow ImageChops pixel diff)
    - Strict threshold (UI elements): 1.0%
    - Loose threshold (terrain with random noise): 5.0%

Platform-specific baselines:
    baselines/linux/      — CI (GitHub Actions Ubuntu)
    baselines/macos/      — local dev (macOS)
    baselines/windows/    — future Windows CI

When intentional visual changes occur, regenerate baselines via:
    python tests/visual_regression/generate_baselines.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Set SDL dummy drivers BEFORE any pygame import (mirror tests/conftest.py).
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

# Constants
BASELINE_ROOT = Path(__file__).parent / "baselines"
DEFAULT_THRESHOLD = 0.03  # 3.0% pixel diff
STRICT_THRESHOLD = 0.01  # 1.0% pixel diff (UI)
LOOSE_THRESHOLD = 0.05  # 5.0% pixel diff (terrain with noise)

# Core scenarios (V-07 Wave B-rev design — 5 scenarios)
SCENARIOS = (
    "main_menu",
    "grass_terrain",
    "urban_terrain",
    "post_battle_report",
    "minimap",
)


def get_baseline_dir(platform: str | None = None) -> Path:
    """Return the baseline directory for the current or specified platform.

    Defaults to the current platform's subdir under baselines/.
    """
    if platform is None:
        platform = sys.platform.lower()
        if platform.startswith("linux"):
            platform = "linux"
        elif platform.startswith("darwin"):
            platform = "macos"
        elif platform.startswith("win"):
            platform = "windows"
    return BASELINE_ROOT / platform


def get_baseline_path(scenario: str, platform: str | None = None) -> Path:
    """Return the baseline PNG path for a scenario."""
    return get_baseline_dir(platform) / f"{scenario}.png"


def baselines_exist(platform: str | None = None) -> bool:
    """Check whether all baseline PNGs exist for the platform."""
    baseline_dir = get_baseline_dir(platform)
    return all((baseline_dir / f"{s}.png").exists() for s in SCENARIOS)
