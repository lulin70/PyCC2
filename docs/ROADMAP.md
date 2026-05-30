# PyCC2 Development Roadmap

**v0.3.0 | May 30, 2026 | Based on DevSquad 7-Role Analysis**

> **Current Version**: v0.3.0 | **Tests**: 3372 (all passing) | **CC2 Fidelity**: ~95%
> **Status**: M1+M2 Complete — Game fully playable with all core systems working | **M3: Visual Polish in Progress**

---

## Executive Summary

PyCC2 has progressed from an unplayable state (~45% fidelity) to a fully functional Alpha (~95% fidelity) through two major milestone phases:

- **M1 (May 23-24)**: Emergency fixes — resolved 5 P0 critical bugs
- **M2 (May 25-27)**: Core features — implemented CC2 victory conditions, command system, garrison, bridge destruction, campaign carryover, enhanced visuals

The project now has **3372 passing tests**, **63 historical maps**, **277 unit templates**, and **69 authentic weapons**. All core gameplay loops work end-to-end.

---

## Current Status Dashboard

| Metric | v0.1.1 (May 23) | v0.3.0 (May 27) | Change |
|--------|------------------|------------------|--------|
| **Test Count** | 2767 (1 failed) | **3372** (all pass) | ✅ +605, 100% pass |
| **Test Pass Rate** | 99.96% | **100%** | ✅ Perfect |
| **CC2 Fidelity** | ~45% | **~95%** | ✅ +50% |
| **Map Count** | 30 | **63** | ✅ +110% |
| **Weapon Types** | 69 | **69** | ✅ Unchanged |
| **Unit Templates** | 277 (data only) | **277** (rendering works) | ✅ Rendering fixed |
| **P0 Bugs** | 5 | **0** | ✅ All cleared |
| **Combat UI** | Crashing | **Fully functional** | ✅ Fixed |
| **AI Behavior** | BT broken | **6 AI types working** | ✅ Fixed |
| **Command System** | 3/7 usable | **7/7 + hotkeys + queue** | ✅ Complete |
| **Unit Rendering** | Geometric shapes | **Sprites + turret rotation** | ✅ Fixed |
| **Victory Conditions** | None | **CC2-authentic triple** | ✅ New feature |
| **Building Garrison** | None | **Defense + window arcs** | ✅ New feature |
| **Bridge Destruction** | None | **Engineer demolition** | ✅ New feature |
| **Campaign Carryover** | None | **Units persist** | ✅ New feature |

---

## Seven-Dimension Quality Assessment

> Updated 2026-05-30 based on codebase static analysis + runtime verification + 7-role review

| Dimension | Score | Trend | Notes |
|-----------|-------|-------|-------|
| **Architecture** | ✅ GOOD | ↑ from NEEDS_IMPROVEMENT | Clean DDD layers; TD-045~049 fixed; remaining TD-050/051 are domain→services/infra violations |
| **Code Quality** | ✅ GOOD | ↑ from NEEDS_IMPROVEMENT | Bare except cleaned (TD-047), duplicate modules merged (TD-046); enhanced_renderer.py still oversized (TD-052) |
| **Test Coverage** | ✅ GOOD | ↑ from ADEQUATE | 3372 tests all green, includes integration+E2E; contract tests and performance regression tests still missing |
| **Security** | ✅ EXCELLENT | — | HMAC integrity protection, input validation complete, no known security vulnerabilities |
| **Performance** | 🟡 ADEQUATE | — | 50×42 map @30fps achieved; 100×100 isometric mode needs optimization (TD-043) |
| **Error Handling** | ✅ GOOD | ↑ from NEEDS_IMPROVEMENT | Bare except replaced with specific exceptions; key paths have error recovery; some modules need enhancement |
| **Documentation** | ✅ GOOD | ↑ from NEEDS_IMPROVEMENT | Version numbers unified; doc-code sync mechanism pending (TD-038) |

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

## Current Phase: M3 — Polish & Visual Fidelity 🟡

**Target**: v0.4-alpha | **Timeline**: 5-7 days | **Focus**: User-facing polish

### M3 Task List

| Task | Priority | Est. Hours | Status | Owner |
|------|----------|------------|--------|-------|
| Command queue UI (visual waypoint display) | P1 | 4h | ⬜ | UI Designer + Coder |
| Vehicle damage visual feedback (smoke, fire, immobilized) | P1 | 4h | ⬜ | UI Designer + Coder |
| Smoke particle effects improvement | P1 | 4h | ⬜ | UI Designer + Coder |
| Save/Load full UI integration | P2 | 4h | ⬜ | PM + Coder |
| Audio mixing balance pass | P2 | 2h | ⬜ | UI Designer |

**M3 Acceptance Criteria**:
- [ ] Command queue shows visual waypoints with numbering
- [ ] Vehicle damage has visual feedback (smoke, fire, disabled appearance)
- [ ] Smoke has improved particle effects
- [ ] Save/Load fully integrated into UI
- [ ] Audio volume levels balanced

---

## Future Phases

### M4: Architecture Improvements (v0.5-alpha)

**Target**: v0.5-alpha | **Timeline**: 5-7 days | **Focus**: Code maintainability

| Task | Priority | Est. Hours | Status | Owner |
|------|----------|------------|--------|-------|
| Domain layer slimdown (75.4% → <50%) | P1 | 8h | ⬜ | Architect + Coder |
| Split large files (8 files >1000 lines) | P1 | 8h | ⬜ | Coder |
| GameLoop split (1226 lines → <400 lines) | P1 | 6h | ⬜ | Coder |
| Merge infra/ into infrastructure/ | P2 | 1h | ⬜ | DevOps |
| Unify unit definition system (4 sets → 1 set) | P2 | 4h | ⬜ | Architect + Coder |
| Clean up duplicate morale modules | P2 | 2h | ⬜ | Coder |
| Fix 68 bare except blocks | P2 | 3h | ⬜ | Coder |
| Remove domain quick_implementations.py | P2 | 2h | ⬜ | Coder |
| Fix domain→presentation layer violations | P2 | 2h | ⬜ | Architect |

**M4 Acceptance Criteria**:
- [ ] No Python file exceeds 800 lines
- [ ] Domain layer code <50% of total
- [ ] GameLoop <400 lines
- [ ] All existing tests still pass
- [ ] No circular dependencies
- [ ] No bare except blocks
- [ ] No duplicate modules

---

### M5: Quality & Sustainability (v0.6-alpha)

**Target**: v0.6-alpha | **Timeline**: 3-5 days | **Focus**: Long-term viability

| Task | Priority | Est. Hours | Status | Owner |
|------|----------|------------|--------|-------|
| Clean up scripts/ directory (32 debug scripts) | P2 | 2h | ⬜ | DevOps |
| Consolidate documentation (4 visual docs merge + root md migration) | P2 | 3h | ⬜ | PM |
| Add E2E test stage to CI | P2 | 4h | ⬜ | Tester + DevOps |
| Add user operation E2E tests | P2 | 6h | ⬜ | Tester |
| Performance optimization for large maps | P2 | 8h | ⬜ | Architect + Coder |

**M5 Acceptance Criteria**:
- [ ] CI pipeline has 4 stages: lint → unit → integration → e2e
- [ ] scripts/ contains only useful utility scripts
- [ ] No overlapping documentation in docs/
- [ ] User operation E2E tests cover: select unit → command → observe result
- [ ] 100×100 isometric map runs at ≥25fps

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
| **v0.3.0** | **Full Features** | **M2** | **~95%** | **3372** | **Victory + Garrison + Bridge + Carryover + Visuals** | ✅ **Current** |
| v0.4-alpha | Polish | M3 | ~96% | 3400 | Command queue UI + Damage visuals + Smoke particles | ⬜ Next |
| v0.5-alpha | Maintainable | M4 | ~97% | 3400 | Architecture refactor + Tech debt cleanup | ⬜ Planned |
| v0.6-alpha | Sustainable | M5 | ~98% | 3500 | CI enhancement + Docs + E2E expansion | ⬜ Planned |
| v0.7-beta | Enhanced | M6 | ~98% | 3600 | Decorations + Sound effects + AI enhancement | ⬜ Planned |
| v1.0-beta | A Bridge Too Far | Final | ≥98% | ≥3600 | Full release candidate | ⬜ Target |

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

**Document Version**: 0.3.0
**Created**: 2026-05-19
**Updated**: 2026-05-30
**Status**: M1+M2 Complete, M3 In Progress
**Next Review**: Upon M3 Completion
**Related Documents**: [GAP_ANALYSIS.md](docs/CC2_GAP_ANALYSIS_AND_PLAN.md) | [TECH_DEBT.md](docs/TECH_DEBT.md)
