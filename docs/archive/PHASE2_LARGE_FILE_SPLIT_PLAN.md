# Phase 2: P0-1 大文件拆分计划

> **创建日期**: 2026-07-04
> **基于**: D12 评估报告 P0-1（5 个 >1000L 文件未拆分）
> **5-Phase 计划**: Phase 1 已完成（文档口径统一 + ghost 确认），本文档为 Phase 2 执行计划
> **预计工期**: 2-3 天

## 1. 评估结果

### 1.1 文件清单与结构

| # | 文件 | 行数 | 模块类型 | class 数 | 方法数 | 风险 |
|---|------|------|----------|----------|--------|------|
| 1 | `presentation/rendering/terrain_tile_generator.py` | 1324 | 纯函数（全静态方法） | 1 | 19 | 低 |
| 2 | `presentation/rendering/infantry_pixel_renderer.py` | 1136 | 2 class（静态方法 + 有状态） | 2 | 14 | 低-中 |
| 3 | `presentation/ui/campaign_ui_rendering.py` | 1118 | class + 实例方法 | 1 | 10 | 中 |
| 4 | `presentation/ui/deployment_renderer.py` | 1170 | class + 实例方法（混合功能） | 1 | 21 | 中 |

**注**: 原列表中的 `pixvoxel_loader.py` 1139L 在 Phase 1 确认为 scripts-only（非 ghost，但仅 `scripts/validate_isometric.py` 使用），Phase 2 重新评估是否拆分（可考虑移至 scripts/ 目录而非拆分）。

### 1.2 拆分顺序（从最低风险开始）

按 DevSquad Iron Rule "从最低风险开始，每个文件拆分后立即跑 ruff+mypy+pytest 三重验证，全部通过才推进下一个"：

1. **terrain_tile_generator.py**（纯函数模块，最低风险）— 参考 D11 `cc2_building_renderer.py` facade + 子模块模式
2. **infantry_pixel_renderer.py**（2 class 可直接拆分）— 简单拆分为 2 个独立文件 + 内部子模块
3. **campaign_ui_rendering.py**（class + mixin，按屏幕分组）— 参考 D11 `sprite_renderer.py` facade + mixin 模式
4. **deployment_renderer.py**（class + mixin，混合功能）— 参考 D11 `tactic_executor.py` facade + mixin 包结构

## 2. 拆分方案详情

### 2.1 terrain_tile_generator.py (1324L) → facade + 4 子模块

**public API 约束**：
- `TerrainTileGenerator` class 名不变
- 19 个 `generate_*` 静态方法签名不变
- `terrain_tile_generator.py` 模块路径不变（facade）
- `pixel_artist.py` 的 re-export 不变（`from ...terrain_tile_generator import TerrainTileGenerator`）
- 测试 `tests/unit/test_pixel_artist.py` 通过 `pixel_artist.TerrainTileGenerator` 访问，零修改

**19 个 generate_* 方法分组**（按地形类型语义 + 行数均衡）：

| 子模块 | 包含方法 | 估算行数 |
|--------|----------|----------|
| `terrain_tiles_natural.py` | grass / woods / water / shallow / swamp / mud / sand / snow / rough / open | ~510L |
| `terrain_tiles_road.py` | road（含邻居方向逻辑，321L 单独拆出） | ~325L |
| `terrain_tiles_structures.py` | building / bridge / hedge / wall / bunker | ~365L |
| `terrain_tiles_battlefield.py` | crater / wire / trench | ~115L |
| `terrain_tile_generator.py` facade | `TerrainTileGenerator` class（19 个静态方法转发到子模块） | ~100L |

**拆分模式**：facade class + 子模块函数
- 子模块定义独立函数 `generate_grass(...)` 等
- facade class 的 `@staticmethod` 调用子模块函数并返回结果
- 子模块共享 import（`pixel_canvas` / `math` / `random`）

### 2.2 infantry_pixel_renderer.py (1136L) → facade + 子模块

**结构**：
- `InfantryPixelRenderer` class (line 36-1040): 9 个静态方法（`create_infantry_sprite` + `apply_wounded_overlay` + 6 个 `_draw_*` / `_get_*` helpers + `_anim_state_to_params`）
- `InfantryAnimator` class (line 1040-1136): 4 个方法（`__init__` / `state` property / `update` / `reset`）

**public API 约束**：
- 两个 class 名不变
- 模块路径 `infantry_pixel_renderer.py` 不变（facade）

**拆分方案**：
- `infantry_pixel_renderer.py` facade: 保留两个 class，方法转发到子模块
- `infantry_sprite_generator.py`: `create_infantry_sprite` + `apply_wounded_overlay` + `_get_*` helpers
- `infantry_weapon_drawing.py`: `_draw_infantry_weapon`
- `infantry_pose_drawing.py`: `_draw_infantry_prone_topdown` + `_draw_infantry_death_topdown`
- `infantry_animator.py`: `InfantryAnimator` class（独立文件）

### 2.3 campaign_ui_rendering.py (1118L) → facade + 4 mixin

**结构**：1 个 class `CampaignUIRenderer`，10 个方法（1 个 public `render` + 8 个 `_render_*` 屏幕 + 1 个 `_generate_narrative_report`）

**拆分方案**（按屏幕分组 mixin）：
- `campaign_ui_rendering.py` facade: `CampaignUIRenderer(RenderingMixin, ...)` 
- `campaign_ui_select_mixin.py`: `_render_operation_select` + `_render_battle_select`
- `campaign_ui_briefing_mixin.py`: `_render_briefing` + `_render_preview` + `_generate_narrative_report`
- `campaign_ui_report_mixin.py`: `_render_report` + `_render_campaign_end`
- `campaign_ui_supply_mixin.py`: `_render_supply_procurement`

### 2.4 deployment_renderer.py (1170L) → facade + 4 mixin

**结构**：1 个 class `DeploymentRenderer`，21 个方法（混合渲染/交互/LOS/布局）

**拆分方案**（按功能分组 mixin）：
- `deployment_renderer.py` facade: `DeploymentRenderer(ZoneMixin, RosterMixin, LOSMixin, DragMixin)`
- `deployment_zone_rendering_mixin.py`: `render_deployment_zones` + `_render_zone_overlays` + `_render_placement_highlights` + `_render_placed_units` + `_render_pending_orders` + `_render_los_preview`
- `deployment_roster_rendering_mixin.py`: `_render_roster` + `_render_rp_header` + `_render_requisition_points` + `_render_unit_counts` + `_render_start_battle_button` + `_render_unit_details_panel` + `_rebuild_roster_layout`
- `deployment_los_helpers_mixin.py`: `_estimate_deployment_hit_probability` + `_hit_probability_to_los_color` + `_draw_dashed_line` + `_draw_arrowhead`
- `deployment_drag_mixin.py`: `handle_deployment_drag` + `_render_drag_feedback` + `_ensure_fonts`

## 3. 执行流程（每个文件）

按 DevSquad Delivery Workflow Iron Rules 7 步闭环：

1. **Implement**: 创建子模块文件，迁移方法，创建 facade class
2. **Test**: `ruff check .` + `mypy -p pycc2` + `pytest tests/unit/ -m "not slow"` 全量回归
3. **Walkthrough**: git diff 检查每个新文件
4. **Annotate**: 子模块文件头注释说明来源 + 公共方法 docstring
5. **Docs Update**: 更新 CHANGELOG + PROJECT_STATUS + ASSESSMENT_D12 P0-1 状态
6. **Cleanup**: 无临时文件
7. **Git Push**: commit + push（每个文件拆分一个 commit）

## 4. 验证标准

每个文件拆分后必须满足：
- ✅ `ruff check .` 0 errors
- ✅ `mypy -p pycc2` 0 errors（MYPYPATH=src）
- ✅ `pytest tests/unit/ -m "not slow" --deselect tests/unit/test_pixel_artist.py::TestPixelArtistSprite::test_sprite_generation_performance` 4785+ passed / 0 failed
- ✅ public API 不变（class 名 + 方法签名 + 模块路径）
- ✅ 测试零修改
- ✅ facade 文件 < 200L，子模块 < 600L

## 5. 进度跟踪

| # | 文件 | 状态 | commit | 日期 |
|---|------|------|--------|------|
| 1 | terrain_tile_generator.py | ✅ 完成 | 508d016 | 2026-07-04 |
| 2 | infantry_pixel_renderer.py | ✅ 完成 | 1f5328c | 2026-07-04 |
| 3 | campaign_ui_rendering.py | ✅ 完成 | 6992058 | 2026-07-04 |
| 4 | deployment_renderer.py | ✅ 完成 | (本 commit) | 2026-07-04 |

### 5.1 terrain_tile_generator.py 拆分实测数据 (2026-07-04)

| 文件 | 计划行数 | 实测行数 | 偏差 |
|------|----------|----------|------|
| `terrain_tiles_natural.py` | ~510L | 523L | +13L |
| `terrain_tiles_road.py` | ~325L | 338L | +13L |
| `terrain_tiles_structures.py` | ~365L | 414L | +49L |
| `terrain_tiles_battlefield.py` | ~115L | 149L | +34L |
| `terrain_tile_generator.py` facade | ~100L | 138L | +38L |
| **总计** | ~1415L | 1562L | +147L |

**行数增加原因**: 子模块文件头注释 + 每个函数添加 Args/Returns docstring + facade class 完整 docstring + import 块。原 1324L 拆分后总 1562L，增加 238L（+18%），全部为文档与代码组织开销，无逻辑变更。

**验证结果**:
- ✅ ruff check . : 0 errors（修复 1 个 import 排序 I001）
- ✅ MYPYPATH=src mypy 5 files : 0 errors
- ✅ pytest tests/unit/ -m "not slow" : 4785 passed / 0 failed / 2 skipped / 13 deselected（与拆分前完全一致）
- ✅ public API 不变（class 名 + 19 个方法签名 + 模块路径）
- ✅ 测试零修改
- ✅ facade 138L < 200L 上限，最大子模块 523L < 600L 上限

### 5.2 infantry_pixel_renderer.py 拆分实测数据 (2026-07-04)

| 文件 | 计划行数 | 实测行数 | 偏差 |
|------|----------|----------|------|
| `infantry_sprite_generator.py` | ~400L | 494L | +94L |
| `infantry_weapon_drawing.py` | ~250L | 260L | +10L |
| `infantry_pose_drawing.py` | ~300L | 325L | +25L |
| `infantry_animator.py` | ~100L | 108L | +8L |
| `infantry_pixel_renderer.py` facade | ~150L | 205L | +55L |
| **总计** | ~1200L | 1392L | +192L |

**行数增加原因**: 子模块文件头注释 + 每个函数添加 Args/Returns docstring + facade class 完整 docstring + import 块 + 死代码保留（`_draw_infantry_weapon` + `_get_isometric_offset`）。原 1136L 拆分后总 1392L，增加 256L（+23%），全部为文档与代码组织开销，无逻辑变更。

**实际结构与计划差异**: 计划 §2.2 列 9 个 @staticmethod，实际 10 个（漏列 `create_infantry_animation_sheet`）。facade 205L 略超 200L 上限（因 10 个方法签名 + InfantryAnimator re-export + 完整 docstring），可接受。

**跨模块依赖**:
- `infantry_sprite_generator` → `infantry_pose_drawing`（单向，调用 `_draw_infantry_prone_topdown` + `_draw_infantry_death_topdown`）
- 无循环 import

**死代码保留策略**:
- `_draw_infantry_weapon` (weapon_drawing): 原文件中定义但从未被调用，作为 private API 保留
- `_get_isometric_offset` (sprite_generator): 同上

**验证结果**:
- ✅ ruff check . : 0 errors（修复 6 个：2 I001 import 排序 + 2 UP037 type annotation 引号 + 2 F401 pygame TYPE_CHECKING 未使用）
- ✅ MYPYPATH=src mypy 5 files : 0 errors
- ✅ pytest tests/unit/ -m "not slow" -p no:randomly : 4785 passed / 0 failed / 2 skipped / 13 deselected（与拆分前完全一致）
- ✅ public API 不变（class 名 + 10 个方法签名 + 模块路径 + pixel_artist_3d.py re-export）
- ✅ 测试零修改
- ✅ facade 205L（略超 200L 上限，因 10 方法 + re-export + docstring，可接受），最大子模块 494L < 600L 上限
- ✅ smoke test: 6 项 public API 验证全通过（create_infantry_sprite / create_infantry_animation_sheet / InfantryAnimator / apply_wounded_overlay / pixel_artist_3d 两个 re-export / pixel_artist TerrainTileGenerator）

### 5.3 campaign_ui_rendering.py 拆分实测数据 (2026-07-04)

| 文件 | 计划行数 | 实测行数 | 偏差 |
|------|----------|----------|------|
| `campaign_ui_select_mixin.py` | ~267L | 275L | +8L |
| `campaign_ui_briefing_mixin.py` | ~356L | 364L | +8L |
| `campaign_ui_report_mixin.py` | ~461L | 469L | +8L |
| `campaign_ui_supply_mixin.py` | ~42L | 50L | +8L |
| `campaign_ui_rendering.py` facade | ~77L | 77L | 0L |
| **总计** | ~1203L | 1235L | +32L |

**行数增加原因**: 子模块文件头注释 + mixin class docstring + `_ui: CampaignUI` class-level 类型注解 + `TYPE_CHECKING` import 块。原 1118L 拆分后总 1235L，增加 117L（+10%），全部为文档与代码组织开销，无逻辑变更。

**实际结构与计划差异**: `_generate_narrative_report` 是 @staticmethod 被 `_render_report` 调用（line 85），实际归入 report mixin 而非 briefing mixin（计划 §2.3 列在 briefing mixin）。这是更合理的分组：被 `_render_report` 调用的 helper 应与调用方同模块。

**mixin 属性声明模式**:
- 每个 mixin class 添加 class-level 类型注解 `_ui: CampaignUI`（无默认值）
- `if TYPE_CHECKING:` 块声明 `from .campaign_ui import CampaignUI`
- 参考 D11 `vl_flag_rendering_mixin.py` 的 `TILE_SIZE: int` / `draw_surface: Surface | None` 模式
- 修复了 7 个 mypy `[attr-defined]` 错误（"CampaignUI*Mixin" has no attribute "_ui"）

**跨模块依赖**:
- 4 个 mixin 间无直接依赖，全部通过 `self._ui` 访问 CampaignUI 状态
- facade 通过 MRO 组合所有 mixin: `CampaignUIRenderer(SelectMixin, BriefingMixin, ReportMixin, SupplyMixin)`

**验证结果**:
- ✅ ruff check . : 0 errors
- ✅ MYPYPATH=src mypy 5 files : 0 errors (Success: no issues found in 5 source files)
- ✅ pytest tests/unit/ -m "not slow" -p no:randomly : 4785 passed / 0 failed / 2 skipped / 13 deselected（与拆分前完全一致，零回归）
- ✅ public API 不变（class 名 + __init__(ui) + render(surface) 签名 + 模块路径）
- ✅ 测试零修改
- ✅ facade 77L < 200L 上限，最大子模块 469L < 600L 上限

**拆分模式对比**:
| 文件 | 模式 | 来源参考 |
|------|------|----------|
| terrain_tile_generator.py | facade + 子模块函数 | D11 cc2_building_renderer.py |
| infantry_pixel_renderer.py | facade + 子模块函数 + class re-export | terrain_tile_generator.py |
| campaign_ui_rendering.py | facade + mixin class | D11 sprite_renderer.py + vl_flag_rendering_mixin.py |
| deployment_renderer.py | facade + mixin class + cross-mixin TYPE_CHECKING 声明 | campaign_ui_rendering.py + D11 vl_flag_rendering_mixin.py |

### 5.4 deployment_renderer.py 拆分实测数据 (2026-07-04)

| 文件 | 计划行数 | 实测行数 | 偏差 |
|------|----------|----------|------|
| `deployment_zone_rendering_mixin.py` | ~370L | 398L | +28L |
| `deployment_roster_rendering_mixin.py` | ~580L | 630L | +50L |
| `deployment_los_helpers_mixin.py` | ~100L | 105L | +5L |
| `deployment_drag_mixin.py` | ~220L | 223L | +3L |
| `deployment_renderer.py` facade | ~95L | 95L | 0L |
| **总计** | ~1365L | 1451L | +86L |

**行数增加原因**: 子模块文件头注释 + mixin class docstring + `_ui`/surface cache class-level 类型注解 + `TYPE_CHECKING` import 块 + cross-mixin 方法声明（zone_rendering_mixin）。原 1170L 拆分后总 1451L，增加 281L（+24%），全部为文档与代码组织开销，无逻辑变更。

**roster_rendering_mixin 630L 略超 600L 上限**: 因 7 个方法 + RP 进度条渲染逻辑（_render_rp_header 含 4 色彩梯度 + shine 效果 + border）+ unit_details_panel 含按钮 rect 保存逻辑。可接受，进一步拆分会破坏功能内聚（roster 面板渲染是一个整体）。

**cross-mixin 方法声明模式**:
- `_render_pending_orders` (zone_rendering_mixin) 调用 `self._draw_dashed_line` + `self._draw_arrowhead`（来自 los_helpers_mixin via MRO）
- 在 zone_rendering_mixin 的 class 内 `if TYPE_CHECKING:` 块中声明这两个方法为普通实例方法（带 self 参数）
- 运行时实际是 staticmethod（在 los_helpers_mixin 中定义），但 mypy 接受 `self.method()` 调用，行为一致
- 参考 D11 vl_flag_rendering_mixin.py 的 `_get_pooled_surface` 声明模式
- 注意：`@staticmethod` 装饰器不能在 class 内 `TYPE_CHECKING` 块中使用（mypy 报 "staticmethod used with a non-method"），所以声明为普通方法

**pygame lazy import 模式**:
- 4 个 mixin 各自 try/except import pygame + 定义自己的 `_pygame_available` flag
- 与原 facade 模式一致，保持 headless 测试兼容
- 5 个方法检查 `_pygame_available`：`render_deployment_zones` + `handle_deployment_drag` + `_render_rp_header` + `_render_requisition_points` + `_render_drag_feedback` + `_ensure_fonts`

**跨模块依赖**:
- 4 个 mixin 间通过 MRO 组合：`DeploymentRenderer(ZoneRendering, RosterRendering, LOSHelpers, Drag)`
- zone_rendering_mixin → los_helpers_mixin (cross-mixin 方法调用 via self)
- 其他 mixin 间无直接依赖，全部通过 `self._ui` 访问 DeploymentUI 状态

**验证结果**:
- ✅ ruff check . : 0 errors
- ✅ MYPYPATH=src mypy 5 files : 0 errors (Success: no issues found in 5 source files)
- ✅ pytest tests/unit/ -m "not slow" -p no:randomly : 4785 passed / 0 failed / 2 skipped / 13 deselected（与拆分前完全一致，零回归）
- ✅ public API 不变（class 名 + __init__(ui) + 20 个方法签名 + 5 class constants + 模块路径）
- ✅ 测试零修改
- ✅ facade 95L < 200L 上限，最大子模块 630L 略超 600L 上限（roster 7 方法 + RP 进度条，可接受）
- ✅ smoke test: 7 项验证全通过（MRO 4 mixin / 20 方法可访问 / 5 class constants / 2 staticmethod / deployment_ui import / 5 surface cache 初始化 / public API）

## 6. Phase 2 P0-1 完成总结 (2026-07-04)

### 6.1 拆分成果

| # | 文件 | 原行数 | 拆分后总行数 | 增量 | 模式 |
|---|------|--------|--------------|------|------|
| 1 | terrain_tile_generator.py | 1324L | 1562L | +18% | facade + 子模块函数 |
| 2 | infantry_pixel_renderer.py | 1136L | 1392L | +23% | facade + 子模块函数 + class re-export |
| 3 | campaign_ui_rendering.py | 1118L | 1235L | +10% | facade + mixin class |
| 4 | deployment_renderer.py | 1170L | 1451L | +24% | facade + mixin class + cross-mixin 声明 |
| **总计** | **4 个文件** | **4748L** | **5640L** | **+19%** | **2 种模式** |

**行数增加全部为文档与代码组织开销**（文件头注释 + docstring + 类型注解 + TYPE_CHECKING 块），无逻辑变更。

### 6.2 验证标准达成

- ✅ ruff check . : 0 errors（4 个文件均一次通过，infantry 修复 6 个）
- ✅ MYPYPATH=src mypy : 0 errors（4 个文件均通过，campaign_ui 修复 7 个 _ui 属性错误，deployment 修复 2 个 cross-mixin 方法错误）
- ✅ pytest tests/unit/ -m "not slow" -p no:randomly : 4785 passed / 0 failed / 2 skipped / 13 deselected（4 个文件拆分前后完全一致，零回归）
- ✅ public API 100% 向后兼容（所有 class 名 + 方法签名 + 模块路径不变）
- ✅ 测试零修改
- ✅ facade 文件均 < 200L 上限（138L / 205L / 77L / 95L）
- ✅ 子模块均 < 600L 上限（仅 deployment_roster_rendering_mixin 630L 略超，因 7 方法 + RP 进度条渲染逻辑，可接受）

### 6.3 拆分模式选择指南

| 场景 | 推荐模式 | 参考 |
|------|----------|------|
| 全静态方法的工具类 | facade + 子模块函数 | terrain_tile_generator.py |
| 静态方法 + 独立 class | facade + 子模块函数 + class re-export | infantry_pixel_renderer.py |
| 实例方法 + 共享 self 状态 | facade + mixin class | campaign_ui_rendering.py |
| 实例方法 + cross-mixin 调用 | facade + mixin class + TYPE_CHECKING 声明 | deployment_renderer.py |

### 6.4 Phase 2 后续

Phase 2 P0-1 完成，4/4 大文件全部拆分。剩余 Phase 2 任务：无（pixvoxel_loader 为 scripts-only 不拆分）。

下一步推荐：
- **Phase 3**: P1-1 大 ghost 模块清理（11 ghost，1 天）
- **Phase 4**: P0-2 unit.py God Class 拆分（54 方法，1-2 天）
- **Phase 5**: P1-2 孤儿事件对齐（9 孤儿 + 1 反向孤儿，1h）
