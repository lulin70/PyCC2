# PyCC2 — Close Combat 2: A Bridge Too Far Remake

**v0.3.0 | 2026-05-27**

<p align="center">
<img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python" />
<img src="https://img.shields.io/badge/Pygame-2-orange.svg" alt="Pygame" />
<img src="https://img.shields.io/badge/Tests-3334%20passed-brightgreen.svg" alt="Tests" />
<img src="https://img.shields.io/badge/CC2%20Fidelity-%E2%88%BC95%25-brightgreen.svg" alt="CC2 Fidelity" />
<img src="https://img.shields.io/badge/Status-Alpha-yellow.svg" alt="Status" />
</p>

<p align="center">
  <em>A Python recreation of Atomic Games' legendary WWII tactical wargame — Alpha Release</em>
</p>

> 🟡 **This project is in Alpha stage. The game is playable but has known rough edges.**
> Core gameplay loop works end-to-end with CC2-authentic victory conditions, campaign carryover, and building garrison.
> See [Known Issues](#known-issues) below.

---

## What's New (v0.3.0)

- **CC2-authentic victory conditions**: Instant VL capture, 20-minute battle timer, point-based scoring
- **7 command hotkeys**: Z (Move Fast) / X (Sneak) / S (Fire) / C (Smoke) / V (Move) / D (Defend) / H (Hide)
- **Command queue**: Shift+right-click to queue multiple commands
- **Engineer bridge destruction**: Engineers can demolish bridges, creating impassable water gaps
- **Building garrison**: Units enter buildings for defense bonuses; window firing arc restrictions apply
- **Deployment LOS preview**: See line-of-sight before committing unit placement
- **Faction difficulty asymmetry**: Different experience/supply levels per faction (Green/Veteran/Elite/Crack)
- **Campaign day briefing**: Strategic map overview at start of each campaign day
- **Battle-to-battle unit carryover**: Surviving units persist across campaign battles
- **Campaign end screen**: Summary of campaign results after final battle
- **Enhanced terrain textures**: Improved procedural terrain with more visual variety
- **Improved unit sprites**: Tank turret rotation, wounded soldier visuals
- **Death animation**: Directional falling animation for casualties
- **Environment lighting**: Shadow rendering for buildings and terrain features
- **3334 tests passing** including integration and E2E
- **63 maps, 3 campaign sectors, 29 battles across 9 days**

---

## Current Status: **Alpha — Playable**

This is an honest assessment of the project's current state. The core gameplay loop works from deployment through combat to victory/defeat, with CC2-authentic victory conditions, campaign carryover, and building garrison. Remaining issues are mostly polish and edge cases.

### What Works

| Feature | Status | Notes |
|---------|--------|-------|
| **Main Menu** | ✅ Working | Full navigation, campaign/scenario selection |
| **Campaign Structure** | ✅ Working | 3 Sectors, 7 Operations, 29 Battles across 9 Days |
| **Campaign Day Briefing** | ✅ Working | Strategic map overview at start of each day |
| **Campaign Carryover** | ✅ Working | Surviving units persist between battles |
| **Campaign End Screen** | ✅ Working | Summary of campaign results |
| **Map Loading** | ✅ Working | 63 map JSON files with terrain, buildings, objectives |
| **Deployment Phase** | ✅ Working | CC2-style drag-and-drop from force pool, LOS preview |
| **Combat Interface** | ✅ Working | Bottom panel, unit info, command buttons, timer |
| **Unit Selection** | ✅ Working | Click to select, info panel shows health/morale/ammo |
| **Command System** | ✅ Working | All 7 CC2 commands with hotkeys: Z/X/S/C/V/D/H |
| **Command Queue** | ✅ Working | Shift+right-click to queue multiple commands |
| **Victory Conditions** | ✅ Working | Instant VL capture, 20min timer, point scoring |
| **Building Garrison** | ✅ Working | Units enter buildings with defense bonuses |
| **Window Firing Arc** | ✅ Working | Building windows restrict firing direction |
| **Bridge Destruction** | ✅ Working | Engineers can demolish bridges |
| **Faction Difficulty** | ✅ Working | Asymmetric experience/supply per faction |
| **AI Opponent** | ✅ Working | Flanking, suppression, VP capture, attack/move behaviors |
| **Sprite Rendering** | ✅ Working | Infantry 8-direction sprites, vehicle sprites with turret rotation |
| **Death Animation** | ✅ Working | Directional falling animation |
| **Environment Lighting** | ✅ Working | Shadow rendering |
| **Audio** | ✅ Working | Weapon sounds, ambient, music playback |
| **Full Gameplay Loop** | ✅ Working | Play a battle from deployment to victory/defeat |

### What Needs Polish

| Feature | Status | Notes |
|---------|--------|-------|
| **Command Queue UI** | ⚠️ Partial | Queue works, visual waypoint display pending |
| **Vehicle Damage Visuals** | ⚠️ Partial | Damage states tracked, visual feedback incomplete |
| **Save/Load** | ⚠️ Partial | Save system exists, full integration pending |
| **Smoke Visuals** | ⚠️ Partial | Smoke mechanics work, particle effects need improvement |

### CC2 Fidelity: ~95%

| Dimension | Target | Current | Status |
|-----------|--------|---------|--------|
| Map Library | 25-30 historical maps | 63 maps with accurate terrain | ✅ Exceeds target |
| Campaign Structure | 4-layer hierarchy | Full hierarchy with carryover & day briefing | ✅ Complete |
| Weapon System | ~50 weapons | 69 weapons with authentic stats | ✅ Complete |
| Unit Diversity | 130+ unit types | 277 templates with sprite rendering | ✅ Complete |
| AI Tactics | Mature behavior trees | Flanking, suppression, VP, attack, move | ✅ Functional |
| Visual Quality | CC2 pixel art | Sprites, terrain textures, buildings, shadows | ✅ ~90% |
| Combat Mechanics | Suppression + morale | Swiss Cheese model, 6 suppression levels | ✅ Complete |
| Command System | 7 commands | All 7 commands with hotkeys | ✅ Complete |
| Victory Conditions | CC2-authentic | Instant VL capture, 20min timer, point scoring | ✅ Complete |
| Building Garrison | CC2 building entry | Defense bonuses, window firing arcs | ✅ Complete |
| Bridge Destruction | Engineer demolitions | Engineers can destroy bridges | ✅ Complete |
| Audio | Full soundscape | Weapon sounds, ambient, music | 🟡 ~85% |

---

## Known Issues

### P1 — Polish (Degrades Experience)

1. **Command queue UI** — Shift+right-click queue works correctly but the visual waypoint display is not yet implemented.

2. **Vehicle damage visuals** — Damage states are tracked internally but visual feedback (smoke, fire, immobilized appearance) is incomplete.

3. **Smoke particle effects** — Smoke mechanics work (blocks LOS, affects morale) but the visual particle rendering needs improvement for CC2 authenticity.

### P2 — Minor (Nice to Have)

4. **Save/Load integration** — Save system backend exists but full UI integration and battle-state serialization are pending.

5. **Audio mixing** — Some weapon sounds have inconsistent volume levels; full audio balancing pass needed.

6. **Edge case crashes** — Rare crashes when rapidly clicking during AI turn or when units are at map boundaries.

---

## About

**PyCC2** is a from-scratch recreation of **Close Combat 2: A Bridge Too Far** (Atomic Games, 1997). Set during **Operation Market Garden** (September 1944), you command Allied and Axis forces across the Dutch countryside.

Built in **Python** with **Pygame 2**, this project aims to recreate CC2's authentic combat mechanics while being fully open-source and moddable.

> **Goal**: ≥90% CC2 fidelity. **Current**: ~95%. Core systems complete, polish ongoing.

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
| Issue Command | Right-click drag (radial menu) or hotkey (Z/X/S/C/V/D/H) |
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
├── tests/                  # 3334 tests (unit + integration + E2E)
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
| Victory Conditions | ✅ Complete | ✅ Verified |
| Building Garrison | ✅ Complete | ✅ Verified |
| Bridge Destruction | ✅ Complete | ✅ Verified |
| Campaign Carryover | ✅ Complete | ✅ Verified |
| Faction Difficulty | ✅ Complete | ✅ Verified |

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

The 3334 tests cover backend domain logic, UI integration, and end-to-end gameplay scenarios.

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
- [x] CC2-authentic victory conditions (instant VL capture, 20min timer, point scoring)
- [x] 7 command hotkeys (Z/X/S/C/V/D/H)
- [x] Command queue (Shift+right-click)
- [x] Engineer bridge destruction
- [x] Building garrison with defense bonuses
- [x] Window firing arc restriction
- [x] Deployment LOS preview
- [x] Faction difficulty asymmetry
- [x] Campaign day briefing with strategic map
- [x] Battle-to-battle unit carryover
- [x] Campaign end screen
- [x] Enhanced terrain textures
- [x] Improved unit sprites (tank turret rotation, wounded visuals)
- [x] Death animation (directional falling)
- [x] Environment lighting (shadows)

### M3: Quality & Visuals (Current)
- [ ] Command queue UI (visual waypoint display)
- [ ] Vehicle damage visual feedback
- [ ] Smoke particle effects
- [ ] Save/Load full integration
- [ ] Audio mixing pass

### M4: Architecture Improvements
- [ ] Slim down domain layer
- [ ] Split large UI files
- [ ] Unify unit definitions
- [ ] Performance optimization
- [ ] Clean up duplicate morale modules
- [ ] Fix bare except blocks
- [ ] Resolve infra/ vs infrastructure/ duplication

### Target: v1.0
- [x] Full gameplay loop working end-to-end
- [x] ≥90% CC2 fidelity
- [x] Complete AI tactical behaviors
- [x] Sound effects and music
- [x] CC2-authentic victory conditions
- [x] Campaign carryover system
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

*Last updated: 2026-05-27 | Version: v0.3.0 | CC2 Fidelity: ~95% | 3334 tests passing*
