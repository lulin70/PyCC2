# Changelog

All notable changes to PyCC2 will be documented in this file.

## [0.3.29] - 2026-06-06

### Architecture
- **[ARCH]** services→presentation layer decoupling: 40 → ~25 violations (-39%)
  - **P0 — Enum migration**: `SoundType` + `InteractionMode` moved to `domain/value_objects/audio_enums.py`
    - 9 import sites updated across save_controller(2), game_loop(1), hud_manager(5)
    - Original presentation modules now re-export from domain for backward compat
  - **P1 — Dependency injection**: `hud_manager.initialize()` accepts optional `minimap`/`cc2_panel` params
    - `deployment_manager.start()` accepts optional `deployment_ui` param
    - Object creation moved to Assembler/GameLoop (Composition Root / caller injection)
    - Fallback imports retained for backward compatibility (only triggered when no injection)
  - **P2 — Composition Root documentation**: `game_loop_assembler.py` documented as sole legal runtime
    coupling point per Clean Architecture Dependency Rule

### Changed
- NEW: `domain/value_objects/audio_enums.py` — SoundType (22 members) + InteractionMode (4 members)
- `sound_system.py`: SoundType class definition → import + re-export from domain
- `interaction_controller.py`: InteractionMode class definition → import + re-export from domain
- `save_controller.py`: 2 SoundType imports → domain path (fixed residue at L65 with different indent)
- `game_loop.py`: 1 SoundType import → domain path; `start_deployment()` creates DeploymentUI for injection
- `hud_manager.py`: 5 imports → domain path (SoundType×1 + InteractionMode×4); initialize() accepts injected objects
- `deployment_manager.py`: start() accepts deployment_ui param; DUI import lifted to try-block scope
- `game_loop_assembler.py`: _init_hud() creates Minimap+CC2BottomPanel and injects into HUDManager

### Fixed
- **[BUGFIX]** e2e test failure: `UnboundLocalError` in deployment_manager when DUI used outside if/else scope
  - Root cause: `DUI.build_force_pool_from_settings()` and `DUI.generate_ai_deployment()` called at L190/L224
    but DUI was only defined inside the else branch; fix: lift import to top of try block

### Stats
- 3929 tests passing, 0 regressions
- Layer violations: 41 → 25 (-39%) | D-class enums: 9 → 0 | A-class runtime (non-Assembler): 3 → 0

---

## [0.3.28] - 2026-06-05

### Changed
- **[ARCH]** EnhancedRenderer God Class split: 1389 → 943 lines (-32%, -446 lines)
  - NEW: `ui_overlay_renderer.py` (389 lines) — VL flags, attack lines, queued commands, LOS overlay
  - Unit Drawing methods migrated to `UnitRenderer` (hexagon/direction/movement-mode)
  - Fixed `direction_indicator` closure capture bug — now receives unit param explicitly
- **[BUGFIX]** Duplicate `spawn_explosion` definition removed (kept ring+dynamic light version)
- **[BUGFIX]** Duplicate `spawn_muzzle_flash` definition removed (kept ParticleSystem version)
- **[CLEANUP]** Removed repeated imports in `_draw_attack_lines` (L1084-1089)
- **[CLEANUP]** Removed unused PULSE_* constants from EnhancedRenderer (moved to UIOverlayRenderer)
- **[TEST]** Updated `test_draw_dashed_line_method_exists` to check UIOverlayRenderer location

### Stats
- 3929 tests passing, 0 regressions
- enhanced_renderer.py: 1389→943 lines | ui_overlay_renderer.py: 389 lines (new) | unit_renderer.py: 311→488 lines

## [0.3.27] - 2026-06-05

### Changed
- **[CLEANUP]** Migrated 20+ bare `print()` statements to proper `logging` module calls
  - interaction_controller.py: 4 prints (HIT_TEST debug on every mouse click)
  - asset_loader.py: 8 prints (every sprite load)
  - animation_controller.py: 4 prints
  - sprite_renderer.py: 2 prints
  - event_dispatcher.py: removed entire DEBUG mouse-event logging block (6 lines)
  - input_router.py: removed 2 `# DEBUG:` comments
- **[BUGFIX]** feedback.py: `pygame.Font` → `pygame.font as Font` (uppercase doesn't exist in pygame API)
- **[BUGFIX]** feedback.py: Added missing `dataclass` import for FeedbackMessage
- **[BUGFIX]** pixel_artist_3d.py: Hardcoded `/tmp/` path → `tempfile.gettempdir()` cross-platform
- **[TEST]** Created `test_smoke_zero_coverage.py` with 27 smoke tests for previously zero-coverage modules
  - Discovered real bugs during creation: wrong class names (Config→Settings, BGMSystem→BGMGenerator, etc.)

### Stats
- 3929 tests passing (+27 new smoke tests)

## [0.3.26] - 2026-06-05

### Changed
- **[P2-1]** Circular dependency fix: Created `GameStateView` Protocol (`domain/interfaces/`)
  - `input_router.py` now imports from domain layer instead of services layer
- **[P2-2]** pixel_artist_3d.py dead code fallback removed (simplified to direct `faction.name.lower()`)
- **[P2-3]** GameLoop God Class: Extracted `GameLoopAssembler` (140-line `__post_init__` → 10 sub-methods)
- **[Faction]** Sprite rendering fix: `_FACTION_MAP` dict for string→enum mapping after enum consolidation
- **[Direction]** `from_angle()` bug fixed: N↔S angle mapping corrected to CC2 convention (Y-down)
- **[SAVE/LOAD]** Critical bug fix: `restore_state()` passed `state=` kwarg to components with `field(init=False)`
  - HealthComponent, MoraleComponent, WeaponComponent now set `.state` AFTER construction
- **[E2E]** Upgraded E2E test suite: 20 phases/dummy mode → **38 phases/real SDL mode**
  - Phase 0: Environment Detection (auto-detect macOS vs Linux vs CI)
  - Phase 3: Input Routing verification (ESC/F3/QUIT via InputRouter)
  - Phase 4: Camera Movement simulation
  - Phase 8: Window Operations (resize handling)
  - Phase 9: Memory Stability & Shutdown (gc object count tracking)
  - Screen content verification + macOS SDL resize workaround

### Stats
- ~3910 tests passing, E2E upgraded to real SDL environment

## [0.3.25] - 2026-06-05

### Changed
- **[ARCH]** Eliminated circular dependencies between presentation→services layers
- **[ARCH]** EventBus type safety: consistent publishing patterns (no more mixed dict/typed/named events)
- **[ARCH]** God Class splits continued: multiple large modules decomposed
- **[TEST]** Test coverage expanded significantly across 90+ modules

### Fixed
- **[P0-1]** Eliminated 94 `self._parent._` penetration couplings — introduced RenderContext DI container
- **[P0-2]** Completed render-path Surface pooling: particle_system (5), lighting_effects (1), deployment_ui (2), terrain_rendering_system (3)
- **[P0-3]** Migrated 11 bare dict `publish({...})` calls to TypedDict or `publish_named()`
- **[P1-3]** Consolidated Direction enum (3→1 definition) and Faction enum (3→1 definition)
- **[P1-5]** Added logging to 6 bare `except Exception:` handlers
- **[P1-6]** Fixed reinforcement_evasion_bgm.py syntax error and removed MagicMock from production code
- **[P2-4]** Moved 6 loop-internal imports to module top level
- **[P2-5]** Replaced 4 hardcoded absolute paths with Path-based relative detection
- **[P2-2]** Replaced 26 `Any` type annotations in deployment_ui.py with proper types
- **[P1-4]** E2E test: crash tolerance reduced from 3 to 0, extracted deployment helper

### Changed
- **[Docs]** Deleted 12 outdated documentation files, version sync to 0.3.24

## [0.3.23] - 2026-06-02

### Changed
- **[OPT-01]** EventBus unification: removed redundant publish_named calls
- **[OPT-02]** EnhancedRenderer God Class split: 2243→1377 lines, 3 sub-modules extracted
- **[OPT-03]** SpriteRenderer Surface pooling: 17 allocations replaced
- **[OPT-04]** ParticlePool activation: dual-mode pool (dataclass + dict)
- **[OPT-05]** Orphan module marking: 8 modules marked PLANNED
- **[OPT-06]** Duplicate code elimination: shared rendering_utils.py, enum import consolidation
- **[OPT-07]** Hardcoded path fix: absolute path → relative

## [0.3.22] - 2026-06-02

### Fixed
- **[P0]** EventBus dual-channel bridge: publish() auto-bridges TypedDict events to named handlers
- **[P0]** Surface pooling: _get_pooled_surface() with LRU eviction
- **[P1]** Achievement persistence: load() on startup, save() on shutdown
- **[P1]** Explosion event: published in CombatDirector
- **[P1]** pyproject.toml version: 0.3.0 → 0.3.21

### Changed
- Created CHANGELOG.md, deleted 9 outdated docs

## [0.3.21] - 2026-06-02

### Fixed
- **P0 EventBus dual-channel break**: dict events now bridge to named handlers via key matching
- **P0 Surface allocation**: ProjectileTrail and DynamicShadow use cached surface pools instead of per-frame allocation
- **P1 Achievement persistence**: AchievementManager.load() called on startup, .save() on shutdown
- **P1 Explosion events**: CombatDirector publishes "Explosion" named event for camera effects
- **P0 pyproject.toml version**: 0.3.0 → 0.3.21

### Changed
- README updated to v0.3.21 with current test count (3657)
- Deleted 9 obsolete/duplicate docs (VISUAL_GAP_CONSENSUS, VISUAL_ROUTE_CORRECTION, CC2_VISUAL_STANDARDS, ISOMETRIC_ARCHITECTURE_PROPOSAL, SYSTEMATIC_FIX_PLAN, DEVSQUAD_CRITICAL_REVIEW, PERFORMANCE_OPTIMIZATION_REPORT, D6_D7_MATURITY_ROADMAP, debug_deploy.py)

### Added
- 17-phase pre-release E2E test (test_pre_release_full_journey.py)

## [0.3.20] - 2026-06-02

### Added
- Deep integration of all 4 modules into GameLoop
- EventBus: subscribe_to()/publish_named() string-based event channel
- CombatCameraController: subscribe_to() instead of subscribe()
- AchievementEventBridge: subscribe_to() instead of subscribe()
- GameLoop.__post_init__(): Creates EffectStack, CombatCameraController, AchievementManager+Bridge, ProjectileTrailSystem, DynamicShadowSystem
- GameLoop._update_logic(): Updates EffectStack, TrailSystem, ShadowSystem
- GameLoop.run(): Applies camera offset from EffectStack, restores after render
- EnhancedRenderer: set_projectile_trail_system/set_dynamic_shadow_system DI setters
- EnhancedRenderer.render(): Renders dynamic shadows + projectile trails
- CombatDirector: Publishes UnitAttacked/UnitKilled/ProjectileFired named events
- 37 integration tests (test_deep_integration.py)

## [0.3.19] - 2026-06-02

### Added
- CombatCameraController (combat_camera_controller.py) — EventBus → EffectStack bridge
- AchievementEventBridge (achievement_event_bridge.py) — EventBus → AchievementManager bridge
- DynamicShadowSystem (dynamic_shadow_system.py) — Time-of-day aware shadow rendering
- ProjectileTrailSystem (projectile_trail_system.py) — 4 trail types with particle rendering
- 24 integration tests for camera controller + achievement bridge + shadows + trails

## [0.3.18] - 2026-06-02

### Added
- Camera Effects System (camera_effects.py) — EffectStack + 5 types + 6 easings
- Achievement System (achievement_system.py) — Manager + 11 defaults + JSON persistence
- 67 tests for camera effects + achievement system

## [0.3.17] - 2026-06-02

### Fixed
- 3 flaky tests permanently fixed with semantic property verification
- 487 additional tests added (3487 total, 100% pass rate)

### Added
- Feature expansion roadmap (FEATURE_EXPANSION_ROADMAP.md)
- Tech debt inventory (TECH_DEBT_INVENTORY_v0316.md)

## [0.3.16] - 2026-06-01

### Changed
- God Class split: Extracted particle_effects_renderer.py + environment_renderer.py from EnhancedRenderer
- Color palette extraction: pixel_artist_color_palette.py
- 102 tests for cc2_hud.py
- 12 performance benchmarks

## [0.3.15] - 2026-06-01

### Fixed
- TD-062: Surface pool memory leak — OrderedDict + LRU eviction (max_size=50)
- TD-029: Visual doc overlap — 4 docs merged to 1
- M-01: Hack comments professionalized

### Added
- 419/419 E2E tests passed
- 91 real-user test scenarios

## [0.3.14] - 2026-06-01

### Fixed
- 121 weak test assertions replaced with exact value verification
- game_loop.shutdown() bug — was not setting state.running = False (hidden by assert True)

## [0.3.13] - 2026-06-01

### Fixed
- 6× __import__('random') dynamic imports replaced with static imports
- Extracted pixel_artist_enums.py from monolith

### Changed
- Critical audit: maturity score honestly assessed at 7.3/10

## [0.3.0] - 2026-05-30

### Added
- Initial release with core gameplay
- Close Combat 2 tactical wargame remake
- Pygame-based rendering engine
- AI opponent system
- Campaign system with Market Garden scenarios
