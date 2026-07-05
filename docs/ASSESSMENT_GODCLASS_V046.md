# God Class 评估报告 (v0.4.6, D13 N-1 遗留)

**评估日期**: 2026-07-05
**评估方法**: 基于项目约定 — God Class = "单一类承担多个不相干职责"，**不**使用 "方法数 >30" 机械阈值
**评估范围**: v0.4.2 遗留的 3 个候选文件（D13 N-1 "方法数 >30" 列表扣除 v0.4.5 已评估项）
**前置评估**: [ASSESSMENT_GODCLASS_V045.md](ASSESSMENT_GODCLASS_V045.md) — TD-067 5 个 >800L 候选 (1 TRUE / 4 FALSE)

## 评估结论速览

| # | 文件 | 行数 | 方法数 | 真实 God Class? | 处置 |
|---|------|------|--------|-----------------|------|
| 1 | `presentation/ui/deployment_ui.py` | 689 | 50 | ❌ FALSE | 保留 — Facade 模式，7 协作者已提取 |
| 2 | `presentation/audio/sound_system.py` | 741 | 43 | ❌ FALSE | 保留 — 单一内聚域"音频引擎" |
| 3 | `presentation/rendering/sprite_renderer_base.py` | 303 | 39 | ❌ FALSE | 保留 — D11-2 SRP 拆分产物，按设计 Facade base |

**Hit rate**: 0/3 = 0%。与 v0.4.5 (1/5 = 20%) 及 D13 N-1 (0/4 = 0%) 结合，**累计 1/12 = 8.3% TRUE**（91.7% 误判率）。

---

## 1. deployment_ui.py (689L, 50 方法) — FALSE positive

**类**: `DeploymentUI`（单一类）

### Facade 模式验证

`__init__` 实例化 **7 个协作者类**，50 个方法中绝大多数是 1-2 行委托包装：

```python
# __init__ (L91-150) — 协作者实例化
self._drag_drop = DeploymentDragDrop()
self._orders = DeploymentOrders()
self._los_system = DeploymentLOSSystem(...)
self._renderer = DeploymentRenderer(self)
self._zone_builder = DeploymentZoneBuilder(self)
self._placement = DeploymentPlacementService(self)
self._input_router = DeploymentInputRouter(self)
```

### 委托方法示例

| 方法 | 委托目标 | 行数 |
|------|---------|------|
| `place_unit(...)` | `self._placement.place_unit(...)` | 1 |
| `can_place_at(...)` | `self._placement.can_place_at(...)` | 1 |
| `handle_click(...)` | `self._input_router.handle_click(...)` | 1 |
| `handle_right_click(...)` | `self._orders.handle_right_click(...)` | 1 |
| `render_deployment_zones(...)` | `self._renderer.render_deployment_zones(...)` | 1 |
| `_create_ghost_surface(...)` | `self._drag_drop._create_ghost_surface(...)` | 1 |
| `start_deployment(...)` | `self._zone_builder.start_deployment(...)` | 1 |

### 单一职责

"部署 UI 协调" — `DeploymentUI` 是 Facade，不持有业务逻辑，仅编排 7 个已提取的协作者。

### 历史背景

v0.3.29-v0.3.32 已完成 SRP 重构，提取 7 个协作者类。50 方法中含 8 个 `@property` backward-compat shim（委托 `_state`）+ 大量 1 行委托。**已是 Facade 终态**，进一步拆分只会增加间接调用无收益。

**保留**。

---

## 2. sound_system.py (741L, 43 方法) — FALSE positive

**文件含 6 个类**:

| 类 | 方法数 | 职责 |
|----|--------|------|
| `SoundConfig` | 0 (dataclass) | 音频配置 |
| `AudioMixerConfig` | 0 (dataclass) | 混音器配置 |
| `SoundPriority` | 0 (Enum) | 优先级枚举 |
| `ProceduralSoundGenerator` | 13 (@classmethod) | DSP 波形合成（纯 numpy，无状态） |
| `SoundSystem` | 27 | 音频引擎核心 |
| `MusicPlayer` | 3 | 背景音乐播放 |

### SoundSystem 27 方法内聚性分析

`SoundSystem` 的 27 方法均围绕"音频引擎"单一内聚域：

- **混音器生命周期** (3): `initialize` / `cleanup` / `reload_config`
- **缓存** (4): `_get_cached_sound` / `_cache_sound` / `clear_cache` / `preload_sounds`
- **播放** (5): `play_sound` / `play_positional` / `stop_sound` / `stop_all` / `_apply_priority`
- **音量** (4): `set_master_volume` / `set_sfx_volume` / `set_music_volume` / `_update_volumes`
- **空间音频** (3): `_calculate_spatial_volume` / `_calculate_spatial_pan` / `set_listener_position`
- **优先级调度** (2): `_apply_priority` / `_evict_low_priority`
- **音乐 ducking** (3): `_duck_music` / `_restore_music` / `_update_music_ducking`
- **状态查询** (3): `is_playing` / `get_active_sounds` / `get_stats`

所有方法共享 `_cache` / `_active_sounds` / `_config` / `_mixer_config` 状态，调用链紧密（播放 → 优先级 → 缓存 → 空间音频 → 音量混合）。

### 与 enhanced_sound_bridge 的本质区别

`enhanced_sound_bridge` (TD-072 TRUE) 是"音频桥接 + DSP 波形合成"两个**完全不相干**职责混合。`sound_system.py` 已将 DSP 合成提取为独立类 `ProceduralSoundGenerator` (13 个 `@classmethod`，纯 numpy，无状态)，剩余 `SoundSystem` 27 方法均为"音频引擎"内聚子方面。

**保留**。`ProceduralSoundGenerator` 已是独立类，无需进一步拆分。

---

## 3. sprite_renderer_base.py (303L, 39 方法) — FALSE positive

**类**: `SpriteRendererBase`（单一类，继承 4 个 focused rendering mixin）

### 39 方法分类

| 类型 | 数量 | 说明 |
|------|------|------|
| `@property` backward-compat shim | 12 | 委托 `_cache_manager` / `_effect_renderer`（如 `_sprite_cache` / `_terrain_cache` / `_effect_particles` / `_damage_numbers` 等） |
| `spawn_*` 委托 | 6 | 1 行委托 `_effect_renderer.spawn_*`（hit_flash / damage_number / muzzle_flash / death_effect / explosion / smoke_screen） |
| `update_*` 显式 no-op | 4 | 系统已迁至专用 renderer，base 保留空实现向后兼容 |
| `render()` orchestrator | 1 | 编排 `_effect_renderer.tick` / `render_decals` / `render_effects` / `render_damage_numbers` / `update_effects` |
| `initialize` / `__init__` | 2 | 生命周期 |
| 其他辅助 | 14 | `_get_pooled_surface` / `draw_surface` 等 |

### 设计意图

D11-2 SRP 拆分产物，明确设计为 **Base/Facade 协调器**。继承自 4 个 focused rendering mixin（terrain / vl-flag / unit / unit-overlay），自身仅提供 backward-compat shim 和编排。303 行是 Facade base 的合理体量。

### 委托方法示例

```python
@property
def _sprite_cache(self) -> dict[str, Surface]:
    return self._cache_manager._sprite_cache

def spawn_hit_flash(self, unit_id: str) -> None:
    self._effect_renderer.spawn_hit_flash(unit_id)

def spawn_damage_number(self, position: Vec2, damage: int, is_kill: bool = False) -> None:
    self._effect_renderer.spawn_damage_number(position, damage, is_kill)
```

**保留**。按设计非 God Class，是 Facade base。

---

## 累计评估历史与教训

### 累计 Hit Rate

| 评估批次 | 候选数 | TRUE | FALSE | Hit Rate |
|---------|--------|------|-------|----------|
| D13 N-1 (方法数 >30) | 4 | 0 | 4 | 0% |
| TD-067 (v0.4.5, >800L) | 5 | 1 | 4 | 20% |
| v0.4.6 (D13 遗留) | 3 | 0 | 3 | 0% |
| **累计** | **12** | **1** | **11** | **8.3%** |

### 唯一 TRUE: enhanced_sound_bridge.py

- v0.4.5 (TD-067) 评估为 TRUE
- v0.4.6 (TD-072) 完成拆分 → `combat_sound_events.py` (47L) + `procedural_sound_synthesizer.py` (536L) + `enhanced_sound_bridge.py` (493L)

### 教训再次验证

> D13 N-1 用"方法数 >30"机械阈值列出候选 → 累计 11/12 误判率 (91.7%)。God Class 评估必须基于"单类多职责"而非方法数/行数机械阈值。

**正确判断标准**:
1. 单一类是否承担**多个不相干职责**？（非"方法多"或"行数长"）
2. 职责间是否**共享状态**？共享 → 可能内聚；不共享 → 可能 God Class
3. 拆分后是否能**独立测试/复用**？能 → 值得拆分；不能 → 拆分无收益
4. 是否已有 **Facade/Coordinator 设计意图**？是 → 非God Class

---

## 处置清单

| 文件 | 处置 | 理由 |
|------|------|------|
| `deployment_ui.py` | 保留 | Facade 终态，7 协作者已提取，进一步拆分无收益 |
| `sound_system.py` | 保留 | 单一内聚域"音频引擎"，DSP 已提取为 ProceduralSoundGenerator |
| `sprite_renderer_base.py` | 保留 | D11-2 SRP 拆分产物，按设计 Facade base |

**无需新立 TD 项**。3 个候选全部 FALSE，关闭 D13 N-1 遗留评估。

---

## 参考

- [ASSESSMENT_GODCLASS_V045.md](ASSESSMENT_GODCLASS_V045.md) — v0.4.5 TD-067 5 候选评估 (1 TRUE / 4 FALSE)
- [TECH_DEBT.md](TECH_DEBT.md) — TD-067 (✅ 5/5 评估完成) / TD-072 (✅ RESOLVED enhanced_sound_bridge 拆分)
- [v0.4.6_PLAN.md](v0.4.6_PLAN.md) — v0.4.6 推进计划 Section 4
- 项目记忆 `Lessons Learned`: "D13 N-1 God Class identification using 'method count >30' threshold led to misjudgment"
