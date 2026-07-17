# PyCC2 Development Roadmap

**v0.7.0 | July 17, 2026 | Based on DevSquad 7-Role Analysis**

> **Current Version**: v0.6.11 | **Tests**: ~6486 (all passing) | **CC2 Fidelity**: ~75% (Visual ~70% / Mechanics ~80%) ⚠️ v0.5.0 P0 PixVoxel 接入 + v0.5.1 P2 isometric 清理 + v0.5.2 P1 调色板修正 + v0.5.3 P1 纹理调优 + v0.6.0 P3-1 LOS 烟雾天气 + v0.6.1 P3-2 窗户射击弧 + v0.6.2 P3-3 散兵坑战壕 + v0.6.3 P3-4 AI 侦察行为 + v0.6.4 P3-5 AI 心理模型 + v0.6.5 P3-6 AI 补给线意识 + v0.6.6 P0-P1 修复 + v0.6.7 TD-COV-BUG 9项源码bug修复 + v0.6.8 R3 评估修复 (幽灵功能接入 + flaky 测试修复 + CI 安全增强) + v0.6.10 覆盖率提升+CI增强 (文档校准 + 脚本归档 + 323 新测试 + radon 复杂度门禁) + v0.6.11 ghost 模块清理 (TD-073/074/075/076a: 3 删除 + 1 type:ignore 修复)
> **Status**: Beta Candidate — AI対戦可用、コア玩法完整 | **M3: Visual Polish Complete (TD-065 + TD-066 both resolved v0.4.11) | v0.5.0 P0: PixVoxel 正交版精灵接入 | v0.5.1 P2: isometric experimental 代码清理**

---

## Executive Summary

PyCC2 has progressed from an unplayable state (~45% fidelity) to a Beta Candidate (~65% fidelity, v0.4.16 code-audited) through multiple milestone phases:

> **⚠️ v0.4.16 诚实修正**: 原 ~88% 还原度数据经代码审核严重高估。问题：(1) 11维度简单平均无权重；(2) isometric_renderer/isometric_transform 文件不存在（幽灵功能）；(3) PixVoxel 精灵加载器1143行完整但完全未接入游戏循环。基于代码证据修正为视觉~52%/机制~78%/综合~65%。详见 [GAP_ANALYSIS.md](GAP_ANALYSIS.md)。

- **M1 (May 23-24)**: Emergency fixes — resolved 5 P0 critical bugs
- **M2 (May 25-27)**: Core features — implemented CC2 victory conditions, command system, garrison, bridge destruction, campaign carryover, enhanced visuals
- **M3 (ongoing)**: Visual polish & deep optimization — SRP refactoring, cinematic effects, ghost feature fixes, visual polish, architecture cleanup

The project now has **~6536 passing tests**, **63 historical maps**, **277 unit templates**, and **69 authentic weapons**. All core gameplay loops work end-to-end. 38-phase E2E user journey validated in real SDL environment.

---

## Current Status Dashboard

> **注**: 此仪表盘反映 v0.4.0 时代状态。当前 v0.6.10 最新指标见 [PROJECT_STATUS.md](PROJECT_STATUS.md)（6536 collected / Domain 38.5%）。

| Metric | v0.1.1 (May 23) | v0.4.0 (June 13) | Change |
|--------|------------------|---------------------|--------|
| **Test Count** | 2767 (1 failed) | **~3985** (all pass) | ✅ +1218, 100% pass |
| **Test Pass Rate** | 99.96% | **100%** | ✅ Perfect |
| **CC2 Fidelity** | ~45% | **~65%** (v0.4.16审核) | ✅ +20% (原声称88%经代码审核高估) |
| **Map Count** | 30 | **63** | ✅ +110% |
| **Weapon Types** | 69 | **69** | ✅ Unchanged |
| **Unit Templates** | 277 (data only) | **277** (rendering works) | ✅ Rendering fixed |
| **P0 Bugs** | 5 | **0** | ✅ All cleared |
| **Combat UI** | Crashing | **Fully functional** | ✅ Fixed |
| **AI Behavior** | BT broken | **8 AI types working** | ✅ Fixed |
| **Command System** | 3/7 usable | **7/7 + hotkeys + queue** | ✅ Complete |
| **Unit Rendering** | Geometric shapes | **Sprites + turret rotation** | ✅ Fixed |
| **Victory Conditions** | None | **CC2-authentic triple** | ✅ New feature |
| **Building Garrison** | None | **Defense + window arcs** | ✅ New feature |
| **Bridge Destruction** | None | **Engineer demolition** | ✅ New feature |
| **Campaign Carryover** | None | **Units persist** | ✅ New feature |
| **E2E Tests** | None | **38-phase real SDL** | ✅ New feature |
| **Visual Polish** | None | **Death fade, flash, weather, shells** | ✅ v0.3.31-v0.3.34 |
| **Architecture** | God classes | **SRP splits, -39% violations** | ✅ v0.3.23-v0.3.29 |
| **SpriteRenderer** | 1529-line God class | **Coordinator + 2 sub-classes** | ✅ v0.4.0 |

---

## Seven-Dimension Quality Assessment

> Updated 2026-07-14 based on codebase static analysis + runtime verification + 7-role review

| Dimension | Score | Trend | Notes |
|-----------|-------|-------|-------|
| **Architecture** | ✅ GOOD | ↑ from NEEDS_IMPROVEMENT | Clean DDD layers; EnhancedRenderer split complete (3 subsystems extracted); layer violations -39%; P2-2 God Class task canceled (4 candidates all judged NOT God Class via SRP analysis) |
| **Code Quality** | ✅ GOOD | ↑ from NEEDS_IMPROVEMENT | Bare print() ~1 remaining (99.3% cleaned); AnimationController dead code removed; logging migration complete |
| **Test Coverage** | ✅ EXCELLENT | ↑ from GOOD | ~6536 tests all green (not-slow baseline), includes integration+E2E+smoke; 55 HUD tests in v0.3.36; 38-phase real SDL E2E; 323 new tests in v0.6.10 |
| **Security** | ✅ EXCELLENT | — | HMAC integrity protection (permissions 0o600, key validation), input validation complete, no injection vectors |
| **Performance** | ✅ GOOD | ↑ from ADEQUATE | Surface pool LRU unified (6/6 consumers), dirty rectangle optimization, terrain cache, tank rotation cache, viewport culling |
| **Error Handling** | ✅ GOOD | ↑ from NEEDS_IMPROVEMENT | Bare except replaced with specific exceptions; key paths have error recovery; some modules need enhancement |
| **Documentation** | ✅ GOOD | ↑ from NEEDS_IMPROVEMENT | Version numbers unified to v0.6.10; doc-code sync via check_doc_consistency.sh integrated to CI; v0.6.10 comprehensive doc audit completed |

**Scoring Scale**: EXCELLENT > GOOD > ADEQUATE > NEEDS_IMPROVEMENT > POOR

---

## Milestone History

### ✅ M1: Emergency Fixes (May 23-24, 2026)

**Goal**: Fix critical P0 bugs to make game playable

| Task | Priority | Est. Hours | Status |
|------|----------|------------|--------|
| ~~P0-1: Add `display_name` attribute to Unit~~ | P0 | 0.5h | ✅ Fixed |
| ~~P0-2/3: Component attribute aliases (health.current/max, morale.current)~~ | P0 | 1h | ✅ Fixed |
| ~~P0-4: Implement AttackNearestAI/MoveToObjectiveAI~~ | P0 | 2h | ✅ Fixed |
| ~~P0-5: Add smoke tests for critical paths~~ | P0 | 2h | ✅ Fixed |
| ~~P1-1: Extend set_mode() signature (accept fast/sneak)~~ | P1 | 1h | ✅ Fixed |

**M1 Acceptance Criteria**: ✅ ALL PASSED
- [x] Game launches without crash
- [x] CC2BottomPanel correctly shows unit name, health, morale, ammo
- [x] AI units move and attack autonomously on battlefield
- [x] Move/Fast/Sneak/Attack/Cancel commands trigger correct interaction modes
- [x] All smoke tests pass

---

### ✅ M2: Core Features (May 25-27, 2026)

**Goal**: Implement CC2-authentic core features to reach ~95% fidelity

| Task | Priority | Est. Hours | Status |
|------|----------|------------|--------|
| ~~P1-2: Smoke/Defend interaction modes~~ | P1 | 4h | ✅ Fixed |
| ~~P1-3: Fix sprite rendering pipeline (PNG→SpriteRenderer)~~ | P1 | 4h | ✅ Fixed |
| ~~P1-6: Add integration tests~~ | P1 | 4h | ✅ Fixed |
| ~~P2-8: Save data validation~~ | P2 | 2h | ✅ Fixed |
| CC2-authentic victory conditions (instant VL/20min timer/scoring) | P1 | 4h | ✅ Complete |
| 7 command hotkeys (Z/X/S/C/V/D/H) | P1 | 2h | ✅ Complete |
| Command queue (Shift+right-click) | P1 | 2h | ✅ Complete |
| Engineer bridge destruction | P1 | 3h | ✅ Complete |
| Building garrison system | P1 | 4h | ✅ Complete |
| Window firing arc restriction | P1 | 2h | ✅ Complete |
| Deployment LOS preview | P2 | 2h | ✅ Complete |
| Faction difficulty asymmetry | P2 | 3h | ✅ Complete |
| Campaign day briefing | P2 | 3h | ✅ Complete |
| Battle-to-battle unit carryover | P1 | 4h | ✅ Complete |
| Campaign end screen | P2 | 2h | ✅ Complete |
| Enhanced terrain textures | P2 | 3h | ✅ Complete |
| Improved unit sprites (turret rotation, wounded visuals) | P2 | 3h | ✅ Complete |
| Death animation (directional falling) | P2 | 2h | ✅ Complete |
| Environment lighting (shadows) | P2 | 3h | ✅ Complete |

**M2 Acceptance Criteria**: ✅ ALL PASSED
- [x] All 7 commands usable with hotkeys
- [x] Units rendered using PNG sprites with turret rotation
- [x] Integration tests cover core interaction paths
- [x] Save loading has data validation
- [x] CC2-authentic victory conditions complete
- [x] Building garrison + window arcs working
- [x] Engineers can destroy bridges
- [x] Campaign units persist across battles

---

### ✅ M3: Visual Polish & Deep Optimization (May 28 - June 13, 2026)

**Goal**: Polish visual fidelity, fix ghost features, deep architecture optimization

#### v0.3.31-v0.3.34 — Visual Quality Overhaul & Ghost Fixes (June 8-10)

| Task | Priority | Status | Notes |
|------|----------|--------|-------|
| Desaturation effect (numpy pixel-level CC2 grayscale) | P1 | ✅ Complete | Was `pass` stub, now active |
| Infantry 8-direction differentiation enhanced | P1 | ✅ Complete | ~80%+ visual variety |
| Minimap terrain detail (roads, buildings, water, woods) | P1 | ✅ Complete | Replaced text placeholder |
| HUD minimap (real Minimap component) | P1 | ✅ Complete | v0.3.31 |
| Weather overlay system (4 modes) | P1 | ✅ Complete | clear/light_fog/dust/smoke |
| Shell casing ejection physics | P2 | ✅ Complete | v0.3.33 |
| Button hover/click feedback + tooltips | P2 | ✅ Complete | v0.3.33 |
| PostProcessingEffects instance creation fix | P0 | ✅ Complete | v0.3.34 — entire pipeline was never instantiated |
| Weather overlay default to light_fog | P1 | ✅ Complete | v0.3.34 |
| Death fade-out (500ms alpha decay) | P1 | ✅ Complete | v0.3.32 |
| Screen flash effect (explosion/kill) | P2 | ✅ Complete | v0.3.32 |
| Movement smoothing (position lerp 12 u/s) | P1 | ✅ Complete | v0.3.32 |
| UI panel transition animations | P2 | ✅ Complete | v0.3.32 |
| Combat particle enrichment (5 types per hit) | P2 | ✅ Complete | v0.3.32 |

#### v0.3.35-v0.4.0 — Infrastructure & Cleanup (June 11-13)

| Task | Priority | Status | Notes |
|------|----------|--------|-------|
| AnimationController dead code deletion (430 lines) | P2 | ✅ Complete | v0.3.35 |
| Save system security hardening (0o600, HMAC key validation) | P1 | ✅ Complete | v0.3.35 |
| ThemeManager runtime activation (3 themes) | P2 | ✅ Complete | v0.3.36 |
| SurfacePool complete unification (6/6 consumers) | P1 | ✅ Complete | v0.3.36 |
| HUD test coverage (55 new tests, 12 classes) | P2 | ✅ Complete | v0.3.36 |
| EnvironmentalAudioSystem activated (11 sounds) | P1 | ✅ Complete | v0.3.37 |
| Dirty Rectangle rendering optimization | P1 | ✅ Complete | v0.3.37 |
| EnhancedRenderer God Class split (ShellCasingSystem + FlashEffectSystem + WeatherSystem) | P1 | ✅ Complete | v0.3.37 |
| ResourceCacheManager (HTTP + SHA256 + LRU + offline) | P2 | ✅ Complete | v0.3.37 |

**M3 Acceptance Criteria**: ✅ MOSTLY PASSED
- [x] CC2 three-panel HUD with VP display
- [x] Visual polish: death fade, screen flash, movement smoothing, UI transitions
- [x] Weather overlay system active
- [x] Ghost features fixed (PostProcessing, desaturation, movement smoothing, UI transitions)
- [x] Architecture: EnhancedRenderer split, layer violations -39%
- [ ] Command queue shows visual waypoints with numbering
- [ ] Vehicle damage has visual feedback (smoke, fire, disabled appearance)
- [ ] Save/Load fully integrated into UI

---

## Current Phase: M3 — Polish & Visual Fidelity 🟡 (Mostly Complete, 2 items deferred to v0.5)

**Target**: v0.4-alpha | **Timeline**: 5-7 days | **Focus**: User-facing polish

> **v0.4.11 同步更新**: M3 任务列表已根据 v0.4.0 D8 Phase 2 实际完成情况同步。R1 (命令队列视觉路径点) 和 R4 (存档系统完整集成) 已在 v0.4.0 D8 Phase 2 完成。Vehicle damage visual feedback 已在 v0.4.11 完成 (TD-065 RESOLVED, 最小化方案：unit.py + unit_damage_vfx_mixin.py)。Smoke particle effects 仍延期至 v0.5 (TD-066)。Audio mixing balance pass 部分完成 (R5 ✅ RESOLVED in v0.3.0, 但部分音效音量仍不一致)。

### M3 Task List

| Task | Priority | Est. Hours | Status | Owner |
|------|----------|------------|--------|-------|
| Command queue UI (visual waypoint display) | P1 | 4h | ✅ Complete (v0.4.0 D8 Phase 2, R1) | UI Designer + Coder |
| Vehicle damage visual feedback (smoke, fire, immobilized) | P1 | 4h | ✅ Complete (v0.4.11 TD-065 RESOLVED, 最小化方案) | UI Designer + Coder |
| Smoke particle effects improvement | P1 | 4h | ✅ Complete (v0.4.11 TD-066 RESOLVED, 分层集成 CC2SmokeEffect) | UI Designer + Coder |
| Save/Load full UI integration | P2 | 4h | ✅ Complete (v0.4.0 D8 Phase 2, R4) | PM + Coder |
| Audio mixing balance pass | P2 | 2h | ⚠️ Partial (R5 RESOLVED v0.3.0, 部分音量不一致) | UI Designer |

**M3 Acceptance Criteria**:
- [x] Command queue shows visual waypoints with numbering ✅ (v0.4.0 D8 Phase 2, R1)
- [x] Vehicle damage has visual feedback (smoke, fire, disabled appearance) ✅ (v0.4.11 TD-065 RESOLVED, 最小化方案：部件差异化 VFX tracks/turret/engine)
- [x] Smoke has improved particle effects ✅ (v0.4.11 TD-066 RESOLVED, CC2SmokeEffect 不规则多边形烟团 + 通用圆形粒子分层渲染)
- [x] Save/Load fully integrated into UI ✅ (v0.4.0 D8 Phase 2, R4)
- [ ] Audio volume levels balanced — ⚠️ Partial (R5 RESOLVED v0.3.0, 部分音量不一致)

---

## Future Phases

### M4: Architecture Improvements (v0.5-alpha) — ✅ Complete (v0.4.12, 2026-07-09)

**Target**: v0.5-alpha | **Timeline**: 5-7 days | **Focus**: Code maintainability

> **v0.4.12 同步更新**: M4 任务列表已根据 v0.3.x~v0.4.12 实际完成情况同步。9 项任务全部完成 (TD-027/045/046/047/048/058 + GameLoop split D11/D12 + Domain slimdown 评估 + Unify unit definition 评估)。详见 [ASSESSMENT_M4_V0411.md](archive/ASSESSMENT_M4_V0411.md)。

| Task | Priority | Est. Hours | Status | Owner |
|------|----------|------------|--------|-------|
| Domain layer slimdown (75.4% → <50%) | P1 | 8h | ✅ 评估完成-目标已达成 (v0.4.12, 实测 38.5% < 50%, 75.4% 为 v0.3.x 过期数据) | Architect |
| Split large files (8 files >1000 lines) | P1 | 8h | ✅ Complete (TD-058, D12 Phase 2, 2026-06-29) | Coder |
| GameLoop split (1226 lines → <400 lines) | P1 | 6h | ✅ Complete (D11/D12) | Coder |
| Merge infra/ into infrastructure/ | P2 | 1h | ✅ Complete (TD-027 RESOLVED v0.4.7, 2026-07-05) | DevOps |
| Unify unit definition system (4 sets → 1 set) | P2 | 4h | ✅ 评估完成-前提不成立 (v0.4.12, 实为 1 套 DDD 协作系统 Entity+Template+Factory+Facade, 非重复定义) | Architect |
| Clean up duplicate morale modules | P2 | 2h | ✅ Complete (TD-046, 2026-05-28) | Coder |
| Fix 68 bare except blocks | P2 | 3h | ✅ Complete (TD-047, 2026-05-28) | Coder |
| Remove domain quick_implementations.py | P2 | 2h | ✅ Complete (TD-048, 2026-05-28) | Coder |
| Fix domain→presentation layer violations | P2 | 2h | ✅ Complete (TD-045, 2026-05-28) | Architect |

**M4 Acceptance Criteria**:
- [x] No Python file exceeds 800 lines ✅ (TD-026 评估 v0.4.7: 44 文件 >500L 但均非 God Class; TD-061 enhanced_renderer 评估 v0.4.9)
- [x] Domain layer code <50% of total ✅ (实测 38.5%, 36966/96137, 2026-07-09 v0.4.12)
- [x] GameLoop <400 lines ✅ (D11/D12)
- [x] All existing tests still pass ✅ (5400 tests, 100% pass rate)
- [x] No circular dependencies ✅ (D11/D12 已清理)
- [x] No bare except blocks ✅ (TD-047, 2026-05-28)
- [x] No duplicate modules ✅ (TD-046 morale + TD-048 quick_implementations 已清理)

---

### M5: Quality & Sustainability (v0.6-alpha)

**Target**: v0.6-alpha | **Timeline**: 3-5 days | **Focus**: Long-term viability

| Task | Priority | Est. Hours | Status | Owner |
|------|----------|------------|--------|-------|
| Clean up scripts/ directory (14 scripts, 10 zero-reference) | P2 | 2h | ✅ Complete (v0.6.10 Wave 3, scripts 归档完成) | DevOps |
| Consolidate documentation (4 visual docs merge + root md migration) | P2 | 3h | ✅ Complete (v0.6.10 Wave 3, 文档校准完成) | PM |
| Add E2E test stage to CI | P2 | 4h | ✅ Complete (CI has 7 stages) | Tester + DevOps |
| Add user operation E2E tests | P2 | 6h | ✅ Complete (491 E2E tests) | Tester |
| Performance optimization for large maps | P2 | 8h | ⬜ Planned (isometric removed v0.5.1, re-scope needed) | Architect + Coder |

**M5 Acceptance Criteria**:
- [x] CI pipeline has 7 stages: lint → unit → slow → benchmark → integration → e2e → docker ✅
- [x] scripts/ contains only useful utility scripts ✅ (v0.6.10 Wave 3)
- [x] No overlapping documentation in docs/ ✅ (v0.6.10 Wave 3)
- [x] User operation E2E tests cover: select unit → command → observe result ✅ (491 E2E tests)
- [ ] 100×100 isometric map runs at ≥25fps — ❌ Obsolete (isometric removed v0.5.1, re-scope to orthogonal map performance)

---

### M6: Content Enhancement (v0.7-beta)

**Target**: v0.7-beta | **Timeline**: 7-10 days | **Focus**: CC2 authenticity

| Task | Priority | Est. Hours | Status | Owner |
|------|----------|------------|--------|-------|
| Add more decorations (tank wrecks, plane wreckage, craters, barricades) | P2 | 8h | ⬜ | UI Designer + Artist |
| CC2-style sound effects (gunshots, explosions, ambient) | P2 | 8h | ⬜ | Audio Designer |
| AI behavior enhancement (smarter tactical decisions) | P2 | 12h | ⬜ | Architect + AI Developer |
| Weather effects polish | P3 | 6h | ⬜ | UI Designer |
| Night combat improvements | P3 | 4h | ⬜ | Coder |

---

## Version Timeline

| Version | Codename | Phase | CC2 Fidelity | Test Target | Key Deliverables | Actual Status |
|---------|----------|-------|-------------|-------------|------------------|---------------|
| v0.1.1 | Fix First | M1 | ~55% | 2767 | Fixed 5 P0 bugs | ✅ Completed |
| v0.2.0 | Playable | M2-first-half | ~90% | 3325 | 7 commands + PNG sprites + AI fix | ✅ Completed |
| v0.3.0 | Full Features | M2 | ~95% | 3372 | Victory + Garrison + Bridge + Carryover + Visuals | ✅ Completed |
| v0.3.1-v0.3.2 | Visual+Arch | M3-start | ~90% | 3400 | HUD + VP display + renderer split + DDD | ✅ Completed |
| v0.3.11-v0.3.16 | Audit+Split | M3-mid | ~88% | 3500 | God class splits, test quality revolution, 121 weak assertions fixed | ✅ Completed |
| v0.3.17-v0.3.23 | Cinematic+Opt | M3-mid | ~88% | 3700 | Camera effects, achievements, shadows, trails, optimization | ✅ Completed |
| v0.3.25-v0.3.30 | Arch Cleanup | M3-late | ~88% | 3850 | Circular deps, GameLoopAssembler, E2E upgrade, doc sync | ✅ Completed |
| v0.3.31-v0.3.34 | Visual Polish | M3-polish | ~88% | 3920 | Desaturation, weather, death fade, screen flash, ghost fixes | ✅ Completed |
| **v0.4.0** | **Beta Candidate** | **M3** | **~88%** | **~3985** | **ThemeManager, env audio, dirty rect, SRP splits, security** | ✅ Completed |
| v0.4.7 | Doc Sync | M3 | ~88% (偏高) | ~4598 | TD-027 关闭 + TD-026 评估 + 文档状态同步 (PRD/ROADMAP/GAP/TECH_DEBT) | ✅ Completed |
| **v0.4.16** | **Code Audit** | **M3** | **~65%** (代码审核) | **~5400** | **严格代码审核修正还原度数据 + ruff/scipy修复 + CI全绿** | ✅ Completed |
| **v0.5.0** | **PixVoxel P0** | **M3** | **~72%** (PixVoxel 接入) | **~5725** | **P0: PixVoxel Blank 正交版精灵接入游戏循环 (3968精灵, 14/18单位覆盖) + TD-042 RESOLVED + D13-N3 RESOLVED** | ✅ Completed |
| **v0.6.6** | **P0-P1 Fix** | **M3** | **~75%** (P3 全完成) | **~5725** | **P3-1~P3-6 全部完成 + P0-P1 修复 (flaky 测试隔离 + CI deselect 移除 + 覆盖率评估)** | ✅ Completed |
| **v0.6.7** | **Bug Fix** | **M3** | **~75%** | **~6178** | **TD-COV-BUG 9项源码bug修复 (阵营硬编码/WeaponState枚举/TurnEndedEvent/deploy_smoke/死代码/Vec2下标)** | ✅ Completed |
| **v0.6.8** | **R3 Assessment Fix** | **M3** | **~75%** | **~6178** | **R3 评估修复: 幽灵功能接入(ReconAI+SupplyAwarenessAI) + flaky 测试修复(SwissCheeseEngine rng注入) + CI安全增强(pip-audit --strict + cov-fail-under 70 + codecov fail_ci_if_error) + Dockerfile非root用户 + 评估报告归档** | ✅ Completed |
| **v0.6.10** | **Coverage+CI** | **M3** | **~75%** | **~6536** | **323新测试(覆盖率提升) + radon复杂度门禁集成CI + 文档校准 + 脚本归档。源码模块388, 测试文件210** | ✅ **Current** |
| v0.4-alpha | Polish Complete | M3-final | ~90% | 4000 | Command queue UI + Save/Load UI ✅ / Damage visuals + Smoke deferred to v0.5 | 🟡 Partial (3/5 done, 2 deferred) |
| v0.5-alpha | Maintainable | M4 | ~92% | 7000 | Architecture refactor + Tech debt cleanup | 🟡 Partial (7/9 M4 tasks done) |
| v0.6-alpha | Sustainable | M5 | ~95% | 7500 | CI enhancement + Docs + E2E expansion | ⬜ Planned |
| v1.0-beta | A Bridge Too Far | Final | ≥95% | ≥8000 | Full release candidate | ⬜ Target |

---

## Risk Register

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| M3 polish introduces regressions | Medium | High | Run full test suite after each task completion |
| M4 refactoring breaks existing functionality | High | High | Refactor incrementally; run tests after each module change |
| Large file splits cause import errors | Medium | Medium | Use IDE refactoring tools; verify imports immediately |
| Performance optimization introduces new bugs | Medium | Medium | Benchmark before/after; keep performance regression tests |
| Documentation drift from code changes | High | Low | Enforce doc update in milestone acceptance criteria |
| Sprite asset loading timing issues | Low | Medium | Ensure pygame display init before SpriteRenderer calls |
| AI behavior tree interface compatibility | Medium | Medium | Confirm BehaviorTree Node interface before implementing new AIs |
| Test coverage gaps persist | Medium | High | Add coverage gates to CI; target ≥80% branch coverage |

---

## Key Principles

1. **Honest Assessment**: Never embellish progress; documentation must match runtime verification
2. **Fix Bugs First**: No new features until M3 polish is complete
3. **Runtime Verification**: All features must be verified in a runnable game, not just by passing tests
4. **Documentation First**: Update docs before starting each milestone; review upon completion
5. **Zero Technical Debt Tolerance**: Record debt immediately; clean up at each milestone boundary
6. **Reference Original**: All decisions benchmarked against CC2 original game data
7. **E2E Validation**: Perform simulated real-user testing after each milestone completion

---

## Dependency Graph

```
M1 (Emergency Fixes) ──┬──→ M2 (Core Features) ──┬──→ M3 (Polish) ──→ v0.4-alpha
                        │                       │
                        │                       ├──→ M4 (Architecture) ──→ v0.5-alpha
                        │                       │
                        │                       ├──→ M5 (Quality) ──────→ v0.6-alpha
                        │                       │
                        │                       └──→ M6 (Content) ──────→ v0.7-beta
                        │                                              │
                        └──────────────────────────────────────────────┘──→ v1.0-beta
```

**Critical Path**: M1 → M2 → M3 → v0.4 (minimum viable polished version)

**Parallel Tracks** (can be done concurrently after M3):
- M4 (Architecture) + M5 (Quality) can overlap
- M6 (Content) can start once M3 is complete

---

## How to Contribute to Roadmap

We welcome community contributions to any milestone:

1. **Check the issue tracker** for tasks tagged with the current milestone
2. **Comment on roadmap items** you'd like to work on
3. **Submit PRs** referencing the specific roadmap task
4. **Suggest new items** via GitHub Issues with the "roadmap" label

**Priority Labels**:
- 🔴 P0: Critical (blocks all users)
- 🟠 P1: Major (degrades experience significantly)
- 🟡 P2: Minor (nice to have)
- 🔵 P3: Enhancement (future consideration)

---

**Document Version**: 0.6.10
**Created**: 2026-05-19
**Updated**: 2026-07-13
**Status**: Beta Candidate — P0-P3 全部完成; v0.6.6 P0-P1 修复; v0.6.7 TD-COV-BUG 9项源码bug修复; v0.6.8 R3 评估修复 (幽灵功能接入 + flaky 测试修复 + CI 安全增强); v0.6.10 覆盖率提升+CI增强 (文档校准+脚本归档+323新测试+radon复杂度门禁)
**Next Review**: 覆盖率提升至 70% + 大文件评估 + docs 归档
**Related Documents**: [GAP_ANALYSIS.md](docs/GAP_ANALYSIS.md) | [TECH_DEBT.md](docs/TECH_DEBT.md) | [VISUAL_FIDELITY_IMPROVEMENT_PLAN.md](VISUAL_FIDELITY_IMPROVEMENT_PLAN.md)
