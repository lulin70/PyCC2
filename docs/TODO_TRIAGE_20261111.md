# 渲染层 TODO 判定（修 / 删 / 留）

- 日期：2026-11-11
- 判定方式：DevSquad Coder + Architect 双角色走读，逐条附证据
- 范围：`src/pycc2` 全量 `grep -rn "TODO\|FIXME" --include="*.py"`

## 0. 数量勘误

评审报告（`PROJECT_REVIEW_20261111.md` 维度 1/3）记载「TODO/FIXME 46 处」为**误计**。实测：

| 口径 | 数量 | 命令 |
|------|------|------|
| 活跃代码（不含 `_archive`） | **4** | `grep -rn "TODO\|FIXME" src --include="*.py" \| grep -v _archive` |
| 含 `_archive` | 4（归档内 0 处） | `grep -rn "TODO\|FIXME" src --include="*.py"` |

4 处全部落在评审点名的 3 个渲染文件（enhanced_renderer / hud_renderer / minimap_renderer），分布与评审描述一致，仅数量有误。

## 1. 逐条判定

### T1 + T2 — [enhanced_renderer.py L471-472](../src/pycc2/presentation/rendering/enhanced_renderer.py#L471-L472) → **留**

```python
current_turn = 0  # TODO: 从GameState获取
game_paused = False  # TODO: 从GameState获取
```

- 现状：HUD 状态栏的回合数恒显 `Turn: 0`，暂停状态恒为 `False`。
- 证据：`RendererStateManager`（renderer_state_manager.py）只管 display/surface/cache/FPS，**不持有**回合数与暂停状态；`EnhancedRenderer.render()` 签名也不接收 GameState。
- 判定理由：修复需沿「game loop → renderer」调用链改签名传递 GameState（跨层接口变更），不是一行修。属于真实功能缺口（状态栏回合数失真），应登记 TECH_DEBT 走 P3 技术设计，不在注释里空转。
- 去向：登记 `docs/TECH_DEBT.md`（TD 条目：HUD 回合数/暂停状态接线）。

### T3 — [hud_renderer.py L229](../src/pycc2/presentation/rendering/hud_renderer.py#L229) → **删**（死代码）

- 现状：`_render_minimap` 整个方法是「Minimap」文字占位符 + TODO。
- 证据：全仓检索 `_render_minimap` 仅命中定义行（L203），**无任何调用点**。活跃渲染路径在 [hud_renderer.py L103-105](../src/pycc2/presentation/rendering/hud_renderer.py#L103-L105)，已委托给 `MinimapRenderer.render()`（真实地形+单位小地图，含点击跳转）。
- 判定理由：功能已被 MinimapRenderer 实现，占位方法是幽灵代码。删除后行为零变化（无调用点、无测试引用）。
- 去向：下一轮代码清理删除整个 `_render_minimap` 方法（约 40 行）。

### T4 — [minimap_renderer.py L349](../src/pycc2/presentation/rendering/minimap_renderer.py#L349) → **修**（下轮，一行）

```python
tile_size = 48  # TODO: 从VisualConfig获取
```

- 现状：点击换算硬编码 48 px/格。
- 证据：权威常量已存在——[enhanced_renderer.py L106](../src/pycc2/presentation/rendering/enhanced_renderer.py#L106) `TILE_SIZE = DEFAULT_VISUAL_CONFIG.dimensions.TILE_SIZE`。硬编码与常量当前数值一致（48），无行为缺陷，但 VisualConfig 若调整会静默漂移。
- 判定理由：TODO 描述即修复方案（改用 `DEFAULT_VISUAL_CONFIG.dimensions.TILE_SIZE`），一行改动 + 现有小地图点击测试即可覆盖。
- 去向：下一轮清理顺手修。

## 2. 汇总

| 编号 | 位置 | 判定 | 理由 | 状态 |
|------|------|------|------|------|
| T1/T2 | enhanced_renderer.py:471-472 | 留→修 | 跨层签名变更，需设计 | ✅ 已修复（2026-11-12，TD-079 关闭：`paused`/`tick` 经 RenderPipeline 透传，回合换算与 hud_manager 一致；回归 7552 passed） |
| T3 | hud_renderer.py:203-239 | 删 | 死代码，无调用点 | ✅ 已删除（同日清理，连带清理仅该方法使用的 `Camera` 导入；回归 7549 passed 保持不变） |
| T4 | minimap_renderer.py:349 | 修 | 一行接权威常量 | ✅ 已修复（改用 `DEFAULT_VISUAL_CONFIG.dimensions.TILE_SIZE`，与 enhanced_renderer V-01 热加载口径一致） |

清空后活跃代码 TODO 归零（T1/T2 转为 TECH_DEBT 条目跟踪）。

## 3. 真实用户验收补充（2026-11-13）

真实窗口 UAT 证明：T1/T2 的 `EnhancedRenderer` 顶部条带不在当前生产渲染路径，仅完成跨层接线不足以让用户看到回合数。已在生产实际使用的 `RenderPipeline` fallback 状态行补充 `Turn`，并修复同一流程发现的 ESC 无法恢复、暂停菜单打开时逻辑仍推进两项缺陷。`scripts/uat_hud_state.py` 验收 PASS，截图存于 `docs/assets/uat_hud_state/`，全量回归 7552 passed / 4 skipped。
