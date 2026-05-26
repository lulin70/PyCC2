# Installation Guide — PyCC2

Complete installation instructions for PyCC2 **v0.1.1** on all supported platforms.

### Version History

| Version | Date | Notes |
|---------|------|-------|
| v1.8 | 2026-05-19 | P5/P6/P7 Complete: Campaign Core (~60%), Combat Depth (~85%), Content Expansion (M6-M10), CC2 Fidelity ~71%, 1566 tests, 10 missions, 10 maps |
| v1.7 | 2026-05-19 | CC2 gap analysis, Roadmap revised to P5 Campaign Core, Night combat, Anti-tank armor, Weather rendering, Trilingual docs, 1377 tests |
| v1.6 | 2026-05-19 | P4 Week 2: Campaign expanded to 5 missions, Tutorial system, Performance optimizations, 1270 tests |
| v1.5 | 2026-05-18 | P4 Week 1: GameLoop decomposition, Settings menu, Security hardening, 1163 tests |
| v1.4 | 2025-05-18 | P3-Fix: 4 critical bugs resolved (weapons/load/AI/entry) |
| v1.3 | 2026-05-17 | Complete Edition baseline |

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Python Setup](#python-setup)
3. [Standard Installation](#standard-installation)
4. [Platform-Specific Notes](#platform-specific-notes)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Development Setup](#development-setup)
8. [Uninstallation](#uninstallation)

---

## System Requirements

### Minimum

| Component | Requirement |
|-----------|-------------|
| OS | macOS 12+, Ubuntu 22.04+, Windows 10+ |
| Python | 3.11 or later (3.12+ recommended) |
| RAM | 4 GB |
| Disk | 200 MB free |
| Display | 1280x720 minimum, 1440x900 recommended |
| Input | Mouse + Keyboard |

### Recommended

| Component | Requirement |
|-----------|-------------|
| OS | macOS 14+ (Apple Silicon M1/M2/M3) |
| Python | 3.12 or 3.13 |
| RAM | 8 GB |
| Display | 1440x900 or higher, Retina display |

---

## Python Setup

### Check Python Version

```bash
python3 --version
# Expected: Python 3.11.x, 3.12.x, or 3.13.x
```

If you see Python 3.10 or earlier, you need to upgrade:

**macOS (Homebrew)**:
```bash
brew install python@3.12
```

**Linux (apt)**:
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
```

**Windows**:
Download from https://www.python.org/downloads/

### Verify pip

```bash
python3 -m pip --version
# Expected: pip 24.x from Python 3.12
```

---

## Standard Installation

### Step 1: Get the Source

```bash
git clone https://github.com/user/pycc2.git
cd PyCC2
```

### Step 2: Virtual Environment (Strongly Recommended)

```bash
# Create
python3 -m venv .venv

# Activate
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows CMD
# .venv\Scripts\Activate.ps1    # PowerShell
```

You'll see `(.venv)` in your terminal prompt when active.

### Step 3: Install Package

```bash
pip install -e .
```

This installs PyCC2 in "editable" mode — changes to source code are immediately available without reinstalling.

**Core dependencies installed automatically**:
- `pygame>=2.2` — 2D game framework (rendering, input, audio via SDL2)
- `numpy>=1.26` — Numerical operations (map grids, vector math)
- `pydantic>=2.0` — Data validation (save files, config schemas)

### Step 4: Verify

```bash
python -c "import pycc2; print('PyCC2 imported successfully')"
python -m pytest tests/ -q --tb=no
# Expected: 1377 passed in ~30 seconds
```

---

## Platform-Specific Notes

### macOS (Apple Silicon M1/M2/M3)

No special steps needed — pygame 2.2+ natively supports Apple Silicon via SDL2.

**Retina Display**: PyCC2 auto-detects Retina mode and scales appropriately. On a 1440x900 physical display, you'll get crisp HiDPI rendering at effective 2880x1800.

**Audio**: Uses CoreAudio via pygame. If you hear no sound:
```bash
# Test pygame audio separately
python -c "import pygame; pygame.init(); pygame.mixer.init(); print('Audio OK')"
```

**Python version**: The project uses `match/case` syntax (requires Python 3.10+) and type parameter syntax. Python 3.12 is recommended for best compatibility with all features.

### Linux (Ubuntu/Debian)

Install system dependencies for pygame's SDL2 backend:

```bash
sudo apt install \
    libsdl2-dev \
    libsdl2-image-dev \
    libsdl2-mixer-dev \
    libsdl2-ttf-dev \
    libportmidi-dev \
    libpng-dev
```

Then proceed with standard installation.

**Note on SDL_VIDEODRIVER**: If you get display errors, try:
```bash
export SDL_VIDEODRIVER=x11
```

### Windows (WSL2 recommended)

For best results, use WSL2 with X11 forwarding:

```bash
# In WSL terminal
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3-pip libsdl2-dev
# Then follow Standard Installation
```

**Native Windows** also works:
```cmd
# In PowerShell or CMD
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python scripts/visual_test.py
```

---

## Verification

### Test Suite

```bash
# Full test suite (should pass all 2767)
python -m pytest tests/ -q

# Quick smoke test (just confirms import works)
python -c "
from pycc2.domain.entities.unit import Unit, Faction, UnitType
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer
print('All core modules importable')
"
```

### Launch Demo

```bash
python scripts/visual_test.py
```

You should see:
1. A window opens (1440x900 or your screen resolution)
2. Console output showing game configuration
3. A battlefield with green (Allied) and gray (Axis) units
4. Interactive controls (click to select, right-click to move/attack)

Expected console output includes:
- Display dimensions and DPI info
- Active P3 features list
- Allied and Axis unit rosters
- AI configuration details
- Audio and save system status

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'pycc2'`

You forgot to install in editable mode:
```bash
pip install -e .
```

### `pygame.error: No video device available`

Display/server issue. Try:
```bash
# macOS: Allow Terminal access in System Preferences > Security & Privacy > Privacy
# Linux: export DISPLAY=:0 && export SDL_VIDEODRIVER=x11
# WSL: Install VcXsrv or use WSLg (built-in since Windows 11)
```

### Tests fail with `ModuleNotFoundError`

Make sure you've activated the virtual environment and installed dev dependencies:
```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

### Audio doesn't work

PyCC2 uses procedural audio (generates sounds mathematically). If silent:
1. Check system volume isn't muted
2. Try: `python -c "import pygame; pygame.mixer.init(); print(pygame.mixer.get_init())"`
3. Some CI/headless environments don't have audio hardware — this is expected and non-fatal

### Performance seems slow

1. Ensure you're running native Python (not Rosetta translation on Apple Silicon)
2. Try reducing window size: edit `scripts/visual_test.py` and change display dimensions
3. Lower quality preset: Change `DisplayConfig.from_screen(...)` parameters

### `SyntaxError: expected ':'` or match/case errors

Your Python version is too old. PyCC2 requires **Python 3.11+** (uses `match/case` statements):
```bash
python3 --version  # Must be 3.11+
```

---

## Development Setup

### Install Dev Dependencies

```bash
pip install -e ".[dev]"
```

This installs additional tools:
- **pytest>=7.4** + plugins — Test runner with coverage, mocking, randomization
- **ruff>=0.1** — Linter and formatter (extremely fast, Rust-based)
- **mypy>=1.7** — Static type checker
- **pre-commit>=3.5** — Git hooks for automated quality checks
- **hypothesis>=6.100** — Property-based testing
- **freezegun**, **scipy** — Test utilities

### Code Quality Tools

```bash
# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check (optional, may have false positives)
mypy src/pycc2/domain/  # Domain layer should be fully typed

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# By category
pytest tests/unit/ -q              # Fastest: pure logic tests
pytest tests/integration/ -q        # Systems working together
pytest tests/e2e/ -q                 # Full pipeline tests

# With coverage HTML report
pytest tests/ --cov=src/pycc2 --cov-report=html
open htmlcov/index.html             # View in browser
```

### Project Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Build config, dependencies, tool settings (ruff, mypy, pytest, coverage) |
| `.pre-commit-config.yaml` | Pre-commit hook definitions |
| `pytest.ini` | pytest options (test paths, output format) |
| `mypy.ini` | mypy type checking rules |

---

## Uninstallation

```bash
# Deactivate virtual environment first
deactivate

# Remove package
pip uninstall pycc2 -y

# Optionally remove environment
rm -rf .venv

# Or remove entire project directory
cd ..
rm -rf PyCC2
```
