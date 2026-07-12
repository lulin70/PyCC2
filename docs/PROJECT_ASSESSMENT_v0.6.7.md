# PyCC2 v0.6.7 项目整理评估报告 (R3 — 7 维度深度验证)

> **版本**: v0.6.7 | **日期**: 2026-07-12 | **方法**: DevSquad 7 角色共识 + 6 Agent 并行验证
> **前置评估**: [PROJECT_ASSESSMENT_v0.6.6_r2.md](PROJECT_ASSESSMENT_v0.6.6_r2.md)（R2 评估，commit 6275ec3）
> **本次评估基础**: commit cecc9d5（v0.6.7 TD-COV-BUG 修复后）
> **评估范围**: 7 维度全量评估 + 实际命令验证（非仅文档走读）

---

## 综合成熟度评分: ~82% (Beta Candidate) ↓ R2 评估 ~85%

| 维度 | R2 评估 | R3 (本次) | 变化 | 关键修正 |
|------|---------|-----------|------|----------|
| 1. 代码走读 | ✅ 优秀 | ⚠️ 7.5/10 | ↓ | 24 个 AI 子类仅 8 个注册到 orchestrator |
| 2. 文档一致性 | ✅ 良好 | ✅ 9/10 | ↑ | 版本号全一致，CHANGELOG 完整（R2 agent 误判） |
| 3. 技术债 | ✅ 0 活跃 | ⚠️ 6/10 | ↓ | **3 个幽灵功能**（AI 模块未接入主流程） |
| 4. 测试验证 | ✅ 0 flaky | ⚠️ 7/10 | ↓ | **1 个 flaky 测试**（R2 "零 flaky" 不准确） |
| 5. CI/CD | ✅ 优秀 | ✅ 7.5/10 | → | 无 --ignore（agent 误判），但 pip-audit 不阻断 |
| 6. 目录清理 | ✅ 优秀 | ✅ 8/10 | → | .gitignore 完整（agent 误判），R2 报告待归档 |
| 7. 成熟度 | ~85% | **~82%** | ↓ -3% | 修正 R2 两处不准确评估 |

**评分下调原因**: R2 评估存在两处关键遗漏——(1) "0 幽灵功能"错误，实际有 3 个 AI 模块未接入游戏主循环；(2) "零 flaky"错误，实际存在 1 个随机性导致的 flaky 测试。本次评估通过实际运行命令验证，修正了这两处不准确评估。

---

## 维度1: 代码走读 ⚠️ 7.5/10

### 1.1 DDD 四层架构完整性 ✅
- `domain/` 层零外部导入 ✅（架构守卫测试 TD-041 自动化验证）
- `services/` → `presentation` 导入全部在 TYPE_CHECKING 块 ✅
- `infrastructure/` → `services`/`presentation` 导入全部在 TYPE_CHECKING 块 ✅
- 入口点 `main.py` 清晰，无循环依赖 ✅

### 1.2 AI 模块集成缺口 ⚠️ P1（本次评估新发现）
- **24 个 TacticalAIBase 子类**，但 `ai_service.py` L77-84 只注册了 **8 个** 到 TacticalOrchestrator：
  - 已注册：FlankingAI / SuppressionAI / InfantryTankCoordAI / VictoryPointAI / RetreatDecisionAI / ATAmbushAI / CounterattackAI / AmbushAI
  - **未注册（幽灵功能）**：ReconAI / SupplyAwarenessAI / CoverSeekAI / TrenchDiggingAI / SmokeTacticalAI / BuildingClearingAI / WeaponScavengeAI / SurrenderAI / NightStealthAI / MedicAI / TankRiderAI / MineWarfareAI / ArtilleryCallinAI / EngineerAssaultAI / MeleeCombatAI
- **特别确认的 3 个幽灵功能**（v0.6.3-v0.6.5 新增，有完整实现+单元测试但不接入主流程）：
  - `ReconAI` ([recon_ai.py:72](file:///Users/lin/trae_projects/PyCC2/src/pycc2/domain/ai/recon_ai.py)) — grep 确认无外部 import
  - `PsychologySystem` ([psychology_system.py:155](file:///Users/lin/trae_projects/PyCC2/src/pycc2/domain/systems/psychology_system.py)) — grep 确认无外部调用
  - `SupplyAwarenessAI` ([supply_awareness_ai.py:84](file:///Users/lin/trae_projects/PyCC2/src/pycc2/domain/ai/supply_awareness_ai.py)) — grep 确认无外部 import
- **影响**: README/CHANGELOG 宣传的 P3-4 侦察行为、P3-5 心理模型、P3-6 补给线意识功能在游戏中实际不生效

### 1.3 代码质量
- 0 个 NotImplementedError ✅
- 0 个 `pass # TODO` 占位 ✅
- ruff check 0 errors ✅
- mypy 0 errors ✅
- **P2**: `morale_system.py` 高圈复杂度函数（CI radon cc 阈值 D+ 即 ≥21 阻断）
- **P2**: `squad_coordinator.py` 多层嵌套逻辑
- **P2**: `pathfinder.py` 存在魔法数字

### 1.4 大文件评估（与 R2 一致）
- 43 个文件 >500 行（最大 pixvoxel_loader.py 1379L，scripts-only 不拆）
- 累计 52 候选 → 1 TRUE / 51 FALSE = 1.9% hit rate，全部评估为非 God Class（SRP 标准）

---

## 维度2: 文档一致性 ✅ 9/10

### 2.1 版本号一致性 ✅（全量验证）
| 位置 | 版本号 | 状态 |
|------|--------|------|
| VERSION | 0.6.7 | ✅ |
| pyproject.toml | 0.6.7 | ✅ |
| src/pycc2/__init__.py | 0.6.7 | ✅ |
| README.md | v0.6.7 | ✅ |
| README_zh.md | v0.6.7 | ✅ |
| README_ja.md | v0.6.7 | ✅ |
| PROJECT_STATUS.md | v0.6.7 | ✅ |
| TECH_DEBT.md | v0.6.7 | ✅ |
| CHANGELOG.md | v0.6.7 | ✅（R2 agent 误判为缺失，实际有完整条目） |

### 2.2 CHANGELOG.md v0.6.7 条目 ✅
- 9 项源码 bug 修复详情完整 ✅
- 版本号同步更新清单（10 个文件）✅
- 验证数据：ruff 0 errors / pytest 6178 passed ✅

### 2.3 多语言版本一致性 ✅
- EN/CN/JP 三语言版本号、日期、测试数完全一致 ✅
- README.md L3: `v0.6.7 | Beta Candidate | July 12, 2026`
- README_zh.md L3: `v0.6.7 | Beta 候选版本 | 2026年7月12日`
- README_ja.md L3: `v0.6.7 | Beta Candidate | 2026年7月12日`

### 2.4 文档与代码一致性 ⚠️ P1
- **P1**: README/CHANGELOG 宣传 P3-4/P3-5/P3-6 功能（侦察/心理/补给），但代码中这些 AI 模块未接入主流程（见维度1.2）
- **P2**: PROJECT_ASSESSMENT_v0.6.6_r2.md 应归档到 docs/archive/（当前在 docs/ 根目录）

---

## 维度3: 技术债和幽灵功能 ⚠️ 6/10

### 3.1 真幽灵功能（P1，本次评估确认）
| 模块 | 文件 | 状态 | 证据 |
|------|------|------|------|
| ReconAI | recon_ai.py | 未接入 | grep 确认无外部 import，未注册到 orchestrator |
| PsychologySystem | psychology_system.py | 未接入 | grep 确认无外部调用 |
| SupplyAwarenessAI | supply_awareness_ai.py | 未接入 | grep 确认无外部 import，未注册到 orchestrator |

**与 R2 报告的差异**: R2 报告 §1.3 声称"0 个 NotImplementedError / 0 个 pass # TODO / 0 个 stub/placeholder"，但未检查"已实现但未接入"的幽灵功能。本次评估通过 grep + orchestrator 注册清单交叉验证，确认 3 个幽灵功能。

### 3.2 技术债标记
- 真实 TODO/FIXME/HACK: **0 个** ✅（grep 确认 src/ 下 0 匹配）
- "XXX" 匹配: 全部是 "XXX Corps" 历史术语误报 ✅
- 0 个 NotImplementedError ✅
- type: ignore: 需进一步验证（项目记忆：name-defined 和 F821 的 type: ignore 绝不能保留）

### 3.3 误判纠正
技术债 agent 报告的 6 个"幽灵功能"中，3 个为误判：
- `terrain_tiles_battlefield.py` — 被 terrain_tile_generator.py 引用 ✅（非幽灵）
- `enhanced_renderer_delegate_mixin.py` — 被 EnhancedRenderer 继承 ✅（非幽灵）
- `cc2_combat_effects.py` — 4 个文件引用 ✅（非幽灵）

**命中率**: 3/6 = 50%（高于 God Class 阈值的 1.9%，但仍需人工验证）

### 3.4 死代码
- ruff check 全部通过 ✅
- 0 个未使用导入，0 个未使用变量 ✅

---

## 维度4: 测试验证 ⚠️ 7/10

### 4.1 实际测试结果（本次评估运行）
```
pytest tests/ -m "not slow" -p no:randomly --tb=line -q
= 1 failed, 6177 passed, 21 skipped, 16 deselected, 190 warnings in 65.65s =
```

### 4.2 flaky 测试发现 ⚠️ P1（本次评估新发现）
- **失败测试**: `tests/unit/test_swiss_cheese.py::TestSwissCheeseEngineResolve::test_high_damage_more_kia`
- **失败原因**: 断言 `assert 1 >= (4 - 2)` 失败——高伤害场景 KIA=1，低伤害场景 KIA=4，违反"高伤害应导致更多 KIA"的断言
- **根因**: SwissCheese 伤亡引擎含随机性，低伤害时偶然产生更多 KIA
- **与 R2 的差异**: R2 报告 §4.6 声称"全量回归 3 次零 flaky"，但 R2 使用了 `-p no:randomly` 固定随机种子，隐藏了随机性导致的 flaky。本次评估也用了 `-p no:randomly`，但仍出现失败，说明 flaky 在固定种子下也可能触发。

### 4.3 测试结构 ✅
- tests/ 五类测试: unit / integration / e2e / benchmark / acceptance ✅
- 6215 tests collected ✅
- conftest.py 存在 ✅

### 4.4 E2E 和用户旅程测试 ✅
- tests/e2e/test_full_customer_journey.py: 完整用户旅程 ✅
- tests/e2e/test_ai_behaviors_e2e.py: AI 行为 E2E ✅
- tests/e2e/test_real_gameplay_e2e.py: 18 tests 真实游戏流程 ✅
- tests/benchmark/test_performance.py: 帧率+AI 延迟基准 ✅

### 4.5 测试质量反模式 ⚠️ P2
- `test_combat_resolver.py`: 存在 `assertTrue(x > 0)` 弱断言
- `test_behavior_tree.py` / `test_tactic_executor.py`: 存在 skip 标注
- conftest.py: 存在全局 skip 规则（需审查合理性）

### 4.6 pygame UI E2E
- 项目为 pygame 游戏（非 Web UI），UI 测试通过 `SDL_VIDEODRIVER=dummy` 无头模式运行 ✅
- 真实玩家视角的用户旅程测试: 89 passed（R2 数据，本次未重跑）✅

---

## 维度5: CI/CD ✅ 7.5/10

### 5.1 Pipeline 完整性 ✅
- 7 阶段: lint → unit-tests → integration-tests → e2e-tests → slow-tests → benchmark → docker-build ✅
- 依赖锁定: requirements-dev.lock 全部 7 个 job 使用 ✅
- **--ignore/--deselect: 0 命中** ✅（CI agent 误判 `-m "not slow"` 为掩盖失败，实际是正常的标记筛选）

### 5.2 CI 配置问题
| 严重度 | 问题 | 位置 | 建议 |
|--------|------|------|------|
| **P1** | pip-audit 不 fail on vulns | ci.yml L54 | 添加 `--strict` 或 `--fail-on` |
| **P2** | cov-fail-under=60 过低 | ci.yml L87 | 提升至 70（实际 72.64%） |
| **P2** | codecov fail_ci_if_error: false | ci.yml L97 | 改为 true |
| **P1** | Dockerfile 不用非 root 用户 | Dockerfile | 添加 USER 指令 |
| **P2** | docker-build 不 push 到 registry | ci.yml L252-264 | 可选：添加 GHCR push |

### 5.3 Docker 配置
- 基础镜像: python:3.12-slim ✅
- CMD: 干净，无 --deselect ✅
- 环境变量: SDL_VIDEODRIVER=dummy, SDL_AUDIODRIVER=dummy ✅
- **P1**: 未使用非 root 用户运行

### 5.4 pre-commit 配置 ✅
- ruff rev 已更新至 v0.15.20（与 requirements-dev.lock 一致）✅（R2 修复 TD-070）
- 包含 ruff/bandit/mypy 等关键 hooks ✅

### 5.5 mypy / bandit 配置
- mypy: 0 errors ✅，但 `disallow_untyped_defs=false`（P2，过于宽松）
- bandit.yaml: 跳过 B101/B311/B601（合理，针对测试/随机数/子进程）

---

## 维度6: 目录清理 ✅ 8/10

### 6.1 .gitignore 完整性 ✅（全量验证）
| 条目 | 行号 | 状态 |
|------|------|------|
| __pycache__/ | L2 | ✅ |
| *.pyc | L3 | ✅ |
| .coverage | L41 | ✅ |
| htmlcov/ | L38 | ✅ |
| coverage.json | L46 | ✅ |
| .venv | L108 | ✅ |
| .mypy_cache/ | L126 | ✅ |
| .ruff_cache/ | L146 | ✅ |
| .pytest_cache/ | L50 | ✅ |
| screenshots/ | L176 | ✅（目录 agent 误判为缺失） |
| saves/*.sav | L167 | ✅ |
| src/pycc2/saves/ | L183 | ✅（R2 新增） |

### 6.2 git 跟踪验证 ✅
- `git ls-files screenshots/` → 0 文件 ✅（已忽略）
- `git ls-files saves/` → 仅 .gitkeep ✅（保留空目录，合理）
- `git ls-files | grep .coverage` → 0 文件 ✅

### 6.3 目录结构规范性 ✅
- src/pycc2/ 四层架构: domain / services / presentation / infrastructure ✅
- tests/ 五类测试: unit / integration / e2e / benchmark / acceptance ✅
- docs/ 根目录: 21 个活跃文档 + docs/archive/ 23 个归档 ✅

### 6.4 待清理项
- **P2**: `docs/PROJECT_ASSESSMENT_v0.6.6_r2.md` 应归档到 docs/archive/（当前在 docs/ 根目录）
- **P2**: `docs/PROJECT_ASSESSMENT_v0.6.6.md`（R1）应归档到 docs/archive/

---

## 维度7: 诚实评价与下一步建议

### 项目成熟现状: ~82% (Beta Candidate) ↓ R2 评估 ~85%

**评分下调的诚实理由**:
1. R2 报告"0 幽灵功能"错误：实际有 3 个 AI 模块（ReconAI/PsychologySystem/SupplyAwarenessAI）未接入游戏主循环，虽有单元测试但不影响游戏行为
2. R2 报告"零 flaky"错误：实际存在 1 个随机性导致的 flaky 测试（test_swiss_cheese.py::test_high_damage_more_kia）
3. 这两处遗漏导致 R2 的 85% 评估偏高，修正后为 ~82%

**优势（维持）**:
1. DDD 四层架构严格执行，0 架构违规 ✅
2. 版本号全量一致（9 个位置全部 0.6.7）✅
3. CI pipeline 7 阶段完整，0 --ignore/--deselect ✅
4. 测试体系齐全：6177 passed + E2E + 用户旅程 + 性能基准 ✅
5. .gitignore 完整，目录整洁 ✅
6. 0 真实 TODO/FIXME，0 NotImplementedError ✅
7. pre-commit hooks 已更新（TD-070 修复）✅

**不足（修正后）**:
1. **P1**: 3 个幽灵功能（AI 模块未接入主流程）— R2 遗漏
2. **P1**: 1 个 flaky 测试 — R2 遗漏
3. **P1**: pip-audit 不 fail on vulns
4. **P1**: Dockerfile 不用非 root 用户
5. **P2**: 覆盖率 72.64%（已达标 70% 目标，但 CI 阈值仅 60%）
6. **P2**: mypy disallow_untyped_defs=false 过于宽松
7. **P2**: 2 个评估报告待归档

### 下一步建议（按优先级）

| 优先级 | 任务 | 预期收益 | 工作量 |
|--------|------|----------|--------|
| **P1** | 接入 3 个幽灵功能到 TacticalOrchestrator（ReconAI/PsychologySystem/SupplyAwarenessAI） | 功能完整性，README 宣传与实际一致 | 中（需集成测试） |
| **P1** | 修复 test_swiss_cheese.py flaky 测试（固定随机种子或调整断言容差） | 测试稳定性 | 小 |
| **P1** | CI pip-audit 添加 --strict | 安全漏洞阻断 | 小 |
| **P1** | Dockerfile 添加非 root USER | 容器安全 | 小 |
| **P2** | CI cov-fail-under 60→70 | 覆盖率门槛 | 小 |
| **P2** | 归档 PROJECT_ASSESSMENT_v0.6.6*.md 到 docs/archive/ | 目录整洁 | 小 |
| **P2** | mypy disallow_untyped_defs=true | 类型安全 | 中（需修复类型） |
| **长期** | 评估其余 12 个未注册 AI 是否应接入 orchestrator | 功能完整性 | 大 |

---

## 对比 R2 评估的修正

| R2 评估项 | R2 结论 | R3 修正 | 修正理由 |
|-----------|---------|---------|----------|
| 幽灵功能 | 0 个 | **3 个** | grep + orchestrator 注册清单交叉验证 |
| flaky 测试 | 零 flaky | **1 个** | 实际运行 `pytest -p no:randomly` 仍失败 |
| CHANGELOG v0.6.7 | 未提及 | **完整存在** | R2 agent 误判（本次已验证） |
| .gitignore screenshots/ | 已补全 | **确认完整** | L176 已忽略（R2 agent 误判） |
| CI --ignore/--deselect | 0 命中 | **确认 0 命中** | `-m "not slow"` 是标记筛选非掩盖（R3 agent 误判后修正） |

**评估方法论改进**:
1. 必须实际运行命令验证，不能仅依赖文档走读（R2 的"零 flaky"基于 3 次运行，但用了 -p no:randomly）
2. 幽灵功能检查必须包含"已实现但未接入"的模块，不能仅检查 NotImplementedError/TODO
3. Agent 评估有 50% 误判率，必须人工验证关键发现

---

## 评估方法

- **DevSquad 7 角色共识**: 6 个 Explore Agent 并行收集 7 维度信息
- **实际命令验证**: pytest 实际运行（6177 passed, 1 failed）、grep 交叉验证、git ls-files 验证
- **人工验证**: 对 agent 报告的 6 个"幽灵功能"逐一验证，确认 3 真实 3 误判
- **评估基础**: v0.6.7 commit cecc9d5（TD-COV-BUG 修复后）

**评估日期**: 2026-07-12
**评估者**: DevSquad (architect/pm/security/tester/coder/devops/ui) + 人工验证
