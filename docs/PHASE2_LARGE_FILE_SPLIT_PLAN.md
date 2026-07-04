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
| 1 | terrain_tile_generator.py | ✅ 完成 | (本 commit) | 2026-07-04 |
| 2 | infantry_pixel_renderer.py | 待启动 | - | - |
| 3 | campaign_ui_rendering.py | 待启动 | - | - |
| 4 | deployment_renderer.py | 待启动 | - | - |

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
