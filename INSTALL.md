# Installation Guide — PyCC2 v0.5.0

> **This document has been updated to v0.5.0. For earlier version information, see Git history.**

**Complete installation instructions for all platforms | Updated: 2026-06-14**

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Python Setup](#python-setup)
3. [Standard Installation](#standard-installation)
4. [Platform-Specific Notes](#platform-specific-notes)
5. [Configuration](#configuration)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)
8. [Development Setup](#development-setup)
9. [Uninstallation](#uninstallation)

---

## System Requirements

### Minimum Specifications

| Component | Requirement |
|-----------|-------------|
| **OS** | macOS 12+, Ubuntu 22.04+, Windows 10+ |
| **Python** | 3.11 or later (3.12+ recommended) |
| **RAM** | 4 GB (8 GB recommended) |
| **Disk Space** | 500 MB free (1 GB for dev dependencies) |
| **Display** | 1280×720 minimum, 1440×900 recommended |
| **Input Devices** | Mouse + Keyboard |

### Recommended Specifications

| Component | Requirement |
|-----------|-------------|
| **OS** | macOS 14+ (Apple Silicon M1/M2/M3) |
| **Python** | 3.12 or 3.13 |
| **RAM** | 8 GB or more |
| **Display** | 1440×900 or higher, Retina display support |

---

## Python Setup

### Check Current Version

```bash
python3 --version
# Expected output: Python 3.11.x, 3.12.x, or 3.13.x
```

If you see Python 3.10 or earlier, you need to upgrade:

**macOS (Homebrew)**:
```bash
brew install python@3.12
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
```

**Windows**: Download from https://www.python.org/downloads/

### Verify pip

```bash
python3 -m pip --version
# Expected: pip 24.x from Python 3.12
```

---

## Standard Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/lulin70/PyCC2.git
cd PyCC2
```

### Step 2: Create Virtual Environment (Strongly Recommended)

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows CMD
# .venv\Scripts\Activate.ps1    # PowerShell
```

You'll see `(.venv)` in your terminal prompt when active.

### Step 3: Install Package

```bash
# Basic installation (runtime only)
pip install -e .

# OR: Full installation with development tools
pip install -e ".[dev]"
```

This installs PyCC2 in "editable" mode — changes to source code are immediately available without reinstalling.

**Core Dependencies Installed Automatically**:
- `pygame>=2.2` — 2D game framework (rendering, input, audio via SDL2)
- `numpy>=1.26` — Numerical operations (map grids, vector math)
- `pydantic>=2.0` — Data validation (save files, config schemas)

**Development Dependencies** (with `[dev]`):
- `pytest>=7.4` — Test framework with coverage reporting
- `ruff>=0.1` — Extremely fast linter and formatter (Rust-based)
- `mypy>=1.7` — Static type checker
- `pre-commit>=3.5` — Git hooks for automated quality checks
- `hypothesis>=6.100` — Property-based testing

---

## Platform-Specific Notes

### macOS (Apple Silicon M1/M2/M3)

✅ **No special steps needed** — pygame 2.2+ natively supports Apple Silicon via SDL2.

**Retina Display**: PyCC2 auto-detects Retina mode and scales appropriately.

**Audio**: Uses CoreAudio via pygame. If you hear no sound:
```bash
python -c "import pygame; pygame.init(); pygame.mixer.init(); print('Audio OK')"
```

**Performance Tip**: Ensure you're running native Python (not Rosetta translation).

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

**Note on Display Driver**: If you get display errors, try:
```bash
export SDL_VIDEODRIVER=x11
```

### Windows

**WSL2 Recommended** (best compatibility):
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
pycc2
```

---

## Configuration

### Engine Configuration

PyCC2 uses TOML configuration files located in `config/`:

| File | Purpose |
|------|---------|
| `config/engine.toml` | Game engine settings (display, physics, AI) |
| `config/logging.conf` | Logging configuration |
| `config/secrets.toml.example` | Template for sensitive data (copy to `secrets.toml`) |

**Example engine.toml settings**:
```toml
[display]
base_width = 1280
base_height = 720
fullscreen = false
vsync = true

[gameplay]
logic_ups = 30        # Logic updates per second
render_fps = 60       # Target render framerate
time_scale = 1.0      # Game speed multiplier

[audio]
enabled = true
master_volume = 0.8
music_volume = 0.6
sfx_volume = 0.9
```

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `PYCC2_DATA_DIR` | Override data directory path | `data/` |
| `PYCC2_SAVE_DIR` | Override save directory path | `saves/` |
| `PYCC2_LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` |
| `SDL_VIDEODRIVER` | SDL video driver (Linux) | auto-detect |

---

## Verification

### Test Suite

```bash
# Full test suite (~3513 tests expected)
pytest tests/ -q --tb=short

# Quick smoke test (just confirms import works)
python -c "
from pycc2.domain.entities.unit import Unit, Faction, UnitType
from pycc2.domain.systems.ballistic import BallisticEngine
from pycc2.presentation.rendering.sprite_renderer import SpriteRenderer
print('✅ All core modules importable')
"
```

### Launch Game

```bash
# Start the game
pycc2

# Or using Python module
python -m pycc2.main
```

**Expected behavior**:
1. A window opens (1280×720 or your screen resolution)
2. Main menu appears with options: New Campaign, Quick Battle, Tutorial, Settings, Exit
3. Console output shows game configuration
4. No errors or crashes

---

## Troubleshooting

### Common Issues

#### `ModuleNotFoundError: No module named 'pycc2'`

**Cause**: Forgot to install in editable mode

**Solution**:
```bash
pip install -e .
```

#### `pygame.error: No video device available`

**Cause**: Display/server issue

**Solutions by platform**:
```bash
# macOS: Grant Terminal screen recording permission
# System Preferences > Security & Privacy > Privacy > Screen Recording

# Linux: Set display driver
export DISPLAY=:0 && export SDL_VIDEODRIVER=x11

# WSL: Install VcXsrv or use WSLg (built-in since Windows 11)
```

#### Tests fail with `ModuleNotFoundError`

**Cause**: Virtual environment not activated or dev dependencies missing

**Solution**:
```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

#### Audio doesn't work

**Cause**: Volume muted or CI/headless environment

**Solutions**:
1. Check system volume isn't muted
2. Test pygame audio separately:
   ```bash
   python -c "import pygame; pygame.mixer.init(); print(pygame.mixer.get_init())"
   ```
3. Some CI environments don't have audio hardware — this is expected and non-fatal

#### Performance seems slow

**Solutions**:
1. Ensure native Python (not Rosetta on Apple Silicon)
2. Reduce window size in settings
3. Close other resource-intensive applications

#### `SyntaxError: expected ':'` or match/case errors

**Cause**: Python version too old (need 3.11+ for match/case)

**Solution**:
```bash
python3 --version  # Must be 3.11+
```

#### Import errors on Windows

**Cause**: Path issues or missing DLLs

**Solution**:
```cmd
# Try running from project root
cd PyCC2
.venv\Scripts\activate
python -m pycc2.main
```

---

## Development Setup

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Code Quality Tools

```bash
# Lint check
ruff check src/ tests/

# Auto-format code
ruff format src/ tests/

# Type checking (domain layer should be fully typed)
mypy src/pycc2/domain/

# Run pre-commit hooks (installs git hooks)
pre-commit install

# Run all pre-commit checks manually
pre-commit run --all-files
```

### Running Tests

```bash
# All tests (full suite)
pytest tests/ -v

# By category
pytest tests/unit/ -q              # Unit tests (~3100 tests)
pytest tests/integration/ -q        # Integration tests (6 test files)
pytest tests/e2e/ -q                # E2E tests (22 test files)

# With coverage report
pytest tests/ --cov=src/pycc2 --cov-report=term-missing

# With HTML coverage report (opens in browser)
pytest tests/ --cov=src/pycc2 --cov-report=html
open htmlcov/index.html             # macOS
# start htmlcov/index.html         # Windows

# Run specific test file
pytest tests/e2e/test_e2e_full_coverage.py -v

# Run tests matching keyword
pytest tests/ -v -k "ballistic"     # All ballistic-related tests
pytest tests/ -v -k "ai"            # All AI-related tests
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

# Optionally remove virtual environment
rm -rf .venv

# Or remove entire project directory (including source)
cd ..
rm -rf PyCC2
```

---

## Getting Help

If you encounter installation issues:

1. **Check the troubleshooting section** above for common solutions
2. **Search existing GitHub Issues** — someone may have already solved it
3. **Open a new Issue** with:
   - Your OS and version
   - Python version (`python --version`)
   - Full error message (use code blocks)
   - Steps to reproduce
   - What you expected vs what happened

---

## Next Steps

After successful installation:

1. 📖 Read the [User Guide](docs/USER_GUIDE.md) for gameplay instructions
2. 🎮 Start playing: `pycc2`
3. 🧪 Run tests: `pytest tests/ -q`
4. 🤝 Consider contributing — see README.md for details

---

*Document Version*: 3.41
*Last Updated*: 2026-06-14
*Compatible with*: PyCC2 v0.5.0+
