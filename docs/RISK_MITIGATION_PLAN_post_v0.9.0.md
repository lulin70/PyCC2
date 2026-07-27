# PyCC2 Post-v0.9.0 风险点改进方案

> **日期**: 2026-07-24
> **来源**: [PROJECT_ASSESSMENT_v0.9.0.md](archive/PROJECT_ASSESSMENT_v0.9.0.md) 维度 7 诚实评价
> **方法**: DevSquad V4.1.7 7-Role 共识
> **范围**: 4 个风险点（风险点 1 视觉回归 baselines 用户接受现状，不纳入本次改进）

---

## 一、风险点清单与改进方案

### 风险点 2: CI 覆盖率门禁 65% < 目标 70%

| 项目 | 详情 |
|------|------|
| **现状** | `ci.yml` L111 `--cov-fail-under=65` (v0.9.0 视觉打磨期临时调整, commit c4e2146) |
| **实际覆盖率** | 72.64% (42764 stmts, 10107 missed, 已达 70% 目标) |
| **改进方案** | 恢复 `--cov-fail-under=70` |
| **风险评估** | 低 — 实际覆盖率 72.64% 已超过 70% 阈值,有 2.64% 缓冲 |
| **实施文件** | `.github/workflows/ci.yml` L111 |
| **验证** | 下次 CI 运行时 unit-tests job 应通过 |

### 风险点 3: dependabot 配置不符合 project_memory Hard Constraint

| 项目 | 详情 |
|------|------|
| **现状** | `.github/dependabot.yml` weekly + groups python-minor (minor+patch) |
| **Hard Constraint** | 1) ignore patch/minor for dev dependencies; 2) daily for security updates; 3) mypy pin upper limit `<1.12` |
| **改进方案 A** | pip ecosystem: schedule weekly → daily (security updates) |
| **改进方案 B** | pip ecosystem: 添加 `ignore` 段排除 dev dependencies 的 patch/minor updates |
| **改进方案 C** | pyproject.toml: `mypy>=1.7` → `mypy>=1.7,<1.12` |
| **风险评估** | 低 — daily 可能增加 PR 噪音,但 Hard Constraint 明确要求; mypy 上限防止新检查破坏构建 |
| **实施文件** | `.github/dependabot.yml` + `pyproject.toml` |
| **验证** | 下次 dependabot 运行时应遵守新配置; mypy 限制生效需重新生成 lock 文件 |

**注意**: github-actions ecosystem 保持 weekly (非 dev dependency,Hard Constraint 仅约束 dev deps)

### 风险点 4: D13-N8 INSTALL 三语文档版本号滞后 + 结构差异

| 项目 | 详情 |
|------|------|
| **现状** | INSTALL.md/INSTALL_zh.md/INSTALL_ja.md 标题均为 "v0.6.10",但项目已 v0.9.0 |
| **根因** | `check_doc_consistency.sh` REQUIRED_DOCS 未包含 INSTALL 三语文件,CI 无法捕获滞后 |
| **结构差异** | INSTALL.md (9 章节,无版本历史) / INSTALL_zh.md (10 章节,含版本历史) / INSTALL_ja.md (8 章节,含版本历史) |
| **改进方案 A** | 修正三语文件标题版本号 v0.6.10 → v0.9.0 |
| **改进方案 B** | 将 INSTALL.md/INSTALL_zh.md/INSTALL_ja.md 加入 check_doc_consistency.sh REQUIRED_DOCS |
| **改进方案 C** | 移除"版本历史"表 (应由 CHANGELOG.md/CHANGELOG_zh.md/CHANGELOG_ja.md 管理,INSTALL 不应维护版本历史) |
| **改进方案 D** | 统一三语章节顺序为: 系统要求 → Python 设置 → 标准安装 → 平台特定说明 → 配置 → 验证 → 故障排查 → 开发环境 → 卸载 |
| **风险评估** | 低 — 文档同步是 user 偏好"文档先行,万事留痕"的核心要求;外部文档是用户第一印象 |
| **实施文件** | `INSTALL.md` + `INSTALL_zh.md` + `INSTALL_ja.md` + `scripts/check_doc_consistency.sh` |
| **验证** | `./scripts/check_doc_consistency.sh` 应包含 INSTALL 三语检查并 PASS |

### 风险点 5: TD-007 地图边界 `_scatter` 函数

| 项目 | 详情 |
|------|------|
| **现状** | ACCEPTED (v0.4.14, 2026-07-09) — `_scatter` 直接覆盖地形不检查重要性 (road/bridge/building 可能被 hedge/woods/rough 覆盖) |
| **不修复原因** | 修改需重新生成 64 个地图 JSON + 影响 7 个测试文件 (含 E2E),高风险低收益; 原始 4 个问题记录已丢失无法验证; 无用户报告实际游戏地图边界问题 |
| **改进方案** | 维持 ACCEPTED 状态,在 TECH_DEBT.md 中明确记录决策依据 |
| **风险评估** | 无 — 已基于 Simplicity First + Surgical Changes 原则评估 |
| **实施文件** | 无代码变更 (TECH_DEBT.md TD-007 条目已完整记录) |
| **验证** | TD-007 条目状态行确认 ACCEPTED |

---

## 二、DevSquad 7-Role 共识表

| 角色 | 投票 | 置信度 | 关键意见 |
|------|------|--------|----------|
| Architect | APPROVE | 高 | 4 项方案均符合 Simplicity First + Surgical Changes,无架构影响 |
| PM | APPROVE | 高 | INSTALL 版本号滞后是严重文档 bug,必须修复;TD-007 维持现状合理 |
| Security | APPROVE | 高 | dependabot daily 安全更新 + mypy 上限防止供应链和构建风险 |
| Tester | APPROVE | 高 | CI 门禁恢复 70% 是质量回归;INSTALL 加入 check_doc_consistency 防回归 |
| Coder | APPROVE | 高 | 4 项实施工作量小,无代码逻辑变更,仅配置和文档 |
| DevOps | APPROVE | 高 | dependabot 配置对齐 Hard Constraint 是 CI/CD 卫生要求 |
| UI Designer | APPROVE | 高 | INSTALL 三语结构统一提升用户第一印象 |

**共识结论**: ✅ 通过 (7/7 APPROVE,无否决) → 推进 4 项改进

---

## 三、实施计划

### Wave 1: 配置修复 (低风险,立即推进)

1. `.github/workflows/ci.yml` L111: `--cov-fail-under=65` → `--cov-fail-under=70`
2. `.github/dependabot.yml`:
   - pip schedule: `weekly` → `daily`
   - pip 添加 `ignore` 段 (dev dependencies patch/minor)
   - github-actions 保持 weekly
3. `pyproject.toml`: `mypy>=1.7` → `mypy>=1.7,<1.12`

### Wave 2: 文档修复 (中等工作量)

4. `INSTALL.md`: 标题 v0.6.10 → v0.9.0,移除"版本历史"(无),章节顺序保持
5. `INSTALL_zh.md`: 标题 v0.6.10 → v0.9.0,移除"版本历史"表,章节顺序统一
6. `INSTALL_ja.md`: 标题 v0.6.10 → v0.9.0,移除"バージョン履歴"表,章节顺序统一
7. `scripts/check_doc_consistency.sh`: REQUIRED_DOCS 添加 INSTALL.md/INSTALL_zh.md/INSTALL_ja.md

### Wave 3: 验证与推送

8. 运行 `./scripts/check_doc_consistency.sh` 验证全绿
9. 运行 `ruff check .` + `ruff format --check .` 验证
10. Git commit + push

---

## 四、验收标准

- [x] `ci.yml` `--cov-fail-under=70`
- [x] `dependabot.yml` pip schedule=daily + ignore patch/minor for dev deps
- [x] `pyproject.toml` mypy `>=1.7,<1.12`
- [x] INSTALL.md/INSTALL_zh.md/INSTALL_ja.md 标题 v0.9.0
- [x] INSTALL_zh.md/INSTALL_ja.md 移除"版本历史"表
- [x] `check_doc_consistency.sh` REQUIRED_DOCS 含 INSTALL 三语
- [x] `./scripts/check_doc_consistency.sh` 全绿
- [x] `ruff check .` 0 errors
- [x] `ruff format --check .` 0 errors
- [x] Git commit + push 成功
