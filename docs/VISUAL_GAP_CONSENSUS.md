# PyCC2 Visual Gap Analysis — CC2 Screenshot Consensus Document

> Generated: 2025-06-11 | Status: APPROVED | Version: 1.0

## 1. Executive Summary

After analyzing **12 CC2 battle screenshots** (`assets/CC2-snapshot/战斗1-9, a-c.jpeg`) against our implementation (`screenshots/smoke_test/`), the DevSquad multi-role team (Architect + UI Designer + Tester) reached consensus on the following:

**Current visual fidelity: ~76%** | **Target: ~92%** | **Gap: 16 percentage points**

---

## 2. CRITICAL Finding: Projection Model Correction

### What We Got WRONG Before

| Previous Assumption | Reality (from screenshots) |
|---------------------|---------------------------|
| "CC2 uses oblique projection with visible wall faces" | **Nearly pure top-down** — walls are 1-2px hints, not 5px faces |
| "Roof numbers are building IDs" | **Roof numbers = FLOOR HEIGHT** ("2"=2-story, "3"=3-story) |
| "Buildings need prominent wall rendering" | **Walls barely visible** — just a dark edge strip |

### Corrected CC2 Projection Model

```
┌──────────────────────────────┐ ← 1px trim line (optional)
│  ╔══════════════════════╗   │
│  ║   [roof texture]  "3" ║   │ ← Roof plane (main visible surface)
│  ║    ○ ○  window dots  ║   │
│  ╚══════════════════════╝   │
▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔  ← 1-2px shadow hint (NOT a wall face!)
```

**Evidence from CC2 screenshots:**
- 战斗2/6/8/9/c: Building roofs dominate the view; walls are thin dark lines
- 战斗4: Trees cast long SE shadows; buildings have minimal wall indication
- 战斗5/7: Infantry units are tiny relative to buildings; pure top-down perspective

---

## 3. Prioritized Fix List (Consensus Order)

### P0 — Must Fix (Visual Impact > 5%)

| # | Fix | File(s) | Effort | Impact |
|---|-----|---------|--------|--------|
| 0.1 | **Wall face: 5px → 1-2px** (barely visible hint) | `cc2_building_renderer.py` L167-168 | 10min | 🔴 High |
| 0.2 | **Global SE shadow system** for trees/units/vehicles | `enhanced_renderer.py` + new `shadow_system.py` | 2hr | 🔴 Critical |
| 0.3 | **Tree multi-tone canopies** (3-4 greens per tree) | `pixel_artist_3d.py` create_tree_sprite | 30min | 🔴 High |
| 0.4 | **Global desaturation pass** (-25% from current) | `pixel_artist.py` CCPalette | 20min | 🟡 Medium |
| 0.5 | **Tree size variation** (small/medium/large) | `pixel_artist_3d.py` + terrain generator | 20min | 🟡 Medium |

### P1 — Should Fix (Visual Impact 2-5%)

| # | Fix | File(s) | Effort | Impact |
|---|-----|---------|--------|--------|
| 1.1 | Crater inner shadow (dark NW→bright SE gradient) | `enhanced_renderer.py` crater rendering | 30min | 🟡 Medium |
| 1.2 | Hedge thicker/darker (deep forest green) | `pixel_artist.py` generate_hedge | 15min | 🟢 Low |
| 1.3 | Road tile smoothing (eliminate square edges) | `enhanced_renderer.py` road blending | 45min | 🟡 Medium |
| 1.4 | Building chimney details | `cc2_building_renderer.py` | 20min | 🟢 Low |
| 1.5 | Roof number = floor height semantics | `cc2_building_renderer.py` label logic | 10min | 🟢 Low |

### P2 — Nice to Have (Visual Impact < 2%)

| # | Fix | File(s) | Effort |
|---|-----|---------|--------|
| 2.1 | Organic river shapes (curved, not tiled straight lines) | Terrain generator overhaul | 4hr |
| 2.2 | Vehicle/unit shadow per-instance | sprite_renderer.py integration | 1hr |
| 2.3 | Smoke effect quality upgrade | visual_effects.py | 1hr |

---

## 4. Integration Plan (Order of Operations)

### Phase 1: Quick Wins (30 min total)

```
Step 0.1: cc2_building_renderer.py → wall_height=5 → wall_height=1 or 2
Step 0.4: pixel_artist.py CCPalette → apply additional -7% desaturation
Step 1.5: cc2_building_renderer.py → roof number = building.height property
```

### Phase 2: Shadow System (2 hr) — BIGGEST VISUAL IMPACT

```
Step 0.2a: Create src/pycc2/presentation/rendering/shadow_system.py
          - ShadowRenderer class
          - render_se_shadow(surface, obj_rect, obj_height) -> offset ellipse
          - Direction: SE (dx=+3, dy=+2 per 24px unit)
          - Color: (0,0,0) alpha=60-100 depending on height
          
Step 0.2b: enhanced_renderer.py → call ShadowRenderer after each object layer
          - Tree layer → shadows
          - Unit layer → shadows  
          - Vehicle layer → shadows
          - Building layer → shadows (optional, walls may suffice)
```

### Phase 3: Tree Upgrade (30 min)

```
Step 0.3: pixel_artist_3d.py create_tree_sprite()
          - Base canopy color + 2-3 accent greens scattered
          - Irregular edge (jagged circle, not smooth)
          - Size parameter: small(16px)/medium(24px)/large(32px)
          - Shadow integrated from Step 0.2
```

### Phase 4: Polish (1.5 hr)

```
Steps 1.1-1.4: Crater shadows, hedges, road smoothing, chimneys
```

---

## 5. Risk Assessment

| Change | Risk Level | Mitigation |
|--------|-----------|------------|
| Wall height 5→2px | 🟢 Low | Only affects visual, no API change |
| Shadow system | 🟡 Medium | New module, isolated; add toggle flag |
| Tree re-render | 🟢 Low | Self-contained in create_tree_sprite() |
| Desaturation | 🟢 Low | Palette-only change; tests check ranges not exact values |
| Road smoothing | 🟡 Medium | Affects terrain pipeline; test autotile system |

**Regression safety**: All changes are in presentation layer only. No domain logic changes.

---

## 6. Verification Criteria

Each fix must pass these checks:

### 0.1 Wall Slimming
- [ ] Building screenshot shows <3px dark edge on S/E sides
- [ ] Roof area occupies >90% of building sprite
- [ ] Tests pass: `test_wall_strip_width <= 3`

### 0.2 Shadow System
- [ ] Each tree in battle_scene.png has SE-pointing dark ellipse
- [ ] Each unit has small shadow dot beneath feet
- [ ] Each vehicle has shadow matching hull shape
- [ ] Shadows do NOT overlap incorrectly (z-order correct)
- [ ] Shadow alpha allows underlying terrain to show through

### 0.3 Tree Multi-tone
- [ ] Tree canopy shows 2+ distinct green shades
- [ ] Edge is irregular (not perfect circle)
- [ ] Different trees in same scene have different sizes

### 0.4 Desaturation
- [ ] composite_showcase.png overall looks darker/more muted than before
- [ ] Grass is clearly darker than `#60A030`
- [ ] Water is clearly darker than `#4090D0`
- [ ] UI elements (buttons, text) NOT affected (stay bright)

### 0.5 Tree Size Variation
- [ ] At least 2 different tree sizes visible in battle scene
- [ ] Size correlates with tree type (oak > bush)

---

## 7. File Change Matrix

| File | Changes | Lines Affected |
|------|---------|---------------|
| `cc2_building_renderer.py` | wall_height, roof number semantics, chimney | ~30 lines |
| `shadow_system.py` | **NEW FILE** — ShadowRenderer class | ~120 lines |
| `enhanced_renderer.py` | integrate shadow calls into render loop | ~40 lines |
| `pixel_artist_3d.py` | tree multi-tone, size variation | ~50 lines |
| `pixel_artist.py` | CCPalette desaturation, hedge darken | ~20 lines |
| Test files | update assertions for new values | ~30 lines |

**Total: ~290 lines changed/added across 6 files**

---

## 8. Appendix: Evidence Links

| Evidence | Location | Key Observation |
|----------|----------|----------------|
| CC2 rural battle | `战斗1.jpeg` | Grass color, road tire tracks, river shape |
| CC2 city battle | `战斗2.jpeg` | Building roofs with numbers, minimal walls, SE shadows |
| CC2 village overview | `战斗3.jpg` | Tree distribution, building spacing, road network |
| CC2 bridge battle | `战斗6.jpeg` | Bridge detail, water appearance, unit scale |
| CC2 desert battle | `战斗8.jpeg` | Sand terrain, crater details, tree shadows |
| Our composite | `composite_showcase.png` | Current state baseline |
| Our battle scene | `battle_scene.png` | In-game rendering comparison |
