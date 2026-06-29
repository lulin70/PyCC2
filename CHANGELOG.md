# Changelog

All notable changes to PyCC2 will be documented in this file.

## [0.5.0] - 2026-06-29 (开发中)

### D9 成熟度评估 P1 修复 (D9 Maturity Assessment)
- **P1-1 README_zh 测试数表述错误**: 6 处过期表述（4367个通过/100%）已修正为实测值（4424 collected / 4398 passed / 25 skipped），含 badge + 5 处正文 + 最后更新日期。
- **P1-2 TECH_DEBT TD-058 过期**: 标记为 ✅ 已解决 — 4 文件实测行数（deployment_ui 689 / pixel_artist_3d 456 / enhanced_renderer 485 / campaign_four_layer 524）全部达标 <1500 行。状态行与表格 P1 数字对齐（2→1）。">1000 行" 计数修正（12→8，实测验证）。核查日期更新为 2026-06-29。
- **P1-3 E2E 测试隔离缺陷**: 修复 `test_vertical_slice.py::pygame_env` fixture teardown `pygame.quit()` 破坏后续测试 display 子系统 → `pygame.display.quit()`（限定 teardown 范围）。`test_visual_smoke.py::setup_pygame` 添加 `pygame.display.quit()` + `pygame.display.init()` 防御性重置。完整 E2E 套件 483 passed / 0 failed（修复前 482+1 failed）。
- **Verification**: mypy 0 errors / ruff 仅 1 预先存在的 I001 error（morale_system.py:16，非本次修改范围）/ pytest 全量回归待确认

### D9 后续发现验证 (DevSquad ConsensusEngine)
- **后续发现 1 (ruff I001 morale_system.py:16)**: ✅ **已修复** — `ruff --fix` 一键重排 `morale_types` import 块（4 个 MixedCase 名称排序）。DevSquad Worker A 独立验证：错误真实存在 + 预先存在（父 commit 253e471 已有相同 diff，引入于 commit 0f4da91 P5-1 game_loop 拆分）+ 本次 723150a 未触碰该文件。CI 现状：`ruff check .` "All checks passed!" (0 errors)。
- **后续发现 2 (TD-061 enhanced_renderer God Class)**: 🟡 **部分解决** — TD-061 描述严重过期已更新：行数 2250→485（↓78%），方法数 59→30（公开 23 / 私有 7，↓49%），清理方案中 3 个子模块（particle_effects_renderer / unit_renderer / environment_renderer）已于 commit 61b9b39 (2026-06-26) 全部提取。架构定位从 God Class 转为 Coordinator/Delegator 模式。状态从 ❌ 未解决改为 🟡 部分解决，优先级 P1→P2（残留 30 方法略超 <20 SRP 阈值，但本质是薄委托包装）。
- **Verification**: ruff 0 errors / mypy 0 errors (CI 命令 MYPYPATH=src mypy -p pycc2) / pytest 全量回归待确认
- **DevSquad 共识**: 两项发现均非 D9 P1 修复遗漏，ruff I001 为预先存在机械问题（一键修复），TD-061 描述过期是技术债登记滞后（已同步）

### Phase 4: CC2 机制补全 (D8 Remediation Plan)
- **P4-0 TacticExecutor 5 缺失 handler 修复** (前置阻断项): 补齐 FLANKING/COORDINATED_ADVANCE/CAPTURE_VL/DEFEND_VL/DEMOLISH_BRIDGE 5 个有枚举无 handler 的 TacticType。DEMOLISH_BRIDGE 搜索单位 3x3 邻域的 BRIDGE 地形并设为 BRIDGE_DESTROYED。17 个新单元测试。
- **P4-1 通用步兵伏击 AI** (新建): `AmbushAI(TacticalAIBase)` — 检测隐蔽地形（concealment>0.4）中的步兵 + 敌方接近 → SET_AMBUSH（潜伏等待）/ BREAK_AMBUSH（集中开火）。夜间加成 +0.2。新增 SET_AMBUSH/BREAK_AMBUSH 枚举 + handler。15 个单元测试。
- **P4-2 撤退断后增强**: `RetreatDecisionAI` 新增 Phase 4 断后逻辑 — HP>70% 单位发出 HOLD_POSITION + SUPPRESS_FIRE 掩护撤退。断后数量不超过撤退单位 1/3。3 个新测试。
- **P4-3 战略反击 AI** (新建): `CounterattackAI(TacticalAIBase)` — force_ratio>1.2（增援到达后力量逆转）触发反击。选 2-3 个友方单位攻击最弱敌方。新增 COUNTER_ATTACK 枚举 + handler。5 个单元测试。
- **P4-5 地形高度系统修复**: `GameMap.from_json` 从 `tiles_enhanced.height` 读取到 `height_grid`（建筑高度）。`LOSSystem._get_elevation`/`_get_building_height` 改读 `GameMap` grid 而非 enhanced dict。修复后 night_map.json 的 height_grid 有 403/672 个非零格（修复前为 0）。3 个新测试 + 2 个回归修复。
- **P4-4 补给线征用点采购 UI**: 完成 — `SupplyLineManager.procure_supply()` 接入 + `SupplyProcurementUI` 新建（参考 deployment_ui SRP 模式）+ CampaignUI 集成（新增 'supply_procurement' 字符串状态）。每点补给提升 ammo(+0.6%)/reinforcement(+0.4%)/morale(+0.3%) 速率，10/30/60 点阈值提升 SupplyLevel 等级。31 单元测试 + 227 回归测试通过。
- **Verification**: ruff 0 errors / mypy 0 errors / 83 AI behavior tests passed / 90 P4-0/P4-5 tests passed / 31 P4-4 tests passed

### Phase 5: 长期架构改进 (D8 Remediation Plan)
- **P5-4 CI 管道 4 阶段分离**: 重写 `.github/workflows/ci.yml` — lint→unit-tests→integration-tests→e2e-tests→docker-build 串行 + slow-tests/benchmark 并行。分层 timeout（10/20/15/30/20/15min）+ 每 job 独立 junit.xml artifact。
- **P5-3 slow 测试优化**: 完成 — `pixel_artist.py` 新增 `@lru_cache(maxsize=128)` sprite 缓存（`UnitSpriteGenerator.generate()` 确定性随机，缓存安全）；`create_unit_sprite()` 返回 `.copy()` 防止调用方修改污染缓存。5 个 session-scoped fixture 共享 canvas。slow 测试 3.5min→0.56s。
- **P5-1 第1批 数据文件拆分**: 完成 — 3 个大数据文件按 facade 模式拆分（共 4310→367L facade + 9 子模块）：
  - `campaign_data.py` (1456→63L facade): arnhem/nijmegen/eindhoven 3 个 sector 文件，268 测试通过
  - `cc2_authentic_weapons.py` (1854→76L facade): weapon_type_defs/allied/axis/vehicle 4 个文件，84 测试通过 / 69 weapons
  - `unit_diversity_expansion.py` (1000→228L facade): vehicle_variant/faction_variant 2 个文件，69 测试通过 / 277 templates
  - `weapon_sounds.py` (607L): 评估完成无需拆分（模块内聚）
  - 全量回归: ruff 0 / mypy 0 (356 files) / 4352 tests passed
- **P5-1 第2批 逻辑类拆分**: 完成 — 2 个大逻辑文件按 SRP 拆分（共 1529→712L facade + 8 子模块）：
  - `morale_system.py` (701→311L facade): morale_types/calculator/effects/routing 4 个子模块（types+calculator 纯计算无副作用，effects+routing 副作用隔离）。94 单元 + 145 e2e 测试通过。commit b2b51da
  - `game_loop.py` (828→401L facade): game_loop_types/rendering/updating/combat 4 个子模块（mixin 模式）。mypy 兼容性关键：mixin 类用类级属性声明替代 `self: GameLoop` 注解（Django mixin 标准模式）。102 单元 + 34 e2e + 全量 4398 测试通过。
  - 全量回归: ruff 0 / mypy 0 (364 files) / 4398 tests passed / 0 failures
- **P5-2 精简版 基础设施事件层迁移**: 完成 — 3 个事件基础设施文件从 services/ 迁移至 infrastructure/events/（方向C决策，避免全量161导入重组违反 Simplicity First）：
  - `event_bus.py` / `event_dispatcher.py` / `event_protocol.py` → `infrastructure/events/`
  - 57 个外部导入 + 3 个内部导入更新；services/__init__.py 保持 EventBus 向后兼容重导出
  - 全量回归: ruff 0 / mypy 0 (365 files) / 4398 passed / 0 failures / E2E 34 + 关键 124 测试通过

## [0.4.0] - 2026-06-27

### Phase 2: CC2 Visual Polish (D8 Remediation Plan)
- **P2-5 VP numeral display fix** (BUG): `SpriteRenderer._draw_vl_flag` production path was only drawing the flag polygon, omitting the CC2-authentic large gold numeral. Added VP value rendering (font size 52, gold color (255,220,100), 4-direction black outline, pulse animation) mirroring the `ui_overlay_renderer` fallback. `MapObjective` gained a `points` field; `GameMap.from_json` resolves VP values via `_resolve_vp_points()` using CC2 standard (Bridge=40, Road=30, LZ=20, Regular=10). 5 unit tests + 1 E2E test added.
- **P2-6 Dynamic crater rendering fix** (BUG): `EffectRenderer.spawn_explosion` was only generating transient particles, leaving no persistent ground mark. Added `_crater_decals` persistent decal list (FIFO cap 64), `_spawn_crater_decal()` using `SpriteGenerator._draw_crater_small`/`_draw_crater_large`, `render_decals()` method called in `SpriteRenderer.render` after terrain but before units/VL flags, and `clear_decals()` for map unload. 8 unit tests added.
- **P2-1 Command queue visual waypoints enhancement**: `draw_queued_commands` now renders CC2-authentic waypoint numbers (1, 2, 3...) beside each queued command target, with black-outlined white text for legibility. Attack commands now show an orange crosshair marker (circle + horizontal/vertical lines) instead of the generic cyan circle.
- **P2-2 Vehicle damage visual feedback**: Deferred to v0.5 (TD-065). Current `damage_state`/`update_damage_vfx` is generic (smoke + fire based on HP ratio); vehicle-specific differentiation (track/turret damage) requires `unit.py` core logic changes.
- **P2-3 Smoke particle effects unification**: Deferred to v0.5 (TD-066). `CC2SmokeEffect` (10-16 irregular polygon puffs) exists in `cc2_combat_effects.py` but is not wired into the production `spawn_smoke_screen` call chain.
- **P2-4 Save/Load UI**: Verified complete — `new_game_menu.py:504-565` load-game screen with save slot list; `pause_menu_controller.py:76-81` in-game pause menu has Save/Load buttons.
- **P2-7 Explosion effects cleanup**: Verified complete — `particle_system.py:297-350` `_render_explosion_ring` already implements irregular flame tongues (16-vertex polygon with noise perturbation), not concentric circles. No deduplication needed.
- **Verification**: ruff 0 errors / mypy 0 errors (344 source files) / 3691 unit tests passed / 126 targeted tests passed (including 5 VP numeral + 8 crater decal tests)

### Phase 1: Pre-Release Blockers (D8 Remediation Plan)
- **P1-1 Benchmark tests**: Verified 21/21 benchmark tests pass (regressions already fixed in D7-P0)
- **P1-2 E2E user journey**: 482 E2E tests pass — complete user journey validated (Main Menu → Campaign → Deploy → Battle → Commands → Victory Detection → 60s Long Run → Quit); 25 core journey tests pass with real pygame.event.post() event injection
- **P1-3 Version bump**: v0.3.42 → v0.4.0 across 20 files (pyproject.toml, __init__.py, 3 READMEs, 3 INSTALLs, 3 MANUALs, 8 docs)
- **Docstring fix**: __init__.py docstring "Company Command 2" → "Close Combat 2"

## [Unreleased] - 2026-06-27

### D8: Project Organization Assessment Remediation (7维度项目整理评估)
- **P0-1 Hotkey mapping fix**: README×3 (en/zh/ja) hotkey mapping corrected to match code — Z=Move / X=Move Fast / S=Sneak / C=Fire / V=Smoke (was completely wrong: Z=Move Fast / X=Sneak / S=Fire / C=Smoke / V=Move)
- **P0-2 Test count unification**: README×3 test counts unified to 4367 collected / 4327 passed (was 3 different values: badge 4298 / text 3985 / table 4369)
- **P0-3 strict_e2e_journey.py refs removed**: README_zh/ja replaced non-existent script reference with `pytest tests/e2e/ -m e2e -v`
- **P0-4 pyproject.toml description fix**: "Company Command 2" → "Close Combat 2"
- **P0-5 requirements.lock regenerated**: 308-line global pip freeze (containing torch/transformers/jupyter/etc.) → 21-line project-specific lock file via `uv pip compile` (8 packages only)
- **P0-6 scripts/archive/ deleted**: 18 files removed (15 duplicates of scripts/ + 3 obsolete scripts)
- **P0-7 CI workflow hardened**: Added `permissions: contents: read` + `concurrency: cancel-in-progress: true`
- **P0-8 Release workflow hardened**: Added ruff+mypy+bandit quality gate step; removed hardcoded version default
- **D8 Assessment Report**: docs/ASSESSMENT_D8_MATURITY.md — comprehensive 7-dimension maturity assessment (62→78→80→82/100)
- **Verification**: ruff 0 errors / 3678 unit tests passed / 136 integration tests passed

### D7-P0: Critical Fixes (D7 Assessment Remediation)
- **ruff lint**: Auto-fixed 26 errors (I001/UP037/B010/F401/UP035) + manual F841 fix; ruff check src/ tests/ → 0 errors
- **23 test failures fixed**: 2 benchmark (`_surface_pool`→`_state_manager._surface_pool`), 18 e2e (`_screen` setter→`initialize(screen)`), 1 acceptance assertion, 1 headless vsync=0, 1 Bresenham algorithm bug (`y0 += sy` misplaced causing infinite loop in `pixel_canvas.py:218`)
- **CI timeout protection**: `pytest-timeout>=2.3` + `--timeout=300` in pyproject.toml; `timeout-minutes: 30` in ci.yml (test + slow-tests jobs)
- **Version sync**: `__version__` 0.3.41→0.3.42; 11+ docs synced (README/INSTALL/USER_MANUAL 中英日 + DESIGN/PRD/ROADMAP/GAP_ANALYSIS/USER_GUIDE)
- **Dependency lock**: `requirements.lock` (308 packages) for reproducible builds
- **CI coverage gate**: `--cov-fail-under=70` added to pytest command
- **README fix**: Replaced non-existent `scripts/strict_e2e_journey.py` with `pytest tests/e2e/ -m e2e -v`
- **.gitignore**: Added `.ruff_cache/`
- **Verification**: ruff 0 errors / mypy 0 errors / 4329 passed / 72s

### D7-P1: Codebase Cleanup (D7 Assessment Remediation)
- **4 pure ghost modules deleted** (-1679 lines): `ceasefire_retreat.py` (581L), `enhanced_aar.py` (425L), `battle_replay.py` (311L), `reinforcement_evasion_bgm.py` (362L) — all had zero production references
- **2 naming conflicts resolved**:
  - `TrenchDiggingAI` dual definition: `domain/systems/` version renamed to `TrenchDiggingTracker` (progress tracker, not AI); `domain/ai/` version (TacticalAIBase subclass) is canonical
  - `weather_effects.py` dual module: `presentation/rendering/weather_effects.py` renamed to `weather_visual_effects.py` (particle rendering system); `domain/systems/weather_effects.py` is canonical business logic
- **Process files cleaned**: Deleted root `IMAGE_OPTIMIZATION_COMPLETION_SUMMARY.md`, 4 docs/ execution reports (INTEGRATION_EXECUTION_PLAN/PRONE_ENHANCEMENT/STEP1_PORTRAIT/STEP2-5), 2 overlapping test strategy docs (TEST_STRATEGY_COMPREHENSIVE/TEST_USER_CENTRIC), 21 test artifact PNGs (enhancement_test_results/ + prone_test_results/)
- **README test counts corrected**: badge 4298→4369, text 3985→4329 passed (4369 total), table updated in 3 README files (en/zh/ja)
- **Verification**: ruff 0 errors / mypy 0 errors / 100 targeted tests pass

### D7-P2: Engineering Hardening (D7 Assessment Remediation)
- **P2-1 deployment_ui.py God Class split** (commit 88fe1b9): 1183→687 lines (-41.9%); extracted 3 SRP submodules (deployment_zone_builder.py 211L + deployment_placement.py 155L + deployment_input_router.py 174L); preserved IDeploymentUI protocol via thin delegation shims; all 117 regression tests pass
- **P2-3 pip-audit + dependabot** (commit 40c9f02): CI lint job enhanced with `pip-audit --desc` dependency vulnerability scan; `.github/dependabot.yml` expanded from minimal to full config (labels, groups for minor+patch, commit-message prefixes `deps:`/`ci:`, open-pull-requests-limit 10/5)
- **P2-2 vulture dead code cleanup** (commits c147eb6 + 5c3e2be + 9d730b8):
  - 11 of 12 vulture findings cleaned: 7 unused parameters removed (engagement/inf_pos/observer_height/target_height/panic_thr/rout_thr/spread_radius), minimap.py dead `getattr` statement + `if True` redundant condition removed + `import math` hoisted to module level, render_pipeline.py + cc2_hud.py unused `_ENHANCED_*_AVAILABLE` feature-flag try blocks deleted (flags never read, imported symbols never called)
  - 1 vulture finding preserved as false positive: `renderer.py:75 fog_grid` is `IRenderer` Protocol method parameter (contract cannot be removed)
  - 2 obsolete integration tests removed (verified `_ENHANCED_POST_PROCESSING_AVAILABLE` / `_ENHANCED_UI_AVAILABLE` flags which no longer exist)
  - ruff format规范化: 37 files reformatted (dict indent alignment, trailing comma, line width) — no logic change
  - **Verification**: ruff 0 errors / mypy 0 errors / vulture 12→1 (only Protocol false positive) / 4327 tests pass
- **P2-2 docstring coverage assessment** (recorded as TD-063 in TECH_DEBT.md):
  - `interrogate src/` measured 62.8% coverage (1717/4611 definitions have docstring, 2894 missing)
  - Target 80% requires ~1972 new docstrings — too large for single session, documented as technical debt with 4-phase remediation plan (Phase A: auto-fix 808 format issues; Phase B: public API docstrings; Phase C: boy-scout rule; Phase D: CI gate with 65% baseline)
  - ruff D-rule breakdown: 1388 missing docstring (D102×911 + D101×216 + D107×167 + D100×46 + D105×36 + others×12) + 1163 format issues (D212/D400/D415/D413 etc.)

### Phase 3: God Class Split
- Split `cc2_bottom_panel.py` (2007→480 lines) into 8 focused submodules (roster/unit_detail/soldier_monitor/command_bar/minimap_section/urgency/icons/input_handler)
- Split `cc2_authentic_units.py` (1960→51 lines facade) into `unit_templates.py` + `deployment.py` + `unit_database.py` + `unit_factories/` (5 faction files)
- Split `enhanced_renderer.py` (1450→477 lines) into 10 specialized submodules (renderer_state_manager/combat_effects_coordinator/atmosphere_controller/world_renderer/environment_renderer/screen_effects_renderer/etc.)
- All public APIs preserved; 117 regression tests pass; mypy 0 errors

### Phase 4: Security Hardening
- **B314 Fixed**: Replaced `xml.etree.ElementTree.parse` with `defusedxml.ElementTree.parse` in `svg_sprite_loader.py` (XXE prevention)
- **B310 Suppressed**: Added `# nosec B310` to `resource_cache.py` (URL scheme already restricted to http/https)
- **HMAC Hardening**: `save_system.py` dev fallback switched from project-path-derived key to `secrets.token_bytes(32)` ephemeral key (saves unreadable after restart, making danger explicit)
- **subprocess Hardening**: `pixvoxel_loader.py` added `timeout=120` + `TimeoutExpired` handling; command whitelist confirmed
- **Dependency**: Added `defusedxml>=0.7` to `pyproject.toml`
- **Verification**: bandit Medium 0 issues (from 2); mypy 0 errors; ruff clean; 69 security tests pass

### Phase 5: Test Governance
- **Auto-marker**: Added `pytest_collection_modifyitems` hook in `tests/conftest.py` to auto-apply markers by directory path (`tests/unit/`→`unit`, `tests/integration/`→`integration`, `tests/e2e/`→`e2e`, `tests/benchmark/`→`benchmark`). Marker coverage 4%→100% (4369/4369).
- **Slow test marking**: Identified 7 timeout tests (>30s) via `pytest --durations=30`; marked `TestMGSquadSprite`, `TestEightDirections`, `TestCreateUnitSpriteFactory` in `test_pixel_artist.py` and `TestNewUnitSprites` in `test_content_expansion.py` with `@pytest.mark.slow`. `pytest -m "not slow"` now skips 14 slow tests.
- **TEST_PLAN.md sync**: Updated from v0.1.1 (claimed 2767) to v0.3.42 (actual 4369). Corrected pyramid: unit 3680 (84.2%), integration 138 (3.2%), e2e 530 (12.1%), benchmark 20 (0.5%), slow 14 (orthogonal).
- **E2E coverage audit**: Verified 530 existing E2E tests cover click (27 files), drag (13), select (25), move/attack (10), save/load (22). No redundant E2E added.

### Phase 6: Performance Optimization
- **Dirty rect refinement**: `suppression_overlay_renderer.py` replaced `mark_full_dirty()` with 4 targeted edge `mark_dirty(rect)` calls (top/bottom/left/right edge bands only).
- **Terrain cache optimization**: `terrain_rendering_system.py` switched from viewport-exact cache key to 8-tile grid-snapped + 2-tile margin. Camera movement within 8-tile grid no longer invalidates cache; only blit offset adjusts. Tile drawing uses relative coordinates (camera-independent).
- **FPS adaptive post-processing**: `renderer_state_manager.py` added `update_fps()` (60-frame rolling window via `time.monotonic()`) and `is_post_processing_active` property. Auto-disables color grading when avg FPS < 45, re-enables when > 55 (hysteresis). Wired into `enhanced_renderer.py` render() entry + post-processing guard.
- **Cleanup**: Deleted stale `enhanced_renderer.py.backup`.
- **Verification**: mypy 0 errors; ruff clean; bandit Medium 0; 138 rendering/security tests pass.

### Phase 7: Documentation Sync
- **Version consistency**: All docs aligned to v0.3.42 (pyproject.toml, README, TEST_PLAN, TECH_DEBT, CHANGELOG, PYCC2_QUALITY_SPRINT).
- **TECH_DEBT.md**: Updated to v0.3.42; corrected file line counts (12 files >1000 lines, 53 files >500 lines documented as remaining debt).
- **PYCC2_QUALITY_SPRINT.md**: Phase 1-7 all marked complete; acceptance checklist updated with honest status.

## [0.3.42] - 2026-06-19

### P0-A: Terrain Rendering Overhaul
- Integrated 22 textured PNG terrain tiles (GRASS, WOODS, WATER, ROAD, HEDGE, BUILDING, etc.)
- AssetLoader dual-strategy lookup: numeric ID + TerrainType enum name
- Replaced flat procedural colors with high-quality texture tiles

### P0-B: Unit Sprite Visibility Fix
- SPRITE_SIZE increased from 32→48px (matching TILE_SIZE for CC2 clarity)
- base_radius increased from 24→32px (fallback shapes)
- Replaced placeholder unit PNGs with high-quality pixel art (~737KB each)
- SpriteRenderer and UnitRenderer synchronized to new 48px standard

### P1-A: Minimap Integration (was placeholder)
- Minimap now fully wired into GameLoop → HUDManager → CC2BottomPanel pipeline
- Real-time data sync: units, selected_unit, camera viewport every frame
- Fixed viewport_color undefined bug in minimap.py
- Minimap.show() called at initialization for immediate visibility

### P1-B: Combat Effects System (verified complete)
- TopDownParticleSystem: explosion rings, muzzle flash, smoke clouds, hit markers, death animations
- CombatPopupManager: floating damage numbers, critical hit indicators
- All effects integrated into EnhancedRenderer._render_effects() pipeline

### P2-A: Troop Roster UI Enhancement
- Roster item height increased 24→26px for better readability
- HP numeric value displayed next to health bar (e.g., "100/100")
- Morale status indicator: green/yellow/red dot per unit
- Health bar border darkened for contrast

### Test Infrastructure Fixes (11 failures → 0)
- test_sprite_renderer.py: Updated SPRITE_SIZE assertions (32→48, < to <=)
- test_display_config.py: Added pygame_init fixture for display-dependent tests
- test_performance_baseline.py: Fixed SurfacePool API (stats property), SaveGameStateData schema compliance

### Project Cleanup
- Deleted 19 process/report .md files from root directory
- Deleted 22 debug/one-off scripts from scripts/
- Deleted 11 redundant diagnostic screenshots
- Total test count: 4269 passed, 0 failed, 49 known pygame-init errors (pass individually)

### P0: Morale System Routing Bug Fix (PR #8)
- **[FIX]** `MoraleSystem.can_accept_orders()` returned True for routing units
- Root cause: `get_state(morale_value)` maps numeric value only — value=5 → BROKEN, never reaches ROUTING branch
- Fix: Check component-level `_is_routing` flag before numeric state mapping in `can_accept_orders()`
- Removed `@pytest.mark.xfail` from `test_routing_cannot_accept_orders` — now passes (+1 pass)
- Test result: **4298 passed, 0 failed** (up from 4297)

### P1: Directory Cleanup
- Moved `screenshot_real_game.py` from root directory to `scripts/`
- Root directory now contains only standard project config files

### P0: Version Synchronization Fix (PR #9)
- **[FIX]** `pyproject.toml` version updated from 0.3.41 → 0.3.42 (matches README/CHANGELOG)
- **[FIX]** README test badge updated from ~4269 → ~4298 (matches actual test count)
- All three version sources now consistent: pyproject.toml = README.md = CHANGELOG.md = 0.3.42

## [0.3.41] - 2026-06-14

### Architecture: SpriteRenderer Responsibility Separation
- Extracted `SpriteCacheManager` from SpriteRenderer — sprite generation, caching, and lookup now isolated (~200 lines)
- Extracted `EffectRenderer` from SpriteRenderer — particle effects, damage numbers, death animations, hit flash now isolated (~350 lines)
- SpriteRenderer refactored to coordinator pattern — composes SpriteCacheManager + EffectRenderer, backward-compatible property accessors preserve old API
- No functional changes: all 3411 unit tests pass, full regression green

### Code Quality: Naming Convention Fix
- Renamed `Lossystem` → `LOSSystem` (PascalCase compliance, 5 references updated)

### Code Quality: CombatDirector Performance Fix
- Replaced O(unit_ids × units) linear `next()` lookup with O(1) dict lookup in `handle_player_command`
- Removed 5 duplicate `import logging` + `logger = logging.getLogger(__name__)` inside method branches (moved to module-level)

### Code Quality: Logging Consistency
- Converted 61 f-string logger calls to %-formatting (Python logging best practice, lazy evaluation)

### Documentation: Version Sync
- Synchronized version to v0.3.41 across README.md, README_zh.md, README_ja.md, CHANGELOG.md, release.yml
- Updated TECH_DEBT.md from v0.3.13 to v0.3.41 (28 versions behind)
- Updated ROADMAP.md from v0.3.39 to v0.3.41

## [0.3.40] - 2026-06-13

### User Experience Overhaul — "Ready for Players"

#### P0: HUD Minimap Integration (was placeholder)
- CC2HUD now renders real Minimap with terrain, units, and camera viewport
- Added `set_game_map()` and `set_camera()` setters for data binding
- Replaced gray grid + "Preview" text with actual tactical overview

#### P0: Procedural Weapon Sound Generation (was only 2 WAV files)
- Added 5 new weapon sound types: tank_cannon, at_gun, mortar, smg, sniper
- ProceduralSoundGenerator creates realistic waveforms when WAV files don't exist
- Each weapon has distinct audio signature (frequency, duration, decay pattern)
- Updated sound_effects.py and enhanced_sound_bridge.py with full weapon mapping

#### P1: Victory Auto-Transition (was stuck on pause)
- VictoryManager now auto-transitions to PostBattleScreen after 2-second delay
- Players see "Victory!" then naturally flow to battle results
- Delay timer runs even when game is paused

#### P1: Suppression Visual Feedback (was invisible)
- Red gradient overlay on screen edges when ally units are PINNED/BROKEN
- Alpha ramps up during suppression, decays when pressure lifts
- Per-line alpha fade creates immersive "under fire" feeling

#### P2: GameLoop._update_logic() Refactored (was 187-line God Method)
- Split into 11 focused methods: weather, audio, movement, fatigue, combat,
  popups, camera, visual_effects, hud, ai, victory
- Dispatcher is now 15 lines — zero logic change, pure extraction

#### P2: Technical Debt Cleanup
- bare except → specific exceptions with logger.debug() in enhanced_renderer.py
- EventBus circuit breaker: auto-unsubscribe handlers after 3 consecutive failures
- README_ja.md completely rewritten (was describing v0.4-p4w2 era project)
- docs/ROADMAP.md, USER_GUIDE.md, DESIGN.md updated to v0.3.40

## [0.3.39] - 2026-06-13

### Critical Fix: AI Combat Fire Chain (P0)
- **Fixed**: AI units now properly execute attacks via CombatDirector (was broken - TacticExecutor published untyped dict events that CombatDirector never received)
- **Fixed**: game_loop now calls `ai_service.tick()` instead of legacy `update_all()` for full decision pipeline (perception, difficulty, engagement rules, commander AI, squad coordination)
- **Impact**: AI opponents can now actually fight back - game is playable against AI

### Performance Fix: Dirty Rectangle Optimization (P1)
- **Fixed**: Dirty rect tracking now actually works - particles and terrain use targeted dirty rects instead of full-screen marks
- **Fixed**: Render pipeline uses `display.update(rects)` for partial updates instead of always `display.flip()`
- **Impact**: Significant FPS improvement on large maps and during combat

### Stability Fixes (P1)
- **Fixed**: Save system HMAC key now stable across sessions (was random per launch, making saves unreadable on next start)
- **Fixed**: Empty deployment validation - players can no longer start battle with 0 units
- **Fixed**: Save version incompatibility shows error dialog instead of crashing

### Documentation & CI
- Updated all README versions to v0.3.39
- Added Dependabot configuration
- Added bandit security scanning to CI
- Upgraded Codecov and upload-artifact actions to v4
- Removed duplicate pytest.ini and mypy.ini (merged into pyproject.toml)
- Removed committed .baseline_results.json (378KB auto-generated)

## [0.3.38] - 2026-06-12

### Evaluation Fix & P0-P2 Optimization Round

#### P0: pixel_artist_3d.py God Class Split (2418→1001 lines)
| Extracted System | File | Lines | Content |
|---|---|---|---|
| TankPixelRenderer | `tank_pixel_renderer.py` | 688 | Tank sprites, rotation cache, Sherman/Panther/Tiger drawing |
| InfantryPixelRenderer | `infantry_pixel_renderer.py` | 876 | Infantry sprites, 8-direction params, 9 weapon types, InfantryAnimator |
- pixel_artist_3d.py retains Facade delegates + vehicle/environment sprites (halftrack, jeep, AT gun, tree, building)
- All public API signatures preserved — zero caller changes needed

#### P1: ResourceCacheManager Bug Fix + Test Coverage
- **Fixed**: `cache_dir` parameter now accepts both `str` and `Path` (was TypeError with str input)
- **25 new tests** in `test_resource_cache.py`: init, offline mode, download mock, cache hit, TTL, invalidate, SHA256, LRU eviction, stats, filename sanitize, network failure, corrupted index, persistence

#### P1: GitHub Actions Release Workflow
- **New file**: `.github/workflows/release.yml` — auto-publish to GitHub Releases on tag push (`v*`)
- Quality gate: tests must pass before build
- Auto-extract changelog from CHANGELOG.md
- Upload sdist + wheel artifacts
- **Updated**: `ci.yml` now supports `workflow_dispatch` manual trigger

#### P2: Weather Rendering Test Fix
- Fixed missing `WeatherRenderer` re-export in `weather_system.py` (ImportError)
- Updated 4 tests to use new `WeatherState` API instead of deprecated `WeatherCondition` enum
- Result: 77/77 weather tests passing (was 8 failed)

#### P2: Integration Test Verification
- Confirmed 132/132 integration tests passing (attack line, combat loop, rendering pipeline, victory flow)

## [0.3.37] - 2026-06-11

### Deep Optimization Phase (DevSquad Top-10 Round 3 — All Remaining Items)

#### #5 EnvironmentalAudioSystem Activated (~760 lines finally alive)
- **[INTEGRATE]** EnvironmentalAudioSystem instantiated in `game_loop_assembler._init_sound()` with full graceful degradation
- 11 ambient sound types (BIRDS, WIND, RAIN, THUNDER, DISTANT_ARTILLERY, etc.) — all procedurally generated, zero audio files needed
- Game loop context sync: time-of-day → bird/insect activity, weather → rain/thunder sounds, combat intensity → distant artillery/radio static
- Full try/except protection: missing pygame.mixer/numpy/scipy → silent fallback to no-audio mode

#### #6 Dirty Rectangle Rendering Optimization (Highest ROI perf item)
- New `_DirtyRectTracker` class: tracks dirty screen regions, merges overlapping rects, auto-degrades to full redraw when >16 dirty regions or fullscreen effects active
- 6 dirty-mark points in render pipeline: terrain(full), units(40×40 bbox), particles(conditional), HUD(bottom 120px), flash(full), post-processing(full)
- Final output: `pygame.display.update(rects)` instead of `flip()` when partial update possible
- Safety valve: `_dirty_tracker = None` disables optimization entirely (backward compatible)
- Resize handler rebuilds tracker for new screen dimensions

#### #7 EnhancedRenderer God Class Split (3 subsystems extracted)
| Extracted System | File | Lines | Methods |
|---|---|---|---|
| ShellCasingSystem | `shell_casing_system.py` | 125 | spawn/update/render |
| FlashEffectSystem | `flash_effect_system.py` | 101 | trigger/update + properties |
| WeatherSystem | `weather_system.py` | 160 | set_mode/update/render/screen_size |
- enhanced_renderer.py: 7 original methods → thin delegates, public API unchanged (game_loop zero changes)
- Internal state (_shell_casings/_flash_color/_weather_mode etc.) fully migrated to subsystems

#### #10 ResourceCacheManager + PixVoxel Auto-Download
- **New file**: `infrastructure/resource_cache.py` — HTTP download manager with:
  - JSON-indexed local disk cache (default ~/.cache/pycc2/assets/)
  - TTL expiration (7 days default), SHA256 integrity verification
  - LRU eviction at 500MB limit, atomic writes (.tmp→rename)
  - Offline mode support, progress callback API
- **PixVoxelLoader integration**: auto_download=True triggers automatic asset fetch when sprites missing; multi-tool extraction fallback (py7zr → 7z → 7za); manifest.json generation

## [0.3.36] - 2026-06-11

### Infrastructure Phase (DevSquad Top-10 Optimization Round 2)

#### ThemeManager Activation (176-line system finally alive)
- **[INTEGRATE]** `ThemeManager` singleton now initialized in `EnhancedRenderer.initialize()` with `"default"` theme active at startup
- **3 files connected**: enhanced_renderer.py (background fill), cc2_bottom_panel.py (5 color constants → dynamic properties), hud.py (VisualSpec 5-color override)
- Runtime theme switching: `ThemeManager.set_theme("dark")` / `"light"` / `"default"` — all connected UI components respond immediately
- All theme lookups have fallback defaults — zero crash risk if ThemeManager not initialized

#### SurfacePool Complete Unification (4→1, now 6/6)
- **enhanced_renderer.py**: Internal OrderedDict pool → `SurfacePool(max_size=50)`, `_get_pooled_surface()` simplified from ~20 lines to 3
- **terrain_rendering_system.py**: Internal dict pool → `SurfacePool(max_size=20)`, `_get_overlay_surface()` simplified
- **lighting_effects.py**: Internal dict pool → `SurfacePool(max_size=15)`, `_get_light_surface()` simplified
- **Status**: All 6 Surface consumers now use unified LRU pooling — eliminated duplicate memory management code across rendering pipeline

#### HUD Test Coverage (1138 lines → 55 new tests)
- **New file**: `tests/unit/test_cc2_hud.py` — 12 test classes, 55 test methods covering:
  - Init defaults (13 attrs), selection management, clear/hide behavior
  - Click edge cases (7 scenarios), HP status bar boundary values (5 boundaries)
  - AP/AT bar edge cases, scrolling behavior, minimap integration
  - Info mode cycling, render stability across states (5 variants)
- **Bug found during testing**: hide_button_rects vs unit_rects area overlap in handle_click — documented for future fix

#### Save System Test Fix
- Fixed 2 e2e `test_save_load_e2e` failures: test path mismatch (`saves/save_slot_X` → `save_slot_X` after SAVE_DIR_NAME="") + chmod OSError tolerance

## [0.3.35] - 2026-06-11

### Quick Wins (DevSquad Top-10 Optimization Round 1)

#### Dead Code Removal
- **[DELETE]** `animation_controller.py` (430 lines) — Removed completely. 90% functional overlap with existing `animation_system.py` + `sprite_renderer.py` + `pixel_artist_3d.py`. Zero production imports, only 2 test methods depended on it.
- **[CLEANUP]** Removed 2 orphan test methods from `test_phase_a.py`. Updated `TEST_STRATEGY_COMPREHENSIVE.md` to mark as removed.

#### Security Hardening (Save System: 8.0→8.5/10)
- **[P1]** Save file permissions locked to `0o600` (owner read/write only) after write — prevents same-machine users from reading or tampering with saves.
- **[P1]** `save_game()` exceptions now logged via `logger.warning()` instead of silently swallowed — improves debuggability for disk-full/permission errors.
- **[P2]** Fixed double `saves/saves/` directory nesting bug in default save path.
- **[P2]** HMAC key minimum length validation (16 bytes) — short keys now rejected with warning + auto-fallback to CSPRNG random key.

#### Documentation Sync
- README.md, README_zh.md, README_ja.md all synchronized to v0.3.34 reality:
  - Version: 0.3.34 → 0.3.35
  - Test count: 3929 → 3930
  - Added v0.31-v0.34 feature summaries (rendering overhaul, combat polish, ghost fixes, P3 features)
  - Architecture tree updated with new modules (SurfacePool, FadeTransition, WeatherOverlay, ShellEjection, TooltipManager)
  - Quality metrics: Overall health 8.0 → 8.2, Visual Polish dimension added at 8/10

## [0.3.34] - 2026-06-10

### Full Ghost Feature Sweep — 2 Critical Fixes

- **[FIX]** **PostProcessingEffects instance was never created** — `EnhancedRenderer.__init__` had no `_post_processing = PostProcessingEffects(...)` initialization. The entire post-processing pipeline (desaturation, vignette) was unreachable despite complete implementation code. Now instantiated in `initialize()` with `enable_color_grading()` called, making CC2 war atmosphere desaturation **finally visible** after 3 versions of being ghost code.
- **[FIX]** **Weather overlay had zero callers** — `set_weather()` API was fully implemented (clear/light_fog/dust/smoke with particle animation) but never invoked from any initialization or game setup path. Now defaults to `"light_fog"` at end of `initialize()`, giving every battle a subtle atmospheric haze.

### Remaining Ghost Inventory (Technical Debt)
After this fix, confirmed remaining ghosts are all **non-critical dead code** (not breaking visible features):
| Module | Lines | Status | Recommendation |
|--------|-------|--------|----------------|
| AnimationController | ~430 | Never instantiated | Decide: integrate or remove |
| EnvironmentalAudioSystem | ~700+ | Never instantiated | Keep for future audio phase |
| ThemeManager (singleton) | ~150 | `.instance()` never called | Low priority: nice-to-have |
| invalidate_terrain_cache() | 1 method | No external caller | Accept: key-mismatch covers most cases |

## [0.3.33] - 2026-06-10

### Ghost Feature Audit & Fixes (4 critical integration bugs resolved)

- **[FIX]** **P0-1**: Re-enabled post-processing pipeline in render() — `_apply_desaturation()` numpy color grading was completely unreachable (commented out as "causes flickering"). Fixed by applying post-processing to display surface after offscreen→screen blit, before flip.
- **[FIX]** **P0-4**: Tank rotation cache key strategy changed from `id(base)` to `(width, height, angle)`. Old key caused 100% cache miss since each frame creates new Surface objects. Also wired `precache_tank_rotations()` into `EnhancedRenderer.initialize()`.
- **[FIX]** **P2-04**: Movement smoothing now works for PNG sprite path — `position_overrides` propagated through `UnitRenderer` → `SpriteRenderer._draw_units()` → `SpriteRenderer._draw_sprite_unit()`. Previously only the fallback shape-rendering path used smooth positions.
- **[FIX]** **P2-05**: UI fade transitions now animate — `HUDManager.update(dt)` called from `GameLoop._update_logic()`. Previously FadeTransition alpha was stuck at 0.0 because no code path invoked `update()`.

### Audit Summary
| Item | Before Fix | After Fix |
|------|-----------|-----------|
| Desaturation color grading | Ghost (commented out) | **Active** — CC2 war atmosphere visible |
| Tank rotation cache | Partial ghost (0% hit rate) | **Active** — size-based key, precache at init |
| Movement smoothing (sprites) | Bypassed by PNG path | **Active** — all rendering paths covered |
| UI panel fade transitions | Ghost (update() never called) | **Active** — 0.18s smooth fade |

### P3 Deep Visual Improvements (3 new features)

- **[VISUAL]** **P3-01**: Weather overlay system — 4 modes (clear/light_fog/dust/smoke) with animated particle drift. Light fog uses semi-transparent gray surface; dust uses 30 drifting particles with sine-wave motion; smoke uses turbulent brown particles. Integrated into render pipeline + game_loop update cycle via `set_weather()` / `update_weather(dt)`.
- **[VISUAL]** **P3-02**: Shell casing ejection physics — combat hits spawn brass shell casings with realistic ejection trajectory (perpendicular to firing direction + random spread), gravity (400px/s²), ground bounce (0.3x velocity retention), 1.5-3s lifetime with fade-out. 3 brass color variants. Triggered from combat_director.process_effects().
- **[VISUAL]** **P3-03**: Button hover/click feedback + tooltip system — BottomPanel buttons now highlight on hover (bright blue border, fill brighten 10%), darken on press (sunken 3D effect). TooltipManager class provides 0.4s-delayed tooltips for all command buttons ("Move unit [Z]", "End turn [E]", etc.). Mouse events forwarded through EventDispatcher → HUDManager → BottomPanel.

## [0.3.32] - 2026-06-09

### Deep Visual Polish (5 P2 improvements)

- **[VISUAL]** **P2-01**: Combat particle enrichment — `dirt_splash` (radial debris), `blood_pool` (persistent ground stain on kill), and `hit_marker` (colored flash by damage type) now triggered from combat_director.process_effects(). 3 new delegate methods added to particle_effects_renderer + enhanced_renderer
- **[VISUAL]** **P2-02**: Unit death fade-out animation — units now fade out over 500ms (alpha 255→0) with CC2 dark-gray ghost rendering instead of instant vanishing. `_fading_units` dict with time.monotonic() for frame-rate-independent smooth decay
- **[VISUAL]** **P2-03**: Screen flash effect — explosion hits trigger warm white flash (255,240,200), kill shots trigger soft red flash (255,100,100). Uses BLEND_RGBA_ADD overlay with ease-out quad decay curve. Integrated into game_loop update cycle
- **[VISUAL]** **P2-04**: Unit movement smoothing — position lerp interpolation at 12 u/s prevents teleportation between tiles. `_unit_positions` dict tracks displayed positions, auto-cleans dead units. unit_renderer accepts optional position_overrides param
- **[VISUAL]** **P2-05**: UI panel transition animations — FadeTransition utility class (0.18-0.2s duration) applied to BottomPanel, Minimap, and HUD unit panel. Uses SRCALPHA surface compositing with zero-overhead fast path when fully visible

### New File
- `presentation/rendering/fade_transition.py` — Reusable alpha-based fade transition helper

### Visual Fidelity Impact
| Metric | Before | After |
|--------|--------|-------|
| Combat particles per hit | 2 types (flash+damage) | **5 types** (+dirt+blood+marker) |
| Unit death visual | Instant vanish | **500ms ghost fade** |
| Explosion feedback | Shake only | **Shake + flash + particles** |
| Unit movement | Teleport | **Smooth lerp** |
| UI panel show/hide | Instant pop | **0.2s fade transition** |

## [0.3.31] - 2026-06-08

### Rendering & Visual Quality Overhaul (8 improvements)

- **[VISUAL]** **P0-1**: Implemented `_apply_desaturation()` — CC2 signature grayscale war atmosphere now works (was `pass` stub). Uses numpy pixel-level desaturation with perceptual luminance weighting (R×0.299 + G×0.587 + B×0.114)
- **[VISUAL]** **P0-2**: Building wall thickness confirmed 2px (CC2-style flat top-down), docstring updated
- **[VISUAL]** **P1-1**: Infantry 8-direction differentiation enhanced — helmet size/position, body width/height, weapon angle, leg spread, backpack visibility (S-direction only), shadow offset all vary by facing direction
- **[VISUAL]** **P1-5**: Minimap terrain detail enhanced — roads (brown-gray + connecting lines), buildings (dark fill + outline border), water (deep blue), woods (dark green + tree dots)
- **[VISUAL]** **P1-6**: HUD minimap placeholder ("MINIMAP" text) replaced with real Minimap component rendering

### Performance Optimizations

- **[PERF]** **P0-3**: Unified SurfacePool class (`surface_pool.py`) — eliminated 3 duplicate LRU pool implementations in sprite_renderer/particle_system/dynamic_shadow_system. Single shared pool with stats tracking
- **[PERF]** **P0-4**: Tank sprite rotation pre-caching — 10 `pygame.transform.rotate()` calls replaced with cached lookups. 24 pre-cached angles (every 15°) generated at init time via `precache_tank_rotations()`
- **[PERF]** **P1-2**: Terrain static layer cache — dirty-flag-based large-surface cache for static terrain. When camera/terrain unchanged, single blit replaces N×M tile blits. Expected +15-20 FPS on terrain-heavy scenes

### New File
- `presentation/rendering/surface_pool.py` — Unified SurfacePool utility class

### Visual Fidelity Impact
| Metric | Before | After |
|--------|--------|-------|
| Desaturation effect | **Broken** (pass stub) | **Working** (numpy pixel ops) |
| Infantry direction variety | ~30% diff | **~80%+ diff** (8 params × 8 dirs) |
| Minimap terrain detail | Solid colors only | **5-type differentiation** |
| HUD minimap | Text placeholder | **Real component** |
| Surface pool duplication | 3 independent copies | **1 shared class** |
| Tank rotation cost | Per-frame rotate | **Cache hit O(1)** |

---

## [0.3.30] - 2026-06-07

### Product Maturity (7-dimension assessment → execution)
- **[CLEANUP]** README synchronized to v0.3.29→v0.3.30: version, stats, What's New, quality metrics
- **[CLEANUP]** Deleted 3 garbage files from root: `29,`, `63`, `Beta` (0-byte artifacts)
- **[CLEANUP]** main.py: 4× `traceback.print_exc()` → `logger.error(..., exc_info=True)`
- **[CLEANUP]** **144 bare print() statements → logger** across 17 files (99.3% cleanup rate)
  - Top4 files: combat_mechanics(20), cc2_units(18), terrain_detail(18), ceasefire(16)
  - Remaining 13 files: weapons(15), diversity(11), morale(9), persistence(8), etc.
- **[SPLIT]** DeploymentRenderer extracted from deployment_ui.py: **2071 → 1323 lines (-36%, -748)**
  - 20 rendering methods moved to dedicated class with composition pattern
  - 71 deployment-related tests pass with zero regressions
- **[ARCH]** save_system.py: 3× `except Exception` tightened to specific exception types
- **[ARCH]** save_system.py: `_victory_manager` private access → public `victory_manager` property
- **[TEST]** conftest.py: 13× bare print/traceback → logger calls
- God Class count: 4 → 3 (deployment_ui now 1323 lines)

### Stats
- **3933 tests passed, 0 failed** (16m36s full suite) — +4 from test quality fixes
- Bare print() in src/pycc2/: 144 → 1 (docstring example only, 99.3% cleanup rate)
- Code Quality score: 6.5 → 7.5/10 (print cleanup impact)
- Documentation score: 6.5 → **8.5/10** (README×3 sync + LICENSE created + process docs deleted)
- Overall maturity: 7.45 → **7.55/10** (DevSquad 7-dimension re-assessment)

### Additional Fixes (post-assessment)
- **[DOC]** README.md: version v0.3.29→v0.3.30, stats updated (God Class 4→3, print 144→1, quality 6.5→7.5)
- **[DOC]** README_zh.md: v0.3.28→v0.3.30, tests 3372→3929, Alpha→Beta Candidate (10 items fixed)
- **[DOC]** README_ja.md: v0.3.28→v0.3.30, tests 1377→3929, GitHub URL corrected (4 items fixed)
- **[DOC]** Created LICENSE file (MIT, was missing despite pyproject.toml declaration)
- **[TEST]** Fixed `assert True` anti-pattern in test_tutorial_flow.py::test_render_complete_shows_finish_message
- **[TEST]** Fixed duplicate method name in test_user_journey.py (test_victory_when_all_enemies_dead → _eliminated)
- **[CLEANUP]** Deleted P0_BUG_INVESTIGATION_REPORT.md and PROJECT_STATUS_REPORT.md (process artifacts)
- Integration tests: **132/132 passed** | E2E tests: **448/440+ passed** (DevSquad audit confirmed)

---

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
