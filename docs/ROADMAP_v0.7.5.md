# ROADMAP v0.7.5 — INTEGRATE psychology_system + squad_group_manager 接入游戏循环 (PATCH)

**Status**: ✅ 完成
**Created**: 2026-07-18
**Completed**: 2026-07-18
**Version**: 0.7.5 (PATCH — 完整接入，SemVer 偏离理由见 §1.3)
**Prev**: v0.7.4 INTEGRATE 前置准备 (squad_group_manager 测试增强 5→35 tests + mypy 7 errors 修复)

---

## 1. 背景与决策

### 1.1 v0.7.4 完成 + v0.7.5 INTEGRATE 计划

v0.7.4 完成了 INTEGRATE 前置准备（squad_group_manager 测试增强 5→35 tests + psychology_system/squad_group_manager INTEGRATE 设计文档 + mypy 7 个预先存在错误修复）。ROADMAP_v0.7.4.md §5 已规划接入蓝图。v0.7.5 执行真正的 INTEGRATE：将两个 ORPHAN 模块接入游戏循环，让功能可用。

### 1.2 接入范围

| 模块 | 接入点 | 修改文件 | 工作量 |
|------|--------|----------|--------|
| **psychology_system** | TacticalOrchestrator.tick() Phase 5 评估 | `tactical_orchestrator.py` | <2h |
| **squad_group_manager** | GameLoop 属性 + Assembler 装配 + Input Ctrl+1~9 + Minimap 渲染 | `game_loop.py` / `game_loop_assembler.py` / `handler.py` / `ui_overlay_renderer.py` | 2-5h |

### 1.3 版本号决策 (SemVer 偏离说明)

**用户决策**: v0.7.5 (PATCH 完整接入)

**SemVer 偏离理由**:
- psychology_system (369行) + squad_group_manager (149行) 的**功能逻辑已实现**（v0.7.4 已有 35+93 处测试验证）
- v0.7.5 只是**"接线"**让模块接入游戏循环，不新增功能逻辑
- 接入后用户可使用 Ctrl+1~9 编组 + AI 行为受 psychology 影响，从用户视角是"功能新增"
- 但从代码视角，只是"调用已有代码"，非"编写新功能"
- **7-Role 共识**: 尊重用户决策，定位为 PATCH，在 CHANGELOG 中诚实记录 SemVer 偏离

---

## 2. DevSquad 7-Role 共识评估

| Role | Vote | Rationale |
|------|------|-----------|
| **Architect** | ✅ 支持 | ROADMAP_v0.7.4.md §5 已规划接入蓝图，接入点清晰；psychology_system 纯静态无状态低风险；squad_group_manager dataclass 接入 game_loop 符合现有 facade 模式 |
| **PM** | ✅ 支持 | 用户可使用 Ctrl+1~9 编组是 CC2 核心战术体验；AI 行为受 psychology 影响提升真实感；v0.7.5 PATCH 定位符合用户"功能逻辑已实现只是接线"的认知 |
| **Security** | ✅ 支持 | 无外部输入新增（Ctrl+1~9 是已有键盘事件）；psychology_system 无副作用；squad_group_manager 无持久化无泄露风险 |
| **Tester** | ✅ 支持 | psychology_system 有 93 处测试调用 + squad_group_manager 有 35 tests 保障业务逻辑；v0.7.5 需补充集成测试验证接入后行为；需验证 Ctrl+1~9 键盘映射 + minimap 渲染 |
| **Coder** | ✅ 支持 | psychology_system 接入只需在 TacticalOrchestrator.tick() 添加 Phase 5 过滤；squad_group_manager 接入遵循现有 assembler 模式；修改文件清单明确 |
| **DevOps** | ✅ 支持 | 无新依赖；版本号 0.7.4→0.7.5 全量同步 18 文件；check_doc_consistency.sh 11/11 PASS；CI 无新增步骤 |
| **UI** | ✅ 支持 | minimap 彩色矩形绘制编组 bounds 提升战术可读性；Ctrl+1~9 是 RTS 标准交互；bottom_panel 显示编组单元数量 |

**共识结果**: 7/7 ✅ 一致通过 — v0.7.5 定位为 PATCH 完整接入（SemVer 偏离已记录）

---

## 3. 接入设计

### 3.1 psychology_system 接入

**当前状态**: 纯静态类，`PsychologySystem.evaluate_order(unit, tactic_type) -> OrderAcceptance`，6 步短路评估

**接入点**: `src/pycc2/domain/ai/tactical_orchestrator.py` `TacticalOrchestrator.tick()` L87-126

**当前 tick() 流程**:
```
Phase 1: 各 AI evaluate(context) 打分 (L90-94)
Phase 2: 收集 score≥0.1 的 AI 的 intents (L96-105)
Phase 3: 冲突解决 — 每个单位只分配给一个 AI (L107-119)
Phase 4: 构建最终命令列表按优先级排序 (L121-125)
```

**v0.7.5 新增 Phase 5: Psychology 评估**:
```python
# Phase 5: Psychology evaluation — filter orders by unit psychological state
from pycc2.domain.systems.psychology_system import PsychologySystem

filtered: list[TacticIntent] = []
for intent in final:
    unit = next((u for u in context.friendly_units if u.id == intent.unit_id), None)
    if unit is None:
        filtered.append(intent)  # 未找到单位，保留命令
        continue
    acceptance = PsychologySystem.evaluate_order(unit, intent.tactic_type)
    if acceptance.accepted:
        filtered.append(intent)
    else:
        logger.debug(
            "Order rejected: unit=%s tactic=%s reason=%s",
            intent.unit_id, intent.tactic_type, acceptance.reason
        )
final = filtered
```

**依赖**: `TacticIntent.tactic_type` 属性（需确认存在）+ `OrderAcceptance.accepted` / `.reason` 属性

### 3.2 squad_group_manager 接入

**当前状态**: `SquadGroupManager` dataclass，MAX_GROUPS=9，已有 35 tests 保障

**接入点 1: GameLoop 属性**
- 文件: `src/pycc2/services/game_loop.py` L91-118 GameLoop dataclass
- 新增: `_squad_group_manager: SquadGroupManager | None = field(init=False, default=None)`

**接入点 2: Assembler 装配**
- 文件: `src/pycc2/services/game_loop_assembler.py` L49 `assemble()`
- 新增: `_init_squad_groups()` 方法，实例化 SquadGroupManager
- 在 `assemble()` 中调用 `self._init_squad_groups()`

**接入点 3: Input Handler 键盘事件**
- 文件: `src/pycc2/presentation/input/handler.py` L35 `process_event()`
- 新增: KEYDOWN 事件处理 Ctrl+1~9 (创建组) / 1~9 (选择组)
- 需要 game_loop 或 interaction_controller 持有当前选中单位列表

**接入点 4: Minimap 渲染**
- 文件: `src/pycc2/presentation/rendering/ui_overlay_renderer.py`
- 新增: 遍历 `active_group_numbers`，调用 `get_group_bounds()` 绘制彩色矩形

---

## 4. 执行清单 (5 Waves)

### Wave 1: psychology_system 接入 (Coder) — ✅ 完成

**风险等级**: LOW（纯静态类，无状态，additive 设计）

- [x] 确认 `TacticIntent.tactic_type` 属性存在
- [x] 确认 `OrderAcceptance.accepted` / `.reason` 属性
- [x] 在 `tactical_orchestrator.py` `tick()` Phase 4 后添加 Phase 5: Psychology 评估
- [x] 补充集成测试 `tests/integration/test_psychology_integration.py` (11 tests)
- [x] 验证 psychology_system STATUS 标记从 ORPHAN 改为 INTEGRATED

### Wave 2: squad_group_manager 接入 (Coder) — ✅ 完成

**风险等级**: MEDIUM（涉及 input + rendering + game_loop）

- [x] `game_loop.py` 添加 `_squad_group_manager` 属性
- [x] `game_loop_assembler.py` 添加 `_init_squad_groups()` 装配方法
- [x] `input_router.py` 添加 KEYDOWN 处理 Ctrl+1~9 / 1~9
- [x] `minimap.py` 添加 minimap 编组矩形渲染（含 tile 坐标空间修复）
- [x] `input_router_protocol.py` IInputRouter protocol 新增 `squad_group_manager` 属性
- [x] 补充集成测试 `tests/integration/test_squad_group_integration.py` (16 tests)
- [x] 验证 squad_group_manager STATUS 标记从 ORPHAN 改为 INTEGRATED

### Wave 3: 版本号 0.7.4→0.7.5 + 文档同步 (DevOps) — ✅ 完成

- [x] `VERSION` / `__init__.py` / `pyproject.toml` / `SKILL.md`
- [x] `docs/PRD.md` / `docs/TEST_PLAN.md` / `docs/TECH_DEBT.md` / `docs/PROJECT_STATUS.md`
- [x] `README.md` / `README_zh.md` / `README_ja.md`
- [x] `docs/DESIGN.md` / `docs/ROADMAP.md`
- [x] `check_doc_consistency.sh` 11/11 PASS

### Wave 4: 全量验证 (Tester/DevOps) — ✅ 完成

- [x] `pytest tests/ -m "not slow"` — **6216 passed, 2 skipped, 18 deselected** (67.06s)
- [x] `ruff check .` — 0 errors
- [x] `MYPYPATH=src mypy -p pycc2` — 0 errors (374 source files)
- [x] `bash scripts/check_doc_consistency.sh` — 11/11 PASS
- [x] 新增集成测试全部通过 (11 psychology + 16 squad_group = 27 tests)

### Wave 5: CHANGELOG + Git 推送 (DevOps) — ✅ 完成

- [x] `CHANGELOG.md` 插入 v0.7.5 完整条目（含 SemVer 偏离说明）
- [x] `docs/ROADMAP_v0.7.5.md` 状态更新为 ✅ 完成
- [x] Git commit + push origin/main
- [x] CarryMem `classify_and_remember` 记录会话总结

---

## 5. 风险与缓解

| 风险 | 等级 | 缓解 |
|------|------|------|
| psychology_system 过滤导致 AI 命令全部被拒 | LOW | evaluate_order 默认 accept（除非 morale/suppression 极低）；集成测试验证 |
| squad_group_manager Ctrl+1~9 与现有快捷键冲突 | MEDIUM | 检查现有 KEYDOWN 处理，确认 1~9 未被占用；冲突则改用 Ctrl+Shift+1~9 |
| minimap 渲染 bounds 计算错误 | LOW | get_group_bounds() 已有测试；渲染时验证 bounds 非 None |
| 接入后测试数变化导致文档不一致 | LOW | Wave 3 同步测试数；Wave 4 验证 |

---

## 6. DevSquad 11-Phase 生命周期映射

| Phase | 状态 | 产出 |
|-------|------|------|
| 1. Intent | ✅ | 用户要求 INTEGRATE psychology_system + squad_group_manager |
| 2. Spec | ✅ | 本文档 §3 接入设计 |
| 3. Plan | ✅ | 本文档 §4 执行清单 (5 Waves) |
| 4. Consensus | ✅ | 7/7 一致通过 (§2) |
| 5. Design | ✅ | ROADMAP_v0.7.4.md §5 蓝图 + 本文档 §3 |
| 6. Implement | ✅ | Wave 1 + Wave 2 完成（psychology_system + squad_group_manager 完整接入） |
| 7. Test | ✅ | Wave 4 验证（6216 passed / 0 failed / 2 skipped） |
| 8. Review | ✅ | Wave 4 验证（mypy 0 errors / ruff 0 errors / doc_consistency 11/11） |
| 9. Document | ✅ | Wave 3 + Wave 5 完成（11 文档同步 + CHANGELOG + ROADMAP） |
| 10. Deploy | ✅ | Wave 5 Git push 到 origin/main |
| 11. Learn | ✅ | Wave 5 CarryMem 记录会话总结 |
