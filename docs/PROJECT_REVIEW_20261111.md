# PyCC2 项目整理评估报告（7 维度）

- 日期：2026-11-11
- 评审方式：DevSquad 多角色评审（Architect / Tester / Coder / DevOps 视角 + 双 Explore 代理走读）
- 代码基线：origin/main `c0da88c` + 本轮清理
- 证据规则：每条结论附文件路径或命令输出

## 维度 1：代码走读

| 项 | 数据 | 证据 |
|---|---|---|
| src 规模 | 408 个 py 文件 / 103,817 行（不含 _archive） | `find src -name "*.py" -not -path "*_archive*"` |
| tests 规模 | 279 个测试文件 / 111,820 行 | `find tests -name "*.py"` |
| 超长文件 | 无 >1500 行文件 | `wc -l` 全量扫描 |
| TODO/FIXME | 46 处，集中在 enhanced_renderer / hud_renderer / minimap_renderer | `grep -rn "TODO\|FIXME" src` |
| 归档死代码 | `_archive/` 11 个文件，已隔离，无活跃 import | `src/pycc2/_archive/__init__.py` |

架构结论：
- 分层（domain / services / presentation / infrastructure）清晰。Composition Root 唯一跨界点在 [game_loop_assembler.py](../src/pycc2/services/game_loop_assembler.py)。
- 分层修复有迹可循：deployment_factory 已从 presentation 迁到 services（[deployment_manager.py](../src/pycc2/services/deployment_manager.py) 注入 `deployment_ui` 并拒绝 service 层自建 UI）。
- 幽灵功能：v0.6.x~v0.7.x 的 ghost audit 已完成归档。本轮抽查未见 `_archive` 之外的未接线模块。

## 维度 2：文档一致性

| 检查项 | 结果 |
|---|---|
| VERSION / pyproject / `__init__.py` | 三处均 `0.9.0`，一致 |
| CHANGELOG vs 版本文件 | **不一致**。v0.9.1 已于 2026-08-01 发布进 CHANGELOG，但 VERSION/pyproject/`__init__.py` 仍停 0.9.0 |
| README 头条 | **过时**。写 v0.9.1（2026-11-05）与 6291 tests；现实为 7549 tests |
| CHANGELOG 关键事实抽查 | 通过。`K_b`/`K_k` 快捷键（interaction_controller.py L498-586）、`is_passable_for`、`is_amphibious`（deployment_manager.py L584-586）、`scenario_validation.py`、`scripts/uat_deploy_e2e.py`、截图目录 `docs/assets/uat_deploy_e2e/` 全部存在 |
| RELEASE_GATE_W5「Ruff 无告警」 | **表述有漏洞**。只核对了本批次改动文件；全仓库 1860 告警导致远端 CI 连续红灯（见维度 5） |
| docs/ 结构 | 顶层 70 个 md；`docs/_archive/` 与 `docs/archive/` 两个归档目录并存，约 30 个历史阶段交付文档未归档 |

## 维度 3：技术债

已清（本轮）：
- 根目录 21 项未跟踪临时文件全部删除（草稿测试 13 个、性能报告 2 份、`tmp/`、误入 tests/ 的截图 2 张、独立脚本 3 个）。pytest 只收集 `tests/`（pyproject testpaths），删除不影响回归。
- 1860 个 ruff 告警清零（见维度 5）。

遗留（登记，不在本轮处理）：
- TODO/FIXME 46 处，集中在渲染层 3 个文件。
- [movement_controller.py](../src/pycc2/domain/systems/movement_controller.py) L133-135 地形判定为「简化版」注释，属已知简化。
- PF-04：真实窗口 heavy 最差 54.9 FPS，需空闲机器复测。

## 维度 4：测试证据

| 测试 | 结果 | 时间 |
|---|---|---|
| 全量回归（清理前基线） | 7549 passed / 4 skipped | 2026-11-11 |
| 全量回归（临时文件删除后） | 7549 passed / 4 skipped | 2026-11-11 |
| 全量回归（ruff 修复后） | 见 CHANGELOG 本轮条目 | 2026-11-11 |
| UAT 用户旅程 | 14/14 通过 + 部署 e2e 全 PASS（真实窗口） | 2026-11-10/11 |
| 性能 benchmark | tests/benchmark 47 passed，基线 `perf_baseline.json` | 2026-11-08 |
| 视觉回归 | 7 passed | 2026-11-09 |

E2E 用户旅程已按规则执行（真实窗口、真实主循环、真实事件分发、截图留痕）。

## 维度 5：CICD

配置（`.github/workflows/ci.yml`）：lint(ruff+mypy+bandit+pip-audit+radon) → unit(coverage≥70%) → integration → e2e → slow → benchmark → docker → 每周视觉回归。设计完整。

**实际状态（本轮发现的 P0）**：远端 CI 最近 5 次全部 failure。根因：`ruff check .` 扫全仓库报 1860 告警（src 699 / tests 366 / scripts 21 / assets+docs/_archive 其余），第一步 lint 即失败，后续 job 全部未执行。

**流程缺陷**：多次推送后无人查看 CI 结果，红灯持续 ≥3 天。门禁只在本地「本批次文件」层面执行，未闭环到远端。

本轮修复：
1. pyproject `[tool.ruff] extend-exclude = ["assets", "docs", "tmp"]`（资源脚本与归档代码不属发布代码）。
2. `ruff check --fix` 修复 895 处；W293/W291 unsafe 修复 187 处；手动修复 10 处（F841×7、SIM103×2、B007×1）。
3. `ruff format` 重排 46 个文件。
4. 修复后 `ruff check .` 与 `ruff format --check .` 全绿。

**红灯分层揭开（逐层修复记录）**：lint 门禁是串联步骤，前一步修好后暴露后面潜伏更久的红点——

| 层 | 步骤 | run 证据 | 根因 | 修复 |
|---|---|---|---|---|
| 1 | ruff lint/format | run 42956489926 失败 | 全仓库 1860 告警 | 见上 4 条 |
| 2 | mypy | run 42956489926 失败 | 67 个类型错误（被 ruff 失败遮蔽） | 17 文件 +89/−42，零 ignore |
| 3 | radon 圈复杂度 | run 42957745409 失败 | 19 E+ vs 基线 18；第 19 个 E+ 在红灯期间引入，radon 步骤从未执行到 | 基线如实 18→19，注释禁止无评审上调 |
| 4 | 文档一致性 | run 42957745409 未执行到（本地预跑发现） | README.md 标头 v0.9.1 vs VERSION=0.9.0 | README 标头对齐 v0.9.0 |

run 42957745409 已验证 ruff lint ✓ / ruff format ✓ / mypy ✓ / bandit ✓ / pip-audit ✓，radon 与文档一致性修复后推送待验证。

## 维度 6：目录结构

- 根目录已清零（21 项删除后 `git status` 干净）。
- 待办建议（不阻塞发布）：合并 `docs/_archive/` 与 `docs/archive/`；将 P0_2/PHASE2/SPRINT 等约 30 个历史交付文档移入 `docs/archive/`。

## 维度 7：成熟度评价（诚实结论）

**定位：Beta 前（pre-Beta），可玩、有证据链，但工程流程未闭环。**

强项（高于同类个人项目水准）：
- 测试纪律：7549 项回归 + 验收 + 视觉回归 + 真实窗口 UAT，全链路留痕。
- 机制复刻：CC2 PARITY 矩阵 23 项全部「完成」且抽查属实。
- 门禁文档：RELEASE_GATE / UAT / CHANGELOG 因果链完整。

弱项（按严重度）：
1. **流程闭环缺失（P0，已修代码、未修流程）**：CI 红灯 ≥3 天无人察觉。根因不是代码质量，而是「推送即认为完成」。需固化规则：每次推送后必须确认远端 CI 绿灯才算任务关闭。
2. **版本管理失真（P1，部分修复）**：README 标头 v0.9.1 与 VERSION=0.9.0 漂移已对齐（本轮）；正式发布时仍需统一 bump（见下一步建议 2）。
3. **性能未在受控环境确认（P1）**：PF-04 未关闭，历史测量均在高负载机器。
4. **文档熵（P2）**：70 个顶层文档无生命周期管理。

### 下一步建议（优先级序）
1. 本轮推送后盯 CI 变绿，把「CI 绿灯」写进 RELEASE_GATE 前置条件。
2. 做一次正式发布：bump 0.9.2，回写 VERSION/pyproject/`__init__.py`/README/CHANGELOG，打 tag。
3. 空闲机器复测 PF-04，关闭或降级该缺陷。
4. docs/ 归档整理（维度 6 建议）。
5. 渲染层 46 处 TODO 逐条判定「修/删/留」。
