"""V-07 Wave C2: Visual regression tests against committed baselines.

Runs each of the 5 core scenarios through the same renderer used by
``generate_baselines.py`` and compares the resulting pixels against the
committed baseline PNGs in ``baselines/<platform>/``.

Thresholds (per V-07 Wave B-rev design):
    - main_menu            : strict  (1.0% pixel diff)
    - grass_terrain        : loose   (5.0% — procedural texture has noise)
    - urban_terrain        : default (3.0%)
    - post_battle_report   : strict  (1.0% — UI text)
    - minimap              : default (3.0%)

If a baseline is missing for the current platform, the test is skipped
with a clear instruction to run ``generate_baselines.py``.

If a diff exceeds threshold, the failing diff image is written to
``tests/visual_regression/.diff/<scenario>.png`` for inspection.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# Set SDL dummy drivers BEFORE any pygame import (mirror conftest.py).
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_JOYSTICK_DRIVER", "dummy")

from PIL import Image, ImageChops  # noqa: E402

from tests.visual_regression.conftest import (  # noqa: E402
    DEFAULT_THRESHOLD,
    LOOSE_THRESHOLD,
    STRICT_THRESHOLD,
    baselines_exist,
    get_baseline_dir,
    get_baseline_path,
)
from tests.visual_regression.generate_baselines import (  # noqa: E402
    SCENARIO_RENDERERS,
    _make_screen,
)

# Per-scenario thresholds (see module docstring).
SCENARIO_THRESHOLDS: dict[str, float] = {
    "main_menu": STRICT_THRESHOLD,
    "grass_terrain": LOOSE_THRESHOLD,
    "urban_terrain": DEFAULT_THRESHOLD,
    "post_battle_report": STRICT_THRESHOLD,
    "minimap": DEFAULT_THRESHOLD,
}

DIFF_OUTPUT_DIR = Path(__file__).parent / ".diff"


def _pixel_diff_ratio(baseline_path: Path, current_png_path: Path) -> float:
    """Return the fraction of differing pixels between two PNGs.

    Uses Pillow's ImageChops.difference; pixels are considered "different"
    when any channel differs by more than 8 (out of 255) to absorb
    anti-aliasing noise.
    """
    baseline = Image.open(baseline_path).convert("RGB")
    current = Image.open(current_png_path).convert("RGB")

    if baseline.size != current.size:
        # Size mismatch is always a hard failure.
        return 1.0

    diff = ImageChops.difference(baseline, current)
    diff_data = diff.getdata()
    total = len(diff_data)
    if total == 0:
        return 0.0

    diff_pixels = sum(
        1
        for r, g, b in diff_data
        if r > 8 or g > 8 or b > 8
    )
    return diff_pixels / total


@pytest.fixture(scope="module")
def screen():
    """Module-scoped headless screen shared across scenario tests."""
    return _make_screen()


@pytest.fixture(scope="module")
def current_platform() -> str:
    """Resolve the baseline platform for the current host."""
    import sys

    p = sys.platform.lower()
    if p.startswith("linux"):
        return "linux"
    if p.startswith("darwin"):
        return "macos"
    if p.startswith("win"):
        return "windows"
    return "other"


@pytest.fixture(scope="module")
def baselines_ready(current_platform) -> bool:
    """Skip the entire module if baselines are missing."""
    return baselines_exist(current_platform)


def _render_scenario_to_tmp(screen, scenario: str, tmp_path: Path) -> Path:
    """Render the scenario to a temporary PNG and return its path."""
    import pygame

    out_path = tmp_path / f"{scenario}_current.png"
    screen.fill((0, 0, 0))
    renderer_fn = SCENARIO_RENDERERS[scenario]
    renderer_fn(screen)
    pygame.image.save(screen, str(out_path))
    return out_path


@pytest.mark.parametrize("scenario", list(SCENARIO_RENDERERS.keys()))
def test_visual_regression_baseline(
    scenario: str,
    screen,
    current_platform: str,
    baselines_ready: bool,
    tmp_path: Path,
) -> None:
    """Compare rendered scenario against committed baseline."""
    if not baselines_ready:
        pytest.skip(
            f"Baselines missing for platform '{current_platform}'. "
            f"Run: python tests/visual_regression/generate_baselines.py"
        )

    baseline = get_baseline_path(scenario, current_platform)
    if not baseline.exists():
        pytest.skip(
            f"Baseline {baseline.name} missing for platform "
            f"'{current_platform}'. Run generate_baselines.py."
        )

    current_png = _render_scenario_to_tmp(screen, scenario, tmp_path)
    diff_ratio = _pixel_diff_ratio(baseline, current_png)
    threshold = SCENARIO_THRESHOLDS[scenario]

    if diff_ratio > threshold:
        # Persist the diff image for inspection.
        DIFF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        baseline_img = Image.open(baseline).convert("RGB")
        current_img = Image.open(current_png).convert("RGB")
        diff_img = ImageChops.difference(baseline_img, current_img)
        diff_path = DIFF_OUTPUT_DIR / f"{scenario}_diff.png"
        diff_img.save(diff_path)

        pytest.fail(
            f"Visual regression on '{scenario}': "
            f"{diff_ratio:.2%} pixel diff > {threshold:.2%} threshold. "
            f"Diff saved to {diff_path}. "
            f"If intentional, regenerate baseline: "
            f"python tests/visual_regression/generate_baselines.py "
            f"--scenario {scenario} --force"
        )


def test_baseline_coverage(current_platform: str) -> None:
    """Smoke test: ensure all 5 baselines exist for the current platform."""
    baseline_dir = get_baseline_dir(current_platform)
    missing = [
        s
        for s in SCENARIO_RENDERERS
        if not (baseline_dir / f"{s}.png").exists()
    ]
    if missing:
        pytest.fail(
            f"Missing baselines for platform '{current_platform}': {missing}. "
            f"Run: python tests/visual_regression/generate_baselines.py"
        )


def test_thresholds_are_within_design_limits() -> None:
    """Sanity test: thresholds must match V-07 Wave B-rev design (3-5%)."""
    assert STRICT_THRESHOLD == 0.01, "Strict threshold must be 1.0%"
    assert DEFAULT_THRESHOLD == 0.03, "Default threshold must be 3.0%"
    assert LOOSE_THRESHOLD == 0.05, "Loose threshold must be 5.0%"

    # All scenarios must have a threshold assigned.
    for scenario in SCENARIO_RENDERERS:
        assert scenario in SCENARIO_THRESHOLDS, (
            f"Missing threshold for scenario '{scenario}'"
        )
        # Thresholds must be in [0.01, 0.05] range per Wave B-rev design.
        assert 0.01 <= SCENARIO_THRESHOLDS[scenario] <= 0.05, (
            f"Threshold for '{scenario}' out of design range: "
            f"{SCENARIO_THRESHOLDS[scenario]}"
        )
