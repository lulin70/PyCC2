# PyCC2 — Close Combat 2: A Bridge Too Far Remake

**v0.2.0 | 2026-05-26**

<p align="center">
<img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python" />
<img src="https://img.shields.io/badge/Pygame-2-orange.svg" alt="Pygame" />
<img src="https://img.shields.io/badge/Tests-3325%20passed-brightgreen.svg" alt="Tests" />
<img src="https://img.shields.io/badge/CC2%20Fidelity-%E2%88%BC90%25-brightgreen.svg" alt="CC2 Fidelity" />
<img src="https://img.shields.io/badge/Status-Alpha-yellow.svg" alt="Status" />
</p>

<p align="center">
  <em>A Python recreation of Atomic Games' legendary WWII tactical wargame — Alpha Release</em>
</p>

> 🟡 **This project is in Alpha stage. The game is playable but has known rough edges.**
> Core gameplay loop works end-to-end. Some visual polish and edge cases remain.
> See [Known Issues](#known-issues) below.

---

## What's New (v0.2.0)

- **PS-01→PS-12 feature milestones completed**: Full combat loop, AI tactics, sprite rendering, audio, deployment, and more
- **63 maps** covering all Market Garden operations (was 1)
- **~90% CC2 fidelity** across all dimensions (was ~45%)
- **3325 tests passing** including integration and E2E (was 2767 backend-only)
- **AI opponent functional**: Flanking, suppression, victory point, attack, and move behaviors all working
- **Full command system**: All 7 CC2 commands operational (Move, Move Fast, Sneak, Fire, Smoke, Defend, Hide)
- **Sprite rendering**: Infantry and vehicle sprites render correctly with 8-directional facing
- **Audio system**: Weapon sounds, ambient effects, and music playback working
- **Deployment phase**: CC2-style drag-and-drop deployment from force pool

---

## Current Status: **Alpha — Playable**

This is an honest assessment of the project's current state. The core gameplay loop works from deployment through combat to victory/defeat. Remaining issues are mostly polish and edge cases.

### What Works

| Feature | Status | Notes |
|---------|--------|-------|
| **Main Menu** | ✅ Working | Full navigation, campaign/scenario selection |
| **Campaign Structure** | ✅ Working | 3 Sectors, 7 Operations, 63 Battles |
| **Map Loading** | ✅ Working | 63 map JSON files with terrain, buildings, objectives |
| **Deployment Phase** | ✅ Working | CC2-style drag-and-drop from force pool |
| **Combat Interface** | ✅ Working | Bottom panel, unit info, command buttons, timer |
| **Unit Selection** | ✅ Working | Click to select, info panel shows health/morale/ammo |
| **Command System** | ✅ Working | All 7 CC2 commands: Move, Move Fast, Sneak, Fire, Smoke, Defend, Hide |
| **AI Opponent** | ✅ Working | Flanking, suppression, VP capture, attack/move behaviors |
| **Sprite Rendering** | ✅ Working | Infantry 8-direction sprites, vehicle sprites |
| **Audio** | ✅ Working | Weapon sounds, ambient, music playback |
| **Full Gameplay Loop** | ✅ Working | Play a battle from deployment to victory/defeat |

### What Needs Polish

| Feature | Status | Notes |
|---------|--------|-------|
| **Command Queue** | ⚠️ Partial | Shift+right-click queue works, visual queue display not yet implemented |
| **Vehicle Damage Visuals** | ⚠️ Partial | Damage states tracked, visual feedback incomplete |
| **Save/Load** | ⚠️ Partial | Save system exists, full integration pending |
| **Smoke Visuals** | ⚠️ Partial | Smoke mechanics work, particle effects need improvement |
| **Map Textures** | ⚠️ Partial | Good terrain variety, some tile repetition |

### CC2 Fidelity: ~90%

| Dimension | Target | Current | Status |
|-----------|--------|---------|--------|
| Map Library | 25-30 historical maps | 63 maps with accurate terrain | ✅ Exceeds target |
| Campaign Structure | 4-layer hierarchy | Full hierarchy with operations/battles | ✅ Complete |
| Weapon System | ~50 weapons | 69 weapons with authentic stats | ✅ Complete |
| Unit Diversity | 130+ unit types | 277 templates with sprite rendering | ✅ Complete |
| AI Tactics | Mature behavior trees | Flanking, suppression, VP, attack, move | ✅ Functional |
| Visual Quality | CC2 pixel art | Sprites, terrain textures, buildings | 🟡 ~85% |
| Combat Mechanics | Suppression + morale | Swiss Cheese model, 6 suppression levels | ✅ Complete |
| Command System | 7 commands | All 7 commands operational | ✅ Complete |
| Audio | Full soundscape | Weapon sounds, ambient, music | 🟡 ~80% |

---

## Known Issues

### P1 — Polish (Degrades Experience)

1. **Command queue UI** — Shift+right-click queue works correctly but the visual queue display (showing queued waypoints) is not yet implemented.

2. **Vehicle damage visuals** — Damage states are tracked internally but visual feedback (smoke, fire, immobilized appearance) is incomplete.

3. **Smoke particle effects** — Smoke mechanics work (blocks LOS, affects morale) but the visual particle rendering needs improvement for CC2 authenticity.

4. **Map texture repetition** — Some terrain tiles show visible repetition patterns; procedural generation could benefit from more variation.

### P2 — Minor (Nice to Have)

5. **Save/Load integration** — Save system backend exists but full UI integration and battle-state serialization are pending.

6. **Audio mixing** — Some weapon sounds have inconsistent volume levels; full audio balancing pass needed.

7. **Edge case crashes** — Rare crashes when rapidly clicking during AI turn or when units are at map boundaries.

---

## About

**PyCC2** is a from-scratch recreation of **Close Combat 2: A Bridge Too Far** (Atomic Games, 1997). Set during **Operation Market Garden** (September 1944), you command Allied and Axis forces across the Dutch countryside.

Built in **Python** with **Pygame 2**, this project aims to recreate CC2's authentic combat mechanics while being fully open-source and moddable.

> **Goal**: ≥90% CC2 fidelity. **Current**: ~90%. Core systems complete, polish ongoing.

---

## Quick Start

### Prerequisites

- **Python 3.11+** (3.12+ recommended)
- **Pygame 2** (`pip install pygame`)
- **macOS / Linux / Windows**

### Installation

```bash
git clone https://github.com/lulin70/PyCC2.git
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
| Issue Command | Right-click drag (radial menu) or hotkey (Z/X/C/V/S/D/H) |
| Multi-select | Shift + Left-click |
| Queue Commands | Shift + Right-click |
| Pan Camera | Arrow keys / WASD / Edge scroll |
| Zoom | Mouse wheel |
| Pause | ESC (menu) / Space (time control) |
| LOS Check | Hold Ctrl |

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
├── data/maps/              # 63 map JSON files
├── tests/                  # 3325 tests (unit + integration + E2E)
└── docs/                   # Documentation
```

**Design Principles**:
- Domain layer is mostly framework-free (minor exceptions for numpy/pygame in legacy code)
- Event-driven via EventBus
- Fixed timestep: Logic @30 UPS, Render @60 FPS

---

## Implemented Systems

| System | Code Status | Runtime Status |
|--------|-------------|----------------|
| Swiss Cheese Damage Model | ✅ Complete | ✅ Verified |
| Suppression System (6 levels) | ✅ Complete | ✅ Verified |
| Morale & Psychology | ✅ Complete | ✅ Verified |
| Fatigue System | ✅ Complete | ✅ Verified |
| Weapon Jamming | ✅ Complete | ✅ Verified |
| Ammo Pickup/Scavenging | ✅ Complete | ✅ Verified |
| Surrender/Capture | ✅ Complete | ✅ Verified |
| Squad Degradation | ✅ Complete | ✅ Verified |
| NCO Rally | ✅ Complete | ✅ Verified |
| Smoke Tactics AI | ✅ Complete | ✅ Verified |

### AI Behaviors

| AI Type | Code Status | Runtime Status |
|---------|-------------|----------------|
| Flanking AI | ✅ Complete | ✅ Working |
| Suppression AI | ✅ Complete | ✅ Working |
| Victory Point AI | ✅ Complete | ✅ Working |
| Attack Nearest AI | ✅ Complete | ✅ Working |
| Move to Objective AI | ✅ Complete | ✅ Working |
| Basic Attack/Move | ✅ Complete | ✅ Working |

---

## Testing

```bash
# Full suite (~3300 tests)
python -m pytest tests/ -q

# By category
pytest tests/unit/ -q          # Unit tests
pytest tests/integration/ -q   # Integration tests
pytest tests/e2e/ -q           # End-to-end tests
```

The 3325 tests cover backend domain logic, UI integration, and end-to-end gameplay scenarios.

---

## Roadmap

### M1: Polish & Visual Fidelity ✅ (Completed)
- [x] Fix Unit.display_name attribute
- [x] Fix component attribute aliases
- [x] Implement AttackNearestAI / MoveToObjectiveAI
- [x] Add smoke tests for critical paths
- [x] Fix set_mode signature for Fast/Sneak
- [x] Fix sprite rendering pipeline
- [x] Fix audio playback

### M2: Core Functionality ✅ (Completed)
- [x] Add Smoke/Defend interaction modes
- [x] Fix sprite rendering pipeline
- [x] Fix audio playback
- [x] Add integration tests

### M3: Quality & Visuals (Current)
- [ ] Command queue UI
- [ ] Vehicle damage visual feedback
- [ ] Smoke particle effects
- [ ] Map texture variation
- [ ] Save/Load full integration
- [ ] Audio mixing pass

### M4: Architecture Improvements
- [ ] Slim down domain layer
- [ ] Split large UI files
- [ ] Unify unit definitions
- [ ] Performance optimization

### Target: v1.0
- [x] Full gameplay loop working end-to-end
- [x] ≥90% CC2 fidelity
- [x] Complete AI tactical behaviors
- [x] Sound effects and music
- [ ] Save/Load functionality
- [ ] Full visual polish

---

## Contributing

This is an early-stage project with many known issues. Contributions welcome:

1. **Bug Reports** — Include logs, screenshots, steps to reproduce
2. **Code** — Follow existing patterns, add tests
3. **Assets** — Sprites, sounds, maps always needed
4. **Documentation** — Improvements to docs/user guide

Contributions welcome — open an issue or pull request on GitHub.

---

## Documentation

| Document | Description |
|----------|-------------|
| [User Guide](docs/USER_GUIDE.md) | Player instructions (Chinese) |
| [Design Doc](docs/DESIGN.md) | Architecture decisions |
| [PRD](docs/PRD.md) | Product requirements |
| [Gap Analysis](docs/CC2_GAP_ANALYSIS_AND_PLAN.md) | CC2 fidelity comparison (honest assessment) |

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

*Last updated: 2026-05-26 | Version: v0.2.0 | CC2 Fidelity: ~90% | 3325 tests passing*
