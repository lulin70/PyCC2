# TD-073~078 推进计划 — Ghost 模块清理与类型安全修复

> **版本**: v0.6.10 → v0.6.11 | **日期**: 2026-07-17 | **状态**: ✅ v0.6.11 完成 (TD-073/074/075/076a 已 RESOLVED) + 📋 v0.7.0 计划已制定
> **来源**: 7 维度项目整理评估 D3 修正版发现（commit `d12e9b9`）
> **原则**: 文档先行，充分验证，达成共识后推进；P0/P1 按项目生命周期推进，P2/P3 给方案待用户审核
> **下一步**: v0.7.0 推进计划详见 [ROADMAP_v0.7.0.md](ROADMAP_v0.7.0.md) (3 点 Next-Step Plan, 7-Role 共识)

---

## ✅ v0.6.11 完成摘要 (2026-07-17)

**执行范围**: P0 清理 (TD-073/074/075) + P1 部分 (TD-076a context_menu 删除)

| TD | 操作 | 行数 | 测试删除 | 状态 |
|----|------|------|----------|------|
| TD-073 | 删除 spritesheet_parser.py | 508 | 8 (TestSpritesheetParser) | ✅ RESOLVED |
| TD-074 | 删除 operation_timeline.py | 151 | 26 (6 TestTimeline* + 4 Integration) | ✅ RESOLVED |
| TD-075 | 修复 tactical_ai_types.py L68 type:ignore[name-defined] | 1 | 0 | ✅ RESOLVED |
| TD-076a | 删除 context_menu.py (被 radial_menu 取代) | 308 | 13 (5 TestA4ContextMenu + ~8 TestContextMenu) | ✅ RESOLVED |

**验证结果**:
- 全量测试: 6486 passed / 2 skipped / 16 deselected / 1 warning in 65.60s
- ruff: 0 errors
- mypy: 0 errors (MYPYPATH=src mypy -p pycc2 --no-error-summary)
- 源码模块数: 388 → 385 (删除 3 ghost 模块)
- 文档一致性: `./scripts/check_doc_consistency.sh` 11/11 通过
- 零回归

**延期到 v0.7.0**:
- TD-076b: 接入 surrender_system (~3h)
- TD-076c: 接入 weapon_jam (~4h)
- TD-076d: 接入 campaign_persistence (~5h)
- TD-077/078: P2 评估待用户审核

---

## 7-Role 共识结论（2026-07-17）

### Architect + Coder 视角（TD-076 验证）

4 个半集成候选全部确认为真实 ghost（0 外部 src 引用，非误报）。3 接入 + 1 删除：

| 候选 | 结论 | 工作量 | 风险 | 关键证据 |
|------|------|--------|------|----------|
| surrender_system | **接入** | ~3h | 中 | SurrenderAI 未注册到 ai_service.py；FallenUnitCache 与 ammo_pickup.py 重复 |
| weapon_jam | **接入** | ~4h | 中 | 对称半成品：WeaponComponent.clear_jam() 已存在无人调用 + WeaponJammed 事件无人 emit |
| context_menu | **删除** | ~1.5h | 低 | 被 radial_menu.py 取代，interaction_controller.py 已用 RadialMenu；持续维护死文件的沉没成本陷阱 |
| campaign_persistence | **接入** | ~5h | 中 | campaign_four_layer.py:68 `_persistence = None` 预留注入点从未赋值；跨会话战役持久化缺失；110+ 测试已去风险 |

**附带文档错误**: `tests/e2e/E2E_REAL_USER_SCENARIOS.md:509-511` 引用不存在的 `CampaignPersistence` 类名（应为 `CampaignPersistenceManager`），接入时一并修正。

### Tester + DevOps 视角（测试影响评估）

- **test_phase_b_final_sprint.py**: 74 测试中 8 个 TestSpritesheetParser 需删除（L75-L210）
- **test_strategic_ui.py**: 22 个 TestTimeline* 测试需删除 + 6 类 + 2 fixture + import 块
- **tactical_ai_types.py L68 修复方案明确**: 改为 `intent: TacticIntent`（已有 TYPE_CHECKING import + PEP 563 `from __future__ import annotations`）；TacticIntent 类存在于 tactic_intent.py L51-64；0 连锁类型错误
- **测试数变化**: 6534 → ~6504（删除 30 个 ghost 测试）
- **CI gates 预期全绿**: lint/mypy/coverage(70%)/complexity(BASELINE=23) 均通过

### PM 视角（优先级与版本号）

- **版本号**: 0.6.10 → 0.6.11 (PATCH) — 无新功能，仅删除 ghost + 修复 type:ignore
- **TD-076 接入工作（~13.5h）**: 工作量较大，建议留待 v0.7.0（MINOR，新功能：投降/卡弹/战役持久化）
- **本次 v0.6.11 范围**: 仅 P0（TD-073/074/075）+ TD-076 context_menu 删除（共 ~2h）

### Security 视角

- `type: ignore[name-defined]` 是 project_memory 明确警告的隐藏 bug 风险，必须修复
- 删除 ghost 模块不引入新安全风险

### 共识执行顺序

1. **本次 v0.6.11**（P0 + 部分 P1，~2h）:
   - TD-073: 删除 spritesheet_parser.py + 8 测试
   - TD-074: 删除 operation_timeline.py + 22 测试
   - TD-075: 修复 tactical_ai_types.py L68
   - TD-076a: 删除 context_menu.py + 相关测试（被 radial_menu 取代）
2. **v0.7.0**（P1 接入，~12h，新功能版本）:
   - TD-076b: 接入 surrender_system (~3h)
   - TD-076c: 接入 weapon_jam (~4h)
   - TD-076d: 接入 campaign_persistence (~5h)
3. **v0.7.0+**（P2 方案待用户审核）:
   - TD-077: 19 个孤立原型处置（推荐选项 C：标记 `# STATUS: ORPHAN`）
   - TD-078: deployment_manager.py 架构 smell（推荐留待 v0.7.0 与 M6 一起）

---

## 一、执行摘要（修订版）

7 维度项目整理评估 D3 修正版（2026-07-17）发现 25 个 0 src 引用 ghost 候选模块 + 1 处 `type:ignore[name-defined]` 高风险。本计划聚焦 6 项技术债（TD-073~TD-078），按 P0→P1→P2 优先级分波次推进。

**v0.6.11 范围（本次执行）**: P0 清理（TD-073/074/075）+ TD-076 context_menu 删除 — 恢复就绪度 ~80% → ~85%
**v0.7.0 范围（下次执行）**: TD-076 三个接入 + P2 评估 — 恢复就绪度 ~85% → ~90%

**核心原则**：
1. **文档先行**：本计划文档先于代码变更；每个 TD 完成后同步更新 TECH_DEBT.md
2. **充分验证**：每个 TD 完成后运行全量测试，零回归才可推进下一个
3. **外科手术式变更**：精准删除/修复，不触碰无关代码
4. **诚实评估**：4 个半集成候选必须逐个验证实际引用链，不能主观假设

---

## 二、波次划分

### Wave 1: P0 Ghost 模块清理（TD-073, TD-074）

**目标**: 删除 2 个明确 PLANNED 标记的 ghost 模块及其测试

| ID | 文件 | 行数 | 测试引用 | 操作 |
|----|------|------|----------|------|
| TD-073 | `src/pycc2/presentation/rendering/spritesheet_parser.py` | 508 | `tests/unit/test_phase_b_final_sprint.py` (8 处) | 删除源文件 + 删除相关测试 |
| TD-074 | `src/pycc2/presentation/ui/operation_timeline.py` | 151 | `tests/unit/test_phase_b_final_sprint.py` (含 OperationTimelineUI 测试) | 删除源文件 + 删除相关测试 |

**生命周期映射**: P5 (Interaction Design) — N/A（删除）+ P8 (Implementation) — 删除实现 + P9 (Test Execution) — 全量回归

**验证**: `find src/pycc2 -name "*.py" | wc -l` 从 388 → 386；全量测试 0 失败

**风险**: 低 — 已确认 0 src 外部引用，删除不影响运行时

**回滚方案**: `git revert <commit>` 一键回滚

### Wave 2: P0 类型安全修复（TD-075）

**目标**: 修复 `tactical_ai_types.py:68` 的 `type: ignore[name-defined]` 隐藏 bug 风险

**文件**: `src/pycc2/domain/ai/tactical_ai_types.py:68`

**问题代码**:
```python
intent: pycc2.domain.ai.tactic_intent.TacticIntent  # type: ignore[name-defined]  # noqa: F821
```

**修复方案**:
```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from pycc2.domain.ai.tactic_intent import TacticIntent

# 在类定义中
intent: "TacticIntent"  # 字符串前向引用，TYPE_CHECKING 下解析
```

**生命周期映射**: P3 (Technical Design) — 类型设计 + P8 (Implementation) — 修复 + P9 — mypy 验证

**验证**: `mypy src/pycc2/domain/ai/tactical_ai_types.py` 0 errors + 全量测试 0 失败

**风险**: 中 — 前向引用修复可能暴露其他隐藏的类型错误

### Wave 3: P1 半集成候选验证（TD-076）

**目标**: 验证 4 个无 PLANNED 标记但 ≥2 测试引用的 ghost 候选

| 候选 | 行数 | 验证方法 | 可能结论 |
|------|------|----------|----------|
| `src/pycc2/domain/ai/surrender_system.py` | 403 | grep `SurrenderSystem` + 检查 game_loop_assembler.py / ai_service.py | 接入 / 删除 |
| `src/pycc2/domain/ai/weapon_jam.py` | 252 | grep `WeaponJam` + 检查 combat_systems.py | 接入 / 删除 |
| `src/pycc2/presentation/ui/context_menu.py` | 308 | grep `ContextMenu` + 检查 interaction_controller.py | 接入 / 删除 |
| `src/pycc2/domain/systems/campaign_persistence.py` | 373 | grep `CampaignPersistenceManager` + 检查 campaign_four_layer.py | 接入 / 删除 |

**生命周期映射**: P1 (Requirements Analysis) — 是否需要该功能 + P2 (Architecture) — 如何接入

**验证**: 每个候选必须明确结论（接入路径 or 删除理由），不可悬而未决

**风险**: 中 — 接入工作量大；删除可能丢失有价值的功能

### Wave 4: P2 方案待审核（TD-077, TD-078）

**目标**: 给出 19 个孤立原型 + 1 处架构 smell 的处置方案，待用户审核

**TD-077**: 19 个孤立原型（~5000 行）评估方案
- 选项 A: 逐个评估删除/集成（工作量大，~6-8h）
- 选项 B: 整体归档到 `src/pycc2/_archive/` 目录（保留历史，不参与 import）
- 选项 C: 标记为 `# STATUS: ORPHAN` 注释，留待 v0.7.0 处理
- **推荐**: 选项 C（最小化变更，留待 v0.7.0 系统性处理）

**TD-078**: `deployment_manager.py:158` 架构 smell
- 方案: 将 `deployment_factory.py` 的纯函数迁移到 `services/deployment/` 目录
- 工作量: 1.5h（含 import 路径更新 + 测试调整）
- **推荐**: 留待 v0.7.0 与 M6 功能开发一起推进

---

## 三、生命周期阶段映射

| Phase | 本次涉及 TD | 责任角色 | 产出 |
|-------|------------|----------|------|
| P1 Requirements | TD-076 (4 候选是否需要) | PM + Architect | 候选处置决策表 |
| P2 Architecture | TD-076 接入方案 | Architect | 接入路径设计 |
| P3 Technical Design | TD-075 类型设计 | Architect + Coder | TYPE_CHECKING 方案 |
| P5 Interaction Design | N/A（无 UI 变更） | — | — |
| P6 Security Review | TD-075 修复后 | Security | mypy 0 errors 确认 |
| P7 Test Planning | 全部 | Tester | 回归测试计划 |
| P8 Implementation | TD-073/074/075/076 | Coder | 代码变更 |
| P9 Test Execution | 全部 | Tester | 6534+ tests 0 failure |
| P10 Deployment | N/A（本地项目） | — | — |

---

## 四、验证策略

### 4.1 每个 TD 完成后的验证

```bash
# 1. 全量回归测试
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy .venv/bin/python -m pytest -m "not slow" --tb=short -q

# 2. 类型检查
.venv/bin/python -m mypy src/pycc2/ --check-untyped-defs

# 3. Lint
.venv/bin/python -m ruff check . && .venv/bin/python -m ruff format --check .

# 4. 文档一致性
./scripts/check_doc_consistency.sh
```

### 4.2 全部完成后的最终验证

- 源码模块数: 388 → 386（删除 2 个 PLANNED ghost）+ N（TD-076 视结论）
- 测试数: 6534 → ≥6520（删除相关测试后仍 ≥6520，TD-075/TD-076 不删测试）
- mypy: 0 errors
- ruff: 0 errors
- 文档一致性: 11/11

---

## 五、文档同步清单（每个 TD 完成后必须更新）

| 文档 | 更新内容 |
|------|----------|
| `docs/TECH_DEBT.md` | TD 状态从 🔴 P0 待清理 → ✅ RESOLVED |
| `docs/PROJECT_ASSESSMENT_v0.6.10.md` | Ghost features 数量更新 |
| `VERSION` | 0.6.10 → 0.6.11（PATCH 递增，无新功能） |
| `src/pycc2/__init__.py` | 版本号同步 |
| `pyproject.toml` | 版本号同步 |
| `README.md` / `README_zh.md` / `README_ja.md` | 模块数 388 → 386 |
| `CHANGELOG.md` | 新增 v0.6.11 条目 |
| `SKILL.md` | 测试计数更新 |

---

## 六、共识待达成的关键问题

1. **TD-076 的 4 个半集成候选**: 接入 or 删除？需 7-role 评估
2. **TD-077 的 19 个孤立原型**: 选项 A/B/C 哪个？需用户决策
3. **TD-078 的架构 smell**: 立即修复 or 留待 v0.7.0？需用户决策
4. **版本号**: 0.6.10 → 0.6.11 (PATCH) or 0.7.0 (MINOR)？建议 PATCH（无新功能）

---

> **文档先行，万事留痕** — 本计划文档先于代码变更，7-role 评估共识后将作为执行依据。
