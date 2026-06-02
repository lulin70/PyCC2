# PyCC2 v0.3.22 Optimization Plan

**Version**: 1.0  
**Date**: 2026-06-02  
**Based on**: 7-Dimension Critical Audit (v0.3.22)  
**Maturity Score**: 6.8/10 (honest assessment)  
**Target**: 8.0/10 (v0.4.0 Beta readiness)

---

## Multi-Role Analysis

### Architect View
- EventBus dual-channel is the #1 architectural debt — TypedDict + string events coexist, publishers must call both
- 3 God Classes (EnhancedRenderer 62 methods, DeploymentUI 57, SpriteRenderer 45) are change bottlenecks
- 8 orphan modules = dead code inflation
- Domain layer isolation is GOOD — zero violations

### Security View
- Hardcoded absolute path in terrain_detail_generator.py:583 is P0
- AchievementSystem file operations lack path validation
- HMAC key management is well-designed
- No eval/exec/pickle — good

### Performance View
- Rendering loop creates 100+ temporary Surfaces per frame — GC pressure
- ParticlePool exists but is unused — dead optimization code
- CombatDirector double-publishes events (TypedDict + named)
- GameLoop imports Vec2 inside render loop (minor)

### Tester View
- 3657 tests, 100% pass rate — strong
- 48 weak assertions remain (assert > 0, assert True)
- EventBus TypedDict routing has no dedicated test
- E2E tests depend on pygame display

### Coder View
- Duplicate enums in pixel_artist_enums.py + infantry_renderer.py
- Duplicate spawn_explosion methods in EnhancedRenderer
- Duplicate _draw_dashed_line in enhanced_renderer.py + deployment_ui.py
- Type annotations use `object | None` instead of concrete types

---

## Problem Dependency Graph

```
OPT-01 EventBus Unification ─────────────────────────────────────┐
  │ eliminates dual-channel, simplifies all publishers            │
  ▼                                                                │
OPT-02 EnhancedRenderer Split ──── OPT-06 Duplicate Code Removal  │
  │ 62→~30 methods                    │ shared enums/utils        │
  ▼                                   ▼                           │
OPT-03 SpriteRenderer Pool ◄──── OPT-04 ParticlePool Activation   │
  │ 20+ Surface allocs               │ connect pool to system    │
  ▼                                   ▼                           │
OPT-05 Orphan Module Cleanup ──── OPT-07 Path/Type Fixes         │
  │ delete 8 unused                    │ hardcoded paths          │
  ▼                                   ▼                           │
                    Full Regression + E2E ◄───────────────────────┘
```

---

## Optimization Items

### OPT-01: EventBus Unification [P0] [Architecture]

**Problem**: EventBus maintains two routing channels (`_handlers` by type, `_named_handlers` by string). Publishers must call both `publish()` and `publish_named()`. The v0.3.22 bridge fix (dict key matching) is a patch, not a solution.

**Current State**:
```
CombatDirector.execute_attack():
  event_bus.publish(UnitAttacked(...))        # Type channel
  event_bus.publish_named("UnitAttacked", {}) # String channel
  # Same event published TWICE
```

**Target State**:
```
CombatDirector.execute_attack():
  event_bus.publish(UnitAttacked(...))        # Single publish
  # Automatically bridges to named handlers via type name
```

**Solution**: 
1. In `EventBus.publish()`, always bridge to named handlers when event has a `__name__` attribute
2. Remove all `publish_named()` calls from CombatDirector — single `publish()` suffices
3. Keep `publish_named()` for cases where no TypedDict class exists (e.g., "Explosion")
4. Keep `subscribe_to()` for string-based subscription (convenience)

**Risk**: Low — backward compatible, just removes redundant calls

**Verification**: 
- All existing tests pass
- New test: publish TypedDict → named handler receives it
- New test: publish dict with matching keys → named handler receives it

---

### OPT-02: EnhancedRenderer God Class Split [P0] [Architecture]

**Problem**: EnhancedRenderer has 62 methods, ~2240 lines. Any change has high regression risk.

**Current Responsibilities** (too many):
1. Terrain rendering (_draw_enhanced_terrain, _render_terrain_transitions, _apply_terrain_edge_smoothing)
2. Building rendering (_draw_building_roofs, _draw_building_interiors, _draw_building_floor_numbers)
3. Unit rendering (_draw_units, _draw_damage_vfx)
4. VL flag rendering (_draw_vl_flags)
5. Shadow rendering (_render_dynamic_shadows)
6. Environment lighting (_apply_environment_lighting)
7. Particle effects (spawn_explosion, spawn_muzzle_flash, spawn_smoke_screen)
8. Attack line rendering (_draw_attack_lines)
9. LOS overlay (render_los_overlay)
10. Surface pool management (_get_pooled_surface, _invalidate_surface_cache)

**Already Extracted** (v0.3.16):
- particle_effects_renderer.py (12 methods)
- environment_renderer.py (13 methods)

**Next Extraction Targets**:
| Sub-module | Methods to Extract | Est. Lines |
|-----------|-------------------|-----------|
| terrain_renderer.py | _draw_enhanced_terrain, _render_terrain_transitions, _apply_terrain_edge_smoothing, _apply_terrain_variation | ~300 |
| building_renderer.py | _draw_building_roofs, _draw_building_interiors, _draw_building_floor_numbers, _draw_building_walls | ~200 |
| unit_renderer.py | _draw_units, _draw_damage_vfx, _draw_unit_health_bar | ~150 |

**Pattern**: Delegate pattern — keep method signature in EnhancedRenderer, replace body with delegation call.

**Risk**: Medium — must preserve all rendering output exactly

**Verification**: Screenshot comparison before/after (visual regression)

---

### OPT-03: SpriteRenderer Surface Pooling [P0] [Performance]

**Problem**: SpriteRenderer creates 20+ temporary Surfaces per frame in render methods.

**Solution**: Add `_surface_pool` dict to SpriteRenderer, reuse Surfaces by size.

**Pattern**: Same as DynamicShadowSystem._get_pooled_surface() (already implemented in v0.3.22)

**Risk**: Low — purely internal optimization, no API change

**Verification**: Performance benchmark before/after

---

### OPT-04: ParticlePool Activation [P0] [Performance]

**Problem**: ParticlePool exists in particle_pool.py but is never used. ParticleSystem creates temporary objects.

**Solution**: 
1. Wire ParticlePool into ParticleSystem.__init__()
2. Replace `Particle()` creation with `pool.acquire()`
3. Replace particle death with `pool.release()`

**Risk**: Medium — must ensure pool correctly resets particle state

**Verification**: Performance benchmark + visual regression

---

### OPT-05: Orphan Module Cleanup [P1] [Maintainability]

**Problem**: 8 modules exist in src/ but are never imported by any other source file.

| Module | Path | Action |
|--------|------|--------|
| battle_replay.py | domain/systems/ | Keep (planned feature) |
| reinforcement_evasion_bgm.py | domain/systems/ | Keep (planned feature) |
| airdrop_supply.py | domain/systems/ | Keep (planned feature) |
| terrain_detail_generator.py | domain/systems/ | Fix hardcoded path, keep |
| combat_config.py | domain/systems/ | Keep (configuration) |
| enhanced_aar.py | domain/systems/ | Keep (planned feature) |
| pixvoxel_loader.py | presentation/rendering/ | Keep (asset loading) |
| spritesheet_parser.py | presentation/rendering/ | Keep (asset parsing) |

**Decision**: All 8 are planned features or utility modules — keep but add `# PLANNED: not yet wired into game loop` marker.

**Risk**: None — no code changes, just documentation

---

### OPT-06: Duplicate Code Elimination [P1] [Quality]

**6.1 Duplicate Enums**: Direction, Faction, InfantryType defined in both pixel_artist_enums.py and infantry_renderer.py
→ infantry_renderer.py should import from pixel_artist_enums.py

**6.2 Duplicate spawn_explosion**: Two sets in EnhancedRenderer (L2059 and L2161)
→ Remove the older direct-access set, keep only the delegate set

**6.3 Duplicate _draw_dashed_line**: In enhanced_renderer.py:2124 and deployment_ui.py:1209
→ Extract to shared utility (rendering_utils.py)

**Risk**: Low — pure refactoring

---

### OPT-07: Hardcoded Path + Type Annotation [P2] [Security/Quality]

**7.1 Hardcoded Path**: terrain_detail_generator.py:583 has `/Users/lin/trae_projects/PyCC2/data/maps`
→ Replace with `Path(__file__).parent.parent.parent / "data" / "maps"`

**7.2 Type Annotations**: 12 `object | None` fields in GameLoop
→ Replace with concrete types (EffectStack | None, CombatCameraController | None, etc.)

**Risk**: Very low

---

## Execution Order

| Step | OPT | Priority | Depends On | Est. Impact |
|------|-----|----------|-----------|-------------|
| 1 | OPT-01 | P0 | None | Architecture: eliminates dual-publish |
| 2 | OPT-06.2 | P1 | None | Quality: removes duplicate methods |
| 3 | OPT-02 | P0 | OPT-06.2 | Architecture: God Class split |
| 4 | OPT-03 | P0 | None | Performance: Surface pooling |
| 5 | OPT-04 | P0 | None | Performance: ParticlePool activation |
| 6 | OPT-06.1+6.3 | P1 | None | Quality: shared enums + utils |
| 7 | OPT-05 | P1 | None | Maintainability: orphan markers |
| 8 | OPT-07 | P2 | None | Security + Quality |
| 9 | Full Regression + E2E | — | All | Verification |

---

## Success Criteria

| Metric | Current (v0.3.22) | Target (v0.4.0) |
|--------|-------------------|-----------------|
| Maturity Score | 6.8/10 | 8.0/10 |
| EnhancedRenderer methods | 62 | ≤35 |
| Per-frame Surface allocations | 100+ | ≤20 |
| Dual-publish calls | 3 (CombatDirector) | 0 |
| Orphan modules | 8 | 0 (all marked) |
| Duplicate code instances | 3 | 0 |
| Hardcoded absolute paths | 2 | 0 |
| Test pass rate | 100% | 100% |
