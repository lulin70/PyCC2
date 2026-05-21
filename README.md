# PyCC2 — Close Combat 2: A Bridge Too Far Remake (WIP)

**v0.8-alpha | 2026-05-21**

<p align="center">
<img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python" />
<img src="https://img.shields.io/badge/Pygame-2-orange.svg" alt="Pygame" />
<img src="https://img.shields.io/badge/Tests-2200%20passed-brightgreen.svg" alt="Tests" />
<img src="https://img.shields.io/badge/CC2%20Fidelity-%E2%88%BC65%25-orange.svg" alt="CC2 Fidelity" />
<img src="https://img.shields.io/badge/Maps-28-informational.svg" alt="Maps" />
<img src="https://img.shields.io/badge/Status-Alpha-red.svg" alt="Status" />
</p>

<p align="center">
  <em>A Python recreation of Atomic Games' legendary WWII tactical wargame — Work in Progress</em>
</p>

> ⚠️ **WARNING: This is an ALPHA version with known issues.** See [Known Issues](#known-issues) below.

---

## Current Status: **ALPHA — Playable but Incomplete**

### What Works ✅

| Feature | Status | Notes |
|---------|--------|-------|
| **Campaign System** | ✅ Working | 3 Sectors, 7 Operations, 29 Battles structure |
| **Deployment Phase** | ✅ Working | Drag-and-drop unit placement, RP system |
| **Unit Selection** | ✅ Fixed | Left-click to select, right-click to command |
| **Combat Mechanics** | ⚠️ Partial | Core systems implemented, needs integration testing |
| **AI System** | ⚠️ Basic | Simple AI behaviors, tactical AI incomplete |
| **28 Maps** | ✅ Loaded | All Market Garden maps present |
| **69 Weapons** | ✅ Defined | Weapon parameters configured |
| **80 Unit Types** | ✅ Defined | Unit templates created |

### Known Issues 🔴

#### Critical (Blocks Gameplay)
1. **Visual Quality** — Map rendering is basic, units are simple shapes (not sprites)
2. **Combat Flow** — After selecting units, combat interaction is limited
3. **Audio** — Sound system initialization fails on some systems
4. **Performance** — May lag on lower-end hardware

#### Important (Affects Experience)
5. **Minimap** — Click-to-center not working correctly
6. **Camera** — Zoom/pan could be smoother
7. **HUD** — Unit info panel shows but lacks detail
8. **AI Behavior Trees** — Import errors for some AI modules

#### Minor (Cosmetic)
9. **UI Polish** — Buttons, panels need visual refinement
10. **Animations** — No smooth transitions or effects

---

## About

**PyCC2** is a from-scratch recreation of **Close Combat 2: A Bridge Too Far** (Atomic Games, 1997). Set during **Operation Market Garden** (September 1944), you command Allied and Axis forces across the Dutch countryside.

Built in **Python** with **Pygame 2**, this project aims to recreate CC2's authentic combat mechanics while being fully open-source and moddable.

> **Current CC2 Fidelity: ~65%** — Core mechanics implemented, visual polish and gameplay integration ongoing.

---

## Quick Start

### Prerequisites

- **Python 3.11+** (3.12+ recommended)
- **Pygame 2** (`pip install pygame`)
- **macOS / Linux / Windows**

### Installation

```bash
git clone https://github.com/user/pycc2.git
cd PyCC2
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
pip install -e .
```

### Running

```bash
python -m pycc2.main
```

### Controls

| Action | Input |
|--------|-------|
| Select Unit | Left-click |
| Command Unit | Right-click (after selection) |
| Multi-select | Shift + Left-click |
| Pan Camera | Arrow keys / Middle mouse drag |
| Zoom | Mouse wheel |
| Pause | ESC / Space |

---

## Technical Architecture

```
PyCC2/
├── src/pycc2/
│   ├── domain/              # Core game logic (pure Python, testable)
│   │   ├── ai/             # AI behaviors, tactical AIs
│   │   ├── components/     # Health, Morale, Weapon, Position
│   │   ├── entities/       # Unit, GameMap, Projectile
│   │   └── systems/        # Campaign, Combat, Supply
│   ├── services/           # Game loop, AI service, Event bus
│   ├── presentation/       # Rendering, Input, UI, Audio
│   └── infrastructure/     # Save system, Config
├── data/maps/              # 28 map JSON files
├── tests/                  # 2200+ tests
└── docs/                   # Documentation
```

**Design Principles**:
- Domain layer has **zero framework imports**
- Event-driven via EventBus
- Fixed timestep: Logic @30 UPS, Render @60 FPS

---

## Implemented Systems (Technical Detail)

### Combat Mechanics (Backend)

These systems are **implemented in code** but may not be fully integrated into gameplay:

| System | Implementation Status |
|--------|----------------------|
| Swiss Cheese Damage Model | ✅ Complete |
| Suppression System (6 levels) | ✅ Complete |
| Morale & Psychology | ✅ Complete |
| Fatigue System | ✅ Complete |
| Weapon Jamming | ✅ Complete |
| Ammo Pickup/Scavenging | ✅ Complete |
| Surrender/Capture | ✅ Complete |
| Squad Degradation | ✅ Complete |
| NCO Rally | ✅ Complete |
| Smoke Tactics AI | ✅ Complete |

### AI Behaviors (Partially Integrated)

| AI Type | Status |
|---------|--------|
| Flanking AI | ⚠️ Code exists, import issues |
| Suppression AI | ⚠️ Code exists, import issues |
| Victory Point AI | ⚠️ Code exists, import issues |
| Basic Attack/Move | ✅ Working |

---

## Testing

```bash
# Full suite (~2200 tests)
python -m pytest tests/ -q

# By category
pytest tests/unit/ -q          # Unit tests
pytest tests/integration/ -q   # Integration tests
```

**Note**: High test count reflects thorough backend testing. Frontend/UI integration testing is limited.

---

## Roadmap

### v0.9 (Next Release)
- [ ] Fix all critical issues blocking gameplay
- [ ] Improve map visuals (textures, terrain detail)
- [ ] Add unit sprites (or better shapes)
- [ ] Integrate combat mechanics into gameplay loop
- [ ] Fix AI behavior tree imports

### v1.0 (Target)
- [ ] Full gameplay flow working end-to-end
- [ ] Visual polish matching CC2 aesthetic
- [ ] Complete AI tactical behaviors
- [ ] Sound effects and music
- [ ] Save/Load functionality
- [ ] Tutorial for new players

---

## Contributing

This is a work-in-progress project. Contributions welcome:

1. **Bug Reports** — Include logs, screenshots, steps to reproduce
2. **Code** — Follow existing patterns, add tests
3. **Assets** — Sprites, sounds, maps always needed
4. **Documentation** — Improvements to docs/user guide

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

---

## Documentation

| Document | Description |
|----------|-------------|
| [User Guide](docs/PLAYER_GUIDE.md) | Player instructions (Chinese) |
| [Design Doc](docs/DESIGN.md) | Architecture decisions |
| [PRD](docs/PRD.md) | Product requirements |
| [Gap Analysis](docs/GAP_ANALYSIS.md) | CC2 fidelity comparison |

---

## License

MIT License — see [LICENSE](LICENSE)

Close Combat 2 is a trademark of its respective owners. This is an unofficial fan remake for educational purposes.

---

## Acknowledgments

- **Atomic Games** — For the original Close Combat series
- **Dr. Steven Silver** — For the military psychology model
- **OpenCombat** — For CC2 analysis reference
- **Community contributors** — For code, feedback, and patience during development

---

*Last updated: 2026-05-21 | Version: 0.8-alpha*
