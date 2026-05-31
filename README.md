# PyCC2 — Close Combat 2: A Bridge Too Far (Python Remake)

**v0.3.2 | Alpha Release | May 30, 2026**

<p align="center">
<img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python" />
<img src="https://img.shields.io/badge/Pygame-2.2+-orange.svg" alt="Pygame" />
<img src="https://img.shields.io/badge/Tests-3372%20passed-brightgreen.svg" alt="Tests" />
<img src="https://img.shields.io/badge/CC2%20Fidelity-%E2%88%BC91%25-yellow.svg" alt="CC2 Fidelity" />
<img src="https://img.shields.io/badge/Status-Alpha-yellow.svg" alt="Status" />
</p>

<p align="center">
<em>A Python recreation of Atomic Games' legendary WWII tactical wargame — Playable Alpha with full combat loop</em>
</p>

> 🟡 **Alpha Status**: Core gameplay is fully functional — deployment, combat, AI, campaign, and CC2-authentic victory conditions all working.
> See [Current Status](#current-status) for detailed feature matrix.

---

## What's New in v0.3.2

### ✨ v0.3.1 — Visual Fidelity Sprint (V01-V05)

- **V01: CC2 Three-Panel HUD** (25%/45%/30% layout) matching original CC2 interface
- **V02: VP Number Display** with golden bold font + pulse animation
- **V03: Crater Depth Enhancement** with 5-layer gradient rendering + debris particles
- **V04: Irregular Explosion Fireball** with flame tongues (not perfect circles)
- **V05: CC2 Dark Color Tone Grading** (-15% brightness, warm shift)

### 🏗️ v0.3.2 — Architecture Refactoring

- **A1: Renderer Split** — 5500-line monolith → 8 focused modules (sprite/particle/lighting/terrain/unit/decoration)
- **A2: DDD Dependency Inversion** — 9 domain layer violations fixed (IEventPublisher + IRandomNumberGenerator interfaces)
- **A3: Naming Convention Audit** — Passed (unit_id/is_alive/can_act patterns consistent)
- **A4: Performance Optimization** — Particle system +16.8% FPS (1082→1263), _render_smoke bugfix

### 📊 v0.3.0 Major Features (Previous Release)

- **CC2-Authentic Victory Conditions**: Instant VL capture, 20-minute battle timer, point-based scoring
- **7 Command Hotkeys**: Z (Move Fast) / X (Sneak) / S (Fire) / C (Smoke) / V (Move) / D (Defend) / H (Hide)
- **Command Queue System**: Shift+right-click to queue multiple commands
- **Engineer Bridge Demolition**: Engineers can destroy bridges, creating impassable water gaps
- **Building Garrison System**: Units enter buildings for defense bonuses; window firing arc restrictions
- **Deployment LOS Preview**: See line-of-sight before committing unit placement
- **Faction Difficulty Asymmetry**: Different experience/supply levels per faction (Green/Veteran/Elite/Crack)
- **Campaign Day Briefing**: Strategic map overview at start of each campaign day
- **Battle-to-Battle Unit Carryover**: Surviving units persist across campaign battles
- **Campaign End Screen**: Summary of campaign results after final battle
- **Enhanced Visuals**: Improved terrain textures, tank turret rotation, wounded soldier visuals
- **Death Animation**: Directional falling animation for casualties
- **Environment Lighting**: Shadow rendering for buildings and terrain features

### 📊 Statistics

| Metric | Value |
|--------|-------|
| **Total Tests** | 3372 (all passing) ✅ |
| **E2E Tests** | 22 test files (18/18 deep integration = 100%) |
| **Maps** | 63 historical maps (Operation Market Garden) |
| **Unit Templates** | 277 (infantry, vehicles, weapons) |
| **Weapon Types** | 69 authentic CC2 weapons |
| **Campaign Battles** | 29 battles across 9 days, 3 sectors |
| **AI Behaviors** | 6 tactical AI types (flanking, suppression, VP, etc.) |
| **Code Files** | 200+ Python modules |
| **Class Definitions** | 286 classes |
| **CC2 Fidelity** | ~91% (Visual: 91%, Mechanics: 92%) ⚠️ | See [GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) for details |

---

## Current Status: **Alpha — Fully Playable**

This is an honest assessment based on runtime verification and E2E testing.

### What Works ✅

| Feature | Status | Details |
|---------|--------|---------|
| **Main Menu** | ✅ Working | Full navigation, campaign/scenario selection |
| **Campaign Structure** | ✅ Working | 3 Sectors, 7 Operations, 29 Battles, 9 Days |
| **Campaign Day Briefing** | ✅ Working | Strategic map overview at start of each day |
| **Campaign Carryover** | ✅ Working | Surviving units persist between battles |
| **Campaign End Screen** | ✅ Working | Summary of campaign results |
| **Map Loading** | ✅ Working | 63 map JSON files with accurate terrain |
| **Deployment Phase** | ✅ Working | CC2-style drag-and-drop with LOS preview |
| **Combat Interface** | ✅ Working | Bottom panel, unit info, command buttons, timer |
| **Unit Selection** | ✅ Working | Click to select, info panel shows health/morale/ammo |
| **Command System** | ✅ Working | All 7 CC2 commands with hotkeys (Z/X/S/C/V/D/H) |
| **Command Queue** | ✅ Working | Shift+right-click to queue (visual feedback pending) |
| **Victory Conditions** | ✅ Working | Instant VL capture, 20min timer, point scoring |
| **Building Garrison** | ✅ Working | Defense bonuses + window firing arcs |
| **Bridge Destruction** | ✅ Working | Engineers can demolish bridges |
| **Faction Difficulty** | ✅ Working | Asymmetric experience/supply per faction |
| **AI Opponent** | ✅ Working | Flanking, suppression, VP capture, attack/move behaviors |
| **Sprite Rendering** | ✅ Working | Infantry 8-direction sprites, vehicle turret rotation |
| **Death Animation** | ✅ Working | Directional falling animation |
| **Environment Lighting** | ✅ Working | Shadow rendering |
| **Audio** | ✅ Working | Weapon sounds, ambient, music playback |
| **Save System** | ✅ Working | HMAC-SHA256 signed saves with Pydantic validation |
| **Tutorial System** | ✅ Working | Interactive new player guidance |

### Needs Polish ⚠️

| Feature | Status | Notes |
|---------|--------|-------|
| **Command Queue UI** | ⚠️ Partial | Queue works, visual waypoint display pending |
| **Vehicle Damage Visuals** | ⚠️ Partial | Damage states tracked, visual feedback incomplete |
| **Smoke Particle Effects** | ⚠️ Partial | Mechanics work, particle rendering needs improvement |
| **Save/Load UI Integration** | ⚠️ Partial | Backend exists, full UI pending |

---

## Game Screenshots

### Combat Scenes

<table>
<tr>
<td width="50%">
<img src="assets/CC2-snapshot/战斗1.jpeg" alt="Combat Scene 1" width="100%" />
<br><em>Allied infantry advancing through Arnhem streets</em>
</td>
<td width="50%">
<img src="assets/CC2-snapshot/战斗2.jpeg" alt="Combat Scene 2" width="100%" />
<br><em>Tank engagement near bridge objective</em>
</td>
</tr>
<tr>
<td width="50%">
<img src="assets/CC2-snapshot/战斗3.jpg" alt="Combat Scene 3" width="100%" />
<br><em>Defensive position in Dutch countryside</em>
</td>
<td width="50%">
<img src="assets/CC2-snapshot/战斗4.jpeg" alt="Combat Scene 4" width="100%" />
<br><em>Urban warfare in city streets</em>
</td>
</tr>
</table>

### Strategic Map

<p align="center">
<img src="assets/CC2-snapshot/战略地图.jpg" alt="Strategic Map" width="80%" />
<br><em>Operation Market Garden — Three-sector strategic overview</em>
</p>

### More Screenshots

[![战斗5](assets/CC2-snapshot/战斗5.jpeg)](assets/CC2-snapshot/战斗5.jpeg)
[![战斗6](assets/CC2-snapshot/战斗6.jpeg)](assets/CC2-snapshot/战斗6.jpeg)
[![战斗7](assets/CC2-snapshot/战斗7.jpeg)](assets/CC2-snapshot/战斗7.jpeg)
[![战斗8](assets/CC2-snapshot/战斗8.jpeg)](assets/CC2-snapshot/战斗8.jpeg)
[![战斗9](assets/CC2-snapshot/战斗9.jpeg)](assets/CC2-snapshot/战斗9.jpeg)

[View all 13 screenshots in assets/CC2-snapshot/](assets/CC2-snapshot/)

---

## Quick Start

### Prerequisites

- **Python 3.11+** (3.12+ recommended)
- **Pygame 2.2+**
- **macOS / Linux / Windows**

### Installation

```bash
# Clone the repository
git clone https://github.com/lulin70/PyCC2.git
cd PyCC2

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install package (editable mode for development)
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

### Running the Game

```bash
# Start the game
pycc2

# Or using Python module
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
│   ├── domain/              # Core game logic (pure Python, highly testable)
│   │   ├── ai/             # Behavior Tree AI, tactical decision systems
│   │   ├── components/     # ECS: Health, Morale, Weapon, Position, Vision
│   │   ├── entities/       # Squad, Unit, GameMap, Projectile
│   │   ├── systems/        # Campaign, Combat, Ballistics, Pathfinding
│   │   └── value_objects/  # Damage, Direction, TerrainType, Vec2
│   ├── services/           # Game loop, AI service, Event bus, Combat director
│   ├── presentation/       # Rendering, Input handling, UI, Audio
│   │   ├── rendering/      # Camera, HUD, Minimap, Sprites, Isometric engine
│   │   ├── input/          # Command system, Interaction controller
│   │   ├── ui/             # Menus, Panels, Tooltips, Deployment UI
│   │   └── audio/          # Sound system, Voice commands
│   └── infrastructure/     # Save system, Config, Parsers
├── data/
│   ├── maps/               # 63 historical map JSON files
│   ├── scenarios/          # 11 scenario configurations
│   └── units/              # Unit template definitions
├── tests/                  # 3372 tests (unit + integration + E2E)
├── assets/                 # Sprites, sounds, CC2 reference screenshots
└── docs/                   # Design documents, PRD, Gap analysis
```

**Design Principles**:
- **Domain-Driven Design**: Clean separation of business logic from infrastructure
- **Event-Driven Architecture**: EventBus for loose coupling between systems
- **Fixed Timestep**: Logic @30 UPS, Rendering @60 FPS
- **Component-Based Entities**: ECS pattern for flexible unit composition
- **Behavior Tree AI**: Modular, extensible AI decision framework

---

## Implemented Systems

### Combat Systems

| System | Status | Description |
|--------|--------|-------------|
| Swiss Cheese Damage Model | ✅ Complete | Realistic penetration and damage calculation |
| Suppression System (6 levels) | ✅ Complete | From light to full suppression with morale effects |
| Morale & Psychology | ✅ Complete | Dr. Silver's military psychology model |
| Fatigue System | ✅ Complete | Performance degradation over time |
| Weapon Jamming | ✅ Complete | Historical weapon reliability (e.g., Sten 1.5%) |
| Ammo Pickup/Scavenging | ✅ Complete | Search bodies for ammo and weapons |
| Surrender/Capture | ✅ Complete | Units surrender when broken |
| Squad Degradation | ✅ Complete | Combat effectiveness declines with losses |
| NCO Rally | ✅ Complete | Sergeants can rally panicked troops |
| Smoke Tactics AI | ✅ Complete | AI uses smoke for movement cover |
| Ballistic System | ✅ Complete | Physics-based trajectory with range/drop |

### AI Behaviors

| AI Type | Status | Description |
|---------|--------|-------------|
| Flanking AI | ✅ Working | Attempts to attack from the side/rear |
| Suppression AI | ✅ Working | Pins enemies with sustained fire |
| Victory Point AI | ✅ Working | Captures and holds objectives |
| Attack Nearest AI | ✅ Working | Engages closest threat |
| Move to Objective AI | ✅ Working | Advances toward mission goals |
| Commander AI | ✅ Working | Coordinates squad-level tactics |
| Cover Seek AI | ✅ Working | Takes cover when under fire |
| Retreat AI | ✅ Working | Withdraws when overwhelmed |

### Campaign Systems

| System | Status | Description |
|--------|--------|-------------|
| Four-Layer Hierarchy | ✅ Complete | Campaign → Sector → Operation → Battle |
| Supply Lines | ✅ Complete | Land/air supply with cutoff mechanics |
| Unit Carryover | ✅ Complete | Veterans persist between battles |
| Reinforcement System | ✅ Complete | Dynamic reinforcements based on supply |
| Victory Conditions | ✅ Complete | CC2-authentic VL/timer/scoring |
| Faction Difficulty | ✅ Complete | Asymmetric Green/Veteran/Elite/Crack levels |

---

## Testing

```bash
# Full test suite (3372 tests)
pytest tests/ -q

# By category
pytest tests/unit/ -q              # Unit tests (~3100)
pytest tests/integration/ -q        # Integration tests (6 files)
pytest tests/e2e/ -q                # End-to-end tests (22 files)

# With coverage report
pytest tests/ --cov=src/pycc2 --cov-report=term-missing

# E2E deep integration tests (18 scenarios, 100% pass rate)
pytest tests/e2e/test_e2e_full_coverage.py -v
```

**Test Coverage Highlights**:
- ✅ Backend domain logic: comprehensively tested
- ✅ UI integration: key interaction paths covered
- ✅ E2E gameplay: 18 deep integration scenarios (deployment → combat → victory)
- ✅ AI behaviors: all 6 major AI types verified
- ✅ Campaign flow: multi-battle carryover validated

---

## CC2 Fidelity Assessment

| Dimension | Target | Current | Status |
|-----------|--------|---------|--------|
| **Map Library** | 25-30 historical maps | **63 maps** with accurate terrain | ✅ Exceeds |
| **Campaign Structure** | 4-layer hierarchy | **Full hierarchy** with carryover & briefing | ✅ Complete |
| **Weapon System** | ~50 weapons | **69 weapons** with authentic stats | ✅ Complete |
| **Unit Diversity** | 130+ unit types | **277 templates** with sprite rendering | ✅ Complete |
| **AI Tactics** | Mature behavior trees | **6 AI types** with BT framework | ✅ Functional |
| **Visual Quality** | CC2 pixel art | Sprites, terrain, buildings, shadows, 3-panel HUD, VP display, color grading | ✅ ~91% |
| **Combat Mechanics** | Suppression + morale | Swiss Cheese model, 6 levels | ✅ Complete |
| **Command System** | 7 commands | **All 7 commands** with hotkeys + queue | ✅ Complete |
| **Victory Conditions** | CC2-authentic | Instant VL, 20min timer, points | ✅ Complete |
| **Building Garrison** | CC2 building entry | Defense bonuses, window arcs | ✅ Complete |
| **Bridge Destruction** | Engineer demos | Engineers destroy bridges | ✅ Complete |
| **Audio** | Full soundscape | Weapons, ambient, music | 🟡 ~85% |

**Overall Fidelity: ~91%** (Visual: 91%, Mechanics: 92%) ⚠️ See [GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) for remaining gaps

---

## Roadmap

### Completed Milestones

- [x] **M1: Emergency Fixes** (May 23-24) — Fixed 5 P0 critical bugs, game became playable
- [x] **M2: Core Features** (May 25-27) — CC2 victory conditions, 7 commands, garrison, bridge destruction, campaign carryover, enhanced visuals

### Current Phase: M3 — Polish & Visual Fidelity

- [x] ~~CC2 Three-Panel HUD~~ ✅ v0.3.1-V01
- [x] ~~VP Number Display (golden bold + pulse)~~ ✅ v0.3.1-V02
- [x] ~~Crater Depth Enhancement (5-layer gradient)~~ ✅ v0.3.1-V03
- [x] ~~Irregular Explosion Fireball~~ ✅ v0.3.1-V04
- [x] ~~CC2 Dark Color Tone Grading~~ ✅ v0.3.1-V05
- [ ] Command queue UI (visual waypoint display)
- [ ] Vehicle damage visual feedback (smoke, fire, immobilized)
- [ ] Save/Load full UI integration
- [ ] Audio mixing balance pass

### Future Phases

**M4: Architecture Improvements** (v0.5) — **PARTIALLY COMPLETE (v0.3.2)**
- [x] ~~Split large files (enhanced_renderer 5500→8 modules)~~ ✅ v0.3.2-A1
- [x] ~~Domain layer dependency inversion (9 violations fixed)~~ ✅ v0.3.2-A2
- [x] ~~Naming convention unification (audit passed)~~ ✅ v0.3.2-A3
- [x] ~~Performance profiling (+16.8% FPS)~~ ✅ v0.3.2-A4
- [ ] Domain layer slimdown (75.4% → <50%)
- [ ] Unify unit definition system (4 sets → 1)
- [ ] Clean up technical debt (30 bare except → specific exceptions)

**M5: Quality & Sustainability** (v0.6)
- [ ] CI/CD enhancement (4-stage pipeline)
- [ ] Documentation consolidation
- [ ] Additional E2E test coverage
- [ ] Performance optimization for large maps

**Target: v1.0**
- [x] Full gameplay loop working end-to-end
- [x] ≥90% CC2 fidelity (currently ~90%, visual 88% / mechanics 92%)
- [x] Complete AI tactical behaviors
- [x] Sound effects and music
- [x] CC2-authentic victory conditions
- [x] Campaign carryover system
- [ ] Save/Load functionality (backend done, UI pending)
- [ ] Full visual polish

---

## Contributing

We welcome contributions! This is an early-stage project with many opportunities for involvement:

1. **Bug Reports** — Include logs, screenshots, steps to reproduce
2. **Code** — Follow existing patterns, add tests, maintain style guide
3. **Assets** — Sprites, sounds, maps always needed (see assets/README.md)
4. **Documentation** — Improvements to docs, user guides, tutorials
5. **Playtesting** — Feedback on gameplay balance and CC2 authenticity

### Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Code quality checks
ruff check src/ tests/          # Lint
ruff format src/ tests/         # Format
mypy src/pycc2/domain/          # Type check (domain layer)

# Run pre-commit hooks
pre-commit run --all-files
```

See [INSTALL.md](INSTALL.md) for complete setup instructions.

---

## Documentation

| Document | Description |
|----------|-------------|
| [User Guide](docs/USER_GUIDE.md) | Player instructions (Chinese) |
| [Installation Guide](INSTALL.md) | Detailed setup instructions |
| [Design Doc](docs/DESIGN.md) | Architecture decisions |
| [PRD](docs/PRD.md) | Product requirements document |
| [Gap Analysis](docs/CC2_GAP_ANALYSIS_AND_PLAN.md) | CC2 fidelity comparison |
| [Technical Debt](docs/TECH_DEBT.md) | Known debt items and cleanup plan |
| [Security](docs/SECURITY.md) | Security design and audit |
| [Test Plan](docs/TEST_PLAN.md) | Testing strategy and coverage goals |

---

## License

MIT License — see [LICENSE](LICENSE)

Close Combat 2 is a trademark of its respective owners. This is an unofficial fan remake for educational purposes.

---

## Acknowledgments

- **Atomic Games** — For the original Close Combat series (1997)
- **Dr. Steven Silver** — For the military psychology model underlying morale mechanics
- **OpenCombat Community** — For CC2 analysis and reverse engineering references
- **All Contributors** — For code, feedback, assets, and patience during development

---

## Star History

<a href="https://github.com/lulin70/PyCC2/stargazers">
<img src="https://api.star-history.com/svg?repos=lulin70/PyCC2&type=Date" alt="Star History Chart">
</a>

---

<p align="center"><sub>Generated on 2026-05-30 | v0.3.2 (7-dimension review v2, post-refactor) | <a href="docs/GAP_ANALYSIS.md">GAP Analysis</a> | <a href="docs/ROADMAP.md">Roadmap</a></sub></p>
