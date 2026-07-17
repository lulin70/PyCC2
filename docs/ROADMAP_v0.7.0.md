# PyCC2 v0.7.0 推进计划 — 3 点 Next-Step Plan

> **版本**: v0.6.11 → v0.7.0 (✅ 已发布) | **日期**: 2026-07-17 | **状态**: ✅ 全部完成 — Wave 1/2/3 + TD-078 同步推进
> **来源**: DevSquad 7-Role 共识评估 (2026-07-17) + 7-Role 实施评估 (2026-07-17 session 2) + 7-Role 实施完成 (2026-07-17 session 3)
> **原则**: 文档先行，活文档时刻更新；P1 按项目生命周期推进，P2/P3 给方案待用户决策

## ✅ 执行进度 (2026-07-17 session 3 — 全部完成)

| Wave | 任务 | 状态 | 接入点 | 测试 |
|------|------|------|--------|------|
| Wave 1 | TD-076c weapon_jam 接入 | ✅ 完成 | `ai_service.py:tick()` 循环内调用 `WeaponJamSystem.tick(unit)` + `__init__` 实例化 + `weapon_jam_system` property | 3 E2E + off-by-one bug 修复 |
| Wave 2 | TD-076b surrender_system 接入 | ✅ 完成 | `ai_service.py:__init__()` 注册 `SurrenderAI()` 到 TacticalOrchestrator (第 11 个 AI) + `surrender_system` property | 3 E2E + 1 测试同步 (10→11 AIs) |
| Wave 3 | TD-076d campaign_persistence 接入 | ✅ 完成 | `game_loop.py` 新增 `_campaign_persistence` 字段 + property + save/load 方法; `game_loop_assembler.py` 接线 | 6 E2E (save/load roundtrip + 继承 + GameLoop wiring) |
| TD-078 | deployment_manager 架构修复 | ✅ 完成 | 3 纯函数迁移到 `services/deployment_factory.py` + 4 domain 类型迁移到 `domain/value_objects/deployment_types.py` + 旧文件删除 | 8 架构守卫 + 200 deployment 测试全绿 |

### 验证结果 (2026-07-17 session 3)

- **全量测试**: 6509 passed / 2 skipped / 16 deselected (98.64s) — 零回归
- **E2E 真实用户模拟测试**: 12 新增 (`tests/e2e/test_v0_7_0_ghost_integration_e2e.py`) + 2 测试同步更新
- **ruff**: 0 errors (check + format)
- **mypy**: 2 pre-existing errors (`config.rendering_features`, v0.6.11 commit 中就存在, 与 v0.7.0 无关)
- **check_doc_consistency.sh**: 11/11 PASS (VERSION=0.7.0)
- **架构守卫**: 8 tests passed (services 层不再 module-level import presentation)

### 实施前评估关键发现 (2026-07-17 session 2)

1. **3 个 ghost 模块代码完整存在**（非 PLANNED 占位符）：
   - `src/pycc2/domain/ai/weapon_jam.py` (252L) — `WeaponJamSystem` 类，`check_jam_on_fire(unit)` + `tick(unit)` 完整实现
   - `src/pycc2/domain/ai/surrender_system.py` (403L) — `SurrenderSystem` + `SurrenderAI` 类，`SurrenderAI` 已实现 `TacticalAIBase` 接口可直接注册
   - `src/pycc2/domain/systems/campaign_persistence.py` (373L) — `CampaignPersistenceManager` 类，save/load/apply_inheritance_to_units 完整实现
2. **3 个模块均无任何测试文件** — 必须新增 unit + integration + E2E 测试
3. **TD-078 违规精确位置**: `deployment_manager.py:L157-L161` 运行时 import `presentation.ui.deployment_factory`，影响 11 个文件
4. **TD-078 修复方案**: 将 `deployment_factory.py` + `deployment_models.py` 一起迁移到 `services/deployment/` 目录（DeploymentUnit 本质是业务数据，不是纯 UI 概念）
5. **版本号决策**: v0.6.11 → v0.7.0 (MINOR 递增，3 个新功能接入；TD-078 架构修复合并不单独触发版本变更，遵循"功能没有更新时版本不变前两位"原则)

---

## 📋 执行摘要

v0.6.11 已完成 4 个 ghost 模块清理 (TD-073/074/075/076a)，恢复就绪度 ~80% → ~85%。v0.7.0 聚焦 3 点下一步推进，按优先级分波次推进：

| # | 推进点 | 优先级 | 类型 | 工作量 | 风险 |
|---|--------|--------|------|--------|------|
| 1 | TD-076b/c/d 三个半集成模块接入 | P1 | 代码实施 | ~12h | 中 |
| 2 | TD-077 19 个孤立原型决策 | P2 | 决策方案 | ~2h (决策) / ~6-8h (执行) | 低 |
| 3 | E2E 真实用户模拟测试 (用户规则3) | P0 | 验证执行 | ~1h | 低 |

**核心原则**：
1. **文档先行**：本计划文档先于代码变更；每个 TD 完成后同步更新 TECH_DEBT.md
2. **充分验证**：每个 TD 完成后运行全量测试 + E2E 真实用户测试
3. **外科手术式变更**：精准接入，不触碰无关代码
4. **活文档原则**：文档与代码同步演进，绝不滞后

---

## 🎯 Point 1: TD-076b/c/d 三个半集成模块接入 (P1)

### 1.1 7-Role 共识结论

**Architect + Coder 视角** (基于 subagent 评估)：

| 模块 | 行数 | 接入点 | 工作量 | 风险 | CC2 符合度 | PRD 更新 |
|------|------|--------|--------|------|-----------|---------|
| TD-076b surrender_system | 403 | `ai_service.py` 注册 SurrenderAI | 中 (~3h) | 低 | HIGH (CC2 原版有投降) | 是 |
| TD-076c weapon_jam | 252 | `ai_service.py.tick()` 调用 WeaponJamSystem.tick() | 低 (~2h) | 低 | HIGH (CC2 原版有卡弹) | 是 |
| TD-076d campaign_persistence | 373 | `game_loop_assembler.py` battle 结束时 save/load | 中高 (~5h) | 中 | HIGH (CC2 原版有战役持久化) | 是 |

**PM 视角**：
- **版本号**: 0.6.11 → 0.7.0 (MINOR，3 个新功能：投降/卡弹/战役持久化)
- **工作量总计**: ~10-12h (含测试)
- **建议分两个小版本**：v0.7.0 接入 weapon_jam + surrender (战术层)，v0.7.1 接入 campaign_persistence (战役层)

**Tester 视角**：
- 每个模块接入后必须新增集成测试 (参考 `tests/integration/test_ai_gameloop_integration.py` 模式)
- 必须新增 E2E 用户旅程测试 (用户规则 3)
- 接入后全量回归 0 失败

**Security 视角**：
- campaign_persistence 涉及存档文件 I/O，需验证 SecureSaveManager 集成
- 其他两个模块无安全风险

**DevOps 视角**：
- 无 CI/CD 变更
- 无新依赖

**UI 视角**：
- surrender_system: 需要显示投降旗 (CC2SmokeEffect 已有投降旗实现可复用)
- weapon_jam: 需要 UI 反馈"武器卡弹"状态 (HUD 提示)
- campaign_persistence: 需要在战役界面显示"已保存"提示

### 1.2 推进顺序 (生命周期 11-Phase 映射)

**Wave 1: v0.7.0 — weapon_jam 接入** (最快胜利)
- P1 Requirements: ✅ 已确认 CC2 原版有此功能
- P2 Architecture: 在 `ai_service.py.tick()` 中调用 `WeaponJamSystem.tick()`
- P3 Technical Design: WeaponJammed 事件 emit 路径
- P7 Test Planning: 新增 4-6 个集成测试
- P8 Implementation: 修改 `ai_service.py` + `event_bus.py`
- P9 Test Execution: 全量回归 + E2E 真实用户测试

**Wave 2: v0.7.0 — surrender_system 接入**
- P1 Requirements: ✅ 已确认 CC2 原版有此功能
- P2 Architecture: 在 `ai_service.py` 注册 SurrenderAI 到 TacticalOrchestrator
- P3 Technical Design: 投降条件判断 + 事件发布 + FallenUnitCache 协调
- P5 Interaction Design: 投降旗视觉反馈 (复用 cc2_combat_effects.py)
- P7 Test Planning: 新增 5-8 个集成测试
- P8 Implementation: 修改 `ai_service.py` + `surrender_system.py`
- P9 Test Execution: 全量回归 + E2E 真实用户测试

**Wave 3: v0.7.1 — campaign_persistence 接入** (独立小版本，避免 v0.7.0 过载)
- P1 Requirements: ✅ 已确认 CC2 原版有此功能
- P2 Architecture: `campaign_four_layer.py:68` 实例化 `CampaignPersistenceManager`
- P3 Technical Design: battle start 加载 + battle end 保存
- P4 Data Design: 存档文件 schema (已有，需验证)
- P7 Test Planning: 新增 6-10 个集成测试 (含跨 battle 继承)
- P8 Implementation: 修改 `campaign_four_layer.py` + `game_loop_assembler.py`
- P9 Test Execution: 全量回归 + E2E 战役旅程测试

### 1.3 前置依赖

- **weapon_jam**: 无前置依赖，可立即启动
- **surrender_system**: 建议在 weapon_jam 完成后接入（投降判断依赖弹药状态）
- **campaign_persistence**: 需确认 `SecureSaveManager` 集成正常 + `campaign_four_layer.py` 现有状态

### 1.4 验收标准

- [ ] weapon_jam: `WeaponJammed` 事件能被 emit + `clear_jam()` 在 tick 中被调用 + 4+ 集成测试通过
- [ ] surrender_system: `SurrenderAI` 注册到 `ai_service.py` + 投降条件触发 + 5+ 集成测试通过
- [ ] campaign_persistence: `_persistence` 不再为 None + save/load 循环测试通过 + 6+ 集成测试通过
- [ ] 全量回归: 6486+ tests 0 failed
- [ ] E2E 真实用户测试: 模拟真实玩家使用流程 0 failed (用户规则 3)
- [ ] 文档同步: PRD + TECH_DEBT + CHANGELOG + 三语 README + SKILL.md 全部更新

---

## 🎯 Point 2: TD-077 19 个孤立原型决策 (P2)

### 2.1 7-Role 共识结论

**Architect 视角**：
- 19 个模块 ~5000 行，逐个评估工作量大
- 部分模块（如 `cover_seek_ai`, `psychology_system`）符合 CC2 设计，有接入价值
- 部分模块（如 `enhanced_ui_renderer`, `enhanced_post_processing`）疑似已被其他模块取代
- 部分模块（如 `vehicle_variant_generator`, `faction_variant_generator`）是数据生成器，接入价值低

**PM 视角**：
- 不阻塞 v0.7.0 发布
- 建议分两步：(1) 快速分类决策 (~2h)，(2) 按决策执行 (~6-8h)
- 推荐选项 C (标记 ORPHAN 注释) 作为 v0.7.0 最小化方案

**Tester 视角**：
- 19 个模块每个都有 1 个测试文件，删除源文件需同步删除测试
- 部分测试可能已失效（依赖过时 API）

**DevOps 视角**：
- 无 CI/CD 影响
- 删除模块会减少 mypy 检查范围 (385 → ~366)

### 2.2 推荐方案: 三步走

**Step 1 (v0.7.0)**: 标记 `# STATUS: ORPHAN` 注释 (最小化变更，~30min)
- 在 19 个模块 docstring 顶部添加 `# STATUS: ORPHAN — pending integration decision (TD-077)`
- 不删除、不接入，仅标记状态
- 更新 TECH_DEBT.md 记录决策

**Step 2 (v0.7.1)**: 分类决策 (~2h)
- 按 5 类分组评估：
  - AI 类 (4): cover_seek_ai / psychology_system / ai_config / squad_group_manager
  - UI 类 (7): cc2_hud / enhanced_ui_renderer / path_preview / strategic_map_view / range_indicator / aar_panel / strategic_map
  - 渲染类 (2): enhanced_post_processing / weather_visual_effects
  - 系统类 (4): casualty_system / ammo_type_system / day_night_cycle / combat_log
  - 生成器类 (2): vehicle_variant_generator / faction_variant_generator
- 每个模块决策: INTEGRATE / ARCHIVE / DELETE

**Step 3 (v0.7.2+)**: 按决策执行
- INTEGRATE: 按 TD-076 模式接入
- ARCHIVE: 移动到 `src/pycc2/_archive/` (保留历史，不参与 import)
- DELETE: 删除源文件 + 测试文件

### 2.3 快速胜利候选 (低风险高价值)

基于初步评估，以下模块可能是"快速胜利"（接入价值高、工作量低）：
- `path_preview.py` (309L) — 路径预览，CC2 原版有此功能，接入到 `interaction_controller.py`
- `range_indicator.py` (192L) — 射程指示器，CC2 原版有此功能，接入到 `interaction_controller.py`
- `combat_log.py` (284L) — 战斗日志，CC2 原版有 AAR，接入到 `aar_panel.py`

**注意**: 这些候选需在 Step 2 详细评估后确认。

### 2.4 TD-078: deployment_manager.py 架构 smell (P2)

**方案**: 将 `deployment_factory.py` 的纯函数迁移到 `services/deployment/` 目录
**工作量**: 1.5h（含 import 路径更新 + 测试调整）
**推荐**: 留待 v0.7.0 与 Point 1 Wave 1/2 一起推进（共享 v0.7.0 测试周期）

---

## 🎯 Point 3: E2E 真实用户模拟测试 (P0, 用户规则 3)

### 3.1 用户规则 3 要求

> "测试计划中补充对系统进行 e2e 的测试，要发布前一定要做模拟真实用户使用的测试。"

### 3.2 测试范围

**v0.6.11 当前 E2E 测试状态**:
- 491 E2E tests / 7.9% 占比
- 覆盖核心场景: Tutorial / Combat / Save-Load / Vertical Slice / Interactive Smoke / Full Coverage

**v0.7.0 新增 E2E 测试需求**:
- 投降流程 E2E: 单位弹药耗尽 → 触发投降 → 投降旗显示 → 敌方接受
- 武器卡弹 E2E: Sten 枪持续射击 → 触发 jam → HUD 提示 → 自动清除
- 战役持久化 E2E: 完成 battle 1 → 保存 → 退出 → 加载 → battle 2 单位继承

### 3.3 v0.6.11 验证收尾 E2E 测试 (本次执行)

**目标**: 验证 v0.6.11 ghost 模块清理未破坏现有 E2E 用户旅程

**测试命令**:
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  python -m pytest tests/e2e/ -v --tb=short
```

**验收标准**:
- 491 E2E tests 全部通过
- 无新增 skip
- 无 flaky 测试 (3 次连续运行稳定)

### 3.4 v0.7.0 E2E 测试计划 (待 Point 1 完成后执行)

新增 E2E 测试文件:
- `tests/e2e/test_surrender_flow_e2e.py` (~10 tests)
- `tests/e2e/test_weapon_jam_e2e.py` (~8 tests)
- `tests/e2e/test_campaign_persistence_e2e.py` (~12 tests, v0.7.1)

---

## 📅 推进时间表

| 阶段 | 内容 | 优先级 | 预估工作量 |
|------|------|--------|-----------|
| **本次 (v0.6.11 收尾)** | E2E 真实用户测试 + 文档同步 | P0 | ~1h |
| **v0.7.0 Wave 1** | weapon_jam 接入 + 集成测试 + E2E | P1 | ~4h |
| **v0.7.0 Wave 2** | surrender_system 接入 + 集成测试 + E2E | P1 | ~5h |
| **v0.7.0 Wave 3** | TD-077 Step 1 (ORPHAN 标记) + TD-078 修复 | P2 | ~2h |
| **v0.7.1** | campaign_persistence 接入 + E2E | P1 | ~6h |
| **v0.7.1** | TD-077 Step 2 (分类决策) | P2 | ~2h |
| **v0.7.2+** | TD-077 Step 3 (按决策执行) | P2 | ~6-8h |

---

## 🔒 共识待达成的关键问题

1. **v0.7.0 范围**: 是否包含 campaign_persistence？建议拆到 v0.7.1 (避免 v0.7.0 过载)
2. **TD-077 处置**: 选项 A (逐个评估) / B (整体归档) / C (标记 ORPHAN)？推荐 C
3. **TD-078 时机**: v0.7.0 一起修复 vs v0.7.1 单独修复？推荐 v0.7.0
4. **E2E 测试自动化**: 是否在 CI 中增加 daily E2E job？推荐是

---

## 📚 文档同步清单 (活文档原则)

每个 Wave 完成后必须更新：

| 文档 | 更新内容 |
|------|----------|
| `docs/TECH_DEBT.md` | TD 状态从 🟡 P1 → ✅ RESOLVED |
| `docs/PRD.md` | 用户故事状态更新 (投降/卡弹/战役持久化) |
| `docs/ROADMAP.md` | v0.7.0 里程碑记录 |
| `docs/PROJECT_STATUS.md` | 版本号 + 模块数 + 测试数 |
| `VERSION` / `__init__.py` / `pyproject.toml` | 版本号同步 |
| `README.md` / `README_zh.md` / `README_ja.md` | 三语同步 |
| `CHANGELOG.md` | 新版本条目 |
| `SKILL.md` | 测试计数更新 |
| `docs/TEST_PLAN.md` | E2E 测试新增 |

---

## 🎓 教训预防

基于 v0.6.11 教训，v0.7.0 推进时必须：

1. **ghost feature 检测用深度扫描**: 接入后必须验证 `grep -rn "module_name" src/pycc2/` 有外部引用
2. **type:ignore[name-defined] 绝不保留**: 接入过程中如发现新的 type:ignore，必须修复
3. **文档先行+活文档原则**: 每个 Wave 先更新本文档，再写代码
4. **E2E 真实用户测试**: 每个 Wave 完成后必须运行 E2E 测试 (用户规则 3)
5. **批判性评估**: 接入前必须验证模块是否符合 CC2 原版设计，不盲目接入

---

> **文档先行，万事留痕** — 本计划文档先于代码变更，7-Role 评估共识后将作为执行依据。
> **活文档原则** — 本文档随 v0.7.0 推进实时更新，每个 Wave 完成后同步状态。
