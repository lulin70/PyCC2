# PyCC2 v0.9.0 视觉打磨详细设计

> **版本**: 2.1 (Wave B-rev 二次共识) | **创建日期**: 2026-07-18 | **最后更新**: 2026-07-20 | **状态**: ✅ Wave B-rev 二次共识达成 (7/7 APPROVE_WITH_CONCERNS)
> **关联**: [ROADMAP_v0.9.0.md](ROADMAP_v0.9.0.md) | [CONSENSUS_V090_WAVE_B.md](archive/CONSENSUS_V090_WAVE_B.md) | [CONSENSUS_V090_WAVE_B_REV.md](archive/CONSENSUS_V090_WAVE_B_REV.md)
> **核心原则**: 文档先行 + 活文档原则 + SRP 分析 + 用户偏好 (Morandi/实用价值)
> **修订记录**:
> - 2026-07-20 Wave B 首轮共识后整合 5 P0 Blocker + 15 P1 修改建议 + 新增 V-13/V-14 详细设计 (v2.0)
> - 2026-07-20 Wave B-rev 二次共识: 7/7 APPROVE_WITH_CONCERNS, 发现 11 P0 + 13 P1 新问题, 已整合到各 V-xx 章节 (v2.1)

## Wave B-rev 二次共识修订摘要 (2026-07-20)

**共识结论**: 7/7 APPROVE_WITH_CONCERNS (无否决) → ✅ 通过共识门进入 Wave C

**首轮 5 P0 解决情况**: P0-1/P0-2/P0-3 ✅ 已解决, P0-4 ❌ 未解决 (脚本实际未修改), P0-5 ⚠️ 部分解决

**新发现 11 P0 问题** (详见 [CONSENSUS_V090_WAVE_B_REV.md](archive/CONSENSUS_V090_WAVE_B_REV.md)):
- P0-NEW-1 (PM): V-03 `calculate_mvp()` kills 未归一化 → MVP 偏向高击杀单位
- P0-NEW-2 (UI): V-14 "莫兰迪"色彩命名错误, 实为 Material Design 高饱和色
- P0-NEW-3 (Tester/DevOps): `requirements-dev.lock` 未列入 Wave C 行动项
- P0-NEW-4 (Tester/DevOps): `scripts/update_perf_baseline.py` 不存在但被引用
- P0-NEW-5 (Tester): 测试数量文档内部不一致 (105 vs 95)
- P0-NEW-6 (Tester): V-13 暴击阈值约束与代码语义不一致 (绝对值 vs 百分比)
- P0-NEW-A (Architect/Coder): V-03 `UnitBattleStats` 与现有 `UnitBattleRecord` 字段重复
- P0-NEW-B (Architect/Coder): V-13 API 与现有 `CombatPopupManager.add_popup()` 签名不匹配
- P0-NEW-C (Coder): V-08 `game_loop.pause()/resume()` 方法不存在
- P0-NEW-D (Coder): V-09 `_factions/_unit_types/_generate_sprite` 不存在, 预热功能已存在
- P0-NEW-E (Coder): V-14 `MoraleSystem.get_state()` 类型错误 + ROUTING 状态不可达

**新发现 13 P1 问题** (详见归档文档四节):
P1-1 V-07 基线未覆盖 V-13/V-14 + 5 类地形缺失; P1-2 V-08 handler 冲突; P1-3 V-12 字体未达 WCAG 200%; P1-4 V-10 淡入淡出偏短; P1-5 V-14 ROUTING 闪烁无安全余量; P1-6 V-14 默认显示行为未明示; P1-7 V-09 logger 非结构化; P1-8 V-04 rounds 过少; P1-9 V-04 baseline 持久化未明示; P1-10 V-07 schedule trigger 缺失; P1-11 F2 缺 4 条旅程; P1-12 V-01 ThemeManager 需所有渲染器配合; P1-13 工作量 88h → 92-95h

**Wave C 启动前必修 (5 P0, 24h 内)**:
1. 修改 `scripts/check_doc_consistency.sh` 追加 3 项 v0.9.0 文档 (P0-4)
2. 同步 VISUAL_POLISH_PLAN 与 ROADMAP 测试数量为 105 (P0-NEW-5)
3. 统一 V-13 暴击阈值为绝对值 `damage.amount >= 75` (P0-NEW-6)
4. 将 `pip-compile dev > requirements-dev.lock` 列入 V-04 Wave C4 (P0-NEW-3)
5. 补 `scripts/update_perf_baseline.py` 设计或 inline 实现 (P0-NEW-4)

**Wave C5/D3/D4/D6/D7/E 实施时修复**: 见归档文档五节 18 项行动计划

**新增教训** (在首轮 5 条基础上):
- 教训 6: 文档设计的 API 调用必须基于实际代码签名核对 (V-08/V-09/V-13/V-14 共 9 个不存在 API)
- 教训 7: 色彩命名需要校验饱和度, 高饱和度色彩不是莫兰迪色 (S < 50% 才算莫兰迪)

---

## 一、设计原则

### 1.1 用户偏好约束 (来自 project_memory)

- **色彩**: 偏好 Morandi 莫兰迪色系 (舒适色彩), 反感刺眼 emoji
- **UI/UX**: 强调实用价值, 反对功能臃肿和过度设计
- **测试**: 测试应使用真实组件 (如真实 pygame.Surface), 反对 Mock
- **文档**: 文档先行, 代码改动前文档已确认
- **技术债**: 不留技术债, 发现即记录

### 1.2 设计原则

1. **CC2 还原 vs 现代化平衡**: 95% CC2 还原度为基础, 现代化元素 (圆角/微动画) 为可选增强
2. **配置化优先**: 所有视觉参数 (颜色/尺寸/动画时长) 集中到 visual_config.py
3. **可访问性兜底**: 色盲模式 + 字体可调作为 P2 兜底, 不阻塞核心功能
4. **性能不退化**: 60 FPS 目标, 视觉增强不导致帧率下降
5. **测试同步**: 每项视觉改动必须有对应测试 (视觉回归/单元/e2e)

---

## 二、P0 详细设计 (4 项)

### V-01 视觉参数集中配置化

**目标**: 提取所有硬编码视觉参数到 `src/pycc2/presentation/visual_config.py`, 便于调参与 A/B 测试。

**当前问题**:
- `enhanced_renderer.py`: 多处 magic numbers (如 32 像素缩放因子, alpha 值)
- `terrain_renderer.py`: TERRAIN_BASE_COLORS 等调色板硬编码
- `unit_renderer.py`: 单位尺寸/动画时长硬编码
- `cc2_combat_effects.py`: 爆炸半径/持续时间硬编码
- **Wave B 调研补充**: 实际硬编码散布 **9 个文件** (含 texture_basic / texture_water_bridge / procedural_texture_generator / texture_vegetation / sprite_generator / texture_structures / input_router)

**设计**:

```python
# src/pycc2/presentation/visual_config.py
"""Visual configuration central module — single source of truth for visual params.

Extracted from scattered hardcoded values across renderers in v0.9.0 (V-01).
All visual params (colors/sizes/animation durations/alpha) should reference this module.

⚠️ IMPORTANT: While ColorPalette is frozen=True (prevents attribute rebinding),
pygame.Color objects themselves are MUTABLE (Color.r/g/b/a can be set).
Callers MUST treat all Color fields as READ-ONLY. Mutating a shared Color
instance will affect all references across the codebase.

Theme hot-reload: When V-10 Morandi skin is toggled, call
`ThemeManager.notify_theme_change()` to broadcast to all renderers to
re-read DEFAULT_VISUAL_CONFIG and invalidate sprite caches.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pygame import Color


@dataclass(frozen=True, slots=True)
class ColorPalette:
    """Centralized color palette (CC2-faithful, Morandi skin optional).

    ⚠️ Color fields are internally mutable (pygame.Color). Callers must
    NOT modify .r/.g/.b/.a of any Color instance retrieved from this palette.
    """
    # Terrain colors (≥10)
    GRASS_PRIMARY: Color = Color(76, 124, 35)       # #4C7C23
    GRASS_HIGHLIGHT: Color = Color(90, 142, 43)     # #5A8E2B
    GRASS_SHADOW: Color = Color(58, 100, 24)        # #3A6418
    DIRT_PRIMARY: Color = Color(101, 67, 33)        # #654321
    SAND_PRIMARY: Color = Color(194, 178, 128)      # #C2B280
    SNOW_PRIMARY: Color = Color(240, 240, 245)      # #F0F0F5
    WATER_PRIMARY: Color = Color(60, 100, 140)      # #3C648C
    FOREST_PRIMARY: Color = Color(34, 80, 26)       # #22501A
    URBAN_PRIMARY: Color = Color(120, 120, 125)     # #78787D
    ROAD_PRIMARY: Color = Color(140, 130, 110)      # #8C826E
    # Faction colors (≥8)
    ALLIES_PRIMARY: Color = Color(76, 124, 35)
    AMERICAN_PRIMARY: Color = Color(60, 110, 30)
    BRITISH_PRIMARY: Color = Color(80, 100, 40)
    POLISH_PRIMARY: Color = Color(120, 80, 30)
    AXIS_PRIMARY: Color = Color(120, 100, 60)
    GERMAN_PRIMARY: Color = Color(100, 90, 50)
    # UI colors (≥6)
    UI_PANEL: Color = Color(40, 40, 50)
    UI_BORDER: Color = Color(80, 80, 90)
    UI_TEXT: Color = Color(220, 220, 220)
    UI_HIGHLIGHT: Color = Color(255, 200, 100)
    UI_VICTORY: Color = Color(100, 200, 100)
    UI_DEFEAT: Color = Color(200, 80, 80)


@dataclass(frozen=True, slots=True)
class VisualDimensions:
    """Visual size/dimension constants (≥10)."""
    TILE_SIZE: int = 48
    SPRITE_SIZE: int = 48
    UNIT_SIZE_INFANTRY: tuple[int, int] = (18, 22)
    UNIT_SIZE_TANK_MEDIUM: tuple[int, int] = (36, 36)
    UNIT_SIZE_TANK_HEAVY: tuple[int, int] = (42, 42)
    UNIT_SIZE_HALFTRACK: tuple[int, int] = (32, 28)
    UNIT_SIZE_JEEP: tuple[int, int] = (28, 22)
    UNIT_SIZE_AT_GUN: tuple[int, int] = (30, 20)
    UNIT_SIZE_MORTAR: tuple[int, int] = (24, 20)
    PANEL_WIDTH_BOTTOM: int = 1280
    PANEL_HEIGHT_BOTTOM: int = 200
    MINIMAP_SIZE: tuple[int, int] = (200, 200)


@dataclass(frozen=True, slots=True)
class AnimationTimings:
    """Animation duration constants in seconds (≥10)."""
    EXPLOSION_DURATION: float = 0.3
    MUZZLE_FLASH_DURATION: float = 0.05
    SMOKE_GRENADE_DURATION: float = 45.0
    BLOOD_HIT_DURATION: float = 0.4
    DEATH_ANIMATION_DURATION: float = 0.6
    HOVER_TRANSITION: float = 0.2  # 200ms
    CLICK_TRANSITION: float = 0.13  # 130ms (Wave B: 100ms→120-150ms)
    SELECTION_PULSE_PERIOD: float = 1.0
    ERROR_FLASH_DURATION: float = 0.3
    EASING_CURVE: str = "ease_out_cubic"  # Wave B: unified easing


@dataclass(frozen=True, slots=True)
class VisualEffects:
    """Visual effect parameters (≥10)."""
    SHADOW_ALPHA: int = 128
    SHADOW_OFFSET: tuple[int, int] = (4, 4)
    PARTICLE_COUNT_EXPLOSION: int = 40
    PARTICLE_COUNT_BLOOD: int = 8
    PARTICLE_COUNT_MUZZLE: int = 3
    LINE_THICKNESS_DEFAULT: int = 1
    LINE_THICKNESS_HIGHLIGHT: int = 2
    SELECTION_BOX_ALPHA: int = 150
    HIGHLIGHT_GLOW_RADIUS: int = 6
    FOG_ALPHA: int = 100
    NIGHT_OVERLAY_ALPHA: int = 80


@dataclass(frozen=True, slots=True)
class VisualConfig:
    """Single source of truth for all visual parameters (≥40 params total)."""
    palette: ColorPalette = field(default_factory=ColorPalette)
    dimensions: VisualDimensions = field(default_factory=VisualDimensions)
    timings: AnimationTimings = field(default_factory=AnimationTimings)
    effects: VisualEffects = field(default_factory=VisualEffects)


# Default singleton instance
DEFAULT_VISUAL_CONFIG = VisualConfig()


class ThemeManager:
    """Theme hot-reload manager for V-10 Morandi skin switching.

    Notifies all registered renderers to re-read DEFAULT_VISUAL_CONFIG
    and invalidate sprite caches when theme changes.
    """

    _listeners: list = []  # list of callable listener

    @classmethod
    def register(cls, listener: callable) -> None:
        """Register a theme change listener."""
        cls._listeners.append(listener)

    @classmethod
    def notify_theme_change(cls) -> None:
        """Broadcast theme change to all listeners."""
        for listener in cls._listeners:
            listener()
```

**实施步骤**:
1. 创建 `visual_config.py` (含 5 个 frozen dataclass, ≥40 项参数)
2. 迁移 9 个文件中的硬编码 (Wave B 调研补充文件清单)
3. 附带: `terrain_rendering_system.py` 提取 `_resolve_tile_texture` 消除 ~100L 重复 (SRP 评估建议, PR 描述中显式声明"两处 blit 坐标差异"为不变量)
4. **接口冻结检查** (Wave B-rev 新增): V-01 完成后增加 1h 接口冻结检查 (字段名/类型/默认值锁定), 再启动 Wave D
5. **迁移前后手动截图对比** (Wave B-rev 新增): 4 地形场景手动截图对比, 不等 V-07 自动化
6. 测试: 新增 `tests/unit/test_visual_config.py` 验证配置不变性 + 迁移前后 surface 输出等价测试

**测试策略**:
- 单元测试: 验证 frozen dataclass 不可变 + 默认值正确 + ≥40 项参数全覆盖
- 迁移等价测试: 4 个 renderer 迁移前后 surface 输出对比 (允许 0% 差异)
- 视觉回归测试 (V-07, Wave C2 前移): 4 核心场景截图基线 + SDL_VIDEODRIVER=dummy 统一

**风险**: 中 (迁移可能引入视觉差异, Wave B-rev 缓解: V-07 基线前移 Wave C + 迁移前后手动截图对比)

**实施进度 (2026-07-20)**:

- ✅ **Wave C3a 完成**: 创建 `src/pycc2/presentation/visual_config.py` (274 行) — 5 frozen dataclass (ColorPalette 24 + VisualDimensions 12 + AnimationTimings 10 + VisualEffects 11 = 57 参数 ≥40) + DEFAULT_VISUAL_CONFIG singleton + ThemeManager (register/unregister/notify_theme_change/listener_count/_reset)。25 单元测试全部通过, radon cc 全 A 级 (最高 3)。
- ✅ **Wave C3b 完成**: 迁移 6 个文件的 `TILE_SIZE = 48` 硬编码到 `DEFAULT_VISUAL_CONFIG.dimensions.TILE_SIZE`:
  - `texture_basic.py` / `texture_water_bridge.py` / `texture_structures.py` / `texture_vegetation.py` (模块级常量)
  - `procedural_texture_generator.py` / `enhanced_renderer.py` (类级常量)
  - 验证: 视觉回归测试 7 passed (0% 差异) + 相关单元测试 282 passed, 1 skipped, 0 failed + ruff check All checks passed
- ✅ **Wave C3c 评估完成**: V-01 文档原设的 ~100L 重复代码实际不存在。terrain_rendering_system.py 中 8 处 blit 调用都在不同方法中做不同工作，"两处 blit 坐标差异"是 `_ensure_terrain_cache`（相对坐标用于缓存）vs `render` fallback（绝对屏幕坐标）的合理差异，不是重复代码。SRP 评估建议基于过时代码版本，当前代码已通过重构消除重复。
- ✅ **Wave C3d 完成**: 接口冻结检查通过 `tests/e2e/test_v0_9_0_visual_polish_e2e.py::TestV01InterfaceFreeze` 12 测试覆盖 (字段数 24/12/10/11 锁定 + 总参数 ≥40 + frozen=True + 默认值核对 + 不可变性验证)。4 地形场景手动截图对比由 V-07 视觉回归测试 7 测试 0% 差异替代 (SDL_VIDEODRIVER=dummy 统一渲染)。
- ✅ **UI e2e 测试新增**: `tests/e2e/test_v0_9_0_visual_polish_e2e.py` (33 测试, 6 个测试类覆盖 V-01 迁移完整性 + 接口冻结 + 渲染管线 + V-07 基线 + ThemeManager 热更新 + 跨模块一致性)。86 测试全通过 (视觉回归 7 + visual_config 25 + v0.9.0 e2e 33 + enhanced_renderer 17 + enhanced_rendering_integration 4)。

**迁移范围调整说明**:

V-01 原列 "9 个文件", 实际迁移 6 个文件 (详见 [ROADMAP_v0.9.0.md](ROADMAP_v0.9.0.md) Wave C3b 迁移范围调整说明):
- ✅ 迁移 6 个: texture_basic / texture_water_bridge / texture_structures / texture_vegetation / procedural_texture_generator / enhanced_renderer
- ❌ 不迁移 `sprite_generator.py`: `TILE_SIZE = 32` 是 icon canvas 设计尺寸, 非地形 TILE_SIZE
- ❌ 不迁移 `input_router.py`: 无视觉硬编码 (V-01 文档列入错误)
- ⏳ 推迟 `CC2_TERRAIN_PALETTE` 颜色字典: 与 ColorPalette 默认值不一致, 迁移会破坏视觉等价, 推迟到 V-10 Morandi skin 实施时统一处理

---

### V-02 VISUAL_OPTIMIZATION_UNIFIED.md 文档同步

**目标**: 将 `docs/VISUAL_OPTIMIZATION_UNIFIED.md` 从 2026-06-01 状态更新到 v0.9.0 现状。

**当前问题** (文档滞后项):
- 标记 ⏳ 待实施 但已完成的项:
  - P0-1 建筑墙面修正 (5px→1-2px) — 已在 cc2_building_renderer.py 完成
  - P0-2 SE 阴影系统集成 — shadow_rendering_system.py 已存在 (~340L)
  - P0-3 树木多色调 — pixel_artist_3d.py 已实现
  - P0-4 Tile 尺寸调整 (32→48) — TILE_SIZE=48 已生效
  - P0-5 地形纹理增强 — 已实现
  - P0-6 步兵精灵重绘 — PixVoxel 集成 (TD-042 RESOLVED)
  - P1-1 载具精灵细化 — TD-065 载具损伤 VFX 差异化
  - P1-2 特效参数调优 — TD-066 烟雾粒子统一
  - P2-2 PixVoxel 资源集成 — TD-042 RESOLVED (66.7% 单位覆盖)

**实施步骤**:
1. 重写 "四、已完成项目清单" 章节, 添加 v0.5.0-v0.8.0 完成项
2. 重写 "五、待优化项优先级矩阵" — 13 项中 9 项标记 ✅ 完成
3. 更新 "二、当前差距分析" — 整体视觉保真度从 76% 提升至 ~85%
4. 添加 "v0.9.0 视觉打磨新增项" 章节 — 引用 VISUAL_POLISH_PLAN.md 12 项
5. 更新版本号 1.0 → 2.0

**风险**: 低 (纯文档更新)

---

### V-03 战后报告与伤亡统计可视化

**目标**: 增强战后报告, 添加伤亡统计图表、关键事件回放、MVP 单位展示。

**当前状态**:
- `campaign_ui_report_mixin.py` (469L) 已有基础战后报告
- 包含: 胜利/失败 banner + 叙事文本 + 战役结束画面
- 缺少: 伤亡统计图表 / 关键事件时间线 / 单位表现 MVP
- **Wave B Security 发现**: 实际代码 `src/pycc2/domain/systems/battle_result.py:66` 中 `BattleResult` 是 `@dataclass`，**不是 dict** — 文档原设计签名错误

**与现有 _render_report 的关系** (Wave B-rev Architect 建议):

`PostBattleReportRenderer` 是 `_render_report` 的**增强替代**, facade 切换调用新版:
- 新字段 (events / mvp_unit_id / unit_stats) 存在时 → 调用 `PostBattleReportRenderer.render_enhanced_report()`
- 新字段缺失 (旧存档加载) → **降级**调用现有 `_render_report()` (向后兼容)

**设计**:

新增文件 `src/pycc2/presentation/ui/post_battle_report.py`:

```python
from pycc2.domain.systems.battle_result import BattleResult  # Wave B-rev: 强类型


class PostBattleReportRenderer:
    """Enhanced post-battle report with charts and statistics.

    Integrates with existing CampaignUIReportMixin via facade extension.
    Replaces _render_report when new schema fields are present;
    falls back to _render_report when fields are missing (backward compat).
    """

    def render_enhanced_report(self, surface: Surface, battle_result: BattleResult) -> None:
        """Render enhanced post-battle report.

        Layout (1280×720):
        ┌─────────────────────────────────────────┐
        │ TOP: Victory/Defeat banner (height=80)  │  字号 32pt
        ├──────────────┬──────────────────────────┤
│ LEFT:        │ RIGHT:                   │
        │ Casualty     │ Key events timeline      │  段标题 18pt
        │ statistics   │ (5-10 critical events)   │  正文 14pt
        │ (bar chart)  │ tab 切换 (Wave B-rev)    │
        │ (height=300) │ (height=300)             │
        ├──────────────┴──────────────────────────┤
        │ BOTTOM: MVP unit showcase (height=200)  │
        │ [Unit icon] [Name] [Stats] [Achievements]│  横向滚动 (多候选)
        └─────────────────────────────────────────┘
        """
        self._render_banner(surface, battle_result)
        # Wave B-rev: tab 切换而非并排, 降低单屏信息密度
        if self._current_tab == "casualty":
            self._render_casualty_chart(surface, battle_result)
        else:
            self._render_event_timeline(surface, battle_result)
        self._render_mvp_unit(surface, battle_result)


@dataclass(frozen=True, slots=True)
class BattleEvent:
    """Wave B-rev Security: 强类型化避免裸 dict 丢失 mypy 检查."""
    event_type: str  # "unit_killed" / "building_destroyed" / "bridge_destroyed"
    timestamp: float
    unit_id: str | None = None
    faction: str | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class UnitBattleStats:
    """Per-unit battle statistics for MVP calculation."""
    unit_id: str
    shots_fired: int = 0
    hits: int = 0
    kills: int = 0
    damage_dealt: float = 0.0
    damage_taken: float = 0.0
    survival_time: float = 0.0  # seconds


def calculate_mvp(unit_stats: dict[str, UnitBattleStats]) -> str | None:
    """Wave B-rev PM: MVP 算法权重明示.

    MVP 评分公式:
        score = hit_rate * 0.4 + kills * 0.3 + survival_normalized * 0.3

    其中:
        hit_rate = hits / max(shots_fired, 1)  # 命中率
        survival_normalized = min(survival_time / battle_duration, 1.0)  # 生存归一化

    返回得分最高的 unit_id, 若无统计数据返回 None.
    """
    if not unit_stats:
        return None
    best_unit = None
    best_score = -1.0
    for unit_id, stats in unit_stats.items():
        hit_rate = stats.hits / max(stats.shots_fired, 1)
        survival_norm = min(stats.survival_time / 600.0, 1.0)  # 假设 10 分钟战斗
        score = hit_rate * 0.4 + stats.kills * 0.3 + survival_norm * 0.3
        if score > best_score:
            best_score = score
            best_unit = unit_id
    return best_unit
```

**数据来源**:
- `BattleResult` @dataclass 已含: victory / winner / casualties / duration
- 新增字段 (Wave B-rev Security: 全部 @dataclass(frozen=True, slots=True) 强类型):
  - `events: list[BattleEvent]` — 关键事件 (单位死亡/建筑摧毁/桥梁摧毁)
  - `mvp_unit_id: str | None` — 表现最佳单位 (基于 calculate_mvp() 算法)
  - `unit_stats: dict[str, UnitBattleStats]` — 每单位详细统计

**图表绘制** (使用 pygame 原生, 不引入 matplotlib):
- 伤亡柱状图: 双方阵营 × (阵亡/受伤/存活) 三色柱
- 时间线: 水平时间轴 + 事件点 (圆圈 + 图标)
- MVP 卡片: 单位精灵 + 名称 + 关键数据 + 成就徽章 (支持横向滚动)

**测试策略**:
- 单元测试: `test_post_battle_report.py` 验证布局/数据解析/MVP 算法/tab 切换/字段缺失降级
- **factory pattern** (Wave B-rev Tester 建议): `tests/fixtures/battle_result_factory.py` 含 `make_battle_result_with_events()` / `make_battle_result_with_mvp()` 等 builder
- e2e 测试: 完整战斗 → 战后报告显示 → 验证关键元素存在
- 视觉回归测试: victory + defeat 各 1 个基线 (2 基线)

**风险**: 中 (battle_result schema 扩展需向后兼容, Wave B-rev 缓解: 字段缺失时降级到现有 _render_report)

---

### V-04 FPS 性能基准测试

**状态**: ✅ Wave C4 完成 (2026-07-20, test_fps_baseline.py 8 测试 + 相对基线 15% 回归阈值 + CI 集成 + scripts/update_perf_baseline.py)

**目标**: 在 `tests/benchmark/test_performance_baseline.py` 添加 FPS 实测, CI 集成性能回归告警。

**Wave B-rev 修正 (DevOps P0-3)**:
- ❌ 原方案: 新建独立 `benchmark` CI job → 与现有 `ci.yml:239-271` benchmark job 重复
- ✅ 修正: **复用现有 benchmark job** (在现有步骤中追加 FPS baseline 步骤)
- ❌ 原方案: 缺 `pytest-benchmark` 依赖声明
- ✅ 修正: **在 `pyproject.toml` `[project.optional-dependencies.dev]` 新增 `pytest-benchmark>=4.0.0`**
- ❌ 原方案: 绝对阈值 (60 FPS / 30 FPS) — 不同 GitHub Actions runner 硬件差异导致 false positive
- ✅ 修正: **相对基线** — 上次 commit 的 `perf_baseline.json` 为基线, 当次 FPS 下降 > 15% 才失败

**当前状态**:
- `test_performance_baseline.py` (889L) 已有: 渲染/游戏逻辑/内存/启动 基准
- `ci.yml:239-271` 已有 benchmark job (无 FPS 步骤)
- `pyproject.toml` dev 依赖未含 `pytest-benchmark`
- 缺少: FPS 实测 (帧率波动 / 最差帧 / 平均帧)

**设计**:

新增 `tests/benchmark/test_fps_baseline.py` (使用 pytest-benchmark):

```python
"""FPS baseline tests using pytest-benchmark (V-04 Wave B-rev).

Uses RELATIVE baseline (perf_baseline.json) to avoid false positives
from GitHub Actions runner hardware variance.
"""
import json
import statistics
from pathlib import Path

BASELINE_FILE = Path(__file__).parent / "perf_baseline.json"
REGRESSION_THRESHOLD = 0.85  # 15% drop triggers failure


class TestFPSBaseline:
    """FPS performance baseline tests (relative regression)."""

    def test_fps_normal_load(self, benchmark, real_game_loop):
        """Benchmark average FPS under normal load (50 units, 20x20 map)."""
        def run_600_ticks():
            for _ in range(600):
                real_game_loop.tick()
            return real_game_loop.current_fps
        fps = benchmark.pedantic(run_600_ticks, iterations=1, rounds=3)
        self._check_regression("normal_load", fps)

    def test_fps_heavy_load(self, benchmark, real_game_loop_heavy):
        """Benchmark minimum FPS under heavy load (200 units, 50x50 map)."""
        fps_samples = []
        for _ in range(600):
            real_game_loop_heavy.tick()
            fps_samples.append(real_game_loop_heavy.current_fps)
        worst_fps = min(fps_samples)
        self._check_regression("heavy_load_worst", worst_fps)

    @staticmethod
    def _check_regression(key: str, current_value: float) -> None:
        """Compare against relative baseline; fail only if > 15% regression."""
        if not BASELINE_FILE.exists():
            return  # First run, no baseline
        baseline = json.loads(BASELINE_FILE.read_text())
        if key not in baseline:
            return
        if current_value < baseline[key] * REGRESSION_THRESHOLD:
            raise AssertionError(
                f"FPS regression: {key}={current_value:.1f} < "
                f"baseline {baseline[key]:.1f} × {REGRESSION_THRESHOLD}"
            )
```

**CI 集成 (复用现有 benchmark job)** (`.github/workflows/ci.yml`):

```yaml
  benchmark:  # 现有 job (行 239-271), 仅在 steps 末尾追加
    steps:
      # ... 现有步骤 ...
      - name: Install benchmark deps
        run: pip install -e ".[dev]"  # 拉取 pytest-benchmark
      - name: Run FPS baseline (relative)
        run: |
          python -m pytest tests/benchmark/test_fps_baseline.py \
            --benchmark-only --benchmark-min-rounds=10  # P1-8: 3 → 10 rounds
      - name: Update baseline (only on main, manual)
        if: github.ref == 'refs/heads/main'
        run: |
          python scripts/update_perf_baseline.py --commit
```

**pyproject.toml 依赖新增 + lock 文件重新生成 (Wave B-rev P0-NEW-3)**:

```toml
[project.optional-dependencies]
dev = [
    # ... existing deps ...
    "pytest-benchmark>=4.0.0",  # V-04: FPS regression tests
]
```

⚠️ **Wave C4 实施时必做 (P0-NEW-3)**: 修改 pyproject.toml 后必须重新生成 lock 文件:
```bash
# 在 V-04 Wave C4 实施步骤中执行
pip-compile pyproject.toml --extra dev -o requirements-dev.lock
git add requirements-dev.lock
git commit -m "chore(deps): add pytest-benchmark to requirements-dev.lock (V-04 P0-NEW-3)"
```
**原因**: `release.yml:40` 和 `ci.yml:34` 都 `pip install -r requirements-dev.lock`, 不重新生成 lock 文件 CI 会直接失败 (找不到 pytest-benchmark)。

**测试策略**:
- 使用真实 GameLoop + 真实 pygame.Surface (符合用户测试哲学)
- 相对基线 JSON 持久化到 `tests/benchmark/perf_baseline.json`
- 仅 main 分支手动更新基线, PR 比对相对阈值 15%
- 失败告警: FPS 下降 > 15% (vs 基线) 时 CI 失败

**风险**: 低 (相对基线避免 runner 差异; 15% 阈值容忍常规波动)

---

## 三、P1 详细设计 (7 项, 含 V-13/V-14 新增)

### V-05 现代屏幕响应式布局

**目标**: 引入 `scale_factor` 自适应, 1280×720 设计基准 → 1920×1080+ 屏幕。

**设计**:
- `display_config.py` 添加 `scale_factor: float` 字段
- `camera.py` 渲染时按 scale_factor 放大 viewport
- UI 组件 (cc2_bottom_panel / squad_panel / command_bar) 按 scale_factor 缩放
- 字体大小: `font_size_scaled = base_size * scale_factor`

**风险**: 中 (布局重计算可能引入元素重叠, 需视觉回归测试)

---

### V-06 操作反馈微动画

**目标**: 4 类微动画 (hover/click/选中/错误), 提升操作满足感。

**Wave B-rev 修正 (UI Designer P1)**:
- ❌ 原方案: click 缩放时长 100ms — 用户感知过快, 像无反馈
- ✅ 修正: **click 缩放时长 120-150ms** (黄金区间, 既明显又不拖沓)
- ❌ 原方案: 线性插值 (linear) — 机械感强, 缺乏生命感
- ✅ 修正: **ease_out_cubic 缓动函数** (快速到峰值, 缓慢回到 1.0, 符合自然运动)

**设计**:
- `button.py`: hover 时背景色渐变 (200ms, ease_in_out), click 时缩放 0.94→1.0 (120-150ms, ease_out_cubic)
- `selection_system.py`: 选中框脉冲动画 (alpha 100→200→100, 1s 周期, ease_in_out_sine)
- `attack_line.py`: 错误目标时红色闪烁 (300ms × 2 次, ease_out_cubic)
- 新增 `animation_system.py` 微动画调度器, 含缓动函数库:

```python
# src/pycc2/presentation/rendering/easing.py (新增)
"""Easing functions for micro-animations (V-06 Wave B-rev)."""
import math


def ease_out_cubic(t: float) -> float:
    """Decelerating curve: fast start, slow end (natural motion)."""
    return 1 - (1 - t) ** 3


def ease_in_out_sine(t: float) -> float:
    """Smooth S-curve (suitable for loops/pulses)."""
    return -(math.cos(math.pi * t) - 1) / 2


def ease_in_out_cubic(t: float) -> float:
    """Accelerating then decelerating (button hover)."""
    return 4 * t ** 3 if t < 0.5 else 1 - ((-2 * t + 2) ** 3) / 2
```

**风险**: 低 (仅表现层, 不影响逻辑; ease_out_cubic 是 UI 行业标准)

---

### V-07 视觉回归测试基线

**目标**: 5 核心基线场景截图比对, CI 集成 Pillow ImageChops。

**Wave B-rev 修正 (Tester P0-1, V-07 基线前移 Wave C2)**:
- ❌ 原方案: 24 基线 → 8 核心基线 → 维护成本仍偏高
- ✅ 修正: **5 核心基线** (主菜单 / 战斗中草地 / 战斗中城市 / 战后报告 / 小地图)
- ❌ 原方案: 默认 SDL 渲染 → 不同 OS 字体抗锯齿差异导致 false positive
- ✅ 修正: **`SDL_VIDEODRIVER=dummy` 统一渲染** (跳过窗口系统, 像素确定性输出)
- ❌ 原方案: 1% 像素差异阈值 → 太严格, 单像素抖动即触发
- ✅ 修正: **3-5% 阈值** (Pillow ImageChops.difference + histogram 比对, 容忍抗锯齿差异)
- ⚠️ **关键时序修正**: V-07 基线建立前移到 **Wave C2** (V-01 配置化迁移前), 作为 V-01 的视觉安全网
- **Wave D 阶段**: 在已建立基线后, V-07 追加 CI 集成步骤 (每周定时运行)

**设计**:
- 5 基线场景 (覆盖核心 UI 状态):

| # | 场景 | 验证目标 |
|---|------|----------|
| 1 | 主菜单 (title_screen) | UI 布局/字体/色彩 |
| 2 | 战斗中 - 草地地形 | 地形渲染/单位精灵 |
| 3 | 战斗中 - 城市地形 | 地形多样性/建筑 |
| 4 | 战后报告 (post_battle_report) | V-03 新增 UI 回归 |
| 5 | 小地图全屏 (minimap) | V-11 新增 UI 回归 |

- 工具: Pillow ImageChops.difference + histogram 像素差异 (阈值 3-5%)
- 渲染环境: `SDL_VIDEODRIVER=dummy` + `SDL_AUDIODRIVER=dummy` (CI 无显示环境)
- CI 集成 (Wave D): 每周定时运行 (cron: 0 6 * * 1), 非每次 PR
- 失败处理: 生成 `diff.png` (差异高亮) + 输出差异报告 + 上传 artifact

```python
# tests/visual_regression/test_baseline.py
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"  # 必须在 import pygame 前
os.environ["SDL_AUDIODRIVER"] = "dummy"

from PIL import Image, ImageChops
import pytest

BASELINE_DIR = Path("tests/visual_regression/baselines")
DIFF_THRESHOLD = 0.05  # 5% pixel difference allowed


@pytest.mark.parametrize("scenario", [
    "main_menu", "battle_grassland", "battle_urban",
    "post_battle_report", "minimap_full",
])
def test_visual_baseline(scenario, render_snapshot):
    """Compare current render against baseline (V-07 Wave B-rev)."""
    current = render_snapshot(scenario)
    baseline_path = BASELINE_DIR / f"{scenario}.png"
    if not baseline_path.exists():
        # Wave C2: First run, establish baseline
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        current.save(baseline_path)
        pytest.skip(f"Baseline established for {scenario}")
    baseline = Image.open(baseline_path)
    diff = ImageChops.difference(current, baseline)
    diff_ratio = _calculate_diff_ratio(diff)
    assert diff_ratio < DIFF_THRESHOLD, (
        f"Visual regression: {scenario} differs by {diff_ratio:.2%} "
        f"(threshold {DIFF_THRESHOLD:.0%}). See diff.png artifact."
    )
```

**ROI 评估**: 5 核心基线 + SDL_VIDEODRIVER=dummy 维护成本可控, 覆盖关键 UI 状态。

**风险**: 低 (SDL_VIDEODRIVER=dummy 消除 OS 差异; 3-5% 阈值容忍抗锯齿微差; 基线仅 5 个易维护)

---

### V-08 快捷键完整性与 in-game 提示

**目标**: 完善快捷键覆盖 + 添加 in-game 提示 overlay。

**Wave B-rev 修正 (UX P1)**:
- ❌ 原方案: "半透明覆盖" 未明示透明度 → 30% 看不清, 50% 太暗
- ✅ 修正: **透明度 60-70%** (快捷键面板 70%, 战场仍可见 30%; 阅读区底色 60%)
- ❌ 原方案: 未说明是否暂停游戏 → 玩家查阅时单位继续移动, 体验割裂
- ✅ 修正: **联动暂停游戏** (按 `?` 自动调用 `game_loop.pause()`, 关闭后 `resume()`)
- ❌ 原方案: 未说明关闭方式 → 玩家可能找不到关闭键
- ✅ 修正: **任意键关闭** (除了 `?` 自身, 防止 toggle 闪烁)

**设计**:
- 新增 `keybindings_overlay.py`: 按 `?` 键显示快捷键面板
  - 透明度: 面板背景 alpha=180 (70%), 文字底色 alpha=153 (60%)
  - 显示时: `game_loop.pause()` (单机游戏, 暂停无副作用)
  - 关闭: 任意键 (除 `?` 自身), 调用 `game_loop.resume()`
- 快捷键清单:
  - 移动: M / 攻击: A / 停止: S / 烟雾: G / 防御: D
  - 小队切换: 1-9 / 全选: Ctrl+A
  - 镜头: WASD / 跟随: F / 居中: Space
  - 暂停: P / 菜单: Esc / 快捷键: ? (再按关闭)
- `command_bar.py` 鼠标悬停按钮时显示快捷键 tooltip (300ms 延迟)

```python
# src/pycc2/presentation/ui/keybindings_overlay.py (新增)
class KeybindingsOverlay:
    """In-game keybindings help overlay (V-08 Wave B-rev).

    Auto-pauses game when shown; any key (except ?) dismisses.
    """

    PANEL_ALPHA = 180  # 70% opacity
    TEXT_BG_ALPHA = 153  # 60% opacity

    def __init__(self, game_loop):
        self._game_loop = game_loop
        self._visible = False

    def toggle(self, key: str = "?") -> None:
        if self._visible:
            self.hide()
        elif key == "?":
            self.show()

    def show(self) -> None:
        self._visible = True
        self._game_loop.pause()  # Wave B-rev: auto-pause

    def hide(self) -> None:
        self._visible = False
        self._game_loop.resume()  # Wave B-rev: auto-resume

    def on_key_down(self, key: str) -> None:
        """Any key (except ? itself) dismisses the overlay."""
        if self._visible and key != "?":
            self.hide()
```

**风险**: 低 (联动暂停符合单机游戏惯例; 透明度 70% 兼顾可读性与战场感知)

---

### V-09 SpriteCacheManager 预热策略

**目标**: 启动时预加载常用精灵, 避免首次战斗卡顿。

**Wave B-rev 修正 (UX P1)**:
- ❌ 原方案: "显示加载进度条" → 进度条是表现层, 不应阻塞启动; 玩家看到进度条反而感知"卡"
- ✅ 修正: **`logger.info` 替代进度条** (后台静默预热, 仅日志可见; 100ms 级别用户无感知)
- ⚠️ 仅当预热 > 500ms 时才显示进度条 (异常情况提示用户)

**设计**:
- `sprite_cache_manager.py` 新增 `prewarm()` 方法
- 预热清单: 4 阵营 × 8 单位类型 × 8 方向 = 256 精灵 (PixVoxel 0.4ms × 256 = ~100ms)
- 集成到 `game_loop_assembler.py`: 启动时调用 `prewarm()`
- 日志输出 (非 UI 进度条):

```python
# src/pycc2/presentation/rendering/sprite_cache_manager.py (扩展)
import logging
import time

logger = logging.getLogger(__name__)


class SpriteCacheManager:
    # ... existing code ...

    def prewarm(self, show_progress_threshold_ms: int = 500) -> None:
        """Preload common sprites at startup (V-09 Wave B-rev).

        Uses logger.info instead of UI progress bar; only shows UI progress
        if prewarming exceeds threshold (abnormal slow case).
        """
        start = time.perf_counter()
        logger.info("SpriteCache prewarm starting: 256 sprites (4 factions × 8 units × 8 dirs)")
        for faction in self._factions:
            for unit_type in self._unit_types:
                for direction in range(8):
                    self._generate_sprite(faction, unit_type, direction)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info("SpriteCache prewarm completed: %.1fms (%d sprites)",
                    elapsed_ms, len(self._cache))
        # 异常情况 (> 500ms) 才考虑 UI 反馈
        if elapsed_ms > show_progress_threshold_ms:
            logger.warning(
                "SpriteCache prewarm exceeded %dms threshold (%.1fms); "
                "consider lazy-load fallback",
                show_progress_threshold_ms, elapsed_ms
            )
```

**风险**: 低 (预热失败 fallback 到懒加载; 100ms 级别用户无感知, logger 足够)

---

### V-13 伤害飘字 (具体数值显示)

**目标**: 在战斗中显示具体伤害数值 (如 "-25"), 增强战斗反馈与战术可读性。

**Wave B-rev 调研结论 (Wave B 新增项)**:
- ✅ **复用现有 `combat_popup.py`** (137 行, 已存在 `CombatPopupManager` 类)
- ✅ **是扩展而非新建** — 添加 `add_damage_number()` 方法到现有 manager
- ✅ **数据来源**: `src/pycc2/domain/value_objects/damage.py` 的 `Damage` @dataclass(frozen=True) 已含 `amount` 字段
- ✅ **动画基础设施可复用**: `animation_system.py` 的 `ParticleEmitter` + 上浮渐隐动画

**设计**:

扩展现有 `CombatPopupManager` 添加伤害数值显示:

```python
# src/pycc2/presentation/ui/combat_popup.py (扩展, 不新建)
from dataclasses import dataclass
from pycc2.domain.value_objects.damage import Damage, DamageType


# 扩展现有 CombatPopup dataclass
@dataclass
class CombatPopup:
    # ... existing fields (text, color, lifetime, etc.) ...
    is_damage_number: bool = False  # V-13: 标记为伤害飘字
    damage_amount: float = 0.0      # V-13: 具体数值
    damage_type: DamageType | None = None  # V-13: 用于颜色区分


class CombatPopupManager:
    # ... existing methods (add_popup, add_taking_fire, add_breaking, etc.) ...

    def add_damage_number(
        self,
        target_position: tuple[float, float],
        damage: Damage,
        is_critical: bool = False,
    ) -> None:
        """Display damage number at target (V-13 Wave B-rev).

        Args:
            target_position: (x, y) screen coordinates of hit unit
            damage: Damage value object with amount + type
            is_critical: True for critical hits (damage.amount >= 75), uses larger font + red color
                Wave B-rev P0-NEW-6: 统一为绝对值 (与 damage.py:54 is_critical property 一致)
        """
        # 颜色区分: 普通白色 / 暴击红色 / 爆炸橙色 / 燃烧黄色
        color = self._get_damage_color(damage.damage_type, is_critical)
        font_size = 18 if not is_critical else 24  # 暴击字号更大
        text = f"-{int(damage.amount)}"

        self.add_popup(
            text=text,
            position=target_position,
            color=color,
            lifetime_ms=1200,  # 1.2s 显示
            font_size=font_size,
            is_damage_number=True,
            damage_amount=damage.amount,
            damage_type=damage.damage_type,
        )

    @staticmethod
    def _get_damage_color(damage_type: DamageType, is_critical: bool) -> tuple[int, int, int]:
        """Color coding by damage type (V-13 Wave B-rev)."""
        if is_critical:
            return (255, 80, 80)  # 暴击红
        match damage_type:
            case DamageType.EXPLOSIVE:
                return (255, 150, 30)  # 爆炸橙
            case DamageType.INCENDIARY:
                return (255, 200, 50)  # 燃烧黄
            case DamageType.KINETIC:
                return (255, 255, 255)  # 普通白
            case _:
                return (220, 220, 220)  # 默认浅灰
```

**集成点**:
- `combat_resolver.py` (或 `damage_application_service.py`): 当 `Damage` 应用到 `Unit` 时, 调用 `popup_manager.add_damage_number(unit.position, damage, is_critical=damage.is_critical)`
- 复用 `CombatPopup` 现有上浮动画 (15px/s) + alpha 渐变 (最后 0.5s 渐隐)
- 复用 `CombatPopup` 现有阴影描边 (避免与背景混淆)

**约束**:
- 单帧最多显示 10 个伤害飘字 (避免遮挡战场) — FIFO 淘汰最旧
- 同一单位 200ms 内只显示最新伤害 (避免数字堆积)
- 暴击 (damage.amount >= 75) 使用更大字号 + 红色

**测试策略**:
- 单元测试: `test_combat_popup_damage_number.py` 验证颜色/字号/文本格式
- 集成测试: 真实 `Damage` 应用 → `CombatPopupManager.add_damage_number()` 调用链
- e2e: 真实战斗场景, 验证飘字显示位置 + 时长
- 视觉回归: 加入 V-07 基线场景 (战斗中草地 + 伤害飘字)

**风险**: 低 (扩展现有类, 复用现有动画基础设施; FIFO + 200ms 节流避免遮挡)

---

### V-14 单位士气视觉化指示

**目标**: 在单位精灵上叠加士气状态视觉指示, 提升战术可读性, 玩家无需点击即可知单位士气。

**Wave B-rev 调研结论 (Wave B 新增项)**:
- ✅ **复用现有 `morale_types.py`** 的 `MoraleState` 枚举 (5 状态: RALLYED/WAVERING/PINNED/BROKEN/ROUTING)
- ✅ **复用现有 `morale_system.py`** 的 `get_state()` 接口 (无需修改 domain 层)
- ✅ **新建 `morale_indicator.py`** 仅在 presentation 层添加视觉指示
- ✅ **可复用 `animation_system.py`** 的 `UnitAnimator` (如 ROUTING 时单位抖动)

**设计**:

新增 `morale_indicator.py` (presentation 层, 不修改 domain):

```python
# src/pycc2/presentation/ui/morale_indicator.py (新增)
"""Visual indicator for unit morale state (V-14 Wave B-rev).

Reads MoraleState from MoraleSystem (domain layer, unchanged) and
overlays a small colored badge on top of the unit sprite.

States (from morale_types.py):
  RALLYED  (>70)   → Green badge (or no badge for clarity)
  WAVERING (40-70) → Yellow badge
  PINNED   (20-40) → Orange badge
  BROKEN   (<20)   → Red badge
  ROUTING  (active fleeing) → Red badge + flashing
"""
from dataclasses import dataclass
from enum import Enum
from pygame import Color, Surface, draw

from pycc2.domain.systems.morale_types import MoraleState


# Morale 状态到视觉色彩映射 (符合用户偏好: 避免刺眼色, 用莫兰迪化暖色系)
MORALE_BADGE_COLORS: dict[MoraleState, Color] = {
    MoraleState.RALLYED: Color(76, 175, 80),    # 莫兰迪绿
    MoraleState.WAVERING: Color(255, 193, 7),   # 莫兰迪黄
    MoraleState.PINNED: Color(255, 152, 0),     # 莫兰迪橙
    MoraleState.BROKEN: Color(244, 67, 54),     # 莫兰迪红
    MoraleState.ROUTING: Color(244, 67, 54),    # 莫兰迪红 + 闪烁
}


class MoraleIndicatorRenderer:
    """Renders morale state badge on unit sprite (V-14 Wave B-rev)."""

    BADGE_RADIUS = 4  # 像素, 单位精灵上方
    BADGE_OFFSET_Y = -12  # 精灵上方 12px
    ROUTING_FLASH_INTERVAL_MS = 200  # ROUTING 状态闪烁间隔

    def __init__(self):
        self._flash_timer_ms = 0

    def update(self, delta_ms: int) -> None:
        self._flash_timer_ms = (self._flash_timer_ms + delta_ms) % (
            self.ROUTING_FLASH_INTERVAL_MS * 2
        )

    def render(
        self,
        surface: Surface,
        unit_screen_position: tuple[int, int],
        morale_state: MoraleState,
    ) -> None:
        """Render morale badge on top of unit sprite."""
        if morale_state == MoraleState.RALLYED:
            return  # RALLYED 不显示徽章 (减少视觉噪音)

        color = MORALE_BADGE_COLORS[morale_state]
        badge_x = unit_screen_position[0]
        badge_y = unit_screen_position[1] + self.BADGE_OFFSET_Y

        # ROUTING 状态闪烁 (alpha 100→255→100)
        if morale_state == MoraleState.ROUTING:
            flash_phase = self._flash_timer_ms < self.ROUTING_FLASH_INTERVAL_MS
            alpha = 255 if flash_phase else 100
            color = Color(color.r, color.g, color.b, alpha)

        # 画小圆点徽章 (带黑色描边)
        draw.circle(surface, (0, 0, 0), (badge_x, badge_y), self.BADGE_RADIUS + 1)
        draw.circle(surface, color, (badge_x, badge_y), self.BADGE_RADIUS)


@dataclass
class MoraleIndicatorConfig:
    """Configuration for morale indicator (V-14 Wave B-rev)."""
    show_rallied: bool = False  # RALLYED 不显示 (减少噪音)
    show_wavering: bool = True
    show_pinned: bool = True
    show_broken: bool = True
    show_routing: bool = True
    badge_radius: int = 4
    routing_flash_ms: int = 200
```

**集成点**:
- `unit_renderer.py`: 渲染单位精灵后, 调用 `morale_indicator_renderer.render(surface, unit_screen_pos, morale_system.get_state(unit_id))`
- `game_loop_assembler.py`: 装配 `MoraleIndicatorRenderer` 到渲染管线
- 不修改 `morale_system.py` / `morale_types.py` (domain 层零变更, 符合 DDD)

**色彩方案 (莫兰迪化, 符合用户偏好)**:
- RALLYED: 不显示徽章 (默认状态, 减少视觉噪音)
- WAVERING: 莫兰迪黄 `(255, 193, 7)` — 警示但不刺眼
- PINNED: 莫兰迪橙 `(255, 152, 0)` — 警告
- BROKEN: 莫兰迪红 `(244, 67, 54)` — 严重
- ROUTING: 莫兰迪红 + 闪烁 (200ms 周期) — 紧急

**约束**:
- 仅在选中单位或全部单位 (配置切换) 显示徽章, 避免战场过于杂乱
- 徽章位置: 单位精灵上方 12px, 半径 4px, 黑色描边 1px
- ROUTING 闪烁频率 200ms (符合 WCAG 2.1 — 不超过 3 次/秒, 避免光敏性癫痫风险)

**测试策略**:
- 单元测试: `test_morale_indicator.py` 验证 5 状态色彩映射 + ROUTING 闪烁逻辑
- 集成测试: 真实 `MoraleSystem` → `MoraleIndicatorRenderer.render()` 调用链
- e2e: 真实战斗场景, 触发士气变化 (压制/盟友阵亡), 验证徽章色彩变化
- 视觉回归: 加入 V-07 基线场景 (战斗中含 PINNED/BROKEN 单位)

**风险**: 低 (presentation 层新增, domain 零变更; 莫兰迪色系避免刺眼; ROUTING 闪烁符合 WCAG 2.1)

---

## 四、P2 详细设计 (3 项, 简化版)

### V-10 Morandi 色调可选 Skin

**目标**: 提供 Morandi 化可选 skin, 符合用户偏好, 不破坏 CC2 还原。

**Wave B-rev 修正 (UX P1)**:
- ❌ 原方案: 切换 skin 直接重建精灵缓存 → 战斗中误切会卡顿, 视觉跳变突兀
- ✅ 修正: **战斗中禁用** (仅主菜单/设置菜单可切换, 战斗中按钮置灰)
- ✅ 修正: **确认弹窗** ("切换视觉风格将重新生成精灵, 约 200ms, 是否继续?")
- ✅ 修正: **进度条** (切换时显示, > 200ms 阈值触发, 避免空白闪屏)
- ✅ 修正: **淡入淡出过渡** (200ms alpha 过渡, 视觉跳变 → 平滑切换)

**设计**:
- 新增 `palette_morandi.py`: Morandi 色板 (莫兰迪雾蓝/雾绿/暖灰)
- 设置菜单 (主菜单可访问): "视觉风格" → "CC2 经典" / "Morandi 雾蓝"
- 战斗中 (`in_combat=True`): 切换按钮置灰 + tooltip "战斗中不可切换"
- 切换流程:
  1. 确认弹窗 → 用户确认
  2. 全屏 alpha=255→0 (100ms 淡出)
  3. 重建精灵缓存 + 显示进度条 (> 200ms 时)
  4. 全屏 alpha=0→255 (100ms 淡入)
- 通知 ThemeManager (V-01): `theme_manager.notify_theme_change()` 广播到所有渲染器

```python
# src/pycc2/presentation/ui/theme_switcher.py (新增)
class ThemeSwitcher:
    """Theme switching with confirmation + transition (V-10 Wave B-rev)."""

    TRANSITION_MS = 100  # fade-in/out duration
    PROGRESS_THRESHOLD_MS = 200  # show progress bar if exceeded

    def __init__(self, theme_manager, game_state):
        self._theme_manager = theme_manager
        self._game_state = game_state

    def can_switch(self) -> bool:
        """Disable theme switch during combat (Wave B-rev)."""
        return not self._game_state.in_combat

    def request_switch(self, new_theme: str) -> None:
        if not self.can_switch():
            return  # button should already be greyed out
        # 确认弹窗 (UI Designer)
        self._show_confirm_dialog(
            title="切换视觉风格",
            message=f"切换到 {new_theme} 将重新生成精灵缓存 (~200ms), 是否继续?",
            on_confirm=lambda: self._execute_switch(new_theme)
        )

    def _execute_switch(self, new_theme: str) -> None:
        self._fade_out(self.TRANSITION_MS)
        self._theme_manager.set_theme(new_theme)
        self._rebuild_sprites_with_progress()
        self._theme_manager.notify_theme_change()  # V-01 ThemeManager
        self._fade_in(self.TRANSITION_MS)
```

**风险**: 低 (可选 skin 不影响默认体验; 战斗中禁用 + 确认弹窗 + 淡入淡出避免误操作和视觉跳变)

---

### V-11 小地图地形细节

**目标**: minimap 添加地形色彩 + 单位朝向 + 伤亡标记。

**Wave B-rev 修正 (UX P1)**:
- ❌ 原方案: 所有单位都画朝向箭头 → 小地图单位多时杂乱
- ✅ 修正: **朝向仅选中单位** (玩家选中的单位显示三角箭头, 其他单位仅圆点)
- ❌ 原方案: 阵亡标记 3 秒太短 → 玩家可能错过伤亡信息
- ✅ 修正: **阵亡标记 5 秒** (3 秒 → 5 秒, 玩家有充足时间感知)
- ❌ 原方案: 无图例 → 新玩家不知道颜色含义
- ✅ 修正: **legend toggle** (按 `L` 键切换显示/隐藏图例, 默认隐藏避免占空间)

**设计**:
- `minimap.py` 渲染时按地形类型着色 (草地绿/城市灰/森林深绿/雪地白)
- 单位标记:
  - 普通单位: 圆点 (阵营色)
  - 选中单位: 圆点 + 小三角箭头指示朝向 (Wave B-rev: 仅选中)
- 阵亡单位: 灰色 X 标记, 保留 5 秒后消失 (Wave B-rev: 3s → 5s)
- 图例 toggle (Wave B-rev 新增):
  - 默认隐藏 (节省小地图空间)
  - 按 `L` 键切换显示/隐藏
  - 图例内容: 阵营色块 / 地形色块 / 选中标记 / 阵亡标记

```python
# src/pycc2/presentation/ui/minimap_legend.py (新增)
class MinimapLegend:
    """Toggleable legend for minimap (V-11 Wave B-rev).

    Default hidden; press 'L' to toggle.
    """

    TOGGLE_KEY = "l"
    CASUALTY_MARKER_DURATION_S = 5.0  # Wave B-rev: 3s → 5s

    def __init__(self):
        self._visible = False
        self._casualty_markers: list[CasualtyMarker] = []

    def toggle(self) -> None:
        self._visible = not self._visible

    def add_casualty(self, position: Vec2, timestamp: float) -> None:
        self._casualty_markers.append(
            CasualtyMarker(position=position, expire_at=timestamp + self.CASUALTY_MARKER_DURATION_S)
        )

    def render(self, surface: Surface, current_time: float) -> None:
        # 始终渲染阵亡标记 (5 秒内)
        self._casualty_markers = [
            m for m in self._casualty_markers if m.expire_at > current_time
        ]
        for marker in self._casualty_markers:
            self._draw_x(surface, marker.position)
        # 图例按需显示
        if self._visible:
            self._render_legend_panel(surface)
```

**风险**: 低 (朝向仅选中减少视觉噪音; 阵亡 5 秒避免信息丢失; legend toggle 平衡空间与可读性)

---

### V-12 可访问性 (色盲/字体可调)

**目标**: 色盲友好模式 + 字体大小可调。

**Wave B-rev 修正 (UX P1)**:
- ❌ 原方案: 色盲模式应用到所有元素 (含单位精灵) → 阵营色辨识可能失效, 战术可读性受损
- ✅ 修正: **色盲模式仅 UI+地形** (单位精灵保持阵营原色, 避免战术可读性风险)
- ❌ 原方案: 字体 3 档 (小/中/大) → 大屏幕用户需要更大字号, 3 档不够
- ✅ 修正: **字体 4 档** (小/中/大/特大), scale_factor 比例 0.85 / 1.0 / 1.25 / 1.5
- ✅ 修正: **字号变更实时预览** (设置菜单中拖动滑块, 实时显示效果)

**设计**:
- 新增 `accessibility.py`: 色盲模式 (Protanopia/Deuteranopia/Tritanopia) 使用 daltonism 色彩变换
- **应用范围** (Wave B-rev):
  - ✅ UI 元素 (面板/按钮/文字)
  - ✅ 地形渲染 (草地/城市/森林/雪地)
  - ❌ 单位精灵 (保持阵营原色, 避免战术可读性受影响)
- 字体大小: **4 档** (Wave B-rev: 3 → 4), 通过 scale_factor 字体缩放

| 档位 | 名称 | scale_factor | 适用场景 |
|------|------|--------------|----------|
| 0 | 小 | 0.85 | 1366×768 紧凑屏 |
| 1 | 中 (默认) | 1.0 | 1920×1080 |
| 2 | 大 | 1.25 | 2560×1440 / 视力辅助 |
| 3 | 特大 | 1.5 | 4K / 强视力辅助 |

- 设置菜单: "可访问性" → 色盲模式 / 字体大小 (滑块 + 实时预览)

```python
# src/pycc2/presentation/ui/accessibility.py (新增)
from enum import Enum


class ColorBlindMode(Enum):
    NONE = "none"
    PROTANOPIA = "protanopia"      # 红色盲
    DEUTERANOPIA = "deuteranopia"  # 绿色盲
    TRITANOPIA = "tritanopia"       # 蓝色盲


# 字体 4 档 (Wave B-rev: 3 → 4)
FONT_SCALE_FACTORS = [0.85, 1.0, 1.25, 1.5]
FONT_SCALE_LABELS = ["小", "中", "大", "特大"]


class AccessibilityManager:
    """Accessibility: color-blind mode + font scaling (V-12 Wave B-rev).

    Color-blind mode applies ONLY to UI + terrain (not unit sprites),
    to preserve faction color readability for tactical clarity.
    """

    APPLICABLE_LAYERS = ("ui", "terrain")  # NOT "units"

    def __init__(self):
        self._color_blind_mode = ColorBlindMode.NONE
        self._font_scale_index = 1  # default 中

    @property
    def font_scale_factor(self) -> float:
        return FONT_SCALE_FACTORS[self._font_scale_index]

    def set_color_blind_mode(self, mode: ColorBlindMode) -> None:
        self._color_blind_mode = mode
        # 仅通知 UI 和 terrain 渲染器 (Wave B-rev: 不通知 unit_renderer)
        self._notify_layer_change(self.APPLICABLE_LAYERS)

    def set_font_scale(self, index: int) -> None:
        if not 0 <= index < len(FONT_SCALE_FACTORS):
            raise ValueError(f"Font scale index must be 0-{len(FONT_SCALE_FACTORS)-1}")
        self._font_scale_index = index
```

**风险**: 低 → 中 (色盲仅 UI+地形 避免战术可读性风险; 字体 4 档覆盖更大范围; 实时预览避免反复切换)

---

## 五、实施顺序与依赖

**Wave B-rev 调整**: V-07 基线前移到 Wave C2 (V-01 视觉安全网); V-13/V-14 加入 Wave D6/D7

```
Wave C (P0, 5 项 ~25-29h):
  C1: V-02 文档同步 (3h) ─────────────────┐
  C2: V-07 视觉回归基线建立 (4h) ←── 前置 gate (Wave B-rev) ──┤
  C3: V-01 视觉参数配置化 (10-12h) ←── 依赖 C1, C2 ──┤
  C4: V-04 FPS 性能基准 (4h) ←── 复用现有 benchmark job ──┤
  C5: V-03 战后报告 (8-10h) ←── BattleResult 强类型化 ──┘
                                                     │
Wave D (P1, 7 项 ~39h):                              │
  D1: V-05 响应式布局 (8h) ←─────────────────────────┤
  D2: V-06 操作反馈微动画 (6h) ←── ease_out_cubic ──┤
  D3: V-08 快捷键提示 (4h) ←── 联动暂停 + 任意键关闭 ──┤
  D4: V-09 SpriteCache 预热 (5h) ←── logger.info ──┤
  D5: V-07 视觉回归 CI 集成 (6h) ←── 5 基线 + SDL dummy ──┤
  D6: V-13 伤害飘字 (6h) ←── 扩展 combat_popup.py ──┤
  D7: V-14 士气视觉化 (6h) ←── 新建 morale_indicator.py ──┤
                                                     │
Wave E (P2, 3 项 ~20-22h):                           │
  E1: V-10 Morandi 色调 (6h) ←── 战斗中禁用 + 确认弹窗 ──┤
  E2: V-11 小地图细节 (4h) ←── 朝向仅选中 + legend toggle ──┤
  E3: V-12 可访问性 (10-12h) ←── 色盲仅 UI+地形 + 字体 4 档 ──┘
```

**总计**: 14 项 / ~84-90h (与 ROADMAP 80-88h 范围一致, 含 V-13/V-14 各 6h)

---

## 六、测试策略总览

### 6.1 测试金字塔 (v0.9.0 新增, Wave B-rev 更新)

| 层级 | 新增测试 | 覆盖项 |
|------|----------|--------|
| Unit | ~55 测试 | visual_config (≥40 项参数) + post_battle_report (BattleResult/Event/UnitBattleStats/calculate_mvp) + keybindings_overlay + accessibility (4 档字体) + palette_morandi + ThemeManager + easing 函数 + combat_popup 扩展 + morale_indicator |
| Integration | ~15 测试 | SpriteCache 预热 + 响应式布局 + 微动画集成 + MoraleSystem → MoraleIndicatorRenderer + Damage → CombatPopupManager.add_damage_number + ThemeSwitcher 确认弹窗 + KeybindingsOverlay 联动暂停 |
| E2E | ~25 测试 | 战后报告显示 + 快捷键提示 + 色盲模式切换 + 伤害飘字显示 + 士气徽章变化 + 5 个真实玩家旅程 (F2 扩展) + Morandi 主题切换 (战斗中禁用) + 小地图 legend toggle |
| Benchmark | ~5 测试 | FPS 基准 (相对基线) + 预热性能 + 响应式性能 |
| Visual Regression | 5 基线 | 主菜单 + 战斗中草地 + 战斗中城市 + 战后报告 + 小地图 (Wave B-rev: 8 → 5, SDL_VIDEODRIVER=dummy) |

**总计**: ~105 新增测试 → v0.9.0 预期 6301+105 = 6406 passed (Wave B-rev 上调: 78 → 105)

### 6.2 测试工具

- **单元/集成/e2e**: pytest (现有)
- **FPS 基准**: pytest-benchmark (V-04 Wave B-rev 新引入, 加入 pyproject.toml dev 依赖)
- **视觉回归**: Pillow ImageChops + SDL_VIDEODRIVER=dummy (Wave B-rev: 消除 OS 差异)
- **真实组件**: pygame.Surface / real GameLoop / real Damage / real MoraleSystem (符合用户测试哲学)

### 6.3 真实玩家旅程 (Wave B-rev F2 P0-2 扩展)

`tests/e2e/test_pre_release_full_journey.py` (新增) 覆盖 5-8 真实玩家旅程:

1. 新玩家首次启动 → 主菜单 → 设置 → 调整字体 → 进入战斗
2. 战斗中遭遇压制 → 士气从 RALLYED → PINNED → 查看小地图 legend → 撤退
3. 战后报告查看 → MVP 卡片 → 时间线 tab → 关闭报告
4. 切换 Morandi 主题 (主菜单) → 确认弹窗 → 重新进入战斗
5. 战斗中误按 ? → 快捷键面板弹出 + 游戏暂停 → 任意键关闭 + 游戏恢复
6. 色盲玩家开启 Deuteranopia 模式 → 验证 UI/地形色彩变化 + 单位精灵不变
7. 4K 屏幕玩家调整字号到特大 → 验证字体缩放 + 布局不重叠
8. 伤害飘字密集场景 (爆炸) → 验证 FIFO + 200ms 节流不遮挡战场

---

## 七、风险评估 (Wave B-rev 更新)

| 风险 | 严重度 | 缓解措施 |
|------|--------|----------|
| V-01 配置化迁移引入视觉差异 | 中 | **V-07 基线前移 Wave C2** (Wave B-rev) + 接口冻结检查 + 迁移前后手动截图对比 |
| V-03 BattleResult schema 强类型化破坏向后兼容 | 中 | BattleEvent/UnitBattleStats 用 @dataclass(frozen=True) + factory pattern + 字段缺失降级到 _render_report |
| V-04 FPS 基准 CI false positive (runner 差异) | 中 | 相对基线 (vs 上次 commit) + 15% 阈值容忍 (Wave B-rev) |
| V-05 响应式布局元素重叠 | 中 | 1920×1080 / 2560×1440 多分辨率测试 |
| V-07 视觉回归 false positive (OS 字体差异) | 中 | **SDL_VIDEODRIVER=dummy 统一渲染** + 3-5% 阈值 (Wave B-rev) |
| V-12 色盲模式影响战术可读性 | 中 | **色盲仅 UI+地形** (单位精灵不变) + playtest 验证 (Wave B-rev) |
| V-13 伤害飘字遮挡战场 | 低 | FIFO 10 个上限 + 200ms 节流 (Wave B-rev) |
| V-14 ROUTING 闪烁引发光敏性癫痫 | 低 | 200ms 间隔 (2.5 次/秒) 符合 WCAG 2.1 (≤3 次/秒) (Wave B-rev) |
| Wave B-rev 文档与代码一致性 | 中 | check_doc_consistency.sh 需扩展 v0.9.0 文档清单 (P0-4) |

---

**最后更新**: 2026-07-20 | **状态**: 🚧 Wave B-rev 修订完成, 待 7-Role 二次共识评估 | **下一步**: Wave B-rev 7-Role 二次共识评估
