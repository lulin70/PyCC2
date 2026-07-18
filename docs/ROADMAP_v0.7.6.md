# ROADMAP v0.7.6 — INTEGRATE TD-077 剩余 6 个 ORPHAN 模块 (PATCH)

**Status**: ✅ 完成 (2026-07-18)
**Created**: 2026-07-18
**Version**: 0.7.6 (PATCH — 完整接入 6 个 ORPHAN 模块，SemVer 偏离理由见 §1.3)
**Prev**: v0.7.5 INTEGRATE psychology_system + squad_group_manager (27 集成测试)
**Result**: 6311 collected / 6291 passed / 2 skipped / 18 deselected (59.16s); 75 新增集成测试 (18 path_preview+range_indicator + 9 cover_seek + 34 day_night_cycle + 14 variant_generators); 503 E2E 全绿; ruff 0 errors; 详见 CHANGELOG.md

---

## 1. 背景与决策

### 1.1 v0.7.5 完成 + v0.7.6 范围

v0.7.5 完成了 psychology_system + squad_group_manager 接入（27 集成测试，6216 passed）。TD-077 在 v0.7.1 标记了 8 个 ORPHAN 模块，v0.7.5 已接入 2 个，**剩余 6 个**待 v0.7.6 接入。

### 1.2 接入范围（用户决策：全接 6 个）

| # | 模块 | 行数 | 层 | 功能 | 风险 | Wave |
|---|------|------|-----|------|------|------|
| 1 | `path_preview.py` | 309 | presentation/rendering | 移动路径预览+危险评估 | LOW | Wave 1 |
| 2 | `range_indicator.py` | 192 | presentation/rendering | 武器射程圈显示 | LOW | Wave 1 |
| 3 | `cover_seek_ai.py` | 540 | domain/ai | 被压制时自动找掩体 | LOW | Wave 2 |
| 4 | `day_night_cycle.py` | 214 | domain/systems | 日夜循环（v0.7.3 已修接口） | MEDIUM | Wave 3 |
| 5 | `vehicle_variant_generator.py` | 388 | domain/systems | Sherman/Panzer 等车辆变体 | MEDIUM | Wave 4 |
| 6 | `faction_variant_generator.py` | 366 | domain/systems | Commando/Ranger 等阵营单位 | MEDIUM | Wave 4 |

**总工作量**: ~13-17h（用户决策全接，分 4 个 Wave 增量推进）

### 1.3 版本号决策 (SemVer 偏离说明)

**用户决策**: v0.7.6 (PATCH 完整接入)

**SemVer 偏离理由**:
- 6 个模块的功能逻辑均已实现（每个都有对应单元测试保障）
- v0.7.6 只是"接线"让模块接入游戏循环，不新增功能逻辑
- 接入后用户可使用路径预览/射程圈/掩体 AI/日夜循环/更多单位变体，从用户视角是"功能新增"
- 但从代码视角，只是"调用已有代码"，非"编写新功能"
- **7-Role 共识**: 尊重用户决策，定位为 PATCH，在 CHANGELOG 中诚实记录 SemVer 偏离

---

## 2. DevSquad 7-Role 共识评估

| Role | Vote | Rationale |
|------|------|-----------|
| **Architect** | ✅ 支持 | 6 个模块接入点清晰，分 4 Wave 增量推进风险可控；path_preview/range_indicator 接入 InputRouter/Minimap 符合现有渲染管线；cover_seek_ai 接入 TacticalOrchestrator Phase 6 与 Phase 5 Psychology 协同；day_night_cycle 接入 GameLoop 符合 facade 模式；2 个生成器接入 unit_template_registry 符合现有数据加载流程 |
| **PM** | ✅ 支持 | 6 个 ORPHAN 模块接入让 TD-077 彻底清零，是 CC2 战术体验完整性的关键提升；路径预览+射程圈是 RTS 标配；掩体 AI + 日夜循环 + 更多单位变体显著提升真实感和多样性；v0.7.6 PATCH 定位符合用户"功能逻辑已实现只是接线"的认知 |
| **Security** | ✅ 支持 | 无外部输入新增；6 个模块均无持久化无网络调用；path_preview/range_indicator 纯渲染无副作用；cover_seek_ai 输出 TacticIntent 与现有 AI 模式一致；day_night_cycle 状态变更通过 GameTime.advance() 受控；2 个生成器仅生成模板数据无运行时风险 |
| **Tester** | ✅ 支持 | 6 个模块均有对应单元测试保障业务逻辑；v0.7.6 需为每个 Wave 补充集成测试验证接入行为：Wave 1 渲染集成测试、Wave 2 AI 决策集成测试、Wave 3 时间推进+视觉同步集成测试、Wave 4 模板注册集成测试；总目标 ≥24 新集成测试 |
| **Coder** | ✅ 支持 | 6 个模块接入遵循 v0.7.5 经验：先确认接口契约、再添加字段/方法、最后同步 Protocol；Wave 1 渲染类接入 minimap/hud 现有模式；Wave 2 cover_seek_ai 与 Phase 5 Psychology 自然衔接；Wave 3 day_night_cycle 已在 v0.7.3 修好接口只需装配；Wave 4 生成器接入 unit_template_registry 现有流程 |
| **DevOps** | ✅ 支持 | 无新依赖；版本号 0.7.5→0.7.6 全量同步 18 文件；check_doc_consistency.sh 11/11 PASS；CI 无新增步骤；分 Wave 推进每步可验证 |
| **UI** | ✅ 支持 | path_preview 绿/黄/红色分段路径是 CC2 标志性视觉；range_indicator 内黄外红射程圈提升战术可读性；day_night_cycle 颜色分级增强氛围；2 个生成器新增单位变体提升视觉多样性；接入遵循现有 FadeTransition/Minimap 渲染管线 |

**共识结果**: 7/7 ✅ 一致通过 — v0.7.6 定位为 PATCH 完整接入 6 个 ORPHAN 模块（SemVer 偏离已记录）

---

## 3. 接入设计

### 3.1 Wave 1: path_preview + range_indicator (低风险渲染类)

**path_preview.py 接入**:
- 接入点: `input_router.py` 鼠标右键拖拽预览 + `minimap.py` 或 `ui_overlay_renderer.py` 渲染
- 添加 `_path_preview: PathPreview | None` 字段到 InputRouter
- 右键按下时调用 `path_preview.calculate_path(unit, target, game_map, los_system)`
- 渲染层调用 `path_preview.render(camera, surface)` 绘制虚线路径

**range_indicator.py 接入**:
- 接入点: `minimap.py` 或 `ui_overlay_renderer.py` 选中单位变化时更新
- 添加 `_range_indicator: RangeIndicator | None` 字段
- selected_unit_ids 变化时调用 `range_indicator.set_unit(unit)`
- 渲染层调用 `range_indicator.render(camera, surface)` 绘制射程圈

### 3.2 Wave 2: cover_seek_ai (AI 类)

**接入点**: `tactical_orchestrator.py` `tick()` Phase 6 新增（Phase 5 Psychology 之后）

```python
# Phase 6: Cover seeking — units under heavy suppression auto-seek cover
from pycc2.domain.ai.cover_seek_ai import CoverSeekAI

cover_ai = CoverSeekAI(los_system=self.los_system, game_map=context.game_map)
for unit in context.friendly_units:
    if CoverSeekAI.should_seek_cover(unit):
        cover_intent = cover_ai.evaluate(context)
        if cover_intent:
            final.append(cover_intent)
```

### 3.3 Wave 3: day_night_cycle (系统类)

**接入点**: `game_loop.py` 添加 `_game_time: GameTime | None` 字段 + `game_loop_assembler.py` 装配

- GameLoop.tick() 调用 `game_time.advance(dt)`
- 渲染层根据 `game_time.time_phase` 调整颜色分级（DAWN/DAY/DUSK/NIGHT）
- shadow_system 根据 `game_time.time_of_day` (float 0.0-24.0) 计算阴影角度
- audio_system 根据 `int(game_time.time_of_day) % 24` 切换环境音

### 3.4 Wave 4: vehicle_variant_generator + faction_variant_generator (生成器类)

**接入点**: `unit_template_registry` 单位模板注册流程

- 在数据加载阶段调用 `VehicleVariantGenerator().generate()` 和 `FactionVariantGenerator().generate()`
- 将生成的 `CC2UnitTemplate` 列表注册到 registry
- 验证 deployment 阶段能选择新单位

---

## 4. 执行清单 (7 Waves)

### Wave 0: 文档先行 + 7-Role 共识 — ✅ 完成

- [x] 创建 `docs/ROADMAP_v0.7.6.md`
- [x] 7-Role 共识评估 (7/7 一致通过)

### Wave 1: path_preview + range_indicator (Coder) — ✅ 完成

**风险等级**: LOW（纯渲染，additive）

- [ ] `input_router.py` 添加 `_path_preview` 字段 + 右键拖拽预览逻辑
- [ ] `minimap.py` 或 `ui_overlay_renderer.py` 添加路径渲染调用
- [ ] `minimap.py` 添加 `_range_indicator` 字段 + 选中单位变化时更新
- [ ] 渲染层添加射程圈绘制
- [ ] 补充集成测试 `tests/integration/test_path_preview_integration.py` (≥6 tests)
- [ ] 补充集成测试 `tests/integration/test_range_indicator_integration.py` (≥6 tests)
- [ ] 验证 STATUS 标记从 ORPHAN 改为 INTEGRATED v0.7.6

### Wave 2: cover_seek_ai (Coder) — ✅ 完成

**风险等级**: LOW（additive AI，与 Phase 5 协同）

- [ ] `tactical_orchestrator.py` `tick()` Phase 5 后新增 Phase 6: Cover Seek
- [ ] 验证 `CoverSeekAI.should_seek_cover(unit)` + `evaluate(context)` 接口
- [ ] 补充集成测试 `tests/integration/test_cover_seek_integration.py` (≥6 tests)
- [ ] 验证 STATUS 标记从 ORPHAN 改为 INTEGRATED v0.7.6

### Wave 3: day_night_cycle (Coder) — ✅ 完成

**风险等级**: MEDIUM（涉及渲染+音频+阴影+隐蔽）

- [ ] `game_loop.py` 添加 `_game_time: GameTime | None` 字段
- [ ] `game_loop_assembler.py` 添加 `_init_day_night_cycle()` 装配方法
- [ ] `game_loop_updating.py` 添加 `game_time.advance(dt)` 调用
- [ ] 渲染层根据 `time_phase` 调整颜色分级
- [ ] `shadow_system` 根据 `time_of_day` (float) 计算阴影
- [ ] `audio_system` 根据 `int(time_of_day) % 24` 切换环境音
- [ ] 补充集成测试 `tests/integration/test_day_night_cycle_integration.py` (≥8 tests)
- [ ] 验证 STATUS 标记从 ORPHAN 改为 INTEGRATED v0.7.6

### Wave 4: vehicle_variant_generator + faction_variant_generator (Coder) — ✅ 完成

**风险等级**: MEDIUM（涉及数据加载+单位模板系统）

- [ ] 找到 `unit_template_registry` 或数据加载入口
- [ ] 调用 `VehicleVariantGenerator().generate()` 注册车辆变体
- [ ] 调用 `FactionVariantGenerator().generate()` 注册阵营变体
- [ ] 验证 deployment 阶段能选择新单位
- [ ] 补充集成测试 `tests/integration/test_variant_generators_integration.py` (≥6 tests)
- [ ] 验证 STATUS 标记从 ORPHAN 改为 INTEGRATED v0.7.6

### Wave 5: 版本号 0.7.5→0.7.6 + 文档同步 (DevOps) — ✅ 完成

- [ ] `VERSION` / `__init__.py` / `pyproject.toml` / `SKILL.md`
- [ ] `docs/PRD.md` / `docs/TEST_PLAN.md` / `docs/TECH_DEBT.md` / `docs/PROJECT_STATUS.md`
- [ ] `README.md` / `README_zh.md` / `README_ja.md`
- [ ] `docs/DESIGN.md` / `docs/ROADMAP.md`
- [ ] `check_doc_consistency.sh` 11/11 PASS

### Wave 6: 全量验证 + Git 推送 (Tester/DevOps) — ✅ 完成

- [ ] `pytest tests/ -m "not slow"` — 期望 6216+新增集成测试 passed
- [ ] `ruff check .` — 期望 0 errors
- [ ] `MYPYPATH=src mypy -p pycc2` — 期望 0 errors (374+ files)
- [ ] `bash scripts/check_doc_consistency.sh` — 期望 11/11 PASS
- [ ] 新增集成测试全部通过 (≥26 tests)
- [ ] `CHANGELOG.md` 插入 v0.7.6 完整条目
- [ ] `docs/ROADMAP_v0.7.6.md` 状态更新为 ✅ 完成
- [ ] Git commit + push origin/main
- [ ] CarryMem `classify_and_remember` 记录会话总结

---

## 5. 风险与缓解

| 风险 | 等级 | 缓解 |
|------|------|------|
| path_preview 路径计算性能 | LOW | A* 已有优化；仅右键拖拽时触发，不持续计算 |
| range_indicator 字体/颜色与现有 HUD 冲突 | LOW | 使用 CC2 标准色板；半透明渲染不遮挡 |
| cover_seek_ai 与 Phase 5 Psychology 冲突 | LOW | Phase 5 过滤被拒命令，Phase 6 添加掩体命令，互补不冲突 |
| day_night_cycle 渲染颜色分级性能 | MEDIUM | 静态层缓存；time_phase 变化时才重新计算 |
| day_night_cycle 阴影系统兼容性 | MEDIUM | v0.7.3 已修接口 (time_of_day float)；需验证 shadow_system 接受 0.0-24.0 |
| 生成器注册后单位模板 ID 冲突 | MEDIUM | 验证所有 template_id 唯一；冲突时跳过并记日志 |
| 接入后测试数变化导致文档不一致 | LOW | Wave 5 同步测试数；Wave 6 验证 |

---

## 6. DevSquad 11-Phase 生命周期映射

| Phase | 状态 | 产出 |
|-------|------|------|
| 1. Intent | ✅ | 用户要求 INTEGRATE TD-077 剩余 6 个 ORPHAN 模块 |
| 2. Spec | ✅ | 本文档 §3 接入设计 |
| 3. Plan | ✅ | 本文档 §4 执行清单 (7 Waves) |
| 4. Consensus | ✅ | 7/7 一致通过 (§2) |
| 5. Design | ✅ | 本文档 §3 + 6 个模块 docstring |
| 6. Implement | ✅ | Wave 1-4 (75 集成测试) |
| 7. Test | ✅ | Wave 6 验证 (6291 passed) |
| 8. Review | ✅ | Wave 6 验证 (ruff 0) |
| 9. Document | ✅ | Wave 5 + Wave 6 (18 文档同步) |
| 10. Deploy | ✅ | Wave 6 Git push |
| 11. Learn | ✅ | Wave 6 CarryMem 记录 |
