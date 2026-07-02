# PyCC2 项目成熟度评估 D12 (2026-07-02)

## 评估概览

| 维度 | 评分 | 等级 | D9 对比 |
|------|------|------|---------|
| 1. 架构 | 5/10 | D+ | ↓ (D9: 7) |
| 2. 安全 | 7/10 | B- | → (D9: 7) |
| 3. 测试 | 7/10 | B- | ↓ (D9: 8) |
| 4. 性能 | 8/10 | B+ | → (D9: 8) |
| 5. 可维护性 | 6/10 | C | ↓ (D9: 7) |
| 6. 文档 | 3/10 | F | ↓ (D9: 5) |
| 7. 集成 | 5/10 | D+ | ↓ (D9: 7) |
| **总分** | **5.9/10** | **D+** | ↓ (D9: 6.6/C+) |

**评估方法**: DevSquad V3.8 — 4 个并行评估 agent（架构+可维护性 / 安全+集成 / 测试+性能 / 文档+CI/CD+目录）+ Coordinator 独立验证关键 P0 发现。

**评分下降原因**: D12 比 D9 检查更严格，暴露了 D9 未发现的硬约束违反（PROJECT_STATUS.md/SKILL.md/VERSION 文件缺失、SKIP_E2E 缺失、覆盖率 53%<60%）。D11 拆分质量高但仅处理 3/8 大文件。

---

## 维度1: 架构 (5/10)

### 发现
- **>1000 行文件**: 5 个（D11 仅处理 3/8，D9 清单遗漏）
  - `terrain_tile_generator.py` 1324L
  - `deployment_renderer.py` 1170L
  - `pixvoxel_loader.py` 1139L（同时是 ghost 模块）
  - `infantry_pixel_renderer.py` 1136L
  - `campaign_ui_rendering.py` 1120L
- **>500 行文件**: 50 个（D9 时 53，仅减 3）
- **God Class** (>30 方法): 9 个
  - `unit.py` 54 方法 / 937L — 最高优先级
  - `deployment_ui.py` 50 方法
  - `enhanced_sound_bridge.py` 44 方法
  - `sound_system.py` 43 方法
  - `sprite_renderer_base.py` 39 方法（D11 拆分后）
  - `smoke_tactical_ai.py` 35 方法
  - `cc2_combat_effects.py` 33 方法
  - `environmental_audio.py` 33 方法
  - `enhanced_renderer.py` 31 方法
- **循环依赖**: 无运行时循环。30+ TYPE_CHECKING 守卫。

### 正面
- D11 拆分的 3 个文件 facade/mixin 模式一致，__all__ 完整，public API 100% 向后兼容
- _environment 死代码正确保留并文档化（3 处注释）

---

## 维度2: 安全 (7/10)

### 发现
- **密码存储**: 项目无用户认证（单机 pygame 游戏）。存档完整性用 HMAC-SHA256（`save_system.py:274`）。`hashlib.sha256` 裸用仅见于 resource_cache.py（资源校验）和 cc2_building_common.py:37（程序化生成确定性哈希），均非密码场景。
- **hmac.compare_digest**: 使用确认（`save_system.py:350`）
- **prompt injection**: 不适用（项目无 LLM 集成）
- **CORS**: 不适用（无 web 服务器）
- **敏感信息**: 无明文存储

### P1 问题
- `docs/SECURITY.md` 宣称 "PBKDF2 100k 迭代已实现"，实际 `save_system.py` 未实现 PBKDF2（仅 HMAC）。文档/代码不一致。

---

## 维度3: 测试 (7/10)

### 实测数据（独立复跑验证）
- **单元测试**: 3734 passed / 0 failed / 2 skipped (9.97s)
- **E2E 测试**: 483 passed / 0 failed / 5 skipped / 1 xpassed (38.58s)
- **覆盖率**: **53%**（门槛 60% — **未达标**）
  - 实测命令: `pytest tests/unit/ --cov=src/pycc2 --cov-report=term`
  - TOTAL: 44166 statements, 18812 missed, 14014 partial, 1591 branches
- **mypy**: 0 errors / 382 files
- **ruff**: 0 errors
- **slow tests**: 15 passed / 0 failed (2.38s)
- **benchmark**: 21 passed / 0 failed (9.62s)

### P0 问题
- 覆盖率 53% < 60% 门槛，且 `pyproject.toml [tool.coverage.report]` 未配置 `fail_under`，无回归门禁，存在静默下降风险

### P1 问题
- SKIP_E2E 机制在 CI 中完全缺失（代码库无 SKIP_E2E 引用）
- unit 层显式 performance 维度用例偏少（perf/timeout 断言集中在 tests/benchmark/）

---

## 维度4: 性能 (8/10)

### 发现
- slow tests + benchmark 36 项全过
- `tests/benchmark/PERF_THRESHOLDS.md` 定义 4 组件阈值
- `.baseline_results.json` 366KB 历史基线数据
- 3 个性能测试文件

### 正面
- 性能护栏完整，有阈值文档 + 历史基线 + 回归检测

---

## 维度5: 可维护性 (6/10)

### 幽灵功能（有测试无生产引用）: 12 个
- **大文件 ghost**: `infantry_renderer.py` 653L、`pixvoxel_loader.py` 1139L（仅 scripts/ 引用）、`enhanced_pixel_artist.py`、`terrain_enhancer.py`、`debug_overlay.py`、`lighting_renderer.py`
- **小 ghost**: `domain.ai.command_obedience`、`communication_system`、`mg_takeover`、`domain.systems.combat_config`、`terrain_detail_generator`、`unit_diversity_expansion`（已部分迁移）

### 正面
- D11 facade/mixin 拆分模式一致
- _environment 死代码正确文档化

---

## 维度6: 文档 (3/10)

### P0 问题（硬约束违反）
1. **`docs/PROJECT_STATUS.md` 缺失** — 硬约束要求项目必须包含此文档
2. **`SKILL.md` 缺失** — 硬约束要求模块数与实际一致
3. **`VERSION` 文件缺失** — 硬约束要求 VERSION+__init__.py+pyproject.toml 三处一致
4. **三语 README 测试数不一致**: README.md/README_ja.md 仍为旧值 `~4367`，README_zh.md 已更新为 `4424/4398/25`
5. **模块数严重低估**: README_zh.md 声称 `~283个`，实际 src/pycc2 下 380 个 .py 文件

### P1 问题
- CHANGELOG D11 "累计 4217 tests" 与 D10 "4424 collected/4398 passed" 数据口径不一致
- README.md/README_ja.md 缺 "最后更新" 行
- docs/SECURITY.md PBKDF2 宣称与代码不符

---

## 维度7: 集成 (5/10)

### P0 问题
- **事件名大小写不匹配**: `combat_service.py:118` `publish_named("unit_attacked",...)` 但订阅者用 PascalCase `"UnitAttacked"`（`achievement_event_bridge.py:38`、`combat_camera_controller.py:52`），事件丢失

### P1 问题
- **9 个孤儿事件**（发布无订阅）: UnitArrived、weapon_fired、AttackCommand、OrderRefused、BridgeDestroyed、MGAbandoned、MGTakeover、EndBattle
- **1 个反向孤儿**（订阅无发布）: CampaignComplete

### 正面
- tactic_executor 包 9 文件导入 OK，MRO 正确
- sprite_renderer 5 mixin 组合 OK
- dispatch_table 32 TacticType 完整

---

## CI/CD (5/10)

### P0 问题（硬约束违反）
1. **SKIP_E2E 变量完全缺失** — 硬约束要求默认 "0"
2. **release.yml 无独立 publish-pypi job** — 仅有 step（release.yml:104），非独立 job

### P1 问题
- `ci.yml` docker-build job 缺 timeout-minutes
- `release.yml` release job 缺 timeout-minutes

### 正面
- mypy 检查为阻塞状态（无 continue-on-error）
- 6/7 个 ci.yml job 有 timeout-minutes

---

## 目录清理 (7/10)

### P1 问题
- `.gitignore` 缺 `coverage.json`（仅有 coverage.xml）

### 正面
- 无临时文件（.tmp/.bak/_draft/_old 均无）
- 工作区干净
- __pycache__ 正确 gitignore
- requirements.lock 干净（无 SSH 私有仓库、无本地路径）

---

## P0 问题汇总（9 项，按优先级）

| # | 问题 | 文件 | 修复方案 |
|---|------|------|----------|
| P0-1 | 5个>1000L文件未拆分 | terrain_tile_generator.py 等 5 文件 | D13 按风险从低到高拆分 |
| P0-2 | unit.py God Class 54方法 | src/pycc2/domain/entities/unit.py | 拆分为 entity+combat+morale+movement mixin |
| P0-3 | 事件名大小写不匹配致事件丢失 | combat_service.py:118 | 统一为 snake_case 或 PascalCase |
| P0-4 | PROJECT_STATUS.md 缺失 | docs/ | 新建，含版本/模块/测试数 |
| P0-5 | 三语 README 测试数不一致 | README.md/README_ja.md | 同步为 4217 passed |
| P0-6 | SKILL.md 缺失 + 模块数低估 | README_zh.md:106 | 新建 SKILL.md，更新模块数 380 |
| P0-7 | SKIP_E2E 在 CI 缺失 | .github/workflows/ | 添加 SKIP_E2E=0 默认值 |
| P0-8 | release.yml 无独立 publish-pypi job | .github/workflows/release.yml | 拆为独立 job |
| P0-9 | 覆盖率 53%<60% 无门禁 | pyproject.toml | 添加 fail_under=60 + 提升覆盖率 |

## P1 问题汇总（8 项）

| # | 问题 | 修复方案 |
|---|------|----------|
| P1-1 | 12 ghost 模块 | 删除或集成 |
| P1-2 | 9 孤儿事件 + 1 反向孤儿 | 对齐发布/订阅契约 |
| P1-3 | SECURITY.md PBKDF2 宣称不符 | 修正文档或实现 PBKDF2 |
| P1-4 | VERSION 文件缺失 | 新建 VERSION 文件 |
| P1-5 | 2 处 timeout-minutes 缺失 | ci.yml docker-build + release.yml release |
| P1-6 | .gitignore 缺 coverage.json | 添加 |
| P1-7 | CHANGELOG 测试数口径不一致 | 统一口径 |
| P1-8 | README en/ja 缺"最后更新"行 | 同步 |

---

## 下一步建议

### 立即修复（P0，优先级从高到低）
1. **P0-4/5/6/7/8 文档+CI 修复**（低风险，1-2h）: PROJECT_STATUS.md + VERSION + SKILL.md + SKIP_E2E + publish-pypi job + 三语 README 同步 + .gitignore
2. **P0-9 覆盖率门禁**（低风险，30min）: pyproject.toml 添加 `fail_under=60`，先建立门禁再逐步提升覆盖率
3. **P0-3 事件名统一**（中风险，1h）: 统一 event_bus 事件名为 snake_case，修复 9 个孤儿事件
4. **P0-1 5个大文件拆分**（高风险，2-3天）: D13 按风险从低到高拆分 terrain_tile_generator / deployment_renderer / pixvoxel_loader / infantry_pixel_renderer / campaign_ui_rendering
5. **P0-2 unit.py God Class 拆分**（最高风险，1天）: 拆分为 entity+combat+morale+movement mixin

### 中期改进（P1）
1. 删除 12 ghost 模块（含 2 个 >600L）
2. 对齐 event_bus 发布/订阅契约（9 孤儿 + 1 反向孤儿）
3. 修正 SECURITY.md PBKDF2 宣称
4. 逐步提升覆盖率 53%→60%+

### 长期改进（P2）
1. mypy 启用 `check_untyped_defs=true`
2. 添加独立 application 层
3. 性能阈值组件数从 4 扩展到 8+

---

## 评估方法学说明

- **评估命令**: DevSquad V3.8 "项目整理评估"（7 维度 + CI/CD + 目录清理）
- **数据采集**: 4 个并行 Explore subagent
- **独立验证**: 9 项 P0 发现全部经直接命令验证（find/wc -l/ls/grep/pytest --cov）
- **基线对比**: D9 报告 docs/ASSESSMENT_D9_MATURITY.md（v0.4.0, commit 253e471, 2026-06-29）
- **本次基线**: v0.4.0, commit 884c6e1, 2026-07-02
- **回归测试**: 3734 unit + 483 e2e = 4217 passed / 0 failed
