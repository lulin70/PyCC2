# God Class 评估报告 (v0.4.5, TD-067)

**评估日期**: 2026-07-05
**评估方法**: 基于项目约定 — God Class = "单一类承担多个不相干职责"，**不**使用 "方法数 >30" 机械阈值
**评估范围**: D14 标记的 5 个 >800L 候选文件

## 评估结论速览

| # | 文件 | 行数 | 真实 God Class? | 处置 |
|---|------|------|-----------------|------|
| 1 | `presentation/audio/enhanced_sound_bridge.py` | 949 | ✅ TRUE | 计划 v0.5.0 拆分 |
| 2 | `presentation/rendering/terrain_rendering_system.py` | 896 | ❌ FALSE | 保留 |
| 3 | `presentation/ui/hud_renderer.py` | 886 | ❌ FALSE | 保留 |
| 4 | `domain/systems/vehicle_weapon_profiles.py` | 826 | ❌ FALSE | 保留 |
| 5 | `infrastructure/audio/environmental_audio.py` | 811 | ❌ FALSE | 保留（D13 判断正确）|

**Hit rate**: 1/5 = 20%。再次验证 D13 教训：机械阈值误判率高。

---

## 1. enhanced_sound_bridge.py (949L) — TRUE God Class

**类**: `EnhancedSoundSystem`

### 不相干职责
- **职责 A**: 音频桥接（文件加载 → 缓存 → 播放调度），共享状态 `_sound_cache` / `_event_mappings` / `_initialized` / volume
- **职责 B**: 程序化波形合成（13 个 `_gen_*` numpy DSP 方法，~500 LOC），仅读 `self._sfx_volume`，返回 `np.ndarray`，与缓存/加载无协作

### 拆分边界建议（v0.5.0）
- 提取 `ProceduralSoundSynthesizer`（或 `CombatSoundGenerator`）：持有全部 `_gen_*` + `_generate_cc2_combat_fallback` + `_generate_procedural_fallback`
- `EnhancedSoundSystem` 通过组合委托调用合成器
- 预期结果：~450 行合成器 + ~450 行桥接，各自单一职责

### 17 个 `play_*` 便捷方法不是问题
这些是生命周期/缓存的内聚辅助，不构成额外职责。

### 注
文档承诺的 "3D positional audio" 实际未实现 — `position` 参数被接受但未使用，可在拆分时一并清理。

---

## 2. terrain_rendering_system.py (896L) — FALSE positive

**类**: `TerrainRenderingSystem`（v0.3.10 从 `EnhancedRenderer` 抽出）

**单一职责**: 地形渲染管线。所有方法（caching / transitions / smoothing / borders）是同一渲染 pass 的顺序层，共享 `TILE_SIZE` / `_renderer` / TERRAIN_COLORS / `_overlay_surface_pool`。

`draw_enhanced_terrain` 编排：`_ensure_terrain_cache` → `apply_terrain_edge_smoothing` → `render_terrain_transitions` → `draw_terrain_borders`。拆分会打散紧耦合的管线层。

**保留**。次要清理：`get_cached_sprite` 可移至 SpriteCache owner（非 God Class 重构）。

---

## 3. hud_renderer.py (886L) — FALSE positive

**类**: `CC2HUDRenderer`，仅 14 个方法（其中 13 个私有）。

**单一职责**: 渲染 CC2 HUD。三个 `_render_*_panel` 方法是同一布局的空间划分（left=roster, center=detail, right=commands+minimap），非正交职责。

**状态**: 单一字段 `_portrait_renderer`。无独立生命周期、无独立状态、无独立调用者。

**保留**。D13 的 "方法数 >30" 在此失效（仅 14 方法）。如需尺寸优化，可抽 `create_unit_icons` / `create_command_icons` 静态工厂到 `IconFactory`，但非 God Class 重构。

---

## 4. vehicle_weapon_profiles.py (826L) — FALSE positive

**结构**: 无 class 定义。单一函数 `build_vehicle_weapons() -> dict[str, WeaponProfile]`。

**性质**: 纯数据/查找表模块。30 个 `# ---` 区段注释只是组织顺序的 `weapons["key"] = WeaponProfile(...)` 字面量赋值，非方法、非职责。

**保留**。D13 机械阈值把 826 行 + 多区段注释误读为方法数。如为可读性可按武器类别拆分（tank_guns.py / mgs.py / mortars.py），但非 God Class 问题。

---

## 5. environmental_audio.py (811L) — FALSE positive（D13 判断正确）

**双类结构已存在自然缝隙**:
- `EnvironmentalSoundGenerator`: 11 个 `@classmethod` DSP 合成（stateless）
- `EnvironmentalAudioSystem`: mixer 生命周期 + 通道池 + 缓存 + 播放/停止 + 上下文门控（weather/time/location/combat）

**单一概念**: 程序化环境氛围音。11 个生成器是同一合成模式的变体配方，非正交职责。上下文 setter 共答一问："当前应播哪些氛围音？" 并喂给同一 loop 机制。

**保留**。强行抽 `EnvironmentalContextRules` 会打散共享 `_active_sounds` 状态的紧耦合规则集，净负面。

---

## 下一步行动

### v0.5.0 计划（仅 1 项）
- TD-072（新建）: 拆分 `enhanced_sound_bridge.py` → `ProceduralSoundSynthesizer` + `EnhancedSoundSystem`，并清理未实现的 `position` 参数承诺

### v0.4.5 收尾
- 4 个 false positive 保留，无需变更
- 评估报告归档至 `docs/ASSESSMENT_GODCLASS_V045.md`
- TECH_DEBT.md 更新 TD-067 状态

### 教训沉淀
- D13 → D14 → v0.4.5 三轮评估，机械阈值误判率持续 ~80%
- 必须用 "多不相干职责" 实质判断，行数/方法数仅作候选筛选
- 数据/查找表模块（如 vehicle_weapon_profiles）天然不属于 God Class 范畴
