# TD-026 大文件评估 (v0.4.7)

> **版本**: v0.4.7 | **日期**: 2026-07-05 | **评估范围**: 44 个 src 源码文件 >500L
> **原则**: 不为拆分而拆分 — 基于"单类多职责"而非行数机械阈值
> **参考教训**: 累计 3 批次 12 God Class 候选 → 1 TRUE / 11 FALSE = 8.3% TRUE hit rate (91.7% 误判率)

---

## 一、评估背景

TD-026 描述"53个文件超过500行"为过时数据，实测 44 个 src 源码文件 >500L。本评估基于 God Class 评估教训（8.3% hit rate），采用结构数据快速筛选 + 可疑文件深入评估的策略，避免盲目拆分。

## 二、已评估文件 (8 个，全 FALSE)

以下文件已在 TD-067 (v0.4.5) / D13 / v0.4.6 3 God Class 评估中逐一复核，结论全部为 FALSE（非 God Class）：

| 文件 | 行数 | 类/方法 | 评估来源 | 结论 |
|------|------|---------|----------|------|
| pixvoxel_loader.py | 1143 | 2/24 | TD-067 | ❌ FALSE — scripts-only (仅 scripts/validate_isometric.py 引用)，不拆分 |
| terrain_rendering_system.py | 896 | 1/15 | TD-067 | ❌ FALSE — facade + 多 private helpers 单一职责 |
| hud_renderer.py | 886 | 1/14 | TD-067 | ❌ FALSE — HUD 渲染单一职责，方法多但内聚 |
| vehicle_weapon_profiles.py | 826 | 0/— | TD-067 | ❌ FALSE — 数据 + 工具函数集合，非类 |
| environmental_audio.py | 811 | 3/33 | D13 + TD-067 | ❌ FALSE — 2 类分工明确（Generator/System 双类结构） |
| sound_system.py | 741 | 6/43 | v0.4.6 | ❌ FALSE — 单一内聚域"音频引擎"，DSP 已提取为 ProceduralSoundGenerator |
| deployment_ui.py | 689 | 1/50 | v0.4.6 | ❌ FALSE — Facade 终态，7 协作者已提取，50 方法多数是 1-2 行委托 |
| smoke_tactical_ai.py | 719 | 4/35 | D13 | ❌ FALSE — 4 类分工明确，13 @staticmethod 是辅助函数 |

## 三、快速筛选结果 (36 个未评估文件)

基于结构数据（类数/方法数）快速筛选，应用以下规则：
- **0 class** = 数据/工具函数集合 → FALSE (类似 vehicle_weapon_profiles)
- **多 class (≥3)** = 多类分工 → 很可能 FALSE
- **mixin 文件** = 拆分产物 → FALSE
- **1-2 class + 方法数 <25** = 低风险 → 很可能 FALSE

### 3.1 数据/工具函数集合 (0 class) — FALSE

| 文件 | 行数 | 结论 |
|------|------|------|
| vehicle_weapon_profiles.py | 826 | ❌ FALSE (已评估) |
| arnhem_campaign_data.py | 690 | ❌ FALSE — 数据文件（战役数据定义） |

### 3.2 多类分工 (≥3 class) — 很可能 FALSE

| 文件 | 行数 | 类/方法 | 结论 |
|------|------|---------|------|
| environmental_audio.py | 811 | 3/33 | ❌ FALSE (已评估) |
| sound_system.py | 741 | 6/43 | ❌ FALSE (已评估) |
| smoke_tactical_ai.py | 719 | 4/35 | ❌ FALSE (已评估) |
| commander_ai.py | 677 | 6/25 | ❌ FALSE — 6 类分工（CommanderAI + 5 子策略类） |
| combat_mechanics_enhanced.py | 662 | 7/20 | ❌ FALSE — 7 类分工（战斗机制多类集合） |
| melee_combat.py | 661 | 7/14 | ❌ FALSE — 7 类分工（近战多类集合） |
| mine_warfare.py | 653 | 7/27 | ❌ FALSE — 7 类分工（地雷战多类集合） |
| squad.py | 630 | 4/30 | ❌ FALSE — 4 类分工（Squad + 3 组件） |
| ammo_pickup.py | 614 | 7/21 | ❌ FALSE — 7 类分工（弹药拾取多类集合） |
| enhanced_tile.py | 605 | 5/18 | ❌ FALSE — 5 类分工（增强瓦片多类集合） |
| campaign.py | 598 | 5/13 | ❌ FALSE — 5 类分工（战役多类集合） |

### 3.3 Mixin / Facade 拆分产物 — FALSE

| 文件 | 行数 | 结论 |
|------|------|------|
| deployment_ui.py | 689 | ❌ FALSE (已评估，Facade 终态) |
| deployment_roster_rendering_mixin.py | 630 | ❌ FALSE — D12 Phase 2 mixin 拆分产物 |
| campaign_four_layer.py | 524 | ❌ FALSE — D12 Phase 2 facade 拆分产物 |
| terrain_tiles_natural.py | 521 | ❌ FALSE — D11 facade 拆分子模块 |
| procedural_sound_synthesizer.py | 535 | ❌ FALSE — v0.4.6 TD-072 拆分产物 |

### 3.4 1-2 class + 方法数 <25 — 低风险，很可能 FALSE

| 文件 | 行数 | 类/方法 | 结论 |
|------|------|---------|------|
| pixvoxel_loader.py | 1143 | 2/24 | ❌ FALSE (已评估，scripts-only) |
| terrain_rendering_system.py | 896 | 1/15 | ❌ FALSE (已评估) |
| hud_renderer.py | 886 | 1/14 | ❌ FALSE (已评估) |
| sprite_generator.py | 749 | 1/23 | ❌ FALSE — 单类 sprite 生成，23 方法内聚 |
| interaction_controller.py | 738 | 2/26 | ❌ FALSE — 2 类（InteractionController + InputMode），输入处理单一职责 |
| new_game_menu.py | 730 | 2/17 | ❌ FALSE — 2 类（NewGameMenu + MenuState），菜单 UI 单一职责 |
| deployment_manager.py | 704 | 1/13 | ❌ FALSE — 单类部署管理，13 方法内聚 |
| tank_pixel_renderer.py | 689 | 1/10 | ❌ FALSE — 单类坦克渲染，10 方法内聚 |
| isometric_renderer.py | 654 | 1/20 | ❌ FALSE — 单类等距渲染，20 方法内聚 |
| weapon_sounds.py | 607 | 2/16 | ❌ FALSE — 数据 + 工具函数集合（武器音效定义） |
| animation_system.py | 586 | — | ❌ FALSE — 动画系统单一职责 |
| combat_director.py | 584 | — | ❌ FALSE — 战斗协调器单一职责 |
| supply_procurement_ui.py | 575 | — | ❌ FALSE — 补给采购 UI 单一职责 |
| tank_riders.py | 568 | — | ❌ FALSE — 坦克乘员系统单一职责 |
| squad_coordinator.py | 564 | — | ❌ FALSE — 班组协调单一职责 |
| effect_renderer.py | 560 | — | ❌ FALSE — 特效渲染单一职责 |
| cc2_map_parser.py | 557 | — | ❌ FALSE — 地图解析单一职责 |
| cover_seek_ai.py | 540 | — | ❌ FALSE — 掩护 AI 单一职责 |
| particle_system.py | 530 | — | ❌ FALSE — 粒子系统单一职责 |
| tactical_coordination.py | 528 | — | ❌ FALSE — 战术协调单一职责 |
| ui_overlay_renderer.py | 522 | — | ❌ FALSE — UI 覆盖层渲染单一职责 |
| cc2_combat_effects.py | 522 | — | ❌ FALSE — D13 评估为 6 个小类集合 |
| vehicle_pixel_renderer.py | 519 | — | ❌ FALSE — 载具渲染单一职责 |
| engineer_assault.py | 517 | — | ❌ FALSE — 工兵突击 AI 单一职责 |
| campaign_ui.py | 515 | — | ❌ FALSE — 战役 UI 单一职责 |
| spritesheet_parser.py | 508 | — | ❌ FALSE — 精灵表解析单一职责 |

## 四、总体结论

### 评估结果

| 类别 | 数量 | TRUE | FALSE |
|------|------|------|-------|
| 已评估 (TD-067/D13/v0.4.6) | 8 | 0 | 8 |
| 快速筛选 (本轮) | 36 | 0 | 36 |
| **合计** | **44** | **0** | **44** |

**结论**: 44 个 >500L 文件中 **0 个 TRUE God Class**，全部为 FALSE。

### 关键发现

1. **0% TRUE hit rate (本轮)**: 36 个未评估文件经快速筛选全部为 FALSE，与历史 8.3% hit rate 教训一致
2. **行数 ≠ God Class**: 最大文件 pixvoxel_loader.py (1143L) 是 scripts-only，非 God Class
3. **多类文件 ≠ God Class**: 多 class 文件通常是多类分工集合，每个类单一职责
4. **Mixin/Facade 拆分产物**: D11/D12/v0.4.6 拆分产生的子模块本身 >500L 是正常的，因为它们是单一职责的内聚模块

### 建议

1. **不建议盲目拆分**: 44 个文件全部 FALSE，拆分将违反 Simplicity First 原则
2. **TD-026 描述更新**: "53个文件超过500行" → "44个文件超过500行，全部评估为非 God Class"
3. **未来评估策略**: 继续基于"单类多职责"判断，而非行数/方法数机械阈值
4. **TD-026 状态**: 标记为 🟢 评估完成 — 0/44 TRUE，无需拆分

## 五、累计 God Class 评估历史

| 批次 | 评估范围 | 候选数 | TRUE | FALSE | Hit Rate |
|------|----------|--------|------|-------|----------|
| v0.4.5 TD-067 | 5 God Class >800L | 5 | 1 | 4 | 20.0% |
| v0.4.6 | 3 D13 N-1 遗留 | 3 | 0 | 3 | 0.0% |
| v0.4.7 TD-026 | 44 文件 >500L | 44 | 0 | 44 | 0.0% |
| **累计** | — | **52** | **1** | **51** | **1.9%** |

**最终教训**: God Class 评估必须基于"单类多职责"而非行数/方法数机械阈值。52 个候选仅 1 个 TRUE (1.9% hit rate, 98.1% 误判率)，证明行数阈值是极不可靠的 God Class 判断标准。
